# ruff: noqa: E501
"""P10IS6 corpus (ADR-0031 section 6): articles, the exclusion set E, the compact re-implementation of ``pilot_data.select``, the pools, the uint8 chunk table, the pool-size decision and the panels.

``select_compact`` is a gated equal of ``pilot_data.select`` (section 6.4 rule 3): it works on packed digests and arrays (no Python object per chunk beyond the dict of kept digests) and a test and the D0 gate prove it equal to ``select`` on the
WikiText-2 train rows with the old rank string. No numpy (not installed): ``array``, ``bytearray`` and torch only. No network, no download here (the fetch is ``fetch.py``). Self-check only.

Order of operations (rule 3, ruling G6): (1) rows in file order, numbered consecutively across files; (2) articles segmented on ``str.strip()`` of each row; (3) articles holding a chunk whose digest is in E are removed whole; (4) ``select``'s cutting,
de-duplication and ranking are applied once to all remaining rows; (5) each kept chunk goes to the pool of the article holding its kept occurrence. Articles are numbered in file order AFTER the exclusion (surviving articles 0, 1, 2, ...; an
article with no row does not exist), pool membership is by that number (rule 4).
"""

import hashlib
from array import array
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arborlm.io import canonical_json, sha256

from . import core
from .core import EngineeringStop

CHUNK = 65


def is_heading(text: str) -> bool:
    """A row is an article heading if, after removing leading and trailing white space, it starts with ``= ``, ends with `` =`` and its third character is not ``=`` (rule 1)."""
    s = text.strip()
    return len(s) >= 3 and s.startswith("= ") and s.endswith(" =") and s[2] != "="


def excluded_digests(texts: Iterable[str]) -> set[bytes]:
    """E (ruling G7): the SHA-256 digest of every 65-byte candidate chunk at ``select``'s offsets, before de-duplication and before cross-split exclusion. Raw 32-byte digests (the hex string of ``select`` is their encoding)."""
    out: set[bytes] = set()
    for text in texts:
        enc = text.encode("utf-8")
        for off in range(0, len(enc) - CHUNK + 1, CHUNK):
            out.add(hashlib.sha256(enc[off : off + CHUNK]).digest())
    return out


@dataclass
class Scan:
    """The compact record of one pass over the rows: per full chunk its digest, row, offset, article (file-order number, before the exclusion) and payload; per article whether it holds a chunk of E."""

    digests: bytearray = field(default_factory=bytearray)
    payloads: bytearray = field(default_factory=bytearray)
    rows: array = field(default_factory=lambda: array("I"))
    offsets: array = field(default_factory=lambda: array("I"))
    article: array = field(default_factory=lambda: array("I"))
    articles_with_rows: list[int] = field(default_factory=list)  # raw article numbers that have at least one row
    hit: set[int] = field(default_factory=set)  # raw article numbers holding a chunk of E
    n_rows: int = 0

    @property
    def n_chunks(self) -> int:
        return len(self.rows)


def scan_rows(rows: Iterable[str], excluded: set[bytes] | None = None) -> Scan:
    """Rule 1-2 and the first half of rule 3. Raw article numbers: rows before the first heading are article 0 (if any row precedes it), each heading row starts the next article."""
    sc = Scan()
    cur: int | None = None
    for text in rows:
        if not isinstance(text, str):
            raise EngineeringStop(f"ENGINEERING STOP — non-string text field at row {sc.n_rows}")
        if cur is None:  # the first row starts article 0 (a preamble, or the first heading itself)
            cur = 0
            sc.articles_with_rows.append(0)
        elif is_heading(text):
            cur += 1
            sc.articles_with_rows.append(cur)
        enc = text.encode("utf-8")
        for off in range(0, len(enc) - CHUNK + 1, CHUNK):
            payload = enc[off : off + CHUNK]
            d = hashlib.sha256(payload).digest()
            sc.digests += d
            sc.payloads += payload
            sc.rows.append(sc.n_rows)
            sc.offsets.append(off)
            sc.article.append(cur)
            if excluded is not None and d in excluded:
                sc.hit.add(cur)
        sc.n_rows += 1
    return sc


def rank_of(label: str, row: int, offset: int) -> bytes:
    """The rank of ``select``: SHA-256 of ``{label}:{row}:{offset}`` (its hex string and its raw bytes sort identically)."""
    return hashlib.sha256(f"{label}:{row}:{offset}".encode()).digest()


@dataclass
class Selection:
    kept: list[int]  # chunk indices of the Scan, in rank order
    counts: dict[str, Any]
    article_number: dict[int, int]  # raw article number -> its number after the exclusion


def select_compact(sc: Scan, label: str, *, remove_hit_articles: bool = True) -> Selection:
    """Steps 3 to 4: remove the articles that hold a chunk of E (when ``remove_hit_articles``), then ``select``'s de-duplication (lowest (rank, row, offset) per digest) and ranking. ``counts`` mirrors ``select``'s."""
    removed_articles = sc.hit if remove_hit_articles else set()
    surviving = [a for a in sc.articles_with_rows if a not in removed_articles]
    number = {a: i for i, a in enumerate(surviving)}
    best: dict[bytes, int] = {}  # digest -> chunk index of the lowest (rank, row, offset) so far
    full = dup = removed_chunks = 0
    for i in range(sc.n_chunks):
        if sc.article[i] in removed_articles:
            removed_chunks += 1
            continue
        full += 1
        d = bytes(sc.digests[32 * i : 32 * i + 32])
        j = best.get(d)
        if j is None:
            best[d] = i
            continue
        dup += 1
        if (rank_of(label, sc.rows[i], sc.offsets[i]), sc.rows[i], sc.offsets[i]) < (rank_of(label, sc.rows[j], sc.offsets[j]), sc.rows[j], sc.offsets[j]):
            best[d] = i
    kept = sorted(best.values(), key=lambda i: (rank_of(label, sc.rows[i], sc.offsets[i]), sc.rows[i], sc.offsets[i]))
    counts = {"rows": sc.n_rows, "candidate_chunks": sc.n_chunks, "full_chunks": full, "chunks_in_removed_articles": removed_chunks, "articles_removed": len(removed_articles), "articles_total": len(sc.articles_with_rows), "duplicates": dup, "eligible_unique_chunks": len(kept)}
    return Selection(kept, counts, number)


def payload_of(sc: Scan, i: int) -> bytes:
    return bytes(sc.payloads[CHUNK * i : CHUNK * (i + 1)])


def reproduces_select(rows: Sequence[str], split: str = "train", *, label: str | None = None, count: int | None = None) -> dict[str, Any]:
    """The gate of rule 3: ``select_compact`` (no exclusion) gives, rank for rank, the chunks of ``pilot_data.select`` with the same rank string. ``count`` limits the comparison to the first ranks (None: all)."""
    from arborlm.pilot_data import select

    sc = scan_rows(rows)
    sel = select_compact(sc, label or f"arborlm-pilot-v1:{split}", remove_hit_articles=False)
    ref, _, rc = select(rows, split, len(sel.kept))  # select raises if it finds fewer: that is a failed gate by exception
    n = len(ref) if count is None else min(count, len(ref))
    same = rc["eligible_unique_chunks"] == len(sel.kept) and all((payload_of(sc, sel.kept[r]), sc.rows[sel.kept[r]], sc.offsets[sel.kept[r]]) == (ref[r].payload, ref[r].row, ref[r].offset) for r in range(n))
    return {"passed": bool(same), "compared": n, "eligible": len(sel.kept), "reference_eligible": rc["eligible_unique_chunks"]}


# --- pools (rule 4, section 6.5) -----------------------------------------------------------------------------------------------------------------------
@dataclass
class Pools:
    registered: list[int]  # chunk indices in rank order
    calibration: list[int]
    definition: str  # "mod3" or "mod2"


def assign_pools(sc: Scan, sel: Selection, cfg: Mapping[str, Any], *, definition: str) -> Pools:
    d = cfg["data"]
    mod, res = (int(d["calibration_article_mod"]), int(d["calibration_article_residue"])) if definition == "mod3" else (int(d["fallback_article_mod"]), int(d["fallback_article_residue"]))
    reg, cal = [], []
    for i in sel.kept:
        (cal if sel.article_number[sc.article[i]] % mod == res else reg).append(i)
    return Pools(reg, cal, definition)


def decide_pools(sc: Scan, sel: Selection, cfg: Mapping[str, Any]) -> tuple[Pools, int, dict[str, Any]]:
    """Section 6.5: ``(pools, k_max, record)`` by code from counts alone, before any calibration run. mod-3 is used; if its calibration pool is short and the mod-2 definition gives both pools at least 2,097,152 chunks, mod-2 is used.
    Then the ceiling rule (``core.k_max_for_pools``); below rung 2: ENGINEERING STOP — CORPUS TOO SMALL."""
    need = int(cfg["data"]["pool_chunks_for_umax"])
    p3 = assign_pools(sc, sel, cfg, definition="mod3")
    chosen, why = p3, "mod 3 = 2 (the registered definition)"
    if len(p3.calibration) < need:
        p2 = assign_pools(sc, sel, cfg, definition="mod2")
        if len(p2.calibration) >= need and len(p2.registered) >= need:
            chosen, why = p2, "mod 2 = 1 (the calibration pool was short under mod 3 and mod 2 gives both pools at least 2,097,152 chunks)"
    k_max = core.k_max_for_pools(cfg, len(chosen.registered), len(chosen.calibration))
    return chosen, k_max, {"definition": chosen.definition, "why": why, "registered_pool": len(chosen.registered), "calibration_pool": len(chosen.calibration), "k_max": k_max, "mod3_pools": [len(p3.registered), len(p3.calibration)]}


def write_chunk_table(sc: Scan, pools: Pools, directory: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """One uint8 file: the registered pool in rank order, then the calibration pool in rank order (section 6.4 rule 7); hashed. Streams take ``[0, n_reg)`` and ``[n_reg, n_reg + n_cal)``."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / str(cfg["data"]["chunk_table_name"])
    if path.exists():
        raise FileExistsError(path)
    h = hashlib.sha256()
    with path.open("xb") as f:
        for part in (pools.registered, pools.calibration):
            for lo in range(0, len(part), 65536):
                block = b"".join(payload_of(sc, i) for i in part[lo : lo + 65536])
                f.write(block)
                h.update(block)
    return {"name": path.name, "sha256": h.hexdigest(), "rows": len(pools.registered) + len(pools.calibration), "registered_rows": len(pools.registered), "calibration_rows": len(pools.calibration), "bytes": path.stat().st_size}


def overlap_with_excluded(sc: Scan, pools: Pools, excluded: set[bytes]) -> int:
    """Gate 2 of rule 3: zero digest overlap between the pools and E."""
    return sum(1 for part in (pools.registered, pools.calibration) for i in part if bytes(sc.digests[32 * i : 32 * i + 32]) in excluded)


def pools_disjoint(sc: Scan, pools: Pools) -> bool:
    a = {bytes(sc.digests[32 * i : 32 * i + 32]) for i in pools.registered}
    return not any(bytes(sc.digests[32 * i : 32 * i + 32]) in a for i in pools.calibration)


# --- near-duplicates at other offsets (section 12.5, descriptive) ------------------------------------------------------------------------------------------
def shares_32_byte_substring(panel: Sequence[bytes], pool_payloads: Iterator[bytes]) -> dict[str, Any]:
    """Descriptive, no rule: the share of panel chunks that have a 32-byte substring occurring in the pool (at any offset of any pool chunk). Exact (set of the panel's 32-byte windows; the pool is scanned once)."""
    windows: dict[bytes, set[int]] = {}
    for n, p in enumerate(panel):
        for o in range(len(p) - 31):
            windows.setdefault(p[o : o + 32], set()).add(n)
    shared: set[int] = set()
    for payload in pool_payloads:
        for o in range(len(payload) - 31):
            hit = windows.get(payload[o : o + 32])
            if hit:
                shared |= hit
    return {"panel_chunks": len(panel), "sharing": len(shared), "share": len(shared) / len(panel) if panel else None}


def counts_record(sc: Scan, sel: Selection, pools: Pools, decision: Mapping[str, Any], table: Mapping[str, Any], gates: Mapping[str, Any], validation_left: int | None) -> dict[str, Any]:
    return {**core.envelope("d0"), "counts": sel.counts, "decision": dict(decision), "table": dict(table), "gates": dict(gates), "eligible_validation_spans_left_for_panels": validation_left}


def digest_hex(sc: Scan, i: int) -> str:
    return sc.digests[32 * i : 32 * i + 32].hex()


def table_sha(path: Path) -> str:
    return sha256(path.read_bytes()) if path.stat().st_size < 10**8 else hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def manifest_bytes(obj: Mapping[str, Any]) -> bytes:
    return canonical_json(dict(obj))
