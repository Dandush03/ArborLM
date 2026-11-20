# ruff: noqa: E501
"""Part T command line and freeze (ADR-0025 sections 10, 11, 19): ``candidate-plan``, ``caps-proposal``, ``freeze`` and the registered entry points ``registered`` and ``work``.

A registered entry point REFUSES unless the tree is clean, the freeze commit is an ancestor of HEAD and the Part T frozen files equal their content there, the frozen plan and its freeze record exist and agree,
every identity in the plan holds, a COMMITTED Decision 2 for Part T (results/p10is2-partt-freeze-*/DECISION_2_PARTT.md) names the freeze commit, and the run directory is git-ignored or outside the repository.
Nothing is frozen today, so every registered path refuses. Exit codes: 0 done; 2 refused; 75 PAUSED — IDENTITY; 3 returned to the lead (a piece of the scientific core that is not implemented here).

``freeze`` writes only ``freeze/partt_freeze_record.json`` and REFUSES unless: caps not provisional and equal to what the code computes from the Part T measuring rehearsal; the plan equals a re-derivation
from the current code and config; the import walk reaches only listed files; the counting rehearsal names this plan file's SHA-256 and shows every stage COMPLETE, one forced pause and resume and one forced
PAUSED — IDENTITY and restore; the calibration records are not stand-ins, not SUPERSEDED and carry the frozen files' hashes (the repetition used is the one whose hashes equal them, never chosen on its values);
the pilot passed; the Part Q manifest and its ACCEPTANCE record are listed by hash; the shared panel ledger is listed by hash; gate G9 passes; the attestations are given.
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import calibration as cal
from . import partt_caps, partt_plan
from .common import core, gates
from .common import plan as planmod
from .common.caps import caps_match_config
from .common.core import PendingLeadReview, StageRefused

EXIT_REFUSED, EXIT_IDENTITY, EXIT_LEAD, EXIT_INCOMPLETE, EXIT_RECOMPUTATION = 2, planmod.IDENTITY_EXIT, 3, 4, 5  # 4: the stage did not complete (PAUSED or a task failed): see its manifest
REGISTERED_STAGES = partt_plan.STAGES
NOT_IMPLEMENTED = (
    "the arms' training loops over the P10-S2 student, store and LoRA modules (M1, M-append, M-seq, M-ii, D1, D-append, D-seq, M-joint, D-joint, E-table) with the seeded draws of Part Q's manifest",
    "scoring of every snapshot on CPU and the recomputation", "the permutation, marker-only and words-only controls", "the keyword router, GEN readings and route accuracy", "the lookup baselines wired to the Part Q bank (R-gloss-icl through stored segments)",
    "the combined tasks C1 and C2", "the five cost measures' recording", "the Part T gates G1-G8 on real data", "the Part T rehearsals and calibration runs on MPS",
)  # fmt: skip
REHEARSAL_STAGES = partt_plan.STAGES


def repo_of(args: argparse.Namespace | None = None) -> Path:
    r = getattr(args, "repo", None) if args is not None else None
    return Path(r) if r else core.ROOT


def claim_run_dir(run_dir: Path, mode: str, plan_run_dir: str | None = None) -> None:
    """A run directory belongs to ONE mode (registered, rehearsal or calibration), recorded in ``run_mode.json`` the first time and checked every time (audit R15). A rehearsal or a calibration never uses the run
    directory the plan names (the registered one); a registered stage never uses a directory that holds rehearsal or calibration records."""
    if plan_run_dir is not None and mode != "registered" and Path(plan_run_dir).resolve() == run_dir.resolve():
        raise StageRefused(f"refused: {run_dir} is the plan's registered run directory: a {mode} never writes there")
    marker = run_dir / "run_mode.json"
    if marker.is_file():
        have = read_json(marker).get("mode")
        if have != mode:
            raise StageRefused(f"refused: {run_dir} is a {have} run directory; this is a {mode} stage: a directory holds one mode only")
        return
    if run_dir.is_dir() and any(run_dir.iterdir()):
        raise StageRefused(f"refused: {run_dir} holds files but no run_mode.json: a directory holds one mode only and is claimed when it is first used")
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(marker, {"mode": mode, "utc": core.utc_stamp()})


def refuse_unless_registered_ready(repo: Path, run_dir: Path, freeze_commit: str | None, stage: str) -> planmod.Plan:
    if stage not in REGISTERED_STAGES:
        raise StageRefused(f"refused: {stage!r} is not a registered Part T stage")
    cfg = core.load_config("T", repo / core.CONFIG_T)
    gates.apply_platform_settings(cfg)  # configured BEFORE the platform check (see the Part Q entry point)
    planmod.check_preconditions("T", planmod.REGISTERED, repo, freeze_commit, cfg)
    plan = planmod.load_registered_plan(repo, "T")
    planmod.verify_plan(plan, repo, run_dir)
    planmod.require_decision_2(repo, str(freeze_commit), "T")
    core.require_ignored_run_dir(repo, run_dir)
    claim_run_dir(run_dir, "registered")
    problems = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p and os.path.realpath(p) == os.path.realpath(core.DURABLE_PACKAGES)]  # normalized: a trailing slash or a symlink does not slip through
    if problems:
        raise StageRefused("refused: Part T uses the lock alone (section 13 item 6): the durable package copy is on this process's PYTHONPATH")
    return plan


def refuse_unless_rehearsal_ready(repo: Path, run_dir: Path, plan_file: str | None, stage: str, freeze_commit: str | None) -> planmod.Plan:
    """The preconditions of a REHEARSAL stage: those of a registered stage except the three a rehearsal cannot have (a freeze commit, a committed Decision 2, the plan's registered run directory). The platform of
    record, the plan's frozen-file hashes, the config and its caps, the manifests and the Part Q door are checked exactly as for a registered stage, so a plan copy with an altered hash is PAUSED — IDENTITY (exit 75)."""
    if stage not in REGISTERED_STAGES:
        raise StageRefused(f"refused: {stage!r} is not a Part T stage")
    if freeze_commit != "-":
        raise StageRefused("refused: a rehearsal stage takes '-' as its freeze commit; a registered launch never takes --rehearsal")
    if (repo / core.FREEZE_RECORD_T).exists():
        raise StageRefused("refused: a freeze record exists: the rehearsals run BEFORE the freeze, against the candidate plan")
    cfg = core.load_config("T", repo / core.CONFIG_T)
    gates.apply_platform_settings(cfg)
    bad = gates.platform_problems(cfg)
    if bad:
        raise StageRefused("refused: not the platform of record (section 11 item 10): " + "; ".join(bad))
    plan = planmod.Plan.load(Path(plan_file) if plan_file else repo / core.PLAN_T, "T")
    planmod.verify_plan(plan, repo, Path(plan.data["run_dir"]), candidate=True)
    core.require_ignored_run_dir(repo, run_dir)
    claim_run_dir(run_dir, "rehearsal", plan.data["run_dir"])
    problems = [q for q in os.environ.get("PYTHONPATH", "").split(os.pathsep) if q and os.path.realpath(q) == os.path.realpath(core.DURABLE_PACKAGES)]
    if problems:
        raise StageRefused("refused: Part T uses the lock alone (section 13 item 6): the durable package copy is on this process's PYTHONPATH")
    return plan


def plan_for(args: argparse.Namespace, repo: Path, stage: str) -> tuple[planmod.Plan, str]:
    """The plan and the mode of this launch: ``registered`` (freeze, Decision 2) or ``rehearsal`` (``--rehearsal``: the candidate plan). The only branch between the two; everything after it is one path."""
    if getattr(args, "rehearsal", False):
        return refuse_unless_rehearsal_ready(repo, Path(args.run_dir), getattr(args, "plan_file", None), stage, args.freeze_commit), "rehearsal"
    if getattr(args, "plan_file", None) or getattr(args, "pause_after_updates", None) is not None:
        raise StageRefused("refused: --plan-file and --pause-after-updates exist in a rehearsal (--rehearsal) only")
    return refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, stage), "registered"


def execute_stage(args: argparse.Namespace, repo: Path, plan: planmod.Plan, mode: str) -> int:
    """THE stage path, called by a registered launch and by a rehearsal launch with only ``mode`` differing: stage order, the gates, the task runner (task stages) or the stage body, the merges and the completion record."""
    from . import partt_real, partt_tasks

    cfg = core.load_config("T", repo / core.CONFIG_T)
    run_dir = Path(args.run_dir)
    if not (args.stage == "analysis" and partt_real.engineering_failures_of(run_dir)):  # N6: after a recorded engineering failure the analysis needs no recomputation: it records the stop (never a label)
        partt_tasks.require_predecessor(run_dir, args.stage, REGISTERED_STAGES)
    partt_real.require_gates_passed(run_dir, args.stage)
    if args.stage in partt_tasks.TASK_STAGES:
        extra = ["--rehearsal", "--rehearsal-kind", getattr(args, "rehearsal_kind", "counting"), *(["--plan-file", str(args.plan_file)] if getattr(args, "plan_file", None) else [])] if mode == "rehearsal" else []
        man = partt_tasks.run_stage_tasks(args.stage, plan, cfg, repo, run_dir, str(args.freeze_commit), partt_real.qdir_of(plan, Path(args.part_q_dir)), mode=mode, kind=getattr(args, "rehearsal_kind", "counting"), extra=extra, pause_after_updates=getattr(args, "pause_after_updates", None))
        if man["status"] == "COMPLETE":  # the results are merged at the END of the stage that produces them
            if args.stage == "evaluate":
                partt_real.merge_evaluate(run_dir)
            elif args.stage == "combined":
                partt_real.merge_combined(run_dir)
            partt_tasks.mark_complete(run_dir, args.stage, mode)
        print(json.dumps({"stage": args.stage, "status": man["status"], "charged_seconds": man["charged_seconds"]}))
        return 0 if man["status"] == "COMPLETE" else EXIT_INCOMPLETE
    out = partt_real.run_stage(args.stage, repo, run_dir, Path(args.part_q_dir), plan, mode=mode, kind=getattr(args, "rehearsal_kind", "counting"))
    if args.stage == "recompute" and not out.get("ok"):
        print(json.dumps(out))
        return EXIT_RECOMPUTATION  # the failed attempt is kept; nothing is labelled
    partt_tasks.mark_complete(run_dir, args.stage, mode)
    return 0


def cmd_registered(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    plan, mode = plan_for(args, repo, args.stage)
    return execute_stage(args, repo, plan, mode)


def cmd_task(args: argparse.Namespace) -> int:
    """One worker: it re-checks everything the entry point checks (an identity difference exits 75 and writes nothing), then runs its one task."""
    repo = repo_of(args)
    try:
        plan, mode = plan_for(args, repo, args.stage)
    except StageRefused as e:  # a worker never turns a precondition refusal (an untracked note in the worktree, a frozen file, Decision 2) into a failed task and an item error: it PAUSES, the runner records it, restoring the cause resumes
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_IDENTITY
    from . import partt_real

    partt_real.run_task(args.stage, args.task_id, repo, Path(args.run_dir), Path(args.part_q_dir), plan, mode=mode, stop_after=getattr(args, "pause_after_updates", None), kind=getattr(args, "rehearsal_kind", "counting"))
    return 0


def cmd_recompute(args: argparse.Namespace) -> int:
    """The independent recomputation (stage 8): re-score every snapshot on CPU. Exit 0 if it agrees; 5 on ENGINEERING STOP — RECOMPUTATION (nothing is labelled)."""
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, "analysis")
    from . import partt_real

    out = partt_real.run_recompute(repo, Path(args.run_dir), Path(args.part_q_dir), plan, own_code=bool(args.own_code))
    print(json.dumps(out))
    return 0 if out["ok"] else EXIT_RECOMPUTATION


def cmd_timing(args: argparse.Namespace) -> int:
    """Stage 7, the timing benchmark: it runs ALONE (no other process of any study alive), one attempt per invocation; the quiet condition is read before each repetition. Exit 0 if measured, 4 if the attempt
    was incomplete (reschedule it)."""
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, "analysis")
    from . import partt_real, partt_timing

    cfg = core.load_config("T", repo / core.CONFIG_T)
    w, _gloss, _ = partt_real.build_world_real(repo, cfg, Path(args.part_q_dir), plan.data["calibration"], "registered")
    t0 = time.monotonic()
    rec = partt_timing.run_stage(cfg, Path(args.run_dir) / "timing", partt_timing.make_repetition(w, Path(args.run_dir) / "snapshots"))
    core.Ledger(Path(args.run_dir) / "charged_ledger.json", "T", max(1.0, float(cfg["stage_caps"].get("total_hours", 0.0)) * 3600.0) or 1e12).charge_process("timing", "registered", "main", time.monotonic() - t0)
    print(json.dumps(core.jsonable({k: v for k, v in rec.items() if k != "record"}), default=str))
    return 0 if rec["status"] in ("MEASURED", "NOT MEASURED") else EXIT_INCOMPLETE


def cmd_cost(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    plan = refuse_unless_registered_ready(repo, Path(args.run_dir), args.freeze_commit, "analysis")
    from . import partt_real

    print(json.dumps(partt_real.run_cost(repo, Path(args.run_dir), Path(args.part_q_dir), plan)))
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    from . import partt_tasks

    print(json.dumps(partt_tasks.retry(Path(args.run_dir), args.stage, args.task_id, args.cause, bool(args.fix_changes_frozen_file))))
    return 0


REPETITION_RECORD = Path("results/p10is2-partt-calibration/REPETITION.md")


def read_calibration_log(repo: Path) -> list[dict[str, Any]]:
    """The WORKING calibration log (what ``calibrate`` appends to). The plan and the freeze read ``committed_calibration_log`` instead."""
    p = repo / core.CALIBRATION_LOG
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.is_file() else []


def log_calibration(repo: Path, event: dict[str, Any]) -> None:
    """Ruling 21: every calibration session appends a line to the tracked log under ``results/`` (append only)."""
    p = repo / core.CALIBRATION_LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"utc": core.utc_stamp(), **event}, sort_keys=True) + "\n")


def committed_calibration_log(repo: Path) -> list[dict[str, Any]]:
    """Ruling 26: the log as committed at git HEAD, never the working file. Refused if it is not committed, if the working file differs from HEAD, or if its history in git is not append-only (every earlier committed
    version a prefix of the next)."""
    rel = str(core.CALIBRATION_LOG)
    head = core.git(repo, "show", f"HEAD:{rel}")
    if head.returncode != 0:
        raise StageRefused(f"refused: {rel} is not committed at HEAD (ruling 26: the plan and the freeze read the committed log)")
    work = (repo / rel).read_bytes() if (repo / rel).is_file() else b""
    if work != head.stdout:
        raise StageRefused(f"refused: the working {rel} differs from HEAD: commit it (or restore it); the committed log is the one that counts")
    revs = [x for x in core.git(repo, "log", "--format=%H", "--reverse", "--", rel).stdout.decode().split() if x]
    texts = [core.git(repo, "show", f"{r}:{rel}").stdout for r in revs]
    for older, newer in zip(texts, texts[1:], strict=False):
        if not newer.startswith(older):
            raise StageRefused(f"refused: the history of {rel} in git is not append-only (a committed version is not a prefix of the next)")
    return [json.loads(x) for x in head.stdout.decode("utf-8").splitlines() if x.strip()]


def repetition_record_problems(repo: Path) -> list[str]:
    """Ruling 26: ``second/`` is used only when a COMMITTED lead record names the reason and the commit of the code change that forced the repetition; the commit must exist and be an ancestor of HEAD."""
    rel = str(REPETITION_RECORD)
    got = core.git(repo, "show", f"HEAD:{rel}")
    if got.returncode != 0:
        return [f"{rel} is not committed at HEAD"]
    import re

    text = got.stdout.decode("utf-8")
    reason = re.search(r"(?mi)^reason:\s*(\S.*)$", text)
    commit = re.search(r"(?mi)^commit:\s*([0-9a-f]{40})\s*$", text)
    out = []
    if not reason:
        out.append(f"{rel} names no reason (a line 'reason: ...')")
    if not commit:
        out.append(f"{rel} names no 40-hex commit of the code change that forced the repetition (a line 'commit: <sha>')")
    elif core.git(repo, "merge-base", "--is-ancestor", commit.group(1), "HEAD").returncode != 0:
        out.append(f"the commit {commit.group(1)} named in {rel} is not an ancestor of HEAD")
    return out


def calibration_record_paths(repo: Path) -> dict[int, Path]:
    d = core.calibration_dir(repo)
    return {0: d / "calibration_0.json", 1: d / "second" / "calibration_1.json"}


def chosen_calibration(repo: Path) -> tuple[Path, int]:
    """The record the plan takes: only the one calibration directory's, by ``calibration.repetition_used`` (the repetition whose code hashes equal the frozen files; the first when both do), never by its values. The
    second is used only under a committed lead record (ruling 26): a code edit alone never switches the record."""
    d = core.calibration_dir(repo)
    if not d.is_dir():
        raise StageRefused(f"refused: the calibration directory {d} does not exist (ruling 21: the plan takes only that directory's record)")
    paths = {i: p for i, p in calibration_record_paths(repo).items() if p.is_file()}
    if not paths:
        raise StageRefused(f"refused: no calibration record in {d}")
    frozen = planmod.frozen_file_hashes(repo, "T")
    files = [f for f in frozen if f.startswith("studies/p10is2/") and f.endswith(".py")]
    used = cal.repetition_used({i: core.read_record(p, "calibration") for i, p in paths.items()}, frozen, files)
    if used["used"] is None:
        raise StageRefused("refused: " + used["refused"])
    if int(used["used"]) == 1:
        problems = repetition_record_problems(repo)
        if problems:
            raise StageRefused("refused: the second calibration is used only under a committed lead record (ruling 26): " + "; ".join(problems))
    return paths[used["used"]], int(used["used"])


def check_calibration_ledger(repo: Path, log: list[dict[str, Any]]) -> None:
    """Ruling 26: the calibration ledger's sessions against the logged ones: every ledger entry belongs to a logged session (its ``run`` is the session's start UTC), and every logged session has an entry or is followed by an
    INTERRUPTED line (a killed process charges nothing)."""
    led = core.Ledger(core.calibration_dir(repo) / "charged_ledger.json", "T", 1e12)
    ran = {e["run"] for e in led.entries() if e["stage"] == "calibration"}
    sessions = [e["session"] for e in log if e.get("event") == "start"]
    interrupted_after: set[str | None] = set()
    stray = sorted(ran - set(sessions))
    if stray:
        raise StageRefused(f"refused: the calibration ledger holds sessions the log does not list: {stray}")
    last_session: str | None = None
    for e in log:
        if e.get("event") == "start":
            last_session = e["session"]
        elif e.get("event") == "INTERRUPTED":
            interrupted_after.add(last_session)
    missing = [x for x in sessions if x not in ran and x not in interrupted_after]
    if missing:
        raise StageRefused(f"refused: logged calibration sessions with no ledger entry and no INTERRUPTED line: {missing}")


def check_study_budget(cfg: Any, total_hours: float, allowance_hours: float) -> None:
    """Ruling 30: if the counting allowance makes the plan's total cap exceed the study's budget bound, the candidate plan (and the registered caps) refuse and it goes to the human lead; no automatic extension. A bound of 0.0 is
    'not set' (the human lead sets it)."""
    budget = float(cfg["caps"].get("study_budget_hours", 0.0))
    if budget > 0.0 and total_hours > budget:
        raise StageRefused(f"refused: PENDING LEAD REVIEW: the plan's total cap {total_hours} h exceeds the study's budget bound {budget} h (the counting allowance is {allowance_hours} h): the human lead decides; nothing is extended here")


def session_identity(repo: Path) -> dict[str, str]:
    """Ruling 28: the hashes of the files a calibration computes with (every ``studies/p10is2/*.py``) and of the config. Each session's start line carries them; a resume refuses when they differ from the first session's, and
    the final record's must equal every session's."""
    frozen = planmod.frozen_file_hashes(repo, "T")
    return {k: v for k, v in sorted(frozen.items()) if (k.startswith("studies/p10is2/") and k.endswith(".py")) or k == str(core.CONFIG_T)}


def open_session(log: Sequence[dict[str, Any]], rep: int) -> dict[str, Any] | None:
    """The OPEN start line of a repetition: an ``open`` start with no ``end`` after it."""
    opened = None
    for e in log:
        if e.get("repetition") != rep:
            continue
        if e.get("event") == "start" and e.get("open"):
            opened = e
        elif e.get("event") == "end":
            opened = None
    return opened


def line_sha(event: dict[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()


def committed_head_log(repo: Path) -> list[dict[str, Any]]:
    """The log at HEAD for a RUN (``calibrate`` without ``--open``): committed, its history append-only; the working file must extend it (the lines of a stopped session, appended after the commit, are allowed)."""
    rel = str(core.CALIBRATION_LOG)
    head = core.git(repo, "show", f"HEAD:{rel}")
    if head.returncode != 0:
        raise StageRefused(f"refused: {rel} is not committed at HEAD: run `calibrate --open`, and the lead commits the log, before any unit runs (ruling 29)")
    work = (repo / rel).read_bytes() if (repo / rel).is_file() else b""
    if not work.startswith(head.stdout):
        raise StageRefused(f"refused: the working {rel} does not extend HEAD's (it was changed or checked out): the committed log is the one that counts")
    revs = [x for x in core.git(repo, "log", "--format=%H", "--reverse", "--", rel).stdout.decode().split() if x]
    texts = [core.git(repo, "show", f"{r}:{rel}").stdout for r in revs]
    for older, newer in zip(texts, texts[1:], strict=False):
        if not newer.startswith(older):
            raise StageRefused(f"refused: the history of {rel} in git is not append-only")
    extra = work[len(head.stdout) :].decode("utf-8")
    if any(json.loads(x).get("event") == "end" or json.loads(x).get("open") for x in extra.splitlines() if x.strip()):
        raise StageRefused(f"refused: the working {rel} holds an end line or an open start line HEAD does not: commit it first (the lead commits the end line before the plan)")
    return [json.loads(x) for x in head.stdout.decode("utf-8").splitlines() if x.strip()]


def cmd_calibrate(args: argparse.Namespace) -> int:
    """ONE calibration (ruling 21), in two steps (ruling 29). ``calibrate --open``: the tracked log must be clean and equal to HEAD; it appends the session's start line (with the code and config hashes, ruling 28) and
    exits without running a unit; the lead commits it. ``calibrate``: refuses unless HEAD's log carries an open start line for the repetition (the working file extending it) and the calibration directory's state is
    consistent with the log; it then runs, PAUSED when it stops and resumable by the same command with no new commit (ruling 25): the INTERRUPTED line is appended and the same open session continues, from the stored
    per-unit state, under the same code (a resume under other code is refused: that is the single recorded repetition, ruling 26). The end line is committed by the lead before the plan."""
    from . import partt_real

    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    d = core.calibration_dir(repo)
    rep = int(args.repetition)
    cap_h = float(cfg["stage_caps"]["calibration_hours"])
    if cap_h <= 0.0:
        raise StageRefused("refused: the calibration cap is 0 (never 'uncapped'): write it from the measuring rehearsal first (caps-config --phase calibration)")
    log = read_calibration_log(repo)
    if any(e.get("event") == "end" and e.get("repetition") == rep for e in log):
        raise StageRefused(f"refused: the calibration for repetition {rep} is complete (an end line is in {core.CALIBRATION_LOG}): there is ONE calibration; its single repetition is second/ under a committed lead record, the first is kept")
    if rep == 1:
        if not any(e.get("event") == "end" and e.get("repetition") == 0 for e in log):
            raise StageRefused("refused: the single repetition (section 7.1 rule 4) needs a completed first calibration")
        problems = repetition_record_problems(repo)
        if problems:
            raise StageRefused("refused: the single repetition needs a committed lead record (ruling 26): " + "; ".join(problems))
    sub_dir = d if rep == 0 else d / "second"
    identity = session_identity(repo)
    if args.open:
        if open_session(log, rep) is not None:
            raise StageRefused(f"refused: a session for repetition {rep} is already open in {core.CALIBRATION_LOG}: run it (or resume it); no second start line")
        rel = str(core.CALIBRATION_LOG)
        if core.git(repo, "show", f"HEAD:{rel}").returncode == 0:
            committed_calibration_log(repo)  # clean, equal to HEAD, append-only
        elif (repo / rel).is_file() and (repo / rel).read_bytes():
            raise StageRefused(f"refused: {rel} holds lines that are not committed: the log must be clean before a session is opened")
        core.require_ignored_run_dir(repo, d)
        claim_run_dir(d, "calibration", None)
        sub_dir.mkdir(parents=True, exist_ok=True)
        session = core.utc_stamp()
        event = {"event": "start", "repetition": rep, "session": session, "open": True, "resumed": False, "identity": identity, "directory": str(sub_dir), "cap_seconds": cap_h * 3600.0}
        log_calibration(repo, event)
        written = read_calibration_log(repo)[-1]
        write_json(sub_dir / "session.json", {"session": session, "repetition": rep, "start_line_sha256": line_sha(written)})
        print(json.dumps({"opened": session, "next": f"commit {core.CALIBRATION_LOG}, then run calibrate (without --open)"}))
        return 0
    if not args.part_q_plan:
        raise StageRefused("refused: calibrate needs --part-q-plan: the checked door admits generation/result.json through Part Q's plan reuse list")
    head_log = committed_head_log(repo)
    opened = open_session(head_log, rep)
    if opened is None:
        raise StageRefused(f"refused: HEAD's {core.CALIBRATION_LOG} holds no open start line for repetition {rep}: `calibrate --open`, then the lead commits it (ruling 29); no unseen redraw")
    marker = sub_dir / "session.json"
    if not marker.is_file() or json.loads(marker.read_text()).get("session") != opened["session"] or json.loads(marker.read_text()).get("start_line_sha256") != line_sha(opened):
        raise StageRefused(f"refused: the calibration directory {sub_dir} does not hold the session HEAD's log opened (a deleted or replaced directory under a log that lists a session): the lead decides")
    after_open = log[log.index(opened) + 1 :] if opened in log else []
    listed = {e["unit"] for e in after_open if e.get("event") == "unit"}
    state_dir = sub_dir / "state"
    on_disk = {p.stem for p in state_dir.glob("*.json")} if state_dir.is_dir() else set()
    if listed - on_disk:
        raise StageRefused(f"refused: the log lists finished units whose state is not in {state_dir} (a deleted or emptied directory): {sorted(listed - on_disk)[:3]}")
    session_events = [e for e in after_open if e.get("repetition") == rep]
    resumed = bool(session_events)
    if resumed and opened.get("identity") != identity:
        differ = sorted(k for k in set(opened.get("identity") or {}) | set(identity) if (opened.get("identity") or {}).get(k) != identity.get(k))
        raise StageRefused(f"refused: a resume under other code or config than the session's first start line (ruling 28): {differ[:4]}; that is the single recorded repetition (second/ under a committed lead record), never a silent continue")
    led = core.Ledger(d / "charged_ledger.json", "T", 1e12)
    remaining = cap_h * 3600.0 - led.charged("calibration")
    if remaining <= 0:
        raise StageRefused("refused: the calibration cap is spent (PAUSED): an extension is the lead's")
    for unit_id in sorted(on_disk - listed):  # state written, its log line not (a stop between the two): reconciled, never redrawn
        log_calibration(repo, {"event": "unit", "repetition": rep, "session": opened["session"], "unit": unit_id, "reconciled": True})
    if resumed:  # the reason found is logged, nothing is edited by hand
        last = next((e for e in reversed(session_events) if e.get("event") in ("stopped", "start", "end")), session_events[-1])
        reason = str(last.get("error")) if last.get("event") == "stopped" and last.get("error") else "UNKNOWN"
        log_calibration(repo, {"event": "INTERRUPTED", "repetition": rep, "reason": reason, "after": last.get("event")})
        session = core.utc_stamp()
        log_calibration(repo, {"event": "start", "repetition": rep, "session": session, "open": False, "resumed": True, "identity": identity, "directory": str(sub_dir), "remaining_seconds": remaining})
    else:
        session = str(opened["session"])
    t0 = time.monotonic()
    try:
        out = partt_real.calibrate_command(repo, Path(args.part_q_dir), sub_dir, rep, Path(args.part_q_plan), remaining, on_unit=lambda uid: log_calibration(repo, {"event": "unit", "repetition": rep, "session": session, "unit": uid}))
        record = core.read_record(sub_dir / f"calibration_{rep}.json", "calibration")
        now = session_identity(repo)
        starts = [e for e in read_calibration_log(repo) if e.get("event") == "start" and e.get("repetition") == rep]
        bad = [e["session"] for e in starts if e.get("identity") != now]
        wrong = sorted(k for k in now if (record.get("code_hashes") or {}).get(k) != now[k])
        if bad or wrong:
            raise StageRefused(f"refused: the final record's code and config hashes must equal every session's (ruling 28): sessions {bad}, record {wrong[:3]}")
    except BaseException as e:
        log_calibration(repo, {"event": "stopped", "repetition": rep, "session": session, "error": f"{type(e).__name__}: {e}"[:300]})
        raise
    finally:
        charged(d / "charged_ledger.json", "calibration", session, time.monotonic() - t0)
    log_calibration(repo, {"event": "end", "repetition": rep, "session": session, "record": str(sub_dir / f"calibration_{rep}.json"), "record_sha256": file_sha256(sub_dir / f"calibration_{rep}.json")})
    print(json.dumps(core.jsonable(out), default=str))
    return 0


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The Part T rehearsals, driven through the registered entry point (``partt_counting``): one fresh process per stage invocation, the stage's tasks as worker processes, in a run directory of the rehearsal's own."""
    from . import partt_counting

    repo = repo_of(args)
    if args.kind == "measuring":
        rec = partt_counting.run_measuring_rehearsal(repo, Path(args.run_dir), Path(args.part_q_dir), part_q_plan=Path(args.part_q_plan) if args.part_q_plan else None, manifests=read_json(Path(args.manifests)) if args.manifests else None, charged_ledgers=args.charged_ledger)
    else:
        rec = partt_counting.run_counting_rehearsal(repo, Path(args.run_dir), charged_ledgers=args.charged_ledger)
    print(json.dumps({k: rec[k] for k in ("kind_of_rehearsal", "status", "stages", "forced", "rates_seconds_per_unit", "overhead_seconds") if k in rec}, default=str))
    return 0


def differing_paths(a: Any, b: Any, path: str = "") -> list[str]:
    """The paths at which two parsed JSON values differ (a path present in one only counts)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            out += [f"{path}.{k}"] if (k not in a or k not in b) else differing_paths(a[k], b[k], f"{path}.{k}")
        return out
    return [] if a == b else [path or "."]


def calibration_from_record(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    """The plan's calibration block, taken from the calibration's OWN record file by hash, never from a hand-assembled file (ruling 13): U, the rates, the layer, the pilot and the code hashes it carries, and the
    record's path and SHA-256. A stand-in record, a superseded one or one that records a repetition reason without the record it supersedes is refused."""
    sha = file_sha256(path)
    if expected_sha is not None and sha != expected_sha:
        raise StageRefused(f"refused: the calibration record {path} differs from the hash in the plan (PAUSED — IDENTITY)")
    rec = core.read_record(path, "calibration")
    if rec.get("stand_in") or rec.get("superseded"):
        raise StageRefused(f"refused: {path} is a stand-in or superseded calibration record")
    block = {k: rec[k] for k in ("store_rate", "lora_rate", "etable_rate", "read_layer", "U", "converged", "pilot") if k in rec}
    block["records"] = {path.stem: {"code_hashes": rec.get("code_hashes") or {}}}
    block["record"] = {"path": str(path.resolve()), "sha256": sha, "repetition": rec.get("repetition")}
    return block


def part_q_block(qdir: Path, part_q_plan: Path | None) -> dict[str, Any]:
    """What the Part T plan records of Part Q: the run directory of record, its manifest and (for the files of reused stages) Part Q's plan, each by path and SHA-256 (rulings 6 and 10)."""
    man = qdir / "manifest.json"
    if not man.is_file():
        raise StageRefused(f"refused: {man} does not exist")
    out: dict[str, Any] = {"run_dir": str(qdir.resolve()), "manifest": {"path": str(man.resolve()), "sha256": file_sha256(man)}}
    if part_q_plan is not None:
        out["plan"] = {"path": str(part_q_plan.resolve()), "sha256": file_sha256(part_q_plan)}
    return out


def ledgers_charge(paths: Sequence[str]) -> dict[str, Any]:
    """The charge before the freeze: the sum of every named Part T ledger, each listed (a path that is not absolute or does not exist is refused)."""
    per: dict[str, float] = {}
    for x in paths:
        pth = Path(x)
        if not pth.is_absolute() or not pth.is_file():
            raise StageRefused(f"refused: --charged-ledger {x} must be the absolute path of an existing charged_ledger.json")
        per[str(pth)] = core.Ledger(pth, "T", 1e12).charged()
    return {"seconds": sum(per.values()), "ledgers": per}


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    committed_calibration_log(repo)  # ruling 26: the log is committed, clean and append-only
    cal_path, _rep = chosen_calibration(repo)  # ruling 21: no free path; the record of the one calibration directory
    calib = calibration_from_record(cal_path)
    walk = planmod.import_walk(repo, "T")
    manifests = read_json(Path(args.manifests)) if args.manifests else {}
    meas_path = Path(args.measuring_rehearsal)
    meas = core.read_record(meas_path, "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: --measuring-rehearsal must be the Part T measuring rehearsal's record")
    ledgers = sorted({*[str(Path(x)) for x in (meas.get("charged_ledgers") or {})], str(core.calibration_dir(repo) / "charged_ledger.json"), *args.charged_ledger})
    charge = ledgers_charge(ledgers)  # the charge before the freeze: the measuring rehearsal's and the calibration's ledgers by rule, plus any named
    pin = {"path": str(meas_path.resolve()), "sha256": file_sha256(meas_path)}
    pq = part_q_block(Path(args.part_q_dir), Path(args.part_q_plan) if args.part_q_plan else None)
    allowance = partt_caps.counting_allowance_hours(meas, partt_plan.stage_items(calib), int(calib["U"]))  # ruling 20 at the calibrated U (ruling 27): fixed in the plan BEFORE the counting rehearsal runs
    rec = partt_plan.build_candidate(repo, Path(args.run_dir).resolve(), cfg, calib, walk=walk, manifests=manifests, charge_before_freeze=charge, part_q=pq, counting_allowance_hours=allowance, measuring_rehearsal=pin)
    check_study_budget(cfg, float(cfg["stage_caps"].get("total_hours", 0.0)), allowance)
    path = repo / core.PLAN_T
    if path.exists():
        if not args.supersede:
            raise StageRefused(f"refused: {path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / core.FREEZE_RECORD_T).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(path)
        target = path.parent / "superseded" / f"partt_plan-{old[:12]}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        path.rename(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, core.jsonable(rec))
    print(json.dumps({"candidate_plan": str(path), "plan_file_sha256": file_sha256(path), "items": {k: len(v) for k, v in rec["items"].items()}}))
    return 0


def cmd_caps_proposal(args: argparse.Namespace) -> int:
    """The caps by the rule from the measuring record (nothing typed). ``--phase calibration``: the cap for calibration only (2 x the projected calibration charge; no plan exists yet). Default: the registered stages' caps and the
    total from the PLAN's own task units, the charge before the freeze and the counting allowance the plan recorded, plus the calibration cap."""
    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps are computed from a MEASURING rehearsal's record")
    cal_h = partt_caps.calibration_cap_hours(meas, cfg)
    if getattr(args, "phase", "registered") == "calibration":
        print(json.dumps({"proposal_hours": {"calibration_hours": cal_h}, "rule": "calibration cap = 2 x the projected calibration charge (measured per-update rates x the calibration units, plus D_cal scoring)"}))
        return 0
    plan = planmod.Plan.load(repo / core.PLAN_T, "T")
    charge = float((plan.data.get("charge_before_freeze") or {}).get("seconds", 0.0))
    allowance = float(plan.data.get("counting_allowance_hours", 0.0)) * 3600.0
    prop = partt_caps.proposal_from_record(meas, plan.data["items"], plan.data["task_units_basis"], charge, allowance)
    print(json.dumps({"proposal_hours": {"calibration_hours": cal_h, **prop}, "charge_before_freeze_seconds": charge, "counting_allowance_seconds": allowance, "rule": "stage cap = 2 x projected; total = plan charge + counting allowance + 2 x all registered stages, rounded up to 0.01 h"}))
    return 0


def cmd_caps_config(args: argparse.Namespace) -> int:
    """Writes the caps into ``[stage_caps]`` by the shared function (no hand entry). ``--phase calibration`` (BEFORE calibration, ruling 22): ``calibration_hours`` only. The registered phase (after calibration and the candidate
    plan): every other cap and ``caps.provisional = false``; it refuses unless the calibration cap in the config is the one the record gives. The candidate plan must be rebuilt afterwards."""
    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring":
        raise StageRefused("refused: the caps come from a MEASURING rehearsal's record")
    cal_h = partt_caps.calibration_cap_hours(meas, cfg)
    path = repo / core.CONFIG_T
    if getattr(args, "phase", "registered") == "calibration":
        if args.apply:
            path.write_text(partt_caps.apply_caps_text(path.read_text(encoding="utf-8"), {"calibration_hours": cal_h}, final=False), encoding="utf-8")
            print(json.dumps({"config": str(path), "applied": {"calibration_hours": cal_h}, "next": "commit the config, then calibrate"}))
        else:
            print(f"calibration_hours = {cal_h}")
        return 0
    if abs(float(cfg["stage_caps"]["calibration_hours"]) - cal_h) > 1e-9:
        raise StageRefused(f"refused: the calibration cap in the config ({cfg['stage_caps']['calibration_hours']}) is not the one the measuring record gives ({cal_h}): write it with --phase calibration first")
    plan = planmod.Plan.load(repo / core.PLAN_T, "T")
    charge = float((plan.data.get("charge_before_freeze") or {}).get("seconds", 0.0))
    proposal = partt_caps.proposal_from_record(meas, plan.data["items"], plan.data["task_units_basis"], charge, float(plan.data.get("counting_allowance_hours", 0.0)) * 3600.0)
    check_study_budget(cfg, float(proposal["total_hours"]), float(plan.data.get("counting_allowance_hours", 0.0)))
    if args.apply:
        path.write_text(partt_caps.apply_caps_text(path.read_text(encoding="utf-8"), proposal), encoding="utf-8")
        print(json.dumps({"config": str(path), "applied": proposal, "next": "commit the config, candidate-plan --supersede, the counting rehearsal, the freeze"}))
    else:
        print("\n".join(f"{k} = {v}" for k, v in proposal.items()))
    return 0


def counting_charge_of(counting: dict[str, Any]) -> float:
    """The counting rehearsal's charge, READ from its own ledger (the file the record names, re-read now) and checked against what the record says (ruling 17)."""
    ledgers = counting.get("charged_ledgers") or {}
    own = next((p for p in ledgers if p.endswith("charged_ledger.json")), None)
    if own is None or not Path(own).is_file():
        raise StageRefused("refused: the counting rehearsal's record names no ledger that exists: its charge cannot be read (ruling 17)")
    seconds = core.Ledger(Path(own), "T", 1e12).charged()
    if abs(seconds - float(counting.get("charged_seconds", -1.0))) > 1e-6:
        raise StageRefused(f"refused: the counting rehearsal's ledger holds {seconds} s but its record says {counting.get('charged_seconds')} s")
    return seconds


def charged(ledger: Path, stage: str, mode: str, seconds: float) -> None:
    """One Part T ledger: every Part T process (calibration and its repetitions, the rehearsals, a counting rehearsal) charges its wall time, also when it fails."""
    core.Ledger(ledger, "T", 1e12).charge_process(stage, mode, "main", seconds)


def cmd_freeze(args: argparse.Namespace) -> int:
    repo = repo_of(args)
    cfg = core.load_config("T", repo / core.CONFIG_T)
    plan_path, record = repo / core.PLAN_T, repo / core.FREEZE_RECORD_T
    if record.exists():
        raise StageRefused(f"refused: {record} exists; a freeze is written once")
    plan = planmod.Plan.load(plan_path, "T")
    if cfg["caps"]["provisional"] or plan.data.get("caps_provisional"):
        raise StageRefused("refused: caps.provisional is true: the caps are computed by code from the Part T measuring rehearsal and set before the freeze")
    plan_sha = file_sha256(plan_path)
    meas = core.read_record(Path(args.measuring_rehearsal), "rehearsal")
    if meas.get("kind_of_rehearsal") != "measuring" or meas.get("caps_provisional") is not True:
        raise StageRefused("refused: --measuring-rehearsal must be the Part T measuring rehearsal's record")
    if meas.get("status") == "INCOMPLETE" or meas.get("problems"):
        raise StageRefused(f"refused: the measuring rehearsal's record is INCOMPLETE ({meas.get('problems')}): caps are computed from a complete measurement of every kind")
    pin = plan.data.get("measuring_rehearsal")
    if not pin or pin.get("sha256") != file_sha256(Path(args.measuring_rehearsal)) or Path(pin["path"]).resolve() != Path(args.measuring_rehearsal).resolve():
        raise StageRefused("refused: the plan does not pin this measuring record by SHA-256 (candidate-plan --measuring-rehearsal): one measuring record, the one the plan names")
    zero = partt_caps.zero_caps(cfg, REGISTERED_STAGES)
    if float(cfg["stage_caps"].get("calibration_hours", 0.0)) <= 0.0:
        zero = [*zero, "calibration"]
    if zero:
        raise StageRefused(f"refused: stage cap(s) of 0 in the config ({zero}): a cap of 0 is never 'uncapped'; every registered stage has a cap by the rule")
    charge = plan.data.get("charge_before_freeze") or {}
    if not charge.get("seconds"):
        raise StageRefused("refused: the plan records no charge before the freeze (candidate-plan --charged-ledger): the caps' total counts it")
    if "counting_allowance_hours" not in plan.data:
        raise StageRefused("refused: the plan carries no counting allowance (candidate-plan --measuring-rehearsal, ruling 20): re-plan with --supersede")
    allowance_h = float(plan.data["counting_allowance_hours"])
    if abs(allowance_h - partt_caps.counting_allowance_hours(meas, plan.data["items"], int(plan.data["calibration"]["U"]))) > 1e-9:
        raise StageRefused("refused: the plan's counting allowance is not 2 x the counting charge projected from this measuring record: re-plan with --supersede (no cap is edited by hand)")
    proposal = partt_caps.proposal_from_record(meas, plan.data["items"], plan.data["task_units_basis"], float(charge["seconds"]), allowance_h * 3600.0)  # the units come from the plan; the charge and the allowance are the ones the plan recorded
    proposal = {"calibration_hours": partt_caps.calibration_cap_hours(meas, cfg), **proposal}
    differ = caps_match_config(cfg, proposal)
    if differ:
        raise StageRefused("refused: the config's stage caps are not what the code computes from the measuring rehearsal: " + "; ".join(differ))
    walk = planmod.import_walk(repo, "T")
    crec = plan.data["calibration"]["record"]
    chosen, chosen_rep = chosen_calibration(repo)  # ruling 21: only the one calibration directory's record, by the rule, never another
    if Path(crec["path"]).resolve() != chosen.resolve():
        raise StageRefused(f"refused: the plan's calibration record {crec['path']} is not the record of the one calibration directory ({chosen})")
    clog = committed_calibration_log(repo)  # ruling 26: from git HEAD, clean, append-only
    check_calibration_ledger(repo, clog)
    if not any(e.get("event") == "end" and e.get("repetition") == chosen_rep and e.get("record_sha256") == crec["sha256"] for e in clog):
        raise StageRefused(f"refused: no calibration session in {core.CALIBRATION_LOG} lists this record (an unlisted session)")
    calib = calibration_from_record(chosen, crec["sha256"])  # U, the rates, the layer and the pilot come from the calibration's own record, by hash
    ledgers_now = ledgers_charge(list((charge.get("ledgers") or {}).keys()))
    if abs(ledgers_now["seconds"] - float(charge["seconds"])) > 1e-6:  # the charge before the freeze is RE-DERIVED from the ledgers, never taken from the plan
        raise StageRefused(f"refused: the plan's charge before the freeze ({charge['seconds']} s) is not the sum of its ledgers now ({ledgers_now['seconds']} s)")
    required = {str(Path(x)) for x in (meas.get("charged_ledgers") or {})} | {str(core.calibration_dir(repo) / "charged_ledger.json")}
    if required - set(ledgers_now["ledgers"]):
        raise StageRefused(f"refused: the plan's ledgers omit {sorted(required - set(ledgers_now['ledgers']))}: the measuring rehearsal's and the calibration's ledgers are part of the charge")
    if core.Ledger(core.calibration_dir(repo) / "charged_ledger.json", "T", 1e12).charged("calibration") > float(cfg["stage_caps"]["calibration_hours"]) * 3600.0 + 1e-6:
        raise StageRefused("refused: calibration charged more than its cap")
    rederived = partt_plan.build_candidate(repo, Path(plan.data["run_dir"]), cfg, calib, mode=plan.data["mode"], walk=walk, manifests=plan.data.get("manifests"), charge_before_freeze=ledgers_now, part_q=plan.data.get("part_q"), counting_allowance_hours=allowance_h, measuring_rehearsal=pin)
    differing = differing_paths(json.loads(json.dumps(core.jsonable({k: v for k, v in rederived.items() if k not in ("adr", "platform")}))), {k: v for k, v in plan.data.items() if k not in ("adr", "platform")})
    if differing:
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code, config and calibration record in: " + ", ".join(differing[:10]) + ": supersede it, repeat calibration if a training or scoring file changed (section 7.1 rule 4), and rehearse again")
    now_charge = ledgers_charge(list((charge.get("ledgers") or {}).keys()))
    lost = [k for k, v in (charge.get("ledgers") or {}).items() if now_charge["ledgers"][k] < float(v) - 1e-6]
    if lost:
        raise StageRefused("refused: a ledger the plan's charge before the freeze was taken from holds less now: " + ", ".join(lost))
    wp = planmod.walk_problems(walk, plan.data["frozen_files"], repo)
    if wp:
        raise StageRefused("refused: " + "; ".join(wp))
    files = [f for f in plan.data["frozen_files"] if f.startswith("studies/p10is2/") and f.endswith(".py")]
    records = calib.get("records") or {}
    bad = ["the plan carries no calibration records"] if not records else [f"{n}: {p}" for n, rec in records.items() for p in cal.code_identity_problems(rec, plan.data["frozen_files"], files)]
    if bad:
        raise StageRefused("refused: the calibration records do not match the frozen files: " + "; ".join(bad[:4]))
    from .partt_door import PartQDoor

    if not plan.data.get("part_q"):
        raise StageRefused("refused: the plan names no Part Q run directory of record (--part-q-dir): Part T reads Part Q through one checked door")
    PartQDoor.from_plan(plan.data["part_q"])  # Part Q's manifest (and plan) are the hashes the plan recorded
    for name in ("part_q_acceptance", "panel_ledger"):
        m = (plan.data.get("manifests") or {}).get(name)
        p = None if not m else (Path(m["path"]) if Path(m["path"]).is_absolute() else repo / m["path"])
        if p is None or not p.is_file() or file_sha256(p) != m["sha256"]:
            raise StageRefused(f"refused: the plan does not list {name} by a hash that holds (Part T reads the Part Q manifest's files only, by hash: ruling L12)")
    counting = core.read_record(Path(args.counting_rehearsal), "rehearsal")
    reh = gates.rehearsal_gate(counting, REHEARSAL_STAGES, plan_file_sha256=plan_sha)
    mps = counting.get("g4_mps") or {}
    if mps.get("passed") is not True or (counting.get("platform") or {}).get("machine") != gates.platform_record()["machine"] or (counting.get("platform") or {}).get("system") != gates.platform_record()["system"]:
        raise StageRefused(f"refused: gate G4 MPS against CPU must have RUN and PASSED on this machine before the freeze (a skipped gate is not a pass); the counting rehearsal's record has: {mps}")
    if not reh["passed"]:
        raise StageRefused(f"refused: the counting rehearsal's record does not show every stage COMPLETE, one forced pause and resume, one forced PAUSED — IDENTITY and restore, and this plan file's SHA-256: {reh}")
    counting_charge = counting_charge_of(counting)  # ruling 17: read from the counting rehearsal's ledger, recorded, added to the pre-freeze charge the registered ledger starts from
    plan_charge = float(charge["seconds"])
    total_cap = float(cfg["stage_caps"]["total_hours"]) * 3600.0
    if counting_charge > allowance_h * 3600.0 + 1e-6:  # ruling 20: ENGINEERING STOP; the plan is re-made with --supersede, no cap is edited by hand
        raise StageRefused(f"refused: ENGINEERING STOP: the counting rehearsal charged {counting_charge:.1f} s, above the counting allowance of {allowance_h * 3600.0:.1f} s fixed in the plan before it ran: re-plan with --supersede")
    need = plan_charge + counting_charge
    attest = [x for x in args.attest_sealed_unopened.split(",") if x]
    if not args.seal_broken and set(attest) != {"lead", "implementer", "auditor"}:
        raise StageRefused("refused: the record must state, for the lead, the implementer and the auditor, that none has opened a sealed value, or declare the seal broken")
    seed = gates.seed_gate("T", cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: gate G9 did not pass: {seed['problems']}")
    rec = {
        **core.envelope("freeze_record", "T"), "plan_file_sha256": plan_sha, "counting_rehearsal": {"path": str(Path(args.counting_rehearsal).resolve()), "sha256": file_sha256(Path(args.counting_rehearsal))},
        "attestations": {"sealed_values_unopened_by": attest}, "seal_broken": bool(args.seal_broken), "seed_gate": seed, "rehearsal_gate": reh, "caps_by_code": proposal, "adr_hash_provenance_only": plan.data["adr"]["sha256"],
        "pre_freeze_charge": {"plan_seconds": plan_charge, "counting_rehearsal_seconds": counting_charge, "counting_allowance_seconds": allowance_h * 3600.0, "registered_ledger_starts_from_seconds": need, "total_cap_seconds": total_cap},
    }  # fmt: skip
    record.parent.mkdir(parents=True, exist_ok=True)
    write_json(record, core.jsonable(rec))
    print(json.dumps({"freeze_record": str(record), "sha256": file_sha256(record), "plan_file_sha256": plan_sha}))
    return 0


def add_rehearsal_flags(r: argparse.ArgumentParser) -> None:
    r.add_argument("--rehearsal", action="store_true", help="a rehearsal stage: the candidate plan, '-' for the freeze commit, no Decision 2, rehearsal seeds, the plan-derived subset, D_cal only")
    r.add_argument("--rehearsal-kind", choices=("measuring", "counting"), default="counting", help="rehearsal only: which rehearsal's fixed cap applies")
    r.add_argument("--plan-file", help="rehearsal only: a plan file other than freeze/partt_plan.json (the measuring rehearsal's own plan, the forced identity check)")
    r.add_argument("--pause-after-updates", type=int, help="rehearsal only: the forced pause (the cell train|M1|AB|r0 stops after this many updates, exits 74; the same command resumes it)")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="studies.p10is2.partt_stages", description="P10IS2 Part T (ADR-0025). Registered entry points refuse until a freeze record and a committed Decision 2 exist.")
    sub = ap.add_subparsers(dest="command", required=True)
    cp = sub.add_parser("candidate-plan")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--manifests", help="JSON naming part_q_acceptance and panel_ledger by path and SHA-256")
    cp.add_argument("--part-q-dir", required=True, help="Part Q's run directory of record (attempt 3): named in the plan; its manifest is listed by hash")
    cp.add_argument("--part-q-plan", help="Part Q's plan file, whose reuse list holds the hashes of the reused stages' files")
    cp.add_argument("--charged-ledger", action="append", default=[], help="every Part T charged_ledger.json charged so far (absolute): the charge before the freeze")
    cp.add_argument("--measuring-rehearsal", required=True, help="the Part T measuring rehearsal's record, pinned by SHA-256: the plan carries the counting allowance (2 x the projected counting charge) fixed before the counting rehearsal (ruling 20)")
    cp.add_argument("--supersede", action="store_true")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze")
    f.add_argument("--measuring-rehearsal", required=True)
    f.add_argument("--counting-rehearsal", required=True)
    f.add_argument("--attest-sealed-unopened", default="")
    f.add_argument("--seal-broken", action="store_true")
    f.add_argument("--repo")
    c = sub.add_parser("caps-proposal")
    c.add_argument("--measuring-rehearsal", required=True)
    c.add_argument("--phase", choices=("calibration", "registered"), default="registered")
    c.add_argument("--repo")
    cc = sub.add_parser("caps-config")
    cc.add_argument("--measuring-rehearsal", required=True)
    cc.add_argument("--apply", action="store_true")
    cc.add_argument("--phase", choices=("calibration", "registered"), default="registered")
    cc.add_argument("--repo")
    tk = sub.add_parser("task")
    for a in ("--stage", "--task-id", "--run-dir"):
        tk.add_argument(a, required=True)
    tk.add_argument("--freeze-commit")
    tk.add_argument("--part-q-dir", default=".")
    tk.add_argument("--repo")
    add_rehearsal_flags(tk)
    co = sub.add_parser("cost")
    co.add_argument("--run-dir", required=True)
    co.add_argument("--freeze-commit")
    co.add_argument("--part-q-dir", default=".")
    co.add_argument("--repo")
    tm = sub.add_parser("timing")
    tm.add_argument("--run-dir", required=True)
    tm.add_argument("--freeze-commit")
    tm.add_argument("--part-q-dir", default=".")
    tm.add_argument("--repo")
    rc = sub.add_parser("recompute")
    rc.add_argument("--run-dir", required=True)
    rc.add_argument("--freeze-commit")
    rc.add_argument("--part-q-dir", default=".")
    rc.add_argument("--own-code", action="store_true")
    rc.add_argument("--repo")
    rt = sub.add_parser("retry")
    for a in ("--stage", "--task-id", "--run-dir", "--cause"):
        rt.add_argument(a, required=True)
    rt.add_argument("--fix-changes-frozen-file", action="store_true")
    cal = sub.add_parser("calibrate")
    cal.add_argument("--part-q-dir", required=True)
    cal.add_argument("--part-q-plan", help="Part Q's plan file (its reuse list holds generation/result.json): required")
    cal.add_argument("--open", action="store_true", help="step 1: append the session's open start line (with the code and config hashes) and exit without running a unit; the lead commits the log")
    cal.add_argument("--repetition", type=int, default=0, choices=(0, 1))
    cal.add_argument("--reason", default="", help="required for the single repetition (second/)")
    cal.add_argument("--repo")
    for name in ("registered", "work"):
        r = sub.add_parser(name)
        r.add_argument("--part-q-dir", required=False, default=".")
        r.add_argument("--stage", required=True)
        r.add_argument("--run-dir", required=True)
        r.add_argument("--freeze-commit")
        r.add_argument("--repo")
        add_rehearsal_flags(r)
    h = sub.add_parser("rehearse")
    h.add_argument("--kind", choices=("measuring", "counting"), required=True)
    h.add_argument("--run-dir", required=True)
    h.add_argument("--part-q-dir", required=False, default=".")
    h.add_argument("--part-q-plan")
    h.add_argument("--manifests", help="JSON naming part_q_acceptance and panel_ledger by path and SHA-256")
    h.add_argument("--charged-ledger", action="append", default=[], help="an earlier Part T charged_ledger.json (absolute), listed in the record")
    h.add_argument("--repo")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        table: dict[str, Any] = {"candidate-plan": cmd_candidate_plan, "freeze": cmd_freeze, "caps-proposal": cmd_caps_proposal, "registered": cmd_registered, "work": cmd_registered, "rehearse": cmd_rehearse, "calibrate": cmd_calibrate, "task": cmd_task, "retry": cmd_retry, "recompute": cmd_recompute, "timing": cmd_timing, "cost": cmd_cost, "caps-config": cmd_caps_config}
        return int(table[args.command](args))
    except StageRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return EXIT_IDENTITY if "PAUSED — IDENTITY" in str(e) else EXIT_REFUSED
    except PendingLeadReview as e:
        print(f"PENDING LEAD REVIEW: {e}", file=sys.stderr)
        return EXIT_LEAD


if __name__ == "__main__":
    raise SystemExit(main())
