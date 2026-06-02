"""
Tournament structures for the 2026 World Cup: teams, group stage and the
48-team knockout bracket.
"""

from __future__ import annotations

import csv
import os
import random
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from data.bracket import is_third, third_allowed_groups
from .model import DEFAULT_PARAMS, ModelParams, simulate_knockout, simulate_match

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass
class Team:
    name: str
    group: str
    confederation: str
    elo: float
    attack: float          # expected goals scored vs an average team
    defense: float         # expected goals conceded vs an average team (lower = better)
    market_decimal_odds: float | None = None


def load_teams(path: str | None = None) -> list[Team]:
    path = path or os.path.join(DATA_DIR, "teams.csv")
    teams: list[Team] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            odds = row["market_decimal_odds"].strip()
            teams.append(Team(
                name=row["team"].strip(),
                group=row["group"].strip(),
                confederation=row["confederation"].strip(),
                elo=float(row["elo"]),
                attack=float(row["attack"]),
                defense=float(row["defense"]),
                market_decimal_odds=float(odds) if odds else None,
            ))
    return teams


def groups_from_teams(teams: list[Team]) -> dict[str, list[Team]]:
    groups: dict[str, list[Team]] = defaultdict(list)
    for t in teams:
        groups[t.group].append(t)
    return dict(sorted(groups.items()))


# --------------------------------------------------------------------------
# Group stage
# --------------------------------------------------------------------------

@dataclass
class GroupRow:
    team: Team
    points: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def _rank_key(row: GroupRow, rng: random.Random):
    # Points, then goal difference, then goals for; a random nudge stands in
    # for head-to-head / fair-play / drawing-of-lots tie-breakers.
    return (row.points, row.gd, row.gf, rng.random())


def play_group(teams: list[Team], rng: random.Random,
               p: ModelParams) -> list[GroupRow]:
    """Round-robin a group, return rows sorted best-first."""
    rows = {t.name: GroupRow(t) for t in teams}
    for a, b in combinations(teams, 2):
        ga, gb = simulate_match(a, b, rng, p)
        ra, rb = rows[a.name], rows[b.name]
        ra.gf += ga; ra.ga += gb
        rb.gf += gb; rb.ga += ga
        if ga > gb:
            ra.points += 3
        elif gb > ga:
            rb.points += 3
        else:
            ra.points += 1; rb.points += 1
    return sorted(rows.values(), key=lambda r: _rank_key(r, rng), reverse=True)


# --------------------------------------------------------------------------
# Knockout stage
# --------------------------------------------------------------------------

def select_best_thirds(thirds: list[tuple[str, GroupRow]], n: int,
                       rng: random.Random) -> list[tuple[str, GroupRow]]:
    """Rank the 12 third-placed teams and return the best `n`."""
    return sorted(
        thirds,
        key=lambda gr: _rank_key(gr[1], rng),
        reverse=True,
    )[:n]


def assign_thirds_to_slots(round_of_32, third_entries, rng):
    """
    Fill the third-place slots ("3:ABCDF" etc.) in the Round of 32 with the 8
    qualifying third-placed teams, respecting each slot's allowed groups (FIFA's
    cluster codes). `third_entries` is a list of (group_letter, Team).

    Which third lands where depends on the combination of qualifying groups
    (FIFA resolves it from a 495-scenario table). We instead find *a* valid
    assignment by constrained matching: any matching that honours every slot's
    allowed groups is bracket-legal, and which legal matching is picked has
    negligible effect on aggregate probabilities. Ties are broken randomly.
    """
    # Slots that need a third: (tie_index, allowed_groups).
    third_slots = [(i, third_allowed_groups(b))
                   for i, (a, b) in enumerate(round_of_32) if is_third(b)]
    thirds = list(third_entries)
    rng.shuffle(thirds)

    assignment = {}            # tie_index -> Team
    used = [False] * len(thirds)

    # Match most-constrained slots first for an efficient backtracking search.
    slots_sorted = sorted(third_slots, key=lambda s: len(s[1]))

    def backtrack(k):
        if k == len(slots_sorted):
            return True
        idx, allowed = slots_sorted[k]
        for ti, (g, team) in enumerate(thirds):
            if not used[ti] and g in allowed:
                used[ti] = True
                assignment[idx] = team
                if backtrack(k + 1):
                    return True
                used[ti] = False
                del assignment[idx]
        return False

    if not backtrack(0):
        # No constraint-satisfying matching (shouldn't occur with FIFA's
        # clusters); fall back to assigning leftovers arbitrarily so the
        # simulation never stalls.
        for idx, _allowed in third_slots:
            if idx not in assignment:
                ti = next(i for i, u in enumerate(used) if not u)
                used[ti] = True
                assignment[idx] = thirds[ti][1]

    ties = []
    for i, (a, b) in enumerate(round_of_32):
        ties.append((a, assignment[i]) if i in assignment else (a, b))
    return ties


def run_knockout(round_of_32_ties, rng: random.Random, p: ModelParams):
    """
    Run a single-elimination bracket from concrete Round-of-32 ties (each a
    (Team, Team) pair). Consecutive ties are paired down the tree.
    Returns dict with the team that reached each round.
    """
    reached = {"R32": [], "R16": [], "QF": [], "SF": [], "Final": [], "Champion": None,
               "RunnerUp": None}
    for a, b in round_of_32_ties:
        reached["R32"].extend([a, b])

    # Each label is the round the *winners* of the current ties advance to.
    # 16 R32 ties -> R16 -> QF -> SF -> Final -> Champion (five rounds).
    current = list(round_of_32_ties)
    for label in ["R16", "QF", "SF", "Final", "Champion"]:
        winners = [simulate_knockout(a, b, rng, p) for a, b in current]
        if label == "Champion":
            champ = winners[0]
            final_a, final_b = current[0]
            reached["Champion"] = champ
            reached["RunnerUp"] = final_b if champ is final_a else final_a
            break
        reached[label].extend(winners)
        current = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
    return reached
