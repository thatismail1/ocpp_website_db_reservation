"""Figures for the Lambda_total report: rebuild fig 1/2 and add the
decomposition panel (D_err vs D_agg across rho, from the closed loop)."""
import json
import numpy as np

W, H = 650, 300
L, RM, T, B = 66, 16, 14, 40


def frame(ymax, yticks, xticks, xlab, ylab, xmax=1.0, xmin=0.0):
    sx = lambda x: L + (W - L - RM) * (x - xmin) / (xmax - xmin)
    sy = lambda y: H - B - (H - B - T) * y / ymax
    s = [f'<svg viewBox="0 0 {W} {H}" class="ch" role="img">']
    for gy in yticks:
        s.append(f'<line class="grid" x1="{L}" y1="{sy(gy):.1f}" x2="{W-RM}" y2="{sy(gy):.1f}"/>'
                 f'<text class="tk" x="{L-8}" y="{sy(gy)+3.5:.1f}" text-anchor="end">{gy:g}</text>')
    for gx in xticks:
        s.append(f'<text class="tk" x="{sx(gx):.1f}" y="{H-B+18}" text-anchor="middle">{gx:g}</text>')
    s.append(f'<text class="ax" x="{(L+W-RM)/2:.0f}" y="{H-6}" text-anchor="middle">{xlab}</text>')
    yc = int((T + H - B) / 2)
    s.append(f'<text class="ax" x="13" y="{yc}" text-anchor="middle" '
             f'transform="rotate(-90 13 {yc})">{ylab}</text>')
    return s, sx, sy


def series(s, sx, sy, xs, ys, col, dash=None, r=3.4):
    d = ' '.join(f'{"M" if i==0 else "L"}{sx(a):.1f},{sy(b):.1f}' for i, (a, b) in enumerate(zip(xs, ys)))
    da = f' stroke-dasharray="{dash}"' if dash else ''
    s.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.4"{da}/>')
    for a, b in zip(xs, ys):
        s.append(f'<circle cx="{sx(a):.1f}" cy="{sy(b):.1f}" r="{r}" fill="{col}"/>')


A = sorted(json.load(open("agg_rows.json")), key=lambda r: r["rho"])
out = {}

# --- panel 3a: decomposition of the neglected drop across rho (band 0.005)
for band, key in ((0.005, "dec005"), (0.010, "dec010")):
    g = [r for r in A if abs(r["band"] - band) < 1e-9]
    if not g:
        continue
    xs = [r["rho"] for r in g]
    ymax = max(max(r["d_agg_p95"] for r in g), max(r["d_err_max"] for r in g)) * 1.15
    s, sx, sy = frame(ymax, [0, round(ymax/3, 4), round(2*ymax/3, 4)],
                      [0, 0.25, 0.5, 0.75, 1.0],
                      "shared-resistance fraction &#961;",
                      "neglected drop (p.u. of u)")
    series(s, sx, sy, xs, [r["d_agg_p95"] for r in g], "#B4442F")
    series(s, sx, sy, xs, [r["d_agg_hub_p95"] for r in g], "#C08A1E", dash="5 4")
    series(s, sx, sy, xs, [r["d_err_max"] for r in g], "#2E7D8C")
    series(s, sx, sy, xs, [r["d_err_med"] for r in g], "#2F6B45", dash="5 4")
    s.append('</svg>')
    out[key] = ''.join(s)

# --- panel 3b: closed-loop violating minutes and what each index catches
g = [r for r in A if abs(r["band"] - 0.005) < 1e-9]
xs = [r["rho"] for r in g]
ymax = max(max(r["viol_min"] for r in g), 1) * 1.2
s, sx, sy = frame(ymax, [0, int(ymax/3), int(2*ymax/3), int(ymax)],
                  [0, 0.25, 0.5, 0.75, 1.0],
                  "shared-resistance fraction &#961;",
                  "violating minutes (AC sweep)")
series(s, sx, sy, xs, [r["viol_min"] for r in g], "#171A1F")
series(s, sx, sy, xs, [r["tp_t"] for r in g], "#2E7D8C")
series(s, sx, sy, xs, [r["tp_e"] for r in g], "#B4442F", dash="5 4")
s.append('</svg>')
out["closed"] = ''.join(s)

json.dump(out, open("crit_fig3.json", "w"))
print("panels:", list(out), {k: len(v) for k, v in out.items()})
