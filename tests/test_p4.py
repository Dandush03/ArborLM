"""Synthetic engineering checks for the P4 runner and snapshots."""

import random
from pathlib import Path

import pytest
import torch

from arborlm.frozen_capacity import CELL_FILES, _interventions, _status, _summary, launch
from arborlm.io import file_sha256, read_json, write_json
from arborlm.optimization_followup import _export
from arborlm.p2_config import CONTROL
from arborlm.p2_config import Cell as ParentCell
from arborlm.p2_model import FollowupModel
from arborlm.p3_checkpoint import bitwise_equal
from arborlm.p4_checkpoint import restore, save
from arborlm.p4_config import BASELINE, DENSE, MEMORY, Cell, batch_offset, cells, counters
from arborlm.p4_model import FrozenModel, backbone_digest, evaluate, optimizer_for, train_step


def _parent() -> FollowupModel:
    return FollowupModel(ParentCell(101, 201, 301, CONTROL))


def _batch() -> torch.Tensor:
    return torch.randint(0, 256, (8, 5), generator=torch.Generator().manual_seed(812))


def test_grid_and_exact_two_epoch_offsets() -> None:
    rows = cells()
    assert len(rows) == len(set(rows)) == 63
    assert [cell.variant for cell in rows[:7]] == [
        BASELINE,
        MEMORY,
        DENSE,
        MEMORY,
        DENSE,
        MEMORY,
        DENSE,
    ]
    assert [cell.index for cell in rows if cell.variant == MEMORY] == list(range(27))
    assert [batch_offset(s) for s in range(1, 513)] == list(range(0, 2048, 8)) * 2
    assert counters(512) == dict(
        additional_step=512,
        absolute_order_cursor=4096,
        next_cyclic_order_cursor=0,
        additional_targets=262144,
    )


@pytest.mark.parametrize("variant", (MEMORY, DENSE))
def test_real_synthetic_updates_and_resumed_checkpoint(
    tmp_path: Path,
    variant: str,
) -> None:
    parent = _parent()
    cell = Cell(101, 301, 401, variant)
    model = FrozenModel(cell, parent)
    optimizer = optimizer_for(model)
    assert optimizer is not None
    frozen = backbone_digest(model.backbone)
    identity = {"cell": cell.fields(), "backbone_sha256": frozen}
    assert model.addition is not None
    initial = {key: value.detach().clone() for key, value in model.addition.state_dict().items()}
    step0 = tmp_path / "checkpoint-0"
    save(step0, model, optimizer, 0, identity)
    clone = FrozenModel(cell, parent)
    clone_opt = optimizer_for(clone)
    assert clone_opt is not None
    assert restore(step0, clone, clone_opt, identity) == counters(0)
    assert not clone_opt.state
    batch = _batch()
    for step in range(1, 257):
        train_step(model, optimizer, batch, step)
    assert any(
        not torch.equal(tensor, initial[name])
        for name, tensor in model.addition.state_dict().items()
    )
    assert all(param.grad is None for param in model.backbone.parameters())
    assert backbone_digest(model.backbone) == frozen
    intermediate = tmp_path / "checkpoint-256"
    save(intermediate, model, optimizer, 256, identity)
    assert restore(intermediate, clone, clone_opt, identity) == counters(256)
    assert train_step(model, optimizer, batch, 257) == train_step(clone, clone_opt, batch, 257)
    assert bitwise_equal(model.state_dict(), clone.state_dict())
    assert bitwise_equal(optimizer.state_dict(), clone_opt.state_dict())
    with pytest.raises(ValueError, match="identity"):
        restore(intermediate, clone, clone_opt, {**identity, "other": True})
    clone.backbone.mask[0, 0] = 1
    with pytest.raises(ValueError, match="frozen-backbone"):
        restore(intermediate, clone, clone_opt, identity)
    state = intermediate / "state.pt"
    state.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        restore(intermediate, clone, clone_opt, identity)


@pytest.mark.parametrize("variant", (BASELINE, MEMORY, DENSE))
def test_fresh_interventions_restore_baseline_and_preserve_live_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
) -> None:
    from arborlm import p4_model

    parent = _parent()
    cell = Cell(101, 301, 0 if variant == BASELINE else 403, variant)
    model = FrozenModel(cell, parent)
    opt = optimizer_for(model)
    batch = _batch()
    identity = {"cell": cell.fields(), "backbone_sha256": backbone_digest(model.backbone)}
    step = 0 if opt is None else 512
    if opt is not None:
        train_step(model, opt, batch, 1)
        # Synthetic serialization fixture only; set the registered snapshot clock.
        for state in opt.state.values():
            state["step"].fill_(step)
    path = tmp_path / f"checkpoint-{step}"
    digest = save(path, model, opt, step, identity)
    index = file_sha256(path / "index.json")

    def tiny_eval(m: FrozenModel, data: torch.Tensor) -> dict:
        return evaluate(m, data, expected_targets=32)

    monkeypatch.setattr(p4_model, "evaluate", tiny_eval)
    baseline = FrozenModel(Cell(101, 301, 0, BASELINE), parent)
    nll, base_nll = tiny_eval(model, batch)["nll"], tiny_eval(baseline, batch)["nll"]
    py, rng = random.getstate(), torch.get_rng_state()
    weights = {name: tensor.clone() for name, tensor in model.state_dict().items()}
    evidence = _interventions(tmp_path, model, path, digest, identity, batch, nll, base_nll)
    assert evidence["enabled"]["invariance_passed"]
    assert len(evidence) == {BASELINE: 1, MEMORY: 4, DENSE: 2}[variant]
    if variant != BASELINE:
        assert evidence["disabled"]["nll"] == base_nll
    assert bitwise_equal(weights, model.state_dict())
    assert py == random.getstate() and torch.equal(rng, torch.get_rng_state())
    assert index == file_sha256(path / "index.json") and digest == file_sha256(path / "state.pt")


def test_partial_export_and_no_parent_write(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    status = _status()
    status[0].update(status="running")
    write_json(run / "cells.json", status)
    assert _summary(run, "fixture failure")["cells"][0]["status"] == "interrupted"
    assert _summary(run, "fixture failure")["cells"][1]["status"] == "unexecuted"
    checkpoint = run / "checkpoint-0"
    checkpoint.mkdir()
    (checkpoint / "state.pt").write_bytes(b"local")
    write_json(checkpoint / "index.json", {"test": "fixture"})
    export = tmp_path / "compact"
    _export(run, export, CELL_FILES)
    assert read_json(export / "checkpoint-0" / "index.json") == {"test": "fixture"}
    assert not list(export.rglob("*.pt"))
    with pytest.raises(ValueError, match="inside the registered parent suite"):
        launch(tmp_path, tmp_path, run, run, export)


def test_synthetic_suite_handoff_and_failed_child_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from types import SimpleNamespace

    from arborlm import frozen_capacity as runner
    from arborlm import p4_data, p4_parent

    suite = tmp_path / "suite"
    suite.mkdir()
    write_json(suite / "manifest.json", {})
    parent_suite = tmp_path / "parent"
    parent_suite.mkdir()
    export = tmp_path / "results"
    sequence = [BASELINE, MEMORY, DENSE]
    parent_hash = "synthetic-parent"

    def freeze(path: Path, _source: Path) -> dict[str, str]:
        result = {"fixture": "synthetic"}
        write_json(path / "dataset_manifest.json", result)
        return result

    def supervise_child(root: Path, operation: str, arguments: list[str], **kwargs: object):
        index = 3 - len(sequence)
        child = root / f"synthetic-{index}"
        child.mkdir(parents=True)
        callback = kwargs["worker_argv"]
        assert callable(callback)
        argv = callback(child)
        variant = sequence.pop(0)
        assert argv[-1] == variant
        assert operation == "p4_capacity_cell" and arguments == []
        if variant != BASELINE:
            assert read_json(suite / "baselines.json")["b101-o301-control"] == {
                "nll": 2.0,
                "backbone_sha256": "frozen",
                "parent_checkpoint_state_sha256": parent_hash,
            }
        completed = variant != DENSE
        write_json(
            child / "terminal.json",
            {
                "status": "completed" if completed else "failed",
                "reason": None if completed else "fixture",
                "process_wall_seconds": 0.1,
                "peak_process_tree_rss_bytes": 1,
            },
        )
        if completed:
            write_json(
                child / "result.json",
                {
                    "final": {"nll": 2.0 if variant == BASELINE else 1.99},
                    "initial": None if variant == BASELINE else {"nll": 2.01},
                    "interventions": {"enabled": {"nll": 2.0}}
                    if variant == BASELINE
                    else {
                        "enabled": {"nll": 1.99},
                        "disabled": {"nll": 2.0},
                        "values_permuted": {"nll": 2.0},
                        "joint_within_branch": {"nll": 1.99},
                    },
                    "additional_training_targets": 0 if variant == BASELINE else 262144,
                    "checkpoint_state_sha256": {"checkpoint-0": "zero"},
                    "backbone_sha256": "frozen",
                },
            )
        else:
            (child / "stderr.log").write_text("fixture diagnostic failure\n")
        return child, completed

    monkeypatch.setattr(runner, "_prepare", lambda _run, _config: ({}, {}))
    monkeypatch.setattr(p4_parent, "verify_suite", lambda *_: {(101, 301): {"fixture": True}})
    monkeypatch.setattr(
        p4_parent,
        "verify_parent",
        lambda *_: SimpleNamespace(provenance={"checkpoint_state_sha256": parent_hash}),
    )
    monkeypatch.setattr(p4_data, "freeze", freeze)
    monkeypatch.setattr(runner, "supervise", supervise_child)
    with pytest.raises(RuntimeError, match="b101-o301-dense-s401 failed"):
        runner._suite(suite, runner.DEFAULT_CONFIG, tmp_path, parent_suite, export)
    result = read_json(suite / "result.json")
    assert [r["status"] for r in result["cells"][:4]] == [
        "completed",
        "completed",
        "failed",
        "unexecuted",
    ]
    assert result["counts"]["scientific_evaluations"] == 8
    assert result["counts"]["integrity_evaluations"] == 1
    assert (export / "b101-o301-dense-s401" / "stderr.log").read_text() == (
        "fixture diagnostic failure\n"
    )
    assert read_json(export / "suite" / "result.json") == result
    assert capsys.readouterr().out.count('"event":"cell_finished"') == 3
