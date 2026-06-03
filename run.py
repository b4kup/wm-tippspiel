#!/usr/bin/env python3
"""
Run the 2026 World Cup Monte Carlo predictor and write a Markdown report.

Examples:
    python run.py                       # 20,000 sims -> output/predictions.md
    python run.py --sims 100000         # more sims, tighter probabilities
    python run.py --seed 7 --out my.md  # reproducible run, custom output
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Allow running as a plain script (python run.py) as well as a module.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataclasses import replace

from src.injuries import load_injuries
from src.model import DEFAULT_PARAMS
from src.report import build_report
from src.results import load_results, update_ratings
from src.simulate import run
from src.tournament import load_teams


def main(argv=None):
    ap = argparse.ArgumentParser(description="2026 World Cup statistical predictor")
    ap.add_argument("--sims", type=int, default=20000,
                    help="number of Monte Carlo simulations (default 20000)")
    ap.add_argument("--seed", type=int, default=2026,
                    help="random seed for reproducibility (default 2026)")
    ap.add_argument("--rating-sigma", type=float, default=None,
                    help="std-dev (Elo) of per-tournament team strength; "
                         "0 disables uncertainty (default %d)"
                         % DEFAULT_PARAMS.rating_sigma_elo)
    ap.add_argument("--dc-rho", type=float, default=None,
                    help="Dixon-Coles low-score correlation; 0 disables it "
                         "(default %g)" % DEFAULT_PARAMS.dc_rho)
    ap.add_argument("--no-injuries", action="store_true",
                    help="ignore data/injuries.csv and run every team at full "
                         "strength (default: apply the availability layer)")
    ap.add_argument("--results", default=os.path.join("data", "results.csv"),
                    help="path to results CSV (re-tune ratings + condition the "
                         "simulation on played matches; default data/results.csv)")
    ap.add_argument("--no-results", action="store_true",
                    help="ignore data/results.csv entirely (pre-tournament view)")
    ap.add_argument("--out", default=os.path.join("output", "predictions.md"),
                    help="output Markdown path (default output/predictions.md)")
    ap.add_argument("--html", default=os.path.join("output", "dashboard.html"),
                    help="output interactive dashboard HTML path "
                         "(default output/dashboard.html)")
    ap.add_argument("--no-html", action="store_true",
                    help="skip the interactive HTML dashboard")
    args = ap.parse_args(argv)

    params = DEFAULT_PARAMS
    if args.rating_sigma is not None:
        params = replace(params, rating_sigma_elo=args.rating_sigma)
    if args.dc_rho is not None:
        params = replace(params, dc_rho=args.dc_rho)

    injuries = [] if args.no_injuries else load_injuries()
    teams = load_teams(injuries=not args.no_injuries)

    results = None if args.no_results else load_results(args.results)
    n_results = len(results) if results is not None else 0
    if n_results:
        teams = update_ratings(teams, results)

    print(f"Simulating the 2026 World Cup {args.sims:,} times "
          f"(seed {args.seed}, rating σ {params.rating_sigma_elo:g} Elo"
          + (", injuries off" if args.no_injuries else
             f", {len(injuries)} injuries applied")
          + (f", {n_results} results applied" if n_results else "") + ")...")
    t0 = time.time()
    stats, groups = run(args.sims, params, seed=args.seed, teams=teams,
                        results=results)
    elapsed = time.time() - t0

    report = build_report(stats, groups, args.sims, args.seed, params,
                          injuries=injuries, n_results=n_results)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)

    if not args.no_html:
        from src.dashboard import build_dashboard_html
        html = build_dashboard_html(stats, groups, params, args.sims, args.seed,
                                    n_results=n_results)
        os.makedirs(os.path.dirname(os.path.abspath(args.html)), exist_ok=True)
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(html)

    # Console summary.
    top = sorted(((n, stats.prob(stats.champion, n)) for g in groups.values()
                  for n in (t.name for t in g)),
                 key=lambda kv: kv[1], reverse=True)[:10]
    print(f"\nDone in {elapsed:.1f}s. Report written to {args.out}")
    if not args.no_html:
        print(f"Interactive dashboard at {args.html}")
    print()
    print("Top 10 title contenders:")
    for i, (name, p) in enumerate(top, 1):
        print(f"  {i:2d}. {name:<16} {p*100:5.1f}%")


if __name__ == "__main__":
    main()
