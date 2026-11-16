# ruff: noqa: E501
"""The freeze procedure (ADR-0022 sections 13.3, 16): writes the frozen plan and cap files, and checks them before every registered stage.

Order (each step before the next; the freeze commit is the last): the rehearsal measures the rates (``rehearsal``); the rung rule decides the design from the charged hours (the one study ledger) and the
rates (``budget.rehearsal_rule``; ``NOT STARTED: BUDGET`` is recorded and nothing is written if no rung fits); ``write_freeze`` copies the pre-freeze records into ``studies/p10s2/freeze/records/``, writes
``studies/p10s2/freeze/stage_caps.json`` (one entry per design configuration and stage, 2x the projection), ``plan.json`` (the identities every registered stage checks) and
``rehearsal_outcome.json``; the lead writes the section 16 freeze record and makes one freeze commit; the launch scripts take that commit.

Nothing typed enters the plan (audit B M11): the read layer, the learning rates and the pilot result come from the calibration record (for U = 1,000 from the 1,000-update snapshots), the design from the
rung rule, the cap from the study ledger and the rehearsal record, the device from the rehearsal record. A failed pilot, a missing record, a recorded registered seed or a device other than MPS stops the
freeze.

The run decision is recorded AFTER the freeze commit in ``results/p10s2-freeze-<date>/DECISION.md`` (outside every frozen path): it must contain the exact line ``DECISION: RUN`` and the full freeze commit
hash, and it must be committed in a later commit than the freeze commit. A registered stage refuses without it. Nothing designed to be written after the freeze commit is hashed by it (the ADR itself is a
frozen path, so a record is never written into it afterwards).

A registered stage refuses unless: the working tree is clean; the freeze commit is the commit that added ``plan.json`` and an ancestor of HEAD; ``studies/p10s2``, ``studies/__init__.py``, the config, the ADR,
``src/arborlm``, ``uv.lock``, ``pyproject.toml`` and every ``tests/test_p10s2_*`` equal their content at that commit; the plan's identities hold (config, cap table, data manifest, the copied records, cap
raise, code digest, run directory); the study ledger's cap equals the plan's; the design is one of the registered rungs; and a committed run decision exists. No registered stage is launched by a typed command.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from arborlm.io import atomic_write, file_sha256

from . import budget, core
from .ledger import Ledger, study_ledger_path


class FreezeRefused(RuntimeError):
    """A registered stage or the freeze itself refuses (nothing is started, nothing is re-run with changed settings)."""


FROZEN_PATHS = ("studies/p10s2", "studies/__init__.py", "configs/p10s2_transfer.toml", core.SPEC, "src/arborlm", "uv.lock", "pyproject.toml")
TEST_PREFIX = "tests/test_p10s2_"
RECORDS_DIR = core.FREEZE_DIR / "records"
RECORD_NAMES = ("calibration.json", "prefreeze_record.json", "prefreeze_gates.json", "rehearsal.json", "rates.json")
DECISION_GLOB = "results/p10s2-freeze-*/DECISION.md"
DECISION_LINE = "DECISION: RUN"
FREEZE_OUTPUTS = ("plan.json", "stage_caps.json", "cap_raise.json", "rehearsal_outcome.json", "projection.json")


def git(repo: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *argv], capture_output=True, check=False)  # noqa: S603, S607


def _rev(repo: Path, rev: str, path: str) -> bytes:
    r = git(repo, "rev-parse", f"{rev}:{path}")
    return r.stdout if r.returncode == 0 else b""  # a path absent at one revision compares equal to a path absent at another


def refusal_dir() -> Path:
    """Refusal records are written outside every frozen folder (a refusal that leaves an untracked file in the frozen tree makes the next stage refuse on an unclean tree)."""
    d = study_ledger_path().parent / "refusals"
    d.mkdir(parents=True, exist_ok=True)
    return d


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


def check_freeze_identity(repo: Path, full: str) -> None:
    """``--freeze-commit`` must be the commit that ADDED ``plan.json`` (a later commit with the same frozen paths is not the freeze commit; audit B m5)."""
    added = git(repo, "log", "--diff-filter=A", "--format=%H", "--", str(core.PLAN_FILE)).stdout.decode().split()
    if not added:
        raise FreezeRefused(f"refused: no commit in the history of this branch adds {core.PLAN_FILE}: there is no freeze commit")
    if added[-1] != full:
        raise FreezeRefused(f"refused: {full} is not the freeze commit: the commit that added {core.PLAN_FILE} is {added[-1]}")


def check_decision(repo: Path, full: str) -> str:
    """The run decision: a ``results/p10s2-freeze-<date>/DECISION.md`` committed in a commit after the freeze commit, containing the exact line ``DECISION: RUN`` and the full freeze commit hash. The content is
    read from the committed blob at HEAD, never from the working tree. Returns the path."""
    names = [n for n in git(repo, "ls-tree", "-r", "--name-only", "HEAD", "results/").stdout.decode().split("\n") if re.fullmatch(r"results/p10s2-freeze-[^/]+/DECISION\.md", n)]
    for rel in sorted(names):
        text = git(repo, "show", f"HEAD:{rel}").stdout.decode()
        if DECISION_LINE not in text.splitlines() or full not in text:
            continue
        added = git(repo, "log", "--diff-filter=A", "--format=%H", "-1", "--", rel).stdout.decode().strip()
        if added and added != full and git(repo, "merge-base", "--is-ancestor", full, added).returncode == 0:
            return rel
    raise FreezeRefused(f"refused: no committed run decision: {DECISION_GLOB} must contain the line {DECISION_LINE!r} and the full freeze commit {full}, committed after the freeze commit")


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


def code_digest(repo: Path) -> dict[str, str]:
    """Per-file SHA-256 of the study package (launch scripts included) for the freeze record, without the files the freeze itself writes and the copied records."""
    root = repo / "studies" / "p10s2"
    skip_dirs = {"__pycache__", "records"}
    out = {str(p.relative_to(repo)): file_sha256(p) for p in sorted(root.rglob("*")) if p.is_file() and not (skip_dirs & set(p.relative_to(root).parts)) and p.name not in FREEZE_OUTPUTS}
    init = repo / "studies" / "__init__.py"
    if init.is_file():
        out[str(init.relative_to(repo))] = file_sha256(init)
    return out


def verify_plan(plan: dict[str, Any], repo: Path, run_dir: Path, *, ledger: Ledger | None = None) -> None:
    """Every identity the freeze recorded must hold now."""

    def check(path: Path, expected: str, what: str) -> None:
        if not path.is_file() or file_sha256(path) != expected:
            raise FreezeRefused(f"refused: {path} does not hash to the frozen {what}")

    check(repo / core.DEFAULT_CONFIG, plan["config_sha256"], "configuration")
    check(repo / core.CAPS_FILE, plan["stage_caps_sha256"], "stage-cap table")
    check(repo / plan["data_dir"] / "manifest.json", plan["data_manifest_sha256"], "data manifest")
    for key in ("calibration", "prefreeze_record", "projection", "prefreeze_gates", "rehearsal", "rates"):
        if key in plan:
            check(repo / plan[key]["path"], plan[key]["sha256"], f"{key} record")
    raise_path = repo / core.RAISE_FILE
    if plan.get("cap_raise_sha256") is not None:
        check(raise_path, plan["cap_raise_sha256"], "cap-raise record")
    elif raise_path.exists():
        raise FreezeRefused("refused: a cap-raise record exists that the freeze plan does not name")
    if budget.effective_cap(raise_path) != float(plan["cap_hours"]):
        raise FreezeRefused("refused: the cap in force differs from the cap the freeze recorded")
    if ledger is not None:
        verify_ledger_snapshot(plan, ledger)
    if ledger is not None and ledger.cap_hours() != float(plan["cap_hours"]):
        raise FreezeRefused(f"refused: the study ledger's cap ({ledger.cap_hours()} h) differs from the cap the freeze recorded ({plan['cap_hours']} h): a raise after the freeze is not allowed")
    design = (int(plan["design"]["replicates"]), int(plan["design"]["updates"]))
    if design not in budget.rungs():
        raise FreezeRefused(f"refused: the plan's design {design} is not a registered rung")
    if plan.get("run_dir") is not None and Path(plan["run_dir"]).resolve() != run_dir.resolve():
        raise FreezeRefused(f"refused: the freeze names the run directory {plan['run_dir']}, not {run_dir}")
    if "code" in plan and plan["code"] != code_digest(repo):
        changed = sorted(set(plan["code"]) ^ set(code_digest(repo)) | {k for k, v in plan["code"].items() if code_digest(repo).get(k) != v})
        raise FreezeRefused("refused: the code differs from the frozen digest: " + ", ".join(changed[:6]))


def ledger_snapshot(ledger: Ledger) -> dict[str, Any]:
    """The study ledger's length and the SHA-256 of its lines now (recorded in the plan at the freeze; every registered stage checks that the ledger still begins with exactly these lines)."""
    raw = ledger.path.read_bytes() if ledger.path.exists() else b""
    lines = raw.splitlines(keepends=True)
    return {"lines": len(lines), "sha256": hashlib.sha256(b"".join(lines)).hexdigest()}


def verify_ledger_snapshot(plan: dict[str, Any], ledger: Ledger) -> None:
    """N2: a registered stage runs only against the study ledger that held P at the freeze: it begins with the recorded lines, byte for byte, and its charged total is not below the plan's. A fresh or edited
    ledger (it is git-ignored and per checkout) is refused."""
    snap = plan.get("ledger")
    if snap is None:
        raise FreezeRefused("refused: the plan records no study-ledger snapshot")
    raw = ledger.path.read_bytes() if ledger.path.exists() else b""
    lines = raw.splitlines(keepends=True)
    n = int(snap["lines"])
    if len(lines) < n or hashlib.sha256(b"".join(lines[:n])).hexdigest() != snap["sha256"]:
        raise FreezeRefused(f"refused: the study ledger does not begin with the {n} lines recorded at the freeze (a fresh, edited or other ledger): P is not what the freeze charged")
    if ledger.total_hours() + 1e-9 < float(plan["charged_hours_at_freeze"]):
        raise FreezeRefused("refused: the study ledger charges fewer hours than the plan recorded at the freeze")


def check_identities(repo: Path, data_dir: str, cal: dict[str, Any], gates_rec: dict[str, Any], reh: dict[str, Any], pre_record: dict[str, Any], rates: budget.Rates) -> None:
    """N3: every pre-freeze record carries the identity of what produced it (``identity``: bundle manifest SHA-256, code commit, configuration SHA-256, seed mode, update counts, device); the freeze refuses a
    record without one, one that names another bundle, configuration or seed mode, the wrong update counts, a stand-in or dry record (in the real configuration), and a CPU device without the rehearsal's own
    recorded failed MPS attempt."""
    manifest = file_sha256(repo / data_dir / "manifest.json")
    config = file_sha256(repo / core.DEFAULT_CONFIG)
    cfg = core.CFG
    expected = {"calibration": ("calibration", {"updates": int(cfg["calibration"]["updates"])}), "prefreeze_gates": ("rehearsal", {"updates": int(cfg["rehearsal"]["short_updates"])}), "rehearsal": ("rehearsal", {"updates": int(cfg["rehearsal"]["short_updates"]), "full_updates": int(cfg["rehearsal"]["full_updates"])})}
    for name, rec in (("calibration", cal), ("prefreeze_gates", gates_rec), ("rehearsal", reh)):
        ident = rec.get("identity")
        if not isinstance(ident, dict):
            raise FreezeRefused(f"refused: the {name} record carries no identity (bundle manifest, code commit, configuration, seed mode, update counts, device): a record written without one cannot be checked")
        if rec.get("synthetic") or rec.get("dry"):
            raise FreezeRefused(f"refused: the {name} record is marked synthetic or dry")
        if ident.get("bundle_manifest_sha256") != manifest:
            raise FreezeRefused(f"refused: the {name} record was made on another data bundle than the one being frozen")
        if ident.get("config_sha256") != config:
            raise FreezeRefused(f"refused: the {name} record was made under another configuration than the one being frozen")
        if not ident.get("code_commit"):
            raise FreezeRefused(f"refused: the {name} record names no code commit")
        mode, counts = expected[name]
        if ident.get("seed_mode") != mode:
            raise FreezeRefused(f"refused: the {name} record's seed mode is {ident.get('seed_mode')!r}, not {mode!r}")
        for k, v in counts.items():
            if ident.get("update_counts", {}).get(k) != v:
                raise FreezeRefused(f"refused: the {name} record ran {ident.get('update_counts', {}).get(k)} {k}, the configuration says {v} (a typed count)")
        if ident.get("device") != rates.train_device:
            raise FreezeRefused(f"refused: the {name} record ran on {ident.get('device')!r}, the rehearsal's rates on {rates.train_device!r}")
    if pre_record.get("bundle_manifest_sha256") != manifest:
        raise FreezeRefused("refused: the data-generation record names no bundle manifest, or another one, than the bundle being frozen")
    if pre_record.get("seed_mode") != "registered-data" and not core.is_test_configuration():
        raise FreezeRefused(f"refused: the data-generation record's seed mode is {pre_record.get('seed_mode')!r}: a stand-in bundle cannot be frozen under the real configuration")
    if rates.train_device == "cpu":
        att = reh.get("mps_attempt") or {}
        if att.get("ok") is not False or not str(att.get("error", "")).strip():
            raise FreezeRefused("refused: CPU is frozen without the rehearsal's own recorded failed MPS attempt (a typed reason is not one)")


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


def write_json_file(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, (json.dumps(core.jsonable(obj), sort_keys=True, indent=1) + "\n").encode())


def _refuse(name: str, obj: Any, message: str) -> FreezeRefused:
    write_json_file(refusal_dir() / name, obj)
    return FreezeRefused(message)


def selection_from_calibration(cal: dict[str, Any], updates: int) -> tuple[int, float, float]:
    """(read layer, store learning rate, LoRA learning rate) from the calibration record, never typed. For the reduced design (U = 1,000) the selection and the pilot gate of the 1,000-update snapshots
    are used (section 12.1, 12.2). A failed pilot, or a missing selection, refuses."""
    reduced = budget.reduced_updates(updates)
    sel_key, pilot_key = ("selection_at_snapshot", "pilot_at_snapshot") if reduced else ("selection", "pilot")
    if sel_key not in cal or pilot_key not in cal:
        raise FreezeRefused(f"refused: the calibration record has no {sel_key!r}/{pilot_key!r} (needed for U = {updates})")
    if not cal[pilot_key].get("ok"):
        raise FreezeRefused(f"{cal[pilot_key].get('outcome')}: the registered run does not start (section 12.2; recorded with the calibration records)")
    sel = cal[sel_key]
    return int(sel["read_layer"]), float(core.CFG["training"]["store_learning_rate"]), float(sel["lora_lr"])


def write_freeze(repo: Path, *, rates: budget.Rates, ledger: Ledger, run_dir: Path, data_dir: str, calibration: Path, prefreeze: Path, prefreeze_gates: Path, rehearsal: Path) -> dict[str, Any]:
    """The freeze procedure. Refuses if a registered seed has been observed (study ledger, seed record, committed plan), if the data or records are missing, if the pilot failed, if the rehearsal's gates
    stage failed, if the rehearsal trained on a device other than MPS, if a recorded cap raise is not the one recomputed from the rehearsal record, or if no rung fits (the outcome NOT STARTED: BUDGET
    is recorded first). The layer, the learning rates, the pilot result, the cap and the device come from the records."""
    freeze_dir = repo / core.FREEZE_DIR
    if budget.registered_seed_observed(ledger, repo):
        raise FreezeRefused("refused: a registered seed has been observed before the freeze")
    if ledger.unfinished():
        raise FreezeRefused("refused: the study ledger has a start marker with no end (a killed process): its time is charged but the record is unresolved")
    p_ledger = ledger.total_hours()
    measured = prefreeze_caps_from_ledger(ledger)
    if measured["provisional"]:
        raise _refuse("prefreeze_caps.json", measured, "refused: the pre-freeze stage caps are still provisional (" + ", ".join(measured["missing"]) + " not measured): the rehearsal replaces them with twice the measured wall time")
    for needed in (calibration, prefreeze, prefreeze_gates, rehearsal, repo / data_dir / "manifest.json"):
        if not needed.is_file():
            raise FreezeRefused(f"refused: {needed} does not exist")
    reh = json.loads(rehearsal.read_text())
    if "charged_hours_at_end_of_rehearsal" not in reh:
        raise FreezeRefused("refused: the rehearsal record does not name the charged hours at its end (P of the rung rule)")
    p_hours = float(reh["charged_hours_at_end_of_rehearsal"])  # the ADR's P: the hours charged when the rehearsal ended (the lead's ruling m7)
    if p_ledger > p_hours + 1e-6:
        raise FreezeRefused(f"refused: the study ledger holds {p_ledger:.6f} h, more than the {p_hours:.6f} h at the end of the rehearsal: something was charged after it")
    try:
        computed = budget.computed_cap(p_hours, rates)  # the cap is a rule, not a discretion (the lead's ruling of 2026-11-15)
        raise_recorded = ledger.cap_raise_entry() is not None or (repo / core.RAISE_FILE).exists()
        cap = budget.verify_raise(repo / core.RAISE_FILE, p_hours, rates, ledger) if raise_recorded else computed  # a recorded raise must equal the computed one; none yet is recorded below, once everything else is accepted
    except budget.CapRefused as e:
        raise FreezeRefused(str(e)) from e
    decision = budget.rehearsal_rule(p_hours, rates, cap)
    projection = budget.projection_record(p_hours, rates, decision)
    outcome = {"outcome": decision.outcome, "decision": decision.to_json(), "headroom_check": budget.headroom_check(p_hours, rates, ledger, repo / core.RAISE_FILE)}
    if decision.outcome == budget.NOT_STARTED_BUDGET:
        raise _refuse("rehearsal_outcome.json", outcome, f"{budget.NOT_STARTED_BUDGET}: recorded in {refusal_dir() / 'rehearsal_outcome.json'}; the work returns to the human lead ({decision.reason})")
    assert decision.replicates is not None and decision.updates is not None
    frozen_device = str(core.CFG["budget"]["training_device"])
    if rates.train_device != frozen_device and not (rates.train_device == "cpu" and rates.train_device_reason.strip()):
        # the lead's ruling of 2026-11-15: the frozen device is MPS unless the rehearsal itself cannot run on MPS, in which case the freeze may record CPU (section 13.3's fallback) with the reason and every rate rehearsed on CPU
        raise _refuse("device.json", {"train_device": rates.train_device, "reason": rates.train_device_reason, "frozen_device": frozen_device}, f"refused: the rehearsal trained on {rates.train_device!r} without a recorded reason; the frozen device is {frozen_device.upper()} unless the rehearsal itself cannot run on it (the reason is recorded with --device-reason) and no device changes after the freeze")
    pg = json.loads(prefreeze_gates.read_text())
    if not pg.get("ok"):
        raise _refuse("prefreeze_gates.json", pg, "refused: the pre-freeze gates stage on rehearsal seeds failed (a failed gate stops the run, section 12.3)")
    cal = json.loads(calibration.read_text())
    layer, store_lr, lora_lr = selection_from_calibration(cal, decision.updates)
    if int(cal["selection"]["read_layer"]) != rates.calibrated_layer:
        raise FreezeRefused(f"refused: the rehearsal's calibrated layer {rates.calibrated_layer} differs from the calibration record's selection {cal['selection']['read_layer']}")
    from .prefreeze import prefreeze_summary, tokenization_required_ok

    pre_record = json.loads(prefreeze.read_text())
    summary = prefreeze_summary(pre_record)
    if not summary["combined_whole_string_ok"]:
        raise FreezeRefused("refused: the combined-task whole-string check (addendum section 4.4) is absent or has a required mismatch: the same consequence as a prompt mismatch in test (a)")
    if summary["stop"]:
        raise _refuse("prefreeze_stop.json", {"label": summary["stop"], "summary": summary}, f"{summary['stop']}: the study stops before the freeze (recorded in {refusal_dir() / 'prefreeze_stop.json'})")
    if not tokenization_required_ok(pre_record):
        raise FreezeRefused("refused: test (a) of section 14.2 step 4 is absent or has a mismatch on a prompt or an R-icl prompt (0 required)")
    check_identities(repo, data_dir, json.loads(calibration.read_text()), json.loads(prefreeze_gates.read_text()), reh, json.loads(prefreeze.read_text()), rates)
    # everything is accepted: now (and only now) the computed raise is recorded (if the rule needs one) and the frozen folder is written
    if cap > budget.base_cap() and not raise_recorded:
        budget.record_raise(rates, repo / core.RAISE_FILE, ledger, repo=repo, recorded_by="freeze (computed rule)")
    records: dict[str, dict[str, str]] = {}
    for key, src in (("calibration", calibration), ("prefreeze_record", prefreeze), ("prefreeze_gates", prefreeze_gates), ("rehearsal", rehearsal)):
        dst = freeze_dir / "records" / f"{key}.json"
        write_json_file(dst, json.loads(src.read_text()))
        records[key] = {"path": str(dst.relative_to(repo)), "sha256": file_sha256(dst)}
    write_json_file(freeze_dir / "records" / "rates.json", rates.to_json())
    records["rates"] = {"path": str((freeze_dir / "records" / "rates.json").relative_to(repo)), "sha256": file_sha256(freeze_dir / "records" / "rates.json")}
    write_json_file(freeze_dir / "rehearsal_outcome.json", outcome)
    write_json_file(freeze_dir / "projection.json", projection)
    caps = budget.stage_caps(rates)
    write_json_file(freeze_dir / "stage_caps.json", caps)
    raise_path = repo / core.RAISE_FILE
    ledger_snap = ledger_snapshot(ledger)  # after the raise entry: every later stage checks the ledger still begins with these lines
    plan = {
        "config_sha256": file_sha256(repo / core.DEFAULT_CONFIG), "stage_caps_sha256": file_sha256(freeze_dir / "stage_caps.json"),
        "design": {"replicates": decision.replicates, "updates": decision.updates, "layer": layer, "store_lr": store_lr, "lora_lr": lora_lr, "rung": decision.outcome, "device": rates.train_device, "scoring_device": "cpu"},
        "cap_hours": cap, "cap_raise_sha256": file_sha256(raise_path) if raise_path.exists() else None, "charged_hours_at_freeze": p_hours, "ledger": ledger_snap,
        "data_dir": data_dir, "data_manifest_sha256": file_sha256(repo / data_dir / "manifest.json"),
        "projection": {"path": str((freeze_dir / "projection.json").relative_to(repo)), "sha256": file_sha256(freeze_dir / "projection.json")},
        **records,
        "prefreeze": summary,
        "planned_seeds": sorted(s for r in range(decision.replicates) for s in core.SeedPlan("registered-run", r).planned()),
        "prefreeze_caps": measured, "run_dir": str(run_dir), "code": code_digest(repo),
        "decision_rule": f"a run decision is committed after the freeze commit in {DECISION_GLOB} with the line {DECISION_LINE!r} and the full freeze commit hash",
    }  # fmt: skip
    write_json_file(freeze_dir / "plan.json", plan)
    return {"written": [str(core.PLAN_FILE), str(core.CAPS_FILE), str(core.FREEZE_DIR / "rehearsal_outcome.json"), str(core.FREEZE_DIR / "projection.json"), *[v["path"] for v in records.values()]], "decision": decision.to_json()}

