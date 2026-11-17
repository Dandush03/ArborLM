# ruff: noqa: E501
"""P10S0 tests for the independent re-check's findings N2-N9 and its informational items: the stage token of a registered worker, the profile recorded in the products, the headroom reserve from the frozen caps,
the one place the hour cap is set, the manifest checks of ``set-generation-cap``, the latest commit that added the plan, ``stage_cap`` in registered mode, the deleted test file, the A5-D strings in every record,
and the README's list of implementer-worded strings. Throwaway repositories and run directories only; test seeds 920001-920999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9 import pool  # noqa: E402
from studies.p10s0 import budget, core, report, stages  # noqa: E402
from studies.p10s0 import classes as C  # noqa: E402,F401
from studies.p10s0 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def work_args(run_dir: Path, worker: str, labels: str | None = None) -> argparse.Namespace:
    argv = ["work", worker, "--mode", "registered", "--run-dir", str(run_dir)]
    if labels:
        argv += ["--labels", labels]
    return stages.build_parser().parse_args(argv)


def a_cell_label() -> str:
    return core.q1_cells(False)[0].label


@pytest.fixture
def tmp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway repository for ``repo_of`` (so the guards under test never read the real tree), with the acceptance, the run decision and a set generation cap."""
    repo = tmp_path / "repo"
    (repo / "docs/decisions").mkdir(parents=True)
    (repo / "configs").mkdir()
    (repo / core.P9II_ACCEPTANCE_SOURCE).write_text(core.P9II_ACCEPTANCE_QUOTE + "\n")
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(core.set_generation_cap(30.0)))
    (repo / "results/p10s0-freeze-test").mkdir(parents=True)
    (repo / "results/p10s0-freeze-test/DECISION.md").write_text("d\n")
    monkeypatch.setattr(stages, "repo_of", lambda _a: repo)
    return repo


def running(run_dir: Path, stage: str, nonce: str, cells: list[str]) -> None:
    (run_dir / stage).mkdir(parents=True, exist_ok=True)
    (run_dir / stage / stages.RUNNING_FILE).write_text(json.dumps({"stage": stage, "nonce": nonce, "task_labels": cells, "cells": cells}))


# --- N2: the stage token -----------------------------------------------------------------------------------------------------------------------------
def test_a_registered_worker_without_a_token_refuses(tmp_path: Path, tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(stages.TOKEN_ENV, raising=False)
    for fn, worker in ((stages.work_train, "train"), (stages.work_evaluate, "evaluate"), (stages.work_gates, "gates"), (stages.work_analyze, "analyze"), (stages.work_report, "report")):
        with pytest.raises(pool.StageRefused, match="no P10S0_STAGE_TOKEN"):
            fn(work_args(tmp_path, worker, a_cell_label() if worker in ("train", "evaluate") else None))


def test_a_token_of_another_stage_kind_a_stale_run_or_a_wrong_nonce_refuses(tmp_path: Path, tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    label = a_cell_label()
    running(tmp_path, "train-q1", "n0nce", [label])
    monkeypatch.setenv(stages.TOKEN_ENV, "evaluate-q1:n0nce")
    with pytest.raises(pool.StageRefused, match="not for a train worker"):
        stages.work_train(work_args(tmp_path, "train", label))
    monkeypatch.setenv(stages.TOKEN_ENV, "train-q1:wrong")
    with pytest.raises(pool.StageRefused, match="does not match"):
        stages.work_train(work_args(tmp_path, "train", label))
    monkeypatch.setenv(stages.TOKEN_ENV, "train-wx:n0nce")
    with pytest.raises(pool.StageRefused, match="is not running"):
        stages.work_train(work_args(tmp_path, "train", label))
    (tmp_path / "train-q1" / "manifest.json").write_text("{}")  # the stage finished: its token is dead
    monkeypatch.setenv(stages.TOKEN_ENV, "train-q1:n0nce")
    with pytest.raises(pool.StageRefused, match="is not running"):
        stages.work_train(work_args(tmp_path, "train", label))


def test_a_cell_outside_the_stage_s_tasks_or_the_frozen_matrix_refuses(tmp_path: Path, tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cells = core.q1_cells(False)
    inside, other = cells[0].label, cells[1].label
    running(tmp_path, "train-q1", "n", [inside, "Q1-A0-2K4K-d99-j9"])
    monkeypatch.setenv(stages.TOKEN_ENV, "train-q1:n")
    with pytest.raises(pool.StageRefused, match="not among the tasks of the running stage"):
        stages.work_train(work_args(tmp_path, "train", other))
    with pytest.raises(pool.StageRefused, match="not in the frozen matrix"):
        stages.work_train(work_args(tmp_path, "train", "Q1-A0-2K4K-d99-j9"))
    assert stages.require_stage_token(work_args(tmp_path, "train", inside), "train") == "train-q1"  # the same call with a matching token and cell passes


def test_registered_generation_as_a_worker_applies_the_acceptance_the_decision_the_cap_and_the_token(tmp_path: Path, tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = work_args(tmp_path / "run", "generate")
    monkeypatch.delenv(stages.TOKEN_ENV, raising=False)
    with pytest.raises(pool.StageRefused, match="no P10S0_STAGE_TOKEN"):
        stages.work_generate(args)
    name = core.registered_set(1, "registered").name if hasattr(core.registered_set(1, "registered"), "name") else "p10s0-draw-1"
    running(tmp_path / "run", f"generate-{name}", "n", [])
    monkeypatch.setenv(stages.TOKEN_ENV, f"generate-{name}:n")
    (tmp_repo / "results/p10s0-freeze-test/DECISION.md").unlink()
    with pytest.raises(pool.StageRefused, match="DECISION.md"):
        stages.work_generate(args)
    (tmp_repo / "results/p10s0-freeze-test/DECISION.md").write_text("d\n")
    (tmp_repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())  # provisional
    with pytest.raises(pool.StageRefused, match="provisional"):
        stages.work_generate(args)
    (tmp_repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(core.set_generation_cap(30.0)))
    (tmp_repo / core.P9II_ACCEPTANCE_SOURCE).write_text("none\n")
    with pytest.raises(pool.StageRefused, match="acceptance"):
        stages.work_generate(args)
    (tmp_repo / core.P9II_ACCEPTANCE_SOURCE).write_text(core.P9II_ACCEPTANCE_QUOTE + "\n")
    monkeypatch.setenv(stages.TOKEN_ENV, "generate-p10s0-draw-9:n")  # a token of another draw's stage
    with pytest.raises(pool.StageRefused, match="not running|is not"):
        stages.work_generate(args)


def test_run_stage_tasks_writes_the_running_marker_and_passes_the_token_then_removes_the_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ns = stages.build_parser().parse_args(["gates", "--dry", "--run-dir", str(tmp_path / "run"), "--experiments-root", str(tmp_path), "--stage-cap-seconds", "5"])
    ns.mode = stages.DRY
    seen: dict[str, Any] = {}
    label = a_cell_label()

    def fake_run_stage(tasks: Any, **kwargs: Any) -> Any:
        marker = tmp_path / "run" / "train-q1" / stages.RUNNING_FILE
        seen["marker"] = json.loads(marker.read_text())
        seen["token"] = kwargs["env"][stages.TOKEN_ENV]
        raise RuntimeError("stop")

    monkeypatch.setattr(pool, "run_stage", fake_run_stage)
    task = stages.make_task("train-q1", label, stages.worker_argv("train", "--labels", label), tmp_path / "run", core.code_identity(), tmp_path / "run" / "r.json")
    with pytest.raises(RuntimeError, match="stop"):
        stages.run_stage_tasks("train-q1", ns, [task], tmp_path / "run", cap=5.0)
    assert seen["token"] == f"train-q1:{seen['marker']['nonce']}" and seen["marker"]["cells"] == [label] and seen["marker"]["task_labels"] == [label]
    assert not (tmp_path / "run" / "train-q1" / stages.RUNNING_FILE).exists()  # removed even though the stage raised


def test_the_drivers_stage_names_are_the_workers_kinds() -> None:
    for stage, worker in (("train-q1", "train"), ("evaluate-wx", "evaluate"), ("gates", "gates"), ("analyze", "analyze"), ("report", "report"), ("generate-p10s0-draw-1", "generate")):
        assert stage.split("-")[0] == worker


# --- N3: the profile is recorded ------------------------------------------------------------------------------------------------------------------------------
def test_the_test_profile_banner_and_the_profile_field_are_in_the_report(tmp_path: Path) -> None:
    res = syn.make_run(patterns=syn.a0_unreliable(), candidate="A1")
    from studies.p10s0 import analysis as an

    result = an.analyze(res)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    core.write_record(run_dir / "analysis.json", {**core.envelope("analysis"), "dry": False, "profile": "test", "result": result})
    paths = report.write_report(run_dir, tmp_path / "out")
    md, product = paths[0].read_text(encoding="utf-8"), json.loads(paths[1].read_text(encoding="utf-8"))
    assert report.TEST_PROFILE_BANNER == "TEST PROFILE — test seeds, tiny sizes, synthetic backbone; not a result" and report.TEST_PROFILE_BANNER in md
    assert product["profile"] == "test" and product["dry"] is False and product["profile_banner"] == report.TEST_PROFILE_BANNER
    run2 = tmp_path / "run2"
    run2.mkdir()
    core.write_record(run2 / "analysis.json", {**core.envelope("analysis"), "dry": False, "profile": "registered", "result": result})
    out2 = report.write_report(run2, tmp_path / "out2")
    assert "TEST PROFILE" not in out2[0].read_text(encoding="utf-8") and json.loads(out2[1].read_text(encoding="utf-8"))["profile"] == "registered"


def test_freeze_plan_with_test_profile_needs_the_end_to_end_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / core.TEST_PROFILE_MARKER).write_text("x\n")
    monkeypatch.delenv(stages.E2E_ENV, raising=False)
    ns = stages.build_parser().parse_args(["freeze-plan", "--test-profile", "--run-dir", str(run), "--out", str(tmp_path / "plan.json")])
    with pytest.raises(pool.StageRefused, match="end-to-end exercise only"):
        stages.cmd_freeze_plan(ns)
    from studies.p10s0 import e2e

    assert e2e.clone_env(tmp_path, tmp_path)[stages.E2E_ENV] == "1"


# --- N4: the reserve is the sum of the frozen analysis and report caps --------------------------------------------------------------------------------------------
def test_the_reserve_doubled_is_the_sum_of_the_frozen_analysis_and_report_caps() -> None:
    rates = {item: budget.Rate(0.01, 1, 1, 1.0) for item in budget.rehearsal_items()}
    for analysis_s, report_s, cap_a, cap_r in ((3.0, 2.0, 60.0, 60.0), (100.0, 40.0, 200.0, 80.0)):
        caps = budget.caps_table(rates, gates_wall_seconds=10, gates_per_draw_seconds=1, analysis_wall_seconds=analysis_s, report_wall_seconds=report_s, generate_wall_seconds=10)
        assert caps["analysis"] == cap_a and caps["report"] == cap_r  # 2 x measured with the 60 s floor
        assert stages.frozen_reserve(caps) == (cap_a + cap_r) / 2 and core.HEADROOM * stages.frozen_reserve(caps) == caps["analysis"] + caps["report"]
        assert caps["measured"]["reserve_analysis_report"] == stages.frozen_reserve(caps)
    assert stages.frozen_reserve({}) == 0.0


# --- N5: the hour cap is read from the config -----------------------------------------------------------------------------------------------------------------------------
def test_the_hour_cap_is_set_in_the_config_only(tmp_path: Path) -> None:
    assert not hasattr(core, "CAP_HOURS")
    cfg = tmp_path / "c.toml"
    cfg.write_text(core.render_config_toml(None, 20.0))
    assert core.cap_hours(cfg) == 20.0 and core.ledger_for(tmp_path, cfg).cap_seconds == 20.0 * 3600 and core.resource_limits(cfg)["cap_hours"] == 20.0
    assert core.ledger_for(tmp_path).cap_seconds == core.cap_hours() * 3600  # whatever the real config holds: no test depends on its value
    for bad in (0.0, -1.0, float("inf"), float("nan")):
        cfg.write_text(core.render_config_toml(None, bad).replace("nan", "nan"))
        with pytest.raises(ValueError):
            core.load_config(cfg)
    cfg.write_text(core.render_config_toml(None, 20.0).replace("workers = 6", "workers = 7"))
    with pytest.raises(Exception):  # noqa: B017
        core.load_config(cfg)  # every other resource is still the registered constant


# --- N6: set-generation-cap reads a rehearsal-mode generation manifest ---------------------------------------------------------------------------------------------------
def gen_manifest(path: Path, *, stage: str, mode: str) -> Path:
    core.write_record(path, {**core.envelope("stage_manifest"), "stage": stage, "status": "COMPLETE", "mode": mode, "tasks": [{"seconds": 40.0}]})
    return path


def test_set_generation_cap_refuses_a_dry_or_check_draw_manifest_outside_the_end_to_end_exercise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    cfg = repo / core.DEFAULT_CONFIG
    cfg.write_text(core.render_config_toml())
    monkeypatch.delenv(stages.E2E_ENV, raising=False)

    def attempt(manifest: Path) -> int:
        return stages.main(["set-generation-cap", "--repo", str(repo), "--generate-manifest", str(manifest)])

    assert attempt(gen_manifest(tmp_path / "dry.json", stage="generate-p10s0-rehearsal", mode="dry")) == 2 and "rehearsal-mode" in capsys.readouterr().err
    assert attempt(gen_manifest(tmp_path / "check.json", stage="generate-p10s0-check", mode="check")) == 2
    assert attempt(gen_manifest(tmp_path / "other.json", stage="generate-p10s0-draw-1", mode="rehearsal")) == 2 and "generate-p10s0-rehearsal" in capsys.readouterr().err
    assert core.generation_block(cfg)["provisional"] is True  # none of the refusals changed the config
    assert attempt(gen_manifest(tmp_path / "ok.json", stage="generate-p10s0-rehearsal", mode="rehearsal")) == 0
    assert core.generation_block(cfg)["cap_seconds"] == 80.0
    cfg.write_text(core.render_config_toml(None, 20.0))
    monkeypatch.setenv(stages.E2E_ENV, "1")  # the end-to-end exercise may use its DRY generation
    assert attempt(gen_manifest(tmp_path / "dry2.json", stage="generate-p10s0-test-draw-1", mode="dry")) == 0
    assert core.cap_hours(cfg) == 20.0  # the file's own hour cap survives the rewrite of the generation block


# --- N8, I5: the latest commit that added the plan; a test file deleted after the freeze -----------------------------------------------------------------------------------------
def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, check=True, text=True).stdout.strip()


def make_repo(tmp: Path) -> Path:
    tmp.mkdir(parents=True)
    git(tmp, "init", "-q")
    for rel, text in (("studies/p10s0/a.py", "x = 1\n"), (str(core.DEFAULT_CONFIG), "a = 1\n"), (core.SPEC, "adr\n"), ("tests/test_p10s0_x.py", "def test_x(): pass\n"), ("tests/test_p10s0_y.py", "def test_y(): pass\n")):
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(text)
    git(tmp, "add", "-A")
    git(tmp, "commit", "-q", "-m", "base")
    return tmp


def test_the_freeze_commit_is_the_latest_commit_that_added_the_plan(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r")
    plan = repo / "studies/p10s0/freeze/plan.json"
    plan.parent.mkdir(parents=True)
    plan.write_text("{}")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze 1")
    first = git(repo, "rev-parse", "HEAD")
    git(repo, "rm", "-q", "studies/p10s0/freeze/plan.json")
    git(repo, "commit", "-q", "-m", "remove the plan")
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("{}")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze 2")
    second = git(repo, "rev-parse", "HEAD")
    with pytest.raises(pool.StageRefused, match="not the commit that added"):
        stages.check_preconditions("registered", repo, first)  # the earlier addition is not the freeze: the latest one is
    with pytest.raises(pool.StageRefused) as exc:
        stages.check_preconditions("registered", repo, second)
    assert "not the commit that added" not in str(exc.value)  # it passes this check and stops later (the stand-in repository has no src/)


def test_a_test_file_deleted_after_the_freeze_is_detected(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "r")
    plan = repo / "studies/p10s0/freeze/plan.json"
    plan.parent.mkdir(parents=True)
    plan.write_text("{}")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    freeze = git(repo, "rev-parse", "HEAD")
    git(repo, "rm", "-q", "tests/test_p10s0_y.py")
    git(repo, "commit", "-q", "-m", "delete a test")
    with pytest.raises(pool.StageRefused, match=r"test_p10s0_y.py differs from the freeze commit \(changed, added or deleted\)"):
        stages.check_preconditions("registered", repo, freeze)


# --- N9: stage_cap never returns a typed value in registered mode -------------------------------------------------------------------------------------------------------------
def test_stage_cap_in_registered_mode_ignores_a_typed_value() -> None:
    ns = argparse.Namespace(mode=stages.REGISTERED, stage_cap_seconds=99999.0, dry=False)
    assert stages.stage_cap(ns, 123.0) == 123.0  # the frozen table's cap
    with pytest.raises(pool.StageRefused, match="frozen table"):
        stages.stage_cap(ns)
    ns2 = argparse.Namespace(mode=stages.CHECK, stage_cap_seconds=7.0, dry=False)
    assert stages.stage_cap(ns2, 123.0) == 7.0  # the calibration modes keep their typed cap


# --- informational: the A5-D strings in every record, the gates timing ------------------------------------------------------------------------------------------------
def test_every_record_that_names_a5d_carries_the_strings_except_the_whitelisted_rehearsal_one(tmp_path: Path) -> None:
    for kind in ("gates", "stage_manifest", "train", "data_manifest", "projection"):
        core.write_record(tmp_path / f"{kind}.json", {**core.envelope(kind), "arm": "A5-D", "candidates": ["A5-D", "A1"]})
        data = json.loads((tmp_path / f"{kind}.json").read_text(encoding="utf-8"))
        assert data["a5d_provenance"] == core.a5d_fields(), kind
    core.write_record(tmp_path / "nothing.json", {**core.envelope("gates"), "arm": "A0"})
    assert "a5d_provenance" not in json.loads((tmp_path / "nothing.json").read_text())


def test_the_gates_timing_records_the_registered_over_rehearsal_per_draw_ratio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    (repo / stages.FREEZE_PLAN.parent).mkdir(parents=True)
    (repo / stages.CAPS_FILE).write_text(json.dumps({"measured": {"gates_per_draw": 0.5}}))
    monkeypatch.setattr(stages, "repo_of", lambda _a: repo)
    ns = argparse.Namespace(mode=stages.REGISTERED)
    t = stages.gates_timing(ns, 0.8, 20.0)
    assert t["rehearsal_per_draw_seconds"] == 0.5 and t["registered_over_rehearsal_per_draw_ratio"] == pytest.approx(1.6) and t["draws_timed"] == core.N_DRAWS
    t2 = stages.gates_timing(argparse.Namespace(mode=stages.REHEARSAL), 0.5, 5.0)
    assert t2["draws_timed"] == 1 and "registered_over_rehearsal_per_draw_ratio" not in t2


# --- N7: the README lists every implementer-worded string, generated from the code ------------------------------------------------------------------------------------------
def test_the_readme_lists_every_implementer_worded_string() -> None:
    from studies.p10s0 import implementer_strings

    found = implementer_strings.scan(ROOT)
    assert len(found) >= 20, "the scan found suspiciously few strings"
    readme = (ROOT / "studies/p10s0/freeze/README.md").read_text(encoding="utf-8")
    missing = [name for name, text in found.items() if text.replace("|", "\\|") not in readme]
    assert missing == [], f"the README's table of implementer-worded strings lacks: {missing}; regenerate it with `python -m studies.p10s0.implementer_strings`"
    assert "guard_seconds_per_task" in readme and "implementer addition" in readme.lower()
    assert implementer_strings.markdown(ROOT) in readme  # the table is the generated one, not an edited copy


# --- the end-to-end variant in which the probe is not refused for memory (opt-in, like the full exercise) ------------------------------------------------------------------------
@pytest.mark.skipif(os.environ.get("P10S0_E2E") != "1", reason="the full end-to-end exercise takes about 15 minutes per variant: opt in with P10S0_E2E=1 (or run python -m studies.p10s0.e2e --variant probe)")
def test_the_probe_variant_of_the_end_to_end_exercise_runs_the_probe_after_wx(tmp_path: Path) -> None:
    from studies.p10s0 import e2e

    summary = e2e.run_e2e(tmp_path / "e2e", variant="probe")
    s = summary["steps"]
    assert s["scripts"] == [["gates", 0], ["q1", 0], ["q1_gate", 0], ["probe", 2], ["wx", 0], ["probe", 0], ["analysis", 0], ["report", 0], ["q1", 2]]
    assert s["cut3"] is False and s["blocks"]["probe"]["run"] is True and s["blocks"]["wx"]["run"] is True and s["evaluate_probe"]["tasks"] == 6
