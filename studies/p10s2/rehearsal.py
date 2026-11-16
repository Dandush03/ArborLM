# ruff: noqa: E501
"""Rehearsal measurements (ADR-0022 section 13.3, "Rehearsal content"): the rates the rung rule reads. The rehearsal measures what the registered stages do, by running the registered stage functions
themselves (revision after audit B, M5, and the lead's ruling A-M3 of 2026-11-15):

* training: ``stages.stage_train`` for all 18 cells of a rehearsal replicate at the short number of updates (200), at the calibrated read layer and at the other one (E-table included), on the frozen
  training device; one store cell, one M-ii cell (from an appended 2N store, as registered) and one LoRA cell for the full U;
* scoring: ``stages.stage_evaluate`` (Stage 0, the 18 cells, the assembled arms, retrieval, the three routers, the ensemble), ``stages.stage_timing`` at the registered item count and repetitions, and
  ``stages.stage_recompute``, in a FRESH child process on CPU (so the evaluation and recomputation peaks are those of their own process); all of it on the rehearsal world, which scores calibration items
  (D_cal) and never an evaluation panel, and the times are scaled by the registered item counts (``scale_factor``);
* the analysis and report stages on synthetic records of the whole registry (four replicates, with a missing cell, a rejected consolidation, an inertia cell and a non-finite value), in the same child;
* the second gates stage at real size comes from the separate pre-freeze gates stage on rehearsal seeds (``time_prefreeze_gates``), whose scaled time is ``gates2_seconds``;
* memory: the peak is the larger of the process's resident set and the MPS driver's allocation, sampled (``train.process_memory_bytes``); the training peak is sampled after every training phase, the
  evaluation and recomputation peaks come from the child, the whole-task peak from a start-up child.

Nothing here is run in this implementation step except on synthetic stand-ins and test seeds. No number is a result.
"""

import contextlib
import dataclasses
import io
import json
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from arborlm.io import read_json, write_json

from . import budget, cells, core, evaluate, gates
from . import combined as combined_mod
from .combined import Sentence, combined_set
from .memory import MemoryArm, NullArm, SparseStore, new_lora_arm
from .registry import replicate_cells
from .train import process_memory_bytes, train_arm
from .world import World, load_arm

ANALYSIS_REPLICATES = 4  # the synthetic registry of the rehearsal is the whole registry (four replicates, the largest rung)


class RehearsalFailed(RuntimeError):
    """A rehearsal cell or probe failed: the rates cannot be measured and the work stops before the freeze (a device error is reported to the lead; nothing is silently moved to another device)."""


def peak_rss_bytes() -> int:
    return int(process_memory_bytes()["rss_peak"])


def timed(fn: Callable[[], Any]) -> float:
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def scale_factor(world: World) -> float:
    """The registered scoring work over the rehearsal's: every item of every registered panel (E_A, E_B and, where built, E_open_A and E_open_B: re-check B, N1) over the calibration items the rehearsal world
    scores in their place (each panel is replaced by the D_cal panel of its capability), at least 1 (a smaller registered panel is not scaled down: the rule counts the larger). Scoring time is proportional to
    the items scored, so the rehearsal's seconds on D_cal items are multiplied by this factor (a projection from item counts, not a measurement of E)."""
    reg = sum(len(p.examples) for p in world.ctx.panels.values())
    cal = sum(len(world.d_cal[p.task].examples) for p in world.ctx.panels.values())
    return max(1.0, reg / max(1, cal))


def rate_key(group: str, layer: int) -> str:
    return f"{group}@L{layer}" if group in budget.STORE_TYPE_GROUPS else group


def rates_from_records(records: Mapping[str, Mapping[str, Any]], layer: int) -> dict[str, float]:
    """Seconds per update of each cell group from the training records of a rehearsal replicate (the slowest variant of a group counts). A cell that did not complete stops the rehearsal."""
    bad = [f"{lab}: {r['train'][0].get('error') if r.get('train') else r['status']}" for lab, r in records.items() if r["status"] != "completed"]
    if bad:
        raise RehearsalFailed("rehearsal cells did not complete: " + "; ".join(bad[:4]))
    out: dict[str, float] = {}
    for lab, r in records.items():
        group = lab.split("/")[1]
        k = rate_key(group, layer)
        out[k] = max(out.get(k, 0.0), float(r["train"][0]["seconds_per_update"]))
    return out


def full_length_rates(short: Mapping[str, float], full: Mapping[str, float], layer: int) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    """The per-update rates of the registered projection: the short-run rates, replaced by the full-length cells' where they were run. The full-length store cell is the ST1 type itself and the full-length M-ii
    cell the M-ii type itself. Where a full-length cell of one type stands in for another (ST1 for M-append-frozen, M-seq and MA-gold; the LoRA cell for L-seq), the record says so and the projection uses the
    LARGER of that rate and the type's own short-run rate (the lead's rule of 2026-11-15). Returns the rates and the stand-in record."""
    rates_u = dict(short)
    stand_in: dict[str, dict[str, Any]] = {}

    def stands_in(key: str, source: str) -> None:
        own = float(short.get(key, 0.0))
        rates_u[key] = max(float(full[source]), own)
        stand_in[key] = {"full_length_cell": source, "full_length_rate": float(full[source]), "own_short_run_rate": own, "used": rates_u[key], "rule": "the larger of the full-length stand-in rate and the type's own short-run rate"}

    rates_u[f"ST1@L{layer}"] = float(full["ST1"])
    for g in ("MAF", "MSEQ", "MAGOLD"):
        stands_in(f"{g}@L{layer}", "ST1")
    rates_u[f"MII@L{layer}"] = float(full["MII"])
    rates_u["LORA1"] = float(full["LORA1"])
    stands_in("LSEQ", "LORA1")
    for g in ("MJOINT", "ETABLE"):  # rehearsed at 200 updates; the larger of that rate and the full-length rate of the nearest type (a store cell), at the calibrated layer (re-check B, m2; the lead's ruling)
        stands_in(f"{g}@L{layer}", "ST1")
    stands_in("LJOINT", "LORA1")
    return rates_u, stand_in


def measure_full_length(world: World, replicate: int, full_updates: int) -> dict[str, float]:
    """The ADR's rehearsal content: one store cell, one M-ii cell and one LoRA cell for the full U, at the calibrated read layer and learning rates, each in its registered configuration (M-ii continues an
    appended 2N-row store, as registered). Their per-update rates (and the peak after them) replace the short-run rates of the same cell types at the calibrated layer."""
    plan = world.plan(replicate)
    ex_a, ex_b = world.train_examples(replicate, "A"), world.train_examples(replicate, "B")
    codes = world.codes(replicate)

    def run(arm: Any, examples: Any, lr: float, **kw: Any) -> float:
        rec = train_arm(world.student, arm, examples, full_updates, world.batch, lr, plan.gen(2, "batch order (full-length rehearsal)"), world.marker_index, device=world.device, **kw)
        if rec.status != "completed":
            raise RehearsalFailed(f"the full-length rehearsal cell failed: {rec.error}")
        return float(rec.seconds_per_update)

    st = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (full-length rehearsal)")), world.layer, codes)
    out = {"ST1": run(st, ex_a, world.store_lr)}
    peak = process_memory_bytes()["max"]
    maf = st.store.clone()
    maf.append_stage(world.rows_per_stage, plan.gen(6, "stage-2 appended rows (full-length rehearsal)"))
    maf.freeze_stage(0)
    maf.set_trainable([1])
    mii_store = maf.clone()
    mii_store.set_trainable([0, 1])
    mii = MemoryArm(mii_store, world.layer, codes)
    out["MII"] = run(mii, ex_b, world.store_lr, replay=ex_a, replay_rows=world.replay_rows, replay_generator=plan.gen(2, "M-ii replayed rows order (full-length rehearsal)"))
    peak = max(peak, process_memory_bytes()["max"])
    out["LORA1"] = run(new_lora_arm(world.cfg, world.rank_single, plan.gen(8, "LoRA initialization (full-length rehearsal)")), ex_a, world.lora_lr)
    out["peak_bytes"] = float(max(peak, process_memory_bytes()["max"]))
    out["updates"] = float(full_updates)
    return out


class _Replay:
    """A tokenizer stand-in for text that is already tokenized: it returns the stored ids and character offsets (``windows.cut_windows`` needs only ``encode_offsets``)."""

    def __init__(self, ids: list[int], offs: list[tuple[int, int]]) -> None:
        self.ids, self.offs = ids, offs

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        return list(self.ids), list(self.offs)


def train_windows(world: World) -> list[evaluate.GeneralWindow]:
    """The GEN windows of the rehearsal (re-check A, R14; the lead's ruling): the stored WikiText-2 TRAIN token ids, decoded with the study's byte decoder, cut by ``windows.cut_windows`` (the same rule as the
    registered windows: consecutive non-overlapping windows, the marker-like and ordinary strata) and sampled to the registered stratum counts. The registered windows (WikiText-2 validation, "used for nothing
    else") are never used here. A stratum with too few windows repeats its own windows (timing only); an empty stratum borrows the other one's."""
    import codecs

    from .windows import cut_windows

    registered = world.ctx.windows
    window = len(registered[0].ids)
    decision = world.ctx.decision_index + 1
    want = {s: sum(1 for w in registered if w.stratum == s) for s in ("marker", "ordinary")}
    ids_all = list(world.wiki_train_ids)
    found: list[evaluate.GeneralWindow] = []
    for limit in (window * 600, len(ids_all)):
        ids = ids_all[:limit]
        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
        parts: list[str] = []
        offs: list[tuple[int, int]] = []
        pos = 0
        for i in ids:
            s = dec.decode(world.decoder.table[i])
            offs.append((pos, pos + len(s)))
            pos += len(s)
            parts.append(s)
        parts.append(dec.decode(b"", final=True))
        found = cut_windows(_Replay(ids, offs), "".join(parts), world.partition.vocab_index, window, decision)  # type: ignore[arg-type]
        if sum(w.stratum == "marker" for w in found) >= want["marker"] and sum(w.stratum == "ordinary" for w in found) >= want["ordinary"]:
            break
    pools = {s: [w for w in found if w.stratum == s] for s in ("marker", "ordinary")}
    if not pools["marker"] and not pools["ordinary"]:
        raise RehearsalFailed("the WikiText-2 train text yields no GEN window by the registered rule: the rehearsal cannot time the GEN measurement")
    out: list[evaluate.GeneralWindow] = []
    for s in ("marker", "ordinary"):
        pool = pools[s] or pools["ordinary" if s == "marker" else "marker"]
        out += [pool[k % len(pool)] for k in range(want[s])]
    return out


def rehearsal_world(world: World) -> World:
    """The world as the rehearsal scores it: the single-task panels, the combined set and the teacher outputs are D_cal (the rehearsal's own scoring set), the replacement keeping every name the scoring
    code reads. E_A, E_B, E_C and E_open are not touched. Combined scorings reuse the first items of that set (item i paired with i + 1 mod m in stored order, the same alternation, no seed); an answer
    whose source has no reference in that language is generated and timed and not scored. Rehearsal combined scores are timing records, not results. (The lead's ruling A-M3: no evaluation panel is scored
    and no gap on one is computed before the freeze.)"""
    cap = len(world.d_cal["A"].examples)
    n_sub = min(len(world.ctx.subsample["E_A"]), cap)  # the same size of subsample, taken from the first D_cal items
    panels = {"E_A": world.d_cal["A"], "E_B": world.d_cal["B"]}
    for name, p in world.ctx.panels.items():  # E_open_A and E_open_B are timed on calibration stand-ins, oracle route only (re-check B, N1); every registered panel name has its stand-in
        if name.startswith("E_open"):
            dc = world.d_cal[p.task]
            panels[name] = dataclasses.replace(dc, source_index=tuple(range(len(dc.examples))))
    items = world.partition.panels["D_cal"]
    sentences = [Sentence(it.key, {c: world.bank.prompt(c, it.en) for c in core.TASKS if c in it.refs}, {c: tuple(it.refs.get(c, ())) for c in core.TASKS}) for it in items]
    ec = combined_set(sentences, None)
    ctx = dataclasses.replace(world.ctx, panels=panels, subsample={"E_A": list(range(n_sub)), "E_B": list(range(n_sub))}, ec=ec, windows=train_windows(world))
    part = dataclasses.replace(world.partition, panels={**world.partition.panels, "E_A": items, "E_B": items, "E_C": items, **({"E_open": items} if any(n.startswith("E_open") for n in panels) else {})})
    outs = {c: {"E_" + c: world.teacher_outputs[c]["D_cal"], "E_C": world.teacher_outputs[c]["D_cal"], **({"E_open": world.teacher_outputs[c]["D_cal"]} if "E_open_" + c in panels else {})} for c in core.TASKS}
    return dataclasses.replace(world, ctx=ctx, partition=part, teacher_outputs=outs, timing_items={})  # the stored timing draw indexes E_A and E_B, not D_cal: the rehearsal times the first items


def measure_combined(rw: World, replicate: int, store_arm: MemoryArm, items_for_check: int = 20) -> dict[str, Any]:
    """The check of the addendum (section 11 item 9): cache continuation against full recomputation of the step-2 input on up to 20 items, identical tokens, for a store arm, a one-adapter arm and L-sep. A
    difference is a G4-class defect and stops the work before the freeze. Times on the rehearsal set are recorded; the rates take the combined scoring from the stage functions themselves."""
    from .cells import AdapterRouteArm  # local: cells imports this module's neighbours

    ctx = rw.ctx
    cs = ctx.ec
    plan = rw.plan(replicate)
    lora = new_lora_arm(rw.cfg, rw.rank_single, plan.gen(8, "LoRA initialization (rehearsal combined)"))
    lora2 = new_lora_arm(rw.cfg, rw.rank_single, plan.gen(8, "LoRA initialization (rehearsal combined)"))
    lsep = AdapterRouteArm({"A": lora, "B": lora2})
    out: dict[str, Any] = {"items": len(cs.sentences)}
    times: dict[str, float] = {}
    for name, arm in (("store", store_arm), ("adapter", lora), ("lsep", lsep)):
        times[name] = timed(lambda arm=arm: combined_mod.score_combined_cell(ctx, arm, cs))  # type: ignore[misc]
        chk = combined_mod.check_continuation(ctx, arm, cs, items_for_check)
        out[f"continuation_{name}"] = chk
        if not chk["ok"]:
            raise RuntimeError(f"G4-class defect: cache continuation differs from full recomputation for the {name} arm: {chk['differences']}")
    n_c = rw.sizes.panel_combined
    scale = n_c / max(1, len(cs.sentences))
    out["seconds_on_rehearsal_items"] = times
    out["cell_seconds_at_panel_size"] = max(times.values()) * scale  # the slowest kind of arm, scaled to |E_C| (a projection, not a measurement of E_C)
    out["stage0_seconds_at_panel_size"] = timed(lambda: combined_mod.score_combined_cell(ctx, NullArm(), cs)) * scale
    return out


# --- the child process ---------------------------------------------------------------------------------------------------------------------------
def _child_world(data_dir: Path, layer: int, lora_lr: float) -> World:
    """The world of a fresh child: the REAL registered entry (``build_world`` with ``RunConfig.registered`` on rehearsal seeds, scoring device CPU), never a test-mode stand-in path (audit B m2)."""
    from .worldio import RunConfig, build_world, read_bundle

    return build_world(read_bundle(data_dir), "rehearsal", max(a for a, _b in budget.rungs()), RunConfig.registered(layer, 1, float(core.CFG["training"]["store_learning_rate"]), lora_lr, "cpu"))


def _startup(data_dir: Path, layer: int, lora_lr: float) -> dict[str, Any]:
    t0 = time.perf_counter()
    _child_world(data_dir, layer, lora_lr)
    return {"seconds_in_child": time.perf_counter() - t0, "peak_bytes": process_memory_bytes()["max"]}


def synthetic_registry_run(src: Path, dst: Path, updates: int, replicates: int = ANALYSIS_REPLICATES) -> dict[str, Any]:
    """Synthetic records of the whole registry (four replicates of 18 cells) built by copying the one scored rehearsal replicate under each replicate's labels, with a missing cell, a rejected consolidation,
    an inertia cell and a non-finite value injected. They exist to run the analysis and report stages at registry size; the study they describe is synthetic and its label is not a result."""
    base_text = (src / "r0.json").read_text()
    dst.mkdir(parents=True, exist_ok=True)
    for sub in ("evaluate", "recompute"):
        (dst / sub).mkdir(exist_ok=True)
    injected: list[str] = []
    for r in range(replicates):
        rep = json.loads(base_text.replace('"r0/', f'"r{r}/'))
        labs = {c.group + "/" + c.variant: f"r{r}/{c.group}/{c.variant}" for c in replicate_cells(r)}
        if r == 1 and replicates > 1:
            rep["cells"].pop(labs["MAF/AB"], None)
            injected.append(f"r{r}: a missing cell ({labs['MAF/AB']})")
        if r == 2 and replicates > 2:
            cons = rep["cells"].get(labs["MII/AB"], {}).get("extras", {}).get("consolidation")
            if cons is not None:
                cons.update(rejected=True, published=False)
                injected.append(f"r{r}: a rejected consolidation ({labs['MII/AB']})")
            cons = rep["cells"].get(labs["MII/BA"], {}).get("extras", {}).get("consolidation")
            if cons is not None:
                cons.update(below_floor=True)
                injected.append(f"r{r}: an inertia cell ({labs['MII/BA']})")
        if r == 3 and replicates > 3:
            sc = rep["cells"].get(labs["MAF/BA"], {}).get("scores", {}).get(labs["MAF/BA"], {}).get("panels", {}).get("E_A")
            if sc is not None:
                sc["mean"] = "nan"
                injected.append(f"r{r}: a non-finite value ({labs['MAF/BA']} E_A mean)")
        for sub in ("evaluate", "recompute"):
            write_json(dst / sub / f"r{r}.json", rep)
    base = json.loads((src / "baseline.json").read_text())
    for sub in ("evaluate", "recompute"):
        write_json(dst / sub / "baseline.json", base)
        write_json(dst / sub / "stopped.json", [])
    (dst / "train").mkdir(exist_ok=True)
    write_json(dst / "train" / "stopped.json", [])
    write_json(dst / "gates.json", {**{f"G{i}": {"ok": True} for i in range(1, 10)}, "ok": True, "replicate_overlap": {}})
    return {"injected": injected, "design": {"replicates": replicates, "updates": updates, "synthetic": True}, "prefreeze": {"teacher_only": True, "stop": None}}


def _probe(data_dir: Path, scratch: Path, layer: int, lora_lr: float, updates: int) -> dict[str, Any]:
    """The scoring half of the rehearsal in a fresh process on CPU, on the rehearsal world (D_cal in place of every evaluation panel): the registered evaluate, timing and recompute stage functions on the
    snapshots the parent trained, the combined continuation check, and the analysis and report stages on synthetic records of the whole registry. Returns seconds on D_cal items (the parent scales them)."""
    from . import stages

    t0 = time.perf_counter()
    world = _child_world(data_dir, layer, lora_lr)
    rw = rehearsal_world(world)
    out: dict[str, Any] = {"startup_world_seconds": time.perf_counter() - t0, "start_peak_bytes": process_memory_bytes()["max"]}
    arm = load_arm(rw, 0, scratch / "snapshots", "r0/ST1/AB")
    out["panel_seconds"] = timed(lambda: [evaluate.score_panel(rw.ctx, arm, p) for p in rw.ctx.panels.values()])
    out["baseline_seconds"] = timed(lambda: cells.stage0_scores(rw))
    out["evaluate_total_seconds"] = timed(lambda: stages.stage_evaluate(rw, scratch))
    out["eval_peak_bytes"] = process_memory_bytes()["max"]
    out["timing_seconds"] = timed(lambda: stages.stage_timing(rw, scratch))
    out["recompute_seconds"] = timed(lambda: stages.stage_recompute(rw, scratch))
    out["recompute_peak_bytes"] = process_memory_bytes()["max"]
    assert isinstance(arm, MemoryArm)
    out["combined_check"] = measure_combined(rw, 0, arm)
    synth = scratch / "synthetic-registry"
    meta = synthetic_registry_run(scratch / "evaluate", synth, updates)
    with contextlib.redirect_stdout(io.StringIO()):
        out["analysis_seconds"] = timed(lambda: stages.stage_analysis(synth, meta["design"], meta["prefreeze"]))
        out["report_seconds"] = timed(lambda: stages.stage_report(synth))
    out["synthetic_registry"] = {"injected": meta["injected"], "note": "synthetic records of the whole registry: a mechanics and timing check; the label printed is not a result", "omission": "a missing cell is injected, so the analysis computes no bootstrap intervals here: analysis_seconds excludes them (about 5 s at registered size, inside the 60 s floor; re-check B, m10)"}
    out["probe_peak_bytes"] = process_memory_bytes()["max"]
    return out


def _run_child(args: list[str], repo: Path | None) -> dict[str, Any]:
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, "-m", "studies.p10s2.rehearsal", *args], cwd=repo or core.ROOT, check=False, capture_output=True, text=True)  # noqa: S603
    wall = time.perf_counter() - t0
    if p.returncode != 0:
        raise RehearsalFailed(f"the rehearsal child {args[0]} failed (exit {p.returncode}):\n{p.stderr[-2000:]}")
    last = [ln for ln in p.stdout.splitlines() if ln.startswith("{")][-1]
    return {**json.loads(last), "wall_seconds": wall}


def measure_task_overhead(data_dir: Path, repo: Path | None = None, *, layer: int | None = None, lora_lr: float | None = None) -> dict[str, float]:
    """Per-process start-up: the wall seconds of a fresh child process that imports the package, reads the frozen bundle (hash-checked) and builds the world through the registered entry on rehearsal seeds,
    and the child's own peak (the whole-task peak). The child reports its own peak (the parent's children-peak would be a maximum over every child ever run)."""
    ly = layer if layer is not None else core.READ_LAYERS[0]
    lr = lora_lr if lora_lr is not None else float(core.CFG["training"]["lora_learning_rates"][0])
    r = _run_child(["startup", "--data-dir", str(data_dir), "--layer", str(ly), "--lora-lr", str(lr)], repo)
    return {"seconds": float(r["wall_seconds"]), "peak_bytes": float(r["peak_bytes"])}


def time_prefreeze_gates(world: World, run_dir: Path, g1: Mapping[str, Any], g3: Mapping[str, Any], equivalence_record: dict[str, Any] | None, file_manifest: Mapping[str, Mapping[str, str]], root: Path, *, updates: int | None = None, require_mps: bool = True, cpu_by_freeze: bool = False) -> dict[str, Any]:
    """The pre-freeze gates stage at real size on rehearsal seeds, on the rehearsal world (no evaluation panel scored, no gap on one computed). Its wall time scaled by the registered item counts is the
    second gates stage's time in R: the scoring-bearing parts (G2's two Stage 0 scorings and the three panel scorings of G4) are multiplied by ``scale_factor``, the rest (20-update runs, hash checks) is not."""
    rw = rehearsal_world(world)
    plan = core.SeedPlan("rehearsal", 0)
    s = scale_factor(world)
    t0 = time.perf_counter()
    out = gates.run_gates(rw, plan, g1=g1, g3=g3, equivalence_record=equivalence_record, file_manifest=file_manifest, root=root, updates=updates, require_mps=require_mps, cpu_by_freeze=cpu_by_freeze)
    total = time.perf_counter() - t0
    first = next(iter(rw.ctx.panels.values()))
    t_g2 = timed(lambda: gates.g2(rw))
    t_panel = timed(lambda: evaluate.score_panel(rw.ctx, NullArm(), first, route="none"))
    scaled = total + (s - 1.0) * (t_g2 + 3.0 * t_panel)
    return {"gates": out, "ok": bool(out["ok"]), "seconds_measured": total, "scale": s, "seconds_scaled_to_registered_panels": scaled, "scaled_parts": {"g2_seconds": t_g2, "g4_panel_scorings_seconds": 3.0 * t_panel}, "method": "wall seconds of the gates stage on D_cal items; G2's two Stage 0 scorings and G4's three panel scorings multiplied by (registered items) / (D_cal items); the rest unscaled", "type": "measured on rehearsal seeds and D_cal items, scaled by item counts (a projection, not a measurement of E)"}


def measure_rates(world: World, replicate: int, *, updates: int, full_updates: int, overhead: dict[str, float], gates2_seconds: float, scratch: Path, data_dir: Path, repo: Path | None = None, device_reason: str = "", gates_peak_bytes: int = 0) -> tuple[budget.Rates, dict[str, Any]]:
    """The rates of section 13.3, measured by the registered stage functions (see the module docstring). ``world`` is a rehearsal-mode world on the frozen training device at the calibrated layer;
    ``scratch`` receives the rehearsal's snapshots and records; ``gates2_seconds`` is the scaled time of the pre-freeze gates stage."""
    from . import stages

    t_all = time.perf_counter()
    rec: dict[str, Any] = {"device": str(world.device), "calibrated_layer": world.layer}
    layers = [world.layer, *[ly for ly in core.READ_LAYERS if ly != world.layer]] if world.layer in core.READ_LAYERS else [world.layer]
    short: dict[str, float] = {}
    train_peak = 0
    phase_seconds: dict[str, float] = {}
    for ly in layers:
        w = dataclasses.replace(world, layer=ly, updates=updates)
        d = scratch / f"train-L{ly}"
        phase_seconds[f"train_all_cells_L{ly}"] = timed(lambda w=w, d=d: stages.stage_train(w, d))  # type: ignore[misc]
        short.update(rates_from_records(read_json(d / "train" / f"r{replicate}.json"), ly))
        train_peak = max(train_peak, int(process_memory_bytes()["max"]))
    rec["short_run_update_seconds"] = dict(short)
    rec["other_layer_seconds"] = float(sum(v for k, v in phase_seconds.items() if not k.endswith(f"L{world.layer}")))
    full = measure_full_length(world, replicate, full_updates)
    rec["full_length"] = full
    train_peak = max(train_peak, int(full["peak_bytes"]))
    ly = world.layer
    rates_u, stand_in = full_length_rates(short, full, ly)
    rec["stand_in_rates"] = stand_in
    rec["update_seconds"] = rates_u
    s = scale_factor(world)
    probe = _run_child(["probe", "--data-dir", str(data_dir), "--scratch", str(scratch / f"train-L{ly}"), "--layer", str(ly), "--lora-lr", str(world.lora_lr), "--updates", str(updates)], repo)
    rec["probe"] = probe
    rec["scale"] = s
    panel = float(probe["panel_seconds"]) * s
    comb = probe["combined_check"]
    combined_cell, combined_stage0 = float(comb["cell_seconds_at_panel_size"]), float(comb["stage0_seconds_at_panel_size"])  # the combined scoring at the size of E_C (addendum section 10), counted on its own line
    base = max(0.0, float(probe["baseline_seconds"]) * s - combined_stage0)  # Stage 0 and the teacher scores, without the combined Stage 0 counted separately
    rep_total = max(0.0, (float(probe["evaluate_total_seconds"]) - float(probe["baseline_seconds"])) * s)
    extra = max(0.0, rep_total - 18 * panel - budget.COMBINED_CELLS * combined_cell)  # the replicate's whole scoring as measured, less the 18 panel scorings and the combined scorings the rate model counts separately
    timing_items = int(core.CFG["budget"]["timing_items"])
    cal_items = min(len(world.d_cal[c].examples) for c in core.TASKS)
    t_scale = max(1.0, timing_items / max(1, min(cal_items, timing_items)))  # the timing benchmark scores min(200, items) items per panel in the probe; scaled to the registered count if the probe had fewer
    timing = float(probe["timing_seconds"]) * t_scale
    rec.update({"panel_seconds": panel, "replicate_extra_seconds": extra, "fixed_seconds": base, "timing_seconds": timing, "gates2_seconds": gates2_seconds, "phase_seconds": phase_seconds, "wall_seconds_total": time.perf_counter() - t_all,
                "method": "stage functions run on the rehearsal world (D_cal items); scoring seconds multiplied by (registered E_A + E_B items) / (D_cal items); the combined scoring is timed on the D_cal set and scaled to |E_C|, and is subtracted from the replicate's measured scoring so that it is counted once"})
    rates = budget.Rates(
        update_seconds=rates_u, calibrated_layer=world.layer, panel_seconds=panel, replicate_extra_seconds=extra, fixed_seconds=base, timing_seconds=timing, gates2_seconds=gates2_seconds,
        task_overhead_seconds=float(overhead["seconds"]), train_peak_bytes=train_peak, eval_peak_bytes=int(probe["eval_peak_bytes"]), recompute_peak_bytes=int(probe["recompute_peak_bytes"]), task_peak_bytes=int(max(overhead["peak_bytes"], probe["start_peak_bytes"], gates_peak_bytes)),
        other_layer_seconds=rec["other_layer_seconds"], combined_cell_seconds=combined_cell, combined_stage0_seconds=combined_stage0, analysis_seconds=float(probe["analysis_seconds"]), report_seconds=float(probe["report_seconds"]),
        train_device=world.device.type, train_device_reason=device_reason,
    )  # fmt: skip
    return rates, rec


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="python -m studies.p10s2.rehearsal")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("startup", help="build the world from a frozen bundle through the registered entry and report (measures the per-process start-up)")
    pr = sub.add_parser("probe", help="the scoring half of the rehearsal in a fresh process (CPU, rehearsal world)")
    for c in (s, pr):
        c.add_argument("--data-dir", required=True)
        c.add_argument("--layer", type=int, required=True)
        c.add_argument("--lora-lr", type=float, required=True)
    pr.add_argument("--scratch", required=True)
    pr.add_argument("--updates", type=int, required=True)
    a = p.parse_args(argv)
    res = _startup(Path(a.data_dir), a.layer, a.lora_lr) if a.command == "startup" else _probe(Path(a.data_dir), Path(a.scratch), a.layer, a.lora_lr, a.updates)
    sys.stdout.write(json.dumps(core.jsonable(res)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
