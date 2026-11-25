# ruff: noqa: E501
"""Ruling 40: the measuring rehearsal's cumulative cap is raised once, from 3.0 h to 6.0 h (docs/decisions/ADR-0025-addendum-part-t-rulings-9.md). Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is2 import partt_tasks  # noqa: E402
from studies.p10is2.common import core  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config("T")
ORIGINAL_HOURS = 3.0  # ADR-0025 section 10


def test_the_measuring_cap_is_the_one_extension_to_twice_the_original_and_no_more() -> None:
    c = CFG["caps"]
    assert float(c["measuring_rehearsal_hours"]) == 6.0 == float(c["extension_factor_max"]) * ORIGINAL_HOURS  # the most extension_factor_max allows
    assert partt_tasks.rehearsal_cap_seconds(CFG, "measuring") == 6.0 * 3600.0
    assert float(c["rehearsal_hours"]) == ORIGINAL_HOURS  # the counting rehearsal's fallback figure is untouched (its cap is its own allowance, ruling 30)


def test_the_ruling_file_records_what_happened_the_numbers_and_the_limits() -> None:
    text = (ROOT / "docs/decisions/ADR-0025-addendum-part-t-rulings-9.md").read_text()
    for must in ("P10IS2-T-measuring2-20261120", "P10IS2-T-measuring3-20261120", "2,355 s", "10,800 s", "10,801 s", "3.95 h", "raised once, from 3.0 h to 6.0 h", "does not track", "no further extension", "No rate, score or governed value was read", "Astra review: NOT_PERFORMED", "progress records"):
        assert must in text, must
