"""
Penalty-shootout skill per team, with Bayesian shrinkage to a 50/50 prior.

Why a separate model
--------------------
Open-play strength (Elo, attack/defense) doesn't transfer cleanly to a
shootout. Take a 12-yard penalty with no defender and one kick: the
better-overall team's edge collapses to almost nothing. Historical
international records bear this out:

  Germany  ████████  7-1   ← exceptional
  Italy    █████     5-3
  Brazil   ███       3-4   ← Elo says elite, shootouts say middling
  Spain    █         1-3   ← Elo says elite, shootouts say bottom

Two problems with using raw win-rates as-is:

  1. Tiny samples. Most teams have played fewer than 10 shootouts ever.
     A 1-0 record is not "100% shootout team".
  2. Selection bias. Better teams reach later rounds where more shootouts
     happen, so total counts don't reflect underlying skill.

Bayesian shrinkage handles (1): we *start* every team at 50% with a
"phantom" record of (α, β) wins/losses, then update with the real data.
For α = β = 8 (our default), every team's posterior win-rate sits on:

    posterior = (α + wins) / (α + β + total)

A team with no record stays at 8/16 = 50.0%. Germany's 7-1 only moves
them to 15/24 = 62.5% — strong but capped. The PRIOR_STRENGTH constant
controls how aggressively we shrink toward 50%: bigger = more shrinkage.

How it plugs into the match model
---------------------------------
For a drawn knockout tie, `simulate_knockout` no longer uses the Elo
win expectancy as a stand-in for "extra time + penalties". Instead it
draws the shootout winner with:

    P(A wins shootout) = skill_A / (skill_A + skill_B)

If both teams sit at the 50% prior, this is a fair coin flip. The wider
the skill gap, the bigger the shootout edge — but always damped by the
prior.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
# Prior strength: pretend every team starts with α+β shootouts at 50/50.
# Larger values pull posteriors harder toward 50%. With 16 we need ~16
# real shootouts before the observed rate has more weight than the prior;
# perfect for the small samples (most teams ≤ 8 shootouts ever) we have.
PRIOR_STRENGTH = 16.0
PRIOR_WIN_RATE = 0.5
PRIOR_ALPHA = PRIOR_STRENGTH * PRIOR_WIN_RATE
PRIOR_BETA = PRIOR_STRENGTH * (1 - PRIOR_WIN_RATE)


@dataclass(frozen=True)
class ShootoutRecord:
    team: str
    wins: int
    losses: int

    @property
    def total(self) -> int:
        return self.wins + self.losses

    @property
    def posterior_skill(self) -> float:
        """Beta-Binomial posterior win-rate, shrunk to a 50% prior."""
        return (PRIOR_ALPHA + self.wins) / (PRIOR_ALPHA + PRIOR_BETA + self.total)


def load_records(path: str | None = None) -> dict[str, ShootoutRecord]:
    """Read data/shootouts.csv. Missing file -> no records (every team
    falls back to the 50% prior)."""
    path = path or os.path.join(DATA_DIR, "shootouts.csv")
    out: dict[str, ShootoutRecord] = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            team = (row.get("team") or "").strip()
            if not team or team.startswith("#"):
                continue
            out[team] = ShootoutRecord(
                team=team,
                wins=int(row.get("wins") or 0),
                losses=int(row.get("losses") or 0),
            )
    return out


def skill_for(team_name: str, records: dict[str, ShootoutRecord]) -> float:
    """Posterior shootout-skill for `team_name`. Teams with no record
    default to the 50% prior."""
    rec = records.get(team_name)
    if rec is None:
        return PRIOR_WIN_RATE
    return rec.posterior_skill


def resolve_shootout(skill_a: float, skill_b: float, rnd: float) -> bool:
    """True if team A wins the shootout, given each team's posterior skill
    and a uniform[0, 1) draw. Returns False if team B wins."""
    p_a = skill_a / (skill_a + skill_b)
    return rnd < p_a
