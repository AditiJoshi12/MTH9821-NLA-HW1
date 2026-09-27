"""
config.py -- Model, contract and time-grid conventions for Assignment 1.

Everything in this module is taken directly from the assignment statement
("Model, contract, and time conventions"). Nothing here is a modelling
choice of ours, EXCEPT the helper functions' interfaces.

Conventions
-----------
* Calendar time t runs from 0 to T.  Grid dates t_j = j*T/N, j = 0..N.
* "Time remaining" u = T - t is used ONLY for plotting (assignment's
  plotting convention). Calendar time advances as u DECREASES.
* Dividend dates are stored as INTEGER grid indices (assignment: "Use
  integer dividend indices in code") to avoid floating-point comparisons
  such as t_j == 5/24.
* At a dividend date the stored value / boundary refers to the state
  IMMEDIATELY AFTER the jump (post-jump), per the assignment.
"""

from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

# ---------------------------------------------------------------------------
# Contract and market parameters (fixed by the assignment)
# ---------------------------------------------------------------------------
K = 100.0                     # strike
T = 0.75                      # maturity in years (3/4)
R = float(np.log(1.05))       # continuously compounded riskless rate
SIGMA = 0.30                  # annual volatility

# Dividend dates as exact fractions of a year -> exact integer indices later
DIV_DATES_FRAC = (Fraction(5, 24), Fraction(11, 24), Fraction(17, 24))
DIV_DATES = tuple(float(d) for d in DIV_DATES_FRAC)

# The only two dividend fractions studied
DELTAS = (0.0, 0.0125)

# Exercise counts studied
NS = (180, 360)

# Dividend markers in time-remaining coordinates u = T - d_k
# (13/24, 7/24, 1/24) -- used for plots.
DIV_MARKERS_U = tuple(float(Fraction(3, 4) - d) for d in DIV_DATES_FRAC)


# ---------------------------------------------------------------------------
# Time grid
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TimeGrid:
    """Exercise grid t_j = j*T/N with integer dividend indices.

    Attributes
    ----------
    N        : number of intervals (exercise dates are j = 0..N)
    h        : step T/N
    t        : array of calendar dates, shape (N+1,)
    div_idx  : tuple of integer indices j with t_j = d_k (sorted)
    is_div   : boolean mask, shape (N+1,), True at dividend indices
    """
    N: int
    h: float = field(init=False)
    t: np.ndarray = field(init=False, repr=False)
    div_idx: tuple = field(init=False)
    is_div: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        # frozen dataclass -> use object.__setattr__ inside __post_init__
        object.__setattr__(self, "h", T / self.N)
        object.__setattr__(self, "t", np.arange(self.N + 1) * (T / self.N))

        # Exact integer index: d_k / T * N must be an integer
        # (assignment: "Every dividend date belongs to both grids").
        idx = []
        for d in DIV_DATES_FRAC:
            j = d / Fraction(3, 4) * self.N
            if j.denominator != 1:
                raise ValueError(f"Dividend date {d} is not on the N={self.N} grid")
            idx.append(int(j))
        object.__setattr__(self, "div_idx", tuple(idx))

        mask = np.zeros(self.N + 1, dtype=bool)
        mask[list(idx)] = True
        object.__setattr__(self, "is_div", mask)

    @property
    def j_star(self) -> int:
        """Index of the LAST dividend d_3 (assignment: j* = 17N/18)."""
        return self.div_idx[-1]

    def u(self) -> np.ndarray:
        """Time remaining u_j = T - t_j (plotting coordinate)."""
        return T - self.t


# ---------------------------------------------------------------------------
# The dividend cap U_j from Part 1 / Part 2
# ---------------------------------------------------------------------------
def dividend_cap(grid: TimeGrid, delta: float) -> np.ndarray:
    """Return U_j for j = 0..N-1 (length N).

    U_j = min{K, K(1 - exp(-r (d(j) - t_j))) / delta}   if delta > 0 and a
          dividend occurs STRICTLY after t_j (d(j) = earliest such date)
        = K                                             otherwise.

    Note: at a dividend date t_j = d_k the state is post-jump, so d(j) is
    the FOLLOWING dividend d_{k+1} (strictly after), exactly as in the
    assignment.  After the last dividend U_j = K.
    """
    U = np.full(grid.N, K)
    if delta <= 0.0:
        return U
    for j in range(grid.N):
        later = [jd for jd in grid.div_idx if jd > j]   # strictly after t_j
        if later:
            eps = grid.t[later[0]] - grid.t[j]           # d(j) - t_j  (> 0)
            U[j] = min(K, K * (1.0 - np.exp(-R * eps)) / delta)
    return U
