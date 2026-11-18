# ruff: noqa: E501
"""Helpers of the P10IR tests: tiny synthetic memories, models, data and registries. Seeds are the registry's unit-test range 938001-938999 only (``core.test_seeds``); the backbone is a random
synthetic one; no registered seed, no checkpoint of the experiments directory and no sealed value is touched. Self-check only."""

import functools
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

from studies.p9 import controls  # noqa: E402
from studies.p9 import core as p9core  # noqa: E402
from studies.p9 import data as d  # noqa: E402
from studies.p9.model import AdditionSpec  # noqa: E402
from studies.p10ir import core  # noqa: E402
from studies.p10s1 import model as s1model  # noqa: E402

CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
FACTS = 128


@functools.cache
def data(k: int = 0, trained: int = 512) -> d.StudyData:
    return d.build_study_data(core.test_seeds(k), CORPUS, sizes=d.DataSizes(main_trained=trained, unseen=64, lane_d_per_set=128))


@functools.cache
def backbone() -> Any:
    return controls.synthetic_backbone(101, 301)


def tree_memory(branches: int, seed: int, *, kw: int = 16) -> s1model.S1Memory:
    """A random tree memory of ``branches`` branches of 256 slots (keys and router random normal, so that every branch matters)."""
    mem = s1model.S1Memory(AdditionSpec("learned_tree", 256 * branches, kw, "R1", branches, 0), seed)
    gen = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        mem.keys.copy_(torch.randn(mem.keys.shape, generator=gen))
        mem.router.copy_(torch.randn(mem.router.shape, generator=gen))
    return mem


def flat_memory(slots: int, seed: int, *, kw: int = 16) -> s1model.S1Memory:
    mem = s1model.S1Memory(AdditionSpec("flat", slots, kw, "R1", 0, 0), seed)
    gen = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        mem.keys.copy_(torch.randn(mem.keys.shape, generator=gen))
    return mem


def unit_queries(n: int, seed: int, kw: int = 16) -> torch.Tensor:
    gen = torch.Generator().manual_seed(seed)
    return torch.nn.functional.normalize(torch.randn(n, kw, generator=gen), dim=-1)


def model(arm: str, slots: int, k: int = 0, init_seed: int | None = None) -> s1model.P10S1Model:
    seeds = core.test_seeds(k)
    init = core.load_config()["seeds"]["test_init"][0] if init_seed is None else init_seed
    return s1model.build_model(arm, slots, init, backbone(), r1_seed=seeds.r1_codes, seed_rng=False)
