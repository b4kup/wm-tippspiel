"""
Deterministic scraper for Wikipedia match tables (`footballbox` template).

Why a scraper instead of an LLM agent
-------------------------------------
Wikipedia renders match results inside a fixed CSS template with stable
class names:

    <table class="footballbox" itemtype="...SportsEvent">
      <div class="fdate">June 20, 2024</div>
      ...
      <th class="fhome"><a href="...">Argentina</a></th>
      <th class="fscore">2–0</th>
      <th class="faway"><a href="...">Canada</a></th>
      ...
    </table>

Plain stdlib `urllib` + a few regexes parse that structure in
milliseconds. An LLM agent would re-read the same HTML, re-derive the
same pattern every time, and occasionally hallucinate scores. Reserve
agents for genuinely ambiguous parsing; here, code is faster, cheaper,
and exact.

Output: a list of `Match` records with date, home, away, goals, and an
optional knockout/extra-time/penalties tag pulled from the score string.
"""

from __future__ import annotations

import csv
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict

USER_AGENT = "wm-tippspiel-scraper/1.0 (educational; python-urllib)"
WIKI_BASE = "https://en.wikipedia.org/wiki/"
FETCH_DELAY_S = 0.5     # be nice to Wikipedia


@dataclass(frozen=True)
class Match:
    date: str           # YYYY-MM-DD where possible
    home: str
    away: str
    goals_home: int     # at full time (90' for KO, includes 90' result only)
    goals_away: int
    tournament: str     # e.g. "Copa America 2024"
    et_or_pen: str      # "ET", "PEN:X-Y", or "" — tracked but not summed


def fetch(url: str, retries: int = 2) -> str:
    """Fetch one URL. Returns the body; on 404 returns an empty string so the
    caller can skip a missing tournament page rather than fail the whole run."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            last_err = e
            time.sleep(1.0)
        except Exception as e:
            last_err = e
            time.sleep(1.0)
    raise RuntimeError(f"fetch failed for {url}: {last_err}")


# --- HTML parsing ----------------------------------------------------------

_DATE_PATS = [
    # "June 20, 2024" / "20 June 2024"
    re.compile(r"(\w+)\s+(\d{1,2}),\s+(\d{4})"),
    re.compile(r"(\d{1,2})\s+(\w+)\s+(\d{4})"),
]
_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def _iso_date(date_text: str) -> str:
    """Convert "June 20, 2024" or "20 June 2024" to "2024-06-20"; on
    failure return the raw text."""
    if not date_text:
        return ""
    # Prefer the machine-readable <span class="bday"> embedded by Wikipedia.
    bday = re.search(r'class="bday[^"]*"[^>]*>(\d{4}-\d{2}-\d{2})', date_text)
    if bday:
        return bday.group(1)
    plain = re.sub(r"<[^>]+>", "", date_text).strip()
    for pat in _DATE_PATS:
        m = pat.search(plain)
        if m:
            g = m.groups()
            if g[0].isalpha():
                month_name, day, year = g
            else:
                day, month_name, year = g
            month = _MONTHS.get(month_name.capitalize())
            if month:
                return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    return plain


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def _team_name(cell_html: str) -> str:
    """Pull the (linked) team name out of a `fhome`/`faway` cell."""
    # First <a> inside is the team article link.
    m = re.search(r"<a[^>]*>([^<]+)</a>", cell_html)
    if m:
        return m.group(1).strip()
    return _strip_tags(cell_html)


_FBOX_START = re.compile(r'class="footballbox"')
_FHOME = re.compile(r'<th class="fhome"[^>]*>(.*?)</th>', re.DOTALL)
_FSCORE = re.compile(r'<th class="fscore"[^>]*>([^<]+)</th>')
_FAWAY = re.compile(r'<th class="faway"[^>]*>(.*?)</th>', re.DOTALL)
_FDATE = re.compile(r'class="fdate"[^>]*>(.*?)</div>', re.DOTALL)
_SCORE_GOALS = re.compile(r"\s*(\d+)\s*[–\-]\s*(\d+)\s*(.*)$")
_PEN_TAG = re.compile(r"\((\d+)\s*[–\-]\s*(\d+)\s*p\.?\)", re.IGNORECASE)


def parse_footballboxes(html: str, tournament: str) -> list[Match]:
    """Extract every football-box match from one rendered Wikipedia page."""
    out: list[Match] = []
    starts = [m.start() for m in _FBOX_START.finditer(html)]
    starts.append(len(html))
    for i in range(len(starts) - 1):
        chunk = html[starts[i]:starts[i + 1]]
        h = _FHOME.search(chunk)
        s = _FSCORE.search(chunk)
        a = _FAWAY.search(chunk)
        if not (h and s and a):
            continue
        d = _FDATE.search(chunk)
        score_text = s.group(1).replace("&#8211;", "–").replace("&ndash;", "–")
        gm = _SCORE_GOALS.match(score_text)
        if not gm:
            continue
        gh, ga, tail = int(gm.group(1)), int(gm.group(2)), gm.group(3)
        et_or_pen = ""
        pen = _PEN_TAG.search(tail)
        if pen:
            et_or_pen = f"PEN:{pen.group(1)}-{pen.group(2)}"
        elif "a.e.t" in tail.lower() or "extra" in tail.lower():
            et_or_pen = "ET"
        out.append(Match(
            date=_iso_date(d.group(1)) if d else "",
            home=_team_name(h.group(1)),
            away=_team_name(a.group(1)),
            goals_home=gh,
            goals_away=ga,
            tournament=tournament,
            et_or_pen=et_or_pen,
        ))
    return out


# --- Public entry point ----------------------------------------------------

def scrape_pages(specs: list[tuple[str, str]]) -> list[Match]:
    """Scrape each (tournament_label, wikipedia_slug) pair and merge.

    `wikipedia_slug` is the URL fragment after `/wiki/` (URL-encoded if
    needed — pass the actual slug like `2024_Copa_Am%C3%A9rica_Group_A`).
    """
    all_matches: list[Match] = []
    for label, slug in specs:
        url = WIKI_BASE + slug
        html = fetch(url)
        if not html:
            print(f"  [skip] {slug} (404)")
            continue
        matches = parse_footballboxes(html, tournament=label)
        if matches:
            print(f"  [ok]   {slug}  → {len(matches)} matches")
        else:
            print(f"  [empty] {slug} (no football boxes found)")
        all_matches.extend(matches)
        time.sleep(FETCH_DELAY_S)
    # De-duplicate (same teams + score + date)
    seen = set()
    dedup = []
    for m in all_matches:
        key = (m.date, m.home, m.away, m.goals_home, m.goals_away)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(m)
    return dedup


def write_csv(matches: list[Match], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "home", "away", "goals_home", "goals_away",
                    "tournament", "et_or_pen"])
        for m in matches:
            w.writerow([m.date, m.home, m.away, m.goals_home, m.goals_away,
                        m.tournament, m.et_or_pen])
