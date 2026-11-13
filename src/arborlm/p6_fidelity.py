"""P6-Q routing-fidelity measurements (ADR-0011 Part Q, sections 4.1-4.6).

Inference only. For one restored tree checkpoint this module runs the *unmodified* P5 model
under four selection rules by substituting the memory's lookup (nothing else) inside the full
forward pass, records every per-query quantity of section 4.3 and derives the registered
measurements and engineering gates.

Rule substitution never touches parameters or buffers: ``substituted_rule`` places a temporary
instance attribute ``lookup`` on the ``Memory`` module (shadowing the class method) and removes
it on exit. The substituted lookup calls the frozen ``pilot_model.tree_candidates`` with the
rule's ``visit`` and ``use_prior`` after computing the route scores with exactly the expression
``Memory.lookup`` uses. Query projection, value gathering, softmax weighting, output projection
and gate are the unmodified ``Memory.forward``. Rule T2P (``visit=2``, ``use_prior=True``, the
defaults of ``Memory.lookup``) is therefore the same computation as the unmodified model.

Every statement about prediction or fidelity needs the registered run. No P6-Q quantity (no rule
substitution, no recall, no flag) has been computed on any real checkpoint. The only real-checkpoint
contact so far is the ``loader-smoke`` subcommand of ``p6_fidelity_study``: locate, hash
verification, strict restore and the bitwise replay of the unmodified model's recorded P5 NLL for
one cell, and nothing else.
"""

from __future__ import annotations

import ctypes
import importlib
import math
import os
import random
import struct
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import torch
from torch import Tensor
from torch.nn import functional as F

from . import pilot_model
from .io import canonical_json, sha256
from .longer_training import _isolated_rng
from .p5_config import BATCH, VAL_TARGETS
from .p5_model import Model, evaluate, state_digest
from .pilot_metrics import RetrievalCounts, loss_for
from .pilot_model import (
    BRANCHES,
    EPS,
    PER_BRANCH,
    SLOTS,
    TEMP,
    TOP,
    VOCAB,
    Lookup,
    Memory,
    tree_candidates,
)

RULES = ("T2P", "T2N", "X16P", "X16N")
RULE_SPEC: dict[str, tuple[int, bool]] = {
    "T2P": (2, True),
    "T2N": (2, False),
    "X16P": (16, True),
    "X16N": (16, False),
}
WIDTHS = (2, 3, 4, 6, 8, 12, 16)
NEAR_TIE = 1e-5
QUANTILES = (0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)
CERTIFICATE_BASE = 1.0 / TEMP
SCHEMA = "P6Q-checkpoint-v1"
TREE_VARIANTS = ("fixed_tree", "learned_tree")
# Analytical-work fields of ``RetrievalCounts.report`` that describe the registered T2P rule only.
ANALYTICAL_WORK_FIELDS = (
    "unit_warning",
    "logical_value_elements_per_query",
    "router_dots_per_query",
    "full_key_dots_per_query",
    "logical_key_elements_per_query",
    "logical_router_elements_per_query",
)
KNOWN_LIMITS = (
    "RNG-unchanged checks inside an isolated-RNG block cannot observe RNG use, because the block "
    "restores the generator state on exit. The check in evaluate_checkpoint runs outside the "
    "isolated blocks of run_rule and evaluate, so it only sees changes made outside them.",
)

ReferenceFn = Callable[..., tuple[Tensor, Tensor, Tensor]]
# hook(query offset of the batch, queries, selected scores, lookup, captured candidate scores)
Hook = Callable[[int, Tensor, Tensor, Lookup, list[tuple[Tensor, Tensor]]], None]


class GateViolation(RuntimeError):
    """An engineering gate of ADR-0011 section 4.3 (or an integrity check) failed."""

    def __init__(self, gate: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"gate {gate}: {message}")
        self.gate = gate
        self.message = message
        self.details = details or {}


def load_reference() -> ReferenceFn:
    """Load the auditor's independent float64 reference (never written by this module)."""
    module = importlib.import_module("arborlm.p6_fidelity_reference")
    return cast(ReferenceFn, module.exhaustive_reference)


# ---------------------------------------------------------------------------------------------
# Rule substitution
# ---------------------------------------------------------------------------------------------


@contextmanager
def _spy_candidate_scores(sink: list[tuple[Tensor, Tensor]]) -> Iterator[None]:
    """Record the (candidate scores, candidate IDs) that frozen ``tree_candidates`` selects from."""
    original = pilot_model.stable_top

    def spy(scores: Tensor, count: int, ids: Tensor | None = None) -> tuple[Tensor, Tensor]:
        if ids is not None:
            sink.append((scores, ids))
        return original(scores, count, ids)

    setattr(pilot_model, "stable_top", spy)  # noqa: B010
    try:
        yield
    finally:
        setattr(pilot_model, "stable_top", original)  # noqa: B010


class RuleRecorder:
    """Per-rule store of the lookups seen during one pass over the panel."""

    def __init__(
        self, rule: str, variant: str, *, hook: Hook | None = None, spy_scores: bool = False
    ) -> None:
        self.rule = rule
        self.hook = hook
        self.spy_scores = spy_scores
        self.tracker = RetrievalCounts(variant)
        self.offset = 0
        self.batch_sizes: list[int] = []
        self.q: list[Tensor] = []
        self.values: list[Tensor] = []
        self.selected: list[Tensor] = []
        self.branches: list[Tensor] = []
        self.routes: list[Tensor] = []
        self.weights: list[Tensor] = []

    def add(
        self,
        q: Tensor,
        values: Tensor,
        lookup: Lookup,
        captured: list[tuple[Tensor, Tensor]],
    ) -> None:
        if lookup.branch_ids is None or lookup.route_scores is None:
            raise ValueError("tree lookup without branch IDs or route scores")
        if not bool(torch.isfinite(values).all()) or not bool(
            torch.isfinite(lookup.route_scores).all()
        ):
            raise GateViolation("finite", f"non-finite scores under rule {self.rule}")
        self.tracker.update(lookup)
        self.q.append(q)
        self.values.append(values)
        self.selected.append(lookup.selected)
        self.branches.append(lookup.branch_ids)
        self.routes.append(lookup.route_scores)
        self.weights.append(values.softmax(-1))
        self.batch_sizes.append(q.shape[0])
        if self.hook is not None:
            self.hook(self.offset, q, values, lookup, captured)
        self.offset += q.shape[0]


@contextmanager
def substituted_rule(memory: Memory, rule: str, recorder: RuleRecorder) -> Iterator[None]:
    """Temporarily replace ``memory.lookup`` by the tree lookup under ``rule``."""
    if memory.variant not in TREE_VARIANTS:
        raise ValueError("rule substitution requires a tree memory")
    if "lookup" in memory.__dict__:
        raise ValueError("memory lookup is already substituted")
    visit, use_prior = RULE_SPEC[rule]

    def lookup(q: Tensor) -> tuple[Tensor, Lookup]:
        routes = (q @ F.normalize(memory.router, dim=-1, eps=EPS).T) / TEMP
        captured: list[tuple[Tensor, Tensor]] = []
        if recorder.spy_scores:
            with _spy_candidate_scores(captured):
                values, selected, candidates, branches = tree_candidates(
                    q, memory.keys, routes, visit=visit, use_prior=use_prior
                )
        else:
            values, selected, candidates, branches = tree_candidates(
                q, memory.keys, routes, visit=visit, use_prior=use_prior
            )
        result = Lookup(selected, candidates, branch_ids=branches, route_scores=routes)
        recorder.add(q, values, result, captured)
        return values, result

    memory.__dict__["lookup"] = lookup
    try:
        yield
    finally:
        memory.__dict__.pop("lookup", None)


@dataclass
class RulePass:
    rule: str
    nll: float
    token_loss: Tensor
    q: Tensor
    values: Tensor
    selected: Tensor
    branches: Tensor
    routes: Tensor
    weights: Tensor
    tracker: RetrievalCounts
    batch_sizes: list[int]


def run_rule(
    model: Model,
    data: Tensor,
    rule: str,
    *,
    hook: Hook | None = None,
    spy_scores: bool = False,
    expected_targets: int = VAL_TARGETS,
) -> RulePass:
    """Full forward over the panel in the registered 8-row batches under ``rule``."""
    memory = model.addition
    if not isinstance(memory, Memory):
        raise ValueError("P6-Q requires a tree Memory addition")
    recorder = RuleRecorder(rule, model.cell.variant, hook=hook, spy_scores=spy_scores)
    was_training = model.training
    model.eval()
    total, count = 0.0, 0
    losses: list[Tensor] = []
    try:
        with _isolated_rng(), torch.no_grad(), substituted_rule(memory, rule, recorder):
            for start in range(0, data.shape[0], BATCH):
                batch = data[start : start + BATCH]
                logits, _ = model(batch[:, :-1])
                targets = batch[:, 1:]
                total += float(loss_for(logits, targets, "sum"))
                count += targets.numel()
                losses.append(
                    F.cross_entropy(
                        logits.reshape(-1, VOCAB), targets.reshape(-1), reduction="none"
                    )
                )
    finally:
        model.train(was_training)
    if count != expected_targets or count <= 0 or not math.isfinite(total):
        raise GateViolation("finite", f"wrong target count or non-finite loss under rule {rule}")
    return RulePass(
        rule=rule,
        nll=total / count,
        token_loss=torch.cat(losses),
        q=torch.cat(recorder.q),
        values=torch.cat(recorder.values),
        selected=torch.cat(recorder.selected),
        branches=torch.cat(recorder.branches),
        routes=torch.cat(recorder.routes),
        weights=torch.cat(recorder.weights),
        tracker=recorder.tracker,
        batch_sizes=recorder.batch_sizes,
    )


# ---------------------------------------------------------------------------------------------
# Pure measurements
# ---------------------------------------------------------------------------------------------


def overlap_counts(first: Tensor, second: Tensor) -> Tensor:
    """Per query |first ∩ second| for ID rows without repeats."""
    return (first[:, :, None] == second[:, None, :]).any(-1).sum(-1)


def membership(first: Tensor, second: Tensor) -> Tensor:
    """Per entry of ``first`` whether the slot is in the same query's ``second`` row."""
    return (first[:, :, None] == second[:, None, :]).any(-1)


def recall_summary(counts: Tensor) -> dict[str, Any]:
    queries = int(counts.numel())
    total = int(counts.sum())
    histogram = torch.bincount(counts, minlength=TOP + 1).tolist()
    return {
        "queries": queries,
        "overlap_sum": total,
        "mean": total / (TOP * queries),
        "fraction_one": histogram[TOP] / queries,
        "histogram": histogram,
    }


def quantile_summary(values: Tensor) -> dict[str, Any]:
    flat = values.detach().double().flatten()
    if flat.numel() == 0:
        return {"count": 0, "mean": None, "min": None, "max": None, "quantiles": None}
    levels = torch.tensor(QUANTILES, dtype=torch.float64)
    return {
        "count": int(flat.numel()),
        "mean": float(flat.mean()),
        "min": float(flat.min()),
        "max": float(flat.max()),
        "quantiles": {
            f"{p:g}": float(v) for p, v in zip(QUANTILES, torch.quantile(flat, levels), strict=True)
        },
    }


def certificate_mask(values: Tensor, routes: Tensor, visited: Tensor) -> Tensor:
    """Tree's 8th score >= 1/0.2 + best prior among unvisited branches (section 4.3)."""
    prior = routes.log_softmax(-1)
    unvisited_best = prior.scatter(-1, visited, float("-inf")).max(-1).values
    return values[:, TOP - 1].double() >= CERTIFICATE_BASE + unvisited_best.double()


def certificate_summary(
    values: Tensor, routes: Tensor, visited: Tensor, recall_counts: Tensor
) -> dict[str, Any]:
    certified = certificate_mask(values, routes, visited)
    queries = int(certified.numel())
    return {
        "certified_queries": int(certified.sum()),
        "fraction": int(certified.sum()) / queries,
        "certified_with_recall_below_one": int((certified & (recall_counts < TOP)).sum()),
    }


def slot_coverage(
    final_keys: Tensor, final_values: Tensor, initial_keys: Tensor, initial_values: Tensor
) -> dict[str, Tensor]:
    """Per slot bitwise change flags and L2 distance moved from the paired step-0 snapshot."""

    def changed(final: Tensor, initial: Tensor) -> Tensor:
        return (final.contiguous().view(torch.int32) != initial.contiguous().view(torch.int32)).any(
            -1
        )

    return {
        "key_changed": changed(final_keys, initial_keys),
        "value_changed": changed(final_values, initial_values),
        "key_l2": (final_keys.double() - initial_keys.double()).norm(dim=-1),
        "value_l2": (final_values.double() - initial_values.double()).norm(dim=-1),
    }


def coverage_summary(coverage: dict[str, Tensor]) -> dict[str, Any]:
    key, value = coverage["key_changed"], coverage["value_changed"]
    return {
        "slots": int(key.numel()),
        "key_changed": int(key.sum()),
        "value_changed": int(value.sum()),
        "key_only_changed": int((key & ~value).sum()),
        "value_only_changed": int((value & ~key).sum()),
        "both_changed": int((key & value).sum()),
        "either_changed": int((key | value).sum()),
        "key_l2_of_changed": quantile_summary(coverage["key_l2"][key]),
        "value_l2_of_changed": quantile_summary(coverage["value_l2"][value]),
        "definition": "trained slot = key or value differs bitwise from the paired step-0 snapshot",
    }


def trained_recall(reference: Tensor, kept: Tensor, trained: Tensor) -> dict[str, Any]:
    """Recall restricted to reference-selected slots whose key or value moved in training."""
    reference_trained = trained[reference]
    per_query = reference_trained.sum(-1)
    hits = (reference_trained & kept).sum(-1)
    has = per_query > 0
    total = int(per_query.sum())
    return {
        "reference_slots_total": int(reference.numel()),
        "reference_slots_trained": total,
        "queries_with_trained_reference": int(has.sum()),
        "recall_macro_over_queries_with_trained_reference": (
            float((hits[has].double() / per_query[has].double()).mean())
            if bool(has.any())
            else None
        ),
        "recall_pooled": (int(hits.sum()) / total) if total else None,
    }


def lost_candidates(
    reference: Tensor,
    reference_values: Tensor,
    reference_branches: Tensor,
    t2p_selected: Tensor,
    t2p_values: Tensor,
    trained: Tensor | None,
    *,
    with_scores: bool,
) -> dict[str, Any]:
    """Reference-selected slots absent from the T2P selection (section 4.3)."""
    kept = membership(reference, t2p_selected)
    lost = ~kept
    branch = reference // PER_BRANCH
    rank = (reference_branches[:, None, :] == branch[:, :, None]).to(torch.int32).argmax(-1) + 1
    per_query = lost.sum(-1)
    out: dict[str, Any] = {
        "lost_candidates": int(lost.sum()),
        "queries_with_loss": int((per_query > 0).sum()),
        "lost_per_query_histogram": torch.bincount(per_query, minlength=TOP + 1).tolist(),
        "route_rank_histogram": torch.bincount(rank[lost], minlength=BRANCHES + 1)[1:].tolist(),
    }
    if with_scores:
        out["reference_score"] = quantile_summary(reference_values[lost])
        margin = reference_values - t2p_values[:, TOP - 1 : TOP]
        out["margin_to_t2p_boundary"] = quantile_summary(margin[lost])
    if trained is not None:
        is_trained = trained[reference]
        out["lost_trained"] = int((lost & is_trained).sum())
        out["lost_untrained"] = int((lost & ~is_trained).sum())
        out["reference_recall_trained"] = trained_recall(reference, kept, trained)
    return out


def weighted_recall(reference_weights: Tensor, reference: Tensor, other: Tensor) -> float:
    """Mean over queries of the reference softmax mass on slots ``other`` also selects."""
    kept = membership(reference, other)
    return float((reference_weights.double() * kept).sum(-1).mean())


def prior_effects(
    routes: Tensor, t2p_branches: Tensor, t2p_selected: Tensor, t2n_selected: Tensor
) -> dict[str, Any]:
    top2 = routes.topk(2, dim=-1).values.double()
    counts = overlap_counts(t2p_selected, t2n_selected)
    all_top1 = ((t2p_selected // PER_BRANCH) == t2p_branches[:, :1]).all(-1)
    return {
        "route_gap_top1_minus_top2": quantile_summary(top2[:, 0] - top2[:, 1]),
        "fraction_all_selected_in_top1_branch": float(all_top1.double().mean()),
        "fraction_t2n_t2p_sets_differ": float((counts < TOP).double().mean()),
        "t2n_t2p_overlap_mean": int(counts.sum()) / (TOP * int(counts.numel())),
    }


def concentration_report(
    tracker: RetrievalCounts, slots: int = SLOTS, rule: str = "T2P"
) -> dict[str, Any]:
    """Exactly the tail of ``p5_model.evaluate`` for the retrieval statistics.

    ``RetrievalCounts.report`` hard-codes the analytical work of the registered T2P rule (512 key
    dots per query and so on). Those fields are kept byte-for-byte for T2P, whose report must
    reproduce the P5 record, and are dropped for every other rule, where they would be wrong
    (under X16 every query scores 4,096 keys).
    """
    retrieval = tracker.report()
    if rule != "T2P":
        for name in ANALYTICAL_WORK_FIELDS:
            retrieval.pop(name, None)
        retrieval["analytical_work_fields"] = "omitted: computed for the registered T2P rule only"
    observed = tracker.selected.double()
    probabilities = observed[observed > 0] / observed.sum()
    entropy = float(-(probabilities * probabilities.log()).sum())
    retrieval["selected_slot_entropy_normalized"] = entropy / math.log(slots)
    retrieval["effective_selected_slots"] = math.exp(entropy)
    return retrieval


def token_loss_split(loss_t2p: Tensor, loss_alt: Tensor, changed: Tensor) -> dict[str, Any]:
    """Per-token loss differences (alternative minus T2P) by whether the selected set changed."""
    difference = (loss_alt.double() - loss_t2p.double()).flatten()
    result: dict[str, Any] = {}
    everything = torch.ones_like(changed)
    for name, mask in (("changed", changed), ("unchanged", ~changed), ("all", everything)):
        count = int(mask.sum())
        selected = difference[mask]
        result[name] = {
            "tokens": count,
            "mean_difference": float(selected.mean()) if count else None,
            "mean_loss_T2P": float(loss_t2p.double().flatten()[mask].mean()) if count else None,
            "mean_loss_alternative": (
                float(loss_alt.double().flatten()[mask].mean()) if count else None
            ),
            "fraction_alternative_lower": float((selected < 0).double().mean()) if count else None,
        }
    return result


# ---------------------------------------------------------------------------------------------
# Gates (hard checks)
# ---------------------------------------------------------------------------------------------


def restricted_selection_mismatches(
    captured_scores: Tensor,
    captured_ids: Tensor,
    x16_branches: Tensor,
    t2p_selected: Tensor,
    t2p_values: Tensor,
    t2p_branches: Tensor,
) -> dict[str, Any]:
    """Gate (ii) for one batch: T2P equals the top 8 of the X16P scores of its visited branches."""
    width = 2 * PER_BRANCH
    restricted_values, restricted = pilot_model.stable_top(
        captured_scores[:, :width], TOP, captured_ids[:, :width]
    )
    rows = (restricted != t2p_selected).any(-1).nonzero().flatten().tolist()
    branch_rows = (x16_branches[:, :2] != t2p_branches).any(-1).nonzero().flatten().tolist()
    return {
        "selection_mismatch_rows": rows,
        "visited_branch_mismatch_rows": branch_rows,
        "score_bitwise_mismatch_rows": int((restricted_values != t2p_values).any(-1).sum()),
    }


def lost_rank_violations(
    x16p_selected: Tensor, x16_branches: Tensor, t2p_selected: Tensor
) -> list[dict[str, int]]:
    """Gate (iii): every lost slot must lie in a branch of route rank >= 3."""
    lost = ~membership(x16p_selected, t2p_selected)
    branch = x16p_selected // PER_BRANCH
    rank = (x16_branches[:, None, :] == branch[:, :, None]).to(torch.int32).argmax(-1) + 1
    bad = (lost & (rank < 3)).nonzero().tolist()
    return [
        {"query": q, "position": p, "slot": int(x16p_selected[q, p]), "rank": int(rank[q, p])}
        for q, p in bad
    ]


def reference_disagreements(
    rule: str,
    offset: int,
    frozen: Tensor,
    reference: Tensor,
    gap: Tensor,
    scores: Tensor | None = None,
) -> list[dict[str, Any]]:
    """Gate (iv) for one batch: list every query whose frozen and reference ID rows differ.

    A disagreement is registered as a stop only when the selected ID *sets* differ outside a
    near-tie (reference boundary gap <= 1e-5). Rows with equal sets but a different order are
    listed too, with ``sets_differ`` false and the smallest adjacent reference gap among the
    top 8 (a float32-versus-float64 interior tie), because the registered measurements use sets.
    """
    rows = (frozen != reference).any(-1).nonzero().flatten().tolist()
    out: list[dict[str, Any]] = []
    for row in rows:
        sets_differ = set(frozen[row].tolist()) != set(reference[row].tolist())
        entry: dict[str, Any] = {
            "rule": rule,
            "query": offset + row,
            "frozen_ids": frozen[row].tolist(),
            "reference_ids": reference[row].tolist(),
            "boundary_gap": float(gap[row]),
            "near_tie": float(gap[row]) <= NEAR_TIE,
            "sets_differ": sets_differ,
        }
        if scores is not None:
            top = scores[row].topk(TOP).values
            entry["min_adjacent_gap_top8"] = float((top[:-1] - top[1:]).min())
        out.append(entry)
    return out


# ---------------------------------------------------------------------------------------------
# Raw array output
# ---------------------------------------------------------------------------------------------

DTYPES = {
    torch.int8: "int8",
    torch.int16: "int16",
    torch.int64: "int64",
    torch.uint8: "uint8",
    torch.float32: "float32",
    torch.float64: "float64",
}


def write_array(directory: Path, name: str, tensor: Tensor) -> dict[str, Any]:
    """Write a little-endian row-major raw array; the returned record carries its SHA-256."""
    data = tensor.detach().cpu().contiguous()
    raw = ctypes.string_at(data.data_ptr(), data.numel() * data.element_size())
    path = directory / f"{name}.bin"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "file": path.name,
        "dtype": DTYPES[data.dtype],
        "shape": list(data.shape),
        "bytes": len(raw),
        "sha256": sha256(raw),
    }


# ---------------------------------------------------------------------------------------------
# One checkpoint
# ---------------------------------------------------------------------------------------------


def _bitwise(first: float, second: float) -> bool:
    return struct.pack("!d", first) == struct.pack("!d", second)


def _width_recall(selected: Tensor, reference: Tensor) -> dict[str, float]:
    counts = overlap_counts(selected, reference)
    return {
        "mean": int(counts.sum()) / (TOP * int(counts.numel())),
        "fraction_one": int((counts == TOP).sum()) / int(counts.numel()),
    }


def evaluate_checkpoint(
    model: Model,
    panel: Tensor,
    *,
    recorded_nll: float,
    recorded_retrieval: dict[str, Any],
    initial_tensors: tuple[Tensor, Tensor] | None,
    reference: ReferenceFn,
    expected_targets: int = VAL_TARGETS,
) -> tuple[dict[str, Any], dict[str, Tensor]]:
    """Run the four rules and derive every registered measurement for one checkpoint."""
    memory = model.addition
    if not isinstance(memory, Memory) or memory.variant not in TREE_VARIANTS:
        raise ValueError("P6-Q requires a tree checkpoint")
    clock = time.perf_counter()
    phases: dict[str, float] = {}

    def tick(name: str) -> None:
        nonlocal clock
        now = time.perf_counter()
        phases[name] = now - clock
        clock = now

    state_before = state_digest(model)
    python_before, torch_before = random.getstate(), torch.get_rng_state()

    # Gate (i): unmodified replay, then T2P through the substitution wrapper.
    unmodified = evaluate(model, panel, expected_targets)
    tick("unmodified_replay")
    if not _bitwise(unmodified["nll"], recorded_nll):
        raise GateViolation(
            "i",
            "unmodified model did not reproduce the recorded P5 NLL bitwise",
            {"replayed": unmodified["nll"], "recorded": recorded_nll},
        )
    if canonical_json(unmodified["retrieval"]) != canonical_json(recorded_retrieval):
        raise GateViolation("i", "unmodified retrieval statistics differ from the P5 record")
    t2p = run_rule(model, panel, "T2P", expected_targets=expected_targets)
    tick("rule_T2P")
    t2p_concentration = concentration_report(t2p.tracker)
    if not _bitwise(t2p.nll, recorded_nll) or not _bitwise(t2p.nll, unmodified["nll"]):
        raise GateViolation(
            "i",
            "T2P through the wrapper is not bitwise the unmodified model",
            {"t2p": t2p.nll, "unmodified": unmodified["nll"], "recorded": recorded_nll},
        )
    if canonical_json(t2p_concentration) != canonical_json(recorded_retrieval):
        raise GateViolation("i", "T2P concentration does not reproduce the P5 record")

    t2n = run_rule(model, panel, "T2N", expected_targets=expected_targets)
    tick("rule_T2N")

    keys, router = memory.keys.detach(), memory.router.detach()
    disagreements: list[dict[str, Any]] = []
    restricted_failures: dict[str, Any] = {"rows": [], "branches": [], "score_mismatch": 0}
    # Width curve: the visit-k candidates are the first 256 * k columns of the X16P candidate
    # scores (route-rank branch order), selected with the frozen ``stable_top``. The first batch
    # of every checkpoint is cross-checked against ``tree_candidates(visit=k, use_prior=True)``.
    width_parts: dict[int, list[Tensor]] = {k: [] for k in WIDTHS if k != 16}
    width_check: dict[str, Any] = {"batch_offset": 0, "widths": [], "passed": False}

    def reference_hook(rule: str, use_prior: bool) -> Hook:
        def hook(
            offset: int,
            q: Tensor,
            values: Tensor,
            lookup: Lookup,
            captured: list[tuple[Tensor, Tensor]],
        ) -> None:
            ref_scores, ids, gap = reference(q, keys, router, use_prior=use_prior)
            disagreements.extend(
                reference_disagreements(rule, offset, lookup.selected, ids, gap, ref_scores)
            )
            if rule == "X16P":
                if lookup.branch_ids is None or len(captured) != 1:
                    raise GateViolation("ii", "X16P candidate scores were not captured")
                scores, candidate_ids = captured[0]
                end = offset + q.shape[0]
                found = restricted_selection_mismatches(
                    scores,
                    candidate_ids,
                    lookup.branch_ids,
                    t2p.selected[offset:end],
                    t2p.values[offset:end],
                    t2p.branches[offset:end],
                )
                restricted_failures["rows"].extend(
                    offset + r for r in found["selection_mismatch_rows"]
                )
                restricted_failures["branches"].extend(
                    offset + r for r in found["visited_branch_mismatch_rows"]
                )
                restricted_failures["score_mismatch"] += found["score_bitwise_mismatch_rows"]
                for k in WIDTHS:
                    if k == 16:
                        continue
                    columns = PER_BRANCH * k
                    _, chosen = pilot_model.stable_top(
                        scores[:, :columns], TOP, candidate_ids[:, :columns]
                    )
                    width_parts[k].append(chosen)
                if offset == 0:
                    for k in WIDTHS:
                        _, direct, _, _ = tree_candidates(
                            q, keys, cast(Tensor, lookup.route_scores), visit=k, use_prior=True
                        )
                        from_scores = lookup.selected if k == 16 else width_parts[k][0]
                        if not torch.equal(direct, from_scores):
                            raise GateViolation(
                                "width",
                                f"width-{k} selection from the captured X16P scores differs from "
                                "tree_candidates on the first batch",
                                {"k": k},
                            )
                        width_check["widths"].append(k)
                    width_check["passed"] = True

        return hook

    x16p = run_rule(
        model,
        panel,
        "X16P",
        hook=reference_hook("X16P", True),
        spy_scores=True,
        expected_targets=expected_targets,
    )
    tick("rule_X16P")
    x16n = run_rule(
        model,
        panel,
        "X16N",
        hook=reference_hook("X16N", False),
        expected_targets=expected_targets,
    )
    tick("rule_X16N")
    passes = {"T2P": t2p, "T2N": t2n, "X16P": x16p, "X16N": x16n}

    for other in (t2n, x16p, x16n):
        if not torch.equal(other.q, t2p.q) or not torch.equal(other.routes, t2p.routes):
            raise GateViolation("i", f"queries or route scores differ under rule {other.rule}")

    # Gate (ii).
    if restricted_failures["rows"] or restricted_failures["branches"]:
        raise GateViolation(
            "ii",
            "T2P differs from the top 8 of X16P restricted to the two visited branches",
            {
                "selection_mismatch_queries": restricted_failures["rows"][:100],
                "selection_mismatch_count": len(restricted_failures["rows"]),
                "visited_branch_mismatch_count": len(restricted_failures["branches"]),
            },
        )
    # Gate (iii).
    violations = lost_rank_violations(x16p.selected, x16p.branches, t2p.selected)
    if violations:
        raise GateViolation(
            "iii",
            "a lost slot lies in a branch of route rank < 3",
            {"count": len(violations), "first": violations[:100]},
        )
    # Gate (iv).
    outside = [d for d in disagreements if d["sets_differ"] and not d["near_tie"]]
    if outside:
        raise GateViolation(
            "iv",
            "frozen and independent reference select different sets outside near-ties",
            {"outside_near_ties": len(outside), "listed": disagreements[:200]},
        )
    tick("gates")

    if not width_check["passed"]:
        raise GateViolation("width", "the width cross-check on the first batch did not run")
    widths = {k: torch.cat(parts) for k, parts in width_parts.items()}
    widths[16] = x16p.selected
    if not torch.equal(widths[2], t2p.selected):
        raise GateViolation("width", "the width-2 selection differs from T2P")

    # Derived measurements.
    counts_p = overlap_counts(t2p.selected, x16p.selected)
    counts_c = overlap_counts(t2p.selected, x16n.selected)
    trained: Tensor | None = None
    coverage_arrays: dict[str, Tensor] = {}
    coverage_record: dict[str, Any] | None = None
    if initial_tensors is not None:
        coverage_arrays = slot_coverage(
            memory.keys.detach(), memory.values.detach(), *initial_tensors
        )
        trained = coverage_arrays["key_changed"] | coverage_arrays["value_changed"]
        coverage_record = coverage_summary(coverage_arrays)

    token_changed = {
        rule: overlap_counts(t2p.selected, passes[rule].selected) < TOP
        for rule in ("T2N", "X16P", "X16N")
    }
    nll = {rule: passes[rule].nll for rule in RULES}
    record: dict[str, Any] = {
        "nll": nll,
        "delta_nll": {
            "restrict": nll["X16P"] - nll["T2P"],
            "prior": nll["T2N"] - nll["T2P"],
            "both": nll["X16N"] - nll["T2P"],
        },
        "recall": {"P": recall_summary(counts_p), "C": recall_summary(counts_c)},
        "recall_by_width": {str(k): _width_recall(widths[k], x16p.selected) for k in WIDTHS},
        "width_curve_method": "visit-k candidates = first 256*k columns of the X16P candidate "
        "scores (route-rank branch order), selected with frozen stable_top; first batch "
        "cross-checked against tree_candidates(visit=k, use_prior=True) for every k",
        "width_cross_check": width_check,
        "certificate": certificate_summary(t2p.values, t2p.routes, t2p.branches, counts_p),
        "coverage": coverage_record,
        "lost": {
            "P": lost_candidates(
                x16p.selected,
                x16p.values,
                x16p.branches,
                t2p.selected,
                t2p.values,
                trained,
                with_scores=True,
            ),
            "C": lost_candidates(
                x16n.selected,
                x16n.values,
                x16n.branches,
                t2p.selected,
                t2p.values,
                trained,
                with_scores=False,
            ),
        },
        "weighted_recall": {
            "P": weighted_recall(x16p.weights, x16p.selected, t2p.selected),
            "C": weighted_recall(x16n.weights, x16n.selected, t2p.selected),
        },
        "prior_effects": prior_effects(t2p.routes, t2p.branches, t2p.selected, t2n.selected),
        "concentration": {
            rule: (
                t2p_concentration
                if rule == "T2P"
                else concentration_report(passes[rule].tracker, rule=rule)
            )
            for rule in RULES
        },
        "token_loss": {
            rule: token_loss_split(t2p.token_loss, passes[rule].token_loss, token_changed[rule])
            for rule in ("T2N", "X16P", "X16N")
        },
    }
    tick("measurements")

    # State, parameters and RNG must be unchanged.
    if (
        state_digest(model) != state_before
        or random.getstate() != python_before
        or not torch.equal(torch.get_rng_state(), torch_before)
        or "lookup" in memory.__dict__
    ):
        raise GateViolation("state", "module state, buffers, RNG or lookup changed by evaluation")

    record["gates"] = {
        "i": {
            "passed": True,
            "recorded_nll": recorded_nll,
            "unmodified_nll": unmodified["nll"],
            "t2p_wrapper_nll": t2p.nll,
            "t2p_concentration_reproduces_p5": True,
        },
        "ii": {
            "passed": True,
            "queries_checked": int(t2p.selected.shape[0]),
            "restricted_score_bitwise_mismatch_queries": restricted_failures["score_mismatch"],
        },
        "iii": {"passed": True},
        "iv": {
            "passed": True,
            "near_tie_threshold": NEAR_TIE,
            "disagreements": disagreements,
            "disagreement_count": len(disagreements),
            "sets_differ_count": sum(1 for d in disagreements if d["sets_differ"]),
        },
        "state_and_rng_unchanged": True,
    }
    record["known_limits"] = list(KNOWN_LIMITS)
    record["phase_seconds"] = phases

    arrays: dict[str, Tensor] = {"q": t2p.q}
    for rule in RULES:
        p = passes[rule]
        arrays[f"selected_ids_{rule}"] = p.selected.to(torch.int16)
        arrays[f"selected_scores_{rule}"] = p.values
        arrays[f"visited_branches_{rule}"] = p.branches.to(torch.int8)
        arrays[f"route_scores_{rule}"] = p.routes
        arrays[f"softmax_weights_{rule}"] = p.weights
        arrays[f"token_loss_{rule}"] = p.token_loss
    for k in WIDTHS:
        if k not in (2, 16):
            arrays[f"selected_ids_width{k}"] = widths[k].to(torch.int16)
    for name, tensor in coverage_arrays.items():
        arrays[f"coverage_{name}"] = (
            tensor.to(torch.uint8) if tensor.dtype is torch.bool else tensor
        )
    return record, arrays
