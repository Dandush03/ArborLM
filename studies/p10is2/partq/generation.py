# ruff: noqa: E501
"""Q_check by three stopping rules, and generate-until-met in whole blocks (ADR-0025 section 4.3).

Q_check (rules 1-3): the filter setting is fixed from Q_fit before the first block is drawn; blocks are taken in the reserve's seeded order, never skipped or reordered, also across a pause; after each
block ONLY the filter is applied and accepted items are counted; drawing stops at the first block boundary with at least 150 accepted items and the stop block index is recorded; NO reference is read and no
chrF is computed for any Q_check item before that record exists; precision is then computed once, in one call, over every accepted item of every block drawn. Q_check is never extended afterwards.

Generation (rules 4-5): each teacher works only on its own sources, in a seeded order (seed 250905), in blocks of 20,000 sources; a capability stops at the first block boundary with at least 24,000 accepted
sources (after the evaluation-equal drop) or when its pool ends. Batches are stored one by one (``batches.run_stream``), so a paused stage resumes at the next batch and completed blocks are not regenerated.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from arborlm.io import canonical_json, read_json, write_json
from studies.p10s2.data import Item, TrainItem
from studies.p10s2.filtering import FilterSetting, Output, accepts
from studies.p10s2.text import normalize

from ..common import core
from . import qualify
from .batches import StoredBatch, run_stream
from .teacher import BatchTeacher


class QCheckViolation(RuntimeError):
    """A reference was requested or a chrF computed for a Q_check item before the stop was recorded (rule 3)."""


def source_orders(n_a: int, n_b: int, seed: int, allowed: frozenset[int] | set[int]) -> dict[str, list[int]]:
    """The seeded order of each capability's own sources (seed 250905): ONE generator, capability A's permutation first, then B's; every caller draws both so that a worker that runs only B sees B's order."""
    g = core.seeded_generator(seed, "source block order", allowed)
    return {"A": torch.randperm(n_a, generator=g).tolist(), "B": torch.randperm(n_b, generator=g).tolist()}


def outputs_of(batches: Sequence[StoredBatch], source_of_key: Mapping[str, str]) -> list[Output]:
    out: list[Output] = []
    for b in batches:
        for k, text, sc in zip(b.keys, b.texts, b.scores, strict=True):
            out.append(Output(source_of_key[k], text, sc))
    return out


# --- Q_check ---------------------------------------------------------------------------------------------------------------------------------
@dataclass
class CheckCount:
    """The state after the counting phase: nothing here depends on a reference or a chrF."""

    blocks_drawn: int
    accepted: int
    accepted_by_block: list[int]
    stop_block: int | None  # index of the block at whose boundary drawing stopped (None if the reserve ended first)
    exhausted: bool
    keys_by_block: list[list[str]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"blocks_drawn": self.blocks_drawn, "accepted": self.accepted, "accepted_by_block": self.accepted_by_block, "stop_block": self.stop_block, "exhausted": self.exhausted}


def count_phase(
    teacher: BatchTeacher, blocks: Sequence[Sequence[Item]], setting: FilterSetting, directory: Path, *, target: int, size: int, deadline: Callable[[], bool] | None = None, source_text: Callable[[Item], str] = lambda i: i.en
) -> CheckCount:
    """Rules 1 and 2. Blocks in the reserve's order; after each block the filter is applied and accepted items counted (no reference is touched: only ``Item.key`` and the English source are read)."""
    accepted_by_block: list[int] = []
    keys_by_block: list[list[str]] = []
    total = 0
    for bi, block in enumerate(blocks):
        keys = [it.key for it in block]
        srcs = [source_text(it) for it in block]
        batches = run_stream(teacher, directory / f"block_{bi:03d}", keys, srcs, size=size, deadline=deadline)
        outs = outputs_of(batches, dict(zip(keys, srcs, strict=True)))
        n = sum(1 for o in outs if accepts(o, setting))
        accepted_by_block.append(n)
        keys_by_block.append(keys)
        total += n
        if total >= target:
            return CheckCount(bi + 1, total, accepted_by_block, bi, False, keys_by_block)
    return CheckCount(len(blocks), total, accepted_by_block, None, True, keys_by_block)


def record_stop(path: Path, count: CheckCount, part: str = "Q") -> None:
    """The stop is recorded BEFORE any reference is read (rule 3). Written once; a second write with different content is refused."""
    rec = {**core.envelope("block_record", part), "what": "qcheck_stop", **count.to_json()}
    if path.exists():
        if read_json(path)["blocks_drawn"] != count.blocks_drawn or read_json(path)["stop_block"] != count.stop_block:
            raise QCheckViolation("a Q_check stop is already recorded with other values; Q_check is not extended")
        return
    core.write_record(path, rec)


def finalize(
    teacher: BatchTeacher, blocks: Sequence[Sequence[Item]], count: CheckCount, setting: FilterSetting, directory: Path, stop_record: Path, refs_provider: Callable[[Item], Sequence[str]], cfg: Mapping[str, Any], *, size: int
) -> dict[str, Any]:
    """Rule 3: precision computed ONCE, in one call, over every accepted item of every block drawn. ``refs_provider`` is called here and nowhere before; the call is refused unless the stop record exists."""
    if not stop_record.is_file():
        raise QCheckViolation("refused: no recorded Q_check stop; no reference may be read before it")
    drawn = [it for block in blocks[: count.blocks_drawn] for it in block]
    keys = [it.key for it in drawn]
    srcs = [it.en for it in drawn]
    batches: list[StoredBatch] = []
    for bi in range(count.blocks_drawn):
        block = blocks[bi]
        batches += run_stream(teacher, directory / f"block_{bi:03d}", [it.key for it in block], [it.en for it in block], size=size)  # stored batches only: this reads them, nothing is regenerated
    outs = outputs_of(batches, dict(zip(keys, srcs, strict=True)))
    refs = [list(refs_provider(it)) for it in drawn]
    scores = qualify.item_scores(outs, refs)
    return {**qualify.precision_on_check(outs, scores, setting, cfg), "items_per_item_scores": scores, "outputs": len(outs)}


# --- generation ------------------------------------------------------------------------------------------------------------------------------
@dataclass
class GenerationResult:
    capability: str
    sources: int
    blocks_run: int
    accepted: list[TrainItem]
    dropped_evaluation_equal: int
    rejected_scores: list[float]  # the score of every rejected generation output (rule 8)
    pool_ended: bool
    reached_target: bool
    accepted_by_block: list[int]

    def counts(self) -> dict[str, Any]:
        return {"capability": self.capability, "sources_generated": self.sources, "blocks": self.blocks_run, "accepted": len(self.accepted), "dropped_evaluation_equal": self.dropped_evaluation_equal, "pool_ended": self.pool_ended, "reached_target": self.reached_target, "accepted_by_block": self.accepted_by_block}


def generate_until_met(
    teacher: BatchTeacher, capability: str, sources: Sequence[Item], order: Sequence[int], setting: FilterSetting, directory: Path, eval_refs_norm: set[str], *, target: int, block_sources: int, size: int, max_blocks: int | None = None,
    deadline: Callable[[], bool] | None = None,
) -> GenerationResult:  # fmt: skip
    """Rules 4 and 5 for one capability, over its own ``sources`` taken in ``order``. After each whole block the accepted count (after the evaluation-equal drop) is compared with ``target``; stop at the first
    block boundary at or above it, or when the pool ends, or after ``max_blocks`` (the rehearsals' limit; never set in a registered stage). Stored batches are reused on resume."""
    ordered = [sources[i] for i in order]
    accepted: list[TrainItem] = []
    rejected: list[float] = []
    dropped = 0
    per_block: list[int] = []
    done = 0
    blocks = 0
    for b0 in range(0, len(ordered), block_sources):
        if max_blocks is not None and blocks >= max_blocks:
            break
        block = ordered[b0 : b0 + block_sources]
        keys = [it.key for it in block]
        srcs = [it.en for it in block]
        batches = run_stream(teacher, directory / f"block_{blocks:04d}", keys, srcs, size=size, deadline=deadline)
        item_of = {it.key: it for it in block}
        n_acc = 0
        for bt in batches:
            for k, text, sc in zip(bt.keys, bt.texts, bt.scores, strict=True):
                it = item_of[k]
                o = Output(it.en, text, sc)
                if not accepts(o, setting):
                    rejected.append(sc)
                    continue
                if normalize(text) in eval_refs_norm:
                    dropped += 1
                    continue
                accepted.append(TrainItem(it.key, it.en, text, it.group))
                n_acc += 1
        per_block.append(n_acc)
        done += len(block)
        blocks += 1
        if len(accepted) >= target:
            return GenerationResult(capability, done, blocks, accepted, dropped, rejected, done >= len(ordered), True, per_block)
    return GenerationResult(capability, done, blocks, accepted, dropped, rejected, done >= len(ordered), False, per_block)


def hash_of(obj: Any) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(obj)).hexdigest()


def write_json_atomic(path: Path, obj: Any) -> None:
    write_json(path, obj)
