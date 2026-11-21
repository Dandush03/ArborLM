# ruff: noqa: E501
"""P10IS2 Part Q re-audit fixes: L1 (the public record of a rehearsal does not depend on Q1-Q4), N1 (a refusal is not a COMPLETE stage; the negative-outcome path), N2 (the forced identity probe), B3-c (the counting
rehearsal runs every stage of the registered run), A9 (sealed permissions). Each test fails on the behaviour the re-audit found and patches nothing under test. Seeds 935001-935999. Self-check only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10is2_audit_fixes import ctx_of  # noqa: E402
from test_p10is2_launch import freeze, make_repo  # noqa: E402
from test_p10is2_partq_freeze import ctx_factory  # noqa: E402

from studies.p10is2.common import core, gates, runner  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.partq import batches as bt  # noqa: E402
from studies.p10is2.partq import pipeline, real_stages  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402
from studies.p10is2.partq import real as qreal  # noqa: E402
from studies.p10is2.partq import rehearsal as reh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def fake_ledger(run: Path) -> core.Ledger:
    run.mkdir(parents=True, exist_ok=True)
    return core.Ledger(run / "charged_ledger.json", "Q", 1e12)


def exec_stage(run: Path, stage: str, body):  # type: ignore[no-untyped-def]
    guard = real_stages.Guard(1e12, 1e9)
    return real_stages.execute(stage, run, "test", fake_ledger(run), guard, 1e12, body, {"ctx": None}, lambda: [])


# --- N1: a refusal is a refusal, and the stage can run again -----------------------------------------------------------------------------------------
def test_a_refused_stage_is_not_complete_and_can_be_run_again(tmp_path: Path) -> None:
    run = tmp_path / "run"

    def refuse() -> dict[str, object]:
        raise core.StageRefused("refused: a pin differs")

    with pytest.raises(core.StageRefused):
        exec_stage(run, "inputs", refuse)
    assert not real_stages.completion_path(run, "inputs").exists()  # NOT recorded complete
    assert not (run / "stages/inputs.json").exists()
    assert runner.read_manifest(run, "inputs") is None  # no COMPLETE manifest that would forbid a re-run
    assert json.loads((run / "stages/inputs.refused.json").read_text())["status"] == "REFUSED"
    again = exec_stage(run, "inputs", lambda: {"ok": 1})  # the cause is fixed: the same stage runs
    assert again["status"] == "COMPLETE" and real_stages.completion_path(run, "inputs").is_file()
    assert runner.read_manifest(run, "inputs")["status"] == "COMPLETE"  # type: ignore[index]
    real_stages.require_prerequisites(run, "partition")  # and the next stage may follow


def test_a_cap_stop_is_paused_and_charges_the_ledger(tmp_path: Path) -> None:
    run = tmp_path / "run"

    def stop() -> dict[str, object]:
        raise bt.StageCapExceeded("cap")

    out = exec_stage(run, "qfit", stop)
    assert out["status"] == "PAUSED" and not real_stages.completion_path(run, "qfit").exists()
    assert json.loads((run / "stages/qfit.json").read_text())["status"] == "PAUSED"
    assert (run / "charged_ledger.json").is_file()


def test_an_item_error_leaves_no_completion_record(tmp_path: Path) -> None:
    run = tmp_path / "run"

    def boom() -> dict[str, object]:
        raise ValueError("x")

    with pytest.raises(ValueError):
        exec_stage(run, "qfit", boom)
    assert not real_stages.completion_path(run, "qfit").exists()


# --- N1: the negative-outcome path is explicit ------------------------------------------------------------------------------------------------------
def test_a_teacher_that_fails_qualification_stops_generation_and_analysis_gives_the_registered_label(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, student_scores=lambda items, p=None: {"A": 0.0, "B": 0.0})
    ctx.cfg = {**ctx.cfg, "quality": {**ctx.cfg["quality"], "q1_own_score_min": 0.999}}  # type: ignore[index]
    pipeline.run_all(ctx)
    run = ctx.run_dir
    for s in ("inputs", "partition", "qfit", "qcheck"):
        real_stages._mark(run, s, "COMPLETE")
    for s in ("generation", "regeneration", "outputs"):
        out = real_stages.run_stage(s, ROOT, run, "test")
        assert out["status"] == "NOT RUN BY RULE" and "did not pass Q1-Q4" in out["reason"]
        assert json.loads(real_stages.completion_path(run, s).read_text())["status"] == "NOT RUN BY RULE"  # recorded as what it is
    assert not (run / "generation").exists() and not (run / "outputs").exists()
    real_stages.run_stage("analysis", ROOT, run, "test")
    rec = json.loads((run / "qualification.json").read_text())
    assert "NEGATIVE: QUALITY" in rec["label"] and "Q1" in rec["label"] and rec["part_t"] is not True


# --- L1 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_public_record_of_a_rehearsal_does_not_depend_on_q1_to_q4(tmp_path: Path) -> None:
    ok = reh.run_measuring(ctx_factory(tmp_path / "ok"), cap_seconds=3600.0, charged_before_freeze_seconds=0.0)
    bad_make = ctx_factory(tmp_path / "bad", student_scores=lambda items, p=None: {"A": 0.0, "B": 0.0}, force_generation=True)

    def make_bad() -> pipeline.QContext:
        c = bad_make()
        c.cfg = {**c.cfg, "quality": {**c.cfg["quality"], "q1_own_score_min": 0.9999}}  # type: ignore[index]
        return c

    bad = reh.run_measuring(make_bad, cap_seconds=3600.0, charged_before_freeze_seconds=0.0)
    for rec in (ok, bad):
        shown = json.dumps({k: v for k, v in rec.items() if k != "oracle_line"}).lower()
        for hidden in ("filter_setting", "yield", "accepted", "tau", "q1", "q2", "q3", "q4", "chrf", "precision"):
            assert hidden not in shown, hidden
        assert "generation_items_per_second" in rec
    assert set(ok) == set(bad)  # the same keys whether the teachers qualify or not
    assert ok["counts"]["generation_sources"].keys() == bad["counts"]["generation_sources"].keys()
    assert next((tmp_path / "bad").rglob("rehearsal_values.json")).is_file()


def test_the_whitelist_refuses_filter_yield_and_accepted_keys() -> None:
    for k in ("filter_setting", "yields", "accepted_counts"):
        with pytest.raises(ValueError, match="sealed key"):
            reh.whitelist({k: 1})
    assert reh.whitelist({"generation_items_per_second": 3.0}) == {"generation_items_per_second": 3.0}


def test_the_sealed_values_are_written_with_private_permissions(tmp_path: Path) -> None:
    ctx = ctx_of(tmp_path, seal=True)
    pipeline.run_all(ctx)
    path = pipeline.write_sealed_summary(ctx)
    assert path.stat().st_mode & 0o777 == 0o600 and path.parent.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o077 == 0 for p in path.parent.iterdir() if p.is_file())


# --- N2 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_forced_identity_probe_pauses_for_identity_in_a_run_dir_that_is_not_the_plans(tmp_path: Path) -> None:
    r = make_repo(tmp_path)
    freeze(r, "Q")
    plan = planmod.Plan.load(r / core.PLAN_Q, "Q")
    other = tmp_path / "rehearsal_run"  # the rehearsal runs in its own directory, not the plan's
    other.mkdir()
    with pytest.raises(core.ForcedIdentityPause):
        qreal.identity_probe(plan, r, other)()


def test_the_part_t_identity_probe_is_the_same(tmp_path: Path) -> None:
    from studies.p10is2 import partt_stages

    r = make_repo(tmp_path)
    freeze(r, "T")
    plan = planmod.Plan.load(r / core.PLAN_T, "T")
    other = tmp_path / "rehearsal_run"
    other.mkdir()
    with pytest.raises(core.ForcedIdentityPause):
        partt_stages.identity_probe(plan, r, other)()


# --- B3-c --------------------------------------------------------------------------------------------------------------------------------------------
def test_the_rehearsal_stage_list_is_the_registered_stage_list() -> None:
    assert tuple(qplan.REHEARSAL_STAGES) == tuple(real_stages.STAGE_ORDER)


def test_a_counting_record_with_every_stage_passes_the_gate_and_one_without_the_outputs_fails(tmp_path: Path) -> None:
    def probe() -> None:
        raise core.ForcedIdentityPause("PAUSED — IDENTITY")

    make = ctx_factory(tmp_path, seal=True)
    here = make()

    def write(name: str):  # type: ignore[no-untyped-def]
        def fn() -> None:
            p = here.d(pipeline.loc(here, name))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")

        return fn

    kw = dict(plan_file_sha256="c" * 64, caps_provisional=False, cap_seconds=10800.0, identity_probe=probe, pause_after_batches=4)
    full = reh.run_counting(make, post_stages={"inputs": write("inputs/record.json"), "outputs": write("outputs/record.json")}, plan_stage_items={"qfit": 2000}, **kw)  # type: ignore[arg-type]
    assert set(full["stages"]) == set(qplan.REHEARSAL_STAGES) and all(v["status"] == "COMPLETE" for v in full["stages"].values()) and full["status"] == "COMPLETE"
    assert full["plan_stage_items"] == {"qfit": 2000}
    assert gates.rehearsal_gate(full, qplan.REHEARSAL_STAGES, plan_file_sha256="c" * 64)["passed"] is True
    partial = reh.run_counting(ctx_factory(tmp_path / "p", seal=True), **kw)  # type: ignore[arg-type]
    assert partial["stages"]["outputs"]["status"] == "NOT RUN"
    assert gates.rehearsal_gate(partial, qplan.REHEARSAL_STAGES, plan_file_sha256="c" * 64)["passed"] is False


# --- the candidate plan pins the shared ledger by absolute path and hash, and does not rewrite the file ------------------------------------------
def test_the_candidate_plan_pins_the_shared_ledger_hash_and_leaves_the_file_alone(tmp_path: Path) -> None:
    from arborlm.io import file_sha256

    ledger = tmp_path / "panel_ledger.json"
    ledger.write_text('{"format": "p10i-panel-ledger-v1", "windows": []}')
    before = (file_sha256(ledger), ledger.stat().st_mtime_ns)
    base = core.load_config("Q")
    cfg = {**base, "paths": {**base["paths"], "panel_ledger": str(ledger)}}
    walk = {"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}
    rec = qplan.build_candidate(ROOT, tmp_path / "run", cfg, inputs={}, walk=walk, test_mode=True)
    assert rec["manifests"]["panel_ledger"] == {"path": str(ledger), "sha256": before[0]}
    assert (file_sha256(ledger), ledger.stat().st_mtime_ns) == before
    assert base["paths"]["panel_ledger"].endswith("/p10i-s6-backups/panel_ledger.before-s6.json")  # attempt 3 pins the preserved copy, not the live shared file
