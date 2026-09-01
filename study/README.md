# Hierarchical bi-level opportunity-charging case study

IEEE 33-bus feeder, four charging hubs, twelve electric buses, one day at
one-minute resolution. Four dispatch strategies are compared and every one of
them is evaluated on a nonlinear backward/forward-sweep power flow, never on
the model it optimised against.

| module | contents |
|---|---|
| `system.py` | 33-bus branch/load data, hub definitions, exogenous profiles (tariff, PV, site and feeder load) |
| `powerflow.py` | backward/forward-sweep AC power flow, vectorised over the 1440 time steps |
| `transit.py` | longitudinal bus model (LL-3), route energy, timetable, dwell indicators |
| `opt.py` | upper-level LinDistFlow LP (UL-1..UL-10), fleet LP for ADMM (C-3), hub MILP MPC (LL-1..LL-10) |
| `run.py` | staged runner: ADMM coordination, envelope dispatch, closed-loop simulation, evaluation |
| `report.py` | metric table and `series.json` export |
| `mkpage.py`, `emit.py` | chart and results-page generation |

## Reproducing

```bash
pip install numpy scipy pyomo highspy
cd study
python3 run.py admm       # ADMM coordination -> admm.pkl
python3 run.py admm_sb    # security-band envelope -> admm_sb.pkl
python3 run.py C0         # uncoordinated baseline
python3 run.py C1         # local MPC, TOU price, site cap only
python3 run.py C2         # hierarchical bi-level
python3 run.py C2b        # hierarchical + 0.963 p.u. security band
python3 run.py bound      # centralised 15-min relaxed bound
python3 run.py pack && python3 report.py
```

Deterministic given the seeds (route trace 3, PV/cloud 7). Total runtime is
under 15 minutes on 4 cores.

## Headline result

Against uncoordinated charging, the hierarchical framework with a security
band cuts under-voltage exposure from 703 to 2 bus-minutes, lifts the minimum
bus voltage from 0.9162 to 0.9498 p.u., drops the substation peak 18.2 % and
feeder losses 13.4 %, with zero departure-SoC deficits and an 87 ms mean hub
MPC solve time. Day-neutral energy cost falls 1.3 %; the network result, not
the bill, is the case for coordination.

Local price-only MPC (C1) lowers cost slightly but *increases* under-voltage
minutes from 164 to 201: a system-wide tariff makes hubs defer in unison.

Known limitations are documented in the results page and in the module
docstrings: the ADMM proximal term is piecewise-linear (residual floor of
17 kW RMS per hub-interval), envelope margins are computed one hub at a time,
and the coordination-stage decomposition is DSO to fleet rather than DSO to
independent hubs, because vehicles circulating between hubs couple the hub
subproblems through vehicle SoC.
