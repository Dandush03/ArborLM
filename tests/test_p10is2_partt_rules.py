# ruff: noqa: E501
"""P10IS2 Part T rules that need no training: calibration selection and ladder, pilot gate, divergence cases, code identity, counted multiply-adds, the timing benchmark's control logic and the report
(ADR-0025 sections 7, 8.5, 10; rulings G1-G4, G22, L4, L8). Hand-written expectations; no model, no file outside tmp_path. Self-check only. Seeds 934001-934999."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_partt_fixtures import CFG_T, build, quantities  # noqa: E402

from studies.p10is2 import calibration as cal  # noqa: E402
from studies.p10is2 import cost, report, timing  # noqa: E402
from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2.common import core  # noqa: E402

STORE, LORA = [0.001, 0.003, 0.01], [0.0001, 0.0003, 0.001]


# --- rates ---------------------------------------------------------------------------------------------------------------------------------
def test_rate_is_the_smallest_within_0_01_of_the_best() -> None:
    assert cal.select_rate(CFG_T, "store", {0.001: 0.40, 0.003: 0.50, 0.01: 0.51}) == 0.003  # 0.001 is 0.11 behind; 0.003 within 0.01 of 0.51
    assert cal.select_rate(CFG_T, "store", {0.001: 0.50, 0.003: 0.51, 0.01: 0.49}) == 0.001  # all within 0.01: the smallest
    assert cal.select_rate(CFG_T, "store", {0.001: 0.25, 0.003: 0.30, 0.01: 0.50}) == 0.01
    assert cal.select_rate(CFG_T, "lora", {0.0001: 0.1, 0.0003: 0.45, 0.001: 0.46}) == 0.0003
    assert cal.select_rate(CFG_T, "etable", {0.001: 0.30, 0.003: 0.30, 0.01: 0.30}) == 0.001  # a three-way tie goes to the smallest (C4)


def test_rate_tie_edge_is_inclusive_and_free_of_float_noise() -> None:
    assert cal.select_rate(CFG_T, "store", {0.001: 0.49, 0.003: 0.50, 0.01: 0.40}) == 0.001  # exactly 0.01 behind: within
    assert cal.select_rate(CFG_T, "store", {0.001: 0.4899, 0.003: 0.50, 0.01: 0.40}) == 0.003  # 0.0101 behind: not within
    assert cal.within(0.5, 0.5 - 0.0100000000000001, 0.01)  # noise below 1e-12 does not decide


def test_diverged_rates_are_not_eligible_and_all_diverged_stops() -> None:
    assert cal.select_rate(CFG_T, "store", {0.001: None, 0.003: 0.45, 0.01: 0.50}) == 0.01  # 0.001 diverged: not eligible even though it is the smallest
    assert cal.select_rate(CFG_T, "store", {0.001: 0.30, 0.003: None, 0.01: None}) == 0.001
    with pytest.raises(cal.CalibrationStop, match="every store rate diverged"):
        cal.select_rate(CFG_T, "store", {0.001: None, 0.003: None, 0.01: None})
    with pytest.raises(cal.CalibrationStop, match="DIVERGED"):
        cal.select_rate(CFG_T, "store", {0.001: float("nan"), 0.003: 0.4, 0.01: 0.4})
    with pytest.raises(ValueError, match="exactly"):
        cal.select_rate(CFG_T, "lora", {0.001: 0.4, 0.003: 0.4, 0.01: 0.4})  # the store's grid is not the LoRA grid


def test_read_layer_by_the_same_rule_with_four_as_the_smaller() -> None:
    assert cal.select_read_layer(CFG_T, 0.50, 0.51) == 4  # within 0.01: the smaller
    assert cal.select_read_layer(CFG_T, 0.50, 0.5101) == 12
    assert cal.select_read_layer(CFG_T, 0.50, None) == 4  # a diverged read-layer run is not eligible
    assert cal.select_read_layer(CFG_T, 0.50, 0.40) == 4


# --- the convergence ladder ----------------------------------------------------------------------------------------------------------------
def ladder(store_cap: dict, lora_cap: dict) -> dict:  # type: ignore[type-arg]
    return {"store": {"A": store_cap, "B": store_cap}, "lora": {"A": lora_cap, "B": lora_cap}}


def test_training_length_smallest_rung_that_converged_for_both_module_types() -> None:
    flat = {1000: 0.40, 2000: 0.405, 4000: 0.41, 8000: 0.41}
    assert cal.choose_training_length(CFG_T, ladder(flat, flat))["U"] == 1000  # 0.005 < 0.01
    slow_store = {1000: 0.20, 2000: 0.40, 4000: 0.405, 8000: 0.41}
    r = cal.choose_training_length(CFG_T, ladder(slow_store, flat))
    assert r["U"] == 2000 and r["converged"] and r["line_note"] is None  # u = 1000: +0.20; u = 2000: 0.005
    never = {1000: 0.10, 2000: 0.20, 4000: 0.30, 8000: 0.40}
    r2 = cal.choose_training_length(CFG_T, ladder(never, flat))
    assert r2["U"] == 8000 and r2["converged"] is False and r2["line_note"] == "NOT CONVERGED AT U"
    assert cal.choose_training_length(CFG_T, ladder(flat, {1000: 0.1, 2000: 0.3, 4000: 0.305, 8000: 0.30}))["U"] == 2000  # LoRA decides


def test_ladder_difference_edges_and_decreases() -> None:
    edge = {1000: 0.40, 2000: 0.4099, 4000: 0.42, 8000: 0.43}  # +0.0099 at u = 1000 (converged), but +0.0101 at 2000 and 4000...
    assert cal.choose_training_length(CFG_T, ladder(edge, edge))["U"] == 1000
    exact = {1000: 0.25, 2000: 0.50, 4000: 0.75, 8000: 0.76}  # +0.01 is NOT below 0.01: u = 1000 fails (0.25), 2000 fails (0.25), 4000: +0.01 -> not below
    assert cal.choose_training_length(CFG_T, ladder(exact, exact))["U"] == 8000
    decreasing = {1000: 0.50, 2000: 0.30, 4000: 0.10, 8000: 0.05}  # a decrease counts as converged (G3)
    assert cal.choose_training_length(CFG_T, ladder(decreasing, decreasing))["U"] == 1000


def test_non_finite_or_missing_ladder_value_stops_calibration() -> None:
    good = {1000: 0.4, 2000: 0.4, 4000: 0.4, 8000: 0.4}
    bad = {**good, 4000: float("nan")}
    with pytest.raises(cal.CalibrationStop, match="returns to the human lead"):
        cal.choose_training_length(CFG_T, ladder(good, bad))
    with pytest.raises(cal.CalibrationStop):
        cal.choose_training_length(CFG_T, ladder(good, {1000: 0.4, 2000: 0.4, 4000: 0.4}))  # no 8,000 snapshot
    with pytest.raises(cal.CalibrationStop):
        cal.choose_training_length(CFG_T, ladder(good, {**good, 2000: None}))


# --- the pilot -----------------------------------------------------------------------------------------------------------------------------
def test_pilot_gate_rows() -> None:
    assert cal.pilot_gate(CFG_T, {"A": 0.25, "B": 0.9}) == {"passed": True, "label": None, "below": []}  # 0.25 is not below 0.25
    assert cal.pilot_gate(CFG_T, {"A": 0.2499, "B": 0.9})["label"] == "NOT STARTED: PILOT"
    r = cal.pilot_gate(CFG_T, {"A": 0.1, "B": 0.2})
    assert r["label"] == "NOT STARTED: PILOT" and r["below"] == ["A", "B"]
    assert cal.pilot_gate(CFG_T, {"A": None, "B": 0.9}) == {"passed": False, "label": "NOT STARTED: PILOT (GAP UNDEFINED)"}
    with pytest.raises(cal.CalibrationStop):
        cal.pilot_gate(CFG_T, {"A": float("inf"), "B": 0.9})


def test_calibration_units_are_section_14s_36_units() -> None:
    units = cal.calibration_units(CFG_T)
    by = {k: sum(u["units_of_2000"] for u in units if u["kind"] == k) for k in ("store-type", "lora")}
    assert by == {"store-type": 22, "lora": 14} and sum(by.values()) == 36
    assert len({u["id"] for u in units}) == len(units)
    assert all(u["layer"] == 4 for u in units if u["id"].startswith("grid-store"))  # the grid at L = 4
    assert all(u["draw"] == 1 for u in units if u["id"].startswith("ladder")) and all(u["draw"] == 0 for u in units if not u["id"].startswith("ladder"))
    assert [u for u in units if u["id"] == "layer12-A"][0]["layer"] == 12


def test_calibration_code_identity_and_repetition_choice() -> None:
    frozen = {"studies/p10is2/a.py": "h1", "studies/p10is2/b.py": "h2"}
    files = list(frozen)
    ok = {"code_hashes": dict(frozen)}
    assert cal.code_identity_problems(ok, frozen, files) == []
    assert any("differs" in p for p in cal.code_identity_problems({"code_hashes": {**frozen, "studies/p10is2/b.py": "x"}}, frozen, files))
    assert any("stand-in" in p for p in cal.code_identity_problems({**ok, "stand_in": True}, frozen, files))
    assert any("SUPERSEDED" in p for p in cal.code_identity_problems({**ok, "superseded": True}, frozen, files))
    assert any("no hash" in p for p in cal.code_identity_problems({"code_hashes": {"studies/p10is2/a.py": "h1"}}, frozen, files))
    changed = {"code_hashes": {**frozen, "studies/p10is2/b.py": "old"}}
    r = cal.repetition_used({0: changed, 1: ok}, frozen, files)
    assert r["used"] == 1 and r["superseded"] == [0] and r["draws"] == [2, 3]  # the repetition whose hashes equal the frozen files
    assert cal.repetition_used({0: ok, 1: ok}, frozen, files)["used"] == 0
    assert cal.repetition_used({0: changed}, frozen, files)["used"] is None and "decision of the lead" in cal.repetition_used({0: changed}, frozen, files)["refused"]


# --- counted multiply-adds -----------------------------------------------------------------------------------------------------------------
TINY = cost.StudentShape(width=8, layers=2, heads=2, kv_heads=1, intermediate=16, vocab=32)


def test_block_linear_maps_by_hand() -> None:
    maps = dict((n, (i, o)) for n, i, o in TINY.block_linear_maps())
    assert TINY.head_dim == 4 and maps == {"q": (8, 8), "k": (8, 4), "v": (8, 4), "o": (8, 8), "gate": (8, 16), "up": (8, 16), "down": (16, 8)}
    assert sum(i * o for i, o in maps.values()) == 64 + 32 + 32 + 64 + 128 + 128 + 128 == 576
    assert cost.per_token_forward(TINY) == 2 * 576 + 8 * 32 == 1408
    assert cost.per_token_forward(TINY, lora_rank=2) == 2 * (576 + 2 * (8 + 8) + 2 * (8 + 4)) + 256 == 2 * (576 + 56) + 256


def test_training_multiply_adds_lora_hand_case() -> None:
    r = cost.training_multiply_adds(TINY, "lora", batch=2, mean_len=5.0, lora_rank=2)
    tokens, block, extra, head = 10, 576, 2 * 16 + 2 * 12, 256
    assert extra == 56
    assert r["forward"] == tokens * (2 * (block + extra) + head)
    assert r["backward"] == tokens * (2 * (block + 2 * extra) + head)  # frozen maps once, trainable factors twice
    assert r["total"] == r["forward"] + r["backward"] and r["tokens"] == 10


def test_training_multiply_adds_memory_hand_case() -> None:
    r = cost.training_multiply_adds(TINY, "memory", batch=2, mean_len=5.0, mean_reads=3.0, rows=100, trainable_rows=40, read_block=0, trainable_share=0.5)
    tokens, reads, block, head = 10, 6, 576, 256
    assert r["forward"] == tokens * (2 * block + head) + reads * (100 * 16 + 8 * 576)
    above = 2 - (0 + 1)  # one block above the read
    assert r["backward"] == tokens * (above * block + head) + reads * (100 * 16 + 40 * 16 + 8 * 576 + 8 * 576 * 0.5)
    with pytest.raises(ValueError):
        cost.training_multiply_adds(TINY, "lora", batch=2, mean_len=5.0)
    with pytest.raises(ValueError):
        cost.training_multiply_adds(TINY, "other", batch=2, mean_len=5.0)


def test_student_shape_defaults_are_the_pinned_student() -> None:
    s = cost.StudentShape()
    assert (s.width, s.layers, s.heads, s.kv_heads, s.intermediate, s.vocab, s.head_dim) == (576, 30, 9, 3, 1536, 49152, 64)
    # the LoRA parameter count of ADR section 5.2: rank 42 on q and v of all 30 blocks = 2,419,200
    assert 30 * sum(i * o for _, i, o in cost.lora_maps(s, 42)) == 2_419_200


# --- the timing benchmark's control logic --------------------------------------------------------------------------------------------------
class Clock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps = 0

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps += 1
        assert self.sleeps < 10_000, "an unbounded wait"
        self.t += s


def attempt(clock: Clock, *, loads, alive=lambda: [], durations=(1.0, 1.0, 1.0)):  # type: ignore[no-untyped-def]
    it = iter(durations)

    def rep() -> float:
        d = next(it)
        clock.t += d
        return d

    return timing.run_attempt(rep, cfg=CFG_T, clock=clock.now, sleep=clock.sleep, load_fn=loads, alive_fn=alive)


def test_quiet_condition_needs_load_at_most_two_no_process_and_sixty_seconds() -> None:
    assert timing.quiet(2.0, [], 60.0, CFG_T) and not timing.quiet(2.01, [], 60.0, CFG_T) and not timing.quiet(1.0, ["p10ir"], 60.0, CFG_T) and not timing.quiet(1.0, [], 59.9, CFG_T)


def test_attempt_with_a_quiet_machine_completes_three_repetitions_and_reads_load_before() -> None:
    c = Clock()
    a = attempt(c, loads=lambda: 0.5, durations=(10.0, 10.0, 10.0))
    assert a["status"] == "COMPLETE" and len(a["repetitions"]) == 3 and a["median_seconds"] == 10.0 and a["cv"] == 0.0 and a["unstable"] is False
    for r in a["repetitions"]:
        assert r["load_before"]["quiet_seconds"] >= 60.0 and r["load_before"]["load1"] == 0.5 and r["load_before"]["alive"] == []  # the condition was read BEFORE the repetition
    assert a["repetitions"][1]["load_before"]["quiet_seconds"] >= 60.0  # and again before the second


def test_attempt_that_cannot_start_in_thirty_minutes_ends_incomplete_and_keeps_repetitions() -> None:
    c = Clock()
    state = {"busy_after": 1}

    def loads() -> float:
        return 0.5 if c.t < 100 else 9.0  # busy from 100 s on: the second repetition can never start

    a = attempt(c, loads=loads)
    assert a["status"] == "INCOMPLETE ATTEMPT" and len(a["repetitions"]) == 1 and "30 minutes" in a["reason"] and c.t <= 30 * 60 + 5.0 + 1.0
    assert state["busy_after"] == 1


def test_a_process_alive_resets_the_quiet_clock() -> None:
    c = Clock()
    alive_until = {"t": 100.0}
    a = attempt(c, loads=lambda: 0.1, alive=lambda: ["p10s1"] if c.t < alive_until["t"] else [])
    assert a["status"] == "COMPLETE" and a["repetitions"][0]["load_before"]["quiet_seconds"] >= 60.0
    assert a["repetitions"][0]["load_before"]["alive"] == [] and c.t >= 160.0  # 100 s of an alive process, then 60 s of quiet


def test_unstable_when_cv_exceeds_five_percent_and_stage_records() -> None:
    c = Clock()
    a = attempt(c, loads=lambda: 0.1, durations=(10.0, 10.0, 12.0))
    assert a["unstable"] is True and a["cv"] > 0.05
    c2 = Clock()
    a2 = attempt(c2, loads=lambda: 0.1, durations=(10.0, 10.2, 10.0))
    assert a2["unstable"] is False
    inc = {"status": "INCOMPLETE ATTEMPT", "repetitions": [{"seconds": 9.0}], "reason": "x"}
    rec = timing.stage_record([inc, a, a2], CFG_T)
    assert rec["status"] == "MEASURED" and rec["attempt"] == 2 and rec["record"] is a and rec["incomplete_attempts_kept"] == [inc]  # the FIRST complete attempt, never chosen on its figures
    assert timing.stage_record([inc] * 4, CFG_T)["status"] == "RESCHEDULE"
    assert timing.stage_record([inc] * 5, CFG_T)["status"] == "NEEDS DECISION: NOT MEASURED"


# --- the report ----------------------------------------------------------------------------------------------------------------------------
def test_report_prints_the_fixed_line_above_every_line_and_the_replicate_count() -> None:
    q = quantities()
    derived = L.derive_all(q)
    st = L.study_status(build())
    text = report.render(st, derived, {"U": 2000, "converged": True})
    blocks = text.split("\n\n")
    assert len(blocks) >= 9 and all(b.split("\n")[0] == core.ORACLE_LINE for b in blocks)
    assert "SUPPORTED (append-frozen + consolidation)" in blocks[0] and "(3 replicates, U = 2000)" in blocks[0]
    assert "acquisition: MEMORY AHEAD; retention: NOT DISTINGUISHED" in blocks[1] and report.QUALIFIER in blocks[1]
    assert "NOT CONVERGED AT U" not in text and "OVERLAPPING" not in text


def test_report_says_not_converged_and_overlap_share_where_the_adr_says() -> None:
    derived = L.derive_all(quantities())
    ctx = {"U": 8000, "converged": False, "draws": "OVERLAPPING DRAWS", "shared_share": {"A": 0.41, "B": 0.52}}
    text = report.render(L.study_status(build()), derived, ctx)
    for b in text.split("\n\n")[:-1]:
        assert "(3 replicates, U = 8000) NOT CONVERGED AT U" in b
    assert text.count("OVERLAPPING DRAWS; shared share") == 7 and "A 0.410, B 0.520" in text  # beside every line that says "every cell"
    assert "MODIFICATION (M-ii, descriptive): RETAINS UNDER MODIFICATION (3 replicates, U = 8000) NOT CONVERGED AT U" in text


def test_report_under_an_engineering_status_derives_no_line() -> None:
    reg = build()
    st = L.study_status(reg, item_errors=["out of memory in cell M-append 0AB"])
    text = report.render(st, None, {"U": 2000})
    assert text.startswith(core.ORACLE_LINE) and "ENGINEERING STOP — ITEM ERRORS" in text and "No line is derived." in text and "MILESTONE" not in text


def test_report_refuses_a_line_without_the_fixed_line_or_u() -> None:
    with pytest.raises(report.ReportRefused):
        report.check("MILESTONE: SUPPORTED (3 replicates, U = 2000)")
    with pytest.raises(report.ReportRefused):
        report.check(core.under_line("MILESTONE: SUPPORTED"))
    with pytest.raises(report.ReportRefused):
        report.line("X", "y", {"U": None})
    assert report.check(core.under_line("X: y (3 replicates, U = 2000)")).startswith(core.ORACLE_LINE)
