"""
run_parts23.py -- Reproduces all Part 2 and Part 3 results (and a preview
of the Part 5 evaluation for LS).  One command:

    python run_parts23.py

Writes
  results.csv                 long format: section, case, N, delta, method, S0, metric, value
  tables/p2_*.csv, tables/p3_*.csv
  fitted/ls_boundaries.npz    frozen LS thresholds for every case
  fitted/run_config.json      seeds, sizes, assumptions, versions, timings
  figures/p23_*.png
"""

import json
import os
import platform
import time

import numpy as np
import pandas as pd
import scipy

import config as cfg
import simulation as sim
import lsm
import evaluate as ev
import part2_reference_check as p2
from reference import load_reference
import plotting_p23 as PP

os.makedirs("tables", exist_ok=True)
os.makedirs("fitted", exist_ok=True)
os.makedirs("figures", exist_ok=True)

RESULTS = []          # long-format rows for results.csv


def put(section, metric, value, case=None, method=None, S0=None):
    N, d = sim.CASES[case] if case is not None else (None, None)
    RESULTS.append(dict(section=section, case=case, N=N, delta=d, method=method,
                        S0=S0, metric=metric, value=value))


timings = {}

# ---------------------------------------------------------------- Part 2
t0 = time.perf_counter()
ref_tab = p2.refinement_table()
ref_tab.to_csv("tables/p2_reference_refinement.csv", index=False)
nch = p2.n_change_table()
nch.to_csv("tables/p2_N_change.csv", index=False)
for r in ref_tab.itertuples():
    c = [k for k, v in sim.CASES.items() if v == (r.N, r.delta)][0]
    put("p2_refinement", f"dV_spots[{r.refinement}]", r.dV_spots, c, "ref")
    put("p2_refinement", f"db[{r.refinement}]", r.db, c, "ref")
timings["part2_reference_check_s"] = time.perf_counter() - t0

mart = pd.DataFrame([sim.martingale_check(c) for c in range(4)])
mart.to_csv("tables/p2_martingale.csv", index=False)
for r in mart.itertuples():
    put("p2_martingale", "z_(mean-theory)/se", r.z, r.case)
    put("p2_martingale", "diff_dollars", r.diff, r.case)

# ---------------------------------------------------------------- Part 3
ls, diag_rows, fb_rows = {}, [], []
t0 = time.perf_counter()
for c in range(4):
    N, d = sim.CASES[c]
    tg, S = sim.training_paths_LS(c)
    t1 = time.perf_counter()
    r = lsm.fit_ls(S, tg, d)
    ls[c] = r
    timings[f"ls_fit_case{c}_s"] = time.perf_counter() - t1
    diag = dict(case=c, N=N, delta=d,
                fallback_count=len(r.fallback),
                multi_crossing_count=len(r.multi_cross_dates),
                capped_count=len(r.capped_dates),
                max_crossings=int(r.n_cross.max()),
                replay_max_abs_diff=r.replay_max_abs_diff,
                train_mean_Y_insample=r.train_mean_Y)
    diag_rows.append(diag)
    for k in ("fallback_count", "multi_crossing_count", "capped_count", "replay_max_abs_diff"):
        put("p3_ls_diagnostics", k, diag[k], c, "LS")
    for j, why in sorted(r.fallback.items()):
        fb_rows.append(dict(case=c, j=j, fallback=why))
timings["ls_total_s"] = time.perf_counter() - t0
pd.DataFrame(diag_rows).to_csv("tables/p3_ls_diagnostics.csv", index=False)
pd.DataFrame(fb_rows, columns=["case", "j", "fallback"]).to_csv("tables/p3_ls_fallbacks.csv", index=False)
np.savez("fitted/ls_boundaries.npz",
         **{f"case{c}_boundary": ls[c].boundary for c in ls},
         **{f"case{c}_candidate": ls[c].candidate for c in ls},
         **{f"case{c}_coef": ls[c].coef for c in ls})

# ------------------------------------------- Preview of Part 5 for LS
t0 = time.perf_counter()
price_rows, err_rows, pair_rows = [], [], []
for c in range(4):
    N, d = sim.CASES[c]
    ref = load_reference(N, d)
    rows, paired = ev.price_policies(c, {"LS": ls[c].boundary,
                                         "ref-boundary policy": ref.boundary})
    for row in rows:
        row["ref_value"] = ref.value_at(row["S0"])
        price_rows.append(row)
        put("p5_prices_preview", "mean", row["mean"], c, row["method"], row["S0"])
        put("p5_prices_preview", "ci_lo", row["lo"], c, row["method"], row["S0"])
        put("p5_prices_preview", "ci_hi", row["hi"], c, row["method"], row["S0"])
    for (m1, m2, s0), (md, se) in paired.items():
        pair_rows.append(dict(case=c, pair=f"{m1} - {m2}", S0=s0, mean_diff=md, se=se))
    e = ev.boundary_errors(ls[c].boundary, ref.boundary, N)
    err_rows.append(dict(case=c, N=N, delta=d, method="LS", **e))
    put("p5_boundary_error_preview", "E_mean", e["E_mean"], c, "LS")
    put("p5_boundary_error_preview", "E_max", e["E_max"], c, "LS")
    put("reference", "source", ref.source, c, "ref")
timings["evaluation_preview_s"] = time.perf_counter() - t0
pd.DataFrame(price_rows).to_csv("tables/p5_prices_preview.csv", index=False)
pd.DataFrame(pair_rows).to_csv("tables/p5_paired_preview.csv", index=False)
pd.DataFrame(err_rows).to_csv("tables/p5_boundary_errors_preview.csv", index=False)

# ------------------------------------- Part 1 checks with fitted LS
ord_rows = []
for N, (cn, cd) in ((180, (0, 1)), (360, (2, 3))):
    for m, (bd, b0) in {
        "ref": (load_reference(N, 0.0125).boundary, load_reference(N, 0.0).boundary),
        "LS": (ls[cd].boundary, ls[cn].boundary)}.items():
        o = ev.ordering_diagnostics(bd, b0, N)
        ord_rows.append(dict(N=N, method=m, **o))
        for k, v in o.items():
            put("p1_ordering_checks", k, v, cd, m)
    r0, rd = load_reference(N, 0.0), load_reference(N, 0.0125)
    mx = float(np.max(np.maximum(r0.V0 - rd.V0, 0.0)))
    ord_rows.append(dict(N=N, method="ref: max (V0 - V0.0125)^+ $", A=np.nan, B=np.nan, F=mx))
pd.DataFrame(ord_rows).to_csv("tables/p1_ordering_checks.csv", index=False)

pd.DataFrame(RESULTS).to_csv("results.csv", index=False)

# ------------------------------------------------------------- figures
PP.fig_ls_vs_ref(ls, "figures/p23_boundaries_ls_ref.png")
PP.fig_final_dividend(ls, "figures/p23_final_dividend.png")
PP.fig_H_example(ls, "figures/p23_H_example.png")

# ------------------------------------------------------ run config
json.dump(dict(
    reference_source={c: load_reference(*sim.CASES[c]).source for c in range(4)},
    seeds=dict(ls_training="1000+c", evaluation="4000+10c+a"),
    sizes=dict(ls_training=sim.N_TRAIN_LS, eval_paths=sim.N_EVAL, eval_batch=sim.EVAL_BATCH),
    draw_order_ASSUMED="see simulation.py docstring; replace with README.md order",
    precision="float64 throughout",
    versions=dict(python=platform.python_version(), numpy=np.__version__,
                  scipy=scipy.__version__),
    hardware=dict(cpu_threads=os.cpu_count(), machine=platform.machine(),
                  processor=platform.processor() or "n/a"),
    timings_seconds=timings), open("fitted/run_config.json", "w"), indent=2)

pd.set_option("display.width", 200)
for f in ("p2_martingale", "p3_ls_diagnostics", "p5_prices_preview",
          "p5_paired_preview", "p5_boundary_errors_preview", "p1_ordering_checks"):
    print(f"\n== {f} ==\n", pd.read_csv(f"tables/{f}.csv").to_string(index=False))
print("\ntimings", json.dumps(timings, indent=1))
