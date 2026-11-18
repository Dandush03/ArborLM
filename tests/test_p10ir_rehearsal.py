# ruff: noqa: E501
"""P10IR rehearsal tests (ADR-0029 section 13): every registered stage's code path end to end against a plan of its own on a synthetic memory (tiny sizes, the unit-test seeds, a random backbone), with the
miniature P10-S1 run made by P10-S1's OWN training and evaluation functions; the real-size phase's code path at tiny sizes; gates 1 and 2 on a miniature standing in for the registered checkpoints, with the
sealed values untouched. Nothing here reads a registered checkpoint, a registered seed or the experiments directory. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10ir import (  # noqa: E402
    core,
    gates,
    items,
    labels,
    rehearsal,
    report,
    runner,
    sealed,
    stages,
)
from studies.p10ir import plan as planmod
from studies.p10ir.plan import Plan  # noqa: E402
from studies.p10s1 import train as s1train  # noqa: E402

CFG = core.load_config()
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def synthetic_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """The synthetic phase with the five replicates (the denominator of every label is 5), run once: seven stages, inline."""
    root = tmp_path_factory.mktemp("rehearsal") / "synthetic"
    res = rehearsal.run_synthetic(root, draws=5, repo=ROOT, inline=True)
    return {"root": root, "result": res, "plan": Plan.load(root / "freeze" / "plan.json")}


def test_every_stage_runs_to_complete_against_the_rehearsals_own_plan(synthetic_run: dict[str, Any]) -> None:
    res = synthetic_run["result"]
    assert list(res["stages"]) == list(stages.REHEARSAL_STAGES)
    assert all(v["status"] == "COMPLETE" for v in res["stages"].values()), res
    root: Path = synthetic_run["root"]
    for s in stages.REHEARSAL_STAGES:
        m = runner.read_manifest(root, s)
        assert m is not None and m["status"] == "COMPLETE" and m["mode"] == "rehearsal" and m["identity"]["plan_sha256"] == synthetic_run["plan"].sha256()
    assert (root / "report" / "REPORT.md").is_file() and (root / "analysis" / "analysis.json").is_file()


def test_items_come_from_the_rehearsals_plan_and_every_planned_read_exists_or_is_not_applicable(synthetic_run: dict[str, Any]) -> None:
    plan: Plan = synthetic_run["plan"]
    root: Path = synthetic_run["root"]
    assert len(plan.items("A1")) == 5 * 2 * 2 * 4 and len(plan.items("A2")) == 5 * 2 * 2 * 2
    for stage in ("A1", "A2"):
        for it in plan.items(stage):
            rec = items.Recorder(items.Ctx("rehearsal", root, root / "s1", None), it)
            assert rec.complete(), it["id"]
            for r in it["reads"]:
                assert rec.has_read(r["name"]) == (r["status"] == "RUN"), (it["id"], r["name"])
            done = core.read_record(rec.dir / "item.json", "item")
            assert [x["name"] for x in done["not_applicable"]] == [r["name"] for r in it["reads"] if r["status"] != "RUN"]


def test_every_gate_of_every_item_passes_on_records_made_by_p10s1s_own_code(synthetic_run: dict[str, Any]) -> None:
    """Gate 2 (T0 through the common path, F0 and I256@512 equal P10-S1's recorded counts; the index hash), gate 3 (the recall quantities, here of the rehearsal's own records), gate 4 and the index rebuild:
    all pass on the platform of record; elsewhere the bit-exact ones are skipped and the tolerance gates pass."""
    plan: Plan = synthetic_run["plan"]
    root: Path = synthetic_run["root"]
    seen: set[str] = set()
    for stage in ("A1", "A2"):
        for it in plan.items(stage):
            gs = core.read_record(items.Recorder(items.Ctx("rehearsal", root, root / "s1", None), it).dir / "item.json", "item")["gates"]
            seen |= set(gs)
            for name, g in gs.items():
                assert g["passed"] in (True, None), (it["id"], name, g)
                if gates.on_platform_of_record(CFG):
                    assert g["passed"] is True, (it["id"], name, g)
            if it["arm"] == "T-OQ" and stage == "A1" and it["update"] == it["u_p"]:
                assert "tree_recall_reproduction" in gs  # gate 3(a) at U_P only
            if it["arm"] == "F-OQ" and stage == "A1":
                assert "ivf_recall_reproduction" in gs  # gate 3(b) at every checkpoint read
            if stage == "A2":
                assert not any("recall" in n for n in gs)  # fresh checkpoints have no recorded recall: gate 3 does not apply
                assert all(g["source"].startswith("P10-S1's evaluation functions called from the adapter") for n, g in gs.items() if n.endswith("_counts") and "source" in g)
    assert {"checkpoint_identity", "t0_path", "t0_counts", "f0_counts", "i256_counts", "index_rebuild_i256", "tv1_priors_on_against_off", "t3_against_independent_flat", "t2_against_independent_flat"} <= seen
    assert {f"index_rebuild_i64_s{s}" for s in core.i64_seeds(CFG)} <= seen


def test_a2_gates_include_the_adapter_identity_gate_and_stop_before_training_on_a_failure(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    root: Path = synthetic_run["root"]
    g = core.read_record(stages.gates_record_path(root, "gates-a2"), "gates_record")
    assert g["passed"] is True and set(g["gates"]) == {"gate1_identities", "gate5_rehearsal", "gate6_seeds", "adapter_identity"}
    assert g["gates"]["adapter_identity"]["passed"] in (True, None) and "cells" in g["gates"]["adapter_identity"] or g["gates"]["adapter_identity"]["status"] == "skipped"
    # a gates record that did not pass stops the stage before any training or reading
    bad = {**core.envelope("gates_record"), "stage": "gates-a2", "passed": False, "failed": ["adapter_identity"]}
    core.write_record(stages.gates_record_path(tmp_path, "gates-a2"), bad)
    with pytest.raises(planmod.StageRefused, match="did not all pass"):
        stages.require_gates_passed(tmp_path, "gates-a2")
    with pytest.raises(planmod.StageRefused, match="no gates record"):
        stages.require_gates_passed(tmp_path, "gates-a1")


def test_a2_reads_need_the_training_stage_complete_and_a_completed_stage_is_not_rerun(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    plan: Plan = synthetic_run["plan"]
    root: Path = synthetic_run["root"]
    ctx = stages.ctx_for(plan, root, run_sealed=True, experiments_root=None)
    with pytest.raises(planmod.StageRefused, match="is COMPLETE"):
        stages.execute_stage("a1", plan, ctx, root, root / "freeze" / "plan.json", repo=ROOT, workers=1, inline=True)
    # a fresh run directory with the same plan but no a2-train manifest: a2 refuses
    other = tmp_path / "other"
    stages_io_dir = other / "gates-a2"
    stages_io_dir.mkdir(parents=True)
    core.write_record(stages.gates_record_path(other, "gates-a2"), {**core.envelope("gates_record"), "passed": True, "failed": []})
    ctx2 = items.Ctx("rehearsal", other, root / "s1", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64})
    with pytest.raises(planmod.StageRefused, match="a2-train is not COMPLETE"):
        stages.execute_stage("a2", plan, ctx2, other, root / "freeze" / "plan.json", repo=ROOT, workers=1, inline=True)


def test_the_analysis_and_report_of_the_rehearsal_are_well_formed_and_make_no_claim(synthetic_run: dict[str, Any]) -> None:
    root: Path = synthetic_run["root"]
    full = json.loads((root / "analysis" / "analysis.json").read_text(encoding="utf-8"))
    a1 = full["A1"]
    assert set(a1["cells"]) == {"128/1K", "128/4K"} and a1["stage_tag"] == core.A1_TAG and full["A2"]["stage_tag"] == core.A2_TAG
    assert set(full["r_confirm"]) == {"R-CONFIRM-TREE", "R-CONFIRM-INDEX"}
    for cell in a1["cells"].values():
        assert set(cell["checkpoints"]) == {"U_P", "RUN", "TRAJ1", "TRAJ2"}
        for ck in cell["checkpoints"].values():
            for comp in ("tree", "index"):
                assert ck[comp]["label"] in (*labels.TREE_ROWS, *labels.INDEX_ROWS, labels.MIXED)
                assert len(ck[comp]["replicates"]) == 5 and all(r["draw"] in (1, 2, 3, 4, 5) for r in ck[comp]["replicates"])
    # every replicate is evaluable (all gates passed): an untrained 16-update memory is at chance, so F0 is a WEAK REFERENCE and the label is NOT EVALUABLE for that reason, not for a gate
    reasons = {r["reason"] for c in a1["cells"].values() for ck in c["checkpoints"].values() for r in ck["tree"]["replicates"] if r["row"] == labels.NOT_EVALUABLE}
    assert reasons <= {labels.WEAK, ""} or all("gate" not in x for x in reasons)
    text = (root / "report" / "REPORT.md").read_text(encoding="utf-8")
    assert core.LIMIT_SENTENCE in text and "unproven research" in text and "Astra review: NOT_PERFORMED" in text and "R-DIAGNOSIS-LOADED" in text
    assert report.HEADER in text and "success" not in text.lower().replace("not a success", "")
    ledger = json.loads(next(root.parent.glob("P10IR-rehearsal-*ledger.json")).read_text(encoding="utf-8"))
    assert {e["stage"] for e in ledger["entries"]} == set(stages.REHEARSAL_STAGES) and ledger["total_seconds"] == 8 * 3600.0


def test_gates_1_and_2_run_on_a_stand_in_for_the_registered_checkpoints_and_never_touch_a_sealed_value(synthetic_run: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan: Plan = synthetic_run["plan"]
    root: Path = synthetic_run["root"]

    def forbidden(*a: Any, **k: Any) -> bool:
        raise AssertionError("a sealed value was compared before the freeze")

    monkeypatch.setattr(sealed, "sealed_equal", forbidden)
    names = [rehearsal._mini_seed_a1(d)["name"] for d in range(5)]
    res = rehearsal.run_gates12(
        tmp_path / "g12", root / "s1", repo=ROOT, workers=0, plan_items=plan.items("A1"), synthetic=True, sizes={"table_facts": 512, "unseen": 64}, draw_names=names,
        identity={"cells": [tuple(c) for c in plan.data["identity_gate_cells"]], "seeds_of": stages._mini_seeds_of(plan), "updates": plan.data["identity_gate_updates"]},
    )  # fmt: skip
    assert res["gate3_run"] is False and res["items_done"] == res["items_expected"] == 80
    if gates.on_platform_of_record(CFG):
        assert res["gate1_passed"] is True and res["gate2_passed"] is True and res["adapter_identity"]["passed"] is True
    # gate 5 reads that record: with every stage complete it passes; without gates 1 and 2 on the registered checkpoints it does not
    record = {"stages": {s: {"status": "COMPLETE"} for s in stages.REHEARSAL_STAGES}, "registered_checkpoint_gates": res}
    assert gates.rehearsal_gate(record, stages.REHEARSAL_STAGES)["passed"] is gates.on_platform_of_record(CFG)
    assert gates.rehearsal_gate({"stages": record["stages"]}, stages.REHEARSAL_STAGES)["passed"] is False


def test_gates_1_and_2_fail_closed_when_a_checkpoint_differs(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    if not gates.on_platform_of_record(CFG):
        pytest.skip("bit-exact gates run on macOS arm64 only")
    import shutil

    plan: Plan = synthetic_run["plan"]
    root: Path = synthetic_run["root"]
    copy = tmp_path / "s1copy"
    shutil.copytree(root / "s1", copy)
    one = next(i for i in plan.items("A1") if i["arm"] == "T-OQ" and i["update"] == i["u_p"])
    pt = copy / "cells" / one["cell"] / "snapshots" / "u0000008" / "model.pt"
    import torch

    payload = torch.load(pt, weights_only=True, map_location="cpu")
    payload["model"]["addition.keys"] = payload["model"]["addition.keys"] * 1.0001
    pt.chmod(0o644)
    torch.save(payload, pt)
    ctx = items.Ctx("rehearsal", tmp_path / "run", copy, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64})
    got = items.run_gates12_item(ctx, one)
    assert got["identity"]["passed"] is False and got["passed"] is False  # the file no longer hashes to its snapshot record


def test_the_real_size_phase_code_path_at_tiny_sizes(tmp_path: Path) -> None:
    """``rehearsal.run_real`` through the stages (gates-a1, a1, gates-a2, a2-train, a2) on one tree cell and one flat cell, at tiny sizes on a unit-test seed set and a random backbone (the rehearsal proper uses
    32,768 facts, 16,384 slots and the rehearsal draw)."""
    s1train.configure()
    cfg = json.loads(json.dumps(dict(CFG)))
    cfg["rehearsal"].update({"facts": 128, "slots": 1024, "snapshots": [8, 16]})
    res = rehearsal.run_real(tmp_path / "real", repo=ROOT, workers=1, inline=True, cfg=cfg, synthetic=True, seeds=core.test_seeds(6), init=330699, sizes={"table_facts": 512, "unseen": 64})
    assert all(v["status"] == "COMPLETE" for v in res["stages"].values()) and list(res["stages"]) == ["gates-a1", "a1", "gates-a2", "a2-train", "a2"]
    assert res["facts"] == 128 and res["slots"] == 1024
    keys = list(res["seconds_per_read"])
    assert any("|T0" in k for k in keys) and any("|F0" in k for k in keys) and any("A2|" in k for k in keys) and all(v >= 0 for v in res["seconds_per_read"].values())
    assert set(res["peak_rss_bytes_by_stage"]) == set(res["stages"])


def test_rehearse_command_refuses_a_non_empty_directory_and_an_unknown_phase(tmp_path: Path) -> None:
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "f").write_text("1", encoding="utf-8")
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "x")]) == 2
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "y"), "--phases", "nope"]) == 2
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "z"), "--phases", "gates12"]) == 2  # needs --s1-run-dir
