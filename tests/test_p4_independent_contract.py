"""Independent synthetic contract checks for the registered P4 capacity screen."""

import copy
import hashlib
import json
import random
from pathlib import Path

import pytest
import torch
from torch.nn import functional as F

from arborlm.p2_config import BACKBONES, ORDERS
from arborlm.p2_config import CONTROL as P2_CONTROL
from arborlm.p2_config import Cell as P2Cell
from arborlm.p2_model import FollowupModel
from arborlm.p4_checkpoint import restore as restore_p4
from arborlm.p4_checkpoint import save as save_p4
from arborlm.p4_config import (
    BASELINE,
    DENSE,
    MEMORY,
    Cell,
    batch_offset,
    cells,
    counters,
)
from arborlm.p4_model import (
    DenseAdapter,
    FrozenModel,
    Memory,
    backbone_digest,
    evaluate,
    extract,
    intervene,
    optimizer_for,
    optimizer_names,
    train_step,
)


def _parent(backbone: int = 101, order: int = 301) -> FollowupModel:
    return FollowupModel(P2Cell(backbone, 201, order, P2_CONTROL))


def _batch(seed: int = 913) -> torch.Tensor:
    return torch.randint(0, 256, (8, 5), generator=torch.Generator(device="cpu").manual_seed(seed))


def _tensor_snapshot(module: torch.nn.Module) -> dict[str, torch.Tensor]:
    tensors = dict(module.named_parameters()) | dict(module.named_buffers())
    return {name: value.detach().clone() for name, value in tensors.items()}


def _bitwise_equal(left: torch.Tensor, right: torch.Tensor) -> bool:
    return (
        left.shape == right.shape
        and left.dtype == right.dtype
        and torch.equal(
            left.detach().contiguous().reshape(-1).view(torch.uint8),
            right.detach().contiguous().reshape(-1).view(torch.uint8),
        )
    )


def _assert_snapshot(module: torch.nn.Module, before: dict[str, torch.Tensor]) -> None:
    tensors = dict(module.named_parameters()) | dict(module.named_buffers())
    assert set(tensors) == set(before)
    assert all(_bitwise_equal(tensors[name], value) for name, value in before.items())


def _independent_backbone_digest(module: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    tensors = sorted([*module.named_parameters(), *module.named_buffers()])
    for name, tensor in tensors:
        metadata = (
            json.dumps(
                {"name": name, "shape": list(tensor.shape), "dtype": str(tensor.dtype)},
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        )
        digest.update(metadata.encode())
        raw = tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
        digest.update(bytes(raw.tolist()))
    return digest.hexdigest()


def _addition_state(model: FrozenModel) -> dict[str, torch.Tensor]:
    assert model.addition is not None
    return {name: value.detach().clone() for name, value in model.addition.state_dict().items()}


def _assert_addition_state(
    model: FrozenModel, before: dict[str, torch.Tensor], *, changed: bool
) -> None:
    assert model.addition is not None
    after = model.addition.state_dict()
    assert set(after) == set(before)
    equal = all(_bitwise_equal(after[name], value) for name, value in before.items())
    assert equal is (not changed)


def test_registry_counts_and_parameter_matched_optimizer_membership() -> None:
    registered = cells()
    assert len(registered) == 63
    assert sum(cell.variant == BASELINE for cell in registered) == 9
    assert sum(cell.variant == MEMORY for cell in registered) == 27
    assert sum(cell.variant == DENSE for cell in registered) == 27

    for variant in (MEMORY, DENSE):
        model = FrozenModel(Cell(101, 301, 401, variant), _parent())
        optimizer = optimizer_for(model)
        assert optimizer is not None
        names = optimizer_names(model, optimizer)
        parameters = dict(model.named_parameters())
        expected_names = [name for name, param in parameters.items() if param.requires_grad]
        actual = [param for group in optimizer.param_groups for param in group["params"]]
        assert names == expected_names
        assert len({id(param) for param in actual}) == len(actual)
        assert [id(param) for param in actual] == [id(parameters[name]) for name in names]
        assert sum(parameters[name].numel() for name in names) == 198401
        assert all(name.startswith("addition.") for name in names)
        assert all(
            not param.requires_grad and param.grad is None for param in model.backbone.parameters()
        )
        assert optimizer.defaults["lr"] == 0.003
        assert optimizer.defaults["betas"] == (0.9, 0.999)
        assert optimizer.defaults["eps"] == 1e-8
        assert optimizer.defaults["weight_decay"] == 0
        assert optimizer.defaults["amsgrad"] is False
        assert optimizer.defaults["foreach"] is False
        assert optimizer.defaults["fused"] is False

    baseline = FrozenModel(Cell(101, 301, 0, BASELINE), _parent())
    assert optimizer_for(baseline) is None
    assert sum(parameter.numel() for parameter in baseline.parameters()) == 27392
    assert all(not parameter.requires_grad for parameter in baseline.parameters())


def test_parent_extraction_digest_tied_output_and_bypass_are_bitwise() -> None:
    parent = _parent()
    parent.eval()
    before = _tensor_snapshot(parent)
    backbone = extract(parent)
    extracted = FrozenModel(Cell(101, 301, 0, BASELINE), backbone)
    assert backbone_digest(backbone) == _independent_backbone_digest(backbone)
    assert backbone_digest(extracted.backbone) == _independent_backbone_digest(extracted.backbone)
    assert backbone_digest(backbone) == backbone_digest(extracted.backbone)

    parent_parameters = dict(parent.named_parameters())
    extracted_parameters = dict(extracted.backbone.named_parameters())
    assert set(parent_parameters) - {
        n for n in parent_parameters if n.startswith("memory_state.")
    } == set(extracted_parameters)
    for name, value in extracted_parameters.items():
        assert _bitwise_equal(value, parent_parameters[name])
    assert _bitwise_equal(extracted.backbone.mask, parent.mask)
    assert extracted.token.weight.data_ptr() == extracted.backbone.token.weight.data_ptr()
    assert not hasattr(extracted, "lm_head") and not hasattr(extracted, "output_head")

    tokens = _batch()[:, :-1]
    with torch.no_grad():
        parent_logits, parent_lookup = parent(tokens)
        extracted_logits, extracted_lookup = extracted(tokens)
        hidden = extracted.token(tokens) + extracted.position(torch.arange(tokens.shape[1]))
        hidden = extracted.blocks[0](hidden, extracted.mask[: tokens.shape[1], : tokens.shape[1]])
        hidden = extracted.blocks[1](hidden, extracted.mask[: tokens.shape[1], : tokens.shape[1]])
        tied_projection_logits = F.linear(extracted.final_norm(hidden), extracted.token.weight)
    assert parent_lookup is extracted_lookup is None
    assert _bitwise_equal(parent_logits, extracted_logits)
    assert _bitwise_equal(extracted_logits, tied_projection_logits)
    assert sum(parameter.numel() for parameter in extracted.parameters()) == 27392
    _assert_snapshot(parent, before)


@pytest.mark.parametrize("variant", (MEMORY, DENSE))
def test_disabling_each_addition_matches_frozen_parent_logits(variant: str) -> None:
    parent = _parent()
    parent.eval()
    baseline = FrozenModel(Cell(101, 301, 0, BASELINE), parent)
    model = FrozenModel(Cell(101, 301, 401, variant), parent)
    model.eval()
    assert model.addition is not None
    assert model.bypass is False
    assert intervene(model, "disabled") is None
    assert model.bypass is True
    tokens = _batch(914)[:, :-1]
    with torch.no_grad():
        expected, _ = baseline(tokens)
        actual, lookup = model(tokens)
    assert lookup is None
    assert _bitwise_equal(actual, expected)


@pytest.mark.parametrize("variant", (MEMORY, DENSE))
def test_updates_leave_every_frozen_backbone_tensor_and_buffer_unchanged(
    variant: str,
) -> None:
    parent = _parent()
    parent_before = _tensor_snapshot(parent)
    model = FrozenModel(Cell(101, 301, 401, variant), parent)
    optimizer = optimizer_for(model)
    assert optimizer is not None
    backbone_before = _tensor_snapshot(model.backbone)
    digest_before = backbone_digest(model.backbone)
    addition_before = _addition_state(model)

    for step in (1, 2, 3):
        loss, norm, router_norm = train_step(model, optimizer, _batch(920 + step), step)
        assert torch.isfinite(torch.tensor(loss))
        assert torch.isfinite(torch.tensor(norm))
        assert router_norm is None or torch.isfinite(torch.tensor(router_norm))

    _assert_snapshot(model.backbone, backbone_before)
    _assert_snapshot(parent, parent_before)
    assert backbone_digest(model.backbone) == digest_before
    _assert_addition_state(model, addition_before, changed=True)
    assert all(parameter.grad is None for parameter in model.backbone.parameters())
    assert all(not parameter.requires_grad for parameter in model.backbone.parameters())
    assert model.backbone.mask.grad_fn is None
    baseline = FrozenModel(Cell(101, 301, 0, BASELINE), parent)
    model.eval()
    baseline.eval()
    assert intervene(model, "disabled") is None
    with torch.no_grad():
        baseline_logits, _ = baseline(_batch(929)[:, :-1])
        disabled_logits, lookup = model(_batch(929)[:, :-1])
    assert lookup is None
    assert _bitwise_equal(disabled_logits, baseline_logits)


@pytest.mark.parametrize("variant", (MEMORY, DENSE))
def test_gradients_flow_through_frozen_suffix_into_addition(variant: str) -> None:
    model = FrozenModel(Cell(101, 301, 401, variant), _parent())
    model.train()
    optimizer = optimizer_for(model)
    assert optimizer is not None and model.addition is not None
    train_step(model, optimizer, _batch(950), 1)
    addition_gradients = [parameter.grad for parameter in model.addition.parameters()]
    assert all(gradient is not None for gradient in addition_gradients)
    assert all(
        torch.isfinite(gradient).all() for gradient in addition_gradients if gradient is not None
    )
    assert any(
        bool(gradient.ne(0).any()) for gradient in addition_gradients if gradient is not None
    )
    assert all(parameter.grad is None for parameter in model.backbone.parameters())
    assert all(not parameter.requires_grad for parameter in model.backbone.parameters())


def test_memory_and_dense_initialization_use_independent_seeded_generators() -> None:
    parent = _parent()
    torch.manual_seed(123456)
    rng_before = torch.get_rng_state().clone()
    first = FrozenModel(Cell(101, 301, 401, MEMORY), parent)
    assert _bitwise_equal(torch.get_rng_state(), rng_before)
    torch.manual_seed(987654)
    second = FrozenModel(Cell(103, 303, 401, MEMORY), _parent(103, 303))
    dense_a = DenseAdapter(401)
    dense_b = DenseAdapter(401)
    assert first.addition is not None and second.addition is not None
    assert all(
        _bitwise_equal(first.addition.state_dict()[name], second.addition.state_dict()[name])
        for name in first.addition.state_dict()
    )
    assert all(
        _bitwise_equal(dense_a.state_dict()[name], dense_b.state_dict()[name])
        for name in dense_a.state_dict()
    )


def test_dense_adapter_matches_registered_formula_exactly() -> None:
    adapter = DenseAdapter(401)
    h = torch.randn(2, 3, 32, generator=torch.Generator().manual_seed(962))
    expected = h + adapter.gate.sigmoid() * F.linear(
        F.gelu(F.linear(h, adapter.w1), approximate="none"), adapter.w2
    )
    actual, lookup = adapter(h)
    assert lookup is None
    assert torch.equal(actual, expected)


def test_evaluation_uses_independent_token_weighted_nll_and_preserves_state() -> None:
    model = FrozenModel(Cell(101, 301, 401, DENSE), _parent())
    model.train()
    rows = torch.randint(0, 256, (9, 5), generator=torch.Generator(device="cpu").manual_seed(951))
    model_before = _tensor_snapshot(model)
    python_rng = random.getstate()
    torch_rng = torch.get_rng_state().clone()
    with torch.no_grad():
        logits, _ = model(rows[:, :-1])
        token_losses = torch.logsumexp(logits.double(), dim=-1) - logits.double().gather(
            -1, rows[:, 1:, None]
        ).squeeze(-1)
        expected = token_losses.sum().item() / rows[:, 1:].numel()
    result = evaluate(model, rows, expected_targets=rows[:, 1:].numel())
    assert result["target_tokens"] == 36
    # Evaluation uses actual 8+1 float32 batch reductions; the double oracle
    # intentionally sums per-token losses independently, so allow float32
    # kernel/reduction roundoff while remaining far below a meaningful NLL shift.
    assert result["nll"] == pytest.approx(expected, abs=2e-6, rel=0)
    assert result["nll_units"] == "nats_per_byte"
    assert result["byte_perplexity"] == pytest.approx(torch.exp(torch.tensor(expected)).item())
    assert model.training
    _assert_snapshot(model, model_before)
    assert random.getstate() == python_rng
    assert _bitwise_equal(torch.get_rng_state(), torch_rng)


def test_evaluation_weights_unequal_batches_by_token_count() -> None:
    class KnownLogitModel(torch.nn.Module):
        memory = None

        def forward(self, tokens: torch.Tensor) -> tuple[torch.Tensor, None]:
            logits = torch.zeros((*tokens.shape, 256), dtype=torch.float32)
            is_last = tokens[:, 0] == 8
            logits[~is_last, :, 1] = 10.0
            logits[is_last, :, 2] = -10.0
            return logits, None

    rows = torch.zeros((9, 5), dtype=torch.int64)
    rows[:, 0] = torch.arange(9)
    rows[:8, 1:] = 1
    rows[8, 1:] = 2
    logits = torch.zeros((9, 4, 256), dtype=torch.float64)
    logits[:8, :, 1] = 10.0
    logits[8, :, 2] = -10.0
    targets = rows[:, 1:]
    token_losses = torch.logsumexp(logits, dim=-1) - logits.gather(
        -1, targets.unsqueeze(-1)
    ).squeeze(-1)
    expected_weighted = token_losses.sum().item() / targets.numel()
    first_batch_mean = token_losses[:8].mean().item()
    last_batch_mean = token_losses[8:].mean().item()
    incorrect_unweighted_batch_mean = (first_batch_mean + last_batch_mean) / 2

    result = evaluate(KnownLogitModel(), rows, expected_targets=36)  # type: ignore[arg-type]

    assert result["nll"] == pytest.approx(expected_weighted, abs=2e-6, rel=0)
    assert abs(result["nll"] - incorrect_unweighted_batch_mean) > 1.0


def test_causal_prefix_logits_are_unchanged_by_future_token_perturbation() -> None:
    model = FrozenModel(Cell(101, 301, 401, MEMORY), _parent())
    model.eval()
    first = torch.tensor([[11, 12, 13, 14]], dtype=torch.int64)
    changed_future = first.clone()
    changed_future[0, 3] = 222
    with torch.no_grad():
        logits_a, _ = model(first)
        logits_b, _ = model(changed_future)
    assert logits_a.shape == (1, 4, 256)
    assert _bitwise_equal(logits_a[:, :3], logits_b[:, :3])


def test_memory_permutations_match_seeded_ids_and_preserve_contract() -> None:
    model = FrozenModel(Cell(102, 302, 402, MEMORY), _parent(102, 302))
    assert isinstance(model.addition, Memory)
    before = {name: value.detach().clone() for name, value in model.addition.state_dict().items()}
    index = (102 - 101) * 9 + (302 - 301) * 3 + (402 - 401)

    generator = torch.Generator(device="cpu").manual_seed(40000 + index)
    expected_values_ids = torch.randperm(4096, generator=generator)
    values_ids, values_seed = intervene(model, "values_permuted")
    assert values_seed == 40000 + index
    assert torch.equal(values_ids, expected_values_ids)
    assert torch.equal(model.addition.values, before["values"][expected_values_ids])
    for name, value in before.items():
        if name != "values":
            assert torch.equal(model.addition.state_dict()[name], value)

    model = FrozenModel(Cell(102, 302, 402, MEMORY), _parent(102, 302))
    assert isinstance(model.addition, Memory)
    before = {name: value.detach().clone() for name, value in model.addition.state_dict().items()}
    generator = torch.Generator(device="cpu").manual_seed(50000 + index)
    expected_joint_ids = torch.cat(
        [branch * 256 + torch.randperm(256, generator=generator) for branch in range(16)]
    )
    joint_ids, joint_seed = intervene(model, "joint_within_branch")
    assert joint_seed == 50000 + index
    assert torch.equal(joint_ids, expected_joint_ids)
    assert torch.equal(model.addition.keys, before["keys"][expected_joint_ids])
    assert torch.equal(model.addition.values, before["values"][expected_joint_ids])
    assert torch.equal(torch.div(joint_ids, 256, rounding_mode="floor"), torch.arange(4096) // 256)
    for name, value in before.items():
        if name not in ("keys", "values"):
            assert torch.equal(model.addition.state_dict()[name], value)


def test_registered_two_epoch_offsets_and_checkpoint_counters() -> None:
    expected = {
        0: (0, 0, 0),
        1: (8, 8, 512),
        256: (2048, 0, 131072),
        257: (2056, 8, 131584),
        512: (4096, 0, 262144),
    }
    for step, values in expected.items():
        result = counters(step)
        assert (
            result["absolute_order_cursor"],
            result["next_cyclic_order_cursor"],
            result["additional_targets"],
        ) == values
    assert [batch_offset(step) for step in (1, 255, 256, 257, 511, 512)] == [
        0,
        2032,
        2040,
        0,
        2032,
        2040,
    ]
    with pytest.raises(ValueError, match="invalid P4 update"):
        batch_offset(0)
    with pytest.raises(ValueError, match="invalid P4 checkpoint step"):
        counters(513)


def test_p4_panel_split_requires_2048_unique_candidates_and_full_train_disjointness() -> None:
    from arborlm.io import sha256
    from arborlm.p4_data import panel
    from arborlm.pilot_data import Candidate

    validation = [
        Candidate(
            f"rank-{index:04}",
            index,
            0,
            index.to_bytes(4, "big") + bytes([index % 251]) * 61,
        )
        for index in range(2048)
    ]
    p1, p2, p3, p4 = panel(validation, set())
    expected = [
        b"".join(row.payload for row in validation[start : start + 512])
        for start in (0, 512, 1024, 1536)
    ]
    assert [p1, p2, p3, p4] == expected
    assert all(len(part) == 512 * 65 for part in (p1, p2, p3, p4))
    with pytest.raises(ValueError, match="first 2048"):
        panel(validation[:-1], set())
    duplicate = validation.copy()
    duplicate[1800] = validation[12]
    with pytest.raises(ValueError, match="overlap"):
        panel(duplicate, set())
    train_overlap = {sha256(validation[1700].payload)}
    with pytest.raises(ValueError, match="overlap"):
        panel(validation, train_overlap)


def test_parent_map_requires_all_nine_completed_unique_controls() -> None:
    from arborlm.p4_parent import map_parents

    records = [
        {
            "backbone": backbone,
            "order": order,
            "memory": 201,
            "condition": "disabled_throughout",
            "label": f"b{backbone}-o{order}-control",
            "run_id": f"P3LT-fixture-{backbone}-{order}",
            "status": "completed",
        }
        for backbone in BACKBONES
        for order in ORDERS
    ]
    mapped = map_parents(records)
    assert set(mapped) == {(backbone, order) for backbone in BACKBONES for order in ORDERS}
    with pytest.raises(ValueError, match="all nine"):
        map_parents(records[:-1])
    duplicate = records.copy()
    duplicate[-1] = records[0]
    with pytest.raises(ValueError, match="invalid or duplicate"):
        map_parents(duplicate)
    wrong = records.copy()
    wrong[-1] = {**wrong[-1], "run_id": "../outside"}
    with pytest.raises(ValueError, match="invalid or duplicate"):
        map_parents(wrong)


def test_checkpoint_restore_roundtrip_rng_parent_identity_and_membership_rejection(
    tmp_path: Path,
) -> None:
    import shutil

    from arborlm.p3_checkpoint import bitwise_equal

    cell = Cell(101, 301, 401, MEMORY)
    parent = _parent()
    model = FrozenModel(cell, parent)
    optimizer = optimizer_for(model)
    assert optimizer is not None
    identity = {
        "cell": cell.fields(),
        "backbone_sha256": backbone_digest(model.backbone),
        "parent": {"checkpoint_state_sha256": "synthetic-parent"},
        "order_sha256": "synthetic-order",
    }
    train_step(model, optimizer, _batch(961), 1)
    # A synthetic restored-state fixture exercises the registered 256-step
    # checkpoint schema without spending a real training trajectory.
    for state in optimizer.state.values():
        state["step"].fill_(256)
    for name, value in model.named_parameters():
        if name.startswith("addition."):
            assert value.isfinite().all()

    random.seed(8001)
    torch.manual_seed(8002)
    expected_python_rng = random.getstate()
    expected_torch_rng = torch.get_rng_state().clone()
    checkpoint = tmp_path / "p4-step-256"
    checkpoint_hash = save_p4(checkpoint, model, optimizer, 256, identity)
    assert checkpoint_hash == hashlib.sha256((checkpoint / "state.pt").read_bytes()).hexdigest()
    index = json.loads((checkpoint / "index.json").read_text())
    assert index["state_sha256"] == checkpoint_hash
    stored = torch.load(checkpoint / "state.pt", map_location="cpu", weights_only=True)
    assert stored["counters"] == counters(256)
    assert stored["identity"] == identity
    assert stored["optimizer_parameter_names"] == optimizer_names(model, optimizer)

    restored_parent = _parent()
    restored = FrozenModel(cell, restored_parent)
    restored_optimizer = optimizer_for(restored)
    assert restored_optimizer is not None
    different_initialization = {**identity, "backbone_sha256": backbone_digest(restored.backbone)}
    random.seed(1)
    torch.manual_seed(2)
    assert restore_p4(
        checkpoint, restored, restored_optimizer, different_initialization
    ) == counters(256)
    assert bitwise_equal(model.state_dict(), restored.state_dict())
    assert bitwise_equal(optimizer.state_dict(), restored_optimizer.state_dict())
    assert random.getstate() == expected_python_rng
    assert torch.equal(torch.get_rng_state(), expected_torch_rng)

    # Resume from the same serialized model/optimizer/RNG state; the remaining
    # synthetic updates must match an uninterrupted continuation bitwise.
    for step in (257, 258):
        batch = _batch(970 + step)
        train_step(model, optimizer, batch, step)
        train_step(restored, restored_optimizer, batch, step)
    assert bitwise_equal(model.state_dict(), restored.state_dict())
    assert bitwise_equal(optimizer.state_dict(), restored_optimizer.state_dict())

    untouched_model = _tensor_snapshot(restored)
    untouched_optimizer = copy.deepcopy(restored_optimizer.state_dict())
    wrong_parent = {**identity, "parent": {"checkpoint_state_sha256": "wrong-parent"}}
    with pytest.raises(ValueError, match="schema/identity"):
        restore_p4(checkpoint, restored, restored_optimizer, wrong_parent)
    _assert_snapshot(restored, untouched_model)
    assert bitwise_equal(untouched_optimizer, restored_optimizer.state_dict())

    wrong_variant_cell = Cell(101, 301, 401, DENSE)
    wrong_variant = FrozenModel(wrong_variant_cell, _parent())
    wrong_variant_optimizer = optimizer_for(wrong_variant)
    wrong_variant_identity = {
        "cell": wrong_variant_cell.fields(),
        "backbone_sha256": backbone_digest(wrong_variant.backbone),
        "parent": identity["parent"],
        "order_sha256": identity["order_sha256"],
    }
    with pytest.raises(ValueError, match="schema/identity"):
        restore_p4(checkpoint, wrong_variant, wrong_variant_optimizer, wrong_variant_identity)

    membership_error = torch.optim.AdamW([next(restored.addition.parameters())], lr=0.003)
    with pytest.raises(ValueError, match="optimizer membership"):
        restore_p4(checkpoint, restored, membership_error, identity)
    _assert_snapshot(restored, untouched_model)

    masked = FrozenModel(cell, _parent())
    masked_identity = {**identity, "backbone_sha256": backbone_digest(masked.backbone)}
    masked.backbone.mask[0, 1] = 0.0
    with pytest.raises(ValueError, match="frozen-backbone mismatch"):
        save_p4(tmp_path / "mutated-mask", masked, optimizer_for(masked), 0, masked_identity)
    with pytest.raises(ValueError, match="frozen-backbone mismatch"):
        restore_p4(checkpoint, masked, optimizer_for(masked), identity)

    corrupt = tmp_path / "corrupt-checkpoint"
    shutil.copytree(checkpoint, corrupt)
    with (corrupt / "state.pt").open("ab") as stream:
        stream.write(b"corrupt")
    before_corrupt_restore = _tensor_snapshot(restored)
    with pytest.raises(ValueError, match="checksum mismatch"):
        restore_p4(corrupt, restored, restored_optimizer, identity)
    _assert_snapshot(restored, before_corrupt_restore)


def test_paired_analysis_recomputes_registered_capacity_dependence_and_dense_flags() -> None:
    from arborlm.p4_analysis import describe

    rows = []
    negative_cells = {
        (101, 301, 401),
        (101, 301, 402),
        (101, 301, 403),
        (101, 302, 401),
        (101, 302, 402),
    }
    for backbone in BACKBONES:
        for order in ORDERS:
            baseline_nll = 2.0 + (backbone - 101) * 0.1 + (order - 301) * 0.01
            rows.append(
                {
                    **Cell(backbone, order, 0, BASELINE).fields(),
                    "initial_nll": None,
                    "final_nll": baseline_nll,
                    "interventions": {"enabled": baseline_nll},
                }
            )
            for seed in (401, 402, 403):
                positive = (backbone, order, seed) not in negative_cells
                memory_nll = baseline_nll - 0.01 if positive else baseline_nll + 0.001
                dense_nll = memory_nll + 0.003
                rows.append(
                    {
                        **Cell(backbone, order, seed, MEMORY).fields(),
                        "initial_nll": memory_nll + 0.02,
                        "final_nll": memory_nll,
                        "interventions": {
                            "enabled": memory_nll,
                            "disabled": baseline_nll,
                            "values_permuted": memory_nll + (0.01 if positive else -0.001),
                            "joint_within_branch": memory_nll,
                        },
                    }
                )
                rows.append(
                    {
                        **Cell(backbone, order, seed, DENSE).fields(),
                        "initial_nll": dense_nll + 0.02,
                        "final_nll": dense_nll,
                        "interventions": {
                            "enabled": dense_nll,
                            "disabled": baseline_nll,
                        },
                    }
                )
    result = describe(rows)
    assert result["summary"]["C"]["mean"] == pytest.approx((22 * 0.01 - 5 * 0.001) / 27)
    assert result["summary"]["D"]["mean"] == result["summary"]["C"]["mean"]
    assert result["summary"]["P"]["mean"] == pytest.approx((22 * 0.01 - 5 * 0.001) / 27)
    assert result["summary"]["Q"]["mean"] == pytest.approx(0.003)
    assert result["counts"]["C_positive_cells"] == 22
    assert result["counts"]["C_positive_parents"] == 8
    assert result["counts"]["C_and_P_positive_cells"] == 22
    assert result["counts"]["P_positive_parents"] == 8
    assert result["composite_success"]
    assert not result["flags"]["secondary_memory_advantage"]

    broken = copy.deepcopy(rows)
    memory_row = next(row for row in broken if row["variant"] == MEMORY)
    memory_row["interventions"]["disabled"] += 0.01
    with pytest.raises(ValueError, match="equal their baseline bitwise"):
        describe(broken)

    failed_clause = copy.deepcopy(rows)
    positive_cell = next(
        row
        for row in failed_clause
        if row["variant"] == MEMORY and row["backbone"] == 102 and row["order"] == 301
    )
    parent_baseline = next(
        row["final_nll"]
        for row in failed_clause
        if row["variant"] == BASELINE
        and row["backbone"] == positive_cell["backbone"]
        and row["order"] == positive_cell["order"]
    )
    positive_cell["final_nll"] = parent_baseline + 0.001
    positive_cell["interventions"]["enabled"] = parent_baseline + 0.001
    positive_cell["interventions"]["disabled"] = parent_baseline
    positive_cell["interventions"]["values_permuted"] = parent_baseline
    positive_cell["interventions"]["joint_within_branch"] = parent_baseline + 0.001
    failed = describe(failed_clause)
    assert failed["counts"]["C_positive_cells"] == 21
    assert not failed["flags"]["added_predictive_capacity"]
    assert not failed["flags"]["useful_slot_association_dependence"]
