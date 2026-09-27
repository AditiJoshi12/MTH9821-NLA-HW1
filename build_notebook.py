"""Builds and executes part1_walkthrough.ipynb (run once; not part of the analysis)."""
import nbformat as nbf
from nbclient import NotebookClient

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Part 1 walkthrough — Explain the boundary & dividend ordering

Step-by-step companion to `part1_writeup.md`. Every cell calls a function from the modules:

| module | role |
|---|---|
| `config.py` | fixed parameters, time grid with **integer** dividend indices, cap $U_j$ |
| `lognormal_kernel.py` | exact one-step Gaussian expectation on a log grid |
| `grid_solver.py` | **our own** grid-exercise solver (put/call, dividend/exercise ordering) |
| `analytics.py` | Black–Scholes closed form, used only for validation |
| `experiments_part1.py` | experiments E1–E4 |
| `plotting.py` | figures (axis $u=T-t$, $b/K$) |

> The supplied `reference_solver.py` was not available, so "ref" below means **our** solver. Re-run the E3 diagnostics with the supplied solver later."""),
code("""import pandas as pd, numpy as np
pd.set_option("display.width", 160); pd.set_option("display.precision", 6)
import config as cfg, experiments_part1 as E, plotting as P
from IPython.display import Image
for N in cfg.NS:
    tg = cfg.TimeGrid(N)
    print(f"N={N}: h={tg.h:.6f}, dividend indices={tg.div_idx}, j*={tg.j_star}")"""),
md("""## Step 0 — Can we trust our solver?

**Experiment design.** Turn off early exercise and compare with the closed form. With proportional dividends, a European option equals Black–Scholes at spot $S_0(1-\\delta)^3$. This one check tests three things at once: the kernel, the exact dividend shift, and the truncated domain. Then we halve $dx$ to check spatial convergence.

**What to look for.**
* The European error does **not** grow with $N$. This is the purpose of the variance correction, $\\sigma^2h - dx^2/6$.
* Refinement changes values by about $10^{-5}$."""),
code("""import validate_solver as VS
VS.check_kernel(); VS.check_european(); VS.check_refinement()"""),
md("""## Step 1 — Direction of time

The horizontal axis is time remaining, $u=T-t$. **Calendar time advances right → left.** In panel (b), each dividend marker has the near-zero boundary on its **right** (just *before* the dividend in calendar time). The high post-jump boundary is on its **left**."""),
code("""P.fig_boundaries("figures/p1_boundaries.png"); Image("figures/p1_boundaries.png")"""),
md("""## Step 2 — Item 1: never exercise the put just before the jump

**Design.** At each $d_k$, take the pre-jump value $W(s)=V(d_k^+,(1-\\delta)s)$ from the solver and compare it with the pre-jump payoff $K-s$. The theory predicts $W(s)-(K-s)\\ge\\delta s>0$.

We then re-solve the put under three orderings:
* `after`: the assignment's rule (jump, then decide).
* `both`: exercise allowed on either side of the jump.
* `before`: exercise allowed only before the jump."""),
code("""display(E.e1_dividend_identity()); display(E.e1_put_orderings())"""),
md("""**Reading.**
* `min_excess` is about $-4\\times10^{-14}$, i.e. zero. The gap is **exactly** $\\delta s$ wherever the put is exercised at $d_k^+$.
* `both` equals `after` to machine precision: pre-jump exercise is worthless.
* `before` is strictly worse."""),
code("""P.fig_pre_jump("figures/p1_pre_jump.png"); Image("figures/p1_pre_jump.png")"""),
md("""## Step 3 — Item 2: the cap and its limit

**Design.**
1. Check the lower bound $V\\ge Ke^{-r\\varepsilon}-(1-\\delta)s$ on every grid node before each dividend.
2. Tabulate $b_j$ against $K(1-e^{-r\\varepsilon})/\\delta$ for the last few grid dates before each $d_k$.
3. Compute $\\varepsilon^*(s)$, the $s$-dependent proximity.
4. Show that the one-step cap shrinks with $h$.
5. Show the limit at maturity."""),
code("""print("worst slack of the lower bound:", {N: E.e2_lower_bound_check(N) for N in cfg.NS})
display(E.e2_cap_table(180))"""),
code("""display(E.e2_one_step_cap()); display(E.e2_proximity()); display(E.e2_maturity_limit())"""),
md("""**An unexpected finding worth reporting.** Near each dividend the boundary sits **on** the cap, not merely below it. The reason is that for small $s$, exercise at $d_k^+$ is essentially certain, so the continuation value *equals* the wait-and-exercise value. This explains the straight lines in the Cox–Rubinstein figure, with slope $\\approx rK/\\delta$."""),
code("""print("slope r/delta =", cfg.R/E.DELTA)
for N in cfg.NS: display(E.e2_cap_tightness(N).assign(N=N))
P.fig_cap_zoom("figures/p1_cap_zoom.png"); Image("figures/p1_cap_zoom.png")"""),
code("""P.fig_proximity("figures/p1_proximity.png"); Image("figures/p1_proximity.png")"""),
md("""## Step 4 — Item 3: dividend ordering

**Design.**
* Compute the assignment's diagnostics $A$, $B$, $F$ with $M=$ ref (ours). Also compute $\\max(V_0-V_\\delta)^+$ at $t_0$ and on every date.
* Run a coupled Monte Carlo that mirrors the proof. The **same** normals drive both models. We compare:
  * one **common** stopping time, versus
  * a model-specific rule.

(Seed 9001 is ours and avoids the assignment's seed ranges.)"""),
code("""display(E.e3_ordering_diagnostics()); display(E.e3_coupled_mc())"""),
md("""**Reading.**
* With a common $\\tau$, **no path** violates $Q_\\delta\\ge Q_0$.
* With model-specific $\\tau$, about 12% of paths do, although the averages remain ordered.
* This is exactly why the proof fixes $\\tau$ first and takes the supremum last.

The LS/NN rows of these diagnostics come later (Parts 3–4)."""),
md("""## Step 5 — Item 4: exercise timing for a call

**Design.** Solve the call four ways:
* European
* put-style ordering (jump, then decide)
* pre-jump-only exercise
* correct (both sides)

Then find the pre-jump thresholds $s^*_k$."""),
code("""display(E.e4_call_orderings())
thr, other = E.e4_call_pre_div_threshold(); display(thr)
print("early-exercise nodes at any post-jump / non-dividend date (S<5K):", other)"""),
md("""**Reading.**
* The correct call must test exercise **before** applying the dividend.
* The put-style implementation instead exercises one grid step early and loses the interest $K(1-e^{-rh})$. Its value lies between the European and the correct values.
* For the put, `both` = `after` (Step 2), so jump-then-decide is exact."""),
]
nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
nbf.write(nb, "part1_walkthrough.ipynb")
print("ok")
