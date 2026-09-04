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


def test_set():
    """IEEE 33-bus, published impedances. Held out."""
    import system as S
    par, ch, bidx, r, x, order = S.feeder_topology()
    p = np.zeros(33); q = np.zeros(33)
    for b, (pp, qq) in S.LOAD.items():
        p[b - 1] = pp; q[b - 1] = qq
    rr = np.array([r[bidx[j]] for j in range(1, 33)])
    xx = np.array([x[bidx[j]] for j in range(1, 33)])
    parent = np.array([max(par[j], 0) for j in range(33)])
    out = []
    base = CR.RadialNet(parent, rr, xx, p, q)
    pairs = []
    for rho_t in RHOS:
        hp, err = CR.pick_hub_pair(base, rho_t)
        if hp is not None:
            pairs.append((hp, CR.coupling(base, *hp)))
    for hp, rho in pairs:
        for vb in MARGINS:
            net = CR.RadialNet(parent, rr, xx, p, q)
            CR.scale_to_vmin(net, vb)
            for band in BANDS:
                out += one(net, hp, V_MIN + band, "ieee33",
                           dict(seed=0, rho=rho, v_base=vb, band=band,
                                margin=vb ** 2 - V_MIN ** 2))
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = json.load(open("crit_rows.json")) if os.path.exists("crit_rows.json") else []
    if what in ("all", "deriv"):
        res += derivation_set(int(os.environ.get("NTOP", 20)))
    if what in ("all", "test"):
        res += test_set()
    json.dump(res, open("crit_rows.json", "w"))
    print("rows:", len(res))
