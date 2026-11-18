# ruff: noqa: E501
"""P10IS2 Part Q plan, freeze, registered preconditions, gates, rehearsal drivers, real-path guards (ADR-0025 sections 10, 11, 13; rulings L1, L5, L7, L10, L11). Throwaway git repositories under pytest's
tmp_path; synthetic data; no package outside the lock; nothing registered runs. Self-check only: not independent review."""

import argparse
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_fixtures import (  # noqa: E402
    SMALL_SIZES,
    lex_teachers,
    small_cfg,
    small_corpus,
    stub_student,
)

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2.common import core, gates  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.partq import freeze, pipeline, real, stages  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402
from studies.p10is2.partq import rehearsal as reh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config("Q")


def git(repo: Path, *a: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True, check=True)  # noqa: S603, S607
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository holding the files of Part Q's frozen set, a config with set caps, and a delegation record; one commit."""
    r = tmp_path / "repo"
    for rel in ("studies/p10is2", "studies/p10s2/requirements-datagen.txt", "configs/p10is2_partq.toml", "configs/p10is2_partt.toml", "uv.lock", "pyproject.toml", core.SPEC, "docs/reviews/p10-i-direction-2026-11-17/DELEGATION_2026-11-18.md"):
        src, dst = ROOT / rel, r / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "freeze"))
        else:
            shutil.copy(src, dst)
    (r / "studies/p10is2/freeze").mkdir(exist_ok=True)
    git(r, "init", "-q")
    (r / ".gitignore").write_text("runs/\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    return r


def set_caps(repo: Path, hours: dict[str, float], provisional: bool = False) -> None:
    p = repo / core.CONFIG_Q
    t = p.read_text()
    for k, v in hours.items():
        t = t.replace(f"{k} = 0.0", f"{k} = {v}")
    if not provisional:
        t = t.replace("provisional = true", "provisional = false")
    p.write_text(t)


CAP_HOURS = {f"{k}_hours": 1.0 for k in qplan.STAGES} | {"total_hours": 20.0}
INPUTS = {"downloads": {"path": "/x", "sha256": "0" * 64}}
FAKE_WALK = {"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}


@pytest.fixture
def platform_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    rec = {"system": "Darwin", "machine": "arm64", "torch": "2.8.0", "torch_num_threads": 6, "torch_interop_threads": 1, "deterministic_algorithms": True, "release": "x", "platform": "x"}
    monkeypatch.setattr(gates, "platform_record", lambda: rec)


def frozen_repo(repo: Path, platform_ok: None) -> tuple[Path, str, planmod.Plan]:
    """Caps set, plan written and committed, freeze record written and committed: the freeze commit."""
    set_caps(repo, CAP_HOURS)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    rec = qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK)
    qplan.write_candidate(repo, rec)
    plan_sha = file_sha256(repo / core.PLAN_Q)
    write_json(repo / core.FREEZE_RECORD_Q, {"kind": "freeze_record", "plan_file_sha256": plan_sha})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    commit = git(repo, "rev-parse", "HEAD")
    return repo, commit, planmod.Plan.load(repo / core.PLAN_Q, "Q")


# --- the plan --------------------------------------------------------------------------------------------------------------------------------
def test_items_per_stage_and_layout() -> None:
    items = qplan.registered_items(CFG)
    assert {k: len(v) for k, v in items.items()} == {"inputs": 1, "partition": 1, "qfit": 2, "qcheck": 2, "generation": 2, "regeneration": 2, "outputs": 12}
    ids = [i["id"] for v in items.values() for i in v]
    assert len(set(ids)) == len(ids) == 22
    q = items["qcheck"][0]
    assert q["blocks"] == list(range(16)) and q["block_items"] == 500 and q["runs_after_failed_q1_q2"] is True
    assert items["qfit"][0]["batches"] == 63 and items["qfit"][0]["never_extended"] is True
    assert items["generation"][1]["target_accepted"] == 24000 and items["generation"][1]["minimum_accepted"] == 10000
    lay = qplan.layout(CFG)
    assert lay["batch_size"] == 32 and lay["threads"] == 6 and lay["digest"] == {"batches": 4, "seed": 250908, "stream": "Q_fit, the same draw indices for both teachers"}
    assert lay["regeneration"]["batches"] == 32 and lay["regeneration"]["seed"] == 250914 and lay["generation_block_sources"] == 20000 and lay["q_check_block"] == 500


def test_candidate_plan_written_once_superseded_never_deleted_never_after_freeze(repo: Path) -> None:
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    rec = qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK)
    path = qplan.write_candidate(repo, rec)
    first = file_sha256(path)
    with pytest.raises(core.StageRefused, match="supersede"):
        qplan.write_candidate(repo, rec)
    rec2 = {**rec, "note": "second"}
    qplan.write_candidate(repo, rec2, supersede=True)
    assert (repo / core.FREEZE_DIR / "superseded" / f"partq_plan-{first[:12]}.json").is_file()
    write_json(repo / core.FREEZE_RECORD_Q, {"kind": "freeze_record"})
    with pytest.raises(core.StageRefused, match="freeze record exists"):
        qplan.write_candidate(repo, rec2, supersede=True)


def test_plan_carries_every_threshold_the_config_has() -> None:
    cfg_rec = qplan.build_candidate(ROOT, ROOT / "experiments" / "_unused", CFG, inputs=INPUTS, walk=FAKE_WALK)
    assert cfg_rec["thresholds"] == CFG["quality"] and cfg_rec["seeds"]["bootstrap"] == 250915 and cfg_rec["adr"]["note"].startswith("provenance only")
    assert "studies/p10is2/common/core.py" in cfg_rec["frozen_files"] and "studies/p10is2/partq/pipeline.py" in cfg_rec["frozen_files"]
    assert not any(f.startswith("studies/p10is2/freeze/") for f in cfg_rec["frozen_files"])
    assert "uv.lock" in cfg_rec["frozen_files"] and "studies/p10s2/requirements-datagen.txt" in cfg_rec["frozen_files"] and "configs/p10is2_partq.toml" in cfg_rec["frozen_files"]
    assert "configs/p10is2_partt.toml" not in cfg_rec["frozen_files"]


def test_part_q_set_excludes_part_t_files_and_the_reverse() -> None:
    q, t = planmod.frozen_file_hashes(ROOT, "Q"), planmod.frozen_file_hashes(ROOT, "T")
    assert not any("/partq/" in f for f in t) and "configs/p10is2_partt.toml" in t and "studies/p10is2/common/core.py" in t
    assert not any(f.startswith("studies/p10is2/") and "/partq/" not in f and "/common/" not in f for f in q)


# --- caps by code ----------------------------------------------------------------------------------------------------------------------------
def test_caps_by_code_double_projected_and_total_counts_charge_once() -> None:
    proj = {"qfit": 1800.0, "generation": 36000.0}
    c = qplan.caps_proposal(7200.0, proj)
    assert c == {"qfit_hours": 1.0, "generation_hours": 20.0, "total_hours": 2.0 + 2 * (0.5 + 10.0)}
    assert qplan.caps_proposal(0.0, {"x": 1.0})["x_hours"] == 0.01  # rounded up to 0.01 h
    with pytest.raises(ValueError, match="no measured rate"):
        qplan.project_stage_seconds({"qfit": 10}, {})
    assert qplan.project_stage_seconds({"qfit": 100, "gen": 5}, {"qfit": 0.5, "gen": 2.0}) == {"qfit": 50.0, "gen": 10.0}
    cfg = small_cfg()
    cfg["stage_caps"]["qfit_hours"] = 1.0
    assert qplan.caps_match_config(cfg, {"qfit_hours": 1.0}) == [] and qplan.caps_match_config(cfg, {"qfit_hours": 1.01})


# --- registered preconditions ------------------------------------------------------------------------------------------------------------------
def test_refuses_dirty_tree_no_commit_bad_commit(repo: Path, platform_ok: None) -> None:
    repo, commit, _ = frozen_repo(repo, platform_ok)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    ident = planmod.check_preconditions("Q", "registered", repo, commit, cfg)
    assert ident and ident["commit"] == commit
    assert planmod.check_preconditions("Q", "rehearsal", repo, None, cfg) is None
    with pytest.raises(core.StageRefused, match="requires --freeze-commit"):
        planmod.check_preconditions("Q", "registered", repo, None, cfg)
    with pytest.raises(core.StageRefused, match="not a commit"):
        planmod.check_preconditions("Q", "registered", repo, "deadbeef" * 5, cfg)
    (repo / "junk.txt").write_text("x")
    with pytest.raises(core.StageRefused, match="not clean"):
        planmod.check_preconditions("Q", "registered", repo, commit, cfg)


def test_refuses_commit_not_ancestor_and_frozen_file_changed_after_freeze(repo: Path, platform_ok: None) -> None:
    repo, commit, _ = frozen_repo(repo, platform_ok)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    f = repo / "studies/p10is2/partq/split.py"
    f.write_text(f.read_text() + "\n# changed\n")
    git(repo, "commit", "-q", "-am", "edit a frozen file after the freeze")
    with pytest.raises(core.StageRefused, match="differs from the freeze commit"):
        planmod.check_preconditions("Q", "registered", repo, commit, cfg)
    git(repo, "checkout", "-q", "-b", "other", commit)
    (repo / "other.txt").write_text("o")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "other")
    other = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-")
    with pytest.raises(core.StageRefused, match="not an ancestor"):
        planmod.check_preconditions("Q", "registered", repo, other, cfg)


def test_refuses_another_studys_freeze_record_and_wrong_platform(repo: Path, platform_ok: None, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, commit, _ = frozen_repo(repo, platform_ok)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    other = repo / "studies/p10ir/freeze/freeze_record.json"
    other.parent.mkdir(parents=True)
    other.write_text("{}")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "foreign record")
    c2 = git(repo, "rev-parse", "HEAD")
    with pytest.raises(core.StageRefused, match="another study's freeze record"):
        planmod.check_preconditions("Q", "registered", repo, c2, cfg)
    git(repo, "rm", "-q", "-r", "studies/p10ir")
    git(repo, "commit", "-q", "-m", "remove")
    monkeypatch.setattr(gates, "platform_record", lambda: {"system": "Linux", "machine": "x86_64", "torch": "2.8.0", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": False})
    with pytest.raises(core.StageRefused, match="platform of record"):
        planmod.check_preconditions("Q", "registered", repo, commit, cfg)


def test_decision_2_must_be_committed_name_the_commit_and_say_run(repo: Path, platform_ok: None) -> None:
    repo, commit, _ = frozen_repo(repo, platform_ok)
    d = repo / "results/p10is2-partq-freeze-20261120/DECISION_2_PARTQ.md"
    with pytest.raises(core.StageRefused, match="no committed"):
        planmod.require_decision_2(repo, commit, "Q")
    d.parent.mkdir(parents=True)
    d.write_text(f"freeze {commit}\nDECISION: RUN\n")
    with pytest.raises(core.StageRefused, match="no committed"):  # in the working tree only: not committed
        planmod.require_decision_2(repo, commit, "Q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decision")
    assert planmod.require_decision_2(repo, commit, "Q").endswith("DECISION_2_PARTQ.md")
    d.write_text(f"freeze {commit}\nDECISION: RUN\nDECISION: DO NOT RUN\n")
    git(repo, "commit", "-q", "-am", "withdrawn")
    with pytest.raises(core.StageRefused):
        planmod.require_decision_2(repo, commit, "Q")
    d.write_text("freeze abc\nDECISION: RUN\n")
    git(repo, "commit", "-q", "-am", "other commit named")
    with pytest.raises(core.StageRefused):
        planmod.require_decision_2(repo, commit, "Q")
    with pytest.raises(core.StageRefused):  # Part T's decision file is a different glob
        planmod.require_decision_2(repo, commit, "T")


def test_run_directory_must_be_ignored_or_outside(repo: Path) -> None:
    core.require_ignored_run_dir(repo, repo / "runs" / "a")
    core.require_ignored_run_dir(repo, repo.parent / "elsewhere")
    with pytest.raises(core.StageRefused, match="not git-ignored"):
        core.require_ignored_run_dir(repo, repo / "tracked")
    with pytest.raises(core.StageRefused):
        core.require_ignored_path(repo, repo / "ledger.json")


# --- identity: PAUSED — IDENTITY ---------------------------------------------------------------------------------------------------------------
def test_identity_difference_is_paused_identity_and_resumes_on_restore(repo: Path, platform_ok: None) -> None:
    repo, commit, plan = frozen_repo(repo, platform_ok)
    run = repo / "runs"
    planmod.verify_plan(plan, repo, run, candidate=False)
    f = repo / "studies/p10is2/partq/labels.py"
    original = f.read_bytes()
    f.write_bytes(original + b"\n# x\n")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        planmod.verify_plan(plan, repo, run)
    f.write_bytes(original)
    planmod.verify_plan(plan, repo, run)  # restored bit for bit: the stage resumes
    with pytest.raises(core.StageRefused, match="run directory"):
        planmod.verify_plan(plan, repo, repo / "runs2")


def test_identity_exit_code_is_75_and_nothing_written(repo: Path, platform_ok: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo, commit, plan = frozen_repo(repo, platform_ok)
    (repo / "studies/p10is2/partq/labels.py").write_text("changed\n")
    git(repo, "commit", "-q", "-am", "x")  # changed AND committed: the frozen roots differ at HEAD, which is a plain refusal at the precondition
    rc = stages.main(["registered", "--stage", "qfit", "--run-dir", str(repo / "runs"), "--freeze-commit", commit, "--repo", str(repo)])
    assert rc == stages.EXIT_IDENTITY  # a frozen root that differs from the freeze commit is an identity difference: PAUSED — IDENTITY, exit 75
    assert not (repo / "runs").exists()
    # an UNCOMMITTED change fails the clean-tree precondition first; the identity exit is reached only where the tree is clean: see the verify_plan test above and the exit mapping below
    assert stages.EXIT_IDENTITY == 75 == planmod.IDENTITY_EXIT


def test_registered_entry_points_refuse_today_in_the_real_repository(tmp_path: Path) -> None:
    """Nothing is frozen: no plan, no freeze record, no Decision 2 in this checkout."""
    assert not (ROOT / core.PLAN_Q).exists() and not (ROOT / core.FREEZE_RECORD_Q).exists()
    for argv in (["registered", "--stage", "qfit", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "HEAD"], ["work", "--stage", "generation", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "HEAD"], ["registered", "--stage", "qfit", "--run-dir", str(tmp_path / "r")]):
        assert stages.main(argv) in (stages.EXIT_REFUSED, stages.EXIT_IDENTITY)  # a checkout with uncommitted frozen files (work in progress) is an identity pause, a clean one a plain refusal: never a run
    assert stages.main(["freeze", "--measuring-rehearsal", "m", "--counting-rehearsal", "c"]) == stages.EXIT_REFUSED
    assert stages.main(["registered", "--stage", "nonsense", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "HEAD"]) == stages.EXIT_REFUSED
    assert not (tmp_path / "r").exists()


def test_rehearse_refuses_outside_the_package_environment(tmp_path: Path) -> None:
    """Without the 28 packages on the durable path, offline, the real rehearsal refuses before reading anything."""
    assert stages.main(["rehearse", "--kind", "measuring", "--run-dir", str(tmp_path / "x")]) == stages.EXIT_REFUSED


# --- freeze refusals ---------------------------------------------------------------------------------------------------------------------------
def freeze_args(repo: Path, tmp: Path, **kw) -> argparse.Namespace:  # type: ignore[no-untyped-def]
    meas, cnt = tmp / "meas.json", tmp / "cnt.json"
    d = dict(repo=str(repo), measuring_rehearsal=str(meas), counting_rehearsal=str(cnt), attest_sealed_unopened="lead,implementer,auditor", seal_broken=False)
    d.update(kw)
    return argparse.Namespace(**d)


def measuring_record(tmp: Path, units: dict, rates: dict, charged: float = 3600.0) -> None:  # type: ignore[type-arg]
    core.write_record(tmp / "meas.json", {**core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "measuring", "caps_provisional": True, "rates_seconds_per_unit": rates, "projection_units": units, "charged_before_freeze_seconds": charged}, overwrite=True)


def test_freeze_refuses_provisional_caps_and_caps_that_are_not_the_codes(repo: Path, tmp_path: Path, platform_ok: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planmod, "import_walk", lambda *a, **k: FAKE_WALK)  # the throwaway repository holds no P10-S2 code to import
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    qplan.write_candidate(repo, qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK))
    with pytest.raises(core.StageRefused, match="provisional"):
        freeze.cmd_freeze(freeze_args(repo, tmp_path))
    set_caps(repo, CAP_HOURS)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    qplan.write_candidate(repo, qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK), supersede=True)
    measuring_record(tmp_path, {"qfit": 4000.0}, {"qfit": 0.5})
    with pytest.raises(core.StageRefused, match="not what the code computes"):
        freeze.cmd_freeze(freeze_args(repo, tmp_path))
    bad = tmp_path / "bad.json"
    core.write_record(bad, {**core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "counting", "caps_provisional": False}, overwrite=True)
    with pytest.raises(core.StageRefused, match="measuring rehearsal's record"):
        freeze.cmd_freeze(freeze_args(repo, tmp_path, measuring_rehearsal=str(bad)))


def test_freeze_refuses_a_counting_record_that_is_not_for_this_plan(repo: Path, tmp_path: Path, platform_ok: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planmod, "import_walk", lambda *a, **k: FAKE_WALK)
    units, rates = {k: 100.0 for k in qplan.STAGES}, {k: 36.0 for k in qplan.STAGES}  # 1 h projected per stage -> cap 2 h
    caps = qplan.caps_proposal(3600.0, qplan.project_stage_seconds(units, rates))
    set_caps(repo, caps)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    qplan.write_candidate(repo, qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK))
    measuring_record(tmp_path, units, rates)
    core.write_record(tmp_path / "cnt.json", {**core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "counting", "caps_provisional": False, "plan_file_sha256": "0" * 64, "stages": {s: {"status": "COMPLETE"} for s in qplan.STAGES}, "forced": {"pause_resume": True, "paused_identity_restore": True}}, overwrite=True)
    with pytest.raises(core.StageRefused, match="counting rehearsal's record"):
        freeze.cmd_freeze(freeze_args(repo, tmp_path))


def test_rehearsal_gate_rows() -> None:
    sha = "a" * 64
    good = {"kind_of_rehearsal": "counting", "caps_provisional": False, "plan_file_sha256": sha, "stages": {s: {"status": "COMPLETE"} for s in qplan.STAGES}, "forced": {"pause_resume": True, "paused_identity_restore": True}}
    assert gates.rehearsal_gate(good, qplan.STAGES, plan_file_sha256=sha)["passed"]
    assert not gates.rehearsal_gate(good, qplan.STAGES, plan_file_sha256="b" * 64)["passed"]
    assert not gates.rehearsal_gate({**good, "kind_of_rehearsal": "measuring"}, qplan.STAGES, plan_file_sha256=sha)["passed"]
    assert not gates.rehearsal_gate({**good, "caps_provisional": True}, qplan.STAGES, plan_file_sha256=sha)["passed"]
    assert not gates.rehearsal_gate({**good, "forced": {"pause_resume": True}}, qplan.STAGES, plan_file_sha256=sha)["passed"]
    assert not gates.rehearsal_gate({**good, "stages": {"qfit": {"status": "COMPLETE"}}}, qplan.STAGES, plan_file_sha256=sha)["passed"]
    assert not gates.rehearsal_gate(None, qplan.STAGES)["passed"]


# --- the import walk (C8) ------------------------------------------------------------------------------------------------------------------------
def test_import_walk_reaches_p10s2_and_its_config_read_at_import() -> None:
    w = planmod.import_walk(ROOT, "Q", ["studies.p10is2.partq.qualify"])
    assert "studies/p10s2/filtering.py" in w["outside_study_python"] and "studies/p10s2/core.py" in w["outside_study_python"]
    assert "src/arborlm/io.py" in w["outside_study_python"]
    assert "configs/p10s2_transfer.toml" in w["outside_study_data"]  # importing studies/p10s2 loads its config (correction C8)
    assert "studies/p10is2/partq/qualify.py" in w["python_files"]
    listed = planmod.walk_set(w, ROOT)
    assert planmod.walk_problems(w, listed, ROOT) == []
    assert any("studies/p10s2/core.py" in p for p in planmod.walk_problems(w, {k: v for k, v in listed.items() if k != "studies/p10s2/core.py"}, ROOT))
    assert any("differs" in p for p in planmod.walk_problems(w, {**listed, "studies/p10s2/core.py": "0" * 64}, ROOT))


def test_part_q_imports_the_rest_of_the_package_only_through_common() -> None:
    bad = []
    for p in (ROOT / "studies/p10is2/partq").glob("*.py"):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level == 2 and not (mod == "common" or mod.startswith("common.")) and not (mod == "" and all(a.name == "common" or a.name.startswith("common") for a in node.names)):
                    bad.append(f"{p.name}: from {'.' * node.level}{mod} import {[a.name for a in node.names]}")
                if node.level == 0 and mod.startswith("studies.p10is2") and not mod.startswith(("studies.p10is2.common", "studies.p10is2.partq")):
                    bad.append(f"{p.name}: {mod}")
            if isinstance(node, ast.Import):
                bad += [f"{p.name}: import {a.name}" for a in node.names if a.name.startswith("studies.p10is2") and not a.name.startswith(("studies.p10is2.common", "studies.p10is2.partq"))]
    assert bad == []


# --- real-path guards (no package, no real data) --------------------------------------------------------------------------------------------------
def test_wikitext_pins_from_adr_0004_and_the_hash_check(tmp_path: Path) -> None:
    pins = real.wikitext_pins(ROOT)
    assert pins["validation-00000-of-00001.parquet"] == {"bytes": 657209, "sha256": "204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c"}
    assert pins["train-00000-of-00001.parquet"]["bytes"] == 6357543
    with pytest.raises(core.StageRefused, match="does not exist"):
        real.check_wikitext(tmp_path / "nope", pins)
    d = tmp_path / "wt"
    d.mkdir()
    fake = {"a.parquet": {"bytes": 5, "sha256": file_sha256(_write(d / "a.parquet", b"hello"))}, "b.parquet": {"bytes": 3, "sha256": "0" * 64}}
    _write(d / "b.parquet", b"abc")
    with pytest.raises(core.StageRefused, match="does not match its pin"):
        real.check_wikitext(d, fake)
    assert real.check_wikitext(d, {"a.parquet": fake["a.parquet"]})["a.parquet"]["bytes"] == 5
    with pytest.raises(core.StageRefused, match="does not exist"):
        real.check_wikitext(d, {"c.parquet": {"bytes": 1, "sha256": "0" * 64}})


def _write(p: Path, b: bytes) -> Path:
    p.write_bytes(b)
    return p


def test_package_path_guard_names_only_the_durable_copy_offline() -> None:
    durable = CFG["paths"]["durable_packages"]
    ok = real.package_path_problems(CFG, {"PYTHONPATH": durable}, ["uv", "run", "--locked", "--offline", "--extra", "pilot", "python", "-m", "x"])
    assert ok == []
    assert real.package_path_problems(CFG, {"PYTHONPATH": "data/datagen-packages"}, ["--offline"])  # relative and not the durable copy
    assert any("not offline" in p for p in real.package_path_problems(CFG, {"PYTHONPATH": durable}, ["uv", "run"]))
    assert any("requirements" in p for p in real.package_path_problems(CFG, {"PYTHONPATH": durable}, ["uv", "run", "--offline", "--with-requirements", "studies/p10s2/requirements-datagen.txt"]))
    assert any("worktree" in p for p in real.package_path_problems(CFG, {"PYTHONPATH": f"{durable}:/Users/x/.claude/worktrees/a/data/datagen-packages"}, ["--offline"]))
    assert real.package_path_problems(CFG, {"PYTHONPATH": durable, "UV_OFFLINE": "1"}, ["uv", "run"]) == []
    assert real.part_t_package_problems({"PYTHONPATH": durable}, CFG) and real.part_t_package_problems({"PYTHONPATH": ""}, CFG) == []
    assert real.durable_inputs_problems(CFG) == []
    assert CFG["paths"]["packages_requirements_sha256"] == file_sha256(ROOT / CFG["paths"]["packages_requirements"])  # the set the human lead approved for P10-S2's data step


def test_delegation_section_7_condition(repo: Path) -> None:
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    assert freeze.delegation_section7_present(repo, cfg) in (True, False)
    p = repo / cfg["paths"]["delegation_record"]
    p.write_text("# record\n## 6 something\n")
    assert not freeze.delegation_section7_present(repo, cfg)
    p.write_text("# record\n## 7 the packages\n")
    assert freeze.delegation_section7_present(repo, cfg)


# --- gates -----------------------------------------------------------------------------------------------------------------------------------
def test_checker_copy_substitutions_apply_exactly_once_and_parse_problems() -> None:
    text = (ROOT / CFG["seeds"]["registry_checker"]).read_text()
    out = gates.checker_copy(text, Path("/x/y"))
    assert "ROOT = Path('/x/y')" in out and 'startswith("p10is2_")' in out and '"p10is2" not in q.name' in out
    with pytest.raises(ValueError):
        gates.checker_copy(text.replace("ROOT = Path(__file__).resolve().parents[3]", "ROOT = x"), Path("/x"))
    sample = "RESULT: FAIL\n    FAIL: P10-I-R ADR-0029 / x hits inventory: P10IR / a\n    FAIL: P10-I-S2 ADR-0025 / y hits inventory: P10IS2 / b\n"
    fl = gates.fail_lines(sample)
    assert len(fl) == 2 and [f for f in fl if any(m in f for m in gates.OWN_MARKERS)] == [fl[1]]


def test_seed_gate_passes_on_this_tree_and_detects_a_value_outside_the_rows() -> None:
    for part in ("Q", "T"):
        r = gates.seed_gate(part, core.load_config(part), root=ROOT)
        assert r["passed"], r["problems"]
        assert r["checker"]["problems_naming_this_study"] == [] and r["checker"]["copy_sha256"] and r["checker"]["allocation_rows"] == 8
    rows = gates.allocation_rows((ROOT / CFG["seeds"]["registry_checker"]).read_text())
    assert (  # the registry's rows of this study
        ("data: registered replicate sets (3)", 250001, 250899) in rows and ("init sub-row", 330201, 330299) in rows and ("test", 934001, 934999) in rows
    )
    cfg = core.load_config("Q")
    cfg["seeds"]["disjoint_permutation_a"] = 251999  # a value moved out of its row
    assert gates.allocation_problems("Q", cfg, rows)
    t = core.load_config("T")
    t["seeds"]["rehearsal_base"] = 253500
    assert gates.allocation_problems("T", t, rows)


def test_platform_problems_name_each_difference() -> None:
    rec = {"system": "Linux", "machine": "x86_64", "torch": "2.7.0", "torch_num_threads": 1, "torch_interop_threads": 1, "deterministic_algorithms": False}
    assert len(gates.platform_problems(CFG, rec)) == 5
    assert gates.platform_problems(CFG, {"system": "Darwin", "machine": "arm64", "torch": "2.8.0+cpu", "torch_num_threads": 6, "torch_interop_threads": 3, "deterministic_algorithms": True}) == []


# --- the rehearsal drivers on synthetic data -------------------------------------------------------------------------------------------------------
def ctx_factory(tmp: Path, **kw):  # type: ignore[no-untyped-def]
    def make() -> pipeline.QContext:
        d = dict(cfg=small_cfg(), mode="test", corpus=small_corpus(), teachers=lex_teachers(), student_scores=stub_student, run_dir=tmp / "reh", sizes=SMALL_SIZES, batch_size=8, block_sources=100, accepted_min=30, accepted_disjoint=300, per_replicate=20, regeneration_batches=3, digest_batches=2, seal=True)
        d.update(kw)
        return pipeline.QContext(**d)

    return make


def test_measuring_rehearsal_measures_and_seals(tmp_path: Path) -> None:
    rec = reh.run_measuring(ctx_factory(tmp_path), cap_seconds=3600.0, charged_before_freeze_seconds=12.0)
    assert rec["kind_of_rehearsal"] == "measuring" and rec["caps_provisional"] is True and rec["cannot_be_frozen_on"] is True
    assert set(rec["rates_seconds_per_unit"]) >= {"partition", "qfit", "qcheck", "generation"} and all(v > 0 for v in rec["rates_seconds_per_unit"].values())
    assert rec["projection_units"]["generation"] > rec["projection_units"]["qfit"] > 0 and rec["charged_before_freeze_seconds"] == 12.0
    assert rec["memory"]["peak_rss_mib"] > 0 and len(rec["load"]["start"]) == 3
    run = tmp_path / "reh"
    assert (run / "sealed/qfit_values.json").is_file() and (run / "sealed/qfit_record.json").is_file() and not (run / "qfit/record.json").exists()
    assert not (run / "qualification.json").exists() and (run / "sealed/qualification.json").is_file()
    shown = json.dumps({k: v for k, v in rec.items() if k != "oracle_line"})  # the fixed line itself says "measured-precision filter"
    for hidden in ("q1", "q2", "q3", "q4", "chrf", "precision", "TEACHERS-QUALIFIED", "QUALIFICATION-"):
        assert hidden not in shown.replace("seconds_per_generated_source", "")  # no quality value or label in what is displayed
    assert rec["filter_setting"]["A"] is not None  # the chosen filter setting and the yields are visible (section 10)


def test_whitelist_refuses_sealed_keys() -> None:
    assert reh.whitelist({"counts": {"x": 1}, "timings": {}, "junk": 3}) == {"counts": {"x": 1}, "timings": {}}
    with pytest.raises(ValueError, match="sealed key"):
        reh.whitelist({"q1": True})
    with pytest.raises(ValueError, match="sealed key"):
        reh.whitelist({"per_item_chrf": []})


def test_counting_rehearsal_forces_one_pause_and_one_identity_pause(tmp_path: Path) -> None:
    probes = {"n": 0}

    def probe() -> None:
        probes["n"] += 1
        raise core.ForcedIdentityPause("PAUSED — IDENTITY")

    rec = reh.run_counting(ctx_factory(tmp_path, seal=True), plan_file_sha256="c" * 64, caps_provisional=False, cap_seconds=10800.0, identity_probe=probe, pause_after_batches=4)
    assert rec["kind_of_rehearsal"] == "counting" and rec["plan_file_sha256"] == "c" * 64
    assert rec["forced"] == {"pause_resume": True, "paused_identity_restore": True} and probes["n"] == 1
    assert rec["stages"]["qfit"]["status"] == "COMPLETE" and rec["stages"]["inputs"]["status"] == "NOT RUN" and rec["status"] == "INCOMPLETE"  # nothing is called COMPLETE that did not run
    assert rec["timings"]["resume_seconds"] >= 0


def test_stage_statuses_follow_the_records_on_disk(tmp_path: Path) -> None:
    ctx = ctx_factory(tmp_path)()
    assert not any(reh.stage_statuses(ctx).values())
    pipeline.run_all(ctx)
    st = reh.stage_statuses(ctx)
    assert st["partition"] and st["qfit"] and st["qcheck"] and st["generation"] and st["regeneration"] and not st["inputs"] and not st["outputs"]


def test_a_changed_frozen_file_is_paused_identity_and_resumes_on_restore(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R5, without patching the platform check or the preconditions: an UNCOMMITTED change of a frozen file gives exit 75 and writes nothing; restoring it bit for bit lets the very same launch reach its stage."""
    import platform as pf

    if not (pf.system() == "Darwin" and pf.machine() == "arm64"):
        pytest.skip("the platform of record")
    repo, commit, _ = frozen_repo_real_platform(repo)
    d = repo / "results/p10is2-partq-freeze-20261201/DECISION_2_PARTQ.md"
    d.parent.mkdir(parents=True)
    d.write_text(f"freeze {commit}\nDECISION: RUN\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "decision 2")
    reached: list[str] = []
    monkeypatch.setattr(real, "run_registered_stage", lambda stage, repo_, run_dir, plan: reached.append(stage) or {"status": "COMPLETE"})
    argv = ["registered", "--stage", "qfit", "--run-dir", str(repo / "runs"), "--freeze-commit", commit, "--repo", str(repo)]
    f = repo / "studies/p10is2/partq/labels.py"
    original = f.read_bytes()
    f.write_bytes(original + b"\n# edited\n")
    assert stages.main(argv) == stages.EXIT_IDENTITY == 75 and reached == [] and not (repo / "runs").exists()
    f.write_bytes(original)
    assert stages.main(argv) == 0 and reached == ["qfit"]


def frozen_repo_real_platform(repo: Path):  # type: ignore[no-untyped-def]
    set_caps(repo, CAP_HOURS)
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    rec = qplan.build_candidate(repo, repo / "runs", cfg, inputs=INPUTS, walk=FAKE_WALK)
    qplan.write_candidate(repo, rec)
    write_json(repo / core.FREEZE_RECORD_Q, {"kind": "freeze_record", "plan_file_sha256": file_sha256(repo / core.PLAN_Q)})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    return repo, git(repo, "rev-parse", "HEAD"), None
