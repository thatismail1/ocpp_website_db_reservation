"""Forecast-error Monte Carlo (Sec. 3.5-i)."""
import os, sys, json, subprocess, pickle, time
BASE = dict(PV_SCALE="1.0", N_VEH="12", FEEDER_LOAD="0.60", CTRL_INT="5",
            BAND="0.955")
CASE = sys.argv[1] if len(sys.argv) > 1 else "C2b"
SEEDS = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else range(1, 16)
fn = f"mc_{CASE}.json"
res = json.load(open(fn)) if os.path.exists(fn) else {}
for sd in SEEDS:
    if str(sd) in res:
        continue
    e = dict(os.environ); e.update(BASE); e["FORECAST_SEED"] = str(sd)
    if os.path.exists("cases.pkl"):
        os.remove("cases.pkl")
    t0 = time.perf_counter()
    rc = subprocess.run([sys.executable, "run.py", "coord_sb"], env=e,
                        capture_output=True, text=True, timeout=900)
    if rc.returncode != 0:
        print(f"seed {sd} coord FAILED\n{rc.stdout[-600:]}{rc.stderr[-600:]}"); continue
    r = subprocess.run([sys.executable, "run.py", CASE], env=e,
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print(f"seed {sd} FAILED\n{r.stdout[-800:]}{r.stderr[-800:]}"); continue
    c = pickle.load(open("cases.pkl", "rb"))
    m = c[list(c)[0]]
    res[str(sd)] = {k: m[k] for k in
                    ["V_min", "undervolt_bus_min", "undervolt_minutes",
                     "Ssub_peak_kVA", "loss_MWh", "cost_adjusted",
                     "deficit_kWh", "deficit_events", "charge_energy_MWh",
                     "soc_end_mean"]}
    json.dump(res, open(fn, "w"), indent=1)
    x = res[str(sd)]
    print(f"{CASE} seed {sd:3d}: Vmin {x['V_min']:.4f} uv {x['undervolt_bus_min']:5.0f} "
          f"peak {x['Ssub_peak_kVA']:.0f} cost {x['cost_adjusted']:.0f} "
          f"def {x['deficit_kWh']:.1f} kWh  ({time.perf_counter()-t0:.0f}s)", flush=True)
