#!/usr/bin/env python3
"""
Live update for the 2026 World Cup Tippspiel.

As results come in (recorded in data/results.csv), this:
  * scores our submitted tips (data/our_tips.csv) under the CHECK24 rules,
  * checks how well reality matched our pre-tournament predictions,
  * re-tunes team ratings from observed form and re-simulates the rest of the
    tournament conditioned on what's happened,
  * re-optimizes the tips for upcoming, not-yet-played group matches.

Examples:
    python update.py                      # safe tips -> output/live_status.md
    python update.py --risk aggressive    # chase 4-pointers when behind
"""

from __future__ import annotations

import argparse
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.liveupdate import (build_live_report, calibration, group_tips,
                            load_our_tips, save_our_tips, score_our_tips)
from src.model import DEFAULT_PARAMS
from src.results import GROUP, load_results, update_ratings
from src.tippspiel import (PRESETS, most_likely_score, optimal_tip,
                           outcome_probs, score_distribution)
from src.tournament import groups_from_teams, load_teams

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def remaining_group_tips(groups, results, rule, params, risk):
    """(team_a, team_b, tip, (pw,pd,pl)) for each not-yet-played group match.

    `risk` mirrors `tipps.py`: safe (EV-optimal), aggressive (most likely
    exact score), contrarian (EV with a small crowd-overlap penalty)."""
    out = []
    for teams in groups.values():
        for a, b in combinations(teams, 2):
            if results.group_score(a.name, b.name) is not None:
                continue  # already played
            grid = score_distribution(a, b, params)
            tip, _ev = optimal_tip(grid, rule, risk=risk)
            out.append((a.name, b.name, tip, outcome_probs(grid)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Live Tippspiel update")
    ap.add_argument("--preset", default="check24", choices=sorted(PRESETS),
                    help="scoring preset (default check24)")
    ap.add_argument("--risk", default="safe",
                    choices=("safe", "aggressive", "contrarian"),
                    help="tip strategy for upcoming matches. safe = pure EV "
                         "(default); aggressive = chase exact scores when "
                         "trailing; contrarian = EV with a small crowd-overlap "
                         "penalty to gain differentiation in a tied pool")
    ap.add_argument("--sims", type=int, default=30000)
    ap.add_argument("--no-injuries", action="store_true",
                    help="ignore data/injuries.csv (full-strength ratings)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--results", default=os.path.join(DATA_DIR, "results.csv"))
    ap.add_argument("--tips", default=os.path.join(DATA_DIR, "our_tips.csv"))
    ap.add_argument("--out", default=os.path.join("output", "live_status.md"))
    ap.add_argument("--no-notify", action="store_true",
                    help="skip tip-change detection / notifications.json")
    ap.add_argument("--no-auto-tips", action="store_true",
                    help="log notifications but do NOT auto-update our_tips.csv")
    args = ap.parse_args(argv)

    rule = PRESETS[args.preset]
    teams = load_teams(injuries=not args.no_injuries)
    results = load_results(args.results)
    groups_base = groups_from_teams(teams)

    # Frozen tips: generate from the base model on first run so there's always
    # something to score (you then commit/freeze data/our_tips.csv).
    our_tips = load_our_tips(args.tips)
    if not our_tips:
        our_tips = group_tips(groups_base, rule, DEFAULT_PARAMS)
        save_our_tips(args.tips, our_tips)
        print(f"No tips found — generated and saved frozen group tips to {args.tips}")

    print(f"{len(results)} results loaded. Scoring tips and re-simulating...")
    scored, total = score_our_tips(our_tips, results, rule)
    calib = calibration(teams, results, DEFAULT_PARAMS)

    # Re-tune ratings from results, then re-simulate the remainder conditioned
    # on what has actually happened.
    tuned = update_ratings(teams, results)
    from src.simulate import run
    stats, _ = run(args.sims, DEFAULT_PARAMS, seed=args.seed,
                   teams=tuned, results=results)
    names = [t.name for t in tuned]
    champion_top = sorted(((n, stats.prob(stats.champion, n)) for n in names),
                          key=lambda kv: kv[1], reverse=True)

    groups_tuned = groups_from_teams(tuned)
    remaining = remaining_group_tips(groups_tuned, results, rule,
                                     DEFAULT_PARAMS, args.risk)

    # Detect recommendation changes and (optionally) sync our frozen tips.
    # Notifications always track the *safe* recommendation so the alert feed is
    # stable regardless of --risk.
    if not args.no_notify:
        from src.notify import sync_and_notify
        safe_remaining = remaining_group_tips(groups_tuned, results, rule,
                                              DEFAULT_PARAMS, "safe")
        group_of = {t.name: t.group for t in tuned}
        new_notifs = sync_and_notify(safe_remaining, args.tips, results,
                                     group_of=group_of,
                                     auto_update=not args.no_auto_tips)
        for n in new_notifs:
            print(f"  📣 {n['match']}: {n['old'][0]}–{n['old'][1]} → "
                  f"{n['new'][0]}–{n['new'][1]}")
        if new_notifs:
            verb = ("logged" if args.no_auto_tips
                    else "logged + our_tips.csv updated")
            print(f"{len(new_notifs)} tip change(s) {verb}")
        # Re-load tips so the live report reflects any auto-update.
        if new_notifs and not args.no_auto_tips:
            our_tips = load_our_tips(args.tips)
            scored, total = score_our_tips(our_tips, results, rule)

    report = build_live_report(results, rule, scored, total, calib,
                               champion_top, remaining, args.risk)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)

    print(f"\nTippspiel score: {total} pts from {len(scored)} matches")
    if calib.n:
        print(f"Prediction accuracy: {calib.tendency_acc*100:.0f}% tendency, "
              f"Brier {calib.brier:.3f}")
    print(f"Updated favourite: {champion_top[0][0]} "
          f"({champion_top[0][1]*100:.1f}%)")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
