# ruff: noqa
"""Audit 3 (R1): exact structure counts (isomorphism classes under renaming; presentation order and symmetric phrasing ignored)
for the small cells, by canonical forms over all relabellings.
  swap_tracking L0, L1: full enumeration of every (op sequence, asked person) the generator can emit, orbits under S_n.
  pet_owners, seating_row L0, L1; graph_bipartite L0-L3: distinct canonical forms over a large generator draw (D, a lower bound)
  and, for graph_bipartite, the number of graphs on n vertices (an upper bound: the answer is a function of the graph).
usage (worktree root): PYTHONHASHSEED=0 uv run --locked python <this> <N draws>
"""
import itertools, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen

N = int(sys.argv[1])
L = gen.lineages()


def swap_orbits(n, steps):
    P = list(range(n))
    swaps = [("s", a, b) for a, b in itertools.combinations(P, 2)]
    rots = []
    seen = set()
    for a, b, c in itertools.permutations(P, 3):
        key = min((a, b, c), (b, c, a), (c, a, b))  # the same simultaneous hand-over
        if key not in seen:
            seen.add(key); rots.append(("r",) + key)
    ops = swaps + rots
    perms = list(itertools.permutations(P))

    def canon_op(o, p):
        if o[0] == "s":
            a, b = sorted((p[o[1]], p[o[2]]))
            return ("s", a, b)
        a, b, c = p[o[1]], p[o[2]], p[o[3]]
        return ("r",) + min((a, b, c), (b, c, a), (c, a, b))

    orbits = set()
    for seq in itertools.product(ops, repeat=steps):
        for ask in P:
            orbits.add(min((tuple(canon_op(o, p) for o in seq), p[ask]) for p in perms))
    return len(orbits), len(ops) ** steps * n


print("swap_tracking L0 (3 people, 2 operations): orbits, labelled =", swap_orbits(3, 2))
print("swap_tracking L1 (4 people, 4 operations): orbits, labelled =", swap_orbits(4, 4))


def canon_pets(b):
    st = b.structured
    n = len(st["people"])
    best = None
    for pp in itertools.permutations(range(n)):
        for qq in itertools.permutations(range(n)):
            cl = []
            for c in st["clues"]:
                if c[0] == "either":
                    cl.append(("either", pp[c[1]], tuple(sorted((qq[c[2]], qq[c[3]])))))
                else:
                    cl.append((c[0], pp[c[1]], qq[c[2]]))
            k = (tuple(sorted(cl)), qq[st["ask"]])
            if best is None or k < best:
                best = k
    return best


def canon_seat(b):
    st = b.structured
    n = len(st["people"])
    best = None
    for pp in itertools.permutations(range(n)):
        cl = []
        for c in st["clues"]:
            t = c[0]
            if t == "notnext":
                cl.append((t,) + tuple(sorted((pp[c[1]], pp[c[2]]))))
            elif t == "pos":
                cl.append((t, pp[c[1]], c[2]))
            elif t == "between":
                a, m, z = pp[c[1]], pp[c[2]], pp[c[3]]
                cl.append((t, min(a, z), m, max(a, z)))
            else:
                cl.append((t,) + tuple(pp[x] for x in c[1:]))
        k = (tuple(sorted(cl)), st["seat"])
        if best is None or k < best:
            best = k
    return best


def canon_graph(b):
    ppl = b.structured["people"]
    idx = {p: i for i, p in enumerate(ppl)}
    E = [tuple(sorted((idx[a], idx[c]))) for a, c in b.structured["rivals"]]
    n = len(ppl)
    return min(tuple(sorted(tuple(sorted((p[a], p[c]))) for a, c in E)) for p in itertools.permutations(range(n)))


GRAPHS = {4: 11, 5: 34, 6: 156, 7: 1044, 8: 12346, 9: 274668, 10: 12005168}  # non-isomorphic simple graphs on n vertices (OEIS A000088)
for lid, fn, lvs in (("R1.pet_owners", canon_pets, (0, 1)), ("R1.seating_row", canon_seat, (0, 1)), ("R1.graph_bipartite", canon_graph, (0, 1, 2, 3))):
    for lv in lvs:
        its = gen.items(L[lid], lv, N if lid != "R1.graph_bipartite" or lv < 3 else N // 4, 9900)
        ks = {fn(b) for b in its}
        extra = f"; graphs on {lv + 4} vertices (upper bound) {GRAPHS[lv + 4]:,}" if lid == "R1.graph_bipartite" else ""
        print(f"{lid} L{lv}: distinct exact structures seen {len(ks):,} in {len(its):,} draws{extra}", flush=True)
for lv in range(7):
    n = lv + 4
    print(f"R1.graph_bipartite L{lv}: upper bound (graphs on {n} vertices) {GRAPHS[n]:,}")
