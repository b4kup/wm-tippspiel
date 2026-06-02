"""
Point-maximizing predictions for a Tippspiel (prediction pool).

The key idea: the scoreline that maximizes your *expected points* is usually
**not** the most likely scoreline. A pool rewards getting the exact score, the
goal difference, or just the tendency (win/draw/loss) — that scoring structure
reshapes what you should pick. So for each match we:

  1. compute the full scoreline distribution P(x, y) analytically from the
     match model (attack/defense -> Poisson, with the Dixon-Coles correction);
  2. for every candidate tip, sum P(x, y) * points(tip, (x, y)) over all
     outcomes to get its expected points;
  3. pick the tip with the highest expected points.

The scoring rule is configurable to match your pool.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from itertools import combinations

from .model import DEFAULT_PARAMS, ModelParams, _dc_tau, expected_goals


@dataclass(frozen=True)
class ScoringRule:
    """Points awarded for a tip. Defaults match the classic kicktipp scheme."""
    exact: int = 4          # exact final score
    diff: int = 3           # correct (non-zero) goal difference, wrong score
    tendency: int = 2       # correct tendency only (win/draw/loss)
    # Whether a non-exact correct draw (e.g. tip 2-2, result 1-1) counts as a
    # goal-difference hit. kicktipp treats it as tendency only -> False.
    diff_applies_to_draws: bool = False
    name: str = "kicktipp (4/3/2)"


def points(pred, actual, rule: ScoringRule) -> int:
    """Points for tipping `pred` when the result is `actual`."""
    if pred == actual:
        return rule.exact
    pt = (pred[0] > pred[1]) - (pred[0] < pred[1])      # -1 / 0 / +1
    at = (actual[0] > actual[1]) - (actual[0] < actual[1])
    if pt != at:
        return 0
    if pt == 0:  # both draws, but not exact
        return rule.diff if rule.diff_applies_to_draws else rule.tendency
    if pred[0] - pred[1] == actual[0] - actual[1]:
        return rule.diff
    return rule.tendency


# Named scoring presets. CHECK24: 4 (exact) / 3 (right tendency AND goal
# difference) / 2 (right winner only). The 2-point tier is "richtiger Gewinner",
# which only exists for a non-draw; a correct but non-exact DRAW has the right
# tendency and the right goal difference (0), so it scores 3 -> diff applies to
# draws. Bonus questions (10 pts each) are separate from per-match scoring and
# so don't change the optimal per-match tip.
PRESETS = {
    "check24": ScoringRule(
        exact=4, diff=3, tendency=2, diff_applies_to_draws=True,
        name="CHECK24 (4 exact / 3 tendency+goal-diff / 2 winner)"),
    "kicktipp": ScoringRule(name="kicktipp (4/3/2)"),
}


def score_distribution(team_a, team_b, p: ModelParams = DEFAULT_PARAMS,
                       max_goals: int = 8):
    """Analytic joint scoreline pmf P[x][y] over 0..max_goals, normalised."""
    la, lb = expected_goals(team_a, team_b, p)

    def pois(k, lam):
        return math.exp(-lam) * lam ** k / math.factorial(k)

    px = [pois(k, la) for k in range(max_goals + 1)]
    py = [pois(k, lb) for k in range(max_goals + 1)]
    grid = [[px[x] * py[y] * _dc_tau(x, y, la, lb, p.dc_rho)
             for y in range(max_goals + 1)] for x in range(max_goals + 1)]
    total = sum(v for row in grid for v in row)
    return [[v / total for v in row] for row in grid]


def outcome_probs(grid):
    """Return (P(home win), P(draw), P(away win)) from a scoreline grid."""
    n = len(grid)
    pw = sum(grid[x][y] for x in range(n) for y in range(n) if x > y)
    pd = sum(grid[x][x] for x in range(n))
    pl = sum(grid[x][y] for x in range(n) for y in range(n) if x < y)
    return pw, pd, pl


def most_likely_score(grid):
    n = len(grid)
    best, bp = (0, 0), -1.0
    for x in range(n):
        for y in range(n):
            if grid[x][y] > bp:
                bp, best = grid[x][y], (x, y)
    return best, bp


def optimal_tip(grid, rule: ScoringRule):
    """Tip (x, y) maximizing expected points, plus that expected value.

    Candidate tips are capped at a small score range (almost all expected-points
    optima are low scores); outcomes are summed over the full grid."""
    n = len(grid)
    cap = min(n - 1, 6)
    best_tip, best_ev = (0, 0), -1.0
    for tx in range(cap + 1):
        for ty in range(cap + 1):
            ev = 0.0
            for ax in range(n):
                for ay in range(n):
                    pts = points((tx, ty), (ax, ay), rule)
                    if pts:
                        ev += grid[ax][ay] * pts
            if ev > best_ev:
                best_ev, best_tip = ev, (tx, ty)
    return best_tip, best_ev


def _pct(x: float) -> str:
    return f"{x*100:.0f}%" if x >= 0.10 else f"{x*100:.1f}%"


def build_tipps_report(groups, rule: ScoringRule, p: ModelParams,
                       champion_top=None, extra_note: str = "") -> str:
    """Markdown report of point-maximizing tips for every group-stage match."""
    L: list[str] = []
    L.append("# 2026 World Cup — Tippspiel tips (point-maximizing)\n")
    L.append(f"*Generated {date.today().isoformat()}. "
             f"Scoring: **{rule.name}** — exact {rule.exact}, goal-difference "
             f"{rule.diff}, tendency {rule.tendency} pts.*\n")
    L.append("> For each match the **tip** below maximizes expected points "
             "under your scoring rule. It is **not always the most likely "
             "score** — when an exact score is unlikely, a safer tendency/"
             "goal-difference tip can score more on average. The most likely "
             "score is shown alongside for comparison.\n")

    if champion_top:
        picks = ", ".join(f"{n} ({_pct(q)})" for n, q in champion_top[:3])
        L.append(f"## 🏆 Outright winner pick\n\n**{champion_top[0][0]}** is the "
                 f"single most likely champion. Top picks: {picks}.\n")

    L.append("## Group-stage match tips\n")
    for letter, teams in groups.items():
        L.append(f"**Group {letter}**\n")
        L.append("| Match | Tip | E[pts] | Win–Draw–Loss | Most likely |")
        L.append("|-------|:---:|-------:|:-------------:|:-----------:|")
        for a, b in combinations(teams, 2):
            grid = score_distribution(a, b, p)
            tip, ev = optimal_tip(grid, rule)
            pw, pd, pl = outcome_probs(grid)
            (mx, my), _mp = most_likely_score(grid)
            flag = "" if tip == (mx, my) else " ⚠️"
            L.append(f"| {a.name} – {b.name} | **{tip[0]}–{tip[1]}**{flag} "
                     f"| {ev:.2f} | {_pct(pw)} · {_pct(pd)} · {_pct(pl)} "
                     f"| {mx}–{my} |")
        L.append("")

    L.append("## Notes\n")
    L.append(
        "- ⚠️ marks matches where the point-maximizing tip differs from the most "
        "likely score — the interesting cases.\n"
        "- Scoreline distributions are analytic (attack/defense → Poisson with "
        "the Dixon-Coles low-score correction), using central ratings (the "
        "per-tournament strength resampling used for the simulation report does "
        "not apply to a single fixed match).\n"
        "- Knockout fixtures aren't listed: the participants aren't known until "
        "the bracket resolves. Re-run once the matchups are set.\n"
        "- Adjust the scoring rule (`--exact/--diff/--tendency/--diff-draws`) to "
        "match your pool — the optimal tips shift with the rule.\n")
    if extra_note:
        L.append(extra_note + "\n")
    return "\n".join(L)
