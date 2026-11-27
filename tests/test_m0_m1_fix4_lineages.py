# ruff: noqa: E501
"""M1 fix round 4: the repaired builders (R-25 (b) and (c)), the level checks and the hygiene edit. Self-check only: not independent review, not Astra, not human approval; nothing here is a registration."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from studies.m0 import core
from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_fix3 import load_all as load_fix3
from studies.m0.lineages_m1_fix4 import (
    FIX4,
    GCD_LCM_TABLE,
    NOT_REGISTERED_FIX4,
    REPLACES,
    ZERO_SENTENCE,
    fd_ceilings,
    gcd_lcm_ceiling,
    level_parameter_values,
    load_all,
    load_registered,
    not_registered,
    stem,
    zero_rule_stated,
)
from studies.m0.m1_fix4_checks import (
    identical_level_pairs,
    key_problems,
    rising_parameter_problems,
    slot_zero_problems,
)
from studies.m0.m1_fix4_verify import verify

ROOT = Path(__file__).resolve().parents[1]
M0 = ROOT / "studies" / "m0"
NEW = {x.id: x for x in load_all()}
OLD = {x.id: x for x in load_fix3()}
REPAIRED = sorted(x.id for x in FIX4)
STEMS = ["average_missing", "clock_duration", "finite_differences", "gcd_lcm", "mixture", "slot_permutations"]


def test_the_six_repairs_replace_exactly_their_r3_predecessors_and_nothing_else_changes() -> None:
    assert REPAIRED == [f"M1.{s}_r4" for s in STEMS]
    assert {v for v in REPLACES.values()} == {f"M1.{s}_r3" for s in STEMS}
    assert len(NEW) == len(OLD) == 36
    assert set(OLD) - set(NEW) == {f"M1.{s}_r3" for s in STEMS}
    assert set(NEW) - set(OLD) == set(REPAIRED)
    for lid in sorted(set(OLD) & set(NEW)):
        assert NEW[lid] is OLD[lid]  # the very same Lineage objects: no other lineage was touched


def test_nothing_enters_core_registry_and_ids_are_new() -> None:
    reg = {x.id for ev in core.REGISTRY.values() for x in ev}
    assert not reg & set(NEW)
    assert all(not lid.endswith("_r3") or lid in OLD for lid in NEW)


def test_min_cost_packs_is_nowhere() -> None:
    assert not any("min_cost_packs" in lid for lid in NEW) and not any("min_cost_packs" in lid for lid in not_registered())


@pytest.mark.parametrize("lid", REPAIRED)
def test_same_structured_fields_as_the_r3_predecessor_so_every_rule_and_key_reads_it_unchanged(lid: str) -> None:
    old = OLD[REPLACES[lid]]
    for lv in ALL_LEVELS:
        a = build_item(NEW[lid], lv, stream(441001, "fields", lid, str(lv)), "A", "t")
        b = build_item(old, lv, stream(441001, "fields", lid, str(lv)), "A", "t")
        assert sorted(a.structured) == sorted(b.structured), (lid, lv)
        assert a.answer_type == b.answer_type == "number" and a.k is None


@pytest.mark.parametrize("lid", REPAIRED)
def test_no_retry_and_deterministic(lid: str) -> None:
    for lv in ALL_LEVELS:
        a = [NEW[lid].build(lv, stream(441002, "det", lid, str(lv))) for _ in range(1)]
        b = [NEW[lid].build(lv, stream(441002, "det", lid, str(lv))) for _ in range(1)]
        assert a == b
        r = stream(441003, "noretry", lid, str(lv))
        for _ in range(60):
            NEW[lid].build(lv, r)  # core.Retry would propagate and fail the test


# ---------------------------------------------------------------- (c) levels


@pytest.mark.parametrize("lid", REPAIRED)
def test_every_level_pair_gives_different_items(lid: str) -> None:
    assert identical_level_pairs(NEW[lid], n=120) == []


@pytest.mark.parametrize("stem_", ["mixture", "gcd_lcm", "finite_differences", "slot_permutations", "average_missing", "clock_duration"])
def test_the_check_fails_on_the_r3_shape_that_collapsed_its_levels(stem_: str) -> None:
    """Failing-first evidence: the same check applied to the r3 builder reports the identical levels audit 4 found."""
    pairs = identical_level_pairs(OLD[f"M1.{stem_}_r3"], n=120)
    assert pairs, stem_
    expected = {"mixture": {"0=1", "1=2", "3=4", "4=5", "5=6"}, "gcd_lcm": {"0=1", "1=2", "3=4", "5=6"}, "finite_differences": {"0=1", "1=2", "3=4", "5=6"},
                "slot_permutations": {"0=1", "2=3", "3=4", "5=6"}, "average_missing": {"0=1", "2=3", "4=5"}, "clock_duration": {"0=1", "2=3", "4=5"}}[stem_]
    assert expected <= set(pairs)


@pytest.mark.parametrize("stem_", STEMS)
def test_the_stated_parameter_is_strictly_rising_and_documented(stem_: str) -> None:
    assert rising_parameter_problems(stem_) == []
    v = level_parameter_values(stem_)
    assert len(v) == 7 and all(v[i] < v[i + 1] for i in range(6))
    from studies.m0.lineages_m1_fix4 import LEVEL_PARAMETER

    assert LEVEL_PARAMETER[stem_]


def test_rising_check_catches_a_flat_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    import studies.m0.m1_fix4_checks as chk

    monkeypatch.setattr(chk, "level_parameter_values", lambda st: [1, 2, 2, 3, 4, 5, 6])
    assert chk.rising_parameter_problems("x") == ["level 1 -> 2: 2 -> 2 is not rising"]


def test_level_parameter_values_are_the_values_the_builders_use() -> None:
    assert level_parameter_values("mixture") == [30, 36, 42, 48, 54, 60, 66]
    assert [gcd_lcm_ceiling(x) for x in ALL_LEVELS] == level_parameter_values("gcd_lcm")
    assert GCD_LCM_TABLE[0] == (2, 50, 40) and GCD_LCM_TABLE[3] == (3, 30, 24) and GCD_LCM_TABLE[5] == (4, 24, 24)  # level 0, 3, 5: the r3 values of their k
    assert fd_ceilings(0) == (60, 25, 15) and fd_ceilings(5) == (60, 20, 9, 4)  # level 0 and 5: the r3 coefficient ranges
    # every item respects the ceilings it states (mixture prices, average_missing marks, clock legs, gcd/lcm answer, finite-difference answer)
    for lv in ALL_LEVELS:
        r = stream(441004, "ceil", str(lv))
        for _ in range(80):
            m = build_item(NEW["M1.mixture_r4"], lv, r, "A", "t").structured
            assert max(m["a"], m["b"]) <= 30 + 6 * lv
            av = build_item(NEW["M1.average_missing_r4"], lv, r, "A", "t")
            assert max(av.structured["scores"]) <= 100 + 10 * lv and int(av.answer) <= 100 + 10 * lv
            g = build_item(NEW["M1.gcd_lcm_r4"], lv, r, "A", "t")
            assert int(g.answer) <= gcd_lcm_ceiling(lv)
            fd = build_item(NEW["M1.finite_differences_r4"], lv, r, "A", "t")
            assert int(fd.answer) <= level_parameter_values("finite_differences")[lv]
            cl = build_item(NEW["M1.clock_duration_r4"], lv, r, "A", "t").structured["legs"]
            assert all(b - a <= 110 + 6 * lv for a, b in cl) and len(cl) == 2 + lv // 2


def test_level_zero_keeps_the_r3_ranges_where_the_capacity_widening_was_needed() -> None:
    """Level 0 of mixture and finite_differences and gcd_lcm draws from the same ranges as r3 (the widening that capacity needed is kept at the bottom)."""
    for st_ in ("mixture", "finite_differences", "gcd_lcm"):
        a = [build_item(NEW[f"M1.{st_}_r4"], 0, stream(441005, "l0", st_), "A", "t").question for _ in range(1)]
        b = [build_item(OLD[f"M1.{st_}_r3"], 0, stream(441005, "l0", st_), "A", "t").question for _ in range(1)]
        assert a == b, st_


# ---------------------------------------------------------------- (b) wording


def test_zero_rule_is_stated_exactly_where_it_matters_and_the_key_counts_codes_starting_with_zero() -> None:
    assert slot_zero_problems(NEW["M1.slot_permutations_r4"]) == []


def test_the_zero_wording_check_fails_on_the_r3_wording() -> None:
    """Failing-first: r3 printed the leading-zero sentence only for the rule 'any'; the same check reports it missing for 'even' and 'less than 5' items."""
    problems = slot_zero_problems(OLD["M1.slot_permutations_r3"])
    assert any("missing" in p for p in problems)


def test_zero_rule_stated_truth_table() -> None:
    assert zero_rule_stated([0, 1, 2, 3], "any") and zero_rule_stated([0, 1, 2, 3], "even") and zero_rule_stated([0, 1, 2, 3], "lt5") and zero_rule_stated([0, 5, 6, 7], "odd")
    assert not zero_rule_stated([0, 1, 2, 3], "not0") and not zero_rule_stated([1, 2, 3, 4], "even") and not zero_rule_stated([1, 2, 3, 4], "any")


def test_a_leading_zero_changes_the_key_so_the_sentence_matters() -> None:
    """The audit's example: digits 0 1 3 5 7, first digit even, last odd (repeat allowed, 4 digits). Codes starting with 0 are counted; under the other reading the first digit has no allowed value (key 0)."""
    s = {"digits": [0, 1, 3, 5, 7], "length": 4, "repeat": True, "first": "even", "last": "odd"}
    assert verify("slot_permutations", s) == "100"  # first digit 0 only (1) x 5 x 5 x 4 odd last digits = 100
    assert zero_rule_stated(s["digits"], s["first"])
    assert ZERO_SENTENCE.startswith("A code may start with the digit 0")


# ---------------------------------------------------------------- keys


@pytest.mark.parametrize("lid", REPAIRED)
def test_answer_keys_agree_with_the_second_derivation(lid: str) -> None:
    assert key_problems(NEW[lid], n=40) == []


def test_the_second_derivation_checks_slot_codes_that_are_too_large_to_enumerate() -> None:
    s = {"digits": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "length": 9, "repeat": False, "first": "even", "last": "odd"}
    # 5 even first digits x 5 odd last digits, minus none shared (even vs odd), middle: 8 * 7 * 6 * 5 * 4 * 3 * 2 = 8!/1! = 40320 for 7 positions
    assert verify("slot_permutations", s) == str(5 * 5 * 40320)
    s2 = {"digits": [0, 1, 2, 3, 4], "length": 9, "repeat": True, "first": "any", "last": "even"}
    assert verify("slot_permutations", s2) == str(5 * 3 * 5**7)


def test_second_derivation_of_average_missing_reaches_the_new_ceiling() -> None:
    s = {"scores": [150, 140, 160], "mean_cents": 15250, "n": 4}
    assert verify("average_missing", s) == "160"


# ---------------------------------------------------------------- registry of drops and hygiene


def test_round_4_drops_are_removed_from_the_loaders_and_the_round_3_drops_stay_removed() -> None:
    nr = not_registered()
    assert set(NOT_REGISTERED_FIX4) == {"M1.coins_r3", "M1.pigeonhole_worst_case_r3", "M1.mode_tally_r3", "M1.slot_permutations_r4"}
    assert {"M1.pythagoras_r3", "M1.binomial_choose_r3", "M1.digit_puzzle_r3"} <= set(nr)
    reg = {x.id for x in load_registered()}
    assert not reg & set(nr) and len(reg) == 36 - len(nr) == 29


def test_stem_strips_every_revision_suffix() -> None:
    assert stem("M1.mixture_r4") == stem("M1.mixture_r3") == "mixture" and stem("M1.tiered_pricing") == "tiered_pricing"


def test_the_hygiene_edit_is_the_smallest_edit_and_the_package_has_no_set_iteration() -> None:
    src = (M0 / "lineages_m1_fix3_c.py").read_text()
    assert "for d in sorted(set(ds)) if ds.count(d) == 1]" in src and "for d in set(ds)" not in src
    bad: list[str] = []
    for f in sorted(M0.glob("*.py")):
        if not (f.name.startswith("m1_fix4_") or f.name.startswith("lineages_m1_fix4") or f.name == "lineages_m1_fix3_c.py"):
            continue
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash":
                bad.append(f"{f.name}:{node.lineno} hash()")
            its = []
            if isinstance(node, ast.For):
                its.append(node.iter)
            if isinstance(node, ast.comprehension):
                its.append(node.iter)
            for it in its:
                if isinstance(it, ast.Set | ast.SetComp) or (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id in ("set", "frozenset")):
                    bad.append(f"{f.name}:{it.lineno} iterates a set")
    assert bad == []


def test_new_modules_import_only_the_standard_library_torch_and_studies() -> None:
    stdlib = set(sys.stdlib_module_names)
    bad: list[str] = []
    for f in sorted(M0.glob("*.py")):
        if not (f.name.startswith("m1_fix4_") or f.name.startswith("lineages_m1_fix4")):
            continue
        for node in ast.walk(ast.parse(f.read_text())):
            mods = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else []
            bad += [f"{f.name}: {m}" for m in mods if m not in stdlib and m not in ("torch", "studies")]
    assert bad == []
