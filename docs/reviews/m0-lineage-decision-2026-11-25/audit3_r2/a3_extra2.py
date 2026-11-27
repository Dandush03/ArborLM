# ruff: noqa
"""Audit 3 (R2): third-pass checks. (1) subtraction_game: does key balancing by redraw leak through the move set or pile sizes alone?
For each simple feature f, the best rule 'answer = yes iff f' or its negation is fitted on the training draw (seed |5) and scored on the test draw (seed |6).
(2) bracket_match valid: share of 'no' items whose swapped pairs include a top-level pair. N per level from argv."""
import random
import sys
from collections import Counter

from studies.m0.core import ALL_LEVELS, build_item
from a3_set import current

N = int(sys.argv[1])
cur = current()

FEATS = {
    "1 in moves": lambda s: 1 in s["moves"],
    "smallest move even": lambda s: s["moves"][0] % 2 == 0,
    "all moves odd": lambda s: all(m % 2 for m in s["moves"]),
    "four moves": lambda s: len(s["moves"]) == 4,
    "piles same parity": lambda s: s["piles"][0] % 2 == s["piles"][1] % 2,
    "piles differ by < smallest move": lambda s: abs(s["piles"][0] - s["piles"][1]) < s["moves"][0],
    "piles congruent mod smallest move": lambda s: s["piles"][0] % s["moves"][0] == s["piles"][1] % s["moves"][0],
    "piles congruent mod (smallest+largest)": lambda s: s["piles"][0] % (s["moves"][0] + s["moves"][-1]) == s["piles"][1] % (s["moves"][0] + s["moves"][-1]),
}
lin = cur["R2.subtraction_game"]
for fname, f in FEATS.items():
    cells = []
    for lv in ALL_LEVELS:
        tr = [build_item(lin, lv, random.Random(f"a3r2|{lin.id}|{lv}|5"), "A", "t") for _ in range(0)]
        rtr = random.Random(f"a3r2|{lin.id}|{lv}|5")
        rte = random.Random(f"a3r2|{lin.id}|{lv}|6")
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(N)]
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(N)]
        acc_pos = sum((it.answer == "yes") == f(it.structured) for it in tr) / N
        sign = acc_pos >= 0.5
        acc = sum(((it.answer == "yes") == f(it.structured)) == sign for it in te) / N
        cells.append(f"{acc:.2f}")
    print(f"subtraction_game | {fname} (direction fitted on train) | " + " ".join(cells), flush=True)

lin = cur["R2.bracket_match"]
cells = []
for lv in ALL_LEVELS:
    r = random.Random(f"a3r2|{lin.id}|{lv}|6")
    k = n = 0
    for _ in range(N):
        it = build_item(lin, lv, r, "A", "e")
        s = it.structured
        if s["ask"] != "valid" or it.answer != "no":
            continue
        t = s["s"]
        # find positions where the depth-0 pairs mismatch
        d, st, bad_top = 0, [], False
        mp = {")": "(", "]": "[", "}": "{"}
        for ch in t:
            if ch in "([{":
                st.append(ch)
            else:
                o = st.pop()
                if not st and o != mp[ch]:
                    bad_top = True
        n += 1
        k += bad_top
    cells.append(f"{k / n:.2f}(n={n})")
print("bracket_match valid/no: share with a mismatched top-level pair | " + " ".join(cells))
