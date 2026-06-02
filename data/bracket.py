"""
Knockout bracket structure for the 48-team 2026 FIFA World Cup.

This is the **official** bracket (match numbers W73-W104, third-place cluster
codes, and the full tree), transcribed from FIFA's published draw. The 12 group
winners, 12 runners-up and the 8 best third-placed teams (32 teams) play a
Round of 32, then a straight knockout to the final.

Representation
--------------
`ROUND_OF_32` is the 16 ties in *bracket order*, top to bottom, so that pairing
consecutive ties reproduces the real tree: ties (0,1) meet in the Round of 16,
(2,3) next, ...; consecutive R16 winners meet in the quarter-finals; etc.

Slot codes:
    "1X"     winner of group X
    "2X"     runner-up of group X
    "3:WXYZ" one of the 8 best third-placed teams, restricted to the groups in
             the code (FIFA's cluster for that slot). The specific third that
             lands here depends on which 8 groups qualify a third-placed team;
             we resolve it at simulation time by a constrained matching that
             respects every slot's allowed groups (see
             src/tournament.assign_thirds_to_slots).

Real tree (for reference):
    R16: W89=74/77 W90=73/75 W91=76/78 W92=79/80
         W93=83/84 W94=81/82 W95=86/88 W96=85/87
    QF:  W97=89/90 W98=93/94 W99=91/92 W100=95/96
    SF:  W101=97/98  W102=99/100        Final: 101/102
"""

# (slot_a, slot_b) per tie, in bracket order. The comment gives the official
# match number and host city.
ROUND_OF_32 = [
    ("1E", "3:ABCDF"),   # W74  Boston
    ("1I", "3:CDFGH"),   # W77  New York
    ("2A", "2B"),        # W73  Los Angeles
    ("1F", "2C"),        # W75  Monterrey
    ("2K", "2L"),        # W83  Toronto
    ("1H", "2J"),        # W84  Los Angeles
    ("1D", "3:BEFIJ"),   # W81  San Francisco
    ("1G", "3:AEHIJ"),   # W82  Seattle
    ("1C", "2F"),        # W76  Houston
    ("2E", "2I"),        # W78  Dallas
    ("1A", "3:CEFHI"),   # W79  Mexico City
    ("1L", "3:EHIJK"),   # W80  Atlanta
    ("1J", "2H"),        # W86  Miami
    ("2D", "2G"),        # W88  Dallas
    ("1B", "3:EFGIJ"),   # W85  Vancouver
    ("1K", "3:DEIJL"),   # W87  Kansas City
]

# Number of third-placed teams that qualify.
N_THIRD_PLACE = 8


def is_third(slot) -> bool:
    return isinstance(slot, str) and slot.startswith("3")


def third_allowed_groups(slot) -> set:
    """Groups whose third-placed team may fill this slot (e.g. '3:ABCDF')."""
    return set(slot.split(":", 1)[1])


def _validate():
    winners, runners, thirds = [], [], 0
    for tie in ROUND_OF_32:
        for slot in tie:
            if is_third(slot):
                thirds += 1
                # A slot never admits its tie-mate winner's own group.
                assert tie[0][0] == "1"
                assert tie[0][1] not in third_allowed_groups(slot)
            elif slot[0] == "1":
                winners.append(slot[1])
            elif slot[0] == "2":
                runners.append(slot[1])
    assert len(ROUND_OF_32) == 16, "Round of 32 must have 16 ties"
    assert sorted(winners) == list("ABCDEFGHIJKL"), "each group winner exactly once"
    assert sorted(runners) == list("ABCDEFGHIJKL"), "each runner-up exactly once"
    assert thirds == N_THIRD_PLACE, "must have 8 third-place slots"
    # No two same-group seeds (winner/runner) inside one R16 pair.
    for i in range(0, 16, 2):
        letters = [s[1] for tie in (ROUND_OF_32[i], ROUND_OF_32[i + 1])
                   for s in tie if not is_third(s)]
        assert len(letters) == len(set(letters)), f"same-group clash in R16 pair {i//2}"


_validate()
