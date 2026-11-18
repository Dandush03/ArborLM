# ruff: noqa: E501
"""P10IS0 plan, freeze, preconditions, launch scripts, run_cell and a tiny Stage R (ADR-0023 sections 5.2, 10, 14). Registered entry points refuse today (nothing is frozen)."""

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is0 import adapter, core, freeze, items, ladder  # noqa: E402
from studies.p10is0 import plan as planmod  # noqa: E402
from studies.p10is0.plan import StageRefused  # noqa: E402

torch.set_num_threads(1)
CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)


def make_repo(tmp: Path, *, provisional: bool = True) -> Path:
    """A copy of what the freeze reads (code, config, the seed checker, the ADR), so no file of the worktree is written."""
    root = tmp / "repo"
    ign = shutil.ignore_patterns("__pycache__", "*.pyc", "freeze", "results")
    shutil.copytree(REPO / "studies", root / "studies", ignore=ign)
    shutil.copytree(REPO / "configs", root / "configs")
    (root / "docs/reviews/p10-i-direction-2026-11-17").mkdir(parents=True)
    shutil.copy(REPO / core.SPEC, root / core.SPEC) if (root / core.SPEC).parent.exists() else (root / core.SPEC).parent.mkdir(parents=True) or shutil.copy(REPO / core.SPEC, root / core.SPEC)
    shutil.copy(REPO / CFG["seed_ranges"]["checker"], root / CFG["seed_ranges"]["checker"])
    (root / "studies/p10is0/freeze").mkdir(parents=True, exist_ok=True)
    if not provisional:
        p = root / core.CONFIG
        p.write_text(p.read_text().replace("provisional = true", "provisional = false"))
    return root


def write_durations(root: Path, **over: dict[str, object]) -> None:
    entries = {ct.name: {"t_exposures": 1024, "convergence": "SHOWN", "flat_below_floor": False, "reference_flags": {"cond4": False, "other": []}} for ct in core.cell_types(CFG)}
    entries.update({k: {**entries[k], **v} for k, v in over.items()})
    write_json(root / core.DURATIONS, ladder.durations_record(entries))


def write_caps(root: Path, provisional: bool) -> None:
    write_json(root / core.STAGE_CAPS, {**core.envelope("stage_caps"), "provisional": provisional, "total_hours": 100.0, "stage_r_hours": 20.0})


def test_registered_entry_points_refuse_today(tmp_path: Path) -> None:
    run = tmp_path / "refusal_run"
    for stage in ("main", "x8-gate", "x8", "analysis", "report"):
        p = subprocess.run([sys.executable, "-m", "studies.p10is0.stages", "registered", stage, "--run-dir", str(run), "--freeze-commit", "0" * 40], cwd=REPO, capture_output=True, text=True, check=False)
        assert p.returncode == 2 and "refused" in p.stderr, (stage, p.stderr)
        assert not run.exists()  # nothing was written
    with pytest.raises(StageRefused):
        planmod.check_preconditions(REPO, run, "0" * 40)


def test_launch_scripts_take_exactly_two_arguments_and_nothing_else() -> None:
    scripts = sorted((REPO / core.LAUNCH_DIR).glob("*.sh"))
    assert [s.stem for s in scripts] == ["analysis", "disclose", "main", "report", "x8-gate", "x8"]
    for s in scripts:
        text = s.read_text()
        assert 'if [ "$#" -ne 2 ]' in text and "set -eu" in text and "sleep" not in text.replace("no sleep", "") and "while" not in text and " & " not in text
        assert f"registered {s.stem} --run-dir" in text
        p = subprocess.run([str(s)], capture_output=True, text=True, check=False)
        assert p.returncode == 2 and "usage" in p.stderr


def test_run_dir_must_be_ignored_untracked_and_named(tmp_path: Path) -> None:
    """On its own repository (the test does not assume the directory it runs in is a working tree: A11)."""
    repo = tmp_path / "wt"
    (repo / "experiments").mkdir(parents=True)
    (repo / "studies").mkdir()
    (repo / "studies" / "tracked.py").write_text("x = 1\n")
    (repo / ".gitignore").write_text("/experiments/\n")
    for argv in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@e.invalid", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "x"]):
        subprocess.run(["git", *argv], cwd=repo, check=True, capture_output=True)
    assert planmod.run_dir_problems(repo / "experiments" / "p10is0-run-x", repo) == []
    assert planmod.run_dir_problems(Path("/nonexistent-elsewhere/run"), repo) == []
    assert any("tracked" in x or "not git-ignored" in x for x in planmod.run_dir_problems(repo / "studies", repo))
    assert any("not git-ignored" in x for x in planmod.run_dir_problems(repo / "zz_untracked_run", repo))
    with pytest.raises(ValueError):
        core.assert_run_dir_ignored(repo / "zz_untracked_run", repo)
    core.assert_run_dir_ignored(repo / "experiments" / "x", repo)


def test_frozen_inputs_are_a_file_list_hashed_individually() -> None:
    paths = planmod.frozen_paths(REPO)
    assert all((REPO / p).is_file() for p in paths) and len(paths) == len(set(paths))
    assert "configs/p10is0_overload.toml" in paths and "studies/p10is0/core.py" in paths and "studies/p10is0/launch/main.sh" in paths
    assert "studies/p10s0/core.py" in paths and "studies/p9ii/train.py" in paths and "studies/p9/core.py" in paths
    h = planmod.hash_inputs(REPO)
    assert set(h) == set(paths) and all(len(v) == 64 for v in h.values())
    assert planmod.verify_inputs(REPO, h) == []
    bad = dict(h)
    bad["studies/p10is0/core.py"] = "0" * 64
    assert planmod.verify_inputs(REPO, bad) == ["studies/p10is0/core.py: differs from the recorded hash"]


def test_candidate_plan_freeze_and_refusals(tmp_path: Path) -> None:
    root = make_repo(tmp_path, provisional=False)
    with pytest.raises(StageRefused, match="durations"):
        freeze.candidate_plan(root)
    write_durations(root, **{"2K/1K": {"t_exposures": 1024, "reference_flags": {"cond4": False, "other": [3]}}})
    write_caps(root, provisional=True)
    res = freeze.candidate_plan(root)
    plan = planmod.load_plan(root / core.PLAN)
    assert res["cells"] == len(plan["items"]["main"]) == 200 - 20 and plan["cell_types"]["2K/1K"]["removed"] is True  # a cell type removed by the rule has no cells
    assert plan["durations_sha256"] and res["caps_provisional"] is True
    with pytest.raises(StageRefused, match="exists"):
        freeze.candidate_plan(root)
    freeze.candidate_plan(root, supersede=True)
    assert len(list((root / "studies/p10is0/freeze/superseded").glob("plan-*.json"))) == 1  # moved aside, never deleted
    rehearsal = freeze.counting_rehearsal(root)
    assert rehearsal["candidate"]["status"] == "COMPLETE" and rehearsal["items"]["main"] == 180 and rehearsal["analysis_on_synthetic_registry"]["headline_step"] == 4  # the removed cell type is at load 1: its series is NOT EVALUABLE there, so the break is at load 1
    reh_path = tmp_path / "rehearsal.json"
    write_json(reh_path, core.jsonable(rehearsal))
    with pytest.raises(StageRefused, match="provisional"):
        freeze.freeze(root, reh_path, attest_unopened=["lead", "implementer", "auditor"], run_checker=False)
    write_caps(root, provisional=False)
    # the caps file is a frozen input and the plan records caps: rewrite the candidate plan and rehearse again
    freeze.candidate_plan(root, supersede=True)
    again = freeze.counting_rehearsal(root)
    assert again["caps_provisional"] is False
    write_json(reh_path, core.jsonable(again))
    with pytest.raises(StageRefused, match="sealed"):
        freeze.freeze(root, reh_path, attest_unopened=["lead"], run_checker=False)
    out = freeze.freeze(root, reh_path, attest_unopened=["lead", "implementer", "auditor"], run_checker=False)
    rec = core.read_record(root / core.FREEZE_RECORD, "freeze_record")
    assert out["plan_file_sha256"] == rec["plan_file_sha256"] and "studies/p10is0/core.py" in rec["inputs"] and "studies/p10is0/freeze/plan.json" in rec["inputs"] and "studies/p10is0/freeze/stage_caps.json" in rec["inputs"]
    assert rec["seed_gate"]["named_spare_values"]["initialisation"] == [330061, 330062, 330063, 330064, 330065, 330066] and len(rec["seed_gate"]["named_spare_values"]["draw_sets"]) == 6
    with pytest.raises(StageRefused, match="exists"):
        freeze.freeze(root, reh_path, attest_unopened=["lead", "implementer", "auditor"], run_checker=False)
    # the plan is not the rehearsed one if the file changes afterwards
    root2 = make_repo(tmp_path / "b", provisional=False)
    write_durations(root2)
    write_caps(root2, provisional=False)
    freeze.candidate_plan(root2)
    r2 = freeze.counting_rehearsal(root2)
    r2["candidate"]["plan_file_sha256"] = "0" * 64
    write_json(reh_path, core.jsonable(r2))
    with pytest.raises(StageRefused, match="rehearsed"):
        freeze.freeze(root2, reh_path, attest_unopened=["lead", "implementer", "auditor"], run_checker=False)
    p = root2 / core.DURATIONS
    p.unlink()
    write_durations(root2, **{"8K/4K": {"t_exposures": 2048}})
    freeze.counting_rehearsal(root2)  # still resolves: it reads the plan file
    with pytest.raises(StageRefused, match="re-derivation"):
        freeze.freeze(root2, reh_path, attest_unopened=["lead", "implementer", "auditor"], run_checker=False)


def test_seed_gate_fast_part() -> None:
    from studies.p10is0 import seeds

    r = seeds.seed_gate(CFG, run_checker=False)
    assert r["passed"], r["problems"]
    assert r["checker"]["sha256"] == CFG["seed_ranges"]["checker_sha256"] and r["checker"]["allocation_rows"] == 8
    assert r["named_spare_values"] == {"draw_sets": [309401, 309501, 309601, 309701, 309801, 309901], "initialisation": [330061, 330062, 330063, 330064, 330065, 330066]}
    assert core.calibration_set(1, 3, CFG).base == 309801 and core.calibration_set(2, 2, CFG).base == 309701 and core.init_seed("CAL", "A6", 2, 3, CFG) == 330066
    with pytest.raises(ValueError, match="fourth repeat"):
        core.calibration_set(1, 4, CFG)
    assert [core.init_seed("REG", a, d, 0, CFG) for a, d in (("A5-D", 1), ("A5-D", 2), ("A0", 3), ("A0", 4), ("A6", 2))] == [330001, 330002, 330001, 330002, 330001]
    assert core.init_seed("CAL", "A5-D", 1, 0, CFG) == 330091 and core.init_seed("CAL", "A5-D", 2, 0, CFG) == 330093 and core.init_seed("REH", "A0", 1, 0, CFG) == 330092
    assert core.registered_set(10, CFG).base == 300901 and core.reserve_set(4, CFG).base == 301301
    r2 = seeds.checker_copy((REPO / CFG["seed_ranges"]["checker"]).read_text(), REPO)
    assert "p10is0" in r2 and r2.count("p10ir_routing.toml") == 1 and "repeated Stage R" in r2 and "330066" in r2 and "309901" in r2


def test_labels_of_cells_are_unique_across_roles_and_attempts() -> None:
    cells = core.registered_cells(CFG, include_x8=True)
    assert len({c.label for c in cells}) == len(cells) == 230
    ct = core.cell_type_by_name("8K/4K", CFG)
    a, b = core.make_cell("REG", ct, "A5-D", 1, 0, CFG), core.make_cell("CAL", ct, "A5-D", 1, 0, CFG)
    c = core.make_cell("CAL", ct, "A5-D", 1, 2, CFG)
    assert len({a.label, b.label, c.label}) == 3


# --- run_cell and a tiny Stage R -------------------------------------------------------------------------------------------------------------
FACTS = 128


def tiny_env() -> items.Env:
    return items.Env(adapter.SYNTHETIC_CORPUS, adapter.synthetic_backbone(), tiny=True, facts_override=FACTS)


def test_run_cell_writes_a_record_resumes_and_loads(tmp_path: Path) -> None:
    ct = core.cell_type_by_name("2K/512", CFG)
    cell = core.make_cell("TEST", ct, "A5-D", 1, 0, CFG)
    cell = core.Cell("TEST", "S", "A5-D", FACTS, 512, 1, cell.init_seed)
    env = tiny_env()
    rec = items.run_cell(cell, ct, 16, tmp_path, env, CFG, diag=(4, 8, 8))
    assert rec["status"] == "ok" and set(rec["readouts"]) == {"e512", "half", "T"}
    again = items.run_cell(cell, ct, 16, tmp_path, env, CFG, diag=(4, 8, 8))  # a finished cell is not recomputed (the train files would refuse a second write)
    assert again["readouts"] == rec["readouts"]
    o = items.obs_from_json(rec["readouts"]["T"])
    assert o.a[1] > 0 and o.m_p.denominator > 0
    reg, errs = items.load_registry(tmp_path, [{"label": cell.label, "cell_type": ct.name, "arm": "A5-D", "draw": 1}, {"label": "missing", "cell_type": ct.name, "arm": "A0", "draw": 1}])
    assert errs == [] and list(reg) == [(ct.name, "A5-D", 1)] and reg[(ct.name, "A5-D", 1)].status == "ok"
    (items.cell_dir(tmp_path, cell.label) / "result.json").write_text("{}")
    _, errs = items.load_registry(tmp_path, [{"label": cell.label, "cell_type": ct.name, "arm": "A5-D", "draw": 1}])
    assert len(errs) == 1  # an unreadable record is an item error, not a label


def test_run_cell_records_a_divergence_as_a_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p9ii.train import Trainer

    real = Trainer.step

    def diverge(self: Trainer, batch: object) -> dict[str, object]:
        if self.update == 3:
            self.all_finite["gradients"] = False
            raise ValueError("non-finite gradient norm at update 4")
        return real(self, batch)  # type: ignore[arg-type]

    monkeypatch.setattr(Trainer, "step", diverge)
    ct = core.cell_type_by_name("2K/512", CFG)
    cell = core.Cell("TEST", "S", "A5-D", FACTS, 512, 1, 330098)
    rec = items.run_cell(cell, ct, 16, tmp_path, tiny_env(), CFG)
    assert rec["status"] == "nonfinite" and rec["nonfinite_update"] == 4
    assert items.run_cell(cell, ct, 16, tmp_path, tiny_env(), CFG)["status"] == "nonfinite"  # kept, not re-run
