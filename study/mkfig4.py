"""Side-by-side closed-loop panels: IEEE-33 fitting set, IEEE-33 holdout,
IEEE-69 second topology."""
import json
import numpy as np

W, H = 650, 300
L, RM, T, B = 66, 16, 14, 40
SETS = [("agg_rows.json", "IEEE-33 fit", "#B4442F"),
        ("hold_rows.json", "IEEE-33 holdout", "#2E7D8C"),
        ("i69_rows.json", "IEEE-69", "#7A6A9B")]


def frame(ymax, yticks, xlab, ylab, ylabfmt="{:g}"):
    sx = lambda x: L + (W - L - RM) * x
    sy = lambda y: H - B - (H - B - T) * y / ymax
    s = [f'<svg viewBox="0 0 {W} {H}" class="ch" role="img">']
    for gy in yticks:
        s.append(f'<line class="grid" x1="{L}" y1="{sy(gy):.1f}" x2="{W-RM}" y2="{sy(gy):.1f}"/>'
                 f'<text class="tk" x="{L-8}" y="{sy(gy)+3.5:.1f}" text-anchor="end">{ylabfmt.format(gy)}</text>')
    for gx in (0, 0.25, 0.5, 0.75, 1.0):
        s.append(f'<text class="tk" x="{sx(gx):.1f}" y="{H-B+18}" text-anchor="middle">{gx:g}</text>')
    s.append(f'<text class="ax" x="{(L+W-RM)/2:.0f}" y="{H-6}" text-anchor="middle">{xlab}</text>')
    yc = int((T + H - B) / 2)
    s.append(f'<text class="ax" x="13" y="{yc}" text-anchor="middle" '
             f'transform="rotate(-90 13 {yc})">{ylab}</text>')
    return s, sx, sy


def line(s, sx, sy, pts, col, dash=None):
    pts = sorted(pts)
    d = ' '.join(f'{"M" if i==0 else "L"}{sx(a):.1f},{sy(b):.1f}' for i, (a, b) in enumerate(pts))
    da = f' stroke-dasharray="{dash}"' if dash else ''
    s.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.4"{da}/>')
    for a, b in pts:
        s.append(f'<circle cx="{sx(a):.1f}" cy="{sy(b):.1f}" r="3.4" fill="{col}"/>')


data = {}
for fn, lab, col in SETS:
    rows = [r for r in json.load(open(fn)) if abs(r["band"] - 0.005) < 1e-9]
    data[lab] = (rows, col)

out = {}
# panel A: violating minutes vs rho
ymax = max(r["viol_min"] for rows, _ in data.values() for r in rows) * 1.15
s, sx, sy = frame(ymax, [0, 30, 60, 90, 120],
                  "shared-resistance fraction &#961;", "violating minutes (AC sweep)")
for lab, (rows, col) in data.items():
    line(s, sx, sy, [(r["rho"], r["viol_min"]) for r in rows], col)
s.append('</svg>')
out["viol"] = ''.join(s)

# panel B: D_agg p95 vs rho -- the term that does NOT replicate
s, sx, sy = frame(0.016, [0, 0.004, 0.008, 0.012, 0.016],
                  "shared-resistance fraction &#961;", "D_agg p95 (p.u. of u)", "{:.3f}")
for lab, (rows, col) in data.items():
    line(s, sx, sy, [(r["rho"], r["d_agg_p95"]) for r in rows], col)
for lab, (rows, col) in data.items():
    line(s, sx, sy, [(r["rho"], r["d_err_med"]) for r in rows], col, dash="4 4")
s.append('</svg>')
out["dagg"] = ''.join(s)

json.dump(out, open("crit_fig4.json", "w"))
print({k: len(v) for k, v in out.items()})
