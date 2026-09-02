"""Summarise results.pkl and export compact series for the results page."""
import pickle, json, numpy as np, sys
sys.path.insert(0, '.')
import system as S, transit as T

d = pickle.load(open("results.pkl", "rb"))
out = d["out"]
ORDER = ["C0  Uncoordinated", "C1  Local MPC (TOU, site cap)",
         "C2  Hierarchical bi-level", "C2b Hierarchical + security band",
         "C2c Hierarchical, net-import envelope",
         "C2d Rolling upper level, net-import envelope",
         "C2e Rolling + AC-corrected LinDistFlow",
         "C3  Centralised 15-min bound"]
labels = [k for k in ORDER if k in out]

def g(r, k, f="%.4g"):
    return f % r[k] if k in r else "--"

print("\n================= CASE SUMMARY =================")
# day-neutrality correction: value the end-of-day fleet SoC gap (positive or
# negative) at the day-mean tariff, so cases that end depleted are not
# credited for energy they simply did not buy.
pmean = float(d["exo"]["price"].mean())
for l in labels:
    r = out[l]
    if "soc_end_mean" in r:
        gap = (T.SOC_START - r["soc_end_mean"]) * T.N_VEH * T.E_VEH_KWH
        r["soc_gap_kWh"] = gap
        r["cost_adjusted"] = r["energy_cost"] + gap / T.ETA_CHG * pmean
        r["energy_delivered_MWh"] = r["charge_energy_MWh"] + gap / 1000.0

rows = [
    ("Minimum bus voltage [p.u.]", "V_min", "%.4f"),
    ("Under-voltage minutes (any bus <0.95)", "undervolt_minutes", "%d"),
    ("Under-voltage bus-minutes", "undervolt_bus_min", "%d"),
    ("Voltage deviation RMS [p.u.]", "V_dev_rms", "%.5f"),
    ("Feeder loss energy [MWh]", "loss_MWh", "%.3f"),
    ("Peak loss [kW]", "loss_peak_kW", "%.1f"),
    ("Substation peak [kVA]", "Ssub_peak_kVA", "%.0f"),
    ("Substation overload [min]", "sub_overload_min", "%d"),
    ("Max branch loading [p.u.]", "branch_max_loading", "%.3f"),
    ("Branch overload bus-min", "branch_overload_bus_min", "%d"),
    ("Fleet charging energy [MWh]", "charge_energy_MWh", "%.3f"),
    ("BESS throughput [MWh]", "bess_throughput_MWh", "%.3f"),
    ("Substation import [MWh]", "substation_energy_MWh", "%.3f"),
    ("Fleet SoC gap at 24:00 [kWh]", "soc_gap_kWh", "%.0f"),
    ("Energy delivered, SoC-adjusted [MWh]", "energy_delivered_MWh", "%.3f"),
    ("Feeder energy cost [currency]", "energy_cost", "%.0f"),
    ("Feeder cost, day-neutral [currency]", "cost_adjusted", "%.0f"),
    ("Charging cost at TOU [currency]", "charging_cost", "%.0f"),
    ("Departure deficit events", "deficit_events", "%d"),
    ("Departure deficit [kWh]", "deficit_kWh", "%.2f"),
    ("Minimum fleet SoC [p.u.]", "soc_min", "%.3f"),
    ("Mean end-of-day SoC [p.u.]", "soc_end_mean", "%.3f"),
    ("Envelope excess, max", "env_excess_max_kW", "%.1f"),
    ("Upper-level re-dispatches", "ul_ticks", "%d"),
    ("MPC solves", "n_solves", "%d"),
    ("Mean solve time [ms]", "t_mean_ms", "%.1f"),
    ("Max solve time [ms]", "t_max_ms", "%.1f"),
    ("Closed-loop wall time [s]", "wall_s", "%.0f"),
]
w = 36
SHORT = {l: l.split()[0] for l in labels}
hdr = "Metric".ljust(w) + "".join(SHORT[l].rjust(11) for l in labels)
print(hdr); print("-" * len(hdr))
for name, key, fmt in rows:
    line = name.ljust(w)
    for l in labels:
        r = out[l]
        line += (fmt % r[key]).rjust(11) if key in r else "--".rjust(11)
    print(line)

print("\nHub peak import [kW]:")
for l in labels:
    if "hub_peak_kW" in out[l]:
        print("  %-32s" % l, [round(x) for x in out[l]["hub_peak_kW"]])

a = out.get("admm")
if a is None:
    import pickle as _p; a = _p.load(open("admm_sb.pkl","rb"))
print("\n================= ADMM =================")
print("iterations run      :", len(a["hist"]))
print("final primal resid  : %.1f kW  (RMS %.1f kW per hub-interval)"
      % (a["hist"][-1]["primal"], a["hist"][-1]["primal"] / np.sqrt(4 * S.T_DAY)))
print("final dual resid    : %.3f" % a["hist"][-1]["dual"])
print("UL solve time total : %.1f s ; fleet LP total %.1f s" % (a["t_ul"], a["t_fleet"]))
print("nodal price lam     : min %.3f  mean %.3f  max %.3f  [cur/kWh]"
      % (a["lam"].min(), a["lam"].mean(), a["lam"].max()))
print("TOU price           : min %.3f  mean %.3f  max %.3f"
      % (d["exo"]["price"].min(), d["exo"]["price"].mean(), d["exo"]["price"].max()))
print("envelope margin     : mean %.0f kW  min %.0f kW  binding(<1kW) %d of %d"
      % (a["margin"].mean(), a["margin"].min(), (a["margin"] < 1).sum(), a["margin"].size))
print("envelope Pmax mean per hub [kW]:", a["pmax"].mean(1).round(0))

# ---- export compact series
def ds(x, n=288):
    x = np.asarray(x, dtype=float)
    return np.round(x.reshape(n, -1).mean(1), 4).tolist()

exp = {"labels": labels, "series": {}, "metrics": {}, "admm": {
    "primal": [h["primal"] for h in a["hist"]],
    "dual": [h["dual"] for h in a["hist"]],
    "lam_mean": ds(a["lam"].mean(0).repeat(15)),
    "pmax": {str(h): ds(a["pmax"][h].repeat(15)) for h in range(4)},
    "margin_mean": float(a["margin"].mean()),
}}
for l in labels:
    r = out[l]
    exp["metrics"][l] = {k: v for k, v in r.items() if not k.startswith("_")}
    if "_series" in r:
        s = r["_series"]
        exp["series"][l] = dict(
            Vmin=ds(s["Vmin_t"]), Ssub=ds(s["Ssub"]), loss=ds(s["loss"]),
            ctrl_total=ds(s["ctrl"].sum(0)),
            ctrl=[ds(s["ctrl"][h]) for h in range(4)],
            soc_min=ds(s["soc"][:, :-1].min(0)),
            soc_mean=ds(s["soc"][:, :-1].mean(0)),
            Vbus=np.round(s["Vm_bus_min"], 4).tolist(),
        )
exp["price"] = ds(d["exo"]["price"])
exp["pv"] = ds(d["exo"]["pv_hub"].sum(0))
exp["site_load"] = ds(d["exo"]["load_hub"].sum(0))
json.dump(exp, open("series.json", "w"))
print("\nwrote series.json")
