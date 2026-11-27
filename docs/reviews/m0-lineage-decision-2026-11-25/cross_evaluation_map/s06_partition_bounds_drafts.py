# ruff: noqa
"""Cross-evaluation map (M0), step 4 under both addendum texts: the range of part sizes each evaluation could receive, by enumeration
over every outcome of the shuffles (no seed, no shuffle computed, no real split). COUNTS ONLY.

Texts (docs/decisions/ADR-0033-addendum-1-lineage-clusters.md on claude/m0-spec):
  draft 2 (commit a2fb316f, SHA-256 0df152b1...): X dealt A, B, A, ... (A gets the odd one); k_e = min(|L_e|, max(0, floor(G_e/2) - a_e)).
  draft 3 (commit 9788a8ef, SHA-256 2df30a29...): X dealt B, A, B, ... (B gets the odd one); same k_e with N_e; and, as an option
           (section 4 item 9, not the default), borderline groups kept in one part: the unit of steps 1-3 is the group (component of
           the borderline links between clusters), counted in groups; every cluster takes its group's part; sizes are in clusters.
Survivors of the fix-4 manifests are taken as the candidate lineages (draft 3 stage 2); this is an assumption (second solvers etc. not checked).

Attempt 1 (kept: *_attempt1_smaller_part_bug.*) computed the smaller part from the two extremes only and under-reported its maximum.
Run: python s06_partition_bounds_drafts.py cross_evaluation_procedures_proposed.json [--drop-file FILE]
"""
import itertools, json, math, sys

EVALS = ("R1", "R2", "M1", "C1")


def comps(nodes, edges):
    adj = {k: set() for k in nodes}
    for a, b in edges:
        if a in adj and b in adj:
            adj[a].add(b); adj[b].add(a)
    seen, out = set(), []
    for k in sorted(adj):
        if k in seen:
            continue
        st, c = [k], []
        seen.add(k)
        while st:
            u = st.pop(); c.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); st.append(v)
        out.append(sorted(c))
    return out


def ksums(sizes, k):
    """Every achievable sum of k elements chosen from the multiset sizes (DP over count and sum)."""
    reach = {(0, 0)}
    for x in sizes:
        reach |= {(c + 1, t + x) for c, t in reach if c < k}
    return sorted({t for c, t in reach if c == k})


def ranges(units, first):
    """units: list of dicts eval -> number of clusters of that eval in the unit. Returns per-eval (A values, total) over all outcomes."""
    X = [i for i, u in enumerate(units) if len(u) >= 2]
    nX = len(X)
    nA = nX // 2 if first == "B" else math.ceil(nX / 2)
    res = {}
    for e in EVALS:
        Ne_units = [i for i, u in enumerate(units) if e in u]
        Le = [i for i in Ne_units if len(units[i]) == 1]
        size_e = sum(units[i][e] for i in Ne_units)
        Lsizes = [units[i][e] for i in Le]
        cache = {}
        Avals = set()
        for Aset in itertools.combinations(X, nA):
            aset = [i for i in Aset if e in units[i]]
            a = len(aset)
            k = min(len(Le), max(0, len(Ne_units) // 2 - a))
            if k not in cache:
                cache[k] = ksums(Lsizes, k)
            base = sum(units[i][e] for i in aset)
            Avals.update(base + t for t in cache[k])
        res[e] = (sorted(Avals), size_e, len(Ne_units))
    return res, nX


def main():
    doc = json.load(open(sys.argv[1]))
    drops = set(doc.get("dropped_since_fix4", []))
    if len(sys.argv) > 3 and sys.argv[2] == "--drop-file":
        drops |= {l.strip() for l in open(sys.argv[3]) if l.strip() and not l.startswith("#")}
    clusters = [(c["eval"], c["cluster"]) for c in doc["strict_clusters"] if any(m not in drops for m in c["survivors"])]
    S = [(tuple(p["a"]), tuple(p["b"])) for p in doc["pairs"] if p["grade"] == "STRONG"]
    B = [(tuple(p["a"]), tuple(p["b"])) for p in doc["pairs"] if p["grade"] == "BORDERLINE"]

    def units_of(components):
        out = []
        for c in components:
            u = {}
            for e, _ in c:
                u[e] = u.get(e, 0) + 1
            out.append(u)
        return out

    gS = comps(clusters, S)                      # global clusters, reading 1
    gSB = comps(clusters, S + B)                 # global clusters, reading 2
    idx = {k: i for i, c in enumerate(gS) for k in c}
    groups = comps(list(range(len(gS))), [(idx[a], idx[b]) for a, b in B if a in idx and b in idx])
    # reading 1, groups option: a unit is a group of reading-1 global clusters; its size in e is the number of reading-1 global clusters touching e
    gunits = []
    for g in groups:
        u = {}
        for gi in g:
            for e in {e for e, _ in gS[gi]}:
                u[e] = u.get(e, 0) + 1
        gunits.append(u)

    def gl_units(gl):  # each global cluster counts once per evaluation it touches
        return [{e: 1 for e in {e for e, _ in c}} for c in gl]

    cases = [
        ("reading 1 (STRONG), draft 2 deal (A first)", gl_units(gS), "A"),
        ("reading 1 (STRONG), draft 3 deal (B first)", gl_units(gS), "B"),
        ("reading 1 (STRONG), draft 3 option item 9: borderline groups kept in one part (B first)", gunits, "B"),
        ("reading 2 (STRONG+BORDERLINE merged), draft 2 deal (A first)", gl_units(gSB), "A"),
        ("reading 2 (STRONG+BORDERLINE merged), draft 3 deal (B first)", gl_units(gSB), "B"),
    ]
    for label, units, first in cases:
        res, nX = ranges(units, first)
        print(f"{label}: units={len(units)}, cross-evaluation units={nX}")
        for e in EVALS:
            Avals, size, n_units = res[e]
            small = [min(A, size - A) for A in Avals]
            print(f"  {e}: clusters (independent units) {size} in {n_units} partition units; part A {min(Avals)}..{max(Avals)} (achievable sizes {Avals}), part B {size-max(Avals)}..{size-min(Avals)}; smaller part {min(small)}..{max(small)}")


if __name__ == "__main__":
    main()
