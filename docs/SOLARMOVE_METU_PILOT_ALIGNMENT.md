# SOLAR-MOVE ↔ METU Campus Pilot: Alignment & Adaptation Plan

Source: SOLAR-MOVE proposal v0.7 (HORIZON-CL5-2024-D3-02-05), Part B.
Target: this repository (OCPP 1.6 CSMS + dashboard + reservations) as the software
backbone of the METU campus pilot.

---

## 1. What the proposal actually commits METU to

METU appears in the Turkish pilot as **both** a VIPV site and an ePIPV site:

| Ref | Commitment | Lead |
|-----|-----------|------|
| T4.3 | Passenger VIPV bus pilot (TK), bus on a METU campus line, operated by METU Rectorship | Bozankaya (P: METU, Strath, SonoM, iTech, LIST, GUNAM) |
| T5.2 | **ePIPV Bus Opportunity charging (TK pilot)**, M13–M39 | **METU** (P: Strath, Bozankaya) |
| T3.4 | ePIPV Bus Depot energy management — opportunity charging with PV, optimising charging *and bus scheduling* (simulation) | METU contribution |
| T3.5 | Hardware supporting ePIPV development | INESC ID, P: METU |
| SOL15 (ii) | ePIPV **planning/design tool for passenger bus depots**, accounting for fleet usage and parking types — TRL5→7 | METU |
| SOL16 (ii) | ePIPV **optimal operation tool for bus depots** — forecasting, look-ahead optimisation, control — TRL5→7 | METU |
| O5.2 | "Investigate innovative opportunity **fast (50 kW)** charging for public transportation (TK)" | METU |

Physical scope stated in the proposal:
- One **50 kW DC fast charger** on METU's existing distribution network.
- Campus microgrid already hosting PV at **50 / 200 / 220 / 230 kW**, sited near the shuttle routes; >100 kW referenced as already installed.
- Ring shuttle network, **08:00–20:30**, free to students/visitors.
- **Eight shuttle services / six weekday routes** (2 business-hours, 2 morning, 2 night; weekend 1 day + 1 night). Business-hours headway **15–20 min**, others 1–2/hour.
- Pyranometer on existing diesel shuttles to classify routes by PV-generation potential.
- Hourly passenger counts collected, linked to bus load.

Charging strategies to be **implemented and compared**:
1. Fixed-interval opportunity charging (e.g. 10 or 15 min),
2. Green-optimised charging (longer sessions aligned to high PV generation),
3. Baseline overnight depot charging (single session).

Project-level KPIs this pilot must feed (Table 1.1 / project targets): grid-dependency
reduction of **20–50 %**, VIPV range gain **5–10 km/day**, positive NPV, and TRL 5→7 for
SOL15/SOL16.

---

## 2. Honest read: how well does this repo fit?

**What already fits well.**
- OCPP 1.6-J central system over WebSocket (`backend/ocpp/ocpp_server.py`) with
  BootNotification, Heartbeat, Authorize, Start/StopTransaction, MeterValues,
  StatusNotification. That is exactly the interface a 50 kW DC charger will speak.
- A real meter-value pipeline: per-phase power, reactive power, power factor, voltage,
  frequency, delivered/supplied energy, persisted to SQLite (`MeterLog` in
  `backend/ocpp/db.py`). This is the *right* granularity for T5.2 evidence — most pilots
  only log session kWh and then cannot answer the reviewer's questions.
- Vendor normalisation already handled (LIVOLTEK kWh vs Schneider/EVlink Wh) — the kind of
  detail that otherwise silently corrupts a 27-month dataset.
- A `Reservation` + `BlockedTimeSlot` schema already exists. Reservation is the natural
  data structure for a *bus charging slot*, which is the core of opportunity charging.
- Auth, quotas, dashboards, logs, history endpoints — enough to run the site day to day.

**What is missing or wrong for the pilot.**

1. **The reservation API does not exist.** The frontend calls
   `/api/user/reservations`, `/api/user/reservations/availability`, and
   `DELETE /api/user/reservations/{id}` (`frontend/src/components/reservations/*.js`),
   but `backend/server.py` defines none of them — grep for `reservation` in the backend
   returns nothing outside `db.py`. The reservation feature is currently a UI shell over a
   schema, with no server in between. This is the single most concrete blocker.
2. **No PV / irradiance data model at all.** There is no table, no ingestion, no endpoint
   for the 50/200/220/230 kW arrays or for the pyranometer. Without it, "green-optimised
   charging" cannot be implemented, and the grid-dependency KPI (20–50 %) cannot be
   computed — you would have no denominator.
3. **No smart charging.** Only `RemoteStartTransaction` is used. OCPP 1.6
   `SetChargingProfile` / `ChangeConfiguration` are absent, so the platform can currently
   only start and stop — it cannot modulate power to follow a PV curve. Both of METU's
   TRL5→7 solutions (SOL16 especially) require modulation, not just scheduling.
4. **No fleet/route/timetable domain.** Nothing represents shuttle routes, headways,
   trips, state of charge, or passenger counts. T3.4 explicitly requires optimising
   *charging and bus scheduling* jointly; SOL15 requires fleet usage and parking types.
5. **No forecasting layer.** SOL16 names forecasting (production, consumption, EV
   profiles), look-ahead optimisation, and control as required components.
6. **Users are a CSV.** `backend/data/users1.csv` with kWh quotas is a campus-permit model,
   not a fleet model. A bus is not a quota-limited user.
7. **Operational risk.** JSON files (`active_transactions.json`, `charger_status.json`) as
   live state alongside SQLite; no migrations; `backend/backflip.py` is empty; the OCPP
   server binds a plain `ws://` port with no TLS and no per-charger auth. For a 27-month
   demonstrator that must not lose data, this is the weak spot.

**Verdict.** The repo is a good *CSMS foundation* — roughly 60 % of what a T5.2 platform
needs on the charging side, and close to 0 % on the PV, scheduling, and optimisation side.
It is worth adapting rather than replacing: rewriting the OCPP layer would be a waste of
work that already exists and already talks to real hardware.

---

## 3. What I'd actually do — three layers

### Layer A — Make the pilot recordable (do this first, before the bus arrives)

The M13 hardware date is the deadline you cannot move. Everything here is cheap and
unblocks data collection.

- **A1. Implement the reservation endpoints** that the UI already calls. Add
  `GET/POST /api/user/reservations`, `GET /api/user/reservations/availability`,
  `DELETE /api/user/reservations/{reservation_id}`, plus admin listing. Enforce no
  overlapping reservations per charger and honour `BlockedTimeSlot`. Reuse the existing
  `reservation_to_dict` / `blocked_slot_to_dict` helpers.
- **A2. Add a `PvProduction` table and ingestion.** Columns: `plant_id`, `timestamp`,
  `ac_power_kw`, `irradiance_w_m2`, `poa_irradiance`, `module_temp`, `source`. Backfill the
  four campus arrays from whatever the existing monitoring exposes; if it exposes nothing
  machine-readable, that is a procurement item to raise now, not at M13.
- **A3. Add a `RouteIrradiance` table** for the pyranometer-on-diesel-shuttle campaign:
  `route_id`, `timestamp`, `lat`, `lon`, `ghi_w_m2`, `vehicle_id`. This is the dataset that
  makes the "practical benchmarking tool" claim in the proposal real, and it can start
  collecting **before** any VIPV bus exists. Highest evidence-per-euro item in the pilot.
- **A4. Add `PassengerCount`** (`route_id`, `trip_start`, `hour`, `count`) — the proposal
  ties passenger numbers to bus load and to VIPV route viability.
- **A5. Grid-import metering.** Log the site's import/export separately from charger meter
  values. Without this, "reduce dependency on the grid by 20–50 %" is unverifiable and the
  reviewers will say so.
- **A6. Harden.** Alembic migrations, `wss://` + per-charger identity on the OCPP port,
  move `active_transactions.json` state into SQLite, and a nightly DB backup. 27 months of
  irreplaceable pilot data should not sit behind an unauthenticated `ws://`.

### Layer B — Make it a bus-depot platform (SOL15 / SOL16 groundwork)

- **B1. Fleet domain model.** `Vehicle` (bus, capacity kWh, usable SoC window, PV area for
  the VIPV bus), `Route`, `Trip` (scheduled start/end, route, vehicle), `ChargingSlot`
  (specialised reservation bound to a `Trip` gap rather than a person). Encode the real
  timetable: 08:00–20:30, six weekday routes, 15–20 min business-hours headway.
- **B2. OCPP smart charging.** Implement `SetChargingProfile`, `ClearChargingProfile`,
  `GetCompositeSchedule` and `ChangeConfiguration` as CSMS→charger calls, with a profile
  store keyed by charger and validity window. This is the mechanism that turns a strategy
  into a physical kW setpoint, and it is the TRL 5→7 step.
- **B3. Strategy engine with three pluggable strategies**, matching the proposal one-to-one:
  `fixed_interval` (10 / 15 min, parameterised), `green_optimised` (windows selected from
  the PV forecast), `overnight_depot` (baseline). Each run writes a labelled experiment
  record so results are comparable. Make the strategy a first-class DB object with a
  campaign id — you will be A/B-ing them across seasons for two years.
- **B4. Forecast service.** Day-ahead PV production per array (persistence + clear-sky, then
  a learned model once you have a season of data), shuttle energy demand per trip from
  historical MeterLog + passenger counts, and a SoC projection per bus.
- **B5. Look-ahead optimiser.** A rolling MILP/heuristic over the next 24 h: decide, for
  each inter-trip gap, whether to charge and at what power, maximising PV self-consumption
  and respecting the hard constraint that **no scheduled trip may be missed**. Feasibility
  of the timetable is a constraint, never an objective term — a bus depot pilot that
  strands passengers is a failed pilot regardless of its KPI numbers.

### Layer C — Make it produce deliverable evidence

- **C1. KPI service** computing, per day/week/month: PV self-consumption %, grid-import
  energy, grid dependency reduction vs. the overnight baseline, peak import kW, energy cost
  under Turkish tariffs, and CO₂ avoided. These map directly to the SO/KPI table and to WP6
  (T6.1 LCA, T6.2 CBA).
- **C2. Experiment/campaign dashboard** — one screen that shows "strategy X ran on these
  dates, here is the PV overlay, here is grid import, here is the delta". This is what you
  screenshot into D5.x.
- **C3. Data export** (CSV/Parquet + a documented schema) for Strathclyde, LIST, and DTU.
  Strath is a partner in T5.2 and DTU needs hourly profiles for the PyPSA-Eur work in T3.6.
  Agreeing the export schema early is much cheaper than reconciling it at M30.
- **C4. Digital-twin / simulation mode.** T3.4 lists the Turkish bus-depot work as
  *simulation*. Let the same strategy engine run against synthetic or replayed data with no
  hardware attached — that de-risks the whole schedule, because you can develop and publish
  SOL16 results even if the bus or charger is late.

---

## 4. Sequencing against the project calendar

| Window | Focus |
|--------|-------|
| Now → M12 | Layer A in full. Start pyranometer + passenger-count collection immediately — it needs no bus. Freeze the data schema and agree exports with Strath/DTU/LIST. |
| M13 → M18 | Charger commissioning; B1–B2. Run `overnight_depot` as the measured **baseline** — a baseline collected after you start optimising is worthless. |
| M18 → M27 | B3–B5 in operation. Rotate strategies on a fixed schedule so seasons are covered evenly. Feed SOL15/SOL16 TRL evidence. |
| M27 → M39 | Layer C; hand data to WP6 (LCA/CBA) and WP7; write up the benchmark dataset. |

---

## 5. The three decisions worth making early

1. **Baseline before optimisation.** Reserve a genuine measurement period for overnight
   depot charging. Every comparative claim in T5.2 rests on it.
2. **Seasonal symmetry.** Ankara swings from sub-zero to >30 °C, which the proposal itself
   cites as the reason the site generalises to Europe. Rotate strategies *within* each
   season rather than running one strategy per season, or the comparison confounds strategy
   with weather.
3. **Simulation parity.** Build the simulation path (C4) as the same code path as live
   operation, not a separate script. It is the only insurance against hardware slipping.

---

## 6. Risks specific to this pilot

- **One charger, one bus** is a very small n. Mitigate with the simulation mode and with
  the route-irradiance campaign across all eight shuttle services, which gives fleet-scale
  evidence from a single-vehicle demonstrator.
- **A free campus shuttle has no price signal**, so cost-based optimisation is synthetic.
  Be explicit in the CBA about which tariff is assumed and why.
- **PV monitoring access.** The four arrays predate this project and may not expose an API.
  Resolve before M13.
- **Missing endpoints today** means the reservation feature is untested against real users.
  Fix it early so the campus community is habituated to the tool before the pilot starts.

---

## 7. Summary

Adapt, don't rebuild. The OCPP layer, the meter-value pipeline, and the reservation schema
are genuinely useful assets. The gap is that this is currently a *charging-point management
system*, and T5.2 needs a *PV-aware bus depot energy management system*. The distance
between those two is: a working reservation API, a PV/irradiance data model, OCPP smart
charging profiles, a fleet/timetable domain, a forecast + look-ahead optimiser, and a KPI
layer. In that order — and the first three are small enough to finish before the hardware
lands.
