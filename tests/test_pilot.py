"""Correctness fixtures only; no training or evaluation on the registered corpus."""

import hashlib
import math
import random
from pathlib import Path

import pytest
import torch
from torch.nn import functional as F

from arborlm.engine import optimizer_for
from arborlm.pilot_checkpoint import restore, save
from arborlm.pilot_config import load_pilot_config, validate_pilot_config
from arborlm.pilot_data import _rows, select
from arborlm.pilot_metrics import evaluate, loss_for
from arborlm.pilot_model import (
    COUNTS,
    EPS,
    TEMP,
    VARIANTS,
    Memory,
    PilotModel,
    product_candidates,
    stable_top,
    tree_candidates,
)

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "p1_ram_screen.toml"


def test_strict_pilot_configuration() -> None:
    config = load_pilot_config(CONFIG)
    config["model"]["visited_branches"] = 3
    with pytest.raises(ValueError, match="visited_branches"):
        validate_pilot_config(config)
    config = load_pilot_config(CONFIG)
    config["extra"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        validate_pilot_config(config)


def test_utf8_row_boundaries_and_dedup_against_entire_train() -> None:
    chunk_a = "a" * 63 + "é"
    chunk_b = "b" * 65
    chunk_c = "c" * 65
    train, hashes, counts = select([chunk_a + chunk_b, chunk_b, "x", "y" * 64], "train", 1)
    assert counts["full_chunks"] == 3
    assert counts["eligible_unique_chunks"] == 2
    assert counts["remainder_bytes"] == 65
    assert counts["duplicates_after_cross_split"] == 1
    validation, _, counts = select(
        [chunk_a, chunk_b, chunk_c * 2], "validation", 1, excluded=hashes
    )
    assert len(hashes) == 2 and len(train) == 1
    assert counts["excluded_cross_split"] == 2
    assert counts["duplicates_after_cross_split"] == 1
    assert validation[0].payload == chunk_c.encode()
    ranked, _, _ = select([chunk_a + chunk_b, chunk_b], "train", 2)
    assert {c.payload for c in ranked} == {chunk_a.encode(), chunk_b.encode()}
    first = next(c for c in ranked if c.payload == chunk_b.encode())
    expected = min(
        (hashlib.sha256(f"arborlm-pilot-v1:train:{row}:{offset}".encode()).hexdigest(), row, offset)
        for row, offset in [(0, 65), (1, 0)]
    )
    assert (first.rank, first.row, first.offset) == expected


def test_local_parquet_reader_preserves_text_exactly(tmp_path: Path) -> None:
    import pyarrow
    from pyarrow import parquet

    texts = [" A\u0301 ", "", "\né", "text " * 15]
    fixture = tmp_path / "synthetic.parquet"
    parquet.write_table(pyarrow.table({"text": texts}), fixture)
    assert list(_rows(fixture)) == texts


def test_top_breaks_inside_and_boundary_ties_by_id() -> None:
    scores = torch.tensor([[3.0, 3.0, 2.0, 2.0, 2.0, 1.0]])
    ids = torch.tensor([[20, 2, 40, 8, 10, 1]])
    vals, selected = stable_top(scores, 3, ids)
    assert selected.tolist() == [[2, 20, 8]]
    assert vals.tolist() == [[3.0, 3.0, 2.0]]


@pytest.mark.parametrize("kind", ["normal", "ties", "near_boundary", "mixed"])
def test_product_exact_float32_reference(kind: str) -> None:
    generator = torch.Generator().manual_seed(105)
    left = torch.rand((4, 64), generator=generator) * 2 - 1
    right = torch.rand((4, 64), generator=generator) * 2 - 1
    if kind == "ties":
        left.zero_()
        right.zero_()
    elif kind in ("near_boundary", "mixed"):
        affected = slice(0, 4 if kind == "near_boundary" else 1)
        left[affected] = -0.1
        left[affected, :9] = 0.1
        left[affected, :8] += 5e-7
        right[affected] = -0.2
        right[affected, 0] = 1.0
    left.requires_grad_()
    right.requires_grad_()
    scores, indices, _, fallback = product_candidates(left, right)
    all_scores = (left[:, :, None] + right[:, None, :]).flatten(1) / (math.sqrt(2) * TEMP)
    expected = all_scores.argsort(dim=-1, descending=True, stable=True)[:, :8]
    assert torch.equal(indices, expected)
    assert torch.equal(scores, all_scores.gather(-1, expected))
    if kind == "normal":
        assert not fallback.any()
    if kind in ("ties", "near_boundary"):
        assert fallback.all()
    if kind == "mixed":
        assert fallback.tolist() == [True, False, False, False]
    scores.sum().backward()
    assert left.grad is not None and right.grad is not None
    assert torch.isfinite(left.grad).all() and torch.isfinite(right.grad).all()


def test_tree_all_branches_zero_prior_matches_flat() -> None:
    generator = torch.Generator().manual_seed(214)
    q = F.normalize(torch.randn((3, 16), generator=generator), dim=-1, eps=EPS)
    keys = torch.randn((64, 16), generator=generator)
    routes = torch.randn((3, 4), generator=generator)
    scores, ids, _, branches = tree_candidates(
        q,
        keys,
        routes,
        visit=4,
        keys_per_branch=16,
        use_prior=False,
    )
    expected = (q @ F.normalize(keys, dim=-1, eps=EPS).T) / TEMP
    reference, reference_ids = stable_top(expected, 8)
    assert torch.equal(ids, reference_ids)
    torch.testing.assert_close(scores, reference, rtol=1e-6, atol=1e-6)
    assert branches.shape == (3, 4)


def test_tree_conditional_router_gradient_uses_selected_branch_scores() -> None:
    keys = torch.zeros((16, 16))
    q = torch.zeros((1, 16))
    routes = torch.tensor([[1.0, 0.9, -5.0, -5.0]], requires_grad=True)
    scores, ids, _, branches = tree_candidates(q, keys, routes, keys_per_branch=4)
    assert branches.tolist() == [[0, 1]] and ids.tolist() == [list(range(8))]
    weight_branch0 = scores.softmax(-1)[0, :4].sum()
    grad = torch.autograd.grad(weight_branch0, routes)[0]
    assert grad[0, 0] > 0 and grad[0, 1] < 0
    torch.testing.assert_close(grad[0, 2:], torch.zeros(2), rtol=0, atol=1e-7)
    scores, _, _, _ = tree_candidates(q, torch.zeros((32, 16)), routes, keys_per_branch=8)
    single_branch_grad = torch.autograd.grad(scores.softmax(-1)[0, 0], routes)[0]
    torch.testing.assert_close(single_branch_grad, torch.zeros_like(routes), rtol=0, atol=1e-7)


@pytest.mark.parametrize("variant", VARIANTS[2:])
def test_memory_values_receive_only_selected_gradients(variant: str) -> None:
    memory = Memory(variant, 42)
    h = torch.randn((1, 4, 32))
    output, lookup = memory(h)
    output.square().mean().backward()
    assert memory.values.grad is not None
    visited = lookup.selected.unique()
    nonzero = (memory.values.grad.abs().sum(-1) > 0).nonzero().flatten()
    assert torch.equal(visited, nonzero)


def test_counts_and_common_initialization() -> None:
    states = {variant: PilotModel(variant, 42) for variant in VARIANTS}
    for variant, model in states.items():
        assert sum(p.numel() for p in model.parameters()) == COUNTS[variant]
    for name, param in states["dense_small"].named_parameters():
        for variant in VARIANTS[2:]:
            assert torch.equal(param, dict(states[variant].named_parameters())[name])
    for name in ("values", "wq", "wo", "gate"):
        expected = states["flat"].state_dict()[f"memory.{name}"]
        for variant in VARIANTS[3:]:
            assert torch.equal(expected, states[variant].state_dict()[f"memory.{name}"])
    assert torch.equal(
        states["fixed_tree"].state_dict()["memory.router"],
        states["learned_tree"].state_dict()["memory.router"],
    )


@pytest.mark.parametrize("variant", VARIANTS[2:])
def test_checkpoint_restores_optimizer_rng_cursor_and_validation(
    tmp_path: Path, variant: str
) -> None:
    model = PilotModel(variant, 43)
    opt = optimizer_for(model)
    assert model.memory is not None
    initial_router = model.memory.router.detach().clone() if variant.endswith("_tree") else None
    # Tiny fixture: 128 updates on just one two-byte target, not a pilot run.
    batch = torch.tensor([[8, 9, 8]], dtype=torch.int64)
    for _ in range(128):
        opt.zero_grad(set_to_none=True)
        logits, _ = model(batch[:, :-1])
        loss = loss_for(logits, batch[:, 1:], "mean")
        assert torch.isfinite(loss)
        loss.backward()
        assert torch.isfinite(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0))
        opt.step()
    if variant == "fixed_tree":
        assert not model.memory.router.requires_grad
        assert torch.equal(initial_router, model.memory.router)
    identity = {"variant": variant, "fixture": "synthetic", "seed": 43}
    destination = tmp_path / "checkpoint-128"
    save(destination, model, opt, 128, identity)
    old_eval = evaluate(model, batch)
    py_rng, torch_rng = random.getstate(), torch.get_rng_state()
    random.random()
    torch.rand(1)
    new_model = PilotModel(variant, 43)
    new_opt = optimizer_for(new_model)
    with pytest.raises(ValueError, match="variant/config/data/spec"):
        restore(destination, new_model, new_opt, {**identity, "fixture": "different"})
    assert restore(destination, new_model, new_opt, identity) == (128, 1024, 65536)
    assert py_rng == random.getstate() and torch.equal(torch_rng, torch.get_rng_state())
    assert all(
        torch.equal(tensor, new_model.state_dict()[key])
        for key, tensor in model.state_dict().items()
    )
    assert old_eval == evaluate(new_model, batch)
    for index, state in opt.state_dict()["state"].items():
        for key, value in state.items():
            assert torch.equal(value, new_opt.state_dict()["state"][index][key])
