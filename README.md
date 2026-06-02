# WM Tippspiel — 2026 World Cup statistical predictor

Statistically-based predictions for the 2026 FIFA World Cup (USA · Canada ·
Mexico, 48 teams). It runs a **Monte Carlo simulation** of the entire
tournament tens of thousands of times and reports, for every team, the
probability of winning its group, advancing, reaching each knockout round, and
lifting the trophy.

```
$ python run.py --sims 50000

Top 10 title contenders:
   1. Spain             21.7%
   2. France            17.1%
   3. Argentina         15.3%
   4. England            8.8%
   5. Brazil             7.2%
   6. Portugal           6.1%
   ...
```

The full report (title odds for all 48 teams, group-by-group probabilities,
round-by-round chances, most-likely final, and a model-vs-betting-market
comparison) is written to [`output/predictions.md`](output/predictions.md).

## Tippspiel tips

Playing a prediction pool? `tipps.py` computes the **point-maximizing** scoreline
for every group match under your pool's scoring rule — which is usually **not**
the most likely score (predicting the unlikely 1–1 every game scores poorly; a
representative favourite win scores more on average).

```bash
python tipps.py --preset check24                 # CHECK24 rules -> output/tipps.md
python tipps.py                                  # kicktipp 4/3/2
python tipps.py --exact 3 --diff 2 --tendency 1  # match any pool's rules
```

Built-in presets: **`check24`** (4 exact / 3 right tendency **and** goal
difference / 2 right winner — so a correct non-exact draw scores 3; bonus
questions worth 10 pts are separate) and `kicktipp` (4/3/2). The committed
[`output/tipps.md`](output/tipps.md) uses the CHECK24 ruleset.

Output: [`output/tipps.md`](output/tipps.md) — the EV-optimal tip, its expected
points, the win/draw/loss split, and the most likely score for each match.

## Quick start

No dependencies — pure Python 3.10+ standard library.

```bash
python run.py                  # 20,000 sims -> output/predictions.md
python run.py --sims 100000    # more sims = tighter probabilities (slower)
python run.py --rating-sigma 0 # disable rating uncertainty (point estimates)
python run.py --seed 7 --out output/run7.md
python tests/test_model.py     # smoke tests
```

## How it works

Each team has two ratings instead of one overall number, so matches turn on a
genuine **attack-vs-defense matchup**:

| Rating | Meaning |
|--------|---------|
| `attack`  | expected goals the team **scores** against an average World Cup side |
| `defense` | expected goals the team **concedes** against an average side (lower = better) |

For a match between A and B, expected goals combine multiplicatively (the
standard independent-Poisson / SPI-style model):

```
λ_A = attack_A · defense_B / LG_AVG        # goals A scores
λ_B = attack_B · defense_A / LG_AVG        # goals B scores
```

A sharp attack meeting a leaky defence produces goals; two compact sides grind
out a low-scoring game. Scorelines are drawn from Poisson distributions, hosts
get a small home edge, and a drawn knockout match is resolved by an
Elo-weighted shootout.

To avoid the over-confidence of a pure point-estimate model, each team's *true*
tournament strength is **resampled every simulation** from a Gaussian around its
rating (`--rating-sigma`, in Elo points), capturing rating error and
tournament-level form. This fattens the upset tail toward reality.

The tournament structure is the real 48-team format: 12 groups of 4, then the
top 2 of each group plus the 8 best third-placed teams into a Round of 32 and a
single-elimination bracket to the final.

```
data/teams.csv          team ratings (the inputs you tweak)
data/derive_ratings.py  generates attack/defense from Elo + style; rewrites teams.csv
data/bracket.py         knockout bracket structure (editable config)
src/model.py            match model: ratings -> expected goals -> scoreline
src/tournament.py       groups, third-place selection, knockout
src/simulate.py         Monte Carlo driver
src/report.py           Markdown report generator
run.py                  CLI entry point
tests/test_model.py     smoke tests
```

## Improving the predictions

The model is only as good as its inputs. To raise fidelity, replace
`data/teams.csv` with better numbers — **[`DATA_SOURCES.md`](DATA_SOURCES.md)
lists exactly where to get Elo, xG-based attack/defense, and betting odds**, and
which columns to fill. You can also re-tune the model constants in
`src/model.py` (home advantage, goal level) and `data/derive_ratings.py`
(how strongly quality and style separate attack from defence).

## Caveats

- Ratings are a hand-assembled **June-2026 snapshot**, not a live feed.
- The knockout bracket is the **official** FIFA bracket — real match numbers,
  third-place cluster codes and tree (`data/bracket.py`). The specific
  third-placed team filling each slot depends on the qualifying groups and is
  resolved by a constraint-respecting matching.
- No model captures injuries, red cards, or a hot goalkeeper. These are
  probabilities, not prophecies.
