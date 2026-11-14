"""Synthetic tests for the P7-A simulator, layouts, streams and closed form (ADR-0013).

Every number here is a hand calculation or a measurement on synthetic data; none is evidence about
the registered study. No model and no checkpoint is used.
"""

import random
from pathlib import Path

import pytest
import torch

from arborlm import p7a_core as core
from arborlm import p7a_sim as sim
from arborlm.p7a_trace import synthetic_trace

SMALL = 4 * core.CONTEXT  # four contexts of 64 queries


def run(queries: list[tuple[int, ...]], capacity: int, warm: int | None = None) -> list[int]:
    return sim.lru_pass(queries, capacity, warm)


# --- cache model, hand computed -------------------------------------------------------------------
def test_capacity_exactly_eight_hand_trace() -> None:
    # C = 8. q0 touches pages 0..7 (8 first-touch misses). q1 needs page 8: one miss, and the
    # least recently used page not used by q1 is page 0 (ties evicted in ascending page order).
    # q2 needs page 0: a capacity miss; it evicts page 1. q3 needs page 1: capacity miss.
    stream = [tuple(range(8)), (8,), (0,), (1,)]
    # misses_all, first_touch_all, misses_warm (q2, q3), first_touch_warm
    assert run(stream, 8, warm=2) == [11, 9, 2, 0]


def test_eviction_never_removes_a_page_of_the_current_query() -> None:
    # q1 reuses pages 0..6 and adds 8. The only page not used by q1 is 7, so 7 is evicted even
    # though pages 0..6 are older than 8. q2 then misses on 7 (capacity), q3 hits on 0..6 and 8.
    stream = [tuple(range(8)), (0, 1, 2, 3, 4, 5, 6, 8), (7,), (0, 1, 2, 3, 4, 5, 6, 8)]
    # q0 8 misses; q1 1 miss; q2 1 miss (7 was evicted; evicts 0, the LRU of q1's set);
    # q3 needs 0 again -> a capacity miss for page 0 only.
    assert run(stream, 8, warm=0) == [11, 9, 11, 9]
    assert run(stream, 8, warm=3) == [11, 9, 1, 0]


def test_cache_larger_than_the_store_misses_only_first_touches() -> None:
    stream = [(0, 1, 2, 3), (1, 2), (3,), (0, 4), (4, 0, 1)] * 20
    result = run([tuple(sorted(q)) for q in stream], 128)
    assert result[0] == result[1] == 5  # five distinct pages, never evicted
    assert result[2] == result[3] == 0  # nothing new in the second half


def test_repeated_pages_within_a_query_count_once() -> None:
    positions = list(range(core.SLOTS))
    selected = torch.tensor([[0, 1, 2, 3, 4, 5, 6, 7], [0, 8, 16, 24, 32, 40, 48, 56]])
    assert sim.page_sets(positions, 4, selected) == [(0, 1), (0, 2, 4, 6, 8, 10, 12, 14)]
    assert sim.page_sets(positions, 512, selected) == [(0,), (0,)]


def test_first_touch_versus_capacity_classification() -> None:
    # C = 8, nine distinct pages cycled twice. Every page of the second cycle was read before
    # and has been evicted: those are capacity misses, the first cycle's are first touches.
    cycle = [(p,) for p in range(9)]
    for index in range(9):  # make every query need one page but give the cache real pressure
        assert len(cycle[index]) == 1
    stream = [tuple(range(8)), (8,)] + [(p,) for p in range(9)]
    misses_all, first_all, misses_warm, first_warm = run(stream, 8, warm=2)
    assert first_all == 9 and first_warm == 0
    # After q0..q1 the cache holds 1..8; (0,) misses and evicts 1, (1,) misses and evicts 2, ...
    assert misses_warm == 9 and misses_all == 8 + 1 + 9


def test_warm_up_boundary_is_by_stream_position() -> None:
    stream = [(0,), (1,), (2,), (3,)]
    assert run(stream, 8, warm=2) == [4, 4, 2, 2]  # queries 2 and 3 are counted
    assert run(stream, 8, warm=3) == [4, 4, 1, 1]
    assert run(stream, 8) == [4, 4, 2, 2]  # default: the second half is counted


def test_overflowing_query_keeps_all_its_pages_then_trims() -> None:
    # Only possible for a key cache: three pages against capacity 2. All three are held after the
    # query; the next query (page 5) evicts from the old query's pages, ascending, down to C.
    stream = [(0, 1, 2), (5,), (2,)]
    # q0: 3 misses; q1: miss, cache 4 -> pops 0 and 1, keeps (2, 5); q2: hit on 2.
    assert run(stream, 2, warm=0) == [4, 4, 4, 4]


def test_shortcut_equals_the_full_pass_and_invariants_hold() -> None:
    rng = random.Random(5)
    for _ in range(25):
        pages = rng.randint(3, 40)
        stream = [
            tuple(sorted(rng.sample(range(pages), rng.randint(1, min(8, pages)))))
            for _ in range(200)
        ]
        stats, _, _ = sim.stream_stats(stream)
        by_full = {c: sim.cache_counts(stream, c, stats, shortcut=False) for c in core.CS}
        by_short = {c: sim.cache_counts(stream, c, stats, shortcut=True) for c in core.CS}
        assert by_full == by_short
        sim.check_group(stats, by_full, "random")


def test_invariant_violations_are_hard_stops() -> None:
    stream = [(0, 1), (2,), (0,)]
    stats, _, _ = sim.stream_stats(stream)
    good = {c: sim.cache_counts(stream, c, stats) for c in (8, 16)}
    sim.check_group(stats, good, "hand")
    bad = {c: dict(v) for c, v in good.items()}
    bad[8]["misses_all"] = stats["pages_sum"] + 1
    with pytest.raises(core.InvariantError):
        sim.check_group(stats, bad, "hand")
    bad = {c: dict(v) for c, v in good.items()}
    bad[16]["first_touch_all"] += 1
    with pytest.raises(core.InvariantError):
        sim.check_group(stats, bad, "hand")
    bad = {c: dict(v) for c, v in good.items()}
    bad[16]["misses_all"] = bad[16]["first_touch_all"] = stats["distinct_stream"] - 1
    with pytest.raises(core.InvariantError):
        sim.check_group(stats, bad, "hand")
    grow = {8: dict(good[8]), 16: dict(good[16])}
    grow[8]["misses_warm"] = grow[8]["first_touch_warm"]
    grow[16]["misses_warm"] = grow[16]["first_touch_warm"] + 1
    with pytest.raises(core.InvariantError):
        sim.check_group(stats, grow, "hand")


def test_capacity_misses_never_grow_with_capacity_on_random_streams() -> None:
    rng = random.Random(9)
    for _ in range(10):
        stream = [tuple(sorted(rng.sample(range(60), rng.randint(1, 8)))) for _ in range(500)]
        previous = None
        for capacity in core.CS:
            counts = sim.lru_pass(stream, capacity)
            if previous is not None:
                assert counts[0] <= previous[0] and counts[2] <= previous[2]
            previous = counts


def test_stream_stats_hand_example() -> None:
    # 128 queries = two contexts. Pages: context 0 alternates (0,) and (0, 1); context 1 is (2,).
    stream = [((0,) if i % 2 == 0 else (0, 1)) for i in range(64)] + [(2,)] * 64
    stats, ctx_sum, ctx_distinct = sim.stream_stats(stream)
    assert stats["hist"][:2] == [96, 32]  # 96 one-page queries, 32 two-page queries
    assert stats["pages_sum"] == 96 + 64
    assert ctx_sum == [96, 64] and ctx_distinct == [2, 1]
    assert stats["distinct_stream"] == 3 and stats["distinct_first_half"] == 2
    # reuse inside context 0: 63 pairs; a (0,1) query after (0,) reuses 1 of 2 pages, a (0,) query
    # after (0,1) reuses 1 of 1. Pairs i = 1..63: odd i -> (0,1) touches 2, reuses 1 (32 of them);
    # even i -> (0,) touches 1, reuses 1 (31 of them). Context 1 (i = 65..127): (2,) reuses 1 of 1.
    assert stats["reuse_within"] == [32 + 31 + 63, 64 + 31 + 63]
    # the only boundary pair (query 64 after query 63 = (0, 1)): (2,) shares nothing.
    assert stats["reuse_cross"] == [0, 1]
    assert stats["curve_points"] == [64, 128]
    assert stats["curve"] == [2, 3]


def test_branch_locality_hand_example() -> None:
    # Two contexts of 64 queries: context 0 visits (0, 1) throughout; context 1 alternates top-1
    # between 2 and 3 with the visited pair (2, 3) / (3, 2).
    rows = [[0, 1]] * 64 + [[2, 3] if i % 2 == 0 else [3, 2] for i in range(64)]
    result = sim.branch_locality(torch.tensor(rows))
    assert result["same_top1_within"] == [63, 63 + 63]  # context 0 all same; context 1 never
    assert result["same_top1_within"][0] == 63
    assert result["same_top1_across"] == [0, 1]
    assert result["share_branch_within"] == [126, 126]
    assert result["share_branch_across"] == [0, 1]  # (0, 1) then (2, 3) share nothing
    assert result["top1_runs"] == 1 + 64
    assert result["top1_run_length_hist"][0] == 64 and result["top1_run_length_hist"][63] == 1
    assert result["distinct_branches_per_context_sum"] == 2 + 2


def test_key_page_sets_and_flat_analytic() -> None:
    positions = list(range(core.SLOTS))
    # 64 key rows per 4 KiB page: branch 0 pages 0-3, branch 1 pages 4-7, branch 5 pages 20-23
    pages = sim.key_page_sets(positions, 64, torch.tensor([[0, 1], [5, 0]]))
    assert pages == [tuple(range(8)), (0, 1, 2, 3, 20, 21, 22, 23)]
    # 64 KiB pages hold 1,024 key rows: branches 0..3 share page 0
    assert sim.key_page_sets(positions, 1024, torch.tensor([[0, 3], [0, 4]])) == [(0,), (0, 1)]
    flat = sim.flat_key_analytic(32)
    assert flat["key_pages"] == 64 and flat["by_c"]["32"]["misses_warm"] == 16384 * 64
    assert flat["by_c"]["64"]["misses_warm"] == 0 and flat["by_c"]["64"]["misses_all"] == 64
    assert sim.flat_key_analytic(512)["key_pages"] == 4
    assert sim.flat_key_analytic(512)["by_c"]["8"]["misses_warm"] == 0


# --- closed form ----------------------------------------------------------------------------------
def test_closed_form_matches_the_registered_values() -> None:
    assert core.uniform_flat(32) == pytest.approx(7.7911, abs=5e-5)
    assert core.uniform_flat(128) == pytest.approx(7.1831, abs=5e-5)
    assert core.uniform_flat(512) == pytest.approx(5.2538, abs=5e-5)
    assert core.uniform_flat(2) == pytest.approx(7.9932, abs=5e-5)
    positions = core.layout_id()

    def two_branches(rows: int, pair: tuple[int, int]) -> float:
        return core.expected_distinct_pages(
            core.branch_pair_rows_per_page(positions, rows, pair), core.TOP
        )

    assert two_branches(32, (0, 1)) == pytest.approx(6.4876, abs=5e-5)
    assert two_branches(128, (0, 1)) == pytest.approx(3.6069, abs=5e-5)
    assert two_branches(2, (0, 1)) == pytest.approx(7.9452, abs=5e-5)
    assert two_branches(512, (0, 1)) == pytest.approx(1.0)  # branches 0 and 1 share a 512-row page
    assert two_branches(512, (0, 2)) == pytest.approx(1.9926, abs=5e-5)


def test_closed_form_against_monte_carlo() -> None:
    generator = torch.Generator().manual_seed(1)
    draws = 20000
    for rows in (2, 32):
        picks = torch.stack(
            [torch.randperm(core.SLOTS, generator=generator)[: core.TOP] for _ in range(draws)]
        )
        pages = (picks // rows).sort(dim=1).values
        distinct = 1 + (pages[:, 1:] != pages[:, :-1]).sum(dim=1)
        assert float(distinct.float().mean()) == pytest.approx(core.uniform_flat(rows), abs=0.03)
    # two branches (512 rows) at R = 32
    positions = core.layout_id()
    ref = core.expected_distinct_pages(core.branch_pair_rows_per_page(positions, 32, (3, 9)))
    picks = torch.stack([torch.randperm(512, generator=generator)[:8] for _ in range(draws)])
    slots = torch.where(picks < 256, 3 * 256 + picks, 9 * 256 + picks - 256)
    pages = (slots // 32).sort(dim=1).values
    distinct = 1 + (pages[:, 1:] != pages[:, :-1]).sum(dim=1)
    assert float(distinct.float().mean()) == pytest.approx(ref, abs=0.03)


# --- layouts --------------------------------------------------------------------------------------
def test_layouts_are_permutations_and_bfreq_keeps_branches() -> None:
    selected, _ = synthetic_trace("fixed_tree", 3, queries=SMALL)
    counts = core.selection_counts(selected)
    layouts = core.build_layouts("fixed_tree", counts)
    assert list(layouts) == ["L-ID", *core.LAYOUTS_RAND, "L-FREQ", "L-BFREQ"]
    assert all(core.is_permutation(p) for p in layouts.values())
    bfreq = layouts["L-BFREQ"]
    assert all(bfreq[s] // 256 == s // 256 for s in range(core.SLOTS))
    flat_layouts = core.build_layouts("flat", counts)
    assert "L-BFREQ" not in flat_layouts and len(core.layouts_for("flat")) == 5
    assert len(core.layouts_for("fixed_tree")) == 6 == len(core.layouts_for("learned_tree"))


def test_freq_layout_order_and_tie_rule() -> None:
    counts = [0] * core.SLOTS
    counts[10], counts[300], counts[5] = 7, 7, 9
    freq = core.layout_freq(counts)
    assert freq[5] == 0  # highest count first
    assert freq[10] == 1 and freq[300] == 2  # tie: ascending slot ID
    assert freq[0] == 3 and freq[1] == 4  # zero counts: ascending slot ID
    bfreq = core.layout_bfreq(counts)
    assert bfreq[5] == 0 and bfreq[10] == 1  # branch 0: counts 9, 7 first
    assert bfreq[300] == 256  # branch 1 starts at position 256; slot 300 is its hottest
    assert bfreq[256] == 257  # then the zero-count slots in ascending ID


def test_layouts_depend_only_on_the_calibration_trace() -> None:
    calibration, _ = synthetic_trace("flat", 1, queries=SMALL)
    first, _ = synthetic_trace("flat", 2, queries=SMALL)
    second, _ = synthetic_trace("flat", 3, queries=SMALL)
    cal_counts = core.selection_counts(calibration)
    assert core.layout_freq(cal_counts) == core.layout_freq(list(cal_counts))
    sims = [
        sim.simulate_checkpoint(
            kind="flat",
            index=0,
            eval_selected=ev,
            eval_branches=None,
            calibration_selected=calibration,
        )
        for ev in (first, second)
    ]
    assert sims[0]["layouts"] == sims[1]["layouts"]  # same fingerprints for different eval traces
    other_cal, _ = synthetic_trace("flat", 9, queries=SMALL)
    changed = sim.simulate_checkpoint(
        kind="flat",
        index=0,
        eval_selected=first,
        eval_branches=None,
        calibration_selected=other_cal,
    )
    assert changed["layouts"]["L-FREQ"] != sims[0]["layouts"]["L-FREQ"]
    assert changed["layouts"]["L-ID"] == sims[0]["layouts"]["L-ID"]


def test_rand_layouts_are_the_registered_seeds_and_shared_across_checkpoints() -> None:
    for seed in core.RAND_SEEDS:
        expected = torch.randperm(core.SLOTS, generator=torch.Generator().manual_seed(seed))
        assert core.layout_rand(seed) == expected.tolist()
    assert len({tuple(core.layout_rand(s)) for s in core.RAND_SEEDS}) == 3
    counts = [1] * core.SLOTS
    assert core.build_layouts("flat", counts)["L-RAND-91102"] == core.layout_rand(91102)


# --- streams --------------------------------------------------------------------------------------
def test_shuffles_are_the_registered_permutations() -> None:
    order = torch.randperm(core.QUERIES, generator=torch.Generator().manual_seed(91201)).tolist()
    assert core.query_order("order_shuffled") == order == core.order_permutation()
    contexts = torch.randperm(
        core.CONTEXTS, generator=torch.Generator().manual_seed(91202)
    ).tolist()
    expanded = core.query_order("context_shuffled")
    assert expanded[:64] == [contexts[0] * 64 + i for i in range(64)]  # order inside kept
    assert sorted(expanded) == list(range(core.QUERIES))
    assert [expanded[i] // 64 for i in range(0, core.QUERIES, 64)] == contexts


def test_shuffled_streams_keep_the_multiset_of_queries() -> None:
    selected, _ = synthetic_trace("flat", 4, queries=SMALL)
    kwargs = dict(
        kind="flat",
        index=0,
        eval_selected=selected,
        eval_branches=None,
        calibration_selected=selected,
    )
    record = sim.simulate_checkpoint(**kwargs)  # type: ignore[arg-type]
    actual = record["streams"]["actual"]["L-ID|R2"]["stats"]["hist"]
    assert record["streams"]["order_shuffled"]["L-ID|R2"]["stats"]["hist"] == actual
    assert record["streams"]["context_shuffled"]["L-ID|R2"]["stats"]["hist"] == actual
    again = sim.simulate_checkpoint(**kwargs)  # type: ignore[arg-type]
    for item in (record, again):
        item.pop("seconds")
    assert record == again  # deterministic


AUDITOR_NULL = (
    Path(__file__).resolve().parents[1]
    / "docs/reviews/p7a-preflight-2026-11-13/check_exact_null.py"
)


def heavy_counts(
    queries: int, hottest: int, active: int = 700, slots: int = core.SLOTS
) -> list[int]:
    """A heavy-tailed histogram with ``8 * queries`` occurrences, slot 0 selected ``hottest`` times
    and a Zipf-like tail over ``active`` further slots (no count above ``queries``)."""
    total = core.TOP * queries
    counts = [0] * slots
    counts[0] = hottest
    remaining = total - hottest
    weights = [1 / (rank + 1) for rank in range(1, active + 1)]
    for i, weight in enumerate(weights, start=1):
        counts[i] = min(queries, int(remaining * weight / sum(weights)))
    leftover = total - sum(counts)
    slot = 1
    while leftover:
        if counts[slot] < queries:
            counts[slot] += 1
            leftover -= 1
        slot = slot % active + 1
    assert sum(counts) == total and max(counts) <= queries
    return counts


def check_exact(counts: list[int], drawn: torch.Tensor) -> None:
    assert drawn.shape[1] == core.TOP
    assert core.selection_counts(drawn) == counts  # every per-slot count reproduced exactly
    assert bool((drawn.sort(dim=1).values[:, 1:] != drawn.sort(dim=1).values[:, :-1]).all())


@pytest.mark.parametrize("queries", [64, 512, 4096])
def test_frequency_matched_reproduces_counts_exactly_on_heavy_tails(queries: int) -> None:
    for hottest in (queries // 10, queries * 3 // 5, queries):  # last: slot 0 in EVERY query
        counts = heavy_counts(queries, hottest)
        drawn = core.frequency_matched(counts, 91301, 7, queries=queries)
        assert drawn.shape == (queries, 8)
        check_exact(counts, drawn)


def test_frequency_matched_full_size_with_a_slot_in_more_than_half_the_queries() -> None:
    counts = heavy_counts(core.QUERIES, 20000)  # 20,000 > 16,384 = half of 32,768
    assert counts[0] > core.QUERIES // 2
    drawn, info = core.frequency_matched_detail(counts, 91302, 40)
    check_exact(counts, drawn)
    assert info["counts_equal_trace"] and info["distinct_slots_per_query"]
    assert info["generator_seed"] == 91302 * 1000 + 40 and info["repair_swaps"] > 0
    assert len(info["stream_sha256"]) == 64


def test_frequency_matched_repair_terminates_in_the_extreme_cases() -> None:
    # every query holds slot 0 (count == queries): the repair must still finish, with no duplicate
    counts = heavy_counts(256, 256, active=60)
    for seed in core.FM_SEEDS:
        check_exact(counts, core.frequency_matched(counts, seed, 3, queries=256))
    # uniform over exactly the minimum number of slots (8): every query holds all eight
    tight = [0] * core.SLOTS
    for slot in range(8):
        tight[slot] = 128
    drawn = core.frequency_matched(tight, 91301, 0, queries=128)
    check_exact(tight, drawn)
    assert bool((drawn.sort(dim=1).values == torch.arange(8)).all())


def test_frequency_matched_is_deterministic_and_replicates_differ() -> None:
    counts = heavy_counts(512, 400)
    first = core.frequency_matched(counts, 91301, 7, queries=512)
    assert torch.equal(core.frequency_matched(counts, 91301, 7, queries=512), first)
    for other in (
        core.frequency_matched(counts, 91302, 7, queries=512),  # another replicate
        core.frequency_matched(counts, 91301, 8, queries=512),  # another checkpoint index
    ):
        assert not torch.equal(other, first)
        check_exact(counts, other)
    assert core.fm_generator_seed(91301, 0) == 91301000
    assert core.fm_generator_seed(91303, 80) == 91303080


def test_frequency_matched_infeasible_histograms_raise_clear_errors() -> None:
    counts = heavy_counts(64, 60)
    counts[1] += counts[0] - 65  # slot 0 -> 65 occurrences (> 64 queries); the total is kept
    counts[0] = 65
    assert sum(counts) == 8 * 64 and max(counts) > 64
    with pytest.raises(ValueError, match="no arrangement"):
        core.frequency_matched(counts, 91301, 0, queries=64)
    with pytest.raises(ValueError, match="sum to"):
        core.frequency_matched([1] * 100, 91301, 0, queries=64)
    with pytest.raises(ValueError, match="negative"):
        core.frequency_matched([-1, 513] + [0] * 4094, 91301, 0, queries=64)


def test_frequency_matched_check_is_a_hard_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    counts = heavy_counts(64, 30)
    original = core._deal_and_repair

    def broken(
        c: list[int], g: random.Random, queries: int, top: int
    ) -> tuple[list[list[int]], int]:
        rows, swaps = original(c, g, queries, top)
        rows[0][0] = (rows[0][0] + 1) % core.SLOTS  # corrupt one occurrence
        return rows, swaps

    monkeypatch.setattr(core, "_deal_and_repair", broken)
    with pytest.raises(core.InvariantError):
        core.frequency_matched(counts, 91301, 0, queries=64)


def test_frequency_matched_steps_1_to_3_equal_the_auditors_script() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_exact_null", AUDITOR_NULL)
    assert spec is not None and spec.loader is not None
    auditor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auditor)  # no side effects: main() is behind __name__ == "__main__"
    counts = heavy_counts(core.QUERIES, 20000)
    seed = core.fm_generator_seed(91301, 7)
    theirs, their_swaps = auditor.exact_null(counts, seed)
    mine, my_swaps = core._deal_and_repair(counts, random.Random(seed), core.QUERIES, core.TOP)
    assert mine == theirs and my_swaps == their_swaps
    # the registered stream is that arrangement with the queries permuted by the same generator,
    # after the step-1 shuffle (step 4)
    generator = random.Random(seed)
    check_rows, _ = core._deal_and_repair(counts, generator, core.QUERIES, core.TOP)
    order = list(range(core.QUERIES))
    generator.shuffle(order)
    stream = core.frequency_matched(counts, 91301, 7)
    assert stream.tolist() == [check_rows[i] for i in order]
    assert stream.tolist() != check_rows  # the final permutation is applied


def test_frequency_matched_is_fast_enough() -> None:
    import time

    counts = heavy_counts(core.QUERIES, 20000)
    started = time.monotonic()
    core.frequency_matched(counts, 91303, 11)
    assert time.monotonic() - started < 5.0  # measured about 0.1-0.4 s; generous for slow CI


def test_frequency_matched_streams_in_a_checkpoint_record_are_checkable() -> None:
    selected, _ = synthetic_trace("flat", 14, queries=SMALL)
    record = sim.simulate_checkpoint(
        kind="flat",
        index=2,
        eval_selected=selected,
        eval_branches=None,
        calibration_selected=selected,
    )
    counts = core.selection_counts(selected)
    for name, seed in zip(core.STREAMS_FM, core.FM_SEEDS, strict=True):
        info = record["frequency_matched"][name]
        stream, again = core.frequency_matched_detail(counts, seed, 2, queries=SMALL)
        assert info == again and info["generator_seed"] == seed * 1000 + 2
        # the by_c counts and stats are stored for L-ID and L-FREQ exactly as for the actual stream
        for layout in ("L-ID", "L-FREQ"):
            for rows in core.RS:
                group = record["streams"][name][f"{layout}|R{rows}"]
                assert set(group) == {"stats", "by_c"} and set(group["by_c"]) == {
                    "8",
                    "16",
                    "32",
                    "64",
                    "128",
                }
                positions = core.layout_id() if layout == "L-ID" else None
                if positions is not None:
                    pages = sim.page_sets(positions, rows, stream)
                    assert group["stats"]["pages_sum"] == sum(len(q) for q in pages)
                    assert group["by_c"]["32"] == sim.cache_counts(pages, 32, group["stats"])


def test_registered_independent_selection_is_the_auditors() -> None:
    import importlib.util

    path = AUDITOR_NULL.with_name("independent_sim.py")
    spec = importlib.util.spec_from_file_location("independent_sim", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mine = core.independent_selection()
    assert len(mine) == 18 and len(set(mine)) == 18
    assert mine == module.registered_selection()
    assert mine[:3] == [
        core.cell_label(p, "flat")
        for p in sorted({p for p, _ in core.registered_checkpoints()})[:3]
    ]


# --- whole checkpoint -----------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ["flat", "fixed_tree"])
def test_checkpoint_configuration_set_is_the_enumerated_one(kind: str) -> None:
    selected, branches = synthetic_trace(kind, 11, queries=SMALL)
    calibration, _ = synthetic_trace(kind, 12, queries=SMALL)
    record = sim.simulate_checkpoint(
        kind=kind,
        index=1,
        eval_selected=selected,
        eval_branches=branches,
        calibration_selected=calibration,
    )
    assert record["complete"] is True
    total = sum(len(group["by_c"]) for s in record["streams"].values() for group in s.values())
    assert total == sim.config_count(kind) == (450 if kind == "flat" else 480)
    assert set(record["streams"]) == {
        "actual",
        "order_shuffled",
        "freq_matched_1",
        "freq_matched_2",
        "freq_matched_3",
        "context_shuffled",
    }
    assert len(record["streams"]["actual"]) == len(core.layouts_for(kind)) * 6
    for name in ("order_shuffled", "freq_matched_1", "context_shuffled"):
        assert set(record["streams"][name]) == {
            f"{layout}|R{r}" for layout in ("L-ID", "L-FREQ") for r in core.RS
        }
    assert ("branch_locality" in record) == (kind != "flat")
    assert len(record["bootstrap"]) == len(core.layouts_for(kind)) * 6
    for group in record["streams"]["actual"].values():
        assert set(group["by_c"]) == {"8", "16", "32", "64", "128"}


def test_checkpoint_at_hand_computable_extremes() -> None:
    # One page per slot (R = 1): per-query distinct pages is always 8. One page for 512 slots:
    # at most 8 pages exist, so the cache holds everything and capacity misses are zero.
    selected, _ = synthetic_trace("flat", 21, queries=SMALL)
    record = sim.simulate_checkpoint(
        kind="flat",
        index=0,
        eval_selected=selected,
        eval_branches=None,
        calibration_selected=selected,
    )
    stats = record["streams"]["actual"]["L-ID|R1"]["stats"]
    assert stats["hist"] == [0] * 7 + [SMALL]
    big = record["streams"]["actual"]["L-ID|R512"]
    assert all(v["misses_warm"] == v["first_touch_warm"] for v in big["by_c"].values())
    assert big["stats"]["distinct_stream"] <= 8


def test_deadline_preserves_the_partial_record() -> None:
    selected, _ = synthetic_trace("flat", 22, queries=SMALL)
    with pytest.raises(sim.CapExceeded) as caught:
        sim.simulate_checkpoint(
            kind="flat",
            index=0,
            eval_selected=selected,
            eval_branches=None,
            calibration_selected=selected,
            deadline=0.0,
        )
    assert caught.value.partial["complete"] is False  # type: ignore[attr-defined]


def test_bootstrap_is_seeded_and_brackets_the_mean() -> None:
    sums = [8 * 64 - (i % 5) for i in range(512)]
    first = sim.bootstrap_interval(sums, sim.bootstrap_indices())
    second = sim.bootstrap_interval(sums, sim.bootstrap_indices())
    assert first == second
    assert first["boot_lower"] <= first["mean"] <= first["boot_upper"]
    assert sim.bootstrap_indices().shape == (1000, 512)
    expected = torch.randint(0, 512, (1000, 512), generator=torch.Generator().manual_seed(91401))
    assert torch.equal(sim.bootstrap_indices(), expected)


def test_uniform_references_for_flat_and_tree() -> None:
    selected, branches = synthetic_trace("fixed_tree", 5, queries=SMALL)
    layouts = core.build_layouts("fixed_tree", core.selection_counts(selected))
    refs = sim.uniform_references("fixed_tree", layouts, branches)
    visited = {core.pair_key(a, b) for a, b in branches.tolist()}
    assert visited  # the reference averages over the visited pairs of the trace
    assert refs["L-ID"]["512"] <= 2.0 and refs["L-ID"]["1"] == pytest.approx(8.0)
    flat_refs = sim.uniform_references("flat", core.build_layouts("flat", [1] * 4096), None)
    assert flat_refs["L-RAND-91101"]["32"] == pytest.approx(core.uniform_flat(32))


# --- item 10: eviction tie order -----------------------------------------------------------------
def test_ascending_is_the_registered_tie_rule_and_descending_differs_by_hand() -> None:
    # C = 8. q0 holds pages 0..7; q1 needs page 8 and one page must go. Ascending (registered)
    # evicts page 0, descending evicts page 7. q2 then needs page 0, q3 needs page 7.
    stream = [tuple(range(8)), (8,), (0,), (7,)]
    asc = sim.lru_pass(stream, 8, warm_start=2)
    desc = sim.lru_pass(stream, 8, warm_start=2, descending=True)
    # ascending: q2 misses page 0 (evicts page 1), q3 hits page 7  -> 1 warm miss, all 10
    assert asc == [10, 9, 1, 0]
    # descending: q1 evicts 7; q2 hits page 0; q3 misses page 7 -> 1 warm miss, all 10
    assert desc == [10, 9, 1, 0]
    swapped = [tuple(range(8)), (8,), (7,), (7,)]
    assert sim.lru_pass(swapped, 8, warm_start=2) == [9, 9, 0, 0]  # ascending keeps page 7
    assert sim.lru_pass(swapped, 8, warm_start=2, descending=True) == [10, 9, 1, 0]
    assert (
        sim.lru_pass(stream, 8, warm_start=2, descending=False) == asc
    )  # the default is ascending


def test_descending_sensitivity_leaves_every_ascending_result_unchanged() -> None:
    selected, _ = synthetic_trace("flat", 31, queries=SMALL)
    record = sim.simulate_checkpoint(
        kind="flat",
        index=0,
        eval_selected=selected,
        eval_branches=None,
        calibration_selected=selected,
    )
    layouts = core.build_layouts("flat", core.selection_counts(selected))
    pages = sim.page_sets(layouts["L-FREQ"], 2, selected)
    stats, _, _ = sim.stream_stats(pages)
    for capacity in core.CS:  # the stored ascending numbers are the plain default pass
        stored = record["streams"]["actual"]["L-FREQ|R2"]["by_c"][str(capacity)]
        assert stored == sim.cache_counts(pages, capacity, stats)
    sens = record["eviction_order_sensitivity"]
    assert sens["setting"]["R"] == 2 and sens["setting"]["C"] == 32
    assert sens["setting"]["layout"] == "L-FREQ" and sens["setting"]["stream"] == "actual"
    assert sens["ascending"] == record["streams"]["actual"]["L-FREQ|R2"]["by_c"]["32"]
    descending = sim.lru_pass(pages, 32, descending=True)
    assert list(sens["descending"].values()) == descending
    # first touches do not depend on the order, and misses never exceed page touches
    assert sens["descending"]["first_touch_all"] == sens["ascending"]["first_touch_all"]
    assert sens["descending"]["misses_all"] <= stats["pages_sum"]
    # adding it changes nothing else: the same record without the sensitivity block is identical
    again = sim.simulate_checkpoint(
        kind="flat",
        index=0,
        eval_selected=selected,
        eval_branches=None,
        calibration_selected=selected,
    )
    for item in (record, again):
        item.pop("seconds")
    assert record == again


def test_tree_key_cache_hand_trace() -> None:
    # 64 key rows per 4 KiB page. L-ID: branches 0 and 1 hold key pages 0-7, branches 2 and 3
    # pages 8-15. Queries: (0,1) (0,1) (2,3) (0,1); warm-up = first two queries.
    branches = torch.tensor([[0, 1], [0, 1], [2, 3], [0, 1]])
    layouts = {name: core.layout_id() for name in core.KEY_LAYOUTS}
    keys = sim.tree_key_reads(branches, layouts, None)["4096"]["layouts"]["L-ID"]
    assert keys["stats"]["pages_sum"] == 32 and keys["stats"]["distinct_stream"] == 16
    small = keys["by_c"]["8"]  # one query fills the cache: q2 evicts all of q0's pages, q3 reloads
    assert small == {
        "misses_all": 24,
        "first_touch_all": 16,
        "misses_warm": 16,
        "first_touch_warm": 8,
    }
    roomy = keys["by_c"]["16"]  # both page sets fit: only first touches
    assert roomy == {
        "misses_all": 16,
        "first_touch_all": 16,
        "misses_warm": 8,
        "first_touch_warm": 8,
    }
    assert keys["uncached_amplification"] == 1.0
