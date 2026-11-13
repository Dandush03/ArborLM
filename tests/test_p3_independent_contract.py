"""Independent synthetic contract checks for the registered P3 continuation."""

import copy
import random
from pathlib import Path

import pytest
import torch

from arborlm.io import sha256
from arborlm.longer_training import _duration, _training_step
from arborlm.optimization_followup import _optimizer
from arborlm.p2_checkpoint import save as save_p2
from arborlm.p2_config import CONTROL, LEARNED, Cell, cells
from arborlm.p2_data import Candidate
from arborlm.p2_model import FollowupModel
from arborlm.p3_analysis import describe
from arborlm.p3_checkpoint import bitwise_equal, convert
from arborlm.p3_checkpoint import restore as restore_p3
from arborlm.p3_checkpoint import save as save_p3
from arborlm.p3_config import batch_offset, counters
from arborlm.p3_data import panel


def _state(model: FollowupModel) -> dict[str, torch.Tensor]:
    return {name: value.detach().clone() for name, value in model.state_dict().items()}


def _batch(rows: torch.Tensor, order: torch.Tensor, step: int) -> torch.Tensor:
    offset = batch_offset(step)
    return rows[order[offset : offset + 8]]


def test_global_step_cursors_roll_exactly_over_the_parent_order() -> None:
    expected = {
        256: (2048, 0, 131072, 0),
        512: (4096, 0, 262144, 131072),
        768: (6144, 0, 393216, 262144),
        1024: (8192, 0, 524288, 393216),
    }
    for step, values in expected.items():
        result = counters(step)
        assert (
            result["absolute_order_cursor"],
            result["next_cyclic_order_cursor"],
            result["cumulative_targets"],
            result["additional_targets"],
        ) == values

    assert {
        step: batch_offset(step) for step in (257, 511, 512, 513, 767, 768, 769, 1023, 1024)
    } == {
        257: 0,
        511: 2032,
        512: 2040,
        513: 0,
        767: 2032,
        768: 2040,
        769: 0,
        1023: 2032,
        1024: 2040,
    }
    with pytest.raises(ValueError, match="global step"):
        counters(255)
    with pytest.raises(ValueError, match="unregistered P3 update"):
        batch_offset(256)
    with pytest.raises(ValueError, match="unregistered P3 update"):
        batch_offset(1025)


def test_fresh_panel_is_ranks_1024_through_1535_and_disjoint() -> None:
    validation = [
        Candidate(
            f"rank-{index:04}",
            index,
            0,
            index.to_bytes(4, "big") + bytes([index % 251]) * 61,
        )
        for index in range(1536)
    ]
    first, second, third = panel(validation, set())
    assert len(first) == len(second) == len(third) == 512 * 65
    assert first == b"".join(row.payload for row in validation[:512])
    assert second == b"".join(row.payload for row in validation[512:1024])
    assert third == b"".join(row.payload for row in validation[1024:])
    assert len({row.payload for row in validation}) == 1536

    with pytest.raises(ValueError, match="1536"):
        panel(validation[:-1], set())
    duplicate = validation.copy()
    duplicate[1400] = validation[10]
    with pytest.raises(ValueError, match="overlap"):
        panel(duplicate, set())
    with pytest.raises(ValueError, match="overlap"):
        panel(validation, {sha256(validation[1200].payload)})


def test_parent_cell_mapping_requires_complete_unique_registered_grid() -> None:
    from arborlm.optimization_followup import _label
    from arborlm.p3_parent import map_cells

    records = [
        {
            **cell.fields(),
            "label": _label(cell),
            "run_id": f"P2-fixture-{index:02}",
            "status": "completed",
        }
        for index, cell in enumerate(cells())
    ]
    mapped = map_cells(records)
    assert set(mapped) == set(cells())
    with pytest.raises(ValueError, match="every completed P2 parent"):
        map_cells(records[:-1])
    duplicate = records.copy()
    duplicate[-1] = records[0]
    with pytest.raises(ValueError, match="invalid or duplicate"):
        map_cells(duplicate)


def test_control_remains_bypassed_frozen_and_optimizer_excluded() -> None:
    cell = Cell(101, 201, 301, CONTROL)
    model = FollowupModel(cell)
    optimizer = _optimizer(model)
    optimized = {id(parameter) for group in optimizer.param_groups for parameter in group["params"]}
    memory_ids = {id(parameter) for parameter in model.memory_state.parameters()}
    assert model.memory is None and model.bypass
    assert all(not parameter.requires_grad for parameter in model.memory_state.parameters())
    assert not optimized & memory_ids
    assert sum(parameter.numel() for parameter in model.parameters()) == 225793
    assert (
        sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
        == 27392
    )

    before = _state(model)
    batch = torch.randint(
        0, 256, (8, 65), generator=torch.Generator(device="cpu").manual_seed(7000)
    )
    _training_step(model, optimizer, batch, 257)
    assert all(
        torch.equal(value, model.state_dict()[name])
        for name, value in before.items()
        if name.startswith("memory_state.")
    )


def test_parent_conversion_resume_and_duration_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from arborlm import optimization_followup
    from arborlm.p2_data import order_ids as registered_order
    from arborlm.p3_checkpoint import counters as p3_counters

    cell = Cell(101, 201, 301, LEARNED)
    parent_identity = {"cell": cell.fields()}
    p3_identity = {
        "cell": cell.fields(),
        "parent": {"checkpoint_state_sha256": "synthetic-parent-identity"},
        "source_sha256": "synthetic-source-identity",
    }
    train = torch.randint(
        0, 256, (2048, 65), generator=torch.Generator(device="cpu").manual_seed(7001)
    )
    order = registered_order(cell.order)
    parent_model = FollowupModel(cell)
    parent_optimizer = _optimizer(parent_model)
    for step in range(1, 257):
        batch = train[order[((step - 1) * 8) % 2048 : ((step - 1) * 8) % 2048 + 8]]
        _training_step(parent_model, parent_optimizer, batch, step)
    assert all(int(state["step"].item()) == 256 for state in parent_optimizer.state.values())

    parent_path = tmp_path / "p2-parent"
    save_p2(parent_path, parent_model, parent_optimizer, 256, parent_identity)
    parent_state_hash = sha256((parent_path / "state.pt").read_bytes())
    parent_index_hash = sha256((parent_path / "index.json").read_bytes())
    initial_model_state = _state(parent_model)
    initial_optimizer_state = copy.deepcopy(parent_optimizer.state_dict())

    converted_model = FollowupModel(cell)
    converted_optimizer = _optimizer(converted_model)
    converted_path = tmp_path / "p3-step-256"
    conversion_hash = convert(
        parent_path,
        parent_identity,
        converted_path,
        converted_model,
        converted_optimizer,
        p3_identity,
    )
    assert sha256((parent_path / "state.pt").read_bytes()) == parent_state_hash
    assert sha256((parent_path / "index.json").read_bytes()) == parent_index_hash
    assert bitwise_equal(initial_model_state, converted_model.state_dict())
    assert bitwise_equal(initial_optimizer_state, converted_optimizer.state_dict())
    assert all(int(state["step"].item()) == 256 for state in converted_optimizer.state.values())
    converted_state = torch.load(converted_path / "state.pt", map_location="cpu", weights_only=True)
    assert converted_state["zero_training_conversion"] is True
    assert converted_state["counters"] == p3_counters(256)
    assert conversion_hash == sha256((converted_path / "state.pt").read_bytes())

    with pytest.raises(ValueError, match="factor identity"):
        bad_model = FollowupModel(cell)
        convert(
            parent_path,
            {"cell": Cell(101, 202, 301, LEARNED).fields()},
            tmp_path / "must-not-publish",
            bad_model,
            _optimizer(bad_model),
            p3_identity,
        )
    assert not (tmp_path / "must-not-publish").exists()
    assert sha256((parent_path / "state.pt").read_bytes()) == parent_state_hash

    for step in range(257, 513):
        batch = _batch(train, order, step)
        _training_step(parent_model, parent_optimizer, batch, step)
        _training_step(converted_model, converted_optimizer, batch, step)
    assert bitwise_equal(parent_model.state_dict(), converted_model.state_dict())
    assert bitwise_equal(parent_optimizer.state_dict(), converted_optimizer.state_dict())
    assert all(int(state["step"].item()) == 512 for state in converted_optimizer.state.values())

    checkpoint_512 = tmp_path / "p3-step-512"
    save_p3(checkpoint_512, converted_model, converted_optimizer, 512, p3_identity)
    resumed_model = FollowupModel(cell)
    resumed_optimizer = _optimizer(resumed_model)
    assert (
        restore_p3(checkpoint_512, resumed_model, resumed_optimizer, p3_identity)
        == p3_counters(512)
    )
    assert bitwise_equal(converted_model.state_dict(), resumed_model.state_dict())
    assert bitwise_equal(converted_optimizer.state_dict(), resumed_optimizer.state_dict())

    wrong_identity = {**p3_identity, "source_sha256": "wrong"}
    untouched = _state(resumed_model)
    optimizer_before_reject = copy.deepcopy(resumed_optimizer.state_dict())
    with pytest.raises(ValueError, match="identity mismatch"):
        restore_p3(checkpoint_512, resumed_model, resumed_optimizer, wrong_identity)
    assert bitwise_equal(untouched, resumed_model.state_dict())
    assert bitwise_equal(optimizer_before_reject, resumed_optimizer.state_dict())

    # The duration evaluator and fresh intervention restores must preserve the live
    # trajectory's Python and torch RNG as well as model and optimizer state.
    monkeypatch.setattr(optimization_followup, "VAL_TARGETS", 128)
    validation = torch.randint(
        0, 256, (2, 65), generator=torch.Generator(device="cpu").manual_seed(7002)
    )
    duration_dir = tmp_path / "duration-512"
    duration_dir.mkdir()
    before_model = _state(converted_model)
    before_optimizer = copy.deepcopy(converted_optimizer.state_dict())
    before_python_rng = random.getstate()
    before_torch_rng = torch.get_rng_state().clone()
    checkpoint_hash = sha256((checkpoint_512 / "state.pt").read_bytes())
    measurement = _duration(
        duration_dir,
        cell,
        checkpoint_512,
        checkpoint_hash,
        p3_identity,
        validation,
        converted_model,
        512,
    )
    assert measurement["reference"]["target_tokens"] == 128
    assert measurement["interventions"]["enabled"]["nll"] == measurement["reference"]["nll"]
    assert measurement["interventions"]["joint_within_branch"]["invariance_passed"] is True
    assert bitwise_equal(before_model, converted_model.state_dict())
    assert bitwise_equal(before_optimizer, converted_optimizer.state_dict())
    assert random.getstate() == before_python_rng
    assert torch.equal(torch.get_rng_state(), before_torch_rng)
    assert sha256((parent_path / "state.pt").read_bytes()) == parent_state_hash

    # A subsequent update after the intervening evaluations must match an untouched restore.
    batch = _batch(train, order, 513)
    _training_step(converted_model, converted_optimizer, batch, 513)
    _training_step(resumed_model, resumed_optimizer, batch, 513)
    assert bitwise_equal(converted_model.state_dict(), resumed_model.state_dict())
    assert bitwise_equal(converted_optimizer.state_dict(), resumed_optimizer.state_dict())


def test_duration_analysis_hand_computation_and_quality_guard() -> None:
    rows = []
    for cell in cells():
        durations = {}
        for step, enabled in ((256, 3.0), (512, 2.9), (1024, 2.8)):
            if cell.condition == CONTROL:
                nlls = {"enabled": enabled + 0.1}
            else:
                dependence = {256: 0.001, 512: 0.006, 1024: 0.012}[step]
                nlls = {
                    "enabled": enabled,
                    "disabled": enabled + dependence,
                    "values_permuted": enabled + dependence,
                    "joint_within_branch": enabled,
                }
            durations[str(step)] = nlls
        rows.append({**cell.fields(), "durations": durations})

    result = describe(rows)
    assert result["changes_from_256"]["1024"]["learned"]["D"]["mean"] == pytest.approx(0.011)
    assert result["changes_from_256"]["1024"]["learned"]["P"]["mean"] == pytest.approx(0.011)
    assert result["by_duration"]["1024"]["unique_control_nll"]["mean"] == pytest.approx(2.9)
    assert result["flags"] == {
        "duration_increases_dependence": True,
        "endpoint_dependence": True,
        "endpoint_quality_guard": True,
    }

    bad_quality = copy.deepcopy(rows)
    for row in bad_quality:
        for step in (512, 1024):
            row["durations"][str(step)]["enabled"] = 3.1
            if row["condition"] == CONTROL:
                row["durations"][str(step)]["enabled"] = 3.0
            else:
                delta = 0.006 if step == 512 else 0.012
                row["durations"][str(step)]["disabled"] = 3.1 + delta
                row["durations"][str(step)]["values_permuted"] = 3.1 + delta
                row["durations"][str(step)]["joint_within_branch"] = 3.1
    failed_guard = describe(bad_quality)
    assert failed_guard["flags"]["endpoint_quality_guard"] is False
