"""Synthetic tests for the P7-B analysis (ADR-0014 sections 2, 7, 7a, 9): E, rho, the OLS-adjusted
ratio, non-degeneracy, the class table, tie-rule dependence, PART_K, the outcome table, stream
pairing, decision classes and the recommendation table. Records are built from hand-chosen
integer miss counts so every expected value is exact."""

import itertools
import math
from collections.abc import Callable
from fractions import Fraction
from typing import Any

import pytest

from arborlm import p7b_analysis as an
from arborlm import p7b_core as core

Fn = Callable[[str, tuple[int, int, int], str, str, int, int, str], int | None]
PAIRS = sorted({p for p, _ in core.registered_checkpoints()})


def parent_index(pair: tuple[int, int, int]) -> int:
    return PAIRS.index(pair) // 3


def entry(capacity: int) -> dict[str, Any]:
    return {
        "misses_all": capacity + 200,
        "first_touch_all": 200,
        "misses_warm": capacity + 100,
        "first_touch_warm": 100,
        "ctx_q": [0] * 7,
    }


def build(
    fn: Fn, entropy: Callable[[tuple[int, int, int], str], float] | None = None
) -> dict[str, Any]:
    """Per-checkpoint worker results for all 81 checkpoints. ``fn`` returns the warm capacity-miss
    COUNT (of 16,384 counted queries) or None for 'not simulated'."""
    records: dict[str, Any] = {}
    for pair, kind in core.registered_checkpoints():
        label = core.cell_label(pair, kind)
        streams: dict[str, Any] = {s: {} for s in core.STREAMS_ALL}
        for stream in core.STREAMS_ALL:
            for layout in core.all_layouts(kind):
                for rows, cap in core.CRITERION_SETTINGS:
                    for tie in core.TIES:
                        value = fn(kind, pair, stream, layout, rows, cap, tie)
                        if value is None:
                            continue
                        group = streams[stream].setdefault(
                            core.layout_key(layout, rows),
                            {
                                "stats": {
                                    "hist": [0, 0, 0, 0, 0, 0, 0, 32768],
                                    "pages_sum": 8 * 32768,
                                    "distinct_stream": 500,
                                    "distinct_first_half": 400,
                                },
                                "by_c": {},
                            },
                        )
                        group["by_c"].setdefault(str(cap), {})[tie] = entry(value)
        x = entropy(pair, kind) if entropy else 4.0 + 0.05 * PAIRS.index(pair)
        records[label] = {
            "outcome": "completed",
            "label": label,
            "record": {
                "complete": True,
                "kind": kind,
                "label": label,
                "queries": 32768,
                "evaluation_counts": {
                    "unique_selected_slots": 300,
                    "entropy_nats": x,
                    "effective_slots": math.exp(x),
                    "counts_sha256": "",
                },
                "streams": streams,
            },
        }
    return records


NULL = 10_000  # null denominators: 0.61 per query, far above every floor


def scenario(
    *,
    tree_bcoax: Callable[[tuple[int, int, int], int, int, str], int] = lambda p, r, c, t: 6400,
    tree_coax: int = 8000,
    flat_coax: int = 8000,
    flat_null: Callable[[int, int, str], int] = lambda r, c, t: NULL,
    tree_null: Callable[[int, int, str], int] = lambda r, c, t: NULL,
    partition_actual: Callable[[str, tuple[int, int, int]], int] = lambda n, p: 8000,
    partition_null: Callable[[str, tuple[int, int, int]], int] = lambda n, p: NULL,
    bcoax_null: Callable[[tuple[int, int, int], int, int, str], int] = lambda p, r, c, t: NULL,
) -> Fn:
    def fn(
        kind: str,
        pair: tuple[int, int, int],
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str,
    ) -> int | None:
        tree = kind != "flat"
        null = stream in core.STREAMS_NULL
        if stream not in ("actual", *core.STREAMS_NULL):
            return None
        if layout == core.L_FREQ:
            if null:
                return tree_null(rows, cap, tie) if tree else flat_null(rows, cap, tie)
            return 9000
        if layout == core.L_COAX:
            if null:
                return tree_null(rows, cap, tie) if tree else flat_null(rows, cap, tie)
            return tree_coax if tree else flat_coax
        if layout == core.L_BCOAX:
            if null:
                return bcoax_null(pair, rows, cap, tie)
            return tree_bcoax(pair, rows, cap, tie)
        if layout in core.L_PCOAX:
            return partition_null(layout, pair) if null else partition_actual(layout, pair)
        return None

    return fn


def stream_of(fn: Fn, **kw: Any) -> an.Stream:
    return an.Stream("A", build(fn, **kw))


F = Fraction


# --- classification table
@pytest.mark.parametrize(
    ("rho", "rho_adj", "tree", "flat", "expected"),
    [
        (F(4, 5), F(4, 5), True, False, an.TREE_BETTER),  # exactly 0.80 passes (<=)
        (F(4, 5) + F(1, 1000), F(4, 5), True, False, an.INTERMEDIATE),
        (F(4, 5), F(4, 5) + F(1, 1000), True, False, an.INTERMEDIATE),  # both must hold
        (F(4, 5), F(4, 5), False, False, an.INTERMEDIATE),  # counts must favour the tree
        (F(1, 2), F(1, 2), True, True, an.TREE_BETTER),  # registered order
        (F(5, 4), F(5, 4), False, True, an.FLAT_BETTER),  # exactly 1.25 passes (>=)
        (F(5, 4) - F(1, 1000), F(5, 4), False, True, an.INTERMEDIATE),
        (F(5, 4), F(5, 4), False, False, an.INTERMEDIATE),
        (F(9, 10), F(9, 10), False, False, an.WITHIN),  # exactly 0.90 passes
        (F(11, 10), F(11, 10), False, False, an.WITHIN),  # exactly 1.10 passes
        (F(9, 10) - F(1, 1000), F(1), False, False, an.INTERMEDIATE),
        (F(11, 10) + F(1, 1000), F(1), False, False, an.INTERMEDIATE),
        (F(1), F(11, 10) + F(1, 1000), False, False, an.INTERMEDIATE),
        (F(1), None, False, False, an.INTERMEDIATE),  # undefined adjusted ratio
        (F(1, 2), None, True, False, an.INTERMEDIATE),
    ],
)
def test_class_table_boundaries(
    rho: Fraction, rho_adj: Fraction | None, tree: bool, flat: bool, expected: str
) -> None:
    assert an.classify(rho, rho_adj, tree, flat) == expected


def lower_values(
    lower: set[int], low: int = 5000, equal: int = 8000
) -> tuple[an.Values, an.Values]:
    reference = {p: F(equal) for p in PAIRS}
    candidate = {p: F(low) if i in lower else F(equal) for i, p in enumerate(PAIRS)}
    return reference, candidate


def test_count_rule_22_of_27_and_8_of_9_with_ties() -> None:
    spread = {0, 3, 6, 9, 12, 15, 18, 21, 24}  # one pair in each parent
    assert len(spread) == 9
    five_tied = set(range(27)) - {1, 5, 10, 14, 20}  # 22 strictly lower, ties elsewhere
    reference, candidate = lower_values(five_tied)
    counts = an.count_rule(reference, candidate)
    assert counts["cells_strictly_lower"] == 22 and counts["cells_tied"] == 5
    assert counts["holds"] and counts["parents_strictly_lower"] == 9
    reference, candidate = lower_values(set(range(27)) - {1, 5, 10, 14, 20, 25})
    assert an.count_rule(reference, candidate)["cells_strictly_lower"] == 21
    assert not an.count_rule(reference, candidate)["holds"]
    # 8 of 9 parents: one whole parent tied -> 24 cells, 8 parents
    reference, candidate = lower_values(set(range(27)) - {0, 1, 2})
    counts = an.count_rule(reference, candidate)
    assert (counts["cells_strictly_lower"], counts["parents_strictly_lower"]) == (24, 8)
    assert counts["holds"]
    # 7 parents: two parents whose mean is not lower although most of their cells are
    reference = {p: F(8000) for p in PAIRS}
    candidate = {p: F(3000) for p in PAIRS}
    for i in (2, 5):  # the third seed of two parents is far above
        candidate[PAIRS[i]] = F(30000)
    counts = an.count_rule(reference, candidate)
    assert counts["cells_strictly_lower"] == 25 and counts["parents_strictly_lower"] == 7
    assert not counts["holds"]


def test_ols_adjusted_ratio_on_hand_calculated_numbers() -> None:
    # E = 4 - 0.5 x + 1 [tree], exact: flat x = 1..4, tree x = 1.5..4.5
    xf = {PAIRS[i]: float(i + 1) for i in range(4)}
    xt = {PAIRS[i]: float(i + 1) + 0.5 for i in range(4)}
    ef = {p: F(4) - F(1, 2) * F(x) for p, x in xf.items()}
    et = {p: F(4) - F(1, 2) * F(x) + 1 for p, x in xt.items()}
    fit = an.ols_adjusted(ef, et, xf, xt)
    assert (fit["a_exact"], fit["b_exact"], fit["d_exact"]) == ("4/1", "-1/2", "1/1")
    # xbar = 2.75; a + b xbar = 2.625; rho_adj = 3.625 / 2.625 = 29/21
    assert fit["rho_adj_exact"] == "29/21" and fit["defined"]


def test_ols_adjusted_ratio_is_undefined_when_the_level_is_not_positive() -> None:
    xf = {PAIRS[i]: 0.125 + 0.015625 * i for i in range(4)}
    xt = {PAIRS[i]: 3.0 + 0.125 * i for i in range(4)}
    ef = {p: F(1) - F(x) for p, x in xf.items()}  # a = 1, b = -1
    et = {p: F(1) - F(x) + 3 for p, x in xt.items()}  # d = 3, all E positive
    assert min([*ef.values(), *et.values()]) > 0
    fit = an.ols_adjusted(ef, et, xf, xt)
    assert fit["a_exact"] == "1/1" and fit["b_exact"] == "-1/1" and fit["d_exact"] == "3/1"
    assert fit["defined"] is False and fit["rho_adj"] is None
    assert fit["level_at_mean_utilization"] < 0
    assert an.classify(F(1, 100), fit.get("_rho_adj"), True, False) == an.INTERMEDIATE
    # a singular design (identical x everywhere, tree indicator collinear with the constant)
    same = {p: 5.0 for p in PAIRS[:4]}
    assert an.ols_adjusted(ef, et, same, same)["defined"] is False


# --- comparisons at the registered settings
def hb(stream: an.Stream, rows: int = 2, cap: int = 32) -> dict[str, Any]:
    return an.comparison(stream, "fixed_tree", rows, cap, core.L_BCOAX, core.L_COAX)


def test_e_and_exploited_structure_arithmetic() -> None:
    stream = stream_of(scenario())
    pair = PAIRS[0]
    # m = 6400 / 16384 and the null mean is 10000 / 16384, so E = 0.64, S = 0.64
    num = stream.m(pair, "fixed_tree", "actual", core.L_BCOAX, 2, 32, "asc")
    assert num == F(6400, 16384)
    assert stream.null_mean(pair, "fixed_tree", core.L_FREQ, 2, 32, "asc") == F(10000, 16384)
    _, _, e = an.e_values(stream, "fixed_tree", core.L_BCOAX, 2, 32, "asc", "actual")
    assert e is not None and e[pair] == F(64, 100)
    s = an.exploited(stream, "fixed_tree", core.L_BCOAX, 2, 32, "asc")
    assert s is not None and s[pair] == F(64, 100)
    # flat coax: E = 0.8
    _, _, ef = an.e_values(stream, "flat", core.L_COAX, 2, 32, "asc", "actual")
    assert ef is not None and ef[pair] == F(8, 10)


def test_e_uses_the_mean_of_three_null_replicates() -> None:
    def flat_null(rows: int, cap: int, tie: str) -> int:
        return NULL

    base = scenario(flat_null=flat_null)

    def fn(
        kind: str,
        pair: tuple[int, int, int],
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str,
    ) -> int | None:
        if kind == "flat" and layout == core.L_FREQ and stream == "null_1":
            return 9000
        if kind == "flat" and layout == core.L_FREQ and stream == "null_2":
            return 10000
        if kind == "flat" and layout == core.L_FREQ and stream == "null_3":
            return 11000
        return base(kind, pair, stream, layout, rows, cap, tie)

    stream = stream_of(fn)
    assert stream.null_mean(PAIRS[0], "flat", core.L_FREQ, 2, 32, "asc") == F(10000, 16384)


def test_exact_boundary_ratio_is_tree_materially_better_under_both_tie_rules() -> None:
    result = hb(stream_of(scenario()))
    assert result["class"] == an.TREE_BETTER
    for tie in core.TIES:
        one = result["by_tie"][tie]
        assert one["rho_exact"] == "4/5" and one["rho_adj_exact"] == "4/5"
        assert one["counts_favour_tree"]["cells_strictly_lower"] == 27
    # one count above the boundary and the class is INTERMEDIATE
    above = hb(stream_of(scenario(tree_bcoax=lambda p, r, c, t: 6401)))
    assert above["class"] == an.INTERMEDIATE


@pytest.mark.parametrize(
    ("tree_count", "expected"),
    [
        (7200, an.WITHIN),  # rho = 0.90
        (7199, an.INTERMEDIATE),
        (8800, an.WITHIN),  # rho = 1.10
        (8801, an.INTERMEDIATE),
        (10000, an.FLAT_BETTER),  # rho = 1.25, flat strictly lower in every pair
        (9999, an.INTERMEDIATE),
    ],
)
def test_rho_boundaries_through_the_full_comparison(tree_count: int, expected: str) -> None:
    result = hb(stream_of(scenario(tree_bcoax=lambda p, r, c, t, v=tree_count: v)))
    assert result["class"] == expected


def test_counts_decide_when_the_ratio_would_qualify() -> None:
    def bcoax(low: set[int]) -> Callable[[tuple[int, int, int], int, int, str], int]:
        return lambda p, r, c, t: 5000 if PAIRS.index(p) in low else 8000

    twenty_two = set(range(27)) - {1, 5, 10, 14, 20}
    ok = hb(stream_of(scenario(tree_bcoax=bcoax(twenty_two))))
    assert ok["class"] == an.TREE_BETTER
    twenty_one = set(range(27)) - {1, 5, 10, 14, 20, 25}
    assert hb(stream_of(scenario(tree_bcoax=bcoax(twenty_one))))["class"] == an.INTERMEDIATE


def test_tie_rule_dependent_is_recorded_when_the_two_rules_disagree() -> None:
    def bcoax(p: tuple[int, int, int], r: int, c: int, t: str) -> int:
        return 6400 if t == "asc" else 7600  # TREE BETTER under asc, WITHIN under desc

    result = hb(stream_of(scenario(tree_bcoax=bcoax)))
    assert result["by_tie"]["asc"]["class"] == an.TREE_BETTER
    assert result["by_tie"]["desc"]["class"] == an.WITHIN
    assert result["class"] == an.TIE_DEPENDENT


@pytest.mark.parametrize(
    "case",
    ["flat_mean", "tree_mean", "each", "numerator_tree", "numerator_flat", "desc_only"],
)
def test_non_degeneracy_floors_under_both_tie_rules(case: str) -> None:
    kwargs: dict[str, Any] = {}
    if case == "flat_mean":
        kwargs["flat_null"] = lambda r, c, t: 800  # 0.0488 < 0.05
    if case == "tree_mean":
        kwargs["tree_null"] = lambda r, c, t: 160  # 0.00977 < 0.01
        kwargs["bcoax_null"] = lambda p, r, c, t: 160
    if case == "each":
        kwargs["tree_null"] = lambda r, c, t: NULL
        # every flat/tree null mean is high, but one tree checkpoint has a null of 80/16384
        kwargs["bcoax_null"] = lambda p, r, c, t: NULL
    if case == "numerator_tree":
        kwargs["tree_bcoax"] = lambda p, r, c, t: 100  # mean numerator 0.0061 < 0.01
    if case == "numerator_flat":
        kwargs["flat_coax"] = 100
    if case == "desc_only":
        kwargs["flat_null"] = lambda r, c, t: 800 if t == "desc" else NULL
    stream = stream_of(scenario(**kwargs))
    if case == "each":
        # one tree checkpoint's L-FREQ null below 0.005 (80 counts) while every mean stays high
        for label, rec in stream.records.items():
            if label == core.cell_label(PAIRS[0], "fixed_tree"):
                for stream_name in core.STREAMS_NULL:
                    for tie in core.TIES:
                        rec["record"]["streams"][stream_name][core.layout_key(core.L_FREQ, 2)][
                            "by_c"
                        ]["32"][tie] = entry(80)
    result = hb(stream)
    assert result["class"] == an.DEGENERATE, case


def test_incomplete_streams_do_not_raise_and_list_the_missing_checkpoints() -> None:
    records = build(scenario())
    del records[core.cell_label(PAIRS[4], "learned_tree")]
    records[core.cell_label(PAIRS[7], "flat")]["record"]["complete"] = False
    analysis = an.analyze_streams({"A": records, "B": {}})
    assert analysis["streams"]["A"]["status"] == an.INCOMPLETE
    assert sorted(analysis["streams"]["A"]["missing_or_failed"]) == sorted(
        [core.cell_label(PAIRS[4], "learned_tree"), core.cell_label(PAIRS[7], "flat")]
    )
    assert len(analysis["streams"]["B"]["missing_or_failed"]) == 81
    for kind in core.TREE_KINDS:
        assert analysis["per_stream"]["A"]["tree_kinds"][kind]["outcome"] == an.INCOMPLETE
        assert analysis["combined"]["tree_kinds"][kind]["decision_class"] == an.INCOMPLETE
    assert analysis["combined"]["recommendation"]["row"] is None
    empty = an.analyze_streams({})  # nothing at all: still no exception
    assert empty["streams"]["A"]["status"] == an.INCOMPLETE


# --- PART_K
def part(stream: an.Stream, rows: int = 2, cap: int = 32) -> dict[str, Any]:
    return an.part_k(stream, "fixed_tree", rows, cap)


def test_part_k_real_branches_better_when_every_clause_holds() -> None:
    result = part(stream_of(scenario(partition_actual=lambda n, p: 8000)))
    assert result["label"] == an.REAL_BETTER
    for tie in core.TIES:
        assert result["by_tie"][tie]["aggregate"]["ratio_exact"] == "4/5"  # 0.64 / 0.8
    assert result["by_tie"]["asc"]["spread"]["cells_S_B_lower_than_all_five"] == 27


def test_part_k_aggregate_holds_but_one_partition_alone_fails() -> None:
    """S_B = 0.64. Partition 3 has S = 0.64 (ratio 1.0); the other four have S = 1.28, so the
    mean S_P = 1.152 and S_B <= 0.8 S_P holds in aggregate, but not against partition 3."""

    def actual(name: str, pair: tuple[int, int, int]) -> int:
        return 6400 if name == "L-PCOAX-3" else 12800

    result = part(stream_of(scenario(partition_actual=actual)))
    asc = result["by_tie"]["asc"]
    assert asc["aggregate"]["holds"] is True
    clauses = {e["layout"]: e["clause"] for e in asc["every_partition"]}
    assert clauses["L-PCOAX-3"] is False and clauses["L-PCOAX-1"] is True
    assert result["label"] == an.NOT_BETTER


def test_part_k_cell_and_parent_counts_are_required() -> None:
    # S_B lower than S_P in only 21 cells although the means qualify
    def actual(name: str, pair: tuple[int, int, int]) -> int:
        return 3000 if PAIRS.index(pair) in {1, 5, 10, 14, 20, 25} else 20000

    assert part(stream_of(scenario(partition_actual=actual)))["label"] == an.NOT_BETTER


def test_part_k_degenerate_when_a_null_denominator_is_too_small() -> None:
    assert (
        part(stream_of(scenario(partition_null=lambda n, p: 80 if n == "L-PCOAX-2" else NULL)))[
            "label"
        ]
        == an.DEGENERATE
    )
    assert (
        part(stream_of(scenario(bcoax_null=lambda p, r, c, t: 150)))["label"] == an.DEGENERATE
    )  # mean below 0.01


def test_part_k_flags_tie_rule_dependence_but_still_reads_not_better() -> None:
    def actual(name: str, pair: tuple[int, int, int]) -> int:
        return 8000

    def bcoax(p: tuple[int, int, int], r: int, c: int, t: str) -> int:
        return 6400 if t == "asc" else 9000  # fails under desc

    result = part(stream_of(scenario(tree_bcoax=bcoax, partition_actual=actual)))
    assert result["label"] == an.NOT_BETTER and result["tie_rule_dependent"] is True


# --- the outcome table, enumerated
HB_CLASSES = (
    an.TREE_BETTER,
    an.FLAT_BETTER,
    an.WITHIN,
    an.INTERMEDIATE,
    an.TIE_DEPENDENT,
    an.DEGENERATE,
)
PART_LABELS = (an.REAL_BETTER, an.NOT_BETTER, an.DEGENERATE)


def hb_stub(label: str, rho: str = "9/10") -> dict[str, Any]:
    return {"class": label, "by_tie": {"asc": {"rho_exact": rho}}}


def rows_that_apply(hp: str, hc: str, pp: str, pc: str) -> list[int]:
    """The seven rows of the outcome table as mutually exclusive predicates on the classes."""
    hit = []
    if hp == an.DEGENERATE:
        hit.append(1)
    if (
        hp == an.TREE_BETTER
        and hc == an.TREE_BETTER
        and pp == an.REAL_BETTER
        and pc == an.REAL_BETTER
    ):
        hit.append(2)
    if (
        hp == an.TREE_BETTER
        and hc == an.TREE_BETTER
        and not (pp == an.REAL_BETTER and pc == an.REAL_BETTER)
    ):
        hit.append(3)
    if hp == an.TREE_BETTER and hc != an.TREE_BETTER:
        hit.append(4)
    if hp == an.FLAT_BETTER:
        hit.append(5)
    if hp == an.WITHIN:
        hit.append(6)
    if hp in (an.INTERMEDIATE, an.TIE_DEPENDENT):
        hit.append(7)
    return hit


def test_outcome_table_every_combination_has_exactly_one_row() -> None:
    expected = {
        1: an.UNRESOLVED,
        2: an.HIERARCHY,
        3: an.NOT_BRANCH,
        4: an.NOT_ROBUST,
        5: an.FLAT_COAX_BETTER,
        6: an.WITHIN_FLAT,
        7: an.INTERMEDIATE_TREE,
    }
    seen_rows: set[int] = set()
    for hp, hc, pp, pc in itertools.product(HB_CLASSES, HB_CLASSES, PART_LABELS, PART_LABELS):
        rows = rows_that_apply(hp, hc, pp, pc)
        assert len(rows) == 1, (hp, hc, pp, pc, rows)
        label = an.outcome_for(hb_stub(hp), hb_stub(hc), pp, pc)
        assert label == expected[rows[0]], (hp, hc, pp, pc)
        seen_rows.add(rows[0])
    assert seen_rows == set(range(1, 8))


@pytest.mark.parametrize(
    ("rho", "expected"),
    [
        ("9/10", an.INTERMEDIATE_TREE),
        ("99/100", an.INTERMEDIATE_TREE),
        ("1/1", an.INTERMEDIATE_FLAT),  # 'otherwise'
        ("101/100", an.INTERMEDIATE_FLAT),
    ],
)
def test_intermediate_carries_its_direction(rho: str, expected: str) -> None:
    out = an.outcome_for(
        hb_stub(an.INTERMEDIATE, rho), hb_stub(an.WITHIN), an.NOT_BETTER, an.NOT_BETTER
    )
    assert out == expected


def test_incomplete_inputs_give_incomplete_outcome() -> None:
    assert (
        an.outcome_for(hb_stub(an.INCOMPLETE), hb_stub(an.WITHIN), an.NOT_BETTER, an.NOT_BETTER)
        == an.INCOMPLETE
    )


# --- stream pairing, decision classes, recommendation
def test_stream_pairing_every_pair_of_labels_has_exactly_one_description() -> None:
    labels = an.OUTCOME_LABELS
    for a, b in itertools.product(labels, labels):
        rows = []
        if a == b and a != an.UNRESOLVED:
            rows.append(an.REPLICATED)
        if a == b == an.UNRESOLVED:
            rows.append(an.UNRESOLVED_BOTH)
        if (a == an.UNRESOLVED) != (b == an.UNRESOLVED):
            rows.append(an.SINGLE_STREAM)
        if a != b and an.UNRESOLVED not in (a, b):
            rows.append(an.NOT_REPLICATED)
        assert len(rows) == 1, (a, b)
        result = an.stream_pairing(a, b)
        assert result["pairing"] == rows[0]
        if rows[0] == an.REPLICATED:
            assert result["description"] == f"{a}, REPLICATED"
        if rows[0] == an.SINGLE_STREAM:
            other = b if a == an.UNRESOLVED else a
            assert result["description"] == f"{other}, SINGLE-STREAM"
        if rows[0] == an.NOT_REPLICATED:
            assert a in result["description"] and b in result["description"]


def test_decision_classes_are_exhaustive_and_exclusive() -> None:
    labels = an.OUTCOME_LABELS
    counts = {an.CLASS_S: 0, an.CLASS_U: 0, an.CLASS_N: 0, an.CLASS_I: 0}
    for a, b in itertools.product(labels, labels):
        applies = []
        if a == b == an.HIERARCHY:
            applies.append(an.CLASS_S)
        if a == b == an.UNRESOLVED:
            applies.append(an.CLASS_U)
        n_set = (an.WITHIN_FLAT, an.FLAT_COAX_BETTER, an.NOT_BRANCH)
        if a in n_set and b in n_set:
            applies.append(an.CLASS_N)
        if not applies:
            applies.append(an.CLASS_I)
        assert len(applies) == 1, (a, b)
        assert an.decision_class(a, b) == applies[0]
        counts[applies[0]] += 1
    assert all(v > 0 for v in counts.values())
    # the two streams need not give the same N outcome; any INTERMEDIATE / NOT ROBUST is I
    assert an.decision_class(an.WITHIN_FLAT, an.NOT_BRANCH) == an.CLASS_N
    assert an.decision_class(an.INTERMEDIATE_TREE, an.WITHIN_FLAT) == an.CLASS_I
    assert an.decision_class(an.UNRESOLVED, an.WITHIN_FLAT) == an.CLASS_I
    assert an.decision_class(an.NOT_ROBUST, an.NOT_ROBUST) == an.CLASS_I


def test_recommendation_table_is_ordered_and_total() -> None:
    classes = (an.CLASS_S, an.CLASS_U, an.CLASS_N, an.CLASS_I)
    for a, b in itertools.product(classes, classes):
        row = an.recommendation(a, b)["row"]
        if an.CLASS_S in (a, b):
            assert row == 1
        elif (a, b) == (an.CLASS_N, an.CLASS_N):
            assert row == 2
        elif (a, b) == (an.CLASS_U, an.CLASS_U):
            assert row == 3
        else:
            assert row == 4
    assert an.recommendation(an.CLASS_S, an.CLASS_U)["row"] == 1
    assert "Do not scale" in an.recommendation(an.CLASS_N, an.CLASS_N)["recommendation"]
    assert an.recommendation(an.CLASS_N, an.CLASS_U)["row"] == 4
    assert an.recommendation(an.INCOMPLETE, an.CLASS_N)["row"] is None


# --- both streams, end to end on synthetic records
def test_full_analysis_on_two_consistent_streams_reaches_class_s() -> None:
    records = build(scenario())
    analysis = an.analyze_streams({"A": records, "B": build(scenario())})
    for kind in core.TREE_KINDS:
        per = analysis["per_stream"]["A"]["tree_kinds"][kind]
        assert per["HB"] == {"primary": an.TREE_BETTER, "confirmation": an.TREE_BETTER}
        assert per["PART"] == {"primary": an.REAL_BETTER, "confirmation": an.REAL_BETTER}
        assert per["outcome"] == an.HIERARCHY
        combined = analysis["combined"]["tree_kinds"][kind]
        assert combined["decision_class"] == an.CLASS_S
        assert combined["pairing"]["description"] == f"{an.HIERARCHY}, REPLICATED"
    assert analysis["combined"]["recommendation"]["row"] == 1
    # descriptive items are present and well formed
    d = analysis["descriptive"]["A"]
    assert d["ncoax_control"]["band"] == [0.97, 1.03]
    assert any(k.startswith("fixed_tree|L-COAX|R2|C32") for k in d["co_access_gain"])
    assert d["BC_K"]["fixed_tree|R2|C32|asc"]["BC"] == pytest.approx(0.8)
    assert d["BC_K"]["fixed_tree|R2|C32|asc"]["five_partition_counterpart"] == pytest.approx(1.0)
    assert d["utilization"]["flat"]["cells"] == 27
    assert analysis["streams"]["A"]["status"] == "COMPLETE"


def test_ncoax_control_flags_a_layout_that_manufactures_locality() -> None:
    def fn(
        kind: str,
        pair: tuple[int, int, int],
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str,
    ) -> int | None:
        if layout == core.L_NCOAX and stream == "actual":
            return 8000  # 8000 / 9000 = 0.889: outside 0.97-1.03
        return scenario()(kind, pair, stream, layout, rows, cap, tie)

    flagged = an.ncoax_control(stream_of(fn))
    assert flagged["flag_every_coaccess_result"] is True

    def ok(
        kind: str,
        pair: tuple[int, int, int],
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str,
    ) -> int | None:
        if layout == core.L_NCOAX and stream == "actual":
            return 9100  # 1.011
        return scenario()(kind, pair, stream, layout, rows, cap, tie)

    assert an.ncoax_control(stream_of(ok))["flag_every_coaccess_result"] is False


# --- robustness grid (audit m8)
def test_ascending_only_variants_are_labelled_not_run_under_the_descending_rule() -> None:
    base = scenario()

    def fn(
        kind: str,
        pair: tuple[int, int, int],
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str,
    ) -> int | None:
        if layout in (
            core.L_BCOAX8,
            core.L_COAX8,
        ):  # simulated on the actual stream, ascending only
            if stream != "actual" or tie == "desc":
                return None
            return 6400 if layout == core.L_BCOAX8 else 8000
        return base(kind, pair, stream, layout, rows, cap, tie)

    grid = an.robustness_grid(stream_of(fn))
    for kind in core.TREE_KINDS:
        by_cell = {(r["R"], r["C"]): r for r in grid[kind]}
        primary, other = by_cell[core.PRIMARY_SETTING], by_cell[(1, 8)]
        assert primary["HB_A8"]["class"] != an.INCOMPLETE  # was INCOMPLETE: no descending runs
        assert primary["HB_A8"]["status"] != an.INCOMPLETE
        for name in an.ASC_ONLY_VARIANTS:
            assert primary[name]["descending_rule"] == "not run under the descending rule"
            assert "descending_rule" not in other[name]  # non-criterion cells are ascending anyway
        for name in ("HB", "HU"):  # criterion layouts do have descending runs
            assert "descending_rule" not in primary[name]
            assert primary[name]["class"] != an.INCOMPLETE


def test_missing_descending_data_of_a_criterion_layout_is_still_incomplete() -> None:
    def fn(
        kind: str,
        pair: tuple[int, int, int],
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str,
    ) -> int | None:
        if layout == core.L_BCOAX and tie == "desc":
            return None
        return scenario()(kind, pair, stream, layout, rows, cap, tie)

    grid = an.robustness_grid(stream_of(fn))
    primary = {(r["R"], r["C"]): r for r in grid["fixed_tree"]}[core.PRIMARY_SETTING]
    assert primary["HB"]["class"] == an.INCOMPLETE  # genuinely missing data is not relabelled
