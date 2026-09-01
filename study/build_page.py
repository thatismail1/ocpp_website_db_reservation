import json, numpy as np
D = json.load(open("series.json")); C = json.load(open("charts.json"))
M = D["metrics"]
K = {"C0": "C0  Uncoordinated", "C1": "C1  Local MPC (TOU, site cap)",
     "C2": "C2  Hierarchical bi-level", "C2b": "C2b Hierarchical + security band",
     "C3": "C3  Centralised 15-min bound"}
cols = ["C0", "C1", "C2", "C2b", "C3"]


def cell(c, key, fmt="%.4g"):
    m = M.get(K[c], {})
    return fmt % m[key] if key in m else "&mdash;"


ROWS = [
 ("Network security", None, None),
 ("Minimum bus voltage", "V_min", "%.4f", "p.u."),
 ("Under-voltage minutes (any bus)", "undervolt_minutes", "%d", "min"),
 ("Under-voltage bus-minutes", "undervolt_bus_min", "%d", "bus-min"),
 ("Voltage deviation RMS", "V_dev_rms", "%.5f", "p.u."),
 ("Max branch loading", "branch_max_loading", "%.3f", "p.u."),
 ("Substation peak", "Ssub_peak_kVA", "%.0f", "kVA"),
 ("Substation overload", "sub_overload_min", "%d", "min"),
 ("Energy &amp; economics", None, None),
 ("Feeder loss energy", "loss_MWh", "%.3f", "MWh"),
 ("Peak feeder loss", "loss_peak_kW", "%.1f", "kW"),
 ("Substation import", "substation_energy_MWh", "%.2f", "MWh"),
 ("Fleet charging energy", "charge_energy_MWh", "%.3f", "MWh"),
 ("BESS throughput", "bess_throughput_MWh", "%.3f", "MWh"),
 ("Fleet SoC gap at 24:00", "soc_gap_kWh", "%.0f", "kWh"),
 ("Energy delivered, SoC-adjusted", "energy_delivered_MWh", "%.3f", "MWh"),
 ("Feeder energy cost, raw", "energy_cost", "%.0f", "TL"),
 ("Feeder energy cost, day-neutral", "cost_adjusted", "%.0f", "TL"),
 ("Charging cost at TOU", "charging_cost", "%.0f", "TL"),
 ("Transit service", None, None),
 ("Departure deficit events", "deficit_events", "%d", "&mdash;"),
 ("Departure deficit energy", "deficit_kWh", "%.2f", "kWh"),
 ("Minimum fleet SoC", "soc_min", "%.3f", "p.u."),
 ("Mean end-of-day SoC", "soc_end_mean", "%.3f", "p.u."),
 ("Computation", None, None),
 ("MPC solves", "n_solves", "%d", "&mdash;"),
 ("Mean solve time", "t_mean_ms", "%.1f", "ms"),
 ("Max solve time", "t_max_ms", "%.1f", "ms"),
 ("Closed-loop wall time", "wall_s", "%.0f", "s"),
]

trs = []
for row in ROWS:
    if row[1] is None:
        trs.append(f'<tr class="grp"><td colspan="7">{row[0]}</td></tr>')
        continue
    name, key, fmt, unit = row
    tds = "".join(f'<td class="num">{cell(c,key,fmt)}</td>' for c in cols)
    trs.append(f'<tr><td>{name}</td>{tds}<td class="unit">{unit}</td></tr>')
TABLE = "\n".join(trs)

hub = []
for c in ["C0", "C1", "C2", "C2b"]:
    v = M[K[c]].get("hub_peak_kW", [])
    hub.append(f'<tr><td>{c}</td>' + "".join(f'<td class="num">{x:.0f}</td>' for x in v) + "</tr>")
HUB = "\n".join(hub)

adm = D["admm"]
ctx = dict(TABLE=TABLE, HUB=HUB,
           it=len(adm["primal"]),
           rfin=adm["primal"][-1], rrms=adm["primal"][-1] / np.sqrt(384),
           marg=adm["margin_mean"], **C)
open("ctx.json", "w").write(json.dumps({k: (v if isinstance(v, str) else float(v))
                                        for k, v in ctx.items() if k != "it"} |
                                       {"it": int(ctx["it"])}))
print("ctx ready", ctx["it"], round(ctx["rfin"],1), round(ctx["rrms"],1), round(ctx["marg"]))
