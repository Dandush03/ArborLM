"""Can a registered-mode stage run without the frozen plan, and does the driver accept cap / ledger / memory / backbone overrides?
Only argument parsing and the stage functions up to the pool are exercised: check_preconditions, the gate/draw-plan guards and the pool are stubbed
(the stubs stand in for a real post-freeze state with a clean tree, a passed gates.json and an ok draw plan). Nothing is trained; no seed is built.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json, tempfile
from pathlib import Path
from studies.p10s0 import stages, core
from studies.p9 import pool

out = {}
tmp = Path(tempfile.mkdtemp())
p = stages.build_parser()
argv = ["registered", "q1", "--run-dir", str(tmp / "run"), "--freeze-commit", "c", "--caps", stages.CAPS_FILE, "--stage-cap-seconds", "1e9", "--ledger-root", str(tmp / "fresh-ledger"),
        "--rss-worker-bytes", str(10**12), "--rss-aggregate-bytes", str(10**13), "--synthetic-backbone", "--only", "Q1-A5-D-2K4K-d01-j0", "--experiments-root", str(tmp), "--cut3", "--restore-split", "1"]
ns = p.parse_args(argv)
ns.mode = "registered"
out["registered_q1_parses_with_overrides"] = True
out["stage_cap_given_frozen_100s"] = stages.stage_cap(ns, 100.0)
out["limits"] = stages.limits(ns)
out["synthetic_backbone_in_registered_mode"] = stages.is_synthetic(ns)
out["ledger_root"] = str(stages.ledger_root(ns))

# A typed 'train' command defaults to registered mode and never loads the frozen plan
calls = {"load_plan": 0, "run_stage": None}
stages.check_preconditions = lambda mode, repo, fc: {"commit": "c"}
stages.require_gates_passed = lambda run_dir: {}
stages.require_draw_plan = lambda run_dir: {"ok": True, "seed_set_of": {}}
orig_load = stages.load_plan
def lp(repo):
    calls["load_plan"] += 1
    return orig_load(repo)
stages.load_plan = lp
class Stop(Exception):
    pass
def fake_run_stage(tasks, **kw):
    calls["run_stage"] = {"tasks": len(tasks), "stage_cap_seconds": kw["stage_cap_seconds"], "rss_worker_bytes": kw["rss_worker_bytes"], "workers": kw["workers"], "first_argv_has_synthetic": "--synthetic-backbone" in tasks[0].argv}
    raise Stop()
pool.run_stage = fake_run_stage
t = p.parse_args(["train", "--block", "q1", "--run-dir", str(tmp / "run2"), "--freeze-commit", "c", "--stage-cap-seconds", "50000", "--ledger-root", str(tmp / "l2"), "--rss-worker-bytes", str(10**12), "--synthetic-backbone", "--cut3"])
t.mode = t.mode or stages.DEFAULT_MODE.get("train", "registered")
out["typed_train_mode"] = t.mode
try:
    stages.cmd_train(t)
except Stop:
    pass
out["typed_train_reached_pool"] = calls["run_stage"]
out["typed_train_called_load_plan"] = calls["load_plan"]
out["typed_train_wrote_q1_start"] = (tmp / "run2" / "q1_start.json").exists()
print(json.dumps(out, indent=1))
