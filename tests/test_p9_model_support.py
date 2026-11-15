# ruff: noqa: E501
"""Shared helpers of the P9 package-I2 tests (model, objective, train): a random frozen backbone, tiny
fact tables and token tensors in the contract's position convention, a fake training stream, cell
construction. No real data and no registered seeds are used; the fake data object carries a rehearsal
seed set and model initialization uses seeds at or above 179001.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

from arborlm.p2_config import CONTROL as P2_CONTROL  # noqa: E402
from arborlm.p2_config import Cell as P2Cell  # noqa: E402
from arborlm.p2_model import FollowupModel  # noqa: E402
from arborlm.p4_model import Backbone  # noqa: E402
from studies.p9 import core  # noqa: E402

TEST_SEED = 179001  # rehearsal namespace: never a registered seed
SITES = core.ANSWER_SITE_POSITIONS
NON_SITES = tuple(p for p in range(63) if p not in SITES)


def make_backbone() -> Backbone:
    """A random (seeded) frozen P4-shaped backbone: the structure is the real one, the weights are not."""
    return Backbone(FollowupModel(P2Cell(101, 201, 301, P2_CONTROL)))


_BACKBONE: Backbone | None = None


def backbone() -> Backbone:
    global _BACKBONE
    if _BACKBONE is None:
        _BACKBONE = make_backbone()
    return _BACKBONE


class Facts:
    """``count`` facts with unique 5-symbol identifiers (four symbols plus their sum modulo 32) and
    random answers, deterministic in ``seed``."""

    def __init__(self, count: int, seed: int = TEST_SEED) -> None:
        g = torch.Generator().manual_seed(seed)
        codes = torch.randperm(32**4, generator=g)[:count]
        self.codes = codes
        syms = torch.stack([(codes // 32**i) % 32 for i in range(4)], dim=1)
        self.ident = torch.cat([syms, (syms.sum(1, keepdim=True) % 32)], dim=1)
        self.answer = torch.randint(0, 32, (count,), generator=g)
        self.count = count

    def lut(self) -> torch.Tensor:
        lut = torch.full((32**4,), -1, dtype=torch.int64)
        lut[self.codes] = torch.arange(self.count)
        return lut

    def context(
        self, fact_ids: list[int], separator: int = 0x20, binding: int = 0x2C
    ) -> torch.Tensor:
        """One 64-byte context of 8 records: separator, 5 identifier bytes, binding, answer."""
        out = torch.zeros(64, dtype=torch.int64)
        for r, f in enumerate(fact_ids):
            out[8 * r] = separator
            out[8 * r + 1 : 8 * r + 6] = 0x40 + self.ident[f]
            out[8 * r + 6] = binding
            out[8 * r + 7] = 0x40 + self.answer[f]
        return out

    def batch(self, update: int, contexts: int = 16, offset: int = 0) -> torch.Tensor:
        rows = []
        for c in range(contexts):
            start = ((update - 1) * contexts + c) * 8 + offset
            rows.append(self.context([(start + k) % self.count for k in range(8)]))
        return torch.stack(rows)


class FakeStream:
    """Duck-typed ``data.TrainingStream``: ``batch(update)`` is a pure function of the 1-based update."""

    def __init__(self, facts: Facts, replay: Facts | None = None) -> None:
        self.facts_obj = facts
        self.replay = replay
        self.facts = torch.arange(facts.count)

    def batch(self, update: int) -> Any:
        tokens = self.facts_obj.batch(update)
        replay = None if self.replay is None else self.replay.batch(update)
        return SimpleNamespace(
            tokens=tokens,
            fact_ids=None,
            cluster=None,
            template=None,
            replay_tokens=replay,
            replay_fact_ids=None,
        )

    def exposures(self, updates: int) -> torch.Tensor:
        counts = torch.zeros(self.facts_obj.count, dtype=torch.int64)
        for u in range(1, updates + 1):
            start = (u - 1) * 128
            counts[(start + torch.arange(128)) % self.facts_obj.count] += 1
        return counts


def fake_data() -> Any:
    return SimpleNamespace(seeds=core.rehearsal_seeds(7))


def cell_of(block: str, **match: Any) -> core.Cell:
    """The first registered cell of ``block`` whose fields equal ``match``."""
    for c in core.cells_of_block(block):
        if all(getattr(c, k) == v for k, v in match.items()):
            return c
    raise LookupError((block, match))


def variant(cell: core.Cell, **changes: Any) -> core.Cell:
    """A registered cell with some fields changed (all values still registered ones)."""
    return replace(cell, **changes)


def base_cell(**changes: Any) -> core.Cell:
    """Flat R0 key-16 4,096-slot AdamW cell (A1, seed 1701) with fields changed."""
    return variant(cell_of("A1", arch="flat", slots=4096, seed=1701, parent=(101, 301)), **changes)
