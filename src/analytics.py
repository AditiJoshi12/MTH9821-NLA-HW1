"""
analytics.py -- Closed-form European prices used ONLY to validate the
grid solver.

With proportional (fractional) dividends the ex-dividend stock at T is
S_T = S_0 (1-delta)^n  * GBM factor, where n = number of dividends in
(0, T].  Hence a European option equals Black-Scholes with spot
S_0 (1-delta)^n and no dividend yield.  This is exact for our model.
"""

import numpy as np
from scipy.stats import norm

import config as cfg


def bs_price(S0, kind="put", delta=0.0, K=cfg.K, T=cfg.T, r=cfg.R,
             sigma=cfg.SIGMA, n_div=3):
    S_adj = np.asarray(S0, float) * (1.0 - delta) ** n_div
    d1 = (np.log(S_adj / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if kind == "put":
        return K * np.exp(-r * T) * norm.cdf(-d2) - S_adj * norm.cdf(-d1)
    return S_adj * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
