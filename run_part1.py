"""
run_part1.py -- One command that reproduces every Part 1 table and figure.

    python run_part1.py

Outputs: tables/*.csv and figures/*.png, plus environment info.
"""
import os, platform, time
import numpy as np, pandas as pd, scipy, matplotlib

import experiments_part1 as E
import plotting as P

os.makedirs("tables", exist_ok=True)
os.makedirs("figures", exist_ok=True)

def save(df, name):
    df.to_csv(f"tables/{name}.csv", index=False)
    print(f"\n== {name} ==\n{df.to_string(index=False)}")

t0 = time.perf_counter()
save(E.e1_dividend_identity(), "e1_dividend_identity")
save(E.e1_put_orderings(), "e1_put_orderings")
save(pd.concat([E.e2_cap_table(N).assign(N=N) for N in (180, 360)]), "e2_cap_table")
save(pd.concat([E.e2_cap_tightness(N).assign(N=N) for N in (180, 360)]), "e2_cap_tightness")
save(pd.DataFrame([dict(N=N, worst_slack=E.e2_lower_bound_check(N)) for N in (180, 360)]),
     "e2_lower_bound_check")
save(E.e2_proximity(), "e2_proximity")
save(E.e2_one_step_cap(), "e2_one_step_cap")
save(E.e2_maturity_limit(), "e2_maturity_limit")
save(E.e3_ordering_diagnostics(), "e3_ordering_diagnostics_ref")
save(E.e3_coupled_mc(), "e3_coupled_mc")
save(E.e4_call_orderings(), "e4_call_orderings")
thr, other = E.e4_call_pre_div_threshold()
save(thr.assign(other_early_exercise_nodes=other), "e4_call_thresholds")

P.fig_boundaries("figures/p1_boundaries.png")
P.fig_cap_zoom("figures/p1_cap_zoom.png")
P.fig_proximity("figures/p1_proximity.png")
P.fig_pre_jump("figures/p1_pre_jump.png")

print(f"\nTotal time {time.perf_counter()-t0:.1f}s | Python {platform.python_version()} "
      f"| NumPy {np.__version__} | SciPy {scipy.__version__} | matplotlib {matplotlib.__version__} "
      f"| CPU threads {os.cpu_count()} | float64 throughout")
