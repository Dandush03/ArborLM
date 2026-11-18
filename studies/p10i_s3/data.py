# ruff: noqa: E501
"""P10IS3 data: the chunk table beyond rank 4,095, the three regimes' rows, byte-span lineage gates, the panel walk and the shared ledger (ADR-0026 sections 3.3, 4 and 16 ruling 4).

The recipe is the existing one: ``pilot_data.select`` over the pinned parquet (no download, no test split) with ``count`` = all eligible chunks. A gate ties the new table to the recorded one: the first 4,096 train ranks and the
first 2,048 validation ranks reproduce the recorded SHA-256 values bitwise. Spans are (row, start, end) in bytes of the source row.
"""

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from arborlm.io import atomic_write, canonical_json, file_sha256, sha256
from arborlm.pilot_data import CHUNK_BYTES, select

from .core import EngineeringStop

Span = tuple[int, int, int]


def span_of(row: int, offset: int) -> Span:
    return (row, offset, offset + CHUNK_BYTES)


def overlaps(a: Span, b: Span) -> bool:
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


def count_overlaps(spans: Iterable[Span], against: Iterable[Span]) -> int:
    """Number of spans of the first set that overlap any span of the second (by row index, so it is linear)."""
    by_row: dict[int, list[Span]] = {}
    for s in against:
        by_row.setdefault(s[0], []).append(s)
    return sum(1 for s in spans if any(overlaps(s, t) for t in by_row.get(s[0], ())))


@dataclass
class ChunkSet:
    train_rows: Tensor  # [N, 65] int64, in rank order
    train_spans: list[Span]
    val_rows: Tensor  # [M, 65] int64, in rank order (validation excluded against every train candidate)
    val_spans: list[Span]
    counts: dict[str, Any]

    def regime_rows(self, regime: str, cfg: Mapping[str, Any]) -> Tensor:
        d = cfg["data"]
        lo, hi = {"REP": d["rep_ranks"], "REP-U": d["rep_u_ranks"]}.get(regime, (d["fresh_start"], self.train_rows.shape[0]))
        return self.train_rows[int(lo) : int(hi)]

    def regime_spans(self, regime: str, cfg: Mapping[str, Any]) -> list[Span]:
        d = cfg["data"]
        lo, hi = {"REP": d["rep_ranks"], "REP-U": d["rep_u_ranks"]}.get(regime, (d["fresh_start"], len(self.train_spans)))
        return self.train_spans[int(lo) : int(hi)]


def _tensor(payloads: Sequence[bytes]) -> Tensor:
    raw = b"".join(payloads)
    return torch.frombuffer(bytearray(raw), dtype=torch.uint8).long().reshape(len(payloads), CHUNK_BYTES)


def corpus_from_texts(train_texts: Iterable[str], validation_texts: Iterable[str], eligible_train: int, eligible_validation: int) -> ChunkSet:
    """``select`` with count = all eligible chunks (the recorded pool), for train and then for validation excluded against every train candidate."""
    train, full_train, tc = select(train_texts, "train", eligible_train)
    validation, _, vc = select(validation_texts, "validation", eligible_validation, excluded=full_train)
    if tc["eligible_unique_chunks"] != eligible_train or vc["eligible_unique_chunks"] != eligible_validation:
        raise EngineeringStop(f"ENGINEERING STOP — the eligible pool differs from the recorded one: train {tc['eligible_unique_chunks']} (recorded {eligible_train}), validation {vc['eligible_unique_chunks']} (recorded {eligible_validation})")
    return ChunkSet(_tensor([c.payload for c in train]), [span_of(c.row, c.offset) for c in train], _tensor([c.payload for c in validation]), [span_of(c.row, c.offset) for c in validation], {"train": tc, "validation": vc})


def pinned_files() -> Mapping[str, Mapping[str, Any]]:
    from arborlm.fetch_wikitext import DOWNLOAD_FILES, FILES

    return {name: FILES[name] for name in DOWNLOAD_FILES}


def validation_rows(source: Path) -> list[str]:
    """The validation parquet's ``text`` column in file order, exactly as stored (ADR-0022 ruling A-B3's text; needs the optional ``pilot`` extra, pyarrow)."""
    from arborlm.fetch_wikitext import DOWNLOAD_FILES
    from arborlm.pilot_data import _rows

    return list(_rows(source / DOWNLOAD_FILES[1]))


def corpus_from_parquet(source: Path, cfg: Mapping[str, Any], pins: Mapping[str, Mapping[str, Any]] | None = None) -> ChunkSet:
    """The pinned WikiText-2 parquet (ADR-0004 / ADR-0005): the pinned files' size and hash are those of ``fetch_wikitext.FILES`` (``pins`` replaces them in tests with a fixture). Reads nothing else; the test split is
    never read."""
    from arborlm.fetch_wikitext import DOWNLOAD_FILES
    from arborlm.pilot_data import _rows

    pins = pins or pinned_files()
    for name in DOWNLOAD_FILES:
        p = source / name
        if p.stat().st_size != pins[name]["bytes"] or file_sha256(p) != pins[name]["sha256"]:
            raise EngineeringStop(f"ENGINEERING STOP — pinned acquisition file mismatch: {name}")
    return corpus_from_texts(_rows(source / DOWNLOAD_FILES[0]), _rows(source / DOWNLOAD_FILES[1]), int(cfg["data"]["eligible_train"]), int(cfg["data"]["eligible_validation"]))


def reproduction_gate(cs: ChunkSet, expected: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Ruling 4: the first 4,096 train ranks and the first four validation blocks of 512 reproduce the recorded SHA-256 values bitwise."""
    if expected is None:
        from arborlm.p2_data import P1_TRAIN_SHA256, P1_VALIDATION_SHA256
        from arborlm.p3_data import P2_VALIDATION_SHA256
        from arborlm.p4_data import P3_VALIDATION_SHA256, P4_VALIDATION_SHA256

        expected = {"train_4096": P1_TRAIN_SHA256, "val_p1": P1_VALIDATION_SHA256, "val_p2": P2_VALIDATION_SHA256, "val_p3": P3_VALIDATION_SHA256, "val_p4": P4_VALIDATION_SHA256}

    def h(t: Tensor) -> str:
        return sha256(bytes(t.to(torch.uint8).reshape(-1).tolist()))

    got: dict[str, str] = {}
    if cs.train_rows.shape[0] >= 4096:
        got["train_4096"] = h(cs.train_rows[:4096])
    for i, k in enumerate(("val_p1", "val_p2", "val_p3", "val_p4")):
        if cs.val_rows.shape[0] >= 512 * (i + 1):
            got[k] = h(cs.val_rows[512 * i : 512 * (i + 1)])
    ok = {k: got.get(k) == v for k, v in expected.items()}
    return {"passed": all(ok.values()), "per_item": ok}


def write_chunk_files(cs: ChunkSet, directory: Path) -> dict[str, str]:
    """The new chunk files are written and hashed (frozen inputs, section 11 item 7)."""
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "train_all.bytes": bytes(cs.train_rows.to(torch.uint8).reshape(-1).tolist()),
        "validation_all.bytes": bytes(cs.val_rows.to(torch.uint8).reshape(-1).tolist()),
        "train_spans.json": canonical_json([list(s) for s in cs.train_spans]),
        "validation_spans.json": canonical_json([list(s) for s in cs.val_spans]),
    }
    out = {}
    for name, payload in files.items():
        atomic_write(directory / name, payload)
        out[name] = sha256(payload)
    return out


# --- lineage gates (section 3.3) ---------------------------------------------------------------------------------------------
def lineage_gate(train_spans: Sequence[Span], consumed_ranks_by_parent: Mapping[str, Sequence[int]], p1_consumed_ranks: Sequence[int], rep_u: tuple[int, int], fresh_start: int) -> dict[str, Any]:
    """No training batch in the lineage of the nine parents contained a REP-U or FRESH chunk: the ranks the lineage consumed are the ranks of each parent's ``ranked_train_row_ids`` (P2 and P3 repeat that order) and the
    ranks P1 consumed (256 updates x 8 in fixed ranked cyclic order); their byte spans overlap no REP-U span and no FRESH span, and no consumed rank lies at or above ``rep_u[0]``."""
    consumed: set[int] = set(p1_consumed_ranks)
    for ranks in consumed_ranks_by_parent.values():
        consumed |= set(ranks)
    spans_consumed = [train_spans[r] for r in sorted(consumed)]
    rep_u_spans = list(train_spans[rep_u[0] : rep_u[1]])
    fresh_spans = list(train_spans[fresh_start:])
    problems = []
    if any(r >= rep_u[0] for r in consumed):
        problems.append("a consumed rank lies in REP-U or FRESH")
    n_u, n_f = count_overlaps(rep_u_spans, spans_consumed), count_overlaps(fresh_spans, spans_consumed)
    if n_u or n_f:
        problems.append(f"byte-span overlap with the lineage: REP-U {n_u}, FRESH {n_f}")
    return {"passed": not problems, "problems": problems, "consumed_ranks": len(consumed), "rep_u_overlaps": n_u, "fresh_overlaps": n_f}


def rep_u_fresh_disjoint(train_spans: Sequence[Span], rep_u: tuple[int, int], fresh_start: int, rep: tuple[int, int]) -> dict[str, Any]:
    """REP, REP-U and FRESH are three disjoint rank ranges and their byte spans overlap pairwise nowhere."""
    parts = {"REP": train_spans[rep[0] : rep[1]], "REP-U": train_spans[rep_u[0] : rep_u[1]], "FRESH": train_spans[fresh_start:]}
    over = {f"{a}|{b}": count_overlaps(parts[a], parts[b]) for a in parts for b in parts if a < b}
    return {"passed": not any(over.values()), "overlaps": over}


# --- the panel walk and the ledger (section 4) -------------------------------------------------------------------------------
class PanelWalkExhausted(EngineeringStop):
    pass


def walk_panels(val_spans: Sequence[Span], excluded: Iterable[Span], start: int, size: int, count: int = 2) -> list[list[int]]:
    """The first ``size`` validation chunks, walking down the ranking from rank ``start``, whose byte span overlaps no excluded span and no earlier panel's span; then the next panel, the same way (the registered
    panel first, the calibration panel second). Raises ``PanelWalkExhausted`` (an engineering stop) if the ranking runs out."""
    by_row: dict[int, list[Span]] = {}
    for s in excluded:
        by_row.setdefault(s[0], []).append(s)
    panels: list[list[int]] = [[] for _ in range(count)]
    p = 0
    for rank in range(start, len(val_spans)):
        s = val_spans[rank]
        if any(overlaps(s, t) for t in by_row.get(s[0], ())):
            continue
        panels[p].append(rank)
        by_row.setdefault(s[0], []).append(s)
        if len(panels[p]) == size:
            p += 1
            if p == count:
                return panels
    raise PanelWalkExhausted(f"ENGINEERING STOP — the panel walk ran out of eligible chunks after {sum(map(len, panels))} of {size * count}")


def ledger(panels: Mapping[str, Sequence[int]], val_spans: Sequence[Span], windows: Sequence[Span]) -> dict[str, Any]:
    """The shared ledger ADR-0025 and ADR-0027 must exclude: both panels in byte spans, with the spans excluded by the walk (ADR-0025's windows) and its SHA-256."""
    body = {"panels": {k: [list(val_spans[r]) for r in v] for k, v in panels.items()}, "excluded_windows": [list(w) for w in windows], "panel_ranks": {k: list(v) for k, v in panels.items()}}
    return {"ledger": body, "sha256": hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def panel_tensor(cs: ChunkSet, ranks: Sequence[int]) -> Tensor:
    return cs.val_rows[torch.tensor(list(ranks), dtype=torch.int64)]
