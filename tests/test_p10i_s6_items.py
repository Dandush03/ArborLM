# ruff: noqa: E501
"""P10IS6 items and workers end to end on tiny synthetic inputs: derivation, run sharing, training, evaluation, registry, analysis, failed cells, resume and pause. Self-check only."""

import copy
from pathlib import Path
from typing import Any

import pytest
import torch

from studies.p10i_s6 import analysis, core, items, model, testing
from studies.p10i_s6.core import DENSE, FLAT

BASE_CFG = core.load_config()
KMAX = 2


def tiny_cfg() -> dict[str, Any]:
    cfg = copy.deepcopy(dict(BASE_CFG))
    cfg["ladder"] = {**BASE_CFG["ladder"], "base_updates": 2, "below_updates": 1}  # U_-1 = 1, U_0 = 2, U_1 = 4, U_2 = 8
    return cfg


CFG = tiny_cfg()
RT_DISTINCT = {"rates": {FLAT: {"-1": 0.003, "0": 0.01, "1": 0.03, "2": 0.1}, DENSE: {"-1": 0.003, "0": 0.003, "1": 0.01, "2": 0.03}}}
RT_SHARED = {"rates": {a: {str(k): 0.01 for k in range(-1, KMAX + 1)} for a in core.ARMS}}


def resources(resume_ok: bool = True) -> items.Resources:
    table = testing.random_rows(300, core.test_seed(20, CFG)).to(torch.uint8)
    panel = testing.random_rows(4, core.test_seed(21, CFG))
    return items.Resources(CFG, table, {"registered": (0, 200), "calibration": (200, 100)}, {"registered": panel, "calibration": panel}, lambda g, p: testing.synthetic_backbone(p % 3), expected_targets=256, resume_ok=resume_ok)


def test_run_groups_share_runs_and_name_every_snapshot() -> None:
    g = items.run_groups(CFG, RT_SHARED, FLAT, KMAX)
    assert len(g) == 1 and g[0]["serves"] == [-1, 0, 1, 2] and g[0]["max_update"] == 8 and g[0]["snapshots"] == [0, 1, 2, 4, 8]
    assert g[0]["modes"] == {0: "step0", 1: "triple", 2: "full", 4: "full", 8: "full"}
    d = items.run_groups(CFG, RT_DISTINCT, FLAT, KMAX)
    assert [x["rate"] for x in d] == [0.003, 0.01, 0.03, 0.1] and [x["max_update"] for x in d] == [1, 2, 4, 8]
    assert d[0]["snapshots"] == [0, 1] and d[2]["snapshots"] == [0, 1, 2, 4] and d[3]["modes"][4] == "enabled" and d[3]["modes"][8] == "full"  # every rung up to the run's maximum is evaluated at least on the enabled read (along-run curve)
    dense = items.run_groups(CFG, RT_DISTINCT, DENSE, KMAX)
    assert dense[0]["serves"] == [-1, 0] and dense[0]["max_update"] == 2


def test_registered_items_counts_and_keys() -> None:
    it = items.registered_items(CFG, RT_DISTINCT, KMAX, cells=[0, 1, 2], oa_cells=[0, 1, 2])
    n_train = (4 + 3) * 3 + 2 * 3  # flat: 4 rates, dense: 3 rates, 3 cells; OA: 2 arms x 3 cells
    assert len(it["train"]) == n_train and len({i["id"] for i in it["train"]}) == n_train
    assert all(e["train"] in {t["id"] for t in it["train"]} for e in it["eval"])
    assert {t["profile"] for t in it["train"]} == {"registered", "oa"}
    assert all(t["stream_seed"] == core.Seeds("registered", CFG).stream(t["cell"]) for t in it["train"] if t["profile"] == "registered")
    # the ladder cannot be extended by an item: no update count exceeds U_{k_max}
    assert max(t["max_update"] for t in it["train"]) == core.rung_updates(CFG, KMAX)
    cal = items.calibration_items(CFG, {FLAT: [0.01, 0.03], DENSE: [0.01]}, KMAX)
    assert len(cal["train"]) == 3 * 3 and all(t["max_update"] == 8 and t["pool"] == "calibration" for t in cal["train"]) and {e["controls"] for e in cal["eval"]} == {"enabled"}


def run_everything(res: items.Resources, plan_items: dict[str, list[dict[str, Any]]], run_dir: Path) -> None:
    by_id = {t["id"]: t for t in plan_items["train"]}
    for t in plan_items["train"]:
        items.guarded(items.train_record_path(run_dir, t), t["id"], lambda t=t: items.run_train(res, t, run_dir))
    for e in plan_items["eval"]:
        t = by_id[e["train"]]
        rec = core.read_record(items.train_record_path(run_dir, t), "train")
        items.guarded(items.eval_record_path(run_dir, e), e["id"], lambda e=e, t=t, rec=rec: items.run_eval(res, e, run_dir, rec, t), "eval")


def bases(res: items.Resources, parents: int, oa: bool) -> dict[str, dict[str, float]]:
    out = {}
    for p in range(parents):
        b = model.evaluate(model.S3Model(res.backbone("old" if oa else "registered", p), core.BASE, None), res.panels["registered"], expected_targets=256)
        out[f"{'oa' if oa else ''}{p}"] = {"enabled": b, "replay": b}
    return out


def test_end_to_end_train_eval_registry_analysis_and_resume() -> None:
    res = resources()
    cells = [0, 1, 2]
    for rt, label in ((RT_DISTINCT, "distinct"), (RT_SHARED, "shared")):
        plan_items = items.registered_items(CFG, rt, KMAX, cells=cells, oa_cells=cells)
        with testing.scratch(f"e2e-{label}") as d:
            run_everything(res, plan_items, d)
            reg = items.collect_registry(d, plan_items, {**bases(res, 1, False), **bases(res, 1, True)})
            out = analysis.analyse(reg, rt, CFG, k_max=KMAX, bitwise=True, cells=3, oa_cells=3)
            assert out["line_p"]["row"] in range(1, 13) and out["k_max"] == KMAX and out["cells"] == 3
            assert set(out["per_rung"]) == {"0", "1", "2"} and out["r16"]["label"] and out["oa"]["label"]
            assert out["line_p"]["integrity_problems"] == []  # disabled == BASE and replay == enabled bitwise on every read the rules use
            assert out["trend"]["text"].endswith("nothing about the ordering at convergence and is not the label PERSISTS.")
            assert all(core.read_record(items.eval_record_path(d, e), "eval") for e in plan_items["eval"])
    # restart from nothing: an existing record is returned, not recomputed
    with testing.scratch("e2e-rec") as d:
        t = items.registered_items(CFG, RT_SHARED, KMAX, cells=[0], with_oa=False)["train"][0]
        r1 = items.run_train(res, t, d)
        assert items.run_train(res, t, d) == r1


def test_resume_after_a_pause_equals_the_uninterrupted_run_and_no_resume_restarts() -> None:
    res = resources(resume_ok=True)
    t = items.registered_items(CFG, RT_SHARED, KMAX, cells=[0], with_oa=False)["train"][0]
    with testing.scratch("pause-ref") as ref, testing.scratch("pause-run") as d, testing.scratch("pub") as pub:
        full = items.run_train(res, t, ref)
        (pub / core.PAUSE_FILE).write_text("another study needs the machine")
        paused = items.run_train(res, t, d, pub)
        assert paused["status"] == "paused" and paused["resume_from"] < t["max_update"] and not items.train_record_path(d, t).exists()
        (pub / core.PAUSE_FILE).unlink()
        done = items.run_train(res, t, d, pub)
        assert done["status"] == "ok" and done["resumed_from"] == paused["resume_from"]
        for u in t["snapshots"]:
            assert model.snapshots_equal(items.item_dir(ref, t["id"]) / "snapshots", u, items.item_dir(d, t["id"]) / "snapshots", u)
        assert full["updates_done"] == t["max_update"]
    # without the resume-identity gate a partial run restarts from update 0 (ruling 6)
    res2 = resources(resume_ok=False)
    with testing.scratch("pause-run2") as d, testing.scratch("pub2") as pub:
        (pub / core.PAUSE_FILE).write_text("x")
        assert items.run_train(res2, t, d, pub)["status"] == "paused"
        (pub / core.PAUSE_FILE).unlink()
        again = items.run_train(res2, t, d, pub)
        assert again["status"] == "ok" and again["resumed_from"] is None


def test_failed_cell_is_a_record_not_an_item_error_and_other_exceptions_are() -> None:
    res = resources()
    t = items.registered_items(CFG, RT_SHARED, KMAX, cells=[0], with_oa=False)["train"][0]

    def nan_backbone(g: str, p: int) -> Any:
        bb = testing.synthetic_backbone(0)
        with torch.no_grad():
            bb.token.weight.fill_(float("nan"))  # a non-finite training loss: a failed cell, by the code's own FailedCell
        return bb

    bad = items.Resources(CFG, res.table, res.pools, res.panels, nan_backbone, expected_targets=256)
    with testing.scratch("fail") as d:
        rec = items.guarded(items.train_record_path(d, t), t["id"], lambda: items.run_train(bad, t, d))
        assert rec["status"] == "failed_cell" and "non-finite training loss" in rec["reason"]
        for e in [x for x in items.registered_items(CFG, RT_SHARED, KMAX, cells=[0], with_oa=False)["eval"] if x["train"] == t["id"]]:
            r = items.run_eval(bad, e, d, rec, t)
            assert "skipped" in r or r["nonfinite_enabled"]  # no snapshot of a failed run is read as a value
    with testing.scratch("err") as d:
        t2 = items.registered_items(CFG, RT_SHARED, KMAX, cells=[0], with_oa=False)["train"][0]
        broken = items.Resources(CFG, res.table, {"registered": (0, 4), "calibration": (200, 100)}, res.panels, res.backbone, expected_targets=256)  # a pool that is too small: an engineering stop
        with pytest.raises(core.EngineeringStop):
            items.guarded(items.train_record_path(d, t2), t2["id"], lambda: items.run_train(broken, t2, d))
        with pytest.raises(RuntimeError):
            items.guarded(items.train_record_path(d, t2), t2["id"], lambda: (_ for _ in ()).throw(RuntimeError("disk full")))
        assert core.read_record(items.train_record_path(d, t2), "train")["status"] == "item_error"
        with pytest.raises(core.EngineeringStop, match="ITEM ERRORS"):
            items.collect_registry(d, {"train": [t2], "eval": []})  # collect refuses on an item error
