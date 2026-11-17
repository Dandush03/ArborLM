"""Pilot token-weighted validation and logical retrieval counters."""

import math
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F

from .pilot_config import BATCH_SIZE
from .pilot_model import BRANCHES, PER_BRANCH, SLOTS, TOP, VOCAB, Lookup, PilotModel


class RetrievalCounts:
    def __init__(self, variant: str) -> None:
        self.variant = variant
        self.selected = torch.zeros(SLOTS, dtype=torch.int64)
        self.candidates = torch.zeros(SLOTS, dtype=torch.bool)
        self.top1 = torch.zeros(BRANCHES, dtype=torch.int64)
        self.visited = torch.zeros_like(self.top1)
        self.selected_branches = torch.zeros_like(self.top1)
        self.entropy_sum = 0.0
        self.fallbacks = 0
        self.queries = 0

    def update(self, lookup: Lookup) -> None:
        self.queries += lookup.selected.shape[0]
        self.selected += torch.bincount(lookup.selected.flatten(), minlength=SLOTS)
        if lookup.candidate_ids is None:
            self.candidates.fill_(True)
        elif lookup.exhaustive_queries is not None:
            self.fallbacks += int(lookup.exhaustive_queries.sum())
            if self.fallbacks:
                self.candidates.fill_(True)
            else:
                self.candidates[lookup.candidate_ids.flatten()] = True
        else:
            self.candidates[lookup.candidate_ids.flatten()] = True
        if lookup.branch_ids is not None and lookup.route_scores is not None:
            self.top1 += torch.bincount(lookup.branch_ids[:, 0], minlength=BRANCHES)
            self.visited += torch.bincount(lookup.branch_ids.flatten(), minlength=BRANCHES)
            branches = lookup.selected.flatten() // PER_BRANCH
            self.selected_branches += torch.bincount(branches, minlength=BRANCHES)
            logp = lookup.route_scores.log_softmax(-1).double()
            self.entropy_sum -= float((logp.exp() * logp).sum())

    def report(self) -> dict[str, Any]:
        queries = self.queries
        result: dict[str, Any] = {
            "queries": queries,
            "unique_selected_slots": int((self.selected > 0).sum()),
            "unique_candidate_slots": int(self.candidates.sum()),
            "selected_slot_counts": self.selected.tolist(),
            "hottest_selected_slot_fraction": int(self.selected.max()) / (queries * TOP),
            "logical_value_elements_per_query": TOP * 32,
            "unit_warning": "analytical logical elements/work; not physical I/O or measured FLOPs",
            "router": None,
        }
        if self.variant == "flat":
            result.update(full_key_dots_per_query=4096, logical_key_elements_per_query=4096 * 16)
        elif self.variant == "product_key":
            result.update(
                eight_dim_subkey_dots_per_query=128,
                logical_key_elements_per_query=128 * 8,
                candidate_sums_total=64 * (queries - self.fallbacks) + 4096 * self.fallbacks,
                candidate_sums_histogram={"64": queries - self.fallbacks, "4096": self.fallbacks},
                exhaustive_fallback_queries=self.fallbacks,
                exhaustive_fallback_fraction=self.fallbacks / queries,
            )
        else:
            probs = self.top1.double() / queries
            nonzero = probs[probs > 0]
            result.update(
                router_dots_per_query=16,
                full_key_dots_per_query=512,
                logical_key_elements_per_query=512 * 16,
                logical_router_elements_per_query=16 * 16,
                router={
                    "top1_branch_counts": self.top1.tolist(),
                    "visited_branch_counts": self.visited.tolist(),
                    "selected_value_branch_counts": self.selected_branches.tolist(),
                    "normalized_top1_entropy": float(-(nonzero * nonzero.log()).sum())
                    / math.log(BRANCHES),
                    "mean_normalized_query_router_entropy": self.entropy_sum
                    / (queries * math.log(BRANCHES)),
                    "hottest_top1_branch_fraction": float(probs.max()),
                    "nonzero_top1_branches": int((self.top1 > 0).sum()),
                },
            )
        return result


def loss_for(logits: Tensor, targets: Tensor, reduction: str) -> Tensor:
    return F.cross_entropy(logits.reshape(-1, VOCAB), targets.reshape(-1), reduction=reduction)


def evaluate(model: PilotModel, data: Tensor) -> dict[str, Any]:
    training = model.training
    model.eval()
    tracker = RetrievalCounts(model.variant) if model.memory is not None else None
    nll_sum = 0.0
    count = 0
    try:
        with torch.no_grad():
            for start in range(0, data.shape[0], BATCH_SIZE):
                batch = data[start : start + BATCH_SIZE]
                inputs, targets = batch[:, :-1], batch[:, 1:]
                logits, lookup = model(inputs)
                nll_sum += float(loss_for(logits, targets, "sum"))
                count += targets.numel()
                if tracker is not None and lookup is not None:
                    tracker.update(lookup)
    finally:
        model.train(training)
    nll = nll_sum / count
    if not math.isfinite(nll):
        raise ValueError("non-finite pilot validation loss")
    try:
        ppl = math.exp(nll)
        reason = None
    except OverflowError:
        ppl = None
        reason = "exp(NLL) exceeds floating-point range"
    return {
        "nll": nll,
        "nll_units": "nats_per_byte",
        "byte_perplexity": ppl,
        "perplexity_null_reason": reason,
        "target_tokens": count,
        "retrieval": tracker.report() if tracker is not None else None,
    }
