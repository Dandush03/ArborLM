# ruff: noqa: E501
"""P10IS5 file contents, tiling and request lists (ADR-0028 sections 4.1 and 4.3, rulings 1, 3, 4, 5).

Tile ``t`` of a file is 1,048,576 bytes of one ``torch.randint(0, 256, ..., dtype=torch.uint8)`` call from a generator seeded by the first 8 bytes (big-endian) of SHA-256(``p10is5|store|<seed>|<t>``) modulo 2**63. One seeded
permutation of the usable tiles deals tiles to (repeat, k, s); a tile given to size s is cut into floor(64 / s) aligned, non-overlapping segments from its start, so no page of any pass is requested twice by construction: there is no
acceptance loop. torch and the standard library only (no numpy: it is not in the lock).
"""

import ctypes
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

import torch

from .core import Geometry, sha_seed

PAGE = 16384
TILE_PAGES = 64
TILE_BYTES = PAGE * TILE_PAGES  # 1,048,576
SIZES = (1, 3, 8, 64)
DEPTHS = (1, 2, 4, 8, 16, 32)


def tile_seed(contents_seed: int, tile: int) -> int:
    return sha_seed(f"p10is5|store|{contents_seed}|{tile}")


def tile_bytes(contents_seed: int, tile: int) -> bytes:
    """Ruling 1: one generator per tile, one ``torch.randint`` call of 1,048,576 uint8 values (the bytes are read out through ``ctypes``: no numpy)."""
    g = torch.Generator().manual_seed(tile_seed(contents_seed, tile))
    t = torch.randint(0, 256, (TILE_BYTES,), dtype=torch.uint8, generator=g).contiguous()
    return ctypes.string_at(t.data_ptr(), TILE_BYTES)


def tile_sha256(contents_seed: int, tile: int) -> str:
    return hashlib.sha256(tile_bytes(contents_seed, tile)).hexdigest()


def page_hashes(data: bytes, page: int = PAGE) -> list[str]:
    """SHA-256 of every whole page of ``data`` (its length is a multiple of the page)."""
    if len(data) % page:
        raise ValueError("whole pages only")
    return [hashlib.sha256(data[i : i + page]).hexdigest() for i in range(0, len(data), page)]


# --- the deal (ruling 3) ------------------------------------------------------------------------------------------------------------------------
def tile_permutation(assignment_seed: int, usable_tiles: int) -> list[int]:
    return [int(x) for x in torch.randperm(usable_tiles, generator=torch.Generator().manual_seed(assignment_seed)).tolist()]


def deal(geometry: Geometry, assignment_seed: int) -> dict[tuple[int, int, int], list[int]]:
    """Tiles are dealt in the order repeat (1..5, spare 6), then k = 1..32, then s = 1, 3, 8, 64, taking ``geometry.tiles`` tiles each, from one seeded permutation of the usable tiles."""
    need = geometry.tiles_needed()
    if need > geometry.usable_tiles:
        raise ValueError(f"the geometry needs {need} tiles and the file has {geometry.usable_tiles} usable")
    perm = tile_permutation(assignment_seed, geometry.usable_tiles)
    out: dict[tuple[int, int, int], list[int]] = {}
    pos = 0
    for repeat in geometry.all_repeats:
        for k in geometry.depths:
            for s, count in zip(geometry.sizes, geometry.tiles, strict=True):
                out[(repeat, k, s)] = perm[pos : pos + count]
                pos += count
    if pos != need:
        raise AssertionError("the deal used a different number of tiles than the geometry says")
    return out


@dataclass(frozen=True)
class Request:
    """One request of a pass: ``index`` is its place in the seeded order, ``thread`` is ``index mod k``, offset and length are in bytes (whole pages at page offsets)."""

    index: int
    thread: int
    tile: int
    segment: int
    offset: int
    length: int

    @property
    def pages(self) -> int:
        return self.length // PAGE


def segments_of(tiles: Sequence[int], s: int) -> list[tuple[int, int]]:
    """The pass's segments listed by (tile position in the deal, segment index): floor(64 / s) per tile."""
    return [(t, i) for t in tiles for i in range(TILE_PAGES // s)]


def order_generator(order_seed: int, k: int, s: int) -> torch.Generator:
    """Ruling 4: the state is the first 8 bytes of SHA-256(``p10is5|order|<repeat seed>|<k>|<s>``) modulo 2**63."""
    return torch.Generator().manual_seed(sha_seed(f"p10is5|order|{order_seed}|{k}|{s}"))


def pass_requests(tiles: Sequence[int], k: int, s: int, n: int, order_seed: int) -> list[Request]:
    """The first ``n`` of the pass's segments in the seeded order; request j goes to thread j mod k."""
    segs = segments_of(tiles, s)
    if len(segs) < n:
        raise ValueError(f"a pass of size {s} has {len(segs)} segments, fewer than the {n} requests it needs")
    order = torch.randperm(len(segs), generator=order_generator(order_seed, k, s)).tolist()[:n]
    out = []
    for j, idx in enumerate(order):
        tile, seg = segs[int(idx)]
        out.append(Request(j, j % k, tile, seg, (tile * TILE_PAGES + seg * s) * PAGE, s * PAGE))
    return out


def predicted_bytes(requests: Sequence[Request]) -> int:
    """The registered prediction: 16,384 x pages requested."""
    return PAGE * sum(r.pages for r in requests)


def pass_order(order_seed: int, geometry: Geometry) -> list[tuple[int, int]]:
    """Ruling 5: ``torch.randperm(24)`` over the cells listed k-major."""
    cells = geometry.cells()
    perm = torch.randperm(len(cells), generator=torch.Generator().manual_seed(order_seed)).tolist()
    return [cells[int(i)] for i in perm]


def thread_lists(requests: Sequence[Request], k: int) -> list[list[Request]]:
    lists: list[list[Request]] = [[] for _ in range(k)]
    for r in requests:
        lists[r.thread].append(r)
    return lists


def expected_page_hashes(contents_seed: int, requests: Sequence[Request], cache: dict[int, list[str]] | None = None) -> list[list[str]]:
    """The expected SHA-256 of every page of every request, regenerated from the seed (the file is never read back for this). ``cache`` maps tile -> its 64 page hashes."""
    cache = cache if cache is not None else {}
    out = []
    for r in requests:
        if r.tile not in cache:
            cache[r.tile] = page_hashes(tile_bytes(contents_seed, r.tile))
        first = (r.offset // PAGE) - r.tile * TILE_PAGES
        out.append(cache[r.tile][first : first + r.pages])
    return out


def pages_of(r: Request) -> range:
    first = r.offset // PAGE
    return range(first, first + r.pages)


def enumerate_registered(geometry: Geometry, assignment_seed: int, order_seeds: Sequence[int]) -> dict[str, int]:
    """K's check of the registered geometry, in RAM (no file read): every pass has enough segments, the tile counts are the fixed arithmetic, no tile is dealt twice and no page is requested twice across all passes of
    all repeats. ``order_seeds`` has one seed per repeat (the spare included, last). Returns the counts; raises AssertionError on any violation."""
    dealt = deal(geometry, assignment_seed)
    all_tiles = [t for tiles in dealt.values() for t in tiles]
    assert len(all_tiles) == len(set(all_tiles)) == geometry.tiles_needed(), "a tile is dealt twice or the count differs"
    assert all(0 <= t < geometry.usable_tiles for t in all_tiles), "a tile outside the usable range"
    assert len(order_seeds) == len(geometry.all_repeats), "one order seed per repeat"
    seen: set[int] = set()
    requests = pages = 0
    for (repeat, k, s), tiles in dealt.items():
        reqs = pass_requests(tiles, k, s, geometry.n_of[s], order_seeds[repeat - 1])
        assert len(tiles) == geometry.tiles_of[s]
        for r in reqs:
            for p in pages_of(r):
                assert p not in seen, f"page {p} requested twice"
                seen.add(p)
            assert r.offset % PAGE == 0 and r.length % PAGE == 0 and r.offset // TILE_BYTES == (r.offset + r.length - 1) // TILE_BYTES, "a request outside its tile or off the page grid"
        requests += len(reqs)
        pages += sum(r.pages for r in reqs)
    return {"tiles_dealt": len(all_tiles), "passes": len(dealt), "requests": requests, "pages": pages, "bytes": pages * PAGE, "distinct_pages": len(seen)}
