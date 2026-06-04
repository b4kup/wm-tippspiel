"""
Scenario tool — nudge a team's rating and re-run the predictor.

Usage from `run.py`:

    python run.py --scenario "Spain:attack*0.85"
    python run.py --scenario "Brazil:elo+30" --scenario "France:defense*1.10"

Spec format: `TEAM:FIELD<op>VALUE` where
- `TEAM` matches a row's `name` exactly (case-insensitive lookup);
- `FIELD` is one of `elo`, `attack`, `defense`;
- `<op>` is `*` (multiplicative) or `+` (additive);
- `VALUE` is a finite float.

Multiplicative is the natural lever for attack/defense (they're
positive scalars); additive is the natural lever for Elo. Both work
on all fields — pick whichever frames the scenario you have in mind
(e.g. "Spain's star striker is out, attack down 15%" → `*0.85`;
"Brazil acclimates faster to the heat, +30 Elo" → `+30`).

Apply-time order matches CLI order — chained nudges compose
multiplicatively on the same field.
"""

from __future__ import annotations

import re
from dataclasses import replace

SPEC_RE = re.compile(
    r"^(?P<team>[^:]+):(?P<field>elo|attack|defense)"
    r"(?P<op>[*+])(?P<value>-?\d+(?:\.\d+)?)$"
)
ALLOWED_FIELDS = ("elo", "attack", "defense")


def parse_spec(spec: str) -> tuple[str, str, str, float]:
    """Return (team_name, field, op, value); raise on bad input."""
    m = SPEC_RE.match(spec.strip())
    if not m:
        raise ValueError(
            f"bad scenario spec {spec!r} — expected TEAM:FIELD<op>VALUE "
            f"with FIELD in {ALLOWED_FIELDS} and <op> in '*' or '+'")
    return (m.group("team").strip(), m.group("field"),
            m.group("op"), float(m.group("value")))


def apply_scenarios(teams: list, specs: list[str]
                    ) -> tuple[list, list[str]]:
    """Return (new_teams_list, human_readable_log).

    Unrecognised team names raise `KeyError` — typos in scenarios should
    fail loudly rather than silently change nothing."""
    by_name = {t.name.lower(): i for i, t in enumerate(teams)}
    teams = list(teams)
    log: list[str] = []
    for spec in specs:
        team_name, field, op, value = parse_spec(spec)
        i = by_name.get(team_name.lower())
        if i is None:
            raise KeyError(f"unknown team in scenario {spec!r}: {team_name}")
        t = teams[i]
        before = getattr(t, field)
        after = before * value if op == "*" else before + value
        teams[i] = replace(t, **{field: after})
        log.append(f"{t.name}: {field} {before:.3f} -> {after:.3f} ({op}{value})")
    return teams, log
