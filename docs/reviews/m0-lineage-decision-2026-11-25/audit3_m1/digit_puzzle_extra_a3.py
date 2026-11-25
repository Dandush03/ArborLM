# ruff: noqa
"""Audit 3 of M1: digit_puzzle_r2 extras. (1) The 'one of its digits is d' clue under the reading 'exactly one digit is d': how many keys change, how many
items lose a unique answer. (2) Cheap rules: the smallest / largest number meeting only the first printed clue; meeting the first two clues; the share of items in
which some clue is redundant. Seed 9 (audit throwaway), N per level."""
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a3 import ALL_LEVELS, current_set, items
import solve_text_a3 as st
import re

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
lin = current_set()["M1.digit_puzzle_r2"]
for lv in ALL_LEVELS:
    its = items(lin, lv, N, 9, "dp")
    changed = nonuniq = 0
    with_contains = 0
    first_small = two_small = redundant = 0
    for it in its:
        key, alt = st.solve(lin.id, it.question)
        a = alt["contains_means_exactly_one"]
        if "one of its digits is" in it.question:
            with_contains += 1
        if a != it.answer:
            if a.startswith("NOT_UNIQUE"):
                nonuniq += 1
            else:
                changed += 1
        nd = it.structured["digits"]
        rng = range(10 ** (nd - 1), 10 ** nd)
        from studies.m0.lineages_m1_rev2 import _clue_holds  # the generator's clue predicate, used only to evaluate cheap rules (keys were checked by my own text solver)
        cl = [tuple(c) for c in it.structured["clues"]]
        def ok(x, cs):
            return all(_clue_holds(x, tuple(int(ch) for ch in str(x)), c) for c in cs)
        f1 = [x for x in rng if ok(x, cl[:1])]
        f2 = [x for x in rng if ok(x, cl[:2])]
        first_small += str(min(f1)) == it.answer
        two_small += str(min(f2)) == it.answer
        redundant += any(len([x for x in rng if ok(x, cl[:i] + cl[i + 1:])]) == 1 for i in range(len(cl)))
    print(f"L{lv}: items with a 'one of its digits is' clue {with_contains}/{N}; under 'exactly one': key changed {changed}, no unique answer {nonuniq}; "
          f"smallest meeting clue 1: {first_small / N:.3f}; smallest meeting clues 1-2: {two_small / N:.3f}; some clue redundant: {redundant / N:.3f}")
