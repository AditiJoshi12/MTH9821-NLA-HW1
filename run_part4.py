"""
run_part4.py -- Part 4 (neural boundary) for all four cases, then adds the
NN policy to the independent evaluation (prices, boundary errors, Part 1
ordering checks) and the figures.

    python run_part4.py          (needs fitted/ls_boundaries.npz from run_parts23.py)

Writes
  fitted/nn_params_case{c}.pt       selected checkpoint's parameters (+ all checkpoints)
  fitted/nn_boundaries.npz          every checkpoint's float64 boundary, selected one
  fitted/run_config_part4.json      versions, threads, timings, selections
  tables/p4_validation.csv          per case x checkpoint: validation mean, paired diff vs 0, E_mean vs ref
  tables/p4_summary.csv             initial/selected validation means, selected ckpt, timings
  tables/p5_prices.csv, p5_paired.csv, p5_boundary_errors.csv, p1_ordering_checks.csv
  results.csv                       Part 4 / NN rows appended (older NN rows replaced)
  figures/p4_training.png, p4_validation.png, fig1_boundaries.png, fig2_final_dividend.png
"""

import json
import os
import platform
import time

import numpy as np
import pandas as pd
import torch

import config as cfg
import simulation as sim
import evaluate as ev
import nn_policy as NP
import plotting_p23 as PP
from reference import load_reference


class _LS:                                      # tiny adapter for the plotting helpers
    def __init__(self, b):
        self.boundary = b


def main():
    torch.set_num_threads(os.cpu_count())
    lsz = np.load("fitted/ls_boundaries.npz")
    ls = {c: _LS(lsz[f"case{c}_boundary"]) for c in range(4)}

    # ------------------------------------------------------------ training
    nn, val_rows, sum_rows = {}, [], []
    for c in range(4):
        print(f"== case {c} {sim.CASES[c]}")
        out = NP.train_case(c, ls[c].boundary)
        nn[c] = out
        N, d = sim.CASES[c]
        ref = load_reference(N, d)
        for k in sorted(out["val_means"]):
            e = ev.boundary_errors(out["checkpoints"][k], ref.boundary, N)
            md, se = out["val_diff_vs0"][k]
            val_rows.append(dict(case=c, N=N, delta=d, checkpoint=k,
                                 val_mean=out["val_means"][k], diff_vs_ckpt0=md, se_diff=se,
                                 E_mean_vs_ref=e["E_mean"], E_max_vs_ref=e["E_max"],
                                 selected=(k == out["selected"])))
        sum_rows.append(dict(case=c, N=N, delta=d, val_mean_ckpt0=out["val_initial"],
                             selected_checkpoint=out["selected"], val_mean_selected=out["val_selected"],
                             sup_loss_final=out["sup_loss_final"],
                             **{f"time_{k}": v for k, v in out["timings"].items()}))
        torch.save(dict(selected=out["selected"], params=out["params"]),
                   f"fitted/nn_params_case{c}.pt")
    pd.DataFrame(val_rows).to_csv("tables/p4_validation.csv", index=False)
    pd.DataFrame([NP.check_soft_limit(c, ls[c].boundary) for c in range(4)]).to_csv(
        "tables/p4_soft_limit_check.csv", index=False)
    pd.DataFrame(sum_rows).to_csv("tables/p4_summary.csv", index=False)
    np.savez("fitted/nn_boundaries.npz",
             **{f"case{c}_selected": nn[c]["boundary"] for c in nn},
             **{f"case{c}_ckpt{k}": b for c in nn for k, b in nn[c]["checkpoints"].items()})

    # ------------------------------------------ independent evaluation
    t0 = time.perf_counter()
    price_rows, pair_rows, err_rows = [], [], []
    for c in range(4):
        N, d = sim.CASES[c]
        ref = load_reference(N, d)
        rows, paired = ev.price_policies(c, {"LS": ls[c].boundary, "NN": nn[c]["boundary"],
                                             "ref-boundary policy": ref.boundary})
        for r in rows:
            r["ref_value"] = ref.value_at(r["S0"])
            price_rows.append(r)
        for (m1, m2, s0), (md, se) in paired.items():
            pair_rows.append(dict(case=c, pair=f"{m1} - {m2}", S0=s0, mean_diff=md, se=se))
        for m, b in (("LS", ls[c].boundary), ("NN", nn[c]["boundary"])):
            err_rows.append(dict(case=c, N=N, delta=d, method=m, **ev.boundary_errors(b, ref.boundary, N)))
    eval_s = time.perf_counter() - t0
    pd.DataFrame(price_rows).to_csv("tables/p5_prices.csv", index=False)
    pd.DataFrame(pair_rows).to_csv("tables/p5_paired.csv", index=False)
    pd.DataFrame(err_rows).to_csv("tables/p5_boundary_errors.csv", index=False)

    # ---------------------------------- Part 1 ordering checks incl. NN
    ord_rows = []
    for N, (cn, cd) in ((180, (0, 1)), (360, (2, 3))):
        pairs = {"ref": (load_reference(N, 0.0125).boundary, load_reference(N, 0.0).boundary),
                 "LS": (ls[cd].boundary, ls[cn].boundary),
                 "NN": (nn[cd]["boundary"], nn[cn]["boundary"])}
        for m, (bd, b0) in pairs.items():
            ord_rows.append(dict(N=N, method=m, **ev.ordering_diagnostics(bd, b0, N)))
        r0, rd = load_reference(N, 0.0), load_reference(N, 0.0125)
        ord_rows.append(dict(N=N, method="ref: max (V0 - V0.0125)^+ $", A=np.nan, B=np.nan,
                             F=float(np.max(np.maximum(r0.V0 - rd.V0, 0.0)))))
    pd.DataFrame(ord_rows).to_csv("tables/p1_ordering_checks.csv", index=False)

    # ------------------------------------------------ results.csv rows
    res = pd.read_csv("results.csv") if os.path.exists("results.csv") else pd.DataFrame()
    if len(res):
        res = res[~res.section.isin(["p4_validation", "p4_selection", "p5_prices",
                                     "p5_boundary_error", "p1_ordering_checks", "timing"])]
    new = []
    add = lambda sec, met, val, c=None, m=None, s0=None: new.append(dict(
        section=sec, case=c, N=sim.CASES[c][0] if c is not None else None,
        delta=sim.CASES[c][1] if c is not None else None, method=m, S0=s0, metric=met, value=val))
    for r in val_rows:
        add("p4_validation", f"val_mean_ckpt{r['checkpoint']}", r["val_mean"], r["case"], "NN")
    for r in sum_rows:
        add("p4_selection", "selected_checkpoint", r["selected_checkpoint"], r["case"], "NN")
        add("p4_selection", "val_mean_initial", r["val_mean_ckpt0"], r["case"], "NN")
        add("p4_selection", "val_mean_selected", r["val_mean_selected"], r["case"], "NN")
        for k in ("time_supervised_s", "time_banks_s", "time_payoff_s", "time_validation_s"):
            add("timing", k, r[k], r["case"], "NN")
    for r in price_rows:
        for met, key in (("mean", "mean"), ("se", "se"), ("ci_lo", "lo"), ("ci_hi", "hi")):
            add("p5_prices", met, r[key], r["case"], r["method"], r["S0"])
    for r in err_rows:
        add("p5_boundary_error", "E_mean", r["E_mean"], r["case"], r["method"])
        add("p5_boundary_error", "E_max", r["E_max"], r["case"], r["method"])
    for r in ord_rows:
        for k in ("A", "B", "F"):
            add("p1_ordering_checks", f"{k}[N={r['N']}]", r[k], None, r["method"])
    add("timing", "evaluation_3_policies_s", eval_s)
    pd.concat([res, pd.DataFrame(new)]).to_csv("results.csv", index=False)

    # -------------------------------------------------------- figures
    PP.fig_nn_training(nn, "figures/p4_training.png")
    PP.fig_nn_validation(nn, "figures/p4_validation.png")
    PP.fig_ls_vs_ref(ls, "figures/fig1_boundaries.png", nn=nn)
    PP.fig_final_dividend(ls, "figures/fig2_final_dividend.png", nn=nn)

    json.dump(dict(
        torch=torch.__version__, numpy=np.__version__, python=platform.python_version(),
        torch_threads=torch.get_num_threads(), cpu_count=os.cpu_count(),
        device="cpu (no accelerator; nothing to synchronise when timing)",
        training_dtype="float32", validation_evaluation_dtype="float64",
        seeds=dict(torch_construction="5000+c", train_bank="2000+c", val_bank="3000+c"),
        bank_draw_order_ASSUMED="J, then S_J ~ A, then (n, N) normals; see nn_policy.py",
        selected={c: nn[c]["selected"] for c in nn},
        timings={c: nn[c]["timings"] for c in nn}, evaluation_s=eval_s),
        open("fitted/run_config_part4.json", "w"), indent=2)

    pd.set_option("display.width", 220)
    for f in ("p4_summary", "p4_validation", "p5_prices", "p5_paired", "p5_boundary_errors",
              "p1_ordering_checks"):
        print(f"\n== {f} ==\n", pd.read_csv(f"tables/{f}.csv").to_string(index=False))


if __name__ == "__main__":
    main()
