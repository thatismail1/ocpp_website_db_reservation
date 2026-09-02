"""Transit layer: longitudinal bus model (LL-3), route energy, and the
timetable that produces the dwell indicators a_{b,tau} at each hub."""
from __future__ import annotations
import os
import numpy as np
from dataclasses import dataclass
from typing import List
import system as S

# ------------------------------------------------------- vehicle physics ----
@dataclass
class BusParams:
    mass_kg: float = 14000.0
    frontal_area_m2: float = 8.18
    drag_coeff: float = 0.63
    rolling_res_coeff: float = 0.010
    air_density: float = 1.225
    gravity: float = 9.81
    driveline_eff: float = 0.95
    motor_eff: float = 0.92
    batt_eff_dis: float = 0.95
    batt_eff_chg: float = 0.95
    max_motor_kw: float = 140.0
    max_regen_kw: float = 80.0
    aux_kw: float = 6.0
    rot_mass_factor: float = 1.05


def synthetic_urban_cycle(duration_s: int, seed: int = 3):
    """Stop-and-go urban bus speed trace [m/s] with a grade profile [rad]."""
    rng = np.random.default_rng(seed)
    v, t = [], 0
    while t < duration_s:
        cruise = rng.uniform(11.0, 15.5)              # m/s (40-56 km/h)
        acc_t = int(rng.uniform(9, 15))
        cru_t = int(rng.uniform(25, 70))
        dec_t = int(rng.uniform(8, 13))
        dwell = int(rng.uniform(12, 26))              # bus stop
        v += list(np.linspace(0, cruise, acc_t))
        v += [cruise] * cru_t
        v += list(np.linspace(cruise, 0, dec_t))
        v += [0.0] * dwell
        t = len(v)
    v = np.array(v[:duration_s])
    grade = 0.020 * np.sin(2 * np.pi * np.arange(duration_s) / 900.0)
    return v, grade


def leg_energy_kwh(v, grade, p=BusParams(), dt_s=1.0):
    """Integrate the longitudinal model -> (energy kWh, distance km)."""
    a = np.zeros_like(v); a[1:] = np.diff(v) / dt_s; a[0] = a[1]
    F = (p.rot_mass_factor * p.mass_kg * a
         + p.mass_kg * p.gravity * p.rolling_res_coeff * np.cos(grade)
         + 0.5 * p.air_density * p.drag_coeff * p.frontal_area_m2 * v ** 2
         + p.mass_kg * p.gravity * np.sin(grade))
    pm = np.clip(F * v / 1000.0, -p.max_regen_kw, p.max_motor_kw)
    pb = np.where(pm >= 0,
                  pm / (p.driveline_eff * p.motor_eff * p.batt_eff_dis),
                  pm * p.driveline_eff * p.motor_eff * p.batt_eff_chg) + p.aux_kw
    return float(pb.sum() * dt_s / 3600.0), float(v.sum() * dt_s / 1000.0)


# ------------------------------------------------------------- timetable ----
E_VEH_KWH = 300.0
SOC_MIN, SOC_MAX = 0.20, 0.90
SOC_START = 0.85
ETA_CHG = 0.95
E_RESERVE_KWH = 10.0

DWELL = {"A": 8, "B": 8, "C": 3, "D": 0}     # minutes at each hub
LEG_MIN = 22                                  # driving minutes per leg
N_VEH = int(os.environ.get("N_VEH", 12))
SERVICE_START, SERVICE_END = 5 * 60, 23 * 60  # 05:00 - 23:00
DEPOT_IN, DEPOT_OUT = 23 * 60 + 30, 4 * 60 + 40


@dataclass
class Event:
    veh: int
    hub: int          # index into S.HUBS
    arr: int          # minute of arrival (dwell start)
    dep: int          # minute of departure
    e_next: float     # energy of the leg that follows this dwell [kWh]


def build_timetable(leg_kwh: float):
    """Cycle  A -(leg)- C -(leg)- B -(leg)- C -(leg)- A , staggered fleet."""
    seq = [("A", DWELL["A"]), ("C", DWELL["C"]), ("B", DWELL["B"]), ("C", DWELL["C"])]
    cycle = sum(d for _, d in seq) + 4 * LEG_MIN            # 110 min
    events: List[Event] = []
    headway = cycle // N_VEH * 1                            # stagger
    for b in range(N_VEH):
        offset = (b * cycle) // N_VEH
        # half the fleet starts at the southern terminal
        rot = 0 if b % 2 == 0 else 2
        t = SERVICE_START + offset
        i = rot
        while t < SERVICE_END:
            hub_c, dw = seq[i % 4]
            h = S.HUB_IDX[hub_c]
            arr, dep = t, t + dw
            if dep > SERVICE_END:
                break
            events.append(Event(b, h, arr, dep, leg_kwh))
            t = dep + LEG_MIN
            i += 1
        # depot dwells: pre-service (00:00 -> pull-out) and post-service
        events.append(Event(b, S.HUB_IDX["D"], 0, DEPOT_OUT, 0.0))
        events.append(Event(b, S.HUB_IDX["D"], DEPOT_IN, 24 * 60 - 1, 0.0))
    return events, cycle


def availability(events, K=S.K_DAY, nh=len(S.HUBS), nv=N_VEH):
    """a[h,b,k] in {0,1}: vehicle b berthed at hub h at minute k."""
    a = np.zeros((nh, nv, K), dtype=np.int8)
    for e in events:
        a[e.hub, e.veh, e.arr:e.dep] = 1
    return a


def drive_energy(events, leg_kwh, K=S.K_DAY, nv=N_VEH):
    """E_drv[b,k] kWh consumed by traction, spread over the driving minutes."""
    E = np.zeros((nv, K))
    by_veh = {}
    for e in events:
        by_veh.setdefault(e.veh, []).append(e)
    for b, evs in by_veh.items():
        evs.sort(key=lambda x: x.arr)
        for e1, e2 in zip(evs[:-1], evs[1:]):
            n = e2.arr - e1.dep
            if 0 < n <= 4 * LEG_MIN:
                E[b, e1.dep:e2.arr] += leg_kwh / n
    return E


def departures(events):
    """List of (veh, hub, dep_minute, required_energy_kwh) for LL-5."""
    out = []
    for e in events:
        if e.e_next > 0:
            out.append((e.veh, e.hub, e.dep, e.e_next + E_RESERVE_KWH))
    return out
