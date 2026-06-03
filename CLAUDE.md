# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Project

WM Tippspiel — 2026 World Cup statistical predictor + point-maximizing Tippspiel
tip generator. Pure Python 3.10+, **stdlib only** (no dependencies, no
`requirements.txt`). Monte Carlo tournament simulation built on per-team
attack/defense ratings, independent Poisson goals with Dixon-Coles low-score
correction, rating-uncertainty resampling, and the real 48-team FIFA bracket.

## Layout

```
run.py                      # CLI: simulate tournament -> output/predictions.md
tipps.py                    # CLI: EV-optimal group-match tips -> output/tipps.md
update.py                   # CLI: live re-tune + re-score -> output/live_status.md
src/model.py                # match model: ratings -> expected goals -> scoreline
src/simulate.py             # Monte Carlo driver
src/tournament.py           # groups, third-place selection, knockout
src/tippspiel.py            # scoring rules + EV-maximal tip search
src/liveupdate.py           # scoring + calibration + report glue for update.py
src/results.py              # results.csv loader, conditioning, rating re-tune
src/report.py               # predictions.md generator
data/teams.csv              # team ratings (the inputs you tweak)
data/derive_ratings.py      # generates attack/defense from Elo + style
data/bracket.py             # knockout bracket structure (editable config)
data/results.csv            # live match results, append as matches play
data/our_tips.csv           # frozen Tippspiel tips for scoring
tests/test_model.py         # smoke tests
output/                     # generated Markdown reports (committed)
```

## Commands

```bash
python run.py                              # 20k sims -> output/predictions.md
python run.py --sims 100000 --seed 7       # more sims, custom seed
python tipps.py --preset check24           # CHECK24 4/3/2 -> output/tipps.md
python tipps.py --exact 3 --diff 2 --tendency 1   # custom pool rules
python update.py                           # live re-tune -> output/live_status.md
python update.py --risk aggressive         # chase exact scores when behind

python -m pytest tests/ -q                 # run tests
python tests/test_model.py                 # or run directly
```

## Conventions

- **No new dependencies.** Stdlib only — `random`, `math`, `dataclasses`, `csv`,
  `argparse`. Do not add numpy/pandas/scipy.
- Model parameters live in `ModelParams` (`src/model.py`). Constants tuned
  together with `data/derive_ratings.py` (`LG_AVG`, `K_Q`) — change in lockstep.
- CLIs prepend repo root to `sys.path` so scripts run via `python run.py` and as
  modules. Keep that pattern when adding entry points.
- Reports are Markdown, written to `output/`, committed to the repo.
- Scoring presets (`PRESETS` in `src/tippspiel.py`): default is `check24`
  (4 exact / 3 right tendency + goal diff / 2 right winner; non-exact correct
  draw scores 3).

## When making changes

- Re-run `tests/test_model.py` — fast smoke check.
- If model math changes, regenerate `output/predictions.md` with default flags
  so the committed report matches the code.
- Live-update flow: `tipps.py --save-tips data/our_tips.csv` freezes tips once;
  `update.py` then scores them as `data/results.csv` grows.

## Caveats

- Ratings in `data/teams.csv` are a hand-assembled June-2026 snapshot, not a
  live feed. `DATA_SOURCES.md` lists where to source better numbers.
- Knockout bracket in `data/bracket.py` is the official FIFA bracket; the
  specific third-placed team filling each slot is solved by constraint matching.
- See `IMPROVEMENTS.md` for the model roadmap.
