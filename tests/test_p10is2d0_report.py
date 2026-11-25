# ruff: noqa: E501
"""P10-I-S2-D0 (ADR-0035 sections 6 and 7): the decomposition's telescoping arithmetic, the interaction, the fixed wording under both orders, the counterfactual RET arithmetic and the label lines."""

import importlib
from types import ModuleType

import pytest


def _m(name: str) -> ModuleType:
    return importlib.import_module(f"studies.p10is2d0.{name}")


def means(b1: float, d1: float, e1: float, a: float, g1: float) -> dict[str, float]:
    return {"b1": b1, "d1": d1, "e1": e1, "a": a, "g1": g1}


def test_the_three_terms_telescope_to_t_exactly() -> None:
    rep = _m("report")
    d = rep.decompose(means(0.70, 0.66, 0.61, 0.60, 0.65), registered_f=0.10)
    assert d["T"] == pytest.approx(0.10)
    assert d["i"] + d["ii"] + d["iii"] == pytest.approx(d["T"], abs=1e-12)
    assert d["residual"] == pytest.approx(0.0, abs=1e-15)
    assert d["i"] == pytest.approx(0.04) and d["ii"] == pytest.approx(0.05) and d["iii"] == pytest.approx(0.01)


def test_values_first_order_and_the_interaction() -> None:
    rep = _m("report")
    d = rep.decompose(means(0.70, 0.66, 0.61, 0.60, 0.65), registered_f=0.10)
    assert d["values_first_values"] == pytest.approx(0.05)  # s[b1] - s[g1]
    assert d["values_first_competition"] == pytest.approx(0.05)  # s[g1] - s[a]
    assert d["interaction"] == pytest.approx(d["iii"] - 0.05)
    assert d["shares"]["competition_path"] == pytest.approx(0.9)
    assert d["shares"]["values_path"] == pytest.approx(0.1)
    assert d["shares"]["competition_values_first"] == pytest.approx(0.5)
    assert d["shares"]["values_values_first"] == pytest.approx(0.5)


def test_a_residual_against_the_registered_f_is_printed_not_hidden() -> None:
    rep = _m("report")
    d = rep.decompose(means(0.70, 0.66, 0.61, 0.60, 0.65), registered_f=0.1000001)
    assert d["residual"] == pytest.approx(1e-7, rel=1e-3)


def test_the_append_point_decomposition_has_no_values_term() -> None:
    rep = _m("report")
    d = rep.decompose_append(s_m1=0.70, s_d1_append=0.67, s_a_append=0.66)
    assert d["i"] == pytest.approx(0.03) and d["ii"] == pytest.approx(0.01) and d["iii"] == 0.0
    assert d["T"] == pytest.approx(0.04)


def test_summary_word_needs_five_of_six_cells() -> None:
    rep = _m("report")
    five = [0.7, 0.7, 0.7, 0.7, 0.7, 0.3]
    assert rep.summary_word(five, [1 - x for x in five]) == "COMPETITION-LARGER"
    four = [0.7, 0.7, 0.7, 0.7, 0.5, 0.5]
    assert rep.summary_word(four, [1 - x for x in four]) == "MIXED"
    vals = [0.8, 0.8, 0.8, 0.8, 0.8, 0.1]
    assert rep.summary_word([1 - x for x in vals], vals) == "VALUES-LARGER"
    assert rep.summary_word([2 / 3] * 6, [1 / 3] * 6) == "COMPETITION-LARGER"  # >= 2/3 is inclusive


def test_a_cell_with_no_positive_total_never_counts_toward_a_word() -> None:
    rep = _m("report")
    shares = [0.9, 0.9, 0.9, 0.9, None, None]  # four defined cells of six: never enough
    assert rep.summary_word(shares, [None if x is None else 1 - x for x in shares]) == "MIXED"
    assert rep.share(0.01, -0.02) is None
    assert rep.share(0.01, 0.0) is None
    assert rep.share(0.02, 0.04) == pytest.approx(0.5)


def test_order_dependent_is_added_on_a_large_interaction_or_differing_words() -> None:
    rep = _m("report")
    comp = [0.9] * 6
    val = [0.1] * 6
    small = rep.final_wording(path=("COMPETITION-LARGER"), values_first="COMPETITION-LARGER", interactions=[0.001] * 6, totals=[0.06] * 6)
    assert small == "COMPETITION-LARGER"
    big = rep.final_wording(path="COMPETITION-LARGER", values_first="COMPETITION-LARGER", interactions=[0.001, 0.001, 0.025, 0.001, 0.001, 0.001], totals=[0.06] * 6)
    assert big == "COMPETITION-LARGER; ORDER-DEPENDENT"  # |0.025| >= 0.06 / 3 in one cell
    differ = rep.final_wording(path="COMPETITION-LARGER", values_first="MIXED", interactions=[0.0] * 6, totals=[0.06] * 6)
    assert differ == "COMPETITION-LARGER; ORDER-DEPENDENT"
    assert comp and val


def test_counterfactual_ret_arithmetic_uses_the_unchanged_thresholds() -> None:
    rep = _m("report")
    assert rep.counterfactual_ret(forgetting=0.03, rho=0.90, evaluable=True, f_max=0.03, rho_min=0.90) == "HOLDS"
    assert rep.counterfactual_ret(forgetting=0.031, rho=0.95, evaluable=True, f_max=0.03, rho_min=0.90) == "DOES NOT HOLD"
    assert rep.counterfactual_ret(forgetting=0.0, rho=0.89, evaluable=True, f_max=0.03, rho_min=0.90) == "DOES NOT HOLD"
    assert rep.counterfactual_ret(forgetting=0.0, rho=1.0, evaluable=False, f_max=0.03, rho_min=0.90) == "NOT EVALUABLE"


def test_paired_contrast_uses_the_sample_standard_deviation() -> None:
    rep = _m("report")
    x = [1.0, 2.0, 4.0, 7.0]
    y = [0.0, 2.0, 1.0, 3.0]
    c = rep.paired_contrast(x, y)
    diffs = [1.0, 0.0, 3.0, 4.0]
    m = sum(diffs) / 4
    sd = (sum((d - m) ** 2 for d in diffs) / 3) ** 0.5
    assert c["mean"] == pytest.approx(m)
    assert c["se"] == pytest.approx(sd / 4**0.5)
    assert c["n"] == 4


def test_every_block_carries_the_oracle_line_and_the_posthoc_line() -> None:
    rep = _m("report")
    from studies.p10is2.common import core

    out = rep.block("T", ["a line", "another"])
    lines = out.splitlines()
    assert lines[0] == core.ORACLE_LINE
    assert lines[1] == "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL"
    assert rep.POSTHOC in lines
    with pytest.raises(ValueError):
        rep.require_labelled("no label here")
    assert rep.require_labelled(out) == out
