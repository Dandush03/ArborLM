# ruff: noqa: E501
"""P10IS6 stage D0 on a small fixture (ADR-0031 sections 6.4, 6.5): exclusion, pools, table, decision, panels, ledger append, gates, refusals. No parquet, no network. Self-check only."""

import copy
import json
import random
from pathlib import Path
from typing import Any

import pytest

from studies.p10i_s6 import core, corpus, d0, model, testing

CFG0 = core.load_config()


def cfg_small() -> dict[str, Any]:
    cfg = copy.deepcopy(dict(CFG0))
    cfg["ladder"] = {**CFG0["ladder"], "base_updates": 1, "below_updates": 1}  # U_k = 2^k: a stream needs 8 * 2^k chunks
    cfg["data"] = {**CFG0["data"], "pool_chunks_for_umax": 8 * 16, "panel_walk_start": 0}
    cfg["setting"] = {**CFG0["setting"], "panel_chunks": 8}
    return cfg


def text(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("abcdefghij \n") for _ in range(n))


def wiki(rng: random.Random, articles: int, rows_each: int = 3, n: int = 300) -> list[str]:
    rows = [text(rng, 200)]
    for a in range(articles):
        rows.append(f" = Article {rng.random()} {a} = \n")
        rows += [text(rng, n) for _ in range(rows_each)]
    return rows


def make_ledger(path: Path) -> None:
    body = {"panels": {"s3-registered": [[0, 0, 65]], "s3-calibration": [[1, 0, 65]]}, "excluded_windows": [[2, 0, 65]], "panel_ranks": {}}
    path.write_text(json.dumps({"ledger": body, "sha256": "x"}), encoding="utf-8")


def test_d0_end_to_end_on_a_fixture() -> None:
    cfg = cfg_small()
    rng = random.Random(7)
    wt2_train, wt2_val = wiki(rng, 10), wiki(rng, 12, 3, 400)
    rows103 = wiki(rng, 120)
    leak = wt2_train[6]  # a WikiText-2 train row placed whole inside one WikiText-103 article: that article must go
    rows103.insert(20, leak)
    with testing.scratch("d0") as d:
        ledger = d / "panel_ledger.json"
        make_ledger(ledger)
        m = d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "out", cfg)
        assert all(g["passed"] for g in m["gates"].values()) and m["gates"]["overlap_with_E"]["passed"] and m["gates"]["select_equal"]["passed"]
        assert m["counts"]["articles_removed"] >= 1 and m["counts"]["chunks_in_removed_articles"] >= 1
        t = m["table"]
        assert t["rows"] == t["registered_rows"] + t["calibration_rows"] and m["k_max"] >= 2 and m["decision"]["definition"] in ("mod3", "mod2")
        assert (d / "out" / t["name"]).stat().st_size == t["rows"] * 65
        tab = model.map_table(d / "out" / t["name"], t["rows"])
        e = corpus.excluded_digests([*wt2_train, *wt2_val])
        import hashlib

        assert not any(hashlib.sha256(bytes(tab[i].tolist())).digest() in e for i in range(tab.shape[0]))  # nothing of WikiText-2 train or validation is in either pool
        # panels: 8 + 8 chunks of validation text, disjoint from the spans of the ledger, appended to it
        reg, cal = m["panels"]["registered"], m["panels"]["calibration"]
        assert len(reg) == len(cal) == 8 and not set(reg) & set(cal)
        led = json.loads(ledger.read_text())
        assert set(d0.LEDGER_KEYS) <= set(led["ledger"]["panels"]) and len(led["ledger"]["panels"]["p10i-s6-registered"]) == 8 and "s3-registered" in led["ledger"]["panels"]
        val, spans, _ = d0.validation_candidates(wt2_train, wt2_val)
        old = set(d0.spans_in_ledger({"ledger": {"panels": {"a": [[0, 0, 65], [1, 0, 65]]}, "excluded_windows": [[2, 0, 65]]}}))
        assert not any(spans[r] in old for r in reg + cal)
        pb = (d / "out" / "panels.bytes").read_bytes()
        assert len(pb) == 16 * 65 and pb[: 8 * 65] == b"".join(val[r].payload for r in reg)
        assert set(m["files"]) == {t["name"], "panels.bytes"} and m["near_duplicate_share_registered_panel"]["panel_chunks"] == 8 and m["eligible_validation_spans_left_for_panels"] >= 0
        assert m["gates"]["rss"]["peak_rss_bytes"] > 0
        with pytest.raises(core.EngineeringStop, match="written once"):
            d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "out", cfg)


def test_d0_refuses_a_ledger_key_that_exists_a_failed_reproduction_and_a_too_small_corpus() -> None:
    cfg = cfg_small()
    rng = random.Random(8)
    wt2_train, wt2_val, rows103 = wiki(rng, 10), wiki(rng, 12, 3, 400), wiki(rng, 120)
    with testing.scratch("d0b") as d:
        ledger = d / "l.json"
        make_ledger(ledger)
        d0.append_ledger(ledger, {"x": [0]}, [(0, 0, 65)])
        with pytest.raises(core.EngineeringStop, match="already holds"):
            d0.append_ledger(ledger, {"x": [0]}, [(0, 0, 65)])
        make_ledger(ledger)
        with pytest.raises(core.EngineeringStop, match="gate failed"):
            d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "o1", cfg, expect_p1_train_sha="0" * 64)  # the old recorded hash is not reproduced
        make_ledger(ledger)
        tiny = wiki(rng, 3, 1, 100)
        with pytest.raises(core.EngineeringStop, match="CORPUS TOO SMALL"):
            d0.prepare(iter(tiny), wt2_train, wt2_val, ledger, d / "o2", cfg)
        with pytest.raises(core.EngineeringStop, match="exhausted|ran out"):
            d0.prepare(iter(rows103), wt2_train, wt2_val[:3], ledger, d / "o3", cfg)  # the panel walk runs out: engineering stop before Decision 2


def test_ledger_byte_ranges_in_the_concatenated_rows_are_converted_to_row_spans() -> None:
    """Audit R5(c): the shared ledger may hold byte offsets in the concatenated validation rows; ``walk_panels`` overlaps (row, start, end) spans, so each range is split over the rows it touches."""
    lengths = [100, 50, 200]
    led = {"ledger": {"panels": {"a": [[0, 10, 75], {"start": 90, "end": 170}, [160, 300]]}, "excluded_windows": [{"byte_start": 0, "byte_end": 5}]}}
    got = d0.spans_in_ledger(led, lengths)
    assert got == [(0, 10, 75), (0, 90, 100), (1, 0, 50), (2, 0, 20), (2, 10, 150), (0, 0, 5)]
    with pytest.raises(core.EngineeringStop, match="row lengths"):
        d0.spans_in_ledger(led)
    with pytest.raises(core.EngineeringStop, match="unknown shape"):
        d0.spans_in_ledger({"ledger": {"panels": {"a": [[1, 2, 3, 4]]}}}, lengths)
    from studies.p10i_s3.data import overlaps

    assert any(overlaps((1, 20, 85), s) for s in got) and not any(overlaps((2, 150, 215), s) for s in got)
