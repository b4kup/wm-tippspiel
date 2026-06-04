"""
CLI: backtest the match model on 2018 + 2022 World Cups, then auto-tune
ModelParams to minimise log-loss on those outcomes. Writes a Markdown
report to `output/backtest.md`. Optionally writes the tuned constants
back into the codebase (`--apply`).

    python tune.py                  # backtest + tune + write report
    python tune.py --verbose        # print per-iteration progress
    python tune.py --apply          # also rewrite default constants in
                                    # src/model.py and data/derive_ratings.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.backtest import BacktestStats, load_all, score_model
from src.tune import PARAM_SPEC, TunedParams, tune

REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "output", "backtest.md")


def _fmt(stats: BacktestStats) -> str:
    return (f"log-loss `{stats.log_loss:.4f}`, "
            f"Brier `{stats.brier:.4f}`, "
            f"tendency-accuracy `{stats.accuracy * 100:.1f}%`, "
            f"goal MAE `{stats.mae_goals:.3f}`")


def _calibration_table(stats: BacktestStats) -> list[str]:
    L = ["| Predicted prob | Observed freq | n | gap | reliability |",
         "|---------------:|--------------:|--:|----:|:------------|"]
    for p, freq, n in stats.calibration:
        gap = freq - p
        L.append(f"| {p*100:.1f}% | {freq*100:.1f}% | {n} | {gap*100:+.1f}% "
                 f"| {_reliability_bar(p, freq)} |")
    return L


def _reliability_bar(predicted: float, observed: float, width: int = 24) -> str:
    """Side-by-side mini-bar: `P` marks the predicted bin centre on a
    0-100% scale, `█` overlays the observed frequency. Good calibration =
    the `█` ends roughly where `P` sits. Wide gap = visibly mis-calibrated.
    """
    p_pos = max(0, min(width - 1, int(predicted * width)))
    o_pos = max(0, min(width, int(observed * width)))
    chars = []
    for i in range(width):
        if i < o_pos:
            chars.append("█")
        elif i == p_pos:
            chars.append("│")
        else:
            chars.append("·")
    return "`" + "".join(chars) + "`"


def _calibration_summary(stats: BacktestStats) -> str:
    """Single-line summary: mean |gap| across bins (expected calibration
    error, ECE) and how many bins are off by >5 pp."""
    if not stats.calibration:
        return "no bins"
    ece = sum(n * abs(freq - p) for p, freq, n in stats.calibration)
    total = sum(n for _, _, n in stats.calibration)
    if total == 0:
        return "no samples"
    ece /= total
    bad = sum(1 for p, freq, _n in stats.calibration if abs(freq - p) > 0.05)
    return (f"**ECE** (sample-weighted mean |gap|): **{ece*100:.1f} pp**; "
            f"{bad}/{len(stats.calibration)} bins miss by > 5 pp.")


def _sparkline(history: list[tuple[int, float]]) -> str:
    if not history:
        return ""
    vals = [v for _, v in history]
    lo, hi = min(vals), max(vals)
    blocks = "▁▂▃▄▅▆▇█"
    if hi - lo < 1e-12:
        return blocks[0] * len(vals)
    return "".join(blocks[min(7, int((1 - (v - lo) / (hi - lo)) * 7))] for v in vals)


def write_report(baseline_v: list[float], tuned: TunedParams,
                 sb: BacktestStats, sa: BacktestStats,
                 history: list[tuple[int, float]]) -> None:
    rows = []
    bound_hits: list[str] = []
    for (name, _, lo, hi), b, t in zip(PARAM_SPEC, baseline_v, tuned.to_vector()):
        delta = t - b
        # Flag params that converged to within 1% of either bound.
        span = max(hi - lo, 1e-9)
        hit = ""
        if abs(t - lo) / span < 0.01:
            hit = " ⚠️ at lower bound"; bound_hits.append(name)
        elif abs(t - hi) / span < 0.01:
            hit = " ⚠️ at upper bound"; bound_hits.append(name)
        rows.append(f"| `{name}` | {b:+.4f} | {t:+.4f}{hit} | {delta:+.4f} | [{lo}, {hi}] |")

    goal_mae_delta = sa.mae_goals - sb.mae_goals
    body = [
        f"# Model backtest — 2018 + 2022 World Cups",
        "",
        f"*Generated {date.today().isoformat()}. "
        f"Scored on {sa.n_matches} matches; outcome = W/D/L at 90 minutes "
        "(extra-time / penalty results ignored — they're a separate model).*",
        "",
        "## Headline",
        "",
        f"- **Baseline** (current defaults): {_fmt(sb)}",
        f"- **Tuned** (Nelder-Mead): {_fmt(sa)}",
        f"- Log-loss improvement: **{(sb.log_loss - sa.log_loss):+.4f}** "
        f"({(sb.log_loss - sa.log_loss) / sb.log_loss * 100:+.1f}%)",
        f"- Goal-MAE change: **{goal_mae_delta:+.3f}** "
        f"(positive = worse goal precision; the optimiser targets outcome "
        "log-loss, not scoreline)",
        f"- Convergence ({len(history)} iters): `{_sparkline(history)}`",
        "",]
    if bound_hits:
        body.extend([
            "> ⚠️ **Bound hit**: " + ", ".join(f"`{n}`" for n in bound_hits) +
            ". The optimiser wants to push beyond the configured range — "
            "with only 2 hosts (Russia 2018 overperformed, Qatar 2022 "
            "underperformed) the data can't pin this down. Treat the "
            "host-edge values as suggestive, not definitive.",
            "",
        ])
    body.extend([
        "## Tuned constants",
        "",
        "| Param | Baseline | Tuned | Δ | Bounds |",
        "|-------|---------:|------:|--:|--------|",
        *rows,
        "",
        "## Calibration — tuned model",
        "",
        "Bins of predicted probability vs. how often the predicted event "
        "actually happened. A well-calibrated model has `gap ≈ 0` per bin; "
        "the `reliability` column shows the observed frequency (█) overlaid "
        "with the predicted bin centre (│) on the same 0-100% scale.",
        "",
        _calibration_summary(sa),
        "",
        *_calibration_table(sa),
        "",
        "## How to apply",
        "",
        "Rerun with `--apply` to rewrite the defaults in `src/model.py` and "
        "`data/derive_ratings.py`. After applying, regenerate the report:",
        "",
        "```bash",
        "python tune.py --apply",
        "python -m data.derive_ratings",
        "python run.py",
        "```",
        "",
        "## Caveats",
        "",
        "- Historical Elos were synthesised from FIFA-rank ordering "
        "(canonical eloratings.net archives were not reachable). Each "
        "tournament's spread is rescaled to a target std-dev of "
        "140 Elo so `K_Q` is comparable to the canonical scale, but "
        "absolute rating noise is higher than a real Elo feed would give.",
        f"- {sa.n_matches}-match sample (expected 128 — agent missed 8 "
        "group games). Log-loss differences below ~0.005 are within "
        "noise on this dataset.",
        "- Outcomes are W/D/L at 90 minutes — knockouts that went to "
        "extra time / penalties contribute their 90-minute result (so "
        "draws in R16/QF/SF count as draws even though one side advanced).",
        "- Optimiser minimises log-loss, not scoreline MAE — a tuned "
        "model can be better-calibrated yet predict slightly less precise "
        "score expectations.",
        "",
    ])
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))


def apply_to_codebase(tuned: TunedParams) -> list[str]:
    """Rewrite default constants in src/model.py and data/derive_ratings.py.
    Regex-based so it stays idempotent across multiple --apply runs.
    Returns list of files modified (deduped)."""
    here = os.path.dirname(os.path.abspath(__file__))
    model_py = os.path.join(here, "src", "model.py")
    derive_py = os.path.join(here, "data", "derive_ratings.py")
    modified: set[str] = set()

    def _sub(path: str, pattern: str, repl: str):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        new, n = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE)
        if n == 0:
            raise RuntimeError(f"pattern not found in {path}: {pattern!r}")
        if new != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            modified.add(path)

    # Match a number literal (optional minus, digits, optional decimal).
    num = r"-?\d+(?:\.\d+)?"

    # src/model.py module constants and dataclass defaults
    _sub(model_py, rf"^LG_AVG = {num}$",
         f"LG_AVG = {tuned.lg_avg:.4f}")
    _sub(model_py, rf"^K_Q = {num}$",
         f"K_Q = {tuned.k_q:.4f}")
    _sub(model_py, rf"host_attack_mult: float = {num}",
         f"host_attack_mult: float = {tuned.host_attack_mult:.4f}")
    _sub(model_py, rf"host_defense_mult: float = {num}",
         f"host_defense_mult: float = {tuned.host_defense_mult:.4f}")
    _sub(model_py, rf"dc_rho: float = {num}",
         f"dc_rho: float = {tuned.dc_rho:.4f}")

    # data/derive_ratings.py
    _sub(derive_py,
         rf"^LG_AVG = {num}\s*#.*$",
         f"LG_AVG = {tuned.lg_avg:.4f}    # tuned by tune.py against 2018/2022 backtest")
    _sub(derive_py,
         rf"^K_Q = {num}\s*#.*$",
         f"K_Q = {tuned.k_q:.4f}       # tuned by tune.py against 2018/2022 backtest")
    return sorted(modified)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true",
                    help="print Nelder-Mead progress")
    ap.add_argument("--apply", action="store_true",
                    help="rewrite default constants in src/model.py + "
                         "data/derive_ratings.py")
    args = ap.parse_args()

    print("Loading 2018 + 2022 World Cup data...")
    datasets = load_all()
    total = sum(len(matches) for _teams, matches in datasets)
    print(f"  loaded {total} matches across {len(datasets)} tournaments.")

    print("Tuning ModelParams (Nelder-Mead)...")
    tuned, sb, sa, history = tune(datasets, verbose=args.verbose)

    print(f"\nBaseline: {_fmt(sb)}")
    print(f"Tuned:    {_fmt(sa)}")
    print(f"Tuned params:")
    for (name, default, _, _), val in zip(PARAM_SPEC, tuned.to_vector()):
        print(f"  {name:<20} {default:+.4f}  ->  {val:+.4f}")

    baseline_v = [spec[1] for spec in PARAM_SPEC]
    write_report(baseline_v, tuned, sb, sa, history)
    print(f"\nReport written to {REPORT_PATH}")

    if args.apply:
        files = apply_to_codebase(tuned)
        print(f"\nApplied tuned constants to:")
        for f in files:
            print(f"  {f}")
        print("Run `python -m data.derive_ratings` to regenerate teams.csv, "
              "then `python run.py` to regenerate predictions.")


if __name__ == "__main__":
    main()
