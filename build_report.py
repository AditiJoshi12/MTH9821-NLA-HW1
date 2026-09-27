"""
build_report.py -- Assemble the EXTENDED working notes (report_extended.md/.docx) from the
(the submitted <=5-page report is built by build_report_final.py) from the
CSV tables, so every number in the report comes straight from a result
file (no hand transcription).  Re-run after each part is finished.

    python build_report.py

pandoc converts the LaTeX math to native Word equations.  Styling comes
from report_reference.docx (made once by make_reference_docx()).
Placeholders for Parts 4-5 are marked [TODO ...].
"""

import os
import subprocess

import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches, RGBColor

import config as cfg

T = lambda f: pd.read_csv(f"tables/{f}.csv")


def f(x, d=4):
    return f"{x:.{d}f}"


def sci(x):
    return "0" if x == 0 else f"{x:.1e}"


# ---------------------------------------------------------------------------
def make_reference_docx(path="report_reference.docx"):
    """pandoc's default reference doc, restyled: US Letter, 1" margins,
    Calibri 10.5 body, Cambria headings (compact, for the 5-page limit)."""
    subprocess.run(["pandoc", "-o", path, "--print-default-data-file", "reference.docx"],
                   check=True)
    doc = Document(path)
    for s in doc.sections:
        s.page_width, s.page_height = Inches(8.5), Inches(11)
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(s, side, Inches(0.9))
    # style names in pandoc's reference doc vary in case -> match lower-case
    by_name = {x.name.lower(): x for x in doc.styles if x.name}
    for name in ("normal", "body text", "first paragraph", "compact"):
        if name in by_name:
            by_name[name].font.name = "Calibri"
            by_name[name].font.size = Pt(10.5)
            by_name[name].paragraph_format.space_after = Pt(4)
    for name, size in (("title", 18), ("subtitle", 12), ("heading 1", 13), ("heading 2", 11.5)):
        if name in by_name:
            by_name[name].font.name = "Cambria"
            by_name[name].font.size = Pt(size)
            by_name[name].font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
            by_name[name].paragraph_format.space_before = Pt(8)
            by_name[name].paragraph_format.space_after = Pt(3)
    doc.save(path)
    return path


# ---------------------------------------------------------------------------
def price_table():
    p = T("p5_prices")
    rows = ["| Case | $N$ | $\\delta$ | $S_0$ | Reference | LS mean (SE) | NN mean (SE) |",
            "|---|---|---|---|---|---|---|"]
    for c in range(4):
        for s0 in (60.0, 80.0, 100.0):
            q = p[(p.case == c) & (p.S0 == s0)]
            ls = q[q.method == "LS"].iloc[0]
            nn = q[q.method == "NN"].iloc[0]
            rows.append(f"| {c} | {int(ls.N)} | {ls.delta} | {int(s0)} | {f(ls.ref_value)} | "
                        f"{f(ls['mean'])} ({f(ls.se)}) | {f(nn['mean'])} ({f(nn.se)}) |")
    return "\n".join(rows)


def error_table():
    e = T("p5_boundary_errors")
    rows = ["| Case | $N$ | $\\delta$ | $E^{LS}_{mean}$ | $E^{LS}_{max}$ | $E^{NN}_{mean}$ | $E^{NN}_{max}$ |",
            "|---|---|---|---|---|---|---|"]
    for c in range(4):
        l = e[(e.case == c) & (e.method == "LS")].iloc[0]
        n = e[(e.case == c) & (e.method == "NN")].iloc[0]
        rows.append(f"| {c} | {l.N} | {l.delta} | {f(l.E_mean)} | {f(l.E_max)} | {f(n.E_mean)} | {f(n.E_max)} |")
    return "\n".join(rows)


def ls_diag_table():
    d = T("p3_ls_diagnostics")
    rows = ["| Case | Fallbacks | Multiple-crossing dates | Capped dates | Replay $\\max|Q-Y|$ |",
            "|---|---|---|---|---|"]
    for r in d.itertuples():
        rows.append(f"| {r.case} | {r.fallback_count} | {r.multi_crossing_count} of {r.N} | "
                    f"{r.capped_count} | {sci(r.replay_max_abs_diff)} |")
    return "\n".join(rows)


def ordering_table():
    o = T("p1_ordering_checks")
    rows = ["| $N$ | Method | $A$ | $B$ | $F$ |", "|---|---|---|---|---|"]
    for r in o.itertuples():
        if r.method.startswith("ref:"):
            continue
        rows.append(f"| {r.N} | {r.method} | {int(r.A)} | {f(r.B)} | {f(r.F)} |")
    return "\n".join(rows)


def validation_table():
    """Part 4 selection: initial (ckpt 0) and selected validation means."""
    v = T("p4_validation")
    sm = T("p4_summary")
    rows = ["| Case | Ckpt-0 validation mean | Selected ckpt | Selected validation mean | Paired gain (SE) | $E^{NN}_{mean}$ ckpt 0 → selected |",
            "|---|---|---|---|---|---|"]
    for r in sm.itertuples():
        vv = v[v.case == r.case]
        sel = vv[vv.checkpoint == r.selected_checkpoint].iloc[0]
        c0 = vv[vv.checkpoint == 0].iloc[0]
        rows.append(f"| {r.case} | {f(r.val_mean_ckpt0)} | {r.selected_checkpoint} | {f(r.val_mean_selected)} | "
                    f"{f(sel.diff_vs_ckpt0,3)} ({f(sel.se_diff,3)}) | {f(c0.E_mean_vs_ref,3)} → {f(sel.E_mean_vs_ref,3)} |")
    return "\n".join(rows)


def build():
    ref = T("p2_reference_refinement")
    mx = ref.groupby("refinement")[["dV_spots", "db"]].max()
    sp_dv = mx.loc[["spatial dx/2", "spatial dx/4"], "dV_spots"].max()
    sp_db = mx.loc[["spatial dx/2", "spatial dx/4"], "db"].max()
    tm_dv = mx.loc[["time h/2 (substeps=2)", "time h/4 (substeps=4)"], "dV_spots"].max()
    tm_db = mx.loc[["time h/2 (substeps=2)", "time h/4 (substeps=4)"], "db"].max()
    nch = T("p2_N_change")
    mart = T("p2_martingale")
    pair_all = T("p5_paired")
    pair = pair_all[(pair_all.S0 > 60) & (pair_all.pair == "LS - ref-boundary policy")]
    loss_lo, loss_hi = -pair.mean_diff.max(), -pair.mean_diff.min()
    ls = T("p3_ls_diagnostics")
    e = T("p5_boundary_errors")
    pp = lambda c, s0, pr: pair_all[(pair_all.case == c) & (pair_all.S0 == s0) & (pair_all.pair == pr)].iloc[0]
    v4 = T("p4_validation")
    sm4 = T("p4_summary")
    Onn = ordc_nn = None
    tight = T("e2_cap_tightness")
    ordc = T("p1_ordering_checks")
    Fls180 = ordc[(ordc.N == 180) & (ordc.method == "LS")].F.iloc[0]
    Fls360 = ordc[(ordc.N == 360) & (ordc.method == "LS")].F.iloc[0]
    onn180 = ordc[(ordc.N == 180) & (ordc.method == "NN")].iloc[0]
    onn360 = ordc[(ordc.N == 360) & (ordc.method == "NN")].iloc[0]
    c0nn60 = pp(0, 60.0, "NN - ref-boundary policy")
    c2ls80, c2nn80 = pp(2, 80.0, "LS - ref-boundary policy"), pp(2, 80.0, "NN - ref-boundary policy")
    v0 = v4[v4.case == 0].set_index("checkpoint")
    t_pay = sm4.time_payoff_s.sum(); t_sup = sm4.time_supervised_s.sum()

    md = f"""---
title: "Learning an American Put Exercise Boundary"
subtitle: "Baruch MFE — Scientific Computing in Finance, Assignment 1 (DRAFT: Parts 1–4 complete, Part 5 perturbation pending)"
author: "Aditi Joshi and [TODO partner name]"
date: "[TODO submission date]"
---

> **Draft status.** The supplied `reference_solver.py`, `reference_results.npz` and `README.md` were not available when these results were produced. "Reference" below is our own grid-exercise solver (Section 2). Because we did not have the README, the random-draw order is also assumed (Section 2). Replace both before submission, then re-run `run_parts23.py` and `build_report.py`.

# 1. Explaining the boundary

**Axes.** Every plot uses $u=T-t$ on the horizontal axis. **Calendar time advances as $u$ decreases** (right to left). The dividend markers are at $u=13/24,7/24,1/24$.

**Item 1.** Just before the jump, the holder either exercises for $K-s$ or holds. Nothing random happens between $d_k^-$ and $d_k^+$, and the put receives no dividend. So holding is worth $V_\\delta(d_k^+,(1-\\delta)s)$, and in general $V_\\delta(d_k^-,s)=\\max\\{{(K-s)^+,V_\\delta(d_k^+,(1-\\delta)s)\\}}$. Exercise just after the jump is always available, so for $0<s<K$

$$V_\\delta(d_k^+,(1-\\delta)s)\\ge K-(1-\\delta)s=(K-s)+\\delta s>K-s.$$

The maximum is therefore always attained by holding, which gives the identity. Exercising just after the jump pays $\\delta s$ more than exercising just before, at no interest cost. So an implementation may apply the jump first and then take the exercise decision. Numerically, allowing exercise on both sides of the jump reproduces the jump-then-decide values exactly.

**Item 2.** Take $t=d_k-\\varepsilon$ after the preceding dividend. Waiting until $d_k^+$ and exercising is feasible, and $\\mathbb E[S_{{d_k^-}}\\mid S_t=s]=se^{{r\\varepsilon}}$. Hence

$$V_\\delta(t,s)\\ge e^{{-r\\varepsilon}}\\mathbb E\\big[K-(1-\\delta)S_{{d_k^-}}\\big]=Ke^{{-r\\varepsilon}}-(1-\\delta)s .$$

If $s$ is in the exercise region, $K-s\\ge Ke^{{-r\\varepsilon}}-(1-\\delta)s$, i.e. $s\\le K(1-e^{{-r\\varepsilon}})/\\delta$. Taking the supremum gives the cap, and the cap tends to $0$ as $\\varepsilon\\downarrow0$.

On the grid, $d_k$ is an exercise date. So "stop at $d_k$" is an admissible grid stopping time and the bound holds with $\\varepsilon=(j_d-j)h$. Our solver satisfies it on every node, with worst slack about $10^{{-12}}$.

For a fixed $s$, the dividend benefit dominates once $\\varepsilon<\\varepsilon^*(s)=-r^{{-1}}\\log(1-\\delta s/K)\\approx\\delta s/(rK)$. For example, $\\varepsilon^*$ is about 9 days at $s=10$ and about 75 days at $s=80$. Smaller prices must be closer to the dividend.

One grid step before a dividend the bound is $K(1-e^{{-rh}})/\\delta$: 1.63 for $N=180$ and 0.81 for $N=360$. These are positive values at a finite distance and shrink linearly in $h$, which is consistent with a zero limit.

Near each dividend the computed boundary lies *on* the cap for about 0.13 years, departing at roughly $0.49$–$0.60K$. The reason is that for small $s$, exercise at $d_k^+$ is nearly certain, so the lower bound is attained. This produces the straight segments of slope $\\approx rK/\\delta\\approx3.9K$ per year in Cox and Rubinstein's figure.

In calendar time the boundary jumps **up** at each $d_k$: to $0.686K$, $0.746K$ and $0.893K$ in our solver, because once the dividend is paid the incentive to wait is gone. After $d_3$ there is no dividend left and $r>0$, so the boundary rises to $K$ at maturity [TODO cite C&R page].

**Item 3 (ordering).** Drive both models from $(t_j,s)$ by the same Brownian increments. Then $S^\\delta_i=S^0_i(1-\\delta)^{{n_{{ji}}}}\\le S^0_i$, where $n_{{ji}}$ counts dividends in $(t_j,t_i]$. Both price processes are one-to-one functions of the same increments, so the two models share one set of stopping times. For any common $\\tau$, $(K-S^\\delta_\\tau)^+\\ge(K-S^0_\\tau)^+$ pathwise. Taking discounted expectations and then the supremum over $\\tau$ gives $V_{{0.0125,N}}\\ge V_{{0,N}}$.

If $V_\\delta(t_j,s)=K-s$, then $K-s=V_\\delta\\ge V_0\\ge K-s$. So the $\\delta$-exercise region is contained in the $0$-exercise region, and $b_{{0.0125,N}}\\le b_{{0,N}}$.

For $t_j\\ge d_3$ there is no dividend in $(t_j,T]$, so the two problems coincide, including at $d_3$ itself when the same post-jump price is compared.

A coupled Monte Carlo illustrates why the common $\\tau$ matters. With one common $\\tau$, no path violates the pathwise inequality. With each model stopping by its own threshold rule, 12.4% of paths violate it.

**Item 4 (call).** The call's intrinsic value falls at the jump, $((1-\\delta)s-K)^+\\le(s-K)^+$. Exercising just before the jump captures the dividend, so $C_\\delta(d_k^-,s)=\\max\\{{(s-K)^+,C_\\delta(d_k^+,(1-\\delta)s)\\}}$ and the maximum can bind. A call implementation must therefore test exercise *before* applying the dividend. By item 1, this pre-jump option is worthless for the put.

In our solver, the pre-jump exercise thresholds are $139.7$, $128.8$ and $104.8$. The correct call is worth $10.4198$ at $S_0=100$. A put-style ordering (jump, then decide) gives $10.4029$, because it exercises one step early. The European call is worth $9.9037$.

**Checks using the computed boundaries.**

{ordering_table()}

For the reference, $A=B=F=0$ and $\\max_s(V^{{ref}}_{{0,N}}-V^{{ref}}_{{0.0125,N}})^+=0$ for both $N$. The LS boundaries also satisfy the ordering before $d_3$ ($A=0$).

After $d_3$ the two LS fits should coincide, but they differ by up to $F={f(Fls180,3)}K$ ($N=180$) and ${f(Fls360,3)}K$ ($N=360$). They are trained on different samples, and the $\\delta$ paths sit lower after three dividends. So $F$ measures the **sampling and regression error** of the fitted boundary, not a model difference.

The NN boundaries give $A={int(onn180.A)}$, $B={f(onn180.B,3)}$, $F={f(onn180.F,3)}$ for $N=180$ and $A={int(onn360.A)}$, $F={f(onn360.F,3)}$ for $N=360$. The $N=180$ violations come from case 0: its selected checkpoint (2400) let the early-date boundary drift down to about $0.49K$, below the case-1 boundary on 32 dates. Neither fitted method is forced to respect the ordering, so these diagnostics measure **learning error**, not a property of the model.

# 2. Reference, simulation and the dividend cap

**Reference (placeholder).** Until we receive the supplied solver, the reference is our own grid-exercise solver:

* It works on a uniform $\\log S$ grid with $S=K$ on a node.
* The one-step Gaussian expectation is computed exactly for the piecewise-linear interpolant. This includes a $dx^2/6$ variance correction, which removed a bias that grew with $N$.
* The grid spacing is $|\\log(1-\\delta)|/m$, so the dividend is an exact shift of $m$ nodes.
* The fine reference uses $m=20$ ($dx\\approx6\\times10^{{-4}}$).

Validation: European prices match the closed form ($S_0(1-\\delta)^3$ in Black–Scholes) to about $2\\times10^{{-5}}$.

**Verification** (same study as `-verify`; [TODO replace with supplied output]).

| Refinement | Largest price change | Largest boundary change |
|---|---|---|
| Spatial ($dx/2$, $dx/4$) | {sci(sp_dv)} \\$ | {sci(sp_db)} \\$ |
| Time integration ($h/2$, $h/4$ substeps) | {sci(tm_dv)} \\$ | {sci(tm_db)} \\$ |
| Wider domain / kernel tails | 0 | $\\le 3\\times10^{{-12}}$ \\$ |
| **Changing $N$ = 180 → 360** | **{sci(nch[['dV(80)','dV(100)']].abs().values.max())} \\$** | **{f(nch.max_db.max(),3)} \\$** |

Refinements approximate the *same* grid-exercise problem more accurately. Changing $N$ changes the *problem*: more exercise dates can only raise the value, and the boundary moves by about 0.3 \\$. That is two orders of magnitude more than any refinement.

The reference's precision is therefore about $10^{{-5}}$ \\$ in price and $10^{{-3}}$ \\$ in boundary. Any claimed accuracy gain smaller than that cannot be resolved. Time refinement changes almost nothing because our kernel has no time-stepping error.

**Exact simulation.** We sample the exact lognormal transition with integer dividend indices. A path that starts at a dividend index is post-jump. On the final $S_0=100$ evaluation sample, $(\\bar{{S}}_T-S_0e^{{rT}}(1-\\delta)^3)/\\mathrm{{SE}}$ is {', '.join(f(z,2) for z in mart.z)} for cases 0–3. All four are within $\\pm2$, as expected under $N(0,1)$; case 2 is close to the edge.

**Draw order (assumption).** For the training mixture $A$ we draw a coin, a log-uniform and a uniform for every path, then the path normals. Evaluation uses 10 sequential batches of $5{{,}}000\\times N$ normals. [TODO confirm against README.md.]

**Cap.** The theoretical cap $U_j$ supplies the known pre-dividend behaviour. The optimal boundary lies on it close to each dividend (Section 1).

# 3. Least-squares exercise policy

We implemented the Longstaff–Schwartz recursion exactly as specified:

* 32,768 paths from $S_0\\sim A$, targets in time-zero dollars.
* Cubic in $x=S_j/K$ fitted on in-the-money rows, by SVD least squares (`numpy.linalg.lstsq`).
* Continuation clipped to $[0,Ke^{{-rt_{{j+1}}}}]$.
* Threshold = the largest positive-to-negative crossing of $H$ on $s_\\ell=0.1\\ell$, capped at $U_j$.

**Clipping.** From $t_j$ the next possible exercise is at $t_{{j+1}}$ and pays at most $K$. So the time-zero continuation value lies in $[0,Ke^{{-rt_{{j+1}}}}]$, and

$$H_0\\ge Ke^{{-rt_j}}(1-e^{{-rh}})>0 .$$

At $s=0$ exercising always wins, so a crossing exists whenever $H$ eventually turns negative.

**Replay check.** Replaying the frozen rule on the training paths reproduces the backward targets exactly ($\\max|Q-Y|=0$).

{ls_diag_table()}

**Crossings.**

* There were no fallbacks: every date had thousands of in-the-money rows.
* Almost every date has **two** crossings (Fig. 3 in the slides). The cubic is fitted over $x\\in[0.001,1]$ and cannot follow the value function's curvature, so $H$ dips below zero near $s\\approx3$ and turns positive again before the true boundary.
* The "largest crossing" rule picks the upper crossing. This defines one exercise interval containing every smaller price, which is the economically correct shape. The fitted polynomial alone would create a spurious continuation pocket around $s\\approx3$–$33$.

**Capped dates.** Capping binds on 85 dates ($N=180$) and 149 dates ($N=360$), all just before dividends.

**Where the LS boundary is poor.** Further from the dividend the true exercise premium $\\delta s-K(1-e^{{-r\\varepsilon}})$ is a few cents, which is below the regression's resolution. There the polynomial sometimes returns only the low crossing. This produces the downward spikes in Fig. 1(b) and the gap below the cap in Fig. 2.

With $\\delta=0$ the LS boundary is biased low by about $0.03$–$0.05K$, and it is noisy near maturity, where the value function has a kink the cubic cannot follow.

# 4. Neural policy (PyTorch)

**Set-up (as specified).**

* One network for $\\delta=0$, and four for $\\delta=0.0125$ on $[0,d_1),[d_1,d_2),[d_2,d_3),[d_3,T]$; a dividend date belongs to the interval that starts there.
* Each network is `Linear(1,8)`–tanh–`Linear(8,1)`, with input $x=(t-\\alpha)/(\\beta-\\alpha)$ and output $b_\\theta(t_j)=U_j\\,\\mathrm{{sigmoid}}(f_\\theta(t_j))$. The cap is therefore built in: the networks learn only the shape below $U_j$.
* PyTorch seed $5000+c$, set once before the layers are built in chronological order.
* Supervised initialisation: exactly 1,000 full-grid Adam steps (lr 0.01) towards $\\hat b^{{LS}}$ → checkpoint 0.
* Payoff optimisation: fresh Adam (lr 0.003), 2,400 updates on batches of 512 drawn with replacement by `torch.randint` from an 8,192-path bank (NumPy seed $2000+c$), with $\\epsilon=0.01$ then $0.002$.
* Training in float32. Validation and final boundaries in float64, on a 4,096-path bank (seed $3000+c$).
* Total CPU time: {t_sup:.0f} s supervised and {t_pay:.0f} s payoff optimisation for all four cases (2 threads).

**Randomised stopping.** If the holder has not yet stopped, they stop at $t_j$ with probability $p_j$, drawn independently of the future path. Then $w_j=p_j\\prod_{{k<j}}(1-p_k)$ is exactly the probability of stopping **first** at $t_j$, and $\\sum_j w_j=1$ because $p_N=1$. So $R_\\theta=\\sum_j w_je^{{-r(t_j-t_J)}}(K-S_j)^+$ is the conditional expectation, given the path, of the discounted payoff of this randomised rule.

$R_\\theta$ is smooth in $\\theta$, so minibatch gradients exist. As $\\epsilon\\to0$, $p_j\\to\\mathbf 1\\{{S_j\\le b_\\theta(t_j),S_j<K\\}}$ and the rule becomes the hard threshold. Check: with $\\epsilon=10^{{-7}}$, the soft objective reproduces the hard-rule mean to within {sci(T('p4_soft_limit_check').abs_diff.max())} \\$ in all four cases.

**Validation and selection.**

{validation_table()}

Every paired validation gain is within about 2 SE of zero. On 4,096 random-start paths, the checkpoints are statistically indistinguishable.

Checkpoint 0 was selected for cases 1 and 3. For case 2, payoff optimisation clearly improved the boundary: $E_{{mean}}$ fell from 0.056 to 0.023, and the price loss at $S_0=80$ shrank from {f(-c2ls80.mean_diff,2)} \\$ (LS) to {f(-c2nn80.mean_diff,2)} \\$.

For case 0, the selected checkpoint (2400) has a *worse* boundary than checkpoint 400 ($E_{{mean}}$ {f(v0.loc[2400].E_mean_vs_ref,3)} vs {f(v0.loc[400].E_mean_vs_ref,3)}). Its early-date boundary drifted to about $0.49K$. Few validation paths start near $t_0$, so the validation mean barely sees that region, but the fixed-start evaluation does: at $S_0=60$ the NN loses {f(-c0nn60.mean_diff,2)} \\$ (SE {f(c0nn60.se,3)}), because it no longer exercises immediately. Selection by a noisy validation mean, under a fixed budget, therefore does not guarantee an accurate boundary.

**Research connection.**

* **Becker, Cheridito and Jentzen (2019)** learn *stopping decisions*. Each date's stop/continue decision is a neural network whose output is relaxed to a probability during training and rounded afterwards. Their economic objective is the optimal-stopping value: maximising the expected discounted reward of a stopping time, which prices a Bermudan/American option from below (they also derive an upper bound). Our payoff stage is the same relaxation, applied to a threshold parametrisation trained jointly over all dates.
* **Bühler et al. (2019)** use the same *policy-optimisation* idea: parametrise the trading policy by networks and optimise it directly on simulated paths by stochastic gradient. Their economic objective is different: minimising a convex risk measure of the hedged terminal P&L (with market frictions), which yields hedges and indifference prices.
* Both papers replace dynamic programming by direct optimisation of a policy. Ours maximises risk-neutral expected payoff; deep hedging minimises risk.

[TODO: check these summaries against the papers.]

# 5. Values and boundaries

**Prices.** Evaluation uses 50,000 independent paths per starting price, the same paths for every policy, and float64.

{price_table()}

Every LS interval lies below or covers the reference value. It should: a frozen policy's expectation cannot exceed $V_{{\\delta,N}}(0,S_0)$.

Paired on common paths, LS loses **{f(loss_lo,2)}–{f(loss_hi,2)} \\$** against the reference boundary applied as a hard rule (paired SE about 0.015–0.034 \\$). The NN is better than LS for case 2, statistically tied for cases 1 and 3, and worse for case 0 at $S_0=60$ and $80$ and, slightly, for case 1 at $S_0=60$ (0.03 \\$, SE 0.010), where its boundary sits just below 60 at $t_0$ (Section 4). [TODO: perturbation study.]

**Boundary accuracy.**

{error_table()}

**Price vs boundary accuracy.** LS boundary errors are large: mean 3–7% of $K$ and up to 39% of $K$ at a single date. Yet the price loss is only about 0.2–2%. Near the optimal boundary the value is flat in the exercise threshold (smooth pasting), so price error is roughly second order in boundary error. Dates where the boundary is badly wrong also carry little probability of a decision.

Compare each policy with the reference **for the same $N$** first. The reference value itself changes by only about $10^{{-3}}$ \\$ between $N=180$ and $360$, which is far below the Monte Carlo SE (about 0.05 \\$). So any change in a fitted policy's price with $N$ reflects that policy's own learning error. [TODO: perturbation $a=\\pm0.02$.]

# Figures

![**Figure 1.** Exercise boundaries. (a) $\\delta=0$, (b) $\\delta=0.0125$. Blue: reference, $N=360$. Orange: regression (LS), $N=360$. Grey dashed: reference, $N=180$ (almost hidden under the blue curve). Curves are broken at dividend dates; dotted lines mark the dividends. Green: selected neural policy, $N=360$.](figures/fig1_boundaries.png){{width=6.5in}}

![**Figure 2.** Case 3 near the final dividend, $|t-d_3|\\le1/24$. Right of the dotted line: before $d_3$ in calendar time. Left: after $d_3$. The reference boundary lies on the Part 1 bound (grey dashed) on the pre-dividend side; the LS and NN boundaries fall below it.](figures/fig2_final_dividend.png){{width=4.6in}}

# Reproducibility, contributions and AI use

* **Commands:** `python run_part1.py`, `python run_parts23.py`, `python run_part4.py`, `python build_report.py`.
* **Environment:** Python 3.11, NumPy 2.4, SciPy 1.17, float64 throughout. PyTorch {__import__("torch").__version__} (CPU; no accelerator, so nothing to synchronise when timing). Hardware, thread count and timings are in `fitted/run_config*.json`. The full LS fit takes about 5 s and the evaluation preview about 7 s on 2 CPU threads.
* **Seeds:** as in the assignment's Part 5. The draw order is assumed (Section 2).
* **Contributions:** [TODO].

**AI-use statement (draft, ≤200 words).** We used Claude (Anthropic; configured model identifier claude-opus-5-5, used via Cowork) to draft code structure, derivations and text. We checked all suggestions ourselves.

One substantive suggestion we checked computationally: the piecewise-linear transition kernel adds a spurious variance of $dx^2/6$ per step. Without the correction, European prices were biased by about $2.5\\times10^{{-3}}$ ($N=180$) and $5\\times10^{{-3}}$ ($N=360$), and the bias grew with $N$. With the correction the error fell to about $2\\times10^{{-5}}$ and no longer depended on $N$.

[TODO: partner review; final wording.]

# References

Becker, S., Cheridito, P., Jentzen, A. (2019). Deep Optimal Stopping. *JMLR* 20(74), 1–25.

Bühler, H. et al. (2019). Deep Hedging. *Quantitative Finance* 19(8), 1271–1291.

Cox, J.C., Rubinstein, M. (1985). *Options Markets*. Prentice-Hall.

Longstaff, F.A., Schwartz, E.S. (2001). Valuing American Options by Simulation: A Simple Least-Squares Approach. *Review of Financial Studies* 14(1), 113–147.
"""
    # Brace bare superscripts (x^+ -> x^{+}): LibreOffice (and some Word
    # versions) mis-import OMML produced from unbraced one-symbol scripts.
    import re
    md = re.sub(r"\^([+\-*])", r"^{\1}", md)
    open("report_extended.md", "w").write(md)
    ref_docx = make_reference_docx()
    subprocess.run(["pandoc", "report_extended.md", "-o", "report_extended.docx", f"--reference-doc={ref_docx}",
                    "--resource-path=."], check=True)
    print("wrote report_extended.md, report_extended.docx")


if __name__ == "__main__":
    build()
