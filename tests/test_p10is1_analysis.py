# ruff: noqa: E501
"""P10IS1 analysis on synthetic registries with known answers (ADR-0024 sections 9 and 18). Every registry is built from DESIGNED levels of i (``synthetic.positive_levels``: F-OQ gains capacity at both loaded steps, D-OQ is behind
it at the larger cells, T-OQ and H8 do not gain); the expected classes and labels below are derived BY HAND from that design (the arithmetic is in the comments), never with the analysis' own helpers. Distinct values are
planted in the F-OQ and F-OQ-IVF reads so that a shared key would show. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is1 import analysis, core, synthetic  # noqa: E402
from studies.p10is1.synthetic import positive_levels  # noqa: E402

CAP_SUP = "CAPACITY_SUPPORTED"


@pytest.fixture(scope="module")
def positive() -> dict[str, Any]:
    return analysis.analyze(synthetic.build())


def lines(res: dict[str, Any]) -> tuple[str, str, str]:
    return res["lines"]["C-CAPACITY"], res["lines"]["C-SATURATION"], res["lines"]["C-EFFICIENCY"]


def test_positive_design_gives_the_hand_derived_answers(positive: dict[str, Any]) -> None:
    res = positive
    assert res["status"] == "COMPLETE" and lines(res) == ("CAPACITY-POSITIVE", "SATURATION-PROPORTIONAL", "EFFICIENCY-POSITIVE")
    arms = res["capacity"]["arms"]
    # F-OQ: C1 small 8K/1K final 1.5 (loaded), large 8K/4K 3.5 at U_P: d_MU 2.0, d_SAT 3.5 - 1.5 = 2.0, plateau gain 0, a_use(3.5 bits) ~ 0.85 -> CAPACITY in 5 of 5; C2 likewise at 32K/16K
    assert {k: v["class"] for k, v in arms["F-OQ"]["steps"].items()} == {"C1": "CAPACITY STEP", "N1": "NO GAIN", "C2": "CAPACITY STEP", "N2": "NO GAIN"}
    assert arms["F-OQ"]["class"] == CAP_SUP and arms["F-OQ-IVF"]["class"] == CAP_SUP and arms["F-OQ"]["a_use_at_32K_16K_all5"]  # i = 3.5 bits is a_use ~ 0.85 >= 0.80
    # T-OQ and H8 are flat across the fourfold step (1.5 -> 1.6, 3.9 -> 4.0): NULL in every step -> NO GAIN -> CAPACITY_NOT_SUPPORTED, and NOT APPLICABLE as a dense label (no CAPACITY STEP)
    for arm in ("T-OQ", "H8"):
        assert arms[arm]["class"] == "CAPACITY_NOT_SUPPORTED" and arms[arm]["dense_arm"] == "NOT APPLICABLE" and arms[arm]["capacity_steps"] == []
    # D-OQ is behind F-OQ at the larger cells (3.2 against 3.5): d = +0.3 in every reading -> STORE NOT BEHIND at both, NOT BEHIND DENSE
    assert {k: v["label"] for k, v in arms["F-OQ"]["dense_cells"].items()} == {"8K/4K": "STORE NOT BEHIND", "32K/16K": "STORE NOT BEHIND"} and arms["F-OQ"]["dense_arm"] == "NOT BEHIND DENSE"
    for cell in arms["F-OQ"]["dense_cells"].values():
        assert cell["counts"] == {"MU": 0, "MC-A": 0, "MC-T": 0, "MC-C": 0, "D-BEST": 0}
    # at saturation F-OQ holds 1.5 against D-OQ's 1.2 (ratio 1.25 >= 1.10), D-OQ full; the cost condition (D-OQ's cost per update at least the arm's in both measures) holds at 32K/4K (0.0088 >= 0.0085 s) and not at 8K/1K (0.0051 < 0.0060 s)
    sat = arms["F-OQ"]["dense_at_saturation"]
    assert sat["8K/1K"]["label"] == "SAME AT SATURATION" and sat["32K/4K"]["label"] == "STORE HOLDS MORE AT SATURATION"
    out = res["capacity"]["outcome"]
    assert out["row"] == 3 and out["arms"] == ["F-OQ", "F-OQ-IVF"] and out["post_hoc_only"] is False
    # saturation: S(256) = 2048 x 1.0, S(1K) = 8192 x 1.5, S(4K) = 32768 x 1.5: rho = 6.0 and 4.0, both >= 3.0
    pairs = res["saturation"]["arms"]["F-OQ"]["pairs"]
    assert pairs["256→1K"]["class"] == "PROPORTIONAL STEP" and pairs["1K→4K"]["class"] == "PROPORTIONAL STEP"
    assert abs(pairs["256→1K"]["replicates"][0]["detail"]["rho"]["A"] - 6.0) < 0.05 and abs(pairs["1K→4K"]["replicates"][0]["detail"]["rho"]["A"] - 4.0) < 0.05
    assert res["saturation"]["outcome"]["arms"] == ["F-OQ", "T-OQ", "F-OQ-IVF"]  # H8 alone cannot give PROPORTIONAL, and its class does not enter
    assert res["saturation"]["arms"]["H8"]["class"] == "SATURATION_PROPORTIONAL_ALL_PAIRS"
    # efficiency: F-OQ reaches 3.0 bits at 5,952 updates (2K/1K) and 1,448 (2K/4K), at 6,717 and 1,680 at 8K: at most half the updates and at most 0.8 of the cost in both readings -> FASTER STEP, DENSE NOT FASTER
    for r in ("E-A", "E-T"):
        e = res["efficiency"]["readings"][r]["arms"]["F-OQ"]
        assert e["class"] == "EFFICIENCY_SUPPORTED" and {k: v["class"] for k, v in e["steps"].items()} == {"N1": "FASTER STEP", "N2": "FASTER STEP"} and set(e["dense_speed"].values()) == {"DENSE NOT FASTER"}
    assert res["efficiency"]["readings"]["E-T"]["arms"]["F-OQ"]["steps"]["N1"]["replicates"][0]["u_t_large"][1] == pytest.approx(1448.15, abs=0.5)
    assert res["not_tested_x"] == "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED"


def test_ladder_cells_stop_together_and_later_items_are_not_reached(positive: dict[str, Any]) -> None:
    assert positive["ladder_stops"] == {"2K/256": {"u_run": 98304}, "8K/1K": {"u_run": 131072}, "32K/4K": {"u_run": 131072}}
    nr = positive["not_reached"]
    assert nr  # every ladder-cell label has snapshots beyond its stop (G is above U0)
    for label, ups in nr.items():
        assert ups and all(u > (98304 if "n256_" in label else 131072) for u in ups)
    assert positive["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["replicates"][0]["u_run_small"] == 131072


def test_f_oq_and_its_ivf_read_never_share_a_record() -> None:
    # plant a different i in F-OQ's index read at 32K/16K: 3.0 bits (a_use ~ 0.75 < 0.80) while the main read keeps 3.5
    def ov(arm: str, f: int, n: int, d: int, u: int, read: str, panel: str) -> float | None:
        return 3.0 if (arm, f, n, read) == ("F-OQ", 32768, 16384, "ivf") and u >= 16384 else None

    res = analysis.analyze(synthetic.build(override=ov))
    arms = res["capacity"]["arms"]
    assert arms["F-OQ"]["a_use_at_32K_16K_all5"] and not arms["F-OQ-IVF"]["a_use_at_32K_16K_all5"]
    assert arms["F-OQ"]["class"] == CAP_SUP and arms["F-OQ-IVF"]["class"] == "CAPACITY_ONE_TRANSITION"  # a_use below 0.80 at 32K/16K: SUPPORTED needs it
    assert res["capacity"]["outcome"]["arms"] == ["F-OQ"]
    assert res["saturation"]["arms"]["F-OQ-IVF"]["class"] == "SATURATION_PROPORTIONAL_ALL_PAIRS"  # saturation reads the ladder cells, untouched
    # the sparse-arm label reads T-OQ against the index read of F-OQ, not the main read: T-OQ 1.6 over IVF 3.0 -> BEHIND at 32K/16K, and over 3.5 at 8K/4K
    assert res["capacity"]["sparse"]["U_P"]["label"] == "BEHIND" and res["capacity"]["sparse"]["run"]["label"] == "BEHIND"
    assert core.read_key("x", 512, "main") != core.read_key("x", 512, "ivf")


def test_dense_ahead_gives_capacity_negative_b() -> None:
    # D-OQ at 8K/4K reaches 4.0 against F-OQ's 3.5: d = -0.5 in MU, MC-A, MC-T, MC-C and D-BEST -> DENSE AHEAD at that cell for F-OQ and F-OQ-IVF; T-OQ is NOT_SUPPORTED; (b): every supported arm is DENSE AHEAD
    lv = positive_levels()
    lv[("D-OQ", 8192, 4096)] = (4.0, 8192)
    res = analysis.analyze(synthetic.build(levels=lv))
    foq = res["capacity"]["arms"]["F-OQ"]
    assert foq["dense_cells"]["8K/4K"]["label"] == "DENSE AHEAD" and foq["dense_cells"]["8K/4K"]["counts"] == {"MU": 5, "MC-A": 5, "MC-T": 5, "MC-C": 5, "D-BEST": 5} and foq["dense_arm"] == "DENSE AHEAD"
    out = res["capacity"]["outcome"]
    assert out["label"] == "CAPACITY-NEGATIVE" and out["clause"] == "(b)" and out["arms"] == ["F-OQ", "F-OQ-IVF"]
    assert lines(res)[0] == "CAPACITY-NEGATIVE"


def test_dense_lead_only_at_matched_updates_is_annotated() -> None:
    # D-OQ's curve rises faster but reaches only 3.45 < 3.5 + ... : use a D-OQ best snapshot above F-OQ only at a late update that matched compute never reaches: D-OQ 4.0 after 49152 only
    lv = positive_levels()

    def ov(arm: str, f: int, n: int, d: int, u: int, read: str, panel: str) -> float | None:
        if (arm, f, n) == ("D-OQ", 8192, 4096) and u > 8192 * 3:
            return 4.0  # only D-OQ's best snapshot sees it: MU (at U_P = 8,192) and the matched snapshots (<= 3 x U_P by the cost ratios) read 3.2
        return None

    res = analysis.analyze(synthetic.build(levels=lv, override=ov))
    cell = res["capacity"]["arms"]["F-OQ"]["dense_cells"]["8K/4K"]
    assert cell["counts"]["D-BEST"] == 5 and cell["counts"]["MU"] == 0 and cell["counts"]["MC-A"] == 0
    assert cell["label"] == "DENSE AHEAD (NOT AT MATCHED COMPUTE)"
    assert res["capacity"]["outcome"]["label"] == "CAPACITY-NEGATIVE"  # DENSE AHEAD (NOT AT MATCHED COMPUTE) is DENSE AHEAD in every rule below


def test_mc_t_not_measured_makes_a_positive_unreachable() -> None:
    res = analysis.analyze(synthetic.build(cpu=None))
    assert res["mct_measured"] is False
    foq = res["capacity"]["arms"]["F-OQ"]
    assert foq["class"] == CAP_SUP and foq["steps"]["C1"]["matched_compute_in_mc_a_only"] is True  # CAPACITY verdicts carry MATCHED COMPUTE IN MC-A ONLY
    assert {v["label"] for v in foq["dense_cells"].values()} == {"DENSE COMPARISON SPLIT"} and foq["dense_arm"] == "DENSE SPLIT"  # STORE NOT BEHIND needs MC-T
    out = res["capacity"]["outcome"]
    assert out["label"] == "CAPACITY-INCONCLUSIVE" and out["mct_note"] == "MEASURED COST NOT AVAILABLE: a positive was not reachable"
    assert foq["dense_at_saturation"]["32K/4K"]["label"] == "SAME AT SATURATION"  # STORE HOLDS MORE AT SATURATION needs the cost condition
    eff = res["efficiency"]
    assert set(eff["readings"]) == {"E-A"} and eff["outcome"]["label"] == "EFFICIENCY-INCONCLUSIVE" and eff["e_a_only"] and "MEASURED COST NOT AVAILABLE" in eff["outcome"]["reasons"]


def _excess(draw: int, update: int, extra: int = 300, arm: str = "F-OQ", cell: tuple[int, int] = (8192, 4096), read: str = "main"):  # type: ignore[no-untyped-def]
    def fn(a: str, f: int, n: int, d: int, u: int, r: str, panel: str) -> int:
        return extra if (a, f, n, d, u, r) == (arm, cell[0], cell[1], draw, update, read) else 0

    return fn


def test_dependence_failure_with_the_dep_c_test_and_the_reference_qualification() -> None:
    # planted: 300 correct answers that do not depend on the read at 8K/4K, draw 3, update 4096, main read, both panels. n = 8,192, u ~ 4,750, m ~ 3,440: the quantile of Binomial(m, 325/8192) is ~178, the excess ~ 407
    # (> 178), and (407 - m b / n) / n = 0.037 > 0.01: DEP-c fails.
    res = analysis.analyze(synthetic.build(excess=_excess(3, 4096)))
    foq, ivf = res["capacity"]["arms"]["F-OQ"], res["capacity"]["arms"]["F-OQ-IVF"]
    assert foq["steps"]["C1"]["verdicts"] == ["CAPACITY", "CAPACITY", "DEPENDENCE_FAILED", "CAPACITY", "CAPACITY"] and foq["steps"]["C1"]["class"] == "MIXED"
    assert foq["class"] == "CAPACITY_ONE_TRANSITION" and ivf["class"] == CAP_SUP  # the index read has its own record and is untouched
    out = res["capacity"]["outcome"]
    assert out["label"] == "CAPACITY-POSITIVE" and out["arms"] == ["F-OQ-IVF"] and out["post_hoc_only"] is True  # POST-HOC READ ONLY; NO TRAINED ARM QUALIFIES
    # two replicates -> DEPENDENCE_FAILED class and arm class
    both = {(3, 4096), (4, 4096)}

    def ex2(a: str, f: int, n: int, d: int, u: int, r: str, panel: str) -> int:
        return 300 if (a, f, n, r) == ("F-OQ", 8192, 4096, "main") and (d, u) in both else 0

    r2 = analysis.analyze(synthetic.build(excess=ex2))
    assert r2["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["class"] == "DEPENDENCE_FAILED" and r2["capacity"]["arms"]["F-OQ"]["class"] == "DEPENDENCE_FAILED"
    # the reference qualification: a condition R2 fails at a fraction is not used at that fraction (NOT QUALIFIED AT 0.5 of U_P for row 8,192)
    q = {"8192": {"0.5": ["a", "b"]}}
    res_q = analysis.analyze(synthetic.build(excess=_excess(3, 4096), qualification=q))
    assert res_q["capacity"]["arms"]["F-OQ"]["class"] == CAP_SUP and res_q["capacity"]["outcome"]["arms"] == ["F-OQ", "F-OQ-IVF"]
    # a DEP-c failure at a fraction ABOVE 1 is judged by the qualification at fraction 1: qualify nothing at 1 and the failure at 16,384 is not applied
    res_hi = analysis.analyze(synthetic.build(excess=_excess(3, 16384), qualification={"8192": {"1": ["a", "b"]}}))
    assert res_hi["capacity"]["arms"]["F-OQ"]["class"] == CAP_SUP
    res_hi2 = analysis.analyze(synthetic.build(excess=_excess(3, 16384)))
    assert res_hi2["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["verdicts"][2] == "DEPENDENCE_FAILED"


def test_registered_reference_failure_disables_the_condition_in_that_replicate() -> None:
    # R2 at 8K/16K (the reference cell of row 8,192) fails DEP-c at update 4096 in draw 3 (same planted excess): the condition is not applied at that snapshot, in that replicate, to every arm of the row
    r2_excess = _excess(3, 4096, arm="R2", cell=(8192, 16384))

    def both(a: str, f: int, n: int, d: int, u: int, r: str, p: str) -> int:
        return r2_excess(a, f, n, d, u, r, p) + _excess(3, 4096)(a, f, n, d, u, r, p)

    res = analysis.analyze(synthetic.build(excess=both))
    assert res["capacity"]["arms"]["F-OQ"]["class"] == CAP_SUP
    assert {"row": 8192, "draw": 3, "update": 4096, "conditions": ["c"]} in res["reference_failed_dep"]
    assert not analysis.analyze(synthetic.build())["reference_failed_dep"]


def test_ref_failure_and_leakage_make_a_replicate_not_evaluated() -> None:
    def low_r2(count: int):  # type: ignore[no-untyped-def]
        def ov(arm: str, f: int, n: int, d: int, u: int, read: str, panel: str) -> float | None:
            return 3.0 if arm == "R2" and (f, n) == (8192, 16384) and d <= count and u == 8192 else None  # a_use ~ 0.75 < 0.95 at U_P

        return ov

    one = analysis.analyze(synthetic.build(override=low_r2(1)))
    assert one["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["verdicts"] == ["NOT_EVALUATED", "CAPACITY", "CAPACITY", "CAPACITY", "CAPACITY"]
    assert one["capacity"]["arms"]["F-OQ"]["steps"]["N1"]["class"] == "NO GAIN"  # row 2,048 has its own reference
    two = analysis.analyze(synthetic.build(override=low_r2(2)))
    assert two["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["class"] == "NOT_EVALUATED" and two["capacity"]["arms"]["F-OQ"]["steps"]["N2"]["class"] == "NOT_EVALUATED"
    assert two["capacity"]["arms"]["F-OQ"]["steps"]["C2"]["class"] == "CAPACITY STEP"  # row 32,768 is untouched

    def leak(arm: str, f: int, n: int, d: int, u: int) -> int:
        return 900 if (arm, f, n, d) == ("F-OQ", 8192, 4096, 1) else 2

    lk = analysis.analyze(synthetic.build(unseen=leak))
    assert lk["capacity"]["arms"]["F-OQ"]["steps"]["C1"]["verdicts"][0] == "NOT_EVALUATED" and lk["capacity"]["arms"]["T-OQ"]["steps"]["C1"]["verdicts"][0] == "NULL"


def test_a_cell_not_full_within_budget() -> None:
    # 8K/1K for F-OQ rises to 3.0 over 400,000 updates: not full at G = 262,144 (the cell stops at G); 8K/4K reaches only 0.36 so that d_MU = 0.36 - 0.06 = 0.3 (between 0.25 and 0.5): UNRESOLVED, the smaller cell not full in 5 of 5
    lv = positive_levels()
    lv[("F-OQ", 8192, 1024)] = (3.0, 400000)
    lv[("F-OQ", 8192, 4096)] = (0.36, 8192)
    res = analysis.analyze(synthetic.build(levels=lv, u_run={**synthetic.U0, "8K/1K": 262144}))
    assert res["status"] == "COMPLETE"
    c1 = res["capacity"]["arms"]["F-OQ"]["steps"]["C1"]
    assert c1["class"] == "NOT FULL WITHIN BUDGET" and set(c1["verdicts"]) == {"UNRESOLVED"} and not any(r["small_full"] for r in c1["replicates"])
    assert res["saturation"]["arms"]["F-OQ"]["pairs"]["1K→4K"]["class"] == "NOT FULL" and res["saturation"]["arms"]["F-OQ"]["class"] == "SATURATION_NOT_MEASURED"
    assert res["saturation"]["arms"]["T-OQ"]["class"] == "SATURATION_PROPORTIONAL_ALL_PAIRS" and res["saturation"]["outcome"]["label"] == "SATURATION-PROPORTIONAL"  # T-OQ alone carries it
    # the recorded stop must be the stop rule's: stopping at 8K/1K's U0 although F-OQ is not full there is an engineering failure, not a label
    bad = analysis.analyze(synthetic.build(levels=lv, u_run={**synthetic.U0}))
    assert bad["status"] == "ENGINEERING-FAILURE" and "8K/1K" in bad["gate_failures"][0]


def test_statuses_refuse_or_print_no_outcome() -> None:
    errs = analysis.analyze(synthetic.build(status={"item_errors": ["train: a: ValueError"]}))
    assert errs["status"] == "ENGINEERING STOP — ITEM ERRORS" and errs["refused"] and set(errs["lines"].values()) == {"ENGINEERING STOP — ITEM ERRORS"} and "capacity" not in errs
    gate = analysis.analyze(synthetic.build(status={"gate_failures": ["G4 restoration differs"]}))
    assert gate["status"] == "ENGINEERING-FAILURE" and set(gate["lines"].values()) == {"ENGINEERING-FAILURE"}
    first = None

    def drop(key: str) -> bool:
        nonlocal first
        if first is None and key.endswith("|main") and "_n4096_" in key:
            first = key
        return key == first

    inc = analysis.analyze(synthetic.build(drop=drop))
    assert inc["status"] == "INCOMPLETE" and inc["missing_count"] == 1 and set(inc["lines"].values()) == {"INCOMPLETE"}
    paused = analysis.analyze(synthetic.build(status={"paused": ["QUIET CONDITION NOT MET"]}))
    assert paused["status"] == "PAUSED" and set(paused["lines"].values()) == {"PAUSED"} and "capacity" not in paused
    # an item error outranks everything, and a gate failure outranks incompleteness
    both = analysis.analyze(synthetic.build(status={"item_errors": ["x"], "gate_failures": ["y"]}, drop=lambda k: True))
    assert both["status"] == "ENGINEERING STOP — ITEM ERRORS"
    gi = analysis.analyze(synthetic.build(status={"gate_failures": ["y"]}, drop=lambda k: True))
    assert gi["status"] == "ENGINEERING-FAILURE"


def test_fraction_key_maps_snapshots_to_u_over_u_p() -> None:
    assert analysis.fraction_key(4096, 8192) == "0.5" and analysis.fraction_key(512, 8192) == "0.0625" and analysis.fraction_key(8192, 8192) == "1" and analysis.fraction_key(49152, 8192) == "1"  # above 1: fraction 1
    assert analysis.fraction_key(12288, 8192) == "1"


def test_counted_work_is_logical_and_labelled() -> None:
    rows = analysis.analyze(synthetic.build())["counted_work"]
    assert {r["arm"] for r in rows} == {"F-OQ", "T-OQ", "H8", "D-OQ", "R2"} and all("not measured efficiency" in r["note"] for r in rows)
