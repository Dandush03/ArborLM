# ruff: noqa: E501
"""P10IS2 Part T training loops on a tiny world (ADR-0025 sections 5.1, 5.2, 11 item 4): every arm trains, frozen parts stay frozen, checkpoint-resume equals an uninterrupted run, a non-finite loss is not
resumed, seeds are the listed ones. CPU, tiny models. Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402

from studies.p10is2 import engine, partt_plan  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10s2.memory import MemoryArm  # noqa: E402

CELL_ORDER = ["M1", "M-append", "M-seq", "M-ii", "D1", "D-append", "D-seq"]


def test_every_arm_trains_snapshots_and_keeps_frozen_parts(tmp_path: Path) -> None:
    w = world()
    snaps = tmp_path / "snaps"
    arms = {}
    for name in CELL_ORDER:
        spec = engine.CellSpec(name, "AB", 0)
        before = None
        if spec.parent is not None:
            parent = engine.load_t(w, 0, snaps, spec.parent.label)
            before = engine.frozen_hashes(parent)
        rec, arm = engine.run_cell(w, spec, 4, snaps, tmp_path / "ck")
        assert rec["status"] == "COMPLETE" and rec["updates_done"] == 4 and rec["snapshot"]["arm_hash"] == arm.state_hash(), rec
        arms[name] = arm
        if name == "M-append":
            assert isinstance(arm, MemoryArm) and arm.store.stages == 2 and arm.store.rows == 32
            assert before is not None and engine.frozen_hashes(arm)["stage0"] == "|".join(__import__("studies.p10s2.model", fromlist=["x"]).tensor_sha(p) for p in engine.load_t(w, 0, snaps, "r0/M1/AB").store.stage_parameters(0))  # first-stage rows are those of M1, bit for bit
            assert (snaps / "r0__M-append__AB_at_append.pt").exists() or any("append" in p.name for p in snaps.iterdir())
        if name == "D-append":
            assert engine.frozen_hashes(arm)["first_adapter"] == engine.frozen_hashes(engine.load_t(w, 0, snaps, "r0/D-append/AB"))["first_adapter"]
    for name in ("M-joint", "D-joint"):
        rec, _ = engine.run_cell(w, engine.CellSpec(name, "-", 0), 4, snaps, None)
        assert rec["status"] == "COMPLETE" and rec["updates_done"] == 8  # the joint arms train 2U
    for c in core.TASKS:
        rec, arm = engine.run_cell(w, engine.CellSpec("E-table", "-", 0, c), 4, snaps, None)
        assert rec["status"] == "COMPLETE" and arm.parameter_count() == (w.vocabulary + 1) * w.cfg.width + 1
    # the loaded snapshot is the trained arm
    again = engine.load_t(w, 0, snaps, "r0/M-ii/AB")
    assert again.state_hash() == arms["M-ii"].state_hash()
    with pytest.raises(FileExistsError):
        engine.save_t(arms["M-ii"], snaps, "r0/M-ii/AB")  # snapshots are immutable


def test_trainable_sets_by_arm(tmp_path: Path) -> None:
    w = world()
    snaps = tmp_path / "s"
    engine.run_cell(w, engine.CellSpec("M1", "AB", 0), 2, snaps, None)
    m1 = engine.load_t(w, 0, snaps, "r0/M1/AB")
    for name, want in (("M-append", {1}), ("M-seq", {0}), ("M-ii", {0, 1})):
        spec = engine.CellSpec(name, "AB", 0)
        parent = m1 if name != "M-ii" else engine.run_cell(w, engine.CellSpec("M-append", "AB", 0), 2, snaps, None)[1]
        arm, _, _ = engine.build_cell_arm(w, spec, parent)
        got = {k for k in range(arm.store.stages) if arm.store.keys[k].requires_grad}  # type: ignore[attr-defined]
        assert got == want, name
    d1 = engine.run_cell(w, engine.CellSpec("D1", "AB", 0), 2, snaps, None)[1]
    arm, _, opts = engine.build_cell_arm(w, engine.CellSpec("D-append", "AB", 0), d1)
    assert len(arm.trainable()) == len(list(arm.second.parameters())) and opts["rate"] == w.lora_lr  # type: ignore[attr-defined]
    assert engine.CellSpec("M-ii", "AB", 1).parent.arm == "M-append" and engine.CellSpec("D-seq", "BA", 2).parent.label == "r2/D1/BA" and engine.CellSpec("M1", "AB", 0).parent is None


def test_checkpoint_resume_equals_an_uninterrupted_run(tmp_path: Path) -> None:
    w = world(updates=6)
    spec = engine.CellSpec("M1", "AB", 0)
    arm_a, rows, opts = engine.build_cell_arm(w, spec, None)
    full = engine.train_cell(w, spec, arm_a, rows, opts, 6, checkpoint_dir=tmp_path / "a", checkpoint_every=3)
    arm_b, rows, opts = engine.build_cell_arm(w, spec, None)
    part = engine.train_cell(w, spec, arm_b, rows, opts, 6, checkpoint_dir=tmp_path / "b", checkpoint_every=3, stop_after=3)
    assert part["status"] == "PAUSED" and part["last_finite_checkpoint"] == 3 and (tmp_path / "b").exists()
    arm_c, rows, opts = engine.build_cell_arm(w, spec, None)  # a new process: the arm is rebuilt from its seeds, the checkpoint restores it
    res = engine.train_cell(w, spec, arm_c, rows, opts, 6, checkpoint_dir=tmp_path / "b", checkpoint_every=3)
    assert res["status"] == "COMPLETE" and res["resumed"] is True and res["updates_done"] == 6
    assert arm_c.state_hash() == arm_a.state_hash() and full["resumed"] is False  # bit-identical on CPU
    assert not list((tmp_path / "b").glob("*.ckpt"))  # deleted once complete (G20)


def test_non_finite_loss_stops_the_cell_and_is_not_resumed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    w = world()
    spec = engine.CellSpec("M1", "AB", 0)
    arm, rows, opts = engine.build_cell_arm(w, spec, None)
    real = engine.p10train.loss_of
    calls = {"n": 0}

    def bad(*a, **k):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(*a, **k) if calls["n"] == 1 else torch.tensor(float("nan"))

    monkeypatch.setattr(engine.p10train, "loss_of", bad)
    rec = engine.train_cell(w, spec, arm, rows, opts, 4, checkpoint_dir=tmp_path, checkpoint_every=1)
    assert rec["status"] == "STOPPED_NONFINITE" and rec["updates_done"] == 1 and "non-finite" in rec["error"]
    d = partt_plan.resume_decision({"status": rec["status"], "last_finite_checkpoint": rec["last_finite_checkpoint"]})
    assert d["action"] == "refuse" and d["label"] == "ENGINEERING STOP — NON-FINITE VALUE"


def test_a_code_error_is_recorded_with_its_cause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    w = world()
    spec = engine.CellSpec("M1", "AB", 0)
    arm, rows, opts = engine.build_cell_arm(w, spec, None)
    monkeypatch.setattr(engine.p10train, "loss_of", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("out of memory")))
    rec = engine.train_cell(w, spec, arm, rows, opts, 4)
    assert rec["status"] == "ERROR" and "out of memory" in rec["error"] and rec["cause_recorded"] is True


def test_seed_plan_serves_only_listed_offsets_and_roles() -> None:
    plan = engine.SeedPlanT(CFG_T, "test", 0)
    assert plan.init_seed("D1") == 330298 + 3 and plan.code_seed() == 934001 + 10
    with pytest.raises(core.SeedRefused):
        plan.gen(7, "x")
    with pytest.raises(core.SeedRefused):
        plan.gen(0, "x")
    g1, g2 = plan.gen(2), plan.gen(2)
    assert torch.equal(torch.randperm(5, generator=g1), torch.randperm(5, generator=g2))  # a fresh generator per use
    reg = engine.SeedPlanT(CFG_T, "registered", 1)
    assert reg.init_seed("E-table") == 330211 + 6 and reg.values["data"]["batch_order"] == 250103
    assert reg.gen(3, "router sampling").initial_seed() == 250114 and reg.gen(3, "router initialization").initial_seed() == 330211 + 7
