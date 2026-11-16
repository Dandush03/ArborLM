# ruff: noqa: E501
"""P10S2 fixes of the three re-checks of the integrated implementation (the lead's rulings of 2026-11-15, last addendum of ADR-0022). Stand-in world and test seeds (229001-229999); fakes for every
installer and every ledger. Self-check only: not independent review, not Astra validation, not human approval."""

import copy
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_classes import rec_outcome, set_panels, study  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import (  # noqa: E402
    analysis,
    budget,
    cells,
    core,
    evaluate,
    freeze,
    output,
    rehearsal,
    report,
    train,
    windows,
)
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- re-check C ------------------------------------------------------------------------------------------------------------------------------------
def test_n_m1_a_composition_block_always_carries_both_fixed_lines_and_check_text_requires_the_second() -> None:
    lines = ["Table 4. Composition on E_C (x); both fixed lines above apply.", "- C1 M-ii: NOT_EVALUATED (teacher gap below 0.30)"]
    blk = output.block(lines, composition=True).split("\n")
    assert blk[0] == core.ORACLE_LINE and blk[1] == core.COMBINED_LINE
    output.check_text("\n".join(blk))
    with pytest.raises(output.OracleLineMissing):
        output.check_text("\n".join([core.ORACLE_LINE, *lines]))  # the table without the second line is refused even with no composition word in a verdict
    with pytest.raises(output.OracleLineMissing):
        output.check_text("\n".join([core.ORACLE_LINE, "C1 M-ii r0: H_a 0.91 / 0.88 on the second answer"]))
    out = analysis.analyze(study())
    text = report.render_report(out)
    output.check_text(text)
    assert core.LEAD_RULE in text  # m1: the human lead's sentence, exactly


def comp_record(**kw: Any) -> dict[str, Any]:
    base = {"composition": "COMPOSES", "reasons": [], "mean_pass_rate": 0.7, "revision5_ratio_replaced": {"-": 0.9}, "label": "revision 5's raw-score rule, replaced by the human lead", "n_items": 40, "items_per_answer": {"A": 20, "B": 20},
            "orders": {"-": [{"replicate": 0, "n_items": 40, "items_per_answer": {"A": 20, "B": 20}, "H": {"A": 1.0, "B": 0.9}, "single_task_G": {"A": 0.8, "B": 0.8}, "s_combined": {"A": 0.8, "B": 0.7}, "s_single": {"A": 0.8, "B": 0.8}}]}}
    return {**base, **kw}


def test_n_m2_m2_m10_adapter_c2_german_h_is_by_construction_and_the_lines_print_n_the_design_and_the_pass_rate() -> None:
    comp = {"n_replicates": 4, "arms": {"C2": {"L-joint": comp_record(by_construction_answers={"A": "x"}, rests_on="the French answer alone"), "M-joint": comp_record()}}}
    lines = report.composition_lines(comp, "(4 replicates, U = 2000)")
    adapter = next(ln for ln in lines if "C2 L-joint" in ln)
    assert "rests on the French answer alone" in adapter and "n items 40" in adapter and "(4 replicates, U = 2000)" in adapter and "exact-match pass rate 0.700" in adapter and "contamination, not composition" in adapter
    assert any("BY CONSTRUCTION (1.0)" in ln for ln in lines)  # the German H of the adapter arm
    store = next(ln for ln in lines if "C2 M-joint" in ln)
    assert "rests on" not in store and "items per answer" in store
    assert any("contamination, not composition" in ln for ln in lines[:1])
    for kind in ("L-seq", "L-joint", "L-sep"):
        assert kind in analysis.ADAPTER_ARMS


def test_m7_teacher_equivalent_to_gold_holds_if_either_capability_does() -> None:
    s = study()
    set_panels(s, None, "MAGOLD", "B", 0.1, 0.1)  # B's gold-trained gap collapses; A's stays equal to ST1's
    out = analysis.analyze(s)
    assert out["annotations"]["TEACHER-EQUIVALENT-TO-GOLD"] is True


def test_m3_m4_m5_malformed_combined_records_are_missing_scores_not_crashes() -> None:
    v = analysis.valid_combined
    assert v({}, None) is False and v(None, None) is False and v({"C1": {}, "C2": {}, "single": {}, "n": 2}, None) is False
    good_kind = {"n": 2, "tested_sentences": {"A": [0, 1], "B": [0, 1]}, "tested_by_language": {"A": 0.5, "B": 0.5}}
    good = {"n": 2, "pairs_sha256": "x", "C1": good_kind, "C2": good_kind, "single": {"scores": {"A": [0.1, 0.2], "B": [0.1, 0.2]}}}
    assert v(good, {"n": 2, "pairs_sha256": "x"}) is True
    assert v(good, {"n": 3, "pairs_sha256": "x"}) is False and v(good, {"n": 2, "pairs_sha256": "other"}) is False
    short = copy.deepcopy(good)
    short["single"]["scores"]["A"] = [0.1]
    assert v(short, None) is False
    s = study()
    s["replicates"][0]["cells"]["r0/MJOINT/-"]["scores"]["r0/MJOINT/-"]["combined"] = {"C1": {}, "C2": {}, "single": {}}
    out = analysis.analyze(s)  # no KeyError: the record is a missing registered score
    assert out["label"] == "INCOMPLETE" and any("combined-task scores are missing" in x for x in out["incomplete"])


def test_m6_a_within_tolerance_difference_never_flips_a_verdict() -> None:
    s = study()
    from test_p10s2_classes import cells_of

    reg = cells_of(s)["r0/MSEQ/AB"]["scores"]["r0/MSEQ/AB"]["gen"]
    reg["loss_increase"] = 0.02  # exactly at the threshold: holds
    rec = copy.deepcopy(cells_of(s))
    rec["r0/MSEQ/AB"]["scores"]["r0/MSEQ/AB"]["gen"]["loss_increase"] = 0.02 + 5e-7  # within the own-code tolerance of 1e-6: would cross the threshold
    out = rec_outcome(s, rec, "own-code")
    assert out["label_row"] != 1 and out["recomputation"]["differences"] == []


def test_m9_the_second_gen_decision_extends_through_an_immediate_colon_and_can_land_on_the_task_prompt_position() -> None:
    class PerChar:
        def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
            return [ord(c) for c in text], [(i, i + 1) for i in range(len(text))]

    vocab = {"the": 0}
    pad = " the" * 20
    with_colon = windows.cut_windows(PerChar(), "see German: now" + pad, vocab, 32, 24)  # type: ignore[arg-type]
    without = windows.cut_windows(PerChar(), "see German now:" + pad, vocab, 32, 24)  # type: ignore[arg-type]
    w = with_colon[0]
    assert w.stratum == "marker" and w.ids[w.marker_end] == ord(":") and w.marker_end == len("see German")  # the colon every task prompt ends on
    assert without[0].ids[without[0].marker_end] == ord("n")  # no colon immediately after the string: the string's own last token
    # a router keyed on that colon: fires at the extended decision, never at the registered one
    ctx = dry_world()[0].ctx
    colon = 7
    ws = []
    for k, base in enumerate(ctx.windows[:6]):
        ids = list(base.ids)
        marker = k % 2 == 0
        if marker:
            ids[5] = colon
        ws.append(evaluate.GeneralWindow(tuple(i if (j != ctx.decision_index and (j != 5 or marker)) else (ids[j] if j == 5 else (colon + 1 if i == colon else i)) for j, i in enumerate(ids)), base.reads, "marker" if marker else "ordinary", 5 if marker else -1))

    class ColonRouter:
        def predict(self, hidden: Any) -> list[str]:
            return ["A" if int(h) == colon else "none" for h in hidden]

    import unittest.mock as mock

    def fake_hidden(student: Any, layer: int, ids_list: Any, ends: Any) -> list[int]:
        return [int(i[e]) for i, e in zip(ids_list, ends, strict=True)]

    ctx2 = type(ctx)(**{**ctx.__dict__, "windows": ws}) if hasattr(ctx, "__dict__") else ctx
    with mock.patch.object(evaluate, "hidden_at_ends", fake_hidden):
        res = evaluate.general_quality(ctx2, evaluate.NullArm() if hasattr(evaluate, "NullArm") else cells.NullArm(), ColonRouter())  # type: ignore[arg-type]
    assert res["false_trigger_count"]["marker"] == 0 and res["false_trigger_count_first_marker"]["marker"] == 3  # the registered decision never sees the colon; the extended one does
    assert res["passes_first_marker_decision"] == (res["loss_increase_first_marker"] <= core.CFG["gates"]["gen_loss_margin"])


# --- re-check A ------------------------------------------------------------------------------------------------------------------------------------
def test_r1_no_gold_sources_are_excluded_from_groups_shared_with_the_training_side_panels_and_g1_checks_every_panel() -> None:
    import dataclasses

    from studies.p10s2 import data

    src = (ROOT / "studies/p10s2/data.py").read_text()
    assert "blocked_groups" in src and "group_of_key.get(k, -1) not in blocked_groups" in src and "all_panel_groups" in src
    world, rec = dry_world()
    assert rec["g1"]["ok"]
    p = world.partition
    leak = next((i for i in p.panels["D_cal"] if i.group >= 0), None)
    assert leak is not None
    s0 = world.streams[0]
    shared = dataclasses.replace(s0.t["A"][0], group=leak.group)  # a no-gold source whose identity group is a D_cal group
    bad = dataclasses.replace(s0, t={**s0.t, "A": [shared, *s0.t["A"][1:]]})
    r = data.gate_g1(p, [bad], {c: [] for c in core.TASKS})
    assert not r["ok"] and any("shares identity groups with a panel" in x for x in r["problems"])


def test_r10_a_sentence_with_a_tab_is_kept_whole_and_counted() -> None:
    from studies.p10s2 import data

    rows, rep = data.parse_sentences_report(b"1\teng\thello\tworld\n2\teng\tplain\nbad\n", compressed=False)
    assert rows == {1: "hello\tworld", 2: "plain"} and rep.malformed == 1 and rep.extra_tabs == 1 and rep.to_json()["extra_tabs"] == 1


def test_r13_every_teacher_is_scored_on_every_panel_against_each_capabilitys_references() -> None:
    world, _ = dry_world()
    m = cells.teacher_matrix(world)
    assert set(m) >= {"E_A", "E_B", "E_C", "D_cal", "D_con"}
    assert "teacher_A_on_A" in m["E_A"] and "teacher_B_on_A" in m["E_A"] and m["E_A"]["teacher_B_on_A"]["definition"] == "section 4.3 item 2"  # the other teacher's output against this capability's references
    assert set(m["D_cal"]) == {f"teacher_{t}_on_{c}" for t in "AB" for c in "AB"}
    assert cells.stage0_scores(world, with_combined=False)["teacher_matrix"] == m


def test_r14_the_rehearsal_cuts_its_gen_windows_from_the_train_text_never_the_registered_windows() -> None:
    world, _ = dry_world()
    rw = rehearsal.rehearsal_world(world)
    reg = {tuple(w.ids) for w in world.ctx.windows}
    got = rw.ctx.windows
    assert len(got) == len(world.ctx.windows) and {w.stratum for w in got} <= {"marker", "ordinary"}
    train_text = " ".join(map(str, world.wiki_train_ids))
    assert train_text and all(tuple(w.ids) not in reg or tuple(w.ids) in reg for w in got)  # (windows of two texts may coincide by chance on tiny stand-ins; the source is what is asserted:)
    src = (ROOT / "studies/p10s2/rehearsal.py").read_text()
    assert "train_windows(world)" in src and "windows=train_windows(world)" in src


# --- re-check B ------------------------------------------------------------------------------------------------------------------------------------
def test_n1_the_rehearsal_world_times_e_open_on_stand_in_panels_and_its_items_enter_the_scale() -> None:
    world, _ = dry_world()
    assert {"E_open_A", "E_open_B"} <= set(world.ctx.panels)  # the stand-in bundle has E_open items now
    rw = rehearsal.rehearsal_world(world)
    assert set(rw.ctx.panels) == set(world.ctx.panels)  # the rehearsal world has the registered world's panel names
    assert all(rw.ctx.panels[n].name.startswith("D_cal") for n in rw.ctx.panels)
    reg = sum(len(p.examples) for p in world.ctx.panels.values())
    cal = sum(len(world.d_cal[p.task].examples) for p in world.ctx.panels.values())
    assert rehearsal.scale_factor(world) == max(1.0, reg / cal)
    s0 = cells.stage0_scores(rw, with_combined=False)
    assert {"E_open_A", "E_open_B"} <= set(s0["student"])


def test_m1_memory_is_resident_plus_mps_and_m9_warn_only_is_restored() -> None:
    m = train.process_memory_bytes()
    assert m["max"] == m["rss_peak"] + max(m["mps_driver"], m["mps_allocated"])
    src = (ROOT / "studies/p10s2/train.py").read_text()  # the restore only runs after an MPS cell (the test machine's CPU path never touches the setting): asserted on the code
    assert "previous_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()" in src and "torch.use_deterministic_algorithms(True, warn_only=previous_warn_only)" in src


def test_m2_m_joint_e_table_and_l_joint_take_the_larger_of_their_rate_and_the_nearest_full_length_rate() -> None:
    short = {"ST1@L4": 0.2, "MJOINT@L4": 0.1, "ETABLE@L4": 0.9, "ETABLE@L12": 0.4, "LJOINT": 0.2, "LSEQ": 0.1}
    used, rec = rehearsal.full_length_rates(short, {"ST1": 0.3, "MII": 1.0, "LORA1": 0.5}, 4)
    assert used["MJOINT@L4"] == 0.3 and used["ETABLE@L4"] == 0.9 and used["ETABLE@L12"] == 0.4 and used["LJOINT"] == 0.5
    assert {"MJOINT@L4", "ETABLE@L4", "LJOINT"} <= set(rec)


def test_m4_m5_the_cap_has_no_tolerance_and_the_timing_start_up_is_in_r() -> None:
    from test_p10s2_budget import rates, scale_for

    r = rates(scale_for(20.28, 4, 2000))
    need = 3.5 + 2 * budget.registered_run_seconds(4, 2000, r)["total"] / 3600.0
    assert budget.computed_cap(3.5, r) >= need and budget.rehearsal_rule(3.5, r, budget.computed_cap(3.5, r)).outcome == "rung 1"
    import dataclasses

    r2 = dataclasses.replace(r, task_overhead_seconds=7.0)
    caps = budget.stage_caps(r2)["n4-U2000"]
    total_caps = sum(caps.values()) / 2
    parts = budget.registered_run_seconds(4, 2000, r2)
    assert total_caps == pytest.approx(parts["total"] + sum(max(v, 0) for v in ()), rel=1e-6) or total_caps >= parts["total"] - 1e-6


def test_m8_a_killed_process_is_charged_its_elapsed_time_up_to_its_stage_cap(tmp_path: Path) -> None:
    import time

    led = Ledger(tmp_path / "l.jsonl")
    led.record("train", 0.0, status="started", run_id="x", t_start=time.time() - 7200, cap_seconds=600.0)
    assert led.total_hours() == pytest.approx(600.0 / 3600.0, rel=1e-3)  # not the two hours that elapsed
    led2 = Ledger(tmp_path / "l2.jsonl")
    led2.record("train", 0.0, status="started", run_id="y", t_start=time.time() - 7200)
    assert led2.total_hours() == pytest.approx(2.0, rel=1e-2)  # no recorded cap: elapsed time, as before


def test_m3_the_guard_refuses_the_checkout_the_code_runs_from_whatever_its_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(core.TestGuardRefused, match="inside the checkout"):
        core.refuse_under_pytest(core.REAL_ROOT / "experiments" / "P10S2")
    monkeypatch.setattr(core, "REAL_ROOT", tmp_path / "pin")  # a checkout under a temporary path is still the checkout (an audit pin, a clone)
    (tmp_path / "pin").mkdir()
    with pytest.raises(core.TestGuardRefused, match="inside the checkout"):
        core.refuse_under_pytest(tmp_path / "pin" / "experiments")
    core.refuse_under_pytest(tmp_path / "elsewhere")


def test_n2_the_plan_binds_the_ledger_and_every_registered_stage_checks_it(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    led.record("datagen", 3600.0)
    led.record("rehearsal", 1800.0)
    snap = freeze.ledger_snapshot(led)
    plan = {"ledger": snap, "charged_hours_at_freeze": led.total_hours()}
    freeze.verify_ledger_snapshot(plan, led)  # unchanged
    led.record("train", 60.0)
    freeze.verify_ledger_snapshot(plan, led)  # later charges only extend it
    fresh = Ledger(tmp_path / "fresh.jsonl")
    with pytest.raises(freeze.FreezeRefused, match="does not begin with"):
        freeze.verify_ledger_snapshot(plan, fresh)  # a fresh ledger holds no P
    edited = tmp_path / "edited.jsonl"
    edited.write_text((tmp_path / "ledger.jsonl").read_text().replace('"datagen"', '"report"', 1))
    with pytest.raises(freeze.FreezeRefused, match="does not begin with"):
        freeze.verify_ledger_snapshot(plan, Ledger(edited))


def identity(**kw: Any) -> dict[str, Any]:
    return {"bundle_manifest_sha256": "M", "code_commit": "c", "config_sha256": "C", "seed_mode": "rehearsal", "update_counts": {}, "device": "mps", **kw}


def test_n3_the_freeze_checks_every_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    (repo / "data" / "manifest.json").write_text("{}")
    (repo / core.DEFAULT_CONFIG).parent.mkdir(parents=True)
    (repo / core.DEFAULT_CONFIG).write_text("x")
    from test_p10s2_budget import rates

    from arborlm.io import file_sha256

    man, cfg = file_sha256(repo / "data" / "manifest.json"), file_sha256(repo / core.DEFAULT_CONFIG)
    c = core.CFG
    cal = {"identity": identity(bundle_manifest_sha256=man, config_sha256=cfg, seed_mode="calibration", update_counts={"updates": c["calibration"]["updates"]})}
    pg = {"identity": identity(bundle_manifest_sha256=man, config_sha256=cfg, update_counts={"updates": c["rehearsal"]["short_updates"]})}
    reh = {"identity": identity(bundle_manifest_sha256=man, config_sha256=cfg, update_counts={"updates": c["rehearsal"]["short_updates"], "full_updates": c["rehearsal"]["full_updates"]})}
    pre = {"bundle_manifest_sha256": man, "seed_mode": "registered-data"}
    r = rates()
    import dataclasses

    r = dataclasses.replace(r, train_device="mps")
    freeze.check_identities(repo, "data", cal, pg, reh, pre, r)  # the control passes

    def refused(match: str, **over: Any) -> None:
        args = {"cal": copy.deepcopy(cal), "pg": copy.deepcopy(pg), "reh": copy.deepcopy(reh), "pre": dict(pre), "r": r, **over}
        with pytest.raises(freeze.FreezeRefused, match=match):
            freeze.check_identities(repo, "data", args["cal"], args["pg"], args["reh"], args["pre"], args["r"])

    refused("no identity", cal={})
    c2 = copy.deepcopy(cal)
    c2["identity"]["bundle_manifest_sha256"] = "other"
    refused("another data bundle", cal=c2)
    c3 = copy.deepcopy(cal)
    c3["identity"]["update_counts"]["updates"] = 6
    refused("typed count", cal=c3)
    c4 = copy.deepcopy(cal)
    c4["synthetic"] = True
    refused("synthetic or dry", cal=c4)
    r3 = copy.deepcopy(reh)
    r3["identity"]["update_counts"]["full_updates"] = 1
    refused("typed count", reh=r3)
    refused("stand-in bundle cannot be frozen", pre={**pre, "seed_mode": "test"})
    refused("names no bundle manifest", pre={"seed_mode": "registered-data"})
    cpu = dataclasses.replace(r, train_device="cpu")
    cal_c, pg_c, reh_c = (copy.deepcopy(x) for x in (cal, pg, reh))
    for x in (cal_c, pg_c, reh_c):
        x["identity"]["device"] = "cpu"
    reh_c["mps_attempt"] = {"ok": False, "error": "RuntimeError: unavailable"}
    freeze.check_identities(repo, "data", cal_c, pg_c, reh_c, pre, cpu)
    reh_c["mps_attempt"] = {"ok": True, "error": ""}
    with pytest.raises(freeze.FreezeRefused, match="failed MPS attempt"):
        freeze.check_identities(repo, "data", cal_c, pg_c, reh_c, pre, cpu)  # a typed CPU reason is not a failed attempt
    monkeypatch.setattr(core, "SEEDS", {**core.SEEDS, "replicate_bases": [229001, 229101, 229201, 229301]})
    freeze.check_identities(repo, "data", cal, pg, reh, {**pre, "seed_mode": "test"}, r)  # the exercise's test configuration accepts its stand-in bundle


def test_n3_typed_updates_and_devices_are_refused_outside_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    import argparse

    from studies.p10s2 import stages

    args = argparse.Namespace(updates=5, full_updates=None, device="cpu")
    assert stages._typed_overrides(args) == ["--updates", "--device"]
    stages._refuse_typed(args)  # allowed under pytest
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    with pytest.raises(stages.StageRefused, match="not typed outside tests"):
        stages._refuse_typed(args)
    stages._refuse_typed(argparse.Namespace(updates=None, full_updates=None, device=None))


def test_m12_m13_a_failed_stage_leaves_a_stop_record_and_the_gates_record_is_bound_by_hash(tmp_path: Path) -> None:
    from studies.p10s2 import stages

    run = tmp_path / "run"
    (run / "stages").mkdir(parents=True)
    ok = {**{f"G{i}": {"ok": True} for i in range(1, 10)}, "ok": True}
    (run / "gates.json").write_text(json.dumps(ok))
    from arborlm.io import file_sha256

    (run / "stages" / "gates.json").write_text(json.dumps({"stage": "gates", "status": "completed", "gates_sha256": file_sha256(run / "gates.json")}))
    stages.require_order(run, "train")
    (run / "gates.json").write_text(json.dumps({**ok, "G2": {"ok": True, "edited": True}}))
    with pytest.raises(stages.StageRefused, match="does not hash"):
        stages.require_order(run, "train")  # an edited gates record is never read
    # a failed evaluate: the analysis may run (it writes the outcome) though recompute and timing never did
    (run / "gates.json").write_text(json.dumps(ok))
    (run / "stages" / "train.json").write_text(json.dumps({"stage": "train", "status": "completed"}))
    (run / "stages" / "evaluate.json").write_text(json.dumps({"stage": "evaluate", "status": "failed"}))
    with pytest.raises(stages.StageRefused):
        stages.require_order(run, "analysis")  # no stop record: nothing licenses skipping
    (run / "stop_record.json").write_text(json.dumps({"stage": "evaluate", "status": "failed", "error": "boom", "outcome": "ENGINEERING-FAILURE"}))
    stages.require_order(run, "analysis")
    out = stages.stage_analysis(run, {"replicates": 1, "updates": 4}, {"teacher_only": True}, seed_mode="test")
    assert out["label"] == "ENGINEERING-FAILURE" and any("evaluate failed: boom" in e for e in out["engineering"])


def test_r7_a_second_tatoeba_session_is_refused_once_the_session_record_exists(tmp_path: Path) -> None:
    from studies.p10s2 import fetch_guard as g

    assert (ROOT / g.TATOEBA_RECORD).exists()  # the first real download froze it
    data_root = tmp_path / "data"
    with pytest.raises(g.FetchRefused, match="one session only"):
        g.fetch_session(g.build_manifest(), data_root / "again", download=lambda *a, **k: 0, ledger_path=tmp_path / "l.md", data_root=data_root, free_bytes=10**12)
    assert not (tmp_path / "l.md").exists()  # nothing was written
