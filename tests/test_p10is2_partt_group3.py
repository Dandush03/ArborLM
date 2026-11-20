# ruff: noqa: E501
"""Group 3 of the second audit: GEN stored per window and recomputable (N5), the analysis after an engineering failure (N6), the A4 readings (ruling 23: seen-item, E_open, edit-distance-1 share and the scores without
those items) and the report's disclosures. Tiny world, test size. Self-check only."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from p10is2_engine_fixtures import CFG_T, world  # noqa: E402
from p10is2_partt_e2e_world import fake_gloss_bank  # noqa: E402
from p10is2_partt_fixtures import quantities  # noqa: E402

from studies.p10is2 import labels as L  # noqa: E402
from studies.p10is2 import (  # noqa: E402
    partt_items,
    partt_plan,
    partt_real,
    partt_run,
    partt_stages,
    partt_tasks,
    report,
    scoring,
)
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10s2.data import neighbour_share  # noqa: E402


@pytest.fixture(scope="module")
def stored(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    d = tmp_path_factory.mktemp("g3")
    w = world(updates=2, n_reps=1)
    gloss = fake_gloss_bank(w, {c: w.streams[0].t[c] for c in core.TASKS})
    partt_run.train_all(w, d / "snapshots", None, 2, replicates=(0,))
    scoring.ITEMS.clear()
    records = partt_run.reference_task(w)
    rec, _side = partt_run.score_replicate(w, 0, d / "snapshots", gloss, routers_mode="save")
    records.update(rec)
    return w, d, scoring.registry_from_reads(records), scoring.take_items()


def test_gen_is_stored_per_window_and_recomputed_from_the_stored_records(stored) -> None:  # type: ignore[no-untyped-def]
    _w, _d, reg, items = stored
    gen_keys = [k for k in items if k.endswith(("|gen:token64", "|gen:first_marker"))]
    assert gen_keys and all({"nll_base", "nll_arm", "strata", "preds"} <= set(items[k]["gen"]) for k in gen_keys)
    cmp = partt_items.compare(reg.values, items)
    assert cmp["differ"] == [] and all(k in cmp["not_covered_by_items"] or True for k in gen_keys)
    assert not [k for k in cmp["not_covered_by_items"] if "|gen:" in k]  # GEN is no longer outside what is stored
    assert all(abs(partt_items.recompute_registry(items)[k] - reg.values[k]) < 1e-9 for k in gen_keys)
    assert {k.split("|")[-1].split(":")[0] for k in cmp["not_covered_by_items"]} <= {"modification"}  # what remains not item-based
    bad = {k: ({**v, "gen": {**v["gen"], "nll_arm": [x + 0.1 for x in v["gen"]["nll_arm"]]}} if k == gen_keys[0] else v) for k, v in items.items()}
    assert partt_items.compare(reg.values, bad)["differ"], "a changed per-window loss must change the recomputed GEN value"
    assert partt_items.compare_items(items, bad) and partt_items.compare_items(items, items) == []


def test_the_a4_readings_are_stored_and_reported_without_entering_a_label(stored) -> None:  # type: ignore[no-untyped-def]
    w, _d, reg, items = stored
    assert any("|seen:" in k for k in reg.values) and any("|open:" in k for k in reg.values) and "S0|-|-|open:A" in reg.values or "S0|-|-|open:B" in reg.values
    flags = {k: v["flags"] for k, v in items.items() if k.startswith("edit1|-|0|")}
    assert set(flags) == {"edit1|-|0|edit1:E_A", "edit1|-|0|edit1:E_B"}
    train_keys = [x.key for c in core.TASKS for x in w.streams[0].t[c]]
    for n in ("E_A", "E_B"):  # the per-item flags reproduce the share P10-S2's gate G1 computes
        keys = [i.key for i in w.partition.panels[n]]
        assert abs(sum(flags[f"edit1|-|0|edit1:{n}"]) / len(keys) - neighbour_share(keys, train_keys)) < 1e-12
    lines = partt_items.a4_lines(reg.values, items)
    text = "\n".join(lines)
    assert "seen-item score" in text and "E_open score" in text and "edit-distance-1 share of E_A" in text and "without the edit-distance-1 items" in text
    assert partt_items.edit1_flags(["a b c", "a b c d e", "p q"], ["a b d", "x y z"]) == [True, False, False]
    q = quantities()
    rendered = report.render(L.study_status(q.reg, required=partt_plan.required_keys()), L.derive_all(q), {"U": 2000, "converged": True, "draws": "DISJOINT DRAWS", "shared_share": {}, "a4_lines": lines})
    assert "A4 READING (reported, enters no label)" in rendered and "DISCLOSED LIMITATION (rehearsal world, audit 4c)" in rendered and "DISCLOSED LIMITATION (untrained cells in rehearsals, audit 4d)" in rendered
    assert L.derive_all(q) == L.derive_all(quantities())  # the labels do not read them (the registry the labels read has no seen: or open: key)


def test_the_analysis_runs_after_an_engineering_failure_without_a_registry_or_a_recomputation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    w = world(updates=2, n_reps=1)
    run = tmp_path / "run"
    run.mkdir()
    (run / "gates.json").write_text(json.dumps({"status": "ENGINEERING-FAILURE", "failed": ["G1"]}))
    monkeypatch.setattr(partt_real, "build_world_real", lambda *a, **k: (w, {}, {"draws_label": "DISJOINT DRAWS"}))
    plan = planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "items": {}, "stage_caps": {}, "calibration": {"U": 2, "converged": True}}, "T")
    args = argparse.Namespace(stage="analysis", run_dir=str(run), part_q_dir=str(tmp_path), freeze_commit="x", repo=None, rehearsal=False, rehearsal_kind="counting", plan_file=None, pause_after_updates=None)
    assert not partt_tasks.stage_marker(run, "recompute").exists() and not (run / "registry.json").exists()
    assert partt_stages.execute_stage(args, Path(__file__).resolve().parents[1], plan, "registered") == 0  # the predecessor check is skipped for the recorded failure
    res = json.loads((run / "analysis.json").read_text())
    assert res["status"]["status"] == "ENGINEERING-FAILURE" and "lines" not in res  # the stop is recorded and no scientific label is derived
    assert "ENGINEERING-FAILURE" in (run / "report.txt").read_text() and partt_tasks.stage_marker(run, "analysis").is_file()
    clean = tmp_path / "clean"
    clean.mkdir()
    with pytest.raises(core.StageRefused, match="needs 'recompute'"):  # without a recorded failure the order still holds
        partt_stages.execute_stage(argparse.Namespace(**{**vars(args), "run_dir": str(clean)}), Path(__file__).resolve().parents[1], plan, "registered")


def test_the_config_counts_the_a4_units_and_the_basis_carries_them() -> None:
    basis: dict[str, Any] = {"eval_panel": 1000, "control_subsample": 300, "d_con_panel": 300, "seen_items": 300, "e_open_panel": 500}
    assert CFG_T["data"]["seen_items"] == 300 and CFG_T["data"]["e_open_panel"] == 500
    from studies.p10is2 import partt_caps

    assert partt_caps.basis_of(CFG_T) == basis
    plain = partt_caps.replicate_units(1000, 300, 300, 300, 500)["score:plain"]
    assert plain == partt_caps.replicate_units(1000, 300, 300)["score:plain"] + 2 * 2 * 2 * (300 + 500)
