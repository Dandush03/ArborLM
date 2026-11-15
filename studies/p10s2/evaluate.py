# ruff: noqa: E501
"""Scoring of a snapshot (ADR-0022 sections 6.4, 7, 10): panels under the oracle route, under a learned route, ablations on the 300-item subsample, the combined tasks, general-language
quality (GEN, always-on), seen items, and the work counts. Everything runs on CPU, one item at a time (a fixed composition: scores do not depend on the worker), greedy decoding with a
key-value cache, stop at the first newline byte. A scoring is a pure function of (student weights, arm state, panel records): it is repeated bit-identically (gate G4) and recomputed
independently (section 13.3).

Combined tasks: how C1 pairs two sources and how C2 lays out its prompt are not specified by the ADR. They are implemented behind ``core.CFG["pending"]["combined_tasks_defined"]`` and, when
that is false, ``score_combined`` raises ``PendingLeadReview``; a provisional layout (marked PROVISIONAL in every record) runs only when the caller says so explicitly (tests and the dry stage).
"""

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import torch
from torch.nn import functional as F

from . import core
from .memory import Ablation, Arm, MemoryArm, NullArm, Read, make_ablation, run_student
from .model import Student
from .routing import Router, hidden_at_ends
from .text import chrf_item, mean, normalize
from .tokenization import ByteDecoder, Example
from .train import reads_of

CPU = torch.device("cpu")


@dataclass
class PanelData:
    name: str
    task: str
    examples: list[Example]
    refs: list[list[str]]


@dataclass(frozen=True)
class GeneralWindow:
    """A window of the general-language panel as stored by the data-generation step: ids, the (position, vocabulary index) of every in-vocabulary word, the stratum and, for a marker-like
    window, the position of the last token of the first marker-like string within tokens 1-64."""

    ids: tuple[int, ...]
    reads: tuple[tuple[int, int], ...]
    stratum: str  # "marker" | "ordinary"
    marker_end: int = -1


@dataclass(frozen=True)
class CombinedItem:
    ex_a: Example
    ex_b: Example
    refs_a: tuple[str, ...]
    refs_b: tuple[str, ...]


@dataclass
class EvalContext:
    student: Student
    decoder: ByteDecoder
    marker_index: int
    max_new: int
    router_layer: int
    newline_ids: tuple[int, ...]
    panels: dict[str, PanelData]  # E_A, E_B (and any other single-task panel)
    subsample: dict[str, list[int]]  # panel name -> indices of the 300-item ablation subsample
    combined: list[CombinedItem] = field(default_factory=list)
    windows: list[GeneralWindow] = field(default_factory=list)
    decision_index: int = 63  # token 64 (0-based index 63)
    first_nll_index: int = 64  # tokens 65..: the loss positions start at token index 64
    vocabulary: int = core.VOCABULARY
    provisional_combined: bool = False
    seed_plan: core.SeedPlan | None = None


# --- decoding and single-panel scoring --------------------------------------------------------------------------------------------------------------
def generate(ctx: EvalContext, arm: Arm, ex: Example, tasks: Sequence[str], ablation: Ablation | None = None, extra_reads: Sequence[Read] = ()) -> list[int]:
    reads = reads_of(ex, tasks, ctx.marker_index) + list(extra_reads)
    add, adapter = arm.prepare([reads], 1, len(ex.prompt_ids), CPU, ablation)
    ctx.student.read_layer = arm.layer
    return ctx.student.greedy(torch.tensor([list(ex.prompt_ids)]), add=add, adapter=adapter, max_new=ctx.max_new, stop_bytes=ctx.decoder.table)


def route_for(ctx: EvalContext, ex: Example, router: Router | None, route: str) -> list[str]:
    """The tasks an example is read with: the oracle route (the example's own task, from the marker by rule), a learned route (the router's decision at the last prompt token), or none."""
    if route == "oracle":
        return [ex.task]
    if route == "none":
        return []
    if route == "learned" and router is not None:
        pred = router.predict(hidden_at_ends(ctx.student, ctx.router_layer, [ex.prompt_ids]))[0]
        return [] if pred == "none" else [pred]
    raise ValueError(f"unknown route {route!r}")


@dataclass
class PanelScore:
    mean: float
    items: list[float]
    exact: list[bool]
    sequences: list[list[int]]
    texts: list[str]

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = core.jsonable({"mean": self.mean, "items": self.items, "exact": self.exact, "sequences": self.sequences, "exact_rate": mean([float(x) for x in self.exact])})
        return out


def score_panel(ctx: EvalContext, arm: Arm, panel: PanelData, *, route: str = "oracle", router: Router | None = None, ablation: Ablation | None = None, indices: Sequence[int] | None = None) -> PanelScore:
    idx = list(range(len(panel.examples))) if indices is None else list(indices)
    items: list[float] = []
    exact: list[bool] = []
    seqs: list[list[int]] = []
    texts: list[str] = []
    for i in idx:
        ex = panel.examples[i]
        tasks = route_for(ctx, ex, router, route)
        ids = generate(ctx, arm, ex, tasks, ablation)
        text = ctx.decoder.answer_text(ids)
        refs = panel.refs[i]
        items.append(chrf_item(text, refs))
        exact.append(normalize(text) in {normalize(r) for r in refs})
        seqs.append(ids)
        texts.append(text)
    return PanelScore(mean(items), items, exact, seqs, texts)


# --- ablations (section 7) ----------------------------------------------------------------------------------------------------------------------------
def memory_ablations(ctx: EvalContext, arm: MemoryArm, panels: Sequence[str], stages: Sequence[int], tasks: Sequence[str]) -> dict[str, dict[str, Any]]:
    """The five ablations on the 300-item subsample of each panel: memory off; values permuted (the given stages among themselves); word codes permuted (the given tasks, marker kept); marker-only;
    words-only. Each permutation control draws from a fresh +4 generator; the subsample is the same for every cell and replicate."""
    assert ctx.seed_plan is not None
    out: dict[str, dict[str, Any]] = {}
    for name in panels:
        panel = ctx.panels[name]
        sub = ctx.subsample[name]
        res: dict[str, Any] = {"subsample_indices": sub, "unablated": score_panel(ctx, arm, panel, indices=sub).to_json()}
        for kind in ("off", "value_perm", "code_perm", "marker_only", "words_only"):
            ab = make_ablation(kind, arm.store, ctx.seed_plan.gen(4, f"permutation controls: {kind}"), stages=stages, tasks=tasks, vocabulary=ctx.vocabulary)
            res[kind] = score_panel(ctx, arm, panel, ablation=ab, indices=sub).to_json()
        out[name] = res
    return out


# --- combined tasks (section 6.4) -------------------------------------------------------------------------------------------------------------------
def _answer_ids(ctx: EvalContext, ids: Sequence[int]) -> list[int]:
    """The model's own answer: the generated tokens before the stop token (the stop token and anything after it are dropped; the newline is re-inserted as its own segment)."""
    k = ctx.decoder.stop_index(ids)
    return list(ids if k is None else ids[:k])


def _bos_len(ex: Example) -> int:
    return len(ex.segments[0].ids) if ex.segments and ex.segments[0].text == "<bos>" else 0


def _generate_ids(ctx: EvalContext, arm: Arm, ids: Sequence[int], reads: Sequence[Read]) -> list[int]:
    add, adapter = arm.prepare([list(reads)], 1, len(ids), CPU, None)
    ctx.student.read_layer = arm.layer
    return ctx.student.greedy(torch.tensor([list(ids)]), add=add, adapter=adapter, max_new=ctx.max_new, stop_bytes=ctx.decoder.table)


def score_combined(ctx: EvalContext, arm: Arm, kind: str) -> dict[str, Any]:
    """C1 (two sources: ``English: {s1}\\nGerman:`` ..., then after the model's own answer ``\\nEnglish: {s2}\\nFrench:`` ...) or C2 (one source, both answers; the source words are read with both tasks'
    codes and the reads are summed). Score: mean chrF of the two answers; an item passes if both match a reference exactly. PROVISIONAL layouts: see the module docstring."""
    if ctx.provisional_combined and (ctx.seed_plan is None or ctx.seed_plan.mode != "test"):
        raise core.PendingLeadReview("the provisional combined-task layout is test-only: it is unreachable in calibration, rehearsal or registered mode")
    if not core.CFG["pending"]["combined_tasks_defined"] and not ctx.provisional_combined:
        raise core.PendingLeadReview("combined tasks C1/C2: the ADR does not say how C1 pairs two sources or how C2 lays out its prompt (section 6.4); stopped, pending the lead's decision")
    if kind not in ("C1", "C2"):
        raise ValueError(kind)
    n = len(ctx.combined)
    scores: list[float] = []
    passes: list[bool] = []
    for i, it in enumerate(ctx.combined):
        if kind == "C1":
            ex2 = ctx.combined[(i + 1) % n].ex_b  # PROVISIONAL pairing: item i's German prompt with item i+1's French prompt (cyclic)
            refs2 = ctx.combined[(i + 1) % n].refs_b
            a1 = _generate_ids(ctx, arm, it.ex_a.prompt_ids, reads_of(it.ex_a, ["A"], ctx.marker_index))
            part2 = list(ex2.prompt_ids)[_bos_len(ex2) :]
            ids2 = [*it.ex_a.prompt_ids, *_answer_ids(ctx, a1), *ctx.newline_ids, *part2]
            off = len(ids2) - len(part2)
            reads2 = [(off + p - _bos_len(ex2), "B", j) for p, j in ex2.reads] + [(off + ex2.marker - _bos_len(ex2), "B", ctx.marker_index)]
            a2 = _generate_ids(ctx, arm, ids2, reads_of(it.ex_a, ["A"], ctx.marker_index) + reads2)
            h1, h2, r1, r2 = ctx.decoder.answer_text(a1), ctx.decoder.answer_text(a2), it.refs_a, refs2
        else:
            reads_first = reads_of(it.ex_a, ["A", "B"], ctx.marker_index)
            reads_first = [r for r in reads_first if not (r[2] == ctx.marker_index and r[1] == "B")]  # PROVISIONAL: the French marker is read where it stands, in the appended part
            a1 = _generate_ids(ctx, arm, it.ex_a.prompt_ids, reads_first)
            marker_b = list(it.ex_b.segments[-1].ids)
            ids2 = [*it.ex_a.prompt_ids, *_answer_ids(ctx, a1), *ctx.newline_ids, *marker_b]
            reads2 = [*reads_first, (len(ids2) - 1, "B", ctx.marker_index)]
            a2 = _generate_ids(ctx, arm, ids2, reads2)
            h1, h2, r1, r2 = ctx.decoder.answer_text(a1), ctx.decoder.answer_text(a2), it.refs_a, it.refs_b
        s1, s2 = chrf_item(h1, r1), chrf_item(h2, r2)
        scores.append((s1 + s2) / 2)
        passes.append(normalize(h1) in {normalize(r) for r in r1} and normalize(h2) in {normalize(r) for r in r2})
    return {"kind": kind, "layout": "PROVISIONAL (PENDING LEAD REVIEW)" if not core.CFG["pending"]["combined_tasks_defined"] else "registered", "mean": mean(scores), "items": scores, "pass_rate": mean([float(p) for p in passes])}


# --- general-language quality (section 6.4) ---------------------------------------------------------------------------------------------------------------
@torch.no_grad()
def _window_logits(ctx: EvalContext, arm: Arm, w: GeneralWindow, tasks: Sequence[str]) -> torch.Tensor:
    reads: list[Read] = []
    for t in tasks:
        reads += [(p, t, j) for p, j in w.reads]
    ids = torch.tensor([list(w.ids)])
    return run_student(ctx.student, arm, ids, [reads])[0]


@torch.no_grad()
def general_quality(ctx: EvalContext, arm: Arm, router: Router | None, *, always_on_task: str | None = None) -> dict[str, Any]:
    """Condition (a), the registered GEN measurement: for each window the learned router of the snapshot reads the student's hidden state at token 64 of a memory-free pass; if it returns a task
    the store is read with that task's codes at every in-vocabulary word of the whole window, if "none" nothing is read. The loss is the mean next-token negative log-likelihood over tokens 65 onwards
    of all windows, against the unmodified student's on the same positions; the router's false-trigger count per stratum is printed beside it. Condition (b), the always-on diagnostic, reads with
    ``always_on_task``'s codes at every in-vocabulary word (an adapter is always applied); it enters no rule. Also: mean KL to the Stage 0 student and the share of unchanged top-1 tokens."""
    null = NullArm()
    res: dict[str, Any] = {"windows": len(ctx.windows)}
    nll_base: list[float] = []
    nll_a: list[float] = []
    nll_b: list[float] = []
    kl_a: list[float] = []
    same_a: list[float] = []
    triggers = {"marker": 0, "ordinary": 0}
    counts = {"marker": 0, "ordinary": 0}
    preds: list[str] = []
    if router is not None and ctx.windows:
        preds = router.predict(hidden_at_ends(ctx.student, ctx.router_layer, [w.ids for w in ctx.windows], [ctx.decision_index] * len(ctx.windows)))
    for k, w in enumerate(ctx.windows):
        tgt = torch.tensor(list(w.ids[ctx.first_nll_index :]))
        base = _window_logits(ctx, null, w, [])[ctx.first_nll_index - 1 : -1]
        lp_base = F.log_softmax(base, dim=-1)
        nll_base.append(float(-lp_base.gather(1, tgt[:, None]).mean()))
        counts[w.stratum] += 1
        pred = preds[k] if router is not None else "none"
        tasks = [] if pred == "none" else [pred]
        if tasks:
            triggers[w.stratum] += 1
        a = _window_logits(ctx, arm, w, tasks)[ctx.first_nll_index - 1 : -1]
        lp_a = F.log_softmax(a, dim=-1)
        nll_a.append(float(-lp_a.gather(1, tgt[:, None]).mean()))
        kl_a.append(float((lp_base.exp() * (lp_base - lp_a)).sum(-1).mean()))
        same_a.append(float((a.argmax(-1) == base.argmax(-1)).float().mean()))
        if always_on_task is not None:
            b = _window_logits(ctx, arm, w, [always_on_task])[ctx.first_nll_index - 1 : -1]
            nll_b.append(float(-F.log_softmax(b, dim=-1).gather(1, tgt[:, None]).mean()))
    res.update({"nll_base": mean(nll_base), "nll_router": mean(nll_a), "loss_increase": mean(nll_a) - mean(nll_base), "false_trigger_count": triggers, "stratum_sizes": counts, "mean_kl_to_stage0": mean(kl_a), "top1_unchanged": mean(same_a)})
    if always_on_task is not None:
        res["always_on_loss_increase"] = mean(nll_b) - mean(nll_base)
    res["gate_margin"] = core.CFG["gates"]["gen_loss_margin"]
    res["passes"] = bool(res["loss_increase"] <= res["gate_margin"])
    return core.jsonable(res)  # type: ignore[no-any-return]


@torch.no_grad()
def general_by_construction(ctx: EvalContext, arm: Arm) -> dict[str, Any]:
    """Under oracle routes every arm is bit-identical to the student on the general panel: no read and no adapter on route "none". Printed BY CONSTRUCTION; it counts for nothing (gate G5a checks it)."""
    same = True
    for w in ctx.windows:
        a, b = _window_logits(ctx, arm, w, []), _window_logits(ctx, NullArm(), w, [])
        same = same and bool(torch.equal(a, b))
    return {"bit_identical_to_student": same, "label": "BY CONSTRUCTION"}


# --- work counts and timing (section 10.2) ------------------------------------------------------------------------------------------------------------
def active_work(arm: Arm, reads_per_item: float, generated_tokens_per_item: float, rows_total: int | None = None) -> dict[str, Any]:
    """Logical counts, never measured efficiency: reads per item, key products per read (N or 2N, a flat scan), value rows read per item, and per generated token: value rows read per item x
    width / generated tokens for the store; adapter parameters applied per generated token for LoRA."""
    if isinstance(arm, MemoryArm):
        rows = rows_total if rows_total is not None else arm.store.rows
        width = arm.store.width
        value_rows = reads_per_item * core.TOP
        return {"kind": "memory", "reads_per_item": reads_per_item, "key_products_per_read": rows, "value_rows_read_per_item": value_rows, "value_parameters_read_per_generated_token": value_rows * width / max(1.0, generated_tokens_per_item), "type": "analytical count"}
    params = arm.parameter_count()
    return {"kind": arm.kind, "adapter_parameters_applied_per_generated_token": params if arm.kind == "lora" else 0, "type": "analytical count"}


def timing_benchmark(fn: Callable[[], Any], repetitions: int | None = None) -> dict[str, Any]:
    """Median wall seconds of ``fn`` over the repetitions (CPU, descriptive only: no latency, throughput, storage or efficiency claim)."""
    reps = repetitions if repetitions is not None else core.CFG["budget"]["timing_repetitions"]
    times: list[float] = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return {"repetitions": reps, "median_seconds": sorted(times)[len(times) // 2], "all_seconds": times, "type": "measured, descriptive"}


def truncation_percentile(token_lengths: Sequence[int], q: float | None = None) -> int:
    """The new-token limit: the 99.5th percentile of the gold references of D_cal in student tokens (rule of section 5.4; measured in the rehearsal and frozen)."""
    qq = q if q is not None else core.CFG["data"]["truncation_percentile"]
    s = sorted(token_lengths)
    return int(s[min(len(s) - 1, math.ceil(qq * len(s)) - 1)]) if s else 0
