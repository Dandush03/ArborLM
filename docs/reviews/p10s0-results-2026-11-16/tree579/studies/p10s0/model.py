# ruff: noqa: E501
"""P10S0 models. The arms A0, A1, A2, A5-D, A6 and A7 are ``studies.p9ii``'s, unedited (``studies.p9ii.model.build_model``); this module adds only WX, the full-context
query (ADR-0020 section 5.2), the seeded derangement of the read swap (section 8.1) and the read-swap helpers.

WX. For an answer site at position t let h~_j = h_j for j >= 0 and the zero vector for j < 0 (h = the frozen block-0 output, width 32). Then z = W_X [h~_{t-63}; ...; h~_t],
W_X in R^{16 x 2,048} (drawn by W7's initializer at fan-in 2,048: ``_matrix(seed + 3000, 16, 2048)``), q = z / |z|. W7 is the special case in which every column of W_X but the last 224
is zero. WX(X) is trained exactly as arm X: it is built as arm X's model with the query projection replaced, so the keys, values, output projection, gate, losses and schedule
are X's. WX is told nothing about where a record starts; the memory still reads only at the answer positions 8r + 6 (section 5.2: no label says the interface finds where to read).
"""

from typing import TYPE_CHECKING, cast

import torch
from torch import nn
from torch.nn import functional as F

from arborlm.pilot_model import _matrix
from studies.p9ii import core as p9iicore
from studies.p9ii import model as p9iimodel
from studies.p9ii.model import IIMemory, P9IIModel

from . import core

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

SITES = p9iimodel.SITES
FULL_OFFSETS = torch.arange(-(core.FULL_WINDOW - 1), 1, dtype=torch.int64)  # -63 .. 0


class WXMemory(IIMemory):
    """``IIMemory`` of the base arm (W7's memory) whose query projection ``wq`` is 16 x 2,048 over the whole causal context (zero-padded before position 0)."""

    def __init__(self, base: str, slots: int, seed: int) -> None:
        super().__init__(base, slots, seed)
        self.wq = nn.Parameter(_matrix(seed + 3000, core.KEY_WIDTH, core.WX_FEATURES))

    @staticmethod
    def full_window(x: "Tensor", positions: "Tensor") -> "Tensor":
        """``[B, P, 64 * 32]`` features ``[h~_{t-63}; ...; h~_t]`` (oldest first), zero where t - 63 + i < 0."""
        index = positions[:, None] + FULL_OFFSETS[None, :]  # [P, 64]
        valid = (index >= 0).to(x.dtype)
        gathered = x[:, index.clamp(min=0)]  # [B, P, 64, 32]
        gathered = gathered * valid[None, :, :, None]
        return gathered.reshape(x.shape[0], positions.numel(), -1)

    def _features(self, x: "Tensor", positions: "Tensor") -> "Tensor":
        return self.full_window(x, positions)

    def window_z(self, h_pre: "Tensor", positions: "Tensor") -> "Tensor":
        return F.linear(self.full_window(h_pre, positions), self.wq)


class WXModel(P9IIModel):
    """The model of base arm X with the WX query: ``P9IIModel`` with its addition replaced by ``WXMemory``. Every other member is the base arm's."""

    def __init__(self, arm: str, slots: int, seed: int, backbone: "Backbone", *, r1_seed: int | None = None) -> None:
        if not core.is_wx(arm) or core.base_arm(arm) not in p9iicore.LEARNED_ARMS:
            raise ValueError(f"not a WX arm: {arm!r}")
        super().__init__(core.base_arm(arm), slots, seed, backbone, r1_seed=r1_seed)
        self.addition = WXMemory(core.base_arm(arm), slots, seed)
        self.arm = arm
        for p in self.backbone.parameters():
            p.requires_grad_(False)


def build_model(arm: str, slots: int, seed: int, backbone: "Backbone", *, r1_seed: int | None = None, seed_rng: bool = True) -> P9IIModel:
    """Model of an S0 arm at ``slots``: ``studies.p9ii.model.build_model`` for A0, A1, A2, A5-D, A6 and A7; WX for ``WX-A5-D`` and ``WX-A1``."""
    if arm not in core.ARMS:
        raise ValueError(f"unknown P10S0 arm {arm!r}")
    if not core.is_wx(arm):
        return p9iimodel.build_model(arm, slots, seed, backbone, r1_seed=r1_seed, seed_rng=seed_rng)
    if seed_rng:
        import random

        random.seed(seed)
        torch.default_generator.manual_seed(seed)
    return WXModel(arm, slots, seed, backbone, r1_seed=r1_seed)


def w7_equivalent_projection(w7: "Tensor") -> "Tensor":
    """The 16 x 2,048 matrix that is zero outside its last 224 columns and equals ``w7`` (16 x 224) there (G4: it must give W7's query)."""
    out = torch.zeros(core.KEY_WIDTH, core.WX_FEATURES)
    out[:, -w7.shape[1] :] = w7
    return out


# --- the read swap (section 8.1) ---------------------------------------------------------------------------------------------------
def derangement(answers: "Tensor", seed: int) -> "Tensor":
    """A seeded derangement pi of the facts with ``answer(pi(f)) != answer(f)`` for every f (so no fixed point and no pair with equal answers). Start from a seeded permutation;
    each violating position is swapped, in a fixed order, with the next position that leaves both sides valid. Deterministic in (answers, seed); raises if none exists."""
    n = int(answers.shape[0])
    generator = torch.Generator().manual_seed(seed)
    perm = torch.randperm(n, generator=generator).tolist()
    ans = answers.tolist()

    def bad(i: int) -> bool:
        return bool(perm[i] == i or ans[perm[i]] == ans[i])

    for _ in range(64):
        violating = [i for i in range(n) if bad(i)]
        if not violating:
            break
        for i in violating:
            if not bad(i):
                continue
            for k in range(1, n):
                j = (i + k) % n
                perm[i], perm[j] = perm[j], perm[i]
                if not bad(i) and not bad(j):
                    break
                perm[i], perm[j] = perm[j], perm[i]
            else:
                raise ValueError("no derangement with differing answers exists for these answers")
    out = torch.tensor(perm, dtype=torch.int64)
    if bool((out == torch.arange(n)).any()) or bool((answers[out] == answers).any()):
        raise ValueError("the derangement could not be repaired")
    return out


def swap_reads(table: "Tensor", perm: "Tensor") -> "Tensor":
    """The read vectors with fact f's replaced by fact pi(f)'s: ``table [F, d]`` -> ``table[perm]``. Swapping with pi and then with pi's inverse restores the table."""
    return table[perm]


def inverse(perm: "Tensor") -> "Tensor":
    out = torch.empty_like(perm)
    out[perm] = torch.arange(perm.shape[0], dtype=perm.dtype)
    return out


def memory_arms() -> tuple[str, ...]:
    return tuple(a for a in core.ARMS if a != "A7")


def trainable_query(model: P9IIModel) -> "Tensor":
    return cast("Tensor", model.addition.wq)
