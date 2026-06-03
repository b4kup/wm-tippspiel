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


def test_travel_module_basic():
    from src.travel import (compute_match_fatigues, haversine_km,
                            ALTITUDE_ACCLIMATED_TEAMS, fatigue_score, lookup_fatigue)
    # Haversine sanity: NYC ↔ LA ≈ 3950 km (great-circle).
    assert 3800 < haversine_km(40.81, -74.07, 33.95, -118.34) < 4100
    fs = compute_match_fatigues()
    assert len(fs) == 72                              # group-stage matches
    # Mexico City opener: Mexico (acclimated) has 0 altitude; South Africa
    # (lowland) gets a 740 m altitude penalty.
    pair = lookup_fatigue(fs, "Mexico", "South Africa")
    assert pair is not None
    mex, sa = pair
    assert mex.altitude_excess_m == 0
    assert sa.altitude_excess_m > 700
    assert "Mexico" in ALTITUDE_ACCLIMATED_TEAMS
    # Lookup order-independence.
    pair2 = lookup_fatigue(fs, "South Africa", "Mexico")
    assert pair2[0] is sa and pair2[1] is mex


def test_fatigue_differential_in_expected_goals():
    # If team_a is more tired than team_b, team_a's goals go down and team_b's
    # up. Symmetric fatigue is a no-op.
    teams = {t.name: t for t in load_teams()}
    base = expected_goals(teams["Spain"], teams["Haiti"], DEFAULT_PARAMS)
    tired_a = expected_goals(teams["Spain"], teams["Haiti"], DEFAULT_PARAMS,
                             fatigue_a=0.05, fatigue_b=0.0)
    assert tired_a[0] < base[0]
    assert tired_a[1] > base[1]
    sym = expected_goals(teams["Spain"], teams["Haiti"], DEFAULT_PARAMS,
                        fatigue_a=0.03, fatigue_b=0.03)
    assert abs(sym[0] - base[0]) < 1e-9
    assert abs(sym[1] - base[1]) < 1e-9


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


def test_results_scoring_and_conditioning():
    from src.results import MatchResult, Results, update_ratings
    from src.tippspiel import PRESETS
    from src.liveupdate import score_our_tips, calibration
    from src.model import DEFAULT_PARAMS
    teams = load_teams()
    res = Results([MatchResult("group", "Spain", "Uruguay", 3, 0)])
    rule = PRESETS["check24"]

    # Tip 2-1 on a 3-0 result: correct winner, wrong difference -> 2 pts.
    scored, total = score_our_tips([("group", "Spain", "Uruguay", 2, 1)], res, rule)
    assert total == 2 and len(scored) == 1

    # Calibration runs and is in range.
    c = calibration(teams, res, DEFAULT_PARAMS)
    assert c.n == 1 and 0.0 <= c.tendency_acc <= 1.0 and c.brier >= 0.0

    # Re-tuning: a big Spain win lifts Spain's Elo/attack and drops Uruguay's.
    by = {t.name: t for t in teams}
    tuned = {t.name: t for t in update_ratings(teams, res)}
    assert tuned["Spain"].elo > by["Spain"].elo
    assert tuned["Spain"].attack > by["Spain"].attack
    assert tuned["Uruguay"].elo < by["Uruguay"].elo


def test_injuries_layer_adjusts_ratings():
    from src.injuries import Injury, apply_injuries, load_injuries, team_adjustments

    # The shipped tracker loads and every team named is a real World Cup side.
    injuries = load_injuries()
    assert injuries, "expected data/injuries.csv to contain absences"
    valid = {t.name for t in load_teams(injuries=False)}
    assert all(i.team in valid for i in injuries), "unknown team in injuries.csv"

    # A forward out dents attack and barely touches defence; a keeper out
    # worsens defence and barely touches attack. Direction matters.
    fwd = team_adjustments([Injury("X", "Striker", "FWD", "star", "out")])["X"]
    assert fwd.attack_mult < 1.0 and fwd.defense_mult > 1.0
    assert (1 - fwd.attack_mult) > (fwd.defense_mult - 1)        # attack hit larger
    gk = team_adjustments([Injury("X", "Keeper", "GK", "star", "out")])["X"]
    assert gk.attack_mult == 1.0 and gk.defense_mult > 1.0

    # A "doubtful" player counts for less than the same player "out".
    out = team_adjustments([Injury("X", "P", "MID", "key", "out")])["X"]
    doubt = team_adjustments([Injury("X", "P", "MID", "key", "doubtful")])["X"]
    assert out.attack_mult < doubt.attack_mult < 1.0

    # Applying the layer weakens an affected side; toggling it off restores it.
    full = {t.name: t for t in load_teams(injuries=False)}
    hurt = {t.name: t for t in apply_injuries(list(full.values()),
                                              [Injury("Spain", "Yamal", "FWD",
                                                      "star", "out")])}
    assert hurt["Spain"].attack < full["Spain"].attack
    assert hurt["Spain"].elo < full["Spain"].elo
    # Unaffected teams are untouched.
    assert hurt["Haiti"].attack == full["Haiti"].attack


def test_load_teams_injuries_toggle():
    # The default load applies injuries, so at least one shipped side is weaker
    # than its full-strength rating; --no-injuries restores it exactly.
    full = {t.name: t for t in load_teams(injuries=False)}
    adj = {t.name: t for t in load_teams()}
    assert any(adj[n].attack < full[n].attack - 1e-9 or
               adj[n].defense > full[n].defense + 1e-9 for n in full)
    assert adj["Brazil"].attack < full["Brazil"].attack    # Rodrygo & co. out


def test_conditioning_uses_real_group_score():
    import random
    from src.results import MatchResult, Results
    from src.tournament import groups_from_teams, play_group
    from src.model import DEFAULT_PARAMS
    groups = groups_from_teams(load_teams())
    res = Results([MatchResult("group", "Spain", "Uruguay", 5, 0)])
    rows = play_group(groups["H"], random.Random(1), DEFAULT_PARAMS, res)
    spain = next(r for r in rows if r.team.name == "Spain")
    uruguay = next(r for r in rows if r.team.name == "Uruguay")
    assert spain.gf >= 5 and uruguay.ga >= 5     # the real 5-0 is included


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all tests passed")
