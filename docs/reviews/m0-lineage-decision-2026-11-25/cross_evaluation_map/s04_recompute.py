# ruff: noqa
"""Cross-evaluation map (M0), step 3/4: global clusters by transitive merging, counts per evaluation, and the range of part sizes
the addendum's partition text allows. COUNTS ONLY: no shuffle is computed, no seed is used, no split of real clusters is made.

Usage:
  python s04_recompute.py cross_evaluation_procedures_proposed.json [--drop LINEAGE_ID ...] [--drop-file FILE] [--promote PAIR_ID ...]
(--promote treats a BORDERLINE pair as STRONG, for sensitivity runs only.)
Lineages to drop are removed (also those listed in the JSON's "dropped_since_fix4"); a strict cluster with no lineage left
vanishes, and every pair touching it vanishes. Standard library only.

Partition text used (ADR-0033 addendum 1, DRAFT 2, section 4 'The procedure', file SHA-256 0df152b1...): X = global clusters with
registered lineages in >= 2 evaluations, shuffled once and dealt A, B, A, B... (A gets the extra one); then for each evaluation e,
k_e = min(|L_e|, max(0, floor(G_e/2) - a_e)) single-evaluation clusters go to A and the rest to B. Which X clusters land in A is
the only random input to the counts, so the bounds below range a_e over every value a shuffle of X can give:
max(0, x_e - floor(|X|/2)) <= a_e <= min(x_e, ceil(|X|/2)).
"""
import json, math, sys
from collections import defaultdict

EVALS = ("R1", "R2", "M1", "C1")


def load(path, extra_drops):
    doc = json.load(open(path))
    drops = set(doc.get("dropped_since_fix4", [])) | set(extra_drops)
    clusters = {}
    for c in doc["strict_clusters"]:
        left = [m for m in c["survivors"] if m not in drops]
        if left:
            clusters[(c["eval"], c["cluster"])] = left
    unknown = sorted(drops - {x["id"] for x in doc["lineages"]})
    return doc, clusters, drops, unknown


def components(clusters, pairs, grades):
    parent = {k: k for k in clusters}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    used = []
    for p in pairs:
        a, b = tuple(p["a"]), tuple(p["b"])
        if p["grade"] in grades and a in clusters and b in clusters:
            used.append(p["id"])
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    comp = defaultdict(list)
    for k in clusters:
        comp[find(k)].append(k)
    out = []
    for members in comp.values():
        lins = sorted(l for k in members for l in clusters[k])
        out.append({"identity": lins[0], "members": sorted(members), "evals": sorted({e for e, _ in members}, key=EVALS.index), "lineages": lins})
    return sorted(out, key=lambda g: g["identity"]), used


def bounds(G, x_e, L, nA, nB):
    rows = []
    lo, hi = max(0, x_e - nB), min(x_e, nA)
    for a in range(lo, hi + 1):
        k = min(L, max(0, G // 2 - a))
        A = a + k
        rows.append((a, A, G - A))
    return rows


def report(doc, clusters, grades, label):
    gl, used = components(clusters, doc["pairs"], grades)
    print(f"\n==================== reading {label}: links of grade {sorted(grades)} ({len(used)} links used: {', '.join(used)})")
    X = [g for g in gl if len(g["evals"]) >= 2]
    nA, nB = math.ceil(len(X) / 2), len(X) // 2
    print(f"global clusters: {len(gl)}; cross-evaluation (X): {len(X)} -> {nA} to A, {nB} to B")
    for g in X:
        mem = "; ".join(f"{e}:{c}[{', '.join(l for l in clusters[(e, c)])}]" for e, c in g["members"])
        print(f"  X {g['identity']}  evals={'/'.join(g['evals'])}  size={len(g['members'])} strict clusters  {mem}")
    summary = {}
    for e in EVALS:
        strict = sum(1 for (ev, _) in clusters if ev == e)
        G = sum(1 for g in gl if e in g["evals"])
        x_e = sum(1 for g in X if e in g["evals"])
        L = G - x_e
        merged = [g for g in gl if sum(1 for ev, _ in g["members"] if ev == e) > 1]
        rows = bounds(G, x_e, L, nA, nB)
        As = [r[1] for r in rows]; Bs = [r[2] for r in rows]; small = [min(r[1], r[2]) for r in rows]
        summary[e] = {"strict": strict, "G": G, "x": x_e, "L": L, "A": (min(As), max(As)), "B": (min(Bs), max(Bs)), "smaller": (min(small), max(small))}
        print(f"  {e}: strict clusters {strict}; independent units G_{e} = {G} (within-evaluation merges: {len(merged)}"
              + (" -> " + "; ".join("+".join(c for ev, c in g['members'] if ev == e) for g in merged) if merged else "") + ")"
              + f"; X touching {e}: {x_e}; single-evaluation L_{e}: {L}")
        print(f"      part A size range {min(As)}..{max(As)}, part B size range {min(Bs)}..{max(Bs)}, smaller part {min(small)}..{max(small)}"
              f"  (half split would be A={G // 2}, B={G - G // 2});  rows (a_e, A, B): {rows}")
    largest = max(gl, key=lambda g: (len(g["members"]), len(g["lineages"])))
    print(f"  largest global cluster: {largest['identity']} with {len(largest['members'])} strict clusters, {len(largest['lineages'])} lineages, evals {'/'.join(largest['evals'])}")
    return gl, summary


def main():
    args = sys.argv[1:]
    path = args[0]
    drops = []
    promote = []
    i = 1
    while i < len(args):
        if args[i] == "--drop":
            drops.append(args[i + 1]); i += 2
        elif args[i] == "--promote":
            promote.append(args[i + 1]); i += 2
        elif args[i] == "--drop-file":
            drops += [l.strip() for l in open(args[i + 1]) if l.strip() and not l.startswith("#")]; i += 2
        else:
            raise SystemExit(f"unknown argument {args[i]}")
    doc, clusters, dropped, unknown = load(path, drops)
    for p in doc["pairs"]:
        if p["id"] in promote:
            p["grade"] = "STRONG"
    if promote:
        print(f"SENSITIVITY: pairs promoted to STRONG for this run only: {promote}")
    print(f"input {path}; lineages dropped: {sorted(dropped) or 'none'}" + (f"; NOT IN MAP (ignored): {unknown}" if unknown else ""))
    print("strict clusters left:", {e: sum(1 for (ev, _) in clusters if ev == e) for e in EVALS},
          "lineages left:", {e: sum(len(v) for (ev, _), v in clusters.items() if ev == e) for e in EVALS})
    report(doc, clusters, {"STRONG"}, "1 (STRONG only)")
    report(doc, clusters, {"STRONG", "BORDERLINE"}, "2 (STRONG + BORDERLINE)")


if __name__ == "__main__":
    main()
