# ruff: noqa
"""Task 1: integrity of attempt 2. Manifests, task counts, identities, snapshot completeness, chance interval check."""
import collections, glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from auditlib import RUN, chance_interval, load_cells, load_plan, U_P_ROW, U_L

plan = load_plan()
ident = plan["identity"]
print("freeze identity", json.dumps(ident))
print("chance intervals 2048/8192/32768:", chance_interval(2048), chance_interval(8192), chance_interval(32768), " (ADR: [34,100] [192,325] [894,1159])")

bad = 0
for st in ("train", "evaluate", "timing", "simulate", "analyze", "report"):
    m = json.load(open(f"{RUN}/{st}/manifest.json"))
    c = collections.Counter(t["status"] for t in m["tasks"])
    idok = m["identity"] == ident
    print(f"stage {st:9s} status={m['status']:10s} tasks={len(m['tasks']):4d} statuses={dict(c)} identity==freeze:{idok} started={m['started_utc']} finished={m['finished_utc']}")
    for t in m["tasks"]:
        if t["status"] != "completed":
            print("   NOT COMPLETED:", t["label"], t["status"], t["reason"], t["returncode"], round(t["seconds"], 3))
gates = json.load(open(f"{RUN}/gates.json"))
print("gates passed:", {k: v for k, v in gates.items() if k.endswith("_passed")}, "identity==freeze:", gates.get("identity") == ident)

cells = load_cells()
main = {k: v for k, v in cells.items() if k[1] != "F-OQ-IVF"}
print("cell dirs:", len(main), "kinds:", collections.Counter(k[0] for k in main), "views incl. F-OQ-IVF (P only):", sum(1 for k in cells if k[0] == "P"))
# expected snapshot grid from section 5.4 (excluding MC extras, which are checked as a superset)
for k, c in sorted(main.items()):
    t = c["meta"]
    if t["status"] != "completed":
        print("TRAIN NOT COMPLETED", c["label"]); bad += 1
    if t["identity"] != ident:
        print("TRAIN IDENTITY DIFFERS", c["label"]); bad += 1
    for u, idt in c["evals_identity"].items():
        if idt != ident:
            print("EVAL IDENTITY DIFFERS", c["label"], u); bad += 1
    arm, f, n = k[1], k[2], k[3]
    up = U_P_ROW[f]
    if t["u_p"] != up:
        print("U_P differs", c["label"], t["u_p"], up); bad += 1
    if arm == "R2":
        run = up
    elif (f, n) in U_L:
        run = U_L[(f, n)]
    else:
        run = 6 * up
    if t["run_updates"] != run:
        print("RUN differs", c["label"], t["run_updates"], run); bad += 1
    grid = {up // 16, up // 8, up // 4, up // 2, up, 2 * up, 4 * up}
    grid = {u for u in grid if u <= run} | {run // 2, run}
    if (f, n) in U_L:
        cands = [65536, 98304, 131072, 196608, 262144, 393216] if n == 1024 else [131072, 196608, 262144, 393216, 524288, 786432]
        grid |= {32768, 49152} | {x for x in cands if x <= run}
    have = set(c["snap"])
    if not grid <= have:
        print("MISSING SNAPSHOTS", c["label"], sorted(grid - have)); bad += 1
    if set(t["snapshots"]) != have:
        print("train snapshot list != eval dirs", c["label"], sorted(set(t["snapshots"]) ^ have)); bad += 1
    if not all(c["snap"][u][p]["n"] == f for u in have for p in ("A", "B")):
        print("panel n != facts", c["label"]); bad += 1
print("integrity problems:", bad)
# draws: the same facts table? each replicate's data manifest hash vs freeze
for d in range(1, 6):
    p = glob.glob(f"{RUN}/generate-p10s1-draw-{d}/*.json")
    print("draw", d, "generate files:", [os.path.basename(x) for x in p][:4])
