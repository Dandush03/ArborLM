# ruff: noqa
"""Diagnose discrepancies between the author's two-sided table and my measurements by applying the AUTHOR'S heuristic
functions (lineages_r1_shortcuts; read-only import, diagnosis only) to my rendered items, beside my own computation."""
import gzip, json, os, re, sys
from collections import Counter

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
from studies.m0.core import Item
from studies.m0 import lineages_r1_shortcuts as S

d = sys.argv[1]
L = lambda lid: [json.loads(x) for x in gzip.open(os.path.join(d, f"{lid}.reg.jsonl.gz"), "rt")]


def item(r, lid):
    return Item(r["id"], "R1", "A", "R1." + lid, "f", r["level"], r["q"], r["s"], r["a"], r["t"], r["k"])


# 1. temporal_critical_path longest_job
rows = [r for r in L("temporal_critical_path") if 1 <= r["level"] <= 5]
a_cr = []
mine = []
for r in rows:
    it = item(r, "temporal_critical_path")
    p = S._longest_job(it)
    a_cr.append(S.credit(p, it))
    top = max(j[1] for j in r["s"]["jobs"])
    lst = [j[0] for j in r["s"]["jobs"] if j[1] == top]
    mine.append(1 / len(lst) if r["a"] in lst else 0)
print("critical_path L1-5: author credit() mean", round(sum(a_cr) / len(a_cr), 4), "| my credit", round(sum(mine) / len(mine), 4))
ex = rows[0]
it = item(ex, "temporal_critical_path")
print("  example", ex["id"], "key", ex["a"], "author pred", S._longest_job(it), "author _valid", S._valid(S._longest_job(it), it), "parse_options", S.parse_options(ex["q"]))

# 2. minimax: author's generic smallest_number vs true smallest leaf
rows = [r for r in L("minimax_tree") if 1 <= r["level"] <= 5]
g = [S.generic(item(r, "minimax_tree")).get("smallest_number") == r["a"] for r in rows]
def leaves(t):
    return [t] if isinstance(t, int) else [x for c in t for x in leaves(c)]
true_small = [str(min(leaves(r["s"]["tree"]))) == r["a"] for r in rows]
print("minimax L1-5: author generic smallest_number exact", round(sum(g) / len(g), 4), "| signed smallest leaf exact", round(sum(true_small) / len(true_small), 4))
print("  example body numbers parsed by the author's regex:", re.findall(r"\d+", S.split_body(rows[0]["q"])[0])[:8], "key", rows[0]["a"])

# 3. order_compare: author's direction-blind verbatim heuristic vs direction-aware
rows = [r for r in L("order_compare") if 1 <= r["level"] <= 5]
fa = [S.generic(item(r, "order_compare")).get("asked_pair_stated_verbatim") for r in rows]
fired = [(p, r["a"]) for p, r in zip(fa, rows) if p is not None]
print("order_compare L1-5: author verbatim fires", len(fired), "/", len(rows), "correct", sum(p == a for p, a in fired))
fw = sum(1 for r in rows if [r["s"]["x"], r["s"]["y"]] in r["s"]["taller"])
rv = sum(1 for r in rows if [r["s"]["y"], r["s"]["x"]] in r["s"]["taller"])
print("  direction-aware: asked order stated", fw, "(key yes:", sum(1 for r in rows if [r['s']['x'], r['s']['y']] in r['s']['taller'] and r['a'] == 'yes'), ") reverse stated", rv, "(key no:", sum(1 for r in rows if [r['s']['y'], r['s']['x']] in r['s']['taller'] and r['a'] == 'no'), ")")

# 4. queue_line_r2: most/least mentioned
rows = [r for r in L("containers_queue_line_r2") if 1 <= r["level"] <= 5]
for name in ("most_mentioned", "least_mentioned"):
    c = [S.credit(S.generic(item(r, "containers_queue_line_r2")).get(name), item(r, "containers_queue_line_r2")) for r in rows]
    print(f"queue_line_r2 L1-5 author {name}: mean credit {sum(c)/len(c):.4f}, chance {sum(1/r['k'] for r in rows)/len(rows):.4f}")
