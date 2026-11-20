# ruff: noqa: E501
"""The frozen batch layout of every teacher run, the digest and the regeneration check (ADR-0025 section 4.3 rule 9, section 4.4).

Layout: batch size 32, the order of sources within a block and the order of blocks are in the Part Q plan; every run (Q_fit, Q_check, generation, panel outputs) uses it. A batch is stored with its
index, its source keys in order, its token sequences and its beam scores, one file per batch, written atomically; a resumed stage skips stored batches and never regenerates them.

Digest: 4 whole batches (128 sources) of each teacher's Q_fit run, drawn without replacement by a fresh generator seeded 250908 (the same draw indices for both teachers); asserted at every resume.
Regeneration subsample: 32 whole generation batches per teacher, drawn without replacement by a fresh generator seeded 250914 for each teacher over that teacher's stored generation batches after
generation has ended; regenerated with the same composition and order. Tolerance on token sequences: ZERO. Beam scores within 1e-4 are compared and a larger difference is printed, not acted on.
"""

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from arborlm.io import atomic_write, canonical_json

from ..common import core
from .teacher import BatchTeacher, Generated


class StageCapExceeded(RuntimeError):
    """The stage's cap of charged time was reached: the stage is PAUSED and resumes at the next batch (section 4.3 rule 7)."""


class DigestMismatch(RuntimeError):
    """A resume found a teacher's Q_fit digest different from the recorded one: QUALIFICATION-ENGINEERING-FAILURE (section 4.4 row 1)."""


@dataclass(frozen=True)
class StoredBatch:
    index: int
    keys: tuple[str, ...]
    tokens: tuple[tuple[int, ...], ...]
    scores: tuple[float, ...]
    texts: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {"index": self.index, "keys": list(self.keys), "tokens": [list(t) for t in self.tokens], "scores": list(self.scores), "texts": list(self.texts)}

    @staticmethod
    def from_json(d: Mapping[str, Any]) -> "StoredBatch":
        return StoredBatch(int(d["index"]), tuple(d["keys"]), tuple(tuple(int(x) for x in t) for t in d["tokens"]), tuple(float(s) for s in d["scores"]), tuple(d["texts"]))


def layout(n_sources: int, size: int) -> list[range]:
    """Whole batches in stored order: consecutive ranges of ``size`` sources, the last possibly shorter. The layout depends on nothing but the count."""
    if size < 1:
        raise ValueError("batch size must be positive")
    return [range(i, min(i + size, n_sources)) for i in range(0, n_sources, size)]


def batch_path(directory: Path, index: int) -> Path:
    return directory / f"batch_{index:07d}.json"


def read_batch(directory: Path, index: int) -> StoredBatch:
    return StoredBatch.from_json(json.loads(batch_path(directory, index).read_text(encoding="utf-8")))


def stored_indices(directory: Path) -> list[int]:
    if not directory.is_dir():
        return []
    return sorted(int(p.stem.split("_")[1]) for p in directory.glob("batch_*.json"))


def write_batch(directory: Path, b: StoredBatch) -> None:
    """Atomic: a batch file is either absent or complete."""
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(batch_path(directory, b.index), canonical_json(b.to_json()))


def run_stream(
    teacher: BatchTeacher, directory: Path, keys: Sequence[str], sources: Sequence[str], *, size: int, deadline: Callable[[], bool] | None = None, base_index: int = 0, on_batch: Callable[[StoredBatch], None] | None = None
) -> list[StoredBatch]:
    """Run the teacher over ``sources`` in the frozen layout, storing every batch before the next starts. Batches already stored are read, not regenerated. ``deadline()`` True (checked between batches)
    raises ``StageCapExceeded``: completed batches stay and the next call resumes at the next batch. Returns every batch in order. ``base_index`` offsets the stored index (a block's first batch)."""
    if len(keys) != len(sources):
        raise ValueError("keys and sources differ in length")
    out: list[StoredBatch] = []
    for i, r in enumerate(layout(len(sources), size)):
        idx = base_index + i
        if batch_path(directory, idx).is_file():
            b = read_batch(directory, idx)
            if b.keys != tuple(keys[r.start : r.stop]):
                raise DigestMismatch(f"stored batch {idx} holds other source keys than the plan's layout")
            out.append(b)
            continue
        if deadline is not None and deadline():
            raise StageCapExceeded(f"cap reached before batch {idx}")
        gen: list[Generated] = teacher.generate_batch(list(sources[r.start : r.stop]))
        if len(gen) != len(r):
            raise RuntimeError("the teacher returned a different number of outputs than sources")
        b = StoredBatch(idx, tuple(keys[r.start : r.stop]), tuple(g.tokens for g in gen), tuple(float(g.score) for g in gen), tuple(g.text for g in gen))
        write_batch(directory, b)
        if on_batch is not None:
            on_batch(b)
        out.append(b)
    return out


# --- digest (rule 9) -------------------------------------------------------------------------------------------------------------------------
def draw_batch_indices(n_batches: int, count: int, seed: int, allowed: frozenset[int] | set[int], purpose: str) -> list[int]:
    """``count`` batch indices drawn without replacement by a FRESH generator seeded ``seed`` (one randperm, first ``count``, returned sorted). Fewer batches than ``count``: all of them."""
    g = core.seeded_generator(seed, purpose, allowed)
    order = torch.randperm(n_batches, generator=g).tolist()
    return sorted(order[: min(count, n_batches)])


def digest_of(batches: Sequence[StoredBatch]) -> str:
    """SHA-256 of the canonical JSON of the whole batches' index, keys and token sequences (beam scores are not part of the digest: they are compared within a tolerance, not exactly)."""
    return hashlib.sha256(canonical_json([{"index": b.index, "keys": list(b.keys), "tokens": [list(t) for t in b.tokens]} for b in batches])).hexdigest()


def assert_digest(recorded: Mapping[str, Any], batches: Sequence[StoredBatch]) -> None:
    now = digest_of(batches)
    if now != recorded["sha256"]:
        raise DigestMismatch(f"the Q_fit digest differs from the recorded one: {now} against {recorded['sha256']}")


# --- regeneration check (rule 9, section 4.4) ---------------------------------------------------------------------------------------------------
@dataclass
class RegenReport:
    batches: list[int]
    sources: int
    token_mismatches: list[dict[str, Any]]
    max_score_difference: float
    scores_beyond_tolerance: list[dict[str, Any]]
    thread_count: int | None = None

    @property
    def ok(self) -> bool:
        """Zero tolerance on token sequences. Score differences never fail the check."""
        return not self.token_mismatches

    @property
    def label(self) -> str | None:
        return None if self.ok else "QUALIFICATION-ENGINEERING-FAILURE"

    def to_json(self) -> dict[str, Any]:
        return {
            "batches": self.batches, "sources": self.sources, "ok": self.ok, "token_mismatches": self.token_mismatches, "max_score_difference": self.max_score_difference, "scores_beyond_tolerance": self.scores_beyond_tolerance,
            "thread_count": self.thread_count, "label_if_failed": "QUALIFICATION-ENGINEERING-FAILURE",
        }  # fmt: skip


def regeneration_check(teacher: BatchTeacher, stored: Mapping[int, StoredBatch], indices: Sequence[int], source_of_key: Mapping[str, str], *, score_tolerance: float, threads: int | None = None, clock: Callable[[], float] = time.monotonic) -> RegenReport:
    """Regenerate whole stored batches with the same composition and order and compare. Every output token sequence must equal the stored one; a difference is recorded with the batch index, the item and
    both sequences. The caller sets six threads and deterministic algorithms first: a subsample regenerated in any other layout proves nothing and is never passed here."""
    mism: list[dict[str, Any]] = []
    beyond: list[dict[str, Any]] = []
    worst = 0.0
    n = 0
    for i in indices:
        b = stored[i]
        gen = teacher.generate_batch([source_of_key[k] for k in b.keys])
        for j, (g, key) in enumerate(zip(gen, b.keys, strict=True)):
            n += 1
            if tuple(g.tokens) != b.tokens[j]:
                mism.append({"batch": i, "item": j, "key": key, "stored": list(b.tokens[j]), "regenerated": list(g.tokens)})
            d = abs(float(g.score) - b.scores[j])
            worst = max(worst, d)
            if d > score_tolerance:
                beyond.append({"batch": i, "item": j, "key": key, "stored": b.scores[j], "regenerated": float(g.score), "difference": d})
    return RegenReport(list(indices), n, mism, worst, beyond, threads)


def resume_digest_check(teacher: BatchTeacher, stored: Mapping[int, StoredBatch], indices: Sequence[int], source_of_key: Mapping[str, str], recorded: Mapping[str, Any]) -> str:
    """Asserted at every resume: the digest batches are REGENERATED by the (re)loaded teacher in the stored composition and order, and the digest of the regenerated token sequences must equal the recorded one
    (a changed thread count or layout is caught here). A difference raises ``DigestMismatch`` (QUALIFICATION-ENGINEERING-FAILURE). Returns the digest."""
    regenerated: list[StoredBatch] = []
    for i in indices:
        b = stored[i]
        gen = teacher.generate_batch([source_of_key[k] for k in b.keys])
        regenerated.append(StoredBatch(i, b.keys, tuple(g.tokens for g in gen), tuple(float(g.score) for g in gen), tuple(g.text for g in gen)))
    now = digest_of(regenerated)
    if now != recorded["sha256"] or list(indices) != list(recorded["indices"]):
        raise DigestMismatch(f"the regenerated digest {now} differs from the recorded {recorded['sha256']} (indices {list(indices)} against {list(recorded['indices'])})")
    return now
