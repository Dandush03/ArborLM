"""ADR-0015 section 10 items 1, 2, 3 (lambda = 0), 9: the P8 proxy, its gradients and the step.

Synthetic only: float64 score tensors and a random full-dimension parent; no local data."""

import math

import pytest
import torch
from torch import Tensor

from arborlm import p8_core as core
from arborlm import p8_objective as obj
from arborlm.p5_model import Model, optimizer_for, state_digest
from arborlm.p5_model import train_step as p5_train_step
from arborlm.pilot_model import Memory, stable_top

S = 128  # slots in the small instances (group 8 -> 16 groups); soft top is 64 of them


def random_scores(queries: int, count: int, seed: int, scale: float = 0.5) -> Tensor:
    generator = torch.Generator().manual_seed(seed)
    return torch.randn(queries, count, generator=generator, dtype=torch.float64) * scale


def hand_soft(ids: list[list[int]], p: float) -> obj.Soft:
    """Constructed inclusions: ``p`` on the listed slots, zero on filler candidates (up to 64)."""
    rows = len(ids)
    pad = [[i for i in range(S) if i not in chosen][: 64 - len(chosen)] for chosen in ids]
    full = torch.tensor([chosen + extra for chosen, extra in zip(ids, pad, strict=True)])
    pi = torch.zeros(rows, 64, dtype=torch.float64)
    pi[:, : len(ids[0])] = p
    return obj.Soft(pi, full, torch.log1p(-pi), torch.zeros(rows, dtype=torch.float64))


# --- item 1: gradcheck on small synthetic float64 instances ---------------------------------------
@pytest.mark.parametrize("name", ["conc", "co", "temp"])
@pytest.mark.parametrize("tree", [False, True])
def test_gradcheck_each_regularizer(name: str, tree: bool) -> None:
    queries, rows = 12, 2
    if tree:
        count = 96
        gen = torch.Generator().manual_seed(3)
        ids = torch.stack([torch.randperm(S, generator=gen)[:count] for _ in range(queries)])
    else:
        count = S
        ids = torch.arange(S).expand(queries, -1).contiguous()
    scores = random_scores(queries, count, seed=5 + tree).requires_grad_(True)

    def fn(s: Tensor) -> Tensor:
        soft = obj.soft_inclusion(s, ids)
        if name == "conc":
            return obj.r_conc(soft, S)
        if name == "co":
            return obj.r_co(soft, core.GROUP, S)
        return obj.r_temp(soft, rows, core.WINDOW, S)

    assert torch.autograd.gradcheck(fn, (scores,), eps=1e-6, atol=1e-6, rtol=1e-4)
    assert 0.0 <= float(fn(scores)) <= 1.0


def test_regularizers_are_in_unit_interval_full_size() -> None:
    scores = random_scores(64, 4096, seed=9, scale=1.0).float()
    ids = torch.arange(4096).expand(64, -1)
    soft = obj.soft_inclusion(scores, ids)
    for value in obj.regularizer_values(soft, rows=4).values():
        assert 0.0 <= float(value) <= 1.0


# --- item 2: proxy properties ---------------------------------------------------------------------
def test_exactly_eight_above_half_random_untied() -> None:
    for seed, scale in ((1, 0.1), (2, 1.0), (3, 50.0)):
        scores = random_scores(50, 4096, seed=seed, scale=scale)
        ids = torch.arange(4096).expand(50, -1)
        soft = obj.soft_inclusion(scores, ids)
        assert soft.pi.shape == (50, 64)
        assert bool(((soft.pi > 0.5).sum(-1) == 8).all())
        hard = scores.topk(8, dim=-1).indices
        assert torch.equal(soft.ids[:, :8], hard)


def test_tied_eighth_and_ninth_give_seven_and_two_halves() -> None:
    scores = random_scores(20, 4096, seed=4)
    top = scores.topk(9, dim=-1).values
    for q in range(20):  # make the 9th score exactly equal to the 8th
        scores[q][scores[q] == top[q, 8]] = top[q, 7]
    soft = obj.soft_inclusion(scores, torch.arange(4096).expand(20, -1))
    assert bool(((soft.pi > 0.5).sum(-1) == 7).all())
    assert bool(((soft.pi == 0.5).sum(-1) == 2).all())


def test_inclusion_is_zero_outside_the_top_64() -> None:
    scores = random_scores(10, 4096, seed=6, scale=0.3)
    ids = torch.arange(4096).expand(10, -1)
    soft = obj.soft_inclusion(scores, ids)
    dense = obj.to_slots(soft.pi, soft.ids, 4096)
    assert bool(((dense > 0).sum(-1) == 64).all())
    kept = scores.topk(64, dim=-1).indices
    outside = torch.ones_like(dense, dtype=torch.bool).scatter(1, kept, False)
    assert bool((dense[outside] == 0).all())
    assert bool((soft.log_miss <= 0).all()) and bool(torch.isfinite(soft.log_miss).all())
    assert torch.allclose(soft.log_miss, torch.log1p(-soft.pi), atol=1e-12)  # = -softplus(z)


@pytest.mark.parametrize("p", [0.51, 0.9, 0.999])
def test_r_co_closed_form_one_group(p: float) -> None:
    soft = hand_soft([list(range(8 * g, 8 * g + 8)) for g in (0, 5, 9, 12)], p)
    closed = (1 - (1 - p) ** 8) / (8 * p)
    assert float(obj.r_co(soft, 8, S)) == pytest.approx(closed, rel=1e-9)


def test_r_co_near_one_for_eight_groups() -> None:
    soft = hand_soft([[8 * k + g for k in range(8)] for g in range(4)], 0.9)
    assert float(obj.r_co(soft, 8, S)) == pytest.approx(1.0, abs=1e-6)


def test_r_temp_extremes() -> None:
    length = 16
    p = 1 - 1e-6
    same = hand_soft([list(range(8))] * length, p)
    fresh = hand_soft([list(range(8 * (t % 14), 8 * (t % 14) + 8)) for t in range(length)], p)
    assert float(obj.r_temp(same, 1, 8, S)) < 1e-4
    assert float(obj.r_temp(fresh, 1, 8, S)) > 0.9999


def test_r_temp_window_is_eight_positions() -> None:
    length = 12
    p = 1 - 1e-6
    ids = [
        list(range(8)) if t in (0, 9) else [8 * (1 + t) % 128 + k for k in range(8)]
        for t in range(length)
    ]
    soft = hand_soft(ids, p)
    # position 9 sees slots 0..7 at lag 9: outside the window, so counted as new
    cube_new = obj.r_temp(soft, 1, 8, S)
    wide = obj.r_temp(soft, 1, 9, S)
    assert float(cube_new) > float(wide)


def test_r_conc_ordering_and_floor() -> None:
    queries = 32
    concentrated = hand_soft([list(range(8))] * queries, 0.9)
    uniform = hand_soft([[(8 * q + k) % S for k in range(8)] for q in range(queries)], 0.9)
    low = float(obj.r_conc(concentrated, 4096))
    assert low == pytest.approx(math.log(8) / math.log(4096), rel=1e-9)
    assert low == pytest.approx(0.25)
    assert low < float(obj.r_conc(uniform, 4096))


# --- the real model: candidate scores, selection equivalence, gradient locality -------------------
def make(case: str, seed: int = 601, parent: int = 101) -> Model:
    cell = core.Cell(parent, 300 + parent - 100, seed, case)
    return core.build_model(cell, core.synthetic_backbone(cell))


def batch_for(model: Model, rows: int = 4) -> Tensor:
    cell = model.cell
    assert isinstance(cell, core.Cell)
    train, order, _ = core.synthetic_training(cell)
    return core.ordered_rows(train, order)[:rows]


@pytest.mark.parametrize("case", ["C01", "C02", "C03"])
def test_candidate_scores_top8_equals_lookup_selected(case: str) -> None:
    model = make(case)
    batch = batch_for(model)
    with torch.no_grad():
        _, lookup = model(batch[:, :-1])
        scores, ids, soft = obj.proxy_inputs(model, batch[:, :-1])
    assert lookup is not None
    assert scores.shape[-1] == (4096 if case == "C01" else 512)
    assert torch.equal(stable_top(scores, 8, ids)[1], lookup.selected)
    assert bool(((soft.pi > 0.5).sum(-1) == 8).all())


@pytest.mark.parametrize("case", ["C04", "C07", "C10"])
def test_gradients_reach_routing_but_not_values_wo_gate(case: str) -> None:
    model = make(case)
    batch = batch_for(model)
    memory = model.addition
    assert isinstance(memory, Memory)
    scores, ids, soft = obj.proxy_inputs(model, batch[:, :-1])
    values = obj.regularizer_values(soft, batch.shape[0])
    named = {n: p for n, p in model.named_parameters() if p.requires_grad}
    assert all(n.startswith("addition.") for n in named)
    for name, value in values.items():
        grads = torch.autograd.grad(
            value, list(named.values()), retain_graph=True, allow_unused=True
        )
        by_name = dict(zip(named, grads, strict=True))
        for dead in ("addition.values", "addition.wo", "addition.gate"):
            grad = by_name[dead]
            assert grad is None or bool((grad == 0).all()), (name, dead)
        for live in ("addition.keys", "addition.wq"):
            assert by_name[live] is not None and float(by_name[live].abs().sum()) > 0, (name, live)
        if model.cell.variant == core.LEARNED:
            router = by_name["addition.router"]
            assert router is not None and float(router.abs().sum()) > 0, name


# --- item 3: the standard path is P5's step; lambda = 0 is the standard path ---------------------
STEPS = 4


def run_p8(model: Model, objective: tuple[str, ...], steps: int = STEPS, **kw: float) -> list[dict]:
    optimizer = optimizer_for(model)
    rows = batch_for(model, 8 * steps)
    return [
        obj.train_step_p8(model, optimizer, rows[8 * (i - 1) : 8 * i][:, :], i, objective, **kw)
        for i in range(1, steps + 1)
    ]


@pytest.mark.parametrize("case", ["C01", "C02", "C03"])
def test_standard_path_is_bit_identical_to_p5_train_step(case: str) -> None:
    a, b = make(case), make(case)
    assert state_digest(a) == state_digest(b)
    optimizer = optimizer_for(a)
    rows = batch_for(a, 8 * STEPS)
    losses = []
    for i in range(1, STEPS + 1):
        losses.append(p5_train_step(a, optimizer, rows[8 * (i - 1) : 8 * i], i)[0])
    records = run_p8(b, ())
    assert state_digest(a) == state_digest(b)
    assert [r["loss"] for r in records] == losses


@pytest.mark.parametrize("case", ["C06", "C07", "C10", "C04", "C09"])
def test_lambda_zero_equals_standard_path_bit_for_bit(case: str) -> None:
    regularized, standard = make(case), make(case)
    run_p8(standard, ())
    records = run_p8(regularized, regularized.cell.objective, alpha=0.0)  # type: ignore[attr-defined]
    assert state_digest(regularized) == state_digest(standard)
    assert all(v == 0.0 for r in records for v in r["lam"].values())


def test_lambda_floor_event_is_counted_and_equals_standard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(obj, "LAMBDA_FLOOR", 1e9)
    regularized, standard = make("C07"), make("C07")
    run_p8(standard, ())
    records = run_p8(regularized, ("co",))
    assert all(r["lambda_zero_event"]["co"] for r in records)
    assert state_digest(regularized) == state_digest(standard)


def test_matched_pressure_and_regularizer_changes_the_update() -> None:
    plain, regularized = make("C07"), make("C07")
    run_p8(plain, ())
    records = run_p8(regularized, ("co",))
    for r in records:
        assert r["lam"]["co"] * r["g_r_norm"]["co"] == pytest.approx(
            core.ALPHA * r["g_l_theta_norm"], rel=1e-5
        )
        assert r["selection_consistent"] is True
        assert math.isfinite(r["pre_clip_gradient_norm"])
    assert state_digest(regularized) != state_digest(plain)
    # the frozen parts of the model are untouched by the regularizer
    a, b = dict(plain.named_parameters()), dict(regularized.named_parameters())
    assert all(torch.equal(a[n], b[n]) for n in a if n.startswith("backbone."))


def test_reach_record_and_tracker() -> None:
    model = make("C07")
    optimizer = optimizer_for(model)
    tracker = obj.ReachTracker()
    rows = batch_for(model, 8)
    record = obj.train_step_p8(model, optimizer, rows, 1, ("co",), tracker=tracker, reach=True)
    assert record["cumulative_hard_selected_slots"] == int(tracker.seen.sum()) > 0
    assert record["reach_g_l_key_rows"] > 0
    assert record["reach_g_r_key_rows"]["co"] > 0
    assert 0 <= record["reach_g_r_not_hard_selected"]["co"] <= record["reach_g_r_key_rows"]["co"]


# --- item 9: determinism -----------------------------------------------------------------------
def test_repeated_run_gives_identical_digest() -> None:
    first, second = make("C10"), make("C10")
    run_p8(first, ("co", "temp"))
    run_p8(second, ("co", "temp"))
    assert state_digest(first) == state_digest(second)


@pytest.mark.parametrize("case", ["C01", "C03"])
def test_logging_on_keeps_standard_path_bit_identical_and_records_diagnostics(case: str) -> None:
    a, b = make(case), make(case)
    optimizer = optimizer_for(a)
    rows = batch_for(a, 8 * STEPS)
    for i in range(1, STEPS + 1):
        p5_train_step(a, optimizer, rows[8 * (i - 1) : 8 * i], i)
    records = run_p8(b, (), reach=True)
    assert state_digest(a) == state_digest(b)
    for r in records:
        diag = r["diagnostics"]
        assert set(diag["regularizer_all"]) == {"conc", "co", "temp"}
        assert diag["mean_gap_8_9"] > 0 and diag["mean_pi_mass_outside_top8"] >= 0
        moved = r["param_change_l2"]
        assert moved["theta_r"] > 0 and moved["other"] > 0
