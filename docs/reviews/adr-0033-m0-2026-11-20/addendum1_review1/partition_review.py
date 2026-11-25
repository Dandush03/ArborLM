# ruff: noqa
"""The cluster partition of addendum 1, section 4, implemented by the reviewer from the addendum's text alone (plus
ADR-0033 section 12 line 576), on a MADE-UP cluster list. Imports nothing from studies/.

Every point where the text did not determine the computation is a GUESS, numbered, and the script runs the partition
under alternative guesses to show whether the split changes.

Part 2 quantifies section 4 step 5 (unequal parts forced by cross-evaluation clusters) by Monte Carlo over seeds, for
made-up counts. Nothing here is a real lineage or a real map.

Run: uv run --locked python docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/partition_review.py
"""
import hashlib
import random

SEED = 400004

# ---- made-up written lineages: id -> (evaluation, registered?) ; ids carry the evaluation prefix (GUESS 3)
LINEAGES = {}
for e, k in (("R1", 9), ("R2", 10), ("M1", 7), ("C1", 8)):
    for i in range(k):
        LINEAGES[f"{e.lower()}_l{i:02d}"] = (e, not (e == "M1" and i == 6))  # m1_l06 NOT REGISTERED
# made-up auditor links ("same procedure"), within and across evaluations
LINKS = [
    ("r1_l00", "r1_l01"), ("r2_l03", "c1_l00"), ("r2_l04", "c1_l01"), ("c1_l01", "r2_l05"),  # chain: r2_l04~c1_l01~r2_l05
    ("m1_l02", "r2_l07"), ("m1_l06", "c1_l05"),  # m1_l06 is NOT REGISTERED: its cluster is X only via registered members?
    ("r1_l05", "c1_l06"), ("c1_l06", "m1_l03"), ("r2_l09", "r2_l08"),
]


def components():
    parent = {x: x for x in LINEAGES}

    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in LINKS:
        ra, rb = f(a), f(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    comp = {}
    for x in LINEAGES:
        comp.setdefault(f(x), []).append(x)
    # identity: lexicographically smallest lineage id (GUESS 4: Python code-point order of the id string)
    return {min(v): sorted(v) for v in comp.values()}


def stream_v1(*labels):
    """GUESS 1a: the implementation-style reading: sha256('|'.join([str(seed), *labels])) first 8 bytes big-endian,
    seeding Python's random.Random (Mersenne Twister). Not stated in ADR-0033 line 576 or the addendum."""
    dg = hashlib.sha256("|".join([str(SEED), *labels]).encode()).digest()
    return random.Random(int.from_bytes(dg[:8], "big"))


def stream_v2(*labels):
    """GUESS 1b: an equally literal reading: sha256 over the seed's decimal text followed directly by the labels,
    full 256-bit integer, seeding random.Random."""
    dg = hashlib.sha256((str(SEED) + "".join(labels)).encode()).digest()
    return random.Random(int.from_bytes(dg, "big"))


def shuffle_py(xs, rng):
    """GUESS 2a: Python's random.shuffle (Fisher-Yates from the end with _randbelow)."""
    ys = list(xs)
    rng.shuffle(ys)
    return ys


def shuffle_sortkey(xs, rng):
    """GUESS 2b: sort by a random key per element drawn in input order."""
    keys = [rng.random() for _ in xs]
    return [x for _, x in sorted(zip(keys, xs))]


def partition(stream, shuffle):
    comps = components()
    evals = ("R1", "R2", "M1", "C1")
    # step 1: only global clusters with at least one registered lineage; X = registered in >= 2 evaluations
    reg_evals = {cid: sorted({LINEAGES[x][0] for x in mem if LINEAGES[x][1]}) for cid, mem in comps.items()}
    assigned = {cid: ev for cid, ev in reg_evals.items() if ev}
    X = sorted(cid for cid, ev in assigned.items() if len(ev) >= 2)
    part = {}
    # step 2: shuffle X, alternate starting with A (the text: "A, B, A, B")
    for i, cid in enumerate(shuffle(X, stream("cluster-partition", "cross"))):
        part[cid] = "A" if i % 2 == 0 else "B"
    # step 3
    report = {}
    for e in evals:
        total = sorted(cid for cid, ev in assigned.items() if e in ev)
        target = len(total) // 2
        xa = sum(1 for cid in total if cid in X and part[cid] == "A")
        L = sorted(cid for cid in total if assigned[cid] == [e])
        sh = shuffle(L, stream("cluster-partition", e))
        k = max(0, target - xa)  # GUESS 5: if k > len(L) every L cluster goes to A (text silent)
        for i, cid in enumerate(sh):
            part[cid] = "A" if i < k else "B"
        a = sum(1 for cid in total if part[cid] == "A")
        report[e] = (len(total), a, len(total) - a)
    return part, report, X


def main():
    comps = components()
    print("made-up global clusters (identity: members):")
    for cid, mem in sorted(comps.items()):
        if len(mem) > 1:
            print(f"  {cid}: {mem}")
    results = {}
    for sname, s in (("stream v1 ('|'-joined, 8 bytes)", stream_v1), ("stream v2 (concatenated, 32 bytes)", stream_v2)):
        for hname, h in (("random.shuffle", shuffle_py), ("sort by random key", shuffle_sortkey)):
            part, rep, X = partition(s, h)
            results[(sname, hname)] = part
            print(f"\n== {sname}; {hname}: X = {X}")
            print("   per evaluation (G_e,total, A, B):", rep)
            print("   part A:", sorted(c for c, p in part.items() if p == "A"))
    keys = list(results)
    print("\n== do the guesses change the split?")
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            diff = sorted(c for c in results[keys[i]] if results[keys[i]][c] != results[keys[j]][c])
            print(f"  {keys[i]} vs {keys[j]}: {len(diff)} clusters differ")

    # ---- part 2: how often step 5 bites, made-up counts (G_e, number of X clusters touching e), |X| = 14
    print("\n== step 5: made-up scenario; |X| = 14 cross clusters, each touching two evaluations")
    rng = random.Random(1)
    scen = {"R1": 13, "R2": 19, "M1": 11, "C1": 14}
    # X clusters: 10 shared R2-C1, 2 shared M1-R2, 2 shared R1-C1 (C1 programs implementing R2 algorithms)
    xs = [("R2", "C1")] * 10 + [("M1", "R2")] * 2 + [("R1", "C1")] * 2
    reps = 20000
    worst = {e: 0 for e in scen}
    unequal = {e: 0 for e in scen}
    minpart = {e: [] for e in scen}
    for _ in range(reps):
        order = list(range(len(xs)))
        rng.shuffle(order)
        pa = {i: ("A" if r % 2 == 0 else "B") for r, i in enumerate(order)}
        for e, g in scen.items():
            xe = [i for i, t in enumerate(xs) if e in t]
            xa = sum(1 for i in xe if pa[i] == "A")
            xb = len(xe) - xa
            le = g - len(xe)
            target = g // 2
            a = xa + min(le, max(0, target - xa))
            b = g - a
            if a != target:
                unequal[e] += 1
            worst[e] = max(worst[e], abs(a - b))
            minpart[e].append(min(a, b))
    for e, g in scen.items():
        mp = sorted(minpart[e])
        print(f"  {e}: G={g}, X touching it={sum(1 for t in xs if e in t)}: P(parts not floor/ceil half)={unequal[e] / reps:.3f}; "
              f"largest |A-B|={worst[e]}; smallest part, 1st percentile={mp[int(0.01 * reps)]}, minimum={mp[0]}")


if __name__ == "__main__":
    main()
