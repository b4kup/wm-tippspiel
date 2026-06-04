"""
Monte Carlo driver: simulate the whole tournament many times and accumulate
probabilities for every team.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field

from .model import ModelParams, perturb_team
from .tournament import (
    Team,
    assign_thirds_to_slots,
    groups_from_teams,
    play_group,
    run_knockout,
    select_best_thirds,
)
from data.bracket import N_THIRD_PLACE, ROUND_OF_32, is_third


@dataclass
class Stats:
    n: int = 0
    # team name -> count
    win_group: dict = field(default_factory=lambda: defaultdict(int))
    advance: dict = field(default_factory=lambda: defaultdict(int))  # top-2 of group
    reach_r32: dict = field(default_factory=lambda: defaultdict(int))
    reach_r16: dict = field(default_factory=lambda: defaultdict(int))
    reach_qf: dict = field(default_factory=lambda: defaultdict(int))
    reach_sf: dict = field(default_factory=lambda: defaultdict(int))
    reach_final: dict = field(default_factory=lambda: defaultdict(int))
    champion: dict = field(default_factory=lambda: defaultdict(int))
    # group -> (winner_name, runnerup_name) -> count  (most likely qualifiers)
    group_pairs: dict = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    # (finalist_a, finalist_b) sorted -> count
    finals: dict = field(default_factory=lambda: defaultdict(int))
    # Per-R32-tie occupancy. 16 ties × 2 sides = 32 slots, indexed by
    # `tie_idx*2 + side`. Each slot maps team name -> sim count. Feeds the
    # interactive bracket explorer in the HTML dashboard.
    r32_slots: list = field(default_factory=lambda: [defaultdict(int) for _ in range(32)])
    # (a, b) sorted of the two teams in a given R32 tie -> count (per tie idx).
    r32_pairs: list = field(default_factory=lambda: [defaultdict(int) for _ in range(16)])

    def prob(self, counter: dict, name: str) -> float:
        return counter[name] / self.n if self.n else 0.0


def _make_ko_fatigue_callback(ko_state: dict, ties, p):
    """Build the `(stage, tie_idx, a, b) -> (fa, fb)` callback for the
    knockout walk. Tracks each team's last-played (date, city) as it
    advances; computes per-tie travel/rest/altitude/heat fatigue from
    that lookback to the scheduled KO venue.

    Cross-round mapping (consecutive pairing in run_knockout):
        R16 tie i  ← R32 ties (2i, 2i+1)
        QF  tie i  ← R16 ties (2i, 2i+1) ← R32 ties (4i..4i+3)
        ...
    """
    from .travel import ko_team_fatigue, fatigue_score, KO_SCHEDULE

    last = dict(ko_state["last_group_fixture"])  # team_name -> (date, city)
    venues = ko_state["venues"]
    schedule = ko_state.get("ko_schedule", KO_SCHEDULE)

    def _fatigue_for(team_name: str, fixture) -> float:
        prev = last.get(team_name)
        if prev is None:
            return 0.0
        tf = ko_team_fatigue(team_name, prev[0], prev[1], fixture, venues)
        return fatigue_score(tf, p.travel_per_1000km, p.rest_day_value,
                             p.altitude_per_1000m, p.heat_per_degree)

    def callback(stage, tie_idx, a, b):
        fixture = schedule.get((stage, tie_idx))
        if fixture is None:
            return 0.0, 0.0
        fa = _fatigue_for(a.name, fixture)
        fb = _fatigue_for(b.name, fixture)
        # Update both teams' last fixture so the *winner's* next-round lookup
        # has the right starting point. (Losers don't play another round.)
        last[a.name] = (fixture.date, fixture.city)
        last[b.name] = (fixture.date, fixture.city)
        return fa, fb

    return callback


def simulate_tournament_once(groups, rng, p, stats: Stats, results=None,
                             fatigues=None, ko_state=None):
    """`ko_state`, when provided, is a dict carrying immutable refs needed
    by the KO travel calc: `last_group_fixture` ({team -> (date, city)}),
    `venues` ({city -> Venue}), `ko_schedule` ({(round, idx) -> KOFixture}).
    Missing/None disables KO carryover."""
    winners_by_group, runners_by_group = {}, {}
    third_entries = []  # (group_letter, Team)

    # Sample each team's true strength for this tournament (rating uncertainty
    # + form). Done once per simulation so a team's bonus persists across all
    # its matches, which is what produces realistic deep runs and upsets.
    if p.rating_sigma_elo > 0:
        groups = {letter: [perturb_team(t, p.rating_sigma_elo, rng) for t in teams]
                  for letter, teams in groups.items()}

    for letter, teams in groups.items():
        table = play_group(teams, rng, p, results, fatigues=fatigues)
        winner, runner, third = table[0].team, table[1].team, table[2]
        winners_by_group[letter] = winner
        runners_by_group[letter] = runner
        third_entries.append((letter, third))  # keep GroupRow for ranking

        stats.win_group[winner.name] += 1
        stats.advance[winner.name] += 1
        stats.advance[runner.name] += 1
        stats.group_pairs[letter][(winner.name, runner.name)] += 1

    # Best 8 third-placed teams.
    best_thirds = select_best_thirds(third_entries, N_THIRD_PLACE, rng)
    third_teams = [(letter, gr.team) for letter, gr in best_thirds]
    for _letter, team in third_teams:
        stats.advance[team.name] += 1

    # Build concrete Round-of-32 ties. Third-place slots stay as their slot
    # string (e.g. "3:ABCDF") and are filled by the constrained matching below.
    def resolve(slot):
        if is_third(slot):
            return slot
        return winners_by_group[slot[1]] if slot[0] == "1" else runners_by_group[slot[1]]

    seeded = [(resolve(a), resolve(b)) for a, b in ROUND_OF_32]
    ties = assign_thirds_to_slots(seeded, third_teams, rng)

    # Record bracket occupancy before resolving the knockout.
    for i, (a, b) in enumerate(ties):
        stats.r32_slots[i * 2][a.name] += 1
        stats.r32_slots[i * 2 + 1][b.name] += 1
        pair = tuple(sorted((a.name, b.name)))
        stats.r32_pairs[i][pair] += 1

    ko_callback = _make_ko_fatigue_callback(ko_state, ties, p) if ko_state else None
    reached = run_knockout(ties, rng, p, results, ko_fatigues=ko_callback)
    for t in reached["R32"]:
        stats.reach_r32[t.name] += 1
    for t in reached["R16"]:
        stats.reach_r16[t.name] += 1
    for t in reached["QF"]:
        stats.reach_qf[t.name] += 1
    for t in reached["SF"]:
        stats.reach_sf[t.name] += 1
    for t in reached["Final"]:
        stats.reach_final[t.name] += 1
    stats.champion[reached["Champion"].name] += 1
    fa, fb = sorted(t.name for t in reached["Final"])
    stats.finals[(fa, fb)] += 1


def run(n_sims: int, params: ModelParams, seed: int | None = None,
        teams: list[Team] | None = None, results=None,
        travel: bool = True) -> tuple[Stats, dict]:
    from .tournament import load_teams
    rng = random.Random(seed)
    teams = teams or load_teams()
    groups = groups_from_teams(teams)
    fatigues = None
    ko_state = None
    if travel:
        try:
            from .travel import (compute_match_fatigues, load_schedule,
                                 load_venues, team_last_group_fixture,
                                 KO_SCHEDULE)
            schedule = load_schedule()
            venues = load_venues()
            fatigues = compute_match_fatigues(schedule, venues)
            ko_state = {
                "last_group_fixture": team_last_group_fixture(schedule),
                "venues": venues,
                "ko_schedule": KO_SCHEDULE,
            }
        except FileNotFoundError:
            fatigues = None
            ko_state = None
    stats = Stats(n=n_sims)
    for _ in range(n_sims):
        simulate_tournament_once(groups, rng, params, stats, results, fatigues,
                                 ko_state=ko_state)
    return stats, groups
