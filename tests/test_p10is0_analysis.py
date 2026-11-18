# ruff: noqa: E501
"""P10IS0 analysis (ADR-0023 sections 6 to 8) on synthetic registries with known answers: the headlines, per-series states, reference flags, events that let the study proceed, missing cells, item errors, X8, convergence tags,
the paired annotation and the descriptive tags. Expected answers are written out here by hand, not derived with the analysis's helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is0 import analysis, core, labels  # noqa: E402
from studies.p10is0.analysis import AnalysisRefused, CellRecord  # noqa: E402
from studies.p10is0.labels import Obs  # noqa: E402

CFG = core.load_config()
CTS = core.cell_types(CFG, include_x8=True)
DRAWS = range(1, 11)
N = 1000


def obs(acc: float = 0.95, *, h: float | None = None, a_use: float | None = None, stab: float = 0.95, distinct: int = 200, leak: bool = False, lm: float = 0.0) -> Obs:
    c = round(acc * N)
    hc = round((acc if h is None else h) * N)
    au = acc if a_use is None else a_use
    return Obs((c, N), (c, N), (hc, N), (hc, N), True, True, leak, distinct, 0.01, 256, lm, stab, au, au)


def rec(o: Obs, *, half: Obs | None = None) -> CellRecord:
    return CellRecord("ok", {"e512": o, "half": half or o, "T": o})


def default_entry() -> dict[str, object]:
    return {"t_exposures": 1024, "convergence": "SHOWN", "flat_below_floor": False, "reference_flags": {"cond4": False, "other": []}}


def registry(bad: dict[tuple[str, str, int], CellRecord] | None = None) -> dict[analysis.Key, CellRecord]:
    reg: dict[analysis.Key, CellRecord] = {}
    for ct in CTS:
        for arm in ct.arms:
            for d in DRAWS:
                reg[(ct.name, arm, d)] = rec(obs())
    reg.update(bad or {})
    return reg


def durations(**over: dict[str, object]) -> dict[str, dict[str, object]]:
    out = {ct.name: default_entry() for ct in CTS}
    for k, v in over.items():
        out[k.replace("_", "/", 1).replace("_", "")] = {**default_entry(), **v}
    return out


def fails(ct: str, arm: str, draws: range | list[int], record: CellRecord) -> dict[tuple[str, str, int], CellRecord]:
    return {(ct, arm, d): record for d in draws}


def run(reg: dict[analysis.Key, CellRecord], dur: dict[str, dict[str, object]] | None = None, **kw: object) -> dict[str, object]:
    return analysis.analyze(reg, dur or durations(), cfg=CFG, **kw)  # type: ignore[arg-type]


def head(out: dict[str, object]) -> str:
    return out["headline"]["text"]  # type: ignore[index]


def test_everything_holds_triggers_x8_and_load_8() -> None:
    out = run(registry())
    assert head(out) == "OVERLOAD-QUALIFIED UP TO 4; NO BREAK FOUND ON THE GRID; LOAD 8 INCOMPLETE"
    assert out["x8"]["triggered"] is True and out["x8"]["label"] == "ONE SERIES"  # type: ignore[index]
    done = run(registry(), x8_status="COMPLETE")
    assert head(done) == "OVERLOAD-QUALIFIED UP TO 8; NO BREAK FOUND ON THE GRID"
    assert out["annotations"]["licence_loads"] == [0.5, 1.0, 2.0, 4.0]  # type: ignore[index]


def test_break_at_load_two_in_series_m_confirmed_and_unresolved() -> None:
    bad = fails("8K/4K", "A5-D", range(1, 4), rec(obs(0.5)))  # condition 1 (and 4's ratio holds): three failing cells: n_A = 3
    out = run(registry(bad))
    assert head(out) == "OVERLOAD NOT QUALIFIED AT ℓ₁; ADDRESSING QUALIFIED UP TO 1"
    assert out["states_by_load_series"]["2"]["M"]["Q"] == "FAILS" and out["states_by_load_series"]["2"]["S"]["Q"] == "HOLDS"  # type: ignore[index]
    assert out["l1_failure_counts_by_series"]["M"][1] == 3 and out["holds_in_one_series_only"]["2"].startswith("IN SERIES S ONLY (slots 1024)")  # type: ignore[index]
    assert out["x8"]["triggered"] is False  # type: ignore[index]
    rising = {(("8K/4K", "A5-D", d)): rec(obs(0.5), half=obs(0.40)) for d in range(1, 4)}  # m(T) - m(T/2) = +0.10 on three cells and 0 on seven: the median is 0 ...
    rising = {("8K/4K", "A5-D", d): rec(obs(0.5), half=obs(0.40)) for d in range(1, 11)}  # ... so make it all ten cells
    out2 = run(registry(rising))
    assert head(out2) == "OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (RISING); ADDRESSING QUALIFIED UP TO 1"
    out3 = run(registry(bad), durations(**{"8K_4K": {"convergence": labels.NOT_SHOWN_REFUSED}}))
    assert head(out3) == "OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (NOT SHOWN); ADDRESSING QUALIFIED UP TO 1"
    assert labels.NOT_SHOWN_REFUSED in out3["types"]["8K/4K"]["labels"]  # type: ignore[index]


def test_declining_at_t_tag() -> None:
    declining = {("8K/4K", "A5-D", d): rec(obs(0.5), half=obs(0.60)) for d in range(1, 11)}
    assert head(run(registry(declining))).startswith("OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (DECLINING AT T)")


def test_anchor_not_evaluable_and_anchor_fails() -> None:
    low_ref = fails("8K/16K", "A6", range(1, 6), rec(obs(0.30)))
    assert head(run(registry(low_ref))) == labels.HEAD_ANCHOR_NE
    bad = fails("2K/4K", "A5-D", range(1, 4), rec(obs(0.5)))
    assert head(run(registry(bad))).startswith(labels.HEAD_ANCHOR_FAILS)


def test_held_out_failures_make_line_g_fail_not_line_a() -> None:
    bad = fails("8K/4K", "A5-D", range(1, 4), rec(obs(0.95, h=0.5)))  # condition 4 only
    out = run(registry(bad))
    st = out["states_by_load_series"]["2"]["M"]  # type: ignore[index]
    assert (st["A"], st["G"], st["Q"]) == ("HOLDS", "FAILS", "FAILS")
    assert out["lines"]["A"]["L"] == 4 and out["lines"]["G"]["L"] == 1 and out["lines"]["Q"]["L"] == 1  # type: ignore[index]
    assert out["annotations"]["hypotheses"]["H23-G"] == "supported" and out["annotations"]["hypotheses"]["H23-O"] == "not supported"  # type: ignore[index]


def test_flag_on_condition_4_keeps_line_a_and_prints_not_evaluable() -> None:
    dur = durations(**{"8K_4K": {"reference_flags": {"cond4": True, "other": []}}})
    reg = registry()
    out = run(reg, dur)
    st = out["states_by_load_series"]["2"]["M"]  # type: ignore[index]
    assert (st["A"], st["G"], st["Q"]) == ("HOLDS", "NOT EVALUABLE", "NOT EVALUABLE")
    assert head(out) == "OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO 1"  # load 2: M NE, S holds -> NE
    assert out["l1_line_a_beside_headline"] == {"M": "HOLDS"}  # type: ignore[index]
    assert "REFERENCE ALSO FAILS CONDITION 4 (A6 H-ratio x on calibration draws)" in out["types"]["8K/4K"]["labels"]  # type: ignore[index]
    two = run({**reg, **fails("8K/4K", "A5-D", range(1, 3), rec(obs(0.5)))}, dur)  # n_A = 2: Line Q FAILS whatever condition 4 gives
    assert two["states_by_load_series"]["2"]["M"]["Q"] == "FAILS" and two["states_by_load_series"]["2"]["M"]["G"] == "NOT EVALUABLE"  # type: ignore[index]
    unstable = run({**reg, **fails("8K/4K", "A5-D", DRAWS, rec(obs(stab=0.3)))}, dur)  # Line A holds but not ADDRESS STABLE: FAILS
    assert unstable["states_by_load_series"]["2"]["M"]["Q"] == "FAILS"  # type: ignore[index]
    assert head(unstable).startswith("OVERLOAD NOT QUALIFIED AT ℓ₁") and "which_line" in unstable["headline"]["detail"]  # type: ignore[index]
    assert unstable["headline"]["detail"]["which_line"]["M"].startswith("LINE A HOLDS; LINE G NOT EVALUABLE — REFERENCE; THE COMPOSITE FAILS ON ADDRESS STABLE")  # type: ignore[index]


def test_removed_cell_type_and_events_do_not_stop_the_study() -> None:
    dur = durations(**{"2K_1K": {"reference_flags": {"cond4": False, "other": [6]}, "removed": True}})
    reg = {k: v for k, v in registry().items() if not (k[0] == "2K/1K")}  # removed from the plan: no records
    out = run(reg, dur)
    assert out["states_by_load_series"]["2"]["S"]["combination"] == 1  # type: ignore[index]
    assert "NOT RUN — REFERENCE FAILS CONDITION 6" in out["types"]["2K/1K"]["labels"] and out["missing_cells"] == []  # type: ignore[index]
    assert head(out) == "OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO 1"


def test_a_flag_at_load_four_alone_does_not_change_lower_loads() -> None:
    dur = durations(**{"8K_2K": {"reference_flags": {"cond4": False, "other": [3]}, "removed": True}})
    reg = {k: v for k, v in registry().items() if k[0] != "8K/2K"}
    out = run(reg, dur)
    assert out["lines"]["Q"]["L"] == 2 and head(out).startswith("OVERLOAD-QUALIFIED UP TO 2; NOT EVALUABLE AT ℓ₁ — REFERENCE")  # type: ignore[index]


def test_missing_cells_paused_and_item_errors_refuse() -> None:
    reg = registry()
    del reg[("8K/4K", "A5-D", 3)]
    out = run(reg)
    assert head(out) == labels.HEAD_PAUSED and out["scientific_labels"] is None and out["missing_cells"] == ["REG-M-A5-D-8K-4K-d03-i330001"]  # type: ignore[index]
    with pytest.raises(AnalysisRefused):
        run(registry(), item_errors=["REG-M-A5-D-8K-4K-d03-i330001: ValueError"])
    assert head(run(registry(), gate_failed=True)) == labels.HEAD_ENGINEERING
    assert head(run(registry(), paused=True)) == labels.HEAD_PAUSED


def test_non_finite_learned_cells_fail_and_non_finite_reference_is_not_evaluated() -> None:
    nf = {("8K/4K", "A5-D", d): CellRecord("nonfinite", {}, 42) for d in range(1, 4)}
    out = run(registry(nf))
    assert out["types"]["8K/4K"]["descriptive"]["non_finite_cells"] == {1: 42, 2: 42, 3: 42}  # type: ignore[index]
    assert head(out) == "OVERLOAD NOT QUALIFIED AT ℓ₁; ADDRESSING QUALIFIED UP TO 1"
    ref = {("8K/4K", "A6", d): CellRecord("nonfinite", {}, 9) for d in range(1, 4)}
    assert run(registry(ref))["states_by_load_series"]["2"]["M"]["Q"] == "NOT EVALUABLE"  # type: ignore[index]


def test_descriptive_tags() -> None:
    higher = {(("8K/4K", "A6", d)): rec(obs(0.60)) for d in DRAWS}
    out = run(registry({**higher, **{("8K/4K", "A5-D", d): rec(obs(0.70)) for d in DRAWS}}))
    labs = out["types"]["8K/4K"]["labels"]  # type: ignore[index]
    assert "RATIO ABOVE 1" in labs and "QUALIFIED RELATIVE TO A DEGRADED REFERENCE" in labs
    assert out["types"]["8K/4K"]["descriptive"]["regime"].startswith("REFERENCE DEGRADED (A6 = 0.600")  # type: ignore[index]
    assert out["types"]["8K/16K"]["descriptive"]["regime"] == "REFERENCE NEAR CEILING"  # type: ignore[index]
    flat = durations(**{"8K_16K": {"flat_below_floor": True}})
    assert labels.FLAT_BELOW_FLOOR in run(registry(), flat)["types"]["8K/16K"]["labels"]  # type: ignore[index]
    assert out["types"]["8K/4K"]["descriptive"]["e512_readout"]["label"].startswith("P10-S0's regime on new draws")  # type: ignore[index]
    assert out["false_negative_table"][0]["kind"] == "ANALYTICAL"  # type: ignore[index]


def test_penalty_annotation_and_h23_p() -> None:
    a0_fail = fails("8K/4K", "A0", range(1, 7), rec(obs(0.3)))
    out = run(registry(a0_fail))
    assert out["annotations"]["penalty_vs_a0"]["8K/4K"]["label"] == labels.IMPROVES and out["annotations"]["penalty_vs_a0"]["8K/4K"]["pairs"] == 10  # type: ignore[index]
    assert out["annotations"]["hypotheses"]["H23-P"] == "supported"  # type: ignore[index]
    assert out["annotations"]["penalty_vs_a0"]["8K/16K"]["label"] == labels.NOT_DISTINGUISHED  # type: ignore[index]


def test_replaced_draw_is_printed_and_x8_flag_runs() -> None:
    out = run(registry(), replaced_draws={4: "p10is0-reserve-1"})
    assert out["replaced_draws"] == {4: "p10is0-reserve-1"}
    dur = durations(**{"8K_1K": {"reference_flags": {"cond4": True, "other": []}}})
    done = run(registry(), dur, x8_status="COMPLETE")
    assert head(done) == "OVERLOAD-QUALIFIED UP TO 4; NOT EVALUABLE AT ℓ₁ — REFERENCE"
    paused = run(registry(), x8_status="PAUSED")
    assert head(paused).endswith("LOAD 8 PAUSED")


def test_lane_licence_is_empty_without_a_qualified_anchor() -> None:
    bad = fails("2K/4K", "A5-D", range(1, 4), rec(obs(0.5)))
    out = run(registry(bad))
    assert out["annotations"]["licence_loads"] == [] and out["licence_text"].startswith("OMITTED")  # type: ignore[index]
