"""
part2_supplied_verify.py -- Part 2 "Numerical reference".

1. Runs the supplied `reference_solver.py --verify` (unchanged instructor
   code): it checks the saved arrays and repeats the spatial (dS 0.10 -> 0.05)
   and time-integration (16 -> 32 substeps) refinements for all four cases.
   We tabulate the largest price change at S0 = 60, 80, 100 and the largest
   boundary change across exercise dates, plus the saved-array differences.
2. Cross-checks the supplied arrays against OUR independent solver
   (grid_solver.py, exact Gaussian step on a log grid): an agreement check
   between two different numerical methods.
"""
import contextlib
import io

import numpy as np
import pandas as pd

import config as cfg
import reference_solver as RS
from reference import load_reference

KEYS = {"N180_d0": (180, 0.0), "N180_d0125": (180, 0.0125),
        "N360_d0": (360, 0.0), "N360_d0125": (360, 0.0125)}


def supplied_verify():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):          # keep the JSON log, print a table instead
        reports = RS.verify_reference()
    rows = []
    for key, rep in reports.items():
        N, d = KEYS[key]
        rows.append(dict(
            case_key=key, N=N, delta=d,
            spatial_dV_max=rep["spatial_010_to_005"]["maximum_price_difference"],
            spatial_db_max=rep["spatial_010_to_005"]["maximum_boundary_difference"],
            spatial_db_median=rep["spatial_010_to_005"]["median_boundary_difference"],
            temporal_dV_max=rep["temporal_16_to_32"]["maximum_price_difference"],
            temporal_db_max=rep["temporal_16_to_32"]["maximum_boundary_difference"],
            temporal_db_median=rep["temporal_16_to_32"]["median_boundary_difference"],
            db_max_time=rep["temporal_16_to_32"]["maximum_boundary_difference_time"],
            saved_price_max_diff=rep["saved_price_max_difference"],
            saved_boundary_max_diff=rep["saved_boundary_max_difference"]))
    return pd.DataFrame(rows), buf.getvalue()


def own_vs_supplied():
    rows = []
    for key, (N, d) in KEYS.items():
        s, o = load_reference(N, d), load_reference(N, d, "own")
        db = np.abs(s.boundary - o.boundary)
        rows.append(dict(case_key=key, N=N, delta=d,
                         **{f"V_supplied({x})": s.value_at(x) for x in (60, 80, 100)},
                         dV_max=max(abs(s.value_at(x) - o.value_at(x)) for x in (60.0, 80.0, 100.0)),
                         db_max=db.max(), db_median=float(np.median(db)),
                         db_max_j=int(db.argmax())))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    v, log = supplied_verify()
    print(v.to_string(index=False)); print(own_vs_supplied().to_string(index=False))
