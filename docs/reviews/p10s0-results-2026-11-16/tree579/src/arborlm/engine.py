"""Deterministic CPU execution, loss reduction and evaluation."""

import math
import random
from collections.abc import Iterable

import torch
from torch import Tensor, nn
from torch.nn import functional as F
from torch.optim import AdamW

from .data import next_token_batch

BATCH_SIZE = 8
CONTEXT = 32
STEPS = 32
CHECKPOINT_STEPS = (16, 32)


def configure_cpu() -> None:
    torch.set_default_device("cpu")
    torch.set_default_dtype(torch.float32)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    random.seed(42)
    torch.manual_seed(42)


def optimizer_for(model: nn.Module) -> AdamW:
    return AdamW(
        model.parameters(),
        lr=0.003,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=0,
        amsgrad=False,
        foreach=False,
        fused=False,
    )


def token_loss(logits: Tensor, targets: Tensor, *, reduction: str = "mean") -> Tensor:
    return F.cross_entropy(logits.reshape(-1, 16), targets.reshape(-1), reduction=reduction)


def aggregate_evaluation(
    batches: Iterable[tuple[Tensor, Tensor]],
) -> dict[str, float | int | str | None]:
    total_nll = 0.0
    total_tokens = 0
    for logits, targets in batches:
        total_nll += token_loss(logits, targets, reduction="sum").item()
        total_tokens += targets.numel()
    if total_tokens == 0:
        raise ValueError("no evaluation targets")
    nll = total_nll / total_tokens
    if not math.isfinite(nll):
        raise ValueError("non-finite evaluation NLL")
    try:
        ppl: float | None = math.exp(nll)
        reason = None
    except OverflowError:
        ppl = None
        reason = "exp(NLL) exceeds floating-point range"
    return {"nll": nll, "perplexity": ppl, "perplexity_null_reason": reason, "tokens": total_tokens}


def evaluate(model: nn.Module, rows: list[list[int]]) -> dict[str, float | int | str | None]:
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():

            def batches() -> Iterable[tuple[Tensor, Tensor]]:
                for start in range(0, len(rows), BATCH_SIZE):
                    x, y = next_token_batch(rows[start : start + BATCH_SIZE])
                    yield model(x), y

            return aggregate_evaluation(batches())
    finally:
        model.train(was_training)


def train_step(model: nn.Module, optimizer: AdamW, rows: list[list[int]]) -> tuple[float, float]:
    x, y = next_token_batch(rows)
    optimizer.zero_grad(set_to_none=True)
    loss = token_loss(model(x), y)
    if not bool(torch.isfinite(loss)):
        raise ValueError("non-finite training loss")
    loss.backward()  # type: ignore[no-untyped-call]  # PyTorch stub
    grad = nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    return loss.item(), grad.item()
