"""Builds and executes part4_walkthrough.ipynb (reads results written by run_part4.py)."""
import nbformat as nbf
from nbclient import NotebookClient
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Part 4 walkthrough — neural exercise boundary (PyTorch)

Run `python run_part4.py` first (about 1.5 min on 2 CPU threads). It trains all four cases and saves the tables and figures this notebook reads. All the modelling code is in `nn_policy.py`.

**Modelling choices that are ours** (everything else follows the assignment):
* The path-bank draw order follows the supplied README: $J$, then $S_J\\sim A$, then the normals. Torch runs with 2 threads, 1 inter-op thread and deterministic algorithms.
* The in-the-money indicator uses $S_j<K$ on the path. Dates before $J$ get $p_j=0$, so they neither stop nor discount.
* Supervised targets are the stored float64 LS thresholds, cast to float32."""),
code("""import numpy as np, pandas as pd, torch
pd.set_option("display.width", 160)
import config as cfg, simulation as sim, nn_policy as NP
from IPython.display import Image
print("torch", torch.__version__, "threads", torch.get_num_threads())"""),
md("""## Step 1 — The model maps each date to its own interval network

For $\\delta>0$ there are four networks. A dividend date belongs to the interval that **starts** there (post-jump). The cap $U_j$ multiplies the sigmoid, so the boundary can never exceed the Part 1 bound."""),
code("""for c in (0, 1):
    N, d = sim.CASES[c]; tg = cfg.TimeGrid(N)
    torch.manual_seed(5000 + c); m = NP.BoundaryModel(tg, d)
    print(f"case {c}: {len(m.nets)} net(s); interval of j = 0, d1-1, d1, d3 ->",
          m.interval[[0, tg.div_idx[0]-1, tg.div_idx[0], tg.j_star]].tolist(),
          "| params:", sum(p.numel() for p in m.parameters()))"""),
md("""## Step 2 — Is the randomised-stopping objective right?

As $\\epsilon\\to0$ the soft objective must equal the hard-rule payoff. We check this with the LS boundary on a throw-away bank."""),
code("""display(pd.read_csv("tables/p4_soft_limit_check.csv"))"""),
md("""## Step 3 — Training curves

The supervised loss drops quickly for $\\delta=0$ (one smooth curve to match). It stalls higher for $\\delta>0$: the LS targets have spikes, and hitting the cap exactly needs sigmoid$\\to1$.

The payoff objective is noisy because random start states make batch means vary by about \\$1. That noise matters for Step 4."""),
code("""Image("figures/p4_training.png")"""),
md("""## Step 4 — Validation and checkpoint selection"""),
code("""display(pd.read_csv("tables/p4_summary.csv"))
display(pd.read_csv("tables/p4_validation.csv"))
Image("figures/p4_validation.png")"""),
md("""**Reading.**
* All selected gains are within about 1.3 paired SE of zero, so selection is close to picking among statistically equal checkpoints. Checkpoint 0 was never selected.
* Payoff training barely changed the boundary error in cases 0–2.
* In case 3 it made the boundary worse ($E_{mean}$ 0.029 → 0.043): the network overshoots just after $d_1$. The validation mean barely reacts, because the value is flat near the optimal threshold."""),
md("""## Step 5 — Independent evaluation (float64, 50,000 fresh paths per start)"""),
code("""p = pd.read_csv("tables/p5_prices.csv")
display(p.pivot_table(index=["case","S0"], columns="method", values="mean"))
display(pd.read_csv("tables/p5_paired.csv"))
display(pd.read_csv("tables/p5_boundary_errors.csv"))
display(pd.read_csv("tables/p1_ordering_checks.csv"))
Image("figures/fig1_boundaries.png")"""),
]
nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
nbf.write(nb, "part4_walkthrough.ipynb"); print("ok")
