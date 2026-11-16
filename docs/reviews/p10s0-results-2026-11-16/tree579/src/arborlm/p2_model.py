"""P2 factorized construction using the frozen P1 forward and retrieval."""

import torch
from torch import Tensor, nn

from .model import Block, _Embedding
from .p2_config import CONDITIONS, CONTROL, Cell
from .pilot_model import BRANCHES, CONTEXT, PER_BRANCH, SLOTS, VOCAB, WIDTH, Memory, PilotModel


class FollowupModel(nn.Module):
    mask: Tensor
    forward = PilotModel.forward

    def __init__(self, cell: Cell) -> None:
        # Do not expand P1's accepted seed set. Construct the same backbone in the same order.
        nn.Module.__init__(self)
        self.cell = cell
        self.variant = "learned_tree"
        self.seed = cell.backbone
        with torch.random.fork_rng(devices=[]):
            torch.default_generator.manual_seed(cell.backbone)
            self.token = _Embedding(VOCAB, WIDTH)
            self.position = _Embedding(CONTEXT, WIDTH)
            self.blocks = nn.ModuleList([Block(64), Block(64)])
            self.final_norm = nn.LayerNorm(WIDTH, eps=1e-5)
        self.register_buffer(
            "mask",
            torch.full((CONTEXT, CONTEXT), -torch.inf, dtype=torch.float32).triu(1),
            persistent=False,
        )
        self.memory_state = Memory("learned_tree", cell.memory)
        self.bypass = cell.condition == CONTROL
        if self.bypass:
            self.memory_state.requires_grad_(False)

    @property
    def memory(self) -> Memory | None:
        # P1 forward and evaluation see None for bypass, while all tensors stay registered.
        return None if self.bypass else self.memory_state


def memory_permutation(cell: Cell, condition: str) -> tuple[Tensor, int]:
    generator = torch.Generator(device="cpu")
    if condition == "values_permuted":
        seed = 20000 + cell.index
        return torch.randperm(SLOTS, generator=generator.manual_seed(seed), device="cpu"), seed
    if condition == "joint_within_branch":
        seed = 30000 + cell.index
        generator.manual_seed(seed)
        return torch.cat(
            [
                branch * PER_BRANCH + torch.randperm(PER_BRANCH, generator=generator, device="cpu")
                for branch in range(BRANCHES)
            ]
        ), seed
    raise ValueError("condition has no permutation")


def intervene(model: FollowupModel, condition: str) -> tuple[Tensor, int] | None:
    if condition not in CONDITIONS or (model.cell.condition == CONTROL and condition != "enabled"):
        raise ValueError("unregistered P2 intervention")
    if condition == "enabled":
        return None
    if condition == "disabled":
        model.bypass = True
        return None
    ids, seed = memory_permutation(model.cell, condition)
    memory = model.memory_state
    with torch.no_grad():
        if condition == "joint_within_branch":
            memory.keys.copy_(memory.keys[ids])
        memory.values.copy_(memory.values[ids])
    return ids, seed
