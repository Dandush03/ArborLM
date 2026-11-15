# ruff: noqa: E501
"""P10S1 stages (ADR-0021 sections 8.1, 10, 11): the guards (calibration, registered, modes and seeds, freeze preconditions, ledger), the freeze plan verification, the freeze procedure
and its refusals, and the DRY stage end to end at tiny synthetic size (generate, calibrate, gates, rehearse, isolated timing, synthetic registry, projection, freeze, gates, train,
evaluate, throughput, simulate, analysis, report). Nothing here uses a verified backbone, a calibration or rehearsal draw or a registered seed; the DRY profile uses test seeds
(921001+) and a random synthetic backbone. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import canonical_json, file_sha256, sha256  # noqa: E402
from studies.p9 import pool  # noqa: E402
from studies.p10s1 import budget, core, stages  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def parse(*argv: str) -> Any:
    return stages.build_parser().parse_args(list(argv))


# --- guards -------------------------------------------------------------------------------------------------------------------------
def test_calibration_guard_allows_only_the_calibration_cells() -> None:
    for cell in core.calibration_cells(True):
        stages.calibration_guard(cell)
    for cell in core.calibration_cells(True, 8):
        stages.calibration_guard(cell, 8)
    for cell in core.registered_cells(core.Plan(seed_block_draws=(1, 2))):
        with pytest.raises(stages.CalibrationRefused):
            stages.calibration_guard(cell)
    bad = (
        core.make_cell("CAL", "F-OQ", 8192, 4096, 3, 2191, run_updates=65536),  # a draw that is not a calibration draw
        core.make_cell("CAL", "T-OQ", 8192, 4096, 1, 2191, run_updates=65536),  # T-OQ is never run in calibration
        core.make_cell("CAL", "F-OQ", 8192, 4096, 1, 2101, run_updates=65536),  # not the calibration initialization seed
        core.make_cell("CAL", "F-OQ", 8192, 4096, 1, 2191, run_updates=100),  # not a registered calibration run length
        core.make_cell("P", "F-OQ", 8192, 4096, 1, 2191),
    )
    for cell in bad:
        with pytest.raises(stages.CalibrationRefused):
            stages.calibration_guard(cell)


def test_calibrate_worker_refuses_other_cells_before_building_anything(tmp_path: Path) -> None:
    registered = core.registered_cells(core.Plan())[0].label
    for label in (registered, "TEST_P_F-OQ_f128_n4096_d1_i2101_y8", "CAL_F-OQ_f8192_n4096_d3_i2191_y65536", "nonsense"):
        code = stages.main(["work", "calibrate-cell", "--labels", label, "--run-dir", str(tmp_path), "--mode", "calibration", "--dry"])
        assert code == 2
    assert not list(tmp_path.rglob("*"))


def test_registered_guard_allows_only_the_frozen_registry() -> None:
    fro = fz.Frozen.build(core.Plan(seed_block_draws=(1,), dense_cut=("8K/64K",)), fz.default_cpu_table())
    for cell in core.registered_cells(fro.plan, dense_rates=fro.dense_rates):
        if cell.kind != "LN":
            stages.registered_guard(cell, fro)
    cut = core.make_cell("P", "D-OQ", 8192, 65536, 1, 2101)
    for refused in (cut, core.calibration_cells()[0], core.make_cell("SB", "F-OQ", 8192, 4096, 2, 2112), core.make_cell("P", "F-OQ", 8192, 4096, 1, 2999), core.lane_cells()[0]):
        with pytest.raises(stages.RegisteredRefused):
            stages.registered_guard(refused, fro)


def test_seed_sets_follow_the_mode() -> None:
    assert stages.seeds_for(parse("train", "--mode", "registered", "--draw", "3")).facts == 210201
    assert stages.seeds_for(parse("train", "--mode", "calibration", "--draw", "2")).facts == 219101
    assert stages.seeds_for(parse("train", "--mode", "rehearsal")).facts == 219201
    assert stages.seeds_for(parse("train", "--mode", "calibration", "--dry")).facts == 921001
    for bad in (("--mode", "registered", "--dry"), ("--mode", "registered", "--synthetic-backbone")):
        with pytest.raises(pool.StageRefused):
            stages.seeds_for(parse("train", *bad))
    with pytest.raises(ValueError):
        stages.seeds_for(parse("train", "--mode", "calibration", "--draw", "3"))
    with pytest.raises(ValueError):
        stages.seeds_for(parse("train", "--mode", "registered", "--draw", "6"))
    with pytest.raises(ValueError):
        core.check_seed_set("rehearsal", stages.seeds_for(parse("train", "--mode", "calibration", "--draw", "1")).name)
    assert stages.seeds_for(parse("train", "--mode", "calibration", "--draw", "1")).name == "p10s1-cal-1"


def test_registered_mode_refuses_without_freeze_plan_or_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "repo_root", lambda: tmp_path)  # the driver takes no --repo (section 22 M3): the tests move the repository instead
    assert stages.main(["registered", "train", "--run-dir", str(tmp_path)]) == 2  # no freeze commit
    assert stages.main(["registered", "train", "--run-dir", str(tmp_path), "--freeze-commit", "deadbeef"]) == 2  # not a commit
    with pytest.raises(SystemExit):
        stages.main(["registered", "stage1", "--run-dir", str(tmp_path)])
    with pytest.raises(pool.StageRefused, match="no freeze plan"):
        stages.load_plan(tmp_path)
    assert stages.main(["train", "--dry", "--mode", "registered", "--run-dir", str(tmp_path)]) == 2
    assert stages.main(["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp_path)]) == 2  # needs --i-understand-freeze-time
    assert stages.main(["train", "--run-dir", str(tmp_path), "--mode", "registered"]) == 2  # registered mode through the plain command: no preconditions, no freeze commit
    assert not list(tmp_path.rglob("*"))
    assert stages.REGISTERED_STAGES == ("gates", "train", "evaluate", "timing", "simulate", "analysis", "report")


# --- preconditions in a throw-away git repository --------------------------------------------------------------------------------------
def git(repo: Path, *argv: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, text=True, check=True, env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})
    return r.stdout.strip()


def make_repo(tmp: Path) -> tuple[Path, str]:
    repo = tmp / "repo"
    for rel, text in (("studies/a.py", "x = 1\n"), (str(core.DEFAULT_CONFIG), "c = 1\n"), (core.SPEC, "adr\n"), ("tests/test_p10s1_x.py", "def test_x(): pass\n"), ("tests/test_other.py", "pass\n")):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    return repo, git(repo, "rev-parse", "HEAD")


def test_check_preconditions_refusals(tmp_path: Path) -> None:
    assert stages.check_preconditions("calibration", tmp_path, None) is None and stages.check_preconditions("rehearsal", tmp_path, None) is None
    repo, c1 = make_repo(tmp_path)
    with pytest.raises(pool.StageRefused, match="requires --freeze-commit"):
        stages.check_preconditions("registered", repo, None)
    with pytest.raises(pool.StageRefused, match="not a commit"):
        stages.check_preconditions("registered", repo, "deadbeef")
    (repo / "untracked.txt").write_text("x")
    with pytest.raises(pool.StageRefused, match="not clean"):
        stages.check_preconditions("registered", repo, c1)
    (repo / "untracked.txt").unlink()
    with pytest.raises(pool.StageRefused, match="frozen inputs do not verify"):  # everything matches the commit: the next check (src/arborlm, uv.lock) is reached and the tmp repo has none
        stages.check_preconditions("registered", repo, c1)
    for rel, expect in (("studies/a.py", "studies at HEAD differs"), (str(core.DEFAULT_CONFIG), "p10s1_capacity.toml at HEAD differs"), (core.SPEC, "ADR-0021"), ("tests/test_p10s1_x.py", "test_p10s1_x.py differs")):
        (repo / rel).write_text("changed\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "after the freeze")
        with pytest.raises(pool.StageRefused, match=expect):
            stages.check_preconditions("registered", repo, c1)
        git(repo, "reset", "-q", "--hard", c1)
    (repo / "tests/test_other.py").write_text("changed\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "other test")
    with pytest.raises(pool.StageRefused, match="frozen inputs do not verify"):  # a test file outside tests/test_p10s1_* is not part of the freeze
        stages.check_preconditions("registered", repo, c1)
    git(repo, "reset", "-q", "--hard", c1)
    git(repo, "checkout", "-q", "-b", "side")
    git(repo, "commit", "-q", "--allow-empty", "-m", "side")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-")
    with pytest.raises(pool.StageRefused, match="not an ancestor"):
        stages.check_preconditions("registered", repo, side)


# --- ledger ----------------------------------------------------------------------------------------------------------------------------------
def test_a_stage_refuses_to_start_below_its_cap_and_charges_what_it_used(tmp_path: Path) -> None:
    ledger = core.Ledger.from_config(tmp_path)
    assert ledger.cap_seconds == core.cap_seconds() == 16 * 3600.0
    code = stages.main(["synthetic", "--dry", "--mode", "rehearsal", "--run-dir", str(tmp_path / "r"), "--ledger-root", str(tmp_path), "--stage-cap-seconds", str(core.cap_seconds() + 3600.0)])
    assert code == 2 and not (tmp_path / "r").exists() and ledger.charged() == 0.0  # the stage cap exceeds the whole cap: refused before anything runs
    ledger.charge("earlier", "run", core.cap_seconds() - 400.0)
    code = stages.main(["synthetic", "--dry", "--mode", "rehearsal", "--run-dir", str(tmp_path / "r"), "--ledger-root", str(tmp_path), "--stage-cap-seconds", "500"])
    assert code == 2 and not (tmp_path / "r").exists()  # 400 s remain: below the stage cap of 500 s
    assert len(ledger.entries()) == 1


# --- the freeze plan, verified and tampered ------------------------------------------------------------------------------------------------
def make_freeze(tmp: Path) -> tuple[Path, Path, dict[str, Any]]:
    """A throw-away repository (a copy of ``studies/``, the config and the ADR), a run directory with five data manifests and a plan whose every hash holds."""
    repo, run = tmp / "repo", tmp / "run"
    shutil.copytree(ROOT / "studies", repo / "studies", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (repo / "configs").mkdir(parents=True)
    shutil.copy(ROOT / core.DEFAULT_CONFIG, repo / core.DEFAULT_CONFIG)
    (repo / core.SPEC).parent.mkdir(parents=True)
    shutil.copy(ROOT / core.SPEC, repo / core.SPEC)
    plan = core.Plan(seed_block_draws=(1,))
    fro = fz.Frozen.build(plan, fz.default_cpu_table())
    files = {}
    for name, body in (("calibration", {"hyper": 1}), ("timing", {"cpu_per_update": 1}), ("rehearsal_gates", {"g": 1}), ("synthetic", {"s": 1})):
        p = tmp / f"{name}.json"
        p.write_text(json.dumps(body))
        files[name] = {"path": str(p), "sha256": file_sha256(p)}
    proj = tmp / "projection.json"
    proj.write_text(json.dumps({**core.envelope("projection"), "calibration_sha256": files["calibration"]["sha256"]}))
    files["projection"] = {"path": str(proj), "sha256": file_sha256(proj)}
    caps = repo / stages.CAPS_FILE
    caps.parent.mkdir(parents=True, exist_ok=True)
    caps.write_text(json.dumps({"rule": "x"}))
    manifests = {}
    for name in core.DRAW_NAMES:
        m = stages.manifest_dir(run, name) / "data_manifest.json"
        m.parent.mkdir(parents=True, exist_ok=True)
        m.write_text(json.dumps({"g1_passed": True, "name": name}))
        manifests[name] = file_sha256(m)
    record = {**files, "stage_caps_sha256": file_sha256(caps), "run_dir": str(run.resolve()), "data_manifests": manifests, "frozen": fro.as_json(), "frozen_sha256": sha256(canonical_json(fro.as_json())), "cap_seconds": core.cap_seconds(), "identity": core.code_identity(repo)}
    return repo, run, record


def test_verify_plan_accepts_a_consistent_freeze_and_refuses_every_tamper(tmp_path: Path) -> None:
    repo, run, plan = make_freeze(tmp_path)
    stages.verify_plan(plan, repo, run)  # a consistent freeze passes

    def refuses(match: str, **changes: Any) -> None:
        with pytest.raises(pool.StageRefused, match=match):
            stages.verify_plan({**plan, **changes}, repo, run)

    refuses("does not hash to the frozen calibration", calibration={**plan["calibration"], "sha256": "0" * 64})
    refuses("does not hash to the frozen projection", projection={"path": str(tmp_path / "nowhere.json"), "sha256": plan["projection"]["sha256"]})
    refuses("frozen timing", timing={**plan["timing"], "sha256": "1" * 64})
    refuses("frozen rehearsal_gates", rehearsal_gates={**plan["rehearsal_gates"], "sha256": "1" * 64})
    refuses("stage-cap table", stage_caps_sha256="2" * 64)
    refuses("run directory", run_dir=str(tmp_path / "elsewhere"))
    refuses("five registered draws", data_manifests={k: v for k, v in list(plan["data_manifests"].items())[:4]})
    refuses("data manifest of p10s1-draw-3", data_manifests={**plan["data_manifests"], "p10s1-draw-3": "3" * 64})
    refuses("frozen plan and tables", frozen={**plan["frozen"], "cuts": ["tampered"]})
    refuses("cap in the config differs", cap_seconds=plan["cap_seconds"] + 1.0)
    refuses("identity of the freeze", identity={**plan["identity"], "source_sha256": "4" * 64})
    (run / "draws" / "p10s1-draw-1" / "data_manifest.json").write_text("{}")
    refuses("data manifest of p10s1-draw-1")


def test_verify_plan_refuses_a_projection_not_bound_to_the_frozen_calibration(tmp_path: Path) -> None:
    repo, run, plan = make_freeze(tmp_path)
    proj = Path(plan["projection"]["path"])
    proj.write_text(json.dumps({**core.envelope("projection"), "calibration_sha256": "5" * 64}))
    with pytest.raises(pool.StageRefused, match="not bound to the frozen calibration"):
        stages.verify_plan({**plan, "projection": {**plan["projection"], "sha256": file_sha256(proj)}}, repo, run)


def test_verify_plan_refuses_code_or_config_edited_after_the_freeze(tmp_path: Path) -> None:
    repo, run, plan = make_freeze(tmp_path / "code")
    (repo / "studies" / "p10s1" / "gates.py").write_text((repo / "studies" / "p10s1" / "gates.py").read_text() + "\n# edited after the freeze\n")
    with pytest.raises(pool.StageRefused, match="identity of the freeze"):
        stages.verify_plan(plan, repo, run)
    repo2, run2, plan2 = make_freeze(tmp_path / "cap")
    (repo2 / "configs" / "p10s1_capacity.toml").write_text(core.render_config_toml(20.0))  # the lead changed the cap after the freeze
    with pytest.raises(pool.StageRefused, match="cap in the config differs"):
        stages.verify_plan(plan2, repo2, run2)
    repo3, run3, plan3 = make_freeze(tmp_path / "script")
    (repo3 / "studies" / "p10s1" / "launch" / "train.sh").write_text("#!/bin/sh\necho changed\n")  # a launch script is part of the identity
    with pytest.raises(pool.StageRefused, match="identity of the freeze"):
        stages.verify_plan(plan3, repo3, run3)


# --- the freeze procedure --------------------------------------------------------------------------------------------------------------------------
def fake_projection(tmp: Path, **over: Any) -> dict[str, Path]:
    """A projection record whose bindings hold, with the files it binds."""
    paths: dict[str, Path] = {}
    bound = {}
    for name, rec in (("calibration", {**core.envelope("calibration"), "load_decision": {"action": "GRID_STANDS"}}), ("timing", {**core.envelope("timing"), "status": "MEASURED"}), ("gates", {**core.envelope("gates"), "wall_seconds": 1.0}), ("synthetic", {**core.envelope("rehearsal")})):
        p = tmp / f"{name}.json"
        core.write_record(p, rec)
        paths[name] = p
        bound[name] = {"path": str(p.resolve()), "sha256": file_sha256(p)}
    plan = core.Plan(None, (1,), ("8K/64K",))
    cpu = {f"{a}|{n}": v for (a, n), v in fz.default_cpu_table().items()}
    fro = fz.Frozen.build(plan, fz.default_cpu_table())
    caps = budget.caps_table({i: budget.Rate(0.01, 5.0, 2.0, 10**9, 0, 0, 0) for i in budget.rehearsal_items()}, budget.Fixed(), fz.default_cpu_table())
    record = {
        **core.envelope("projection"), "calibration": bound["calibration"], "timing": bound["timing"], "rehearsal_gates": bound["gates"], "synthetic": bound["synthetic"], "calibration_sha256": bound["calibration"]["sha256"],
        "returns_to_lead": [], "memory": {"ok": True}, "cap_seconds": core.cap_seconds(), "chosen": {"ok": True, "plan": plan.as_json(), "applied_cuts": ["cut 1", "cut 2", "cut 3: D-OQ at 8K/64K"], "headroom": {"ok": True}},
        "caps": caps, "cpu_per_update": cpu, "dense_rates": {"4096": 0.003, "16384": 0.01, "65536": 0.001}, "h8_undertrained": ["8K/16K"], **over,
    }  # fmt: skip
    p = tmp / "projection.json"
    core.write_record(p, record)
    paths["projection"] = p
    assert fro.plan == plan
    return paths


def run_dir_with_draws(tmp: Path) -> Path:
    run = tmp / "run"
    for name in core.DRAW_NAMES:
        m = stages.manifest_dir(run, name) / "data_manifest.json"
        core.write_record(m, {**core.envelope("data_manifest"), "g1_passed": True, "seed_set": name})
    return run


def projection_in(tmp: Path, name: str, **over: Any) -> dict[str, Path]:
    folder = tmp / name
    folder.mkdir()
    return fake_projection(folder, **over)


def config_repo(folder: Path) -> Path:
    """A directory holding the config with a generation cap the rehearsal has set (the freeze refuses a provisional one)."""
    repo = folder / "config-repo"
    if not repo.exists():
        (repo / "configs").mkdir(parents=True)
        (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(generation={"cap_seconds": 600.0, "provisional": False, "table_facts": core.FACT_TABLE}))
    return repo


def freeze_argv(paths: dict[str, Path], run: Path, out: Path, *extra: str) -> list[str]:
    return ["freeze", "--run-dir", str(run), "--projection", str(paths["projection"]), "--calibration", str(paths["calibration"]), "--timing", str(paths["timing"]), "--gates", str(paths["gates"]), "--freeze-dir", str(out), "--repo", str(config_repo(out.parent)), *extra]


def test_freeze_writes_plan_and_caps_deterministically(tmp_path: Path) -> None:
    paths = fake_projection(tmp_path)
    run = run_dir_with_draws(tmp_path)
    assert stages.main(freeze_argv(paths, run, tmp_path / "f1")) == 0 and stages.main(freeze_argv(paths, run, tmp_path / "f2")) == 0
    for name in ("plan.json", "stage_caps.json"):
        assert (tmp_path / "f1" / name).read_bytes() == (tmp_path / "f2" / name).read_bytes()  # a pure function of its inputs
    plan = json.loads((tmp_path / "f1" / "plan.json").read_text())
    assert plan["stage_caps_sha256"] == file_sha256(tmp_path / "f1" / "stage_caps.json") and set(plan["data_manifests"]) == set(core.DRAW_NAMES) and plan["cap_seconds"] == core.cap_seconds()
    fro = fz.Frozen.from_json(plan["frozen"])
    assert fro.plan == core.Plan(None, (1,), ("8K/64K",)) and fro.dense_rates == {4096: 0.003, 16384: 0.01, 65536: 0.001} and fro.h8_undertrained == ["8K/16K"] and fro.s0_status == fz.S0_NOT_DECIDED
    assert fro.lane_status == fz.LANE_OMITTED_NO_INTERFACE and fro.cuts == ["cut 1", "cut 2", "cut 3: D-OQ at 8K/64K"] and plan["frozen_sha256"] == sha256(canonical_json(plan["frozen"]))
    assert plan["identity"] == core.code_identity() and plan["lane_l"] == fz.LANE_OMITTED_NO_INTERFACE
    assert stages.main(freeze_argv(paths, run, tmp_path / "f1")) == 2  # a freeze is written once
    s0 = tmp_path / "s0.json"
    s0.write_text(json.dumps({"outcome": "ADDRESSING-NOT-QUALIFIED"}))
    again = stages.main(freeze_argv(paths, run, tmp_path / "f3", "--s0-record", str(s0), "--no-loaded-transitions", "16K→64K"))
    plan3 = json.loads((tmp_path / "f3" / "plan.json").read_text())
    assert again == 0 and plan3["frozen"]["s0_status"] == "S0 ADDRESSING-NOT-QUALIFIED" and plan3["frozen"]["no_loaded_transitions"] == ["16K→64K"] and plan3["s0_record"]["sha256"] == file_sha256(s0)


def test_freeze_refusals(tmp_path: Path) -> None:
    paths = fake_projection(tmp_path)
    run = run_dir_with_draws(tmp_path)
    assert stages.main(freeze_argv(paths, run, tmp_path / "lane", "--lane-l")) == 2 and not (tmp_path / "lane").exists()  # lane L is not implemented
    open_return = projection_in(tmp_path, "ret", returns_to_lead=["the U_P check failed"])
    assert stages.main(freeze_argv(open_return, run, tmp_path / "f_ret")) == 2 and not (tmp_path / "f_ret").exists()
    no_plan = projection_in(tmp_path, "np", chosen={"ok": False, "plan": None, "applied_cuts": [], "headroom": None})
    assert stages.main(freeze_argv(no_plan, run, tmp_path / "f_np")) == 2
    bad_mem = projection_in(tmp_path, "bm", memory={"ok": False})
    assert stages.main(freeze_argv(bad_mem, run, tmp_path / "f_bm")) == 2
    cap_moved = projection_in(tmp_path, "cm", cap_seconds=core.cap_seconds() + 3600.0)
    assert stages.main(freeze_argv(cap_moved, run, tmp_path / "f_cm")) == 2  # the cap changed after the projection
    other = tmp_path / "other_cal.json"
    other.write_text(paths["calibration"].read_text().replace("GRID_STANDS", "OVERLOAD_ROW"))
    assert stages.main(["freeze", "--run-dir", str(run), "--projection", str(paths["projection"]), "--calibration", str(other), "--timing", str(paths["timing"]), "--gates", str(paths["gates"]), "--freeze-dir", str(tmp_path / "f_h")]) == 2
    missing = tmp_path / "run_missing"
    for name in core.DRAW_NAMES[:4]:
        core.write_record(stages.manifest_dir(missing, name) / "data_manifest.json", {**core.envelope("data_manifest"), "g1_passed": True})
    assert stages.main(freeze_argv(paths, missing, tmp_path / "f_m")) == 2
    failed_g1 = run_dir_with_draws(tmp_path / "g1")
    core.write_record(stages.manifest_dir(failed_g1, "p10s1-draw-2") / "data_manifest.json", {**core.envelope("data_manifest"), "g1_passed": False})
    assert stages.main(freeze_argv(paths, failed_g1, tmp_path / "f_g1")) == 2
    assert not any((tmp_path / n).exists() for n in ("f_ret", "f_np", "f_bm", "f_cm", "f_h", "f_m", "f_g1"))


def test_project_refuses_without_its_bindings(tmp_path: Path) -> None:
    assert stages.main(["project", "--mode", "rehearsal", "--run-dir", str(tmp_path)]) == 2
    assert stages.main(["project", "--mode", "rehearsal", "--run-dir", str(tmp_path), "--calibration", "x", "--timing", "y", "--gates", "z"]) == 2  # --synthetic missing


def test_rehearse_is_bound_to_the_calibration_record(tmp_path: Path) -> None:
    assert stages.main(["rehearse", "--run-dir", str(tmp_path / "r"), "--stage-cap-seconds", "100"]) == 2  # no --calibration
    assert not (tmp_path / "r").exists()


def test_generate_and_stage_codes_use_the_experiments_root(tmp_path: Path) -> None:
    assert stages.experiments_root(parse("train", "--experiments-root", str(tmp_path))) == tmp_path
    assert stages.experiments_root(parse("train")).name == "experiments" and core.default_experiments_root().parent.name == "ArborLM"
    n = core.run_name("calibrate")
    assert n.startswith("P10S1C-")


# --- the DRY stage, end to end -----------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dry(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    root = tmp_path_factory.mktemp("dry")
    code = stages.main(["dry", "--workers", "6", "--out-root", str(root)])
    summary = json.loads((root / "DRY_SUMMARY.json").read_text())
    yield {"root": root, "code": code, "summary": summary, "run": Path(summary["run_dir"]), "reh": root / "P10S1DRY-rehearsal", "cal": root / "P10S1DRY-calibration", "freeze": root / "freeze"}
    shutil.rmtree(root, ignore_errors=True)  # the DRY stage's outputs are removed when the module's tests end


def test_dry_runs_every_stage_in_order(dry: dict[str, Any]) -> None:
    s = dry["summary"]
    assert dry["code"] == 0 and s["status"] == "COMPLETE" and s["report"] and Path(s["report"]).is_file()
    assert sorted(s["stages"]) == sorted(["generate", "generate-rehearsal", "calibrate", "gates", "rehearse", "timing", "synthetic", "project", "freeze", "gates-run", "train", "evaluate", "throughput", "simulate", "analyze", "report"])
    assert all(code == 0 for name, code in s["stages"].items() if name != "calibrate")
    assert s["stages"]["calibrate"] in (0, 1)  # tiny numbers: the calibration's returns to the human lead are listed, not acted on
    assert "DRY" in s["banner"] and s["capacity"] in (C.CAPACITY_INCONCLUSIVE, C.CAPACITY_NOT_TESTED, C.CAPACITY_NEGATIVE, C.CAPACITY_POSITIVE)


def test_dry_charges_one_ledger_below_the_config_cap(dry: dict[str, Any]) -> None:
    ledger = core.Ledger.from_config(dry["root"])
    stages_charged = [e["stage"] for e in ledger.entries()]
    assert 0 < ledger.charged() < ledger.cap_seconds and ledger.cap_seconds == core.cap_seconds()
    for stage in ("calibrate", "gates", "rehearse", "timing", "synthetic", "train", "evaluate", "simulate", "analyze", "report"):
        assert stage in stages_charged
    assert abs(dry["summary"]["charged_seconds"] - ledger.charged()) < 1e-6


def test_dry_every_run_manifest_records_environment_and_cap(dry: dict[str, Any]) -> None:
    manifests = sorted(dry["run"].glob("*/manifest.json"))
    assert len(manifests) >= 8
    for p in manifests:
        m = core.read_record(p, "stage_manifest")
        env = m["environment"]
        assert env["platform"] and env["python"] and env["torch"] and "threads" in env and env["threads"]["torch_num_threads"] >= 1 and m["cap_seconds"] == core.cap_seconds() and m["identity"] and m["caps"]["stage_seconds"] > 0
        assert m["study"] == "P10S1" and m["status"] == "COMPLETE" and all(t["status"] == "completed" for t in m["tasks"])
        assert m["caps"]["rss_worker_bytes"] == 3 * 1024**3 and m["caps"]["rss_aggregate_bytes"] == 18 * 1024**3 and 1 <= m["workers"] <= 6


def test_dry_gates_cover_every_configuration_and_every_gate(dry: dict[str, Any]) -> None:
    g = core.read_record(dry["reh"] / "gates.json", "gates")
    assert g["configurations_checked"] == 30 and all(g[f"{n}_passed"] is True for n in stages.GATE_NAMES) and g["harness_errors"] == [] and g["g4_defects"] == []
    assert g["g2"]["tests"] >= 6 and g["g2"]["level_tests"] == 40 and g["checks"]["g9"]["passed"] and g["checks"]["g8"]["passed"] and g["checks"]["g7"]["4096"]["passed"] and g["checks"]["g6"]["passed"]
    assert set(g["checks"]["restoration"]) == set(core.ARMS) and all(v["identical"] for v in g["checks"]["restoration"].values()) and g["checks"]["index_rebuild"]["identical"]
    assert g["checks"]["identity_F-OQ"]["passed"] and g["checks"]["identity_R2"]["passed"] and g["checks"]["backbone_hashes_unchanged"]
    run_gates = core.read_record(dry["run"] / "gates.json", "gates")
    assert all(run_gates[f"{n}_passed"] is True for n in stages.GATE_NAMES) and run_gates["configurations_checked"] == 30  # the gates again before training, in the run directory


def test_dry_calibration_covers_all_its_cells_and_leaves_decisions_to_the_lead(dry: dict[str, Any]) -> None:
    cells = core.calibration_cells(False, 8)
    for c in cells:
        assert (core.cell_dir(dry["cal"], c.label) / "train.json").is_file()
    cal = core.read_record(dry["cal"] / "calibration.json", "calibration")
    assert cal["load_decision"]["action"] in ("GRID_STANDS", "OVERLOAD_ROW", "RETURN_TO_LEAD") and set(cal["cut3_eligible"]) == {"8K/64K", "32K/16K"} and cal["calibration_accuracy_note"].startswith("calibration accuracies")
    assert set(cal["dense_rates"]) == {"16384", "65536"} and "readings" in cal and len(cal["load"]) == 8
    assert all(e["rate"] is None for e in cal["dense_rates"].values() if "tie" in e)  # a tie is not resolved by code


def test_dry_rehearsal_writes_only_whitelisted_records_and_binds_the_calibration(dry: dict[str, Any]) -> None:
    from studies.p10s1 import train

    records = sorted((dry["reh"] / "rehearsal").glob("REH-*/rehearsal*.json"))
    assert len(records) == 30 * 2 + 3  # 30 configurations (record and evaluation) and 3 baselines
    for p in records:
        rec = core.read_record(p, "rehearsal")
        train.validate_rehearsal_record(rec)
        assert not any(w in k for k in rec if k != "loss_finite" for w in train.FORBIDDEN_WORDS)
    assert not list((dry["reh"] / "rehearsal").rglob("*.pt"))  # the rehearsal keeps no snapshot
    proj = core.read_record(dry["reh"] / "projection.json", "projection")
    assert proj["calibration_sha256"] == file_sha256(dry["cal"] / "calibration.json") == proj["calibration"]["sha256"] and proj["dry"] is True
    assert proj["memory"]["ok"] and proj["memory"]["worst_item"] and "evaluation" in proj["memory"]["rule"]
    assert all(r["task_overhead_seconds"] > 0 for r in proj["rates"].values()) and all(r["evaluation_peak_rss_bytes"] > 0 and r["task_peak_rss_bytes"] > 0 for r in proj["rates"].values())
    assert len(proj["caps"]["configurations"]) == 12 and proj["chosen"]["ok"] and proj["charged_seconds"] > 0 and proj["cap_seconds"] == core.cap_seconds()
    assert proj["chosen"]["headroom"]["required_seconds"] <= proj["cap_seconds"] and proj["fixed"]["gates"] > 0 and proj["fixed"]["analysis"] > 0
    timing = core.read_record(dry["reh"] / "timing.json", "timing")
    assert timing["status"] == "MEASURED" and len(timing["cpu_per_update"]) == 15 and all(v > 0 for v in timing["cpu_per_update"].values()) and timing["quiet"]["quiet"]


def test_dry_freeze_is_a_pure_function_of_its_inputs(dry: dict[str, Any], tmp_path: Path) -> None:
    plan = json.loads((dry["freeze"] / "plan.json").read_text())
    assert plan["stage_caps_sha256"] == file_sha256(dry["freeze"] / "stage_caps.json") and plan["cap_seconds"] == core.cap_seconds() and plan["headroom"]["ok"] is True
    assert set(plan["data_manifests"]) == {"p10s1-test-0"}  # the DRY profile has one draw
    caps = json.loads((dry["freeze"] / "stage_caps.json").read_text())
    assert len(caps["configurations"]) == 12
    proj = dry["reh"] / "projection.json"
    code = stages.main(["freeze", "--dry", "--mode", "rehearsal", "--run-dir", str(dry["run"]), "--projection", str(proj), "--calibration", str(dry["cal"] / "calibration.json"), "--timing", str(dry["reh"] / "timing.json"), "--gates", str(dry["reh"] / "gates.json"), "--freeze-dir", str(tmp_path / "again")])
    assert code == 0 and (tmp_path / "again" / "plan.json").read_bytes() == (dry["freeze"] / "plan.json").read_bytes() and (tmp_path / "again" / "stage_caps.json").read_bytes() == (dry["freeze"] / "stage_caps.json").read_bytes()


def test_dry_trains_and_evaluates_the_whole_frozen_registry(dry: dict[str, Any]) -> None:
    fro = fz.Frozen.from_json(json.loads((dry["freeze"] / "plan.json").read_text())["frozen"])
    cells = [c for c in core.registered_cells(fro.plan, dense_rates=fro.dense_rates) if c.kind != "LN"]
    assert len(cells) == 150 + 14 + 14 and fro.plan.unit == 8
    for c in cells:
        folder = core.cell_dir(dry["run"], c.label)
        tr = core.read_record(folder / "train.json", "train")
        assert tr["status"] == "completed" and tr["run_updates"] == c.run_updates and sorted(int(u) for u in tr["snapshot_meta"]) == list(fro.snapshots(c)) and tr["trainable_backbone_parameters"] == 0
        for u in fro.snapshots(c):
            assert core.eval_path(dry["run"], c.label, u).is_file()
    for r in range(1, 6):
        for facts in (2048, 8192, 32768):
            assert (dry["run"] / "baselines" / f"d{r}_f{facts}.json").is_file()
    assert len(list((dry["run"] / "simulation").glob("*.json"))) == 21 and (dry["run"] / "throughput.json").is_file()
    thr = core.read_record(dry["run"] / "throughput.json", "throughput")
    assert thr["status"] == "MEASURED" and set(thr["results"]) == {f"{a}|{n}" for a in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8", "D-OQ") for n in core.SLOT_COUNTS} and "not storage I/O" in thr["scope"]


def test_dry_analysis_and_report(dry: dict[str, Any]) -> None:
    analysis_rec = core.read_record(dry["run"] / "analysis.json", "analysis")
    result = analysis_rec["result"]
    assert result["assessment"]["status"] == "COMPLETE" and result["assessment"]["missing_cells"] == [] and result["assessment"]["failed_cells"] == [] and result["assessment"]["engineering"]["failed"] is False
    assert result["timing"]["status"] == "MEASURED" and result["throughput"]["status"] == "MEASURED" and len(result["simulation"]) == 21
    text = (dry["run"] / "results" / "RESULTS.md").read_text()
    assert text.splitlines()[2].startswith("**DRY:") and C.untagged_positive_labels(text) == [] and core.ORACLE_SENTENCE in text and "Astra review: NOT_PERFORMED" in text
    results = json.loads((dry["run"] / "results" / "results.json").read_text())
    assert results["banner"].startswith("DRY") and results["analysis"]["assessment"]["status"] == "COMPLETE"
    sims = list(result["simulation"].values())
    assert all("no device" in s["disclaimer"] and "working_set_slots" in s for s in sims)
    for stage in ("analyze", "report"):
        with pytest.raises(pool.StageRefused):
            stages.run_stage_tasks(stage, parse("analyze", "--ledger-root", str(dry["root"]), "--dry"), [], dry["run"], cap=10.0)  # a stage is run once and never overwritten
