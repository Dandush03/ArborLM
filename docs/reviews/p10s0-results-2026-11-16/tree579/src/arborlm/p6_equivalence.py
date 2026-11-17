"""P6-E equivalence stage (ADR-0011 section 3.3).

For every checkpoint (flat, fixed tree, learned tree of one parent/seed) this module

1. replays the unmodified model on the P5 panel and requires the registered final NLL bitwise,
   with the snapshot file hash checked before and after;
2. compares every applicable variant with the reference on (a) the full P5 panel through the
   full model, (b) the P5 timing inputs at both registered batch shapes and (c) constructed
   exact-tie fixtures;
3. classifies each comparison STRICT, BOUNDED or NOT_EQUIVALENT exactly per the ADR table.

Nothing here times anything. Status: SPEC: HUMAN-APPROVED (ADR-0011); self-checked only.
"""

import copy
import hashlib
import json
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F

from .longer_training import _isolated_rng
from .p5_config import BATCH, FLAT
from .p5_model import evaluate, insertion_hidden, normalized_query, state_digest
from .p5_timing import inputs_from_rows
from .p6_common import KINDS, CellSource, bits_equal_float
from .p6_retrieval import (
    Binding,
    VariantModel,
    bit_equal,
    build_variant_model,
    variants_for,
)
from .pilot_metrics import loss_for
from .pilot_model import EPS, TEMP, TOP, Lookup, Memory, stable_top

STRICT, BOUNDED, NOT_EQUIVALENT = "STRICT", "BOUNDED", "NOT_EQUIVALENT"
RANK = {STRICT: 0, BOUNDED: 1, NOT_EQUIVALENT: 2}
SCORE_TOLERANCE, LOGIT_TOLERANCE, NLL_TOLERANCE = 1e-5, 1e-4, 1e-6
EXPECTED_CHECKPOINTS = {"F": 27, "T": 54}
GATE_SCOPES = ("a_panel", "b_w8", "b_w1", "c_fixtures")
FIXTURE_SEED = 91001  # implementer-chosen seed for constructed-tie fixtures; not a P5 seed


# ---------------------------------------------------------------------------------------------
# Classification (pure functions, unit tested on hand-built cases)
# ---------------------------------------------------------------------------------------------
def classify(summary: dict[str, Any], scope: str | None = None) -> str:
    """STRICT / BOUNDED / NOT_EQUIVALENT for one comparison summary.

    Quantities that do not apply to a scope (logits, NLL) are ``None`` and are vacuously met.
    Non-finite differences never satisfy a tolerance. On the constructed-tie fixtures (c) the
    variant must also obey the registered tie rule itself: any query on which its selection
    differs from the full-sort oracle (descending score, then ascending slot ID) makes it NOT
    EQUIVALENT, whatever its agreement with the reference.
    """
    if scope == "c_fixtures" and summary.get("tie_rule_violations_variant", 0) > 0:
        return NOT_EQUIVALENT
    identical_selection = summary["selected_mismatch_queries"] == 0
    ids_equal = bool(summary["branch_ids_equal"] and summary["candidate_ids_equal"])
    strict = (
        identical_selection
        and bool(summary["selected_scores_bitwise"])
        and ids_equal
        and bool(summary["route_scores_bitwise"])
        and summary["logits_bitwise"] in (True, None)
        and summary["nll_bitwise"] in (True, None)
    )
    if strict:
        return STRICT
    logits = summary["max_abs_logit_diff"]
    nll = summary["nll_abs_diff"]
    bounded = (
        identical_selection
        and ids_equal
        and summary["max_abs_score_diff"] <= SCORE_TOLERANCE
        and (logits is None or logits <= LOGIT_TOLERANCE)
        and (nll is None or nll <= NLL_TOLERANCE)
    )
    return BOUNDED if bounded else NOT_EQUIVALENT


def worst(classes: Sequence[str]) -> str:
    return max(classes, key=lambda c: RANK[c]) if classes else NOT_EQUIVALENT


# ---------------------------------------------------------------------------------------------
# Reference helpers
# ---------------------------------------------------------------------------------------------
def reference_scores(memory: Memory, q: Tensor) -> tuple[Tensor, Tensor | None]:
    """Candidate scores exactly as the frozen ``Memory.lookup`` computes them (all candidates).

    Returns scores and, for trees, the candidate IDs in the reference order.
    """
    if memory.variant == FLAT:
        return (q @ F.normalize(memory.keys, dim=-1, eps=EPS).T) / TEMP, None
    routes = (q @ F.normalize(memory.router, dim=-1, eps=EPS).T) / TEMP
    _, branch_ids = stable_top(routes, 2)
    indices = (branch_ids[..., None] * 256 + torch.arange(256, device="cpu")).flatten(1)
    local = F.normalize(memory.keys[indices], dim=-1, eps=EPS)
    scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
    prior = routes.log_softmax(-1).gather(-1, branch_ids)
    return scores + prior.repeat_interleave(256, dim=-1), indices


def full_sort_oracle(scores: Tensor, ids: Tensor | None) -> Tensor:
    """Registered rule by sorting everything: descending score, ties by ascending slot ID."""
    if ids is None:
        ids = torch.arange(scores.shape[-1]).expand_as(scores)
    by_id = ids.argsort(dim=-1)
    ordered_scores, ordered_ids = scores.gather(-1, by_id), ids.gather(-1, by_id)
    order = ordered_scores.argsort(dim=-1, descending=True, stable=True)[..., :TOP]
    return ordered_ids.gather(-1, order)


def oracle_selection(scores: Tensor, ids: Tensor | None) -> tuple[Tensor, int]:
    """Registered-rule selection and the number of queries with an exact tie among the top 9.

    A query whose nine largest scores are strictly decreasing has an unambiguous top 8, taken
    from ``topk``. Every query with an exactly equal adjacent pair among the nine largest goes
    through the full sort oracle. Returns the expected IDs and the tie-query count.
    """
    top, positions = scores.topk(TOP + 1, sorted=True)
    ties = (top[:, :-1] == top[:, 1:]).any(dim=-1)
    chosen = positions[:, :TOP]
    expected = chosen if ids is None else ids.gather(-1, chosen)
    expected = expected.clone()
    if bool(ties.any()):
        sub_ids = None if ids is None else ids[ties]
        expected[ties] = full_sort_oracle(scores[ties], sub_ids)
    return expected, int(ties.sum())


def exact_tie_queries(scores: Tensor) -> int:
    """Queries whose top-9 candidate scores contain an exactly equal adjacent pair."""
    return oracle_selection(scores, None)[1]


# ---------------------------------------------------------------------------------------------
# Comparison accumulation
# ---------------------------------------------------------------------------------------------
class MismatchSink:
    """Append-only JSONL of every mismatching query; hashed on close."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.count = 0
        self._stream = path.open("wb")

    def write(self, record: dict[str, Any]) -> None:
        self._stream.write((json.dumps(record, sort_keys=True, allow_nan=False) + "\n").encode())
        self.count += 1

    def close(self) -> str:
        self._stream.flush()
        self._stream.close()
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


@dataclass
class Tally:
    """Accumulates one variant-versus-reference comparison over many calls."""

    queries: int = 0
    selected_mismatch_queries: int = 0
    selected_scores_bitwise: bool = True
    max_abs_score_diff: float = 0.0
    candidate_ids_equal: bool = True
    branch_ids_equal: bool = True
    route_scores_bitwise: bool = True
    logits_seen: bool = False
    logits_bitwise: bool = True
    max_abs_logit_diff: float = 0.0
    nll_ref_sum: float = 0.0
    nll_var_sum: float = 0.0
    targets: int = 0
    oracle_reference_violations: int = 0
    oracle_variant_violations: int = 0
    exact_tie_queries: int = 0
    # Lookup passes and forward passes are logged separately so that nothing is counted twice.
    fallback_lookup: list[list[int]] = field(default_factory=list)
    fallback_forward: list[list[int]] = field(default_factory=list)

    def add_fallbacks(self, pass_name: str, entries: Sequence[tuple[int, int]]) -> None:
        target = self.fallback_lookup if pass_name == "lookup" else self.fallback_forward
        target.extend([int(n), int(f)] for n, f in entries)

    @staticmethod
    def _fallback_summary(entries: list[list[int]]) -> dict[str, Any]:
        queries = sum(n for n, _ in entries)
        flagged = sum(f for _, f in entries)
        return {
            "calls": len(entries),
            "queries": queries,
            "flagged_queries": flagged,
            "fraction": flagged / queries if queries else None,
            "per_call": entries,
        }

    def summary(self) -> dict[str, Any]:
        nll_ref = self.nll_ref_sum / self.targets if self.targets else None
        nll_var = self.nll_var_sum / self.targets if self.targets else None
        nll_diff = nll_bits = None
        if nll_ref is not None and nll_var is not None:
            nll_diff, nll_bits = abs(nll_ref - nll_var), bits_equal_float(nll_ref, nll_var)
        return {
            "queries": self.queries,
            "selected_mismatch_queries": self.selected_mismatch_queries,
            "selected_scores_bitwise": self.selected_scores_bitwise,
            "max_abs_score_diff": self.max_abs_score_diff,
            "candidate_ids_equal": self.candidate_ids_equal,
            "branch_ids_equal": self.branch_ids_equal,
            "route_scores_bitwise": self.route_scores_bitwise,
            "logits_bitwise": self.logits_bitwise if self.logits_seen else None,
            "max_abs_logit_diff": self.max_abs_logit_diff if self.logits_seen else None,
            "nll_reference": nll_ref,
            "nll_variant": nll_var,
            "nll_abs_diff": nll_diff,
            "nll_bitwise": nll_bits,
            "targets": self.targets,
            "tie_rule_violations_reference": self.oracle_reference_violations,
            "tie_rule_violations_variant": self.oracle_variant_violations,
            "queries_with_exact_ties_in_reference_top9": self.exact_tie_queries,
            "guard_fallback_lookup": self._fallback_summary(self.fallback_lookup),
            "guard_fallback_forward": self._fallback_summary(self.fallback_forward),
        }


def _finite(*tensors: Tensor) -> None:
    for tensor in tensors:
        if tensor.dtype.is_floating_point and not bool(tensor.isfinite().all()):
            raise ValueError("P6 stop: non-finite output")


def _max_abs(a: Tensor, b: Tensor) -> float:
    return float((a.double() - b.double()).abs().max()) if a.numel() else 0.0


@dataclass
class ReferenceExtras:
    """Per-call quantities derived from the reference arithmetic, shared by all variants."""

    candidates: Tensor
    ids: Tensor | None
    expected: Tensor
    tie_queries: int


def reference_extras(memory: Memory, q: Tensor) -> ReferenceExtras:
    candidates, ids = reference_scores(memory, q)
    expected, ties = oracle_selection(candidates, ids)
    return ReferenceExtras(candidates, ids, expected, ties)


def update_lookup_tally(
    tally: Tally,
    extras: ReferenceExtras,
    ref: tuple[Tensor, Lookup],
    var: tuple[Tensor, Lookup],
    *,
    offset: int,
    context: dict[str, Any],
    sink: MismatchSink | None,
) -> None:
    ref_scores, ref_look = ref
    var_scores, var_look = var
    _finite(ref_scores, var_scores)
    n = int(ref_look.selected.shape[0])
    rows = (ref_look.selected != var_look.selected).any(dim=-1)
    tally.queries += n
    tally.selected_mismatch_queries += int(rows.sum())
    tally.selected_scores_bitwise &= bit_equal(ref_scores, var_scores)
    tally.max_abs_score_diff = max(tally.max_abs_score_diff, _max_abs(ref_scores, var_scores))
    tally.candidate_ids_equal &= _same_or_none(ref_look.candidate_ids, var_look.candidate_ids)
    tally.branch_ids_equal &= _same_or_none(ref_look.branch_ids, var_look.branch_ids)
    tally.route_scores_bitwise &= _same_or_none(ref_look.route_scores, var_look.route_scores)
    tally.oracle_reference_violations += int(
        (extras.expected != ref_look.selected).any(dim=-1).sum()
    )
    tally.oracle_variant_violations += int((extras.expected != var_look.selected).any(dim=-1).sum())
    tally.exact_tie_queries += extras.tie_queries
    if bool(rows.any()) and sink is not None:
        ordered = extras.candidates.sort(dim=-1, descending=True, stable=True).values[:, : TOP + 1]
        for row in rows.nonzero().flatten().tolist():
            sink.write(
                {
                    **context,
                    "query_index": offset + row,
                    "reference_selected": ref_look.selected[row].tolist(),
                    "variant_selected": var_look.selected[row].tolist(),
                    "reference_selected_scores": ref_scores[row].tolist(),
                    "variant_selected_scores": var_scores[row].tolist(),
                    "reference_top9_scores": ordered[row].tolist(),
                    "reference_gap_8th_9th": float(ordered[row, TOP - 1] - ordered[row, TOP]),
                }
            )


def _same_or_none(a: Tensor | None, b: Tensor | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return bit_equal(a, b)


def compare_batches(
    reference: Any,
    variants: dict[str, VariantModel],
    batches: Sequence[Tensor],
    *,
    targets: bool,
    context: dict[str, Any],
    sink: MismatchSink | None,
) -> dict[str, Tally]:
    """Reference model versus variant models through the full model on token batches.

    ``targets`` True: rows are [B, 65] (input = first 64, target = last 64) and NLL is
    accumulated as in ``p5_model.evaluate``. False: rows are [B, 64] inputs only.
    """
    tallies = {v: Tally() for v in variants}
    memory = reference.addition
    for model in variants.values():
        model.addition.reset_log()
    offset = 0
    with torch.no_grad(), _isolated_rng():
        for batch in batches:
            inputs = batch[:, :-1] if targets else batch
            q = normalized_query(memory, insertion_hidden(reference, inputs))
            ref = memory.lookup(q)
            extras = reference_extras(memory, q)
            ref_logits, _ = reference(inputs)
            _finite(ref_logits)
            ref_nll = float(loss_for(ref_logits, batch[:, 1:], "sum")) if targets else 0.0
            for name, model in variants.items():
                tally = tallies[name]
                log = model.addition.fallback_log
                before = len(log)
                var = model.addition.lookup(q)
                tally.add_fallbacks("lookup", log[before:])
                update_lookup_tally(
                    tally,
                    extras,
                    ref,
                    var,
                    offset=offset,
                    context={**context, "variant": name},
                    sink=sink,
                )
                before = len(log)
                logits, _ = model(inputs)
                tally.add_fallbacks("forward", log[before:])
                _finite(logits)
                tally.logits_seen = True
                tally.logits_bitwise &= bit_equal(ref_logits, logits)
                tally.max_abs_logit_diff = max(
                    tally.max_abs_logit_diff, _max_abs(ref_logits, logits)
                )
                if targets:
                    tally.nll_ref_sum += ref_nll
                    tally.nll_var_sum += float(loss_for(logits, batch[:, 1:], "sum"))
                    tally.targets += int(batch[:, 1:].numel())
            offset += int(q.shape[0])
    return tallies


# ---------------------------------------------------------------------------------------------
# Constructed-tie fixtures (c)
# ---------------------------------------------------------------------------------------------
@dataclass
class FixtureCase:
    name: str
    memory: Memory
    q: Tensor


def _unit(x: Tensor) -> Tensor:
    return F.normalize(x, dim=-1, eps=EPS)


def _copy_memory(source: Memory) -> Memory:
    clone = copy.deepcopy(source)
    clone.eval()
    return clone


def _randint(generator: torch.Generator, low: int, high: int) -> int:
    return int(torch.randint(low, high, (1,), generator=generator))


def build_fixtures(source: Memory, seed: int = FIXTURE_SEED) -> list[FixtureCase]:
    """Exact-tie cases built on copies of a checkpoint's own weights (the source is untouched)."""
    generator = torch.Generator().manual_seed(seed)
    noise = _unit(torch.randn(24, 16, generator=generator))
    cases: list[FixtureCase] = []
    if source.variant == FLAT:
        memory = _copy_memory(source)
        with torch.no_grad():
            queries = []
            for i in range(12):  # two- and three-fold duplicate rows anywhere in the table
                a, b, c = (_randint(generator, 0, 4096) for _ in range(3))
                memory.keys[b] = memory.keys[a]
                if i % 2:
                    memory.keys[c] = memory.keys[a]
                queries.append(_unit(memory.keys[a].detach()))
            base = _randint(generator, 0, 4000)
            for k in range(10):  # a ten-fold tie that straddles the 8th/9th boundary
                memory.keys[base + k] = memory.keys[base]
            queries.append(_unit(memory.keys[base].detach()))
        cases.append(
            FixtureCase("flat_duplicate_rows", memory, torch.cat([torch.stack(queries), noise]))
        )
        return cases

    # Duplicate key rows inside one branch.
    memory = _copy_memory(source)
    queries = []
    with torch.no_grad():
        for branch in range(16):
            first = branch * 256 + _randint(generator, 0, 120)
            second = first + 1 + _randint(generator, 0, 120)
            memory.keys[second] = memory.keys[first]
            if branch % 4 == 0:  # ten-fold tie across the 8th/9th boundary
                for k in range(10):
                    memory.keys[first + 2 + k] = memory.keys[first]
            query = _unit(memory.keys[first].detach())
            memory.router[branch] = query
            queries.append(query)
    cases.append(
        FixtureCase(
            "tree_duplicate_keys_within_branch", memory, torch.cat([torch.stack(queries), noise])
        )
    )

    # Duplicate key rows across the two visited branches with exactly equal route scores.
    memory = _copy_memory(source)
    queries = []
    with torch.no_grad():
        for pair in range(8):
            low, high = 2 * pair, 2 * pair + 1
            first = low * 256 + _randint(generator, 0, 256)
            second = high * 256 + _randint(generator, 0, 256)
            memory.keys[second] = memory.keys[first]
            query = _unit(memory.keys[first].detach())
            memory.router[low] = query
            memory.router[high] = query
            queries.append(query)
    cases.append(
        FixtureCase(
            "tree_duplicate_keys_across_visited_branches",
            memory,
            torch.cat([torch.stack(queries), noise]),
        )
    )

    # Duplicate router rows tying the second and third routed branch.
    memory = _copy_memory(source)
    queries = []
    with torch.no_grad():
        for t in range(4):
            query = _unit(torch.randn(16, generator=generator))
            tied = _unit(query + 0.5 * torch.randn(16, generator=generator))
            memory.router[t] = query
            memory.router[8 + 2 * t] = tied
            memory.router[9 + 2 * t] = tied
            queries.append(query)
    cases.append(
        FixtureCase("tree_duplicate_router_rows", memory, torch.cat([torch.stack(queries), noise]))
    )
    return cases


def compare_fixtures(
    kind: str,
    source: Memory,
    variant_ids: Sequence[str],
    *,
    binding: Binding,
    context: dict[str, Any],
    sink: MismatchSink | None,
) -> dict[str, dict[str, Any]]:
    from .p6_retrieval import build_memory_variant

    tallies = {v: Tally() for v in variant_ids}
    cases = {}
    facts: dict[str, dict[str, int]] = {}
    with torch.no_grad():
        for case in build_fixtures(source):
            wrappers = {
                v: build_memory_variant(case.memory, v, binding=binding) for v in variant_ids
            }
            ref = case.memory.lookup(case.q)
            extras = reference_extras(case.memory, case.q)
            facts[case.name] = fixture_case_facts(case, extras, ref[1])
            for v, wrapper in wrappers.items():
                update_lookup_tally(
                    tallies[v],
                    extras,
                    ref,
                    wrapper.lookup(case.q),
                    offset=0,
                    context={**context, "variant": v, "fixture": case.name},
                    sink=sink,
                )
                tallies[v].add_fallbacks("lookup", wrapper.fallback_log)
            cases[case.name] = int(case.q.shape[0])
    return {
        v: {**t.summary(), "fixture_queries": cases, "fixture_cases": facts, "kind": kind}
        for v, t in tallies.items()
    }


ROUTER_CASE = "tree_duplicate_router_rows"


def fixture_case_facts(case: FixtureCase, extras: ReferenceExtras, ref: Lookup) -> dict[str, int]:
    """Per-case facts that show the constructed fixtures actually contain what they claim."""
    facts = {
        "queries": int(case.q.shape[0]),
        "exact_tie_queries_in_reference_top9": extras.tie_queries,
        "reference_tie_rule_violations": int((extras.expected != ref.selected).any(dim=-1).sum()),
    }
    if case.memory.variant != FLAT:
        routes = (case.q @ F.normalize(case.memory.router, dim=-1, eps=EPS).T) / TEMP
        ordered = routes.sort(dim=-1, descending=True, stable=True).values
        facts["route_ties_rank2_rank3_queries"] = int((ordered[:, 1] == ordered[:, 2]).sum())
    return facts


def check_fixture_integrity(fixtures: dict[str, dict[str, Any]]) -> None:
    """Stop when the constructed fixtures do not test what they are supposed to test.

    The reference must obey the registered tie rule on every fixture; every non-router case must
    contain queries with exact ties in the reference top nine; the router case must contain a
    route tie between rank 2 and rank 3.
    """
    for record in fixtures.values():
        for name, facts in record["fixture_cases"].items():
            if facts["reference_tie_rule_violations"] > 0:
                raise ValueError(f"P6 stop: reference violates the tie rule on fixture {name}")
            if name == ROUTER_CASE:
                if facts["route_ties_rank2_rank3_queries"] == 0:
                    raise ValueError(f"P6 stop: fixture {name} has no route tie at rank 2/3")
            elif facts["exact_tie_queries_in_reference_top9"] == 0:
                raise ValueError(f"P6 stop: fixture {name} has no exact tie in the top nine")
        break  # the facts are properties of the fixtures, identical for every variant


def check_reference_tie_rule(
    scopes: dict[str, dict[str, Tally]], descriptive: dict[str, Tally]
) -> None:
    """Stop when the unmodified reference disagrees with the registered tie-rule oracle."""
    for scope, tallies in (*scopes.items(), ("b_wtok_descriptive", descriptive)):
        for tally in tallies.values():
            if tally.oracle_reference_violations > 0:
                raise ValueError(f"P6 stop: reference violates the tie rule in scope {scope}")


# ---------------------------------------------------------------------------------------------
# One checkpoint and one cell
# ---------------------------------------------------------------------------------------------
def integrity_replay(source: CellSource, kind: str) -> dict[str, Any]:
    """Unmodified model must reproduce the recorded P5 final NLL bitwise."""
    model = source.models[kind]
    measured = evaluate(model, source.panel, source.expected_targets)["nll"]
    recorded = source.recorded[kind]["nll"]
    record = {
        "recorded_final_nll": recorded,
        "replayed_nll": measured,
        "bitwise_equal": bits_equal_float(measured, recorded),
    }
    if not record["bitwise_equal"]:
        raise ValueError(f"P6 stop: integrity replay mismatch for {source.label} {kind}")
    return record


def panel_batches(panel: Tensor) -> list[Tensor]:
    return [panel[start : start + BATCH] for start in range(0, panel.shape[0], BATCH)]


def run_checkpoint(
    source: CellSource,
    kind: str,
    sink: MismatchSink,
    *,
    binding: Binding = "hash",
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    model = source.models[kind]
    model.eval()
    emit = on_event or (lambda _event: None)
    state_before, python_rng, torch_rng = (
        state_digest(model),
        random.getstate(),
        torch.get_rng_state(),
    )
    file_before = source.files_unchanged()
    integrity = integrity_replay(source, kind)
    emit({"event": "integrity_replay", "label": source.label, "kind": kind, **integrity})
    variants = {v: build_variant_model(model, v, binding=binding) for v in variants_for(kind)}
    context = {"label": source.label, "kind": kind}
    inputs = inputs_from_rows(source.train)
    scopes: dict[str, dict[str, Tally]] = {
        "a_panel": compare_batches(
            model,
            variants,
            panel_batches(source.panel),
            targets=True,
            context={**context, "scope": "a_panel"},
            sink=sink,
        )
    }
    for size in (8, 1):
        scopes[f"b_w{size}"] = compare_batches(
            model,
            variants,
            list(inputs[size]),
            targets=False,
            context={**context, "scope": f"b_w{size}"},
            sink=sink,
        )
    descriptive = compare_batches(
        model,
        variants,
        [x[:, :1] for x in inputs[1]],
        targets=False,
        context={**context, "scope": "b_wtok_descriptive"},
        sink=sink,
    )
    fixtures = compare_fixtures(
        kind,
        model.addition,  # type: ignore[arg-type]
        list(variants),
        binding=binding,
        context={**context, "scope": "c_fixtures"},
        sink=sink,
    )
    for variant in variants.values():
        variant.addition.verify_source()
    check_reference_tie_rule(scopes, descriptive)
    check_fixture_integrity(fixtures)
    state_unchanged = (
        state_digest(model) == state_before
        and random.getstate() == python_rng
        and torch.equal(torch_rng, torch.get_rng_state())
    )
    if not state_unchanged:
        raise ValueError(f"P6 stop: model state, buffers or RNG changed for {source.label} {kind}")
    if not (file_before and source.files_unchanged()):
        raise ValueError(f"P6 stop: checkpoint file hash changed for {source.label} {kind}")
    records: dict[str, Any] = {}
    for name in variants:
        summaries = {scope: tallies[name].summary() for scope, tallies in scopes.items()}
        summaries["c_fixtures"] = fixtures[name]
        classes = {scope: classify(s, scope) for scope, s in summaries.items()}
        records[name] = {
            "class": worst([classes[scope] for scope in GATE_SCOPES]),
            "scope_classes": classes,
            "scopes": summaries,
            "descriptive_wtok": descriptive[name].summary(),
            "persistent_extra_bytes": variants[name].addition.persistent_extra_bytes,
        }
        emit(
            {
                "event": "variant_classified",
                "label": source.label,
                "kind": kind,
                "variant": name,
                "class": records[name]["class"],
            }
        )
    record = {
        "kind": kind,
        "integrity": integrity,
        "checkpoint_files_unchanged_before_and_after": True,
        "model_state_and_rng_unchanged": True,
        "binding": binding,
        "variants": records,
    }
    # Persisted immediately so that a later breach in the same worker keeps this checkpoint.
    emit({"event": "checkpoint_record", "label": source.label, **record})
    return record


def run_cell(
    source: CellSource,
    run_dir: Path,
    *,
    binding: Binding = "hash",
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    sink = MismatchSink(run_dir / "mismatches.jsonl")
    try:
        checkpoints = {
            kind: run_checkpoint(source, kind, sink, binding=binding, on_event=on_event)
            for kind in KINDS
        }
    finally:
        digest = sink.close()
    return {
        "pair": list(source.pair),
        "label": source.label,
        "synthetic": source.synthetic,
        "checkpoints": checkpoints,
        "mismatch_file": {"name": "mismatches.jsonl", "sha256": digest, "records": sink.count},
    }


# ---------------------------------------------------------------------------------------------
# Gate over all checkpoints
# ---------------------------------------------------------------------------------------------
def gate(cells: Sequence[dict[str, Any]], *, expected_cells: int = 27) -> dict[str, Any]:
    """EQ(v): STRICT or BOUNDED on all of the variant's checkpoints, on (a), (b) and (c)."""
    per_variant: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        for kind, checkpoint in cell["checkpoints"].items():
            for variant, record in checkpoint["variants"].items():
                # A missing gate scope is NOT_EQUIVALENT, never silently skipped.
                scope_classes = {
                    scope: (
                        classify(record["scopes"][scope], scope)
                        if scope in record["scopes"]
                        else NOT_EQUIVALENT
                    )
                    for scope in GATE_SCOPES
                }
                per_variant.setdefault(variant, []).append(
                    {
                        "label": cell["label"],
                        "kind": kind,
                        "class": worst(list(scope_classes.values())),
                        "scope_classes": scope_classes,
                    }
                )
    result: dict[str, Any] = {}
    for variant, rows in sorted(per_variant.items()):
        expected = expected_cells * (1 if variant.startswith("F") else 2)
        counts = {c: sum(r["class"] == c for r in rows) for c in (STRICT, BOUNDED, NOT_EQUIVALENT)}
        complete = len(rows) == expected
        result[variant] = {
            "checkpoints": len(rows),
            "expected_checkpoints": expected,
            "counts": counts,
            "overall_class": worst([r["class"] for r in rows]),
            "EQ": complete and counts[NOT_EQUIVALENT] == 0,
            "complete": complete,
            "not_equivalent": [r for r in rows if r["class"] == NOT_EQUIVALENT],
        }
    return result


def timing_eligibility(gated: dict[str, Any]) -> dict[str, Any]:
    from .p6_analysis import eligibility_from_gate

    return eligibility_from_gate(gated)


# ---------------------------------------------------------------------------------------------
# Worker and stage runner
# ---------------------------------------------------------------------------------------------
def equivalence_worker(spec: dict[str, Any], child: Path, pair: tuple[int, int, int]) -> None:
    from .engine import configure_cpu
    from .io import write_json
    from .p6_common import KNOWN_LIMITS, StudyArgs, compact_evidence, load_cell
    from .p6_stage import verify_source_unchanged
    from .records import append_event

    args = StudyArgs.from_json(spec["args"])
    configure_cpu()
    source = load_cell(args, pair, child)
    try:
        result = run_cell(source, child, binding="hash", on_event=lambda e: append_event(child, e))
        source_recheck = verify_source_unchanged(child, spec["source"])
    except Exception as exc:
        write_json(
            child / "result.json", {"outcome": "failed", "error": f"{type(exc).__name__}: {exc}"}
        )
        raise
    write_json(
        child / "result.json",
        {
            "outcome": "completed",
            **result,
            "dry_run": args.dry_run,
            "checkpoint_evidence": compact_evidence(source),
            "source_recheck_at_worker_end": source_recheck,
            "known_limits": list(KNOWN_LIMITS),
        },
    )


def load_cells(compact_dir: Path) -> list[dict[str, Any]]:
    """Completed per-worker equivalence records of one stage run, in file order."""
    from .io import read_json

    records = [
        read_json(path)
        for path in sorted((compact_dir / "workers").glob("b*-o*-s*.json"))
        if not path.name.endswith((".terminal.json", ".manifest.json"))
    ]
    # A failed worker leaves a failure marker, not a cell record; it is never gated.
    return [record for record in records if record.get("outcome") == "completed"]


def run_equivalence_stage(args: Any, argv: list[str]) -> int:
    from .io import canonical_json, write_json
    from .p6_stage import finish_stage, open_stage, run_worker_stage, source_expectations

    context = open_stage(
        "equivalence",
        output_root=args.output_root,
        results_root=args.results_root,
        argv=argv,
        arguments=args.to_json(),
        dry_run=args.dry_run,
        supersede=args.supersede,
        supersede_reason=args.supersede_reason,
    )
    spec = {
        "mode": "equivalence",
        "args": args.to_json(),
        "source": source_expectations(context),
    }
    write_json(context.run / "stage-spec.json", spec)
    write_json(context.compact / "stage-spec.json", spec)

    def argv_for(pair: tuple[int, int, int], child: Path) -> list[str]:
        import sys

        return [
            sys.executable,
            "-m",
            "arborlm.p6_retrieval_study",
            "_worker",
            str(context.run / "stage-spec.json"),
            str(child),
            *map(str, pair),
        ]

    outcome = run_worker_stage(context, args.pair_list(), argv_for=argv_for)
    cells = load_cells(context.compact)
    gated = gate(cells, expected_cells=len(args.pair_list()))
    status, reason = outcome.status, outcome.reason
    if status == "completed" and len(cells) != len(args.pair_list()):
        status, reason = "failed", "equivalence records missing for some workers"
    result = {
        "stage": "equivalence",
        "workers": outcome.rows,
        "completed_workers": len(cells),
        "gate": gated,
        "eligibility": timing_eligibility(gated),
        "peak_stage_process_tree_rss_bytes": outcome.peak_rss_bytes,
        "stage_wall_seconds": outcome.wall_seconds,
        "mismatch_files": {c["label"]: c["mismatch_file"] for c in cells if "mismatch_file" in c},
    }
    finish_stage(context, status, reason, result)
    print(
        canonical_json(
            {"stage": "equivalence", "run": context.run.name, "status": status, "reason": reason}
        )
        .decode()
        .strip(),
        flush=True,
    )
    return 0 if status == "completed" else 1
