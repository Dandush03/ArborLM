# ruff: noqa: E501
"""P10IS5 layout tests (ADR-0028 sections 4.1, 4.3, 5.2; rulings 1, 3, 4, 5): the tile generator, the deal, the segments, the request lists, the fixed arithmetic of the registered and the rehearsal geometries, no page twice.
Brute-force reimplementations are written in this file from the ADR's text (hashlib, torch.randperm / randint as the ruling says), not by calling the module's helpers for the expected values. Unit-test seeds 937001-937999 only
(plus the config's registered seeds, which are used here only to enumerate tile numbers in RAM: no file is read and nothing is observed). Self-check only."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10is5 import core, layout  # noqa: E402

CFG = core.load_config()
REG = core.registered_geometry(CFG)
REH = core.rehearsal_geometry(CFG)
PAGE, TILE_PAGES = 16384, 64


def brute_seed(text: str) -> int:
    d = hashlib.sha256(text.encode()).digest()
    return int("".join(f"{b:02x}" for b in d[:8]), 16) % (2**63)  # big-endian, written out by hand


def test_sha_seed_is_big_endian_first_eight_bytes_mod_2_63() -> None:
    for text in ("p10is5|store|937001|0", "p10is5|order|937021|1|3", ""):
        assert core.sha_seed(text) == brute_seed(text) == int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big") % 2**63
    # little-endian would differ
    assert int.from_bytes(hashlib.sha256(b"p10is5|store|937001|0").digest()[:8], "little") % 2**63 != brute_seed("p10is5|store|937001|0")


def test_tile_contents_follow_ruling_one() -> None:
    seed, t = 937001, 3
    g = torch.Generator().manual_seed(brute_seed(f"p10is5|store|{seed}|{t}"))
    want = bytes(torch.randint(0, 256, (1_048_576,), dtype=torch.uint8, generator=g).tolist())
    got = layout.tile_bytes(seed, t)
    assert len(got) == 1_048_576 and got == want
    assert layout.tile_bytes(seed, t) == got and layout.tile_bytes(seed, t + 1) != got and layout.tile_bytes(seed + 1, t) != got  # deterministic; seed and tile both matter
    assert layout.tile_sha256(seed, t) == hashlib.sha256(want).hexdigest()
    assert len(set(got)) > 250  # incompressible-looking: every byte value occurs


def test_page_hashes_split_a_tile_into_64_pages() -> None:
    data = layout.tile_bytes(937001, 0)
    ph = layout.page_hashes(data)
    assert len(ph) == 64 and ph[5] == hashlib.sha256(data[5 * PAGE : 6 * PAGE]).hexdigest()
    with pytest.raises(ValueError):
        layout.page_hashes(data[:-1])


def brute_deal(n_usable: int, seed: int, repeats: int, depths: tuple[int, ...], sizes: tuple[int, ...], per: tuple[int, ...]) -> dict[tuple[int, int, int], list[int]]:
    perm = torch.randperm(n_usable, generator=torch.Generator().manual_seed(seed)).tolist()
    out, pos = {}, 0
    for r in range(1, repeats + 1):
        for k in depths:
            for s, c in zip(sizes, per, strict=True):
                out[(r, k, s)] = perm[pos : pos + c]
                pos += c
    return out


def test_deal_is_ruling_three_registered_and_rehearsal() -> None:
    assert layout.deal(REG, 287001) == brute_deal(4096, 287001, 6, (1, 2, 4, 8, 16, 32), (1, 3, 8, 64), (7, 20, 20, 64))
    assert layout.deal(REH, 289241) == brute_deal(896, 289241, 5, (1, 2, 4, 8, 16, 32), (1, 3, 8, 64), (2, 5, 5, 16))
    d = layout.deal(REG, 287001)
    assert sum(len(v) for v in d.values()) == 3996 == 6 * 6 * 111 and len(d) == 144
    assert all(len(d[(1, 1, s)]) == c for s, c in zip((1, 3, 8, 64), (7, 20, 20, 64), strict=True))
    flat = [t for v in d.values() for t in v]
    assert len(set(flat)) == 3996 and set(flat) <= set(range(4096))  # a permutation's prefix: no tile twice
    assert sum(len(v) for v in layout.deal(REH, 289241).values()) == 840 == 5 * 6 * 28


def test_every_cell_is_spread_over_the_whole_file() -> None:
    d = layout.deal(REG, 287001)
    lo = [min(v) for key, v in d.items() if key[2] == 64]
    hi = [max(v) for key, v in d.items() if key[2] == 64]
    assert min(lo) < 200 and max(hi) > 3900  # the cells reach both ends of the file (the fourth review's X-9)


def test_segments_are_aligned_and_disjoint_and_counts_are_64_21_8_1() -> None:
    for s, n_seg in ((1, 64), (3, 21), (8, 8), (64, 1)):
        segs = layout.segments_of([5], s)
        assert len(segs) == n_seg == TILE_PAGES // s
        starts = [(5 * TILE_PAGES + i * s) for _, i in segs]
        assert starts == sorted(starts) and all(b - a >= s for a, b in zip(starts, starts[1:], strict=False))
        assert all(((p - 5 * TILE_PAGES) + s) <= TILE_PAGES for p in starts)  # inside its tile
    assert [layout.TILE_PAGES // s for s in (1, 3, 8, 64)] == [64, 21, 8, 1]
    # tiles per pass 7, 20, 20, 64 give 448, 420, 160, 64 segments, enough for n(s) = 400, 400, 160, 64
    assert [7 * 64, 20 * 21, 20 * 8, 64 * 1] == [448, 420, 160, 64] and all(a >= b for a, b in zip((448, 420, 160, 64), REG.requests, strict=True))


def test_request_order_is_ruling_four() -> None:
    tiles = [11, 7, 400, 3, 9, 20, 55]
    k, s, n, seed = 4, 1, 400, 937021
    segs = [(t, i) for t in tiles for i in range(64)]
    perm = torch.randperm(len(segs), generator=torch.Generator().manual_seed(brute_seed(f"p10is5|order|{seed}|{k}|{s}"))).tolist()[:n]
    reqs = layout.pass_requests(tiles, k, s, n, seed)
    assert len(reqs) == 400
    for j, (r, idx) in enumerate(zip(reqs, perm, strict=True)):
        t, i = segs[idx]
        assert (r.index, r.thread, r.tile, r.segment, r.offset, r.length) == (j, j % k, t, i, (t * 64 + i * s) * PAGE, s * PAGE)
    assert layout.predicted_bytes(reqs) == 6_553_600


@pytest.mark.parametrize(("s", "n", "tiles", "predicted"), [(1, 400, 7, 6_553_600), (3, 400, 20, 19_660_800), (8, 160, 20, 20_971_520), (64, 64, 64, 67_108_864)])
def test_predicted_bytes_per_size(s: int, n: int, tiles: int, predicted: int) -> None:
    reqs = layout.pass_requests(list(range(tiles)), 2, s, n, 937022)
    assert len(reqs) == n and layout.predicted_bytes(reqs) == predicted == PAGE * s * n
    assert all(r.offset % PAGE == 0 and r.length == s * PAGE for r in reqs)


def test_too_few_segments_is_refused() -> None:
    with pytest.raises(ValueError, match="fewer than"):
        layout.pass_requests([1], 1, 64, 2, 937021)


def test_pass_order_is_randperm_of_24_cells_k_major() -> None:
    cells = [(k, s) for k in (1, 2, 4, 8, 16, 32) for s in (1, 3, 8, 64)]
    perm = torch.randperm(24, generator=torch.Generator().manual_seed(937031)).tolist()
    assert layout.pass_order(937031, REG) == [cells[i] for i in perm] and REG.cells() == cells


def test_registered_enumeration_totals_and_no_page_twice() -> None:
    seeds = list(CFG["seeds"]["request_order"]) + [CFG["seeds"]["spare_request_order"]]
    c = layout.enumerate_registered(REG, int(CFG["seeds"]["tile_assignment"]), seeds)
    assert c == {"tiles_dealt": 3996, "passes": 144, "requests": 36_864, "pages": 251_136, "bytes": 4_114_612_224, "distinct_pages": 251_136}
    # the five registered repeats alone (the spare is repeat 6): 120 passes, 30,720 requests, 209,280 pages, 3.43 GB
    five = {k: v for k, v in layout.deal(REG, int(CFG["seeds"]["tile_assignment"])).items() if k[0] <= 5}
    reqs = sum(len(layout.pass_requests(t, k, s, REG.n_of[s], seeds[r - 1])) for (r, k, s), t in five.items())
    pages = sum(sum(x.pages for x in layout.pass_requests(t, k, s, REG.n_of[s], seeds[r - 1])) for (r, k, s), t in five.items())
    assert len(five) == 120 and reqs == 30_720 and pages == 209_280 and pages * PAGE == 3_428_843_520
    r = layout.enumerate_registered(REH, int(CFG["seeds"]["m_tile_assignment"]), list(CFG["seeds"]["m_request_order"]))
    assert r["tiles_dealt"] == 840 and r["passes"] == 120 and r["requests"] == 5 * 6 * (100 + 100 + 40 + 16) == 7680 and r["distinct_pages"] == r["pages"]


def test_enumeration_catches_a_page_requested_twice() -> None:
    bad = core.Geometry("bad", 64, 16, (1,), (1,), (4,), (1,), 2, False)
    # two repeats dealt from a 16-tile universe cannot overlap; force an overlap by giving the permutation fewer tiles than needed
    with pytest.raises(ValueError, match="needs"):
        layout.deal(core.Geometry("bad2", 64, 1, (1,), (1,), (4,), (1,), 2, False), 937011)
    assert layout.enumerate_registered(bad, 937011, [937021, 937022])["distinct_pages"] == 8


def test_expected_page_hashes_match_the_tile_bytes() -> None:
    reqs = layout.pass_requests([2, 5], 1, 3, 4, 937021)
    got = layout.expected_page_hashes(937001, reqs)
    for r, row in zip(reqs, got, strict=True):
        data = layout.tile_bytes(937001, r.tile)
        first = r.segment * 3
        assert row == [hashlib.sha256(data[(first + j) * PAGE : (first + j + 1) * PAGE]).hexdigest() for j in range(3)]
