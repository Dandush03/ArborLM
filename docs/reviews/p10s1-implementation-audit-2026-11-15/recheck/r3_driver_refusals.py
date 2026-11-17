"""M3 re-check, in-process and safe: every probe is either refused before any git, data, seed or file access, or is a pure function call.

1. `registered <stage>` with each override flag (predecessor's c10 list plus every other common option): exit code and message.
2. Every non-driver command with `--mode registered`, and with no --mode (train, gates, evaluate, ... default to registered): exit code.
3. `generate --mode registered` with a typed cap / ledger / repo (run under P10S1_TEST_SEEDS=1 so that, if a refusal were missing, only test seeds could be touched;
   the run directory is a scratch path), and with no override while the config's generation cap is provisional.
4. The worker entry point: `work train --mode registered` without a plan (refused) and verify_worker_plan() on a SELF-MADE plan whose digest is typed on the same
   command line (pure call; shows the check binds the plan to the typed digest only, not to the committed freeze plan).
5. The predecessor's c10 (argparse level) is re-run unchanged separately: argparse still accepts the flags; the refusal is in cmd_registered/main.

Run (worktree root): PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r3_driver_refusals.py <scratch-dir>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import contextlib
import io
import json
import os
import sys
from pathlib import Path

from arborlm.io import file_sha256
from studies.p10s1 import core
from studies.p10s1 import frozen as fz
from studies.p10s1 import stages as S

scratch = Path(sys.argv[1])
scratch.mkdir(parents=True, exist_ok=True)
RUN = str(scratch / "never-created-run")
OUT = {}


def call(argv):
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        try:
            code = S.main(argv)
        except SystemExit as exc:
            code = f"SystemExit({exc.code})"
        except Exception as exc:  # noqa: BLE001
            code = f"{type(exc).__name__}: {exc}"
    return {"exit": code, "stderr": err.getvalue().strip().splitlines()[-1:] if err.getvalue() else []}


overrides = [("--stage-cap-seconds", "999999"), ("--ledger-root", str(scratch / "fresh-ledger")), ("--experiments-root", str(scratch / "x")), ("--rss-worker-bytes", "99999999999"),
             ("--rss-aggregate-bytes", "99999999999"), ("--only", "P_F-OQ_f2048_n4096_d1_i2101"), ("--repo", str(scratch)), ("--workers", "1"), ("--freeze-plan", str(scratch / "p.json")),
             ("--freeze-plan-sha256", "00"), ("--seed-block", "1,2"), ("--overload-u-p", "16384"), ("--labels", "x"), ("--updates", "5"), ("--draw", "2"), ("--synthetic-backbone", None),
             ("--timing", str(scratch / "t.json")), ("--calibration", str(scratch / "c.json")), ("--results-dir", str(scratch / "r")), ("--restore-split", "4")]
OUT["registered_with_override"] = {}
for flag, value in overrides:
    argv = ["registered", "train", "--run-dir", RUN, "--freeze-commit", "HEAD", flag] + ([value] if value is not None else [])
    OUT["registered_with_override"][flag] = call(argv)
OUT["registered_with_dry"] = call(["registered", "train", "--run-dir", RUN, "--freeze-commit", "HEAD", "--dry"])

OUT["non_driver_commands_registered_mode"] = {}
for cmd in ("train", "evaluate", "gates", "timing", "simulate", "analyze", "report", "calibrate", "rehearse", "synthetic", "project", "freeze", "set-generation-cap"):
    OUT["non_driver_commands_registered_mode"][cmd] = {"--mode registered": call([cmd, "--mode", "registered", "--run-dir", RUN, "--freeze-commit", "HEAD", "--stage-cap-seconds", "100"])}
for cmd in ("train", "evaluate", "gates", "simulate", "analyze", "report"):
    OUT["non_driver_commands_registered_mode"][cmd]["no --mode (defaults to registered)"] = call([cmd, "--run-dir", RUN, "--freeze-commit", "HEAD", "--stage-cap-seconds", "100"])

os.environ[core.TEST_SWITCH_ENV] = "1"  # safety: if a refusal were missing, only test seed sets could be generated (into the scratch run dir)
OUT["generate_registered"] = {
    "typed cap": call(["generate", "--mode", "registered", "--draw", "1", "--run-dir", RUN, "--i-understand-freeze-time", "--stage-cap-seconds", "1"]),
    "typed ledger root": call(["generate", "--mode", "registered", "--draw", "1", "--run-dir", RUN, "--i-understand-freeze-time", "--ledger-root", str(scratch)]),
    "typed repo": call(["generate", "--mode", "registered", "--draw", "1", "--run-dir", RUN, "--i-understand-freeze-time", "--repo", str(scratch)]),
    "no override, provisional cap in this worktree's config": call(["generate", "--mode", "registered", "--draw", "1", "--run-dir", RUN, "--i-understand-freeze-time"]),
}
del os.environ[core.TEST_SWITCH_ENV]
OUT["config_generation"] = core.generation_settings()
OUT["run_dir_created_by_any_probe"] = Path(RUN).exists()

# 4. worker entry point
OUT["work_train_registered_without_plan"] = call(["work", "train", "--mode", "registered", "--run-dir", RUN, "--labels", "x"])
fake = scratch / "self-made-plan.json"
fro = fz.Frozen.build(core.Plan(seed_block_draws=(1,)), fz.default_cpu_table())
fake.write_text(json.dumps({"frozen": fro.as_json(), "note": "self-made by the auditor; no freeze, no commit"}))
args = S.build_parser().parse_args(["work", "train", "--mode", "registered", "--run-dir", RUN, "--labels", "x", "--freeze-plan", str(fake), "--freeze-plan-sha256", file_sha256(fake)])
try:
    S.verify_worker_plan(args)
    OUT["verify_worker_plan_on_self_made_plan"] = "ACCEPTED (the digest is typed on the same command line; nothing binds it to studies/p10s1/freeze/plan.json or a freeze commit)"
except Exception as exc:  # noqa: BLE001
    OUT["verify_worker_plan_on_self_made_plan"] = f"refused: {exc}"
OUT["frozen_of_self_made_plan_cells"] = len(S.registered_cell_list(S.frozen_of(args)))
import inspect  # noqa: E402

src = {n: inspect.getsource(getattr(S, n)) for n in ("work_train", "work_gates", "work_evaluate", "verify_worker_plan")}
OUT["worker_functions_call_check_preconditions"] = {n: "check_preconditions" in s for n, s in src.items()}
OUT["worker_functions_check_ledger"] = {n: "Ledger" in s for n, s in src.items()}
fake.unlink()
json.dump(OUT, sys.stdout, indent=1, default=str)
print()
