# ruff: noqa: E501
"""Rehearsal measurements (ADR-0022 section 13.3, "Rehearsal content"): the rates the rung rule reads. The measuring functions here are generic over a ``World``; the rehearsal itself is not run in this
implementation step (only a tiny test on synthetic stand-ins and test seeds checks the plumbing from timed phases to ``budget.Rates`` and to the rule).

Rehearsal content, at full size on rehearsal seeds: every cell type for 200 updates; one store cell, one M-ii cell and one LoRA cell for the full U; 200 updates of each store-type cell type at the read layer
that calibration did not select (for the rule's rates); one scoring of each kind; the truncation percentile of section 5.4; the gates stage; analysis and report on synthetic records of the whole registry
including missing cells, rejected consolidations, inertia cells and non-finite values. Peak memory is the process's maximum resident set after each phase (monotone, so a later phase's peak is an upper bound
of an earlier one's: conservative); the whole-task peak and the per-process start-up are measured in a fresh child process.
"""

import dataclasses
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from . import budget, cells, core, evaluate, gates
from . import combined as combined_mod
from .combined import Sentence, combined_set
from .memory import MemoryArm, NullArm, SparseStore, TableArm, new_lora_arm
from .train import train_arm
from .world import World


def peak_rss_bytes() -> int:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r if sys.platform == "darwin" else r * 1024)


def measure_update_rates(world: World, replicate: int, updates: int) -> dict[str, float]:
    """Seconds per update for every cell type, store-type cells at both read layers (the rate the rule needs for U = 1,000), measured on ``updates`` updates."""
    plan = world.plan(replicate)
    out: dict[str, float] = {}
    ex_a = world.train_examples(replicate, "A")
    ex_b = world.train_examples(replicate, "B")

    def timed(arm: Any, examples: Any, **kw: Any) -> float:
        rec = train_arm(world.student, arm, examples, updates, world.batch, world.store_lr, plan.gen(2, "batch order (rehearsal)"), world.marker_index, device=world.device, **kw)
        return float(rec.seconds_per_update)

    for ly in core.READ_LAYERS if world.layer in core.READ_LAYERS else (world.layer,):
        w = dataclasses.replace(world, layer=ly)
        codes = w.codes(replicate)

        def store(rows: int, w: Any = w, codes: Any = codes) -> MemoryArm:
            return MemoryArm(SparseStore.new(w.cfg.width, rows, plan.gen(0, "stage-1 store (rehearsal)")), w.layer, codes)

        out[f"ST1@L{ly}"] = timed(store(w.rows_per_stage), ex_a)
        out[f"MAF@L{ly}"] = out[f"ST1@L{ly}"]
        out[f"MSEQ@L{ly}"] = out[f"ST1@L{ly}"]
        out[f"MAGOLD@L{ly}"] = out[f"ST1@L{ly}"]
        out[f"MJOINT@L{ly}"] = timed(store(2 * w.rows_per_stage), [*ex_a, *ex_b])
        mii = store(w.rows_per_stage)
        out[f"MII@L{ly}"] = timed(mii, ex_b, replay=ex_a, replay_rows=w.replay_rows, replay_generator=plan.gen(2, "M-ii replayed rows order (rehearsal)"))
    out["ETABLE"] = timed(TableArm("A", world.cfg.width, world.vocabulary, world.layer, plan.gen(9, "E-table initialization (rehearsal)")), ex_a)
    out["LORA1"] = timed(new_lora_arm(world.cfg, world.rank_single, plan.gen(8, "LoRA initialization (rehearsal)")), ex_a)
    out["LSEQ"] = out["LORA1"]
    out["LJOINT"] = timed(new_lora_arm(world.cfg, world.rank_joint, plan.gen(8, "LoRA initialization (rehearsal, L-joint)")), [*ex_a, *ex_b])
    return out


def measure_full_length(world: World, replicate: int, full_updates: int) -> dict[str, float]:
    """The ADR's rehearsal content: one store cell, one M-ii cell and one LoRA cell for the full U, at the calibrated read layer and learning rates. Their per-update rates (and the peak after them)
    replace the short-run rates of the same cell types at the calibrated layer; rates must not come only from short runs."""
    plan = world.plan(replicate)
    ex_a, ex_b = world.train_examples(replicate, "A"), world.train_examples(replicate, "B")
    codes = world.codes(replicate)

    def run(arm: Any, examples: Any, lr: float, **kw: Any) -> float:
        rec = train_arm(world.student, arm, examples, full_updates, world.batch, lr, plan.gen(2, "batch order (full-length rehearsal)"), world.marker_index, device=world.device, **kw)
        return float(rec.seconds_per_update)

    st = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (full-length rehearsal)")), world.layer, codes)
    out = {"ST1": run(st, ex_a, world.store_lr)}
    mii = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (full-length rehearsal)")), world.layer, codes)
    out["MII"] = run(mii, ex_b, world.store_lr, replay=ex_a, replay_rows=world.replay_rows, replay_generator=plan.gen(2, "M-ii replayed rows order (full-length rehearsal)"))
    out["LORA1"] = run(new_lora_arm(world.cfg, world.rank_single, plan.gen(8, "LoRA initialization (full-length rehearsal)")), ex_a, world.lora_lr)
    out["peak_bytes"] = float(peak_rss_bytes())
    out["updates"] = float(full_updates)
    return out


def rehearsal_world(world: World) -> World:
    """The world as the rehearsal scores it: the single-task panels, the combined set and the teacher outputs are D_cal (the rehearsal's own scoring set), the replacement keeping every name the scoring
    code reads. E_A, E_B, E_C and E_open are not touched. Combined scorings reuse the first items of that set (item i paired with i + 1 mod m in stored order, the same alternation, no seed); an answer
    whose source has no reference in that language is generated and timed and not scored. Rehearsal combined scores are timing records, not results."""
    cap = len(world.d_cal["A"].examples)
    n_sub = min(len(world.ctx.subsample["E_A"]), cap)  # the same size of subsample, taken from the first D_cal items
    panels = {"E_A": world.d_cal["A"], "E_B": world.d_cal["B"]}
    items = world.partition.panels["D_cal"]
    sentences = [Sentence(it.key, {c: world.bank.prompt(c, it.en) for c in core.TASKS if c in it.refs}, {c: tuple(it.refs.get(c, ())) for c in core.TASKS}) for it in items]
    ec = combined_set(sentences, None)
    ctx = dataclasses.replace(world.ctx, panels=panels, subsample={"E_A": list(range(n_sub)), "E_B": list(range(n_sub))}, ec=ec)
    part = dataclasses.replace(world.partition, panels={**world.partition.panels, "E_A": items, "E_B": items, "E_C": items})
    outs = {c: {"E_" + c: world.teacher_outputs[c]["D_cal"], "E_C": world.teacher_outputs[c]["D_cal"]} for c in core.TASKS}
    return dataclasses.replace(world, ctx=ctx, partition=part, teacher_outputs=outs)


def measure_combined(rw: World, replicate: int, store_arm: MemoryArm, items_for_check: int = 20) -> dict[str, Any]:
    """One combined scoring of each kind of arm on the rehearsal set (a store arm, a one-adapter arm, L-sep), timed, and the check of the addendum (section 11 item 9): cache continuation against full
    recomputation of the step-2 input on up to 20 items, identical tokens. A difference is a G4-class defect and stops the work before the freeze."""
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
        times[name] = timed(lambda arm=arm: combined_mod.score_combined_cell(ctx, arm, cs))
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


def measure_task_overhead(data_dir: Path, repo: Path | None = None) -> dict[str, float]:
    """Per-process start-up: the wall seconds of a fresh child process that imports the package, reads the frozen bundle (hash-checked) and builds the world, and the child's peak RSS (the whole-task peak)."""
    t0 = time.perf_counter()
    subprocess.run([sys.executable, "-m", "studies.p10s2.rehearsal", "startup", "--data-dir", str(data_dir)], cwd=repo or core.ROOT, check=True, capture_output=True)  # noqa: S603
    wall = time.perf_counter() - t0
    r = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return {"seconds": wall, "peak_bytes": float(r if sys.platform == "darwin" else r * 1024)}


def measure_rates(world: World, replicate: int, *, updates: int, full_updates: int, overhead: dict[str, float], timing_items: int = 3) -> tuple[budget.Rates, dict[str, Any]]:
    """The rates of section 13.3: ``updates`` (200) updates of every cell type at both read layers, the full-U cells of ``measure_full_length`` for the calibrated layer, and one scoring of each kind. Returns
    the rates and the raw measurements."""
    ctx = world.ctx
    ctx.seed_plan = world.plan(replicate)
    rec: dict[str, Any] = {}
    t0 = time.perf_counter()
    rates_u = measure_update_rates(world, replicate, updates)
    rec["short_run_update_seconds"] = dict(rates_u)
    full = measure_full_length(world, replicate, full_updates)
    rec["full_length"] = full
    ly = world.layer
    for g in ("ST1", "MAF", "MSEQ", "MAGOLD"):
        rates_u[f"{g}@L{ly}"] = full["ST1"]  # the same cell type as the full-length store cell
    rates_u[f"MII@L{ly}"] = full["MII"]
    rates_u["LORA1"] = rates_u["LSEQ"] = full["LORA1"]
    rec["update_seconds"] = rates_u
    train_peak = max(peak_rss_bytes(), int(full["peak_bytes"]))
    # one training of each kind for scoring
    plan = world.plan(replicate)
    arm = MemoryArm(SparseStore.new(world.cfg.width, world.rows_per_stage, plan.gen(0, "stage-1 store (rehearsal)")), world.layer, world.codes(replicate))
    train_arm(world.student, arm, world.train_examples(replicate, "A"), updates, world.batch, world.store_lr, plan.gen(2, "batch order (rehearsal)"), world.marker_index, device=world.device)
    t1 = time.perf_counter()
    rw = rehearsal_world(world)  # every scoring below is on D_cal, never on E_A, E_B, E_C or any registered panel (the lead's ruling)
    ctx = rw.ctx
    ctx.seed_plan = world.plan(replicate)
    panel_seconds = timed(lambda: [evaluate.score_panel(ctx, arm, p) for p in ctx.panels.values()])
    routers = cells.build_routers(rw, replicate)
    extra = timed(lambda: (cells.score_snapshot(rw, replicate, arm, router=routers[("A",)][0], ablation_stages=[0], ablation_tasks=core.TASKS, gen=True, learned_route=True, combined=False, seen=True), cells.retrieval_scores(rw, replicate)))
    fixed = timed(lambda: cells.stage0_scores_without_combined(rw))
    comb = measure_combined(rw, replicate, arm)
    rec["combined"] = comb
    timing = timed(lambda: evaluate.timing_benchmark(lambda: evaluate.score_panel(ctx, arm, next(iter(ctx.panels.values())), indices=list(range(timing_items))), 1))
    eval_peak = peak_rss_bytes()
    plan0 = core.SeedPlan(world.mode, replicate)
    gates_seconds = timed(lambda: (gates.g4(rw, plan0, 2), gates.g5(rw, plan0)))
    rec.update({"panel_seconds": panel_seconds, "replicate_extra_seconds": extra, "fixed_seconds": fixed, "timing_seconds": timing, "gates2_seconds": gates_seconds, "wall_seconds_total": time.perf_counter() - t0, "scoring_started_after": t1 - t0})
    # the 18 scorings include one panel scoring each; the extras measured above are for one memory cell: scale to the cells that carry them (reading: the ADR lists the extras per replicate)
    rates = budget.Rates(
        update_seconds=rates_u, calibrated_layer=world.layer, panel_seconds=panel_seconds, replicate_extra_seconds=extra * 11, fixed_seconds=fixed, timing_seconds=timing, gates2_seconds=gates_seconds,
        combined_cell_seconds=comb["cell_seconds_at_panel_size"], combined_stage0_seconds=comb["stage0_seconds_at_panel_size"], task_overhead_seconds=float(overhead["seconds"]), train_peak_bytes=train_peak, eval_peak_bytes=eval_peak, recompute_peak_bytes=eval_peak, task_peak_bytes=int(overhead["peak_bytes"]),
    )  # fmt: skip
    return rates, rec


def timed(fn: Any) -> float:
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def _startup(data_dir: Path) -> int:
    from .worldio import RunConfig, build_world, read_bundle

    build_world(read_bundle(data_dir), "test", 1, RunConfig.dry())
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="python -m studies.p10s2.rehearsal")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("startup", help="build the world from a frozen bundle and exit (measures the per-process start-up)")
    s.add_argument("--data-dir", required=True)
    a = p.parse_args(argv)
    return _startup(Path(a.data_dir)) if a.command == "startup" else 2


if __name__ == "__main__":
    raise SystemExit(main())
