"""Step 3: manipulation test. One structural knob (resistance profile of hub
A's path), rho swept identically inside each arm, everything else matched.

ARM "back"  : long thin lateral, resistance accumulating near the tip.
ARM "front" : resistance close to the substation, outer path electrically short.

FEEDER_LOAD is set per arm so both arms start from the same base-case minimum
voltage (0.9570). That is the same operating-point match used between IEEE-33
and IEEE-69, and it is a confound: the arms carry different total load
(0.415 vs 1.150 of nominal) to reach the same margin. Stated, not hidden.
"""
import os, sys, subprocess, time

ARMS = {"front": ("0.4151", [(3, 0.229), (8, 0.616), (14, 0.863)]),
        "back":  ("1.1500", [(11, 0.239), (17, 0.589), (20, 0.879)])}
for arm, (load, places) in ARMS.items():
    for bus, rho in places:
        out = f"syn_{arm}_b{bus}_0.005.npz"
        if os.path.exists(out):
            continue
        env = dict(os.environ, FEEDER="synth", SYN_PROFILE=arm,
                   HUB_BUSES=f"21,27,{bus},33", HUB_C_BARE="1",
                   FEEDER_LOAD=load, N_VEH="16", CTRL_INT="5",
                   DOE_FAIR="proportional")
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, "agg_run.py", str(bus), "0.005", out],
                           env=env, capture_output=True, text=True, timeout=2400)
        tail = r.stdout.strip().splitlines()[-1] if r.returncode == 0 else "FAIL " + r.stderr[-400:]
        print(f"{arm} rho {rho}: {tail}  [{time.perf_counter()-t0:.0f}s]", flush=True)
