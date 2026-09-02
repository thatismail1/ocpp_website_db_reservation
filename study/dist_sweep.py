"""Distance sweep: does the failure of connection-specific envelope allocation
scale with the electrical coupling between contending charging hubs?

Hub A is fixed at bus 18 (end of the longest lateral). Hub C is moved inward
along the same lateral and finally onto a separate one. Hub C is modelled as a bare
en-route charging point (no building load, no canopy PV), so the base case is
identical at every placement (minimum voltage 0.9572 p.u., zero violations)
and electrical coupling between the two hubs is the only quantity that varies.
"""
import os, sys, json, subprocess, pickle, time


BUSES = [17, 16, 14, 12, 8, 4, 22]
COUPLING = {17: 0.934, 16: 0.817, 14: 0.696, 12: 0.515,
            8: 0.276, 4: 0.086, 22: 0.008}      # R_shared / R_AA
FN = "dist_sweep.json"
res = json.load(open(FN)) if os.path.exists(FN) else {}
ARMS = [("DOE-fair", "CDOE", dict(DOE_FAIR="proportional", DOE_VMIN="0.955")),
        ("DOE-eff", "CDOE", dict(DOE_FAIR="efficiency", DOE_VMIN="0.955")),
        ("fleet-aware", "C2e", dict(BAND="0.95"))]
ONLY = sys.argv[1:] if len(sys.argv) > 1 else None


def run(bus, arm, case, extra):
    key = f"{bus}|{arm}"
    if key in res:
        return
    env = dict(os.environ, HUB_BUSES=f"18,33,{bus},25", HUB_C_BARE="1",
               FEEDER_LOAD="0.60", N_VEH="16", CTRL_INT="5", **extra)
    if os.path.exists("cases.pkl"):
        os.remove("cases.pkl")
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, "run.py", case], env=env,
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print(f"  bus {bus} {arm} FAILED\n{r.stdout[-500:]}{r.stderr[-400:]}", flush=True)
        return
    m = pickle.load(open("cases.pkl", "rb"))
    m = m[list(m)[0]]
    res[key] = dict(bus=bus, arm=arm, coupling=COUPLING[bus],
                    V_min=m["V_min"], uv=m["undervolt_bus_min"],
                    deficit_kWh=m["deficit_kWh"], deficit_n=m["deficit_events"],
                    charge=m["charge_energy_MWh"], cost=m["energy_cost"],
                    peak=m["Ssub_peak_kVA"], wall=time.perf_counter() - t0)
    json.dump(res, open(FN, "w"), indent=1)
    x = res[key]
    print(f"  bus {bus:2d} (coupling {x['coupling']:.3f})  {arm:12s} "
          f"Vmin {x['V_min']:.4f}  uv {x['uv']:4.0f}  "
          f"missed {x['deficit_n']:3d} ({x['deficit_kWh']:6.1f} kWh)  "
          f"charged {x['charge']:.2f} MWh  [{x['wall']:.0f}s]", flush=True)


# the fleet-aware reference is ~3x the cost of a DOE run, so it is evaluated
# at four placements spanning the coupling range rather than all seven
FA_BUSES = [17, 14, 8, 22]
for bus in BUSES:
    for arm, case, extra in ARMS:
        if ONLY and arm not in ONLY:
            continue
        if arm == "fleet-aware" and bus not in FA_BUSES:
            continue
        run(bus, arm, case, extra)
