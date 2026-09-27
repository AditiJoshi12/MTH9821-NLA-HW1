"""Builds and executes part5_walkthrough.ipynb (reads results of run_part5.py)."""
import nbformat as nbf
from nbclient import NotebookClient
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Part 5 walkthrough — independent evaluation

`run_part5.py` computes everything in this notebook, and all the logic is in `part5.py`. Every fit and checkpoint selection (Parts 3–4) finishes before any evaluation path is generated.

**Design**
* Each case and start gets 50,000 fresh paths (seed $4000+10c+a$, batches of 5,000).
* The same paths are used for LS, NN and the reference boundary applied as a hard rule. Differences between policies are therefore **paired**, and their SEs are much smaller than the SE of each price.
* Everything is float64."""),
code("""import pandas as pd, numpy as np
pd.set_option("display.width", 180)
from IPython.display import Image"""),
md("""## 1. Prices and the upper bound

A frozen rule is one admissible stopping time, so $E[Q]\\le V_{\\delta,N}(0,S_0)$. We check that no fitted mean sits significantly above the reference, using $z=(\\text{mean}-V^{ref})/\\text{SE}$. At $S_0=60$ every path exercises immediately, so the SE is about 0 and $z$ is undefined (NaN)."""),
code("""p = pd.read_csv("tables/p5_prices.csv")
display(p[["case","S0","method","mean","se","lo","hi","ref_value","z_vs_ref"]])
print("largest z among fitted policies:", p[p.method.isin(["LS","NN"])].z_vs_ref.max())"""),
code("""pp = pd.read_csv("tables/p5_paired.csv")
display(pp.pivot_table(index=["case","S0"], columns="pair", values="mean_diff").round(4))"""),
md("""## 2. Boundary accuracy, and how much the optimum moves with $N$

$E_{mean}$ and $E_{max}$ compare each method with the reference **for the same $N$**. `p5_N_effect` measures how much the *optimal* boundary moves between $N=180$ and $360$. That movement is the yardstick for reading a fitted method's change with $N$."""),
code("""display(pd.read_csv("tables/p5_boundary_errors.csv"))
display(pd.read_csv("tables/p5_N_effect.csv"))"""),
md("""## 3. Perturbation (case 3, $S_0=100$)

$b^{(a)}_j=\\min\\{U_j,\\max\\{0,\\hat b^{NN}_j+aK\\}\\}$, evaluated on the same evaluation paths.

The extra columns explain the mechanism:
* how much of the shift survives the cap and the floor;
* how many paths actually change their stopping time;
* in which direction the stopping time moves.

The finer sweep is supplementary; it is not required by the assignment."""),
code("""display(pd.read_csv("tables/p5_perturbation.csv"))
display(pd.read_csv("tables/p5_perturbation_sweep_supplementary.csv")[["a","mean_diff","se_diff","applied_shift_mean","frac_paths_changed","cap_binds_dates"]])
Image("figures/p5_perturbation.png")"""),
md("""## 4. Ordering diagnostics with the final policies"""),
code("""display(pd.read_csv("tables/p1_ordering_checks.csv"))"""),
]
nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
nbf.write(nb, "part5_walkthrough.ipynb"); print("ok")
