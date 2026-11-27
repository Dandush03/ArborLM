"""Auditor probe 2: only id-like string fields and status strings (no figures).
R1 shapes: name, earlier_id, status. R2 lineages: per-entry key names, presence of
'id', id==key, status_before_capacity. C1 lineages: name, status. Drops file text."""
import json
import subprocess

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"


def show(p):
    return subprocess.run(["git", "-C", REPO, "show", p], check=True, capture_output=True).stdout


r1 = json.loads(show("7cd0ac5a:studies/m0/manifests/r1_fix4_survivors.json"))
print("R1 shapes (name | earlier_id | status):")
for e in r1["shapes"]:
    print("  ", repr(e.get("name")), "|", repr(e.get("earlier_id")), "|", repr(e.get("status")))

r2 = json.loads(show("7cd0ac5a:studies/m0/manifests/r2_fix4_survivors.json"))
print("R2 lineages: type", type(r2["lineages"]).__name__)
allkeys = set()
for k, v in r2["lineages"].items():
    allkeys |= set(v.keys())
print("  entry keys:", sorted(allkeys))
for k, v in r2["lineages"].items():
    print("  ", repr(k), "| id:", repr(v.get("id", "<ABSENT>")), "| id==key:", v.get("id") == k,
          "| status_before_capacity:", repr(v.get("status_before_capacity", "<ABSENT>")))

m1 = json.loads(show("7cd0ac5a:studies/m0/manifests/m1_fix4_survivors.json"))
print("M1 survivors:", m1["survivors"])

c1 = json.loads(show("7cd0ac5a:studies/m0/manifests/c1_fix4_survivors.json"))
print("C1 lineages (name | status):")
for e in c1["lineages"]:
    print("  ", repr(e.get("name")), "|", repr(e.get("status")))

print("DROPS FILE raw:")
print(repr(show("b78e58b1:docs/reviews/m0-lineage-decision-2026-11-25/cross_evaluation_map/drops_after_final_checks.txt").decode("utf-8")))
