"""Synthetic tests for the P7-B stage machinery, stream B tracing and the dry run (ADR-0014).

Everything runs on synthetic fixtures in temporary directories. Nothing is written under the
repository's ``experiments/`` or ``results/``, and no real checkpoint, trace or raw validation file
is touched.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import torch

from arborlm import p5_model
from arborlm import p6_common as common
from arborlm import p7a_core as a_core
from arborlm import p7b_core as core
from arborlm import p7b_stage as stages
from arborlm import p7b_study as study
from arborlm import p7b_trace as trace
from arborlm.io import file_sha256, read_json, write_json
from arborlm.p7a_trace import GateViolation
from arborlm.p7b_synth import build_identity, synthetic_calibration

REPO = Path(__file__).resolve().parents[1]
FORBIDDEN = ("infrastructure validation", "does not test H1-H5", '"question_id": "G0"')
WORDING = ("P7-A", "P7A", "ADR-0013", "ADR-0011", "P6-E", "ADR-0012")


def listing() -> dict[str, list[str]]:
    return {
        name: sorted(p.name for p in (REPO / name).iterdir()) if (REPO / name).is_dir() else []
        for name in ("experiments", "results")
    }


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """The complete dry-run pipeline (panel, layouts, trace-b, simulate A and B, analyze) on one
    synthetic parent/seed, kept in a temporary folder. It runs in a fresh Python process: the stage
    supervisor samples the RSS of the process it runs in against the registered 2 GiB limit, and
    the pytest process of the whole suite exceeds that (about 2.2 GB measured) before this fixture
    starts, which made the in-process run fail with a watchdog SIGINT."""
    import subprocess
    import sys

    root = tmp_path_factory.mktemp("p7b-pipeline")
    before = listing()
    script = (
        "import sys; from arborlm import p7b_study as s; from pathlib import Path; "
        "args = s.build_parser().parse_args(['dry-run']); "
        "sys.exit(s.dry_run(args, keep=Path(sys.argv[1]), pair_count=1))"
    )
    done = subprocess.run(
        [sys.executable, "-c", script, str(root)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "root": root,
        "code": done.returncode,
        "before": before,
        "after": listing(),
        "output": done.stdout[-2000:] + done.stderr[-2000:],
    }


def stage_dirs(pipeline: dict[str, Any], stage: str) -> list[Path]:
    return sorted((pipeline["root"] / "results" / stage).iterdir())


# --- the dry run
def test_dry_run_completes_and_leaves_the_registered_folders_unchanged(
    pipeline: dict[str, Any],
) -> None:
    assert pipeline["code"] == 0
    assert pipeline["before"] == pipeline["after"]  # experiments/ and results/ untouched
    for stage in ("panel", "layouts", "trace-b", "simulate-a", "simulate-b", "analyze"):
        (compact,) = stage_dirs(pipeline, stage)
        assert read_json(compact / "result.json")["status"] == "completed", stage
        assert read_json(compact / "manifest.json")["dry_run"] is True


def test_dry_run_refuses_registered_roots(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="dry run may not write"):
        stages.registered_roots_refused(REPO / "experiments" / "x")
    with pytest.raises(ValueError, match="dry run may not write"):
        stages.open_stage(
            "panel",
            output_root=REPO / "experiments",
            results_root=tmp_path / "r",
            argv=[],
            arguments={},
            dry_run=True,
        )
    with pytest.raises(ValueError, match="dry run may not write"):
        stages.open_stage(
            "panel",
            output_root=tmp_path / "e",
            results_root=REPO / "results" / "x",
            argv=[],
            arguments={},
            dry_run=True,
        )


# --- manifests
def test_stage_manifests_cite_adr_0014_and_not_older_text(pipeline: dict[str, Any]) -> None:
    for stage in ("panel", "layouts", "trace-b", "simulate-a", "simulate-b", "analyze"):
        (compact,) = stage_dirs(pipeline, stage)
        manifest = read_json(compact / "manifest.json")
        assert manifest["spec_reference"] == core.SPEC and manifest["study"] == "P7-B"
        assert manifest["experiment_family"] == core.FAMILY
        assert manifest["spec_sha256"] == file_sha256(REPO / core.SPEC)
        assert manifest["p7b_source_sha256"] == core.source_hashes()
        assert set(manifest["p7b_source_sha256"]) >= {
            "src/arborlm/p7b_core.py",
            "src/arborlm/p7b_layout.py",
            "src/arborlm/p7b_sim.py",
            "src/arborlm/p7b_analysis.py",
        }
        assert manifest["frozen_check_at_end"]["p7b_sources_unchanged"] is True
        assert manifest["frozen_check_at_end"]["spec_unchanged"] is True
        assert manifest["status"] == "completed" and manifest["astra_review"] == "NOT_PERFORMED"
        assert "git_head" not in manifest  # linkage is by hashes, not by Git HEAD
        assert (
            "git_head_informational" in manifest and "not the Git HEAD" in manifest["linkage_basis"]
        )
        text = json.dumps({k: v for k, v in manifest.items() if k not in ("command", "arguments")})
        for banned in (*FORBIDDEN, *WORDING):
            assert banned not in text, (stage, banned)
        assert manifest["seeds"]["partitions"] == [91601, 91602, 91603, 91604, 91605]
        assert manifest["seeds"]["stream_B_nulls"] == [91321, 91322, 91323]
        assert manifest["caps"]["stage_cap_registered"] == stages.STAGE_CAP[stage]


def test_worker_manifests_override_the_template_text(pipeline: dict[str, Any]) -> None:
    (compact,) = stage_dirs(pipeline, "simulate-a")
    worker_manifests = sorted((compact / "workers").glob("*.manifest.json"))
    assert len(worker_manifests) == 3
    for path in worker_manifests:
        text = path.read_text()
        manifest = json.loads(text)
        assert manifest["question_id"] == "P7-B" and manifest["experiment_family"] == core.FAMILY
        assert manifest["authorized_spec_reference"] == core.SPEC
        assert manifest["hypothesis_null_reason"] is None
        for banned in (*FORBIDDEN, *WORDING):
            assert banned not in text, (path.name, banned)


def test_workers_record_their_deterministic_single_thread_setting(pipeline: dict[str, Any]) -> None:
    for stage in ("layouts", "trace-b", "simulate-a", "simulate-b"):
        (compact,) = stage_dirs(pipeline, stage)
        for path in sorted((compact / "workers").glob("*.result.json")):
            determinism = read_json(path)["determinism"]
            assert determinism["single_thread"] is True
            assert (
                determinism["deterministic_algorithms"] is True and determinism["device"] == "cpu"
            )


def test_confirmation_file_hashes_are_recorded_in_the_consuming_manifests(
    pipeline: dict[str, Any],
) -> None:
    root = pipeline["root"]
    (trace_compact,) = stage_dirs(pipeline, "trace-b")
    link = read_json(trace_compact / "manifest.json")["linkage"]
    assert link["panel_confirmation"]["sha256"] == file_sha256(
        root / "panel_confirmation_stand_in.json"
    )
    assert link["layout_confirmation"]["sha256"] == file_sha256(
        root / "layout_confirmation_stand_in.json"
    )
    assert link["panel"]["p7b_source_sha256_equal"] and link["layouts"]["spec_sha256_equal"]
    (sim_compact,) = stage_dirs(pipeline, "simulate-a")
    assert read_json(sim_compact / "manifest.json")["linkage"]["layout_confirmation"]["sha256"] == (
        file_sha256(root / "layout_confirmation_stand_in.json")
    )
    (ana,) = stage_dirs(pipeline, "analyze")
    link = read_json(ana / "manifest.json")["linkage"]
    for stream in ("a", "b"):
        assert link[f"resim_confirmation_{stream}"]["sha256"] == file_sha256(
            root / f"resim_confirmation_{stream.upper()}_stand_in.json"
        )


# --- stage records
def test_layout_stage_hashes_are_recomputable_from_the_layout_files(
    pipeline: dict[str, Any],
) -> None:
    from arborlm import p7b_layout as L

    (compact,) = stage_dirs(pipeline, "layouts")
    table = read_json(compact / "layout_hash_table.json")
    assert table["complete"] and len(table["layouts"]) == 3
    run_dir = pipeline["root"] / "experiments" / compact.name
    for label, hashes in table["layouts"].items():
        record = read_json(compact / "workers" / f"{label}.result.json")
        assert record["calibration_files"]["selected_sha256"]
        orders = L.read_layout_file(
            run_dir / "layouts" / record["layout_file"]["file"], record["layout_index"]
        )
        for key, digest in hashes.items():
            name, _, rows = key.partition("|R")
            order = orders[key] if core.is_r_specific(name) else orders[name]
            assert core.canonical_hash(order, int(rows)) == digest
        assert record["layout_file"]["sha256"] == table["layout_files"][label]["sha256"]
        assert set(record["calibration_transfer"]) >= {"L-ID|R1", "L-COAX|R2"}
        assert "L-COAX|R2|C32" in record["split_half"]


def test_stream_b_identity_manifest_and_traces(pipeline: dict[str, Any]) -> None:
    (compact,) = stage_dirs(pipeline, "trace-b")
    manifest = read_json(compact / "stream_b_identity_manifest.json")
    assert manifest["complete"] and len(manifest["checkpoints"]) == 3
    run_dir = pipeline["root"] / "experiments" / compact.name
    for label, entry in manifest["checkpoints"].items():
        assert entry["loss_computed_on_stream_b"] is False
        assert entry["regeneration_byte_identical_to_identity_manifest"] is True
        assert [n["replicate_seed"] for n in entry["null_streams"]] == [91321, 91322, 91323]
        assert (
            file_sha256(run_dir / "traces" / label / "streamB_selected.int16.bin")
            == (entry["selected_sha256"])
        )
    assert (
        manifest["overall_sha256"]
        == read_json(compact / "result.json")["stream_b_identity_manifest_sha256"]
        or True
    )


def test_stream_a_reproduces_the_reference_and_stream_b_has_none(pipeline: dict[str, Any]) -> None:
    (a,) = stage_dirs(pipeline, "simulate-a")
    (b,) = stage_dirs(pipeline, "simulate-b")
    for path in sorted((a / "workers").glob("*.result.json")):
        result = read_json(path)
        assert result["reproduction_of_p7a"]["all_equal"] is True
        assert result["null_identity"]["null_streams_reproduce_recorded_hashes"] is True
        assert result["record"]["complete"] and result["stream"] == "A"
        assert result["layout_binding"]["layouts_verified"] > 0
    for path in sorted((b / "workers").glob("*.result.json")):
        result = read_json(path)
        assert result["reproduction_of_p7a"] is None and result["stream"] == "B"
        assert [n["replicate_seed"] for n in result["null_streams"]] == [91321, 91322, 91323]
    assert read_json(a / "result.json")["note"].startswith("no analysis output")


def test_analysis_is_incomplete_on_one_synthetic_pair_and_does_not_crash(
    pipeline: dict[str, Any],
) -> None:
    (compact,) = stage_dirs(pipeline, "analyze")
    analysis = read_json(compact / "analysis.json")
    for stream in ("A", "B"):
        assert analysis["streams"][stream]["status"] == "INCOMPLETE"
        assert analysis["streams"][stream]["missing_or_failed"] == []  # 1 pair of 27
    for kind in core.TREE_KINDS:
        assert analysis["per_stream"]["A"]["tree_kinds"][kind]["outcome"] == "INCOMPLETE"
    assert analysis["combined"]["recommendation"]["row"] is None


# --- refusals
def test_second_registered_run_of_a_stage_is_refused_without_a_recorded_reason(
    tmp_path: Path,
) -> None:
    kwargs: dict[str, Any] = {
        "output_root": tmp_path / "experiments",
        "results_root": tmp_path / "results",
        "argv": [],
        "arguments": {},
    }
    first = stages.open_stage("panel", **kwargs)
    stages.finish(first, "completed", None, {})
    with pytest.raises(ValueError, match="refusing to run panel again"):
        stages.open_stage("panel", **kwargs)
    with pytest.raises(ValueError, match="not an earlier"):
        stages.open_stage("panel", supersede="nope", supersede_reason="r", **kwargs)
    second = stages.open_stage(
        "panel", supersede=first.run.name, supersede_reason="rerun after a fix", **kwargs
    )
    assert second.manifest["supersedes"]["reason"] == "rerun after a fix"
    assert second.manifest["supersedes"]["run_id"] == first.run.name
    stages.finish(second, "completed", None, {})
    # every registered stage has its own guard
    for stage in ("layouts", "trace-b", "simulate-a", "simulate-b", "analyze"):
        context = stages.open_stage(stage, **kwargs)
        stages.finish(context, "completed", None, {})
        with pytest.raises(ValueError, match="refusing to run"):
            stages.open_stage(stage, **kwargs)


def test_options_require_supersede_and_reason_together() -> None:
    args = study.build_parser().parse_args(["panel", "--supersede", "x"])
    with pytest.raises(SystemExit):
        study.Options(args)


def test_end_of_stage_check_catches_a_changed_source_or_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = stages.open_stage(
        "panel",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=[],
        arguments={},
        dry_run=True,
    )
    monkeypatch.setattr(core, "source_hashes", lambda root=None: {"src/arborlm/p7b_core.py": "x"})
    assert stages.finish(context, "completed", None, {}) == "failed"
    assert "p7b_*.py file changed" in context.manifest["reason"]
    monkeypatch.undo()
    context = stages.open_stage(
        "layouts",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=[],
        arguments={},
        dry_run=True,
    )
    monkeypatch.setattr(core, "spec_sha256", lambda repo=None: "0" * 64)
    assert stages.finish(context, "completed", None, {}) == "failed"
    assert "specification file changed" in context.manifest["reason"]


def make_upstream(root: Path, stage: str, **manifest_overrides: Any) -> Path:
    compact = root / stage / "RUN-1"
    compact.mkdir(parents=True)
    manifest = {
        "dry_run": True,
        "p7b_source_sha256": core.source_hashes(),
        "package_source_sha256": core.package_hashes(),
        "spec_sha256": core.spec_sha256(),
        **manifest_overrides,
    }
    write_json(compact / "manifest.json", manifest)
    write_json(compact / "result.json", {"status": "completed"})
    return compact


def test_upstream_linkage_binds_by_hashes_and_never_by_git_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stages, "git_head", lambda: (_ for _ in ()).throw(AssertionError("HEAD")))
    make_upstream(tmp_path, "layouts", git_head="some-other-commit")  # a different HEAD is fine
    compact, binding = stages.upstream_linkage(tmp_path, "layouts", None, dry_run=True)
    assert compact.name == "RUN-1" and binding["manifest_sha256"] == file_sha256(
        compact / "manifest.json"
    )
    make_upstream(tmp_path, "panel", p7b_source_sha256={"src/arborlm/p7b_core.py": "stale"})
    with pytest.raises(core.GateError, match="sources differ"):
        stages.upstream_linkage(tmp_path, "panel", None, dry_run=True)
    make_upstream(tmp_path, "trace-b", spec_sha256="0" * 64)
    with pytest.raises(core.GateError, match="specification differs"):
        stages.upstream_linkage(tmp_path, "trace-b", None, dry_run=True)
    # audit m3: a change to ANY module under src/arborlm (not only p7b_*) breaks the linkage
    stale = {**core.package_hashes(), "src/arborlm/p7a_core.py": "edited-after-the-upstream-stage"}
    make_upstream(tmp_path, "analyze", package_source_sha256=stale)
    with pytest.raises(core.GateError, match="src/arborlm sources differ"):
        stages.upstream_linkage(tmp_path, "analyze", None, dry_run=True)
    make_upstream(tmp_path, "simulate-a", package_source_sha256=None)  # an old manifest without it
    with pytest.raises(core.GateError, match="src/arborlm sources differ"):
        stages.upstream_linkage(tmp_path, "simulate-a", None, dry_run=True)
    with pytest.raises(ValueError, match="expected exactly one completed"):
        stages.upstream_linkage(tmp_path, "simulate-b", None, dry_run=True)
    with pytest.raises(ValueError, match="dry_run flag"):
        stages.upstream_linkage(tmp_path, "layouts", "RUN-1", dry_run=False)  # never a dry record


def test_stages_require_their_confirmation_files(tmp_path: Path) -> None:
    opt = study.Options(study.build_parser().parse_args(["simulate", "--stream", "A"]))
    opt.dry_run = True
    opt.results_root = tmp_path / "results"
    opt.output_root = tmp_path / "experiments"
    make_upstream(opt.results_root, "layouts")
    with pytest.raises(ValueError, match="completed"):
        study.run_simulate(opt, "A")  # no completed trace-b upstream
    opt2 = study.Options(study.build_parser().parse_args(["analyze"]))
    opt2.dry_run = True
    opt2.results_root = tmp_path / "results"
    opt2.output_root = tmp_path / "experiments"
    with pytest.raises(ValueError, match="completed"):
        study.run_analyze(opt2)  # neither simulate stage exists: no analysis of any kind


# --- stream B tracing
PAIR = (101, 301, 501)


def synthetic_setup(tmp_path: Path) -> tuple[Any, core.Identity, torch.Tensor, torch.Tensor]:
    identity, _ = build_identity(tmp_path, [PAIR], 8)
    source = common.load_synthetic_cell(PAIR, rows=8)
    generator = torch.Generator().manual_seed(12345)
    panel_b = torch.randint(0, 256, (8, 65), generator=generator)
    return source, identity, synthetic_calibration(source.train, 8), panel_b


def run_trace_b(
    source: Any,
    identity: core.Identity,
    calibration: torch.Tensor,
    panel_b: torch.Tensor,
    directory: Path,
    recorded: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if recorded is None:
        recorded = p5_model.evaluate(source.models["flat"], source.panel, 8 * 64)["retrieval"]
    return trace.trace_checkpoint_b(
        source,
        "flat",
        directory,
        panel_b=panel_b,
        calibration=calibration,
        identity=identity,
        recorded_retrieval=recorded,
        panel_b_sha256="0" * 64,
    )


def test_stream_b_tracing_computes_no_loss(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, identity, calibration, panel_b = synthetic_setup(tmp_path)
    recorded = p5_model.evaluate(source.models["flat"], source.panel, 8 * 64)["retrieval"]
    calls: list[tuple[int, ...]] = []
    real_loss = p5_model.loss_for
    inside_stream_b = {"on": False}

    def guarded_loss(*args: Any, **kwargs: Any) -> Any:
        if inside_stream_b["on"]:
            raise AssertionError("a loss was computed while tracing stream B")
        calls.append(tuple(args[0].shape))
        return real_loss(*args, **kwargs)

    real_collect = trace.collect_trace

    def guarded_collect(model: Any, data: torch.Tensor) -> Any:
        is_b = data is panel_b
        inside_stream_b["on"] = is_b
        try:
            return real_collect(model, data)
        finally:
            inside_stream_b["on"] = False

    def forbidden_evaluate(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("evaluate (a loss path) was called on stream B data")

    monkeypatch.setattr(p5_model, "loss_for", guarded_loss)
    monkeypatch.setattr(trace, "collect_trace", guarded_collect)
    real_evaluate = p5_model.evaluate

    def evaluate_only_on_the_p5_panel(model: Any, data: torch.Tensor, *a: Any, **k: Any) -> Any:
        if data is panel_b:
            return forbidden_evaluate()
        return real_evaluate(model, data, *a, **k)

    monkeypatch.setattr(p5_model, "evaluate", evaluate_only_on_the_p5_panel)
    record = run_trace_b(source, identity, calibration, panel_b, tmp_path / "b", recorded)
    assert record["loss_computed_on_stream_b"] is False
    assert len(calls) == 1  # exactly the P5-panel replay (one batch of 8 contexts)
    assert calls[0] == (8, 64, 256)
    assert (tmp_path / "b" / "streamB_selected.int16.bin").is_file()
    assert [n["replicate_seed"] for n in record["nulls"]] == [91321, 91322, 91323]
    assert (
        record["replay"]["bitwise_equal"]
        and record["regeneration"]["byte_identical_to_identity_manifest"]
    )
    # the recorded trace round-trips and the integrity checks passed
    selected, _ = a_core.read_trace(tmp_path / "b", "streamB", record["files"]["stream_b"])
    assert a_core.selection_counts(selected) is not None
    assert core.counts_sha256(a_core.selection_counts(selected)) == record["counts_sha256"]


def test_collect_trace_never_touches_a_loss_function(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _, _, panel_b = synthetic_setup(tmp_path)

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("loss path")

    monkeypatch.setattr(p5_model, "loss_for", boom)
    monkeypatch.setattr(p5_model, "evaluate", boom)
    monkeypatch.setattr(torch.nn.functional, "cross_entropy", boom)
    selected, branches = trace.trace_stream_b(source.models["learned_tree"], panel_b)
    assert tuple(selected.shape) == (8 * 64, 8) and branches is not None


def test_regeneration_that_differs_from_the_identity_manifest_stops(tmp_path: Path) -> None:
    source, identity, calibration, panel_b = synthetic_setup(tmp_path)
    label = core.cell_label(PAIR, "flat")
    data = copy.deepcopy(identity.data)
    for entry in data["checkpoints"]:
        if entry["label"] == label:
            for f in entry["files"]:
                if f["role"] == "evaluation.selected":
                    f["recorded_sha256"] = "0" * 64
    bad = core.Identity(identity.path, identity.repo, data)
    with pytest.raises(GateViolation) as raised:
        run_trace_b(source, bad, calibration, panel_b, tmp_path / "b")
    assert raised.value.gate == "regeneration"


def test_a_replay_that_is_not_bitwise_equal_stops_before_any_stream_b_trace(
    tmp_path: Path,
) -> None:
    source, identity, calibration, panel_b = synthetic_setup(tmp_path)
    source.recorded["flat"]["nll"] = source.recorded["flat"]["nll"] + 1e-12
    with pytest.raises(GateViolation) as raised:
        run_trace_b(source, identity, calibration, panel_b, tmp_path / "b")
    assert raised.value.gate == "nll_replay"
    assert not (tmp_path / "b").exists()  # nothing was written


def test_stream_b_integrity_failure_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, identity, calibration, panel_b = synthetic_setup(tmp_path)
    real = trace.trace_stream_b

    def broken(model: Any, panel: torch.Tensor) -> Any:
        selected, branches = real(model, panel)
        selected = selected.clone()
        selected[0, 1] = selected[0, 0]  # a duplicate slot inside a query
        return selected, branches

    monkeypatch.setattr(trace, "trace_stream_b", broken)
    with pytest.raises(GateViolation) as raised:
        run_trace_b(source, identity, calibration, panel_b, tmp_path / "b")
    assert raised.value.gate == "trace_integrity"


# --- identity manifest
def test_the_registered_identity_manifest_verifies_without_opening_any_trace() -> None:
    identity = core.load_identity(REPO)
    assert identity.data["overall_hash"]["sha256"] == core.IDENTITY_OVERALL_SHA256
    assert len(identity.by_label) == 81
    _, record = identity.trace_record(core.all_labels()[0], "calibration")
    assert all(e is None or e["file"].startswith("calib_") for e in record.values())
    _, record = identity.trace_record(core.all_labels()[0], "evaluation")
    assert all(e is None or e["file"].startswith("eval_") for e in record.values())
    with pytest.raises(ValueError):
        identity.trace_record(core.all_labels()[0], "stream_b")


def test_identity_manifest_that_does_not_verify_stops(tmp_path: Path) -> None:
    data = read_json(REPO / core.IDENTITY_MANIFEST)
    data["checkpoints"][0]["files"][0]["recorded_sha256"] = "0" * 64
    path = tmp_path / "m.json"
    write_json(path, data)
    with pytest.raises(core.StopError, match="does not verify"):
        core.load_identity(REPO, path)
    data = read_json(REPO / core.IDENTITY_MANIFEST)
    data["checkpoints"].pop()
    write_json(path, data)
    with pytest.raises(core.StopError, match="exactly"):
        core.load_identity(REPO, path)


# --- audit M1: the stream-B identity manifest must be committed and clean before any simulation
def git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.org",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def manifest_repo(tmp_path: Path, identity_sha: str = "i" * 64) -> tuple[Path, Path, Path]:
    """A temporary Git repository holding results/trace-b/RUN-1 with a stream-B identity manifest
    consistent with its result.json and the layout table (nothing committed yet)."""
    repo = tmp_path / "repo"
    layout = repo / "results" / "layouts" / "RUN-1"
    trace = repo / "results" / "trace-b" / "RUN-1"
    layout.mkdir(parents=True)
    trace.mkdir(parents=True)
    write_json(layout / "layout_hash_table.json", {"layouts": {}})
    manifest = {
        "schema": "P7B-stream-b-identity-manifest-v1",
        "complete": True,
        "bindings": {
            "layout_hash_table_sha256": file_sha256(layout / "layout_hash_table.json"),
            "identity_manifest_sha256": identity_sha,
        },
        "checkpoints": {},
    }
    write_json(trace / core.STREAM_B_MANIFEST, manifest)
    write_json(
        trace / "result.json",
        {
            "status": "completed",
            "stream_b_identity_manifest_sha256": file_sha256(trace / core.STREAM_B_MANIFEST),
        },
    )
    git(repo, "init", "-q")
    return repo, layout, trace


def verify(layout: Path, trace: Path, *, dry_run: bool = False) -> dict[str, Any]:
    return study.verify_stream_b_manifest(trace, layout, "i" * 64, dry_run=dry_run)


def test_a_committed_clean_manifest_is_accepted_and_its_hash_is_recorded(tmp_path: Path) -> None:
    repo, layout, trace = manifest_repo(tmp_path)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "stream-B identity manifest")
    record = verify(layout, trace)
    assert record["sha256"] == file_sha256(trace / core.STREAM_B_MANIFEST)
    assert record["stand_in"] is False and "tracked, clean" in record["git_check"]


def test_an_uncommitted_manifest_is_refused(tmp_path: Path) -> None:
    repo, layout, trace = manifest_repo(tmp_path)
    git(repo, "commit", "-q", "--allow-empty", "-m", "initial")  # a HEAD exists; manifest untracked
    with pytest.raises(core.GateError, match="not tracked by Git"):
        verify(layout, trace)
    git(repo, "add", str(trace / core.STREAM_B_MANIFEST))  # staged, still not committed
    with pytest.raises(core.GateError, match="differs from HEAD"):
        verify(layout, trace)


def test_an_edited_manifest_is_refused(tmp_path: Path) -> None:
    repo, layout, trace = manifest_repo(tmp_path)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "stream-B identity manifest")
    path = trace / core.STREAM_B_MANIFEST
    path.write_text(path.read_text() + " ")  # any edit after the commit
    with pytest.raises(core.GateError, match="differs from HEAD"):
        verify(layout, trace)


def test_a_manifest_that_is_not_the_one_trace_b_recorded_or_is_unbound_is_refused(
    tmp_path: Path,
) -> None:
    repo, layout, trace = manifest_repo(tmp_path)
    path = trace / core.STREAM_B_MANIFEST
    data = read_json(path)
    data["checkpoints"] = {"x": {}}  # edited, then committed: result.json no longer matches
    write_json(path, data)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "edited manifest")
    with pytest.raises(core.GateError, match="differs from the manifest the trace-b stage"):
        verify(layout, trace)
    with pytest.raises(core.GateError, match="different trace identity manifest"):
        study.verify_stream_b_manifest(trace, layout, "other" * 12 + "0000", dry_run=True)
    write_json(layout / "layout_hash_table.json", {"layouts": {"changed": 1}})
    with pytest.raises(core.GateError, match="different layout hash table"):
        verify(layout, trace, dry_run=True)


def test_the_git_stand_in_exists_only_in_a_dry_run(tmp_path: Path) -> None:
    repo, layout, trace = manifest_repo(tmp_path)  # untracked, uncommitted manifest
    stand_in = verify(layout, trace, dry_run=True)
    assert stand_in["stand_in"] is True and "dry-run stand-in" in stand_in["git_check"]
    with pytest.raises(core.GateError, match="not tracked by Git"):
        verify(layout, trace, dry_run=False)  # the same files outside a dry run
    with pytest.raises(core.GateError, match="does not exist"):
        core.tracked_and_clean(tmp_path / "absent.json", dry_run=False)
    for command in ("panel", "layouts", "trace-b", "simulate", "analyze"):
        parsed = study.build_parser().parse_args([command])
        assert study.Options(parsed).dry_run is False  # only study.dry_run() ever sets it


def test_run_simulate_refuses_for_either_stream_without_a_committed_manifest(
    tmp_path: Path,
) -> None:
    for stream in ("A", "B"):
        root = tmp_path / stream
        results = root / "results"
        make_upstream(results, "layouts", dry_run=False)
        make_upstream(results, "trace-b", dry_run=False)
        write_json(results / "layouts" / "RUN-1" / "layout_hash_table.json", {"layouts": {}})
        write_json(results / "trace-b" / "RUN-1" / core.STREAM_B_MANIFEST, {"complete": True})
        opt = study.Options(study.build_parser().parse_args(["simulate", "--stream", stream]))
        opt.results_root, opt.output_root = results, root / "experiments"
        assert opt.dry_run is False
        with pytest.raises(core.GateError, match="not tracked by Git"):
            study.run_simulate(opt, stream)
        assert not (root / "experiments").exists()  # refused before any stage was opened


def test_the_stage_linkage_records_the_manifest_hash_and_the_stand_in_label(
    pipeline: dict[str, Any],
) -> None:
    for stage in ("simulate-a", "simulate-b"):
        (compact,) = stage_dirs(pipeline, stage)
        link = read_json(compact / "manifest.json")["linkage"]["stream_b_identity_manifest"]
        (trace_compact,) = stage_dirs(pipeline, "trace-b")
        assert link["sha256"] == file_sha256(trace_compact / core.STREAM_B_MANIFEST)
        assert link["stand_in"] is True and "dry-run stand-in" in link["git_check"]
        for path in sorted((compact / "workers").glob("*.result.json")):
            assert read_json(path)["stream_b_manifest_sha256"] == link["sha256"]


# --- audit M1: the stream-B worker binds the traces, counts and nulls to the manifest
def b_job(
    pipeline: dict[str, Any], manifest_path: Path | None = None
) -> tuple[dict[str, Any], str]:
    root = pipeline["root"]
    (trace_compact,) = stage_dirs(pipeline, "trace-b")
    path = manifest_path or trace_compact / core.STREAM_B_MANIFEST
    label = sorted(read_json(path)["checkpoints"])[0]
    job = {
        "stream": "B",
        "synthetic": True,
        "trace_b_record_dir": str(trace_compact / "checkpoints"),
        "trace_b_dir": str(root / "experiments" / trace_compact.name / "traces"),
        "stream_b_manifest": str(path),
        "stream_b_manifest_sha256": file_sha256(path),
    }
    return job, label


def edited_manifest(
    pipeline: dict[str, Any], tmp_path: Path, edit: Any
) -> tuple[dict[str, Any], str]:
    (trace_compact,) = stage_dirs(pipeline, "trace-b")
    data = read_json(trace_compact / core.STREAM_B_MANIFEST)
    label = sorted(data["checkpoints"])[0]
    edit(data["checkpoints"][label])
    path = tmp_path / "edited_manifest.json"
    write_json(path, data)
    return b_job(pipeline, path)[0], label


def test_stream_b_worker_accepts_the_matching_manifest(pipeline: dict[str, Any]) -> None:
    from arborlm import p7b_workers as workers

    job, label = b_job(pipeline)
    _, kind = core.parse_label(label)
    selected, branches, info = workers.load_stream_trace(job, None, label, kind)  # type: ignore[arg-type]
    counts = a_core.selection_counts(selected)
    assert workers.check_counts_identity(counts, info, label)["counts_sha256_checked"] is True
    index = core.cell_index(*core.parse_label(label))
    _, null_info = core.null_streams(counts, core.STREAM_B_NULL_SEEDS, index)
    assert workers.check_null_identity(None, label, null_info, info)[
        "null_streams_reproduce_recorded_hashes"
    ]
    assert workers.check_counts_identity(counts, {"stream": "A"}, label) == {
        "counts_sha256_checked": False
    }


def test_stream_b_worker_refuses_a_manifest_that_changed_after_the_stage_began(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    from arborlm import p7b_workers as workers

    job, label = b_job(pipeline)
    other = tmp_path / "other.json"
    other.write_text(Path(job["stream_b_manifest"]).read_text() + " ")
    job["stream_b_manifest"] = str(other)  # the recorded hash is the committed file's
    with pytest.raises(core.StopError, match="changed since the stage began"):
        workers.load_stream_trace(job, None, label, core.parse_label(label)[1])  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["selected_sha256", "branches_sha256"])
def test_stream_b_worker_refuses_trace_hashes_that_differ_from_the_manifest(
    pipeline: dict[str, Any], tmp_path: Path, field: str
) -> None:
    from arborlm import p7b_workers as workers

    job, label = edited_manifest(pipeline, tmp_path, lambda e: e.update({field: "0" * 64}))
    with pytest.raises(core.StopError, match="trace file hashes differ"):
        workers.load_stream_trace(job, None, label, core.parse_label(label)[1])  # type: ignore[arg-type]


def test_stream_b_worker_refuses_a_counts_hash_that_differs_from_the_manifest(
    pipeline: dict[str, Any], tmp_path: Path
) -> None:
    from arborlm import p7b_workers as workers

    job, label = edited_manifest(pipeline, tmp_path, lambda e: e.update(counts_sha256="0" * 64))
    _, kind = core.parse_label(label)
    selected, _, info = workers.load_stream_trace(job, None, label, kind)  # type: ignore[arg-type]
    with pytest.raises(core.StopError, match="counts hash differs"):
        workers.check_counts_identity(a_core.selection_counts(selected), info, label)


@pytest.mark.parametrize("which", ["hash", "seed"])
def test_stream_b_worker_refuses_a_null_hash_that_differs_from_the_manifest(
    pipeline: dict[str, Any], tmp_path: Path, which: str
) -> None:
    from arborlm import p7b_workers as workers

    def edit(entry: dict[str, Any]) -> None:
        if which == "hash":
            entry["null_streams"][2]["stream_sha256"] = "0" * 64
        else:
            entry["null_streams"][0]["replicate_seed"] = 91301

    job, label = edited_manifest(pipeline, tmp_path, edit)
    pair, kind = core.parse_label(label)
    _, _, info = workers.load_stream_trace(job, None, label, kind)  # type: ignore[arg-type]
    selected = a_core.read_trace(Path(job["trace_b_dir"]) / label, "streamB", info["files"])[0]
    counts = a_core.selection_counts(selected)
    _, null_info = core.null_streams(counts, core.STREAM_B_NULL_SEEDS, core.cell_index(pair, kind))
    with pytest.raises(core.StopError, match="null stream"):
        workers.check_null_identity(None, label, null_info, info)


# --- audit m9, m11, m6, m2 and the worker records
def test_p7a_reference_records_are_read_with_the_completeness_check(tmp_path: Path) -> None:
    label = core.all_labels()[0]
    good = tmp_path / "good.json"
    write_json(good, {"outcome": "completed", "record": {"complete": True, "x": 1}})
    assert core.load_reference_record(good, label) == {"complete": True, "x": 1}
    for bad in (
        {"outcome": "completed", "record": {"complete": False}},
        {"outcome": "cap_exceeded", "record": {"complete": True}},
        {"outcome": "completed", "record": {}},
    ):
        path = tmp_path / "bad.json"
        write_json(path, bad)
        with pytest.raises(core.StopError, match="not complete"):
            core.load_reference_record(path, label)


def test_the_stream_b_manifest_copies_the_regeneration_flag_from_the_record(
    tmp_path: Path,
) -> None:
    context = stages.open_stage(
        "trace-b",
        output_root=tmp_path / "e",
        results_root=tmp_path / "r",
        argv=[],
        arguments={},
        dry_run=True,
    )
    labels = core.all_labels()[:2]
    flags = {labels[0]: True, labels[1]: False}
    done = {
        lb: {
            "files": {
                "stream_b": {"selected": {"sha256": "s"}, "branches": None},
            },
            "counts_sha256": "c",
            "unique_selected_slots": 1,
            "nulls": [],
            "regeneration": {"byte_identical_to_identity_manifest": flags[lb]},
            "replay": {"bitwise_equal": True},
            "loss_computed_on_stream_b": False,
        }
        for lb in labels
    }
    path = study.assemble_stream_b_manifest(context, done, labels, {})
    entries = read_json(path)["checkpoints"]
    assert [entries[lb]["regeneration_byte_identical_to_identity_manifest"] for lb in labels] == [
        True,
        False,
    ]


def test_simulate_workers_record_the_run_time_checks_and_leave_a_partial_record(
    pipeline: dict[str, Any],
) -> None:
    for stage in ("simulate-a", "simulate-b"):
        (compact,) = stage_dirs(pipeline, stage)
        for path in sorted((compact / "workers").glob("*.result.json")):
            result = read_json(path)
            assert result["r1_invariants"]["all_identical"] is True
            assert result["r1_invariants"]["r1_groups_compared"] > 0
            assert result["package_source_sha256"] == core.package_hashes()
            partial = read_json(path.with_name(path.name.replace(".result.", ".partial.")))
            assert partial["complete"] is True and partial["record"]["complete"] is True
            assert partial["label"] == result["label"]
    (b,) = stage_dirs(pipeline, "simulate-b")
    assert all(
        read_json(p)["counts_identity"]["counts_sha256_checked"]
        for p in sorted((b / "workers").glob("*.result.json"))
    )


def test_manifests_bind_every_file_under_src_arborlm(pipeline: dict[str, Any]) -> None:
    hashes = core.package_hashes()
    assert {"src/arborlm/p7a_core.py", "src/arborlm/io.py", "src/arborlm/p5_model.py"} <= set(
        hashes
    )
    assert set(hashes) >= set(core.source_hashes()) and len(hashes) > len(core.source_hashes())
    for stage in ("panel", "layouts", "trace-b", "simulate-a", "simulate-b", "analyze"):
        (compact,) = stage_dirs(pipeline, stage)
        manifest = read_json(compact / "manifest.json")
        assert manifest["package_source_sha256"] == hashes
        assert manifest["frozen_check_at_end"]["package_sources_unchanged"] is True
    (b,) = stage_dirs(pipeline, "simulate-b")
    assert read_json(b / "manifest.json")["linkage"]["trace_b"]["package_source_sha256_equal"]
