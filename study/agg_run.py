"""One closed-loop DOE run with per-minute state dumped for Lambda_total.

Run as:  HUB_BUSES=... python agg_run.py <bus> <band> <out.npz>

Dumps, at every simulated minute: the full nodal injection vector actually
realised, the 15-minute planning vector the envelope was allocated against,
and the AC voltages from the backward/forward sweep. Everything the criterion
is scored on is computed afterwards from these arrays, so no reported
violation comes from the model the allocation was optimised against.
"""
import os, sys, pickle
import numpy as np
import system as S, run as R, coord, powerflow as PF

bus, band, out = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
d = R.setup()
vplan = S.V_MIN + band
pmax15 = coord.envelope_doe(d, fairness=os.environ.get("DOE_FAIR", "proportional"),
                            vmin=vplan, verbose=True)
sim = R.simulate(d, mode="hier", pmax15=pmax15, lam15=None,
                 env_on_net=True, ctrl_int=int(os.environ.get("CTRL_INT", 5)),
                 verbose=False)
H, K = len(S.HUBS), S.K_DAY
ctrl = sim["Pchg"].sum(1) + 0.0
hD = S.HUB_IDX["D"]
ctrl[hD] += sim["Pbess"][0] - sim["Pbess"][1]
exo = d["exo"]
P = exo["P_feeder"].copy(); Q = exo["Q_feeder"].copy()
for h in range(H):
    P[S.HUBS[h].bus - 1] += ctrl[h]
pf = d["feeder"].solve(P, Q)

# the planning-time injection vector: 15-minute means, repeated over the
# interval. This is exactly what envelope_doe saw.
P15 = P.reshape(S.N_BUS, S.T_DAY, 15).mean(2).repeat(15, axis=1)
Q15 = Q.reshape(S.N_BUS, S.T_DAY, 15).mean(2).repeat(15, axis=1)
np.savez_compressed(out, P=P, Q=Q, P15=P15, Q15=Q15, Vm=pf["Vm"],
                    pmax15=pmax15, ctrl=ctrl, bus=bus, band=band,
                    hubbus=np.array([h.bus for h in S.HUBS]),
                    feeder=os.environ.get("FEEDER", "ieee33"),
                    n_veh=int(os.environ.get("N_VEH", 12)))
print("dumped", out, "Vmin %.4f uv %d" % (pf["Vm"].min(),
      int((pf["Vm"] < S.V_MIN - 1e-6).sum())), flush=True)
