"""Backward/forward-sweep AC power flow for the radial 33-bus feeder,
vectorised over the 1440 time steps. Used to EVALUATE every case on the
true nonlinear network, independently of the model each case optimised."""
from __future__ import annotations
import numpy as np
import system as S


class Feeder:
    def __init__(self):
        self.parent, self.children, self.bidx, self.r, self.x, self.order = \
            S.feeder_topology()
        self.z = self.r + 1j * self.x
        self.rev = self.order[::-1]
        self.R = S.path_resistance_matrix(self.parent, self.bidx, self.r)
        self.smax = S.branch_rating_pu()

    def solve(self, P_kw, Q_kvar, tol=1e-9, itmax=60):
        """P_kw,Q_kvar : (33,K) consumed power. Returns dict of results."""
        nb, K = P_kw.shape
        Sb = (P_kw + 1j * Q_kvar) / S.S_BASE_KVA
        V = np.full((nb, K), S.V_REF + 0j, dtype=complex)
        Ibr = np.zeros((len(self.r), K), dtype=complex)
        for _ in range(itmax):
            Vold = V.copy()
            Iload = np.conj(Sb / V)
            Inode = Iload.copy()
            for j in self.rev:
                if self.parent[j] >= 0:
                    Ibr[self.bidx[j]] = Inode[j]
                    Inode[self.parent[j]] += Inode[j]
            V[0] = S.V_REF
            for j in self.order:
                if self.parent[j] >= 0:
                    V[j] = V[self.parent[j]] - self.z[self.bidx[j]] * Ibr[self.bidx[j]]
            if np.max(np.abs(V - Vold)) < tol:
                break
        Vm = np.abs(V)
        loss_kw = (np.abs(Ibr) ** 2 * self.r[:, None]).sum(0) * S.S_BASE_KVA
        Sbr = V[[b[0] - 1 for b in S.BRANCH]] * np.conj(Ibr)      # p.u.
        Ssub = (V[0] * np.conj(Inode[0]))
        return dict(Vm=Vm, loss_kw=loss_kw,
                    Sbr_kva=np.abs(Sbr) * S.S_BASE_KVA,
                    Pbr_kw=Sbr.real * S.S_BASE_KVA,
                    Psub_kw=Ssub.real * S.S_BASE_KVA,
                    Qsub_kvar=Ssub.imag * S.S_BASE_KVA,
                    Ssub_kva=np.abs(Ssub) * S.S_BASE_KVA)
