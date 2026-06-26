# 2026 FIFA World Cup — Statistical Predictions

*Generated 2026-06-26 from 20,000 Monte Carlo simulations (seed `2026`).*

> 🟢 **Live view** — conditioned on **60 played matches** (`data/results.csv`). Ratings re-tuned via Elo update; played fixtures use their real scoreline.

> Hosts: United States · Canada · Mexico. 48 teams, 12 groups of 4. Top 2 of each group plus the 8 best third-placed teams reach the Round of 32.

## 🏆 Title probability (all 48 teams)

*Champion column shows the 95% Monte Carlo CI (`p ± 1.96 · √(p(1−p)/20,000)`); other columns omit it for readability.*

| # | Team | Champion | Final | Semi | Quarter | R16 |
|--:|------|---------:|------:|-----:|--------:|----:|
| 1 | Argentina | 23% ±0.6 | 35% | 51% | 72% | 89% |
| 2 | France | 15% ±0.5 | 26% | 40% | 58% | 81% |
| 3 | Spain | 11% ±0.4 | 21% | 34% | 46% | 71% |
| 4 | England | 7.9% ±0.4 | 14% | 28% | 43% | 73% |
| 5 | Colombia | 5.7% ±0.3 | 11% | 21% | 42% | 71% |
| 6 | Portugal | 4.8% ±0.3 | 10% | 20% | 35% | 66% |
| 7 | Mexico | 4.6% ±0.3 | 9.2% | 22% | 37% | 71% |
| 8 | Brazil | 4.0% ±0.3 | 8.1% | 19% | 39% | 56% |
| 9 | Netherlands | 3.5% ±0.3 | 8.6% | 17% | 37% | 55% |
| 10 | Germany | 2.8% ±0.2 | 7.1% | 15% | 29% | 71% |
| 11 | Switzerland | 2.4% ±0.2 | 5.5% | 12% | 32% | 68% |
| 12 | Japan | 1.8% ±0.2 | 4.6% | 12% | 28% | 44% |
| 13 | Croatia | 1.7% ±0.2 | 4.1% | 9.4% | 19% | 41% |
| 14 | Ecuador | 1.6% ±0.2 | 4.1% | 10% | 23% | 46% |
| 15 | Canada | 1.6% ±0.2 | 5.1% | 12% | 31% | 71% |
| 16 | United States | 1.5% ±0.2 | 4.5% | 12% | 34% | 61% |
| 17 | Morocco | 1.5% ±0.2 | 4.5% | 10% | 26% | 45% |
| 18 | Belgium | 1.4% ±0.2 | 3.6% | 8.4% | 20% | 51% |
| 19 | Austria | 0.71% ±0.1 | 2.0% | 5.7% | 11% | 28% |
| 20 | Norway | 0.69% ±0.1 | 2.1% | 7.4% | 22% | 63% |
| 21 | Australia | 0.61% ±0.1 | 1.8% | 4.7% | 12% | 53% |
| 22 | Paraguay | 0.41% | 1.4% | 3.9% | 10.0% | 26% |
| 23 | Uruguay | 0.39% | 1.1% | 2.9% | 6.3% | 15% |
| 24 | IR Iran | 0.34% | 1.1% | 3.5% | 12% | 33% |
| 25 | South Korea | 0.21% | 0.89% | 3.0% | 12% | 30% |
| 26 | Bosnia & Herzegovina | 0.19% | 0.93% | 3.6% | 14% | 35% |
| 27 | Senegal | 0.16% | 0.60% | 2.0% | 6.1% | 15% |
| 28 | Algeria | 0.10% | 0.40% | 1.4% | 4.6% | 15% |
| 29 | Ivory Coast | 0.09% | 0.37% | 2.0% | 8.4% | 34% |
| 30 | Egypt | 0.09% | 0.50% | 2.0% | 9.4% | 33% |
| 31 | South Africa | 0.07% | 0.33% | 1.4% | 6.5% | 29% |
| 32 | Ghana | 0.07% | 0.27% | 1.2% | 5.5% | 20% |
| 33 | Sweden | 0.04% | 0.24% | 1.2% | 5.2% | 22% |
| 34 | Scotland | 0.02% | 0.04% | 0.18% | 0.68% | 2.5% |
| 35 | DR Congo | 0.02% | 0.05% | 0.27% | 1.1% | 4.9% |
| 36 | Saudi Arabia | 0.01% | 0.07% | 0.27% | 1.2% | 4.2% |
| 37 | Czechia | — | — | — | — | — |
| 38 | Qatar | — | — | — | — | — |
| 39 | Haiti | — | — | — | — | — |
| 40 | Türkiye | — | — | — | — | — |
| 41 | Curaçao | — | — | — | — | — |
| 42 | Tunisia | — | — | — | — | — |
| 43 | New Zealand | — | 0.01% | 0.05% | 0.23% | 2.4% |
| 44 | Cabo Verde | — | — | 0.08% | 0.74% | 3.7% |
| 45 | Iraq | — | — | 0.01% | 0.07% | 0.23% |
| 46 | Jordan | — | 0.01% | 0.03% | 0.13% | 0.45% |
| 47 | Uzbekistan | — | — | 0.03% | 0.14% | 0.48% |
| 48 | Panama | — | — | 0.01% | 0.07% | 0.19% |

## 🎯 Headline calls

- **Most likely champion:** Argentina (23%, ±0.6% Monte Carlo 95% CI)
- **Most likely final pairing:** Argentina vs France (8.1% of simulations)
- **Top contenders:** Argentina 23%, France 15%, Spain 11%, England 7.9%

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
| Mexico | 1889 | 1.85 | 1.29 | 100% | 100% |
| South Africa | 1708 | 1.34 | 1.88 | — | 100% |
| South Korea | 1738 | 1.69 | 1.73 | — | 68% |
| Czechia | 1698 | 1.39 | 1.85 | — | — |

*Most likely qualifiers: Mexico (1st) & South Africa (2nd) — 100%.*

**Group B**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Switzerland | 1915 | 1.87 | 1.11 | 100% | 100% |
| Canada | 1784 | 1.64 | 1.66 | — | 100% |
| Bosnia & Herzegovina | 1743 | 1.57 | 1.71 | — | 100% |
| Qatar | 1640 | 1.37 | 2.19 | — | — |

*Most likely qualifiers: Switzerland (1st) & Canada (2nd) — 100%.*

**Group C**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Brazil | 1928 | 2.38 | 1.21 | 100% | 100% |
| Morocco | 1896 | 1.75 | 1.20 | — | 100% |
| Scotland | 1736 | 1.45 | 1.77 | — | 12% |
| Haiti | 1604 | 1.12 | 2.33 | — | — |

*Most likely qualifiers: Brazil (1st) & Morocco (2nd) — 100%.*

**Group D**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Australia | 1767 | 1.74 | 1.42 | — | 100% |
| United States | 1770 | 1.57 | 1.65 | 100% | 100% |
| Paraguay | 1780 | 1.37 | 1.34 | — | 100% |
| Türkiye | 1834 | 1.93 | 1.75 | — | — |

*Most likely qualifiers: United States (1st) & Australia (2nd) — 100%.*

**Group E**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Germany | 1870 | 2.32 | 1.44 | 100% | 100% |
| Ecuador | 1887 | 1.63 | 1.06 | — | 100% |
| Ivory Coast | 1740 | 1.50 | 1.87 | — | 100% |
| Curaçao | 1587 | 1.04 | 2.21 | — | — |

*Most likely qualifiers: Germany (1st) & Ivory Coast (2nd) — 100%.*

**Group F**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Netherlands | 1922 | 2.43 | 1.27 | 100% | 100% |
| Japan | 1841 | 2.16 | 1.29 | — | 100% |
| Sweden | 1733 | 1.38 | 1.86 | — | 100% |
| Tunisia | 1586 | 0.90 | 2.12 | — | — |

*Most likely qualifiers: Netherlands (1st) & Japan (2nd) — 100%.*

**Group G**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Egypt | 1731 | 1.34 | 1.76 | 41% | 100% |
| Belgium | 1873 | 2.15 | 1.45 | 32% | 89% |
| IR Iran | 1767 | 1.63 | 1.46 | 27% | 74% |
| New Zealand | 1579 | 1.10 | 2.21 | — | 10% |

*Most likely qualifiers: Egypt (1st) & Belgium (2nd) — 33%.*

**Group H**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Spain | 2036 | 2.75 | 1.01 | 84% | 100% |
| Cabo Verde | 1609 | 1.05 | 2.21 | 2.2% | 56% |
| Saudi Arabia | 1587 | 1.14 | 1.92 | — | 44% |
| Uruguay | 1825 | 1.56 | 1.25 | 14% | 36% |

*Most likely qualifiers: Spain (1st) & Cabo Verde (2nd) — 43%.*

**Group I**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| France | 2070 | 2.80 | 0.95 | 88% | 100% |
| Norway | 1796 | 2.00 | 1.71 | 12% | 100% |
| Senegal | 1825 | 1.68 | 1.53 | — | 43% |
| Iraq | 1584 | 1.15 | 1.98 | — | 1.2% |

*Most likely qualifiers: France (1st) & Norway (2nd) — 88%.*

**Group J**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Argentina | 2086 | 3.05 | 0.91 | 100% | 100% |
| Austria | 1816 | 1.88 | 1.45 | 0.40% | 88% |
| Algeria | 1774 | 1.59 | 1.78 | 0.01% | 56% |
| Jordan | 1650 | 1.34 | 1.76 | — | 1.6% |

*Most likely qualifiers: Argentina (1st) & Austria (2nd) — 72%.*

**Group K**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| Portugal | 1985 | 2.58 | 1.29 | 35% | 100% |
| Colombia | 1979 | 2.42 | 1.13 | 65% | 100% |
| DR Congo | 1687 | 1.35 | 2.05 | — | 30% |
| Uzbekistan | 1694 | 1.35 | 1.64 | — | 2.0% |

*Most likely qualifiers: Colombia (1st) & Portugal (2nd) — 64%.*

**Group L**

| Team | Elo | Att | Def | Win group | Advance |
|------|----:|----:|----:|----------:|--------:|
| England | 1998 | 2.45 | 0.98 | 80% | 100% |
| Ghana | 1695 | 1.52 | 1.96 | 6.0% | 100% |
| Croatia | 1897 | 1.97 | 1.24 | 14% | 90% |
| Panama | 1700 | 1.27 | 1.82 | — | 1.1% |

*Most likely qualifiers: England (1st) & Croatia (2nd) — 49%.*

## 💰 Model vs. betting market

Model champion probability vs. the **de-vigged** market probability (`(1 / decimal odds)` normalised across the listed teams to strip out the bookmaker margin of ~21%). A sanity check, and a way to spot where the model disagrees with the market.

> Polymarket (real-money) has **France 17.0%** ahead of **Spain 16.1%** — bookmakers still have Spain a fraction shorter. The two sharpest market views disagree on the favourite.

| Team | Model | Market (de-vig) | Polymarket | Decimal odds | Lean |
|------|------:|----------------:|-----------:|-------------:|:-----|
| Spain | 11% | 15% | 16.1% | 5.5 | market higher |
| France | 15% | 14% | 17.0% | 5.75 | ≈ agree |
| England | 7.9% | 11% | 11.1% | 7.5 | market higher |
| Brazil | 4.0% | 9.2% | 8.4% | 9 | market higher |
| Argentina | 23% | 9.2% | 9.0% | 9 | model higher |
| Portugal | 4.8% | 6.9% | 9.5% | 12 | market higher |
| Germany | 2.8% | 5.5% | 5.6% | 15 | market higher |
| Netherlands | 3.5% | 3.7% | 3.9% | 22 | ≈ agree |
| Norway | 0.69% | 2.8% | — | 29 | market higher |
| Belgium | 1.4% | 2.4% | 1.9% | 34 | market higher |
| Colombia | 5.7% | 2.3% | 0.7% | 36 | model higher |
| Morocco | 1.5% | 1.6% | — | 51 | ≈ agree |
| Japan | 1.8% | 1.6% | — | 52 | model higher |
| United States | 1.5% | 1.3% | — | 63 | model higher |
| Uruguay | 0.39% | 1.3% | — | 65 | market higher |
| Switzerland | 2.4% | 1.2% | — | 66 | model higher |
| Türkiye | — | 1.2% | — | 67 | market higher |
| Croatia | 1.7% | 1.2% | — | 67 | model higher |
| Mexico | 4.6% | 1.0% | — | 81 | model higher |
| Senegal | 0.16% | 1.0% | — | 81 | market higher |
| Ecuador | 1.6% | 0.82% | — | 101 | model higher |
| Austria | 0.71% | 0.82% | — | 101 | ≈ agree |
| Scotland | 0.02% | 0.55% | — | 151 | market higher |
| Sweden | 0.04% | 0.55% | — | 151 | market higher |
| Egypt | 0.09% | 0.55% | — | 151 | market higher |
| Algeria | 0.10% | 0.55% | — | 151 | market higher |
| Ghana | 0.07% | 0.55% | — | 151 | market higher |
| Australia | 0.61% | 0.41% | — | 201 | model higher |
| Ivory Coast | 0.09% | 0.41% | — | 201 | market higher |
| South Korea | 0.21% | 0.33% | — | 251 | market higher |
| Canada | 1.6% | 0.33% | — | 251 | model higher |
| IR Iran | 0.34% | 0.33% | — | 251 | ≈ agree |

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
