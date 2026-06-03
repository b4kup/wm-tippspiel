"""
Generate per-team ATTACK and DEFENSE ratings for the match model and write
data/teams.csv.

Why attack/defense instead of a single Elo number
--------------------------------------------------
A single strength number cannot tell apart a 3-2 team and a 1-0 team of equal
overall quality. Real matches are decided by a *style matchup*: one side's
attack against the other side's defence. So every team gets two ratings:

    attack  = expected goals it SCORES against an average World Cup team
    defense = expected goals it CONCEDES against an average World Cup team

(lower `defense` = better defence). In a match these combine multiplicatively
(see src/model.py): a sharp attack meeting a leaky defence produces goals,
while two defensive sides grind out a low-scoring game.

How the two numbers are derived (transparent + reproducible)
------------------------------------------------------------
Each team starts from two inputs that are easy to source and audit:

  1. ELO  - overall strength snapshot (June 2026), cross-checked against
            eloratings.net ordering, worldfootballrankings.com and the
            betting market. Sets HOW GOOD a team is.
  2. STYLE - an offensive/defensive tilt in roughly [-0.4, +0.3], informed by
            each team's playing identity and 2026 qualifying goal record.
            Positive = open/attacking (scores more, concedes more);
            negative = compact/defensive (scores less, concedes less).
            Sets HOW a team's quality is split between attack and defence.

    attack_i  = LG_AVG * exp( + K_Q * (elo_i - elo_avg)/400 + K_STYLE * style_i )
    defense_i = LG_AVG * exp( - K_Q * (elo_i - elo_avg)/400 + K_STYLE * style_i )

LG_AVG is the average goals one team scores in a match (~1.35, i.e. ~2.7 per
game). The quality term moves attack up and defence down together; the style
term moves both the same way (attacking sides also leak more).

Run `python -m data.derive_ratings` to regenerate data/teams.csv.
"""

from __future__ import annotations

import csv
import math
import os

# Calibration constants (documented in src/model.py too).
LG_AVG = 1.35      # average goals scored by one team per match
K_Q = 0.70         # how strongly Elo quality separates attack/defence
K_STYLE = 0.50     # how strongly style tilts attack vs defence

# team -> (group, confederation, elo, style, market_decimal_odds, polymarket_prob)
# Elo is an eloratings.net-style scale (top ~2090). Style: + attacking / - defensive.
# market_decimal_odds: bookmaker consensus (n-tv.de).
# polymarket_prob: real-money implied probability (%). None when no liquid market.
# Refreshed 2026-06-03 against eloratings.net, worldfootballrankings.com,
# Wikipedia qualifying campaigns, n-tv.de, Polymarket.
TEAMS = {
    # Group A
    "Mexico":              ("A", "CONCACAF", 1855, 0.00, 81,   None),
    "South Africa":        ("A", "CAF",      1700, 0.00, None, None),
    "South Korea":         ("A", "AFC",      1760, 0.10, 251,  None),
    "Czechia":             ("A", "UEFA",     1740, 0.00, None, None),
    # Group B
    "Canada":              ("B", "CONCACAF", 1795, 0.10, 251,  None),
    "Bosnia & Herzegovina":("B", "UEFA",     1760, 0.10, None, None),
    "Qatar":               ("B", "AFC",      1690, 0.00, None, None),
    "Switzerland":         ("B", "UEFA",     1890, -0.20, 66,  None),
    # Group C
    "Brazil":              ("C", "CONMEBOL", 1990, 0.30, 9,    8.4),
    "Morocco":             ("C", "CAF",      1870, -0.20, 51,  None),
    "Haiti":               ("C", "CONCACAF", 1640, 0.10, None, None),
    "Scotland":            ("C", "UEFA",     1780, 0.00, 151,  None),
    # Group D
    "United States":       ("D", "CONCACAF", 1755, 0.10, 63,   None),
    "Paraguay":            ("D", "CONMEBOL", 1800, -0.30, None, None),
    "Australia":           ("D", "AFC",      1770, -0.10, 201, None),
    "Türkiye":             ("D", "UEFA",     1880, 0.25, 67,   None),
    # Group E
    "Germany":             ("E", "UEFA",     1925, 0.25, 15,   5.6),
    "Curaçao":             ("E", "CONCACAF", 1610, 0.00, None, None),
    "Ivory Coast":         ("E", "CAF",      1700, 0.10, 201,  None),
    "Ecuador":             ("E", "CONMEBOL", 1910, -0.20, 101, None),
    # Group F
    "Netherlands":         ("F", "UEFA",     1960, 0.20, 22,   3.9),
    "Japan":               ("F", "AFC",      1890, 0.10, 52,   None),
    "Sweden":              ("F", "UEFA",     1720, 0.00, 151,  None),
    "Tunisia":             ("F", "CAF",      1640, -0.30, None, None),
    # Group G
    "Belgium":             ("G", "UEFA",     1890, 0.20, 34,   1.9),
    "Egypt":               ("G", "CAF",      1700, -0.10, 151, None),
    "IR Iran":             ("G", "AFC",      1770, -0.20, 251, None),
    "New Zealand":         ("G", "OFC",      1590, -0.10, None, None),
    # Group H
    "Spain":               ("H", "UEFA",     2090, 0.20, 5.5,  16.1),
    "Cabo Verde":          ("H", "CAF",      1580, -0.10, None, None),
    "Saudi Arabia":        ("H", "AFC",      1580, 0.00, None, None),
    "Uruguay":             ("H", "CONMEBOL", 1850, -0.20, 65,  None),
    # Group I
    "France":              ("I", "UEFA",     2080, 0.10, 5.75, 17.0),
    "Senegal":             ("I", "CAF",      1865, 0.00, 81,   None),
    "Iraq":                ("I", "AFC",      1610, -0.20, None, None),
    "Norway":              ("I", "UEFA",     1750, 0.30, 29,   None),
    # Group J
    "Argentina":           ("J", "CONMEBOL", 2095, 0.10, 9,    9.0),
    "Algeria":             ("J", "CAF",      1770, 0.10, 151,  None),
    "Austria":             ("J", "UEFA",     1830, 0.10, 101,  None),
    "Jordan":              ("J", "AFC",      1685, -0.20, None, None),
    # Group K
    "Portugal":            ("K", "UEFA",     1985, 0.25, 12,   9.5),
    "DR Congo":            ("K", "CAF",      1680, 0.10, None, None),
    "Uzbekistan":          ("K", "AFC",      1720, -0.10, None, None),
    "Colombia":            ("K", "CONMEBOL", 1960, 0.00, 36,   0.7),
    # Group L
    "England":             ("L", "UEFA",     2020, 0.00, 7.5,  11.1),
    "Croatia":             ("L", "UEFA",     1910, -0.10, 67,  None),
    "Ghana":               ("L", "CAF",      1740, 0.10, 151,  None),
    "Panama":              ("L", "CONCACAF", 1735, -0.10, None, None),
}


def derive():
    elos = [v[2] for v in TEAMS.values()]
    elo_avg = sum(elos) / len(elos)
    rows = []
    for name, (group, confed, elo, style, odds, poly) in TEAMS.items():
        q = (elo - elo_avg) / 400.0
        attack = LG_AVG * math.exp(K_Q * q + K_STYLE * style)
        defense = LG_AVG * math.exp(-K_Q * q + K_STYLE * style)
        rows.append({
            "team": name,
            "group": group,
            "confederation": confed,
            "elo": elo,
            "attack": round(attack, 3),
            "defense": round(defense, 3),
            "market_decimal_odds": odds if odds is not None else "",
            "polymarket_prob": poly if poly is not None else "",
        })
    rows.sort(key=lambda r: (r["group"], -r["elo"]))
    return rows, elo_avg


def write_csv(path: str | None = None):
    rows, elo_avg = derive()
    path = path or os.path.join(os.path.dirname(__file__), "teams.csv")
    fields = ["team", "group", "confederation", "elo", "attack", "defense",
              "market_decimal_odds", "polymarket_prob"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path, elo_avg, len(rows)


if __name__ == "__main__":
    path, elo_avg, n = write_csv()
    print(f"Wrote {n} teams to {path} (mean Elo {elo_avg:.1f})")
