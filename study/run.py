"""Case study runner: ADMM coordination, envelope dispatch, closed-loop
1-minute MPC, and nonlinear AC evaluation of every case."""
from __future__ import annotations
import numpy as np, json, time, sys
import system as S, transit as T, powerflow as PF, opt, coord

RES = {}


# --------------------------------------------------------------- setup -----
def setup(seed=7):
    v, g = T.synthetic_urban_cycle(T.LEG_MIN * 60)
    leg, dist = T.leg_energy_kwh(v, g)
    events, cycle = T.build_timetable(leg)
    av = T.availability(events)
    edrv = T.drive_energy(events, leg)
    deps = T.departures(events)
    exo = S.build_exogenous(seed=seed)
    feeder = PF.Feeder()
    net = opt.Network(feeder, exo)
    d = dict(leg_kwh=leg, leg_km=dist, cycle=cycle, av=av, edrv=edrv,
             deps=deps, exo=exo, feeder=feeder, net=net,
             netload=exo["load_hub"] - exo["pv_hub"])
    d["av15"] = av.reshape(4, T.N_VEH, S.T_DAY, 15).mean(3)
    d["edrv15"] = edrv.reshape(T.N_VEH, S.T_DAY, 15).sum(2)
    d["netload15"] = d["netload"].reshape(4, S.T_DAY, 15).mean(2)
    # controllable-power capacity per hub at 15 min (bays actually occupied)
    occ = np.minimum(d["av15"].sum(1), np.array([h.n_bays for h in S.HUBS])[:, None])
    d["cap15"] = occ * np.array([h.p_bay_kw for h in S.HUBS])[:, None]
    d["cap15"][S.HUB_IDX["D"]] += S.HUBS[S.HUB_IDX["D"]].bess_kw
    return d


# ---------------------------------------------------------------- ADMM -----
def admm(d, rho=2.0e-3, iters=40, tol_p=8.0, verbose=True, vmin_ul=None):
    H, Tn = len(S.HUBS), S.T_DAY
    P = np.zeros((H, Tn)); F = np.zeros((H, Tn)); U = np.zeros((H, Tn))
    hist = []
    tul = tfl = 0.0
    for it in range(iters):
        P, dt1, oul, u, fl = opt.upper_level(
            d["net"], d["exo"], d["exo"]["price"], d["netload15"], d["cap15"],
            rho=rho * S.S_BASE_KVA ** 2, target=F - U, vmin_ul=vmin_ul)
        r = opt.fleet_lp(d["av15"], d["edrv15"], d["deps"], d["exo"]["price"],
                         rho=rho, target=P + U, lam=np.zeros(Tn),
                         cap_ctrl=d["cap15"])
        Fn = r["ctrl"]
        s = rho * np.linalg.norm(Fn - F)          # dual residual
        F = Fn
        res = P - F
        U = U + res
        pr = np.linalg.norm(res)
        tul += dt1; tfl += r["t"]
        hist.append(dict(it=it + 1, primal=float(pr), dual=float(s),
                         obj_ul=float(oul), obj_fleet=float(r["obj"]),
                         eps=float(r["eps"].sum())))
        if verbose:
            print(f"  ADMM {it+1:3d}  ||r||={pr:9.2f} kW  ||s||={s:9.3f}  "
                  f"f_UL={oul:11.1f}  f_F={r['obj']:9.1f}", flush=True)
        if pr < tol_p and s < tol_p * rho * 50:
            break
    # C-4: at the fixed point rho*U = -d f_UL / d P, i.e. minus the network's
    # marginal cost of hub power. The nodal price seen by the fleet is its negative.
    lam = -rho * U / S.DT_UL                          # currency/kWh
    return dict(P=P, F=F, lam=lam, hist=hist, u=u, flow=fl,
                t_ul=tul, t_fleet=tfl, soc15=r["soc"], eps=r["eps"],
                obj_ul=oul, obj_fleet=r["obj"])


# ------------------------------------------------------------- envelope ----
def envelope(d, P, u, flow, vmin=None):
    """UL-9 / UL-9a: largest hub-power perturbation preserving security."""
    vmin = S.V_MIN if vmin is None else vmin
    net, f = d["net"], d["feeder"]
    H, Tn = len(S.HUBS), S.T_DAY
    rho_p = np.full((H, Tn), np.inf)
    for h in range(H):
        col = net.Mu[:, h]
        m = col > 1e-9
        vmarg = (u[m] - vmin ** 2) / col[m][:, None]           # (nb',T)
        rho_p[h] = np.minimum(rho_p[h], vmarg.min(0))
        g = net.G[:, h] > 0
        lim = np.sqrt(np.maximum(net.smax[g][:, None] ** 2 - net.Qb[g] ** 2, 1e-9))
        rho_p[h] = np.minimum(rho_p[h], (lim - flow[g]).min(0))
    rho_p = np.maximum(rho_p, 0.0) * S.S_BASE_KVA               # kW
    pmax = P + rho_p
    for h in range(H):
        pmax[h] = np.minimum(pmax[h], S.HUBS[h].p_pcc_kw - d["netload15"][h])
    return np.maximum(pmax, 0.0), rho_p


# ------------------------------------------------------- closed-loop sim ----
def forecast_series(d, seed, pv_std=0.10, load_std=0.02, clip=0.30):
    """Sec. 3.5-i: the MPC plans on forecasts, the plant realises the truth.
    Multiplicative, correlated error on PV and site load; the dispatch is then
    executed against the measured series in `evaluate`."""
    rng = np.random.default_rng(seed)
    H, K = len(S.HUBS), S.K_DAY
    kern = np.exp(-0.5 * (np.arange(-45, 46) / 18.0) ** 2); kern /= kern.sum()

    def err(std):
        e = np.stack([np.convolve(rng.normal(0, 1, K), kern, mode="same")
                      for _ in range(H)])
        e = e / max(e.std(), 1e-9) * std
        return np.clip(e, -clip, clip)

    pv_f = np.clip(d["exo"]["pv_hub"] * (1 + err(pv_std)), 0.0, None)
    ld_f = np.clip(d["exo"]["load_hub"] * (1 + err(load_std)), 0.0, None)
    return ld_f - pv_f


def simulate(d, mode, pmax15=None, lam15=None, Np=40, ctrl_int=2, verbose=True,
             netload_fc=None, env_on_net=False, d_plan=None, band=0.955,
             tick_min=60, ac_correct=False):
    """mode: 'dumb' | 'local' | 'hier' | 'roll'

    'roll' is the framework as specified: the upper level re-solves on a
    rolling window every `tick_min` minutes against the fleet's measured SoC,
    so feeder-load forecast error is rejected in closed loop instead of being
    carried for the whole day.
    """
    H, K, NV = len(S.HUBS), S.K_DAY, T.N_VEH
    av, edrv, deps = d["av"], d["edrv"], d["deps"]
    soc = np.full(NV, T.SOC_START)
    bess = 0.5
    Pchg = np.zeros((H, NV, K)); Pb = np.zeros((2, K))
    socs = np.zeros((NV, K + 1)); socs[:, 0] = soc
    bs = np.zeros(K + 1); bs[0] = bess
    tsolve = []
    price = d["exo"]["price"]
    if pmax15 is None:
        pmax15 = np.stack([np.full(S.T_DAY, S.HUBS[h].p_pcc_kw)
                           - d["netload15"][h] for h in range(H)])
    pmax1 = np.repeat(pmax15, 15, axis=1)
    if lam15 is None:
        lam1 = np.stack([price] * H)          # plain TOU tariff
    else:
        lam1 = np.repeat(lam15, 15, axis=1)   # distribution nodal price (UL-10)
    hD = S.HUB_IDX["D"]
    dp = d if d_plan is None else d_plan
    ul_ticks, ul_time = 0, 0.0
    k = 0
    while k < K:
        na = min(ctrl_int, K - k)
        if mode == "roll" and k % tick_min == 0:
            t15 = k // 15
            t0c = time.perf_counter()
            if ac_correct:
                a = coord.coordinate_ac(dp, t0=t15, soc0=soc, bess0=bess,
                                        band=band)
            else:
                a = coord.admm_qp(dp, rho=1.2e-2, iters=60, eps_abs=0.02,
                                  verbose=False, t0=t15, soc0=soc, bess0=bess)
            pm, _, _ = coord.envelope_joint(dp, a["P"], a["u"], a["flow"],
                                            vmin=band, t0=t15)
            pm_net = dp["netload15"][:, t15:] + pm
            end = min(k + tick_min, K)
            n15 = int(np.ceil((end - k) / 15))
            pmax1[:, k:end] = np.repeat(pm_net[:, :n15], 15, axis=1)[:, :end - k]
            lam1[:, k:end] = np.repeat(a["lam"][:, :n15], 15, axis=1)[:, :end - k]
            ul_ticks += 1
            ul_time += time.perf_counter() - t0c
        for h in range(H):
            present = av[h, :, k:min(k + Np, K)].any()
            if not present:
                continue
            if mode == "dumb":
                # greedy: fill the lowest-SoC vehicles first, bays permitting
                cand = [b for b in range(NV) if av[h, b, k] and soc[b] < T.SOC_MAX - 1e-6]
                cand.sort(key=lambda b: soc[b])
                for b in cand[:S.HUBS[h].n_bays]:
                    room = (T.SOC_MAX - soc[b]) * T.E_VEH_KWH / (T.ETA_CHG * S.DT_LL)
                    Pchg[h, b, k] = min(S.HUBS[h].p_bay_kw, room)
                continue
            # terminal value of stored energy: mean forward price plus a
            # premium, so the receding horizon does not walk the fleet down
            phi = 1.20 * float(np.mean(lam1[h, k:min(k + 300, K)])) \
                * T.E_VEH_KWH * T.ETA_CHG
            nl_h = (d["netload"] if netload_fc is None else netload_fc)[h]
            r = opt.hub_mpc(h, k, Np, av, edrv, deps, soc, bess,
                            lam1[h], pmax1[h], nl_h, phi=phi,
                            n_apply=na, env_on_net=env_on_net)
            nj = r["pchg"].shape[1]
            Pchg[h, :, k:k + nj] = r["pchg"]
            if h == hD:
                Pb[0, k:k + nj] = r["bc"]; Pb[1, k:k + nj] = r["bd"]
            if r["t"] > 0:
                tsolve.append(r["t"])
        # advance state over the applied control interval
        steps = 1 if mode == "dumb" else na
        for j in range(steps):
            kk = k + j
            tot = Pchg[:, :, kk].sum(0)
            soc = soc + (T.ETA_CHG * tot * S.DT_LL - edrv[:, kk]) / T.E_VEH_KWH
            soc = np.clip(soc, T.SOC_MIN - 1e-6, T.SOC_MAX + 1e-6)
            bess = bess + (0.96 * Pb[0, kk] - Pb[1, kk] / 0.96) * S.DT_LL / max(S.HUBS[hD].bess_kwh, 1)
            socs[:, kk + 1] = soc; bs[kk + 1] = bess
        k += steps
        if verbose and k % 240 == 0:
            print(f"    t={k//60:02d}:00  solves={len(tsolve)}", flush=True)
    return dict(Pchg=Pchg, Pbess=Pb, soc=socs, bess=bs,
                tsolve=np.array(tsolve), ul_ticks=ul_ticks, ul_time=ul_time,
                pmax1=pmax1, env_on_net=env_on_net)


# ------------------------------------------------------------ evaluation ---
def evaluate(d, sim, label):
    H, K = len(S.HUBS), S.K_DAY
    exo, f = d["exo"], d["feeder"]
    ctrl = sim["Pchg"].sum(1) + 0.0
    hD = S.HUB_IDX["D"]
    ctrl[hD] += sim["Pbess"][0] - sim["Pbess"][1]
    P = exo["P_feeder"].copy(); Q = exo["Q_feeder"].copy()
    for h in range(H):
        P[S.HUBS[h].bus - 1] += ctrl[h]
    pf = f.solve(P, Q)
    Vm, loss, Ssub = pf["Vm"], pf["loss_kw"], pf["Ssub_kva"]
    load_pu = pf["Sbr_kva"] / (f.smax[:, None] * S.S_BASE_KVA)
    price = exo["price"]
    # departure feasibility on the realised trajectory
    defs = []
    for (b, h, dm, ereq) in d["deps"]:
        need = ereq / T.E_VEH_KWH + T.SOC_MIN
        defs.append(max(0.0, need - sim["soc"][b, dm]))
    defs = np.array(defs)
    hub_import = d["netload"] + ctrl
    # did the hubs actually respect the dispatched envelope?
    pm1 = sim.get("pmax1")
    if pm1 is not None:
        lhs = hub_import if sim.get("env_on_net") else ctrl
        exc = np.maximum(lhs - pm1, 0.0)
    else:
        exc = np.zeros((1, 1))
    r = dict(
        case=label,
        V_min=float(Vm.min()),
        V_min_bus=int(Vm.min(1).argmin() + 1),
        undervolt_bus_min=int((Vm < S.V_MIN - 1e-6).sum()),
        undervolt_minutes=int(((Vm < S.V_MIN - 1e-6).any(0)).sum()),
        V_dev_rms=float(np.sqrt(((Vm - 1.0) ** 2).mean())),
        loss_MWh=float(loss.sum() / 60 / 1000),
        loss_peak_kW=float(loss.max()),
        Ssub_peak_kVA=float(Ssub.max()),
        Psub_peak_kW=float(pf["Psub_kw"].max()),
        sub_overload_min=int((Ssub > S.SUB_MVA * 1000).sum()),
        branch_max_loading=float(load_pu.max()),
        branch_overload_bus_min=int((load_pu > 1.0).sum()),
        charge_energy_MWh=float(sim["Pchg"].sum() / 60 / 1000),
        bess_throughput_MWh=float(sim["Pbess"].sum() / 60 / 1000),
        substation_energy_MWh=float(pf["Psub_kw"].sum() / 60 / 1000),
        energy_cost=float((price * pf["Psub_kw"]).sum() * S.DT_LL),
        charging_cost=float((price * ctrl.sum(0)).sum() * S.DT_LL),
        hub_peak_kW=[float(x) for x in hub_import.max(1)],
        deficit_events=int((defs > 1e-4).sum()),
        deficit_kWh=float(defs.sum() * T.E_VEH_KWH),
        soc_min=float(sim["soc"].min()),
        soc_end_mean=float(sim["soc"][:, -1].mean()),
        soc_gap_kWh=float(max(0.0, (T.SOC_START - sim["soc"][:, -1]).sum())
                          * T.E_VEH_KWH),
        pv_used_MWh=float(exo["pv_hub"].sum() / 60 / 1000),
        cost_adjusted=float((price * pf["Psub_kw"]).sum() * S.DT_LL
                            + max(0.0, (T.SOC_START - sim["soc"][:, -1]).sum())
                            * T.E_VEH_KWH / T.ETA_CHG * float(price.mean())),
        env_excess_max_kW=float(exc.max()),
        env_excess_kWh=float(exc.sum() / 60.0),
        env_breach_min=int((exc.max(0) > 1.0).sum()),
        n_solves=int(len(sim["tsolve"])),
        t_mean_ms=float(sim["tsolve"].mean() * 1000) if len(sim["tsolve"]) else 0.0,
        t_max_ms=float(sim["tsolve"].max() * 1000) if len(sim["tsolve"]) else 0.0,
        t_total_s=float(sim["tsolve"].sum()) if len(sim["tsolve"]) else 0.0,
    )
    r["_series"] = dict(Vmin_t=Vm.min(0), Ssub=Ssub, loss=loss,
                        ctrl=ctrl, hub_import=hub_import,
                        soc=sim["soc"], Vm_bus_min=Vm.min(1))
    return r


# ------------------------------------------------------------------ main ---
import pickle, os


def stage_admm(vmin_ul=None, tag=""):
    d = setup()
    print(f"route leg {d['leg_kwh']:.2f} kWh / {d['leg_km']:.2f} km "
          f"({d['leg_kwh']/d['leg_km']:.2f} kWh/km), cycle {d['cycle']} min", flush=True)
    a = admm(d, rho=1.2e-2, iters=15, tol_p=25.0, vmin_ul=vmin_ul)
    pmax15, margin = envelope(d, a["P"], a["u"], a["flow"], vmin=vmin_ul)
    print(f"envelope: mean margin {margin.mean():.0f} kW, min {margin.min():.0f} kW, "
          f"binding(<1kW) {(margin < 1).sum()} of {margin.size}", flush=True)
    pickle.dump(dict(hist=a["hist"], lam=a["lam"], P=a["P"], F=a["F"],
                     pmax=pmax15, margin=margin, eps=a["eps"],
                     t_ul=a["t_ul"], t_fleet=a["t_fleet"],
                     obj_ul=a["obj_ul"], obj_fleet=a["obj_fleet"]),
                open(f"admm{tag}.pkl", "wb"))


def stage_coord(band=None, tag="", fseed=None):
    """True-QP ADMM coordination followed by the jointly-certified envelope.

    With `fseed` set, the coordination layer plans on a perturbed forecast of
    PV, site load and feeder base load, while the envelope it dispatches is
    later executed against the true realisation. This is the experiment that
    actually tests Sec. 3.5: the hub MPC is insensitive to site-forecast error
    by construction (its envelope and price are both stated on controllable
    power), so the exposure lives entirely in the upper level.
    """
    d = setup()
    if fseed is not None:
        d = perturb_forecast(d, int(fseed))
    print(f"route leg {d['leg_kwh']:.2f} kWh / {d['leg_km']:.2f} km "
          f"({d['leg_kwh']/d['leg_km']:.2f} kWh/km), cycle {d['cycle']} min",
          flush=True)
    a = coord.admm_qp(d, rho=1.2e-2, iters=60, eps_abs=0.02)
    vm = S.V_MIN if band is None else band
    pmax, RP, RM = coord.envelope_joint(d, a["P"], a["u"], a["flow"],
                                        vmin=vm, verbose=True)
    chk = coord.verify_envelope(d, pmax, vmin=S.V_MIN)
    print(f"  corner certificate vs 0.95 p.u.: {chk['v_ok']} "
          f"(worst {chk['v_worst']:.4f}), thermal {chk['s_ok']}, "
          f"substation {chk['sub_ok']}", flush=True)
    out = dict(hist=a["hist"], lam=a["lam"], P=a["P"], F=a["F"], pmax=pmax,
               margin=RP, margin_dn=RM, eps=a["eps"], t_ul=a["t_ul"],
               t_fleet=a["t_fleet"], obj_ul=a["obj_ul"],
               obj_fleet=a["obj_fleet"], rho=a["rho"], check=chk, band=vm,
               netload15=d["netload15"], curt=a.get("curt"))
    pickle.dump(out, open(f"admm{tag}.pkl", "wb"))


def stage_env_sb(vmin=0.963):
    """Recompute the dispatched envelope from the converged upper-level
    solution against a de-rated voltage floor (Sec. 3.5-ii security band).
    LinDistFlow neglects losses and therefore under-predicts voltage drop;
    the band absorbs that model error plus intra-interval variation."""
    d = setup()
    a = pickle.load(open("admm.pkl", "rb"))
    P = a["P"] / S.S_BASE_KVA
    u = d["net"].u0 - d["net"].Mu @ P
    flow = d["net"].Pb + d["net"].G @ P
    pmax, margin = envelope(d, a["P"], u, flow, vmin=vmin)
    print(f"security band vmin={vmin}: mean margin {margin.mean():.0f} kW "
          f"(was {a['margin'].mean():.0f}), binding {(margin < 1).sum()} of "
          f"{margin.size}", flush=True)
    b = dict(a); b["pmax"] = pmax; b["margin"] = margin
    pickle.dump(b, open("admm_sb.pkl", "wb"))


def perturb_forecast(d, seed, pv_std=0.10, load_std=0.02, feeder_std=0.05,
                     clip=0.30):
    """Return a copy of the scenario in which every quantity the upper level
    forecasts is perturbed. The true series stay in `d["exo_true"]`."""
    import copy
    rng = np.random.default_rng(seed)
    K, H = S.K_DAY, len(S.HUBS)
    kern = np.exp(-0.5 * (np.arange(-45, 46) / 18.0) ** 2); kern /= kern.sum()

    def err(shape, std):
        e = np.stack([np.convolve(rng.normal(0, 1, K), kern, mode="same")
                      for _ in range(shape)])
        return np.clip(e / max(e.std(), 1e-9) * std, -clip, clip)

    d2 = dict(d)
    exo = {k: (v.copy() if hasattr(v, "copy") else v)
           for k, v in d["exo"].items()}
    pv_e, ld_e = err(H, pv_std), err(H, load_std)
    fd_e = err(1, feeder_std)[0]
    pv_f = np.clip(exo["pv_hub"] * (1 + pv_e), 0.0, None)
    ld_f = np.clip(exo["load_hub"] * (1 + ld_e), 0.0, None)
    dP = (ld_f - exo["load_hub"]) - (pv_f - exo["pv_hub"])
    P = exo["P_feeder"].copy(); Q = exo["Q_feeder"].copy()
    for h in range(H):
        P[S.HUBS[h].bus - 1] += dP[h]
    for b in range(S.N_BUS):                       # feeder-wide load forecast
        if b not in [S.HUBS[h].bus - 1 for h in range(H)]:
            P[b] *= (1 + fd_e); Q[b] *= (1 + fd_e)
    exo["pv_hub"], exo["load_hub"] = pv_f, ld_f
    exo["P_feeder"], exo["Q_feeder"] = P, Q
    d2["exo_true"] = d["exo"]
    d2["exo"] = exo
    d2["netload"] = ld_f - pv_f
    d2["netload15"] = d2["netload"].reshape(H, S.T_DAY, 15).mean(2)
    d2["net"] = opt.Network(d["feeder"], exo)
    return d2


def inflate_forecast(dp, d_true, z_sigma):
    """Sec. 3.5-ii applied where the residual risk actually is.

    The security band on the voltage floor cannot absorb forecast error,
    because the error enters through load the hubs do not control. The
    correct place for the margin is the forecast itself: plan against feeder
    and site load inflated by z*sigma, so the dispatched envelope is secure
    for the upper tail of the load distribution rather than for its mean.
    """
    import copy
    H = len(S.HUBS)
    dp2 = dict(dp)
    exo = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in dp["exo"].items()}
    exo["load_hub"] = exo["load_hub"] * (1 + z_sigma)
    exo["pv_hub"] = exo["pv_hub"] * (1 - z_sigma)        # PV under-delivers
    P = exo["P_feeder"].copy(); Q = exo["Q_feeder"].copy()
    hub_buses = [S.HUBS[h].bus - 1 for h in range(H)]
    for b in range(S.N_BUS):
        if b not in hub_buses:
            P[b] *= (1 + z_sigma); Q[b] *= (1 + z_sigma)
    for h in range(H):
        b = S.HUBS[h].bus - 1
        P[b] = (P[b] - dp["netload"][h]) * (1 + z_sigma) \
            + (exo["load_hub"][h] - exo["pv_hub"][h])
    exo["P_feeder"], exo["Q_feeder"] = P, Q
    dp2["exo"] = exo
    dp2["netload"] = exo["load_hub"] - exo["pv_hub"]
    dp2["netload15"] = dp2["netload"].reshape(H, S.T_DAY, 15).mean(2)
    dp2["net"] = opt.Network(dp["feeder"], exo)
    return dp2


def _store(label, r):
    fn = "cases.pkl"
    cur = pickle.load(open(fn, "rb")) if os.path.exists(fn) else {}
    cur[label] = r
    pickle.dump(cur, open(fn, "wb"))


def stage_case(which):
    d = setup()
    a = pickle.load(open("admm.pkl", "rb"))
    label, kw = {
        "C0": ("C0  Uncoordinated", dict(mode="dumb")),
        "C1": ("C1  Local MPC (TOU, site cap)", dict(mode="local")),
        "C2": ("C2  Hierarchical bi-level", dict(mode="hier", pmax15=a["pmax"],
                                                 lam15=a["lam"])),
        "C2b": ("C2b Hierarchical + security band", dict(mode="hier")),
        "C2c": ("C2c Hierarchical, net-import envelope",
                dict(mode="hier", env_on_net=True)),
        "C2d": ("C2d Rolling upper level, net-import envelope",
                dict(mode="roll", env_on_net=True)),
        "C2e": ("C2e Rolling + AC-corrected LinDistFlow",
                dict(mode="roll", env_on_net=True, ac_correct=True)),
    }[which]
    if which == "C2b":
        a = pickle.load(open("admm_sb.pkl", "rb"))
        kw.update(pmax15=a["pmax"], lam15=a["lam"])
    if which in ("C2d", "C2e"):
        # the plant is the true scenario; the coordination layer plans on the
        # (possibly perturbed) forecast scenario
        dp = perturb_forecast(d, int(fs)) if (
            fs := os.environ.get("FORECAST_SEED")) else d
        fm = float(os.environ.get("FEEDER_MARGIN", 0.0))
        if fm > 0:
            dp = inflate_forecast(dp, d, fm)
        kw["d_plan"] = dp
        kw["band"] = float(os.environ.get("BAND", 0.955))
        kw["tick_min"] = int(os.environ.get("UL_TICK", 60))
    if which == "C2c":
        a = pickle.load(open("admm_sb.pkl", "rb"))
        # envelope re-expressed on net PCC import, using the planning-time
        # forecast of site netload that the certificate was built on
        kw.update(pmax15=a["netload15"] + a["pmax"], lam15=a["lam"])
    print(f"== {label} ==", flush=True)
    ci = int(os.environ.get("CTRL_INT", 2))
    kw["ctrl_int"] = ci
    fseed = os.environ.get("FORECAST_SEED")
    if fseed is not None:
        # the plant realises the truth; only the envelope was built on forecast
        label = label + f" [fc seed {fseed}]"
    t0 = time.perf_counter()
    sim = simulate(d, **kw)
    r = evaluate(d, sim, label)
    r["ul_ticks"] = sim.get("ul_ticks", 0)
    r["ul_time"] = sim.get("ul_time", 0.0)
    r["wall_s"] = time.perf_counter() - t0
    print(f"  Vmin {r['V_min']:.4f} | undervolt {r['undervolt_minutes']} min "
          f"({r['undervolt_bus_min']} bus-min) | Ssub {r['Ssub_peak_kVA']:.0f} kVA | "
          f"loss {r['loss_MWh']:.3f} MWh | cost {r['energy_cost']:.0f} | "
          f"charge {r['charge_energy_MWh']:.2f} MWh | deficits {r['deficit_events']} "
          f"({r['deficit_kWh']:.1f} kWh) | wall {r['wall_s']:.0f} s", flush=True)
    _store(label, r)


def stage_bound():
    d = setup()
    a = pickle.load(open("admm.pkl", "rb"))
    ctrl = a["F"]
    P = d["exo"]["P_feeder"].reshape(S.N_BUS, S.T_DAY, 15).mean(2).copy()
    Q = d["exo"]["Q_feeder"].reshape(S.N_BUS, S.T_DAY, 15).mean(2).copy()
    for h in range(len(S.HUBS)):
        P[S.HUBS[h].bus - 1] += ctrl[h]
    pf = d["feeder"].solve(P, Q)
    pr15 = d["exo"]["price"].reshape(S.T_DAY, 15).mean(1)
    r = dict(case="C3  Centralised 15-min bound",
             V_min=float(pf["Vm"].min()),
             Ssub_peak_kVA=float(pf["Ssub_kva"].max()),
             loss_MWh=float(pf["loss_kw"].sum() * S.DT_UL / 1000),
             energy_cost=float((pr15 * pf["Psub_kw"]).sum() * S.DT_UL),
             charge_energy_MWh=float(ctrl.sum() * S.DT_UL / 1000),
             deficit_kWh=float(a["eps"].sum() * T.E_VEH_KWH),
             undervolt_minutes=int(((pf["Vm"] < S.V_MIN - 1e-6).any(0)).sum() * 15))
    print("C3 bound:", {k: round(v, 4) for k, v in r.items() if k != "case"}, flush=True)
    _store(r["case"], r)


def stage_pack():
    d = setup()
    a = pickle.load(open("admm.pkl", "rb"))
    cases = pickle.load(open("cases.pkl", "rb"))
    out = dict(cases); out["admm"] = a
    pickle.dump(dict(out=out, exo=d["exo"], netload=d["netload"]),
                open("results.pkl", "wb"))
    print("packed", list(out), flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "admm":
        stage_admm()
    elif cmd == "coord":
        stage_coord()
    elif cmd == "coord_sb":
        stage_coord(band=float(os.environ.get("BAND", 0.955)), tag="_sb",
                    fseed=os.environ.get("FORECAST_SEED"))
    elif cmd == "admm_sb":
        stage_env_sb()
    elif cmd == "bound":
        stage_bound()
    elif cmd == "pack":
        stage_pack()
    else:
        stage_case(cmd)
