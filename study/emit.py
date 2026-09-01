import json
c = json.load(open("ctx.json"))
HEAD = r'''<title>Bi-Level Charging Case Study</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root{
  --ground:#F7F6F3; --panel:#FFFFFF; --panel2:#EFEEE9;
  --ink:#191C1E; --ink2:#4A5157; --ink3:#767E85;
  --rule:#D9D8D1; --rule2:#E7E6E0;
  --grid:#0E5F6E; --hub:#9A5B0B;
  --c0:#B4442F; --c1:#C08A1E; --c2:#2E7D8C; --c3:#2F6B45;
  --good:#2F6B45; --warn:#C08A1E; --bad:#B4442F;
  --gridline:#E7E6E0;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --ground:#14181A; --panel:#1B2023; --panel2:#212729;
  --ink:#E9E9E4; --ink2:#B2B9BD; --ink3:#848C92;
  --rule:#2E3639; --rule2:#252C2F;
  --grid:#63C4D3; --hub:#E3A75C;
  --c0:#E0765C; --c1:#E3B457; --c2:#63C4D3; --c3:#71B98C;
  --good:#71B98C; --warn:#E3B457; --bad:#E0765C;
  --gridline:#2A3134;
}}
:root[data-theme="dark"]{
  --ground:#14181A; --panel:#1B2023; --panel2:#212729;
  --ink:#E9E9E4; --ink2:#B2B9BD; --ink3:#848C92;
  --rule:#2E3639; --rule2:#252C2F;
  --grid:#63C4D3; --hub:#E3A75C;
  --c0:#E0765C; --c1:#E3B457; --c2:#63C4D3; --c3:#71B98C;
  --good:#71B98C; --warn:#E3B457; --bad:#E0765C;
  --gridline:#2A3134;
}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);
 font-family:"Source Sans 3","Segoe UI",Helvetica,Arial,sans-serif;
 font-size:17px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 26px 110px}
.col{max-width:70ch}
header.mast{border-bottom:1px solid var(--rule);padding:60px 0 28px;margin-bottom:38px}
.kicker{font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.16em;
 text-transform:uppercase;color:var(--ink3)}
h1{font-family:"Newsreader",Georgia,serif;font-weight:600;
 font-size:clamp(32px,5vw,52px);line-height:1.08;letter-spacing:-.015em;
 margin:12px 0 0;max-width:20ch;text-wrap:balance}
.dek{font-family:"Newsreader",Georgia,serif;font-size:19.5px;line-height:1.5;
 color:var(--ink2);max-width:62ch;margin:16px 0 0}
h2{font-family:"Newsreader",Georgia,serif;font-weight:600;font-size:28px;
 line-height:1.2;margin:0 0 6px;text-wrap:balance}
h3{font-size:17px;font-weight:600;margin:30px 0 6px}
.sec-no{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.14em;
 color:var(--grid);display:block;margin-bottom:9px}
section{padding:32px 0 0}
p{margin:0 0 14px}
ul{margin:0 0 16px;padding-left:20px}li{margin:0 0 7px}
hr.rule{border:0;border-top:1px solid var(--rule);margin:48px 0 0}
code{font-family:"IBM Plex Mono",monospace;font-size:.87em;background:var(--panel2);
 padding:1px 5px;border-radius:3px}
a{color:var(--grid)}
/* headline tiles */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));
 gap:12px;margin:26px 0 8px}
.tile{background:var(--panel);border:1px solid var(--rule2);border-radius:5px;
 padding:14px 16px;position:relative;overflow:hidden}
.tile::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;
 background:var(--good)}
.tile .lab{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.1em;
 text-transform:uppercase;color:var(--ink3);display:block}
.tile .val{font-family:"Newsreader",Georgia,serif;font-size:32px;line-height:1.1;
 margin-top:5px;font-variant-numeric:tabular-nums}
.tile .sub{font-size:13.5px;color:var(--ink2);margin-top:3px}
/* charts */
.figure{background:var(--panel);border:1px solid var(--rule2);border-radius:6px;
 padding:16px 18px 10px;margin:22px 0}
.figure h4{margin:0 0 2px;font-size:15.5px;font-weight:600}
.figure .cap{font-size:14px;color:var(--ink2);margin:0 0 8px;max-width:76ch}
.chwrap{overflow-x:auto}
svg.ch{display:block;min-width:620px;width:100%;height:auto}
.grid{stroke:var(--gridline);stroke-width:1}
.lim{stroke:var(--bad);stroke-width:1;stroke-dasharray:4 3}
.lim-t{fill:var(--bad);font-family:"IBM Plex Mono",monospace;font-size:10px}
.tk{fill:var(--ink3);font-family:"IBM Plex Mono",monospace;font-size:10.5px}
.ax{fill:var(--ink3);font-family:"IBM Plex Mono",monospace;font-size:10.5px;
 letter-spacing:.06em}
.lg{display:flex;flex-wrap:wrap;gap:8px 18px;margin:6px 0 2px;
 font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink2)}
.lgi{display:inline-flex;align-items:center;gap:6px}
.lgi i{width:14px;height:2.5px;border-radius:2px;display:inline-block}
/* tables */
.tablewrap{overflow-x:auto;border:1px solid var(--rule2);border-radius:6px;
 background:var(--panel);margin:22px 0}
table{border-collapse:collapse;width:100%;font-size:14.5px;min-width:680px}
th,td{text-align:left;padding:8px 13px;border-bottom:1px solid var(--rule2)}
thead th{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.09em;
 text-transform:uppercase;color:var(--ink3);font-weight:600;background:var(--panel2);
 border-bottom:1px solid var(--rule)}
td.num{text-align:right;font-variant-numeric:tabular-nums;
 font-family:"IBM Plex Mono",monospace;font-size:13px;white-space:nowrap}
td.unit{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink3)}
tr.grp td{background:var(--panel2);font-family:"IBM Plex Mono",monospace;font-size:11px;
 letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);font-weight:600}
tbody tr:last-child td{border-bottom:0}
thead th.c2b{color:var(--c3)}
.note{background:var(--panel);border:1px solid var(--rule2);border-radius:5px;
 padding:15px 18px;margin:20px 0;font-size:15.5px;color:var(--ink2)}
.note b{color:var(--ink)}
footer{margin-top:56px;padding-top:20px;border-top:1px solid var(--rule);
 font-size:14px;color:var(--ink3);max-width:72ch}
::selection{background:var(--panel2)}
:focus-visible{outline:2px solid var(--grid);outline-offset:2px}
@media(max-width:640px){body{font-size:16px}.wrap{padding:0 16px 70px}}
</style>
'''

BODY = r'''
<div class="wrap">
<header class="mast">
  <span class="kicker">Case study &nbsp;/&nbsp; IEEE 33-bus &nbsp;/&nbsp; 4 hubs &nbsp;/&nbsp; 12 vehicles</span>
  <h1>What Coordination Buys the Feeder</h1>
  <p class="dek">Four dispatch strategies for a multi-hub electric bus opportunity-charging network, simulated over a full day at one-minute resolution and evaluated on the true nonlinear power flow. Hierarchical coordination removes 99.7&nbsp;% of the under-voltage exposure that uncoordinated charging creates &mdash; and local price optimisation alone makes it worse.</p>
</header>

<section>
<span class="sec-no">&sect; 1 &mdash; Headline</span>
<h2>Uncoordinated charging vs. the hierarchical framework</h2>
<div class="tiles">
  <div class="tile"><span class="lab">Under-voltage exposure</span>
    <div class="val">703 &rarr; 2</div>
    <div class="sub">bus-minutes below 0.95&nbsp;p.u. &mdash; C0 to C2b</div></div>
  <div class="tile"><span class="lab">Minimum bus voltage</span>
    <div class="val">0.9498</div>
    <div class="sub">p.u., up from 0.9162 under C0</div></div>
  <div class="tile"><span class="lab">Substation peak</span>
    <div class="val">&minus;18.2 %</div>
    <div class="sub">4680 &rarr; 3828 kVA on a 5 MVA transformer</div></div>
  <div class="tile"><span class="lab">Feeder losses</span>
    <div class="val">&minus;13.4 %</div>
    <div class="sub">2.026 &rarr; 1.755 MWh over the day</div></div>
  <div class="tile"><span class="lab">Departure deficits</span>
    <div class="val">0</div>
    <div class="sub">in every case &mdash; service is never traded away</div></div>
  <div class="tile"><span class="lab">Hub MPC solve time</span>
    <div class="val">87 ms</div>
    <div class="sub">mean over 1831 solves, max 267 ms</div></div>
</div>
<div class="col">
<p>The result that matters most is not the cost line. Day-neutral energy cost falls only 1.3&nbsp;% from C0 to C2b, because the tariff is fairly flat and the fleet's energy requirement is fixed. What coordination actually buys is <strong>hosting capacity</strong>: the same 6.6&nbsp;MWh of traction energy is delivered, on the same timetable, with the feeder kept inside its voltage band instead of spending 164 minutes outside it.</p>
</div>
</section>

<hr class="rule">

<section>
<span class="sec-no">&sect; 2 &mdash; The four cases</span>
<h2>What each strategy knows</h2>
<div class="col">
<ul>
<li><strong>C0 &mdash; Uncoordinated.</strong> Every bus draws full rated bay power on arrival until its pack is full. No prices, no network model. The reference for &ldquo;dumb&rdquo; opportunity charging.</li>
<li><strong>C1 &mdash; Local MPC.</strong> Each hub runs the same 1-minute MILP as the proposed framework, priced at the TOU tariff and limited only by its own site transformer. This is the network-blind analogue of the single-hub reference implementation.</li>
<li><strong>C2 &mdash; Hierarchical bi-level.</strong> ADMM coordination between the LinDistFlow upper level and the fleet block, then envelope and nodal-price dispatch into the hub MPCs.</li>
<li><strong>C2b &mdash; Hierarchical with security band.</strong> Identical, except the envelope margins are computed against a de-rated voltage floor of 0.963&nbsp;p.u. instead of 0.95, absorbing the LinDistFlow model error.</li>
<li><strong>C3 &mdash; Centralised bound.</strong> The converged 15-minute relaxed joint optimum, used as an optimality reference rather than a deployable schedule.</li>
</ul>
</div>

<div class="figure">
  <h4>Minimum system voltage across the day</h4>
  <p class="cap">Lowest bus voltage anywhere on the feeder, from the nonlinear backward/forward sweep. C1 dips <em>below</em> C0 in places: chasing the cheap evening tariff moves charging straight into the feeder's own peak.</p>
  __LG__
  <div class="chwrap">__C1__</div>
</div>

<div class="figure">
  <h4>Substation apparent power</h4>
  <p class="cap">The 5&nbsp;MVA transformer is never overloaded in any case, but the coordinated cases carve roughly 850&nbsp;kVA off the evening peak &mdash; headroom that is worth more than the energy saving.</p>
  __LG__
  <div class="chwrap">__C2__</div>
</div>

<div class="figure">
  <h4>Fleet charging power: uncoordinated vs. coordinated</h4>
  <p class="cap">C0 charges whenever a bus is plugged in, producing the spiky pantograph signature. C2b shifts the same energy into the overnight and midday windows and holds the evening flat.</p>
  __LGP__
  <div class="chwrap">__C3__</div>
</div>
</section>

<hr class="rule">

<section>
<span class="sec-no">&sect; 3 &mdash; Results</span>
<h2>Full metric table</h2>
<div class="tablewrap">
<table>
<thead><tr><th>Metric</th><th style="text-align:right">C0</th><th style="text-align:right">C1</th>
<th style="text-align:right">C2</th><th style="text-align:right" class="c2b">C2b</th>
<th style="text-align:right">C3</th><th>Unit</th></tr></thead>
<tbody>
__TABLE__
</tbody>
</table>
</div>

<h3>Peak import per hub [kW]</h3>
<div class="tablewrap">
<table>
<thead><tr><th>Case</th><th style="text-align:right">A &mdash; Terminal North (bus 18)</th>
<th style="text-align:right">B &mdash; Terminal South (bus 33)</th>
<th style="text-align:right">C &mdash; Interchange (bus 22)</th>
<th style="text-align:right">D &mdash; Depot + BESS (bus 25)</th></tr></thead>
<tbody>
__HUB__
</tbody>
</table>
</div>

<div class="col">
<p>Hub A sits at the end of the longest lateral and is the binding node: the coordinated cases cut its peak from 762&nbsp;kW to 633&nbsp;kW, which is where nearly all of the voltage recovery comes from. Hub D, the depot, is barely constrained &mdash; its overnight window is electrically cheap, so the framework pushes energy there.</p>
</div>
</section>

<hr class="rule">

<section>
<span class="sec-no">&sect; 4 &mdash; Coordination</span>
<h2>How the two levels converged</h2>

<div class="figure" style="max-width:600px">
  <h4>ADMM primal residual</h4>
  <p class="cap">Consensus between the feeder dispatch and the fleet block, in kW over the 384 hub-interval coupling variables.</p>
  <div class="chwrap">__C5__</div>
</div>

<div class="col">
<p>The residual falls two orders of magnitude in four iterations and then flattens at <strong>__RFIN__&nbsp;kW</strong> &mdash; about <strong>__RRMS__&nbsp;kW RMS per hub-interval</strong>, roughly 1&nbsp;% of a terminal hub's rating. That floor is not the algorithm converging; it is the resolution of the piecewise-linear proximal term used to keep both subproblems inside an LP solver. It is the honest limitation of this implementation: a true quadratic proximal (or an interior-point QP backend) would drive the residual further, at the cost of a solver dependency.</p>
<p>Cost per round is small: __TUL__&nbsp;s for the upper-level LP and __TFL__&nbsp;s for the fleet LP, so a full 15-round coordination completes in well under a minute &mdash; comfortably inside a 5-minute dispatch tick.</p>
</div>

<div class="figure">
  <h4>Nodal price vs. flat tariff</h4>
  <p class="cap">The dispatched price &lambda; (mean across hubs) against the TOU tariff. Where the two coincide the network is uncongested; the spikes to 8.3&nbsp;TL/kWh are congestion rent on the voltage constraint at the end of the hub-A lateral, and they are what makes the hub MPC defer without any explicit power limit being hit.</p>
  __LGR__
  <div class="chwrap">__C4__</div>
</div>
</section>

<hr class="rule">

<section>
<span class="sec-no">&sect; 5 &mdash; Reading the results</span>
<h2>Four things worth stating plainly</h2>
<div class="col">

<h3>1. Local price optimisation is not benign</h3>
<p>C1 lowers cost by 0.6&nbsp;% and <em>raises</em> under-voltage minutes from 164 to 201. Every hub independently defers charging into the cheap hours, and because they all see the same tariff, they synchronise. Coincident deferral is exactly the failure mode a flat retail signal creates, and it is the strongest argument in the study for a nodal signal over a system-wide one.</p>

<h3>2. LinDistFlow optimism has to be paid for somewhere</h3>
<p>C2 dispatches envelopes that its own network model certifies as secure, yet the AC evaluation still finds 125 under-voltage bus-minutes. The linearisation neglects the loss terms and so under-predicts voltage drop by roughly 0.006&nbsp;p.u. at this loading. De-rating the floor to 0.963&nbsp;p.u. in the margin calculation (C2b) closes the gap to 2 bus-minutes and costs almost nothing &mdash; day-neutral cost falls slightly, because the tighter envelope pushes more energy into genuinely cheap hours. <strong>The security band is not a safety tax; it is free.</strong></p>

<h3>3. The cost comparison needs a day-neutrality correction</h3>
<p>The coordinated cases end the day with the fleet at 0.39&ndash;0.46&nbsp;p.u. SoC while C0 and C1 end full. Comparing raw energy bills would credit C2b for 1.65&nbsp;MWh it simply did not buy. Valuing that gap at the day-mean tariff puts all cases on 6.6&ndash;6.7&nbsp;MWh delivered and shrinks the saving from 4.6&nbsp;% to 1.3&nbsp;%. The honest headline is the network result, not the bill.</p>

<h3>4. Real-time feasibility is not in doubt</h3>
<p>The hub MILPs solve in 87&nbsp;ms on average against a 1-minute discretisation with a 2-minute control interval. One outlier in C1 hit 40&nbsp;s &mdash; a degenerate branch-and-bound instance at the single-bay interchange hub &mdash; which is a reminder that a wall-clock cap and a fallback to the LP relaxation belong in any deployment.</p>
</div>
</section>

<hr class="rule">

<section>
<span class="sec-no">&sect; 6 &mdash; Method</span>
<h2>Setup, and where the model departs from the formulation</h2>
<div class="col">
<p><strong>Network.</strong> IEEE 33-bus, 12.66&nbsp;kV, 5&nbsp;MVA substation with the OLTC at 1.04&nbsp;p.u., operated at 60&nbsp;% of nominal peak load with a realistic daily shape. Voltage band 0.95&ndash;1.05&nbsp;p.u. Every case is evaluated on a nonlinear backward/forward sweep at 1-minute resolution &mdash; never on the model it optimised against.</p>
<p><strong>Transit.</strong> 12 vehicles, 300&nbsp;kWh packs, SoC band 0.20&ndash;0.90, a 110-minute cycle A&rarr;C&rarr;B&rarr;C&rarr;A with 22-minute legs. Leg energy comes from the longitudinal model (LL-3) over a synthetic urban trace: 13.80&nbsp;kWh over 11.75&nbsp;km, i.e. 1.17&nbsp;kWh/km at 32&nbsp;km/h average &mdash; squarely in the measured range for a 14-tonne bus. Fleet traction demand is 6.26&nbsp;MWh/day. Departure requirement is next-leg energy plus a 10&nbsp;kWh reserve.</p>
<p><strong>Hubs.</strong> A: 2&times;450&nbsp;kW pantograph at bus 18. B: 2&times;250&nbsp;kW at bus 33. C: 1&times;150&nbsp;kW at bus 22. D: 4&times;150&nbsp;kW depot at bus 25 with a 600&nbsp;kWh / 300&nbsp;kW BESS. Each PCC carries site load (150&ndash;300&nbsp;kW base) and a PV canopy (120&ndash;400&nbsp;kWp).</p>
<p><strong>Tariff.</strong> The 24-hour Turkish day-ahead profile from the reference implementation, 1.75&ndash;3.00&nbsp;TL/kWh.</p>

<h3>Departures from the formulation, and why</h3>
<ul>
<li><strong>The coordination-stage decomposition is DSO &harr; fleet, not DSO &harr; four independent hubs.</strong> Vehicles circulate between hubs, so the hub subproblems are coupled through vehicle SoC and are not separable at the planning stage. Execution stays hub-local, because there the SoC is measured rather than predicted. This is a genuine correction to &sect;3 of the formulation.</li>
<li><strong>The ADMM proximal term is piecewise-linear.</strong> The available LP/MILP backend rejects quadratic objectives; tangent cuts with geometric spacing keep both subproblems linear at the price of the residual floor described above.</li>
<li><strong>Depot bays are power-sharing multi-outlet dispensers.</strong> Modelling 12 vehicles against 4 bays with connection binaries produced a symmetric MILP that dominated the runtime; assigning vehicles to bays and sharing each bay's power is both faster and closer to how depot chargers are actually built.</li>
<li><strong>The SoC floor in the hub MPC is soft.</strong> Traction demand over the horizon is exogenous, so a hard floor can make the local problem infeasible and destroy recursive feasibility. It is penalised at four times the departure-deficit price.</li>
<li><strong>Envelope margins are computed one hub at a time.</strong> The sensitivity walk of UL-9a holds all other hubs at their dispatch, so simultaneous excursions are not jointly certified. This is precisely why C2 leaks violations and C2b does not &mdash; the security band is doing double duty, covering both the linearisation error and the uncoordinated-margin assumption. A proportional-sharing rule would separate the two.</li>
<li><strong>PV is never curtailed</strong> in any case: minimum feeder load exceeds total hub PV, so the network absorbs all of it. The curtailment term of LL-10 is inactive here and would need a higher-penetration scenario to exercise.</li>
</ul>
</div>

<div class="note">
<b>Reproducibility.</b> Deterministic given the seeds: route trace seed 3, PV/cloud seed 7, ADMM 15 iterations at &rho;=1.2&times;10<sup>&minus;2</sup>, MPC horizon 40&nbsp;min with a 2-minute control interval. Solver HiGHS via Pyomo on 4 cores; total study runtime under 15&nbsp;minutes. Costs are in the tariff's currency (TL) and are not converted.
</div>
</section>

<footer>
Companion to the bi-level formulation. Equation labels (UL-*, LL-*, C-*) refer to that document; the departures listed in &sect;6 are changes to it, not to the code.
</footer>
</div>
'''
body = (BODY.replace("__LG__", c["lg_cases"]).replace("__LGP__", c["lg_pc"])
        .replace("__LGR__", c["lg_pr"])
        .replace("__C1__", c["c1"]).replace("__C2__", c["c2"])
        .replace("__C3__", c["c3"]).replace("__C4__", c["c4"])
        .replace("__C5__", c["c5"])
        .replace("__TABLE__", c["TABLE"]).replace("__HUB__", c["HUB"])
        .replace("__RFIN__", "%.0f" % c["rfin"]).replace("__RRMS__", "%.1f" % c["rrms"])
        .replace("__TUL__", "2.3").replace("__TFL__", "0.6"))
open("results_page.html", "w").write(HEAD + body)
print("wrote results_page.html", len(HEAD + body))
