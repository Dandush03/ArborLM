# ruff: noqa
"""Cross-evaluation map (M0), check of step 4: enumerate EVERY subset of the cross-evaluation clusters X that the addendum's deal
(A, B, A, B, ... on a shuffled list) can send to part A (all subsets of size ceil(|X|/2); each arises from the same number of
permutations), apply step 3 of the addendum's procedure per evaluation, and report the joint min/max of the part sizes and the
fraction of shuffles in which some evaluation's parts differ from the floor/ceil half split. No seed, no shuffle, no real split.
Independent of s04's closed-form a_e range (same component code is NOT reused: components are recomputed here).

Run: python s05_bounds_by_enumeration.py cross_evaluation_procedures_proposed.json [--drop-file FILE]
"""
import itertools, json, math, sys

EVALS = ("R1", "R2", "M1", "C1")


def comps(clusters, pairs, grades):
    adj = {k: set() for k in clusters}
    for p in pairs:
        a, b = tuple(p["a"]), tuple(p["b"])
        if p["grade"] in grades and a in adj and b in adj:
            adj[a].add(b); adj[b].add(a)
    seen, out = set(), []
    for k in sorted(adj):
        if k in seen:
            continue
        stack, comp = [k], []
        seen.add(k)
        while stack:
            u = stack.pop(); comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); stack.append(v)
        out.append(comp)
    return out


def main():
    doc = json.load(open(sys.argv[1]))
    drops = set(doc.get("dropped_since_fix4", []))
    if len(sys.argv) > 3 and sys.argv[2] == "--drop-file":
        drops |= {l.strip() for l in open(sys.argv[3]) if l.strip() and not l.startswith("#")}
    clusters = {}
    for c in doc["strict_clusters"]:
        left = [m for m in c["survivors"] if m not in drops]
        if left:
            clusters[(c["eval"], c["cluster"])] = left
    for label, grades in (("1 STRONG", {"STRONG"}), ("2 STRONG+BORDERLINE", {"STRONG", "BORDERLINE"})):
        cs = comps(clusters, doc["pairs"], grades)
        evs = [sorted({e for e, _ in c}) for c in cs]
        X = [i for i, e in enumerate(evs) if len(e) >= 2]
        G = {e: sum(1 for x in evs if e in x) for e in EVALS}
        L = {e: sum(1 for x in evs if e in x and len(x) == 1) for e in EVALS}
        nA = math.ceil(len(X) / 2)
        rng = {e: [10**9, -1] for e in EVALS}
        off = {e: 0 for e in EVALS}
        any_off = 0
        n = 0
        for Aset in itertools.combinations(X, nA):
            n += 1
            bad = False
            for e in EVALS:
                a = sum(1 for i in Aset if e in evs[i])
                k = min(L[e], max(0, G[e] // 2 - a))
                A = a + k
                rng[e][0] = min(rng[e][0], A); rng[e][1] = max(rng[e][1], A)
                if A != G[e] // 2:
                    off[e] += 1; bad = True
            any_off += bad
        print(f"reading {label}: |X|={len(X)}, subsets enumerated={n}, G={G}")
        for e in EVALS:
            print(f"  {e}: part A {rng[e][0]}..{rng[e][1]}, part B {G[e]-rng[e][1]}..{G[e]-rng[e][0]}; shuffles off the half split: {off[e]}/{n} = {off[e]/n:.4f}")
        print(f"  shuffles with at least one evaluation off the half split: {any_off}/{n} = {any_off/n:.4f}")


if __name__ == "__main__":
    main()
