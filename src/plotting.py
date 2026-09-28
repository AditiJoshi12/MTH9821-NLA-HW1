"""
plotting.py -- Figures for Part 1.  Assignment plotting convention:
horizontal axis u = T - t (time remaining), vertical axis b/K.
Calendar time ADVANCES LEFTWARD (u decreases).  Dividend markers at
u = 13/24, 7/24, 1/24.

Colours: fixed categorical order (blue, orange, aqua) from a validated
palette; the theoretical cap is drawn in neutral grey dashes so it reads
as a reference line, not a data series.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as cfg
from grid_solver import LogGrid
import experiments_part1 as E

BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
TEXT2 = "#52514e"

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": GREY, "axes.labelcolor": TEXT2, "xtick.color": TEXT2,
    "ytick.color": TEXT2, "axes.grid": True, "grid.color": "#e6e5e0",
    "grid.linewidth": 0.6, "lines.linewidth": 1.6, "legend.frameon": False,
})


def _segments(tg):
    """Index ranges between dividends, so curves can be BROKEN at the
    jump (post-jump value at d_k starts a new segment)."""
    cuts = [0] + list(tg.div_idx) + [tg.N]
    return [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]


def _div_markers(ax):
    for u in cfg.DIV_MARKERS_U:
        ax.axvline(u, color=GREY, lw=0.8, ls=":", zorder=0)


def _plot_broken(ax, tg, y, **kw):
    """Plot y_j vs u_j, one line per inter-dividend segment [d_{k-1}, d_k).

    The last segment includes j = N (b_N = K).  At a dividend date the
    point belongs to the segment that STARTS there (post-jump value).
    """
    u = tg.u()
    segs = _segments(tg)
    for i, (a, b) in enumerate(segs):
        stop = b + 1 if i == len(segs) - 1 else b
        ax.plot(u[a:stop], y[a:stop], **kw)
        kw.pop("label", None)


def fig_boundaries(path):
    """Figure P1-1: our reference boundaries, both deltas, N = 180/360."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, d, title in zip(axes, cfg.DELTAS,
                            ("(a) delta = 0", "(b) delta = 0.0125")):
        for N, col, ls in ((360, BLUE, "-"), (180, ORANGE, "--")):
            tg = cfg.TimeGrid(N)
            b = E.get(N, d).boundary / cfg.K
            _plot_broken(ax, tg, b, color=col, ls=ls, label=f"our grid solver, N={N}")
        if d > 0:
            tg = cfg.TimeGrid(360)
            U = np.append(cfg.dividend_cap(tg, d), cfg.K) / cfg.K
            _plot_broken(ax, tg, U, color=GREY, ls=(0, (2, 2)), lw=1.0,
                         label="cap U_j / K (N=360)")
            _div_markers(ax)
        ax.set_title(title, loc="left", color=TEXT2)
        ax.set_xlabel("time remaining u = T - t   (calendar time runs right -> left)")
        ax.set_xlim(0, cfg.T)   # same orientation as Cox-Rubinstein Fig 5-37
    axes[0].set_ylabel("exercise boundary b / K")
    axes[1].legend(loc="lower right", fontsize=8)
    axes[0].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_cap_zoom(path, window=1 / 8):
    """Figure P1-2: boundary vs cap just before each dividend (item 2)."""
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.3), sharey=True)
    for ax, k in zip(axes, range(3)):
        for N, col, mk in ((360, BLUE, "o"), (180, ORANGE, "s")):
            tg = cfg.TimeGrid(N)
            jd = tg.div_idx[k]
            u = tg.u()
            b = E.get(N, E.DELTA).boundary / cfg.K
            sel = (u >= u[jd] - 0.04) & (u <= u[jd] + window)
            pre = sel & (np.arange(N + 1) < jd)            # before d_k
            post = sel & (np.arange(N + 1) >= jd)          # at/after d_k
            ax.plot(u[pre], b[pre], mk, ms=2.5, color=col, label=f"b, N={N}")
            ax.plot(u[post], b[post], mk, ms=2.5, color=col, mfc="none")
        # continuous cap K(1-e^{-r eps})/delta, eps = u - u_d
        ud = cfg.DIV_MARKERS_U[k]
        ee = np.linspace(1e-6, window, 200)
        ax.plot(ud + ee, np.minimum(1, (1 - np.exp(-cfg.R * ee)) / E.DELTA),
                color=GREY, ls=(0, (2, 2)), lw=1.0, label="K(1-e^{-r eps})/(delta K)")
        ax.axvline(ud, color=GREY, lw=0.8, ls=":")
        ax.set_title(f"dividend d{k+1}  (u = {ud:.4f})", loc="left", color=TEXT2)
        ax.set_xlabel("u = T - t")
    axes[0].set_ylabel("b / K")
    axes[0].legend(fontsize=7, loc="upper right")
    fig.suptitle("Filled: before the dividend (right of dotted line).  "
                 "Hollow: at/after it (post-jump).", fontsize=8, color=TEXT2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_proximity(path):
    """Figure P1-3: eps*(s) -- how close to the dividend s must be."""
    s = np.linspace(0.5, 99.5, 400)
    eps = -np.log(1 - E.DELTA * s / cfg.K) / cfg.R
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.plot(s / cfg.K, eps, color=BLUE, label="eps*(s) = -log(1 - delta s/K)/r")
    for N, col in ((180, ORANGE), (360, AQUA)):
        ax.axhline(cfg.T / N, color=col, lw=1.0, ls="--", label=f"one grid step h, N={N}")
    ax.set_xlabel("s / K")
    ax.set_yscale("log")   # log scale so the one-step lines h are visible
    ax.set_ylabel("eps (years before dividend, log scale)")
    ax.set_title("s is NOT exercised whenever eps < eps*(s)", loc="left", color=TEXT2)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_pre_jump(path, N=180):
    """Figure P1-4 (item 1 / item 4): payoffs on both sides of d_3.

    Left: PUT.  W(s) - (K-s) (pre-jump value minus pre-jump payoff) vs
    delta*s (extra payoff from exercising just after).  Always positive.
    Right: CALL.  Pre-jump payoff (s-K)^+ vs C(d^+,(1-delta)s); they
    cross at s*, above which the call must be exercised BEFORE the jump.
    """
    tg = cfg.TimeGrid(N)
    jd = tg.div_idx[-1]
    g = LogGrid()
    S, k = g.S, g.shift_for(E.DELTA)
    idx = np.arange(S.size)

    rp = E.get(N, E.DELTA)
    W = rp.W_div[jd]
    m = (S < cfg.K) & (S > 5) & (idx >= k)

    rc = E.get(N, E.DELTA, kind="call", ordering="both")
    Cpost = np.empty_like(S); Cpost[k:] = rc.V_plus[jd][:-k]; Cpost[:k] = rc.V_plus[jd][0]
    mc = (S > 60) & (S < 160)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.3))
    a1.plot(S[m], W[m] - (cfg.K - S[m]), color=BLUE, label="V(d3-,s) - (K - s)")
    a1.plot(S[m], E.DELTA * S[m], color=GREY, ls=(0, (2, 2)), lw=1.0,
            label="delta s  (= payoff gain from waiting past the jump)")
    a1.set_xlabel("pre-jump price s"); a1.set_ylabel("dollars")
    a1.set_title("Put at d3: never exercise before the jump", loc="left", color=TEXT2)
    a1.legend(fontsize=7)

    a2.plot(S[mc], np.maximum(S[mc] - cfg.K, 0), color=ORANGE, label="(s - K)^+  exercise pre-jump")
    a2.plot(S[mc], Cpost[mc], color=BLUE, label="C(d3+, (1-delta)s)  wait")
    sstar = E.e4_call_pre_div_threshold(N)[0].s_star_pre_jump.iloc[-1]
    a2.axvline(sstar, color=GREY, lw=0.8, ls=":")
    a2.annotate(f"s* = {sstar:.1f}", (sstar, 5), xytext=(4, 0),
                textcoords="offset points", fontsize=8, color=TEXT2)
    a2.set_xlabel("pre-jump price s")
    a2.set_title("Call at d3: exercise before the jump if s >= s*", loc="left", color=TEXT2)
    a2.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def split_panels(path, n=2):
    """Save each of the n side-by-side panels of a saved figure as its own
    PNG (path_panel1.png, ...), for slides that show one panel at a time."""
    from PIL import Image
    im = Image.open(path)
    w, h = im.size
    stem = path[:-4]
    out = []
    for i in range(n):
        p = f"{stem}_panel{i + 1}.png"
        im.crop((i * w // n, 0, (i + 1) * w // n, h)).save(p)
        out.append(p)
    return out
