"""Run ADR-0006 against the immutable local pilot checkpoints."""

from __future__ import annotations

import argparse
import math
import statistics
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from torch import Tensor

    from .pilot_model import PilotModel

from .io import canonical_json, file_sha256, read_json, sha256, write_json
from .pilot_config import FAMILY as PILOT_FAMILY
from .pilot_config import SEEDS, VAL_ROWS, pilot_config_hash, validate_pilot_config
from .pilot_config import SPEC as PILOT_SPEC
from .records import append_event, record_environment, record_source, runtime_supported
from .watchdog import POLL_SECONDS, RSS_BYTES, supervise

FAMILY = "P1_MEMORY_DIAGNOSTIC"
SPEC = "docs/decisions/ADR-0006-frozen-memory-diagnostic.md"
PARENT_ID = "P1-20261113T023302942989Z-acbad32bf88f40b3b60e1993e042d5d8"
PARENT_SUITE_COMMIT = "0b0555c86a8690122a2ba9d07f62235c4b1b384c"
PARENT_SOURCE_SHA256 = "ea8b852b9fbb616b73dcad7ed51fc1305a55f5d1756b938128d30798d3845c65"
REVIEW_RECORDS = "results/p1-2026-11-12"
CONDITIONS = ("original", "disabled", "values_permuted", "joint_within_branch")
VARIANT = "learned_tree"
CELL_SECONDS, SUITE_SECONDS = 60, 300
EXPECTED_TARGETS = VAL_ROWS * 64
JOINT_TOLERANCE = 1e-6
DEPENDENCE_THRESHOLD = 0.005


@dataclass(frozen=True)
class ParentCell:
    directory: Path
    checkpoint: Path
    config: dict[str, Any]
    identity: dict[str, Any]
    checkpoint_sha256: str
    index_sha256: str
    nll: float
    validation: bytes
    dataset: dict[str, Any]
    provenance: dict[str, Any]


def _update(run: Path, **fields: Any) -> None:
    manifest = read_json(run / "manifest.json")
    manifest.update(fields)
    write_json(run / "manifest.json", manifest)


def _fields(**extra: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_family": FAMILY,
        "question_id": FAMILY,
        "hypothesis": None,
        "hypothesis_null_reason": "exploratory frozen-checkpoint dependence diagnostic",
        "authorized_spec_reference": SPEC,
        "parent_spec_reference": PILOT_SPEC,
        "parent_pilot_suite_id": PARENT_ID,
        "reviewer_override": "human-authorized Codex reviewer per ADR-0003",
        **extra,
    }


def _prepare(run: Path) -> tuple[Path, dict[str, Any]]:
    config = {
        "schema_version": 1,
        "experiment_family": FAMILY,
        "spec": SPEC,
        "parent_spec": PILOT_SPEC,
        "parent_suite_id": PARENT_ID,
        "seed_order": list(SEEDS),
        "condition_order": list(CONDITIONS),
        "value_permutation_seed_offset": 9001,
        "joint_permutation_seed_offset": 10001,
        "cell_wall_seconds": CELL_SECONDS,
        "suite_wall_seconds": SUITE_SECONDS,
        "rss_bytes": RSS_BYTES,
        "poll_seconds": POLL_SECONDS,
        "validation_targets": EXPECTED_TARGETS,
        "joint_absolute_tolerance": JOINT_TOLERANCE,
        "joint_relative_tolerance": 0,
        "original_comparison": "bitwise",
        "dependence_threshold_nats_per_byte": DEPENDENCE_THRESHOLD,
    }
    write_json(run / "config.resolved.json", config)
    source = record_source(run, Path.cwd(), spec=SPEC)
    environment = record_environment(run, family=FAMILY)
    _update(
        run,
        code_commit=source["code_commit"],
        dirty=source["dirty"],
        source_sha256=source["archive"]["sha256"],
        lock_sha256=source["lock_sha256"],
        spec_sha256=source["spec_sha256"],
        diagnostic_config_sha256=sha256(canonical_json(config)),
        environment=environment,
        training=False,
        test_data_access=False,
    )
    runtime_supported()
    return Path(source["git_root"]), environment


def _same_environment(current: dict[str, Any], parent: dict[str, Any]) -> bool:
    fields = ("accelerator", "architecture", "cpu", "os", "python", "python_implementation")
    return all(current[key] == parent[key] for key in fields) and (
        current["packages"]["torch"] == parent["packages"]["torch"]
    )


def _verified_source(
    root: Path, original: Path, parent_manifest: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, str]:
    if snapshot["code_commit"] != parent_manifest["code_commit"]:
        raise ValueError("parent source manifest code commit mismatch")
    if parent_manifest["source_sha256"] != PARENT_SOURCE_SHA256:
        raise ValueError("wrong parent source archive identity")
    if file_sha256(original / "source.tar") != parent_manifest["source_sha256"]:
        raise ValueError("parent source archive hash mismatch")
    if snapshot["archive"]["sha256"] != parent_manifest["source_sha256"]:
        raise ValueError("parent source manifest archive hash mismatch")
    if snapshot["spec_sha256"] != parent_manifest["spec_sha256"]:
        raise ValueError("parent source manifest spec hash mismatch")
    files = snapshot["archive_file_sha256"]
    # Require all original package source files, plus dependency and registration inputs.
    if (
        not {
            "src/arborlm/pilot_model.py",
            "src/arborlm/model.py",
            "src/arborlm/engine.py",
            "src/arborlm/pilot_metrics.py",
            "src/arborlm/pilot_checkpoint.py",
            "src/arborlm/checkpoint.py",
            "src/arborlm/pilot_data.py",
            "src/arborlm/pilot_config.py",
            "uv.lock",
            PILOT_SPEC,
            "configs/p1_ram_screen.toml",
        }
        <= files.keys()
    ):
        raise ValueError("parent source record lacks required numerical inputs")
    selected = {
        name: digest
        for name, digest in files.items()
        if (
            name.startswith("src/arborlm/")
            or name
            in (
                "uv.lock",
                "pyproject.toml",
                PILOT_SPEC,
                "configs/p1_ram_screen.toml",
            )
        )
    }
    for name, digest in selected.items():
        if file_sha256(root / name) != digest:
            raise ValueError(f"parent source hash mismatch: {name}")
    return selected


def _parent(
    suite: Path,
    root: Path,
    seed: int,
    environment: dict[str, Any],
) -> ParentCell:
    from .pilot_data import load_frozen

    if suite.name != PARENT_ID or seed not in SEEDS:
        raise ValueError("only the registered local pilot suite and seeds are permitted")
    suite_manifest = read_json(suite / "manifest.json")
    if (
        suite_manifest["run_id"] != PARENT_ID
        or suite_manifest["code_commit"] != PARENT_SUITE_COMMIT
        or suite_manifest["status"] != "completed"
        or suite_manifest["experiment_family"] != PILOT_FAMILY
        or suite_manifest["authorized_spec_reference"] != PILOT_SPEC
    ):
        raise ValueError("wrong pilot suite manifest")
    reviewed = root / REVIEW_RECORDS / f"seed-{seed}" / VARIANT
    record = read_json(reviewed / "manifest.json")
    run_id = record["run_id"]
    if not isinstance(run_id, str) or Path(run_id).name != run_id:
        raise ValueError("invalid parent run ID")
    candidates = [
        cell
        for cell in read_json(suite / "cells.json")
        if cell["variant"] == VARIANT and cell["seed"] == seed
    ]
    if len(candidates) != 1 or (
        candidates[0]["run_id"] != run_id or candidates[0]["status"] != "completed"
    ):
        raise ValueError("unexpected parent pilot cell")
    directory = suite / "cells" / run_id
    for name in (
        "manifest.json",
        "result.json",
        "source.json",
        "config.resolved.json",
        "dataset_manifest.json",
        "checkpoint-256/index.json",
    ):
        if file_sha256(directory / name) != file_sha256(reviewed / name):
            raise ValueError(f"original and reviewed parent records differ: {name}")
    parent = read_json(directory / "manifest.json")
    if (
        parent["parent_run_id"] != PARENT_ID
        or parent["run_id"] != run_id
        or parent["seed"] != seed
        or parent["variant"] != VARIANT
        or parent["status"] != "completed"
        or parent["experiment_family"] != PILOT_FAMILY
        or parent["authorized_spec_reference"] != PILOT_SPEC
    ):
        raise ValueError("wrong parent checkpoint run")
    if not _same_environment(environment, parent["environment"]):
        raise ValueError("diagnostic numerical environment differs from the parent")
    for key in ("source_sha256", "config_sha256", "dataset_manifest_sha256", "spec_sha256"):
        if parent[key] != suite_manifest[key]:
            raise ValueError(f"original suite and cell differ: {key}")
    source = _verified_source(root, directory, parent, read_json(directory / "source.json"))
    spec_hash = file_sha256(root / PILOT_SPEC)
    config = validate_pilot_config(read_json(directory / "config.resolved.json"))
    config_hash = pilot_config_hash(config)
    if config_hash != parent["config_sha256"] or spec_hash != parent["spec_sha256"]:
        raise ValueError("parent config or spec identity mismatch")
    _, validation, dataset = load_frozen(suite / "frozen-data")
    dataset_hash = sha256(canonical_json(dataset))
    if dataset_hash != parent["dataset_manifest_sha256"] or dataset != read_json(
        directory / "dataset_manifest.json"
    ):
        raise ValueError("parent dataset manifest identity mismatch")
    result = read_json(directory / "result.json")
    if (
        result["outcome"] != "completed"
        or result["completed_steps"] != 256
        or result["final"]["target_tokens"] != EXPECTED_TARGETS
        or not math.isfinite(result["final"]["nll"])
    ):
        raise ValueError("wrong original validation result")
    checkpoint = directory / "checkpoint-256"
    index = read_json(checkpoint / "index.json")
    digest = file_sha256(checkpoint / "state.pt")
    if (
        digest != index["state_sha256"]
        or digest != result["checkpoint_state_sha256"]["checkpoint-256"]
    ):
        raise ValueError("original checkpoint hash mismatch")
    index_hash = file_sha256(checkpoint / "index.json")
    provenance = {
        "suite_run_id": PARENT_ID,
        "cell_run_id": run_id,
        "code_commit": parent["code_commit"],
        "suite_code_commit": PARENT_SUITE_COMMIT,
        "source_archive_sha256": parent["source_sha256"],
        "source_file_sha256": source,
        "pilot_spec_sha256": spec_hash,
        "pilot_config_sha256": config_hash,
        "dataset_manifest_sha256": dataset_hash,
        "validation_bytes_sha256": sha256(validation),
        "checkpoint_state_sha256": digest,
        "checkpoint_index_sha256": index_hash,
        "checkpoint_path": str(checkpoint),
        "pilot_final_nll": result["final"]["nll"],
        "reviewed_result_sha256": file_sha256(reviewed / "result.json"),
    }
    return ParentCell(
        directory,
        checkpoint,
        config,
        {
            "variant": VARIANT,
            "seed": seed,
            "config_sha256": config_hash,
            "spec_sha256": spec_hash,
            "dataset_manifest_sha256": dataset_hash,
        },
        digest,
        index_hash,
        float(result["final"]["nll"]),
        validation,
        dataset,
        provenance,
    )


def _permute(model: PilotModel, seed: int, condition: str) -> Tensor | None:
    import torch

    from .pilot_model import BRANCHES, PER_BRANCH, SLOTS

    if (
        condition not in CONDITIONS
        or seed not in SEEDS
        or model.variant != VARIANT
        or model.seed != seed
    ):
        raise ValueError("unregistered diagnostic intervention")
    memory = model.memory
    if memory is None:
        raise ValueError("original learned-tree memory module missing")
    if condition == "original":
        return None
    if condition == "disabled":
        # The model's unmodified forward already bypasses the additive module for None.
        model.memory = None
        return None
    generator = torch.Generator(device="cpu")
    with torch.no_grad():
        if condition == "values_permuted":
            perm = torch.randperm(SLOTS, generator=generator.manual_seed(9001 + seed), device="cpu")
        else:
            generator.manual_seed(10001 + seed)
            perm = torch.cat(
                [
                    branch * PER_BRANCH
                    + torch.randperm(PER_BRANCH, generator=generator, device="cpu")
                    for branch in range(BRANCHES)
                ]
            )
            memory.keys.copy_(memory.keys[perm])
        memory.values.copy_(memory.values[perm])
    return perm


def _invariance(condition: str, observed: float, original: float) -> bool:
    if condition == "original":
        return struct.pack("!d", observed) == struct.pack("!d", original)
    if condition == "joint_within_branch":
        return math.isclose(observed, original, abs_tol=JOINT_TOLERANCE, rel_tol=0)
    return True


def _cell(run: Path, suite: Path, seed: int, condition: str) -> None:
    import torch

    from .engine import configure_cpu, optimizer_for
    from .pilot_checkpoint import restore
    from .pilot_data import CHUNK_BYTES
    from .pilot_metrics import evaluate
    from .pilot_model import PilotModel

    if condition not in CONDITIONS:
        raise ValueError("unregistered diagnostic condition")
    root, environment = _prepare(run)
    parent = _parent(suite, root, seed, environment)
    write_json(run / "parent_provenance.json", parent.provenance)
    write_json(run / "parent_config.resolved.json", parent.config)
    write_json(run / "dataset_manifest.json", parent.dataset)
    _update(run, parent_run_id=parent.directory.name, parent_provenance=parent.provenance)

    configure_cpu()
    model = PilotModel(VARIANT, seed)
    optimizer = optimizer_for(model)
    if restore(parent.checkpoint, model, optimizer, parent.identity) != (256, 2048, 131072):
        raise ValueError("original final checkpoint counters differ")
    permutation = _permute(model, seed, condition)
    if permutation is not None:
        artifact = run / "permutation.json"
        ids = {
            "condition": condition,
            "pilot_seed": seed,
            "generator_seed": (9001 if condition == "values_permuted" else 10001) + seed,
            "direction": "new slot row i receives original row permutation_ids[i]",
            "permutation_ids": permutation.tolist(),
        }
        write_json(artifact, ids)
        _update(run, permutation_sha256=file_sha256(artifact))
    validation = torch.frombuffer(bytearray(parent.validation), dtype=torch.uint8).long()
    metrics = evaluate(model, validation.view(-1, CHUNK_BYTES))
    nll = metrics["nll"]
    unchanged = (
        file_sha256(parent.checkpoint / "state.pt") == parent.checkpoint_sha256
        and file_sha256(parent.checkpoint / "index.json") == parent.index_sha256
    )
    invariance = _invariance(condition, nll, parent.nll)
    passed = unchanged and invariance and metrics["target_tokens"] == EXPECTED_TARGETS
    result = {
        "outcome": "completed" if passed else "failed",
        "seed": seed,
        "condition": condition,
        "validation": metrics,
        "original_pilot_nll": parent.nll,
        "delta_from_original_pilot_nll": nll - parent.nll,
        "original_checkpoint_unchanged": unchanged,
        "invariance_check_passed": invariance
        if condition in ("original", "joint_within_branch")
        else None,
        "training_target_tokens": 0,
    }
    append_event(run, {"event": "diagnostic_evaluation", **result})
    write_json(run / "result.json", result)
    if not passed:
        raise ValueError("diagnostic correctness failure; inspect saved result")


def _cells() -> list[dict[str, Any]]:
    return [
        {"seed": seed, "condition": condition, "status": "unexecuted", "run_id": None}
        for seed in SEEDS
        for condition in CONDITIONS
    ]


def _summary(run: Path, reason: str | None = None) -> dict[str, Any]:
    path = run / "cells.json"
    cells = read_json(path) if path.exists() else _cells()
    complete = True
    for cell in cells:
        if cell["status"] == "running":
            cell.update(status="interrupted", reason=reason)
        elif cell["status"] == "unexecuted":
            cell["reason"] = reason
        complete &= cell["status"] == "completed"
    report: dict[str, Any] = {
        "outcome": "completed" if complete else "failed",
        "cells": cells,
        "reason": reason,
        "parent_promotion_gate": "failed_unchanged",
        "dependence_threshold_nats_per_byte": DEPENDENCE_THRESHOLD,
    }
    if complete:
        deltas = {
            condition: statistics.mean(
                cell["delta_nll"] for cell in cells if cell["condition"] == condition
            )
            for condition in CONDITIONS
        }
        report["mean_deltas_nats_per_byte"] = deltas
        report["threshold_met"] = {
            "memory_module": deltas["disabled"] >= DEPENDENCE_THRESHOLD,
            "slot_binding": deltas["values_permuted"] >= DEPENDENCE_THRESHOLD,
        }
    return report


def _suite(run: Path, suite: Path) -> None:
    cells = _cells()
    write_json(run / "cells.json", cells)
    try:
        root, environment = _prepare(run)
        parents = {seed: _parent(suite, root, seed, environment) for seed in SEEDS}
        write_json(
            run / "parent_provenance.json",
            {str(seed): parent.provenance for seed, parent in parents.items()},
        )
        write_json(run / "parent_config.resolved.json", parents[SEEDS[0]].config)
        write_json(run / "dataset_manifest.json", parents[SEEDS[0]].dataset)
        originals: dict[int, float] = {}
        for cell in cells:
            seed, condition = cell["seed"], cell["condition"]

            def worker(child: Path) -> list[str]:
                cell.update(run_id=child.name, status="running")
                write_json(run / "cells.json", cells)
                return [
                    sys.executable,
                    "-m",
                    "arborlm.diagnose_memory",
                    "_cell",
                    str(child),
                    str(suite),
                    str(seed),
                    condition,
                ]

            child, ok = supervise(
                run / "cells",
                "memory_diagnostic_cell",
                [],
                requested_argv=sys.argv,
                process_seconds=CELL_SECONDS,
                worker_argv=worker,
                run_prefix="P1DIAG",
                manifest_fields=_fields(
                    parent_diagnostic_run_id=run.name,
                    parent_run_id=parents[seed].directory.name,
                    seed=seed,
                    condition=condition,
                ),
            )
            terminal = read_json(child / "terminal.json")
            cell.update(status=terminal["status"], reason=terminal["reason"])
            if ok:
                result = read_json(child / "result.json")
                nll = result["validation"]["nll"]
                if condition == "original":
                    originals[seed] = nll
                cell.update(nll=nll, delta_nll=nll - originals[seed])
            write_json(run / "cells.json", cells)
            append_event(run, {"event": "cell_finished", **cell})
            if not ok:
                raise RuntimeError(f"{condition}/{seed} failed; see {child / 'terminal.json'}")
    except BaseException as exc:
        write_json(run / "result.json", _summary(run, str(exc)))
        raise
    write_json(run / "result.json", _summary(run))


def launch(suite: Path, output_root: Path) -> tuple[Path, bool]:
    suite, output_root = suite.resolve(), output_root.resolve()
    if output_root == suite or output_root.is_relative_to(suite):
        raise ValueError("diagnostic output root must be outside the original pilot suite")
    run, ok = supervise(
        output_root,
        "memory_diagnostic_suite",
        [],
        requested_argv=[sys.executable, "-m", "arborlm.diagnose_memory", *sys.argv[1:]],
        process_seconds=SUITE_SECONDS,
        worker_argv=lambda run: [
            sys.executable,
            "-m",
            "arborlm.diagnose_memory",
            "_suite",
            str(run),
            str(suite),
        ],
        manifest_fields=_fields(),
        run_prefix="P1DIAG",
        nested_workers=True,
    )
    if not ok and not (run / "result.json").exists():
        write_json(run / "result.json", _summary(run, read_json(run / "terminal.json")["reason"]))
    return run, ok


def main() -> int:
    if sys.argv[1:2] in (["_suite"], ["_cell"]):
        parser = argparse.ArgumentParser()
        parser.add_argument("worker", choices=("_suite", "_cell"))
        parser.add_argument("run", type=Path)
        parser.add_argument("suite", type=Path)
        parser.add_argument("seed", type=int, nargs="?")
        parser.add_argument("condition", choices=CONDITIONS, nargs="?")
        args = parser.parse_args()
        if args.run.resolve().is_relative_to(args.suite.resolve()):
            raise ValueError("worker output must be outside original suite")
        record = read_json(args.run / "manifest.json")
        if record["status"] != "running" or record["experiment_family"] != FAMILY:
            raise ValueError("missing diagnostic watchdog record")
        if args.worker == "_suite":
            _suite(args.run, args.suite)
        else:
            _cell(args.run, args.suite, args.seed, args.condition)
        return 0

    parser = argparse.ArgumentParser(description="Run the registered frozen-memory diagnostic")
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    run, ok = launch(args.suite, args.output_root)
    print(
        f"{'Recorded' if ok else 'Failed'} memory diagnostic: {run}",
        file=sys.stdout if ok else sys.stderr,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
