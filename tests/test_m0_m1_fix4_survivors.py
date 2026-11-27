# ruff: noqa: E501
"""M1 fix round 4: the decision rules, the union battery's summary, the capacity report under both builders and the pinned manifest. Self-check only: not independent review, not Astra, not human approval."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from studies.m0.lineages_m1_fix3 import NOT_REGISTERED as NR3
from studies.m0.lineages_m1_fix4 import (
    NOT_REGISTERED_FIX4,
    load_all,
    load_registered,
    not_registered,
)
from studies.m0.lineages_m1_fix4_clusters import cluster_of, count_strict, strict_clusters
from studies.m0.m1_fix4_battery import A3, A4, procedure_exclusions, summarise
from studies.m0.m1_fix4_capacity import demand, family_parts, n_eff, report
from studies.m0.m1_fix4_survivors import BOUND, REPAIRED, decide

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "studies" / "m0" / "manifests" / "m1_fix4_survivors.json"
M = 30000


# ---------------------------------------------------------------- demand and the pool builder as written


def test_demand_is_the_lead_formula_written_out_by_hand_and_rises_as_g_falls() -> None:
    assert demand(8) == 10 * (500 + 2500 + 100) == 31000
    assert demand(9) == 10 * (445 + 2223 + 100) == 27680
    assert demand(10) == 25000 and demand(17) == 10 * (236 + 1177 + 100) == 15130
    assert all(demand(g) > demand(g + 1) for g in range(4, 20))


def test_family_parts_is_the_core_rule_on_an_arbitrary_family_list() -> None:
    # the same function on the families core knows gives the same split as core.family_partition
    from studies.m0.core import family_partition, lineages_of

    fams = sorted({x.family for x in lineages_of("M1")})
    assert family_parts(fams) == family_partition("M1")
    p = family_parts([x.family for x in load_registered()])
    assert sorted(set(p.values())) == ["A", "B"] and abs(sum(v == "A" for v in p.values()) - sum(v == "B" for v in p.values())) <= 1


# ---------------------------------------------------------------- the union battery's summary


def _rules(minus: dict[str, float], base: float = 0.02) -> dict[str, Any]:
    return {"N": 100, "base": base, "rates": {k: base + v for k, v in minus.items()}, "minus_base": minus}


def test_summary_takes_the_largest_two_sided_effect_over_the_union_and_excludes_procedure_rules() -> None:
    lv = {str(i): _rules({"echo_best_position[first/first]": 0.01}) for i in range(7)}
    res: dict[str, dict[str, dict[str, Any]]] = {"own": {"M1.ages_r3": lv}, "a4": {"M1.ages_r3": {str(i): _rules({"a4:echo_pos": 0.02, "im:x": -0.12 if i == 3 else 0.0}) for i in range(7)}}, "a3": {"M1.ages_r3": lv}}
    s = summarise(res)["M1.ages_r3"]
    assert s["3"]["max_abs_excess"] == 0.12 and s["3"]["signed"] == -0.12 and s["3"]["rule"] == "im:x"  # two-sided: a rule BELOW the base counts
    assert s["0"]["rule"] == "a4:echo_pos"
    # procedure rules (division_counting k - remainder) are excluded from the maximum and recorded separately, with the source prefix ignored
    d = {str(i): _rules({"k_minus_remainder_ignores_exact_fit": 0.4, "remainder": 0.05}) for i in range(7)}
    d4 = {str(i): _rules({"im:k_minus_remainder_ignores_exact_fit": 0.45, "a4:echo_pos": 0.02}) for i in range(7)}
    s2 = summarise({"own": {"M1.division_counting_r3": d}, "a4": {"M1.division_counting_r3": d4}, "a3": {"M1.division_counting_r3": d}})["M1.division_counting_r3"]
    assert s2["0"]["max_abs_excess"] == 0.05 and s2["0"]["rule"] == "own:remainder"
    assert s2["0"]["excluded_procedure_max_signed"] == 0.45 and s2["0"]["excluded_procedure_rule"] == "im:k_minus_remainder_ignores_exact_fit"


def test_the_exclusion_list_is_the_audit_and_implementer_lists_and_nothing_hidden() -> None:
    ex = procedure_exclusions()
    assert "ignore_first_rule" in ex["slot_permutations"] and "largest_share" in ex["ratio_share"] and "mean_plus_step" in ex["consecutive"]
    assert any("product_over_gcd_pow_k_minus_1" in n for n in ex["gcd_lcm"])
    # the three lineages audit 4 names are NOT protected by any exclusion
    for st in ("mode_tally", "pigeonhole_worst_case", "coins"):
        assert st not in ex


def test_the_auditors_rule_scripts_are_present_where_the_battery_reads_them() -> None:
    for p in (A3 / "shortcuts_a3.py", A3 / "common_a3.py", A4 / "shortcuts_a4.py", A4 / "common_a4.py", A4 / "capacity_a4.py"):
        assert p.is_file(), p


def test_the_battery_runs_the_auditors_rule_scripts_unchanged_on_a_repaired_lineage() -> None:
    from studies.m0.m1_fix4_battery import a3_task, a4_task, own_task

    for fn in (own_task, a4_task, a3_task):
        lid, out = fn(("M1.mixture_r4", 60))
        assert lid == "M1.mixture_r4" and set(map(str, range(7))) <= set(out)
        assert out["3"]["minus_base"] and all(abs(v) <= 1 for v in out["3"]["minus_base"].values())


# ---------------------------------------------------------------- the decision rules


def _synthetic(over: dict[str, tuple[int, float]] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    over = over or {}
    summ: dict[str, Any] = {}
    chk: dict[str, Any] = {}
    for x in load_all():
        lv = {}
        for i in range(7):
            e = over.get(x.id, (-1, 0.0))
            sig = e[1] if i == e[0] else 0.01
            lv[str(i)] = {"max_abs_excess": abs(sig), "signed": sig, "rule": "a4:synthetic", "excluded_procedure_max_signed": 0.0, "excluded_procedure_rule": ""}
        summ[x.id] = lv
        if "digit_puzzle" not in x.id:
            chk[x.id] = {"identical_level_pairs": [], "profile": {}, "key_problems": [], "rising_parameter_problems": [] if x.id in REPAIRED else None}
    return {"summary": summ}, {"lineages": chk}


def test_decide_applies_the_bound_two_sided_and_exactly() -> None:
    b, c = _synthetic({"M1.ages_r3": (2, 0.15), "M1.change_ways_r3": (4, -0.1501), "M1.tip_split_r3": (1, 0.1501)})
    d = decide(b, c)
    assert not d["M1.ages_r3"]["reasons"]  # exactly 0.15 is within the bound ("more than 0.15" drops)
    assert d["M1.change_ways_r3"]["reasons"] and "R-24" in d["M1.change_ways_r3"]["reasons"][0]  # below the base by more than 0.15
    assert d["M1.tip_split_r3"]["reasons"] and "level 1" in d["M1.tip_split_r3"]["reasons"][0]
    assert BOUND == 0.15


def test_decide_drops_collapsed_levels_flat_parameters_and_key_mismatches() -> None:
    b, c = _synthetic()
    c["lineages"]["M1.mixture_r4"]["identical_level_pairs"] = ["1=2"]
    c["lineages"]["M1.gcd_lcm_r4"]["rising_parameter_problems"] = ["level 1 -> 2: 5 -> 5 is not rising"]
    c["lineages"]["M1.ages_r3"]["key_problems"] = ["L0 item 3: key 4 != second derivation 5"]
    d = decide(b, c)
    assert "R-21" in d["M1.mixture_r4"]["reasons"][0] and "R-25 (c)" in d["M1.gcd_lcm_r4"]["reasons"][0] and "second derivation" in d["M1.ages_r3"]["reasons"][0]
    assert not d["M1.clock_duration_r4"]["reasons"]


def test_decide_keeps_round_3_drops_dropped_and_never_adds_a_lineage() -> None:
    b, c = _synthetic()
    d = decide(b, c)
    assert set(d) == {x.id for x in load_all()}
    for lid in NR3:
        assert d[lid]["reasons"] and "stays so" in d[lid]["reasons"][0]
    assert not any(v["reasons"] for k, v in d.items() if k not in NR3)


def test_clusters_are_the_strict_map_minus_dropped_lineages_and_a_cluster_survives_with_one_member() -> None:
    ids = [x.id for x in load_registered()]
    cl = strict_clusters(ids)
    assert count_strict(ids) == len(cl) == 17
    assert "S4_product_rule_counting" not in cl  # its only registered member (slot_permutations) is dropped
    assert cl["S1_linear_solve"] == sorted(i for i in ids if cluster_of(i) == "S1_linear_solve") and len(cl["S1_linear_solve"]) == 6  # coins left, the cluster stays
    assert "M1.coins_r3" not in sum(cl.values(), [])
    assert not {"mode_tally", "pigeonhole_worst_case"} & set(cl)


# ---------------------------------------------------------------- capacity report, synthetic data


def _cap(rows: dict[str, list[float | None]], chao_factor: float = 1.0) -> dict[str, Any]:
    return {"M": M, "seed": 23, "levels": {lid: {str(i): {"M": M, "n_eff": v, "chao1": round((v or M * (M - 1) / 6) * chao_factor)} for i, v in enumerate(vals)} for lid, vals in rows.items()}}


def test_n_eff_of_a_level_without_a_collision_is_the_audit_value() -> None:
    assert n_eff({"n_eff": None, "chao1": 1}, M) == M * (M - 1) / 6 == 149995000.0 and n_eff({"n_eff": 5.0, "chao1": 1}, M) == 5.0


def test_report_flags_as_written_and_hypothetical_separately() -> None:
    ids = [x.id for x in load_registered()]
    big = [1e9] * 7
    rows: dict[str, list[float | None]] = {i: list(big) for i in ids}
    rows["M1.rectangle_r3"] = [3000, 4000, 5000, 6000, 7000, 8000, 9000]  # weak member of S1
    rows["M1.ages_r3"] = [20000.0] * 7
    rep = report(_cap(rows), ids)
    assert rep["clusters"] == 17 and rep["G_per_part_smaller"] == 8 and rep["demand_G_per_part"] == 31000 == demand(8)
    assert rep["demand_literal_G_equals_all_clusters"] == demand(17)
    aw = rep["as_written"]
    assert sum(aw["lineages_in_part"].values()) == 29
    assert aw["fails"]["M1.rectangle_r3"] == [0, 1, 2, 3, 4, 5, 6]  # fails the per-lineage demand at every level
    assert "M1.ages_r3" in aw["fails"] or aw["lineages"]["M1.ages_r3"]["demand"] <= 20000  # depends on the lineage's part; consistent either way
    assert aw["by_cluster"]["S1_linear_solve"]["0"].startswith("FAIL") and aw["by_cluster"]["S2_weighted_sum"]["0"] == "PASS"
    hyp = rep["hypothetical_per_cluster"]
    assert hyp["LABEL"].startswith("HYPOTHETICAL") and hyp["G"] == 8 and hyp["demand"] == 31000
    assert hyp["fails"]["S1_linear_solve"]["equal_share"] == [0, 1, 2]  # rectangle x 6 members: 18,000 / 24,000 / 30,000 are below 31,000, 36,000 from level 3 is not
    assert "mixture" not in hyp["fails"]["S1_linear_solve"]  # the mixture basis (harmonic) is high because the other members are huge
    assert "S2_weighted_sum" not in hyp["fails"]


def test_report_passes_when_every_unit_is_large() -> None:
    ids = [x.id for x in load_registered()]
    rep = report(_cap({i: [1e9] * 7 for i in ids}), ids)
    assert rep["as_written"]["fails"] == {} and rep["hypothetical_per_cluster"]["fails"] == {}


def test_report_shows_the_rising_demand_when_clusters_are_removed() -> None:
    ids = [x.id for x in load_registered()]
    cap = _cap({i: [1e9] * 7 for i in ids})
    full = report(cap, ids)
    fewer = report(cap, [i for i in ids if cluster_of(i) not in ("clock_duration", "median_list", "tiered_pricing", "quadratic_area")])
    assert fewer["clusters"] == 13 and fewer["demand_G_per_part"] > full["demand_G_per_part"]


# ---------------------------------------------------------------- the pinned manifest


@pytest.fixture(scope="module")
def man() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text())


def test_manifest_lists_every_candidate_once_with_a_status_a_reason_and_seven_levels(man: dict[str, Any]) -> None:
    assert sorted(man["candidates"]) == sorted(x.id for x in load_all())
    for lid, v in man["candidates"].items():
        assert v["status"] in ("SURVIVES", "NOT_REGISTERED") and v["reason"] and v["strict_cluster"] and v["audit4_reference"]
        assert sorted(v["per_level_max_rule_excess"]) == [str(i) for i in range(7)]
        for lv in v["per_level_max_rule_excess"].values():
            assert lv["rule"] or lv["max_abs_excess"] == 0.0
    assert "M1.min_cost_packs_r2" in man["excluded_everywhere"] and not any("min_cost_packs" in k for k in man["candidates"])


def test_manifest_agrees_with_the_loaders_and_the_bound(man: dict[str, Any]) -> None:
    surv = sorted(x.id for x in load_registered())
    assert man["survivors"] == surv and man["survivor_count"] == len(surv)
    assert sorted(man["dropped"]) == sorted(not_registered()) and man["dropped_count"] == len(not_registered())
    round4 = {k for k in man["dropped"] if k not in NR3}
    assert round4 == set(NOT_REGISTERED_FIX4)
    for lid, v in man["candidates"].items():
        worst = max(x["max_abs_excess"] for x in v["per_level_max_rule_excess"].values())
        if v["status"] == "SURVIVES":
            assert worst <= BOUND, (lid, worst)
        elif lid not in NR3 and lid not in REPAIRED:
            assert worst > BOUND, (lid, worst)  # a lineage dropped in round 4 only for the bound exceeds it
    assert man["bound"]["value"] == 0.15 and man["bound"]["two_sided"] is True


def test_manifest_clusters_and_capacity_are_consistent(man: dict[str, Any]) -> None:
    ids = man["survivors"]
    cl = strict_clusters(ids)
    assert man["surviving_cluster_count"] == len(cl) and man["surviving_cluster_names"] == sorted(cl)
    cap = man["capacity"]
    assert cap["clusters"] == len(cl) and cap["G_per_part_smaller"] == len(cl) // 2 and cap["demand_G_per_part"] == demand(len(cl) // 2)
    assert set(cap["hypothetical_per_cluster"]["clusters"]) == set(cl) and set(cap["as_written"]["by_cluster"]) == set(cl)
    assert set(cap["as_written"]["lineages"]) == set(ids)
    for cluster in cl:
        for lv in range(7):
            assert cap["as_written"]["by_cluster"][cluster][str(lv)] in ("PASS",) or cap["as_written"]["by_cluster"][cluster][str(lv)].startswith("FAIL")
    # every capacity-only failure under the as-written builder is listed for the lead and its lineage still carries a status of its own
    assert man["capacity_as_written_failures_listed_for_the_lead"] == cap["as_written"]["fails"]
    for lid, bad in cap["as_written"]["fails"].items():
        assert man["candidates"][lid]["capacity_as_written_fails_at_levels"] == bad and man["candidates"][lid]["status"] == "SURVIVES"
    # the demand is recomputed from G, not copied
    assert cap["as_written"]["demand_per_lineage_part"] == {p: demand(n) for p, n in cap["as_written"]["lineages_in_part"].items()}
    assert math.isclose(cap["demand_G_per_part"], demand(cap["G_per_part_smaller"]))


def test_manifest_repaired_survivors_have_distinct_rising_levels_and_the_hygiene_record_is_honest(man: dict[str, Any]) -> None:
    for lid in REPAIRED:
        v = man["candidates"][lid]
        assert v["repaired_in_round_4"] and v["replaces"]
        assert v["level_checks"]["identical_level_pairs"] == [] and v["level_checks"]["rising_parameter_problems"] == [] and v["level_checks"]["key_problems"] == []
    h = man["hygiene_edit"]
    assert h["generated_items_identical"] is False and h["total_before"] != h["total_after"]  # the edit changed the items of the unregistered digit_puzzle: said plainly
    assert h["file"] == "studies/m0/lineages_m1_fix3_c.py" and h["line"] == 116


def test_manifest_lists_the_procedure_rules_above_the_bound_for_the_lead(man: dict[str, Any]) -> None:
    listed = man["survivors_with_an_excluded_procedure_rule_above_the_bound_PENDING_LEAD_REVIEW"]
    expect = {lid for lid in man["survivors"] if any(abs(v["excluded_procedure_max_signed"]) > BOUND for v in man["candidates"][lid]["per_level_max_rule_excess"].values())}
    assert set(listed) == expect and expect  # at least ratio_share, division_counting, consecutive, gcd_lcm, finite_differences, prime_factors
    for lid, row in listed.items():
        assert abs(row["largest_signed"]) > BOUND and row["rules"] and row["levels"]
