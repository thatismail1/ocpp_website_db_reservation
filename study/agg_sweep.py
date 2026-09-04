"""Closed-loop sweep for Lambda_total: 7 hub placements x 2 planning bands.

Same design as dist_sweep.py -- hub C is a bare en-route point moved along
the lateral so that electrical coupling rho is the only quantity that varies
and the base case is identical at every placement.
"""
import os, sys, subprocess, time
BUSES = [17, 16, 14, 12, 8, 4, 22]
BANDS = [0.005, 0.010]
for band in BANDS:
    for bus in BUSES:
        out = f"agg_b{bus}_{band}.npz"
        if os.path.exists(out):
            continue
        env = dict(os.environ, HUB_BUSES=f"18,33,{bus},25", HUB_C_BARE="1",
                   FEEDER_LOAD="0.60", N_VEH="16", CTRL_INT="5",
                   DOE_FAIR="proportional")
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, "agg_run.py", str(bus), str(band), out],
                           env=env, capture_output=True, text=True, timeout=1800)
        print(f"bus {bus} band {band}: {r.stdout.strip().splitlines()[-1] if r.returncode==0 else 'FAIL '+r.stderr[-300:]}"
              f"  [{time.perf_counter()-t0:.0f}s]", flush=True)
