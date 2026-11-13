"""Hand checks of the reviewer's reading of ADR-0014 section 4 (affinity weights, greedy tie rules).
Usage (repo root): .venv/bin/python -I docs/reviews/p7b-spec-review-2026-11-13/scripts/test_reading.py"""
import array, importlib.util
spec = importlib.util.spec_from_file_location("cc", "docs/reviews/p7b-spec-review-2026-11-13/scripts/calib_coaccess.py")
cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)
# one context; query 0 selects slots 0..7, query 1 selects 0,8..14; others select 100..107 (far away)
rows = [list(range(8)), [0] + list(range(8, 15))] + [list(range(100, 108))] * 62
sel = array.array("h", [s for r in rows for s in r] + [200 + (i % 8) for i in range(8 * 64 * 511)])
A0 = cc.affinity(sel, 0, [0]); A1 = cc.affinity(sel, 1, [0])
print("A0[1][2] (same query) =", A0[1][2], "| A1[1][2] =", A1[1][2], "| A1[1][9] (lag 1, once each way) =", A1[1][9], "| A1[0][9] =", A1[0][9])
assert A0[1][2] == 2 and A1[1][9] == 1   # same-query pair weighted 2, lagged pair 1: the transpose doubles t=u
assert 0 not in A1[0]                    # slot 0 at t=0 and t=1: i != j excludes self-pairs
# greedy ties: f ties and score ties resolved by (score, f, -id)
f = [0] * 4096; f[5] = 10; f[3] = 10; f[7] = 4; f[9] = 4; f[11] = 1
A = {3: {7: 2, 9: 2}, 7: {3: 2}, 9: {3: 2}, 5: {11: 1}, 11: {5: 1}}
pages = cc.greedy_pages(list(range(4096)), 2, f, A)
print("first pages:", pages[:3])
assert pages[0] == [3, 7]   # seed: f tie 3 vs 5 -> lowest id 3; then score tie 7 vs 9 at equal f -> lowest id 7
assert pages[1] == [5, 11] and pages[2] == [9, 0]   # 9 has no unplaced partner -> hottest unplaced (f=0 -> id 0)
print("reading checks OK")
