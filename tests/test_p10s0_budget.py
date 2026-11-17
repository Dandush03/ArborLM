# ruff: noqa: E501
"""P10S0 budget (ADR-0020 section 10): the rehearsal matrix, rates merged from two rehearsals (the larger is used), projections that include the task start-up time, the headroom rule under reading A with the cuts in
their registered order (the ADR's own arithmetic reproduced), the memory rule with evaluation and pool peaks, and the cap table (one entry per configuration, written by a procedure). Every number is analytical.
Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s0 import budget, core  # noqa: E402

H = 3600.0
CAP16 = 16 * H  # the ADR's worked examples are stated for a 16-hour cap: they pass it explicitly, so no test depends on cap_hours in the real config (the pre-freeze audit's F1)


def holds16(charged: float, projected: list[float]) -> bool:
    return budget.holds(charged, projected, CAP16)


def pre16(*a: float, **k: float) -> budget.PreQ1Decision:
    return budget.pre_q1_decision(*a, cap_seconds=CAP16, **k)


def post16(*a: float, **k: float) -> budget.PostQ1Decision:
    return budget.post_q1_decision(*a, cap_seconds=CAP16, **k)
SLOWEST = {4096: 0.0112, 16384: 0.0195, 65536: 0.0619}


def rates_at(by_slots: dict[int, float], *, evaluation: float = 0.0, overhead: float = 0.0, peak: int = 10**9, candidates: tuple[str, ...] = core.CANDIDATE_ARMS) -> budget.Rates:
    out: budget.Rates = {}
    for item in budget.rehearsal_items(candidates):
        slots = core.CELLTYPES[item[1]].slots
        out[item] = budget.Rate(by_slots[slots], peak, peak, evaluation, overhead, peak, peak)
    return out


def scaled(m: float) -> budget.Rates:
    return rates_at({k: v * m for k, v in SLOWEST.items()})


# --- the matrix ------------------------------------------------------------------------------------------------------------------------------
def test_rehearsal_items_are_the_adr_s() -> None:
    items = budget.rehearsal_items()
    assert len(items) == len(set(items)) == 24
    assert {i for i in items if i[0] == "A2"} == {("A2", ct, ph) for ct in core.CORE_CELLTYPES for ph in ("pre", "post")}
    assert {i for i in items if i[1] == "32K/64K"} == {("A5-D", "32K/64K", "main"), ("A1", "32K/64K", "main"), ("A6", "32K/64K", "main")}
    assert {i[0] for i in items if i[1] == "8K/4K"} == {"A0", "A5-D", "A6"}
    assert {i[0] for i in items if core.is_wx(i[0])} == {"WX-A5-D", "WX-A1"} and not [i for i in items if i[0] in ("A0", "A2") and i[1] == "32K/64K"]
    assert len(budget.rehearsal_items(("A5-D",))) == 21


def test_item_labels_round_trip() -> None:
    for item in budget.rehearsal_items():
        assert budget.parse_item_label(budget.item_label(item)) == item
    with pytest.raises(ValueError):
        budget.parse_item_label("REH-A0-nonsense-main")


# --- rates ---------------------------------------------------------------------------------------------------------------------------------
def test_rates_from_records_include_the_task_start_up_time() -> None:
    item = ("A0", "2K/4K", "main")
    train = [{"arm": "A0", "celltype": "2K/4K", "phase": "main", "label": "L", "seconds_per_update": 0.01, "wall_seconds": 3.0, "peak_rss_bytes": 700, "sampled_rss_bytes": 650}]
    evaluation = [{"label": "L", "evaluation_wall_seconds": 2.0, "peak_rss_bytes": 900}]
    tasks = {budget.item_label(item): {"seconds": 8.5, "peak_rss_bytes": 1000}}
    r = budget.rates_from_records(train, evaluation, tasks)[item]
    assert r.task_overhead_seconds == pytest.approx(3.5) and r.evaluation_peak_rss_bytes == 900 and r.task_peak_rss_bytes == 1000 and budget.peak_of(r) == 1000
    assert budget.rates_from_records(train, evaluation, None)[item].task_overhead_seconds == 0.0
    neg = budget.rates_from_records(train, evaluation, {budget.item_label(item): {"seconds": 1.0, "peak_rss_bytes": 1}})[item]
    assert neg.task_overhead_seconds == 0.0  # never negative


def test_the_larger_of_the_two_rehearsals_is_used() -> None:
    a = rates_at({4096: 0.01, 16384: 0.02, 65536: 0.05}, evaluation=2.0, overhead=1.0, peak=100)
    b = rates_at({4096: 0.02, 16384: 0.01, 65536: 0.05}, evaluation=1.0, overhead=3.0, peak=200)
    m = budget.merge_rates(a, b)
    item = ("A0", "2K/4K", "main")
    assert (m[item].seconds_per_update, m[item].evaluation_seconds, m[item].task_overhead_seconds, m[item].peak_rss_bytes) == (0.02, 2.0, 3.0, 200)
    item2 = ("A0", "8K/16K", "main")
    assert m[item2].seconds_per_update == 0.02
    partial = budget.merge_rates({item: a[item]}, b)
    assert set(partial) == set(b) and partial[("A1", "2K/4K", "main")] == b[("A1", "2K/4K", "main")]


def test_missing_items_include_a_nan_evaluation() -> None:
    r = rates_at(SLOWEST)
    assert budget.missing_items(r) == []
    del r[("A1", "2K/4K", "main")]
    r[("A0", "2K/4K", "main")] = budget.Rate(0.01, 1, 1, float("nan"))
    assert set(budget.missing_items(r)) == {("A1", "2K/4K", "main"), ("A0", "2K/4K", "main")}


# --- projections ---------------------------------------------------------------------------------------------------------------------------
def test_projections_reproduce_the_adr_arithmetic_at_the_slowest_rates() -> None:
    r = rates_at(SLOWEST)
    q1 = budget.block_projection(core.q1_cells(), r)
    assert q1.cells == 230 and q1.training_seconds / H == pytest.approx(3.89, rel=0.03) and q1.rounds == 39  # rounds of six (3.96 h) against the ADR's perfect packing (3.89 h)
    cut3 = budget.block_projection(core.q1_cells(True), r)
    assert cut3.cells == 190 and cut3.total_seconds / H == pytest.approx(2.71, rel=0.04)
    wx = budget.block_projection(core.wx_cells("A5-D"), r)
    assert wx.cells == 20 and wx.total_seconds / H == pytest.approx(0.34, rel=0.25) and wx.rounds == 4  # four rounds of six (0.41 h) against perfect packing (0.34 h)
    probe = budget.block_projection(core.probe_cells("A1"), r)
    assert probe.cells == 6 and probe.rounds == 1 and probe.total_seconds / H == pytest.approx(2.25, rel=0.01)


def test_the_task_start_up_time_enters_every_cell() -> None:
    plain = rates_at(SLOWEST)
    with_overhead = rates_at(SLOWEST, overhead=2.0)
    cell = core.q1_cells()[0]
    assert budget.cell_training_seconds(cell, with_overhead) == pytest.approx(budget.cell_training_seconds(cell, plain) + 2.0)
    assert budget.cell_evaluation_seconds(cell, with_overhead) == pytest.approx(budget.cell_evaluation_seconds(cell, plain) + 2.0)
    ev = rates_at(SLOWEST, evaluation=3.0)
    c8 = next(c for c in core.q1_cells() if c.celltype == "8K/16K")
    assert budget.cell_evaluation_seconds(c8, ev) == 6.0  # two readouts at 8K/16K
    assert budget.cell_evaluation_seconds(cell, ev) == 3.0


def test_a2_uses_its_two_phase_rates() -> None:
    r = rates_at({4096: 0.01, 16384: 0.01, 65536: 0.01})
    r[("A2", "2K/4K", "pre")] = budget.Rate(0.02, 1, 1, 0.0)
    a2 = next(c for c in core.q1_cells() if c.arm == "A2" and c.celltype == "2K/4K")
    assert budget.cell_training_seconds(a2, r) == pytest.approx(2048 * 0.02 + (8192 - 2048) * 0.01)
    a2b = next(c for c in core.q1_cells() if c.arm == "A2" and c.celltype == "8K/16K")
    r[("A2", "8K/16K", "pre")] = budget.Rate(0.03, 1, 1, 0.0)
    assert budget.cell_training_seconds(a2b, r) == pytest.approx(8192 * 0.03 + (32768 - 8192) * 0.01)


def test_makespan_is_rounds_of_six() -> None:
    assert budget.makespan([10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1]) == 10 + 4 and budget.makespan([]) == 0.0 and budget.makespan([5.0] * 6) == 5.0 and budget.makespan([5.0] * 7) == 10.0


def test_the_most_expensive_candidate_is_over_the_arms_that_can_still_be_the_candidate() -> None:
    r = rates_at(SLOWEST)
    r[("WX-A1", "8K/16K", "main")] = budget.Rate(0.2, 1, 1, 0.0)
    table = budget.projection_table(r)
    assert budget.most_expensive(table, "wx")[0] == "A1" and budget.most_expensive(table, "probe", ("A5-D",))[0] == "A5-D"
    assert set(table) == {"q1:full", "q1:cut3", "wx:A5-D", "wx:A1", "probe:A5-D", "probe:A1"}


# --- the headroom rule and the cuts ----------------------------------------------------------------------------------------------------------
def test_the_adr_s_worked_examples() -> None:
    other, q1, wx, probe = 0.8 * H, 3.89 * H, 0.34 * H, 2.25 * H
    assert holds16(0.0, [other, q1])  # 2 x (0.8 + 3.89) = 9.38 h
    assert holds16(other + q1, [wx, probe])  # 4.69 + 2 x (0.34 + 2.25) = 9.87 h
    assert holds16(other + 2 * q1, [wx, probe])  # if Q1 had run up to its own cap: 13.77 h
    assert not holds16(other + 2 * q1 + 3.0 * H, [wx, probe])
    assert 2 * (0.8 + 3.89) == pytest.approx(9.38) and 0.8 + 7.79 + 5.18 == pytest.approx(13.77) and 4.69 + 2 * (0.34 + 2.25) == pytest.approx(9.87)
    assert not holds16(0.0, [float("inf")]) and not holds16(0.0, [float("nan")])


def test_pre_q1_rule_counts_unrun_stages_and_charged_hours_once() -> None:
    d = pre16(0.0, 0.8 * H, 3.89 * H, 2.71 * H)
    assert d.action == "full" and d.cut is None and d.status is None and d.required_seconds == pytest.approx(2 * 4.69 * H)
    d2 = pre16(0.8 * H, 0.0, 3.89 * H, 2.71 * H)  # the 0.8 h already charged: counted once, as charged
    assert d2.action == "full" and d2.required_seconds == pytest.approx(2 * 3.89 * H)
    heavy = pre16(0.0, 0.8 * H, 7.5 * H, 5.0 * H)
    assert heavy.action == "cut3" and heavy.cut == 3
    stop = pre16(0.0, 0.8 * H, 9.0 * H, 8.0 * H)
    assert stop.action == "stop" and stop.status == "NOT RUN — BUDGET"


def test_the_multiples_of_the_slowest_rates_at_which_each_cut_applies() -> None:
    def pre(m: float) -> str:
        r = scaled(m)
        q1, cut3 = budget.block_projection(core.q1_cells(), r), budget.block_projection(core.q1_cells(True), r)
        return pre16(0.0, 0.8 * H, q1.total_seconds, cut3.total_seconds).action

    assert [pre(m) for m in (1.0, 1.8, 1.95, 2.55, 2.8)] == ["full", "full", "cut3", "cut3", "stop"]

    def post(m: float) -> tuple[bool, bool]:
        r = scaled(m)
        q1 = budget.block_projection(core.q1_cells(), r)
        d = post16(0.8 * H + q1.total_seconds, budget.block_projection(core.wx_cells("A5-D"), r).total_seconds, budget.block_projection(core.probe_cells("A5-D"), r).total_seconds)
        return d.wx, d.probe

    assert post(1.0) == (True, True) and post(1.6) == (True, True) and post(1.75) == (True, False)


def test_cut_order_is_probe_then_wx() -> None:
    both = post16(4.0 * H, 0.5 * H, 2.0 * H)
    assert (both.wx, both.probe, both.cuts) == (True, True, ())
    no_probe = post16(12.0 * H, 0.5 * H, 2.0 * H)
    assert (no_probe.wx, no_probe.probe, no_probe.cuts, no_probe.probe_status, no_probe.wx_status) == (True, False, (1,), "NOT RUN — BUDGET", None)
    neither = post16(15.5 * H, 0.5 * H, 2.0 * H)
    assert (neither.wx, neither.probe, neither.cuts, neither.wx_status, neither.probe_status) == (False, False, (1, 2), "NOT RUN — BUDGET", "NOT RUN — BUDGET")


def test_the_multiples_context_function() -> None:
    m = budget.multiple_thresholds({"q1": 3.89, "wx": 0.34, "probe": 2.25, "q1_cut3": 2.71}, cap_hours=16.0)
    assert m["q1"] == pytest.approx(1.85, abs=0.01) and m["q1_cut3"] == pytest.approx(2.66, abs=0.02) and m["probe"] > 3


# --- memory --------------------------------------------------------------------------------------------------------------------------------
GIB = 1024**3


def test_memory_rule_uses_every_peak_and_a_per_worker_limit_of_one_and_a_half_gib() -> None:
    r = rates_at(SLOWEST, peak=int(1.2 * GIB))
    assert budget.memory_check(r, "q1", "full")["ok"]
    item = ("A0", "8K/16K", "main")
    base = r[item]
    for field, value in (("peak_rss_bytes", int(1.6 * GIB)), ("sampled_rss_bytes", int(1.6 * GIB)), ("evaluation_peak_rss_bytes", int(1.6 * GIB)), ("task_peak_rss_bytes", int(1.6 * GIB))):
        r[item] = budget.Rate(**{**base.__dict__, field: value})
        m = budget.memory_check(r, "q1", "full")
        assert not m["ok"] and m["status"] == "NOT RUN — MEMORY" and m["peak_rss_bytes"] == value, field
    r[item] = base
    assert budget.memory_check(r, "q1", "full")["ok"]
    r[("A0", "8K/16K", "main")] = budget.Rate(**{**base.__dict__, "peak_rss_bytes": int(1.5 * GIB)})
    assert budget.memory_check(r, "q1", "full")["ok"]  # exactly 1.5 GiB passes (2x fits 3 GiB; six workers at 2x fit 18 GiB)
    assert 2 * int(1.5 * GIB) * 6 == 18 * GIB


def test_memory_rule_is_per_block_configuration_and_a_missing_item_fails() -> None:
    r = rates_at(SLOWEST, peak=int(1.0 * GIB))
    r[("A1", "32K/64K", "main")] = budget.Rate(0.06, int(1.8 * GIB), 1, 1.0)
    table = budget.memory_table(r)
    assert table["q1:full"]["ok"] and table["wx:A1"]["ok"] and not table["probe:A1"]["ok"] and table["probe:A5-D"]["ok"]  # the probe of A1 only
    del r[("A6", "32K/64K", "main")]
    m = budget.memory_check(r, "probe", "A5-D")
    assert not m["ok"] and m["missing_items"] == ["REH-A6-32K64K-main"]
    with pytest.raises(ValueError):
        budget.block_cells("q1", "nonsense")
    with pytest.raises(ValueError):
        budget.block_cells("other", "x")


# --- caps ----------------------------------------------------------------------------------------------------------------------------------
def test_cap_table_has_one_entry_per_block_configuration_and_is_twice_the_projection() -> None:
    r = rates_at(SLOWEST, evaluation=2.0, overhead=1.0)
    caps = budget.caps_table(r, gates_wall_seconds=100, gates_per_draw_seconds=5, analysis_wall_seconds=10, report_wall_seconds=5, generate_wall_seconds=400)
    assert set(caps["q1"]) == {"full", "cut3"} and set(caps["wx"]) == set(caps["probe"]) == {"A5-D", "A1"}
    p = budget.block_projection(core.q1_cells(), r)
    assert caps["q1"]["full"] == {"train": 2 * p.training_seconds, "evaluate": 2 * p.evaluation_seconds}
    assert caps["gates"] == 2 * (100 + 12 * 5) and caps["generate"] == 800 and caps["analysis"] == 60.0 and caps["report"] == 60.0  # the floor
    assert budget.cap_for(caps, "q1", "cut3") == caps["q1"]["cut3"] and budget.cap_for(caps, "gates") == 2 * (100 + 12 * 5)
    json.dumps(caps)


@pytest.mark.parametrize("stage,key", [("q1", None), ("q1", "other"), ("wx", "A0"), ("probe", None), ("nonsense", None)])
def test_a_missing_cap_entry_refuses(stage: str, key: str | None) -> None:
    caps = budget.caps_table(rates_at(SLOWEST), gates_wall_seconds=1, gates_per_draw_seconds=1, analysis_wall_seconds=1, report_wall_seconds=1, generate_wall_seconds=1)
    with pytest.raises(budget.CapMissing):
        budget.cap_for(caps, stage, key)


def test_cost_differences_are_descriptive_rate_differences() -> None:
    r = rates_at({4096: 0.01, 16384: 0.01, 65536: 0.01})
    r[("A1", "2K/4K", "main")] = budget.Rate(0.013, 1, 1, 0.0)
    r[("WX-A5-D", "2K/4K", "main")] = budget.Rate(0.012, 1, 1, 0.0)
    d = budget.cost_differences(r)
    assert d["L_addr (A1 - A0)"]["2K/4K"] == pytest.approx(0.003) and d["WX query (WX-A5-D - A5-D)"]["2K/4K"] == pytest.approx(0.002)
