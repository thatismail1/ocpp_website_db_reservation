"""Step 1-2: decompose what actually moves with rho on each feeder.

For every closed-loop placement already simulated, split Lambda_total into its
numerator pieces and its denominator, and split D_agg itself into "how much
drift" (gamma, in kW at the hub bus) and "how much weight" (the sensitivity
2 R_mC / S_b that turns that drift into a voltage drop). Also record the
structural descriptors of each placement so the correlation can be tested
WITHIN each feeder, not only between the two.

No new simulation: this reads the .npz dumps produced by agg_run.py.
"""
import glob, json, sys
import numpy as np
import criterion as CR

VMIN = 0.95
SETS = [("agg_b*.npz", "ieee33-fit"), ("hold_*.npz", "ieee33-hold"),
        ("i69_*.npz", "ieee69"), ("syn_*.npz", "synthetic")]


def descriptors(net, bus0):
    """Structural descriptors of a bus: path resistance, upstream branch
    count, subtree size (1 = lateral tip), and depth."""
    d, v, sub = 0, bus0, np.ones(net.n)
    for j in net.rev:
        if j != 0:
            sub[net.parent[j]] += sub[j]
    while v != 0:
        d += 1; v = net.parent[v]
    return dict(R_path=float(net.R[bus0, bus0]), n_up=d,
                subtree=int(sub[bus0]), is_tip=bool(sub[bus0] == 1))


def analyse(fn, tag):
    z = np.load(fn, allow_pickle=True)
    feeder = str(z["feeder"]) if "feeder" in z.files else "ieee33"
    if feeder == "ieee69":
        net = CR.ieee69()
    elif feeder.startswith("synth"):
        net = synth_net(feeder[len("synth"):])
    else:
        net = CR.ieee33()
    P, Q, P15, Q15, Vm = z["P"], z["Q"], z["P15"], z["Q15"], z["Vm"]
    hb = z["hubbus"] - 1
    A, C = int(hb[0]), int(hb[2])
    rho = float(net.R[A, C] / net.R[A, A])
    K = P.shape[1]
    uac = Vm ** 2
    mm = uac.argmin(0)
    dP = P - P15
    slack = np.empty(K); dagg = np.empty(K); derr = np.empty(K)
    dagg_C = np.empty(K); wC = np.empty(K)
    for t in range(K):
        m = int(mm[t])
        slack[t] = net.u_lin(p_kw=P15[:, t], q_kvar=Q15[:, t])[m] - VMIN ** 2
        dagg[t] = CR.agg_drop(net, dP[:, t], Q[:, t] - Q15[:, t])[m]
        derr[t] = net.loss_drop(p_kw=P[:, t], q_kvar=Q[:, t])[m]
        wC[t] = 2.0 * net.R[m, C] / net.sb
        dagg_C[t] = wC[t] * dP[C, t]
    mode_m = int(np.bincount(mm).argmax())
    # gamma: the raw intra-interval drift in kW, unweighted by topology
    gam_C = float(np.percentile(np.abs(dP[C]), 95))
    gam_A = float(np.percentile(np.abs(dP[A]), 95))
    gam_all = float(np.percentile(np.abs(dP).sum(0), 95))
    return dict(
        file=fn, set=tag, feeder=feeder, band=float(z["band"]), rho=rho,
        hub_A=A + 1, hub_C=C + 1, bind_bus=mode_m + 1,
        viol_min=int((uac.min(0) < VMIN ** 2 - 1e-12).sum()),
        slack_med=float(np.median(slack)), slack_p5=float(np.percentile(slack, 5)),
        d_agg_p95=float(np.percentile(dagg, 95)),
        d_aggC_p95=float(np.percentile(dagg_C, 95)),
        d_err_med=float(np.median(derr)),
        gamma_C_kw=gam_C, gamma_A_kw=gam_A, gamma_all_kw=gam_all,
        w_C=float(np.median(wC)), w_C_x_gamma=float(np.median(wC) * gam_C),
        **{f"C_{k}": v for k, v in descriptors(net, C).items()},
        **{f"A_{k}": v for k, v in descriptors(net, A).items()},
        **{f"m_{k}": v for k, v in descriptors(net, mode_m).items()},
    )


def synth_net(profile):
    """Rebuild the parametric feeder for a given resistance profile."""
    import importlib, system as S
    os_env = __import__("os").environ
    if profile:
        os_env["FEEDER"] = "synth"; os_env["SYN_PROFILE"] = profile
        os_env["FEEDER_LOAD"] = {"front": "0.4151", "back": "1.1500"}.get(profile, "0.60")
        importlib.reload(S)
    par, ch, bidx, r, x, order = S.feeder_topology()
    p = np.zeros(S.N_BUS); q = np.zeros(S.N_BUS)
    for b, (pp, qq) in S.LOAD.items():
        p[b - 1] = pp; q[b - 1] = qq
    rr = np.array([r[bidx[j]] for j in range(1, S.N_BUS)])
    xx = np.array([x[bidx[j]] for j in range(1, S.N_BUS)])
    parent = np.array([max(par[j], 0) for j in range(S.N_BUS)])
    return CR.RadialNet(parent, rr, xx, p, q)


if __name__ == "__main__":
    rows = []
    for pat, tag in SETS:
        for fn in sorted(glob.glob(pat)):
            rows.append(analyse(fn, tag))
    json.dump(rows, open("mech_rows.json", "w"), indent=1)
    print("rows:", len(rows))
