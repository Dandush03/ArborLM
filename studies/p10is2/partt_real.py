# ruff: noqa: E501
"""Part T's real-run drivers: the world from Part Q's outputs, calibration, the registered stage bodies and the two rehearsals (ADR-0025 sections 7, 10, 11 item 5).

Everything is a function of a ``WorldT`` (``engine.build_world_t``), so the tests drive it with a tiny world on CPU and the lead's runs drive it with the real bundle on MPS. Part T uses the lock alone: nothing
here imports a package outside it. Part T reads Part Q's manifest files only, by hash (ruling L12): the bundle, the pools, the generation record and the gloss bank; never a sealed file, never a Q_fit or Q_check
per-item score. Charged time is the wall time of each process (ruling L2); the stage bodies run in one process here (a worker split is an optimisation the lead's launch can add: the cell tasks are independent).
"""

import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json, write_json
from studies.p10s2.data import TrainItem
from studies.p10s2.evaluate import score_panel
from studies.p10s2.memory import NullArm
from studies.p10s2.worldio import read_bundle

from . import (
    annotations,
    calibration,
    engine,
    partt_gates,
    partt_plan,
    partt_rehearsal,
    partt_run,
    report,
    scoring,
)
from . import labels as L
from .common import core
from .partt_g8 import q_equivalence_through_door
from .quantities import CELLS, Quantities, Registry, Thresholds


# --- Part Q's outputs -------------------------------------------------------------------------------------------------------------------------------
def load_part_q(qdir: Path, cfg: Mapping[str, Any], mode: str, door: Any = None) -> tuple[Any, list[dict[str, list[TrainItem]]], dict[str, Any], dict[str, Any]]:
    """The bundle, the replicates' training draws, the gloss bank and the draws record from a Part Q run directory (``outputs/bundle``, ``generation/pools.json``, ``generation/result.json``,
    ``outputs/gloss_bank.json``). DISJOINT DRAWS: the recorded permutation positions; OVERLAPPING DRAWS: each replicate draws 8,000 from the whole pool with its training-draw seed (capability A first, then B, one
    generator per replicate)."""
    if door is not None:  # the one checked door (ruling 10): every file read is re-hashed against Part Q's manifest or reuse hashes; the pools come from the listed bundle, not from generation/pools.json
        door.verify_prefix("outputs/bundle")
        bundle = read_bundle(qdir / "outputs/bundle")
        result = door.read_json("generation/result.json")
        pool = {c: list(bundle.accepted[c]) for c in core.TASKS}
    else:
        bundle = read_bundle(qdir / "outputs/bundle")
        pools = read_json(qdir / "generation/pools.json")["pools"]
        result = read_json(qdir / "generation/result.json")
        pool = {c: [TrainItem(x["key"], x["en"], x["target"], int(x["group"])) for x in pools[c]] for c in core.TASKS}
    per = int(cfg["data"].get("per_replicate", 8000)) if "per_replicate" in cfg.get("data", {}) else 8000
    if mode == "rehearsal":  # a rehearsal trains on its own draw (252002) and holds no evaluation panel (partt_rehearsal)
        if result["draws_label"] not in ("DISJOINT DRAWS", "OVERLAPPING DRAWS"):
            raise core.StageRefused(f"refused: Part Q's draws label is {result['draws_label']!r}: Part T has no material")
        gloss = door.read_json("outputs/gloss_bank.json") if door is not None else read_json(qdir / "outputs/gloss_bank.json")
        from studies.p10s2.text import normalize

        rb = partt_rehearsal.rehearsal_bundle(bundle, cfg, door.q_check_keys() if door is not None else ())
        stand_in_refs = {normalize(r) for n in ("E_A", "E_B", "E_C") for it in rb.panels[n] for refs in it.refs.values() for r in refs}
        info: dict[str, Any] = {}
        draws = rehearsal_draws(pool, cfg, per, stand_in_refs, info)
        return rb, draws, gloss, {**result, "rehearsal_draw": info}
    if result["draws_label"] == "DISJOINT DRAWS":
        idx = result["draws"]["indices"]
        draws = [{c: [pool[c][i] for i in idx[c][r]] for c in core.TASKS} for r in range(3)]
    elif result["draws_label"] == "OVERLAPPING DRAWS":
        draws = []
        for r in range(3):
            plan = engine.SeedPlanT(cfg, mode, r)
            g = plan.gen(1, "overlapping draw")
            draws.append({c: [pool[c][i] for i in torch.randperm(len(pool[c]), generator=g).tolist()[:per]] for c in core.TASKS})
    else:
        raise core.StageRefused(f"refused: Part Q's draws label is {result['draws_label']!r}: Part T has no material")
    if mode == "rehearsal":  # a rehearsal never trains on Part Q's registered indices (audit B2, ruling 1): the rehearsal's own draw, SeedPlanT(rehearsal, 0).gen(1), A then B, one generator
        draws = rehearsal_draws(pool, cfg, per)
    gloss = door.read_json("outputs/gloss_bank.json") if door is not None else read_json(qdir / "outputs/gloss_bank.json")
    return bundle, draws, gloss, result


def rehearsal_draws(pool: Mapping[str, Sequence[TrainItem]], cfg: Mapping[str, Any], per: int = 8000, forbidden: set[str] | None = None, report: dict[str, Any] | None = None) -> list[dict[str, list[TrainItem]]]:
    """The rehearsal's own training draw (registry revision 5: seed 252002 = ``gen(1)`` of the rehearsal set), A then B, one generator; never Part Q's registered indices. Ruling 24 (audit N9): D_cal stands in for the
    evaluation panels in a rehearsal, so every item whose output equals (normalized) a stand-in reference is DROPPED from the draw by the rule Part Q applied to evaluation references; the count dropped per capability
    goes into ``report`` and the rehearsal record. ``forbidden`` is None only in a test of what G1 does without the drop."""
    from studies.p10s2.text import normalize

    g = engine.SeedPlanT(cfg, "rehearsal", 0).gen(1, "rehearsal training draw")
    draw = {c: [pool[c][k] for k in torch.randperm(len(pool[c]), generator=g).tolist()[:per]] for c in core.TASKS}
    dropped = {c: 0 for c in core.TASKS}
    if forbidden is not None:
        for c in core.TASKS:
            kept = [x for x in draw[c] if normalize(x.target) not in forbidden]
            dropped[c] = len(draw[c]) - len(kept)
            draw[c] = kept
    if report is not None:
        report.update({"rule": "items whose normalized output equals a normalized stand-in reference are dropped (ruling 24)", "dropped_per_capability": dropped, "drawn_per_capability": {c: len(draw[c]) + dropped[c] for c in core.TASKS}, "applied": forbidden is not None})
    return [draw]


def shared_share(draws: Sequence[Mapping[str, Sequence[TrainItem]]]) -> dict[str, float]:
    """Mean over replicate pairs of |intersection| / draw size, per capability: printed beside every line that says "every cell" when the draws overlap."""
    out = {}
    for c in core.TASKS:
        sets = [{x.key for x in d[c]} for d in draws]
        pairs = [(i, j) for i in range(len(sets)) for j in range(i + 1, len(sets))]
        out[c] = sum(len(sets[i] & sets[j]) / max(1, len(sets[i])) for i, j in pairs) / max(1, len(pairs))
    return out


# --- calibration ------------------------------------------------------------------------------------------------------------------------------------
@torch.no_grad()
def dcal_mean(world: engine.WorldT, arm: Any, cap: str) -> float:
    return score_panel(world.ctx, arm, world.d_cal[cap]).mean


def calibration_draws(pool: Mapping[str, Sequence[TrainItem]], cfg: Mapping[str, Any], indices: Sequence[int], per: int = 8000) -> list[dict[str, list[TrainItem]]]:
    """The training draws of calibration draws 0..3 (draws 2 and 3 are the repetition of section 7.1 rule 4): from Part Q's accepted pools with each draw's training-draw seed (+1), A then B."""
    out = []
    for i in indices:
        g = engine.SeedPlanT(cfg, "calibration", i).gen(1, "calibration training draw")
        out.append({c: [pool[c][k] for k in torch.randperm(len(pool[c]), generator=g).tolist()[:per]] for c in core.TASKS})
    return out


def draw_overlap(calibration: Sequence[Mapping[str, Sequence[TrainItem]]], registered: Sequence[Mapping[str, Sequence[TrainItem]]]) -> dict[str, Any]:
    """Ruling 2: the calibration draws may overlap the registered draws (teacher A's pool is 24,187 items, the registered replicates take 24,000 disjoint ones, leaving 187), and the overlap is STATED: per
    capability and per calibration draw, the number and the share of its items (by English key) that are in the union of the registered replicates' draws. Training material only; no evaluation item is involved."""
    out: dict[str, Any] = {}
    for c in core.TASKS:
        reg = {x.key for d in registered for x in d[c]}
        out[c] = [{"draw": i, "items": len(d[c]), "in_registered_draws": sum(1 for x in d[c] if x.key in reg), "share": (sum(1 for x in d[c] if x.key in reg) / len(d[c])) if d[c] else 0.0} for i, d in enumerate(calibration)]
    return out


_DEADLINE: list[float | None] = []
_STATE: list[Path | None] = []
_ON_UNIT: list[Any] = []
_ON_BEGIN: list[Any] = []


def run_unit(world: engine.WorldT, unit: Mapping[str, Any], rate: float, layer: int | None, draw_index: int) -> dict[str, Any]:
    """One calibration training unit on a calibration draw's seeds (the world is built in ``calibration`` mode with the calibration draws), scored on D_cal. A non-finite loss is DIVERGED (``diverged``, no
    mean at the diverged snapshot); the caller applies ``calibration``'s rules. A ladder unit has ``snapshots``; each is scored on D_cal on CPU while the optimizer state is kept."""
    cap, module = unit["capability"], unit["module"]
    state_file = (_STATE[-1] / f"{unit['id']}.json") if _STATE and _STATE[-1] is not None else None
    if state_file is not None and state_file.is_file():  # ruling 25: a unit already run in an earlier session is read back, never drawn again (a non-finite outcome is a stored outcome, not retried)
        cached = json.loads(state_file.read_text())
        cached["means"] = {int(k): v for k, v in cached["means"].items()}
        return cached  # type: ignore[no-any-return]
    if _DEADLINE and _DEADLINE[-1] is not None and time.monotonic() > _DEADLINE[-1]:
        raise calibration.CalibrationStop("calibration reached its cap (ruling 22): the work returns to the lead; nothing is extended here")
    if _ON_BEGIN and _ON_BEGIN[-1] is not None:
        _ON_BEGIN[-1](unit["id"])  # ruling 34: the unit_begin line is committed BEFORE the unit trains; a failed commit stops here
    saved = (world.layer, world.store_lr, world.lora_lr, getattr(world, "etable_lr", None), world.ctx.router_layer)
    try:
        if layer is not None:
            world.layer = world.ctx.router_layer = int(layer)
        if module == "lora":
            world.lora_lr = rate
        else:
            world.store_lr = rate
            world.etable_lr = rate  # type: ignore[attr-defined]
        arm_name = {"store": "M1", "lora": "D1", "etable": "E-table"}[module]
        spec = engine.CellSpec(arm_name, cap + core.other_task(cap) if module != "etable" else "-", draw_index, cap if module == "etable" else "")
        arm, rows, opts = engine.build_cell_arm(world, spec, None)
        snaps = list(unit.get("snapshots") or [])
        means: dict[int, float | None] = {}

        def cb(update: int, a: Any) -> None:
            means[update] = dcal_mean(world, a, cap)

        rec = engine.train_cell(world, spec, arm, rows, {**opts, "rate": rate}, int(unit["updates"]), snapshots=snaps, on_snapshot=cb)
        if not snaps and rec["status"] == "COMPLETE":
            means[int(unit["updates"])] = dcal_mean(world, arm, cap)
        if rec["status"] == "ERROR":
            raise RuntimeError(f"calibration unit {unit['id']} stopped on a code or environment error (an engineering stop, never DIVERGED): {rec['error']}")
        diverged = rec["status"] == "STOPPED_NONFINITE"
        result = {"unit": unit["id"], "rate": rate, "layer": world.layer, "means": means, "diverged": diverged, "status": rec["status"], "error": rec["error"], "seconds_per_update": rec["seconds_per_update"]}
        if state_file is not None:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            write_json(state_file, core.jsonable(result))
            if _ON_UNIT and _ON_UNIT[-1] is not None:
                _ON_UNIT[-1](unit["id"])  # ruling 29: the finished unit is listed in the log, after its state is on disk
        return result
    finally:
        world.layer, world.store_lr, world.lora_lr, el, world.ctx.router_layer = saved
        if el is not None:
            world.etable_lr = el  # type: ignore[attr-defined]


def run_calibration(world: engine.WorldT, cfg: Mapping[str, Any], deadline: float | None = None, state_dir: Path | None = None, on_unit: Any = None, on_begin: Any = None) -> dict[str, Any]:
    """The whole of section 7.1 on a calibration world: the store's and LoRA's rate grids (draw 0, store at L = 4), the store at L = 12 at its chosen rate, E-table's grid at the chosen layer, the convergence
    ladder (M1 and D1 on each capability, draw 1, to 8,000 updates), then U and the pilot. Returns the record the Part T plan is built from. A stop (every rate diverged, a non-finite value in the ladder
    or the pilot) is ``calibration.CalibrationStop``: the work returns to the human lead."""
    _DEADLINE.append(deadline)
    _STATE.append(state_dir)
    _ON_UNIT.append(on_unit)
    _ON_BEGIN.append(on_begin)
    try:
        return _run_calibration(world, cfg)
    finally:
        _DEADLINE.pop()
        _STATE.pop()
        _ON_UNIT.pop()
        _ON_BEGIN.pop()


def _run_calibration(world: engine.WorldT, cfg: Mapping[str, Any]) -> dict[str, Any]:
    c = cfg["calibration"]
    units = {u["id"]: u for u in calibration.calibration_units(cfg)}
    rec: dict[str, Any] = {"units": {}, "stand_in": False}

    def mean_over_caps(prefix: str, rate: float, layer: int | None, mod: str) -> float | None:
        vals = []
        for cap in core.TASKS:
            r = run_unit(world, units[f"{prefix}-{cap}-{rate}"], rate, layer, 0)
            rec["units"][r["unit"]] = r
            if r["diverged"]:
                return None
            vals.append(next(iter(r["means"].values())))
        return float(sum(vals) / len(vals))

    store = {r: mean_over_caps("grid-store", r, int(c["rate_grid_read_layer"]), "store") for r in c["store_rates"]}
    lora = {r: mean_over_caps("grid-lora", r, None, "lora") for r in c["lora_rates"]}
    store_rate, lora_rate = calibration.select_rate(cfg, "store", store), calibration.select_rate(cfg, "lora", lora)
    l12 = []
    for cap in core.TASKS:
        r = run_unit(world, units[f"layer12-{cap}"], store_rate, int(cfg["memory"]["read_layers"][1]), 0)
        rec["units"][r["unit"]] = r
        l12.append(None if r["diverged"] else next(iter(r["means"].values())))
    layer = calibration.select_read_layer(cfg, store[store_rate] or 0.0, None if any(v is None for v in l12) else sum(l12) / 2)  # type: ignore[arg-type]
    et = {r: mean_over_caps("grid-etable", r, layer, "etable") for r in c["store_rates"]}
    etable_rate = calibration.select_rate(cfg, "etable", et)
    ladder: dict[str, dict[str, dict[int, float | None]]] = {"store": {}, "lora": {}}
    for module in ("store", "lora"):
        for cap in core.TASKS:
            r = run_unit(world, units[f"ladder-{module}-{cap}"], store_rate if module == "store" else lora_rate, layer if module == "store" else None, 1)
            rec["units"][r["unit"]] = r
            ladder[module][cap] = r["means"]
    length = calibration.choose_training_length(cfg, ladder)
    gaps: dict[str, float | None] = {}
    for cap in core.TASKS:
        r = rec["units"][f"ladder-store-{cap}"]
        s0 = score_panel(world.ctx, NullArm(), world.d_cal[cap]).mean
        gaps[cap] = None  # the gap needs the teacher's D_cal score: filled below
        t = sum(chrf for chrf in _teacher_dcal(world, cap)) / max(1, len(_teacher_dcal(world, cap)))
        mean = r["means"][length["U"]]
        gaps[cap] = None if t - s0 < float(cfg["data"]["gap_denominator_min"]) else (mean - s0) / (t - s0)
    pilot = calibration.pilot_gate(cfg, gaps)
    rec.update({"store_rate": store_rate, "lora_rate": lora_rate, "etable_rate": etable_rate, "read_layer": layer, "U": length["U"], "converged": length["converged"], "line_note": length["line_note"], "pilot": pilot, "grids": {"store": store, "lora": lora, "etable": et}, "ladder_differences": length["differences"]})
    return rec


def _teacher_dcal(world: engine.WorldT, cap: str) -> list[float]:
    from studies.p10s2.text import chrf_item

    texts = world.teacher_outputs[cap]["D_cal"]
    return [chrf_item(t, r) for t, r in zip(texts, world.d_cal[cap].refs, strict=True)]


# The rehearsals are NOT here: they run through the registered entry point (``partt_counting``), never in this process (audit B1).


# --- analysis and report -----------------------------------------------------------------------------------------------------------------------------
def analyse(reg: Registry, side: Mapping[str, Any], comb: Mapping[str, Any] | None, ctx: Mapping[str, Any], *, required: Sequence[str], thresholds: Thresholds, item_errors: Sequence[str] = (), recompute_failed: Sequence[Any] = (), engineering_failure: Sequence[str] = ()) -> dict[str, Any]:
    """Study status, the lines, the annotations and the report (pure over the records). Under a status that does not derive, no line is produced."""
    st = L.study_status(reg, item_errors=item_errors, recompute_failed=recompute_failed, engineering_failure=engineering_failure, required=required)
    if not st["derive"]:
        return {"status": st, "report": report.render(st, None, ctx)}
    q = Quantities(reg, thresholds)
    derived = L.derive_all(q, recompute_failed)
    ann = annotations.all_annotations(q, side if all(f"r{r}/M-append/{o}" in side and "route" in side[f"r{r}/M-append/{o}"] for r, o in CELLS) else None, comb)
    return {"status": st, "lines": derived, "annotations": ann, "report": report.render(st, derived, {**ctx, "annotations": ann})}


def write_analysis(run_dir: Path, result: Mapping[str, Any]) -> None:
    core.write_record(core.records_dir(run_dir) / "analysis.json", {**core.envelope("analysis", "T"), **core.jsonable(dict(result))}, overwrite=True)
    (core.records_dir(run_dir) / "report.txt").write_text(core.require_oracle_line(result["report"]) + "\n", encoding="utf-8")


def json_safe(x: Any) -> Any:
    return json.loads(json.dumps(core.jsonable(x), default=str))


__all__ = ["file_sha256", "write_json"]


# --- the registered stage bodies and the commands --------------------------------------------------------------------------------------------------
def door_of(plan: Any, qdir: Path) -> Any:
    """The checked door of a plan that names Part Q (every registered plan does); a plan without ``part_q`` (a unit-test fixture) has none."""
    from .partt_door import PartQDoor

    pq = (getattr(plan, "data", None) or {}).get("part_q")
    return PartQDoor.from_plan(pq) if pq else None


def qdir_of(plan: Any, fallback: Path) -> Path:
    """The Part Q run directory of record is the plan's, never the command line's (audit R2)."""
    pq = (getattr(plan, "data", None) or {}).get("part_q")
    return Path(pq["run_dir"]) if pq else fallback


def build_world_real(repo: Path, cfg: Mapping[str, Any], qdir: Path, plan_calibration: Mapping[str, Any], mode: str, door: Any = None) -> tuple[engine.WorldT, Mapping[str, Any], Any]:
    """The world of a registered run or a rehearsal: Part Q's bundle and draws, the calibrated settings, the frozen devices (MPS training, CPU scoring)."""
    bundle, draws, gloss, result = load_part_q(qdir, cfg, mode, door)
    run = engine.run_config(cfg, layer=int(plan_calibration["read_layer"]), updates=int(plan_calibration["U"]), store_rate=float(plan_calibration["store_rate"]), lora_rate=float(plan_calibration["lora_rate"]), device=cfg["training"]["training_device"])
    w = engine.build_world_t(bundle, cfg, draws, run, plan_mode=mode)
    w.etable_lr = float(plan_calibration["etable_rate"])  # type: ignore[attr-defined]
    if mode == "rehearsal":
        w.evaluation_is_d_cal = True  # type: ignore[attr-defined]
        w.snapshot_alias = partt_rehearsal.AliasMap()  # type: ignore[attr-defined]
    return w, gloss, result


SINGLE_BODY_STAGES = ("controls", "recompute", "analysis", "report")


class StageGuard:
    """The cap and the memory guard of a stage that runs in its own process (audit N7): a watcher thread stops the process, PAUSED (exit 4, ``stages/<stage>.paused.json``, the time charged), when the stage's remaining cap
    is spent or the process's resident set passes the per-worker guard. A resume gets what is left of the cap."""

    def __init__(self, stage: str, run_dir: Path, ledger: Any, cap_seconds: float, rss_limit: int, poll: float = 1.0, on_trip: Any = None) -> None:
        import threading

        self.stage, self.run_dir, self.ledger, self.cap, self.limit, self.poll = stage, run_dir, ledger, cap_seconds, rss_limit, poll
        self.t0 = time.monotonic()
        self.stop = threading.Event()
        self.on_trip = on_trip or self._exit
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def __enter__(self) -> "StageGuard":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop.set()

    def _watch(self) -> None:
        import psutil

        while not self.stop.wait(self.poll):
            elapsed = time.monotonic() - self.t0
            rss = psutil.Process().memory_info().rss
            if elapsed > self.cap:
                self.trip(f"the stage cap of {self.cap:.0f} s is spent")
                return
            if rss > self.limit:
                self.trip(f"resident set {rss} above the per-worker guard {self.limit}")
                return

    def trip(self, reason: str) -> None:
        elapsed = time.monotonic() - self.t0
        self.ledger.charge_process(self.stage, "guard", "main", elapsed)
        (self.run_dir / "stages").mkdir(parents=True, exist_ok=True)
        write_json(self.run_dir / "stages" / f"{self.stage}.paused.json", {"stage": self.stage, "status": "PAUSED", "reason": reason, "charged_seconds": elapsed, "note": "run the same command again: it gets what is left of the cap (an extension is the lead's)"})
        self.on_trip(reason)

    @staticmethod
    def _exit(reason: str) -> None:
        import os

        print(f"PAUSED: {reason}", file=sys.stderr, flush=True)
        os._exit(4)


def calibration_of(cfg: Mapping[str, Any], plan: Any, mode: str, kind: str = "counting") -> dict[str, Any]:
    """The calibration block a stage uses: the plan's in a registered run; in a rehearsal the same with U = the ADR's 200 updates (section 10), whatever the plan's U (the measuring rehearsal needs no calibration result)."""
    calib = dict(plan.data["calibration"])
    if mode == "rehearsal" and kind == "measuring":  # ruling 27: the measuring rehearsal trains the ADR's 200 updates; the counting rehearsal the calibrated U (the plan's)
        calib["U"] = int(cfg["rehearsal"]["updates"])
    return calib


def run_stage(stage: str, repo: Path, run_dir: Path, qdir: Path, plan: Any, mode: str = "registered", kind: str = "counting") -> dict[str, Any]:
    """One registered Part T stage over the run directory (``train``, ``evaluate``, ``controls``, ``combined``, ``gates``, ``analysis``, ``report``). The entry point has checked identity."""
    cfg = core.load_config("T", repo / core.CONFIG_T)
    calib = calibration_of(cfg, plan, mode, kind)
    qdir = qdir_of(plan, qdir)
    st0 = partt_rehearsal.stats_begin(run_dir)
    t_proc = time.monotonic()
    guard = None
    if stage in SINGLE_BODY_STAGES and plan.data.get("stage_caps"):  # the cap and the memory guard (audit N7)
        from . import partt_tasks

        led0 = core.Ledger(run_dir / "charged_ledger.json", "T", 1e12)
        remaining = partt_tasks.stage_cap_for(plan, stage, led0) if mode == "registered" else partt_tasks.rehearsal_cap_seconds(cfg, kind, plan) - led0.charged()
        if remaining <= 0:
            raise core.StageRefused(f"refused: the cap of stage {stage!r} is spent (PAUSED): an extension is the lead's")
        guard = StageGuard(stage, run_dir, led0, remaining, int(float(cfg["caps"]["memory_per_worker_gib"]) * 2**30)).__enter__()
    w, gloss, qres = build_world_real(repo, cfg, qdir, calib, mode, door_of(plan, qdir))
    world_build = time.monotonic() - t_proc
    snaps = run_dir / "snapshots"
    t0 = time.monotonic()
    if stage == "gates":
        out = partt_gates.run_gates(w, cfg, snaps / "gates", equivalence_records=(bundle_equivalence(qdir) or None), q_equivalence_record=q_equivalence_through_door(door_of(plan, qdir)), root=repo, require_mps=mode in ("registered", "rehearsal"), q_check_keys=(door_of(plan, qdir).q_check_keys() if door_of(plan, qdir) is not None else None))
        core.write_record(run_dir / "gates.json", {**core.envelope("gates", "T"), **core.jsonable(out)}, overwrite=True)
    elif stage == "train":
        out = partt_run.train_all(w, snaps, run_dir / "checkpoints", int(calib["U"]))
        core.write_record(run_dir / "train_records.json", {**core.envelope("cell_record", "T"), "records": core.jsonable(out)}, overwrite=True)
    elif stage == "evaluate":
        reg, side = partt_run.score_all(w, snaps, gloss)  # the in-process path of the tests; the registered stage runs worker tasks and ``merge_evaluate``
        write_json(core.records_dir(run_dir) / "registry.json", reg.values)
        core.write_record(core.records_dir(run_dir) / "side_records.json", {**core.envelope("cell_record", "T"), "side": core.jsonable(side)}, overwrite=True)
        out = {"registry_keys": len(reg.values)}
    elif stage == "controls":
        out = check_controls(run_dir, plan, mode)
        if out["n_missing"]:
            raise core.StageRefused(f"refused: {out['n_missing']} control key(s) the plan names are not in the registry: {out['missing'][:3]}")
    elif stage == "recompute":
        out = run_recompute(repo, run_dir, qdir, plan, mode=mode, charge=False)  # run_stage charges the stage below
    elif stage == "combined":
        comb = partt_run.combined_all(w, snaps)
        core.write_record(core.records_dir(run_dir) / "combined.json", {**core.envelope("cell_record", "T"), "combined": core.jsonable(comb)}, overwrite=True)
        out = {"records": len(comb)}
    elif stage in ("analysis", "report"):
        eng = engineering_failures_of(run_dir)
        if not eng:  # N6: after a recorded engineering failure there may be no registry and no recomputation; the analysis then records the stop and derives nothing
            require_recomputation(run_dir)  # the recomputation is a registered stage before this one; the results were merged at the end of evaluate and combined
        rd = core.records_dir(run_dir)
        reg_values = read_json(rd / "registry.json") if (rd / "registry.json").is_file() else {}
        if mode == "rehearsal":  # the rehearsal scored one replicate: the analysis and the report run on a registry keyed by the plan's labels, replicates 1 and 2 copied from 0 (listed), never a result
            reg_values, filled = partt_rehearsal.fill_registry(reg_values)
            write_json(core.records_dir(run_dir) / "analysis_registry_filled.json", {"filled_from_replicate_0": filled, "note": "plumbing for the analysis and the report; a rehearsal registry is never a result"})
        reg = Registry(reg_values)
        side = read_json(rd / "side_records.json")["side"] if (rd / "side_records.json").is_file() else {}
        comb = read_json(core.records_dir(run_dir) / "combined.json")["combined"] if (core.records_dir(run_dir) / "combined.json").is_file() else None
        errors = sorted(str(p) for p in (run_dir / "item_errors").glob("*.json")) if (run_dir / "item_errors").is_dir() else []
        ctx = {"U": int(calib["U"]), "converged": bool(calib.get("converged", True)), "draws": qres["draws_label"], "shared_share": shared_share([dict(s.t) for s in w.streams])}
        if (run_dir / "cost.json").is_file():  # the cost lines (section 8.5) when the cost stage has run; they enter no label
            from . import partt_cost

            ctx["cost_lines"] = partt_cost.lines(read_json(run_dir / "cost.json"))
        if reg_values and not eng:  # the A4 readings (ruling 23): seen-item and E_open scores, the edit-distance-1 share and the scores without those items; reported, they enter no label
            from . import partt_items

            stored = read_json(rd / "item_records.json")["items"] if (rd / "item_records.json").is_file() else None
            ctx["a4_lines"] = partt_items.a4_lines(reg_values, stored)
        res = analyse(reg, side, comb, ctx, required=sorted(partt_plan.required_keys()), thresholds=Thresholds.from_config(cfg), item_errors=errors, engineering_failure=eng)
        write_analysis(run_dir, res)
        out = {"status": res["status"]["status"]}
    else:
        raise core.StageRefused(f"refused: {stage!r} is not a Part T stage")
    total = float(cfg["stage_caps"].get("total_hours", 0.0)) * 3600.0
    led = core.Ledger(run_dir / "charged_ledger.json", "T", total if total > 0 and mode == "registered" else 1e12)
    body = time.monotonic() - t0
    led.charge_process(stage, mode, "main", time.monotonic() - t_proc)  # the wall time of this process, the world build inside it (ruling L2)
    if guard is not None:
        guard.__exit__()
    (run_dir / "stages").mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "stages" / f"{stage}.timing.json", {"stage": stage, "mode": mode, "world_build_seconds": world_build, "body_seconds": body, **partt_rehearsal.stats_end(st0, run_dir)})
    return json_safe(out)  # type: ignore[no-any-return]


def bundle_equivalence(qdir: Path) -> Mapping[str, Any] | None:
    return read_bundle(qdir / "outputs/bundle").extra.get("equivalence_layers")


def calibrate_command(repo: Path, qdir: Path, run_dir: Path, repetition: int, part_q_plan: Path | None, cap_seconds: float, on_unit: Any = None, on_begin: Any = None) -> dict[str, Any]:
    """Calibration and the pilot on calibration draws (0, 1; the single repetition 2, 3) with the frozen devices, in ``run_dir`` (the one calibration directory, or its ``second/``), under its cap; writes
    ``calibration_<repetition>.json`` once with the code hashes of every file it ran (section 7.1 rule 4). Part Q is read through the checked door built from Part Q's manifest AND its plan (the reuse list holds
    ``generation/result.json``). Nothing it scores is a result."""
    from .common import plan as planmod
    from .partt_door import PartQDoor
    from .partt_stages import part_q_block

    cfg = core.load_config("T", repo / core.CONFIG_T)
    door = PartQDoor.from_plan(part_q_block(qdir, part_q_plan))  # every Part Q file read is re-hashed against Part Q's manifest or its plan's reuse list
    bundle, registered_draws, _gloss, _res = load_part_q(qdir, cfg, "registered", door)
    pool = {c: list(bundle.accepted[c]) for c in core.TASKS}
    off = 2 * repetition
    run = engine.run_config(cfg, layer=int(cfg["calibration"]["rate_grid_read_layer"]), updates=int(cfg["calibration"]["rate_grid_updates"]), store_rate=0.003, lora_rate=0.0003, device=cfg["training"]["training_device"])
    w = engine.build_world_t(bundle, cfg, calibration_draws(pool, cfg, [off, off + 1]), run, plan_mode="calibration")
    w.plan_offset = off
    rec = run_calibration(w, cfg, deadline=time.monotonic() + cap_seconds, state_dir=run_dir / "state", on_unit=on_unit, on_begin=on_begin)
    rec["overlap_with_registered_draws"] = draw_overlap(calibration_draws(pool, cfg, [off, off + 1]), registered_draws)  # ruling 2: stated, by code
    rec["part_q_manifest_sha256"] = file_sha256(qdir / "manifest.json")
    from .partt_stages import session_identity

    rec["code_hashes"] = planmod.frozen_file_hashes(repo, "T")
    rec["session_identity"] = session_identity(repo)  # ruling 31: the identity the record was computed under
    rec["repetition"] = repetition
    path = run_dir / f"calibration_{repetition}.json"
    core.write_record(path, {**core.envelope("calibration", "T"), **core.jsonable(rec)}, overwrite=False)  # one record per directory: never overwritten, no re-draw (ruling 21)
    return {k: rec[k] for k in ("store_rate", "lora_rate", "etable_rate", "read_layer", "U", "converged", "pilot")}


# --- worker tasks (one process each; ``partt_tasks`` derives them from the frozen plan) --------------------------------------------------------------------------
def run_task(stage: str, task_id: str, repo: Path, run_dir: Path, qdir: Path, plan: Any, mode: str = "registered", stop_after: int | None = None, kind: str = "counting") -> dict[str, Any]:
    """The body of one worker. A trained cell: parent from its snapshot, resume from its checkpoint, train, snapshot; the cell record is written either way; the RESULT file only if the cell COMPLETED (a cell that
    stopped on a non-finite loss or an error exits non-zero: the runner keeps a failed record and the analysis refuses while the item error stands). Scoring and the combined tasks write their records as the
    result."""
    from . import partt_tasks

    cfg = core.load_config("T", repo / core.CONFIG_T)
    calib = calibration_of(cfg, plan, mode, kind)
    qdir = qdir_of(plan, qdir)
    st0 = partt_rehearsal.stats_begin(run_dir)
    t_proc = time.monotonic()
    scoring.KIND_SECONDS.clear()
    scoring.KIND_CALLS.clear()
    w, gloss, qres_task = build_world_real(repo, cfg, qdir, calib, mode, door_of(plan, qdir))
    if mode == "rehearsal" and stage == "gates" and not (run_dir / "rehearsal_draw.json").is_file():  # ruling 24: what the draw dropped is recorded in the rehearsal's record
        write_json(run_dir / "rehearsal_draw.json", qres_task.get("rehearsal_draw") or {})
    world_build = time.monotonic() - t_proc
    d = partt_tasks.tasks_dir(run_dir, stage)
    sid = partt_tasks.safe(task_id)
    snaps = run_dir / "snapshots"
    result: dict[str, Any]
    kinds: dict[str, Any] = {}
    if stage == "train":
        item = next(i for i in plan.items("train") if i["id"] == task_id)
        spec = engine.CellSpec(item["arm"], item["order"], int(item["rep"]), item.get("capability", ""))
        rec, _ = engine.run_cell(w, spec, int(calib["U"]), snaps, run_dir / "checkpoints", stop_after=stop_after)
        core.write_record(d / f"{sid}.cell.json", {**core.envelope("cell_record", "T"), **core.jsonable(rec)}, overwrite=True)
        if rec["status"] == "PAUSED" and stop_after is not None:  # the rehearsal's ONE forced pause: the checkpoint is on disk; exit 74 is PAUSED for the runner and the same command resumes it
            raise SystemExit(partt_rehearsal.FORCED_PAUSE_EXIT)
        if rec["status"] != "COMPLETE":
            raise SystemExit(f"cell {task_id}: {rec['status']}: {rec['error']}")
        result = {"cell": rec}
        kinds = {"seconds": {f"train:{item['arm']}": float(rec["wall_seconds"])}, "units": {f"train:{item['arm']}": int(rec["updates_done"])}}
    elif stage in ("evaluate", "controls"):
        if task_id.endswith("|reference"):
            result = {"records": partt_run.reference_task(w), "side": {}, "items": scoring.take_items()}
        else:
            rep = int(task_id.rsplit("|r", 1)[1])
            recs, side = partt_run.score_replicate(w, rep, snaps, gloss, routers_mode="save")
            result = {"records": recs, "side": side, "items": scoring.take_items()}
    elif stage == "combined":
        if task_id.endswith("|reference"):
            ref = partt_run.combined_reference(w)
            result = {"combined": ref, "ensemble_check": partt_run.ensemble_check(w, ref["ensemble"])}
        else:
            rep = int(task_id.rsplit("|r", 1)[1])
            tol = Thresholds.from_config(cfg).modification_dcon_tolerance
            reg_values = read_json(core.records_dir(run_dir) / "registry.json") if (core.records_dir(run_dir) / "registry.json").is_file() else {}
            result = {"combined": partt_run.combined_replicate(w, rep, snaps, pinned_orders=partt_run.rejected_orders(reg_values, rep, tol))}
    elif stage == "gates":
        out = partt_gates.run_gates(w, cfg, snaps / "gates", equivalence_records=(bundle_equivalence(qdir) or None), q_equivalence_record=q_equivalence_through_door(door_of(plan, qdir)), root=repo, require_mps=mode in ("registered", "rehearsal"), q_check_keys=(door_of(plan, qdir).q_check_keys() if door_of(plan, qdir) is not None else None))
        core.write_record(run_dir / "gates.json", {**core.envelope("gates", "T"), **core.jsonable(out)}, overwrite=True)
        result = {"gates": out["status"], "failed": out["failed"], "skipped": out["skipped"]}  # a failed gate is recorded in gates.json and makes the study status ENGINEERING-FAILURE; it is no item error
    else:
        raise core.StageRefused(f"refused: {stage!r} has no worker task")
    if stage in ("evaluate", "combined", "gates") and not kinds:
        kinds = task_kinds(w, stage, task_id)
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / f"{sid}.timing.json", {"task": task_id, "mode": mode, "world_build_seconds": world_build, "task_body_seconds": time.monotonic() - t_proc - world_build, "kinds": core.jsonable(kinds), **partt_rehearsal.stats_end(st0, run_dir)})
    core.write_record(d / f"{sid}.result.json", {**core.envelope("cell_record", "T"), "task": task_id, **core.jsonable(result)}, overwrite=False)
    return result


def task_kinds(w: engine.WorldT, stage: str, task_id: str) -> dict[str, Any]:
    """Seconds of unit work per kind in this process and the units they covered (counted from this world's panel sizes by the shared ``partt_caps.replicate_units`` for scoring; arm-cells for the combined stage).
    GEN seconds are folded into ``score:plain`` (the plan has no unit kind for them): conservative, and listed separately."""
    from . import partt_caps

    sec = dict(scoring.KIND_SECONDS)
    gen = sec.pop("score:gen", 0.0)
    sec["score:plain"] = sec.get("score:plain", 0.0) + gen
    e = len(w.ctx.panels["E_A"].refs)
    s = len(w.ctx.subsample["E_A"])
    dcon = len(w.d_con["A"].refs)
    if stage == "gates":
        return {"seconds": {}, "units": {"gates:all": 1}, "note": "the gates run as one body: its seconds are the task body"}
    if stage == "evaluate":
        n_open = sum(len(w.ctx.panels[f"E_open_{c}"].refs) for c in core.TASKS if f"E_open_{c}" in w.ctx.panels) // 2
        n_seen = len(w.seen_items[0][core.TASKS[0]]) if getattr(w, "seen_items", None) else 0
        units = {"score:reference": 2 * e + 2 * n_open} if task_id.endswith("|reference") else partt_caps.replicate_units(e, s, dcon, n_seen, n_open)
        return {"seconds": sec, "units": {k: v for k, v in units.items() if k in sec}, "gen_seconds_folded_into_plain": gen}
    return {"seconds": sec, "units": {"combined:arm-cell": int(scoring.KIND_CALLS.get("combined:arm-cell", 0))}}


def merge_results(run_dir: Path) -> dict[str, int]:
    """The task results of the evaluate and combined stages into ``registry.json``, ``side_records.json`` and ``combined.json`` (the analysis reads those). A missing replicate is simply absent: the study
    status then says INCOMPLETE."""
    records: dict[str, dict[str, float]] = {}
    side: dict[str, Any] = {}
    for f in sorted((run_dir / "tasks" / "evaluate").glob("*.result.json")):
        r = read_json(f)
        records.update(r["records"])
        side.update(r["side"])
    comb: dict[str, Any] = {}
    for f in sorted((run_dir / "tasks" / "combined").glob("*.result.json")):
        comb.update(read_json(f)["combined"])
    write_json(core.records_dir(run_dir) / "registry.json", scoring.registry_from_reads(records).values)
    core.write_record(core.records_dir(run_dir) / "side_records.json", {**core.envelope("cell_record", "T"), "side": core.jsonable(side)}, overwrite=True)
    core.write_record(core.records_dir(run_dir) / "combined.json", {**core.envelope("cell_record", "T"), "combined": core.jsonable(comb)}, overwrite=True)
    return {"records": len(records), "combined": len(comb)}


def engineering_failures_of(run_dir: Path) -> list[str]:
    """The causes ADR-0025 section 8.6 names for ENGINEERING-FAILURE that the run records: a failed gate (``gates.json``) and a failed oracle-routed ensemble integrity check (``ensemble_check.json``). Passed to the
    analysis so that the status is ENGINEERING-FAILURE, not an item error (audit R9, ruling 14)."""
    out: list[str] = []
    g = run_dir / "gates.json"
    if g.is_file() and read_json(g).get("status") == "ENGINEERING-FAILURE":
        out.append(f"gates failed: {read_json(g).get('failed')}")
    e = core.records_dir(run_dir) / "ensemble_check.json"
    if e.is_file() and not read_json(e).get("ok", True):
        out.append("the oracle-routed ensemble's score differs from the teacher's own (section 8.6)")
    return out


def require_gates_passed(run_dir: Path, stage: str) -> None:
    """A failed gate is ENGINEERING-FAILURE before training: no stage but the analysis and the report runs after it."""
    if stage in ("gates", "analysis", "report"):
        return
    fails = engineering_failures_of(run_dir)
    if fails:
        raise core.StageRefused(f"refused: ENGINEERING-FAILURE recorded ({fails[0]}): nothing further is trained or scored; only the analysis states the status")


def merge_evaluate(run_dir: Path) -> dict[str, int]:
    """The END of the evaluate stage: its task results into ``registry.json`` and ``side_records.json`` (the recomputation and the analysis read those). Written once; a second call must produce the same bytes."""
    records: dict[str, dict[str, float]] = {}
    side: dict[str, Any] = {}
    items: dict[str, Any] = {}
    for f in sorted((run_dir / "tasks" / "evaluate").glob("*.result.json")):
        r = read_json(f)
        records.update(r["records"])
        side.update(r["side"])
        items.update(r.get("items") or {})
    reg = scoring.registry_from_reads(records).values
    if not (core.records_dir(run_dir) / "item_records.json").is_file():  # ruling 8: every registered score's per-item scores and greedy sequences, written once
        core.write_record(core.records_dir(run_dir) / "item_records.json", {**core.envelope("cell_record", "T"), "items": core.jsonable(items)}, overwrite=False)
    if (core.records_dir(run_dir) / "registry.json").is_file():
        if read_json(core.records_dir(run_dir) / "registry.json") != json_safe(reg):
            raise core.StageRefused("refused: registry.json exists and differs from the evaluate results: no record is overwritten")
    else:
        write_json(core.records_dir(run_dir) / "registry.json", reg)
        core.write_record(core.records_dir(run_dir) / "side_records.json", {**core.envelope("cell_record", "T"), "side": core.jsonable(side)}, overwrite=False)
    return {"records": len(records)}


def merge_combined(run_dir: Path) -> dict[str, int]:
    """The END of the combined stage: its task results into ``combined.json`` (written once)."""
    comb: dict[str, Any] = {}
    for f in sorted((run_dir / "tasks" / "combined").glob("*.result.json")):
        r = read_json(f)
        comb.update(r["combined"])
        if "ensemble_check" in r and not (core.records_dir(run_dir) / "ensemble_check.json").is_file():
            core.write_record(core.records_dir(run_dir) / "ensemble_check.json", {**core.envelope("cell_record", "T"), **core.jsonable(r["ensemble_check"])}, overwrite=False)
    if not (core.records_dir(run_dir) / "combined.json").is_file():
        core.write_record(core.records_dir(run_dir) / "combined.json", {**core.envelope("cell_record", "T"), "combined": core.jsonable(comb)}, overwrite=False)
    return {"combined": len(comb)}


def check_controls(run_dir: Path, plan: Any, mode: str = "registered") -> dict[str, Any]:
    """The controls stage (ruling 12): the controls of section 5.2 were scored on their registered subsamples by the evaluate tasks; this stage scores nothing. It checks that every control key the plan's items
    name is in the registry (the analysis would otherwise call the line INCOMPLETE)."""
    reg = read_json(core.records_dir(run_dir) / "registry.json")
    need = [k for k in plan.data.get("registry_keys", []) if ":sub:" in k or "|sub:" in k]
    if mode == "rehearsal":  # a rehearsal scored replicate 0 only
        need = [k for k in need if k.split("|")[2] in (str(partt_rehearsal.SUBSET_REP), "-")]
    missing = [k for k in need if k not in reg]
    return {"control_keys_required": len(need), "missing": missing[:20], "n_missing": len(missing)}


def require_recomputation(run_dir: Path) -> dict[str, Any]:
    """No result is reported before every registered score is recomputed on CPU (section 8.6). A record of a recomputation that differs is ENGINEERING STOP — RECOMPUTATION: nothing is labelled."""
    from . import partt_recompute

    atts = partt_recompute.attempts(run_dir)
    if not atts:
        raise core.StageRefused("refused: no recomputation record: every registered score is recomputed on CPU before any result is reported (section 8.6)")
    recs = [read_json(a) for a in atts]
    failed = [r for r in recs if not r.get("ok")]
    if failed and not (run_dir / "recomputation_lead_record.json").is_file():  # a failed attempt stands: the analysis refuses unless a lead record names the cause (section 8.6)
        raise core.StageRefused(f"refused: ENGINEERING STOP — RECOMPUTATION: {len(failed)} attempt(s) with differences ({len(failed[0].get('differences', []))} in the first); no line, condition or annotation is derived")
    return dict(recs[-1])


def run_recompute(repo: Path, run_dir: Path, qdir: Path, plan: Any, own_code: bool = False, mode: str = "registered", charge: bool = True) -> dict[str, Any]:
    """The recomputation command: re-score every snapshot on CPU, compare, write ``recomputation.json`` and charge the time to the ledger."""
    from . import partt_recompute

    cfg = core.load_config("T", repo / core.CONFIG_T)
    t0 = time.monotonic()
    qdir = qdir_of(plan, qdir)
    w, gloss, _ = build_world_real(repo, cfg, qdir, calibration_of(cfg, plan, mode), mode, door_of(plan, qdir))
    reg = read_json(core.records_dir(run_dir) / "registry.json")
    comb = read_json(core.records_dir(run_dir) / "combined.json")["combined"] if (core.records_dir(run_dir) / "combined.json").is_file() else None
    stored = read_json(core.records_dir(run_dir) / "item_records.json")["items"] if (core.records_dir(run_dir) / "item_records.json").is_file() else None
    rec = partt_recompute.recompute(w, run_dir, gloss, reg, comb, own_code=own_code, stored_items=stored, **({"replicates": (partt_rehearsal.SUBSET_REP,)} if mode == "rehearsal" else {}))
    partt_recompute.write(run_dir, rec)
    if charge:
        total = float(cfg["stage_caps"].get("total_hours", 0.0)) * 3600.0
        core.Ledger(run_dir / "charged_ledger.json", "T", total if total > 0 else 1e12).charge_process("recompute", mode, "main", time.monotonic() - t0)
    return {k: rec[k] for k in ("ok", "outcome", "checked", "tolerance")}


def run_cost(repo: Path, run_dir: Path, qdir: Path, plan: Any, mode: str = "registered") -> dict[str, Any]:
    """The cost-recording stage: the five measures from the run, written to ``cost.json`` and ``cost.txt`` (each line under the note that it enters no label)."""
    from . import partt_cost

    cfg = core.load_config("T", repo / core.CONFIG_T)
    qdir = qdir_of(plan, qdir)
    w, _gloss, _ = build_world_real(repo, cfg, qdir, calibration_of(cfg, plan, mode), mode, door_of(plan, qdir))
    rec = partt_cost.record(w, run_dir, qdir if (qdir / "charged_ledger.json").is_file() else None, run_dir / "snapshots")
    partt_cost.write(run_dir, rec)
    return {"lines": len(partt_cost.lines(rec))}
