# 2026 FIFA World Cup — Statistical Predictions

*Generated 2026-07-04 from 20,000 Monte Carlo simulations (seed `2026`).*

> 🟢 **Live view** — conditioned on **85 played matches** (`data/results.csv`). Ratings re-tuned via Elo update; played fixtures use their real scoreline.

> Hosts: United States · Canada · Mexico. 48 teams, 12 groups of 4. Top 2 of each group plus the 8 best third-placed teams reach the Round of 32.

## 🏆 Title probability (all 48 teams)

*Champion column shows the 95% Monte Carlo CI (`p ± 1.96 · √(p(1−p)/20,000)`); other columns omit it for readability.*

| # | Team | Champion | Final | Semi | Quarter | R16 |
|--:|------|---------:|------:|-----:|--------:|----:|
| 1 | Argentina | 23% ±0.6 | 36% | 56% | 81% | 96% |
| 2 | France | 17% ±0.5 | 30% | 50% | 67% | 87% |
| 3 | Spain | 14% ±0.5 | 27% | 44% | 61% | 100% |
| 4 | England | 9.7% ±0.4 | 18% | 36% | 57% | 100% |
| 5 | Brazil | 6.6% ±0.3 | 14% | 32% | 71% | 100% |
| 6 | Portugal | 5.5% ±0.3 | 12% | 24% | 39% | 100% |
| 7 | Mexico | 5.3% ±0.3 | 11% | 24% | 41% | 87% |
| 8 | Colombia | 4.6% ±0.3 | 10.0% | 20% | 47% | 83% |
| 9 | Switzerland | 2.6% ±0.2 | 6.5% | 15% | 43% | 85% |
| 10 | Morocco | 2.2% ±0.2 | 6.5% | 18% | 50% | 100% |
| 11 | Belgium | 2.1% ±0.2 | 6.0% | 14% | 42% | 77% |
| 12 | Canada | 2.0% ±0.2 | 6.1% | 17% | 50% | 100% |
| 13 | United States | 1.8% ±0.2 | 5.3% | 14% | 44% | 88% |
| 14 | Germany | 1.3% ±0.2 | 3.6% | 9.5% | 18% | 51% |
| 15 | Australia | 0.56% ±0.1 | 1.8% | 5.3% | 14% | 65% |
| 16 | Norway | 0.48% | 1.8% | 7.5% | 29% | 100% |
| 17 | Paraguay | 0.42% | 1.4% | 4.9% | 12% | 46% |
| 18 | Ecuador | 0.41% | 1.3% | 3.7% | 12% | 26% |
| 19 | Senegal | 0.11% | 0.46% | 1.5% | 5.9% | 20% |
| 20 | Sweden | 0.03% | 0.08% | 0.53% | 2.4% | 14% |
| 21 | Egypt | 0.03% | 0.22% | 1.1% | 4.3% | 35% |
| 22 | Algeria | 0.03% | 0.17% | 0.66% | 3.7% | 12% |
| 23 | Bosnia & Herzegovina | 0.01% | 0.09% | 0.51% | 1.5% | 8.6% |
| 24 | Ghana | 0.01% | 0.12% | 0.60% | 4.3% | 17% |
| 25 | South Korea | — | — | — | — | — |
| 26 | Czechia | — | — | — | — | — |
| 27 | South Africa | — | — | — | — | — |
| 28 | Qatar | — | — | — | — | — |
| 29 | Scotland | — | — | — | — | — |
| 30 | Haiti | — | — | — | — | — |
| 31 | Türkiye | — | — | — | — | — |
| 32 | Ivory Coast | — | — | — | — | — |
| 33 | Curaçao | — | — | — | — | — |
| 34 | Netherlands | — | — | — | — | — |
| 35 | Japan | — | — | — | — | — |
| 36 | Tunisia | — | — | — | — | — |
| 37 | IR Iran | — | — | — | — | — |
| 38 | New Zealand | — | — | — | — | — |
| 39 | Uruguay | — | — | — | — | — |
| 40 | Cabo Verde | — | 0.03% | 0.17% | 1.1% | 4.3% |
| 41 | Saudi Arabia | — | — | — | — | — |
| 42 | Iraq | — | — | — | — | — |
| 43 | Austria | — | — | — | — | — |
| 44 | Jordan | — | — | — | — | — |
| 45 | Uzbekistan | — | — | — | — | — |
| 46 | DR Congo | — | — | — | — | — |
| 47 | Croatia | — | — | — | — | — |
| 48 | Panama | — | — | — | — | — |

## 🎯 Headline calls

- **Most likely champion:** Argentina (23%, ±0.6% Monte Carlo 95% CI)
- **Most likely final pairing:** Argentina vs France (11% of simulations)
- **Top contenders:** Argentina 23%, France 17%, Spain 14%, England 9.7%

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
| Mexico | 1919 | 1.96 | 1.22 | 100% | 100% |
| South Africa | 1692 | 1.30 | 1.95 | — | 100% |
| South Korea | 1738 | 1.69 | 1.73 | — | — |
| Czechia | 1698 | 1.39 | 1.85 | — | — |

*Most likely qualifiers: Mexico (1st) & South Africa (2nd) — 100%.*

**Group B**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Switzerland | 1934 | 1.95 | 1.07 | 100% | 100% |
| Canada | 1800 | 1.69 | 1.61 | — | 100% |
| Bosnia & Herzegovina | 1716 | 1.48 | 1.81 | — | 100% |
| Qatar | 1640 | 1.37 | 2.19 | — | — |

*Most likely qualifiers: Switzerland (1st) & Canada (2nd) — 100%.*

**Group C**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Brazil | 1943 | 2.46 | 1.17 | 100% | 100% |
| Morocco | 1898 | 1.76 | 1.20 | — | 100% |
| Scotland | 1736 | 1.45 | 1.77 | — | — |
| Haiti | 1604 | 1.12 | 2.33 | — | — |

*Most likely qualifiers: Brazil (1st) & Morocco (2nd) — 100%.*

**Group D**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Paraguay | 1785 | 1.39 | 1.33 | — | 100% |
| Australia | 1767 | 1.74 | 1.42 | — | 100% |
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
| Egypt | 1733 | 1.34 | 1.75 | — | 100% |
| IR Iran | 1765 | 1.62 | 1.46 | — | — |
| New Zealand | 1567 | 1.08 | 2.26 | — | — |

*Most likely qualifiers: Belgium (1st) & Egypt (2nd) — 100%.*

**Group H**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Spain | 2060 | 2.88 | 0.96 | 100% | 100% |
| Cabo Verde | 1608 | 1.05 | 2.22 | — | 100% |
| Uruguay | 1816 | 1.53 | 1.27 | — | — |
| Saudi Arabia | 1589 | 1.14 | 1.92 | — | — |

*Most likely qualifiers: Spain (1st) & Cabo Verde (2nd) — 100%.*

**Group I**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| France | 2090 | 2.91 | 0.92 | 100% | 100% |
| Senegal | 1824 | 1.67 | 1.53 | — | 100% |
| Norway | 1801 | 2.02 | 1.69 | — | 100% |
| Iraq | 1568 | 1.12 | 2.05 | — | — |

*Most likely qualifiers: France (1st) & Norway (2nd) — 100%.*

**Group J**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Argentina | 2090 | 3.08 | 0.91 | 100% | 100% |
| Austria | 1799 | 1.82 | 1.50 | — | 100% |
| Algeria | 1758 | 1.54 | 1.83 | — | 100% |
| Jordan | 1646 | 1.33 | 1.78 | — | — |

*Most likely qualifiers: Argentina (1st) & Austria (2nd) — 100%.*

**Group K**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Portugal | 2001 | 2.66 | 1.25 | — | 100% |
| Colombia | 1979 | 2.43 | 1.13 | 100% | 100% |
| DR Congo | 1712 | 1.42 | 1.95 | — | 100% |
| Uzbekistan | 1663 | 1.27 | 1.75 | — | — |

*Most likely qualifiers: Colombia (1st) & Portugal (2nd) — 100%.*

**Group L**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| England | 2014 | 2.53 | 0.95 | 100% | 100% |
| Croatia | 1891 | 1.95 | 1.26 | — | 100% |
| Ghana | 1686 | 1.49 | 1.99 | — | 100% |
| Panama | 1691 | 1.25 | 1.85 | — | — |

*Most likely qualifiers: England (1st) & Croatia (2nd) — 100%.*

## 💰 Model vs. betting market

Model champion probability vs. the **de-vigged** market probability (`(1 / decimal odds)` normalised across the listed teams to strip out the bookmaker margin of ~21%). A sanity check, and a way to spot where the model disagrees with the market.

> Polymarket (real-money) has **France 17.0%** ahead of **Spain 16.1%** — bookmakers still have Spain a fraction shorter. The two sharpest market views disagree on the favourite.

| Team | Model | Market (de-vig) | Polymarket | Decimal odds | Lean |
|------|------:|----------------:|-----------:|-------------:|:-----|
| Spain | 14% | 15% | 16.1% | 5.5 | ≈ agree |
| France | 17% | 14% | 17.0% | 5.75 | model higher |
| England | 9.7% | 11% | 11.1% | 7.5 | ≈ agree |
| Brazil | 6.6% | 9.2% | 8.4% | 9 | market higher |
| Argentina | 23% | 9.2% | 9.0% | 9 | model higher |
| Portugal | 5.5% | 6.9% | 9.5% | 12 | market higher |
| Germany | 1.3% | 5.5% | 5.6% | 15 | market higher |
| Netherlands | — | 3.7% | 3.9% | 22 | market higher |
| Norway | 0.48% | 2.8% | — | 29 | market higher |
| Belgium | 2.1% | 2.4% | 1.9% | 34 | ≈ agree |
| Colombia | 4.6% | 2.3% | 0.7% | 36 | model higher |
| Morocco | 2.2% | 1.6% | — | 51 | model higher |
| Japan | — | 1.6% | — | 52 | market higher |
| United States | 1.8% | 1.3% | — | 63 | model higher |
| Uruguay | — | 1.3% | — | 65 | market higher |
| Switzerland | 2.6% | 1.2% | — | 66 | model higher |
| Türkiye | — | 1.2% | — | 67 | market higher |
| Croatia | — | 1.2% | — | 67 | market higher |
| Mexico | 5.3% | 1.0% | — | 81 | model higher |
| Senegal | 0.11% | 1.0% | — | 81 | market higher |
| Ecuador | 0.41% | 0.82% | — | 101 | market higher |
| Austria | — | 0.82% | — | 101 | market higher |
| Scotland | — | 0.55% | — | 151 | market higher |
| Sweden | 0.03% | 0.55% | — | 151 | market higher |
| Egypt | 0.03% | 0.55% | — | 151 | market higher |
| Algeria | 0.03% | 0.55% | — | 151 | market higher |
| Ghana | 0.01% | 0.55% | — | 151 | market higher |
| Australia | 0.56% | 0.41% | — | 201 | model higher |
| Ivory Coast | — | 0.41% | — | 201 | market higher |
| South Korea | — | 0.33% | — | 251 | market higher |
| Canada | 2.0% | 0.33% | — | 251 | model higher |
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
