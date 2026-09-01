"""Upper-level LinDistFlow dispatch (UL-1..UL-10), hub LP used inside the
ADMM coordination (C-2..C-4), and the 1-minute hub MILP (LL-1..LL-10)."""
from __future__ import annotations
import numpy as np, time
import pyomo.environ as pyo
import system as S, transit as T

SOLVER = "appsi_highs"


def _solve(m, mip_gap=None, tl=30, qp=False):
    """qp=True routes to the Pyomo `highs` interface, which accepts the
    quadratic ADMM proximal term; MILPs go to appsi_highs."""
    if qp:
        s = pyo.SolverFactory("highs")
        t0 = time.perf_counter()
        res = s.solve(m)
        return time.perf_counter() - t0, res
    s = pyo.SolverFactory(SOLVER)
    if mip_gap is not None:
        s.config.mip_gap = mip_gap
    s.config.time_limit = tl
    t0 = time.perf_counter()
    res = s.solve(m)
    return time.perf_counter() - t0, res


# ============================================================ UPPER LEVEL ===
class Network:
    """Affine LinDistFlow maps: with exogenous reactive injections, squared
    voltage and branch flow are affine in the hub imports Phat."""

    def __init__(self, feeder, exo):
        self.f = feeder
        nb, nbr = S.N_BUS, len(S.BRANCH)
        # subtree indicator D[br, bus] = 1 if bus is downstream of branch br
        D = np.zeros((nbr, nb))
        for j in range(nb):
            n = j
            while feeder.parent[n] >= 0:
                D[feeder.bidx[n], j] = 1.0
                n = feeder.parent[n]
        self.D = D
        # path indicator A[bus, br] = 1 if branch br on path root->bus
        self.A = D.T.copy()
        # exogenous 15-min feeder injections (hub charging excluded)
        P = exo["P_feeder"].reshape(S.N_BUS, S.T_DAY, 15).mean(2)
        Q = exo["Q_feeder"].reshape(S.N_BUS, S.T_DAY, 15).mean(2)
        self.Pb = D @ P / S.S_BASE_KVA        # (nbr,T) base branch flow p.u.
        self.Qb = D @ Q / S.S_BASE_KVA
        self.hub_bus = np.array([h.bus - 1 for h in S.HUBS])
        # G[br,h] = 1 if hub h downstream of branch br
        self.G = D[:, self.hub_bus]
        # u_i = Vref^2 - 2*sum_path(r*P + x*Q)  -> u = u0 - Mu @ Phat
        self.u0 = (S.V_REF ** 2
                   - 2 * (self.A @ (feeder.r[:, None] * self.Pb
                                    + feeder.x[:, None] * self.Qb)))
        self.Mu = 2 * (self.A @ (feeder.r[:, None] * self.G))   # (nb,H) p.u./p.u.
        self.smax = feeder.smax


def upper_level(net, exo, price, netload, cap, rho=0.0, target=None,
                w_loss=0.9, w_v=8.0, w_peak=0.0, n_cuts=6, quiet=True,
                vmin_ul=None):
    """LinDistFlow LP (UL-1..UL-8) over the controllable hub power Pctrl[h,t].

    netload[h,t] : site load minus PV at 15-min resolution [kW]  (exogenous,
                   already inside net.Pb)
    cap[h,t]     : upper bound on controllable hub power [kW]
    target       : ADMM consensus target [kW] (C-2); rho = penalty
    """
    H, Tn = len(S.HUBS), S.T_DAY
    nbr = len(S.BRANCH)
    m = pyo.ConcreteModel()
    m.P = pyo.Var(range(H), range(Tn))                    # p.u., controllable
    m.loss = pyo.Var(range(nbr), range(Tn), domain=pyo.NonNegativeReals)
    m.sp = pyo.Var(range(S.N_BUS), range(Tn), domain=pyo.NonNegativeReals)
    m.sm = pyo.Var(range(S.N_BUS), range(Tn), domain=pyo.NonNegativeReals)
    m.pk = pyo.Var(domain=pyo.NonNegativeReals)
    for h in range(H):
        lo = -S.HUBS[h].bess_kw / S.S_BASE_KVA
        for t in range(Tn):
            m.P[h, t].setlb(lo)
            m.P[h, t].setub(max(cap[h, t], 0.0) / S.S_BASE_KVA)

    def flow(b, t):
        return net.Pb[b, t] + sum(net.G[b, h] * m.P[h, t] for h in range(H)
                                  if net.G[b, h])

    vmin_ul = S.V_MIN if vmin_ul is None else vmin_ul
    m.c = pyo.ConstraintList()

    def add(expr):
        if isinstance(expr, (bool, np.bool_)):
            return
        m.c.add(expr)
    # UL-7 site connection capacity at the PCC
    for h in range(H):
        for t in range(Tn):
            add(netload[h, t] / S.S_BASE_KVA + m.P[h, t]
                    <= S.HUBS[h].p_pcc_kw / S.S_BASE_KVA)
    # UL-4 voltage band + deviation slacks
    for i in range(S.N_BUS):
        row = net.Mu[i]
        for t in range(Tn):
            u = net.u0[i, t] - sum(row[h] * m.P[h, t] for h in range(H) if row[h])
            add(u >= vmin_ul ** 2)
            add(u <= S.V_MAX ** 2)
            add(m.sp[i, t] >= u - 1.0)
            add(m.sm[i, t] >= 1.0 - u)
    # UL-5 branch thermal limit (Q exogenous -> reduces to a P band)
    for b in range(nbr):
        for t in range(Tn):
            lim = np.sqrt(max(net.smax[b] ** 2 - net.Qb[b, t] ** 2, 1e-6))
            add(flow(b, t) <= lim)
            add(flow(b, t) >= -lim)
    # UL-8a piecewise-linear (tangent) loss under-estimator
    for b in range(nbr):
        p0s = np.linspace(-0.3, min(net.smax[b], 4.5), n_cuts)
        for t in range(Tn):
            for p0 in p0s:
                add(m.loss[b, t] >= (2 * p0 * flow(b, t) - p0 ** 2
                                         + net.Qb[b, t] ** 2) / S.V_REF ** 2)
    # UL-6 substation headroom and reverse-flow limit
    for t in range(Tn):
        psub = flow(0, t)
        add(psub <= S.SUB_MVA * 1000.0 / S.S_BASE_KVA * 0.93)
        add(psub >= -S.REV_LIMIT_KW / S.S_BASE_KVA)
        add(m.pk >= psub)

    pr = price.reshape(Tn, 15).mean(1)
    obj = sum(pr[t] * flow(0, t) * S.S_BASE_KVA * S.DT_UL for t in range(Tn))
    obj += w_loss * sum(net.f.r[b] * m.loss[b, t] * S.S_BASE_KVA * S.DT_UL
                        for b in range(nbr) for t in range(Tn))
    obj += w_v * sum(m.sp[i, t] + m.sm[i, t]
                     for i in range(S.N_BUS) for t in range(Tn))
    obj += w_peak * m.pk * S.S_BASE_KVA
    if target is not None:
        # convex PWL (tangent) model of the ADMM proximal term, so the
        # subproblem stays an LP for HiGHS
        m.pen = pyo.Var(range(H), range(Tn), domain=pyo.NonNegativeReals)
        _g = np.array([0.0, .004, .008, .016, .032, .064, .128, .256, .5, 1.0])
        cuts = np.unique(np.concatenate([-_g[::-1], _g]))
        for h in range(H):
            for t in range(Tn):
                dev = m.P[h, t] - target[h, t] / S.S_BASE_KVA
                for x0 in cuts:
                    add(m.pen[h, t] >= 2 * x0 * dev - x0 ** 2)
        obj += (rho / 2) * sum(m.pen[h, t] for h in range(H) for t in range(Tn))
    m.obj = pyo.Objective(expr=obj, sense=pyo.minimize)
    dt, res = _solve(m)
    P = np.array([[pyo.value(m.P[h, t]) for t in range(Tn)]
                  for h in range(H)]) * S.S_BASE_KVA
    # LinDistFlow state at the optimum, for the UL-9a sensitivity walk
    u = net.u0 - net.Mu @ (P / S.S_BASE_KVA)
    fl = net.Pb + net.G @ (P / S.S_BASE_KVA)
    return P, dt, float(pyo.value(m.obj)), u, fl


# ====================================================== FLEET BLOCK (15 min) =
def fleet_lp(av15, edrv15, deps, price, rho=0.0, target=None, lam=None,
             soc0=None, w_deg=0.012, w_eps=3000.0, cap_ctrl=None):
    """LP relaxation of the transit-side block used inside ADMM (C-3).

    av15[h,b,t] : fraction of 15-min interval t that vehicle b is berthed at h
    edrv15[b,t] : traction energy consumed in interval t [kWh]
    deps        : list of (veh, hub, dep_minute, required_energy_kwh)
    lam         : price seen by the fleet [cur/kWh] (T,) or None -> `price`
    """
    H, Tn, NV = len(S.HUBS), S.T_DAY, T.N_VEH
    pr = price.reshape(Tn, 15).mean(1) if lam is None else lam
    idx = [(h, b, t) for h in range(H) for b in range(NV) for t in range(Tn)
           if av15[h, b, t] > 1e-9]
    m = pyo.ConcreteModel()
    m.pc = pyo.Var(idx, domain=pyo.NonNegativeReals)
    m.soc = pyo.Var(range(NV), range(Tn + 1), bounds=(T.SOC_MIN, T.SOC_MAX))
    m.ctrl = pyo.Var(range(H), range(Tn))
    dep_keys = list(range(len(deps)))
    m.eps = pyo.Var(dep_keys, bounds=(0, 0.6))
    hD = S.HUB_IDX["D"]
    m.bc = pyo.Var(range(Tn), bounds=(0, S.HUBS[hD].bess_kw))
    m.bd = pyo.Var(range(Tn), bounds=(0, S.HUBS[hD].bess_kw))
    m.bs = pyo.Var(range(Tn + 1), bounds=(0.15, 0.9))
    m.c = pyo.ConstraintList()

    for (h, b, t) in idx:
        m.pc[h, b, t].setub(av15[h, b, t] * S.HUBS[h].p_bay_kw)
    # bay count per hub
    for h in range(H):
        for t in range(Tn):
            terms = [m.pc[h, b, t] for b in range(NV) if (h, b, t) in m.pc]
            if terms:
                m.c.add(sum(terms) <= S.HUBS[h].n_bays * S.HUBS[h].p_bay_kw)
    # SoC dynamics
    for b in range(NV):
        m.c.add(m.soc[b, 0] == (T.SOC_START if soc0 is None else soc0[b]))
        for t in range(Tn):
            ch = sum(m.pc[h, b, t] for h in range(H) if (h, b, t) in m.pc)
            m.c.add(m.soc[b, t + 1] == m.soc[b, t]
                    + (T.ETA_CHG * ch * S.DT_UL - edrv15[b, t]) / T.E_VEH_KWH)
        m.c.add(m.soc[b, Tn] >= T.SOC_START)          # day-neutral terminal SoC
    # departure feasibility
    for k, (b, h, dm, ereq) in enumerate(deps):
        t = min(dm // 15, Tn)
        m.c.add(m.soc[b, t] + m.eps[k] >= ereq / T.E_VEH_KWH + T.SOC_MIN)
    # BESS
    for t in range(Tn):
        m.c.add(m.bs[t + 1] == m.bs[t]
                + (0.96 * m.bc[t] - m.bd[t] / 0.96) * S.DT_UL / S.HUBS[hD].bess_kwh)
    m.c.add(m.bs[0] == 0.5); m.c.add(m.bs[Tn] >= 0.5)
    # controllable hub power
    for h in range(H):
        for t in range(Tn):
            ch = sum(m.pc[h, b, t] for b in range(NV) if (h, b, t) in m.pc)
            extra = (m.bc[t] - m.bd[t]) if h == hD else 0.0
            m.c.add(m.ctrl[h, t] == ch + extra)
            if cap_ctrl is not None:
                m.c.add(m.ctrl[h, t] <= cap_ctrl[h, t])

    obj = sum(pr[t] * m.ctrl[h, t] * S.DT_UL for h in range(H) for t in range(Tn))
    obj += w_deg * sum((m.bc[t] + m.bd[t]) * S.DT_UL for t in range(Tn))
    obj += 0.25 * w_deg * sum(m.pc[k] * S.DT_UL for k in idx)
    obj += w_eps * sum(m.eps[k] for k in dep_keys)
    if target is not None:
        m.pen = pyo.Var(range(H), range(Tn), domain=pyo.NonNegativeReals)
        _g = 900.0 * np.array([0.0, .004, .008, .016, .032, .064, .128, .256, .5, 1.0])
        cuts = np.unique(np.concatenate([-_g[::-1], _g]))
        for h in range(H):
            for t in range(Tn):
                dev = m.ctrl[h, t] - target[h, t]
                for x0 in cuts:
                    m.c.add(m.pen[h, t] >= 2 * x0 * dev - x0 ** 2)
        obj += (rho / 2) * sum(m.pen[h, t] for h in range(H) for t in range(Tn))
    m.obj = pyo.Objective(expr=obj, sense=pyo.minimize)
    dt, res = _solve(m)
    ctrl = np.array([[pyo.value(m.ctrl[h, t]) for t in range(Tn)] for h in range(H)])
    soc = np.array([[pyo.value(m.soc[b, t]) for t in range(Tn + 1)] for b in range(NV)])
    eps = np.array([pyo.value(m.eps[k]) for k in dep_keys])
    return dict(ctrl=ctrl, soc=soc, eps=eps, obj=float(pyo.value(m.obj)), t=dt)


# ================================================ HUB MPC (1 min, LL-1..LL-10)
def hub_mpc(h, k, Np, av, edrv, deps, soc_now, bess_now, lam, pmax_env,
            netload, w_deg=0.012, w_eps=3000.0, phi=None, mip_gap=1e-4,
            n_apply=1):
    """One receding-horizon solve for hub h at minute k. Returns first sample."""
    hub = S.HUBS[h]
    K = min(k + Np, S.K_DAY)
    W = range(k, K)
    veh = [b for b in range(T.N_VEH) if av[h, b, k:K].any()]
    na = max(1, min(n_apply, K - k))
    if not veh and hub.bess_kwh <= 0:
        return dict(pchg=np.zeros((T.N_VEH, na)), bc=np.zeros(na),
                    bd=np.zeros(na), t=0.0, obj=0.0, na=na)
    need_bin = bool(veh) and av[h, :, k:K].sum(0).max() > hub.n_bays
    m = pyo.ConcreteModel()
    m.pc = pyo.Var(veh, W, domain=pyo.NonNegativeReals)
    # SoC floor is soft: traction demand over the horizon is exogenous, so a
    # hard floor can make the local problem infeasible and break recursive
    # feasibility (LL-2 with a reserve-violation slack).
    m.soc = pyo.Var(veh, range(k, K + 1), bounds=(0.02, T.SOC_MAX))
    m.sl = pyo.Var(veh, range(k, K + 1), domain=pyo.NonNegativeReals)
    m.wp = pyo.Var(veh, W, domain=pyo.NonNegativeReals)     # above-knee power
    if need_bin and veh:
        m.z = pyo.Var(veh, W, domain=pyo.Binary)
    has_b = hub.bess_kwh > 0
    if has_b:
        m.bc = pyo.Var(W, bounds=(0, hub.bess_kw))
        m.bd = pyo.Var(W, bounds=(0, hub.bess_kw))
        m.bs = pyo.Var(range(k, K + 1), bounds=(0.15, 0.9))
    dk = [(i, d) for i, d in enumerate(deps)
          if d[1] == h and k <= d[2] < K and d[0] in veh]
    m.eps = pyo.Var([i for i, _ in dk], bounds=(0, 0.6))
    m.c = pyo.ConstraintList()
    P_KNEE = 0.6 * hub.p_bay_kw

    for b in veh:
        m.c.add(m.soc[b, k] == min(max(soc_now[b], 0.02), T.SOC_MAX))
        for t in range(k, K + 1):
            m.c.add(m.soc[b, t] + m.sl[b, t] >= T.SOC_MIN)
        for t in W:
            if need_bin:
                m.c.add(m.pc[b, t] <= hub.p_bay_kw * m.z[b, t])
                m.c.add(m.z[b, t] <= int(av[h, b, t]))
            else:
                m.c.add(m.pc[b, t] <= hub.p_bay_kw * int(av[h, b, t]))
            m.c.add(m.wp[b, t] >= m.pc[b, t] - P_KNEE)
            m.c.add(m.soc[b, t + 1] == m.soc[b, t]
                    + (T.ETA_CHG * m.pc[b, t] * S.DT_LL - edrv[b, t]) / T.E_VEH_KWH)
    for t in W:
        if not veh:
            continue
        if need_bin:
            m.c.add(sum(m.z[b, t] for b in veh) <= hub.n_bays)
        else:
            m.c.add(sum(m.pc[b, t] for b in veh) <= hub.n_bays * hub.p_bay_kw)
    for i, (b, hh, dm, ereq) in dk:
        m.c.add(m.soc[b, dm] + m.eps[i] >= ereq / T.E_VEH_KWH + T.SOC_MIN)
    if has_b:
        m.c.add(m.bs[k] == bess_now)
        for t in W:
            m.c.add(m.bs[t + 1] == m.bs[t]
                    + (0.96 * m.bc[t] - m.bd[t] / 0.96) * S.DT_LL / hub.bess_kwh)
    # LL-8/LL-9 site balance and dispatched envelope
    for t in W:
        ctrl = sum(m.pc[b, t] for b in veh) + ((m.bc[t] - m.bd[t]) if has_b else 0.0)
        m.c.add(ctrl <= max(pmax_env[t], 0.0))                 # LL-9 envelope
        m.c.add(netload[t] + ctrl <= hub.p_pcc_kw)              # site capacity

    if phi is None:
        phi = 0.0
    obj = sum(lam[t] * (sum(m.pc[b, t] for b in veh)
                        + ((m.bc[t] - m.bd[t]) if has_b else 0.0)) * S.DT_LL
              for t in W)
    obj += 0.25 * w_deg * sum(m.pc[b, t] * S.DT_LL for b in veh for t in W)
    obj += 0.004 * sum(m.wp[b, t] * S.DT_LL for b in veh for t in W)
    if has_b:
        obj += w_deg * sum((m.bc[t] + m.bd[t]) * S.DT_LL for t in W)
    obj += w_eps * sum(m.eps[i] for i, _ in dk)
    obj += 4.0 * w_eps * sum(m.sl[b, t] for b in veh for t in range(k, K + 1))
    obj -= phi * sum(m.soc[b, K] for b in veh)
    if has_b:
        obj -= phi * 0.5 * m.bs[K]
    m.obj = pyo.Objective(expr=obj, sense=pyo.minimize)
    dt, res = _solve(m, mip_gap=mip_gap if need_bin else None, tl=20)
    pch = np.zeros((T.N_VEH, na))
    for b in veh:
        for j in range(na):
            pch[b, j] = max(0.0, pyo.value(m.pc[b, k + j]))
    bc = np.array([pyo.value(m.bc[k + j]) for j in range(na)]) if has_b else np.zeros(na)
    bd = np.array([pyo.value(m.bd[k + j]) for j in range(na)]) if has_b else np.zeros(na)
    return dict(pchg=pch, bc=bc, bd=bd, t=dt, obj=float(pyo.value(m.obj)), na=na)
