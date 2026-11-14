# ruff: noqa: E501
"""P9 package I4: general-N page simulator, nulls, cache rule, planted traces (studies/p9/sim.py).

Self-check only: not independent review, not Astra validation, not human approval. No local data: the
equivalence with the frozen P7-B code is tested on synthetic 4,096-slot traces here; the check on
P8's recorded traces is the script ``python -m studies.p9.sim equivalence``."""

import json
import random
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm import p7a_core as a_core  # noqa: E402
from arborlm import p7b_sim as frozen_sim  # noqa: E402
from studies.p9 import core, sim  # noqa: E402
from studies.p9 import layout as lay  # noqa: E402
from studies.p9.core import Trace  # noqa: E402


def make_trace(
    selected: torch.Tensor,
    slots: int,
    *,
    stream: str = "panel_a",
    kind: str = "answer",
    cluster: torch.Tensor | None = None,
) -> Trace:
    q = int(selected.shape[0])
    zeros = torch.zeros(q, dtype=torch.int64)
    return Trace(
        "t",
        0,
        stream,
        kind,
        slots,
        selected.to(torch.int64),
        None,
        zeros,
        zeros,
        zeros,
        zeros - 1 if cluster is None else cluster,
    )


def random_selected(slots: int, queries: int, seed: int, hot: int | None = None) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    if hot is None:
        return torch.rand(queries, slots, generator=g).argsort(dim=1)[:, :8]
    pool = torch.randperm(slots, generator=g)[:hot]
    return pool[torch.rand(queries, hot, generator=g).argsort(dim=1)[:, :8]]


# --- brute-force LRU reference (independent of the simulator's data structures) --------------------------------------
def brute_force(pages: list[list[int]], capacity: int, tie: str, warm: int) -> dict[str, int]:
    """Cache as a dict page -> last-use time. A query touches its distinct pages in ascending (or
    descending) order; afterwards the page with the oldest last-use time that the query did not use is
    evicted while the cache is above ``capacity``."""
    last: dict[int, int] = {}
    clock = 0
    seen: set[int] = set()
    misses = first = at_warm_m = at_warm_f = 0
    for i, query in enumerate(pages):
        if i == warm:
            at_warm_m, at_warm_f = misses, first
        distinct = sorted(set(query), reverse=(tie == "desc"))
        for page in distinct:
            clock += 1
            if page not in last:
                misses += 1
                if page not in seen:
                    seen.add(page)
                    first += 1
            last[page] = clock
        while len(last) > capacity:
            victims = [p for p in last if p not in distinct]
            if not victims:
                break
            del last[min(victims, key=lambda p: last[p])]
    if warm >= len(pages):
        at_warm_m, at_warm_f = misses, first
    return {
        "misses_all": misses,
        "first_touch_all": first,
        "misses_warm": misses - at_warm_m,
        "first_touch_warm": first - at_warm_f,
    }


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("tie", ["asc", "desc"])
@pytest.mark.parametrize("capacity", [1, 3, 8, 20])
def test_lru_matches_brute_force(seed: int, tie: str, capacity: int) -> None:
    rng = random.Random(seed)
    universe = rng.choice([12, 40, 100])
    pages = [
        [rng.randrange(universe) for _ in range(8)] for _ in range(rng.choice([1, 2, 150, 301]))
    ]
    pages += pages[-3:]  # repeated queries exercise the "same pages as the previous query" shortcut
    warm = len(pages) // 2
    sets = sim.page_sets(torch.tensor(pages))
    got = sim.lru_counts(sets, capacity, tie, warm=warm)
    want = brute_force(pages, capacity, tie, warm)
    assert {k: got[k] for k in want} == want
    # the shortcut for streams that fit in the cache equals the full pass
    full = sim._lru_pass([s[::-1] for s in sets] if tie == "desc" else sets, capacity, warm)
    assert {k: full[k] for k in want} == want


def test_tie_rules_differ_and_are_both_run() -> None:
    rng = random.Random(1)
    pages = [[rng.randrange(40) for _ in range(8)] for _ in range(400)]
    sets = sim.page_sets(torch.tensor(pages))
    asc = sim.lru_counts(sets, 10, "asc")["misses_warm"]
    desc = sim.lru_counts(sets, 10, "desc")["misses_warm"]
    assert asc != desc
    with pytest.raises(ValueError):
        sim.lru_counts(sets, 10, "up")


def test_lru_misses_counts_after_warm_up_and_cache_may_hold_one_query() -> None:
    pages = torch.tensor(
        [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15], [0, 1, 2, 3, 4, 5, 6, 7]]
    )
    # C = 1 < 8 pages per query: the cache holds the current query's pages, evicts the rest next query
    assert sim.lru_misses(pages, 1, "asc", warm_queries=0) == 24
    assert sim.lru_misses(pages, 1, "asc", warm_queries=1) == 16
    assert (
        sim.lru_misses(pages, 16, "asc", warm_queries=1) == 8
    )  # only the second query's pages are new


# --- equivalence with the frozen P7-B simulator on synthetic 4,096-slot traces -----------------------------------------
@pytest.mark.parametrize("rows", [2, 8, 32])
def test_equivalent_to_p7b_on_synthetic_4096_traces(rows: int) -> None:
    queries = 64 * 16
    selected = torch.cat(
        [
            random_selected(4096, queries // 2, 1, hot=300),
            random_selected(4096, queries // 2, 2, hot=900),
        ]
    )
    positions = torch.randperm(4096, generator=torch.Generator().manual_seed(5))
    order = torch.empty(4096, dtype=torch.int64)
    order[positions] = torch.arange(4096)
    layout = lay.Layout("random_partition", rows, order)
    trace = make_trace(selected, 4096)
    mine_sets = sim.page_sets(sim.page_sequence(trace, layout, rows))
    frozen_sets = frozen_sim.page_sets(frozen_sim.positions_tensor(order.tolist()), rows, selected)
    assert mine_sets == frozen_sets
    assert sim.stream_stats(mine_sets, queries // 2) == frozen_sim.stream_stats(frozen_sets)
    reverse = frozen_sim.reversed_order(frozen_sets)
    for capacity in (8, 16, 32, 64):
        for tie, order_ in (("asc", frozen_sets), ("desc", reverse)):
            ref = frozen_sim.lru_pass(frozen_sets, capacity, touch_order=order_)
            got = sim.lru_counts(mine_sets, capacity, tie, context=64)
            assert {k: got[k] for k in sim.COUNT_KEYS} == {k: ref[k] for k in sim.COUNT_KEYS}
            assert frozen_sim.quantiles(got["context_capacity"]) == ref["ctx_q"]
            assert (
                sim.lru_misses(
                    sim.page_sequence(trace, layout, rows), capacity, tie, warm_queries=queries // 2
                )
                == ref["misses_warm"]
            )
            plain = sim.lru_counts(
                mine_sets, capacity, tie
            )  # without per-context counts (skips the full pass when all pages fit)
            assert {k: plain[k] for k in sim.COUNT_KEYS} == {k: ref[k] for k in sim.COUNT_KEYS}


def test_shortcut_taken_when_everything_fits() -> None:
    selected = random_selected(4096, 1024, 3, hot=40)
    layout = lay.identity_layout(4096)
    sets = sim.page_sets(sim.page_sequence(make_trace(selected, 4096), layout, 8))
    stats = sim.stream_stats(sets, 512)
    assert stats["distinct_stream"] <= 64  # fits: no eviction can happen
    fast = sim.lru_counts(sets, 64, "asc", stats=stats)
    slow = sim.lru_counts(sets, 64, "asc", context=64)
    assert {k: fast[k] for k in sim.COUNT_KEYS} == {k: slow[k] for k in sim.COUNT_KEYS}
    assert fast["misses_warm"] == fast["first_touch_warm"]  # no capacity misses


# --- the cache rule ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "working,rows,rho,expected",
    [
        (1000, 8, 1 / 16, 8),  # 7.8125
        (1000, 32, 1 / 16, 2),  # 1.95
        (1000, 8, 1 / 4, 31),  # 31.25
        (1000, 32, 1 / 4, 8),  # 7.8125
        (4096, 8, 1.0, 512),
        (4096, 2, 1.0, 2048),
        (10, 32, 1 / 16, 1),  # 0.02 -> max(1, 0)
        (0, 8, 1 / 4, 1),
        (64, 32, 1 / 4, 1),  # 0.5 -> round half to even -> 0 -> max(1, 0)
        (96, 32, 1 / 4, 1),  # 0.75 -> 1
        (160, 32, 1 / 4, 1),  # 1.25 -> 1
        (224, 32, 1 / 4, 2),  # 1.75 -> 2
    ],
)
def test_cache_rule_values(working: int, rows: int, rho: float, expected: int) -> None:
    assert sim.cache_pages(working, rows, rho) == expected


def test_cache_rule_rejects_nonsense_and_working_set_is_per_trace_type() -> None:
    with pytest.raises(ValueError):
        sim.cache_pages(10, 0, 0.25)
    answer = make_trace(torch.arange(32).view(4, 8), 64, stream="calibration", kind="answer")
    allpos = make_trace(torch.arange(64).view(8, 8), 64, stream="calibration", kind="all")
    assert sim.working_set(answer) == 32 and sim.working_set(allpos) == 64
    assert sim.cache_pages(sim.working_set(answer), 8, 1.0) != sim.cache_pages(
        sim.working_set(allpos), 8, 1.0
    )


# --- nulls -------------------------------------------------------------------------------------------------------------
def counts_of(selected: torch.Tensor, slots: int) -> list[int]:
    return torch.bincount(selected.flatten(), minlength=slots).tolist()


@pytest.mark.parametrize("slots", [512, 4096, 65536])
def test_null_preserves_counts_and_distinctness(slots: int) -> None:
    selected = random_selected(slots, 600, 4, hot=min(slots, 700))
    trace = make_trace(selected, slots)
    nulls = sim.make_nulls(trace, (171331, 171332, 171333), index=3)
    assert nulls.method == sim.REGISTERED_NULL_METHOD and not nulls.single_set
    assert len(nulls.traces) == 3 and len(set(nulls.stream_sha256)) == 3
    for t in nulls.traces:
        assert counts_of(t.selected, slots) == counts_of(selected, slots)
        assert all(len(set(row)) == 8 for row in t.selected.tolist())
        assert not torch.equal(t.selected, selected)
    assert torch.equal(
        sim.count_preserving_null(trace, 171331, index=3).selected, nulls.traces[0].selected
    )


def test_null_equals_the_frozen_generator_where_that_one_runs() -> None:
    selected = random_selected(4096, 512, 6, hot=500)
    counts = counts_of(selected, 4096)
    for seed, index in ((91331, 0), (171341, 57)):
        frozen_stream, _ = a_core.frequency_matched_detail(counts, seed, index, queries=512)
        mine = sim.make_nulls(make_trace(selected, 4096), (seed,), index=index)
        assert torch.equal(mine.traces[0].selected, frozen_stream)


def test_frozen_generator_cannot_run_above_32767_slots_but_ours_does() -> None:
    selected = random_selected(65536, 300, 2, hot=2000)
    counts = counts_of(selected, 65536)
    assert max(i for i, c in enumerate(counts) if c) > 32767
    with pytest.raises(Exception, match="format requires"):
        a_core.frequency_matched_detail(counts, 1, 0, queries=300)
    stream = sim.registered_generator(counts, 1, 0, queries=300)
    assert counts_of(stream, 65536) == counts


def test_identity_null_only_under_the_single_set_precondition() -> None:
    slots, q = 65536, 256
    s = torch.tensor([5, 40000, 7, 65535, 100, 20000, 3, 9], dtype=torch.int64)
    one = s.repeat(q, 1)
    nulls = sim.make_nulls(make_trace(one, slots), core.NULL_SEEDS_A, index=1)
    assert nulls.single_set and nulls.method == sim.IDENTITY_NULL_METHOD
    assert (
        len(set(nulls.stream_sha256)) == 1 and len(nulls.stream_sha256) == 3
    )  # three identical hashes
    for t in nulls.traces:
        assert all(row == sorted(s.tolist()) for row in t.selected.tolist())
        assert counts_of(t.selected, slots) == counts_of(one, slots)
    # near-single-set inputs: one query differs, nine slots, unequal counts, 17 slots -> registered path
    near = one.clone()
    near[0, 0] = 11
    nine = one.clone()
    nine[::2, 0] = 11
    spread = random_selected(slots, q, 8, hot=17)
    # the registered generator may succeed or fail on these (ADR-0016: it failed on collapsed panels);
    # either way the identity null is never used and a failure is reported, not repaired
    outcomes = []
    for variant in (near, nine, spread):
        try:
            result = sim.make_nulls(make_trace(variant, slots), core.NULL_SEEDS_A, index=1)
        except sim.NullGenerationError as error:
            assert "registered generator failed" in str(error)
            outcomes.append("failed")
            continue
        assert not result.single_set and result.method == sim.REGISTERED_NULL_METHOD
        for t in result.traces:
            assert counts_of(t.selected, slots) == counts_of(variant, slots)
        assert len(set(result.stream_sha256)) == 3
        outcomes.append("ok")
    assert outcomes[2] == "ok"  # 17 spread slots: the registered generator succeeds


def test_generator_failure_is_a_failure_not_repaired() -> None:
    slots, q = 512, 64
    # a histogram no arrangement can realize: counts sum to 8Q but one slot count exceeds Q
    bad = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]] * q)
    bad[:, 7] = 1  # duplicate slot inside each query: slot 1 counted twice per query (> Q)
    with pytest.raises(sim.NullGenerationError):
        sim.make_nulls(make_trace(bad, slots), (1, 2, 3), index=0)


# --- degenerate test, E, descriptive statistics -------------------------------------------------------------------------
def test_degenerate_and_e_ratio() -> None:
    assert sim.is_degenerate(0.0499, False) and not sim.is_degenerate(0.05, False)
    assert sim.is_degenerate(7.0, True)  # single-set stream, whatever the rate
    assert sim.e_ratio(30, [40, 50, 60]) == pytest.approx(0.6) and sim.e_ratio(5, [0, 0, 0]) is None
    assert sim.raw_miss_ratio(3, 4) == 0.75 and sim.raw_miss_ratio(3, 0) is None
    assert not sim.is_descriptive(1 / 16, 8) and not sim.is_descriptive(0.25, 32)
    assert (
        sim.is_descriptive(1.0, 8) and sim.is_descriptive(0.25, 2) and sim.is_descriptive(1 / 16, 2)
    )


def test_degenerate_uses_the_frequency_layout_null_denominator() -> None:
    planted = planted_pair("popularity_only", 512, 179005)
    assert planted.calibration is not None
    flags = {
        name: setting(planted, layout, 8, 1 / 16)
        for name, layout in (
            ("identity", lay.identity_layout(512)),
            ("frequency", lay.frequency_layout(planted.calibration)),
        )
    }
    assert flags["identity"]["null_miss_rate"] == flags["frequency"]["null_miss_rate"]
    assert flags["identity"]["degenerate"] == flags["frequency"]["degenerate"]
    assert (
        flags["identity"]["null_miss_rate_same_layout"] != flags["identity"]["null_miss_rate"]
    )  # the descriptive rate is not the one tested against the floor


def test_pages_per_query_and_cross_query_reuse() -> None:
    pages = torch.tensor(
        [
            [0, 0, 0, 0, 1, 1, 1, 1],  # 2 distinct
            [1, 2, 3, 4, 5, 6, 7, 8],  # 8 distinct; page 1 seen before
            [9, 9, 9, 9, 9, 9, 9, 9],  # 1 distinct, new
            [
                0,
                1,
                2,
                9,
                9,
                9,
                9,
                9,
            ],  # 4 distinct; 0 and 9 seen at lag 3 and 1, 1 and 2 at lag 2 and 3
        ]
    )
    assert sim.pages_per_query(pages) == pytest.approx((2 + 8 + 1 + 4) / 4)
    # window 1: q1 -> 1/8 (page 1), q2 -> 0, q3 -> 1/4 (page 9 from q2)
    assert sim.cross_query_reuse(pages, 1) == pytest.approx((1 / 8 + 0 + 1 / 4) / 3)
    # window 3: q1 -> 1/8; q2 -> 0; q3 -> pages {0,1,2,9}: 0,1 (q0), 1,2 (q1), 9 (q2) = 4/4 = 1
    assert sim.cross_query_reuse(pages, 3) == pytest.approx((1 / 8 + 0 + 1) / 3)
    groups = torch.tensor([0, 0, 1, 1])  # only same-group predecessors count; q0 and q2 have none
    assert sim.cross_query_reuse(pages, 3, groups=groups) == pytest.approx((1 / 8 + 1 / 4) / 2)
    assert sim.cross_query_reuse(pages[:1], 3) == 0.0


# --- simulate_setting and simulate_cell ---------------------------------------------------------------------------------
def planted_pair(kind: str, slots: int = 4096, seed: int = 179001) -> sim.PlantedTrace:
    return sim.planted_trace(kind, slots=slots, seed=seed)


def setting(
    planted: sim.PlantedTrace, layout: lay.Layout, rows: int, rho: float, tie: str = "asc"
) -> sim.SimRecordX:
    assert planted.trace is not None and planted.calibration is not None
    return sim.simulate_setting(
        planted.trace,
        planted.calibration,
        layout,
        rows=rows,
        rho=rho,
        tie=tie,
        null_seeds=core.NULL_SEEDS_A,
        label="x",
        update=0,
        stream="panel_a",
    )


def test_simulate_setting_fields() -> None:
    planted = planted_pair("popularity_only")
    assert planted.trace is not None and planted.calibration is not None
    record = setting(planted, lay.identity_layout(4096), 8, 1 / 4)
    working = sim.working_set(planted.calibration)
    assert record["working_set"] == working and record["cache_pages"] == sim.cache_pages(
        working, 8, 0.25
    )
    assert (
        record["layout"] == "identity"
        and record["rows_per_page"] == 8
        and record["cache_fraction"] == 0.25
    )
    assert (
        record["kind"] == "sim"
        and record["study"] == core.STUDY
        and record["trace_kind"] == "answer"
    )
    assert len(record["null_misses"]) == 3 and record["e_ratio"] == pytest.approx(
        record["actual_misses"] / (sum(record["null_misses"]) / 3)
    )
    assert record["null_miss_rate"] == pytest.approx(
        sum(record["null_misses"]) / 3 / record["counted_queries"]
    )
    assert (
        record["counted_queries"] == 1024 and not record["descriptive"] and not record["degenerate"]
    )
    assert record["actual_misses_with_first_touch"] >= record["actual_misses"]
    # primary E: the nulls are simulated under the FREQUENCY layout fitted on the calibration trace
    freq = setting(planted, lay.frequency_layout(planted.calibration), 8, 1 / 4)
    assert record["null_layout"] == "frequency" and record["null_misses"] == freq["null_misses"]
    assert record["null_miss_rate"] == freq["null_miss_rate"]
    assert freq["e_ratio"] == freq["e_same_layout"]  # for the frequency layout the two coincide
    assert freq["null_misses_same_layout"] == freq["null_misses"]
    assert record["e_same_layout"] == pytest.approx(
        record["actual_misses"] / (sum(record["null_misses_same_layout"]) / 3)
    )
    assert record["null_miss_rate_same_layout"] == pytest.approx(
        sum(record["null_misses_same_layout"]) / 3 / record["counted_queries"]
    )
    # identity packs hot slots apart, so its own nulls miss more than the frequency-layout nulls
    assert sum(record["null_misses_same_layout"]) > sum(record["null_misses"])
    assert record["e_ratio"] > record["e_same_layout"]
    assert set(record["identity"]) == {
        "source_sha256",
        "spec_sha256",
        "config_sha256",
        "frozen_source_sha256",
    }
    assert json.dumps(record)  # JSON-serializable
    assert setting(planted, lay.identity_layout(4096), 2, 1.0)["descriptive"]
    with pytest.raises(ValueError):
        sim.simulate_setting(
            planted.trace,
            make_trace(planted.calibration.selected, 4096, kind="all", stream="calibration"),
            lay.identity_layout(4096),
            rows=8,
            rho=0.25,
            tie="asc",
            null_seeds=core.NULL_SEEDS_A,
            label="x",
            update=0,
            stream="panel_a",
        )


def test_simulate_cell_writes_records_and_layout_files(tmp_path: Path) -> None:
    cell = next(
        c
        for c in core.cells()
        if c.arch == "flat" and c.slots == 4096 and c.block == "A1" and c.seed == 1701
    )
    planted = planted_pair("clusters_aligned_sharing")
    assert planted.trace is not None and planted.calibration is not None
    for name, trace in (("calibration", planted.calibration), ("panel_a", planted.trace)):
        core.write_trace(core.trace_path(tmp_path, cell.label, 5, name, "answer"), trace)
    records = sim.simulate_cell(cell, tmp_path, 5, "panel_a", trace_kinds=("answer",))
    # 3 R-independent layouts x 3 R x 3 rho x 2 ties + 2 R-specific layouts x 3 rho x 2 ties per R
    assert len(records) == 3 * 3 * 6 + 2 * 3 * 6
    file = core.read_record(core.sim_path(tmp_path, cell.label, 5, "panel_a"), "sim")
    assert file["status"] == "completed" and len(file["records"]) == len(records)
    primary = [r for r in records if not r["descriptive"]]  # type: ignore[typeddict-item]
    assert {(r["cache_fraction"], r["rows_per_page"]) for r in primary} == {
        (a, b) for a in core.CACHE_RHOS_PRIMARY for b in core.CACHE_ROWS_PRIMARY
    }
    assert {r["tie"] for r in records} == {"asc", "desc"}
    assert {r["layout"] for r in records} >= {
        "identity",
        "frequency",
        "oracle_cluster",
        "coaccess@8",
        "random_partition@32",
    }
    directory = core.cell_dir(tmp_path, cell.label) / "layouts" / core.snapshot_stem(5)
    back = lay.read_layouts(directory / "layouts.answer.int32.bin", file["layout_sha256"]["answer"])
    assert "coaccess@8" in back
    with pytest.raises(ValueError):
        sim.simulate_cell(cell, tmp_path, 5, "calibration")


def test_simulate_cell_writes_a_failed_record_when_the_generator_fails(tmp_path: Path) -> None:
    cell = next(
        c
        for c in core.cells()
        if c.arch == "flat" and c.slots == 4096 and c.block == "A1" and c.seed == 1701
    )
    planted = planted_pair("popularity_only")
    assert planted.trace is not None and planted.calibration is not None
    bad_selected = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]] * 1024)
    bad_selected[:, 7] = 1  # a slot counted twice per query: no count-preserving arrangement exists
    bad = make_trace(bad_selected, 4096)
    core.write_trace(
        core.trace_path(tmp_path, cell.label, 0, "calibration", "answer"), planted.calibration
    )
    core.write_trace(core.trace_path(tmp_path, cell.label, 0, "panel_a", "answer"), bad)
    with pytest.raises(sim.SimulationFailed):
        sim.simulate_cell(cell, tmp_path, 0, "panel_a", trace_kinds=("answer",))
    file = core.read_record(core.sim_path(tmp_path, cell.label, 0, "panel_a"), "sim")
    assert (
        file["status"] == "failed"
        and file["records"] == []
        and "registered generator failed" in file["failures"][0]["error"]
    )


# --- planted traces: the classes they must receive ----------------------------------------------------------------------
def test_planted_popularity_only_has_e_near_one() -> None:
    """Derivation. Queries are i.i.d. draws from one popularity with no fact or cluster structure, so under
    ANY layout the actual stream is exchangeable with its count-preserving nulls: ``e_same_layout`` is 1
    up to sampling noise (1,024 counted queries; tolerance 0.05). The primary E divides by the nulls under
    the frequency layout, so (a) under the frequency layout it equals ``e_same_layout`` and is 1 by
    construction, and (b) under a layout that packs hot slots worse than frequency packing (identity,
    oracle) it exceeds 1: primary E = e_same * (null misses under L / null misses under frequency) > 1."""
    planted = planted_pair("popularity_only")
    assert planted.calibration is not None
    clusters = int(planted.calibration.cluster.max()) + 1
    layouts = lay.build_layouts(planted.calibration, (8,), arch="flat", seed=1, clusters=clusters)
    for rho in core.CACHE_RHOS_PRIMARY:
        for key, layout in layouts.items():
            if layout.rows not in (None, 8) or key == "random_partition@8":
                continue
            record = setting(planted, layout, 8, rho)
            assert not record["degenerate"] and record["e_same_layout"] is not None
            assert 0.95 < record["e_same_layout"] < 1.05
            assert record["e_ratio"] is not None
            if key == "frequency":
                assert 0.96 < record["e_ratio"] < 1.04
                assert record["e_ratio"] == record["e_same_layout"]
            elif key in ("identity", "oracle_cluster"):
                assert record["e_ratio"] > 1.1  # observed 1.24-1.42; hot slots spread over pages
    assert planted.expected == "E~1"


def test_planted_aligned_sharing_has_e_well_below_one_and_random_sharing_does_not() -> None:
    """Derivation (primary E, nulls under the frequency layout). Random sharing: each fact owns random
    slots, so a layout fitted afterwards gains only through co-selection inside one query; the auditor's
    expectation is E near 0.77 for the optimised layouts (observed 0.79-0.82; band 0.7-0.9), and
    identity/frequency, which do not pack by co-selection, stay at 1 (band 0.95-1.1: identity sits
    slightly above 1 because its pages are less hot-packed than the frequency null's). Aligned sharing:
    a cluster owns a 32-slot block and contexts of eight facts of one cluster are consecutive, so the
    block's pages are reused across the context: the optimised and oracle layouts nearly eliminate
    capacity misses (< 0.2), and even identity/frequency, which keep part of a block on shared pages
    through temporal reuse, are well below 1 (< 0.5)."""
    aligned, shared = (
        planted_pair("clusters_aligned_sharing"),
        planted_pair("clusters_random_sharing"),
    )
    assert aligned.calibration is not None and shared.calibration is not None
    clusters = int(aligned.calibration.cluster.max()) + 1
    results: dict[str, dict[str, float]] = {}
    for name, planted in (("aligned", aligned), ("random", shared)):
        assert planted.calibration is not None
        layouts = lay.build_layouts(
            planted.calibration, (8,), arch="flat", seed=1, clusters=clusters
        )
        results[name] = {}
        for key in ("identity", "frequency", "coaccess@8", "oracle_cluster"):
            record = setting(planted, layouts[key], 8, 1 / 4)
            assert record["e_ratio"] is not None and not record["degenerate"]
            assert record["e_same_layout"] is not None
            results[name][key] = record["e_ratio"]
            results[name][key + "|same"] = record["e_same_layout"]
    assert results["aligned"]["oracle_cluster"] < 0.2 and results["aligned"]["coaccess@8"] < 0.2
    assert results["aligned"]["identity"] < 0.5 and results["aligned"]["frequency"] < 0.5
    assert 0.7 < results["random"]["coaccess@8"] < 0.9  # the auditor's expectation: near 0.77
    assert 0.7 < results["random"]["coaccess@8|same"] < 0.9
    assert 0.95 < results["random"]["identity"] < 1.1
    assert 0.95 < results["random"]["frequency"] < 1.05
    for key in ("coaccess@8", "oracle_cluster"):
        assert results["aligned"][key] / results["random"][key] < 0.8  # LOCALITY_POSITIVE-sized gap
    assert (aligned.expected, shared.expected) == ("LOCALITY_POSITIVE", "NO_DIFFERENCE")


def test_planted_collapsed_single_set_is_degenerate_with_the_identity_null() -> None:
    planted = planted_pair("collapsed_single_set")
    assert planted.trace is not None and planted.calibration is not None
    nulls = sim.make_nulls(planted.trace, core.NULL_SEEDS_A)
    assert nulls.single_set and len(set(nulls.stream_sha256)) == 1
    for rows in (2, 8, 32):
        for rho in core.CACHE_RHOS_SWEEP:
            record = setting(planted, lay.identity_layout(4096), rows, rho)
            assert record["degenerate"] and record["single_set"] and record["actual_misses"] == 0
            assert record["null_miss_rate"] == 0.0 and record["e_ratio"] is None
            assert record["null_method"] == sim.IDENTITY_NULL_METHOD
    assert planted.expected == "DEGENERATE"


def test_planted_working_set_below_cache_is_degenerate_but_not_single_set() -> None:
    planted = planted_pair("working_set_below_cache", slots=16384)
    assert planted.trace is not None and planted.calibration is not None
    assert sim.working_set(planted.calibration) > 12000  # large W, so the cache is large
    assert int(torch.unique(planted.trace.selected).numel()) == sim.PLANTED_BELOW_CACHE_SLOTS
    layout = lay.identity_layout(16384)
    for rows in core.CACHE_ROWS_PRIMARY:
        for rho in core.CACHE_RHOS_PRIMARY:
            record = setting(planted, layout, rows, rho)
            assert record["degenerate"] and not record["single_set"]
            assert record["null_miss_rate"] < core.E_NULL_FLOOR
            assert record["null_method"] == sim.REGISTERED_NULL_METHOD
    assert planted.expected == "DEGENERATE"


def test_planted_incomplete_input_and_unknown_kind() -> None:
    planted = planted_pair("incomplete_input")
    assert (
        planted.trace is None and planted.calibration is None and planted.expected == "INCOMPLETE"
    )
    with pytest.raises(ValueError):
        sim.planted_trace("nonsense", slots=4096, seed=1)
    with pytest.raises(ValueError):
        sim.planted_trace("popularity_only", slots=4001, seed=1)


def test_planted_traces_are_deterministic_and_well_formed() -> None:
    for kind in sim.PLANTED_KINDS[:-1]:
        a, b = planted_pair(kind, 512, 179003), planted_pair(kind, 512, 179003)
        c = planted_pair(kind, 512, 179004)
        assert (
            a.trace is not None
            and b.trace is not None
            and c.trace is not None
            and a.calibration is not None
        )
        assert torch.equal(a.trace.selected, b.trace.selected)
        assert a.trace.selected.shape == (256, 8) and a.calibration.selected.shape == (512, 8)
        assert a.calibration.stream == "calibration" and a.trace.stream == "panel_a"
        assert bool((a.trace.position % 8 == 6).all()) and int(a.trace.cluster.max()) == 15
        assert all(len(set(r)) == 8 for r in a.trace.selected.tolist())
        if kind != "collapsed_single_set":
            assert not torch.equal(a.trace.selected, c.trace.selected)
    # facts: every fact once in the evaluation stream, twice in the calibration stream
    a = planted_pair("clusters_aligned_sharing", 512, 179003)
    assert a.trace is not None and a.calibration is not None
    assert (
        torch.bincount(a.trace.fact).tolist() == [1] * 256
        and torch.bincount(a.calibration.fact).tolist() == [2] * 256
    )
    # eight consecutive queries are one context of one cluster
    assert bool((a.trace.cluster.view(-1, 8) == a.trace.cluster.view(-1, 8)[:, :1]).all())


# --- which registered cells are simulated ------------------------------------------------------------------------------
def test_simulation_plan_counts_and_membership() -> None:
    plan = sim.simulation_plan()
    full, sweep, none = plan["full"], plan["sweep_answer_only"], plan["not_simulated"]
    assert (len(full), len(sweep), len(none)) == (22, 12, 66)
    assert len(full) + len(sweep) + len(none) == core.TOTAL_CELLS == len(core.cells())
    assert {c.label for c in full}.isdisjoint({c.label for c in sweep})
    assert {c.block for c in full} == {"A1", "A2", "B1", "C1"}
    assert {c.slots for c in full} == {16384}
    assert {c.block for c in sweep} == {"A1", "A2"} and {c.slots for c in sweep} == {4096, 65536}
    assert {c.arch for c in full + sweep} <= {"flat", "fixed_tree", "learned_tree"}
    # per-(block, slots) counts
    assert {
        (b, n): sum(1 for c in full if (c.block, c.slots) == (b, n))
        for b, n in (("A1", 16384), ("A2", 16384), ("B1", 16384), ("C1", 16384))
    } == {("A1", 16384): 3, ("A2", 16384): 3, ("B1", 16384): 8, ("C1", 16384): 8}
    assert all(
        sum(1 for c in sweep if (c.block, c.slots) == (b, n)) == 3
        for b in ("A1", "A2")
        for n in (4096, 65536)
    )
    # every A1/A2 cell is in a simulated group; nothing outside A1/A2/B1/C1 is
    assert all(
        c.block in ("A1", "A2") for c in core.cells() if c.slots != 16384 and c in full + sweep
    )
    assert not any(c.block not in ("A1", "A2", "B1", "C1") for c in full + sweep)
    scope = sim.simulation_scope(full[0])
    assert scope is not None and scope.trace_kinds == ("answer", "all") and not scope.descriptive
    scope = sim.simulation_scope(sweep[0])
    assert scope is not None and scope.trace_kinds == ("answer",) and scope.descriptive
    assert sim.simulation_scope(none[0]) is None


# --- key traffic: arithmetic only ------------------------------------------------------------------------------------------
def test_key_traffic_is_an_identity() -> None:
    flat = sim.key_traffic("flat", 16384, 16, 1000)
    tree = sim.key_traffic("learned_tree", 16384, 16, 1000)
    assert flat["basis"] == "identity" and tree["basis"] == "identity"
    assert flat["key_rows_per_query"] == 16384 and tree["key_rows_per_query"] == 64 + 512
    assert flat["keys_on_storage_bytes_per_query"] == 16384 * 16 * 4
    assert tree["keys_on_storage_total_bytes"] == (64 + 512) * 16 * 4 * 1000
    assert flat["keys_in_ram_total_bytes"] == 0 == tree["keys_in_ram_bytes_per_query"]
    with pytest.raises(ValueError):
        sim.key_traffic("dense", 4096, 16, 1)


# --- 65,536 slots: time and memory ------------------------------------------------------------------------------------------
SMOKE = textwrap.dedent(
    """
    import json, resource, sys, time
    sys.path.insert(0, {root!r})
    import torch
    from studies.p9 import core, sim, layout
    from studies.p9.core import Trace
    planted = sim.planted_trace("popularity_only", slots=65536, seed=179001)
    trace, cal = planted.trace, planted.calibration
    q = int(trace.selected.shape[0])
    t0 = time.time()
    record = sim.simulate_setting(trace, cal, layout.identity_layout(65536), rows=8, rho=0.25, tie="asc",
        null_seeds=core.NULL_SEEDS_A, label="s", update=0, stream="panel_a")
    print(json.dumps({{"seconds": time.time() - t0, "maxrss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
        "actual_misses": record["actual_misses"], "e": record["e_ratio"], "queries": q}}))
    """
)


def test_65536_slot_smoke_time_and_memory() -> None:
    code = SMOKE.format(root=str(Path(__file__).resolve().parents[1]))
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["maxrss_bytes"] < 1024**3  # peak resident set of the whole process, bytes
    assert (
        out["queries"] == 32768 and out["seconds"] < 60
    )  # simulate_setting: pages, three nulls, four LRU passes
    assert out["e"] is not None
