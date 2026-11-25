# ruff: noqa
"""Audit 4 (R1): exact structural keys (canonical forms up to renaming and presentation order) for the capacity cells that the
collision estimate leaves open. Distinct keys seen in N draws are a LOWER bound on the support; Chao1 = D + f1^2 / (2 f2) is printed
as an estimate. Seed base 9400 (throwaway).
usage (implementation worktree root): PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> <lineage> <levels comma> <N> [a|b]
"""
import itertools, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen4


def ahu(root, kids, mark):
    return "(" + mark(root) + "".join(sorted(ahu(c, kids, mark) for c in kids[root])) + ")"


def forest_key(parent, mark):
    kids = defaultdict(list)
    nodes = set(parent) | set(parent.values())
    for c, p in parent.items():
        kids[p].append(c)
    roots = sorted(n for n in nodes if n not in parent)
    return tuple(sorted(ahu(r, kids, mark) for r in roots))


def k_kinship_ancestor(b, reading):
    st = b.structured
    opts = set(st["options"])
    return (st["generations"], forest_key(st["parent"], lambda n: ("C" if n == st["child"] else "") + ("O" if n in opts else "")))


def k_seating(b, reading):  # seats are structure; people relabelled: clue multiset over SEATS of the hidden arrangement
    st = b.structured
    # recover the seat of each person index from the unique solution: the clues are over person indices, the answer by seat
    ppl = st["people"]
    n = len(ppl)
    cl = st["clues"]
    sols = []
    for perm in itertools.permutations(range(n)):
        pos = {p: i for i, p in enumerate(perm)}
        ok = True
        for c in cl:
            t = c[0]
            if t == "adj": ok = pos[c[2]] == pos[c[1]] + 1
            elif t == "left": ok = pos[c[1]] < pos[c[2]]
            elif t == "end": ok = pos[c[1]] in (0, n - 1)
            elif t == "pos": ok = pos[c[1]] == c[2]
            elif t == "between": ok = pos[c[1]] < pos[c[2]] < pos[c[3]] or pos[c[3]] < pos[c[2]] < pos[c[1]]
            elif t == "notnext": ok = abs(pos[c[1]] - pos[c[2]]) != 1
            if not ok: break
        if ok:
            sols.append(perm)
    # relabel people by... the clue set is NOT unique in solutions in general; use orbit canonical form: minimise over all relabellings
    best = None
    for lab in itertools.permutations(range(n)):
        def r(c):
            if c[0] in ("pos",): return (c[0], lab[c[1]], c[2])
            if c[0] == "between": return (c[0], lab[c[2]], *sorted((lab[c[1]], lab[c[3]])))
            if c[0] == "notnext": return (c[0], *sorted((lab[c[1]], lab[c[2]])))
            return (c[0], *[lab[x] for x in c[1:]])
        k = tuple(sorted(r(c) for c in cl))
        if best is None or k < best:
            best = k
    return (n, st["seat"], best)


def k_knights(b, reading):
    st = b.structured
    n = len(st["people"])
    stm = st["statements"]
    sym = {"both_knights", "some_knave", "same_kind", "differ"}
    best = None
    for lab in itertools.permutations(range(n)):
        rows = [None] * n
        for i, (k, a) in enumerate(stm):
            args = tuple(sorted(lab[x] for x in a)) if k in sym else tuple(lab[x] for x in a)
            rows[lab[i]] = (k, args)
        key = (tuple(rows), lab[st["who"]])
        if best is None or key < best:
            best = key
    return best


def k_one_culprit(b, reading):
    st = b.structured
    n = len(st["people"])
    best = None
    for lab in itertools.permutations(range(n)):
        rows = [None] * n
        for i, s in enumerate(st["statements"]):
            rows[lab[i]] = (s[0], *(sorted(lab[x] for x in s[1:]) if s[0] == "either" else [lab[x] for x in s[1:]]))
        key = tuple(rows)
        if best is None or key < best:
            best = key
    return (best, st["true_count"])


def k_swap(b, reading):
    st = b.structured
    ppl = list(st["hold"])
    n = len(ppl)
    best = None
    for lab0 in itertools.permutations(range(n)):
        lab = dict(zip(ppl, lab0))
        ops = []
        for o in st["ops"]:
            if o[0] == "swap":
                ops.append(("s", *sorted((lab[o[1]], lab[o[2]]))))
            else:
                t = (lab[o[1]], lab[o[2]], lab[o[3]])
                ops.append(("r", *min(t, t[1:] + t[:1], t[2:] + t[:2])))
        key = (tuple(ops), lab[st["who"]])
        if best is None or key < best:
            best = key
    return best  # objects are named once each, held one per person: relabelling objects is implied by relabelling people


KEYS = {"R1.kinship_ancestor_r4": k_kinship_ancestor, "R1.seating_row_r5": k_seating, "R1.knights_knaves_r5": k_knights, "R1.one_culprit": k_one_culprit,
        "R1.swap_tracking_r5": k_swap}



def k_topo(b, reading):  # names relabelled only up to alphabetical order (the order decides the tie-break): ranks are structure
    st = b.structured
    rank = {p: i for i, p in enumerate(sorted(p for p, _ in st["jobs"]))}
    return (tuple(sorted((rank[p], tuple(sorted(rank[d] for d in deps))) for p, deps in st["jobs"])), st["day"])


KEYS["R1.topological_order_r5"] = k_topo


def main():  # audit-4 fix 4: the run code moved here (run 1 of the topological key failed: the key was defined after the top-level run code)
    lid, levels, N = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], int(sys.argv[3])
    reading = sys.argv[4] if len(sys.argv) > 4 else "a"
    lin = gen4.lineages()[lid]
    for lv in levels:
        cnt = Counter(KEYS[lid](b, reading) for b in gen4.items(lin, lv, N, 9400))
        f = Counter(cnt.values())
        chao = len(cnt) + (f[1] ** 2 / (2 * f[2]) if f[2] else f[1] * (f[1] - 1) / 2)
        pairs = sum(v * (v - 1) // 2 for v in cnt.values())
        print(f"{lid} L{lv} N={N} distinct={len(cnt)} singletons={f[1]} doubletons={f[2]} chao1={chao:,.0f} collision_S={(N * (N - 1) / (2 * pairs)) if pairs else float('inf'):,.0f}", flush=True)


if __name__ == "__main__":
    main()
