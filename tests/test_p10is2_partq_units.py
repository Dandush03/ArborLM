# ruff: noqa: E501
"""P10IS2 Part Q units (ADR-0025 sections 4.2, 4.3, 4.4, 6; rulings G15, G17, G18). Expected values are hand-written or computed by independent brute-force code in this file, not by the helper
under test. Synthetic data only; seeds 934001-934999. Self-check only: not independent review."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from p10is2_fixtures import (  # noqa: E402
    CFG_Q,
    CFG_T,
    TEST_ALLOWED,
    LexTeacher,
    lex_teachers,
    small_cfg,
)

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common.panel_ledger import (  # noqa: E402
    PanelLedger,
    RowMap,
    Span,
    SpanError,
    char_to_byte_offsets,
    overlap,
    per_row_spans,
)
from studies.p10is2.partq import batches as bt  # noqa: E402
from studies.p10is2.partq import generation as gen  # noqa: E402
from studies.p10is2.partq import labels, qualify, split  # noqa: E402
from studies.p10is2.partq.teacher import FakeTeacher  # noqa: E402
from studies.p10s2.data import Item  # noqa: E402
from studies.p10s2.filtering import FilterSetting  # noqa: E402

Z = 1.959963984540054


# --- Wilson and the sampling-risk table of section 4.2 ----------------------------------------------------------------------------------------
def brute_wilson_lower(k: int, n: int) -> float:
    p = k / n
    return (p + Z * Z / (2 * n) - Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))) / (1 + Z * Z / n)


@pytest.mark.parametrize(("n", "errors"), [(35, 0), (53, 1), (69, 2), (84, 3)])
def test_wilson_threshold_counts_of_section_4_2(n: int, errors: int) -> None:
    """Section 4.2: a lower bound of 0.90 needs at least 35 accepted with no error, 53 with one, 69 with two, 84 with three."""
    assert brute_wilson_lower(n - errors, n) >= 0.90 > brute_wilson_lower(n - errors - 1, n - 1) if errors == 0 else brute_wilson_lower(n - errors, n) >= 0.90
    assert qualify.wilson(n - errors, n, Z)[0] >= 0.90
    assert qualify.wilson_error_allowance(n, Z, 0.90) == errors
    assert qualify.wilson_error_allowance(n - 1, Z, 0.90) in (None, errors - 1)


@pytest.mark.parametrize(("accepted", "tolerated"), [(104, 4), (41, 0), (416, 29), (164, 8)])
def test_errors_tolerated_table_of_section_4_2(accepted: int, tolerated: int) -> None:
    assert qualify.wilson_error_allowance(accepted, Z, 0.90) == tolerated


def test_wilson_matches_brute_force_on_grid() -> None:
    for n in (1, 5, 40, 150, 500):
        for k in range(0, n + 1, max(1, n // 7)):
            lo, hi = qualify.wilson(k, n, Z)
            assert lo == pytest.approx(max(0.0, brute_wilson_lower(k, n)), abs=1e-12) or k in (0, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0


def test_wilson_empty_is_the_whole_interval() -> None:
    assert qualify.wilson(0, 0, Z) == (0.0, 1.0)


# --- Q3: selection and ties -------------------------------------------------------------------------------------------------------------------
def row(tau: float, rho1: float, rho2: float, share: float, lower: float, accepted: int = 100, correct: int = 99):  # type: ignore[no-untyped-def]
    return {"tau": tau, "rho1": rho1, "rho2": rho2, "accepted": accepted, "accepted_share": share, "correct": correct, "precision": correct / max(1, accepted), "wilson_lower": lower, "wilson_upper": 1.0}


def test_q3_picks_largest_share_whose_lower_bound_passes() -> None:
    table = [row(-0.05, 0.5, 2.0, 0.10, 0.95), row(-0.30, 0.5, 2.0, 0.30, 0.91), row(-0.60, 0.5, 2.0, 0.50, 0.85)]
    r = qualify.select_filter(table, CFG_Q)
    assert (r.setting.tau, r.setting.rho1) == (-0.30, 0.5)  # type: ignore[union-attr]
    assert r.candidates == 2


def test_q3_ties_larger_tau_then_narrower_range() -> None:
    table = [row(-0.30, 0.5, 2.0, 0.30, 0.95), row(-0.20, 0.5, 2.0, 0.30, 0.95), row(-0.20, 0.6, 1.6, 0.30, 0.95)]
    s = qualify.select_filter(table, CFG_Q).setting
    assert (s.tau, s.rho1, s.rho2) == (-0.20, 0.6, 1.6)  # type: ignore[union-attr]
    table2 = [row(-0.30, 0.6, 1.6, 0.30, 0.95), row(-0.30, 0.5, 2.0, 0.30, 0.95)]
    assert qualify.select_filter(table2, CFG_Q).setting.rho1 == 0.6  # type: ignore[union-attr]


def test_q3_fails_when_no_setting_reaches_the_bound_and_ignores_empty_settings() -> None:
    assert qualify.select_filter([row(-0.1, 0.5, 2.0, 0.4, 0.899)], CFG_Q).setting is None
    assert qualify.select_filter([row(-0.1, 0.5, 2.0, 0.0, 1.0, accepted=0, correct=0)], CFG_Q).setting is None


def test_grid_has_24_settings_in_the_spec_order() -> None:
    g = qualify.settings_grid(CFG_Q)
    assert len(g) == 24 and g[0] == FilterSetting(-0.05, 0.5, 2.0) and g[1] == FilterSetting(-0.05, 0.6, 1.6) and g[-1] == FilterSetting(-0.6, 0.6, 1.6)


def test_q1_q2_hand_values() -> None:
    assert qualify.q1({"A": 0.55, "B": 0.5499}, CFG_Q) == {"A": True, "B": False}
    t = {"A": {"A": 0.80, "B": 0.10}, "B": {"A": 0.20, "B": 0.70}}
    s = {"A": 0.30, "B": 0.45}
    q2 = qualify.q2(t, s, CFG_Q)
    assert q2["A"]["margin"] == pytest.approx(0.80 - 0.30) and q2["A"]["pass"]
    assert q2["B"]["margin"] == pytest.approx(0.70 - 0.45) and not q2["B"]["pass"]  # student 0.45 is the larger: 0.25 < 0.30


def test_q4_reads_only_on_150_accepted_and_needs_090() -> None:
    from studies.p10s2.filtering import Output

    f = FilterSetting(-1.0, 0.0, 9.0)
    outs = [Output("a b", f"x{i} y", -0.1) for i in range(200)]
    good = [0.7] * 180 + [0.2] * 20
    r = qualify.precision_on_check(outs, good, f, CFG_Q)
    assert r["accepted"] == 200 and r["read_ok"] and r["precision"] == 0.9 and r["pass"]
    r2 = qualify.precision_on_check(outs[:149], [0.7] * 149, f, CFG_Q)
    assert not r2["read_ok"] and not r2["pass"]
    r3 = qualify.precision_on_check(outs, [0.7] * 179 + [0.2] * 21, f, CFG_Q)
    assert r3["read_ok"] and not r3["pass"]  # 0.895


# --- Q_check: the three stopping rules --------------------------------------------------------------------------------------------------------
def make_items(n: int) -> list[Item]:
    return [Item(f"k{i} w", f"k{i} w", {"A": (f"r{i}",), "B": (f"s{i}",)}, i) for i in range(n)]


class AcceptEvery(FakeTeacher):
    """Accepts every k-th source: score -0.05 for accepted, -0.9 for the rest; the output is the source with a suffix (differs from the source, same word count)."""

    def __init__(self, k: int) -> None:
        super().__init__("T")
        self.k = k

    def generate_batch(self, sources):  # type: ignore[no-untyped-def]
        from studies.p10is2.partq.teacher import Generated

        self.calls += 1
        return [Generated((i,), s.replace("w", "z"), -0.05 if int(s.split()[0][1:]) % self.k == 0 else -0.9) for i, s in enumerate(sources)]


def test_qcheck_stops_at_first_block_boundary_with_enough_accepted(tmp_path: Path) -> None:
    items = make_items(400)
    blocks = [items[i : i + 40] for i in range(0, 400, 40)]
    t = AcceptEvery(4)  # 10 accepted per block of 40
    f = FilterSetting(-0.3, 0.5, 2.0)
    c = gen.count_phase(t, blocks, f, tmp_path, target=25, size=8)
    assert c.stop_block == 2 and c.blocks_drawn == 3 and c.accepted == 30 and not c.exhausted and c.accepted_by_block == [10, 10, 10]
    assert not (tmp_path / "block_003").exists()  # no block after the stop is drawn


def test_qcheck_exhausted_when_reserve_ends(tmp_path: Path) -> None:
    items = make_items(80)
    c = gen.count_phase(AcceptEvery(4), [items[:40], items[40:]], FilterSetting(-0.3, 0.5, 2.0), tmp_path, target=500, size=8)
    assert c.exhausted and c.stop_block is None and c.blocks_drawn == 2 and c.accepted == 20


def test_qcheck_no_reference_before_stop_and_one_call_over_all_drawn_blocks(tmp_path: Path) -> None:
    items = make_items(400)
    blocks = [items[i : i + 40] for i in range(0, 400, 40)]
    t, f = AcceptEvery(4), FilterSetting(-0.3, 0.5, 2.0)
    c = gen.count_phase(t, blocks, f, tmp_path, target=25, size=8)
    asked: list[str] = []

    def provider(it: Item) -> list[str]:
        asked.append(it.key)
        return list(it.refs["A"])

    assert asked == []  # nothing read during counting
    with pytest.raises(gen.QCheckViolation):
        gen.finalize(t, blocks, c, f, tmp_path, tmp_path / "stop.json", provider, small_cfg(), size=8)  # no recorded stop
    assert asked == []
    gen.record_stop(tmp_path / "stop.json", c)
    res = gen.finalize(t, blocks, c, f, tmp_path, tmp_path / "stop.json", provider, small_cfg(), size=8)
    assert sorted(asked) == sorted(it.key for b in blocks[:3] for it in b)  # every item of every block drawn, exactly once, none of the blocks after
    assert len(asked) == 120 and res["accepted"] == 30 and res["outputs"] == 120


def test_qcheck_stop_record_cannot_be_changed(tmp_path: Path) -> None:
    c1 = gen.CheckCount(3, 30, [10, 10, 10], 2, False)
    gen.record_stop(tmp_path / "s.json", c1)
    gen.record_stop(tmp_path / "s.json", c1)  # idempotent
    with pytest.raises(gen.QCheckViolation):
        gen.record_stop(tmp_path / "s.json", gen.CheckCount(4, 40, [10, 10, 10, 10], 3, False))


def test_qcheck_pause_and_resume_gives_the_same_blocks(tmp_path: Path) -> None:
    items = make_items(400)
    blocks = [items[i : i + 40] for i in range(0, 400, 40)]
    f = FilterSetting(-0.3, 0.5, 2.0)
    whole = gen.count_phase(AcceptEvery(4), blocks, f, tmp_path / "a", target=25, size=8)
    t = AcceptEvery(4)
    stop_after = {"n": 0}

    def deadline() -> bool:
        stop_after["n"] += 1
        return stop_after["n"] > 7

    with pytest.raises(bt.StageCapExceeded):
        gen.count_phase(t, blocks, f, tmp_path / "b", target=25, size=8, deadline=deadline)
    calls_before = t.calls
    resumed = gen.count_phase(t, blocks, f, tmp_path / "b", target=25, size=8)
    assert resumed.to_json() == whole.to_json()
    assert t.calls - calls_before == 15 - 7  # 3 blocks x 5 batches, the first 7 batches were kept and not regenerated


# --- batch layout, digest, regeneration --------------------------------------------------------------------------------------------------------
def test_layout_is_whole_batches_in_order() -> None:
    lay = bt.layout(2000, 32)
    assert len(lay) == 63 and lay[0] == range(0, 32) and lay[61] == range(1952, 1984) and lay[62] == range(1984, 2000)
    assert len(bt.layout(20000, 32)) == 625 and bt.layout(0, 32) == []


def test_digest_indices_same_for_both_teachers_and_seeded() -> None:
    a = bt.draw_batch_indices(63, 4, 934002, TEST_ALLOWED, "digest")
    b = bt.draw_batch_indices(63, 4, 934002, TEST_ALLOWED, "digest")
    assert a == b and len(set(a)) == 4 and a == sorted(a)
    g = torch.Generator().manual_seed(934002)
    assert a == sorted(torch.randperm(63, generator=g).tolist()[:4])  # brute force
    assert bt.draw_batch_indices(63, 4, 934003, TEST_ALLOWED, "digest") != a
    with pytest.raises(core.SeedRefused):
        bt.draw_batch_indices(63, 4, 250908, TEST_ALLOWED, "digest")  # a registered seed is refused in test mode


def test_regeneration_zero_tolerance_on_tokens_and_scores_printed_not_acted(tmp_path: Path) -> None:
    items = make_items(64)
    keys, srcs = [i.key for i in items], [i.en for i in items]
    src_of = dict(zip(keys, srcs, strict=True))
    t = lex_teachers()["A"]
    stored = {b.index: b for b in bt.run_stream(t, tmp_path, keys, srcs, size=32)}
    ok = bt.regeneration_check(t, stored, [0, 1], src_of, score_tolerance=1e-4, threads=6)
    assert ok.ok and ok.label is None and ok.sources == 64
    # a teacher whose beam scores drift by 1e-3 but whose tokens are identical: printed, not acted on
    class Drift(LexTeacher):
        def generate_batch(self, sources):  # type: ignore[no-untyped-def]
            from studies.p10is2.partq.teacher import Generated

            return [Generated(g.tokens, g.text, g.score + 1e-3) for g in super().generate_batch(sources)]

    d = Drift("A", t.mapping)
    rep = bt.regeneration_check(d, stored, [0], src_of, score_tolerance=1e-4)
    assert rep.ok and len(rep.scores_beyond_tolerance) == 32 and rep.max_score_difference == pytest.approx(1e-3, abs=1e-9)
    # a layout-dependent teacher: one token differs in a batch of more than one source -> engineering failure
    bad = LexTeacher("A", t.mapping, batch_dependent=True)
    stored_bad = {b.index: b for b in bt.run_stream(t, tmp_path / "x", keys, srcs, size=32)}
    rep2 = bt.regeneration_check(bad, stored_bad, [0, 1], src_of, score_tolerance=1e-4)
    assert not rep2.ok and rep2.label == "QUALIFICATION-ENGINEERING-FAILURE" and len(rep2.token_mismatches) == 2
    m = rep2.token_mismatches[0]
    assert set(m) == {"batch", "item", "key", "stored", "regenerated"} and m["item"] == 0


def test_resume_digest_check_catches_a_changed_teacher(tmp_path: Path) -> None:
    items = make_items(64)
    keys, srcs = [i.key for i in items], [i.en for i in items]
    src_of = dict(zip(keys, srcs, strict=True))
    t = FakeTeacher("A")
    stored = {b.index: b for b in bt.run_stream(t, tmp_path, keys, srcs, size=32)}
    rec = {"indices": [0, 1], "sha256": bt.digest_of([stored[0], stored[1]])}
    assert bt.resume_digest_check(t, stored, [0, 1], src_of, rec) == rec["sha256"]
    with pytest.raises(bt.DigestMismatch):
        bt.resume_digest_check(FakeTeacher("A", batch_dependent=True), stored, [0, 1], src_of, rec)
    with pytest.raises(bt.DigestMismatch):
        bt.resume_digest_check(t, stored, [1, 0], src_of, rec)


def test_stored_batch_with_other_keys_is_a_mismatch(tmp_path: Path) -> None:
    items = make_items(32)
    keys, srcs = [i.key for i in items], [i.en for i in items]
    bt.run_stream(FakeTeacher("A"), tmp_path, keys, srcs, size=32)
    with pytest.raises(bt.DigestMismatch):
        bt.run_stream(FakeTeacher("A"), tmp_path, list(reversed(keys)), list(reversed(srcs)), size=32)


# --- the split (G17) and the draws (rule 6) ---------------------------------------------------------------------------------------------------
def test_split_follows_g17_brute_force() -> None:
    units = [f"u{i:03d}" for i in range(300)]
    mine = split.assign_shared(list(reversed(units)), 934004, TEST_ALLOWED, 0.8)  # unsorted input: the rule sorts
    g = torch.Generator().manual_seed(934004)
    want = {}
    for u in sorted(units):
        want[u] = "B" if float(torch.rand(1, generator=g).item()) < 0.8 else "A"
    assert mine == want
    share_b = sum(1 for v in mine.values() if v == "B") / len(units)
    assert 0.7 < share_b < 0.9


def test_split_sources_keeps_pool_order_and_units_together() -> None:
    a = [Item(k, k, {}, -1) for k in ("go now", "can not go", "cannot go", "only a")]
    b = [Item(k, k, {}, -1) for k in ("go now", "cannot go", "can not go", "only b")]
    unit = lambda x: "x:" + x.key.replace("can not", "cannot")  # noqa: E731
    r = split.split_sources(a, b, unit, 934004, TEST_ALLOWED, 0.8)
    assert {x.key for x in r["A"]} | {x.key for x in r["B"]} >= {"only a", "only b"}
    owner_cannot = r["owner"]["x:cannot go"]
    for cap in ("A", "B"):
        keys = {x.key for x in r[cap]}
        assert ({"can not go", "cannot go"} <= keys) == (owner_cannot == cap)  # both spellings of a unit go to one capability only
    assert ("go now" in {x.key for x in r["A"]}) != ("go now" in {x.key for x in r["B"]})
    assert [x.key for x in r["A"]] == [k for k in (x.key for x in a) if k in {y.key for y in r["A"]}]  # pool order kept


@pytest.mark.parametrize(
    ("a", "b", "want"),
    [(24000, 24000, "DISJOINT DRAWS"), (23999, 24000, "OVERLAPPING DRAWS"), (24000, 10000, "OVERLAPPING DRAWS"), (10000, 10000, "OVERLAPPING DRAWS"), (9999, 30000, "DATA-EXHAUSTED"), (30000, 9999, "DATA-EXHAUSTED")],
)
def test_draws_label_thresholds(a: int, b: int, want: str) -> None:
    assert split.draws_label({"A": a, "B": b}, CFG_Q) == want


def test_disjoint_draws_are_disjoint_consecutive_positions() -> None:
    pos = split.disjoint_positions(50, 934016, TEST_ALLOWED, 3, 10)
    g = torch.Generator().manual_seed(934016)
    perm = torch.randperm(50, generator=g).tolist()
    assert pos == [perm[0:10], perm[10:20], perm[20:30]]
    assert len({i for p in pos for i in p}) == 30
    with pytest.raises(ValueError):
        split.disjoint_positions(29, 934016, TEST_ALLOWED, 3, 10)


def test_overlapping_draws_one_generator_per_replicate_a_then_b_and_share_printed() -> None:
    d = split.overlapping_positions({"A": 40, "B": 25}, [934021, 934022, 934023], TEST_ALLOWED, 20)
    g = torch.Generator().manual_seed(934021)
    assert d["A"][0] == torch.randperm(40, generator=g).tolist()[:20] and d["B"][0] == torch.randperm(25, generator=g).tolist()[:20]
    sh = split.shared_share(d["A"])
    pairs = [(0, 1), (0, 2), (1, 2)]
    assert sh == pytest.approx(sum(len(set(d["A"][i]) & set(d["A"][j])) / 20 for i, j in pairs) / 3)
    assert 0.0 < sh < 1.0


def test_make_draws_registered_rule_label_and_zero_share_when_disjoint() -> None:
    cfg = small_cfg()
    cfg["generation"].update(accepted_min=30, accepted_disjoint=60, per_replicate=20)
    seeds = core.partq_seeds(cfg, "test")
    d = split.make_draws({"A": 60, "B": 70}, cfg, seeds, [], TEST_ALLOWED)
    assert d.label == "DISJOINT DRAWS" and all(v == 0.0 for v in d.shared_share.values())
    d2 = split.make_draws({"A": 59, "B": 70}, cfg, seeds, [934031, 934032, 934033], TEST_ALLOWED)
    assert d2.label == "OVERLAPPING DRAWS"
    with pytest.raises(ValueError):
        split.make_draws({"A": 29, "B": 70}, cfg, seeds, [], TEST_ALLOWED)


# --- the panel ledger (G18, C13) --------------------------------------------------------------------------------------------------------------
def test_spans_end_exclusive_and_overlap_needs_one_shared_byte() -> None:
    a, b, c = Span(0, 5, 0, 0), Span(5, 9, 0, 1), Span(4, 6, 0, 1)
    assert not overlap(a, b) and overlap(a, c) and overlap(b, c) and overlap(a, a)
    with pytest.raises(SpanError):
        Span(3, 3, 0, 0)


def test_row_map_is_cumulative_utf8_bytes_with_nothing_between() -> None:
    rows = ["ab", "é", "", "xyz"]  # 2, 2 (two bytes), 0, 3
    m = RowMap.from_rows(rows)
    assert m.starts == (0, 2, 4, 4) and m.total == 7 and m.row_bytes == (2, 2, 0, 3)
    assert m.offset(1, 2) == 4 and m.offset(3, 3) == 7
    assert [m.row_of(o) for o in range(7)] == [0, 0, 1, 1, 3, 3, 3]
    sp = m.span(0, 1, 3, 2)  # from the second byte of row 0 to the byte before byte 2 of row 3
    assert (sp.start, sp.end) == (1, 6) and (sp.first_row, sp.last_row) == (0, 3)
    assert per_row_spans(sp, m) == [(0, 1, 2), (1, 0, 2), (3, 0, 2)]  # the empty row 2 holds no byte and is omitted; ends exclusive
    with pytest.raises(SpanError):
        m.offset(0, 3)


def test_char_offsets_to_bytes() -> None:
    assert char_to_byte_offsets("aé€") == [0, 1, 3, 6]


def test_ledger_sampling_excludes_foreign_spans_and_checks_counts() -> None:
    foreign = [Span(100, 200, 1, 2, "panel", "P10IS3")]
    led = PanelLedger(foreign)
    cands = [Span(i * 100, i * 100 + 100, i, i, "ordinary") for i in range(10)]  # [100, 200) is cand 1
    assert [c.start for c in led.eligible_ordinary(cands)] == [i * 100 for i in range(10) if i != 1]
    g = torch.Generator().manual_seed(934007)
    pick = led.sample_ordinary(cands, 4, g)
    assert len(pick) == 4 and all(not led.overlapping(p) for p in pick) and pick == sorted(pick, key=lambda s: s.start)
    with pytest.raises(SpanError):
        led.sample_ordinary(cands, 10, torch.Generator().manual_seed(934007))
    for p in pick:
        led.add(Span(p.start, p.end, p.first_row, p.last_row, "ordinary", "P10IS2"))
    led.add(Span(2000, 2100, 20, 20, "marker", "P10IS2"))
    assert led.check_own_panel("P10IS2", 1, 4)["ok"]
    led.add(Span(2050, 2060, 20, 20, "ordinary", "P10IS2"))
    assert not led.check_own_panel("P10IS2", 1, 5)["ok"]  # an own span overlapping another own span
    assert PanelLedger.from_record(led.to_record()).to_record() == led.to_record()


# --- the labels (section 4.4) ------------------------------------------------------------------------------------------------------------------
def tq(q1=True, q2=True, q3=True, q4="pass", exhausted=False):  # type: ignore[no-untyped-def]
    q4v = None if q4 is None else {"read_ok": q4 != "short", "pass": q4 == "pass"}
    return {"q1": q1, "q2": q2, "q3": q3, "q4": q4v, "reserve_exhausted": exhausted}


def facts(a=None, b=None, pools=(30000, 26000), draws="DISJOINT DRAWS", **kw):  # type: ignore[no-untyped-def]
    f = {"engineering_failure": [], "data_insufficient": [], "teachers": {"A": a or tq(), "B": b or tq()}, "pools": None if pools is None else {"A": pools[0], "B": pools[1]}, "draws": draws, "item_errors": [], "paused": []}
    f.update(kw)
    return f


def test_label_row_5_qualified_with_both_draw_variants_and_part_t_not_started_otherwise() -> None:
    r = labels.part_q_label(facts())
    assert r["label"] == "TEACHERS-QUALIFIED (DISJOINT DRAWS)" and r["part_t"] != labels.PART_T_NOT_STARTED
    assert labels.part_q_label(facts(draws="OVERLAPPING DRAWS", pools=(12000, 13000)))["label"] == "TEACHERS-QUALIFIED (OVERLAPPING DRAWS)"
    for bad in (facts(a=tq(q1=False)), facts(data_insufficient=["E_A short"]), facts(engineering_failure=["digest"]), facts(draws="DATA-EXHAUSTED", pools=(9000, 30000))):
        assert labels.part_q_label(bad)["part_t"] == labels.PART_T_NOT_STARTED


def test_label_row_order_first_match_wins() -> None:
    assert labels.part_q_label(facts(engineering_failure=["x"], data_insufficient=["y"], a=tq(q1=False)))["label"] == labels.ENGINEERING_FAILURE
    assert labels.part_q_label(facts(data_insufficient=["y"], a=tq(q1=False)))["label"] == labels.DATA_INSUFFICIENT
    r = labels.part_q_label(facts(a=tq(q1=False), b=tq(q4="short", exhausted=True)))
    assert r["label"].startswith(labels.NEGATIVE_QUALITY) and "teacher A" in r["label"] and "Q1" in r["label"]  # row 3 beats row 4
    assert labels.part_q_label(facts(b=tq(q4="short", exhausted=True)))["label"] == labels.DATA_EXHAUSTED
    assert labels.part_q_label(facts(draws="DATA-EXHAUSTED", pools=(9000, 30000)))["label"] == labels.DATA_EXHAUSTED


def test_label_names_teacher_and_first_failed_criterion_for_every_criterion() -> None:
    for crit, kw in (("Q1", {"q1": False}), ("Q2", {"q2": False}), ("Q3", {"q3": False, "q4": None}), ("Q4", {"q4": "fail"})):
        for who in ("A", "B"):
            r = labels.part_q_label(facts(**{who.lower(): tq(**kw)}))
            assert r["label"].startswith(labels.NEGATIVE_QUALITY) and f"teacher {who}" in r["label"] and crit in r["label"]
    r = labels.part_q_label(facts(a=tq(q2=False, q4="fail"), b=tq(q1=False)))
    assert "teacher A" in r["label"] and "Q2" in r["label"]  # teacher-major, then Q1..Q4 (reading, listed)


def test_q4_below_150_is_exhaustion_not_a_precision_failure() -> None:
    r = labels.part_q_label(facts(a=tq(q4="short")))
    assert r["label"] == labels.DATA_EXHAUSTED


def test_g15_failed_q1_or_q2_teacher_still_prints_complete_table() -> None:
    r = labels.part_q_label(facts(a=tq(q1=False, q2=False, q3=True, q4="pass")))
    assert r["per_teacher"]["A"]["failed"] == ["Q1", "Q2"] and r["per_teacher"]["A"]["q4"] == {"read_ok": True, "pass": True}
    text = labels.render(r)
    assert text.startswith(core.ORACLE_LINE) and "Part T: NOT STARTED" in text and "FAIL" in text


def test_states_are_not_outcomes() -> None:
    assert labels.part_q_label(facts(item_errors=["x"]))["label"] == labels.ENGINEERING_STOP_ITEMS
    assert labels.part_q_label(facts(item_errors=["x"]))["derived"] is False
    assert labels.part_q_label(facts(paused=["generation"]))["label"] == labels.PAUSED
    assert labels.part_q_label(facts(nonfinite=True))["label"] == labels.ENGINEERING_STOP_NONFINITE
    assert labels.part_q_label(facts(pools=None, draws=None))["label"] == labels.PAUSED  # both pass, generation not ended
    assert labels.resource_cap_decision_label("generation", {"A": 12000, "B": 9000}) == "STOPPED AT A RESOURCE CAP BY DECISION (generation; A 12000, B 9000)"


# --- seeds -------------------------------------------------------------------------------------------------------------------------------------
def test_partq_seed_table() -> None:
    s = core.partq_seeds(CFG_Q, "registered")
    assert [s[k] for k in ("partition", "q_fit", "q_check_reserve_order", "source_split", "source_block_order", "control_subsample", "gen_ordinary_windows", "teacher_tokenizer_sentences_and_digest", "tokenization_test_c", "equivalence_injection", "c1_pairing", "seen_items", "timing_items", "regeneration_subsample")] == list(range(250901, 250915))
    assert (s["bootstrap"], s["disjoint_permutation_a"], s["disjoint_permutation_b"], s["route_accuracy_pieces"]) == (250915, 250916, 250917, 250918)
    r = core.partq_seeds(CFG_Q, "rehearsal")
    assert list(r.values()) == list(range(252901, 252915))
    assert "disjoint_permutation_a" not in r


def test_partt_seed_values_listed_never_the_formula_at_i_2() -> None:
    reg = [core.partt_replicate_values(CFG_T, "registered", r) for r in range(3)]
    assert [v["base"] for v in reg] == [250001, 250101, 250201]
    assert reg[0]["data"] == {"training_draw": 250002, "batch_order": 250003, "permutation_controls": 250005, "code_hash": 250011, "router": 250014}
    assert [v["init_base"] for v in reg] == [330201, 330211, 330221] and reg[1]["init"]["D1"] == 330214 and reg[2]["init"]["router projection and keys"] == 330228
    cal = [core.partt_replicate_values(CFG_T, "calibration", i) for i in range(4)]
    assert [v["base"] for v in cal] == [251001, 251101, 251201, 251301]
    assert [v["init_base"] for v in cal] == [330231, 330241, 330261, 330271]  # draws 2 and 3: the listed values
    assert cal[2]["init_base"] != 330231 + 10 * 2  # the formula at i = 2 would be the rehearsal's 330251
    assert core.partt_replicate_values(CFG_T, "rehearsal", 0)["init_base"] == 330251
    with pytest.raises(core.SeedRefused):
        core.partt_replicate_values(CFG_T, "calibration", 4)
    with pytest.raises(core.SeedRefused):
        core.partt_replicate_values(CFG_T, "rehearsal", 1)


def test_seeded_generator_refuses_unlisted_and_records() -> None:
    allowed = core.partt_listed_seeds(CFG_T, "calibration")
    with pytest.raises(core.SeedRefused):
        core.seeded_generator(330251, "the formula's value", allowed)
    g = core.seeded_generator(251002, "unit", allowed)
    assert (251002, "unit") in core.recorded_seeds() and isinstance(g, torch.Generator)
    assert not (core.partt_listed_seeds(CFG_T, "registered") & core.partt_listed_seeds(CFG_T, "calibration"))
    assert not (core.partt_listed_seeds(CFG_T, "registered") & core.partt_listed_seeds(CFG_T, "rehearsal"))


# --- records and the ledger ---------------------------------------------------------------------------------------------------------------------
def test_record_requires_oracle_line_and_refuses_nan(tmp_path: Path) -> None:
    rec = {**core.envelope("qualification", "Q"), "x": float("nan")}
    core.write_record(tmp_path / "r.json", rec)
    assert core.read_record(tmp_path / "r.json")["x"] is None
    with pytest.raises(ValueError):
        core.check_envelope({**rec, "oracle_line": "other"})
    with pytest.raises(ValueError):
        core.require_oracle_line("a line without it")
    with pytest.raises(FileExistsError):
        core.write_record(tmp_path / "r.json", rec)


def test_ledger_sums_every_process_and_caps_by_rule(tmp_path: Path) -> None:
    led = core.Ledger(tmp_path / "ledger.json", "Q", 1000.0)
    led.charge_process("generation", "r1", "w1", 300.0)
    led.charge_process("generation", "r1", "w2", 250.0)  # two workers in parallel: both charged (ruling L2)
    assert led.charged() == 550.0 and led.charged("generation") == 550.0 and led.remaining() == 450.0
    led.charge_process("generation", "r2", "w1", 600.0)
    with pytest.raises(core.LedgerRefused):
        led.require_room("generation", 100.0)
    assert core.stage_cap_seconds(1500.0) == 3000.0
    assert core.total_cap_seconds(700.0, {"qfit": 100.0, "gen": 1000.0}) == 700.0 + 2 * 1100.0
    with pytest.raises(ValueError):
        core.Ledger(tmp_path / "l2.json", "Q", 0.0)
