# ruff: noqa: E501
"""P10IS3 data tests (ADR-0026 sections 3.3, 4; ruling 4): the chunk table, byte-span lineage gates, the panel walk and the ledger, on synthetic text with brute-force expectations. Self-check only."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10i_s3 import core, data  # noqa: E402

C = 65


def texts(rows: int, seed: int, per_row: int = 6) -> list[str]:
    rng = random.Random(seed)
    return ["".join(rng.choice("abcdefghijklmnopqrstuvwxyz ") for _ in range(C * per_row)) for _ in range(rows)]


def test_corpus_table_matches_the_recipe_and_spans() -> None:
    tr, va = texts(20, 935001), texts(10, 935002)
    cs = data.corpus_from_texts(tr, va, eligible_train=120, eligible_validation=60)
    assert cs.train_rows.shape == (120, 65) and cs.val_rows.shape == (60, 65)
    # every row of the table is the bytes of its span in the source row
    for i in (0, 7, 119):
        row, start, end = cs.train_spans[i]
        assert end - start == C and cs.train_rows[i].tolist() == list(tr[row].encode()[start:end])
    for i in (0, 33, 59):
        row, start, end = cs.val_spans[i]
        assert cs.val_rows[i].tolist() == list(va[row].encode()[start:end])
    # rank order: the recipe's SHA-256 rank, ascending (recomputed here)
    import hashlib

    ranks = [hashlib.sha256(f"arborlm-pilot-v1:train:{r}:{o}".encode()).hexdigest() for r, o, _ in cs.train_spans]
    assert ranks == sorted(ranks)
    with pytest.raises(core.EngineeringStop, match="differs from the recorded"):
        data.corpus_from_texts(tr, va, eligible_train=119, eligible_validation=60)


def test_regime_rows_and_the_recorded_reproduction_gate() -> None:
    cs = data.corpus_from_texts(texts(60, 935003, 8), texts(20, 935004, 8), eligible_train=480, eligible_validation=160)
    cfg = {"data": {"rep_ranks": [0, 8], "rep_u_ranks": [8, 16], "fresh_start": 16}}
    assert cs.regime_rows("REP", cfg).shape[0] == 8 and cs.regime_rows("REP-U", cfg).shape[0] == 8 and cs.regime_rows("FRESH", cfg).shape[0] == 480 - 16
    assert cs.regime_rows("REP-U", cfg).tolist() == cs.train_rows[8:16].tolist()
    g = data.reproduction_gate(cs, {"train_4096": "0" * 64})
    assert g["passed"] is False  # a synthetic corpus does not reproduce the recorded hashes
    same = data.reproduction_gate(cs, {})
    assert same["passed"] is True  # nothing expected, nothing differs (the real call passes the recorded constants)


def test_span_overlap_brute_force() -> None:
    rng = random.Random(935005)
    spans = [(rng.randrange(3), rng.randrange(0, 300), 0) for _ in range(40)]
    spans = [(r, s, s + C) for r, s, _ in spans]
    other = [(rng.randrange(3), rng.randrange(0, 300), 0) for _ in range(40)]
    other = [(r, s, s + C) for r, s, _ in other]
    brute = sum(1 for a in spans if any(a[0] == b[0] and a[1] < b[2] and b[1] < a[2] for b in other))
    assert data.count_overlaps(spans, other) == brute
    assert data.overlaps((1, 0, 65), (1, 64, 129)) and not data.overlaps((1, 0, 65), (1, 65, 130)) and not data.overlaps((1, 0, 65), (2, 0, 65))


def _spans(n: int) -> list[data.Span]:
    return [(i // 6, (i % 6) * C, (i % 6) * C + C) for i in range(n)]


def test_lineage_gate_passes_for_disjoint_ranks_and_fails_otherwise() -> None:
    sp = _spans(60)
    ok = data.lineage_gate(sp, {"b101-o301": list(range(8))}, list(range(8)), (8, 16), 16)
    assert ok["passed"] and ok["consumed_ranks"] == 8 and ok["rep_u_overlaps"] == 0
    bad = data.lineage_gate(sp, {"b101-o301": list(range(8)), "b102-o301": [12]}, list(range(8)), (8, 16), 16)
    assert not bad["passed"] and any("consumed rank" in p for p in bad["problems"])
    # a byte-span overlap without a rank overlap: a REP-U chunk whose span lies inside a consumed chunk's
    sp2 = list(sp)
    sp2[9] = (sp[0][0], sp[0][1] + 10, sp[0][1] + 10 + C)
    ov = data.lineage_gate(sp2, {"b": list(range(8))}, list(range(8)), (8, 16), 16)
    assert not ov["passed"] and ov["rep_u_overlaps"] == 1
    dj = data.rep_u_fresh_disjoint(sp, (8, 16), 16, (0, 8))
    assert dj["passed"] and not data.rep_u_fresh_disjoint(sp2, (8, 16), 16, (0, 8))["passed"]


def test_panel_walk_brute_force_exclusions_and_exhaustion() -> None:
    val = _spans(100)
    excluded = [(val[10][0], val[10][1], val[10][2]), (val[12][0], val[12][1] + 30, val[12][1] + 30 + C)]  # exact and partial overlaps
    p = data.walk_panels(val, excluded, start=8, size=5, count=2)
    # brute force
    keep = [r for r in range(8, 100) if not any(val[r][0] == e[0] and val[r][1] < e[2] and e[1] < val[r][2] for e in excluded)]
    assert p[0] == keep[:5] and p[1] == keep[5:10]
    assert 10 not in p[0] + p[1] and 12 not in p[0] + p[1] and not set(p[0]) & set(p[1])
    # the walk starts at the given rank
    assert min(p[0]) >= 8
    with pytest.raises(data.PanelWalkExhausted, match="ENGINEERING STOP"):
        data.walk_panels(val, excluded, start=8, size=50, count=2)
    # a chunk of the first panel is excluded from the second even through an overlapping span
    val2 = list(val)
    val2[9] = (val[8][0], val[8][1] + 20, val[8][1] + 20 + C)  # overlaps val[8]
    p2 = data.walk_panels(val2, [], start=8, size=3, count=2)
    assert 9 not in p2[0] + p2[1] and p2[0][0] == 8


def test_ledger_names_both_panels_in_byte_spans_and_is_deterministic() -> None:
    val = _spans(30)
    led = data.ledger({"registered": [8, 9], "calibration": [10, 11]}, val, [(0, 0, 65)])
    assert led["ledger"]["panels"]["registered"] == [list(val[8]), list(val[9])] and led["ledger"]["excluded_windows"] == [[0, 0, 65]]
    assert led["sha256"] == data.ledger({"registered": [8, 9], "calibration": [10, 11]}, val, [(0, 0, 65)])["sha256"]
    assert led["sha256"] != data.ledger({"registered": [8, 9], "calibration": [10, 12]}, val, [(0, 0, 65)])["sha256"]


def test_chunk_files_are_written_and_hashed(tmp_path: Path) -> None:
    cs = data.corpus_from_texts(texts(10, 935006), texts(5, 935007), eligible_train=60, eligible_validation=30)
    hashes = data.write_chunk_files(cs, tmp_path)
    assert set(hashes) == {"train_all.bytes", "validation_all.bytes", "train_spans.json", "validation_spans.json"}
    assert (tmp_path / "train_all.bytes").stat().st_size == 60 * 65
    from arborlm.io import file_sha256

    assert file_sha256(tmp_path / "train_all.bytes") == hashes["train_all.bytes"]
