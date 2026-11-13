"""Synthetic P3 continuation, intervention and failure evidence contracts."""

import random
from pathlib import Path

import pytest
import torch

from arborlm.io import file_sha256, read_json, write_json
from arborlm.longer_training import CELL_FILES, _duration, _status, _summary
from arborlm.optimization_followup import _export, _optimizer, _training_step
from arborlm.p2_checkpoint import save as save_p2
from arborlm.p2_config import CONTROL, LEARNED, Cell, cells
from arborlm.p2_model import FollowupModel
from arborlm.p3_analysis import describe
from arborlm.p3_checkpoint import bitwise_equal, convert, restore, save
from arborlm.p3_config import DURATIONS, batch_offset, counters, load_config, validate_config

ROOT = Path(__file__).resolve().parents[1]


def test_registered_cursors_and_strict_config() -> None:
    config = load_config(ROOT / "configs" / "p3_longer_training.toml")
    config["training"]["final_step"] = 512
    with pytest.raises(ValueError, match="final_step"):
        validate_config(config)
    assert [batch_offset(step) for step in range(257, 513)] == list(range(0, 2048, 8))
    assert all(batch_offset(step) == batch_offset(step + 256) for step in range(257, 769))
    assert counters(256)["additional_targets"] == counters(512)["next_cyclic_order_cursor"] == 0
    assert counters(1024) == {
        "completed_step": 1024,
        "absolute_order_cursor": 8192,
        "next_cyclic_order_cursor": 0,
        "cumulative_targets": 524288,
        "additional_targets": 393216,
    }


@pytest.mark.parametrize("condition", (CONTROL, LEARNED))
def test_conversion_resume_and_intervention_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
) -> None:
    cell = Cell(101, 201, 301, condition)
    model = FollowupModel(cell)
    opt = _optimizer(model)
    batch = torch.randint(0, 256, (8, 3), generator=torch.Generator().manual_seed(11))
    # Tiny fixture: fill optimizer clocks after one update, then compare continuation.
    _training_step(model, opt, batch, 1)
    for state in opt.state.values():
        state["step"].fill_(256)
    p2_id = {"cell": cell.fields(), "fixture": "P2 synthetic"}
    parent = tmp_path / "p2"
    parent_hash = save_p2(parent, model, opt, 256, p2_id)
    parent_index = file_sha256(parent / "index.json")
    identity = {"cell": cell.fields(), "parent": {"checkpoint_state_sha256": parent_hash}}
    resumed = FollowupModel(cell)
    resumed_opt = _optimizer(resumed)
    path = tmp_path / "checkpoint-256"
    digest = convert(parent, p2_id, path, resumed, resumed_opt, identity)
    assert bitwise_equal(model.state_dict(), resumed.state_dict())
    assert bitwise_equal(opt.state_dict(), resumed_opt.state_dict())
    state = torch.load(path / "state.pt", weights_only=True)
    assert state["zero_training_conversion"] and state["counters"] == counters(256)
    assert bitwise_equal(state["python_rng"], random.getstate())
    assert bitwise_equal(state["torch_rng"], torch.get_rng_state())
    saved_python, saved_torch = random.getstate(), torch.get_rng_state().clone()
    weights = {key: value.clone() for key, value in resumed.state_dict().items()}
    monkeypatch.setattr("arborlm.optimization_followup.VAL_TARGETS", 16)
    evidence = _duration(tmp_path, cell, path, digest, identity, batch, resumed, 256)
    assert evidence["interventions"]["enabled"]["invariance_passed"]
    assert bitwise_equal(resumed.state_dict(), weights)
    assert bitwise_equal(opt.state_dict(), resumed_opt.state_dict())
    assert saved_python == random.getstate()
    assert bitwise_equal(saved_torch, torch.get_rng_state())
    assert _training_step(model, opt, batch, 257) == _training_step(
        resumed, resumed_opt, batch, 257
    )
    assert bitwise_equal(model.state_dict(), resumed.state_dict())
    assert bitwise_equal(opt.state_dict(), resumed_opt.state_dict())
    for state in resumed_opt.state.values():
        state["step"].fill_(512)
    next_path = tmp_path / "checkpoint-512"
    next_digest = save(next_path, resumed, resumed_opt, 512, identity)
    later = _duration(tmp_path, cell, next_path, next_digest, identity, batch, resumed, 512)
    if condition == LEARNED:
        for tag in ("values_permuted", "joint_within_branch"):
            assert (
                evidence["interventions"][tag]["permutation"]
                == later["interventions"][tag]["permutation"]
            )
    assert file_sha256(parent / "state.pt") == parent_hash
    assert file_sha256(parent / "index.json") == parent_index
    clone = FollowupModel(cell)
    with pytest.raises(ValueError, match="identity mismatch"):
        restore(next_path, clone, _optimizer(clone), {**identity, "unexpected": True})
    assert restore(next_path, clone, _optimizer(clone), identity) == counters(512)
    index_path = next_path / "index.json"
    write_json(index_path, {**read_json(index_path), "schema_version": 9})
    with pytest.raises(ValueError, match="schema"):
        restore(next_path, clone, _optimizer(clone), identity)


def test_failure_compact_evidence_stays_partial(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    status = _status()
    status[0].update(status="completed")
    status[1].update(status="running", run_id="fixture")
    write_json(run / "cells.json", status)
    result = _summary(run, "fixture failure")
    assert result["outcome"] == "failed"
    assert result["cells"][1]["status"] == "interrupted"
    assert all(row["status"] == "unexecuted" for row in result["cells"][2:])
    write_json(run / "duration_status.json", {"256": {"reference": 2.0}})
    for step in DURATIONS:
        checkpoint = run / f"checkpoint-{step}"
        checkpoint.mkdir()
        (checkpoint / "state.pt").write_bytes(b"local")
        write_json(checkpoint / "index.json", {"hash": "fixture"})
    export = tmp_path / "compact"
    _export(run, export, CELL_FILES)
    assert len(list(export.rglob("index.json"))) == 3
    assert not list(export.rglob("*.pt"))
    assert (export / "duration_status.json").is_file()


def test_primary_duration_flags_and_quality_guard() -> None:
    rows = []
    for cell in cells():
        if cell.condition == CONTROL:
            durations = {str(step): {"enabled": 2.1} for step in DURATIONS}
        else:
            durations = {}
            for step, enabled, effect in ((256, 2.0, 0.001), (512, 1.9, 0.003), (1024, 1.8, 0.01)):
                durations[str(step)] = {
                    "enabled": enabled,
                    "disabled": enabled + effect,
                    "values_permuted": enabled + effect,
                    "joint_within_branch": enabled,
                }
        rows.append({**cell.fields(), "durations": durations})
    result = describe(rows)
    assert result["all_three_flags"]
    assert result["changes_from_256"]["1024"]["learned"]["D"]["mean"] == pytest.approx(0.009)
    assert result["changes_from_256"]["512"]["learned"]["P"]["mean"] == pytest.approx(0.002)
    assert result["changes_from_256"]["1024"]["learned_quality_directions"]["improved"] == 27
    assert len(result["unique_controls"]) == 9
    for row in rows:
        if row["condition"] == CONTROL:
            row["durations"]["1024"]["enabled"] = 1.7
    changed = describe(rows)
    assert not changed["flags"]["endpoint_quality_guard"]
    assert changed["criteria"]["endpoint_enabled_mean_strictly_improved"]
    assert not changed["criteria"]["endpoint_mean_G_nonnegative"]
