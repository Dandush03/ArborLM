# ruff: noqa: E501
"""P10IS3 items and workers (ADR-0026 sections 5 to 9, 16 rulings 6, 10, 15).

``registered_items(cfg, rate_table)`` is the one derivation of the plan's items (a pure function of the config and the frozen rate table): train items (one run per arm, regime, cell and distinct rate group), eval
items (one per snapshot) and the P4-rate anchor runs. Every stage reads its items from ``freeze/plan.json`` only. A worker restarts a training run from update 0 and discards its partial snapshots (ruling 6); an
evaluation is resumable per (run, checkpoint): its record is written last.

``Resources`` carries what a worker reads (rows of the three regimes, the registered and calibration panels, a backbone loader). Registered and rehearsal modes build it from the real corpus and parents; tests build a synthetic one.
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
from .core import DENSE, FRESH, REP, TREE, FailedCell


# --- the items --------------------------------------------------------------------------------------------------------------------------
def run_groups(cfg: Mapping[str, Any], rt: Mapping[str, Any], arm: str, regime: str, *, anchor_rate: float | None = None) -> list[dict[str, Any]]:
    """The runs of one (arm, regime, cell): the primary run at the rate for U* (snapshots at every checkpoint, full controls where its rate is the rate of that duration, enabled reads elsewhere) and one run per other distinct
    rate (snapshots at the durations that use it, full controls). The anchor run (REP, M-TREE and D-ADAPT, rate for U* not 0.003) is run at the P4 rate to U* with enabled reads only."""
    ckpts = [int(x) for x in cfg["duration"]["checkpoints"]]
    u = int(cfg["duration"]["u_star"])
    rates = {d: float(rt["rates"][f"{arm}|{regime}"][str(d)]) for d in ckpts}
    primary = rates[u]
    groups: list[dict[str, Any]] = [{"role": "primary", "rate": primary, "snapshots": ckpts, "max_update": u, "full": [d for d in ckpts if rates[d] == primary]}]
    for r in sorted({v for v in rates.values() if v != primary}):
        ds = [d for d in ckpts if rates[d] == r]
        groups.append({"role": "duration", "rate": r, "snapshots": ds, "max_update": max(ds), "full": ds})
    if anchor_rate is not None and regime == REP and arm in (TREE, DENSE) and primary != anchor_rate:
        groups.append({"role": "anchor", "rate": anchor_rate, "snapshots": ckpts, "max_update": u, "full": []})
    return groups


def train_id(arm: str, regime: str, rate: float, cell: int) -> str:
    return f"train|{arm}|{regime}|r{core.rate_label(rate)}|c{cell:02d}"


def eval_id(arm: str, regime: str, rate: float, cell: int, update: int) -> str:
    return f"eval|{arm}|{regime}|r{core.rate_label(rate)}|c{cell:02d}|u{update:05d}"


def registered_items(cfg: Mapping[str, Any], rt: Mapping[str, Any], *, profile: str = "registered", cells: Sequence[int] | None = None) -> dict[str, list[dict[str, Any]]]:
    seeds = core.Seeds(profile, cfg)
    cells = list(cells if cells is not None else range(27))
    anchor = float(cfg["rates"]["p4_rate"])
    trains: list[dict[str, Any]] = []
    evals: list[dict[str, Any]] = []
    for g in core.REGIMES:
        for arm in core.REGIME_ARMS[g]:
            for c in cells:
                parent = core.parent_of(c) if profile in ("registered", "test") else core.calibration_parent(c)
                for grp in run_groups(cfg, rt, arm, g, anchor_rate=anchor):
                    tid = train_id(arm, g, grp["rate"], c)
                    snaps = ([0] if grp["role"] == "primary" else []) + list(grp["snapshots"])
                    trains.append({"id": tid, "kind": "train", "profile": profile, "arm": arm, "regime": g, "cell": c, "parent": parent, "rate": grp["rate"], "role": grp["role"], "max_update": grp["max_update"], "snapshots": snaps, "init_seed": seeds.init(c), "stream_seed": seeds.stream(c, core.REGIME_INDEX[g])})  # fmt: skip
                    for u in snaps:
                        mode = "step0" if u == 0 else "full" if u in grp["full"] else "enabled"
                        evals.append({"id": eval_id(arm, g, grp["rate"], c, u), "kind": "eval", "train": tid, "profile": profile, "arm": arm, "regime": g, "cell": c, "parent": parent, "rate": grp["rate"], "update": u, "controls": mode, "role": grp["role"]})  # fmt: skip
    for lst in (trains, evals):
        ids = [i["id"] for i in lst]
        if len(set(ids)) != len(ids):
            raise ValueError("a plan names an item twice")
    return {"train": trains, "eval": evals}


# --- resources -------------------------------------------------------------------------------------------------------------------------
@dataclass
class Resources:
    cfg: Mapping[str, Any]
    rows: Mapping[str, Tensor]  # regime -> rows of 65 bytes
    panels: Mapping[str, Tensor]  # "registered" | "calibration"
    backbone: Callable[[int], Any]  # parent index -> Backbone (a deep copy is made per use)
    expected_targets: int = 32768

    def panel_for(self, profile: str) -> Tensor:
        return self.panels["registered" if profile == "registered" else "calibration"]


def _identity(item: Mapping[str, Any]) -> dict[str, Any]:
    return {k: item[k] for k in ("arm", "regime", "rate", "cell", "parent", "init_seed", "stream_seed", "profile")}


def _paths(run_dir: Path, item_id: str) -> Path:
    return run_dir / "items" / item_id.replace("|", "__").replace("/", "~")


def train_record_path(run_dir: Path, item: Mapping[str, Any]) -> Path:
    return _paths(run_dir, item["id"]) / "train.json"


def eval_record_path(run_dir: Path, item: Mapping[str, Any]) -> Path:
    return _paths(run_dir, item["id"]) / "eval.json"


def _build(res: Resources, item: Mapping[str, Any], init_seed: int | None = None) -> model.S3Model:
    import copy

    return model.build_model(copy.deepcopy(res.backbone(int(item["parent"]))), item["arm"], int(item["init_seed"]) if init_seed is None else init_seed)


def run_train(res: Resources, item: Mapping[str, Any], run_dir: Path) -> dict[str, Any]:
    """Restart from update 0 (ruling 6). A non-finite event is a failed run (K1: also in calibration and DRY); anything else propagates to ``guarded`` as an item error."""
    d = _paths(run_dir, item["id"])
    rec_path = d / "train.json"
    if rec_path.is_file():
        return core.read_record(rec_path, "train")
    if d.exists():
        shutil.rmtree(d)  # partial snapshots of an interrupted run are discarded
    regime = item["regime"]
    rows = res.rows[regime]
    stream = model.Stream(rows, int(item["stream_seed"]), fresh=regime == FRESH)
    m = _build(res, item)
    out = model.train_run(m, stream, float(item["rate"]), d / "snapshots", [int(x) for x in item["snapshots"]], int(item["max_update"]), _identity(item))
    rec = {**core.envelope("train"), "id": item["id"], **{k: out[k] for k in ("status", "snapshots", "seconds", "updates_done", "bytes")}, "reason": out.get("reason"), "failed_at_update": out.get("failed_at_update"), "trainable_parameters": model.trainable_count(m)}
    core.write_record(rec_path, rec)
    return rec


def run_eval(res: Resources, item: Mapping[str, Any], run_dir: Path, train_rec: Mapping[str, Any]) -> dict[str, Any]:
    """One checkpoint: restore, evaluate (reference), restore into a fresh model and evaluate again (replay). A failed run has no snapshot: the record says so. A non-finite enabled NLL gives None for every read (K2)."""
    path = eval_record_path(run_dir, item)
    if path.is_file():
        return core.read_record(path, "eval")
    arm, update = item["arm"], int(item["update"])
    if train_rec["status"] != "ok" and str(update) not in train_rec["snapshots"]:
        rec = {**core.envelope("eval"), "id": item["id"], "skipped": "the run failed before this checkpoint", "reads": {}, "stats": {}}
        core.write_record(path, rec)
        return rec
    cfg = res.cfg
    seeds = core.Seeds(item["profile"], cfg)
    panel = res.panel_for(item["profile"])
    snap_root = _paths(run_dir, item["train"]) / "snapshots"
    ident = _identity({**item, "init_seed": _train_seed(item, seeds, "init"), "stream_seed": _train_seed(item, seeds, "stream")})
    m = _build(res, item, ident["init_seed"])
    model.restore_snapshot(snap_root, m, update, ident)
    keys = [f"{r}|{d}" for r, d in core.read_list(arm, int(cfg["controls"]["p_used_draws"]))]
    controls = item["controls"]
    try:
        out = model.evaluate_reads(m, panel, seeds, int(item["cell"]), with_controls=controls == "full", draws_p=int(cfg["controls"]["p_used_draws"]), draws_x=int(cfg["controls"]["x_draws"]), exhaustive_visit=int(cfg["controls"]["exhaustive_visit"]), prior_off_visit=int(cfg["controls"]["prior_off_visit"]), expected_targets=res.expected_targets)
        reads, stats = out["reads"], out["stats"]
        m2 = _build(res, item, ident["init_seed"])
        model.restore_snapshot(snap_root, m2, update, ident)
        replay = model.evaluate(m2, panel, expected_targets=res.expected_targets)
        reads[f"{core.READ_REPLAY}|0"] = replay if math.isfinite(replay) else None
        if controls == "enabled":
            reads = {k: v for k, v in reads.items() if k.startswith(core.READ_ENABLED)}
        elif controls == "step0":
            reads = {k: v for k, v in reads.items() if k.split("|")[0] in (core.READ_ENABLED, core.READ_DISABLED)}
        nonfinite = False
    except FailedCell:
        reads, stats, nonfinite = ({k: None for k in keys} if controls == "full" else {f"{core.READ_ENABLED}|0": None}), {}, True
    stats = {k: v for k, v in stats.items() if k != "usage"} | ({"usage": stats["usage"]} if item["profile"] != "registered" and "usage" in stats else {})
    rec = {**core.envelope("eval"), "id": item["id"], "reads": reads, "stats": stats, "nonfinite_enabled": nonfinite, "update": update, "controls": controls}
    core.write_record(path, rec)
    return rec


def _train_seed(item: Mapping[str, Any], seeds: core.Seeds, which: str) -> int:
    c = int(item["cell"])
    return seeds.init(c) if which == "init" else seeds.stream(c, core.REGIME_INDEX[item["regime"]])


def guarded(path: Path, item_id: str, fn: Callable[[], Any]) -> Any:
    """An exception that is not a failed cell is an ``item_error``: recorded, never a scientific NOT EVALUABLE (section 10). The record keeps the traceback and the exception propagates."""
    try:
        return fn()
    except core.EngineeringStop:
        raise
    except Exception as e:
        path.parent.mkdir(parents=True, exist_ok=True)
        core.write_record(path, {**core.envelope("train"), "id": item_id, "status": "item_error", "reason": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()[-4000:]}, overwrite=True)
        raise


# --- the registry from records ----------------------------------------------------------------------------------------------------------
def collect_registry(run_dir: Path, plan_items: Mapping[str, Sequence[Mapping[str, Any]]], bases: Mapping[str, Mapping[str, float | None]] | None = None) -> dict[str, Any]:
    """The analysis registry (keys of ``core``) from the train and eval records of the planned items only. A planned item without a record is simply absent (the analysis then refuses: a missing evaluation is an engineering stop)."""
    reg: dict[str, Any] = {}
    for it in plan_items["train"]:
        p = train_record_path(run_dir, it)
        if p.is_file():
            rec = core.read_record(p, "train")
            reg[core.run_key(it["arm"], it["regime"], it["rate"], it["cell"])] = {"status": rec["status"], "reason": rec.get("reason")}
    for it in plan_items["eval"]:
        p = eval_record_path(run_dir, it)
        if not p.is_file():
            continue
        rec = core.read_record(p, "eval")
        for k, v in rec["reads"].items():
            read, draw = k.split("|")
            reg[core.nll_key(it["arm"], it["regime"], it["rate"], it["cell"], it["update"], read, int(draw))] = v
        for name in ("used_slots", "branch_entropy"):
            if name in rec["stats"]:
                reg[core.stat_key(it["arm"], it["regime"], it["rate"], it["cell"], it["update"], name)] = rec["stats"][name]
    for parent, d in (bases or {}).items():
        reg[core.base_key(int(parent))] = d["enabled"]
        reg[core.base_key(int(parent), "replay")] = d["replay"]
    return reg
