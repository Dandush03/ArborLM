# ruff: noqa
"""Audit 3 (R1): extra checks written after the first battery design.
(a) containers_stack_piles_r4: the asked pile is chosen among piles whose last change was a removal or a turn. Read as a
    two-sided tell: "the block last moved onto the asked pile" (never right by that rule?) and the elimination reading.
(b) temporal_critical_path_r4: share of items whose key changes under the inclusive-day reading (a job of t days that starts on
    day d works days d..d+t-1, is finished on day d+t-1, and a job waiting for it starts on day d+t).
(c) instant_runoff_r4: share of draws refused by the tie rule, per level (affects what the generator can produce).
(d) nim_xor_r4: accuracy of the "xor of bit 1 only" rule per level.
Seeds: base 8100 + level (throwaway). usage (worktree root): PYTHONHASHSEED=0 uv run --locked python <this> <n>
"""
import os, random, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import gen
from studies.m0.core import Retry

n = int(sys.argv[1])
L = gen.lineages()
print("(a) containers_stack_piles_r4")
for lv in range(7):
    its = gen.items(L["R1.containers_stack_piles_r4"], lv, n, 8100)
    hit = fired = anti = 0.0
    for b in its:
        st = b.structured
        onto = [o for o in st["ops"] if o[0] == "move" and o[2] == st["ask"]]
        # which block was moved onto the asked pile last: simulate
        s = {p: list(v) for p, v in st["initial"].items()}
        last_onto = None
        for o in st["ops"]:
            if o[0] == "reverse":
                s[o[1]].reverse()
            else:
                blk = s[o[1]].pop(); s[o[2]].append(blk)
                if o[2] == st["ask"]:
                    last_onto = blk
        if last_onto is None:
            continue
        fired += 1
        hit += last_onto == b.answer
        anti += (b.answer != last_onto) / (b.k - 1)
    print(f"  level {lv}: fires {int(fired)}/{n}, last-onto right {hit / max(fired, 1):.3f} vs chance {1 / its[0].k:.3f}; elimination (pick among the others) {anti / max(fired, 1):.3f}, gain {anti / max(fired, 1) - 1 / its[0].k:+.3f}")
print("(b) temporal_critical_path_r4: key under the inclusive-day reading equals key - 1 in every item (by construction); checked:")
ch = 0; tot = 0
for lv in range(7):
    for b in gen.items(L["R1.temporal_critical_path_r4"], lv, n, 8100):
        jobs = {p: (d, deps) for p, d, deps in b.structured["jobs"]}
        start = {}
        def fin(p):  # inclusive: works start..start+d-1; dependents start the day after the last finishes
            if p not in start:
                start[p] = max([fin(x) + 1 for x in jobs[p][1]], default=0)
            return start[p] + jobs[p][0] - 1
        alt = max(fin(p) for p in jobs)
        ch += str(alt) != b.answer; tot += 1
print(f"  keys that change: {ch}/{tot}")
print("(c) instant_runoff_r4 refusals by the tie rule")
for lv in range(7):
    r = random.Random(8100 + lv); ok = rej = 0
    while ok < n:
        try:
            L["R1.instant_runoff_r4"].build(lv, r); ok += 1
        except Retry:
            rej += 1
    print(f"  level {lv}: refused {rej} of {ok + rej} draws ({rej / (ok + rej):.2f})")
print("(d) nim_xor_r4 bit-1 parity rule")
for lv in range(7):
    its = gen.items(L["R1.nim_xor_r4"], lv, n, 8100)
    acc = sum((("first" if sum((p >> 1) & 1 for p in b.structured["piles"]) % 2 else "second") == b.answer) for b in its) / n
    print(f"  level {lv}: accuracy {acc:.3f} (chance 0.5), gain {acc - 0.5:+.3f}")
