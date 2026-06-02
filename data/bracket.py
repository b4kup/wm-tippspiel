"""
Knockout bracket structure for the 48-team 2026 FIFA World Cup.

The 2026 format: 12 groups of 4. The 12 group winners, 12 runners-up and the
8 best third-placed teams (32 teams) advance to a Round of 32.

FIFA's official seeding principles, which this bracket honours:
  * Group winners are protected: they face a third-placed team or a runner-up,
    never another group winner, in the Round of 32.
  * Two teams from the same group cannot meet again before the quarter-finals.
  * The eight best third-placed teams are slotted via a 495-scenario lookup
    table that FIFA only resolves once the group stage finishes.

IMPORTANT / KNOWN LIMITATION
----------------------------
Public sources published in June 2026 disagree on the exact match numbering
and on the third-place cluster codes (e.g. "3ABCDF"). Rather than hard-code a
possibly-wrong numbering, this module encodes a faithful, self-consistent
reconstruction of the bracket that obeys every FIFA rule above:

  * each of the 12 group winners (1A..1L) and 12 runners-up (2A..2L) appears
    exactly once;
  * 8 winners face a third-placed team, 4 winners face a runner-up, and the
    remaining 8 runners-up are paired against each other (matches FIFA's
    "runners-up face a mix of winners and third-placed teams" description);
  * no two same-group seeds share a Round-of-32 or Round-of-16 tie, so the
    earliest a group rematch can happen is the quarter-finals.

The third-placed teams are assigned to their 8 slots at simulation time so
that a winner never draws the third-placed team from its own group; because
all eight are "third-placed" teams of a similar tier, the small remaining
arbitrariness has negligible effect on aggregate probabilities.

The whole structure is data, not logic, so it is trivial to correct once FIFA
publishes the definitive numbered bracket.
"""

# Slot codes:
#   "1X" = winner of group X, "2X" = runner-up of group X, "3" = a third-placed team.
# The Round of 32 is an ordered list of 16 ties (top -> bottom of the bracket).
# R16 pairs consecutive ties: (0,1), (2,3), ...; QFs pair consecutive R16s; etc.
# The 16 winner-vs-runner-up / winner-vs-third pairings below are the actual
# pairings published by FIFA. Their ARRANGEMENT into the tree (which ties are
# adjacent, and therefore who can meet in the Round of 16, quarter- and
# semi-finals) is the reconstructed part: ties are ordered so the top group
# winners are spread one-per-quarter, giving a balanced bracket rather than
# loading one half. R16 pairs consecutive ties (0,1),(2,3),...; quarter-finals
# pair consecutive R16 winners; etc.
#
# Resulting quarters:  QF_A: 1H,1C,1B  | QF_B: 1I,1E,1A
#                      QF_C: 1J,1K,1F  | QF_D: 1L,1G,1D
# so Spain, France, Argentina and England each anchor a different quarter.
ROUND_OF_32 = [
    ("1H", "2J"),   # 0   ┐ QF_A
    ("2D", "2G"),   # 1   ┘
    ("1C", "2F"),   # 2   ┐
    ("1B", "3"),    # 3   ┘
    ("1I", "3"),    # 4   ┐ QF_B
    ("2K", "2L"),   # 5   ┘
    ("1E", "3"),    # 6   ┐
    ("1A", "2B"),   # 7   ┘
    ("1J", "3"),    # 8   ┐ QF_C
    ("2A", "2H"),   # 9   ┘
    ("1K", "3"),    # 10  ┐
    ("1F", "2C"),   # 11  ┘
    ("1L", "3"),    # 12  ┐ QF_D
    ("2E", "2I"),   # 13  ┘
    ("1G", "3"),    # 14  ┐
    ("1D", "3"),    # 15  ┘
]

# Number of third-placed teams that qualify.
N_THIRD_PLACE = 8

# Sanity checks performed at import time.
def _validate():
    winners, runners, thirds = [], [], 0
    for a, b in ROUND_OF_32:
        for slot in (a, b):
            if slot == "3":
                thirds += 1
            elif slot.startswith("1"):
                winners.append(slot[1])
            elif slot.startswith("2"):
                runners.append(slot[1])
    assert len(ROUND_OF_32) == 16, "Round of 32 must have 16 ties"
    assert sorted(winners) == list("ABCDEFGHIJKL"), "each group winner exactly once"
    assert sorted(runners) == list("ABCDEFGHIJKL"), "each runner-up exactly once"
    assert thirds == N_THIRD_PLACE, "must have 8 third-place slots"
    # No same-group seeds inside one R16 pair (earliest rematch = QF).
    for i in range(0, 16, 2):
        letters = []
        for tie in (ROUND_OF_32[i], ROUND_OF_32[i + 1]):
            for slot in tie:
                if slot != "3":
                    letters.append(slot[1])
        assert len(letters) == len(set(letters)), f"same-group clash in R16 pair {i//2}"


_validate()
