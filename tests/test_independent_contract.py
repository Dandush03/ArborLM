"""Independent engineering checks for the approved E0 contract."""

import copy
import hashlib
import math
import random

import pytest
import torch

from arborlm.data import generate_dataset, next_token_batch
from arborlm.engine import aggregate_evaluation, evaluate, optimizer_for, train_step
from arborlm.model import DenseBaseline


def _logits_for_target_zero() -> torch.Tensor:
    """Logits whose target-0 probability is 2/17 and all others are 1/17."""
    logits = torch.zeros((1, 1, 16), dtype=torch.float32)
    logits[0, 0, 0] = math.log(2.0)
    return logits


def _assert_nested_tensors_equal(left: object, right: object) -> None:
    if isinstance(left, torch.Tensor):
        assert isinstance(right, torch.Tensor)
        assert torch.equal(left, right)
    elif isinstance(left, dict):
        assert isinstance(right, dict)
        assert left.keys() == right.keys()
        for key in left:
            _assert_nested_tensors_equal(left[key], right[key])
    elif isinstance(left, list | tuple):
        assert isinstance(right, type(left))
        assert len(left) == len(right)
        for first, second in zip(left, right, strict=True):
            _assert_nested_tensors_equal(first, second)
    else:
        assert left == right


def test_nonuniform_loss_and_unequal_batch_token_weighting() -> None:
    logits = _logits_for_target_zero()
    target_zero = torch.tensor([[0]], dtype=torch.int64)
    # Z = 2 + 15 = 17, so target 0 has probability 2/17.
    observed = aggregate_evaluation([(logits, target_zero)])
    assert observed["nll"] == pytest.approx(math.log(17.0 / 2.0), abs=1e-7)

    # One token in the first batch has loss ln(17/2); three tokens in the
    # second batch each have uniform loss ln(16). Aggregate by tokens, not
    # by averaging the two batch means.
    uniform_logits = torch.zeros((1, 3, 16), dtype=torch.float32)
    three_targets = torch.tensor([[0, 1, 2]], dtype=torch.int64)
    weighted = aggregate_evaluation(
        [(logits, target_zero), (uniform_logits, three_targets)]
    )
    expected = (math.log(17.0 / 2.0) + 3 * math.log(16.0)) / 4
    assert weighted["tokens"] == 4
    assert weighted["nll"] == pytest.approx(expected, abs=1e-7)
    assert weighted["nll"] != pytest.approx(
        (math.log(17.0 / 2.0) + math.log(16.0)) / 2, abs=1e-7
    )


def test_next_token_alignment_and_independently_calculated_generator_golden() -> None:
    row = list(range(8)) * 4 + list(range(8))[:1]
    x, y = next_token_batch([row])
    assert x.dtype == torch.int64
    assert y.dtype == torch.int64
    assert x.shape == y.shape == (1, 32)
    assert x.tolist() == [row[:32]]
    assert y.tolist() == [row[1:33]]
    assert y[0, :-1].tolist() == x[0, 1:].tolist()

    # Independently computed with hashlib.sha256 over the ADR's literal input:
    # digest bcfe930294b2a10ece907df5df08a4724b1b961e6bc1d3371120c984274b8e73
    # first eight bytes modulo 16 -> [12, 14, 3, 2, 4, 2, 1, 14].
    motif = [12, 14, 3, 2, 4, 2, 1, 14]
    generated = generate_dataset()
    assert generated.train[0] == (motif * 5)[:33]
    assert hashlib.sha256(b"arborlm-e0-v1:101:0").hexdigest() == (
        "bcfe930294b2a10ece907df5df08a4724b1b961e6bc1d3371120c984274b8e73"
    )


def test_model_shape_parameter_count_and_causal_perturbation() -> None:
    torch.manual_seed(7)
    model = DenseBaseline().eval()
    tokens = torch.arange(32, dtype=torch.int64).remainder(16).unsqueeze(0)
    changed = tokens.clone()
    changed[:, 14:] = (changed[:, 14:] + 5).remainder(16)

    with torch.no_grad():
        logits = model(tokens)
        changed_logits = model(changed)

    assert logits.shape == (1, 32, 16)
    assert logits.dtype == torch.float32
    assert sum(parameter.numel() for parameter in model.parameters()) == 18_688
    assert all(parameter.requires_grad for parameter in model.parameters())
    # Changing tokens strictly after position 13 cannot affect logits at or
    # before position 13 in this causal model.
    torch.testing.assert_close(logits[:, :14], changed_logits[:, :14], atol=1e-7, rtol=0)


def test_evaluation_isolates_state_on_success_and_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    random.seed(29)
    torch.manual_seed(29)
    model = DenseBaseline()
    optimizer = optimizer_for(model)
    rows = [list(range(8)) * 4 + [0]] * 8
    train_step(model, optimizer, rows)
    model.train()

    model_before = {key: value.detach().clone() for key, value in model.state_dict().items()}
    gradients_before = [
        None if parameter.grad is None else parameter.grad.detach().clone()
        for parameter in model.parameters()
    ]
    optimizer_before = copy.deepcopy(optimizer.state_dict())
    python_rng_before = random.getstate()
    torch_rng_before = torch.get_rng_state().clone()

    result = evaluate(model, rows[:3])
    assert result["tokens"] == 3 * 32
    assert model.training is True
    _assert_nested_tensors_equal(model.state_dict(), model_before)
    _assert_nested_tensors_equal(
        [parameter.grad for parameter in model.parameters()], gradients_before
    )
    _assert_nested_tensors_equal(optimizer.state_dict(), optimizer_before)
    assert random.getstate() == python_rng_before
    assert torch.equal(torch.get_rng_state(), torch_rng_before)

    def fail_forward(_tokens: torch.Tensor) -> torch.Tensor:
        raise RuntimeError("injected evaluation failure")

    monkeypatch.setattr(model, "forward", fail_forward)
    with pytest.raises(RuntimeError, match="injected evaluation failure"):
        evaluate(model, rows[:3])
    assert model.training is True
    _assert_nested_tensors_equal(model.state_dict(), model_before)
    _assert_nested_tensors_equal(
        [parameter.grad for parameter in model.parameters()], gradients_before
    )
    _assert_nested_tensors_equal(optimizer.state_dict(), optimizer_before)
    assert random.getstate() == python_rng_before
    assert torch.equal(torch.get_rng_state(), torch_rng_before)
