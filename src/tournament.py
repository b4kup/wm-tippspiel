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
from datetime import datetime
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
    polymarket_prob: float | None = None   # real-money implied probability (%)
    shootout_skill: float = 0.5            # posterior win-rate (see src/shootout.py)


def load_teams(path: str | None = None, *, injuries: bool = True,
               injuries_path: str | None = None) -> list[Team]:
    """Load team ratings from CSV.

    By default the squad-availability layer in data/injuries.csv is applied on
    top of the baseline strength snapshot (see src/injuries.py); pass
    `injuries=False` for a full-strength run.
    """
    path = path or os.path.join(DATA_DIR, "teams.csv")
    teams: list[Team] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            odds = row["market_decimal_odds"].strip()
            poly = row.get("polymarket_prob", "").strip()
            teams.append(Team(
                name=row["team"].strip(),
                group=row["group"].strip(),
                confederation=row["confederation"].strip(),
                elo=float(row["elo"]),
                attack=float(row["attack"]),
                defense=float(row["defense"]),
                market_decimal_odds=float(odds) if odds else None,
                polymarket_prob=float(poly) if poly else None,
            ))
    if injuries:
        from .injuries import apply_injuries
        teams = apply_injuries(teams, path=injuries_path)
    # Attach per-team shootout skill (Bayesian posterior; 50% prior if no record).
    from dataclasses import replace
    from .shootout import load_records, skill_for
    records = load_records()
    teams = [replace(t, shootout_skill=skill_for(t.name, records)) for t in teams]
    return teams


def groups_from_teams(teams: list[Team]) -> dict[str, list[Team]]:
    groups: dict[str, list[Team]] = defaultdict(list)
    for t in teams:
        groups[t.group].append(t)
    return dict(sorted(groups.items()))


# --------------------------------------------------------------------------
# Fixture list (group-stage schedule)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Fixture:
    """One scheduled group-stage match. `home`/`away` are team names (the home
    team as listed in the official fixture); `kickoff` is CEST/MESZ."""
    number: int            # official match number (Spiel 1-72)
    kickoff: datetime      # kickoff in Central European Summer Time (MESZ)
    group: str
    home: str
    away: str
    venue: str


def load_fixtures(path: str | None = None) -> list[Fixture]:
    """Load the group-stage schedule from data/fixtures.csv, sorted by kickoff.

    Returns [] if the file is absent. Kickoff dates/times are MESZ (the source
    is a German fixture list), so the ordering is the one a Central-European
    viewer sees."""
    path = path or os.path.join(DATA_DIR, "fixtures.csv")
    if not os.path.exists(path):
        return []
    fixtures: list[Fixture] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("home"):
                continue  # skip blank / template lines
            fixtures.append(Fixture(
                number=int(row["number"]),
                kickoff=datetime.strptime(
                    f"{row['date'].strip()} {row['time'].strip()}",
                    "%Y-%m-%d %H:%M"),
                group=row["group"].strip(),
                home=row["home"].strip(),
                away=row["away"].strip(),
                venue=row["venue"].strip(),
            ))
    return sorted(fixtures, key=lambda f: (f.kickoff, f.number))


# --------------------------------------------------------------------------
# Group stage
# --------------------------------------------------------------------------

@dataclass
class GroupRow:
    team: Team
    points: int = 0
    gf: int = 0
    ga: int = 0
    # Per-opponent ledger: opp_name -> (points, gf, ga) for that head-to-head
    # fixture. Populated as the round-robin plays out; consumed by the FIFA
    # tiebreaker chain when teams finish on equal points + overall GD + GF.
    h2h: dict = field(default_factory=dict)

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def _overall_key(row: GroupRow) -> tuple:
    """FIFA's first three tiebreakers: points, GD, then GF."""
    return (row.points, row.gd, row.gf)


def _head_to_head_key(row: GroupRow, group_rows: list[GroupRow],
                      tied_names: frozenset[str]) -> tuple:
    """FIFA tiebreakers 4-6: points / GD / GF in the mini-table of matches
    played between the tied teams only."""
    pts = gf = ga = 0
    for opp in tied_names:
        if opp == row.team.name:
            continue
        rec = row.h2h.get(opp)
        if rec is None:
            continue
        p_, gf_, ga_ = rec
        pts += p_; gf += gf_; ga += ga_
    return (pts, gf - ga, gf)


def _resolve_overall_ties(rows: list[GroupRow], rng: random.Random
                          ) -> list[GroupRow]:
    """Sort one group's rows applying the full FIFA tiebreaker chain.

    Order: overall points / GD / GF, then a head-to-head mini-table among any
    teams still tied (points / GD / GF in matches played between them only),
    then a random nudge (which stands in for fair-play / drawing of lots)."""
    # Group rows by the overall key; tied rows inside each bucket get the
    # head-to-head treatment, then a coin flip for any residual ties.
    rows = sorted(rows, key=_overall_key, reverse=True)
    out: list[GroupRow] = []
    i = 0
    while i < len(rows):
        j = i + 1
        while j < len(rows) and _overall_key(rows[j]) == _overall_key(rows[i]):
            j += 1
        bucket = rows[i:j]
        if len(bucket) > 1:
            tied_names = frozenset(r.team.name for r in bucket)
            bucket.sort(
                key=lambda r: (_head_to_head_key(r, bucket, tied_names),
                               rng.random()),
                reverse=True)
        out.extend(bucket)
        i = j
    return out


def play_group(teams: list[Team], rng: random.Random,
               p: ModelParams, results=None, fatigues=None) -> list[GroupRow]:
    """Round-robin a group, return rows sorted best-first. Matches already in
    `results` use their real scoreline instead of being simulated.

    `fatigues` is the pre-computed map from `src/travel.compute_match_fatigues`;
    when present, each match's expected goals are nudged by travel / rest /
    altitude carryover for the two sides."""
    rows = {t.name: GroupRow(t) for t in teams}
    for a, b in combinations(teams, 2):
        actual = results.group_score(a.name, b.name) if results else None
        fa = fb = 0.0
        if fatigues is not None:
            from .travel import lookup_fatigue, fatigue_score
            pair = lookup_fatigue(fatigues, a.name, b.name)
            if pair is not None:
                ta, tb = pair
                fa = fatigue_score(ta, p.travel_per_1000km, p.rest_day_value,
                                   p.altitude_per_1000m, p.heat_per_degree)
                fb = fatigue_score(tb, p.travel_per_1000km, p.rest_day_value,
                                   p.altitude_per_1000m, p.heat_per_degree)
        ga, gb = actual if actual is not None else simulate_match(
            a, b, rng, p, fatigue_a=fa, fatigue_b=fb)
        ra, rb = rows[a.name], rows[b.name]
        ra.gf += ga; ra.ga += gb
        rb.gf += gb; rb.ga += ga
        if ga > gb:
            pa, pb = 3, 0
            ra.points += 3
        elif gb > ga:
            pa, pb = 0, 3
            rb.points += 3
        else:
            pa = pb = 1
            ra.points += 1; rb.points += 1
        ra.h2h[b.name] = (pa, ga, gb)
        rb.h2h[a.name] = (pb, gb, ga)
    return _resolve_overall_ties(list(rows.values()), rng)


# --------------------------------------------------------------------------
# Knockout stage
# --------------------------------------------------------------------------

def select_best_thirds(thirds: list[tuple[str, GroupRow]], n: int,
                       rng: random.Random) -> list[tuple[str, GroupRow]]:
    """Rank the 12 third-placed teams and return the best `n`. Third-placed
    teams sit in different groups, so head-to-head doesn't apply — fall back
    to overall points / GD / GF and break residual ties randomly."""
    return sorted(
        thirds,
        key=lambda gr: (_overall_key(gr[1]), rng.random()),
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


def _ko_winner_from_result(r, a: Team, b: Team):
    """Resolve the advancing team from a recorded knockout result."""
    name = r.winner_name()
    if name == a.name:
        return a
    if name == b.name:
        return b
    return a  # draw with no recorded shootout winner: fall back deterministically


def run_knockout(round_of_32_ties, rng: random.Random, p: ModelParams,
                 results=None, ko_fatigues=None):
    """
    Run a single-elimination bracket from concrete Round-of-32 ties (each a
    (Team, Team) pair). Consecutive ties are paired down the tree. Any tie whose
    result is recorded in `results` uses the real outcome instead of simulating.
    Returns dict with the team that reached each round.

    `ko_fatigues` (optional): callable `(stage, tie_idx, team_a, team_b) ->
    (fatigue_a, fatigue_b)` giving each team's travel/rest/altitude/heat
    fatigue score going into the match. Defaults to no carryover.
    """
    reached = {"R32": [], "R16": [], "QF": [], "SF": [], "Final": [], "Champion": None,
               "RunnerUp": None}
    for a, b in round_of_32_ties:
        reached["R32"].extend([a, b])

    # `stage` is the round the current ties belong to; `label` is the round their
    # winners advance to. 16 R32 ties -> R16 -> QF -> SF -> Final -> Champion.
    current = list(round_of_32_ties)
    for stage, label in zip(["R32", "R16", "QF", "SF", "Final"],
                            ["R16", "QF", "SF", "Final", "Champion"]):
        winners = []
        for tie_idx, (a, b) in enumerate(current):
            r = results.ko_result(stage, a.name, b.name) if results else None
            if r is not None:
                winners.append(_ko_winner_from_result(r, a, b))
            else:
                fa = fb = 0.0
                if ko_fatigues is not None:
                    fa, fb = ko_fatigues(stage, tie_idx, a, b)
                winners.append(simulate_knockout(a, b, rng, p,
                                                 fatigue_a=fa, fatigue_b=fb))
        if label == "Champion":
            champ = winners[0]
            final_a, final_b = current[0]
            reached["Champion"] = champ
            reached["RunnerUp"] = final_b if champ is final_a else final_a
            break
        reached[label].extend(winners)
        current = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
    return reached
