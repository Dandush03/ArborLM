# ruff: noqa: E501
"""C1 fix round 4: the measurement code (rules table, level check) on synthetic inputs, and the written manifests. Self-checked only; nothing is registered."""

from __future__ import annotations

import json
from pathlib import Path

from studies.m0.c1_fix4_levels import ks
from studies.m0.c1_fix4_rules_table import A3_MUTATIONS, a3_levels, battery_levels, merge
from studies.m0.lineages_c1_fix4 import current_after_audit4
from studies.m0.lineages_c1_fix4_clusters import MEMBERS

MAN = Path(__file__).resolve().parent.parent / "studies" / "m0" / "manifests"


def _per(n: int = 400) -> dict[str, dict]:  # type: ignore[type-arg]
    return {"n": n, "MF_cv": 0.01, "MF_shape_cv": 0.02, "BEST_generic_cv": 0.03, "BEST_generic_chosen": [], "S": {}, "MF_printform_cv": 0.0, "oracle_any_literal": 0.9, "shapes": {}, "distinct_keys": 5, "retries": 0, "MF_shape_cv_": 0.0}


def test_battery_control_rules_are_not_counted() -> None:
    per = {str(lv): {**_per(), "S": {"counts|C.self_check": {"hit": 400, "n_shape": 400, "rate": 1.0}, "counts|S.uniform": {"hit": 20, "n_shape": 400, "rate": 0.05}}} for lv in range(7)}
    out = battery_levels(per)
    assert max(x[0] for x in out["3"]) == 0.05  # the 1.0 control rule is not a shortcut


def test_audit3_mutation_rules_are_not_counted() -> None:
    per = {str(lv): {**_per(), "S": {f"xy|{A3_MUTATIONS[1]}": {"hit": 400}, "xy|S.other": {"hit": 8}}} for lv in range(7)}
    out = a3_levels(per)
    assert max(x[0] for x in out["0"]) == 0.03  # the no-op mutation (1.0) is excluded; the best generic 0.03 and the rule 8/400 = 0.02 remain


def test_merge_takes_the_largest_over_sources_and_reports_the_rule() -> None:
    cand = {str(lv): [(0.02, "a4.EFF_S")] for lv in range(7)}
    cand["2"] = [(0.02, "a4.EFF_S"), (0.31, "a4.x|F.closed")]
    a4 = {"cand": cand, "shapes": {}, "m_wide": {str(lv): 0.0 for lv in range(7)}, "shape_counts": {}}
    r = merge("C1.t", a4, None, None)
    assert r["level_wide_max"] == 0.31 and r["level_wide_cheap"]["2"]["rule"] == "a4.x|F.closed" and r["level_wide_cheap"]["0"]["max_excess"] == 0.02


def test_ks_statistic() -> None:
    assert ks([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0
    assert ks([1.0, 2.0], [10.0, 11.0]) == 1.0
    assert 0.0 < ks([1.0, 2.0, 3.0, 4.0], [3.0, 4.0, 5.0, 6.0]) < 1.0


def test_survivors_manifest_agrees_with_the_map_and_the_bound() -> None:
    m = json.loads((MAN / "c1_fix4_survivors.json").read_text())
    surv = {x["name"] for x in m["lineages"] if x["status"] == "SURVIVES"}
    assert surv == set(current_after_audit4())
    assert surv == {i for ms in MEMBERS.values() for i in ms}
    assert m["surviving_lineages"]["count"] == 27 and m["surviving_clusters"]["count"] == 18 and m["surviving_clusters"]["count_without_variants"] == 16
    assert m["G"]["smaller_part_N_div_2"] == 9 and m["G"]["demand_per_cluster_and_level"] == 27680
    for x in m["lineages"]:
        assert x["status"] in ("SURVIVES", "NOT_REGISTERED") and x["reason"] and x["strict_cluster"]
        assert set(x["level_wide_cheap_per_level"]) == {str(i) for i in range(7)}
        if x["status"] == "SURVIVES":
            assert x["level_wide_max"] <= m["bound"] == 0.15
            assert x["levels"]["distinct"] and x["execution"]["key_mismatches"] == 0 and x["execution"]["second_solver_mismatches"] == 0 and x["execution"]["errors"] == 0
    assert m["capacity"]["all_clusters_all_levels_pass_per_lineage"] is True
    assert set(m["capacity"]["clusters"]) == set(m["surviving_clusters"]["list"])


def test_exec_manifest_has_no_mismatch() -> None:
    e = json.loads((MAN / "c1_fix4_exec.json").read_text())
    assert e["total"]["items"] == 28350 and sum(v for k, v in e["total"].items() if k != "items") == 0


def test_pre_repair_levels_were_collapsed_for_the_two_builders() -> None:
    m = json.loads((MAN / "c1_fix4_survivors.json").read_text())
    for old in ("C1.func_branch", "C1.func_compose_f3"):
        assert m["pre_repair_levels"][old]["levels_distinct"] is False
