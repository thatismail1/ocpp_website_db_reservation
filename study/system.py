"""IEEE 33-bus feeder, transit network, and exogenous profiles for the
hierarchical bi-level opportunity-charging case study."""
from __future__ import annotations
import os
import numpy as np
from dataclasses import dataclass, field

# ---------------------------------------------------------------- feeder ----
S_BASE_KVA = 1000.0
V_BASE_KV = 12.66
Z_BASE = V_BASE_KV ** 2 * 1000.0 / S_BASE_KVA        # ohm
V_MIN, V_MAX = 0.95, 1.05

# from, to, R[ohm], X[ohm]
BRANCH = [
    (1, 2, 0.0922, 0.0477), (2, 3, 0.4930, 0.2511), (3, 4, 0.3660, 0.1864),
    (4, 5, 0.3811, 0.1941), (5, 6, 0.8190, 0.7070), (6, 7, 0.1872, 0.6188),
    (7, 8, 0.7114, 0.2351), (8, 9, 1.0300, 0.7400), (9, 10, 1.0440, 0.7400),
    (10, 11, 0.1966, 0.0650), (11, 12, 0.3744, 0.1238), (12, 13, 1.4680, 1.1550),
    (13, 14, 0.5416, 0.7129), (14, 15, 0.5910, 0.5260), (15, 16, 0.7463, 0.5450),
    (16, 17, 1.2890, 1.7210), (17, 18, 0.7320, 0.5740), (2, 19, 0.1640, 0.1565),
    (19, 20, 1.5042, 1.3554), (20, 21, 0.4095, 0.4784), (21, 22, 0.7089, 0.9373),
    (3, 23, 0.4512, 0.3083), (23, 24, 0.8980, 0.7091), (24, 25, 0.8960, 0.7011),
    (6, 26, 0.2030, 0.1034), (26, 27, 0.2842, 0.1447), (27, 28, 1.0590, 0.9337),
    (28, 29, 0.8042, 0.7006), (29, 30, 0.5075, 0.2585), (30, 31, 0.9744, 0.9630),
    (31, 32, 0.3105, 0.3619), (32, 33, 0.3410, 0.5302),
]
# bus: (P[kW], Q[kvar])  -- peak nominal
LOAD = {
    2: (100, 60), 3: (90, 40), 4: (120, 80), 5: (60, 30), 6: (60, 20),
    7: (200, 100), 8: (200, 100), 9: (60, 20), 10: (60, 20), 11: (45, 30),
    12: (60, 35), 13: (60, 35), 14: (120, 80), 15: (60, 10), 16: (60, 20),
    17: (60, 20), 18: (90, 40), 19: (90, 40), 20: (90, 40), 21: (90, 40),
    22: (90, 40), 23: (90, 50), 24: (420, 200), 25: (420, 200), 26: (60, 25),
    27: (60, 25), 28: (60, 20), 29: (120, 70), 30: (200, 600), 31: (150, 70),
    32: (210, 100), 33: (60, 40),
}
N_BUS = 33
SUB_MVA = 5.0                       # substation transformer rating [MVA]
V_REF = 1.04                        # substation OLTC set point [p.u.]
LOAD_SCALE = float(os.environ.get("FEEDER_LOAD", 0.60))   # operating point
PV_SCALE = float(os.environ.get("PV_SCALE", 1.0))          # PV penetration
REV_LIMIT_KW = 1000.0               # permitted reverse flow at substation
BRANCH_S_MAX_KVA = 5000.0           # trunk rating; laterals derated below


def feeder_topology():
    """Return (parent, children, branch_index, r_pu, x_pu, order) 0-indexed."""
    nb = N_BUS
    parent = -np.ones(nb, dtype=int)
    bidx = -np.ones(nb, dtype=int)
    r = np.zeros(len(BRANCH)); x = np.zeros(len(BRANCH))
    for k, (f, t, rr, xx) in enumerate(BRANCH):
        parent[t - 1] = f - 1
        bidx[t - 1] = k
        r[k] = rr / Z_BASE
        x[k] = xx / Z_BASE
    children = [[] for _ in range(nb)]
    for j in range(nb):
        if parent[j] >= 0:
            children[parent[j]].append(j)
    # BFS order from root
    order, stack = [], [0]
    while stack:
        n = stack.pop(0)
        order.append(n)
        stack.extend(children[n])
    return parent, children, bidx, r, x, np.array(order)


def path_resistance_matrix(parent, bidx, r):
    """R[i,j] = sum of r over branches common to paths root->i and root->j."""
    nb = N_BUS
    paths = []
    for i in range(nb):
        p, n = [], i
        while parent[n] >= 0:
            p.append(bidx[n]); n = parent[n]
        paths.append(set(p))
    R = np.zeros((nb, nb))
    for i in range(nb):
        for j in range(nb):
            R[i, j] = sum(r[k] for k in paths[i] & paths[j])
    return R


def branch_rating_pu():
    """Apparent-power rating per branch in p.u. (trunk vs lateral)."""
    s = np.full(len(BRANCH), BRANCH_S_MAX_KVA / S_BASE_KVA)
    laterals = {17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31}
    for k in laterals:
        s[k] = 2500.0 / S_BASE_KVA
    return s


# ------------------------------------------------------------------ hubs ----
@dataclass
class Hub:
    name: str
    bus: int              # 1-indexed feeder bus
    n_bays: int
    p_bay_kw: float
    p_pcc_kw: float       # site connection / transformer capacity
    pv_kwp: float
    base_load_kw: float
    bess_kwh: float = 0.0
    bess_kw: float = 0.0


HUBS = [
    Hub("A  Terminal North", 18, 2, 450.0, 1300.0, 250.0, 300.0),
    Hub("B  Terminal South", 33, 2, 250.0,  900.0, 180.0, 220.0),
    Hub("C  Interchange",    22, 1, 150.0,  600.0, 120.0, 150.0),
    Hub("D  Central Depot",  25, 4, 150.0, 1200.0, 400.0, 260.0, 600.0, 300.0),
]
# Hub placement is configurable: whether hubs COMPETE for shared network
# capacity (same lateral) or are electrically near-independent (separate
# laterals) turns out to decide whether fleet-aware allocation beats a
# connection-specific one.
_hb = os.environ.get("HUB_BUSES")
if _hb:
    for _h, _b in zip(HUBS, [int(x) for x in _hb.split(",")]):
        _h.bus = _b

HUB_IDX = {h.name[0]: i for i, h in enumerate(HUBS)}

# ------------------------------------------------------------- time grid ----
DT_LL = 1.0 / 60.0          # h   (1 min)
DT_UL = 15.0 / 60.0         # h   (15 min)
K_DAY = 1440                # 1-min steps
T_DAY = 96                  # 15-min steps
UL_OF_LL = np.arange(K_DAY) // 15


# ------------------------------------------------------------- profiles ----
def tariff_1min(rng=None):
    """TOU / day-ahead price [currency per kWh], 1-min resolution."""
    hourly = np.array([
        2901.36, 2788.78, 2212.08, 2321.13, 2244.99, 1967.99,
        1749.99, 2049.99, 2830.00, 2749.90, 2647.99, 2700.00,
        2089.00, 2444.78, 2915.94, 2950.00, 2929.99, 2951.58,
        3000.00, 3000.00, 3000.00, 3000.00, 2950.00, 2908.15]) / 1000.0
    return np.repeat(hourly, 60)


def pv_shape(k=K_DAY, seed=7):
    """Normalized clear-sky-with-cloud PV shape in [0,1]."""
    rng = np.random.default_rng(seed)
    t = np.arange(k) / 60.0
    clear = np.clip(np.sin(np.pi * (t - 6.2) / 12.4), 0.0, None) ** 1.25
    # correlated cloud attenuation
    noise = rng.normal(0, 1, k)
    kern = np.exp(-0.5 * (np.arange(-90, 91) / 28.0) ** 2); kern /= kern.sum()
    cloud = np.convolve(noise, kern, mode="same")
    atten = np.clip(1.0 + 0.22 * cloud, 0.35, 1.05)
    atten[t < 11.0] = np.clip(atten[t < 11.0] * 1.05, 0.4, 1.05)
    return np.clip(clear * atten, 0.0, None)


def site_load_shape(k=K_DAY, phase=0.0):
    t = np.arange(k) / 60.0
    s = (0.62
         + 0.30 * np.exp(-0.5 * ((t - 10.0 - phase) / 2.6) ** 2)
         + 0.42 * np.exp(-0.5 * ((t - 19.0 - phase) / 3.0) ** 2)
         - 0.22 * np.exp(-0.5 * ((t - 3.5) / 2.4) ** 2))
    return np.clip(s, 0.15, None)


def feeder_load_shape(k=K_DAY):
    t = np.arange(k) / 60.0
    s = (0.60
         + 0.22 * np.exp(-0.5 * ((t - 11.0) / 3.0) ** 2)
         + 0.46 * np.exp(-0.5 * ((t - 19.5) / 2.6) ** 2)
         - 0.18 * np.exp(-0.5 * ((t - 4.0) / 2.5) ** 2))
    s = np.clip(s, 0.2, None)
    return LOAD_SCALE * s / s.max()


def build_exogenous(seed=7):
    """Return dict of 1-min exogenous series."""
    pv = pv_shape(seed=seed)
    out = {}
    out["price"] = tariff_1min()
    out["pv_hub"] = np.stack([PV_SCALE * h.pv_kwp * pv for h in HUBS])  # (H,K)
    out["load_hub"] = np.stack([h.base_load_kw * site_load_shape(phase=0.3 * i)
                                for i, h in enumerate(HUBS)])        # (H,K)
    fs = feeder_load_shape()
    P = np.zeros((N_BUS, K_DAY)); Q = np.zeros((N_BUS, K_DAY))
    for b, (p, q) in LOAD.items():
        P[b - 1] = p * fs
        Q[b - 1] = q * fs
    # hub site load and PV sit at the hub PCC bus, on top of feeder load
    for i, h in enumerate(HUBS):
        P[h.bus - 1] += out["load_hub"][i] - out["pv_hub"][i]
        Q[h.bus - 1] += 0.32 * out["load_hub"][i]
    out["P_feeder"] = P          # kW, excludes bus charging
    out["Q_feeder"] = Q          # kvar
    return out
