"""Synthetic P5 orchestration and timing acceptance tests."""

import gc
import random
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from arborlm import hierarchy_ablation
from arborlm.io import read_json, write_json
from arborlm.p2_config import CONTROL
from arborlm.p2_config import Cell as ParentCell
from arborlm.p2_model import FollowupModel
from arborlm.p3_checkpoint import bitwise_equal
from arborlm.p4_model import extract
from arborlm.p5_checkpoint import restore, save
from arborlm.p5_clock import ActiveClock, wait_for_ack
from arborlm.p5_config import BASELINE, FIXED, FLAT, LEARNED, VARIANTS, Cell, cells, counters
from arborlm.p5_model import Model, backbone_digest, optimizer_for, state_digest, train_step
from arborlm.p5_timing import inputs_from_rows, run_schedule, schedule, trace_memory


def test_registered_grid_and_timing_call_counts() -> None:
    matrix = cells()
    assert len(matrix) == len(set(matrix)) == 117
    assert [c.variant for c in matrix[:5]] == [BASELINE, *VARIANTS]
    assert [c.variant for c in matrix[5:9]] == [*VARIANTS[1:], VARIANTS[0]]
    assert len([c for c in matrix if c.variant == BASELINE]) == 9
    blocks = list(schedule(0, VARIANTS))
    assert len(blocks) == 176
    assert sum(len(b.warm) + len(b.timed) for b in blocks) * 27 + 192 * 9 == 58752


def test_ack_clock_excludes_only_external_wait(tmp_path: Path) -> None:
    t = [100.0]
    clock = ActiveClock(1790, now=lambda: t[0])
    t[0] += 50
    ack = {}

    def announce(value: dict) -> None:
        ack.update(value)
        t[0] += 0.1  # This supervisor notification is charged, not excluded.

    def sleep(_duration: float) -> None:
        t[0] += 123
        write_json(
            Path(ack["ack_path"]),
            {
                "suite_id": "suite",
                "worker_id": "worker",
                "commit": "a" * 40,
                "push_completed": True,
            },
        )

    used: set[str] = set()
    record = wait_for_ack(tmp_path, "suite", "worker", used, clock, announce=announce, sleep=sleep)
    assert record["external_wait_seconds"] == pytest.approx(123)
    t[0] += 5
    assert clock.snapshot()["timing_worker_active_seconds"] == pytest.approx(55.1)
    assert clock.snapshot()["combined_worker_active_seconds"] == pytest.approx(1845.1)
    assert clock.worker_budget(45) == 45
    with pytest.raises(ValueError, match="before its worker request"):
        wait_for_ack(tmp_path, "suite", "worker", used, clock, announce=announce)
    t[0] += 535
    assert clock.worker_budget(45) == pytest.approx(9.9)
    t[0] += 10
    with pytest.raises(TimeoutError, match="deadline"):
        clock.worker_budget(45)


@pytest.mark.parametrize("malformed", [False, True])
def test_delayed_invalid_ack_wait_remains_charged(tmp_path: Path, malformed: bool) -> None:
    now = [100.0]
    clock = ActiveClock(1790, now=lambda: now[0])
    ack_path = tmp_path / "report-acks" / "worker.json"
    used: set[str] = set()

    def sleep(_duration: float) -> None:
        now[0] += 7
        if malformed:
            ack_path.write_text("not JSON", encoding="utf-8")
        else:
            write_json(
                ack_path,
                {
                    "suite_id": "suite",
                    "worker_id": "wrong-worker",
                    "commit": "a" * 40,
                    "push_completed": True,
                },
            )

    with pytest.raises(ValueError):
        wait_for_ack(tmp_path, "suite", "worker", used, clock, announce=lambda _: None, sleep=sleep)
    assert not used
    accounting = clock.snapshot()
    assert accounting["external_reporting_wait_seconds"] == 0
    assert accounting["timing_worker_active_seconds"] == 7


@pytest.mark.parametrize("finalization", [2.0, 20.0])
def test_quality_finalization_is_charged_before_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, finalization: float
) -> None:
    now = [100.0]
    monkeypatch.setattr(hierarchy_ablation, "time", SimpleNamespace(monotonic=lambda: now[0]))
    quality = tmp_path / "mock-quality"
    quality.mkdir()
    export = tmp_path / "results"
    timing_calls: list[tuple[float, float]] = []

    def supervise(*_args: object, **_kwargs: object) -> tuple[Path, bool]:
        now[0] += 1790
        write_json(quality / "result.json", {"cells": []})
        write_json(quality / "terminal.json", {"process_wall_seconds": 1790, "reason": None})
        return quality, True

    def finalize(_run: Path, target: Path, _files: tuple[str, ...]) -> None:
        now[0] += finalization
        target.mkdir(parents=True)

    def timing(*args: object, timing_start: float) -> bool:
        assert isinstance(args[4], float)
        timing_calls.append((args[4], timing_start))
        return True

    monkeypatch.setattr(hierarchy_ablation, "supervise", supervise)
    monkeypatch.setattr(hierarchy_ablation, "_finalize_stage", finalize)
    monkeypatch.setattr(hierarchy_ablation, "_timing_stage", timing)
    root, ok = hierarchy_ablation._launch(
        tmp_path / "config",
        tmp_path / "data",
        tmp_path / "output",
        tmp_path / "parent",
        export,
        hierarchy_ablation.SuiteRSS(),
    )
    total = 1790 + finalization
    if total < 1800:
        assert ok and timing_calls == [(total, 100 + total)]
    else:
        assert not ok and not timing_calls
        terminal = read_json(export / "suite" / "terminal.json")
        assert terminal == read_json(root / "terminal.json")
        assert terminal["quality_stage_wall_seconds"] == total
        assert terminal["timing"] == "unexecuted"


def test_real_synthetic_timing_and_operand_probe_preserve_state() -> None:
    backbone = extract(FollowupModel(ParentCell(101, 201, 301, CONTROL)))
    rows = torch.randint(0, 256, (32, 65), generator=torch.Generator().manual_seed(37))
    models = {v: Model(Cell(101, 301, 501, v), backbone) for v in VARIANTS}
    inputs = inputs_from_rows(rows)
    before = {v: state_digest(m) for v, m in models.items()}
    python_rng, torch_rng, gc_state = random.getstate(), torch.get_rng_state(), gc.isenabled()
    for v in (FLAT, FIXED, LEARNED):
        trace = trace_memory(models[v], inputs[8][0])
        assert trace["queries"] == 512 and trace["selected_values_per_query"] == 8
        assert trace["key_dot_products_per_query"] == (4096 if v == FLAT else 512)
        assert trace["key_normalization_input_elements"] == (65536 if v == FLAT else 4194304)
        assert trace["operators"]
    evidence = run_schedule(models, inputs, 0)
    assert evidence["call_counts"] == {
        "insertion_hidden": 32,
        "normalized_query": 24,
        "warmups": 352,
        "timed": 1760,
    }
    assert len(evidence["records"]) == 22
    assert all(len(row["durations_ns"]) == 80 for row in evidence["records"])
    assert before == {v: state_digest(m) for v, m in models.items()}
    assert all(m.training for m in models.values())
    assert python_rng == random.getstate() and torch.equal(torch_rng, torch.get_rng_state())
    assert gc_state is gc.isenabled()


def test_fixed_checkpoint_resume_and_router_buffer_guard(tmp_path: Path) -> None:
    backbone = extract(FollowupModel(ParentCell(101, 201, 301, CONTROL)))
    cell = Cell(101, 301, 501, FIXED)
    model = Model(cell, backbone)
    opt = optimizer_for(model)
    assert opt is not None
    identity = {"cell": cell.fields(), "backbone_sha256": backbone_digest(model.backbone)}
    batch = torch.randint(0, 256, (8, 3), generator=torch.Generator().manual_seed(61))
    before = state_digest(model)
    checkpoint = tmp_path / "step0"
    save(checkpoint, model, opt, 0, identity)
    clone = Model(cell, backbone)
    clone_opt = optimizer_for(clone)
    assert clone_opt is not None
    assert restore(checkpoint, clone, clone_opt, identity) == counters(0)
    assert state_digest(clone) == before
    for step in range(1, 257):
        train_step(model, opt, batch, step)
    mid = tmp_path / "step256"
    save(mid, model, opt, 256, identity)
    assert restore(mid, clone, clone_opt, identity) == counters(256)
    assert train_step(model, opt, batch, 257) == train_step(clone, clone_opt, batch, 257)
    assert bitwise_equal(model.state_dict(), clone.state_dict())
    assert bitwise_equal(opt.state_dict(), clone_opt.state_dict())
    original = read_json(mid / "index.json")
    write_json(mid / "index.json", {**original, "schema_version": 3})
    with pytest.raises(ValueError, match="schema"):
        restore(mid, clone, clone_opt, identity)
