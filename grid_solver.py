"""
grid_solver.py -- Our OWN independent grid-exercise (Bermudan) solver.

Purpose: a numerical reference for the Part 1 experiments while the
supplied reference_solver.py is not available.  It is NOT a replacement
for the supplied solver in Parts 2-5.

Problem solved
--------------
Exercise is allowed only at t_j = jT/N (j = 0..N, including t_0 = 0).
Between dates the stock is GBM under Q; at a dividend index the price
jumps S -> (1 - delta) S.  Backward induction:

    C_j(s)   = e^{-rh} E[ W_{j+1}(S_{j+1}^-) | S_j = s ]    (continuation)
    V_j^+(s) = max( payoff(s), C_j(s) )                   (post-jump value)
    W_j(s)   = value as a function of the PRE-jump price at t_j

and W_j = V_j^+ on non-dividend dates.  On a dividend date the ORDERING
RULE decides W_j (this is exactly what items 1 and 4 are about):

    'after'  : W_j(s) = V_j^+((1-delta) s)
               -> jump first, then exercise decision (assignment's rule
                  for the put: "Apply the dividend jump before the
                  exercise decision at that date").
    'both'   : W_j(s) = max( payoff(s), V_j^+((1-delta) s) )
               -> the holder may exercise just before OR just after the
                  jump (the correct American rule; item 4 identity).
    'before' : W_j(s) = max( payoff(s), C_j((1-delta) s) )
               -> exercise ONLY before the jump (deliberately wrong
                  ordering, used as a contrast).

Space discretisation (modelling choices)
----------------------------------------
* Uniform grid in X = log S centred so that S = K is a node (payoff kink
  on a node -> the piecewise-linear representation of the payoff is exact).
* dx = |log(1 - delta_ref)| / m with delta_ref = 0.0125, m integer.  Then
  the dividend jump is an EXACT shift of m grid nodes: no interpolation
  error at the dividend.  The same dx is used for delta = 0 so that the
  two models share one grid (important for the ordering comparison in
  item 3: any difference comes from the model, not from the grid).
* Truncated domain [K e^{-x_lo}, K e^{x_hi}] with edge-value extension
  (see lognormal_kernel.expect_one_step).
"""

from dataclasses import dataclass

import numpy as np

import config as cfg
from lognormal_kernel import transition_weights, expect_one_step


# ---------------------------------------------------------------------------
# Spatial grid
# ---------------------------------------------------------------------------
@dataclass
class LogGrid:
    """Uniform log-price grid with dividend jump = exact integer shift."""
    m_per_div: int = 10          # grid nodes per dividend jump
    x_lo: float = 7.0            # domain extends to K*exp(-x_lo) (~0.09)
    x_hi: float = 3.0            # ... and to K*exp(+x_hi) (~2009)
    delta_ref: float = 0.0125    # dividend fraction that fixes dx

    def __post_init__(self):
        self.dx = -np.log(1.0 - self.delta_ref) / self.m_per_div
        n_lo = int(np.ceil(self.x_lo / self.dx))
        n_hi = int(np.ceil(self.x_hi / self.dx))
        self.i_K = n_lo                                   # index of S = K
        self.x = np.log(cfg.K) + (np.arange(n_lo + n_hi + 1) - n_lo) * self.dx
        self.S = np.exp(self.x)

    def shift_for(self, delta: float) -> int:
        """Number of nodes the price moves down at a dividend of size delta.

        Only delta in {0, delta_ref} are exact; anything else is refused
        rather than silently interpolated.
        """
        if delta == 0.0:
            return 0
        k = -np.log(1.0 - delta) / self.dx
        if abs(k - round(k)) > 1e-9:
            raise ValueError("delta is not an exact multiple of the grid shift")
        return int(round(k))


def shift_down(V: np.ndarray, k: int) -> np.ndarray:
    """Return F with F_i = V_{i-k}, i.e. F(s) = V((1-delta) s) on the grid.

    Below the grid we use the edge value (same extrapolation as the kernel).
    """
    if k == 0:
        return V.copy()
    F = np.empty_like(V)
    F[k:] = V[:-k]
    F[:k] = V[0]
    return F


# ---------------------------------------------------------------------------
# Payoffs
# ---------------------------------------------------------------------------
def put_payoff(S):
    return np.maximum(cfg.K - S, 0.0)


def call_payoff(S):
    return np.maximum(S - cfg.K, 0.0)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class SolveResult:
    N: int
    delta: float
    kind: str                 # 'put' or 'call'
    ordering: str
    american: bool
    S: np.ndarray             # spatial grid
    V_plus: np.ndarray        # (N+1, nS): post-jump value V_j^+
    C: np.ndarray             # (N,   nS): continuation C_j (post-jump coords)
    W_div: dict               # {j: W_j} pre-jump value at dividend indices
    boundary: np.ndarray      # (N+1,) put exercise boundary b_j (b_N = K)
    n_cross: np.ndarray       # (N,) number of +/- sign changes (diagnostic)

    def value_at(self, s0: float, j: int = 0) -> float:
        """Linear interpolation in log S of the date-j value.

        j = 0 is not a dividend date, so V_0^+ = W_0.
        """
        return float(np.interp(np.log(s0), np.log(self.S), self.V_plus[j]))


# ---------------------------------------------------------------------------
# Boundary extraction
# ---------------------------------------------------------------------------
def put_boundary_from(S, cont, tol=0.0):
    """b = sup({0} U {s < K : V(s) = K - s}) from a continuation curve.

    g(s) = C(s) - (K - s).  Exercise where g <= tol.  We take the LARGEST
    exercise node below K and locate the zero of g by linear interpolation
    towards the next (continuation) node.  If there is no exercise node,
    b = 0.  We also count sign changes of the exercise indicator below K:
    a connected exercise interval (0, b] gives at most 1 change.
    """
    below = S < cfg.K
    g = cont[below] - (cfg.K - S[below])
    ex = g <= tol
    n_changes = int(np.count_nonzero(ex[1:] != ex[:-1]))
    if not ex.any():
        return 0.0, n_changes
    i = np.flatnonzero(ex)[-1]
    Sb = S[below]
    if i + 1 < len(Sb) and g[i + 1] > 0:
        # linear interpolation of the zero of g between nodes i and i+1
        lam = -g[i] / (g[i + 1] - g[i])
        return float(Sb[i] + lam * (Sb[i + 1] - Sb[i])), n_changes
    return float(Sb[i]), n_changes


# ---------------------------------------------------------------------------
# The solver
# ---------------------------------------------------------------------------
def solve(N: int, delta: float, kind: str = "put", ordering: str = "after",
          american: bool = True, grid: LogGrid | None = None,
          substeps: int = 1, n_sd: float = 10.0) -> SolveResult:
    """Backward induction for a grid-exercise put or call.

    Parameters
    ----------
    N        : number of time intervals
    delta    : dividend fraction (0 or 0.0125)
    kind     : 'put' or 'call'
    ordering : 'after' | 'both' | 'before'  (see module docstring)
    american : False -> European (no early exercise, used for validation)
    substeps : split each [t_j, t_{j+1}] into this many kernel applications
               WITHOUT extra exercise dates.  Our kernel is exact in time,
               so this is the "time-integration refinement" of Part 2: any
               change it causes is interpolation error, not time error.
    n_sd     : kernel truncation in standard deviations (domain refinement)
    """
    grid = grid or LogGrid()
    tg = cfg.TimeGrid(N)
    S = grid.S
    k = grid.shift_for(delta)
    payoff = put_payoff if kind == "put" else call_payoff
    pay = payoff(S)

    w, L = transition_weights(grid.dx, tg.h / substeps, cfg.R, cfg.SIGMA, n_sd=n_sd)
    disc = np.exp(-cfg.R * tg.h)

    nS = S.size
    V_plus = np.empty((N + 1, nS))
    C = np.empty((N, nS))
    W_div = {}
    boundary = np.empty(N + 1)
    n_cross = np.zeros(N, dtype=int)

    # Terminal date: settle every surviving option (no dividend at T).
    V_plus[N] = pay
    W_next = pay.copy()
    boundary[N] = cfg.K

    for j in range(N - 1, -1, -1):
        # 1) continuation in post-jump coordinates at t_j
        E_next = W_next
        for _ in range(substeps):                # no exercise inside a step
            E_next = expect_one_step(E_next, w, L)
        C[j] = disc * E_next

        # 2) exercise decision (post-jump)
        V_plus[j] = np.maximum(pay, C[j]) if american else C[j]

        # 3) boundary for the put (from post-jump continuation vs payoff)
        if kind == "put" and american:
            boundary[j], n_cross[j] = put_boundary_from(S, C[j])
        else:
            boundary[j] = np.nan

        # 4) pre-jump value W_j depending on the ordering rule
        if tg.is_div[j] and k > 0:
            if ordering == "after" or not american:
                W = shift_down(V_plus[j], k)
            elif ordering == "both":
                W = np.maximum(pay, shift_down(V_plus[j], k))
            elif ordering == "before":
                W = np.maximum(pay, shift_down(C[j], k))
            else:
                raise ValueError(ordering)
            W_div[j] = W
        else:
            W = V_plus[j]
        W_next = W

    return SolveResult(N, delta, kind, ordering, american, S, V_plus, C,
                       W_div, boundary, n_cross)
