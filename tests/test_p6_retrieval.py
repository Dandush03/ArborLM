"""Synthetic tests for P6-E (ADR-0011 Part E). No real checkpoint, panel or outcome is used.

Every number in this file is either a hand calculation or a measurement on random synthetic
tensors; none is evidence about the registered study.
"""

import copy
import inspect
import itertools
import json
import random
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import pytest
import torch
from torch import Tensor
from torch.nn import functional as nnf

from arborlm import p5_timing
from arborlm import p6_analysis as an
from arborlm import p6_common as common
from arborlm import p6_equivalence as eq
from arborlm import p6_retrieval as rv
from arborlm import p6_retrieval_study as cli
from arborlm import p6_stage as stage
from arborlm import p6_timing_study as ts
from arborlm.p2_config import BACKBONES, ORDERS
from arborlm.p5_config import FIXED, FLAT, LEARNED, SEEDS, Cell
from arborlm.p5_model import evaluate, state_digest
from arborlm.pilot_model import EPS, TOP, Lookup, Memory

REPO = Path(__file__).resolve().parents[1]
TREE_KINDS = (FIXED, LEARNED)
ALL_KINDS = (FLAT, *TREE_KINDS)
STRICT_PREDICTED = {"F1", "T1", "T2"}  # ADR E-H1 and the F1 definition predict bitwise scores
TOLERANCE = 1e-5


# ---------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------
def make_memory(kind: str, seed: int = 7) -> Memory:
    """A registered-shape ``Memory`` with random (not trained) keys and router rows."""
    generator = torch.Generator().manual_seed(seed)
    memory = Memory(kind, 501).eval()
    with torch.no_grad():
        memory.keys.copy_(torch.randn(4096, 16, generator=generator))
        memory.values.copy_(torch.randn(4096, 32, generator=generator) * 0.1)
        if kind != FLAT:
            memory.router.copy_(torch.randn(16, 16, generator=generator))
    return memory


def make_queries(count: int = 512, seed: int = 11) -> Tensor:
    generator = torch.Generator().manual_seed(seed)
    return nnf.normalize(torch.randn(count, 16, generator=generator), dim=-1, eps=EPS)


def variants_of(kind: str) -> tuple[str, ...]:
    return rv.variants_for(kind)


def run_lookup(wrapper: Any, q: Tensor) -> tuple[Tensor, Lookup]:
    with torch.no_grad():
        return wrapper.lookup(q)  # type: ignore[no-any-return]


def assert_same_contract(
    ref: tuple[Tensor, Lookup], var: tuple[Tensor, Lookup], *, bitwise_scores: bool
) -> None:
    ref_scores, ref_look = ref
    var_scores, var_look = var
    assert torch.equal(ref_look.selected, var_look.selected)  # IDs and order
    if ref_look.branch_ids is None:
        assert var_look.branch_ids is None and var_look.candidate_ids is None
        assert var_look.route_scores is None
    else:
        assert var_look.branch_ids is not None and var_look.candidate_ids is not None
        assert var_look.route_scores is not None
        assert rv.bit_equal(ref_look.branch_ids, var_look.branch_ids)
        assert rv.bit_equal(ref_look.candidate_ids, var_look.candidate_ids)  # type: ignore[arg-type]
        assert rv.bit_equal(ref_look.route_scores, var_look.route_scores)  # type: ignore[arg-type]
    if bitwise_scores:
        assert rv.bit_equal(ref_scores, var_scores)
    else:
        assert float((ref_scores - var_scores).abs().max()) <= TOLERANCE


@pytest.fixture(scope="module")
def memories() -> dict[str, Memory]:
    return {kind: make_memory(kind) for kind in ALL_KINDS}


# ---------------------------------------------------------------------------------------------
# Variants versus the reference on random fixtures
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_every_variant_matches_reference_on_random_queries(
    memories: dict[str, Memory], kind: str
) -> None:
    memory = memories[kind]
    q = make_queries()
    with torch.no_grad():
        ref = memory.lookup(q)
    assert variants_of(kind) == (("F1", "F2") if kind == FLAT else ("T1", "T2", "T3", "T4", "T5"))
    for variant in variants_of(kind):
        wrapper = rv.build_memory_variant(memory, variant)
        assert_same_contract(
            ref, run_lookup(wrapper, q), bitwise_scores=variant in STRICT_PREDICTED
        )


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_forward_matches_reference_and_scores_are_not_rescaled(
    memories: dict[str, Memory], kind: str
) -> None:
    memory = memories[kind]
    generator = torch.Generator().manual_seed(5)
    h = torch.randn(8, 64, 32, generator=generator)
    with torch.no_grad():
        ref_out, ref_look = memory(h)
        for variant in variants_of(kind):
            out, look = rv.build_memory_variant(memory, variant)(h)
            assert torch.equal(ref_look.selected, look.selected)
            if variant in STRICT_PREDICTED:
                assert rv.bit_equal(ref_out, out)
            assert float((ref_out - out).abs().max()) <= 1e-4


def test_branch_ids_and_candidate_ids_keep_reference_rank_order(
    memories: dict[str, Memory],
) -> None:
    memory = memories[FIXED]
    q = make_queries()
    with torch.no_grad():
        _, ref = memory.lookup(q)
    assert ref.branch_ids is not None and ref.candidate_ids is not None
    # The fixture must actually distinguish rank order from ID order.
    assert bool((ref.branch_ids[:, 0] > ref.branch_ids[:, 1]).any())
    for variant in variants_of(FIXED):
        _, look = run_lookup(rv.build_memory_variant(memory, variant), q)
        assert look.branch_ids is not None and look.candidate_ids is not None
        assert torch.equal(look.branch_ids, ref.branch_ids)
        top1 = look.route_scores.argmax(dim=-1)  # type: ignore[union-attr]
        assert torch.equal(look.branch_ids[:, 0], top1)
        assert torch.equal(look.candidate_ids, ref.candidate_ids)
        assert torch.equal(look.candidate_ids[:, 0] // 256, ref.branch_ids[:, 0])


def test_division_by_temperature_not_reciprocal_multiplication() -> None:
    source = inspect.getsource(rv)
    assert not re.search(r"\*\s*\(?\s*1(\.0)?\s*/\s*TEMP", source)
    assert "RECIP" not in source and "* 5.0" not in source and "* 5)" not in source
    assert source.count("/ TEMP") >= 3


def test_variants_apply_to_the_right_kind_only(memories: dict[str, Memory]) -> None:
    with pytest.raises(ValueError, match="does not apply"):
        rv.build_memory_variant(memories[FLAT], "T1")
    with pytest.raises(ValueError, match="does not apply"):
        rv.build_memory_variant(memories[FIXED], "F1")
    with pytest.raises(ValueError, match="unregistered"):
        rv.build_memory_variant(memories[FIXED], "T6")
    with pytest.raises(ValueError):
        rv.variants_for("dense")


def test_persistent_extra_bytes_hand_calculation(memories: dict[str, Memory]) -> None:
    key_table = 4096 * 16 * 4  # normalized key table, float32
    router_table = 16 * 16 * 4  # normalized router, float32
    offsets = 256 * 8  # arange(256), int64
    assert key_table == 262144
    for variant in ("F1", "F2"):
        assert rv.build_memory_variant(memories[FLAT], variant).persistent_extra_bytes == key_table
    for variant in ("T1", "T2", "T3", "T4", "T5"):
        wrapper = rv.build_memory_variant(memories[FIXED], variant)
        assert wrapper.persistent_extra_bytes == key_table + router_table + offsets


def test_construction_records_cache_build_and_binding_times(memories: dict[str, Memory]) -> None:
    wrapper = rv.build_memory_variant(memories[FIXED], "T2")
    assert wrapper.build_ns > 0 and wrapper.bind_ns > 0


# ---------------------------------------------------------------------------------------------
# Selection kernel
# ---------------------------------------------------------------------------------------------
def test_first_occurrence_top_matches_stable_sort_with_heavy_ties() -> None:
    generator = torch.Generator().manual_seed(3)
    scores = torch.randint(0, 6, (200, 300), generator=generator).float()  # many exact ties
    values, positions = rv.first_occurrence_top(scores, TOP + 1)
    order = scores.argsort(dim=-1, descending=True, stable=True)[:, : TOP + 1]
    assert torch.equal(positions, order)
    assert torch.equal(values, scores.gather(-1, order))


def test_first_occurrence_top_hand_case() -> None:
    row = torch.tensor([[1.0, 5.0, 5.0, 3.0, 5.0, 2.0]])
    values, positions = rv.first_occurrence_top(row, 4)
    assert positions.tolist() == [[1, 2, 4, 3]]  # three equal maxima: lowest position first
    assert values.tolist() == [[5.0, 5.0, 5.0, 3.0]]
    assert row.tolist() == [[1.0, 5.0, 5.0, 3.0, 5.0, 2.0]]  # input untouched


# ---------------------------------------------------------------------------------------------
# Constructed exact ties (registered rule: descending score, then ascending slot ID)
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_constructed_tie_fixtures_obey_the_tie_rule(memories: dict[str, Memory], kind: str) -> None:
    cases = eq.build_fixtures(memories[kind])
    expected_names = (
        ["flat_duplicate_rows"]
        if kind == FLAT
        else [
            "tree_duplicate_keys_within_branch",
            "tree_duplicate_keys_across_visited_branches",
            "tree_duplicate_router_rows",
        ]
    )
    assert [c.name for c in cases] == expected_names
    for case in cases:
        with torch.no_grad():
            ref = case.memory.lookup(case.q)
        scores, ids = eq.reference_scores(case.memory, case.q)
        _, ties = eq.oracle_selection(scores, ids)
        if case.name == "tree_duplicate_router_rows":
            # The tie is between routers 8+2t and 9+2t for the second visited branch (t < 4):
            # equal route scores, resolved to the lower branch ID.
            routes = ref[1].route_scores
            assert routes is not None and ref[1].branch_ids is not None
            for t in range(4):
                assert routes[t, 8 + 2 * t] == routes[t, 9 + 2 * t]
                assert ref[1].branch_ids[t].tolist() == [t, 8 + 2 * t]
        else:
            assert ties > 0, f"{case.name}: fixture did not construct an exact tie"
        # The frozen reference itself obeys the registered rule on every query.
        assert torch.equal(ref[1].selected, eq.full_sort_oracle(scores, ids))
        for variant in variants_of(kind):
            wrapper = rv.build_memory_variant(case.memory, variant)
            var = run_lookup(wrapper, case.q)
            assert torch.equal(var[1].selected, eq.full_sort_oracle(scores, ids)), (
                case.name,
                variant,
            )
            assert_same_contract(ref, var, bitwise_scores=variant in STRICT_PREDICTED)


def test_hand_built_tie_orders_by_ascending_slot_id() -> None:
    memory = make_memory(FLAT)
    with torch.no_grad():
        for slot in (900, 30, 2500, 31):  # four identical rows
            memory.keys[slot] = memory.keys[30]
        q = nnf.normalize(memory.keys[30:31], dim=-1, eps=EPS)
        ref = memory.lookup(q)
    scores = ref[0][0]
    tied = [i for i in range(TOP) if bool(scores[i] == scores[0])]
    assert len(tied) >= 4  # the four identical rows are tied for the top
    assert ref[1].selected[0, :4].tolist() == [30, 31, 900, 2500]  # ascending slot ID
    for variant in ("F1", "F2"):
        out = run_lookup(rv.build_memory_variant(memory, variant), q)
        assert out[1].selected[0, :4].tolist() == [30, 31, 900, 2500]
        assert torch.equal(out[1].selected, ref[1].selected)


def test_exact_tie_across_visited_branches_prefers_lower_slot_id() -> None:
    memory = make_memory(FIXED)
    with torch.no_grad():
        memory.keys[3 * 256 + 17] = memory.keys[5 * 256 + 40]  # duplicate across branches 3 and 5
        direction = nnf.normalize(memory.keys[5 * 256 + 40 : 5 * 256 + 41], dim=-1, eps=EPS)
        memory.router[3] = direction[0]
        memory.router[5] = direction[0]  # equal route scores: equal prior
        ref = memory.lookup(direction)
    assert ref[1].branch_ids is not None and ref[1].branch_ids[0].tolist() == [3, 5]
    assert ref[1].selected[0, 0].item() == 3 * 256 + 17 and ref[1].selected[0, 1].item() == (
        5 * 256 + 40
    )
    for variant in variants_of(FIXED):
        var = run_lookup(rv.build_memory_variant(memory, variant), direction)
        assert var[1].selected[0, :2].tolist() == [3 * 256 + 17, 5 * 256 + 40]
        assert torch.equal(var[1].selected, ref[1].selected)


def test_duplicate_router_rows_fix_the_branch_order_by_lower_branch_id() -> None:
    memory = make_memory(FIXED)
    with torch.no_grad():
        q = make_queries(1)
        memory.router[11] = q[0]  # the unique top route
        memory.router[6] = nnf.normalize(q + 0.3 * make_queries(1, 99), dim=-1, eps=EPS)[0]
        memory.router[9] = memory.router[6]  # second place tied between branches 6 and 9
        ref = memory.lookup(q)
    assert ref[1].branch_ids is not None and ref[1].branch_ids[0].tolist() == [11, 6]
    for variant in variants_of(FIXED):
        var = run_lookup(rv.build_memory_variant(memory, variant), q)
        assert var[1].branch_ids is not None and var[1].branch_ids[0].tolist() == [11, 6]
        assert torch.equal(var[1].selected, ref[1].selected)


# ---------------------------------------------------------------------------------------------
# Guard band
# ---------------------------------------------------------------------------------------------
def near_tie_memory() -> tuple[Memory, Tensor]:
    """Slots 10 and 200 of one branch differ in score by about 1e-5, less than the guard band."""
    memory = make_memory(FIXED)
    branch = 4
    first, second = branch * 256 + 10, branch * 256 + 200
    with torch.no_grad():
        q = nnf.normalize(memory.keys[first : first + 1], dim=-1, eps=EPS)
        orthogonal = torch.randn(1, 16, generator=torch.Generator().manual_seed(1))
        orthogonal -= (orthogonal @ q.T) * q
        orthogonal = nnf.normalize(orthogonal, dim=-1, eps=EPS)
        memory.keys[second] = q[0] + 2e-3 * orthogonal[0]  # cosine lower by about 2e-6
        memory.router[branch] = q[0]
        queries = torch.cat([q, make_queries(63, 21)])
    return memory, queries


def test_guard_band_flags_near_ties_and_returns_reference_selection() -> None:
    memory, queries = near_tie_memory()
    with torch.no_grad():
        ref = memory.lookup(queries)
    with torch.no_grad():
        scores, ids = eq.reference_scores(memory, queries)
    top = scores.topk(TOP + 1, sorted=True).values
    gaps = top[:, :-1] - top[:, 1:]
    assert 0 < float(gaps[0].min()) < rv.GUARD_DELTA  # the near-tie is not an exact tie
    for variant in ("T3", "T4", "T5"):
        wrapper = rv.build_memory_variant(memory, variant)
        var = run_lookup(wrapper, queries)
        assert torch.equal(var[1].selected, ref[1].selected)
        assert len(wrapper.fallback_log) == 1
        count, flagged = wrapper.fallback_log[0]
        assert count == 64 and flagged >= 1
        assert wrapper.fallback_fraction() == flagged / 64
        # Flagged queries use T2 arithmetic, so they are bitwise equal to the reference.
        assert rv.bit_equal(var[0][0], ref[0][0])


class _NoisyT3(rv.T3):
    """T3 whose contraction carries a deterministic error below the guard band (test only)."""

    def _contract(self, q: Tensor, ordered: Tensor) -> Tensor:
        return super()._contract(q, ordered) + torch.linspace(0.0, 5e-5, 512)


def test_guard_band_is_what_protects_the_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    memory, queries = near_tie_memory()
    with torch.no_grad():
        ref = memory.lookup(queries)
    guarded = _NoisyT3(memory, "T3")
    assert torch.equal(run_lookup(guarded, queries)[1].selected, ref[1].selected)
    assert guarded.fallback_fraction() is not None and guarded.fallback_fraction() > 0
    # Without the guard (delta 0) the same arithmetic error flips the near-tie.
    monkeypatch.setattr(rv, "GUARD_DELTA", 0.0)
    unguarded = _NoisyT3(memory, "T3")
    flipped = run_lookup(unguarded, queries)[1].selected
    assert not torch.equal(flipped, ref[1].selected)
    assert unguarded.fallback_fraction() == 0.0


def test_exact_ties_force_the_fallback_for_every_guarded_variant() -> None:
    memory = make_memory(FIXED)
    cases = {c.name: c for c in eq.build_fixtures(memory)}
    case = cases["tree_duplicate_keys_within_branch"]
    for variant in ("T3", "T4", "T5"):
        wrapper = rv.build_memory_variant(case.memory, variant)
        run_lookup(wrapper, case.q)
        _, flagged = wrapper.fallback_log[0]
        assert flagged >= 16  # all sixteen constructed queries contain an exact tie
    flat_case = eq.build_fixtures(make_memory(FLAT))[0]
    f2 = rv.build_memory_variant(flat_case.memory, "F2")
    run_lookup(f2, flat_case.q)
    assert f2.fallback_log[0][1] >= 1  # F2's tie-safety fallback triggers on the ten-fold tie


def test_fallback_log_is_per_call_and_resettable(memories: dict[str, Memory]) -> None:
    wrapper = rv.build_memory_variant(memories[FIXED], "T5")
    q = make_queries(64)
    run_lookup(wrapper, q)
    run_lookup(wrapper, q[:10])
    assert [n for n, _ in wrapper.fallback_log] == [64, 10]
    wrapper.reset_log()
    assert wrapper.fallback_log == [] and wrapper.fallback_fraction() is None
    assert rv.build_memory_variant(memories[FIXED], "T2").fallback_fraction() is None


# ---------------------------------------------------------------------------------------------
# Inference-only, binding, non-mutation
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_refuses_grad_enabled_and_training_mode(memories: dict[str, Memory], kind: str) -> None:
    memory = memories[kind]
    q = make_queries(8)
    h = torch.randn(1, 8, 32)
    for variant in variants_of(kind):
        wrapper = rv.build_memory_variant(memory, variant)
        with pytest.raises(RuntimeError, match="gradients are enabled"):
            wrapper.lookup(q)
        with pytest.raises(RuntimeError, match="gradients are enabled"):
            wrapper(h)
        with torch.no_grad():
            wrapper.train()
            with pytest.raises(RuntimeError, match="training mode"):
                wrapper.lookup(q)
            wrapper.eval()
            wrapper.lookup(q)  # runs again once back in eval mode
        with torch.inference_mode():
            wrapper.lookup(q)  # inference mode also satisfies the guard
    local = copy.deepcopy(memory)
    wrapper = rv.build_memory_variant(local, variants_of(kind)[0])
    local.train()  # the wrapped module in training mode
    with torch.no_grad(), pytest.raises(RuntimeError, match="training mode"):
        wrapper.lookup(q)


def test_wrapper_train_and_eval_never_touch_the_wrapped_module(
    memories: dict[str, Memory],
) -> None:
    local = copy.deepcopy(memories[FIXED])
    wrapper = rv.build_memory_variant(local, "T2")
    wrapper.train()
    assert local.training is False
    local.train()
    wrapper.eval()
    assert local.training is True


def test_variant_model_refuses_when_source_model_trains() -> None:
    cell = common.load_synthetic_cell((101, 301, 501), rows=2)
    model = cell.models[FIXED]
    wrapped = rv.build_variant_model(model, "T2")
    tokens = cell.panel[:2, :64]
    with torch.no_grad():
        wrapped(tokens)
        model.train()
        with pytest.raises(RuntimeError, match="training mode"):
            wrapped(tokens)
    model.eval()
    with torch.enable_grad(), pytest.raises(RuntimeError, match="gradients are enabled"):
        wrapped(tokens)


@pytest.mark.parametrize("binding", ["hash", "fingerprint"])
def test_cache_is_bound_to_the_source_tensors(binding: str) -> None:
    memory = make_memory(FIXED)
    wrapper = rv.build_memory_variant(memory, "T2", binding=binding)  # type: ignore[arg-type]
    q = make_queries(8)
    run_lookup(wrapper, q)
    with torch.no_grad():
        memory.keys[5, 3] += 1e-3  # in-place change of one bound element
    with pytest.raises(RuntimeError, match="source tensors changed"):
        run_lookup(wrapper, q)


@pytest.mark.parametrize("binding", ["hash", "fingerprint"])
def test_cache_rejects_a_replaced_or_resized_router(binding: str) -> None:
    memory = make_memory(LEARNED)
    wrapper = rv.build_memory_variant(memory, "T5", binding=binding)  # type: ignore[arg-type]
    run_lookup(wrapper, make_queries(8))
    memory.router = torch.nn.Parameter(memory.router.detach().clone())  # same bytes, new tensor
    if binding == "fingerprint":
        with pytest.raises(RuntimeError, match="source tensors changed"):
            run_lookup(wrapper, make_queries(8))
    else:
        run_lookup(wrapper, make_queries(8))  # identical bytes still match the recorded hash
        with torch.no_grad():
            memory.router[0, 0] += 1.0
        with pytest.raises(RuntimeError, match="source tensors changed"):
            run_lookup(wrapper, make_queries(8))


def test_digest_changes_with_name_shape_and_bytes() -> None:
    a = torch.arange(6, dtype=torch.float32)
    base = rv.tensors_digest({"x": a})
    assert base == rv.tensors_digest({"x": a.clone()})
    assert base != rv.tensors_digest({"y": a})
    assert base != rv.tensors_digest({"x": a.reshape(2, 3)})
    changed = a.clone()
    changed[3] = torch.nextafter(changed[3], torch.tensor(10.0))  # one ULP
    assert base != rv.tensors_digest({"x": changed})
    assert rv.tensors_digest({"x": a.double()}) != base


def test_bit_equal_distinguishes_signed_zero_and_one_ulp() -> None:
    zero, negative = torch.tensor([0.0]), torch.tensor([-0.0])
    assert torch.equal(zero, negative) and not rv.bit_equal(zero, negative)
    one = torch.tensor([1.0])
    assert not rv.bit_equal(one, torch.nextafter(one, torch.tensor([2.0])))
    assert not rv.bit_equal(one, one.double())


def _module_fingerprint(memory: Memory) -> tuple[Any, ...]:
    state = {k: v.clone() for k, v in memory.state_dict().items()}
    buffers = {k: v.clone() for k, v in memory.named_buffers()}
    versions = {k: v._version for k, v in itertools.chain(memory.named_parameters())}
    return state, buffers, versions, memory.training, random.getstate(), torch.get_rng_state()


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_variants_do_not_mutate_the_wrapped_module_or_rng(kind: str) -> None:
    memory = make_memory(kind)
    q = make_queries(64)
    h = torch.randn(2, 32, 32)
    before = _module_fingerprint(memory)
    with torch.no_grad():
        for variant in variants_of(kind):
            wrapper = rv.build_memory_variant(memory, variant)
            wrapper.lookup(q)
            wrapper(h)
            wrapper.verify_source()
    after = _module_fingerprint(memory)
    assert all(torch.equal(before[0][k], after[0][k]) for k in before[0])
    assert all(torch.equal(before[1][k], after[1][k]) for k in before[1])
    assert before[2] == after[2]  # no in-place write bumped any parameter version
    assert before[3] == after[3] and before[4] == after[4]
    assert torch.equal(before[5], after[5])


def test_wrapper_registers_no_parameters_or_buffers(memories: dict[str, Memory]) -> None:
    wrapper = rv.build_memory_variant(memories[FIXED], "T4")
    assert list(wrapper.parameters()) == [] and list(wrapper.buffers()) == []
    assert all(not t.requires_grad for t in wrapper.caches.values())


# ---------------------------------------------------------------------------------------------
# Full-model use in the three P5 timing scopes
# ---------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cell() -> common.CellSource:
    return common.load_synthetic_cell((101, 301, 501), rows=16)


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_variant_models_match_reference_logits_and_nll(cell: common.CellSource, kind: str) -> None:
    model = cell.models[kind]
    tokens = cell.panel[:8, :64]
    with torch.no_grad():
        ref_logits, ref_look = model(tokens)
        for variant in variants_of(kind):
            wrapped = rv.build_variant_model(model, variant)
            logits, look = wrapped(tokens)
            assert ref_look is not None and look is not None
            assert torch.equal(ref_look.selected, look.selected)
            assert float((ref_logits - logits).abs().max()) <= 1e-4
            if variant in STRICT_PREDICTED:
                assert rv.bit_equal(ref_logits, logits)
            assert wrapped.memory is wrapped.addition
            assert wrapped.addition.source is model.addition


def test_variant_model_works_in_all_three_timing_scopes(cell: common.CellSource) -> None:
    model = cell.models[FIXED]
    entities = {"fixed_tree:T0": model, "fixed_tree:T5": rv.build_variant_model(model, "T5")}
    inputs = ts.workload_inputs(cell.train)
    result = ts.run_timing(entities, inputs, 0, rounds=1)
    seen = {(r["workload"], r["scope"], r["entity"]) for r in result["records"]}
    expected = {(w, s, e) for w in ts.WORKLOADS for s in ts.scopes_for(w) for e in entities}
    assert seen == expected
    assert all(len(r["durations_ns"]) == 10 for r in result["records"])
    t5 = [r for r in result["records"] if r["entity"] == "fixed_tree:T5"]
    assert all("guard_fallback_fraction" in r for r in t5)
    assert all(len(r["guard_fallback_per_timed_call"]) == 10 for r in t5)
    t0 = [r for r in result["records"] if r["entity"] == "fixed_tree:T0"]
    assert all("guard_fallback_fraction" not in r for r in t0)


def test_p5_helper_functions_accept_a_wrapper(cell: common.CellSource) -> None:
    from arborlm.p5_model import insertion_hidden, normalized_query

    model = cell.models[FIXED]
    wrapper = rv.build_memory_variant(model.addition, "T1")  # type: ignore[arg-type]
    h = insertion_hidden(model, cell.panel[:2, :64])
    with torch.no_grad():
        assert torch.equal(normalized_query(wrapper, h), normalized_query(model.addition, h))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------------
# Classification (hand-built cases)
# ---------------------------------------------------------------------------------------------
def summary(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "selected_mismatch_queries": 0,
        "selected_scores_bitwise": True,
        "max_abs_score_diff": 0.0,
        "candidate_ids_equal": True,
        "branch_ids_equal": True,
        "route_scores_bitwise": True,
        "logits_bitwise": True,
        "max_abs_logit_diff": 0.0,
        "nll_abs_diff": 0.0,
        "nll_bitwise": True,
    }
    return {**base, **overrides}


def test_classification_table_hand_cases() -> None:
    assert eq.classify(summary()) == eq.STRICT
    assert eq.classify(summary(logits_bitwise=None, nll_bitwise=None)) == eq.STRICT  # (b), (c)
    bounded_base = {"selected_scores_bitwise": False, "nll_bitwise": False, "logits_bitwise": False}
    cases = [
        (dict(max_abs_score_diff=1e-5, max_abs_logit_diff=1e-4, nll_abs_diff=1e-6), eq.BOUNDED),
        (dict(max_abs_score_diff=1.0001e-5), eq.NOT_EQUIVALENT),
        (dict(max_abs_score_diff=5e-6, max_abs_logit_diff=1.01e-4), eq.NOT_EQUIVALENT),
        (dict(max_abs_score_diff=5e-6, nll_abs_diff=1.1e-6), eq.NOT_EQUIVALENT),
        (dict(max_abs_score_diff=5e-6, selected_mismatch_queries=1), eq.NOT_EQUIVALENT),
        (dict(max_abs_score_diff=5e-6, branch_ids_equal=False), eq.NOT_EQUIVALENT),
        (dict(max_abs_score_diff=5e-6, candidate_ids_equal=False), eq.NOT_EQUIVALENT),
        (dict(max_abs_score_diff=float("nan")), eq.NOT_EQUIVALENT),
    ]
    for overrides, expected in cases:
        assert eq.classify(summary(**{**bounded_base, **overrides})) == expected, overrides
    # Any single bitwise failure demotes STRICT to BOUNDED when within tolerance.
    for key in ("selected_scores_bitwise", "route_scores_bitwise", "logits_bitwise", "nll_bitwise"):
        assert eq.classify(summary(**{key: False})) == eq.BOUNDED, key
    # A single selection mismatch is never BOUNDED, even with bitwise scores elsewhere.
    assert eq.classify(summary(selected_mismatch_queries=1)) == eq.NOT_EQUIVALENT
    assert eq.worst([eq.STRICT, eq.BOUNDED]) == eq.BOUNDED
    assert eq.worst([eq.STRICT, eq.NOT_EQUIVALENT, eq.BOUNDED]) == eq.NOT_EQUIVALENT
    assert eq.worst([]) == eq.NOT_EQUIVALENT


def hand_extras(expected: Tensor) -> eq.ReferenceExtras:
    # Twelve candidates per query; boundary gap (8th - 9th) is 5 - 4.5 = 0.5 by hand.
    row = torch.tensor([12.0, 11, 10, 9, 8, 7, 6, 5, 4.5, 1, 0, -1])
    return eq.ReferenceExtras(row.repeat(4, 1), None, expected, 0)


def hand_lookup(selected: Tensor) -> tuple[Tensor, Lookup]:
    scores = torch.arange(8, 0, -1, dtype=torch.float32).repeat(selected.shape[0], 1)
    return scores, Lookup(selected, None)


def test_one_mismatching_query_is_classified_and_recorded(tmp_path: Path) -> None:
    selected = torch.arange(8).repeat(4, 1)
    variant_selected = selected.clone()
    variant_selected[2, :2] = torch.tensor([1, 0])  # query 2: order of the first two swapped
    tally, sink = eq.Tally(), eq.MismatchSink(tmp_path / "mismatches.jsonl")
    eq.update_lookup_tally(
        tally,
        hand_extras(selected),
        hand_lookup(selected),
        hand_lookup(variant_selected),
        offset=100,
        context={"label": "hand", "variant": "X"},
        sink=sink,
    )
    digest = sink.close()
    out = tally.summary()
    assert out["queries"] == 4 and out["selected_mismatch_queries"] == 1
    assert out["tie_rule_violations_reference"] == 0 and out["tie_rule_violations_variant"] == 1
    assert eq.classify({**out, "logits_bitwise": None, "nll_bitwise": None}) == eq.NOT_EQUIVALENT
    (line,) = (tmp_path / "mismatches.jsonl").read_text().splitlines()
    record = json.loads(line)
    assert record["query_index"] == 102  # offset 100 + row 2
    assert record["reference_selected"] == list(range(8))
    assert record["variant_selected"] == [1, 0, 2, 3, 4, 5, 6, 7]
    assert record["reference_selected_scores"] == [8.0, 7, 6, 5, 4, 3, 2, 1]
    assert record["reference_gap_8th_9th"] == 0.5
    assert record["reference_top9_scores"][:2] == [12.0, 11.0]
    assert sink.count == 1 and len(digest) == 64


def test_identical_lookup_is_strict_and_writes_no_mismatch(tmp_path: Path) -> None:
    selected = torch.arange(8).repeat(4, 1)
    tally, sink = eq.Tally(), eq.MismatchSink(tmp_path / "m.jsonl")
    eq.update_lookup_tally(
        tally,
        hand_extras(selected),
        hand_lookup(selected),
        hand_lookup(selected.clone()),
        offset=0,
        context={},
        sink=sink,
    )
    sink.close()
    out = tally.summary()
    assert out["selected_mismatch_queries"] == 0 and sink.count == 0
    assert eq.classify({**out, "logits_bitwise": None, "nll_bitwise": None}) == eq.STRICT


def test_non_finite_outputs_stop() -> None:
    selected = torch.arange(8).repeat(4, 1)
    bad = hand_lookup(selected)
    bad[0][1, 1] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        eq.update_lookup_tally(
            eq.Tally(),
            hand_extras(selected),
            hand_lookup(selected),
            bad,
            offset=0,
            context={},
            sink=None,
        )


def test_fast_oracle_equals_full_sort_oracle_on_tie_heavy_scores() -> None:
    generator = torch.Generator().manual_seed(2)
    scores = torch.randint(0, 5, (300, 512), generator=generator).float()
    ids = torch.stack([torch.randperm(512, generator=generator) for _ in range(300)])
    expected, ties = eq.oracle_selection(scores, ids)
    assert torch.equal(expected, eq.full_sort_oracle(scores, ids))
    assert ties == 300  # integer-valued scores always tie
    distinct = torch.randn(50, 512, generator=generator)
    expected, ties = eq.oracle_selection(distinct, None)
    assert ties == 0 and torch.equal(expected, eq.full_sort_oracle(distinct, None))


# ---------------------------------------------------------------------------------------------
# Equivalence stage on a synthetic fixture
# ---------------------------------------------------------------------------------------------
def test_integrity_replay_requires_the_recorded_nll_bitwise() -> None:
    source = common.load_synthetic_cell((101, 301, 501), rows=8)
    assert eq.integrity_replay(source, FIXED)["bitwise_equal"] is True
    source.recorded[FIXED]["nll"] = float(
        torch.nextafter(
            torch.tensor(source.recorded[FIXED]["nll"], dtype=torch.float64),
            torch.tensor(9.0, dtype=torch.float64),
        )
    )
    with pytest.raises(ValueError, match="integrity replay mismatch"):
        eq.integrity_replay(source, FIXED)


def test_equivalence_cell_on_synthetic_fixture(tmp_path: Path) -> None:
    source = common.load_synthetic_cell((101, 301, 501), rows=16)
    events: list[dict[str, Any]] = []
    result = eq.run_cell(source, tmp_path, binding="hash", on_event=events.append)
    assert result["mismatch_file"]["records"] == 0
    for kind, checkpoint in result["checkpoints"].items():
        assert checkpoint["integrity"]["bitwise_equal"] is True
        assert checkpoint["checkpoint_files_unchanged_before_and_after"] is True
        assert set(checkpoint["variants"]) == set(variants_of(kind))
        for variant, record in checkpoint["variants"].items():
            assert record["class"] in (eq.STRICT, eq.BOUNDED), (kind, variant)
            assert set(record["scope_classes"]) == set(eq.GATE_SCOPES)
            panel = record["scopes"]["a_panel"]
            assert panel["queries"] == 16 * 64 and panel["targets"] == 16 * 64
            assert record["scopes"]["b_w8"]["queries"] == 4 * 8 * 64
            assert record["scopes"]["b_w1"]["queries"] == 4 * 64
            assert "descriptive_wtok" in record
            if variant in STRICT_PREDICTED:
                assert record["class"] == eq.STRICT
    kinds = [e["kind"] for e in events if e["event"] == "checkpoint_record"]
    assert kinds == list(common.KINDS)  # each checkpoint persisted as soon as it finishes
    t5 = result["checkpoints"][FIXED]["variants"]["T5"]["scopes"]["a_panel"]
    # Lookup passes and forward passes are reported separately: one of each per 8-row batch.
    lookup, forward = t5["guard_fallback_lookup"], t5["guard_fallback_forward"]
    assert lookup["calls"] == forward["calls"] == 16 // 8
    assert lookup["queries"] == forward["queries"] == 16 * 64
    assert lookup["fraction"] is not None and forward["fraction"] is not None
    assert sum(f for _, f in lookup["per_call"]) == lookup["flagged_queries"]
    assert sum(f for _, f in forward["per_call"]) == forward["flagged_queries"]
    assert "guard_fallback_fraction" not in t5 and "guard_fallback_queries" not in t5
    t2 = result["checkpoints"][FIXED]["variants"]["T2"]["scopes"]["a_panel"]
    assert (
        t2["guard_fallback_lookup"]["fraction"] is None
        and t2["guard_fallback_forward"]["calls"] == 0
    )
    fixtures = result["checkpoints"][FIXED]["variants"]["T5"]["scopes"]["c_fixtures"]
    assert fixtures["guard_fallback_forward"]["calls"] == 0  # fixtures only run lookups
    assert fixtures["guard_fallback_lookup"]["calls"] == 3  # one lookup per tree fixture case
    assert sum(e["event"] == "variant_classified" for e in events) == 2 + 5 + 5


class _WrongOrder(rv.T2):
    """Swaps the first two selected slots of query 3 (test-only defect)."""

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        values, look = super()._lookup(q)
        if q.shape[0] > 3:
            look.selected = look.selected.clone()
            look.selected[3, :2] = look.selected[3, :2].flip(0)
        return values, look


class _Mutating(rv.T2):
    """Writes to the wrapped module's values on every call (test-only defect)."""

    def _lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        self.source.values.mul_(1.0000001)
        return super()._lookup(q)


def test_one_wrong_query_makes_the_variant_not_equivalent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(rv.REGISTRY, "T2", _WrongOrder)
    source = common.load_synthetic_cell((101, 301, 501), rows=8)
    sink = eq.MismatchSink(tmp_path / "m.jsonl")
    record = eq.run_checkpoint(source, FIXED, sink)
    sink.close()
    assert record["variants"]["T2"]["class"] == eq.NOT_EQUIVALENT
    assert record["variants"]["T1"]["class"] == eq.STRICT
    assert sink.count > 0
    first = json.loads((tmp_path / "m.jsonl").read_text().splitlines()[0])
    assert first["variant"] == "T2" and "reference_gap_8th_9th" in first
    cells = [{"label": "x", "checkpoints": {FIXED: record, LEARNED: record}}]
    gated = eq.gate(cells, expected_cells=1)
    assert gated["T2"]["EQ"] is False and gated["T2"]["counts"][eq.NOT_EQUIVALENT] == 2
    assert gated["T1"]["EQ"] is True
    eligibility = an.eligibility_from_gate(gated)
    assert "T2" not in eligibility["tree_variants"] and "T1" in eligibility["tree_variants"]


def test_state_mutation_stops_the_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(rv.REGISTRY, "T2", _Mutating)
    source = common.load_synthetic_cell((101, 301, 501), rows=4)
    sink = eq.MismatchSink(tmp_path / "m.jsonl")
    with pytest.raises(ValueError, match="state, buffers or RNG changed"):
        eq.run_checkpoint(source, FIXED, sink)
    sink.close()


def test_gate_requires_every_checkpoint_and_all_scopes() -> None:
    def record(klass: dict[str, str]) -> dict[str, Any]:
        scopes = {
            s: summary(max_abs_score_diff=0.0 if c == eq.STRICT else 5e-6, **_flags(c))
            for s, c in klass.items()
        }
        return {"scopes": scopes}

    def _flags(c: str) -> dict[str, Any]:
        if c == eq.STRICT:
            return {}
        if c == eq.BOUNDED:
            return {"selected_scores_bitwise": False}
        return {"selected_mismatch_queries": 1}

    strict = dict.fromkeys(eq.GATE_SCOPES, eq.STRICT)
    one_bounded = {**strict, "b_w1": eq.BOUNDED}
    one_bad = {**strict, "c_fixtures": eq.NOT_EQUIVALENT}

    def cell(label: str, per_kind: dict[str, dict[str, str]]) -> dict[str, Any]:
        return {
            "label": label,
            "checkpoints": {k: {"variants": {"T3": record(v)}} for k, v in per_kind.items()},
        }

    good = [
        cell("a", {FIXED: strict, LEARNED: one_bounded}),
        cell("b", {FIXED: strict, LEARNED: strict}),
    ]
    gated = eq.gate(good, expected_cells=2)["T3"]
    assert gated["EQ"] and gated["counts"] == {"STRICT": 3, "BOUNDED": 1, "NOT_EQUIVALENT": 0}
    assert gated["overall_class"] == eq.BOUNDED and gated["expected_checkpoints"] == 4
    bad = [cell("a", {FIXED: strict, LEARNED: one_bad}), good[1]]
    assert not eq.gate(bad, expected_cells=2)["T3"]["EQ"]  # one scope on one checkpoint fails
    assert not eq.gate(good[:1], expected_cells=2)["T3"]["EQ"]  # missing checkpoints: incomplete
    assert eq.gate(good[:1], expected_cells=2)["T3"]["complete"] is False


def test_a_missing_gate_scope_is_not_equivalent_never_skipped() -> None:
    full = {s: summary() for s in eq.GATE_SCOPES}

    def cells(scopes: dict[str, Any]) -> list[dict[str, Any]]:
        checkpoint = {"variants": {"T3": {"scopes": scopes}}}
        return [{"label": "a", "checkpoints": {FIXED: checkpoint, LEARNED: checkpoint}}]

    assert eq.gate(cells(full), expected_cells=1)["T3"]["EQ"] is True
    for missing in eq.GATE_SCOPES:
        scopes = {k: v for k, v in full.items() if k != missing}
        gated = eq.gate(cells(scopes), expected_cells=1)["T3"]
        assert gated["EQ"] is False, missing
        assert gated["counts"][eq.NOT_EQUIVALENT] == 2
        assert all(
            r["scope_classes"][missing] == eq.NOT_EQUIVALENT for r in gated["not_equivalent"]
        )


def test_the_tie_rule_gates_fixture_scope_c_only() -> None:
    violating = summary(tie_rule_violations_variant=1, tie_rule_violations_reference=0)
    assert eq.classify(violating) == eq.STRICT  # no scope given: the base classes only
    assert eq.classify(violating, "a_panel") == eq.STRICT  # (a) and (b) gate on the reference
    assert eq.classify(violating, "b_w8") == eq.STRICT
    assert eq.classify(violating, "c_fixtures") == eq.NOT_EQUIVALENT
    assert eq.classify(summary(tie_rule_violations_variant=0), "c_fixtures") == eq.STRICT
    # Through the gate: a variant agreeing with a (hypothetically wrong) reference but breaking
    # the tie rule on the fixtures is excluded.
    scopes = {s: summary() for s in eq.GATE_SCOPES}
    scopes["c_fixtures"] = violating
    checkpoint = {"variants": {"T3": {"scopes": scopes}}}
    gated = eq.gate(
        [{"label": "a", "checkpoints": {FIXED: checkpoint, LEARNED: checkpoint}}], expected_cells=1
    )
    assert gated["T3"]["EQ"] is False


def fixture_record(name: str, **facts: int) -> dict[str, dict[str, Any]]:
    base = {
        "queries": 28,
        "exact_tie_queries_in_reference_top9": 5,
        "reference_tie_rule_violations": 0,
        "route_ties_rank2_rank3_queries": 3,
    }
    return {"T1": {"fixture_cases": {name: {**base, **facts}}}}


def test_fixture_integrity_stops_when_fixtures_do_not_test_ties() -> None:
    eq.check_fixture_integrity(fixture_record("tree_duplicate_keys_within_branch"))
    eq.check_fixture_integrity(
        fixture_record(eq.ROUTER_CASE, exact_tie_queries_in_reference_top9=0)
    )
    with pytest.raises(ValueError, match="violates the tie rule"):
        eq.check_fixture_integrity(
            fixture_record("flat_duplicate_rows", reference_tie_rule_violations=1)
        )
    with pytest.raises(ValueError, match="no exact tie"):
        eq.check_fixture_integrity(
            fixture_record("flat_duplicate_rows", exact_tie_queries_in_reference_top9=0)
        )
    with pytest.raises(ValueError, match="no route tie at rank 2/3"):
        eq.check_fixture_integrity(fixture_record(eq.ROUTER_CASE, route_ties_rank2_rank3_queries=0))


def test_reference_tie_rule_violation_in_any_scope_stops() -> None:
    clean, dirty = eq.Tally(), eq.Tally()
    dirty.oracle_reference_violations = 1
    eq.check_reference_tie_rule({"a_panel": {"T1": clean}}, {"T1": clean})
    with pytest.raises(ValueError, match="violates the tie rule in scope b_w8"):
        eq.check_reference_tie_rule(
            {"a_panel": {"T1": clean}, "b_w8": {"T1": dirty}}, {"T1": clean}
        )
    with pytest.raises(ValueError, match="b_wtok_descriptive"):
        eq.check_reference_tie_rule({"a_panel": {"T1": clean}}, {"T1": dirty})


@pytest.mark.parametrize("kind", [FLAT, FIXED])
def test_real_fixtures_contain_what_the_integrity_check_requires(kind: str) -> None:
    memory = make_memory(kind)
    fixtures = eq.compare_fixtures(
        kind, memory, list(variants_of(kind)), binding="hash", context={}, sink=None
    )
    eq.check_fixture_integrity(fixtures)  # must not raise on the constructed fixtures
    cases = next(iter(fixtures.values()))["fixture_cases"]
    assert all(c["reference_tie_rule_violations"] == 0 for c in cases.values())
    if kind == FIXED:
        assert cases[eq.ROUTER_CASE]["route_ties_rank2_rank3_queries"] > 0


# ---------------------------------------------------------------------------------------------
# Analysis: hand-calculated numbers
# ---------------------------------------------------------------------------------------------
PAIRS = an.PAIRS
RES = 1.0  # clock resolution in ns for the hand-built records


def durations(value: float | list[float]) -> list[int]:
    """80 raw samples; a list gives one constant per round (8 rounds x 10 calls)."""
    per_round = value if isinstance(value, list) else [value] * 8
    return [int(v) for v in per_round for _ in range(10)]


def worker(pair: tuple[int, int, int], table: dict[tuple[str, str, str], Any]) -> dict[str, Any]:
    records = [
        {
            "workload": w,
            "scope": s,
            "entity": e,
            "durations_ns": durations(v),
            "resolution_ns": RES,
        }
        for (w, s, e), v in table.items()
    ]
    return {"pair": list(pair), "rounds": 8, "timing": {"records": records}}


def workers(
    base: dict[tuple[str, str, str], Any],
    overrides: dict[tuple[int, int, int], dict[tuple[str, str, str], Any]] | None = None,
) -> list[dict[str, Any]]:
    overrides = overrides or {}
    return [worker(p, {**base, **overrides.get(p, {})}) for p in PAIRS]


A, F = an.ADDITION, an.FORWARD
T0, V, C, F0 = "fixed_tree:T0", "fixed_tree:T2", "flat:F1", "flat:F0"


def speed(addition_v: float, ratio_forward: float = 1.0) -> dict[tuple[str, str, str], Any]:
    """Entity medians in ns: T0 100000/200000; V and the comparator C as given."""
    return {
        ("W8", A, T0): 100_000,
        ("W8", F, T0): 200_000,
        ("W8", A, V): addition_v,
        ("W8", F, V): 200_000 * ratio_forward,
        ("W8", A, C): 100_000,
        ("W8", F, C): 200_000,
        ("W8", A, F0): 100_000,
        ("W8", F, F0): 200_000,
    }


def test_summarize_rounds_reuses_the_p5_reliability_rule() -> None:
    generator = random.Random(4)
    for _ in range(20):
        rounds = [[generator.randint(900, 1500) for _ in range(10)] for _ in range(8)]
        ours = an.summarize_rounds(rounds, 1.0)
        # Everything P5 reports is reproduced; the only addition is the nearest-rank p50.
        assert {k: v for k, v in ours.items() if k != "p50_ns"} == p5_timing.summarize(rounds, 1.0)
        ordered = sorted(x for row in rounds for x in row)
        assert ours["p50_ns"] == ordered[39]  # nearest rank: ceil(80 * 0.5) = 40th sample
        assert ours["median_ns"] == statistics.median(ordered)  # ratios keep the P5 median
    with pytest.raises(ValueError, match="repetition"):
        an.summarize_rounds([[1] * 10] * 7, 1.0)
    with pytest.raises(ValueError, match="repetition"):
        an.summarize_rounds([[1] * 9] * 8, 1.0)


def test_reliability_rule_hand_cases() -> None:
    ok = an.summarize_rounds([[1000] * 10] * 8, 1.0)
    assert ok["usable"] and ok["round_median_ratio"] == 1.0
    unstable = an.summarize_rounds([[1000] * 10] * 7 + [[1300] * 10], 1.0)  # ratio 1.3 > 1.25
    assert (
        unstable["usable"] is False and unstable["reliability_criteria"]["stable_rounds"] is False
    )
    edge = an.summarize_rounds([[1000] * 10] * 7 + [[1250] * 10], 1.0)  # ratio exactly 1.25
    assert edge["usable"] is True
    tiny = an.summarize_rounds([[99] * 10] * 8, 1.0)  # median < 100 x resolution
    assert tiny["reliability_criteria"]["above_clock_resolution"] is False and not tiny["usable"]
    zero = an.summarize_rounds([[0] * 10] * 8, 1.0)
    assert zero["reliability_criteria"]["positive_durations"] is False and not zero["usable"]


def test_sp_all_clauses_pass_with_hand_numbers() -> None:
    # All 27 ratios 40000/100000 = 0.4: GM 0.4 <= 0.5, 27 >= 26 below 1, 9/9 parents below 1.
    indexed = an.index_workers(workers(speed(40_000)))
    sp = an.speedup_criterion(indexed, V, T0)
    clauses = sp["addition_forward"]
    assert sp["status"] == "PASS"
    assert clauses["geometric_mean"]["value"] == pytest.approx(0.4)
    assert clauses["cells"]["count"] == 27 and clauses["parents"]["count"] == 9


def test_sp_geometric_mean_clause_fails_alone() -> None:
    sp = an.speedup_criterion(an.index_workers(workers(speed(51_000))), V, T0)  # ratio 0.51
    clauses = sp["addition_forward"]
    assert sp["status"] == "FAIL"
    assert not clauses["geometric_mean"]["pass"]
    assert clauses["cells"]["pass"] and clauses["parents"]["pass"]


def test_sp_cell_clause_fails_alone_at_25_of_27() -> None:
    # Two pairs at ratio 1.0 (not < 1): 25/27 < 26 required. GM = 0.4^(25/27) = 0.428 <= 0.5.
    over = {PAIRS[0]: {("W8", A, V): 100_000}, PAIRS[1]: {("W8", A, V): 100_000}}
    sp = an.speedup_criterion(an.index_workers(workers(speed(40_000), over)), V, T0)
    clauses = sp["addition_forward"]
    assert clauses["cells"]["count"] == 25 and not clauses["cells"]["pass"]
    assert clauses["geometric_mean"]["pass"] and clauses["parents"]["pass"]  # parent GM 0.737 < 1
    assert clauses["geometric_mean"]["value"] == pytest.approx(0.4 ** (25 / 27))
    assert sp["status"] == "FAIL"


def test_sp_one_slow_pair_still_passes_cells_but_a_slow_parent_fails() -> None:
    # One pair at ratio 1.0: 26/27 meets the cell clause; its parent GM is 0.4^(2/3) < 1.
    one = {PAIRS[0]: {("W8", A, V): 100_000}}
    ok = an.speedup_criterion(an.index_workers(workers(speed(40_000), one)), V, T0)
    assert ok["addition_forward"]["cells"]["count"] == 26 and ok["status"] == "PASS"
    # One pair at ratio 5 (cells 26/27 still below 1) drags its parent GM to
    # (5 * 0.99 * 0.99)^(1/3) = 1.699 > 1, so the 9/9 parent clause fails alone.
    parent = PAIRS[:3]  # b101 o301, seeds 501..503
    over = {
        parent[0]: {("W8", A, V): 500_000},
        parent[1]: {("W8", A, V): 99_000},
        parent[2]: {("W8", A, V): 99_000},
    }
    sp = an.speedup_criterion(an.index_workers(workers(speed(40_000), over)), V, T0)
    clauses = sp["addition_forward"]
    assert clauses["cells"]["count"] == 26 and clauses["cells"]["pass"]
    assert clauses["parents"]["count"] == 8 and not clauses["parents"]["pass"]
    first_parent = clauses["parents"]["parent_geometric_means"][0]["geometric_mean"]
    assert first_parent == pytest.approx((5 * 0.99 * 0.99) ** (1 / 3))
    assert clauses["geometric_mean"]["pass"]  # 0.47 <= 0.5
    assert sp["status"] == "FAIL"


def test_unreliable_or_incomplete_measurements_are_inconclusive_never_pass_or_fail() -> None:
    unstable = {("W8", A, V): [40_000] * 7 + [52_000]}  # round-median ratio 1.3 > 1.25
    indexed = an.index_workers(workers(speed(40_000), {PAIRS[5]: unstable}))
    sp = an.speedup_criterion(indexed, V, T0)
    assert sp["status"] == "INCONCLUSIVE"
    assert sp["addition_forward"]["reliable"] is False
    # The point estimate is still reported and the clauses are still evaluated separately.
    assert sp["addition_forward"]["geometric_mean"]["pass"] is True
    short = an.index_workers(workers(speed(40_000))[:26])
    assert an.speedup_criterion(short, V, T0)["status"] == "INCOMPLETE"
    below_resolution = {("W8", A, V): 50}  # median < 100 x resolution
    tiny = an.index_workers(workers(speed(40_000), {PAIRS[0]: below_resolution}))
    assert an.speedup_criterion(tiny, V, T0)["status"] == "INCONCLUSIVE"


def test_par_and_pr_clauses_with_hand_numbers() -> None:
    def verdict(add: float, forward: float) -> dict[str, Any]:
        indexed = an.index_workers(workers(speed(add, forward / 1.0)))
        return an.comparator_criteria(indexed, V, C)

    # addition ratio 0.7, forward ratio 1.0: parity and practicality both hold.
    out = verdict(70_000, 1.0)
    assert out["PAR"]["status"] == "PASS" and out["PR"]["status"] == "PASS"
    # addition 0.9: parity yes (<= 1.00); PR's gm clause fails alone (0.9 > 0.80).
    out = verdict(90_000, 1.0)
    assert out["PAR"]["status"] == "PASS" and out["PR"]["status"] == "FAIL"
    pr = out["PR"]["addition_forward"]
    assert not pr["geometric_mean"]["pass"] and pr["cells"]["pass"] and pr["parents"]["pass"]
    assert out["PR"]["model_forward"]["geometric_mean"]["pass"]
    # addition exactly equal to flat (ratio 1.0): PAR counts ratio <= 1.00, PR needs ratio < 1.
    out = verdict(100_000, 1.0)
    par = out["PAR"]["addition_forward"]
    assert (
        par["geometric_mean"]["pass"]
        and par["cells"]["count"] == 27
        and par["parents"]["count"] == 9
    )
    pr = out["PR"]["addition_forward"]
    assert pr["cells"]["count"] == 0 and not pr["cells"]["pass"] and not pr["parents"]["pass"]
    assert out["PAR"]["status"] == "PASS" and out["PR"]["status"] == "FAIL"
    # forward ratio 1.10 > 1.05: both model_forward clause groups fail, additions untouched.
    out = verdict(70_000, 1.10)
    assert out["PAR"]["status"] == "FAIL" and out["PR"]["status"] == "FAIL"
    assert out["PAR"]["addition_forward"]["geometric_mean"]["pass"]
    assert not out["PAR"]["model_forward"]["geometric_mean"]["pass"]
    # forward ratio 1.04 passes the 1.05 margin.
    assert verdict(70_000, 1.04)["PR"]["status"] == "PASS"


def test_par_cell_and_parent_clauses_count_exactly() -> None:
    # Five pairs at addition ratio 1.5 (> 1.0): 22/27 pairs <= 1.00 meets the cell clause
    # exactly; six slow pairs give 21/27 and fail it. Slow pairs spread over distinct parents
    # (one each in the first five parents) so parent geometric means stay below 1.00 until
    # their group ratio crosses it: 1.5 * 0.7 * 0.7 = 0.735 < 1 for every parent.
    slow5 = {PAIRS[3 * i]: {("W8", A, V): 150_000} for i in range(5)}
    base = speed(70_000)
    out = an.comparator_criteria(an.index_workers(workers(base, slow5)), V, C)["PAR"]
    add = out["addition_forward"]
    assert add["cells"]["count"] == 22 and add["cells"]["pass"] and add["parents"]["count"] == 9
    slow6 = {**slow5, PAIRS[15]: {("W8", A, V): 150_000}}
    out6 = an.comparator_criteria(an.index_workers(workers(base, slow6)), V, C)["PAR"]
    assert out6["addition_forward"]["cells"]["count"] == 21
    assert not out6["addition_forward"]["cells"]["pass"]
    # Parent clause: two parents (six pairs) with all three pairs slow -> 7/9 parents <= 1.00.
    two_parents = {p: {("W8", A, V): 150_000} for p in PAIRS[:6]}
    out2 = an.comparator_criteria(an.index_workers(workers(base, two_parents)), V, C)["PAR"]
    assert out2["addition_forward"]["parents"]["count"] == 7
    assert not out2["addition_forward"]["parents"]["pass"]
    assert out2["addition_forward"]["cells"]["count"] == 21


def test_comparison_against_f0_is_reported_alongside() -> None:
    table = {**speed(70_000), ("W8", A, F0): 140_000, ("W8", A, C): 100_000}
    indexed = an.index_workers(workers(table))
    comparator = an.comparator_criteria(indexed, V, C)
    uncached = an.comparator_criteria(indexed, V, F0)
    assert comparator["PR"]["addition_forward"]["geometric_mean"]["value"] == pytest.approx(0.7)
    assert uncached["PR"]["addition_forward"]["geometric_mean"]["value"] == pytest.approx(0.5)


def eligibility(trees: tuple[str, ...], flats: tuple[str, ...]) -> dict[str, Any]:
    return {"flat_variants": ["F0", *flats], "tree_variants": ["T0", *trees]}


def screen_table() -> dict[tuple[str, str, str], Any]:
    """Hand-built T-screen medians (ns) at W8 addition_forward for both tree kinds."""
    table: dict[tuple[str, str, str], Any] = {}
    medians = {"T0": 100_000, "T1": 80_000, "T2": 60_000, "T3": 60_000, "T4": 55_000, "T5": 70_000}
    for kind in TREE_KINDS:
        for variant, value in medians.items():
            table[("W8", A, f"{kind}:{variant}")] = value
    for variant, value in {"F0": 50_000, "F1": 45_000, "F2": 45_000}.items():
        table[("W8", A, f"flat:{variant}")] = value
    return table


def test_selection_rule_hand_calculation() -> None:
    screen = workers(screen_table())
    selection = an.select_variants(
        screen, eligibility(("T1", "T2", "T3", "T4", "T5"), ("F1", "F2"))
    )
    # T4 has the lowest ratio (0.55); fixed and learned kinds are selected independently.
    assert selection["tree"][FIXED]["selected"] == "T4"
    assert selection["tree"][LEARNED]["selected"] == "T4"
    assert selection["tree"][FIXED]["table"]["T4"]["geometric_mean_ratio_to_T0"] == pytest.approx(
        0.55
    )
    # F1 and F2 tie at 45000 < F0 50000; the lowest ID wins.
    assert selection["flat"]["comparator"] == "F1"
    # A variant that failed EQ is never eligible, however fast.
    restricted = an.select_variants(screen, eligibility(("T1", "T2", "T3", "T5"), ("F2",)))
    assert restricted["tree"][FIXED]["selected"] == "T2"  # T2 and T3 tie at 0.60 -> lowest ID
    assert restricted["flat"]["comparator"] == "F2"
    assert "T4" not in restricted["tree"][FIXED]["table"]
    only_f0 = an.select_variants(screen, eligibility(("T1",), ()))
    assert only_f0["flat"]["comparator"] == "F0" and only_f0["tree"][LEARNED]["selected"] == "T1"
    # Kinds are independent: make T5 fastest for the learned tree only.
    changed = {p: {("W8", A, "learned_tree:T5"): 30_000} for p in PAIRS}
    mixed = an.select_variants(workers(screen_table(), changed), eligibility(("T4", "T5"), ()))
    assert mixed["tree"][FIXED]["selected"] == "T4" and mixed["tree"][LEARNED]["selected"] == "T5"


def test_confirm_entities_and_canonical_order() -> None:
    selection = {
        "flat": {"comparator": "F1"},
        "tree": {FIXED: {"selected": "T4"}, LEARNED: {"selected": "T2"}},
    }
    plan = an.confirm_entities(selection)
    assert plan == {FLAT: ["F0", "F1"], FIXED: ["T0", "T4"], LEARNED: ["T0", "T2"]}
    assert ts.canonical_entities(plan) == [
        "flat:F0",
        "flat:F1",
        "fixed_tree:T0",
        "fixed_tree:T4",
        "learned_tree:T0",
        "learned_tree:T2",
    ]
    selection["flat"]["comparator"] = "F0"
    assert an.confirm_entities(selection)[FLAT] == ["F0"]
    selection["tree"][FIXED]["selected"] = None  # type: ignore[assignment]
    with pytest.raises(ValueError, match="no selected tree variant"):
        an.confirm_entities(selection)


def full_confirm(add: float, forward: float = 1.0) -> list[dict[str, Any]]:
    table: dict[tuple[str, str, str], Any] = {}
    for kind in TREE_KINDS:
        table.update(
            {
                ("W8", A, f"{kind}:T0"): 100_000,
                ("W8", F, f"{kind}:T0"): 200_000,
                ("W8", A, f"{kind}:T4"): add,
                ("W8", F, f"{kind}:T4"): 200_000 * forward,
            }
        )
    table.update(
        {
            ("W8", A, "flat:F0"): 150_000,
            ("W8", F, "flat:F0"): 250_000,
            ("W8", A, "flat:F1"): 100_000,
            ("W8", F, "flat:F1"): 200_000,
        }
    )
    return workers(table)


def gated_ok(tree: tuple[str, ...] = ("T1", "T2", "T3", "T4", "T5")) -> dict[str, Any]:
    gated: dict[str, Any] = {}
    for v in ("F1", "F2", "T1", "T2", "T3", "T4", "T5"):
        passing = v in tree or v in ("F1", "F2")
        n = 27 if v.startswith("F") else 54
        strict = passing and v in ("F1", "T1", "T2")
        gated[v] = {
            "EQ": passing,
            "complete": True,
            "checkpoints": n,
            "counts": {
                "STRICT": n if strict else 0,
                "BOUNDED": 0 if strict else n if passing else 0,
                "NOT_EQUIVALENT": 0 if passing else n,
            },
        }
    return gated


SELECTION = {
    "flat": {"comparator": "F1"},
    "tree": {FIXED: {"selected": "T4"}, LEARNED: {"selected": "T4"}},
}


def test_full_analysis_pass_and_every_clause_listed() -> None:
    report = an.analyze(gated_ok(), SELECTION, full_confirm(40_000, 1.0))
    for kind in TREE_KINDS:
        criteria = report["criteria"][kind]
        assert criteria["EQ"] and criteria["flat_comparator"] == "F1"
        assert criteria["SP"]["status"] == "PASS"  # ratio 0.4 to T0
        assert criteria["PAR"]["status"] == "PASS" and criteria["PR"]["status"] == "PASS"
        for group in ("addition_forward", "model_forward"):
            for clause in ("geometric_mean", "cells", "parents"):
                assert "pass" in criteria["PR"][group][clause]
        weaker = criteria["versus_F0_weaker_comparison"]["PR"]["addition_forward"]
        assert weaker["geometric_mean"]["value"] == pytest.approx(40_000 / 150_000)
    h = report["hypotheses"]
    assert h["E-H1"]["holds"] is True  # T1 and T2 STRICT on all 54
    assert h["E-H2"]["holds"] is True
    assert h["E-H3"]["holds"] is True and h["E-H4"]["holds"] is True


def test_analysis_distinguishes_sp_pass_from_pr_fail() -> None:
    # Tree 60% of T0 (SP fails: needs <= 0.50) versus flat comparator 100000: PR needs <= 0.80.
    report = an.analyze(gated_ok(), SELECTION, full_confirm(60_000))
    assert report["verdicts"][FIXED] == {"SP": "FAIL", "PAR": "PASS", "PR": "PASS"}
    # Tree 45% of T0 but 150% of the flat comparator: SP passes, PAR and PR fail.
    table = full_confirm(45_000)
    over = {p: {("W8", A, "flat:F1"): 30_000} for p in PAIRS}  # comparator faster than T4
    report = an.analyze(
        gated_ok(), SELECTION, workers({**{k: v for k, v in _first(table).items()}}, over)
    )
    assert report["verdicts"][FIXED]["SP"] == "PASS"
    assert report["verdicts"][FIXED]["PAR"] == "FAIL" and report["verdicts"][FIXED]["PR"] == "FAIL"
    h = report["hypotheses"]
    assert (
        h["E-H3"]["holds"] is True and h["E-H4"]["holds"] is False
    )  # "can fail while E-H3 passes"


def _first(confirm: list[dict[str, Any]]) -> dict[tuple[str, str, str], Any]:
    return {
        (r["workload"], r["scope"], r["entity"]): statistics.median(r["durations_ns"])
        for r in confirm[0]["timing"]["records"]
    }


def test_analysis_inconclusive_incomplete_and_no_eq_cases() -> None:
    unstable = {PAIRS[0]: {("W8", A, "fixed_tree:T4"): [40_000] * 7 + [60_000]}}
    table = _first(full_confirm(40_000))
    report = an.analyze(gated_ok(), SELECTION, workers(table, unstable))
    assert report["verdicts"][FIXED]["SP"] == "INCONCLUSIVE"
    assert report["verdicts"][LEARNED]["SP"] == "PASS"
    h = report["hypotheses"]["E-H3"]
    assert h["per_kind"] == {FIXED: "INCONCLUSIVE", LEARNED: "PASS"} and h["holds"] is True
    both = {
        p: {("W8", A, f"{k}:T4"): [40_000] * 7 + [60_000] for k in TREE_KINDS} for p in PAIRS[:1]
    }
    report = an.analyze(gated_ok(), SELECTION, workers(table, both))
    assert report["hypotheses"]["E-H3"]["holds"] is None  # undecided, not False
    report = an.analyze(gated_ok(), SELECTION, full_confirm(40_000)[:20])
    assert report["verdicts"][FIXED]["SP"] == "INCOMPLETE" and report["complete"] is False
    # A selected variant that failed EQ never counts, however fast.
    failed = gated_ok(tree=("T1", "T2", "T3", "T5"))
    report = an.analyze(failed, SELECTION, full_confirm(40_000))
    assert report["criteria"][FIXED]["EQ"] is False
    assert report["hypotheses"]["E-H3"]["holds"] is False
    assert report["hypotheses"]["E-H2"]["holds"] is False  # T4 is not at least BOUNDED
    # No EQ-passing tree variant: nothing is timed and no latency claim is made.
    nothing = gated_ok(tree=())
    report = an.analyze(nothing, None, [])
    assert an.eligibility_from_gate(nothing)["timing_stage_runs"] is False
    assert report["hypotheses"]["E-H3"]["holds"] is None
    assert report["hypotheses"]["E-H3"]["status"] == "NOT_EVALUATED"
    assert report["hypotheses"]["E-H1"]["holds"] is False


def test_e_h1_requires_strict_everywhere() -> None:
    gated = gated_ok()
    gated["T2"]["counts"] = {"STRICT": 53, "BOUNDED": 1, "NOT_EQUIVALENT": 0}
    assert an.analyze(gated, None, [])["hypotheses"]["E-H1"]["holds"] is False


def test_descriptive_tables_report_ratios_against_the_reference() -> None:
    plan = {FLAT: ["F0", "F1"], FIXED: ["T0", "T4"], LEARNED: ["T0", "T4"]}
    table = an.descriptive_tables(full_confirm(40_000), plan)
    entry = table[f"{FIXED}:T4/W8/{A}"]
    assert entry["pairs"] == 27 and entry["geometric_mean_ratio_to_reference"] == pytest.approx(0.4)
    assert table[f"{FLAT}:F1/W8/{A}"]["geometric_mean_ratio_to_reference"] == pytest.approx(2 / 3)


def test_analysis_recomputes_from_raw_samples_not_from_stored_summaries() -> None:
    records = workers(speed(40_000))
    for w in records:
        for r in w["timing"]["records"]:
            r["median_ns"] = 1  # a misleading stored summary must be ignored
            r["usable"] = False
    sp = an.speedup_criterion(an.index_workers(records), V, T0)
    assert sp["status"] == "PASS"


# ---------------------------------------------------------------------------------------------
# Timing schedule and caps
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("entity_count", [1, 2, 6, 15])
def test_schedule_call_counts_for_all_three_workloads(entity_count: int) -> None:
    entities = tuple(f"e{i}" for i in range(entity_count))
    blocks = list(ts.schedule(0, entities))
    by_workload = {w: [b for b in blocks if b.workload == w] for w in ts.WORKLOADS}
    # W8 and W1: three scopes; Wtok: lookup and addition only. 8 rounds per scope and entity.
    assert len(by_workload["W8"]) == 3 * 8 * entity_count
    assert len(by_workload["W1"]) == 3 * 8 * entity_count
    assert len(by_workload["Wtok"]) == 2 * 8 * entity_count
    assert {b.scope for b in by_workload["Wtok"]} == {an.LOOKUP, an.ADDITION}
    assert {b.scope for b in by_workload["W8"]} == {an.LOOKUP, an.ADDITION, an.FORWARD}
    assert all(len(b.warm) == 2 and len(b.timed) == 10 for b in blocks)
    timed = sum(len(b.timed) for b in blocks)
    warm = sum(len(b.warm) for b in blocks)
    assert (warm, timed) == (2 * 8 * 8 * entity_count, 10 * 8 * 8 * entity_count)  # 8 scope-blocks
    assert warm + timed == ts.expected_scope_calls(entity_count) == 768 * entity_count
    for workload, scope in {(b.workload, b.scope) for b in blocks}:
        per = [b for b in blocks if (b.workload, b.scope) == (workload, scope)]
        for entity in entities:
            mine = [b for b in per if b.entity == entity]
            assert [b.round for b in mine] == list(range(8))
            assert sum(len(b.timed) for b in mine) == 80  # 8 rounds x 10 timed calls


def test_schedule_rotation_and_input_indexes_follow_p5() -> None:
    entities = ("a", "b", "c")
    blocks = [b for b in ts.schedule(4, entities) if (b.workload, b.scope) == ("W8", an.LOOKUP)]
    order = [tuple(b.entity for b in blocks[r * 3 : r * 3 + 3]) for r in range(8)]
    for round_id, names in enumerate(order):
        shift = (4 + round_id) % 3
        assert names == entities[shift:] + entities[:shift]  # rotated by (index + round) mod n
    first = next(b for b in blocks if b.round == 3)
    assert first.warm == (2, 3) and first.timed == tuple((30 + j) % 4 for j in range(10))
    with pytest.raises(ValueError):
        list(ts.schedule(27, entities))
    with pytest.raises(ValueError):
        list(ts.schedule(0, ("a", "a")))


def test_screen_and_confirm_scope_call_budgets() -> None:
    screen = {
        "flat": ["F0", "F1", "F2"],
        FIXED: ["T0", *rv.TREE_VARIANTS],
        LEARNED: ["T0", *rv.TREE_VARIANTS],
    }
    assert len(ts.canonical_entities(screen)) == 15
    assert ts.expected_scope_calls(15) == 11_520
    confirm = {"flat": ["F0", "F1"], FIXED: ["T0", "T4"], LEARNED: ["T0", "T4"]}
    assert ts.expected_scope_calls(len(ts.canonical_entities(confirm))) == 4_608


def test_run_timing_executes_exactly_the_scheduled_calls(cell: common.CellSource) -> None:
    model = cell.models[FIXED]
    entities = {"fixed_tree:T0": model, "fixed_tree:T3": rv.build_variant_model(model, "T3")}
    ticks = itertools.count(0, 1000)
    result = ts.run_timing(
        entities, ts.workload_inputs(cell.train), 3, rounds=2, clock=lambda: next(ticks)
    )
    assert (
        result["call_counts"]["warmups"] == 2 * 2 * 8 * 2
    )  # warmups x rounds x scope-blocks x entities
    assert result["call_counts"]["timed"] == 10 * 2 * 8 * 2
    assert all(set(r["durations_ns"]) == {1000} for r in result["records"])  # fake clock
    assert len(result["records"]) == 8 * 2  # eight workload-scope pairs, two entities


def test_p6_workload_inputs_are_p5_inputs() -> None:
    train = torch.randint(0, 256, (40, 65))
    inputs = ts.workload_inputs(train)
    registered = p5_timing.inputs_from_rows(train)
    assert all(torch.equal(a, b) for a, b in zip(inputs["W8"], registered[8], strict=True))
    assert all(torch.equal(a, b) for a, b in zip(inputs["W1"], registered[1], strict=True))
    assert [tuple(x.shape) for x in inputs["W8"]] == [(8, 64)] * 4
    assert [tuple(x.shape) for x in inputs["W1"]] == [(1, 64)] * 4
    assert [tuple(x.shape) for x in inputs["Wtok"]] == [(1, 1)] * 4
    assert all(torch.equal(t, w[:, :1]) for t, w in zip(inputs["Wtok"], inputs["W1"], strict=True))


def test_stage_caps_match_the_specification() -> None:
    caps = {name: (cap, worker) for name, (_, cap, worker) in stage.STAGES.items()}
    assert caps["equivalence"] == (1200.0, None)
    assert caps["screen"] == (1200.0, 90.0)
    assert caps["confirm"] == (600.0, 45.0)
    assert caps["equivalence"][0] + caps["screen"][0] + caps["confirm"][0] == 3000.0
    from arborlm.watchdog import RSS_BYTES

    assert RSS_BYTES == 2 * 1024**3


def test_registered_runs_cannot_reduce_repetitions_or_pairs(tmp_path: Path) -> None:
    kwargs = {
        "data_dir": tmp_path,
        "parent_suite": tmp_path,
        "output_root": tmp_path,
        "results_root": tmp_path,
    }
    with pytest.raises(ValueError, match="fixed outside a dry run"):
        common.StudyArgs(**kwargs, rounds=7)
    with pytest.raises(ValueError, match="fixed outside a dry run"):
        common.StudyArgs(**kwargs, pair_count=26)
    assert common.StudyArgs(**kwargs).pair_list() == common.pairs()
    assert len(common.pairs()) == 27
    assert [common.pair_index(p) for p in common.pairs()] == list(range(27))
    assert common.pair_index((101, 301, 501)) == Cell(101, 301, 501, FLAT).index == 0
    roundtrip = common.StudyArgs.from_json(common.StudyArgs(**kwargs).to_json())
    assert roundtrip == common.StudyArgs(**kwargs)


def test_stage_budget_uses_the_cap_without_transfer() -> None:
    clock = iter([0.0, 10.0, 10.0, 1300.0])
    budget = common.StageBudget(1200.0, 90.0, now=lambda: next(clock))
    assert budget.remaining() == 1190.0
    assert budget.worker_budget() == 90.0  # min(worker cap 90, remaining 1190)
    with pytest.raises(TimeoutError):
        budget.worker_budget()  # 1300 s elapsed > 1200 s cap


def test_pairs_follow_p5_order() -> None:
    assert common.pairs()[0] == (BACKBONES[0], ORDERS[0], SEEDS[0])
    assert common.pairs()[-1] == (BACKBONES[-1], ORDERS[-1], SEEDS[-1])


# ---------------------------------------------------------------------------------------------
# Stage machinery (cap breach, partial records, refusal to overwrite, dry run)
# ---------------------------------------------------------------------------------------------
def open_test_stage(tmp_path: Path, name: str = "confirm") -> stage.StageContext:
    return stage.open_stage(
        name,
        output_root=tmp_path / "out",
        results_root=tmp_path / "res",
        argv=["test"],
        arguments={},
        dry_run=True,
    )


def test_manifest_has_every_registered_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO)
    context = open_test_stage(tmp_path)
    manifest = json.loads((context.compact / "manifest.json").read_text())
    for key in (
        "command",
        "git_head",
        "git_dirty",
        "p6_source_sha256",
        "spec_sha256",
        "environment",
        "start_utc",
        "end_utc",
        "status",
        "run_id",
        "caps",
    ):
        assert key in manifest, key
    assert manifest["status"] == "running" and manifest["end_utc"] is None
    assert len(manifest["git_head"]) == 40 and isinstance(manifest["git_dirty"], bool)
    assert set(manifest["p6_source_sha256"]) == {
        f"src/arborlm/{p.name}" for p in (REPO / "src" / "arborlm").glob("p6_*.py")
    }
    assert "src/arborlm/p6_retrieval.py" in manifest["p6_source_sha256"]
    environment = manifest["environment"]
    assert "torch_config_show" in environment and environment["threads"]["intra_op"] == 1
    assert environment["threads"]["inter_op"] == 1 and "clock" in environment
    assert environment["deterministic_algorithms"] is True
    assert manifest["spec_reference"].endswith("routing-fidelity.md")
    stage.finish_stage(context, "completed", None, {"x": 1})
    final = json.loads((context.compact / "manifest.json").read_text())
    assert final["status"] == "completed" and final["end_utc"] is not None
    # A second stage of the same name never reuses or overwrites the first run directory.
    second = open_test_stage(tmp_path)
    assert second.run != context.run and second.compact != context.compact
    assert (context.compact / "result.json").is_file()


def test_cap_breach_preserves_partial_and_unexecuted_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO)
    context = open_test_stage(tmp_path)
    pairs = common.pairs()[:3]
    seen: list[tuple[int, int, int]] = []

    def argv_for(pair: tuple[int, int, int], child: Path) -> list[str]:
        seen.append(pair)
        target, payload = str(child / "result.json"), json.dumps({"outcome": "completed"})
        ok = f"open({target!r}, 'w').write({payload!r})"
        code = ok if pair == pairs[0] else "import sys; sys.exit(3)"
        return [sys.executable, "-c", code]

    outcome = stage.run_worker_stage(context, pairs, argv_for=argv_for)
    assert outcome.status == "failed" and "failed" in (outcome.reason or "")
    assert seen == pairs[:2]  # the third worker never started
    statuses = [row["status"] for row in outcome.rows]
    assert statuses[0] == "completed" and statuses[1] != "completed" and statuses[2] == "unexecuted"
    persisted = json.loads((context.compact / "workers.json").read_text())["workers"]
    assert [row["label"] for row in persisted] == [common.pair_label(p) for p in pairs]
    assert persisted[2]["status"] == "unexecuted" and persisted[2]["run_id"] is None


def test_exhausted_stage_cap_stops_before_any_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO)
    context = open_test_stage(tmp_path)
    started: list[int] = []
    outcome = stage.run_worker_stage(
        context,
        common.pairs()[:2],
        argv_for=lambda p, c: started.append(1) or [sys.executable, "-c", "pass"],
        cap_seconds=-1.0,
    )
    assert outcome.status == "failed" and "cap exhausted" in (outcome.reason or "")
    assert started == [] and {r["status"] for r in outcome.rows} == {"unexecuted"}


def test_require_completed_picks_only_completed_matching_runs(tmp_path: Path) -> None:
    results = tmp_path / "res"
    for name, status, dry in (
        ("A", "failed", True),
        ("B", "completed", True),
        ("C", "completed", False),
    ):
        directory = results / "equivalence" / name
        directory.mkdir(parents=True)
        (directory / "result.json").write_text(json.dumps({"status": status}))
        (directory / "manifest.json").write_text(json.dumps({"dry_run": dry}))
    assert stage.require_completed(results, "equivalence", dry_run=True).name == "B"
    assert stage.require_completed(results, "equivalence", dry_run=False).name == "C"
    with pytest.raises(ValueError, match="not a completed"):
        stage.require_completed(results, "equivalence", "A")
    (results / "equivalence" / "D").mkdir()
    (results / "equivalence" / "D" / "result.json").write_text(json.dumps({"status": "completed"}))
    (results / "equivalence" / "D" / "manifest.json").write_text(json.dumps({"dry_run": True}))
    with pytest.raises(ValueError, match="expected exactly one"):
        stage.require_completed(results, "equivalence", dry_run=True)


def test_timing_stage_does_not_run_without_an_eq_passing_tree_variant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = tmp_path / "res"
    directory = results / "equivalence" / "R1"
    directory.mkdir(parents=True)
    gate = {v: {"EQ": v.startswith("F")} for v in ("F1", "F2", "T1", "T2", "T3", "T4", "T5")}
    (directory / "result.json").write_text(json.dumps({"status": "completed", "gate": gate}))
    (directory / "manifest.json").write_text(json.dumps({"dry_run": True}))
    args = common.StudyArgs(
        data_dir=tmp_path,
        parent_suite=tmp_path,
        output_root=tmp_path / "out",
        results_root=results,
        synthetic=True,
        pair_count=1,
        rounds=1,
    )
    assert ts.run_timing_stage("screen", args, ["test"]) == 2
    assert "no tree variant passed EQ" in capsys.readouterr().out
    assert not (tmp_path / "out").exists()  # nothing was started


def test_cli_parser_accepts_the_registered_commands(tmp_path: Path) -> None:
    parser = cli._parser()
    for command in ("equivalence", "screen", "confirm", "analyze"):
        ns = parser.parse_args(
            [
                command,
                "--data-dir",
                "data/wikitext2",
                "--parent-suite",
                "experiments/P5HIER-x",
                "--output-root",
                "experiments",
                "--results-root",
                "results/p6-e-2026-11-13",
            ]
        )
        args = cli._args(ns)
        assert (args.pair_count, args.rounds, args.synthetic) == (27, 8, False)
    with pytest.raises(SystemExit):
        parser.parse_args(["equivalence"])  # --output-root and --results-root are required


def test_dry_run_refuses_to_write_under_experiments_or_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO)
    for out, res in (("experiments", "/tmp/x"), ("/tmp/x", "results/p6-e-2026-11-13")):
        with pytest.raises(SystemExit, match="refuses"):
            cli.main(["dry-run", "--output-root", out, "--results-root", res])
    assert not (REPO / "results" / "p6-e-2026-11-13").exists()


def test_dry_run_end_to_end_on_a_synthetic_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """All four stages with real subprocess workers, one synthetic pair, one timing round."""
    monkeypatch.chdir(REPO)
    code = cli.main(
        [
            "dry-run",
            "--output-root",
            str(tmp_path / "out"),
            "--results-root",
            str(tmp_path / "res"),
            "--pair-count",
            "1",
            "--rounds",
            "1",
            "--panel-rows",
            "8",
        ]
    )
    assert code == 0, capsys.readouterr().out
    res = tmp_path / "res"
    runs = {
        name: sorted((res / name).iterdir())
        for name in ("equivalence", "screen", "confirm", "analysis")
    }
    assert all(len(v) == 1 and v[0].name.startswith("P6E") for v in runs.values())
    equivalence = json.loads((runs["equivalence"][0] / "result.json").read_text())
    assert equivalence["status"] == "completed" and equivalence["completed_workers"] == 1
    assert all(g["EQ"] for g in equivalence["gate"].values())
    assert equivalence["eligibility"]["timing_stage_runs"] is True
    screen = json.loads((runs["screen"][0] / "result.json").read_text())
    assert screen["entities_per_worker"] == 15 and screen["scope_calls_per_worker"] == 11_520 // 8
    selection = json.loads((runs["screen"][0] / "selection.json").read_text())
    assert selection["tree"][FIXED]["selected"] in ("T1", "T2", "T3", "T4", "T5")
    confirm = json.loads((runs["confirm"][0] / "result.json").read_text())
    assert confirm["selection_used"] == selection
    assert confirm["evidence"]["screen_run"] == runs["screen"][0].name
    worker_file = next((runs["confirm"][0] / "workers").glob("b101-o301-s501.json"))
    worker_record = json.loads(worker_file.read_text())
    assert worker_record["dry_run"] is True and worker_record["timing_scope_calls"] > 0
    assert all(len(r["durations_ns"]) == 10 for r in worker_record["timing"]["records"])
    assert set(worker_record["memory_profile"]) and "first_call_after_load_ns" in worker_record
    assert set(worker_record["integrity_replay_before_timing"]) == set(common.KINDS)
    assert worker_record["source_recheck_at_worker_end"]["p6_sources_unchanged"] is True
    equivalence_worker = json.loads(
        next((runs["equivalence"][0] / "workers").glob("b101-o301-s501.json")).read_text()
    )
    assert equivalence_worker["source_recheck_at_worker_end"]["archive_unchanged"] is True
    assert equivalence_worker["known_limits"] == list(common.KNOWN_LIMITS)
    analysis = json.loads((runs["analysis"][0] / "result.json").read_text())
    assert analysis["status"] == "completed" and "criteria" in analysis["analysis"]
    assert analysis["analysis"]["complete"] is False or analysis["analysis"]["pairs"] == 1
    for name in runs:
        manifest = json.loads((runs[name][0] / "manifest.json").read_text())
        assert manifest["dry_run"] is True and manifest["status"] == "completed"
    assert not (REPO / "results" / "p6-e-2026-11-13").exists()


def test_state_digest_is_unchanged_by_wrapping(cell: common.CellSource) -> None:
    model = cell.models[LEARNED]
    before = state_digest(model)
    rv.build_variant_model(model, "T5")
    with torch.no_grad():
        evaluate(model, cell.panel, cell.expected_targets)
    assert state_digest(model) == before


# ---------------------------------------------------------------------------------------------
# One registered run per stage; run linkage; recorded limits
# ---------------------------------------------------------------------------------------------
def _open_registered(tmp_path: Path, **kwargs: Any) -> stage.StageContext:
    return stage.open_stage(
        "equivalence",
        output_root=tmp_path / "out",
        results_root=tmp_path / "res",
        argv=["test"],
        arguments={},
        dry_run=False,
        **kwargs,
    )


def test_second_registered_run_is_refused_unless_superseded_with_a_recorded_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO)
    first = _open_registered(tmp_path)
    assert first.manifest["supersedes"] is None
    stage.finish_stage(first, "failed", "worker failed", {})
    runs_before = sorted(p.name for p in (tmp_path / "out").iterdir())
    with pytest.raises(ValueError, match="refusing to run equivalence again"):
        _open_registered(tmp_path)  # a failed earlier run counts as a run
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == runs_before  # nothing allocated
    with pytest.raises(ValueError, match="not an earlier equivalence run"):
        _open_registered(tmp_path, supersede="no-such-run", supersede_reason="r")
    with pytest.raises(ValueError, match="non-empty"):
        _open_registered(tmp_path, supersede=first.run.name, supersede_reason="  ")
    with pytest.raises(ValueError, match="together"):
        common.StudyArgs(
            data_dir=tmp_path,
            parent_suite=tmp_path,
            output_root=tmp_path,
            results_root=tmp_path,
            supersede="x",
        )
    second = _open_registered(
        tmp_path, supersede=first.run.name, supersede_reason="worker crashed; rerun approved"
    )
    recorded = json.loads((second.compact / "manifest.json").read_text())["supersedes"]
    assert recorded == {
        "run_id": first.run.name,
        "reason": "worker crashed; rerun approved",
        "earlier_runs": [first.run.name],
    }
    stage.finish_stage(second, "completed", None, {})
    # A third run must name an existing run, and the earlier ones stay on record.
    third = _open_registered(tmp_path, supersede=second.run.name, supersede_reason="again")
    assert third.manifest["supersedes"]["earlier_runs"] == [first.run.name, second.run.name]  # type: ignore[index]


def test_dry_runs_are_neither_counted_nor_supersedable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO)
    for _ in range(2):  # any number of dry runs
        stage.finish_stage(open_test_stage(tmp_path, "equivalence"), "completed", None, {})
    registered = _open_registered(tmp_path)  # the first registered run is not blocked by them
    assert registered.manifest["dry_run"] is False
    with pytest.raises(ValueError, match="dry run"):
        stage.open_stage(
            "equivalence",
            output_root=tmp_path / "out",
            results_root=tmp_path / "res",
            argv=["t"],
            arguments={},
            dry_run=True,
            supersede="x",
            supersede_reason="r",
        )


def test_every_stage_manifest_records_the_known_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO)
    manifest = json.loads((open_test_stage(tmp_path).compact / "manifest.json").read_text())
    assert manifest["known_limits"] == list(common.KNOWN_LIMITS) and manifest["supersedes"] is None
    text = " ".join(manifest["known_limits"])
    assert ".data" in text and "slot_offsets" in text and "RNG" in text


def test_require_completed_with_an_explicit_id_checks_the_dry_run_flag(tmp_path: Path) -> None:
    results = tmp_path / "res"
    for name, dry in (("DRY", True), ("REG", False)):
        directory = results / "screen" / name
        directory.mkdir(parents=True)
        (directory / "result.json").write_text(json.dumps({"status": "completed"}))
        (directory / "manifest.json").write_text(json.dumps({"dry_run": dry}))
    assert stage.require_completed(results, "screen", "DRY", dry_run=True).name == "DRY"
    assert stage.require_completed(results, "screen", "REG", dry_run=False).name == "REG"
    with pytest.raises(ValueError, match="different dry_run flag"):
        stage.require_completed(results, "screen", "DRY", dry_run=False)
    with pytest.raises(ValueError, match="different dry_run flag"):
        stage.require_completed(results, "screen", "REG", dry_run=True)


LINK_PLAN = {"flat": ["F0", "F1"], FIXED: ["T0", "T2"], LEARNED: ["T0", "T2"]}
LINK_SELECTION = {
    "flat": {"comparator": "F1"},
    "tree": {FIXED: {"selected": "T2"}, LEARNED: {"selected": "T2"}},
}


def build_chain(root: Path, **tamper: Any) -> tuple[Path, Path, Path, list[Any], list[Any]]:
    """Hand-built equivalence, screen and confirm folders that point at each other."""
    from arborlm.io import file_sha256

    def put(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    eq_dir, screen_dir, confirm_dir = (
        root / n / r for n, r in (("e", "E1"), ("s", "S1"), ("c", "C1"))
    )
    put(eq_dir / "result.json", {"status": "completed", "gate": {}})
    put(screen_dir / "selection.json", LINK_SELECTION)
    selection_sha = file_sha256(screen_dir / "selection.json")
    screen_plan = {"flat": ["F0", "F1"], FIXED: ["T0", "T2"], LEARNED: ["T0", "T2"]}
    put(
        screen_dir / "result.json",
        {
            "status": "completed",
            "plan": screen_plan,
            "selection_sha256": selection_sha,
            "evidence": {"equivalence_run": "E1"},
        },
    )
    evidence = {
        "equivalence_run": "E1",
        "equivalence_result_sha256": file_sha256(eq_dir / "result.json"),
        "screen_run": "S1",
        "selection_sha256": selection_sha,
        "screen_result_sha256": file_sha256(screen_dir / "result.json"),
    }
    evidence.update(tamper.get("evidence", {}))
    put(confirm_dir / "result.json", {"status": "completed", "evidence": evidence})
    base = {"outcome": "completed", "dry_run": False}
    screen_workers = [{**base, "plan": screen_plan}]
    confirm_workers = [{**base, "plan": LINK_PLAN, **tamper.get("worker", {})}]
    return eq_dir, screen_dir, confirm_dir, screen_workers, confirm_workers


def test_linkage_accepts_a_consistent_chain(tmp_path: Path) -> None:
    eq_dir, screen_dir, confirm_dir, sw, cw = build_chain(tmp_path)
    cli.check_linkage(eq_dir, screen_dir, confirm_dir, LINK_SELECTION, sw, cw, dry_run=False)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ({"evidence": {"screen_run": "S2"}}, "confirm consumed this screen run"),
        ({"evidence": {"selection_sha256": "0" * 64}}, "confirm consumed this selection"),
        ({"evidence": {"equivalence_run": "E2"}}, "confirm consumed this equivalence run"),
        (
            {"evidence": {"equivalence_result_sha256": "0" * 64}},
            "confirm recorded this equivalence",
        ),
        ({"evidence": {"screen_result_sha256": "0" * 64}}, "confirm recorded this screen result"),
        (
            {"worker": {"plan": {**LINK_PLAN, FIXED: ["T0", "T1"]}}},
            "confirm workers timed the plan",
        ),
        ({"worker": {"outcome": "failed"}}, "all workers completed"),
        ({"worker": {"dry_run": True}}, "worker dry-run flags match"),
    ],
)
def test_linkage_rejects_every_broken_link(
    tmp_path: Path, tamper: dict[str, Any], message: str
) -> None:
    eq_dir, screen_dir, confirm_dir, sw, cw = build_chain(tmp_path, **tamper)
    with pytest.raises(ValueError, match=message):
        cli.check_linkage(eq_dir, screen_dir, confirm_dir, LINK_SELECTION, sw, cw, dry_run=False)


def test_linkage_rejects_a_screen_that_used_another_equivalence_run_or_selection(
    tmp_path: Path,
) -> None:
    eq_dir, screen_dir, confirm_dir, sw, cw = build_chain(tmp_path)
    screen = json.loads((screen_dir / "result.json").read_text())
    for key, value, message in (
        ("evidence", {"equivalence_run": "E9"}, "screen consumed this equivalence run"),
        ("selection_sha256", "1" * 64, "screen result records this selection"),
    ):
        broken = {**screen, key: value}
        (screen_dir / "result.json").write_text(json.dumps(broken))
        with pytest.raises(ValueError, match=message):
            cli.check_linkage(
                eq_dir, screen_dir, confirm_dir, LINK_SELECTION, sw, cw, dry_run=False
            )


def test_analyze_stage_fails_on_a_selection_that_the_confirm_did_not_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real CLI path: a swapped selection file is a failed analysis, not a silent mix."""
    monkeypatch.chdir(REPO)
    code = cli.main(
        [
            "dry-run",
            "--output-root", str(tmp_path / "out"),
            "--results-root", str(tmp_path / "res"),
            "--pair-count", "1", "--rounds", "1", "--panel-rows", "8",
        ]
    )  # fmt: skip
    assert code == 0
    screen_dir = next((tmp_path / "res" / "screen").iterdir())
    selection = json.loads((screen_dir / "selection.json").read_text())
    other = "T3" if selection["tree"][FIXED]["selected"] != "T3" else "T4"
    selection["tree"][FIXED]["selected"] = other
    (screen_dir / "selection.json").write_text(json.dumps(selection))
    args = common.StudyArgs(
        data_dir=tmp_path,
        parent_suite=tmp_path,
        output_root=tmp_path / "out",
        results_root=tmp_path / "res",
        synthetic=True,
        pair_count=1,
        rounds=1,
    )
    assert cli.analyze_stage(args, ["t"]) == 1
    analysis_runs = sorted((tmp_path / "res" / "analysis").iterdir())
    failed = json.loads((analysis_runs[-1] / "result.json").read_text())
    assert failed["status"] == "failed" and "linkage" in failed["reason"]


# ---------------------------------------------------------------------------------------------
# Timing worker: replay before measuring, source re-check at the end
# ---------------------------------------------------------------------------------------------
def worker_spec(source: dict[str, Any]) -> dict[str, Any]:
    args = common.StudyArgs(
        data_dir=Path("."),
        parent_suite=Path("."),
        output_root=Path("."),
        results_root=Path("."),
        synthetic=True,
        pair_count=1,
        rounds=1,
        panel_rows=8,
    )
    plan = {"flat": ["F0"], FIXED: ["T0"], LEARNED: ["T0"]}
    return {"mode": "screen", "args": args.to_json(), "plan": plan, "source": source}


def real_source_expectations(scratch: Path) -> dict[str, Any]:
    from arborlm.records import record_source

    return {
        "source_archive_sha256": record_source(scratch, REPO, spec=common.SPEC)["archive"][
            "sha256"
        ],
        "p6_source_sha256": stage.p6_source_hashes(),
    }


def test_timing_worker_replays_the_recorded_nll_before_any_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import arborlm.engine as engine

    monkeypatch.chdir(REPO)
    monkeypatch.setattr(engine, "configure_cpu", lambda: None)
    source = common.load_synthetic_cell((101, 301, 501), rows=8)
    nll = source.recorded[FIXED]["nll"]
    source.recorded[FIXED]["nll"] = float(
        torch.nextafter(
            torch.tensor(nll, dtype=torch.float64), torch.tensor(9.0, dtype=torch.float64)
        )
    )
    monkeypatch.setattr(ts, "load_cell", lambda args, pair, run: source)
    timed: list[int] = []
    monkeypatch.setattr(ts, "run_timing", lambda *a, **k: timed.append(1))
    spec = worker_spec({"source_archive_sha256": "x", "p6_source_sha256": {}})
    with pytest.raises(ValueError, match="integrity replay mismatch"):
        ts.timing_worker(spec, tmp_path, (101, 301, 501))
    assert timed == [] and not (tmp_path / "result.json").exists()  # stopped before timing


def test_timing_worker_stops_when_the_source_changed_and_records_the_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import arborlm.engine as engine

    monkeypatch.chdir(REPO)
    monkeypatch.setattr(engine, "configure_cpu", lambda: None)
    source = common.load_synthetic_cell((101, 301, 501), rows=8)
    monkeypatch.setattr(ts, "load_cell", lambda args, pair, run: source)
    (tmp_path / "scratch").mkdir()
    expected = real_source_expectations(tmp_path / "scratch")
    good = tmp_path / "good"
    good.mkdir()
    ts.timing_worker(worker_spec(expected), good, (101, 301, 501))
    record = json.loads((good / "result.json").read_text())
    assert set(record["integrity_replay_before_timing"]) == set(common.KINDS)
    assert all(r["bitwise_equal"] for r in record["integrity_replay_before_timing"].values())
    assert record["source_recheck_at_worker_end"]["archive_unchanged"] is True
    assert record["known_limits"] == list(common.KNOWN_LIMITS)
    assert all("p50_ns" in r for r in record["timing"]["records"])
    for broken in (
        {**expected, "source_archive_sha256": "0" * 64},
        {
            **expected,
            "p6_source_sha256": {**expected["p6_source_sha256"], "src/arborlm/p6_x.py": "0"},
        },
    ):
        bad = tmp_path / f"bad{len(str(broken))}"
        bad.mkdir()
        with pytest.raises(ValueError, match="source archive or a p6 module changed"):
            ts.timing_worker(worker_spec(broken), bad, (101, 301, 501))
        assert not (bad / "result.json").exists()


# ---------------------------------------------------------------------------------------------
# loader-smoke: the real loading path and the unmodified replay, nothing else
# ---------------------------------------------------------------------------------------------
def test_loader_smoke_calls_no_variant_equivalence_timing_or_stage_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("loader-smoke reached a forbidden code path")

    for module, names in (
        (rv, ("build_variant_model", "build_memory_variant")),
        (
            eq,
            (
                "run_cell",
                "run_checkpoint",
                "compare_batches",
                "compare_fixtures",
                "classify",
                "gate",
            ),
        ),
        (ts, ("run_timing", "timing_worker", "run_timing_stage")),
        (stage, ("open_stage", "run_worker_stage", "finish_stage")),
        (an, ("analyze", "select_variants")),
        (cli, ("analyze_stage", "_dry_run", "_worker")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, boom)
    loaded: list[tuple[int, int, int]] = []

    def fake_loader(pair: tuple[int, int, int], **kwargs: Any) -> common.CellSource:
        loaded.append(pair)
        assert Path(kwargs["run"]).is_dir()
        return common.load_synthetic_cell(pair, rows=8)

    monkeypatch.setattr(common, "load_real_cell", fake_loader)
    monkeypatch.chdir(tmp_path)  # experiments/ and results/ would appear here if anything wrote
    code = cli.main(["loader-smoke", "--parent-suite", "suite", "--pair", "101", "301", "501"])
    report = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert code == 0 and loaded == [(101, 301, 501)]
    assert report["command"] == "loader-smoke" and report["p6_quantities_computed"] is False
    assert set(report["replay"]) == set(common.KINDS)
    assert all(r["bitwise_equal"] and r["seconds"] > 0 for r in report["replay"].values())
    assert report["peak_rss_bytes_ru_maxrss"] > 0 and report["wall_seconds"] > 0
    assert report["load_seconds"] >= 0 and report["checkpoint_files_unchanged"] is True
    assert sorted(p.name for p in tmp_path.iterdir()) == []  # nothing written, scratch removed


def test_loader_smoke_stops_on_a_replay_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = common.load_synthetic_cell((101, 301, 501), rows=8)
    source.recorded[LEARNED]["nll"] += 1e-9
    monkeypatch.setattr(common, "load_real_cell", lambda pair, **kw: source)
    with pytest.raises(ValueError, match="integrity replay mismatch"):
        cli.loader_smoke(
            (101, 301, 501),
            parent_suite=tmp_path,
            output_root=tmp_path,
            p5_results=tmp_path,
            data_dir=tmp_path,
        )


def test_loader_smoke_refuses_a_scratch_folder_under_results_or_experiments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    (tmp_path / "results").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "results"))
    monkeypatch.setattr(common, "load_real_cell", lambda *a, **k: pytest.fail("must not load"))
    with pytest.raises(SystemExit, match="outside experiments/ results/"):
        cli.loader_smoke(
            (101, 301, 501),
            parent_suite=tmp_path,
            output_root=tmp_path,
            p5_results=tmp_path,
            data_dir=tmp_path,
        )


def test_real_cell_loader_keeps_only_the_three_memory_kinds_and_rehashes_their_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression for the loader-smoke finding: P5's loader also returns the dense variant."""
    import arborlm.hierarchy_ablation as hierarchy
    import arborlm.p5_data as p5_data
    from arborlm.io import file_sha256
    from arborlm.p5_config import STEPS

    pair = (101, 301, 501)
    synthetic = common.load_synthetic_cell(pair, rows=8)
    quality = tmp_path / "suite" / "quality" / "P5QUALITY-x"
    (quality / "frozen-data").mkdir(parents=True)
    (quality / "frozen-data" / "acquisition.json").write_text("{}")
    (quality / "manifest.json").write_text(json.dumps({"dataset_manifest_sha256": "d"}))
    data_dir, p5_results = tmp_path / "data", tmp_path / "p5"
    data_dir.mkdir()
    (data_dir / "manifest.json").write_text("{}")  # same bytes as the frozen acquisition manifest
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    (parent_dir / "state.pt").write_bytes(b"parent-state")
    (parent_dir / "index.json").write_bytes(b"parent-index")
    provenance = {
        "checkpoint_path": str(parent_dir),
        "checkpoint_state_sha256": file_sha256(parent_dir / "state.pt"),
        "checkpoint_index_sha256": file_sha256(parent_dir / "index.json"),
    }
    provenance["upstream_p3"] = dict(provenance)
    evidence: dict[str, Any] = {}
    for kind in ("dense", *common.KINDS):
        folder = tmp_path / "cells" / kind
        folder.mkdir(parents=True)
        (folder / "state.pt").write_bytes(f"state-{kind}".encode())
        (folder / "index.json").write_bytes(f"index-{kind}".encode())
        evidence[kind] = {
            "path": str(folder),
            "state_sha256": file_sha256(folder / "state.pt"),
            "index_sha256": file_sha256(folder / "index.json"),
            "checkpoint_identity": {"parent": provenance},
            "quality_run_id": f"run-{kind}",
        }
        if kind != "dense":
            cell = Cell(*pair, kind)
            record = p5_results / cell.label
            record.mkdir(parents=True)
            (record / "result.json").write_text(
                json.dumps(
                    {
                        "cell": cell.fields(),
                        "completed_steps": STEPS,
                        "final": {"target_tokens": 32768, "nll": synthetic.recorded[kind]["nll"]},
                        "checkpoint_state_sha256": {
                            f"checkpoint-{STEPS}": evidence[kind]["state_sha256"]
                        },
                    }
                )
            )
    models = {**synthetic.models, "dense": object()}
    monkeypatch.setattr(hierarchy, "_timing_models", lambda *a, **k: (models, evidence))
    monkeypatch.setattr(
        p5_data, "load_frozen", lambda *a, **k: (synthetic.train, None, synthetic.panel, None)
    )
    source = common.load_real_cell(
        pair,
        p5_suite=tmp_path / "suite",
        output_root=tmp_path / "out",
        p5_results=p5_results,
        data_dir=data_dir,
        run=tmp_path,
    )
    assert set(source.models) == set(source.evidence) == set(common.KINDS)
    assert source.files_unchanged() is True  # would raise KeyError('dense') before the fix
    assert all(
        e["recorded_final_nll"] == source.recorded[k]["nll"] for k, e in source.evidence.items()
    )
    (tmp_path / "cells" / FLAT / "state.pt").write_bytes(b"tampered")
    assert source.files_unchanged() is False
