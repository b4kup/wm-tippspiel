"""
Tip-change notifications.

When new results re-tune the model and shift the EV-optimal recommendation for
a not-yet-played group match, this records a notification
(``data/notifications.json``) and — when ``auto_update`` is on — syncs the
frozen tip in ``data/our_tips.csv`` to the new recommendation.

A small state file (``data/tip_state.json``) holds the last-known
recommendation per match plus the set of results already seen, so diffs are
computed against the *previous run's recommendation*, not against a
manually-set tip. That way a tip you deliberately kept off the model's pick
isn't re-flagged every run — only an actual change in the recommendation,
triggered by fresh results, raises a notification.

Recommendations are always computed under the *safe* (pure-EV) risk mode so
the alert stream is stable regardless of how the live report is run.
"""

from __future__ import annotations

import json
import os
from datetime import date

from .liveupdate import load_our_tips, save_our_tips
from .results import GROUP, Results

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
NOTIF_PATH = os.path.join(DATA_DIR, "notifications.json")
STATE_PATH = os.path.join(DATA_DIR, "tip_state.json")


def _key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _result_keys(results: Results) -> dict:
    """key -> (goals_a, goals_b, team_a, team_b) for every played group match."""
    return {_key(r.team_a, r.team_b): (r.goals_a, r.goals_b, r.team_a, r.team_b)
            for r in results.group_results()}


def _fmt_result(meta) -> str:
    ga, gb, a, b = meta
    return f"{a} {ga}–{gb} {b}"


def sync_and_notify(remaining, our_tips_path, results: Results, *,
                    group_of, auto_update=True, today=None,
                    notif_path=NOTIF_PATH, state_path=STATE_PATH):
    """Diff the current recommendations against the previous run, log changes.

    ``remaining``: iterable of ``(a_name, b_name, tip_tuple, probs)`` for the
    not-yet-played group matches, computed on re-tuned ratings under safe risk.
    ``group_of``: mapping team name -> group letter.

    Returns the list of new notification dicts (also appended to
    ``notifications.json``). On the very first run (no prior state) it just
    records the baseline and returns ``[]`` so the feed doesn't fill with
    pre-tournament noise.
    """
    today = today or date.today().isoformat()

    # Current recommendation per match, oriented to canonical (sorted) order.
    current: dict[str, list[int]] = {}
    for a, b, tip, _probs in remaining:
        a2, b2 = sorted((a, b))
        current[_key(a, b)] = [tip[0], tip[1]] if (a, b) == (a2, b2) \
            else [tip[1], tip[0]]

    state = _load_json(state_path, {})
    prev_tips = state.get("tips", {})
    prev_results = set(state.get("result_keys", []))
    cur_results = _result_keys(results)
    new_result_keys = [k for k in cur_results if k not in prev_results]
    trigger = [_fmt_result(cur_results[k]) for k in new_result_keys]

    added = []
    changed_keys = set()
    if prev_tips:  # skip first-run baseline — no spam
        for k, newtip in sorted(current.items()):
            oldtip = prev_tips.get(k)
            if oldtip is not None and list(oldtip) != newtip:
                a2, b2 = k.split("|")
                changed_keys.add(k)
                added.append({
                    "ts":      today,
                    "match":   f"{a2} – {b2}",
                    "group":   group_of.get(a2, "?"),
                    "old":     list(oldtip),
                    "new":     newtip,
                    "trigger": trigger,
                })

    if added:
        notifs = _load_json(notif_path, [])
        notifs.extend(added)
        _save_json(notif_path, notifs)

    if auto_update and changed_keys:
        _apply_to_our_tips(our_tips_path, current, changed_keys)

    _save_json(state_path, {
        "updated":     today,
        "result_keys": sorted(cur_results),
        "tips":        current,
    })
    return added


def _apply_to_our_tips(path, current, changed_keys):
    """Overwrite the frozen tip for each changed (unplayed) match, preserving
    each row's own team order."""
    rows = load_our_tips(path)
    out = []
    for stage, a, b, ta, tb in rows:
        k = _key(a, b)
        if stage == GROUP and k in changed_keys:
            ctip = current[k]                     # oriented to sorted(a, b)
            a2, b2 = sorted((a, b))
            ta, tb = (ctip[0], ctip[1]) if (a, b) == (a2, b2) \
                else (ctip[1], ctip[0])
        out.append((stage, a, b, ta, tb))
    save_our_tips(path, out)


def load_notifications(path=NOTIF_PATH) -> list:
    """Notification feed, newest first, for the dashboard."""
    return list(reversed(_load_json(path, [])))
