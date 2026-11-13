"""Offline P2 runner and checkpoint tests; no registered data are consumed."""

from pathlib import Path

import pytest
import torch

from arborlm.io import file_sha256, write_json
from arborlm.optimization_followup import (
    CELL_EXPORT,
    _diagnostics,
    _export,
    _optimizer,
    _status,
    _summary,
    _training_step,
)
from arborlm.p2_analysis import describe
from arborlm.p2_checkpoint import restore, save
from arborlm.p2_config import CONTROL, LEARNED, Cell, cells, load_config, validate_config
from arborlm.p2_data import order_ids
from arborlm.p2_model import FollowupModel
from arborlm.pilot_metrics import evaluate

ROOT = Path(__file__).resolve().parents[1]


def test_registry_and_strict_config() -> None:
    grid = cells()
    assert len(grid) == 36 and len(set(grid)) == 36
    assert [cell.index for cell in grid if cell.condition == LEARNED] == list(range(27))
    assert all(grid[i].condition == CONTROL for i in range(0, 36, 4))
    config = load_config(ROOT / "configs" / "p2_optimization_followup.toml")
    config["data"]["validation_rank_interval"] = [0, 512]
    with pytest.raises(ValueError, match="validation_rank_interval"):
        validate_config(config)


def _synthetic_batches() -> torch.Tensor:
    generator = torch.Generator().manual_seed(431)
    return torch.randint(0, 256, (2048, 3), generator=generator)[order_ids(301)]


@pytest.mark.parametrize("condition", (CONTROL, LEARNED))
def test_checkpoint_resume_and_reject_corruption(tmp_path: Path, condition: str) -> None:
    cell = Cell(101, 201, 301, condition)
    identity = {"cell": cell.fields(), "fixture": "synthetic"}
    batches = _synthetic_batches()
    model = FollowupModel(cell)
    optimizer = _optimizer(model)
    for step in range(1, 129):
        left = (step - 1) * 8
        _training_step(model, optimizer, batches[left : left + 8], step)
    path = tmp_path / "checkpoint-128"
    digest = save(path, model, optimizer, 128, identity)
    assert digest == file_sha256(path / "state.pt")
    resume = FollowupModel(cell)
    other = _optimizer(resume)
    with pytest.raises(ValueError, match="identity mismatch"):
        restore(path, resume, other, {**identity, "fixture": "mismatch"})
    assert restore(path, resume, other, identity) == (128, 1024, 65536)
    for step in range(129, 132):
        left = (step - 1) * 8
        a = _training_step(model, optimizer, batches[left : left + 8], step)
        b = _training_step(resume, other, batches[left : left + 8], step)
        assert a == b
    assert all(
        torch.equal(tensor, resume.state_dict()[name])
        for name, tensor in model.state_dict().items()
    )
    for key, state in optimizer.state_dict()["state"].items():
        assert all(
            torch.equal(tensor, other.state_dict()["state"][key][name])
            for name, tensor in state.items()
        )
    (path / "state.pt").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        restore(path, resume, other, identity)


@pytest.mark.parametrize("condition", (CONTROL, LEARNED))
def test_interventions_restore_fresh_and_preserve_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
) -> None:
    cell = Cell(102, 201, 302, condition)
    identity = {"cell": cell.fields(), "fixture": "synthetic"}
    batch = _synthetic_batches()[:8]
    model = FollowupModel(cell)
    optimizer = _optimizer(model)
    _training_step(model, optimizer, batch, 1)
    # Serialization fixture: model sees only eight rows; metadata marks a final snapshot.
    for state in optimizer.state.values():
        state["step"].fill_(256)
    path = tmp_path / "checkpoint-256"
    digest = save(path, model, optimizer, 256, identity)
    index = file_sha256(path / "index.json")
    final = evaluate(model, batch)
    monkeypatch.setattr("arborlm.optimization_followup.VAL_TARGETS", 16)
    evidence = _diagnostics(tmp_path, cell, path, digest, identity, batch, final)
    assert evidence["enabled"]["nll"] == final["nll"]
    assert evidence["enabled"]["invariance_passed"]
    if condition == CONTROL:
        assert set(evidence) == {"enabled"}
    else:
        assert evidence["joint_within_branch"]["invariance_passed"]
        assert evidence["disabled"]["retrieval"] is None
        for name in ("values_permuted", "joint_within_branch"):
            recorded = evidence[name]["permutation"]
            assert file_sha256(tmp_path / recorded["file"]) == recorded["sha256"]
    assert file_sha256(path / "state.pt") == digest
    assert file_sha256(path / "index.json") == index


def test_compact_allowlist_and_failure_cells(tmp_path: Path) -> None:
    raw, export = tmp_path / "raw", tmp_path / "export"
    raw.mkdir()
    (raw / "checkpoint-128").mkdir()
    (raw / "checkpoint-128" / "index.json").write_text("{}")
    (raw / "checkpoint-128" / "state.pt").write_bytes(b"weights")
    (raw / "metrics.jsonl").write_text("{}\n")
    (raw / "train.bytes").write_bytes(b"corpus")
    _export(raw, export, CELL_EXPORT)
    assert set(export.iterdir()) == {export / "checkpoint-128", export / "metrics.jsonl"}
    assert list((export / "checkpoint-128").iterdir()) == [export / "checkpoint-128" / "index.json"]
    with pytest.raises(FileExistsError):
        _export(raw, export, CELL_EXPORT)
    status = _status()
    status[0].update(status="running", run_id="synthetic")
    write_json(raw / "cells.json", status)
    result = _summary(raw, "fixture failure")
    assert result["outcome"] == "failed"
    assert result["cells"][0]["status"] == "interrupted"
    assert all(cell["status"] == "unexecuted" for cell in result["cells"][1:])


def test_prespecified_analysis_flags_overlap() -> None:
    rows = []
    for cell in cells():
        if cell.condition == CONTROL:
            continue
        index = cell.index
        # 24 cells show useful dependence and 3 show the opposite; both flags can hold.
        effect = -0.01 if index < 3 else 0.02
        rows.append(
            {
                **cell.fields(),
                "enabled": 2.0,
                "disabled": 2.0 + effect,
                "values_permuted": 2.0 + effect,
                "joint_within_branch": 2.0,
                "control": 2.01,
            }
        )
    report = describe(rows)
    assert report["flags"]["consistent_dependence"]
    assert report["flags"]["heterogeneous_useful_dependence"]
    assert report["flags"]["consistent_and_heterogeneous"]
    assert report["counts"]["both_positive"] == 24
    assert report["independent_control_runs"] == 9
    assert all(
        row["G"] == pytest.approx(row["D"] + row["S"], abs=1e-12) for row in report["learned_cells"]
    )
    assert report["summary"]["D"]["negative"] == 3
    assert report["summary"]["D"]["mean"] == pytest.approx((24 * 0.02 - 3 * 0.01) / 27)
    assert report["factor_decomposition"]["G"]["interaction_rms"] == pytest.approx(0.0)
    with pytest.raises(ValueError, match="27 unique"):
        describe(rows[:-1])
    rows[0]["control"] = 3.0
    with pytest.raises(ValueError, match="paired control"):
        describe(rows)
