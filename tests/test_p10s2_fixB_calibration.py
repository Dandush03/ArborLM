# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: calibration's mid-training snapshot is moved to CPU before CPU scoring (audit B B1: the copy stayed on ``mps:0`` and scoring it raised ``RuntimeError: mat1 is on CPU, expected GPU``
at the first 1,000-update snapshot); a calibration cell that does not complete makes the calibration uninterpretable; the pilot gate and the selection for U = 1,000 come from the snapshots. Stand-in world and test
seeds; the real MPS test runs where MPS is available. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import calibration, core, train  # noqa: E402


class DeviceArm:
    """A stand-in that mimics a second device: ``to`` records where the arm lives (a plain tensor cannot live on a device the machine lacks)."""

    def __init__(self) -> None:
        self.device = "mps:0"
        self.moves: list[str] = []
        self.payload = torch.zeros(3)

    def to(self, device: torch.device) -> "DeviceArm":
        self.device = str(device)
        self.moves.append(str(device))
        return self


def test_the_snapshot_is_a_copy_on_cpu_and_the_live_arm_stays_where_it_is() -> None:
    live = DeviceArm()
    snap = calibration.cpu_snapshot(live)
    assert snap is not live and snap.device == "cpu" and snap.moves == ["cpu"]  # the copy was moved to CPU
    assert live.device == "mps:0" and live.moves == []  # the live arm keeps training on the training device
    live.payload += 1
    assert float(snap.payload.sum()) == 0.0  # a copy, not a view


def test_the_snapshot_taken_inside_the_update_loop_is_on_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """The calibration loop takes every snapshot through ``cpu_snapshot`` (the real path trains on MPS; the MPS-gated test below runs it for real)."""
    world, _ = dry_world()
    monkeypatch.setitem(calibration.CAL, "read_layers", [0, 1])
    seen: list[str] = []
    real = calibration.cpu_snapshot

    def spy(arm: Any) -> Any:
        snap = real(arm)
        seen.append(str(next(iter(snap.trainable())).device))
        return snap

    monkeypatch.setattr(calibration, "cpu_snapshot", spy)
    rec = calibration.run_calibration(world, 0, updates=3, snapshot_updates=2)
    assert len(seen) == 8 and set(seen) == {"cpu"} and all(v == v for v in rec["snapshot_scores"].values())
    assert rec["device"] == "cpu" and rec["updates"] == 3 and rec["snapshot_updates"] == 2


@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="MPS is not available on this machine")
def test_the_real_mps_snapshot_is_scored_on_cpu_without_error() -> None:
    import dataclasses

    from studies.p10s2.memory import MemoryArm, SparseStore

    world, _ = dry_world()
    w = dataclasses.replace(world, device=torch.device("mps"))
    plan = core.SeedPlan("test", 0)
    arm = MemoryArm(SparseStore.new(w.cfg.width, w.rows_per_stage, plan.gen(0, "stage-1 store (test)")), w.layer, w.codes(0))
    holder: dict[str, Any] = {}

    def on_update(u: int) -> None:
        if u == 2:
            holder["snap"] = calibration.cpu_snapshot(arm)  # taken while the arm is on mps:0

    rec = train.train_arm(w.student, arm, w.train_examples(0, "A"), 3, w.batch, 0.003, plan.gen(2, "t"), w.marker_index, device=w.device, on_update=on_update)
    assert rec.status == "completed" and rec.device == "mps"
    assert all(p.device.type == "cpu" for p in holder["snap"].trainable())
    from studies.p10s2 import evaluate

    s = evaluate.score_panel(world.ctx, holder["snap"], world.d_cal["A"]).mean  # CPU scoring of the snapshot: this raised RuntimeError before the fix
    assert 0.0 <= s <= 1.0


def test_a_calibration_cell_that_fails_makes_the_calibration_uninterpretable(monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = dry_world()
    monkeypatch.setitem(calibration.CAL, "read_layers", [0, 1])
    calls = {"n": 0}
    real = train.loss_of

    def flaky(*a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 5:
            raise RuntimeError("unsupported operation")
        return real(*a, **k)

    monkeypatch.setattr(train, "loss_of", flaky)
    with pytest.raises(calibration.CalibrationFailed, match="unsupported operation"):
        calibration.run_calibration(world, 0, updates=3, snapshot_updates=2)  # nothing is selected from a calibration with a failed cell


def test_the_pilot_gate_and_selection_apply_to_the_snapshots_when_present() -> None:
    cs = calibration.calibration_cells()
    scores = {c.label: 0.5 for c in cs}
    assert calibration.select(scores).read_layer == 4 and calibration.pilot_gate({"A": 0.3, "B": 0.4})["ok"]
    assert calibration.pilot_gate({"A": 0.3, "B": None})["outcome"] == calibration.PILOT_STOP and calibration.PILOT_STOP == "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"
