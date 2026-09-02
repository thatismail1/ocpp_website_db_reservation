import json, numpy as np, os
D = json.load(open("series.json")); M = D["metrics"]; SER = D["series"]
SW = json.load(open("sweep.json"))
MC955 = json.load(open("mc_C2b_0.955.json"))
MCE = json.load(open("mc_C2e_margin.json")) if os.path.exists("mc_C2e_margin.json") else {}
K = {k.split()[0]: k for k in M}
ORD = ["C0", "C1", "C2", "C2b", "C2c", "C2d", "C2e", "C3"]
ORD = [c for c in ORD if c in K]
CC = {"C0": "#B4442F", "C1": "#C08A1E", "C2": "#7A6A9B", "C2b": "#2E7D8C",
      "C2c": "#2E7D8C", "C2d": "#8A6D3B", "C2e": "#2F6B45"}
N = 288


def path(y, x0, y0, w, h, ymin, ymax, n=N):
    y = np.asarray(y, float)
    xs = x0 + np.arange(n) / (n - 1) * w
    ys = y0 + h - (np.clip(y, ymin, ymax) - ymin) / (ymax - ymin) * h
    return "M" + " L".join(f"{a:.1f},{b:.2f}" for a, b in zip(xs, ys))


def chart(series, ymin, ymax, ylab, yticks, hline=None, hlab="", w=760, h=200):
    x0, y0 = 54, 14
    o = [f'<svg viewBox="0 0 {w+72} {h+50}" role="img" class="ch">']
    for v in yticks:
        yy = y0 + h - (v - ymin) / (ymax - ymin) * h
        o.append(f'<line class="grid" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
        o.append(f'<text class="tk" x="{x0-8}" y="{yy+3.5:.1f}" text-anchor="end">{v:g}</text>')
    for hr in range(0, 25, 3):
        xx = x0 + hr / 24 * w
        o.append(f'<text class="tk" x="{xx:.1f}" y="{y0+h+18}" text-anchor="middle">{hr:02d}</text>')
    if hline is not None:
        yy = y0 + h - (hline - ymin) / (ymax - ymin) * h
        o.append(f'<line class="lim" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
        o.append(f'<text class="lim-t" x="{x0+w+4}" y="{yy+3.5:.1f}">{hlab}</text>')
    for nm, ys, col, sw in series:
        o.append(f'<path d="{path(ys,x0,y0,w,h,ymin,ymax)}" fill="none" stroke="{col}" '
                 f'stroke-width="{sw}" stroke-linejoin="round"/>')
    o.append(f'<text class="ax" x="{x0}" y="{y0+h+36}">hour of day</text>')
    o.append(f'<text class="ax" transform="translate(13,{y0+h/2}) rotate(-90)" '
             f'text-anchor="middle">{ylab}</text></svg>')
    return "".join(o)


def legend(items):
    return ('<div class="lg">' + "".join(
        f'<span class="lgi"><i style="background:{c}"></i>{n}</span>' for n, c in items) + "</div>")


PICK = ["C0", "C1", "C2b", "C2e"]
c_volt = chart([(c, SER[K[c]]["Vmin"], CC[c], 1.7) for c in PICK],
               0.910, 0.975, "min bus voltage [p.u.]",
               [0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97], 0.95, "0.95")
c_sub = chart([(c, np.array(SER[K[c]]["Ssub"]) / 1000, CC[c], 1.7) for c in PICK],
              1.4, 5.2, "substation [MVA]", [2, 3, 4, 5], 5.0, "5 MVA")
c_pow = chart([("C0", SER[K["C0"]]["ctrl_total"], CC["C0"], 1.5),
               ("C2e", SER[K["C2e"]]["ctrl_total"], CC["C2e"], 1.8)],
              0, 1500, "fleet charging [kW]", [0, 500, 1000, 1500])
lg_main = legend([(c, CC[c]) for c in PICK])
lg_pow = legend([("C0 uncoordinated", CC["C0"]), ("C2e coordinated", CC["C2e"])])

# ADMM convergence, log scale
pri = D["admm"]["primal"]; n = len(pri)
x0, y0, w, h = 54, 14, 380, 170
lo, hi = np.log10(0.5), np.log10(3000)
pts = [(x0 + i / max(n - 1, 1) * w, y0 + h - (np.log10(max(v, 0.5)) - lo) / (hi - lo) * h)
       for i, v in enumerate(pri)]
c_adm = [f'<svg viewBox="0 0 520 240" role="img" class="ch">']
for v in [1, 10, 100, 1000]:
    yy = y0 + h - (np.log10(v) - lo) / (hi - lo) * h
    c_adm.append(f'<line class="grid" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
    c_adm.append(f'<text class="tk" x="{x0-8}" y="{yy+3.5:.1f}" text-anchor="end">{v}</text>')
for i in range(n):
    xx = x0 + i / max(n - 1, 1) * w
    c_adm.append(f'<text class="tk" x="{xx:.1f}" y="{y0+h+18}" text-anchor="middle">{i+1}</text>')
c_adm.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) +
             f'" fill="none" stroke="{CC["C2e"]}" stroke-width="1.8"/>')
for a, b in pts:
    c_adm.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3" fill="{CC["C2e"]}"/>')
c_adm.append(f'<text class="ax" x="{x0}" y="{y0+h+36}">ADMM iteration</text>')
c_adm.append(f'<text class="ax" transform="translate(13,{y0+h/2}) rotate(-90)" '
             f'text-anchor="middle">||r|| [kW]</text></svg>')
c_adm = "".join(c_adm)


def sweep_panel(fam, xlab, w=228, h=150):
    pts = sorted([v for v in SW.values() if v["family"] == fam], key=lambda z: z["value"])
    xs = [p["value"] for p in pts]
    ymax = max(max(p["c0_uv"] for p in pts), 1) * 1.15
    x0, y0 = 44, 12
    o = [f'<svg viewBox="0 0 {w+60} {h+46}" role="img" class="ch sm">']
    for f in [0, .5, 1]:
        yy = y0 + h - f * h
        o.append(f'<line class="grid" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
        o.append(f'<text class="tk" x="{x0-6}" y="{yy+3.5:.1f}" text-anchor="end">{f*ymax:.0f}</text>')
    for key, col in [("c0_uv", CC["C0"]), ("c2_uv", CC["C2e"])]:
        d = " L".join(f"{x0 + (i/(len(xs)-1))*w:.1f},{y0+h-(p[key]/ymax)*h:.1f}"
                      for i, p in enumerate(pts))
        o.append(f'<path d="M{d}" fill="none" stroke="{col}" stroke-width="1.8"/>')
        for i, p in enumerate(pts):
            o.append(f'<circle cx="{x0+(i/(len(xs)-1))*w:.1f}" '
                     f'cy="{y0+h-(p[key]/ymax)*h:.1f}" r="3" fill="{col}"/>')
    for i, x in enumerate(xs):
        o.append(f'<text class="tk" x="{x0+(i/(len(xs)-1))*w:.1f}" y="{y0+h+17}" '
                 f'text-anchor="middle">{x:g}</text>')
    o.append(f'<text class="ax" x="{x0}" y="{y0+h+35}">{xlab}</text></svg>')
    return "".join(o)


sw_pv, sw_fl, sw_ld = (sweep_panel("PV", "PV multiple"),
                       sweep_panel("FLEET", "vehicles"),
                       sweep_panel("LOAD", "feeder loading"))

# ---- tables
ROWS = [("Network security", None, None, None),
        ("Minimum bus voltage", "V_min", "%.4f", "p.u."),
        ("Under-voltage bus-minutes", "undervolt_bus_min", "%d", "bus-min"),
        ("Substation peak", "Ssub_peak_kVA", "%.0f", "kVA"),
        ("Max branch loading", "branch_max_loading", "%.3f", "p.u."),
        ("Envelope excess, max", "env_excess_max_kW", "%.1f", "kW"),
        ("Energy &amp; cost", None, None, None),
        ("Feeder loss energy", "loss_MWh", "%.3f", "MWh"),
        ("Fleet charging energy", "charge_energy_MWh", "%.3f", "MWh"),
        ("Energy delivered, SoC-adjusted", "energy_delivered_MWh", "%.3f", "MWh"),
        ("Fleet SoC gap at 24:00", "soc_gap_kWh", "%.0f", "kWh"),
        ("Feeder cost, day-neutral", "cost_adjusted", "%.0f", "TL"),
        ("Transit service", None, None, None),
        ("Departure deficit energy", "deficit_kWh", "%.2f", "kWh"),
        ("Minimum fleet SoC", "soc_min", "%.3f", "p.u."),
        ("Computation", None, None, None),
        ("Upper-level re-dispatches", "ul_ticks", "%d", "&mdash;"),
        ("Mean hub MPC solve", "t_mean_ms", "%.1f", "ms"),
        ("Max hub MPC solve", "t_max_ms", "%.1f", "ms"),
        ("Closed-loop wall time", "wall_s", "%.0f", "s")]
tr = []
for name, key, fmt, unit in ROWS:
    if key is None:
        tr.append(f'<tr class="grp"><td colspan="{len(ORD)+2}">{name}</td></tr>'); continue
    tds = "".join(f'<td class="num">{(fmt % M[K[c]][key]) if key in M[K[c]] else "&mdash;"}</td>'
                  for c in ORD)
    tr.append(f"<tr><td>{name}</td>{tds}<td class='unit'>{unit}</td></tr>")
TABLE = "\n".join(tr)
HEAD = "".join(f'<th style="text-align:right"{" class=win" if c=="C2e" else ""}>{c}</th>'
               for c in ORD)

def mcrow(dic, lab):
    if not dic:
        return f"<tr><td>{lab}</td><td colspan='5' class='unit'>not run</td></tr>"
    uv = [v["undervolt_bus_min"] for v in dic.values()]
    vm = [v["V_min"] for v in dic.values()]
    ch = [v["charge_energy_MWh"] for v in dic.values()]
    ct = [v["cost_adjusted"] for v in dic.values()]
    df = [v["deficit_kWh"] for v in dic.values()]
    return (f"<tr><td>{lab}</td><td class='num'>{len(uv)}</td>"
            f"<td class='num'>{min(vm):.4f}</td>"
            f"<td class='num'>{min(uv):.0f}&ndash;{max(uv):.0f}</td>"
            f"<td class='num'>{np.mean(ch):.2f}</td>"
            f"<td class='num'>{np.mean(ct):.0f}</td>"
            f"<td class='num'>{max(df):.1f}</td></tr>")

MCT = (mcrow(MC955, "C2b, static envelope + 0.955 band") +
       mcrow(MCE, "C2e, rolling + AC correction + 5&nbsp;% forecast margin"))

SWT = "\n".join(
    f"<tr><td>{v['family']} = {v['value']:g}</td>"
    f"<td class='num'>{v['c0_vmin']:.4f}</td><td class='num'>{v['c2_vmin']:.4f}</td>"
    f"<td class='num'>{v['c0_uv']:.0f}</td><td class='num'>{v['c2_uv']:.0f}</td>"
    f"<td class='num'>{v['c0_peak']:.0f}</td><td class='num'>{v['c2_peak']:.0f}</td>"
    f"<td class='num'>{v['c0_cost']:.0f}</td><td class='num'>{v['c2_cost']:.0f}</td></tr>"
    for k, v in sorted(SW.items(), key=lambda z: (z[1]["family"], z[1]["value"])))

json.dump(dict(c_volt=c_volt, c_sub=c_sub, c_pow=c_pow, c_adm=c_adm,
               lg_main=lg_main, lg_pow=lg_pow, sw_pv=sw_pv, sw_fl=sw_fl,
               sw_ld=sw_ld, TABLE=TABLE, HEAD=HEAD, MCT=MCT, SWT=SWT,
               ncol=len(ORD)), open("ctx2.json", "w"))
print("ctx2 ready; cases:", ORD)
