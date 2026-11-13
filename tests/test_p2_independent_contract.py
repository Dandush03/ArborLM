"""Independent synthetic contract checks for the registered P2 follow-up."""

import copy
from pathlib import Path

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from arborlm.engine import optimizer_for
from arborlm.io import sha256
from arborlm.optimization_followup import _optimizer
from arborlm.p2_analysis import describe
from arborlm.p2_checkpoint import restore, save
from arborlm.p2_config import CONTROL, LEARNED, Cell
from arborlm.p2_data import Candidate, order_ids, panel
from arborlm.p2_model import FollowupModel
from arborlm.pilot_model import PilotModel


def _backbone_state(model: nn.Module) -> dict[str, torch.Tensor]:
    return {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if not name.startswith("memory_state.")
    }


def _step(model: nn.Module, optimizer: torch.optim.Optimizer, batch: torch.Tensor) -> None:
    optimizer.zero_grad(set_to_none=True)
    logits, _ = model(batch[:, :-1])
    loss = F.cross_entropy(logits.reshape(-1, 256), batch[:, 1:].reshape(-1))
    loss.backward()  # type: ignore[no-untyped-call]  # PyTorch stub
    nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()


def test_factor_initialization_and_order_have_isolated_rngs() -> None:
    torch.manual_seed(9001)
    before = torch.get_rng_state().clone()
    first = FollowupModel(Cell(101, 201, 301, LEARNED))
    assert torch.equal(torch.get_rng_state(), before)
    second = FollowupModel(Cell(101, 203, 303, LEARNED))
    assert torch.equal(torch.get_rng_state(), before)
    assert all(
        torch.equal(value, _backbone_state(second)[name])
        for name, value in _backbone_state(first).items()
    )
    assert not torch.equal(first.memory_state.values, second.memory_state.values)

    expected = torch.randperm(2048, generator=torch.Generator(device="cpu").manual_seed(301))
    before_order = torch.get_rng_state().clone()
    order = order_ids(301)
    assert torch.equal(order, expected)
    assert torch.equal(torch.sort(order).values, torch.arange(2048))
    assert torch.equal(order.reshape(256, 8), expected.reshape(256, 8))
    assert torch.equal(order_ids(301), order)
    assert torch.equal(torch.get_rng_state(), before_order)
    other_order = order_ids(302)
    assert not torch.equal(order, other_order)
    assert torch.equal(torch.sort(other_order).values, torch.arange(2048))
    row_ids = torch.arange(2048)
    assert torch.equal(torch.sort(row_ids[order]).values, torch.sort(row_ids[other_order]).values)


def test_control_is_dense_equivalent_and_memory_is_frozen_and_excluded() -> None:
    control = FollowupModel(Cell(101, 201, 301, CONTROL))
    reference = PilotModel("dense_small", 42)
    reference.load_state_dict(
        {
            name: value
            for name, value in control.state_dict().items()
            if not name.startswith("memory_state.")
        },
        strict=False,
    )
    assert control.memory is None and control.bypass
    assert all(not parameter.requires_grad for parameter in control.memory_state.parameters())
    optimizer = _optimizer(control)
    optimized_ids = {
        id(parameter) for group in optimizer.param_groups for parameter in group["params"]
    }
    assert optimized_ids == {
        id(parameter) for parameter in control.parameters() if parameter.requires_grad
    }
    assert not optimized_ids & {id(parameter) for parameter in control.memory_state.parameters()}

    memory_before = {
        name: value.clone() for name, value in control.memory_state.state_dict().items()
    }
    generator = torch.Generator(device="cpu").manual_seed(44)
    batch = torch.randint(0, 256, (8, 65), generator=generator)
    reference_optimizer = optimizer_for(reference)
    torch.testing.assert_close(
        control(batch[:, :-1])[0], reference(batch[:, :-1])[0], rtol=0, atol=0
    )
    for _ in range(2):
        _step(control, optimizer, batch)
        _step(reference, reference_optimizer, batch)
    assert all(
        torch.equal(value, reference.state_dict()[name])
        for name, value in control.state_dict().items()
        if not name.startswith("memory_state.")
    )
    assert all(
        torch.equal(value, control.memory_state.state_dict()[name])
        for name, value in memory_before.items()
    )
    logits_control, lookup_control = control(batch[:, :-1])
    logits_dense, _ = reference(batch[:, :-1])
    assert lookup_control is None
    torch.testing.assert_close(logits_control, logits_dense, rtol=0, atol=0)


def test_checkpoint_resume_restores_optimizer_model_and_rng(tmp_path: Path) -> None:
    cell = Cell(102, 202, 302, LEARNED)
    identity = {"cell": cell.fields(), "source": "synthetic-fixture"}
    first = FollowupModel(cell)
    optimizer_first = _optimizer(first)
    batch = torch.randint(0, 256, (8, 65), generator=torch.Generator().manual_seed(91))
    for _ in range(128):
        _step(first, optimizer_first, batch)
    path = tmp_path / "checkpoint"
    save(path, first, optimizer_first, 128, identity)

    # Continue once from the saved state and record its complete trainable result.
    random_draw = torch.rand(4)
    _step(first, optimizer_first, batch)
    expected_model = copy.deepcopy(first.state_dict())
    expected_optimizer = copy.deepcopy(optimizer_first.state_dict())

    resumed = FollowupModel(cell)
    optimizer_resumed = _optimizer(resumed)
    assert restore(path, resumed, optimizer_resumed, identity) == (128, 1024, 65536)
    torch.testing.assert_close(torch.rand(4), random_draw, rtol=0, atol=0)
    _step(resumed, optimizer_resumed, batch)
    assert all(
        torch.equal(value, resumed.state_dict()[name]) for name, value in expected_model.items()
    )
    actual_optimizer = optimizer_resumed.state_dict()
    assert actual_optimizer["param_groups"] == expected_optimizer["param_groups"]
    for parameter_id, expected_state in expected_optimizer["state"].items():
        for name, value in expected_state.items():
            actual = actual_optimizer["state"][parameter_id][name]
            if isinstance(value, torch.Tensor):
                assert torch.equal(actual, value)
            else:
                assert actual == value


def test_p2_validation_panel_is_exact_and_disjoint() -> None:
    validation = [
        Candidate(f"rank-{index:04}", index, 0, f"chunk-{index:04}".encode().ljust(65, b"!"))
        for index in range(1024)
    ]
    train_candidate = b"training candidate".ljust(65, b"!")
    prior, measured = panel(validation, {sha256(train_candidate)})
    assert len(prior) == len(measured) == 512
    assert prior == validation[:512]
    assert measured == validation[512:]
    assert not {row.payload for row in prior} & {row.payload for row in measured}
    with pytest.raises(ValueError, match="overlaps"):
        duplicated = validation.copy()
        duplicated[700] = validation[12]
        panel(duplicated, set())
    with pytest.raises(ValueError, match="overlaps"):
        panel(validation, {sha256(validation[700].payload)})


def test_balanced_grid_decomposition_matches_hand_computed_interaction() -> None:
    rows = []
    centered = {101: -1, 102: 0, 103: 1}
    centered_memory = {201: -1, 202: 0, 203: 1}
    for backbone in (101, 102, 103):
        for memory in (201, 202, 203):
            for order in (301, 302, 303):
                b = centered[backbone]
                m = centered_memory[memory]
                delta = 0.001 * m + 0.009 * b * m
                enabled = 1.0
                disabled = enabled + delta
                control = enabled + 0.04 + 0.003 * b
                rows.append(
                    {
                        "backbone": backbone,
                        "memory": memory,
                        "order": order,
                        "enabled": enabled,
                        "disabled": disabled,
                        "values_permuted": enabled + 0.01,
                        "joint_within_branch": enabled,
                        "control": control,
                    }
                )
    result = describe(rows)
    decomposition = result["factor_decomposition"]["D"]
    assert decomposition["marginal_ranges"]["memory"] == pytest.approx(0.002)
    assert decomposition["interaction_rms"] == pytest.approx(0.006)
    assert result["flags"]["measured_factor_sensitivity"]
    assert all(abs(row["G"] - row["D"] - row["S"]) <= 1e-12 for row in result["learned_cells"])
