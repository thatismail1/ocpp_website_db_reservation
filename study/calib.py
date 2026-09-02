"""Equalise base-case voltage headroom across hub placements, so the distance
sweep varies electrical coupling between hubs and nothing else."""
import os, subprocess, sys, json
TARGET = 0.9520
out = {}
for b in [17, 16, 14, 12, 8, 4, 22]:
    lo, hi = 0.35, 0.85
    for _ in range(14):
        mid = (lo + hi) / 2
        e = dict(os.environ, HUB_BUSES=f"18,33,{b},25", FEEDER_LOAD=f"{mid:.5f}")
        r = subprocess.run([sys.executable, "-c", """
import sys; sys.path.insert(0,'.')
import system as S, powerflow as PF
f=PF.Feeder(); e=S.build_exogenous(); print(f.solve(e['P_feeder'],e['Q_feeder'])['Vm'].min())
"""], env=e, capture_output=True, text=True)
        v = float(r.stdout.strip())
        if v > TARGET:      # too much headroom -> load it more
            lo = mid
        else:
            hi = mid
    out[b] = round(lo, 5)
    print(f"  hub C @ bus {b:2d}: FEEDER_LOAD={lo:.4f}  (base Vmin ~ {TARGET})", flush=True)
json.dump(out, open("calib.json", "w"))
