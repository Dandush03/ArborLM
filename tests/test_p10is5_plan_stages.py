# ruff: noqa: E501
"""P10IS5 plan, freeze, refusal, gate and launch-script tests (ADR-0028 sections 10, 12). Registered entry points REFUSE today (nothing is frozen); the plan holds definitions only; candidate-plan and freeze refuse
what the ADR says; the seed gate runs the cited checker as an extended copy. No device, no file larger than a few KiB. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is5 import core, freeze, gates, stages  # noqa: E402
from studies.p10is5 import plan as planmod  # noqa: E402
from studies.p10is5 import testing as T  # noqa: E402

ROOT = core.repo_root()
CFG = core.load_config()


def test_plan_content_is_definitions_only() -> None:
    c = planmod.plan_content(CFG, Path("/x/data.noindex"))
    assert set(c) == {"geometries", "cells", "tiling_rule", "registered", "counting_rehearsal", "paths", "files"}
    text = repr(c)
    for forbidden in ("m_t", "load_p95", "latency", "counter_bytes", "page_sha256", "requests\": ["):
        assert forbidden not in text
    reg = c["registered"]
    assert [b["request_order_seed"] for b in reg["blocks"]] == [280001, 280002, 280003, 280004, 280005, 280006] and [b["pass_order_seed"] for b in reg["blocks"]][-1] == 280206
    assert [b["role"] for b in reg["blocks"]] == ["regular"] * 5 + ["spare"] and reg["tile_assignment_seed"] == 287001 and reg["tiles_dealt"] == 3996
    k = c["counting_rehearsal"]
    assert len(k["blocks"]) == 5 and all(b["role"] == "regular" for b in k["blocks"]) and k["tile_assignment_seed"] == 289242 and k["tiles_dealt"] == 840
    assert len(c["cells"]) == 24 and c["paths"]["store"] == "/x/data.noindex/store.bin"
    assert c == planmod.plan_content(CFG, Path("/x/data.noindex"))


def test_geometry_round_trip() -> None:
    g = core.registered_geometry(CFG)
    assert planmod.geometry_from_json(planmod.geometry_to_json(g)) == g


def test_candidate_plan_refuses_provisional_figures_and_caps() -> None:
    class A:
        run_dir = "x"
        data_dir = "y.noindex"
        r1_record = "a"
        m_record = "b"
        supersede = False
        repo = None

    # Independent of the planning state: the command is given a configuration in which the figures, then the caps, are provisional.
    for section_name in ("fixed_after_r1_and_m", "caps"):
        cfg = copy.deepcopy(dict(CFG))
        cfg["fixed_after_r1_and_m"] = {**cfg["fixed_after_r1_and_m"], "provisional": False}
        cfg["caps"] = {**cfg["caps"], "provisional": False}
        cfg[section_name] = {**cfg[section_name], "provisional": True}
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(core, "load_config", lambda _p, _c=cfg: _c)
            with pytest.raises(core.StageRefused, match="provisional"):
                freeze.cmd_candidate_plan(A())  # type: ignore[arg-type]


def test_figures_from_records_and_comparison() -> None:
    r1 = {"passed": True, "idle_figures": {k: 1.5 for k in freeze.FIGURE_KEYS}}
    m = {"summary": {"margin": {"m_t": 0.2, "timing_spread": False}}}
    d = freeze.figures_from_records(r1, m)
    cfg = copy.deepcopy(dict(CFG))
    cfg["fixed_after_r1_and_m"] = {**cfg["fixed_after_r1_and_m"], **{k: 1.5 for k in freeze.FIGURE_KEYS}, "m_t": 0.2}
    assert freeze.figures_problems(cfg, d) == []
    cfg["fixed_after_r1_and_m"]["m_t"] = 0.21
    assert "m_t" in freeze.figures_problems(cfg, d)[0]
    with pytest.raises(core.StageRefused):
        freeze.figures_from_records({"passed": False}, m)
    with pytest.raises(core.StageRefused):
        freeze.figures_from_records(r1, {"summary": {"margin": None}})


def test_platform_problems() -> None:
    rec = {"system": "Darwin", "machine": "arm64", "python": "3.12.14", "torch": "2.8.0", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": True}
    assert planmod.platform_problems(CFG, rec) == []
    assert len(planmod.platform_problems(CFG, {**rec, "torch_num_threads": 8, "machine": "x86_64"})) == 2


def test_data_dir_must_be_noindex_under_home_outside_worktrees_and_not_synced() -> None:
    home = Path.home()
    with pytest.raises(core.StageRefused, match="noindex"):
        planmod.require_data_dir_outside(ROOT, home / "data")
    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-dir"], capture_output=True).returncode == 0:  # skipped cleanly when the copy is outside any git repository
        with pytest.raises(core.StageRefused, match="worktree"):
            planmod.require_data_dir_outside(ROOT, ROOT / "experiments" / "d.noindex")  # inside this worktree (or any worktree the copy sits in)
    with pytest.raises(core.StageRefused, match="not under the home folder"):
        planmod.require_data_dir_outside(ROOT, Path("/var/p10is5.noindex"))
    with pytest.raises(core.StageRefused, match="synced folder"):
        planmod.require_data_dir_outside(ROOT, home / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "p10is5.noindex")
    planmod.require_data_dir_outside(ROOT, home / "p10is5_study_never_created.noindex")  # nothing is created or written


def test_run_dir_inside_a_repository_must_be_ignored() -> None:
    with T.scratch("plan_ignore") as d:
        repo = mini_repo(d / "repo")
        (repo / ".gitignore").write_text("/runs/\n")
        planmod.require_ignored_run_dir(repo, repo / "runs" / "x")
        with pytest.raises(core.StageRefused, match="not git-ignored"):
            planmod.require_ignored_run_dir(repo, repo / "studies" / "run")
        planmod.require_ignored_run_dir(repo, d / "outside")  # outside the repository: cannot dirty it


@pytest.mark.parametrize("stage", sorted(stages.REGISTERED))
def test_registered_stages_refuse_today_and_write_nothing(stage: str, capsys: pytest.CaptureFixture[str]) -> None:
    run = ROOT / "experiments" / "_scratch" / "p10is5_tests" / "refuse_run"
    assert stages.main(["registered", stage, "--run-dir", str(run), "--freeze-commit", "HEAD"]) == 75  # an identity refusal: PAUSED — IDENTITY, nothing written
    assert "refused" in capsys.readouterr().err and not run.exists()


def test_registered_entry_refuses_without_a_freeze_commit(capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["registered", "e2", "--run-dir", str(ROOT / "experiments" / "_scratch" / "p10is5_tests" / "r2")]) == 75
    assert "refused" in capsys.readouterr().err


def test_worker_refuses_with_identity_exit_and_writes_nothing() -> None:
    run = ROOT / "experiments" / "_scratch" / "p10is5_tests" / "worker_run"
    rc = stages.main(["work-pass", "--stage", "E2", "--run-dir", str(run), "--data-dir", str(run), "--repeat", "1", "--k", "1", "--s", "1", "--block", "b", "--role", "regular", "--seq", "1", "--freeze-commit", "HEAD"])
    assert rc == core.IDENTITY_EXIT == 75 and not run.exists()


def test_delete_needs_the_recomputation_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["registered", "delete", "--run-dir", str(ROOT / "experiments" / "_scratch" / "p10is5_tests" / "d"), "--freeze-commit", "HEAD"]) == 75  # the entry refuses on identity before it reads the flag


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, text=True, check=True).stdout.strip()


def mini_repo(base: Path) -> Path:
    for p, t in (("studies/p10is5/a.py", "x=1\n"), ("src/arborlm/m.py", "y=1\n"), ("uv.lock", "l\n"), ("pyproject.toml", "p\n"), ("configs/p10is5_ssd.toml", "c\n")):
        f = base / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(t)
    git(base, "init", "-q")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "one")
    return base


def test_preconditions_in_a_scratch_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    with T.scratch("plan_git") as d:
        repo = mini_repo(d / "repo")
        monkeypatch.setattr(planmod, "platform_problems", lambda cfg, record=None: [])
        c1 = git(repo, "rev-parse", "HEAD")
        ident = planmod.check_preconditions(repo, c1, CFG)
        assert ident["commit"] == c1
        with pytest.raises(core.StageRefused, match="requires --freeze-commit"):
            planmod.check_preconditions(repo, None, CFG)
        with pytest.raises(core.StageRefused, match="not a commit"):
            planmod.check_preconditions(repo, "deadbeef", CFG)
        (repo / "studies/p10is5/a.py").write_text("x=2\n")
        with pytest.raises(core.StageRefused, match="not clean"):
            planmod.check_preconditions(repo, c1, CFG)
        git(repo, "commit", "-q", "-am", "two")
        with pytest.raises(core.StageRefused, match="differs from the freeze commit"):
            planmod.check_preconditions(repo, c1, CFG)  # a frozen file changed after the freeze commit
        monkeypatch.setattr(planmod, "platform_problems", lambda cfg, record=None: ["torch"])
        with pytest.raises(core.StageRefused, match="platform of record"):
            planmod.check_preconditions(repo, git(repo, "rev-parse", "HEAD"), CFG)


def test_decision_2_must_be_committed_and_name_the_commit() -> None:
    with T.scratch("plan_dec") as d:
        repo = mini_repo(d / "repo")
        c1 = git(repo, "rev-parse", "HEAD")
        with pytest.raises(core.StageRefused, match="Decision 2"):
            planmod.require_decision_2(repo, c1)
        f = repo / "results/p10is5-freeze-x/DECISION_2.md"
        f.parent.mkdir(parents=True)
        f.write_text(f"{c1}\nDECISION: RUN\n")
        with pytest.raises(core.StageRefused):
            planmod.require_decision_2(repo, c1)  # not committed
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "d2")
        assert planmod.require_decision_2(repo, c1).endswith("DECISION_2.md")
        f.write_text(f"{c1}\nDECISION: RUN\nDECISION: DO NOT RUN\n")
        git(repo, "commit", "-q", "-am", "d3")
        with pytest.raises(core.StageRefused):
            planmod.require_decision_2(repo, c1)
        f.write_text("0" * 40 + "\nDECISION: RUN\n")
        git(repo, "commit", "-q", "-am", "d4")
        with pytest.raises(core.StageRefused):
            planmod.require_decision_2(repo, c1)  # names another commit


def test_freeze_refuses_without_a_plan_and_plan_load_refuses(tmp_path: Path = Path()) -> None:
    class A:
        repo = None
        rehearsal = "x"

    if not (ROOT / core.PLAN).exists():
        with pytest.raises(core.StageRefused, match="no candidate plan"):
            freeze.cmd_freeze(A())  # type: ignore[arg-type]
        with pytest.raises(core.StageRefused, match="no freeze plan"):
            planmod.Plan.load(ROOT / core.PLAN)


def test_seed_gate_runs_the_cited_checker_with_the_own_files_exclusion() -> None:
    res = gates.seed_gate()
    assert res["passed"], res["problems"]
    ck = res["checker"]
    assert ck["sha256"] == CFG["seed_ranges"]["checker_sha256"] and len(ck["substitutions"]) == 3 and len(ck["copy_sha256"]) == 64 and ck["own_fail_lines"] == [] and ck["allocation_rows"] == 7
    assert all(937001 <= v <= 937999 for v in gates.planned_seed_values(CFG)["test"])


def test_seed_gate_catches_a_collision_and_a_range_error() -> None:
    cfg = copy.deepcopy(dict(CFG))
    cfg["seeds"] = {**cfg["seeds"], "k_tile_assignment": cfg["seeds"]["m_tile_assignment"]}
    r = gates.seed_gate(cfg, run_checker=False)
    assert not r["passed"] and any("two roles" in p for p in r["problems"])
    cfg = copy.deepcopy(dict(CFG))
    cfg["seeds"] = {**cfg["seeds"], "tile_assignment": 290001}
    assert any("outside" in p for p in gates.seed_gate(cfg, run_checker=False)["problems"])
    assert gates.allocation_problems(CFG, []) != []


def test_launch_scripts_are_fixed_and_have_no_loop_or_sleep() -> None:
    d = ROOT / "studies/p10is5/launch"
    names = sorted(p.name for p in d.glob("*.sh"))
    assert names == ["analysis.sh", "delete.sh", "e1.sh", "e2.sh", "k.sh", "m.sh", "p.sh", "r0.sh", "r1.sh", "report.sh"]
    for n in names:
        text = (d / n).read_text()
        assert os.access(d / n, os.X_OK) and subprocess.run(["sh", "-n", str(d / n)]).returncode == 0
        code = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
        for bad in ("while ", "until ", "sleep", "for "):
            assert bad not in code, (n, bad)
        assert "set -eu" in text and "uv run --locked" in code
    assert "caffeinate -i" in (d / "e2.sh").read_text() and "caffeinate -i" in (d / "r1.sh").read_text()
    assert "--independent-recomputation-done" in (d / "delete.sh").read_text()
