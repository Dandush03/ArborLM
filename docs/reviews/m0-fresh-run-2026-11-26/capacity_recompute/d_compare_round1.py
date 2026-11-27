"""Compare my round-1 counts with the record cell by cell; my own condition (i) and (ii) for round 1."""
import json
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

S = rc.SCR
mine = {}
for f in ("round1_text.jsonl", "round1_c1.jsonl"):
    for line in open(f"{S}/deliver/{f}"):
        r = json.loads(line)
        mine[(r["lineage"], r["level"])] = r
rec = rc.load_json("studies/m0/manifests/capacity_of_record.json")
ended_vocab = set()
diffs, agree, ncell = [], 0, 0
for e, pp in rec["parts"].items():
    for p, part in pp.items():
        r1 = part["rounds"][0]
        for c, cd in r1["clusters"].items():
            for lid, levels in cd["lineages"].items():
                for lv, x in levels.items():
                    ncell += 1
                    ended_vocab.add(x["ended"])
                    m = mine[(lid, int(lv))]
                    fields = {"target": (x["target"], m["target"]), "count": (x["count"], m["count"]),
                              "attempts": (x["attempts"], m["attempts"]), "ended": (x["ended"], m["ended"]),
                              "solver_disagreements": (x["solver_disagreements"], m["solver_disagreements"])}
                    bad = {k: v for k, v in fields.items() if v[0] != v[1]}
                    if bad:
                        diffs.append({"part": e + p, "cluster": c, "lineage": lid, "level": lv, "record_vs_mine": bad})
                    else:
                        agree += 1
print("cells in record round 1:", ncell, "cells I counted:", len(mine), "agree on all five fields:", agree, "differ:", len(diffs))
print("record 'ended' values:", sorted(ended_vocab))
for d in diffs:
    print("DIFF", json.dumps(d))
tot_att = sum(m["attempts"] for m in mine.values())
print("total attempts (builds) in my round 1:", tot_att, "; solver disagreements total:", sum(m["solver_disagreements"] for m in mine.values()),
      "; largest single solver call (s):", max(m["max_solver_seconds"] for m in mine.values()))
json.dump({"n_record": ncell, "n_mine": len(mine), "agree": agree, "diffs": diffs}, open(f"{S}/deliver/d_compare_round1.json", "x"), indent=1)
