"""
validate_solver.py -- Checks that our independent solver is trustworthy
before we use it to illustrate Part 1.

Check 1: kernel weights are a probability distribution (sum ~ 1) and
         reproduce the lognormal mean E[S_{j+1}/S_j] = e^{rh}.
Check 2: European put/call (no early exercise) vs closed form, both deltas.
         This tests the kernel, the dividend shift and the boundaries of
         the truncated domain in one go.
Check 3: Spatial refinement (m_per_div = 5, 10, 20) of the Bermudan put
         at S0 = 60, 80, 100 and of the boundary.
"""
import time
import numpy as np
import config as cfg
from grid_solver import solve, LogGrid
from lognormal_kernel import transition_weights
from analytics import bs_price

SPOTS = (60.0, 80.0, 100.0)

def check_kernel():
    g = LogGrid()
    for N in cfg.NS:
        h = cfg.T / N
        w, L = transition_weights(g.dx, h, cfg.R, cfg.SIGMA)
        n = np.arange(-L, L + 1)
        mass = w.sum()
        # mean of exp(Y) under the piecewise-linear representation
        mean_growth = (w * np.exp(n * g.dx)).sum()
        print(f"N={N}: L={L}, sum w - 1 = {mass-1:.2e}, "
              f"E[e^Y]/e^(rh) - 1 = {mean_growth/np.exp(cfg.R*h)-1:.2e}")

def check_european():
    print("\nEuropean check: grid - closed form (dollars)")
    for N in cfg.NS:
        for d in cfg.DELTAS:
            for kind in ("put", "call"):
                res = solve(N, d, kind=kind, american=False)
                errs = [res.value_at(s) - bs_price(s, kind, d) for s in SPOTS]
                print(f"  N={N} delta={d:<7} {kind:4s}: "
                      + "  ".join(f"{e:+.2e}" for e in errs))

def check_refinement():
    print("\nSpatial refinement, American (grid-exercise) put, N=180")
    for d in cfg.DELTAS:
        out = {}
        for m in (5, 10, 20):
            t0 = time.perf_counter()
            res = solve(180, d, grid=LogGrid(m_per_div=m))
            out[m] = res
            vals = [res.value_at(s) for s in SPOTS]
            print(f"  delta={d:<7} m={m:2d} dx={res.S.size and LogGrid(m_per_div=m).dx:.2e} "
                  f"V(60,80,100) = " + ", ".join(f"{v:.6f}" for v in vals)
                  + f"   [{time.perf_counter()-t0:.2f}s]")
        db = np.nanmax(np.abs(out[20].boundary - out[10].boundary))
        dv = max(abs(out[20].value_at(s) - out[10].value_at(s)) for s in SPOTS)
        print(f"  m=10 vs m=20: max|dV| = {dv:.2e} $, max|db| = {db:.2e} $")

if __name__ == "__main__":
    check_kernel(); check_european(); check_refinement()
