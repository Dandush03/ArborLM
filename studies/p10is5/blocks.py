# ruff: noqa: E501
"""P10IS5 stage block loop, shared by M, K and E2 (ADR-0028 sections 7 to 9, rulings 12, 14): dependencies, the resumable state, the process-per-pass runner, the spare and the recovery rules.

A stage's blocks run alone and in order. Finished blocks are not run again (resume). A pass whose counter is below prediction ends its block and is recovered by the stage's ``recover`` callback (E2: the file is rebuilt once;
a second pollution is PAUSED). An invalid block is replaced once by the spare (repeat 6, seeds 280006 and 280206; E2 only; M and K have no spare). An ENGINEERING STOP is recorded with its cause and ends the stage; a
rerun after it uses the spare's tiles and seeds only, at most one, and only with a recorded amendment naming the stop. Every wait has a deadline (``system.wait_for_quiet``).
"""

import os
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import analysis, bench, core, system
from .core import EngineeringStop, Paused
from .device import Counter, PRead


@dataclass
class Deps:
    """Everything a stage touches outside itself, injectable so that the whole loop is tested with fakes (no device)."""

    counter: Counter
    gate: bench.QuietGate
    run: system.Run = system.run_command
    run_b: Callable[[Sequence[str]], tuple[int, bytes]] = system.run_bytes
    sleep: system.Sleep = time.sleep
    clock: system.Clock = time.monotonic
    pread: PRead = os.pread
    opener: Callable[[Any, bool], int] | None = None
    cross_check: Callable[[], dict[str, Any]] | None = None
    pass_runner: Callable[[bench.Context, Mapping[str, Any]], bench.PassRunner] | None = None  # None: one process per pass (production)


@dataclass
class StageState:
    """The resumable state of a stage, in ``<run>/<stage>/state.json``."""

    path: Path
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "StageState":
        d = read_json(path) if path.is_file() else {}
        d.setdefault("status", "NOT STARTED")
        for k, v in (("quiet_sessions_failed", 0), ("quiet_exhausted", False), ("spare_used", None), ("rebuilds", 0), ("pollutions", 0), ("write_budget_declined", False), ("engineering_stop", None), ("next_seq", 1), ("history", [])):
            d.setdefault(k, v)
        return cls(path, d)

    def save(self) -> None:
        core.write_record(self.path, {**core.envelope("stage_manifest"), **self.data}, overwrite=True)

    def note(self, event: str, **detail: Any) -> None:
        self.data["history"].append({"event": event, "utc": core.utc_stamp(), **detail})


def stop_path(ctx: bench.Context, stop_id: str) -> Path:
    return ctx.stage_dir() / "stops" / f"{core.safe_name(stop_id)}.json"


def record_stop(ctx: bench.Context, key: str, cause: str, detail: str) -> str:
    """An engineering stop is recorded with its cause (``resolved`` False until a complete rerun on the spare names it)."""
    stop_id = f"{ctx.stage}|{key}|{cause}"
    core.write_record(stop_path(ctx, stop_id), {**core.envelope("engineering_stop"), "id": stop_id, "stage": ctx.stage, "key": key, "cause": cause, "detail": detail, "utc": core.utc_stamp(), "resolved": False}, overwrite=True)
    return stop_id


def load_stops(ctx: bench.Context) -> list[dict[str, Any]]:
    d = ctx.stage_dir() / "stops"
    return [read_json(p) for p in sorted(d.glob("*.json"))] if d.is_dir() else []


def resolved_stops(ctx: bench.Context, blocks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """A stop is resolved only when a COMPLETE spare block names it (``rerun_of``)."""
    done = {b.get("rerun_of") for b in blocks if b["role"] == "spare" and b.get("complete")}
    return [{**s, "resolved": s["id"] in done} for s in load_stops(ctx)]


def spawn_pass_runner(ctx: bench.Context, extra_argv: Sequence[str], attempt: int = 1, timeout: float = 900.0) -> bench.PassRunner:
    """One process per pass: ``python -m studies.p10is5.stages work-pass ...`` (it re-checks identity, derives the pass again from the plan or the config and writes the pass record). Exit 75: PAUSED — IDENTITY
    (nothing written); exit 70: ENGINEERING STOP (the worker recorded the cause); anything else non-zero is an ENGINEERING STOP (WORKER FAILED)."""

    def run_one(repeat: int, k: int, s: int, block: str, role: str, seq: int) -> dict[str, Any]:
        argv = [sys.executable, "-m", "studies.p10is5.stages", "work-pass", "--stage", ctx.stage, "--run-dir", str(ctx.run_dir), "--repeat", str(repeat), "--k", str(k), "--s", str(s), "--attempt", str(attempt), "--block", block, "--role", role, "--seq", str(seq), *extra_argv]
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603 - argument list, no shell
        except subprocess.TimeoutExpired as e:
            raise EngineeringStop("WORKER TIMEOUT", f"{core.pass_key(ctx.stage, repeat, k, s, attempt)} after {timeout} s") from e
        key = core.pass_key(ctx.stage, repeat, k, s, attempt)
        if p.returncode == core.IDENTITY_EXIT:
            raise Paused(core.PAUSED_IDENTITY, p.stderr.strip()[-300:])
        if p.returncode != 0:
            stops = [x for x in load_stops(ctx) if x["key"] == key]
            raise EngineeringStop(stops[-1]["cause"] if stops else "WORKER FAILED", (stops[-1]["detail"] if stops else p.stderr.strip()[-300:]))
        path = ctx.pass_path(key)
        if not path.is_file():
            raise EngineeringStop("WORKER FAILED", f"exit status 0 but no pass record for {key}")
        return core.read_record(path, "pass")

    return run_one


def inprocess_pass_runner(ctx: bench.Context, deps: Deps, prediction: Mapping[str, Any], attempt: int = 1) -> bench.PassRunner:
    """The same pass, in this process (used by the tests with fakes, and by R1-style passes)."""

    def run_one(repeat: int, k: int, s: int, block: str, role: str, seq: int) -> dict[str, Any]:
        rec = bench.execute_pass(ctx, repeat, k, s, attempt, prediction, deps.counter, block=block, role=role, seq=seq, pread=deps.pread, cross_check=deps.cross_check, opener=deps.opener)
        bench.commit_pass(ctx, rec)
        return rec

    return run_one


def block_status(ctx: bench.Context) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    passes, blocks = bench.load_stage_records(ctx)
    cells = ctx.geometry.cells()
    sel = analysis.select_valid(blocks, passes, cells) if blocks else {"valid": [], "invalid": [], "replaced_block": None, "spare_block": None, "verdicts": {}}
    return passes, blocks, sel


def run_stage_blocks(
    ctx: bench.Context,
    deps: Deps,
    state: StageState,
    runner_for: Callable[[int], bench.PassRunner],
    *,
    hours: core.HoursLedger | None = None,
    recover: Callable[[], None] | None = None,
    rerun_after_stop: str | None = None,
    extra_sessions: int = 3,
) -> StageState:
    """Run (or resume) the stage's blocks. Resumable: a block with a record is not run again. Raises ``Paused`` (quiet rule, write budget, hours, identity, second pollution) or ``EngineeringStop``; the state is saved
    first with the status and the cause."""
    regular = [b for b in ctx.blocks if b["role"] == "regular"]
    spare = next((b for b in ctx.blocks if b["role"] == "spare"), None)
    if state.data["engineering_stop"] and rerun_after_stop != state.data["engineering_stop"]:
        raise Paused("PAUSED — ENGINEERING STOP UNRESOLVED", f"{state.data['engineering_stop']}: a rerun on the spare's tiles and seeds needs --rerun-after-stop with a recorded amendment")

    def one(repeat: int, role: str, reason: str, rerun_of: str | None = None) -> dict[str, Any]:
        t0 = deps.clock()
        if hours is not None:
            hours.require_room()
        try:
            block = bench.run_block(ctx, repeat, role, reason, deps.gate, runner_for(repeat), int(state.data["next_seq"]), rerun_of=rerun_of)
        except Paused as e:
            if e.reason == "PAUSED — MACHINE NOT QUIET":
                state.data["quiet_sessions_failed"] += 1
                state.data["quiet_exhausted"] = state.data["quiet_sessions_failed"] >= 1 + extra_sessions
            state.data["status"] = f"{e.reason}"
            state.note("paused", reason=e.reason, detail=e.detail)
            state.save()
            raise
        except EngineeringStop as e:
            stop_id = record_stop(ctx, core.block_key(ctx.stage, repeat), e.cause, e.detail)
            core.write_record(ctx.block_path(core.block_key(ctx.stage, repeat)), {**core.envelope("block"), "key": core.block_key(ctx.stage, repeat), "stage": ctx.stage, "repeat": repeat, "role": role, "reason": reason, "rerun_of": rerun_of, "pass_keys": [], "complete": False, "aborted": f"ENGINEERING STOP ({e.cause})", "quiet_start": None, "quiet_end": None}, overwrite=True)
            state.data["engineering_stop"] = stop_id
            state.data["status"] = f"ENGINEERING STOP ({e.cause})"
            state.note("engineering_stop", cause=e.cause, detail=e.detail)
            state.save()
            raise
        state.data["next_seq"] = block["next_seq"]
        if hours is not None:
            hours.charge(ctx.stage, block["key"], deps.clock() - t0)
        state.note("block", key=block["key"], complete=block["complete"], aborted=block["aborted"])
        state.save()
        return block

    state.data["status"] = "RUNNING"
    state.save()
    if rerun_after_stop:
        if spare is None or state.data["spare_used"]:
            raise core.StageRefused("refused: the spare is not available: it serves one invalid block or one rerun, not both")
        state.data["spare_used"] = f"rerun_after_stop:{rerun_after_stop}"
        state.data["engineering_stop"] = None
        state.save()
        one(spare["repeat"], "spare", "RERUN_AFTER_STOP", rerun_of=rerun_after_stop)
    for b in regular:
        if bench.block_done(ctx, b["repeat"]):
            continue
        block = one(b["repeat"], "regular", "REGISTERED")
        if block["aborted"]:
            state.data["pollutions"] += 1
            state.note("pollution", block=block["key"], detail=block["aborted"])
            if recover is None:
                state.save()
            else:
                if state.data["pollutions"] > 1:
                    state.data["status"] = "PAUSED — STORE POLLUTED AGAIN"
                    state.save()
                    raise Paused("PAUSED — STORE POLLUTED AGAIN", "a second pollution: a restart, or purge, is the human lead's action")
                try:
                    recover()
                except Paused as e:
                    if isinstance(e, core.WriteBudgetExceeded):
                        state.data["status"] = e.reason
                    state.save()
                    raise
                state.data["rebuilds"] += 1
                state.save()
    if spare is not None and not state.data["spare_used"] and not bench.block_done(ctx, spare["repeat"]):
        _, _, sel = block_status(ctx)
        if sel["invalid"]:
            state.data["spare_used"] = "invalid_block"
            state.save()
            one(spare["repeat"], "spare", "REPLACES_FIRST_INVALID_BLOCK")
    _, blocks, _ = block_status(ctx)
    state.data["status"] = "COMPLETE"
    state.data["blocks"] = [b["key"] for b in blocks]
    state.save()
    return state
