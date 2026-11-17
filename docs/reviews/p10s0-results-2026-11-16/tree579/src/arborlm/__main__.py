"""Command-line entry point for E0 train, eval and smoke runs."""

import argparse
import sys
from pathlib import Path

from .watchdog import PROCESS_SECONDS, SMOKE_SECONDS, supervise


def main() -> int:
    parser = argparse.ArgumentParser(description="ArborLM E0 CPU infrastructure validation")
    commands = parser.add_subparsers(dest="operation", required=True)
    train = commands.add_parser("train")
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--output-root", type=Path, required=True)
    options = train.add_mutually_exclusive_group()
    options.add_argument("--stop-after", type=int, choices=(16,))
    options.add_argument("--resume", type=Path)
    evaluation = commands.add_parser("eval")
    evaluation.add_argument("--checkpoint", type=Path, required=True)
    evaluation.add_argument("--output-root", type=Path, required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--config", type=Path, required=True)
    smoke.add_argument("--output-root", type=Path, required=True)
    pilot = commands.add_parser("pilot")
    pilot.add_argument("--config", type=Path, required=True)
    pilot.add_argument("--data-dir", type=Path, required=True)
    pilot.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "pilot":
        from .pilot import launch

        run, ok = launch(
            args.config.resolve(),
            args.data_dir.resolve(),
            args.output_root.resolve(),
            [sys.executable, "-m", "arborlm", *sys.argv[1:]],
        )
        print(
            f"{'Recorded' if ok else 'Failed'} P1_SCREEN: {run}",
            file=sys.stdout if ok else sys.stderr,
        )
        return 0 if ok else 1

    worker: list[str] = []
    for name in ("config", "checkpoint", "resume", "stop_after"):
        value = getattr(args, name, None)
        if value is not None:
            worker += [
                "--" + name.replace("_", "-"),
                str(value.resolve() if isinstance(value, Path) else value),
            ]
    run, ok = supervise(
        args.output_root.resolve(),
        args.operation,
        worker,
        requested_argv=[sys.executable, "-m", "arborlm", *sys.argv[1:]],
        process_seconds=SMOKE_SECONDS if args.operation == "smoke" else PROCESS_SECONDS,
    )
    print(
        f"{'Recorded' if ok else 'Failed'} E0 {args.operation}: {run}",
        file=sys.stdout if ok else sys.stderr,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
