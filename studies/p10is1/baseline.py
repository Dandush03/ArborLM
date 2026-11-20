# ruff: noqa: E501
"""P10IS1 quiet baseline (ADR-0024 addendum A3.1, A8 item 1): one idle window taken on this machine BEFORE the candidate plan, from which the quiet limit L is measured. It reads no seed, no data and no sealed value.

``python -m studies.p10is1.baseline run --out-dir D`` (a single command; the lead launches it with its own ``timeout`` and output redirected to a file, and makes no tool call until it exits):

* every 10 s one sample (the one-minute and five-minute load averages in integer hundredths, and every condition of ``machine.read_conditions``) is appended to ``D/samples.jsonl`` AS IT IS TAKEN;
* an attempt is 60 settle samples (loads recorded, entering no figure) and the next 360 window samples; ONE failure of one condition at one sample, a gap above 15 s, a changed boot time or a changed application
  presence discards the attempt and the next begins again at the settle period; the command holds ``caffeinate -i -w <pid>`` (a child: inside its own process family) for the whole run;
* the window is SETTLED only if the two-sided tests of ``loadrule.settled`` hold; L = P95 + 50 hundredths; L above 300 is BASELINE ABOVE CEILING (refused, retaken, never clamped);
* a session is at most 6 hours and no attempt starts that could not finish inside it (70 minutes); a session without an accepted window is PAUSED — NO QUIET BASELINE, every sample kept, rescheduled by running the
  same command again; after three such sessions in the OPEN condition the condition changes to CLOSED by this rule (recorded); after three further ones in the closed condition the matter returns to the human lead
  (a refusal); no outcome follows automatically;
* a second baseline only for one of ``SECOND_REASONS`` (``--replaces``), the reason written BEFORE the sampling starts, and never once a registered timing value exists.

``verify`` re-derives P95, L, the condition and both presences from a committed samples file (the freeze does the same: ``verify_against_config``).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256

from . import core, loadrule, machine, quiet

SAMPLES = "samples.jsonl"
RECORD = "record.json"
REASON_FILE = "second_baseline_reason.json"
PAUSED_NO_BASELINE = "PAUSED — NO QUIET BASELINE"
ACCEPTED = "ACCEPTED"
SECOND_REASONS = ("os_update", "hardware_or_power_change", "condition_change_by_human_lead", "failure_of_the_first_found_by_review")
EXIT_PAUSED = 3


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def next_condition(sessions: Sequence[Mapping[str, Any]], q: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    """The condition of the next session by the rule of A3.1 item 7: OPEN until three sessions in the open condition ended PAUSED — NO QUIET BASELINE, then CLOSED; after three further ones in the closed condition
    the matter returns to the human lead (``StageRefused``). Returns the condition and the counts."""
    open_n = sum(1 for s in sessions if s["condition"] == "open" and s["status"] == PAUSED_NO_BASELINE)
    closed_n = sum(1 for s in sessions if s["condition"] == "closed" and s["status"] == PAUSED_NO_BASELINE)
    counts = {"open": open_n, "closed": closed_n}
    forced = next((s for s in sessions if s.get("forced_condition")), None)
    if forced is not None:
        return str(forced["condition"]), counts
    if closed_n >= int(q["closed_sessions_to_human_lead"]):
        raise core.StageRefused(f"refused: {closed_n} baseline sessions in the closed condition ended {PAUSED_NO_BASELINE}: the matter returns to the human lead; no outcome follows automatically")
    return ("closed" if open_n >= int(q["open_sessions_before_closed"]) else "open"), counts


_test_root: Path | None = None  # TEST-ONLY override (set through ``set_test_root`` by a test module): no option, no environment variable and no launch script reaches it


def canonical_root() -> Path:
    """The study's ONE baseline root (F4): ``<experiments>/P10IS1-quiet-baseline``, derived from the repository's experiments directory; no option and no environment variable changes it. It holds ``first/`` (every
    session of the first baseline) and, only for one of the four reasons, ``second/``; nothing else may hold a baseline record."""
    from studies.p9 import core as p9core

    return Path(p9core.default_experiments_root()) / "P10IS1-quiet-baseline"


def set_test_root(path: Path | None) -> None:
    """TEST ONLY. A record taken under it says ``test_root = true`` and is refused by the candidate plan and the freeze."""
    global _test_root
    _test_root = path


def default_root() -> Path:
    return _test_root if _test_root is not None else canonical_root()


def resolve_out(root: Path, replaces: bool) -> Path:
    """One baseline per STUDY, not per output directory (F4). The first baseline lives in ``root/first`` and continues there across PAUSED sessions; a record that is not ACCEPTED is "not settled under the addendum's own
    rule" and may be continued, never restarted elsewhere. Refused: any other directory under the root that holds a baseline record; a new first baseline once ``first`` is ACCEPTED; a second baseline otherwise than
    through ``--replaces`` (into ``root/second``, with one of the four reasons, written before the sampling)."""
    first, second = root / "first", root / "second"
    strays = sorted(str(p.parent) for p in root.glob("*/" + RECORD) if p.parent.name not in ("first", "second")) if root.is_dir() else []
    if strays:
        raise core.StageRefused(f"refused: {strays} hold baseline records outside first/ and second/: this study has ONE baseline root ({root})")
    first_status = core.read_record(first / RECORD, "quiet_baseline").get("status") if (first / RECORD).is_file() else None
    if not replaces:
        if first_status == ACCEPTED or (second / RECORD).is_file() or (second / REASON_FILE).is_file():
            raise core.StageRefused(f"refused: this study's baseline is taken once ({first / RECORD} is ACCEPTED); a second only with --replaces and one of {list(SECOND_REASONS)}")
        return first
    if first_status != ACCEPTED:
        raise core.StageRefused("refused: there is no ACCEPTED first baseline to replace")
    if (second / RECORD).is_file() and core.read_record(second / RECORD, "quiet_baseline").get("status") == ACCEPTED:
        raise core.StageRefused("refused: a second baseline has been taken; there is no third")
    return second


def check_root_consistency(root: Path, record_path: Path, interrupted: Collection[tuple[str, int, int]] = ()) -> None:
    """The freeze's check (F4). The canonical root must exist (no skip). The committed record must say it was taken under THIS root and not under a test root, must be the root's first ACCEPTED record (or the root's
    second whose reason file predates its first sample), its samples file must be the root's, and the attempts it lists must be exactly the root's full list of attempts (every attempt of every session)."""
    if not root.is_dir():
        raise core.StageRefused(f"refused: the canonical baseline root {root} does not exist: the baseline was not taken by this study's command, so nothing can be frozen on it")
    committed = core.read_record(record_path, "quiet_baseline")
    if committed.get("test_root") is not False:
        raise core.StageRefused("refused: the committed baseline record does not say test_root = false: a baseline taken under a test root is never frozen")
    if committed.get("root") != str(root.resolve()):
        raise core.StageRefused(f"refused: the committed baseline was taken under {committed.get('root')!r}, not under the canonical root {str(root.resolve())!r}")
    first, second = root / "first", root / "second"
    sha = file_sha256(record_path)
    which: Path | None = None
    if (first / RECORD).is_file() and file_sha256(first / RECORD) == sha:
        if (second / RECORD).is_file() and core.read_record(second / RECORD, "quiet_baseline").get("status") == ACCEPTED:
            raise core.StageRefused("refused: the committed baseline is the first, but an ACCEPTED second baseline exists in the root: the second replaced it")
        which = first
    elif (second / RECORD).is_file() and file_sha256(second / RECORD) == sha:
        reason, samples = second / REASON_FILE, second / SAMPLES
        if not reason.is_file() or not samples.is_file() or json.loads(reason.read_text())["utc"] >= json.loads(samples.read_text().splitlines()[0])["utc"]:
            raise core.StageRefused("refused: the second baseline's reason file does not predate its first sample")
        which = second
    if which is None:
        raise core.StageRefused(f"refused: the committed baseline record is neither the first ACCEPTED record nor the second of {root}: one baseline per study, taken by this command in its root")
    root_samples = which / SAMPLES
    if not root_samples.is_file() or file_sha256(root_samples) != committed["samples_sha256"] or file_sha256(record_path.parent / str(committed["samples_file"])) != committed["samples_sha256"]:
        raise core.StageRefused("refused: the committed samples file is not the root's samples file")
    seen = {(int(r["session"]), int(r["attempt"])) for r in (json.loads(x) for x in root_samples.read_text(encoding="utf-8").splitlines() if x.strip()) if int(r["attempt"]) > 0}
    listed = {(int(a["session"]), int(a["attempt"])) for a in committed["attempts"]} | {(s, a) for d, s, a in interrupted if d == which.name}  # attempts of a killed session are listed in SESSIONS.log as INTERRUPTED
    if seen != listed:
        raise core.StageRefused(f"refused: the record lists attempts {sorted(listed)} but the root's samples hold {sorted(seen)}: every attempt must be listed")


def check_second(reason: str, replaces: Path, registered_run_dir: Path) -> dict[str, Any]:
    """A second baseline only for one of the four reasons, an accepted first record to replace, and no registered timing value yet."""
    if reason not in SECOND_REASONS:
        raise core.StageRefused(f"refused: a second baseline is taken only for one of {list(SECOND_REASONS)}, not {reason!r}")
    rec_path = replaces / RECORD
    if not rec_path.is_file() or core.read_record(rec_path, "quiet_baseline").get("status") != ACCEPTED:
        raise core.StageRefused(f"refused: {rec_path} is not an accepted baseline record: there is nothing to replace")
    if (registered_run_dir / "timing" / "timing.json").exists():
        raise core.StageRefused("refused: a registered timing value exists: no baseline is taken after it")
    return {"replaces": str(rec_path.resolve()), "replaces_sha256": file_sha256(rec_path), "earlier_attempts": core.read_record(rec_path, "quiet_baseline").get("attempts", [])}  # the first baseline's attempts stay listed


SESSIONS_LOG = "results/p10is1-quiet-baseline/SESSIONS.log"  # repository-tracked; written by the baseline command OUTSIDE any registered stage (the baseline is not one)


def default_sessions_log() -> Path:
    return core.repo_root() / SESSIONS_LOG


def prefix_sha(samples_path: Path, upto_session: int) -> str | None:
    """SHA-256 of the samples file's PREFIX that holds the samples of sessions 1 to ``upto_session`` (sessions are appended in order): what the file was when that session ended. None if there is no such prefix."""
    if not samples_path.is_file():
        return None
    import hashlib

    h, n = hashlib.sha256(), 0
    for ln in samples_path.read_bytes().splitlines(keepends=True):
        if not ln.strip():
            continue
        if int(json.loads(ln)["session"]) > upto_session:
            break
        h.update(ln)
        n += 1
    return h.hexdigest() if n else None


def samples_maxes(samples_path: Path) -> tuple[int, int]:
    """(highest session, highest attempt) already in the samples file: a new session or attempt never reuses a number of a session that was interrupted."""
    s = a = 0
    if samples_path.is_file():
        for ln in samples_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                s, a = max(s, int(r["session"])), max(a, int(r["attempt"]))
    return s, a


def _log_line(log: Path, directory: str, session: int, span: str, status: str, sha: str | None) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{_utc()}\tdir={directory}\tsession={session}\tattempts={span}\tstatus={status}\tsamples_sha256={sha}\n")
        f.flush()
        os.fsync(f.fileno())


def append_session_line(log: Path, directory: str, session: int, rec: Mapping[str, Any], status: str, samples_path: Path | None = None) -> None:
    """One line per baseline session (Advisory 2): UTC time, the directory (first/second), the session, the attempt numbers it ran (``first-last``, or ``none``), its status and the SHA-256 of the samples file as it was
    when the session ended (the prefix through that session). The lead commits the file before the next step; the freeze refuses repeated (directory, session) lines, a hash that is not the matching prefix of the root's
    samples, and attempts of the root that are not all listed."""
    nums = [int(a["attempt"]) for a in rec["attempts"] if int(a["session"]) == session]
    span = f"{min(nums)}-{max(nums)}" if nums else "none"
    sha = prefix_sha(samples_path, session) if samples_path is not None else rec.get("samples_sha256")
    _log_line(log, directory, session, span, status, sha)


def parse_log(log: Path) -> list[dict[str, str]]:
    return [dict(x.split("=", 1) for x in ln.split("\t")[1:]) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]


def listed_attempts(log: Path) -> tuple[set[tuple[str, int, int]], str | None]:
    """(dir, session, attempt) for every attempt the log lists (INTERRUPTED lines included), and the samples hash of its last line."""
    out: set[tuple[str, int, int]] = set()
    last = None
    for f in parse_log(log):
        if f["attempts"] != "none":
            a, b = (int(x) for x in f["attempts"].split("-"))
            out |= {(f["dir"], int(f["session"]), n) for n in range(a, b + 1)}
        last = f["samples_sha256"]
    return out, last


def interrupted_attempts(log: Path) -> set[tuple[str, int, int]]:
    """(dir, session, attempt) of the attempts the log lists as INTERRUPTED (a session that was killed before it wrote its record)."""
    out: set[tuple[str, int, int]] = set()
    if log.is_file():
        for f in parse_log(log):
            if f["status"] == "INTERRUPTED" and f["attempts"] != "none":
                a, b = (int(x) for x in f["attempts"].split("-"))
                out |= {(f["dir"], int(f["session"]), n) for n in range(a, b + 1)}
    return out


def record_interrupted(log: Path, out: Path) -> list[int]:
    """At the START of a session (before any sampling): every attempt present in this directory's samples but not listed in SESSIONS.log belongs to a session that was killed before it could log itself; it gets an appended
    INTERRUPTED line (with the samples hash through that session). Returns the sessions so recorded."""
    sp = out / SAMPLES
    if not sp.is_file():
        return []
    listed = {(s, a) for d, s, a in (listed_attempts(log)[0] if log.is_file() else set()) if d == out.name}
    missing: dict[int, list[int]] = {}
    for ln in sp.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            if int(r["attempt"]) > 0 and (int(r["session"]), int(r["attempt"])) not in listed:
                missing.setdefault(int(r["session"]), [])
                if int(r["attempt"]) not in missing[int(r["session"])]:
                    missing[int(r["session"])].append(int(r["attempt"]))
    for s, nums in sorted(missing.items()):
        _log_line(log, out.name, s, f"{min(nums)}-{max(nums)}", "INTERRUPTED", prefix_sha(sp, s))
    return sorted(missing)


def check_sessions_log(root: Path, log: Path) -> None:
    """The freeze's check: the committed SESSIONS.log exists; no (directory, session) is listed twice; each line's samples SHA-256 is the hash of the matching PREFIX of the root's samples file (so a deleted-and-retaken
    root cannot pass); and it lists EVERY attempt of the root's samples (first/ and second/), INTERRUPTED lines included."""
    if not log.is_file():
        raise core.StageRefused(f"refused: {log} does not exist: every baseline session appends a line to it and the lead commits it before the next step")
    lines = parse_log(log)
    keys = [(f["dir"], int(f["session"])) for f in lines]
    if len(set(keys)) != len(keys):
        raise core.StageRefused(f"refused: {log.name} lists a (directory, session) more than once: {sorted(k for k in set(keys) if keys.count(k) > 1)}")
    for f in lines:
        sp = root / f["dir"] / SAMPLES
        want = prefix_sha(sp, int(f["session"]))
        if str(want) != f["samples_sha256"]:
            raise core.StageRefused(f"refused: {log.name} line for {f['dir']} session {f['session']} names samples hash {f['samples_sha256']}, not the hash {want} of the matching prefix of the root's samples file")
    listed, _ = listed_attempts(log)
    seen: set[tuple[str, int, int]] = set()
    for d in ("first", "second"):
        sp = root / d / SAMPLES
        if sp.is_file():
            seen |= {(d, int(r["session"]), int(r["attempt"])) for r in (json.loads(x) for x in sp.read_text(encoding="utf-8").splitlines() if x.strip()) if int(r["attempt"]) > 0}
    if seen != listed:
        raise core.StageRefused(f"refused: {log.name} lists attempts {sorted(listed)} but the root's samples hold {sorted(seen)}: every attempt of every session must be listed (and committed)")


BASELINE_FILES = ("machine.py", "baseline.py", "quiet.py", "loadrule.py", "watch_child.py")  # the code a baseline is taken with, under studies/p10is1/
CODE_PATHS = ("studies/p10is1", "configs/p10is1_capacity.toml")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, timeout=60)  # noqa: S603, S607


def head_commit(repo: Path) -> str:
    r = _git(repo, "rev-parse", "HEAD")
    if r.returncode != 0:
        raise core.StageRefused(f"refused: no git HEAD in {repo}")
    return r.stdout.strip()


def require_clean_code(repo: Path) -> str:
    """The baseline runs only on a clean tree for the files of studies/p10is1 and the config (untracked files included); returns HEAD, which the record carries."""
    r = _git(repo, "status", "--porcelain", "--", *CODE_PATHS)
    if r.returncode != 0 or r.stdout.strip():
        raise core.StageRefused("refused: the tree is not clean for studies/p10is1 and the config: commit them first (the baseline is taken on a commit):\n" + r.stdout.rstrip())
    return head_commit(repo)


def check_code_commit(repo: Path, record_path: Path) -> None:
    """The candidate plan and the freeze: the record's code commit exists, is an ancestor of HEAD, and the baseline-relevant files (machine.py, baseline.py, quiet.py, loadrule.py, watch_child.py) are, in the working
    tree, exactly what that commit holds."""
    commit = core.read_record(record_path, "quiet_baseline").get("code_commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise core.StageRefused("refused: the baseline record carries no code commit")
    if _git(repo, "cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
        raise core.StageRefused(f"refused: the baseline's code commit {commit} is not a commit of this repository")
    if _git(repo, "merge-base", "--is-ancestor", commit, "HEAD").returncode != 0:
        raise core.StageRefused(f"refused: the baseline's code commit {commit} is not an ancestor of HEAD")
    paths = [f"studies/p10is1/{f}" for f in BASELINE_FILES]
    d = _git(repo, "diff", "--name-only", commit, "--", *paths)
    if d.returncode != 0 or d.stdout.strip():
        raise core.StageRefused(f"refused: baseline-relevant files differ from the baseline's code commit {commit}: {d.stdout.split()}")


def write_record(out: Path, rec: Mapping[str, Any]) -> None:
    core.write_record(out / RECORD, rec, overwrite=True)


def run_baseline(
    out: Path,
    *,
    cfg: Mapping[str, Any] | None = None,
    probe: machine.Probe | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    wall: Callable[[], float] = time.time,
    condition: str | None = None,
    second: Mapping[str, Any] | None = None,
    os_build: Callable[[], str] = lambda: machine._run(["sw_vers", "-buildVersion"]).strip(),  # noqa: SLF001
    awake: Callable[[], Any] = machine.keep_awake,
    config_file_sha256: str | None = None,
    sessions_log: Path | None = None,
    code_commit: str | None = None,
) -> dict[str, Any]:
    """One SESSION of the baseline (at most ``baseline_session_hours``) in ``out``. Returns the record (also written to ``out/record.json``). Every wait has a deadline; every sample is on disk when taken."""
    q = core.cfg_of(cfg)["quiet"]
    pr = probe or machine.Probe()
    out.mkdir(parents=True, exist_ok=True)
    rec_path = out / RECORD
    rec: dict[str, Any] = dict(core.read_record(rec_path, "quiet_baseline")) if rec_path.is_file() else {**core.envelope("quiet_baseline"), "status": PAUSED_NO_BASELINE, "sessions": [], "attempts": [], "accepted": None, "second_baseline": dict(second) if second else None}
    if rec["status"] == ACCEPTED:
        raise core.StageRefused(f"refused: {rec_path} is an ACCEPTED baseline: a baseline is taken once (a second only by --replaces with one of {list(SECOND_REASONS)})")
    rules = core.quiet_rules_sha256(cfg)
    if rec.get("quiet_rules_sha256") not in (None, rules):
        raise core.StageRefused("refused: this baseline was begun under other [quiet] rules (hash differs): one baseline per study is taken under one set of rules")
    rec["quiet_rules_sha256"] = rules  # F4-b: the rules (the committed config's [quiet] block without the figures entered afterwards) this baseline is taken under
    rec["config_file_sha256"] = config_file_sha256
    if code_commit is not None:
        if rec.get("code_commit") not in (None, code_commit):
            raise core.StageRefused("refused: this baseline was begun on another code commit: one baseline per study is taken on one commit")
        rec["code_commit"] = code_commit  # the commit the baseline-relevant files were at (the freeze compares them with it)
    elif "code_commit" not in rec:
        rec["code_commit"] = None
    if sessions_log is not None:
        record_interrupted(sessions_log, out)  # BEFORE any sampling: attempts of a killed session get their INTERRUPTED line
    rec["root"] = str(out.parent.resolve())  # F4: where it was taken
    rec["test_root"] = _test_root is not None  # a record taken under the test-only override is refused by the candidate plan and the freeze
    sessions: list[dict[str, Any]] = list(rec["sessions"])
    cond, counts = next_condition(sessions, q)
    if condition is not None:
        if second is None or second.get("reason") != "condition_change_by_human_lead":
            raise core.StageRefused("refused: the condition is chosen by the rule of A3.1 item 7; only a second baseline for 'condition_change_by_human_lead' may name it")
        if condition not in machine.CONDITIONS:
            raise core.StageRefused(f"refused: condition is 'open' or 'closed', not {condition!r}")
        cond = condition
    max_session, max_attempt = samples_maxes(out / SAMPLES)
    n_session = max(len(sessions), max_session) + 1  # never the number of a session that was interrupted
    interval, settle, window_n = float(q["baseline_interval_seconds"]), int(q["settle_samples"]), int(q["baseline_samples"])
    gap_max = float(q["sample_gap_max_seconds"])
    limit_s = float(q["baseline_session_hours"]) * 3600.0
    attempt_s = float(q["baseline_attempt_minutes"]) * 60.0
    samples_path = out / SAMPLES
    session: dict[str, Any] = {"session": n_session, "condition": cond, "started_utc": _utc(), "status": PAUSED_NO_BASELINE, "attempts": 0, "samples": 0, **({"forced_condition": True} if condition is not None else {})}
    began, cpu0 = clock(), pr.cpu()
    attempt_no = max(int(rec["attempts"][-1]["attempt"]) if rec["attempts"] else 0, max_attempt)
    cur: list[dict[str, Any]] = []
    cur_top: list[Any] = []
    cur_start = ""

    def finish_attempt(outcome: str, reason: str, derived: Mapping[str, Any] | None) -> None:
        rec["attempts"].append({"session": n_session, "attempt": attempt_no, "condition": cond, "outcome": outcome, "reason": reason, "samples": len(cur), "started_utc": cur_start, "ended_utc": _utc(), "top_processes_start": cur_top, "top_processes_end": _safe_top(pr), "derived": derived})
        session["attempts"] += 1
        cur.clear()

    def checkpoint() -> None:
        rec.update(sessions=[*sessions, dict(session)], condition=cond, paused_sessions=counts, sampler_cpu_seconds=pr.cpu() - cpu0)
        write_record(out, rec)

    with awake():  # the power assertion (``caffeinate -i -w <pid>``) is a child of this process
        try:
            while True:
                if not cur and clock() - began + attempt_s > limit_s:
                    break  # no attempt starts that could not finish inside the session
                t = wall()
                got = machine.read_conditions(pr, q, condition=cond, expect=None)
                try:
                    l1, l5 = pr.load()
                    h1, h5 = loadrule.hundredths(l1), loadrule.hundredths(l5)
                except Exception:  # noqa: BLE001 - fail closed
                    h1 = h5 = -1
                    got["failed"] = [*got["failed"], "LOAD UNREADABLE"]
                failed = list(got["failed"])
                if cur:
                    gap = t - cur[-1]["t"]
                    if gap > gap_max:
                        failed.append(f"SAMPLING GAP OF {gap:.1f} s (SLEEP OR STALL)")
                    if got["boot"] != cur[0]["boot"]:
                        failed.append("BOOT TIME CHANGED")
                    if (got["app_present"], got["cli_present"]) != (cur[0]["app_present"], cur[0]["cli_present"]):
                        failed.append("APPLICATION PRESENCE CHANGED")
                    if got.get("claude_pids") != cur[0].get("claude_pids"):
                        failed.append("CLAUDE PROCESS SET CHANGED")  # F1: a new or ended Claude process (another session started or stopped) inside the attempt
                in_attempt = bool(cur) or not failed
                if in_attempt and not cur:
                    attempt_no += 1
                    cur_start, cur_top = _utc(), _safe_top(pr)
                idx = len(cur) + 1 if in_attempt else 0
                sample = {
                    "session": n_session, "attempt": attempt_no if in_attempt else 0, "index": idx, "phase": ("settle" if idx <= settle else "window") if in_attempt else "waiting", "utc": _utc(), "t": t, "condition": cond, "load1_h": h1, "load5_h": h5,
                    "failed": failed, "app_present": got["app_present"], "cli_present": got["cli_present"], "claude_pids": got.get("claude_pids"), "tool_shells": got.get("tool_shells", []), "hid_idle_seconds": got.get("hid_idle_seconds"), "boot": got["boot"], "mains": got.get("mains"), "low_power_mode": got.get("low_power_mode"),
                    "thermal_lines": got.get("thermal_lines", []), "other_study_processes": got["other_study_processes"], "vm_processes": got["vm_processes"], "sampler_cpu_seconds": pr.cpu() - cpu0,
                }  # fmt: skip
                quiet.append_line(samples_path, sample)  # on disk before anything else happens
                session["samples"] += 1
                if failed:
                    if cur:
                        finish_attempt("DISCARDED", "; ".join(failed), None)
                        checkpoint()
                elif in_attempt:
                    cur.append(sample)
                    if len(cur) == settle + window_n:
                        derived = loadrule.derive([int(s["load1_h"]) for s in cur[settle:]], q)
                        st = derived["settled"]
                        if not st["settled"]:
                            finish_attempt("DISCARDED", "NOT SETTLED (two-sided test: " + ("medians" if not st["median_ok"] else "") + (" and " if not st["median_ok"] and not st["p95_ok"] else "") + ("P95s" if not st["p95_ok"] else "") + ")", derived)
                        elif derived["above_ceiling"]:
                            finish_attempt("DISCARDED", f"BASELINE ABOVE CEILING (L = {derived['load_limit']} > {int(q['load_ceiling'])} hundredths)", derived)
                        else:
                            finish_attempt(ACCEPTED, "", derived)
                            rec["accepted"] = {"session": n_session, "attempt": attempt_no, **derived, "app_present": bool(cur_presence(rec, attempt_no, samples_path, "app_present")), "cli_present": bool(cur_presence(rec, attempt_no, samples_path, "cli_present")), "condition": cond}
                            session["status"], rec["status"] = ACCEPTED, ACCEPTED
                            break
                        checkpoint()
                sleep(interval)
        finally:
            session["ended_utc"] = _utc()
            if rec["status"] != ACCEPTED:
                session["status"] = PAUSED_NO_BASELINE
            sessions_final = [*sessions, dict(session)]
            counts = {"open": sum(1 for s in sessions_final if s["condition"] == "open" and s["status"] == PAUSED_NO_BASELINE), "closed": sum(1 for s in sessions_final if s["condition"] == "closed" and s["status"] == PAUSED_NO_BASELINE)}
            fell_back = cond == "closed" and not any(s.get("forced_condition") for s in sessions_final) and counts["open"] >= int(q["open_sessions_before_closed"])
            rec.update(
                sessions=sessions_final, condition=cond, paused_sessions=counts, condition_changed_to_closed=({"after_open_sessions": counts["open"], "by": "the rule of ADR-0024 addendum A3.1 item 7, not by a new decision"} if fell_back else None),
                os_build=os_build(), boot=_safe(pr.boot), samples_file=SAMPLES, samples_sha256=file_sha256(samples_path) if samples_path.is_file() else None, sampler_cpu_seconds=(pr.cpu() - cpu0), config_figures={k: q[k] for k in ("baseline_samples", "baseline_interval_seconds", "settle_samples", "settled_median_diff_max", "settled_p95_diff_max", "load_margin", "load_ceiling", "percentile")},
            )  # fmt: skip
            write_record(out, rec)
            if sessions_log is not None:
                append_session_line(sessions_log, out.name, n_session, rec, session["status"], samples_path)
    return dict(rec)


def cur_presence(rec: Mapping[str, Any], attempt: int, samples_path: Path, key: str) -> bool:
    """The attempt's application presence, read back from its samples (it was constant by the rule that discards a change)."""
    for line in reversed(samples_path.read_text(encoding="utf-8").splitlines()):
        s = json.loads(line)
        if s["attempt"] == attempt:
            return bool(s[key])
    return False


def _safe(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return None


def _safe_top(pr: machine.Probe) -> list[Any]:
    try:
        return list(pr.top())
    except Exception:  # noqa: BLE001 - recorded, never a condition
        return []


# --- re-derivation from the committed samples (the freeze) --------------------------------------------------------------------------------------------
def rederive(record_path: Path, q: Mapping[str, Any]) -> dict[str, Any]:
    """Re-derive P95, L, the condition and both presences of the ACCEPTED attempt from the committed samples file the record names, checking every sample of the attempt: all conditions held, gaps within tolerance,
    one boot time, one presence, 60 settle and 360 window samples in order, and the two-sided settled tests. Raises ``StageRefused`` on anything else; never clamps L."""
    rec = core.read_record(record_path, "quiet_baseline")
    if rec.get("status") != ACCEPTED or not rec.get("accepted"):
        raise core.StageRefused(f"refused: {record_path} is not an ACCEPTED quiet baseline ({rec.get('status')})")
    samples_path = record_path.parent / str(rec["samples_file"])
    if not samples_path.is_file() or file_sha256(samples_path) != rec["samples_sha256"]:
        raise core.StageRefused("refused: the baseline's samples file is missing or does not hash to what the record names")
    acc = rec["accepted"]
    rows = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    sel = [r for r in rows if r["session"] == acc["session"] and r["attempt"] == acc["attempt"]]
    settle, window_n = int(q["settle_samples"]), int(q["baseline_samples"])
    if len(sel) != settle + window_n or [r["index"] for r in sel] != list(range(1, settle + window_n + 1)):
        raise core.StageRefused(f"refused: the accepted attempt has {len(sel)} samples, not {settle} settle and {window_n} window samples in order")
    bad = [r["index"] for r in sel if r["failed"]]
    if bad:
        raise core.StageRefused(f"refused: samples {bad[:5]} of the accepted attempt carry a failed condition")
    gap_max = float(q["sample_gap_max_seconds"])
    gaps = [b["t"] - a["t"] for a, b in zip(sel, sel[1:], strict=False)]
    if any(g > gap_max for g in gaps):
        raise core.StageRefused(f"refused: a gap of {max(gaps):.1f} s between samples is above {gap_max} s")
    if len({r["boot"] for r in sel}) != 1 or len({(r["app_present"], r["cli_present"]) for r in sel}) != 1 or len({r["condition"] for r in sel}) != 1:
        raise core.StageRefused("refused: the accepted attempt's boot time, application presence or condition is not constant")
    cond = sel[0]["condition"]
    if cond == "closed" and (sel[0]["app_present"] or sel[0]["cli_present"]):
        raise core.StageRefused("refused: the closed condition's baseline has the application or Claude Code present")
    derived = loadrule.derive([int(r["load1_h"]) for r in sel[settle:]], q)
    if not derived["settled"]["settled"]:
        raise core.StageRefused(f"refused: the accepted window is not settled on re-derivation: {derived['settled']}")
    if derived["above_ceiling"]:
        raise core.StageRefused(f"refused: BASELINE ABOVE CEILING: L = {derived['load_limit']} hundredths is above {int(q['load_ceiling'])}; it is never clamped")
    return {**derived, "condition": cond, "app_present": bool(sel[0]["app_present"]), "cli_present": bool(sel[0]["cli_present"]), "record_sha256": file_sha256(record_path), "samples_sha256": rec["samples_sha256"]}


def verify_against_config(repo: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The freeze's check: the committed record hashes to the config's ``baseline_record_sha256`` and its re-derived P95, L, condition and both presences equal the config's; prints (returns) a notice if L is above 250."""
    q = cfg["quiet"]
    if q["baseline_provisional"]:
        raise core.StageRefused("refused: [quiet] baseline_provisional is true: the quiet baseline has not been taken and written into the config")
    path = repo / str(q["baseline_record_path"])
    if not str(q["baseline_record_path"]) or not path.is_file():
        raise core.StageRefused(f"refused: the config's baseline_record_path {q['baseline_record_path']!r} is not a file of the repository")
    if file_sha256(path) != q["baseline_record_sha256"]:
        raise core.StageRefused("refused: the baseline record does not hash to the config's baseline_record_sha256")
    committed = core.read_record(path, "quiet_baseline")
    if committed.get("quiet_rules_sha256") != core.quiet_rules_sha256(cfg):
        raise core.StageRefused("refused: the baseline record was taken under other [quiet] rules than the committed config's (relaxed conditions are not frozen on): its quiet_rules_sha256 differs")
    if committed.get("test_root") is not False:
        raise core.StageRefused("refused: the baseline record does not say test_root = false: a baseline taken under a test root is refused")
    d = rederive(path, q)
    want = {"load_p95": int(q["load_p95"]), "load_limit": int(q["load_limit"]), "condition": str(q["condition"]), "app_present": bool(q["app_present"]), "cli_present": bool(q["cli_present"])}
    got = {"load_p95": d["load_p95"], "load_limit": d["load_limit"], "condition": d["condition"], "app_present": d["app_present"], "cli_present": d["cli_present"]}
    if got != want:
        raise core.StageRefused(f"refused: the config's quiet figures {want} differ from the ones re-derived from the committed samples {got}")
    d["notice"] = f"NOTICE: L = {d['load_limit']} hundredths is above {int(q['load_report_above'])}: report it to the human lead before the candidate plan is frozen (a report, not a gate)" if d["report_above"] else None
    return d


# --- the command ------------------------------------------------------------------------------------------------------------------------------------------
def preflight(probe: machine.Probe | None = None, cfg: Mapping[str, Any] | None = None) -> None:
    """N4: before any sampling, refuse (exit 2, nothing written) if a process that the baseline would discard every attempt for is alive, and PRINT its command line: a tool-call shell of any Claude session outside
    this command's own chain (the lead's long-running background shells included), another study's process, a virtual machine."""
    q = core.cfg_of(cfg)["quiet"]
    got = machine.read_conditions(probe or machine.Probe(), q, condition="open")
    groups = (("CLAUDE TOOL-CALL SHELL ACTIVE", "tool-call shells of Claude sessions", "tool_shells"), ("OTHER STUDY PROCESS ALIVE", "processes of other studies", "other_study_processes"), ("VIRTUAL MACHINE PRESENT", "virtual machine processes", "vm_processes"))
    lines: list[str] = []
    for failure, title, key in groups:
        if failure in got["failed"]:
            lines.append(f"{title}:")
            lines += [f"  {x}" for x in got[key]]
    if lines:
        raise core.StageRefused("refused: stop these processes before the baseline (every attempt would be discarded):\n" + "\n".join(lines))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studies.p10is1.baseline")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="one session of the quiet baseline (about 80 minutes when the machine is left alone; up to 6 hours)")
    r.add_argument("--replaces", action="store_true", help="a second baseline, replacing the ACCEPTED first one of the root")
    r.add_argument("--reason", help=f"one of {list(SECOND_REASONS)} (second baseline only)")
    r.add_argument("--reason-text", default="")
    r.add_argument("--registered-run-dir", help="the registered run directory (a second baseline is refused if its timing record exists)")
    r.add_argument("--condition", help="only with --reason condition_change_by_human_lead")
    v = sub.add_parser("verify", help="re-derive the figures from a committed baseline record and its samples")
    v.add_argument("--record", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = core.load_config()  # ALWAYS the committed configs/p10is1_capacity.toml: there is no option for another
    try:
        if args.command == "verify":
            d = rederive(Path(args.record), cfg["quiet"])
            print(json.dumps(core.jsonable({"load_p95": d["load_p95"], "load_limit": d["load_limit"], "condition": d["condition"], "app_present": d["app_present"], "cli_present": d["cli_present"], "baseline_record_sha256": d["record_sha256"], "settled": d["settled"], "report_above": d["report_above"]}), sort_keys=True))
            return 0
        code = require_clean_code(core.repo_root())  # the baseline is taken on a clean, committed tree; the record carries the commit
        preflight(cfg=cfg)
        root = default_root()  # the canonical root: there is no option for another
        out = resolve_out(root, bool(args.replaces))
        second = None
        if args.replaces:
            if not args.reason or not args.registered_run_dir:
                raise core.StageRefused("refused: a second baseline needs --reason and --registered-run-dir")
            second = {**check_second(args.reason, root / "first", Path(args.registered_run_dir)), "reason": args.reason, "text": args.reason_text, "utc": _utc()}
            out.mkdir(parents=True, exist_ok=True)
            if not (out / REASON_FILE).exists():
                (out / REASON_FILE).write_text(json.dumps(second, indent=2, sort_keys=True) + "\n", encoding="utf-8")  # the reason is on disk BEFORE the second baseline is taken
        elif args.reason or args.condition:
            raise core.StageRefused("refused: --reason and --condition belong to a second baseline (--replaces)")
        rec = run_baseline(out, cfg=cfg, condition=args.condition, second=second, config_file_sha256=core.config_sha256(), sessions_log=default_sessions_log(), code_commit=code)
    except core.StageRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    last = rec["accepted"]
    print(json.dumps(core.jsonable({"status": rec["status"], "condition": rec["condition"], "paused_sessions": rec["paused_sessions"], "accepted": last, "record": str(out / RECORD), "samples_sha256": rec["samples_sha256"], "record_sha256": file_sha256(out / RECORD)}), sort_keys=True))
    return 0 if rec["status"] == ACCEPTED else EXIT_PAUSED


if __name__ == "__main__":
    sys.exit(main())
