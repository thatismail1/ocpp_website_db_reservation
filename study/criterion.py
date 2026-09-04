"""Analytical failure criterion for per-site operating-envelope allocation.

--------------------------------------------------------------------------
WHAT THIS DOES AND DOES NOT CLAIM
--------------------------------------------------------------------------
Two distinct failure modes are often conflated. They are separated here.

(A) NAIVE ONE-AT-A-TIME ALLOCATION. If each hub's headroom is computed by
    perturbing that hub alone, the resulting box is not jointly secure. This
    is exact and easy, and it is NOT what the operating-envelope literature
    does -- joint feasibility is the defining property of a DOE. It is
    included because a practitioner using raw sensitivity factors may do it.

(B) CORRECTLY-ALLOCATED JOINT ENVELOPES THAT STILL VIOLATE IN AC. A joint LP
    on LinDistFlow is secure *in the linear model*. LinDistFlow drops the loss
    terms, so it over-predicts voltage, and a maximal allocation sits exactly
    on the linear boundary where that error is largest. This is the mechanism
    behind every violation measured in this project, and it is what the
    criterion below predicts.

--------------------------------------------------------------------------
DERIVATION (assumptions stated first)
--------------------------------------------------------------------------
A1  Radial network, single feed at bus 0 held at V_ref.
A2  LinDistFlow: u_i = V_ref^2 - 2 sum_j (R_ij p_j + X_ij q_j), where R_ij is
    the resistance shared by the paths from the root to i and to j. R >= 0
    elementwise, so u is monotone decreasing in every injection -- this is the
    property that makes corner certification valid.
A3  Reactive injections are exogenous (no hub reactive control).
A4  Losses are small relative to flows, so one correction step suffices.

Exact DistFlow differs from A2 in two ways: branch flows carry the losses of
everything downstream, and there is a +(r^2+x^2)*l term. The first dominates.
Writing L_ij for the loss generated downstream of branch (i,j), the additional
voltage-square drop at bus m relative to LinDistFlow is

    D_err(m)  ~=  2 * sum_{(i,j) in path(m)} r_ij * L_ij ,
    L_ij      ~=  sum_{(k,l) downstream of (i,j)} r_kl * (P_kl^2 + Q_kl^2)/u .

Collapsing the path sum onto the shared and exclusive segments of two hubs A
and B, with R_AA the resistance of A's own path and R_AB the resistance shared
with B, and writing rho = R_AB / R_AA:

    D_err(A) ~= (2/V_ref^2) [ R_AB^2 * S_shared^2 + (R_AA-R_AB)^2 * S_excl^2 ]
             =  (2/V_ref^2) R_AA^2 [ rho^2 S_shared^2 + (1-rho)^2 S_excl^2 ]

S_shared carries the SUM of both hubs' draws plus the base flow through the
shared segment; S_excl carries only hub A's. So rho enters twice: it weights
the shared term, and the shared term itself grows with (P_A + P_B)^2. That is
why sharing hurts superlinearly, and why two hubs on separate laterals do not
interact even at high individual loading.

--------------------------------------------------------------------------
THE CRITERION
--------------------------------------------------------------------------
An allocation planned on LinDistFlow against a de-rated floor V_plan is AC
insecure at bus m when the neglected loss drop exceeds the planning band:

    LAMBDA(m) = D_err(m) / (V_plan^2 - V_min^2)  >  1

LAMBDA is computable from topology (R, X), the base-case flows, and the
allocated caps alone -- no simulation. LAMBDA <= 1 predicts security.

--------------------------------------------------------------------------
MOBILITY (tau)
--------------------------------------------------------------------------
tau is the time for dispatch at one hub to affect state at another (travel
plus dwell). It does NOT appear above, and that is a result rather than an
omission: the voltage constraint is instantaneous and electrical, so the
timing of energy demand cannot enter it. tau governs ENERGY feasibility --
whether the fleet can meet its departures -- not network security. Section 4
of the report states the service-side criterion where tau does appear.

As tau -> 0 the hubs become one connection point: R_AB -> R_AA, rho -> 1,
S_excl -> 0, and LAMBDA reduces to the single-site condition
    2 R^2 S^2 / V_ref^2 > band,
which is the ordinary stationary-DER envelope safety condition. The mobile
case is therefore a generalisation of the stationary one, not a departure.
"""
from __future__ import annotations
import numpy as np

V_REF = 1.04


# ------------------------------------------------------- generic radial net --
class RadialNet:
    """A radial feeder given as parent/impedance arrays, so that synthetic
    topologies and published test systems share one code path."""

    def __init__(self, parent, r_pu, x_pu, p_kw, q_kvar, s_base_kva=1000.0,
                 v_ref=V_REF):
        self.parent = np.asarray(parent, int)
        self.r = np.asarray(r_pu, float)
        self.x = np.asarray(x_pu, float)
        self.p = np.asarray(p_kw, float)
        self.q = np.asarray(q_kvar, float)
        self.sb = s_base_kva
        self.vref = v_ref
        self.n = len(self.parent)
        self.bidx = np.arange(self.n) - 1          # branch feeding bus i
        self.children = [[] for _ in range(self.n)]
        for j in range(1, self.n):
            self.children[self.parent[j]].append(j)
        order, stack = [], [0]
        while stack:
            v = stack.pop(0); order.append(v); stack.extend(self.children[v])
        self.order = np.array(order)
        self.rev = self.order[::-1]
        self.R = self._path_matrix(self.r)
        self.X = self._path_matrix(self.x)

    def _path_matrix(self, z):
        paths = []
        for i in range(self.n):
            s, v = set(), i
            while v != 0:
                s.add(v); v = self.parent[v]
            paths.append(s)
        M = np.zeros((self.n, self.n))
        for i in range(self.n):
            for j in range(self.n):
                M[i, j] = sum(z[k - 1] for k in (paths[i] & paths[j]))
        return M

    # ---- linear model
    def u_lin(self, p_kw=None, q_kvar=None):
        p = self.p if p_kw is None else p_kw
        q = self.q if q_kvar is None else q_kvar
        return self.vref ** 2 - 2 * (self.R @ (p / self.sb)
                                     + self.X @ (q / self.sb))

    # ---- exact AC by backward/forward sweep (the referee)
    def solve_ac(self, p_kw=None, q_kvar=None, tol=1e-10, itmax=80):
        p = self.p if p_kw is None else p_kw
        q = self.q if q_kvar is None else q_kvar
        S = (p + 1j * q) / self.sb
        z = self.r + 1j * self.x
        V = np.full(self.n, self.vref + 0j)
        Ibr = np.zeros(self.n - 1, dtype=complex)
        for _ in range(itmax):
            Vold = V.copy()
            Inode = np.conj(S / V)
            for j in self.rev:
                if j != 0:
                    Ibr[j - 1] = Inode[j]
                    Inode[self.parent[j]] += Inode[j]
            V[0] = self.vref
            for j in self.order:
                if j != 0:
                    V[j] = V[self.parent[j]] - z[j - 1] * Ibr[j - 1]
            if np.max(np.abs(V - Vold)) < tol:
                break
        return np.abs(V), Ibr

    # ---- the criterion: predicted extra drop LinDistFlow neglects
    def loss_drop(self, p_kw=None, q_kvar=None):
        """D_err[i]: voltage-square drop at bus i that LinDistFlow omits.

        One correction step: compute loss-free branch flows, the loss each
        branch generates, then propagate the extra drop those losses cause
        along each path. Uses only R, X and the injections -- no AC solve.
        """
        p = (self.p if p_kw is None else p_kw) / self.sb
        q = (self.q if q_kvar is None else q_kvar) / self.sb
        # loss-free branch flows (downstream sums)
        Pbr = np.zeros(self.n - 1); Qbr = np.zeros(self.n - 1)
        acc_p, acc_q = p.copy(), q.copy()
        for j in self.rev:
            if j != 0:
                Pbr[j - 1] = acc_p[j]; Qbr[j - 1] = acc_q[j]
                acc_p[self.parent[j]] += acc_p[j]
                acc_q[self.parent[j]] += acc_q[j]
        # loss generated per branch
        ell = (Pbr ** 2 + Qbr ** 2) / self.vref ** 2
        loss = self.r * ell
        # loss flowing through each branch = sum of losses downstream (incl self)
        Ldown = np.zeros(self.n - 1)
        acc = np.zeros(self.n)
        for j in self.rev:
            if j != 0:
                acc[j] += loss[j - 1]
                Ldown[j - 1] = acc[j]
                acc[self.parent[j]] += acc[j]
        # extra drop at bus i = 2 * sum over path of r * L  (plus the small
        # +(r^2+x^2)l term, which acts the other way and is subtracted)
        extra = 2 * self.r * Ldown - (self.r ** 2 + self.x ** 2) * ell
        D = np.zeros(self.n)
        for i in range(self.n):
            v = i
            while v != 0:
                D[i] += extra[v - 1]; v = self.parent[v]
        return D


# ------------------------------------------------------ synthetic topologies --
def random_radial(seed, n=33, n_lat=3, r_lo=0.05, r_hi=1.2, xr=0.7,
                  load_lo=40.0, load_hi=350.0, scale=1.0, s_base=1000.0):
    """A synthetic radial feeder: random branching, MV-plausible impedances.

    Not a published test system and not presented as one. Its purpose is to
    give the criterion many independent topologies to be checked against, so
    that the held-out published feeder is a genuine test rather than the only
    evidence.
    """
    rng = np.random.default_rng(seed)
    parent = np.zeros(n, int)
    trunk = max(6, int(n * rng.uniform(0.35, 0.6)))
    for j in range(1, n):
        if j < trunk:
            parent[j] = j - 1                       # main trunk
        else:
            parent[j] = int(rng.integers(1, j))     # laterals hang off it
    r = rng.uniform(r_lo, r_hi, n - 1) / 160.28      # ohm -> pu on 12.66 kV
    x = r * rng.uniform(xr * 0.6, xr * 1.6, n - 1)
    p = np.zeros(n); q = np.zeros(n)
    p[1:] = rng.uniform(load_lo, load_hi, n - 1) * scale
    q[1:] = p[1:] * rng.uniform(0.3, 0.5, n - 1)
    return RadialNet(parent, r, x, p, q, s_base_kva=s_base)


# ------------------------------------------------- snapshot DOE + corner test --
def allocate_doe(net, hubs, v_plan, caps_kw, fairness="proportional"):
    """Joint per-site envelope allocation at one interval, on LinDistFlow.

    This is the correctly-computed envelope: one LP over all hubs at once, so
    any combination inside the box is secure IN THE LINEAR MODEL. It is not a
    one-at-a-time bound.
    """
    import cvxpy as cp
    H = len(hubs)
    P = cp.Variable(H, nonneg=True)
    e = np.zeros((net.n, H))
    for k, h in enumerate(hubs):
        e[:, k] = 2 * net.R[:, h] / net.sb
    u0 = net.u_lin()
    cons = [u0 - e @ P >= v_plan ** 2, P <= np.asarray(caps_kw, float)]
    obj = cp.sum(cp.log(P + 1e-3)) if fairness == "proportional" else cp.sum(P)
    pr = cp.Problem(cp.Maximize(obj), cons)
    try:
        pr.solve(solver=cp.CLARABEL)
    except Exception:
        return None
    if P.value is None:
        return None
    return np.maximum(P.value, 0.0)


def naive_doe(net, hubs, v_plan, caps_kw):
    """(A) One-at-a-time headroom: each hub perturbed alone. Included to show
    it is a different, and strictly worse, object than allocate_doe."""
    u0 = net.u_lin()
    out = []
    for h in hubs:
        m = 2 * net.R[:, h] / net.sb
        ok = m > 1e-12
        out.append(min(float(np.min((u0[ok] - v_plan ** 2) / m[ok])),
                       float(caps_kw[hubs.index(h)])))
    return np.maximum(np.array(out), 0.0)


def corner_test(net, hubs, P_kw, v_min):
    """Push every hub to its cap simultaneously and judge on the AC solver."""
    p = net.p.copy()
    for k, h in enumerate(hubs):
        p[h] += P_kw[k]
    Vac, _ = net.solve_ac(p_kw=p)
    ul = net.u_lin(p_kw=p)
    D = net.loss_drop(p_kw=p)
    return dict(v_ac=float(Vac.min()),
                v_lin=float(np.sqrt(max(ul.min(), 1e-9))),
                viol=float(max(0.0, v_min - Vac.min())),
                lin_err=float(np.sqrt(max(ul.min(), 1e-9)) - Vac.min()),
                D_at_min=float(D[int(np.argmin(ul))]))


def lambda_index(net, hubs, P_kw, v_min, v_plan):
    """LAMBDA = predicted neglected drop / planning band. >1 predicts failure."""
    p = net.p.copy()
    for k, h in enumerate(hubs):
        p[h] += P_kw[k]
    D = net.loss_drop(p_kw=p)
    ul = net.u_lin(p_kw=p)
    m = int(np.argmin(ul))
    band = v_plan ** 2 - v_min ** 2
    return float(D[m] / band) if band > 1e-12 else np.inf


def coupling(net, ha, hb):
    """rho = shared path resistance / hub A's own path resistance."""
    return float(net.R[ha, hb] / net.R[ha, ha]) if net.R[ha, ha] > 0 else 0.0


def scale_to_vmin(net, target_vmin, lo=0.02, hi=3.0, iters=40):
    """Scale all loads so the base-case AC minimum voltage equals `target`.

    The baseline margin is a swept variable in the validation, so it has to be
    set rather than observed. Scaling loads is the cleanest knob: it changes
    the operating point without touching the topology, so rho is unaffected.
    """
    p0, q0 = net.p.copy(), net.q.copy()
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        net.p, net.q = p0 * mid, q0 * mid
        v = net.solve_ac()[0].min()
        if v > target_vmin:
            lo = mid
        else:
            hi = mid
    net.p, net.q = p0 * lo, q0 * lo
    return lo


def pick_hub_pair(net, rho_target, tol=0.06, min_depth=4):
    """Find two buses whose shared-path fraction is near rho_target."""
    depth = np.array([len({0}) for _ in range(net.n)])
    d = np.zeros(net.n, int)
    for j in net.order:
        if j != 0:
            d[j] = d[net.parent[j]] + 1
    cand = [i for i in range(net.n) if d[i] >= min_depth]
    best, berr = None, 1e9
    for a in cand:
        for b in cand:
            if a == b:
                continue
            r = coupling(net, a, b)
            if abs(r - rho_target) < berr:
                berr, best = abs(r - rho_target), (a, b)
    return (best, berr) if berr < tol else (None, berr)


# =====================================================================
#  N-HUB GENERALISATION AND THE TEMPORAL-AGGREGATION TERM
# =====================================================================
"""
T1  CORNER CERTIFICATION AT N HUBS.
    Under A2, u_i(P) = u_i(0) - 2 sum_h R_ih P_h with R_ih >= 0 elementwise
    (R_ih = sum of r over path(i) & path(h), a sum of positive resistances).
    So u_i is non-increasing in every coordinate of P. A function that is
    non-increasing in each coordinate attains its minimum over a box
    prod_h [0, Pbar_h] at the maximal corner P = Pbar. Hence one evaluation
    at the all-caps corner certifies the entire box, for any N. Nothing in
    the argument is pairwise.

T2  EXACT N-HUB FORM OF D_err.
    D_err(m) = 2 sum_{k in path(m)} r_k L_k with L_k = (1/u) sum_{l >= k} r_l S_l^2.
    Exchange the order of summation: a branch l contributes to every k in
    path(m) that lies upstream of l, and the total resistance of those k is
    exactly R_{m,l}, the shared resistance of bus m and branch l. Therefore

        D_err(m) = (2/u) sum_l r_l R_ml S_l^2                              (*)

    which is exact, needs no pairwise collapse, and holds for any N. Writing
    S_l = B_l + sum_h 1[l in path(h)] P_h and expanding (*):

        D_err(m) = (2/u) [ P' C^(m) P + 2 b^(m)' P + c^(m) ]
        C^(m)_hh' = sum_{l in path(h) & path(h')} r_l R_ml
        b^(m)_h   = sum_{l in path(h)}          r_l R_ml B_l
        c^(m)     = sum_l                       r_l R_ml B_l^2

    C^(m) is a Gram matrix of the vectors (sqrt(r_l R_ml) 1[l in path(h)])_l,
    hence positive semidefinite: D_err is a convex quadratic in the caps. The
    two-hub expression in the header is the H=2 case of this, with
    C_AB/C_AA -> rho^2 in the limit where the hubs' own segments are short.

T3  TEMPORAL AGGREGATION.
    An envelope allocated once per interval of length Delta is planned against
    the interval-mean exogenous injections pbar. Within the interval the plant
    realises p(t). In LinDistFlow the resulting extra drop is exact and FIRST
    order:

        D_agg(m,t) = (2/S_b) sum_j [ R_mj dp_j(t) + X_mj dq_j(t) ],
        dp_j(t) = p_j(t) - pbar_j

    and if injection j drifts at bounded rate |dp_j/dt| <= gamma_j, then
    max_t |dp_j| <= gamma_j Delta / 2, giving the planning-time bound

        D_agg(m) <= (Delta / (2 S_b)) sum_j [ R_mj gamma_j + X_mj gamma^q_j ]

    Collapsing onto two hubs with A at m: D_agg(A) <= (Delta/2S_b) R_AA
    [ rho * gamma_shared + (1-rho) * gamma_excl ]. Note the structural
    contrast with D_err: D_err is QUADRATIC in power and carries rho^2 (via
    C^(m)); D_agg is LINEAR in the drift and carries rho^1. They are additive
    at first order, and

        LAMBDA_total(m) = ( D_err(m) + D_agg(m) ) / (V_plan^2 - V_min^2).

    D_agg vanishes at a static operating point, which is why the snapshot
    validation saw only D_err and found it flat in rho.
"""


def err_form(net, hubs):
    """Exact N-hub quadratic form (C, b, c) of D_err at the bus that binds.

    Returns a callable D(P_kw) plus the pieces, evaluated for the given hub
    list. Verified against loss_drop() elementwise in the validation.
    """
    n = net.n
    # branch l is indexed by its downstream bus (l = bus j means branch j-1)
    # base flows B_l with hubs at zero
    p = net.p / net.sb
    q = net.q / net.sb
    Pbr = np.zeros(n); Qbr = np.zeros(n)
    ap, aq = p.copy(), q.copy()
    for j in net.rev:
        if j != 0:
            Pbr[j] = ap[j]; Qbr[j] = aq[j]
            ap[net.parent[j]] += ap[j]; aq[net.parent[j]] += aq[j]
    onpath = np.zeros((n, len(hubs)))
    for k, h in enumerate(hubs):
        v = h
        while v != 0:
            onpath[v, k] = 1.0; v = net.parent[v]

    def pieces(m):
        onp_m = np.zeros(n); v = m
        while v != 0:
            onp_m[v] = 1.0; v = net.parent[v]
        # w_l = 2 r_l R_ml  -  (r_l^2 + x_l^2) 1[l in path(m)]
        # the second piece is the +(r^2+x^2)l term of exact DistFlow, which
        # acts the other way; including it makes the form exact, not just
        # dominant-term.
        w = np.zeros(n)
        for j in range(1, n):
            w[j] = (2.0 * net.r[j - 1] * net.R[m, j]
                    - (net.r[j - 1] ** 2 + net.x[j - 1] ** 2) * onp_m[j])
        C = (onpath * w[:, None]).T @ onpath
        b = (onpath * (w * Pbr)[:, None]).sum(0)
        c = float((w * (Pbr ** 2 + Qbr ** 2)).sum())
        return C, b, c

    def D(m, P_kw):
        C, b, c = pieces(m)
        P = np.asarray(P_kw, float) / net.sb
        return float((P @ C @ P + 2 * b @ P + c) / net.vref ** 2)

    return pieces, D


def agg_drop(net, dp_kw, dq_kvar=None):
    """D_agg[i]: exact first-order extra drop from intra-interval deviation.

    dp_kw is the realised-minus-planned injection vector for one minute.
    Positive dp (more load than planned) gives positive D_agg (more drop).
    """
    dq = np.zeros(net.n) if dq_kvar is None else np.asarray(dq_kvar, float)
    return 2.0 * (net.R @ (np.asarray(dp_kw, float) / net.sb)
                  + net.X @ (dq / net.sb))


def agg_bound(net, m, gamma_kw_per_min, delta_min, gamma_q=None):
    """Planning-time bound on D_agg(m) from drift-rate limits (T3)."""
    gq = np.zeros(net.n) if gamma_q is None else np.asarray(gamma_q, float)
    return float(delta_min / (2 * net.sb)
                 * (net.R[m] @ np.asarray(gamma_kw_per_min, float)
                    + net.X[m] @ gq))


# ------------------------------------------------------ published feeders --
def _matpower_case(path, s_base_kva=1000.0, v_base_kv=12.66):
    """Parse a MATPOWER radial distribution case (branch R/X in ohm, load kW).

    Used for IEEE 69-bus: MATPOWER `data/case69.m`, whose header cites
    M. E. Baran and F. F. Wu, "Optimal capacitor placement on radial
    distribution systems", IEEE Trans. Power Delivery 4(1):725-734, 1989.
    Not reconstructed from memory -- the file is fetched and parsed.
    """
    import re
    t = open(path).read()

    def blk(name):
        mm = re.search(r"mpc\." + name + r"\s*=\s*\[(.*?)\n\s*\];", t, re.S)
        rows = []
        for line in mm.group(1).splitlines():
            line = line.split("%")[0].strip().rstrip(";").strip()
            if line:
                rows.append([float(z) for z in re.split(r"[\s,]+", line)])
        return rows

    bus, br = blk("bus"), blk("branch")
    ids = [int(b[0]) for b in bus]
    idx = {b: i for i, b in enumerate(ids)}
    n = len(bus)
    zb = v_base_kv ** 2 / (s_base_kva / 1000.0)
    parent = np.zeros(n, int)
    r = np.zeros(n - 1); x = np.zeros(n - 1)
    # order branches so that each bus's feeding branch is at index bus-1
    child_of = {}
    for row in br:
        f, tt = idx[int(row[0])], idx[int(row[1])]
        child_of[tt] = (f, row[2] / zb, row[3] / zb)
    for j in range(1, n):
        f, rr, xx = child_of[j]
        parent[j] = f; r[j - 1] = rr; x[j - 1] = xx
    p = np.array([b[2] for b in bus]); q = np.array([b[3] for b in bus])
    return RadialNet(parent, r, x, p, q, s_base_kva=s_base_kva)


def ieee69(path="case69.m"):
    return _matpower_case(path)


def ieee33():
    """IEEE 33-bus from the project's own published branch table."""
    import system as S
    par, ch, bidx, r, x, order = S.feeder_topology()
    p = np.zeros(33); q = np.zeros(33)
    for b, (pp, qq) in S.LOAD.items():
        p[b - 1] = pp; q[b - 1] = qq
    rr = np.array([r[bidx[j]] for j in range(1, 33)])
    xx = np.array([x[bidx[j]] for j in range(1, 33)])
    parent = np.array([max(par[j], 0) for j in range(33)])
    return RadialNet(parent, rr, xx, p, q)
