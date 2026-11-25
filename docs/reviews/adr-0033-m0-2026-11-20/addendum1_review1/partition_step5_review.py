# ruff: noqa
"""Addendum 1 section 4 step 5: how unequal can parts be forced by cross-evaluation (X) clusters? Made-up counts only.
Reviewer's own code. A first scratch attempt (experiments/_scratch/m0_addendum1_review1_20261125/step5_scen.py) had a
scenario "B" in which 20 X clusters touched R2 with G_R2 = 19, which is impossible; it is kept there and not used.
Run: uv run --locked python docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/partition_step5_review.py
"""
import random
def run(scen, xs, reps=20000, seed=1):
    for e, g in scen.items():
        assert sum(1 for t in xs if e in t) <= g, (e, "more X clusters than clusters")
    rng = random.Random(seed)
    stats = {e: [0, 0, []] for e in scen}
    for _ in range(reps):
        order = list(range(len(xs))); rng.shuffle(order)
        pa = {i: ("A" if r % 2 == 0 else "B") for r, i in enumerate(order)}
        for e, g in scen.items():
            xe = [i for i, t in enumerate(xs) if e in t]
            xa = sum(1 for i in xe if pa[i] == "A"); le = g - len(xe); target = g // 2
            a = xa + min(le, max(0, target - xa)); b = g - a
            st = stats[e]; st[0] += (a != target); st[1] = max(st[1], abs(a - b)); st[2].append(min(a, b))
    for e, g in scen.items():
        st = stats[e]; mp = sorted(st[2])
        print(f"  {e}: G={g}, X touching={sum(1 for t in xs if e in t)}: P(parts differ from floor/ceil half)={st[0]/reps:.3f}; "
              f"largest |A-B|={st[1]}; smaller part: 1st percentile {mp[int(.01*reps)]}, minimum {mp[0]}")
print("scenario 1: |X| = 14, mostly R2-C1 (C1 programs implementing R2 algorithms)")
run({"R1": 13, "R2": 19, "M1": 11, "C1": 14}, [("R2","C1")]*10 + [("M1","R2")]*2 + [("R1","C1")]*2)
print("scenario 2: |X| = 21; C1 has 11 clusters, 10 of them cross")
run({"R1": 13, "R2": 19, "M1": 11, "C1": 11}, [("R2","C1")]*7 + [("M1","R2")]*6 + [("R1","C1")]*2 + [("M1","C1")]*1 + [("R1","R2")]*5)
print("scenario 3: |X| = 21; C1 has 14 clusters, 8 of them cross")
run({"R1": 13, "R2": 19, "M1": 11, "C1": 14}, [("R2","C1")]*5 + [("M1","R2")]*6 + [("R1","C1")]*2 + [("M1","C1")]*1 + [("R1","R2")]*7)
