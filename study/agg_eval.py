"""Score LAMBDA_total against the closed-loop runs, minute by minute.

For each simulated minute t and the bus m that binds:

    u_ac(m,t)  ~=  u_lin(m, P15(t))  -  D_agg(m,t)  -  D_err(m,t)

    u_lin(m,P15) is what the DOE allocation certified (>= v_plan^2),
    D_agg        is the first-order drop from the realised injections
                 deviating from the 15-minute planning vector (T3),
    D_err        is the loss term LinDistFlow omits (T2).

    LAMBDA_total(m,t) = (D_err + D_agg) / (u_lin(m,P15) - V_min^2)

and LAMBDA_total > 1 predicts u_ac < V_min^2. All violations are read off
the backward/forward AC sweep, never off the linear model.
"""
import glob, json, re, sys
import numpy as np
import criterion as CR

VMIN = 0.95
PAT = sys.argv[1] if len(sys.argv) > 1 else "agg_b*.npz"
OUT = sys.argv[2] if len(sys.argv) > 2 else "agg_rows.json"

rows = []
for fn in sorted(glob.glob(PAT)):
    z = np.load(fn, allow_pickle=True)
    bus, band = int(z["bus"]), float(z["band"])
    feeder = str(z["feeder"]) if "feeder" in z.files else "ieee33"
    n_veh = int(z["n_veh"]) if "n_veh" in z.files else 16
    P, Q, P15, Q15, Vm = z["P"], z["Q"], z["P15"], z["Q15"], z["Vm"]
    net = CR.ieee69() if feeder == "ieee69" else CR.ieee33()
    hb = z["hubbus"] - 1
    rho = float(net.R[hb[0], hb[2]] / net.R[hb[0], hb[0]])
    K = P.shape[1]
    uac = Vm ** 2
    # binding bus per minute, from the AC solution
    mm = uac.argmin(0)
    ulin15 = np.empty(K); dagg = np.empty(K); derr = np.empty(K)
    for t in range(K):
        m = int(mm[t])
        ulin15[t] = net.u_lin(p_kw=P15[:, t], q_kvar=Q15[:, t])[m]
        dagg[t] = CR.agg_drop(net, P[:, t] - P15[:, t], Q[:, t] - Q15[:, t])[m]
        derr[t] = net.loss_drop(p_kw=P[:, t], q_kvar=Q[:, t])[m]
    # attribution: which buses' intra-interval deviation drives D_agg?
    dP = P - P15
    dagg_hub = np.empty(K); dagg_exo = np.empty(K)
    for t in range(K):
        m = int(mm[t])
        mask = np.zeros(net.n, bool); mask[hb] = True
        dagg_hub[t] = 2.0 * net.R[m][mask] @ (dP[mask, t] / net.sb)
        dagg_exo[t] = dagg[t] - dagg_hub[t]
    ucert = ulin15 - VMIN ** 2
    lam_e = derr / np.maximum(ucert, 1e-9)
    lam_t = (derr + dagg) / np.maximum(ucert, 1e-9)
    viol = uac.min(0) < VMIN ** 2 - 1e-12
    recon = ulin15 - dagg - derr
    rows.append(dict(
        bus=bus, band=band, rho=rho, feeder=feeder, n_veh=n_veh,
        minutes=int(K), viol_min=int(viol.sum()),
        V_min=float(Vm.min()),
        depth=float(max(0.0, VMIN - Vm.min())),
        d_err_med=float(np.median(derr)), d_err_max=float(derr.max()),
        d_agg_med=float(np.median(dagg)), d_agg_max=float(dagg.max()),
        d_agg_p95=float(np.percentile(dagg, 95)),
        d_agg_hub_p95=float(np.percentile(dagg_hub, 95)),
        d_agg_exo_p95=float(np.percentile(dagg_exo, 95)),
        share_agg=float(np.median(dagg / np.maximum(dagg + derr, 1e-12))),
        recon_mae=float(np.abs(recon - uac.min(0)).mean()),
        recon_max=float(np.abs(recon - uac.min(0)).max()),
        # classification, per minute, LAMBDA vs LAMBDA_total
        tp_e=int((( lam_e > 1) &  viol).sum()), fp_e=int((( lam_e > 1) & ~viol).sum()),
        fn_e=int(((lam_e <= 1) &  viol).sum()), tn_e=int(((lam_e <= 1) & ~viol).sum()),
        # how deep are the violations LAMBDA_total misses?
        fn_depth_max=float((VMIN - np.sqrt(np.maximum(uac.min(0), 1e-9)))[viol & (lam_t <= 1)].max(initial=0.0)),
        fn_depth_med=float(np.median((VMIN - np.sqrt(np.maximum(uac.min(0), 1e-9)))[viol & (lam_t <= 1)])) if int((viol & (lam_t <= 1)).sum()) else 0.0,
        tp_depth_med=float(np.median((VMIN - np.sqrt(np.maximum(uac.min(0), 1e-9)))[viol & (lam_t > 1)])) if int((viol & (lam_t > 1)).sum()) else 0.0,
        lam_t_fn_med=float(np.median(lam_t[viol & (lam_t <= 1)])) if int((viol & (lam_t <= 1)).sum()) else 0.0,
        # the practical operating threshold, applied as-is
        tp_85=int((( lam_t > 0.85) &  viol).sum()), fp_85=int((( lam_t > 0.85) & ~viol).sum()),
        fn_85=int(((lam_t <= 0.85) &  viol).sum()), tn_85=int(((lam_t <= 0.85) & ~viol).sum()),
        tp_t=int((( lam_t > 1) &  viol).sum()), fp_t=int((( lam_t > 1) & ~viol).sum()),
        fn_t=int(((lam_t <= 1) &  viol).sum()), tn_t=int(((lam_t <= 1) & ~viol).sum()),
    ))
    r = rows[-1]
    print(f"{feeder} bus {bus:2d} rho {r['rho']:.3f} band {band:.3f}  uv {r['viol_min']:4d} min  "
          f"Vmin {r['V_min']:.4f}  D_err {r['d_err_med']:.5f}  D_agg med {r['d_agg_med']:.5f} "
          f"p95 {r['d_agg_p95']:.5f}  recon MAE {r['recon_mae']:.2e}  "
          f"L: {r['tp_e']}/{r['fn_e']}  Lt: {r['tp_t']}/{r['fn_t']}", flush=True)

json.dump(rows, open(OUT, "w"), indent=1)
print("wrote", OUT)
