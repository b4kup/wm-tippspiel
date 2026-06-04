"""
Per-confederation strength offsets, calibrated from inter-confederation
match history.

Why this exists
---------------
Elo (the prior used to seed attack/defense in `data/derive_ratings.py`)
is a global rating but most international matches are intra-confederation.
A confederation can drift relative to others — AFC sides cycle a lot of
matches against weak intra-confed opposition that inflates their Elo;
CONMEBOL plays a small, uniformly hard schedule that can compress it.

The Poisson fit (`src/poisson_fit.py`) corrects this *if* the data has
enough cross-confederation bridges. In practice the bridges are sparse
(few AFC vs CONMEBOL matches, etc.), so the fit's shrinkage to the Elo
prior reintroduces the Elo bias.

What this module does
---------------------
For every match in `data/matches_recent.csv`:
1. predict each side's expected goals from the Elo prior alone (no
   confed adjustment yet);
2. take the log-residual `log(actual / predicted)` for each side;
3. average residuals per (confederation, side=attack|defense) across all
   matches *the team played as that confederation*;
4. centre the table so the residuals sum to 0 (one confed has to be the
   baseline — UEFA, the largest sample).

Output: a dict `{confed: (alpha_offset, delta_offset)}` in log space.
A positive alpha offset means "this confederation scores more than
its Elo prior suggests on average against opponents from other
confederations" — add to the prior to bias-correct.

Limitations
-----------
- Aggregates ignore opponent strength within the cross-confed sample;
  a confederation that disproportionately plays *strong* opponents of
  other confederations gets credited too harshly. Mitigated by
  shrinkage and by aggregating only over matches where the *opponent*
  is from a different confed (so the within-confed sample doesn't
  contaminate the cross-confed signal).
- Sample sizes vary wildly (UEFA: thousands of matches, OFC: dozens).
  Shrinkage to 0 by `N / (N + N_PRIOR)` damps small-sample noise.
"""

from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from dataclasses import dataclass

from .poisson_fit import canonical, load_matches

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
# Shrinkage denominator. A confederation needs ~30 cross-confed sample
# matches to half-weight the data signal against zero. Conservative —
# OFC has roughly that many in the dataset; UEFA has hundreds.
N_PRIOR = 30.0


@dataclass(frozen=True)
class ConfedOffset:
    """Log-space offsets to add to a team's Elo-derived prior."""
    confederation: str
    alpha_offset: float    # attack: positive = score more than prior predicts
    delta_offset: float    # defense: positive = concede less than prior predicts
    n_matches: int


def _load_team_confederations(teams_path: str | None = None
                              ) -> dict[str, str]:
    teams_path = teams_path or os.path.join(DATA_DIR, "teams.csv")
    out: dict[str, str] = {}
    if not os.path.exists(teams_path):
        return out
    with open(teams_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[canonical(r["team"])] = r["confederation"].strip()
    return out


def _load_team_elos(teams_path: str | None = None) -> dict[str, float]:
    teams_path = teams_path or os.path.join(DATA_DIR, "teams.csv")
    out: dict[str, float] = {}
    if not os.path.exists(teams_path):
        return out
    with open(teams_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[canonical(r["team"])] = float(r["elo"])
    return out


def fit_offsets(matches: list[dict] | None = None,
                teams_path: str | None = None,
                lg_avg: float = 1.5972,
                k_q: float = 0.8155,
                ) -> dict[str, ConfedOffset]:
    """Compute per-confederation log-attack and log-defense offsets from
    cross-confederation matches in `matches_recent.csv`.

    Returns {confed: ConfedOffset}. Confederations missing from the data
    map to all-zero offsets (no correction).
    """
    matches = matches if matches is not None else load_matches()
    confed = _load_team_confederations(teams_path)
    elos = _load_team_elos(teams_path)
    if not confed or not elos:
        return {}

    elo_avg = sum(elos.values()) / len(elos)

    # Collect log-residuals per (team-confederation, attack|defense).
    alpha_sums: dict[str, float] = defaultdict(float)
    delta_sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)

    for m in matches:
        h, a = canonical(m["home"]), canonical(m["away"])
        gh, ga = m["gh"], m["ga"]
        ch, ca = confed.get(h), confed.get(a)
        if not ch or not ca or ch == ca:
            continue           # only cross-confederation matches
        if h not in elos or a not in elos:
            continue
        qh = (elos[h] - elo_avg) / 400.0
        qa = (elos[a] - elo_avg) / 400.0
        att_h = lg_avg * math.exp(k_q * qh)
        def_h = lg_avg * math.exp(-k_q * qh)
        att_a = lg_avg * math.exp(k_q * qa)
        def_a = lg_avg * math.exp(-k_q * qa)
        pred_h = att_h * def_a / lg_avg
        pred_a = att_a * def_h / lg_avg
        # Log-ratio with a half-goal smoothing to handle 0s
        alpha_sums[ch] += math.log((gh + 0.5) / (pred_h + 0.5))
        alpha_sums[ca] += math.log((ga + 0.5) / (pred_a + 0.5))
        # Defense residual: positive value = conceded fewer than predicted.
        delta_sums[ch] += math.log((pred_a + 0.5) / (ga + 0.5))
        delta_sums[ca] += math.log((pred_h + 0.5) / (gh + 0.5))
        counts[ch] += 1
        counts[ca] += 1

    if not counts:
        return {}

    # Shrink toward zero by N/(N + N_PRIOR), then centre so the sample-
    # weighted mean offset is zero (one confed has to be the reference).
    raw_alpha: dict[str, float] = {}
    raw_delta: dict[str, float] = {}
    for c, n in counts.items():
        w = n / (n + N_PRIOR)
        raw_alpha[c] = w * (alpha_sums[c] / n)
        raw_delta[c] = w * (delta_sums[c] / n)
    total_n = sum(counts.values())
    mean_alpha = sum(raw_alpha[c] * counts[c] for c in counts) / total_n
    mean_delta = sum(raw_delta[c] * counts[c] for c in counts) / total_n

    out: dict[str, ConfedOffset] = {}
    for c, n in counts.items():
        out[c] = ConfedOffset(
            confederation=c,
            alpha_offset=raw_alpha[c] - mean_alpha,
            delta_offset=raw_delta[c] - mean_delta,
            n_matches=n,
        )
    return out


def format_table(offsets: dict[str, ConfedOffset]) -> str:
    """Pretty-print the table for an audit / sanity-check."""
    if not offsets:
        return "(no cross-confederation matches available)\n"
    L = ["| Confederation | n | Δα (attack) | Δδ (defense) |",
         "|---------------|--:|------------:|-------------:|"]
    for c, o in sorted(offsets.items(), key=lambda kv: -kv[1].n_matches):
        L.append(f"| {c} | {o.n_matches} | {o.alpha_offset:+.3f} "
                 f"| {o.delta_offset:+.3f} |")
    return "\n".join(L) + "\n"
