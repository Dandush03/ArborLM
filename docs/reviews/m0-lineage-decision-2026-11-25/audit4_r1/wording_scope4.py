# ruff: noqa
"""Audit 4 (R1): attribute_rule_r5 under the wide reading of "it is not true that ..." (the negation takes the rest of its parenthesis).
Counts items whose key changes or that lose a unique answer; also how many rules have a negation followed by "and"/"or" at the same depth
(the only places where the two readings can differ). Seed base 4100 (as the key check), 400 per level.
usage: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this>"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen4, solvers4 as S
lin = gen4.lineages()["R1.attribute_rule_r5"]
for lv in range(7):
    its = gen4.items(lin, lv, 400, 4100)
    exposed = changed = nonunique = 0
    for b in its:
        rule = re.search(r"satisfies this rule: (.+?)\. The badges: ", b.question).group(1)
        if re.search(r"it is not true that (it is \w+|it has an? \w+) (and|or) ", rule):
            exposed += 1
        try:
            a = S.attribute_rule_r5(b.question, wide=True)
            changed += a != b.answer
        except S.Ambiguous:
            nonunique += 1
    print(f"L{lv}: items 400, negation followed by and/or at its depth {exposed}, key changes {changed}, no unique answer {nonunique}")
