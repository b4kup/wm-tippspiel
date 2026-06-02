"""
Smoke tests for the World Cup predictor. Run with:  python -m pytest -q
(or plain `python tests/test_model.py`).
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.bracket import ROUND_OF_32, N_THIRD_PLACE, is_third, third_allowed_groups
from src.model import DEFAULT_PARAMS, _sample_goals, expected_goals, win_expectancy
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
    thirds = sum(1 for tie in ROUND_OF_32 for slot in tie if is_third(slot))
    assert thirds == N_THIRD_PLACE == 8
    # A third-place slot never admits its tie-mate winner's own group.
    for a, b in ROUND_OF_32:
        if is_third(b):
            assert a[0] == "1" and a[1] not in third_allowed_groups(b)


def test_expected_goals_favour_stronger_team():
    teams = {t.name: t for t in load_teams()}
    la, lb = expected_goals(teams["Spain"], teams["Haiti"])
    assert la > lb
    assert la > 2.0          # strong attack vs weak defence -> many goals
    assert lb < la


def test_win_expectancy_monotonic():
    assert win_expectancy(2000, 1700) > 0.5
    assert abs(win_expectancy(1800, 1800) - 0.5) < 1e-9


def test_dixon_coles_lifts_low_scores():
    # Negative rho should produce more 0-0 / 1-1 draws than independent Poisson.
    la = lb = 1.3
    n = 40000

    def low_draw_rate(rho):
        r = random.Random(3)
        hits = 0
        for _ in range(n):
            x, y = _sample_goals(la, lb, r, rho)
            if (x, y) in ((0, 0), (1, 1)):
                hits += 1
        return hits / n
    assert low_draw_rate(-0.12) > low_draw_rate(0.0)


def test_scoring_rule_points():
    from src.tippspiel import PRESETS, ScoringRule, points
    r = ScoringRule()  # 4 / 3 / 2
    assert points((2, 1), (2, 1), r) == 4          # exact
    assert points((3, 2), (2, 1), r) == 3          # same +1 difference
    assert points((3, 0), (2, 1), r) == 2          # home win, wrong difference
    assert points((0, 1), (2, 1), r) == 0          # wrong tendency
    assert points((2, 2), (1, 1), r) == 2          # draw, non-exact -> tendency
    assert points((2, 2), (1, 1), ScoringRule(diff_applies_to_draws=True)) == 3
    # CHECK24: 4/3/2; exact draw -> 4; non-exact correct draw -> 3 (right
    # tendency AND goal difference); right winner with wrong difference -> 2.
    c = PRESETS["check24"]
    assert (c.exact, c.diff, c.tendency) == (4, 3, 2)
    assert points((1, 1), (1, 1), c) == 4
    assert points((2, 2), (1, 1), c) == 3
    assert points((3, 0), (2, 1), c) == 2


def test_optimal_tip_is_ev_maximal():
    from src.tippspiel import (ScoringRule, optimal_tip, points,
                               score_distribution)
    teams = {t.name: t for t in load_teams()}
    rule = ScoringRule()
    grid = score_distribution(teams["Spain"], teams["Haiti"])
    tip, ev = optimal_tip(grid, rule)
    n = len(grid)
    # No other candidate tip beats the reported expected value.
    for tx in range(7):
        for ty in range(7):
            alt = sum(grid[ax][ay] * points((tx, ty), (ax, ay), rule)
                      for ax in range(n) for ay in range(n))
            assert alt <= ev + 1e-9
    # A strong favourite should be tipped to win.
    assert tip[0] > tip[1]


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
