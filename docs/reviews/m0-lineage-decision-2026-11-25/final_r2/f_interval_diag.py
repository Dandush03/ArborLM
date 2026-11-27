# ruff: noqa
"""Final R2 audit, DIAGNOSTIC ONLY (not pooled into the R-32 estimate): the '[impl] shortest first' rule on interval_scheduling level 0
over 10 further independent seed sets of 2,000 test items, to see whether my fresh-seed reading (0.1512 on 4,000) is in the spread.
Seeds random.Random(f"finalr2-diag|R2.interval_scheduling|0|{j}") j = 0..9. Usage: as f_rules.py."""
import random
from studies.m0.core import build_item
from studies.m0.r2_fix4_set import fix4_set
from studies.m0.r2_fix3_heuristics import OWN
lin = fix4_set()["R2.interval_scheduling"]
fn = dict(OWN["interval_scheduling"])["shortest first"]
tot = 0
for j in range(10):
    r = random.Random(f"finalr2-diag|R2.interval_scheduling|0|{j}")
    k = 0
    for _ in range(2000):
        it = build_item(lin, 0, r, "A", "e")
        k += fn(it.structured, it.question) == it.answer
    tot += k
    print(j, k / 2000)
print("mean over 20,000:", tot / 20000)
