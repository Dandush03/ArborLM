"""Audit B, check B2: the registered driver's guards, exercised in a throwaway git repository with a real write_freeze plan.

Heavy stage functions (world building, training, scoring) are replaced by recorders, so no world is built, no seed is drawn and no
registered seed is touched. Everything else is the pinned code. Usage: python b2_registered_driver_bypass.py <pin> <scratch-dir>
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "tests"))

from studies.p10s2 import budget, core, freeze, stages  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

GIB = 2**30


def git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a],
                          capture_output=True, text=True, check=True).stdout.strip()


def rates(scale: float) -> budget.Rates:
    us = {}
    for g in ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD"):
        us[f"{g}@L4"] = 0.5 * scale
        us[f"{g}@L12"] = 0.5 * scale
    for g in ("ETABLE", "LORA1", "LSEQ", "LJOINT"):
        us[g] = 0.6 * scale
    return budget.Rates(us, 4, 100.0 * scale, 600.0 * scale, 300.0 * scale, 120.0 * scale, 200.0 * scale, 0.0,
                        train_peak_bytes=2 * GIB, eval_peak_bytes=3 * GIB, recompute_peak_bytes=3 * GIB, task_peak_bytes=3 * GIB)


results: dict[str, object] = {}
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
repo = OUT / "repo"
for rel in ("studies/p10s2/x.py", "src/arborlm/a.py", "uv.lock", "pyproject.toml", "tests/test_p10s2_a.py"):
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text("x\n")
(repo / core.DEFAULT_CONFIG).parent.mkdir(parents=True, exist_ok=True)
(repo / core.DEFAULT_CONFIG).write_text((PIN / core.DEFAULT_CONFIG).read_text())
(repo / core.SPEC).parent.mkdir(parents=True, exist_ok=True)
(repo / core.SPEC).write_text("adr\n")
(repo / ".gitignore").write_text("/run/\n/prefreeze-run/\n")
(repo / "data").mkdir()
(repo / "data/manifest.json").write_text('{"files": {}}')
(repo / "calibration.json").write_text('{"selection": {"read_layer": 4}}')
(repo / "prefreeze.json").write_text(json.dumps({"g1": {"ok": True}, "qualification": {"ok": True, "outcome": None}, "sufficiency_pools": {"outcome": None}, "sufficiency_after_filter": {"outcome": None}}))
git(repo, "init", "-q", "-b", "main")
git(repo, "add", "-A")
git(repo, "commit", "-q", "-m", "pre-freeze")

# pre-freeze ledger as the README prescribes (<run-dir>/ledger.jsonl of the pre-freeze run directory): P = 3.5 h
pre_led = Ledger(repo / "prefreeze-run" / "ledger.jsonl")
pre_led.record("datagen", 1.0 * 3600)
pre_led.record("calibration", 1.0 * 3600)
pre_led.record("rehearsal", 1.5 * 3600)
run_dir = repo / "run"
core.reset_seed_record()
# scale so that rung 1 fits 36 h with P = 3.5 h: R(4,2000) ~ 16 h
rt = rates(1.0)
r1 = budget.registered_run_seconds(4, 2000, rt)["total"] / 3600
scale = 15.5 / r1
rt = rates(scale)
rec = freeze.write_freeze(repo, rates=rt, ledger=pre_led, run_dir=run_dir, data_dir="data", calibration=repo / "calibration.json", prefreeze=repo / "prefreeze.json", design_layer=4, store_lr=0.003, lora_lr=0.001)
git(repo, "add", "-A")
git(repo, "commit", "-q", "-m", "freeze")
fc = git(repo, "rev-parse", "HEAD")
plan = freeze.load_plan(repo)
frozen_caps = json.loads((repo / core.CAPS_FILE).read_text())
results["freeze"] = {"decision": rec["decision"]["outcome"], "R1_hours": rec["decision"]["projections_hours"]["n4-U2000"], "P_at_freeze": plan["charged_hours_at_freeze"], "frozen_train_cap_s": frozen_caps["n4-U2000"]["train"]}

# --- recorders in place of the heavy stage functions --------------------------------------------------------------------------------------------
calls: list[dict[str, object]] = []


class FakeBundle:
    extra: dict[str, object] = {}


stages.read_bundle = lambda d: FakeBundle()  # type: ignore[assignment]
stages.build_world = lambda b, mode, n, run: {"mode": mode, "n": n, "run": run}  # type: ignore[assignment]
stages.stage_train = lambda world, rd, deadline=None: calls.append({"stage": "train", "deadline_cap_s": None if deadline is None else deadline.cap, "gates_json_exists": (rd / "gates.json").exists()})  # type: ignore[assignment]
stages.stage_gates = lambda *a, **k: calls.append({"stage": "gates"})  # type: ignore[assignment]
stages.gate_inputs = lambda w, p: ({}, {})  # type: ignore[assignment]


def run(name: str, *extra: str) -> int:
    return stages.main(["registered", name, "--run-dir", str(run_dir), "--freeze-commit", fc, "--caps", "studies/p10s2/freeze/stage_caps.json", "--repo", str(repo), *extra])


# B2a: train runs without any gates record (the second gates stage never ran, or failed)
code = run("train")
results["B2a_train_without_gates"] = {"exit": code, "calls": list(calls)}

# B2b: a typed --caps file replaces the frozen stage-cap table (verify_plan hashes the frozen file; the driver uses the typed one)
typed = OUT / "my_caps.json"
typed.write_text(json.dumps({k: {**v, "train": 10 * 3600.0} for k, v in frozen_caps.items()}))
calls.clear()
code = stages.main(["registered", "train", "--run-dir", str(run_dir), "--freeze-commit", fc, "--caps", str(typed), "--repo", str(repo)])
results["B2b_typed_caps_override"] = {"exit": code, "frozen_train_cap_s": frozen_caps["n4-U2000"]["train"], "deadline_used_s": calls[0]["deadline_cap_s"] if calls else None}

# B2c: the registered ledger is <run-dir>/ledger.jsonl, a different file from the pre-freeze ledger: P is not in it.
reg_led = Ledger(run_dir / "ledger.jsonl")
results["B2c_ledger"] = {"registered_ledger_total_h": reg_led.total_hours(), "prefreeze_ledger_total_h": pre_led.total_hours(), "plan_charged_hours_at_freeze": plan["charged_hours_at_freeze"]}
# a train cap that would not fit once P is counted: 3.5 + 33 > 36, yet the stage starts
big = OUT / "big_caps.json"
big.write_text(json.dumps({k: {**v, "train": 33 * 3600.0} for k, v in frozen_caps.items()}))
calls.clear()
code = stages.main(["registered", "train", "--run-dir", str(run_dir), "--freeze-commit", fc, "--caps", str(big), "--repo", str(repo)])
results["B2c_ledger"]["train_with_33h_cap_started"] = bool(calls)  # type: ignore[index]

# B2d: --repo makes the checks read another tree than the code that runs
results["B2d_repo_override"] = {"code_running_from": str(core.ROOT), "tree_checked": str(repo), "same": core.ROOT.resolve() == repo.resolve()}

# B2e: after registered processes have run (registered entries in <run-dir>/ledger.jsonl), the cap-raise and a second freeze still pass
# when given the pre-freeze ledger, as the README's freeze command does
led_entries = Ledger(run_dir / "ledger.jsonl").entries()
results["B2e_registered_entries_in_run_ledger"] = sum(1 for e in led_entries if e.get("registered"))
slow = rates(scale * 1.6)
prop = budget.propose_raise(pre_led.total_hours(), slow)
raise_ok = None
try:
    budget.record_raise(prop, repo / core.RAISE_FILE, pre_led) if prop is not None else None
    raise_ok = True
except budget.CapRefused as e:
    raise_ok = f"refused: {e}"
try:
    rec2 = freeze.write_freeze(repo, rates=slow, ledger=pre_led, run_dir=run_dir, data_dir="data", calibration=repo / "calibration.json", prefreeze=repo / "prefreeze.json", design_layer=4, store_lr=0.003, lora_lr=0.001)
    refreeze = {"accepted": True, "decision": rec2["decision"]["outcome"], "cap": json.loads((repo / core.PLAN_FILE).read_text())["cap_hours"]}
except freeze.FreezeRefused as e:
    refreeze = {"accepted": False, "why": str(e)}
results["B2e_raise_and_refreeze_after_registered_observation"] = {"proposal": None if prop is None else prop.to_json(), "record_raise": raise_ok, "second_freeze": refreeze}
# with the registered run's own ledger the guard does fire
try:
    freeze.write_freeze(repo, rates=slow, ledger=Ledger(run_dir / "ledger.jsonl"), run_dir=run_dir, data_dir="data", calibration=repo / "calibration.json", prefreeze=repo / "prefreeze.json", design_layer=4, store_lr=0.003, lora_lr=0.001)
    results["B2e_with_run_ledger"] = "accepted"
except freeze.FreezeRefused as e:
    results["B2e_with_run_ledger"] = f"refused: {e}"

print(json.dumps(core.jsonable(results), indent=1, default=str))
