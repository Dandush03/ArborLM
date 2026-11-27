"""Item 4: three facts. (i) R1.temporal_weekday_shift_r6: no repeated key; (ii) R2.cellular_automaton level 0 = 2^15;
(iii) M1.rectangle_r3 key space at levels 0 and 1 and the M1.ages cluster."""
import json
import random
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402
from studies.m0.core import build_item  # noqa: E402
from studies.m0.registration.distinct_key import item_key, key_text  # noqa: E402

S = rc.SCR
out = {}
L = rc.lineages()

# ---------------------------------------------------------------- (i) temporal
tid = "R1.temporal_weekday_shift_r6"
for label in ("capacity", "capacity-recompute-extra"):
    r = rc.count_cell(tid, 0, 500000, check_solver=False, save_keys=False, budget_override=500000, label=label)
    out[f"i_temporal_L0_500k_{label}"] = {k: r[k] for k in ("count", "attempts", "ended", "keys_sha256")}
    print("(i)", label, out[f"i_temporal_L0_500k_{label}"], flush=True)
n = 500000
out["i_key_space_lower_bound_L0"] = {
    "ordered_day_counts": "300^7", "value": 300 ** 7,
    "expected_pairs_sharing_the_ordered_tuple_in_241000": 241000 * 240999 / 2 / 300 ** 7,
    "expected_pairs_sharing_the_ordered_tuple_in_500000": n * (n - 1) / 2 / 300 ** 7,
}
print("(i) lower bound", out["i_key_space_lower_bound_L0"], flush=True)

# names-only rename: same random state, EVENTS replaced by a permutation of itself in the builder's module
import studies.m0.lineages_r1_fix4_a as mod  # noqa: E402

orig = list(mod.EVENTS)
perm = orig[:]
random.Random(7).shuffle(perm)
assert perm != orig
res = {}
for lv in (0, 3, 6):
    same_key = diff_text = diff_answer = 0
    example = None
    for j in range(2000):
        st = random.Random(f"rename|{lv}|{j}").getstate()
        g = random.Random()
        g.setstate(st)
        mod.EVENTS = orig
        a = build_item(L[tid], lv, g, "x", "y")
        g.setstate(st)
        mod.EVENTS = perm
        b = build_item(L[tid], lv, g, "x", "y")
        mod.EVENTS = orig
        if a.question != b.question:
            diff_text += 1
        if a.answer != b.answer:
            diff_answer += 1
        if item_key(tid, a.question, a.structured) == item_key(tid, b.question, b.structured):
            same_key += 1
        if example is None and a.question != b.question:
            example = {"a": a.question, "b": b.question, "key_text_a": key_text(tid, a.question, a.structured),
                       "key_text_b": key_text(tid, b.question, b.structured)}
    res[lv] = {"pairs": 2000, "texts_differ": diff_text, "keys_equal": same_key, "answers_differ": diff_answer}
    if lv == 0:
        out["i_rename_example_L0"] = example
out["i_rename_names_only"] = res
print("(i) rename", res, flush=True)
# a sharper control: change ONE day count by 1 in the same item -> key must change
from studies.m0.lineages_r1_common import pl  # noqa: E402,F401
g = random.Random(11)
a = build_item(L[tid], 0, g, "x", "y")
qa = a.question
i = qa.index(" day")
j = i
while qa[j - 1].isdigit():
    j -= 1
num = int(qa[j:i])
qb = qa[:j] + str(num + 1 if num < 300 else num - 1) + qa[i:]
out["i_one_number_changed_key_differs"] = item_key(tid, qa, a.structured) != item_key(tid, qb, a.structured)
print("(i) one number changed -> key differs:", out["i_one_number_changed_key_differs"], flush=True)

# ---------------------------------------------------------------- (ii) cellular automaton
cid = "R2.cellular_automaton"
# enumerate the level-0 item space from the builder's own parameters: 9 free row bits x 6 free table bits
space = {}
for lv in rc.LEVELS:
    space[lv] = 2 ** (11 + 2 * lv - 2) * 2 ** 6
out["ii_space_by_level"] = space
# check the counting: no retry is possible (001 = 1 - 100 makes the table non-constant); first attempt reaching 2^15
r = rc.count_cell(cid, 0, 32768, check_solver=False, save_keys=False)
out["ii_L0_draw_to_32768"] = {k: r[k] for k in ("count", "attempts", "ended")}
r2 = rc.count_cell(cid, 0, 40000, check_solver=False, save_keys=False, budget_override=2000000)
out["ii_L0_2000000_attempts"] = {k: r2[k] for k in ("count", "attempts", "ended")}
# distinct texts by exhaustive rendering through the builder with a scripted random source
class Scripted(random.Random):
    def __init__(self, bits):
        super().__init__(0)
        self.bits = list(bits)

    def randint(self, a, b):
        assert (a, b) == (0, 1)
        return self.bits.pop(0)


texts = set()
keys = set()
answers = {}
for row in range(2 ** 9):
    for tb in range(2 ** 6):
        rb = [(row >> i) & 1 for i in range(9)]
        free = [(tb >> i) & 1 for i in range(6)]
        # table keys in builder order: 111,110,101,100,011,010,001,000 ; 011 and 001 overwritten afterwards
        tbits = [free[0], free[1], free[2], free[3], 0, free[4], 0, free[5]]
        b = L[cid].build(0, Scripted(rb + tbits))
        texts.add(b.question)
        keys.add(item_key(cid, b.question, b.structured))
out["ii_L0_exhaustive"] = {"distinct_texts": len(texts), "distinct_keys": len(keys)}
print("(ii)", out["ii_space_by_level"], out["ii_L0_draw_to_32768"], out["ii_L0_2000000_attempts"], out["ii_L0_exhaustive"], flush=True)

# ---------------------------------------------------------------- (iii) rectangle and M1.ages
rid = "M1.rectangle_r3"
rect = {}
for lv in rc.LEVELS:
    nw = 60 + 10 * lv - 1
    rect[lv] = {"widths": nw, "ratio_items": nw * 11, "excess_items": nw * 60, "total": nw * 71}
out["iii_rectangle_space"] = rect
# exhaustive by rendering
for lv in (0, 1):
    ks = set()
    for w in range(2, 61 + 10 * lv):
        for k in range(2, 13):
            ks.add(f"r|{2 * (w + k * w)}|{k}")
        for d in range(1, 61):
            ks.add(f"e|{2 * (2 * w + d)}|{d}")
    rect[lv]["distinct_(shape,perimeter,parameter)"] = len(ks)
# the demand on rectangle as a function of k in its cluster at G = 8
out["iii_D_lin_8_k"] = {k: rc.D_lin(8, k) for k in range(1, 9)}
print("(iii)", rect, out["iii_D_lin_8_k"], flush=True)
json.dump(out, open(f"{S}/deliver/g_facts.json", "x"), indent=1, sort_keys=True)
