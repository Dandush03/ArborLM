# ruff: noqa
"""Test vectors for ADR-0033 addendum 1, draft 4: the cluster partition with borderline groups (section 4, steps 1 to 3
as rewritten after review 3, G4) and the capacity stage with independent counts (section 4A stage 4, review 3, G2).
Supersedes nothing: partition_vector_rev3.py stays, and its vectors V1 to V5 are reproduced here unchanged.

This is NOT the partition code of record and it reads NO cluster map. Every identity, link, borderline pair,
candidate flag and capacity figure below is made up; no identity names a written lineage. It exists so that a third
party who implements the text alone can check the result byte for byte. Standard library only; imports nothing from
studies/ and nothing from the other scripts. CPython 3.12.

What is new against partition_vector_rev3.py:
(1) the unit of steps 1 to 3 is the GROUP: a connected component of the graph whose nodes are global clusters and
    whose links are the borderline pairs between two different clusters. With no borderline pair every group is one
    cluster and the result is that of draft 3 (asserted below on V1 to V5).
(2) balance is counted in CLUSTERS, not in groups. Step 2: walking the shuffled list of cross-evaluation groups, a
    group goes to part B if B so far holds no more of the placed clusters than A, otherwise to A. Step 3: walking
    the shuffled list of the groups of one evaluation, a group goes to part A if the clusters of that evaluation in
    A would not then exceed floor(N_e / 2), otherwise to B.
(3) a cluster with no candidate lineage: reading 'pass' (drafted): it is a node of the group graph, so it passes a
    group on, and it takes no part. Reading 'ignore' (the other option): it is not a node, and a borderline pair
    that touches it does nothing. Both are computed on V6 and V7.
(4) vectors V6 (a group that spans cross-evaluation clusters, holds a cluster with no candidate lineage and two
    clusters of one evaluation), V7 (review 3's probe B2) and V8 (review 3's probe B3).
(5) the placement rules that were NOT drafted are computed beside the drafted one, to show where they differ:
    'groups' = draft 3's item 9 (N_e, a_e and k_e counted in groups, cross groups alternated by index);
    'prefix' = as drafted, except that step 3 stops at the first group that does not fit.
(6) part 4: stage 4 with counts that are independent per lineage (a lineage's count depends on that lineage, the
    level and the target only), the cluster's count as the union of its lineages' key sets, and the union condition
    read only on a cluster all of whose lineages meet their own demand in that round.

Run:  uv run --locked python -I -B docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/partition_vector_rev4.py
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


def components(nodes, links) -> dict[str, list[str]]:
    """Connected components. Identity: smallest node id."""
    parent = {x: x for x in nodes}

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
    for x in nodes:
        comp.setdefault(find(x), []).append(x)
    return {min(v): sorted(v) for v in comp.values()}


def partition(lineages: dict[str, bool], links, borderline=(), no_candidate: str = "pass", placement: str = "clusters"):
    """Section 4 of draft 4. lineages: id -> is a candidate (section 4A stage 2). links: same-procedure pairs of
    lineages. borderline: borderline pairs of lineages. Returns clusters, the part of every cluster with a candidate
    lineage, the per-evaluation counts IN CLUSTERS, the shuffled order of the cross-evaluation groups, the groups."""
    comps = components(lineages, links)  # global clusters, over ALL written lineages
    where = {x: cid for cid, mem in comps.items() for x in mem}
    cand_evals = {cid: sorted({ev(x) for x in mem if lineages[x]}) for cid, mem in comps.items()}
    has = {cid: bool(e) for cid, e in cand_evals.items()}

    pairs = sorted({tuple(sorted((where[a], where[b]))) for a, b in borderline if where[a] != where[b]})
    if no_candidate == "pass":
        raw = components(list(comps), pairs)
    else:  # 'ignore'
        raw = components([c for c in comps if has[c]], [(a, b) for a, b in pairs if has[a] and has[b]])
    groups: dict[str, list[str]] = {}
    for mem in raw.values():
        with_cand = sorted(c for c in mem if has[c])
        if with_cand:  # step 1: only groups with a candidate lineage are assigned
            groups[with_cand[0]] = with_cand  # identity: smallest identity among its clusters with a candidate
    g_evals = {g: sorted({e for c in cs for e in cand_evals[c]}) for g, cs in groups.items()}

    def w(g: str, e: str) -> int:
        return sum(1 for c in groups[g] if e in cand_evals[c])

    cross = [g for g in groups if len(g_evals[g]) >= 2]
    gpart: dict[str, str] = {}
    order_x = shuffled(cross, stream(SEED, "cluster-partition", "cross"))  # step 2
    in_a = in_b = 0
    for i, g in enumerate(order_x):
        if placement == "groups":
            to_b = i % 2 == 0
        else:
            to_b = in_b <= in_a
        gpart[g] = "B" if to_b else "A"
        if to_b:
            in_b += len(groups[g])
        else:
            in_a += len(groups[g])
    report = {}
    for e in EVALS:  # step 3
        local = [g for g in groups if g_evals[g] == [e]]
        order = shuffled(local, stream(SEED, "cluster-partition", e))
        if placement == "groups":
            n_units = sum(1 for g in groups if e in g_evals[g])
            a_units = sum(1 for g in cross if e in g_evals[g] and gpart[g] == "A")
            k = min(len(order), max(0, n_units // 2 - a_units))
            for i, g in enumerate(order):
                gpart[g] = "A" if i < k else "B"
        else:
            n_e = sum(1 for c in comps if e in cand_evals[c])
            a_e = sum(w(g, e) for g in cross if gpart[g] == "A")
            placed, stopped = 0, False
            for g in order:
                fits = a_e + placed + w(g, e) <= n_e // 2
                if placement == "prefix" and not fits:
                    stopped = True
                if fits and not stopped:
                    gpart[g] = "A"
                    placed += w(g, e)
                else:
                    gpart[g] = "B"
    part = {c: gpart[g] for g, cs in groups.items() for c in cs}
    for e in EVALS:
        cs = [c for c in comps if e in cand_evals[c]]
        a = sum(1 for c in cs if part[c] == "A")
        report[e] = (len(cs), a, len(cs) - a)
    return comps, part, report, order_x, groups


def _m(spec: str) -> dict[str, bool]:
    """'R1.a R1.b! ...' -> id -> candidate; a trailing '!' marks a lineage that is NOT a candidate."""
    return {t.rstrip("!"): not t.endswith("!") for t in spec.split()}


# ---------------- made-up maps ----------------
# V1 to V5: exactly those of partition_vector_rev3.py; no borderline pair
VECTORS = {
    "V1": (
        _m("R1.alpha R1.beta R1.gamma R1.delta! R1.epsilon R1.zeta R2.alpha R2.beta R2.gamma R2.delta R2.epsilon "
           "M1.alpha M1.beta M1.gamma M1.delta C1.alpha C1.beta C1.gamma C1.delta C1.epsilon!"),
        [("R1.alpha", "R1.beta"), ("C1.alpha", "R2.alpha"), ("C1.beta", "R2.beta"), ("M1.alpha", "R2.gamma"),
         ("C1.gamma", "M1.beta"), ("R1.gamma", "R1.delta"), ("C1.epsilon", "R1.epsilon")],
        [],
    ),
    "V2": (
        _m("R1.a R1.b R1.c R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c C1.a C1.b C1.c C1.d C1.e C1.f! C1.g!"),
        [("C1.a", "R2.a"), ("C1.b", "R2.b"), ("C1.c", "R2.c"), ("C1.d", "M1.a"), ("C1.e", "R1.a"), ("C1.f", "C1.g")],
        [],
    ),
    "V3": (
        _m("R1.e R2.e C1.e! R1.a M1.a C1.a C1.b C1.c C1.d"),
        [("R1.e", "R2.e"), ("C1.e", "R1.e"), ("R1.a", "M1.a")],
        [],
    ),
    "V4": (
        _m("R1.p R1.q R1.r R1.s R2.p! R2.q R2.r M1.p M1.q C1.p C1.q"),
        [("R1.p", "R2.p"), ("R1.q", "R2.p"), ("R2.q", "C1.p"), ("M1.p", "C1.q")],
        [],
    ),
    "V5": (
        _m("C1.a C1.b C1.c C1.d C1.e C1.f C1.g M1.b M1.z0 M1.z1 R1.d R1.e R1.g R1.z0 R2.a R2.c R2.f R2.z0"),
        [("C1.a", "R2.a"), ("C1.b", "M1.b"), ("C1.c", "R2.c"), ("C1.d", "R1.d"), ("C1.e", "R1.e"), ("C1.f", "R2.f"),
         ("C1.g", "R1.g")],
        [],
    ),
    # V6: a borderline group that spans cross-evaluation clusters (C1.a = {C1.a, R2.a}), holds a cluster with no
    # candidate lineage (C1.x) and two clusters of one evaluation (R1.a, R1.b); a second group inside R1 (R1.c, R1.d);
    # a third between a cross-evaluation cluster and a local one (M1.a = {M1.a, R2.b} with M1.b)
    "V6": (
        _m("R1.a R1.b R1.c R1.d R1.e R1.f R1.g R2.a R2.b R2.c R2.d R2.e M1.a M1.b M1.c M1.d "
           "C1.a C1.b C1.c C1.d C1.x!"),
        [("C1.a", "R2.a"), ("M1.a", "R2.b"), ("C1.b", "R2.c")],
        [("R1.a", "C1.x"), ("C1.x", "R1.b"), ("R1.b", "C1.a"), ("R1.c", "R1.d"), ("M1.b", "R2.b")],
    ),
    # V7: review 3's probe B2. R1.a ~ C1.x ~ R1.b borderline; C1.x has no candidate lineage
    "V7": (
        _m("R1.a R1.b R1.c R1.d C1.x!"),
        [],
        [("R1.a", "C1.x"), ("C1.x", "R1.b")],
    ),
    # V8: review 3's probe B3. Six R1 clusters, one borderline group of three
    "V8": (
        _m("R1.a R1.b R1.c R1.d R1.e R1.f"),
        [],
        [("R1.a", "R1.b"), ("R1.b", "R1.c")],
    ),
}

# part A and the per-evaluation counts of partition_vector_rev3.out.txt (SHA-256 a21e62c5...939e), copied by hand
REV3 = {
    "V1": (["C1.alpha", "C1.beta", "C1.epsilon", "M1.delta", "M1.gamma", "R1.alpha"],
           {"R1": (4, 2, 2), "R2": (5, 2, 3), "M1": (4, 2, 2), "C1": (4, 2, 2)}),
    "V2": (["C1.a", "C1.b", "M1.c", "R1.b"], {"R1": (3, 1, 2), "R2": (5, 2, 3), "M1": (3, 1, 2), "C1": (5, 2, 3)}),
    "V3": (["C1.c", "C1.d", "C1.e"], {"R1": (2, 1, 1), "R2": (1, 1, 0), "M1": (1, 0, 1), "C1": (4, 2, 2)}),
    "V4": (["C1.p", "M1.q", "R1.s"], {"R1": (3, 1, 2), "R2": (2, 1, 1), "M1": (2, 1, 1), "C1": (2, 1, 1)}),
    "V5": (["C1.a", "C1.c", "C1.f", "M1.z1", "R1.z0"],
           {"R1": (4, 1, 3), "R2": (4, 3, 1), "M1": (3, 1, 2), "C1": (7, 3, 4)}),
}


def show(name: str, no_candidate: str = "pass", placement: str = "clusters", head: str = "") -> None:
    lineages, links, borderline = VECTORS[name]
    comps, part, report, order_x, groups = partition(lineages, links, borderline, no_candidate, placement)
    print(f"-- {name}{head}")
    if placement == "clusters" and no_candidate == "pass":
        print("   lineages (! = not a candidate):", " ".join(x + ("" if c else "!") for x, c in sorted(lineages.items())))
        for cid, mem in sorted(comps.items()):
            if len(mem) > 1:
                print(f"   cluster {cid}: {mem}")
        if borderline:
            print("   borderline pairs:", borderline)
    multi = {g: cs for g, cs in sorted(groups.items()) if len(cs) > 1}
    if borderline:
        print("   groups of more than one cluster (clusters with a candidate lineage only):", multi if multi else "none")
    print("   cross-evaluation groups in shuffled order:", order_x)
    print("   part A:", sorted(c for c, p in part.items() if p == "A"))
    print("   part B:", sorted(c for c, p in part.items() if p == "B"))
    print("   no part (no candidate lineage):", sorted(c for c in comps if c not in part))
    print("   per evaluation (N_e, clusters in A, clusters in B):", report)
    split = sorted(tuple(sorted((a, b))) for g, cs in groups.items() for a in cs for b in cs if a < b and part[a] != part[b])
    assert not split, "a group is in two parts"


def demand(g: int) -> int:
    return 10 * (math.ceil(DEV / g) + math.ceil(POOL / g) + TUNING)


def demand_lin(g: int, k: int) -> int:
    return 10 * (math.ceil(math.ceil(DEV / g) / k) + math.ceil(math.ceil(POOL / g) / k) + math.ceil(TUNING / k))


def stage4(members: dict[str, list[str]], cap: dict[str, int], shared: dict[tuple[str, str], int]):
    """Section 4A stage 4 for ONE evaluation part, weakest level only. members: cluster -> its candidate lineages of
    this evaluation. cap: lineage -> made-up number of distinct keys it yields inside any attempt budget, so its
    count at a target T is min(cap, T): independent of every other lineage. shared: pair of sibling lineages ->
    made-up number of keys their two key sets have in common. One round: (i) a lineage fails if its count is below
    D_lin(G, k); (ii) on a cluster all of whose lineages passed (i), the union of the key sets must reach D(G), or
    all its lineages fail. Every failing lineage is removed at once."""
    alive = {c: list(v) for c, v in members.items() if v}
    rounds = []
    while True:
        g = len(alive)
        if g == 0:
            rounds.append((0, [], []))
            return alive, rounds
        drop_lin, drop_union = [], []
        for c, v in alive.items():
            t = demand_lin(g, len(v))
            failing = [x for x in v if min(cap[x], t) < t]
            if failing:
                drop_lin += failing
                continue
            union = len(v) * t - sum(n for (a, b), n in shared.items() if a in v and b in v)
            if union < demand(g):
                drop_union += v
        rounds.append((g, sorted(drop_lin), sorted(drop_union)))
        if not drop_lin and not drop_union:
            return alive, rounds
        gone = set(drop_lin) | set(drop_union)
        alive = {c: [x for x in v if x not in gone] for c, v in alive.items()}
        alive = {c: v for c, v in alive.items() if v}


CAP_V1 = {  # the made-up capacities of partition_vector_rev3.py, unchanged
    "R1.alpha": 70_000, "R1.beta": 9_000, "R1.gamma": 300_000, "R1.epsilon": 300_000, "R1.zeta": 300_000,
    "R2.alpha": 300_000, "R2.beta": 300_000, "R2.gamma": 90_000, "R2.delta": 50_000, "R2.epsilon": 300_000,
    "M1.alpha": 300_000, "M1.beta": 300_000, "M1.gamma": 300_000, "M1.delta": 300_000,
    "C1.alpha": 300_000, "C1.beta": 300_000, "C1.gamma": 130_000, "C1.delta": 100,
}
REV3_REGISTERED = {  # registered lineages per evaluation part in partition_vector_rev3.out.txt, part 4
    ("R1", "A"): ["R1.epsilon"], ("R1", "B"): ["R1.gamma", "R1.zeta"], ("R2", "A"): ["R2.alpha", "R2.beta"],
    ("R2", "B"): ["R2.epsilon"], ("M1", "A"): ["M1.delta", "M1.gamma"], ("M1", "B"): ["M1.alpha", "M1.beta"],
    ("C1", "A"): ["C1.alpha", "C1.beta"], ("C1", "B"): [],
}


def trail(rounds) -> str:
    out = []
    for g, dl, du in rounds:
        bits = []
        if dl:
            bits.append(f"below D_lin: {dl}")
        if du:
            bits.append(f"union below D({g}) = {demand(g):,}: {du}")
        out.append(f"G={g}: " + ("; ".join(bits) if bits else "nothing fails"))
    return " | ".join(out)


def main() -> None:
    print("python", sys.version.split()[0])
    print("== 1. derived integers (first 8 bytes of SHA-256, big-endian); unchanged from drafts 2 and 3")
    for labels in (("cluster-partition", "cross"), *[("cluster-partition", e) for e in EVALS]):
        print(f"  {'|'.join([str(SEED), *labels])!r}  ->  {derive(SEED, *labels)}")
    print("== 2. V1 to V5 (no borderline pair): the draft-4 rule against partition_vector_rev3.out.txt")
    for name, (exp_a, exp_report) in REV3.items():
        lineages, links, borderline = VECTORS[name]
        for placement in ("clusters", "prefix", "groups"):
            for nc in ("pass", "ignore"):
                _, part, report, _, _ = partition(lineages, links, borderline, nc, placement)
                assert sorted(c for c, p in part.items() if p == "A") == exp_a, (name, placement, nc)
                assert report == exp_report, (name, placement, nc)
        print(f"  {name}: part A {exp_a}; per evaluation {exp_report}: identical under every reading computed here")
    print("== 3. vectors with borderline pairs. Drafted: a cluster with no candidate lineage passes a group on and")
    print("      takes no part ('pass'); balance counted in clusters ('clusters')")
    for name in ("V6", "V7", "V8"):
        show(name)
    print("== 3b. the other option for a cluster with no candidate lineage: it is not a node of the group graph ('ignore')")
    for name in ("V6", "V7"):
        show(name, no_candidate="ignore", head="  [ignore]")
    print("== 3c. placement rules NOT drafted, for comparison, with 'pass'")
    for name in ("V6", "V7", "V8"):
        show(name, placement="groups", head="  [draft 3's item 9: counted in groups]")
    for name in ("V6", "V8"):
        show(name, placement="prefix", head="  [step 3 stops at the first group that does not fit]")
    print("== 3d. review 3's probe B2 under draft 3's counting in groups: R1 (N, A, B) with 'ignore' / 'pass'")
    lineages, links, borderline = VECTORS["V7"]
    r_i = partition(lineages, links, borderline, "ignore", "groups")[2]["R1"]
    r_p = partition(lineages, links, borderline, "pass", "groups")[2]["R1"]
    print(f"   {r_i} / {r_p}   (the reviewer's 2/2 against 1/3)")
    print("== 4. stage 4 with independent counts, made-up capacities, weakest level only")
    print("   4a. V1 with the capacities of partition_vector_rev3.py and no shared key")
    lineages, links, borderline = VECTORS["V1"]
    comps, part, _, _, _ = partition(lineages, links, borderline)
    where = {x: cid for cid, mem in comps.items() for x in mem}
    for e in EVALS:
        for p in ("A", "B"):
            members: dict[str, list[str]] = {}
            for x, c in sorted(lineages.items()):
                if c and ev(x) == e and part[where[x]] == p:
                    members.setdefault(where[x], []).append(x)
            alive, rounds = stage4(members, CAP_V1, {})
            reg = sorted(x for v in alive.values() for x in v)
            assert reg == REV3_REGISTERED[(e, p)], (e, p, reg)
            print(f"   {e} part {p}: candidate clusters {len(members)} -> registered G = {len(alive)}   [{trail(rounds)}]")
    print("   registered lineages identical to partition_vector_rev3.out.txt part 4 in all eight parts (asserted)")
    print("   4b. one made-up part: a weak sibling does not take a strong lineage with it; one shared key does")
    members = {"c1": ["c1.x", "c1.y"], "c2": ["c2.x", "c2.y"], "c3": ["c3.x"], "c4": ["c4.x"], "c5": ["c5.x"]}
    cap = {"c1.x": 300_000, "c1.y": 9_000, "c2.x": 300_000, "c2.y": 300_000, "c3.x": 300_000, "c4.x": 300_000,
           "c5.x": 300_000}
    alive, rounds = stage4(members, cap, {("c2.x", "c2.y"): 1})
    print(f"      D(5) = {demand(5):,}; D_lin(5, 2) = {demand_lin(5, 2):,}; 2 x D_lin(5, 2) - D(5) = {2 * demand_lin(5, 2) - demand(5)}")
    print(f"      clusters 5 -> registered G = {len(alive)}   [{trail(rounds)}]")
    print(f"      registered: { {c: v for c, v in sorted(alive.items())} }")
    alive2, rounds2 = stage4(members, cap, {})
    print(f"      the same with no shared key: registered G = {len(alive2)}   [{trail(rounds2)}]")
    print(f"      registered: { {c: v for c, v in sorted(alive2.items())} }")


if __name__ == "__main__":
    main()
