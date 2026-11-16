# ruff: noqa: E501
"""P9 task data (package I1): alphabet, checksum identifiers, facts, clusters, templates, streams and
panels, Lane D sets, hashing, the G1 generator checks and the rehearsal seed namespace.

Specification: ADR-0017 section 4 (task and data), 4.6 (gate G1), 5.5 (training order and exposure) and
10 (data seeds). Self-checked only: not independent review, not Astra validation, not human approval.

Data flow: ``build_study_data`` (needs the training-corpus bytes only for the template pool) produces a
``StudyData``. ``training_stream_for`` turns it into the ``TrainingStream`` of one cell; its ``batch(u)``
is a pure function of the update index, so a restored snapshot resumes the exact schedule. Panels and
the calibration stream are fixed ``Stream`` objects read by ``controls`` and ``evaluate``.

Conventions (see ``core``): a context is 64 bytes, model input = bytes 0..62, targets = bytes 1..63,
record ``r`` = bytes 8r..8r+7, answer site = input position 8r+6, target byte 8r+7. Symbols are indices
0..31 into ``core.ALPHABET``; token tensors hold byte values (int64).

Implementation choices not fixed by the ADR (all PENDING LEAD REVIEW, listed again in the report):

* **Held-out contexts by construction.** Every 8-subset of a cluster's 16 facts comes in complementary
  pairs (a context pair partitions the cluster). A pair is assigned to one of 32 classes by a seeded
  hash of (cluster, canonical mask). Classes 0..4 are reserved for the calibration stream (2), panel A
  (0), panel B (1), H1 (3) and H2 (4); training draws only pairs of classes 5..31, so no training
  context of any cell, at any exposure, equals a calibration or panel context, and the streams do not
  overlap each other. This is verified again by hash in G1 (``panel_not_in_training``).
* **Streams are built once for the largest table** and a cell's panel is the sub-selection of contexts
  whose facts are all below ``cell.facts`` (whole clusters, nested prefix), plus the unseen controls.
  The mixed-cluster stream draws its 8 clusters from one octet of 8 consecutive clusters (128 facts) so
  that it is also prefix-closed.
* **Independence tests** use the plug-in mutual information between the answer and the variable as the
  statistic (a function of the contingency table; Monte Carlo p-value, no asymptotics). Fact-level
  variables (identifier positions, cluster) are tested on the stream's distinct facts; instance-level
  variables (template, record index) on the stream's records. Permutations are shared across the tests
  of a stream (each test still has ``permutations`` of its own).
"""

import ctypes
import hashlib
import random
from collections.abc import Callable, Collection
from dataclasses import dataclass
from itertools import combinations
from typing import Any, TypedDict

import torch

from . import core
from .core import Cell, SeedSet

WORLD_MAIN, WORLD_LANE_D = "main", "lane_d"
TEMPLATE_SETS = ("T", "H1", "H2")
IDENT_SPACE = 32**4
FULL_MASK = 0xFFFF
CLASS_MODULUS = 32
RESERVED_CLASS = {"panel_a": 0, "panel_b": 1, "calibration": 2, "h1": 3, "h2": 4}
N_RESERVED = len(RESERVED_CLASS)
_P1, _P2, _PCLASS = 2147483647, 2147483629, 2147483647
_ALPHABET = torch.tensor(core.ALPHABET, dtype=torch.int64)
_BYTE_TO_SYMBOL = torch.full((256,), -1, dtype=torch.int64)
_BYTE_TO_SYMBOL[_ALPHABET] = torch.arange(32)


def _derive(seed: int, *tags: object) -> int:
    """A 62-bit seed derived from ``seed`` and tags (SHA-256), so no derived seed collides by addition."""
    text = "|".join([str(seed), *map(str, tags)]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "little") & ((1 << 62) - 1)


def _gen(seed: int, *tags: object) -> torch.Generator:
    return torch.Generator().manual_seed(_derive(seed, *tags))


def _tensor_bytes(t: torch.Tensor) -> bytes:
    t = t.detach().contiguous().cpu()
    return ctypes.string_at(t.data_ptr(), t.numel() * t.element_size()) if t.numel() else b""


def _hash_tensors(header: str, *tensors: torch.Tensor) -> str:
    digest = hashlib.sha256(header.encode())
    for t in tensors:
        t = t.to(torch.int32) if t.dtype == torch.int64 else t
        digest.update(f"|{list(t.shape)}|{t.dtype}|".encode())
        digest.update(_tensor_bytes(t))
    return digest.hexdigest()


@dataclass(frozen=True)
class Template:
    """A (separator, binding) byte pair; one template per context (ADR 4.2)."""

    separator: int
    binding: int


@dataclass(frozen=True)
class TemplateSplit:
    """Disjoint byte sets from the 48-byte pool (ADR 4.2): ``train`` is T (16 templates from 16
    separators and 16 binding bytes paired one to one), ``h1`` and ``h2`` are 8 of 16 combinations of
    4 separators x 4 binding bytes each. No byte appears in more than one set."""

    train: tuple[Template, ...]
    h1: tuple[Template, ...]
    h2: tuple[Template, ...]

    def of(self, template_set: str) -> tuple[Template, ...]:
        if template_set == "T":
            return self.train
        if template_set == "H1":
            return self.h1
        if template_set == "H2":
            return self.h2
        raise ValueError(f"unknown template set {template_set!r}")

    def byte_set(self, template_set: str) -> frozenset[int]:
        return frozenset(b for t in self.of(template_set) for b in (t.separator, t.binding))

    def tensors(self, template_set: str) -> tuple[torch.Tensor, torch.Tensor]:
        ts = self.of(template_set)
        return (
            torch.tensor([t.separator for t in ts], dtype=torch.int64),
            torch.tensor([t.binding for t in ts], dtype=torch.int64),
        )


@dataclass
class FactTable:
    """A world of facts. ``ident [F, 5] int64`` symbol indices (the first four uniform, the fifth the
    sum modulo 32); ``answer [F] int64`` symbol index; ``cluster [F] int64`` cluster id of 16 facts
    (-1 for unseen controls). The first ``trained`` rows are trainable facts; the rest are unseen
    controls with random answers (ADR 4.1). Identifiers are unique within a world, and the main and
    Lane D worlds use disjoint identifiers (core.OPEN_CHOICES c04). ``pair_salt`` seeds the class hash
    of context pairs (module docstring); it is part of the table's identity."""

    world: str
    ident: torch.Tensor
    answer: torch.Tensor
    cluster: torch.Tensor
    trained: int
    pair_salt: int = 0

    @property
    def size(self) -> int:
        return int(self.ident.shape[0])


@dataclass
class Stream:
    """Fixed contexts of one stream. ``tokens [C, 64] int64`` bytes; ``fact_ids [C, 8] int64`` fact id
    of each record in the stream's ``world`` table (ids >= ``trained`` are unseen controls);
    ``cluster [C] int64`` (-1 when the context mixes clusters or holds unseen facts); ``template [C]
    int64`` index into ``TemplateSplit.of(template_set)``. ``sha256`` hashes the tensors (ADR 4.4)."""

    name: str
    world: str
    template_set: str
    tokens: torch.Tensor
    fact_ids: torch.Tensor
    cluster: torch.Tensor
    template: torch.Tensor
    sha256: str

    def answer_targets(self) -> torch.Tensor:
        """``[C, 8] int64`` answer symbol indices of the records (the target of each answer site)."""
        return _BYTE_TO_SYMBOL[self.tokens[:, core.ANSWER_TARGET_OFFSET :: core.RECORD_BYTES]]


@dataclass
class Batch:
    """One training batch: ``tokens [16, 64] int64``, ``fact_ids [16, 8] int64``, ``cluster [16]``,
    ``template [16]`` (replay arms add 16 replayed contexts in ``replay_*``, else None)."""

    tokens: torch.Tensor
    fact_ids: torch.Tensor
    cluster: torch.Tensor
    template: torch.Tensor
    replay_tokens: torch.Tensor | None = None
    replay_fact_ids: torch.Tensor | None = None


@dataclass(frozen=True)
class DataSizes:
    """Sizes of a draw. The registered values are the defaults; tests use tiny ones. Constraints:
    ``main_trained`` and ``lane_d_per_set`` are multiples of 128 (whole octets of clusters and whole
    updates), ``unseen`` a multiple of 8."""

    main_trained: int = core.FACTS_PROPORTIONAL[65536]
    unseen: int = core.UNSEEN_FACTS
    lane_d_per_set: int = core.LANE_D_FACTS

    def __post_init__(self) -> None:
        if self.main_trained % 128 or self.lane_d_per_set % 128 or self.unseen % 8:
            raise ValueError("sizes must be multiples of 128 / 128 / 8")


# --- hashing helpers ---------------------------------------------------------------------------
def context_keys(fact_ids: torch.Tensor) -> torch.Tensor:
    """``[C] int64`` 62-bit hash of the unordered fact set of each context row of ``fact_ids [C, 8]``
    (two independent polynomial hashes of the sorted ids, modulo two primes below 2**31)."""
    ids = fact_ids.sort(dim=1).values
    h1 = torch.zeros(ids.shape[0], dtype=torch.int64)
    h2 = torch.zeros(ids.shape[0], dtype=torch.int64)
    for j in range(ids.shape[1]):
        h1 = (h1 * 1000003 + ids[:, j] + 1) % _P1
        h2 = (h2 * 998244353 + ids[:, j] + 7) % _P2
    return h1 * (1 << 31) + h2


def context_key(fact_ids: torch.Tensor) -> bytes:
    """Hash of the unordered fact set of one context (``[8] int64``); used to keep panel contexts out
    of training (ADR 4.4). Eight bytes, little-endian signed form of ``context_keys``."""
    return int(context_keys(fact_ids.reshape(1, -1))[0]).to_bytes(8, "little", signed=True)


def _as_key_tensor(keys: "Collection[bytes] | torch.Tensor") -> torch.Tensor:
    if isinstance(keys, torch.Tensor):
        return keys.to(torch.int64).reshape(-1)
    return torch.tensor([int.from_bytes(k, "little", signed=True) for k in keys], dtype=torch.int64)


def _pair_class(cluster: torch.Tensor, canonical_mask: torch.Tensor, salt: int) -> torch.Tensor:
    """Class 0..31 of a context pair: a seeded hash of (cluster, canonical mask), stays below 2**62."""
    x = (cluster * 65536 + canonical_mask + salt) % _PCLASS
    for a, b in ((48271, 12345), (69621, 6789), (16807, 1013)):
        x = (x * a + b) % _PCLASS
        x = x ^ (x >> 13)
    return x % CLASS_MODULUS


def _partition_class(perm: torch.Tensor, cluster: torch.Tensor, salt: int) -> torch.Tensor:
    mask = (1 << perm[:, :8]).sum(dim=1)
    return _pair_class(cluster, torch.minimum(mask, FULL_MASK ^ mask), salt)


def _draw_partitions(
    cluster: torch.Tensor,
    gen: torch.Generator,
    salt: int,
    accept: Callable[[torch.Tensor, torch.Tensor], torch.Tensor],
) -> torch.Tensor:
    """``[n, 16]`` permutations of the members of ``n`` clusters; rows are redrawn (deterministically,
    from ``gen``) until ``accept(perm, class)`` holds. Terminates with probability one."""
    n = int(cluster.shape[0])
    perm = torch.rand(n, 16, generator=gen).argsort(dim=1)
    for _ in range(1_000_000):
        bad = ~accept(perm, _partition_class(perm, cluster, salt))
        if not bool(bad.any()):
            return perm
        perm[bad] = torch.rand(int(bad.sum()), 16, generator=gen).argsort(dim=1)
    raise RuntimeError("partition draw did not terminate")


def _group_clusters(table: FactTable, fact_ids: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """``members [n, 16]`` (fact ids by cluster, in the given order within a cluster) and ``cluster
    [n]`` ids, clusters ascending. Requires whole clusters of 16."""
    cl = table.cluster[fact_ids]
    if bool((cl < 0).any()):
        raise ValueError("fact ids include unseen controls (no cluster)")
    order = torch.argsort(cl, stable=True)
    cl_sorted = cl[order]
    unique, counts = torch.unique_consecutive(cl_sorted, return_counts=True)
    if bool((counts != core.CLUSTER_SIZE).any()):
        raise ValueError("fact ids must be whole clusters of 16")
    return fact_ids[order].reshape(-1, core.CLUSTER_SIZE), unique


def _build_tokens(
    table: FactTable, ids: torch.Tensor, sep: torch.Tensor, bind: torch.Tensor
) -> torch.Tensor:
    """``[C, 64]`` bytes from ``ids [C, 8]`` and the context's template bytes ``[C]``."""
    c = ids.shape[0]
    ident = _ALPHABET[table.ident[ids]]  # [C, 8, 5]
    answer = _ALPHABET[table.answer[ids]]
    sepb = sep[:, None].expand(c, 8)
    bindb = bind[:, None].expand(c, 8)
    record = torch.cat([sepb[..., None], ident, bindb[..., None], answer[..., None]], dim=-1)
    return record.reshape(c, core.CONTEXT_BYTES)


def stream_sha256(stream: Stream) -> str:
    return _hash_tensors(
        f"{stream.name}|{stream.world}|{stream.template_set}",
        stream.tokens.to(torch.uint8),
        stream.fact_ids,
        stream.cluster,
        stream.template,
    )


def _new_stream(
    name: str,
    table: FactTable,
    templates: TemplateSplit,
    template_set: str,
    ids: torch.Tensor,
    cluster: torch.Tensor,
    template: torch.Tensor,
) -> Stream:
    sep, bind = templates.tensors(template_set)
    tokens = _build_tokens(table, ids, sep[template], bind[template])
    stream = Stream(name, table.world, template_set, tokens, ids, cluster, template, "")
    stream.sha256 = stream_sha256(stream)
    return stream


# --- facts -------------------------------------------------------------------------------------
def encode_identifiers(ident: torch.Tensor) -> torch.Tensor:
    """``[F, 5] int64`` symbols -> ``[F] int64`` code ``sum(symbol_i * 32**i, i < 4)`` (< 32**4)."""
    weights = torch.tensor([32**i for i in range(4)], dtype=torch.int64)
    return (ident[:, :4] * weights).sum(dim=1)


def _decode(codes: torch.Tensor) -> torch.Tensor:
    free = torch.stack([(codes >> (5 * i)) & 31 for i in range(4)], dim=1)
    return torch.cat([free, (free.sum(dim=1) % core.CHECKSUM_MODULUS)[:, None]], dim=1)


def make_fact_table(
    seed: int,
    trained: int,
    unseen: int,
    *,
    exclude: Collection[int] = (),
    cluster_seed: int,
    world: str = WORLD_MAIN,
) -> FactTable:
    """Unique identifiers (four uniform symbols plus checksum, never in ``exclude`` = encoded
    identifiers already used), uniform independent answers, clusters of 16 (ADR 4.1, 4.3).

    Identifiers are the first ``trained + unseen`` entries of a seeded permutation of the 32**4 codes
    (so they are unique, and any two differ in at least two positions because the fifth symbol is the
    sum of the first four). The trained rows are then reordered by a permutation seeded with
    ``cluster_seed``; cluster of trained row ``i`` is ``i // 16`` (so any prefix of whole clusters is
    a valid smaller table). Unseen rows follow, with cluster -1. Answers are uniform on 0..31, drawn
    after, and independent of, the identifiers."""
    if trained % core.CLUSTER_SIZE or trained < 0 or unseen < 0:
        raise ValueError("trained must be a non-negative multiple of 16")
    total = trained + unseen
    gen = _gen(seed, "facts")
    perm = torch.randperm(IDENT_SPACE, generator=gen)
    if len(exclude):
        taken = torch.zeros(IDENT_SPACE, dtype=torch.bool)
        taken[torch.tensor(list(exclude), dtype=torch.int64)] = True
        perm = perm[~taken[perm]]
    if perm.shape[0] < total:
        raise ValueError("not enough identifiers")
    codes = perm[:total]
    order = torch.randperm(trained, generator=_gen(cluster_seed, "cluster_assignment"))
    codes = torch.cat([codes[:trained][order], codes[trained:]])
    answer = torch.randint(0, core.ALPHABET_SIZE, (total,), generator=gen)
    cluster = torch.cat(
        [torch.arange(trained) // core.CLUSTER_SIZE, torch.full((unseen,), -1, dtype=torch.int64)]
    )
    salt = _derive(cluster_seed, "pair_salt") % _PCLASS
    return FactTable(world, _decode(codes), answer, cluster, trained, salt)


def identifier_lut(table: FactTable, fact_ids: torch.Tensor) -> torch.Tensor:
    """``[32**4] int64`` lookup: encoded identifier -> position in ``fact_ids`` (the R2 slot index of
    that fact), -1 elsewhere. Passed to ``model.build_model`` for the R2 rung."""
    lut = torch.full((IDENT_SPACE,), -1, dtype=torch.int64)
    lut[encode_identifiers(table.ident[fact_ids])] = torch.arange(fact_ids.shape[0])
    return lut


def neighbour_flags(table: FactTable, among: int | None = None) -> torch.Tensor:
    """``[F] bool``: the fact has another fact whose identifier differs in at most two positions
    (accuracy is reported separately with and without such a neighbour, ADR 4.1). ``among`` limits the
    other facts to the first ``among`` rows (default ``table.trained``), so a cell of ``cell.facts``
    facts passes ``among=cell.facts``. Two identifiers differ in at least two positions, so a
    neighbour differs in exactly two."""
    n = table.size
    m = table.trained if among is None else among
    flags = torch.zeros(n, dtype=torch.bool)
    in_subset = (torch.arange(n) < m).to(torch.int64)
    for i, j in combinations(range(5), 2):
        keep = [k for k in range(5) if k not in (i, j)]
        key = table.ident[:, keep[0]] + 32 * table.ident[:, keep[1]] + 1024 * table.ident[:, keep[2]]
        count = torch.bincount(key[:m], minlength=32**3)
        flags |= (count[key] - in_subset) >= 1
    return flags


# --- templates ---------------------------------------------------------------------------------
def split_templates(pool: tuple[int, ...], seed: int) -> TemplateSplit:
    """Split the 48-byte pool by seed as in ``core.OPEN_CHOICES['c03_template_split']``."""
    if len(pool) != core.TEMPLATE_POOL_SIZE or len(set(pool)) != len(pool):
        raise ValueError("template pool must hold 48 distinct bytes")
    shuffled = list(pool)
    random.Random(seed).shuffle(shuffled)
    train = tuple(Template(s, b) for s, b in zip(shuffled[:16], shuffled[16:32], strict=True))
    rng = random.Random(seed + 1)

    def held(chunk: list[int]) -> tuple[Template, ...]:
        seps, binds = chunk[:4], chunk[4:]
        return tuple(Template(seps[c // 4], binds[c % 4]) for c in sorted(rng.sample(range(16), 8)))

    return TemplateSplit(train, held(shuffled[32:40]), held(shuffled[40:48]))


# --- the training schedule -----------------------------------------------------------------------
class TrainingStream:
    """Deterministic training schedule over a fact subset (ADR 4.3, 5.5).

    Each epoch visits the clusters in seeded order and each cluster as two contexts of 8 distinct facts
    in seeded order, so every fact appears exactly once per epoch (``len(facts) / 128`` updates per
    epoch). ``batch(update)`` is a pure function of the 1-based update index (no hidden state; a
    one-epoch cache only saves time). The partition of a cluster into two halves is redrawn until its
    class (module docstring) is not a reserved evaluation class."""

    facts: torch.Tensor

    def __init__(
        self,
        table: FactTable,
        fact_ids: torch.Tensor,
        templates: TemplateSplit,
        order_seed: int,
        replay: "TrainingStream | None" = None,
    ) -> None:
        if fact_ids.shape[0] % 128:
            raise ValueError("a training schedule needs a multiple of 128 facts")
        self.table = table
        self.facts = fact_ids
        self.templates = templates
        self.order_seed = order_seed
        self.replay = replay
        self.members, self.cluster_ids = _group_clusters(table, fact_ids)
        self.updates_per_epoch = fact_ids.shape[0] // core.ANSWER_SITES_PER_BATCH
        self._sep, self._bind = templates.tensors("T")
        self._cache: tuple[int, tuple[torch.Tensor, torch.Tensor, torch.Tensor]] | None = None

    def epoch_contexts(self, epoch: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """``(fact_ids [2n, 8], template [2n], cluster [2n])`` of the epoch, in visiting order."""
        if self._cache is not None and self._cache[0] == epoch:
            return self._cache[1]
        gen = _gen(self.order_seed, "epoch", epoch)
        n = self.members.shape[0]
        visit = torch.randperm(n, generator=gen)
        members, cluster = self.members[visit], self.cluster_ids[visit]
        perm = _draw_partitions(
            cluster, gen, self.table.pair_salt, lambda _p, cls: cls >= N_RESERVED
        )
        first, second = members.gather(1, perm[:, :8]), members.gather(1, perm[:, 8:])
        ids = torch.stack([first, second], dim=1).reshape(2 * n, 8)
        template = torch.randint(0, len(self._sep), (2 * n,), generator=gen)
        out = (ids, template, cluster.repeat_interleave(2))
        self._cache = (epoch, out)
        return out

    def batch(self, update: int) -> Batch:
        """Batch for 1-based ``update``: 16 contexts of 8 facts (plus 16 replay contexts if the
        stream was built with replay ids)."""
        if update < 1:
            raise ValueError("updates are 1-based")
        epoch, within = divmod(update - 1, self.updates_per_epoch)
        ids, template, cluster = self.epoch_contexts(epoch)
        lo, hi = core.BATCH_CONTEXTS * within, core.BATCH_CONTEXTS * (within + 1)
        ids, template, cluster = ids[lo:hi], template[lo:hi], cluster[lo:hi]
        tokens = _build_tokens(self.table, ids, self._sep[template], self._bind[template])
        replay_tokens = replay_ids = None
        if self.replay is not None:
            inner = self.replay.batch(update)
            replay_tokens, replay_ids = inner.tokens, inner.fact_ids
        return Batch(tokens, ids, cluster, template, replay_tokens, replay_ids)

    def exposures(self, updates: int) -> torch.Tensor:
        """``[len(facts)] int64`` times each fact has been an answer site after ``updates`` updates."""
        full, rest = divmod(updates, self.updates_per_epoch)
        out = torch.full((self.facts.shape[0],), full, dtype=torch.int64)
        if rest:
            ids = self.epoch_contexts(full)[0][: core.BATCH_CONTEXTS * rest].reshape(-1)
            position = torch.full((int(self.facts.max()) + 1,), -1, dtype=torch.int64)
            position[self.facts] = torch.arange(self.facts.shape[0])
            out[position[ids]] += 1
        return out

    def keys(self, epochs: int) -> torch.Tensor:
        """Context keys (``context_keys``) of the first ``epochs`` epochs, concatenated."""
        return torch.cat([context_keys(self.epoch_contexts(e)[0]) for e in range(epochs)])


def make_training_stream(
    table: FactTable,
    fact_ids: torch.Tensor,
    templates: TemplateSplit,
    order_seed: int,
    *,
    replay_ids: torch.Tensor | None = None,
) -> TrainingStream:
    """Schedule over ``fact_ids`` (``[F] int64`` ids in ``table``) with training templates T.
    ``replay_ids`` (a replayed set, Lane D) adds one replayed context per training context."""
    replay = (
        None
        if replay_ids is None
        else TrainingStream(table, replay_ids, templates, _derive(order_seed, "replay"))
    )
    return TrainingStream(table, fact_ids, templates, order_seed, replay)


# --- fixed streams -------------------------------------------------------------------------------
def _cluster_pass(
    members: torch.Tensor,
    cluster: torch.Tensor,
    salt: int,
    gen: torch.Generator,
    reserved_class: int | None,
    avoid: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    def accept(perm: torch.Tensor, cls: torch.Tensor) -> torch.Tensor:
        ok = torch.ones(perm.shape[0], dtype=torch.bool)
        if reserved_class is not None:
            ok &= cls == reserved_class
        if avoid.numel():
            first, second = members.gather(1, perm[:, :8]), members.gather(1, perm[:, 8:])
            ok &= ~torch.isin(context_keys(first), avoid) & ~torch.isin(context_keys(second), avoid)
        return ok

    perm = _draw_partitions(cluster, gen, salt, accept)
    first, second = members.gather(1, perm[:, :8]), members.gather(1, perm[:, 8:])
    return torch.cat([first, second]), torch.cat([cluster, cluster])


def _mixed_pass(
    members: torch.Tensor, cluster: torch.Tensor, gen: torch.Generator
) -> tuple[torch.Tensor, torch.Tensor]:
    n = members.shape[0]
    if n % 8:
        raise ValueError("a mixed-cluster stream needs a multiple of 8 clusters (128 facts)")
    shuffled = members.gather(1, torch.rand(n, 16, generator=gen).argsort(dim=1))
    layers = shuffled.reshape(n // 8, 8, 16).permute(0, 2, 1).reshape(-1, 8)  # 8 clusters per row
    order = torch.rand(layers.shape[0], 8, generator=gen).argsort(dim=1)
    return layers.gather(1, order), torch.full((layers.shape[0],), -1, dtype=torch.int64)


def make_stream(
    name: str,
    table: FactTable,
    fact_ids: torch.Tensor,
    templates: TemplateSplit,
    template_set: str,
    seed: int,
    *,
    passes: int = 1,
    mixed_clusters: bool = False,
    avoid_context_keys: "Collection[bytes] | torch.Tensor" = (),
    reserved_class: int | None = None,
) -> Stream:
    """Fixed stream: every fact ``passes`` times in contexts whose fact set is not in
    ``avoid_context_keys`` (``context_key`` of each training context, or a tensor from
    ``context_keys``), a fact's own record never earlier in its context than its answer site is read
    (ADR 4.3: the 8 facts of a context are distinct). ``mixed_clusters`` draws the 8 facts from 8
    different clusters. ``reserved_class`` (see ``RESERVED_CLASS``) restricts clustered contexts to
    the pairs of that class, which training never uses. Unseen controls (no cluster) are grouped
    at random into contexts of their own."""
    gen = _gen(seed, "stream", name)
    avoid = _as_key_tensor(avoid_context_keys)
    clustered = bool((table.cluster[fact_ids] >= 0).all())
    ids_parts: list[torch.Tensor] = []
    cluster_parts: list[torch.Tensor] = []
    for _ in range(passes):
        if clustered:
            members, cluster = _group_clusters(table, fact_ids)
            if mixed_clusters:
                ids, cl = _mixed_pass(members, cluster, gen)
            else:
                ids, cl = _cluster_pass(
                    members, cluster, table.pair_salt, gen, reserved_class, avoid
                )
                avoid = torch.cat([avoid, context_keys(ids)])
        else:
            if mixed_clusters or fact_ids.shape[0] % 8:
                raise ValueError("unseen controls need a multiple of 8 facts and no mixing")
            ids = fact_ids[torch.randperm(fact_ids.shape[0], generator=gen)].reshape(-1, 8)
            cl = torch.full((ids.shape[0],), -1, dtype=torch.int64)
        ids_parts.append(ids)
        cluster_parts.append(cl)
    ids = torch.cat(ids_parts)
    cluster = torch.cat(cluster_parts)
    order = torch.randperm(ids.shape[0], generator=gen)
    ids, cluster = ids[order], cluster[order]
    template = torch.randint(0, len(templates.of(template_set)), (ids.shape[0],), generator=gen)
    return _new_stream(name, table, templates, template_set, ids, cluster, template)


def _concat_streams(name: str, table: FactTable, templates: TemplateSplit, *parts: Stream) -> Stream:
    first = parts[0]
    ids = torch.cat([p.fact_ids for p in parts])
    return _new_stream(
        name,
        table,
        templates,
        first.template_set,
        ids,
        torch.cat([p.cluster for p in parts]),
        torch.cat([p.template for p in parts]),
    )


def restrict_stream(stream: Stream, table: FactTable, facts: int) -> Stream:
    """The contexts of ``stream`` whose facts are all trained facts below ``facts`` or all unseen
    controls. Returns ``stream`` itself when nothing is dropped."""
    below = (stream.fact_ids < facts).all(dim=1)
    unseen = (stream.fact_ids >= table.trained).all(dim=1)
    keep = below | unseen
    if bool(keep.all()):
        return stream
    sub = Stream(
        stream.name,
        stream.world,
        stream.template_set,
        stream.tokens[keep],
        stream.fact_ids[keep],
        stream.cluster[keep],
        stream.template[keep],
        "",
    )
    sub.sha256 = stream_sha256(sub)
    return sub


# --- the whole draw ------------------------------------------------------------------------------
@dataclass
class StudyData:
    """Everything generated from one ``SeedSet`` before any training (ADR 4.4)."""

    seeds: SeedSet
    templates: TemplateSplit
    facts: FactTable  # main world: 32,768 trained facts then 2,048 unseen controls
    lane_d: FactTable  # Lane D world: set A ids 0..4095, set B ids 4096..8191, no unseen rows
    streams: dict[
        str, Stream
    ]  # keys core.STREAM_NAMES plus lane_d_<panel>_<set> (panel in a|b, set in A|B)
    pool: tuple[int, ...]

    def sha256s(self) -> dict[str, str]:
        """Stream and table hashes, written to the stage manifest before any training."""
        out = {
            "facts": _hash_tensors("facts", self.facts.ident, self.facts.answer, self.facts.cluster),
            "lane_d": _hash_tensors(
                "lane_d", self.lane_d.ident, self.lane_d.answer, self.lane_d.cluster
            ),
            "templates": _hash_tensors(
                "templates",
                *(
                    torch.tensor([[t.separator, t.binding] for t in self.templates.of(s)])
                    for s in TEMPLATE_SETS
                ),
            ),
            "pool": _hash_tensors("pool", torch.tensor(self.pool)),
        }
        out.update({f"stream:{k}": v.sha256 for k, v in sorted(self.streams.items())})
        return out

    @property
    def lane_d_set_size(self) -> int:
        return self.lane_d.trained // 2


def _lane_d_table(seeds: SeedSet, main: FactTable, per_set: int) -> FactTable:
    exclude = encode_identifiers(main.ident).tolist()
    set_a = make_fact_table(
        seeds.lane_d_a,
        per_set,
        0,
        exclude=exclude,
        cluster_seed=_derive(seeds.clusters, "lane_d_a"),
        world=WORLD_LANE_D,
    )
    set_b = make_fact_table(
        seeds.lane_d_b,
        per_set,
        0,
        exclude=exclude + encode_identifiers(set_a.ident).tolist(),
        cluster_seed=_derive(seeds.clusters, "lane_d_b"),
        world=WORLD_LANE_D,
    )
    return FactTable(
        WORLD_LANE_D,
        torch.cat([set_a.ident, set_b.ident]),
        torch.cat([set_a.answer, set_b.answer]),
        torch.cat([set_a.cluster, set_b.cluster + per_set // core.CLUSTER_SIZE]),
        2 * per_set,
        set_a.pair_salt,
    )


def build_study_data(seeds: SeedSet, corpus: bytes, *, sizes: DataSizes | None = None) -> StudyData:
    """Generate the whole draw. ``corpus`` is ``core.load_trained_corpus(...)`` (used only through
    ``core.derive_template_pool``; its result must equal ``core.TEMPLATE_POOL`` for registered use).
    Deterministic in ``seeds``; ADR 4.1-4.4. ``sizes`` (tests only) shrinks the draw."""
    sizes = sizes or DataSizes()
    pool = core.derive_template_pool(corpus)
    if seeds.name == "registered" and pool != core.TEMPLATE_POOL:
        raise ValueError("registered template pool differs from core.TEMPLATE_POOL")
    templates = split_templates(pool, seeds.templates)
    main = make_fact_table(
        seeds.facts, sizes.main_trained, sizes.unseen, cluster_seed=seeds.clusters
    )
    lane_d = _lane_d_table(seeds, main, sizes.lane_d_per_set)
    trained_ids = torch.arange(sizes.main_trained)
    unseen_ids = torch.arange(sizes.main_trained, sizes.main_trained + sizes.unseen)
    streams: dict[str, Stream] = {}

    def clustered(name: str, template_set: str, seed: int, **kw: Any) -> Stream:
        return make_stream(name, main, trained_ids, templates, template_set, seed, **kw)

    streams["calibration"] = clustered(
        "calibration",
        "T",
        seeds.calibration_stream,
        passes=2,
        reserved_class=RESERVED_CLASS["calibration"],
    )
    for name, seed in (("panel_a", seeds.panel_a), ("panel_b", seeds.panel_b)):
        trained_part = clustered(name, "T", seed, reserved_class=RESERVED_CLASS[name])
        unseen_part = make_stream(name, main, unseen_ids, templates, "T", seed)
        streams[name] = _concat_streams(name, main, templates, trained_part, unseen_part)
    streams["h1"] = clustered("h1", "H1", seeds.held_out, reserved_class=RESERVED_CLASS["h1"])
    streams["h2"] = clustered("h2", "H2", seeds.held_out, reserved_class=RESERVED_CLASS["h2"])
    streams["mixed"] = clustered("mixed", "T", seeds.mixed_cluster, mixed_clusters=True)
    per_set = sizes.lane_d_per_set
    for panel, seed in (("a", seeds.panel_a), ("b", seeds.panel_b)):
        for label, lo in (("A", 0), ("B", per_set)):
            ids = torch.arange(lo, lo + per_set)
            name = f"lane_d_{panel}_{label}"
            streams[name] = make_stream(
                name,
                lane_d,
                ids,
                templates,
                "T",
                _derive(seed, "lane_d", label),
                reserved_class=RESERVED_CLASS[f"panel_{panel}"],
            )
    return StudyData(seeds, templates, main, lane_d, streams, pool)


# --- cells ---------------------------------------------------------------------------------------
def _lane_d_ids(data: StudyData, which: str) -> torch.Tensor:
    n = data.lane_d_set_size
    if which == "A":
        return torch.arange(0, n)
    if which == "B":
        return torch.arange(n, 2 * n)
    return torch.arange(0, 2 * n)


def facts_of(data: StudyData, cell: Cell) -> torch.Tensor:
    """``[cell.facts] int64`` ids of the cell's trained facts in its world (the R2 slot order)."""
    if not cell.is_lane_d:
        return torch.arange(cell.facts)
    which = {"phaseA": "A", "joint": "AB"}.get(cell.lane_d_arm or "", "B")
    ids = _lane_d_ids(data, which)
    if ids.shape[0] != cell.facts:
        raise ValueError("cell.facts does not match the Lane D set size")
    return ids


def training_stream_for(data: StudyData, cell: Cell) -> TrainingStream:
    """The schedule of ``cell``: main world facts ``0..cell.facts-1``; Lane D: phaseA/sequential/
    memory_only/replay use set A (phaseA) or B (phase B; replay adds set A), joint uses A then B."""
    seed = data.seeds.training_order
    if not cell.is_lane_d:
        return make_training_stream(
            data.facts, facts_of(data, cell), data.templates, _derive(seed, "main")
        )
    arm = cell.lane_d_arm
    which = {"phaseA": "A", "joint": "AB"}.get(arm or "", "B")
    return make_training_stream(
        data.lane_d,
        facts_of(data, cell),
        data.templates,
        _derive(seed, "lane_d", which),
        replay_ids=_lane_d_ids(data, "A") if arm == "replay" else None,
    )


def panel_streams(data: StudyData, cell: Cell, panel: str) -> list[Stream]:
    """Streams on which ``cell`` is evaluated for ``panel`` in {A, B}: the primary panel (trained
    facts and unseen-control contexts); for Lane D cells the A and B panels of each set."""
    if panel not in core.PANELS:
        raise ValueError("panel must be 'A' or 'B'")
    if cell.is_lane_d:
        return [data.streams[f"lane_d_{panel.lower()}_{s}"] for s in ("A", "B")]
    stream = data.streams[core.PANEL_STREAM[panel]]
    return [restrict_stream(stream, data.facts, cell.facts)]


# --- gate G1 ---------------------------------------------------------------------------------------
class G1Check(TypedDict):
    name: str
    stream: str | None
    passed: bool
    detail: dict[str, Any]


class G1Report(TypedDict):
    """Gate G1 (ADR 4.6): uniqueness and checksum, coverage and equal frequency, independence tests
    (k = ``core.G1_TESTS_PER_STREAM`` per stream, permutations >= 2000 k, Bonferroni within a stream),
    no panel context in training, no fact's record before its own answer site, dictionary lookup
    scores, and rehearsal seeds disjoint from registered ones."""

    passed: bool
    checks: list[G1Check]
    tests_per_stream: dict[str, int]


def _check(name: str, stream: str | None, passed: bool, **detail: Any) -> G1Check:
    return G1Check(name=name, stream=stream, passed=bool(passed), detail=detail)


def _table_checks(table: FactTable) -> G1Check:
    ident = table.ident
    codes = encode_identifiers(ident)
    unique = int(torch.unique(codes).numel()) == table.size
    checksum = bool((ident[:, 4] == ident[:, :4].sum(dim=1) % core.CHECKSUM_MODULUS).all())
    in_range = bool(((ident >= 0) & (ident < 32)).all() and ((table.answer >= 0) & (table.answer < 32)).all())
    hamming_ok = True
    for leave_out in range(5):  # two ids sharing 4 positions would repeat a leave-one-out key
        keep = [k for k in range(5) if k != leave_out]
        key = sum(ident[:, k] * 32**n for n, k in enumerate(keep))
        hamming_ok &= int(torch.unique(key).numel()) == table.size
    trained = table.cluster[: table.trained]
    counts = torch.bincount(trained, minlength=max(1, table.trained // 16))
    clusters_ok = bool((counts == core.CLUSTER_SIZE).all()) and bool((table.cluster[table.trained :] == -1).all())
    return _check(
        "identifiers",
        None,
        unique and checksum and in_range and hamming_ok and clusters_ok,
        world=table.world,
        facts=table.size,
        unique=unique,
        checksum=checksum,
        symbol_range=in_range,
        min_hamming_at_least_2=bool(hamming_ok),
        clusters_of_16=clusters_ok,
    )


def _mi_statistic(codes32: torch.Tensor, k: int, answer: torch.Tensor) -> float:
    counts = torch.bincount(codes32 + answer, minlength=k * 32).double()
    return float((counts * counts.clamp_min(1.0).log()).sum())


def independence_tests(
    answer: torch.Tensor,
    variables: list[tuple[str, torch.Tensor]],
    permutations: int,
    gen: torch.Generator,
) -> list[dict[str, Any]]:
    """Seeded Monte Carlo permutation tests of independence between ``answer [N]`` (symbols 0..31) and
    each categorical variable ``[N]`` (integer codes, any values). Statistic: plug-in mutual
    information, in the equivalent form ``sum c log c`` of the contingency counts (margins are fixed
    under permutation). p = (1 + #{permuted >= observed}) / (permutations + 1). Returns, per variable,
    ``name``, ``categories``, ``n``, ``statistic``, ``p`` (no correction)."""
    prepared: list[tuple[str, torch.Tensor, int, float]] = []
    for name, values in variables:
        _, inverse = torch.unique(values, return_inverse=True)
        k = int(inverse.max()) + 1
        codes32 = inverse * 32
        prepared.append((name, codes32, k, _mi_statistic(codes32, k, answer)))
    exceed = [0] * len(prepared)
    n = answer.shape[0]
    for _ in range(permutations):
        shuffled = answer[torch.randperm(n, generator=gen)]
        for i, (_, codes32, k, observed) in enumerate(prepared):
            if _mi_statistic(codes32, k, shuffled) >= observed - 1e-9 * max(1.0, abs(observed)):
                exceed[i] += 1
    return [
        {
            "name": name,
            "categories": k,
            "n": n,
            "statistic": observed,
            "p": (1 + exceed[i]) / (permutations + 1),
        }
        for i, (name, _, k, observed) in enumerate(prepared)
    ]


def stream_independence(
    stream: Stream, table: FactTable, permutations: int, seed: int
) -> G1Check:
    """The ``k = 8`` tests of one stream (five identifier positions and the cluster on its distinct
    facts; template and record index on its records), Bonferroni-corrected within the stream."""
    gen = _gen(seed, "permutation", stream.name)
    flat = stream.fact_ids.reshape(-1)
    facts = torch.unique(flat)
    fact_tests = independence_tests(
        table.answer[facts],
        [(f"identifier_{p + 1}", table.ident[facts, p]) for p in range(5)]
        + [("cluster", table.cluster[facts])],
        permutations,
        gen,
    )
    record_tests = independence_tests(
        table.answer[flat],
        [
            ("template", stream.template.repeat_interleave(core.RECORDS_PER_CONTEXT)),
            ("record_index", torch.arange(core.RECORDS_PER_CONTEXT).repeat(stream.fact_ids.shape[0])),
        ],
        permutations,
        gen,
    )
    tests = fact_tests + record_tests
    k = len(tests)
    for t in tests:
        t["p_adjusted"] = min(1.0, k * t["p"])
    smallest = min(t["p_adjusted"] for t in tests)
    return _check(
        "independence",
        stream.name,
        k == core.G1_TESTS_PER_STREAM and smallest >= core.G1_P_THRESHOLD,
        k=k,
        permutations=permutations,
        smallest_adjusted_p=smallest,
        threshold=core.G1_P_THRESHOLD,
        tests=tests,
    )


def _expected_counts(name: str, table: FactTable, stream: Stream) -> torch.Tensor:
    passes = 2 if name == "calibration" else 1
    counts = torch.zeros(table.size, dtype=torch.int64)
    if name.startswith("lane_d"):  # one set of the Lane D world, once
        half = table.trained // 2
        lo = 0 if name.endswith("_A") else half
        counts[lo : lo + half] = 1
    elif name in ("calibration", "h1", "h2", "mixed"):
        counts[: table.trained] = passes
    else:  # panels: trained once, unseen once
        counts[:] = 1
    return counts


def _stream_checks(stream: Stream, table: FactTable, templates: TemplateSplit) -> list[G1Check]:
    out: list[G1Check] = []
    name = stream.name
    counts = torch.bincount(stream.fact_ids.reshape(-1), minlength=table.size)
    expected = _expected_counts(name, table, stream)
    out.append(
        _check(
            "coverage",
            name,
            bool((counts == expected).all()),
            facts_expected=int((expected > 0).sum()),
            count_min=int(counts[expected > 0].min()),
            count_max=int(counts.max()),
            exact=bool((counts == expected).all()),
        )
    )
    # layout: bytes at the contract's positions
    c = stream.fact_ids.shape[0]
    sep, bind = templates.tensors(stream.template_set)
    rec = stream.tokens.reshape(c, 8, 8)
    layout = (
        bool((rec[:, :, 0] == sep[stream.template][:, None]).all())
        and bool((rec[:, :, 6] == bind[stream.template][:, None]).all())
        and bool((rec[:, :, 1:6] == _ALPHABET[table.ident[stream.fact_ids]]).all())
        and bool((rec[:, :, 7] == _ALPHABET[table.answer[stream.fact_ids]]).all())
        and bool((stream.answer_targets() == table.answer[stream.fact_ids]).all())
        and stream.tokens.shape == (c, core.CONTEXT_BYTES)
        and stream.sha256 == stream_sha256(stream)
    )
    out.append(_check("layout", name, layout, contexts=c, answer_site_positions=list(core.ANSWER_SITE_POSITIONS)))
    # cluster rule and distinct facts (a record never precedes its own answer site)
    ids = stream.fact_ids
    srt = ids.sort(dim=1).values
    distinct = bool((srt[:, 1:] != srt[:, :-1]).all())
    cl = table.cluster[ids]
    if name == "mixed":
        cluster_rule = bool((cl.sort(dim=1).values[:, 1:] != cl.sort(dim=1).values[:, :-1]).all())
    else:
        unseen = (ids >= table.trained).all(dim=1)
        same = (cl == cl[:, :1]).all(dim=1)
        cluster_rule = bool((same | unseen).all()) and bool(((ids >= table.trained).all(dim=1) | (ids < table.trained).all(dim=1)).all())
    out.append(
        _check(
            "context_rules",
            name,
            distinct and cluster_rule,
            distinct_facts_per_context=distinct,
            cluster_rule=cluster_rule,
            rule="8 distinct clusters" if name == "mixed" else "8 distinct facts of one cluster (or all unseen)",
        )
    )
    return out


def _training_schedules(data: StudyData) -> dict[str, TrainingStream]:
    seed = data.seeds.training_order
    out: dict[str, TrainingStream] = {}
    trained = data.facts.trained
    for size in sorted({min(trained, f) for f in core.FACTS_PROPORTIONAL.values()}):
        out[f"main_{size}"] = make_training_stream(
            data.facts, torch.arange(size), data.templates, _derive(seed, "main")
        )
    for which in ("A", "B", "AB"):
        out[f"lane_d_{which}"] = make_training_stream(
            data.lane_d,
            _lane_d_ids(data, which),
            data.templates,
            _derive(seed, "lane_d", which if which != "AB" else "AB"),
        )
    return out


def _registered_epochs(facts: int) -> int:
    """Epochs of the longest registered run of a schedule over ``facts`` facts (E = 128, run length
    ``max(F, U_16K)`` updates for the main world)."""
    updates = max(facts, core.fixed_compute_updates(core.EXPOSURE_MENU[-1]))
    return updates * core.ANSWER_SITES_PER_BATCH // facts


def run_g1(
    data: StudyData,
    *,
    permutations: int | None = None,
    train_epochs: int | None = None,
    only_streams: Collection[str] | None = None,
) -> G1Report:
    """Run gate G1 on every stream of ``data`` (ADR 4.6). ``permutations`` overrides the registered
    ``2000 k`` per test, ``train_epochs`` the registered horizon of the training-contexts check, and
    ``only_streams`` restricts the per-stream checks (all three for tests only)."""
    k = core.G1_TESTS_PER_STREAM
    perms = core.G1_PERMUTATIONS_PER_TEST if permutations is None else permutations
    checks: list[G1Check] = [_table_checks(data.facts), _table_checks(data.lane_d)]
    disjoint = not bool(
        torch.isin(encode_identifiers(data.facts.ident), encode_identifiers(data.lane_d.ident)).any()
    )
    checks.append(_check("identifiers_disjoint_worlds", None, disjoint))
    names = sorted(data.streams) if only_streams is None else sorted(only_streams)
    tables = {WORLD_MAIN: data.facts, WORLD_LANE_D: data.lane_d}
    tests_per_stream: dict[str, int] = {}
    for name in names:
        stream = data.streams[name]
        table = tables[stream.world]
        checks += _stream_checks(stream, table, data.templates)
        checks.append(stream_independence(stream, table, perms, data.seeds.permutation_tests))
        tests_per_stream[name] = k
    # equal frequency of every training schedule, and no evaluation context in training
    schedules = _training_schedules(data)
    train_keys: dict[str, torch.Tensor] = {}
    for sname, sched in schedules.items():
        epochs = train_epochs if train_epochs is not None else _registered_epochs(sched.facts.shape[0])
        expo = sched.exposures(epochs * sched.updates_per_epoch)
        extra = min(3, sched.updates_per_epoch - 1)
        part = sched.exposures(epochs * sched.updates_per_epoch + extra) - expo
        checks.append(
            _check(
                "equal_frequency",
                sname,
                bool((expo == epochs).all()) and int(part.max()) <= 1 and int(part.min()) >= 0,
                facts=int(sched.facts.shape[0]),
                epochs=epochs,
                exposures_min=int(expo.min()),
                exposures_max=int(expo.max()),
            )
        )
        train_keys[sname] = sched.keys(epochs)
    for name in names:
        stream = data.streams[name]
        world_prefix = "lane_d" if stream.world == WORLD_LANE_D else "main"
        keys = context_keys(stream.fact_ids)
        hits = {
            sname: int(torch.isin(keys, tk).sum())
            for sname, tk in train_keys.items()
            if sname.startswith(world_prefix)
        }
        checks.append(
            _check(
                "panel_not_in_training",
                name,
                sum(hits.values()) == 0,
                stream_context_keys=int(keys.numel()),
                hits_by_schedule=hits,
                training_keys_checked={s: int(t.numel()) for s, t in train_keys.items()},
            )
        )
    checks.append(_dictionary_check(data))
    checks.append(_seed_check(data.seeds))
    return {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "tests_per_stream": tests_per_stream,
    }


def _dictionary_check(data: StudyData) -> G1Check:
    from . import controls  # lazy: controls imports this module

    stream = data.streams["panel_a"]
    scores = controls.exact_retrieval(data.facts, stream, torch.arange(data.facts.trained))
    seen = (stream.fact_ids < data.facts.trained).reshape(-1)
    answers = data.facts.answer[stream.fact_ids.reshape(-1)]
    trained_ok = bool(scores.correct[seen].all())
    chance_matches = int((answers[~seen] == 0).sum())
    unseen_correct = int(scores.correct[~seen].sum())
    return _check(
        "dictionary_lookup",
        "panel_a",
        trained_ok and unseen_correct == chance_matches,
        trained_accuracy=float(scores.correct[seen].float().mean()),
        unseen_correct=unseen_correct,
        unseen_chance_matches=chance_matches,
    )


def _seed_check(seeds: SeedSet) -> G1Check:
    registered = core.registered_seed_values()
    values = [*seeds.data_values(), *seeds.null_seeds_a, *seeds.null_seeds_b]
    if seeds.name == "registered":
        ok = seeds == core.registered_seeds()
        return _check("seeds_disjoint", None, ok, seed_set=seeds.name, registered=True)
    ok = all(v >= core.REHEARSAL_SEED_BASE and v not in registered for v in values)
    return _check("seeds_disjoint", None, ok, seed_set=seeds.name, registered=False)
