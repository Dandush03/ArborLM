"""Synthetic tests for the P7-B value-page simulator (ADR-0014 section 5 and 10): both eviction
tie rules on a hand trace, the cache-capacity hard check, invariants, equality with P7-A's
simulator on the configurations P7-A ran, the plan and the reproduction stop."""

import copy
import inspect
import random

import pytest
import torch

from arborlm import p7a_core as a_core
from arborlm import p7a_sim as a_sim
from arborlm import p7b_core as core
from arborlm import p7b_layout as L
from arborlm import p7b_sim as sim
from arborlm import p7b_synth
from arborlm.p7a_trace import synthetic_trace


def tie_stream(last: int) -> sim.PageSets:
    """Capacity 3. Warm half: page 9 only. Counted half: (1, 2) then (5,) then (7,) then (last,)
    and filler hits on page 7. After (7,) the cache is {1, 2, 5, 7}: ascending evicts 1,
    descending evicts 2."""
    stream: sim.PageSets = [(9,)] * 64
    stream += [(1, 2), (5,), (7,), (last,)]
    stream += [(7,)] * 60
    return stream


def capacity_misses(counts: dict[str, int]) -> int:
    return counts["misses_warm"] - counts["first_touch_warm"]


def test_both_tie_rules_on_a_hand_trace() -> None:
    for last, asc_misses, desc_misses in ((1, 1, 0), (2, 0, 1)):
        stream = tie_stream(last)
        stats = sim.stream_stats(stream)
        asc = sim.cache_counts(stream, 3, stats)
        desc = sim.cache_counts(stream, 3, stats, descending=True)
        assert capacity_misses(asc) == asc_misses, last
        assert capacity_misses(desc) == desc_misses, last
        # first-touch misses depend on neither the tie rule nor C
        assert asc["first_touch_warm"] == desc["first_touch_warm"] == 4  # pages 1, 2, 5, 7
        assert asc["first_touch_all"] == desc["first_touch_all"] == 5  # plus page 9


def test_per_context_quantiles_count_only_counted_contexts() -> None:
    stream = tie_stream(1)
    counts = sim.lru_pass(stream, 3)
    assert counts["ctx_q"] == [1] * 7  # one counted context holding one capacity miss


def test_eviction_never_removes_a_page_of_the_current_query() -> None:
    stream: sim.PageSets = [(1, 2, 3, 4, 5, 6, 7, 8)] * 64 + [(9, 10, 11, 12, 13, 14, 15, 16)] * 64
    out = sim.lru_pass(stream, 8)  # C = 8 and every query needs 8 pages
    assert out["misses_all"] == 16 and out["first_touch_all"] == 16


def test_cache_capacity_check_fires_on_a_corrupted_simulator() -> None:
    stream = tie_stream(1)
    assert sim.lru_pass(stream, 3)["misses_all"] > 0  # healthy
    with pytest.raises(core.InvariantError, match="above C"):
        sim.lru_pass(stream, 3, evict_extra=2)  # a simulator that evicts too little


def test_shortcut_equals_the_full_pass_when_everything_fits() -> None:
    generator = random.Random(2)
    stream: sim.PageSets = [
        tuple(sorted(generator.sample(range(6), generator.randrange(1, 4)))) for _ in range(128)
    ]
    stats = sim.stream_stats(stream)
    assert stats["distinct_stream"] <= 8
    full = sim.lru_pass(stream, 8)
    short = sim.cache_counts(stream, 8, stats)
    assert {k: v for k, v in full.items() if k != "ctx_q"} == {
        k: v for k, v in short.items() if k != "ctx_q"
    }
    assert full["ctx_q"] == short["ctx_q"]


@pytest.mark.parametrize("rows", [1, 2, 8, 32])
def test_equal_to_p7a_on_the_configurations_p7a_ran(rows: int) -> None:
    """Direct cross-check with P7-A's simulator (test only; no key-read path is called)."""
    selected, _ = synthetic_trace("fixed_tree", 61)
    counts = a_core.selection_counts(selected)
    positions = a_core.layout_freq(counts)
    pos = torch.tensor(positions)
    mine = sim.page_sets(pos, rows, selected)
    assert mine == a_sim.page_sets(positions, rows, selected)
    stats = sim.stream_stats(mine)
    for cap in core.CS:
        theirs = a_sim.lru_pass(mine, cap)
        ours = sim.cache_counts(mine, cap, stats)
        assert [ours[k] for k in sim.COUNT_KEYS] == theirs
        theirs_desc = a_sim.lru_pass(mine, cap, descending=True)
        ours_desc = sim.cache_counts(mine, cap, stats, descending=True)
        assert [ours_desc[k] for k in sim.COUNT_KEYS] == theirs_desc


def test_group_invariants_fire_when_violated() -> None:
    stream = tie_stream(1)
    group = sim.simulate_group(stream, (3, 8), (3,), "t")
    assert (
        group["by_c"]["3"]["asc"]["first_touch_warm"]
        == group["by_c"]["3"]["desc"]["first_touch_warm"]
    )
    stats = group["stats"]
    by_c = {int(c): copy.deepcopy(v) for c, v in group["by_c"].items()}
    by_c[8]["asc"]["first_touch_all"] += 1  # first touches must not depend on C
    with pytest.raises(core.InvariantError, match="first-touch"):
        sim.check_group(stats, by_c, "t")
    by_c = {int(c): copy.deepcopy(v) for c, v in group["by_c"].items()}
    by_c[3]["desc"]["misses_warm"] = stats["pages_sum"] + 1  # misses cannot exceed touches
    with pytest.raises(core.InvariantError, match="exceed"):
        sim.check_group(stats, by_c, "t")
    by_c = {int(c): copy.deepcopy(v) for c, v in group["by_c"].items()}
    by_c[8]["asc"]["misses_warm"] += 5  # capacity misses must not grow with C
    by_c[8]["asc"]["misses_all"] += 5
    with pytest.raises(core.InvariantError, match="grew"):
        sim.check_group(stats, by_c, "t")


def test_this_module_has_no_key_read_path_and_does_not_import_p7a_simulator() -> None:
    source = inspect.getsource(sim)
    assert "p7a_sim" not in source
    for banned in ("key_page_sets", "tree_key_reads", "flat_key_analytic", "key_rows_per_page"):
        assert banned not in source


# --- the plan (sections 6 and 11)
@pytest.mark.parametrize("kind", ["flat", "fixed_tree"])
def test_plan_covers_the_registered_configuration_set(kind: str) -> None:
    groups = sim.plan(kind)
    by_key = {(g.layout, g.stream, g.rows): g for g in groups}
    assert len(by_key) == len(groups)
    # the actual stream on every layout at every R and C (ascending)
    for layout in core.all_layouts(kind):
        for rows in core.RS:
            assert by_key[(layout, "actual", rows)].asc == core.CS
    # order-shuffled stream and the three nulls on L-FREQ, L-COAX and (trees) L-BCOAX
    nulls = [core.L_FREQ, core.L_COAX] + ([core.L_BCOAX] if kind != "flat" else [])
    for layout in nulls:
        for stream in (core.STREAM_ORDER, *core.STREAMS_NULL):
            for rows in core.RS:
                assert by_key[(layout, stream, rows)].asc == core.CS
    # the five partition layouts: three nulls at the two criterion settings, both tie rules
    for layout in core.L_PCOAX:
        for stream in core.STREAMS_NULL:
            for rows, cap in core.CRITERION_SETTINGS:
                g = by_key[(layout, stream, rows)]
                assert cap in g.asc and cap in g.desc
            assert (layout, stream, 4) not in by_key  # nothing outside the two settings
    # descending rule at the two criterion settings for every layout that enters a criterion
    for layout in sim.desc_actual_layouts(kind):
        for rows, cap in core.CRITERION_SETTINGS:
            assert cap in by_key[(layout, "actual", rows)].desc
    # nothing is simulated for layouts that need no run
    assert (core.L_NCOAX, core.STREAMS_NULL[0], 2) not in by_key
    assert (core.L_BFREQ, core.STREAM_ORDER, 2) not in by_key


def test_plan_sizes_match_the_registered_layout_counts() -> None:
    assert len([n for n in core.coaccess_layouts("flat")]) == 9  # 54 builds over 6 R
    assert len([n for n in core.coaccess_layouts("fixed_tree")]) == 12  # 72 builds
    assert sim.plan_size("fixed_tree")["descending_runs"] > sim.plan_size("flat")["descending_runs"]


# --- one full small checkpoint
@pytest.fixture(scope="module")
def small_checkpoint() -> dict:  # type: ignore[type-arg]
    kind, label = "fixed_tree", "b101-o301-fixed_tree-s501"
    pair, _ = core.parse_label(label)
    index = core.cell_index(pair, kind)
    ev, ev_br = synthetic_trace(kind, 71, queries=1024)
    cal, cal_br = synthetic_trace(kind, 72, queries=1024)
    built, _ = L.build_layouts(L.CalibrationTrace.declared(cal, cal_br, kind, label))
    orders = {b.key(): b.order for b in built}
    counts = a_core.selection_counts(ev)
    nulls, info = core.null_streams(counts, core.STREAM_A_NULL_SEEDS, index)
    trace = sim.EvaluationTrace(ev, ev_br, kind, label, "A")
    record = sim.simulate_checkpoint(
        trace=trace,
        layouts=sim.LayoutSet(orders),
        null_selected=dict(zip(core.STREAMS_NULL, nulls, strict=True)),
    )
    return {
        "record": record,
        "ev": ev,
        "cal": cal,
        "index": index,
        "kind": kind,
        "orders": orders,
        "nulls": nulls,
        "info": info,
    }


def test_full_checkpoint_record_is_complete_and_consistent(small_checkpoint: dict) -> None:  # type: ignore[type-arg]
    record = small_checkpoint["record"]
    assert record["complete"] and record["queries"] == 1024
    assert record["evaluation_counts"]["unique_selected_slots"] > 0
    groups = sim.plan("fixed_tree")
    for g in groups:
        entry = record["streams"][g.stream][core.layout_key(g.layout, g.rows)]
        assert sorted(int(c) for c in entry["by_c"]) == sorted(set(g.asc) | set(g.desc))
        for cap in g.asc:
            assert "asc" in entry["by_c"][str(cap)]
        for cap in g.desc:
            assert "desc" in entry["by_c"][str(cap)]
    # at R = 1 the quantities of section 4 are identical across layouts on the actual stream
    rows = {
        name: record["streams"]["actual"][core.layout_key(name, 1)]
        for name in ("L-ID", "L-FREQ", "L-BFREQ", "L-COAX", "L-BCOAX", "L-PCOAX-1", "L-NCOAX")
    }
    reference = rows["L-ID"]
    for name, entry in rows.items():
        assert entry["stats"] == reference["stats"], name
        for key in ("first_touch_all", "first_touch_warm"):
            assert entry["by_c"]["8"]["asc"][key] == reference["by_c"]["8"]["asc"][key]
        assert (
            entry["by_c"]["8"]["asc"]["misses_warm"] == reference["by_c"]["8"]["asc"]["misses_warm"]
        )


def test_reference_reproduction_passes_and_a_perturbed_record_stops(small_checkpoint: dict) -> None:  # type: ignore[type-arg]
    c = small_checkpoint
    reference = p7b_synth.reference_record(c["kind"], c["index"], c["ev"], c["cal"])
    report = sim.check_reproduction(c["record"], reference)
    assert report["all_equal"] and report["configurations_compared"] > 100
    # the reference was produced from P7-A's own layouts: perturb one miss count
    broken = copy.deepcopy(reference)
    broken["streams"]["freq_matched_2"]["L-FREQ|R2"]["by_c"]["32"]["misses_warm"] += 1
    with pytest.raises(core.StopError, match="reproduction failed"):
        sim.check_reproduction(c["record"], broken)
    broken = copy.deepcopy(reference)
    broken["streams"]["actual"]["L-RAND-91102|R8"]["stats"]["pages_sum"] += 1
    with pytest.raises(core.StopError, match="pages_sum"):
        sim.check_reproduction(c["record"], broken)


def test_checkpoint_callback_runs_after_the_layouts_p7a_also_ran(small_checkpoint: dict) -> None:  # type: ignore[type-arg]
    c = small_checkpoint
    seen: list[set[str]] = []

    def at_point(record: dict) -> None:  # type: ignore[type-arg]
        seen.append({k.split("|")[0] for g in record["streams"].values() for k in g})

    sim.simulate_checkpoint(
        trace=sim.EvaluationTrace(c["ev"], None, "flat", "b101-o301-flat-s501", "A"),
        layouts=sim.LayoutSet(
            {k: v for k, v in c["orders"].items() if "BFREQ" not in k and "BCOAX" not in k}
        ),
        null_selected=dict(zip(core.STREAMS_NULL, c["nulls"], strict=True)),
        checkpoint=at_point,
    )
    (names,) = seen
    assert names == set(core.r_independent_layouts("flat"))  # only P7-A's layouts so far


def test_deadline_preserves_a_partial_record(small_checkpoint: dict) -> None:  # type: ignore[type-arg]
    import time

    c = small_checkpoint
    with pytest.raises(sim.CapExceeded) as raised:
        sim.simulate_checkpoint(
            trace=sim.EvaluationTrace(c["ev"], None, c["kind"], "b101-o301-fixed_tree-s501", "A"),
            layouts=sim.LayoutSet(c["orders"]),
            null_selected=dict(zip(core.STREAMS_NULL, c["nulls"], strict=True)),
            deadline=time.monotonic() - 1.0,
        )
    assert raised.value.partial["complete"] is False  # type: ignore[attr-defined]


def test_null_streams_are_count_preserving_and_use_the_registered_seeds(
    small_checkpoint: dict,  # type: ignore[type-arg]
) -> None:
    c = small_checkpoint
    counts = a_core.selection_counts(c["ev"])
    for stream, info, seed in zip(c["nulls"], c["info"], core.STREAM_A_NULL_SEEDS, strict=True):
        assert a_core.selection_counts(stream) == counts
        assert info["generator_seed"] == seed * 1000 + c["index"]
    assert core.CAL_NULL_SEEDS == (91311, 91312, 91313)
    assert core.STREAM_B_NULL_SEEDS == (91321, 91322, 91323)


def test_page_sets_sorted_distinct_and_independent_of_row_order() -> None:
    selected, _ = synthetic_trace("flat", 9, queries=64)
    order = list(range(core.SLOTS))
    random.Random(1).shuffle(order)
    queries = sim.page_sets(sim.positions_tensor(order), 4, selected)
    assert all(list(q) == sorted(set(q)) for q in queries)
    # moving rows around inside a page changes no page set
    swapped = list(order)
    for start in range(0, core.SLOTS, 4):
        swapped[start], swapped[start + 1] = swapped[start + 1], swapped[start]
    assert sim.page_sets(sim.positions_tensor(swapped), 4, selected) == queries


def test_whole_stream_capacity_miss_monotonicity_is_checked_as_in_p7a() -> None:
    """Audit m10: capacity misses over the whole stream (warm-up included) must not grow with C
    either, even when the counted half is unchanged."""
    group = sim.simulate_group(tie_stream(1), (3, 8), (), "t")
    by_c = {int(c): copy.deepcopy(v) for c, v in group["by_c"].items()}
    sim.check_group(group["stats"], by_c, "t")  # healthy
    by_c[8]["asc"]["misses_all"] += 20  # only the whole-stream count changes
    with pytest.raises(core.InvariantError, match="grew"):
        sim.check_group(group["stats"], by_c, "t")


def test_r1_invariants_hold_on_a_real_record_and_fire_when_a_layout_differs(
    small_checkpoint: dict,  # type: ignore[type-arg]
) -> None:
    record = small_checkpoint["record"]
    report = sim.check_r1_invariants(record)
    assert report["all_identical"] and report["r1_groups_compared"] == 18 + 4 + 3 * 4
    for field, tweak in (
        ("stats", lambda g: g["stats"]["hist"].__setitem__(0, g["stats"]["hist"][0] + 1)),
        ("first touch", lambda g: g["by_c"]["8"]["asc"].update(first_touch_warm=0)),
        ("capacity misses at C = 8", lambda g: g["by_c"]["8"]["asc"].update(misses_warm=10**6)),
    ):
        broken = copy.deepcopy(record)
        tweak(broken["streams"]["actual"]["L-COAX|R1"])
        with pytest.raises(core.InvariantError, match=r"R = 1 invariant violated.*actual"):
            sim.check_r1_invariants(broken)
        broken = copy.deepcopy(record)  # a null stream is checked too
        tweak(broken["streams"]["null_2"]["L-FREQ|R1"])
        with pytest.raises(core.InvariantError, match="null_2"):
            sim.check_r1_invariants(broken)


def test_r1_invariant_does_not_constrain_larger_pages_or_larger_cache(
    small_checkpoint: dict,  # type: ignore[type-arg]
) -> None:
    broken = copy.deepcopy(small_checkpoint["record"])
    broken["streams"]["actual"]["L-COAX|R2"]["by_c"]["32"]["asc"]["misses_warm"] += 3
    broken["streams"]["actual"]["L-COAX|R1"]["by_c"]["16"]["asc"]["misses_warm"] += 3  # C > 8
    assert sim.check_r1_invariants(broken)["all_identical"]


def test_a_partial_record_is_offered_after_every_finished_layout(
    small_checkpoint: dict,  # type: ignore[type-arg]
) -> None:
    c = small_checkpoint
    calls: list[dict] = []  # type: ignore[type-arg]

    def progress(info: dict) -> None:  # type: ignore[type-arg]
        calls.append(
            {
                "layout": info["finished_layout"],
                "complete": info["complete"],
                "layouts_in_record": {
                    k.split("|")[0] for g in info["record"]["streams"].values() for k in g
                },
            }
        )

    sim.simulate_checkpoint(
        trace=sim.EvaluationTrace(c["ev"], None, "flat", "b101-o301-flat-s501", "A"),
        layouts=sim.LayoutSet(
            {k: v for k, v in c["orders"].items() if "BFREQ" not in k and "BCOAX" not in k}
        ),
        null_selected=dict(zip(core.STREAMS_NULL, c["nulls"], strict=True)),
        progress=progress,
    )
    layouts = [x["layout"] for x in calls]
    assert len(calls) == len(core.all_layouts("flat")) and layouts[-1] == calls[-1]["layout"]
    assert [x["complete"] for x in calls] == [False] * (len(calls) - 1) + [True]
    assert layouts[0] == core.L_ID and layouts[:2] == [core.L_ID, core.L_RANDS[0]]
    assert calls[0]["layouts_in_record"] == {core.L_ID}  # earlier layouts only: a real partial
