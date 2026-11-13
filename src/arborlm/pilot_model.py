"""Registered RAM-only pilot models and stable sparse lookups."""

import math
from dataclasses import dataclass

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from .model import Block, _Embedding
from .pilot_config import SEEDS, VARIANTS

COUNTS = dict(zip(VARIANTS, (27392, 225512, 225537, 161025, 225537, 225793), strict=True))
SLOTS, BRANCHES, PER_BRANCH = 4096, 16, 256
CONTEXT, VOCAB, WIDTH = 64, 256, 32
TEMP, EPS, TOP, PK_GAP = 0.2, 1e-8, 8, 1e-5


def stable_top(scores: Tensor, count: int, ids: Tensor | None = None) -> tuple[Tensor, Tensor]:
    """Return exact top-k, using the ID only as a secondary key."""
    # For ascending-ID input, topk plus a boundary check avoids sorting the whole table.
    if ids is None:
        if scores.shape[-1] > count:
            with torch.no_grad():
                top, chosen = scores.topk(count + 1, sorted=True)
                safe = (top[..., :-1] > top[..., 1:]).all(dim=-1)
                indices = chosen[..., :count].contiguous()
                if not bool(safe.all()):
                    indices[~safe] = scores[~safe].argsort(dim=-1, descending=True, stable=True)[
                        ..., :count
                    ]
            return scores.gather(-1, indices), indices
        indices = scores.argsort(dim=-1, descending=True, stable=True)[..., :count]
        return scores.gather(-1, indices), indices
    by_id = ids.argsort(dim=-1)
    scores, ids = scores.gather(-1, by_id), ids.gather(-1, by_id)
    selected, order = stable_top(scores, count)
    return selected, ids.gather(-1, order)


def product_candidates(left: Tensor, right: Tensor) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    """Return selected scores/IDs, candidate IDs, and mask of exhaustive queries."""
    lv, li = stable_top(left, TOP + 1)
    rv, ri = stable_top(right, TOP + 1)
    fallback = ((lv[:, 7] - lv[:, 8]) <= PK_GAP) | ((rv[:, 7] - rv[:, 8]) <= PK_GAP)
    ids = (li[:, :TOP, None] * 64 + ri[:, None, :TOP]).flatten(1)
    if not bool(fallback.any()):
        scores = (lv[:, :TOP, None] + rv[:, None, :TOP]).flatten(1) / (math.sqrt(2) * TEMP)
        selected_scores, selected = stable_top(scores, TOP, ids)
        return selected_scores, selected, ids, fallback
    selected_scores = left.new_empty((left.shape[0], TOP))
    selected = li.new_empty((left.shape[0], TOP))
    if not bool(fallback.all()):
        scores = (lv[~fallback, :TOP, None] + rv[~fallback, None, :TOP]).flatten(1)
        selected_scores[~fallback], selected[~fallback] = stable_top(
            scores / (math.sqrt(2) * TEMP), TOP, ids[~fallback]
        )
    all_scores = (left[fallback, :, None] + right[fallback, None, :]).flatten(1)
    selected_scores[fallback], selected[fallback] = stable_top(
        all_scores / (math.sqrt(2) * TEMP), TOP
    )
    return selected_scores, selected, ids, fallback


def tree_candidates(
    q: Tensor,
    keys: Tensor,
    routes: Tensor,
    *,
    visit: int = 2,
    keys_per_branch: int = PER_BRANCH,
    use_prior: bool = True,
) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    _, branch_ids = stable_top(routes, visit)
    indices = (
        branch_ids[..., None] * keys_per_branch + torch.arange(keys_per_branch, device="cpu")
    ).flatten(1)
    local = F.normalize(keys[indices], dim=-1, eps=EPS)
    scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
    if use_prior:
        prior = routes.log_softmax(-1).gather(-1, branch_ids)
        scores = scores + prior.repeat_interleave(keys_per_branch, dim=-1)
    values, selected = stable_top(scores, TOP, indices)
    return values, selected, indices, branch_ids


@dataclass
class Lookup:
    selected: Tensor
    candidate_ids: Tensor | None
    exhaustive_queries: Tensor | None = None
    branch_ids: Tensor | None = None
    route_scores: Tensor | None = None


def _matrix(seed: int, *shape: int) -> Tensor:
    generator = torch.Generator(device="cpu").manual_seed(seed)
    return torch.empty(shape, device="cpu", dtype=torch.float32).normal_(
        0, 0.02, generator=generator
    )


class Memory(nn.Module):
    router: Tensor

    def __init__(self, variant: str, seed: int) -> None:
        super().__init__()
        self.variant = variant
        if variant == "product_key":
            key_generator = torch.Generator(device="cpu").manual_seed(seed + 1000)
            self.left = nn.Parameter(
                torch.empty((64, 8), dtype=torch.float32).normal_(0, 0.02, generator=key_generator)
            )
            self.right = nn.Parameter(
                torch.empty((64, 8), dtype=torch.float32).normal_(0, 0.02, generator=key_generator)
            )
        else:
            self.keys = nn.Parameter(_matrix(seed + 1000, SLOTS, 16))
        self.values = nn.Parameter(_matrix(seed + 2000, SLOTS, 32))
        self.wq = nn.Parameter(_matrix(seed + 3000, 16, 32))
        self.wo = nn.Parameter(_matrix(seed + 4000, 32, 32))
        self.gate = nn.Parameter(torch.tensor(-2.0, dtype=torch.float32))
        if variant in ("fixed_tree", "learned_tree"):
            router = _matrix(seed + 5000, BRANCHES, 16)
            if variant == "fixed_tree":
                self.register_buffer("router", router)
            else:
                self.router = nn.Parameter(router)

    def lookup(self, q: Tensor) -> tuple[Tensor, Lookup]:
        if self.variant == "flat":
            scores = (q @ F.normalize(self.keys, dim=-1, eps=EPS).T) / TEMP
            weights, selected = stable_top(scores, TOP)
            return weights, Lookup(selected, None)
        if self.variant == "product_key":
            left = q[:, :8] @ F.normalize(self.left, dim=-1, eps=EPS).T
            right = q[:, 8:] @ F.normalize(self.right, dim=-1, eps=EPS).T
            weights, selected, candidates, fallback = product_candidates(left, right)
            return weights, Lookup(selected, candidates, fallback)
        routes = (q @ F.normalize(self.router, dim=-1, eps=EPS).T) / TEMP
        weights, selected, candidates, branches = tree_candidates(q, self.keys, routes)
        return weights, Lookup(selected, candidates, branch_ids=branches, route_scores=routes)

    def forward(self, h: Tensor) -> tuple[Tensor, Lookup]:
        q = F.normalize(F.linear(h, self.wq), dim=-1, eps=EPS).reshape(-1, 16)
        scores, lookup = self.lookup(q)
        combined = (scores.softmax(-1)[..., None] * self.values[lookup.selected]).sum(dim=-2)
        return h + self.gate.sigmoid() * F.linear(combined.reshape(h.shape), self.wo), lookup


class PilotModel(nn.Module):
    mask: Tensor

    def __init__(self, variant: str, seed: int) -> None:
        super().__init__()
        if variant not in VARIANTS or seed not in SEEDS:
            raise ValueError("unknown registered pilot variant or seed")
        self.variant = variant
        self.seed = seed
        # Global training RNG is set by the caller; backbone initialization cannot perturb it.
        with torch.random.fork_rng(devices=[]):
            torch.default_generator.manual_seed(seed)
            self.token = _Embedding(VOCAB, WIDTH)
            self.position = _Embedding(CONTEXT, WIDTH)
            ffn_width = 1588 if variant == "dense_parameter_matched" else 64
            self.blocks = nn.ModuleList([Block(ffn_width), Block(ffn_width)])
            self.final_norm = nn.LayerNorm(WIDTH, eps=1e-5)
        self.register_buffer(
            "mask",
            torch.full((CONTEXT, CONTEXT), -torch.inf, dtype=torch.float32).triu(1),
            persistent=False,
        )
        self.memory = Memory(variant, seed) if variant in VARIANTS[2:] else None

    def forward(self, tokens: Tensor) -> tuple[Tensor, Lookup | None]:
        if (
            tokens.ndim != 2
            or tokens.shape[0] == 0
            or not 1 <= tokens.shape[1] <= CONTEXT
            or tokens.dtype != torch.int64
            or tokens.device.type != "cpu"
        ):
            raise ValueError("expected nonempty CPU int64 [B,T] with 1 <= T <= 64")
        if bool(((tokens < 0) | (tokens >= VOCAB)).any()):
            raise ValueError("expected byte token IDs")
        t = tokens.shape[1]
        h = self.token(tokens) + self.position(torch.arange(t, device="cpu"))
        h = self.blocks[0](h, self.mask[:t, :t])
        lookup = None
        if self.memory is not None:
            h, lookup = self.memory(h)
        h = self.blocks[1](h, self.mask[:t, :t])
        return F.linear(self.final_norm(h), self.token.weight), lookup
