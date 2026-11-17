# Independent scan of the S0 rehearsal, gates and pipeline-check records (read-only). No arborlm/studies imports.
import json, re, sys, hashlib
from pathlib import Path
E = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
ID_9CCA = {"source_sha256": "6e56d4c7088388d86930167d559c168fdcaba0e6aa267228de079c9d7a96f408", "spec_sha256": "bb3d213e8a44b5e68034ea23f70093d174d5ab4c73420f026a84fdb3db64237b", "config_sha256": "6261db9259444a6f83ffe133bfaa7896f7b9afde654422883179a4093e5c443d", "frozen_source_sha256": "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507"}
FORBID = re.compile(r"loss\"|accurac|\"acc|correct|logit|recall|success|_auc|\"auc|margin|answer", re.I)
EXPECTED_ITEMS = sorted(
    [f"REH-{a}-{ct}-main" for a in ("A0", "A1", "A5-D", "A6", "A7") for ct in ("2K4K", "8K16K")]
    + [f"REH-{a}-8K4K-main" for a in ("A0", "A5-D", "A6")]
    + [f"REH-A2-{ct}-{p}" for ct in ("2K4K", "8K16K") for p in ("pre", "post")]
    + [f"REH-WX-{c}-{ct}-main" for c in ("A5-D", "A1") for ct in ("2K4K", "8K16K")]
    + [f"REH-{a}-32K64K-main" for a in ("A5-D", "A1", "A6")])
out = {"expected_items_n": len(EXPECTED_ITEMS)}
def walk_keys(o, prefix=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield prefix + k
            yield from walk_keys(v, prefix + k + ".")
    elif isinstance(o, list):
        for v in o:
            yield from walk_keys(v, prefix)
for name in ("alone", "busy"):
    d = E / f"P10S0H-rehearsal-{name}-20261115"
    items = sorted(p.name for p in (d / "rehearsal").iterdir())
    man = json.loads((d / "rehearse" / "manifest.json").read_text())
    r = {"items_n": len(items), "items_equal_expected": items == EXPECTED_ITEMS, "missing": sorted(set(EXPECTED_ITEMS) - set(items)), "extra": sorted(set(items) - set(EXPECTED_ITEMS)),
         "manifest_status": man["status"], "manifest_tasks": len(man["tasks"]), "tasks_completed": sum(t["status"] == "completed" for t in man["tasks"]), "manifest_identity_eq_9cca808": man["identity"] == ID_9CCA}
    keysets, ids_ok, busy, forb, files, loads, upd = {}, True, set(), [], 0, [], set()
    for f in sorted((d / "rehearsal").rglob("*")):
        if not f.is_file():
            continue
        files += 1
        txt = f.read_text()
        rec = json.loads(txt)
        keysets.setdefault(f.name, set()).update(rec.keys())
        ids_ok &= rec.get("identity") == ID_9CCA
        if "busy_processes" in rec:
            busy.add(rec["busy_processes"])
        if "load_average" in rec:
            loads.append(rec["load_average"][0])
        if f.name == "rehearsal.json":
            upd.add(rec["updates"])
        for k in walk_keys(rec):
            if FORBID.search('"' + k.split(".")[-1] + '"'):
                forb.append((str(f.relative_to(d)), k))
    # logs: scan for loss/accuracy words
    logwords = []
    for f in sorted((d / "rehearse").glob("*.log")):
        for line in f.read_text(errors="replace").splitlines():
            if re.search(r"loss|accura|recall", line, re.I):
                logwords.append((f.name, line[:160]))
    r.update({"record_files": files, "keys_by_file": {k: sorted(v) for k, v in keysets.items()}, "record_identity_eq_9cca808": ids_ok, "busy_processes_values": sorted(busy), "forbidden_keys": forb, "log_lines_with_loss_or_accuracy": logwords[:20], "n_log_lines_flagged": len(logwords), "updates_values": sorted(upd), "load_avg_1min_min_max": [min(loads), max(loads)] if loads else None})
    out[name] = r
# gates
g = json.loads((E / "P10S0G-rehearsal-gates-20261115/gates.json").read_text())
gm = json.loads((E / "P10S0G-rehearsal-gates-20261115/gates/manifest.json").read_text())
genm = json.loads((E / "P10S0G-rehearsal-gates-20261115/generate-p10s0-rehearsal/manifest.json").read_text())
out["gates"] = {k: g.get(k) for k in ("g1_passed", "g2_passed", "g4_passed", "g5_passed", "g6_passed", "g9_passed", "g10_passed", "dry", "profile", "seed_set", "mode", "timing")}
out["gates"]["harness_errors"] = g.get("harness_errors"); out["gates"]["g4_defects"] = g.get("g4_defects")
out["gates"]["g10"] = {k: v for k, v in g["g10"].items() if k in ("passed", "auditor_script_run", "auditor_script_sha256", "pinned", "script_sha256", "candidates", "table_cell", "cited_cell")} | {"keys": sorted(g["g10"].keys())}
out["gates"]["identity_eq_9cca808"] = g.get("identity") == ID_9CCA
out["gates"]["keys"] = sorted(g.keys())
out["gates_manifest"] = {"status": gm["status"], "mode": gm["mode"], "tasks": [(t["label"], t["status"], t["returncode"], t["seconds"]) for t in gm["tasks"]], "identity_eq_9cca808": gm["identity"] == ID_9CCA, "caps": gm.get("caps")}
out["generate_manifest"] = {"status": genm["status"], "mode": genm["mode"], "stage": genm["stage"], "tasks": [(t["label"], t["status"], t["seconds"], t["peak_rss_bytes"]) for t in genm["tasks"]], "sum_task_seconds": sum(t["seconds"] for t in genm["tasks"]), "identity_eq_9cca808": genm["identity"] == ID_9CCA, "caps": genm.get("caps")}
dm = json.loads((E / "P10S0G-rehearsal-gates-20261115/draws/p10s0-rehearsal/data_manifest.json").read_text())
out["rehearsal_data_manifest"] = {"g1_passed": dm.get("g1_passed"), "g1_by_fact_set": dm.get("g1_by_fact_set"), "seed_set": dm.get("seed_set"), "seeds": dm.get("seeds"), "dry": dm.get("dry"), "profile": dm.get("profile")}
# pipeline check
K = next(E.glob("P10S0K-*"))
pk = {}
for st in ("train-check", "evaluate-check"):
    m = json.loads((K / st / "manifest.json").read_text())
    pk[st] = {"status": m["status"], "mode": m["mode"], "tasks": [(t["label"], t["status"], t["returncode"]) for t in m["tasks"]], "identity": m["identity"]}
out["pipeline_check"] = pk
cells = {}
for c in sorted((K / "cells").iterdir()):
    ev = sorted((c / "eval").rglob("*.json"))
    cells[c.name] = {"eval_files": [str(p.relative_to(c)) for p in ev]}
    for p in ev:
        rec = json.loads(p.read_text())
        flat = {k: v for k, v in rec.items() if isinstance(v, (int, float, str, bool)) or v is None}
        cells[c.name][p.name] = {k: flat[k] for k in flat if re.search(r"acc|chance|seed|draw|slots|facts|updates|n_|count", k, re.I)}
    tj = json.loads((c / "train.json").read_text())
    cells[c.name]["train_keys"] = sorted(tj.keys()); cells[c.name]["updates"] = tj.get("updates") or tj.get("updates_done"); cells[c.name]["seed_set"] = tj.get("seed_set")
out["pipeline_cells"] = cells
json.dump(out, sys.stdout, indent=1, default=str)
