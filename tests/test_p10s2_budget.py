# ruff: noqa: E501
"""P10S2 charged-time ledger, projections with task start-up, the memory rule, the rehearsal rung rule in its registered order, the cap extension with its recorded-raise mechanism, and the per-configuration
stage caps (ADR-0022 sections 13.2, 13.3). The rates are constructed to exercise the rules; every hour is analytical, never a measurement. Self-check only: not independent review, not Astra validation, not
human approval."""

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import budget, core  # noqa: E402
from studies.p10s2.ledger import Ledger, LedgerRefused, sum_charged  # noqa: E402

GIB = 2**30
STORE = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD", "ETABLE")  # E-table is store-type: measured at both read layers (the lead's ruling of 2026-11-15)


def rates(scale: float = 1.0, *, slow12: float = 1.0, overhead: float = 0.0, **peaks: int) -> budget.Rates:
    us: dict[str, float] = {}
    for g in STORE:
        us[f"{g}@L4"] = 0.5 * scale
        us[f"{g}@L12"] = 0.5 * scale * slow12
    for g in ("LORA1", "LSEQ", "LJOINT"):
        us[g] = 0.6 * scale
    us["ETABLE@L4"] = 0.6 * scale
    us["ETABLE@L12"] = 0.6 * scale * slow12
    return budget.Rates(us, 4, 100.0 * scale, 600.0 * scale, 300.0 * scale, 120.0 * scale, 200.0 * scale, overhead, analysis_seconds=400.0 * scale, report_seconds=200.0 * scale, **{"train_peak_bytes": 2 * GIB, "eval_peak_bytes": 3 * GIB, "recompute_peak_bytes": 3 * GIB, "task_peak_bytes": 4 * GIB, **peaks})


def uniform(rate: float = 1.0, overhead: float = 0.0) -> budget.Rates:
    us = {f"{g}@L{ly}": rate for g in STORE for ly in (4, 12)}
    us.update({g: rate for g in ("LORA1", "LSEQ", "LJOINT")})
    return budget.Rates(us, 4, 10.0, 20.0, 30.0, 5.0, 7.0, overhead)


# --- the ledger ----------------------------------------------------------------------------------------------------------------------------------
def test_charged_hours_are_the_sum_over_all_processes_k_workers_t_hours(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("datagen", 3600.0)
    led.record("train", 3600.0, workers=3, process="three parallel workers for one hour")  # k parallel workers running for t hours charge k t
    led.record("gates-registered", 1800.0, registered=True)  # the second gates stage on registered seeds is charged
    led.record("recompute", 7200.0, workers=2, registered=True)  # the independent recomputation is charged
    assert led.total_hours() == pytest.approx(1 + 3 + 0.5 + 4)
    assert led.by_kind() == {"datagen": 1.0, "train": 3.0, "gates-registered": 0.5, "recompute": 4.0}
    assert sum_charged(led.entries(), ["gates-registered", "recompute"]) == pytest.approx(4.5)
    assert led.registered_observed() and not Ledger(tmp_path / "other.jsonl").registered_observed()
    with pytest.raises(ValueError):
        led.record("unknown stage", 1.0)
    with pytest.raises(ValueError):
        led.record("train", 1.0, workers=0)
    assert led.summary(36.0)["remaining_hours"] == pytest.approx(36 - 8.5)


def test_an_entry_is_written_when_the_process_fails_and_a_stage_over_the_cap_is_not_started(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    with pytest.raises(RuntimeError):
        with led.charge("train", workers=2, process="fails"):
            raise RuntimeError("boom")
    done = [e for e in led.entries() if e["status"] != "started"]
    assert len(done) == 1 and done[0]["status"] == "failed" and done[0]["workers"] == 2 and done[0]["charged_hours"] >= 0.0
    assert led.entries()[0]["status"] == "started" and led.entries()[0]["run_id"] == done[0]["run_id"]  # a start marker is written first
    with led.charge("report"):
        pass
    assert len([e for e in led.entries() if e["status"] != "started"]) == 2
    led.record("train", 35 * 3600.0)
    led.refuse_if_over(0.5, 36.0, "ok")
    with pytest.raises(LedgerRefused):
        led.refuse_if_over(1.5, 36.0, "stage evaluate")
    led.refuse_if_over(1.5, 72.0, "under a raised cap")


# --- projections include task start-up -----------------------------------------------------------------------------------------------------------------
def test_training_projection_counts_updates_times_measured_rate_plus_task_start_up() -> None:
    assert budget.training_seconds(1, 100, uniform(1.0), slower=False) == 2000.0  # 14 store-type cell-updates of U plus 6 LoRA ones, M-ii at U updates (its measured rate carries the 64-row cost)
    assert budget.training_seconds(1, 100, uniform(1.0, overhead=10.0), slower=False) == 2000.0 + 18 * 10.0  # one process per cell
    assert budget.training_seconds(4, 100, uniform(1.0, overhead=10.0), slower=False) == 4 * 2180.0
    assert budget.cell_updates("MJOINT", 100) == 200 and budget.cell_updates("LJOINT", 100) == 200 and budget.cell_updates("MII", 100) == 100 and budget.cell_updates("ST1", 100) == 100


def test_scoring_second_gates_and_recomputation_include_start_up() -> None:
    r0, r1 = uniform(1.0, 0.0), uniform(1.0, overhead=10.0)
    assert budget.scoring_seconds(1, r0) == 18 * 10.0 + 20.0 + 30.0 + 5.0
    assert budget.scoring_seconds(1, r1) - budget.scoring_seconds(1, r0) == 18 * 10.0  # one start-up per scoring process
    assert budget.recompute_seconds(2, r1) == budget.scoring_seconds(2, r1)  # one repetition of the scoring rows, the timing row included (the lead's ruling of 2026-11-15)
    parts = budget.registered_run_seconds(2, 100, r1)
    assert parts["second_gates_stage"] == 7.0 + 10.0 and parts["total"] == pytest.approx(parts["training"] + parts["scoring"] + parts["second_gates_stage"] + parts["recomputation"] + parts["analysis_and_report"])
    assert parts["analysis_and_report"] == budget.CAP_FLOOR_SECONDS  # never below the reserved floor: analysis and report are always inside R
    assert parts["recomputation"] > 0 and parts["second_gates_stage"] > 0  # both are inside R (charged)


def test_u_1000_uses_the_slower_of_the_two_read_layers() -> None:
    fast = rates(slow12=1.0)
    slow = rates(slow12=3.0)
    t2000 = budget.registered_run_seconds(4, 2000, slow)["training"]
    assert t2000 == budget.registered_run_seconds(4, 2000, fast)["training"]  # U = 2,000 uses the calibrated layer (L = 4) rates
    assert budget.registered_run_seconds(4, 1000, slow)["training"] > budget.registered_run_seconds(4, 1000, fast)["training"]
    assert budget.group_rate("ST1", slow, None, slower=True) == 1.5 and budget.group_rate("ST1", slow, None, slower=False) == 0.5 and budget.group_rate("ST1", slow, 12, slower=False) == 1.5
    assert budget.group_rate("LORA1", slow, None, slower=True) == 0.6
    with pytest.raises(KeyError):
        budget.group_rate("MAF", replace(slow, update_seconds={}), None, slower=True)


# --- the memory rule (evaluation and recomputation peaks count) ----------------------------------------------------------------------------------------
def test_memory_rule_reads_every_peak_not_only_training_and_needs_twice_the_peak_within_the_limits() -> None:
    assert budget.memory_check(rates())["ok"]  # twice the largest peak (4 GiB task) is exactly 8 GiB per worker
    for name, bytes_ in (("eval_peak_bytes", 5 * GIB), ("recompute_peak_bytes", 5 * GIB), ("task_peak_bytes", 5 * GIB)):
        m = budget.memory_check(rates(**{name: bytes_}))
        assert not m["ok"] and "twice that exceeds" in " ".join(m["problems"]), name  # the training peak alone (2 GiB) would have passed; 5 GiB alone passes 8 GiB but not twice
    assert budget.memory_check(rates(task_peak_bytes=4 * GIB))["ok"] and not budget.memory_check(rates(task_peak_bytes=4 * GIB + 1))["ok"]  # exactly twice 4 GiB is within 8 GiB
    assert budget.memory_check(rates(), workers=3)["ok"] is True  # 3 workers x twice 4 GiB = 24 GiB
    agg = budget.memory_check(rates(), workers=4)
    assert agg["ok"] is False and "aggregate" in " ".join(agg["problems"])  # 4 x 8 GiB = 32 GiB > 24 GiB
    assert budget.memory_check(rates(task_peak_bytes=3 * GIB), workers=4)["ok"] is True  # 4 x twice 3 GiB = 24 GiB
    assert core.CFG["budget"]["workers"] == 1 and core.CFG["budget"]["memory_per_worker_gib"] == 8.0 and core.CFG["budget"]["memory_aggregate_gib"] == 24.0


# --- the rung rule in its registered order -------------------------------------------------------------------------------------------------------------
def hours(scale: float, n: int, u: int, overhead: float = 0.0) -> float:
    return budget.registered_run_seconds(n, u, rates(scale, overhead=overhead))["total"] / 3600.0


def scale_for(target_hours: float, n: int, u: int) -> float:
    return target_hours / hours(1.0, n, u)  # R is linear in the rates when every rate is scaled


def test_projection_is_linear_in_the_rates() -> None:
    assert hours(2.0, 3, 2000) == pytest.approx(2 * hours(1.0, 3, 2000)) and hours(1.0, 4, 2000) > hours(1.0, 3, 2000) > hours(1.0, 3, 1000)


def test_rung_rule_order_and_outcome_not_started_budget() -> None:
    assert [(n, u) for n, u in budget.rungs()] == [(4, 2000), (3, 2000), (4, 1000), (3, 1000)]
    # P = 3.5 h, cap 36 h: a rung fits iff R <= 16.25 h
    p = 3.5
    k1 = scale_for(16.0, 4, 2000)  # rung 1 fits with R = 16.0
    d = budget.rehearsal_rule(p, rates(k1), 36.0)
    assert d.outcome == "rung 1" and (d.replicates, d.updates) == (4, 2000) and d.reason == ""
    k2 = scale_for(16.5, 4, 2000)  # rung 1 does not fit (R = 16.5 > 16.25); rung 2 (three replicates) does
    d = budget.rehearsal_rule(p, rates(k2), 36.0)
    assert d.outcome == "rung 2" and (d.replicates, d.updates) == (3, 2000)
    # rung 2 does not fit but rung 3 (four replicates at U = 1,000) is tried before rung 4 only where it is the first that fits
    k = scale_for(16.25 * 1.0001, 3, 2000)
    d = budget.rehearsal_rule(p, rates(k), 36.0)
    assert d.outcome in ("rung 3", "rung 4") and d.updates == 1000 and d.charged_hours == p
    assert hours(k, 4, 1000) > hours(k, 3, 1000)  # rung 3 costs more than rung 4, so rung 4 can be the first to fit
    huge = budget.rehearsal_rule(p, rates(scale_for(100.0, 4, 2000)), 36.0)
    assert huge.outcome == budget.NOT_STARTED_BUDGET == "NOT STARTED: BUDGET" and huge.replicates is None and "no rung" in huge.reason
    assert set(huge.projections) == {"n4-U2000", "n3-U2000", "n4-U1000", "n3-U1000"}  # the rehearsal record keeps every projection
    # the exact boundary: P + 2 R == cap fits
    exact = scale_for((36.0 - p) / 2, 4, 2000)
    assert budget.rehearsal_rule(p, rates(exact * 0.9999), 36.0).outcome == "rung 1"  # just inside P + 2R <= cap
    assert budget.rehearsal_rule(p, rates(exact * 1.0001), 36.0).outcome != "rung 1"  # just outside


def test_rung_rule_with_a_slow_second_read_layer_for_u_1000() -> None:
    p = 3.5
    base = rates(scale_for(30.0, 3, 1000))  # rung 4 projected at R = 30 h: far too slow at 36 h, fits against 72 h
    assert budget.rehearsal_rule(p, base, 72.0).updates in (2000, 1000)
    slow = rates(scale_for(30.0, 3, 1000), slow12=2.0)
    assert hours(scale_for(30.0, 3, 1000), 3, 1000) < budget.registered_run_seconds(3, 1000, slow)["total"] / 3600.0  # the slower rate counts more time against the cap


def test_rung_rule_refuses_on_memory() -> None:
    d = budget.rehearsal_rule(1.0, rates(0.001, eval_peak_bytes=5 * GIB), 36.0)
    assert d.outcome == budget.NOT_STARTED_BUDGET and d.reason.startswith("memory:")


# --- the cap extension and its recorded-raise mechanism --------------------------------------------------------------------------------------------------
def needed(p: float, scale: float) -> float:
    return p + 2 * hours(scale, 4, 2000)


def test_no_raise_when_rung_1_fits_and_the_raise_is_the_smallest_whole_number_of_hours() -> None:
    p = 3.5
    assert budget.propose_raise(p, rates(scale_for(16.0, 4, 2000))) is None
    k = scale_for(20.28, 4, 2000)  # the ADR's fast end of the unmeasured range
    prop = budget.propose_raise(p, rates(k))
    assert prop is not None and prop.old_cap_hours == 36.0 and prop.new_cap_hours == float(math.ceil(needed(p, k))) and not prop.ceiling_hit
    assert prop.rung1_total_hours == pytest.approx(needed(p, k)) and 36 < prop.new_cap_hours <= 72
    big = budget.propose_raise(p, rates(scale_for(40.0, 4, 2000)))
    assert big is not None and big.new_cap_hours == 72.0 and big.ceiling_hit  # beyond 72 the cap is the ceiling and the rung rule applies against it
    exact = budget.propose_raise(p, rates(scale_for((50.0 - p) / 2, 4, 2000)))
    assert exact is not None and exact.new_cap_hours == pytest.approx(50.0, abs=1.0)


def test_record_raise_once_recomputed_from_the_rehearsal_record(tmp_path: Path) -> None:
    core.reset_seed_record()
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("rehearsal", 3.5 * 3600)
    r = rates(scale_for(20.28, 4, 2000))
    prop = budget.propose_raise(led.total_hours(), r)
    assert prop is not None
    path = tmp_path / "cap_raise.json"
    assert budget.effective_cap(path) == 36.0 and led.cap_hours() == 36.0
    rec = budget.record_raise(r, path, led)  # nothing is typed: the amount is recomputed from the rates and P
    assert rec["new_cap_hours"] == prop.new_cap_hours and rec["recorded_at_stage"] == "rehearsal headroom check" and budget.effective_cap(path) == prop.new_cap_hours == led.cap_hours()
    saved = json.loads(path.read_text())
    assert saved["old_cap_hours"] == 36.0 and saved["rung1_total_hours"] == pytest.approx(prop.rung1_total_hours) and "projections_hours" in saved  # the raise, the measured projection, the old and the new cap
    with pytest.raises(budget.CapRefused, match="once already"):
        budget.record_raise(r, path, led)  # raised once
    path.unlink()
    with pytest.raises(budget.CapRefused, match="once already"):
        budget.record_raise(r, path, led)  # deleting the file does not allow a second raise: the ledger holds it
    assert budget.rehearsal_rule(led.total_hours(), r, led.cap_hours()).outcome == "rung 1"  # the rung rule then runs against the raised cap


def test_record_raise_refuses_after_a_registered_seed_has_been_observed(tmp_path: Path) -> None:
    r = rates(scale_for(20.28, 4, 2000))
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("rehearsal", 3.5 * 3600)
    # (1) a registered process in the study ledger (its start marker is enough: a killed process has still drawn its seeds)
    with led.measure("train", registered=True):
        pass
    with pytest.raises(budget.CapRefused, match="registered seed has been observed"):
        budget.record_raise(r, tmp_path / "a.json", led)
    assert not (tmp_path / "a.json").exists()
    # (2) a registered replicate seed in the seed record
    core.reset_seed_record()
    core.seeded_generator(220001, "stage-1 store", "registered-run")
    with pytest.raises(budget.CapRefused, match="registered seed has been observed"):
        budget.record_raise(r, tmp_path / "b.json", Ledger(tmp_path / "fresh.jsonl"))
    core.reset_seed_record()
    # the partition-side seeds are drawn before the rehearsal and are not replicate seeds
    core.seeded_generator(220901, "partition", "registered-data")
    assert not budget.registered_seed_observed(Ledger(tmp_path / "fresh2.jsonl"))
    core.reset_seed_record()


def test_record_raise_refuses_when_rung_1_fits_and_verify_raise_recomputes(tmp_path: Path) -> None:
    core.reset_seed_record()
    led = Ledger(tmp_path / "l.jsonl")
    fits = rates(scale_for(10.0, 4, 2000))
    with pytest.raises(budget.CapRefused, match="fits the 36-hour cap"):
        budget.record_raise(fits, tmp_path / "x.json", led)
    assert not (tmp_path / "x.json").exists()
    led.record("rehearsal", 3.5 * 3600)
    r = rates(scale_for(20.28, 4, 2000))
    path = tmp_path / "cap_raise.json"
    assert budget.verify_raise(path, led.total_hours(), fits, led) == 36.0
    budget.record_raise(r, path, led)
    cap = budget.verify_raise(path, led.total_hours(), r, led)
    assert cap > 36.0
    with pytest.raises(budget.CapRefused, match="recomputed from the rehearsal record"):
        budget.verify_raise(path, led.total_hours(), rates(scale_for(30.0, 4, 2000)), led)  # other rates: the recorded cap is not the recomputed one
    path.write_text(json.dumps({**json.loads(path.read_text()), "new_cap_hours": 71.0}))
    with pytest.raises(budget.CapRefused, match="disagree"):
        budget.verify_raise(path, led.total_hours(), r, led)  # an edited raise file against the ledger
    (tmp_path / "bad.json").write_text(json.dumps({"new_cap_hours": 100.0}))
    with pytest.raises(budget.CapRefused):
        budget.effective_cap(tmp_path / "bad.json")


def test_headroom_check_returns_the_proposal_and_the_decision(tmp_path: Path) -> None:
    core.reset_seed_record()
    led = Ledger(tmp_path / "l.jsonl")
    led.record("rehearsal", 3.5 * 3600)
    r = rates(scale_for(20.28, 4, 2000))
    h = budget.headroom_check(led.total_hours(), r, led, tmp_path / "cap_raise.json")
    assert h["proposal"] is not None and h["cap_in_force_hours"] == 36.0 and h["decision"]["outcome"] in ("rung 2", "rung 3", "rung 4", "NOT STARTED: BUDGET")
    budget.record_raise(r, tmp_path / "cap_raise.json", led)
    h2 = budget.headroom_check(led.total_hours(), r, led, tmp_path / "cap_raise.json")
    assert h2["cap_in_force_hours"] > 36.0 and h2["decision"]["outcome"] == "rung 1"


# --- stage caps per configuration -------------------------------------------------------------------------------------------------------------------
def test_stage_caps_are_per_configuration_twice_the_projection_with_task_start_up() -> None:
    r = rates(1.0, overhead=5.0)
    caps = budget.stage_caps(r)
    assert set(caps) == {"n4-U2000", "n3-U2000", "n4-U1000", "n3-U1000"} and all(set(v) == set(budget.REGISTERED_STAGES) for v in caps.values())
    sec = budget.stage_seconds(4, 2000, r)
    assert caps["n4-U2000"]["train"] == 2 * sec["train"] == 2 * budget.training_seconds(4, 2000, r, slower=False)
    assert caps["n4-U2000"]["evaluate"] == 2 * sec["evaluate"] and caps["n4-U2000"]["recompute"] == 2 * budget.recompute_seconds(4, r)
    assert caps["n4-U2000"]["analysis"] >= budget.CAP_FLOOR_SECONDS and caps["n4-U2000"]["report"] >= budget.CAP_FLOOR_SECONDS
    assert caps["n4-U2000"]["train"] > caps["n3-U2000"]["train"] > caps["n3-U1000"]["train"]  # a cap per design, not one number
    no_overhead = budget.stage_caps(rates(1.0, overhead=0.0))
    assert caps["n4-U2000"]["gates"] - no_overhead["n4-U2000"]["gates"] == 2 * 5.0 and caps["n4-U2000"]["evaluate"] > no_overhead["n4-U2000"]["evaluate"]  # the start-up is in every cap
    assert budget.cap_for(caps, "train", 4, 2000) == caps["n4-U2000"]["train"]
    with pytest.raises(budget.CapMissing):
        budget.cap_for(caps, "train", 2, 2000)  # a configuration with no entry refuses
    with pytest.raises(budget.CapMissing):
        budget.cap_for(caps, "unknown-stage", 4, 2000)
    # the stages of the plan project to less than twice themselves: the total registered run fits the sum of the caps
    assert sum(sec.values()) <= sum(caps["n4-U2000"].values())


def test_projection_record_is_labelled_analytical() -> None:
    r = rates(scale_for(10.0, 4, 2000))
    d = budget.rehearsal_rule(3.5, r, 36.0)
    rec = budget.projection_record(3.5, r, d)
    assert "analytical" in rec["type"] and "analytical" in rec["decision"]["type"] and rec["rates"]["calibrated_layer"] == 4
    assert budget.Rates.from_json(rec["rates"]) == r
