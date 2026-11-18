# ruff: noqa: E501
"""P10IS3 config, seeds, items, plan, freeze and refusal tests (ADR-0026 sections 4, 5, 6, 7, 11, 16). Every threshold of the config is LISTED here with its section and a literal that section must contain. Self-check only.
Registered entry points refuse today (nothing is frozen): tested."""

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10i_s3 import (  # noqa: E402
    core,
    gates,
    items,
    plan,
    report,
    runner,
    stages,
    synthetic,
)

ROOT = Path(__file__).resolve().parents[1]
ADR = (ROOT / core.SPEC).read_text(encoding="utf-8")
CFG = core.load_config()


def at(cfg: Any, path: str) -> Any:
    for part in path.split("."):
        cfg = cfg[part]
    return cfg


# (config path, expected value, a literal the ADR text must contain)
THRESHOLDS: list[tuple[str, Any, str]] = [
    ("duration.u_star", 16384, "U\\* = 16,384"),
    ("duration.checkpoints", [512, 2048, 8192, 16384], "0, 512, 2,048, 8,192 and U\\* = 16,384"),
    ("duration.epsilon", 0.001, "ε = 0.001"),
    ("duration.past_best_margin", 0.005, "more than 0.005 above its lowest earlier checkpoint"),
    ("rates.grid", [0.0003, 0.001, 0.003, 0.01, 0.03], "0.0003, 0.001, 0.003, 0.01, 0.03"),
    ("rates.tie_tolerance", 0.0005, "within 0.0005 nats/byte of m"),
    ("rates.max_extensions_per_side", 2, "at most twice per side"),
    ("rates.p4_rate", 0.003, "0.003"),
    ("thresholds.effect", 0.005, "mean C ≥ 0.005"),
    ("thresholds.dense_tolerance", -0.005, "mean Q ≥ −0.005"),
    ("thresholds.min_cells", 22, "≥ 22/27 cells"),
    ("thresholds.min_parents", 8, "≥ 8/9"),
    ("thresholds.cells", 27, "27 cells"),
    ("thresholds.half", 0.5, "P_used ≥ 0.5·C"),
    ("thresholds.dense_share", 0.90, "mean C ≥ 0.90 × mean C_dense"),
    ("thresholds.dense_floor", 0.005, "mean C_dense < 0.005"),
    ("thresholds.tolerance_joint", 1e-6, "NLL must match the enabled reference within 1e-6"),
    ("thresholds.tolerance_neg_ref", 1e-6, "must be 0 within 1e-6"),
    ("thresholds.routing_effect", 0.005, "mean ≥ +0.005 and G_train > 0 in ≥ 22/27 cells"),
    ("thresholds.loaded_load_average", 4.0, "load average exceeds 4"),
    ("controls.p_used_draws", 4, "Mean over 4 seeded draws"),
    ("controls.x_draws", 4, "Mean over 4 seeded draws"),
    ("controls.exhaustive_visit", 16, "`visit=16`"),
    ("data.rep_u_ranks", [2048, 4096], "train ranks 2,048–4,095"),
    ("data.fresh_start", 4096, "Chunks at train ranks ≥ 4,096"),
    ("data.panel_walk_start", 8192, "from rank 8,192"),
    ("data.fresh_pool", 152515, "152,515"),
    ("data.max_fresh_updates", 19064, "19,064"),
    ("data.eligible_train", 156611, "156,611"),
    ("data.eligible_validation", 16407, "16,407"),
    ("resources.rss_worker_bytes", 2 * 2**30, "RSS guard 2 GiB per worker"),
    ("resources.rss_aggregate_bytes", 12 * 2**30, "12 GiB aggregate"),
    ("resources.rss_aggregate_alone_bytes", 24 * 2**30, "24 GiB aggregate"),
    ("caps.rehearsal_hours", 25.0, "rehearsal 25 h"),
    ("caps.registered_hours", 48.0, "48 h until then"),
    ("setting.panel_chunks", 512, "first 512 eligible validation chunks"),
    ("setting.val_targets", 32768, "32,768"),
    ("setting.dense_width", 3100, "width 3,100"),
    ("setting.tree_parameters", 198401, "198,401"),
    ("setting.flat_parameters", 198145, "198,145"),
    ("platform.torch", "2.8.0", "PyTorch as in `uv.lock`"),
]


@pytest.mark.parametrize(("path", "value", "literal"), THRESHOLDS)
def test_every_threshold_equals_the_specification(path: str, value: Any, literal: str) -> None:
    assert at(CFG, path) == value
    text = re.sub(r"\\", "", literal)
    assert text in ADR.replace("\\*", "*") or literal in ADR, f"the ADR no longer contains {literal!r}"


def test_adamw_settings_and_study_constants() -> None:
    assert CFG["setting"]["adamw_betas"] == [0.9, 0.999] and CFG["setting"]["adamw_eps"] == 1e-8 and CFG["setting"]["weight_decay"] == 0 and CFG["setting"]["grad_clip"] == 1.0
    assert (CFG["setting"]["batch"], CFG["setting"]["context"], CFG["setting"]["positions_per_eval_batch"]) == (8, 64, 512)
    assert CFG["rates"]["extension_up"] == [0.1, 0.3] and CFG["rates"]["extension_down"] == [0.0001, 0.00003]  # half-decade steps (1, 3 per decade): an implementer's reading, listed
    assert CFG["caps"]["provisional"] is False  # set after R2; the plan carries the computed cap


def test_config_validation_refuses_missing_sections_and_nonfinite() -> None:
    bad = json.loads(json.dumps(dict(CFG)))
    del bad["rates"]["tie_tolerance"]
    with pytest.raises(ValueError, match="lacks"):
        core.validate_config(bad)
    bad = json.loads(json.dumps(dict(CFG)))
    bad["duration"]["epsilon"] = float("inf")
    with pytest.raises(ValueError, match="non-finite"):
        core.validate_config(bad)
    bad = json.loads(json.dumps(dict(CFG)))
    bad["spec_reference"] = "x"
    with pytest.raises(ValueError):
        core.validate_config(bad)


# ---------------- seeds ----------------
def test_seed_layout_matches_the_registry_rows() -> None:
    reg, cal, dry = core.Seeds("registered"), core.Seeds("calibration"), core.Seeds("dry")
    assert [reg.init(c) for c in (0, 1, 2, 3, 26)] == [330301, 330302, 330303, 330301, 330303]
    assert (reg.stream(0, 0), reg.stream(26, 2), reg.stream(9, 1)) == (260001, 260081, 260029)  # 260001 + 3c + g
    assert (reg.p_all(0), reg.p_all(26)) == (260101, 260127) and (reg.joint(0), reg.joint(26)) == (260131, 260157)
    assert (reg.p_used(0, 0), reg.p_used(26, 3), reg.p_used(5, 2)) == (260201, 260308, 260223)
    assert (reg.x(0, 0), reg.x(26, 3), reg.x(5, 2)) == (260401, 260508, 260423)
    assert (cal.init(0), cal.stream(2, 2), cal.p_all(2), cal.joint(2), cal.p_used(2, 3), cal.x(2, 3)) == (330391, 269009, 269023, 269026, 269042, 269062)
    assert (dry.init(0), dry.stream(0, 2), dry.p_all(0), dry.joint(0), dry.p_used(0, 3), dry.x(0, 3)) == (330392, 269203, 269221, 269222, 269234, 269254)
    assert core.test_seed(0) == 935001 and core.Seeds("test").init(0) == 330398 and core.Seeds("test").init(1) == 330399
    with pytest.raises(ValueError):
        reg.stream(27, 0)


def test_cell_index_and_parents() -> None:
    assert core.cell_index(101, 301, 0) == 0 and core.cell_index(103, 303, 2) == 26 and core.cell_index(102, 302, 1) == 13
    assert [core.parent_label(core.calibration_parent(c)) for c in range(3)] == ["b101-o301", "b102-o302", "b103-o303"]
    assert core.parent_of(26) == 8 and core.seed_position(26) == 2


def test_study_never_calls_the_p4_or_p5_permutation_helpers() -> None:
    src = "\n".join(p.read_text() for p in (ROOT / "studies/p10i_s3").glob("*.py"))
    assert "p4_model.intervene" not in src and "p5_model" not in src and "memory_permutation" not in src
    assert not re.search(r"\b(40000|50000|60000|70000)\b", src)


def test_seed_problems_empty_and_gate_passes_with_the_extended_checker() -> None:
    assert gates.seed_problems() == []
    g = gates.seed_gate(CFG, root=ROOT)
    assert g["passed"] is True, g["problems"]
    assert g["checker"]["result_line"] == "RESULT: PASS" and len(g["checker"]["copy_sha256"]) == 64 and len(g["checker"]["substitutions"]) == (2 if (ROOT / "studies/p10i_s3/freeze/seed_registry_check.py").exists() else 3)  # the frozen copy needs no ROOT substitution
    assert g["roles"]["registered_streams"] == 81 and g["roles"]["registered_p_used"] == 108 and g["roles"]["registered_joint"] == 27


# ---------------- items ----------------
def rt_single(rate: float = 0.003) -> dict[str, Any]:
    return synthetic.rate_table(CFG, rate=rate)


def rt_distinct() -> dict[str, Any]:
    out: dict[str, Any] = {"rates": {}, "edge": {}}
    for g in core.REGIMES:
        for a in core.REGIME_ARMS[g]:
            out["rates"][f"{a}|{g}"] = {"512": 0.0003, "2048": 0.001, "8192": 0.01, "16384": 0.03}
            out["edge"][f"{a}|{g}"] = False
    return out


def test_item_counts_match_section_9() -> None:
    one = items.registered_items(CFG, rt_single())
    assert len(one["train"]) == 216 and len(one["eval"]) == 216 * 5  # 3 arms x REP and FRESH + 2 arms x REP-U = 8 arm-regimes x 27 cells; step 0 and four checkpoints
    many = items.registered_items(CFG, rt_distinct())
    assert len(many["train"]) == 216 * 4 + 54  # 216 primary + 648 short runs + 54 anchor runs (REP, M-TREE and D-ADAPT, rate for U* is not 0.003)
    assert len(many["train"]) == 918
    for lst in many.values():
        assert len({i["id"] for i in lst}) == len(lst)
    # M-FLAT is not run in REP-U
    assert not [i for i in many["train"] if i["arm"] == "M-FLAT" and i["regime"] == "REP-U"]
    # full controls only at the checkpoint whose rate the run has; enabled reads elsewhere on the primary run
    prim = [i for i in many["eval"] if i["role"] == "primary" and i["arm"] == "M-TREE" and i["regime"] == "FRESH" and i["cell"] == 0]
    assert {i["update"]: i["controls"] for i in prim} == {0: "step0", 512: "enabled", 2048: "enabled", 8192: "enabled", 16384: "full"}
    short = [i for i in many["eval"] if i["role"] == "duration" and i["arm"] == "M-TREE" and i["regime"] == "FRESH" and i["cell"] == 0]
    assert sorted((i["update"], i["controls"]) for i in short) == [(512, "full"), (2048, "full"), (8192, "full")]
    t = [i for i in many["train"] if i["arm"] == "M-TREE" and i["regime"] == "FRESH" and i["cell"] == 5]
    assert sorted((i["max_update"], i["role"]) for i in t) == [(512, "duration"), (2048, "duration"), (8192, "duration"), (16384, "primary")]
    assert all(i["init_seed"] == 330301 + 5 % 3 and i["stream_seed"] == 260001 + 3 * 5 + 2 for i in t)


def test_equal_rates_make_one_run_serve_every_duration() -> None:
    rt = rt_single()
    rt["rates"]["M-TREE|REP"] = {"512": 0.003, "2048": 0.003, "8192": 0.01, "16384": 0.01}
    g = items.run_groups(CFG, rt, "M-TREE", "REP", anchor_rate=0.003)
    # no anchor item next to the 0.003 duration run: they are one run (prefix identity), recorded with both roles
    assert [(x["role"], x["rate"], x["snapshots"], x["max_update"], x["full"]) for x in g] == [("primary", 0.01, [512, 2048, 8192, 16384], 16384, [8192, 16384]), ("duration+anchor", 0.003, [512, 2048, 8192, 16384], 16384, [512, 2048])]


def test_b2_anchor_at_the_rate_of_a_short_duration_does_not_collide() -> None:
    """The audit's reproducer E1: 0.003 for the short durations and a lower rate for U* used to raise 'a plan names an item twice'."""
    rt = rt_single(0.001)
    rt["rates"]["M-TREE|REP"] = {"512": 0.003, "2048": 0.001, "8192": 0.001, "16384": 0.001}
    its = items.registered_items(CFG, rt)
    for lst in its.values():
        assert len({i["id"] for i in lst}) == len(lst)
    t = [i for i in its["train"] if i["arm"] == "M-TREE" and i["regime"] == "REP" and i["cell"] == 0]
    assert sorted((i["role"], i["rate"], i["max_update"]) for i in t) == [("duration+anchor", 0.003, 16384), ("primary", 0.001, 16384)]
    e = {x["update"]: x["controls"] for x in its["eval"] if x["train"] == items.train_id("M-TREE", "REP", 0.003, 0)}
    assert e == {512: "full", 2048: "enabled", 8192: "enabled", 16384: "enabled"}  # full controls where the run's rate is the duration's rate, enabled reads elsewhere (the anchor's U* read)


def test_registered_items_are_a_pure_function_of_config_and_rate_table() -> None:
    assert items.registered_items(CFG, rt_single()) == items.registered_items(CFG, rt_single())
    assert items.registered_items(CFG, rt_single()) != items.registered_items(CFG, rt_single(0.01))


def write_r2(path: Path, spu: float = 0.01, enabled: float = 0.1, full: float = 1.0, workers: int = 6) -> Path:
    """An R2 record with the same unit cost for every arm (a fixture: real unit costs come from the probes)."""
    arm = {"seconds_per_update": spu, "seconds_per_enabled_read": enabled, "seconds_per_full_read_set": full}
    path.write_text(json.dumps({"unit_costs": {"workers": workers, "arms": {a: dict(arm) for a in core.ARMS}, "slowdown": dict.fromkeys(core.ARMS, 1.0)}}))
    return path


def expected_hours(rt: dict[str, Any], spu: float = 0.01, enabled: float = 0.1, full: float = 1.0, workers: int = 6) -> float:
    """The projection counted by hand from the items (not through cost.project_hours): updates x seconds, plus the reads of every evaluation item, plus the gates, over the workers."""
    its = items.registered_items(CFG, rt)
    sec = sum(t["max_update"] * spu for t in its["train"])
    for e in its["eval"]:
        sec += full if e["controls"] == "full" else (3 * enabled if e["controls"] == "enabled" else 2 * enabled)
    arm_regimes = sum(len(core.REGIME_ARMS[g]) for g in core.REGIMES)
    sec += arm_regimes * ((512 + 16384) * spu + 4 * enabled) + 9 * 3 * enabled
    return sec / workers / 3600.0


# ---------------- the plan, the freeze, the refusals ----------------
def _skeleton(tmp: Path) -> Path:
    for rel in ("studies/p10i_s3", "src/arborlm"):
        shutil.copytree(ROOT / rel, tmp / rel, ignore=shutil.ignore_patterns("__pycache__", "freeze", "*.pyc"))
    (tmp / "studies/p10i_s3/freeze").mkdir(parents=True)
    (tmp / "configs").mkdir()
    shutil.copy(ROOT / core.CONFIG, tmp / core.CONFIG)
    (tmp / "tests").mkdir()
    for f in (ROOT / "tests").glob("test_p10is3_*.py"):
        shutil.copy(f, tmp / "tests" / f.name)
    for f in ("uv.lock", "pyproject.toml"):
        shutil.copy(ROOT / f, tmp / f)
    (tmp / "docs/decisions").mkdir(parents=True)
    shutil.copy(ROOT / core.SPEC, tmp / core.SPEC)
    (tmp / "studies/__init__.py").write_text("")
    chk = tmp / CFG["seed_ranges"]["checker"]
    chk.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / CFG["seed_ranges"]["checker"], chk)
    return tmp


def _args(**kw: Any) -> Any:
    import argparse

    return argparse.Namespace(**kw)


def test_candidate_plan_is_written_first_and_once_and_superseded_aside(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    (repo / core.RATE_TABLE).write_text(json.dumps(rt_single()))
    a = _args(repo=str(repo), run_dir=str(tmp_path / "run"), data_manifest=None, parent_suite=None, r2=None, over_cap_approved=False, supersede=False)
    assert stages.cmd_candidate_plan(a) == 0
    first = (repo / core.PLAN).read_bytes()
    with pytest.raises(plan.StageRefused, match="--supersede"):
        stages.cmd_candidate_plan(a)
    a.supersede = True
    a.r2 = str(write_r2(tmp_path / "r2.json"))
    assert stages.cmd_candidate_plan(a) == 0
    moved = list((repo / "studies/p10i_s3/freeze/superseded").glob("plan-*.json"))
    assert len(moved) == 1 and moved[0].read_bytes() == first  # the old file is moved aside, never deleted
    p = plan.Plan.load(repo / core.PLAN)
    assert p.data["caps"]["registered_hours"] == pytest.approx(2.0 * expected_hours(rt_single())) and p.data["caps_provisional"] is False  # 0 charged + 2 x the projection computed from R2's record
    assert p.data["projection"]["r2_sha256"] == file_sha256(tmp_path / "r2.json") and p.data["projection"]["hours"] == pytest.approx(expected_hours(rt_single()))
    assert len(p.items("train")) == 216 and p.data["workers"] * p.data["rss_worker_bytes"] <= p.data["rss_aggregate_bytes"] == 12 * 2**30
    a.r2 = str(write_r2(tmp_path / "big.json", spu=0.5))
    with pytest.raises(plan.StageRefused, match="exceeds 48"):
        stages.cmd_candidate_plan(a)


def test_plan_identity_detects_a_changed_frozen_file_and_a_changed_src_file(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    (repo / core.RATE_TABLE).write_text(json.dumps(rt_single()))
    cfg = core.load_config(repo / core.CONFIG)
    rec = plan.build_plan(mode=plan.REGISTERED, cfg=cfg, repo=repo, run_dir=tmp_path / "run", rate_table=rt_single(), projected_remaining_hours=5.0)
    p = plan.Plan(rec)
    plan.verify_identity(p, repo)
    # K3: a named file that the import walk does not reach is still hashed in the plan
    assert "src/arborlm/__init__.py" in rec["src"]["files"] and "src/arborlm/p4_parent.py" in rec["src"]["files"] and "src/arborlm/p4_model.py" in rec["src"]["files"]
    assert "src/arborlm/p4_parent.py" in rec["src"]["named_not_reached"] or "src/arborlm/p4_parent.py" in rec["src"]["files"]
    assert set(rec["src"]["files"]) >= {f"src/arborlm/{n}.py" for n in plan.NAMED_SRC}  # the walk adds to the named list and never removes from it
    with (repo / "src/arborlm/p4_parent.py").open("a") as f:
        f.write("\n# changed\n")
    with pytest.raises(plan.StageRefused, match="PAUSED — IDENTITY"):
        plan.verify_identity(p, repo)
    shutil.copy(ROOT / "src/arborlm/p4_parent.py", repo / "src/arborlm/p4_parent.py")  # restoring the file bit for bit resumes
    plan.verify_identity(p, repo)
    (repo / "studies/p10i_s3/core.py").write_text((repo / "studies/p10i_s3/core.py").read_text() + "\n# x\n")
    with pytest.raises(plan.StageRefused, match="frozen file"):
        plan.verify_identity(p, repo)
    shutil.copy(ROOT / "studies/p10i_s3/core.py", repo / "studies/p10i_s3/core.py")
    (repo / "tests/test_p10is3_extra.py").write_text("# a new test file of this study is a frozen input too\n")
    with pytest.raises(plan.StageRefused, match="test_p10is3_extra"):
        plan.verify_identity(p, repo)


def test_provisional_caps_and_missing_pieces_refuse(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    (repo / core.RATE_TABLE).write_text(json.dumps(rt_single()))
    a = _args(repo=str(repo), run_dir=str(tmp_path / "run"), data_manifest=None, parent_suite=None, r2=None, over_cap_approved=False, supersede=False)
    assert stages.cmd_candidate_plan(a) == 0
    p = plan.Plan.load(repo / core.PLAN)
    assert p.data["caps_provisional"] is True  # no projection yet: the 48-hour bound and provisional
    f = _args(repo=str(repo), rehearsal=str(tmp_path / "none.json"))
    with pytest.raises(plan.StageRefused, match="provisional"):
        stages.cmd_freeze(f)  # a measuring rehearsal cannot be frozen on
    with pytest.raises(plan.StageRefused, match="provisional"):
        plan.verify_plan(p, repo, tmp_path / "run")


def test_registered_entry_points_refuse_today(tmp_path: Path) -> None:
    run = tmp_path / "run"
    for stage in plan.REGISTERED_STAGES:
        code = stages.main(["registered", stage, "--run-dir", str(run), "--freeze-commit", "HEAD"])
        assert code == 2
    assert not run.exists() or not any(run.iterdir())  # nothing was written
    with pytest.raises(plan.StageRefused, match="no freeze plan"):
        plan.load_registered_plan(tmp_path)
    with pytest.raises(plan.StageRefused, match="Decision 2"):
        plan.require_decision_2(ROOT, "HEAD")  # no committed DECISION_2.md names a freeze commit


def test_worker_refuses_with_the_identity_exit_code_and_writes_nothing(tmp_path: Path) -> None:
    repo = _skeleton(tmp_path / "repo")
    cfg = core.load_config(repo / core.CONFIG)
    rec = plan.build_plan(mode=plan.REHEARSAL, cfg=cfg, repo=repo, run_dir=tmp_path / "run", rate_table=rt_single())
    pf = tmp_path / "plan.json"
    core.write_record(pf, rec)
    (repo / "studies/p10i_s3/core.py").write_text((repo / "studies/p10i_s3/core.py").read_text() + "\n# x\n")
    code = stages.main(["work", "train", "--run-dir", str(tmp_path / "run"), "--plan", str(pf), "--repo", str(repo), "--item", "x"])
    assert code == stages.IDENTITY_EXIT == 75
    assert not (tmp_path / "run").exists()


# ---------------- the lead's pause file (K6) ----------------
def test_pause_file_pauses_between_tasks_and_resume_runs_them(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    tasks = [runner.Task(f"t{i}", (sys.executable, "-c", "import sys, pathlib; pathlib.Path(sys.argv[1]).write_text('x')", str(tmp_path / f"r{i}")), tmp_path / f"r{i}", tmp_path / f"f{i}", tmp_path / f"l{i}") for i in range(3)]
    (run / core.PAUSE_FILE).write_text("ADR-0025 stage 7 is running")
    out, _ = runner.run_tasks(tasks, workers=2, cap_seconds=60, rss_worker_bytes=2**31, rss_aggregate_bytes=2**33, run_dir=run)
    assert all(o["status"] == runner.PAUSED_BY_LEAD for o in out.values()) and not (tmp_path / "r0").exists()
    rec = runner.write_manifest(run, "train", "test", out, 0.0, identity={}, started="t", caps={})
    assert rec["status"] == "PAUSED — BY THE LEAD"
    (run / core.PAUSE_FILE).unlink()
    out2, _ = runner.run_tasks(tasks, workers=2, cap_seconds=60, rss_worker_bytes=2**31, rss_aggregate_bytes=2**33, run_dir=run)
    assert all(o["status"] == runner.COMPLETED for o in out2.values())
    assert runner.write_manifest(run, "train", "test", out2, 1.0, identity={}, started="t", caps={})["status"] == "COMPLETE"
    with pytest.raises(RuntimeError, match="COMPLETE"):
        runner.write_manifest(run, "train", "test", out2, 1.0, identity={}, started="t", caps={})


def test_stage_status_rules() -> None:
    ok, bad = {"status": runner.COMPLETED}, {"status": runner.FAILED}
    assert runner.stage_status({"a": ok}) == "COMPLETE"
    assert runner.stage_status({"a": ok, "b": bad}) == "FAILED"
    assert runner.stage_status({"a": ok, "b": {"status": runner.KILLED_RSS}}) == "PAUSED"
    assert runner.stage_status({"a": {"status": runner.PAUSED_IDENTITY}}) == "PAUSED"


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="needs a git checkout (a git archive has no .git)")
def test_ledger_paths_must_be_ignored_or_outside(tmp_path: Path) -> None:
    plan.require_ignored_path(ROOT, tmp_path / "ledger.json")  # outside the repository: fine
    with pytest.raises(plan.StageRefused, match="not git-ignored"):
        plan.require_ignored_path(ROOT, ROOT / "studies" / "p10i_s3" / "ledger.json")
    plan.require_ignored_run_dir(ROOT, ROOT / "experiments" / "x")


# ---------------- the report ----------------
def test_report_is_a_pure_function_with_every_section() -> None:
    from studies.p10i_s3 import analysis

    reg = synthetic.registry(CFG, {("M-TREE", "FRESH"): synthetic.Spec(gain=0.02), ("D-ADAPT", "FRESH"): synthetic.Spec(gain=0.022)})
    reg[core.nll_key("M-TREE", "FRESH", 0.003, 7, 512, "enabled")] = None
    res = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    text = report.render(res, "test")
    assert text == report.render(res, "test")
    for needle in ("Registered labels", "FRESH", "REP-U", "Route A", "Routing and duration", "Six-parent readout", "Contrasts", "Limits", "Astra review: NOT_PERFORMED", "64 passes", "G_prior"):
        assert needle in text
    assert "COMPETITIVE" in text and "success" not in text.lower().replace("is not a success claim", "").replace("none is a success claim", "")
