# 2026 FIFA World Cup — Statistical Predictions

*Generated 2026-07-06 from 20,000 Monte Carlo simulations (seed `2026`).*

> 🟢 **Live view** — conditioned on **92 played matches** (`data/results.csv`). Ratings re-tuned via Elo update; played fixtures use their real scoreline.

> Hosts: United States · Canada · Mexico. 48 teams, 12 groups of 4. Top 2 of each group plus the 8 best third-placed teams reach the Round of 32.

## 🏆 Title probability (all 48 teams)

*Champion column shows the 95% Monte Carlo CI (`p ± 1.96 · √(p(1−p)/20,000)`); other columns omit it for readability.*

| # | Team | Champion | Final | Semi | Quarter | R16 |
|--:|------|---------:|------:|-----:|--------:|----:|
| 1 | Argentina | 24% ±0.6 | 39% | 61% | 90% | 100% |
| 2 | England | 20% ±0.6 | 36% | 73% | 97% | 100% |
| 3 | France | 18% ±0.5 | 33% | 53% | 75% | 87% |
| 4 | Spain | 13% ±0.5 | 26% | 45% | 62% | 100% |
| 5 | Colombia | 5.4% ±0.3 | 12% | 23% | 58% | 100% |
| 6 | Portugal | 4.9% ±0.3 | 12% | 24% | 38% | 100% |
| 7 | Morocco | 4.6% ±0.3 | 14% | 35% | 100% | 100% |
| 8 | Switzerland | 2.2% ±0.2 | 5.3% | 12% | 37% | 85% |
| 9 | Norway | 2.1% ±0.2 | 6.6% | 26% | 100% | 100% |
| 10 | Belgium | 1.9% ±0.2 | 5.7% | 14% | 43% | 77% |
| 11 | United States | 1.5% ±0.2 | 4.9% | 13% | 42% | 87% |
| 12 | Germany | 1.1% ±0.1 | 3.3% | 8.7% | 17% | 51% |
| 13 | Ecuador | 0.45% | 1.3% | 3.5% | 11% | 26% |
| 14 | Paraguay | 0.12% | 0.51% | 2.0% | 5.2% | 46% |
| 15 | Senegal | 0.11% | 0.41% | 1.7% | 5.5% | 20% |
| 16 | Egypt | 0.07% | 0.44% | 2.4% | 9.5% | 100% |
| 17 | Algeria | 0.03% | 0.15% | 0.65% | 4.0% | 12% |
| 18 | Sweden | 0.03% | 0.10% | 0.56% | 2.1% | 14% |
| 19 | Bosnia & Herzegovina | 0.01% | 0.10% | 0.50% | 1.6% | 9.0% |
| 20 | Mexico | — | — | — | — | 86% |
| 21 | South Korea | — | — | — | — | — |
| 22 | Czechia | — | — | — | — | — |
| 23 | South Africa | — | — | — | — | — |
| 24 | Canada | — | — | — | — | 100% |
| 25 | Qatar | — | — | — | — | — |
| 26 | Brazil | — | — | — | — | 100% |
| 27 | Scotland | — | — | — | — | — |
| 28 | Haiti | — | — | — | — | — |
| 29 | Türkiye | — | — | — | — | — |
| 30 | Australia | — | — | — | — | — |
| 31 | Ivory Coast | — | — | — | — | — |
| 32 | Curaçao | — | — | — | — | — |
| 33 | Netherlands | — | — | — | — | — |
| 34 | Japan | — | — | — | — | — |
| 35 | Tunisia | — | — | — | — | — |
| 36 | IR Iran | — | — | — | — | — |
| 37 | New Zealand | — | — | — | — | — |
| 38 | Uruguay | — | — | — | — | — |
| 39 | Cabo Verde | — | — | — | — | — |
| 40 | Saudi Arabia | — | — | — | — | — |
| 41 | Iraq | — | — | — | — | — |
| 42 | Austria | — | — | — | — | — |
| 43 | Jordan | — | — | — | — | — |
| 44 | Uzbekistan | — | — | — | — | — |
| 45 | DR Congo | — | — | — | — | — |
| 46 | Croatia | — | — | — | — | — |
| 47 | Ghana | — | — | — | — | — |
| 48 | Panama | — | — | — | — | — |

## 🎯 Headline calls

- **Most likely champion:** Argentina (24%, ±0.6% Monte Carlo 95% CI)
- **Most likely final pairing:** Argentina vs France (13% of simulations)
- **Top contenders:** Argentina 24%, England 20%, France 18%, Spain 13%

## 🩹 Injuries & availability

Current absences nudge the affected teams' attack/defense ratings (see `data/injuries.csv`; run with `--no-injuries` for full strength). A forward out dents **attack**; a defender or keeper out worsens **defense**.

| Team | Att | Def | Out / doubtful |
|------|----:|----:|:---------------|
| Brazil | -13% | +6% | Rodrygo, Estêvão, Éder Militão, Neymar (questionable) |
| Ghana | -6% | +11% | Mohammed Kudus, Mohammed Salisu, Alexander Djiku |
| Netherlands | -6% | +8% | Xavi Simons, Matthijs de Ligt, Jerdy Schouten |
| Germany | -4% | +9% | Marc-André ter Stegen, Serge Gnabry |
| Japan | -9% | +3% | Kaoru Mitoma, Takumi Minamino |
| United States | -6% | +3% | Patrick Agyemang, Johnny Cardoso |
| Spain | -6% | +3% | Fermín López, Lamine Yamal (doubtful) |
| Argentina | -1% | +6% | Juan Foyth, Emiliano Martínez (questionable) |
| France | -3% | +4% | William Saliba (doubtful), Hugo Ekitike |
| England | -2% | +4% | Ben White, Jarrad Branthwaite, Jack Grealish |
| Canada | -2% | +4% | Alphonso Davies (doubtful), Marcelo Flores |
| Scotland | -2% | +2% | Billy Gilmour |
| Austria | -2% | +2% | Christoph Baumgartner |
| Bosnia & Herzegovina | -4% | +1% | Haris Tabakovic |
| Mexico | +0% | +5% | Luis Ángel Malagón |
| Australia | -0% | +2% | Lewis Miller |

*Att/Def columns show the percentage change to each rating (defense `+` = more goals conceded). Doubtful/questionable players count at a reduced weight.*

## ✈️ Group-stage travel & altitude burden

Total km flown between consecutive venues and total altitude exposure (sum of metres above 1500 m across the three group matches; 0 for teams from highland nations). Both feed into a small attack/defense penalty in the match where they apply.

| Team | km | Altitude m·matches | Notes |
|------|---:|-------------------:|:------|
| Czechia | 4544 | 807 | coast-to-coast group |
| South Africa | 3943 | 740 | — |
| Bosnia & Herzegovina | 5058 | 0 | coast-to-coast group |
| Algeria | 4797 | 0 | coast-to-coast group |
| Colombia | 4654 | 0 | altitude-acclimated, coast-to-coast group |
| DR Congo | 3660 | 67 | — |
| Ecuador | 3405 | 0 | altitude-acclimated |
| Canada | 3357 | 0 | — |
| Belgium | 3302 | 0 | — |
| United States | 3106 | 0 | — |
| Austria | 3054 | 0 | — |
| Uruguay | 2439 | 67 | — |

## 📊 Group stage

Probability each team **wins its group** / **advances** (top 2, before best-third places are counted).

**Group A**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Mexico | 1904 | 1.91 | 1.25 | 100% | 100% |
| South Africa | 1692 | 1.30 | 1.95 | — | 100% |
| South Korea | 1738 | 1.69 | 1.73 | — | — |
| Czechia | 1698 | 1.39 | 1.85 | — | — |

*Most likely qualifiers: Mexico (1st) & South Africa (2nd) — 100%.*

**Group B**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Switzerland | 1934 | 1.95 | 1.07 | 100% | 100% |
| Canada | 1774 | 1.61 | 1.70 | — | 100% |
| Bosnia & Herzegovina | 1716 | 1.48 | 1.81 | — | 100% |
| Qatar | 1640 | 1.37 | 2.19 | — | — |

*Most likely qualifiers: Switzerland (1st) & Canada (2nd) — 100%.*

**Group C**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Brazil | 1915 | 2.32 | 1.24 | 100% | 100% |
| Morocco | 1923 | 1.85 | 1.14 | — | 100% |
| Scotland | 1736 | 1.45 | 1.77 | — | — |
| Haiti | 1604 | 1.12 | 2.33 | — | — |

*Most likely qualifiers: Brazil (1st) & Morocco (2nd) — 100%.*

**Group D**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Paraguay | 1779 | 1.37 | 1.34 | — | 100% |
| Australia | 1765 | 1.74 | 1.42 | — | 100% |
| United States | 1798 | 1.66 | 1.56 | 100% | 100% |
| Türkiye | 1834 | 1.93 | 1.75 | — | — |

*Most likely qualifiers: United States (1st) & Australia (2nd) — 100%.*

**Group E**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Germany | 1865 | 2.30 | 1.45 | 100% | 100% |
| Ecuador | 1857 | 1.53 | 1.12 | — | 100% |
| Ivory Coast | 1722 | 1.44 | 1.94 | — | 100% |
| Curaçao | 1587 | 1.04 | 2.21 | — | — |

*Most likely qualifiers: Germany (1st) & Ivory Coast (2nd) — 100%.*

**Group F**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Netherlands | 1920 | 2.43 | 1.27 | 100% | 100% |
| Japan | 1826 | 2.09 | 1.34 | — | 100% |
| Sweden | 1724 | 1.36 | 1.89 | — | 100% |
| Tunisia | 1586 | 0.90 | 2.12 | — | — |

*Most likely qualifiers: Netherlands (1st) & Japan (2nd) — 100%.*

**Group G**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Belgium | 1903 | 2.28 | 1.37 | 100% | 100% |
| Egypt | 1735 | 1.35 | 1.74 | — | 100% |
| IR Iran | 1765 | 1.62 | 1.46 | — | — |
| New Zealand | 1567 | 1.08 | 2.26 | — | — |

*Most likely qualifiers: Belgium (1st) & Egypt (2nd) — 100%.*

**Group H**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Spain | 2060 | 2.88 | 0.96 | 100% | 100% |
| Cabo Verde | 1606 | 1.05 | 2.23 | — | 100% |
| Uruguay | 1816 | 1.53 | 1.27 | — | — |
| Saudi Arabia | 1589 | 1.14 | 1.92 | — | — |

*Most likely qualifiers: Spain (1st) & Cabo Verde (2nd) — 100%.*

**Group I**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| France | 2096 | 2.95 | 0.91 | 100% | 100% |
| Senegal | 1824 | 1.67 | 1.53 | — | 100% |
| Norway | 1829 | 2.14 | 1.59 | — | 100% |
| Iraq | 1568 | 1.12 | 2.05 | — | — |

*Most likely qualifiers: France (1st) & Norway (2nd) — 100%.*

**Group J**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Argentina | 2093 | 3.09 | 0.90 | 100% | 100% |
| Austria | 1799 | 1.82 | 1.50 | — | 100% |
| Algeria | 1758 | 1.54 | 1.83 | — | 100% |
| Jordan | 1646 | 1.33 | 1.78 | — | — |

*Most likely qualifiers: Argentina (1st) & Austria (2nd) — 100%.*

**Group K**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Portugal | 2001 | 2.66 | 1.25 | — | 100% |
| Colombia | 1985 | 2.46 | 1.11 | 100% | 100% |
| DR Congo | 1712 | 1.42 | 1.95 | — | 100% |
| Uzbekistan | 1663 | 1.27 | 1.75 | — | — |

*Most likely qualifiers: Colombia (1st) & Portugal (2nd) — 100%.*

**Group L**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| England | 2028 | 2.60 | 0.92 | 100% | 100% |
| Croatia | 1891 | 1.95 | 1.26 | — | 100% |
| Ghana | 1680 | 1.47 | 2.02 | — | 100% |
| Panama | 1691 | 1.25 | 1.85 | — | — |

*Most likely qualifiers: England (1st) & Croatia (2nd) — 100%.*

## 💰 Model vs. betting market

Model champion probability vs. the **de-vigged** market probability (`(1 / decimal odds)` normalised across the listed teams to strip out the bookmaker margin of ~21%). A sanity check, and a way to spot where the model disagrees with the market.

> Polymarket (real-money) has **France 17.0%** ahead of **Spain 16.1%** — bookmakers still have Spain a fraction shorter. The two sharpest market views disagree on the favourite.

| Team | Model | Market (de-vig) | Polymarket | Decimal odds | Lean |
|------|------:|----------------:|-----------:|-------------:|:-----|
| Spain | 13% | 15% | 16.1% | 5.5 | ≈ agree |
| France | 18% | 14% | 17.0% | 5.75 | model higher |
| England | 20% | 11% | 11.1% | 7.5 | model higher |
| Brazil | — | 9.2% | 8.4% | 9 | market higher |
| Argentina | 24% | 9.2% | 9.0% | 9 | model higher |
| Portugal | 4.9% | 6.9% | 9.5% | 12 | market higher |
| Germany | 1.1% | 5.5% | 5.6% | 15 | market higher |
| Netherlands | — | 3.7% | 3.9% | 22 | market higher |
| Norway | 2.1% | 2.8% | — | 29 | market higher |
| Belgium | 1.9% | 2.4% | 1.9% | 34 | market higher |
| Colombia | 5.4% | 2.3% | 0.7% | 36 | model higher |
| Morocco | 4.6% | 1.6% | — | 51 | model higher |
| Japan | — | 1.6% | — | 52 | market higher |
| United States | 1.5% | 1.3% | — | 63 | ≈ agree |
| Uruguay | — | 1.3% | — | 65 | market higher |
| Switzerland | 2.2% | 1.2% | — | 66 | model higher |
| Türkiye | — | 1.2% | — | 67 | market higher |
| Croatia | — | 1.2% | — | 67 | market higher |
| Mexico | — | 1.0% | — | 81 | market higher |
| Senegal | 0.11% | 1.0% | — | 81 | market higher |
| Ecuador | 0.45% | 0.82% | — | 101 | market higher |
| Austria | — | 0.82% | — | 101 | market higher |
| Scotland | — | 0.55% | — | 151 | market higher |
| Sweden | 0.03% | 0.55% | — | 151 | market higher |
| Egypt | 0.07% | 0.55% | — | 151 | market higher |
| Algeria | 0.03% | 0.55% | — | 151 | market higher |
| Ghana | — | 0.55% | — | 151 | market higher |
| Australia | — | 0.41% | — | 201 | market higher |
| Ivory Coast | — | 0.41% | — | 201 | market higher |
| South Korea | — | 0.33% | — | 251 | market higher |
| Canada | — | 0.33% | — | 251 | market higher |
| IR Iran | — | 0.33% | — | 251 | market higher |

## 🔬 Methodology

- **Engine:** Monte Carlo. The full tournament (72 group matches + 31 knockout matches) is simulated 20,000 times; every probability is the share of simulations in which the event happened.
- **Match model:** each team has an **attack** rating (expected goals scored vs an average team) and a **defense** rating (expected goals conceded). A match's expected goals combine as `λ_A = attack_A · defense_B / LG_AVG`, then scorelines are drawn from Poisson distributions with a **Dixon-Coles** low-score correction (ρ = -0.0885) that lifts 0-0/1-0/1-1 outcomes to match real football. Hosts get a small home edge; drawn knockout games are settled by an Elo-weighted shootout.
- **Rating uncertainty:** each team's *true* tournament strength is resampled every simulation from a Gaussian (σ = 45 Elo) around its rating, capturing both rating error and tournament-level form. Without this a point-estimate model is over-confident in the favourites; resampling fattens the upset tail toward reality.
- **Sampling error:** probabilities carry Monte Carlo noise of ≈ √(p(1−p)/N); the favourite's 95% interval is shown above. More `--sims` tightens it.
- **Ratings:** derived from a June-2026 Elo strength snapshot plus a per-team offensive/defensive style tilt (see `data/derive_ratings.py`), then adjusted for current injuries/absences (`data/injuries.csv`, see the Injuries section above; `--no-injuries` disables it).
- **Tie-breakers:** group tables rank by points, goal difference, then goals for; remaining ties (and head-to-head / fair-play / drawing of lots) are approximated by a random nudge.

### Caveats

- Ratings are a hand-assembled snapshot, not a live feed — replace `data/teams.csv` with better numbers to improve fidelity (see `DATA_SOURCES.md`).
- The knockout bracket is the **official** FIFA bracket (match numbers, third-place cluster codes and tree), encoded in `data/bracket.py`. Which third-placed team fills each slot depends on the qualifying groups; it is resolved by a constraint-respecting matching.
- Known injuries are folded in via `data/injuries.csv`, but the model still can't capture in-tournament momentum, red cards or a hot goalkeeper. Treat these as probabilities, not prophecies.
