# ruff: noqa: E501
"""P10IS6 stage D0 on a small fixture (ADR-0031 sections 6.4, 6.5; addendum 2 rulings 16 and 17): exclusion, pools, table, decision, panels, the shared ledger in its REAL format, the P10-I-S3 excluded set, gates, rerunnability. No parquet, no network. Self-check only."""

import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import pytest

from studies.p10i_s3.data import count_overlaps
from studies.p10i_s6 import core, corpus, d0, model, testing

CFG0 = core.load_config()


def cfg_small(s3_sha: str | None = None) -> dict[str, Any]:
    cfg = copy.deepcopy(dict(CFG0))
    cfg["ladder"] = {**CFG0["ladder"], "base_updates": 1, "below_updates": 1}
    cfg["data"] = {**CFG0["data"], "pool_chunks_for_umax": 8 * 16, "panel_walk_start": 0, **({"s3_excluded_spans_sha256": s3_sha} if s3_sha else {})}
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


def real_format_ledger(path: Path, val_rows: list[str]) -> bytes:
    """A ledger in the REAL format: ``format``, ``p10is2`` and ``windows`` (byte windows, end-exclusive, in the concatenation of the validation rows), canonical JSON with a trailing newline."""
    lengths = [len(r.encode()) for r in val_rows]
    starts = d0.row_starts(lengths)
    windows = [
        {"start": starts[3] + 5, "end": starts[3] + 70, "first_row": 3, "last_row": 3, "source": "P10-I-S3 panel registered"},
        {"start": starts[6], "end": starts[7] + 30, "first_row": 6, "last_row": 7, "source": "P10IS2-partq GEN ordinary window", "per_row": [[6, 0, lengths[6]], [7, 0, 30]]},
    ]
    rec = {"format": d0.LEDGER_FORMAT, "p10is2": {"end_exclusive": True, "owner": "x", "unit": "byte offsets in the concatenation of the rows"}, "windows": windows}
    raw = (json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    return raw


def s3_file(path: Path, spans: list[list[int]]) -> str:
    path.write_text(json.dumps({"format": "p10i-s3-excluded-spans-v1", "end_offsets": "exclusive", "spans": spans, "windows": len(spans)}), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_d0_end_to_end_on_a_fixture() -> None:
    rng = random.Random(7)
    wt2_train, wt2_val = wiki(rng, 10), wiki(rng, 12, 3, 400)
    rows103 = wiki(rng, 120)
    rows103.insert(20, wt2_train[6])  # a WikiText-2 train row inside one WikiText-103 article: that article must go
    with testing.scratch("d0") as d:
        ledger = d / "panel_ledger.json"
        raw = real_format_ledger(ledger, wt2_val)
        s3_spans = [[9, 0, 120], [10, 0, 400]]  # P10-I-S3's own excluded set (row spans)
        sha = s3_file(d / "excluded_spans.json", s3_spans)
        cfg = cfg_small(sha)
        spans, got_sha = d0.load_s3_excluded(d / "excluded_spans.json", cfg)
        assert got_sha == sha and spans == [(9, 0, 120), (10, 0, 400)]
        m = d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "out", cfg, s3_excluded=spans, s3_excluded_sha256=sha)
        assert all(g["passed"] for g in m["gates"].values()) and m["gates"]["panels_disjoint_from_excluded"]["excluded_spans"] >= 4 and m["s3_excluded_spans_sha256"] == sha
        assert m["counts"]["articles_removed"] >= 1 and m["counts"]["chunks_in_removed_articles"] >= 1 and m["k_max"] >= 2
        t = m["table"]
        tab = model.map_table(d / "out" / t["name"], t["rows"])
        e = corpus.excluded_digests([*wt2_train, *wt2_val])
        assert not any(hashlib.sha256(bytes(tab[i].tolist())).digest() in e for i in range(tab.shape[0]))
        # the ledger: every old byte and key unchanged, 16 windows appended in the file's own format, hash before and after recorded
        new_raw = ledger.read_bytes()
        old, new = json.loads(raw), json.loads(new_raw)
        assert new["windows"][:2] == old["windows"] and {k: v for k, v in new.items() if k != "windows"} == {k: v for k, v in old.items() if k != "windows"}
        added = new["windows"][2:]
        assert len(added) == 16 and [w["source"] for w in added[:8]] == [d0.SOURCES[0]] * 8 and [w["source"] for w in added[8:]] == [d0.SOURCES[1]] * 8 and all(set(w) == {"start", "end", "first_row", "last_row", "source"} for w in added)
        assert m["panels"]["ledger_append"] == {"sha256_before": hashlib.sha256(raw).hexdigest(), "sha256_after": hashlib.sha256(new_raw).hexdigest(), "entries_added": 16, "windows_before": 2, "windows_after": 18}
        # the 16 new panel chunks overlap no ledger window and no P10-I-S3 span
        lengths = [len(r.encode()) for r in wt2_val]
        excl = [*d0.spans_in_ledger(old, lengths), *spans]
        val, vspans, _ = d0.validation_candidates(wt2_train, wt2_val)
        panel = [vspans[r] for r in m["panels"]["registered"] + m["panels"]["calibration"]]
        assert count_overlaps(panel, excl) == 0 and len(panel) == 16
        pb = (d / "out" / "panels.bytes").read_bytes()
        assert len(pb) == 16 * 65 and pb[: 8 * 65] == b"".join(val[r].payload for r in m["panels"]["registered"])
        again = d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "out", cfg, s3_excluded=spans)  # a rerun on a complete verified output with the ledger already holding these windows changes nothing
        assert again == m and ledger.read_bytes() == new_raw
        assert not list((d / "out").glob("_work"))  # the work folder was moved into place


def test_a_failed_d0_leaves_nothing_that_makes_a_rerun_refuse_and_the_ledger_untouched() -> None:
    rng = random.Random(8)
    wt2_train, wt2_val, rows103 = wiki(rng, 10), wiki(rng, 12, 3, 400), wiki(rng, 120)
    with testing.scratch("d0b") as d:
        ledger = d / "l.json"
        raw = real_format_ledger(ledger, wt2_val)
        cfg = cfg_small()
        with pytest.raises(core.EngineeringStop, match="gate failed"):
            d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "o", cfg, expect_p1_train_sha="0" * 64)  # the old recorded hash is not reproduced
        assert ledger.read_bytes() == raw  # the ledger is appended LAST: a gate failure never touches it
        assert len(list((d / "o").glob("_failed-*"))) == 1 and not (d / "o" / "d0_manifest.json").exists() and not list((d / "o").glob("*.u8"))
        m = d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / "o", cfg)  # the rerun is not refused by leftovers
        assert m["panels"]["ledger_append"]["entries_added"] == 16 and len(list((d / "o").glob("_failed-*"))) == 1  # the partial output is kept aside, not deleted
        with pytest.raises(core.EngineeringStop, match="already holds"):
            d0.append_panels(ledger, [{"start": 0, "end": 1, "first_row": 0, "last_row": 0, "source": d0.SOURCES[0]}])
        tiny = wiki(rng, 3, 1, 100)
        ledger2 = d / "l2.json"
        raw2 = real_format_ledger(ledger2, wt2_val)
        with pytest.raises(core.EngineeringStop, match="CORPUS TOO SMALL"):
            d0.prepare(iter(tiny), wt2_train, wt2_val, ledger2, d / "o2", cfg)
        with pytest.raises(core.EngineeringStop, match="ran out|exhausted"):
            d0.prepare(iter(rows103), wt2_train, wt2_val[:3], ledger2, d / "o3", cfg)
        assert ledger2.read_bytes() == raw2


def test_ledger_reader_refuses_other_formats_and_the_s3_file_is_pinned() -> None:
    with testing.scratch("fmt") as d:
        (d / "a.json").write_text(json.dumps({"ledger": {"panels": {}}, "sha256": "x"}))
        with pytest.raises(core.EngineeringStop, match="not a p10i-panel-ledger-v1"):
            d0.read_ledger(d / "a.json")
        (d / "b.json").write_text(json.dumps({"format": d0.LEDGER_FORMAT, "p10is2": {"end_exclusive": True}, "windows": [{"start": 5, "end": 5, "first_row": 0, "last_row": 0}]}))
        with pytest.raises(core.EngineeringStop, match="integer start"):
            d0.read_ledger(d / "b.json")
        (d / "c.json").write_text(json.dumps({"format": d0.LEDGER_FORMAT, "p10is2": {"end_exclusive": True}, "windows": []}, indent=2))
        with pytest.raises(core.EngineeringStop, match="canonical form"):
            d0.append_panels(d / "c.json", [])
        sha = s3_file(d / "s3.json", [[0, 0, 1]])
        with pytest.raises(core.EngineeringStop, match="does not hash"):
            d0.load_s3_excluded(d / "s3.json", CFG0)  # not the pinned file
        (d / "s3b.json").write_text(json.dumps([[0, 0, 1]]))
        with pytest.raises(core.EngineeringStop):
            d0.load_s3_excluded(d / "s3b.json", cfg_small(hashlib.sha256((d / "s3b.json").read_bytes()).hexdigest()))  # a bare list of triples is not the file's format
        assert sha


def test_byte_windows_of_the_concatenated_rows_become_row_spans() -> None:
    lengths = [100, 50, 200]
    starts = d0.row_starts(lengths)
    assert d0.window_spans(90, 170, starts, lengths) == [(0, 90, 100), (1, 0, 50), (2, 0, 20)]
    assert d0.window_spans(100, 150, starts, lengths) == [(1, 0, 50)] and d0.window_spans(150, 151, starts, lengths) == [(2, 0, 1)]  # end-exclusive
    led = {"windows": [{"start": 0, "end": 5, "first_row": 0, "last_row": 0}]}
    assert d0.spans_in_ledger(led, lengths) == [(0, 0, 5)]
    with pytest.raises(core.EngineeringStop, match="row lengths"):
        d0.spans_in_ledger(led, [])
    from studies.p10i_s3.data import overlaps

    assert overlaps((1, 20, 85), (1, 0, 50)) and not overlaps((2, 150, 215), (2, 10, 150))


def test_n1_a_failure_before_or_right_after_the_append_is_rerunnable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Audit N1: the manifest in its final form is in place and verified BEFORE the append; the append is the last act. A crash before it leaves the ledger untouched and the rerun performs only the append; a crash right after it leaves exactly these windows and the rerun accepts them."""
    rng = random.Random(9)
    wt2_train, wt2_val, rows103 = wiki(rng, 10), wiki(rng, 12, 3, 400), wiki(rng, 120)
    cfg = cfg_small()
    real_commit = d0.commit_append

    def run(d: Path, ledger: Path, tag: str) -> dict[str, Any]:
        return d0.prepare(iter(rows103), wt2_train, wt2_val, ledger, d / tag, cfg)

    with testing.scratch("n1a") as d:
        ledger = d / "l.json"
        raw = real_format_ledger(ledger, wt2_val)

        def boom(path: Path, plan: Any) -> Any:
            raise OSError("disk full before the append")

        monkeypatch.setattr(d0, "commit_append", boom)
        with pytest.raises(OSError):
            run(d, ledger, "o")
        assert ledger.read_bytes() == raw and (d / "o" / "d0_manifest.json").is_file()  # output complete and verified, ledger untouched
        d0.verify_output(d / "o")
        monkeypatch.setattr(d0, "commit_append", real_commit)
        m = run(d, ledger, "o")  # the rerun does only the append
        assert hashlib.sha256(ledger.read_bytes()).hexdigest() == m["panels"]["ledger_append"]["sha256_after"] and len(json.loads(ledger.read_bytes())["windows"]) == 2 + 16
    with testing.scratch("n1b") as d:
        ledger = d / "l.json"
        raw = real_format_ledger(ledger, wt2_val)

        def after(path: Path, plan: Any) -> Any:
            real_commit(path, plan)
            raise OSError("killed right after the append")

        monkeypatch.setattr(d0, "commit_append", after)
        with pytest.raises(OSError):
            run(d, ledger, "o")
        done = ledger.read_bytes()
        assert done != raw
        monkeypatch.setattr(d0, "commit_append", real_commit)
        m = run(d, ledger, "o")  # accepted: exactly this study's windows, complete verified output
        assert ledger.read_bytes() == done and m["panels"]["ledger_append"]["entries_added"] == 16
        rec = json.loads(done)
        rec["windows"][-1]["end"] += 1
        ledger.write_bytes((json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode())
        with pytest.raises(core.EngineeringStop, match="not exactly this D0's panels"):
            run(d, ledger, "o")  # any other mismatch still refuses
        rec = json.loads(done)
        del rec["windows"][-1]
        ledger.write_bytes((json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode())
        with pytest.raises(core.EngineeringStop, match="not exactly this D0's panels"):
            run(d, ledger, "o")  # a partial append is refused
        (d / "o" / "panels.bytes").write_bytes(b"x")
        with pytest.raises(core.EngineeringStop, match="does not hash"):
            run(d, ledger, "o")  # an unverified output is refused


REAL_LEDGER = Path("/Users/daniellaloush/dandush03/ArborLM/data/p10i-shared/panel_ledger.json")


@pytest.mark.skipif(not REAL_LEDGER.is_file(), reason="the lead's shared ledger is not on this machine")
def test_n1_primitives_on_a_copy_of_the_real_ledger() -> None:
    before = hashlib.sha256(REAL_LEDGER.read_bytes()).hexdigest()
    add = [{"start": 10 * i, "end": 10 * i + 5, "first_row": 0, "last_row": 0, "source": d0.SOURCES[i % 2]} for i in range(1024)]
    with testing.scratch("n1real") as d:
        copy_ = d / "ledger.json"
        copy_.write_bytes(REAL_LEDGER.read_bytes())
        assert d0.ledger_state(copy_, add) == "absent"
        plan = d0.plan_append(copy_, add)  # planning writes nothing
        assert hashlib.sha256(copy_.read_bytes()).hexdigest() == before
        info = d0.commit_append(copy_, plan)
        assert info["entries_added"] == 1024 and info["windows_after"] == info["windows_before"] + 1024 and d0.ledger_state(copy_, add) == "present"
        with pytest.raises(core.EngineeringStop, match="not exactly"):
            d0.ledger_state(copy_, add[:-1])
        with pytest.raises(core.EngineeringStop, match="changed since"):
            d0.commit_append(copy_, plan)  # the file is no longer the one the plan was made on
    assert hashlib.sha256(REAL_LEDGER.read_bytes()).hexdigest() == before
