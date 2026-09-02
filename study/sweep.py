"""Sensitivity sweeps. Each configuration runs in its own process (via env
vars) so no scenario state leaks between points."""
import os, sys, json, subprocess, pickle, time

BASE = dict(PV_SCALE="1.0", N_VEH="12", FEEDER_LOAD="0.60", CTRL_INT="5",
            BAND="0.955")
POINTS = []
for v in ["0.0", "1.0", "2.0", "3.0"]:
    POINTS.append(("PV", v, dict(PV_SCALE=v)))
for v in ["8", "12", "16"]:
    POINTS.append(("FLEET", v, dict(N_VEH=v)))
for v in ["0.50", "0.60", "0.70"]:
    POINTS.append(("LOAD", v, dict(FEEDER_LOAD=v)))


def run(stage, env):
    e = dict(os.environ); e.update(BASE); e.update(env)
    r = subprocess.run([sys.executable, "run.py", stage], env=e,
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"{stage} failed:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r.stdout


def main():
    fn = "sweep.json"
    res = json.load(open(fn)) if os.path.exists(fn) else {}
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for fam, val, env in POINTS:
        key = f"{fam}={val}"
        if key in res or (only and fam != only):
            continue
        t0 = time.perf_counter()
        if os.path.exists("cases.pkl"):
            os.remove("cases.pkl")
        out = run("coord_sb", env)
        curt = [l for l in out.splitlines() if "curtail" in l.lower()]
        run("C0", env)
        run("C2b", env)
        c = pickle.load(open("cases.pkl", "rb"))
        pick = lambda lab, k: c[[x for x in c if x.startswith(lab)][0]][k]
        res[key] = dict(
            family=fam, value=float(val),
            c0_vmin=pick("C0", "V_min"), c2_vmin=pick("C2b", "V_min"),
            c0_uv=pick("C0", "undervolt_bus_min"), c2_uv=pick("C2b", "undervolt_bus_min"),
            c0_peak=pick("C0", "Ssub_peak_kVA"), c2_peak=pick("C2b", "Ssub_peak_kVA"),
            c0_loss=pick("C0", "loss_MWh"), c2_loss=pick("C2b", "loss_MWh"),
            c0_cost=pick("C0", "cost_adjusted"), c2_cost=pick("C2b", "cost_adjusted"),
            c0_def=pick("C0", "deficit_kWh"), c2_def=pick("C2b", "deficit_kWh"),
            c2_charge=pick("C2b", "charge_energy_MWh"),
            wall=time.perf_counter() - t0)
        json.dump(res, open(fn, "w"), indent=1)
        r = res[key]
        print(f"{key:14s} Vmin {r['c0_vmin']:.4f}->{r['c2_vmin']:.4f} | "
              f"uv {r['c0_uv']:5.0f}->{r['c2_uv']:4.0f} bus-min | "
              f"peak {r['c0_peak']:.0f}->{r['c2_peak']:.0f} kVA | "
              f"cost {r['c0_cost']:.0f}->{r['c2_cost']:.0f} | "
              f"{r['wall']:.0f}s", flush=True)


main()
