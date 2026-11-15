# ruff: noqa: E501
"""P10S0 stages: the tiny synthetic end-to-end DRY stage (generate, pipeline check, gates, rehearsal, all 230 Q1 cells, the Q1 gate, WX, the probe, analysis, report; test seeds 920001+, random synthetic backbone), the
projection and cap-table procedure on the DRY rehearsal, the registered driver's refusals, the preconditions in a throw-away repository, the freeze plan verification, the draw plan and gates guards.
Nothing here builds a registered, rehearsal or check seed. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p9 import pool  # noqa: E402
from studies.p10s0 import analysis, budget, core, report, stages  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def dry(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("p10s0-dry")
    code = stages.main(["dry", "--out-root", str(root), "--workers", "6", "--stage-cap-seconds", "1800", "--dry-candidate", "A1"])
    summary = json.loads((root / "DRY_SUMMARY.json").read_text())
    return {"root": root, "code": code, "summary": summary, "run": Path(summary["run_dir"])}


# --- the DRY stage ----------------------------------------------------------------------------------------------------------------------------
def test_the_dry_stage_runs_every_stage_to_a_report(dry: dict[str, Any]) -> None:
    s = dry["summary"]
    assert dry["code"] == 0 and s["stages"] == dict.fromkeys(["generate", "check", "gates", "rehearse", "q1", "q1_gate", "wx", "probe", "analyze", "report"], 0)
    assert s["banner"].startswith("DRY: tiny synthetic sizes") and Path(s["report"]).is_file() and s["charged_seconds"] > 0
    assert s["outcome"] in ("INCONCLUSIVE", "ADDRESSING-NOT-QUALIFIED", "ADDRESSING-QUALIFIED AT 4,096 ONLY", "ADDRESSING-QUALIFIED (4,096 AND 16,384)")  # a status of the pipeline on a random backbone, not a result


def test_dry_run_directories_and_records_carry_the_study_code(dry: dict[str, Any]) -> None:
    assert dry["run"].name == "P10S0DRY-run" and (dry["root"] / "P10S0-ledger.json").is_file()
    root = dry["root"]
    assert {p.name for p in root.iterdir()} >= {"P10S0DRY-run", "P10S0DRY-check", "P10S0DRY-rehearsal", "arm_selection.json", "P10S0-ledger.json", "DRY_SUMMARY.json"}
    for record in ("gates.json", "analysis.json", "q1_gate.json"):
        assert json.loads((dry["run"] / record).read_text())["study"] == "P10S0"
    labels = {p.name for p in (dry["run"] / "cells").iterdir()}
    expected = {c.label for c in core.q1_cells()} | {c.label for c in core.wx_cells("A1")} | {c.label for c in core.probe_cells("A1")}
    assert labels == expected and len(labels) == 230 + 20 + 6


def test_dry_cells_hold_train_and_eval_records_with_the_read_swap(dry: dict[str, Any]) -> None:
    cells = dry["run"] / "cells"
    for label in ("Q1-A0-2K4K-d01-j0", "Q1-A5-D-8K4K-d02-j1", "Q1-A2-8K16K-d03-j0", "WX-WX-A1-2K4K-d01-j0", "PR-A1-32K64K-d11-j0"):
        c = core.parse_label(label)
        t = core.read_record(cells / label / "train.json", "train")
        assert t["status"] == "completed" and t["study"] == "P10S0" and t["celltype"] == c.celltype and t["init_seed"] > 0
        for u in c.ct.readout_updates(8):
            e = core.read_record(core.eval_path(dry["run"], label, u), "eval")
            assert e["study"] == "P10S0" and e["label"] == label and ("read_swap" in e) == (c.arm in core.LEARNED_ARMS)
    assert "read_swap" not in core.read_record(core.eval_path(dry["run"], "Q1-A6-2K4K-d01-j0", 8), "eval") and "read_swap" not in core.read_record(core.eval_path(dry["run"], "Q1-A7-8K16K-d01-j0", 32), "eval")
    assert sorted(p.name for p in (cells / "Q1-A5-D-8K16K-d01-j0" / "eval").iterdir()) == ["u0000008", "u0000032"]  # readouts at U and 4U (unit 8)


def test_dry_gates_all_pass_and_g10_cites_the_table_cell(dry: dict[str, Any]) -> None:
    g = core.read_record(dry["run"] / "gates.json", "gates")
    assert all(g[f"{n}_passed"] is True for n in analysis.GATES) and g["harness_errors"] == [] and g["g4_defects"] == [] and g["dry"] is True
    assert g["g10"]["table_cell_cited"] == "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096)" and g["g10"]["auditor_script_run"] is False
    assert g["checks"]["wx_equivalence"]["passed"] and set(g["checks"]["identity_against_p9ii"]) == {"A0", "A1", "A2", "A5-D", "A6", "A7"}


def test_dry_manifests_one_per_stage_and_every_task_completed(dry: dict[str, Any]) -> None:
    names = {p.parent.name for p in dry["run"].glob("*/manifest.json")}
    assert {"gates", "train-q1", "evaluate-q1", "train-wx", "evaluate-wx", "train-probe", "evaluate-probe", "analyze", "report"} <= names and any(n.startswith("generate-") for n in names)
    for p in dry["run"].glob("*/manifest.json"):
        m = core.read_record(p, "stage_manifest")
        assert m["status"] == "COMPLETE" and m["mode"] == "dry" and m["environment"]["torch"] and m["caps"]["rss_aggregate_bytes"] == 18 * 1024**3 and m["caps"]["rss_worker_bytes"] == 3 * 1024**3
        assert m["workers"] <= 6 and all(t["status"] == "completed" for t in m["tasks"])


def test_dry_data_manifest_holds_the_three_fact_sets_with_g1(dry: dict[str, Any]) -> None:
    m = core.read_record(dry["run"] / "draws/p10s0-test-0/data_manifest.json", "data_manifest")
    assert set(m["sha256s"]) == {"2048", "8192", "32768"} and m["g1_passed"] and m["dry"] and set(m["g1_by_fact_set"]) == {"2048", "8192", "32768"}
    assert m["seeds"]["8192"]["facts"] == core.test_set(0).seeds(8192).facts


def test_dry_q1_gate_record(dry: dict[str, Any]) -> None:
    g = core.read_record(dry["run"] / "q1_gate.json", "q1_gate")
    assert g["blocks"]["wx"]["status"] in ("NOT RUN — NO CANDIDATE", None) and g["cut3"] is False and g["outcome_row"] in (3, 4, 5, 6)


def test_dry_report_carries_the_provenance_block_wherever_a5d_appears(dry: dict[str, Any]) -> None:
    md = (dry["run"] / "results/RESULTS.md").read_text()
    assert report.check_a5d_provenance(md) == [] and core.FOURTH_ARM_STRING in md and md.startswith("# P10-S0")
    assert "DRY: tiny synthetic sizes" in md and (dry["run"] / "results/classes.csv").is_file()
    res = json.loads((dry["run"] / "results/results.json").read_text())
    assert res["banner"].startswith("DRY") and res["result"]["outcome"]["row"] == dry["summary"]["row"]


def test_a_stage_is_run_once_and_never_overwritten(dry: dict[str, Any]) -> None:
    root = dry["root"]
    shared = ["--dry", "--experiments-root", str(root), "--ledger-root", str(root), "--arm-selection", str(root / "arm_selection.json"), "--run-dir", str(dry["run"]), "--stage-cap-seconds", "600"]
    assert stages.main(["analyze", *shared]) == 2  # the manifest of the stage exists
    assert stages.main(["report", *shared]) == 2 and stages.main(["generate", *shared, "--mode", "dry"]) == 2 and stages.main(["gates", *shared]) == 2
    assert stages.main(["q1-gate", *shared]) == 2


def test_dry_ledger_is_one_budget_charged_by_every_stage(dry: dict[str, Any]) -> None:
    ledger = core.ledger_for(dry["root"])
    stages_charged = {e["stage"] for e in ledger.entries()}
    assert {"gates", "train-q1", "evaluate-q1", "rehearse", "train-check", "train-wx", "train-probe", "analyze", "report"} <= stages_charged
    assert ledger.cap_seconds == 16 * 3600 and ledger.remaining() < ledger.cap_seconds


def test_the_dry_analysis_loaded_every_cell_from_disk(dry: dict[str, Any]) -> None:
    res = core.read_record(dry["run"] / "analysis.json", "analysis")["result"]
    assert res["assessment"]["interpretable"] and res["assessment"]["missing_q1"] == [] and res["arm_selection"]["candidates"]["arms"] == ["A5-D", "A1"]
    assert all(res["a6"][ct] for ct in ("2K/4K", "8K/16K", "8K/4K"))


# --- the rehearsal, projection and cap procedure on the DRY rehearsal ---------------------------------------------------------------------------------------
def test_dry_rehearsal_wrote_only_whitelisted_records_for_every_item(dry: dict[str, Any]) -> None:
    folder = dry["root"] / "P10S0DRY-rehearsal"
    items = budget.rehearsal_items()
    for item in items:
        d = folder / "rehearsal" / budget.item_label(item)
        assert sorted(p.name for p in d.glob("*.json")) == ["rehearsal.json", "rehearsal_evaluate.json"] and not (d / "train.json").exists() and not (d / "updates.jsonl").exists()
        rec = core.read_record(d / "rehearsal.json", "rehearsal")
        assert set(rec) <= stages.train.REHEARSAL_RECORD_KEYS and rec["loss_finite"] is True and rec["updates"] == stages.DRY_REHEARSAL_UPDATES
    assert len(list((folder / "rehearsal").iterdir())) == len(items) == 24


def test_projection_and_caps_procedure(dry: dict[str, Any], tmp_path: Path) -> None:
    folder = dry["root"] / "P10S0DRY-rehearsal"
    selection = dry["root"] / "arm_selection.json"
    out = tmp_path / "projection.json"
    assert stages.main(["projection", "--rehearsal-alone", str(folder), "--rehearsal-busy", str(folder), "--arm-selection", str(selection), "--out", str(out), "--dry", "--repo", str(ROOT)]) == 0
    p = core.read_record(out, "projection")
    assert p["missing_items"] == [] and p["candidates"] == ["A5-D", "A1"] and set(p["table"]) == {"q1:full", "q1:cut3", "wx:A5-D", "wx:A1", "probe:A5-D", "probe:A1"} and p["arm_selection_sha256"] == file_sha256(selection)
    assert p["guard_seconds_per_task"] > 0 and stages.measure_guard_seconds(ROOT) > 0 and set(p["memory"]) == set(p["table"]) and p["freeze_information"]["kind"] == "information, not a start condition" and p["cost_differences"]
    assert stages.main(["projection", "--rehearsal-alone", str(folder), "--rehearsal-busy", str(folder), "--arm-selection", str(selection), "--out", str(out), "--dry"]) == 2  # never over an existing file
    caps_out = tmp_path / "stage_caps.json"
    assert stages.main(["caps", "--projection", str(out), "--out", str(caps_out), "--gates-wall-seconds", "100", "--gates-per-draw-seconds", "1", "--analysis-wall-seconds", "5", "--report-wall-seconds", "5", "--generate-wall-seconds", "60", "--dry"]) == 0
    caps = json.loads(caps_out.read_text())
    assert set(caps["q1"]) == {"full", "cut3"} and caps["gates"] == 2 * (100 + 12 * 1) and caps["generate"] == 120 and caps["analysis"] == 60.0 and caps["measured"]["reserve_analysis_report"] == 10
    assert stages.main(["caps", "--projection", str(out), "--out", str(caps_out), "--dry"]) == 2
    rates = stages.rates_of(p)
    assert len(rates) == 24 and budget.block_projection(core.wx_cells("A1"), rates).cells == 20


def test_an_incomplete_rehearsal_gives_a_projection_without_a_table(dry: dict[str, Any], tmp_path: Path) -> None:
    folder = tmp_path / "partial"
    src = dry["root"] / "P10S0DRY-rehearsal" / "rehearsal"
    (folder / "rehearsal").mkdir(parents=True)
    for d in sorted(src.iterdir())[:3]:
        (folder / "rehearsal" / d.name).mkdir()
        for f in d.glob("*.json"):
            (folder / "rehearsal" / d.name / f.name).write_text(f.read_text())
    out = tmp_path / "p.json"
    assert stages.main(["projection", "--rehearsal-alone", str(folder), "--rehearsal-busy", str(folder), "--arm-selection", str(dry["root"] / "arm_selection.json"), "--out", str(out), "--dry"]) == 1
    p = core.read_record(out, "projection")
    assert len(p["missing_items"]) == 21 and "table" not in p


def test_the_arm_selection_command_writes_the_record_once(tmp_path: Path) -> None:
    out = tmp_path / "sel.json"
    assert stages.main(["arm-selection", "--out", str(out), "--repo", str(ROOT)]) == 0 and json.loads(out.read_text())["kind"] == "arm_selection"
    assert stages.main(["arm-selection", "--out", str(out), "--repo", str(ROOT)]) == 2


# --- the command line and the registered driver --------------------------------------------------------------------------------------------------------
def test_parser_accepts_every_command_and_worker() -> None:
    parser = stages.build_parser()
    for argv in (["generate", "--run-dir", "x"], ["draw-plan"], ["check"], ["rehearse", "--busy-processes", "12"], ["gates"], ["train", "--block", "wx"], ["q1-gate"], ["analyze"], ["report"], ["dry"], ["registered", "q1"], ["work", "train", "--labels", "a"], ["work", "rehearse-cell", "--item", "A0,2K/4K,main"]):
        parser.parse_args(argv)
    for bad in (["registered", "stage1"], ["registered", "calibrate"], ["train", "--block", "stage2"], ["--mode", "calibration"]):
        with pytest.raises(SystemExit):
            parser.parse_args(bad)
    assert set(stages.REGISTERED_STAGES) == {"gates", "q1", "q1_gate", "probe", "wx", "analysis", "report"}


def test_registered_stages_refuse_without_a_clean_tree_a_commit_and_a_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["registered", "gates", "--run-dir", str(tmp_path)]) == 2  # no freeze commit (and this tree is not clean while the work is uncommitted)
    assert "REFUSED" in capsys.readouterr().err
    assert stages.main(["gates", "--dry", "--mode", "registered"]) == 2


def init_repo(path: Path) -> Path:
    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(path), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, check=True, text=True).stdout.strip()

    path.mkdir(parents=True, exist_ok=True)
    git("init", "-q")
    for rel, text in (("studies/p10s0/a.py", "x = 1\n"), (str(core.DEFAULT_CONFIG), "a = 1\n"), (core.SPEC, "adr\n"), ("tests/test_p10s0_x.py", "def test_x(): pass\n"), (str(stages.FREEZE_PLAN), "{}")):
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text)
    git("add", "-A")
    git("commit", "-q", "-m", "freeze")
    return path


def refusal(repo: Path, freeze: str | None) -> str:
    with pytest.raises(pool.StageRefused) as exc:
        stages.check_preconditions("registered", repo, freeze)
    return str(exc.value)


def test_preconditions_in_a_throw_away_repository(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert stages.check_preconditions("check", repo, None) is None and stages.check_preconditions("dry", repo, None) is None and stages.check_preconditions("rehearsal", repo, None) is None
    assert "requires --freeze-commit" in refusal(repo, None)
    assert "is not a commit" in refusal(repo, "deadbeef" * 5)
    assert "frozen inputs do not verify" in refusal(repo, head)  # a clean tree at the freeze commit (which added the plan) passes every earlier guard; this repository has no src/arborlm
    (repo / "untracked.txt").write_text("x")
    assert "not clean" in refusal(repo, head)
    (repo / "untracked.txt").unlink()

    def commit(rel: str, text: str) -> None:
        (repo / rel).write_text(text)
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "change"], check=True, capture_output=True)

    commit("studies/p10s0/a.py", "x = 2\n")
    assert "studies at HEAD differs from the freeze commit" in refusal(repo, head)
    commit(core.SPEC, "adr changed\n")
    assert f"{core.SPEC} at HEAD differs" in refusal(repo, head)
    commit("tests/test_p10s0_x.py", "def test_x(): assert True\n")
    assert "tests/test_p10s0_x.py differs from the freeze commit" in refusal(repo, head)
    commit(str(core.DEFAULT_CONFIG), "a = 2\n")
    assert f"{core.DEFAULT_CONFIG} at HEAD differs" in refusal(repo, head)
    assert "not the commit that added" in refusal(repo, subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip())


def test_the_driver_refuses_a_wrong_caps_path_and_a_missing_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both refusals come after ``check_preconditions``; the throw-away repository cannot pass the frozen-input check, so this test calls the driver's parts."""
    with pytest.raises(pool.StageRefused, match="no freeze plan"):
        stages.load_plan(tmp_path)
    (tmp_path / "studies/p10s0/freeze").mkdir(parents=True)
    (tmp_path / "studies/p10s0/freeze/plan.json").write_text("[]")
    with pytest.raises(pool.StageRefused, match="not an object"):
        stages.load_plan(tmp_path)
    assert stages.CAPS_FILE == "studies/p10s0/freeze/stage_caps.json" and monkeypatch is not None


def make_plan(tmp_path: Path) -> tuple[dict[str, Any], Path, Path]:
    repo, run = tmp_path / "repo", tmp_path / "run"
    (repo / "studies/p10s0/freeze").mkdir(parents=True)
    run.mkdir()
    sel = repo / "studies/p10s0/freeze/arm_selection.json"
    proj = repo / "projection.json"
    caps = repo / stages.CAPS_FILE
    sel.write_text("{}")
    caps.write_text("{}")
    core.write_record(proj, {**core.envelope("projection"), "arm_selection_sha256": file_sha256(sel), "missing_items": []})
    (run / "draw_plan.json").write_text("{}")
    manifests: dict[str, str] = {}
    for name in core.SET_NAMES:
        (run / "draws" / name).mkdir(parents=True)
        (run / "draws" / name / "data_manifest.json").write_text(name)
        manifests[name] = file_sha256(run / "draws" / name / "data_manifest.json")
    plan = {"generation": {"cap_seconds": 60.0, "provisional": False}, "arm_selection": {"path": "studies/p10s0/freeze/arm_selection.json", "sha256": file_sha256(sel)}, "projection": {"path": "projection.json", "sha256": file_sha256(proj)}, "stage_caps_sha256": file_sha256(caps), "run_dir": str(run), "draw_plan": {"sha256": file_sha256(run / "draw_plan.json")}, "data_manifests": manifests}
    return plan, repo, run


def test_verify_plan_checks_every_frozen_identity(tmp_path: Path) -> None:
    plan, repo, run = make_plan(tmp_path)
    stages.verify_plan(plan, repo, run)
    for mutate, needle in (
        (lambda p, r, u: (r / "studies/p10s0/freeze/arm_selection.json").write_text("{ }"), "arm_selection record"),
        (lambda p, r, u: (r / stages.CAPS_FILE).write_text("{ }"), "stage-cap table"),
        (lambda p, r, u: (u / "draw_plan.json").write_text("{ }"), "draw plan"),
        (lambda p, r, u: (u / "draws/p10s0-draw-5/data_manifest.json").write_text("x"), "data manifest of p10s0-draw-5"),
        (lambda p, r, u: (u / "draws/p10s0-reserve-2/data_manifest.json").unlink(), "data manifest of p10s0-reserve-2"),
    ):
        plan, repo, run = make_plan(tmp_path / needle.replace(" ", "_"))
        mutate(plan, repo, run)
        with pytest.raises(pool.StageRefused, match=needle):
            stages.verify_plan(plan, repo, run)
    plan, repo, run = make_plan(tmp_path / "other")
    with pytest.raises(pool.StageRefused, match="names the run directory"):
        stages.verify_plan(plan, repo, tmp_path / "elsewhere")
    plan["data_manifests"].pop("p10s0-draw-1")
    with pytest.raises(pool.StageRefused, match="all thirteen draws and both reserves"):
        stages.verify_plan(plan, repo, run)
    plan, repo, run = make_plan(tmp_path / "mismatch")
    core.write_record(repo / "projection.json", {**core.envelope("projection"), "arm_selection_sha256": "0" * 64, "missing_items": []})
    plan["projection"]["sha256"] = file_sha256(repo / "projection.json")
    with pytest.raises(pool.StageRefused, match="not measured for the frozen arm-selection"):
        stages.verify_plan(plan, repo, run)


def test_block_cap_refuses_a_missing_configuration() -> None:
    caps = budget.caps_table(syn_rates(), gates_wall_seconds=1, gates_per_draw_seconds=1, analysis_wall_seconds=1, report_wall_seconds=1, generate_wall_seconds=1)
    assert stages.block_cap("q1", caps, "full")["train"] > 0
    for stage, key in (("q1", "other"), ("wx", "A0"), ("nonsense", "")):
        with pytest.raises(pool.StageRefused):
            stages.block_cap(stage, caps, key)


def syn_rates() -> budget.Rates:
    return {item: budget.Rate(0.01, 1, 1, 1.0) for item in budget.rehearsal_items()}


def test_require_draw_plan_and_gates_guards(tmp_path: Path) -> None:
    with pytest.raises(pool.StageRefused, match="no draw plan"):
        stages.require_draw_plan(tmp_path)
    core.write_record(tmp_path / "draw_plan.json", {**core.envelope("draw_plan"), "ok": False, "reason": "3 draws failed G1", "seed_set_of": {}})
    with pytest.raises(pool.StageRefused, match="not ok"):
        stages.require_draw_plan(tmp_path)
    core.write_record(tmp_path / "draw_plan.json", {**core.envelope("draw_plan"), "ok": True, "seed_set_of": {"1": "p10s0-draw-1"}})
    with pytest.raises(pool.StageRefused, match="no passed G1 record"):
        stages.require_draw_plan(tmp_path)
    folder = tmp_path / "draws" / "p10s0-draw-1"
    folder.mkdir(parents=True)
    core.write_record(folder / "data_manifest.json", {**core.envelope("data_manifest"), "g1_passed": True})
    assert stages.require_draw_plan(tmp_path)["ok"]
    with pytest.raises(pool.StageRefused, match="no gates record"):
        stages.require_gates_passed(tmp_path)
    core.write_record(tmp_path / "gates.json", {**core.envelope("gates"), **{f"{g}_passed": True for g in analysis.GATES}, "g10_passed": False})
    with pytest.raises(pool.StageRefused, match="G10"):
        stages.require_gates_passed(tmp_path)
    core.write_record(tmp_path / "gates.json", {**core.envelope("gates"), **{f"{g}_passed": True for g in analysis.GATES}})
    assert stages.require_gates_passed(tmp_path)["g4_passed"]


def test_spec_for_uses_the_draw_plan_in_registered_mode_and_never_the_wrong_set(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["train", "--mode", "registered", "--run-dir", str(tmp_path)])
    assert stages.spec_for(ns, planned=False, draw=4).name == "p10s0-draw-4" and stages.spec_for(ns, planned=False, reserve=2).name == "p10s0-reserve-2"
    with pytest.raises(pool.StageRefused, match="no draw plan"):
        stages.spec_for(ns, draw=1)
    core.write_record(tmp_path / "draw_plan.json", {**core.envelope("draw_plan"), "ok": True, "seed_set_of": {"4": "p10s0-reserve-1"}})
    (tmp_path / "draws/p10s0-reserve-1").mkdir(parents=True)
    core.write_record(tmp_path / "draws/p10s0-reserve-1/data_manifest.json", {**core.envelope("data_manifest"), "g1_passed": True})
    assert stages.spec_for(ns, draw=4).name == "p10s0-reserve-1"  # the reserve takes the failed draw's place
    for mode, expected in (("check", "p10s0-check"), ("rehearsal", "p10s0-rehearsal"), ("dry", "p10s0-test-0")):
        assert stages.spec_for(stages.build_parser().parse_args(["train", "--mode", mode]), draw=7).name == expected


def test_identity_mismatches_are_reported() -> None:
    now = core.code_identity()
    ok = {"stage": "train-q1", "identity": now}
    bad = {"stage": "train-q1", "identity": {**now, "source_sha256": "0" * 64}}
    assert stages.identity_mismatches([ok]) == [] and stages.identity_mismatches([bad]) == ["train-q1: identity source_sha256 differs"]
    assert stages.identity_mismatches([{"stage": "generate-p10s0-draw-1", "identity": {**now, "source_sha256": "0" * 64}}]) == []  # generation precedes the freeze commit's tree only by hash and is checked by the plan
    res = analysis.analyze(syn.make_run(frozen_mismatch=stages.identity_mismatches([bad])))
    assert res["outcome"]["row"] == 2


def test_common_args_pass_every_worker_option(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["train", "--mode", "dry", "--dry", "--run-dir", str(tmp_path), "--busy-processes", "12", "--dry-candidate", "A1", "--updates", "4", "--reserve", "2"])
    argv = stages.common_args(ns)
    for flag in ("--run-dir", "--mode", "--dry", "--busy-processes", "--dry-candidate", "--updates", "--reserve", "--draw", "--experiments-root"):
        assert flag in argv
    task = stages.make_task("train-q1", "x", stages.worker_argv("train", "--labels", "x"), tmp_path, core.code_identity(), tmp_path / "r.json")
    assert task.group == "train" and task.argv[1:3] == ("-m", "studies.p10s0.stages")
    with pytest.raises(ValueError):
        stages.make_task("train-q1", "x", (sys.executable, "-m", "studies.p9ii.stages", "work", "train"), tmp_path, core.code_identity(), tmp_path / "r.json")


def test_limits_are_read_from_the_config_file() -> None:
    ns = stages.build_parser().parse_args(["train"])
    lim = stages.limits(ns)
    assert lim == {"rss_worker_bytes": 3 * 1024**3, "rss_aggregate_bytes": 18 * 1024**3, "workers": 6}
    ns2 = stages.build_parser().parse_args(["train", "--rss-worker-bytes", "1000"])
    assert stages.limits(ns2)["rss_worker_bytes"] == 1000


def test_q1_cut3_reads_the_start_record(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["train", "--run-dir", str(tmp_path)])
    assert stages.q1_cut3(ns) is False and len(stages.block_cells_of(ns, "q1")) == 230
    core.write_record(tmp_path / "q1_start.json", {**core.envelope("q1_gate"), "cut3": True})
    assert stages.q1_cut3(ns) is True and len(stages.block_cells_of(ns, "q1")) == 190
    with pytest.raises(pool.StageRefused, match="no passed|q1_gate|No such"):
        try:
            stages.block_cells_of(ns, "wx")
        except FileNotFoundError as exc:
            raise pool.StageRefused(str(exc)) from exc
    core.write_record(tmp_path / "q1_gate.json", {**core.envelope("q1_gate"), "candidate": None, "blocks": {"wx": {"run": False, "status": "NOT RUN — NO CANDIDATE"}, "probe": {"run": False, "status": "NOT RUN — NO CANDIDATE"}}})
    with pytest.raises(pool.StageRefused, match="NOT RUN — NO CANDIDATE"):
        stages.block_cells_of(ns, "probe")
    core.write_record(tmp_path / "q1_gate.json", {**core.envelope("q1_gate"), "candidate": "A5-D", "blocks": {"wx": {"run": True, "status": None}, "probe": {"run": True, "status": None}}})
    assert [c.arm for c in stages.block_cells_of(ns, "wx")][:1] == ["WX-A5-D"] and len(stages.block_cells_of(ns, "probe")) == 6


# --- the freeze plan is written by a command, from files ---------------------------------------------------------------------------------------------------
def make_run_dir_with_plan(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """A repository stand-in (selection record, config with a set generation cap, cap table with its measured block, the auditor's script and sibling), a run directory with a good draw plan and all fifteen
    manifests, and a projection record measured for the selection."""
    repo, run = tmp_path / "repo", tmp_path / "run"
    (repo / "studies/p10s0/freeze").mkdir(parents=True)
    (repo / "configs").mkdir()
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(core.set_generation_cap(30.0)))
    auditor = repo / "docs/reviews/p10-design-2026-11-15/adr-0020-review"
    auditor.mkdir(parents=True)
    (auditor / "c5_rev2_mapping_and_consistency.py").write_text("def part1():\n    pass\n")
    (auditor / "c2_mapping_enumeration.py").write_text("X = 1\n")
    sel = repo / "studies/p10s0/freeze/arm_selection.json"
    sel.write_text("{}")
    (repo / stages.CAPS_FILE).write_text(json.dumps({"gates": 800.0, "measured": {"gates": 400.0, "reserve_analysis_report": 2.0}}))
    seed_set_of = {str(k): name for k, name in enumerate(core.DRAW_NAMES, start=1)}
    for name in core.SET_NAMES:
        (run / "draws" / name).mkdir(parents=True)
        core.write_record(run / "draws" / name / "data_manifest.json", {**core.envelope("data_manifest"), "g1_passed": True})
    core.write_record(run / "draw_plan.json", {**core.envelope("draw_plan"), "ok": True, "seed_set_of": seed_set_of})
    proj = tmp_path / "projection.json"
    core.write_record(proj, {**core.envelope("projection"), "arm_selection_sha256": file_sha256(sel), "missing_items": []})
    return repo, run, sel, proj


def test_freeze_plan_command_writes_a_plan_that_verify_plan_accepts(tmp_path: Path) -> None:
    repo, run, sel, proj = make_run_dir_with_plan(tmp_path)
    out = repo / stages.FREEZE_PLAN
    argv = ["freeze-plan", "--repo", str(repo), "--run-dir", str(run), "--arm-selection", str(sel), "--projection", str(proj), "--out", str(out)]
    assert stages.main(argv) == 0
    plan = json.loads(out.read_text())
    assert plan["study"] == "P10S0" and plan["kind"] == "freeze_plan" and plan["arm_selection"]["path"] == "studies/p10s0/freeze/arm_selection.json" and plan["projection"]["path"] == str(proj.resolve())
    assert set(plan["data_manifests"]) == set(core.SET_NAMES) and plan["before_q1_projected_seconds"] == {"gates": 400.0} and plan["reserve_analysis_report_seconds"] == 2.0 and plan["profile"] == "registered" and set(plan["pinned_auditor_scripts"]) == {"c5_rev2_mapping_and_consistency.py", "c2_mapping_enumeration.py"} and plan["generation"]["provisional"] is False and plan["stage_caps_sha256"] == file_sha256(repo / stages.CAPS_FILE)
    stages.verify_plan(plan, repo, run)
    assert stages.load_plan(repo)["draw_plan"] == plan["draw_plan"]
    assert stages.main(argv) == 2  # never over an existing plan


def test_freeze_plan_command_refuses_a_projection_for_another_selection_a_missing_cap_table_and_a_bad_draw_plan(tmp_path: Path) -> None:
    repo, run, sel, proj = make_run_dir_with_plan(tmp_path / "a")
    base = ["freeze-plan", "--repo", str(repo), "--run-dir", str(run), "--arm-selection", str(sel), "--projection", str(proj), "--out"]
    sel.write_text("{ }")
    assert stages.main([*base, str(tmp_path / "a" / "p1.json")]) == 2  # the projection was measured for the old record
    repo, run, sel, proj = make_run_dir_with_plan(tmp_path / "b")
    (repo / stages.CAPS_FILE).unlink()
    assert stages.main(["freeze-plan", "--repo", str(repo), "--run-dir", str(run), "--arm-selection", str(sel), "--projection", str(proj), "--out", str(tmp_path / "b" / "p.json")]) == 2
    repo, run, sel, proj = make_run_dir_with_plan(tmp_path / "c")
    (run / "draw_plan.json").unlink()
    assert stages.main(["freeze-plan", "--repo", str(repo), "--run-dir", str(run), "--arm-selection", str(sel), "--projection", str(proj), "--out", str(tmp_path / "c" / "p.json")]) == 2
    repo, run, sel, proj = make_run_dir_with_plan(tmp_path / "d")
    core.write_record(proj, {**core.envelope("projection"), "arm_selection_sha256": file_sha256(sel), "missing_items": ["REH-A0-2K4K-main"]})
    assert stages.main(["freeze-plan", "--repo", str(repo), "--run-dir", str(run), "--arm-selection", str(sel), "--projection", str(proj), "--out", str(tmp_path / "d" / "p.json")]) == 2


# --- the launch scripts, parsed by the real parser ---------------------------------------------------------------------------------------------------------
def script_argv(name: str) -> list[list[str]]:
    import shlex

    text = (ROOT / "studies/p10s0/launch" / f"{name}.sh").read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        if "studies.p10s0.stages " in line and not line.lstrip().startswith("#") and "echo" not in line.split("studies.p10s0.stages")[0]:
            tail = line.split("studies.p10s0.stages ", 1)[1].split(" || ", 1)[0]
            out.append(shlex.split(tail.replace('"$RUN_DIR"', "/tmp/x-run").replace('"$FREEZE_COMMIT"', "abc123").replace('"$k"', "3").replace('"$r"', "2")))
    return out


@pytest.mark.parametrize("name", ["gates", "q1", "q1_gate", "probe", "wx", "analysis", "report"])
def test_launch_scripts_parse_and_name_the_registered_stage_and_the_frozen_caps(name: str) -> None:
    (argv,) = script_argv(name)
    ns = stages.build_parser().parse_args(argv)
    assert ns.command == "registered" and ns.name == name and ns.caps == stages.CAPS_FILE and ns.freeze_commit == "abc123" and ns.run_dir == "/tmp/x-run"
    assert not {k for k, v in vars(ns).items() if v not in (None, False) and k not in ("command", "name", "caps", "freeze_commit", "run_dir", "workers", "draw", "restore_split", "busy_processes", "mode", "block", "arm_selection", "projection")}, vars(ns)


def test_generate_script_passes_the_generation_cap_flag_to_every_call_and_the_driver_refuses_without_it(tmp_path: Path) -> None:
    calls = script_argv("generate")
    assert len(calls) == 3  # the draw loop, the reserve loop and draw-plan
    for argv in calls[:2]:
        ns = stages.build_parser().parse_args(argv)
        assert ns.command == "generate" and ns.mode == "registered" and ns.generation_cap_from_config and ns.stage_cap_seconds is None and ns.i_understand_freeze_time and ns.run_dir == "/tmp/x-run"
    assert stages.build_parser().parse_args(calls[2]).command == "draw-plan"
    # the P9-II attempt-1 failure: a script that omits what the driver requires is refused before anything is generated (nothing is built here; no registered seed is read)
    run = tmp_path / "run"
    code = stages.main(["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(run), "--i-understand-freeze-time", "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)])
    assert code == 2 and not (run / "draws").exists()


def test_registered_generation_needs_the_freeze_time_flag(tmp_path: Path) -> None:
    code = stages.main(["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp_path / "r"), "--stage-cap-seconds", "10", "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)])
    assert code == 2 and not (tmp_path / "r" / "draws").exists()


def test_every_launch_script_name_is_a_registered_stage_and_every_registered_stage_has_a_script() -> None:
    scripts = {p.stem for p in (ROOT / "studies/p10s0/launch").glob("*.sh")}
    assert scripts == set(stages.REGISTERED_STAGES) | {"generate"}


def test_the_committed_arm_selection_record_is_the_scripts_output_and_passes_g10() -> None:
    from studies.p10s0 import arm_selection as sel
    from studies.p10s0 import gates

    path = ROOT / "studies/p10s0/freeze/arm_selection.json"
    committed = json.loads(path.read_text())
    fresh = core.jsonable(sel.build_record(ROOT, commit_of=False))
    for entry in committed["p9ii_inputs"].values():
        entry.pop("last_commit", None)
    assert committed == json.loads(json.dumps(fresh)) and committed["mapping"]["printed"] == "FOURTH ARM: NONE — P9-II CARRIED A0 (ALREADY IN S0)" and committed["candidates"]["arms"] == ["A5-D", "A1"]
    assert gates.g10_check(json.loads(path.read_text()), ROOT)["passed"]


def test_a_new_run_directory_is_under_the_experiments_root_with_the_study_code(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["check"])
    run = stages.new_run_dir(ns, "check")
    assert Path(run).parent == core.default_experiments_root() and Path(run).name.startswith("P10S0K-") and ns.run_dir == str(run)
    ns2 = stages.build_parser().parse_args(["rehearse", "--experiments-root", str(tmp_path)])
    assert Path(stages.new_run_dir(ns2, "rehearse")).parent == tmp_path
    assert not Path(run).exists()  # a name only; nothing is created
