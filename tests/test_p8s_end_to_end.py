"""ADR-0016 gate 4: a synthetic single-set cell simulates end to end and meets predictions 1-3
(and the other record-level predictions), flat and tree; the worker enforces its identity checks."""

import sys
from functools import cache
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tempfile  # noqa: E402

import pytest  # noqa: E402

from arborlm import p8_analysis as an  # noqa: E402
from arborlm import p8_core as core  # noqa: E402
from arborlm.io import read_json, write_json  # noqa: E402
from arborlm.p7a_trace import configure_deterministic_cpu  # noqa: E402
from supplements.p8s import (  # noqa: E402
    analysis,
    common,
    null,
    synthetic,  # noqa: E402
)
from supplements.p8s import sim as ssim  # noqa: E402

LABELS = {"flat": "b101-o301-s601-C04", "tree": "b102-o302-s601-C05"}


@cache
def _cell(which: str) -> tuple[Path, Path, dict[str, Any], core.Cell]:
    configure_deterministic_cpu()
    root = Path(tempfile.mkdtemp(prefix="p8s-e2e-"))
    cell = core.parse_label(LABELS[which])
    eval_dir = synthetic.write_single_set_cell(root / "eval", cell)
    out_dir = root / "sim" / cell.label
    out_dir.mkdir(parents=True)
    record = ssim.simulate_cell_s(cell, eval_dir, out_dir, null.supplement_null_provider)
    return eval_dir, out_dir, record, cell


def _cells(which: str) -> dict[str, an.CellData]:
    eval_dir, _, record, cell = _cell(which)
    return {cell.label: an.CellData(cell, read_json(eval_dir / "eval.json"), record)}


@pytest.fixture(params=["flat", "tree"])
def which(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def test_identity_null_used_on_both_panels(which: str) -> None:
    _, _, record, _ = _cell(which)
    for panel in ("A", "B"):
        entries = record["panels"][panel]["null_streams"]
        assert {e["method"] for e in entries} == {"single-set identity null (ADR-0016 §3)"}
        assert all(e["precondition"] is True for e in entries)
        assert len({e["stream_sha256"] for e in entries}) == 1  # prediction 7
        assert record["supplement_null_preconditions"][panel]["holds"] is True
        assert record["supplement_null_preconditions"][panel]["nonzero_slots"] == 8


@pytest.mark.parametrize("name", ["pred_1", "pred_2", "pred_3", "pred_4", "pred_6", "pred_7"])
def test_record_level_predictions_hold(which: str, name: str) -> None:
    cells = _cells(which)
    result = getattr(analysis, name)(cells, tuple(cells))
    assert result["holds"], result
    assert result["checked"] > 0


def test_counts_are_exactly_zero_misses_and_eight_pages(which: str) -> None:
    _, _, record, _ = _cell(which)
    actual = record["panels"]["A"]["streams"]["actual"]
    assert actual  # every layout of the plan is present
    for group in actual.values():
        assert group["stats"]["distinct_stream"] <= 8
        for ties in group["by_c"].values():
            for counts in ties.values():
                assert counts["misses_warm"] == 0 and counts["first_touch_warm"] == 0
    assert record["panels"]["A"]["temporal_reuse"]["actual"]["value"] == 1.0


def test_layout_file_is_built_from_calibration_and_hashed(which: str) -> None:
    _, out_dir, record, _ = _cell(which)
    assert record["layouts"]["meta"]["unique_selected_slots"] == 8
    assert record["layouts"]["meta"]["built_from"].startswith("calibration")
    from arborlm.io import file_sha256

    assert file_sha256(out_dir / "layouts.int16.bin") == record["layouts"]["file_sha256"]


def test_worker_writes_record_with_supplement_identity(tmp_path: Path) -> None:
    if not common.commit_available(common.ROOT, common.FREEZE_COMMIT):
        pytest.skip("freeze commit not available in this clone (shallow checkout)")
    configure_deterministic_cpu()
    cell = core.parse_label(LABELS["flat"])
    eval_dir = synthetic.write_single_set_cell(tmp_path / "eval", cell)
    job = {
        "label": cell.label,
        "eval_cell_dir": str(eval_dir),
        "out_dir": str(tmp_path / "out"),
        "stage_deadline_epoch": 4e9,
        "supplement_spec_sha256": common.supplement_spec_sha256(),
        "supplement_source_sha256": common.supplement_source_digest(),
        "supplement_freeze_commit": {"commit": "c" * 40, "tree": "d" * 40},
    }
    write_json(tmp_path / "job.json", job)
    assert ssim.worker_main(tmp_path / "job.json") == 0
    rec = read_json(tmp_path / "out" / "sim.json")
    assert rec["supplement"] == "ADR-0016" and rec["dry_run"] is False
    assert rec["supplement_spec_sha256"] == common.supplement_spec_sha256()
    assert rec["supplement_source_sha256"] == common.supplement_source_digest()
    assert rec["supplement_freeze_commit"] == {"commit": "c" * 40, "tree": "d" * 40}
    assert rec["frozen_inputs"]["source_sha256"] == common.FROZEN_SOURCE_DIGEST
    assert rec["frozen_inputs"]["freeze_tree"] == common.FREEZE_TREE
    assert rec["source_sha256"] == core.source_digest() == common.FROZEN_SOURCE_DIGEST
    # no registered identity is claimed as the producer's own
    assert "spec_sha256" not in rec and "reproduction_record_sha256" not in rec
    assert "freeze" not in rec and "supplement_freeze_commit" in rec


def test_worker_refuses_changed_identity_and_other_cells(tmp_path: Path) -> None:
    base = {
        "label": LABELS["flat"],
        "eval_cell_dir": str(tmp_path),
        "out_dir": str(tmp_path / "o"),
        "stage_deadline_epoch": 4e9,
        "supplement_spec_sha256": common.supplement_spec_sha256(),
        "supplement_source_sha256": common.supplement_source_digest(),
        "supplement_freeze_commit": None,
    }
    for patch in (
        {"supplement_spec_sha256": "0" * 64},
        {"supplement_source_sha256": "0" * 64},
        {"label": "b101-o301-s601-C06"},  # not one of the five
    ):
        write_json(tmp_path / "job.json", {**base, **patch})
        with pytest.raises(common.SupplementError):
            ssim.worker_main(tmp_path / "job.json")
