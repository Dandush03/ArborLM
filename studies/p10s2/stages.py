# ruff: noqa: E501
"""P10S2 stage drivers: the stage functions (shared by the dry stage and the registered stages), the fixed registered launch interface, and the command line.

* ``dry``: a tiny synthetic end-to-end run on stand-ins and test seeds (gates, training of the whole registry, scoring, assembled composites, retrieval, routers, independent recomputation, analysis,
  report). It is not calibration, pilot, rehearsal or a registered stage and produces no result.
* ``registered <name> --run-dir D --freeze-commit C --caps studies/p10s2/freeze/stage_caps.json``: one registered stage by name. The launch scripts pass exactly this; every other value (design, data,
  calibration record, projection, caps) comes from the frozen plan and the frozen cap table, so no registered stage is launched by a typed value. A registered stage refuses unless the working tree is clean,
  the freeze commit is an ancestor of HEAD, the frozen paths equal their content at that commit, every identity in the plan holds, the stage has a cap for the plan's design, and the charged ledger has room.
* ``freeze`` and ``caps``: the freeze procedure writes the frozen plan and cap files (``freeze``).

Registered stages: gates (the second gates stage on registered seeds), train, evaluate, timing, recompute (the independent CPU recomputation, charged), analysis, report. Nothing here runs a registered
stage unless invoked through the registered command with a recorded freeze.
"""

import argparse
import json
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json, write_json

from . import analysis, budget, cells, core, freeze, gates, output, report, standins
from .ledger import Ledger, LedgerRefused
from .prefreeze import prefreeze_summary
from .registry import registry
from .world import World
from .worldio import DataBundle, RunConfig, build_world, read_bundle, write_bundle

REGISTERED_STAGES = budget.REGISTERED_STAGES


class StageRefused(RuntimeError):
    """A registered stage refuses to start (the P9-II convention): nothing is started and nothing is re-run with changed settings."""


class CapReached(RuntimeError):
    """A stage cap was reached: the stage is not continued (the label becomes INCOMPLETE)."""


class Deadline:
    def __init__(self, cap_seconds: float | None) -> None:
        self.cap = cap_seconds
        self.t0 = time.perf_counter()

    def check(self, what: str) -> None:
        if self.cap is not None and time.perf_counter() - self.t0 > self.cap:
            raise CapReached(f"the stage cap of {self.cap:.1f} s was reached before {what}")


def record(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, core.jsonable(obj))


# --- stage functions ---------------------------------------------------------------------------------------------------------------------------
def gate_inputs(world: World, prefreeze: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """G1 at stream level (the replicate draws of this run's seeds against the panels) and G3 from the pre-freeze record's qualification. The data step checked G1 on the pools; the gates stage checks the
    streams, where a registered replicate seed may be used."""
    from .data import gate_g1

    g1 = gate_g1(world.partition, world.streams, {c: [x.target for s in world.streams for x in s.t[c]] for c in core.TASKS})
    q = prefreeze.get("qualification", {})
    return g1, {"ok": bool(q.get("ok", False)), "outcome": q.get("outcome"), "failed": q.get("failed", [])}


def stage_gates(world: World, run_dir: Path, plan: core.SeedPlan, *, g1: Mapping[str, Any], g3: Mapping[str, Any], equivalence_record: dict[str, Any] | None, file_manifest: Mapping[str, Mapping[str, str]] | None = None, root: Path | None = None, updates: int | None = None) -> dict[str, Any]:
    out = gates.run_gates(world, plan, g1=g1, g3=g3, equivalence_record=equivalence_record, file_manifest=file_manifest, root=root, updates=updates)
    from .data import replicate_overlap

    out["replicate_overlap"] = replicate_overlap(world.streams)  # the share of training items common to each pair of replicates (section 5.2); no part of any gate
    record(run_dir / "gates.json", out)
    return out


def stage_train(world: World, run_dir: Path, deadline: Deadline | None = None) -> dict[str, Any]:
    stopped: list[str] = []
    for r in range(world.replicates):
        try:
            if deadline is not None:
                deadline.check(f"training replicate {r}")
        except CapReached as e:
            stopped.append(str(e))
            break
        recs = cells.train_replicate(world, r, run_dir / "snapshots")
        record(run_dir / "train" / f"r{r}.json", recs)
    record(run_dir / "train" / "stopped.json", stopped)
    return {"stopped": stopped}


def _load_train(run_dir: Path, r: int) -> dict[str, dict[str, Any]]:
    p = run_dir / "train" / f"r{r}.json"
    return read_json(p) if p.exists() else {}


def stage_evaluate(world: World, run_dir: Path, deadline: Deadline | None = None, *, subdir: str = "evaluate") -> dict[str, Any]:
    """Scoring on CPU from the snapshots: Stage 0 and the stored teacher scores, then per replicate the 18 cells, the assembled composites, the retrieval baselines and the router lane."""
    stopped: list[str] = []
    base = cells.stage0_scores(world)
    record(run_dir / subdir / "baseline.json", base)
    teacher_own = {c: base["teacher"].get("E_" + c, {}).get("mean") for c in core.TASKS}  # each teacher's own score on its panel (the ensemble must reproduce it)
    for r in range(world.replicates):
        try:
            if deadline is not None:
                deadline.check(f"scoring replicate {r}")
        except CapReached as e:
            stopped.append(str(e))
            break
        tr = _load_train(run_dir, r)
        routers = cells.build_routers(world, r)
        scored = cells.score_replicate(world, r, run_dir / "snapshots", tr, routers)
        ens_oracle = {c: evaluate_mean_teacher(world, c) for c in core.TASKS}
        ens_learned = ensemble_under_router(world, routers[("A", "B")][0])
        rep = {
            "cells": scored, "assembled": cells.assembled_scores(world, r, run_dir / "snapshots") if all(f"r{r}/{g}/{v}" in tr and tr[f"r{r}/{g}/{v}"]["status"] == "completed" for g, v in (("ST1", "AB"), ("ST1", "BA"), ("LORA1", "AB"), ("LORA1", "BA"))) else {},
            "retrieval": cells.retrieval_scores(world, r), "routers": cells.router_record(world, r, routers), "ensemble": {"oracle": ens_oracle, "teacher_own": teacher_own, "learned_router": ens_learned},
        }  # fmt: skip
        record(run_dir / subdir / f"r{r}.json", rep)
    record(run_dir / subdir / "stopped.json", stopped)
    return {"stopped": stopped}


def ensemble_under_router(world: World, router: Any) -> dict[str, float] | None:
    """The two teachers behind the learned keyword router: an item goes to the teacher the router names from the prompt (a wrongly routed item, or one routed to "none", scores 0)."""
    from . import evaluate, retrieval

    ctx = world.ctx
    refs = {c: ctx.panels["E_" + c].refs for c in core.TASKS}
    outs: dict[str, list[str]] = {}
    for c in core.TASKS:
        o = world.teacher_outputs.get(c, {}).get("E_" + c)
        if o is None:
            return None
        outs[c] = o
    decisions = {c: [(evaluate.route_for(ctx, ex, router, "learned") or ["none"])[0] for ex in ctx.panels["E_" + c].examples] for c in core.TASKS}
    return retrieval.ensemble_scores(outs, refs, lambda c, i: decisions[c][i])


def evaluate_mean_teacher(world: World, cap: str) -> float | None:
    """The oracle-routed ensemble's score on capability ``cap``: every item goes to its own capability's teacher through the route function, scored by the same chrF code. It must equal the teacher's own
    score (a difference is ENGINEERING-FAILURE, section 11.3)."""
    from . import retrieval

    ctx = world.ctx
    refs = {c: ctx.panels["E_" + c].refs for c in core.TASKS}
    outs: dict[str, list[str]] = {}
    for c in core.TASKS:
        o = world.teacher_outputs.get(c, {}).get("E_" + c)
        if o is None:
            return None
        outs[c] = o
    scores = retrieval.ensemble_scores(outs, refs, lambda c, _i: c)
    return scores[cap]


def stage_timing(world: World, run_dir: Path, items: int | None = None) -> dict[str, Any]:
    """The timing benchmark, separate from training: after all training, one process, CPU, six threads, median of three repetitions on a fixed subset of each panel. Descriptive only; no latency,
    throughput, storage or efficiency claim. The thread count of the process is restored afterwards (a leaked setting would change the bit-level behaviour of everything that runs later)."""
    from . import evaluate
    from .world import load_arm

    n_items = items if items is not None else core.CFG["budget"]["timing_items"]
    ctx = world.ctx
    previous = torch.get_num_threads()
    torch.set_num_threads(int(core.CFG["budget"]["timing_threads"]))
    try:
        out: dict[str, Any] = {"threads": torch.get_num_threads(), "items_per_panel": n_items, "type": "measured, descriptive; no efficiency claim"}
        snap_dir = run_dir / "snapshots"
        for label in ("r0/ST1/AB", "r0/MAF/AB", "r0/LORA1/AB"):
            if not (snap_dir / (label.replace("/", "__") + ".pt")).exists():
                continue
            arm = load_arm(world, 0, snap_dir, label)
            for name, p in ctx.panels.items():
                idx = list(range(min(n_items, len(p.examples))))
                out[f"{label}/{name}"] = evaluate.timing_benchmark(lambda arm=arm, p=p, idx=idx: evaluate.score_panel(ctx, arm, p, indices=idx))  # type: ignore[misc]
    finally:
        torch.set_num_threads(previous)
    record(run_dir / "timing.json", out)
    return out


def stage_recompute(world: World, run_dir: Path, deadline: Deadline | None = None) -> dict[str, Any]:
    """The independent recomputation of every score from the snapshots, on CPU, with deterministic algorithms, in a separate pass (``recompute/``). With the frozen scoring code every score must be
    bit-identical; the comparison and the label rule are in ``analysis.analyze_with_recomputation``."""
    previous, warn = torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled()
    torch.use_deterministic_algorithms(True)
    try:
        return stage_evaluate(world, run_dir, deadline, subdir="recompute")
    finally:
        torch.use_deterministic_algorithms(previous, warn_only=warn)


# --- assembling the study record and the outcome ------------------------------------------------------------------------------------------------
def assemble_study(run_dir: Path, design: Mapping[str, Any], prefreeze: Mapping[str, Any], gates_record: Mapping[str, Any] | None, *, subdir: str = "evaluate", extra_incomplete: Sequence[str] = ()) -> dict[str, Any]:
    n = int(design["replicates"])
    reps = []
    for r in range(n):
        p = run_dir / subdir / f"r{r}.json"
        reps.append(read_json(p) if p.exists() else {"cells": {}})
    base_p = run_dir / subdir / "baseline.json"
    incomplete = list(extra_incomplete)
    for kind in ("train", subdir):
        sp = run_dir / kind / "stopped.json"
        if sp.exists():
            incomplete += [f"a cap stopped the {kind} stage: {m}" for m in read_json(sp)]
    return {"design": dict(design), "prefreeze": dict(prefreeze), "gates": dict(gates_record or {}), "baseline": read_json(base_p) if base_p.exists() else {}, "replicates": reps, "incomplete": incomplete, "engineering": []}


def stage_analysis(run_dir: Path, design: Mapping[str, Any], prefreeze: Mapping[str, Any], mode: str = "frozen-code") -> dict[str, Any]:
    gp = run_dir / "gates.json"
    gates_record = read_json(gp) if gp.exists() else {}
    reg = assemble_study(run_dir, design, prefreeze, gates_record)
    rec_cells = None
    if (run_dir / "recompute").exists() and all((run_dir / "recompute" / f"r{r}.json").exists() for r in range(int(design["replicates"]))):
        rec_study = assemble_study(run_dir, design, prefreeze, gates_record, subdir="recompute")
        rec_cells = {lab: rec for rep in rec_study["replicates"] for lab, rec in rep["cells"].items()}
    outcome = analysis.analyze_with_recomputation(reg, rec_cells, mode)
    output.write_record(run_dir / "outcome.json", analysis.outcome_record(outcome))
    return outcome


def stage_report(run_dir: Path) -> str:
    rec = read_json(run_dir / "outcome.json")
    outcome = rec["outcome"]
    gp = run_dir / "gates.json"
    overlap = read_json(gp).get("replicate_overlap", {}) if gp.exists() else {}
    extra = [report.overlap_line(overlap)] if overlap else []
    text = report.render_report(outcome, extra=extra)
    output.write_text(run_dir / "REPORT.md", text)
    output.emit(report.summary_lines(outcome))
    return text


# --- the dry stage ------------------------------------------------------------------------------------------------------------------------------
def dry(run_dir: Path, replicates: int = 2, updates: int | None = None, gates_updates: int = 3) -> dict[str, Any]:
    """Tiny synthetic end to end on stand-ins and test seeds. Every number is a mechanics check, not a result."""
    core.reset_seed_record()
    ledger = Ledger(run_dir / "ledger.jsonl")
    with ledger.charge("datagen", process="dry: synthetic data generation and partition"):
        bundle, pre = standins.build_synthetic_bundle(replicates)
        bundle.extra["equivalence"] = _dry_equivalence(bundle, RunConfig.dry(updates).layer)  # what the data-generation step records against its reference
        data_dir = run_dir / "data"
        write_bundle(bundle, data_dir)
        bundle = read_bundle(data_dir)  # hash-checked load
        world = build_world(bundle, "test", replicates, RunConfig.dry(updates))
    plan0 = core.SeedPlan("test", 0)
    streams_g1, g3 = gate_inputs(world, pre)
    with ledger.charge("gates-rehearsal", process="dry: gates"):
        g = stage_gates(world, run_dir, plan0, g1=streams_g1, g3=g3, equivalence_record=bundle.extra["equivalence"], file_manifest=_manifest_of(data_dir), root=data_dir, updates=gates_updates)
    with ledger.charge("train", process="dry: training"):
        stage_train(world, run_dir)
    with ledger.charge("evaluate", process="dry: scoring"):
        stage_evaluate(world, run_dir)
    with ledger.charge("timing", process="dry: timing benchmark"):
        stage_timing(world, run_dir, items=3)
    with ledger.charge("recompute", process="dry: independent recomputation"):
        stage_recompute(world, run_dir)
    design = {"replicates": replicates, "updates": world.updates, "synthetic": True}
    prefreeze = prefreeze_summary(pre)
    with ledger.charge("analysis", process="dry: analysis"):
        outcome = stage_analysis(run_dir, design, prefreeze)
    with ledger.charge("report", process="dry: report"):
        stage_report(run_dir)
    core_record = {"seeds": core.seed_gate(core.seed_record(), planned_mode="test"), "ledger": ledger.summary(core.CFG["budget"]["cap_hours"])}
    record(run_dir / "run_record.json", {"gates_ok": g["ok"], **core_record})
    return {"gates": g, "outcome": outcome, "run_record": core_record}


def _manifest_of(directory: Path) -> dict[str, dict[str, str]]:
    return {n: {"algo": "sha256", "digest": file_sha256(directory / n)} for n in sorted(p.name for p in directory.iterdir() if p.is_file() and p.name != "manifest.json")}


def _dry_equivalence(bundle: DataBundle, layer: int) -> dict[str, Any]:
    """A reference stand-in written independently of the student (explicit loops, Hugging Face naming) records the equivalence result, as the data-generation step would with the real reference."""
    from .equivalence import build_record
    from .model import build_student, export_hf_state_dict, load_plain_state
    from .reference_standin import ReferenceLlama

    student = build_student(bundle.cfg)
    load_plain_state(student, bundle.student_state)
    ref = ReferenceLlama(bundle.cfg, export_hf_state_dict(student))
    g = core.seeded_generator(core.SEEDS["test_low"] + 700, "dry equivalence text", "test")
    ids = torch.randint(0, bundle.cfg.vocab, (1, 32), generator=g)
    vec = torch.randn(bundle.cfg.width, generator=g)
    prompts = [[int(x) for x in torch.randint(0, bundle.cfg.vocab, (6,), generator=g).tolist()] for _ in range(3)]
    return build_record(student, ref, ids, vec, layer, prompts, 5)


# --- registered stages ---------------------------------------------------------------------------------------------------------------------------
def load_plan(repo: Path) -> dict[str, Any]:
    return freeze.load_plan(repo)


def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name, with everything else from the frozen plan and the frozen cap table. The only free arguments are the run directory and the freeze commit."""
    if args.name not in REGISTERED_STAGES:
        raise StageRefused(f"unknown registered stage {args.name!r}; the stages are {', '.join(REGISTERED_STAGES)}")
    repo = Path(args.repo).resolve() if args.repo else core.ROOT
    run_dir = Path(args.run_dir).resolve()
    try:
        freeze.check_preconditions(repo, args.freeze_commit)
        plan = freeze.load_plan(repo)
        freeze.verify_plan(plan, repo, run_dir)
        caps = json.loads((repo / args.caps).read_text()) if args.caps else json.loads((repo / core.CAPS_FILE).read_text())
        n, u = int(plan["design"]["replicates"]), int(plan["design"]["updates"])
        cap_seconds = budget.cap_for(caps, args.name, n, u)
        ledger = Ledger(run_dir / "ledger.jsonl")
        cap_hours = budget.effective_cap(repo / core.RAISE_FILE)
        ledger.refuse_if_over(cap_seconds / 3600.0, cap_hours, f"stage {args.name}")
    except (freeze.FreezeRefused, budget.CapMissing, LedgerRefused, budget.CapRefused, StageRefused) as e:
        output.emit_plain(str(e), sys.stderr)
        return 2
    deadline = Deadline(cap_seconds)
    design = {"replicates": n, "updates": u}
    prefreeze = dict(plan.get("prefreeze", {}))
    pre_record = json.loads((repo / plan["prefreeze_record"]["path"]).read_text())
    needs_world = args.name in ("gates", "train", "evaluate", "timing", "recompute")
    if needs_world:
        run = RunConfig.registered(int(plan["design"]["layer"]), u, float(plan["design"]["store_lr"]), float(plan["design"]["lora_lr"]))
        bundle = read_bundle(repo / plan["data_dir"])
        world = build_world(bundle, "registered-run", n, run)
    stage_fn: dict[str, Callable[[], Any]] = {
        "gates": lambda: stage_gates(world, run_dir, core.SeedPlan("registered-run", 0), g1=gate_inputs(world, pre_record)[0], g3=gate_inputs(world, pre_record)[1], equivalence_record=bundle.extra.get("equivalence"), file_manifest=_manifest_of(repo / plan["data_dir"]), root=repo / plan["data_dir"]),
        "train": lambda: stage_train(world, run_dir, deadline),
        "evaluate": lambda: stage_evaluate(world, run_dir, deadline),
        "timing": lambda: stage_timing(world, run_dir),
        "recompute": lambda: stage_recompute(world, run_dir, deadline),
        "analysis": lambda: stage_analysis(run_dir, design, prefreeze),
        "report": lambda: stage_report(run_dir),
    }
    kind = {"gates": "gates-registered", "train": "train", "evaluate": "evaluate", "timing": "timing", "recompute": "recompute", "analysis": "analysis", "report": "report"}[args.name]
    with ledger.charge(kind, process=f"registered {args.name}", registered=args.name in ("gates", "train", "evaluate", "timing", "recompute")):
        stage_fn[args.name]()
    return 0


def cmd_dry(args: argparse.Namespace) -> int:
    out = dry(Path(args.run_dir), replicates=args.replicates, updates=args.updates)
    output.emit_plain(f"dry stage complete: gates ok = {out['gates']['ok']}; outputs in {args.run_dir}")
    return 0 if out["gates"]["ok"] else 1


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Calibration and the pilot gate (section 12.1, 12.2) on the frozen data files and calibration seeds. Not run in this implementation step."""
    from . import calibration

    repo = Path(args.repo).resolve() if args.repo else core.ROOT
    try:
        freeze.check_code_commit(repo, args.code_commit)
    except freeze.FreezeRefused as e:
        output.emit_plain(str(e), sys.stderr)
        return 2
    run_dir = Path(args.run_dir).resolve()
    ledger = Ledger(run_dir / "ledger.jsonl")
    bundle = read_bundle(Path(args.data_dir))
    world = build_world(bundle, "calibration", 1, RunConfig.registered(core.READ_LAYERS[0], int(args.updates), core.CFG["training"]["store_learning_rate"], core.CFG["training"]["lora_learning_rates"][0], args.device))
    with ledger.charge("calibration", process="calibration and pilot"):
        rec = calibration.run_calibration(world, 0, updates=int(args.updates))
    record(run_dir / "calibration.json", rec)
    output.emit_plain(f"calibration record written to {run_dir / 'calibration.json'}")
    return 0 if rec["pilot"]["ok"] else 3


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The rehearsal (section 13.3): the rates, the headroom check and the rung rule's decision. Not run in this implementation step."""
    from . import rehearsal

    repo = Path(args.repo).resolve() if args.repo else core.ROOT
    try:
        freeze.check_code_commit(repo, args.code_commit)
    except freeze.FreezeRefused as e:
        output.emit_plain(str(e), sys.stderr)
        return 2
    run_dir = Path(args.run_dir).resolve()
    ledger = Ledger(run_dir / "ledger.jsonl")
    bundle = read_bundle(Path(args.data_dir))
    world = build_world(bundle, "rehearsal", 1, RunConfig.registered(int(args.layer), int(args.updates), core.CFG["training"]["store_learning_rate"], core.CFG["training"]["lora_learning_rates"][0], args.device))
    with ledger.charge("rehearsal", process="rehearsal"):
        overhead = rehearsal.measure_task_overhead(Path(args.data_dir), repo)
        rates, raw = rehearsal.measure_rates(world, 0, updates=int(args.updates), full_updates=int(args.full_updates), overhead=overhead)
    record(run_dir / "rates.json", rates.to_json())
    check = budget.headroom_check(ledger.total_hours(), rates, ledger, repo / core.RAISE_FILE)
    record(run_dir / "rehearsal.json", {"raw": raw, "headroom_check": check})
    output.emit_plain(f"rehearsal record written to {run_dir / 'rehearsal.json'}; rung rule outcome: {check['decision']['outcome']}")
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve() if args.repo else core.ROOT
    rates = budget.Rates.from_json(read_json(Path(args.rates)))
    ledger = Ledger(Path(args.ledger))
    rec = freeze.write_freeze(repo, rates=rates, ledger=ledger, run_dir=Path(args.run_dir), data_dir=args.data_dir, calibration=Path(args.calibration), prefreeze=Path(args.prefreeze), design_layer=args.layer, store_lr=args.store_lr, lora_lr=args.lora_lr)
    output.emit_plain(f"freeze files written: {', '.join(rec['written'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.stages", description="P10S2 stage drivers (ADR-0022 revision 5). Implementation on synthetic stand-ins only.")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dry", help="tiny synthetic end-to-end (stand-ins, test seeds; not a calibration, rehearsal or registered stage)")
    d.add_argument("--run-dir", required=True)
    d.add_argument("--replicates", type=int, default=2)
    d.add_argument("--updates", type=int, default=None)
    d.set_defaults(func=cmd_dry)
    r = sub.add_parser("registered", help="one registered stage by name, from the frozen plan")
    r.add_argument("name", choices=REGISTERED_STAGES)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--freeze-commit", required=True)
    r.add_argument("--caps", required=True, help="the frozen stage-cap table (every launch script passes it)")
    r.add_argument("--repo", default=None)
    r.set_defaults(func=cmd_registered)
    for name, fn, hlp in (("calibrate", cmd_calibrate, "calibration and the pilot gate on calibration seeds (pre-freeze; not run here)"), ("rehearse", cmd_rehearse, "the rehearsal: rates, headroom check, rung rule (pre-freeze; not run here)")):
        c = sub.add_parser(name, help=hlp)
        c.add_argument("--run-dir", required=True)
        c.add_argument("--code-commit", required=True, help="must equal a clean HEAD")
        c.add_argument("--stage-cap-seconds", type=float, required=True, help="the stage cap (seconds); every launch script passes it")
        c.add_argument("--data-dir", required=True)
        c.add_argument("--updates", type=int, required=True)
        if name == "rehearse":
            c.add_argument("--full-updates", type=int, required=True, help="U for the full-length store, M-ii and LoRA rehearsal cells (the ADR's rehearsal content)")
        c.add_argument("--device", default="auto")
        c.add_argument("--layer", type=int, default=None, help="the calibrated read layer (default: from the calibration record in the run directory)")
        c.add_argument("--repo", default=None)
        c.set_defaults(func=fn)
    f = sub.add_parser("freeze", help="write the frozen plan and cap files from a rehearsal record (the freeze procedure)")
    f.add_argument("--rates", required=True)
    f.add_argument("--ledger", required=True)
    f.add_argument("--run-dir", required=True)
    f.add_argument("--data-dir", required=True)
    f.add_argument("--calibration", required=True)
    f.add_argument("--prefreeze", required=True)
    f.add_argument("--layer", type=int, required=True)
    f.add_argument("--store-lr", type=float, required=True)
    f.add_argument("--lora-lr", type=float, required=True)
    f.add_argument("--repo", default=None)
    f.set_defaults(func=cmd_freeze)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code = args.func(args)
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "dry", "build_parser", "DataBundle", "registry"]
