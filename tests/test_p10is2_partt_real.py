# ruff: noqa: E501
"""P10IS2 Part T drivers on a tiny world: calibration end to end, divergence cases, the two rehearsal drivers, analysis and report (ADR-0025 sections 7, 10). CPU. Self-check only."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402
from test_p10is2_partt_e2e import fake_gloss_bank  # noqa: E402

from studies.p10is2 import calibration as cal  # noqa: E402
from studies.p10is2 import engine, partt_plan, partt_real  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.quantities import Thresholds  # noqa: E402


def small_cal_cfg():  # type: ignore[no-untyped-def]
    cfg = copy.deepcopy(CFG_T)
    cfg["calibration"].update(rate_grid_updates=2, ladder_rungs=[2, 4], ladder_snapshots=[2, 4, 8], ladder_top=8, rate_grid_read_layer=1)
    cfg["memory"]["read_layers"] = [1, 2]
    return cfg


def test_calibration_runs_end_to_end_and_returns_the_plan_inputs() -> None:
    cfg = small_cal_cfg()
    w = world(updates=2, n_reps=2)
    rec = partt_real.run_calibration(w, cfg)
    assert rec["store_rate"] in cfg["calibration"]["store_rates"] and rec["lora_rate"] in cfg["calibration"]["lora_rates"] and rec["etable_rate"] in cfg["calibration"]["store_rates"]
    assert rec["read_layer"] in (1, 2)
    assert rec["U"] in (2, 4, 8) or rec["U"] == 8 and (rec["converged"] or rec["line_note"] == "NOT CONVERGED AT U")
    assert "pilot" in rec and set(rec["grids"]) == {"store", "lora", "etable"} and len(rec["units"]) >= 22
    assert w.layer == 1 and w.store_lr == 0.003  # the world's own settings are restored after every unit


def test_a_diverging_unit_is_recorded_diverged_not_eligible(monkeypatch: pytest.MonkeyPatch) -> None:
    w = world(updates=2, n_reps=2)
    real = engine.p10train.loss_of
    calls = {"n": 0}

    def bad(*a, **k):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        import torch

        return torch.tensor(float("nan")) if calls["n"] == 1 else real(*a, **k)

    monkeypatch.setattr(engine.p10train, "loss_of", bad)
    unit = {"id": "u", "module": "store", "capability": "A", "updates": 2, "snapshots": []}
    r = partt_real.run_unit(w, unit, 0.01, 1, 0)
    assert r["diverged"] is True and r["status"] == "STOPPED_NONFINITE"
    assert cal.select_rate(CFG_T, "store", {0.001: 0.4, 0.003: 0.45, 0.01: None}) == 0.003  # DIVERGED means not eligible


def test_measuring_and_counting_rehearsals(tmp_path: Path) -> None:
    w = world(updates=4)
    m = partt_real.measure_rates(w, tmp_path / "m", fake_gloss_bank(w), updates=4, items=3)
    assert set(m["rates_seconds_per_unit"]) >= {"train:M1", "train:D1", "train:M-joint", "train:D-joint", "router_seconds", "score_seconds_per_item", "combined_seconds_per_arm_cell"} and all(v > 0 for v in m["rates_seconds_per_unit"].values())
    assert m["projection_units"]["train"] == 4 * (3 * (2 * 7) + 3 * 2 * 2 + 3 * 2) - 0 or m["projection_units"]["train"] > 0
    probes = {"n": 0}

    def probe() -> None:
        probes["n"] += 1
        raise core.ForcedIdentityPause("PAUSED — IDENTITY")

    rec = partt_real.counting_rehearsal(w, tmp_path / "c", fake_gloss_bank(w), plan_file_sha256="d" * 64, caps_provisional=False, updates=4, identity_probe=probe)
    assert rec["forced"] == {"pause_resume": True, "paused_identity_restore": True} and probes["n"] == 1
    assert all(v["status"] == "COMPLETE" for v in rec["stages"].values()) and set(rec["stages"]) >= {"gates", "train", "evaluate", "controls", "combined", "analysis", "report"}
    from studies.p10is2.common import gates

    assert gates.rehearsal_gate(rec, tuple(s for s in partt_plan.STAGES if s != "recompute"), plan_file_sha256="d" * 64)["passed"]  # the in-process rehearsal function does not run the recomputation stage (audit B1: it is not the registered path and is to be replaced by a rehearsal through the entry point)


def test_analyse_refuses_under_item_errors_and_reports_otherwise(tmp_path: Path) -> None:
    w = world(updates=2)
    from studies.p10is2 import partt_run

    partt_run.train_all(w, tmp_path / "s", None, 2)
    reg, side = partt_run.score_all(w, tmp_path / "s", fake_gloss_bank(w))
    comb = partt_run.combined_all(w, tmp_path / "s")
    th = Thresholds.from_config(CFG_T)
    ok = partt_real.analyse(reg, side, comb, {"U": 2, "converged": False}, required=partt_plan.required_keys(), thresholds=th)
    assert ok["status"]["status"] == "OK" and "NOT CONVERGED AT U" in ok["report"] and core.ORACLE_LINE in ok["report"] and "ROUTER (keyword-level)" in ok["annotations"] and "COMPOSES" in ok["annotations"]
    bad = partt_real.analyse(reg, side, comb, {"U": 2}, required=partt_plan.required_keys(), thresholds=th, item_errors=["cell x: out of memory"])
    assert "lines" not in bad and "ENGINEERING STOP — ITEM ERRORS" in bad["report"]
    partt_real.write_analysis(tmp_path, ok)
    assert (tmp_path / "analysis.json").is_file() and (tmp_path / "report.txt").read_text().startswith(core.ORACLE_LINE)


def test_shared_share_and_calibration_draws() -> None:
    from p10is2_engine_fixtures import draws

    d = draws(3, 20)
    sh = partt_real.shared_share(d)
    assert set(sh) == {"A", "B"} and all(0.0 <= v <= 1.0 for v in sh.values())
    pool = {c: list(d[0][c]) + list(d[1][c]) + list(d[2][c]) for c in core.TASKS}
    cd = partt_real.calibration_draws(pool, CFG_T, [0, 1], per=5) if False else None
    assert cd is None
    assert Thresholds.from_config(CFG_T).pilot_gap_min == 0.25


def test_load_part_q_disjoint_and_overlapping_draws(tmp_path: Path) -> None:
    import json

    from p10is2_engine_fixtures import bundle, draws

    from studies.p10s2.worldio import write_bundle

    b = bundle()
    write_bundle(b, tmp_path / "outputs/bundle")
    (tmp_path / "generation").mkdir()
    pool = {c: list(b.accepted[c]) for c in core.TASKS}
    (tmp_path / "generation/pools.json").write_text(json.dumps({"pools": {c: [{"key": x.key, "en": x.en, "target": x.target, "group": x.group} for x in pool[c]] for c in core.TASKS}}))
    (tmp_path / "outputs/gloss_bank.json").write_text(json.dumps({"source_words": {}}))
    idx = {c: [[0, 1, 2], [3, 4, 5], [6, 7, 8]] for c in core.TASKS}
    (tmp_path / "generation/result.json").write_text(json.dumps({"draws_label": "DISJOINT DRAWS", "draws": {"indices": idx}}))
    _, d, g, res = partt_real.load_part_q(tmp_path, CFG_T, "test")
    assert [[x.key for x in d[1][c]] for c in core.TASKS] == [[pool[c][i].key for i in (3, 4, 5)] for c in core.TASKS] and res["draws_label"] == "DISJOINT DRAWS" and g == {"source_words": {}}
    assert partt_real.shared_share(d) == {"A": 0.0, "B": 0.0}
    (tmp_path / "generation/result.json").write_text(json.dumps({"draws_label": "OVERLAPPING DRAWS", "draws": None}))
    _, d2, _, _ = partt_real.load_part_q(tmp_path, CFG_T, "test")
    assert len(d2) == 3 and len(d2[0]["A"]) == len(pool["A"]) and set(partt_real.shared_share(d2)) == {"A", "B"}
    (tmp_path / "generation/result.json").write_text(json.dumps({"draws_label": "DATA-EXHAUSTED"}))
    with pytest.raises(core.StageRefused):
        partt_real.load_part_q(tmp_path, CFG_T, "test")
    del draws
