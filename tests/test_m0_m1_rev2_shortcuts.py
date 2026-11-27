# ruff: noqa: E501
"""M1 rev2, shortcuts by construction (R-1, R-3): the combined battery (author's and the independent auditor's heuristics, copied with attribution into m1_shortcut_check_rev2.py) is measured per level on
the revised shapes. Display screen (not a registered threshold): rate >= max(0.25, 2 x the most-frequent-answer rate). The batch-1 shapes named by the audit are flagged by the same measurement."""

from __future__ import annotations

from studies.m0.lineages_m1_rev2 import NOT_REGISTERED, load_rev2
from studies.m0.m1_shortcut_check_rev2 import measure_lineage, summarise

N = 400
MARGIN = 0.05  # sampling noise at N = 400 (one s.d. is about 0.02)


def _flags(which: str, lid: str) -> list[int]:
    return summarise(dict([measure_lineage((which, lid, N))]))[lid]["flagged_levels"]


def test_batch1_shapes_named_by_the_audit_are_flagged_on_this_battery() -> None:
    for lid in ("M1.min_cost_packs", "M1.mode_tally", "M1.last_digit_power"):
        assert _flags("batch1", lid), lid


def test_every_registered_revised_shape_stays_under_the_screen_at_every_level() -> None:
    for lin in load_rev2():
        if lin.id in NOT_REGISTERED:
            continue
        res = dict([measure_lineage(("rev2", lin.id, N))])[lin.id]
        for lv, r in res.items():
            surf = {k: v for k, v in r["rates"].items() if not k.startswith("oracle")}
            from studies.m0.m1_shortcut_check_rev2 import _tag

            surf = {k: v for k, v in surf.items() if not _tag(k, lin.id)}
            worst = max(surf, key=lambda k: surf[k])
            assert surf[worst] < max(0.25, 2 * r["const_rate"]) + MARGIN, (lin.id, lv, worst, surf[worst], r["const_rate"])


def test_not_registered_shape_is_flagged_and_carries_its_reason() -> None:
    assert set(NOT_REGISTERED) == {"M1.min_cost_packs_r2"}
    assert _flags("rev2", "M1.min_cost_packs_r2") == [0, 1, 2, 3, 4, 5, 6]
    assert len(NOT_REGISTERED["M1.min_cost_packs_r2"]) > 100
