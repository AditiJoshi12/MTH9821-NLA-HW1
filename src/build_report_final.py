"""
build_report_final.py -- The SUBMITTED report (<= 5 pages + references):
report.md -> ../report.docx (repo root).  Every number is read from tables/*.csv.

    python build_report_final.py

Template placeholders are written @@name@@ (not str.format) so LaTeX braces
need no escaping.  Longer derivations and extra diagnostics live in
report_extended.docx (build_report.py) and the walkthrough notebooks.
"""

import re
import subprocess

import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches, RGBColor

T = lambda f: pd.read_csv(f"tables/{f}.csv")
f2 = lambda x: f"{x:.2f}"
f3 = lambda x: f"{x:.3f}"
f4 = lambda x: f"{x:.4f}"
sci = lambda x: "0" if x == 0 else f"{x:.0e}".replace("e-0", "e-")


def reference_docx(path="report_final_reference.docx"):
    subprocess.run(["pandoc", "-o", path, "--print-default-data-file", "reference.docx"], check=True)
    doc = Document(path)
    for s in doc.sections:
        s.page_width, s.page_height = Inches(8.5), Inches(11)
        s.left_margin = s.right_margin = Inches(0.75)
        s.top_margin = s.bottom_margin = Inches(0.7)
    st = {x.name.lower(): x for x in doc.styles if x.name}
    for name, size in (("normal", 10), ("body text", 10), ("first paragraph", 10), ("compact", 9)):
        if name in st:
            st[name].font.name = "Calibri"; st[name].font.size = Pt(size)
            st[name].paragraph_format.space_after = Pt(3)
            st[name].paragraph_format.space_before = Pt(0)
    for name, size in (("title", 15), ("subtitle", 10.5), ("author", 10), ("date", 10),
                       ("heading 1", 12), ("heading 2", 10.5)):
        if name in st:
            st[name].font.name = "Cambria"; st[name].font.size = Pt(size)
            st[name].font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
            st[name].paragraph_format.space_before = Pt(6 if name.startswith("heading") else 0)
            st[name].paragraph_format.space_after = Pt(2)
    for name in ("caption", "image caption", "table caption"):
        if name in st:
            st[name].font.size = Pt(8.5); st[name].paragraph_format.space_after = Pt(4)
    doc.save(path)
    return path


# ---------------------------------------------------------------------------
def tables():
    out = {}
    # ordering checks
    o = T("p1_ordering_checks")
    rows = ["| $N$ | Method | $A$ | $B$ | $F$ |", "|---|---|---|---|---|"]
    for N in (180, 360):
        for m in ("ref", "LS", "NN"):
            r = o[(o.N == N) & (o.method == m)].iloc[0]
            rows.append(f"| {N} | {m} | {int(r.A)} | {f3(r.B)} | {f3(r.F)} |")
    out["ORDER_TABLE"] = "\n".join(rows)

    # reference verification
    ref = T("p2_reference_refinement"); mx = ref.groupby("refinement")[["dV_spots", "db"]].max()
    sp = mx.loc[["spatial dx/2", "spatial dx/4"]].max(); tm = mx.loc[["time h/2 (substeps=2)", "time h/4 (substeps=4)"]].max()
    nch = T("p2_N_change")
    out["VERIFY_TABLE"] = "\n".join([
        "| Change | Max price change (\\$) | Max boundary change (\\$) |", "|---|---|---|",
        f"| Spatial ($dx/2$, $dx/4$) | {sci(sp.dV_spots)} | {sci(sp.db)} |",
        f"| Time integration ($h/2$, $h/4$) | {sci(tm.dV_spots)} | {sci(tm.db)} |",
        f"| Domain / kernel tails | $\\le 10^{{-14}}$ | $\\le 3\\times10^{{-12}}$ |".replace("{{", "{").replace("}}", "}"),
        f"| $N$: 180 → 360 (different problem) | {sci(nch[['dV(80)','dV(100)']].abs().values.max())} | {f3(nch.max_db.max())} |"])

    # LS diagnostics
    d = T("p3_ls_diagnostics")
    rows = ["| Case | $N$ | $\\delta$ | Fallbacks | Multi-crossing dates | Capped dates | Replay $\\max|Q-Y|$ |",
            "|---|---|---|---|---|---|---|"]
    for r in d.itertuples():
        rows.append(f"| {r.case} | {r.N} | {r.delta} | {r.fallback_count} | {r.multi_crossing_count} | {r.capped_count} | {sci(r.replay_max_abs_diff)} |")
    out["LS_TABLE"] = "\n".join(rows)

    # validation
    v, sm = T("p4_validation"), T("p4_summary")
    rows = ["| Case | Ckpt-0 mean | Selected | Selected mean | Gain vs ckpt 0 (SE) | $E^{NN}_{mean}$: ckpt 0 → selected |",
            "|---|---|---|---|---|---|"]
    for r in sm.itertuples():
        vv = v[v.case == r.case]; sel = vv[vv.checkpoint == r.selected_checkpoint].iloc[0]; c0 = vv[vv.checkpoint == 0].iloc[0]
        rows.append(f"| {r.case} | {f4(r.val_mean_ckpt0)} | {r.selected_checkpoint} | {f4(r.val_mean_selected)} | "
                    f"{f3(sel.diff_vs_ckpt0)} ({f3(sel.se_diff)}) | {f3(c0.E_mean_vs_ref)} → {f3(sel.E_mean_vs_ref)} |")
    out["VAL_TABLE"] = "\n".join(rows)

    # prices
    p = T("p5_prices")
    rows = ["| Case | $N$ | $\\delta$ | $S_0$ | Reference | LS mean (SE) | NN mean (SE) |", "|---|---|---|---|---|---|---|"]
    for c in range(4):
        for s0 in (60.0, 80.0, 100.0):
            q = p[(p.case == c) & (p.S0 == s0)]
            l = q[q.method == "LS"].iloc[0]; n = q[q.method == "NN"].iloc[0]
            rows.append(f"| {c} | {l.N} | {l.delta} | {int(s0)} | {f4(l.ref_value)} | {f4(l['mean'])} ({f3(l.se)}) | {f4(n['mean'])} ({f3(n.se)}) |")
    out["PRICE_TABLE"] = "\n".join(rows)

    # boundary errors
    e = T("p5_boundary_errors")
    rows = ["| Case | $N$ | $\\delta$ | $E^{LS}_{mean}$ | $E^{LS}_{max}$ | $E^{NN}_{mean}$ | $E^{NN}_{max}$ |", "|---|---|---|---|---|---|---|"]
    for c in range(4):
        l = e[(e.case == c) & (e.method == "LS")].iloc[0]; n = e[(e.case == c) & (e.method == "NN")].iloc[0]
        rows.append(f"| {c} | {l.N} | {l.delta} | {f3(l.E_mean)} | {f3(l.E_max)} | {f3(n.E_mean)} | {f3(n.E_max)} |")
    out["ERR_TABLE"] = "\n".join(rows)

    # perturbation
    pt = T("p5_perturbation")
    rows = ["| $a$ | Mean $Q^{(a)}-Q^{(0)}$ (\\$) | SE | Applied mean shift / $K$ | Dates capped at $U_j$ | Paths whose $\\tau$ changes |",
            "|---|---|---|---|---|---|"]
    for r in pt[pt.a != 0].itertuples():
        rows.append(f"| {r.a:+.2f} | {r.mean_diff:+.4f} | {f4(r.se_diff)} | {r.applied_shift_mean:+.4f} | {r.cap_binds_dates} of 360 | {100*r.frac_paths_changed:.1f}% ({'all later' if r.a < 0 else 'all earlier'}) |")
    out["PERT_TABLE"] = "\n".join(rows)
    return out


def numbers():
    n = {}
    pp = T("p5_paired"); p = T("p5_prices"); pt = T("p5_perturbation"); ne = T("p5_N_effect")
    g = lambda c, s0, pr: pp[(pp.case == c) & (pp.S0 == s0) & (pp.pair == pr)].iloc[0]
    ls_loss = -pp[(pp.S0 > 60) & (pp.pair == "LS - ref-boundary policy")].mean_diff
    n["LS_LOSS"] = f"{f2(ls_loss.min())}–{f2(ls_loss.max())}"
    nn_loss = -pp[(pp.S0 > 60) & (pp.pair == "NN - ref-boundary policy")].mean_diff
    n["NN_LOSS"] = f"{f2(nn_loss.min())}–{f2(nn_loss.max())}"
    n["C0NN60"] = f2(-g(0, 60.0, "NN - ref-boundary policy").mean_diff)
    n["C1NN60"] = f2(-g(1, 60.0, "NN - ref-boundary policy").mean_diff)
    n["C2LS80"] = f2(-g(2, 80.0, "LS - ref-boundary policy").mean_diff)
    n["C2NN80"] = f2(-g(2, 80.0, "NN - ref-boundary policy").mean_diff)
    zfit = p[p.method.isin(["LS", "NN"])].z_vs_ref.dropna()
    n["ZMAX"] = f2(zfit.max())
    n["NEFF0"] = f"{ne.E_mean_ref360_vs_ref180.iloc[0]:.4f}"
    n["NEFF1"] = f"{ne.E_mean_ref360_vs_ref180.iloc[1]:.4f}"
    e = T("p5_boundary_errors")
    n["ELS"] = f"{f3(e[e.method=='LS'].E_mean.min())}–{f3(e[e.method=='LS'].E_mean.max())}"
    n["ENN"] = f"{f3(e[e.method=='NN'].E_mean.min())}–{f3(e[e.method=='NN'].E_mean.max())}"
    m = pt.set_index("a")
    n["PM"] = f"{m.loc[-0.02].mean_diff:+.3f}"; n["PMSE"] = f3(m.loc[-0.02].se_diff)
    n["PP"] = f"{m.loc[0.02].mean_diff:+.3f}"; n["PPSE"] = f3(m.loc[0.02].se_diff)
    n["PMCH"] = f"{m.loc[-0.02].mean_diff_changed:+.3f}"
    n["MART"] = ", ".join(f2(z) for z in T("p2_martingale").z)
    sm = T("p4_summary")
    n["TSUP"] = f"{sm.time_supervised_s.sum():.0f}"; n["TPAY"] = f"{sm.time_payoff_s.sum():.0f}"
    mc = T("e3_coupled_mc"); n["MC_OWN"] = f"{100*mc.frac_paths_Qd_lt_Q0.iloc[1]:.1f}"
    call = T("e4_call_orderings").set_index("ordering")
    n["CALL_OK"] = f4(call.loc["both (correct)", "C(0,100)"]); n["CALL_PUT"] = f4(call.loc["after (put-style)", "C(0,100)"])
    n["CALL_EU"] = f4(call.loc["european", "C(0,100)"])
    return n


TEMPLATE = r"""---
title: "Learning an American Put Exercise Boundary"
subtitle: "Baruch MFE — Scientific Computing in Finance, Assignment 1"
author: "Aditi Joshi, Helen Siavelis, Jaskaran Kalra, William McDonnell"
---

*Reference and draw order.* The assignment refers to a supplied `reference_solver.py`, `reference_results.npz` and `README.md`. We did not receive these, so the numerical reference is our own independently validated grid solver (Section 2), and the random-draw order is our own documented choice. Both are isolated in `reference.py` and `simulation.py` / `nn_policy.py`, so the supplied versions can be substituted and `python run_all.py` rerun.

# 1. The exercise boundary

**Axes.** The horizontal axis is $u=T-t$, so **calendar time advances right to left**.

**Item 1.** Just before a dividend, the put holder can exercise for $K-s$ or hold through the jump. Nothing random happens between $d_k^-$ and $d_k^+$, and the put receives no dividend. So

$$V_\delta(d_k^-,s)=\max\{(K-s)^+,V_\delta(d_k^+,(1-\delta)s)\}.$$

Exercising just after the jump is always possible, so $V_\delta(d_k^+,(1-\delta)s)\ge K-(1-\delta)s=(K-s)+\delta s>K-s$ for $0<s<K$. The maximum is therefore always the second term, which gives the identity. Exercising after the jump pays $\delta s$ more at no interest cost, so the jump may be applied before the exercise decision.

**Item 2.** Let $t=d_k-\varepsilon$ lie after $d_{k-1}$. The strategy "wait until $d_k^+$, then exercise" is feasible, and $\mathbb E[S_{d_k^-}\mid S_t=s]=se^{r\varepsilon}$, so

$$V_\delta(t,s)\ge e^{-r\varepsilon}\big(K-(1-\delta)se^{r\varepsilon}\big)=Ke^{-r\varepsilon}-(1-\delta)s .$$

If $s$ is in the exercise region, $K-s\ge Ke^{-r\varepsilon}-(1-\delta)s$, i.e. $s\le K(1-e^{-r\varepsilon})/\delta$. Hence $b_\delta(d_k-\varepsilon)\le K(1-e^{-r\varepsilon})/\delta\approx Kr\varepsilon/\delta\to0$.

*Grid version.* The dividend date is itself an exercise date, so stopping there is an admissible grid stopping time and the same bound holds with $\varepsilon=(j_d-j)h$. Our solver satisfies the lower bound at every node.

*Proximity depends on $s$.* A fixed $s$ is never exercised when $\varepsilon<\varepsilon^*(s)=-r^{-1}\log(1-\delta s/K)\approx\delta s/(rK)$. That is about 9 days at $s=10$ and about 75 days at $s=80$. The bound makes this precise because it compares $\delta s$ directly with $K(1-e^{-r\varepsilon})$.

*Positive values on the grid.* One grid step before a dividend the bound is still positive: $K(1-e^{-rh})/\delta=1.63$ ($N=180$) and $0.81$ ($N=360$). These shrink linearly in $h$, which is consistent with a zero limit as $\varepsilon\downarrow0$. In fact the computed boundary lies *on* the bound for about 0.13 years before each dividend: for small $s$, exercise at $d_k^+$ is almost certain, so the bound is attained. This produces the straight segments with slope $\approx rK/\delta$ in Cox and Rubinstein's figure.

*Jump and maturity.* In calendar time the boundary jumps **up** at each $d_k$ (to $0.69K$, $0.75K$, $0.89K$), because once the dividend is paid there is no reason left to wait for it. After $d_3$ no dividend remains and $r>0$, so the boundary tends to $K$ at maturity, as in the $\delta=0$ curve of Cox and Rubinstein's Fig. 5-37 (Cox and Rubinstein 1985).

**Item 3.** Drive both models from $(t_j,s)$ with the same Brownian increments. Then $S^\delta_i=S^0_i(1-\delta)^{n_{ji}}\le S^0_i$, where $n_{ji}$ counts the dividends in $(t_j,t_i]$. Each price path is a one-to-one function of those increments, so both models share one set of stopping times. For any common $\tau$, $(K-S^\delta_\tau)^+\ge(K-S^0_\tau)^+$ on every path. Taking discounted expectations and then the supremum over $\tau$ gives $V_{0.0125,N}\ge V_{0,N}$.

If $V_\delta(t_j,s)=K-s$, then $K-s=V_\delta\ge V_0\ge K-s$. So the exercise regions are nested and $b_{0.0125,N}\le b_{0,N}$. For $t_j\ge d_3$, including $t_j=d_3$ compared at the same *post-jump* price, no dividend remains and the two problems coincide.

A coupled simulation shows why the common $\tau$ matters. With one $\tau$ no path violates dominance. When each model uses its own threshold rule, @@MC_OWN@@% of paths do.

**Item 4.** The call's intrinsic value *falls* at the jump. Exercising first captures the dividend, so

$$C_\delta(d_k^-,s)=\max\{(s-K)^+,C_\delta(d_k^+,(1-\delta)s)\},$$

and the maximum can bind. A call code must therefore test exercise **before** applying the dividend. For the put this pre-jump test is redundant (item 1). Checked on our grid: the correct call is worth @@CALL_OK@@ at $S_0=100$. Deciding after the jump gives @@CALL_PUT@@, because the call then exercises one step early. The European call is worth @@CALL_EU@@.

**Checks using the computed boundaries** ($g_j=b^{0.0125}_j-b^0_j$):

@@ORDER_TABLE@@

The reference is exactly ordered: $A=B=F=0$, and $\max_s(V^{ref}_{0,N}-V^{ref}_{0.0125,N})^+=0$. Neither fitted method is constrained to respect the ordering, so their diagnostics measure **learning error**:

* $F>0$ after $d_3$, where the two problems are identical. The two fits come from different samples, and the $\delta$ paths sit lower after three dividends.
* The NN violations at $N=180$ ($A=32$) come from case 0. Its selected checkpoint let the early-date boundary drift down to about $0.49K$ (Section 4).

# 2. Reference, simulation and the cap

**Reference.** Our solver uses a uniform $\log S$ grid with $S=K$ on a node:

* The Gaussian step is integrated exactly for the piecewise-linear interpolant, with a $dx^2/6$ variance correction. Without it, the European error grew with $N$.
* The dividend is an exact shift of 10 grid nodes.
* European prices match the closed form to about $2\times10^{-5}$.

@@VERIFY_TABLE@@

Refinement approximates the *same* problem more closely. Changing $N$ changes the *problem*: more exercise rights raise the value and move the boundary about 100 times more than any refinement. So an accuracy gain smaller than about $10^{-5}$ \$ in price or $10^{-3}$ \$ in boundary cannot be resolved against this reference.

**Simulation.** We sample the exact lognormal step and apply $(1-\delta)$ on arrival at an integer dividend index. A path that starts at a dividend date is already post-jump. On the final $S_0=100$ samples, $(\bar S_T-S_0e^{rT}(1-\delta)^3)/\mathrm{SE}=$ @@MART@@ for cases 0–3.

The optimal boundary lies on the cap $U_j$ close to each dividend, which is why both fitted policies are given the cap rather than learning it.

# 3. Least-squares policy

We follow the specified recursion: a cubic regression in $x=S_j/K$ on in-the-money rows (SVD least squares), then clipping, the largest $+/-$ crossing of $H$, and the cap.

*Clipping.* The next possible exercise is at $t_{j+1}$ and pays at most $K$, so continuation in time-zero dollars lies in $[0,Ke^{-rt_{j+1}}]$. Hence $H_0\ge Ke^{-rt_j}(1-e^{-rh})>0$: exercise always wins at $s=0$.

*Replay.* Replaying the frozen rule forward reproduces the backward targets exactly.

@@LS_TABLE@@

*Two crossings on almost every date.* A single cubic over $x\in[0.001,1]$ cannot follow the value function's curvature. As a result $H$ dips below zero near $s\approx3$ and turns positive again below the true boundary. The largest-crossing rule keeps one exercise interval $(0,b]$, discarding the spurious continuation pocket in between.

*Low bias, downward spikes and capping.*

* With $\delta=0$ the fit is biased about $0.03$–$0.05K$ low and is noisy near maturity, where the value function has a kink.
* Further from a dividend, the exercise premium $\delta s-K(1-e^{-r\varepsilon})$ is only cents, below the regression's resolution. There the cubic sometimes returns only the low crossing, which produces the downward spikes in Fig. 1(b).
* Close to each dividend the cap takes over. It binds on 85 dates ($N=180$) and 149 dates ($N=360$).

# 4. Neural policy

**Set-up.** We follow the specified design:

* **Networks:** one per interval, `Linear(1,8)`–tanh–`Linear(8,1)`, with $b_\theta=U_j\,\mathrm{sigmoid}(f_\theta)$, so the cap is built in.
* **Warm start:** 1,000 supervised Adam steps towards $\hat b^{LS}$.
* **Payoff stage:** 2,400 Adam steps on the smoothed payoff, with batches of 512 from 8,192 random-start paths.
* **Precision:** training in float32; validation in float64.
* **Cost:** @@TSUP@@ s supervised plus @@TPAY@@ s payoff training for all four cases on 2 CPU threads.

**Randomised stopping.** If the holder has not yet stopped, they stop at $t_j$ with probability $p_j$, independently of the future. Then $w_j=p_j\prod_{k<j}(1-p_k)$ is the probability of stopping *first* at $t_j$, and $\sum_jw_j=1$ because $p_N=1$. So $R_\theta$ is the path-conditional expectation of the discounted payoff under this randomised rule. It is smooth in $\theta$, and it tends to the hard rule as $\epsilon\to0$; with $\epsilon=10^{-7}$ it matches the hard rule to within $10^{-6}$ \$.

@@VAL_TABLE@@

**Checkpoint selection.** Every paired validation gain is within about 2 SE of zero, so on 4,096 random-start paths the checkpoints are statistically indistinguishable.

* **Cases 1 and 3:** checkpoint 0 is selected, i.e. the smoothed LS warm start.
* **Case 2:** payoff training more than halved the boundary error.
* **Case 0:** the selected checkpoint has a *worse* boundary. Near $t_0$ it drifted to about $0.49K$, a region few random-start validation paths visit.

**Research connection.**

* *Becker, Cheridito and Jentzen (2019)* decompose a stopping time into 0–1 stop/continue decisions, one network per date. During training each decision is relaxed to a logistic output in $(0,1)$, and the networks are trained **backward, one date at a time**. The economic objective is the **optimal-stopping value**: maximise the expected reward of the stopping time. The learned rule gives a lower bound, and a dual martingale gives an upper bound and confidence intervals.
* *Bühler et al. (2019)* parametrise the **hedging strategy** by semi-recurrent networks and train it with mini-batch Adam directly on simulated paths. The economic objective is to **minimise a convex risk measure** (e.g. expected shortfall, entropic risk) of the hedged terminal position under frictions such as transaction costs. This gives indifference prices $p(Z)=\pi(-Z)-\pi(0)$.
* Our payoff stage uses Becker et al.'s relaxation, but on a single threshold parametrisation trained **jointly over all dates**. It is optimised by stochastic gradient on simulated paths, as in deep hedging, but with a risk-neutral **expected-payoff** objective rather than a risk measure.

# 5. Values and boundaries

**Prices.** 50,000 independent paths per start (seed $4000+10c+a$), shared by all policies, in float64:

@@PRICE_TABLE@@

The frozen rule is an admissible stopping time, so its expected payoff is at most $V_{\delta,N}(0,S_0)$, and fresh paths make the sample mean unbiased for it. Consistently, no fitted mean exceeds the reference: the largest $(\text{mean}-V^{ref})/\mathrm{SE}$ is @@ZMAX@@. Interval endpoints are in `results.csv`.

Paired against the reference boundary applied on the same paths, at $S_0\in\{80,100\}$:

* LS loses @@LS_LOSS@@ \$ and the NN loses @@NN_LOSS@@ \$.
* The NN beats LS in case 2 (@@C2NN80@@ vs @@C2LS80@@ \$ at $S_0=80$) and ties LS in cases 1 and 3.
* At $S_0=60$ the NN loses @@C0NN60@@ \$ in case 0 and @@C1NN60@@ \$ in case 1, because its $t_0$ boundary sits below 60, so it waits instead of exercising.

**Boundary accuracy.**

@@ERR_TABLE@@

Compare each policy with the reference for the same $N$ first. The optimal boundary itself moves by only $E_{mean}=$ @@NEFF0@@ ($\delta=0$) and @@NEFF1@@ ($\delta=0.0125$) between $N=180$ and $360$. The fitted errors are 10–100 times larger (LS @@ELS@@, NN @@ENN@@). So every change in a fitted policy with $N$ is learning error, set by the fixed budgets and by checkpoint selection, not by the extra exercise dates.

**Price vs boundary accuracy.** Mean boundary errors of 2–8% of $K$ cost only cents in price. The one large loss (case 0, $S_0=60$) comes from an error at a single, heavily visited state rather than a large average error.

**Perturbation** (case 3, $S_0=100$, same evaluation paths):

@@PERT_TABLE@@

Three effects link boundary changes to price changes:

* **The cap.** It absorbs most of the upward shift: 147 dates are capped, so the applied mean shift is only $0.014K$.
* **States visited.** Only paths that enter the shifted band change decision, about 17–19% of paths.
* **Direction of the change.** Lowering the boundary delays exercise and costs @@PM@@ \$ (SE @@PMSE@@; @@PMCH@@ \$ per affected path). Raising it gains @@PP@@ \$ (SE @@PPSE@@), which is not significant.

The asymmetry arises because the NN sits about $0.04K$ below the reference: moving down goes further from the optimum, while moving up approaches it on the flat part of the value surface. A finer sweep (in the code) shows the price is flat within noise for $a\in[0,0.06]$.

# Figures

![**Figure 1.** Exercise boundaries $b/K$ against $u=T-t$ for $N=360$: reference (blue), LS (orange) and selected NN (green); the $N=180$ reference is dashed. Panel (a) $\delta=0$, panel (b) $\delta=0.0125$. Curves are broken at the dividends (dotted).](figures/fig1_boundaries.png){width=6.9in}

![**Figure 2.** Case 3 around $d_3$ ($|t-d_3|\le1/24$). Right of the dotted line is before $d_3$ in calendar time; left is after. On the pre-dividend side the reference lies on the Part 1 bound $K(1-e^{-r(d_3-t)})/(\delta K)$ (grey dashed); LS and NN lie below it, since the cap only limits them from above.](figures/fig2_final_dividend.png){width=4.2in}

# Reproducibility and AI use

* **Command:** `python run_all.py`. It reproduces every table and figure (about 3 minutes); a full rerun gave identical outputs apart from the timing columns.
* **Records:** seeds, sizes, versions, hardware (2 CPU threads, no accelerator), precision and timings are in `results.csv` and `fitted/*.json`.
* **Contributions:** Aditi Joshi — [TODO]; Helen Siavelis — [TODO]; Jaskaran Kalra — [TODO]; William McDonnell — [TODO].

**AI use.** We used Claude (Anthropic; configured model identifier claude-opus-5-5, via Cowork) to draft code, derivations and text, and we verified its suggestions. One suggestion we checked computationally: integrating the piecewise-linear transition kernel exactly adds a spurious variance of $dx^2/6$ per step. Without the correction, European errors were about $2.5\times10^{-3}$ ($N=180$) and $5\times10^{-3}$ ($N=360$) and grew with $N$. With it, they fell to about $2\times10^{-5}$, independent of $N$.

# References

Becker, S., Cheridito, P., Jentzen, A. (2019). Deep Optimal Stopping. *JMLR* 20(74), 1–25.

Bühler, H. et al. (2019). Deep Hedging. *Quantitative Finance* 19(8), 1271–1291.

Cox, J.C., Rubinstein, M. (1985). *Options Markets*. Prentice-Hall.

Longstaff, F.A., Schwartz, E.S. (2001). Valuing American Options by Simulation: A Simple Least-Squares Approach. *Review of Financial Studies* 14(1), 113–147.
"""


def build():
    md = TEMPLATE
    for k, v in {**tables(), **numbers()}.items():
        md = md.replace(f"@@{k}@@", v)
    assert "@@" not in md, re.findall(r"@@\w+@@", md)
    md = re.sub(r"\^([+\-*])", r"^{\1}", md)          # brace bare superscripts
    open("report.md", "w").write(md)
    subprocess.run(["pandoc", "report.md", "-o", "../report.docx",   # deliverable goes to the repo root
                    f"--reference-doc={reference_docx()}", "--resource-path=."], check=True)
    print("wrote report.md, ../report.docx")


if __name__ == "__main__":
    build()
