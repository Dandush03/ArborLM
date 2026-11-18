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
    assert list(res["stages"]) == list(stages.REHEARSAL_STAGES) and "confirm" in res["stages"]
    assert all(v["status"] == "COMPLETE" for v in res["stages"].values()), res
    assert res["item_errors"] == []  # no worker code raised inside an item (those are recorded as item_error gates, and would otherwise pass as 'complete')
    root: Path = synthetic_run["root"]
    for s in stages.REHEARSAL_STAGES:
        m = runner.read_manifest(root, s)
        assert m is not None and m["status"] == "COMPLETE" and m["mode"] == "rehearsal" and m["identity"]["plan_sha256"] == synthetic_run["plan"].sha256()
    assert (root / "report" / "REPORT.md").is_file() and (root / "analysis" / "analysis.json").is_file() and (root / "confirm" / "confirm.json").is_file()


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
    assert {f"index_rebuild_i64_s{s}" for s in core.i64_seeds(CFG, test=True)} <= seen
    assert not any(str(x) in n for x in core.i64_seeds(CFG) for n in seen)  # the rehearsal never reads an index with a registered index seed


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


def test_the_analysis_of_the_rehearsal_uses_the_plans_labels_finds_every_record_and_reaches_rows(synthetic_run: dict[str, Any]) -> None:
    """Audit R2: the analysis takes the plan's labels (the rehearsal's items are not the config's derivation), so every replicate is found; the memories are trained past the information floor, so rows other
    than NOT EVALUABLE are reached; and no replicate may say 'no item record'."""
    root: Path = synthetic_run["root"]
    full = json.loads((root / "analysis" / "analysis.json").read_text(encoding="utf-8"))
    a1 = full["A1"]
    assert set(a1["cells"]) == {"128/1K", "128/4K"} and a1["stage_tag"] == core.A1_TAG
    assert full["A2"] is None and {v["value"] for v in full["r_confirm"].values()} == {"NOT RUN"}  # A1's record never holds R-CONFIRM: the confirm stage computes it
    reps = [(ck, comp, r) for c in a1["cells"].values() for ck in c["checkpoints"].values() for comp in ("tree", "index") for r in ck[comp]["replicates"]]
    assert len(reps) == 2 * 4 * 2 * 5
    assert not any("no item record" in r["reason"] for _, _, r in reps)
    rows = {r["row"] for _, _, r in reps}
    assert rows - {labels.NOT_EVALUABLE}, rows  # at least one row other than NOT EVALUABLE
    assert any(r["row"] not in (labels.NOT_EVALUABLE,) for ck, comp, r in reps if ck["update"] in (48, 64))
    for c in a1["cells"].values():
        assert set(c["checkpoints"]) == {"U_P", "RUN", "TRAJ1", "TRAJ2"} and c["checkpoints"]["U_P"]["update"] == 48 and c["checkpoints"]["RUN"]["update"] == 64
        for ck in c["checkpoints"].values():
            for comp in ("tree", "index"):
                assert ck[comp]["label"] in (*labels.TREE_ROWS, *labels.INDEX_ROWS, labels.MIXED) and len(ck[comp]["replicates"]) == 5
    synth = synthetic_run["result"]["synthetic_registry"]
    assert synth["status"] == "COMPLETE" and not synth["A1"]["no_item_record"] and not synth["A2"]["no_item_record"]
    assert len(set(synth["A1"]["rows_reached"]) - {labels.NOT_EVALUABLE}) >= 8  # the synthetic registry keyed by the plan's own labels reaches the rows
    assert {"NOT RUN"} != set(synth["r_confirm"].values())
    text = (root / "report" / "REPORT.md").read_text(encoding="utf-8")
    assert core.LIMIT_SENTENCE in text and "unproven research" in text and "Astra review: NOT_PERFORMED" in text and "R-DIAGNOSIS-LOADED" in text and "accuracy version" in text
    assert report.HEADER in text and "success" not in text.lower().replace("not a success", "")
    ledger = json.loads(next(root.parent.glob("P10IR-rehearsal-*ledger.json")).read_text(encoding="utf-8"))
    assert {e["stage"] for e in ledger["entries"]} == set(stages.REHEARSAL_STAGES) and ledger["total_seconds"] == 8 * 3600.0


def test_the_confirm_stage_writes_its_own_record_against_a1s_frozen_one_and_never_rewrites_it(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    from arborlm.io import file_sha256

    root: Path = synthetic_run["root"]
    plan: Plan = synthetic_run["plan"]
    a1 = stages.analysis_path(root)
    rec = core.read_record(stages.confirm_path(root), "confirm")
    assert rec["a1_analysis_sha256"] == file_sha256(a1)  # A1's record is what it was when the confirmation read it
    assert set(rec["r_confirm"]) == {"R-CONFIRM-TREE", "R-CONFIRM-INDEX"} and rec["A2"]["stage_tag"] == core.A2_TAG and rec["A2"]["cells"].keys() == {"128/1K", "128/4K"}
    assert all(v["value"] in ("CONFIRMED", "NOT CONFIRMED", "NOT EVALUABLE", "NOT APPLICABLE") for v in rec["r_confirm"].values())
    text = (root / "confirm" / "REPORT_CONFIRM.md").read_text(encoding="utf-8")
    assert "R-CONFIRM-TREE" in text and "R-CONFIRM-INDEX" in text and rec["a1_analysis_sha256"] in text and core.A2_TAG in text and "Astra review: NOT_PERFORMED" in text
    m = runner.read_manifest(root, "confirm")
    assert m is not None and m["status"] == "COMPLETE" and runner.read_manifest(root, "analysis")["status"] == "COMPLETE"  # type: ignore[index]
    ctx = stages.ctx_for(plan, root, run_sealed=True, experiments_root=None)
    before = file_sha256(a1)
    with pytest.raises(planmod.StageRefused, match="is COMPLETE"):
        stages.execute_stage("confirm", plan, ctx, root, root / "freeze" / "plan.json", repo=ROOT, workers=1, inline=True)
    with pytest.raises(planmod.StageRefused, match="is COMPLETE"):
        stages.execute_stage("analysis", plan, ctx, root, root / "freeze" / "plan.json", repo=ROOT, workers=1, inline=True)
    assert file_sha256(a1) == before
    # it needs A2 complete and A1's analysis: a run directory without them refuses
    with pytest.raises(planmod.StageRefused, match="is not COMPLETE"):
        stages.execute_stage("confirm", plan, ctx, tmp_path, root / "freeze" / "plan.json", repo=ROOT, workers=1, inline=True)


def test_confirm_computes_every_value_against_the_written_json_of_a1() -> None:
    """The comparison goes through A1's written record (JSON turns tuples into lists): CONFIRMED and NOT CONFIRMED survive the round trip, CELL-DEPENDENT included."""
    from studies.p10ir import analysis, synthetic

    cfg = core.load_config()
    specs = [s for s in core.cell_specs(cfg) if s.role == "primary"]

    def diag(stage: str, tree_b: str) -> Any:
        plan_rows = {(s.name, cp): ((labels.PRIORS if not (s.name == "32K/16K" and cp == "RUN") else tree_b), labels.NOT_APPROACH) for s in specs for cp in ("U_P", "RUN")}
        reg = synthetic.full_registry(stage, plan_rows, cfg, lambda arm, sp, d: f"L_{arm}_{sp.name}_{d}", specs=specs, i64_seeds=core.i64_seeds(cfg, test=True))
        return analysis.analyze_stage(reg, stage, cfg, specs=specs, label_of=lambda arm, sp, d: f"L_{arm}_{sp.name}_{d}", i64_seeds=core.i64_seeds(cfg, test=True))

    a1 = json.loads(json.dumps(analysis.public(diag("A1", labels.CONTENT)), default=str))
    same = labels.r_confirm(labels.diagnosis_from_json(a1["r_diagnosis"]), diag("A2", labels.CONTENT)["_diagnosis_object"])
    assert same["R-CONFIRM-TREE"]["value"] == labels.CONFIRMED and same["R-CONFIRM-INDEX"]["value"] == labels.CONFIRMED
    assert a1["r_diagnosis"]["components"]["tree"]["value"] == labels.CHECKPOINT_DEPENDENT  # PRIORS at U_P in both cells, CELL-DEPENDENT at the run length: the ruled reading
    other = labels.r_confirm(labels.diagnosis_from_json(a1["r_diagnosis"]), diag("A2", labels.JOINT)["_diagnosis_object"])
    assert other["R-CONFIRM-TREE"]["value"] == labels.NOT_CONFIRMED and other["R-CONFIRM-INDEX"]["value"] == labels.CONFIRMED


def test_gate_1_runs_for_every_checkpoint_in_the_gates_stage_and_stops_the_stage(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    """Ruling 8 (audit R1): the identity links of section 4, for all checkpoints, before any read: file = snapshot.json = train.json entry = plan digest; train.json = the committed train manifest's
    result_sha256; the data manifests = P10-S1's frozen data_manifests; the draws regenerated. A difference fails the gates stage, and the read stage then refuses."""
    import shutil

    root: Path = synthetic_run["root"]
    plan: Plan = synthetic_run["plan"]
    g = core.read_record(stages.gates_record_path(root, "gates-a1"), "gates_record")["gates"]["gate1_identities"]
    assert g["passed"] is True and g["checkpoints_checked"] == 80 and g["failed"] == [] and g["draws_regenerated"] == 5 and all(g["manifests"].values())
    ctx = stages.ctx_for(plan, root, run_sealed=False, experiments_root=None)
    assert stages.gate1_all(plan, ctx, core.STAGE_A1, ROOT)["passed"] is True
    copy = tmp_path / "copy"
    shutil.copytree(root / "s1", copy / "s1")
    ctx2 = items.Ctx("rehearsal", tmp_path / "run", copy / "s1", None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, manifests=ctx.manifests)
    cell = plan.items("A1")[0]["cell"]
    # (a) train.json no longer hashes to the committed train manifest
    tj = copy / "s1" / "cells" / cell / "train.json"
    tj.write_text(tj.read_text(encoding="utf-8") + " ", encoding="utf-8")
    bad = stages.gate1_all(plan, ctx2, core.STAGE_A1, ROOT)
    assert bad["passed"] is False and any("train.json" in f for f in bad["failed"])
    # (b) a data manifest does not hash to P10-S1's frozen data_manifests entry
    other = json.loads(json.dumps(plan.data))
    name = next(iter(other["p10s1_frozen_data_manifests"]))
    other["p10s1_frozen_data_manifests"][name] = "0" * 64
    bad2 = stages.gate1_all(Plan(other), ctx, core.STAGE_A1, ROOT)
    assert bad2["passed"] is False and any("frozen data_manifests" in f for f in bad2["failed"])
    # (c) a plan digest that is not the file's
    other2 = json.loads(json.dumps(plan.data))
    k = next(iter(other2["checkpoint_digests"]))
    other2["checkpoint_digests"][k] = "1" * 64
    assert stages.gate1_all(Plan(other2), ctx, core.STAGE_A1, ROOT)["passed"] is False
    # (d) a failed gates record stops the read stage
    failed = {**core.envelope("gates_record"), "stage": "gates-a1", "passed": False, "failed": ["gate1_identities"]}
    core.write_record(stages.gates_record_path(tmp_path, "gates-a1"), failed)
    with pytest.raises(planmod.StageRefused, match="did not all pass"):
        stages.execute_stage("a1", plan, ctx, tmp_path, root / "freeze" / "plan.json", repo=ROOT, workers=1, inline=True)


def _copy_run(synthetic_run: dict[str, Any], tmp_path: Path) -> tuple[Plan, Path, items.Ctx, list[dict[str, Any]]]:
    import shutil

    root: Path = synthetic_run["root"]
    plan: Plan = synthetic_run["plan"]
    copy = tmp_path / "s1"
    shutil.copytree(root / "s1", copy)
    its = [i for i in plan.items("A1") if i["cell"] == plan.items("A1")[0]["cell"]]
    ctx = items.Ctx("rehearsal", tmp_path / "run", copy, None, synthetic=True, run_sealed=True, sizes={"table_facts": 512, "unseen": 64}, manifests=stages.ctx_for(plan, root, run_sealed=True, experiments_root=None).manifests, index_seeds=plan.data["i64_seeds"])
    return plan, copy, ctx, its


def test_a_missing_or_changed_checkpoint_pauses_identity_and_records_nothing_and_resumes_when_restored(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    """N1: an identity failure during the run is not a scientific NOT EVALUABLE. The item raises StageRefused (the worker exits 75: PAUSED — IDENTITY); no item or gate file is written, so restoring the file lets the task resume."""
    plan, copy, ctx, its = _copy_run(synthetic_run, tmp_path)
    victim = its[0]
    pt = copy / "cells" / victim["cell"] / "snapshots" / s1stem(victim["update"]) / "model.pt"
    good = pt.read_bytes()
    pt.unlink()  # a missing checkpoint file
    with pytest.raises(planmod.StageRefused, match="PAUSED — IDENTITY"):
        items.run_item(ctx, victim, plan.data["checkpoint_digests"])
    rec = items.Recorder(ctx, victim)
    assert not rec.complete() and not rec.has_gate("checkpoint_identity") and not rec.has_gate("item_error")
    pt.write_bytes(b"not the checkpoint")  # a changed one
    with pytest.raises(planmod.StageRefused, match="PAUSED — IDENTITY"):
        items.run_item(ctx, victim, plan.data["checkpoint_digests"])
    assert not rec.complete()
    pt.write_bytes(good)  # restored bit for bit
    done = items.run_item(ctx, victim, plan.data["checkpoint_digests"])
    assert done["complete"] is True and "item_error" not in done["gates"] and done["gates"]["checkpoint_identity"]["passed"] is True
    # the data identity: a draw that does not equal its manifest is the same kind of refusal
    bad_manifest = tmp_path / "manifest.json"
    bad_manifest.write_text(json.dumps({"sha256s": {"facts": "0"}}), encoding="utf-8")
    ctx.manifests[victim["seed_name"]] = bad_manifest
    with pytest.raises(planmod.StageRefused, match="differs from the hashes"):
        items.load_data(ctx, victim)


def test_a_missing_checkpoint_makes_the_worker_exit_75_and_the_task_paused(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    import sys as _sys

    plan, copy, ctx, its = _copy_run(synthetic_run, tmp_path)
    label = its[0]["cell"]
    (copy / "cells" / label / "snapshots" / s1stem(its[0]["update"]) / "model.pt").unlink()
    data = json.loads(json.dumps(plan.data))
    data["s1_run_dir"] = str(copy)
    data["run_dir"] = str(tmp_path / "run")
    pf = tmp_path / "plan.json"
    core.write_record(pf, data)
    argv = (_sys.executable, "-m", "studies.p10ir.stages", "work", "reads", "--stage", "a1", "--labels", label, "--run-dir", str(tmp_path / "run"), "--plan", str(pf), "--mode", "rehearsal")
    task = runner.Task(label, argv, tmp_path / "run" / "a1" / "tasks" / "x.done.json", tmp_path / "run" / "a1" / "tasks" / "x.failed.json", tmp_path / "run" / "a1" / "tasks" / "x.log")
    out, _ = runner.run_tasks([task], workers=1, cap_seconds=300.0, rss_worker_bytes=1 << 31, rss_aggregate_bytes=1 << 33, env={"PYTHONPATH": str(ROOT)})
    assert out[label]["returncode"] == 75 and out[label]["status"] == runner.PAUSED_IDENTITY and runner.stage_status(out) == "PAUSED" and not task.failed_path.exists()


def test_an_environment_error_propagates_and_is_not_recorded_as_not_evaluable(synthetic_run: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan, _, ctx, its = _copy_run(synthetic_run, tmp_path)
    item = its[1]

    def boom(*a: Any, **k: Any) -> Any:
        raise OSError("disk went away")

    monkeypatch.setattr(items, "load_model", boom)
    with pytest.raises(OSError):
        items.run_item(ctx, item, plan.data["checkpoint_digests"])
    monkeypatch.setattr(items, "load_model", lambda *a, **k: (_ for _ in ()).throw(MemoryError()))
    with pytest.raises(MemoryError):
        items.run_item(ctx, item, plan.data["checkpoint_digests"])
    assert not items.Recorder(ctx, item).complete()


def test_a_gate_4_failure_makes_that_replicate_not_evaluable_only_and_a_code_error_is_counted(synthetic_run: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """N1: only the scientific gate failures of section 11 make a replicate NOT EVALUABLE; a remaining code error inside an item is an item_error, counted in the manifest and the report."""
    from studies.p10ir import registry

    plan, _, ctx, its = _copy_run(synthetic_run, tmp_path)
    tree = next(i for i in its if i["arm"] == "T-OQ")
    names = ("tv1_priors_on_against_off", "t3_against_independent_flat", "t2_against_independent_flat")
    monkeypatch.setattr(gates, "exactness_gates", lambda *a, **k: {n: gates.gate("tree", False, not_float_ties=3) for n in names})
    done = items.run_item(ctx, tree, plan.data["checkpoint_digests"])
    assert done["complete"] and "item_error" not in done["gates"] and all(done["gates"][n]["passed"] is False for n in names)
    assert registry.scope_ok(done, "tree")[0] is False and registry.scope_ok(done, "f0")[0] is True and registry.scope_ok(done, "index")[0] is True
    monkeypatch.undo()
    flat = next(i for i in plan.items("A1") if i["arm"] == "F-OQ" and i["cell"] == tree["cell"].replace("T-OQ", "F-OQ") and i["update"] == tree["update"])
    monkeypatch.setattr(items.reads, "read_counts", lambda *a, **k: (_ for _ in ()).throw(ValueError("a code error")))
    err = items.run_item(ctx, flat, plan.data["checkpoint_digests"])
    assert err["gates"]["item_error"]["passed"] is False and "ValueError" in err["gates"]["item_error"]["error"]
    errors = stages.item_errors(tmp_path / "run", "A1")
    assert len(errors) == 1 and "ValueError" in errors[0]
    from studies.p10ir import analysis, report, synthetic

    cfg = core.load_config()
    a = analysis.analyze_all(analysis.analyze_stage(synthetic.full_registry("A1", None, cfg, lambda arm, sp, d: f"X{arm}{sp.name}{d}", i64_seeds=core.i64_seeds(cfg, test=True)), "A1", cfg, label_of=lambda arm, sp, d: f"X{arm}{sp.name}{d}", i64_seeds=core.i64_seeds(cfg, test=True)), None)
    assert "ITEM ERRORS" not in report.render(a)
    a["item_errors"] = errors
    assert "ITEM ERRORS (worker code raised inside an item; counted apart from gate failures): 1" in report.render(a)


def test_the_stage_manifest_counts_item_errors(synthetic_run: dict[str, Any]) -> None:
    root: Path = synthetic_run["root"]
    for stage in ("a1", "a2"):
        m = runner.read_manifest(root, stage)
        assert m is not None and m["item_errors"] == 0 and m["clean"] is True and m["item_error_list"] == []


def s1stem(update: int) -> str:
    from studies.p10s1 import core as s1

    return s1.snapshot_stem(update)


def test_a_gate_that_raises_is_recorded_failed_with_its_scope() -> None:
    """``items.guarded``: an exception inside one gate fails that gate only; a gate already recorded is not recomputed."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ctx = items.Ctx("rehearsal", Path(tmp), None, None)
        rec = items.Recorder(ctx, {"stage": "A1", "id": "A1|c|u0000001", "cell": "c", "update": 1})
        items.guarded(rec, "boom", "index", lambda: (_ for _ in ()).throw(KeyError("x")))
        items.guarded(rec, "fine", "tree", lambda: gates.gate("tree", True))
        items.guarded(rec, "boom", "index", lambda: gates.gate("index", True))  # already on disk: not recomputed
        got = rec.all_gates()
        assert got["boom"]["passed"] is False and got["boom"]["scope"] == "index" and "KeyError" in got["boom"]["error"] and got["fine"]["passed"] is True


def test_the_candidate_phase_fails_closed_on_a_plan_that_is_not_the_registered_one(synthetic_run: dict[str, Any], tmp_path: Path) -> None:
    """Ruling 5: the candidate phase rehearses the plan FILE. A plan whose items are not the registered derivation, or whose files are missing, is INCOMPLETE with its problems listed; a rehearsal plan is refused."""
    plan: Plan = synthetic_run["plan"]
    with pytest.raises(planmod.StageRefused, match="registered plan"):
        rehearsal.run_candidate(tmp_path / "c1", repo=ROOT, plan_path=synthetic_run["root"] / "freeze" / "plan.json")
    data = json.loads(json.dumps(plan.data))
    data["mode"] = "registered"
    path = tmp_path / "candidate_plan.json"
    core.write_record(path, data)
    res = rehearsal.run_candidate(tmp_path / "c2", repo=ROOT, plan_path=path)
    assert res["status"] == "INCOMPLETE" and res["plan_file_sha256"] == planmod.file_sha256(path) and any("re-derivation" in p or "280" in p for p in res["problems"])
    assert res["synthetic_registry"]["status"] == "COMPLETE"  # the analysis, report and confirmation on a synthetic registry keyed by the plan's own labels
    assert len(set(res["synthetic_registry"]["A1"]["rows_reached"]) - {labels.NOT_EVALUABLE}) >= 8


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
    pt = copy / "cells" / one["cell"] / "snapshots" / s1stem(one["update"]) / "model.pt"
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
    assert res["facts"] == 128 and res["slots"] == 1024 and res["item_errors"] == []
    keys = list(res["seconds_per_read"])
    assert any("|T0" in k for k in keys) and any("|F0" in k for k in keys) and any("A2|" in k for k in keys) and all(v >= 0 for v in res["seconds_per_read"].values())
    assert set(res["peak_rss_bytes_by_stage"]) == set(res["stages"])


def test_rehearse_command_refuses_a_non_empty_directory_and_an_unknown_phase(tmp_path: Path) -> None:
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "f").write_text("1", encoding="utf-8")
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "x")]) == 2
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "y"), "--phases", "nope"]) == 2
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "z"), "--phases", "gates12"]) == 2  # needs --s1-run-dir
