# ruff: noqa: E501
"""The real-path pieces of Part Q (ADR-0025 sections 4.1 step 1, 11 item 1, 13 item 6; rulings L3, L10): path and pin checks, the package-path guard, and the registered / rehearsal drivers.

IMPLEMENTED AND TESTED WITHOUT ANY PACKAGE: the WikiText-2 path check and the hash check against the pinned acquisition record, the durable-copy path rules, the package-path guard (an absolute path of the durable
copy only, offline, never through uv's cache).

NOT IMPLEMENTED HERE, returned to the lead (``PendingLeadReview``): the glue that needs the real model and the 28 packages and that this implementation was forbidden to run: the student conversion and the
equivalence record (gate G8), the tokenizer record, the GEN-window tokenization that builds the byte spans, the chrF cross-check against ``sacrebleu``, the token-id bank and tokenization tests of ADR-0022
section 14.2, and the construction of the real ``QContext`` (corpus from the durable copy, ``marian_batch_teacher`` for each teacher, the student scorer). ``teacher.marian_batch_teacher`` and
``pipeline`` take those as injected interfaces, so the glue is a bounded piece of work with the packages on the path.
"""

import argparse
import json
import os
import re
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256

from ..common import core
from ..common import plan as planmod
from ..common.core import StageRefused
from . import pipeline

ADR_0004 = "docs/decisions/ADR-0004-real-data-pilot-prerequisite.md"
ADR_0004_REVISION = "b08601e04326c79dfdd32d625aee71d232d685c3"  # the Hugging Face DATASET revision ADR-0004 pins for the parquet files; NOT a git commit
WIKITEXT_FILES = ("train-00000-of-00001.parquet", "validation-00000-of-00001.parquet")
NOT_IMPLEMENTED: tuple[str, ...] = ()  # the real bodies are in real_world / real_bundle / real_stages (not exercised at registered size: see the report)


def wikitext_pins(repo: Path) -> dict[str, dict[str, Any]]:
    """The expected bytes and SHA-256 of each WikiText-2 file from the table of ADR-0004 (ruling L10). ``b08601e`` is the Hugging Face dataset revision ADR-0004 pins for the parquet files, not a git commit; the pinned
    acquisition is ADR-0004's table in the working tree (immutable by policy), and the gate records that file's SHA-256 (``adr_0004_sha256``)."""
    text = (repo / ADR_0004).read_text(encoding="utf-8")
    pins: dict[str, dict[str, Any]] = {}
    for m in re.finditer(r"^\|\s*`([^`]+\.parquet)`\s*\|\s*([\d,]+)\s*\|\s*`([0-9a-f]{64})`\s*\|", text, flags=re.M):
        pins[m[1]] = {"bytes": int(m[2].replace(",", "")), "sha256": m[3]}
    missing = [f for f in WIKITEXT_FILES if f not in pins]
    if missing:
        raise StageRefused(f"refused: {ADR_0004} has no pin for {missing}")
    return {f: pins[f] for f in WIKITEXT_FILES}


def check_wikitext(directory: Path, pins: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Step 1, before anything else: the path exists and each file matches its pin. A difference stops the step (a registered test of the data step, ruling L3)."""
    if not directory.is_dir():
        raise StageRefused(f"refused: the WikiText-2 directory {directory} does not exist (ruling L10: the main checkout's data/wikitext2/)")
    out: dict[str, Any] = {"directory": str(directory), "pins_from": f"{ADR_0004} (working tree; Hugging Face dataset revision {ADR_0004_REVISION})"}
    for name, pin in pins.items():
        p = directory / name
        if not p.is_file():
            raise StageRefused(f"refused: {p} does not exist")
        digest = file_sha256(p)
        if p.stat().st_size != pin["bytes"] or digest != pin["sha256"]:
            raise StageRefused(f"refused: {name} does not match its pin: {p.stat().st_size} bytes, SHA-256 {digest}")
        out[name] = {"bytes": p.stat().st_size, "sha256": digest}
    return out


def package_path_problems(cfg: Mapping[str, Any], env: Mapping[str, str], argv: Sequence[str]) -> list[str]:
    """Section 13 item 6: the 28 packages go on the path of a data-generation process ONLY from the durable copy's absolute path, offline, never through uv's cache, and never for Part T. ``env`` is the
    process environment, ``argv`` its command line. An empty list means the mechanism is the one the ADR names."""
    durable = cfg["paths"]["durable_packages"]
    problems: list[str] = []
    pp = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    if durable not in pp:
        problems.append(f"PYTHONPATH does not name the durable copy {durable}")
    if any(not os.path.isabs(p) for p in pp):
        problems.append("PYTHONPATH holds a relative path: the packages are used by their absolute path only")
    if any("worktrees" in p and p != durable for p in pp):
        problems.append("PYTHONPATH names a worktree path: the durable copy is the only source")
    if "--offline" not in argv and env.get("UV_OFFLINE") not in ("1", "true"):
        problems.append("the process is not offline (--offline or UV_OFFLINE=1)")
    if any(a in ("--with-requirements", "--with", "-r") or a.endswith("requirements-datagen.txt") for a in argv):
        problems.append("the requirements file is never an argument of uv run: nothing is resolved from uv's cache")
    cache = env.get("UV_CACHE_DIR")
    if cache and any(p.startswith(cache) for p in pp):
        problems.append("PYTHONPATH reaches into uv's cache")
    return problems


def part_t_package_problems(env: Mapping[str, str], cfg: Mapping[str, Any]) -> list[str]:
    """Part T uses the lock alone: its processes may not have the durable package copy on their path."""
    durable = cfg["paths"]["durable_packages"]
    return [f"Part T process has {durable} on PYTHONPATH"] if durable in env.get("PYTHONPATH", "").split(os.pathsep) else []


def durable_inputs_problems(cfg: Mapping[str, Any]) -> list[str]:
    """Part Q reads the durable copy only (section 11 item 1)."""
    out = []
    for key in ("durable_downloads", "durable_packages"):
        p = Path(cfg["paths"][key])
        if not p.is_absolute():
            out.append(f"{key} is not an absolute path")
        elif "worktrees" in p.parts:
            out.append(f"{key} lies in a worktree: Part Q reads the durable copy in the main checkout's data folder only")
    return out


def run_registered_stage(stage: str, repo: Path, run_dir: Path, plan: Any) -> dict[str, Any]:
    """A registered stage: the real body, in this process (``real_stages.run_stage``), parameters from the frozen plan. The entry point has already refused unless frozen, committed and Decision 2 recorded."""
    from . import real_stages

    return real_stages.run_stage(stage, repo, run_dir, "registered", plan=plan)


def run_rehearsal(kind: str, repo: Path, run_dir: Path, args: argparse.Namespace) -> None:
    """The two Part Q rehearsals on the real teachers (section 10): ``measuring`` (steps 1-8, one generation block per capability, one Q_check block, the fixed cap) and ``counting`` (the candidate plan file, two
    generation blocks per capability, one forced pause and resume, one forced PAUSED — IDENTITY and restore). The rehearsal runs generation, regeneration and the outputs WHATEVER Q1-Q4 give (``force_generation``:
    a fallback filter setting if Q3 gives none), so that which stages ran does not reveal the sealed outcome. Values of Q1-Q4 and every per-item score go to ``<run-dir>/sealed``; the record printed is the
    whitelist. The rehearsal partition seeds 252901-252914 are used; the wall time of the whole run is charged to ``<run-dir>/charged_ledger.json`` (ruling L2), also when the rehearsal fails."""
    t_start = time.monotonic()
    try:
        _run_rehearsal(kind, repo, run_dir, args)
    except BaseException:
        core.Ledger(run_dir / "charged_ledger.json", "Q", 1e12).charge_process("rehearsal-failed", kind, "main", time.monotonic() - t_start)
        raise


def _run_rehearsal(kind: str, repo: Path, run_dir: Path, args: argparse.Namespace) -> None:
    from ..common import gates as cgates
    from ..common import procs
    from . import real_stages, rehearsal

    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    cgates.apply_platform_settings(cfg)
    core.require_ignored_run_dir(repo, run_dir)
    t0 = time.monotonic()
    if not real_stages.ledger_path(cfg, repo, run_dir, "rehearsal").is_file():
        real_stages.command_ledger(repo, run_dir, "rehearsal")  # the candidate ledger of the rehearsal (seed 252907); inputs verifies it
    cplan = planmod.Plan.load(repo / core.PLAN_Q, "Q") if kind == "counting" else None
    w = real_stages.build_world(cfg, repo, run_dir, "rehearsal", load_teachers=True, plan=cplan)  # with the candidate plan the world runs the SAME stage-start check of the plan's inputs and package manifest as a registered stage
    ctx0 = real_stages.make_ctx(w, "rehearsal")
    inputs = real_stages.stage_inputs(w, ctx0, "rehearsal")
    t_inputs = time.monotonic() - t0

    def factory() -> pipeline.QContext:
        c = real_stages.make_ctx(w, "rehearsal")
        c.force_generation = True
        return c

    cap = float(cfg["caps"]["measuring_rehearsal_hours"]) * 3600.0
    out_info: dict[str, Any] = {}

    def outputs_stage() -> None:
        """Step 8, a stage of the registered run: it runs in EVERY rehearsal, whatever Q1-Q4 gave (whether it ran must not reveal the sealed outcome)."""
        c = factory()
        p = pipeline.step_partition(c)
        t1 = time.monotonic()
        out = real_stages.stage_outputs(w, c, p, "rehearsal")
        out_info.update(seconds=time.monotonic() - t1, bundle=out["bundle"], units=float(sum(len(v) for v in p.panels.values())))

    if kind == "measuring":
        rec = rehearsal.run_measuring(factory, cap_seconds=cap, external={"inputs": (t_inputs, 1.0)}, post_stages={"outputs": outputs_stage})
        rec["rates_seconds_per_unit"]["outputs"] = out_info["seconds"] / max(1.0, out_info["units"])
        rec["projection_units"]["outputs"] = out_info["units"]
    else:
        plan_file = repo / core.PLAN_Q
        plan = cplan if cplan is not None else planmod.Plan.load(plan_file, "Q")
        items = {st: len(v) for st, v in plan.data["items"].items()}
        rec = rehearsal.run_counting(factory, plan_file_sha256=file_sha256(plan_file), caps_provisional=bool(plan.data.get("caps_provisional", True)), cap_seconds=float(cfg["caps"]["rehearsal_hours"]) * 3600.0, identity_probe=identity_probe(plan, repo, run_dir), post_stages={"outputs": outputs_stage}, plan_stage_items=items)
    rec["inputs_stage"] = {"seconds": t_inputs, "ordinary_windows_left": inputs["ordinary_windows_left"], "marker_like_windows": inputs["marker_like_windows"], "corpus_supply": inputs["corpus_supply"]}
    rec["outputs_stage"] = {"ran": True, "seconds": out_info["seconds"]}
    rec["other_studies_alive"] = procs.other_studies_alive()
    total = time.monotonic() - t0
    led = core.Ledger(run_dir / "charged_ledger.json", "Q", 1e12)
    led.charge_process("rehearsal", kind, "main", total)  # rehearsal time counts in the part's charge (ruling L2)
    rec["charged_seconds"] = total
    earlier = {str(Path(x)): core.Ledger(Path(x), "Q", 1e12).charged() for x in (getattr(args, "charged_ledger", None) or [])}  # earlier Part Q ledgers named by the lead (the failed first attempt, the ledger command): their charge belongs to the same total
    rec["charged_ledgers"] = {str(run_dir / "charged_ledger.json"): led.charged(), **earlier}
    rec["charged_before_freeze_seconds"] = led.charged() + sum(earlier.values())  # the caps proposal's pre-freeze charge: this run directory and every ledger named with --charged-ledger
    core.write_record(run_dir / f"rehearsal_{kind}.json", rec, overwrite=True)
    print(json.dumps(rehearsal.whitelist({k: rec[k] for k in ("timings", "memory", "counts", "batches", "generation_items_per_second", "stages", "forced") if k in rec}), default=str))


def identity_probe(plan: Any, repo: Path, run_dir: Path) -> Any:
    """The forced PAUSED — IDENTITY of the counting rehearsal: a copy of the plan with ONE frozen file's hash altered must be refused as PAUSED — IDENTITY; then the real plan must verify (the restore); then the probe
    raises ``StageRefused`` so that the driver records the forced pause. No file is touched."""

    def probe() -> None:
        data = json.loads(json.dumps(plan.data))
        victim = sorted(data["frozen_files"])[0]
        data["frozen_files"][victim] = "0" * 64
        try:
            planmod.verify_plan(planmod.Plan(data, "Q"), repo, Path(plan.data["run_dir"]), candidate=True)  # the PLAN's run directory: the rehearsal runs in its own
        except StageRefused as e:
            if "PAUSED — IDENTITY" not in str(e):
                raise
        else:
            raise RuntimeError("the forced identity difference was not detected")
        planmod.verify_plan(plan, repo, Path(plan.data["run_dir"]), candidate=True)  # restored: the stage resumes
        raise core.ForcedIdentityPause("PAUSED — IDENTITY forced and restored")

    return probe
