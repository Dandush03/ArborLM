"""Stage order, task completeness, result hashes, ledger sums and headroom arithmetic (auditor's own code).

Usage: python3 -I stages.py <run dir> <ledger json> <frozen tree> <projection.json>
"""
import hashlib, json, sys
from pathlib import Path

run, ledger_p, tree, proj_p = map(Path, sys.argv[1:5])
fsha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
order = ["gates", "train-q1", "evaluate-q1", "train-wx", "evaluate-wx", "train-probe", "evaluate-probe", "analyze", "report"]
mans = {}
for s in order:
    mans[s] = json.loads((run / s / "manifest.json").read_text())
prev_end = None
print("stage                started_utc                       finished_utc                      status    tasks  failed  skipped  hash_mismatch")
for s in order:
    m = mans[s]
    tasks = m.get("tasks", [])
    failed = [t["label"] for t in tasks if t.get("status") != "completed" or t.get("returncode") not in (0, None)]
    mism = 0
    for t in tasks:
        rp = t.get("result_path")
        if rp and t.get("result_sha256") and fsha(rp) != t["result_sha256"]:
            mism += 1
    print(f"{s:20s} {m['started_utc']} {m['finished_utc']} {m['status']:9s} {len(tasks):5d} {len(failed):6d} {len(m.get('skipped_for_dependency', [])):7d} {mism:6d}")
    if prev_end is not None and m["started_utc"] < prev_end:
        print("   ORDER VIOLATION: starts before previous stage finished")
    prev_end = m["finished_utc"]
    if s.startswith("train") or s.startswith("evaluate"):
        cap = m.get("caps", {}).get("stage_seconds")
        print(f"   cap {cap}; max task seconds {max((t['seconds'] for t in tasks), default=0):.1f}; peak rss max {max((t.get('peak_rss_bytes') or 0) for t in tasks)/2**30:.3f} GiB")

# q1_gate file timing
for f in ("q1_start.json", "q1_gate.json"):
    import os, datetime
    print(f, "mtime UTC", datetime.datetime.fromtimestamp(os.path.getmtime(run / f), datetime.timezone.utc).isoformat())

L = json.loads(Path(ledger_p).read_text())
ents = L["entries"]
reg = [e for e in ents if e["run"] == run.name]
pre = [e for e in ents if e["run"] != run.name]
tot = sum(e["seconds"] for e in ents)
print("ledger cap", L["cap_seconds"], "= hours", L["cap_seconds"] / 3600)
print("ledger total seconds", round(tot, 3), "hours", round(tot / 3600, 4))
print("pre-registered seconds", round(sum(e["seconds"] for e in pre), 3))
byst = {}
for e in reg:
    byst[e["stage"]] = byst.get(e["stage"], 0) + e["seconds"]
for k, v in byst.items():
    print(f"  {k:28s} {v:10.3f}")
utc = [e["utc"] for e in ents]
print("ledger entries chronological:", utc == sorted(utc))
q1s = json.loads((run / "q1_start.json").read_text())
q1g = json.loads((run / "q1_gate.json").read_text())
proj = json.loads(Path(proj_p).read_text())
caps = json.loads((tree / "studies/p10s0/freeze/stage_caps.json").read_text())
print("projection sha256", fsha(proj_p))
# charged before Q1 = everything before train-q1 in ledger
idx = next(i for i, e in enumerate(ents) if e["stage"] == "train-q1")
charged_before_q1 = sum(e["seconds"] for e in ents[:idx])
print("charged before Q1 (mine)", charged_before_q1, "record", q1s["decision"]["charged_seconds"])
idx2 = next(i for i, e in enumerate(ents) if e["stage"] == "train-wx")
charged_at_gate = sum(e["seconds"] for e in ents[:idx2])
print("charged at Q1 gate (mine)", charged_at_gate, "record", q1g["headroom"]["charged_seconds"])
print("projection top-level keys", list(proj.keys())[:30])
json.dump({"q1_full_train_cap/2": caps["q1"]["full"]["train"] / 2, "q1_full_eval_cap/2": caps["q1"]["full"]["evaluate"] / 2,
           "wx_A5D": (caps["wx"]["A5-D"]["train"] + caps["wx"]["A5-D"]["evaluate"]) / 2,
           "probe_A5D": (caps["probe"]["A5-D"]["train"] + caps["probe"]["A5-D"]["evaluate"]) / 2}, sys.stdout)
print()
cap = L["cap_seconds"]
q1proj = (caps["q1"]["full"]["train"] + caps["q1"]["full"]["evaluate"]) / 2
res = caps["measured"]["reserve_analysis_report"]
need_q1 = charged_before_q1 + 2 * (q1proj + res)
print(f"before Q1: charged {charged_before_q1:.1f} + 2*(Q1 {q1proj:.1f} + reserve {res}) = {need_q1:.1f} <= {cap}: {need_q1 <= cap}; record required_seconds {q1s['decision']['required_seconds']}")
wx = q1g["headroom"]["wx_projection_seconds"]; pr = q1g["headroom"]["probe_projection_seconds"]
need_g = charged_at_gate + 2 * (wx + pr + res)
print(f"Q1 gate: charged {charged_at_gate:.1f} + 2*(wx {wx:.1f} + probe {pr:.1f} + reserve {res}) = {need_g:.1f} <= {cap}: {need_g <= cap}; margin {cap-need_g:.1f}")
print("wx proj from caps/2", (caps["wx"]["A5-D"]["train"] + caps["wx"]["A5-D"]["evaluate"]) / 2, "probe", (caps["probe"]["A5-D"]["train"] + caps["probe"]["A5-D"]["evaluate"]) / 2)
# check each completed stage against its cap
for s, key in (("train-q1", caps["q1"]["full"]["train"]), ("evaluate-q1", caps["q1"]["full"]["evaluate"]), ("train-wx", caps["wx"]["A5-D"]["train"]), ("evaluate-wx", caps["wx"]["A5-D"]["evaluate"]), ("train-probe", caps["probe"]["A5-D"]["train"]), ("evaluate-probe", caps["probe"]["A5-D"]["evaluate"]), ("gates", caps["gates"]), ("analyze", caps["analysis"]), ("report", caps["report"])):
    print(f"  {s:16s} charged {byst.get(s, 0):10.1f} cap {key:10.1f} ratio {byst.get(s, 0) / key:.3f} vs projection(cap/2) {2 * byst.get(s, 0) / key:.3f}")
