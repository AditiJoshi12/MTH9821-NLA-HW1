"""
simulation.py -- Exact path simulation (Part 2) and the training
distribution A.

Transition between post-jump grid states (assignment, Part 2):

    S_{j+1} = S_j exp[(r - sigma^2/2) h + sigma sqrt(h) Z_{j+1}] (1-delta)^{1{j+1 is a dividend index}}

* "Exact": GBM is sampled from its exact lognormal law -- no Euler error.
* Dividend dates are identified by INTEGER indices (config.TimeGrid).
* A path that STARTS at a dividend index is already post-jump: the jump
  factor applies only on arrival at a dividend index (j+1), never at the
  starting index.  (Needed for Part 4's random starts.)

RANDOM-DRAW ORDER -- ASSUMPTION (flag in the report)
----------------------------------------------------
The assignment says the draw order is documented in the supplied
README.md, which we have not seen.  Until then we use the order below,
chosen to be simple and reproducible.  If README.md differs, only the
functions `sample_A`, `training_paths_LS` and `evaluation_normals`
need to change.
  * sample_A(rng, n):  u = rng.random(n)            (mixture coin, <1/2 -> log-uniform branch)
                       a = rng.uniform(log .001, 0, n)
                       b = rng.uniform(0.2, 1.2, n)
                       A = K * where(u < 1/2, exp(a), b)
  * LS training (seed 1000+c): S0 = sample_A(rng, 32768), THEN
                       Z = rng.standard_normal((32768, N))
  * evaluation (seed 4000+10c+a): 10 batches of 5,000 paths, each
                       Z_batch = rng.standard_normal((5000, N)), in order.
"""

import numpy as np

import config as cfg

LOG_A_LO = np.log(0.001)


# ---------------------------------------------------------------------------
# Training distribution A
# ---------------------------------------------------------------------------
def sample_A(rng: np.random.Generator, n: int) -> np.ndarray:
    """Mixture: w.p. 1/2 log(A/K) ~ U[log 0.001, 0]; w.p. 1/2 A/K ~ U[0.2, 1.2].

    We draw ALL three uniforms for every path (rather than only the branch
    that is used) so the number of draws is fixed and the stream position
    after the call does not depend on the coin outcomes.
    """
    coin = rng.random(n)
    a = rng.uniform(LOG_A_LO, 0.0, n)
    b = rng.uniform(0.2, 1.2, n)
    return cfg.K * np.where(coin < 0.5, np.exp(a), b)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def step_factors(tg: cfg.TimeGrid, delta: float, Z: np.ndarray, j0: int = 0) -> np.ndarray:
    """Multiplicative factors for steps j0 -> j0+1 -> ... given normals Z.

    Z has shape (n, k): column i drives step (j0+i) -> (j0+i+1).
    Returns array of the same shape with the dividend factor included on
    arrival at a dividend index.
    """
    k = Z.shape[1]
    drift = (cfg.R - 0.5 * cfg.SIGMA ** 2) * tg.h
    vol = cfg.SIGMA * np.sqrt(tg.h)
    arrive = np.arange(j0 + 1, j0 + k + 1)                  # arrival indices
    jump = np.where(tg.is_div[arrive], 1.0 - delta, 1.0)   # (k,)
    return np.exp(drift + vol * Z) * jump[None, :]


def paths_from_t0(S0: np.ndarray, Z: np.ndarray, tg: cfg.TimeGrid, delta: float) -> np.ndarray:
    """Full paths S_0..S_N (shape (n, N+1)) from t_0, float64.

    Product of factors is computed as exp(cumsum(log)) for numerical
    stability; the dividend enters as log(1-delta) at integer indices.
    """
    f = step_factors(tg, delta, Z, 0)
    logS = np.log(S0)[:, None] + np.concatenate(
        [np.zeros((len(S0), 1)), np.cumsum(np.log(f), axis=1)], axis=1)
    return np.exp(logS)


def paths_from_J(J: np.ndarray, SJ: np.ndarray, Z: np.ndarray, tg: cfg.TimeGrid,
                 delta: float) -> np.ndarray:
    """Paths started at random indices J with S_J = SJ (post-jump if J is a
    dividend index).  Entries before J are NaN.  Z has shape (n, N);
    column i drives step i -> i+1, and columns i < J are simply unused, so
    a path's normals do not depend on other paths.  (Part 4 path banks.)
    """
    n, N = len(J), tg.N
    f = step_factors(tg, delta, Z, 0)                      # (n, N)
    cols = np.arange(N)[None, :]
    logf = np.where(cols >= J[:, None], np.log(f), 0.0)    # ignore steps before J
    logS = np.concatenate([np.zeros((n, 1)), np.cumsum(logf, axis=1)], axis=1)
    S = SJ[:, None] * np.exp(logS)                         # constant up to J
    S[np.arange(N + 1)[None, :] < J[:, None]] = np.nan
    return S


# ---------------------------------------------------------------------------
# Seeded path sets (see ASSUMPTION above)
# ---------------------------------------------------------------------------
N_TRAIN_LS = 32_768
N_EVAL = 50_000
EVAL_BATCH = 5_000
EVAL_SPOTS = (60.0, 80.0, 100.0)
CASES = {0: (180, 0.0), 1: (180, 0.0125), 2: (360, 0.0), 3: (360, 0.0125)}


def training_paths_LS(c: int):
    """Part 3 training paths for case c (seed 1000 + c). Returns (tg, S)."""
    N, delta = CASES[c]
    tg = cfg.TimeGrid(N)
    rng = np.random.default_rng(1000 + c)
    S0 = sample_A(rng, N_TRAIN_LS)
    Z = rng.standard_normal((N_TRAIN_LS, N))
    return tg, paths_from_t0(S0, Z, tg, delta)


def evaluation_batches(c: int, a: int):
    """Yield path batches (5,000 x (N+1)) for case c, starting-price index a.

    Seed 4000 + 10c + a.  The SAME batches are used for every policy
    (common random numbers), so price differences are paired.
    """
    N, delta = CASES[c]
    tg = cfg.TimeGrid(N)
    rng = np.random.default_rng(4000 + 10 * c + a)
    s0 = EVAL_SPOTS[a]
    for _ in range(N_EVAL // EVAL_BATCH):
        Z = rng.standard_normal((EVAL_BATCH, N))
        yield paths_from_t0(np.full(EVAL_BATCH, s0), Z, tg, delta)


def martingale_check(c: int):
    """Part 2 check on the FINAL S0 = 100 sample (a = 2) of case c.

    E[S_T] = S0 e^{rT} (1-delta)^3 under Q.  Returns the sample mean, its
    standard error and z = (mean - theory)/se.  |z| should look like a
    draw from N(0,1): |z| < 2 in ~95% of such checks.
    """
    N, delta = CASES[c]
    ST = np.concatenate([b[:, -1] for b in evaluation_batches(c, 2)])
    theory = 100.0 * np.exp(cfg.R * cfg.T) * (1 - delta) ** 3
    mean, se = ST.mean(), ST.std(ddof=1) / np.sqrt(ST.size)
    return dict(case=c, N=N, delta=delta, mean_ST=mean, theory=theory,
                diff=mean - theory, se=se, z=(mean - theory) / se)
