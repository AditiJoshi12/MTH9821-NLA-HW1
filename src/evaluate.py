"""
evaluate.py -- Independent evaluation of frozen threshold policies
(Part 5 machinery, used now to preview LS; NN plugs in later).

* Prices: for each case and S0 in {60, 80, 100}, 50,000 fresh paths
  (seed 4000 + 10c + a, batches of 5,000), SAME paths for every policy.
  Q_i = e^{-r tau_i}(K - S_tau_i)^+ ; report mean, SE = sd/sqrt(n), and
  mean +/- 1.96 SE.  Because the evaluation paths are independent of the
  training paths, E[Q] is the value of the FROZEN policy, which is at most
  the optimal grid value V_{delta,N}(0,S0) (any stopping rule is feasible,
  the optimum is the supremum).  So a LS mean clearly above the
  reference would signal an error, not a better policy.
* Boundary errors E_mean, E_max against the reference boundary.
* Dividend-ordering diagnostics A, B, F (Part 1 "checks").
"""

import numpy as np
import pandas as pd

import config as cfg
import simulation as sim
from lsm import apply_hard_rule


def price_policies(c: int, boundaries: dict):
    """boundaries: {method_name: b array (N+1,)}.  Returns (rows, paired).

    rows  : one dict per (method, S0): mean, se, lo, hi
    paired: dict (method_a, method_b, S0) -> (mean diff, se diff)
    """
    N, delta = sim.CASES[c]
    tg = cfg.TimeGrid(N)
    rows, paired = [], {}
    for a, s0 in enumerate(sim.EVAL_SPOTS):
        Q = {m: [] for m in boundaries}
        for S in sim.evaluation_batches(c, a):
            for m, b in boundaries.items():
                Q[m].append(apply_hard_rule(S, b, tg)[0])
        Q = {m: np.concatenate(v) for m, v in Q.items()}
        for m, q in Q.items():
            mean, se = q.mean(), q.std(ddof=1) / np.sqrt(q.size)
            rows.append(dict(case=c, N=N, delta=delta, method=m, S0=s0,
                             mean=mean, se=se, lo=mean - 1.96 * se, hi=mean + 1.96 * se))
        ms = list(Q)
        for i in range(len(ms)):
            for k in range(i + 1, len(ms)):
                d = Q[ms[i]] - Q[ms[k]]
                paired[(ms[i], ms[k], s0)] = (d.mean(), d.std(ddof=1) / np.sqrt(d.size))
    return rows, paired


def boundary_errors(b_hat, b_ref, N):
    e = np.abs(b_hat[:N] - b_ref[:N])
    return dict(E_mean=e.mean() / cfg.K, E_max=e.max() / cfg.K, j_at_max=int(e.argmax()))


def ordering_diagnostics(b_div, b_nodiv, N, tol=1e-8):
    """A, B, F with g_j = b^{0.0125}_j - b^0_j (Part 1 checks)."""
    js = cfg.TimeGrid(N).j_star
    g = b_div[:N] - b_nodiv[:N]
    return dict(A=int((g[:js] > tol).sum()),
                B=max(0.0, float(g[:js].max())) / cfg.K,
                F=float(np.abs(g[js:N]).max()) / cfg.K)
