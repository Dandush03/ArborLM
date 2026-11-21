# ruff: noqa: E501
"""Core of the private item generators (ADR-0033 sections 6.2, 6.4, 8, 12).

Everything here is deterministic given a registered seed. Per-evaluation, per-family, per-cluster and per-level
streams are derived by SHA-256 of the seed with a text label, never by adding to a seed (registry condition 4.3
item 1). No function calls ``hash()`` and none iterates a set or dict of strings without sorting.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import random
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

CORE_LEVELS = (1, 2, 3, 4, 5)  # the five registered levels
RESERVE_LEVELS = (0, 6)  # one easier, one harder; implemented before any scoring (section 6.2)
ALL_LEVELS = (0, 1, 2, 3, 4, 5, 6)


def derive_seed(seed: int, *labels: str) -> int:
    """SHA-256 of the seed with text labels (never ``seed + k``)."""
    digest = hashlib.sha256("|".join([str(seed), *labels]).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def stream(seed: int, *labels: str) -> random.Random:
    return random.Random(derive_seed(seed, *labels))


_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """The normalisation used for uniqueness and disjointness (NFKC, case-fold, whitespace collapsed)."""
    return _WS.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


class Retry(Exception):
    """Raised by a builder that wants the item drawn again (an unusable random draw)."""


@dataclass(frozen=True)
class Built:
    """What a lineage's builder returns."""

    question: str
    structured: dict[str, Any]
    answer: str
    answer_type: str  # number | letter | ynu | yn | name | word | list | line | text
    k: int | None  # number of options presented for a closed answer; None for open answers


@dataclass(frozen=True)
class Item:
    id: str
    eval: str
    part: str
    lineage: str
    family: str
    level: int
    question: str
    structured: dict[str, Any]
    answer: str
    answer_type: str
    k: int | None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class Lineage:
    """A hand-written base rule: a distinct solution procedure (section 6.2).

    ``build(level, rng)`` returns one item of that level. Shapes made mechanically from one base rule (by
    changing parameters, order, negation, names or surface frame) belong to the same lineage.
    """

    id: str
    eval: str
    family: str
    build: Callable[[int, random.Random], Built]


REGISTRY: dict[str, list[Lineage]] = {}


def lineage(eval_id: str, family: str) -> Callable[[Callable[[int, random.Random], Built]], Callable[[int, random.Random], Built]]:
    def deco(fn: Callable[[int, random.Random], Built]) -> Callable[[int, random.Random], Built]:
        lid = f"{eval_id}.{fn.__name__}"
        bucket = REGISTRY.setdefault(eval_id, [])
        if any(x.id == lid for x in bucket):
            raise ValueError(f"duplicate lineage {lid}")
        bucket.append(Lineage(lid, eval_id, family, fn))
        return fn

    return deco


def lineages_of(eval_id: str) -> list[Lineage]:
    _load_all()
    return sorted(REGISTRY.get(eval_id, []), key=lambda x: x.id)


def _load_all() -> None:
    from studies.m0 import (  # noqa: F401
        lineages_c1,
        lineages_k0,
        lineages_m1,
        lineages_r1,
        lineages_r2,
    )


def family_partition(eval_id: str, seed: int = 400004) -> dict[str, str]:
    """Registered split of the families of one evaluation into part A and part B, half each (section 6.4).

    With an odd number of families part A takes the smaller half (reading: ruling needed 5).
    """
    fams = sorted({x.family for x in lineages_of(eval_id)})
    r = stream(seed, "family-partition", eval_id)
    shuffled = fams[:]
    r.shuffle(shuffled)
    half = len(shuffled) // 2
    return {f: ("A" if i < half else "B") for i, f in enumerate(shuffled)}


def part_lineages(eval_id: str, part: str, seed: int = 400004) -> list[Lineage]:
    if eval_id == "K0":  # not a gate candidate: no family partition, a single part labelled "K"
        return lineages_of("K0") if part == "K" else []
    pmap = family_partition(eval_id, seed)
    return [x for x in lineages_of(eval_id) if pmap[x.family] == part]


def allocate(total: int, weights: Sequence[float]) -> list[int]:
    """Largest-remainder allocation; ties go to the lower index."""
    s = sum(weights)
    raw = [total * w / s for w in weights]
    base = [int(x) for x in raw]
    rest = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (-(raw[i] - base[i]), i))
    for i in order[:rest]:
        base[i] += 1
    return base


def build_item(lin: Lineage, level: int, rng: random.Random, part: str, ident: str) -> Item:
    for _ in range(500):
        try:
            b = lin.build(level, rng)
        except Retry:
            continue
        return Item(ident, lin.eval, part, lin.id, lin.family, level, b.question, b.structured, b.answer, b.answer_type, b.k)
    raise RuntimeError(f"{lin.id} level {level}: 500 consecutive retries")


def draw_items(
    lin: Lineage,
    part: str,
    level: int,
    count: int,
    rng: random.Random,
    taken: set[str],
    role: str,
    attempt_factor: int = 40,
    allow_short: bool = False,
) -> list[Item]:
    """Draw ``count`` items whose normalised text is new (not in ``taken``, which is updated)."""
    out: list[Item] = []
    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > attempt_factor * count + 1000:
            if allow_short:
                break
            raise RuntimeError(f"{lin.id} level {level}: cannot draw {count} distinct items ({len(out)} found)")
        it = build_item(lin, level, rng, part, f"{lin.id}/{role}/L{level}/{len(out)}")
        h = text_hash(it.question)
        if h in taken:
            continue
        taken.add(h)
        out.append(it)
    return out


def generate_pool(
    eval_id: str,
    part: str,
    role: str,
    seed: int,
    size: int,
    level_mix: dict[int, float],
    taken: set[str],
    salt_label: str = "",
    partition_seed: int = 400004,
    shortfalls: list[tuple[str, int, int, int]] | None = None,
) -> list[Item]:
    """A pool balanced over the part's clusters (lineages) and distributed over levels by ``level_mix``.

    ``taken`` holds the text hashes already used by earlier roles, so pools are disjoint by construction; the
    disjointness is verified again afterwards by ``check_disjoint``.
    """
    lins = part_lineages(eval_id, part, partition_seed)
    levels = sorted(level_mix)
    per_cluster = allocate(size, [1.0] * len(lins))
    out: list[Item] = []
    for lin, q in zip(lins, per_cluster, strict=True):
        per_level = allocate(q, [level_mix[lv] for lv in levels])
        for lv, c in zip(levels, per_level, strict=True):
            if c == 0:
                continue
            rng = stream(seed, role, salt_label, eval_id, part, lin.id, str(lv))
            got = draw_items(lin, part, lv, c, rng, taken, role, allow_short=shortfalls is not None)
            if shortfalls is not None and len(got) < c:
                shortfalls.append((lin.id, lv, c, len(got)))  # (lineage, level, wanted, supplied): a capacity failure
            out.extend(got)
    return out


def check_disjoint(pools: dict[str, Sequence[Item]]) -> list[str]:
    """Return problems: items repeated within a pool or shared between pools, after normalisation."""
    seen: dict[str, str] = {}
    problems: list[str] = []
    for name in sorted(pools):
        for it in pools[name]:
            h = text_hash(it.question)
            if h in seen:
                problems.append(f"{it.id} ({name}) repeats an item of {seen[h]}")
            else:
                seen[h] = name
    return problems


def pool_hash(items: Sequence[Item]) -> str:
    h = hashlib.sha256()
    for it in items:
        h.update(it.to_json().encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def keyed_fingerprint(text: str, key: bytes) -> bytes:
    return hmac.new(key, normalise(text).encode("utf-8"), hashlib.sha256).digest()


def ngram_fingerprints(text: str, key: bytes, n: int = 13) -> list[bytes]:
    """HMAC-SHA-256 of each word 13-gram of the normalised text (reading: word n-grams, ruling needed 6)."""
    words = normalise(text).split(" ")
    if len(words) < n:
        return []
    return [hmac.new(key, " ".join(words[i : i + n]).encode("utf-8"), hashlib.sha256).digest() for i in range(len(words) - n + 1)]


def m0_draw(pool: Sequence[Item], size: int, seed: int = 400006, allow_short: bool = False) -> list[Item]:
    """The registered M0 draw: ``size`` items of the development pool, balanced over clusters (lineages)."""
    by: dict[str, list[Item]] = {}
    for it in pool:
        by.setdefault(it.lineage, []).append(it)
    keys = sorted(by)
    quotas = allocate(size, [1.0] * len(keys))
    out: list[Item] = []
    for key, q in zip(keys, quotas, strict=True):
        r = stream(seed, "m0-draw", key)
        members = by[key][:]
        if q > len(members):
            if not allow_short:
                raise ValueError(f"cluster {key} has {len(members)} items, quota {q}")
            q = len(members)  # rehearsal: the balanced draw is impossible; take what the cluster has and record the short draw
        out.extend(r.sample(members, q))
    return out


def nuisance_order(items: Sequence[Item], seed: int = 400006) -> list[Item]:
    """Registered order for the nuisance subset (the first 150 are used): by SHA-256 of seed, label, id."""
    return sorted(items, key=lambda it: derive_seed(seed, "nuisance", it.id))


def permute_options(n_options: int, item_id: str, seed: int = 400007) -> list[int]:
    r = stream(seed, "answer-order", item_id)
    p = list(range(n_options))
    r.shuffle(p)
    return p


@dataclass
class PoolRecord:
    eval: str
    part: str
    role: str
    size: int
    sha256: str
    per_cluster: dict[str, int] = field(default_factory=dict)
    per_level: dict[int, int] = field(default_factory=dict)
    per_family: dict[str, int] = field(default_factory=dict)


def summarise(items: Sequence[Item], eval_id: str, part: str, role: str) -> PoolRecord:
    rec = PoolRecord(eval_id, part, role, len(items), pool_hash(items))
    for it in items:
        rec.per_cluster[it.lineage] = rec.per_cluster.get(it.lineage, 0) + 1
        rec.per_level[it.level] = rec.per_level.get(it.level, 0) + 1
        rec.per_family[it.family] = rec.per_family.get(it.family, 0) + 1
    return rec
