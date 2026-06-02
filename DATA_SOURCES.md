# Where to get better input data

The model is only as good as `data/teams.csv`. Every row needs five inputs:
`elo`, `attack`, `defense`, and (optionally) `market_decimal_odds`. This file
lists where to pull high-fidelity numbers for each, so you can replace the
hand-assembled snapshot whenever you have better data.

> **How to apply new data:** either edit `data/teams.csv` directly, or update
> the `elo` / `style` values in `data/derive_ratings.py` and run
> `python -m data.derive_ratings` to regenerate attack/defense from them.

## 1. Overall strength → `elo`

| Source | URL | Notes |
|--------|-----|-------|
| World Football Elo Ratings | https://www.eloratings.net/ | The canonical Elo. Top team ~2100. Has per-match history and a "fixtures" forecast. **This is the scale the model is calibrated to.** |
| World Football Rankings (Elo) | https://worldfootballrankings.com/rankings | Clean table, daily updates. Uses a compressed scale (top ~1880) — rescale if you use it as the primary source. |
| FIFA / Coca-Cola World Ranking | https://inside.fifa.com/fifa-world-ranking/men | Official, but a points system rather than true Elo; better as a cross-check. |

## 2. Attack & defense → `attack`, `defense`

This is the data you specifically wanted: how good a team is going forward vs.
at the back. Best signals, in rough order of fidelity:

| Source | URL | What you get |
|--------|-----|--------------|
| FBref (StatsBomb) | https://fbref.com/en/comps/1/World-Cup-Stats and national-team pages | **Best free option.** Per-team **xG for / xG against** over recent matches — exactly attack/defense. Filter to last 1–2 years of internationals. |
| Understat | https://understat.com/ | xG/xGA (club-focused, but useful for player form). |
| FotMob | https://www.fotmob.com/leagues/10195/stats/world-cup-qualification-uefa (and other confederations) | Goals for/against, clean sheets, xG per qualifying campaign, by team. |
| Footystats | https://footystats.org/international/wc-qualification-europe/goals-conceded-table | Goals scored/conceded tables per qualifying group. |
| Opta / TheAnalyst | https://theanalyst.com/ | Their own World Cup supercomputer + team ratings (editorial, not raw export). |

**Turning xG into ratings:** for each team compute average **xG scored per
match** and **xG conceded per match** against comparable opposition, then divide
by the field average (~1.35) — that gives `attack` and `defense` directly in the
units the model expects. If you only have goals (not xG), use goals for/against
per match instead; xG is less noisy but goals work fine.

## 3. Market consensus → `market_decimal_odds`

Used only for the model-vs-market comparison table (not as a model input,
unless you choose to anchor to it).

| Source | URL |
|--------|-----|
| n-tv odds comparison (DE) | https://www.n-tv.de/wettanbieter-vergleich/quoten/wm-2026/ |
| Oddschecker / OddsPortal | aggregate decimal odds across many books |
| Pinnacle | sharpest single book; lowest margin, closest to "true" probability |
| Prediction markets | Polymarket / Kalshi — already de-vigged, real-money probabilities |

Enter the **decimal** odds (e.g. `5.5`), not fractional/American. Leave blank if
unknown.

## 4. Squad / availability adjustments (manual)

No public feed captures injuries and call-ups cleanly. Just before the
tournament, nudge a team's `elo` (or `attack`/`defense`) down for a major
absence (e.g. a key striker out → lower `attack`). Recent squad lists:
- ESPN squad tracker: https://www.espn.com/soccer/story/_/id/48757621
- Olympics.com squads: https://www.olympics.com/en/news/2026-fifa-world-cup-football-teams-squads-players-complete-list

---

### Current snapshot provenance (June 2026)

The shipped `data/teams.csv` was assembled from: the confirmed final draw and
the March-2026 European playoff winners (Bosnia & Herzegovina, Sweden, Türkiye,
Czechia); the Elo ordering from eloratings.net / worldfootballrankings.com; the
betting market (Spain ≈ 5.5, France ≈ 5.75, England ≈ 7.5, Brazil/Argentina
≈ 8.5–9, Portugal ≈ 12, Germany ≈ 15); and per-team offensive/defensive style
tilts informed by playing identity and qualifying goal records. It is a
reasonable baseline, **not** a live data feed — replace it for higher fidelity.
