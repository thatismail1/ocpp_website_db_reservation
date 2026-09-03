"""Second-network robustness test: repeat the distance sweep on a different
lateral of the same feeder, with base headroom matched to the first sweep.

Hub A moves to bus 33 (end of lateral 6-26-...-33), hub B takes bus 18, and
hub C is walked inward along lateral 3 and finally onto lateral 2. Feeder
loading is raised to 0.6719 so the base-case minimum voltage is 0.9572 p.u.,
identical to the first sweep, making the two directly comparable.
"""
import os, sys, json, subprocess, pickle, time

COUPLING = {32: 0.949, 30: 0.755, 28: 0.557, 27: 0.398, 26: 0.355, 22: 0.014}
BUSES = [32, 30, 28, 27, 26, 22]
ARMS = [("DOE-eff", "CDOE", dict(DOE_FAIR="efficiency", DOE_VMIN="0.955")),
        ("DOE-fair", "CDOE", dict(DOE_FAIR="proportional", DOE_VMIN="0.955")),
        ("fleet-aware", "C2e", dict(BAND="0.95"))]
FA_BUSES = [32, 22]
FN = "lat3_sweep.json"
res = json.load(open(FN)) if os.path.exists(FN) else {}
ONLY = sys.argv[1:] or None

for bus in BUSES:
    for arm, case, extra in ARMS:
        if ONLY and arm not in ONLY:
            continue
        if arm == "fleet-aware" and bus not in FA_BUSES:
            continue
        key = f"{bus}|{arm}"
        if key in res:
            continue
        env = dict(os.environ, HUB_BUSES=f"33,18,{bus},25", HUB_C_BARE="1",
                   FEEDER_LOAD="0.6719", N_VEH="16", CTRL_INT="5", **extra)
        if os.path.exists("cases.pkl"):
            os.remove("cases.pkl")
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, "run.py", case], env=env,
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            print(f"  bus {bus} {arm} FAILED\n{r.stdout[-400:]}{r.stderr[-300:]}", flush=True)
            continue
        m = pickle.load(open("cases.pkl", "rb")); m = m[list(m)[0]]
        res[key] = dict(bus=bus, arm=arm, coupling=COUPLING[bus], V_min=m["V_min"],
                        uv=m["undervolt_bus_min"], deficit_kWh=m["deficit_kWh"],
                        deficit_n=m["deficit_events"], charge=m["charge_energy_MWh"],
                        wall=time.perf_counter() - t0)
        json.dump(res, open(FN, "w"), indent=1)
        x = res[key]
        print(f"  bus {bus:2d} (cpl {x['coupling']:.3f})  {arm:12s} Vmin {x['V_min']:.4f} "
              f"uv {x['uv']:4.0f}  missed {x['deficit_n']:3d} ({x['deficit_kWh']:6.1f} kWh) "
              f"chg {x['charge']:.2f} [{x['wall']:.0f}s]", flush=True)
