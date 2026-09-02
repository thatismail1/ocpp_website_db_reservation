import json, numpy as np
d = json.load(open("dist_sweep.json"))
by = {}
for v in d.values(): by.setdefault(v["arm"], []).append(v)
for a in by: by[a].sort(key=lambda z: z["coupling"])
COL = {"DOE-fair": "#C08A1E", "DOE-eff": "#B4442F", "fleet-aware": "#2F6B45"}
LBL = {"DOE-fair": "DOE, proportional fairness", "DOE-eff": "DOE, max efficiency",
       "fleet-aware": "fleet-aware allocation"}

def panel(key, ymax, ylab, ticks, w=430, h=250):
    x0, y0 = 62, 16
    o = [f'<svg viewBox="0 0 {w+80} {h+58}" class="ch" role="img">']
    # threshold band between 0.276 and 0.515
    xa = x0 + 0.276 * w; xb = x0 + 0.515 * w
    o.append(f'<rect x="{xa:.1f}" y="{y0}" width="{xb-xa:.1f}" height="{h}" '
             f'fill="currentColor" opacity="0.07"/>')
    o.append(f'<text class="tk" x="{(xa+xb)/2:.1f}" y="{y0+12}" text-anchor="middle" '
             f'opacity="0.75">threshold</text>')
    for v in ticks:
        yy = y0 + h - v / ymax * h
        o.append(f'<line class="grid" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
        o.append(f'<text class="tk" x="{x0-8}" y="{yy+3.5:.1f}" text-anchor="end">{v:g}</text>')
    for xv in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        xx = x0 + xv * w
        o.append(f'<text class="tk" x="{xx:.1f}" y="{y0+h+18}" text-anchor="middle">{xv:g}</text>')
    for arm in ["DOE-fair", "DOE-eff", "fleet-aware"]:
        pts = [(x0 + v["coupling"] * w, y0 + h - min(v[key], ymax) / ymax * h)
               for v in by[arm]]
        dash = ' stroke-dasharray="5 3"' if arm == "fleet-aware" else ""
        o.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) +
                 f'" fill="none" stroke="{COL[arm]}" stroke-width="2"{dash}/>')
        for a, b in pts:
            o.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3.4" fill="{COL[arm]}"/>')
    o.append(f'<text class="ax" x="{x0}" y="{y0+h+40}">electrical coupling between hubs '
             f'(R shared / R own path)</text>')
    o.append(f'<text class="ax" transform="translate(15,{y0+h/2}) rotate(-90)" '
             f'text-anchor="middle">{ylab}</text></svg>')
    return "".join(o)

fig_uv = panel("uv", 180, "under-voltage bus-minutes", [0, 50, 100, 150])
fig_df = panel("deficit_kWh", 500, "missed departure energy [kWh]", [0, 100, 200, 300, 400, 500])
leg = ('<div class="lg">' + "".join(
    f'<span class="lgi"><i style="background:{COL[a]}"></i>{LBL[a]}</span>'
    for a in ["DOE-fair", "DOE-eff", "fleet-aware"]) + "</div>")
rows = []
for b in [17, 16, 14, 12, 8, 4, 22]:
    r = {v["arm"]: v for v in d.values() if v["bus"] == b}
    c = r["DOE-fair"]["coupling"]
    def cell(a):
        if a not in r: return "<td class='num'>&mdash;</td>"*3
        v = r[a]
        return (f"<td class='num'>{v['uv']}</td><td class='num'>{v['deficit_kWh']:.1f}</td>"
                f"<td class='num'>{v['charge']:.2f}</td>")
    hot = " class='hot'" if c > 0.4 else ""
    rows.append(f"<tr{hot}><td>{b}</td><td class='num'>{c:.3f}</td>"
                + cell("DOE-fair") + cell("DOE-eff") + cell("fleet-aware") + "</tr>")
json.dump(dict(fig_uv=fig_uv, fig_df=fig_df, leg=leg, rows="\n".join(rows)),
          open("figs.json", "w"))
print("ok")
