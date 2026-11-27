# ruff: noqa
"""Test vectors for ADR-0033 addendum 1, draft 3: the cluster partition (section 4) and the order of record with the
capacity fixed point (section 4A). Supersedes partition_vector.py of draft 2, whose step 2 started with part A.

This is NOT the partition code of record and it reads NO cluster map. Every identity, link, candidate flag and
capacity figure below is made up. It exists so that a third party who implements the text alone can check the result
byte for byte. Standard library only; imports nothing from studies/. CPython 3.12.

Changes from partition_vector.py: (1) step 2 gives index 0 to part B (the larger half is held out, as in step 3);
(2) clusters are assigned on CANDIDATE lineages (section 4A), not on registered ones; (3) a_e counts X clusters with
a candidate lineage in e; (4) vectors V2 to V5 exercise the cases the first vector did not (review 2, F19);
(5) part 4 runs the capacity fixed point of section 4A after the partition, which is not recomputed.

Run:  uv run --locked python -I -B docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/partition_vector_rev3.py
"""

from __future__ import annotations

import hashlib
import math
import random
import sys

SEED = 400004
EVALS = ("R1", "R2", "M1", "C1")
DEV, POOL, TUNING = 4_000, 20_000, 100


def derive(seed: int, *labels: str) -> int:
    text = "|".join([str(seed), *labels])
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def stream(seed: int, *labels: str) -> random.Random:
    return random.Random(derive(seed, *labels))


def shuffled(ids, rng: random.Random) -> list[str]:
    out = sorted(ids)  # Python str order = Unicode code-point order
    rng.shuffle(out)
    return out


def ev(lineage_id: str) -> str:
    return lineage_id.split(".", 1)[0]


def components(lineages: dict[str, bool], links: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Connected components over ALL written lineages, candidate or not. Identity: smallest id."""
    parent = {x: x for x in lineages}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    comp: dict[str, list[str]] = {}
    for x in lineages:
        comp.setdefault(find(x), []).append(x)
    return {min(v): sorted(v) for v in comp.values()}


def partition(lineages: dict[str, bool], links: list[tuple[str, str]], a_reading: str = "candidate"):
    """Section 4. lineages: id -> is a candidate (section 4A, stage 3). a_reading='any' is the reading the text
    REJECTS (review 2, F6); it is here only to show that the two differ on vector V3."""
    comps = components(lineages, links)
    cand_evals = {cid: sorted({ev(x) for x in mem if lineages[x]}) for cid, mem in comps.items()}
    any_evals = {cid: sorted({ev(x) for x in mem}) for cid, mem in comps.items()}
    assigned = {cid: e for cid, e in cand_evals.items() if e}  # step 1
    cross = [cid for cid, e in assigned.items() if len(e) >= 2]
    part: dict[str, str] = {}
    order_x = shuffled(cross, stream(SEED, "cluster-partition", "cross"))  # step 2: index 0 -> B
    for i, cid in enumerate(order_x):
        part[cid] = "B" if i % 2 == 0 else "A"
    report, flags = {}, set()
    if len(cross) % 2:
        flags.add("odd |X|")
    for e in EVALS:  # step 3
        total = [cid for cid, es in assigned.items() if e in es]
        n_e = len(total)
        of_e = (lambda cid: e in cand_evals[cid]) if a_reading == "candidate" else (lambda cid: e in any_evals[cid])
        a_e = sum(1 for cid in cross if of_e(cid) and part[cid] == "A")
        local = [cid for cid in total if assigned[cid] == [e]]
        want = max(0, n_e // 2 - a_e)
        k_e = min(len(local), want)
        if want > len(local):
            flags.add(f"clamp k_e = |L_e| in {e}")
        if a_e > n_e // 2:
            flags.add(f"a_e > floor(N_e/2) in {e}")
        for i, cid in enumerate(shuffled(local, stream(SEED, "cluster-partition", e))):
            part[cid] = "A" if i < k_e else "B"
        a = sum(1 for cid in total if part[cid] == "A")
        report[e] = (n_e, a, n_e - a)
    if any(not e for e in cand_evals.values()):
        flags.add("a cluster with no candidate lineage (no part)")
    for cid, mem in comps.items():
        per = {}
        for x in mem:
            if lineages[x]:
                per[ev(x)] = per.get(ev(x), 0) + 1
        if any(v >= 2 for v in per.values()) and any(not lineages[x] and ev(x) not in per for x in mem):
            flags.add("a non-candidate lineage of another evaluation sits in a cluster with two candidates of one evaluation")
    return comps, part, report, order_x, sorted(flags)


def demand_lin(g: int, k: int) -> int:
    return 10 * (math.ceil(math.ceil(DEV / g) / k) + math.ceil(math.ceil(POOL / g) / k) + math.ceil(TUNING / k))


def capacity_fixed_point(members: dict[str, list[str]], cap: dict[str, int]):
    """Section 4A stage 5 for ONE evaluation part. members: cluster -> its candidate lineages of this evaluation.
    cap: lineage -> made-up count of distinct items at its weakest level. Simplification of this vector only: the
    cluster-level condition is taken as met when every surviving lineage meets D_lin."""
    alive = {c: list(v) for c, v in members.items() if v}
    rounds = []
    while True:
        g = len(alive)
        if g == 0:
            rounds.append((0, []))
            return alive, rounds
        drop = [x for c, v in alive.items() for x in v if cap[x] < demand_lin(g, len(v))]
        rounds.append((g, sorted(drop)))
        if not drop:
            return alive, rounds
        alive = {c: [x for x in v if x not in drop] for c, v in alive.items()}
        alive = {c: v for c, v in alive.items() if v}


# ---------------- made-up maps ----------------
def _m(spec: str) -> dict[str, bool]:
    """'R1.a R1.b! ...' -> id -> candidate; a trailing '!' marks a lineage that is NOT a candidate."""
    return {t.rstrip("!"): not t.endswith("!") for t in spec.split()}


VECTORS = {
    # V1: the made-up map of partition_vector.py (draft 2), unchanged, now under the draft-3 rules
    "V1": (
        _m("R1.alpha R1.beta R1.gamma R1.delta! R1.epsilon R1.zeta R2.alpha R2.beta R2.gamma R2.delta R2.epsilon "
           "M1.alpha M1.beta M1.gamma M1.delta C1.alpha C1.beta C1.gamma C1.delta C1.epsilon!"),
        [("R1.alpha", "R1.beta"), ("C1.alpha", "R2.alpha"), ("C1.beta", "R2.beta"), ("M1.alpha", "R2.gamma"),
         ("C1.gamma", "M1.beta"), ("R1.gamma", "R1.delta"), ("C1.epsilon", "R1.epsilon")],
    ),
    # V2: odd |X|; C1 almost wholly cross-evaluation
    "V2": (
        _m("R1.a R1.b R1.c R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c C1.a C1.b C1.c C1.d C1.e C1.f! C1.g!"),
        [("C1.a", "R2.a"), ("C1.b", "R2.b"), ("C1.c", "R2.c"), ("C1.d", "M1.a"), ("C1.e", "R1.a"), ("C1.f", "C1.g")],
    ),
    # V3: review 2's F6 case: an X cluster (R1, R2 candidates) with a NON-candidate C1 lineage, landing in part A
    "V3": (
        _m("R1.e R2.e C1.e! R1.a M1.a C1.a C1.b C1.c C1.d"),
        [("R1.e", "R2.e"), ("C1.e", "R1.e"), ("R1.a", "M1.a")],
    ),
    # V4: a non-candidate lineage of another evaluation joins two candidates of one evaluation (review 2, F18)
    "V4": (
        _m("R1.p R1.q R1.r R1.s R2.p! R2.q R2.r M1.p M1.q C1.p C1.q"),
        [("R1.p", "R2.p"), ("R1.q", "R2.p"), ("R2.q", "C1.p"), ("M1.p", "C1.q")],
    ),
    # V5: the clamp k_e = |L_e| (R1) and a_e > floor(N_e/2) (R2): unequal parts that nothing repairs (step 5)
    "V5": (
        _m("C1.a C1.b C1.c C1.d C1.e C1.f C1.g M1.b M1.z0 M1.z1 R1.d R1.e R1.g R1.z0 R2.a R2.c R2.f R2.z0"),
        [("C1.a", "R2.a"), ("C1.b", "M1.b"), ("C1.c", "R2.c"), ("C1.d", "R1.d"), ("C1.e", "R1.e"), ("C1.f", "R2.f"),
         ("C1.g", "R1.g")],
    ),
}

# made-up capacities (distinct items at the weakest level) for part 4, on vector V1
CAP_V1 = {
    "R1.alpha": 70_000, "R1.beta": 9_000, "R1.gamma": 300_000, "R1.epsilon": 300_000, "R1.zeta": 300_000,
    "R2.alpha": 300_000, "R2.beta": 300_000, "R2.gamma": 90_000, "R2.delta": 50_000, "R2.epsilon": 300_000,
    "M1.alpha": 300_000, "M1.beta": 300_000, "M1.gamma": 300_000, "M1.delta": 300_000,
    "C1.alpha": 300_000, "C1.beta": 300_000, "C1.gamma": 130_000, "C1.delta": 100,
}


def show(name: str) -> None:
    lineages, links = VECTORS[name]
    comps, part, report, order_x, flags = partition(lineages, links)
    print(f"-- {name}")
    print("   lineages (! = not a candidate):", " ".join(x + ("" if c else "!") for x, c in sorted(lineages.items())))
    for cid, mem in sorted(comps.items()):
        if len(mem) > 1:
            print(f"   component {cid}: {mem}")
    print("   cross-evaluation clusters in shuffled order (index 0 -> B):", order_x)
    print("   part A:", sorted(c for c, p in part.items() if p == "A"))
    print("   part B:", sorted(c for c, p in part.items() if p == "B"))
    print("   no part (no candidate lineage):", sorted(c for c in comps if c not in part))
    print("   per evaluation (N_e, clusters in A, clusters in B):", report)
    print("   cases exercised:", flags if flags else "none")


def main() -> None:
    print("python", sys.version.split()[0])
    print("== 1. derived integers (first 8 bytes of SHA-256, big-endian); unchanged from draft 2")
    for labels in (("cluster-partition", "cross"), *[("cluster-partition", e) for e in EVALS]):
        print(f"  {'|'.join([str(SEED), *labels])!r}  ->  {derive(SEED, *labels)}")
    print("== 2. shuffle of ['a'..'h'] (sorted first) on each stream; unchanged from draft 2")
    for labels in (("cluster-partition", "cross"), *[("cluster-partition", e) for e in EVALS]):
        print(f"  {labels[1]:>5}: {shuffled(list('hgfedcba'), stream(SEED, *labels))}")
    print("== 3. section 4 on made-up maps")
    for name in VECTORS:
        show(name)
    lineages, links = VECTORS["V3"]
    _, p_c, r_c, _, _ = partition(lineages, links, "candidate")
    _, p_a, r_a, _, _ = partition(lineages, links, "any")
    print("-- V3 under the reading the text rejects ('any lineage in e'): C1", r_a["C1"], "against", r_c["C1"],
          "under the text; clusters whose part differs:", sorted(c for c in p_c if p_c[c] != p_a[c]))
    print("== 4. section 4A on V1 with made-up capacities: the partition above is kept; capacity per evaluation part")
    lineages, links = VECTORS["V1"]
    comps, part, report, _, _ = partition(lineages, links)
    where = {x: cid for cid, mem in comps.items() for x in mem}
    for e in EVALS:
        for p in ("A", "B"):
            members: dict[str, list[str]] = {}
            for x, c in sorted(lineages.items()):
                if c and ev(x) == e and part[where[x]] == p:
                    members.setdefault(where[x], []).append(x)
            alive, rounds = capacity_fixed_point(members, CAP_V1)
            trail = "; ".join(f"G={g}: drop {d if d else 'nothing'}" for g, d in rounds)
            print(f"   {e} part {p}: candidate clusters {len(members)} -> registered G = {len(alive)}   [{trail}]")
            print(f"      registered: { {c: v for c, v in sorted(alive.items())} }")
    print("   the part of every cluster is as in part 3: nothing is re-shuffled after a capacity drop")


if __name__ == "__main__":
    main()
