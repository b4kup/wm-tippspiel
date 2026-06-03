"""
Render a Monte Carlo `Stats` object into a Markdown predictions report.
"""

from __future__ import annotations

import math
from datetime import date

from .simulate import Stats
from .tournament import Team


def _pct(x: float) -> str:
    if x >= 0.995:
        return "100%"
    if x >= 0.10:
        return f"{x*100:.0f}%"
    if x >= 0.01:
        return f"{x*100:.1f}%"
    if x > 0:
        return f"{x*100:.2f}%"
    return "—"


def _sorted_by(counter: dict, stats: Stats, names: list[str]) -> list[tuple[str, float]]:
    return sorted(((n, stats.prob(counter, n)) for n in names),
                  key=lambda kv: kv[1], reverse=True)


def _append_travel_section(L: list[str], team_names: list[str]) -> None:
    """Per-team group-stage travel + altitude exposure."""
    try:
        from .travel import (load_schedule, load_venues, total_travel_per_team,
                             ALTITUDE_ACCLIMATED_TEAMS, ALTITUDE_THRESHOLD_M)
    except Exception:
        return
    try:
        sched = load_schedule()
        venues = load_venues()
    except FileNotFoundError:
        return
    totals = total_travel_per_team(sched, venues)
    # Altitude exposure: sum of (altitude_excess in m) across a team's matches,
    # zero if the team is acclimated.
    alt_exposure: dict[str, float] = {}
    for m in sched:
        v = venues.get(m.city)
        if v is None:
            continue
        excess = max(0.0, v.altitude_m - ALTITUDE_THRESHOLD_M)
        for t in (m.home, m.away):
            if t in ALTITUDE_ACCLIMATED_TEAMS:
                continue
            alt_exposure[t] = alt_exposure.get(t, 0.0) + excess
    rows = sorted(
        ((t, totals.get(t, 0.0), alt_exposure.get(t, 0.0)) for t in team_names),
        key=lambda r: -(r[1] + r[2] * 5),     # rank by combined burden
    )
    L.append("## ✈️ Group-stage travel & altitude burden\n")
    L.append("Total km flown between consecutive venues and total altitude "
             "exposure (sum of metres above 1500 m across the three group "
             "matches; 0 for teams from highland nations). Both feed into "
             "a small attack/defense penalty in the match where they apply.\n")
    L.append("| Team | km | Altitude m·matches | Notes |")
    L.append("|------|---:|-------------------:|:------|")
    for name, km, alt in rows[:12]:
        notes = []
        if name in ALTITUDE_ACCLIMATED_TEAMS:
            notes.append("altitude-acclimated")
        if km > 4500:
            notes.append("coast-to-coast group")
        if alt > 2000:
            notes.append("heavy altitude")
        L.append(f"| {name} | {km:.0f} | {alt:.0f} | {', '.join(notes) or '—'} |")
    L.append("")


def _append_injury_section(L: list[str], injuries) -> None:
    """List the squad-availability adjustments folded into the ratings."""
    if not injuries:
        return
    from .injuries import team_adjustments

    adj = team_adjustments(injuries)
    L.append("## 🩹 Injuries & availability\n")
    L.append("Current absences nudge the affected teams' attack/defense ratings "
             "(see `data/injuries.csv`; run with `--no-injuries` for full "
             "strength). A forward out dents **attack**; a defender or keeper out "
             "worsens **defense**.\n")
    L.append("| Team | Att | Def | Out / doubtful |")
    L.append("|------|----:|----:|:---------------|")
    for team in sorted(adj, key=lambda t: adj[t].elo_delta):
        a = adj[team]
        players = ", ".join(
            i.player + ("" if i.status.lower() == "out" else f" ({i.status})")
            for i in sorted(a.injuries, key=lambda i: -i.elo_loss))
        L.append(f"| {team} | {(a.attack_mult - 1) * 100:+.0f}% "
                 f"| {(a.defense_mult - 1) * 100:+.0f}% | {players} |")
    L.append("\n*Att/Def columns show the percentage change to each rating "
             "(defense `+` = more goals conceded). Doubtful/questionable players "
             "count at a reduced weight.*\n")


def build_report(stats: Stats, groups: dict[str, list[Team]],
                 n_sims: int, seed, params, injuries=None) -> str:
    teams = [t for g in groups.values() for t in g]
    by_name = {t.name: t for t in teams}
    names = [t.name for t in teams]
    L: list[str] = []

    L.append("# 2026 FIFA World Cup — Statistical Predictions\n")
    L.append(f"*Generated {date.today().isoformat()} from "
             f"{n_sims:,} Monte Carlo simulations (seed `{seed}`).*\n")
    L.append("> Hosts: United States · Canada · Mexico. 48 teams, 12 groups of 4. "
             "Top 2 of each group plus the 8 best third-placed teams reach the "
             "Round of 32.\n")

    # ---- Title odds ------------------------------------------------------
    L.append("## 🏆 Title probability (all 48 teams)\n")
    L.append("| # | Team | Champion | Final | Semi | Quarter | R16 |")
    L.append("|--:|------|---------:|------:|-----:|--------:|----:|")
    champ_sorted = _sorted_by(stats.champion, stats, names)
    for i, (name, p) in enumerate(champ_sorted, 1):
        L.append(f"| {i} | {name} | {_pct(p)} "
                 f"| {_pct(stats.prob(stats.reach_final, name))} "
                 f"| {_pct(stats.prob(stats.reach_sf, name))} "
                 f"| {_pct(stats.prob(stats.reach_qf, name))} "
                 f"| {_pct(stats.prob(stats.reach_r16, name))} |")
    L.append("")

    # ---- Most likely final & champion -----------------------------------
    top_final = max(stats.finals.items(), key=lambda kv: kv[1])
    (fa, fb), fc = top_final
    # 95% Monte Carlo sampling error on the favourite's title probability.
    cp = champ_sorted[0][1]
    ci = 1.96 * math.sqrt(max(cp * (1 - cp), 0) / n_sims)
    L.append("## 🎯 Headline calls\n")
    L.append(f"- **Most likely champion:** {champ_sorted[0][0]} "
             f"({_pct(champ_sorted[0][1])}, ±{ci*100:.1f}% Monte Carlo 95% CI)")
    L.append(f"- **Most likely final pairing:** {fa} vs {fb} "
             f"({_pct(fc / n_sims)} of simulations)")
    podium = ", ".join(f"{n} {_pct(p)}" for n, p in champ_sorted[:4])
    L.append(f"- **Top contenders:** {podium}\n")

    # ---- Injuries / availability ----------------------------------------
    _append_injury_section(L, injuries)

    # ---- Travel / rest / altitude burden --------------------------------
    _append_travel_section(L, names)

    # ---- Group-by-group --------------------------------------------------
    L.append("## 📊 Group stage\n")
    L.append("Probability each team **wins its group** / **advances** "
             "(top 2, before best-third places are counted).\n")
    for letter, gteams in groups.items():
        rows = sorted(
            ((t, stats.prob(stats.win_group, t.name),
              stats.prob(stats.advance, t.name)) for t in gteams),
            key=lambda r: r[2], reverse=True)
        L.append(f"**Group {letter}**\n")
        L.append("| Team | Elo | Att | Def | Win group | Advance |")
        L.append("|------|----:|----:|----:|----------:|--------:|")
        for t, wg, adv in rows:
            L.append(f"| {t.name} | {t.elo:.0f} | {t.attack:.2f} | {t.defense:.2f} "
                     f"| {_pct(wg)} | {_pct(adv)} |")
        # Most likely qualifying pair.
        pair, cnt = max(stats.group_pairs[letter].items(), key=lambda kv: kv[1])
        L.append(f"\n*Most likely qualifiers: {pair[0]} (1st) & {pair[1]} (2nd) "
                 f"— {_pct(cnt / n_sims)}.*\n")

    # ---- Market comparison ----------------------------------------------
    market = [(t, t.market_decimal_odds) for t in teams
              if t.market_decimal_odds]
    if market:
        # De-vig: bookmaker decimal odds imply probabilities that sum to >100%
        # (the margin). Normalising by their total over the teams that have odds
        # removes the margin and makes a like-for-like comparison with the model.
        overround = sum(1.0 / o for _t, o in market)
        has_poly = any(t.polymarket_prob for t, _ in market)
        L.append("## 💰 Model vs. betting market\n")
        L.append("Model champion probability vs. the **de-vigged** market "
                 "probability (`(1 / decimal odds)` normalised across the listed "
                 "teams to strip out the bookmaker margin of "
                 f"~{(overround - 1) * 100:.0f}%). A sanity check, and a way to "
                 "spot where the model disagrees with the market.\n")
        if has_poly:
            # Polymarket is real-money, already de-vigged — useful sharp signal
            # for the top of the market. Listed for teams with a liquid contract.
            spain = by_name.get("Spain")
            france = by_name.get("France")
            if spain and france and spain.polymarket_prob and france.polymarket_prob:
                L.append(f"> Polymarket (real-money) has **France {france.polymarket_prob}%** "
                         f"ahead of **Spain {spain.polymarket_prob}%** — bookmakers still "
                         "have Spain a fraction shorter. The two sharpest market views "
                         "disagree on the favourite.\n")
            L.append("| Team | Model | Market (de-vig) | Polymarket | Decimal odds | Lean |")
            L.append("|------|------:|----------------:|-----------:|-------------:|:-----|")
        else:
            L.append("| Team | Model | Market (de-vig) | Decimal odds | Lean |")
            L.append("|------|------:|----------------:|-------------:|:-----|")
        for t, odds in sorted(market, key=lambda kv: kv[1]):
            model_p = stats.prob(stats.champion, t.name)
            implied = (1.0 / odds) / overround
            lean = "model higher" if model_p > implied * 1.15 else (
                   "market higher" if model_p < implied * 0.85 else "≈ agree")
            if has_poly:
                poly = f"{t.polymarket_prob:.1f}%" if t.polymarket_prob else "—"
                L.append(f"| {t.name} | {_pct(model_p)} | {_pct(implied)} "
                         f"| {poly} | {odds:g} | {lean} |")
            else:
                L.append(f"| {t.name} | {_pct(model_p)} | {_pct(implied)} "
                         f"| {odds:g} | {lean} |")
        L.append("")

    # ---- Methodology -----------------------------------------------------
    L.append("## 🔬 Methodology\n")
    L.append(
        "- **Engine:** Monte Carlo. The full tournament (72 group matches + "
        "31 knockout matches) is simulated "
        f"{n_sims:,} times; every probability is the share of simulations in "
        "which the event happened.\n"
        "- **Match model:** each team has an **attack** rating (expected goals "
        "scored vs an average team) and a **defense** rating (expected goals "
        "conceded). A match's expected goals combine as "
        "`λ_A = attack_A · defense_B / LG_AVG`, then scorelines are drawn from "
        "Poisson distributions with a **Dixon-Coles** low-score correction "
        f"(ρ = {params.dc_rho:g}) that lifts 0-0/1-0/1-1 outcomes to match real "
        "football. Hosts get a small home edge; drawn knockout games are settled "
        "by an Elo-weighted shootout.\n"
        "- **Rating uncertainty:** each team's *true* tournament strength is "
        f"resampled every simulation from a Gaussian (σ = {params.rating_sigma_elo:.0f} "
        "Elo) around its rating, capturing both rating error and tournament-level "
        "form. Without this a point-estimate model is over-confident in the "
        "favourites; resampling fattens the upset tail toward reality.\n"
        "- **Sampling error:** probabilities carry Monte Carlo noise of "
        "≈ √(p(1−p)/N); the favourite's 95% interval is shown above. More "
        "`--sims` tightens it.\n"
        "- **Ratings:** derived from a June-2026 Elo strength snapshot plus a "
        "per-team offensive/defensive style tilt (see `data/derive_ratings.py`), "
        "then adjusted for current injuries/absences (`data/injuries.csv`, "
        "see the Injuries section above; `--no-injuries` disables it).\n"
        "- **Tie-breakers:** group tables rank by points, goal difference, then "
        "goals for; remaining ties (and head-to-head / fair-play / drawing of "
        "lots) are approximated by a random nudge.\n")
    L.append("### Caveats\n")
    L.append(
        "- Ratings are a hand-assembled snapshot, not a live feed — replace "
        "`data/teams.csv` with better numbers to improve fidelity "
        "(see `DATA_SOURCES.md`).\n"
        "- The knockout bracket is the **official** FIFA bracket (match numbers, "
        "third-place cluster codes and tree), encoded in `data/bracket.py`. Which "
        "third-placed team fills each slot depends on the qualifying groups; it is "
        "resolved by a constraint-respecting matching.\n"
        "- Known injuries are folded in via `data/injuries.csv`, but the model "
        "still can't capture in-tournament momentum, red cards or a hot "
        "goalkeeper. Treat these as probabilities, not prophecies.\n")
    return "\n".join(L)
