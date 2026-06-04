"""
xG-based attack/defense ratings.

This module is a thin wrapper around `qualifying_fit.py` that swaps
**goals scored / conceded** for **expected goals (xG) for / against**.
xG is a better signal: a team that under-performs xG was probably
unlucky and should be rated up; an over-performing team should be
rated down.

Data: `data/qualifying_xg.csv` (same shape as `qualifying.csv`, plus
`xg_for`, `xg_against`). Columns:

    team,confederation,matches,gf,ga,xg_for,xg_against

This file is not committed. The reachable data sources (FBref,
StatsBomb) are behind Cloudflare bot protection and don't respond to
`curl`/`WebFetch` from this environment (HTTP 403). To populate:

  1. Pull the qualifying campaign xG tables manually from FBref:
     https://fbref.com/en/comps/1/World-Cup-Stats
     https://fbref.com/en/comps/<n>/  (per qualifying campaign)
  2. Save as `data/qualifying_xg.csv` in the shape above.
  3. The blend below is a drop-in replacement for `qualifying_fit.blend`
     and will fold xG into `data/derive_ratings.py` automatically.

Until that file is present the call site falls back to the
goals-based blend (current production path).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass

from .qualifying_fit import (TYPICAL_OPP, N_PRIOR, shrinkage_weight)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
XG_CSV = os.path.join(DATA_DIR, "qualifying_xg.csv")


@dataclass(frozen=True)
class XGRecord:
    team: str
    matches: int
    xg_for: float
    xg_against: float
    confederation: str

    @property
    def xgf_per_match(self) -> float:
        return self.xg_for / self.matches if self.matches else 0.0

    @property
    def xga_per_match(self) -> float:
        return self.xg_against / self.matches if self.matches else 0.0


def load_xg(path: str | None = None) -> dict[str, XGRecord]:
    """Return {team: XGRecord} from `data/qualifying_xg.csv`, or `{}` when
    the file is absent (the standard case in this environment)."""
    path = path or XG_CSV
    out: dict[str, XGRecord] = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            team = (row.get("team") or "").strip()
            if not team or team.startswith("#"):
                continue
            out[team] = XGRecord(
                team=team,
                matches=int(row["matches"]),
                xg_for=float(row["xg_for"]),
                xg_against=float(row["xg_against"]),
                confederation=row["confederation"].strip(),
            )
    return out


def implied_ratings(rec: XGRecord, lg_avg: float) -> tuple[float, float]:
    """xG-based attack / defence implied by confederation-typical opposition.
    Same accounting as `qualifying_fit.implied_ratings` but the input is xG
    instead of raw goals, which strips a chunk of finishing variance."""
    opp_attack, opp_defense = TYPICAL_OPP.get(rec.confederation, (1.0, 1.5))
    attack = rec.xgf_per_match * lg_avg / opp_defense
    defense = rec.xga_per_match * lg_avg / opp_attack
    return attack, defense


def blend(team: str, attack_prior: float, defense_prior: float,
          records: dict[str, XGRecord], lg_avg: float,
          n_prior: float = N_PRIOR) -> tuple[float, float]:
    """Drop-in replacement for `qualifying_fit.blend` using xG data when
    present. Falls back to the Elo prior when a team has no xG record."""
    rec = records.get(team)
    if rec is None or rec.matches == 0:
        return attack_prior, defense_prior
    a_data, d_data = implied_ratings(rec, lg_avg)
    w = shrinkage_weight(rec.matches, n_prior)
    return (w * a_data + (1 - w) * attack_prior,
            w * d_data + (1 - w) * defense_prior)
