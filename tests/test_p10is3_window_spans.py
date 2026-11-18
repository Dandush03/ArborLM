# ruff: noqa: E501
"""P10IS3 excluded-spans tests (ADR-0026 section 4, C7; ADR-0025 section 4.1): the row layout, the grid and strata (compared with ``studies/p10s2/windows.py`` on a stand-in tokenizer), the draw of P10-S2's ordinary
windows, the ledger reader and writer, and the refusals. No real corpus, no tokenizer package. Self-check only."""

import json
import random
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10i_s3 import core, data  # noqa: E402
from studies.p10i_s3 import window_spans as ws  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG_S2 = tomllib.loads((ROOT / "configs" / "p10s2_transfer.toml").read_text())


class WordTok:
    """Stand-in reference tokenizer: a token is optional whitespace plus a run of non-space characters; ids are the global token index."""

    vocab_size = 10**6
    bos_id = None

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        offs = [(m.start(), m.end()) for m in re.finditer(r"\s*\S+", text)]
        return list(range(len(offs))), offs


def make_rows(seed: int, n_windows: int, window: int = 16, decision: int = 4) -> list[str]:
    """A text of ``n_windows`` windows: window k % 5 == 0 has a marker in tokens 1-4 (marker-like), k % 5 == 1 has a marker only after token 4 (neither stratum), the rest are ordinary. Rows are cut at random places
    and carry multi-byte characters."""
    rng = random.Random(seed)
    words = []
    for k in range(n_windows):
        ws_ = [rng.choice(["alpha", "béta", "gamma", "δelta", "eps", "zeta", "eta", "theta"]) + str(rng.randrange(10)) for _ in range(window)]
        if k % 5 == 0:
            ws_[rng.randrange(0, decision - 1)] = "German"
        elif k % 5 == 1:
            ws_[rng.randrange(decision + 1, window)] = "French"
        words += ws_
    text = " ".join(words) + " tail tail"  # a trailing remainder of two tokens
    cuts = sorted(rng.sample(range(1, len(text)), 12))
    return [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)], strict=True) if text[a:b] != ""] + ["", "ünïcödé"]  # an empty row and a last row; a row may start or end inside a word


def test_row_layout_matches_a_bytewise_map() -> None:
    rows = ["héllo wörld", "", "abc", "δδδ", "x"]
    lay = ws.RowLayout(rows)
    concat = "".join(rows).encode()
    assert lay.total == len(concat) == lay.starts[-1]
    owner = [r for r, t in enumerate(rows) for _ in t.encode()]
    rng = random.Random(935101)
    for _ in range(200):
        a = rng.randrange(0, lay.total)
        b = rng.randrange(a + 1, lay.total + 1)
        brute: dict[int, list[int]] = {}
        for byte in range(a, b):
            brute.setdefault(owner[byte], []).append(byte - lay.starts[owner[byte]])
        expect = [(r, v[0], v[-1] + 1) for r, v in brute.items()]  # end exclusive, one span per row touched
        assert lay.to_row_spans(a, b) == expect
    assert lay.row_of(lay.total - 1) == 4 and lay.row_of(len("héllo wörld".encode())) == 2  # the empty row 1 holds no byte
    with pytest.raises(ValueError):
        lay.to_row_spans(3, 3)
    with pytest.raises(ValueError):
        lay.row_of(lay.total)


def test_char_to_byte_counts_utf8() -> None:
    assert ws.char_to_byte("aé€😀") == [0, 1, 3, 6, 10]


def _classify(rows: list[str], window: int = 16, decision: int = 4) -> tuple[list[int], list[int]]:
    tok = WordTok()
    text = "".join(rows)
    _, offs = tok.encode_offsets(text)
    w = ws.grid_windows(offs, text, window, decision, ws.marker_strings(CFG_S2))
    return [x["index"] for x in w if x["stratum"] == "marker"], [x["index"] for x in w if x["stratum"] == "ordinary"]


def test_grid_and_strata_equal_the_p10s2_implementation() -> None:
    from studies.p10s2.windows import cut_windows, select_windows

    rows = make_rows(935102, 40)
    marker, ordinary = _classify(rows)
    assert marker == [k for k in range(40) if k % 5 == 0] and ordinary == [k for k in range(40) if k % 5 not in (0, 1)]  # by construction; windows with the marker only late are in neither stratum; the 2-token remainder is dropped
    theirs = cut_windows(WordTok(), "".join(rows), {}, 16, 4)  # type: ignore[arg-type]
    t_marker = [w.ids[0] // 16 for w in theirs if w.stratum == "marker"]
    t_ord = [w.ids[0] // 16 for w in theirs if w.stratum == "ordinary"]
    assert (t_marker, t_ord) == (marker, ordinary)
    # the sampled ordinary windows: P10-S2's select_windows with a generator seeded directly
    seed = 935103
    sel = select_windows(theirs, {"marker": len(marker), "ordinary": 7}, torch.Generator().manual_seed(seed), take_all=("marker",), exact={"marker": len(marker)})
    their_sel = sorted(w.ids[0] // 16 for w in sel if w.stratum == "ordinary")
    mine = [ordinary[i] for i in ws.sample_ordinary(len(ordinary), 7, len(marker), seed)]
    assert mine == their_sel and len(set(mine)) == 7


def test_marker_must_lie_wholly_within_tokens_one_to_decision() -> None:
    text = "a b c Germ an e f g h i j k l m n o"  # "Germ"/"an" never form "German" inside tokens 1-4 ... tokens: a b c Germ
    _, offs = WordTok().encode_offsets(text)
    assert ws.grid_windows(offs, text, 16, 4, ws.marker_strings(CFG_S2))[0]["stratum"] == "ordinary"
    text2 = "a b c German e f g h i j k l m n o p"
    _, offs = WordTok().encode_offsets(text2)
    assert ws.grid_windows(offs, text2, 16, 4, ws.marker_strings(CFG_S2))[0]["stratum"] == "marker"
    text3 = "a b c d German e f g h i j k l m n o"  # German at token 5: in neither stratum
    _, offs = WordTok().encode_offsets(text3)
    assert ws.grid_windows(offs, text3, 16, 4, ws.marker_strings(CFG_S2)) == []
    text4 = "a b c d e f g h i j k l m n o x:\ny z"  # a colon followed by a newline anywhere makes the window non-ordinary (token 17 is in the next window)
    _, offs = WordTok().encode_offsets(text4)
    assert [w["stratum"] for w in ws.grid_windows(offs, text4, 16, 4, ws.marker_strings(CFG_S2))] == ["ordinary"]


def test_window_byte_spans_run_from_the_first_byte_of_the_first_token_to_the_last_byte_of_the_last_token() -> None:
    rows = make_rows(935104, 30)
    cfg = {"data": {**CFG_S2["data"], "general_window_tokens": 16, "router_decision_token": 4, "general_windows_marker_like": 6, "general_windows_ordinary": 5}, "seeds": {"partition_streams": [0, 0, 0, 935105]}}
    rec = ws.p10s2_windows(WordTok(), rows, cfg)
    concat = "".join(rows).encode()
    lay = ws.RowLayout(rows)
    marks = [w for w in rec["windows"] if w["stratum"] == "marker"]
    assert [w["grid_index"] for w in marks] == [0, 5, 10, 15, 20, 25]
    for w in rec["windows"]:
        piece = concat[w["start"] : w["end"]].decode()
        words = piece.split()
        assert len(words) == 16 and not piece.endswith(" ") and w["end"] <= lay.total  # 16 tokens, ending at the last byte of the last token
        assert lay.row_of(w["start"]) == w["first_row"] and lay.row_of(w["end"] - 1) == w["last_row"]
    assert len(rec["windows"]) == 11
    # a count other than the configured marker count is an engineering stop, never relaxed
    bad = {**cfg, "data": {**cfg["data"], "general_windows_marker_like": 44}}
    with pytest.raises(core.EngineeringStop, match="marker-like windows"):
        ws.p10s2_windows(WordTok(), rows, bad)


def test_build_excluded_refuses_without_a_ledger_or_a_declaration_and_records_the_declaration(tmp_path: Path) -> None:
    rows = make_rows(935106, 30)
    cfg = {"data": {**CFG_S2["data"], "general_window_tokens": 16, "router_decision_token": 4, "general_windows_marker_like": 6, "general_windows_ordinary": 5}, "seeds": {"partition_streams": [0, 0, 0, 935105]}}
    rec = ws.p10s2_windows(WordTok(), rows, cfg)
    with pytest.raises(core.EngineeringStop, match="exactly one"):
        ws.build_excluded(rows, rec, ledger_path=None, ledger_absent=False)
    with pytest.raises(core.EngineeringStop, match="exactly one"):
        ws.build_excluded(rows, rec, ledger_path=tmp_path / "x.json", ledger_absent=True)
    doc = ws.build_excluded(rows, rec, ledger_path=None, ledger_absent=True)
    assert doc["ledger"]["state"] == "ABSENT-DECLARED" and doc["end_offsets"] == "exclusive"
    # the 44 (here 6) marker-like windows are avoided with the ledger absent: every one of their bytes is covered by the spans
    lay = ws.RowLayout(rows)
    covered = set()
    for r, a, b in map(tuple, doc["spans"]):
        covered |= {(r, i) for i in range(a, b)}
    for w in rec["windows"]:
        s, e = w["start"], w["end"]
        assert all((lay.row_of(i), i - lay.starts[lay.row_of(i)]) in covered for i in range(s, e))
    # the spans are exactly the per-row conversion, sorted and unique
    assert doc["spans"] == sorted(map(list, {sp for w in rec["windows"] for sp in lay.to_row_spans(w["start"], w["end"])}))


def test_ledger_reader_validates_and_the_writer_round_trips(tmp_path: Path) -> None:
    rows = make_rows(935107, 30)
    lay = ws.RowLayout(rows)
    cfg = {"data": {**CFG_S2["data"], "general_window_tokens": 16, "router_decision_token": 4, "general_windows_marker_like": 6, "general_windows_ordinary": 5}, "seeds": {"partition_streams": [0, 0, 0, 935105]}}
    rec = ws.p10s2_windows(WordTok(), rows, cfg)
    entry = ws.ledger_entry(lay, 100, 250, "ADR-0025 ordinary window")
    good = tmp_path / "ledger.json"
    good.write_text(json.dumps({"format": ws.LEDGER_FORMAT, "windows": [entry]}))
    doc = ws.build_excluded(rows, rec, ledger_path=good, ledger_absent=False)
    assert doc["ledger"] == {"state": "read", "path": str(good), "windows": 1}
    assert [r for r, _, _ in lay.to_row_spans(100, 250)] and all(list(sp) in doc["spans"] for sp in lay.to_row_spans(100, 250))
    # a malformed entry, a row mismatch and a foreign shape are refused, never guessed
    for body in ({"windows": [{**entry, "end": entry["start"]}]}, {"windows": [{**entry, "first_row": entry["first_row"] + 1}]}, {"windows": [{**entry, "end": lay.total + 1}]}, [1, 2], {"windows": "x"}):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(body))
        with pytest.raises(core.EngineeringStop):
            ws.read_ledger(p, lay)
    # this study's panels written as ledger entries read back to the same per-row spans
    panel = [(3, 0, 65), (5, 10, 75)]
    body = ws.shared_ledger_body(rows, {"registered": panel}, [])
    p = tmp_path / "shared.json"
    p.write_text(json.dumps(body))
    back = ws.read_ledger(p, lay)
    assert len(back) == 2 and all(w["source"] == "P10-I-S3 panel registered" for w in back)
    assert ws.excluded_spans(lay, back) == sorted(panel)


def test_walk_panels_skips_chunks_that_touch_an_excluded_window() -> None:
    rows = ["x" * 400, "y" * 400]
    lay = ws.RowLayout(rows)
    spans = [(r, o, o + 65) for r in range(2) for o in range(0, 390, 65)]  # chunks of 65 bytes, six per row
    win = lay.to_row_spans(100, 140)  # bytes 100..139 of row 0: touches chunk 1 (65..130) and chunk 2 (130..195)
    p = data.walk_panels(spans, win, start=0, size=3, count=2)
    assert 1 not in p[0] + p[1] and 2 not in p[0] + p[1] and p[0] == [0, 3, 4]
