"""
Market-anchored Bayesian shrinkage for team ratings.

The betting market aggregates a lot of information our model can't see
(squad chemistry, manager confidence, training-camp form). The market
has an edge in raw forecasting and is *especially* hard to beat at the
top — the favourites' true probabilities. Markets are imperfect at the
long tail (low-liquidity outsiders) but they pin down the top of the
table tightly.

This module exposes `apply_market_shrinkage(teams, weight)` which
blends each team's attack / defense ratings toward the market-implied
title strength. The blend is in log-space so it composes naturally
with the other rating layers (Elo, qualifying, Poisson fit, injuries).

Mechanics
---------
1. Read each team's decimal odds and de-vig (`1/odds` normalised across
   the listed teams) → market title probability `m_i`.
2. Map title probability to a log-strength signal `s_i = log(m_i)`,
   centred so `mean(s_i) = 0` over teams with odds.
3. Shrink each team's attack and defense in opposite directions by
   `weight * s_i * STRENGTH_TO_GOALS_LOG`. The factor anchors a
   log-prob shift to a log-goal shift — calibrated so a market shift
   that doubles a team's title probability corresponds to roughly a
   one-standard-deviation strength shift in the model.

Use a small weight (~0.2) — the market should nudge, not dominate.
"""

from __future__ import annotations

import math
from dataclasses import replace

# Empirical: one standard deviation of `log(title_prob)` across the
# field maps roughly to one `K_Q`-scaled strength tilt. So shifting a
# team's log-prob by Δ corresponds to log-attack += Δ · STRENGTH_TO_GOALS_LOG
# and log-defense -= Δ · STRENGTH_TO_GOALS_LOG.
STRENGTH_TO_GOALS_LOG = 0.10


def implied_title_probs(teams) -> dict[str, float]:
    """Return de-vigged market-implied title probabilities for teams with
    `market_decimal_odds` set; teams without odds are omitted."""
    odds_rows = [(t.name, t.market_decimal_odds) for t in teams
                 if getattr(t, "market_decimal_odds", None)]
    if not odds_rows:
        return {}
    overround = sum(1.0 / o for _n, o in odds_rows)
    if overround <= 0:
        return {}
    return {n: (1.0 / o) / overround for n, o in odds_rows}


def apply_market_shrinkage(teams, weight: float = 0.20):
    """Return a new team list shifted toward the market-implied strength.

    `weight` in [0, 1]: 0 = no shrinkage (model only), 1 = full snap to
    the market signal (sledgehammer; almost never the right call). The
    sane range is 0.1-0.3.

    Teams without odds keep their original ratings.
    """
    if weight <= 0:
        return list(teams)
    market = implied_title_probs(teams)
    if not market:
        return list(teams)
    # Centre the log-probabilities so the shrinkage is *direction-only*
    # (the team with mean market strength stays put).
    mean_log = sum(math.log(p) for p in market.values()) / len(market)
    out = []
    for t in teams:
        if t.name not in market:
            out.append(t)
            continue
        s = math.log(market[t.name]) - mean_log
        shift = weight * s * STRENGTH_TO_GOALS_LOG
        out.append(replace(
            t,
            attack=t.attack * math.exp(shift),
            defense=t.defense * math.exp(-shift),
        ))
    return out
