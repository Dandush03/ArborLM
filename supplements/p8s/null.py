# ruff: noqa: E501
"""ADR-0016 section 3: the single-set precondition detector and the identity null provider.

The precondition is checked on the trace rows (after ``p8_sim.load_trace``): exactly eight slots
have a non-zero count and each of those counts equals Q. When it holds, each null replicate is the
stream of Q rows, every row being the set S in ascending slot-ID order (unique as a sequence of
sets, ADR-0016 proofs 1 and 2). When it does not hold, the registered generator is called unchanged.

The replicate seed and generator seed of the registered rule are recorded, not consumed.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor

from arborlm import p7a_core as a_core
from arborlm import p7b_core as b_core
from arborlm import p8_core as core
from arborlm.io import sha256

IDENTITY_METHOD = "single-set identity null (ADR-0016 §3)"
TOP = core.TOP  # 8

NullProvider = Callable[[Tensor, tuple[int, ...], int], tuple[list[Tensor], list[dict[str, Any]]]]


@dataclass(frozen=True)
class Precondition:
    holds: bool
    queries: int
    nonzero_slots: int
    slots: tuple[int, ...]  # S, ascending; empty unless the precondition holds
    reasons: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "holds": self.holds,
            "queries": self.queries,
            "nonzero_slots": self.nonzero_slots,
            "slots": list(self.slots),
            "reasons": list(self.reasons),
        }


def precondition_from_counts(counts: list[int], queries: int) -> Precondition:
    """Counts clause: exactly 8 slots with non-zero count, each equal to ``queries``, and the
    total equal to 8 x ``queries``."""
    nonzero = [i for i, c in enumerate(counts) if c]
    reasons: list[str] = []
    if len(nonzero) != TOP:
        reasons.append(f"{len(nonzero)} slots have a non-zero count, expected {TOP}")
    below = [i for i in nonzero if counts[i] != queries]
    if below:
        reasons.append(f"{len(below)} non-zero counts differ from Q={queries}")
    if sum(counts) != TOP * queries:
        reasons.append(f"counts sum to {sum(counts)}, expected {TOP * queries}")
    if queries <= 0:
        reasons.append("no queries")
    ok = not reasons
    return Precondition(ok, queries, len(nonzero), tuple(nonzero) if ok else (), tuple(reasons))


def detect_single_set(selected: Tensor) -> Precondition:
    """The precondition on a trace's rows ``[Q, 8]``: the counts clause, then the redundant direct
    assertion that every query's slot set is S."""
    if selected.dim() != 2 or int(selected.shape[1]) != TOP:
        return Precondition(
            False, 0, 0, (), (f"trace has shape {tuple(selected.shape)}, expected [Q, {TOP}]",)
        )
    queries = int(selected.shape[0])
    pre = precondition_from_counts(a_core.selection_counts(selected), queries)
    if not pre.holds:
        return pre
    expected = torch.tensor(pre.slots, dtype=torch.int64).expand(queries, TOP)
    rows = selected.to(torch.int64).sort(dim=1).values
    if not bool((rows == expected).all()):
        return Precondition(
            False,
            queries,
            pre.nonzero_slots,
            (),
            ("redundant direct check failed: some query's slot set is not S",),
        )
    return pre


def identity_stream(slots: tuple[int, ...], queries: int) -> Tensor:
    """Q rows, each S in ascending slot-ID order (int64 ``[Q, 8]``)."""
    if len(slots) != TOP or list(slots) != sorted(set(slots)):
        raise ValueError("S must be eight distinct slots")
    return torch.tensor(slots, dtype=torch.int64).repeat(queries, 1)


def check_null_stream(stream: Tensor, counts: list[int]) -> None:
    """The registered hard-stop checks of ``frequency_matched_detail``: every query holds eight
    distinct slots and every per-slot count equals the trace's. Raises ``InvariantError``."""
    realized = [0] * len(counts)
    for row in stream.tolist():
        if len(set(row)) != TOP:
            raise a_core.InvariantError("identity null: a query lacks distinct slots")
        for slot in row:
            realized[slot] += 1
    if realized != counts:
        raise a_core.InvariantError("identity null: per-slot counts differ from the trace's")


def stream_sha256(stream: Tensor) -> str:
    """``sha256(p7a_core._pack(stream, "h"))``: little-endian int16, C order."""
    return sha256(a_core._pack(stream, "h"))


def registered_null_provider(
    selected: Tensor, seeds: tuple[int, ...], index: int
) -> tuple[list[Tensor], list[dict[str, Any]]]:
    """The registered generator, unchanged (``p7b_core.null_streams``), with the info records
    annotated ``precondition: False``. This is the only call to the generator."""
    counts = a_core.selection_counts(selected)
    streams, info = b_core.null_streams(counts, seeds, index)
    return streams, [{**d, "precondition": False} for d in info]


def supplement_null_provider(
    selected: Tensor, seeds: tuple[int, ...], index: int
) -> tuple[list[Tensor], list[dict[str, Any]]]:
    """ADR-0016 section 3: the identity null when the precondition holds on this panel trace,
    otherwise the registered generator (which may raise; the cell then has no record)."""
    pre = detect_single_set(selected)
    if not pre.holds:
        return registered_null_provider(selected, seeds, index)
    counts = a_core.selection_counts(selected)
    stream = identity_stream(pre.slots, pre.queries)
    check_null_stream(stream, counts)
    digest = stream_sha256(stream)
    info = [
        {
            "method": IDENTITY_METHOD,
            "replicate_seed": seed,
            "generator_seed": a_core.fm_generator_seed(seed, index),
            "stream_sha256": digest,
            "precondition": True,
        }
        for seed in seeds
    ]
    return [stream.clone() for _ in seeds], info
