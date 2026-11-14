"""Synthetic tests for the P7-A stage machinery, CLI and loader-smoke (ADR-0013).

Everything runs on synthetic fixtures in temporary directories. Nothing is written under the
repository's ``experiments/`` or ``results/``, and no real checkpoint or trace is touched.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from arborlm import p6_common as common
from arborlm import p7a_analysis, p7a_sim, p7a_stage, p7a_trace
from arborlm import p7a_core as core
from arborlm import p7a_study as study
from arborlm.io import file_sha256, read_json, write_json

REPO = Path(__file__).resolve().parents[1]
FORBIDDEN = ("infrastructure validation", "does not test H1-H5", '"question_id": "G0"')


def options(tmp_path: Path, **overrides: Any) -> study.Options:
    args = argparse.Namespace(
        data_dir=tmp_path / "data",
        parent_suite=tmp_path / "suite",
        output_root=tmp_path / "experiments",
        results_root=tmp_path / "results",
        p5_results=tmp_path / "p5",
        supersede=None,
        reason=None,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    opt = study.Options(args)
    opt.synthetic = True
    opt.contexts = 4
    opt.pair_list = common.pairs()[:1]
    return opt


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """One synthetic trace + simulate run (dry-run flagged) in a temporary directory."""
    root = tmp_path_factory.mktemp("p7a-pipeline")
    opt = options(root)
    opt.dry_run = True
    code, trace_run = study.run_trace(opt)
    assert code == 0
    code, sim_run = study.run_simulate(opt)
    assert code == 0
    return {"opt": opt, "root": root, "trace_run": trace_run, "sim_run": sim_run}


# --- manifests ---
def test_stage_manifests_cite_adr_0013_and_not_the_e0_template(pipeline: dict[str, Any]) -> None:
    opt = pipeline["opt"]
    for stage in ("trace", "simulate"):
        (compact,) = list((opt.results_root / stage).iterdir())
        manifest = read_json(compact / "manifest.json")
        assert manifest["spec_reference"] == core.SPEC
        assert manifest["study"] == "P7-A" and manifest["experiment_family"] == core.FAMILY
        assert manifest["spec_sha256"] == file_sha256(REPO / core.SPEC)
        assert manifest["git_head"] and isinstance(manifest["git_dirty"], bool)
        assert manifest["p7a_source_sha256"] == core.source_hashes()
        assert set(manifest["p7a_source_sha256"]) >= {
            "src/arborlm/p7a_core.py",
            "src/arborlm/p7a_sim.py",
        }
        assert manifest["seeds"]["bootstrap"] == 91401
        assert manifest["seeds"]["L-RAND"] == [91101, 91102, 91103]
        assert manifest["start_utc"] and manifest["end_utc"] and manifest["status"] == "completed"
        assert manifest["frozen_check_at_end"]["p7a_sources_unchanged"] is True
        assert manifest["astra_review"] == "NOT_PERFORMED"
        assert "environment" in manifest and "human_approval" in manifest
        assert "question_id" not in manifest or manifest["question_id"] == "P7-A"
        text = json.dumps(manifest)
        for banned in FORBIDDEN:
            assert banned not in text, banned


def test_worker_manifests_override_the_e0_template(pipeline: dict[str, Any]) -> None:
    opt = pipeline["opt"]
    stage_dir = next((opt.results_root / "trace").iterdir())
    manifests = list((stage_dir / "workers").glob("*.manifest.json"))
    assert manifests
    for path in manifests:
        data = read_json(path)
        assert data["question_id"] == "P7-A"
        assert data["authorized_spec_reference"] == core.SPEC
        assert data["hypothesis_null_reason"] is None
        text = json.dumps(data)
        for banned in FORBIDDEN:
            assert banned not in text, banned


# --- rerun refusal ---
def test_second_run_of_a_stage_is_refused_without_a_recorded_reason(tmp_path: Path) -> None:
    kwargs = dict(
        output_root=tmp_path / "experiments",
        results_root=tmp_path / "results",
        argv=["p7a"],
        arguments={},
    )
    first = p7a_stage.open_stage("trace", **kwargs)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="refusing to run"):
        p7a_stage.open_stage("trace", **kwargs)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="reason"):
        p7a_stage.open_stage("trace", supersede=first.run.name, **kwargs)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="not an earlier"):
        p7a_stage.open_stage(
            "trace",
            supersede="nope",
            supersede_reason="x",
            **kwargs,  # type: ignore[arg-type]
        )
    second = p7a_stage.open_stage(
        "trace",
        supersede=first.run.name,
        supersede_reason="test rerun",
        **kwargs,  # type: ignore[arg-type]
    )
    assert second.manifest["supersedes"]["run_id"] == first.run.name
    assert second.manifest["supersedes"]["reason"] == "test rerun"
    assert second.run != first.run  # a fresh run ID each time
    # a different stage is not blocked, and a dry run is never counted as a prior run
    p7a_stage.open_stage("simulate", **kwargs)  # type: ignore[arg-type]
    for context in (first, second):
        p7a_stage.finish(context, "failed", "test", {})


def test_options_require_supersede_and_reason_together(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        options(tmp_path, supersede="x")
    with pytest.raises(SystemExit):
        options(tmp_path, reason="y")


def test_end_of_stage_check_catches_a_changed_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = p7a_stage.open_stage(
        "trace",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=["p7a"],
        arguments={},
        dry_run=True,
    )
    monkeypatch.setattr(core, "source_hashes", lambda root=None: {"src/arborlm/p7a_core.py": "0"})
    assert p7a_stage.finish(context, "completed", None, {}) == "failed"
    final = read_json(context.run / "manifest.json")
    assert final["status"] == "failed" and "p7a" in final["reason"]
    assert final["frozen_check_at_end"]["p7a_sources_unchanged"] is False


def test_end_of_stage_check_catches_a_changed_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = p7a_stage.open_stage(
        "trace",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=["p7a"],
        arguments={},
        dry_run=True,
    )
    monkeypatch.setattr(core, "spec_sha256", lambda repo=None: "0" * 64)
    assert p7a_stage.finish(context, "completed", None, {}) == "failed"
    assert "specification" in read_json(context.run / "manifest.json")["reason"]


# --- dry-run and registered roots ---
def test_dry_run_refuses_registered_roots() -> None:
    with pytest.raises(ValueError, match="dry run"):
        p7a_stage.registered_roots_refused(REPO / "experiments")
    with pytest.raises(ValueError, match="dry run"):
        p7a_stage.registered_roots_refused(REPO / "results" / "p7a-2026-11-13")
    p7a_stage.registered_roots_refused(Path("/tmp") / "scratch")
    before = _listing()
    with pytest.raises(ValueError, match="dry run"):
        p7a_stage.open_stage(
            "trace",
            output_root=REPO / "experiments",
            results_root=REPO / "results" / "p7a-2026-11-13",
            argv=[],
            arguments={},
            dry_run=True,
        )
    assert _listing() == before


def _listing() -> dict[str, list[str]]:
    out = {}
    for name in ("experiments", "results"):
        root = REPO / name
        out[name] = sorted(p.name for p in root.iterdir()) if root.is_dir() else []
    return out


def test_dry_run_leaves_the_registered_folders_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = _listing()
    registered_results = REPO / "results" / "p7a-2026-11-13"
    existed = registered_results.exists()
    args = argparse.Namespace(
        data_dir=Path("data/wikitext2"),
        parent_suite=None,
        output_root=Path("experiments"),
        results_root=Path("results/p7a-2026-11-13"),
        p5_results=core.P5_RESULTS,
        supersede=None,
        reason=None,
    )
    assert study.dry_run(args) == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["experiments_and_results_unchanged"] is True
    assert summary["trace"] == summary["simulate"] == summary["analyze"] == 0
    assert set(summary["analysis_outcomes"].values()) == {"INCOMPLETE"}
    assert _listing() == before and registered_results.exists() == existed


# --- stage dependencies and linkage ---
def test_simulate_and_analyze_require_a_completed_predecessor(tmp_path: Path) -> None:
    opt = options(tmp_path)
    opt.dry_run = True
    with pytest.raises(ValueError, match="completed trace"):
        study.run_simulate(opt)
    with pytest.raises(ValueError, match="completed simulate"):
        study.run_analyze(opt)
    # a dry-run record is never consumed by a registered (non dry-run) stage
    opt.dry_run = False
    with pytest.raises(ValueError):
        study.run_simulate(opt)


def test_a_failed_trace_is_not_a_completed_trace(tmp_path: Path) -> None:
    opt = options(tmp_path)
    opt.dry_run = True
    context = p7a_stage.open_stage(
        "trace",
        output_root=opt.output_root,
        results_root=opt.results_root,
        argv=[],
        arguments={},
        dry_run=True,
    )
    p7a_stage.finish(context, "failed", "synthetic failure", {"completed_labels": []})
    with pytest.raises(ValueError, match="completed trace"):
        study.run_simulate(opt)


def test_analysis_linkage_detects_a_tampered_trace_record(pipeline: dict[str, Any]) -> None:
    opt = pipeline["opt"]
    sim_compact = next((opt.results_root / "simulate").iterdir())
    records = study.load_simulation_records(opt.results_root, sim_compact.name)
    assert len(records) == 3
    assert study.check_linkage(opt, sim_compact, records)["checked_records"] == 3
    trace_compact = next((opt.results_root / "trace").iterdir())
    victim = next((trace_compact / "checkpoints").iterdir())
    original = victim.read_text()
    try:
        data = json.loads(original)
        data["files"]["evaluation"]["selected"]["sha256"] = "0" * 64
        victim.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="linkage"):
            study.check_linkage(opt, sim_compact, records)
    finally:
        victim.write_text(original)
    manifest = trace_compact / "manifest.json"
    original = manifest.read_text()
    try:
        write_json(manifest, {**json.loads(original), "p7a_source_sha256": {"x": "1"}})
        with pytest.raises(ValueError, match="linkage"):
            study.check_linkage(opt, sim_compact, records)
    finally:
        manifest.write_text(original)
    study.check_linkage(opt, sim_compact, records)  # restored


def test_stage_outputs_have_the_documented_schema(pipeline: dict[str, Any]) -> None:
    opt = pipeline["opt"]
    trace_compact = next((opt.results_root / "trace").iterdir())
    record = read_json(next((trace_compact / "checkpoints").glob("*flat*.json")))
    assert set(record) >= {
        "schema",
        "label",
        "kind",
        "pair",
        "cell_index",
        "queries",
        "files",
        "integrity",
        "replay",
        "checkpoint",
        "format",
        "evaluation_stream",
        "calibration_stream",
        "trace_dir",
    }
    assert set(record["files"]["evaluation"]) == {"selected", "branches"}
    assert record["files"]["evaluation"]["branches"] is None  # flat
    trace_dir = pipeline["trace_run"] / "traces" / record["trace_dir"]
    assert sorted(p.name for p in trace_dir.iterdir()) == [
        "calib_selected.int16.bin",
        "eval_selected.int16.bin",
    ]
    sim_compact = next((opt.results_root / "simulate").iterdir())
    result = read_json(sim_compact / "workers" / f"{record['label']}.result.json")
    assert result["outcome"] == "completed" and result["schema"] == core.SCHEMA_SIM
    assert set(result["record"]) >= {
        "streams",
        "layouts",
        "uniform_reference",
        "bootstrap",
        "key_reads",
        "complete",
        "evaluation_counts",
    }
    stream = result["record"]["streams"]["actual"]["L-FREQ|R2"]
    assert set(stream) == {"stats", "by_c"}
    assert set(stream["by_c"]["32"]) == {
        "misses_all",
        "first_touch_all",
        "misses_warm",
        "first_touch_warm",
    }


def test_simulate_worker_stops_on_a_modified_trace_file(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    opt = pipeline["opt"]
    trace_compact = next((opt.results_root / "trace").iterdir())
    record_path = next((trace_compact / "checkpoints").glob("*flat*.json"))
    record = read_json(record_path)
    traces = tmp_path / "run" / "traces"
    traces.mkdir(parents=True)
    source = pipeline["trace_run"] / "traces" / record["trace_dir"]
    target = traces / record["trace_dir"]
    target.mkdir()
    for path in source.iterdir():
        data = bytearray(path.read_bytes())
        if path.name.startswith("eval_selected"):
            data[0] ^= 1
        (target / path.name).write_bytes(bytes(data))
    run = tmp_path / "worker"
    run.mkdir()
    write_json(
        run / "manifest.json",
        {
            "status": "running",
            "experiment_family": core.FAMILY,
            "question_id": "P7-A",
            "limits": {"process_seconds": 600},
        },
    )
    code = study._sim_worker([str(run), str(traces), str(record_path), str(tmp_path), "1"])
    assert code == 1
    result = read_json(run / "result.json")
    assert result["outcome"] == "gate_violation" and result["gate"] == "trace_integrity"
    # an intact copy succeeds
    run2 = tmp_path / "worker2"
    run2.mkdir()
    write_json(run2 / "manifest.json", read_json(run / "manifest.json"))
    assert (
        study._sim_worker(
            [str(run2), str(pipeline["trace_run"] / "traces"), str(record_path), str(tmp_path), "1"]
        )
        == 0
    )
    assert read_json(run2 / "result.json")["record"]["complete"] is True


def test_worker_refuses_a_manifest_that_does_not_cite_p7a(tmp_path: Path) -> None:
    run = tmp_path / "w"
    run.mkdir()
    write_json(
        run / "manifest.json",
        {"status": "running", "experiment_family": core.FAMILY, "question_id": "G0"},
    )
    with pytest.raises(ValueError, match="P7-A"):
        study._worker_run(str(run), "simulate")


def test_worker_supervision_records_partial_output_and_stops_on_failure(tmp_path: Path) -> None:
    context = p7a_stage.open_stage(
        "simulate",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=[],
        arguments={},
        dry_run=True,
    )
    script = (
        "import json,sys,pathlib; r=pathlib.Path(sys.argv[1]); "
        "(r/'partial.json').write_text('{\"x\":1}'); "
        "(r/'result.json').write_text(json.dumps({'outcome': sys.argv[2], 'gate': 'invariant', "
        "'message': 'boom'})); sys.exit(0 if sys.argv[2]=='completed' else 1)"
    )

    def argv_for(label: str, child: Path) -> list[str]:
        mode = "completed" if label == "first" else "gate_violation"
        return [sys.executable, "-c", script, str(child), mode]

    outcome = p7a_stage.run_workers(
        context,
        [("first", {}), ("second", {}), ("third", {})],
        argv_for=argv_for,
        cap_seconds=60.0,
    )
    assert outcome.status == "failed" and "invariant" in (outcome.reason or "")
    statuses = {r["label"]: r["status"] for r in outcome.rows}
    assert statuses == {"first": "completed", "second": "failed", "third": "unexecuted"}
    workers = context.compact / "workers"
    assert (workers / "second.partial.json").is_file() and (workers / "first.result.json").is_file()
    assert read_json(workers / "second.manifest.json")["question_id"] == "P7-A"
    p7a_stage.finish(context, "failed", outcome.reason, {})


def test_a_zero_cap_stops_before_any_worker_starts(tmp_path: Path) -> None:
    context = p7a_stage.open_stage(
        "simulate",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=[],
        arguments={},
        dry_run=True,
    )
    outcome = p7a_stage.run_workers(
        context,
        [("a", {})],
        argv_for=lambda label, child: [sys.executable, "-c", "pass"],
        cap_seconds=0.0,
    )
    assert outcome.status == "failed" and "cap" in (outcome.reason or "")
    assert outcome.rows[0]["status"] == "unexecuted"
    p7a_stage.finish(context, "failed", outcome.reason, {})


# --- loader-smoke ---
def test_loader_smoke_computes_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("loader-smoke must not compute a trace, simulation or analysis")

    for module, name in (
        (p7a_trace, "trace_checkpoint"),
        (p7a_trace, "collect_trace"),
        (p7a_trace, "synthetic_trace"),
        (p7a_sim, "simulate_checkpoint"),
        (p7a_analysis, "analyze_records"),
        (study, "run_trace"),
        (study, "run_simulate"),
        (study, "run_analyze"),
        (p7a_stage, "open_stage"),
    ):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(
        common, "load_real_cell", lambda pair, **kw: common.load_synthetic_cell(pair, rows=4)
    )
    opt = options(tmp_path)
    before = _listing()
    report = study.loader_smoke(opt)
    assert report["all_replays_bitwise_equal"] is True
    assert report["checkpoint_files_unchanged"] is True
    assert report["p7a_quantities_computed"] is False
    assert set(report["replays"]) == {"flat", "fixed_tree", "learned_tree"}
    assert all(r["state_digest_unchanged"] for r in report["replays"].values())
    assert _listing() == before
    assert not (tmp_path / "experiments").exists() and not (tmp_path / "results").exists()


def test_loader_smoke_reports_a_replay_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def tampered(pair: Any, **kw: Any) -> common.CellSource:
        source = common.load_synthetic_cell(pair, rows=4)
        source.recorded["flat"]["nll"] += 1e-9
        return source

    monkeypatch.setattr(common, "load_real_cell", tampered)
    report = study.loader_smoke(options(tmp_path))
    assert report["all_replays_bitwise_equal"] is False
    assert report["replays"]["flat"]["bitwise_equal"] is False
    assert report["replays"]["fixed_tree"]["bitwise_equal"] is True


def test_configuration_counts_match_section_10() -> None:
    assert p7a_sim.config_count("flat") == 450
    assert p7a_sim.config_count("fixed_tree") == p7a_sim.config_count("learned_tree") == 480


# --- item 11 (M1): the analysis guard ---
LABELS = [core.cell_label(p, k) for p, k in core.registered_checkpoints()[:3]]


def write_check(path: Path, pipeline: dict[str, Any], **changes: Any) -> Path:
    """A synthetic independent_sim.py summary for the pipeline's simulate run (tests only; the file
    is NOT produced by the auditor's script)."""
    sim_id, trace_id = pipeline["sim_run"].name, pipeline["trace_run"].name
    data: dict[str, Any] = {
        "tool": "synthetic test file",
        "argv": [
            "independent_sim.py",
            "--trace-root",
            f"experiments/{trace_id}/traces",
            "--sim-workers",
            f"results/p7a-2026-11-13/simulate/{sim_id}/workers",
            "--registered-selection",
            "--allow-small",
        ],
        "selection": LABELS,
        "tie_rule": "asc",
        "checkpoints": {lb: {"differences": [], "integrity_problems": []} for lb in LABELS},
        "verdict": "AGREE",
    }
    data.update(changes)
    write_json(path, data)
    return path


def analyze_opt(pipeline: dict[str, Any], check: Path | None) -> study.Options:
    opt = pipeline["opt"]
    opt.independent_check, opt.independent_expected = check, LABELS
    return opt


def test_analysis_refuses_when_sources_spec_or_head_differ_from_simulate(
    pipeline: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opt = analyze_opt(pipeline, write_check(tmp_path / "check.json", pipeline))

    def analyses() -> list[Path]:
        root = opt.results_root / "analyze"
        return sorted(root.glob("*")) if root.exists() else []

    before = analyses()
    real = core.source_hashes()
    monkeypatch.setattr(
        core, "source_hashes", lambda root=None: {**real, "src/arborlm/p7a_analysis.py": "0"}
    )
    with pytest.raises(ValueError, match="analysis refused.*p7a_source_sha256"):
        study.run_analyze(opt)
    monkeypatch.setattr(core, "source_hashes", lambda root=None: real)
    monkeypatch.setattr(core, "spec_sha256", lambda repo=None: "0" * 64)
    with pytest.raises(ValueError, match="analysis refused.*spec_sha256"):
        study.run_analyze(opt)
    monkeypatch.undo()
    monkeypatch.setattr(study, "git_head", lambda: ("0" * 40, False))
    with pytest.raises(ValueError, match="analysis refused.*git_head"):
        study.run_analyze(opt)
    assert analyses() == before  # refused before any analysis run directory was opened
    monkeypatch.undo()
    # unchanged: it runs, and records what it checked
    code, run = study.run_analyze(opt)
    assert code == 0
    manifest = read_json(run / "manifest.json")
    assert manifest["linkage"]["frozen_against_simulate"]["equal_to_simulate_manifest"] is True
    assert manifest["linkage"]["independent_check_sha256"] == file_sha256(tmp_path / "check.json")


# --- item 12 (M2): the independent-simulator gate ---
def test_analysis_requires_the_independent_simulator_file(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="--independent-check"):
        study.run_analyze(analyze_opt(pipeline, None))
    with pytest.raises(ValueError, match="not found"):
        study.run_analyze(analyze_opt(pipeline, tmp_path / "missing.json"))
    (tmp_path / "junk.json").write_text("not json")
    with pytest.raises(ValueError, match="not JSON"):
        study.run_analyze(analyze_opt(pipeline, tmp_path / "junk.json"))


def gate(pipeline: dict[str, Any], path: Path, **kw: Any) -> dict[str, Any]:
    return study.check_independent_comparison(
        path,
        simulate_run_id=pipeline["sim_run"].name,
        trace_run_id=pipeline["trace_run"].name,
        expected_selection=kw.pop("expected_selection", LABELS),
        allow_small=kw.pop("allow_small", True),
    )


def test_independent_gate_accepts_an_agreeing_file_and_records_its_hash(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    path = write_check(tmp_path / "agree.json", pipeline)
    record = gate(pipeline, path)
    assert record["sha256"] == file_sha256(path) and record["verdict"] == "AGREE"
    assert record["tie_rule"] == "asc" and record["checkpoints"] == 3
    code, run = study.run_analyze(analyze_opt(pipeline, path))
    assert code == 0
    assert read_json(run / "manifest.json")["linkage"]["independent_check_sha256"] == file_sha256(
        path
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"verdict": "DIFFER"}, "not 'AGREE'"),
        ({"verdict": None}, "not 'AGREE'"),
        ({"tie_rule": "desc"}, "tie rule"),
        ({"selection": LABELS[:2]}, "registered clarification-7 selection"),
        ({"selection": [*LABELS[:2], core.cell_label((103, 303, 503), "flat")]}, "registered"),
        (
            {
                "checkpoints": {
                    lb: {"differences": ["C=8 misses_all: independent 1 study 2"]} for lb in LABELS
                }
            },
            "differences",
        ),
        ({"checkpoints": {lb: {"integrity_problems": ["x"]} for lb in LABELS}}, "integrity"),
        ({"checkpoints": {LABELS[0]: {"differences": [], "integrity_problems": []}}}, "cover"),
        (
            {
                "argv": [
                    "independent_sim.py",
                    "--sim-workers",
                    "results/r/simulate/{sim}/workers",
                    "--trace-root",
                    "experiments/{trace}/traces",
                ]
            },
            "registered-selection",
        ),
    ],
)
def test_independent_gate_refuses_a_file_that_does_not_qualify(
    pipeline: dict[str, Any], tmp_path: Path, changes: dict[str, Any], message: str
) -> None:
    if "argv" in changes:
        changes["argv"] = [
            a.replace("{sim}", pipeline["sim_run"].name).replace(
                "{trace}", pipeline["trace_run"].name
            )
            for a in changes["argv"]
        ]
    path = write_check(tmp_path / "bad.json", pipeline, **changes)
    with pytest.raises(ValueError, match=message):
        gate(pipeline, path)


def test_independent_gate_refuses_a_file_about_another_run(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    path = write_check(tmp_path / "other_sim.json", pipeline)
    data = read_json(path)
    data["argv"] = [a.replace(pipeline["sim_run"].name, "P7AS-OTHER") for a in data["argv"]]
    write_json(path, data)
    with pytest.raises(ValueError, match="this simulate run"):
        gate(pipeline, path)
    path = write_check(tmp_path / "other_trace.json", pipeline)
    data = read_json(path)
    data["argv"] = [a.replace(pipeline["trace_run"].name, "P7AT-OTHER") for a in data["argv"]]
    write_json(path, data)
    with pytest.raises(ValueError, match="this trace run"):
        gate(pipeline, path)
    path = write_check(tmp_path / "no_sim.json", pipeline, argv=["independent_sim.py"])
    with pytest.raises(ValueError, match="this simulate run"):
        gate(pipeline, path)


def test_independent_gate_refuses_a_small_synthetic_check_outside_a_dry_run(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    path = write_check(tmp_path / "small.json", pipeline)
    with pytest.raises(ValueError, match="allow-small"):
        gate(pipeline, path, allow_small=False)


def test_independent_gate_defaults_to_the_registered_eighteen(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    selection = core.independent_selection()
    path = write_check(
        tmp_path / "eighteen.json",
        pipeline,
        selection=selection,
        checkpoints={lb: {"differences": [], "integrity_problems": []} for lb in selection},
        argv=[
            a
            for a in read_json(write_check(tmp_path / "t.json", pipeline))["argv"]
            if a != "--allow-small"
        ],
    )
    record = study.check_independent_comparison(
        path,
        simulate_run_id=pipeline["sim_run"].name,
        trace_run_id=pipeline["trace_run"].name,
    )
    assert record["checkpoints"] == 18 and record["selection"] == sorted(selection)
    with pytest.raises(ValueError, match="registered clarification-7 selection"):
        gate(pipeline, write_check(tmp_path / "three.json", pipeline), expected_selection=None)


# --- item 13 ---
def test_calibration_slice_is_ranks_2048_to_2559_of_the_4096_pool() -> None:
    import torch

    pool = torch.arange(4096 * 3).reshape(4096, 3)
    cal = study.calibration_slice(pool)
    assert cal.shape == (512, 3) and torch.equal(cal, pool[2048:2560])
    assert int(cal[0, 0]) == 2048 * 3 and int(cal[-1, 0]) == 2559 * 3
    with pytest.raises(ValueError, match="4,096"):
        study.calibration_slice(pool[:4095])
    with pytest.raises(ValueError, match="4,096"):
        study.calibration_slice(torch.cat([pool, pool[:1]]))


def test_simulate_worker_reproduces_the_p5_histogram_when_a_record_is_given(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    opt = pipeline["opt"]
    trace_compact = next((opt.results_root / "trace").iterdir())
    record_path = next((trace_compact / "checkpoints").glob("*flat*.json"))
    record = read_json(record_path)
    traces = pipeline["trace_run"] / "traces"
    selected, _ = core.read_trace(
        traces / record["trace_dir"], "eval", record["files"]["evaluation"]
    )
    counts = core.selection_counts(selected)
    p5 = tmp_path / "p5"
    (p5 / record["label"]).mkdir(parents=True)

    def run_worker(name: str, histogram: list[int]) -> tuple[int, Path]:
        write_json(
            p5 / record["label"] / "result.json",
            {
                "final": {
                    "retrieval": {
                        "selected_slot_counts": histogram,
                        "unique_selected_slots": sum(1 for c in histogram if c),
                    }
                }
            },
        )
        run = tmp_path / name
        run.mkdir()
        write_json(
            run / "manifest.json",
            {
                "status": "running",
                "experiment_family": core.FAMILY,
                "question_id": "P7-A",
                "limits": {"process_seconds": 600},
            },
        )
        code = study._sim_worker([str(run), str(traces), str(record_path), str(p5), "0"])
        return code, run

    code, run = run_worker("good", counts)
    assert code == 0 and read_json(run / "result.json")["record"]["complete"] is True
    wrong = list(counts)
    donor = next(i for i, c in enumerate(wrong) if c)
    wrong[donor] -= 1
    wrong[(donor + 1) % core.SLOTS] += 1
    code, run = run_worker("bad", wrong)
    result = read_json(run / "result.json")
    assert code == 1 and result["gate"] == "trace_integrity"
    assert "P5" in result["message"]


def test_workers_use_the_deterministic_configuration_and_their_own_environment_record(
    pipeline: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(p7a_trace, "configure_deterministic_cpu", lambda: calls.append("cfg"))
    opt = pipeline["opt"]
    trace_compact = next((opt.results_root / "trace").iterdir())
    record_path = next((trace_compact / "checkpoints").glob("*flat*.json"))
    run = tmp_path / "w"
    run.mkdir()
    write_json(
        run / "manifest.json",
        {
            "status": "running",
            "experiment_family": core.FAMILY,
            "question_id": "P7-A",
            "limits": {"process_seconds": 600},
        },
    )
    code = study._sim_worker(
        [str(run), str(pipeline["trace_run"] / "traces"), str(record_path), str(tmp_path), "1"]
    )
    assert code == 0 and calls == ["cfg"]  # the single-thread deterministic setup was applied
    environment = read_json(run / "environment.json")
    assert environment["storage_device_reason"] == f"no storage experiment in {core.FAMILY}"
    # every worker folder of the synthetic trace and simulate runs: no P6 wording
    folders = [*(pipeline["trace_run"] / "workers").glob("*/environment.json")]
    folders += [*(pipeline["sim_run"] / "workers").glob("*/environment.json")]
    assert len(folders) == 4  # one trace worker (1 pair) and three simulate workers
    for path in folders:
        text = path.read_text()
        assert "P6E" not in text and "P6" not in text and core.FAMILY in text


# --- item 13: the end-of-stage repository check ---
def _git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for name in ("src/arborlm", "tests", "docs/reviews", "docs/decisions", "configs"):
        (repo / name).mkdir(parents=True)
    (repo / ".gitignore").write_text("results/\nexperiments/\ndata/\n")
    (repo / "src/arborlm/tracked.py").write_text("x = 1\n")
    (repo / "docs/decisions/ADR.md").write_text("spec\n")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "src/arborlm/p7a_x.py").write_text("y = 1\n")  # untracked P7-A source
    return repo


def test_end_of_stage_check_ignores_unrelated_new_files_but_not_code_or_tracked_changes(
    scratch_repo: Path,
) -> None:
    repo = scratch_repo
    base = p7a_stage.tracked_state_sha256(repo)
    assert p7a_stage.tracked_state_sha256(repo) == base  # deterministic
    # not covered, by design: new or edited untracked files outside the guarded trees
    (repo / "docs/reviews/new_audit.md").write_text("audit\n")
    (repo / "scratch").mkdir()
    (repo / "scratch/notes.txt").write_text("n\n")
    (repo / "results").mkdir()
    (repo / "results/out.json").write_text("{}")
    assert p7a_stage.tracked_state_sha256(repo) == base
    (repo / "docs/reviews/new_audit.md").write_text("audit, edited\n")
    assert p7a_stage.tracked_state_sha256(repo) == base
    # covered: a tracked file changes
    (repo / "src/arborlm/tracked.py").write_text("x = 2\n")
    changed = p7a_stage.tracked_state_sha256(repo)
    assert changed != base
    (repo / "src/arborlm/tracked.py").write_text("x = 1\n")
    assert p7a_stage.tracked_state_sha256(repo) == base
    (repo / "docs/decisions/ADR.md").write_text("spec, edited\n")
    assert p7a_stage.tracked_state_sha256(repo) != base
    (repo / "docs/decisions/ADR.md").write_text("spec\n")
    # covered: the content of an untracked p7a source, a new test, a new source file
    (repo / "src/arborlm/p7a_x.py").write_text("y = 2\n")
    assert p7a_stage.tracked_state_sha256(repo) != base
    (repo / "src/arborlm/p7a_x.py").write_text("y = 1\n")
    assert p7a_stage.tracked_state_sha256(repo) == base
    (repo / "tests/test_p7a_new.py").write_text("pass\n")
    assert p7a_stage.tracked_state_sha256(repo) != base
    (repo / "tests/test_p7a_new.py").unlink()
    (repo / "src/arborlm/other.py").write_text("z = 1\n")
    assert p7a_stage.tracked_state_sha256(repo) != base


def test_verify_frozen_flags_a_p7a_source_edit_and_names_the_tracked_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = p7a_stage.open_stage(
        "trace",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=["p7a"],
        arguments={},
        dry_run=True,
    )
    assert p7a_stage.verify_frozen(context) is None
    real = core.source_hashes()
    monkeypatch.setattr(
        core, "source_hashes", lambda root=None: {**real, "src/arborlm/p7a_sim.py": "0"}
    )
    assert "p7a" in (p7a_stage.verify_frozen(context) or "")
    monkeypatch.undo()
    monkeypatch.setattr(p7a_stage, "tracked_state_sha256", lambda repo=None: "0" * 64)
    assert "version-controlled" in (p7a_stage.verify_frozen(context) or "")
    monkeypatch.undo()
    p7a_stage.finish(context, "failed", "test", {})
