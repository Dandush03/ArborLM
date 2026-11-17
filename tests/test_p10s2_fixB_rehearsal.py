# ruff: noqa: E501
"""P10S2 audit-fix tests, lane B: the rehearsal measures what the registered stages do (audit B M5, M6, M7) and scores calibration items only, scaling by registered item counts (audit A M3, the lead's ruling):
rates from the training records of the registered stage function, the scale factor, the rehearsal world, the pre-freeze gates stage on the rehearsal world, synthetic records of the whole registry for the analysis
and report stages. The full measure (`measure_rates` with its child processes) is tested in ``test_p10s2_dry.py``. Stand-in world and test seeds. Self-check only: not independent review, not Astra
validation, not human approval."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10s2_classes import study  # noqa: E402
from test_p10s2_support import dry_world  # noqa: E402

from studies.p10s2 import budget, cells, core, evaluate, rehearsal, stages  # noqa: E402
from studies.p10s2.registry import replicate_cells  # noqa: E402


def records(sec: float = 0.5) -> dict[str, dict[str, Any]]:
    return {c.label: {"label": c.label, "status": "completed", "train": [{"seconds_per_update": sec * (2 if c.variant in ("BA", "B") else 1)}]} for c in replicate_cells(0)}


def test_rates_come_from_the_training_records_of_every_group_and_take_the_slowest_variant() -> None:
    r = rehearsal.rates_from_records(records(0.5), 4)
    assert set(r) == {f"{g}@L4" for g in ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD", "ETABLE")} | {"LORA1", "LSEQ", "LJOINT"}  # E-table is store-type: its rate is keyed by the layer
    assert r["ST1@L4"] == 1.0 and r["ETABLE@L4"] == 1.0 and r["LORA1"] == 1.0 and r["MJOINT@L4"] == 0.5  # the BA / B variant is twice as slow: the slowest variant counts
    assert rehearsal.rate_key("ETABLE", 12) == "ETABLE@L12" and rehearsal.rate_key("LORA1", 12) == "LORA1" and set(budget.STORE_TYPE_GROUPS) >= {"ETABLE"}
    bad = records()
    bad["r0/ST1/AB"] = {"label": "r0/ST1/AB", "status": "failed", "train": [{"error": "device error"}]}
    with pytest.raises(rehearsal.RehearsalFailed, match="device error"):
        rehearsal.rates_from_records(bad, 4)  # a rehearsal cell that fails stops the rehearsal: no rate is invented


def test_both_rehearsed_layers_give_the_slower_rate_for_u_1000_including_e_table() -> None:
    a, b = rehearsal.rates_from_records(records(0.5), 4), rehearsal.rates_from_records(records(0.9), 12)
    rt = budget.Rates({**a, **b}, 4, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
    assert budget.group_rate("ETABLE", rt, None, slower=True) == 1.8 and budget.group_rate("ETABLE", rt, None, slower=False) == 1.0  # E-table at U = 1,000: the slower of L = 4 and L = 12
    assert budget.reduced_updates(1000) and not budget.reduced_updates(2000)


def test_the_scale_factor_is_the_registered_item_count_over_the_rehearsal_item_count_and_never_below_one() -> None:
    world, _ = dry_world()
    s = rehearsal.scale_factor(world)
    reg = sum(len(p.examples) for p in world.ctx.panels.values())  # E_A, E_B and E_open_A, E_open_B (re-check B, N1)
    cal = sum(len(world.d_cal[p.task].examples) for p in world.ctx.panels.values())
    assert s == max(1.0, reg / cal) and s >= 1.0


def test_the_rehearsal_world_scores_calibration_items_in_place_of_every_evaluation_panel() -> None:
    world, _ = dry_world()
    rw = rehearsal.rehearsal_world(world)
    assert rw.ctx.panels["E_A"] is world.d_cal["A"] and rw.ctx.panels["E_B"] is world.d_cal["B"]  # D_cal under the names the scoring code reads
    assert rw.ctx.panels["E_A"] is not world.ctx.panels["E_A"] and world.ctx.panels["E_A"].name == "E_A"  # the original world is untouched
    assert [i.key for i in rw.partition.panels["E_C"]] == [i.key for i in world.partition.panels["D_cal"]]
    assert rw.teacher_outputs["A"]["E_A"] == world.teacher_outputs["A"]["D_cal"]


def test_the_prefreeze_gates_stage_scores_calibration_items_only_and_scales_the_scoring_parts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from studies.p10s2.stages import gate_inputs, manifest_gates

    world, pre = dry_world()
    names: set[str] = set()
    real = evaluate.score_panel

    def spy(ctx: Any, arm: Any, panel: Any, *a: Any, **k: Any) -> Any:
        names.add(panel.name)
        return real(ctx, arm, panel, *a, **k)

    monkeypatch.setattr(evaluate, "score_panel", spy)
    monkeypatch.setattr(cells, "score_panel", spy)
    g1, g3 = gate_inputs(world, pre)
    rec = rehearsal.time_prefreeze_gates(world, tmp_path, g1, g3, None, {}, tmp_path, updates=2, require_mps=False)
    assert not names & {"E_A", "E_B", "E_C", "E_open"} and {"D_cal_A", "D_cal_B"} <= names  # no evaluation panel is scored and no gap on one is computed before the freeze
    assert set(rec["gates"]) >= {f"G{i}" for i in range(1, 10)} and rec["scale"] >= 1.0
    assert rec["seconds_scaled_to_registered_panels"] >= rec["seconds_measured"] > 0 and rec["scaled_parts"]["g2_seconds"] > 0 and "scaled by item counts" in rec["type"]
    assert rec["gates"]["G7"]["ok"] is False and rec["ok"] is False  # no manifest was given: G7 cannot pass on none (and nothing here is a result)
    assert manifest_gates  # the stage passes the creation-time manifest of the bundle


def test_synthetic_records_of_the_whole_registry_run_through_the_real_analysis_and_report_stages(tmp_path: Path) -> None:
    s = study(n=1)
    src = tmp_path / "src"
    src.mkdir()
    (src / "r0.json").write_text(__import__("json").dumps(s["replicates"][0]))
    (src / "baseline.json").write_text(__import__("json").dumps(s["baseline"]))
    meta = rehearsal.synthetic_registry_run(src, tmp_path / "synth", 2000)
    assert len(meta["injected"]) == 4 and meta["design"] == {"replicates": 4, "updates": 2000, "synthetic": True}
    kinds = " | ".join(meta["injected"])
    assert "missing cell" in kinds and "rejected consolidation" in kinds and "inertia cell" in kinds and "non-finite value" in kinds  # the cases the ADR names
    for r in range(4):
        assert (tmp_path / "synth" / "evaluate" / f"r{r}.json").exists() and (tmp_path / "synth" / "recompute" / f"r{r}.json").exists()
    import json

    assert "r1/MAF/AB" not in json.loads((tmp_path / "synth" / "evaluate" / "r1.json").read_text())["cells"] and "r0/MAF/AB" in json.loads((tmp_path / "synth" / "evaluate" / "r0.json").read_text())["cells"]
    out = stages.stage_analysis(tmp_path / "synth", meta["design"], meta["prefreeze"])
    assert out["label"] in ("INCOMPLETE", "ENGINEERING-FAILURE") and out["recomputation"]["state"] in ("complete", "incomplete")  # the missing cell makes the synthetic study INCOMPLETE: a mechanics check, not a result
    text = stages.stage_report(tmp_path / "synth")
    assert core.ORACLE_LINE in text and "Astra review: NOT_PERFORMED" in text
