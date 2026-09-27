"""
reference.py -- ONE entry point for "the numerical reference" used by
Parts 2-5, so the supplied files can replace our solver without touching
any other module.

    ref = load_reference(N, delta)
    ref.S          stock grid (dollars)
    ref.V0         time-zero prices on that grid, V_{delta,N}(0, s)
    ref.boundary   b^ref_{delta,N}(t_j), j = 0..N   (b_N = K)
    ref.source     'supplied' or 'own-solver'
    ref.value_at(s0)

PLACEHOLDER STATUS (read this)
------------------------------
The supplied reference_solver.py / reference_results.npz / README.md were
not available when this was written.  Until they are:
  * source = 'own-solver' : our grid solver (grid_solver.py) at the FINE
    spatial setting m_per_div = 20 (dx ~ 6.3e-4), which our Part 2
    verification shows changes values by ~1e-5 $ vs m = 10.
When reference_results.npz is copied next to this file, fill SUPPLIED_KEYS
with the array names from README.md; everything downstream switches
automatically.  Nothing below guesses those names.
"""

import os
from dataclasses import dataclass

import numpy as np

import config as cfg
from grid_solver import solve, LogGrid

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPLIED_NPZ = os.path.join(HERE, "reference_results.npz")

# TODO(after reading README.md): map each (N, delta) to the npz array names.
# Example shape of the entry (names below are NOT the real ones):
#   (180, 0.0): dict(S="...", V0="...", boundary="..."),
SUPPLIED_KEYS: dict = {}

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
        """Linear interpolation in log S of the time-zero price."""
        m = self.S > 0
        return float(np.interp(np.log(s0), np.log(self.S[m]), self.V0[m]))


_CACHE = {}


def load_reference(N: int, delta: float) -> Reference:
    key = (N, delta)
    if key in _CACHE:
        return _CACHE[key]
    if os.path.exists(SUPPLIED_NPZ) and key in SUPPLIED_KEYS:
        z = np.load(SUPPLIED_NPZ)
        names = SUPPLIED_KEYS[key]
        ref = Reference(N, delta, z[names["S"]], z[names["V0"]],
                        z[names["boundary"]], "supplied")
    else:
        r = solve(N, delta, grid=LogGrid(**FINE_GRID))
        ref = Reference(N, delta, r.S, r.V_plus[0], r.boundary, "own-solver")
    _CACHE[key] = ref
    return ref
