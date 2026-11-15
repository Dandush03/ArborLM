# ruff: noqa: E501
"""Training and scoring of the cells of a replicate (ADR-0022 sections 6, 7, 13.1).

Training writes immutable snapshots (``world.save_arm``); scoring loads them, so every score can be recomputed independently from the snapshots (section 13.3). The two stages are separate
functions: ``train_replicate`` (training device from the world, MPS in the registered run) and ``score_replicate`` (CPU only).

Seeds (section 9; every use starts a fresh generator): +0 initializes ST1 of both orders and MA-gold of both capabilities; +6 the appended rows of both orders (keys, then values); +7 M-joint; +8
LoRA-1 of both orders and, with its own shapes, L-joint; +9 E-table of both capabilities; +2 orders the batches of every stream (a fresh generator per cell and stream, so cells on the same data
share their order) and, separately, M-ii's replayed rows; +3 the routers.
"""

import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from . import combined as combined_mod
from . import core, evaluate, retrieval
from .evaluate import (
    PanelData,
    general_by_construction,
    general_quality,
    memory_ablations,
    score_panel,
)
from .memory import (
    Arm,
    LoRAArm,
    MemoryArm,
    NullArm,
    Read,
    SparseStore,
    TableArm,
    new_lora_arm,
    row_shares,
)
from .registry import Cell, replicate_cells
from .routing import Router, false_triggers, none_pieces, route_accuracy, train_router
from .text import chrf_item, mean, normalize
from .train import NonFiniteLoss, TrainRecord, reads_of, train_arm
from .world import World, load_arm, save_arm

TWO = ("A", "B")


# --- training ---------------------------------------------------------------------------------------------------------------------------------------
def _train(world: World, r: int, arm: Arm, examples: Sequence[Any], updates: int, lr: float, **kw: Any) -> TrainRecord:
    plan = world.plan(r)
    return train_arm(world.student, arm, examples, updates, world.batch, lr, plan.gen(2, "batch order"), world.marker_index, device=world.device, **kw)


def _mem(arms: Mapping[str, Arm], label: str) -> MemoryArm:
    a = arms[label]
    assert isinstance(a, MemoryArm)
    return a


def train_replicate(world: World, r: int, snap_dir: Path, only: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """Train the 18 cells of replicate ``r`` in dependency order. A failed cell (non-finite loss) keeps its record and stops the cells that depend on it (their status is ``skipped_dependency``).
    Returns ``{label: {status, train, snapshots}}``."""
    plan = world.plan(r)
    u, n = world.updates, world.rows_per_stage
    width = world.cfg.width
    codes = world.codes(r)
    arms: dict[str, Arm] = {}
    records: dict[str, dict[str, Any]] = {}

    def done(cell: Cell, arm: Arm, rec: TrainRecord, extra: Mapping[str, Any] | None = None) -> None:
        snaps = {cell.label: save_arm(arm, snap_dir, cell.label)} if rec.status == "completed" else {}
        records[cell.label] = {"label": cell.label, "status": rec.status, "train": [rec.to_json()], "snapshots": snaps, **(dict(extra) if extra else {})}
        if rec.status == "completed":
            arms[cell.label] = arm

    arm: Arm
    for cell in replicate_cells(r):
        if only is not None and cell.label not in only:
            continue
        parent = cell.depends_on
        if parent is not None and parent not in arms:
            records[cell.label] = {"label": cell.label, "status": "skipped_dependency", "train": [], "snapshots": {}, "depends_on": parent}
            continue
        g, v = cell.group, cell.variant
        first, second = (v[0], v[1]) if len(v) == 2 else ("", "")
        if g == "ST1":
            arm = MemoryArm(SparseStore.new(width, n, plan.gen(0, "stage-1 store")), world.layer, codes)
            done(cell, arm, _train(world, r, arm, world.train_examples(r, first), u, world.store_lr))
        elif g == "MAF":
            store = _mem(arms, parent or "").store.clone()
            store.append_stage(n, plan.gen(6, "stage-2 appended rows"))
            store.freeze_stage(0)
            store.set_trainable([1])
            arm = MemoryArm(store, world.layer, codes)
            append_manifest = save_arm(arm, snap_dir, f"{cell.label}@append")  # the append point, scored before any update
            rec = _train(world, r, arm, world.train_examples(r, second), u, world.store_lr)
            done(cell, arm, rec, {"append_snapshot": append_manifest})
        elif g == "MII":
            store = _mem(arms, parent or "").store.clone()
            store.set_trainable([0, 1])
            arm = MemoryArm(store, world.layer, codes)
            rec = _train(world, r, arm, world.train_examples(r, second), u, world.store_lr, replay=world.train_examples(r, first), replay_rows=world.replay_rows, replay_generator=plan.gen(2, "M-ii replayed rows order"))
            done(cell, arm, rec)
        elif g == "MSEQ":
            store = _mem(arms, parent or "").store.clone()
            store.set_trainable([0])
            arm = MemoryArm(store, world.layer, codes)
            done(cell, arm, _train(world, r, arm, world.train_examples(r, second), u, world.store_lr))
        elif g == "LORA1":
            arm = new_lora_arm(world.cfg, world.rank_single, plan.gen(8, "LoRA initialization"))
            done(cell, arm, _train(world, r, arm, world.train_examples(r, first), u, world.lora_lr))
        elif g == "LSEQ":
            arm = copy.deepcopy(arms[parent or ""])
            done(cell, arm, _train(world, r, arm, world.train_examples(r, second), u, world.lora_lr))
        elif g == "MJOINT":
            arm = MemoryArm(SparseStore.new(width, 2 * n, plan.gen(7, "M-joint store")), world.layer, codes)
            mixed = [*world.train_examples(r, "A"), *world.train_examples(r, "B")]
            done(cell, arm, _train(world, r, arm, mixed, 2 * u, world.store_lr))
        elif g == "LJOINT":
            arm = new_lora_arm(world.cfg, world.rank_joint, plan.gen(8, "LoRA initialization (L-joint shapes)"))
            mixed = [*world.train_examples(r, "A"), *world.train_examples(r, "B")]
            done(cell, arm, _train(world, r, arm, mixed, 2 * u, world.lora_lr))
        elif g == "ETABLE":
            arm = TableArm(v, width, world.vocabulary, world.layer, plan.gen(9, "E-table initialization"))
            done(cell, arm, _train(world, r, arm, world.train_examples(r, v), u, world.store_lr))
        elif g == "MAGOLD":
            arm = MemoryArm(SparseStore.new(width, n, plan.gen(0, "stage-1 store (MA-gold)")), world.layer, codes)
            done(cell, arm, _train(world, r, arm, world.gold_examples(r, v), u, world.store_lr))
        else:  # pragma: no cover
            raise ValueError(g)
    return records


# --- composites assembled without training ------------------------------------------------------------------------------------------------------------
class CompositeStoreArm(Arm):
    """M-i-separate: two stores behind the oracle route. Reads of task t go to task t's store (the ST1 store of that capability); one top-8 inside each store."""

    kind = "memory"

    def __init__(self, arms: Mapping[str, MemoryArm]) -> None:
        self.arms = dict(arms)
        self.layer = next(iter(self.arms.values())).layer

    def prepare(self, reads: Sequence[Sequence[Read]], batch: int, length: int, device: torch.device, ablation: Any = None) -> tuple[torch.Tensor | None, Any]:
        total: torch.Tensor | None = None
        for t, a in self.arms.items():
            sub = [[x for x in rs if x[1] == t] for rs in reads]
            add, _ = a.prepare(sub, batch, length, device, ablation)
            if add is not None:
                total = add if total is None else total + add
        return total, None


class AdapterRouteArm(Arm):
    """L-sep: the two LoRA-1 adapters of a replicate behind the oracle route; the adapter of the task of the reads is applied."""

    kind = "lora"

    def __init__(self, arms: Mapping[str, LoRAArm]) -> None:
        self.arms = dict(arms)

    def prepare(self, reads: Sequence[Sequence[Read]], batch: int, length: int, device: torch.device, ablation: Any = None) -> tuple[torch.Tensor | None, Any]:
        tasks = {x[1] for rs in reads for x in rs}
        if len(tasks) != 1:
            return None, None
        return None, self.arms[next(iter(tasks))].adapter


# --- scoring ----------------------------------------------------------------------------------------------------------------------------------------
def build_routers(world: World, r: int) -> dict[tuple[str, ...], tuple[Router, dict[str, Any]]]:
    """One router per (replicate, set of tasks): {A}, {B} and {A, B} (the router depends on the replicate and the tasks, not on the arm), each trained from a fresh +3 generator."""
    out: dict[tuple[str, ...], tuple[Router, dict[str, Any]]] = {}
    for tasks in (("A",), ("B",), TWO):
        prompts = {t: [world.bank.prompt(t, x.en) for x in world.streams[r].t[t]] for t in tasks}
        out[tasks] = train_router(world.student, world.layer, tasks, prompts, world.wiki_train_ids, world.plan(r), world.router_spec)
    return out


def gap_panels(ctx: Any) -> list[str]:
    """The panels that enter a gap, an ablation or a learned-route score: E_A and E_B (any other panel, E_open, is descriptive only and scored under the oracle route alone)."""
    return [n for n in ctx.panels if not n.startswith("E_open")]


def _reads_per_item(panel: PanelData) -> float:
    return sum(len(reads_of(e, [e.task], 10**9)) for e in panel.examples) / max(1, len(panel.examples))


def _generated_per_item(scores: Mapping[str, Any]) -> float:
    seqs = scores["sequences"]
    return sum(len(s) for s in seqs) / max(1, len(seqs))


def score_snapshot(
    world: World,
    r: int,
    arm: Arm,
    *,
    router: Router | None,
    ablation_stages: Sequence[int] | None,
    ablation_tasks: Sequence[str],
    gen: bool,
    always_on: str | None = None,
    learned_route: bool = False,
    combined: bool = False,
    seen: bool = False,
) -> dict[str, Any]:
    """One snapshot's scores. Sections are present only where the ADR scores them for that cell type (section 6.4, 7)."""
    ctx = world.ctx
    ctx.seed_plan = world.plan(r)
    out: dict[str, Any] = {"arm_hash": arm.state_hash(), "parameters": arm.parameter_count()}
    panels = {name: score_panel(ctx, arm, p) for name, p in ctx.panels.items()}
    out["panels"] = {k: v.to_json() for k, v in panels.items()}
    first_name = next(iter(ctx.panels))
    out["work"] = evaluate.active_work(arm, _reads_per_item(ctx.panels[first_name]), _generated_per_item(panels[first_name].to_json()))
    if ablation_stages is not None and isinstance(arm, MemoryArm):
        out["ablations"] = memory_ablations(ctx, arm, gap_panels(ctx), ablation_stages, ablation_tasks)
    if learned_route and router is not None:
        out["learned_route"] = {name: score_panel(ctx, arm, ctx.panels[name], route="learned", router=router).to_json() for name in gap_panels(ctx)}
    if gen and router is not None:
        out["gen"] = general_quality(ctx, arm, router, always_on_task=always_on)
        out["gen_by_construction"] = general_by_construction(ctx, arm)
    if combined:
        out["combined"] = combined_mod.score_combined_cell(ctx, arm, ctx.ec)  # C1, C2 and the single-task E_C answers: oracle route only, no router lane, no ablation
    if seen:
        out["seen"] = {c: score_panel(ctx, arm, PanelData(f"seen_{c}", c, [world.bank.prompt(c, x.en) for x in world.seen_items[r][c]], [[x.target] for x in world.seen_items[r][c]])).to_json() for c in TWO}
    return out


def stage0_scores_without_combined(world: World) -> dict[str, Any]:
    """Stage 0 and the stored teacher scores on the single-task panels (the rehearsal times its combined scoring separately)."""
    res = stage0_scores(world, with_combined=False)
    return res


def stage0_scores(world: World, with_combined: bool = True) -> dict[str, Any]:
    """Stage 0: the untrained student on every panel and on the 300-item subsample; and the stored teacher outputs scored on the same panels (the teachers are not run here)."""
    ctx = world.ctx
    arm = NullArm()
    res: dict[str, Any] = {"student": {}, "teacher": {}}
    for name, p in ctx.panels.items():
        sc = score_panel(ctx, arm, p, route="none")
        if name not in ctx.subsample:  # E_open: descriptive only, no subsample and no gap; the teacher of the panel's capability is scored on the items that carry a reference in its language
            res["student"][name] = {"panel": sc.to_json()}
            oo = world.teacher_outputs.get(p.task, {}).get("E_open")
            if oo is not None and p.source_index is not None:
                outs_o = [oo[i] for i in p.source_index]
                items_o = [chrf_item(o, rf) for o, rf in zip(outs_o, p.refs, strict=True)]
                res["teacher"][name] = {"mean": mean(items_o), "items": items_o, "exact_rate": mean([float(normalize(o) in {normalize(x) for x in rf}) for o, rf in zip(outs_o, p.refs, strict=True)])}
            continue
        sub = score_panel(ctx, arm, p, route="none", indices=ctx.subsample[name])
        res["student"][name] = {"panel": sc.to_json(), "subsample": sub.to_json()}
        outs = world.teacher_outputs.get(p.task, {}).get(name)
        if outs is not None:
            items = [chrf_item(o, rf) for o, rf in zip(outs, p.refs, strict=True)]
            exact = [normalize(o) in {normalize(x) for x in rf} for o, rf in zip(outs, p.refs, strict=True)]
            res["teacher"][name] = {"mean": mean(items), "items": items, "subsample_mean": mean([items[i] for i in ctx.subsample[name]]), "exact_rate": mean([float(e) for e in exact])}
    if not with_combined:
        return res
    # the combined tasks (addendum section 7): Stage 0 on the layouts with no read (the floor of the rule), and the ensemble from the stored teacher outputs on E_C (both teachers generate on every E_C sentence)
    ec_text = {c: world.teacher_outputs.get(c, {}).get("E_C") for c in TWO}
    res["combined"] = {"stage0": combined_mod.score_combined_cell(ctx, arm, ctx.ec), "ensemble": combined_mod.ensemble_record(ctx.ec, ec_text) if all(v is not None for v in ec_text.values()) else None}  # type: ignore[arg-type]
    return res


def score_replicate(world: World, r: int, snap_dir: Path, train_records: Mapping[str, Mapping[str, Any]], routers: Mapping[tuple[str, ...], tuple[Router, dict[str, Any]]] | None = None) -> dict[str, dict[str, Any]]:
    """Score every completed cell of replicate ``r`` from its snapshots (CPU). Returns ``{label: record}`` with the training record, the scores per snapshot and the cell's extras."""
    routers = routers if routers is not None else build_routers(world, r)
    out: dict[str, dict[str, Any]] = {}
    arms: dict[str, Arm] = {}

    def load(label: str) -> Arm:
        if label not in arms:
            arms[label] = load_arm(world, r, snap_dir, label)
        return arms[label]

    for cell in replicate_cells(r):
        rec = dict(train_records.get(cell.label, {"label": cell.label, "status": "missing", "train": [], "snapshots": {}}))
        if rec["status"] != "completed":
            out[cell.label] = rec
            continue
        g, v = cell.group, cell.variant
        first, second = (v[0], v[1]) if len(v) == 2 else ("", "")
        arm = load(cell.label)
        one = routers[(first,)][0] if first else None
        both = routers[TWO][0]
        scores: dict[str, Any] = {}
        extras: dict[str, Any] = {}
        if g == "ST1":
            scores[cell.label] = score_snapshot(world, r, arm, router=one, ablation_stages=[0], ablation_tasks=TWO, gen=True, learned_route=True, seen=True)
        elif g == "MAF":
            scores[cell.label] = score_snapshot(world, r, arm, router=both, ablation_stages=[1], ablation_tasks=[second], gen=True, always_on=first, learned_route=True, combined=True, seen=True)
            ap = load_arm(world, r, snap_dir, f"{cell.label}@append")
            scores[f"{cell.label}@append"] = score_snapshot(world, r, ap, router=None, ablation_stages=None, ablation_tasks=(), gen=False)
            st1 = load(f"r{r}/ST1/{v}")
            n1 = st1.store.rows  # type: ignore[attr-defined]
            q = torch.stack([world.codes(r).get(first, j) for e in world.ctx.panels["E_" + first].examples for _p, j in e.reads] or [world.codes(r).get(first, 0)])
            extras["append"] = {"first_stage_rows": n1, "interference": row_shares(ap.store, q, n1), "stage0_hash_equals_v1": _stage_hash(ap, 0) == _stage_hash(st1, 0) == _stage_hash(arm, 0)}  # type: ignore[attr-defined]
        elif g == "MII":
            scores[cell.label] = score_snapshot(world, r, arm, router=both, ablation_stages=[1], ablation_tasks=[second], gen=True, combined=True)
            maf = load(f"r{r}/MAF/{v}")
            extras["consolidation"] = _consolidation(world, r, maf, arm)
        elif g == "MSEQ":
            scores[cell.label] = score_snapshot(world, r, arm, router=both, ablation_stages=[0], ablation_tasks=TWO, gen=True)
        elif g == "MJOINT":
            scores[cell.label] = score_snapshot(world, r, arm, router=both, ablation_stages=[0], ablation_tasks=TWO, gen=True, combined=True)
        elif g == "MAGOLD":
            scores[cell.label] = score_snapshot(world, r, arm, router=None, ablation_stages=[0], ablation_tasks=TWO, gen=False)
        elif g == "LORA1":
            scores[cell.label] = score_snapshot(world, r, arm, router=None, ablation_stages=None, ablation_tasks=(), gen=False)
        elif g == "LSEQ":
            scores[cell.label] = score_snapshot(world, r, arm, router=both, ablation_stages=None, ablation_tasks=(), gen=True, always_on=first, combined=True)
        elif g == "LJOINT":
            scores[cell.label] = score_snapshot(world, r, arm, router=None, ablation_stages=None, ablation_tasks=(), gen=False, combined=True)
        elif g == "ETABLE":
            scores[cell.label] = score_snapshot(world, r, arm, router=None, ablation_stages=None, ablation_tasks=(), gen=False)
        rec["scores"] = scores
        rec["extras"] = extras
        out[cell.label] = rec
    return out


def _stage_hash(arm: Arm, stage: int) -> str:
    assert isinstance(arm, MemoryArm)
    return core.digest([arm.store.keys[stage].detach().tolist(), arm.store.values[stage].detach().tolist(), arm.store.gates[stage].detach().tolist()])


def _consolidation(world: World, r: int, maf: Arm, mii: Arm) -> dict[str, Any]:
    """M-ii's acceptance and modification statistics. Hard constraint: the new version is published only if, on D_con, chrF on each capability is at least M-append-frozen's minus 0.02;
    otherwise CONSOLIDATION-REJECTED. Modification floor: ||V1(after) - V1(before)|| / ||V1(before)|| over the first stage's value rows (>= 0.10); the share of first-stage rows that changed at all and
    the change of the first-stage gate g_1 are reported."""
    assert isinstance(maf, MemoryArm) and isinstance(mii, MemoryArm)
    ctx = world.ctx
    ctx.seed_plan = world.plan(r)
    d: dict[str, Any] = {}
    ok = True
    margin = core.CFG["training"]["retention_check_drop"]
    for c in TWO:
        p = world.d_con[c]
        s_maf = score_panel(ctx, maf, p).mean
        s_mii = score_panel(ctx, mii, p).mean
        d[c] = {"maf": s_maf, "mii": s_mii}
        ok = ok and s_mii >= s_maf - margin
    before, after = maf.store.values[0].detach(), mii.store.values[0].detach()
    ratio = float((after - before).norm() / before.norm().clamp_min(1e-30))
    changed = float(((after != before).any(dim=1)).float().mean())
    floor = core.CFG["training"]["modification_floor"]
    return {"d_con": d, "rejected": not ok, "relative_change": ratio, "changed_row_share": changed, "g1_change": float(mii.store.gates[0].item() - maf.store.gates[0].item()), "below_floor": ratio < floor, "published": ok, "pinned_version": "stage-2 snapshot of M-ii" if ok else "M-append-frozen's snapshot (the pinned version stays)", "scored_on": "selected on D_con, then confirmed on E"}


def assembled_scores(world: World, r: int, snap_dir: Path) -> dict[str, Any]:
    """M-i-separate (two ST1 stores behind the oracle route) and L-sep (the two LoRA-1 adapters behind the oracle route), assembled from the replicate's snapshots, never trained. Printed BY CONSTRUCTION; no
    class and no label. Their combined-task scores follow the combined-tasks addendum (L-sep: position-wise adapters on C1, a switch per answer on C2)."""
    ctx = world.ctx
    ctx.seed_plan = world.plan(r)
    st = {c: load_arm(world, r, snap_dir, f"r{r}/ST1/{c}{core.other_task(c)}") for c in TWO}
    lo = {c: load_arm(world, r, snap_dir, f"r{r}/LORA1/{c}{core.other_task(c)}") for c in TWO}
    msep = CompositeStoreArm({c: st[c] for c in TWO})  # type: ignore[misc]
    lsep = AdapterRouteArm({c: lo[c] for c in TWO})  # type: ignore[misc]
    out: dict[str, Any] = {"label": "BY CONSTRUCTION"}
    for name, arm in (("M-i-separate", msep), ("L-sep", lsep)):
        out[name] = {n: score_panel(ctx, arm, p).to_json() for n, p in ctx.panels.items()}
        out[name]["combined"] = combined_mod.score_combined_cell(ctx, arm, ctx.ec)
    return out


def _leading_bos(ex: Any) -> int:
    """The length of the stored BOS segment of an example (0 if the tokenizer does not prepend one)."""
    return len(ex.segments[0].ids) if ex.segments and ex.segments[0].text == "<bos>" else 0


def icl_ids(demos: Sequence[Any], query: Any) -> list[int]:
    """The R-icl prompt: the demonstrations (nearest last) then the query prompt, with a BOS token only once at the start if the tokenizer prepends one (never before every demonstration)."""
    ids: list[int] = []
    for k, d in enumerate(demos):
        ids += list(d.ids)[0 if k == 0 else _leading_bos(d) :]
    ids += list(query.prompt_ids)[_leading_bos(query) if demos else 0 :]
    return ids


def retrieval_scores(world: World, r: int) -> dict[str, Any]:
    """The four retrieval baselines on E_A and E_B from the replicate's accepted pairs; R-icl is scored with the frozen student (its prompt carries the 4 nearest pairs)."""
    ctx = world.ctx
    out: dict[str, Any] = {}
    for c in TWO:
        train = world.streams[r].t[c]
        panel_items = [i for i in world.partition.panels["E_" + c]]
        idx = retrieval.TfidfIndex(train)
        icl_scores: list[float] = []
        prompt_tokens = []
        for it, ex in zip(panel_items, ctx.panels["E_" + c].examples, strict=True):
            demos = retrieval.r_icl_prompt_items(train, it.en, 4, idx)
            ids = icl_ids([world.bank.train(c, dm) for dm in demos], ex)
            prompt_tokens.append(len(ids))
            seq = ctx.student.greedy(torch.tensor([ids]), add=None, adapter=None, max_new=ctx.max_new, stop_bytes=ctx.decoder.table)
            icl_scores.append(chrf_item(ctx.decoder.answer_text(seq), ctx.panels["E_" + c].refs[len(icl_scores)]))
        out[c] = {"R-exact": retrieval.r_exact(train, panel_items, c), "R-nn": retrieval.r_nn(train, panel_items, c, idx), "R-gloss": retrieval.r_gloss(train, panel_items, c), "R-icl": {"mean": mean(icl_scores), "items": icl_scores, "prompt_tokens_mean": mean([float(x) for x in prompt_tokens])}}
    return out


def router_record(world: World, r: int, routers: Mapping[tuple[str, ...], tuple[Router, dict[str, Any]]]) -> dict[str, Any]:
    """For each router: its training record, its route accuracy on E_A, E_B and on general prefixes, and the false-trigger diagnostic on the marker-like windows (decision at the last token of the first
    marker-like string within tokens 1-64; it enters no rule). The general prefixes are 64-token pieces of the WikiText-2 train file that the router did not see in training (never the GEN windows: the
    GEN panel is used for nothing else, section 6.4); this is a reading, reported to the lead."""
    ctx = world.ctx
    pieces = none_pieces(world.wiki_train_ids, world.router_spec.prefix_tokens)
    marker = [w for w in ctx.windows if w.stratum == "marker" and w.marker_end >= 0]
    out: dict[str, Any] = {}
    for tasks, (router, rec) in routers.items():
        prefixes = [pieces[i] for i in rec.get("held_out_piece_indices", [])]
        acc = route_accuracy(router, ctx.student, ctx.router_layer, {c: ctx.panels["E_" + c].examples for c in TWO}, prefixes)
        diag = false_triggers(router, ctx.student, ctx.router_layer, [w.ids for w in marker], [w.marker_end for w in marker])
        out["".join(tasks)] = {"training": rec, "accuracy": acc, "general_prefixes": {"source": "WikiText-2 train pieces not used in the router's training", "n": len(prefixes)}, "diagnostic_first_marker": {k: v for k, v in diag.items() if k != "predictions"}}
    return out


__all__ = ["NonFiniteLoss", "train_replicate", "score_replicate", "score_snapshot", "build_routers", "stage0_scores", "assembled_scores", "retrieval_scores", "router_record"]
