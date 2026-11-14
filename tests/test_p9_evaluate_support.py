# ruff: noqa: E501
"""Shared helpers of the P9 package-I3 tests (evaluate): a tiny study draw, hand-constructed memories
whose truth is known, a fixed-selection fitting routine. Random frozen backbone, tiny sizes and test
seeds (>= 179001) only; nothing registered, no real data, no stage.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import sys
from functools import cache as memoize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch  # noqa: E402
from test_p9_model_support import backbone, cell_of  # noqa: E402
from torch.nn import functional as F  # noqa: E402

from arborlm.p4_model import Backbone  # noqa: E402
from studies.p9 import controls, core, data, evaluate  # noqa: E402
from studies.p9 import model as M  # noqa: E402

SITES = core.ANSWER_SITE_POSITIONS
ALPHABET = torch.tensor(core.ALPHABET, dtype=torch.int64)
SIZES = data.DataSizes(main_trained=128, unseen=32, lane_d_per_set=128)
SEEDS = core.rehearsal_seeds(7)
FACTS = SIZES.main_trained
CARRIER_BASE = (
    2048  # hand-built memories: fact f is stored in slot CARRIER_BASE + f, above every junk slot id
)


def corpus() -> bytes:
    g = torch.Generator().manual_seed(11)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


_DRAW: data.StudyData | None = None


def draw() -> data.StudyData:
    global _DRAW
    if _DRAW is None:
        _DRAW = data.build_study_data(SEEDS, corpus(), sizes=SIZES)
    return _DRAW


def cell(block: str = "A1", **match: object) -> core.Cell:
    """A registered cell, relabelled in nothing, with ``facts`` set to the tiny draw's size."""
    from dataclasses import replace

    return replace(cell_of(block, **match), facts=FACTS)


def lut_for(table: data.FactTable, count: int = FACTS) -> torch.Tensor:
    return data.identifier_lut(table, torch.arange(count))


class ShiftBlock(torch.nn.Module):
    """A stand-in for the frozen upper block: position t sees its own input and the input at t - 1
    (causal). It makes the position before the answer site as influential as the site itself, which the
    random backbone's attention is not (its influence saturates near 4% of the site's), so that a fact
    stored one position early can be fitted and known to be there."""

    def forward(self, h: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        prev = torch.cat([torch.zeros_like(h[:, :1]), h[:, :-1]], dim=1)
        return h + prev


class ShiftBackbone(torch.nn.Module):
    mask: torch.Tensor

    def __init__(self) -> None:
        super().__init__()
        base = backbone()
        self.token, self.position = base.token, base.position
        self.blocks = torch.nn.ModuleList([base.blocks[0], ShiftBlock()])
        self.final_norm = base.final_norm
        self.register_buffer("mask", base.mask.clone(), persistent=False)


def make_model(
    c: core.Cell,
    *,
    lut: torch.Tensor | None = None,
    slots: int | None = None,
    bb: torch.nn.Module | None = None,
) -> M.P9Model:
    use: Backbone = bb if bb is not None else backbone()  # type: ignore[assignment]
    if slots is not None and slots != c.slots:
        spec = M.AdditionSpec(c.arch, slots, c.key_width, c.rung, 0, 0)
        return M.build_model_from_spec(spec, 179001, use, fact_lut=lut)
    return M.build_model(c, use, fact_lut=lut, seed_rng=False)


def sigma_loss(logits: torch.Tensor, answer: torch.Tensor) -> torch.Tensor:
    """Cross-entropy over the 32 alphabet logits at the answer sites (the fit target of these tests)."""
    return F.cross_entropy(logits[:, list(SITES)][..., ALPHABET].reshape(-1, 32), answer)


def fit_fixed_selection(
    model: M.P9Model,
    cache: evaluate.ReadCache,
    *,
    steps: int = 250,
    lr: float = 0.05,
    frozen_rows: torch.Tensor | None = None,
) -> float:
    """Train the addition's parameters (selection and weights fixed as in ``cache``) to answer every
    context of the cache; ``frozen_rows`` value rows are reset to zero after each step. Returns the
    final alphabet loss. Test-only 'training' of a tiny memory so that the truth is known."""
    sel = cache.selection
    params = [p for p in model.addition.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    answer = cache.stream.answer_targets().reshape(-1)
    loss = torch.zeros(())
    for _ in range(steps):
        delta = model.memory_delta(cache.h_pre, sel)
        loss = sigma_loss(model.finish(cache.h_pre, delta), answer)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if frozen_rows is not None:
            with torch.no_grad():
                model.addition.values[frozen_rows] = 0.0  # type: ignore[index]
    return float(loss.detach())


def refresh(model: M.P9Model, cache: evaluate.ReadCache) -> None:
    """Recompute the cached answer-site logits after the cache's selection or the model changed."""
    cache.logits_answer = evaluate.logits_with(model, cache)
    cache._upper = None


@memoize
def r2_fixture(steps: int = 500) -> tuple[M.P9Model, evaluate.ReadCache, core.Cell]:
    """R2 memory (one dedicated slot per trained fact, weight 1) fitted on the tiny panel A."""
    c = cell("A5", rung="R2", slots=4096, seed=1701)
    d = draw()
    model = make_model(c, lut=lut_for(d.facts))
    stream = d.streams["panel_a"]
    cache = evaluate.build_cache(model, stream)
    fit_fixed_selection(model, cache, steps=steps)
    cache = evaluate.build_cache(model, stream)
    return model, cache, c


def trained_mask(cache: evaluate.ReadCache) -> torch.Tensor:
    return cache.stream.fact_ids.reshape(-1) < FACTS


@memoize
def hand_cache(
    kind: str, steps: int = 800, lr: float = 0.3
) -> tuple[M.P9Model, evaluate.ReadCache, core.Cell]:
    """A memory with a hand-written selection (fact ``f`` has the dedicated carrier slot ``CARRIER_BASE + f``, a higher id than every junk slot; every
    other read position reads eight unique junk slots whose values are zero) fitted on tiny panel A.

    * ``early``: R0 (reads everywhere) on the stand-in backbone; fact ``f`` is read at the position
      BEFORE its answer site (carrier weight about 0.74), the answer site itself reads junk only.
    * ``diffuse``: R0a (reads at the answer sites); the carrier is one of eight slots with weights
      near 1/8 (score 0.3 above the others).
    * ``dedicated_site``: as ``diffuse`` with the carrier alone at the answer site (score 6, weight 0.98).
    """
    d = draw()
    stream = d.streams["panel_a"]
    n_slots = 4096
    if kind == "early":
        c = cell("A1", arch="flat", slots=4096, seed=1701)
        model = make_model(c, bb=ShiftBackbone())
    else:
        c = cell("A5b", slots=16384, seed=1701)
        model = make_model(c, slots=n_slots)
    cache = evaluate.build_cache(model, stream)
    sel = cache.selection
    assert sel is not None
    pos = sel.positions.tolist()
    n_ctx, n_pos = sel.selected.shape[:2]
    junk = (torch.arange(n_ctx * n_pos * 8).reshape(n_ctx, n_pos, 8) % (CARRIER_BASE - 8)).to(
        torch.int64
    )
    selected, scores = junk.clone(), torch.zeros(n_ctx, n_pos, 8)
    for ci in range(n_ctx):
        for r in range(8):
            f = int(stream.fact_ids[ci, r])
            if f >= FACTS:
                continue
            site = pos.index(8 * r + 6)
            if kind == "early":
                at, score = pos.index(8 * r + 5), 3.0
            else:
                at, score = site, 0.3 if kind == "diffuse" else 6.0
            selected[ci, at, 0] = CARRIER_BASE + f
            scores[ci, at, 0] = score
    sel.selected, sel.scores = selected, scores
    refresh(model, cache)
    frozen = torch.arange(0, CARRIER_BASE)
    with torch.no_grad():
        model.addition.values[frozen] = 0.0  # type: ignore[index]
    fit_fixed_selection(model, cache, steps=steps, lr=lr, frozen_rows=frozen)
    refresh(model, cache)
    return model, cache, c


def nomem_of(model: M.P9Model, stream: data.Stream) -> core.AnswerScores:
    return controls.evaluate_no_memory(model.backbone, draw().facts, stream)  # type: ignore[arg-type]
