"""
plotting_p23.py -- Figures for Parts 2-3 (and the draft of report
Figures 1 and 2; the NN curve is added once Part 4 exists).

Axis convention: u = T - t horizontal (calendar time runs right -> left),
b/K vertical.  Colours: blue = reference, orange = LS, grey dashed =
N = 180 reference / theoretical cap.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as cfg
import simulation as sim
import lsm
from reference import load_reference
from plotting import BLUE, ORANGE, AQUA, GREY, TEXT2, _plot_broken, _div_markers


def fig_ls_vs_ref(ls, path, nn=None):
    """Draft Figure 1: panel (a) delta=0, (b) delta=0.0125; N=360 ref and
    LS, N=180 reference dashed; curves broken at dividend dates."""
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), sharey=True)
    for ax, (c360, c180), title in zip(axes, ((2, 0), (3, 1)),
                                       ("(a) delta = 0", "(b) delta = 0.0125")):
        N, d = sim.CASES[c360]
        tg = cfg.TimeGrid(N)
        _plot_broken(ax, tg, load_reference(N, d).boundary / cfg.K, color=BLUE,
                     label="reference, N=360")
        _plot_broken(ax, tg, ls[c360].boundary / cfg.K, color=ORANGE, lw=1.2,
                     label="regression (LS), N=360")
        if nn is not None:
            _plot_broken(ax, tg, nn[c360]["boundary"] / cfg.K, color=AQUA, lw=1.2,
                         label="neural (selected), N=360")
        tg180 = cfg.TimeGrid(180)
        _plot_broken(ax, tg180, load_reference(180, d).boundary / cfg.K, color=GREY,
                     ls=(0, (3, 2)), lw=1.0, label="reference, N=180")
        if d > 0:
            _div_markers(ax)
        ax.set_xlim(0, cfg.T)
        ax.set_title(title, loc="left", color=TEXT2)
        ax.set_xlabel("time remaining u = T - t  (calendar time runs right -> left)")
    axes[0].set_ylabel("exercise boundary b / K")
    axes[0].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_final_dividend(ls, path, c=3, nn=None):
    """Draft Figure 2: case 3 around d3, |t - d3| <= 1/24, with the Part 1
    bound K(1-e^{-r(d3-t)})/delta / K on the pre-dividend side."""
    N, d = sim.CASES[c]
    tg = cfg.TimeGrid(N)
    u = tg.u()
    ud = cfg.DIV_MARKERS_U[-1]
    win = np.abs(u - ud) <= 1 / 24 + 1e-12
    jd = tg.j_star
    pre = win & (np.arange(N + 1) < jd)     # calendar time BEFORE d3 (u > ud)
    post = win & (np.arange(N + 1) >= jd)   # at / after d3 (post-jump)
    ref = load_reference(N, d).boundary / cfg.K
    b = ls[c].boundary / cfg.K

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for sel in (pre, post):
        ax.plot(u[sel], ref[sel], color=BLUE, label="reference" if sel is pre else None)
        ax.plot(u[sel], b[sel], color=ORANGE, lw=1.2, label="regression (LS)" if sel is pre else None)
        if nn is not None:
            ax.plot(u[sel], nn[c]["boundary"][sel] / cfg.K, color=AQUA, lw=1.2,
                    label="neural (selected)" if sel is pre else None)
    eps = np.linspace(1e-6, 1 / 24, 200)
    ax.plot(ud + eps, np.minimum(1, (1 - np.exp(-cfg.R * eps)) / d), color=GREY,
            ls=(0, (2, 2)), lw=1.0, label="Part 1 bound K(1-e^{-r(d3-t)})/(delta K)")
    ax.axvline(ud, color=GREY, lw=0.8, ls=":")
    ax.text(ud + 0.002, 0.95, "before d3\n(earlier in calendar time)", fontsize=7,
            color=TEXT2, va="top")
    ax.text(ud - 0.002, 0.05, "after d3\n(later in calendar time)", fontsize=7,
            color=TEXT2, ha="right")
    ax.set_xlabel("u = T - t"); ax.set_ylabel("b / K")
    ax.set_title("Case 3 (N=360, delta=0.0125) near the final dividend", loc="left", color=TEXT2)
    ax.legend(fontsize=7, loc="center right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_H_example(ls, path, c=0, j=90, n_scatter=3000):
    """Why the LARGEST crossing is selected: at one date, the clipped cubic
    continuation vs the exercise value, with the training targets."""
    N, d = sim.CASES[c]
    tg, S = sim.training_paths_LS(c)
    r = ls[c]
    disc = np.exp(-cfg.R * tg.t)
    c_raw = lsm._design(lsm.X_GRID) @ r.coef[j]
    cc = np.minimum(cfg.K * disc[j + 1], np.maximum(0, c_raw))
    ex = disc[j] * (cfg.K - lsm.S_GRID)
    H = ex - cc
    idx = np.flatnonzero((H[:-1] >= 0) & (H[1:] < 0)) + 1

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.4))
    a1.plot(lsm.S_GRID, ex, color=GREY, lw=1.0, label="exercise e^{-rt_j}(K - s)")
    a1.plot(lsm.S_GRID, cc, color=ORANGE, label="clipped cubic c_j(s)")
    a1.set_xlabel("s"); a1.set_ylabel("time-zero dollars")
    a1.set_title(f"Case {c}, date j = {j}", loc="left", color=TEXT2)
    a1.legend(fontsize=7)
    a2.plot(lsm.S_GRID, H, color=BLUE, label="H(s) = exercise - continuation")
    a2.axhline(0, color=GREY, lw=0.8)
    for l in idx:
        a2.axvline(lsm.S_GRID[l], color=ORANGE, lw=0.8, ls=":")
    a2.axvline(load_reference(N, d).boundary[j], color=AQUA, lw=1.0, ls="--",
               label="reference boundary")
    a2.set_ylim(-6, 6)
    a2.set_xlabel("s")
    a2.set_title(f"+/- crossings at s = {', '.join(f'{lsm.S_GRID[l]:.1f}' for l in idx)}"
                 f"  (largest selected)", loc="left", color=TEXT2, fontsize=8)
    a2.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_nn_training(nn, path):
    """Part 4 training curves: supervised loss (log scale) and the payoff
    objective (rolling mean of the batch mean R, dollars)."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.3))
    cols = (BLUE, ORANGE, AQUA, GREY)
    for c, col in zip(range(4), cols):
        N, d = sim.CASES[c]
        lab = f"case {c} (N={N}, delta={d})"
        a1.plot(nn[c]["sup_hist"], color=col, lw=1.0, label=lab)
        r = nn[c]["pay_hist"]
        k = 50
        a2.plot(np.arange(k, len(r) + 1), np.convolve(r, np.ones(k) / k, "valid"),
                color=col, lw=1.0, label=lab)
    a1.set_yscale("log"); a1.set_xlabel("supervised Adam step"); a1.set_ylabel("mean ((b - b_LS)/K)^2")
    a1.set_title("Supervised initialisation", loc="left", color=TEXT2)
    a2.axvline(400, color=GREY, lw=0.8, ls=":")
    a2.text(410, a2.get_ylim()[0], " eps 0.01 -> 0.002", fontsize=7, color=TEXT2, va="bottom")
    a2.set_xlabel("payoff update"); a2.set_ylabel("batch mean R (50-update rolling), $")
    a2.set_title("Payoff optimisation", loc="left", color=TEXT2)
    a1.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_nn_validation(nn, path):
    """Validation: each checkpoint's mean payoff minus checkpoint 0's, on
    the SAME validation paths, with 95% paired intervals."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    cols = (BLUE, ORANGE, AQUA, GREY)
    for i, (c, col) in enumerate(zip(range(4), cols)):
        ks = sorted(nn[c]["val_diff_vs0"])
        m = np.array([nn[c]["val_diff_vs0"][k][0] for k in ks])
        se = np.array([nn[c]["val_diff_vs0"][k][1] for k in ks])
        x = np.array(ks) + (i - 1.5) * 25
        ax.errorbar(x, m, yerr=1.96 * se, fmt="o", ms=4, color=col, capsize=2, lw=1,
                    label=f"case {c}" + ("  (selected: ckpt %d)" % nn[c]["selected"]))
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_xticks(sorted(nn[0]["val_diff_vs0"]))
    ax.set_xlabel("checkpoint (payoff updates)"); ax.set_ylabel("validation mean - ckpt 0 ($)")
    ax.set_title("Validation (hard rule, paired on 4,096 paths)", loc="left", color=TEXT2)
    ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_perturbation(sweep, required, gap, path):
    """Part 5.3: paired price change vs a uniform boundary shift a (case 3,
    S0 = 100).  Dots: the assignment's shifts; line + band: our finer sweep
    (supplementary).  Dotted line: the NN's mean distance below the reference."""
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    a = sweep["a"].values
    m, se = sweep["mean_diff"].values, sweep["se_diff"].values
    ax.fill_between(a, m - 1.96 * se, m + 1.96 * se, color=AQUA, alpha=0.18, lw=0)
    ax.plot(a, m, color=AQUA, lw=1.4, label="paired mean Q^(a) - Q^(0) (sweep, ours)")
    ax.errorbar(required["a"], required["mean_diff"], yerr=1.96 * required["se_diff"],
                fmt="o", color=NAVY_DOT, ms=5, capsize=3, lw=1, label="assignment shifts a = -0.02, 0, 0.02")
    ax.axhline(0, color=GREY, lw=0.8)
    ax.axvline(gap, color=GREY, lw=0.8, ls=":")
    ax.text(gap, ax.get_ylim()[0], f" mean (b_ref - b_NN)/K = {gap:.3f}", fontsize=7,
            color=TEXT2, va="bottom")
    ax.set_xlabel("boundary shift a (fraction of K), then capped at U_j and floored at 0")
    ax.set_ylabel("price change ($)")
    ax.set_title("Case 3, S0 = 100: price change vs boundary shift", loc="left", color=TEXT2)
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


NAVY_DOT = "#1E2761"
