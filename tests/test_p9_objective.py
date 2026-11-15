# ruff: noqa: E501
"""P9 package I2, ``studies/p9/objective.py``: soft inclusion, the global usage floor and its b-free
gradient, R_co against ``p8_objective`` and an independent reference, coefficients, diagnostics.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p9_model_support import base_cell, variant  # noqa: E402

from arborlm import p8_objective  # noqa: E402
from studies.p9 import core, objective  # noqa: E402
from studies.p9.model import Selection  # noqa: E402


def candidates(
    q: int, slots: int, seed: int, dtype: torch.dtype = torch.float32
) -> tuple[torch.Tensor, torch.Tensor]:
    """Sorted descending top-64 candidate scores in the cosine/0.2 range and distinct slot ids."""
    g = torch.Generator().manual_seed(seed)
    scores = (
        (torch.rand(q, 64, generator=g, dtype=dtype) * 6 - 1).sort(descending=True, dim=-1).values
    )
    ids = torch.stack([torch.randperm(slots, generator=g)[:64] for _ in range(q)])
    return scores, ids


def selection_of(scores: torch.Tensor, ids: torch.Tensor, positions: tuple[int, ...]) -> Selection:
    """A hand-made selection with the given ``[B * P, 64]`` candidates at ``positions``."""
    p = len(positions)
    b = scores.shape[0] // p
    s, i = scores.reshape(b, p, 64), ids.reshape(b, p, 64)
    return Selection(torch.tensor(positions), i[..., :8], s[..., :8], i, s, None, None, 63)


# --- soft inclusion -------------------------------------------------------------------------------------------------------
def test_soft_inclusion_matches_p8_values_and_gradients() -> None:
    g = torch.Generator().manual_seed(1)
    raw = torch.randn(12, 4096, generator=g, requires_grad=True)
    ids = torch.arange(4096).expand(12, -1)
    theirs = p8_objective.soft_inclusion(raw, ids)
    top, index = raw.topk(64, dim=-1, sorted=True)
    mine = objective.soft_inclusion_full(top)
    assert torch.equal(mine.pi, theirs.pi) and torch.equal(mine.log_miss, theirs.log_miss)
    assert torch.equal(mine.gap, theirs.gap)
    assert torch.equal(index, theirs.ids)
    weights = torch.rand(12, 64, generator=g)
    (g1,) = torch.autograd.grad(
        (mine.pi * weights).sum() + (mine.log_miss * weights).sum(), raw, retain_graph=True
    )
    (g2,) = torch.autograd.grad(
        (theirs.pi * weights).sum() + (theirs.log_miss * weights).sum(), raw
    )
    torch.testing.assert_close(g1, g2, rtol=0, atol=0)
    assert torch.equal(objective.soft_inclusion(top), mine.pi)


def test_soft_inclusion_tau_is_the_midpoint_and_not_detached() -> None:
    scores = torch.linspace(5, -5, 64).expand(2, -1).clone().requires_grad_(True)
    pi = objective.soft_inclusion(scores)
    tau = 0.5 * (scores[:, 7] + scores[:, 8])
    expected = torch.sigmoid((scores - tau[:, None]) / 0.25)
    assert torch.equal(pi, expected)
    # pi sums to 8 at the symmetric midpoint design only approximately; the gradient w.r.t. the 8th score
    # of the 9th candidate's pi must include the tau path (a detached tau would give a different value)
    (grad,) = torch.autograd.grad(pi[0, 8], scores)
    detached = torch.sigmoid((scores - tau.detach()[:, None]) / 0.25)
    (grad_detached,) = torch.autograd.grad(detached[0, 8], scores)
    assert grad[0, 7] != 0 and grad_detached[0, 7] == 0


# --- R_co -------------------------------------------------------------------------------------------------------------------
def test_coaccess_matches_p8_on_a_4096_slot_case() -> None:
    g = torch.Generator().manual_seed(2)
    raw = torch.randn(16, 4096, generator=g, requires_grad=True)
    ids = torch.arange(4096).expand(16, -1)
    theirs = p8_objective.r_co(p8_objective.soft_inclusion(raw, ids))
    top, _ = raw.topk(64, dim=-1, sorted=True)
    top_ids = raw.topk(64, dim=-1, sorted=True).indices
    soft = objective.soft_inclusion_full(top)
    mine = objective.coaccess_term(soft.pi, top_ids, 4096, soft.log_miss)
    assert float(mine) == float(theirs)
    (g1,) = torch.autograd.grad(mine, raw, retain_graph=True)
    (g2,) = torch.autograd.grad(theirs, raw)
    torch.testing.assert_close(g1, g2, rtol=0, atol=0)
    assert float(mine) > core.CO_BEST


def test_coaccess_matches_an_independent_float64_reference() -> None:
    scores, ids = candidates(6, 128, 3, torch.float64)
    scores.requires_grad_(True)
    soft = objective.soft_inclusion_full(scores)
    mine = objective.coaccess_term(soft.pi, ids, 128, soft.log_miss)

    def reference(s: torch.Tensor) -> torch.Tensor:
        total = s.new_zeros(())
        for row in range(s.shape[0]):
            tau = 0.5 * (s[row, 7] + s[row, 8])
            pi = torch.sigmoid((s[row] - tau) / 0.25)
            touched = s.new_zeros(())
            for group in range(16):  # slot groups of 8
                member = (ids[row] // 8) == group
                touched = (
                    touched + (1.0 - torch.prod(1.0 - pi[member]))
                    if bool(member.any())
                    else touched
                )
            total = total + touched / pi.sum()
        return total / s.shape[0]

    ref = reference(scores)
    assert float(mine) == pytest.approx(float(ref), rel=1e-12)
    (g1,) = torch.autograd.grad(mine, scores, retain_graph=True)
    (g2,) = torch.autograd.grad(ref, scores)
    torch.testing.assert_close(g1, g2, rtol=1e-9, atol=1e-12)


def test_coaccess_best_and_worst_values() -> None:
    group = torch.zeros(1, 64, dtype=torch.float64)
    group[0, :8] = 1 - 1e-12  # one whole 8-slot group selected: the best value 1/8
    ids = torch.arange(64).reshape(1, 64)
    best = objective.coaccess_term(group, ids, 128, torch.log1p(-group))
    assert float(best) == pytest.approx(core.CO_BEST, abs=1e-9)
    spread = torch.zeros(1, 64, dtype=torch.float64)
    spread[0, :8] = 1 - 1e-12  # eight selected slots, each in its own group: the worst value 1
    rest = torch.arange(1024)[torch.arange(1024) % 8 != 0][
        :56
    ]  # distinct slots outside the 8 chosen groups
    ids2 = torch.cat([torch.arange(8) * 8, rest]).reshape(1, 64)
    worst = objective.coaccess_term(spread, ids2, 1024, torch.log1p(-spread))
    assert float(worst) == pytest.approx(1.0, abs=1e-9)


# --- slot usage and entropy -------------------------------------------------------------------------------------------
def test_slot_usage_is_normalized_scatter_and_differentiable() -> None:
    scores, ids = candidates(5, 4096, 4)
    scores.requires_grad_(True)
    pi = objective.soft_inclusion(scores)
    u = objective.slot_usage(pi, ids, 4096)
    assert u.shape == (4096,) and float(u.sum()) == pytest.approx(1.0, abs=1e-6)
    manual = torch.zeros(4096)
    for row in range(5):
        for k in range(64):
            manual[ids[row, k]] += pi[row, k].detach()
    torch.testing.assert_close(u.detach(), manual / manual.sum(), rtol=1e-5, atol=1e-9)
    (grad,) = torch.autograd.grad(u[ids[0, 0]], scores)
    assert bool((grad != 0).any())


def test_usage_entropy_zero_log_zero_is_zero() -> None:
    uniform = torch.full((8,), 1 / 8)
    assert float(objective.usage_entropy(uniform)) == pytest.approx(math.log(8), rel=1e-6)
    with_zeros = torch.tensor([0.5, 0.5, 0.0, 0.0])
    assert float(objective.usage_entropy(with_zeros)) == pytest.approx(math.log(2), rel=1e-6)
    assert float(objective.usage_entropy(torch.tensor([1.0, 0.0]))) == 0.0
    assert (
        bool(torch.isfinite(objective.usage_entropy(torch.zeros(4))))
        and float(objective.usage_entropy(torch.zeros(4))) == 0.0
    )


# --- the usage floor ----------------------------------------------------------------------------------------------------------
def r_glob_reference(u: torch.Tensor, slots: int, facts: int) -> torch.Tensor:
    """Independent differentiable R_glob(u) = max(0, ln M - H(u)) / ln N, 0 ln 0 = 0."""
    m = min(slots, 8 * facts) / 2
    safe = u.clamp_min(1e-30)
    h = -torch.where(u > 0, u * torch.log(safe), torch.zeros_like(u)).sum()
    return torch.clamp(math.log(m) - h, min=0.0) / math.log(slots)


def test_gradient_weights_equal_autograd_of_r_glob() -> None:
    slots, facts = 4096, 2048
    scores, ids = candidates(8, slots, 5, torch.float64)
    u = (
        objective.slot_usage(objective.soft_inclusion(scores), ids, slots)
        .detach()
        .requires_grad_(True)
    )
    (reference,) = torch.autograd.grad(r_glob_reference(u, slots, facts), u)
    g = objective.usage_floor_gradient_weights(u.detach(), slots, facts)
    assert g.dtype == torch.float32 and bool(torch.isfinite(g).all())
    seen = u.detach() > 0
    assert bool((reference[seen] != 0).all())  # the hinge is active in this case
    torch.testing.assert_close(g[seen].double(), reference[seen], rtol=1e-5, atol=1e-9)
    assert bool((g[~seen] == 0).all())  # 0 ln 0 = 0 slots carry no weight, nothing is infinite


@pytest.mark.parametrize("steps", [1, 2, 3])
def test_applied_usage_gradient_has_no_factor_b(steps: int) -> None:
    """The applied gradient lam * g_t * d u_bar / d theta equals the literal EMA derivative divided by b."""
    slots, facts = 4096, 2048
    b = core.usage_ema_rate(facts)
    assert b == pytest.approx(1 / 16)
    floor = objective.UsageFloor(slots, facts)
    lam = core.lambda_u(1.0, slots, facts)
    previous: torch.Tensor | None = None
    for step in range(steps):
        scores, ids = candidates(8, slots, 10 + step)
        scores.requires_grad_(True)
        u_bar = objective.slot_usage(objective.soft_inclusion(scores), ids, slots)
        before = None if floor.u is None else floor.u.clone()
        term, info = floor.penalty(u_bar, lam)
        assert info["hinge_active"] is True
        (applied,) = torch.autograd.grad(term, scores, retain_graph=True)
        # literal derivative of lam * R_glob(u_t) with u_t = (1-b) u_{t-1}.detach() + b u_bar_t
        prev = u_bar.detach() if before is None else before
        u_t = (1 - b) * prev + b * u_bar
        (literal,) = torch.autograd.grad(lam * r_glob_reference(u_t, slots, facts), scores)
        mask = literal.abs() > 1e-9
        assert bool(mask.any())
        torch.testing.assert_close(applied[mask], literal[mask] / b, rtol=2e-4, atol=1e-8)
        ratio = literal[mask] / applied[mask]
        torch.testing.assert_close(ratio, torch.full_like(ratio, b), rtol=2e-4, atol=0)
        previous = floor.u
    assert previous is not None and floor.updates == steps


def test_usage_ema_starts_at_the_first_batch_and_follows_the_formula() -> None:
    slots, facts = 4096, 2048
    b = core.usage_ema_rate(facts)
    floor = objective.UsageFloor(slots, facts)
    batches = []
    for step in range(3):
        scores, ids = candidates(8, slots, 20 + step)
        batches.append(objective.slot_usage(objective.soft_inclusion(scores), ids, slots))
    floor.penalty(batches[0], 1.0)
    assert floor.u is not None
    torch.testing.assert_close(
        floor.u, batches[0], rtol=1e-6, atol=1e-9
    )  # u_0 = first batch, so u_1 = u_bar_1
    floor.penalty(batches[1], 1.0)
    expected = (1 - b) * batches[0] + b * batches[1]
    torch.testing.assert_close(floor.u, expected, rtol=1e-5, atol=1e-9)
    floor.penalty(batches[2], 1.0)
    torch.testing.assert_close(floor.u, (1 - b) * expected + b * batches[2], rtol=1e-5, atol=1e-9)


def test_r_glob_is_zero_in_its_zero_region_and_bounded() -> None:
    slots, facts = 4096, 2048  # M = 2048
    floor = objective.UsageFloor(slots, facts)
    spread = torch.zeros(slots)
    spread[:3000] = 1 / 3000  # more than M = 2048 slots in use
    assert floor.r_glob(spread) == 0.0
    g = objective.usage_floor_gradient_weights(spread, slots, facts)
    assert bool((g == 0).all())
    term, info = objective.UsageFloor(slots, facts).penalty(spread.clone(), 1.7)
    assert info["hinge_active"] is False and float(term) == 0.0 and info["r_glob"] == 0.0
    grad_check = spread.clone().requires_grad_(True)
    term2, _ = objective.UsageFloor(slots, facts).penalty(grad_check, 1.7)
    (grad,) = torch.autograd.grad(term2, grad_check)
    assert bool((grad == 0).all())
    # bounded: R_glob lies in [0, ln M / ln N] <= 1, the maximum at a fully collapsed memory
    onehot = torch.zeros(slots)
    onehot[17] = 1.0
    top = math.log(core.usage_floor_support(slots, facts)) / math.log(slots)
    assert floor.r_glob(onehot) == pytest.approx(top, rel=1e-6) and 0 < top <= 1
    for k in (1, 2, 64, 500, 1500, 2047):
        u = torch.zeros(slots)
        u[:k] = 1 / k
        assert 0.0 <= floor.r_glob(u) <= top + 1e-9
    # a fully collapsed memory costs alpha_u times the chance-level answer loss
    for alpha in core.ALPHA_U_DOSES:
        assert core.lambda_u(alpha, slots, facts) * top == pytest.approx(
            alpha * math.log(32), rel=1e-9
        )


def test_floor_state_roundtrip_continues_identically() -> None:
    slots, facts = 4096, 2048
    a, b_ = objective.UsageFloor(slots, facts), objective.UsageFloor(slots, facts)
    scores = [candidates(8, slots, 30 + i) for i in range(4)]
    usage = [objective.slot_usage(objective.soft_inclusion(s), i, slots) for s, i in scores]
    for u in usage[:2]:
        a.penalty(u, 1.0)
    b_.load_state_dict(a.state_dict())
    for u in usage[2:]:
        ta, _ = a.penalty(u, 1.0)
        tb, _ = b_.penalty(u, 1.0)
        assert torch.equal(ta, tb)
    assert (
        a.u is not None
        and b_.u is not None
        and torch.equal(a.u, b_.u)
        and a.updates == b_.updates == 4
    )
    with pytest.raises(ValueError):
        a.load_state_dict({"u": None})


# --- answer sites -------------------------------------------------------------------------------------------------------------
def test_answer_site_rows_pick_the_sites_in_context_record_order() -> None:
    b = 3
    scores, ids = candidates(b * 63, 4096, 6)
    sel63 = selection_of(scores, ids, tuple(range(63)))
    s_rows, i_rows = objective.answer_site_rows(sel63)
    assert s_rows.shape == (b * 8, 64) and i_rows.shape == (b * 8, 64)
    c3 = scores.reshape(b, 63, 64)
    assert torch.equal(s_rows, c3[:, list(core.ANSWER_SITE_POSITIONS)].reshape(-1, 64))
    assert torch.equal(i_rows[8], ids.reshape(b, 63, 64)[1, 6])  # context 1, record 0 -> position 6
    # an answer-site-only selection (R0a/R1) gives the same rows for the same candidates
    only = selection_of(
        c3[:, list(core.ANSWER_SITE_POSITIONS)].reshape(-1, 64),
        ids.reshape(b, 63, 64)[:, list(core.ANSWER_SITE_POSITIONS)].reshape(-1, 64),
        core.ANSWER_SITE_POSITIONS,
    )
    s2, i2 = objective.answer_site_rows(only)
    assert torch.equal(s2, s_rows) and torch.equal(i2, i_rows)
    assert torch.equal(objective.answer_site_selected(sel63)[8], ids.reshape(b, 63, 64)[1, 6, :8])
    no_cands = Selection(
        torch.tensor(core.ANSWER_SITE_POSITIONS),
        torch.zeros(1, 8, 1, dtype=torch.int64),
        torch.zeros(1, 8, 1),
        None,
        None,
        None,
        None,
        63,
    )
    with pytest.raises(ValueError):
        objective.answer_site_rows(no_cands)
    with pytest.raises(ValueError):
        objective.answer_site_rows(
            selection_of(scores[:51], ids[:51], tuple(range(51)))
        )  # does not cover every site


def test_usage_term_ignores_non_answer_positions() -> None:
    cell = variant(base_cell(), alpha_u=1.0)
    scores, ids = candidates(2 * 63, 4096, 7)
    base = selection_of(scores, ids, tuple(range(63)))
    task = torch.tensor(1.0)
    r1 = objective.Objective(cell)(task, base)
    changed_scores = scores.clone().reshape(2, 63, 64)
    changed_scores[:, [0, 1, 2, 3, 4, 5]] += 3.0  # non-answer positions
    base2 = selection_of(changed_scores.reshape(-1, 64), ids, tuple(range(63)))
    r2 = objective.Objective(cell)(task, base2)
    assert float(r1.total) == float(r2.total) and r1.diagnostics == r2.diagnostics


# --- Objective -----------------------------------------------------------------------------------------------------------------
def test_objective_adds_nothing_without_a_dose() -> None:
    cell = base_cell()
    obj = objective.Objective(cell)
    scores, ids = candidates(2 * 63, 4096, 8)
    task = torch.tensor(2.5, requires_grad=True)
    result = obj(task, selection_of(scores, ids, tuple(range(63))))
    assert result.total is task and obj.last_terms == {} and not obj.active
    assert result.usage_penalty == 0.0 and result.coaccess_penalty == 0.0
    assert result.diagnostics["hinge_usage_active"] is False
    assert (
        result.diagnostics["usage_entropy_soft"] is not None
    )  # diagnostics still tracked for memory cells
    assert obj.regularizer_losses(selection_of(scores, ids, tuple(range(63)))) == {}


def test_objective_total_terms_and_coefficients() -> None:
    cell = variant(base_cell(), alpha_u=0.25, alpha_c=0.25)
    obj = objective.Objective(cell)
    assert obj.lambda_u == core.lambda_u_for(cell) and obj.lambda_c == core.lambda_c_for(cell)
    scores, ids = candidates(4 * 63, 4096, 9)
    scores.requires_grad_(True)
    sel = selection_of(scores, ids, tuple(range(63)))
    task = torch.tensor(1.25)
    result = obj(task, sel)
    assert set(obj.last_terms) == {"usage", "coaccess"}
    manual = task + obj.last_terms["usage"] + obj.last_terms["coaccess"]
    assert float(result.total) == pytest.approx(float(manual), rel=1e-6)
    rows, row_ids = objective.answer_site_rows(sel)
    soft = objective.soft_inclusion_full(rows)
    r_co = float(objective.coaccess_term(soft.pi, row_ids, 4096, soft.log_miss))
    assert result.coaccess_penalty == pytest.approx(obj.lambda_c * (r_co - 1 / 8), rel=1e-6)
    assert result.diagnostics["r_co"] == pytest.approx(r_co, rel=1e-6)
    assert (
        result.diagnostics["hinge_coaccess_active"] is True
        and result.diagnostics["hinge_usage_active"] is True
    )
    assert result.usage_penalty == pytest.approx(
        obj.lambda_u * float(result.diagnostics["r_glob"] or 0.0), rel=1e-9
    )
    # regularizer_losses returns the very tensors of the call (no second advance of the average)
    floor = obj.floor
    assert floor is not None
    updates = floor.updates
    terms = obj.regularizer_losses(sel)
    assert terms["usage"] is obj.last_terms["usage"] and floor.updates == updates
    (g_usage,) = torch.autograd.grad(terms["usage"], scores, retain_graph=True)
    assert bool((g_usage != 0).any())
    # a fresh objective rebuilt from the selection, without a preceding call, does not advance either
    obj2 = objective.Objective(cell)
    rebuilt = obj2.regularizer_losses(sel)
    assert (
        obj2.floor is not None and obj2.floor.updates == 0 and set(rebuilt) == {"usage", "coaccess"}
    )


def test_objective_gradient_is_task_plus_each_term() -> None:
    cell = variant(base_cell(), alpha_u=1.0, alpha_c=0.05)
    obj = objective.Objective(cell)
    scores, ids = candidates(4 * 63, 4096, 12)
    scores.requires_grad_(True)
    result = obj(torch.tensor(0.0), selection_of(scores, ids, tuple(range(63))))
    (total,) = torch.autograd.grad(result.total, scores, retain_graph=True)
    parts = [torch.autograd.grad(t, scores, retain_graph=True)[0] for t in obj.last_terms.values()]
    torch.testing.assert_close(total, sum(parts), rtol=1e-6, atol=1e-9)


def test_objective_state_roundtrip_and_errors() -> None:
    cell = variant(base_cell(), alpha_u=0.25)
    a, b = objective.Objective(cell), objective.Objective(cell)
    scores, ids = candidates(2 * 63, 4096, 13)
    sel = selection_of(scores, ids, tuple(range(63)))
    for _ in range(3):
        a(torch.tensor(1.0), sel)
    b.load_state_dict(a.state_dict())
    ra, rb = a(torch.tensor(1.0), sel), b(torch.tensor(1.0), sel)
    assert float(ra.total) == float(rb.total) and ra.diagnostics == rb.diagnostics
    with pytest.raises(ValueError):
        objective.Objective(base_cell()).load_state_dict(a.state_dict())
    with pytest.raises(ValueError):
        a(torch.tensor(1.0), None)  # a regularized cell needs a memory selection with candidates


def test_coefficients_match_the_adr_formulas() -> None:
    ln32 = math.log(32)
    for cell in core.cells_of_block("B1") + core.cells_of_block("C1"):
        obj = objective.Objective(cell)
        support = min(cell.slots, 8 * cell.facts) / 2
        assert support == core.usage_floor_support(cell.slots, cell.facts)
        expected_u = cell.alpha_u * ln32 / (math.log(support) / math.log(cell.slots))
        assert obj.lambda_u == pytest.approx(expected_u, rel=1e-12)
        assert obj.lambda_c == pytest.approx(cell.alpha_c * ln32 / (1 - 1 / 8), rel=1e-12)
        assert obj.lambda_u == objective.lambda_u(cell.alpha_u, cell.slots, cell.facts)
        assert objective.lambda_c(cell.alpha_c) == obj.lambda_c
    flat_b1 = [c for c in core.cells_of_block("B1") if c.arch == "flat" and c.seed == 1701]
    assert [round(objective.Objective(c).lambda_u, 4) for c in flat_b1] == [
        0.9331,
        3.7323,
    ]  # alpha_u = 0.25 and 1
    assert (
        round(objective.lambda_c(0.05), 5) == 0.19804
        and round(objective.lambda_c(0.25), 5) == 0.99021
    )
    assert objective.lambda_u(0.0, 16384, 8192) == 0.0 and objective.lambda_c(0.0) == 0.0
    # the fixed track at 65,536 slots: M = min(N, 8F) / 2 = 8,192
    assert core.usage_floor_support(65536, 2048) == 8192
    # the worst co-access value costs alpha_c times the chance-level answer loss
    assert objective.lambda_c(0.25) * (1 - 1 / 8) == pytest.approx(0.25 * ln32)


def test_usage_stats_entropies_and_state() -> None:
    stats = objective.UsageStats(4096, 2048)
    scores, ids = candidates(8, 4096, 14)
    pi = objective.soft_inclusion(scores)
    selected = ids[:, :8]
    soft_h, hard_h = stats.update(pi, ids, selected)
    assert 0 < hard_h <= math.log(64) + 1e-6 and soft_h >= hard_h
    other = objective.UsageStats(4096, 2048)
    other.load_state_dict(stats.state_dict())
    scores2, ids2 = candidates(8, 4096, 15)
    pi2 = objective.soft_inclusion(scores2)
    assert stats.update(pi2, ids2, ids2[:, :8]) == other.update(pi2, ids2, ids2[:, :8])
    with pytest.raises(ValueError):
        other.load_state_dict({"soft": None})


def test_margin_and_soft_mass_diagnostics() -> None:
    tight = torch.linspace(1.0, 0.0, 64).expand(16, -1).clone()  # tiny 8th-9th margin
    wide = torch.cat(
        [torch.full((16, 8), 5.0), torch.zeros(16, 56)], dim=1
    )  # margin 5.0: saturated
    ids = torch.arange(64).expand(16, -1)
    for scores, margin_expected, mass_small in ((tight, 1 / 63, False), (wide, 5.0, True)):
        sel = selection_of(scores, ids, core.ANSWER_SITE_POSITIONS)
        margins = objective.answer_site_margins(sel)
        assert margins.shape == (16,)
        assert float(margins.mean()) == pytest.approx(margin_expected, rel=1e-5)
        mass = objective.soft_mass_outside_top8(sel)
        assert (mass < 0.01) == mass_small
    assert objective.soft_mass_outside_top8(
        selection_of(wide, ids, core.ANSWER_SITE_POSITIONS)
    ) == pytest.approx(56 * 4.5e-5, rel=0.05)
