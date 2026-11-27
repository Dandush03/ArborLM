# ruff: noqa: E501
"""R2 rev2, ruling R-4 (wording) and R-5 (capacity). Each test shows the defect on the batch-1 shape and the fix on the rev2 shape. Self-checked only."""

from __future__ import annotations

import json

from studies.m0.lineages_r2_parsing import evaluate
from studies.m0.lineages_r2_rev2 import SUPERSEDES
from tests.test_m0_r2_rev2_helpers import CORE, NEW, OLD, draw


def test_expression_wording_states_the_rule_inside_parentheses_and_one_rank_for_plus_minus() -> None:
    old = draw(OLD["R2.expression_eval"], 3, 40)
    new = draw(NEW["R2.expression_eval"], 3, 40)
    assert not any("inside every pair of parentheses" in it.question or "same group" in it.question for it in old)
    for it in new:
        q = it.question
        if it.structured["convention"] == "ranked":
            assert "together as one group" in q and "inside every pair of parentheses" in q and "8 - 3 + 2" in q
        else:
            assert "inside a pair of parentheses use the same rule as outside" in q and "(2 + 3) * 4 = 20" in q


def test_expression_keys_follow_the_stated_rule_and_the_old_ambiguity_was_material() -> None:
    import random

    from studies.m0.lineages_r2_parsing import _render_ltr, _render_std, _tree, _val

    r = random.Random(9)
    differs_inside = 0
    for _ in range(400):
        t = _tree(r, 6, 9)
        text = _render_ltr(t)
        # key under the stated rule (left to right everywhere) vs the misreading 'ranked rules inside parentheses'
        if evaluate(text, False) != evaluate(text, True):
            differs_inside += 1
        assert evaluate(text, False) == _val(t)
        assert evaluate(_render_std(t, r), True) == _val(t)
    assert differs_inside > 40  # the batch-1 wording left this open on more than a tenth of items


def test_merge_wording_says_any_two_piles_and_adjacent_reading_would_change_the_key() -> None:
    old = draw(OLD["R2.merge_smallest_cost"], 2, 40)
    new = draw(NEW["R2.merge_smallest_cost"], 2, 40)
    assert not any("Any two piles" in it.question for it in old) and all("Any two piles" in it.question for it in new)
    from studies.m0.r2_audit_heuristics_copy import _adjacent_opt

    changed = sum(1 for it in new if str(_adjacent_opt(it.structured["ws"])) != it.answer)
    assert changed / len(new) > 0.5  # an adjacent-only reading would give a different key, so the sentence matters


def test_string_rewrite_nonidentity_never_draws_a_do_nothing_rule_while_the_existing_one_does() -> None:
    old = [it for lv in range(7) for it in draw(CORE["R2.string_rewrite"], lv, 200)]
    assert any(p == t for it in old for p, t in it.structured["rules"])  # the defect, found by the audit
    assert any(p not in it.structured["s"] for it in old for p, _t in it.structured["rules"][:1])
    for lv in range(7):
        for it in draw(NEW["R2.string_rewrite_nonidentity"], lv, 200):
            cur = it.structured["s"]
            for p, t in it.structured["rules"]:
                assert p != t and p in cur  # does something at its step
                cur = cur.replace(p, t)
            assert cur == it.answer and cur != ""


def test_structure_capacity_widened_for_merge_level0_and_to_base_level0() -> None:
    # R-5: names, setting and presentation order do not count; the demand at level 0 (reserve) is 10 x 100 = 1000
    def distinct(lin, key, n):  # type: ignore[no-untyped-def]
        return len({key(it.structured) for it in draw(lin, 0, n, "cap")})

    assert distinct(OLD["R2.merge_smallest_cost"], lambda s: json.dumps(sorted(s["ws"])), 6000) < 1000  # the audit's 488
    assert distinct(NEW["R2.merge_smallest_cost"], lambda s: json.dumps(sorted(s["ws"])), 3000) >= 1000
    assert distinct(CORE["R2.to_base"], lambda s: json.dumps(s, sort_keys=True), 6000) < 1000  # the audit's 755
    assert distinct(NEW["R2.to_base_wide"], lambda s: json.dumps(s, sort_keys=True), 3000) >= 1000


def test_to_base_wide_key_is_the_base_representation() -> None:
    for lv in range(7):
        for it in draw(NEW["R2.to_base_wide"], lv, 50):
            n, b = it.structured["n"], it.structured["base"]
            assert int(it.answer, b) == n


def test_new_shape_ids_are_shapes_of_existing_or_batch1_lineages_and_families_are_renamed_where_they_clash() -> None:
    assert SUPERSEDES["R2.string_rewrite_nonidentity"] == "R2.string_rewrite" and SUPERSEDES["R2.to_base_wide"] == "R2.to_base"
    assert {x.family for x in NEW.values() if x.id in ("R2.gcd_euclid", "R2.modular_power", "R2.prime_factor_query")} == {"numtheory_b1"}
    assert CORE["R2.multiples_between"].family == "numtheory"  # the existing family keeps its name
    assert not set(NEW) & set(CORE)


def test_crt_rev2_key_by_search_and_wider_moduli() -> None:
    for lv in (0, 1, 4):
        for it in draw(NEW["R2.crt_smallest"], lv, 25):
            cons = it.structured["congruences"]
            x = next(x for x in range(1, 10**8) if all(x % m == r for r, m in cons))
            assert it.answer == str(x)
    assert max(c[1] for it in draw(NEW["R2.crt_smallest"], 1, 200) for c in it.structured["congruences"]) > 15  # batch 1 stopped at 14 on level 1
