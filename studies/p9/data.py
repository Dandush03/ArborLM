# ruff: noqa: E501
"""P9 task data (package I1): alphabet, checksum identifiers, facts, clusters, templates, streams and
panels, Lane D sets, hashing, the G1 generator checks and the rehearsal seed namespace.

Specification: ADR-0017 section 4 (task and data), 4.6 (gate G1), 5.5 (training order and exposure) and
10 (data seeds). STUB: public signatures and dataclasses only; every function body raises
``NotImplementedError`` until package I1 implements it.

Data flow: ``build_study_data`` (needs the training-corpus bytes only for the template pool) produces a
``StudyData``. ``training_stream_for`` turns it into the ``TrainingStream`` of one cell; its ``batch(u)``
is a pure function of the update index, so a restored snapshot resumes the exact schedule. Panels and
the calibration stream are fixed ``Stream`` objects read by ``controls`` and ``evaluate``.

Conventions (see ``core``): a context is 64 bytes, model input = bytes 0..62, targets = bytes 1..63,
record ``r`` = bytes 8r..8r+7, answer site = input position 8r+6, target byte 8r+7. Symbols are indices
0..31 into ``core.ALPHABET``; token tensors hold byte values (int64).
"""

from collections.abc import Collection
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict

from .core import Cell, SeedSet

if TYPE_CHECKING:
    from torch import Tensor

WORLD_MAIN, WORLD_LANE_D = "main", "lane_d"
TEMPLATE_SETS = ("T", "H1", "H2")


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
        raise NotImplementedError


@dataclass
class FactTable:
    """A world of facts. ``ident [F, 5] int64`` symbol indices (the first four uniform, the fifth the
    sum modulo 32); ``answer [F] int64`` symbol index; ``cluster [F] int64`` cluster id of 16 facts
    (-1 for unseen controls). The first ``trained`` rows are trainable facts; the rest are unseen
    controls with random answers (ADR 4.1). Identifiers are unique within a world, and the main and
    Lane D worlds use disjoint identifiers (core.OPEN_CHOICES c04)."""

    world: str
    ident: "Tensor"
    answer: "Tensor"
    cluster: "Tensor"
    trained: int

    @property
    def size(self) -> int:
        raise NotImplementedError


@dataclass
class Stream:
    """Fixed contexts of one stream. ``tokens [C, 64] int64`` bytes; ``fact_ids [C, 8] int64`` fact id
    of each record in the stream's ``world`` table (ids >= ``trained`` are unseen controls);
    ``cluster [C] int64`` (-1 when the context mixes clusters or holds unseen facts); ``template [C]
    int64`` index into ``TemplateSplit.of(template_set)``. ``sha256`` hashes the tensors (ADR 4.4)."""

    name: str
    world: str
    template_set: str
    tokens: "Tensor"
    fact_ids: "Tensor"
    cluster: "Tensor"
    template: "Tensor"
    sha256: str

    def answer_targets(self) -> "Tensor":
        """``[C, 8] int64`` answer symbol indices of the records (the target of each answer site)."""
        raise NotImplementedError


@dataclass
class Batch:
    """One training batch: ``tokens [16, 64] int64``, ``fact_ids [16, 8] int64``, ``cluster [16]``,
    ``template [16]`` (replay arms add 16 replayed contexts in ``replay_*``, else None)."""

    tokens: "Tensor"
    fact_ids: "Tensor"
    cluster: "Tensor"
    template: "Tensor"
    replay_tokens: "Tensor | None" = None
    replay_fact_ids: "Tensor | None" = None


class TrainingStream:
    """Deterministic training schedule over a fact subset (ADR 4.3, 5.5).

    Each epoch visits the clusters in seeded order and each cluster as two contexts of 8 distinct facts
    in seeded order, so every fact appears exactly once per epoch (``len(facts) / 128`` updates per
    epoch). ``batch(update)`` is a pure function of the 1-based update index (no hidden state)."""

    facts: "Tensor"

    def batch(self, update: int) -> Batch:
        """Batch for 1-based ``update``: 16 contexts of 8 facts (plus 16 replay contexts if the
        stream was built with replay ids)."""
        raise NotImplementedError

    def exposures(self, updates: int) -> "Tensor":
        """``[len(facts)] int64`` times each fact has been an answer site after ``updates`` updates."""
        raise NotImplementedError


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
        raise NotImplementedError


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


def build_study_data(seeds: SeedSet, corpus: bytes) -> StudyData:
    """Generate the whole draw. ``corpus`` is ``core.load_trained_corpus(...)`` (used only through
    ``core.derive_template_pool``; its result must equal ``core.TEMPLATE_POOL`` for registered use).
    Deterministic in ``seeds``; ADR 4.1-4.4."""
    raise NotImplementedError


def make_fact_table(
    seed: int, trained: int, unseen: int, *, exclude: Collection[int] = (), cluster_seed: int
) -> FactTable:
    """Unique identifiers (four uniform symbols plus checksum, never in ``exclude`` = encoded
    identifiers already used), uniform independent answers, clusters of 16 (ADR 4.1, 4.3)."""
    raise NotImplementedError


def encode_identifiers(ident: "Tensor") -> "Tensor":
    """``[F, 5] int64`` symbols -> ``[F] int64`` code ``sum(symbol_i * 32**i, i < 4)`` (< 32**4)."""
    raise NotImplementedError


def identifier_lut(table: FactTable, fact_ids: "Tensor") -> "Tensor":
    """``[32**4] int64`` lookup: encoded identifier -> position in ``fact_ids`` (the R2 slot index of
    that fact), -1 elsewhere. Passed to ``model.build_model`` for the R2 rung."""
    raise NotImplementedError


def split_templates(pool: tuple[int, ...], seed: int) -> TemplateSplit:
    """Split the 48-byte pool by seed as in ``core.OPEN_CHOICES['c03_template_split']``."""
    raise NotImplementedError


def make_training_stream(
    table: FactTable,
    fact_ids: "Tensor",
    templates: TemplateSplit,
    order_seed: int,
    *,
    replay_ids: "Tensor | None" = None,
) -> TrainingStream:
    """Schedule over ``fact_ids`` (``[F] int64`` ids in ``table``) with training templates T.
    ``replay_ids`` (a replayed set, Lane D) adds one replayed context per training context."""
    raise NotImplementedError


def make_stream(
    name: str,
    table: FactTable,
    fact_ids: "Tensor",
    templates: TemplateSplit,
    template_set: str,
    seed: int,
    *,
    passes: int = 1,
    mixed_clusters: bool = False,
    avoid_context_keys: Collection[bytes] = (),
) -> Stream:
    """Fixed stream: every fact ``passes`` times in contexts whose fact set is not in
    ``avoid_context_keys`` (``context_key`` of each training context), a fact's own record never
    earlier in its context than its answer site is read (ADR 4.3). ``mixed_clusters`` draws the 8 facts
    from 8 different clusters."""
    raise NotImplementedError


def context_key(fact_ids: "Tensor") -> bytes:
    """Hash of the unordered fact set of one context (``[8] int64``); used to keep panel contexts out
    of training (ADR 4.4)."""
    raise NotImplementedError


def training_stream_for(data: StudyData, cell: Cell) -> TrainingStream:
    """The schedule of ``cell``: main world facts ``0..cell.facts-1``; Lane D: phaseA/sequential/
    memory_only/replay use set A (phaseA) or B (phase B; replay adds set A), joint uses A then B."""
    raise NotImplementedError


def facts_of(data: StudyData, cell: Cell) -> "Tensor":
    """``[cell.facts] int64`` ids of the cell's trained facts in its world (the R2 slot order)."""
    raise NotImplementedError


def panel_streams(data: StudyData, cell: Cell, panel: str) -> list[Stream]:
    """Streams on which ``cell`` is evaluated for ``panel`` in {A, B}: the primary panel (trained
    facts and unseen-control contexts); for Lane D cells the A and B panels of each set."""
    raise NotImplementedError


def neighbour_flags(table: FactTable) -> "Tensor":
    """``[F] bool``: the fact has another fact whose identifier differs in at most two positions
    (accuracy is reported separately with and without such a neighbour, ADR 4.1)."""
    raise NotImplementedError


def stream_sha256(stream: Stream) -> str:
    raise NotImplementedError


def run_g1(data: StudyData, *, permutations: int | None = None) -> G1Report:
    """Run gate G1 on every stream of ``data`` (ADR 4.6). ``permutations`` overrides the registered
    ``2000 k`` for tests only."""
    raise NotImplementedError
