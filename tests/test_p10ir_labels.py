# ruff: noqa: E501
"""P10IR label tests (ADR-0029 sections 8, 9, 10): the retention rule, the first-match tree table enumerated exhaustively against an independent oracle written from the ADR's table, the index
label, cells, the plateau check, the combination and R-CONFIRM. Pure functions over numbers: no torch beyond reading the floor through the config. Self-check only: not independent review, not
Astra validation, not human approval."""

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10ir import core, labels  # noqa: E402

TH = core.Thresholds.from_config(core.load_config())
F0 = 4.0


def rep(t0: tuple[float, float], t1: tuple[float, float], t3: tuple[float, float], t2: tuple[float, float], cr8: float, *, f0: float = F0, evaluable: bool = True) -> labels.TreeRep:
    i = {"T0": t0, "T1": t1, "T1w": (3.0, 3.0), "T3": t3, "T2": t2, "F0": (f0, f0)}
    return labels.TreeRep(evaluable, {r: {"A": v[0], "B": v[1]} for r, v in i.items()}, cr8)


# --- the retention rule ---------------------------------------------------------------------------------------------------------------
def test_retention_boundaries() -> None:
    assert labels.has_gap(4.0, 3.5, TH) and not labels.has_gap(4.0, 3.51, TH)  # 0.5 bits
    assert labels.retention(3.75, 4.0, TH) == labels.RESTORED  # exactly 0.25 below and above 0.90 * 4.0 = 3.6
    assert labels.retention(3.74, 4.0, TH) == labels.NOT_RESTORED
    assert labels.retention(3.6, 4.0, TH) == labels.NOT_RESTORED  # 0.4 below: the margin binds
    assert labels.retention(1.0, 1.1, TH) == labels.NOT_RESTORED or labels.retention(1.0, 1.1, TH) == labels.RESTORED
    # below about 2.5 bits the ratio binds: i(Y) = 1.0, 0.9 * 1.0 = 0.9
    assert labels.retention(0.9, 1.0, TH) == labels.RESTORED and labels.retention(0.89, 1.0, TH) == labels.NOT_RESTORED
    assert labels.retention(0.3, 0.4, TH) == labels.WEAK  # reference below the floor 0.473
    assert labels.retention(0.473, 0.4731, TH) == labels.RESTORED  # 0.4731 >= floor 0.47307...


def test_closure_is_a_ratio_of_gaps() -> None:
    assert labels.closure(3.0, 2.0, 4.0) == 0.5
    assert labels.closure(2.0, 2.0, 4.0) == 0.0
    with pytest.raises(ValueError):
        labels.closure(3.0, 4.0, 4.0)


# --- the tree table, exhaustively -------------------------------------------------------------------------------------------------------
def oracle_tree(t0: tuple[float, float], t1: tuple[float, float], t3: tuple[float, float], t2: tuple[float, float], cr8: float) -> str:
    """The ADR's table written out directly, with F0 = 4.0 on both panels (a reference above the floor)."""
    gaps = [F0 - t0[p] >= 0.5 - 1e-12 for p in (0, 1)]
    if not any(gaps):
        return "NO GAP"
    if not all(gaps):
        return "MIXED-PANEL"

    def ok(x: tuple[float, float]) -> bool:
        for p in (0, 1):
            restored = F0 - x[p] <= 0.25 + 1e-12 and x[p] >= 0.90 * F0 - 1e-12
            closed = (x[p] - t0[p]) / (F0 - t0[p]) >= 0.5 - 1e-12
            if not (restored or closed):
                return False
        return True

    p, c, j = ok(t1), ok(t3), ok(t2)
    h = all(t2[k] <= t0[k] - 0.25 + 1e-12 for k in (0, 1))
    r = cr8 >= 0.90
    if p and c:
        return "PRIORS AND CANDIDATES, SEPARATELY"
    if p:
        return "PRIORS"
    if c:
        return "CANDIDATES"
    if j:
        return "JOINT"
    if h:
        return "EXACT SEARCH HARMS"
    return "CONTENT" if r else "NOT IDENTIFIED"


def test_every_combination_reaches_exactly_one_label_and_the_oracle_agrees() -> None:
    t0_vals = [2.0, 3.8]
    xs = [1.0, 2.5, 3.0, 3.9]
    seen: set[str] = set()
    count = 0
    for t0 in itertools.product(t0_vals, repeat=2):
        for t1 in itertools.product(xs, repeat=2):
            for t3 in itertools.product(xs, repeat=2):
                for t2 in itertools.product(xs, repeat=2):
                    for cr8 in (0.5, 0.95):
                        got = labels.tree_replicate(rep(t0, t1, t3, t2, cr8), TH)
                        assert got.row in labels.TREE_ROWS
                        assert got.row == oracle_tree(t0, t1, t3, t2, cr8), (t0, t1, t3, t2, cr8)
                        seen.add(got.row)
                        count += 1
    assert count == 4 * 16 * 16 * 16 * 2
    assert seen == set(labels.TREE_ROWS) - {labels.NOT_EVALUABLE}  # every row 2, 2a, 3 to 9 is reached, and reached by a first match


def test_a_gate_failure_or_a_weak_reference_is_row_1() -> None:
    assert labels.tree_replicate(rep((2.0, 2.0), (3.9, 3.9), (3.9, 3.9), (3.9, 3.9), 0.9, evaluable=False), TH).row == labels.NOT_EVALUABLE
    weak = labels.tree_replicate(rep((0.1, 0.1), (0.2, 0.2), (0.2, 0.2), (0.2, 0.2), 0.9, f0=0.4), TH)
    assert weak.row == labels.NOT_EVALUABLE and weak.reason == labels.WEAK
    one_weak = labels.TreeRep(True, {r: {"A": 4.0, "B": 0.4 if r == "F0" else 4.0} for r in labels.TREE_READS}, 0.9)
    assert labels.tree_replicate(one_weak, TH).row == labels.NOT_EVALUABLE  # a weak reference on one panel only


def test_j_and_h_never_both_hold_where_a_gap_exists() -> None:
    xs = [0.2, 1.0, 1.8, 2.0, 2.5, 3.0, 3.9]
    for t0 in itertools.product([1.0, 2.0, 3.0], repeat=2):
        if not all(F0 - v >= 0.5 for v in t0):
            continue
        for t2 in itertools.product(xs, repeat=2):
            j = all((F0 - t2[p] <= 0.25 and t2[p] >= 0.9 * F0) or (t2[p] - t0[p]) / (F0 - t0[p]) >= 0.5 for p in (0, 1))
            h = all(t2[p] <= t0[p] - 0.25 for p in (0, 1))
            assert not (j and h)


def test_fully_and_partly_suffixes_and_the_mainly_tag() -> None:
    full = labels.tree_replicate(rep((2.0, 2.0), (3.9, 3.9), (2.1, 2.1), (3.9, 3.9), 0.5), TH)
    assert (full.row, full.suffix) == (labels.PRIORS, labels.FULLY)
    part = labels.tree_replicate(rep((2.0, 2.0), (3.0, 3.0), (2.1, 2.1), (3.9, 3.9), 0.5), TH)
    assert (part.row, part.suffix) == (labels.PRIORS, labels.PARTLY)
    assert part.tags["mainly"] in ("weights", "selection", "equal")
    # T1w = 3.0 = T1: the whole effect is already in the weights, none in the selection
    assert part.tags["mainly"] == "weights"
    both = labels.tree_replicate(rep((2.0, 2.0), (3.9, 3.9), (3.0, 3.0), (3.9, 3.9), 0.5), TH)
    assert (both.row, both.suffix) == (labels.PRIORS_AND_CANDIDATES, labels.PARTLY)
    assert labels.tree_replicate(rep((2.0, 2.0), (2.1, 2.1), (2.1, 2.1), (3.9, 3.9), 0.5), TH).suffix == labels.FULLY


def test_a_closure_on_one_panel_only_is_not_p_c_or_j() -> None:
    """Section 16 item 10, ruled as recommended: P needs both panels, so a replicate that closes on one panel only can reach CONTENT (here R holds)."""
    got = labels.tree_replicate(rep((2.0, 2.0), (3.9, 2.1), (2.1, 2.1), (2.1, 2.1), 0.95), TH)
    assert got.row == labels.CONTENT and got.tags["P"] is False


def test_the_tree_actions_are_only_the_four_of_the_adr() -> None:
    assert set(labels.TREE_ACTIONS) == {labels.PRIORS_AND_CANDIDATES, labels.PRIORS, labels.CANDIDATES, labels.CONTENT}
    assert set(labels.INDEX_ACTIONS) == {labels.SPARSE_APPROACHES}


# --- the index label -----------------------------------------------------------------------------------------------------------------
def irep(per_budget: dict[int, float], f0: float = F0, evaluable: bool = True) -> labels.IndexRep:
    return labels.IndexRep(evaluable, {"A": f0, "B": f0}, {c: {"A": v, "B": v} for c, v in per_budget.items()})


def test_index_rows_and_c_star() -> None:
    budgets = [128, 256, 512, 1024, 2048]
    good, bad = 3.9, 2.0
    assert labels.index_replicate(irep({c: good for c in budgets}), TH).tags["c_star"] == 128
    r = labels.index_replicate(irep({128: bad, 256: good, 512: good, 1024: good, 2048: good}), TH)
    assert (r.row, r.tags["c_star"]) == (labels.SPARSE_APPROACHES, 256)
    r = labels.index_replicate(irep({128: bad, 256: bad, 512: good, 1024: good, 2048: good}), TH)
    assert (r.row, r.tags["c_star"]) == (labels.SPARSE_APPROACHES, 512)  # 512 is the tree's candidate count: at most 512
    r = labels.index_replicate(irep({128: bad, 256: bad, 512: bad, 1024: good, 2048: good}), TH)
    assert (r.row, r.tags["c_star"]) == (labels.ONLY_ABOVE_512, 1024)
    r = labels.index_replicate(irep({c: bad for c in budgets}), TH)
    assert r.row == labels.NOT_APPROACH and r.tags["c_star"] is None
    # sufficient means restored at c AND at every larger feasible budget: 256 restored but 512 not: c* is 1024
    r = labels.index_replicate(irep({128: bad, 256: good, 512: bad, 1024: good, 2048: good}), TH)
    assert (r.row, r.tags["c_star"]) == (labels.ONLY_ABOVE_512, 1024)
    # the largest budget decides alone when nothing above it exists (1,024 slots: 128, 256, 512)
    r = labels.index_replicate(irep({128: good, 256: good, 512: bad}), TH)
    assert r.row == labels.NOT_APPROACH
    assert labels.index_replicate(irep({128: good}, evaluable=False), TH).row == labels.NOT_EVALUABLE
    assert labels.index_replicate(irep({128: 0.1}, f0=0.4), TH).row == labels.NOT_EVALUABLE  # WEAK REFERENCE


def test_every_index_row_is_reachable_and_unique() -> None:
    budgets = [128, 256, 512, 1024, 2048]
    rows = set()
    for flags in itertools.product((False, True), repeat=len(budgets)):
        r = labels.index_replicate(irep({c: 3.9 if ok else 2.0 for c, ok in zip(budgets, flags, strict=True)}), TH)
        assert r.row in labels.INDEX_ROWS
        rows.add(r.row)
    assert rows == {labels.SPARSE_APPROACHES, labels.ONLY_ABOVE_512, labels.NOT_APPROACH}


# --- cells -----------------------------------------------------------------------------------------------------------------------------
def test_cell_label_rules() -> None:
    P, C = labels.PRIORS, labels.CONTENT
    assert labels.cell_label([P] * 5, TH) == P
    assert labels.cell_label([P, P, P, P, C], TH) == P  # 4 of 5
    assert labels.cell_label([P, P, P, C, C], TH) == labels.MIXED
    assert labels.cell_label([P, P, P, P, labels.NOT_EVALUABLE], TH) == P  # one NOT EVALUABLE replicate: the denominator stays 5, so 4 of 5 still holds
    assert labels.cell_label([P, P, P, labels.NOT_EVALUABLE, labels.NOT_EVALUABLE], TH) == labels.NOT_EVALUABLE  # 2 of 5, before the 4-of-5 rule
    assert labels.cell_label([P, P, P, labels.NOT_EVALUABLE, C], TH) == labels.MIXED  # 3 of 5 only
    assert labels.cell_label([labels.NO_GAP] * 5, TH) == labels.NO_GAP
    # ruling 2: a MIXED-PANEL replicate satisfies no condition, so a cell with four of them is MIXED, and so is one with five; no cell is ever labelled MIXED-PANEL
    assert labels.cell_label([labels.MIXED_PANEL] * 4 + [P], TH) == labels.MIXED
    assert labels.cell_label([labels.MIXED_PANEL] * 5, TH) == labels.MIXED
    assert labels.cell_label([P, P, P, P, labels.MIXED_PANEL], TH) == P
    with pytest.raises(ValueError):
        labels.cell_label([P] * 4, TH)


def test_median_c_star() -> None:
    assert labels.median_c_star([256, 256, 512, None, 1024]) == 384.0
    assert labels.median_c_star([None, None]) is None


# --- the plateau check ---------------------------------------------------------------------------------------------------------------------
def series(top: float, half: float = 3.0, floor_run: int = 100) -> dict[str, dict[int, float]]:
    return {p: {floor_run // 4: min(2.0, half), floor_run // 2: half, floor_run: top} for p in labels.PANELS}


def test_plateau_check_and_tags() -> None:
    assert labels.plateau_ok(series(3.1), 100, TH)
    assert not labels.plateau_ok(series(3.2), 100, TH)  # gain 0.2 > 0.10
    assert not labels.plateau_ok(series(0.4, half=0.3), 100, TH)  # below the floor
    assert labels.i_star({10: 1.0, 50: 3.0, 100: 2.0}, 60) == 3.0
    ok, bad = series(3.1), series(4.0)
    assert not labels.still_learning([ok, ok, ok, ok, bad], 100, TH)  # one failing replicate
    assert labels.still_learning([ok, ok, ok, bad, bad], 100, TH)  # two
    assert labels.still_learning([ok, ok, ok, None, bad], 100, TH)  # a missing replicate fails
    one_panel = {"A": series(3.1)["A"], "B": series(4.0)["B"]}
    assert not labels.plateau_ok(one_panel, 100, TH)  # both panels


# --- the combination -------------------------------------------------------------------------------------------------------------------------
PRIMARY = ["8K/4K", "32K/16K"]


def lab(tree: dict[tuple[str, str], str], index: dict[tuple[str, str], str]) -> dict[str, dict[str, dict[str, str]]]:
    return {"tree": {c: {cp: tree[(c, cp)] for cp in labels.CHECKPOINTS} for c in PRIMARY}, "index": {c: {cp: index[(c, cp)] for cp in labels.CHECKPOINTS} for c in PRIMARY}}


KEYS = [(c, cp) for c in PRIMARY for cp in labels.CHECKPOINTS]


def uniform(v: str) -> dict[tuple[str, str], str]:
    return dict.fromkeys(KEYS, v)


def oracle_component(vals: dict[tuple[str, str], str]) -> str:
    per_cp = {}
    for cp in labels.CHECKPOINTS:
        rows = {vals[(c, cp)] for c in PRIMARY}
        per_cp[cp] = next(iter(rows)) if len(rows) == 1 else ("CD", tuple(sorted((c, vals[(c, cp)]) for c in PRIMARY)))
    if per_cp["U_P"] == per_cp["RUN"]:
        v = per_cp["U_P"]
        return "CELL-DEPENDENT" if isinstance(v, tuple) else v
    return "CHECKPOINT-DEPENDENT"


def test_combination_exhaustive_per_component() -> None:
    values = [labels.PRIORS, labels.CONTENT, labels.MIXED, labels.NO_GAP, labels.NOT_EVALUABLE]
    for combo in itertools.product(values, repeat=4):
        v = dict(zip(KEYS, combo, strict=True))
        d = labels.combine(lab(v, uniform(labels.NOT_APPROACH)), PRIMARY)
        if labels.NOT_EVALUABLE in combo:
            assert not d.evaluable and d.pair is None and d.recommended == {"tree": None, "index": None}
            assert {x[0] for x in d.not_evaluable} == {"tree"}
            continue
        assert d.evaluable and d.components["tree"].value == oracle_component(v)
    iv = [labels.SPARSE_APPROACHES, labels.NOT_APPROACH, labels.ONLY_ABOVE_512, labels.NOT_EVALUABLE]
    for combo in itertools.product(iv, repeat=4):
        v = dict(zip(KEYS, combo, strict=True))
        d = labels.combine(lab(uniform(labels.CONTENT), v), PRIMARY)
        assert d.evaluable == (labels.NOT_EVALUABLE not in combo)
        assert d.components["index"].value == oracle_component(v)


def test_combination_values_and_actions() -> None:
    d = labels.combine(lab(uniform(labels.PRIORS), uniform(labels.SPARSE_APPROACHES)), PRIMARY)
    assert d.pair == (labels.PRIORS, labels.SPARSE_APPROACHES)
    assert d.recommended == {"tree": "Redesign how routing scores enter the read", "index": "Investigate a separately trained sparse index"}
    # a stable tree component is not lost because the index component moves (the rule is per component)
    idx = uniform(labels.NOT_APPROACH) | {("8K/4K", "RUN"): labels.SPARSE_APPROACHES, ("32K/16K", "RUN"): labels.SPARSE_APPROACHES}
    d = labels.combine(lab(uniform(labels.CANDIDATES), idx), PRIMARY)
    assert d.components["tree"].value == labels.CANDIDATES and d.components["index"].value == labels.CHECKPOINT_DEPENDENT
    assert d.recommended == {"tree": "Improve the router and candidate coverage", "index": None}
    for no_action in (labels.JOINT, labels.EXACT_SEARCH_HARMS, labels.NOT_IDENTIFIED, labels.NO_GAP, labels.MIXED):
        assert labels.combine(lab(uniform(no_action), uniform(labels.NOT_APPROACH)), PRIMARY).recommended["tree"] is None
    assert labels.combine(lab(uniform(labels.CONTENT), uniform(labels.NOT_APPROACH)), PRIMARY).recommended["tree"] == "Improve memory training and representation"  # CONTENT keeps its one action


def test_no_read_time_cause_identified_recommends_nothing() -> None:
    for tree in (labels.EXACT_SEARCH_HARMS, labels.NOT_IDENTIFIED):
        d = labels.combine(lab(uniform(tree), uniform(labels.NOT_APPROACH)), PRIMARY)
        assert d.no_read_time_cause and d.recommended == {"tree": None, "index": None}
    for tree, index in ((labels.CONTENT, labels.NOT_APPROACH), (labels.NOT_IDENTIFIED, labels.ONLY_ABOVE_512), (labels.JOINT, labels.NOT_APPROACH)):
        assert not labels.combine(lab(uniform(tree), uniform(index)), PRIMARY).no_read_time_cause


def test_cell_dependent_checkpoint_dependent_and_signatures() -> None:
    v = uniform(labels.PRIORS) | {("32K/16K", "U_P"): labels.CONTENT, ("32K/16K", "RUN"): labels.CONTENT}
    d = labels.combine(lab(v, uniform(labels.NOT_APPROACH)), PRIMARY)
    assert d.components["tree"].value == labels.CELL_DEPENDENT and d.components["tree"].at["U_P"]["cells"] == {"8K/4K": labels.PRIORS, "32K/16K": labels.CONTENT}
    w = uniform(labels.PRIORS) | {("8K/4K", "RUN"): labels.CONTENT, ("32K/16K", "RUN"): labels.CONTENT}
    d = labels.combine(lab(w, uniform(labels.NOT_APPROACH)), PRIMARY)
    assert d.components["tree"].value == labels.CHECKPOINT_DEPENDENT and d.recommended["tree"] is None
    # CELL-DEPENDENT at both checkpoints with different rows per cell is CHECKPOINT-DEPENDENT (the signatures differ)
    x = {("8K/4K", "U_P"): labels.PRIORS, ("32K/16K", "U_P"): labels.CONTENT, ("8K/4K", "RUN"): labels.CONTENT, ("32K/16K", "RUN"): labels.PRIORS}
    assert labels.combine(lab(x, uniform(labels.NOT_APPROACH)), PRIMARY).components["tree"].value == labels.CHECKPOINT_DEPENDENT


# --- R-CONFIRM -------------------------------------------------------------------------------------------------------------------------------
def diag(tree: str, index: str, *, ne: bool = False, ckpt: bool = False) -> labels.Diagnosis:
    t = uniform(tree)
    if ckpt:
        t = t | {("8K/4K", "RUN"): labels.CONTENT, ("32K/16K", "RUN"): labels.CONTENT}
    if ne:
        t = t | {("8K/4K", "U_P"): labels.NOT_EVALUABLE}
    return labels.combine(lab(t, uniform(index)), PRIMARY)


def test_every_value_of_r_confirm() -> None:
    a1 = diag(labels.PRIORS, labels.NOT_APPROACH)
    assert labels.r_confirm(a1, diag(labels.PRIORS, labels.NOT_APPROACH))["R-CONFIRM-TREE"]["value"] == labels.CONFIRMED
    mixed = labels.r_confirm(a1, diag(labels.PRIORS, labels.SPARSE_APPROACHES))
    assert mixed["R-CONFIRM-TREE"]["value"] == labels.CONFIRMED and mixed["R-CONFIRM-INDEX"]["value"] == labels.NOT_CONFIRMED  # per component: neither line substitutes for the other
    assert mixed["R-CONFIRM-INDEX"]["a1"] == labels.NOT_APPROACH and mixed["R-CONFIRM-INDEX"]["a2"] == labels.SPARSE_APPROACHES  # both printed
    assert labels.r_confirm(a1, diag(labels.CONTENT, labels.NOT_APPROACH))["R-CONFIRM-TREE"]["value"] == labels.NOT_CONFIRMED
    assert labels.r_confirm(diag(labels.PRIORS, labels.NOT_APPROACH, ne=True), diag(labels.PRIORS, labels.NOT_APPROACH))["R-CONFIRM-TREE"]["value"] == labels.NOT_APPLICABLE
    got = labels.r_confirm(a1, diag(labels.PRIORS, labels.NOT_APPROACH, ne=True))
    assert got["R-CONFIRM-TREE"]["value"] == labels.NOT_EVALUABLE and got["R-CONFIRM-INDEX"]["value"] == labels.NOT_EVALUABLE
    assert labels.r_confirm(a1, None)["R-CONFIRM-TREE"]["value"] == labels.NOT_RUN
    assert labels.r_confirm(a1, diag(labels.PRIORS, labels.NOT_APPROACH), a2_complete=False)["R-CONFIRM-INDEX"]["value"] == labels.NOT_RUN
    # two CHECKPOINT-DEPENDENT components are equal only if their values at U_P and at the run length are equal
    c1 = diag(labels.PRIORS, labels.NOT_APPROACH, ckpt=True)
    assert labels.r_confirm(c1, diag(labels.PRIORS, labels.NOT_APPROACH, ckpt=True))["R-CONFIRM-TREE"]["value"] == labels.CONFIRMED
    other = lab(uniform(labels.CANDIDATES) | {("8K/4K", "RUN"): labels.CONTENT, ("32K/16K", "RUN"): labels.CONTENT}, uniform(labels.NOT_APPROACH))
    assert labels.r_confirm(c1, labels.combine(other, PRIMARY))["R-CONFIRM-TREE"]["value"] == labels.NOT_CONFIRMED
    assert labels.may_say_cause(labels.r_confirm(a1, diag(labels.PRIORS, labels.NOT_APPROACH)))
    assert not labels.may_say_cause(labels.r_confirm(a1, None))


def test_accuracy_version_of_the_retention_ratio_is_printed_only() -> None:
    assert labels.accuracy_retained(0.92, 0.948, 0.03) == pytest.approx((0.92 - 0.03) / (0.948 - 0.03))
