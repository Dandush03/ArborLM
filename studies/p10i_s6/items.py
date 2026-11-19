# ruff: noqa: E501
"""P10IS6 items and workers (ADR-0031 sections 8, 9.4, 16, 16a G1, G2, G12, G15).

``registered_items(cfg, rate_table, k_max)`` is the one derivation of the registered plan's items from the config and the frozen rate table: one run per distinct (arm, cell, rate) trained to the largest rung that rate serves (run sharing),
snapshots at 0, 8,192 and every rung up to the run's maximum, one evaluation per snapshot (``step0``, ``enabled``, ``triple`` at rung -1, ``full`` at the rungs the run serves), plus the OA block. Every rung always runs (section 9.4). Calibration
items are derived the same way from the grid. Every stage reads its items from ``freeze/plan.json`` only.

A training item that stops at a rung on the pause request is PAUSED (no record is written) and resumes from its last snapshot when the resume-identity gate passed; otherwise a restart is from update 0 (ruling 6). A failed cell (non-finite loss,
gradient norm or parameter) ends the run with status ``failed_cell``. Anything else is an item error. Nothing in this module can extend the ladder: the largest update count of an item is a rung of the plan's ``k_max``.
"""

import math
import shutil
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from torch import Tensor

from . import core, model
from .core import DENSE, FLAT, FailedCell

PAUSE_EXIT = 76


def rate_for(rt: Mapping[str, Any], arm: str, k: int) -> float:
    return float(rt["rates"][arm][str(k)])


def run_groups(cfg: Mapping[str, Any], rt: Mapping[str, Any], arm: str, k_max: int) -> list[dict[str, Any]]:
    """The distinct runs of one (arm, cell): by rate, ascending; ``serves`` the rungs read from it (-1..k_max), ``max_update`` the largest update count of those rungs, ``snapshots`` 0, 8,192 and every rung up to it, ``modes`` the evaluation mode of each snapshot."""
    by_rate: dict[float, list[int]] = {}
    for k in core.rung_range(k_max):
        by_rate.setdefault(rate_for(rt, arm, k), []).append(k)
    groups = []
    for rate in sorted(by_rate):
        serves = by_rate[rate]
        top = core.rung_updates(cfg, max(serves))
        snaps = sorted({0, core.rung_updates(cfg, -1), *(core.rung_updates(cfg, k) for k in range(0, k_max + 1) if core.rung_updates(cfg, k) <= top)})
        modes: dict[int, str] = {u: "enabled" for u in snaps}
        modes[0] = "step0"
        for k in serves:
            modes[core.rung_updates(cfg, k)] = "triple" if k == -1 else "full"
        groups.append({"rate": rate, "serves": serves, "max_update": top, "snapshots": snaps, "modes": modes})
    return groups


def train_id(profile: str, arm: str, rate: float, cell: int) -> str:
    return f"train|{profile}|{arm}|r{core.rate_label(rate)}|c{cell:02d}"


def eval_id(tid: str, update: int) -> str:
    return f"eval|{tid[len('train|'):]}|u{update:06d}"


def _item(profile: str, arm: str, rate: float, cell: int, group: str, parent: int, seeds: core.Seeds, **extra: Any) -> dict[str, Any]:
    return {"id": train_id(profile, arm, rate, cell), "kind": "train", "profile": profile, "arm": arm, "rate": rate, "cell": cell, "backbone_group": group, "parent": parent, "init_seed": seeds.init(cell), "stream_seed": seeds.stream(cell), **extra}


def _evals(tid: str, profile: str, arm: str, rate: float, cell: int, snaps: Sequence[int], modes: Mapping[int, str]) -> list[dict[str, Any]]:
    return [{"id": eval_id(tid, u), "kind": "eval", "train": tid, "profile": profile, "arm": arm, "rate": rate, "cell": cell, "update": u, "controls": modes[u]} for u in snaps]


def registered_items(cfg: Mapping[str, Any], rt: Mapping[str, Any], k_max: int, *, profile: str = "registered", cells: Sequence[int] | None = None, with_oa: bool = True, oa_cells: Sequence[int] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Train and evaluation items of the registered plan (profile ``registered``; the DRY profile passes ``profile="dry"`` and a short cell list)."""
    seeds = core.Seeds(profile, cfg)
    n_cells = core.CELLS_OF[profile]
    cells = list(cells if cells is not None else range(n_cells))
    trains: list[dict[str, Any]] = []
    evals: list[dict[str, Any]] = []
    for arm in core.ARMS:
        for g in run_groups(cfg, rt, arm, k_max):
            for c in cells:
                parent = core.parent_of(c) if profile in ("registered", "test") else 0
                grp = "registered" if profile in ("registered", "test") else "calibration"
                it = _item(profile, arm, g["rate"], c, grp, parent, seeds, max_update=g["max_update"], snapshots=g["snapshots"], serves=g["serves"], pool="registered" if profile == "registered" else "calibration")
                trains.append(it)
                evals += _evals(it["id"], profile, arm, g["rate"], c, g["snapshots"], g["modes"])
    if with_oa:
        oa = core.Seeds("oa", cfg)
        u0, um1 = core.rung_updates(cfg, 0), core.rung_updates(cfg, -1)
        for arm in core.ARMS:
            for c in (oa_cells if oa_cells is not None else range(27)):
                rate = rate_for(rt, arm, 0)
                it = _item("oa", arm, rate, c, "old", core.parent_of(c), oa, max_update=u0, snapshots=[um1, u0], serves=[0], pool="registered")
                trains.append(it)
                evals += _evals(it["id"], "oa", arm, rate, c, [um1, u0], {um1: "enabled", u0: "triple"})
    for lst in (trains, evals):
        ids = [i["id"] for i in lst]
        if len(set(ids)) != len(ids):
            raise ValueError("a plan names an item twice")
    return {"train": trains, "eval": evals}


def calibration_items(cfg: Mapping[str, Any], rates: Mapping[str, Sequence[float]], k_max: int) -> dict[str, list[dict[str, Any]]]:
    """Calibration: one run per (arm, rate, calibration cell) to U_max, snapshots at 8,192 and every rung, the enabled read only (section 8)."""
    seeds = core.Seeds("calibration", cfg)
    snaps = sorted({core.rung_updates(cfg, k) for k in core.rung_range(k_max)})
    trains, evals = [], []
    for arm in core.ARMS:
        for rate in sorted(rates[arm]):
            for q in range(3):
                it = _item("calibration", arm, float(rate), q, "calibration", q, seeds, max_update=core.rung_updates(cfg, k_max), snapshots=snaps, serves=[], pool="calibration")
                trains.append(it)
                evals += _evals(it["id"], "calibration", arm, float(rate), q, snaps, dict.fromkeys(snaps, "enabled"))
    return {"train": trains, "eval": evals}


# --- resources and workers ----------------------------------------------------------------------------------------------------------------------------
@dataclass
class Resources:
    cfg: Mapping[str, Any]
    table: Tensor  # [rows, 65] uint8 (memory-mapped in a real run)
    pools: Mapping[str, tuple[int, int]]  # "registered" | "calibration" -> (start, size) in the table
    panels: Mapping[str, Tensor]  # "registered" | "calibration"
    backbone: Callable[[str, int], Any]  # (group, parent) -> Backbone (deep-copied per use by the caller)
    expected_targets: int = 32768
    resume_ok: bool = False  # the resume-identity gate passed (otherwise a restart is from update 0)

    def panel_for(self, profile: str) -> Tensor:
        return self.panels["registered" if profile in ("registered", "oa", "test") else "calibration"]


def _identity(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: item[k] for k in ("arm", "rate", "cell", "init_seed", "stream_seed", "profile")}


def item_dir(run_dir: Path, item_id: str) -> Path:
    return run_dir / "items" / item_id.replace("|", "__").replace("/", "~")


def train_record_path(run_dir: Path, item: Mapping[str, Any]) -> Path:
    return item_dir(run_dir, item["id"]) / "train.json"


def eval_record_path(run_dir: Path, item: Mapping[str, Any]) -> Path:
    return item_dir(run_dir, item["id"]) / "eval.json"


def _build(res: Resources, item: Mapping[str, Any]) -> model.S3Model:
    import copy

    return model.build_model(copy.deepcopy(res.backbone(item["backbone_group"], int(item["parent"]))), item["arm"], int(item["init_seed"]))


def _last_snapshot(root: Path, wanted: Sequence[int]) -> int | None:
    done = [u for u in wanted if (model.snapshot_dir(root, u) / "index.json").is_file()]
    return max(done) if done else None


def run_train(res: Resources, item: Mapping[str, Any], run_dir: Path, public_dir: Path | None = None) -> dict[str, Any]:
    """Train (or resume) one run. Returns the record; a paused run returns ``{"status": "paused"}`` and writes no record."""
    d = item_dir(run_dir, item["id"])
    rec_path = d / "train.json"
    if rec_path.is_file():
        return core.read_record(rec_path, "train")
    snap_root = d / "snapshots"
    start_step = _last_snapshot(snap_root, [int(x) for x in item["snapshots"]])
    if start_step is not None and (not res.resume_ok or start_step >= int(item["max_update"])) and d.exists():
        shutil.rmtree(d)  # ruling 6: without the resume-identity gate a restart is from update 0 and partial snapshots are discarded
        start_step = None
    pstart, psize = res.pools[item["pool"]]
    stream = model.PoolStream(res.table, pstart, psize, int(item["stream_seed"]))
    m = _build(res, item)
    ident = _identity(item)
    opt = None
    start = 0
    if start_step is not None and start_step > 0:
        opt = model.restore_for_resume(snap_root, m, float(item["rate"]), start_step, ident)
        start = start_step
    pause = (lambda: core.pause_requested(public_dir)) if public_dir is not None else None
    out = model.train_run(m, stream, float(item["rate"]), snap_root, [int(x) for x in item["snapshots"]], int(item["max_update"]), ident, start=start, optimizer=opt, pause_check=pause)
    if out["status"] == "paused":
        return {"status": "paused", "resume_from": out["resume_from"]}
    have = sorted(u for u in (int(x) for x in item["snapshots"]) if (model.snapshot_dir(snap_root, u) / "index.json").is_file())
    rec = {**core.envelope("train"), "id": item["id"], "status": out["status"], "reason": out.get("reason"), "failed_at_update": out.get("failed_at_update"), "snapshots": have, "seconds": out["seconds"], "updates_done": out["updates_done"], "resumed_from": start or None, "trainable_parameters": model.trainable_count(m)}
    core.write_record(rec_path, rec)
    return rec


def run_eval(res: Resources, item: Mapping[str, Any], run_dir: Path, train_rec: Mapping[str, Any], train_item: Mapping[str, Any]) -> dict[str, Any]:
    """One snapshot: restore, evaluate (reference reads), restore into a fresh model and evaluate again (replay). A snapshot the failed run did not produce gives a skipped record. A non-finite enabled NLL gives None for every read."""
    path = eval_record_path(run_dir, item)
    if path.is_file():
        return core.read_record(path, "eval")
    update, mode, arm = int(item["update"]), item["controls"], item["arm"]
    snap_root = item_dir(run_dir, item["train"]) / "snapshots"
    if update not in [int(x) for x in train_rec["snapshots"]]:
        rec = {**core.envelope("eval"), "id": item["id"], "skipped": "the run failed before this snapshot", "reads": {}, "stats": {}, "update": update, "controls": mode}
        core.write_record(path, rec)
        return rec
    seeds = core.Seeds(item["profile"], res.cfg)
    panel = res.panel_for(item["profile"])
    ident = _identity(train_item)
    draws = int(res.cfg["controls"]["p_used_draws"])
    m = _build(res, train_item)
    model.restore_snapshot(snap_root, m, update, ident)
    keys = [f"{r}|{d}" for r, d in core.read_list(arm, mode, draws)]
    try:
        out = model.evaluate_reads(m, panel, seeds, int(item["cell"]), mode, draws=draws, expected_targets=res.expected_targets)
        reads, stats = out["reads"], out["stats"]
        if core.READ_REPLAY in {r for r, _ in core.read_list(arm, mode, draws)}:
            m2 = _build(res, train_item)
            model.restore_snapshot(snap_root, m2, update, ident)
            rp = model.evaluate(m2, panel, expected_targets=res.expected_targets)
            reads[f"{core.READ_REPLAY}|0"] = rp if math.isfinite(rp) else None
        nonfinite = False
    except FailedCell:
        reads, stats, nonfinite = dict.fromkeys(keys), {}, True
    rec = {**core.envelope("eval"), "id": item["id"], "reads": reads, "stats": stats, "nonfinite_enabled": nonfinite, "update": update, "controls": mode}
    core.write_record(path, rec)
    return rec


def guarded(path: Path, item_id: str, fn: Callable[[], Any], kind: str = "train") -> Any:
    """An exception that is not a failed cell is an ``item_error``: recorded with its traceback, never a scientific NOT EVALUABLE (section 12.1); the exception propagates."""
    try:
        return fn()
    except core.EngineeringStop:
        raise
    except Exception as e:
        path.parent.mkdir(parents=True, exist_ok=True)
        core.write_record(path, {**core.envelope(kind), "id": item_id, "status": "item_error", "item_kind": kind, "reason": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-4000:]}, overwrite=True)
        raise


# --- the registry from records ---------------------------------------------------------------------------------------------------------------------------
def collect_registry(run_dir: Path, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], bases: Mapping[str, Mapping[str, float | None]] | None = None) -> dict[str, Any]:
    """The analysis registry (keys of ``core``) from the records of the planned items only. A planned item without a record is absent (the analysis then refuses). An item error of any kind refuses here too."""
    reg: dict[str, Any] = {}
    errors = []
    for kind, path_of in (("train", train_record_path), ("eval", eval_record_path)):
        for it in plan_items[kind]:
            p = path_of(run_dir, it)
            if p.is_file() and core.read_record(p, kind).get("status") == "item_error":
                errors.append(it["id"])
    if errors:
        raise core.EngineeringStop(f"ENGINEERING STOP — ITEM ERRORS: {len(errors)} item(s), first {errors[0]}; nothing is labelled")
    for it in plan_items["train"]:
        p = train_record_path(run_dir, it)
        if p.is_file():
            rec = core.read_record(p, "train")
            reg[core.run_key(it["arm"], it["rate"], it["cell"], oa=it["profile"] == "oa")] = {"status": rec["status"], "reason": rec.get("reason")}
    for it in plan_items["eval"]:
        p = eval_record_path(run_dir, it)
        if not p.is_file():
            continue
        rec = core.read_record(p, "eval")
        oa = it["profile"] == "oa"
        for k, v in rec["reads"].items():
            read, draw = k.split("|")
            reg[core.nll_key(it["arm"], it["rate"], it["cell"], it["update"], read, int(draw), oa=oa)] = v
        if "used_slots" in rec["stats"]:
            reg[core.stat_key(it["arm"], it["rate"], it["cell"], it["update"], "used_slots")] = rec["stats"]["used_slots"]
    for parent, d in (bases or {}).items():
        oa = str(parent).startswith("oa")
        pi = int(str(parent).removeprefix("oa"))
        reg[core.base_key(pi, oa=oa)] = d["enabled"]
        reg[core.base_key(pi, core.READ_REPLAY, oa=oa)] = d["replay"]
    return reg


__all__ = ["DENSE", "FLAT"]
