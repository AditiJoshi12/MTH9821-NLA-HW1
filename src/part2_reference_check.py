"""
part2_reference_check.py -- Part 2, SUPPLEMENTARY cross-check: the same refinement
study applied to OUR independent solver (the required study is the supplied
`reference_solver.py --verify`, run by part2_supplied_verify.py).  The
N = 180 -> 360 comparison (n_change_table) uses the SUPPLIED arrays.

The assignment asks us to run `python reference_solver.py -verify` and
report the largest price and boundary changes under SPATIAL and
TIME-INTEGRATION refinement.  Until the supplied solver is available we
run the SAME STUDY on our own solver.  Once the supplied solver exists,
run its -verify and put its numbers in the report instead; this script
still serves as an independent cross-check.

Design
------
Baseline B = (m_per_div=10, substeps=1, domain [K e^-7, K e^3], n_sd=10).
Each refinement changes ONE setting:
  spatial      : m_per_div 20, 40            (dx halved, quartered)
  time         : substeps 2, 4               (kernel applied in h/2, h/4)
  domain       : x_lo 9, x_hi 4              (wider truncated domain)
  kernel tails : n_sd 14                     (wider Gaussian truncation)
For each we record, per case (N, delta):
  dV_spots = max |V - V_B| over S0 in {60, 80, 100}          (dollars)
  dV_grid  = max |V - V_B| over s in [20, 200]                (dollars)
  db       = max_j |b_j - b_j^B|                              (dollars)
and the same quantities for the change N = 180 -> 360 (a different
PROBLEM, not a refinement), measured at the common dates t = t_j^{180}.
"""

import time

import numpy as np
import pandas as pd

import config as cfg
from grid_solver import solve, LogGrid

SPOTS = (60.0, 80.0, 100.0)
S_EVAL = np.exp(np.linspace(np.log(20), np.log(200), 400))

REFINEMENTS = [
    ("spatial dx/2", dict(grid=dict(m_per_div=20))),
    ("spatial dx/4", dict(grid=dict(m_per_div=40))),
    ("time h/2 (substeps=2)", dict(substeps=2)),
    ("time h/4 (substeps=4)", dict(substeps=4)),
    ("domain wider", dict(grid=dict(x_lo=9.0, x_hi=4.0))),
    ("kernel tails n_sd=14", dict(n_sd=14.0)),
]


def _run(N, delta, grid=None, **kw):
    t0 = time.perf_counter()
    r = solve(N, delta, grid=LogGrid(**(grid or {})), **kw)
    return r, time.perf_counter() - t0


def _V(r, s):
    return np.interp(np.log(s), np.log(r.S), r.V_plus[0])


def refinement_table():
    rows = []
    for N in cfg.NS:
        for d in cfg.DELTAS:
            base, tb = _run(N, d)
            for name, kw in REFINEMENTS:
                r, tr = _run(N, d, **kw)
                rows.append(dict(
                    N=N, delta=d, refinement=name,
                    dV_spots=np.max(np.abs(_V(r, np.array(SPOTS)) - _V(base, np.array(SPOTS)))),
                    dV_grid=np.max(np.abs(_V(r, S_EVAL) - _V(base, S_EVAL))),
                    db=np.nanmax(np.abs(r.boundary - base.boundary)),
                    seconds=tr, baseline_seconds=tb))
    return pd.DataFrame(rows)


def n_change_table():
    """V_{360} - V_{180} from the SUPPLIED fine reference arrays (assignment:
    "Use the supplied fine reference arrays in every comparison").
    More exercise rights -> the value can only rise."""
    from reference import load_reference
    rows = []
    for d in cfg.DELTAS:
        r1, r2 = load_reference(180, d), load_reference(360, d)
        dv = [r2.value_at(s) - r1.value_at(s) for s in SPOTS]
        grid = np.array([r2.value_at(s) - r1.value_at(s) for s in S_EVAL])
        # common dates: t_j^{180} = t_{2j}^{360}; skip j = N (both = K)
        db = r2.boundary[0:360:2] - r1.boundary[:180]
        rows.append(dict(delta=d, **{f"dV({int(s)})": v for s, v in zip(SPOTS, dv)},
                         min_dV_grid=grid.min(), max_db=np.max(np.abs(db)), mean_db=np.mean(db),
                         source=r1.source))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(refinement_table().to_string(index=False))
    print(n_change_table().to_string(index=False))
