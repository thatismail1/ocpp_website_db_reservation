import json, numpy as np
D = json.load(open("series.json"))
M, SER = D["metrics"], D["series"]
LAB = {"C0  Uncoordinated": "C0", "C1  Local MPC (TOU, site cap)": "C1",
       "C2  Hierarchical bi-level": "C2", "C2b Hierarchical + security band": "C2b",
       "C3  Centralised 15-min bound": "C3"}
ORDER = ["C0  Uncoordinated", "C1  Local MPC (TOU, site cap)",
         "C2  Hierarchical bi-level", "C2b Hierarchical + security band"]
COL = {"C0": "var(--c0)", "C1": "var(--c1)", "C2": "var(--c2)", "C2b": "var(--c3)"}
N = 288


def path(y, x0, y0, w, h, ymin, ymax, n=N):
    y = np.asarray(y, float)
    xs = x0 + np.arange(n) / (n - 1) * w
    ys = y0 + h - (np.clip(y, ymin, ymax) - ymin) / (ymax - ymin) * h
    return "M" + " L".join(f"{a:.1f},{b:.2f}" for a, b in zip(xs, ys))


def chart(series, ymin, ymax, ylab, yticks, hline=None, hlab="", w=760, h=210):
    x0, y0 = 52, 14
    out = [f'<svg viewBox="0 0 {w+70} {h+52}" role="img" class="ch">']
    for v in yticks:
        yy = y0 + h - (v - ymin) / (ymax - ymin) * h
        out.append(f'<line class="grid" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
        out.append(f'<text class="tk" x="{x0-8}" y="{yy+3.5:.1f}" text-anchor="end">{v:g}</text>')
    for hr in range(0, 25, 3):
        xx = x0 + hr / 24 * w
        out.append(f'<text class="tk" x="{xx:.1f}" y="{y0+h+18}" text-anchor="middle">{hr:02d}</text>')
    if hline is not None:
        yy = y0 + h - (hline - ymin) / (ymax - ymin) * h
        out.append(f'<line class="lim" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
        out.append(f'<text class="lim-t" x="{x0+w+4}" y="{yy+3.5:.1f}">{hlab}</text>')
    for name, ys, col, sw in series:
        out.append(f'<path d="{path(ys,x0,y0,w,h,ymin,ymax)}" fill="none" '
                   f'stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"/>')
    out.append(f'<text class="ax" x="{x0}" y="{y0+h+38}">hour of day</text>')
    out.append(f'<text class="ax" transform="translate(13,{y0+h/2}) rotate(-90)" '
               f'text-anchor="middle">{ylab}</text>')
    out.append("</svg>")
    return "".join(out)


def legend(items):
    return ('<div class="lg">' + "".join(
        f'<span class="lgi"><i style="background:{c}"></i>{n}</span>' for n, c in items)
        + "</div>")


# ---- chart 1: minimum system voltage
c1 = chart([(LAB[k], SER[k]["Vmin"], COL[LAB[k]], 1.6) for k in ORDER],
           0.910, 0.975, "min bus voltage [p.u.]",
           [0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97], hline=0.95, hlab="0.95")
# ---- chart 2: substation loading
c2 = chart([(LAB[k], np.array(SER[k]["Ssub"]) / 1000, COL[LAB[k]], 1.6) for k in ORDER],
           1.4, 5.2, "substation [MVA]", [2, 3, 4, 5], hline=5.0, hlab="5 MVA")
# ---- chart 3: charging power
c3 = chart([("C0", SER[ORDER[0]]["ctrl_total"], COL["C0"], 1.5),
            ("C2b", SER[ORDER[3]]["ctrl_total"], COL["C2b"], 1.8)],
           0, 1500, "fleet charging [kW]", [0, 500, 1000, 1500])
# ---- chart 4: price signals
lam = np.array(D["admm"]["lam_mean"]); pr = np.array(D["price"])
c4 = chart([("TOU", pr, "var(--ink3)", 1.5),
            ("lambda", lam, "var(--c2)", 1.8)],
           0, 9, "price [TL/kWh]", [0, 2, 4, 6, 8])
# ---- chart 5: ADMM residuals (log)
pri = np.array(D["admm"]["primal"]); it = np.arange(1, len(pri) + 1)
x0, y0, w, h = 52, 14, 400, 180
lo, hi = np.log10(200), np.log10(2500)
pts = [(x0 + (i - 1) / (len(pri) - 1) * w,
        y0 + h - (np.log10(v) - lo) / (hi - lo) * h) for i, v in zip(it, pri)]
c5 = ['<svg viewBox="0 0 540 250" role="img" class="ch">']
for v in [200, 500, 1000, 2000]:
    yy = y0 + h - (np.log10(v) - lo) / (hi - lo) * h
    c5.append(f'<line class="grid" x1="{x0}" y1="{yy:.1f}" x2="{x0+w}" y2="{yy:.1f}"/>')
    c5.append(f'<text class="tk" x="{x0-8}" y="{yy+3.5:.1f}" text-anchor="end">{v}</text>')
for i in range(1, len(pri) + 1, 2):
    xx = x0 + (i - 1) / (len(pri) - 1) * w
    c5.append(f'<text class="tk" x="{xx:.1f}" y="{y0+h+18}" text-anchor="middle">{i}</text>')
c5.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts) +
          '" fill="none" stroke="var(--c2)" stroke-width="1.8"/>')
for a, b in pts:
    c5.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="2.6" fill="var(--c2)"/>')
c5.append(f'<text class="ax" x="{x0}" y="{y0+h+38}">ADMM iteration</text>')
c5.append(f'<text class="ax" transform="translate(13,{y0+h/2}) rotate(-90)" '
          f'text-anchor="middle">||r|| [kW]</text></svg>')
c5 = "".join(c5)

json.dump(dict(c1=c1, c2=c2, c3=c3, c4=c4, c5=c5,
               lg_cases=legend([(LAB[k], {"C0": "#B4442F", "C1": "#C08A1E",
                                          "C2": "#2E7D8C", "C2b": "#2F6B45"}[LAB[k]])
                                for k in ORDER]),
               lg_pc=legend([("C0 uncoordinated", "#B4442F"),
                             ("C2b hierarchical", "#2F6B45")]),
               lg_pr=legend([("TOU tariff", "#767E85"),
                             ("nodal price lambda", "#2E7D8C")])),
          open("charts.json", "w"))
print("charts written")
