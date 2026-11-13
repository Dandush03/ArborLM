"""ADR-0006 invariants with offline synthetic fixtures."""

from pathlib import Path

import pytest
import torch

from arborlm.diagnose_memory import CONDITIONS, _cells, _invariance, _permute, _summary, launch
from arborlm.engine import optimizer_for
from arborlm.io import file_sha256, write_json
from arborlm.pilot_checkpoint import restore, save
from arborlm.pilot_metrics import loss_for
from arborlm.pilot_model import PER_BRANCH, SLOTS, PilotModel


def _snapshot(model: PilotModel) -> dict[str, torch.Tensor]:
    return {name: tensor.clone() for name, tensor in model.state_dict().items()}


def test_disabled_bypasses_memory_without_backbone_change() -> None:
    model = PilotModel("learned_tree", 42)
    tensors = _snapshot(model)
    dense = PilotModel("dense_small", 42)
    dense.load_state_dict(
        {key: val for key, val in tensors.items() if not key.startswith("memory.")}
    )
    batch = torch.arange(64)[None, :]
    assert _permute(model, 42, "disabled") is None
    assert model.memory is None
    assert set(model.state_dict()) == set(dense.state_dict())
    assert all(torch.equal(tensor, tensors[name]) for name, tensor in model.state_dict().items())
    logits, lookup = model(batch)
    assert lookup is None
    assert torch.equal(logits, dense(batch)[0])


def test_values_permutation_changes_only_values_and_preserves_multiset() -> None:
    seed = 43
    model = PilotModel("learned_tree", seed)
    before = _snapshot(model)
    perm = _permute(model, seed, "values_permuted")
    assert perm is not None
    reference = torch.randperm(SLOTS, generator=torch.Generator().manual_seed(9001 + seed))
    assert torch.equal(perm, reference)
    assert torch.equal(perm.sort().values, torch.arange(SLOTS))
    after = model.state_dict()
    assert not torch.equal(before["memory.values"], after["memory.values"])
    assert torch.equal(before["memory.values"][perm], after["memory.values"])
    assert torch.equal(after["memory.values"][perm.argsort()], before["memory.values"])
    assert all(
        torch.equal(value, after[key]) for key, value in before.items() if key != "memory.values"
    )


def test_joint_permutation_preserves_branch_membership_and_pairs() -> None:
    seed = 44
    model = PilotModel("learned_tree", seed)
    before = _snapshot(model)
    perm = _permute(model, seed, "joint_within_branch")
    assert perm is not None
    assert torch.equal(perm.sort().values, torch.arange(SLOTS))
    assert torch.equal(perm // PER_BRANCH, torch.arange(SLOTS) // PER_BRANCH)
    generator = torch.Generator().manual_seed(10001 + seed)
    for branch in range(16):
        lo = branch * PER_BRANCH
        expected = lo + torch.randperm(PER_BRANCH, generator=generator)
        assert torch.equal(perm[lo : lo + PER_BRANCH], expected)
    for name, tensor in model.state_dict().items():
        expected = before[name][perm] if name in ("memory.keys", "memory.values") else before[name]
        assert torch.equal(tensor, expected)


@pytest.mark.parametrize("condition", ("values_permuted", "joint_within_branch"))
def test_repeated_permutation_seed_is_deterministic_without_global_rng_change(
    condition: str,
) -> None:
    a = PilotModel("learned_tree", 42)
    b = PilotModel("learned_tree", 42)
    rng = torch.get_rng_state()
    left, right = _permute(a, 42, condition), _permute(b, 42, condition)
    assert left is not None and right is not None and torch.equal(left, right)
    assert torch.equal(rng, torch.get_rng_state())


def test_original_checkpoint_bytes_unchanged_across_conditions(tmp_path: Path) -> None:
    # Small synthetic checkpoint fixture; it is not a registered pilot cell.
    model = PilotModel("learned_tree", 42)
    optimizer = optimizer_for(model)
    batch = torch.tensor([[1, 2, 3]], dtype=torch.int64)
    optimizer.zero_grad(set_to_none=True)
    logits, _ = model(batch[:, :-1])
    loss_for(logits, batch[:, 1:], "mean").backward()
    optimizer.step()
    # Supply step metadata for this serialization fixture without training 128 steps.
    for state in optimizer.state.values():
        state["step"].fill_(128)
    path = tmp_path / "checkpoint-128"
    identity = {"variant": "learned_tree", "seed": 42}
    save(path, model, optimizer, 128, identity)
    hashes = {name: file_sha256(path / name) for name in ("index.json", "state.pt")}
    for condition in CONDITIONS:
        clone = PilotModel("learned_tree", 42)
        assert restore(path, clone, optimizer_for(clone), identity) == (128, 1024, 65536)
        _permute(clone, 42, condition)
        assert all(file_sha256(path / name) == digest for name, digest in hashes.items())


def test_gate_and_unexecuted_cell_semantics(tmp_path: Path) -> None:
    assert _invariance("original", 2.0, 2.0)
    assert not _invariance("original", 2.0000001, 2.0)
    assert _invariance("joint_within_branch", 2.0000009, 2.0)
    assert not _invariance("joint_within_branch", 2.0000011, 2.0)
    cells = _cells()
    assert len(cells) == 12
    assert [(cell["seed"], cell["condition"]) for cell in cells] == [
        (seed, condition) for seed in (42, 43, 44) for condition in CONDITIONS
    ]
    cells[0].update(status="completed", nll=2.0, delta_nll=0.0)
    cells[1].update(status="running")
    write_json(tmp_path / "cells.json", cells)
    summary = _summary(tmp_path, "test watchdog failure")
    assert summary["outcome"] == "failed"
    assert summary["cells"][0]["status"] == "completed"
    assert summary["cells"][1]["status"] == "interrupted"
    assert all(cell["status"] == "unexecuted" for cell in summary["cells"][2:])


def test_output_cannot_be_inside_original_suite(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside the original pilot suite"):
        launch(tmp_path, tmp_path / "nested")
