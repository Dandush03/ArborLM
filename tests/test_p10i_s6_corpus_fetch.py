# ruff: noqa: E501
"""P10IS6 corpus rules (ADR-0031 section 6.4, 6.5) and the fetch stage against a local fixture (no network). Self-check only."""

import copy
import hashlib
import json
import random
from typing import Any

import pytest

from studies.p10i_s6 import core, corpus, fetch, model, testing

CFG = core.load_config()


def text(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("abcdefgh \n") for _ in range(n))


def toy_rows(seed: int, articles: int = 12) -> list[str]:
    rng = random.Random(seed)
    rows = [text(rng, 300)]  # a preamble: article 0
    for a in range(articles):
        rows.append(f" = Title {a} = \n")
        for _ in range(rng.randint(1, 3)):
            rows.append(text(rng, rng.randint(70, 400)))
    return rows


def test_heading_rule() -> None:
    assert corpus.is_heading(" = Valkyria Chronicles III = \n")
    assert not corpus.is_heading(" = = Gameplay = = \n")  # third character is '='
    assert not corpus.is_heading("= =")  # the third character is '=' (and the row is no title)
    assert not corpus.is_heading("= x")  # does not end with ' ='
    assert not corpus.is_heading("text = x =text")
    assert corpus.is_heading("\t= A =  ")  # white space is removed first


def test_select_compact_equals_pilot_data_select_rank_for_rank() -> None:
    """Rule 3's gate: with the old rank string and no exclusion the compact version reproduces ``select`` exactly, duplicates included."""
    rows = toy_rows(1) + toy_rows(1)[:8]  # the same text again: many duplicate digests
    g = corpus.reproduces_select(rows, "train")
    assert g["passed"] and g["compared"] == g["eligible"] > 50
    # a different rank string gives a different order but the same set of chunks
    sc = corpus.scan_rows(rows)
    a = corpus.select_compact(sc, "arborlm-pilot-v1:train", remove_hit_articles=False)
    b = corpus.select_compact(sc, "p10i-s6-v1:train103", remove_hit_articles=False)
    assert a.kept != b.kept and {corpus.digest_hex(sc, i) for i in a.kept} == {corpus.digest_hex(sc, i) for i in b.kept}


def test_whole_article_exclusion_numbering_and_pools() -> None:
    rows = toy_rows(2, articles=15)
    e = corpus.excluded_digests([rows[5]])  # chunks of one row (inside some article)
    sc = corpus.scan_rows(rows, e)
    hit_articles = {sc.article[i] for i in range(sc.n_chunks) if bytes(sc.digests[32 * i : 32 * i + 32]) in e}
    assert hit_articles == sc.hit and len(hit_articles) == 1
    sel = corpus.select_compact(sc, "p10i-s6-v1:train103")
    assert sel.counts["articles_removed"] == 1 and sel.counts["chunks_in_removed_articles"] >= 1
    kept_articles = {sc.article[i] for i in sel.kept}
    assert not (kept_articles & hit_articles)  # every chunk of the removed article is gone, also those not in E
    assert sorted(sel.article_number.values()) == list(range(len(sel.article_number)))  # numbered consecutively after the exclusion
    assert list(sel.article_number)[0] == 0 or 0 in sel.article_number or 0 in hit_articles
    pools = corpus.assign_pools(sc, sel, CFG, definition="mod3")
    assert corpus.overlap_with_excluded(sc, pools, e) == 0 and corpus.pools_disjoint(sc, pools)
    assert all(sel.article_number[sc.article[i]] % 3 == 2 for i in pools.calibration) and all(sel.article_number[sc.article[i]] % 3 != 2 for i in pools.registered)
    assert len(pools.registered) + len(pools.calibration) == len(sel.kept)
    # each pool is in rank order
    rank = {i: r for r, i in enumerate(sel.kept)}
    assert [rank[i] for i in pools.registered] == sorted(rank[i] for i in pools.registered)
    # the mod-2 fallback is a different split of the same kept chunks
    p2 = corpus.assign_pools(sc, sel, CFG, definition="mod2")
    assert len(p2.registered) + len(p2.calibration) == len(sel.kept)


def test_duplicate_chunk_in_two_articles_lies_in_one_pool_with_its_lowest_rank() -> None:
    chunk = "x" * 65
    rows = ["pre " + "p" * 70, " = A = \n", chunk + "A" * 70, " = B = \n", "q" * 70, " = C = \n", chunk + "C" * 70]
    sc = corpus.scan_rows(rows)
    sel = corpus.select_compact(sc, "p10i-s6-v1:train103")
    holders = [i for i in sel.kept if corpus.payload_of(sc, i) == chunk.encode()]
    assert len(holders) == 1 and sel.counts["duplicates"] >= 1
    label = "p10i-s6-v1:train103"
    cands = [i for i in range(sc.n_chunks) if corpus.payload_of(sc, i) == chunk.encode()]
    best = min(cands, key=lambda i: (corpus.rank_of(label, sc.rows[i], sc.offsets[i]), sc.rows[i], sc.offsets[i]))
    assert holders[0] == best


def test_pool_decision_ceiling_and_fallback() -> None:
    cfg = copy.deepcopy(dict(CFG))
    cfg["ladder"] = {**CFG["ladder"], "base_updates": 1}  # U_k = 2^k, a stream needs 8 * 2^k chunks
    cfg["data"] = {**CFG["data"], "pool_chunks_for_umax": 8 * 16}
    assert core.k_max_for_pools(cfg, 128, 128) == 4
    assert core.k_max_for_pools(cfg, 128, 64) == 3  # a short pool cuts the ladder before any calibration run
    with pytest.raises(core.EngineeringStop, match="CORPUS TOO SMALL"):
        core.k_max_for_pools(cfg, 128, 16)  # below rung 2
    rows = toy_rows(3, articles=40)
    sc = corpus.scan_rows(rows)
    sel = corpus.select_compact(sc, "p10i-s6-v1:train103")
    cfg["data"] = {**cfg["data"], "pool_chunks_for_umax": 1}
    pools, k, rec = corpus.decide_pools(sc, sel, cfg)
    assert rec["definition"] == "mod3" and k >= 2 and rec["registered_pool"] == len(pools.registered)


def test_chunk_table_roundtrip_and_hash() -> None:
    rows = toy_rows(4, articles=20)
    sc = corpus.scan_rows(rows)
    sel = corpus.select_compact(sc, "p10i-s6-v1:train103")
    pools = corpus.assign_pools(sc, sel, CFG, definition="mod3")
    with testing.scratch("table") as d:
        rec = corpus.write_chunk_table(sc, pools, d, CFG)
        assert rec["rows"] == rec["registered_rows"] + rec["calibration_rows"] and rec["sha256"] == hashlib.sha256((d / rec["name"]).read_bytes()).hexdigest()
        table = model.map_table(d / rec["name"], rec["rows"])
        for n, i in enumerate(pools.registered[:5] + pools.calibration[:5]):
            idx = n if n < 5 else rec["registered_rows"] + (n - 5)
            assert bytes(table[idx].tolist()) == corpus.payload_of(sc, i)
        with pytest.raises(FileExistsError):
            corpus.write_chunk_table(sc, pools, d, CFG)


def test_32_byte_substring_share_against_brute_force() -> None:
    rng = random.Random(5)
    panel = [bytes(rng.randrange(256) for _ in range(65)) for _ in range(20)]
    pool = [bytes(rng.randrange(256) for _ in range(65)) for _ in range(50)]
    pool[3] = bytes(7 for _ in range(10)) + panel[2][5:60]  # shares 32+ bytes with panel[2]
    pool[9] = panel[11][40:] + bytes(40)  # only 25 bytes of panel[11]: no 32-byte substring
    got = corpus.shares_32_byte_substring(panel, iter(pool))
    want = sum(1 for p in panel if any(p[o : o + 32] in q for o in range(34) for q in pool))
    assert got["sharing"] == want == 1 and got["share"] == 1 / 20


# ------------------------------------------------------------------------------------------------ fetch against the ledger of record (a throw-away COPY of it)
LEDGER = core.repo_root() / "docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md"
NAMES = ["train-00000-of-00002.parquet", "train-00001-of-00002.parquet"]


class Resp:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self) -> "Resp":
        return self

    def __exit__(self, *a: Any) -> None:
        return None

    def read(self, n: int = -1) -> bytes:
        return self.data


def pointer(data: bytes) -> bytes:
    return f"version https://git-lfs.github.com/spec/v1\noid sha256:{hashlib.sha256(data).hexdigest()}\nsize {len(data)}\n".encode()


def test_the_ledger_of_record_is_the_only_ledger_file() -> None:
    root = core.repo_root()
    assert [p.name for p in root.rglob("DOWNLOAD_LEDGER*.md") if ".venv" not in p.relative_to(root).parts] == ["DOWNLOAD_LEDGER.md"]
    assert LEDGER.is_file() and fetch.DOWNLOAD_LEDGER == fetch.Path("docs/reviews/p10-design-2026-11-15/DOWNLOAD_LEDGER.md")


def test_pin_reads_lfs_pointers_and_refuses_other_names_and_overwrite() -> None:
    files = {n: bytes([i]) * 700 for i, n in enumerate(NAMES)}
    calls: list[str] = []

    def opener(url: str, timeout: int = 0) -> Resp:
        calls.append(url)
        return Resp(pointer(files[url.rsplit("/", 1)[1]]))

    with testing.scratch("pin") as d:
        rec = fetch.pin(NAMES, CFG, opener, d / "pins.json")
        assert [f["sha256"] for f in rec["files"]] == [hashlib.sha256(files[n]).hexdigest() for n in NAMES] and all("/raw/b08601e04326c79dfdd32d625aee71d232d685c3/wikitext-103-raw-v1/" in c for c in calls)
        with pytest.raises(core.EngineeringStop, match="written once"):
            fetch.pin(NAMES, CFG, opener, d / "pins.json")
        for bad in (["test-00000-of-00001.parquet"], ["validation-00000-of-00001.parquet"], []):
            with pytest.raises(core.EngineeringStop, match="train shards"):
                fetch.pin(bad, CFG, opener, d / "p2.json")
        with pytest.raises(core.EngineeringStop, match="Git-LFS pointer"):
            fetch.pin(NAMES[:1], CFG, lambda url, timeout=0: Resp(b"not a pointer"), d / "p3.json")
        assert fetch.load_pins(d / "pins.json", CFG)["files"][0]["name"] == NAMES[0]
        with pytest.raises(core.EngineeringStop, match="no pins file"):
            fetch.load_pins(d / "absent.json", CFG)


def pins_for(files: dict[str, bytes]) -> dict[str, Any]:
    return {"repo": CFG["data"]["publisher_repo"], "revision": CFG["data"]["revision"], "configuration": CFG["data"]["configuration"], "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in sorted(files.items())]}


def test_get_appends_started_rows_first_then_completes_them_like_p10s2() -> None:
    files = {NAMES[0]: b"a" * 1000, NAMES[1]: b"b" * 2000}
    with testing.scratch("get") as d:
        ledger = d / "DL.md"  # the throw-away copy (its name is not DOWNLOAD_LEDGER*.md, the real one is never touched)
        ledger.write_text(LEDGER.read_text())
        before_rows = fetch.ledger_total_bytes(ledger)
        lines_before = ledger.read_text().splitlines()
        seen: list[str] = []

        def download(url: str, part: Any, limit: int) -> int:
            last = [ln for ln in ledger.read_text().splitlines() if ln.startswith("|")][-1]
            seen.append(last)  # the started row exists BEFORE the first byte
            name = url.split("?")[0].rsplit("/", 1)[1]
            part.write_bytes(files[name])
            assert limit == len(files[name])
            return len(files[name])

        res = fetch.get(d / "out", ledger, CFG, pins_for(files), download, root=d)
        assert all("| P10-I-S6 |" in r and "| started |" in r for r in seen) and len(seen) == 2
        text = ledger.read_text().splitlines()
        new = [ln for ln in text if "P10-I-S6" in ln]
        assert len(new) == 2 and all(ln.rstrip().endswith("| completed |") for ln in new)
        assert fetch.ledger_total_bytes(ledger) == before_rows + 3000 and res["total_bytes"] == 3000 and res["ledger_total_after"] - res["ledger_total_before"] == 3000
        # the running-total column is recomputed over the whole table, and the old rows are unchanged but for it
        old_cells = [[c.strip() for c in ln.strip("|").split("|")][:7] + [[c.strip() for c in ln.strip("|").split("|")][8]] for ln in lines_before if ln.startswith("| 2026")]
        new_cells = [[c.strip() for c in ln.strip("|").split("|")][:7] + [[c.strip() for c in ln.strip("|").split("|")][8]] for ln in text if ln.startswith("| 2026") and "P10-I-S6" not in ln]
        assert old_cells == new_cells
        assert "revision b08601e04326c79dfdd32d625aee71d232d685c3; SHA-256".replace("revision ", "") in new[0] and "/resolve/b08601e04326c79dfdd32d625aee71d232d685c3/wikitext-103-raw-v1/" in new[0]
        assert (d / "out" / NAMES[0]).read_bytes() == files[NAMES[0]]
        with pytest.raises(core.EngineeringStop, match="not a fresh folder"):
            fetch.get(d / "out", ledger, CFG, pins_for(files), download, root=d)


def test_get_checksum_mismatch_marks_the_row_failed_and_leaves_no_file() -> None:
    files = {NAMES[0]: b"z" * 500}
    pins = pins_for(files)
    pins["files"][0]["sha256"] = "0" * 64
    with testing.scratch("get-bad") as d:
        ledger = d / "DL.md"
        ledger.write_text(LEDGER.read_text())

        def download(url: str, part: Any, limit: int) -> int:
            part.write_bytes(files[NAMES[0]])
            return 500

        with pytest.raises(fetch.FetchRefused, match="pinned SHA-256"):
            fetch.get(d / "out", ledger, CFG, pins, download, root=d)
        last = [ln for ln in ledger.read_text().splitlines() if "P10-I-S6" in ln][-1]
        assert "| failed: FetchRefused |" in last and not (d / "out" / NAMES[0]).exists() and not (d / "out" / (NAMES[0] + ".part")).exists()
        short = pins_for(files)

        def short_dl(url: str, part: Any, limit: int) -> int:
            part.write_bytes(b"z" * 10)
            return 10

        with pytest.raises(fetch.FetchRefused, match="pinned"):
            fetch.get(d / "out2", ledger, CFG, short, short_dl, root=d)
        capped = pins_for({NAMES[0]: b"q" * 100})
        capped["files"][0]["bytes"] = 30_000_000_000
        with pytest.raises(core.EngineeringStop, match="hard stop"):
            fetch.get(d / "out3", ledger, CFG, capped, download, root=d)
