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
from dataclasses import dataclass, replace

HOSTS = {"United States", "Canada", "Mexico"}

# Must match data/derive_ratings.py (average goals scored by one team per match).
LG_AVG = 1.5972
# Must match data/derive_ratings.py: how Elo quality maps to attack/defence.
K_Q = 0.8155


@dataclass(frozen=True)
class ModelParams:
    lg_avg: float = LG_AVG
    # Multiplicative home edge for host nations: they score more, concede less.
    host_attack_mult: float = 1.2000
    host_defense_mult: float = 0.8500
    # Floor on a team's expected goals so even huge underdogs can score.
    min_lambda: float = 0.15
    # Std-dev (in Elo points) of each team's *true* tournament strength around
    # its rating, sampled once per simulation. Captures rating uncertainty and
    # tournament-level form, which a point-estimate model ignores -> it stops
    # the favourites being over-confident and fattens the upset tail. Set 0 to
    # disable (pure point-estimate Monte Carlo).
    rating_sigma_elo: float = 45.0
    # Dixon-Coles low-score correlation. Independent Poisson under-counts 0-0,
    # 1-0 and 1-1; a small negative rho pushes probability into those cells
    # (more low-scoring games and draws), matching real football. Set 0 to
    # disable (pure independent Poisson). Typical range ~[-0.15, 0].
    dc_rho: float = -0.0885
    # Travel/rest/altitude fatigue weights. The tired side scores less and
    # concedes more (applied as a differential between the two teams). Defaults
    # are conservative reads of the sports-science literature; set any to 0 to
    # disable that channel. See src/travel.py.
    travel_per_1000km: float = 0.002      # ~0.2% goals per 1000 km flown
    rest_day_value: float = 0.010         # ~1% goals per missing rest day
    altitude_per_1000m: float = 0.040     # ~4% goals per 1000 m above 1500 m


DEFAULT_PARAMS = ModelParams()


def perturb_team(team, sigma_elo: float, rng: random.Random):
    """Return a copy of `team` with its strength shifted by a random draw.

    Drawn once per simulation: a positive draw makes the team better this
    tournament (sharper attack, meaner defence), mapped through the same
    Elo->goals relationship used to build the ratings."""
    if sigma_elo <= 0:
        return team
    d = rng.gauss(0.0, sigma_elo)
    f = math.exp(K_Q * d / 400.0)
    return replace(team, attack=team.attack * f, defense=team.defense / f,
                   elo=team.elo + d)


def win_expectancy(elo_a: float, elo_b: float) -> float:
    """Classic Elo win expectancy for team A (draws shared) in [0, 1].

    Used only to resolve a drawn knockout match (extra time / penalties)."""
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def expected_goals(team_a, team_b, p: ModelParams = DEFAULT_PARAMS,
                   fatigue_a: float = 0.0, fatigue_b: float = 0.0):
    """Return (lambda_a, lambda_b): expected goals for each team.

    `fatigue_a` / `fatigue_b` are small non-negative scalars (typically 0-0.05)
    summarising the team's travel / short-rest / altitude burden going into
    this match. Applied as a *differential*: the fresher side scores more and
    concedes less, so two equally-tired teams play a normal game."""
    la = team_a.attack * team_b.defense / p.lg_avg
    lb = team_b.attack * team_a.defense / p.lg_avg
    if team_a.name in HOSTS:
        la *= p.host_attack_mult
        lb *= p.host_defense_mult
    if team_b.name in HOSTS:
        lb *= p.host_attack_mult
        la *= p.host_defense_mult
    if fatigue_a != 0.0 or fatigue_b != 0.0:
        diff = fatigue_a - fatigue_b
        la *= math.exp(-diff)     # team_a tired -> scores less
        lb *= math.exp(diff)      # team_a tired -> concedes more
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


def _dc_tau(x: int, y: int, la: float, lb: float, rho: float) -> float:
    """Dixon-Coles correction factor for the four low-score cells."""
    if x == 0 and y == 0:
        return max(0.0, 1.0 - la * lb * rho)
    if x == 0 and y == 1:
        return max(0.0, 1.0 + la * rho)
    if x == 1 and y == 0:
        return max(0.0, 1.0 + lb * rho)
    if x == 1 and y == 1:
        return max(0.0, 1.0 - rho)
    return 1.0


def _sample_goals(la: float, lb: float, rng: random.Random, rho: float):
    """Draw a scoreline. With rho == 0 this is independent Poisson; otherwise
    it samples exactly from the Dixon-Coles distribution by rejection (the
    only cells where tau != 1 are the four low-score corners)."""
    if rho == 0.0:
        return _poisson(la, rng), _poisson(lb, rng)
    # tau peaks at the (0,0) / (1,1) cells when rho < 0; bound the ratio there.
    m = max(1.0, 1.0 - la * lb * rho, 1.0 - rho)
    while True:
        x, y = _poisson(la, rng), _poisson(lb, rng)
        if rng.random() * m <= _dc_tau(x, y, la, lb, rho):
            return x, y


def simulate_match(team_a, team_b, rng: random.Random,
                   p: ModelParams = DEFAULT_PARAMS,
                   fatigue_a: float = 0.0, fatigue_b: float = 0.0):
    """Simulate a group match. Returns (goals_a, goals_b)."""
    la, lb = expected_goals(team_a, team_b, p, fatigue_a, fatigue_b)
    return _sample_goals(la, lb, rng, p.dc_rho)


def simulate_knockout(team_a, team_b, rng: random.Random,
                      p: ModelParams = DEFAULT_PARAMS):
    """Simulate a knockout match. Returns the winning team (no draws).

    A drawn 90' is resolved with the **shootout model** (see src/shootout.py):
    a Bayesian-shrunk team-specific shootout skill, not an Elo coin flip.
    Open-play Elo doesn't predict penalty outcomes — historical records do,
    once shrunk toward 50% to handle small samples."""
    ga, gb = simulate_match(team_a, team_b, rng, p)
    if ga > gb:
        return team_a
    if gb > ga:
        return team_b
    sa = getattr(team_a, "shootout_skill", 0.5)
    sb = getattr(team_b, "shootout_skill", 0.5)
    p_a = sa / (sa + sb) if (sa + sb) > 0 else 0.5
    return team_a if rng.random() < p_a else team_b
