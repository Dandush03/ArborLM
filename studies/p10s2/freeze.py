# ruff: noqa: E501
"""The freeze procedure (ADR-0022 sections 13.3, 16): writes the frozen plan and cap files, and checks them before every registered stage.

Order (each step before the next; the freeze commit is the last): the rehearsal measures the rates (``rehearsal``); the rung rule decides the design from the charged hours and the rates
(``budget.rehearsal_rule``; ``NOT STARTED: BUDGET`` is recorded and nothing is written if no rung fits); ``write_freeze`` writes ``studies/p10s2/freeze/stage_caps.json`` (one entry per design
configuration and stage, 2x the projection), ``plan.json`` (the identities every registered stage checks) and ``rehearsal_outcome.json``; the lead writes the section 16 freeze record and makes one
freeze commit; the launch scripts take that commit.

A registered stage refuses unless: the working tree is clean; the freeze commit is an ancestor of HEAD; ``studies/p10s2``, the config, the ADR, ``src/arborlm``, ``uv.lock``, ``pyproject.toml`` and every
``tests/test_p10s2_*`` equal their content at that commit; the plan's identities hold (config, cap table, data manifest, calibration and projection records, cap raise, run directory); and the plan's
design is one of the registered rungs. No registered stage is launched by a typed command.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from arborlm.io import atomic_write, file_sha256

from . import budget, core
from .ledger import Ledger


class FreezeRefused(RuntimeError):
    """A registered stage or the freeze itself refuses (nothing is started, nothing is re-run with changed settings)."""


FROZEN_PATHS = ("studies/p10s2", "configs/p10s2_transfer.toml", core.SPEC, "src/arborlm", "uv.lock", "pyproject.toml")
TEST_PREFIX = "tests/test_p10s2_"


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def _rev(repo: Path, rev: str, path: str) -> bytes:
    return git(repo, "rev-parse", f"{rev}:{path}").stdout


def check_preconditions(repo: Path, freeze_commit: str | None) -> dict[str, str]:
    """Clean tree, the commit is an ancestor of HEAD, the frozen paths and every ``tests/test_p10s2_*`` equal their content at the commit. Returns the freeze identity."""
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().strip()
    if dirty:
        raise FreezeRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    if not freeze_commit:
        raise FreezeRefused("refused: a registered stage requires --freeze-commit")
    ok = git(repo, "rev-parse", "--verify", "--quiet", f"{freeze_commit}^{{commit}}")
    if ok.returncode != 0:
        raise FreezeRefused(f"refused: {freeze_commit} is not a commit of this repository")
    full = ok.stdout.decode().strip()
    if git(repo, "merge-base", "--is-ancestor", full, "HEAD").returncode != 0:
        raise FreezeRefused(f"refused: freeze commit {full} is not an ancestor of HEAD")
    problems = [f"{p} at HEAD differs from the freeze commit" for p in FROZEN_PATHS if _rev(repo, full, p) != _rev(repo, "HEAD", p)]
    for name in git(repo, "ls-tree", "--name-only", "HEAD", "tests/").stdout.decode().split():
        if name.startswith(TEST_PREFIX) and _rev(repo, full, name) != _rev(repo, "HEAD", name):
            problems.append(f"{name} differs from the freeze commit")
    if problems:
        raise FreezeRefused("refused: " + "; ".join(problems))
    return {"commit": full, "tree": git(repo, "rev-parse", f"{full}^{{tree}}").stdout.decode().strip()}


def check_code_commit(repo: Path, commit: str | None) -> str:
    """A pre-freeze stage (data generation, calibration, rehearsal) refuses unless the working tree is clean and its code commit equals HEAD (so the manifests record the code that ran)."""
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.decode().strip()
    if dirty:
        raise FreezeRefused("refused: the working tree is not clean:\n" + "\n".join(dirty.splitlines()[:10]))
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    full = git(repo, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}").stdout.decode().strip() if commit else ""
    if not full or full != head:
        raise FreezeRefused(f"refused: the code commit {commit!r} is not a clean HEAD ({head})")
    return full


def load_plan(repo: Path) -> dict[str, Any]:
    path = repo / core.PLAN_FILE
    if not path.is_file():
        raise FreezeRefused(f"refused: no freeze plan at {path}: nothing registered runs before the freeze")
    plan = json.loads(path.read_text())
    if not isinstance(plan, dict):
        raise FreezeRefused("refused: the freeze plan is not an object")
    return plan


def verify_plan(plan: dict[str, Any], repo: Path, run_dir: Path) -> None:
    """Every identity the freeze recorded must hold now."""

    def check(path: Path, expected: str, what: str) -> None:
        if not path.is_file() or file_sha256(path) != expected:
            raise FreezeRefused(f"refused: {path} does not hash to the frozen {what}")

    check(repo / core.DEFAULT_CONFIG, plan["config_sha256"], "configuration")
    check(repo / core.CAPS_FILE, plan["stage_caps_sha256"], "stage-cap table")
    check(repo / plan["data_dir"] / "manifest.json", plan["data_manifest_sha256"], "data manifest")
    for key in ("calibration", "prefreeze_record", "projection"):
        check(repo / plan[key]["path"], plan[key]["sha256"], f"{key} record")
    raise_path = repo / core.RAISE_FILE
    if plan.get("cap_raise_sha256") is not None:
        check(raise_path, plan["cap_raise_sha256"], "cap-raise record")
    elif raise_path.exists():
        raise FreezeRefused("refused: a cap-raise record exists that the freeze plan does not name")
    if budget.effective_cap(raise_path) != float(plan["cap_hours"]):
        raise FreezeRefused("refused: the cap in force differs from the cap the freeze recorded")
    design = (int(plan["design"]["replicates"]), int(plan["design"]["updates"]))
    if design not in budget.rungs():
        raise FreezeRefused(f"refused: the plan's design {design} is not a registered rung")
    if plan.get("run_dir") is not None and Path(plan["run_dir"]).resolve() != run_dir.resolve():
        raise FreezeRefused(f"refused: the freeze names the run directory {plan['run_dir']}, not {run_dir}")


def prefreeze_caps_from_ledger(ledger: Ledger) -> dict[str, Any]:
    """The pre-freeze stage caps in the configuration are provisional (the upper ends of the ADR's projections). The freeze replaces each with twice the wall time the ledger measured for that stage; it
    refuses while any stage has no measurement."""
    by = {"datagen": ["datagen"], "calibrate": ["calibration", "pilot"], "rehearse": ["rehearsal"]}
    seconds: dict[str, float] = {}
    for stage, kinds in by.items():
        total = sum(float(e["wall_seconds"]) for e in ledger.entries() if e["kind"] in kinds and e.get("status") == "completed")
        if total > 0:
            seconds[stage] = total
    missing = [s for s in by if s not in seconds]
    return {"provisional": bool(missing), "missing": missing, "measured_wall_seconds": seconds, "caps_seconds": {s: core.CFG["budget"]["headroom"] * v for s, v in seconds.items()}, "config_provisional_values_seconds": dict(core.CFG["prefreeze_caps"]), "rule": "2 x measured wall time, replacing the provisional configuration values"}


def code_digest(repo: Path) -> dict[str, str]:
    """Per-file SHA-256 of the study package (including the launch scripts) for the freeze record."""
    root = repo / "studies" / "p10s2"
    return {str(p.relative_to(repo)): file_sha256(p) for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.name not in ("plan.json", "stage_caps.json", "cap_raise.json", "rehearsal_outcome.json")}


def write_json_file(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, (json.dumps(core.jsonable(obj), sort_keys=True, indent=1) + "\n").encode())


def write_freeze(
    repo: Path, *, rates: budget.Rates, ledger: Ledger, run_dir: Path, data_dir: str, calibration: Path, prefreeze: Path, design_layer: int, store_lr: float, lora_lr: float,
) -> dict[str, Any]:  # fmt: skip
    """The freeze procedure. Refuses if a registered seed has been observed, if the data or records are missing, or if no rung fits (the outcome NOT STARTED: BUDGET is recorded first)."""
    freeze_dir = repo / core.FREEZE_DIR
    if budget.registered_seed_observed(ledger):
        raise FreezeRefused("refused: a registered seed has been observed before the freeze")
    p_hours = ledger.total_hours()
    measured = prefreeze_caps_from_ledger(ledger)
    write_json_file(freeze_dir / "prefreeze_caps.json", measured)
    if measured["provisional"]:
        raise FreezeRefused("refused: the pre-freeze stage caps are still provisional (" + ", ".join(measured["missing"]) + " not measured): the rehearsal replaces them with twice the measured wall time")
    cap = budget.effective_cap(repo / core.RAISE_FILE)
    decision = budget.rehearsal_rule(p_hours, rates, cap)
    projection = budget.projection_record(p_hours, rates, decision)
    write_json_file(freeze_dir / "rehearsal_outcome.json", {"outcome": decision.outcome, "decision": decision.to_json(), "headroom_check": budget.headroom_check(p_hours, rates, ledger, repo / core.RAISE_FILE)})
    if decision.outcome == budget.NOT_STARTED_BUDGET:
        raise FreezeRefused(f"{budget.NOT_STARTED_BUDGET}: recorded in {freeze_dir / 'rehearsal_outcome.json'}; the work returns to the human lead ({decision.reason})")
    assert decision.replicates is not None and decision.updates is not None
    for needed in (calibration, prefreeze, repo / data_dir / "manifest.json"):
        if not needed.is_file():
            raise FreezeRefused(f"refused: {needed} does not exist")
    from .prefreeze import prefreeze_summary

    summary = prefreeze_summary(json.loads(prefreeze.read_text()))
    if summary["stop"]:
        write_json_file(freeze_dir / "prefreeze_stop.json", {"label": summary["stop"], "summary": summary})
        raise FreezeRefused(f"{summary['stop']}: the study stops before the freeze (recorded in {freeze_dir / 'prefreeze_stop.json'})")
    write_json_file(freeze_dir / "projection.json", projection)
    caps = budget.stage_caps(rates)
    write_json_file(freeze_dir / "stage_caps.json", caps)
    raise_path = repo / core.RAISE_FILE
    plan = {
        "config_sha256": file_sha256(repo / core.DEFAULT_CONFIG), "stage_caps_sha256": file_sha256(freeze_dir / "stage_caps.json"),
        "design": {"replicates": decision.replicates, "updates": decision.updates, "layer": design_layer, "store_lr": store_lr, "lora_lr": lora_lr, "rung": decision.outcome},
        "cap_hours": cap, "cap_raise_sha256": file_sha256(raise_path) if raise_path.exists() else None, "charged_hours_at_freeze": p_hours,
        "data_dir": data_dir, "data_manifest_sha256": file_sha256(repo / data_dir / "manifest.json"),
        "calibration": {"path": str(calibration.relative_to(repo)) if calibration.is_absolute() else str(calibration), "sha256": file_sha256(calibration)},
        "prefreeze_record": {"path": str(prefreeze.relative_to(repo)) if prefreeze.is_absolute() else str(prefreeze), "sha256": file_sha256(prefreeze)},
        "projection": {"path": str((freeze_dir / "projection.json").relative_to(repo)), "sha256": file_sha256(freeze_dir / "projection.json")},
        "prefreeze": prefreeze_summary(json.loads(prefreeze.read_text())),
        "planned_seeds": sorted(s for r in range(decision.replicates) for s in core.SeedPlan("registered-run", r).planned()),
        "prefreeze_caps": measured, "run_dir": str(run_dir), "code": code_digest(repo),
    }  # fmt: skip
    write_json_file(freeze_dir / "plan.json", plan)
    return {"written": [str(core.PLAN_FILE), str(core.CAPS_FILE), str(core.FREEZE_DIR / "rehearsal_outcome.json"), str(core.FREEZE_DIR / "projection.json")], "decision": decision.to_json()}
