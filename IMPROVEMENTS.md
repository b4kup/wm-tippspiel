# Improvement roadmap

Ideas for making the 2026 World Cup predictor better, grouped by the *kind* of
improvement, with rough **impact** and **effort** for each. The current model is
a pure-stdlib Monte Carlo using hand-assembled attack/defense ratings and a
reconstructed bracket — a solid baseline, but every section below is a real step
up.

> **Prerequisite for most data work:** this environment routes outbound traffic
> through a host allowlist (only `WebSearch` works; direct `curl`/`WebFetch` of
> arbitrary sites returns `403 Host not in allowlist`). To pull live data we
> either loosen the network policy when creating the session, or the data is
> pasted/committed in by hand. See
> https://code.claude.com/docs/en/claude-code-on-the-web

Legend — Impact: ⭐ low · ⭐⭐ medium · ⭐⭐⭐ high. Effort: 🔨 small · 🔨🔨 medium · 🔨🔨🔨 large.

---

## 1. Input fidelity — the biggest lever
The model can't be better than `data/teams.csv`. Today those numbers are a
documented snapshot, not a feed.

- **Real xG-based attack/defense** — ⭐⭐⭐ / 🔨🔨 — ✅ **DONE** (goals-based, xG-style follow-up TODO)
  `src/qualifying_fit.py` blends each team's 2026 qualifying goals
  (`data/qualifying.csv`) with the Elo+style prior, using confederation-typical
  opponent strength to undo field-strength bias (UEFA quals include far weaker
  opponents than the WC field; CONMEBOL is uniformly hard). Shrinkage weight
  `N / (N + 20)` keeps small qualifying samples close to the Elo prior; 6-match
  teams get ~23% data weight, 18-match teams ~47%. Hosts (no quals) and a
  couple of playoff winners we couldn't source keep their Elo-derived values.
  Effect: Spain pulls away (17.8%; 3.5 GF/match in UEFA quals); Morocco/Japan
  enter top 9 from data signal; Germany drops out of top 10. *Still TODO:*
  swap goals for **xG** (FBref/StatsBomb) — would handle the "Morocco
  over-performed xG" / "Norway over-performed xG" cases better.
- **Opponent- & venue-adjusted ratings via Poisson regression** — ⭐⭐⭐ / 🔨🔨🔨 — ✅ **DONE**
  `src/poisson_fit.py` fits per-team α (attack) and δ (defence) plus a global
  home-advantage γ via the Maher (1982) fixed-point iteration on 733 match
  results scraped from Wikipedia (`src/scrape_wiki.py` + `scrape.py`). Match
  set: 2024 Copa America, Euro 2024, AFCON 2023, 2023 Asian Cup, 2025 Gold
  Cup, all 2026 WC qualifying campaigns. The fit uses damped updates,
  parameter clipping (|α|, |δ| ≤ 1.4) and an L2 pseudo-count prior for
  numerical stability. Results are shrunk back to the Elo+style prior with
  `N / (N + 25)` weighting — the Elo prior carries the cross-confederation
  signal the data alone can't reach (most matches are within-confed). Effect:
  top tier (Argentina/Spain/France/England) tightens to a 5% spread; Japan
  rises (best AFC qualifier); Australia stays bounded by the prior.
- **Squad-availability adjustments** — ⭐⭐ / 🔨🔨 — ✅ **DONE**
  `data/injuries.csv` + `src/injuries.py` nudge a team's attack/defense/Elo down
  for injured/absent players (position decides whether attack or defense takes
  the hit; status scales it). Applied by default at load time and shown in the
  predictions report; `--no-injuries` runs full strength. *Still TODO:* drive it
  from a squad-value/minutes feed (Transfermarkt) instead of a curated list.
- **Confederation strength priors** — ⭐⭐ / 🔨🔨
  AFC/CONCACAF/OFC sides are systematically mis-rated vs UEFA/CONMEBOL.
  Calibrate a per-confederation correction from inter-confederation history.
- **Market-anchored ratings (Bayesian shrinkage)** — ⭐⭐ / 🔨🔨
  Blend the model with the de-vigged betting market (markets are hard to beat).
  Shrink team strengths toward market-implied values by a tunable weight.

## 2. Match-model sophistication
- **Dixon-Coles low-score correction** — ⭐⭐⭐ / 🔨 — ✅ **DONE**
  Independent Poisson *understates* 0-0, 1-0 and 1-1 — the scorelines that decide
  tournaments. Implemented via `ModelParams.dc_rho` (default −0.10), sampled
  exactly by rejection in `_sample_goals()`; tune with `--dc-rho`.
- **Bivariate / correlated goals** — ⭐⭐ / 🔨🔨
  Model the correlation between the two teams' goals rather than assuming
  independence.
- **Penalty-shootout model** — ⭐⭐ / 🔨 — ✅ **DONE**
  `src/shootout.py` + `data/shootouts.csv` give each team a Bayesian-shrunk
  posterior shootout win-rate (Beta-Binomial, α=β=8 prior at 50%). The Elo
  coin-flip in `simulate_knockout` is replaced by `skill_a / (skill_a + skill_b)`.
  Shrinkage caps even Germany (7-1 history) at 62.5% and Netherlands (1-5)
  at 41% — small samples can't move the prior far. Croatia rises into the
  top 10 (4-1 history); France/Spain drop (both rated weak at pens).
- **Travel / rest / altitude / heat** — ⭐⭐ / 🔨🔨 — ✅ **DONE** (travel + rest + altitude)
  `src/travel.py` + `data/schedule.csv` + `data/venues.csv` compute per-team
  km between consecutive group venues, days since last match, and altitude
  exposure (Mexico City 2240 m, Guadalajara 1567 m; teams from highland
  nations — Mexico, Ecuador, Colombia — are unaffected). Three new
  `ModelParams` (`travel_per_1000km`, `rest_day_value`, `altitude_per_1000m`)
  feed an asymmetric fatigue differential into `expected_goals`: the tired
  side scores less and concedes more. *Still TODO:* heat (Miami/Houston in
  summer) and a KO-stage extension that re-computes carryover per sim once
  the bracket fills in.
- **Time-varying form** — ⭐ / 🔨🔨
  Weight recent results more heavily; let strength drift over a campaign.

## 3. Structural correctness
- **Exact official FIFA bracket** — ⭐⭐ / 🔨🔨 — ✅ **DONE**
  `data/bracket.py` now holds the official bracket (match numbers W73–W104,
  third-place cluster codes, full tree). The exact 495-scenario third-place
  table is approximated by a constraint-respecting matching of qualifying thirds
  to slots (any legal matching has negligible effect on aggregate probabilities).
- **Real group tie-breakers** — ⭐ / 🔨
  Head-to-head then goal difference, goals scored, fair-play — instead of the
  current random nudge.
- **Schedule-aware simulation** — ⭐ / 🔨🔨
  Use the real fixture list and rest days per team.

## 4. Uncertainty & validation — what makes it trustworthy
- **Propagate rating uncertainty** — ⭐⭐⭐ / 🔨🔨 — ✅ **DONE**
  Draw each team's *true* strength from a distribution every simulation.
  Point-estimate Monte Carlo is **overconfident** — almost certainly why the
  model showed Spain ~22% vs the market's ~15%. Implemented via
  `ModelParams.rating_sigma_elo` (default 45) and `perturb_team()`; tune with
  `--rating-sigma`. Spain now ~20% and the upset tail is fatter. The *value* of
  σ should be fixed by the backtest below.
- **Backtest & calibrate on 2018 & 2022** — ⭐⭐⭐ / 🔨🔨 — ✅ **DONE**
  `tune.py` + `src/backtest.py` + `src/tune.py` score the model
  analytically (no Monte Carlo) on 2018 + 2022 outcomes with log-loss /
  Brier, then auto-tune `lg_avg`, `K_Q`, `dc_rho`, host edges via a stdlib
  Nelder-Mead simplex. `--apply` rewrites the default constants in
  `src/model.py` and `data/derive_ratings.py`. Report at
  `output/backtest.md`. Caveat: historical Elos are synthetic (FIFA-rank
  ordering, rescaled to canonical spread) — a real eloratings.net feed
  would tighten the fit. Host-edge bounds tend to be hit on the current
  2-host sample (Russia 2018 overperformed, Qatar 2022 underperformed),
  so those values are best treated as suggestive.
- **Reliability / calibration plots** — ⭐⭐ / 🔨
  Do events we call "30%" happen ~30% of the time?
- **Monte Carlo error bars** — ⭐ / 🔨
  Report binomial ± on every probability so readers know the sampling noise.

## 5. The Tippspiel angle — possibly the actual point
A prediction *pool* rewards **points under its scoring rules**, which is **not**
the same as picking the most likely outcome — if everyone picks the favorite,
the EV-maximizing play can be a contrarian champion.

- **Point-maximizing picks under your pool's rules** — ⭐⭐⭐ / 🔨🔨 — ✅ **DONE**
  `tipps.py` + `src/tippspiel.py` compute, for every group match, the scoreline
  that **maximizes expected points** under a configurable rule (default kicktipp
  4/3/2). Confirms the key insight: the EV-optimal tip differs from the most
  likely score in ~80% of matches. Still **TODO**: contrarian/pool-aware picks
  (account for what others tip) and knockout tips once matchups resolve.
- **Exact-score predictions per fixture** — ⭐⭐ / 🔨 — ✅ **DONE** (group stage)
  `tipps.py` lists the most likely scoreline alongside the EV-optimal tip and the
  win/draw/loss split for each group match.
- **Risk profiles** — ⭐ / 🔨🔨
  "Safe" (maximize expected points) vs. "aggressive" (maximize chance of *winning*
  the pool) pick sets.

## 6. Product & engineering
- **Live re-simulation during the tournament** — ⭐⭐⭐ / 🔨🔨 — ✅ **DONE**
  `update.py` ingests `data/results.csv`, conditions the simulation on played
  matches, **re-tunes ratings** from observed form (Elo update), re-simulates the
  rest, **scores our tips** under CHECK24, reports how reality matched our
  predictions (Brier / log-loss / tendency accuracy + biggest surprises), and
  re-optimizes upcoming tips. `safe`/`aggressive` risk modes included as a
  lightweight pool-position lever. (Full pool-standings-aware contrarian
  optimization is still TODO; needs other players' picks.)
- **Charts & bracket dashboard** — ⭐⭐ / 🔨🔨
  Probability bars, a visual bracket, group tables — a real "Tippspiel" front end.
- **Sensitivity analysis** — ⭐⭐ / 🔨
  Which assumptions move the title odds most? Tornado chart over key inputs.
- **Scenario tool** — ⭐ / 🔨
  "What if Spain's main striker is injured?" — adjust a rating and re-run.
- **numpy vectorization** — ⭐ / 🔨🔨
  Currently ~10s / 50k sims in pure stdlib; numpy enables millions of sims.
- **GitHub Action to regenerate the report** — ⭐ / 🔨
  Auto-rebuild `output/predictions.md` on push / on a schedule.

---

## Suggested sequencing

1. **§4 Uncertainty + backtest** — first, because it's the difference between a
   toy and a calibrated model, and it'll confirm the current overconfidence
   *before* we over-invest in fancy inputs.
2. **§1 Real xG data** — the single biggest fidelity gain once ratings are
   trusted.
3. **§2 Dixon-Coles** — small change, real accuracy bump.
4. **§5 Tippspiel-optimal picks** — the highest-value *feature* if this is for an
   actual pool.
5. Everything else as polish / product.
