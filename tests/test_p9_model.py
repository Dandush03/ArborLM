# ruff: noqa: E501
"""P9 package I2, ``studies/p9/model.py``: P5 forward invariance, chunking, rungs, gradient reach, codes,
branch hash, slot assignment, dense matching, parameter counts.

Uses a random frozen backbone, tiny fact tables and test seeds (>= 179001) only; no real data, no
registered seed, no training on registered or rehearsal data.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p9_model_support import (  # noqa: E402
    NON_SITES,
    SITES,
    TEST_SEED,
    Facts,
    backbone,
    base_cell,
)
from torch.nn import functional as F  # noqa: E402

from arborlm.p4_model import backbone_digest  # noqa: E402
from arborlm.pilot_model import EPS, TEMP, stable_top, tree_candidates  # noqa: E402
from studies.p9 import core, model  # noqa: E402
from studies.p9.model import AdditionSpec, build_model_from_spec  # noqa: E402
from studies.p9.train import answer_site_loss  # noqa: E402


def spec_of(arch: str = "flat", rung: str = "R0", slots: int = 4096, kw: int = 16) -> AdditionSpec:
    branches = core.BRANCHES[slots] if arch in ("fixed_tree", "learned_tree") else 0
    hidden = core.dense_hidden_width(slots) if arch == "dense" else 0
    return AdditionSpec(arch, slots, kw, rung, branches, hidden)


FACTS = Facts(256)
LUT = FACTS.lut()


def build(
    arch: str = "flat", rung: str = "R0", slots: int = 4096, kw: int = 16, seed: int = TEST_SEED
) -> model.P9Model:
    return build_model_from_spec(spec_of(arch, rung, slots, kw), seed, backbone(), fact_lut=LUT)


def tokens(contexts: int = 4, update: int = 1) -> torch.Tensor:
    return FACTS.batch(update, contexts=contexts)


def inputs(contexts: int = 4, update: int = 1) -> torch.Tensor:
    return tokens(contexts, update)[:, :-1]


# --- P5 forward invariance (gate G4) ---------------------------------------------------------------------
@pytest.mark.parametrize("variant", ["flat", "fixed_tree", "learned_tree"])
def test_p5_forward_invariance_exact(variant: str) -> None:
    g = torch.Generator().manual_seed(5)
    for toks in (
        torch.randint(0, 256, (6, 63), generator=g),
        inputs(6),
        torch.randint(0, 256, (3, 40), generator=g),
    ):
        result = model.p5_forward_invariance(backbone(), variant, TEST_SEED, toks)
        assert result["same_parameters"] is True
        assert result["max_abs_logit_difference"] == 0.0
        assert result["logits_identical"] is True
        assert result["selection_identical"] is True
        assert result["routing_identical"] is True


@pytest.mark.parametrize("variant", ["flat", "fixed_tree", "learned_tree"])
def test_p5_invariance_with_the_same_trained_looking_parameter_tensors(variant: str) -> None:
    """The same (perturbed, non-initial) parameter tensors give the same logits and selections."""
    from types import SimpleNamespace
    from typing import Any, cast

    from arborlm.p5_model import Model

    reference = Model(cast(Any, SimpleNamespace(variant=variant, seed=TEST_SEED)), backbone())
    g = torch.Generator().manual_seed(11)
    with torch.no_grad():
        for p in reference.addition.parameters():  # type: ignore[union-attr]
            p.add_(torch.randn(p.shape, generator=g) * 0.3)
        reference.addition.gate.fill_(0.7)  # type: ignore[union-attr]
    branches = 0 if variant == "flat" else 16
    mine = build_model_from_spec(AdditionSpec(variant, 4096, 16, "R0", branches, 0), 1, backbone())
    mine.load_state_dict(reference.state_dict(), strict=True)
    toks = inputs(5)
    with torch.no_grad():
        logits, selection = mine(toks)
        ref_logits, lookup = reference(toks)
    assert selection is not None and lookup is not None
    assert torch.equal(logits, ref_logits)
    assert torch.equal(selection.selected.reshape(-1, 8), lookup.selected)


def test_p5_invariance_rejects_unknown_variant() -> None:
    with pytest.raises(ValueError):
        model.p5_forward_invariance(backbone(), "product_key", TEST_SEED, inputs(2))


# --- chunking ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("arch", ["flat", "learned_tree"])
def test_chunked_equals_unchunked(arch: str) -> None:
    whole, chunked = build(arch), build(arch)
    assert isinstance(whole.addition, model.ScalableMemory) and isinstance(
        chunked.addition, model.ScalableMemory
    )
    chunked.addition.chunk_elements = (
        4096 * 3 if arch == "flat" else 512 * 16 * 3
    )  # 3 queries per chunk
    toks = tokens(4)
    outputs = []
    for m in (whole, chunked):
        logits, selection = m(toks[:, :-1])
        assert selection is not None
        loss = answer_site_loss(logits, toks)
        loss.backward()  # type: ignore[no-untyped-call]
        outputs.append(
            (
                logits,
                selection,
                loss.detach(),
                {n: p.grad.clone() for n, p in m.named_parameters() if p.grad is not None},
            )
        )
    (l0, s0, loss0, g0), (l1, s1, loss1, g1) = outputs
    assert torch.equal(s0.selected, s1.selected)
    assert s0.candidate_ids is not None and s1.candidate_ids is not None
    assert torch.equal(s0.candidate_ids, s1.candidate_ids)
    assert s0.candidate_scores is not None and s1.candidate_scores is not None
    if sys.platform == "darwin":  # the platform of record (macOS arm64): bit for bit
        assert torch.equal(s0.scores, s1.scores)
        assert torch.equal(s0.candidate_scores, s1.candidate_scores)
        assert torch.equal(l0, l1)
    else:  # other BLAS builds round the row-block products differently (Linux x86-64 CI, 2026-11-15)
        assert torch.allclose(s0.scores, s1.scores, rtol=0.0, atol=1e-6)
        assert torch.allclose(s0.candidate_scores, s1.candidate_scores, rtol=0.0, atol=1e-6)
        assert torch.allclose(l0, l1, rtol=0.0, atol=1e-5)
    if sys.platform == "darwin":
        assert torch.equal(loss0, loss1)
    else:
        assert torch.allclose(loss0, loss1, rtol=0.0, atol=1e-5)
    assert g0.keys() == g1.keys()
    for (
        name
    ) in g0:  # the shared key table accumulates chunk gradients: allow float32 summation order
        torch.testing.assert_close(g0[name], g1[name], rtol=1e-5, atol=1e-9)


def test_chunk_rows_bound_the_score_matrix() -> None:
    mem = build("flat", slots=65536).addition
    assert isinstance(mem, model.ScalableMemory)
    rows = mem._rows(65536)
    assert 1 <= rows and rows * 65536 <= model.SCORE_CHUNK_ELEMENTS
    assert mem._rows(10**12) == 1  # a single row is the floor


# --- selection semantics: exact ties, tree equivalence ------------------------------------------------------
def _query_and_routes(
    m: model.P9Model, toks: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor | None]:
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory)
    h = m.embed_block0(toks)
    positions = torch.arange(h.shape[1])
    q = mem._query(h, toks, positions)
    routes = None
    if mem.router is not None:
        routes = (q @ F.normalize(mem.router, dim=-1, eps=EPS).T) / TEMP
    return q, routes


def test_flat_ties_are_broken_by_slot_id_exactly_like_stable_top() -> None:
    m = build("flat")
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory)
    with torch.no_grad():
        mem.keys.copy_(torch.ones_like(mem.keys))  # every score ties
    toks = inputs(2)
    _, selection = m(toks)
    assert selection is not None and selection.candidate_ids is not None
    assert torch.equal(selection.selected[0, 0], torch.arange(8))
    assert torch.equal(selection.candidate_ids[0, 0], torch.arange(64))
    q, _ = _query_and_routes(m, toks)
    dense_scores = (q @ F.normalize(mem.keys, dim=-1, eps=EPS).T) / TEMP
    _, expected = stable_top(dense_scores, 8)
    assert torch.equal(selection.selected.reshape(-1, 8), expected)
    # partial ties: two identical rows must come out in id order wherever both are selected
    m2 = build("flat")
    mem2 = m2.addition
    assert isinstance(mem2, model.ScalableMemory)
    with torch.no_grad():
        mem2.keys[700] = mem2.keys[20]
    _, sel2 = m2(toks)
    q2, _ = _query_and_routes(m2, toks)
    _, expected2 = stable_top((q2 @ F.normalize(mem2.keys, dim=-1, eps=EPS).T) / TEMP, 8)
    assert sel2 is not None and torch.equal(sel2.selected.reshape(-1, 8), expected2)


@pytest.mark.parametrize("arch", ["fixed_tree", "learned_tree"])
@pytest.mark.parametrize("constant_keys", [False, True])
def test_tree_selection_equals_pilot_tree_candidates(arch: str, constant_keys: bool) -> None:
    m = build(arch)
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory) and mem.router is not None
    if constant_keys:
        with torch.no_grad():
            mem.keys.copy_(torch.ones_like(mem.keys))
    toks = inputs(3)
    _, selection = m(toks)
    q, routes = _query_and_routes(m, toks)
    assert selection is not None and routes is not None and selection.branches is not None
    values, selected, candidates, branches = tree_candidates(q, mem.keys, routes)
    assert torch.equal(selection.selected.reshape(-1, 8), selected)
    assert torch.equal(selection.scores.reshape(-1, 8), values)
    assert torch.equal(selection.branches.reshape(-1, 2), branches)
    assert selection.candidate_ids is not None
    assert torch.equal(selection.candidate_ids[..., :8].reshape(-1, 8), selected)
    # the 64 candidates come from the 2 x 256 visited slots only
    visited = (branches[..., None] * 256 + torch.arange(256)).flatten(1)
    flat_candidates = selection.candidate_ids.reshape(-1, 64)
    assert bool((flat_candidates[:, :, None] == visited[:, None, :]).any(-1).all())
    # candidate scores are in descending order
    cs = selection.candidate_scores
    assert cs is not None and bool((cs[..., :-1] >= cs[..., 1:]).all())


# --- positions, rungs, delta ------------------------------------------------------------------------------------
def test_read_positions_by_rung() -> None:
    assert spec_of("flat", "R0").read_positions == tuple(range(63))
    assert spec_of("learned_tree", "OB").read_positions == tuple(range(63))
    for rung in ("R0a", "R1", "R2"):
        assert spec_of("flat", rung).read_positions == SITES
    assert spec_of("dense").read_positions == tuple(range(63))


@pytest.mark.parametrize(
    ("arch", "rung"),
    [("flat", "R0a"), ("flat", "R1"), ("flat", "R2"), ("learned_tree", "R1")],
)
def test_answer_site_rungs_read_only_at_the_answer_sites(arch: str, rung: str) -> None:
    m = build(arch, rung)
    with torch.no_grad():
        m.addition.gate.fill_(2.0)  # type: ignore[union-attr]
        m.addition.wo.normal_(0, 0.5, generator=torch.Generator().manual_seed(3))  # type: ignore[union-attr]
    h = m.embed_block0(inputs(4))
    selection = m.select(h, inputs(4))
    assert selection is not None and torch.equal(selection.positions, torch.tensor(SITES))
    delta = m.memory_delta(h, selection)
    assert delta.shape == h.shape
    assert bool((delta[:, list(NON_SITES)] == 0).all())
    assert bool((delta[:, list(SITES)] != 0).any())


def test_r0_reads_everywhere_and_dense_and_disabled() -> None:
    m = build("flat", "R0")
    h = m.embed_block0(inputs(2))
    selection = m.select(h, inputs(2))
    assert selection is not None and selection.selected.shape == (2, 63, 8)
    assert selection.candidate_ids is not None and selection.candidate_ids.shape == (2, 63, 64)
    delta = m.memory_delta(h, selection)
    assert bool((delta.abs().sum(-1) > 0).all())
    assert bool((m.memory_delta(h, selection, disabled=True) == 0).all())
    dense = build("dense")
    hd = dense.embed_block0(inputs(2))
    assert dense.select(hd, inputs(2)) is None
    assert bool((dense.memory_delta(hd, None) != 0).any())
    assert bool((dense.memory_delta(hd, None, disabled=True) == 0).all())


def test_knockout_values_and_weights() -> None:
    m = build("flat", "R0")
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory)
    with torch.no_grad():
        mem.gate.fill_(1.0)
    h = m.embed_block0(inputs(2))
    selection = m.select(h, inputs(2))
    assert selection is not None
    full = m.memory_delta(h, selection)
    everything = torch.ones_like(selection.selected, dtype=torch.bool)
    assert bool((m.memory_delta(h, selection, knockout=everything) == 0).all())
    none = torch.zeros_like(everything)
    assert torch.equal(m.memory_delta(h, selection, knockout=none), full)
    one = none.clone()
    one[:, :, 0] = True
    partial = m.memory_delta(h, selection, knockout=one)
    assert not torch.equal(partial, full)
    # weights and selections are untouched by the knock-out (not renormalised): rebuild by hand
    w = selection.weights()
    manual = (w * (~one))[..., None] * mem.values[selection.selected]
    expected = mem.gate.sigmoid() * F.linear(manual.sum(-2), mem.wo)
    torch.testing.assert_close(partial, expected, rtol=1e-5, atol=1e-8)
    permuted = mem.values[torch.randperm(4096, generator=torch.Generator().manual_seed(1))]
    assert not torch.equal(m.memory_delta(h, selection, values=permuted), full)
    with pytest.raises(ValueError):
        m.memory_delta(h, selection, knockout=everything[:, :5])


def test_selection_weights_are_a_softmax_of_the_scores() -> None:
    m = build("flat")
    _, selection = m(inputs(2))
    assert selection is not None
    w = selection.weights()
    torch.testing.assert_close(w.sum(-1), torch.ones(w.shape[:2]))
    assert torch.equal(w, selection.scores.softmax(-1))


# --- gradient reach per parameter group and rung -------------------------------------------------------------------
def _grads(m: model.P9Model, contexts: int = 4) -> dict[str, torch.Tensor | None]:
    m.zero_grad(set_to_none=True)
    toks = tokens(contexts)
    logits, _ = m(toks[:, :-1])
    answer_site_loss(logits, toks).backward()  # type: ignore[no-untyped-call]
    return {n: p.grad for n, p in m.named_parameters()}


def _reached(grad: torch.Tensor | None) -> bool:
    return grad is not None and bool(grad.isfinite().all()) and bool((grad != 0).any())


@pytest.mark.parametrize(
    ("arch", "rung", "present", "absent"),
    [
        ("flat", "R0", {"keys", "values", "wq", "wo", "gate"}, {"router"}),
        ("flat", "R0a", {"keys", "values", "wq", "wo", "gate"}, {"router"}),
        ("fixed_tree", "R0", {"keys", "values", "wq", "wo", "gate"}, {"router"}),
        ("learned_tree", "R0", {"keys", "values", "wq", "wo", "gate", "router"}, set()),
        ("flat", "R1", {"keys", "values", "wo", "gate"}, {"wq", "router"}),
        ("learned_tree", "R1", {"keys", "values", "wo", "gate", "router"}, {"wq"}),
        ("flat", "R2", {"values", "wo", "gate"}, {"keys", "wq", "router"}),
        ("learned_tree", "OB", {"keys", "values", "wq", "wo", "gate"}, {"router"}),
    ],
)
def test_gradient_reach_by_rung(arch: str, rung: str, present: set[str], absent: set[str]) -> None:
    m = build(arch, rung)
    grads = _grads(m)
    names = {n.removeprefix("addition.") for n in grads if n.startswith("addition.")}
    assert names == present  # the tensors that exist are exactly the ones the ADR trains
    for name in absent:
        assert (
            not hasattr(m.addition, name)
            or getattr(m.addition, name) is None
            or not isinstance(getattr(m.addition, name), torch.nn.Parameter)
        )
    for name in present:
        assert _reached(grads[f"addition.{name}"]), name
    # frozen backbone: no gradient, no requires_grad
    assert all(not p.requires_grad and p.grad is None for p in m.backbone.parameters())
    assert all(p.requires_grad for n, p in m.addition.named_parameters())


def test_fixed_tree_router_is_a_buffer_without_gradient() -> None:
    m = build("fixed_tree")
    grads = _grads(m)
    assert "addition.router" not in grads
    assert "router" in dict(m.addition.named_buffers())
    assert not m.addition.router.requires_grad  # type: ignore[union-attr]


def test_dense_gradient_reach_and_groups() -> None:
    m = build("dense")
    grads = _grads(m)
    assert {n for n in grads if n.startswith("addition.")} == {
        "addition.w1",
        "addition.w2",
        "addition.gate",
    }
    assert all(_reached(grads[n]) for n in grads if n.startswith("addition."))
    groups = model.trainable_groups(m)
    assert [n for n, _ in groups["dense"]] == ["addition.w1", "addition.w2", "addition.gate"]
    assert not any(groups[g] for g in ("keys", "values", "router", "projections"))


def test_value_and_key_rows_with_gradient_are_exactly_the_selected_rows() -> None:
    m = build("flat")
    toks = tokens(4)
    logits, selection = m(toks[:, :-1])
    assert selection is not None
    answer_site_loss(logits, toks).backward()  # type: ignore[no-untyped-call]
    selected = set(selection.selected.unique().tolist())
    value_rows = set((m.addition.values.grad != 0).any(-1).nonzero().flatten().tolist())  # type: ignore[union-attr]
    key_rows = set((m.addition.keys.grad != 0).any(-1).nonzero().flatten().tolist())  # type: ignore[union-attr]
    assert value_rows <= selected and len(value_rows) > 0.9 * len(selected)
    assert key_rows <= selected and len(key_rows) > 0.9 * len(selected)


def test_unselected_rows_have_no_task_gradient_under_r2() -> None:
    m = build("flat", "R2")
    toks = tokens(4)
    logits, selection = m(toks[:, :-1])
    assert selection is not None
    answer_site_loss(logits, toks).backward()  # type: ignore[no-untyped-call]
    rows = set((m.addition.values.grad != 0).any(-1).nonzero().flatten().tolist())  # type: ignore[union-attr]
    assert rows == set(selection.selected.flatten().tolist())


def test_finite_difference_matches_autograd_in_float64() -> None:
    m = build("flat")
    m.double()
    toks = tokens(3)

    def loss_value() -> float:
        with torch.no_grad():
            logits, _ = m(toks[:, :-1])
            return float(answer_site_loss(logits, toks))

    logits, selection = m(toks[:, :-1])
    assert logits.dtype == torch.float64 and selection is not None
    answer_site_loss(logits, toks).backward()  # type: ignore[no-untyped-call]
    mem = m.addition
    row = int(selection.selected[0, SITES[0], 0])
    probes = [
        ("gate", mem.gate, ()),
        ("wo", mem.wo, (1, 2)),
        ("wq", mem.wq, (3, 5)),
        ("values", mem.values, (row, 4)),
        ("keys", mem.keys, (row, 3)),
    ]
    for name, param, index in probes:
        analytic = float(param.grad[index])
        eps = 1e-6
        with torch.no_grad():
            param[index] += eps
            up = loss_value()
            param[index] -= 2 * eps
            down = loss_value()
            param[index] += eps
        numeric = (up - down) / (2 * eps)
        assert analytic == pytest.approx(numeric, rel=1e-4, abs=1e-9), name


def test_frozen_backbone_does_not_change_under_updates() -> None:
    from studies.p9.objective import Objective
    from studies.p9.train import Trainer, build_optimizer

    cell = base_cell()
    m = model.build_model(cell, backbone(), init_seed=TEST_SEED)
    before = backbone_digest(m.backbone)
    trainer = Trainer(cell, m, build_optimizer(m, cell), Objective(cell))
    for u in (1, 2, 3):
        trainer.step(tokens(16, u))
    assert backbone_digest(m.backbone) == before
    assert all(p.grad is None and not p.requires_grad for p in m.backbone.parameters())


# --- codes, hashes, slots ------------------------------------------------------------------------------------------------
def test_unit_codes_golden_values_and_norms() -> None:
    assert [round(x, 9) for x in model.unit_code(170101, 12345, 4)] == [
        0.55919437,
        0.712911895,
        0.232743181,
        0.353396234,
    ]
    assert [model.branch_of(170102, c, 64) for c in (0, 1, 12345, 999999)] == [45, 15, 35, 48]
    assert [model.branch_of(170102, c, 256) for c in (0, 1, 12345, 999999)] == [237, 143, 35, 112]
    for width in (16, 32):
        for ident in (0, 1, 2, 777, 32**4 - 1):
            code = model.unit_code(170101, ident, width)
            assert len(code) == width
            assert sum(v * v for v in code) == pytest.approx(1.0, abs=1e-12)
            assert code == model.unit_code(170101, ident, width)  # deterministic
    assert model.unit_code(170101, 5, 16) != model.unit_code(170101, 6, 16)
    assert model.unit_code(170101, 5, 16) != model.unit_code(170102, 5, 16)


@pytest.mark.parametrize("kw", [16, 32])
def test_r1_codes_are_per_fact_unit_norm_and_context_independent(kw: int) -> None:
    m = build("flat", "R1", kw=kw)
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory)
    toks = FACTS.batch(1, contexts=16)
    codes = mem._oracle_codes(toks[:, :-1])
    assert codes.shape == (16, 8, kw)
    torch.testing.assert_close(codes.norm(dim=-1), torch.ones(16, 8), rtol=0, atol=1e-6)
    # one fact -> one code, whatever its context, record index, separator, binding byte or answer
    a = FACTS.context([0, 1, 2, 3, 4, 5, 6, 7], separator=0x20, binding=0x2C)[None]
    b = FACTS.context([9, 8, 7, 6, 5, 4, 3, 0], separator=0x65, binding=0x74)[None]
    ca, cb = mem._oracle_codes(a[:, :-1]), mem._oracle_codes(b[:, :-1])
    assert torch.equal(ca[0, 0], cb[0, 7])  # fact 0
    assert torch.equal(ca[0, 7], cb[0, 2])  # fact 7
    assert not torch.equal(ca[0, 1], ca[0, 2])
    fresh = build("flat", "R1", kw=kw).addition
    assert torch.equal(fresh._oracle_codes(a[:, :-1]), ca)  # type: ignore[union-attr]  # deterministic across instances
    other = model.ScalableMemory(spec_of("flat", "R1", kw=kw), TEST_SEED, r1_seed=7)
    assert not torch.equal(other._oracle_codes(a[:, :-1]), ca)
    # the answer byte (not an input at the answer site) never enters the code
    a2 = a.clone()
    a2[0, 7] = 0x41
    assert torch.equal(mem._oracle_codes(a2[:, :-1]), ca)


def test_r1_selection_uses_the_code_as_the_query() -> None:
    m = build("flat", "R1")
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory)
    toks = inputs(2)
    h = m.embed_block0(toks)
    selection = m.select(h, toks)
    assert selection is not None and selection.candidate_scores is not None
    codes = mem._oracle_codes(toks).reshape(-1, 16)
    dense = (codes @ F.normalize(mem.keys, dim=-1, eps=EPS).T) / TEMP
    _, expected = stable_top(dense, 8)
    assert torch.equal(selection.selected.reshape(-1, 8), expected)


def test_r2_slot_assignment_is_injective_and_unseen_facts_read_nothing() -> None:
    m = build("flat", "R2")
    toks = FACTS.batch(1, contexts=16)  # 128 distinct facts
    h = m.embed_block0(toks[:, :-1])
    selection = m.select(h, toks[:, :-1])
    assert selection is not None and selection.selected.shape == (16, 8, 1)
    slots = selection.selected.flatten()
    assert slots.unique().numel() == 128  # injective
    expected = torch.arange(128)  # batch(1) holds facts 0..127 in order
    assert torch.equal(slots, expected)
    assert selection.candidate_ids is None and selection.branches is None
    torch.testing.assert_close(selection.weights(), torch.ones(16, 8, 1))
    # an identifier with no slot: -1, contributes nothing
    extra = Facts(300)
    unseen = extra.context(list(range(280, 288)))[None]
    sel = m.select(m.embed_block0(unseen[:, :-1]), unseen[:, :-1])
    assert sel is not None and bool((sel.selected == -1).all())
    assert bool((m.memory_delta(m.embed_block0(unseen[:, :-1]), sel) == 0).all())
    # the table size does not matter, only the lookup
    assert FACTS.lut().max() == 255 and bool((FACTS.lut()[FACTS.codes] == torch.arange(256)).all())
    with pytest.raises(ValueError):
        build_model_from_spec(spec_of("flat", "R2"), 1, backbone())


def test_oracle_branch_hash_is_deterministic_and_selection_stays_in_the_branch() -> None:
    m = build("learned_tree", "OB")
    mem = m.addition
    assert isinstance(mem, model.ScalableMemory) and mem.router is None
    toks = FACTS.batch(1, contexts=4)
    h = m.embed_block0(toks[:, :-1])
    s1 = m.select(h, toks[:, :-1])
    s2 = build("learned_tree", "OB").select(h, toks[:, :-1])
    assert s1 is not None and s2 is not None and s1.branches is not None and s2.branches is not None
    assert torch.equal(s1.branches, s2.branches) and torch.equal(s1.selected, s2.selected)
    assert s1.branches.shape == (4, 63, 1) and s1.route_scores is None
    assert bool(((s1.branches >= 0) & (s1.branches < 16)).all())
    codes = model.identifier_codes(toks[:, :-1])
    for b in range(4):
        for p in (0, 3, 6, 7, 8, 30, 62):
            assert int(s1.branches[b, p, 0]) == model.branch_of(
                mem.branch_seed, int(codes[b, p // 8]), 16
            )
    # all candidates and selections lie inside the hashed branch
    assert s1.candidate_ids is not None
    lo = s1.branches * 256
    assert bool(((s1.candidate_ids >= lo) & (s1.candidate_ids < lo + 256)).all())
    # one identifier -> one branch, whatever the context
    ctx1 = FACTS.context([0, 1, 2, 3, 4, 5, 6, 7])[None]
    ctx2 = FACTS.context([8, 9, 10, 0, 11, 12, 13, 14], separator=0x65)[None]
    b1 = m.select(m.embed_block0(ctx1[:, :-1]), ctx1[:, :-1])
    b2 = m.select(m.embed_block0(ctx2[:, :-1]), ctx2[:, :-1])
    assert b1 is not None and b2 is not None and b1.branches is not None and b2.branches is not None
    assert int(b1.branches[0, 6, 0]) == int(
        b2.branches[0, 30, 0]
    )  # fact 0 at record 0 and record 3
    # a different branch seed changes the assignment
    other = model.ScalableMemory(spec_of("learned_tree", "OB"), TEST_SEED, branch_seed=3)
    assert other.branch_seed != mem.branch_seed


def test_identifier_codes_match_the_encode_identifiers_convention() -> None:
    toks = FACTS.batch(1, contexts=2)[:, :-1]
    codes = model.identifier_codes(toks)
    assert torch.equal(codes[0], FACTS.codes[:8])
    assert torch.equal(codes[1], FACTS.codes[8:16])
    with pytest.raises(ValueError):
        model.identifier_codes(toks[:, :30])


# --- dense adapter, counts, groups -------------------------------------------------------------------------------------
@pytest.mark.parametrize("slots", list(core.SLOTS_BY_SIZE))
def test_dense_adapter_matches_the_flat_key16_memory(slots: int) -> None:
    hidden = core.dense_hidden_width(slots)
    dense = model.DenseAdapter(hidden, TEST_SEED)
    flat = model.ScalableMemory(spec_of("flat", "R0", slots), TEST_SEED)
    n_dense = sum(p.numel() for p in dense.parameters())
    n_flat = sum(p.numel() for p in flat.parameters())
    assert n_dense == 64 * hidden + 1 == n_flat == core.memory_parameters("flat", slots)
    assert (
        abs(n_dense - core.memory_parameters("learned_tree", slots)) / n_dense < 0.002
    )  # the 0.2% tree tolerance
    cell = base_cell(arch="dense", slots=slots)
    assert AdditionSpec.from_cell(cell).hidden == hidden


def test_dense_adapter_structure_follows_p4() -> None:
    from arborlm.p4_model import DenseAdapter as P4Dense

    ref = P4Dense(TEST_SEED)
    mine = model.DenseAdapter(3100, TEST_SEED)  # the P4 width: identical init and forward
    assert (
        torch.equal(mine.w1, ref.w1)
        and torch.equal(mine.w2, ref.w2)
        and torch.equal(mine.gate, ref.gate)
    )
    h = torch.randn(2, 5, 32, generator=torch.Generator().manual_seed(1))
    assert torch.equal(h + mine.delta(h), ref(h)[0])


def test_parameter_counts_match_p5_and_core() -> None:
    expect = {
        "flat": (198145, 225537),
        "fixed_tree": (198145, 225793),
        "learned_tree": (198401, 225793),
    }
    for arch, (trainable, stored) in expect.items():
        counts = model.parameter_counts(build(arch))
        assert counts.frozen_backbone == 27392
        assert counts.trainable == trainable == core.memory_parameters(arch, 4096)
        assert counts.stored == stored
        assert counts.initialized_slots == 4096
        assert sum(counts.by_group.values()) == counts.trainable
    dense = model.parameter_counts(build("dense"))
    assert (
        dense.trainable == 198145
        and dense.initialized_slots == 0
        and dense.by_group["dense"] == 198145
    )
    wide = model.parameter_counts(build("flat", slots=16384, kw=32))
    assert wide.trainable == core.memory_parameters("flat", 16384, 32)
    assert (
        model.parameter_counts(build("flat", "R1")).trainable
        == core.memory_parameters("flat", 4096) - 16 * 32
    )
    assert model.parameter_counts(build("flat", "R2")).trainable == 4096 * 32 + 32 * 32 + 1
    assert model.parameter_counts(build("learned_tree", "OB")).trainable == core.memory_parameters(
        "flat", 4096
    )
    assert (
        model.parameter_counts(build("learned_tree", "R1")).trainable
        == core.memory_parameters("learned_tree", 4096) - 16 * 32
    )
    for slots in (16384, 65536):
        assert model.parameter_counts(
            build("learned_tree", slots=slots)
        ).trainable == core.memory_parameters("learned_tree", slots)


def test_trainable_groups_and_set_trainable() -> None:
    m = build("learned_tree")
    groups = model.trainable_groups(m)
    assert set(groups) == set(model.PARAMETER_GROUP_NAMES)
    assert [n for n, _ in groups["projections"]] == ["addition.wq", "addition.wo", "addition.gate"]
    assert [n for n, _ in groups["router"]] == ["addition.router"]
    model.set_trainable(m, ("keys", "values"))  # Lane D memory-only
    after = model.trainable_groups(m)
    assert [n for n, _ in after["keys"]] == ["addition.keys"] and [
        n for n, _ in after["values"]
    ] == ["addition.values"]
    assert after["projections"] == [] and after["router"] == []
    assert not m.addition.wq.requires_grad and not m.addition.gate.requires_grad  # type: ignore[union-attr]
    with pytest.raises(ValueError):
        model.set_trainable(m, ("nonsense",))
    r2 = build("flat", "R2")
    model.set_trainable(r2, model.PARAMETER_GROUP_NAMES)  # never unfreezes or invents tensors
    assert model.parameter_counts(r2).trainable == 4096 * 32 + 32 * 32 + 1


def test_spec_validation_and_from_cell() -> None:
    with pytest.raises(ValueError):
        AdditionSpec("flat", 4096, 16, "OB", 0, 0)
    with pytest.raises(ValueError):
        AdditionSpec("flat", 4096, 16, "R0", 16, 0)
    with pytest.raises(ValueError):
        AdditionSpec("learned_tree", 4096, 16, "R0", 0, 0)
    with pytest.raises(ValueError):
        AdditionSpec("dense", 4096, 16, "R0", 0, 0)
    cell = base_cell(arch="learned_tree", slots=16384)
    spec = AdditionSpec.from_cell(cell)
    assert (spec.arch, spec.branches, spec.per_branch, spec.hidden) == ("learned_tree", 64, 256, 0)
    with pytest.raises(ValueError):
        model.ScalableMemory(spec_of("dense"), 1)


def test_forward_shape_dtype_and_input_validation() -> None:
    m = build("flat")
    logits, _ = m(inputs(2))
    assert logits.shape == (2, 63, 256) and logits.dtype == torch.float32
    with pytest.raises(ValueError):
        m(torch.zeros((2, 63), dtype=torch.int32))
    with pytest.raises(ValueError):
        m(torch.full((2, 63), 300, dtype=torch.int64))
    with pytest.raises(ValueError):
        build("flat", "R1")(torch.zeros((2, 30), dtype=torch.int64))


def test_initialization_matches_pilot_matrix_seeds() -> None:
    from arborlm.pilot_model import _matrix

    mem = build("learned_tree", seed=TEST_SEED).addition
    assert isinstance(mem, model.ScalableMemory)
    assert torch.equal(mem.keys, _matrix(TEST_SEED + 1000, 4096, 16))
    assert torch.equal(mem.values, _matrix(TEST_SEED + 2000, 4096, 32))
    assert torch.equal(mem.wq, _matrix(TEST_SEED + 3000, 16, 32))
    assert torch.equal(mem.wo, _matrix(TEST_SEED + 4000, 32, 32))
    assert torch.equal(mem.router, _matrix(TEST_SEED + 5000, 16, 16))  # type: ignore[arg-type]
    assert float(mem.gate) == -2.0
