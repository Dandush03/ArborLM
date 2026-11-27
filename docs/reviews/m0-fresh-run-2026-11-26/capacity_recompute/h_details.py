"""Details for items 4 and 6 from the record and from my results (read-only)."""
import json
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

S = rc.SCR
rec = rc.load_json("studies/m0/manifests/capacity_of_record.json")
print("record top-level keys:", sorted(rec))
for e, p in (("M1", "A"), ("R2", "B")):
    print(e + p, "record removed:", json.dumps(rec["parts"][e][p]["removed"]))
ma = rec["parts"]["M1"]["A"]
for i, ro in enumerate(ma["rounds"]):
    c = ro["clusters"]["M1.ages"]
    print("M1A round", i + 1, "M1.ages k", c["k"], "D_lin", c["D_lin"], "lineages", sorted(c["lineages"]), "union_evaluated", c["union_evaluated"], "union", c.get("union_by_level"))
mine = {}
for f in ("round1_text.jsonl", "round1_c1.jsonl", "round2.jsonl"):
    for line in open(f"{S}/deliver/{f}"):
        r = json.loads(line)
        mine[(r["lineage"], r["level"], r["target"])] = r
print("R1.temporal_weekday_shift_r6 (mine):", [(lv, mine[("R1.temporal_weekday_shift_r6", lv, 241000)]["count"], mine[("R1.temporal_weekday_shift_r6", lv, 241000)]["attempts"]) for lv in rc.LEVELS])
print("R2.cellular_automaton round 1 (mine):", [(lv, mine[("R2.cellular_automaton", lv, 35300)]["count"], mine[("R2.cellular_automaton", lv, 35300)]["attempts"], mine[("R2.cellular_automaton", lv, 35300)]["ended"]) for lv in rc.LEVELS])
print("M1.rectangle_r3 round 1 (mine):", [(lv, mine[("M1.rectangle_r3", lv, 5180)]["count"], mine[("M1.rectangle_r3", lv, 5180)]["attempts"], mine[("M1.rectangle_r3", lv, 5180)]["ended"]) for lv in rc.LEVELS])
# prefix check: the first 241000 keys of the 500k draw under "capacity" equal the round-1 set (order and content)
import hashlib  # noqa: E402
b = open(f"{rc.KEYDIR}/R1.temporal_weekday_shift_r6__L0__T241000.bin", "rb").read()
print("round-1 temporal L0 key file sha256:", hashlib.sha256(b).hexdigest(), "keys:", len(b) // 16)
# give-ups anywhere?
print("cells ending gave_up:", sum(1 for r in mine.values() if r["ended"] == "gave_up"), "; cells counted in total:", len(mine))
# record totals
tot = {e + p: (rec["parts"][e][p]["G_registered"], rec["parts"][e][p]["lineages_registered"]) for e in rec["parts"] for p in rec["parts"][e]}
print("record per part (G, lineages):", tot, "sum lineages:", sum(v[1] for v in tot.values()))
