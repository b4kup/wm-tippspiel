"""
Per-team travel + rest-day + altitude + heat fatigue going into each match.

Why this matters in 2026
------------------------
US-Canada-Mexico is the most geographically spread World Cup ever. Some teams
play a Mexico City → Vancouver → Miami group; others stay within one cluster.
Mexico City sits at 2240 m, and Miami/Houston/Dallas/Monterrey are summer
furnaces. Sports-science literature finds:
  - ~3-5% performance hit per leg of long-haul travel with short rest,
  - ~3-5% aerobic-capacity drop per 1000 m above ~1500 m for unacclimated sides,
  - ~1-2% drop per °C above ~25 °C in WBGT for unacclimated sides
    (Miami/Houston/Dallas summer afternoons reach 32-35 °C ambient; indoor
    venues with climate control cancel the effect).

All effects are small but real, and *asymmetric* between the two teams.

How fatigue is computed
-----------------------
For each team going into each match:

  km_since        = great-circle distance from their previous venue
  rest_days       = days since their previous match (large value for match 1)
  altitude_excess = max(0, venue_altitude - ALTITUDE_THRESHOLD_M),
                    but 0 for teams from altitude-acclimated nations
  heat_excess     = max(0, effective_temp_c - HEAT_THRESHOLD_C),
                    halved for teams from hot-climate nations; 0 when the
                    stadium is climate-controlled (Vancouver, Atlanta, Dallas,
                    Houston, LA, SoFi).

These map to a fatigue score that scales the team's **attack** in that match:

  fatigue = travel_per_1000km * km_since / 1000
          + rest_day_value    * max(0, REST_BASELINE_DAYS - rest_days)
          + altitude_per_1000m * altitude_excess / 1000
          + heat_per_degree   * heat_excess
  attack *= exp(-K_Q * fatigue / 4)        # damp by /4 — keeps the multiplier
                                           # consistent with injury/elo nudges

(K_Q-style scaling keeps the magnitude consistent with how injuries and
Elo-deltas map to ratings; see src/injuries.py and data/derive_ratings.py.)

A rested team with no travel playing at sea level in a 22 °C / climate-
controlled venue has zero fatigue. Tunable via the relevant `ModelParams`.

Limitations
-----------
- Travel is treated as a one-shot fatigue carryover, not cumulative across
  the whole group stage. Good enough for the scale of effect.
- Altitude / heat acclimation are binary lists of countries with
  significant high-altitude or hot-climate domestic football — not per-camp
  acclimation schedules.
- KO-stage carryover uses the same logic but is computed per sim, once the
  bracket fills in. See `ko_match_fatigue`.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
REST_BASELINE_DAYS = 3.5    # 3-4 days is the typical group-stage cadence
ALTITUDE_THRESHOLD_M = 1500.0  # below this, no altitude effect
HEAT_THRESHOLD_C = 25.0        # below this, no heat effect
INDOOR_EFFECTIVE_C = 21.0      # climate-controlled stadium proxy

# National teams whose populations / training bases sit at or near tournament
# altitudes — they don't take an altitude hit playing in Mexico City or
# Guadalajara. Sources: Mexico (capital 2240 m), Ecuador (Quito 2850 m),
# Colombia (Bogotá 2640 m).
ALTITUDE_ACCLIMATED_TEAMS = frozenset({
    "Mexico", "Ecuador", "Colombia",
})

# Teams from hot-climate nations whose squads train and play in similar
# summer conditions year-round; they're less affected by heat at Miami,
# Houston, Dallas, etc. They still take half the heat penalty (heat affects
# everyone above 30 °C, just less). Sources: tropical / subtropical / Gulf
# domestic leagues that play through June-July heat.
HEAT_ACCLIMATED_TEAMS = frozenset({
    "Mexico", "Saudi Arabia", "Qatar", "IR Iran", "United Arab Emirates",
    "Brazil", "Ecuador", "Colombia", "Paraguay", "Venezuela", "Bolivia",
    "Senegal", "Ivory Coast", "Ghana", "Egypt", "Nigeria", "Cameroon",
    "Morocco", "Tunisia", "Algeria", "DR Congo", "Cabo Verde",
    "Jamaica", "Haiti", "Cuba", "Curaçao", "Trinidad and Tobago",
})


@dataclass(frozen=True)
class Venue:
    city: str
    stadium: str
    latitude: float
    longitude: float
    altitude_m: float
    temp_c: float = 25.0      # mean June/July afternoon high (outdoor)
    indoor: bool = False      # climate-controlled stadium

    @property
    def effective_temp_c(self) -> float:
        """Temperature the players experience: outdoor ambient unless the
        stadium is climate-controlled."""
        return INDOOR_EFFECTIVE_C if self.indoor else self.temp_c


@dataclass(frozen=True)
class ScheduledMatch:
    match: int
    date: str           # YYYY-MM-DD
    group: str
    home: str
    away: str
    city: str


def _parse_iso(date_str: str) -> tuple[int, int, int]:
    y, m, d = date_str.split("-")
    return int(y), int(m), int(d)


def _days_between(d1: str, d2: str) -> int:
    """Whole days from d1 to d2 (positive when d2 is later)."""
    from datetime import date
    return (date(*_parse_iso(d2)) - date(*_parse_iso(d1))).days


def load_venues(path: str | None = None) -> dict[str, Venue]:
    path = path or os.path.join(DATA_DIR, "venues.csv")
    out: dict[str, Venue] = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["city"].strip()] = Venue(
                city=r["city"].strip(),
                stadium=r["stadium"].strip(),
                latitude=float(r["latitude"]),
                longitude=float(r["longitude"]),
                altitude_m=float(r.get("altitude_m", 0) or 0),
                temp_c=float(r.get("temp_c") or 25.0),
                indoor=str(r.get("indoor", "0")).strip() in ("1", "true", "yes"),
            )
    return out


def load_schedule(path: str | None = None) -> list[ScheduledMatch]:
    path = path or os.path.join(DATA_DIR, "schedule.csv")
    out: list[ScheduledMatch] = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append(ScheduledMatch(
                match=int(r["match"]),
                date=r["date"].strip(),
                group=r["group"].strip(),
                home=r["home"].strip(),
                away=r["away"].strip(),
                city=r["city"].strip(),
            ))
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    r_earth = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2)
    return 2 * r_earth * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class TeamFatigue:
    """One team's carryover into one match."""
    km_since: float
    rest_days: int
    altitude_excess_m: float    # 0 if at sea level or team is acclimated
    heat_excess_c: float = 0.0  # °C above HEAT_THRESHOLD_C, halved if acclimated


@dataclass(frozen=True)
class MatchFatigue:
    """Fatigue going into a single match, per team. Keyed alphabetically
    so the dict lookup is order-independent."""
    a: TeamFatigue      # team whose name sorts first
    b: TeamFatigue      # team whose name sorts second


def compute_match_fatigues(
    schedule: list[ScheduledMatch] | None = None,
    venues: dict[str, Venue] | None = None,
) -> dict[tuple[str, str], MatchFatigue]:
    """For each (home, away) team-pair in the group stage, compute km
    travelled, rest days and altitude exposure each side carries into that
    match. Keyed by alphabetically-sorted team pair so the lookup works
    regardless of which side `simulate_match` treats as "home".
    """
    schedule = schedule or load_schedule()
    venues = venues or load_venues()
    by_team: dict[str, list[tuple[str, str]]] = {}
    for m in schedule:
        for t in (m.home, m.away):
            by_team.setdefault(t, []).append((m.date, m.city))
    for items in by_team.values():
        items.sort()

    out: dict[tuple[str, str], MatchFatigue] = {}
    for m in schedule:
        venue = venues.get(m.city)
        alt = max(0.0, (venue.altitude_m if venue else 0) - ALTITUDE_THRESHOLD_M)
        heat = max(0.0, ((venue.effective_temp_c if venue else 25.0)
                         - HEAT_THRESHOLD_C))
        home_km, home_rest = _carryover(by_team[m.home], m.date, venues)
        away_km, away_rest = _carryover(by_team[m.away], m.date, venues)
        home_alt = 0.0 if m.home in ALTITUDE_ACCLIMATED_TEAMS else alt
        away_alt = 0.0 if m.away in ALTITUDE_ACCLIMATED_TEAMS else alt
        home_heat = heat * (0.5 if m.home in HEAT_ACCLIMATED_TEAMS else 1.0)
        away_heat = heat * (0.5 if m.away in HEAT_ACCLIMATED_TEAMS else 1.0)
        a_name, b_name = sorted((m.home, m.away))
        if m.home == a_name:
            a = TeamFatigue(home_km, home_rest, home_alt, home_heat)
            b = TeamFatigue(away_km, away_rest, away_alt, away_heat)
        else:
            a = TeamFatigue(away_km, away_rest, away_alt, away_heat)
            b = TeamFatigue(home_km, home_rest, home_alt, home_heat)
        out[(a_name, b_name)] = MatchFatigue(a=a, b=b)
    return out


def lookup_fatigue(fatigues: dict[tuple[str, str], MatchFatigue],
                   team_a: str, team_b: str
                   ) -> tuple[TeamFatigue, TeamFatigue] | None:
    """Return (fatigue_for_team_a, fatigue_for_team_b), or None if not
    in the schedule. Handles either ordering of the team names."""
    key = tuple(sorted((team_a, team_b)))
    mf = fatigues.get(key)
    if mf is None:
        return None
    return (mf.a, mf.b) if team_a == key[0] else (mf.b, mf.a)


def fatigue_score(tf: TeamFatigue, travel_per_1000km: float,
                  rest_day_value: float, altitude_per_1000m: float,
                  heat_per_degree: float = 0.0) -> float:
    """Combine travel / rest-deficit / altitude / heat into one small
    non-negative scalar (typically 0-0.07) suitable for use as a goals-
    multiplier exponent. See `src/model.expected_goals`."""
    return (
        travel_per_1000km * tf.km_since / 1000.0
        + rest_day_value * max(0.0, REST_BASELINE_DAYS - tf.rest_days)
        + altitude_per_1000m * tf.altitude_excess_m / 1000.0
        + heat_per_degree * tf.heat_excess_c
    )


def _carryover(team_history: list[tuple[str, str]], match_date: str,
               venues: dict[str, Venue]) -> tuple[float, int]:
    """For one team approaching a match on `match_date`, find the previous
    match in their history and compute (km travelled, rest days) since then.
    Returns (0, large_rest) for a team's first match."""
    prev = None
    for d, c in team_history:
        if d >= match_date:
            break
        prev = (d, c)
    if prev is None:
        # First match: no carryover (assume teams arrived fresh).
        return 0.0, 30
    cur_match = next((d, c) for d, c in team_history if d == match_date)
    prev_v = venues.get(prev[1])
    cur_v = venues.get(cur_match[1])
    if prev_v is None or cur_v is None:
        return 0.0, _days_between(prev[0], match_date)
    km = haversine_km(prev_v.latitude, prev_v.longitude,
                      cur_v.latitude, cur_v.longitude)
    return km, _days_between(prev[0], match_date)


@dataclass(frozen=True)
class KOFixture:
    """Date + venue for a fixed slot in the knockout bracket. Indexed by
    (round_label, bracket_index): bracket_index goes 0..15 for R32, 0..7 for
    R16, 0..3 for QF, 0..1 for SF, 0 for Final, in bracket order — matching
    the consecutive pairing used in `src/tournament.run_knockout`."""
    date: str
    city: str


# Real 2026 KO schedule, transcribed from FIFA's published draw. R32 venues
# are in `data/bracket.py` comments; R16/QF/SF/F per FIFA news releases.
# Dates for R32 ties not specifically reported are placed inside the
# Jun 28 - Jul 3 window so each winner gets a plausible rest gap.
KO_SCHEDULE: dict[tuple[str, int], KOFixture] = {
    ("R32",  0): KOFixture("2026-06-29", "Boston"),
    ("R32",  1): KOFixture("2026-06-30", "New York"),
    ("R32",  2): KOFixture("2026-06-28", "Los Angeles"),
    ("R32",  3): KOFixture("2026-06-28", "Monterrey"),
    ("R32",  4): KOFixture("2026-07-02", "Toronto"),
    ("R32",  5): KOFixture("2026-07-02", "Los Angeles"),
    ("R32",  6): KOFixture("2026-07-01", "San Francisco"),
    ("R32",  7): KOFixture("2026-07-01", "Seattle"),
    ("R32",  8): KOFixture("2026-06-29", "Houston"),
    ("R32",  9): KOFixture("2026-06-30", "Dallas"),
    ("R32", 10): KOFixture("2026-06-30", "Mexico City"),
    ("R32", 11): KOFixture("2026-07-01", "Atlanta"),
    ("R32", 12): KOFixture("2026-07-03", "Miami"),
    ("R32", 13): KOFixture("2026-07-03", "Dallas"),
    ("R32", 14): KOFixture("2026-07-02", "Vancouver"),
    ("R32", 15): KOFixture("2026-07-03", "Kansas City"),
    ("R16",  0): KOFixture("2026-07-04", "Philadelphia"),
    ("R16",  1): KOFixture("2026-07-04", "Houston"),
    ("R16",  2): KOFixture("2026-07-06", "Dallas"),
    ("R16",  3): KOFixture("2026-07-06", "Seattle"),
    ("R16",  4): KOFixture("2026-07-05", "New York"),
    ("R16",  5): KOFixture("2026-07-05", "Mexico City"),
    ("R16",  6): KOFixture("2026-07-07", "Atlanta"),
    ("R16",  7): KOFixture("2026-07-07", "Vancouver"),
    ("QF",   0): KOFixture("2026-07-09", "Boston"),
    ("QF",   1): KOFixture("2026-07-10", "Kansas City"),
    ("QF",   2): KOFixture("2026-07-10", "Los Angeles"),
    ("QF",   3): KOFixture("2026-07-11", "Miami"),
    ("SF",   0): KOFixture("2026-07-14", "Dallas"),
    ("SF",   1): KOFixture("2026-07-15", "Atlanta"),
    ("Final", 0): KOFixture("2026-07-19", "New York"),
}


def team_last_group_fixture(schedule: list[ScheduledMatch] | None = None
                            ) -> dict[str, tuple[str, str]]:
    """For each team, return (date, city) of their final group-stage match.
    Used as the starting point for KO travel/rest accounting."""
    schedule = schedule or load_schedule()
    last: dict[str, tuple[str, str]] = {}
    for m in schedule:
        for t in (m.home, m.away):
            cur = last.get(t)
            if cur is None or m.date > cur[0]:
                last[t] = (m.date, m.city)
    return last


def ko_team_fatigue(team_name: str, last_date: str, last_city: str,
                    target: KOFixture,
                    venues: dict[str, Venue]) -> TeamFatigue:
    """Travel/rest/altitude/heat carryover for one team into one KO match.

    Uses the same accounting as the group stage: km between consecutive
    venues, rest days since last match, altitude/heat at the target venue
    with acclimation rules applied."""
    prev_v = venues.get(last_city)
    cur_v = venues.get(target.city)
    if prev_v is None or cur_v is None:
        km = 0.0
    else:
        km = haversine_km(prev_v.latitude, prev_v.longitude,
                          cur_v.latitude, cur_v.longitude)
    rest = _days_between(last_date, target.date)
    alt_raw = max(0.0, (cur_v.altitude_m if cur_v else 0.0)
                  - ALTITUDE_THRESHOLD_M)
    heat_raw = max(0.0, ((cur_v.effective_temp_c if cur_v else 25.0)
                         - HEAT_THRESHOLD_C))
    alt = 0.0 if team_name in ALTITUDE_ACCLIMATED_TEAMS else alt_raw
    heat = heat_raw * (0.5 if team_name in HEAT_ACCLIMATED_TEAMS else 1.0)
    return TeamFatigue(km, rest, alt, heat)


def total_travel_per_team(
    schedule: list[ScheduledMatch] | None = None,
    venues: dict[str, Venue] | None = None,
) -> dict[str, float]:
    """Sum of km between consecutive group-stage venues, per team."""
    schedule = schedule or load_schedule()
    venues = venues or load_venues()
    by_team: dict[str, list[tuple[str, str]]] = {}
    for m in schedule:
        for t in (m.home, m.away):
            by_team.setdefault(t, []).append((m.date, m.city))
    out: dict[str, float] = {}
    for team, items in by_team.items():
        items.sort()
        km = 0.0
        for (_, c1), (_, c2) in zip(items, items[1:]):
            v1, v2 = venues.get(c1), venues.get(c2)
            if v1 and v2:
                km += haversine_km(v1.latitude, v1.longitude,
                                   v2.latitude, v2.longitude)
        out[team] = km
    return out
