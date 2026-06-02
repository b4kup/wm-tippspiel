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

- **Real xG-based attack/defense** — ⭐⭐⭐ / 🔨🔨
  Replace the Elo+style derivation with actual expected-goals-for/against over
  recent internationals (FBref/StatsBomb), recency-weighted. This is the upgrade
  already planned. See `DATA_SOURCES.md`.
- **Opponent- & venue-adjusted ratings via Poisson regression** — ⭐⭐⭐ / 🔨🔨🔨
  Instead of eyeballing, *fit* attack/defense by regressing historical goals on
  opponent strength + venue. Produces estimated parameters **with confidence
  intervals** (feeds §4 uncertainty).
- **Squad-availability adjustments** — ⭐⭐ / 🔨🔨
  Aggregate the called-up squad's market values / minutes (Transfermarkt) and
  nudge ratings for injuries and absences just before kickoff.
- **Confederation strength priors** — ⭐⭐ / 🔨🔨
  AFC/CONCACAF/OFC sides are systematically mis-rated vs UEFA/CONMEBOL.
  Calibrate a per-confederation correction from inter-confederation history.
- **Market-anchored ratings (Bayesian shrinkage)** — ⭐⭐ / 🔨🔨
  Blend the model with the de-vigged betting market (markets are hard to beat).
  Shrink team strengths toward market-implied values by a tunable weight.

## 2. Match-model sophistication
- **Dixon-Coles low-score correction** — ⭐⭐⭐ / 🔨
  Independent Poisson *understates* 0-0, 1-0 and 1-1 — the scorelines that decide
  tournaments. Cheap, standard, materially more accurate. Best bang-for-buck
  modelling change.
- **Bivariate / correlated goals** — ⭐⭐ / 🔨🔨
  Model the correlation between the two teams' goals rather than assuming
  independence.
- **Penalty-shootout model** — ⭐⭐ / 🔨
  ~25% of knockout games are drawn after 90'. Replace the Elo coin-flip with a
  shootout model using teams' historical shootout records.
- **Travel / rest / altitude / heat** — ⭐ / 🔨🔨
  Mexico City altitude, summer heat, and rest-day asymmetry between groups are
  small but real edges in a host-spanning tournament.
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
- **Backtest & calibrate on 2018 & 2022** — ⭐⭐⭐ / 🔨🔨
  Score the model with log-loss / Brier against past tournaments and *fit* the
  constants (goal scale, home edge, style weights). Turns guesses into
  calibrated parameters and tells us whether we're actually any good.
- **Reliability / calibration plots** — ⭐⭐ / 🔨
  Do events we call "30%" happen ~30% of the time?
- **Monte Carlo error bars** — ⭐ / 🔨
  Report binomial ± on every probability so readers know the sampling noise.

## 5. The Tippspiel angle — possibly the actual point
A prediction *pool* rewards **points under its scoring rules**, which is **not**
the same as picking the most likely outcome — if everyone picks the favorite,
the EV-maximizing play can be a contrarian champion.

- **Point-maximizing picks under your pool's rules** — ⭐⭐⭐ / 🔨🔨
  Given the scoring system (exact score vs. tendency, knockout bonuses, etc.),
  compute the bracket / score picks that **maximize expected points**, optionally
  accounting for what the rest of the pool is likely to pick.
- **Exact-score predictions per fixture** — ⭐⭐ / 🔨
  Most likely scoreline for each of the 104 matches.
- **Risk profiles** — ⭐ / 🔨🔨
  "Safe" (maximize expected points) vs. "aggressive" (maximize chance of *winning*
  the pool) pick sets.

## 6. Product & engineering
- **Live re-simulation during the tournament** — ⭐⭐⭐ / 🔨🔨
  Feed in actual results as they happen and re-simulate the remainder. (Pairs
  with an FIFA standings / results ingestion step.)
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
