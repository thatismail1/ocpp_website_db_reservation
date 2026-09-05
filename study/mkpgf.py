"""Generate pgfplots figure sources for the paper from the result JSONs."""
import json, os
import numpy as np

OUT = "paper/figs"
os.makedirs(OUT, exist_ok=True)
M = [r for r in json.load(open("mech_rows.json")) if abs(r["band"] - 0.005) < 1e-9]
SETS = [("ieee33-fit", "IEEE 33 (set A)", "c1", 0.0690),
        ("ieee33-hold", "IEEE 33 (set B)", "c2", 0.0690),
        ("ieee69", "IEEE 69", "c3", 0.0463),
        ("synthfront", "S-front", "c4", 0.0474),
        ("synthback", "S-back", "c5", 0.0474)]


def coords(pts, fmt="({:.4f},{:.5f})"):
    return " ".join(fmt.format(a, b) for a, b in pts)


def wrap(body, w="\\columnwidth"):
    return ("\\begin{tikzpicture}\n" + body + "\n\\end{tikzpicture}\n")


# ---------------------------------------------------------------- Fig: collapse
b = ["\\begin{axis}[width=\\columnwidth,height=0.72\\columnwidth,",
     "  xlabel={shared-resistance fraction $\\rho$},",
     "  ylabel={$D_{\\mathrm{agg}}^{C}$ p95 [p.u.]},",
     "  xmin=0,xmax=1,ymin=0,ymax=0.0135,grid=major,",
     "  legend style={font=\\scriptsize,at={(0.02,0.98)},anchor=north west,draw=none,fill=none},",
     "  legend cell align=left,tick label style={font=\\scriptsize},label style={font=\\small}]"]
for key, lab, col, Raa in SETS:
    sl = 2 * Raa * 90.0 / 1000.0
    b.append(f"\\addplot[{col},dashed,forget plot,thick] coordinates {{(0,0) (1,{sl:.5f})}};")
for key, lab, col, Raa in SETS:
    g = sorted([r for r in M if r["feeder"] == key or r["set"] == key], key=lambda r: r["rho"])
    small = [(r["rho"], r["d_aggC_p95"]) for r in g if "n20" not in r["file"]]
    b.append(f"\\addplot[{col},only marks,mark=*,mark size=1.4] coordinates {{{coords(small)}}};")
    b.append(f"\\addlegendentry{{{lab}}}")
big = [(r["rho"], r["d_aggC_p95"]) for r in M if "n20" in r["file"]]
b.append(f"\\addplot[black,only marks,mark=o,mark size=2.4] coordinates {{{coords(big)}}};")
b.append("\\addlegendentry{20-vehicle runs}")
b.append("\\end{axis}")
open(f"{OUT}/fig_collapse.tex", "w").write(wrap("\n".join(b)))

# ------------------------------------------------------------ Fig: closed loop
b = ["\\begin{axis}[width=\\columnwidth,height=0.72\\columnwidth,",
     "  xlabel={shared-resistance fraction $\\rho$},",
     "  ylabel={violating minutes (AC sweep)},",
     "  xmin=0,xmax=1,ymin=0,grid=major,",
     "  legend style={font=\\scriptsize,at={(0.02,0.98)},anchor=north west,draw=none,fill=none},",
     "  legend cell align=left,tick label style={font=\\scriptsize},label style={font=\\small}]"]
for key, lab, col, _ in SETS:
    g = sorted([r for r in M if r["feeder"] == key or r["set"] == key], key=lambda r: r["rho"])
    b.append(f"\\addplot[{col},mark=*,mark size=1.4,thick] coordinates "
             f"{{{coords([(r['rho'], r['viol_min']) for r in g], '({:.4f},{:.0f})')}}};")
    b.append(f"\\addlegendentry{{{lab}}}")
b.append("\\end{axis}")
open(f"{OUT}/fig_closedloop.tex", "w").write(wrap("\n".join(b)))

# ------------------------------------------------------- Fig: static boundary
bnd = json.load(open("crit_fig2.json"))["bnd"]
R = json.load(open("crit_rows.json"))
b = ["\\begin{axis}[width=\\columnwidth,height=0.72\\columnwidth,",
     "  xlabel={shared-resistance fraction $\\rho$},",
     "  ylabel={required planning band [p.u.]},",
     "  xmin=0,xmax=1,ymin=0,ymax=0.035,grid=major,",
     "  legend style={font=\\scriptsize,at={(0.02,0.98)},anchor=north west,draw=none,fill=none},",
     "  legend cell align=left,tick label style={font=\\scriptsize},label style={font=\\small}]"]
for mode, col, lab in (("naive", "c1", "one-at-a-time allocation"),
                       ("joint", "c3", "jointly certified allocation")):
    b.append(f"\\addplot[{col},mark=*,mark size=1.4,thick] coordinates "
             f"{{{coords([(a, c) for a, c in bnd[mode]])}}};")
    b.append(f"\\addlegendentry{{{lab}}}")
b.append("\\addplot[black,dotted,thick] coordinates {(0,0.005) (1,0.005)};")
b.append("\\addlegendentry{a 0.005 p.u. band}")
b.append("\\end{axis}")
open(f"{OUT}/fig_boundary.tex", "w").write(wrap("\n".join(b)))

# ------------------------------------------------- Fig: slack and drift split
b = ["\\begin{axis}[width=\\columnwidth,height=0.72\\columnwidth,",
     "  xlabel={shared-resistance fraction $\\rho$},",
     "  ylabel={p.u. of $u$},",
     "  xmin=0,xmax=1,ymin=0,ymax=0.02,grid=major,",
     "  legend style={font=\\scriptsize,at={(0.98,0.98)},anchor=north east,draw=none,fill=none},",
     "  legend cell align=left,tick label style={font=\\scriptsize},label style={font=\\small}]"]
for key, lab, col, _ in SETS[:3]:
    g = sorted([r for r in M if r["feeder"] == key or r["set"] == key], key=lambda r: r["rho"])
    b.append(f"\\addplot[{col},mark=square*,mark size=1.3,thick] coordinates "
             f"{{{coords([(r['rho'], r['slack_p5']) for r in g])}}};")
    b.append(f"\\addlegendentry{{slack p5, {lab}}}")
for key, lab, col, _ in SETS[:3]:
    g = sorted([r for r in M if r["feeder"] == key or r["set"] == key], key=lambda r: r["rho"])
    b.append(f"\\addplot[{col},dashed,mark=triangle*,mark size=1.3] coordinates "
             f"{{{coords([(r['rho'], r['d_agg_p95']) for r in g])}}};")
    b.append(f"\\addlegendentry{{$D_{{\\mathrm{{agg}}}}$ p95, {lab}}}")
b.append("\\end{axis}")
open(f"{OUT}/fig_split.tex", "w").write(wrap("\n".join(b)))
print("wrote", os.listdir(OUT))
