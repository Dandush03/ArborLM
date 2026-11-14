# ruff: noqa: E501
"""P8 stage "evaluate": panel NLLs, interventions, hard traces and utilization (ADR-0015 section 7.1).

Runs after all training; training never touches a panel. Per cell, for checkpoint steps 0 and 512:
NLL on Panel A and Panel B (``p5_model.evaluate`` semantics, 32,768 targets per panel). At step 512
also: memory-disabled NLL, values-permuted NLL (seed ``80000 + cell.index``; the permutation is
``p5_model.intervene``'s ``values_permuted`` with this seed), and the hard traces (selected slot IDs
``[32768, 8]``, branch IDs ``[32768, 2]`` for trees, first column = top branch) on the calibration
stream, Panel A and Panel B through the unchanged ``p7a_trace.collect_trace``. Every condition is run
on a model freshly restored from the checkpoint, so no intervention leaves a model modified.

Per cell the stage writes ``<eval_run>/cells/<label>/eval.json`` plus the trace files
(``p7a_core.write_trace``: little-endian int16/int8 binaries, SHA-256 in the record).

The stage refuses to run (outside ``--dry-run``) unless the frozen panel record is tracked and clean
in Git (``p7b_core.tracked_and_clean``) and, if ``--freeze-commit`` is given, identical to its content
at that commit, which must be an ancestor of ``HEAD``.

CLI::

    python -m arborlm.p8_eval evaluate --experiments-root E --data-dir D --train-run T \\
        --panel-record R [--panel-cache C] [--freeze-commit SHA] [--labels L ...]
    python -m arborlm.p8_eval evaluate --dry-run --out-root DIR [--cells N]

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p7a_core as a_core
from . import p7b_core as b_core
from . import p8_core as core
from . import p8_panel, p8_pool
from .io import file_sha256, read_json, write_json
from .p5_model import Model, backbone_digest, evaluate, state_digest
from .p7a_trace import collect_trace, configure_deterministic_cpu, synthetic_trace
from .records import allocate_run, utc_now

SCHEMA_EVAL = "P8-eval-v1"
SCHEMA_EVAL_STAGE = "P8-eval-stage-v1"
EVAL_STEPS = (0, 512)
PANELS = ("A", "B")
TRACE_NAMES = ("calibration", "A", "B")
TRACE_PREFIX = {"calibration": "calibration", "A": "panelA", "B": "panelB"}
EVAL_PREFIX, EVAL_PREFIX_DRY = "P8E", "P8ED"
CONDITIONS = ("enabled", "disabled", "values_permuted")


# --- utilization of one hard trace ---------------------------------------------------------------
def context_breadth(selected: Tensor) -> float:
    """Mean number of distinct slots selected within a 64-query context (ADR-0015 7.1, per-context
    breadth): exact, ``sum of per-context distinct counts / contexts``."""
    rows = selected.to(torch.int64)
    contexts = rows.shape[0] // core.CONTEXT
    if contexts * core.CONTEXT != rows.shape[0]:
        raise ValueError("a trace must hold whole 64-query contexts")
    block = rows.reshape(contexts, -1).sort(dim=1).values
    distinct = 1 + (block[:, 1:] != block[:, :-1]).sum(dim=1)
    return int(distinct.sum()) / contexts


def utilization(selected: Tensor, branches: Tensor | None) -> dict[str, Any]:
    """ADR-0015 section 7.1 utilization of a hard trace: distinct selected slots, entropy-effective
    slots ``N_eff = exp(H)`` of the selection counts, share of selections on the 64 most-selected
    slots; for trees the same three quantities for branches.

    Branch statistics count every visited branch (both columns, 2 per query). ``top_column_*`` gives
    the same for the first column only (the top branch of each query). The ADR names "distinct
    branches visited, entropy-effective branches, share of the top branch" without saying which; the
    visited-branch counts are the primary reading (see the report's ambiguity list)."""
    counts = torch.bincount(selected.to(torch.int64).flatten(), minlength=core.SLOTS).tolist()
    total = sum(counts)
    entropy = b_core.entropy_nats(counts)
    hot = sorted(counts, reverse=True)[: core.TOP_SLOTS_SHARE]
    out: dict[str, Any] = {
        "queries": int(selected.shape[0]),
        "selections": total,
        "distinct_slots": sum(1 for c in counts if c),
        "entropy_nats": entropy,
        "n_eff": math.exp(entropy),
        "hot64_share": sum(hot) / total,
        "context_breadth_mean": context_breadth(selected),
        "counts_sha256": b_core.counts_sha256(counts),
    }
    if branches is not None:
        flat = torch.bincount(branches.to(torch.int64).flatten(), minlength=core.BRANCHES).tolist()
        top = torch.bincount(branches[:, 0].to(torch.int64), minlength=core.BRANCHES).tolist()
        h_all, h_top = b_core.entropy_nats(flat), b_core.entropy_nats(top)
        out["branches"] = {
            "distinct_visited": sum(1 for c in flat if c),
            "entropy_nats": h_all,
            "n_eff": math.exp(h_all),
            "top_branch_share": max(flat) / sum(flat),
            "visit_counts": flat,
            "top_column_distinct": sum(1 for c in top if c),
            "top_column_n_eff": math.exp(h_top),
            "top_column_top_share": max(top) / sum(top),
            "top_column_counts": top,
        }
    return out


# --- interventions on a freshly restored model ------------------------------------------------------
def permute_values(model: Model, cell: core.Cell) -> dict[str, Any]:
    """``p5_model.intervene``'s ``values_permuted`` with seed ``80000 + cell.index`` (ADR-0015 7.1)."""
    memory: Any = model.addition
    if memory is None or not hasattr(memory, "values"):
        raise ValueError("values permutation requires a memory addition")
    seed = core.PERMUTE_SEED_OFFSET + cell.index
    generator = torch.Generator(device="cpu").manual_seed(seed)
    ids = torch.randperm(core.SLOTS, generator=generator, device="cpu")
    with torch.no_grad():
        memory.values.copy_(memory.values[ids])
    return {"seed": seed, "permutation_sha256": b_core.tensor_sha256_int16(ids)}


class ModelSource:
    """Hands out freshly restored models of one cell. ``restore`` is the unchanged P8 checkpoint
    restore (identity, file, backbone, optimizer and state-digest checks)."""

    def __init__(self, cell: core.Cell, cell_dir: Path, backbone: Any) -> None:
        self.cell, self.cell_dir, self.backbone = cell, cell_dir, backbone
        self.files: dict[int, dict[str, Any]] = {}

    def load(self, step: int) -> Model:
        from .p8_checkpoint import restore, step_path

        path = step_path(self.cell_dir, step)
        model, _, meta = restore(path, self.cell, self.backbone)
        self.files[step] = {
            "file": path.name,
            "file_sha256": meta["file_sha256"],
            "state_digest": meta["state_digest"],
        }
        return model


# --- one cell ------------------------------------------------------------------------------------
def evaluate_cell(
    cell: core.Cell,
    source: ModelSource,
    panels: dict[str, Tensor],
    calibration: Tensor,
    out_dir: Path,
    *,
    dry_run_traces: dict[str, tuple[Tensor, Tensor | None]] | None = None,
    backbone_expected: str | None = None,
) -> dict[str, Any]:
    """All measurements of one cell. ``dry_run_traces`` (dry run only) replaces the model-derived
    traces after they were collected and timed, to give downstream stages concentrated traces."""
    started = time.monotonic()
    seconds: dict[str, float] = {}
    record: dict[str, Any] = {
        "schema": SCHEMA_EVAL,
        "label": cell.label,
        "cell": cell.fields(),
        "cell_index": cell.index,
        "variant": cell.variant,
        "case": cell.case,
        "nll": {},
        "traces": {},
    }
    nll: dict[str, dict[str, dict[str, float]]] = {}

    def timed(name: str, begin: float) -> None:
        seconds[name] = time.monotonic() - begin

    # step 0
    t0 = time.monotonic()
    model = source.load(0)
    digest_step0 = backbone_digest(model.backbone)
    state0 = state_digest(model)
    nll["step0"] = {
        "enabled": {p: evaluate(model, panels[p], 32768)["nll"] for p in PANELS},
    }
    if state_digest(model) != state0:
        raise ValueError(f"{cell.label}: step-0 model changed during evaluation")
    timed("step0", t0)

    # step 512, enabled: NLL, then the three traces
    t0 = time.monotonic()
    model = source.load(512)
    digest_step512 = backbone_digest(model.backbone)
    state_before = state_digest(model)
    enabled: dict[str, float] = {}
    retrieval_unique: dict[str, int] = {}
    for p in PANELS:
        result = evaluate(model, panels[p], 32768)
        enabled[p] = result["nll"]
        retrieval_unique[p] = int(result["retrieval"]["unique_selected_slots"])
    nll["step512"] = {"enabled": enabled}
    timed("step512_enabled", t0)

    t0 = time.monotonic()
    streams = {"calibration": calibration, "A": panels["A"], "B": panels["B"]}
    for name in TRACE_NAMES:
        selected, branches = collect_trace(model, streams[name])
        a_core.check_trace(selected, branches, cell.variant, queries=core.EVAL_QUERIES)
        if (
            name in PANELS
            and int((torch.bincount(selected.flatten(), minlength=core.SLOTS) > 0).sum())
            != (retrieval_unique[name])
        ):
            raise ValueError(
                f"{cell.label}: trace {name} disagrees with evaluate() on distinct slots"
            )
        substitute = dry_run_traces.get(name) if dry_run_traces else None
        if substitute is not None:
            selected, branches = substitute
            a_core.check_trace(selected, branches, cell.variant, queries=core.EVAL_QUERIES)
        files = a_core.write_trace(
            out_dir, TRACE_PREFIX[name], selected, branches, core.EVAL_QUERIES
        )
        record["traces"][name] = {
            "prefix": TRACE_PREFIX[name],
            "files": files,
            "utilization": utilization(selected, branches),
            "synthetic_substitute": substitute is not None,
        }
    if state_digest(model) != state_before:
        raise ValueError(f"{cell.label}: step-512 model changed during evaluation or tracing")
    timed("step512_traces", t0)

    # step 512, interventions: each on its own freshly restored model
    t0 = time.monotonic()
    model = source.load(512)
    model.bypass = True
    nll["step512"]["disabled"] = {p: evaluate(model, panels[p], 32768)["nll"] for p in PANELS}
    model = source.load(512)
    permutation = permute_values(model, cell)
    nll["step512"]["values_permuted"] = {
        p: evaluate(model, panels[p], 32768)["nll"] for p in PANELS
    }
    timed("step512_interventions", t0)

    check = source.load(512)
    unchanged = state_digest(check) == state_before
    record["nll"] = nll
    record["intervention"] = {"values_permuted": permutation, "disabled": "model.bypass = True"}
    record["digests"] = {
        "backbone_step0": digest_step0,
        "backbone_step512": digest_step512,
        "backbone_expected": backbone_expected,
        "backbone_unchanged": digest_step0 == digest_step512
        and (backbone_expected is None or digest_step512 == backbone_expected),
        "state_step0": state0,
        "state_step512": state_before,
        "fresh_restore_equals_evaluated_state": unchanged,
    }
    if not record["digests"]["backbone_unchanged"] or not unchanged:
        raise ValueError(f"{cell.label}: backbone digest changed or restore is not reproducible")
    record["checkpoint_files"] = {str(k): v for k, v in sorted(source.files.items())}
    record["seconds"] = {**seconds, "total": time.monotonic() - started}
    return record


# --- worker --------------------------------------------------------------------------------------
def make_synthetic_checkpoints(cell: core.Cell, directory: Path) -> Any:
    """Dry run only: random-init checkpoints at steps 0 and 512 on a random full-size backbone, written
    with the real P8 checkpoint writer (no training). Returns the backbone."""
    from .p5_model import optimizer_for
    from .p8_checkpoint import save, step_path

    backbone = core.synthetic_backbone(cell)
    model = core.build_model(cell, backbone)
    optimizer = optimizer_for(model)
    identity = {
        "cell": cell.fields(),
        "backbone_sha256": backbone_digest(model.backbone),
        "source_sha256": "dry-run",
        "spec_sha256": "dry-run",
        "config_sha256": "dry-run",
    }
    save(step_path(directory, 0), model, optimizer, 0, identity)
    generator = torch.Generator().manual_seed(7000 + cell.index)
    with torch.no_grad():
        assert model.addition is not None
        for parameter in model.addition.parameters():
            parameter.add_(0.05 * torch.randn(parameter.shape, generator=generator))
    save(step_path(directory, 512), model, optimizer, 512, identity)
    return backbone


def synthetic_panels(seed: int) -> tuple[dict[str, Tensor], Tensor]:
    generator = torch.Generator().manual_seed(seed)
    data = [torch.randint(0, 256, (512, 65), generator=generator) for _ in range(3)]
    return {"A": data[0], "B": data[1]}, data[2]


def worker_main(job_path: Path) -> int:
    job = read_json(job_path)
    configure_deterministic_cpu()
    cell = core.parse_label(job["label"])
    out_dir = Path(job["cell_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    dry = bool(job["dry_run"])
    if dry:
        backbone = make_synthetic_checkpoints(cell, out_dir / "synthetic_checkpoints")
        source = ModelSource(cell, out_dir / "synthetic_checkpoints", backbone)
        panels, calibration = synthetic_panels(5000 + cell.index)
        traces = {
            name: synthetic_trace(
                cell.variant, 9000 + 3 * cell.index + k, queries=core.EVAL_QUERIES
            )
            for k, name in enumerate(TRACE_NAMES)
        }
        expected = None
        train_json = None
    else:
        experiments_root = Path(job["experiments_root"])
        backbone, provenance = core.load_backbone(cell, experiments_root)
        train_cell_dir = Path(job["train_run"]) / "cells" / cell.label
        source = ModelSource(cell, train_cell_dir, backbone)
        record_path = Path(job["panel_record"])
        if file_sha256(record_path) != job["panel_record_sha256"]:
            raise b_core.GateError("the panel record changed after the stage gated it")
        panel_record = read_json(record_path)
        a, b = p8_panel.panel_tensors(
            Path(job["data_dir"]),
            panel_record,
            cache_dir=Path(job["panel_cache"]) if job.get("panel_cache") else None,
        )
        panels = {"A": a, "B": b}
        calibration = p8_panel.calibration_tensor(Path(job["data_dir"]), panel_record)
        traces = None
        expected = provenance["backbone_sha256"]
        train_json = train_cell_dir / "train.json"
    record = evaluate_cell(
        cell,
        source,
        panels,
        calibration,
        out_dir,
        dry_run_traces=traces,
        backbone_expected=expected,
    )
    record.update(
        {
            "outcome": "completed",
            "dry_run": dry,
            "panel_record_sha256": job.get("panel_record_sha256"),
            "train_json_sha256": (
                file_sha256(train_json) if train_json is not None and train_json.is_file() else None
            ),
            "source_sha256": core.source_digest(),
            "spec_sha256": core.spec_sha256(),
            "determinism": p8_pool.determinism(),
            "worker_seconds": time.monotonic() - started,
            "peak_rss_bytes_ru_maxrss": p8_pool.peak_rss_bytes(),
        }
    )
    write_json(out_dir / "eval.json", record)
    return 0


# --- stage ---------------------------------------------------------------------------------------
def git_gate(record_path: Path, freeze_commit: str | None) -> dict[str, Any]:
    """The panel record must be tracked and clean (``p7b_core.tracked_and_clean``); with a freeze
    commit it must also equal its content at that commit and the commit must be an ancestor of HEAD.
    The freeze commit is required (a registered run never proceeds without one)."""
    if not freeze_commit:
        raise b_core.GateError("refused: a registered evaluation requires --freeze-commit")
    gate = b_core.tracked_and_clean(record_path, dry_run=False)
    cwd, name = record_path.resolve().parent, record_path.name

    def git(*args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)

    if git("merge-base", "--is-ancestor", freeze_commit, "HEAD").returncode != 0:
        raise b_core.GateError(f"refused: freeze commit {freeze_commit} is not an ancestor of HEAD")
    if git("diff", "--quiet", freeze_commit, "--", name).returncode != 0:
        raise b_core.GateError(
            f"refused: {record_path} differs from its content at {freeze_commit}"
        )
    return {**gate, "freeze_commit": freeze_commit, "equal_to_freeze_content": True}


def run_stage(
    labels: list[str],
    *,
    out_root: Path,
    dry_run: bool,
    experiments_root: Path | None = None,
    data_dir: Path | None = None,
    train_run: Path | None = None,
    panel_record: Path | None = None,
    panel_cache: Path | None = None,
    freeze_commit: str | None = None,
    workers: int = core.WORKERS,
    cap_seconds: float = core.EVAL_CAP,
) -> Path:
    gate: dict[str, Any]
    freeze = p8_pool.require_freeze(dry_run, freeze_commit)
    if dry_run:
        gate = b_core.tracked_and_clean(Path("dry-run"), dry_run=True)
    else:
        if None in (experiments_root, data_dir, train_run, panel_record):
            raise ValueError(
                "a registered evaluation needs experiments-root, data-dir, train-run, panel-record"
            )
        assert panel_record is not None
        gate = git_gate(panel_record, freeze_commit)
    run = allocate_run(out_root, prefix=EVAL_PREFIX_DRY if dry_run else EVAL_PREFIX)
    jobs: list[p8_pool.Job] = []
    for label in labels:
        cell_dir = run / "cells" / label
        cell_dir.mkdir(parents=True)
        job = {
            "label": label,
            "cell_dir": str(cell_dir),
            "dry_run": dry_run,
            "experiments_root": str(experiments_root) if experiments_root else None,
            "data_dir": str(data_dir) if data_dir else None,
            "train_run": str(train_run) if train_run else None,
            "panel_record": str(panel_record) if panel_record else None,
            "panel_record_sha256": file_sha256(panel_record) if panel_record else None,
            "panel_cache": str(panel_cache) if panel_cache else None,
        }
        write_json(cell_dir / "job.json", job)
        jobs.append(
            p8_pool.Job(
                label,
                [sys.executable, "-m", "arborlm.p8_eval", "_worker", str(cell_dir / "job.json")],
                cell_dir / "eval.json",
                cell_dir / "eval.failed.json",
                cell_dir / "worker.log",
            )
        )
    stage_started = utc_now()
    result = p8_pool.run_pool(jobs, workers=workers, cap_seconds=cap_seconds)
    manifest = {
        "schema": SCHEMA_EVAL_STAGE,
        "family": core.FAMILY,
        "dry_run": dry_run,
        "spec_sha256": core.spec_sha256(),
        "source_sha256": core.source_digest(),
        "git_gate": gate,
        "freeze": freeze,
        "panel_record_sha256": file_sha256(panel_record) if panel_record else None,
        "train_run": str(train_run) if train_run else None,
        "labels": labels,
        "cells_expected": len(labels),
        "cells_completed": sum(1 for o in result.outcomes if o.status == "completed"),
        "outcomes": [o.__dict__ for o in result.outcomes],
        "started_utc": stage_started,
        "finished_utc": utc_now(),
        "wall_seconds": result.wall_seconds,
        "cap_seconds": cap_seconds,
        "cap_hit": result.cap_hit,
        "workers": workers,
        "peak_aggregate_rss_bytes": result.peak_aggregate_rss_bytes,
        "peak_worker_rss_bytes": max((o.peak_rss_bytes for o in result.outcomes), default=0),
        "status": "completed"
        if result.all_completed and len(result.outcomes) == len(labels)
        else "INCOMPLETE",
    }
    write_json(run / "manifest.json", manifest)
    return run


def main(argv: list[str] | None = None) -> int:
    args_in = sys.argv[1:] if argv is None else argv
    if args_in and args_in[0] == "_worker":
        return worker_main(Path(args_in[1]))
    parser = argparse.ArgumentParser(prog="python -m arborlm.p8_eval")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("evaluate")
    p.add_argument("--experiments-root", type=Path)
    p.add_argument("--data-dir", type=Path)
    p.add_argument("--train-run", type=Path)
    p.add_argument("--panel-record", type=Path)
    p.add_argument("--panel-cache", type=Path)
    p.add_argument("--freeze-commit")
    p.add_argument("--out-root", type=Path)
    p.add_argument("--labels", nargs="*")
    p.add_argument("--cells", type=int, default=60, help="dry run: first N cells")
    p.add_argument("--workers", type=int, default=core.WORKERS)
    p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(args_in)
    labels = args.labels or core.all_labels()[: args.cells if args.dry_run else 60]
    out_root = args.out_root or args.experiments_root
    if out_root is None:
        p.error("--out-root or --experiments-root is required")
    try:
        run = run_stage(
            labels,
            out_root=out_root,
            dry_run=args.dry_run,
            experiments_root=args.experiments_root,
            data_dir=args.data_dir,
            train_run=args.train_run,
            panel_record=args.panel_record,
            panel_cache=args.panel_cache,
            freeze_commit=args.freeze_commit,
            workers=args.workers,
        )
    except b_core.GateError as exc:
        print(f"P8 evaluate REFUSED: {exc}", file=sys.stderr)
        return 2
    manifest = read_json(run / "manifest.json")
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in (
                    "status",
                    "cells_completed",
                    "cells_expected",
                    "wall_seconds",
                    "peak_worker_rss_bytes",
                    "peak_aggregate_rss_bytes",
                )
            },
            indent=2,
        )
    )
    print(f"run directory: {run}")
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
