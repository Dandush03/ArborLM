# ruff: noqa: E501
"""P10S2 tiny synthetic end-to-end ``dry`` stage, the frozen-data round trip, the rehearsal and calibration plumbing, and the stage cap, all on synthetic stand-ins and test seeds. Nothing here is a
calibration, a pilot, a rehearsal or a registered stage, and no number is a result. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import (  # noqa: E402
    analysis,
    budget,
    calibration,
    cells,
    core,
    output,
    rehearsal,
    report,
    stages,
    standins,
)
from studies.p10s2.worldio import RunConfig, build_world, read_bundle, write_bundle  # noqa: E402

LINE = core.ORACLE_LINE


def test_dry_stage_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    threads, deterministic = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled()
    code = stages.main(["dry", "--run-dir", str(run), "--replicates", "1"])
    cap = capsys.readouterr().out
    assert torch.get_num_threads() == threads and torch.are_deterministic_algorithms_enabled() == deterministic  # the timing benchmark's six threads and the recomputation's setting do not leak into the process
    assert code == 0 and "dry stage complete: gates ok = True" in cap
    for rel in ("gates.json", "train/r0.json", "evaluate/r0.json", "evaluate/baseline.json", "recompute/r0.json", "timing.json", "outcome.json", "REPORT.md", "run_record.json", "ledger.jsonl", "data/manifest.json", "snapshots"):
        assert (run / rel).exists(), rel
    gates = json.loads((run / "gates.json").read_text())
    assert all(gates[g]["ok"] for g in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9")) and gates["ok"] is True
    assert gates["G8"]["ok"] and gates["G8"]["greedy_matches_reference"] and gates["G7"]["checked"] >= 8  # the stand-in student reproduces an independently written reference; the data files are hash-checked
    assert gates["G9"]["source"]["ok"] and gates["G9"]["seeds"]["ok"]
    assert gates["G4"]["two_scorings_bit_identical"] and gates["G4"]["repeated_updates_bit_identical"] and gates["G4"]["snapshot_restore_bit_identical"] and gates["G5"]["c_gate_isolation"]
    # every one of the 18 cells has a record, every snapshot a manifest
    tr = json.loads((run / "train/r0.json").read_text())
    assert len(tr) == 18 and all(v["status"] == "completed" for v in tr.values())
    ev = json.loads((run / "evaluate/r0.json").read_text())
    assert ev["ensemble"]["oracle"] == ev["ensemble"]["teacher_own"]  # the oracle-routed ensemble reproduces each teacher's own score (a difference is ENGINEERING-FAILURE)
    assert set(ev["ensemble"]["learned_router"]) == {"A", "B"} and all(ev["ensemble"]["learned_router"][c] <= ev["ensemble"]["oracle"][c] + 1e-12 for c in "AB")  # behind the learned router a wrong route scores 0
    assert "replicate_overlap" in gates and set(ev["routers"]) == {"A", "B", "AB"} and "diagnostic_first_marker" in ev["routers"]["AB"]
    # the independent recomputation (frozen-code case) found every score bit-identical
    outcome = json.loads((run / "outcome.json").read_text())
    o = outcome["outcome"]
    assert o["recomputation"]["state"] == "complete" and o["recomputation"]["differences"] == [] and o["recomputation"]["not_evaluated_cells"] == []
    assert o["design"]["synthetic"] is True and "(1 replicates, U = 4)" in o["label_with_design"]
    assert outcome["oracle_line"] == LINE and o["oracle_line"] == LINE and all(c["oracle_line"] == LINE for by in o["classes"].values() for c in by.values())
    text = (run / "REPORT.md").read_text()
    output.check_text(text)
    assert text.count(LINE) >= 5 and "oracle-assisted" in text
    # the terminal summary was printed under the line
    assert cap.splitlines()[0] == LINE
    # the ledger charges every process, the second gates stage and the recomputation included
    led = [json.loads(ln) for ln in (run / "ledger.jsonl").read_text().splitlines()]
    assert {e["kind"] for e in led} == {"datagen", "gates-rehearsal", "train", "evaluate", "timing", "recompute", "analysis", "report"} and all(e["charged_hours"] >= 0 for e in led)
    rr = json.loads((run / "run_record.json").read_text())
    assert rr["seeds"]["ok"] and rr["ledger"]["cap_hours"] == 36.0 and rr["ledger"]["charged_hours"] == pytest.approx(sum(e["charged_hours"] for e in led), rel=0.05)
    seeds = {u["seed"] for u in rr["seeds"]["recorded"]}
    assert seeds and all(229001 <= s <= 229999 for s in seeds) and not any(220001 <= s <= 228999 for s in seeds)  # test seeds only: no registered seed was used
    t = json.loads((run / "timing.json").read_text())
    assert "no efficiency claim" in t["type"]


def test_frozen_data_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    bundle, rec = standins.build_synthetic_bundle(1)
    manifest = write_bundle(bundle, tmp_path / "data")
    assert set(manifest["files"]) >= {"student.pt", "tokenizer_table.json", "bank.json", "partition.json", "accepted.json", "windows.json", "teacher_outputs.json", "extra.json"} and all(v["algo"] == "sha256" for v in manifest["files"].values())
    back = read_bundle(tmp_path / "data")
    assert back.vocab == bundle.vocab and [i.key for i in back.panels["E_A"]] == [i.key for i in bundle.panels["E_A"]] and back.max_new == bundle.max_new and back.newline_ids == bundle.newline_ids
    assert [(w.ids, w.reads, w.stratum, w.marker_end) for w in back.windows] == [(w.ids, w.reads, w.stratum, w.marker_end) for w in bundle.windows]
    w1 = build_world(bundle, "test", 1, RunConfig.dry())
    w2 = build_world(back, "test", 1, RunConfig.dry())
    assert core.digest(cells.stage0_scores(w1)) == core.digest(cells.stage0_scores(w2))  # the world rebuilt from the frozen files scores identically
    assert [x.key for x in w1.streams[0].t["A"]] == [x.key for x in w2.streams[0].t["A"]]
    assert rec["g1"]["ok"] and "pools" in rec["g1"]["level"] and rec["qualification"]["ok"]  # pool-level G1 in the data step; the stream level in the gates stage
    # the registered replicate seeds are not observed by the data step
    assert all(u.mode in ("test", "registered-data") for u in core.seed_record())
    # tamper with any file: refused at load (gate G7)
    for name in ("bank.json", "student.pt", "windows.json"):
        p = tmp_path / "data" / name
        old = p.read_bytes()
        p.write_bytes(old + b" ")
        with pytest.raises(ValueError, match="does not hash"):
            read_bundle(tmp_path / "data")
        p.write_bytes(old)
    read_bundle(tmp_path / "data")


def test_a_stage_cap_stops_the_stage_and_the_label_is_incomplete(tmp_path: Path) -> None:
    world, rec = dry_world()
    run = tmp_path / "run"
    dl = stages.Deadline(-1.0)
    with pytest.raises(stages.CapReached):
        dl.check("x")
    out = stages.stage_train(world, run, dl)
    assert len(out["stopped"]) == 1 and "cap" in out["stopped"][0] and not (run / "train" / "r0.json").exists()  # a stage that would exceed its cap is not started
    out = stages.stage_evaluate(world, run, dl)
    assert out["stopped"]
    study = stages.assemble_study(run, {"replicates": 1, "updates": 4}, {"teacher_only": True}, {})
    assert any("a cap stopped the train stage" in x for x in study["incomplete"])
    res = analysis.analyze(study)
    assert res["label"] == "INCOMPLETE" and res["label_row"] == 2
    text = report.render_report(res)
    assert "ACQUIRES-AND-RETAINS" not in text and "TRANSFER-POSITIVE" not in text
    assert stages.Deadline(None).check("anything") is None


# --- rehearsal and calibration plumbing (tiny; not a rehearsal or a calibration) --------------------------------------------------------------------------
def test_rehearsal_measurements_feed_the_rate_rule(tmp_path: Path) -> None:
    world, _ = dry_world()
    bundle, _ = standins.build_synthetic_bundle(1)
    write_bundle(bundle, tmp_path / "data")
    ov = rehearsal.measure_task_overhead(tmp_path / "data")
    assert ov["seconds"] > 0 and ov["peak_bytes"] > 0  # a fresh process: imports, hash-checked load, world build
    rates, raw = rehearsal.measure_rates(world, 0, updates=2, full_updates=5, overhead=ov, timing_items=2)
    assert raw["full_length"]["updates"] == 5.0 and set(raw["full_length"]) >= {"ST1", "MII", "LORA1", "peak_bytes"}  # the full-U store, M-ii and LoRA cells ran
    for g in ("ST1", "MAF", "MSEQ", "MAGOLD"):
        assert raw["update_seconds"][f"{g}@L{world.layer}"] == raw["full_length"]["ST1"] != raw["short_run_update_seconds"][f"{g}@L{world.layer}"]  # the rate comes from the full-length run, not the short one
    assert raw["update_seconds"][f"MII@L{world.layer}"] == raw["full_length"]["MII"] and raw["update_seconds"]["LORA1"] == raw["update_seconds"]["LSEQ"] == raw["full_length"]["LORA1"]
    assert raw["update_seconds"]["ETABLE"] == raw["short_run_update_seconds"]["ETABLE"]  # the other cell types keep their 200-update (here 2-update) rates
    assert set(raw) >= {"update_seconds", "panel_seconds", "replicate_extra_seconds", "fixed_seconds", "timing_seconds", "gates2_seconds"}
    for group in ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD"):
        assert f"{group}@L{world.layer}" in rates.update_seconds and rates.update_seconds[f"{group}@L{world.layer}"] > 0
    for group in ("ETABLE", "LORA1", "LSEQ", "LJOINT"):
        assert rates.update_seconds[group] > 0
    assert rates.task_overhead_seconds == ov["seconds"] and rates.eval_peak_bytes >= rates.train_peak_bytes > 0 and rehearsal.peak_rss_bytes() > 0
    d = budget.rehearsal_rule(0.01, rates, 36.0)
    assert d.outcome == "rung 1" and d.replicates == 4 and d.projections["n4-U2000"] > d.projections["n3-U2000"]  # a tiny world fits any cap
    huge = budget.rehearsal_rule(0.01, budget.Rates({**rates.update_seconds, **{k: v * 1e7 for k, v in rates.update_seconds.items()}}, rates.calibrated_layer, 1e5, 1e5, 1e5, 1e5, 1e5, 1e3), 36.0)
    assert huge.outcome == "NOT STARTED: BUDGET"
    cap = budget.stage_caps(rates)
    assert budget.cap_for(cap, "train", 4, 2000) > budget.training_seconds(4, 2000, rates, slower=False)


def test_calibration_rule_and_pilot_gate() -> None:
    cs = calibration.calibration_cells()
    assert len(cs) == 8 and sum(c.kind == "store" for c in cs) == 4 and {c.setting for c in cs if c.kind == "store"} == {4.0, 12.0} and {c.setting for c in cs if c.kind == "lora"} == {0.0003, 0.001}
    scores = {c.label: 0.5 for c in cs}
    sel = calibration.select(scores)
    assert (sel.read_layer, sel.lora_lr) == (4, 0.0003)  # equal: the first value listed
    scores.update({calibration.CalCell("store", 12.0, c).label: 0.5 + 0.0099 for c in core.TASKS})
    assert calibration.select(scores).read_layer == 4  # a difference below 0.01 goes to the first value listed
    scores.update({calibration.CalCell("store", 12.0, c).label: 0.52 for c in core.TASKS})
    assert calibration.select(scores).read_layer == 12
    scores.update({calibration.CalCell("lora", 0.001, c).label: 0.7 for c in core.TASKS})
    assert calibration.select(scores).lora_lr == 0.001
    assert calibration.select({**scores, calibration.CalCell("store", 4.0, "A").label: 0.3, calibration.CalCell("store", 4.0, "B").label: 0.9}).read_layer == 4  # the MEAN over the two capabilities is compared
    with pytest.raises(ValueError, match="missing or not finite"):
        calibration.select({**scores, cs[0].label: float("nan")})
    with pytest.raises(ValueError):
        calibration.select({k: v for k, v in scores.items() if k != cs[1].label})
    assert calibration.pilot_gate({"A": 0.25, "B": 0.9})["ok"] and calibration.pilot_gate({"A": 0.249, "B": 0.9})["outcome"] == "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"
    assert calibration.pilot_gate({"A": None, "B": 0.9})["failed_capabilities"] == ["A"] and calibration.pilot_gate({"A": 0.5, "B": 0.1})["failed_capabilities"] == ["B"]
    assert "optimistic" in calibration.pilot_gate({"A": 0.5, "B": 0.5})["note"]


def test_calibration_runner_trains_and_scores_the_eight_cells_on_d_cal(monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = dry_world()
    monkeypatch.setitem(calibration.CAL, "read_layers", [0, 1])  # the stand-in student has three blocks
    rec = calibration.run_calibration(world, 0, updates=3, snapshot_updates=2)
    assert len(rec["scores"]) == 8 and len(rec["snapshot_scores"]) == 8 and all(0.0 <= v <= 1.0 for v in rec["scores"].values())
    assert rec["selection"]["read_layer"] in (0, 1) and "optimistic" in rec["pilot"]["note"] and "never reported as results" in rec["note"]
    assert "selection_at_snapshot" in rec and "pilot_at_snapshot" in rec  # the rule and the gate are also applied to the 1,000-update snapshots
    assert set(rec["stage0_d_cal"]) == {"A", "B"} and set(rec["teacher_d_cal"]) == {"A", "B"}


def test_the_dry_world_has_no_registered_data_and_nothing_pending() -> None:
    world, rec = dry_world()
    assert world.mode == "test" and "pending" not in core.CFG
    assert all(not isinstance(p, torch.nn.Parameter) or not p.requires_grad for p in world.student.parameters())
    assert rec["qualification"]["ok"] and rec["sufficiency_after_filter"]["ok"] and rec["sufficiency_pools"]["ok"]
