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
LG_AVG = 1.5972    # tuned by tune.py against 2018/2022 backtest
K_Q = 0.8155       # tuned by tune.py against 2018/2022 backtest
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
    # Try the proper Maher-Poisson fit on match-level data first (best).
    # Fall back to the aggregate qualifying-goals blend, then to Elo-only.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    poisson_fit_table = None
    # Shrinkage to Elo prior. Higher = more shrinkage. We picked 25 because
    # cross-confederation matches in the dataset are sparse (mostly Copa America
    # 2024 hosting CONCACAF guests); without strong inter-confed bridges, the
    # fit over-credits AFC/CAF/OFC teams playing weak intra-confed opposition.
    # The Elo prior carries that cross-confederation signal by hand.
    poisson_n_prior = 25.0
    try:
        from src.poisson_fit import load_matches, fit_poisson, shrink_to_prior
        matches_path = os.path.join(os.path.dirname(__file__), "matches_recent.csv")
        if os.path.exists(matches_path):
            matches = load_matches(matches_path)
            # Date-level exponential time-decay (preferred over the year-
            # bucket weighting). 18-month half-life matches the typical
            # international-football turnover: a campaign-cycle ago is
            # worth ~50%, two cycles ago ~25%. Tighter than the previous
            # bucket schedule, smoother across calendar boundaries.
            fitted, _gamma = fit_poisson(matches, half_life_days=540,
                                         ref_date="2026-06-03",
                                         max_iter=400, tol=1e-6)
            poisson_fit_table = fitted
    except Exception:
        poisson_fit_table = None

    qual_records = None
    qual_blend = None
    if poisson_fit_table is None:
        try:
            # Prefer xG-based blend when an xG qualifying table has been
            # supplied (see src/xg_fit.py for the file format and why).
            from src.xg_fit import load_xg, blend as xg_blend
            xg_records = load_xg()
            if xg_records:
                qual_records = xg_records
                qual_blend = xg_blend
        except Exception:
            qual_records = None
        if qual_records is None:
            try:
                from src.qualifying_fit import load_qualifying, blend as q_blend
                qual_records = load_qualifying()
                qual_blend = q_blend
            except Exception:
                pass

    # Per-confederation log-offsets calibrated from cross-confed match
    # history (Elo prior alone is biased when confederations don't play
    # each other often). Falls back to all-zero offsets if data missing.
    confed_offsets = {}
    try:
        from src.confederation_fit import fit_offsets
        confed_offsets = fit_offsets(lg_avg=LG_AVG, k_q=K_Q)
    except Exception:
        confed_offsets = {}

    rows = []
    for name, (group, confed, elo, style, odds, poly) in TEAMS.items():
        q = (elo - elo_avg) / 400.0
        co = confed_offsets.get(confed)
        a_shift = co.alpha_offset if co else 0.0
        d_shift = co.delta_offset if co else 0.0
        attack_prior = LG_AVG * math.exp(K_Q * q + K_STYLE * style + a_shift)
        defense_prior = LG_AVG * math.exp(-K_Q * q + K_STYLE * style - d_shift)

        if poisson_fit_table is not None and name in poisson_fit_table:
            ft = poisson_fit_table[name]
            # Convert Elo prior to log-space (the natural fit space).
            alpha_prior = math.log(max(attack_prior / LG_AVG, 1e-6))
            delta_prior = -math.log(max(defense_prior / LG_AVG, 1e-6))
            alpha, delta = shrink_to_prior(
                ft.alpha, ft.delta, ft.matches,
                alpha_prior, delta_prior, n_prior=poisson_n_prior)
            attack = LG_AVG * math.exp(alpha)
            defense = LG_AVG * math.exp(-delta)
        elif qual_blend is not None and qual_records:
            attack, defense = qual_blend(name, attack_prior, defense_prior,
                                         qual_records, LG_AVG)
        else:
            attack, defense = attack_prior, defense_prior

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
