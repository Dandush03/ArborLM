"""Items 1 and 4: my count (a_common.my_count, written from the text) against capacity.count, on toy lineages and on
real lineages under the audit label; and the cache / prefix question.

capacity.LABEL is set to "capacity-audit" in this process BEFORE any draw, and capacity.stream is wrapped so that a
draw under the label "capacity" raises. Reports agreements and disagreements only: no count of a real lineage is
printed or kept (real-lineage lines print only equal/different and the way the draw ended for the budget probe,
which uses an artificial coarse key, not the key of record)."""
import hashlib, json, os, random, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import AUDIT_LABEL, SCR, W, load_lineages, load_solvers, my_count, my_stream
from studies.m0 import core
from studies.m0.core import Built, Lineage, Retry
from studies.m0.registration import capacity as cap
from studies.m0.registration import distinct_key as dk

# ---- the registered label and argument order, read without drawing
lins = load_lineages()
x = lins["R1.compass_turns"]
assert cap.SEED == 400002 and cap.LABEL == "capacity"
assert cap.stream_labels(x, 3) == ("capacity", "R1", "R1.compass_turns", "3"), cap.stream_labels(x, 3)
assert core.derive_seed(7, "a", "b|c") == int.from_bytes(hashlib.sha256(b"7|a|b|c").digest()[:8], "big")
print("registered label and order: stream_labels ->", cap.stream_labels(x, 3), "seed", cap.SEED)

cap.LABEL = AUDIT_LABEL
_orig_stream = cap.stream
def guarded(seed, *labels):
    if labels and labels[0] == "capacity":
        raise RuntimeError("guard: registered label")
    return _orig_stream(seed, *labels)
cap.stream = guarded
assert cap.stream_labels(x, 3)[0] == AUDIT_LABEL

KEY = dk.item_key
results = {"toys": [], "real": [], "cache": [], "budget_probe": []}
dis = 0


def same(a_draw, mine):
    keys_t = [a_draw.keys[i:i + 16] for i in range(0, len(a_draw.keys), 16)]
    order, ended, att = mine
    return keys_t == order and a_draw.ended == ended and a_draw.count == len(order) and a_draw.attempts == att


# ---- toy lineages
def sched_lineage(lid, schedule):
    """schedule: list of tokens per build CALL: int k -> item with content k; 'R' -> Retry. Fresh closure per use."""
    st = {"n": 0}
    def build(level, rng):
        rng.random()
        i = st["n"]; st["n"] += 1
        tok = schedule[i] if i < len(schedule) else 0
        if tok == "R":
            raise Retry()
        return Built(f"toy item {tok}", {"i": tok}, str(tok), "number", None)
    return Lineage(lid, lid.split(".")[0], "toy", build)


def rand_lineage(lid, n_distinct, retry_p=0.0):
    def build(level, rng):
        if retry_p and rng.random() < retry_p:
            raise Retry()
        k = rng.randrange(n_distinct)
        return Built(f"Ben has {k} apples at level {level}.", {"i": k}, str(k), "number", None)
    return Lineage(lid, lid.split(".")[0], "toy", build)


toy_cases = []
# budget binding exactly at the boundary: T = 5, budget 1,200
s = [1, 2, 3, 4] + [1] * 1195 + [5]
toy_cases.append(("boundary: 5th key at attempt 1200 = budget", lambda: sched_lineage("R1.toyb1", s), 5))
s2 = [1, 2, 3, 4] + [1] * 1196 + [5]
toy_cases.append(("boundary: 5th key at attempt 1201 = budget+1", lambda: sched_lineage("R1.toyb2", s2), 5))
# give-up: 3 keys, then 500 consecutive retries in attempt 4
s3 = [1, 2, 3] + ["R"] * 500 + [4]
toy_cases.append(("give-up after 500 retries at attempt 4", lambda: sched_lineage("R1.toyg1", s3), 10))
s4 = [1, 2, 3] + ["R"] * 499 + [4, 5, 6]
toy_cases.append(("499 retries then success: no give-up", lambda: sched_lineage("R1.toyg2", s4), 6))
s5 = [1, 1, 1, 2] + ["R"] * 500
toy_cases.append(("give-up when duplicates precede", lambda: sched_lineage("R1.toyg3", s5), 3))
s6 = [7] * 2000
toy_cases.append(("one distinct item, T = 1", lambda: sched_lineage("R1.toyone", s6), 1))
toy_cases.append(("one distinct item, T = 2 (budget 1,080)", lambda: sched_lineage("R1.toyone2", s6 * 2), 2))
for n_d in (1, 7, 50, 999, 1000, 1001, 3000):
    for T in (1, 50, 1000, 1001, 2500):
        toy_cases.append((f"random toy {n_d} distinct, T {T}", (lambda n_d=n_d: rand_lineage(f"M1.toyr{n_d}", n_d)), T))
toy_cases.append(("random toy with retries p=0.9", lambda: rand_lineage("R2.toyretry", 400, 0.9), 450))
toy_cases.append(("random toy with retries p=0.995 (gives up)", lambda: rand_lineage("R2.toyretry2", 400, 0.995), 450))

for name, mk, T in toy_cases:
    a = cap.count(mk(), 2, T, key_fn=KEY)
    m = my_count(mk(), 2, T, KEY)
    ok = same(a, m)
    dis += not ok
    results["toys"].append({"case": name, "T": T, "equal": ok, "theirs": [a.count, a.ended, a.attempts], "mine": [len(m[0]), m[1], m[2]]})
    print("TOY", "AGREE" if ok else "DISAGREE", name, "| theirs", a.count, a.ended, a.attempts, "| mine", len(m[0]), m[1], m[2])

# ---- real lineages, audit label, targets <= 3000; equality only
REAL = {
    "R1": ["R1.compass_turns", "R1.knights_knaves_r6", "R1.temporal_weekday_shift_r6"],
    "R2": ["R2.caesar_shift", "R2.cheapest_network", "R2.dictionary_rank"],
    "M1": ["M1.shopping_r3", "M1.change_ways_r3", "M1.tiered_pricing"],
    "C1": ["C1.postfix_evaluation", "C1.slices_f4", "C1.func_compose_f4"],
}
sols = load_solvers()
for ev, ids in REAL.items():
    for lid in ids:
        for lv in (0, 3, 6):
            for T in (300, 3000):
                a = cap.count(lins[lid], lv, T, key_fn=KEY, solver=sols[lid] if T == 300 else None)
                m = my_count(lins[lid], lv, T, KEY)
                ok = same(a, m)
                dis += not ok
                results["real"].append({"lineage": lid, "level": lv, "T": T, "key_sets_identical": ok,
                                        "solver_checked": T == 300, "solver_disagreements": a.n_disagreements if T == 300 else None})
                print("REAL", "AGREE" if ok else "DISAGREE", lid, lv, T, ("solver dis " + str(a.n_disagreements)) if T == 300 else "")

# ---- item 4: cache and prefix, real lineages, audit label
cdir = f"{SCR}/work/cache_d_count"
os.makedirs(cdir, exist_ok=False)
cache = cap.TraceCache(cdir, "audit-d")
for lid in ["R1.compass_turns", "R2.cheapest_network", "M1.shopping_r3", "C1.postfix_evaluation"]:
    for lv in (0, 6):
        T1, T2 = 400, 1500
        a1 = cap.count(lins[lid], lv, T1, cache=cache, key_fn=KEY)
        a2 = cap.count(lins[lid], lv, T2, cache=cache, key_fn=KEY)  # continued from the stored state
        a1b = cap.count(lins[lid], lv, T1, cache=cache, key_fn=KEY)  # answered from the longer trace
        m1 = my_count(lins[lid], lv, T1, KEY); m2 = my_count(lins[lid], lv, T2, KEY)
        prefix = m2[0][:len(m1[0])] == m1[0]
        ok = same(a1, m1) and same(a2, m2) and same(a1b, m1)
        dis += not (ok and prefix)
        results["cache"].append({"lineage": lid, "level": lv, "cache_equals_fresh": ok, "T1_prefix_of_T2": prefix})
        print("CACHE", "AGREE" if ok else "DISAGREE", "prefix" if prefix else "NOT-PREFIX", lid, lv)


# budget probe: an artificial coarse key that makes the budget bind on real builders (NOT the key of record)
def coarse(lid, q, st):
    k = dk.item_key(lid, q, st)
    return k if k[0] < 3 else bytes([k[1] % 50]) * 16


for lid in ["R1.knights_knaves_r6", "M1.change_ways_r3", "R2.dictionary_rank", "C1.slices_f4"]:
    cd = f"{SCR}/work/cache_budget_{lid}"
    os.makedirs(cd, exist_ok=False)
    cc = cap.TraceCache(cd, "audit-budget")
    lv = 4
    T1, T2, T3 = 200, 400, 300
    a1 = cap.count(lins[lid], lv, T1, cache=cc, key_fn=coarse)
    a2 = cap.count(lins[lid], lv, T2, cache=cc, key_fn=coarse)
    a3 = cap.count(lins[lid], lv, T3, cache=cc, key_fn=coarse)
    m1 = my_count(lins[lid], lv, T1, coarse); m2 = my_count(lins[lid], lv, T2, coarse); m3 = my_count(lins[lid], lv, T3, coarse)
    prefix = m2[0][:len(m1[0])] == m1[0] and m2[0][:len(m3[0])] == m3[0]
    ok = same(a1, m1) and same(a2, m2) and same(a3, m3)
    dis += not (ok and prefix)
    results["budget_probe"].append({"lineage": lid, "level": lv, "coarse_key": True, "ended": [m1[1], m2[1], m3[1]],
                                    "cache_equals_fresh": ok, "lower_is_prefix": prefix})
    print("BUDGET-PROBE", "AGREE" if ok else "DISAGREE", "prefix" if prefix else "NOT-PREFIX", lid, "ended", m1[1], m2[1], m3[1])

results["disagreements"] = dis
print("TOTAL DISAGREEMENTS", dis)
with open(f"{SCR}/deliver/d_count.json", "x") as f:
    json.dump(results, f, indent=1, sort_keys=True)
