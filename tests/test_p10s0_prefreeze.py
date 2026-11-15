# ruff: noqa: E501
"""P10S0 tests for the pre-freeze audit's findings: Q1 refuses before the gates without writing its start record (F3), the Q1 gate needs Q1's manifests (F3), the caps read the generation time from the config (F9), the A2
pre and post records are matched by phase (F10), the registered guard of ``work rehearse-cell`` (F11), this run directory's stages in the pre-Q1 count (F8), the informational booleans of the projection against the
cap in the config (F4), the e2e scaling from the cap (F2), the measurement of the analysis and report times, and that no S0 test reads the value of ``cap_hours`` in the real config (F1). Throwaway directories only;
test seeds 920001-920999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9 import pool  # noqa: E402
from studies.p10s0 import budget, core, stages  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = 3600.0


class Reached(Exception):
    pass


def args_for(tmp_path: Path) -> argparse.Namespace:
    ns = stages.build_parser().parse_args(["gates", "--dry", "--run-dir", str(tmp_path / "run"), "--experiments-root", str(tmp_path / "exp")])
    ns.mode = stages.DRY
    (tmp_path / "run").mkdir(exist_ok=True)
    return ns


PROJECTION: dict[str, Any] = {"table": {"q1:full": {"total_seconds": 10.0}, "q1:cut3": {"total_seconds": 7.0}}, "memory": {"q1:full": {"ok": True}, "q1:cut3": {"ok": True}}}
CAPS: dict[str, Any] = {"analysis": 60.0, "report": 60.0, "q1": {"full": {"train": 5.0, "evaluate": 5.0}, "cut3": {"train": 4.0, "evaluate": 4.0}}}


# --- F3 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_q1_before_the_gates_is_refused_and_leaves_no_start_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ns = args_for(tmp_path)
    run = tmp_path / "run"
    monkeypatch.setattr(stages, "run_block", lambda *a, **k: (_ for _ in ()).throw(Reached()))
    monkeypatch.setattr(stages, "require_draw_plan", lambda _r: {})
    with pytest.raises(pool.StageRefused, match="no gates record"):
        stages.registered_q1(ns, run, {}, CAPS, PROJECTION)
    assert not (run / "q1_start.json").exists()  # q1 launched too early does not leave Q1 refused for good
    core.write_record(run / "gates.json", {**core.envelope("gates"), **syn.passing_gates()})
    with pytest.raises(Reached):
        stages.registered_q1(ns, run, {}, CAPS, PROJECTION)
    assert json.loads((run / "q1_start.json").read_text())["cut3"] is False
    with pytest.raises(pool.StageRefused, match="already started"):
        stages.registered_q1(ns, run, {}, CAPS, PROJECTION)


def test_a_failed_gate_also_leaves_no_start_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ns = args_for(tmp_path)
    run = tmp_path / "run"
    monkeypatch.setattr(stages, "require_draw_plan", lambda _r: {})
    core.write_record(run / "gates.json", {**core.envelope("gates"), **syn.passing_gates(), "g4_passed": False})
    with pytest.raises(pool.StageRefused, match="did not pass"):
        stages.registered_q1(ns, run, {}, CAPS, PROJECTION)
    assert not (run / "q1_start.json").exists()


def test_the_q1_gate_refuses_before_q1_has_finished_without_writing_its_record(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["q1-gate", "--run-dir", str(tmp_path), "--mode", "check"])
    with pytest.raises(pool.StageRefused, match="train-q1"):
        stages.cmd_q1_gate(ns)
    (tmp_path / "train-q1").mkdir()
    (tmp_path / "train-q1" / "manifest.json").write_text("{}")
    with pytest.raises(pool.StageRefused, match="evaluate-q1"):
        stages.cmd_q1_gate(ns)
    assert not (tmp_path / "q1_gate.json").exists()


# --- F9 ----------------------------------------------------------------------------------------------------------------------------------------------
def projection_file(tmp_path: Path) -> Path:
    rates = {item: budget.Rate(0.01, 1, 1, 1.0) for item in budget.rehearsal_items()}
    record = {**core.envelope("projection"), "rates": {budget.item_label(i): r.__dict__ for i, r in rates.items()}, "unit_updates": core.UPDATES}
    path = tmp_path / "projection.json"
    core.write_record(path, record)
    return path


def test_caps_read_the_generation_time_from_the_config_and_refuse_a_typed_mismatch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    cfg = repo / core.DEFAULT_CONFIG
    base = ["caps", "--repo", str(repo), "--projection", str(projection_file(tmp_path)), "--gates-wall-seconds", "10", "--gates-per-draw-seconds", "1", "--analysis-wall-seconds", "1", "--report-wall-seconds", "1"]
    cfg.write_text(core.render_config_toml())  # provisional
    assert stages.main([*base, "--out", str(tmp_path / "c0.json")]) == 2 and "provisional" in capsys.readouterr().err
    cfg.write_text(core.render_config_toml(core.set_generation_cap(33.44888391700806)))
    assert stages.main([*base, "--out", str(tmp_path / "c1.json")]) == 0  # nothing typed: the config's measured time
    caps = json.loads((tmp_path / "c1.json").read_text())
    assert caps["measured"]["generate"] == 33.44888391700806 and caps["generate"] == core.generation_block(cfg)["cap_seconds"]
    assert stages.main([*base, "--generate-wall-seconds", "33.455", "--out", str(tmp_path / "c2.json")]) == 2 and "omit it" in capsys.readouterr().err
    assert stages.main([*base, "--generate-wall-seconds", "33.44888391700806", "--out", str(tmp_path / "c3.json")]) == 0  # an identical typed value is accepted


# --- F10 ---------------------------------------------------------------------------------------------------------------------------------------------
def test_the_a2_pre_and_post_records_are_matched_by_phase_and_no_projected_second_changes() -> None:
    def train(phase: str, rate: float) -> dict[str, Any]:
        return {"label": "REH-A2-X", "arm": "A2", "celltype": "2K/4K", "phase": phase, "seconds_per_update": rate, "peak_rss_bytes": 10, "sampled_rss_bytes": 10, "wall_seconds": 1.0}

    def ev(phase: str, seconds: float, peak: int) -> dict[str, Any]:
        return {"label": "REH-A2-X", "phase": phase, "evaluation_wall_seconds": seconds, "peak_rss_bytes": peak}

    trains = [train("pre", 0.5), train("post", 0.25)]
    rates = budget.rates_from_records(trains, [ev("pre", 2.0, 111), ev("post", 3.0, 222)])
    pre, post = rates[("A2", "2K/4K", "pre")], rates[("A2", "2K/4K", "post")]
    assert (pre.evaluation_seconds, pre.evaluation_peak_rss_bytes) == (2.0, 111) and (post.evaluation_seconds, post.evaluation_peak_rss_bytes) == (3.0, 222)
    # what the collision changed: the old rule took the last record of the label for both phases
    collided = {**rates, ("A2", "2K/4K", "pre"): budget.Rate(pre.seconds_per_update, pre.peak_rss_bytes, pre.sampled_rss_bytes, post.evaluation_seconds, post.task_overhead_seconds, post.evaluation_peak_rss_bytes, post.task_peak_rss_bytes)}
    cells = [c for c in core.q1_cells(False) if c.arm == "A2"]
    full = {item: budget.Rate(0.01, 1, 1, 1.0) for item in budget.rehearsal_items()}
    fixed, old = {**full, **rates}, {**full, **collided}
    assert budget.block_projection(cells, fixed) == budget.block_projection(cells, old)  # the projected seconds do not depend on the pre item's evaluation fields: no projected figure changes


# --- F11, F8 -----------------------------------------------------------------------------------------------------------------------------------------
def test_work_rehearse_cell_refuses_a_typed_registered_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(stages.TOKEN_ENV, raising=False)
    monkeypatch.setattr(stages, "repo_of", lambda _a: tmp_path)
    ns = stages.build_parser().parse_args(["work", "rehearse-cell", "--mode", "registered", "--run-dir", str(tmp_path / "run"), "--item", "A0,2K/4K,main"])
    with pytest.raises(pool.StageRefused):
        stages.work_rehearse_cell(ns)


def test_only_this_run_directory_s_stages_count_as_run_before_q1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ns = args_for(tmp_path)
    run = tmp_path / "run"
    ledger = stages.ledger_of(ns)
    ledger.charge("gates", "the-rehearsal-draw-run", 50.0)  # another run's gates
    core.write_record(run / "gates.json", {**core.envelope("gates"), **syn.passing_gates()})
    monkeypatch.setattr(stages, "require_draw_plan", lambda _r: {})
    monkeypatch.setattr(stages, "run_block", lambda *a, **k: (_ for _ in ()).throw(Reached()))
    seen: dict[str, float] = {}
    real = budget.pre_q1_decision

    def spy(charged: float, before: float, *rest: float, **kw: float) -> Any:
        seen["before"] = before
        return real(charged, before, *rest, **kw)

    monkeypatch.setattr(budget, "pre_q1_decision", spy)
    with pytest.raises(Reached):
        stages.registered_q1(ns, run, {"before_q1_projected_seconds": {"gates": 77.0}}, CAPS, PROJECTION)
    assert seen["before"] == 77.0  # the rehearsal draw's gates entry (another run) does not make the registered gates count as run
    (run / "q1_start.json").unlink()
    ledger.charge("gates", run.name, 80.0)  # this run's gates
    with pytest.raises(Reached):
        stages.registered_q1(ns, run, {"before_q1_projected_seconds": {"gates": 77.0}}, CAPS, PROJECTION)
    assert seen["before"] == 0.0


# --- F4 ----------------------------------------------------------------------------------------------------------------------------------------------
def test_the_projection_information_is_computed_against_the_config_cap_and_the_ledger() -> None:
    assert stages.reserve_of.__doc__ and "freeze_information" not in (stages.cmd_projection.__doc__ or "x")
    src = (ROOT / "studies/p10s0/stages.py").read_text(encoding="utf-8")
    assert "PROJECTED_OTHER_HOURS" not in src.split("def cmd_projection")[1].split("def rates_of")[0]  # no design estimate of the other stages
    assert "ledger_of(args).charged()" in src and "core.cap_hours(config_path(args))" in src


# --- F2 ----------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("cap_hours", [16.0, 22.0, 30.0])
def test_the_e2e_scaling_makes_cut_3_apply_at_any_cap(cap_hours: float) -> None:
    from studies.p10s0 import e2e

    rates = {item: budget.Rate(0.01, 1, 1, 1.0, 1.0) for item in budget.rehearsal_items()}
    projection = {"rates": {budget.item_label(i): r.__dict__ for i, r in rates.items()}, "unit_updates": core.UPDATES}
    import dataclasses

    factor = e2e.solve_factor(projection, cap_hours)
    scaled = {k: dataclasses.replace(v, seconds_per_update=v.seconds_per_update * factor) for k, v in rates.items()}
    full = budget.block_projection(core.q1_cells(False), scaled).total_seconds
    cut3 = budget.block_projection(core.q1_cells(True), scaled).total_seconds
    cap = cap_hours * H
    assert full / cap == pytest.approx(e2e.SCALED_Q1_FRACTION_OF_CAP, rel=1e-6)
    d = budget.pre_q1_decision(0.0, 0.0, full, cut3, cap_seconds=cap)
    assert d.action == "cut3"  # 2 x full > cap >= 2 x cut 3, whatever the cap


# --- the measurement of the analysis and report times -------------------------------------------------------------------------------------------------------------------
def test_measure_analysis_writes_both_times_at_the_tiny_unit(tmp_path: Path) -> None:
    code = stages.main(["measure-analysis", "--tiny", "--out", str(tmp_path / "t.json"), "--out-root", str(tmp_path)])
    assert code == 0
    rec = core.read_record(tmp_path / "t.json", "timing")
    assert rec["tiny"] is True and rec["for_caps"] is False and rec["analysis_wall_seconds"] > 0 and rec["report_wall_seconds"] > 0
    assert rec["outcome_rows_reached"] == [1, 2, 3, 4, 5, 6] and rec["registry"]["cells_written"] > 200 and len(rec["registry"]["missing"]) == 3 and rec["registry"]["failed"] and rec["registry"]["non_finite"]
    assert rec["analysis_wall_seconds"] == pytest.approx(rec["analysis_stage_seconds"] + rec["max_row_analysis_seconds"])
    assert not [p for p in tmp_path.iterdir() if p.name.startswith("p10s0-measure-")]  # the registry is deleted
    assert stages.main(["measure-analysis", "--tiny", "--out", str(tmp_path / "t.json"), "--out-root", str(tmp_path)]) == 2  # never over an existing file


def test_the_measurement_registry_has_the_real_number_of_log_lines() -> None:
    from studies.p10s0 import measure

    template = {"update": {"update": 1, "task_loss": 1.0}, "diagnostics": {"update": 4}, "train": {"x": 1}, "eval": {"y": 1}}
    est = measure.expected_bytes(template, core.UPDATES)
    learned = [c for c in [*core.q1_cells(False), *core.wx_cells("A5-D"), *core.probe_cells("A5-D")] if c.learned]
    lines = sum(c.ct.updates(core.UPDATES) for c in learned)
    assert est > lines * len(json.dumps(template["update"], sort_keys=True))  # at least one update line per planned update of every learned cell


# --- F1: no S0 test depends on the value of cap_hours in the real config -------------------------------------------------------------------------------------------------------------
def test_no_s0_test_pins_the_value_of_the_real_config_s_hour_cap() -> None:
    """A test may read ``core.cap_hours()`` but not assert its value, and the ADR's worked examples of a 16-hour cap pass that cap explicitly (``cap_seconds=``)."""
    for path in sorted((ROOT / "tests").glob("test_p10s0_*.py")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"core\.cap_hours\(\)\s*(==|!=|<|>)\s*[0-9]", text), path.name
        assert not re.search(r"cap_seconds\s*==\s*16", text), path.name
    # the worked examples of ADR section 10.4 hold at 16 hours exactly and are independent of the config
    assert budget.holds(0.0, [0.8 * H, 3.89 * H], 16 * H) and not budget.holds(0.0, [0.8 * H, 8.1 * H], 16 * H)
