"""Holdout and second-topology closed-loop runs.

HOLDOUT (task 1): five hub placements on IEEE-33 that were NOT in the 14-run
set used to pick the 0.85 operating threshold, plus two runs at a different
fleet size. The threshold is applied as-is, with no retuning.

IEEE-69 (task 2): the same protocol on a second published feeder. FEEDER_LOAD
is 0.75 there rather than 0.60 so that the base-case minimum voltage matches
the IEEE-33 sweep (0.9567 vs 0.9572) -- the operating point is matched, the
criterion is not tuned.
"""
import os, sys, subprocess, time

JOBS = []
for bus in [15, 13, 10, 9, 6]:                       # new rho placements
    for band in (0.005, 0.010):
        JOBS.append((f"hold_b{bus}_{band}.npz", dict(
            HUB_BUSES=f"18,33,{bus},25", HUB_C_BARE="1", FEEDER_LOAD="0.60",
            N_VEH="16", CTRL_INT="5", DOE_FAIR="proportional"), bus, band))
for bus in [17, 12]:                                 # new fleet size
    for band in (0.005, 0.010):
        JOBS.append((f"hold_n20_b{bus}_{band}.npz", dict(
            HUB_BUSES=f"18,33,{bus},25", HUB_C_BARE="1", FEEDER_LOAD="0.60",
            N_VEH="20", CTRL_INT="5", DOE_FAIR="proportional"), bus, band))
for bus in [64, 61, 59, 57, 56, 7, 46]:              # IEEE-69 rho sweep
    for band in (0.005, 0.010):
        JOBS.append((f"i69_b{bus}_{band}.npz", dict(
            FEEDER="ieee69", HUB_BUSES=f"65,27,{bus},50", HUB_C_BARE="1",
            FEEDER_LOAD="0.75", N_VEH="16", CTRL_INT="5",
            DOE_FAIR="proportional"), bus, band))

only = sys.argv[1] if len(sys.argv) > 1 else ""
for out, extra, bus, band in JOBS:
    if only and not out.startswith(only):
        continue
    if os.path.exists(out):
        continue
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, "agg_run.py", str(bus), str(band), out],
                       env=dict(os.environ, **extra), capture_output=True,
                       text=True, timeout=2400)
    tail = r.stdout.strip().splitlines()[-1] if r.returncode == 0 else "FAIL " + r.stderr[-400:]
    print(f"{out}: {tail}  [{time.perf_counter()-t0:.0f}s]", flush=True)
