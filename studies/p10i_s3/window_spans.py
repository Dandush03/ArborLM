# ruff: noqa: E501
"""P10IS3 excluded spans (ADR-0026 section 4, review correction C7; ADR-0025 section 4.1): the byte spans this study's panels must avoid.

* P10-S2's GEN windows: the 44 marker-like windows of the fixed grid (all taken) and the 100 ordinary windows it sampled with the GEN-window seed (the ``gen_windows`` partition stream of ``configs/p10s2_transfer.toml``,
  a fresh ``torch.Generator`` seeded directly; one ``randperm`` of the marker-like pool, then one of the ordinary pool, ``sorted(order[:100])``, as ``studies/p10s2/windows.select_windows`` does).
* ADR-0025's windows: its 44 marker-like windows are the same text-determined windows (fixed grid, ADR-0022 section 6.4), so they are computed here from the validation text alone and have priority whichever study
  freezes first. Its 100 sampled ordinary windows are drawn after this study's panels if this study freezes first; if the shared ledger exists they are read from it (``read_ledger``).

Coordinates: the validation text is the parquet ``text`` column concatenated in file order with nothing between rows (ADR-0022 ruling A-B3). A window span runs from the first byte of its first token to the last byte
of its last token; END OFFSETS ARE EXCLUSIVE; two spans overlap if they share at least one byte. ``to_row_spans`` converts a concatenated span into per-row spans ``(row, start, end)`` in the row's own bytes,
the form the panel walk compares (a chunk is ``(row, offset, offset + 65)``).

This module re-implements the grid and the strata (it does not import ``studies/p10s2``; a test compares it with ``studies.p10s2.windows`` on a stand-in tokenizer). The tokenizer is injected: anything with
``encode_offsets(text) -> (ids, [(char_start, char_end)])``. Nothing here reads the real corpus; the ``window-spans`` command does, and it is the lead's to run.
"""

import bisect
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

import torch

from .core import EngineeringStop

Span = tuple[int, int, int]
LEDGER_FORMAT = "p10i-panel-ledger-v1"


class OffsetTokenizer(Protocol):
    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]: ...


class RowLayout:
    """Cumulative byte layout of the rows as stored: ``starts[i]`` is the concatenated byte offset of row i."""

    def __init__(self, rows: Sequence[str]) -> None:
        lengths = [len(r.encode("utf-8")) for r in rows]
        self.starts = [0]
        for n in lengths:
            self.starts.append(self.starts[-1] + n)
        self.lengths = lengths

    @property
    def total(self) -> int:
        return self.starts[-1]

    def row_of(self, byte: int) -> int:
        """The row holding concatenated byte ``byte`` (rows of length 0 hold no byte)."""
        if not 0 <= byte < self.total:
            raise ValueError("byte outside the text")
        return bisect.bisect_right(self.starts, byte) - 1

    def to_row_spans(self, start: int, end: int) -> list[Span]:
        """A concatenated span [start, end) as per-row spans (row, start_in_row, end_in_row), one per row it touches."""
        if not 0 <= start < end <= self.total:
            raise ValueError("an empty or out-of-range span")
        out: list[Span] = []
        for r in range(self.row_of(start), self.row_of(end - 1) + 1):
            lo, hi = max(start, self.starts[r]), min(end, self.starts[r + 1])
            if lo < hi:
                out.append((r, lo - self.starts[r], hi - self.starts[r]))
        return out

    def from_row_span(self, row: int, start: int, end: int) -> tuple[int, int]:
        return self.starts[row] + start, self.starts[row] + end


def char_to_byte(text: str) -> list[int]:
    """``out[i]`` is the byte offset of character i (``out[len(text)]`` the total)."""
    out = [0]
    for ch in text:
        out.append(out[-1] + len(ch.encode("utf-8")))
    return out


def marker_strings(cfg_s2: Mapping[str, Any]) -> list[str]:
    d = cfg_s2["data"]
    return [*d["marker_strings"], d["marker_line_ending"] + "\n"]


def _first_marker(text: str, markers: Sequence[str]) -> bool:
    return any(m in text for m in markers)


def grid_windows(offsets: Sequence[tuple[int, int]], text: str, window: int, decision: int, markers: Sequence[str]) -> list[dict[str, Any]]:
    """The fixed grid of ADR-0022 section 6.4: consecutive non-overlapping windows of ``window`` tokens from the first token, a trailing remainder dropped. A window is marker-like if one of the strings lies wholly
    within the text of its tokens 1-``decision``; ordinary if it contains none anywhere; otherwise it is in neither stratum. Returns the window index, the stratum and the character span (first byte of its first token
    to the last byte of its last token)."""
    out = []
    for w0 in range(0, len(offsets) - window + 1, window):
        head = text[offsets[w0][0] : offsets[w0 + decision - 1][1]]
        allt = text[offsets[w0][0] : offsets[w0 + window - 1][1]]
        if _first_marker(head, markers):
            stratum = "marker"
        elif not _first_marker(allt, markers):
            stratum = "ordinary"
        else:
            continue
        out.append({"index": w0 // window, "stratum": stratum, "char_start": offsets[w0][0], "char_end": offsets[w0 + window - 1][1]})
    return out


def sample_ordinary(pool_size: int, n: int, marker_pool_size: int, seed: int) -> list[int]:
    """P10-S2's draw: one fresh generator seeded directly; one permutation of the marker-like pool (taken whole, so nothing is used of it), then one of the ordinary pool; the sample is ``sorted(order[:n])``."""
    gen = torch.Generator().manual_seed(seed)
    torch.randperm(marker_pool_size, generator=gen)
    order = torch.randperm(pool_size, generator=gen).tolist()
    if pool_size < n:
        raise EngineeringStop(f"ENGINEERING STOP — {pool_size} ordinary windows on the grid, fewer than {n}")
    return sorted(order[:n])


def p10s2_windows(tok: OffsetTokenizer, rows: Sequence[str], cfg_s2: Mapping[str, Any]) -> dict[str, Any]:
    """Every window of P10-S2's GEN panel and the 44 marker-like windows ADR-0025 also takes, as concatenated byte spans [start, end) and per-row spans. The expected counts come from the P10-S2 configuration
    (44 marker-like, 100 ordinary); any other count is an engineering stop (the work returns to the lead; nothing is relaxed)."""
    text = "".join(rows)
    layout = RowLayout(rows)
    ids, offs = tok.encode_offsets(text)
    d = cfg_s2["data"]
    wins = grid_windows(offs, text, int(d["general_window_tokens"]), int(d["router_decision_token"]), marker_strings(cfg_s2))
    marker = [w for w in wins if w["stratum"] == "marker"]
    ordinary = [w for w in wins if w["stratum"] == "ordinary"]
    if len(marker) != int(d["general_windows_marker_like"]):
        raise EngineeringStop(f"ENGINEERING STOP — {len(marker)} marker-like windows on the fixed grid, the P10-S2 configuration states {d['general_windows_marker_like']}")
    seed = int(cfg_s2["seeds"]["partition_streams"][3])  # the gen_windows stream (the fourth of 220902..220912)
    picked = sample_ordinary(len(ordinary), int(d["general_windows_ordinary"]), len(marker), seed)
    c2b = char_to_byte(text)
    out: dict[str, Any] = {"layout_total_bytes": layout.total, "windows": [], "gen_window_seed_source": "configs/p10s2_transfer.toml seeds.partition_streams[3]"}
    for stratum, chosen in (("marker", marker), ("ordinary", [ordinary[i] for i in picked])):
        for w in chosen:
            s, e = c2b[w["char_start"]], c2b[w["char_end"]]
            out["windows"].append({"source": "P10-S2 GEN" if stratum == "ordinary" else "P10-S2 GEN and ADR-0025 marker-like", "stratum": stratum, "grid_index": w["index"], "start": s, "end": e, "first_row": layout.row_of(s), "last_row": layout.row_of(e - 1)})
    return out


# --- the shared panel ledger (ADR-0025 section 4.1) -----------------------------------------------------------------------------
def ledger_entry(layout: RowLayout, start: int, end: int, source: str) -> dict[str, Any]:
    return {"source": source, "start": start, "end": end, "first_row": layout.row_of(start), "last_row": layout.row_of(end - 1)}


def read_ledger(path: Path, layout: RowLayout) -> list[dict[str, Any]]:
    """Read the shared ledger: ``{"format": ..., "windows": [{"start", "end", "first_row", "last_row", ...}]}`` in concatenated bytes, end exclusive. Every entry's rows are checked against the layout. The format is this
    implementation's reading of ADR-0025 section 4.1 (Part Q does not exist yet; its plan names the path); a ledger of another shape is refused, never guessed."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("windows"), list):
        raise EngineeringStop(f"ENGINEERING STOP — {path} is not a panel ledger ('windows' list missing)")
    for w in data["windows"]:
        if not all(isinstance(w.get(k), int) for k in ("start", "end", "first_row", "last_row")) or not 0 <= w["start"] < w["end"] <= layout.total:
            raise EngineeringStop(f"ENGINEERING STOP — a ledger entry is malformed: {w!r}")
        if layout.row_of(w["start"]) != w["first_row"] or layout.row_of(w["end"] - 1) != w["last_row"]:
            raise EngineeringStop(f"ENGINEERING STOP — a ledger entry's rows do not match the row layout: {w!r}")
    return list(data["windows"])


def excluded_spans(layout: RowLayout, windows: Sequence[Mapping[str, Any]]) -> list[Span]:
    """Per-row spans of every window (concatenated bytes, end exclusive), sorted and without duplicates."""
    out: set[Span] = set()
    for w in windows:
        out.update(layout.to_row_spans(int(w["start"]), int(w["end"])))
    return sorted(out)


def build_excluded(rows: Sequence[str], windows_record: Mapping[str, Any], *, ledger_path: Path | None, ledger_absent: bool) -> dict[str, Any]:
    """The generated file: P10-S2's windows (and so ADR-0025's 44 marker-like windows) plus, if given, the ledger's windows. Refuses without a ledger file or an explicit ``ledger_absent`` declaration, which is recorded:
    with the ledger absent this study still avoids the 44 marker-like windows (they are in ``windows_record``) and writes its own spans to the ledger first (``prepare-data``)."""
    if (ledger_path is None) == (not ledger_absent):
        raise EngineeringStop("ENGINEERING STOP — give exactly one of a ledger file or an explicit ledger-absent declaration")
    layout = RowLayout(rows)
    wins = list(windows_record["windows"])
    status: dict[str, Any]
    if ledger_path is not None:
        led = read_ledger(ledger_path, layout)
        wins += [{**w, "source": w.get("source", "shared ledger")} for w in led]
        status = {"state": "read", "path": str(ledger_path), "windows": len(led)}
    else:
        status = {"state": "ABSENT-DECLARED", "note": "ADR-0025's 100 ordinary windows are drawn after this study's panels; its 44 marker-like windows are avoided here (ADR-0026 section 4, correction C7)"}
    spans = excluded_spans(layout, wins)
    return {"format": "p10i-s3-excluded-spans-v1", "end_offsets": "exclusive", "ledger": status, "windows": wins, "spans": [list(s) for s in spans], "row_layout_total_bytes": layout.total}


def shared_ledger_body(rows: Sequence[str], panels: Mapping[str, Sequence[Span]], existing: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """This study's panels written as ledger entries (concatenated bytes, end exclusive, one entry per chunk) for ADR-0025 and ADR-0027 to exclude."""
    layout = RowLayout(rows)
    new = []
    for name, spans in panels.items():
        for row, s, e in spans:
            a, b = layout.from_row_span(row, s, e)
            new.append(ledger_entry(layout, a, b, f"P10-I-S3 panel {name}"))
    return {"format": LEDGER_FORMAT, "windows": [*existing, *new]}
