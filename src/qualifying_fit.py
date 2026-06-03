"""
Data-driven attack/defense from 2026 qualifying goals.

What this is and why
--------------------
The Elo+style derivation in `data/derive_ratings.py` is a *prior* — what we'd
expect each team's attack/defense to be from their overall strength. But we
also have a *signal* from the actual qualifying campaign: how many goals each
team scored and conceded over 6-18 matches.

This module blends the two:

    attack_final  = w · attack_from_goals + (1 − w) · attack_from_elo

where `w = matches / (matches + N_PRIOR)` shrinks small samples toward the
Elo prior. A team with 18 CONMEBOL matches gets ~64% weight on the goal
signal; a team with 6 UEFA matches gets ~37%. Teams with no qualifying
data (the three hosts, plus a couple of playoff winners we couldn't source)
keep their Elo-derived values untouched.

Opposition adjustment
---------------------
Raw qualifying goals/match isn't comparable across confederations:

  Norway scored 37 goals in 8 UEFA-weak matches → naive attack ≈ 4.6
  Argentina scored 31 in 18 CONMEBOL matches  → naive attack ≈ 1.7

But CONMEBOL opponents are far stronger than UEFA-weak minnows like
Liechtenstein. So we divide each team's GF/match by a confederation-specific
"typical opponent defense" estimate, undoing the field-strength bias:

    attack_from_goals = (GF/match × LG_AVG) / TYPICAL_OPP_DEFENSE[confed]

`TYPICAL_OPP_DEFENSE` and `_ATTACK` reflect the actual qualifying field for
each confederation (mostly weaker than the WC average ~1.35, except CONMEBOL
which is uniformly strong).

Limitations
-----------
- Confederation-typical opposition is coarse. Within UEFA, group-A teams
  played far weaker opponents than group-K teams. A proper Poisson regression
  on match-level data would do better; we have only aggregates.
- Wikipedia qualifying numbers are mid-update for a few teams (e.g. some
  near-zero "goals against" totals). Treated as directional; the shrinkage
  blunts the impact.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
# Sample-size denominator: a team needs ~20 matches before the data signal
# matches the Elo prior in weight. Bigger = more shrinkage to Elo. We picked
# this conservatively because:
#   - confederation-typical-opponent strengths are coarse;
#   - qualifying and WC play in different competitive environments
#     (UEFA quals include far weaker opponents than the WC field).
# A 6-match team gets ~23% data weight; 18 matches gets ~47%.
N_PRIOR = 20.0

# Per-confederation estimates of the *typical opponent* a WC qualifier faced
# during the 2026 cycle. Higher `defense` = weaker defenders (easier to score
# against). Higher `attack` = stronger attackers (harder to keep clean sheets).
# These reflect the actual qualifying field, not the WC average:
#   - UEFA quals had many minnows (Liechtenstein, Andorra, Moldova) → defense ↑
#   - CONMEBOL is a 10-team league of equals → both close to WC average
#   - OFC outside NZ is very weak → defense ↑↑, attack ↓
TYPICAL_OPP: dict[str, tuple[float, float]] = {
    # confed -> (typical_opp_attack, typical_opp_defense)
    "UEFA":     (1.05, 1.60),
    "CONMEBOL": (1.35, 1.25),
    "AFC":      (1.10, 1.55),
    "CAF":      (1.05, 1.55),
    "CONCACAF": (1.00, 1.65),
    "OFC":      (0.80, 2.00),
}


@dataclass(frozen=True)
class QualifyingRecord:
    team: str
    matches: int
    gf: int
    ga: int
    confederation: str

    @property
    def gf_per_match(self) -> float:
        return self.gf / self.matches if self.matches else 0.0

    @property
    def ga_per_match(self) -> float:
        return self.ga / self.matches if self.matches else 0.0


def load_qualifying(path: str | None = None) -> dict[str, QualifyingRecord]:
    path = path or os.path.join(DATA_DIR, "qualifying.csv")
    out: dict[str, QualifyingRecord] = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            team = (row.get("team") or "").strip()
            if not team or team.startswith("#"):
                continue
            out[team] = QualifyingRecord(
                team=team,
                matches=int(row["matches"]),
                gf=int(row["gf"]),
                ga=int(row["ga"]),
                confederation=row["confederation"].strip(),
            )
    return out


def implied_ratings(record: QualifyingRecord, lg_avg: float
                    ) -> tuple[float, float]:
    """Convert (GF, GA, matches) into (attack, defense) assuming the team's
    opponents had the confederation-typical strength.

    The Poisson model says goals_scored = attack × opp_defense / lg_avg. Solve
    for attack: attack = goals_scored × lg_avg / opp_defense.
    Symmetric reasoning gives defense from goals_conceded.
    """
    opp_attack, opp_defense = TYPICAL_OPP.get(record.confederation, (1.0, 1.5))
    attack = record.gf_per_match * lg_avg / opp_defense
    defense = record.ga_per_match * lg_avg / opp_attack
    return attack, defense


def shrinkage_weight(matches: int, n_prior: float = N_PRIOR) -> float:
    """How much weight the data gets vs. the Elo prior. 6 matches → 0.375;
    10 matches → 0.500; 18 matches → 0.643."""
    return matches / (matches + n_prior)


def blend(team: str, attack_prior: float, defense_prior: float,
          records: dict[str, QualifyingRecord], lg_avg: float,
          n_prior: float = N_PRIOR) -> tuple[float, float]:
    """Return (attack_final, defense_final). When no qualifying data exists
    for this team, return the priors unchanged."""
    rec = records.get(team)
    if rec is None or rec.matches == 0:
        return attack_prior, defense_prior
    a_data, d_data = implied_ratings(rec, lg_avg)
    w = shrinkage_weight(rec.matches, n_prior)
    return (w * a_data + (1 - w) * attack_prior,
            w * d_data + (1 - w) * defense_prior)
