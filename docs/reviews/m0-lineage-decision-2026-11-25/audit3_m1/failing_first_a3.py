# ruff: noqa
"""Audit 3 of M1: would the fix-round tests have failed on the PRE-FIX (batch-1) shapes? Imports the batch-1 shapes read-only (no git state touched) and applies
the same assertions as tests/test_m0_m1_rev2_generators.py::test_shape_mix_is_the_designs_uniform_mix_at_every_level, ::test_no_revised_builder_ever_raises_retry and
test_m0_m1_rev2_generators.py::test_inclusion_exclusion_ask_mix..., with audit seed 9."""
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from studies.m0.core import ALL_LEVELS, Retry, build_item, stream
from studies.m0.lineages_m1_common import load_batch

OLD = {x.id: x for x in load_batch()}
CASES = [("M1.gcd_lcm", "ask", {"gcd", "lcm"}), ("M1.division_counting", "shape", {"pallets", "empty_seats"}), ("M1.pigeonhole_worst_case", "goal", {"same", "all"}),
         ("M1.binomial_choose", "shape", {"plain", "include", "two_groups"}), ("M1.mode_tally", "ask", {"mode", "mode_count"}),
         ("M1.prime_factors", "ask", {"divisors", "largest", "distinct_sum", "factor_count"}), ("M1.pythagoras", "shape", {"ladder_top", "ladder_base", "walk", "diagonal", "perimeter"}),
         ("M1.painted_cube", "faces", {"0", "1", "2"})]
for lid, key, vals in CASES:
    bad = []
    for lv in ALL_LEVELS:
        rng = stream(9, "ff", lid, str(lv))
        try:
            c = Counter(str(build_item(OLD[lid], lv, rng, "A", "t").structured.get(key)) for _ in range(1500))
        except Exception as e:
            bad.append(f"L{lv}: error {e!r}")
            continue
        m = {k: v / 1500 for k, v in c.items()}
        if set(m) != vals or any(abs(s - 1 / len(vals)) >= 0.06 for s in m.values()):
            bad.append(f"L{lv}:{ {k: round(v, 2) for k, v in m.items()} }")
    print(lid, "WOULD FAIL" if bad else "would pass", bad[:3])
lin = OLD["M1.inclusion_exclusion"]
bad = []
for lv in ALL_LEVELS:
    rng = stream(9, "ff-ie", str(lv))
    c = Counter(build_item(lin, lv, rng, "A", "t").structured["ask"] for _ in range(1500))
    want = 4 if lv >= 5 else 2
    if len(c) != want or any(abs(v / 1500 - 1 / want) >= 0.06 for v in c.values()):
        bad.append((lv, dict(c)))
print("M1.inclusion_exclusion ask mix", "WOULD FAIL" if bad else "would pass", bad[:2])
raised = []
for lid, lin in sorted(OLD.items()):
    n = 0
    for lv in ALL_LEVELS:
        rng = stream(9, "ff-retry", lid, str(lv))
        for _ in range(150):
            try:
                lin.build(lv, rng)
            except Retry:
                n += 1
    if n:
        raised.append((lid, n))
print("batch-1 builders that raise Retry (the no-Retry test would fail on them):", raised)
