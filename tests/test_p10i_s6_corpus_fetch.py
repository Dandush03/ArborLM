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


# ------------------------------------------------------------------------------------------------ fetch
class Resp:
    def __init__(self, data: bytes, length: int | None = None) -> None:
        self.data, self.pos = data, 0
        self.headers = {"Content-Length": str(len(data) if length is None else length)}

    def __enter__(self) -> "Resp":
        return self

    def __exit__(self, *a: Any) -> None:
        return None

    def read(self, n: int = -1) -> bytes:
        n = len(self.data) - self.pos if n < 0 else n
        out = self.data[self.pos : self.pos + n]
        self.pos += len(out)
        return out


def fixture(files: dict[str, bytes], *, lie_sha: set[str] | None = None, lie_len: dict[str, int] | None = None) -> tuple[Any, list[str]]:
    cfg = CFG["data"]
    conf = cfg["configuration"]
    listing = [{"type": "file", "path": f"{conf}/{n}", "size": 1, "lfs": {"oid": ("0" * 64 if n in (lie_sha or set()) else hashlib.sha256(b).hexdigest()), "size": len(b)}} for n, b in files.items()]
    listing += [{"type": "file", "path": f"{conf}/test-00000-of-00001.parquet", "lfs": {"oid": "1" * 64, "size": 5}}, {"type": "file", "path": f"{conf}/validation-00000-of-00001.parquet", "lfs": {"oid": "2" * 64, "size": 5}}, {"type": "file", "path": "README.md"}]
    calls: list[str] = []

    def opener(url: str, timeout: int = 0) -> Resp:
        calls.append(url)
        if "/api/datasets/" in url:
            return Resp(json.dumps(listing).encode())
        name = url.split("?")[0].rsplit("/", 1)[1]
        return Resp(files[name], (lie_len or {}).get(name))

    return opener, calls


def test_fetch_writes_ledger_rows_before_fetching_and_verifies() -> None:
    files = {"train-00001-of-00002.parquet": b"b" * 1000, "train-00000-of-00002.parquet": b"a" * 2000}
    opener, calls = fixture(files)
    with testing.scratch("fetch") as d:
        res = fetch.fetch(d / "out", d / "ledger", CFG, opener)
        assert res["total_bytes"] == 3000 and [f["file"] for f in res["files"]] == sorted(files)
        rows = [json.loads(x) for x in (d / "ledger" / "DOWNLOAD_LEDGER_S6.jsonl").read_text().splitlines()]
        assert [r["status"] for r in rows] == ["PLANNED", "PLANNED", "COMPLETE", "COMPLETE"]  # every row is on the ledger before the first byte
        assert all(r["expected_sha256"] for r in rows[:2]) and rows[-1]["running_total_bytes"] == 3000
        assert not any("test-" in c or "validation-" in c for c in calls if "/resolve/" in c)  # the other splits are never fetched
        assert all("b08601e04326c79dfdd32d625aee71d232d685c3" in c for c in calls)
        assert (d / "ledger" / "DOWNLOAD_LEDGER_S6.md").read_text().count("\n") == 6
        again = fetch.fetch(d / "out", d / "ledger", CFG, opener)  # existing verified files are kept
        assert again["total_bytes"] == 3000


def test_fetch_checksum_mismatch_oversize_and_hard_stop() -> None:
    files = {"train-00000-of-00001.parquet": b"z" * 500}
    opener, _ = fixture(files, lie_sha={"train-00000-of-00001.parquet"})
    with testing.scratch("fetch-bad") as d, pytest.raises(core.EngineeringStop, match="differ from the LFS"):
        fetch.fetch(d / "out", d / "ledger", CFG, opener)
    with testing.scratch("fetch-bad2") as d:
        rows = []
        try:
            fetch.fetch(d / "out", d / "ledger", CFG, opener)
        except core.EngineeringStop:
            rows = [json.loads(x) for x in (d / "ledger" / "DOWNLOAD_LEDGER_S6.jsonl").read_text().splitlines()]
        assert rows[-1]["status"] == "FAILED" and (d / "out" / ".staging-train-00000-of-00001.parquet").exists()  # the failed file is kept as evidence
    over, _ = fixture(files, lie_len={"train-00000-of-00001.parquet": 10**9})
    with testing.scratch("fetch-over") as d, pytest.raises(core.EngineeringStop, match="exceeds the expected"):
        fetch.fetch(d / "out", d / "ledger", CFG, over)
    cfg = copy.deepcopy(dict(CFG))
    cfg["data"] = {**CFG["data"], "download_hard_stop_bytes": 100}
    with pytest.raises(core.EngineeringStop, match="hard stop"):
        fetch.plan_from_listing([{"type": "file", "path": f"{CFG['data']['configuration']}/train-00000-of-00001.parquet", "lfs": {"oid": "a" * 64, "size": 500}}], cfg)
    with pytest.raises(core.EngineeringStop, match="no train parquet"):
        fetch.plan_from_listing([], CFG)
