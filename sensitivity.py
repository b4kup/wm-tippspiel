#!/usr/bin/env python3
"""
CLI: run the sensitivity analysis over key model parameters and write
a Markdown tornado report to `output/sensitivity.md`.

    python sensitivity.py                       # 5000 sims, top 8 teams
    python sensitivity.py --sims 10000 --top 6  # tighter, fewer teams
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.sensitivity import render_report, run_sensitivity


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sims", type=int, default=5000,
                    help="Monte Carlo sims per perturbation (default 5000)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--top", type=int, default=8,
                    help="number of teams to render in the report (default 8)")
    ap.add_argument("--out", default=os.path.join("output", "sensitivity.md"))
    args = ap.parse_args(argv)

    print(f"Running sensitivity sweep ({args.sims:,} sims per axis)...")
    t0 = time.time()
    results = run_sensitivity(n_sims=args.sims, seed=args.seed,
                              top_k=args.top)
    report = render_report(results)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"Done in {time.time() - t0:.1f}s. Report written to {args.out}")


if __name__ == "__main__":
    main()
