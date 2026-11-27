"""Item 5 and parts of item 4 from my own results: removal reasons, unions and slack, highest discard rates."""
import json
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

S = rc.SCR
E = json.load(open(f"{S}/deliver/e_rounds.json"))
res = {}
for f in ("round1_text.jsonl", "round1_c1.jsonl", "round2.jsonl"):
    for line in open(f"{S}/deliver/{f}"):
        r = json.loads(line)
        res[(r["lineage"], r["level"], r["target"])] = r
print("== removal reasons (mine)")
for key, o in E["outcome"].items():
    for ro in o["rounds"]:
        for lid, why in ro["reasons"].items():
            print(key, "round", ro["round"], lid, why)
print("== per part: clusters/lineages registered, and every multi-lineage cluster's union slack in its last round")
final_cells = []
zero_slack = []
for key, o in E["outcome"].items():
    last = o["rounds"][-1]
    reg = set(o["registered"])
    print(key, "G", o["G_registered"], "lineages", len(reg), "D(G)", last["D_G"])
    for c, ci in last["clusters"].items():
        if "union_by_level" in ci:
            sl = ci["union_slack_by_level"]
            if ci["k"] > 1:
                print("   ", c, "k", ci["k"], "D_lin", ci["D_lin"], "k*D_lin-D(G)", ci["k"] * ci["D_lin"] - last["D_G"], "union slack by level", sl)
            if min(sl.values()) == 0:
                zero_slack.append((key, c, ci["k"], ci["D_lin"], last["D_G"], sl))
        for lid in ci["lineages"]:
            if lid in reg:
                for lv in rc.LEVELS:
                    final_cells.append((key, c, res[(lid, lv, ci["D_lin"])]))
print("== clusters whose union equals D(G) exactly at some level (zero slack), final round:", len(zero_slack))
for z in zero_slack:
    print("   ", z[0], z[1], "k", z[2], "D_lin", z[3], "D(G)", z[4], "levels at zero:", [lv for lv, s in z[5].items() if s == 0])
print("== registered lineages' cells at their final target:", len(final_cells), "; all ended on target:", all(r["ended"] == "target" and r["count"] == r["target"] for _, _, r in final_cells))
final_cells.sort(key=lambda t: (-t[2]["attempts"] / t[2]["count"], t[2]["lineage"], t[2]["level"]))
print("== the ten passing cells (final round, registered lineages) with the highest attempts/count")
for key, c, r in final_cells[:10]:
    print(f"   {key} {c} {r['lineage']} L{r['level']} T={r['target']} attempts={r['attempts']} count={r['count']} ratio={r['attempts']/r['count']:.4f} budget={40*r['target']+1000} budget_used={r['attempts']/(40*r['target']+1000):.4f}")
allc = sorted(res.values(), key=lambda r: -r["attempts"] / max(r["count"], 1))
print("== for reference, the ten highest attempts/count among ALL cells counted (any round, any outcome)")
for r in allc[:10]:
    print(f"   {r['lineage']} L{r['level']} T={r['target']} attempts={r['attempts']} count={r['count']} ended={r['ended']} ratio={r['attempts']/r['count']:.4f}")
nzero = sum(1 for _, _, r in final_cells if r["attempts"] == r["count"])
print("== final cells with no discard at all (attempts == count):", nzero, "of", len(final_cells))
