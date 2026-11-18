# ruff: noqa: E501
"""The shared P10-I panel ledger in byte spans (ADR-0025 section 4.1, "GEN windows and the shared panel ledger"; rulings G18, C13).

A window is recorded by its start and end byte offsets in the validation text concatenated as ADR-0022's ruling A-B3 defines (rows in file order, nothing between them), with its first and last row. End
offsets are EXCLUSIVE. Two spans overlap if they share at least one byte of that concatenated text. A window covering several rows has ONE span, from the first byte of its first token to the last byte of
its last token. The row <-> concatenated-offset map is the cumulative UTF-8 byte length of the rows. This module does arithmetic on integers only: no tokenizer, no text file, no teacher.

THE LEDGER FILE (stable; the longer-training study READS it, so none of this changes without a recorded decision). One JSON object, written by ``write_ledger``::

    {"format": "p10i-panel-ledger/1",
     "end_exclusive": true,
     "unit": "byte offsets in the concatenation of the rows of the WikiText-2 validation parquet file, rows in file order, nothing between them (ADR-0022 ruling A-B3)",
     "windows": [{"start": int, "end": int, "first_row": int, "last_row": int, "kind": "marker" | "ordinary" | <another study's label>, "owner": str,
                  "per_row": [[row, start_in_row, end_in_row], ...]}, ...],     # per_row only when the writer had the row map; ends exclusive
     "owner": str, "check": {...}, "ordinary_eligible": int, "row_bytes_sha256": str | null,
     "kind": "panel_ledger", "schema": 1, "study": "P10IS2", "part": "Q", "oracle_line": "..."}   # the study envelope

Another study that adds its panel spans appends objects with the same four required keys ``start``, ``end``, ``first_row``, ``last_row`` to ``windows`` and its own ``owner``; a reader needs only those four.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import accumulate
from typing import Any

import torch


class SpanError(ValueError):
    """A span or a row map that violates the ledger's conventions."""


@dataclass(frozen=True)
class Span:
    start: int  # first byte, inclusive
    end: int  # one past the last byte (exclusive)
    first_row: int
    last_row: int
    kind: str = "ordinary"  # "marker" | "ordinary" | another study's label
    owner: str = ""

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise SpanError(f"a span needs 0 <= start < end (end exclusive): {self.start}, {self.end}")
        if self.first_row < 0 or self.last_row < self.first_row:
            raise SpanError(f"a span needs 0 <= first_row <= last_row: {self.first_row}, {self.last_row}")

    def to_json(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "first_row": self.first_row, "last_row": self.last_row, "kind": self.kind, "owner": self.owner}

    @staticmethod
    def from_json(d: Mapping[str, Any]) -> "Span":
        return Span(int(d["start"]), int(d["end"]), int(d["first_row"]), int(d["last_row"]), str(d.get("kind", "ordinary")), str(d.get("owner", "")))


def overlap(a: Span, b: Span) -> bool:
    """True if the spans share at least one byte (both ends exclusive: [0, 5) and [5, 9) share none)."""
    return a.start < b.end and b.start < a.end


class RowMap:
    """Cumulative byte length of the rows, nothing between them: ``starts[r]`` is the offset of row r's first byte, ``total`` the length of the concatenation."""

    def __init__(self, row_bytes: Sequence[int]) -> None:
        if any(n < 0 for n in row_bytes):
            raise SpanError("a row cannot have a negative length")
        self.row_bytes = tuple(int(n) for n in row_bytes)
        self.starts = (0, *accumulate(self.row_bytes))[:-1] if self.row_bytes else ()
        self.total = int(sum(self.row_bytes))

    @staticmethod
    def from_rows(rows: Iterable[str]) -> "RowMap":
        return RowMap([len(r.encode("utf-8")) for r in rows])

    def offset(self, row: int, byte_in_row: int) -> int:
        """The concatenated offset of byte ``byte_in_row`` of ``row`` (``byte_in_row`` may equal the row's length: the position just after its last byte)."""
        if not 0 <= row < len(self.row_bytes):
            raise SpanError(f"row {row} is outside the {len(self.row_bytes)} rows")
        if not 0 <= byte_in_row <= self.row_bytes[row]:
            raise SpanError(f"byte {byte_in_row} is outside row {row} of {self.row_bytes[row]} bytes")
        return self.starts[row] + byte_in_row

    def row_of(self, offset: int) -> int:
        """The row holding the byte at ``offset`` (the first row whose range contains it; zero-length rows hold no byte)."""
        if not 0 <= offset < self.total:
            raise SpanError(f"offset {offset} is outside the {self.total} bytes")
        lo, hi = 0, len(self.row_bytes) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        # skip back over a zero-length row that shares the start offset
        while lo < len(self.row_bytes) and self.row_bytes[lo] == 0:
            lo += 1
        return lo

    def span(self, first_row: int, first_byte: int, last_row: int, last_byte_exclusive: int, kind: str = "ordinary", owner: str = "") -> Span:
        """One span for a window from byte ``first_byte`` of ``first_row`` to the byte before ``last_byte_exclusive`` of ``last_row``."""
        return Span(self.offset(first_row, first_byte), self.offset(last_row, last_byte_exclusive), first_row, last_row, kind, owner)


def per_row_spans(span: Span, rows: RowMap) -> list[tuple[int, int, int]]:
    """The conversion to per-row spans: ``(row, start_in_row, end_in_row)`` with exclusive ends, one entry per row the span touches, rows with no byte in the span omitted."""
    out: list[tuple[int, int, int]] = []
    for r in range(span.first_row, span.last_row + 1):
        lo, hi = rows.starts[r], rows.starts[r] + rows.row_bytes[r]
        a, b = max(span.start, lo), min(span.end, hi)
        if a < b:
            out.append((r, a - lo, b - lo))
    covered = sum(b - a for _, a, b in out)
    if covered != span.end - span.start:
        raise SpanError("the span's bytes are not covered by the rows it names")
    return out


def char_to_byte_offsets(text: str) -> list[int]:
    """``out[i]`` is the UTF-8 byte offset of character ``i`` (``out[len(text)]`` the total length): the conversion of a window found in characters to bytes."""
    return [0, *accumulate(len(c.encode("utf-8")) for c in text)]


class PanelLedger:
    """The ledger as one list of spans. Another study's panel spans (ADR-0026's) may already be in it at the Part Q freeze; the 44 marker-like windows go in whatever they overlap (the marker-like stratum is
    every such window and cannot give any up); the 100 ordinary windows are sampled only from windows overlapping no span already there."""

    def __init__(self, spans: Iterable[Span] = ()) -> None:
        self.spans: list[Span] = list(spans)

    def add(self, span: Span) -> None:
        self.spans.append(span)

    def overlapping(self, span: Span) -> list[Span]:
        return [s for s in self.spans if overlap(s, span)]

    def eligible_ordinary(self, candidates: Sequence[Span]) -> list[Span]:
        """The candidates (ordinary windows) overlapping no span in the ledger now: step 2 of section 4.1 counts these."""
        return [c for c in candidates if not self.overlapping(c)]

    def sample_ordinary(self, candidates: Sequence[Span], n: int, generator: torch.Generator) -> list[Span]:
        """100 ordinary windows from the eligible ones: one seeded permutation of the eligible list (in candidate order), the first ``n``, returned in candidate order. Fewer than ``n`` eligible raises."""
        pool = self.eligible_ordinary(candidates)
        if len(pool) < n:
            raise SpanError(f"only {len(pool)} ordinary windows overlap no recorded span; {n} are needed (DATA-INSUFFICIENT, section 4.1 step 2)")
        order = torch.randperm(len(pool), generator=generator).tolist()[:n]
        return [pool[i] for i in sorted(order)]

    def to_record(self) -> list[dict[str, Any]]:
        return [s.to_json() for s in self.spans]

    @staticmethod
    def from_record(rows: Sequence[Mapping[str, Any]]) -> "PanelLedger":
        return PanelLedger(Span.from_json(r) for r in rows)

    def check_own_panel(self, owner: str, marker_like: int, ordinary: int) -> dict[str, Any]:
        """The Part Q freeze's own check: ``marker_like`` + ``ordinary`` windows of ``owner``, no two overlapping each other, and no ordinary window overlapping any other owner's span."""
        mine = [s for s in self.spans if s.owner == owner]
        counts = {"marker": sum(1 for s in mine if s.kind == "marker"), "ordinary": sum(1 for s in mine if s.kind == "ordinary")}
        self_overlaps = sum(1 for i, a in enumerate(mine) for b in mine[i + 1 :] if overlap(a, b))
        foreign = sum(1 for s in mine if s.kind == "ordinary" and any(overlap(s, o) for o in self.spans if o.owner != owner))
        ok = counts == {"marker": marker_like, "ordinary": ordinary} and self_overlaps == 0 and foreign == 0
        return {"ok": ok, "counts": counts, "self_overlaps": self_overlaps, "ordinary_overlapping_other_owners": foreign}


LEDGER_FORMAT = "p10i-panel-ledger/1"


def write_ledger(path: "Any", led: PanelLedger, owner: str, check: Mapping[str, Any], eligible: int, rows: RowMap | None = None) -> None:
    """Writes the ledger file in the stable format of this module's docstring (overwrites: the ledger grows as studies add their panels)."""
    from arborlm.io import canonical_json, sha256

    from . import core

    windows = []
    for s in led.spans:
        w = s.to_json()
        if rows is not None and s.end <= rows.total:
            w["per_row"] = [list(t) for t in per_row_spans(s, rows)]
        windows.append(w)
    rec = {
        **core.envelope("panel_ledger", "Q"), "format": LEDGER_FORMAT, "end_exclusive": True, "windows": windows, "owner": owner, "check": dict(check), "ordinary_eligible": eligible,
        "unit": "byte offsets in the concatenation of the rows of the WikiText-2 validation parquet file, rows in file order, nothing between them (ADR-0022 ruling A-B3)",
        "row_bytes_sha256": None if rows is None else sha256(canonical_json(list(rows.row_bytes))),
    }  # fmt: skip
    core.write_record(path, rec, overwrite=True)
