# ruff: noqa: E501
"""P10IS3 labels and analysis on a synthetic registry with known answers (ADR-0026 sections 6, 12; ruling 16). The expected labels below are worked out by hand from the numbers each Spec states; no test derives its
expectation with the analysis helpers. Self-check only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10i_s3 import analysis, core, labels, synthetic  # noqa: E402
from studies.p10i_s3.core import DENSE, FLAT, FRESH, REP, REPU, TREE  # noqa: E402
from studies.p10i_s3.synthetic import Spec  # noqa: E402

CFG = core.load_config()
PASS = Spec(gain=0.02, p=0.015, xm=0.012)


def run(specs: dict, **kw):  # type: ignore[no-untyped-def]
    edge = kw.pop("edge", ())
    reg = synthetic.registry(CFG, specs, **kw)
    return analysis.analyse(reg, synthetic.rate_table(CFG, edge=edge), CFG)


def fresh(out: dict, line: str = "line1") -> dict:  # type: ignore[type-arg]
    return out["regimes"][FRESH][line]


def specs_for(tree: Spec, dense: Spec | None = None, g: str = FRESH, flat: Spec | None = None) -> dict:  # type: ignore[type-arg]
    d = {(TREE, g): tree, (DENSE, g): dense or Spec(gain=0.03)}
    if flat:
        d[(FLAT, g)] = flat
    return d


# ---------------- line 1 (hand answers) ----------------
def test_dependent() -> None:
    out = run(specs_for(PASS))
    assert fresh(out)["label"] == "DEPENDENT"  # C 0.02 >= 0.005 everywhere; P 0.015 >= 0.5 x 0.02 = 0.01; X_mean 0.012 >= 0.01
    assert out["registered_positive"]["line1"] is True
    assert out["line1"]["label"] == "DEPENDENT"


def test_capacity_without_dependence_names_failing_conditions() -> None:
    assert fresh(run(specs_for(Spec(gain=0.02, p=0.004, xm=0.012))))["detail"]["failing"] == ["D2"]  # P_used mean 0.004 < 0.005 and < half of C
    out = run(specs_for(Spec(gain=0.02, p=0.015, xm=0.009)))  # 0.009 < 0.01 = 0.5 C in every cell: D3 fails, mean 0.009 >= 0.005
    assert fresh(out)["label"] == "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE" and fresh(out)["detail"]["failing"] == ["D3"]
    both = run(specs_for(Spec(gain=0.02, p=0.001, xm=0.001)))
    assert fresh(both)["detail"]["failing"] == ["D2", "D3"]


def test_no_capacity() -> None:
    assert fresh(run(specs_for(Spec(gain=0.004, p=0.05, xm=0.05))))["label"] == "NO CAPACITY"  # mean C 0.004 < 0.005 whatever the controls show


def test_swapped_reads_change_the_answer() -> None:
    a = run(specs_for(Spec(gain=0.02, p=0.015, xm=0.001)))
    b = run(specs_for(Spec(gain=0.02, p=0.001, xm=0.015)))
    assert fresh(a)["detail"]["failing"] == ["D3"] and fresh(b)["detail"]["failing"] == ["D2"]  # a test that mixed the two reads up would fail here


def test_failed_cell_can_never_be_averaged_away() -> None:
    out = run(specs_for(Spec(gain=0.2, p=0.15, xm=0.15, failed=[4])))
    assert fresh(out)["label"] == "NO CAPACITY"  # one failed M-TREE cell: every mean condition of the arm is false
    assert fresh(out, "line2_tree")["label"] == "NOT COMPETITIVE"  # memory failed, dense fine
    out2 = run(specs_for(PASS, Spec(gain=0.03, failed=[0])))
    assert fresh(out2, "line2_tree")["label"] == "NOT EVALUABLE"  # a dense failed cell
    assert out2["regimes"][FRESH]["convergence"][DENSE]["tag"] == "NOT DETERMINED"


def test_cell_count_threshold_22_of_27() -> None:
    def c(n_pos: int) -> list[float]:
        return [0.03 if i < n_pos else -0.001 for i in range(27)]

    # the negative cells are the last ones, spread over parents 7 and 8 and the tail of 6: every parent mean stays positive except where all three seeds are negative
    assert fresh(run(specs_for(Spec(gain=c(21), p=0.05, xm=0.05))))["label"] == "NO CAPACITY"  # 21 < 22
    assert fresh(run(specs_for(Spec(gain=c(22), p=0.05, xm=0.05))))["detail"]["conditions"]["D1"]["ok"] is True


def test_parent_count_threshold_8_of_9() -> None:
    g = [0.03] * 27
    for parent in (0, 1):  # two parents with mean < 0 but only 4 negative cells: 23 positive cells, mean (21 x 0.03 + 2 x 0.0001 - 4 x 0.1) / 27 = 0.0085
        g[3 * parent : 3 * parent + 3] = [-0.1, -0.1, 0.0001]
    d1 = fresh(run(specs_for(Spec(gain=g, p=0.05, xm=0.05))))["detail"]["conditions"]["D1"]
    assert d1["cells"] == 23 and d1["parents"] == 7 and d1["ok"] is False


def test_d2_per_cell_rule_and_collapsed_and_nonfinite() -> None:
    p = [0.05 if i < 21 else 0.001 for i in range(27)]  # mean 0.039 but only 21 cells reach 0.5 C = 0.01
    out = run(specs_for(Spec(gain=0.02, p=p, xm=0.015)))
    assert fresh(out)["detail"]["conditions"]["D2"]["cells"] == 21 and fresh(out)["detail"]["failing"] == ["D2"]
    col = run(specs_for(Spec(gain=0.02, p=0.015, xm=0.015, used_slots=1)))
    assert fresh(col)["label"] == "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE" and len(fresh(col)["detail"]["collapsed"]) == 27
    nf = run(specs_for(Spec(gain=0.02, p=[None] + [0.015] * 26, xm=0.015)))
    assert fresh(nf)["detail"]["failing"] == ["D2"] and fresh(nf)["detail"]["conditions"]["D1"]["ok"] is True  # a non-finite intervention never passes; capacity stays


# ---------------- line 2 ----------------
@pytest.mark.parametrize(
    ("tree", "dense", "label"),
    [
        (0.02, 0.022, "COMPETITIVE"),  # Q = -0.002 >= -0.005 everywhere; 0.02 >= 0.9 x 0.022 = 0.0198
        (0.018, 0.022, "NOT COMPETITIVE"),  # Q = -0.004 passes K1 but 0.018 < 0.0198 fails K2
        (0.03, 0.02, "MEMORY AHEAD"),  # Q = +0.01
        (0.02, 0.03, "NOT COMPETITIVE"),  # Q = -0.01
        (0.0045, 0.003, "NOT EVALUABLE"),  # dense gain below 0.005: the dense adapter adds nothing measurable
    ],
)
def test_line2_rows(tree: float, dense: float, label: str) -> None:
    assert fresh(run(specs_for(Spec(gain=tree), Spec(gain=dense))), "line2_tree")["base_label"] == label


def test_line2_order_row_two_beats_k3() -> None:
    # memory ahead by 0.01 but dense gain 0.004 < 0.005: order row 2 (NOT EVALUABLE) comes before K3
    assert fresh(run(specs_for(Spec(gain=0.014), Spec(gain=0.004))), "line2_tree")["label"] == "NOT EVALUABLE"


def test_tags_edge_and_still_improving() -> None:
    # NOT COMPETITIVE with the memory rate at the edge -> INCONCLUSIVE (MEMORY RATE AT EDGE)
    out = run(specs_for(Spec(gain=0.02), Spec(gain=0.03)), edge=[(TREE, FRESH)])
    assert fresh(out, "line2_tree")["label"] == "INCONCLUSIVE (MEMORY RATE AT EDGE)" and fresh(out, "line2_tree")["base_label"] == "NOT COMPETITIVE"
    out = run(specs_for(Spec(gain=0.02), Spec(gain=0.022)), edge=[(DENSE, FRESH)])
    assert fresh(out, "line2_tree")["label"] == "INCONCLUSIVE (DENSE RATE AT EDGE)"
    # the dense adapter edge does not touch a NOT COMPETITIVE label
    out = run(specs_for(Spec(gain=0.02), Spec(gain=0.03)), edge=[(DENSE, FRESH)])
    assert fresh(out, "line2_tree")["label"] == "NOT COMPETITIVE"
    # the losing arm still improving: memory loses (0.02 < 0.03) and its curve gains 0.02 x 0.2 = 0.004 >= 0.001 between 8192 and U*
    steep = {512: 0.5, 2048: 0.6, 8192: 0.8, 16384: 1.0}
    out = run(specs_for(Spec(gain=0.02, curve=steep), Spec(gain=0.03)))
    assert fresh(out, "line2_tree")["tags"] == ["(MEMORY STILL IMPROVING)"] and fresh(out, "line2_tree")["label"] == "NOT COMPETITIVE"
    # dense loses and is still improving
    out = run(specs_for(Spec(gain=0.04), Spec(gain=0.03, curve=steep)))
    assert fresh(out, "line2_tree")["tags"] == ["(DENSE STILL IMPROVING)"] and fresh(out, "line2_tree")["base_label"] == "MEMORY AHEAD"
    # exactly equal means: neither loses, no tag (ruling 13)
    out = run(specs_for(Spec(gain=0.03, curve=steep), Spec(gain=0.03, curve=steep)))
    assert fresh(out, "line2_tree")["tags"] == []


def test_convergence_and_past_best_tags() -> None:
    out = run(specs_for(Spec(gain=0.02, curve={512: 0.5, 2048: 0.8, 8192: 0.99, 16384: 1.0}), Spec(gain=0.03, curve={512: 0.5, 2048: 0.8, 8192: 0.9, 16384: 1.0})))
    assert out["regimes"][FRESH]["convergence"][TREE]["tag"] == "CONVERGED"  # delta = 0.02 x 0.01 = 0.0002 < 0.001
    assert out["regimes"][FRESH]["convergence"][DENSE]["tag"] == "NOT CONVERGED"  # delta = 0.03 x 0.1 = 0.003
    rising = {512: 1.0, 2048: 1.0, 8192: 1.0, 16384: 0.9}  # the loss rises after 8192: delta < 0, converged by the rule
    assert run(specs_for(Spec(gain=0.02, curve=rising), g=REP))["regimes"][REP]["convergence"][TREE]["tag"] == "CONVERGED"
    # PAST BEST: the U* loss is more than 0.005 above the lowest earlier checkpoint (gain 0.02 -> 0.01: +0.01)
    over = {512: 1.0, 2048: 1.0, 8192: 1.0, 16384: 0.5}
    o = run(specs_for(Spec(gain=0.02, curve=over), g=REP))
    assert o["regimes"][REP]["past_best"][TREE]["flag"] is True and o["regimes"][REP]["line1"]["tags"] == ["(M-TREE PAST BEST CHECKPOINT)"]
    assert o["regimes"][FRESH]["past_best"][TREE]["flag"] is False  # never read in FRESH


# ---------------- registered label and Route A ----------------
def test_registered_label_is_the_fresh_label() -> None:
    specs = {**specs_for(PASS, g=REP), **specs_for(Spec(gain=0.004), g=FRESH), **specs_for(PASS, g=REPU)}
    out = run(specs)
    assert out["regimes"][REP]["line1"]["label"] == "DEPENDENT" and out["regimes"][REPU]["line1"]["label"] == "DEPENDENT"
    assert out["line1"]["label"] == "NO CAPACITY" and out["registered_positive"]["line1"] is False
    assert out["line1"]["regime_labels"] == {"REP-U": "DEPENDENT", "REP": "DEPENDENT"}


def test_inconclusive_fresh_makes_the_line_inconclusive_whatever_the_others_show() -> None:
    specs = {**specs_for(Spec(gain=0.03), Spec(gain=0.03, curve={512: 0.5, 2048: 0.8, 8192: 0.99, 16384: 1.0}), g=REP), **specs_for(Spec(gain=0.02), Spec(gain=0.03))}
    out = run(specs, edge=[(TREE, FRESH)])
    assert out["line2_tree"]["label"].startswith("INCONCLUSIVE") and out["registered_positive"]["line2"] is False


def test_route_a_closed_by_dense_not_converged() -> None:
    conv = {"counts_as_not_converged": True}
    ok = {"counts_as_not_converged": False}
    assert labels.route_a("DEPENDENT", ("COMPETITIVE", "COMPETITIVE"), conv)["route_a_open"] is False
    assert labels.route_a("DEPENDENT", ("COMPETITIVE", "COMPETITIVE"), ok)["route_a_open"] is True
    assert labels.route_a("DEPENDENT", ("MEMORY AHEAD", "MEMORY AHEAD"), ok)["A2"] is True
    assert labels.route_a("CAPACITY WITHOUT DEMONSTRATED DEPENDENCE", ("COMPETITIVE", "COMPETITIVE"), ok)["A1"] is False
    assert labels.route_a("DEPENDENT", ("NOT COMPETITIVE", "NOT COMPETITIVE"), ok)["A2"] is False
    assert labels.route_a("DEPENDENT", ("COMPETITIVE", "INCONCLUSIVE (DENSE RATE AT EDGE)"), ok)["A2"] is False
    # through the analysis: dense converged and NOT converged
    dense_ok = Spec(gain=0.022, curve={512: 0.5, 2048: 0.8, 8192: 0.99, 16384: 1.0})
    assert run(specs_for(PASS, dense_ok))["route_a"]["route_a_open"] is True
    dense_run = Spec(gain=0.022, curve={512: 0.5, 2048: 0.6, 8192: 0.7, 16384: 1.0})
    assert run(specs_for(PASS, dense_run))["route_a"]["route_a_open"] is False


# ---------------- integrity, base, engineering stops ----------------
def test_integrity_failures_are_not_evaluable() -> None:
    assert fresh(run(specs_for(Spec(gain=0.02, bad_disabled=[2]))))["label"] == "NOT EVALUABLE"
    assert fresh(run(specs_for(Spec(gain=0.02, bad_replay=[2]))))["label"] == "NOT EVALUABLE"
    assert fresh(run(specs_for(Spec(gain=0.02, joint_offset=2e-6))))["label"] == "NOT EVALUABLE"  # joint permutation outside 1e-6
    assert fresh(run(specs_for(Spec(gain=0.02, joint_offset=5e-7))))["label"] == "DEPENDENT"  # inside 1e-6
    out = run(specs_for(PASS, Spec(gain=0.03, bad_replay=[1])))
    assert fresh(out, "line2_tree")["label"] == "NOT EVALUABLE" and fresh(out)["label"] == "DEPENDENT"  # a dense integrity case voids line 2 only


def test_base_failure_voids_every_line_in_every_regime() -> None:
    reg = synthetic.registry(CFG, specs_for(PASS))
    reg[core.base_key(3, "replay")] = 2.0 + 1e-9
    out = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    for g in core.REGIMES:
        assert out["regimes"][g]["line1"]["label"] == "NOT EVALUABLE" and out["regimes"][g]["line2_tree"]["label"] == "NOT EVALUABLE"
    del reg[core.base_key(3)]
    assert analysis.analyse(reg, synthetic.rate_table(CFG), CFG)["regimes"][FRESH]["line1"]["label"] == "NOT EVALUABLE"


def test_item_error_and_missing_cells_refuse() -> None:
    reg = synthetic.registry(CFG, specs_for(PASS))
    reg[core.run_key(TREE, FRESH, 0.003, 3)] = {"status": "item_error", "reason": "oom"}
    with pytest.raises(core.EngineeringStop, match="ITEM ERRORS"):
        analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    reg = synthetic.registry(CFG, specs_for(PASS))
    del reg[core.nll_key(DENSE, FRESH, 0.003, 5, 16384, "enabled")]
    with pytest.raises(core.EngineeringStop, match="missing"):
        analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    with pytest.raises(core.EngineeringStop):
        analysis.analyse({}, synthetic.rate_table(CFG), CFG)


def test_nonfinite_at_earlier_checkpoint_is_printed_and_changes_no_label() -> None:
    reg = synthetic.registry(CFG, specs_for(PASS))
    reg[core.nll_key(TREE, FRESH, 0.003, 7, 512, "enabled")] = None
    out = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    assert out["regimes"][FRESH]["line1"]["label"] == "DEPENDENT"
    assert out["descriptive"][FRESH][TREE]["512"]["C"]["n_nonfinite"] == 1


# ---------------- descriptive sections ----------------
def test_routing_reading_rule_and_trend() -> None:
    flat_spec = Spec(gain=0.02)
    # tree gain 0.02 vs flat gain 0.03: G_train = H_tree - H_flat = +0.01 at every checkpoint (curves equal) -> TREE BEHIND
    specs = {**specs_for(Spec(gain=0.02, ex=0.006, pr=0.001), flat=Spec(gain=0.04), g=FRESH), **specs_for(Spec(gain=0.02), flat=flat_spec, g=REP)}
    out = run(specs)
    rows = out["routing"][FRESH]["rows"]
    assert all(rows[k]["G_train_label"] == "TREE BEHIND" for k in rows)
    assert rows[16384]["G_read_label"] == "RESTRICTION COSTS"  # H_tree - H(exhaustive) = +0.006 >= 0.005
    assert out["routing"][FRESH]["G_train_trend"]["trend"] == "NO CHANGE AT THIS RESOLUTION"
    assert out["routing"][REP]["rows"][16384]["G_train_label"] == "WITHIN RESOLUTION"
    assert abs(out["routing"][FRESH]["rows"][16384]["G_prior_stats"]["mean"] - 0.001) < 1e-12  # G_prior printed with no label
    # the label changes with duration: flat catches up only late
    late = {512: 1.0, 2048: 1.0, 8192: 1.0, 16384: 1.0}
    early = {512: 0.5, 2048: 0.5, 8192: 0.5, 16384: 1.0}
    out2 = run({**specs_for(Spec(gain=0.02, curve=late), flat=Spec(gain=0.02, curve=early), g=FRESH), **specs_for(PASS, flat=PASS, g=REP)})
    r2 = out2["routing"][FRESH]
    assert r2["rows"][512]["G_train_label"] == "TREE AHEAD" and r2["rows"][16384]["G_train_label"] == "WITHIN RESOLUTION"
    assert r2["G_train_trend"]["trend"] == "GAP CHANGES WITH DURATION"
    assert abs(r2["G_train_trend"]["delta_G"]["mean"] - 0.01) < 1e-9  # dG = G(U*) - G(512) = 0 - (-0.01)


def test_descriptive_six_parent_and_contrasts_are_unlabelled() -> None:
    out = run(specs_for(PASS))
    sp = out["six_parent"][FRESH]
    assert sp["cells"] == 18 and sp["parents"] == 6 and "label" not in sp
    assert "label" not in out["contrasts"][FRESH]["16384"]
    d = out["descriptive"][FRESH][TREE]["16384"]
    assert d["n_P_used_above_baseline"] == 0 and d["n_X_mean_above_baseline"] == 0  # B - H_used > 0: the intervention loses the gain but stays under baseline
    assert d["B-H_P_used"]["mean"] == pytest.approx(0.005) and d["B-H_X_mean"]["mean"] == pytest.approx(0.008)


def test_misfiring_intervention_above_baseline_is_counted() -> None:
    out = run(specs_for(Spec(gain=0.02, p=0.05, xm=0.05)))
    d = out["descriptive"][FRESH][TREE]["16384"]
    assert d["n_P_used_above_baseline"] == 27 and d["n_X_mean_above_baseline"] == 27


def test_p4_rate_anchor_only_when_rate_differs() -> None:
    reg = synthetic.registry(CFG, specs_for(PASS), rates={(TREE, REP): 0.01})
    for c in range(27):  # the anchor runs at 0.003 exist for REP, TREE (and D-ADAPT if its rate differs)
        for k in CFG["duration"]["checkpoints"]:
            reg[core.nll_key(TREE, REP, 0.003, c, k, "enabled")] = 2.0 - 0.01
            reg[core.run_key(TREE, REP, 0.003, c)] = {"status": "ok"}
    rt = synthetic.rate_table(CFG, rates={(TREE, REP): 0.01})
    out = analysis.analyse(reg, rt, CFG)
    assert list(out["anchor"]) == [TREE] and out["anchor"][TREE]["C_at_p4_rate"]["mean"] == pytest.approx(0.01)


def test_label_functions_compare_exactly_as_written() -> None:
    th = core.Thresholds.from_config(CFG)
    assert labels.d1([0.00500001] * 27, th)["ok"] is True
    assert labels.d1([0.0049999] * 27, th)["ok"] is False
    assert labels.convergence_tag(0.5, 0.4995, 0.001)["tag"] == "CONVERGED"  # delta 0.0005 < 0.001
    assert labels.convergence_tag(0.5, 0.498, 0.001)["tag"] == "NOT CONVERGED"
    assert labels.convergence_tag(0.5, 0.498, 0.001, failed=True)["tag"] == "NOT DETERMINED"
    assert labels.convergence_tag(0.5, 0.498, 0.001, failed=True)["counts_as_not_converged"] is True
