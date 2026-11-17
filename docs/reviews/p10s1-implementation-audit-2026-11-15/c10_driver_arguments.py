"""Argument handling of the registered driver and of the non-driver commands in registered mode (pure: argparse and pure functions only; no data,
no seed, no git, no training). Shows (1) the 'registered' sub-command accepts --stage-cap-seconds, --ledger-root, --experiments-root, --rss-*-bytes and
--only, and stage_cap() returns the typed cap in preference to the frozen one; (2) 'train --mode registered' builds its plan without any freeze plan.
Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c10_driver_arguments.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import inspect, json, sys
from studies.p10s1 import stages as S
out = {}
a = S.build_parser().parse_args(["registered", "train", "--run-dir", "/x", "--freeze-commit", "abc", "--stage-cap-seconds", "999999", "--ledger-root", "/tmp/fresh-ledger", "--rss-worker-bytes", "99999999999", "--only", "P_F-OQ_f2048_n4096_d1_i2101"])
out["registered_parse_accepts_extra_flags"] = {"stage_cap_seconds": a.stage_cap_seconds, "ledger_root": a.ledger_root, "rss_worker_bytes": a.rss_worker_bytes, "only": a.only}
out["stage_cap_prefers_typed_over_frozen"] = S.stage_cap(a, 100.0)
b = S.build_parser().parse_args(["train", "--mode", "registered", "--run-dir", "/x", "--freeze-commit", "HEAD", "--stage-cap-seconds", "100"])
b.dry = False
fro = S.frozen_of(b)
out["train_mode_registered_without_freeze_plan"] = {"freeze_plan": b.freeze_plan, "plan_used": fro.plan.as_json(), "cells": len(S.registered_cell_list(fro))}
src = inspect.getsource(S.check_preconditions)
out["check_preconditions_mentions_plan_json"] = ("plan.json" in src) or ("load_plan" in src) or ("verify_plan" in src)
out["run_stage_tasks_mentions_plan"] = "verify_plan" in inspect.getsource(S.run_stage_tasks) or "load_plan" in inspect.getsource(S.run_stage_tasks)
json.dump(out, sys.stdout, indent=1); print()
