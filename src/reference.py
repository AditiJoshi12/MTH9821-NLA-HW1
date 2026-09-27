"""
reference.py -- ONE entry point for "the numerical reference" used by
Parts 2-5.

    ref = load_reference(N, delta)            # supplied reference (default)
    own = load_reference(N, delta, "own")     # our grid solver (cross-check)
    ref.S          stock grid (dollars)
    ref.V0         time-zero prices on that grid, V_{delta,N}(0, s)
    ref.boundary   b^ref_{delta,N}(t_j), j = 0..N   (b_N = K; post-dividend
                   at dividend indices)
    ref.source     'supplied' or 'own-solver'
    ref.value_at(s0)

Supplied reference (instructor files, preserved unchanged in this folder)
------------------------------------------------------------------------
reference_results.npz, produced by reference_solver.py: finite differences
in S on [0, 400] with dS = 0.05 and 32 pricing substeps per exercise
interval (Rannacher start, then Crank-Nicolson), exercise only at grid dates.
Array names (reference_README.md):
    spots, <key>_value0, <key>_boundary, <key>_times, <key>_dividend_indices
with key in N180_d0, N180_d0125, N360_d0, N360_d0125.
Prices are read with np.interp(S0, spots, value0), as the README prescribes.

Own solver
----------
grid_solver.py at the fine spatial setting m_per_div = 20: an independent
method (exact Gaussian step on a log grid) used as a cross-check.
"""

import os
from dataclasses import dataclass

import numpy as np

import config as cfg
from grid_solver import solve, LogGrid

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPLIED_NPZ = os.path.join(HERE, "reference_results.npz")

SUPPLIED_KEYS = {(180, 0.0): "N180_d0", (180, 0.0125): "N180_d0125",
                 (360, 0.0): "N360_d0", (360, 0.0125): "N360_d0125"}

FINE_GRID = dict(m_per_div=20)


@dataclass
class Reference:
    N: int
    delta: float
    S: np.ndarray
    V0: np.ndarray
    boundary: np.ndarray
    source: str

    def value_at(self, s0: float) -> float:
        """Time-zero price at s0: linear interpolation in S for the supplied
        grid (README convention), in log S for our log-spaced grid."""
        if self.source == "supplied":
            return float(np.interp(s0, self.S, self.V0))
        m = self.S > 0
        return float(np.interp(np.log(s0), np.log(self.S[m]), self.V0[m]))


_CACHE = {}


def _load_supplied(N, delta):
    key = SUPPLIED_KEYS[(N, delta)]
    with np.load(SUPPLIED_NPZ, allow_pickle=False) as z:
        S, V0, b = z["spots"], z[key + "_value0"], z[key + "_boundary"]
        times, idx = z[key + "_times"], z[key + "_dividend_indices"]
    # consistency with our conventions (fail loudly rather than mis-align)
    tg = cfg.TimeGrid(N)
    assert b.shape == (N + 1,) and b[-1] == cfg.K
    assert np.allclose(times, tg.t, atol=1e-14, rtol=0)
    assert tuple(int(i) for i in idx) == tg.div_idx
    return Reference(N, delta, S, V0, b, "supplied")


def load_reference(N: int, delta: float, source: str = "supplied") -> Reference:
    """source='supplied' (default; falls back to our solver only if the npz
    is missing) or 'own' (our solver, for the cross-check)."""
    use_supplied = source == "supplied" and os.path.exists(SUPPLIED_NPZ)
    key = (N, delta, "supplied" if use_supplied else "own")
    if key not in _CACHE:
        if use_supplied:
            _CACHE[key] = _load_supplied(N, delta)
        else:
            r = solve(N, delta, grid=LogGrid(**FINE_GRID))
            _CACHE[key] = Reference(N, delta, r.S, r.V_plus[0], r.boundary, "own-solver")
    return _CACHE[key]
