"""
Backtest the match model against historical World Cup results.

Computes analytical match-outcome probabilities directly from the
Poisson + Dixon-Coles distribution (no Monte Carlo) and scores them
against actual scorelines from 2018 (Russia) and 2022 (Qatar) with
log-loss and Brier score.

The same code is used by `src/tune.py` as the optimisation objective
to fit `ModelParams` constants (`lg_avg`, `dc_rho`, host edges) and the
`K_Q` Elo-to-goals slope to historical data.

Historical teams are characterised by their pre-tournament Elo only;
style is set to zero (no historical style data). That mirrors the
"Elo-only" lower bound of our `data/derive_ratings.py` pipeline.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass

from .model import ModelParams, _dc_tau

HISTORICAL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "historical")
MAX_GOALS = 10   # P(more than 10 goals) is negligible for the lambdas we see
# Target within-tournament Elo std-dev (canonical scale, ~current 2026 teams).
# Historical Elos (synthesised from FIFA rank) are on a compressed scale; we
# rescale each tournament so its spread matches this target, making the
# Elo-to-goals constant `K_Q` directly comparable across scales.
CANONICAL_ELO_STD = 140.0


@dataclass
class HistoricalTeam:
    name: str
    elo_pre: float
    confederation: str
    is_host: bool


@dataclass
class HistoricalMatch:
    tournament: str
    round: str         # G, R16, QF, SF, 3P, F
    home: str
    away: str
    goals_home: int    # at 90 minutes
    goals_away: int
    et_or_pen: str     # "", "ET", or "PEN:X-Y"


def load_tournament(year: str):
    teams_path = os.path.join(HISTORICAL_DIR, f"wc{year}_teams.csv")
    results_path = os.path.join(HISTORICAL_DIR, f"wc{year}_results.csv")
    teams: dict[str, HistoricalTeam] = {}
    with open(teams_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            teams[r["team"].strip()] = HistoricalTeam(
                name=r["team"].strip(),
                elo_pre=float(r["elo_pre"]),
                confederation=r["confederation"].strip(),
                is_host=r["is_host"].strip().lower() in ("1", "true", "yes"),
            )
    matches: list[HistoricalMatch] = []
    with open(results_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            matches.append(HistoricalMatch(
                tournament=r["tournament"].strip(),
                round=r["round"].strip(),
                home=r["home"].strip(),
                away=r["away"].strip(),
                goals_home=int(r["goals_home"]),
                goals_away=int(r["goals_away"]),
                et_or_pen=r.get("extra_time_or_pen", "").strip(),
            ))
    return teams, matches


def _attack_defense_from_elo(elo: float, elo_avg: float, lg_avg: float,
                             k_q: float) -> tuple[float, float]:
    q = (elo - elo_avg) / 400.0
    return lg_avg * math.exp(k_q * q), lg_avg * math.exp(-k_q * q)


def match_lambdas(home: HistoricalTeam, away: HistoricalTeam, elo_avg: float,
                  p: ModelParams, k_q: float) -> tuple[float, float]:
    a_h, d_h = _attack_defense_from_elo(home.elo_pre, elo_avg, p.lg_avg, k_q)
    a_a, d_a = _attack_defense_from_elo(away.elo_pre, elo_avg, p.lg_avg, k_q)
    la = a_h * d_a / p.lg_avg
    lb = a_a * d_h / p.lg_avg
    if home.is_host:
        la *= p.host_attack_mult
        lb *= p.host_defense_mult
    if away.is_host:
        lb *= p.host_attack_mult
        la *= p.host_defense_mult
    return max(p.min_lambda, la), max(p.min_lambda, lb)


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def score_grid(la: float, lb: float, rho: float,
               max_goals: int = MAX_GOALS) -> list[list[float]]:
    """Joint probability P(x, y) on [0, max_goals]^2 with Dixon-Coles tau."""
    px = [_poisson_pmf(i, la) for i in range(max_goals + 1)]
    py = [_poisson_pmf(j, lb) for j in range(max_goals + 1)]
    grid = [[px[i] * py[j] * _dc_tau(i, j, la, lb, rho)
             for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    z = sum(c for row in grid for c in row)
    return [[c / z for c in row] for row in grid]


def outcome_probs(grid: list[list[float]]) -> tuple[float, float, float]:
    ph = pd = pa = 0.0
    for i, row in enumerate(grid):
        for j, prob in enumerate(row):
            if i > j:
                ph += prob
            elif i == j:
                pd += prob
            else:
                pa += prob
    return ph, pd, pa


@dataclass
class BacktestStats:
    n_matches: int
    log_loss: float        # mean -log(P[actual outcome]); lower = better
    brier: float           # mean SSE on outcome-probability vector; lower = better
    accuracy: float        # share of matches where the top-prob outcome happened
    mae_goals: float       # mean abs error on expected vs actual goals (per team-match)
    # Per-bin calibration: (predicted_prob_bin, frequency_observed, n_in_bin)
    calibration: list[tuple[float, float, int]]


def _calibration_bins(probs_outcomes: list[tuple[float, int]],
                      n_bins: int = 10) -> list[tuple[float, float, int]]:
    bins = [[] for _ in range(n_bins)]
    for p, hit in probs_outcomes:
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, hit))
    out = []
    for i, b in enumerate(bins):
        if not b:
            continue
        avg_p = sum(p for p, _ in b) / len(b)
        freq = sum(h for _, h in b) / len(b)
        out.append((avg_p, freq, len(b)))
    return out


def score_model(p: ModelParams, k_q: float,
                datasets: list[tuple[dict[str, HistoricalTeam], list[HistoricalMatch]]]
                ) -> BacktestStats:
    n = 0
    log_loss = 0.0
    brier = 0.0
    correct = 0
    abs_err = 0.0
    probs_outcomes: list[tuple[float, int]] = []   # for calibration plot

    for teams, matches in datasets:
        elos = [t.elo_pre for t in teams.values()]
        elo_avg = sum(elos) / len(elos)
        elo_std = math.sqrt(sum((e - elo_avg) ** 2 for e in elos) / len(elos))
        scale = CANONICAL_ELO_STD / elo_std if elo_std > 0 else 1.0
        # Rescale each team's Elo so the tournament's spread matches canonical.
        teams = {name: HistoricalTeam(
            name=t.name,
            elo_pre=elo_avg + (t.elo_pre - elo_avg) * scale,
            confederation=t.confederation, is_host=t.is_host,
        ) for name, t in teams.items()}
        for m in matches:
            home = teams.get(m.home)
            away = teams.get(m.away)
            if home is None or away is None:
                continue
            la, lb = match_lambdas(home, away, elo_avg, p, k_q)
            grid = score_grid(la, lb, p.dc_rho)
            ph, pd, pa = outcome_probs(grid)
            if m.goals_home > m.goals_away:
                actual_p, actual_idx = ph, 0
            elif m.goals_home == m.goals_away:
                actual_p, actual_idx = pd, 1
            else:
                actual_p, actual_idx = pa, 2
            log_loss -= math.log(max(actual_p, 1e-12))
            for i, prob in enumerate((ph, pd, pa)):
                brier += (prob - (1.0 if i == actual_idx else 0.0)) ** 2
            top_idx = max(range(3), key=lambda i: (ph, pd, pa)[i])
            if top_idx == actual_idx:
                correct += 1
            abs_err += abs(la - m.goals_home) + abs(lb - m.goals_away)
            for i, prob in enumerate((ph, pd, pa)):
                probs_outcomes.append((prob, 1 if i == actual_idx else 0))
            n += 1

    if n == 0:
        return BacktestStats(0, float("inf"), float("inf"), 0.0, float("inf"), [])
    return BacktestStats(
        n_matches=n,
        log_loss=log_loss / n,
        brier=brier / n,
        accuracy=correct / n,
        mae_goals=abs_err / (2 * n),
        calibration=_calibration_bins(probs_outcomes),
    )


def load_all(years: list[str] | None = None
             ) -> list[tuple[dict[str, HistoricalTeam], list[HistoricalMatch]]]:
    years = years or ["2018", "2022"]
    return [load_tournament(y) for y in years]
