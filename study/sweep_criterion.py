"""Validation of the envelope-failure criterion.

DERIVATION SET : synthetic radial topologies (criterion.random_radial).
TEST SET       : the IEEE 33-bus feeder, real published impedances, held out.

No threshold is fitted on the test set. The criterion's threshold is LAMBDA=1,
which comes from the derivation (neglected drop exceeds the planning band) and
is not tuned at all; the ROC on the derivation set is reported to show where an
empirically optimal threshold would sit, but the prediction reported on IEEE-33
uses LAMBDA=1 exactly.
"""
import os, sys, json, time
import numpy as np
import criterion as CR

V_MIN = 0.95
RHOS = [0.12, 0.30, 0.50, 0.70, 0.88]
MARGINS = [0.9560, 0.9650, 0.9750]      # base-case AC minimum voltage
BANDS = [0.000, 0.005, 0.010]           # v_plan = V_MIN + band
CAPS = 900.0


def one(net, hubs, vplan, tag, extra):
    rows = []
    for mode, alloc in (("joint", CR.allocate_doe), ("naive", CR.naive_doe)):
        P = alloc(net, list(hubs), vplan, [CAPS] * len(hubs))
        if P is None:
            continue
        r = CR.corner_test(net, list(hubs), P, V_MIN)
        lam = CR.lambda_index(net, list(hubs), P, V_MIN, vplan) if vplan > V_MIN \
            else (np.inf if r["viol"] > 0 else CR.lambda_index(
                net, list(hubs), P, V_MIN, V_MIN + 1e-4))
        rows.append(dict(set=tag, mode=mode, lam=float(lam),
                         viol=r["viol"], v_ac=r["v_ac"], lin_err=r["lin_err"],
                         P=[float(z) for z in P], **extra))
    return rows


def derivation_set(n_top=20):
    out = []
    t0 = time.perf_counter()
    for seed in range(1, n_top + 1):
        net0 = CR.random_radial(seed)
        for rho_t in RHOS:
            hp, err = CR.pick_hub_pair(net0, rho_t)
            if hp is None:
                continue
            for vb in MARGINS:
                net = CR.random_radial(seed)
                CR.scale_to_vmin(net, vb)
                rho = CR.coupling(net, *hp)
                for band in BANDS:
                    out += one(net, hp, V_MIN + band, "synthetic",
                               dict(seed=seed, rho=rho, v_base=vb, band=band,
                                    margin=vb ** 2 - V_MIN ** 2))
        print(f"  seed {seed:2d}: {len(out)} rows  [{time.perf_counter()-t0:.0f}s]",
              flush=True)
    return out


def test_set(tag="ieee33"):
    """Published feeders, real impedances, held out from the derivation set.

    ieee33 : the project's own branch table (Baran & Wu 1989, 33-bus).
    ieee69 : MATPOWER data/case69.m, whose header cites Baran & Wu 1989,
             "Optimal capacitor placement on radial distribution systems",
             IEEE Trans. Power Delivery 4(1):725-734. Parsed from the file,
             not reconstructed. Base case reproduces the published minimum
             voltage 0.9092 p.u. at bus 65 with a 1.0 p.u. slack.
    """
    mk = CR.ieee33 if tag == "ieee33" else CR.ieee69
    base = mk()
    out, pairs = [], []
    for rho_t in RHOS:
        hp, err = CR.pick_hub_pair(base, rho_t)
        if hp is not None:
            pairs.append((hp, CR.coupling(base, *hp)))
    for hp, rho in pairs:
        for vb in MARGINS:
            net = mk()
            CR.scale_to_vmin(net, vb)
            for band in BANDS:
                out += one(net, hp, V_MIN + band, tag,
                           dict(seed=0, rho=rho, v_base=vb, band=band,
                                margin=vb ** 2 - V_MIN ** 2))
    return out


def nhub_set():
    """N-hub check on the project's own 4-hub feeder (buses 18, 33, 22, 25),
    plus H = 2..5 on IEEE-69, verifying (i) the exact quadratic form of T2
    against loss_drop, (ii) corner certification at N hubs against the AC
    solver, and (iii) LAMBDA at N hubs."""
    import numpy as np
    rows = []
    cases = [("ieee33-4hub", CR.ieee33, [17, 32, 21, 24]),
             ("ieee69-2hub", CR.ieee69, [64, 26]),
             ("ieee69-3hub", CR.ieee69, [64, 26, 45]),
             ("ieee69-4hub", CR.ieee69, [64, 26, 45, 51]),
             ("ieee69-5hub", CR.ieee69, [64, 26, 45, 51, 34])]
    for tag, mk, hubs in cases:
        for vb in MARGINS:
            for band in BANDS:
                net = mk(); CR.scale_to_vmin(net, vb)
                vplan = V_MIN + band
                P = CR.allocate_doe(net, hubs, vplan, [CAPS] * len(hubs))
                if P is None:
                    continue
                r = CR.corner_test(net, hubs, P, V_MIN)
                pieces, D = CR.err_form(net, hubs)
                p = net.p.copy()
                for k, h in enumerate(hubs):
                    p[h] += P[k]
                m = int(np.argmin(net.u_lin(p_kw=p)))
                Cm, _, _ = pieces(m)
                form = D(m, P)
                exact = float(net.loss_drop(p_kw=p)[m])
                bandu = vplan ** 2 - V_MIN ** 2
                rows.append(dict(set=tag, H=len(hubs), v_base=vb, band=band,
                                 form=form, exact=exact,
                                 form_rel_err=abs(form - exact) / max(exact, 1e-12),
                                 minEig=float(np.linalg.eigvalsh(Cm).min()),
                                 lam=(form / bandu) if bandu > 1e-12 else float("inf"),
                                 viol=r["viol"], v_ac=r["v_ac"],
                                 P=[float(z) for z in P]))
    return rows


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = json.load(open("crit_rows.json")) if os.path.exists("crit_rows.json") else []
    if what in ("all", "deriv"):
        res += derivation_set(int(os.environ.get("NTOP", 20)))
    if what in ("all", "test"):
        res += test_set("ieee33")
        res += test_set("ieee69")
    if what == "nhub":
        import json as _j
        _j.dump(nhub_set(), open("crit_nhub.json", "w"), indent=1)
        print("nhub rows written"); raise SystemExit
    json.dump(res, open("crit_rows.json", "w"))
    print("rows:", len(res))
