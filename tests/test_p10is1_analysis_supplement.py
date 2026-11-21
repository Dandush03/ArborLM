# ruff: noqa: E501
"""P10IS1 analysis supplement (docs/decisions/ADR-0024-addendum-analysis-loader-defect.md): the corrected loader returns exactly what the frozen ``build_registry`` returns once its one glob line is fixed IN MEMORY (never in
the tree), on a synthetic run and on the counting rehearsal's run directory; the driver's refusals, its labels, that it writes only to a new directory beside the run, that it copies only Traceback blocks of the stage-output
file, and what reads ``analysis/analysis.json``. Nothing here runs a registered stage, reads a registered record or opens a sealed value. Self-check only."""

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10is1 import analysis, core, freeze, items, rehearsal, report, stages  # noqa: E402
from studies.p10is1 import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "results" / "p10is1-analysis-supplement-20261121" / "run_analysis_supplement.py"
COUNTING = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS1-counting-20261121")
STAGES_TEXT = """=== train Sat Nov 21 03:12:29 EST 2026
ult": {"SECRET_TRAIN_777": 1}}
=== train exit=0
=== ladder Sat Nov 21 07:48:05 EST 2026
{"stage": "ladder", "status": "COMPLETE", "result": {"u_run": {"2K/256": 123456}}}
=== ladder exit=0
=== evaluate Sat Nov 21 09:45:37 EST 2026
{"stage": "evaluate", "status": "PAUSED", "note": "SECRET_EVAL_VALUE_777"}
=== evaluate exit=3
=== baselines Sat Nov 21 10:45:38 EST 2026
{"stage": "baselines", "status": "PAUSED"}
=== baselines exit=3
=== analysis Sat Nov 21 10:45:42 EST 2026
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/w/studies/p10is1/stages.py", line 483, in _execute_stage_body
    res = do_analysis(ctx, pl, run_dir, rehearsal_record_of(pl, repo))
{"stage": "analysis", "note": "SECRET_ANALYSIS_LINE_888"}
    raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}")
ValueError: expected a 'baseline' record, got 'stage_manifest'
=== analysis exit=1
=== report Sat Nov 21 10:45:45 EST 2026
, run_dir, plan_path, args, repo=repo, inline=inline, workers=workers)
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/x/P10IS1-pre-20261118/analysis/analysis.json'
=== report exit=1
"""  # the structure of the real file (experiments/P10IS1-registered-20261121-stages.out): each stage's output cut to its last 1,500 bytes, section markers, no "Traceback" header, a mid-line start


def driver() -> Any:
    spec = importlib.util.spec_from_file_location("run_analysis_supplement", DRIVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_analysis_supplement"] = mod
    spec.loader.exec_module(mod)
    return mod


def frozen_with_the_one_line_fix_in_memory() -> Any:
    """The frozen ``stages.build_registry`` with its baselines glob changed to ``d*_f*.json`` in a COPY of its source compiled in memory: the tree is untouched."""
    src = inspect.getsource(stages.build_registry)
    old = 'sorted((run_dir / "baselines").glob("*.json"))'
    assert old in src
    ns = dict(stages.__dict__)
    exec(compile(src.replace(old, 'sorted((run_dir / "baselines").glob("d*_f*.json"))'), "<one-line fix applied in memory>", "exec"), ns)  # noqa: S102
    return ns["build_registry"]


def tiny_run(tmp: Path, *, evaluate_manifest: str | None = "COMPLETE") -> tuple[Any, Any, Path]:
    root = tmp / "r"
    root.mkdir()
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(rehearsal.tiny_config_text())
    pl = rehearsal.tiny_plan(root, ROOT, cfg_path)
    run = root / "run"
    ctx = items.Ctx(core.TEST, run, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    args = argparse.Namespace(freeze_commit=None, synthetic=True)
    always = {"quiet": True, "load_average": 0.1, "other_study_processes": []}
    for st in ("gates", "baselines"):
        rec = stages.execute_stage(st, pl, ctx, run, pl.path, args, repo=ROOT, inline=True, quiet_reading=lambda: always, end_fn=lambda s: {"ok": True, "other_study_processes": []}, sleep=lambda s: None)
        assert rec["status"] == "COMPLETE"
    if evaluate_manifest:
        core.write_record(run / "evaluate" / "manifest.json", {**core.envelope("stage_manifest"), "stage": "evaluate", "status": evaluate_manifest, "result": {}})
    return ctx, pl, run


def test_the_corrected_loader_equals_the_frozen_loader_with_its_one_line_fixed_in_memory_on_a_synthetic_run(tmp_path: Path) -> None:
    drv = driver()
    ctx, pl, run = tiny_run(tmp_path)
    assert sorted(p.name for p in (run / "baselines").glob("*.json")) == ["d1_f128.json", "d2_f128.json", "manifest.json"]
    with pytest.raises(ValueError, match="expected a 'baseline' record, got 'stage_manifest'"):
        stages.build_registry(ctx, pl, run)  # the defect, on the unpatched frozen function
    fixed = frozen_with_the_one_line_fix_in_memory()(ctx, pl, run)
    mine = drv.build_registry(ctx, pl, run)
    assert mine == fixed and len(mine.baselines) == 2  # same keys and values: every field of the Registry
    assert sorted(p.name for p in (run / "baselines").glob("*.json")) == ["d1_f128.json", "d2_f128.json", "manifest.json"]
    # the status of the registry still sees the baselines stage manifest (as the frozen function reads */manifest.json): nothing was hidden but the glob
    assert any(s.startswith("baselines:") or s == "baselines: PAUSED" for s in mine.status["paused"]) is False and mine.status["run"].endswith("(test)")


@pytest.mark.skipif(not (COUNTING / "view_plan.json").is_file(), reason="the counting rehearsal's run directory is on this machine only")
def test_the_corrected_loader_equals_the_frozen_loader_with_its_one_line_fixed_in_memory_on_the_counting_rehearsal_run_directory() -> None:
    """Read-only on the counting rehearsal of 2026-11-21 (REHEARSAL draw, not the registered run). Nothing is printed or asserted about a value: only that the two registries are equal."""
    drv = driver()
    view = planmod.Plan.load(COUNTING / "view_plan.json")
    ctx = items.Ctx(view.mode, COUNTING, freeze.experiments_root(), sizes=dict(view.data.get("sizes") or {"table_facts": 32768, "unseen": 2048}))
    rec_path = COUNTING.parent / "P10IS1-counting-20261121-rehearsal.json"
    rehearsal_record = core.read_record(rec_path, "rehearsal") if rec_path.is_file() else None
    with pytest.raises(ValueError, match="expected a 'baseline' record, got 'stage_manifest'"):
        stages.build_registry(ctx, view, COUNTING, rehearsal_record=rehearsal_record)
    fixed = frozen_with_the_one_line_fix_in_memory()(ctx, view, COUNTING, rehearsal_record=rehearsal_record)
    mine = drv.build_registry(ctx, view, COUNTING, rehearsal_record)
    assert mine == fixed and len(mine.baselines) == 3 and len(mine.cells) == len(view.data["cells"])


def test_the_driver_writes_only_a_new_directory_beside_the_run_labels_everything_and_copies_only_traceback_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    drv = driver()
    ctx, pl, run = tiny_run(tmp_path)
    seen: dict[str, Any] = {}

    def fake_analyze(reg: Any) -> dict[str, Any]:
        seen["registry"] = reg
        return {"status": "COMPLETE", "lines": ["a line"]}

    monkeypatch.setattr(analysis, "analyze", fake_analyze)
    monkeypatch.setattr(report, "render", lambda res, *, throughput=None, caps=None: f"RENDERED {res['status']} {throughput} {sorted(caps or {})[:2]}")
    before = sorted(str(p.relative_to(run)) for p in run.rglob("*"))
    out = drv.supplement_dir_of(run)
    assert out == run.parent / "run-analysis-supplement" and out.parent == run.parent
    res = drv.produce(ctx, pl, run, out, rehearsal_record=None, stages_text=STAGES_TEXT, identity={"check_preconditions": "PASS"})
    assert res["analysis_status"] == "COMPLETE" and res["item_errors"] == []
    assert sorted(str(p.relative_to(run)) for p in run.rglob("*")) == before and not (run / "analysis").exists() and not (run / "report").exists()  # nothing written into the run directory
    assert seen["registry"] == frozen_with_the_one_line_fix_in_memory()(ctx, pl, run)  # the frozen analysis function got the registry of the frozen loader with the one line fixed
    names = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
    assert names == ["ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json", "SUPPLEMENT_MANIFEST.json", "analysis/analysis_supplement.json", "report/REPORT_SUPPLEMENT.md"]
    for n in names:
        text = (out / n).read_text()
        assert (drv.LABEL in text) if n.endswith(".md") else (json.loads(text)["label"] == drv.LABEL), n  # every output is labelled
        assert "SECRET_EVAL_VALUE_777" not in text and "SECRET_ANALYSIS_LINE_888" not in text and "SECRET_TRAIN_777" not in text and "123456" not in text and "u_run" not in text.replace("ladder_stops", ""), n  # no non-Traceback line of the stage-output file is copied
    stop = core.read_record(out / "ENGINEERING_STOP_ANALYSIS_LOADER_DEFECT.json", "engineering_stop")
    assert stop["status"] == drv.STOP == "ENGINEERING STOP — ANALYSIS LOADER DEFECT" and stop["traceback_count"] == 2 and "got 'stage_manifest'" in stop["tracebacks"][0] and "analysis.json" in stop["tracebacks"][1]
    assert set(stop["stages"]) == {"analysis", "report"}
    assert "TRUNCATED TAILS that were captured" in stop["tracebacks_note"] and "1,500 bytes" in stop["tracebacks_note"] and stop["section_headers"] == ["=== analysis Sat Nov 21 10:45:42 EST 2026", "=== report Sat Nov 21 10:45:45 EST 2026"]
    md = (out / "report" / "REPORT_SUPPLEMENT.md").read_text()
    assert md.startswith("> **frozen analysis function on the registered records, through a disclosed corrected loader — not the registered analysis stage**") and "RENDERED COMPLETE" in md
    man = core.read_record(out / "SUPPLEMENT_MANIFEST.json", "report_manifest")
    assert man["stage_manifests"] == {"evaluate": "COMPLETE", "baselines": "COMPLETE"} and man["registry_counts"]["baselines"] == 2
    with pytest.raises(SystemExit, match="exists: the supplement is written once"):
        drv.produce(ctx, pl, run, out, rehearsal_record=None, stages_text=STAGES_TEXT, identity={})  # never overwritten
    with pytest.raises(SystemExit, match="inside the run directory"):
        drv.produce(ctx, pl, run, run / "analysis", rehearsal_record=None, stages_text=STAGES_TEXT, identity={})


def test_the_driver_refuses_unless_evaluate_and_baselines_are_complete(tmp_path: Path) -> None:
    drv = driver()
    for k, status in enumerate((None, "PAUSED")):
        (tmp_path / f"t{k}").mkdir()
        ctx, pl, run = tiny_run(tmp_path / f"t{k}", evaluate_manifest=status)
        with pytest.raises(SystemExit, match="evaluate and baselines stage manifests must both be COMPLETE"):
            drv.produce(ctx, pl, run, drv.supplement_dir_of(run), rehearsal_record=None, stages_text=STAGES_TEXT, identity={})
        assert not drv.supplement_dir_of(run).exists()  # nothing created on a refusal


def test_extract_tracebacks_takes_the_two_section_tails_of_the_truncated_file_and_drops_result_lines() -> None:
    drv = driver()
    tbs = drv.extract_tracebacks(STAGES_TEXT)
    assert len(tbs) == 2
    a, r = tbs
    assert a.splitlines()[0].startswith("^^^^") and '  File "/w/studies/p10is1/stages.py", line 483, in _execute_stage_body' in a and a.endswith("ValueError: expected a 'baseline' record, got 'stage_manifest'")
    assert r.endswith("analysis/analysis.json'") and r.splitlines()[-2].strip().startswith("^^^^") and not r.startswith(",")  # the mid-line fragment that began the truncated section is not a frame or an exception line
    assert not any("{" in ln[:1] or "SECRET" in ln or "u_run" in ln for t_ in tbs for ln in t_.splitlines())  # result lines never come along, not even inside a section
    assert drv.extract_tracebacks("no sections\n{}") == []
    only_analysis = STAGES_TEXT.split("=== report Sat")[0]
    assert len(drv.extract_tracebacks(only_analysis)) == 1  # a section without its exit marker or exception line is not a block
    assert len(drv.extract_tracebacks(STAGES_TEXT.replace("FileNotFoundError: [Errno 2] No such file or directory: '/x/P10IS1-pre-20261118/analysis/analysis.json'", "partial output"))) == 1


def test_the_driver_refuses_unless_exactly_two_tracebacks_are_found_and_refuses_a_supplement_inside_the_repository(tmp_path: Path) -> None:
    drv = driver()
    ctx, pl, run = tiny_run(tmp_path)
    out = drv.supplement_dir_of(run)
    for text in ("", STAGES_TEXT.split("=== report Sat")[0]):
        with pytest.raises(SystemExit, match="exactly two captured tracebacks"):
            drv.produce(ctx, pl, run, out, rehearsal_record=None, stages_text=text, identity={})
        assert not out.exists()  # nothing created on a refusal
    for inside in (ROOT / "studies" / "p10is1" / "supp", ROOT / "results" / "supp", ROOT):
        with pytest.raises(SystemExit, match="inside the repository or worktree"):
            drv.produce(ctx, pl, run, inside, rehearsal_record=None, stages_text=STAGES_TEXT, identity={}, repo=ROOT)
        assert not inside.exists() or inside == ROOT
    assert not (ROOT / "studies" / "p10is1" / "supp").exists() and not (ROOT / "results" / "supp").exists()


def test_only_the_registered_report_reads_analysis_json_so_throughput_can_still_run_as_registered() -> None:
    """``analysis/analysis.json`` is written by ``do_analysis`` and read by ``do_report`` only. The throughput branch of ``_execute_stage_body`` neither reads it nor calls ``do_report``/``do_analysis``; the registered
    pre-checks do not look at it."""
    hits = {f.name: [i + 1 for i, ln in enumerate(f.read_text().splitlines()) if "analysis.json" in ln or '"analysis" / "analysis' in ln] for f in (ROOT / "studies" / "p10is1").glob("*.py")}
    assert {k for k, v in hits.items() if v} == {"stages.py"}
    readers = [fn.__name__ for fn in (stages.do_analysis, stages.do_report, stages.cmd_registered, stages.execute_stage, stages._execute_stage_body, stages.measure_throughput) if "analysis.json" in inspect.getsource(fn) or '"analysis" / "analysis' in inspect.getsource(fn)]  # noqa: SLF001
    assert readers == ["do_analysis", "do_report"]
    body = inspect.getsource(stages._execute_stage_body)  # noqa: SLF001
    branch = body[body.index('elif stage in ("timing", "throughput"):') : body.index('elif stage in ("train", "ladder", "evaluate", "baselines"):')]
    assert "do_report" not in branch and "do_analysis" not in branch and "analysis" not in branch.replace("measure_throughput", "")
    assert "analysis" not in inspect.getsource(planmod.check_preconditions) + inspect.getsource(planmod.verify_plan).replace("analysis_", "")


def test_the_addendum_states_the_defect_the_ruling_and_that_the_human_lead_may_overrule() -> None:
    text = (ROOT / "docs" / "decisions" / "ADR-0024-addendum-analysis-loader-defect.md").read_text()
    for needle in ("expected a 'baseline' record, got 'stage_manifest'", "BEFORE any outcome value of P10-I-S1 was read", "may overrule it in favour of an amending freeze (route (a))", "ENGINEERING STOP — ANALYSIS LOADER DEFECT", "ADR-0021 section 25.21",
                   "frozen analysis function on the registered records, through a disclosed corrected loader — not the registered analysis stage", "the throughput stage can still run as registered", "`Astra review: NOT_PERFORMED`", "synthetic_registry_for", "launched once, at 10:45 local", "before `analysis.analyze`, so it produced no value", "last 1,500 bytes", "any second supplement directory is disclosed", "refused inside the repository or worktree"):
        assert needle in text, needle
