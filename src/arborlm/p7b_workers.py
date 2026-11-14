"""P7-B supervised worker bodies: ``layouts`` (one checkpoint), ``trace-b`` (one parent/seed pair)
and ``simulate`` (one checkpoint, one evaluation stream).

Workers are started by ``p7b_study`` as subprocesses (``python -m arborlm.p7b_study _worker ...``)
under the watchdog. Each reads a small JSON job file, records its own deterministic single-thread
configuration, writes ``result.json`` (and ``partial.json`` while running) into its run folder and
exits non-zero on a registered stop.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import resource
import sys
import time
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p6_common as common
from . import p7a_core as a_core
from . import p7b_core as core
from . import p7b_layout as layout_mod
from . import p7b_sim as sim
from .io import read_json, write_json
from .p6_common import Pair
from .records import record_environment


def peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def determinism() -> dict[str, Any]:
    """The worker's own deterministic single-thread setting (ADR-0014 section 11 and clarification
    on workers): recorded in every result."""
    return {
        "threads_intra_op": torch.get_num_threads(),
        "threads_inter_op": torch.get_num_interop_threads(),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "default_dtype": str(torch.get_default_dtype()),
        "device": "cpu",
        "single_thread": torch.get_num_threads() == 1,
    }


def start_worker(run_arg: str) -> tuple[Path, float]:
    """Common start: verify the watchdog manifest, set the registered CPU configuration, record the
    environment. Returns the run folder and the worker's start time."""
    from .p7a_trace import configure_deterministic_cpu

    run = Path(run_arg)
    running = read_json(run / "manifest.json")
    if running["status"] != "running" or running.get("experiment_family") != core.FAMILY:
        raise ValueError("missing P7-B watchdog record")
    if running.get("question_id") != core.STUDY:
        raise ValueError("worker manifest does not cite P7-B")
    configure_deterministic_cpu()
    record_environment(run, family=core.FAMILY)
    return run, time.monotonic()


def load_identity_for(job: dict[str, Any]) -> core.Identity:
    path = Path(job["identity"]) if job.get("identity") else None
    return core.load_identity(Path(job["repo"]), path, job.get("labels"))


# --------------------------------------------------------------------------------------------------
# layouts
# --------------------------------------------------------------------------------------------------
def calibration_transfer_runs(
    selected: Tensor, built: list[layout_mod.BuiltLayout], deadline: float | None = None
) -> dict[str, Any]:
    """The calibration stream itself simulated on every layout at every R and C (ascending rule):
    the calibration side of the calibration-to-evaluation transfer (section 6)."""
    out: dict[str, Any] = {}
    for layout in built:
        rows_list = core.RS if layout.rows is None else (layout.rows,)
        positions = sim.positions_tensor(layout.order)
        for rows in rows_list:
            if deadline is not None and time.monotonic() > deadline:
                raise sim.CapExceeded("layout-stage deadline passed during calibration transfer")
            key = core.layout_key(layout.name, rows)
            queries = sim.page_sets(positions, rows, selected)
            out[key] = sim.simulate_group(queries, core.CS, (), f"calibration|{key}")
    return out


def split_half_runs(cal: layout_mod.CalibrationTrace) -> dict[str, Any]:
    """Split-half stability (calibration only): each criterion layout fitted on one half of the
    calibration contexts and scored on the other half, both directions, at the two criterion
    settings (ascending rule). Scores are warm capacity misses per query on the scored half
    (first half of its contexts warms the cache, second half is counted)."""
    half = int(cal.selected.shape[0]) // 2
    streams = [cal.selected[:half], cal.selected[half:]]
    names = [core.L_FREQ, core.L_COAX, *core.L_PCOAX]
    if core.is_tree(cal.kind):
        names.append(core.L_BCOAX)
    out: dict[str, Any] = {}
    for rows, cap in core.CRITERION_SETTINGS:
        fitted = {h: layout_mod.split_half_layouts(cal, h, names, rows) for h in (0, 1)}
        for name in names:
            entry: dict[str, Any] = {}
            for h in (0, 1):
                scored = streams[1 - h]
                queries = sim.page_sets(sim.positions_tensor(fitted[h][name]), rows, scored)
                stats = sim.stream_stats(queries)
                counts = sim.cache_counts(queries, cap, stats)
                counted = len(queries) - len(queries) // 2
                capacity_misses = counts["misses_warm"] - counts["first_touch_warm"]
                entry[f"fit_half_{h}_score_half_{1 - h}"] = capacity_misses / counted
                entry[f"capacity_misses_fit_{h}"] = capacity_misses
                entry["counted_queries"] = counted
            out[f"{name}|R{rows}|C{cap}"] = entry
    return out


def layouts_worker(argv: list[str]) -> int:
    run_arg, job_arg = argv
    run, started = start_worker(run_arg)
    job = read_json(Path(job_arg))
    label = job["label"]
    pair, kind = core.parse_label(label)

    def write(outcome: str, **extra: Any) -> None:
        write_json(
            run / "result.json",
            {
                "schema": core.SCHEMA_LAYOUT,
                "outcome": outcome,
                "label": label,
                "kind": kind,
                "pair": list(pair),
                "cell_index": core.cell_index(pair, kind),
                "worker_seconds": time.monotonic() - started,
                "peak_rss_bytes_ru_maxrss": peak_rss_bytes(),
                "determinism": determinism(),
                "p7b_source_sha256": core.source_hashes(),
                **extra,
            },
        )

    try:
        limit = float(read_json(run / "manifest.json")["limits"]["process_seconds"])
        deadline = started + max(limit - 5.0, 1.0)
        partitions = layout_mod.verify_partitions()
        identity = load_identity_for(job)
        cal = layout_mod.CalibrationTrace.from_identity(identity, label)
        t_build = time.monotonic()
        built, meta = layout_mod.build_layouts(cal)
        build_seconds = time.monotonic() - t_build
        directory = Path(job["layout_dir"])
        file = directory / f"{label}.layouts.int16.bin"
        index = layout_mod.write_layout_file(file, built)
        table = layout_mod.hash_table(built)
        t_transfer = time.monotonic()
        transfer = calibration_transfer_runs(cal.selected, built, deadline)
        transfer_seconds = time.monotonic() - t_transfer
        t_split = time.monotonic()
        split = split_half_runs(cal)
        split_seconds = time.monotonic() - t_split
        write(
            "completed",
            partitions=partitions,
            identity_manifest_sha256=identity.file_sha256,
            calibration_files={
                "selected_sha256": identity.recorded_sha(label, "calibration.selected"),
                "branches_sha256": identity.recorded_sha(label, "calibration.branches"),
            },
            layout_file={
                "file": file.name,
                "bytes": file.stat().st_size,
                "sha256": layout_mod.layout_file_sha256(file),
                "format": "little-endian int16 x 4096 per entry: the slot at each position",
            },
            layout_index=index,
            hash_table=table,
            hash_method="ADR-0014 section 4 Exactness: SHA-256 of pages in page order, slot IDs "
            "sorted ascending in each page, little-endian 16-bit",
            meta=meta,
            calibration_transfer=transfer,
            split_half=split,
            seconds={
                "build": build_seconds,
                "calibration_transfer": transfer_seconds,
                "split_half": split_seconds,
            },
        )
    except sim.CapExceeded as exc:
        write("cap_exceeded", gate="resource_cap", message=str(exc))
        print(f"P7-B cap exceeded: {exc}", file=sys.stderr)
        return 1
    except (core.StopError, core.TraceIntegrityError, core.InvariantError, TypeError) as exc:
        write("gate_violation", gate=type(exc).__name__, message=str(exc))
        print(f"P7-B layouts stop: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write("error", error=f"{type(exc).__name__}: {exc}")
        raise
    return 0


# --------------------------------------------------------------------------------------------------
# trace-b
# --------------------------------------------------------------------------------------------------
def calibration_slice_real(train: Tensor) -> Tensor:
    """Training-pool ranks 2048-2559 of the frozen pool of 4,096 ranked chunks."""
    if train.shape[0] != 4096:
        raise ValueError("the frozen training pool does not hold 4,096 ranked chunks")
    return train[core.CAL_START : core.CAL_END]


def trace_b_worker(argv: list[str]) -> int:
    from .p5_model import evaluate
    from .p7a_trace import GateViolation
    from .p7b_panel import panel_tensor
    from .p7b_trace import trace_checkpoint_b

    run_arg, job_arg = argv
    run, started = start_worker(run_arg)
    job = read_json(Path(job_arg))
    pair: Pair = (int(job["pair"][0]), int(job["pair"][1]), int(job["pair"][2]))
    synthetic = bool(job["synthetic"])
    records: list[dict[str, Any]] = []

    def write(outcome: str, **extra: Any) -> None:
        write_json(
            run / "result.json",
            {
                "schema": core.SCHEMA_TRACE_B,
                "outcome": outcome,
                "pair": list(pair),
                "records": records,
                "worker_seconds": time.monotonic() - started,
                "peak_rss_bytes_ru_maxrss": peak_rss_bytes(),
                "determinism": determinism(),
                "p7b_source_sha256": core.source_hashes(),
                **extra,
            },
        )

    try:
        identity = load_identity_for(job)
        panel_record = read_json(Path(job["panel_record"]))
        panel_b = panel_tensor(Path(job["panel_bytes"]).read_bytes(), panel_record)
        contexts = int(job["contexts"])
        if synthetic:
            source = common.load_synthetic_cell(pair, rows=contexts)
            from .p7b_synth import synthetic_calibration

            calibration = synthetic_calibration(source.train, contexts)
        else:
            source = common.load_real_cell(
                pair,
                p5_suite=Path(job["parent_suite"]),
                output_root=Path(job["output_root"]),
                p5_results=Path(job["p5_results"]),
                data_dir=Path(job["data_dir"]),
                run=run,
            )
            calibration = calibration_slice_real(source.train)
        record_environment(run, family=core.FAMILY)  # replace P6's record with P7-B's
        for kind in core.KINDS:
            label = core.cell_label(pair, kind)
            if synthetic:
                recorded = evaluate(source.models[kind], source.panel, contexts * 64)["retrieval"]
            else:
                recorded = read_json(Path(job["p5_results"]) / label / "result.json")["final"][
                    "retrieval"
                ]
                if recorded is None:
                    raise ValueError(f"no recorded retrieval for {label}")
            t0 = time.monotonic()
            record = trace_checkpoint_b(
                source,
                kind,
                Path(job["traces_dir"]) / label,
                panel_b=panel_b,
                calibration=calibration,
                identity=identity,
                recorded_retrieval=recorded,
                panel_b_sha256=panel_record["panel_sha256"],
            )
            record["seconds"] = time.monotonic() - t0
            records.append(record)
        if not source.files_unchanged():
            raise GateViolation("checkpoint_hash", "a P5 snapshot file changed during the worker")
        write("completed")
    except GateViolation as exc:
        write("gate_violation", gate=exc.gate, message=exc.message, details=exc.details)
        print(f"P7-B trace-b gate violation: {exc}", file=sys.stderr)
        return 1
    except (core.StopError, core.TraceIntegrityError) as exc:
        write("gate_violation", gate=type(exc).__name__, message=str(exc))
        print(f"P7-B trace-b stop: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write("error", error=f"{type(exc).__name__}: {exc}")
        raise
    return 0


# --------------------------------------------------------------------------------------------------
# simulate
# --------------------------------------------------------------------------------------------------
def verify_layouts(
    label: str, orders: dict[str, list[int]], table: dict[str, dict[str, str]]
) -> dict[str, Any]:
    """Recompute the canonical hash of every layout the plan uses and compare it with the layout
    stage's record. Refuses (``StopError``) on any difference or any missing entry."""
    recorded = table[label]
    checked = 0
    for key, digest in recorded.items():
        name, _, rows = key.partition("|R")
        order = orders.get(key) if core.is_r_specific(name) else orders.get(name)
        if order is None:
            raise core.StopError(f"{label}: layout {key} is missing from the layout file")
        if core.canonical_hash(order, int(rows)) != digest:
            raise core.StopError(f"{label}: layout {key} canonical hash differs from the record")
        checked += 1
    needed = {core.layout_key(g.layout, g.rows) for g in sim.plan(core.parse_label(label)[1])}
    if not needed <= set(recorded):
        raise core.StopError(f"{label}: the layout stage did not record every layout the plan uses")
    return {"layouts_verified": checked}


def stream_b_manifest_entry(job: dict[str, Any], label: str) -> dict[str, Any]:
    """This checkpoint's entry of the committed stream-B identity manifest. The manifest file must
    still hash to what ``run_simulate`` recorded in the stage linkage."""
    from .io import file_sha256

    path = Path(job["stream_b_manifest"])
    if file_sha256(path) != job["stream_b_manifest_sha256"]:
        raise core.StopError(
            f"{label}: the stream-B identity manifest changed since the stage began"
        )
    manifest = read_json(path)
    entry = manifest["checkpoints"].get(label)
    if entry is None:
        raise core.StopError(f"{label}: absent from the stream-B identity manifest")
    result: dict[str, Any] = entry
    return result


def load_stream_trace(
    job: dict[str, Any], identity: core.Identity, label: str, kind: str
) -> tuple[Tensor, Tensor | None, dict[str, Any]]:
    """The evaluation trace of the stream, hash-verified, with its integrity check. For stream B
    the trace file hashes (selected, branches) are first compared with the committed stream-B
    identity manifest; ``read_trace`` then verifies the files against those hashes."""
    if job["stream"] == "A":
        directory, record = identity.trace_record(label, "evaluation")
        selected, branches = a_core.read_trace(directory, "eval", record)
        recorded = None
        if not job["synthetic"]:
            recorded = read_json(Path(job["p5_results"]) / label / "result.json")["final"][
                "retrieval"
            ]
        integrity = a_core.check_trace(
            selected, branches, kind, recorded=recorded, queries=int(selected.shape[0])
        )
        return selected, branches, {"stream": "A", "files": record, "integrity": integrity}
    trace = read_json(Path(job["trace_b_record_dir"]) / f"{label}.json")
    entry = stream_b_manifest_entry(job, label)
    directory = Path(job["trace_b_dir"]) / label
    record = trace["files"]["stream_b"]
    if (
        record["selected"]["sha256"] != entry["selected_sha256"]
        or (None if record["branches"] is None else record["branches"]["sha256"])
        != entry["branches_sha256"]
    ):
        raise core.StopError(
            f"{label}: the trace file hashes differ from the stream-B identity manifest"
        )
    from .p7b_trace import STREAM_B_PREFIX

    selected, branches = a_core.read_trace(directory, STREAM_B_PREFIX, record)
    integrity = a_core.check_trace(selected, branches, kind, queries=int(selected.shape[0]))
    return (
        selected,
        branches,
        {
            "stream": "B",
            "files": record,
            "integrity": integrity,
            "trace_record": trace,
            "manifest_entry": entry,
        },
    )


def check_counts_identity(counts: list[int], trace: dict[str, Any], label: str) -> dict[str, Any]:
    """Stream B only: the per-slot selection counts of the trace file must hash to the manifest's
    ``counts_sha256``."""
    if trace["stream"] != "B":
        return {"counts_sha256_checked": False}
    digest = core.counts_sha256(counts)
    if digest != trace["manifest_entry"]["counts_sha256"]:
        raise core.StopError(f"{label}: per-slot counts hash differs from the stream-B manifest")
    return {"counts_sha256_checked": True, "counts_sha256": digest}


def check_null_identity(
    reference: dict[str, Any] | None,
    label: str,
    info: list[dict[str, Any]],
    trace: dict[str, Any],
) -> dict[str, Any]:
    """Each regenerated null stream must reproduce the recorded hash: stream A against P7-A's
    ``stream_sha256`` (ADR-0014 section 3), stream B against the stream-B identity manifest (seed
    and hash)."""
    for i, detail in enumerate(info):
        if reference is not None:
            recorded = reference["frequency_matched"][a_core.STREAMS_FM[i]]["stream_sha256"]
        else:
            entry = trace["manifest_entry"]["null_streams"][i]
            if entry["replicate_seed"] != detail["replicate_seed"]:
                raise core.StopError(f"{label}: null stream {i + 1} seed differs from the manifest")
            recorded = entry["stream_sha256"]
        if detail["stream_sha256"] != recorded:
            raise core.StopError(
                f"{label}: null stream {i + 1} does not reproduce its recorded hash"
            )
    return {"null_streams_reproduce_recorded_hashes": True}


def simulate_worker(argv: list[str]) -> int:
    run_arg, job_arg = argv
    run, started = start_worker(run_arg)
    job = read_json(Path(job_arg))
    label, stream = job["label"], job["stream"]
    pair, kind = core.parse_label(label)
    index = core.cell_index(pair, kind)
    limit = float(read_json(run / "manifest.json")["limits"]["process_seconds"])
    deadline = started + max(limit - 5.0, 1.0)  # self-check first, so the partial is written
    source_before = core.source_hashes()
    package_before = core.package_hashes()

    def write(outcome: str, **extra: Any) -> None:
        write_json(
            run / "result.json",
            {
                "schema": core.SCHEMA_SIM,
                "outcome": outcome,
                "label": label,
                "kind": kind,
                "stream": stream,
                "pair": list(pair),
                "cell_index": index,
                "worker_seconds": time.monotonic() - started,
                "peak_rss_bytes_ru_maxrss": peak_rss_bytes(),
                "determinism": determinism(),
                **extra,
            },
        )

    def progress(info: dict[str, Any]) -> None:
        """Called after every finished layout: a watchdog kill leaves this partial record."""
        write_json(run / "partial.json", {"label": label, "stream": stream, **info})

    reproduction: dict[str, Any] | None = None
    held: dict[str, Any] = {}
    try:
        identity = load_identity_for(job)
        table = read_json(Path(job["hash_table"]))["layouts"]
        layout_record = read_json(Path(job["layout_worker_record"]))
        layout_file = Path(job["layout_dir"]) / layout_record["layout_file"]["file"]
        from .io import file_sha256

        if file_sha256(layout_file) != layout_record["layout_file"]["sha256"]:
            raise core.StopError(f"{label}: layout file differs from its recorded SHA-256")
        orders = layout_mod.read_layout_file(layout_file, layout_record["layout_index"])
        layouts_verified = verify_layouts(label, orders, table)
        selected, branches, trace_info = load_stream_trace(job, identity, label, kind)
        counts = a_core.selection_counts(selected)
        counts_identity = check_counts_identity(counts, trace_info, label)
        nulls, null_info = core.null_streams(
            counts,
            core.STREAM_A_NULL_SEEDS if stream == "A" else core.STREAM_B_NULL_SEEDS,
            index,
        )
        reference = (
            core.load_reference_record(Path(job["reference"]), label) if stream == "A" else None
        )
        null_identity = check_null_identity(reference, label, null_info, trace_info)

        def at_reproduction_point(record: dict[str, Any]) -> None:
            nonlocal reproduction
            held["record"] = record
            if reference is not None:
                reproduction = sim.check_reproduction(record, reference)

        trace = sim.EvaluationTrace(selected, branches, kind, label, stream)
        record = sim.simulate_checkpoint(
            trace=trace,
            layouts=sim.LayoutSet(orders),
            null_selected=dict(zip(core.STREAMS_NULL, nulls, strict=True)),
            deadline=deadline,
            progress=progress,
            checkpoint=at_reproduction_point,
        )
        held["record"] = record
        r1_invariants = sim.check_r1_invariants(record)  # ADR-0014 section 4, at run time
        if reference is not None and reproduction is None:
            reproduction = sim.check_reproduction(record, reference)
        if core.source_hashes() != source_before or core.package_hashes() != package_before:
            raise ValueError("a source file under src/arborlm changed during the worker")
        write(
            "completed",
            queries=int(selected.shape[0]),
            p7b_source_sha256=source_before,
            package_source_sha256=package_before,
            spec_sha256=core.spec_sha256(),
            stream_b_manifest_sha256=job.get("stream_b_manifest_sha256"),
            counts_identity=counts_identity,
            r1_invariants=r1_invariants,
            layout_binding={
                "layout_file_sha256": layout_record["layout_file"]["sha256"],
                "hash_table_sha256": file_sha256(Path(job["hash_table"])),
                **layouts_verified,
            },
            trace={"files": trace_info["files"], "integrity": trace_info["integrity"]},
            null_streams=[
                {k: d[k] for k in ("replicate_seed", "generator_seed", "stream_sha256")}
                for d in null_info
            ],
            null_identity=null_identity,
            reproduction_of_p7a=reproduction,
            record=record,
        )
    except sim.CapExceeded as exc:
        write(
            "cap_exceeded",
            gate="resource_cap",
            message=str(exc),
            partial=getattr(exc, "partial", None),
        )
        print(f"P7-B cap exceeded: {exc}", file=sys.stderr)
        return 1
    except (core.StopError, core.TraceIntegrityError, core.InvariantError) as exc:
        write(
            "gate_violation",
            gate=type(exc).__name__,
            message=str(exc),
            partial=held.get("record"),
        )
        print(f"P7-B simulate stop: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write("error", error=f"{type(exc).__name__}: {exc}")
        raise
    return 0
