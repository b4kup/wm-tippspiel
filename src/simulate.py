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

    def prob(self, counter: dict, name: str) -> float:
        return counter[name] / self.n if self.n else 0.0


def simulate_tournament_once(groups, rng, p, stats: Stats, results=None):
    winners_by_group, runners_by_group = {}, {}
    third_entries = []  # (group_letter, Team)

    # Sample each team's true strength for this tournament (rating uncertainty
    # + form). Done once per simulation so a team's bonus persists across all
    # its matches, which is what produces realistic deep runs and upsets.
    if p.rating_sigma_elo > 0:
        groups = {letter: [perturb_team(t, p.rating_sigma_elo, rng) for t in teams]
                  for letter, teams in groups.items()}

    for letter, teams in groups.items():
        table = play_group(teams, rng, p, results)
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

    reached = run_knockout(ties, rng, p, results)
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
        teams: list[Team] | None = None, results=None) -> tuple[Stats, dict]:
    from .tournament import load_teams
    rng = random.Random(seed)
    teams = teams or load_teams()
    groups = groups_from_teams(teams)
    stats = Stats(n=n_sims)
    for _ in range(n_sims):
        simulate_tournament_once(groups, rng, params, stats, results)
    return stats, groups
