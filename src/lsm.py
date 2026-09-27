"""
lsm.py -- Part 3: Longstaff-Schwartz backward cash-flow regression with
the assignment's THRESHOLD extraction and dividend cap.

All cash flows are in TIME-ZERO dollars (discounted to t_0), so targets
from different exercise dates can be regressed together.

Step-by-step (numbers refer to the assignment's Part 3 list)
------------------------------------------------------------
1. Y_i = e^{-rT}(K - S_{i,N})^+.  For j = N-1..0 regress Y on
   [1, x, x^2, x^3], x = S_j/K, over in-the-money rows (S_j < K), using
   np.linalg.lstsq (LAPACK gelsd = SVD-based least squares, as required).
   Clip:  c_j(s) = min{K e^{-r t_{j+1}}, max{0, c_raw(s)}}.
   Fallbacks: 1-3 ITM rows -> constant = mean of their targets;
              0 ITM rows    -> c_j(s) = K e^{-r t_{j+1}}.
2. H_l = e^{-r t_j}(K - s_l) - c_j(s_l) on s_l = 0.1 l, l = 0..1000.
   Positive-to-negative crossing at l: H_{l-1} >= 0 and H_l < 0.  Take the
   LARGEST such l, linearly interpolate the zero -> candidate.  None -> K.
3. b_j = min{U_j, candidate}.  On paths with S_j <= b_j and S_j < K,
   set Y = e^{-r t_j}(K - S_j).  Other paths keep Y.
4. Freeze b, set b_N = K, replay the hard rule forward and check the
   replayed discounted cash flows equal the final Y exactly.

Why the clip bounds continuation and gives H_0 > 0
--------------------------------------------------
From t_j the earliest further exercise is t_{j+1} and the payoff is at
most K, so the time-zero continuation value lies in [0, K e^{-r t_{j+1}}].
Hence H_0 >= e^{-r t_j}K - K e^{-r t_{j+1}} = K e^{-r t_j}(1 - e^{-rh}) > 0:
exercising at s = 0 always beats the clipped continuation, so the
exercise set contains a neighbourhood of 0 and a crossing is expected.
"""

from dataclasses import dataclass, field

import numpy as np

import config as cfg

S_GRID = 0.1 * np.arange(1001)          # s_l = 0.1 l, l = 0..1000
X_GRID = S_GRID / cfg.K


def _design(x):
    """Regressors 1, x, x^2, x^3."""
    return np.vander(x, 4, increasing=True)


@dataclass
class LSResult:
    N: int
    delta: float
    boundary: np.ndarray                    # (N+1,), b_N = K
    candidate: np.ndarray                   # (N,) before the cap
    coef: np.ndarray                        # (N, 4) raw coefficients (NaN on fallback)
    fallback: dict = field(default_factory=dict)   # j -> 'const-mean(k rows)' | 'no-ITM'
    multi_cross_dates: list = field(default_factory=list)
    n_cross: np.ndarray = None              # (N,) number of +/- crossings
    capped_dates: list = field(default_factory=list)
    replay_max_abs_diff: float = np.nan     # replay check (should be 0)
    train_mean_Y: float = np.nan            # in-sample mean (biased; info only)


def crossing_candidate(H):
    """Largest positive-to-negative crossing of H on S_GRID.

    Returns (candidate, number_of_crossings).
    """
    idx = np.flatnonzero((H[:-1] >= 0) & (H[1:] < 0)) + 1   # l in 1..1000
    if idx.size == 0:
        return cfg.K, 0
    l = idx[-1]
    # linear zero between s_{l-1} (H >= 0) and s_l (H < 0)
    lam = H[l - 1] / (H[l - 1] - H[l])
    return float(S_GRID[l - 1] + lam * (S_GRID[l] - S_GRID[l - 1])), int(idx.size)


def fit_ls(S: np.ndarray, tg: cfg.TimeGrid, delta: float) -> LSResult:
    """Fit the capped LS threshold policy on training paths S (n, N+1)."""
    N = tg.N
    t = tg.t
    U = cfg.dividend_cap(tg, delta)
    disc = np.exp(-cfg.R * t)                         # e^{-r t_j}

    Y = disc[N] * np.maximum(cfg.K - S[:, N], 0.0)    # time-zero dollars
    b = np.empty(N + 1); b[N] = cfg.K
    cand = np.empty(N)
    coef = np.full((N, 4), np.nan)
    n_cross = np.zeros(N, dtype=int)
    res = LSResult(N, delta, b, cand, coef, n_cross=n_cross)

    for j in range(N - 1, -1, -1):
        Sj = S[:, j]
        itm = Sj < cfg.K
        k = int(itm.sum())
        cap_c = cfg.K * disc[j + 1]                   # K e^{-r t_{j+1}}

        # --- step 1: regression with fallbacks -------------------------
        if k >= 4:
            beta, *_ = np.linalg.lstsq(_design(Sj[itm] / cfg.K), Y[itm], rcond=None)
            coef[j] = beta
            c_raw = _design(X_GRID) @ beta
        elif k >= 1:
            c_raw = np.full_like(S_GRID, Y[itm].mean())
            res.fallback[j] = f"const-mean({k} rows)"
        else:
            c_raw = np.full_like(S_GRID, cap_c)
            res.fallback[j] = "no-ITM"
        c = np.minimum(cap_c, np.maximum(0.0, c_raw))

        # --- step 2: threshold from the largest +/- crossing -------------
        H = disc[j] * (cfg.K - S_GRID) - c
        cand[j], n_cross[j] = crossing_candidate(H)
        if n_cross[j] > 1:
            res.multi_cross_dates.append(j)

        # --- step 3: dividend cap and target update ----------------------
        if cand[j] > U[j]:
            res.capped_dates.append(j)
        b[j] = min(U[j], cand[j])
        ex = (Sj <= b[j]) & itm
        Y[ex] = disc[j] * (cfg.K - Sj[ex])

    # --- step 4: replay the frozen hard rule -------------------------------
    Q, _ = apply_hard_rule(S, b, tg)
    res.replay_max_abs_diff = float(np.max(np.abs(Q - Y)))
    res.train_mean_Y = float(Y.mean())
    return res


def apply_hard_rule(S: np.ndarray, b: np.ndarray, tg: cfg.TimeGrid, j_start=None):
    """Stop at the first j (>= start) with S_j <= b_j and S_j < K; settle at N.

    Returns (Q, tau): Q = payoff discounted to TIME ZERO; tau = stop index.
    (Callers that need discounting to t_J multiply by e^{r t_J}.)
    Dates before a random start j_start never trigger exercise.
    """
    N = tg.N
    with np.errstate(invalid="ignore"):
        hit = (S[:, :N] <= b[None, :N]) & (S[:, :N] < cfg.K)
    hit = np.concatenate([hit, np.ones((S.shape[0], 1), bool)], axis=1)
    if j_start is not None:
        hit &= np.arange(N + 1)[None, :] >= j_start[:, None]
    tau = hit.argmax(axis=1)
    ST = S[np.arange(S.shape[0]), tau]
    Q = np.exp(-cfg.R * tg.t[tau]) * np.maximum(cfg.K - ST, 0.0)
    return Q, tau
