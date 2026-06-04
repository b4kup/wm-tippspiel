"""
Sensitivity analysis — which model parameters move the title odds most?

Builds a tornado chart over the key `ModelParams` knobs. For each param
we re-run the Monte Carlo at low / high perturbations (default ±10%)
and report the per-team change in champion probability.

Output: a Markdown table per top team — one row per perturbed param,
sorted by the absolute size of the swing. The biggest swings sit at
the top of each tornado, which makes it obvious where assumption
uncertainty hurts most.

Costs: each axis takes 3 simulator runs (low / baseline / high). The
default `n_sims=5000` keeps the whole sweep under a minute on a
laptop; numbers in the report are noisier than `run.py --sims 20000`
but consistent across rows (same seeds).
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Iterable

from .model import DEFAULT_PARAMS, ModelParams
from .simulate import run

# (param_name, baseline_extractor, low_factor, high_factor, kind)
# kind="scale" => multiply baseline by factor; "shift" => add factor in absolute
# terms (used for params that can be zero or negative, like dc_rho).
SENSITIVITY_AXES: list[tuple[str, str, float, float, str]] = [
    ("lg_avg",            "lg_avg",            0.90, 1.10, "scale"),
    ("host_attack_mult",  "host_attack_mult",  0.95, 1.05, "scale"),
    ("host_defense_mult", "host_defense_mult", 0.95, 1.05, "scale"),
    ("dc_rho",            "dc_rho",           -0.05, +0.05, "shift"),
    ("rating_sigma_elo",  "rating_sigma_elo",  0.50, 1.50, "scale"),
    ("travel_per_1000km", "travel_per_1000km", 0.0,  2.00, "scale"),
    ("altitude_per_1000m", "altitude_per_1000m", 0.0, 2.00, "scale"),
    ("heat_per_degree",   "heat_per_degree",   0.0,  2.00, "scale"),
]


def _perturb(params: ModelParams, attr: str, factor: float, kind: str) -> ModelParams:
    """Return a perturbed copy of `params` along one axis."""
    base = getattr(params, attr)
    if kind == "scale":
        return replace(params, **{attr: base * factor})
    return replace(params, **{attr: base + factor})


def _champion_probs(params: ModelParams, n_sims: int, seed: int,
                    teams: list, names: Iterable[str]) -> dict[str, float]:
    stats, _ = run(n_sims, params, seed=seed, teams=teams)
    return {n: stats.prob(stats.champion, n) for n in names}


def run_sensitivity(n_sims: int = 5000, seed: int = 2026,
                    top_k: int = 8, teams=None,
                    axes=SENSITIVITY_AXES, baseline=DEFAULT_PARAMS
                    ) -> dict:
    """Return a dict with baseline / per-axis champion probabilities for
    the top-`top_k` teams under baseline parameters."""
    if teams is None:
        from .tournament import load_teams
        teams = load_teams()
    names_all = [t.name for t in teams]
    base_probs = _champion_probs(baseline, n_sims, seed, teams, names_all)
    top = sorted(base_probs.items(), key=lambda kv: -kv[1])[:top_k]
    top_names = [n for n, _ in top]

    axis_results: list[dict] = []
    for attr, _label, low_f, high_f, kind in axes:
        lo_params = _perturb(baseline, attr, low_f, kind)
        hi_params = _perturb(baseline, attr, high_f, kind)
        lo = _champion_probs(lo_params, n_sims, seed, teams, top_names)
        hi = _champion_probs(hi_params, n_sims, seed, teams, top_names)
        baseline_val = getattr(baseline, attr)
        lo_val = (baseline_val * low_f) if kind == "scale" else (baseline_val + low_f)
        hi_val = (baseline_val * high_f) if kind == "scale" else (baseline_val + high_f)
        axis_results.append({
            "attr": attr, "kind": kind,
            "baseline": baseline_val, "low": lo_val, "high": hi_val,
            "probs_low": lo, "probs_high": hi,
        })
    return {
        "n_sims": n_sims, "seed": seed,
        "top_names": top_names, "base_probs": base_probs,
        "axes": axis_results,
    }


def _bar(value: float, *, width: int = 18, vmax: float = 0.05) -> str:
    """Signed bar centred on zero for tornado-chart visuals.
    `value` is a probability delta (e.g. +0.012 for +1.2 percentage points).
    `vmax` is the half-width of the scale in absolute probability."""
    half = width
    pos = max(0, min(half, int(abs(value) / vmax * half)))
    if value >= 0:
        return ("·" * half) + "│" + ("█" * pos) + ("·" * (half - pos))
    return ("·" * (half - pos)) + ("█" * pos) + "│" + ("·" * half)


def render_report(results: dict) -> str:
    from datetime import date
    L = ["# Sensitivity analysis — title odds per parameter",
         "",
         f"*Generated {date.today().isoformat()} from "
         f"{results['n_sims']:,} Monte Carlo sims (seed `{results['seed']}`) "
         "per perturbation. Each axis is run at a low and a high value; the "
         "delta vs the baseline title probability is reported per team.*",
         "",
         "> Tornado bars span ±5 percentage points; the longest bars mark the "
         "assumptions that most affect each team's title odds.",
         ""]
    top = results["top_names"]
    base = results["base_probs"]
    axes = results["axes"]

    for name in top:
        L.append(f"## {name} — baseline {base[name]*100:.1f}%")
        L.append("")
        L.append("| Param | Low value | Δ@low | High value | Δ@high "
                 "| Tornado (low / high) |")
        L.append("|-------|----------:|------:|-----------:|------:|:--------|")
        rows = []
        for ax in axes:
            dlo = ax["probs_low"][name] - base[name]
            dhi = ax["probs_high"][name] - base[name]
            rows.append((max(abs(dlo), abs(dhi)), ax, dlo, dhi))
        rows.sort(key=lambda r: -r[0])
        for _, ax, dlo, dhi in rows:
            L.append(
                f"| `{ax['attr']}` | {ax['low']:+.4f} "
                f"| {dlo*100:+.2f} pp | {ax['high']:+.4f} "
                f"| {dhi*100:+.2f} pp "
                f"| `{_bar(dlo)}` / `{_bar(dhi)}` |")
        L.append("")

    L.append("## Reading guide")
    L.append("")
    L.append(
        "- Each row is one assumption knob; the bar shows how much the team's "
        "title probability moves when the knob is pushed to its low / high "
        "edge. The longer the bar, the more title odds depend on that knob.\n"
        "- Sign convention: `Δ@low` is `prob(low) − prob(baseline)`, so "
        "a positive value means the team is **better off** under the lower "
        "value of the parameter.\n"
        "- `rating_sigma_elo` controls how much rating uncertainty is folded "
        "into each simulation; pushing it down ⇒ favourites get more "
        "confident, pushing it up ⇒ upset tail fattens. Favourites should "
        "react oppositely to underdogs.\n"
        "- Travel / altitude / heat axes typically move only the teams "
        "playing in punishing groups. Most teams will see ~0 swing here.")
    return "\n".join(L) + "\n"
