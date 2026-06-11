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
    # TippBlitz per-match tiers: 4 exact / 3 goal-diff / 2 tendency. Bonuses
    # (early tips, perfect matchdays, KO multiplier, advancement, outright
    # questions) are separate from per-match scoring and don't shift the
    # expected-points-optimal tip, so they aren't modeled in ScoringRule.
    "tippblitz": ScoringRule(
        exact=4, diff=3, tendency=2, diff_applies_to_draws=False,
        name="TippBlitz (4 exact / 3 goal-diff / 2 tendency + bonuses)"),
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


def optimal_tip(grid, rule: ScoringRule, risk: str = "safe"):
    """Tip (x, y) maximizing expected points under the chosen risk profile.

    Risk modes:
    - `safe` (default): straight EV maximisation — the right call when
      you're not chasing the leader.
    - `aggressive`: bias toward exact-score tips. Picks the most likely
      scoreline; trades some EV for a higher chance of a four-pointer when
      you need a swing.
    - `contrarian`: maximise EV with a small penalty against the single
      most-likely score (the tip the crowd will gravitate to). Useful in
      a pool where tying the field on a 'safe' tip costs you relative
      standing; you give up a touch of EV to gain differentiation.

    Candidate tips are capped at a small score range (almost all expected-
    points optima are low scores); outcomes are summed over the full grid.
    """
    n = len(grid)
    cap = min(n - 1, 6)
    most_likely, _ = most_likely_score(grid)
    if risk == "aggressive":
        ev = _ev(grid, most_likely, rule)
        return most_likely, ev

    crowd_penalty = _crowd_penalty(grid, rule) if risk == "contrarian" else 0.0
    best_tip, best_ev = (0, 0), -1.0
    for tx in range(cap + 1):
        for ty in range(cap + 1):
            ev = _ev(grid, (tx, ty), rule)
            adjusted = ev - (crowd_penalty if (tx, ty) == most_likely else 0.0)
            if adjusted > best_ev:
                best_ev, best_tip = adjusted, (tx, ty)
    # Report the *true* EV at the chosen tip — the penalty was only a tie-break.
    return best_tip, _ev(grid, best_tip, rule)


def _ev(grid, tip, rule: ScoringRule) -> float:
    """Expected points for `tip` against the analytic scoreline distribution."""
    n = len(grid)
    ev = 0.0
    for ax in range(n):
        for ay in range(n):
            pts = points(tip, (ax, ay), rule)
            if pts:
                ev += grid[ax][ay] * pts
    return ev


def _crowd_penalty(grid, rule: ScoringRule) -> float:
    """Heuristic differentiation discount applied to the most-likely score
    in contrarian mode. Anchored to the rule's exact-score reward so it's
    comparable across pools: a player who picks the crowd's favourite
    sacrifices ~5% of the exact-tier payout to stand out — small enough to
    keep the choice EV-rational, big enough to break a near-tie with a
    less-popular tip."""
    return 0.05 * rule.exact


def _pct(x: float) -> str:
    return f"{x*100:.0f}%" if x >= 0.10 else f"{x*100:.1f}%"


_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _fmt_kickoff(dt) -> str:
    """e.g. 'Thu 11 Jun, 21:00'."""
    return (f"{_WEEKDAYS[dt.weekday()]} {dt.day} {_MONTHS[dt.month]}, "
            f"{dt:%H:%M}")


def build_schedule_section(fixtures, team_by_name, rule: ScoringRule,
                           p: ModelParams, risk: str = "safe") -> list[str]:
    """Markdown lines: every group-stage fixture in kickoff order with its
    point-maximizing tip. `fixtures` is a list of tournament.Fixture; missing
    teams (a fixture whose sides aren't in `team_by_name`) are skipped."""
    L: list[str] = []
    L.append("## Group-stage tips by date\n")
    L.append("> The same point-maximizing tips as above, but every fixture "
             "listed in kickoff order (times are **MESZ/CEST**). Home team "
             "first, as in the official schedule.\n")
    L.append("| # | Kickoff (MESZ) | Grp | Match | Tip | E[pts] | Venue |")
    L.append("|--:|----------------|:---:|-------|:---:|-------:|-------|")
    for fx in fixtures:
        a = team_by_name.get(fx.home)
        b = team_by_name.get(fx.away)
        if a is None or b is None:
            continue
        grid = score_distribution(a, b, p)
        tip, ev = optimal_tip(grid, rule, risk=risk)
        (mx, my), _mp = most_likely_score(grid)
        flag = "" if tip == (mx, my) else " ⚠️"
        L.append(f"| {fx.number} | {_fmt_kickoff(fx.kickoff)} | {fx.group} "
                 f"| {fx.home} – {fx.away} | **{tip[0]}–{tip[1]}**{flag} "
                 f"| {ev:.2f} | {fx.venue} |")
    L.append("")
    return L


def build_tipps_report(groups, rule: ScoringRule, p: ModelParams,
                       champion_top=None, extra_note: str = "",
                       risk: str = "safe", fixtures=None) -> str:
    """Markdown report of point-maximizing tips for every group-stage match."""
    L: list[str] = []
    L.append("# 2026 World Cup — Tippspiel tips (point-maximizing)\n")
    risk_blurb = {"safe": "expected-value-maximizing",
                  "aggressive": "exact-score chasing (highest-EV when behind)",
                  "contrarian": "EV-optimal with crowd-overlap penalty"}.get(
        risk, risk)
    L.append(f"*Generated {date.today().isoformat()}. "
             f"Scoring: **{rule.name}** — exact {rule.exact}, goal-difference "
             f"{rule.diff}, tendency {rule.tendency} pts. "
             f"Risk profile: **{risk}** ({risk_blurb}).*\n")
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
            tip, ev = optimal_tip(grid, rule, risk=risk)
            pw, pd, pl = outcome_probs(grid)
            (mx, my), _mp = most_likely_score(grid)
            flag = "" if tip == (mx, my) else " ⚠️"
            L.append(f"| {a.name} – {b.name} | **{tip[0]}–{tip[1]}**{flag} "
                     f"| {ev:.2f} | {_pct(pw)} · {_pct(pd)} · {_pct(pl)} "
                     f"| {mx}–{my} |")
        L.append("")

    if fixtures:
        team_by_name = {t.name: t for teams in groups.values() for t in teams}
        L.extend(build_schedule_section(fixtures, team_by_name, rule, p, risk))

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
