"""
Live update pipeline: score our tips, check how reality aligned with our
predictions, and re-optimize the tips we haven't submitted yet.

Used by update.py once `data/results.csv` starts filling up.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from datetime import date
from itertools import combinations

from .model import DEFAULT_PARAMS, ModelParams
from .results import GROUP, Results
from .tippspiel import (ScoringRule, most_likely_score, optimal_tip,
                        outcome_probs, points, score_distribution)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# --------------------------------------------------------------------------
# Our submitted tips (frozen once submitted)
# --------------------------------------------------------------------------

def save_our_tips(path, tips):
    """tips: iterable of (stage, team_a, team_b, tip_a, tip_b)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["stage", "team_a", "team_b", "tip_a", "tip_b"])
        w.writerows(tips)


def load_our_tips(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [(r["stage"], r["team_a"], r["team_b"],
                 int(r["tip_a"]), int(r["tip_b"]))
                for r in csv.DictReader(fh) if r.get("team_a")]


def group_tips(groups, rule: ScoringRule, p: ModelParams):
    """EV-optimal tip for every group-stage pairing."""
    out = []
    for teams in groups.values():
        for a, b in combinations(teams, 2):
            tip, _ev = optimal_tip(score_distribution(a, b, p), rule)
            out.append((GROUP, a.name, b.name, tip[0], tip[1]))
    return out


# --------------------------------------------------------------------------
# Scoring our tips against real results
# --------------------------------------------------------------------------

@dataclass
class TipScore:
    stage: str
    team_a: str
    team_b: str
    tip: tuple
    actual: tuple
    pts: int


def _oriented_actual(results: Results, stage, a, b):
    if stage == GROUP:
        return results.group_score(a, b)
    r = results.ko_result(stage, a, b)
    if r is None:
        return None
    return (r.goals_a, r.goals_b) if r.team_a == a else (r.goals_b, r.goals_a)


def score_our_tips(our_tips, results: Results, rule: ScoringRule):
    scored, total = [], 0
    for stage, a, b, ta, tb in our_tips:
        actual = _oriented_actual(results, stage, a, b)
        if actual is None:
            continue
        pts = points((ta, tb), actual, rule)
        total += pts
        scored.append(TipScore(stage, a, b, (ta, tb), actual, pts))
    return scored, total


# --------------------------------------------------------------------------
# Calibration: did reality align with our (pre-tournament) predictions?
# --------------------------------------------------------------------------

@dataclass
class Calibration:
    n: int
    brier: float           # mean multiclass Brier (0 best, ~0.667 = uninformed)
    logloss: float         # mean negative log-likelihood
    tendency_acc: float    # share of matches whose tendency we called right
    surprises: list        # (stage, a, b, actual, p_actual) for low-prob outcomes


def calibration(teams, results: Results, p: ModelParams, surprise_thresh=0.20):
    by_name = {t.name: t for t in teams}
    n = brier = logloss = hits = 0
    surprises = []
    for r in results.rows:
        ta, tb = by_name.get(r.team_a), by_name.get(r.team_b)
        if ta is None or tb is None:
            continue
        pw, pd, pl = outcome_probs(score_distribution(ta, tb, p))
        if r.goals_a > r.goals_b:
            probs, actual_idx = (pw, pd, pl), 0
        elif r.goals_a == r.goals_b:
            probs, actual_idx = (pw, pd, pl), 1
        else:
            probs, actual_idx = (pw, pd, pl), 2
        y = [0, 0, 0]
        y[actual_idx] = 1
        brier += sum((probs[i] - y[i]) ** 2 for i in range(3))
        p_act = max(probs[actual_idx], 1e-9)
        logloss += -math.log(p_act)
        if max(range(3), key=lambda i: probs[i]) == actual_idx:
            hits += 1
        if p_act < surprise_thresh:
            surprises.append((r.stage, r.team_a, r.team_b,
                              (r.goals_a, r.goals_b), p_act))
        n += 1
    if n == 0:
        return Calibration(0, 0.0, 0.0, 0.0, [])
    surprises.sort(key=lambda s: s[4])
    return Calibration(n, brier / n, logloss / n, hits / n, surprises)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def _fmt(score):
    return f"{score[0]}–{score[1]}"


def build_live_report(results: Results, rule: ScoringRule,
                      scored, total, calib: Calibration,
                      champion_top, remaining_tips, risk: str) -> str:
    L = []
    L.append("# 2026 World Cup — live update\n")
    L.append(f"*Generated {date.today().isoformat()}. "
             f"{len(results)} matches recorded "
             f"({len(results.group_results())} group, "
             f"{len(results.knockout_results())} knockout).*\n")

    # --- Tippspiel score -------------------------------------------------
    L.append("## 🎯 Our Tippspiel score\n")
    if scored:
        n = len(scored)
        exact = sum(1 for s in scored if s.pts == rule.exact)
        L.append(f"**{total} points** from {n} scored matches "
                 f"(avg {total/n:.2f}/match · {exact} exact hits). "
                 "Bonus questions (10 pts each) are tracked separately.\n")
        L.append("| Match | Our tip | Result | Pts |")
        L.append("|-------|:-------:|:------:|----:|")
        for s in scored:
            L.append(f"| {s.team_a} – {s.team_b} | {_fmt(s.tip)} "
                     f"| {_fmt(s.actual)} | {s.pts} |")
        L.append("")
    else:
        L.append("No scored matches yet (add results to `data/results.csv`).\n")

    # --- Alignment / calibration ----------------------------------------
    L.append("## 📏 Did reality match our predictions?\n")
    if calib.n:
        L.append(f"Over {calib.n} played matches (vs our pre-tournament model):\n")
        L.append(f"- **Tendency accuracy:** {calib.tendency_acc*100:.0f}% "
                 "(share where our favourite/draw call was right)")
        L.append(f"- **Brier score:** {calib.brier:.3f} "
                 "(0 = perfect, ~0.667 = uninformed guessing — lower is better)")
        L.append(f"- **Log-loss:** {calib.logloss:.3f} (lower is better)\n")
        if calib.surprises:
            L.append("**Biggest surprises** (results our model rated unlikely):\n")
            L.append("| Match | Result | Our prob. of that outcome |")
            L.append("|-------|:------:|--------------------------:|")
            for stage, a, b, sc, pa in calib.surprises[:8]:
                L.append(f"| {a} – {b} | {_fmt(sc)} | {pa*100:.0f}% |")
            L.append("")
    else:
        L.append("No matches played yet.\n")

    # --- Updated outlook -------------------------------------------------
    if champion_top:
        L.append("## 🔮 Updated title odds (conditioned + re-tuned)\n")
        L.append("Remaining tournament re-simulated given results so far, with "
                 "ratings re-tuned from observed form.\n")
        L.append("| Team | Champion |")
        L.append("|------|---------:|")
        for name, q in champion_top[:12]:
            L.append(f"| {name} | {q*100:.1f}% |")
        L.append("")

    # --- Updated tips for unplayed matches ------------------------------
    if remaining_tips:
        L.append(f"## 📝 Updated tips for upcoming group matches ({risk} mode)\n")
        if risk == "aggressive":
            L.append("*Aggressive mode: tips the single most likely exact score "
                     "to chase 4-pointers (higher variance — use when behind).*\n")
        else:
            L.append("*Safe mode: expected-points-maximizing tips (default).*\n")
        L.append("| Match | Tip | Win–Draw–Loss |")
        L.append("|-------|:---:|:-------------:|")
        for a, b, tip, (pw, pd, pl) in remaining_tips:
            L.append(f"| {a} – {b} | **{_fmt(tip)}** "
                     f"| {pw*100:.0f}% · {pd*100:.0f}% · {pl*100:.0f}% |")
        L.append("")

    # --- Strategy --------------------------------------------------------
    L.append("## 🧭 Strategy\n")
    L.append(
        "- **Safe (default):** expected-points-maximizing tips — best when you're "
        "leading or playing the long game.\n"
        "- **Aggressive (`--risk aggressive`):** tip the most likely *exact* "
        "score to maximize 4-point hits — higher variance, use when you need to "
        "catch up in your round.\n"
        "- Re-run after each matchday: results re-tune the ratings and re-simulate "
        "the rest, and upcoming tips update automatically.\n")
    return "\n".join(L)
