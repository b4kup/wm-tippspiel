# Model backtest — 2018 + 2022 World Cups

*Generated 2026-06-03. Scored on 120 matches; outcome = W/D/L at 90 minutes (extra-time / penalty results ignored — they're a separate model).*

## Headline

- **Baseline** (current defaults): log-loss `0.9237`, Brier `0.5397`, tendency-accuracy `60.0%`, goal MAE `0.873`
- **Tuned** (Nelder-Mead): log-loss `0.9147`, Brier `0.5332`, tendency-accuracy `60.0%`, goal MAE `0.969`
- Log-loss improvement: **+0.0090** (+1.0%)
- Goal-MAE change: **+0.096** (positive = worse goal precision; the optimiser targets outcome log-loss, not scoreline)
- Convergence (180 iters): `▁▁▂▄▄▄▄▄▅▅▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇████`

> ⚠️ **Bound hit**: `host_attack_mult`, `host_defense_mult`. The optimiser wants to push beyond the configured range — with only 2 hosts (Russia 2018 overperformed, Qatar 2022 underperformed) the data can't pin this down. Treat the host-edge values as suggestive, not definitive.

## Tuned constants

| Param | Baseline | Tuned | Δ | Bounds |
|-------|---------:|------:|--:|--------|
| `lg_avg` | +1.3500 | +1.5972 | +0.2472 | [1.0, 2.0] |
| `k_q` | +0.7000 | +0.8155 | +0.1155 | [0.3, 1.5] |
| `dc_rho` | -0.1000 | -0.0885 | +0.0115 | [-0.3, 0.05] |
| `host_attack_mult` | +1.1000 | +1.2000 ⚠️ at upper bound | +0.1000 | [1.0, 1.2] |
| `host_defense_mult` | +0.9200 | +0.8500 ⚠️ at lower bound | -0.0700 | [0.85, 1.0] |

## Calibration — tuned model

Bins of predicted probability vs. how often the predicted event actually happened. A well-calibrated model has `gap ≈ 0` per bin.

| Predicted prob | Observed freq | n | gap |
|---------------:|--------------:|--:|----:|
| 6.0% | 8.0% | 25 | +2.0% |
| 15.8% | 11.0% | 73 | -4.8% |
| 24.1% | 27.2% | 125 | +3.1% |
| 33.4% | 27.8% | 18 | -5.7% |
| 45.1% | 48.6% | 37 | +3.5% |
| 55.6% | 45.5% | 33 | -10.2% |
| 64.9% | 66.7% | 21 | +1.8% |
| 74.5% | 88.9% | 18 | +14.4% |
| 84.6% | 66.7% | 6 | -17.9% |
| 93.1% | 100.0% | 4 | +6.9% |

## How to apply

Rerun with `--apply` to rewrite the defaults in `src/model.py` and `data/derive_ratings.py`. After applying, regenerate the report:

```bash
python tune.py --apply
python -m data.derive_ratings
python run.py
```

## Caveats

- Historical Elos were synthesised from FIFA-rank ordering (canonical eloratings.net archives were not reachable). Each tournament's spread is rescaled to a target std-dev of 140 Elo so `K_Q` is comparable to the canonical scale, but absolute rating noise is higher than a real Elo feed would give.
- 120-match sample (expected 128 — agent missed 8 group games). Log-loss differences below ~0.005 are within noise on this dataset.
- Outcomes are W/D/L at 90 minutes — knockouts that went to extra time / penalties contribute their 90-minute result (so draws in R16/QF/SF count as draws even though one side advanced).
- Optimiser minimises log-loss, not scoreline MAE — a tuned model can be better-calibrated yet predict slightly less precise score expectations.
