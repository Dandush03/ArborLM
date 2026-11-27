# ruff: noqa
"""Final C1 audit (fix 4), step 6b: summarise f6_capacity.py and check collisions BETWEEN jobs (core.generate_pool shares one `taken` set across the
lineages, levels and roles of a part, so an item text drawn by two lineage-levels would be taken only once). Reads the 8-byte hash prefixes each job wrote.
For each lineage-level: supplied, pass at G = 9 / 8 / 7, and the number of its items whose text also occurs in another lineage-level job; the conservative
supply = supplied - collisions (each colliding item removed from BOTH jobs) is compared with the demand. Usage: python3 f6b_collisions.py CAP_DIR OUT_JSON
"""
import glob, json, os, sys
from collections import Counter, defaultdict

cap, outp = sys.argv[1], sys.argv[2]
d = json.load(open(os.path.join(cap, "capacity.json")))
seen = Counter()
per = {}
for fn in sorted(glob.glob(os.path.join(cap, "*.bin"))):
    b = open(fn, "rb").read()
    hs = [b[i:i + 8] for i in range(0, len(b), 8)]
    per[os.path.basename(fn)[:-4]] = hs
    seen.update(set(hs))
out = {"seed": d["seed"], "count": d["count"], "rows": []}
for j in d["jobs"]:
    tag = f"{j['lid'].replace('C1.', '')}_L{j['lv']}"
    coll = sum(1 for h in per[tag] if seen[h] > 1)
    row = {"lid": j["lid"], "lv": j["lv"], "supplied": j["supplied"], "attempts": j["attempts"], "distinct_texts": j["distinct_texts"], "collisions_other_jobs": coll}
    for G in (9, 8, 7):
        g = j[f"G{G}"]
        row[f"G{G}_pass_alone"] = g["pass"]
        row[f"G{G}_pass_after_collisions"] = g["pass"] and (j["supplied"] - coll) >= g["demand"]
        row[f"G{G}_attempt_at_demand"] = g["attempt_at_demand"]
        row[f"G{G}_budget"] = g["budget"]
    out["rows"].append(row)
fails = {G: [(r["lid"], r["lv"]) for r in out["rows"] if not r[f"G{G}_pass_after_collisions"]] for G in (9, 8, 7)}
out["fails"] = fails
out["total_collisions"] = sum(r["collisions_other_jobs"] for r in out["rows"])
out["max_attempt_ratio"] = max((r["G7_attempt_at_demand"] or 0) / 35300 for r in out["rows"])
json.dump(out, open(outp, "w"), indent=1, sort_keys=True)
print("jobs", len(out["rows"]), "total cross-job collisions", out["total_collisions"])
print("fails per G:", {G: len(v) for G, v in fails.items()}, fails)
print("worst attempts per item at the G=7 demand:", round(out["max_attempt_ratio"], 3))
w = sorted(out["rows"], key=lambda r: -(r["G7_attempt_at_demand"] or 10**9))[:5]
for r in w:
    print(r["lid"], r["lv"], "attempt at 35,300:", r["G7_attempt_at_demand"], "budget", r["G7_budget"], "coll", r["collisions_other_jobs"])
print("all supplied 35300:", all(r["supplied"] == 35300 for r in out["rows"]), "distinct==supplied:", all(r["distinct_texts"] == r["supplied"] for r in out["rows"]))
