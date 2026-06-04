"""
Maher-style Poisson regression for international match results.

Model
-----
For a match where team `h` (home) plays team `a` (away):

    log λ_h  =  α_h  −  δ_a  +  γ           (home goals)
    log λ_a  =  α_a  −  δ_h                  (away goals)

    g_h ~ Poisson(λ_h),   g_a ~ Poisson(λ_a)

Parameters:
- α_i — team i's attack strength (positive = scores more)
- δ_i — team i's defence strength (positive = concedes less)
- γ   — home-team scalar (~0.25 in international football)

Identifiability: mean(α) = mean(δ) = 0 after each iteration.

Fitting (Maher 1982 fixed-point)
--------------------------------
The maximum-likelihood update has a clean closed form. For each team:

    α_i = log(G_for_i) − log( Σ_m  exp(−δ_opp + γ·home_indicator) )
    δ_i = log( Σ_m exp(α_opp + γ·home_indicator_opp) ) − log(G_against_i)

Iterate teams round-robin; re-center after each sweep. Converges in
roughly 30-60 iterations to 4 decimals.

Output
------
For each team that appears in the data:
- α, δ in log space (raw fit parameters)
- attack_model = LG_AVG · exp(α)      (model units; >1.35 = above-average)
- defense_model = LG_AVG · exp(−δ)    (model units; <1.35 = above-average)
- matches played (for downstream confidence weighting)
"""

from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from dataclasses import dataclass

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Some Wikipedia team names differ from our `data/teams.csv` canonical
# spelling. Map to canonical so the fit ties back to our 48 teams cleanly.
NAME_ALIASES: dict[str, str] = {
    "Turkey": "Türkiye",
    "Türkiye": "Türkiye",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "DPR Korea": "North Korea",
    "Iran": "IR Iran",
    "IR Iran": "IR Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Cape Verde": "Cabo Verde",
    "Cabo Verde": "Cabo Verde",
    "Czech Republic": "Czechia",
    "Czechia": "Czechia",
    "United States": "United States",
    "USA": "United States",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Bosnia & Herzegovina": "Bosnia & Herzegovina",
    "DR Congo": "DR Congo",
    "Republic of the Congo": "Congo",
    "Curaçao": "Curaçao",
}


def canonical(name: str) -> str:
    n = name.strip()
    return NAME_ALIASES.get(n, n)


@dataclass
class FittedTeam:
    name: str
    alpha: float           # attack in log-space
    delta: float           # defence in log-space
    matches: int
    goals_for: int
    goals_against: int

    def to_model(self, lg_avg: float) -> tuple[float, float]:
        return lg_avg * math.exp(self.alpha), lg_avg * math.exp(-self.delta)


def _recency_weights(matches: list[dict],
                     weight_by_year: dict[str, float] | None,
                     half_life_days: float | None,
                     ref_date: str | None) -> list[float]:
    """Per-match weight in [0, 1] from date-level exp decay or coarse year
    buckets. No decay (uniform 1.0) when neither is given.

    Date-level decay: weight = 0.5 ** ((ref_date - match_date).days /
    half_life_days). Smooth and principled — preferred over year buckets
    when match dates are available."""
    if half_life_days and half_life_days > 0:
        from datetime import date
        ref = date(*_parse_iso(ref_date)) if ref_date else None
        w: list[float] = []
        for m in matches:
            md = m.get("date", "") or ""
            if not md or ref is None:
                w.append(1.0)
                continue
            try:
                d = date(*_parse_iso(md))
            except Exception:
                w.append(1.0)
                continue
            delta = max(0.0, (ref - d).days)
            w.append(0.5 ** (delta / half_life_days))
        return w
    if weight_by_year:
        return [weight_by_year.get((m["date"] or "")[:4], 1.0) for m in matches]
    return [1.0] * len(matches)


def _parse_iso(date_str: str) -> tuple[int, int, int]:
    y, mo, d = date_str.split("-")
    return int(y), int(mo), int(d)


def load_matches(path: str | None = None) -> list[dict]:
    path = path or os.path.join(DATA_DIR, "matches_recent.csv")
    out: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append({
                "date": r.get("date", "").strip(),
                "home": canonical(r["home"]),
                "away": canonical(r["away"]),
                "gh": int(r["goals_home"]),
                "ga": int(r["goals_away"]),
                "tournament": r.get("tournament", "").strip(),
            })
    return out


def fit_poisson(matches: list[dict], *,
                max_iter: int = 300, tol: float = 1e-5,
                weight_by_year: dict[str, float] | None = None,
                half_life_days: float | None = None,
                ref_date: str | None = None,
                damping: float = 0.4,
                param_clip: float = 1.4,
                l2_prior_strength: float = 4.0,
                ) -> tuple[dict[str, FittedTeam], float]:
    """Iteratively fit α_i, δ_i, γ from match results.

    Returns (per-team fit, home-advantage γ in log-space).

    `weight_by_year`: optional {year: weight} coarse recency weighting.
    `half_life_days` + `ref_date`: optional date-level exponential decay
        (overrides weight_by_year). A match `d` days before `ref_date` is
        weighted `0.5 ** (d / half_life_days)`. Smooth, principled recency
        — fresher signal counts more without the cliff of year buckets.
    `damping`: under-relaxation factor — each iteration moves only `damping`
        of the way to the new Maher fixed point. Prevents oscillation on
        teams with very lopsided records (Liechtenstein-tier minnows).
    `param_clip`: hard bound on |α|, |δ| each step. 1.4 means attack/defence
        multipliers stay in roughly [0.25, 4.0] — a reasonable football
        prior.
    `l2_prior_strength`: phantom pseudo-matches at average (G_for=G_against=
        league_avg) added per team to pull the fit toward the mean. 4 ≈
        "treat every team as 4 matches against average opposition for
        regularisation purposes." Bigger = more shrinkage."""
    teams: list[str] = sorted({m["home"] for m in matches}
                              | {m["away"] for m in matches})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    # Per-match weight (recency). Date-level exponential decay takes
    # precedence over coarse year buckets when both are supplied.
    w = _recency_weights(matches, weight_by_year, half_life_days, ref_date)

    # Initialise α, δ from goal averages (centred).
    gf: dict[int, float] = defaultdict(float)
    ga: dict[int, float] = defaultdict(float)
    games: dict[int, float] = defaultdict(float)
    for k, m in enumerate(matches):
        h, a = idx[m["home"]], idx[m["away"]]
        gf[h] += w[k] * m["gh"]; ga[h] += w[k] * m["ga"]
        gf[a] += w[k] * m["ga"]; ga[a] += w[k] * m["gh"]
        games[h] += w[k]; games[a] += w[k]
    league_avg = sum(gf.values()) / max(sum(games.values()), 1.0)
    alpha = [math.log(max(gf[i] / max(games[i], 1.0), 0.2) / max(league_avg, 0.5))
             for i in range(n)]
    delta = [math.log(max(league_avg, 0.5)
                      / max(ga[i] / max(games[i], 1.0), 0.2))
             for i in range(n)]
    gamma = 0.25     # initial home-advantage guess

    # Pre-build per-team incidence: (match_idx, opp_idx, is_home, weight, goals_scored)
    incidence: dict[int, list[tuple[int, int, bool, float, int, int]]] = defaultdict(list)
    for k, m in enumerate(matches):
        h, a = idx[m["home"]], idx[m["away"]]
        incidence[h].append((k, a, True, w[k], m["gh"], m["ga"]))
        incidence[a].append((k, h, False, w[k], m["ga"], m["gh"]))

    def _shift(arr, by):
        return [x - by for x in arr]

    def _clip(x: float) -> float:
        return max(-param_clip, min(param_clip, x))

    # Pseudo-counts implementing an L2 prior toward 0: every team gets
    # `l2_prior_strength` phantom matches against an average opponent with
    # the league-average scoring rate.
    L2 = l2_prior_strength
    log_league = math.log(max(league_avg, 0.5))

    for it in range(max_iter):
        max_change = 0.0
        for i in range(n):
            # Update α_i with L2 regularisation toward 0.
            sum_gf = L2 * league_avg
            sum_exp = L2
            for k, opp, is_home, ww, scored, conceded in incidence[i]:
                sum_gf += ww * scored
                sum_exp += ww * math.exp((gamma if is_home else 0.0) - delta[opp])
            target = math.log(sum_gf) - math.log(sum_exp) - log_league
            new_alpha = _clip(alpha[i] + damping * (target - alpha[i]))
            max_change = max(max_change, abs(new_alpha - alpha[i]))
            alpha[i] = new_alpha

            # Update δ_i with L2 regularisation toward 0.
            sum_ga = L2 * league_avg
            sum_exp = L2
            for k, opp, is_home, ww, scored, conceded in incidence[i]:
                sum_ga += ww * conceded
                opp_home_term = 0.0 if is_home else gamma
                sum_exp += ww * math.exp(alpha[opp] + opp_home_term)
            target = math.log(sum_exp) - math.log(sum_ga) - log_league
            new_delta = _clip(delta[i] + damping * (target - delta[i]))
            max_change = max(max_change, abs(new_delta - delta[i]))
            delta[i] = new_delta

        # Update γ: same damping.
        sum_home_goals = 0.0
        sum_exp = 0.0
        for k, m in enumerate(matches):
            h, a = idx[m["home"]], idx[m["away"]]
            sum_home_goals += w[k] * m["gh"]
            sum_exp += w[k] * math.exp(alpha[h] - delta[a])
        if sum_home_goals > 0 and sum_exp > 0:
            target = math.log(sum_home_goals) - math.log(sum_exp)
            new_gamma = max(0.0, min(0.6, gamma + damping * (target - gamma)))
            max_change = max(max_change, abs(new_gamma - gamma))
            gamma = new_gamma

        # Re-center for identifiability.
        a_mean = sum(alpha) / n
        d_mean = sum(delta) / n
        alpha = _shift(alpha, a_mean)
        delta = _shift(delta, d_mean)

        if max_change < tol:
            break

    fitted: dict[str, FittedTeam] = {}
    for i, name in enumerate(teams):
        fitted[name] = FittedTeam(
            name=name,
            alpha=alpha[i],
            delta=delta[i],
            matches=int(round(games[i])),
            goals_for=int(round(gf[i])),
            goals_against=int(round(ga[i])),
        )
    return fitted, gamma


def shrink_to_prior(alpha_fit: float, delta_fit: float, matches: int,
                    alpha_prior: float, delta_prior: float,
                    n_prior: float = 10.0) -> tuple[float, float]:
    """Bayesian shrinkage to the Elo-derived prior. Sample-size weighting:
    a team with `matches` games gets `matches / (matches + n_prior)` weight
    on the data fit, the remainder on the prior. Both α and δ are in
    log-space, so a simple linear blend is the right thing here."""
    w = matches / (matches + n_prior) if (matches + n_prior) > 0 else 0.0
    return (w * alpha_fit + (1 - w) * alpha_prior,
            w * delta_fit + (1 - w) * delta_prior)
