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

- **Real xG-based attack/defense** — ⭐⭐⭐ / 🔨🔨 — ✅ **DONE** (goals-based; xG drop-in slot wired in `src/xg_fit.py`)
  `src/qualifying_fit.py` blends each team's 2026 qualifying goals
  (`data/qualifying.csv`) with the Elo+style prior, using confederation-typical
  opponent strength to undo field-strength bias (UEFA quals include far weaker
  opponents than the WC field; CONMEBOL is uniformly hard). Shrinkage weight
  `N / (N + 20)` keeps small qualifying samples close to the Elo prior; 6-match
  teams get ~23% data weight, 18-match teams ~47%. Hosts (no quals) and a
  couple of playoff winners we couldn't source keep their Elo-derived values.
  Effect: Spain pulls away (17.8%; 3.5 GF/match in UEFA quals); Morocco/Japan
  enter top 9 from data signal; Germany drops out of top 10. The xG path is
  wired up: drop a `data/qualifying_xg.csv` (columns `team,confederation,
  matches,gf,ga,xg_for,xg_against`) and `src/xg_fit.py` takes over from the
  goals-based blend. FBref / StatsBomb are firewalled in this environment,
  so the file is not committed; populate it from any workstation with
  unrestricted network access.
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
  predictions report; `--no-injuries` runs full strength. `src/transfermarkt.py`
  + `fetch_transfermarkt.py` pull a club's squad page and parse player + market
  value + best-effort injury flag, intended as an audit aid for the curated
  list (cross-check before committing changes — the HTML drifts).
- **Confederation strength priors** — ⭐⭐ / 🔨🔨 — ✅ **DONE**
  `src/confederation_fit.py` averages cross-confederation log-residuals
  (`actual goals / Elo-predicted goals`) across `data/matches_recent.csv`,
  shrinks each by `N / (N + 30)`, and centres so the sample-weighted mean
  is zero. The resulting per-confederation `(Δα, Δδ)` offsets are folded
  into `data/derive_ratings.py` before the Elo prior is shipped to the
  Poisson fit, so confederations that don't play each other much no longer
  inherit the Elo-only bias.
- **Market-anchored ratings (Bayesian shrinkage)** — ⭐⭐ / 🔨🔨 — ✅ **DONE**
  `src/market_fit.py` reads each team's `market_decimal_odds`, de-vigs across
  the listed teams, and shrinks attack/defense in log-space toward the
  implied title-strength signal. Tunable with `python run.py --market-weight`
  (default 0; 0.20 is the typical sane anchor — nudge, don't snap).
  Polymarket real-money probabilities are also available in `data/teams.csv`
  for a sharper top-of-market read.

## 2. Match-model sophistication
- **Dixon-Coles low-score correction** — ⭐⭐⭐ / 🔨 — ✅ **DONE**
  Independent Poisson *understates* 0-0, 1-0 and 1-1 — the scorelines that decide
  tournaments. Implemented via `ModelParams.dc_rho` (default −0.10), sampled
  exactly by rejection in `_sample_goals()`; tune with `--dc-rho`.
- **Bivariate / correlated goals** — ⭐⭐ / 🔨🔨 — ✅ **DONE** (off by default)
  `ModelParams.bivariate_shared_lambda` enables a Karlis-Ntzoufras
  shared-component bivariate Poisson on top of Dixon-Coles. When set > 0,
  scoreline samples draw a common Poisson(λ_shared) shock added to both
  sides (after subtracting λ_shared from each marginal so the totals stay
  calibrated). Default 0 — DC already captures the dominant low-score
  correlation; the shared-component layer is an experimental knob for
  modelling open-game overdispersion.
- **Penalty-shootout model** — ⭐⭐ / 🔨 — ✅ **DONE**
  `src/shootout.py` + `data/shootouts.csv` give each team a Bayesian-shrunk
  posterior shootout win-rate (Beta-Binomial, α=β=8 prior at 50%). The Elo
  coin-flip in `simulate_knockout` is replaced by `skill_a / (skill_a + skill_b)`.
  Shrinkage caps even Germany (7-1 history) at 62.5% and Netherlands (1-5)
  at 41% — small samples can't move the prior far. Croatia rises into the
  top 10 (4-1 history); France/Spain drop (both rated weak at pens).
- **Travel / rest / altitude / heat** — ⭐⭐ / 🔨🔨 — ✅ **DONE**
  `src/travel.py` + `data/schedule.csv` + `data/venues.csv` compute per-team
  km between consecutive venues, days since last match, altitude exposure
  (Mexico City 2240 m, Guadalajara 1567 m; teams from highland nations —
  Mexico, Ecuador, Colombia — unaffected), and heat exposure (Miami/Houston/
  Dallas/Monterrey afternoons 32-35 °C; climate-controlled stadiums and
  teams from hot-climate domestic leagues take a reduced or zero penalty).
  Four `ModelParams` (`travel_per_1000km`, `rest_day_value`,
  `altitude_per_1000m`, `heat_per_degree`) feed an asymmetric fatigue
  differential into `expected_goals`. The KO bracket gets its own
  per-sim carryover (`src/travel.ko_team_fatigue` + `KO_SCHEDULE`),
  threaded through `simulate_tournament_once` so each round's tie uses
  the *winner's* last fixture as its starting point.
- **Time-varying form** — ⭐ / 🔨🔨 — ✅ **DONE**
  `src/poisson_fit.fit_poisson` now accepts `half_life_days` + `ref_date`
  for date-level exponential recency weighting (preferred over the coarse
  year-bucket schedule). `data/derive_ratings.py` runs it with an 18-month
  half-life against a 2026-06-03 reference: matches one year old weight at
  ~63%, two years old ~40%, three years old ~25% — a smooth taper instead
  of the old hard year cliffs.

## 3. Structural correctness
- **Exact official FIFA bracket** — ⭐⭐ / 🔨🔨 — ✅ **DONE**
  `data/bracket.py` now holds the official bracket (match numbers W73–W104,
  third-place cluster codes, full tree). The exact 495-scenario third-place
  table is approximated by a constraint-respecting matching of qualifying thirds
  to slots (any legal matching has negligible effect on aggregate probabilities).
- **Real group tie-breakers** — ⭐ / 🔨 — ✅ **DONE**
  `src/tournament._resolve_overall_ties` walks the full FIFA tiebreaker
  chain: points / overall GD / overall GF, then a head-to-head mini-table
  (points / GD / GF among the tied teams using their direct matches),
  then a random nudge for residual ties (which stands in for fair-play
  and drawing of lots). The per-team `GroupRow.h2h` ledger records each
  pairing's points + goals so the H2H lookup is sample-consistent.
- **Schedule-aware simulation** — ⭐ / 🔨🔨 — ✅ **DONE**
  Group-stage travel/rest already used `data/schedule.csv`; the KO-stage
  extension above completes the loop. Both feed real fixture dates and
  venues through the fatigue model on every sim.

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
- **Reliability / calibration plots** — ⭐⭐ / 🔨 — ✅ **DONE**
  `output/backtest.md` now ships a ten-bin calibration table with an ASCII
  reliability bar (observed frequency overlay vs predicted bin centre) and
  a sample-weighted Expected Calibration Error (ECE) headline so you can
  see at a glance which probability bands the model under- or over-shoots.
- **Monte Carlo error bars** — ⭐ / 🔨 — ✅ **DONE**
  `output/predictions.md` shows the 95% binomial Wald interval next to
  each team's title probability (`p ± 1.96 · √(p(1−p)/N)`), with a note
  on the assumption above the table.

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
- **Risk profiles** — ⭐ / 🔨🔨 — ✅ **DONE**
  `tipps.py` and `update.py` both expose `--risk safe|aggressive|contrarian`.
  `safe` is pure EV maximisation; `aggressive` chases exact scores (most
  likely scoreline) when you're trailing; `contrarian` is EV with a small
  crowd-overlap penalty so near-ties tip the less-popular pick to gain
  differentiation. `src/tippspiel.optimal_tip(grid, rule, risk=...)` is
  the shared entry point.

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
- **Sensitivity analysis** — ⭐⭐ / 🔨 — ✅ **DONE**
  `python sensitivity.py` runs the Monte Carlo at ±10% perturbations on
  eight key parameters (`lg_avg`, `dc_rho`, host edges, rating σ, travel /
  altitude / heat weights) and writes a per-team tornado table to
  `output/sensitivity.md`. The longest bars per team mark the assumptions
  that most move their title odds.
- **Scenario tool** — ⭐ / 🔨 — ✅ **DONE**
  `python run.py --scenario "Spain:attack*0.85"` (or `--scenario
  "Brazil:elo+30"`) nudges a team along one rating axis and re-runs. The
  flag is repeatable for multi-team scenarios; spec format is
  `TEAM:FIELD<op>VALUE` with `FIELD ∈ {elo, attack, defense}` and
  `<op> ∈ {*, +}`. See `src/scenario.py`.
- **numpy vectorization** — ⭐ / 🔨🔨 — *skipped*
  CLAUDE.md forbids new dependencies (stdlib only); the project deliberately
  trades the speedup for zero-install reproducibility.
- **GitHub Action to regenerate the report** — ⭐ / 🔨 — ✅ **DONE**
  `.github/workflows/predict.yml` rebuilds `output/predictions.md`,
  `output/tipps.md`, and `output/live_status.md` (when results exist) on
  push, nightly during the tournament window, and on manual dispatch.
  Commits the refreshed reports back as `chore: regenerate reports [skip ci]`.

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
