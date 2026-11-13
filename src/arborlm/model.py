"""The E0 dense causal reference model."""

import math
from typing import cast

import torch
from torch import Tensor, nn
from torch.nn import functional as F

PARAMETERS = 18_688
CONTEXT = 32
VOCAB = 16
WIDTH = 32


class Block(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.attn_norm = nn.LayerNorm(WIDTH, eps=1e-5)
        self.qkv = _Linear(WIDTH, 96)
        self.attn_out = _Linear(WIDTH, WIDTH)
        self.ffn_norm = nn.LayerNorm(WIDTH, eps=1e-5)
        self.ffn_in = _Linear(WIDTH, 64)
        self.ffn_out = _Linear(64, WIDTH)

    def forward(self, h: Tensor, mask: Tensor) -> Tensor:
        b, t, _ = h.shape
        q, k, v = (
            self.qkv(self.attn_norm(h)).reshape(b, t, 3, 4, 8).permute(2, 0, 3, 1, 4).unbind(0)
        )
        scores = (q @ k.transpose(-2, -1)) / math.sqrt(8)
        attended = (scores + mask).softmax(dim=-1) @ v
        h = h + self.attn_out(attended.transpose(1, 2).reshape(b, t, WIDTH))
        return h + cast(
            Tensor, self.ffn_out(F.gelu(self.ffn_in(self.ffn_norm(h)), approximate="none"))
        )


class DenseBaseline(nn.Module):
    mask: Tensor

    def __init__(self) -> None:
        super().__init__()
        # Skip PyTorch's default parameter initializers. Each matrix is sampled exactly once.
        self.token = _Embedding(VOCAB, WIDTH)
        self.position = _Embedding(CONTEXT, WIDTH)
        self.blocks = nn.ModuleList([Block(), Block()])
        self.final_norm = nn.LayerNorm(WIDTH, eps=1e-5)
        mask = torch.full((CONTEXT, CONTEXT), -torch.inf, dtype=torch.float32).triu(1)
        self.register_buffer("mask", mask, persistent=False)

    def forward(self, tokens: Tensor) -> Tensor:
        if (
            tokens.ndim != 2
            or tokens.shape[0] < 1
            or not 1 <= tokens.shape[1] <= CONTEXT
            or tokens.dtype != torch.int64
            or tokens.device.type != "cpu"
        ):
            raise ValueError("expected nonempty CPU int64 [B,T] with 1 <= T <= 32")
        if bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("token IDs must be in [0, 15]")
        t = tokens.shape[1]
        h = self.token(tokens) + self.position(torch.arange(t, device="cpu"))
        for block in self.blocks:
            h = block(h, self.mask[:t, :t])
        return F.linear(self.final_norm(h), self.token.weight)


class _Embedding(nn.Embedding):
    def reset_parameters(self) -> None:
        nn.init.normal_(self.weight, mean=0.0, std=0.02)


class _Linear(nn.Linear):
    def reset_parameters(self) -> None:
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        if self.bias is not None:
            nn.init.zeros_(self.bias)


def active_parameters(sequence_length: int) -> int:
    if not 1 <= sequence_length <= CONTEXT:
        raise ValueError("sequence length must be in [1, 32]")
    return PARAMETERS - (CONTEXT - sequence_length) * WIDTH
