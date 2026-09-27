"""
lognormal_kernel.py -- One-step risk-neutral expectation on a uniform
log-price grid, computed EXACTLY for a piecewise-linear value function.

Modelling choice (ours, not the assignment's)
---------------------------------------------
Between exercise dates the stock is GBM, so over one step of length h

    X_{j+1} = X_j + Y,   Y ~ Normal(m, s^2),   m = (r - sigma^2/2) h,
                                               s = sigma sqrt(h),

with X = log S.  The transition is TRANSLATION-INVARIANT in X, so on a
uniform X-grid the conditional expectation is a discrete correlation
with a fixed weight vector w:

    E[ V(X_i + Y) ]  =  sum_n  w_n V_{i+n}.

We choose the weights so that the formula is EXACT when V is the
piecewise-linear interpolant of its grid values (a "tent"/hat basis):

    w_n = E[ Lambda((Y - n dx)/dx) ],   Lambda(u) = max(0, 1 - |u|).

Using  dx * Lambda((y - c)/dx) = (y-c+dx)^+ - 2 (y-c)^+ + (y-c-dx)^+,
each w_n is a second difference of the "call-type" function

    f(a) = E[(Y - a)^+] = (m - a) Phi((m-a)/s) + s phi((m-a)/s).

Why this choice
---------------
* No time-stepping error: the Gaussian step is integrated exactly, so the
  only discretisation error is the linear interpolation in X (O(dx^2) in
  smooth regions; the payoff kink is handled exactly because the kink at
  S=K sits on a grid node).
* Very cheap: a correlation of length ~2L+1 per date.
* Weights sum to ~1 (probability mass); we check this in the tests.
"""

import numpy as np
from scipy.stats import norm


def _call_fn(a: np.ndarray, m: float, s: float) -> np.ndarray:
    """f(a) = E[(Y - a)^+] for Y ~ N(m, s^2)  (Bachelier call formula)."""
    z = (m - a) / s
    return (m - a) * norm.cdf(z) + s * norm.pdf(z)


def transition_weights(dx: float, h: float, r: float, sigma: float,
                       n_sd: float = 10.0, variance_correction: bool = True):
    """Return (w, L): weights w_n for n = -L..L (array length 2L+1).

    n_sd controls truncation: we keep offsets up to |m| + n_sd * s.
    With n_sd = 10 the neglected Gaussian mass is ~1e-23 -- negligible.

    variance_correction (modelling choice, found necessary in validation)
    -------------------------------------------------------------------
    Integrating the hat basis exactly is equivalent to convolving the
    Gaussian step with a triangular density of variance dx^2/6.  Applied
    at every one of N steps this adds a spurious variance N*dx^2/6, i.e. a
    small upward bias that GROWS with N (seen in the European check:
    errors ~2.5e-3 at N=180 and ~5e-3 at N=360 without the correction).
    Using s_eff^2 = s^2 - dx^2/6 removes that bias to leading order, so the
    total variance per step is exactly sigma^2 h.
    """
    m = (r - 0.5 * sigma ** 2) * h
    s2 = sigma ** 2 * h - (dx ** 2 / 6.0 if variance_correction else 0.0)
    if s2 <= 0:
        raise ValueError("dx too coarse for this time step")
    s = np.sqrt(s2)
    L = int(np.ceil((abs(m) + n_sd * s) / dx)) + 1
    c = np.arange(-L, L + 1) * dx                      # hat centres n*dx
    w = (_call_fn(c - dx, m, s) - 2.0 * _call_fn(c, m, s)
         + _call_fn(c + dx, m, s)) / dx
    return w, L


def expect_one_step(V: np.ndarray, w: np.ndarray, L: int) -> np.ndarray:
    """E[V(X + Y)] at every grid node (NOT discounted).

    Boundary treatment (modelling assumption): outside the truncated grid
    V is extended by its EDGE VALUE (constant extrapolation).  The grid is
    chosen wide enough (see grid_solver.LogGrid) that this affects only
    prices far from anything we report; the European checks quantify it.
    """
    P = np.pad(V, (L, L), mode="edge")
    # np.correlate(P, w, 'valid')[i] = sum_k P[i+k] w[k] = sum_n V_{i+n} w_n
    return np.correlate(P, w, mode="valid")
