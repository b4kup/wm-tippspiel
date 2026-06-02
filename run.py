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

from src.model import DEFAULT_PARAMS
from src.report import build_report
from src.simulate import run


def main(argv=None):
    ap = argparse.ArgumentParser(description="2026 World Cup statistical predictor")
    ap.add_argument("--sims", type=int, default=20000,
                    help="number of Monte Carlo simulations (default 20000)")
    ap.add_argument("--seed", type=int, default=2026,
                    help="random seed for reproducibility (default 2026)")
    ap.add_argument("--out", default=os.path.join("output", "predictions.md"),
                    help="output Markdown path (default output/predictions.md)")
    args = ap.parse_args(argv)

    print(f"Simulating the 2026 World Cup {args.sims:,} times "
          f"(seed {args.seed})...")
    t0 = time.time()
    stats, groups = run(args.sims, DEFAULT_PARAMS, seed=args.seed)
    elapsed = time.time() - t0

    report = build_report(stats, groups, args.sims, args.seed, DEFAULT_PARAMS)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)

    # Console summary.
    top = sorted(((n, stats.prob(stats.champion, n)) for g in groups.values()
                  for n in (t.name for t in g)),
                 key=lambda kv: kv[1], reverse=True)[:10]
    print(f"\nDone in {elapsed:.1f}s. Report written to {args.out}\n")
    print("Top 10 title contenders:")
    for i, (name, p) in enumerate(top, 1):
        print(f"  {i:2d}. {name:<16} {p*100:5.1f}%")


if __name__ == "__main__":
    main()
