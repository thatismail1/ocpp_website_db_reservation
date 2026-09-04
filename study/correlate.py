"""Correlated transit and network demand.

Grid-aware electric bus studies model vehicle energy demand as an exogenous
profile, statistically independent of feeder loading. It is not independent.
Both are driven by the same human activity pattern:

  ridership   -> passenger mass  -> traction energy per km
  congestion  -> stop-start duty -> traction energy per km
  ambient     -> HVAC auxiliary  -> energy per minute, and the feeder's own peak

This module supplies the three channels and a leg-energy function that depends
on departure time, so that a trip leaving in the evening peak costs more than
the same trip at midday. The shapes here are taken from published transit and
network profiles independently -- the correlation is measured, not imposed.
"""
from __future__ import annotations
import os
import numpy as np
import system as S
import transit as T

# --------------------------------------------------------------- channels ---
PAX_CAPACITY = 90                 # seated + standing
PAX_MASS_KG = 70.0
LOAD_FACTOR_OFFPEAK = 0.15
LOAD_FACTOR_PEAK = 0.90
CONGESTION_SPEED_FACTOR = 0.72    # peak-hour mean speed vs free flow
AUX_SUMMER_KW = 6.0
AUX_WINTER_KW = 18.0              # heating dominates in cold weather


def ridership_profile(k=S.K_DAY):
    """Urban transit load factor over the day: sharp AM and PM commuter peaks."""
    t = np.arange(k) / 60.0
    s = (0.95 * np.exp(-0.5 * ((t - 8.0) / 1.15) ** 2)
         + 1.00 * np.exp(-0.5 * ((t - 17.3) / 1.45) ** 2)
         + 0.30 * np.exp(-0.5 * ((t - 12.5) / 2.6) ** 2))
    s = s / s.max()
    return LOAD_FACTOR_OFFPEAK + (LOAD_FACTOR_PEAK - LOAD_FACTOR_OFFPEAK) * s


def congestion_profile(k=S.K_DAY):
    """Congestion index in [0,1]: 0 free flow, 1 worst peak-hour condition."""
    t = np.arange(k) / 60.0
    s = (0.90 * np.exp(-0.5 * ((t - 8.2) / 1.3) ** 2)
         + 1.00 * np.exp(-0.5 * ((t - 17.6) / 1.7) ** 2))
    return np.clip(s / s.max(), 0.0, 1.0)


# ------------------------------------------------- time-dependent leg energy --
def leg_energy_table(winter=False, n_pts=25, seed=3):
    """Leg energy [kWh] on a grid of (load factor, congestion) states.

    The longitudinal model is re-run for each state: passenger mass enters the
    inertia, rolling and grade terms; congestion is applied as a slower, more
    stop-start version of the same route (same distance, longer duration, so
    the auxiliary load is carried for longer).
    """
    v0, g0 = T.synthetic_urban_cycle(T.LEG_MIN * 60, seed=seed)
    aux = AUX_WINTER_KW if winter else AUX_SUMMER_KW
    lf = np.linspace(LOAD_FACTOR_OFFPEAK, LOAD_FACTOR_PEAK, n_pts)
    cg = np.linspace(0.0, 1.0, n_pts)
    E = np.zeros((n_pts, n_pts))
    D = np.zeros((n_pts, n_pts))
    for i, l in enumerate(lf):
        p = T.BusParams(mass_kg=14000.0 + l * PAX_CAPACITY * PAX_MASS_KG,
                        aux_kw=aux)
        for j, c in enumerate(cg):
            # congestion: same route, lower speed, so the trip takes longer and
            # the fixed auxiliary load is carried over more minutes
            f = 1.0 - c * (1.0 - CONGESTION_SPEED_FACTOR)
            v = v0 * f
            reps = int(round(1.0 / f))          # stretch time to keep distance
            vv = np.repeat(v, reps)[: int(len(v0) / f)]
            gg = np.resize(g0, len(vv))
            e, dkm = T.leg_energy_kwh(vv, gg, p=p)
            # normalise to the free-flow distance so kWh/km is comparable
            E[i, j] = e * (T.LEG_MIN * 60 * np.mean(v0) / 1000.0) / max(dkm, 1e-6)
            D[i, j] = dkm
    return lf, cg, E, D


class CorrelatedDemand:
    """Leg energy as a function of departure minute."""

    def __init__(self, winter=False, seed=3):
        self.rid = ridership_profile()
        self.cong = congestion_profile()
        self.lf, self.cg, self.E, _ = leg_energy_table(winter=winter, seed=seed)
        self.winter = winter

    def leg_kwh(self, minute: int) -> float:
        m = int(minute) % S.K_DAY
        i = np.interp(self.rid[m], self.lf, np.arange(len(self.lf)))
        j = np.interp(self.cong[m], self.cg, np.arange(len(self.cg)))
        i0, j0 = int(np.floor(i)), int(np.floor(j))
        i1 = min(i0 + 1, len(self.lf) - 1); j1 = min(j0 + 1, len(self.cg) - 1)
        a, b = i - i0, j - j0
        return float((1 - a) * (1 - b) * self.E[i0, j0] + a * (1 - b) * self.E[i1, j0]
                     + (1 - a) * b * self.E[i0, j1] + a * b * self.E[i1, j1])

    def mean_leg_kwh(self) -> float:
        """The single constant an independent-model study would use: the
        service-hours average, which is what fitting kWh/km to a fleet gives."""
        mins = np.arange(T.SERVICE_START, T.SERVICE_END)
        return float(np.mean([self.leg_kwh(m) for m in mins]))


# ------------------------------------------------------ coincidence metrics --
def coincidence_metrics(bus_kw, feeder_kw):
    """Utility-facing measures of how bus charging lines up with feeder peak.

    contribution : bus demand at the hour of system peak / bus peak demand.
                   This is the factor a planner needs when sizing a connection:
                   how much of the bus load is actually present when the
                   network is at its worst.
    correlation  : Pearson correlation of the two 1-min series.
    """
    tot = feeder_kw + bus_kw
    k_sys = int(np.argmax(tot))
    k_feed = int(np.argmax(feeder_kw))
    bp = float(bus_kw.max())
    return dict(
        contribution_at_system_peak=float(bus_kw[k_sys] / bp) if bp > 0 else 0.0,
        contribution_at_feeder_peak=float(bus_kw[k_feed] / bp) if bp > 0 else 0.0,
        system_peak_kW=float(tot.max()),
        feeder_peak_kW=float(feeder_kw.max()),
        bus_peak_kW=bp,
        sum_of_separate_peaks_kW=float(feeder_kw.max() + bp),
        coincidence_factor=float(tot.max() / (feeder_kw.max() + bp)) if bp > 0 else 1.0,
        correlation=float(np.corrcoef(bus_kw, feeder_kw)[0, 1]) if bp > 0 else 0.0,
        hour_system_peak=k_sys / 60.0, hour_feeder_peak=k_feed / 60.0,
        hour_bus_peak=float(np.argmax(bus_kw)) / 60.0)
