"""
experiments_part1.py -- Numerical experiments that support the four
Part 1 answers.  Each experiment is one function returning plain data
(dicts / pandas DataFrames) so the notebook can print, plot or save it.

    E1  (item 1)  dividend identity and "never exercise the put just
                  before the jump"
    E2  (item 2)  the cap  b(d_k - eps) <= K(1 - e^{-r eps}) / delta,
                  its limit, the s-dependent proximity, the upward jump
                  and the limit at maturity
    E3  (item 3)  dividend ordering  V_0.0125 >= V_0 ,  b_0.0125 <= b_0 ,
                  equality after d_3 ; diagnostics A, B, F for "ref"
                  (our solver) + a coupled Monte Carlo illustration of
                  the proof
    E4  (item 4)  call exercise timing: which ordering a call needs

All numbers come from OUR solver (grid_solver.py), not from the supplied
reference_solver.py, which we did not have when these were run.
"""

import numpy as np
import pandas as pd

import config as cfg
from grid_solver import solve, LogGrid

SPOTS = (60.0, 80.0, 100.0)
DELTA = 0.0125


# ---------------------------------------------------------------------------
# Cache: one solve per (N, delta, kind, ordering) -- each takes < 0.2 s
# ---------------------------------------------------------------------------
_CACHE = {}


def get(N, delta, kind="put", ordering="after", american=True):
    key = (N, delta, kind, ordering, american)
    if key not in _CACHE:
        _CACHE[key] = solve(N, delta, kind=kind, ordering=ordering,
                            american=american)
    return _CACHE[key]


# ===========================================================================
# E1 -- item 1
# ===========================================================================
def e1_dividend_identity(N=180):
    """For each dividend index j_d, compare the pre-jump put value
    W(s) = V(d^+, (1-delta)s) with the two exercise payoffs.

    Claim tested:  W(s) >= K - (1-delta)s = (K - s) + delta*s  > K - s
    for 0 < s < K, i.e. exercising just BEFORE the jump is never optimal:
    it is dominated by exercising just AFTER, which pays delta*s more.

    Returned columns
      min_gap_pre   = min_{0<s<K} [ W(s) - (K - s) ]           (> 0 expected)
      min_excess    = min_{0<s<K} [ W(s) - (K-s) - delta s ]   (>= 0 expected)
      ex_region_pre = number of grid nodes with W(s) <= K - s  (0 expected)
    """
    res = get(N, DELTA)
    S = res.S
    # Only nodes whose post-jump image (1-delta)s is still ON the grid:
    # for the lowest `shift` nodes the image falls below the truncated
    # domain and W is an edge extrapolation (a grid artefact, not model).
    shift = LogGrid().shift_for(DELTA)
    below = (S < cfg.K) & (np.arange(S.size) >= shift)
    rows = []
    for k, jd in enumerate(cfg.TimeGrid(N).div_idx, start=1):
        W = res.W_div[jd]
        gap = W[below] - (cfg.K - S[below])
        rows.append(dict(dividend=f"d{k}", j=jd,
                         min_gap_pre=gap.min(),
                         min_excess=(gap - DELTA * S[below]).min(),
                         ex_region_pre=int((gap <= 0).sum())))
    return pd.DataFrame(rows)


def e1_put_orderings(N=180):
    """Three ways to order dividend and exercise for the PUT.

    'after'  (assignment rule) = 'both' exactly, while 'before' (exercise
    only ahead of the jump) is strictly worse.  This is the numerical
    content of 'apply the dividend jump before the exercise decision'.
    """
    rows = []
    base = get(N, DELTA, ordering="after")
    for ordering in ("after", "both", "before"):
        r = get(N, DELTA, ordering=ordering)
        rows.append(dict(ordering=ordering,
                         **{f"V(0,{int(s)})": r.value_at(s) for s in SPOTS},
                         max_abs_diff_vs_after=np.abs(r.V_plus[0] - base.V_plus[0]).max()))
    return pd.DataFrame(rows)


# ===========================================================================
# E2 -- item 2
# ===========================================================================
def e2_cap_table(N=180, n_before=6):
    """Boundary vs the cap on the last few grid dates before each dividend,
    plus the post-jump boundary AT the dividend date (the upward jump).

    eps = d_k - t_j = (j_d - j) h.  cap = K(1 - e^{-r eps})/delta (not
    truncated at K here, so its linear-in-eps shape is visible).
    """
    tg = cfg.TimeGrid(N)
    res = get(N, DELTA)
    rows = []
    for k, jd in enumerate(tg.div_idx, start=1):
        for j in range(jd - n_before, jd + 2):
            eps = tg.t[jd] - tg.t[j]
            cap = cfg.K * (1 - np.exp(-cfg.R * eps)) / DELTA if eps > 0 else np.nan
            rows.append(dict(dividend=f"d{k}", j=j, steps_to_div=jd - j,
                             eps_years=eps, b=res.boundary[j], cap=cap,
                             b_over_cap=res.boundary[j] / cap if eps > 0 else np.nan,
                             b_over_K=res.boundary[j] / cfg.K))
    return pd.DataFrame(rows)


def e2_cap_tightness(N=180, rel_tol=1e-3):
    """How far before each dividend does the boundary stay ON the cap?

    Finding (see notebook): for small eps the boundary equals the cap to
    ~1e-6.  Reason: for s near the cap (s << post-dividend boundary) the
    put is exercised at d_k^+ with probability ~1, so the continuation
    value IS the 'wait then exercise' value K e^{-r eps} - (1-delta)s and
    the lower bound of item 2 holds with equality.  The boundary leaves
    the cap only once the chance of ending above the post-jump boundary
    is no longer negligible.
    Returns, per dividend, the largest number of steps before d_k for
    which |b/cap - 1| < rel_tol, and the corresponding b/K.
    """
    tg = cfg.TimeGrid(N)
    res = get(N, DELTA)
    U = cfg.dividend_cap(tg, DELTA)
    rows = []
    prev = 0
    for k, jd in enumerate(tg.div_idx, start=1):
        on = 0
        for j in range(jd - 1, prev - 1, -1):
            if U[j] < cfg.K and abs(res.boundary[j] / U[j] - 1) < rel_tol:
                on = jd - j
            else:
                break
        rows.append(dict(dividend=f"d{k}", steps_on_cap=on,
                         eps_years=on * tg.h,
                         b_over_K_at_departure=res.boundary[jd - on] / cfg.K,
                         max_b_over_K_before_div=res.boundary[prev:jd].max() / cfg.K))
        prev = jd
    return pd.DataFrame(rows)


def e2_lower_bound_check(N=180):
    """Check V(t,s) >= K e^{-r eps} - (1-delta)s on every grid date strictly
    between the previous dividend and the next one (all s on the grid).

    This is the 'wait until d_k^+ then exercise' strategy value; a solver
    violating it would be wrong.  Returns the most negative slack.
    """
    tg = cfg.TimeGrid(N)
    res = get(N, DELTA)
    S = res.S
    worst = np.inf
    prev = 0
    for jd in tg.div_idx:
        for j in range(prev, jd):   # d_{k-1} (post-jump) <= t_j < d_k
            eps = tg.t[jd] - tg.t[j]
            lb = cfg.K * np.exp(-cfg.R * eps) - (1 - DELTA) * S
            worst = min(worst, (res.V_plus[j] - lb).min())
        prev = jd
    return worst


def e2_proximity(s_values=(10, 20, 40, 60, 80, 95)):
    """For each fixed s, how close to the dividend must we be for the
    dividend benefit to dominate?  From the bound, s cannot be in the
    exercise region whenever  delta*s > K(1 - e^{-r eps}), i.e.

        eps < eps*(s) = -(1/r) log(1 - delta s / K).

    Small s needs a much smaller eps (eps* ~ delta s /(rK) -> 0 as s -> 0).
    """
    rows = []
    for s in s_values:
        eps_star = -np.log(1 - DELTA * s / cfg.K) / cfg.R
        rows.append(dict(s=s, eps_star_years=eps_star,
                         eps_star_days=eps_star * 365,
                         steps_N180=eps_star / (cfg.T / 180),
                         steps_N360=eps_star / (cfg.T / 360)))
    return pd.DataFrame(rows)


def e2_one_step_cap():
    """Largest boundary compatible with the bound ONE grid step before a
    dividend: K(1 - e^{-rh})/delta.  Positive, shrinks ~ linearly in h,
    and -> 0 as h -> 0 (consistent with the zero limit)."""
    rows = []
    for N in cfg.NS:
        h = cfg.T / N
        res = get(N, DELTA)
        tg = cfg.TimeGrid(N)
        rows.append(dict(N=N, h=h,
                         cap_one_step=cfg.K * (1 - np.exp(-cfg.R * h)) / DELTA,
                         b_one_step=[round(res.boundary[jd - 1], 4) for jd in tg.div_idx]))
    return pd.DataFrame(rows)


def e2_maturity_limit():
    """Boundary on the last grid dates before T (after d_3, both deltas):
    approaches K as t -> T (b_N = K by definition)."""
    rows = []
    for N in cfg.NS:
        for d in cfg.DELTAS:
            b = get(N, d).boundary
            rows.append(dict(N=N, delta=d, **{f"b_N-{i}/K": b[N - i] / cfg.K
                                                for i in (10, 3, 2, 1)}))
    return pd.DataFrame(rows)


# ===========================================================================
# E3 -- item 3
# ===========================================================================
def e3_ordering_diagnostics(tol=1e-8):
    """Assignment's diagnostics with M = ref (our solver) plus value checks.

    g_j = b_j^{0.0125} - b_j^{0}
    A = #{ j < j* : g_j > 1e-8 }         (ordering violations; expect 0)
    B = max_{j < j*} (g_j)^+ / K          (their size;          expect 0)
    F = max_{j* <= j < N} |g_j| / K       (post-d3 discrepancy; expect 0)
    plus  max_s (V_0(0,s) - V_0.0125(0,s))^+  in dollars, and the same over
    ALL dates j (a stronger check than the assignment asks for).
    """
    rows = []
    for N in cfg.NS:
        tg = cfg.TimeGrid(N)
        r0, rd = get(N, 0.0), get(N, DELTA)
        js = tg.j_star
        g = rd.boundary[:N] - r0.boundary[:N]
        A = int((g[:js] > tol).sum())
        B = max(0.0, g[:js].max()) / cfg.K
        F = np.abs(g[js:N]).max() / cfg.K
        dV0 = np.maximum(r0.V_plus[0] - rd.V_plus[0], 0).max()
        dV_all = np.maximum(r0.V_plus - rd.V_plus, 0).max()
        dV_post = np.abs(r0.V_plus[js:] - rd.V_plus[js:]).max()
        rows.append(dict(N=N, j_star=js, A=A, B=B, F=F,
                         max_pos_V0_minus_Vd_t0=dV0,
                         max_pos_V0_minus_Vd_all_j=dV_all,
                         max_abs_V_diff_j_ge_jstar=dV_post))
    return pd.DataFrame(rows)


def e3_coupled_mc(N=180, n_paths=20_000, seed=9001):
    """Coupled Monte Carlo illustration of the proof of item 3.

    Both stock paths start at S = 100 at t_0 and use the SAME normals Z:
        S^0_j     = S_0 exp(sum of GBM increments)
        S^delta_j = S^0_j (1-delta)^{#dividends in (0, t_j]}  <= S^0_j
    (seed 9001 is ours; it is outside the assignment's seed ranges.)

    Rule 1 (valid for the proof): ONE stopping time tau computed from the
    shared information -- here the first j with S^0_j <= b^0_ref(t_j)
    (any rule measurable w.r.t. the shared Brownian path would do).
    Then pathwise (K - S^delta_tau)^+ >= (K - S^0_tau)^+ .

    Rule 2 (NOT the proof's construction): each model applies the same
    threshold 0.8K to ITS OWN price, giving two different stopping times.
    Pathwise dominance can then fail on some paths, which is why the proof
    fixes a common tau first and only then takes the supremum.
    """
    rng = np.random.default_rng(seed)
    tg = cfg.TimeGrid(N)
    h = tg.h
    Z = rng.standard_normal((n_paths, N))
    logret = (cfg.R - 0.5 * cfg.SIGMA ** 2) * h + cfg.SIGMA * np.sqrt(h) * Z
    S0 = 100.0 * np.exp(np.concatenate([np.zeros((n_paths, 1)),
                                        np.cumsum(logret, axis=1)], axis=1))
    n_div = np.cumsum(tg.is_div.astype(int))           # dividends in (0, t_j]
    Sd = S0 * (1 - DELTA) ** n_div                       # same Z, jumps applied
    disc = np.exp(-cfg.R * tg.t)

    def stop_first(S, thresh):
        """first j with S_j <= thresh_j and S_j < K, else N."""
        hit = (S <= thresh[None, :]) & (S < cfg.K)
        hit[:, -1] = True                                # settle at N
        return hit.argmax(axis=1)

    idx = np.arange(n_paths)
    # Rule 1: common tau from the shared information
    tau = stop_first(S0, get(N, 0.0).boundary)
    Q0 = disc[tau] * np.maximum(cfg.K - S0[idx, tau], 0)
    Qd = disc[tau] * np.maximum(cfg.K - Sd[idx, tau], 0)
    # Rule 2: model-specific stopping times from one threshold
    thr = np.full(N + 1, 0.8 * cfg.K)
    t0, td = stop_first(S0, thr), stop_first(Sd, thr)
    Q0b = disc[t0] * np.maximum(cfg.K - S0[idx, t0], 0)
    Qdb = disc[td] * np.maximum(cfg.K - Sd[idx, td], 0)

    se = lambda x: x.std(ddof=1) / np.sqrt(x.size)
    return pd.DataFrame([
        dict(rule="common tau (proof)", mean_Q0=Q0.mean(), mean_Qd=Qd.mean(),
             mean_diff=(Qd - Q0).mean(), se_diff=se(Qd - Q0),
             frac_paths_Qd_lt_Q0=(Qd < Q0 - 1e-12).mean()),
        dict(rule="own tau per model", mean_Q0=Q0b.mean(), mean_Qd=Qdb.mean(),
             mean_diff=(Qdb - Q0b).mean(), se_diff=se(Qdb - Q0b),
             frac_paths_Qd_lt_Q0=(Qdb < Q0b - 1e-12).mean()),
    ])


# ===========================================================================
# E4 -- item 4
# ===========================================================================
def e4_call_orderings(N=180, spots=(80.0, 100.0, 120.0, 140.0)):
    """American (grid-exercise) CALL under three orderings, plus European.

    'both'  : correct -- the holder may exercise just before the jump,
              C(d^-, s) = max{(s-K)^+, C(d^+, (1-delta)s)}.
    'after' : put-style ordering (jump first) -- loses the pre-dividend
              exercise.  The best it can do is exercise at the grid date
              ONE STEP BEFORE the dividend, forgoing interest K(1-e^{-rh})
              -- so it lies between European and the correct value.
    'before': exercise only pre-jump at dividend dates.
    """
    rows = []
    for label, kw in [("european", dict(american=False)),
                      ("after (put-style)", dict(ordering="after")),
                      ("before", dict(ordering="before")),
                      ("both (correct)", dict(ordering="both"))]:
        r = get(N, DELTA, kind="call", **kw)
        rows.append(dict(ordering=label,
                         **{f"C(0,{int(s)})": r.value_at(s) for s in spots}))
    return pd.DataFrame(rows)


def e4_call_pre_div_threshold(N=180):
    """Critical pre-jump price s*_k above which the call is exercised just
    BEFORE dividend k:  smallest grid s with (s-K) >= C(d^+, (1-delta)s).
    Also: is there ANY post-jump or non-dividend-date early exercise?
    """
    tg = cfg.TimeGrid(N)
    r = get(N, DELTA, kind="call", ordering="both")
    S = r.S
    rows = []
    for k, jd in enumerate(tg.div_idx, start=1):
        cont_pre = np.empty_like(S)                     # C(d^+, (1-delta)s)
        shift = LogGrid().shift_for(DELTA)
        cont_pre[shift:] = r.V_plus[jd][:-shift]
        cont_pre[:shift] = r.V_plus[jd][0]
        ex = (S - cfg.K >= cont_pre) & (S > cfg.K)
        s_star = S[ex].min() if ex.any() else np.nan
        rows.append(dict(dividend=f"d{k}", j=jd, s_star_pre_jump=s_star,
                         s_star_over_K=s_star / cfg.K))
    # early exercise anywhere else (post-jump decisions at j < N)?
    other = 0
    for j in range(N):
        other += int((((S - cfg.K) >= r.C[j]) & (S > cfg.K) & (S < 5 * cfg.K)).sum())
    return pd.DataFrame(rows), other
