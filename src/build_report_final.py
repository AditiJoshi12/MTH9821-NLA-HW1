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
    v = T("p2_supplied_verify"); x = T("p2_own_vs_supplied"); nch = T("p2_N_change")
    out["VERIFY_TABLE"] = "\n".join([
        "| Comparison (max over the four cases) | Price change at $S_0\\in\\{60,80,100\\}$ (\\$) | Boundary change (\\$) |", "|---|---|---|",
        f"| Spatial: $\\Delta S$ 0.10 → 0.05 (16 substeps) | {sci(v.spatial_dV_max.max())} | {sci(v.spatial_db_max.max())} |",
        f"| Time: 16 → 32 substeps ($\\Delta S=0.05$) | {sci(v.temporal_dV_max.max())} | {sci(v.temporal_db_max.max())} |",
        f"| Saved arrays vs recomputed | {sci(v.saved_price_max_diff.max())} | {sci(v.saved_boundary_max_diff.max())} |",
        f"| Our independent log-grid solver vs saved arrays | {sci(x.dV_max.max())} | {sci(x.db_max.max())} |",
        f"| $N$: 180 → 360 (a different problem) | {sci(nch[['dV(80)','dV(100)']].abs().values.max())} | {f3(nch.max_db.max())} |"])

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
    o = T("p1_ordering_checks")
    onn = lambda N, k: o[(o.N == N) & (o.method == "NN")][k].iloc[0]
    n["NNA180"], n["NNA360"] = str(int(onn(180, "A"))), str(int(onn(360, "A")))
    n["NNB"] = f3(max(onn(180, "B"), onn(360, "B")))
    d3 = T("p3_ls_diagnostics")
    n["CAP180"] = str(int(d3[d3.case == 1].capped_count.iloc[0])); n["CAP360"] = str(int(d3[d3.case == 3].capped_count.iloc[0]))
    v4 = T("p4_validation")
    sel = v4[v4.selected]
    n["SEL"] = ", ".join(f"{int(r.checkpoint)}" for r in sel.sort_values("case").itertuples())
    n["MAXZVAL"] = f"{(sel.diff_vs_ckpt0 / sel.se_diff.where(sel.se_diff > 0)).abs().max():.1f}"
    e0 = lambda c: v4[(v4.case == c) & (v4.checkpoint == 0)].E_mean_vs_ref.iloc[0]
    es = lambda c: v4[(v4.case == c) & (v4.selected)].E_mean_vs_ref.iloc[0]
    n["C3E0"], n["C3ES"] = f3(e0(3)), f3(es(3))
    n["C3NN60"] = f3(-g(3, 60.0, "NN - ref-boundary policy").mean_diff)
    n["C3NN60SE"] = f3(g(3, 60.0, "NN - ref-boundary policy").se)
    lsnn = lambda c, s0: g(c, s0, "LS - NN")
    n["C2NNGAIN"] = f3(-lsnn(2, 80.0).mean_diff); n["C2NNGAINSE"] = f3(lsnn(2, 80.0).se)
    n["C0LSGAIN"] = f3(lsnn(0, 80.0).mean_diff); n["C0LSGAINSE"] = f3(lsnn(0, 80.0).se)
    n["C3LSGAIN"] = f3(lsnn(3, 80.0).mean_diff); n["C3LSGAINSE"] = f3(lsnn(3, 80.0).se)
    n["PCAP"] = str(int(m.loc[0.02].cap_binds_dates)); n["PAPPL"] = f3(m.loc[0.02].applied_shift_mean)
    n["PCHM"] = f"{100*m.loc[-0.02].frac_paths_changed:.0f}"; n["PCHP"] = f"{100*m.loc[0.02].frac_paths_changed:.0f}"
    sw = T("p5_perturbation_sweep_supplementary")
    neg = sw[sw.a < 0]
    n["SWNEGMAX"] = f3(neg.mean_diff.max()); n["SWPOS8"] = f2(sw[sw.a == 0.08].mean_diff.iloc[0])
    call = T("e4_call_orderings").set_index("ordering")
    n["CALL_OK"] = f4(call.loc["both (correct)", "C(0,100)"]); n["CALL_PUT"] = f4(call.loc["after (put-style)", "C(0,100)"])
    n["CALL_EU"] = f4(call.loc["european", "C(0,100)"])
    return n


TEMPLATE = r"""---
title: "Learning an American Put Exercise Boundary"
subtitle: "Baruch MFE — Scientific Computing in Finance, Assignment 1"
author: "Aditi Joshi, Helen Siavelis, Jaskaran Kalra, William McDonnell"
---

*Conventions.* All reference values and boundaries are the supplied `reference_results.npz` arrays (preserved unchanged), and every random draw follows the supplied `README.md` conventions. Our own independent solver is used only for the Part 1 illustrations and as a cross-check (Section 2).

# 1. The exercise boundary

**Axes.** The horizontal axis is $u=T-t$, so **calendar time advances right to left**.

**Item 1.** Just before a dividend, the put holder can exercise for $K-s$ or hold through the jump. Nothing random happens between $d_k^-$ and $d_k^+$, and the put receives no dividend. So

$$V_\delta(d_k^-,s)=\max\{(K-s)^+,V_\delta(d_k^+,(1-\delta)s)\}.$$

Exercising just after the jump is always possible, so $V_\delta(d_k^+,(1-\delta)s)\ge K-(1-\delta)s=(K-s)+\delta s>K-s$ for $0<s<K$. The maximum is therefore always the second term, which gives the identity. Exercising after the jump pays $\delta s$ more at no interest cost, so the jump may be applied before the exercise decision.

**Item 2.** Let $t=d_k-\varepsilon$ lie after $d_{k-1}$. The strategy "wait until $d_k^+$, then exercise" is feasible, and $\mathbb E[S_{d_k^-}\mid S_t=s]=se^{r\varepsilon}$, so

$$V_\delta(t,s)\ge e^{-r\varepsilon}\big(K-(1-\delta)se^{r\varepsilon}\big)=Ke^{-r\varepsilon}-(1-\delta)s .$$

If $s$ is in the exercise region, $K-s\ge Ke^{-r\varepsilon}-(1-\delta)s$, i.e. $s\le K(1-e^{-r\varepsilon})/\delta$. Hence $b_\delta(d_k-\varepsilon)\le K(1-e^{-r\varepsilon})/\delta\approx Kr\varepsilon/\delta\to0$.

*Grid version.* The dividend date is itself an exercise date, so stopping there is an admissible grid stopping time and the same bound holds with $\varepsilon=(j_d-j)h$. The reference satisfies the lower bound at every node.

*Proximity depends on $s$.* A fixed $s$ is never exercised when $\varepsilon<\varepsilon^*(s)=-r^{-1}\log(1-\delta s/K)\approx\delta s/(rK)$: about 9 days at $s=10$ and 75 days at $s=80$.

*Positive values on the grid.* One grid step before a dividend the bound is still positive: $K(1-e^{-rh})/\delta=1.63$ ($N=180$) and $0.81$ ($N=360$). These shrink linearly in $h$, which is consistent with a zero limit as $\varepsilon\downarrow0$. In fact the reference boundary lies *on* the bound for about 0.13 years before each dividend: for small $s$, exercise at $d_k^+$ is almost certain, so the bound is attained. This produces the straight segments with slope $\approx rK/\delta$ in Cox and Rubinstein's figure.

*Jump and maturity.* In calendar time the boundary jumps **up** at each $d_k$ (to $0.69K$, $0.75K$, $0.89K$), because once the dividend is paid there is no reason left to wait for it. After $d_3$ no dividend remains and $r>0$, so the boundary tends to $K$ at maturity, as in the $\delta=0$ curve of Cox and Rubinstein's Fig. 5-37 (Cox and Rubinstein 1985).

**Item 3.** Drive both models from $(t_j,s)$ with the same Brownian increments. Then $S^\delta_i=S^0_i(1-\delta)^{n_{ji}}\le S^0_i$, where $n_{ji}$ counts the dividends in $(t_j,t_i]$. Each price path is a one-to-one function of those increments, so both models share one set of stopping times. For any common $\tau$, $(K-S^\delta_\tau)^+\ge(K-S^0_\tau)^+$ on every path. Taking discounted expectations and then the supremum over $\tau$ gives $V_{0.0125,N}\ge V_{0,N}$.

If $V_\delta(t_j,s)=K-s$, then $K-s=V_\delta\ge V_0\ge K-s$. So the exercise regions are nested and $b_{0.0125,N}\le b_{0,N}$. For $t_j\ge d_3$, including $t_j=d_3$ compared at the same *post-jump* price, no dividend remains and the two problems coincide.

In a coupled simulation, one common $\tau$ gives no violations, but model-specific threshold rules violate dominance on @@MC_OWN@@% of paths.

**Item 4.** The call's intrinsic value *falls* at the jump. Exercising first captures the dividend, so

$$C_\delta(d_k^-,s)=\max\{(s-K)^+,C_\delta(d_k^+,(1-\delta)s)\},$$

and the maximum can bind. A call code must therefore test exercise **before** applying the dividend. For the put this pre-jump test is redundant (item 1). Checked on our grid: the correct call is worth @@CALL_OK@@ at $S_0=100$. Deciding after the jump gives @@CALL_PUT@@, because the call then exercises one step early. The European call is worth @@CALL_EU@@.

**Checks using the computed boundaries** ($g_j=b^{0.0125}_j-b^0_j$):

@@ORDER_TABLE@@

The reference is exactly ordered: $A=B=F=0$, and $\max_s(V^{ref}_{0,N}-V^{ref}_{0.0125,N})^+=0$. Neither fitted method is constrained to respect the ordering, so their diagnostics measure **learning error**:

* $F>0$ after $d_3$, where the two problems are identical. The two fits come from different samples, and the $\delta$ paths sit lower after three dividends.
* The NN violates the ordering on @@NNA180@@ dates ($N=180$) and @@NNA360@@ dates ($N=360$), by at most $B=$ @@NNB@@. All violations lie just after $d_1$ and $d_2$, where the $\delta$-network overshoots the post-dividend boundary (by up to $0.08K$, Fig. 1b) and so ends up above the $\delta=0$ network.

# 2. Reference, simulation and the cap

**Reference.** `python reference_solver.py --verify` passed: the saved arrays match a recomputation, and the refinements change little.

@@VERIFY_TABLE@@

The largest boundary changes occur on the last exercise date, where the boundary is steepest. As an independent check, our own solver agrees with the supplied arrays to within the reference's own refinement changes. Our solver uses a different method: an exact Gaussian step on a $\log S$ grid, with a $dx^2/6$ variance correction.

Refinement approximates the *same* problem more closely. Changing $N$ changes the *problem*: more exercise rights raise the value, and the boundary moves over 100 times more than under any refinement. The reference is precise to about $2\times10^{-5}$ \$ in price and $2\times10^{-3}$ \$ in boundary, so smaller claimed accuracy gains cannot be resolved.

**Simulation.** We sample the exact lognormal step, adding $\log(1-\delta)$ in the column that arrives at each integer dividend index (the README arithmetic). A path that starts at a dividend date is already post-jump. On the final $S_0=100$ samples, $(\bar S_T-S_0e^{rT}(1-\delta)^3)/\mathrm{SE}=$ @@MART@@ for cases 0–3.

# 3. Least-squares policy

We follow the specified recursion: a cubic regression in $x=S_j/K$ on in-the-money rows (SVD least squares), then clipping, the largest $+/-$ crossing of $H$, and the cap.

*Clipping.* The next possible exercise is at $t_{j+1}$ and pays at most $K$, so continuation in time-zero dollars lies in $[0,Ke^{-rt_{j+1}}]$. Hence $H_0\ge Ke^{-rt_j}(1-e^{-rh})>0$: exercise always wins at $s=0$.

*Replay.* Replaying the frozen rule forward reproduces the backward targets exactly.

@@LS_TABLE@@

*Two crossings on almost every date.* A single cubic over $x\in[0.001,1]$ cannot follow the value function's curvature. As a result $H$ dips below zero near $s\approx3$ and turns positive again below the true boundary. The largest-crossing rule keeps one exercise interval $(0,b]$, discarding the spurious continuation pocket in between.

*Low bias, downward spikes and capping.*

* With $\delta=0$ the fit is biased about $0.065K$ low on average and is noisy near maturity, where the value function has a kink.
* Further from a dividend, the exercise premium $\delta s-K(1-e^{-r\varepsilon})$ is only cents, below the regression's resolution. There the cubic sometimes returns only the low crossing, which produces the downward spikes in Fig. 1(b).
* Close to each dividend the cap takes over. It binds on @@CAP180@@ dates ($N=180$) and @@CAP360@@ dates ($N=360$).

# 4. Neural policy

**Set-up.** We follow the specified design:

* **Networks:** one per interval, `Linear(1,8)`–tanh–`Linear(8,1)`, with $b_\theta=U_j\,\mathrm{sigmoid}(f_\theta)$, so the cap is built in.
* **Warm start:** 1,000 supervised Adam steps towards $\hat b^{LS}$.
* **Payoff stage:** 2,400 Adam steps on the smoothed payoff, with batches of 512 from 8,192 random-start paths.
* **Precision:** training in float32; validation in float64.
* **Cost:** @@TSUP@@ s supervised plus @@TPAY@@ s payoff training for all four cases, with 2 CPU threads, 1 inter-op thread and deterministic algorithms (README settings).

**Randomised stopping.** If the holder has not yet stopped, they stop at $t_j$ with probability $p_j$, independently of the future. Then $w_j=p_j\prod_{k<j}(1-p_k)$ is the probability of stopping *first* at $t_j$, and $\sum_jw_j=1$ because $p_N=1$. So $R_\theta$ is the path-conditional expectation of the discounted payoff under this randomised rule. It is smooth in $\theta$, and it tends to the hard rule as $\epsilon\to0$; with $\epsilon=10^{-7}$ it matches the hard rule to within $10^{-6}$ \$.

@@VAL_TABLE@@

**Checkpoint selection.** The selected checkpoints are @@SEL@@ for cases 0–3; checkpoint 0 was never selected. Every selected gain over checkpoint 0 is within @@MAXZVAL@@ paired SE, so on 4,096 random-start paths the checkpoints are statistically indistinguishable, and selection is close to picking among equals.

Payoff training changed the boundary error little in cases 0–2. In case 3 it made the boundary *worse* ($E_{mean}$ @@C3E0@@ → @@C3ES@@): it overshoots the reference after $d_1$ and sits below it between $d_2$ and $d_3$. The validation mean barely reacts, because the value is flat near the optimal threshold (Section 5).

**Research connection.**

* *Becker, Cheridito and Jentzen (2019)* learn one stop/continue network per date, relaxed to a logistic probability and trained **backward, one date at a time**. Economic objective: the **optimal-stopping value**, i.e. maximising the expected reward. The learned rule gives a lower bound; a dual martingale gives an upper bound.
* *Bühler et al. (2019)* train semi-recurrent **hedging-strategy** networks with Adam on simulated paths. Economic objective: **minimise a convex risk measure** (e.g. expected shortfall) of hedged P&L under transaction costs, which yields indifference prices.
* Our payoff stage borrows Becker et al.'s relaxation, applied to one threshold trained **jointly over all dates**, and optimises it on simulated paths as in deep hedging, but for **expected payoff** rather than a risk measure.

# 5. Values and boundaries

**Prices.** 50,000 independent paths per start (seed $4000+10c+a$), shared by all policies, in float64:

@@PRICE_TABLE@@

The frozen rule is an admissible stopping time, so its expected payoff is at most $V_{\delta,N}(0,S_0)$, and fresh paths make the sample mean unbiased for it. Consistently, no fitted mean exceeds the reference: the largest $(\text{mean}-V^{ref})/\mathrm{SE}$ is @@ZMAX@@. Interval endpoints are in `results.csv`.

Paired against the reference boundary applied on the same paths, at $S_0\in\{80,100\}$:

* LS loses @@LS_LOSS@@ \$ and the NN loses @@NN_LOSS@@ \$.
* At $S_0=80$, NN vs LS:
  * the NN beats LS in case 2 by @@C2NNGAIN@@ \$ (SE @@C2NNGAINSE@@);
  * LS beats the NN in case 0 by @@C0LSGAIN@@ \$ (SE @@C0LSGAINSE@@) and in case 3 by @@C3LSGAIN@@ \$ (SE @@C3LSGAINSE@@);
  * the two tie in case 1.
* At $S_0=60$ every policy exercises at once except the case-3 NN. Its $t_0$ boundary sits just below 60, so it waits, and loses @@C3NN60@@ \$ (SE @@C3NN60SE@@).

**Boundary accuracy.**

@@ERR_TABLE@@

Compare each policy with the reference for the same $N$ first. The optimal boundary itself moves by only $E_{mean}=$ @@NEFF0@@ ($\delta=0$) and @@NEFF1@@ ($\delta=0.0125$) between $N=180$ and $360$. The fitted errors are 7–90 times larger (LS @@ELS@@, NN @@ENN@@). So a fitted policy's change with $N$ is learning error (fixed budgets, checkpoint selection), not the extra exercise dates.

**Price vs boundary accuracy.** Mean boundary errors of 2–7% of $K$ cost at most about 0.25 \$ in price, and usually a few cents. The two need not rank policies alike: in case 3 the NN has the smaller maximum error but the larger price loss, because what matters is the error where paths decide.

**Perturbation** (case 3, $S_0=100$, same evaluation paths):

@@PERT_TABLE@@

Three effects link boundary changes to price changes:

* **The cap.** It absorbs much of the upward shift: @@PCAP@@ dates are capped, so the applied mean shift is only @@PAPPL@@$K$.
* **States visited.** Only paths that enter the shifted band change decision: @@PCHM@@% of paths for $a=-0.02$ and @@PCHP@@% for $a=+0.02$.
* **Direction of the change.**
  * Lowering the boundary delays exercise and *gains* @@PM@@ \$ (SE @@PMSE@@; @@PMCH@@ \$ per affected path).
  * Raising it makes those paths exercise earlier and changes the price by @@PP@@ \$ (SE @@PPSE@@).

The sign pattern follows where the NN is wrong along the paths. It lies $0.031K$ below the reference on average, but overshoots by up to $0.08K$ just after $d_1$. The gain from lowering it is consistent with those early-exercise errors dominating at $S_0=100$. Our finer sweep (in the code) stays within about @@SWNEGMAX@@ \$ of zero for $a\in[-0.08,0]$ and falls steadily for $a>0$ (@@SWPOS8@@ \$ at $a=0.08$). Exercising too early is costly; waiting a little longer is almost free.

# Figures

![**Figure 1.** Exercise boundaries $b/K$ against $u=T-t$ for $N=360$: reference (blue), LS (orange) and selected NN (green); the $N=180$ reference is dashed. Panel (a) $\delta=0$, panel (b) $\delta=0.0125$. Curves are broken at the dividends (dotted).](figures/fig1_boundaries.png){width=5.8in}

![**Figure 2.** Case 3 around $d_3$ ($|t-d_3|\le1/24$). Right of the dotted line is before $d_3$ in calendar time; left is after. On the pre-dividend side the reference lies on the Part 1 bound $K(1-e^{-r(d_3-t)})/(\delta K)$ (grey dashed); LS and NN lie below it, since the cap only limits them from above.](figures/fig2_final_dividend.png){width=3.2in}

# Reproducibility and AI use

* **Command:** `python run_all.py`. Reproduces every table and figure in about 3 minutes; reruns are identical apart from timings.
* **Records:** seeds, sizes, versions, hardware (2 CPU threads, no accelerator), precision and timings are in `results.csv` and `fitted/*.json`. Run on Python 3.11 (README: 3.12); `--verify` still passed.
* **Contributions:** Aditi Joshi — [TODO]; Helen Siavelis — [TODO]; Jaskaran Kalra — [TODO]; William McDonnell — [TODO].

**AI use.** We used Claude (Anthropic; model identifier claude-opus-5-5, via Cowork) to draft code, derivations and text, and verified its suggestions. One we checked computationally: the piecewise-linear kernel of our cross-check solver adds a spurious variance $dx^2/6$ per step. Without correcting it, European errors grew with $N$ (about $2.5\times10^{-3}$ at $N=180$, $5\times10^{-3}$ at $N=360$); with it they fell to about $2\times10^{-5}$.

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
