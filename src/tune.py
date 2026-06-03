"""
Auto-tune ModelParams to fit historical World Cup data.

Uses a Nelder-Mead simplex search (pure stdlib) over five constants:

    lg_avg, K_Q, dc_rho, host_attack_mult, host_defense_mult

The objective is mean log-loss on the W/D/L outcome of every match in
the backtest set (2018 + 2022). `src/backtest.py` provides the scorer.

Why Nelder-Mead: derivative-free, robust on a small noisy objective,
trivially expressed in stdlib. ~100 iterations converges on this surface.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from .backtest import BacktestStats, score_model
from .model import ModelParams

# (name, default, lower, upper) -- soft bounds; out-of-bounds returns +inf
PARAM_SPEC: list[tuple[str, float, float, float]] = [
    ("lg_avg",            1.35,  1.00,  2.00),
    ("k_q",               0.70,  0.30,  1.50),
    ("dc_rho",           -0.10, -0.30,  0.05),
    # Host edges narrowed: 2-host backtest sample is not enough to justify
    # wide ranges; cap at modest, plausible football-prior values.
    ("host_attack_mult",  1.10,  1.00,  1.20),
    ("host_defense_mult", 0.92,  0.85,  1.00),
]


@dataclass
class TunedParams:
    lg_avg: float
    k_q: float
    dc_rho: float
    host_attack_mult: float
    host_defense_mult: float

    def to_model_params(self, sigma_elo: float = 45.0,
                        min_lambda: float = 0.15) -> ModelParams:
        return ModelParams(
            lg_avg=self.lg_avg,
            host_attack_mult=self.host_attack_mult,
            host_defense_mult=self.host_defense_mult,
            min_lambda=min_lambda,
            rating_sigma_elo=sigma_elo,
            dc_rho=self.dc_rho,
        )

    @classmethod
    def from_vector(cls, v: list[float]) -> "TunedParams":
        return cls(lg_avg=v[0], k_q=v[1], dc_rho=v[2],
                   host_attack_mult=v[3], host_defense_mult=v[4])

    def to_vector(self) -> list[float]:
        return [self.lg_avg, self.k_q, self.dc_rho,
                self.host_attack_mult, self.host_defense_mult]


def _in_bounds(v: list[float]) -> bool:
    return all(lo <= x <= hi for x, (_, _, lo, hi) in zip(v, PARAM_SPEC))


def make_objective(datasets) -> Callable[[list[float]], float]:
    """Return a callable f(vector) -> log-loss, with bound penalties."""
    def f(v: list[float]) -> float:
        if not _in_bounds(v):
            return float("inf")
        tp = TunedParams.from_vector(v)
        mp = tp.to_model_params()
        stats = score_model(mp, tp.k_q, datasets)
        return stats.log_loss
    return f


# ---- Nelder-Mead -----------------------------------------------------------

def _centroid(simplex: list[list[float]], drop_idx: int) -> list[float]:
    n = len(simplex) - 1
    return [sum(p[i] for j, p in enumerate(simplex) if j != drop_idx) / n
            for i in range(len(simplex[0]))]


def _reflect(centroid, worst, alpha=1.0):
    return [c + alpha * (c - w) for c, w in zip(centroid, worst)]


def nelder_mead(f: Callable[[list[float]], float],
                x0: list[float], *,
                step: float = 0.05,
                max_iter: int = 200,
                xtol: float = 1e-4,
                ftol: float = 1e-5,
                verbose: bool = False
                ) -> tuple[list[float], float, list[tuple[int, float]]]:
    n = len(x0)
    # Build initial simplex: start point + one perturbation per axis (rel. step).
    simplex = [list(x0)]
    for i in range(n):
        p = list(x0)
        delta = step * (abs(p[i]) if p[i] != 0 else 1.0)
        p[i] += delta
        simplex.append(p)
    fvals = [f(p) for p in simplex]
    history: list[tuple[int, float]] = []

    for it in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: fvals[i])
        simplex = [simplex[i] for i in order]
        fvals = [fvals[i] for i in order]
        history.append((it, fvals[0]))

        if verbose and it % 10 == 0:
            print(f"  iter {it:3d}  best log-loss = {fvals[0]:.6f}  "
                  f"params = {[round(x, 4) for x in simplex[0]]}")

        # Convergence: simplex collapses or function values agree
        diam = max(max(abs(simplex[i][k] - simplex[0][k]) for i in range(1, n + 1))
                   for k in range(n))
        f_spread = fvals[-1] - fvals[0]
        if diam < xtol and f_spread < ftol:
            break

        worst = simplex[-1]
        c = _centroid(simplex, drop_idx=n)
        xr = _reflect(c, worst, alpha=1.0)
        fr = f(xr)

        if fvals[0] <= fr < fvals[-2]:
            simplex[-1] = xr; fvals[-1] = fr
            continue

        if fr < fvals[0]:
            xe = _reflect(c, worst, alpha=2.0)
            fe = f(xe)
            if fe < fr:
                simplex[-1] = xe; fvals[-1] = fe
            else:
                simplex[-1] = xr; fvals[-1] = fr
            continue

        # Contraction
        if fr < fvals[-1]:
            xc = [ci + 0.5 * (xri - ci) for ci, xri in zip(c, xr)]   # outside
            fc = f(xc)
            if fc <= fr:
                simplex[-1] = xc; fvals[-1] = fc
                continue
        else:
            xc = [ci + 0.5 * (wi - ci) for ci, wi in zip(c, worst)]  # inside
            fc = f(xc)
            if fc < fvals[-1]:
                simplex[-1] = xc; fvals[-1] = fc
                continue

        # Shrink toward best
        best = simplex[0]
        for i in range(1, n + 1):
            simplex[i] = [bi + 0.5 * (xi - bi) for bi, xi in zip(best, simplex[i])]
            fvals[i] = f(simplex[i])

    order = sorted(range(n + 1), key=lambda i: fvals[i])
    return simplex[order[0]], fvals[order[0]], history


def tune(datasets, *, verbose: bool = False
         ) -> tuple[TunedParams, BacktestStats, BacktestStats, list[tuple[int, float]]]:
    """Tune params and return (tuned, stats_before, stats_after, history)."""
    x0 = [spec[1] for spec in PARAM_SPEC]
    baseline = TunedParams.from_vector(x0)
    stats_before = score_model(baseline.to_model_params(), baseline.k_q, datasets)

    obj = make_objective(datasets)
    best, _best_loss, history = nelder_mead(obj, x0, verbose=verbose)
    tuned = TunedParams.from_vector(best)
    stats_after = score_model(tuned.to_model_params(), tuned.k_q, datasets)
    return tuned, stats_before, stats_after, history
