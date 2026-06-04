"""
Pull squad-value / minutes / injury data from Transfermarkt.

Why this exists
---------------
`data/injuries.csv` is a curated hand list. Transfermarkt publishes a
live "absences" widget per club and a market-value column per player.
This module fetches a team's squad page and parses what it can with
stdlib regex — no BeautifulSoup, no extra deps.

What's here is *starter scaffolding*, not a production scraper. The
HTML changes; the parser is brittle. Treat it as a baseline for a
human to audit and refine, not an autonomous data pipeline.

How to use
----------
    from src.transfermarkt import fetch_team_page, parse_squad

    html = fetch_team_page("https://www.transfermarkt.com/spanien/...")
    rows = parse_squad(html)
    for r in rows:
        print(r)

For a national team, the Transfermarkt URL follows the pattern
`https://www.transfermarkt.com/<slug>/startseite/verein/<id>`
(slug examples: `spanien`, `frankreich`, `brasilien`).

Limitations
-----------
- Network policy in this environment lets Transfermarkt through (HTTP
  200) but FBref and most odds aggregators 403 the request. Run from
  a workstation if you need richer scraping.
- The parser pulls player rows from the squad table; injury status is
  not always rendered in the HTML (sometimes it's in a side widget
  loaded by JS). Cross-check critical entries with the live site.
- Transfermarkt rate-limits aggressive scraping. One team page per
  ~5 seconds with a real-browser User-Agent is the safe budget.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
TIMEOUT_S = 15


@dataclass(frozen=True)
class SquadEntry:
    """One row pulled from a Transfermarkt squad page."""
    name: str
    position: str
    market_value_eur: float | None
    injury_note: str | None        # "out", "doubtful", or None


def fetch_team_page(url: str) -> str:
    """GET a Transfermarkt URL and return the HTML body. Raises on
    non-2xx responses."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read().decode("utf-8", errors="replace")


# Transfermarkt anchors each player row on a market-value link of the
# shape `/<player-slug>/marktwertverlauf/spieler/<id>`. We grab the slug
# and the printed value, then look back into the row chunk for the
# position cell. The slug, with dashes replaced by spaces and title-cased,
# is a reasonable display name (close to the actual player name).
PLAYER_RE = re.compile(
    r'<a href="/(?P<slug>[a-z0-9\-]+)/marktwertverlauf/spieler/\d+"'
    r'[^>]*>€(?P<value>[\d.]+)(?P<suffix>[mk]?)</a>',
    re.IGNORECASE,
)

POSITION_RE = re.compile(
    r'(Goalkeeper|Centre[\- ]Back|Centre[\- ]Forward|Left[\- ]?Back'
    r'|Right[\- ]?Back|Left Winger|Right Winger|Attacking Midfield'
    r'|Defensive Midfield|Central Midfield|Second Striker'
    r'|Left Midfield|Right Midfield)',
)

INJURY_NOTE_RE = re.compile(
    r'(injured|out|doubtful|suspension|suspended)', re.IGNORECASE,
)


def parse_squad(html: str) -> list[SquadEntry]:
    """Return SquadEntry rows extracted from the team page HTML.

    Best-effort: malformed rows are skipped. Market values are
    normalised to euros (m → ×1e6, k → ×1e3, plain → as-is)."""
    out: list[SquadEntry] = []
    seen: set[str] = set()
    for m in PLAYER_RE.finditer(html):
        slug = m.group("slug").lower()
        if slug in seen:
            continue
        seen.add(slug)
        try:
            v = float(m.group("value"))
        except ValueError:
            v = None
        else:
            suffix = m.group("suffix").lower()
            v *= 1_000_000 if suffix == "m" else 1_000 if suffix == "k" else 1.0
        # Look back ~2 kB for the row's position cell and ~1 kB ahead for any
        # injury / suspension keyword. The lookback distance covers the full
        # row plus the previous one's trailing markup without crossing into
        # another player record.
        back = html[max(0, m.start() - 2000): m.start()]
        ahead = html[m.end(): m.end() + 1000]
        pos_match = None
        for pm in POSITION_RE.finditer(back):
            pos_match = pm     # take the *last* position match in the lookback
        position = pos_match.group(1) if pos_match else ""
        note = None
        inj = INJURY_NOTE_RE.search(ahead)
        if inj:
            kw = inj.group(1).lower()
            note = ("out" if kw in ("injured", "out", "suspension", "suspended")
                    else "doubtful")
        name = " ".join(w.capitalize() for w in slug.split("-"))
        out.append(SquadEntry(
            name=name,
            position=position,
            market_value_eur=v,
            injury_note=note,
        ))
    return out


def try_fetch(url: str) -> list[SquadEntry]:
    """Best-effort wrapper: return an empty list on any network / parse
    failure rather than raising. Useful for batch scripts."""
    try:
        html = fetch_team_page(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return []
    return parse_squad(html)
