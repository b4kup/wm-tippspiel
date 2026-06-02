"""
Match outcome model: per-team ATTACK and DEFENSE ratings -> expected goals ->
Poisson scoreline.

Each team carries two ratings (see data/derive_ratings.py):

    attack  = expected goals it SCORES against an average World Cup team
    defense = expected goals it CONCEDES against an average team (lower = better)

For a match between A and B the expected goals combine multiplicatively, the
standard independent-Poisson / SPI-style goal model:

    lambda_A = attack_A * defense_B / LG_AVG          (goals A scores)
    lambda_B = attack_B * defense_A / LG_AVG          (goals B scores)

So a sharp attack (high attack_A) meeting a leaky defence (high defense_B)
produces a lot of goals, while two compact sides grind out a low-scoring game.
Hosts get a small multiplicative home advantage. Knockout draws are resolved
by extra time / penalties, modelled as an Elo-weighted coin flip.

All parameters live in `ModelParams` so the model is easy to re-calibrate.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

HOSTS = {"United States", "Canada", "Mexico"}

# Must match data/derive_ratings.py (average goals scored by one team per match).
LG_AVG = 1.35


@dataclass(frozen=True)
class ModelParams:
    lg_avg: float = LG_AVG
    # Multiplicative home edge for host nations: they score more, concede less.
    host_attack_mult: float = 1.10
    host_defense_mult: float = 0.92
    # Floor on a team's expected goals so even huge underdogs can score.
    min_lambda: float = 0.15


DEFAULT_PARAMS = ModelParams()


def win_expectancy(elo_a: float, elo_b: float) -> float:
    """Classic Elo win expectancy for team A (draws shared) in [0, 1].

    Used only to resolve a drawn knockout match (extra time / penalties)."""
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def expected_goals(team_a, team_b, p: ModelParams = DEFAULT_PARAMS):
    """Return (lambda_a, lambda_b): expected goals for each team."""
    la = team_a.attack * team_b.defense / p.lg_avg
    lb = team_b.attack * team_a.defense / p.lg_avg
    if team_a.name in HOSTS:
        la *= p.host_attack_mult
        lb *= p.host_defense_mult
    if team_b.name in HOSTS:
        lb *= p.host_attack_mult
        la *= p.host_defense_mult
    return max(p.min_lambda, la), max(p.min_lambda, lb)


def _poisson(lam: float, rng: random.Random) -> int:
    """Knuth's algorithm for a Poisson sample (lambda is small here)."""
    L = math.exp(-lam)
    k, prod = 0, 1.0
    while True:
        prod *= rng.random()
        if prod <= L:
            return k
        k += 1


def simulate_match(team_a, team_b, rng: random.Random,
                   p: ModelParams = DEFAULT_PARAMS):
    """Simulate a group match. Returns (goals_a, goals_b)."""
    la, lb = expected_goals(team_a, team_b, p)
    return _poisson(la, rng), _poisson(lb, rng)


def simulate_knockout(team_a, team_b, rng: random.Random,
                      p: ModelParams = DEFAULT_PARAMS):
    """Simulate a knockout match. Returns the winning team (no draws)."""
    ga, gb = simulate_match(team_a, team_b, rng, p)
    if ga > gb:
        return team_a
    if gb > ga:
        return team_b
    # Extra time / penalties: weight by Elo win expectancy.
    return team_a if rng.random() < win_expectancy(team_a.elo, team_b.elo) else team_b
