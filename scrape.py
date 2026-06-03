"""
Scrape match results from Wikipedia for recent international tournaments
and the 2026 World Cup qualifying campaigns. Output: data/matches_recent.csv

Used as input to `src/poisson_fit.py`, which fits attack/defense ratings
jointly via Poisson regression.

    python scrape.py             # full run
    python scrape.py --quick     # smaller set for testing
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scrape_wiki import scrape_pages, write_csv

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "matches_recent.csv")

# (tournament_label, wikipedia_slug)
PAGES_FULL: list[tuple[str, str]] = [
    # 2024 Copa America (held in USA — cross-confederation venues count)
    ("Copa America 2024", "2024_Copa_Am%C3%A9rica_Group_A"),
    ("Copa America 2024", "2024_Copa_Am%C3%A9rica_Group_B"),
    ("Copa America 2024", "2024_Copa_Am%C3%A9rica_Group_C"),
    ("Copa America 2024", "2024_Copa_Am%C3%A9rica_Group_D"),
    ("Copa America 2024", "2024_Copa_Am%C3%A9rica_knockout_stage"),

    # UEFA Euro 2024
    ("Euro 2024", "UEFA_Euro_2024_Group_A"),
    ("Euro 2024", "UEFA_Euro_2024_Group_B"),
    ("Euro 2024", "UEFA_Euro_2024_Group_C"),
    ("Euro 2024", "UEFA_Euro_2024_Group_D"),
    ("Euro 2024", "UEFA_Euro_2024_Group_E"),
    ("Euro 2024", "UEFA_Euro_2024_Group_F"),
    ("Euro 2024", "UEFA_Euro_2024_knockout_stage"),

    # 2023 Africa Cup of Nations (held Jan-Feb 2024 in Ivory Coast)
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_Group_A"),
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_Group_B"),
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_Group_C"),
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_Group_D"),
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_Group_E"),
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_Group_F"),
    ("AFCON 2023", "2023_Africa_Cup_of_Nations_knockout_stage"),

    # 2023 AFC Asian Cup (held Jan 2024 in Qatar)
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_Group_A"),
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_Group_B"),
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_Group_C"),
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_Group_D"),
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_Group_E"),
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_Group_F"),
    ("Asian Cup 2023", "2023_AFC_Asian_Cup_knockout_stage"),

    # 2025 CONCACAF Gold Cup
    ("Gold Cup 2025", "2025_CONCACAF_Gold_Cup_Group_A"),
    ("Gold Cup 2025", "2025_CONCACAF_Gold_Cup_Group_B"),
    ("Gold Cup 2025", "2025_CONCACAF_Gold_Cup_Group_C"),
    ("Gold Cup 2025", "2025_CONCACAF_Gold_Cup_Group_D"),
    ("Gold Cup 2025", "2025_CONCACAF_Gold_Cup_knockout_stage"),

    # 2026 WC qualifying — biggest sample. Note: en-dash (%E2%80%93) is the
    # canonical separator on Wikipedia for these slugs; CONMEBOL uses parens.
    ("2026 WC Q (CONMEBOL)", "2026_FIFA_World_Cup_qualification_(CONMEBOL)"),
    *[("2026 WC Q (UEFA)",
       f"2026_FIFA_World_Cup_qualification_%E2%80%93_UEFA_Group_{g}")
      for g in "ABCDEFGHIJKL"],
    ("2026 WC Q (AFC R2)",
     "2026_FIFA_World_Cup_qualification_%E2%80%93_AFC_second_round"),
    ("2026 WC Q (AFC R3)",
     "2026_FIFA_World_Cup_qualification_%E2%80%93_AFC_third_round"),
    ("2026 WC Q (CONCACAF)",
     "2026_FIFA_World_Cup_qualification_%E2%80%93_CONCACAF_third_round"),
    ("2026 WC Q (OFC)",
     "2026_FIFA_World_Cup_qualification_(OFC)"),
]

PAGES_QUICK = PAGES_FULL[:8]  # for testing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="scrape a small subset for testing")
    args = ap.parse_args()
    pages = PAGES_QUICK if args.quick else PAGES_FULL
    print(f"Scraping {len(pages)} Wikipedia pages...")
    matches = scrape_pages(pages)
    print(f"Parsed {len(matches)} unique matches.")
    by_tournament: dict[str, int] = {}
    for m in matches:
        by_tournament[m.tournament] = by_tournament.get(m.tournament, 0) + 1
    for k, v in sorted(by_tournament.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<28s} {v}")
    write_csv(matches, OUT_PATH)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
