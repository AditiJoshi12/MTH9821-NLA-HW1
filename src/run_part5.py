"""
run_part5.py -- Part 5: final independent evaluation of the frozen LS and
NN policies (plus the reference boundary used as a hard rule), boundary
accuracy, the perturbation study, and the final results.csv.

    python run_part5.py     (needs fitted/ls_boundaries.npz and fitted/nn_boundaries.npz)

All fits and checkpoint selections are complete BEFORE this script
generates any evaluation path (assignment requirement).
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
import evaluate as ev
import part5 as P
import plotting_p23 as PP
from reference import load_reference

os.makedirs("tables", exist_ok=True)


def main():
    lsz, nnz = np.load("fitted/ls_boundaries.npz"), np.load("fitted/nn_boundaries.npz")
    B = {c: {"LS": lsz[f"case{c}_boundary"], "NN": nnz[f"case{c}_selected"],
             "ref-boundary policy": load_reference(*sim.CASES[c]).boundary} for c in range(4)}

    # 1. prices ---------------------------------------------------------------
    prices, paired, t_eval = P.price_table(B)
    prices.to_csv("tables/p5_prices.csv", index=False)
    paired.to_csv("tables/p5_paired.csv", index=False)

    # 2. boundary accuracy ------------------------------------------------------
    errs = P.boundary_accuracy(B)
    errs.to_csv("tables/p5_boundary_errors.csv", index=False)
    neff = P.n_effect()
    neff.to_csv("tables/p5_N_effect.csv", index=False)

    # Part 1 ordering checks with the final policies
    ord_rows = []
    for N, (cn, cd) in ((180, (0, 1)), (360, (2, 3))):
        for m in ("LS", "NN"):
            ord_rows.append(dict(N=N, method=m, **ev.ordering_diagnostics(B[cd][m], B[cn][m], N)))
        ord_rows.append(dict(N=N, method="ref", **ev.ordering_diagnostics(
            load_reference(N, 0.0125).boundary, load_reference(N, 0.0).boundary, N)))
        r0, rd = load_reference(N, 0.0), load_reference(N, 0.0125)
        ord_rows.append(dict(N=N, method="ref: max (V0 - V0.0125)^+ $", A=np.nan, B=np.nan,
                             F=float(np.max(np.maximum(r0.V0 - rd.V0, 0.0)))))
    pd.DataFrame(ord_rows).to_csv("tables/p1_ordering_checks.csv", index=False)

    # 3. perturbation (case 3, S0 = 100, existing evaluation paths) --------------
    t0 = time.perf_counter()
    pert = P.perturbation(B[3]["NN"])
    sweep = P.perturbation_sweep(B[3]["NN"])
    t_pert = time.perf_counter() - t0
    pert.to_csv("tables/p5_perturbation.csv", index=False)
    sweep.to_csv("tables/p5_perturbation_sweep_supplementary.csv", index=False)
    gap = float(np.mean(B[3]["ref-boundary policy"][:360] - B[3]["NN"][:360]) / cfg.K)
    PP.fig_perturbation(sweep, pert, gap, "figures/p5_perturbation.png")

    # results.csv: replace every section this script owns ----------------------
    res = pd.read_csv("results.csv")
    owned = ["p5_prices", "p5_prices_preview", "p5_boundary_error", "p5_boundary_error_preview",
             "p1_ordering_checks", "p5_perturbation", "p5_N_effect", "environment", "timing_eval"]  # timing_ls is kept
    res = res[~res.section.isin(owned)]
    new = []

    def add(sec, met, val, c=None, m=None, s0=None):
        N, d = sim.CASES[c] if c is not None else (None, None)
        new.append(dict(section=sec, case=c, N=N, delta=d, method=m, S0=s0, metric=met, value=val))

    for r in prices.itertuples():
        for met, v in (("mean", r.mean), ("se", r.se), ("ci_lo", r.lo), ("ci_hi", r.hi),
                       ("ref_value", r.ref_value), ("z_vs_ref", r.z_vs_ref)):
            add("p5_prices", met, v, r.case, r.method, r.S0)
    for r in errs.itertuples():
        add("p5_boundary_error", "E_mean", r.E_mean, r.case, r.method)
        add("p5_boundary_error", "E_max", r.E_max, r.case, r.method)
    for r in neff.itertuples():
        add("p5_N_effect", f"E_mean_ref360_vs_ref180[delta={r.delta}]", r.E_mean_ref360_vs_ref180)
    for r in ord_rows:
        for k in ("A", "B", "F"):
            add("p1_ordering_checks", f"{k}[N={r['N']}]", r[k], None, r["method"])
    for r in pert.itertuples():
        add("p5_perturbation", f"mean_diff[a={r.a}]", r.mean_diff, 3, "NN", 100.0)
        add("p5_perturbation", f"se_diff[a={r.a}]", r.se_diff, 3, "NN", 100.0)
    for c, t in t_eval.items():
        add("timing_eval", "evaluation_3_policies_s", t, c)
    add("timing_eval", "perturbation_s", t_pert, 3)
    import torch
    for k, v in dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                     pandas=pd.__version__, torch=torch.__version__, cpu_threads=os.cpu_count(),
                     machine=platform.machine(), processor=platform.processor() or "n/a",
                     accelerator="none (CPU)", precision_sim_eval="float64",
                     precision_nn_training="float32",
                     reference_source=load_reference(360, 0.0125).source).items():
        add("environment", k, v)
    pd.concat([res, pd.DataFrame(new)]).to_csv("results.csv", index=False)

    json.dump(dict(eval_seconds=t_eval, perturbation_seconds=t_pert, cpu_threads=os.cpu_count()),
              open("fitted/run_config_part5.json", "w"), indent=2)

    pd.set_option("display.width", 220)
    for f in ("p5_prices", "p5_boundary_errors", "p5_N_effect", "p5_perturbation", "p1_ordering_checks"):
        print(f"\n== {f} ==\n", pd.read_csv(f"tables/{f}.csv").to_string(index=False))
    print("max z_vs_ref:", prices.z_vs_ref.max())


if __name__ == "__main__":
    main()
