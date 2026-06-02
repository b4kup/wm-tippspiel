#!/usr/bin/env python3
"""
Generate point-maximizing Tippspiel tips for the 2026 World Cup group stage.

Examples:
    python tipps.py                          # kicktipp 4/3/2 -> output/tipps.md
    python tipps.py --exact 3 --diff 2 --tendency 1
    python tipps.py --diff-draws             # draws can score the diff bonus
    python tipps.py --sims 0                 # skip the outright-winner pick
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.model import DEFAULT_PARAMS
from src.simulate import run
from src.tippspiel import PRESETS, ScoringRule, build_tipps_report
from src.tournament import groups_from_teams, load_teams


def main(argv=None):
    ap = argparse.ArgumentParser(description="Point-maximizing Tippspiel tips")
    ap.add_argument("--preset", choices=sorted(PRESETS),
                    help="named scoring preset (e.g. check24); overrides the "
                         "individual point options below")
    ap.add_argument("--exact", type=int, default=4, help="points for exact score")
    ap.add_argument("--diff", type=int, default=3, help="points for goal difference")
    ap.add_argument("--tendency", type=int, default=2, help="points for tendency")
    ap.add_argument("--diff-draws", action="store_true",
                    help="count a correct non-exact draw as a goal-difference hit")
    ap.add_argument("--sims", type=int, default=20000,
                    help="sims for the outright-winner pick (0 to skip)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=os.path.join("output", "tipps.md"))
    args = ap.parse_args(argv)

    if args.preset:
        rule = PRESETS[args.preset]
    else:
        rule = ScoringRule(
            exact=args.exact, diff=args.diff, tendency=args.tendency,
            diff_applies_to_draws=args.diff_draws,
            name=f"{args.exact}/{args.diff}/{args.tendency}"
                 + (" (draws score diff)" if args.diff_draws else ""),
        )
    extra_note = ""
    if args.preset == "check24":
        extra_note = (
            "- **CHECK24 scoring:** 4 pts exact result · 3 pts right tendency **and** "
            "goal difference · 2 pts right winner only. A correct **draw** that "
            "isn't exact (e.g. tip 2-2, result 1-1) scores **3** (its tendency and "
            "goal difference are both right; the 2-pt 'winner' tier can't apply to a "
            "draw).\n"
            "- **Bonus questions** are worth **10 points** each — separate from "
            "per-match scoring, so they don't change the optimal tips above, but "
            "they're high-value: answer them.")
    teams = load_teams()
    groups = groups_from_teams(teams)

    champion_top = None
    if args.sims > 0:
        print(f"Estimating the outright winner ({args.sims:,} sims)...")
        stats, _ = run(args.sims, DEFAULT_PARAMS, seed=args.seed, teams=teams)
        names = [t.name for t in teams]
        champion_top = sorted(((n, stats.prob(stats.champion, n)) for n in names),
                              key=lambda kv: kv[1], reverse=True)

    report = build_tipps_report(groups, rule, DEFAULT_PARAMS, champion_top, extra_note)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"Wrote tips for {sum(len(g) for g in groups.values())} teams "
          f"to {args.out}")


if __name__ == "__main__":
    main()
