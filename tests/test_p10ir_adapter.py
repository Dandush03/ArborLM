# ruff: noqa: E501
"""P10IR stage A2 adapter tests (ADR-0029 section 10): the adapter trains through P10-S1's own model and training functions without editing them and without P10-S1's seed whitelist; the identity gate
compares every tensor (``torch.equal``) and the snapshot file hash written through ``train.save_snapshot`` under P10-S1's cell label (R3-2); the snapshot schedule is P10-S1's. Tiny synthetic models, the
unit-test seeds 938001-938999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import read_json  # noqa: E402
from studies.p10ir import adapter, core, freeze, gates, items  # noqa: E402
from studies.p10ir import plan as planmod
from studies.p10ir import testing as tiny  # noqa: E402
from studies.p10s1 import core as s1core  # noqa: E402
from studies.p10s1 import train as s1train  # noqa: E402

CFG = core.load_config()
ROOT = Path(__file__).resolve().parents[1]
FACTS = 128
SNAPS = (4, 8, 12)


def ctx_at(tmp: Path) -> items.Ctx:
    return items.Ctx("rehearsal", tmp / "run", tmp / "s1", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64})


def p10s1_job(tmp: Path, arm: str, seeds: Any, data: Any, *, slots: int = 1024, init: int = 330698, mode: str = "calibration") -> tuple[s1train.TrainJob, s1core.Cell]:
    cell = s1core.make_cell("P", arm, FACTS, slots, 1, init, u_p=8, run_updates=16)
    job = s1train.TrainJob(
        cell=cell, data=data, stream=s1train.training_stream_for(data, FACTS), backbone=tiny.backbone(), out_dir=tmp / "s1" / "cells" / cell.label, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), mode=mode,
        updates=16, snapshots=SNAPS, optimizer_marks=(16,), max_updates=12, log_every=4,
    )  # fmt: skip
    return job, cell


def test_p10s1_refuses_a_bridge_seed_set_and_the_adapter_trains_it_without_touching_p10s1(tmp_path: Path) -> None:
    """The reason for new code (section 10): ``run_job`` calls ``check_job_seeds``, which refuses any seed-set name that is not P10-S1's. The adapter is the loop without that call."""
    data, seeds = items.load_data(ctx_at(tmp_path), {"seed_name": "p10ir-bridge-1", "seed_base": 938301, "table_facts": 512, "unseen": 64}, verify=False)  # a bridge-style name on the unit-test range
    cell = s1core.make_cell("P", "F-OQ", FACTS, 1024, 1, 330601, u_p=8, run_updates=4)
    out = tmp_path / "never"
    job = adapter.job_for(cell, data, seeds, tiny.backbone(), out, (2, 4), mode="registered")
    with pytest.raises(ValueError, match="cannot use the 'p10ir-bridge-1' seed set"):
        s1train.run_job(job)  # P10-S1's own loop refuses, unedited
    assert not out.exists()
    done = adapter.run_cell(adapter.job_for(cell, data, seeds, tiny.backbone(), tmp_path / "adapter", (2, 4), mode="registered"), keep_optimizer=False)  # the adapter's loop runs it
    assert set(done["snapshot_sha256"]) == {"2", "4"}
    s1_source = (ROOT / "studies" / "p10s1" / "train.py").read_text(encoding="utf-8")
    assert "check_job_seeds(job)" in s1_source  # the guard is still there; nothing was removed or patched
    assert "p10ir" not in s1_source and "p10ir" not in (ROOT / "studies" / "p10s1" / "core.py").read_text(encoding="utf-8")


def test_the_adapter_reproduces_p10s1s_checkpoints_tensor_for_tensor_and_file_for_file(tmp_path: Path) -> None:
    data, seeds = items.load_data(ctx_at(tmp_path), {"seed_name": "p10s1-test-3", "seed_base": 938301, "table_facts": 512, "unseen": 64}, verify=False)  # P10-S1's whitelist accepts the name; the values are the unit-test range's
    stored = {}
    for arm in ("F-OQ", "T-OQ"):
        job, cell = p10s1_job(tmp_path, arm, seeds, data)
        s1train.train_cell(job)  # P10-S1's own training writes the stored checkpoints
        stored[arm] = cell
    ctx = ctx_at(tmp_path)
    ctx.s1_run_dir = tmp_path / "s1"
    cells = [(arm, FACTS, 1024, 1, 330698, 8, 16) for arm in ("F-OQ", "T-OQ")]
    ctx.sizes = {"table_facts": 512, "unseen": 64}
    # the identity gate loads the draw through items.load_data, which needs the seed set by name: give it P10-S1's draw layout at base 938301
    res = adapter.identity_gate(ctx, tmp_path / "work", cells=cells, seeds_of=lambda d: s1core.seed_set("p10s1-test-3", 938301), updates=list(SNAPS), cfg=CFG)
    if gates.on_platform_of_record(CFG):
        assert res["passed"] is True and res["status"] == "passed"
        for label, per in res["cells"].items():
            assert set(per) == {"4", "8", "12"} and all(v == {"tensors_equal": True, "model_sha256_equal": True} for v in per.values()), label
        # the adapter's snapshot is byte-identical to P10-S1's: same label inside the payload, same stream write
        a = (tmp_path / "work" / stored["F-OQ"].label / "snapshots" / s1core.snapshot_stem(8) / "model.pt").read_bytes()
        b = (tmp_path / "s1" / "cells" / stored["F-OQ"].label / "snapshots" / s1core.snapshot_stem(8) / "model.pt").read_bytes()
        assert a == b
    else:
        assert res["passed"] is None and res["status"] == "skipped"


def test_the_identity_gate_fails_on_a_different_tensor_a_different_label_and_a_different_seed(tmp_path: Path) -> None:
    if not gates.on_platform_of_record(CFG):
        pytest.skip("the adapter identity gate is bit-exact and runs on macOS arm64 only")
    data, seeds = items.load_data(ctx_at(tmp_path), {"seed_name": "p10s1-test-3", "seed_base": 938301, "table_facts": 512, "unseen": 64}, verify=False)
    job, cell = p10s1_job(tmp_path, "F-OQ", seeds, data)
    s1train.train_cell(job)
    ctx = ctx_at(tmp_path)
    ctx.s1_run_dir = tmp_path / "s1"
    cells = [("F-OQ", FACTS, 1024, 1, 330698, 8, 16)]
    of = lambda d: seeds  # noqa: E731
    ok = adapter.identity_gate(ctx, tmp_path / "w1", cells=cells, seeds_of=of, updates=[4, 8], cfg=CFG)
    assert ok["passed"] is True
    # one tensor of the stored checkpoint differs: the gate fails on that update only
    path = tmp_path / "s1" / "cells" / cell.label / "snapshots" / s1core.snapshot_stem(8) / "model.pt"
    payload = torch.load(path, weights_only=True, map_location="cpu")
    payload["model"]["addition.values"] = payload["model"]["addition.values"] + 1e-7
    path.chmod(0o644)
    torch.save(payload, path)
    bad = adapter.identity_gate(ctx, tmp_path / "w2", cells=cells, seeds_of=of, updates=[4, 8], cfg=CFG)
    assert bad["passed"] is False and bad["cells"][cell.label]["4"]["tensors_equal"] is True and bad["cells"][cell.label]["8"]["tensors_equal"] is False
    # the same tensors written under another label are the same tensors but not the same file: the hash part of the gate sees it (R3-2)
    other = s1core.make_cell("P", "F-OQ", FACTS, 1024, 1, 330698, u_p=8, run_updates=16)
    job2 = adapter.job_for(other, data, seeds, tiny.backbone(), tmp_path / "relabel", SNAPS, max_updates=12)
    job2.cell = s1core.make_cell("P", "F-OQ", FACTS, 1024, 1, 330698, u_p=8, run_updates=20)  # another label, same training
    adapter.run_cell(job2, keep_optimizer=False)
    a = torch.load(tmp_path / "relabel" / "snapshots" / s1core.snapshot_stem(4) / "model.pt", weights_only=True)
    b = torch.load(tmp_path / "s1" / "cells" / cell.label / "snapshots" / s1core.snapshot_stem(4) / "model.pt", weights_only=True)
    assert a["label"] != b["label"] and all(torch.equal(a["model"][k], b["model"][k]) for k in a["model"])
    from arborlm.io import file_sha256

    assert file_sha256(tmp_path / "relabel" / "snapshots" / s1core.snapshot_stem(4) / "model.pt") != read_json(tmp_path / "s1" / "cells" / cell.label / "snapshots" / s1core.snapshot_stem(4) / "snapshot.json")["model_sha256"]
    # a different initialisation seed fails the gate by construction
    seed_cells = [("F-OQ", FACTS, 1024, 1, 330699, 8, 16)]
    with pytest.raises(FileNotFoundError):  # the stored cell of that label does not exist: a missing file raises, which also stops the stage before any bridge seed is used
        adapter.identity_gate(ctx, tmp_path / "w3", cells=seed_cells, seeds_of=of, updates=[4], cfg=CFG)


def test_bridge_cells_are_p10s1_cells_with_p10s1s_rate_and_a_bridge_label() -> None:
    cell = adapter.bridge_cell("T-OQ", 8192, 4096, 1, 8192, 49152, CFG)
    assert (cell.lr, cell.u_p, cell.run_updates, cell.init_seed, cell.kind) == (s1core.LEARNING_RATE, 8192, 49152, 330601, "P")
    assert cell.label == "P_T-OQ_f8192_n4096_d1_i330601" and core.bridge_label("T-OQ", 8192, 4096, 1, 8192, 49152, CFG) == cell.label
    assert core.s1_label("T-OQ", 8192, 4096, 1, 8192, 49152, CFG) == "P_T-OQ_f8192_n4096_d1_i2101"
    seeds = core.bridge_seeds(2, CFG)
    assert seeds.facts == 290101 and s1core.index_seed(seeds) == 290161 and seeds.name == "p10ir-bridge-2"
    assert core.bridge_init_seed(5, CFG) == 330605
    with pytest.raises(ValueError):
        core.bridge_init_seed(6, CFG)
    big = adapter.bridge_cell("F-OQ", 32768, 16384, 3, 16384, 98304, CFG)
    assert big.label == "P_F-OQ_f32768_n16384_d3_i330603_u16384"
    assert adapter.TRAIN_LR == 0.003 == CFG["a2"]["learning_rate"]


def test_the_snapshot_schedule_of_a_bridge_cell_is_p10s1s_for_the_same_arm_facts_and_slots() -> None:
    from studies.p10s1 import frozen as s1frozen

    fro = s1frozen.Frozen.from_json(read_json(ROOT / core.P10S1_PLAN)["frozen"])  # the committed frozen plan of P10-S1 (not a sealed record)
    it = planmod.registered_items(CFG)
    entries = freeze.bridge_cell_entries(CFG, it["A2"], fro)
    assert len(entries) == 20
    for arm in ("F-OQ", "T-OQ"):
        for facts, slots, u_p, run in ((8192, 4096, 8192, 49152), (32768, 16384, 16384, 98304)):
            theirs = s1core.make_cell("P", arm, facts, slots, 1, 2101, u_p=u_p, run_updates=run)
            mine = entries[core.bridge_label(arm, facts, slots, 1, u_p, run, CFG)]["snapshots"]
            assert mine == list(fro.snapshots(theirs)) and u_p in mine and run in mine and run // 2 in mine
    snaps = entries[core.bridge_label("F-OQ", 8192, 4096, 1, 8192, 49152, CFG)]["snapshots"]
    assert snaps[:3] == [512, 1024, 2048]  # the first three snapshots of the identity gate


def test_a_bridge_cell_is_built_partial_renamed_when_complete_and_a_failure_is_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = ctx_at(tmp_path)
    cell = s1core.make_cell("P", "F-OQ", FACTS, 1024, 1, 330698, u_p=8, run_updates=16)
    spec = {"arm": "F-OQ", "facts": FACTS, "slots": 1024, "draw": 1, "init_seed": 330698, "u_p": 8, "run": 16, "seed_name": "p10ir-test-3", "seed_base": 938301, "table_facts": 512, "unseen": 64, "snapshots": [4, 8, 16]}
    cells = {cell.label: spec}
    rec = adapter.train_bridge_cell(ctx, cell.label, cells)
    root = ctx.run_dir / "A2" / "train" / "cells"
    assert rec["status"] == "completed" and (root / cell.label / "train.json").is_file() and not (root / f"{cell.label}.partial").exists()
    assert set(rec["snapshot_sha256"]) == {"4", "8", "16"} and (root / cell.label / "snapshots" / s1core.snapshot_stem(16) / "model.pt").is_file()
    assert adapter.train_bridge_cell(ctx, cell.label, cells)["snapshot_sha256"] == rec["snapshot_sha256"]  # a finished cell is not trained again
    # a killed run leaves a partial directory: the next run removes it and trains the same cell again with the same settings
    spec2 = {**spec, "draw": 2, "init_seed": 330699}
    cell2 = s1core.make_cell("P", "F-OQ", FACTS, 1024, 2, 330699, u_p=8, run_updates=16)
    (root / f"{cell2.label}.partial" / "snapshots").mkdir(parents=True)
    (root / f"{cell2.label}.partial" / "stale").write_text("killed", encoding="utf-8")
    adapter.train_bridge_cell(ctx, cell2.label, {cell2.label: spec2})
    assert not (root / f"{cell2.label}.partial").exists() and not (root / cell2.label / "stale").exists()
    # a failure is kept and the cell is not re-run
    cell3 = s1core.make_cell("P", "T-OQ", FACTS, 1024, 1, 330698, u_p=8, run_updates=16)
    spec3 = {**spec, "arm": "T-OQ"}
    monkeypatch.setattr(adapter, "run_cell", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        adapter.train_bridge_cell(ctx, cell3.label, {cell3.label: spec3})
    assert (root / f"{cell3.label}.failed.json").is_file()
    with pytest.raises(RuntimeError, match="failed before and is kept"):
        adapter.train_bridge_cell(ctx, cell3.label, {cell3.label: spec3})
    wrong = {**spec, "init_seed": 330698, "draw": 1}
    with pytest.raises(ValueError, match="label"):
        adapter.train_bridge_cell(ctx, cell.label.replace("d1", "d4"), {cell.label.replace("d1", "d4"): wrong})


def test_the_seed_check_at_the_point_of_training() -> None:
    """Audit A4: the adapter checks the seeds of the cell it is about to train, not only the plan's items."""
    good = {"seed_name": "p10ir-bridge-2", "seed_base": 290101, "draw": 2, "init_seed": 330602}
    adapter.assert_seed_allowed("registered", good, CFG)
    for bad in (
        {**good, "seed_base": 290001},  # another draw's set
        {**good, "seed_name": "p10s1-draw-2", "seed_base": 210101},  # P10-S1's registered draw
        {**good, "init_seed": 2102},  # P10-S1's initialisation seed
        {**good, "seed_base": 297101},  # outside the registry's bridge range (the set's index seed would be 297161)
    ):
        with pytest.raises(ValueError, match="refused"):
            adapter.assert_seed_allowed("registered", bad, CFG)
    test_spec = {"seed_name": "p10ir-test-3", "seed_base": 938301, "draw": 1, "init_seed": 330698}
    adapter.assert_seed_allowed("rehearsal", test_spec, CFG)
    adapter.assert_seed_allowed("rehearsal", {"seed_name": "p10ir-rehearsal", "seed_base": 299201, "draw": 1, "init_seed": 330692}, CFG)
    for bad in ({**test_spec, "seed_base": 290101}, {**test_spec, "seed_base": 210001}, {**test_spec, "init_seed": 330601}):
        with pytest.raises(ValueError, match="refused"):
            adapter.assert_seed_allowed("rehearsal", bad, CFG)
