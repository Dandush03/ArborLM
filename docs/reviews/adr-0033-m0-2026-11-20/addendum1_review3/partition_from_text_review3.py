"""Review 3 of ADR-0033 addendum 1, draft 3: section 4 (and 4 item 9) implemented from the text alone.

Written before reading partition_vector_rev3.py. Standard library only. Imports nothing from studies/ or
from any drafter or reviewer script. The made-up maps V1..V5 are rebuilt from partition_vector_rev3.out.txt
(lineage list, '!' = not a candidate, the listed components; every other lineage is a singleton).
"""

import hashlib
import random
import sys

SEED = 400004
EVALS = ("R1", "R2", "M1", "C1")


def derive(seed, *labels):
    return int.from_bytes(hashlib.sha256("|".join([str(seed), *labels]).encode("utf-8")).digest()[:8], "big")


def stream(seed, *labels):
    return random.Random(derive(seed, *labels))


def shuffle_text(ids, *labels):
    """Section 4: sort by code point, then the loop of Lib/random.py spelled out; asserted equal to shuffle."""
    xs = sorted(ids)
    r = stream(SEED, *labels)
    for i in reversed(range(1, len(xs))):
        j = r._randbelow(i + 1)
        xs[i], xs[j] = xs[j], xs[i]
    ys = sorted(ids)
    stream(SEED, *labels).shuffle(ys)
    assert xs == ys
    return xs


def components(nodes, links):
    parent = {n: n for n in nodes}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    comp = {}
    for n in nodes:
        comp.setdefault(find(n), []).append(n)
    return {min(v): sorted(v) for v in comp.values()}


def ev(lid):
    return lid.split(".", 1)[0]


def partition(lineages, noncand, comps_listed, reading="candidate", borderline=(), group_through_noncand=False):
    """Steps 1-3 of section 4. reading='any' is the rejected reading of a_e (any lineage in e).

    borderline: pairs of lineage ids judged borderline; if given, section 4 item 9 (groups) is applied.
    group_through_noncand: whether a cluster with no candidate lineage transmits a borderline group
    (item 9 does not say).
    """
    links = []
    for members in comps_listed:
        for m in members[1:]:
            links.append((members[0], m))
    comp = components(lineages, links)  # identity -> members
    of = {m: cid for cid, ms in comp.items() for m in ms}
    cand = [x for x in lineages if x not in noncand]
    cand_evals = {cid: sorted({ev(m) for m in ms if m in cand}) for cid, ms in comp.items()}
    anyl_evals = {cid: sorted({ev(m) for m in ms}) for cid, ms in comp.items()}
    assigned = [c for c in comp if cand_evals[c]]
    unassigned = sorted(c for c in comp if not cand_evals[c])

    if borderline:
        blinks = [(of[a], of[b]) for a, b in borderline if of[a] != of[b]]
        if group_through_noncand:
            g_all = components(list(comp), blinks)
            groups = {}
            for _, cs in g_all.items():
                cs2 = [c for c in cs if c in assigned]
                if cs2:
                    groups[min(cs2)] = sorted(cs2)
        else:
            blinks = [(a, b) for a, b in blinks if a in assigned and b in assigned]
            groups = components(assigned, blinks)
    else:
        groups = {c: [c] for c in assigned}
    unit_cand_evals = {g: sorted({e for c in cs for e in cand_evals[c]}) for g, cs in groups.items()}
    unit_any_evals = {g: sorted({e for c in cs for e in anyl_evals[c]}) for g, cs in groups.items()}

    X = [g for g in groups if len(unit_cand_evals[g]) >= 2]
    part = {}
    xo = shuffle_text(X, "cluster-partition", "cross") if X else []
    for i, g in enumerate(xo):
        part[g] = "B" if i % 2 == 0 else "A"
    for e in EVALS:
        N = sum(1 for g in groups if e in unit_cand_evals[g])
        if reading == "candidate":
            a = sum(1 for g in X if part[g] == "A" and e in unit_cand_evals[g])
        else:
            a = sum(1 for g in X if part[g] == "A" and e in unit_any_evals[g])
        L = [g for g in groups if g not in X and unit_cand_evals[g] == [e]]
        lo = shuffle_text(L, "cluster-partition", e) if L else []
        k = min(len(lo), max(0, N // 2 - a))
        for i, g in enumerate(lo):
            part[g] = "A" if i < k else "B"
    cpart = {c: part[g] for g, cs in groups.items() for c in cs}
    per = {}
    for e in EVALS:
        cs = [c for c in assigned if e in cand_evals[c]]
        per[e] = (len(cs), sum(cpart[c] == "A" for c in cs), sum(cpart[c] == "B" for c in cs))
    return cpart, per, xo, unassigned, groups


V = {
    "V1": (
        "C1.alpha C1.beta C1.delta C1.epsilon! C1.gamma M1.alpha M1.beta M1.delta M1.gamma R1.alpha R1.beta R1.delta! R1.epsilon R1.gamma R1.zeta R2.alpha R2.beta R2.delta R2.epsilon R2.gamma",
        [["C1.alpha", "R2.alpha"], ["C1.beta", "R2.beta"], ["C1.epsilon", "R1.epsilon"], ["C1.gamma", "M1.beta"],
         ["M1.alpha", "R2.gamma"], ["R1.alpha", "R1.beta"], ["R1.delta", "R1.gamma"]],
    ),
    "V2": (
        "C1.a C1.b C1.c C1.d C1.e C1.f! C1.g! M1.a M1.b M1.c R1.a R1.b R1.c R2.a R2.b R2.c R2.d R2.e",
        [["C1.a", "R2.a"], ["C1.b", "R2.b"], ["C1.c", "R2.c"], ["C1.d", "M1.a"], ["C1.e", "R1.a"], ["C1.f", "C1.g"]],
    ),
    "V3": (
        "C1.a C1.b C1.c C1.d C1.e! M1.a R1.a R1.e R2.e",
        [["C1.e", "R1.e", "R2.e"], ["M1.a", "R1.a"]],
    ),
    "V4": (
        "C1.p C1.q M1.p M1.q R1.p R1.q R1.r R1.s R2.p! R2.q R2.r",
        [["C1.p", "R2.q"], ["C1.q", "M1.p"], ["R1.p", "R1.q", "R2.p"]],
    ),
    "V5": (
        "C1.a C1.b C1.c C1.d C1.e C1.f C1.g M1.b M1.z0 M1.z1 R1.d R1.e R1.g R1.z0 R2.a R2.c R2.f R2.z0",
        [["C1.a", "R2.a"], ["C1.b", "M1.b"], ["C1.c", "R2.c"], ["C1.d", "R1.d"], ["C1.e", "R1.e"], ["C1.f", "R2.f"],
         ["C1.g", "R1.g"]],
    ),
}


def parse(spec):
    toks = spec.split()
    lins = [t.rstrip("!") for t in toks]
    non = {t.rstrip("!") for t in toks if t.endswith("!")}
    return lins, non


def show(name, lins, non, comps, **kw):
    cpart, per, xo, un, groups = partition(lins, non, comps, **kw)
    print(f"-- {name}")
    if any(len(v) > 1 for v in groups.values()):
        print("   groups:", {g: cs for g, cs in groups.items() if len(cs) > 1})
    print("   X shuffled (index 0 -> B):", xo)
    print("   part A:", sorted(c for c, p in cpart.items() if p == "A"))
    print("   part B:", sorted(c for c, p in cpart.items() if p == "B"))
    print("   no part:", un)
    print("   per evaluation (N_e, A, B), in clusters:", per)
    return cpart, per


print("python", sys.version.split()[0])
print("== 1. derived integers")
for lab in ("cross", *EVALS):
    print(f"  '400004|cluster-partition|{lab}' -> {derive(SEED, 'cluster-partition', lab)}")
print("== 2. shuffle of a..h")
for lab in ("cross", *EVALS):
    print(f"  {lab:>5}: {shuffle_text(list('abcdefgh'), 'cluster-partition', lab)}")
print("== 3. section 4 on V1..V5, from the text")
for name, (spec, comps) in V.items():
    lins, non = parse(spec)
    show(name, lins, non, comps)
print("== 3b. V3 under the rejected reading of a_e (any lineage in e)")
lins, non = parse(V["V3"][0])
show("V3-any", lins, non, V["V3"][1], reading="any")

print("== 4. item 9 (borderline pairs kept in one part; decided 2026-11-26), made-up probes")
lins, non = parse(V["V1"][0])
show("B1 = V1 + borderline {R1.alpha~R1.zeta, C1.delta~M1.delta}", lins, non, V["V1"][1],
     borderline=[("R1.alpha", "R1.zeta"), ("C1.delta", "M1.delta")])
print("   probe B2: R1.a ~ C1.x borderline and C1.x ~ R1.b borderline; C1.x has no candidate lineage")
lins = ["R1.a", "R1.b", "R1.c", "R1.d", "C1.x"]
non = {"C1.x"}
bl = [("R1.a", "C1.x"), ("C1.x", "R1.b")]
show("B2 non-candidate cluster does not transmit the group", lins, non, [], borderline=bl, group_through_noncand=False)
show("B2 non-candidate cluster transmits the group", lins, non, [], borderline=bl, group_through_noncand=True)
print("   probe B3: groups are counted as one unit in N_e, so clusters per part can be unbalanced")
lins = ["R1.a", "R1.b", "R1.c", "R1.d", "R1.e", "R1.f"]
show("B3 without item 9", lins, set(), [])
show("B3 with R1.a~R1.b~R1.c borderline", lins, set(), [], borderline=[("R1.a", "R1.b"), ("R1.b", "R1.c")])
