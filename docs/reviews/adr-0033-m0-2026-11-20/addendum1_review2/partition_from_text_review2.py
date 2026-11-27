# ruff: noqa
"""Review 2 of ADR-0033 addendum 1, draft 2: section 4 (the cluster partition) implemented from the
addendum's text ALONE, before reading the drafter's partition_vector.py.

Standard library only. Imports nothing from studies/ and nothing from the drafter's scripts.

The made-up map below was reconstructed by the reviewer from partition_vector.out.txt only (its components,
its parts and its per-evaluation counts), because the .py that holds the map was not read first. In
particular C1.epsilon is taken as NOT REGISTERED and R1.epsilon as registered: the only assignment consistent
with the printed per-evaluation counts and with C1.epsilon not being listed as cross-evaluation.

Text used (draft 2, section 4 'The mechanics, complete' and 'The procedure'; section 3 item 1):
- stream(seed, l1..lk) = random.Random(int.from_bytes(sha256('|'.join([str(seed), l1..lk]).encode('utf-8'))
  .digest()[:8], 'big'))
- shuffle: sorted(identity strings), then stream.shuffle(list) once, fresh stream per call
- global cluster = connected component of the link graph over all written lineages; identity = min id
- X = clusters with registered lineages in >= 2 evaluations; L_e = clusters whose registered lineages are all in e
- X shuffled on (400004, 'cluster-partition', 'cross'): index 0 -> A, 1 -> B, ...
- for e in R1, R2, M1, C1: G_e = #global clusters with a registered lineage in e; a_e = #X clusters of e in A;
  L_e shuffled on (400004, 'cluster-partition', e); k_e = min(|L_e|, max(0, floor(G_e/2) - a_e)); first k_e -> A.
"""
import hashlib
import random
import sys


def stream(seed, *labels):
    s = "|".join([str(seed), *labels]).encode("utf-8")
    d = hashlib.sha256(s).digest()
    return random.Random(int.from_bytes(d[:8], "big")), s.decode(), d.hex(), int.from_bytes(d[:8], "big")


def shuffled(ids, seed, *labels):
    r = stream(seed, *labels)[0]
    lst = sorted(ids)
    r.shuffle(lst)
    return lst


def manual_shuffle(ids, seed, *labels):
    """The loop as the text spells it out: for i from n-1 down to 1, j = _randbelow(i+1), swap."""
    r = stream(seed, *labels)[0]
    lst = sorted(ids)
    for i in range(len(lst) - 1, 0, -1):
        j = r._randbelow(i + 1)
        lst[i], lst[j] = lst[j], lst[i]
    return lst


EVALS = ["R1", "R2", "M1", "C1"]


def components(nodes, links):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comps = {}
    for n in nodes:
        comps.setdefault(find(n), []).append(n)
    return {min(v): sorted(v) for v in comps.values()}


def partition(nodes, registered, links, seed=400004, variant_a_e="registered"):
    comps = components(nodes, links)
    ev = lambda lid: lid.split(".", 1)[0]
    reg_evals = {cid: sorted({ev(l) for l in mem if l in registered}) for cid, mem in comps.items()}
    any_evals = {cid: sorted({ev(l) for l in mem}) for cid, mem in comps.items()}
    assigned = [c for c in comps if reg_evals[c]]
    unassigned = [c for c in comps if not reg_evals[c]]
    X = [c for c in assigned if len(reg_evals[c]) >= 2]
    part = {}
    xs = shuffled(X, seed, "cluster-partition", "cross")
    for i, c in enumerate(xs):
        part[c] = "A" if i % 2 == 0 else "B"
    per_eval = {}
    for e in EVALS:
        G_e = sum(1 for c in assigned if e in reg_evals[c])
        if variant_a_e == "registered":
            a_e = sum(1 for c in X if e in reg_evals[c] and part[c] == "A")
        else:  # other reading: an X cluster 'of e' if it contains any lineage of e, registered or not
            a_e = sum(1 for c in X if e in any_evals[c] and part[c] == "A")
        L_e = [c for c in assigned if reg_evals[c] == [e]]
        ls = shuffled(L_e, seed, "cluster-partition", e)
        k = min(len(ls), max(0, G_e // 2 - a_e))
        for i, c in enumerate(ls):
            part[c] = "A" if i < k else "B"
        nA = sum(1 for c in assigned if e in reg_evals[c] and part[c] == "A")
        nB = sum(1 for c in assigned if e in reg_evals[c] and part[c] == "B")
        per_eval[e] = (G_e, nA, nB)
    return comps, xs, part, unassigned, per_eval


def main():
    print("python", sys.version.split()[0])
    print("== 1. derived integers")
    for lab in ["cross", *EVALS]:
        _, s, h, n = stream(400004, "cluster-partition", lab)
        print(f"  {s!r}: sha256 {h} -> {n}")
    print("== 2. shuffle of a..h on each stream (random.shuffle, and the hand-written loop of the text)")
    for lab in ["cross", *EVALS]:
        a = shuffled(list("hgfedcba"), 400004, "cluster-partition", lab)
        b = manual_shuffle(list("hgfedcba"), 400004, "cluster-partition", lab)
        assert a == b
        print(f"  {lab:>5}: {a}")
    ok = shuffled(list("abcdefgh"), 400004, "cluster-partition", "cross") == list("ecbhdfga")
    print("  text claims cross -> e,c,b,h,d,f,g,a:", "match" if ok else "MISMATCH")

    print("== 3. reconstructed made-up map (from partition_vector.out.txt only)")
    links = [("C1.alpha", "R2.alpha"), ("C1.beta", "R2.beta"), ("C1.epsilon", "R1.epsilon"),
             ("C1.gamma", "M1.beta"), ("M1.alpha", "R2.gamma"), ("R1.alpha", "R1.beta"), ("R1.delta", "R1.gamma")]
    singletons = ["C1.delta", "R2.epsilon", "M1.delta", "M1.gamma", "R1.zeta", "R2.delta"]
    nodes = sorted({x for l in links for x in l} | set(singletons))
    registered = set(nodes) - {"C1.epsilon"}
    print("  nodes:", nodes)
    print("  NOT REGISTERED (reconstruction):", sorted(set(nodes) - registered))
    expA = ['C1.delta', 'C1.epsilon', 'C1.gamma', 'M1.alpha', 'R1.alpha', 'R2.epsilon']
    expB = ['C1.alpha', 'C1.beta', 'M1.delta', 'M1.gamma', 'R1.delta', 'R1.zeta', 'R2.delta']
    for variant in ["registered", "any"]:
        comps, xs, part, unassigned, per_eval = partition(nodes, registered, links, variant_a_e=variant)
        print(f"  -- reading of 'X clusters of e': by {variant} lineages")
        for cid, mem in sorted(comps.items()):
            if len(mem) > 1:
                print(f"  component {cid}: {mem}")
        print("  cross-evaluation clusters in shuffled order:", xs)
        A = sorted(c for c, p in part.items() if p == "A")
        B = sorted(c for c, p in part.items() if p == "B")
        print("  part A:", A)
        print("  part B:", B)
        print("  unassigned:", unassigned)
        print("  per evaluation (G_e, A, B):", per_eval)
        assert not set(A) & set(B)
        same = A == expA and B == expB and xs == ['M1.alpha', 'C1.beta', 'C1.gamma', 'C1.alpha']
        print("  compared with partition_vector.out.txt:", "IDENTICAL" if same else "DIFFERENT")

    print("== 4. ambiguity probe: the two readings of 'X clusters of e' on a map where they differ")
    links2 = [("C1.k", "R1.k"), ("R1.k", "R2.k")]
    nodes2 = ["C1.k", "R1.k", "R2.k", "C1.a", "C1.b", "C1.c", "C1.d"]
    reg2 = set(nodes2) - {"C1.k"}
    for variant in ["registered", "any"]:
        _, xs, part, _, pe = partition(nodes2, reg2, links2, variant_a_e=variant)
        print(f"  {variant:>10}: X {xs} parts {dict(sorted(part.items()))} per-eval {pe}")


main()
