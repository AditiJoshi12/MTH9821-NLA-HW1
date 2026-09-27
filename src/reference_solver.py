"""Reference valuation for a put with grid exercise and proportional dividends.

All returned values are immediately after the dividend at that date.  Between
exercise dates this solver applies the linear Black--Scholes semigroup through
finite differences.  Exercise is imposed only at the requested grid dates.

Dependencies: Python 3, NumPy; SciPy supplies a fast optional tridiagonal solver.
Run this file to reproduce the compact reference_results.npz.  Use --verify
to check saved results and repeat refinement calculations without writing files.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import platform
from time import perf_counter
import numpy as np
try:
    import scipy
    from scipy.linalg.lapack import dgttrf, dgttrs
except ImportError:
    scipy = None

K = 100.0
T = 0.75
R = float(np.log(1.05))
SIGMA = 0.30
DIVIDEND_TIMES = np.array([5.0 / 24.0, 11.0 / 24.0, 17.0 / 24.0])


class _Tridiagonal:
    def __init__(self, lower, diagonal, upper):
        self.fast = scipy is not None
        if self.fast:
            *self.factor, info = dgttrf(lower.copy(), diagonal.copy(), upper.copy())
            if info != 0:
                raise ArithmeticError('Tridiagonal factorization failed: %d' % info)
        else:
            self.lower, self.upper = lower.copy(), upper.copy()
            self.diagonal = diagonal.copy()
            for i in range(1, len(diagonal)):
                self.lower[i - 1] /= self.diagonal[i - 1]
                self.diagonal[i] -= self.lower[i - 1] * self.upper[i - 1]

    def solve(self, rhs):
        if self.fast:
            answer, info = dgttrs(*self.factor, rhs[:, None])
            if info != 0:
                raise ArithmeticError('Tridiagonal solve failed: %d' % info)
            return answer[:, 0]
        answer = rhs.copy()
        for i in range(1, len(answer)):
            answer[i] -= self.lower[i - 1] * answer[i - 1]
        answer[-1] /= self.diagonal[-1]
        for i in range(len(answer) - 2, -1, -1):
            answer[i] = (answer[i] - self.upper[i] * answer[i + 1]) / self.diagonal[i]
        return answer


def _exercise_boundary(spots, immediate, continuation):
    """Interpolate the single crossing and reject disconnected exercise sets."""
    eligible = spots < K
    difference = (immediate - continuation)[eligible]
    selected_spots = spots[eligible]
    exercise = difference >= 0.0
    continuation_nodes = np.flatnonzero(~exercise)
    if len(continuation_nodes) == 0:
        return float(K)
    first = int(continuation_nodes[0])
    if first == 0:
        raise ArithmeticError('The zero-spot boundary must be in the exercise set.')
    if np.any(exercise[first:]):
        raise ArithmeticError('Disconnected exercise region detected below the strike.')
    left = first - 1
    weight = difference[left] / (difference[left] - difference[first])
    return float(selected_spots[left] + weight * (selected_spots[first] - selected_spots[left]))


def solve_reference(n_dates=180, dividend_fraction=0.0, ds=0.1,
                    pde_substeps=8, s_max=400.0):
    """Return a dict of finite-difference reference arrays.

    Parameters
    ----------
    n_dates : int
        Number of time intervals.  180 and 360 are the assignment grids.
    dividend_fraction : float
        Spot changes from s to (1-dividend_fraction)*s on each dividend date.
    ds : float
        Uniform spot-grid increment in dollars; s_max/ds must be an integer.
    pde_substeps : int
        Linear PDE steps within each exercise interval.  The first substep
        consists of two backward-Euler half steps; remaining steps use
        Crank--Nicolson.  An exercise maximum is applied after all substeps.
    s_max : float
        Upper truncation of the spot grid.

    Returns
    -------
    dict with spots, times, values, continuation, boundary, dividend_indices,
    parameters, seconds.  values[j,k] is the value at date j and spot k after
    that date's dividend.  continuation at maturity is set to the payoff.
    boundary is a linearly interpolated exercise threshold, with terminal K.
    """
    start = perf_counter()
    if int(n_dates) != n_dates or n_dates < 1:
        raise ValueError('n_dates must be a positive integer.')
    if int(pde_substeps) != pde_substeps or pde_substeps < 1:
        raise ValueError('pde_substeps must be a positive integer.')
    if not 0 <= dividend_fraction < 1:
        raise ValueError('dividend_fraction must lie in [0,1).')
    if ds <= 0 or s_max <= K:
        raise ValueError('Require ds>0 and s_max>K.')
    n_dates, pde_substeps = int(n_dates), int(pde_substeps)
    n_space = int(round(s_max / ds))
    if abs(n_space * ds - s_max) > 1e-9:
        raise ValueError('s_max/ds must be an integer.')
    times = np.linspace(0.0, T, n_dates + 1)
    spots = np.linspace(0.0, s_max, n_space + 1)
    step = T / n_dates
    div_float = DIVIDEND_TIMES / step
    div_indices = np.rint(div_float).astype(int)
    if np.max(np.abs(div_float - div_indices)) > 1e-9:
        raise ValueError('Each dividend time must belong to the exercise grid.')
    div_set = set(div_indices.tolist())
    immediate = np.maximum(K - spots, 0.0)
    values = np.empty((n_dates + 1, n_space + 1), dtype=float)
    continuation = np.empty_like(values)
    boundary = np.empty(n_dates + 1)
    values[-1] = continuation[-1] = immediate
    boundary[-1] = K
    s = spots[1:-1]
    lower = 0.5 * SIGMA ** 2 * s ** 2 / ds ** 2 - 0.5 * R * s / ds
    diagonal = -SIGMA ** 2 * s ** 2 / ds ** 2 - R
    upper = 0.5 * SIGMA ** 2 * s ** 2 / ds ** 2 + 0.5 * R * s / ds
    h = step / pde_substeps
    solvers = {}
    for theta, time_step in [(1.0, 0.5 * h), (0.5, h)]:
        solvers[(theta, time_step)] = _Tridiagonal(
            -theta * time_step * lower[1:],
            1.0 - theta * time_step * diagonal,
            -theta * time_step * upper[:-1])

    def propagate(u, tau, theta, time_step):
        rhs = u[1:-1].copy()
        if theta != 1.0:
            rhs += (1.0 - theta) * time_step * (
                lower * u[:-2] + diagonal * u[1:-1] + upper * u[2:])
        # Zero spot at a future exercise date pays K.  Over a linear PDE
        # segment its discounted value is K*exp(-r*tau).
        left_new = K * np.exp(-R * (tau + time_step))
        rhs[0] += theta * time_step * lower[0] * left_new
        out = np.empty_like(u)
        out[0], out[-1] = left_new, 0.0
        out[1:-1] = solvers[(theta, time_step)].solve(rhs)
        return out

    for j in range(n_dates - 1, -1, -1):
        endpoint = values[j + 1]
        if j + 1 in div_set and dividend_fraction:
            endpoint = np.interp((1.0 - dividend_fraction) * spots, spots, endpoint)
        u = endpoint.copy()
        # Consistent upper-domain boundary for the linear PDE solve.
        u[-1] = 0.0
        u = propagate(u, 0.0, 1.0, 0.5 * h)
        u = propagate(u, 0.5 * h, 1.0, 0.5 * h)
        for substep in range(1, pde_substeps):
            u = propagate(u, substep * h, 0.5, h)
        continuation[j] = u
        boundary[j] = _exercise_boundary(spots, immediate, u)
        values[j] = np.maximum(immediate, u)
    if not np.all(np.isfinite(values)):
        raise ArithmeticError('Non-finite reference values.')
    return dict(spots=spots, times=times, values=values,
                continuation=continuation, boundary=boundary,
                dividend_indices=div_indices,
                parameters=dict(K=K, T=T, r=R, sigma=SIGMA,
                                dividend_fraction=float(dividend_fraction),
                                n_dates=n_dates, ds=ds,
                                pde_substeps=pde_substeps, s_max=s_max,
                                dividend_times=DIVIDEND_TIMES.tolist()),
                seconds=perf_counter() - start)


def _compare(coarse, fine):
    common_spots = [60.0, 80.0, 100.0]
    c = np.interp(common_spots, coarse['spots'], coarse['values'][0])
    f = np.interp(common_spots, fine['spots'], fine['values'][0])
    bd = np.abs(coarse['boundary'] - fine['boundary'])
    return dict(spots=common_spots, coarse_prices=c.tolist(), fine_prices=f.tolist(),
                maximum_price_difference=float(np.max(np.abs(c-f))),
                maximum_boundary_difference=float(np.max(bd)),
                median_boundary_difference=float(np.median(bd)),
                maximum_boundary_difference_time=float(coarse['times'][np.argmax(bd)]),
                coarse_parameters=coarse['parameters'], fine_parameters=fine['parameters'])


def build_reference(output_path=None, full_surfaces=False):
    """Generate four reference cases and spatial/time refinement diagnostics."""
    if output_path is None:
        output_path = Path(__file__).with_name('reference_results.npz')
    metadata = dict(environment=dict(python=platform.python_version(),
                                    numpy=np.__version__,
                                    scipy=None if scipy is None else scipy.__version__,
                                    platform=platform.platform()),
                    convention='All date-j states and surfaces are post-dividend.',
                    exercise='Every uniform grid date including zero and maturity.',
                    diagnostics={})
    arrays = {}
    for n_dates in [180, 360]:
        for delta in [0.0, 0.0125]:
            key = 'N%d_d%s' % (n_dates, '0' if delta == 0 else '0125')
            coarse = solve_reference(n_dates, delta, ds=0.20, pde_substeps=8)
            middle = solve_reference(n_dates, delta, ds=0.10, pde_substeps=8)
            fine = solve_reference(n_dates, delta, ds=0.05, pde_substeps=8)
            temporal = solve_reference(n_dates, delta, ds=0.05, pde_substeps=16)
            final = solve_reference(n_dates, delta, ds=0.05, pde_substeps=32)
            wider = solve_reference(n_dates, delta, ds=0.10, pde_substeps=8, s_max=600.0)
            last_dt = T / n_dates
            def last_european_put(s):
                d1 = (math.log(s / K) + (R + 0.5 * SIGMA ** 2) * last_dt) / (SIGMA * math.sqrt(last_dt))
                d2 = d1 - SIGMA * math.sqrt(last_dt)
                cdf_minus_d1 = 0.5 * math.erfc(d1 / math.sqrt(2.0))
                cdf_minus_d2 = 0.5 * math.erfc(d2 / math.sqrt(2.0))
                return K * math.exp(-R * last_dt) * cdf_minus_d2 - s * cdf_minus_d1
            left, right = 50.0, K
            for unused in range(70):
                midpoint = 0.5 * (left + right)
                if K - midpoint > last_european_put(midpoint):
                    left = midpoint
                else:
                    right = midpoint
            exact_last_boundary = 0.5 * (left + right)
            diagnostics = dict(spatial_020_to_010=_compare(coarse, middle),
                               spatial_010_to_005=_compare(middle, fine),
                               temporal_8_to_16=_compare(fine, temporal),
                               temporal_16_to_32=_compare(temporal, final),
                               domain_400_to_600=_compare(middle, wider),
                               last_interval_analytic_boundary=exact_last_boundary,
                               last_interval_boundary_error=float(final['boundary'][-2] - exact_last_boundary),
                               last_interval_at_money_continuation_error=float(np.interp(
                                   K, final['spots'], final['continuation'][-2]) - last_european_put(K)),
                               final_prices_at_60_80_100=np.interp(
                                   [60., 80., 100.], final['spots'], final['values'][0]).tolist(),
                               final_boundary_at_zero=float(final['boundary'][0]),
                               seconds=sum(x['seconds'] for x in [coarse, middle, fine, temporal, final, wider]))
            metadata['diagnostics'][key] = diagnostics
            metadata[key + '_parameters'] = final['parameters']
            arrays[key + '_value0'] = final['values'][0]
            for name in ['boundary', 'times', 'dividend_indices']:
                arrays[key + '_' + name] = final[name]
            if full_surfaces:
                for name in ['values', 'continuation']:
                    arrays[key + '_' + name] = final[name]
            arrays['spots'] = final['spots']
            print(key, json.dumps(diagnostics), flush=True)
    arrays['metadata_json'] = np.array(json.dumps(metadata, sort_keys=True))
    np.savez_compressed(output_path, **arrays)
    print('Saved', output_path, flush=True)
    return metadata


def verify_reference(input_path=None):
    """Check saved arrays and repeat space/time refinements without writing."""
    if input_path is None:
        input_path = Path(__file__).with_name('reference_results.npz')
    reports = {}
    with np.load(input_path, allow_pickle=False) as archive:
        metadata = json.loads(str(archive['metadata_json']))
        spots = archive['spots']
        if not np.all(np.isfinite(spots)) or not np.all(np.diff(spots) > 0):
            raise AssertionError('Saved spot grid must be finite and increasing.')
        for n_dates in [180, 360]:
            for delta in [0.0, 0.0125]:
                key = 'N%d_d%s' % (n_dates, '0' if delta == 0 else '0125')
                value0 = archive[key + '_value0']
                boundary = archive[key + '_boundary']
                times = archive[key + '_times']
                indices = archive[key + '_dividend_indices']
                if value0.shape != spots.shape or boundary.shape != (n_dates + 1,):
                    raise AssertionError('Saved array shapes disagree for ' + key)
                if not np.all(np.isfinite(value0)) or not np.all(np.isfinite(boundary)):
                    raise AssertionError('Saved values must be finite for ' + key)
                if np.any(value0 < np.maximum(K - spots, 0.0) - 1e-10):
                    raise AssertionError('Saved value violates the exercise payoff for ' + key)
                if np.any(np.diff(value0) > 1e-10):
                    raise AssertionError('Saved value must decrease with spot for ' + key)
                if np.any(boundary < 0.0) or np.any(boundary > K) or boundary[-1] != K:
                    raise AssertionError('Saved boundary lies outside [0,K] for ' + key)
                if not np.allclose(times, np.linspace(0.0, T, n_dates + 1), atol=1e-14, rtol=0):
                    raise AssertionError('Saved dates disagree for ' + key)
                if not np.allclose(times[indices], DIVIDEND_TIMES, atol=1e-14, rtol=0):
                    raise AssertionError('Saved dividend dates disagree for ' + key)
                params = metadata[key + '_parameters']
                if params['n_dates'] != n_dates or params['dividend_fraction'] != delta:
                    raise AssertionError('Saved model parameters disagree for ' + key)
                coarse = solve_reference(n_dates, delta, ds=0.10, pde_substeps=16)
                fine = solve_reference(n_dates, delta, ds=0.05, pde_substeps=16)
                refined = solve_reference(n_dates, delta, ds=0.05, pde_substeps=32)
                np.testing.assert_allclose(spots, refined['spots'], atol=1e-14, rtol=0)
                np.testing.assert_allclose(value0, refined['values'][0], atol=1e-9, rtol=0)
                np.testing.assert_allclose(boundary, refined['boundary'], atol=1e-8, rtol=0)
                reports[key] = dict(
                    spatial_010_to_005=_compare(coarse, fine),
                    temporal_16_to_32=_compare(fine, refined),
                    saved_price_max_difference=float(np.max(np.abs(value0 - refined['values'][0]))),
                    saved_boundary_max_difference=float(np.max(np.abs(boundary - refined['boundary']))))
                print(key, json.dumps(reports[key]), flush=True)
    print('Verification passed; saved arrays match recomputed references.', flush=True)
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify', action='store_true', help='Check the existing NPZ and repeat refinements.')
    mode.add_argument('--full-surfaces', action='store_true', help='Include all date value and continuation surfaces.')
    args = parser.parse_args()
    if args.verify:
        verify_reference(args.output)
    else:
        build_reference(args.output, full_surfaces=args.full_surfaces)
