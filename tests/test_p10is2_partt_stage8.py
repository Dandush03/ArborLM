# ruff: noqa: E501
"""P10IS2 Part T: the independent recomputation, the timing benchmark's stage body and the cost-recording stage on a tiny trained world (ADR-0025 sections 8.5, 8.6, 10). CPU; the numbers mean nothing. Self-check only."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402
from test_p10is2_partt_e2e import fake_gloss_bank  # noqa: E402

from studies.p10is2 import (  # noqa: E402
    cost,
    partt_cost,
    partt_real,
    partt_recompute,
    partt_run,
    partt_timing,
)
from studies.p10is2.common import core  # noqa: E402


@pytest.fixture(scope="module")
def trained(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    d = tmp_path_factory.mktemp("stage8")
    w = world(updates=2)
    recs = partt_run.train_all(w, d / "snapshots", None, 2)
    gloss = fake_gloss_bank(w)
    reg, side = partt_run.score_all(w, d / "snapshots", gloss)
    comb = partt_run.combined_all(w, d / "snapshots")
    return w, d, recs, gloss, reg, side, comb


# --- the recomputation ---------------------------------------------------------------------------------------------------------------------------
def rep0(values):  # type: ignore[no-untyped-def]
    """Only replicate 0 and the references: the recomputation tests re-score one replicate (scoring a whole run again takes minutes on a tiny model)."""
    return {k: v for k, v in values.items() if k.endswith("|0|" + k.split("|", 3)[3]) or k.startswith(("S0|", "TEACHER|"))}


def test_recomputation_is_bit_identical_with_the_frozen_code(trained) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, gloss, reg, side, comb = trained
    rec = partt_recompute.recompute(w, d, gloss, rep0(reg.values), {k: v for k, v in comb.items() if k in ("S0", "ensemble") or k.endswith("|0")}, replicates=(0,))
    assert rec["ok"] and rec["tolerance"] == 0.0 and rec["code"] == "frozen" and rec["differences"] == [] and rec["checked"] == len(rep0(reg.values)) and rec["outcome"] is None


def test_a_difference_is_an_engineering_stop_and_nothing_is_labelled(trained, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, gloss, reg, side, comb = trained
    bad = rep0(reg.values)
    k = "M-append|AB|0|s:E_B"
    bad[k] = bad[k] + 1e-9
    rec = partt_recompute.recompute(w, d, gloss, bad, None, replicates=(0,))
    assert not rec["ok"] and rec["outcome"] == "ENGINEERING STOP — RECOMPUTATION" and rec["differences"][0]["key"] == k and rec["differences"][0]["registered"] == bad[k]  # both values and the cell are recorded
    partt_recompute.write(tmp_path, rec)
    with pytest.raises(core.StageRefused, match="ENGINEERING STOP — RECOMPUTATION"):
        partt_real.require_recomputation(tmp_path)  # the analysis refuses: no line, condition or annotation
    own5 = partt_recompute.recompute(w, d, gloss, {**rep0(reg.values), k: reg.values[k] + 5e-7}, None, own_code=True, replicates=(0,))
    assert own5["ok"] and own5["tolerance"] == 1e-6 and own5["code"] == "own"  # the auditor's own code: within 1e-6
    assert not partt_recompute.recompute(w, d, gloss, {**rep0(reg.values), k: reg.values[k] + 2e-6}, None, own_code=True, replicates=(0,))["ok"]
    missing = {kk: v for kk, v in rep0(reg.values).items() if kk != k}
    assert not partt_recompute.recompute(w, d, gloss, missing, None, replicates=(0,))["ok"]  # a key the run has and the registry lacks is a difference


def test_compare_and_combined_means_by_hand() -> None:
    assert partt_recompute.compare({"a": 1.0, "b": 2.0}, {"a": 1.0, "b": 2.0}, 0.0) == []
    d = partt_recompute.compare({"a": 1.0, "c": 3.0}, {"a": 1.0 + 1e-3, "b": 2.0}, 1e-6)
    assert [x["key"] for x in d] == ["a", "b", "c"] and d[0]["difference"] == pytest.approx(1e-3) and d[1]["why"] == "missing on one side"
    assert partt_recompute.compare({"a": float("nan")}, {"a": 1.0}, 1.0)[0]["why"] == "non-finite"


# --- the timing benchmark ------------------------------------------------------------------------------------------------------------------------
class FakeTime:
    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


def test_timing_stage_measures_the_six_arms_alone_and_records_the_first_complete_attempt(trained, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    w, d = trained[0], trained[1]
    rep = partt_timing.make_repetition(w, d / "snapshots", items=3)
    ft = FakeTime()
    out = partt_timing.run_stage(CFG_T, tmp_path / "timing", rep, clock=ft.now, sleep=ft.sleep, load_fn=lambda: 0.3, alive_fn=lambda: [])
    assert out["status"] == "MEASURED" and out["attempt"] == 1 and len(out["record"]["repetitions"]) == 3
    att = json.loads((tmp_path / "timing" / "attempt_1.json").read_text())
    assert set(att["detail_per_arm_seconds"][0]) == {"S0", "M-append", "D-append", "D-seq", "E-table", "R-icl"} and all(v > 0 for v in att["detail_per_arm_seconds"][0].values())
    assert all(r["load_before"]["quiet_seconds"] >= 60.0 and r["load_before"]["alive"] == [] for r in att["repetitions"]) and att["threads"] > 0
    again = partt_timing.run_stage(CFG_T, tmp_path / "timing", rep, clock=ft.now, sleep=ft.sleep, load_fn=lambda: 0.3, alive_fn=lambda: ["other"])
    assert again["status"] == "MEASURED"  # the record exists: nothing is run again, nothing is chosen on figures


def test_timing_refuses_when_anything_is_alive_and_not_measured_needs_the_decision(tmp_path: Path) -> None:
    ft = FakeTime()
    with pytest.raises(core.StageRefused, match="runs alone"):
        partt_timing.run_stage(CFG_T, tmp_path / "t1", lambda: 1.0, clock=ft.now, sleep=ft.sleep, load_fn=lambda: 0.1, alive_fn=lambda: ["python -m studies.p10ir"])
    d = tmp_path / "t2"
    d.mkdir()
    for i in range(5):
        (d / f"attempt_{i + 1}.json").write_text(json.dumps({"status": "INCOMPLETE ATTEMPT", "repetitions": [{"seconds": 1.0}], "reason": "busy"}))
    with pytest.raises(core.StageRefused, match="recorded decision"):
        partt_timing.run_stage(CFG_T, d, lambda: 1.0, clock=ft.now, sleep=ft.sleep, load_fn=lambda: 0.1, alive_fn=lambda: [])
    (d / partt_timing.DECISION_FILE).write_text("The lead records NOT MEASURED after five attempts.")
    out = partt_timing.run_stage(CFG_T, d, lambda: 1.0, clock=ft.now, sleep=ft.sleep, load_fn=lambda: 0.1, alive_fn=lambda: [])
    assert out["status"] == "NOT MEASURED" and "lead" in out["decision"]
    d3 = tmp_path / "t3"
    d3.mkdir()
    busy = FakeTime()
    out3 = partt_timing.run_stage(CFG_T, d3, lambda: 1.0, clock=busy.now, sleep=busy.sleep, load_fn=lambda: 9.0, alive_fn=lambda: [])  # never quiet: an incomplete attempt, bounded
    assert out3["status"] == "RESCHEDULE" and json.loads((d3 / "attempt_1.json").read_text())["status"] == "INCOMPLETE ATTEMPT" and busy.t <= 30 * 60 + 10


# --- cost ---------------------------------------------------------------------------------------------------------------------------------------------
def test_cost_stage_writes_the_five_measures_each_with_the_note(trained, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    w, d, recs, gloss, reg, side, comb = trained
    cells = tmp_path / "tasks" / "train"
    cells.mkdir(parents=True)
    for label, r in recs.items():
        (cells / (label.replace("/", "_") + ".cell.json")).write_text(json.dumps({**r, "wall_seconds": r["wall_seconds"]}))
    rec = partt_cost.record(w, tmp_path, None, d / "snapshots")
    assert set(rec) >= {"teacher_inference", "student_training", "footprint", "active_work", "counted_training", "timing"} and rec["teacher_inference"]["note"] == "not recorded" and rec["timing"]["status"] == "not yet measured"
    assert set(rec["student_training"]) >= {"M1", "M-append", "M-ii", "D1", "D-append", "D-joint", "E-table"} and rec["student_training"]["M-joint"]["updates"] == 4
    assert rec["footprint"]["lora_rank_single"] == 2 * 2 * (w.cfg.width + w.cfg.width) * 0 + rec["footprint"]["lora_rank_single"]
    c = rec["counted_training"]["per_update"]
    assert c["D-append"]["total"] > c["D1"]["total"] and c["M-append"]["forward"] > c["M1"]["forward"] and c["M-ii"]["total"] > c["M-append"]["total"]
    text = partt_cost.lines(rec)
    assert text and all(cost.COST_NOTE in ln or ln.startswith("footprint") and cost.COST_NOTE in ln for ln in text if not ln.startswith("timing")) and any(ln.startswith("timing benchmark") and cost.COST_NOTE in ln for ln in text)
    assert not any("TRAINING COST COMPARABLE" in ln for ln in text)
    partt_cost.write(tmp_path, rec)
    assert (tmp_path / "cost.txt").read_text().startswith(core.ORACLE_LINE) and (tmp_path / "cost.json").is_file()


def test_teacher_inference_from_a_part_q_ledger(tmp_path: Path) -> None:
    (tmp_path / "generation").mkdir()
    (tmp_path / "generation/result.json").write_text(json.dumps({"counts": {"A": 400, "B": 600}}))
    led = core.Ledger(tmp_path / "charged_ledger.json", "Q", 1e9)
    led.charge_process("generation", "r", "w", 300.0)
    led.charge_process("qfit", "r", "w", 99.0)
    r = partt_cost.teacher_inference(tmp_path)
    assert r["seconds_per_accepted_item"] == pytest.approx(0.3) and r["accepted_items"] == 1000


def test_d_append_counts_its_frozen_adapter_once_in_the_backward_pass() -> None:
    tiny = cost.StudentShape(width=8, layers=2, heads=2, kv_heads=1, intermediate=16, vocab=32)
    a = cost.training_multiply_adds(tiny, "lora", batch=1, mean_len=1.0, lora_rank=2)
    b = cost.training_multiply_adds(tiny, "lora", batch=1, mean_len=1.0, lora_rank=2, frozen_lora_rank=2)
    extra = sum(i * o for _, i, o in cost.lora_maps(tiny, 2))
    assert b["forward"] - a["forward"] == 2 * extra and b["backward"] - a["backward"] == 2 * extra  # forward once, input gradient once, per block
