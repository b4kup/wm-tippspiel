"""
Smoke tests for the World Cup predictor. Run with:  python -m pytest -q
(or plain `python tests/test_model.py`).
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.bracket import ROUND_OF_32, N_THIRD_PLACE
from src.model import DEFAULT_PARAMS, expected_goals, win_expectancy
from src.simulate import run
from src.tournament import groups_from_teams, load_teams


def test_teams_loaded():
    teams = load_teams()
    assert len(teams) == 48
    groups = groups_from_teams(teams)
    assert len(groups) == 12
    assert all(len(g) == 4 for g in groups.values())


def test_bracket_well_formed():
    assert len(ROUND_OF_32) == 16
    thirds = sum(1 for tie in ROUND_OF_32 for slot in tie if slot == "3")
    assert thirds == N_THIRD_PLACE == 8


def test_expected_goals_favour_stronger_team():
    teams = {t.name: t for t in load_teams()}
    la, lb = expected_goals(teams["Spain"], teams["Haiti"])
    assert la > lb
    assert la > 2.0          # strong attack vs weak defence -> many goals
    assert lb < la


def test_win_expectancy_monotonic():
    assert win_expectancy(2000, 1700) > 0.5
    assert abs(win_expectancy(1800, 1800) - 0.5) < 1e-9


def test_probabilities_are_consistent():
    stats, groups = run(400, DEFAULT_PARAMS, seed=1)
    names = [t.name for g in groups.values() for t in g]
    # Champion probabilities sum to 1 across all teams.
    total = sum(stats.champion[n] for n in names)
    assert total == stats.n
    # Reaching the final is at least as likely as winning, for every team.
    for n in names:
        assert stats.reach_final[n] >= stats.champion[n]
        assert stats.reach_sf[n] >= stats.reach_final[n]
    # A top side should be among the favourites.
    champ_sorted = sorted(names, key=lambda n: stats.champion[n], reverse=True)
    assert champ_sorted[0] in {"Spain", "France", "Argentina", "England",
                               "Brazil", "Portugal", "Germany", "Netherlands"}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all tests passed")
