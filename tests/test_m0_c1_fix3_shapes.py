# ruff: noqa: E501
"""C1 fix round 3: one guard per audited defect, written FAILING-FIRST. Each guard is a measurement ``metric(lineage) -> float`` and a bound; the test asserts the NEW lineage meets the bound
and a sibling test asserts that the OLD lineage (kept on file) VIOLATES it, so each guard fails on the old shape and passes on the new one (the second test is the recorded failure against the
old code). Rates are the battery's, from a throwaway-seed draw; the bounds are regression guards for these fixes, not registered thresholds (ruling R-3). Self-checked only."""

from __future__ import annotations

import ast
import inspect
import math
import operator
import re
from collections import Counter
from collections.abc import Callable

import pytest

from studies.m0.c1_fix3_battery import (
    all_lineages,
    int_lists,
    ints_in_order,
    max_sub,
    max_suffix,
    specific,
    top_sets,
)
from studies.m0.c1grammar import render
from studies.m0.core import Retry, build_item, stream
from studies.m0.lineages_c1_fix3 import load_fix3

ALL = all_lineages()
LEVELS = (1, 3, 5)
N = 150


def draw(lid: str, level: int, n: int = N) -> list[tuple[str, str]]:
    r = stream(953961, "c1-fix3-shapes", lid, str(level))
    out = []
    for i in range(n):
        it = build_item(ALL[lid], level, r, "A", f"{lid}/{level}/{i}")
        out.append((render(it.structured["program"]), it.answer))
    return out


def rate(lid: str, pred: Callable[[str, str, ast.Module], bool | None], levels: tuple[int, ...] = LEVELS, n: int = N) -> float:
    """Share of the items to which ``pred`` applies (returns not None) for which it returns True, pooled over ``levels``."""
    hit = tot = 0
    for lv in levels:
        for src, key in draw(lid, lv, n):
            v = pred(src, key, ast.parse(src))
            if v is None:
                continue
            tot += 1
            hit += bool(v)
    return hit / tot if tot else 0.0


def worst_rule(lid: str, levels: tuple[int, ...] = LEVELS, n: int = N) -> float:
    """The battery's worst non-control rule rate inside its shape for a NEW lineage (pooled per level; the maximum over levels, shapes and rules)."""
    worst = 0.0
    for lv in levels:
        per: dict[tuple[str, str], list[int]] = {}
        shapes: Counter[str] = Counter()
        rows = []
        for src, key in draw(lid, lv, n):
            sh, rules = specific(lid, src, ast.parse(src))
            shapes[sh] += 1
            rows.append((sh, rules, key))
        for sh, rules, key in rows:
            for rn, pv in rules.items():
                if rn.startswith("C."):
                    continue
                per.setdefault((sh, rn), [0])[0] += int(pv is not None and pv == key)
        for (sh, _rn), (k,) in per.items():
            if shapes[sh] >= 20:
                worst = max(worst, k / shapes[sh])
    return worst


def most_frequent_key_rate(lid: str, levels: tuple[int, ...] = LEVELS, n: int = N) -> float:
    return max(Counter(k for _, k in draw(lid, lv, n)).most_common(1)[0][1] / n for lv in levels)


def lit_args(tree: ast.Module) -> list[int]:
    return ints_in_order(tree)


# ------------------------------------------------------------------------------------------------ old-shape formulas (the audit's section 3), each returns True/False/None (not applicable)


def f_string_build_len(src: str, key: str, tree: ast.Module) -> bool | None:
    if "print(len(" not in src.strip().splitlines()[-1]:
        return None
    rng = re.search(r"range\((\d+)(?:, (\d+))?\)", src)
    a, b = (0, int(rng.group(1))) if rng.group(2) is None else (int(rng.group(1)), int(rng.group(2)))  # type: ignore[union-attr]
    return key == str(b - a)


def f_while_shrink(src: str, key: str, tree: ast.Module) -> bool | None:
    if "-=" not in src or "!= 1" in src:
        return None
    x0 = ints_in_order(tree)[0]
    thr = int(re.search(r"while \w+ > (\d+):", src).group(1))  # type: ignore[union-attr]
    d = int(re.search(r"-= (\d+)", src).group(1))  # type: ignore[union-attr]
    return key == str(x0 - d * math.ceil((x0 - thr) / d) if x0 > thr else x0)


def f_euclid_gcd(src: str, key: str, tree: ast.Module) -> bool | None:
    ts = top_sets(tree)
    if print_is_name(tree) != ts[0][0]:
        return None
    ints = ints_in_order(tree)
    return key == str(math.gcd(ints[0], ints[1]))


def print_is_name(tree: ast.Module) -> str | None:
    a = tree.body[-1].value.args[0]  # type: ignore[attr-defined]
    return a.id if isinstance(a, ast.Name) else None


def f_fast_power_res(src: str, key: str, tree: ast.Module) -> bool | None:
    ts = top_sets(tree)
    if print_is_name(tree) != ts[0][0]:
        return None
    b, e, m = (ints_in_order(v)[0] for _, v in ts[1:4])
    return key == str(pow(b, e, m))


def f_insertion_list(src: str, key: str, tree: ast.Module) -> bool | None:
    """Every shape of the old insertion_sort (the list afterwards, the element at an index, the number of shifts) from sorted(prefix) and an inversion count."""
    if "while" not in src:
        return None
    vals = int_lists(tree)[0]
    k = int(re.search(r"range\(1, (\d+)\)", src).group(1))  # type: ignore[union-attr]
    op = re.search(r"and \w+\[\w+\] (>=|<=|>|<) \w+:", src).group(1)  # type: ignore[union-attr]
    asc = op in (">", ">=")
    after = sorted(vals[:k], reverse=not asc) + vals[k:]
    last = src.strip().splitlines()[-1]
    name = print_is_name(tree)
    if name == top_sets(tree)[0][0]:
        return key == str(after)
    if name is None:
        return key == str(after[int(re.search(r"\[(\d+)\]\)$", last).group(1))])  # type: ignore[union-attr]
    ops = {">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le}
    return key == str(sum(1 for q in range(k) for p in range(q) if ops[op](vals[p], vals[q])))


def f_minmax_all(src: str, key: str, tree: ast.Module) -> bool | None:
    vals = int_lists(tree)[0]
    op = re.search(r"if \w+\[\w+\] (<|>) \w+:", src).group(1)  # type: ignore[union-attr]
    b = max(vals) if op == ">" else min(vals)
    pos = vals.index(b)
    return key in {str(b), str(pos), str(b + pos)}


def f_kadane_old(src: str, key: str, tree: ast.Module) -> bool | None:
    vals = int_lists(tree)[0]
    return key in {str(max_sub(vals)), str(max_suffix(vals)), str(sum(max_suffix(vals[: i + 1]) for i in range(1, len(vals))))}


def f_partition_swapj(src: str, key: str, tree: ast.Module) -> bool | None:
    if re.search(r"^print\(\w+\)$", src.strip().splitlines()[-1]) and print_is_name(tree) == top_sets(tree)[0][0]:
        return None
    vals = int_lists(tree)[0]
    m1 = int(re.search(r"range\((\d+)\)", src).group(1))  # type: ignore[union-attr]
    op = re.search(r"if \w+\[\w+\] (<=|<) \w+:", src).group(1)  # type: ignore[union-attr]
    return key == str(sum(j for j in range(m1) if (vals[j] <= vals[m1] if op == "<=" else vals[j] < vals[m1])))


def f_digit_peel_b10(src: str, key: str, tree: ast.Module) -> bool | None:
    base = int(re.search(r"% (\d+)\n", src).group(1))  # type: ignore[union-attr]
    if base != 10 or "* 10 +" in src:
        return None
    x = ints_in_order(tree)[0]
    dd = [int(c) for c in str(x)]
    if "% 2 == 0" in src:
        return key == str(sum(d for d in dd if d % 2 == 0))
    if ">=" in src:
        th = int(re.search(r">= (\d+)", src).group(1))  # type: ignore[union-attr]
        return key == str(sum(1 for d in dd if d >= th))
    return key == str(sum(dd))


def f_binary_last_present(src: str, key: str, tree: ast.Module) -> bool | None:
    vals = int_lists(tree)[0]
    t = ints_in_order(tree)[len(vals)]
    if "''" in src or re.search(r"\+= \w+\[\w+\]", src) or "<=" not in re.search(r"while (.*):", src).group(1) or t not in vals:  # type: ignore[union-attr]
        return None
    return key == str(vals.index(t))


def f_counter_hist(src: str, key: str, tree: ast.Module) -> bool | None:
    vals, k = int_lists(tree)[0], len(int_lists(tree)[1])
    c = [0] * k
    for v in vals:
        c[v % k] += 1
    return key == str(c)


def f_cond_chain_gcd(src: str, key: str, tree: ast.Module) -> bool | None:
    ints = ints_in_order(tree)
    g = math.gcd(ints[0], ints[1])
    return key in {str(g), str(2 * g)}


def f_most_frequent(lid: str, level: int) -> float:
    return most_frequent_key_rate(lid, (level,))


def f_string_methods_count_zero(src: str, key: str, tree: ast.Module) -> bool | None:
    if ".count(" not in src:
        return None
    return key == "0"


def f_bytecode_no_skips(src: str, key: str, tree: ast.Module) -> bool | None:
    from studies.m0.c1_fix3_battery import DropIf, mut

    if "% 2 == " not in src:
        return None
    return mut(src, DropIf(r"% 2 == \w+ % 2").visit) == key


def f_bracket_old_zero(src: str, key: str, tree: ast.Module) -> bool | None:
    return key in {"0", "-1"}


def f_majority_even_count(src: str, key: str, tree: ast.Module) -> bool | None:
    if "' '" not in src.strip().splitlines()[-1]:
        return None
    return int(key.split()[1]) % 2 == 0


def f_sieve_indexsum_primes(src: str, key: str, tree: ast.Module) -> bool | None:
    if src.count("for ") < 2:
        return None
    fl = int_lists(tree)[0]

    def isp(k: int) -> bool:
        return k >= 2 and all(k % d for d in range(2, int(k**0.5) + 1))

    return key == str(sum(k for k in range(len(fl)) if fl[k] == 1 and (k < 2 or isp(k))))


# ------------------------------------------------------------------------------------------------ guards: (name, old id, old predicate, old bound, new id, new check)
# direction 'formula': the old shape has a rule that scores >= OLD_MIN of the items it applies to; the new lineage's battery worst rule is <= NEW_MAX.
FORMULA = [
    ("string_build length", "C1.string_build", f_string_build_len, "C1.string_build_f3"),
    ("while_counter shrink", "C1.while_counter", f_while_shrink, "C1.while_counter_f3"),
    ("euclid gcd", "C1.euclid_gcd", f_euclid_gcd, "C1.euclid_gcd_traced_f3"),
    ("fast_power result", "C1.fast_power_r2", f_fast_power_res, "C1.fast_power_f3"),
    ("partition swap positions", "C1.partition_pass", f_partition_swapj, "C1.partition_pass_f3"),
    ("digit_peel base 10", "C1.digit_peel", f_digit_peel_b10, "C1.digit_peel_f3"),
    ("binary_search last probe", "C1.binary_search", f_binary_last_present, "C1.binary_search_f3"),
    ("counter_list histogram", "C1.counter_list", f_counter_hist, "C1.counter_list_f3"),
]


@pytest.mark.parametrize(("name", "old", "pred", "new"), FORMULA, ids=[f[0] for f in FORMULA])
def test_old_shape_is_formula_answerable(name: str, old: str, pred: Callable[..., bool | None], new: str) -> None:
    """The recorded failure against the old code: the closed form answers (nearly) every item of the old shape."""
    assert rate(old, pred) >= 0.95, name


@pytest.mark.parametrize(("name", "old", "pred", "new"), FORMULA, ids=[f[0] for f in FORMULA])
def test_new_lineage_has_no_formula_above_guard(name: str, old: str, pred: Callable[..., bool | None], new: str) -> None:
    assert worst_rule(new) <= 0.25, (name, worst_rule(new))


NOT_REGISTERED_FORMULAS = [("insertion_sort list", "C1.insertion_sort", f_insertion_list), ("minmax_track", "C1.minmax_track", f_minmax_all), ("kadane_scan", "C1.kadane_scan", f_kadane_old)]


@pytest.mark.parametrize(("name", "old", "pred"), NOT_REGISTERED_FORMULAS, ids=[f[0] for f in NOT_REGISTERED_FORMULAS])
def test_not_registered_lineages_are_closed_form(name: str, old: str, pred: Callable[..., bool | None]) -> None:
    """The reason for NOT REGISTERED, measured: a closed form answers every shape of the old lineage."""
    assert rate(old, pred) >= 0.95, name


def test_every_new_lineage_stays_under_the_guard() -> None:
    """No battery rule above 0.25 inside a shape for any new lineage at levels 1, 3 and 5 (the brief: a tell above 0.25 that cannot be removed means NOT REGISTERED)."""
    bad = {x.id: round(worst_rule(x.id), 2) for x in load_fix3() if worst_rule(x.id) > 0.25}
    assert not bad, bad


# ------------------------------------------------------------------------------------------------ shortcut guards with an old and a new side
def test_string_methods_has_no_numeric_answers() -> None:
    assert rate("C1.string_methods", f_string_methods_count_zero) >= 0.7  # the old count shape: '0' in 0.83-0.89 of its items
    assert all(not k.lstrip("-").isdigit() for lv in LEVELS for _, k in draw("C1.string_methods_f3", lv))


def test_cond_chain_gcd_tell_removed() -> None:
    assert rate("C1.cond_chain", f_cond_chain_gcd, levels=(4, 5, 6)) >= 0.25
    assert rate("C1.cond_chain_f3", f_cond_chain_gcd, levels=(4, 5, 6)) <= 0.10


def test_merge_two_sorted_answers_are_not_concentrated() -> None:
    assert most_frequent_key_rate("C1.merge_two_sorted_r2", (3,), 300) >= 0.20
    assert most_frequent_key_rate("C1.merge_two_sorted_f3", (3,), 300) <= 0.10


def test_func_compose_answers_are_not_concentrated() -> None:
    assert most_frequent_key_rate("C1.func_compose", (4,), 300) >= 0.12
    assert most_frequent_key_rate("C1.func_compose_f3", (4,), 300) <= 0.10


def test_bytecode_loop_skips_matter() -> None:
    assert rate("C1.bytecode_loop_r2", f_bytecode_no_skips, levels=(3, 4, 5), n=100) >= 0.25
    assert rate("C1.bytecode_loop_f3", f_bytecode_no_skips, levels=(3, 4, 5), n=100) <= 0.20


def test_sieve_index_sum_tell_removed() -> None:
    assert rate("C1.sieve_marking_r2", f_sieve_indexsum_primes, levels=(1, 2, 3), n=100) >= 0.25
    assert all(f_sieve_indexsum_primes(s, k, ast.parse(s)) is None for lv in (1, 2, 3) for s, k in draw("C1.sieve_marking_f3", lv, 60))  # the shape is gone


def test_majority_count_parity_is_not_constant() -> None:
    assert rate("C1.majority_vote_scan_r2", f_majority_even_count, levels=(2, 3)) == 1.0  # the audit: the printed count was always even
    ans = [k for lv in (2, 3) for _, k in draw("C1.majority_vote_scan_f3", lv)]
    assert not any(" " in a for a in ans)  # the 'candidate count' shape is gone


def test_bracket_matching_answers_are_not_redrawn() -> None:
    """The old builder redrew every answer that was 0 (code shape), -1 or a height of 0: the code shape never prints 0. The new one has no Retry and the natural values occur."""
    old_code = [k for lv in (0, 1, 2, 3) for src, k in draw("C1.bracket_matching", lv, 300) if "* 10" in src.strip().splitlines()[-1]]
    assert len(old_code) > 100 and "0" not in old_code  # the old redraw: 'no error and nothing left open' is never drawn (10 * errors + height = 0)
    new = [k for lv in range(7) for _, k in draw("C1.bracket_matching_f3", lv, 150)]
    assert any(k in {"0", "[]"} for k in new)
    r = stream(953962, "bracket-no-retry")
    for lv in range(7):
        for _ in range(100):
            ALL["C1.bracket_matching_f3"].build(lv, r)  # raises Retry on the first redraw: there is none


def test_partition_never_echoes_the_input_by_construction() -> None:
    lin = ALL["C1.partition_pass_f3"]
    r = stream(953963, "partition-construction")
    for lv in range(7):
        for _ in range(100):
            b = lin.build(lv, r)  # no Retry: nothing is redrawn
            tree = ast.parse(render(b.structured["program"]))
            if re.search(r"^print\(\w+\)$", render(b.structured["program"]).splitlines()[-1]) and print_is_name(tree) == top_sets(tree)[0][0]:
                continue
            vals = int_lists(tree)[0]
            assert b.answer != str(vals)


def test_union_find_has_no_root_query_shape_and_no_retry() -> None:
    lin = ALL["C1.union_find_links_f3"]
    r = stream(953964, "uf-construction")
    for lv in range(7):
        for _ in range(100):
            assert "print(find(" not in render(lin.build(lv, r).structured["program"])


def test_shared_lists_naive_copy_rate_is_not_zero_by_redraw() -> None:
    """The old builder redrew every item whose answer equalled the naive-copy answer (rate exactly 0). The new one does not redraw; the naive rate is what the construction gives."""
    from studies.m0.c1_fix3_battery import mut

    class Copyish(ast.NodeTransformer):
        def visit_Assign(self, n: ast.Assign) -> ast.AST:
            self.generic_visit(n)
            if isinstance(n.value, ast.Name):
                n.value = ast.Subscript(value=n.value, slice=ast.Slice(), ctx=ast.Load())
            return n

    def naive(src: str, key: str, tree: ast.Module) -> bool | None:
        return mut(src, Copyish().visit) == key if "def " not in src else None

    assert rate("C1.shared_lists", naive, levels=(0, 1), n=100) == 0.0  # the redraw's signature
    assert rate("C1.shared_lists_f3", naive, levels=(0, 1, 2), n=150) <= 0.25


def test_retry_sites_are_validity_only() -> None:
    """Only these builders contain ``raise Retry`` and each has a validity reason: euclid (two equal operands; too few rounds for the stated shapes), shared_lists (an assignment of a name to
    itself), cellular_update (a constant row, a constant rule: a degenerate program), string_methods (an empty string), coin_change_table (the 'fewest coins' sentinel 99 would be the answer:
    the old lineage's rule, kept). No other redraw exists, so no redraw is conditioned on a shortcut's outcome; the retry rate stays small."""
    import studies.m0.lineages_c1_fix3_lists as lists_mod
    import studies.m0.lineages_c1_fix3_numbers as numbers_mod
    import studies.m0.lineages_c1_fix3_other as other_mod

    with_retry = set()
    for mod in (numbers_mod, lists_mod, other_mod):
        for nm, fn in inspect.getmembers(mod, inspect.isfunction):
            if nm.endswith("_f3") and "raise Retry" in inspect.getsource(fn):
                with_retry.add(nm)
    assert with_retry == {"euclid_gcd_traced_f3", "shared_lists_f3", "cellular_update_f3", "string_methods_f3", "coin_change_table_f3"}
    for nm in with_retry:
        lin = next(x for x in load_fix3() if x.id == f"C1.{nm}")
        r = stream(953965, "retry-rate", nm)
        retries = built = 0
        while built < 100:
            try:
                lin.build(3, r)
                built += 1
            except Retry:
                retries += 1
        assert retries / built < 12, (nm, retries, built)
