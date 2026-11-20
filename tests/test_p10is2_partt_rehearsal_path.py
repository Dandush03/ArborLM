# ruff: noqa: E501
"""The rehearsal path IS the registered path (audit B1): a rehearsal stage and a registered stage call the same functions with only the mode (and the rehearsal's own flags) differing, a rehearsal world holds no
evaluation item, and the entry point refuses what it must. The defect class that stopped Part Q five times was a rehearsal path that differed from the registered path. Self-check only."""

import argparse
import inspect
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10is2 import (  # noqa: E402
    partt_plan,
    partt_real,
    partt_rehearsal,
    partt_stages,
    partt_tasks,
)
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config("T")


def args_for(stage: str, **kw: Any) -> argparse.Namespace:
    return argparse.Namespace(stage=stage, run_dir="/x/run", part_q_dir="/x/q", freeze_commit="abc", repo=None, rehearsal=False, rehearsal_kind="counting", plan_file=None, pause_after_updates=None, **kw)


def test_rehearsal_and_registered_stages_call_the_same_functions_with_only_the_mode_differing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_tasks(stage: str, plan: Any, cfg: Any, repo: Any, run_dir: Any, fc: Any, qdir: Any, **k: Any) -> dict[str, Any]:
        calls.append(("run_stage_tasks", stage, {"mode": k.get("mode"), "run_dir": str(run_dir)}))
        return {"status": "PAUSED", "charged_seconds": 0.0}

    def fake_stage(stage: str, repo: Any, run_dir: Any, qdir: Any, plan: Any, mode: str = "registered") -> dict[str, Any]:
        calls.append(("run_stage", stage, {"mode": mode, "run_dir": str(run_dir)}))
        return {"ok": True}

    monkeypatch.setattr(partt_tasks, "run_stage_tasks", fake_tasks)
    monkeypatch.setattr(partt_tasks, "require_predecessor", lambda *a, **k: None)
    monkeypatch.setattr(partt_tasks, "mark_complete", lambda *a, **k: None)
    monkeypatch.setattr(partt_real, "run_stage", fake_stage)
    monkeypatch.setattr(partt_real, "require_gates_passed", lambda *a, **k: None)
    plan = planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "items": {}, "stage_caps": {}}, "T")
    for stage in ("gates", "train", "evaluate", "combined", "controls", "recompute", "analysis", "report"):
        for mode in ("registered", "rehearsal"):
            partt_stages.execute_stage(args_for(stage), ROOT, plan, mode)
    by_stage: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for fn, stage, info in calls:
        by_stage.setdefault(stage, []).append((fn, info))
    assert set(by_stage) == set(partt_plan.STAGES)
    for stage, (reg, reh) in by_stage.items():
        assert reg[0] == reh[0], stage  # the same function
        assert reg[1]["mode"] == "registered" and reh[1]["mode"] == "rehearsal" and reg[1]["run_dir"] == reh[1]["run_dir"], stage  # only the mode differs
    assert {fn for fn, _ in sum(by_stage.values(), [])} == {"run_stage_tasks", "run_stage"}


def test_the_two_launch_commands_have_one_body_and_no_stage_logic_of_their_own() -> None:
    for fn in (partt_stages.cmd_registered, partt_stages.cmd_task):
        src = inspect.getsource(fn)
        assert "run_stage_tasks" not in src and "run_stage(" not in src and "mark_complete" not in src  # neither command holds stage logic: both go through plan_for and the shared bodies
    assert "plan_for(" in inspect.getsource(partt_stages.cmd_registered) and "execute_stage(" in inspect.getsource(partt_stages.cmd_registered)
    assert "plan_for(" in inspect.getsource(partt_stages.cmd_task) and "run_task(" in inspect.getsource(partt_stages.cmd_task)
    src = inspect.getsource(partt_stages.plan_for)
    assert "refuse_unless_rehearsal_ready" in src and "refuse_unless_registered_ready" in src  # the one branch between the two


def test_a_registered_launch_refuses_the_rehearsals_flags_and_a_rehearsal_refuses_a_freeze_commit(tmp_path: Path) -> None:
    from studies.p10is2.common.core import StageRefused

    with pytest.raises(StageRefused, match="rehearsal"):
        partt_stages.plan_for(argparse.Namespace(stage="gates", run_dir=str(tmp_path), freeze_commit="abc", repo=None, rehearsal=False, plan_file="x.json", pause_after_updates=None), ROOT, "gates")
    with pytest.raises(StageRefused, match="takes '-'"):
        partt_stages.refuse_unless_rehearsal_ready(ROOT, tmp_path, None, "gates", "abc")


def test_a_rehearsal_world_holds_no_evaluation_item_and_the_subset_is_the_ten_types() -> None:
    from p10is2_engine_fixtures import bundle

    b = bundle()
    d_cal = {i.key for i in b.panels["D_cal"]}
    rb = partt_rehearsal.rehearsal_bundle(b, CFG)
    real_eval = {i.key for n in ("E_A", "E_B", "E_C", "E_open") for i in b.panels[n]}
    for n in ("E_A", "E_B", "E_C", "D_cal"):
        assert {i.key for i in rb.panels[n]} <= d_cal  # every rehearsal panel is made of D_cal items
    keys = {n: {i.key for i in rb.panels[n]} for n in ("E_A", "E_B", "E_C", "D_cal")}
    assert all(not (keys[x] & keys[y]) for x in keys for y in keys if x < y)  # four disjoint parts
    assert not (real_eval - d_cal) & {i.key for n in rb.panels for i in rb.panels[n]} and rb.panels["E_open"] == []
    items = partt_plan.stage_items({"U": 2, "store_rate": 0.003, "lora_rate": 0.001, "etable_rate": 0.003, "read_layer": 1})
    sub = partt_rehearsal.subset_items("train", items["train"])
    assert sorted(i["arm"] for i in sub) == sorted(["M1", "D1", "M-append", "M-seq", "M-ii", "D-append", "D-seq", "M-joint", "D-joint", "E-table"]) and {i["rep"] for i in sub} == {0}
    alias = partt_rehearsal.AliasMap()
    assert alias.get("r0/M-append/BA@append") == "r0/M-append/AB@append" and alias.get("r0/E-table/B") == "r0/E-table/A" and alias.get("r0/M1/AB") == "r0/M1/AB" and alias.get("r0/M-joint/-") == "r0/M-joint/-"
