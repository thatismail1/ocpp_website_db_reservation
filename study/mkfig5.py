"""The collapse figure: hub-C drift term against rho, all five closed-loop
sets, with the closed form 2 R_mm gamma rho / S_b drawn as the prediction."""
import json
import numpy as np
import criterion as CR, mech

W, H = 650, 320
L, RM, T, B = 68, 16, 14, 42
SETS = [("ieee33-fit", "IEEE-33 fit", "#B4442F", 0.0690),
        ("ieee33-hold", "IEEE-33 holdout", "#2E7D8C", 0.0690),
        ("ieee69", "IEEE-69", "#7A6A9B", 0.0463),
        ("synthfront", "synthetic front-loaded", "#C08A1E", 0.0474),
        ("synthback", "synthetic back-loaded", "#2F6B45", 0.0474)]
R = [r for r in json.load(open("mech_rows.json")) if abs(r["band"] - 0.005) < 1e-9]
YMAX = 0.0135
sx = lambda x: L + (W - L - RM) * x
sy = lambda y: H - B - (H - B - T) * y / YMAX
s = [f'<svg viewBox="0 0 {W} {H}" class="ch" role="img">']
for gy in (0, 0.003, 0.006, 0.009, 0.012):
    s.append(f'<line class="grid" x1="{L}" y1="{sy(gy):.1f}" x2="{W-RM}" y2="{sy(gy):.1f}"/>'
             f'<text class="tk" x="{L-8}" y="{sy(gy)+3.5:.1f}" text-anchor="end">{gy:.3f}</text>')
for gx in (0, 0.25, 0.5, 0.75, 1.0):
    s.append(f'<text class="tk" x="{sx(gx):.1f}" y="{H-B+18}" text-anchor="middle">{gx:g}</text>')
# predicted lines, then observed points
for key, lab, col, Raa in SETS:
    sl = 2 * Raa * 90.0 / 1000.0
    s.append(f'<path d="M{sx(0):.1f},{sy(0):.1f} L{sx(1):.1f},{sy(sl):.1f}" fill="none" '
             f'stroke="{col}" stroke-width="1.4" stroke-dasharray="6 4" opacity="0.85"/>')
for key, lab, col, Raa in SETS:
    g = [r for r in R if r["feeder"] == key or r["set"] == key]
    for r in g:
        big = 'n20' in r["file"]
        s.append(f'<circle cx="{sx(r["rho"]):.1f}" cy="{sy(r["d_aggC_p95"]):.1f}" '
                 f'r="{4.6 if big else 3.6}" fill="{"none" if big else col}" '
                 f'stroke="{col}" stroke-width="{2.0 if big else 0}"/>')
s.append(f'<text class="ax" x="{(L+W-RM)/2:.0f}" y="{H-6}" text-anchor="middle">shared-resistance fraction &#961;</text>')
yc = int((T + H - B) / 2)
s.append(f'<text class="ax" x="13" y="{yc}" text-anchor="middle" '
         f'transform="rotate(-90 13 {yc})">D_agg from hub C, p95 (p.u. of u)</text>')
s.append('</svg>')
json.dump({"fig": ''.join(s)}, open("crit_fig5.json", "w"))
print(len(''.join(s)))
