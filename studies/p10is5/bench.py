# ruff: noqa: E501
"""P10IS5 benchmark core, shared by M, K and E2 (ADR-0028 sections 5.2, 7, 8, 9; rulings 3 to 9, 12): the pass context (geometry, tiles, seeds, file) derived from the plan or the config, the prediction record,
one pass (``execute_pass``), and the block runner with the quiet rule.

The prediction record (stage P) holds, for every pass, the ordered request list (index, thread, offset, length), the predicted bytes (16,384 x pages) and the expected SHA-256 of every page (regenerated from the
seed, never read back). Each pass derives its requests again from the plan and asserts they equal the record's before issuing any: a difference is ENGINEERING STOP (PREDICTION MISMATCH). E2 refuses to start on a prediction record
whose SHA-256 is not the one P recorded.
"""

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import core, harness, layout
from .core import EngineeringStop, Geometry
from .device import Counter, PRead


@dataclass(frozen=True)
class Context:
    """Everything a pass needs, from the plan (E2, K) or the config (M): never from a record of an earlier pass."""

    stage: str  # "E2", "M" or "K"
    geometry: Geometry
    contents_seed: int
    assignment_seed: int
    blocks: tuple[Mapping[str, Any], ...]
    file_path: Path
    run_dir: Path
    memory_guard_bytes: int

    def block_def(self, repeat: int) -> Mapping[str, Any]:
        for b in self.blocks:
            if b["repeat"] == repeat:
                return b
        raise core.StageRefused(f"refused: repeat {repeat} is not defined for stage {self.stage}")

    def stage_dir(self) -> Path:
        return self.run_dir / self.stage

    def pass_path(self, key: str) -> Path:
        return self.stage_dir() / "passes" / f"{core.safe_name(key)}.json"

    def block_path(self, key: str) -> Path:
        return self.stage_dir() / "blocks" / f"{core.safe_name(key)}.json"

    def prediction_path(self) -> Path:
        return self.stage_dir() / "prediction.json"

    def prediction_manifest_path(self) -> Path:
        return self.stage_dir() / "prediction_manifest.json"


def context_m(cfg: Mapping[str, Any], data_dir: Path, run_dir: Path) -> Context:
    """M's context from the config (no plan exists yet): the rehearsal geometry, M's seeds, the rehearsal file."""
    s = cfg["seeds"]
    blocks = tuple({"repeat": i + 1, "role": "regular", "request_order_seed": int(s["m_request_order"][i]), "pass_order_seed": int(s["m_pass_order"][i])} for i in range(len(s["m_request_order"])))
    return Context("M", core.rehearsal_geometry(cfg), int(s["r1_rehearsal_file_contents"]), int(s["m_tile_assignment"]), blocks, data_dir / "rehearsal.bin", run_dir, int(cfg["resources"]["memory_guard_bytes"]))


def context_from_plan(stage: str, plan: Any, run_dir: Path, cfg: Mapping[str, Any]) -> Context:
    """E2's context (the registered section) or K's (the counting-rehearsal section), from the plan file only."""
    which = "registered" if stage == "E2" else "k"
    sec = plan.section(which)
    paths = plan.paths
    geo = plan.geometry("registered" if stage == "E2" else "rehearsal")
    return Context(stage, geo, int(sec["file_contents_seed"]), int(sec["tile_assignment_seed"]), tuple(plan.blocks(which)), Path(paths["store"] if stage == "E2" else paths["rehearsal_file"]), run_dir, int(cfg["resources"]["memory_guard_bytes"]))


def derive_pass(ctx: Context, repeat: int, k: int, s: int, dealt: Mapping[tuple[int, int, int], list[int]] | None = None) -> list[layout.Request]:
    dealt = dealt if dealt is not None else layout.deal(ctx.geometry, ctx.assignment_seed)
    b = ctx.block_def(repeat)
    return layout.pass_requests(dealt[(repeat, k, s)], k, s, ctx.geometry.n_of[s], int(b["request_order_seed"]))


def requests_json(reqs: Sequence[layout.Request]) -> list[list[int]]:
    return [[r.index, r.thread, r.offset, r.length] for r in reqs]


def pass_id(repeat: int, k: int, s: int) -> str:
    return f"r{repeat}|k{k}|s{s}"


def build_prediction(ctx: Context) -> dict[str, Any]:
    """Stage P (section 5.2): every pass's requests, predicted bytes and expected page hashes."""
    dealt = layout.deal(ctx.geometry, ctx.assignment_seed)
    cache: dict[int, list[str]] = {}
    passes: dict[str, Any] = {}
    for repeat in ctx.geometry.all_repeats:
        for k, s in ctx.geometry.cells():
            reqs = derive_pass(ctx, repeat, k, s, dealt)
            passes[pass_id(repeat, k, s)] = {"requests": requests_json(reqs), "predicted_bytes": layout.predicted_bytes(reqs), "page_sha256": layout.expected_page_hashes(ctx.contents_seed, reqs, cache)}
    return {**core.envelope("prediction"), "stage": ctx.stage, "geometry": ctx.geometry.name, "contents_seed": ctx.contents_seed, "assignment_seed": ctx.assignment_seed, "passes": passes}


def write_prediction(ctx: Context) -> dict[str, Any]:
    """Write the prediction record once and its manifest (the SHA-256 E2 refuses to differ from)."""
    if ctx.prediction_path().exists():
        raise core.StageRefused(f"refused: {ctx.prediction_path()} exists; the prediction is written once")
    rec = build_prediction(ctx)
    core.write_record(ctx.prediction_path(), rec)
    man = {**core.envelope("prediction_manifest"), "stage": ctx.stage, "path": str(ctx.prediction_path()), "sha256": file_sha256(ctx.prediction_path()), "passes": len(rec["passes"])}
    core.write_record(ctx.prediction_manifest_path(), man)
    return man


def load_prediction(ctx: Context) -> dict[str, Any]:
    """The prediction record, refused unless its SHA-256 is the one stage P recorded."""
    if not ctx.prediction_manifest_path().is_file() or not ctx.prediction_path().is_file():
        raise core.StageRefused(f"refused: no prediction record under {ctx.stage_dir()}: run stage P first")
    man = core.read_record(ctx.prediction_manifest_path(), "prediction_manifest")
    if file_sha256(ctx.prediction_path()) != man["sha256"]:
        raise core.StageRefused(f"refused: the prediction record does not hash to the SHA-256 stage P recorded ({core.PAUSED_IDENTITY})")
    return core.read_record(ctx.prediction_path(), "prediction")


def check_against_prediction(reqs: Sequence[layout.Request], pred_pass: Mapping[str, Any]) -> None:
    """Each pass derives its requests again from the plan and asserts they equal the record's before issuing any; a difference is ENGINEERING STOP (PREDICTION MISMATCH)."""
    if json.loads(json.dumps(requests_json(reqs))) != pred_pass["requests"] or layout.predicted_bytes(reqs) != pred_pass["predicted_bytes"]:
        raise EngineeringStop("PREDICTION MISMATCH", "the requests derived from the plan differ from the prediction record")


def execute_pass(
    ctx: Context,
    repeat: int,
    k: int,
    s: int,
    attempt: int,
    prediction: Mapping[str, Any],
    counter: Counter,
    *,
    block: str,
    role: str,
    seq: int,
    pread: PRead = os.pread,
    cross_check: Callable[[], dict[str, Any]] | None = None,
    opener: Callable[[Any, bool], int] | None = None,
) -> dict[str, Any]:
    """One pass (in production: its own process). Order: derive the requests, assert them against the prediction, hold the expected hashes, run the threaded pass between two counter snapshots, then (after the last
    snapshot) hash every page against the prediction and apply the memory guard. Returns the pass record; a code or environment error propagates (the caller records ENGINEERING STOP)."""
    reqs = derive_pass(ctx, repeat, k, s)
    pp = prediction["passes"][pass_id(repeat, k, s)]
    check_against_prediction(reqs, pp)
    expected = pp["page_sha256"]
    res = harness.run_pass(ctx.file_path, reqs, k, counter, pread=pread, cross_check=cross_check, opener=opener)
    parity = harness.parity_ok(reqs, res.data, expected)
    rec = harness.pass_record(ctx.stage, repeat, k, s, attempt, reqs, res, parity=parity, block=block, role=role, predicted_override=int(pp["predicted_bytes"]))
    rec["seq"] = seq
    rec["memory_guard_exceeded"] = res.counter_end.phys_footprint > ctx.memory_guard_bytes
    rec["expected_digest"] = harness.expected_digest(expected)
    return rec


def commit_pass(ctx: Context, rec: Mapping[str, Any]) -> None:
    """Write the pass record FIRST (EQ-A covers every pass that has both counter snapshots, a stopped one included), then raise the engineering stops of section 7 item 6 and section 9: a page hash that differs from the
    prediction is ENGINEERING STOP (DATA MISMATCH); a footprint above 4 GiB is ENGINEERING STOP (MEMORY GUARD). Neither is ever a label."""
    write_pass(ctx, rec)
    if rec.get("parity_ok") is False:
        raise EngineeringStop("DATA MISMATCH", f"{rec['key']}: {rec.get('parity_bad_pages')} page(s) differ from the expected SHA-256")
    if rec.get("memory_guard_exceeded"):
        raise EngineeringStop("MEMORY GUARD", f"{rec['key']}: footprint above {ctx.memory_guard_bytes} B")


# --- the block runner and the quiet rule --------------------------------------------------------------------------------------------------------
@dataclass
class QuietGate:
    """The quiet rule at the start and the end of a block. ``read`` is one reading (``system.read_quiet``); ``wait`` retries it (``system.wait_for_quiet``); ``settle`` sleeps the 120 s before the end reading."""

    read: Callable[[], dict[str, Any]]
    wait: Callable[[Callable[[], dict[str, Any]]], tuple[dict[str, Any] | None, list[dict[str, Any]]]]
    settle: Callable[[], None]

    def at_start(self) -> dict[str, Any]:
        rec, history = self.wait(self.read)
        if rec is None:
            raise core.Paused("PAUSED — MACHINE NOT QUIET", f"{len(history)} readings; the last failed: {history[-1]['failed']}")
        return {**rec, "attempts": len(history)}

    def at_end(self) -> dict[str, Any]:
        self.settle()
        return self.read()


PassRunner = Callable[[int, int, int, str, str, int, int], dict[str, Any]]  # (repeat, k, s, block key, role, seq, attempt) -> pass record


def next_attempt(ctx: Context, repeat: int) -> int:
    """1 + the highest attempt of any pass record already written for this repeat. A block that stopped halfway (a worker's exit 75, a kill, a sleep) leaves its pass records where they are (EQ-A counts every pass
    attempted) and is run again under attempt + 1 keys: no key is ever written twice."""
    d = ctx.stage_dir() / "passes"
    best = 0
    if d.is_dir():
        for p in d.glob(f"{core.safe_name(ctx.stage)}_r{repeat}_k*_s*_a*.json"):
            best = max(best, core.parse_pass_key(p.stem.replace("_", "|"))[4])
    return best + 1


def run_block(ctx: Context, repeat: int, role: str, reason: str, gate: QuietGate, run_one: PassRunner, seq_start: int, *, rerun_of: str | None = None) -> dict[str, Any]:
    """One block: the quiet reading at its start (before any pass process starts), the 24 passes in the repeat's seeded order (one process each, alone), the quiet reading at its end (after the last pass has exited and
    the settle time). A pass whose counter is below prediction (STORE PAGES CACHED) ends the block at once (it and its block are invalid; the caller handles the recovery of section 7, item 5). The block record is written
    to the run directory. Returns it."""
    bkey = core.block_key(ctx.stage, repeat)
    attempt = next_attempt(ctx, repeat)
    qs = gate.at_start()
    order = layout.pass_order(int(ctx.block_def(repeat)["pass_order_seed"]), ctx.geometry)
    keys: list[str] = []
    aborted: str | None = None
    seq = seq_start
    for k, s in order:
        rec = run_one(repeat, k, s, bkey, role, seq, attempt)
        seq += 1
        keys.append(rec["key"])
        if rec["counter_status"] == core.STORE_PAGES_CACHED:
            aborted = f"{rec['key']}: {core.STORE_PAGES_CACHED}"
            break
    qe = gate.at_end()
    block = {
        **core.envelope("block"), "key": bkey, "stage": ctx.stage, "repeat": repeat, "role": role, "reason": reason, "rerun_of": rerun_of, "order": [list(c) for c in order], "pass_keys": keys, "complete": aborted is None and len(keys) == len(order),
        "aborted": aborted, "attempt": attempt, "quiet_start": qs, "quiet_end": qe, "passes_run": len(keys), "next_seq": seq,
    }  # fmt: skip
    core.write_record(ctx.block_path(bkey), block)
    return block


def block_done(ctx: Context, repeat: int) -> bool:
    return ctx.block_path(core.block_key(ctx.stage, repeat)).is_file()


def load_stage_records(ctx: Context) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(passes, blocks) of a stage from its run directory, in sequence order."""
    passes = [read_json(p) for p in sorted((ctx.stage_dir() / "passes").glob("*.json"))] if (ctx.stage_dir() / "passes").is_dir() else []
    blocks = [read_json(p) for p in sorted((ctx.stage_dir() / "blocks").glob("*.json"))] if (ctx.stage_dir() / "blocks").is_dir() else []
    return sorted(passes, key=lambda r: r["seq"]), sorted(blocks, key=lambda r: (r["repeat"], r["key"]))


def write_pass(ctx: Context, rec: Mapping[str, Any]) -> None:
    core.write_record(ctx.pass_path(rec["key"]), rec)


def write_json_plain(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, core.jsonable(obj))
