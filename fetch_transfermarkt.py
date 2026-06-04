#!/usr/bin/env python3
"""
Fetch a Transfermarkt squad page and print the parsed squad table.

    python fetch_transfermarkt.py \\
        --url https://www.transfermarkt.com/spanien/startseite/verein/3375 \\
        --team Spain

Use this to audit `data/injuries.csv` against the live Transfermarkt
listing for that nation. Players flagged with an injury note here
should appear (or be considered) in `data/injuries.csv`.

The parser is best-effort; cross-check critical entries against the
website before committing changes.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.transfermarkt import try_fetch


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True,
                    help="Transfermarkt team URL (Verein page)")
    ap.add_argument("--team", required=True,
                    help="canonical team name (matches data/teams.csv)")
    args = ap.parse_args(argv)

    rows = try_fetch(args.url)
    if not rows:
        print(f"no rows parsed from {args.url} — page format may have changed",
              file=sys.stderr)
        return 1

    print(f"# {args.team} — squad from Transfermarkt ({len(rows)} players)")
    print()
    print("| Player | Position | Market value (€) | Note |")
    print("|--------|----------|----------------:|:-----|")
    for r in rows:
        mv = f"€{r.market_value_eur:,.0f}" if r.market_value_eur else "—"
        print(f"| {r.name} | {r.position} | {mv} | {r.injury_note or ''} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
