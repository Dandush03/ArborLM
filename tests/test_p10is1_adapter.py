# ruff: noqa: E501
"""P10IS1 adapter and items (ADR-0024 sections 6, 7.2, 14): the adapter trains through P10-S1's own functions without editing them and without their seed whitelist, asserts seeds at the point of use, resumes a
segment bit for bit (G4, on the platform of record), records FAILED — NON-FINITE and keeps it, evaluates a snapshot with DEP counts (P10-S1's own ``evaluate_readout``), and computes the whole cell's stop rule. Tiny
synthetic models, test-range seeds (933001-933999) only; no registered seed and no experiments directory. Self-check only."""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import read_json  # noqa: E402
from studies.p10is1 import adapter, core, gates, items  # noqa: E402
from studies.p10s1 import core as s1core  # noqa: E402
from studies.p10s1 import train as s1train  # noqa: E402

CFG = core.load_config()
ROOT = Path(__file__).resolve().parents[1]
FACTS = 128


STRICT = os.environ.get("P10IS1_STRICT") == "1"
ON_MAC_ARM = sys.platform == "darwin" and platform.machine() == "arm64"


def strict_or_skip() -> None:
    """The bit-exact assertions run only in the configured subprocess (one thread, one interop thread, deterministic algorithms: the platform of record), where they are strict; the outer run skips them."""
    if not STRICT:
        pytest.skip("runs strictly in test_bit_exact_assertions_in_a_configured_subprocess")
    gates.configure_worker(CFG)
    assert gates.on_platform_of_record(CFG), gates.platform_problems(CFG)


def ctx_at(tmp: Path) -> items.Ctx:
    return items.Ctx(core.TEST, tmp / "run", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64})


def tiny_spec(arm: str = "F-OQ", slots: int = 1024, run: int = 16, snaps: tuple[int, ...] = (4, 8, 12, 16), draw: int = 1) -> dict[str, Any]:
    seeds, init = core.seeds_for(core.TEST, draw)
    cell = core.make_cell(core.TEST, arm, FACTS, slots, draw, init, u_p=8, run=run, lr=0.003)
    return {"label": cell.label, "arm": arm, "facts": FACTS, "slots": slots, "draw": draw, "init_seed": init, "seed_name": seeds.name, "seed_base": seeds.facts, "u_p": 8, "lr": 0.003, "run": run, "ladder_cell": False, "snapshots": list(snaps), "mode": core.TEST}


def test_p10s1_refuses_this_studys_seed_set_and_the_adapter_trains_it_unedited(tmp_path: Path) -> None:
    spec = tiny_spec()
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    cell = adapter.cell_of(spec)
    job = adapter.job_for(cell, data, seeds, items.backbone_of(ctx), tmp_path / "never", (4,), optimizer_marks=(4,), max_updates=4, mode="registered")
    with pytest.raises(ValueError, match="cannot use the 'p10is1-test-0' seed set"):
        s1train.run_job(job)  # P10-S1's own loop refuses, unedited: not patched, not wrapped
    assert not (tmp_path / "never").exists()
    rec = adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 8, mode=core.TEST)
    assert rec["trained_to"] == 8 and set(rec["snapshot_sha256"]) == {"4", "8"}
    src = (ROOT / "studies" / "p10s1" / "train.py").read_text(encoding="utf-8")
    assert "check_job_seeds(job)" in src and "p10is1" not in src and "p10is1" not in (ROOT / "studies" / "p10s1" / "core.py").read_text(encoding="utf-8")


def test_assert_seed_allowed_at_the_point_of_use() -> None:
    def spec_of(seeds: Any, init: int, draw: int) -> dict[str, Any]:
        return {"seed_name": seeds.name, "seed_base": seeds.facts, "init_seed": init, "draw": draw}

    for d in range(1, 6):
        adapter.assert_seed_allowed(core.REGISTERED, spec_of(core.registered_seeds(d), core.init_seed_of(d), d))
    # a registered stage refuses every other value: a test, calibration or rehearsal set, a wrong initialisation, a wrong draw
    for bad in (spec_of(core.test_seeds(0), 330198, 1), spec_of(core.calibration_seeds(1), 330191, 1), spec_of(core.rehearsal_seeds(), 330192, 1), spec_of(core.registered_seeds(1), 330102, 1), spec_of(core.registered_seeds(2), 330102, 1)):
        with pytest.raises(ValueError, match="refused"):
            adapter.assert_seed_allowed(core.REGISTERED, bad)
    adapter.assert_seed_allowed("calibration", spec_of(core.calibration_seeds(1), 330191, 1))
    adapter.assert_seed_allowed("calibration", spec_of(core.calibration_seeds(2), 330193, 2))
    with pytest.raises(ValueError):
        adapter.assert_seed_allowed("calibration", spec_of(core.calibration_seeds(1), 330193, 1))  # the pair is fixed
    with pytest.raises(ValueError):
        adapter.assert_seed_allowed("calibration", spec_of(core.registered_seeds(1), 330191, 1))
    adapter.assert_seed_allowed(core.REHEARSAL, spec_of(core.rehearsal_seeds(), 330192, 1))
    with pytest.raises(ValueError):
        adapter.assert_seed_allowed(core.REHEARSAL, spec_of(core.registered_seeds(1), 330192, 1))
    adapter.assert_seed_allowed(core.TEST, spec_of(core.test_seeds(3), 330199, 1))
    with pytest.raises(ValueError):
        adapter.assert_seed_allowed(core.TEST, spec_of(core.registered_seeds(1), 330198, 1))  # a test run never touches a registered seed
    with pytest.raises(ValueError):
        adapter.assert_seed_allowed(core.TEST, spec_of(core.test_seeds(0), 330101, 1))
    with pytest.raises(ValueError):
        adapter.assert_seed_allowed("nonsense", spec_of(core.test_seeds(0), 330198, 1))


@pytest.mark.parametrize("arm", ["F-OQ", "T-OQ", "H8", "D-OQ", "R2"])
def test_every_arm_trains_a_segment_and_resumes_bit_for_bit(tmp_path: Path, arm: str) -> None:
    strict_or_skip()
    spec = tiny_spec(arm, slots=1024 if arm != "R2" else 1024)
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    bb = items.backbone_of(ctx)
    whole = tmp_path / "whole"
    chk = adapter.restoration_check(data, seeds, bb, whole, spec, 8, 16, mode=core.TEST)
    assert chk["split"] == 8 and chk["end"] == 16
    assert chk["tensors_equal"] is True and chk["model_sha256_equal"] is True  # G4 on the platform of record, strictly


def test_train_to_resumes_from_the_optimizer_snapshot_and_skips_complete_segments(tmp_path: Path) -> None:
    strict_or_skip()
    spec = tiny_spec()
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    bb = items.backbone_of(ctx)
    r1 = adapter.train_to(data, seeds, bb, ctx.run_dir, spec, 8, mode=core.TEST)
    out = adapter.cell_dir(ctx.run_dir, spec["label"])
    assert adapter.resumable_snapshots(out) == [8]  # the optimizer is kept at the segment's end only
    again = adapter.train_to(data, seeds, bb, ctx.run_dir, spec, 8, mode=core.TEST)
    assert again["snapshot_sha256"] == r1["snapshot_sha256"] and len(again["segments"]) == 1  # a complete segment is not recomputed
    r2 = adapter.train_to(data, seeds, bb, ctx.run_dir, spec, 16, mode=core.TEST)
    assert r2["segments"][1]["from"] == 8 and r2["segments"][1]["to"] == 16 and set(r2["snapshot_sha256"]) == {"4", "8", "12", "16"}
    # a killed run left a snapshot beyond the last resumable point: it is removed and rewritten identically
    h = r2["snapshot_sha256"]["12"]
    (out / "snapshots" / s1core.snapshot_stem(16) / "snapshot.json").unlink()
    r3 = adapter.train_to(data, seeds, bb, ctx.run_dir, spec, 16, mode=core.TEST)
    assert r3["snapshot_sha256"]["12"] == h
    assert "cpu_seconds_at_snapshot" in r3["segments"][-1]


def test_a_non_finite_update_is_recorded_failed_kept_and_never_rerun(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = tiny_spec()
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    real = s1train.Trainer.step

    def boom(self: Any, batch: Any) -> Any:
        if self.update + 1 == 3:
            raise ValueError("non-finite task loss at update 3")
        return real(self, batch)

    monkeypatch.setattr(s1train.Trainer, "step", boom)
    with pytest.raises(adapter.NonFinite, match="FAILED — NON-FINITE at update 3"):
        adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 8, mode=core.TEST)
    failed = read_json(adapter.cell_dir(ctx.run_dir, spec["label"]) / adapter.FAILED_RECORD)
    assert failed["failed_update"] == 3 and failed["status"] == "failed" and "NON-FINITE" in failed["reason"]
    monkeypatch.setattr(s1train.Trainer, "step", real)
    with pytest.raises(RuntimeError, match="kept, not re-run"):
        adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 8, mode=core.TEST)


def test_an_ordinary_error_is_not_turned_into_non_finite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = tiny_spec()
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    monkeypatch.setattr(s1train.Trainer, "step", lambda self, batch: (_ for _ in ()).throw(ValueError("shape mismatch")))
    with pytest.raises(ValueError, match="shape mismatch"):
        adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 4, mode=core.TEST)
    assert not (adapter.cell_dir(ctx.run_dir, spec["label"]) / adapter.FAILED_RECORD).exists()  # a code error is an item error, not a failed cell


def test_the_adapter_identity_gate_reproduces_p10s1_checkpoints(tmp_path: Path) -> None:
    strict_or_skip()
    ctx = ctx_at(tmp_path)
    spec = tiny_spec()
    data, seeds = items.load_data(ctx, spec, verify=False)
    s1seeds = s1core.seed_set("p10s1-test-3", seeds.facts)  # P10-S1's whitelist accepts the NAME; the values are this study's test range
    stored = {}
    for arm in ("F-OQ", "T-OQ"):
        cell = s1core.make_cell("P", arm, FACTS, 1024, 1, 330198, u_p=8, run_updates=16)
        job = s1train.TrainJob(
            cell=cell, data=data, stream=s1train.training_stream_for(data, FACTS), backbone=items.backbone_of(ctx), out_dir=tmp_path / "s1" / "cells" / cell.label, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds),
            mode="calibration", updates=16, snapshots=(4, 8, 12), optimizer_marks=(16,), max_updates=12, log_every=4,
        )  # fmt: skip
        data_s1 = data
        assert data_s1.seeds.name == "p10is1-test-0" and s1seeds.name == "p10s1-test-3"
        # P10-S1's train_cell checks the NAME of the data's seed set: build the data under P10-S1's test name for its own training only
        from studies.p9 import data as dm

        d2 = dm.build_study_data(s1seeds, items.SYNTHETIC_CORPUS, sizes=dm.DataSizes(main_trained=512, unseen=64, lane_d_per_set=s1core.LANE_D_STUB))
        job.data, job.stream = d2, s1train.training_stream_for(d2, FACTS)
        s1train.train_cell(job)
        stored[arm] = cell
    cells = [(arm, FACTS, 1024, 1, 330198, 8, 16) for arm in ("F-OQ", "T-OQ")]
    d2 = job.data
    res = adapter.identity_gate(tmp_path / "s1", tmp_path / "work", data=d2, seeds=d2.seeds, backbone=items.backbone_of(ctx), cells=cells, updates=[4, 8, 12], cfg=CFG)
    assert res["passed"] is True
    for label, per in res["cells"].items():
        assert all(v == {"tensors_equal": True, "model_sha256_equal": True} for v in per.values()), label


def test_evaluate_snapshot_records_dep_counts_and_the_index_read(tmp_path: Path) -> None:
    spec = tiny_spec("F-OQ")
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 8, mode=core.TEST)
    path = items.evaluate_snapshot(ctx, spec, 8, data=data, seeds=seeds)
    rec = core.read_record(path, "eval")
    assert set(rec["reads"]) == {"main", "ivf"} and rec["update"] == 8
    for read in rec["reads"].values():
        for panel in core.PANELS:
            p = read["panels"][panel]
            assert {"n", "correct", "useful", "disabled_correct", "shuffled_correct", "unseen_n", "unseen_correct"} <= set(p) and p["n"] > 0
    assert items.evaluate_snapshot(ctx, spec, 8, data=data, seeds=seeds) == path  # an existing record is kept
    # a snapshot that does not hash to its train record is an identity refusal, not a result
    spec2 = tiny_spec("T-OQ")
    adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec2, 4, mode=core.TEST)
    snap = adapter.cell_dir(ctx.run_dir, spec2["label"]) / "snapshots" / s1core.snapshot_stem(4) / "model.pt"
    snap.write_bytes(snap.read_bytes() + b"x")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        items.evaluate_snapshot(ctx, spec2, 4, data=data, seeds=seeds)
    b = items.baseline_item(ctx, 1, FACTS, spec, data=data, seeds=seeds)
    brec = core.read_record(b, "baseline")
    assert set(brec["no_memory"]) == {"A", "B"} and all(v >= 0 for v in brec["no_memory"].values())


def test_evaluation_runs_under_no_grad_and_bounded_memory(tmp_path: Path) -> None:
    spec = tiny_spec("D-OQ")
    ctx = ctx_at(tmp_path)
    data, seeds = items.load_data(ctx, spec, verify=False)
    adapter.train_to(data, seeds, items.backbone_of(ctx), ctx.run_dir, spec, 4, mode=core.TEST)
    import resource

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    modes: list[bool] = []
    real = items.s1eval.evaluate_readout

    def spy(*a: Any, **k: Any) -> Any:  # calls through: records whether autograd was enabled while P10-S1's evaluation ran
        modes.append(torch.is_grad_enabled())
        return real(*a, **k)

    items.s1eval.evaluate_readout = spy  # type: ignore[assignment]
    try:
        with torch.enable_grad():
            items.evaluate_snapshot(ctx, spec, 4, data=data, seeds=seeds)
    finally:
        items.s1eval.evaluate_readout = real  # type: ignore[assignment]
    assert modes == [False] and torch.is_grad_enabled()  # evaluation ran under no_grad and the caller's mode is restored
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    assert (after - before) < 3 * 1024**3  # a tiny model must not grow the process by gigabytes (ru_maxrss is bytes on darwin, kilobytes on linux: the bound holds on both)


# --- the ladder decision (the whole cell's stop rule) ----------------------------------------------------------------------------------------------------
def _write_eval(ctx: items.Ctx, spec: dict[str, Any], update: int, a_use: float) -> None:
    n = spec["facts"]
    useful = round(a_use * n)
    pan = {p: {"n": n, "correct": useful, "useful": useful, "disabled_correct": n // 32, "swap_correct": n // 32, "shuffled_correct": n // 32, "unseen_n": 64, "unseen_correct": 2} for p in core.PANELS}
    core.write_record(ctx.eval_path(spec["label"], update), {**core.envelope("eval"), "label": spec["label"], "update": update, "reads": {"main": {"panels": pan}}}, overwrite=True)


def test_ladder_decision_requires_every_store_arm_in_every_replicate_and_ignores_d_oq(tmp_path: Path) -> None:
    params = core.PlanParams({2048: 8192, 8192: 8192, 32768: 16384}, {u: 0.003 for u in core.units()}, {"2K/256": 98304, "8K/1K": 98304, "32K/4K": 131072}, {"2K/256": 196608, "8K/1K": 196608, "32K/4K": 262144})
    specs = [s for s in core.planned_cells(params, core.TEST) if s["ladder_cell"] and core.cell_name(s["facts"], s["slots"]) == "8K/1K"]
    assert {s["arm"] for s in specs} == {"F-OQ", "T-OQ", "H8", "D-OQ"} and len(specs) == 20
    ctx = ctx_at(tmp_path)
    # the plateau test at 98,304 needs i* at 98,304, 49,152, and the previous ladder point 65,536 with its half 32,768: flat a_use 0.6 from 32,768 on is full
    for s in specs:
        for u in s["snapshots"]:
            _write_eval(ctx, s, u, 0.6 if u >= 32768 else 0.3)
    d = items.ladder_decision(ctx, specs, 98304)
    assert d["all_full"] is True and len(d["full"]) == 15 and not any("D-OQ" in k for k in d["full"])  # three store arms x five replicates
    # one T-OQ replicate still rising (a_use 0.3 at 49,152 against 0.6 at 98,304): the whole cell does not stop
    t = next(s for s in specs if s["arm"] == "T-OQ" and s["draw"] == 3)
    _write_eval(ctx, t, 32768, 0.3)
    _write_eval(ctx, t, 49152, 0.3)  # i* is a running maximum: both snapshots below the half must be low for the gain over the last doubling to be 0.3 > 0.10
    d2 = items.ladder_decision(ctx, specs, 98304)
    assert d2["all_full"] is False and [k for k, v in d2["full"].items() if not v] == [t["label"]]
    # D-OQ not full requests nothing
    dq = next(s for s in specs if s["arm"] == "D-OQ")
    _write_eval(ctx, dq, 49152, 0.1)
    assert items.ladder_decision(ctx, specs, 98304)["full"].keys() == d2["full"].keys()
    # the first ladder point (65,536) has no predecessor: never full
    assert items.ladder_decision(ctx, specs, 65536)["all_full"] is False


def test_next_level_is_the_first_granted_ladder_point_above_what_was_reached() -> None:
    assert items.next_level(393216, 786432, 393216) == 524288 and items.next_level(393216, 786432, 524288) == 786432 and items.next_level(393216, 786432, 786432) is None
    assert items.next_level(131072, 131072, 131072) is None  # G = U0: no level is granted
    assert items.next_level(131072, 524288, 131072) == 196608


@pytest.mark.skipif(not ON_MAC_ARM, reason="the platform of record is macOS arm64")
def test_bit_exact_assertions_in_a_configured_subprocess() -> None:
    """The restoration (G4) on all five arms, the resume of a segment with a half-written snapshot, and the adapter identity gate against P10-S1's own training run STRICTLY: the child process is configured to the platform of
    record before it runs (one thread, one interop thread, deterministic algorithms)."""
    out = subprocess.run([sys.executable, "-m", "pytest", str(Path(__file__)), "-q", "-p", "no:cacheprovider", "-k", "bit_for_bit or resumes_from_the_optimizer or identity_gate_reproduces"], cwd=ROOT, env={**os.environ, "P10IS1_STRICT": "1", "PYTHONPATH": str(ROOT)}, capture_output=True, text=True, timeout=900, check=False)
    assert out.returncode == 0, out.stdout[-2500:]
    assert "passed" in out.stdout and "skipped" not in out.stdout.splitlines()[-1] and "failed" not in out.stdout.splitlines()[-1]
