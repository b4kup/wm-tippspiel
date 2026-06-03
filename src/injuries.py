"""
Squad-availability layer: nudge a team's ATTACK/DEFENSE/Elo down for injured or
absent players, on top of the baseline strength snapshot in data/teams.csv.

Why this is a separate layer
----------------------------
`data/teams.csv` is a *full-strength* snapshot of each side (Elo + style ->
attack/defense, see data/derive_ratings.py). Injuries are a different kind of
input: short-lived, player-specific, and known only in the days before kickoff.
Keeping them in their own file (data/injuries.csv) means the underlying strength
ratings stay clean and auditable, the availability hit is transparent and easy
to revise as news breaks, and the whole adjustment can be switched off
(`--no-injuries`) for a like-for-like "full-strength" run.

How a player's absence maps to ratings
---------------------------------------
Each row in data/injuries.csv describes one absence with three judgements that
are easy to source from any injury tracker:

  * importance - how big a loss the player is (talisman / star / key / squad),
                 expressed as an Elo-equivalent strength hit if fully out;
  * status     - how likely the player is to miss matches (out / doubtful /
                 questionable), which scales the hit;
  * position   - which phase of play the loss falls on. A forward mainly
                 weakens the ATTACK; a goalkeeper or defender mainly weakens the
                 DEFENSE; a midfielder splits between the two.

For a team we sum the Elo-equivalent loss across its absences, split it into an
attack-side loss `la` and a defence-side loss `ld` by position, then map both
through the *same* Elo->goals relationship the ratings were built with
(K_Q / 400, see src/model.py and data/derive_ratings.py):

    attack  *= exp(-K_Q * la / 400)      # fewer goals scored
    defense *= exp(+K_Q * ld / 400)      # more goals conceded (higher = worse)
    elo     -= (la + ld)                 # overall strength for KO tie-breaks

So losing a star striker dents a side's attack without pretending it also helps
the defence, and losing a goalkeeper does the reverse. The numbers below are
deliberately modest and fully tunable — injuries shift the dial, they don't
rewrite the favourites.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .model import K_Q

if TYPE_CHECKING:                       # avoid an import cycle at runtime
    from .tournament import Team

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Elo-equivalent strength hit if the player is fully out for the tournament.
IMPORTANCE_ELO = {
    "talisman": 60,    # a genuinely irreplaceable superstar (rare)
    "star": 40,        # world-class, clear difference-maker
    "key": 22,         # nailed-on starter
    "squad": 10,       # rotation / depth piece
}

# How much of that hit actually lands, given how likely the player is to miss.
STATUS_FACTOR = {
    "out": 1.0,            # ruled out
    "doubtful": 0.5,       # likely to miss some matches
    "questionable": 0.25,  # racing the clock, may well play
    "fit": 0.0,            # recovered / available — kept on file, no effect
}

# Fraction of the loss that falls on ATTACK; the remainder worsens DEFENSE.
# A striker is almost all attack; a goalkeeper is all defence; a midfielder
# splits. Both common spellings of each position are accepted.
POSITION_ATTACK_SHARE = {
    "fwd": 0.85, "fw": 0.85, "forward": 0.85, "st": 0.85, "att": 0.85,
    "mid": 0.55, "mf": 0.55, "midfielder": 0.55, "am": 0.60, "dm": 0.45,
    "def": 0.20, "df": 0.20, "defender": 0.20, "cb": 0.15, "fb": 0.30,
    "gk": 0.0, "goalkeeper": 0.0,
}
DEFAULT_ATTACK_SHARE = 0.5              # unknown position: split evenly


@dataclass(frozen=True)
class Injury:
    team: str
    player: str
    position: str
    importance: str
    status: str
    note: str = ""

    @property
    def elo_loss(self) -> float:
        """Elo-equivalent strength the team loses from this absence."""
        base = IMPORTANCE_ELO.get(self.importance.strip().lower(), IMPORTANCE_ELO["key"])
        factor = STATUS_FACTOR.get(self.status.strip().lower(), 1.0)
        return base * factor

    @property
    def attack_share(self) -> float:
        return POSITION_ATTACK_SHARE.get(self.position.strip().lower(),
                                         DEFAULT_ATTACK_SHARE)


@dataclass(frozen=True)
class TeamAdjustment:
    """The net availability adjustment applied to one team."""
    attack_mult: float
    defense_mult: float
    elo_delta: float
    injuries: list[Injury]


def load_injuries(path: str | None = None) -> list[Injury]:
    """Read data/injuries.csv. Missing file -> no injuries (returns [])."""
    path = path or os.path.join(DATA_DIR, "injuries.csv")
    if not os.path.exists(path):
        return []
    injuries: list[Injury] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            team = (row.get("team") or "").strip()
            if not team or team.startswith("#"):
                continue
            injuries.append(Injury(
                team=team,
                player=(row.get("player") or "").strip(),
                position=(row.get("position") or "").strip(),
                importance=(row.get("importance") or "key").strip(),
                status=(row.get("status") or "out").strip(),
                note=(row.get("note") or "").strip(),
            ))
    return injuries


def team_adjustments(injuries: list[Injury]) -> dict[str, TeamAdjustment]:
    """Aggregate a flat injury list into one net adjustment per team."""
    by_team: dict[str, list[Injury]] = {}
    for inj in injuries:
        by_team.setdefault(inj.team, []).append(inj)

    adjustments: dict[str, TeamAdjustment] = {}
    for team, items in by_team.items():
        la = sum(i.elo_loss * i.attack_share for i in items)
        ld = sum(i.elo_loss * (1.0 - i.attack_share) for i in items)
        adjustments[team] = TeamAdjustment(
            attack_mult=_elo_to_factor(-la),
            defense_mult=_elo_to_factor(ld),   # defense rises => worse
            elo_delta=-(la + ld),
            injuries=items,
        )
    return adjustments


def _elo_to_factor(delta_elo: float) -> float:
    """Map an Elo delta to a goals-rating multiplier (matches derive_ratings)."""
    import math
    return math.exp(K_Q * delta_elo / 400.0)


def apply_injuries(teams: list["Team"], injuries: list[Injury] | None = None,
                   path: str | None = None) -> list["Team"]:
    """Return a copy of `teams` with availability adjustments applied.

    Injuries whose team name matches no loaded team are ignored. Pass an empty
    list (or point at a missing file) to leave ratings untouched.
    """
    if injuries is None:
        injuries = load_injuries(path)
    if not injuries:
        return list(teams)
    adj = team_adjustments(injuries)
    out: list["Team"] = []
    for t in teams:
        a = adj.get(t.name)
        if a is None:
            out.append(t)
            continue
        out.append(replace(
            t,
            attack=t.attack * a.attack_mult,
            defense=t.defense * a.defense_mult,
            elo=t.elo + a.elo_delta,
        ))
    return out
