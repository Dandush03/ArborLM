# ruff: noqa: E501
"""The supplementary throughput measurement of ADR-0021 section 25.21: which configurations it measures and which it skips. Nothing here loads a snapshot, a backbone or a registered seed."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10s1 import core, stages, throughput_supplement  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def frozen() -> fz.Frozen:
    return fz.Frozen.from_json(json.loads((REPO / stages.FREEZE_PLAN).read_text())["frozen"])


def test_the_frozen_plan_measures_fifteen_configurations_and_skips_the_cell_that_was_not_run() -> None:
    measured, skipped = throughput_supplement.select(frozen())
    assert len(measured) == 15
    assert [(s["arm"], s["facts"], s["slots"]) for s in skipped] == [("F-OQ", *core.SATURATION_ONLY_CELL)]
    assert all(cell.kind == "P" and cell.draw == 1 for _, cell in measured)
    assert sorted({arm for arm, _ in measured}) == sorted(throughput_supplement.ARMS)
    assert all(cell.arm == ("F-OQ" if arm == "F-OQ-IVF" else arm) for arm, cell in measured)


def test_a_plan_that_runs_the_256_slot_cell_skips_nothing() -> None:
    fro = frozen()
    with_256 = dataclasses.replace(fro, plan=dataclasses.replace(fro.plan, sat256=True))
    measured, skipped = throughput_supplement.select(with_256)
    assert skipped == [] and len(measured) == 16


def test_the_record_is_refused_inside_the_run_directory(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    assert throughput_supplement.main(["--run-dir", str(run), "--out", str(run / "supplement")]) == 2
