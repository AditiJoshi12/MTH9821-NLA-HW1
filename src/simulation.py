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

RANDOM-DRAW AND ARITHMETIC CONVENTIONS (supplied reference_README.md)
---------------------------------------------------------------------
Each sample bank uses its own np.random.default_rng(seed); M = path count.
  1. A (M starting prices): v = rng.random(M), THEN u = rng.random(M);
     A = K exp(log(0.001)(1-u)) if v < 0.5, else K (0.2 + u).
  2. Regression paths (seed 1000+c): A, then rng.standard_normal((M, N)).
  3. Random-start NN bank: J = rng.integers(0, N, size=M, dtype=int64),
     then A, then the full (M, N) normal array.  Column j drives the
     increment whose target date is j+1; its log increment is set to zero
     when j+1 <= J, so S = A in every slot through J.
  4. Log increments = drift + vol * Z, plus log1p(-delta) in the columns
     immediately preceding dividend indices; np.cumsum across columns,
     exponentiate, multiply by the starting price.
  5. Evaluation (seed 4000+10c+a): ten consecutive (5000, N) normal arrays
     from one advancing generator, reused for every policy at that spot.
"""

import numpy as np

import config as cfg

LOG_A_LO = np.log(0.001)


# ---------------------------------------------------------------------------
# Training distribution A
# ---------------------------------------------------------------------------
def sample_A(rng: np.random.Generator, n: int) -> np.ndarray:
    """Mixture A (README rule 1): two uniforms per path, v then u.

    v < 1/2 -> log(A/K) = log(0.001)(1-u), uniform on [log 0.001, 0];
    else    -> A/K = 0.2 + u, uniform on [0.2, 1.2].
    """
    v = rng.random(n)
    u = rng.random(n)
    return np.where(v < 0.5, cfg.K * np.exp(LOG_A_LO * (1.0 - u)), cfg.K * (0.2 + u))


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def log_increments(tg: cfg.TimeGrid, delta: float, Z: np.ndarray) -> np.ndarray:
    """README rule 4: column j (target date j+1) gets drift + vol*Z_j, plus
    log1p(-delta) if j+1 is a dividend index.  Z has shape (n, N)."""
    drift = (cfg.R - 0.5 * cfg.SIGMA ** 2) * tg.h
    vol = cfg.SIGMA * np.sqrt(tg.h)
    div_col = tg.is_div[1:tg.N + 1]                       # target date j+1 is a dividend
    return drift + vol * Z + np.where(div_col, np.log1p(-delta), 0.0)[None, :]


def paths_from_t0(S0: np.ndarray, Z: np.ndarray, tg: cfg.TimeGrid, delta: float) -> np.ndarray:
    """Full paths S_0..S_N (shape (n, N+1)) from t_0, float64:
    S_j = S_0 * exp(cumsum of log increments up to column j-1)."""
    inc = log_increments(tg, delta, Z)
    S = np.empty((len(S0), tg.N + 1))
    S[:, 0] = S0
    S[:, 1:] = S0[:, None] * np.exp(np.cumsum(inc, axis=1))
    return S


def paths_from_J(J: np.ndarray, SJ: np.ndarray, Z: np.ndarray, tg: cfg.TimeGrid,
                 delta: float) -> np.ndarray:
    """Random-start paths (README rule 3).  The mask is applied BEFORE the
    cumulative sum: log increments with target date j+1 <= J are zero, so
    S = S_J = A in every slot through J (post-jump if J is a dividend
    index).  Exercise before J is excluded by the callers (j_start)."""
    inc = log_increments(tg, delta, Z)
    target = np.arange(1, tg.N + 1)[None, :]
    inc = np.where(target <= J[:, None], 0.0, inc)
    S = np.empty((len(J), tg.N + 1))
    S[:, 0] = SJ
    S[:, 1:] = SJ[:, None] * np.exp(np.cumsum(inc, axis=1))
    return S


# ---------------------------------------------------------------------------
# Seeded path sets (README conventions above)
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
