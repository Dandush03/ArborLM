# ruff: noqa: E501
"""P10S1 revision 5: the dense label at saturation, the saturation line (pair verdicts, pair and arm classes, outcomes), the capacity and efficiency lines on the four steps, the milestone
reading, the printed labels and the H8 annotations (ADR-0021 sections 8.2 to 8.10; brief groups 6 to 11), on constructed counts and on synthetic records of the whole registry. The synthetic
accuracies are a declared function of (arm, cell, replicate, update, panel): nothing here measures a model or a seed. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import analysis, core, report  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402
from studies.p10s1 import synthetic as syn  # noqa: E402

PLAN = core.Plan(seed_block_draws=(1,))
FRO = fz.Frozen.build(PLAN, fz.default_cpu_table())


def run(tmp_path: Path, scn: syn.Scenario, fro: fz.Frozen = FRO) -> tuple[dict[str, Any], Path]:
    d = tmp_path / "run"
    syn.write_run(d, fro, scn)
    gates = json.loads((d / "gates.json").read_text())
    result = analysis.analyze_study(analysis.load_study(d, fro), fro, gates=gates)
    core.write_record(d / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": result}))
    return result, d


def rendered(d: Path) -> str:
    text = report.write_report(d, d / "results")[1].read_text()
    assert C.untagged_positive_labels(text) == [] and core.ORACLE_SENTENCE in text and core.STORE_ONLY_TAG in text
    return text


# --- group 7: dense at saturation -------------------------------------------------------------------------------------------------------------------
def sat_cell(cell: str, d: float, r: float | None, status: str = C.PLATEAUED, cost_ok: bool = True, ahead_in: int = 0) -> C.SatDenseCell:
    reps = [dict.fromkeys(core.PANELS, (-0.3 if k < ahead_in else d, r)) for k in range(5)]
    return C.SatDenseCell(cell, reps, [dict.fromkeys(core.PANELS, status) for _ in range(5)], cost_ok)


def test_dense_at_saturation_labels_and_sub_labels() -> None:
    cells = lambda **kw: [sat_cell("8K/1K", 1.0, 1.5, **kw), sat_cell("32K/4K", 1.0, 1.5, **kw)]  # noqa: E731
    assert C.dense_at_saturation(cells())["label"] == C.STORE_HOLDS_MORE
    holds = C.dense_at_saturation([sat_cell("8K/1K", -0.3, 0.5), sat_cell("32K/4K", 1.0, 1.5)])  # d_sat <= -0.25 in all 5 replicates at one loaded cell
    assert holds["label"] == C.DENSE_HOLDS_MORE and holds["sublabels"] == []
    assert C.dense_at_saturation([sat_cell("8K/1K", 1.0, 1.5, ahead_in=4), sat_cell("32K/4K", 1.0, 1.5)])["label"] == C.DENSE_HOLDS_MORE  # at least 4 of 5
    assert C.dense_at_saturation([sat_cell("8K/1K", 1.0, 1.5, ahead_in=3), sat_cell("32K/4K", 1.0, 1.5)])["label"] == C.STORE_HOLDS_MORE  # 3 of 5 do not block
    # either panel counts for a blocking label (section 22 (h))
    either = sat_cell("8K/1K", 1.0, 1.5)
    either.replicates[0]["B"] = (-0.3, 1.5)
    either.replicates[1]["A"] = (-0.3, 1.5)
    either.replicates[2]["B"] = (-0.3, 1.5)
    either.replicates[3]["A"] = (-0.3, 1.5)
    assert C.dense_at_saturation([either, sat_cell("32K/4K", 1.0, 1.5)])["label"] == C.DENSE_HOLDS_MORE
    rising = C.dense_at_saturation(cells(status=C.RISING))
    assert rising["label"] == C.SAME_AT_SATURATION and rising["sublabels"] == [C.DENSE_STILL_RISING] and rising["failing"] == ["dense plateau"]
    floor = C.dense_at_saturation(cells(status=C.FLAT_BELOW_FLOOR))
    assert floor["label"] == C.SAME_AT_SATURATION and floor["sublabels"] == [C.DENSE_NOT_LEARNED]  # fails the plateau only by the floor
    mixed = [sat_cell("8K/1K", 1.0, 1.5, status=C.FLAT_BELOW_FLOOR), sat_cell("32K/4K", 1.0, 1.5, status=C.RISING)]
    assert C.dense_at_saturation(mixed)["sublabels"] == [C.DENSE_STILL_RISING]  # any view still gaining: STILL RISING
    cost = C.dense_at_saturation(cells(cost_ok=False))
    assert cost["label"] == C.SAME_AT_SATURATION and cost["sublabels"] == [C.DENSE_NOT_ESTABLISHED] and cost["failing"] == ["cost"]
    ratio = C.dense_at_saturation([sat_cell("8K/1K", 0.2, 1.05), sat_cell("32K/4K", 1.0, 1.5)])
    assert ratio["label"] == C.SAME_AT_SATURATION and ratio["sublabels"] == [] and ratio["failing"] == ["ratio"]  # r_sat below 1.10 at one cell: no sub-label
    both = C.dense_at_saturation(cells(status=C.RISING, cost_ok=False))
    assert both["sublabels"] == [] and both["failing"] == ["dense plateau", "cost"]  # a sub-label only when exactly one condition fails (section 8.5)
    assert C.dense_at_saturation([sat_cell("8K/1K", 1.0, None), sat_cell("32K/4K", 1.0, 1.5)])["label"] == C.STORE_HOLDS_MORE  # D-OQ's i* zero gives r with a zero denominator
    assert C.is_positive(C.STORE_HOLDS_MORE) and not C.is_positive(C.DENSE_HOLDS_MORE) and not C.is_positive(C.SAME_AT_SATURATION)
    with pytest.raises(C.UntaggedPositiveLabel):
        C.emit(C.STORE_HOLDS_MORE)
    assert C.emit(C.tagged(C.STORE_HOLDS_MORE))


def test_the_path_dense_holds_more_dense_ahead_capacity_negative_b() -> None:
    arms = {a: C.ArmCapacity(a, C.CAPACITY_SUPPORTED, C.DENSE_MATCHES, dense_sat=C.DENSE_HOLDS_MORE, sat_class=C.SAT_PROPORTIONAL_ALL_PAIRS) for a in core.LEARNED_KEY_ARMS}
    assert all(C._is_ahead(a) for a in arms.values())  # DENSE HOLDS MORE AT SATURATION counts as DENSE AHEAD
    out = C.capacity_outcome(arms, engineering_failed=False, incomplete=False)
    assert out.label == C.CAPACITY_NEGATIVE and out.row == 4 and "b: DENSE AHEAD" in out.printed and C.NOT_TESTED_16K_65K in out.printed
    one_free = dict(arms)
    one_free["T-OQ"] = C.ArmCapacity("T-OQ", C.CAPACITY_SUPPORTED, C.DENSE_MATCHES, dense_sat=C.SAME_AT_SATURATION, sat_class=C.SAT_PROPORTIONAL_ALL_PAIRS)
    assert C.capacity_outcome(one_free, engineering_failed=False, incomplete=False).label == C.CAPACITY_POSITIVE  # one supported arm that is not ahead gives the positive


# --- group 8: the saturation line ---------------------------------------------------------------------------------------------------------------------
class FixedView(C.View):
    """A view with a declared i* at its run length: the pair rule is tested on exact numbers."""

    def __init__(self, i: float, run: int = 1000, *, full: bool = True, dep_ok: bool = True) -> None:
        super().__init__({run // 2: C.PanelObs(100, 50, 50, 3, 3), run: C.PanelObs(100, 50, 50, 3, 3)}, run, 8192)
        self._i, self._full, self._dep = i, full, dep_ok

    def i_star(self, limit: int) -> tuple[float, int]:
        return self._i, self.run

    def loaded(self) -> bool:
        return self._full

    def plateau_status(self) -> str:
        return C.PLATEAUED if self._full else C.RISING

    def dep(self, u: int) -> bool | None:
        return None if self._dep else False


def side(i: float, facts: int, slots: int, **kw: Any) -> C.SatSide:
    return C.SatSide(dict.fromkeys(core.PANELS, FixedView(i, **kw)), facts, slots)


def test_every_pair_verdict_with_rho_exactly_three_and_the_printed_numbers() -> None:
    small = side(2.0, 8192, 1024)
    assert C.saturation_pair(small, side(1.5, 32768, 4096), ref_ok=True).verdict == C.PROPORTIONAL  # rho = 3.0 exactly
    sub = C.saturation_pair(small, side(1.4999, 32768, 4096), ref_ok=True)
    assert sub.verdict == C.SUBPROPORTIONAL and sub.detail["rho"]["A"] < 3.0
    ok = C.saturation_pair(small, side(1.5, 32768, 4096), ref_ok=True)
    assert ok.detail["rho"] == {"A": 3.0, "B": 3.0} and ok.detail["small"]["b_bits_per_slot"]["A"] == pytest.approx(16.0) and ok.detail["large"]["b_bits_per_slot"]["A"] == pytest.approx(12.0)
    assert set(ok.detail["small"]["last_doubling_gain"]) == {"A", "B"} and ok.detail["small"]["full"] == {"A": True, "B": True}
    assert C.saturation_pair(small, side(1.5, 32768, 4096), ref_ok=False).verdict == C.NOT_EVALUATED
    assert C.saturation_pair(small, side(1.5, 32768, 4096), ref_ok=True, leakage=True).verdict == C.NOT_EVALUATED
    assert C.saturation_pair(small, side(1.5, 32768, 4096, dep_ok=False), ref_ok=True).verdict == C.DEPENDENCE_FAILED
    assert C.saturation_pair(small, side(1.5, 32768, 4096, full=False), ref_ok=True).verdict == C.NOT_FULL
    assert C.saturation_pair(side(2.0, 8192, 1024, full=False), side(1.5, 32768, 4096), ref_ok=True).verdict == C.NOT_FULL
    mixed_panels = C.SatSide({"A": FixedView(1.5), "B": FixedView(1.0)}, 32768, 4096)
    assert C.saturation_pair(small, mixed_panels, ref_ok=True).verdict == C.SUBPROPORTIONAL  # rho < 3.0 on at least one panel


def test_pair_classes_arm_classes_and_outcomes() -> None:
    v = C.PROPORTIONAL
    assert C.saturation_pair_class([v] * 5) == C.PROPORTIONAL_STEP and C.saturation_pair_class([v] * 4 + [C.SUBPROPORTIONAL]) == C.MIXED
    assert C.saturation_pair_class([C.SUBPROPORTIONAL] * 4 + [v]) == C.SUBPROPORTIONAL_STEP and C.saturation_pair_class([C.SUBPROPORTIONAL] * 3 + [v] * 2) == C.MIXED
    assert C.saturation_pair_class([C.NOT_EVALUATED] * 2 + [v] * 3) == C.NOT_EVALUATED and C.saturation_pair_class([C.DEPENDENCE_FAILED] * 2 + [v] * 3) == C.DEPENDENCE_FAILED
    assert C.saturation_pair_class([C.NOT_FULL] * 2 + [v] * 3) == C.NOT_FULL and C.saturation_pair_class([C.NOT_FULL] + [v] * 4) == C.MIXED
    with pytest.raises(ValueError):
        C.saturation_pair_class([v] * 4)
    P, S, N, E, D = C.PROPORTIONAL_STEP, C.SUBPROPORTIONAL_STEP, C.NOT_FULL, C.NOT_EVALUATED, C.DEPENDENCE_FAILED
    assert C.saturation_arm_class([N, E]) == C.SAT_NOT_MEASURED and C.saturation_arm_class([N]) == C.SAT_NOT_MEASURED
    assert C.saturation_arm_class([D, P]) == C.DEPENDENCE_FAILED and C.saturation_arm_class([S, D]) == C.DEPENDENCE_FAILED  # in the table's order
    assert C.saturation_arm_class([P, S]) == C.SAT_DOES_NOT_SCALE and C.saturation_arm_class([P, P]) == C.SAT_PROPORTIONAL_ALL_PAIRS and C.saturation_arm_class([P]) == C.SAT_PROPORTIONAL_ALL_PAIRS
    assert C.saturation_arm_class([N, P]) == C.INTERMEDIATE and C.saturation_arm_class([C.MIXED, P]) == C.INTERMEDIATE
    assert C.saturation_arm_class([N, P]) == C.INTERMEDIATE  # F-OQ with 2K/256 NOT FULL (or absent) and 1,024 to 4,096 proportional: INTERMEDIATE as the table gives it (the lead's ruling 6)
    assert core.SATURATION_PAIRS["F-OQ"] == ((256, 1024), (1024, 4096)) and all(core.SATURATION_PAIRS[a] == ((1024, 4096),) for a in ("F-OQ-IVF", "T-OQ", "H8"))
    ap, ds, nm, inc = C.SAT_PROPORTIONAL_ALL_PAIRS, C.SAT_DOES_NOT_SCALE, C.SAT_NOT_MEASURED, C.INTERMEDIATE
    pr = C.saturation_outcome({"F-OQ": inc, "T-OQ": ap, "F-OQ-IVF": inc, "H8": inc}, engineering_failed=False, incomplete=False, pairs_read={"T-OQ": ["1024→4096"]}, sat256_absent=True)
    assert pr.row == 3 and pr.label == C.SAT_PROPORTIONAL and all(p in pr.printed for p in (*C.SAT_FIXED_PHRASES, C.NOT_FUNDED_16K, C.NOT_MEASURED_256, "STORE ONLY; ORACLE-ADDRESSED", "T-OQ: pairs 1024→4096")) and not C.untagged_positive_labels(pr.printed)
    assert C.saturation_outcome({"F-OQ": inc, "T-OQ": inc, "F-OQ-IVF": inc, "H8": ap}, engineering_failed=False, incomplete=False).row == 6  # H8 alone cannot give SATURATION-PROPORTIONAL
    assert C.saturation_outcome({"F-OQ": ds, "T-OQ": ds}, engineering_failed=False, incomplete=False).label == C.SAT_SUBPROPORTIONAL
    assert C.saturation_outcome({"F-OQ": ds, "T-OQ": inc}, engineering_failed=False, incomplete=False).label == C.SAT_INCONCLUSIVE
    assert C.saturation_outcome({"F-OQ": nm, "T-OQ": nm}, engineering_failed=False, incomplete=False).label == C.SAT_NOT_MEASURED_OUTCOME
    dep = C.saturation_outcome({"F-OQ": C.DEPENDENCE_FAILED, "T-OQ": nm}, engineering_failed=False, incomplete=False)
    assert dep.label == C.SAT_INCONCLUSIVE and "DEPENDENCE_FAILED" in dep.reasons
    assert C.saturation_outcome({}, engineering_failed=True, incomplete=False).label == C.S1_ENGINEERING_FAILURE and C.saturation_outcome({}, engineering_failed=False, incomplete=True).label == C.S1_INCOMPLETE
    for out in (C.saturation_outcome({"F-OQ": ds, "T-OQ": ds}, engineering_failed=False, incomplete=False), dep):
        assert C.NOT_FUNDED_16K in out.printed


# --- groups 9, 11 and 15 at registry level -------------------------------------------------------------------------------------------------------
def test_default_scenario_gives_the_capacity_saturation_and_efficiency_lines_on_the_four_steps(tmp_path: Path) -> None:
    r, d = run(tmp_path, syn.Scenario())
    assert r["assessment"]["status"] == "COMPLETE" and r["assessment"]["cells_read"] == 155 + 7 * 5  # the 155 registered cells and the index read of F-OQ at the seven grid cells (none at 256 slots)
    steps, arms = r["capacity"]["steps"], r["capacity"]["arms"]
    assert {s: steps["F-OQ"][s]["class"] for s in ("C1", "N1", "C2", "N2")} == {"C1": C.CAPACITY_STEP, "N1": C.NOT_LOADED, "C2": C.CAPACITY_STEP, "N2": C.NOT_LOADED}
    assert steps["F-OQ"]["N1"]["verdicts"] == [C.CEILING] * 5 and {steps["F-OQ"][s]["transition"] for s in steps["F-OQ"]} == {"1K→4K", "4K→16K"}
    assert {a: arms[a]["class"] for a in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")} == dict.fromkeys(("F-OQ", "F-OQ-IVF", "T-OQ", "H8"), C.CAPACITY_SUPPORTED)
    out = r["outcome"]["capacity"]
    assert out["label"] == C.CAPACITY_POSITIVE and out["printed"].startswith("CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; WITHIN REGISTERED RUN LENGTHS; 1,024 TO 16,384 SLOTS; 16,384→65,536 NOT TESTED;")
    assert out["reading"].startswith("Storage half supported, as a necessary condition, from 1,024 to 16,384 slots [STORE ONLY; ORACLE-ADDRESSED; arm F-OQ-IVF") and "T-OQ" not in out["reading"].split("arm ")[1].split(";")[0]
    sat = r["saturation"]
    assert {a: v["class"] for a, v in sat["arms"].items()} == dict.fromkeys(("F-OQ", "F-OQ-IVF", "T-OQ", "H8"), C.SAT_PROPORTIONAL_ALL_PAIRS)
    assert set(sat["arms"]["F-OQ"]["pairs"]) == {"256→1024", "1024→4096"} and set(sat["arms"]["T-OQ"]["pairs"]) == {"1024→4096"}
    assert r["outcome"]["saturation"]["label"] == C.SAT_PROPORTIONAL and sat["separability"]
    assert all(v["label"] == C.SAME_AT_SATURATION and v["sublabels"] == [C.DENSE_NOT_LEARNED] for v in sat["dense_at_saturation"].values())  # the synthetic D-OQ stays below the DEP floor
    eff = r["efficiency"]
    assert set(eff["steps"]["F-OQ"]) == {"N1", "N2"} == set(eff["steps"]["T-OQ"])  # the efficiency line ignores C1 and C2
    assert r["outcome"]["efficiency"]["label"] == C.EFFICIENCY_NEGATIVE and "SIZES 1,024–16,384" in r["outcome"]["efficiency"]["printed"]
    assert arms["F-OQ"]["work_label"] == C.LINEAR_KEY_SCORING and arms["T-OQ"]["work_label"] == C.SUBLINEAR
    assert C.h8_annotations([]) == {"2K/1K": "H8 NOT CALIBRATED AT 2K/1K", "8K/1K": "H8 NOT CALIBRATED AT 8K/1K", "32K/4K": "H8 NOT CALIBRATED AT 32K/4K"} and C.h8_annotations(["8K/4K"])["8K/4K"] == C.UNDERTRAINED
    text = rendered(d)
    assert "16,384→65,536 NOT TESTED" in text and "SIZES 1,024–16,384" in text and "16,384 NOT MEASURED — NOT FUNDED" in text and "Saturation line" in text and "H8 NOT CALIBRATED AT 8K/1K" in text
    assert "SATURATION-PROPORTIONAL [STORE ONLY; ORACLE-ADDRESSED; EIGHT FACTS PER SLOT; FULL = PLATEAU RULE WITHIN REGISTERED RUN LENGTHS" in text and "12. Whatever the outcome" in text
    assert r["capacity"]["arms"]["F-OQ"]["dense_detail"]["mc_ambiguous"] == [] or isinstance(r["capacity"]["arms"]["F-OQ"]["dense_detail"]["mc_ambiguous"], list)
    # every registered a_use floor: the 0.80 line is read at 32K/16K at its row's U_P
    assert analysis.largest_cell_a_use(analysis.load_study(d, FRO), "F-OQ") is True


def test_scenarios_that_reach_the_dense_labels_and_the_saturation_verdicts(tmp_path: Path) -> None:
    cat = syn.scenario_catalogue()
    got = {}
    for name, scn in cat.items():
        r, _ = run(tmp_path / name.replace(" ", "_"), scn)
        got[name] = (r["outcome"]["capacity"]["label"], r["outcome"]["saturation"]["label"], {a: (d["label"], d["sublabels"]) for a, d in r["saturation"]["dense_at_saturation"].items()}, {a: v["class"] for a, v in r["saturation"]["arms"].items()})
    assert got["dense holds more at saturation"][2]["F-OQ"][0] == C.DENSE_HOLDS_MORE and got["dense holds more at saturation"][0] == C.CAPACITY_NEGATIVE
    assert got["store holds more at saturation"][2]["F-OQ"][0] == C.STORE_HOLDS_MORE and got["store holds more at saturation"][0] == C.CAPACITY_POSITIVE
    assert got["dense still rising"][2]["F-OQ"] == (C.SAME_AT_SATURATION, [C.DENSE_STILL_RISING])
    assert got["saturation subproportional"][1] == C.SAT_SUBPROPORTIONAL and got["saturation subproportional"][3]["F-OQ"] == C.SAT_DOES_NOT_SCALE and got["saturation subproportional"][3]["T-OQ"] == C.SAT_DOES_NOT_SCALE
    assert got["saturation not full"][1] == C.SAT_NOT_MEASURED_OUTCOME and got["saturation not full"][3]["F-OQ"] == C.SAT_NOT_MEASURED


def test_capacity_negative_clause_a_and_the_inconclusive_scenarios_never_give_a_negative(tmp_path: Path) -> None:
    flat = syn.Scenario(a_max=lambda arm, f, n, rep: 0.15 if arm == "D-OQ" else (1.0 if arm == "R2" else 0.6), tau=lambda arm, f, n: 200.0 if arm == "R2" else 900.0)
    r, d = run(tmp_path / "flat", flat)
    assert all(s["class"] == C.NO_GAIN for s in r["capacity"]["steps"]["F-OQ"].values()) and r["capacity"]["arms"]["F-OQ"]["class"] == C.CAPACITY_NOT_SUPPORTED
    assert r["outcome"]["capacity"]["label"] == C.CAPACITY_NEGATIVE and r["outcome"]["capacity"]["printed"].startswith("CAPACITY-NEGATIVE (a)")
    assert r["outcome"]["capacity"]["reading"].startswith("Storage half not supported for this store, backbone, task and budget") and "16,384→65,536 NOT TESTED" in r["outcome"]["capacity"]["printed"]
    rendered(d)
    ceiling = syn.Scenario(a_max=lambda arm, f, n, rep: 0.15 if arm == "D-OQ" else 1.0, tau=lambda arm, f, n: 200.0)  # every cell at its ceiling: nothing is loaded
    r2, d2 = run(tmp_path / "ceiling", ceiling)
    assert r2["outcome"]["capacity"]["label"] == C.CAPACITY_NOT_TESTED and "16,384→65,536 NOT TESTED" in r2["outcome"]["capacity"]["printed"] and r2["decision_map"][0].startswith("6.")
    assert r2["outcome"]["saturation"]["label"] == C.SAT_NOT_MEASURED_OUTCOME
    rendered(d2)
    for name, scn in {"dependence failed": syn.Scenario(dep_fail=lambda arm, f, n, rep: arm in ("F-OQ", "T-OQ")), "reference not evaluated": syn.Scenario(a_max=lambda arm, f, n, rep: 0.5 if arm == "R2" else (0.15 if arm == "D-OQ" else min(1.0, 0.7 * n / f)))}.items():
        r3, _ = run(tmp_path / name.replace(" ", "_"), scn)
        assert r3["outcome"]["capacity"]["label"] != C.CAPACITY_NEGATIVE and r3["outcome"]["saturation"]["label"] in (C.SAT_INCONCLUSIVE, C.SAT_NOT_MEASURED_OUTCOME), name


def test_a_missing_cell_a_failed_gate_and_the_256_cell_when_the_plan_does_not_run_it(tmp_path: Path) -> None:
    label = core.registered_cells(PLAN)[2].label
    r, _ = run(tmp_path / "m", syn.Scenario(missing={label}))
    a = r["assessment"]
    assert a["status"] == C.S1_INCOMPLETE and label in a["missing_cells"] and r["capacity"] is None and r["saturation"] is None and r["outcome"]["saturation"]["label"] == C.S1_INCOMPLETE
    r2, _ = run(tmp_path / "g", syn.Scenario(gates_ok=False))
    assert r2["assessment"]["status"] == C.S1_ENGINEERING_FAILURE and r2["outcome"]["saturation"]["label"] == C.S1_ENGINEERING_FAILURE
    no256 = fz.Frozen.build(core.Plan(seed_block_draws=(1,), sat256=False), fz.default_cpu_table())
    r3, d3 = run(tmp_path / "n", syn.Scenario(), no256)
    assert r3["assessment"]["cells_read"] == 150 + 7 * 5 and set(r3["saturation"]["arms"]["F-OQ"]["pairs"]) == {"256→1024", "1024→4096"}
    assert r3["saturation"]["arms"]["F-OQ"]["pairs"]["256→1024"]["class"] == C.NOT_FULL and r3["saturation"]["arms"]["F-OQ"]["pairs"]["256→1024"]["note"] == C.NOT_MEASURED_256
    assert r3["saturation"]["arms"]["F-OQ"]["class"] == C.INTERMEDIATE and r3["saturation"]["arms"]["T-OQ"]["class"] == C.SAT_PROPORTIONAL_ALL_PAIRS  # the table's reading (ruling 6)
    assert r3["outcome"]["saturation"]["label"] == C.SAT_PROPORTIONAL and C.NOT_MEASURED_256 in r3["outcome"]["saturation"]["printed"]
    rendered(d3)


def test_a_mc_ambiguous_pair_is_read_in_the_comparators_favour_and_printed(tmp_path: Path) -> None:
    cpu = dict(fz.default_cpu_table())
    cpu[("T-OQ", 16384)] = cpu[("T-OQ", 4096)] * 0.5  # the measured CPU cost falls while the analytic count rises: the two measures disagree
    cpu[("D-OQ", 4096)] = cpu[("T-OQ", 4096)] * 0.5  # D-OQ cheaper than T-OQ by the CPU measure, dearer by the analytic count
    fro = fz.Frozen.build(PLAN, cpu)
    amb = {k: e for k, e in fro.mc.items() if e.annotation == C.MC_AMBIGUOUS}
    assert "cap|T-OQ|C2" in amb and "dense|T-OQ|8K/4K" in amb and amb["cap|T-OQ|C2"].ok() and amb["dense|T-OQ|8K/4K"].ok()
    cap = amb["cap|T-OQ|C2"]
    assert cap.large_update == core.u_p_of(PLAN, 32768)  # the larger cell at U_P, the smaller at the later snapshot
    assert cap.small_update is not None and cap.small_update > cap.large_update
    dense = amb["dense|T-OQ|8K/4K"]
    assert dense.small_update == core.u_p_of(PLAN, 8192) and dense.large_update is not None and dense.large_update > dense.small_update  # the arm at U_P, D-OQ at the later snapshot
    r, d = run(tmp_path, syn.Scenario(), fro)
    assert r["capacity"]["arms"]["T-OQ"]["dense_detail"]["mc_ambiguous"]  # printed: which pairs were MC-AMBIGUOUS
    assert r["capacity"]["steps"]["T-OQ"]["C2"]["replicates"][0]["detail"]["panels"]["A"]["mc_status"] == "OK"
    text = rendered(d)
    assert "MC-AMBIGUOUS pairs" in text and "cap|T-OQ|C2" in text and "dense|T-OQ|8K/4K" in text and "Pairs read per arm: F-OQ 256→1024, 1024→4096" in text
