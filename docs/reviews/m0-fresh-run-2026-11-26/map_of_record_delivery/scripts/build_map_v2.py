"""Build map_of_record.json, MAP_REASONS.md and counts from (1) the code enumeration e01 and (2) judgements.py.
Standard library only. Usage: python build_map.py <deliver_dir>. Deterministic: no timestamps, sorted output."""
import json, os, re, sys, hashlib
D = sys.argv[1]
sys.path.insert(0, os.path.join(D, 'scripts'))
import judgements_v2 as J

# ---- 1. written lineages: every Lineage id defined in studies/m0/lineages_*.py (all rounds), K0 excluded (not a node, s3 item 5)
cite, evals = {}, {}
for line in open(os.path.join(D, 'e01_enumerate_all_code.out.txt'), encoding='utf-8'):
    if line[:3] not in ('R1.', 'R2.', 'M1.', 'C1.', 'K0.'):
        continue
    lid, rest = line.rstrip('\n').split(' ', 1)
    locs = []
    for part in rest.split(' ; '):
        mod, fn, ln = part.split('|')[0].split(':')
        locs.append(f"studies/m0/{mod.split('.')[-1]}.py:{ln}")
    if lid.startswith('K0.'):
        continue
    cite[lid] = sorted(set(locs))
    evals[lid] = lid.split('.')[0]
ids = sorted(cite)

# ---- 2. revision links: ids of one stem (one written base rule rewritten) are linked to the stem's base id
SPECIAL = {"M1.power_remainder_r2": "M1.last_digit_power", "R2.to_base_wide": "R2.to_base", "R2.string_rewrite_nonidentity": "R2.string_rewrite",
           "C1.fib_shapes_recursive": "C1.recursive_calls", "C1.fib_shapes_recursive_f3": "C1.recursive_calls"}
SUF = ("_r2", "_r3", "_r4", "_r5", "_r6", "_f3", "_f4", "_traced")
def stem(i):
    if i in SPECIAL:
        return SPECIAL[i]
    e, n = i.split('.', 1)
    changed = True
    while changed:
        changed = False
        for s in SUF:
            if n.endswith(s):
                n = n[: -len(s)]; changed = True
    return f"{e}.{n}"
stems = {}
for i in ids:
    stems.setdefault(stem(i), []).append(i)
key = lambda a, b: (a, b) if a < b else (b, a)
judged = {}
for a, b, earlier, src, mine, reason in J.P:
    for x in (a, b):
        if x not in cite:
            sys.exit(f"STOP: judged id not in code: {x}")
    k = key(a, b)
    if k in judged:
        sys.exit(f"STOP: pair judged twice: {k}")
    judged[k] = (earlier, src, mine, reason)
rev = {}
for st, mem in sorted(stems.items()):
    base = st if st in cite else min(mem)
    for m in mem:
        if m == base:
            continue
        k = key(base, m)
        if k in judged:
            continue  # judged explicitly in judgements.py (procedure changed or contested)
        rev[k] = ("-", "revision chain (REPLACES / SUPERSEDES / docstring 'as <earlier id>') in the generators", "LINK",
                  f"Revision of the written base rule {st}: same procedure, rewritten for levels, wording, construction or capacity (builders read).")
allpairs = {**rev, **judged}
links = sorted(k for k, v in allpairs.items() if v[2] == "LINK")
border = sorted(k for k, v in allpairs.items() if v[2] == "BORDERLINE")
nones = sorted(k for k, v in allpairs.items() if v[2] == "NONE")

# ---- 3. components (transitive merging, s3 items 1-2)
par = {i: i for i in ids}
def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
for a, b in links:
    ra, rb = find(a), find(b)
    if ra != rb:
        par[max(ra, rb)] = min(ra, rb)
comp = {}
for i in ids:
    comp.setdefault(find(i), []).append(i)
clusters = sorted(({"cluster_id": min(m), "members": sorted(m)} for m in comp.values()), key=lambda c: c["cluster_id"])
cl_of = {m: c["cluster_id"] for c in clusters for m in c["members"]}
# groups: components of the graph on clusters whose edges are borderline pairs between two different clusters
gp = {c["cluster_id"]: c["cluster_id"] for c in clusters}
def gfind(x):
    while gp[x] != x:
        gp[x] = gp[gp[x]]; x = gp[x]
    return x
inside = []
for a, b in border:
    ca, cb = cl_of[a], cl_of[b]
    if ca == cb:
        inside.append((a, b)); continue
    ra, rb = gfind(ca), gfind(cb)
    if ra != rb:
        gp[max(ra, rb)] = min(ra, rb)
gr = {}
for c in gp:
    gr.setdefault(gfind(c), []).append(c)
groups = sorted(sorted(g) for g in gr.values())

out = {"lineages": {i: {"evaluation": evals[i]} for i in ids}, "links": [list(p) for p in links], "borderline_pairs": [list(p) for p in border],
       "clusters": clusters, "groups": groups}
txt = json.dumps(out, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
open(os.path.join(D, 'map_of_record.json'), 'w', encoding='utf-8').write(txt)

# ---- 4. MAP_REASONS.md
def c(i): return ", ".join(cite[i])
rows = ["# MAP_REASONS: one row per judged pair (map of record, M0, ADR-0033 addendum 1 stage 1)", "",
        "Columns: pair (code-point order); earlier judgement and its source; this auditor's judgement; unchanged/changed against the earlier judgement; reason, then the builders (file:line, all rounds) of both ids.",
        "'-' as earlier judgement: no earlier map judged the pair. Revision-chain rows: the earlier maps filed revisions under their stem without a pair judgement.", "",
        "| # | id A | id B | earlier (source) | mine | change | reason; generators |", "|---|---|---|---|---|---|---|"]
n = 0
for k in sorted(allpairs, key=lambda k: (allpairs[k][1].startswith("revision"), k)):
    earlier, src, mine, reason = allpairs[k]
    n += 1
    ch = "-" if earlier == "-" else ("unchanged" if earlier == mine else "CHANGED")
    rows.append(f"| {n} | {k[0]} | {k[1]} | {earlier} ({src}) | {mine} | {ch} | {reason} A: {c(k[0])}. B: {c(k[1])}. |")
open(os.path.join(D, 'MAP_REASONS.md'), 'w', encoding='utf-8').write("\n".join(rows) + "\n")

# ---- 5. counts
E = ("R1", "R2", "M1", "C1")
print("lineages per evaluation:", {e: sum(1 for i in ids if evals[i] == e) for e in E}, "total", len(ids))
print("judged pairs:", len(allpairs), "(explicit", len(judged), "+ revision", len(rev), ")")
print("links:", len(links), " borderline pairs:", len(border), " NONE rows:", len(nones))
print("global clusters:", len(clusters), " groups:", len(groups), " multi-cluster groups:", sum(1 for g in groups if len(g) > 1))
for e in E:
    print(f"  clusters with a lineage of {e}:", sum(1 for cc in clusters if any(evals[m] == e for m in cc["members"])))
xe = [cc for cc in clusters if len({evals[m] for m in cc["members"]}) > 1]
print("cross-evaluation clusters:", len(xe))
for cc in xe:
    print("   ", cc["cluster_id"], sorted({evals[m] for m in cc["members"]}), len(cc["members"]), "lineages")
print("borderline pairs inside one cluster (no group effect):", len(inside))
for p in inside: print("   ", p)
print("changed against earlier:", sum(1 for v in judged.values() if v[0] != "-" and v[0] != v[2]), " new pairs:", sum(1 for v in judged.values() if v[0] == "-"))
for k, v in sorted(judged.items()):
    if v[0] != "-" and v[0] != v[2]:
        print("   CHANGED", k, v[0], "->", v[2])
print("map_of_record.json sha256", hashlib.sha256(txt.encode('utf-8')).hexdigest())
