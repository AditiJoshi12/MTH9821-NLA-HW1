"""
nn_policy.py -- Part 4: a neural exercise boundary refined with PyTorch.

Boundary model (assignment)
---------------------------
* delta = 0      : ONE network on [0, T].
* delta = 0.0125 : FOUR networks on [0,d1), [d1,d2), [d2,d3), [d3,T]; a
  dividend date belongs to the interval that STARTS there (post-jump).
* On [alpha, beta): scalar input x = (t - alpha)/(beta - alpha),
  Linear(1,8) -> tanh -> Linear(8,1).  Networks are built in chronological
  order right after torch.manual_seed(5000 + c), with default init.
* b_theta(t_j) = U_j * sigmoid(f_theta(t_j)) for j < N, b_theta(T) = K.
  The cap U_j is built in, so the network cannot place the boundary above
  the Part 1 bound; it only learns the SHAPE below it.

Training (assignment)
---------------------
1. Supervised initialisation: exactly 1,000 full-grid Adam steps (lr 0.01)
   on (1/N) sum_j ((b_theta(t_j) - b^LS_j)/K)^2  -> checkpoint 0.
   The optimiser is then discarded.
2. Payoff optimisation: fresh Adam (lr 0.003), 2,400 updates, minibatches
   of 512 paths drawn uniformly WITH replacement from an 8,192-path bank
   using PyTorch's generator; smoothing eps = 0.01 for updates 1-400 and
   0.002 for 401-2400 (optimiser state kept across the change).
   Objective: minimise the batch mean of -R_theta / K, where

     p_j = 1{S_j < K} sigmoid((b_theta(t_j) - S_j)/(eps K)),  J <= j < N,  p_N = 1
     w_j = p_j prod_{k=J}^{j-1} (1 - p_k)
     R   = sum_{j=J}^{N} w_j e^{-r(t_j - t_J)} (K - S_j)^+ .

   Randomised stopping: at each date, if not yet stopped, stop with
   probability p_j (independently of the future).  w_j is then exactly the
   probability of stopping FIRST at j, so R is the conditional expected
   discounted payoff of that randomised rule given the path.  It is smooth
   in theta, so gradients exist; as eps -> 0 the rule becomes the hard
   threshold rule.
3. Validation: checkpoints 0, 400, 800, ..., 2400 evaluated on a separate
   4,096-path bank with the HARD rule (float64).  Highest mean payoff
   (discounted to t_J) wins; ties go to the earliest checkpoint.

Precision: training in float32 (allowed); validation and final boundary
evaluation in float64 (a float64 copy of the network).

RANDOM-DRAW ORDER for the path banks -- ASSUMPTION (README.md not seen):
    J  = rng.integers(0, N, n)          # start index
    SJ = simulation.sample_A(rng, n)    # start price (post-jump at a dividend)
    Z  = rng.standard_normal((n, N))    # column i drives step i -> i+1
"""

import copy
import time

import numpy as np
import torch
import torch.nn as nn

import config as cfg
import simulation as sim
from lsm import apply_hard_rule

N_BANK_TRAIN = 8_192
N_BANK_VAL = 4_096
BATCH = 512
N_SUPERVISED = 1_000
N_PAYOFF = 2_400
EPS_SCHEDULE = ((400, 0.01), (2_400, 0.002))   # (last update index, eps)
CHECKPOINTS = (0, 400, 800, 1_200, 1_600, 2_000, 2_400)


# ---------------------------------------------------------------------------
# Boundary model
# ---------------------------------------------------------------------------
class BoundaryModel(nn.Module):
    """Piecewise-in-time boundary b_theta(t_j), j = 0..N-1 (full grid)."""

    def __init__(self, tg: cfg.TimeGrid, delta: float):
        super().__init__()
        # interval end points (indices): [0, d1, d2, d3, N] or [0, N]
        ends = [0] + (list(tg.div_idx) if delta > 0 else []) + [tg.N]
        # built in chronological order: Linear(1,8) then Linear(8,1) per net
        self.nets = nn.ModuleList(
            nn.Sequential(nn.Linear(1, 8), nn.Tanh(), nn.Linear(8, 1))
            for _ in range(len(ends) - 1))

        # For each grid date j < N: which interval and its scaled input x.
        # A dividend date d_k = t_{j_d} belongs to the interval starting there.
        interval = np.searchsorted(np.array(ends[1:]), np.arange(tg.N), side="right")
        alpha = tg.t[np.array(ends[:-1])][interval]
        beta = tg.t[np.array(ends[1:])][interval]
        x = (tg.t[:tg.N] - alpha) / (beta - alpha)
        self.register_buffer("interval", torch.as_tensor(interval, dtype=torch.long))
        self.register_buffer("x", torch.as_tensor(x, dtype=torch.get_default_dtype()).unsqueeze(1))
        self.register_buffer("U", torch.as_tensor(cfg.dividend_cap(tg, delta),
                                                  dtype=torch.get_default_dtype()))
        self.N = tg.N

    def forward(self) -> torch.Tensor:
        """b_theta(t_j) for j = 0..N-1."""
        # Evaluate every interval network on its own dates only; gather keeps
        # the computation differentiable without in-place writes.
        F = torch.stack([net(self.x).squeeze(1) for net in self.nets])   # (n_nets, N)
        f = F.gather(0, self.interval.unsqueeze(0)).squeeze(0)          # pick own net
        return self.U * torch.sigmoid(f)

    @torch.no_grad()
    def boundary_float64(self) -> np.ndarray:
        """Full boundary (N+1,) in float64, b_N = K (for validation/evaluation)."""
        m64 = copy.deepcopy(self).double()
        return np.append(m64().numpy(), cfg.K)


# ---------------------------------------------------------------------------
# Path banks (random start J, S_J ~ A)
# ---------------------------------------------------------------------------
def make_bank(c: int, seed: int, n: int):
    """Returns (J, S) with S float64 of shape (n, N+1), NaN before J."""
    N, delta = sim.CASES[c]
    tg = cfg.TimeGrid(N)
    rng = np.random.default_rng(seed)
    J = rng.integers(0, N, n)
    SJ = sim.sample_A(rng, n)
    Z = rng.standard_normal((n, N))
    return J, sim.paths_from_J(J, SJ, Z, tg, delta)


def bank_tensors(J, S, tg, dtype=torch.float32):
    """Precompute everything the payoff objective needs that does not
    depend on theta (so each update only computes p, w and R)."""
    n, N = len(J), tg.N
    j = np.arange(N + 1)[None, :]
    active = j >= J[:, None]                              # J <= j <= N
    Sf = np.where(active, S, cfg.K)                        # fill pre-start with K (OTM)
    disc = np.exp(-cfg.R * (tg.t[None, :] - tg.t[J][:, None]))   # e^{-r(t_j - t_J)}
    G = np.where(active, disc * np.maximum(cfg.K - Sf, 0.0), 0.0) # discounted payoff
    itm = active[:, :N] & (Sf[:, :N] < cfg.K)
    return dict(S=torch.as_tensor(Sf[:, :N], dtype=dtype),
                G=torch.as_tensor(G, dtype=dtype),
                itm=torch.as_tensor(itm, dtype=dtype))


def payoff_R(b: torch.Tensor, bt: dict, idx: torch.Tensor, eps: float) -> torch.Tensor:
    """R_theta for the paths idx (randomised stopping, discounted to t_J)."""
    S, G, itm = bt["S"][idx], bt["G"][idx], bt["itm"][idx]
    p = itm * torch.sigmoid((b[None, :] - S) / (eps * cfg.K))        # (B, N), 0 before J
    p = torch.cat([p, torch.ones_like(p[:, :1])], dim=1)             # p_N = 1
    surv = torch.cumprod(1.0 - p, dim=1)                              # prod_{k<=j}(1-p_k)
    surv_excl = torch.cat([torch.ones_like(surv[:, :1]), surv[:, :-1]], dim=1)
    w = p * surv_excl                                                 # first-stop prob
    return (w * G).sum(dim=1)


def hard_payoffs(b64: np.ndarray, J: np.ndarray, S: np.ndarray, tg) -> np.ndarray:
    """Per-path hard-rule payoff discounted to t_J (float64)."""
    Q0, _ = apply_hard_rule(S, b64, tg, j_start=J)                    # time-zero dollars
    return Q0 * np.exp(cfg.R * tg.t[J])


def hard_mean(b64: np.ndarray, J: np.ndarray, S: np.ndarray, tg) -> float:
    """Mean hard-rule payoff discounted to t_J (float64)."""
    return float(np.mean(hard_payoffs(b64, J, S, tg)))


# ---------------------------------------------------------------------------
# Full Part 4 pipeline for one case
# ---------------------------------------------------------------------------
def train_case(c: int, b_ls: np.ndarray, log_every: int = 200, verbose=True):
    N, delta = sim.CASES[c]
    tg = cfg.TimeGrid(N)
    out = dict(case=c, N=N, delta=delta, timings={})

    # --- construction: seed once, then build layers in chronological order
    torch.manual_seed(5000 + c)
    model = BoundaryModel(tg, delta)

    # --- 1) supervised initialisation (full grid, no torch randomness used)
    t0 = time.perf_counter()
    target = torch.as_tensor(b_ls[:N], dtype=torch.float32)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    sup_hist = []
    for it in range(N_SUPERVISED):
        opt.zero_grad()
        loss = torch.mean(((model() - target) / cfg.K) ** 2)
        loss.backward()
        opt.step()
        sup_hist.append(loss.item())
    del opt                                                        # discard optimiser
    out["timings"]["supervised_s"] = time.perf_counter() - t0
    out["sup_loss_final"] = sup_hist[-1]
    ckpt = {0: model.boundary_float64()}
    params = {0: copy.deepcopy(model.state_dict())}

    # --- 2) path banks (NumPy seeds 2000+c train, 3000+c validation)
    t0 = time.perf_counter()
    Jt, St = make_bank(c, 2000 + c, N_BANK_TRAIN)
    Jv, Sv = make_bank(c, 3000 + c, N_BANK_VAL)
    bt = bank_tensors(Jt, St, tg)
    out["timings"]["banks_s"] = time.perf_counter() - t0

    # --- 3) payoff optimisation (fresh Adam; torch stream for minibatches)
    t0 = time.perf_counter()
    opt = torch.optim.Adam(model.parameters(), lr=0.003)
    pay_hist = []
    for it in range(1, N_PAYOFF + 1):
        eps = EPS_SCHEDULE[0][1] if it <= EPS_SCHEDULE[0][0] else EPS_SCHEDULE[1][1]
        idx = torch.randint(0, N_BANK_TRAIN, (BATCH,))            # with replacement
        opt.zero_grad()
        loss = -payoff_R(model(), bt, idx, eps).mean() / cfg.K
        loss.backward()
        opt.step()
        pay_hist.append(-loss.item() * cfg.K)                      # batch mean R ($)
        if it in CHECKPOINTS:
            ckpt[it] = model.boundary_float64()
            params[it] = copy.deepcopy(model.state_dict())
        if verbose and it % log_every == 0:
            print(f"  case {c} update {it:4d} eps={eps} batch mean R = {np.mean(pay_hist[-log_every:]):.4f}")
    out["timings"]["payoff_s"] = time.perf_counter() - t0

    # --- 4) validation (hard rule, float64) and selection
    t0 = time.perf_counter()
    Qv = {k: hard_payoffs(b, Jv, Sv, tg) for k, b in ckpt.items()}
    val = {k: float(q.mean()) for k, q in Qv.items()}
    # paired comparison with checkpoint 0 on the SAME validation paths:
    # tells us whether a difference in validation means is resolvable.
    d0 = {k: (float((q - Qv[0]).mean()), float((q - Qv[0]).std(ddof=1) / np.sqrt(q.size)))
          for k, q in Qv.items()}
    best = max(val.values())
    selected = min(k for k, v in val.items() if v == best)        # ties -> earliest
    out["timings"]["validation_s"] = time.perf_counter() - t0
    out.update(val_means=val, val_diff_vs0=d0, selected=selected, val_initial=val[0],
               val_selected=val[selected], boundary=ckpt[selected],
               checkpoints=ckpt, sup_hist=np.array(sup_hist),
               pay_hist=np.array(pay_hist),
               params=params, selected_params=params[selected])
    return out


def check_soft_limit(c: int = 1, b: np.ndarray = None, eps: float = 1e-7, n: int = 2000):
    """Sanity check of the randomised-stopping objective: as eps -> 0 the
    soft objective R must equal the hard-rule payoff.  Uses float64 and a
    throw-away bank (seed 9100 + c, outside the assignment's seeds)."""
    N, _ = sim.CASES[c]
    tg = cfg.TimeGrid(N)
    J, S = make_bank(c, 9100 + c, n)
    bt = bank_tensors(J, S, tg, dtype=torch.float64)
    soft = payoff_R(torch.as_tensor(b[:N]), bt, torch.arange(n), eps).mean().item()
    hard = hard_mean(b, J, S, tg)
    return dict(case=c, eps=eps, soft_mean=soft, hard_mean=hard, abs_diff=abs(soft - hard))
