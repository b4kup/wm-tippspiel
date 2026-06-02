"""
Real-result ingestion, simulation conditioning and incremental rating updates.

As matches are played you record them in data/results.csv. This module:
  * loads those results and lets the simulator substitute the real scoreline for
    any match already played (conditioning the rest of the tournament on what
    has actually happened);
  * incrementally **re-tunes** team ratings from observed results via a standard
    Elo update (with a goal-margin multiplier), so the re-simulation of the
    remaining matches reflects current form.

results.csv columns:
    stage,team_a,team_b,goals_a,goals_b,winner
  * stage: "group" or a knockout round ("R32","R16","QF","SF","Final","3P").
  * goals_a/goals_b: the 90'(+ET) scoreline as team_a-team_b.
  * winner: only for a knockout match level after extra time (penalty-shootout
    winner). Optional; ignored for group matches.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass, replace

from .model import K_Q

GROUP = "group"
KO_STAGES = ("R32", "R16", "QF", "SF", "3P", "Final")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass(frozen=True)
class MatchResult:
    stage: str
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    winner: str | None = None  # penalty-shootout winner for a drawn KO match

    def winner_name(self) -> str | None:
        if self.goals_a > self.goals_b:
            return self.team_a
        if self.goals_b > self.goals_a:
            return self.team_b
        return self.winner  # decided on penalties (may be None if not recorded)


class Results:
    """Lookup of played matches, keyed by (stage, unordered team pair)."""

    def __init__(self, rows):
        self.rows = list(rows)
        self._by_key = {(r.stage, frozenset((r.team_a, r.team_b))): r
                        for r in rows}

    def __len__(self):
        return len(self.rows)

    def group_score(self, a: str, b: str):
        """(goals_a, goals_b) oriented to (a, b), or None if not played."""
        r = self._by_key.get((GROUP, frozenset((a, b))))
        if r is None:
            return None
        return (r.goals_a, r.goals_b) if r.team_a == a else (r.goals_b, r.goals_a)

    def ko_result(self, stage: str, a: str, b: str):
        return self._by_key.get((stage, frozenset((a, b))))

    def group_results(self):
        return [r for r in self.rows if r.stage == GROUP]

    def knockout_results(self):
        return [r for r in self.rows if r.stage in KO_STAGES]


def load_results(path: str | None = None) -> Results:
    path = path or os.path.join(DATA_DIR, "results.csv")
    if not os.path.exists(path):
        return Results([])
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("team_a") or row.get("goals_a", "") == "":
                continue  # skip blank / template lines
            rows.append(MatchResult(
                stage=row["stage"].strip(),
                team_a=row["team_a"].strip(),
                team_b=row["team_b"].strip(),
                goals_a=int(row["goals_a"]),
                goals_b=int(row["goals_b"]),
                winner=(row.get("winner") or "").strip() or None,
            ))
    return Results(rows)


def _goal_multiplier(gd: int) -> float:
    """World-Football-Elo style goal-difference weight for an Elo update."""
    gd = abs(gd)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def update_ratings(teams, results: Results, k: float = 40.0):
    """Return new Team list with Elo (and attack/defense) re-tuned from results.

    Sequential Elo update over every played match; the Elo change is mapped onto
    attack/defense through the same Elo->goals relation used to build the
    ratings, so a team's offensive/defensive *style* is preserved while its
    overall level moves toward its observed form."""
    elo = {t.name: t.elo for t in teams}
    by_name = {t.name: t for t in teams}

    for r in results.rows:
        a, b = r.team_a, r.team_b
        if a not in elo or b not in elo:
            continue
        ea, eb = elo[a], elo[b]
        exp_a = 1.0 / (1.0 + 10 ** ((eb - ea) / 400.0))
        sa = 0.5 if r.goals_a == r.goals_b else (1.0 if r.goals_a > r.goals_b else 0.0)
        delta = k * _goal_multiplier(r.goals_a - r.goals_b) * (sa - exp_a)
        elo[a] += delta
        elo[b] -= delta

    updated = []
    for t in teams:
        d = elo[t.name] - t.elo
        f = math.exp(K_Q * d / 400.0)
        updated.append(replace(t, elo=elo[t.name],
                               attack=t.attack * f, defense=t.defense / f))
    return updated
