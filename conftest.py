# ruff: noqa: E501
"""Repository-level pytest hooks (new file, 2026-11-18; edits no existing test).

P10-I-R's tests were frozen with the study (freeze commit c712a90). Nine of them assert that nothing is frozen yet ("refuses today"). They held until the freeze and are false by construction since: the plan, the freeze record and Decision 2 now exist. The frozen test file is not edited; the nine are marked as strict expected failures here, so the suite reports them as xfailed and turns red again if one of them ever passes (which would mean the freeze files are missing).
"""

from __future__ import annotations

import pytest

_P10IR_STALE_AFTER_FREEZE = (
    "tests/test_p10ir_stages.py::test_every_registered_stage_refuses_today",
    "tests/test_p10ir_stages.py::test_freeze_and_candidate_plan_refuse_in_this_repository_today",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if item.nodeid.split("[")[0] in _P10IR_STALE_AFTER_FREEZE:
            item.add_marker(pytest.mark.xfail(strict=True, reason="P10-I-R is frozen and executed (c712a90): the 'refuses today' assertion is stale by construction"))
