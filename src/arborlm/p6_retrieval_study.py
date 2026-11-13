"""P6-E command line: equivalence, screen, confirm, analyze (ADR-0011 Part E).

    uv run --locked --extra pilot python -m arborlm.p6_retrieval_study \
        {equivalence|screen|confirm|analyze} --data-dir data/wikitext2 \
        --parent-suite experiments/P5HIER-... --output-root experiments \
        --results-root results/p6-e-2026-11-13

Each stage gets a fresh run ID and refuses to overwrite. ``screen`` requires a completed
``equivalence`` and ``confirm`` a completed ``screen``. ``dry-run`` runs every stage on a tiny
synthetic fixture with reduced repetition counts and is labelled as not registered evidence.

``loader-smoke`` loads one real parent/seed (flat, fixed and learned finals) through the real
loading path only and replays the unmodified model's recorded P5 NLL bitwise. It computes no
variant, no equivalence comparison and no timing, and writes nothing under ``results/`` or
``experiments/``; it reports wall time and peak RSS.

A registered stage runs once: a second non-dry-run run of a stage is refused unless
``--supersede <run-id> --reason <text>`` names the earlier run, and the reason is recorded in the
new stage's manifest.

Importing this module executes nothing. Status: SPEC: HUMAN-APPROVED (ADR-0011); implementation
self-checked only, not independently audited, not Astra validated.
"""

import argparse
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .io import canonical_json, file_sha256, read_json, write_json
from .p6_common import P5_RESULTS, StudyArgs


def _common(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--data-dir", type=Path, required=required, default=Path("data/wikitext2"))
    parser.add_argument("--parent-suite", type=Path, required=required, default=Path("."))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--p5-results", type=Path, default=P5_RESULTS)
    parser.add_argument("--equivalence-run", default=None, help="compact run ID to consume")
    parser.add_argument("--screen-run", default=None, help="compact run ID to consume")
    parser.add_argument("--confirm-run", default=None, help="compact run ID to analyse")
    parser.add_argument(
        "--supersede", default=None, help="earlier run ID of this stage that this run supersedes"
    )
    parser.add_argument("--reason", default=None, help="recorded reason for --supersede")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m arborlm.p6_retrieval_study")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("equivalence", "screen", "confirm", "analyze"):
        _common(sub.add_parser(name), required=True)
    dry = sub.add_parser("dry-run", help="all stages on a synthetic fixture (not evidence)")
    _common(dry, required=False)
    dry.add_argument("--pair-count", type=int, default=2)
    dry.add_argument("--rounds", type=int, default=1)
    dry.add_argument("--panel-rows", type=int, default=16)
    smoke = sub.add_parser(
        "loader-smoke", help="real loading path and unmodified replay for one pair; nothing else"
    )
    smoke.add_argument("--data-dir", type=Path, default=Path("data/wikitext2"))
    smoke.add_argument("--parent-suite", type=Path, required=True)
    smoke.add_argument("--output-root", type=Path, default=Path("experiments"))
    smoke.add_argument("--p5-results", type=Path, default=P5_RESULTS)
    smoke.add_argument("--pair", type=int, nargs=3, required=True, metavar=("B", "O", "SEED"))
    worker = sub.add_parser("_worker")
    worker.add_argument("spec", type=Path)
    worker.add_argument("child", type=Path)
    worker.add_argument("pair", type=int, nargs=3)
    return parser


def _args(ns: argparse.Namespace, *, synthetic: bool = False) -> StudyArgs:
    return StudyArgs(
        data_dir=ns.data_dir,
        parent_suite=ns.parent_suite,
        output_root=ns.output_root,
        results_root=ns.results_root,
        p5_results=ns.p5_results,
        synthetic=synthetic,
        pair_count=getattr(ns, "pair_count", 27),
        rounds=getattr(ns, "rounds", 8),
        panel_rows=getattr(ns, "panel_rows", 16),
        equivalence_run=ns.equivalence_run,
        screen_run=ns.screen_run,
        confirm_run=ns.confirm_run,
        supersede=ns.supersede,
        supersede_reason=ns.reason,
    )


def _worker(spec_path: Path, child: Path, pair: tuple[int, int, int]) -> int:
    from .io import write_json as _write

    spec = read_json(spec_path)
    try:
        if spec["mode"] == "equivalence":
            from .p6_equivalence import equivalence_worker

            equivalence_worker(spec, child, pair)
        else:
            from .p6_timing_study import timing_worker

            timing_worker(spec, child, pair)
    except Exception as exc:
        if not (child / "result.json").exists():
            _write(
                child / "result.json",
                {"outcome": "failed", "error": f"{type(exc).__name__}: {exc}"},
            )
        raise
    return 0


def analyze_stage(args: StudyArgs, argv: list[str]) -> int:
    """Compute every section 3.6 criterion from the raw stage records."""
    from .p6_analysis import analyze, confirm_entities, descriptive_tables
    from .p6_equivalence import gate, load_cells
    from .p6_stage import finish_stage, open_stage, require_completed

    context = open_stage(
        "analysis",
        output_root=args.output_root,
        results_root=args.results_root,
        argv=argv,
        arguments=args.to_json(),
        dry_run=args.dry_run,
        supersede=args.supersede,
        supersede_reason=args.supersede_reason,
    )
    status, reason = "completed", None
    result: dict[str, Any] = {"stage": "analysis"}
    try:
        eq_dir = require_completed(
            args.results_root, "equivalence", args.equivalence_run, dry_run=args.dry_run
        )
        cells = load_cells(eq_dir)
        gated = gate(cells, expected_cells=len(args.pair_list()))
        result["inputs"] = {
            "equivalence_run": eq_dir.name,
            "equivalence_result_sha256": file_sha256(eq_dir / "result.json"),
        }
        selection = None
        confirm_workers: list[dict[str, Any]] = []
        screen_workers: list[dict[str, Any]] = []
        if gated and any(gated.get(v, {}).get("EQ") for v in ("T1", "T2", "T3", "T4", "T5")):
            screen_dir = require_completed(
                args.results_root, "screen", args.screen_run, dry_run=args.dry_run
            )
            selection = read_json(screen_dir / "selection.json")
            screen_workers = _worker_results(screen_dir)
            confirm_dir = require_completed(
                args.results_root, "confirm", args.confirm_run, dry_run=args.dry_run
            )
            confirm_workers = _worker_results(confirm_dir)
            check_linkage(
                eq_dir,
                screen_dir,
                confirm_dir,
                selection,
                screen_workers,
                confirm_workers,
                dry_run=args.dry_run,
            )
            result["inputs"].update(
                screen_run=screen_dir.name,
                selection_sha256=file_sha256(screen_dir / "selection.json"),
                confirm_run=confirm_dir.name,
            )
        report = analyze(gated, selection, confirm_workers, expected_pairs=len(args.pair_list()))
        result["analysis"] = report
        if selection is not None:
            result["screen_descriptive"] = descriptive_tables(
                screen_workers, _screen_plan(screen_workers)
            )
            result["confirm_descriptive"] = descriptive_tables(
                confirm_workers, confirm_entities(selection)
            )
        write_json(context.run / "analysis.json", result)
    except Exception as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
    finish_stage(context, status, reason, result)
    print(
        canonical_json(
            {"stage": "analysis", "run": context.run.name, "status": status, "reason": reason}
        )
        .decode()
        .strip(),
        flush=True,
    )
    return 0 if status == "completed" else 1


def check_linkage(
    eq_dir: Path,
    screen_dir: Path,
    confirm_dir: Path,
    selection: dict[str, Any],
    screen_workers: list[dict[str, Any]],
    confirm_workers: list[dict[str, Any]],
    *,
    dry_run: bool,
) -> None:
    """The analysed equivalence, screen and confirm runs must be one consistent chain.

    A stage can be re-run only with a recorded supersede, but the analysis still refuses to
    combine runs whose recorded evidence does not point at each other, and refuses any confirm
    worker that did not time exactly the plan derived from the analysed selection.
    """
    from .p6_analysis import confirm_entities

    screen = read_json(screen_dir / "result.json")
    confirm = read_json(confirm_dir / "result.json")
    selection_sha = file_sha256(screen_dir / "selection.json")
    evidence = confirm["evidence"]
    checks = {
        "screen consumed this equivalence run": screen["evidence"]["equivalence_run"]
        == eq_dir.name,
        "screen result records this selection": screen["selection_sha256"] == selection_sha,
        "confirm consumed this screen run": evidence["screen_run"] == screen_dir.name,
        "confirm consumed this selection": evidence["selection_sha256"] == selection_sha,
        "confirm consumed this equivalence run": evidence["equivalence_run"] == eq_dir.name,
        "confirm recorded this equivalence result": evidence["equivalence_result_sha256"]
        == file_sha256(eq_dir / "result.json"),
        "confirm recorded this screen result": evidence["screen_result_sha256"]
        == file_sha256(screen_dir / "result.json"),
        "screen workers timed the recorded screen plan": all(
            w.get("plan") == screen["plan"] for w in screen_workers
        ),
        "confirm workers timed the plan of this selection": all(
            w.get("plan") == confirm_entities(selection) for w in confirm_workers
        ),
        "all workers completed": all(
            w.get("outcome") == "completed" for w in [*screen_workers, *confirm_workers]
        ),
        "worker dry-run flags match": all(
            bool(w.get("dry_run")) == dry_run for w in [*screen_workers, *confirm_workers]
        ),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError("P6-E run linkage check failed: " + "; ".join(failed))


def _worker_results(compact_dir: Path) -> list[dict[str, Any]]:
    return [
        read_json(path)
        for path in sorted((compact_dir / "workers").glob("b*-o*-s*.json"))
        if not path.name.endswith((".terminal.json", ".manifest.json"))
    ]


def _screen_plan(workers: list[dict[str, Any]]) -> dict[str, list[str]]:
    return dict(workers[0]["plan"]) if workers else {}


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def loader_smoke(
    pair: tuple[int, int, int],
    *,
    parent_suite: Path,
    output_root: Path,
    p5_results: Path,
    data_dir: Path,
) -> dict[str, Any]:
    """Real loading path for one pair and the bitwise replay of each recorded P5 NLL. Nothing else.

    Writes only into a temporary folder outside ``results/`` and ``experiments/``. No variant,
    equivalence comparison, timing or fidelity quantity is computed.
    """
    from . import p6_common as common
    from . import p6_equivalence

    repo = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="p6e-loader-smoke-") as scratch:
        scratch_path = Path(scratch).resolve()
        for protected in (repo / "experiments", repo / "results"):
            if scratch_path.is_relative_to(protected):
                raise SystemExit(
                    "loader-smoke scratch folder must be outside experiments/ results/"
                )
        started = time.perf_counter()
        source = common.load_real_cell(
            pair,
            p5_suite=parent_suite,
            output_root=output_root,
            p5_results=p5_results,
            data_dir=data_dir,
            run=scratch_path,
        )
        load_seconds = time.perf_counter() - started
        replay: dict[str, Any] = {}
        for kind in common.KINDS:
            tick = time.perf_counter()
            record = p6_equivalence.integrity_replay(source, kind)
            replay[kind] = {**record, "seconds": time.perf_counter() - tick}
        files_unchanged = source.files_unchanged()
    return {
        "command": "loader-smoke",
        "study": "P6-E",
        "pair": list(pair),
        "load_seconds": load_seconds,
        "replay": replay,
        "checkpoint_files_unchanged": files_unchanged,
        "wall_seconds": time.perf_counter() - started,
        "peak_rss_bytes_ru_maxrss": _peak_rss_bytes(),
        "p6_quantities_computed": False,
        "note": "restore, hash verification and unmodified bitwise replay only; no variant, "
        "equivalence comparison, timing or fidelity quantity; nothing written under results/ "
        "or experiments/",
    }


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    command_line = [sys.executable, "-m", "arborlm.p6_retrieval_study", *(argv or sys.argv[1:])]
    if arguments.command == "_worker":
        return _worker(arguments.spec, arguments.child, tuple(arguments.pair))
    import torch

    from .engine import configure_cpu

    already = (
        torch.get_num_threads() == 1
        and torch.get_num_interop_threads() == 1
        and torch.are_deterministic_algorithms_enabled()
    )
    if not already:  # a second configure_cpu() call in one process cannot set interop threads
        configure_cpu()
    if arguments.command == "loader-smoke":
        report = loader_smoke(
            (arguments.pair[0], arguments.pair[1], arguments.pair[2]),
            parent_suite=arguments.parent_suite,
            output_root=arguments.output_root,
            p5_results=arguments.p5_results,
            data_dir=arguments.data_dir,
        )
        print(canonical_json(report).decode().strip(), flush=True)
        return 0 if report["checkpoint_files_unchanged"] else 1
    if arguments.command == "dry-run":
        return _dry_run(arguments, command_line)
    args = _args(arguments)
    if arguments.command == "equivalence":
        from .p6_equivalence import run_equivalence_stage

        return run_equivalence_stage(args, command_line)
    if arguments.command in ("screen", "confirm"):
        from .p6_timing_study import run_timing_stage

        return run_timing_stage(arguments.command, args, command_line)
    return analyze_stage(args, command_line)


def _dry_run(arguments: argparse.Namespace, command_line: list[str]) -> int:
    from .p6_equivalence import run_equivalence_stage
    from .p6_timing_study import run_timing_stage

    repo = Path.cwd().resolve()
    for root in (arguments.output_root, arguments.results_root):
        for protected in (repo / "experiments", repo / "results"):
            if root.resolve().is_relative_to(protected):
                raise SystemExit(
                    "dry-run refuses to write under experiments/ or results/: "
                    "use a temporary directory; dry-run output is not registered evidence"
                )
    args = _args(arguments, synthetic=True)
    codes = [
        run_equivalence_stage(args, command_line),
        run_timing_stage("screen", args, command_line),
        run_timing_stage("confirm", args, command_line),
        analyze_stage(args, command_line),
    ]
    return max(codes)


if __name__ == "__main__":
    raise SystemExit(main())
