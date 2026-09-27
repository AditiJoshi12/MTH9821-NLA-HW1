"""Builds and executes part23_walkthrough.ipynb (companion to run_parts23.py)."""
import nbformat as nbf
from nbclient import NotebookClient
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Parts 2–3 walkthrough — reference, simulation, Longstaff–Schwartz

| module | role |
|---|---|
| `reference.py` | single entry point for the reference: the **supplied** `reference_results.npz` (our solver as cross-check) |
| `part2_supplied_verify.py` | runs the supplied `reference_solver.py --verify` and the cross-check |
| `part2_reference_check.py` | refinement study (spatial / time / domain) vs changing $N$ |
| `simulation.py` | exact paths, training mixture $A$, seeded path sets (README draw order and arithmetic) |
| `lsm.py` | LS regression → threshold → cap, replay check |
| `evaluate.py` | frozen-policy prices, boundary errors, ordering diagnostics |"""),
code("""import numpy as np, pandas as pd
pd.set_option("display.width", 160)
import config as cfg, simulation as sim, lsm, evaluate as ev, part2_reference_check as p2
from reference import load_reference
from IPython.display import Image"""),
md("""## Step 0 — The supplied reference passes `--verify`

The supplied solver is run unchanged. Our independent solver agrees with its arrays to within the refinement changes."""),
code("""display(pd.read_csv("tables/p2_supplied_verify.csv")); display(pd.read_csv("tables/p2_own_vs_supplied.csv"))"""),
md("""## Step 1 — Supplementary: the same refinement study on our own solver

**Design.** Change one numerical setting at a time and record the largest price change and the largest boundary change. The same table shows the effect of going from $N=180$ to $360$, which is a different problem rather than a refinement."""),
code("""display(p2.refinement_table()[["N","delta","refinement","dV_spots","db"]])
display(p2.n_change_table())"""),
md("""**Reading.**
* Supplied reference: spatial and time refinements change prices by about $2\\times10^{-5}$ \\$ and boundaries by about $2\\times10^{-3}$ \\$ (Step 0).
* Our own solver behaves similarly. Its time refinement is essentially zero, because its kernel integrates the lognormal step exactly.
* Changing $N$ (supplied arrays) changes prices by about $2\\times10^{-3}$ \\$ and boundaries by about $0.3$ \\$: a different problem.
* So any accuracy claim smaller than about $2\\times10^{-5}$ \\$ cannot be resolved against the reference."""),
md("""## Step 2 — Exact simulation and the martingale check

Under $Q$, $E[S_T]=S_0e^{rT}(1-\\delta)^3$. We check it on the final $S_0=100$ evaluation sample and report $z$ = (difference)/SE."""),
code("""display(pd.DataFrame([sim.martingale_check(c) for c in range(4)]))
rng = np.random.default_rng(0); A = sim.sample_A(rng, 200_000) / cfg.K
print("P(A/K < 0.2) =", (A < 0.2).mean(), " theory:", 0.5*np.log(200)/np.log(1000))"""),
md("""## Step 3 — Fit LS on each case

**Checks.**
* The fallback, multiple-crossing and capped-date counts.
* The **replay** check: forward application of the frozen rule must reproduce the backward targets exactly."""),
code("""ls = {}
for c in range(4):
    tg, S = sim.training_paths_LS(c)
    ls[c] = lsm.fit_ls(S, tg, sim.CASES[c][1])
    r = ls[c]
    print(c, sim.CASES[c], "fallbacks", len(r.fallback), "| multi-crossing", len(r.multi_cross_dates),
          "| capped", len(r.capped_dates), "| replay max|Q-Y|", r.replay_max_abs_diff)"""),
md("""## Step 4 — Why two crossings?

The cubic is fitted over $x\\in[0.001,1]$. As a result, $H$ dips below zero near $s\\approx3$ and turns positive again before the true boundary. The largest-crossing rule keeps the economically correct single exercise interval."""),
code("""Image("figures/p23_H_example.png")"""),
md("""## Step 5 — Boundaries and prices (Part 5 preview for LS)"""),
code("""Image("figures/p23_boundaries_ls_ref.png")"""),
code("""display(pd.read_csv("tables/p5_prices.csv"))
display(pd.read_csv("tables/p5_paired.csv"))
display(pd.read_csv("tables/p5_boundary_errors.csv"))
display(pd.read_csv("tables/p1_ordering_checks.csv"))"""),
md("""**Reading.**
* LS boundary errors are several percent of $K$, yet the paired price loss against the reference rule is only about 0.02–0.25 \\$. The value is flat near the optimal threshold, so price error is roughly second order in boundary error.
* LS respects the ordering before $d_3$ ($A=0$). The nonzero $F$ after $d_3$ is regression and sampling noise between two independently trained fits."""),
]
nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
nbf.write(nb, "part23_walkthrough.ipynb"); print("ok")
