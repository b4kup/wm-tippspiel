"""
Interactive HTML dashboard for the 2026 World Cup predictor.

Renders a single self-contained `.html` file with embedded JSON data, a dark
dashboard theme, and vanilla-JS interactivity. Four tabs:

  - **Champion race** — top contenders, model vs market vs Polymarket, hover
    for the round-by-round survival fan.
  - **Groups**         — 12 group cards with win-group / advance probability
    bars; hover shows ratings + champion odds; the most-likely qualifier pair
    is annotated.
  - **Bracket**        — the 16 Round-of-32 ties, click a team to highlight
    every slot it can fill, with onward odds and the most-likely R32 pairings.
  - **Tipps**          — per-match EV-optimal CHECK24 tip vs the most likely
    score, expected points, win/draw/loss split.

No build step, no dependencies, no chart library — opens by double-click and
works fully offline. Charts are inline SVG drawn from the embedded data.
"""

from __future__ import annotations

import json
import math
from datetime import date
from itertools import combinations

from .model import DEFAULT_PARAMS, ModelParams
from .simulate import Stats
from .tippspiel import (
    PRESETS,
    ScoringRule,
    most_likely_score,
    optimal_tip,
    outcome_probs,
    score_distribution,
)
from .tournament import Team


CONFED_COLORS = {
    "UEFA":     "#4a9eff",
    "CONMEBOL": "#f7d038",
    "CONCACAF": "#ff6b6b",
    "CAF":      "#51cf66",
    "AFC":      "#c779f0",
    "OFC":      "#20c997",
}


def _team_rounds(stats: Stats, name: str) -> dict[str, float]:
    """Round-by-round survival probabilities for one team."""
    return {
        "advance":   stats.prob(stats.advance,     name),
        "r16":       stats.prob(stats.reach_r16,   name),
        "qf":        stats.prob(stats.reach_qf,    name),
        "sf":        stats.prob(stats.reach_sf,    name),
        "final":     stats.prob(stats.reach_final, name),
        "champion":  stats.prob(stats.champion,    name),
        "win_group": stats.prob(stats.win_group,   name),
    }


def _tipps_data(groups: dict[str, list[Team]], rule: ScoringRule,
                params: ModelParams) -> dict[str, list[dict]]:
    """Per-group analytic tip table."""
    out: dict[str, list[dict]] = {}
    for letter, teams in groups.items():
        matches = []
        for a, b in combinations(teams, 2):
            grid = score_distribution(a, b, params)
            tip, ev = optimal_tip(grid, rule)
            (mx, my), mp = most_likely_score(grid)
            pw, pd, pl = outcome_probs(grid)
            matches.append({
                "home":  a.name,
                "away":  b.name,
                "tip":   [tip[0], tip[1]],
                "ev":    round(ev, 2),
                "ml":    [mx, my],
                "ml_p":  round(mp, 4),
                "pw":    round(pw, 4),
                "pd":    round(pd, 4),
                "pl":    round(pl, 4),
                "diverges": tip != (mx, my),
            })
        out[letter] = matches
    return out


def _bracket_data(stats: Stats) -> list[dict]:
    """One entry per R32 tie: top occupants per side + most-likely pairs."""
    from data.bracket import ROUND_OF_32
    n = stats.n
    ties = []
    for i, (slot_a, slot_b) in enumerate(ROUND_OF_32):
        a_counts = stats.r32_slots[i * 2]
        b_counts = stats.r32_slots[i * 2 + 1]
        top_a = sorted(((nm, c / n) for nm, c in a_counts.items()),
                       key=lambda kv: -kv[1])[:5]
        top_b = sorted(((nm, c / n) for nm, c in b_counts.items()),
                       key=lambda kv: -kv[1])[:5]
        pairs = sorted(((pair, c / n) for pair, c in stats.r32_pairs[i].items()),
                       key=lambda kv: -kv[1])[:3]
        ties.append({
            "idx":     i,
            "slot_a":  slot_a,
            "slot_b":  slot_b,
            "side_a":  [{"name": nm, "p": round(p, 4)} for nm, p in top_a],
            "side_b":  [{"name": nm, "p": round(p, 4)} for nm, p in top_b],
            "pairs":   [{"a": a, "b": b, "p": round(p, 4)} for (a, b), p in pairs],
        })
    return ties


def _market_data(teams: list[Team], stats: Stats) -> dict:
    """De-vigged bookmaker probability per team that has odds."""
    listed = [t for t in teams if t.market_decimal_odds]
    overround = sum(1.0 / t.market_decimal_odds for t in listed) if listed else 1.0
    rows = []
    for t in listed:
        implied = (1.0 / t.market_decimal_odds) / overround if overround else 0.0
        rows.append({
            "name":   t.name,
            "model":  round(stats.prob(stats.champion, t.name), 4),
            "market": round(implied, 4),
            "poly":   t.polymarket_prob,
            "odds":   t.market_decimal_odds,
        })
    return {"overround": round((overround - 1) * 100, 1), "rows": rows}


def _team_payload(t: Team, stats: Stats) -> dict:
    r = _team_rounds(stats, t.name)
    return {
        "name":        t.name,
        "group":       t.group,
        "confed":      t.confederation,
        "elo":         round(t.elo, 0),
        "attack":      round(t.attack, 3),
        "defense":     round(t.defense, 3),
        "market_odds": t.market_decimal_odds,
        "poly":        t.polymarket_prob,
        "shootout":    round(t.shootout_skill, 3),
        **{k: round(v, 4) for k, v in r.items()},
    }


def _build_payload(stats: Stats, groups: dict[str, list[Team]],
                   params: ModelParams, n_sims: int, seed,
                   rule: ScoringRule, n_results: int = 0) -> dict:
    from .model import HOSTS
    teams_flat = [t for g in groups.values() for t in g]
    top_pair = max(stats.finals.items(), key=lambda kv: kv[1])
    (fa, fb), fc = top_pair
    return {
        "meta": {
            "sims":      n_sims,
            "seed":      seed,
            "date":      date.today().isoformat(),
            "lg_avg":    params.lg_avg,
            "dc_rho":    params.dc_rho,
            "rating_sigma": params.rating_sigma_elo,
            "host_attack_mult":  params.host_attack_mult,
            "host_defense_mult": params.host_defense_mult,
            "min_lambda":        params.min_lambda,
            "hosts":     sorted(HOSTS),
            "rule":      rule.name,
            "n_results": n_results,
        },
        "confed_colors": CONFED_COLORS,
        "teams":         [_team_payload(t, stats) for t in teams_flat],
        "groups":        {letter: [t.name for t in gteams]
                          for letter, gteams in groups.items()},
        "group_pairs":   {
            letter: sorted(
                ({"a": pair[0], "b": pair[1], "p": round(c / n_sims, 4)}
                 for pair, c in stats.group_pairs[letter].items()),
                key=lambda kv: -kv["p"])[:5]
            for letter in groups
        },
        "bracket":       _bracket_data(stats),
        "market":        _market_data(teams_flat, stats),
        "tipps":         _tipps_data(groups, rule, params),
        "headline": {
            "final_a":     fa,
            "final_b":     fb,
            "final_p":     round(fc / n_sims, 4),
        },
    }


# --------------------------------------------------------------------------
# HTML / CSS / JS template
# --------------------------------------------------------------------------

_CSS = r"""
:root {
  --bg: #0d1117;
  --bg-2: #161b22;
  --panel: #1c2230;
  --panel-2: #232a3a;
  --border: #2d3548;
  --text: #e6edf3;
  --muted: #8b95a3;
  --accent: #f0a500;
  --accent-2: #58a6ff;
  --good: #3fb950;
  --bad:  #f85149;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}
header {
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.2px;
}
header h1 .accent { color: var(--accent); }
header .meta { color: var(--muted); font-size: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
nav.tabs {
  display: flex;
  padding: 0 24px;
  background: var(--bg-2);
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}
nav.tabs button {
  background: transparent;
  border: 0;
  color: var(--muted);
  padding: 12px 18px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  font-family: inherit;
  white-space: nowrap;
}
nav.tabs button:hover { color: var(--text); }
nav.tabs button.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}
main { padding: 22px 24px 80px; max-width: 1500px; margin: 0 auto; }
section.view { display: none; }
section.view.active { display: block; }
h2 {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--muted);
  margin: 0 0 12px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.kpi {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
}
.kpi .label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
.kpi .value { font-size: 20px; font-weight: 600; margin-top: 4px; }
.kpi .sub   { color: var(--muted); font-size: 12px; }
.kpi.live   { border-color: var(--good); background: rgba(63, 185, 80, 0.08); }
.kpi.live .value { color: var(--good); }
.live-banner {
  background: rgba(63, 185, 80, 0.10);
  border-bottom: 1px solid var(--good);
  color: var(--text);
  font-size: 12.5px;
  padding: 9px 24px;
}
.live-banner b { color: var(--good); }

/* --- champion race --- */
.champ-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
}
@media (max-width: 980px) { .champ-grid { grid-template-columns: 1fr; } }
.champ-bar {
  display: grid;
  grid-template-columns: 30px 130px 1fr 56px;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  cursor: pointer;
  border-radius: 4px;
  padding-left: 6px;
}
.champ-bar:hover { background: var(--panel-2); }
.champ-bar .rank { color: var(--muted); font-size: 12px; text-align: right; }
.champ-bar .name { font-weight: 500; }
.champ-bar .bar  { background: var(--bg-2); height: 14px; border-radius: 3px; overflow: hidden; position: relative; }
.champ-bar .bar > .fill { height: 100%; transition: width 0.4s ease; }
.champ-bar .pct  { text-align: right; font-family: ui-monospace, monospace; font-size: 12px; }
.confed-chip {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  vertical-align: middle; margin-right: 4px;
}
.fl {
  font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji",
               "Twemoji Mozilla", "EmojiOne Color", "Android Emoji", sans-serif;
  font-size: 1.05em;
  line-height: 1;
  margin-right: 6px;
  vertical-align: -1px;
}
.champ-detail {
  background: var(--panel-2);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: 14px 16px;
  margin-bottom: 16px;
  font-size: 13px;
  display: none;
}
.champ-detail.shown { display: block; }
.champ-detail h3 { margin: 0 0 8px; font-size: 14px; }
.funnel-wrap {
  background: var(--bg-2);
  border-radius: 6px;
  padding: 12px 8px 6px;
  margin-top: 10px;
}
.funnel-wrap svg { display: block; width: 100%; height: auto; }
.funnel-wrap .funnel-baseline { stroke: rgba(255,255,255,0.08); }
.funnel-wrap .stage-tick { stroke: rgba(255,255,255,0.25); }
.funnel-wrap .stage-lbl { fill: var(--muted); font-size: 10px; letter-spacing: 1.2px; }
.funnel-wrap .stage-val { fill: var(--text); font-size: 13px; font-weight: 600; }
.funnel-wrap .drop-lbl  { fill: var(--muted); font-size: 9.5px; }
.funnel-wrap .drop-lbl.big { fill: var(--bad); }
.funnel-wrap .drop-lbl.ok  { fill: var(--good); }
.funnel-wrap .funnel-poly { transition: opacity 0.25s ease; }
.funnel-wrap .funnel-poly:hover { opacity: 1; }

/* --- market table --- */
.market-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.market-table th, .market-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); text-align: right; }
.market-table th { color: var(--muted); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
.market-table td:first-child, .market-table th:first-child { text-align: left; }
.market-table .lean-up   { color: var(--good); }
.market-table .lean-down { color: var(--bad); }
.market-table .lean-eq   { color: var(--muted); }

/* --- groups view --- */
.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
  gap: 14px;
}
.group-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
}
.group-card h3 { margin: 0 0 10px; font-size: 13px; color: var(--accent); letter-spacing: 1px; }
.group-team {
  display: grid;
  grid-template-columns: 14px 1fr 60px 60px;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px dashed var(--border);
  font-size: 13px;
  position: relative;
}
.group-team:last-of-type { border-bottom: 0; }
.group-team:hover { background: var(--panel-2); border-radius: 4px; }
.group-team .mini-bar {
  position: relative; height: 8px; background: var(--bg-2); border-radius: 2px; overflow: hidden;
}
.group-team .mini-bar > .fill {
  position: absolute; left: 0; top: 0; bottom: 0; opacity: 0.85;
}
.group-team .num { font-family: ui-monospace, monospace; font-size: 11px; color: var(--muted); text-align: right; }
.group-card .pair-line {
  margin-top: 8px;
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
.group-card .pair-line b { color: var(--text); text-transform: none; letter-spacing: 0; font-weight: 500; }

/* --- bracket view --- */
.bracket-controls {
  margin-bottom: 14px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.bracket-controls select, .bracket-controls input {
  background: var(--panel);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 13px;
}
.bracket-controls .clear {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 6px 12px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
}
.bracket-controls .clear:hover { color: var(--text); }
.bracket-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 1100px) { .bracket-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px)  { .bracket-grid { grid-template-columns: 1fr; } }
.tie {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
}
.tie .tie-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
.tie .side {
  margin: 4px 0;
}
.tie .side-row {
  display: grid;
  grid-template-columns: 14px 1fr 40px;
  gap: 6px;
  align-items: center;
  padding: 2px 4px;
  border-radius: 3px;
  cursor: pointer;
}
.tie .side-row:hover, .tie .side-row.highlight {
  background: var(--panel-2);
}
.tie .side-row.highlight {
  outline: 1px solid var(--accent);
}
.tie .side-row .nm { font-size: 12px; }
.tie .side-row .pp { text-align: right; font-family: ui-monospace, monospace; color: var(--muted); font-size: 11px; }
.tie .divider { text-align: center; color: var(--muted); font-size: 10px; margin: 2px 0; }
.tie .pair-most {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border);
  color: var(--muted);
  font-size: 11px;
}

/* --- tipps view --- */
.tipps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 14px;
}
.tipps-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
}
.tipps-card h3 { margin: 0 0 10px; font-size: 13px; color: var(--accent); letter-spacing: 1px; }
.tipps-match {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed var(--border);
  font-size: 12px;
}
.tipps-match:last-of-type { border-bottom: 0; }
.tipps-match .matchup { font-size: 12px; }
.tipps-match .tip-pill {
  display: inline-block;
  background: var(--bg-2);
  border-radius: 4px;
  padding: 3px 8px;
  font-family: ui-monospace, monospace;
  font-size: 13px;
  font-weight: 600;
  margin-right: 6px;
}
.tipps-match.warn .tip-pill { background: rgba(240,165,0,0.18); color: var(--accent); }
.tipps-match .ev { color: var(--muted); font-family: ui-monospace, monospace; font-size: 11px; text-align: right; }
.tipps-match .wdl { font-size: 10px; color: var(--muted); font-family: ui-monospace, monospace; margin-top: 2px; }
.tipps-card .footer {
  margin-top: 10px;
  font-size: 11px;
  color: var(--muted);
  text-align: right;
  font-family: ui-monospace, monospace;
}

/* --- how-it-works (wiki) view --- */
.wiki-pickers {
  display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 12px;
}
.wiki-pickers label { color: var(--muted); font-size: 12px; display: flex; align-items: center; gap: 6px; }
.wiki-pickers select {
  background: var(--bg-2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 6px 10px;
  font-family: inherit;
  font-size: 12px;
}
.wiki-formula {
  background: var(--bg-2);
  border-radius: 6px;
  padding: 14px 18px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  line-height: 1.9;
  overflow-x: auto;
}
.wiki-formula .var { color: var(--accent); font-weight: 600; }
.wiki-formula .opn { color: var(--accent-2); font-weight: 600; }
.wiki-formula .num { color: var(--text); }
.wiki-formula .ann { color: var(--muted); font-size: 11px; margin-left: 10px; font-style: italic; }
.wiki-formula .arrow { color: var(--accent); font-weight: 700; }

.wiki-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 16px;
}
@media (max-width: 900px) { .wiki-grid-2 { grid-template-columns: 1fr; } }
.wiki-sublabel { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.wiki-bar-row {
  display: grid;
  grid-template-columns: 130px 1fr 50px;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
}
.wiki-bar-row .lbl { color: var(--text); }
.wiki-bar-row .num { font-family: ui-monospace, monospace; font-size: 11px; color: var(--muted); text-align: right; }
.wiki-bar-row .bar { background: var(--bg-2); height: 12px; border-radius: 2px; overflow: hidden; }
.wiki-bar-row .bar > .fill { height: 100%; }
.wiki-pois-row {
  display: grid;
  grid-template-columns: 40px 16px 1fr 50px;
  gap: 6px;
  align-items: center;
  font-size: 11px;
  padding: 2px 0;
}
.wiki-pois-row .k { font-family: ui-monospace, monospace; color: var(--muted); text-align: right; }
.wiki-pois-row .dot { width: 8px; height: 8px; border-radius: 50%; }
.wiki-pois-row .bar { background: var(--bg-2); height: 10px; border-radius: 2px; overflow: hidden; }
.wiki-pois-row .bar > .fill { height: 100%; }
.wiki-pois-row .pp { font-family: ui-monospace, monospace; color: var(--muted); text-align: right; font-size: 10px; }
#wiki-heatmap svg { display: block; width: 100%; height: auto; }
.wiki-roll {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 12px;
}
.roll-btn, .roll-btn-alt {
  background: var(--accent);
  color: #0d1117;
  border: 0;
  border-radius: 5px;
  padding: 8px 16px;
  font-family: inherit;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}
.roll-btn:hover, .roll-btn-alt:hover { filter: brightness(1.1); }
.roll-btn-alt { background: var(--accent-2); color: white; }
.roll-last {
  font-family: ui-monospace, monospace;
  font-size: 22px;
  font-weight: 600;
  padding: 4px 14px;
  background: var(--bg-2);
  border-radius: 6px;
  letter-spacing: 2px;
  min-width: 90px;
  text-align: center;
}
.wiki-roll-tally {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}
.tally-card {
  background: var(--bg-2);
  border-radius: 6px;
  padding: 10px 12px;
}
.tally-lbl { color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
.tally-val { font-size: 22px; font-weight: 600; margin-top: 2px; font-family: ui-monospace, monospace; }
.tally-sub { color: var(--muted); font-size: 11px; font-family: ui-monospace, monospace; }
#wiki-flow svg, #wiki-bracket-pic svg { display: block; width: 100%; height: auto; }

footer {
  border-top: 1px solid var(--border);
  padding: 14px 24px;
  color: var(--muted);
  font-size: 11px;
  text-align: center;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
"""


_JS = r"""
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const pct = (x) => x >= 0.995 ? "100%" : x >= 0.1 ? `${(x*100).toFixed(0)}%` : x >= 0.01 ? `${(x*100).toFixed(1)}%` : x > 0 ? `${(x*100).toFixed(2)}%` : "—";
const cclr = (confed) => DATA.confed_colors[confed] || "#888";
const byName = Object.fromEntries(DATA.teams.map(t => [t.name, t]));

// Country flag emoji per team. Unicode regional-indicator pairs for sovereign
// states (ISO 3166-1 alpha-2) and subdivision tag sequences for England &
// Scotland. Renders natively from the system emoji font — no images, no CDN.
const FLAGS = {
  "Mexico": "\u{1F1F2}\u{1F1FD}", "South Africa": "\u{1F1FF}\u{1F1E6}",
  "South Korea": "\u{1F1F0}\u{1F1F7}", "Czechia": "\u{1F1E8}\u{1F1FF}",
  "Canada": "\u{1F1E8}\u{1F1E6}", "Bosnia & Herzegovina": "\u{1F1E7}\u{1F1E6}",
  "Qatar": "\u{1F1F6}\u{1F1E6}", "Switzerland": "\u{1F1E8}\u{1F1ED}",
  "Brazil": "\u{1F1E7}\u{1F1F7}", "Morocco": "\u{1F1F2}\u{1F1E6}",
  "Haiti": "\u{1F1ED}\u{1F1F9}",
  "Scotland": "\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}",
  "United States": "\u{1F1FA}\u{1F1F8}", "Paraguay": "\u{1F1F5}\u{1F1FE}",
  "Australia": "\u{1F1E6}\u{1F1FA}", "Türkiye": "\u{1F1F9}\u{1F1F7}",
  "Germany": "\u{1F1E9}\u{1F1EA}", "Curaçao": "\u{1F1E8}\u{1F1FC}",
  "Ivory Coast": "\u{1F1E8}\u{1F1EE}", "Ecuador": "\u{1F1EA}\u{1F1E8}",
  "Netherlands": "\u{1F1F3}\u{1F1F1}", "Japan": "\u{1F1EF}\u{1F1F5}",
  "Sweden": "\u{1F1F8}\u{1F1EA}", "Tunisia": "\u{1F1F9}\u{1F1F3}",
  "Belgium": "\u{1F1E7}\u{1F1EA}", "Egypt": "\u{1F1EA}\u{1F1EC}",
  "IR Iran": "\u{1F1EE}\u{1F1F7}", "New Zealand": "\u{1F1F3}\u{1F1FF}",
  "Spain": "\u{1F1EA}\u{1F1F8}", "Cabo Verde": "\u{1F1E8}\u{1F1FB}",
  "Saudi Arabia": "\u{1F1F8}\u{1F1E6}", "Uruguay": "\u{1F1FA}\u{1F1FE}",
  "France": "\u{1F1EB}\u{1F1F7}", "Senegal": "\u{1F1F8}\u{1F1F3}",
  "Iraq": "\u{1F1EE}\u{1F1F6}", "Norway": "\u{1F1F3}\u{1F1F4}",
  "Argentina": "\u{1F1E6}\u{1F1F7}", "Algeria": "\u{1F1E9}\u{1F1FF}",
  "Austria": "\u{1F1E6}\u{1F1F9}", "Jordan": "\u{1F1EF}\u{1F1F4}",
  "Portugal": "\u{1F1F5}\u{1F1F9}", "DR Congo": "\u{1F1E8}\u{1F1E9}",
  "Uzbekistan": "\u{1F1FA}\u{1F1FF}", "Colombia": "\u{1F1E8}\u{1F1F4}",
  "England": "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}",
  "Croatia": "\u{1F1ED}\u{1F1F7}", "Ghana": "\u{1F1EC}\u{1F1ED}",
  "Panama": "\u{1F1F5}\u{1F1E6}",
};
const flag = (name) => FLAGS[name] || "";

// --- funnel diagram --------------------------------------------------------
// Visualizes a team's tournament path as a funnel. Each stage is a vertical
// slice whose height is proportional to the *cumulative* probability of
// reaching that round. Between consecutive stages we draw a trapezoid whose
// converging edges make the round-by-round drop-off intuitive at a glance,
// plus a numeric conditional-survival label.
function funnelSvg(team, color) {
  const stages = [
    {lbl: "Adv",   p: team.advance},
    {lbl: "R16",   p: team.r16},
    {lbl: "QF",    p: team.qf},
    {lbl: "SF",    p: team.sf},
    {lbl: "Final", p: team.final},
    {lbl: "Champ", p: team.champion},
  ];
  const W = 720, H = 170;
  const padX = 36, padTop = 28, padBot = 44;
  const innerH = H - padTop - padBot;
  const midY = padTop + innerH / 2;
  // Floor any tiny prob to a hairline so vanishing slices are still visible.
  const floor = 0.005;
  const pts = stages.map((s, i) => {
    const eff = Math.max(s.p, floor);
    return {
      x: padX + i * ((W - 2 * padX) / (stages.length - 1)),
      h: eff * innerH,
      p: s.p,
      lbl: s.lbl,
    };
  });
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  // Baseline reference for "100%"
  svg += `<line class="funnel-baseline" x1="${padX}" x2="${W-padX}" y1="${midY - innerH/2}" y2="${midY - innerH/2}" stroke-width="1" stroke-dasharray="3,4"/>`;
  svg += `<line class="funnel-baseline" x1="${padX}" x2="${W-padX}" y1="${midY + innerH/2}" y2="${midY + innerH/2}" stroke-width="1" stroke-dasharray="3,4"/>`;
  // Trapezoids
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i], b = pts[i+1];
    const ay1 = midY - a.h/2, ay2 = midY + a.h/2;
    const by1 = midY - b.h/2, by2 = midY + b.h/2;
    svg += `<polygon class="funnel-poly" points="${a.x},${ay1} ${b.x},${by1} ${b.x},${by2} ${a.x},${ay2}" fill="${color}" opacity="${0.85 - i*0.07}"/>`;
  }
  // Stage ticks + value labels
  pts.forEach((pt, i) => {
    const y1 = midY - pt.h/2, y2 = midY + pt.h/2;
    svg += `<line class="stage-tick" x1="${pt.x}" x2="${pt.x}" y1="${y1}" y2="${y2}" stroke-width="1.5"/>`;
    svg += `<text class="stage-lbl" x="${pt.x}" y="${padTop - 12}" text-anchor="middle">${pt.lbl.toUpperCase()}</text>`;
    svg += `<text class="stage-val" x="${pt.x}" y="${H - padBot + 18}" text-anchor="middle" font-family="ui-monospace,monospace">${pct(pt.p)}</text>`;
  });
  // Drop-off labels between stages — conditional survival rate.
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i-1], cur = pts[i];
    const surv = stages[i-1].p > 0 ? (stages[i].p / stages[i-1].p) : 0;
    const cls = surv >= 0.65 ? "drop-lbl ok" : surv < 0.35 ? "drop-lbl big" : "drop-lbl";
    const xm = (prev.x + cur.x) / 2;
    svg += `<text class="${cls}" x="${xm}" y="${H - padBot + 34}" text-anchor="middle" font-family="ui-monospace,monospace">${(surv*100).toFixed(0)}% survive</text>`;
  }
  return `<div class="funnel-wrap">${svg}</svg></div>`;
}

// --- tabs ---
$$("nav.tabs button").forEach(btn => {
  btn.addEventListener("click", () => {
    $$("nav.tabs button").forEach(b => b.classList.toggle("active", b === btn));
    const id = btn.dataset.view;
    $$("section.view").forEach(s => s.classList.toggle("active", s.id === id));
  });
});

// --- champion race ---
function renderChampion() {
  const sorted = [...DATA.teams].sort((a, b) => b.champion - a.champion);
  const top = sorted.slice(0, 24);
  const max = top[0].champion;
  const container = $("#champ-bars");
  container.innerHTML = "";
  top.forEach((t, i) => {
    const row = document.createElement("div");
    row.className = "champ-bar";
    row.dataset.team = t.name;
    const w = max > 0 ? (t.champion / max * 100) : 0;
    row.innerHTML = `
      <div class="rank">${i+1}</div>
      <div class="name"><span class="confed-chip" style="background:${cclr(t.confed)}"></span><span class="fl">${flag(t.name)}</span>${t.name}</div>
      <div class="bar"><div class="fill" style="width:${w.toFixed(1)}%; background:${cclr(t.confed)}"></div></div>
      <div class="pct">${pct(t.champion)}</div>`;
    row.addEventListener("click", () => showChampDetail(t));
    container.appendChild(row);
  });
  showChampDetail(top[0]);
  renderMarket();
}
function showChampDetail(t) {
  const d = $("#champ-detail");
  d.classList.add("shown");
  d.innerHTML = `
    <h3><span class="confed-chip" style="background:${cclr(t.confed)}"></span><span class="fl" style="font-size:1.3em">${flag(t.name)}</span>${t.name} <span style="color:var(--muted); font-weight:400; font-size:12px">— Group ${t.group} · Elo ${t.elo} · att ${t.attack.toFixed(2)} · def ${t.defense.toFixed(2)} · pen skill ${(t.shootout*100).toFixed(0)}%</span></h3>
    ${funnelSvg(t, cclr(t.confed))}
    ${t.market_odds ? `<div style="margin-top:10px; font-size:12px; color:var(--muted)">Bookmaker odds <b style="color:var(--text)">${t.market_odds}</b>${t.poly ? ` · Polymarket <b style="color:var(--text)">${t.poly}%</b>` : ""}</div>` : ""}
  `;
}

// --- market ---
function renderMarket() {
  const m = DATA.market;
  const tbody = $("#market-tbody");
  if (!m.rows.length) { $("#market-card").style.display = "none"; return; }
  const hasPoly = m.rows.some(r => r.poly != null);
  $("#market-overround").textContent = `~${m.overround}%`;
  const head = `<th>Team</th><th>Model</th><th>Market</th>${hasPoly ? "<th>Polymkt</th>" : ""}<th>Odds</th><th>Lean</th>`;
  $("#market-thead").innerHTML = `<tr>${head}</tr>`;
  tbody.innerHTML = "";
  m.rows.sort((a, b) => a.odds - b.odds);
  m.rows.forEach(r => {
    let lean = "≈"; let cls = "lean-eq";
    if (r.model > r.market * 1.15) { lean = "model ▲"; cls = "lean-up"; }
    else if (r.model < r.market * 0.85) { lean = "market ▲"; cls = "lean-down"; }
    tbody.innerHTML += `
      <tr>
        <td>${r.name}</td>
        <td>${pct(r.model)}</td>
        <td>${pct(r.market)}</td>
        ${hasPoly ? `<td>${r.poly != null ? r.poly.toFixed(1) + "%" : "—"}</td>` : ""}
        <td>${r.odds}</td>
        <td class="${cls}">${lean}</td>
      </tr>`;
  });
}

// --- groups view ---
function renderGroups() {
  const root = $("#groups-grid");
  root.innerHTML = "";
  Object.keys(DATA.groups).sort().forEach(letter => {
    const card = document.createElement("div");
    card.className = "group-card";
    card.innerHTML = `<h3>Group ${letter}</h3>`;
    const teams = DATA.groups[letter].map(n => byName[n]);
    teams.sort((a, b) => b.advance - a.advance);
    const maxAdv = Math.max(...teams.map(t => t.advance), 0.01);
    teams.forEach(t => {
      card.innerHTML += `
        <div class="group-team" title="Elo ${t.elo} · att ${t.attack.toFixed(2)} · def ${t.defense.toFixed(2)} · champ ${pct(t.champion)}">
          <span class="confed-chip" style="background:${cclr(t.confed)}"></span>
          <span><span class="fl">${flag(t.name)}</span>${t.name}</span>
          <div class="mini-bar"><div class="fill" style="width:${(t.advance/maxAdv*100).toFixed(0)}%; background:${cclr(t.confed)}"></div></div>
          <span class="num">${pct(t.advance)}</span>
        </div>`;
    });
    const pairs = DATA.group_pairs[letter] || [];
    if (pairs.length) {
      const p = pairs[0];
      card.innerHTML += `<div class="pair-line">Most likely qualifiers · <b>${p.a}</b> + <b>${p.b}</b> · ${pct(p.p)}</div>`;
    }
    root.appendChild(card);
  });
}

// --- bracket view ---
let highlightTeam = null;
function renderBracket() {
  const grid = $("#bracket-grid");
  grid.innerHTML = "";
  DATA.bracket.forEach((tie, i) => {
    const card = document.createElement("div");
    card.className = "tie";
    card.innerHTML = `
      <div class="tie-head"><span>Tie ${i+1}</span><span>${tie.slot_a} v ${tie.slot_b}</span></div>
      <div class="side" data-side="a">
        ${tie.side_a.map(o => `<div class="side-row" data-team="${o.name}"><span class="confed-chip" style="background:${cclr(byName[o.name].confed)}"></span><span class="fl">${flag(o.name)}</span><span class="nm">${o.name}</span><span class="pp">${pct(o.p)}</span></div>`).join("")}
      </div>
      <div class="divider">vs</div>
      <div class="side" data-side="b">
        ${tie.side_b.map(o => `<div class="side-row" data-team="${o.name}"><span class="confed-chip" style="background:${cclr(byName[o.name].confed)}"></span><span class="fl">${flag(o.name)}</span><span class="nm">${o.name}</span><span class="pp">${pct(o.p)}</span></div>`).join("")}
      </div>
      ${tie.pairs.length ? `<div class="pair-most">Top pairing · <b style="color:var(--text)">${tie.pairs[0].a}</b> vs <b style="color:var(--text)">${tie.pairs[0].b}</b> · ${pct(tie.pairs[0].p)}</div>` : ""}
    `;
    grid.appendChild(card);
  });
  $$(".tie .side-row").forEach(row => {
    row.addEventListener("click", () => {
      const team = row.dataset.team;
      highlightTeam = (highlightTeam === team) ? null : team;
      applyHighlight();
      updateBracketStatus();
    });
  });
  // Populate team-finder select.
  const sel = $("#bracket-team");
  sel.innerHTML = `<option value="">— Highlight a team —</option>` +
    [...DATA.teams].sort((a,b) => a.name.localeCompare(b.name))
      .map(t => `<option value="${t.name}">${flag(t.name)} ${t.name} (G${t.group})</option>`).join("");
  sel.addEventListener("change", () => {
    highlightTeam = sel.value || null;
    applyHighlight();
    updateBracketStatus();
  });
  $("#bracket-clear").addEventListener("click", () => {
    highlightTeam = null;
    sel.value = "";
    applyHighlight();
    updateBracketStatus();
  });
}
function applyHighlight() {
  $$(".tie .side-row").forEach(row => {
    row.classList.toggle("highlight", highlightTeam != null && row.dataset.team === highlightTeam);
  });
  $("#bracket-team").value = highlightTeam || "";
}
function updateBracketStatus() {
  const out = $("#bracket-status");
  if (!highlightTeam) { out.innerHTML = ""; return; }
  const t = byName[highlightTeam];
  // Slots where the team appears, sorted by probability.
  const slots = DATA.bracket.flatMap((tie) => {
    const a = tie.side_a.find(o => o.name === highlightTeam);
    const b = tie.side_b.find(o => o.name === highlightTeam);
    const rows = [];
    if (a) rows.push({tie: tie.idx + 1, side: tie.slot_a, p: a.p});
    if (b) rows.push({tie: tie.idx + 1, side: tie.slot_b, p: b.p});
    return rows;
  }).sort((x, y) => y.p - x.p);
  out.innerHTML = `
    <div class="panel" style="margin-top:14px">
      <h2 style="margin-bottom:8px"><span class="fl" style="font-size:1.3em">${flag(t.name)}</span>${t.name} · path probabilities</h2>
      ${funnelSvg(t, cclr(t.confed))}
      ${slots.length ? `<div style="margin-top:12px; font-size:12px; color:var(--muted)">Most likely R32 slots: ${slots.slice(0,4).map(s => `Tie ${s.tie} (${s.side}) <b style="color:var(--text)">${pct(s.p)}</b>`).join(" · ")}</div>` : ""}
    </div>
  `;
}

// --- tipps view ---
function renderTipps() {
  const root = $("#tipps-grid");
  root.innerHTML = "";
  Object.keys(DATA.tipps).sort().forEach(letter => {
    const matches = DATA.tipps[letter];
    const card = document.createElement("div");
    card.className = "tipps-card";
    const total = matches.reduce((s, m) => s + m.ev, 0);
    let html = `<h3>Group ${letter}</h3>`;
    matches.forEach(m => {
      const warn = m.diverges ? "warn" : "";
      html += `
        <div class="tipps-match ${warn}">
          <div class="matchup">
            <div><span class="fl">${flag(m.home)}</span>${m.home} <span style="color:var(--muted)">–</span> <span class="fl">${flag(m.away)}</span>${m.away}</div>
            <div class="wdl">${pct(m.pw)} · ${pct(m.pd)} · ${pct(m.pl)} · most likely ${m.ml[0]}–${m.ml[1]}</div>
          </div>
          <div><span class="tip-pill">${m.tip[0]}–${m.tip[1]}</span></div>
          <div class="ev">${m.ev.toFixed(2)} pts</div>
        </div>`;
    });
    html += `<div class="footer">Expected total · <b style="color:var(--text)">${total.toFixed(2)} pts</b></div>`;
    card.innerHTML = html;
    root.appendChild(card);
  });
}

// --- how-it-works tab -----------------------------------------------------
// Re-implements the Python match model in JS for the explanatory widgets.
// Kept in lockstep with src/model.py — change one, change both.

const LG_AVG = DATA.meta.lg_avg;
const DC_RHO = DATA.meta.dc_rho;
const HOSTS = new Set(DATA.meta.hosts);
const HOST_ATT = DATA.meta.host_attack_mult;
const HOST_DEF = DATA.meta.host_defense_mult;
const MIN_LAM  = DATA.meta.min_lambda;

function lambdas(a, b) {
  let la = a.attack * b.defense / LG_AVG;
  let lb = b.attack * a.defense / LG_AVG;
  if (HOSTS.has(a.name)) { la *= HOST_ATT; lb *= HOST_DEF; }
  if (HOSTS.has(b.name)) { lb *= HOST_ATT; la *= HOST_DEF; }
  return [Math.max(MIN_LAM, la), Math.max(MIN_LAM, lb)];
}
function poisson(k, lam) {
  // exp(-lam) * lam^k / k!
  let p = Math.exp(-lam);
  for (let i = 1; i <= k; i++) p *= lam / i;
  return p;
}
function dcTau(x, y, la, lb, rho) {
  if (x === 0 && y === 0) return Math.max(0, 1 - la*lb*rho);
  if (x === 0 && y === 1) return Math.max(0, 1 + la*rho);
  if (x === 1 && y === 0) return Math.max(0, 1 + lb*rho);
  if (x === 1 && y === 1) return Math.max(0, 1 - rho);
  return 1.0;
}
function scoreGrid(la, lb, N=8) {
  const px = []; const py = [];
  for (let k = 0; k <= N; k++) { px.push(poisson(k, la)); py.push(poisson(k, lb)); }
  const grid = [];
  let total = 0;
  for (let x = 0; x <= N; x++) {
    const row = [];
    for (let y = 0; y <= N; y++) {
      const v = px[x] * py[y] * dcTau(x, y, la, lb, DC_RHO);
      row.push(v); total += v;
    }
    grid.push(row);
  }
  for (let x = 0; x <= N; x++) for (let y = 0; y <= N; y++) grid[x][y] /= total;
  return {grid, px, py};
}
function samplePoisson(lam) {
  // Knuth — fine for small lam.
  const L = Math.exp(-lam);
  let k = 0, p = 1;
  while (true) {
    p *= Math.random();
    if (p <= L) return k;
    k++;
  }
}
function rollMatch(la, lb) {
  // Rejection sampling against the DC correction (cap = max tau).
  const m = Math.max(1, 1 - la*lb*DC_RHO, 1 - DC_RHO);
  while (true) {
    const x = samplePoisson(la), y = samplePoisson(lb);
    if (Math.random() * m <= dcTau(x, y, la, lb, DC_RHO)) return [x, y];
  }
}

function renderWikiFlow() {
  const steps = [
    {lbl: "Ratings",         sub: "attack · defense",  color: cclr("UEFA")},
    {lbl: "Expected goals",  sub: "λ_A, λ_B",          color: cclr("CONMEBOL")},
    {lbl: "Score sample",    sub: "Poisson + DC",      color: cclr("CONCACAF")},
    {lbl: "Group table",     sub: "6 matches",         color: cclr("CAF")},
    {lbl: "Bracket",         sub: "32 → 1",            color: cclr("AFC")},
    {lbl: "Champion",        sub: "count / 20k",       color: cclr("OFC")},
  ];
  const W = 900, H = 100, w = (W - 30) / steps.length;
  let inner = "";
  steps.forEach((s, i) => {
    const x = 8 + i * w;
    inner += `<rect x="${x}" y="22" width="${w-14}" height="58" rx="6" fill="${s.color}" opacity="0.18" stroke="${s.color}" stroke-width="1.5"/>`;
    inner += `<text x="${x + (w-14)/2}" y="46" text-anchor="middle" fill="var(--text)" font-size="13" font-weight="600">${s.lbl}</text>`;
    inner += `<text x="${x + (w-14)/2}" y="66" text-anchor="middle" fill="var(--muted)" font-size="11" font-family="ui-monospace,monospace">${s.sub}</text>`;
    if (i < steps.length - 1) {
      const ax = x + (w-14), bx = 8 + (i+1)*w;
      inner += `<path d="M ${ax} 51 L ${bx} 51" stroke="var(--accent)" stroke-width="1.5" fill="none" marker-end="url(#wikiArrow)"/>`;
    }
  });
  const svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <defs><marker id="wikiArrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L6,3 z" fill="var(--accent)"/></marker></defs>
    ${inner}
  </svg>`;
  $("#wiki-flow").innerHTML = svg;
}

function renderWikiBars() {
  const teams = [...DATA.teams].sort((a, b) => b.attack - a.attack).slice(0, 8);
  const teams_def = [...DATA.teams].sort((a, b) => a.defense - b.defense).slice(0, 8);
  const maxA = Math.max(...DATA.teams.map(t => t.attack));
  const maxD = Math.max(...DATA.teams.map(t => t.defense));
  let html = `<div class="wiki-grid-2">
    <div><div class="wiki-sublabel">Top attacks (goals scored vs avg)</div>`;
  teams.forEach(t => {
    html += `<div class="wiki-bar-row">
      <div class="lbl"><span class="confed-chip" style="background:${cclr(t.confed)}"></span><span class="fl">${flag(t.name)}</span>${t.name}</div>
      <div class="bar"><div class="fill" style="width:${(t.attack/maxA*100).toFixed(0)}%; background:var(--accent)"></div></div>
      <div class="num">${t.attack.toFixed(2)}</div>
    </div>`;
  });
  html += `</div><div><div class="wiki-sublabel">Best defenses (goals conceded vs avg)</div>`;
  teams_def.forEach(t => {
    html += `<div class="wiki-bar-row">
      <div class="lbl"><span class="confed-chip" style="background:${cclr(t.confed)}"></span><span class="fl">${flag(t.name)}</span>${t.name}</div>
      <div class="bar"><div class="fill" style="width:${(t.defense/maxD*100).toFixed(0)}%; background:var(--accent-2)"></div></div>
      <div class="num">${t.defense.toFixed(2)}</div>
    </div>`;
  });
  html += `</div></div>`;
  $("#wiki-bars").innerHTML = html;
  $("#wiki-lgavg").textContent = LG_AVG.toFixed(2);
  $("#wiki-rho").textContent = DC_RHO.toFixed(4);
  $("#wiki-sigma").textContent = DATA.meta.rating_sigma.toFixed(0);
}

function renderWikiFormula() {
  const a = byName[$("#wiki-team-a").value];
  const b = byName[$("#wiki-team-b").value];
  if (!a || !b) return;
  const [la, lb] = lambdas(a, b);
  const hostNote = HOSTS.has(a.name) || HOSTS.has(b.name)
    ? `<div style="color:var(--accent); font-size:11px; margin-top:6px">⚐ Host edge applied: home-soil teams × ${HOST_ATT} attack, × ${HOST_DEF} defense.</div>`
    : "";
  $("#wiki-formula").innerHTML = `
    <div><span class="ann">// raw λ for ${a.name}</span></div>
    <div>λ<sub>${a.name}</sub> = <span class="var">attack(${a.name})</span> × <span class="opn">defense(${b.name})</span> / LG_AVG</div>
    <div>             = <span class="num">${a.attack.toFixed(2)}</span> × <span class="num">${b.defense.toFixed(2)}</span> / <span class="num">${LG_AVG.toFixed(2)}</span> <span class="arrow">→</span> <span class="num"><b>${la.toFixed(2)}</b> goals</span></div>
    <div style="height:6px"></div>
    <div><span class="ann">// raw λ for ${b.name}</span></div>
    <div>λ<sub>${b.name}</sub> = <span class="var">attack(${b.name})</span> × <span class="opn">defense(${a.name})</span> / LG_AVG</div>
    <div>             = <span class="num">${b.attack.toFixed(2)}</span> × <span class="num">${a.defense.toFixed(2)}</span> / <span class="num">${LG_AVG.toFixed(2)}</span> <span class="arrow">→</span> <span class="num"><b>${lb.toFixed(2)}</b> goals</span></div>
    ${hostNote}
  `;
  renderWikiHeatmap(a, b, la, lb);
}

function renderWikiHeatmap(a, b, la, lb) {
  const N = 6;
  const {grid, px, py} = scoreGrid(la, lb, N);
  // Poisson marginal bars (one for each side).
  let bars = `<div style="margin-bottom:10px"><div class="wiki-sublabel"><span class="fl">${flag(a.name)}</span>${a.name} — λ = ${la.toFixed(2)}</div>`;
  let mx = Math.max(...px.slice(0, N+1));
  for (let k = 0; k <= N; k++) {
    bars += `<div class="wiki-pois-row">
      <div class="k">${k}</div>
      <div class="dot" style="background:${cclr(a.confed)}"></div>
      <div class="bar"><div class="fill" style="width:${(px[k]/mx*100).toFixed(0)}%; background:${cclr(a.confed)}"></div></div>
      <div class="pp">${(px[k]*100).toFixed(1)}%</div>
    </div>`;
  }
  bars += `</div><div><div class="wiki-sublabel"><span class="fl">${flag(b.name)}</span>${b.name} — λ = ${lb.toFixed(2)}</div>`;
  mx = Math.max(...py.slice(0, N+1));
  for (let k = 0; k <= N; k++) {
    bars += `<div class="wiki-pois-row">
      <div class="k">${k}</div>
      <div class="dot" style="background:${cclr(b.confed)}"></div>
      <div class="bar"><div class="fill" style="width:${(py[k]/mx*100).toFixed(0)}%; background:${cclr(b.confed)}"></div></div>
      <div class="pp">${(py[k]*100).toFixed(1)}%</div>
    </div>`;
  }
  bars += `</div>`;
  $("#wiki-marginals").innerHTML = bars;

  // Joint heatmap as SVG.
  const cell = 44, pad = 32;
  const size = pad + (N+1) * cell + 8;
  let svg = `<svg viewBox="0 0 ${size} ${size}" preserveAspectRatio="none">`;
  let maxG = 0;
  for (let x = 0; x <= N; x++) for (let y = 0; y <= N; y++) if (grid[x][y] > maxG) maxG = grid[x][y];
  // Cells
  for (let x = 0; x <= N; x++) {
    for (let y = 0; y <= N; y++) {
      const p = grid[x][y];
      const t = maxG > 0 ? p / maxG : 0;
      const fill = `rgba(240, 165, 0, ${(0.05 + t*0.95).toFixed(3)})`;  // accent gold
      const dc = (x <= 1 && y <= 1);
      const stroke = dc ? cclr("UEFA") : "rgba(255,255,255,0.06)";
      const strokeW = dc ? 1.5 : 1;
      svg += `<rect x="${pad + y*cell}" y="${pad + x*cell}" width="${cell-2}" height="${cell-2}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeW}" rx="2"/>`;
      svg += `<text x="${pad + y*cell + (cell-2)/2}" y="${pad + x*cell + (cell-2)/2 + 4}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="10" fill="${t>0.4?'#0d1117':'var(--text)'}">${(p*100).toFixed(p>=0.1?0:1)}%</text>`;
    }
  }
  // Axis labels
  for (let k = 0; k <= N; k++) {
    svg += `<text x="${pad + k*cell + (cell-2)/2}" y="${pad - 8}" text-anchor="middle" fill="var(--muted)" font-size="11">${k}</text>`;
    svg += `<text x="${pad - 8}" y="${pad + k*cell + (cell-2)/2 + 4}" text-anchor="end" fill="var(--muted)" font-size="11">${k}</text>`;
  }
  svg += `<text x="${size/2 + cell/2}" y="12" text-anchor="middle" fill="var(--muted)" font-size="10" font-family="ui-monospace,monospace">${b.name} goals →</text>`;
  svg += `<text x="10" y="${size/2 + cell/2}" text-anchor="middle" fill="var(--muted)" font-size="10" font-family="ui-monospace,monospace" transform="rotate(-90 10 ${size/2 + cell/2})">${a.name} goals →</text>`;
  svg += `</svg>`;
  $("#wiki-heatmap").innerHTML = svg + `<div style="color:var(--muted); font-size:11px; margin-top:4px">Cells (0,0) · (0,1) · (1,0) · (1,1) outlined in blue: Dixon-Coles bumps these. Brightest cell = most likely scoreline.</div>`;
}

// --- roll-a-match state ---
const rollState = { n: 0, w: 0, d: 0, l: 0 };
function rollUpdateTally(x, y, isLast) {
  rollState.n++;
  if (x > y) rollState.w++;
  else if (x < y) rollState.l++;
  else rollState.d++;
  if (isLast) $("#wiki-roll-last").textContent = `${x} · ${y}`;
  $("#wiki-roll-n").textContent = rollState.n;
  $("#wiki-roll-w").textContent = rollState.w;
  $("#wiki-roll-d").textContent = rollState.d;
  $("#wiki-roll-l").textContent = rollState.l;
  const f = (n) => rollState.n ? `${(n/rollState.n*100).toFixed(0)}%` : "—";
  $("#wiki-roll-w-p").textContent = f(rollState.w);
  $("#wiki-roll-d-p").textContent = f(rollState.d);
  $("#wiki-roll-l-p").textContent = f(rollState.l);
}
function rollReset() {
  rollState.n = rollState.w = rollState.d = rollState.l = 0;
  rollUpdateTally(0, 0, false);
  $("#wiki-roll-last").textContent = "— · —";
}

function renderWikiBracketPic() {
  // Schematic 5-column bracket: 32 → 16 → 8 → 4 → 2 → 1.
  const cols = [32, 16, 8, 4, 2, 1];
  const labels = ["R32", "R16", "QF", "SF", "Final", "Champ"];
  const W = 900, H = 220, padX = 30, padY = 18;
  const colW = (W - 2*padX) / (cols.length - 1);
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  cols.forEach((n, i) => {
    const x = padX + i * colW;
    const slotH = (H - 2*padY) / Math.max(n, 2);
    for (let k = 0; k < n; k++) {
      const y = padY + slotH * k + slotH/2;
      svg += `<rect x="${x-22}" y="${y-3}" width="44" height="6" rx="2" fill="${cclr("UEFA")}" opacity="${0.25 + i*0.13}"/>`;
      if (i < cols.length - 1 && k % 2 === 0) {
        const y2 = padY + slotH * (k+1) + slotH/2;
        const ny = (padY + ((H - 2*padY) / Math.max(cols[i+1], 2)) * Math.floor(k/2) + ((H - 2*padY) / Math.max(cols[i+1], 2))/2);
        svg += `<path d="M ${x+22} ${y} L ${x+colW-22} ${ny}" stroke="${cclr("UEFA")}" stroke-width="1" opacity="0.4" fill="none"/>`;
        svg += `<path d="M ${x+22} ${y2} L ${x+colW-22} ${ny}" stroke="${cclr("UEFA")}" stroke-width="1" opacity="0.4" fill="none"/>`;
      }
    }
    svg += `<text x="${x}" y="${H-2}" text-anchor="middle" fill="var(--muted)" font-size="11" font-family="ui-monospace,monospace">${labels[i]} · ${n}</text>`;
  });
  svg += `</svg>`;
  $("#wiki-bracket-pic").innerHTML = svg;
}

function renderWiki() {
  // Populate team pickers.
  const opts = [...DATA.teams].sort((a, b) => a.name.localeCompare(b.name))
    .map(t => `<option value="${t.name}">${flag(t.name)} ${t.name} (G${t.group})</option>`).join("");
  $("#wiki-team-a").innerHTML = opts;
  $("#wiki-team-b").innerHTML = opts;
  $("#wiki-team-a").value = "Spain";
  $("#wiki-team-b").value = "Haiti";
  $("#wiki-team-a").addEventListener("change", renderWikiFormula);
  $("#wiki-team-b").addEventListener("change", renderWikiFormula);
  $("#wiki-swap").addEventListener("click", () => {
    const a = $("#wiki-team-a").value, b = $("#wiki-team-b").value;
    $("#wiki-team-a").value = b;
    $("#wiki-team-b").value = a;
    renderWikiFormula();
    rollReset();
  });
  $("#wiki-roll-btn").addEventListener("click", () => {
    const a = byName[$("#wiki-team-a").value], b = byName[$("#wiki-team-b").value];
    const [la, lb] = lambdas(a, b);
    const [x, y] = rollMatch(la, lb);
    rollUpdateTally(x, y, true);
  });
  $("#wiki-roll-100").addEventListener("click", () => {
    const a = byName[$("#wiki-team-a").value], b = byName[$("#wiki-team-b").value];
    const [la, lb] = lambdas(a, b);
    let last = [0, 0];
    for (let i = 0; i < 100; i++) {
      last = rollMatch(la, lb);
      rollUpdateTally(last[0], last[1], false);
    }
    $("#wiki-roll-last").textContent = `${last[0]} · ${last[1]}`;
  });
  $("#wiki-roll-reset").addEventListener("click", rollReset);

  renderWikiFlow();
  renderWikiBars();
  renderWikiFormula();
  renderWikiBracketPic();
}

renderChampion();
renderGroups();
renderBracket();
renderTipps();
renderWiki();
"""


def _safe_json(obj) -> str:
    """Return JSON safely embeddable in a <script> tag (no `</` injection)."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_dashboard_html(stats: Stats, groups: dict[str, list[Team]],
                         params: ModelParams, n_sims: int, seed,
                         rule: ScoringRule | None = None,
                         n_results: int = 0) -> str:
    rule = rule or PRESETS["check24"]
    payload = _build_payload(stats, groups, params, n_sims, seed, rule,
                             n_results=n_results)
    head = payload["headline"]
    meta = payload["meta"]
    top = sorted(payload["teams"], key=lambda t: -t["champion"])[:3]
    fav = top[0] if top else {"name": "—", "champion": 0.0}
    ci = 1.96 * math.sqrt(max(fav["champion"] * (1 - fav["champion"]), 0) / n_sims) * 100
    body_meta = (f"{n_sims:,} sims · seed {seed} · "
                 f"σ {meta['rating_sigma']:g} Elo · ρ {meta['dc_rho']:g} · "
                 f"{meta['date']}")
    live_banner = ""
    live_kpi = ""
    if n_results:
        live_banner = (
            f'<div class="live-banner">🟢 <b>Live view</b> — '
            f'conditioned on <b>{n_results} played match{"es" if n_results != 1 else ""}</b> '
            f'(data/results.csv). Ratings re-tuned via Elo update; played fixtures '
            f'use their real scoreline in every sim.</div>')
        live_kpi = (
            f'<div class="kpi live"><div class="label">Live state</div>'
            f'<div class="value">{n_results} played</div>'
            f'<div class="sub">ratings re-tuned</div></div>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2026 World Cup Predictor · Interactive Dashboard</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1><span class="accent">⚽ 2026 World Cup</span> · Interactive Predictor</h1>
  <div class="meta">{body_meta}</div>
</header>
{live_banner}
<nav class="tabs">
  <button data-view="view-champion" class="active">🏆 Champion race</button>
  <button data-view="view-groups">📊 Groups</button>
  <button data-view="view-bracket">🪜 Bracket</button>
  <button data-view="view-tipps">🎯 Tipps</button>
  <button data-view="view-howto">📖 How it works</button>
</nav>
<main>

<div class="kpi-row">
  <div class="kpi"><div class="label">Favourite</div><div class="value">{fav["name"]}</div><div class="sub">{fav["champion"]*100:.1f}% (±{ci:.1f}% 95% CI)</div></div>
  <div class="kpi"><div class="label">Top final</div><div class="value">{head["final_a"]} vs {head["final_b"]}</div><div class="sub">{head["final_p"]*100:.1f}% of sims</div></div>
  <div class="kpi"><div class="label">Simulations</div><div class="value">{n_sims:,}</div><div class="sub">seed {seed}</div></div>
  <div class="kpi"><div class="label">Rating σ</div><div class="value">{meta["rating_sigma"]:g} Elo</div><div class="sub">Dixon–Coles ρ = {meta["dc_rho"]:g}</div></div>
  {live_kpi}
</div>

<section id="view-champion" class="view active">
  <div class="champ-grid">
    <div class="panel">
      <h2>Title probability</h2>
      <div id="champ-bars"></div>
    </div>
    <div>
      <div id="champ-detail" class="champ-detail"></div>
      <div id="market-card" class="panel">
        <h2>Model vs. de-vigged market <span style="text-transform:none; letter-spacing:0; color:var(--muted); font-weight:400">(overround <span id="market-overround"></span>)</span></h2>
        <table class="market-table">
          <thead id="market-thead"></thead>
          <tbody id="market-tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
</section>

<section id="view-groups" class="view">
  <div class="panel" style="margin-bottom:14px">
    <h2>12 groups · win-group share · top-2 advance share</h2>
    <div style="color:var(--muted); font-size:12px">Hover a row for ratings + champion odds. The bar shows the team's <b>advance</b> probability relative to the group leader. Most likely qualifier pair shown below each group.</div>
  </div>
  <div id="groups-grid" class="groups-grid"></div>
</section>

<section id="view-bracket" class="view">
  <div class="panel">
    <h2>16 Round-of-32 ties · click a team to highlight every slot it can fill</h2>
    <div class="bracket-controls">
      <select id="bracket-team"></select>
      <button id="bracket-clear" class="clear">Clear</button>
      <span style="color:var(--muted); font-size:12px">Each tie shows the 5 most likely occupants per side and the single most-likely pairing.</span>
    </div>
  </div>
  <div id="bracket-grid" class="bracket-grid"></div>
  <div id="bracket-status"></div>
</section>

<section id="view-tipps" class="view">
  <div class="panel" style="margin-bottom:14px">
    <h2>CHECK24 — point-maximizing tips per group match</h2>
    <div style="color:var(--muted); font-size:12px">
      4 pts exact · 3 pts tendency+goal-diff (incl. non-exact draws) · 2 pts winner only.
      <span style="color:var(--accent)"> Orange pills</span> mark matches where the EV-optimal tip differs from the most likely scoreline.
      <b style="color:var(--text)">Expected total</b> per group sums the per-match EV.
    </div>
  </div>
  <div id="tipps-grid" class="tipps-grid"></div>
</section>

<section id="view-howto" class="view">

  <div class="panel">
    <h2>The big picture · 6 steps from rating to champion</h2>
    <div style="color:var(--muted); font-size:12px; margin-bottom:10px">
      One pass of the simulator walks each team through this pipeline. The Monte Carlo just runs it 20,000 times and counts.
    </div>
    <div id="wiki-flow"></div>
  </div>

  <div class="panel">
    <h2>Step 1 · Two numbers per team</h2>
    <div style="color:var(--muted); font-size:12px; margin-bottom:6px">
      Every team carries an <b style="color:var(--accent)">attack</b> (expected goals vs an average team) and a
      <b style="color:var(--accent-2)">defense</b> (expected goals conceded — <i>lower is better</i>). Derived from Elo + style + a Poisson regression on recent results.
    </div>
    <div id="wiki-bars"></div>
    <div style="color:var(--muted); font-size:11px; margin-top:6px">League average λ = <b style="color:var(--text)" id="wiki-lgavg"></b> goals — that's the "average team" benchmark.</div>
  </div>

  <div class="panel">
    <h2>Step 2 · One match, one formula</h2>
    <div class="wiki-pickers">
      <label>Home <select id="wiki-team-a"></select></label>
      <label>Away <select id="wiki-team-b"></select></label>
      <button id="wiki-swap" class="clear">↔ Swap</button>
    </div>
    <div id="wiki-formula" class="wiki-formula"></div>
  </div>

  <div class="panel">
    <h2>Step 3 · From λ to scorelines</h2>
    <div style="color:var(--muted); font-size:12px; margin-bottom:8px">
      Each side's goals are independently drawn from a Poisson with its λ. Real football under-counts 0-0 / 1-0 / 1-1 — the
      <b style="color:var(--text)">Dixon-Coles correction</b> (ρ = <span id="wiki-rho"></span>) bumps probability into those four cells.
    </div>
    <div class="wiki-grid-2">
      <div>
        <div class="wiki-sublabel">Poisson marginals — P(k goals)</div>
        <div id="wiki-marginals"></div>
      </div>
      <div>
        <div class="wiki-sublabel">Joint scoreline grid (Dixon-Coles applied)</div>
        <div id="wiki-heatmap"></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <h2>Step 4 · Roll a match</h2>
    <div style="color:var(--muted); font-size:12px; margin-bottom:8px">
      Press the button to sample <i>one</i> scoreline from that joint distribution. The simulator does this 103× per tournament (72 group matches + 31 knockouts).
    </div>
    <div class="wiki-roll">
      <button id="wiki-roll-btn" class="roll-btn">🎲 Sample one match</button>
      <button id="wiki-roll-100" class="roll-btn-alt">🎲× Sample 100</button>
      <button id="wiki-roll-reset" class="clear">Reset</button>
      <div id="wiki-roll-last" class="roll-last">— · —</div>
    </div>
    <div class="wiki-roll-tally">
      <div class="tally-card"><div class="tally-lbl">Rolls</div><div class="tally-val" id="wiki-roll-n">0</div></div>
      <div class="tally-card"><div class="tally-lbl">Home wins</div><div class="tally-val" id="wiki-roll-w">0</div><div class="tally-sub" id="wiki-roll-w-p">—</div></div>
      <div class="tally-card"><div class="tally-lbl">Draws</div><div class="tally-val" id="wiki-roll-d">0</div><div class="tally-sub" id="wiki-roll-d-p">—</div></div>
      <div class="tally-card"><div class="tally-lbl">Away wins</div><div class="tally-val" id="wiki-roll-l">0</div><div class="tally-sub" id="wiki-roll-l-p">—</div></div>
    </div>
    <div style="color:var(--muted); font-size:11px; margin-top:6px">
      After enough rolls these should converge to the analytic probabilities shown in Step 3 — that's exactly what the 20,000-sim tournament does, but for every match in the bracket simultaneously.
    </div>
  </div>

  <div class="panel">
    <h2>Step 5 · Group → bracket → champion</h2>
    <div style="color:var(--muted); font-size:12px; margin-bottom:10px">
      Each group plays a 6-match round-robin (every pair, sampled as above). Points: 3 for a win, 1 for a draw. Top 2 of every group plus the 8 best third-placed teams (32 in total) drop into the official FIFA bracket. From there it's straight knockout; a draw at 90' is resolved by a Bayesian-shrunk penalty-shootout skill.
    </div>
    <div id="wiki-bracket-pic"></div>
  </div>

  <div class="panel">
    <h2>Step 6 · Repeat 20,000× = probabilities</h2>
    <div style="color:var(--muted); font-size:12px; margin-bottom:6px">
      All of the above is <i>one</i> sample of how the tournament could play out. Run it 20,000 times, count how often each team wins the title, and the count divided by 20,000 is the title probability you see on the Champion tab.
    </div>
    <div style="color:var(--muted); font-size:12px; margin-top:8px">
      Two extra layers fatten the realistic upset tail beyond a textbook Monte Carlo:
      <ul style="margin: 6px 0 0 0; padding-left: 20px">
        <li><b style="color:var(--text)">Rating uncertainty</b> · σ = <span id="wiki-sigma"></span> Elo. Before each tournament sim, every team's true strength is resampled from a Gaussian around its rating — a point-estimate model is over-confident in the favourites.</li>
        <li><b style="color:var(--text)">Travel · rest · altitude</b>. The tired side scores a touch less and concedes a touch more, applied as a differential between the two sides.</li>
      </ul>
    </div>
  </div>

</section>

</main>
<footer>
  WM Tippspiel · stdlib Monte Carlo · {n_sims:,} sims · {meta["date"]} · one self-contained HTML file (open offline)
</footer>
<script>
const DATA = {_safe_json(payload)};
{_JS}
</script>
</body>
</html>
"""
