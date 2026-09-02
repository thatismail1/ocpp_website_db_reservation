"""Coordination layer as true convex QPs (C-2..C-4).

Replaces the piecewise-linear proximal of the first implementation. Because a
QP backend is available, three things become exact rather than approximated:
the LinDistFlow loss term, the voltage-deviation penalty, and the ADMM
proximal term itself. The primal residual therefore converges instead of
floating on a linearisation floor.
"""
from __future__ import annotations
import numpy as np, time
import cvxpy as cp
import system as S, transit as T

QP_SOLVER = cp.CLARABEL


# ------------------------------------------------------------ upper level ---
class UpperLevel:
    """LinDistFlow feeder dispatch, parameterised so the ADMM target and the
    penalty can be updated without rebuilding the problem."""

    def __init__(self, net, price, netload, cap, w_loss=0.9, w_v=6.0,
                 vmin=None, rho=0.0, pv=None, w_curt=0.5):
        H, Tn = len(S.HUBS), S.T_DAY
        self.net, self.H, self.Tn = net, H, Tn
        vmin = S.V_MIN if vmin is None else vmin
        self.P = cp.Variable((H, Tn), name="Pctrl")            # p.u.
        self.target = cp.Parameter((H, Tn), value=np.zeros((H, Tn)))
        self.rho = rho
        sb0 = S.S_BASE_KVA
        # LL-9 / UL: curtailing PV raises the hub's net injection, which is how
        # the feeder defends its reverse-flow limit at high PV penetration
        self.curt = cp.Variable((H, Tn), nonneg=True)
        pv = np.zeros((H, Tn)) if pv is None else pv
        NET = self.P + self.curt / sb0

        U = net.u0 - net.Mu @ NET                               # (33,T)
        FLOW = net.Pb + net.G @ NET                             # (32,T)
        pr = price.reshape(Tn, 15).mean(1)
        sb = S.S_BASE_KVA

        lim = np.sqrt(np.maximum(net.smax[:, None] ** 2 - net.Qb ** 2, 1e-9))
        lo = np.array([[-S.HUBS[h].bess_kw / sb] * Tn for h in range(H)])
        hi = np.maximum(cap, 0.0) / sb
        cons = [U >= vmin ** 2, U <= S.V_MAX ** 2,
                FLOW <= lim, FLOW >= -lim,
                self.P >= lo, self.P <= hi,
                self.curt <= pv,
                netload / sb + NET <= np.array(
                    [[S.HUBS[h].p_pcc_kw / sb] * Tn for h in range(H)]),
                FLOW[0] <= S.SUB_MVA * 1000.0 / sb * 0.93,
                FLOW[0] >= -S.REV_LIMIT_KW / sb]

        obj = pr @ FLOW[0] * sb * S.DT_UL
        obj += w_loss * cp.sum(cp.multiply(
            net.f.r[:, None] / S.V_REF ** 2,
            cp.square(FLOW) + net.Qb ** 2)) * sb * S.DT_UL      # exact loss
        obj += w_v * cp.sum_squares(U - 1.0)                    # exact deviation
        obj += w_curt * cp.sum(self.curt) * S.DT_UL             # LL-10 curtailment
        if rho > 0:
            obj += (rho / 2) * cp.sum_squares(self.P * sb - self.target)
        self.prob = cp.Problem(cp.Minimize(obj), cons)

    def solve(self, target_kw=None):
        if target_kw is not None:
            self.target.value = target_kw
        t0 = time.perf_counter()
        self.prob.solve(solver=QP_SOLVER, warm_start=True)
        dt = time.perf_counter() - t0
        if self.P.value is None:
            raise RuntimeError(f"upper level {self.prob.status}")
        P = self.P.value * S.S_BASE_KVA
        self.curt_kw = self.curt.value
        net_pu = (P + self.curt_kw) / S.S_BASE_KVA
        u = self.net.u0 - self.net.Mu @ net_pu
        flow = self.net.Pb + self.net.G @ net_pu
        return P, u, flow, dt, float(self.prob.value)


# ------------------------------------------------------------ fleet block ---
class FleetBlock:
    """Transit-side block: per-vehicle SoC over the circulating timetable.

    The four hubs are NOT independent here: a vehicle charged at terminal A
    arrives at interchange C with that state, so the hub subproblems couple
    through vehicle SoC and are solved as one block at the planning stage.
    """

    def __init__(self, av15, edrv15, deps, w_deg=0.012, w_eps=3000.0,
                 cap_ctrl=None, rho=0.0):
        H, Tn, NV = len(S.HUBS), S.T_DAY, T.N_VEH
        self.H, self.Tn = H, Tn
        self.pc = [cp.Variable((NV, Tn), nonneg=True) for _ in range(H)]
        self.soc = cp.Variable((NV, Tn + 1))
        self.ctrl = cp.Variable((H, Tn))
        self.eps = cp.Variable(len(deps), nonneg=True)
        self.target = cp.Parameter((H, Tn), value=np.zeros((H, Tn)))
        hD = S.HUB_IDX["D"]
        self.bc = cp.Variable(Tn, nonneg=True)
        self.bd = cp.Variable(Tn, nonneg=True)
        self.bs = cp.Variable(Tn + 1)

        cons = [self.soc >= T.SOC_MIN, self.soc <= T.SOC_MAX,
                self.soc[:, 0] == T.SOC_START,
                self.soc[:, Tn] >= T.SOC_START,          # day-neutral
                self.eps <= 0.6,
                self.bc <= S.HUBS[hD].bess_kw, self.bd <= S.HUBS[hD].bess_kw,
                self.bs >= 0.15, self.bs <= 0.9,
                self.bs[0] == 0.5, self.bs[Tn] >= 0.5]
        for h in range(H):
            cons += [self.pc[h] <= av15[h] * S.HUBS[h].p_bay_kw,
                     cp.sum(self.pc[h], axis=0)
                     <= S.HUBS[h].n_bays * S.HUBS[h].p_bay_kw]
        CH = sum(self.pc)                                       # (NV,T)
        cons += [self.soc[:, 1:] == self.soc[:, :-1]
                 + (T.ETA_CHG * CH * S.DT_UL - edrv15) / T.E_VEH_KWH]
        cons += [self.bs[1:] == self.bs[:-1]
                 + (0.96 * self.bc - self.bd / 0.96) * S.DT_UL
                 / S.HUBS[hD].bess_kwh]
        for h in range(H):
            extra = (self.bc - self.bd) if h == hD else 0.0
            cons += [self.ctrl[h] == cp.sum(self.pc[h], axis=0) + extra]
        if cap_ctrl is not None:
            cons += [self.ctrl <= cap_ctrl]
        for k, (b, h, dm, ereq) in enumerate(deps):
            t = min(dm // 15, Tn)
            cons += [self.soc[b, t] + self.eps[k]
                     >= ereq / T.E_VEH_KWH + T.SOC_MIN]

        obj = w_deg * cp.sum(self.bc + self.bd) * S.DT_UL
        obj += 0.25 * w_deg * sum(cp.sum(p) for p in self.pc) * S.DT_UL
        obj += w_eps * cp.sum(self.eps)
        if rho > 0:
            obj += (rho / 2) * cp.sum_squares(self.ctrl - self.target)
        self.prob = cp.Problem(cp.Minimize(obj), cons)

    def solve(self, target_kw=None):
        if target_kw is not None:
            self.target.value = target_kw
        t0 = time.perf_counter()
        self.prob.solve(solver=QP_SOLVER, warm_start=True)
        dt = time.perf_counter() - t0
        if self.ctrl.value is None:
            raise RuntimeError(f"fleet block {self.prob.status}")
        return (self.ctrl.value, self.soc.value, self.eps.value, dt,
                float(self.prob.value))


# ------------------------------------------------------------------ ADMM ---
def admm_qp(d, rho=1.2e-2, iters=60, eps_abs=0.5, eps_rel=1e-3,
            vmin=None, balance=True, verbose=True):
    """Scaled ADMM between the feeder block and the fleet block (C-2..C-4)."""
    H, Tn = len(S.HUBS), S.T_DAY
    pv15 = d["exo"]["pv_hub"].reshape(len(S.HUBS), Tn, 15).mean(2)
    ul = UpperLevel(d["net"], d["exo"]["price"], d["netload15"], d["cap15"],
                    vmin=vmin, rho=rho, pv=pv15)
    fb = FleetBlock(d["av15"], d["edrv15"], d["deps"], cap_ctrl=d["cap15"],
                    rho=rho)
    P = np.zeros((H, Tn)); F = np.zeros((H, Tn)); U = np.zeros((H, Tn))
    hist, tul, tfl = [], 0.0, 0.0
    u = flow = None
    for it in range(iters):
        P, u, flow, t1, oul = ul.solve(F - U)
        Fp = F.copy()
        F, soc, eps, t2, ofl = fb.solve(P + U)
        r = P - F                       # primal residual
        s = rho * (F - Fp)              # dual residual
        U = U + r
        rn, sn = np.linalg.norm(r), np.linalg.norm(s)
        tul += t1; tfl += t2
        hist.append(dict(it=it + 1, primal=float(rn), dual=float(sn),
                         obj_ul=float(oul), obj_fleet=float(ofl),
                         eps=float(eps.sum())))
        if verbose:
            print(f"  ADMM {it+1:3d}  ||r||={rn:9.3f} kW  ||s||={sn:9.4f}  "
                  f"f_UL={oul:11.1f}  f_F={ofl:9.1f}", flush=True)
        tol_p = np.sqrt(H * Tn) * eps_abs + eps_rel * max(
            np.linalg.norm(P), np.linalg.norm(F))
        if rn < tol_p and sn < tol_p:
            break
        if balance and it > 2:
            if rn > 10 * sn:
                rho *= 2; U /= 2
                ul = UpperLevel(d["net"], d["exo"]["price"], d["netload15"],
                                d["cap15"], vmin=vmin, rho=rho, pv=pv15)
                fb = FleetBlock(d["av15"], d["edrv15"], d["deps"],
                                cap_ctrl=d["cap15"], rho=rho)
            elif sn > 10 * rn:
                rho /= 2; U *= 2
                ul = UpperLevel(d["net"], d["exo"]["price"], d["netload15"],
                                d["cap15"], vmin=vmin, rho=rho, pv=pv15)
                fb = FleetBlock(d["av15"], d["edrv15"], d["deps"],
                                cap_ctrl=d["cap15"], rho=rho)
    lam = -rho * U / S.DT_UL
    return dict(P=P, F=F, lam=lam, hist=hist, u=u, flow=flow, soc15=soc,
                curt=getattr(ul, "curt_kw", np.zeros((H, Tn))),
                eps=eps, t_ul=tul, t_fleet=tfl, rho=rho,
                obj_ul=oul, obj_fleet=ofl)


# ------------------------------------------------- jointly-certified envelope
def envelope_joint(d, P, u, flow, vmin=None, weights=None, verbose=False):
    """UL-9 with a *joint* security certificate.

    The one-at-a-time sensitivity walk of UL-9a holds every other hub at its
    dispatch, so simultaneous excursions are not certified. Under LinDistFlow
    all network constraints are monotone in hub power (the sensitivity matrix
    2R and the subtree incidence G are non-negative), so the worst case over
    the box [P - rho_minus, P + rho_plus] occurs at a corner. Certifying the
    two corners therefore certifies the whole box, and the largest such box is
    the solution of a small LP per interval:

        max  sum_h w_h^+ rho_h^+ + w_h^- rho_h^-
        s.t. u_i - sum_h Mu[i,h] rho_h^+ >= vmin^2          (all hubs up)
             u_i + sum_h Mu[i,h] rho_h^- <= vmax^2          (all hubs down)
             flow_b + sum_h G[b,h] rho_h^+ <= lim_b
             flow_b - sum_h G[b,h] rho_h^- >= -lim_b
             substation import / reverse-flow limits
             0 <= rho^+ <= headroom to the PCC rating
             0 <= rho^- <= dispatched power plus BESS discharge

    Any hub may then move anywhere inside its envelope, independently and
    without further communication, and the feeder stays secure.
    """
    net = d["net"]
    H, Tn = len(S.HUBS), S.T_DAY
    vmin = S.V_MIN if vmin is None else vmin
    sb = S.S_BASE_KVA
    if weights is None:                      # share headroom by hub rating
        w = np.array([h.n_bays * h.p_bay_kw for h in S.HUBS], float)
        w = w / w.sum()
    else:
        w = np.asarray(weights, float)

    Mu, G = net.Mu, net.G                    # (33,H) >= 0 , (32,H) in {0,1}
    lim = np.sqrt(np.maximum(net.smax[:, None] ** 2 - net.Qb ** 2, 1e-9))
    sub_hi = S.SUB_MVA * 1000.0 / sb * 0.93
    sub_lo = -S.REV_LIMIT_KW / sb

    rp = cp.Variable(H, nonneg=True)
    rm = cp.Variable(H, nonneg=True)
    p_u = cp.Parameter(S.N_BUS)
    p_f = cp.Parameter(len(S.BRANCH))
    p_lim = cp.Parameter(len(S.BRANCH), nonneg=True)
    p_hi = cp.Parameter(H, nonneg=True)
    p_lo = cp.Parameter(H, nonneg=True)
    cons = [p_u - Mu @ rp >= vmin ** 2,
            p_u + Mu @ rm <= S.V_MAX ** 2,
            p_f + G @ rp <= p_lim,
            p_f - G @ rm >= -p_lim,
            p_f[0] + G[0] @ rp <= sub_hi,
            p_f[0] - G[0] @ rm >= sub_lo,
            rp <= p_hi, rm <= p_lo]
    prob = cp.Problem(cp.Maximize(w @ rp + 0.35 * (w @ rm)), cons)

    RP = np.zeros((H, Tn)); RM = np.zeros((H, Tn))
    t0 = time.perf_counter()
    for t in range(Tn):
        p_u.value = u[:, t]
        p_f.value = flow[:, t]
        p_lim.value = lim[:, t]
        p_hi.value = np.maximum(
            [(S.HUBS[h].p_pcc_kw - d["netload15"][h, t]) / sb - P[h, t] / sb
             for h in range(H)], 0.0)
        p_lo.value = np.maximum(
            [P[h, t] / sb + S.HUBS[h].bess_kw / sb for h in range(H)], 0.0)
        try:
            prob.solve(solver=cp.CLARABEL, warm_start=True)
        except Exception:
            continue
        if rp.value is None or prob.status not in ("optimal",
                                                   "optimal_inaccurate"):
            continue      # band tighter than the dispatch: no headroom granted
        RP[:, t] = np.maximum(rp.value, 0.0)
        RM[:, t] = np.maximum(rm.value, 0.0)
    RP *= sb; RM *= sb
    pmax = P + RP
    for h in range(H):
        pmax[h] = np.minimum(pmax[h], S.HUBS[h].p_pcc_kw - d["netload15"][h])
    if verbose:
        print(f"  joint envelope: {time.perf_counter()-t0:.1f} s, "
              f"mean up-margin {RP.mean():.0f} kW, min {RP.min():.0f} kW",
              flush=True)
    return np.maximum(pmax, 0.0), RP, RM


def verify_envelope(d, pmax, vmin=None):
    """Independent check: push every hub to its envelope corner at once and
    confirm the LinDistFlow network model stays inside its limits."""
    net = d["net"]
    vmin = S.V_MIN if vmin is None else vmin
    Pc = pmax / S.S_BASE_KVA
    u = net.u0 - net.Mu @ Pc
    fl = net.Pb + net.G @ Pc
    lim = np.sqrt(np.maximum(net.smax[:, None] ** 2 - net.Qb ** 2, 1e-9))
    return dict(v_ok=bool((u >= vmin ** 2 - 1e-7).all()),
                v_worst=float(np.sqrt(u.min())),
                s_ok=bool((fl <= lim + 1e-7).all()),
                sub_ok=bool((fl[0] <= S.SUB_MVA * 1000 / S.S_BASE_KVA * 0.93
                             + 1e-7).all()))
