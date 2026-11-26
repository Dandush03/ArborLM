"""List every R1 (unit, file kind, lineage, level, rule) row that is exact in all three seeds (fired == n and acc_fired == 1),
and whether the rule is a class-table entry. Usage: python r1_exact_rows.py OUT_JSON"""
import json, os, sys, re
from collections import defaultdict
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126"
SPEC = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
ct = json.load(open(f"{SPEC}/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"))["R1"]["entries"]
def entry(lid, h):
    b = h.split(":", 1)[1] if h.startswith(("a3:", "a4:")) else h
    st = re.sub(r"_r\d+$", "", lid[3:])
    for e in ct:
        if e["rule"] == b and (e["lineage_stems"] == "every R1 lineage" or st in e["lineage_stems"]):
            return f"{e['label']} {e['rule']}"
    return None
ex = defaultdict(list)
for unit in ("R1a", "R1b"):
    for s in "123":
        d = f"{RUN}/{unit}/seed{s}"
        for fn in os.listdir(d):
            if not fn.endswith(".jsonl"):
                continue
            kind = fn.split(".")[-2]
            for l in open(f"{d}/{fn}"):
                x = json.loads(l)
                ok = x.get("fired") == x["n"] and x.get("acc_fired") == 1
                ex[(unit, kind, x["lineage"], x["level"], x["heuristic"])].append(ok)
rows = [list(k) + [entry(k[2], k[4])] for k, v in sorted(ex.items()) if len(v) == 3 and all(v)]
json.dump(rows, open(sys.argv[1], "w"), indent=1)
print("rows exact in all three seeds:", len(rows))
from collections import Counter
print(Counter((r[2], r[4], r[5]) for r in rows))
