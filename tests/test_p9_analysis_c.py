# ruff: noqa: E501
"""P9 Lane C analysis (package I6): the Lane C gate, locality classes (all of them), hierarchy advantage, planted
classes, D09 sweep and the key-traffic identity.

Synthetic evaluation and simulation records only. Self-check only: not independent review, not Astra
validation, not human approval.
"""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p9_analysis_synth import IDENTITY, E, Synth, case_cells, fill, patch  # noqa: E402

from studies.p9 import analysis_a as A  # noqa: E402
from studies.p9 import analysis_c as C  # noqa: E402
from studies.p9 import core  # noqa: E402

FLAT, TREE = "flat", "learned_tree"
STREAMS = {"A": "panel_a", "B": "panel_b"}


def eval_world(
    *, b1_acc: float = 0.9, c1_acc: float = 0.9, c1_ustar: int = 1000, step_ok: bool = True
) -> Synth:
    """A1/A2 at 4K, 16K, 64K (strong), B1 and C1 at 16K."""
    w = Synth()
    fill(
        w,
        ("A1", "A2"),
        (lambda c: (0.9, 0.9))
        if step_ok
        else (lambda c: (0.2, 0.05) if c.slots == 16384 else (0.9, 0.9)),
    )
    for c in core.cells():
        if c.slots == 16384 and c.parent == core.PRIMARY_PARENT:
            if c.block == "B1":
                w.cell(c, b1_acc)
            elif c.block == "C1":
                w.cell(c, c1_acc, useful_slots=c1_ustar)
    return w


def sim_rec(
    label: str,
    update: int,
    stream: str,
    rows: int,
    rho: float,
    tie: str,
    *,
    e: float | None,
    misses: int = 1000,
    degenerate: bool = False,
    layout: str | None = None,
    null_rate: float = 0.3,
) -> dict[str, Any]:
    return {
        "kind": "sim", "schema": 1, "study": "P9", "label": label, "update": update, "stream": stream, "trace_kind": "answer",
        "layout": layout or f"coaccess@{rows}", "rows_per_page": rows, "cache_fraction": rho, "cache_pages": 10 * rows,
        "working_set": 4000, "tie": tie, "actual_misses": misses, "null_misses": [1100, 1000, 1200], "null_miss_rate": null_rate,
        "e_ratio": e, "degenerate": degenerate, "pages_per_query": 3.0, "cross_query_reuse": 0.4, "identity": IDENTITY,
    }  # fmt: skip


EFn = Callable[[core.Cell, int, float, str, str], float | None]
RAW = Callable[[core.Cell, int, float, str, str], int]


def make_sims(
    e_fn: EFn,
    misses_fn: RAW | None = None,
    degenerate_fn: Callable[[core.Cell, int, float, str, str], bool] | None = None,
    sweep: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    sims: dict[str, list[dict[str, Any]]] = {}
    rhos = core.CACHE_RHOS_SWEEP if sweep else core.CACHE_RHOS_PRIMARY
    rows_all = core.CACHE_ROWS_SWEEP if sweep else core.CACHE_ROWS_PRIMARY
    for c in core.cells():
        if c.slots != 16384 or c.parent != core.PRIMARY_PARENT or c.block not in ("A1", "C1"):
            continue
        for panel, stream in STREAMS.items():
            for rho in rhos:
                for rows in rows_all:
                    for tie in core.TIE_RULES:
                        sims.setdefault(c.label, []).append(
                            sim_rec(
                                c.label, core.updates(c, E), stream, rows, rho, tie,
                                e=e_fn(c, rows, rho, tie, panel),
                                misses=misses_fn(c, rows, rho, tie, panel) if misses_fn else 1000,
                                degenerate=degenerate_fn(c, rows, rho, tie, panel) if degenerate_fn else False,
                            )
                        )  # fmt: skip
    return sims


def e_const(case_e: float, ref_e: float = 0.9) -> EFn:
    return lambda c, rows, rho, tie, panel: ref_e if c.block == "A1" else case_e


def group(arch: str = FLAT, alpha_c: float = 0.05) -> list[core.Cell]:
    return case_cells("C1", arch, 0.25, alpha_c)


def classify(
    world: Synth, sims: Any, arch: str = FLAT, alpha_c: float = 0.05, **kw: Any
) -> core.ClassResult:
    return C.classify_locality(world.index, sims, group(arch, alpha_c), E, **kw)


# --- the pure rule (also used by the planted traces) ----------------------------------------------------------------
def S(e: float | None, raw: float | None = 1.0, degenerate: bool = False) -> C.Setting:
    return C.Setting(e, raw, degenerate)


def test_locality_class_rows_in_order() -> None:
    eight = lambda e, raw=1.0: [S(e, raw) for _ in range(8)]  # noqa: E731
    ok = {"collapsed": False, "quality_failed": False, "utilization_ok": True}
    assert C.locality_class(eight(0.6), **ok) == "LOCALITY_POSITIVE"
    assert (
        C.locality_class(eight(0.6), collapsed=True, quality_failed=False, utilization_ok=True)
        == C.QUALITY_FAILED
    )
    assert (
        C.locality_class(eight(0.6), collapsed=False, quality_failed=True, utilization_ok=True)
        == C.QUALITY_FAILED
    )
    # COLLAPSED comes before DEGENERATE (a collapsed cell usually has a degenerate null)
    assert (
        C.locality_class(
            [S(None, None, True)], collapsed=True, quality_failed=False, utilization_ok=False
        )
        == C.QUALITY_FAILED
    )
    assert C.locality_class([*eight(0.6), S(0.6, 1.0, True)], **ok) == "DEGENERATE"
    assert (
        C.locality_class(eight(0.6), collapsed=False, quality_failed=False, utilization_ok=False)
        == core.INTERMEDIATE
    )  # not utilization preserved
    assert C.locality_class(eight(0.95, 0.7), **ok) == "CONCENTRATION_ONLY"
    assert C.locality_class(eight(0.95, 0.9), **ok) == "NO DIFFERENCE"
    assert (
        C.locality_class(eight(1.2), **ok) == "WORSE"
        and C.locality_class(eight(1.10), **ok) == "WORSE"
    )
    assert (
        C.locality_class(eight(0.90, 0.7), **ok) == core.INTERMEDIATE
    )  # E ratio exactly 0.90 is not above 0.90
    assert C.locality_class([*eight(0.6), S(1.0)], **ok) == core.INTERMEDIATE  # settings disagree
    assert C.locality_class([], **ok) == core.INTERMEDIATE
    assert (
        C.locality_class(eight(0.80), **ok) == "LOCALITY_POSITIVE"
    )  # E ratio <= 0.80 includes 0.80


@pytest.mark.parametrize(
    ("kind", "settings", "expected"),
    [
        ("popularity_only", [S(1.0, 1.0)] * 8, "NO DIFFERENCE"),
        ("clusters_random_sharing", [S(0.99, 1.0)] * 8, "NO DIFFERENCE"),
        ("clusters_aligned_sharing", [S(0.4, 0.4)] * 8, "LOCALITY_POSITIVE"),
        ("collapsed_single_set", [S(None, None, True)] * 8, "DEGENERATE"),
        ("working_set_below_cache", [S(None, None, True)] * 8, "DEGENERATE"),
    ],
)
def test_planted_trace_classes(kind: str, settings: list[C.Setting], expected: str) -> None:
    cls = C.locality_class(settings, collapsed=False, quality_failed=False, utilization_ok=True)
    assert cls == expected == C.SYNTHETIC_EXPECTED[kind]
    assert C.classify_planted(kind, cls) is True and C.classify_planted(kind, "WORSE") is False


def test_planted_incomplete_input_gives_incomplete() -> None:
    r = C.classify_locality(eval_world().index, {}, group(), E)
    assert r["cls"] == A.INCOMPLETE and r["details"]["missing"]
    assert C.classify_planted("incomplete_input", r["cls"]) is True
    with pytest.raises(ValueError):
        C.classify_planted("nope", "x")
    assert set(C.SYNTHETIC_EXPECTED.values()) == {
        "NO DIFFERENCE",
        "LOCALITY_POSITIVE",
        "DEGENERATE",
        "INCOMPLETE",
    }


# --- the gate ----------------------------------------------------------------------------------------------------------
def test_gate_passes_with_supported_step_and_preserved_b1() -> None:
    gate = C.lane_c_gate(eval_world().index, FLAT, E)
    assert (
        gate["passed"] is True
        and gate["step_supported"] == {"A": True, "B": True}
        and gate["b1_class"] == "UTILIZATION_PRESERVED"
        and gate["reasons"] == []
    )


def test_gate_fails_when_the_b1_usage_only_cell_collapses_and_h17_loc_is_not_evaluated() -> None:
    w = eval_world()
    for c in case_cells("B1", FLAT, 0.25):
        patch(w, c, useful_slots=600)
    gate = C.lane_c_gate(w.index, FLAT, E)
    assert gate["passed"] is False and gate["b1_class"] == "COLLAPSED"
    r = classify(w, make_sims(e_const(0.5)))
    assert (
        r["cls"] == C.H17_LOC_NOT_EVALUATED
        and C.is_not_evaluated(r["cls"])
        and C.H17_LOC_NOT_EVALUATED in r["annotations"]
    )
    assert r["details"]["descriptive_class"] in (
        "LOCALITY_POSITIVE",
        C.QUALITY_FAILED,
    )  # descriptive only; never promoted
    assert r["details"]["gate"]["passed"] is False


def test_gate_fails_when_the_capacity_step_is_not_supported() -> None:
    w = eval_world(step_ok=False)
    gate = C.lane_c_gate(w.index, FLAT, E)
    assert gate["passed"] is False and any("4K->16K" in r for r in gate["reasons"])
    assert classify(w, make_sims(e_const(0.5)))["cls"] == C.H17_LOC_NOT_EVALUATED


def test_gate_fails_on_ceiling_fail_and_is_per_architecture() -> None:
    w = eval_world()
    assert C.lane_c_gate(w.index, FLAT, E, ceiling_fail=(16384,))["passed"] is False
    assert C.lane_c_gate(w.index, FLAT, E, ceiling_fail=(65536,))["passed"] is True
    for c in core.cells():
        if c.block == "A2" and c.slots == 4096:
            patch(w, c, correct=40, accuracy=40 / 2048)  # the tree's 4K cells are at chance
    assert (
        C.lane_c_gate(w.index, TREE, E)["passed"] is False
        and C.lane_c_gate(w.index, FLAT, E)["passed"] is True
    )
    ceiling = classify(eval_world(), make_sims(e_const(0.5)), ceiling_fail=(16384,))
    assert (
        ceiling["cls"] == C.H17_LOC_NOT_EVALUATED
        and "TASK_CEILING_FAIL(16384)" in ceiling["annotations"]
    )
    assert C.lane_c_gate({}, FLAT, E)["passed"] is False and C.lane_c_gate({}, FLAT, E)["missing"]


# --- every class on simulated records -----------------------------------------------------------------------------------
def test_locality_positive_and_details() -> None:
    w = eval_world()
    r = classify(w, make_sims(e_const(0.6)))  # E ratio 0.667
    assert (
        r["cls"] == "LOCALITY_POSITIVE"
        and r["lane"] == "C"
        and r["details"]["label"] == "SIMULATED"
    )
    unit = r["details"]["panels"]["A"]["numbers"]["1701"]
    assert len(unit["settings"]) == 8 and unit["settings"]["rho0.0625|R8|asc"][
        "e_ratio"
    ] == pytest.approx(0.6 / 0.9)
    assert (
        unit["settings"]["rho0.25|R32|desc"]["pages_per_query_case"] == 3.0
        and unit["settings"]["rho0.25|R32|desc"]["cross_query_reuse_case"] == 0.4
    )
    assert (
        unit["i_ratio_to_locality_reference"] == pytest.approx(1.0)
        and unit["utilization_class"] == "UTILIZATION_PRESERVED"
    )
    assert unit["cache_pages_x_rows_over_ustar"]["rho0.0625|R8|asc"] == pytest.approx(
        10 * 8 * 8 / 1000
    )  # cache slots over U*
    assert unit["locality_reference"].startswith("A1-flat-R0-n16384")


def test_concentration_only() -> None:
    r = classify(
        eval_world(), make_sims(e_const(0.95), lambda c, *a: 1000 if c.block == "A1" else 700)
    )
    assert r["cls"] == "CONCENTRATION_ONLY"


def test_worse_and_no_difference_and_intermediate() -> None:
    w = eval_world()
    assert classify(w, make_sims(e_const(1.2)))["cls"] == "WORSE"
    assert classify(w, make_sims(e_const(0.9)))["cls"] == "NO DIFFERENCE"
    mixed = make_sims(
        lambda c, rows, rho, tie, panel: 0.9 if c.block == "A1" else (0.5 if rows == 8 else 0.9)
    )
    assert classify(w, mixed)["cls"] == core.INTERMEDIATE


def test_degenerate_when_any_setting_is_degenerate_for_case_or_reference() -> None:
    w = eval_world()
    case_deg = make_sims(
        e_const(0.6),
        degenerate_fn=lambda c, rows, rho, tie, panel: c.block == "C1"
        and rows == 32
        and rho == 0.25
        and tie == "desc"
        and panel == "B"
        and c.seed == 1702,
    )
    r = classify(w, case_deg)
    assert (
        r["panel_classes"] == {"A": "LOCALITY_POSITIVE", "B": core.INTERMEDIATE}
        and r["cls"] == core.NOT_REPLICATED
    )
    assert r["details"]["panels"]["B"]["seed_classes"]["1702"] == "DEGENERATE"
    ref_deg = make_sims(e_const(0.6), degenerate_fn=lambda c, *a: c.block == "A1")
    r2 = classify(w, ref_deg)
    assert r2["cls"] == "DEGENERATE" and r2["panel_classes"] == {
        "A": "DEGENERATE",
        "B": "DEGENERATE",
    }
    undefined = make_sims(lambda c, *a: None if c.block == "C1" else 0.9)
    assert classify(w, undefined)["cls"] == "DEGENERATE"  # an undefined E is degenerate
    zero_ref = make_sims(lambda c, *a: 0.0 if c.block == "A1" else 0.5)
    assert classify(w, zero_ref)["cls"] == "DEGENERATE"  # a zero reference E cannot be divided by


def test_collapsed_quality_failed_before_degenerate() -> None:
    all_degenerate = make_sims(e_const(0.6), degenerate_fn=lambda *a: True)
    w = eval_world(c1_ustar=600)  # C1 cells lose U* against their B1 reference
    r = classify(w, all_degenerate)
    assert r["cls"] == C.QUALITY_FAILED  # COLLAPSED is decided before DEGENERATE (RB3)
    quality = eval_world(
        b1_acc=0.9, c1_acc=0.85
    )  # preserved against B1? no: 0.85/0.9 -> I ratio 0.904 >= 0.9, but < 0.97 against dose-zero
    r2 = classify(quality, make_sims(e_const(0.6)))
    assert r2["cls"] == C.QUALITY_FAILED and r2["details"]["panels"]["A"]["numbers"]["1701"][
        "i_ratio_to_locality_reference"
    ] == pytest.approx(0.904, abs=0.005)


def test_seeds_that_disagree_and_panels_that_disagree() -> None:
    w = eval_world()
    seed_split = make_sims(
        lambda c, rows, rho, tie, panel: 0.9
        if c.block == "A1"
        else (0.6 if c.seed == 1701 else 1.2)
    )
    r = classify(w, seed_split)
    assert r["cls"] == core.INTERMEDIATE and r["details"]["panels"]["A"]["seed_classes"] == {
        "1701": "LOCALITY_POSITIVE",
        "1702": "WORSE",
    }
    panel_split = make_sims(
        lambda c, rows, rho, tie, panel: 0.9 if c.block == "A1" else (0.6 if panel == "A" else 1.2)
    )
    r2 = classify(w, panel_split)
    assert (
        r2["panel_classes"] == {"A": "LOCALITY_POSITIVE", "B": "WORSE"}
        and r2["cls"] == core.NOT_REPLICATED
    )


def test_incomplete_with_one_missing_simulation_record() -> None:
    sims = make_sims(e_const(0.6))
    victim = group()[0]
    sims[victim.label] = [
        r
        for r in sims[victim.label]
        if not (r["rows_per_page"] == 32 and r["tie"] == "desc" and r["stream"] == "panel_b")
    ]
    r = classify(eval_world(), sims)
    assert r["cls"] == A.INCOMPLETE and any("sim:" in m for m in r["details"]["missing"])
    assert C.classify_locality_panel(eval_world().index, sims, victim, "B", E) == A.INCOMPLETE
    assert (
        C.classify_locality_panel(eval_world().index, sims, victim, "A", E) == "LOCALITY_POSITIVE"
    )
    w = eval_world()
    w.drop(group()[1], ("A",))
    assert classify(w, make_sims(e_const(0.6)))["cls"] == A.INCOMPLETE


def test_controls_and_pages_are_reported_beside_the_class_and_enter_none() -> None:
    sims = make_sims(e_const(0.6))
    for label in list(sims):
        extra = [
            sim_rec(
                label,
                r["update"],
                r["stream"],
                r["rows_per_page"],
                r["cache_fraction"],
                r["tie"],
                e=0.1,
                layout="identity",
            )
            for r in sims[label]
        ]
        sims[label] += extra
    r = classify(eval_world(), sims)
    assert r["cls"] == "LOCALITY_POSITIVE"  # E 0.1 under the identity layout changes nothing
    controls = r["details"]["panels"]["A"]["numbers"]["1701"]["controls"]
    assert set(controls) == {"identity"} and controls["identity"]["rho0.25|R8|asc"]["e_case"] == 0.1


# --- helpers -----------------------------------------------------------------------------------------------------------------
def test_e_and_raw_ratio_helpers() -> None:
    sims = make_sims(e_const(0.45), lambda c, *a: 1000 if c.block == "A1" else 500)
    case, ref = (
        sims[group()[0].label],
        sims[
            next(
                c
                for c in core.cells()
                if c.block == "A1"
                and c.slots == 16384
                and c.seed == 1701
                and c.parent == core.PRIMARY_PARENT
            ).label
        ],
    )
    kw = {"rows": 8, "rho": 0.25, "tie": "asc", "stream": "panel_a"}
    assert C.e_ratio_case_vs_reference(case, ref, **kw) == pytest.approx(0.5)  # type: ignore[arg-type]
    assert C.raw_miss_ratio(case, ref, **kw) == pytest.approx(0.5)  # type: ignore[arg-type]
    assert (
        C.e_ratio_case_vs_reference(case, ref, rows=2, rho=0.25, tie="asc", stream="panel_a")
        is None
    )  # not simulated
    assert C.raw_miss_ratio(case, [], **kw) is None  # type: ignore[arg-type]
    assert C.find_sim(case, **kw)["layout"] == "coaccess@8"  # type: ignore[arg-type]


# --- hierarchy -------------------------------------------------------------------------------------------------------------------
def hierarchy_world() -> Synth:
    return eval_world()


def tree_sims(tree_e: float, flat_c1_e: float) -> dict[str, list[dict[str, Any]]]:
    def e(c: core.Cell, rows: int, rho: float, tie: str, panel: str) -> float:
        if c.block == "A1":
            return 0.9
        return tree_e if c.arch == TREE else flat_c1_e

    sims = make_sims(e)
    # the tree's C1 cells exist at 16K too: make_sims covers every C1 cell
    return sims


def test_hierarchy_advantage_needs_the_tree_positive_against_the_flat_case_with_the_same_doses() -> (
    None
):
    w = hierarchy_world()
    res = C.analyze(w.index, tree_sims(0.5, 0.85), E)
    h = {r["subject"]: r for r in res if r["subject"].startswith("hierarchy")}
    assert h["hierarchy/ac0.05"]["cls"] == "HIERARCHY_ADVANTAGE"  # 0.5 / 0.85 = 0.59 <= 0.80
    res2 = C.analyze(
        w.index, tree_sims(0.5, 0.55), E
    )  # tree beats dose-zero flat but not the flat case with the same dose
    tree = next(r for r in res2 if r["subject"] == "C1/learned_tree/au0.25/ac0.05")
    flat = next(r for r in res2 if r["subject"] == "C1/flat/au0.25/ac0.05")
    assert (
        tree["cls"] == "LOCALITY_POSITIVE"
        and tree["details"]["vs_flat_same_dose"]["cls"] != "LOCALITY_POSITIVE"
    )
    assert C.hierarchy_advantage(flat, tree) is False
    assert (
        next(r for r in res2 if r["subject"] == "hierarchy/ac0.05")["cls"]
        == "NO_HIERARCHY_ADVANTAGE"
    )
    # the doses must match
    other = next(r for r in res if r["subject"] == "C1/flat/au0.25/ac0.25")
    assert (
        C.hierarchy_advantage(
            other, next(r for r in res if r["subject"] == "C1/learned_tree/au0.25/ac0.05")
        )
        is False
    )
    assert C.hierarchy_advantage(flat, {"details": {}}) is False  # type: ignore[typeddict-item]


def test_hierarchy_absent_when_the_flat_comparator_is_absent() -> None:
    sims = tree_sims(0.5, 0.85)
    for c in core.cells():
        if c.block == "C1" and c.arch == FLAT:
            sims.pop(c.label, None)
    res = C.analyze(hierarchy_world().index, sims, E)
    assert next(r for r in res if r["subject"] == "C1/flat/au0.25/ac0.05")["cls"] == A.INCOMPLETE
    assert (
        next(r for r in res if r["subject"] == "hierarchy/ac0.05")["cls"]
        == "NO_HIERARCHY_ADVANTAGE"
    )


# --- analyze, D09, key traffic -----------------------------------------------------------------------------------------------------------
def test_analyze_structure_and_gate_entries() -> None:
    res = C.analyze(eval_world().index, make_sims(e_const(0.6)), E)
    subjects = [r["subject"] for r in res]
    assert subjects[:2] == ["lane_c_gate/flat", "lane_c_gate/learned_tree"]
    assert (
        subjects.count("d09_sweep") == 1
        and subjects.count("key_traffic_identity") == 1
        and sum(s.startswith("C1/") for s in subjects) == 4
    )
    assert all(r["lane"] == "C" for r in res)
    empty = C.analyze({}, {}, E)
    assert {r["cls"] for r in empty if r["subject"].startswith("C1/")} == {A.INCOMPLETE}
    assert {r["cls"] for r in empty if r["subject"].startswith("lane_c_gate/")} == {
        C.H17_LOC_NOT_EVALUATED
    }


def test_d09_sweep_labels_primary_and_descriptive_settings() -> None:
    sims = make_sims(e_const(0.6), sweep=True)
    rows = C.d09_sweep(sims)
    assert all(r["kind"] == "SIMULATED" for r in rows)
    status = {(r["cache_fraction"], r["rows_per_page"]): r["status"] for r in rows}
    assert status[(0.0625, 8)] == "primary" and status[(0.25, 32)] == "primary"
    assert (
        status[(1.0, 8)] == "descriptive"
        and status[(0.25, 2)] == "descriptive"
        and status[(1.0, 32)] == "descriptive"
    )
    assert {(r["cache_fraction"], r["rows_per_page"]) for r in rows} == {
        (rho, k) for rho in core.CACHE_RHOS_SWEEP for k in core.CACHE_ROWS_SWEEP
    }
    # all-position traces and non-primary layouts are never primary
    sims_all = make_sims(e_const(0.6))
    first = next(iter(sims_all.values()))
    first.append(
        sim_rec(
            group()[0].label,
            first[0]["update"],
            "panel_a",
            8,
            0.25,
            "asc",
            e=0.5,
            layout="identity",
        )
    )
    assert any(
        r["layout"] == "identity" and r["status"] == "descriptive" for r in C.d09_sweep(sims_all)
    )


def test_key_traffic_identity_is_analytical_not_a_simulation() -> None:
    rows = C.key_traffic_rows()
    assert len(rows) == 6 and all(
        "ANALYTICAL" in str(r["kind"]) and "not a simulation" in str(r["kind"]) for r in rows
    )
    by = {(r["arch"], r["slots"]): r["keys_on_storage_key_products_per_query"] for r in rows}
    assert (
        by[("flat", 65536)] == 65536
        and by[("learned_tree", 65536)] == 256 + 512
        and by[("learned_tree", 4096)] == 16 + 512
    )
    assert all(r["keys_in_ram_key_products_read_from_storage"] == 0 for r in rows)


def test_leakage_annotation_on_a_locality_result() -> None:
    w = eval_world()
    patch(w, group()[0], "A", unseen_correct=500)
    r = classify(w, make_sims(e_const(0.6)))
    assert (
        C.LEAKAGE in r["annotations"]
        and r["cls"] == "LOCALITY_POSITIVE"
        and "interpretation_withheld" in r["details"]
    )


def test_flat_and_tree_cases_share_no_state() -> None:
    w = eval_world()
    sims = make_sims(
        lambda c, rows, rho, tie, panel: 0.9
        if c.block == "A1"
        else (0.6 if c.arch == FLAT else 1.2)
    )
    assert (
        classify(w, sims, FLAT)["cls"] == "LOCALITY_POSITIVE"
        and classify(w, sims, TREE)["cls"] == "WORSE"
    )
