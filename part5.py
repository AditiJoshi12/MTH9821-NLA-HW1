"""
part5.py -- Part 5: independent evaluation of the frozen policies.

    1. Prices and uncertainty   (price_table)
    2. Boundary accuracy        (boundary_accuracy, n_effect)
    3. Boundary perturbation    (perturbation, perturbation_sweep)

Conventions (assignment)
------------------------
* Case c, starting-price index a (S0 = 60, 80, 100): 50,000 paths with
  seed 4000 + 10c + a, in batches of at most 5,000 (simulation.evaluation_batches).
  The SAME normals are used for every policy -> paired comparisons.
* Q_i = e^{-r tau_i}(K - S_tau_i)^+, hard rule: first j with S_j <= b_j and
  S_j < K, else settle at N.  Mean, SE = sd/sqrt(50,000), mean +/- 1.96 SE.
* float64 throughout.

Why E[Q] <= V_{delta,N}(0, S0)
------------------------------
The frozen threshold rule is a stopping time on the exercise grid that uses
only the observed prices, so it is one of the rules the supremum in
V_{delta,N} ranges over.  Its expected payoff is therefore at most the
optimum.  The evaluation paths are independent of the training data, so the
sample mean is an UNBIASED estimate of that policy value -- unlike the
in-sample LS targets, which are biased upward by fitting to the same paths.
A mean significantly ABOVE the reference would signal a bug (or a reference
error), not a better policy.  We test this with z = (mean - V_ref)/SE.
"""

import time

import numpy as np
import pandas as pd

import config as cfg
import simulation as sim
import evaluate as ev
from lsm import apply_hard_rule
from reference import load_reference

SHIFTS = (-0.02, 0.0, 0.02)                       # assignment's perturbation
SWEEP = tuple(np.round(np.linspace(-0.08, 0.08, 17), 3))   # supplementary (ours)


# ---------------------------------------------------------------------------
# 1. Prices
# ---------------------------------------------------------------------------
def price_table(boundaries_by_case: dict):
    """boundaries_by_case: {c: {method: b}}.  Returns (prices, paired, timings).

    Adds, per row, the reference value and z = (mean - V_ref)/SE.
    """
    price_rows, pair_rows, timings = [], [], {}
    for c, bs in boundaries_by_case.items():
        N, d = sim.CASES[c]
        ref = load_reference(N, d)
        t0 = time.perf_counter()
        rows, paired = ev.price_policies(c, bs)
        timings[c] = time.perf_counter() - t0
        for r in rows:
            r["ref_value"] = ref.value_at(r["S0"])
            # S0 = 60: every path exercises at t_0, Q = 40 exactly (SE ~ 1e-17).
            # The 2e-6 gap to the reference is the reference's own grid
            # interpolation error, so z is undefined there (NaN).
            r["z_vs_ref"] = ((r["mean"] - r["ref_value"]) / r["se"]) if r["se"] > 1e-10 else np.nan
            price_rows.append(r)
        for (m1, m2, s0), (md, se) in paired.items():
            pair_rows.append(dict(case=c, pair=f"{m1} - {m2}", S0=s0, mean_diff=md, se=se))
    return pd.DataFrame(price_rows), pd.DataFrame(pair_rows), timings


# ---------------------------------------------------------------------------
# 2. Boundary accuracy
# ---------------------------------------------------------------------------
def boundary_accuracy(boundaries_by_case: dict):
    """E_mean, E_max of each fitted method against the reference for the
    SAME N (the assignment's comparison)."""
    rows = []
    for c, bs in boundaries_by_case.items():
        N, d = sim.CASES[c]
        ref = load_reference(N, d)
        for m, b in bs.items():
            if m.startswith("ref"):
                continue
            rows.append(dict(case=c, N=N, delta=d, method=m, **ev.boundary_errors(b, ref.boundary, N)))
    return pd.DataFrame(rows)


def n_effect():
    """How much does the OPTIMAL boundary itself move from N=180 to 360?
    Measured at the common dates t_j^{180} = t_{2j}^{360} with the same
    E_mean / E_max formulas.  This is the yardstick for reading a fitted
    method's change with N: if its error is much larger, the change with N
    is learning noise, not the effect of more exercise dates."""
    rows = []
    for d in cfg.DELTAS:
        b1 = load_reference(180, d).boundary
        b2 = load_reference(360, d).boundary
        e = np.abs(b2[0:360:2] - b1[:180])
        rows.append(dict(delta=d, E_mean_ref360_vs_ref180=e.mean() / cfg.K,
                         E_max_ref360_vs_ref180=e.max() / cfg.K))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Boundary perturbation (case 3, S0 = 100, existing evaluation paths)
# ---------------------------------------------------------------------------
def shifted_boundary(b_nn: np.ndarray, a: float, U: np.ndarray) -> np.ndarray:
    """b^(a)_j = min{U_j, max{0, b_j + aK}} for j < N, b^(a)_N = K."""
    N = len(U)
    out = np.empty(N + 1)
    out[:N] = np.minimum(U, np.maximum(0.0, b_nn[:N] + a * cfg.K))
    out[N] = cfg.K
    return out


def _collect(c, a_idx, boundaries, tg):
    """Run every boundary on the same evaluation batches; return Q and tau."""
    Q = {k: [] for k in boundaries}
    tau = {k: [] for k in boundaries}
    for S in sim.evaluation_batches(c, a_idx):
        for k, b in boundaries.items():
            q, t = apply_hard_rule(S, b, tg)
            Q[k].append(q)
            tau[k].append(t)
    return ({k: np.concatenate(v) for k, v in Q.items()},
            {k: np.concatenate(v) for k, v in tau.items()})


def perturbation(b_nn: np.ndarray, c: int = 3, a_idx: int = 2, shifts=SHIFTS):
    """Paired payoff differences Q^(a) - Q^(0) plus mechanism diagnostics.

    Diagnostics (ours, to explain the numbers):
      applied_shift_mean : mean over j<N of (b^(a)_j - b^(0)_j)/K -- smaller
                           than |a| where the cap U_j or the floor 0 binds
      cap_binds_dates    : dates where the shifted boundary is cut by U_j
      frac_paths_changed : share of paths whose stopping time changes;
                           only these paths can contribute to the difference
      mean_diff_changed  : mean Q^(a) - Q^(0) on those paths
      frac_earlier/later : direction of the change in stopping time
    """
    N, d = sim.CASES[c]
    tg = cfg.TimeGrid(N)
    U = cfg.dividend_cap(tg, d)
    bs = {a: shifted_boundary(b_nn, a, U) for a in shifts}
    Q, tau = _collect(c, a_idx, bs, tg)
    rows = []
    for a in shifts:
        diff = Q[a] - Q[0.0]
        ch = tau[a] != tau[0.0]
        raw = b_nn[:N] + a * cfg.K
        rows.append(dict(
            case=c, S0=sim.EVAL_SPOTS[a_idx], a=a,
            mean_Q=Q[a].mean(), se_Q=Q[a].std(ddof=1) / np.sqrt(Q[a].size),
            mean_diff=diff.mean(), se_diff=diff.std(ddof=1) / np.sqrt(diff.size),
            applied_shift_mean=float(np.mean(bs[a][:N] - bs[0.0][:N]) / cfg.K),
            cap_binds_dates=int(np.sum(raw > U)),
            floor_binds_dates=int(np.sum(raw < 0)),
            frac_paths_changed=float(ch.mean()),
            frac_earlier=float((tau[a] < tau[0.0]).mean()),
            frac_later=float((tau[a] > tau[0.0]).mean()),
            mean_diff_changed=float(diff[ch].mean()) if ch.any() else 0.0))
    return pd.DataFrame(rows)


def perturbation_sweep(b_nn: np.ndarray, c: int = 3, a_idx: int = 2):
    """SUPPLEMENTARY (not required): the same paired experiment over a finer
    grid of shifts, to show the shape of price vs boundary error."""
    return perturbation(b_nn, c, a_idx, shifts=SWEEP)
