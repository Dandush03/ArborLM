"""P10-S0 independent integrity checks (auditor's own code; imports nothing from studies/ or arborlm).

Usage: python3 -I integrity.py <frozen tree dir (git archive of 579d332)> <run dir> <committed run record dir> <worktree>
"""
import hashlib, json, sys, tomllib, os, glob, collections
from pathlib import Path

tree, run, rec, wt = map(Path, sys.argv[1:5])


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canon(o):
    return (json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


out = collections.OrderedDict()
# --- expected identity from the frozen tree
h = {}
for p in sorted((tree / "studies/p10s0").glob("*.py")):
    h[f"studies/p10s0/{p.name}"] = fsha(p)
for p in sorted((tree / "studies/p10s0/launch").glob("*.sh")):
    h[f"studies/p10s0/launch/{p.name}"] = fsha(p)
for p in sorted((tree / "studies/p9ii").glob("*.py")):
    h[f"studies/p9ii/{p.name}"] = fsha(p)
for n in ("__init__", "classes", "core", "evaluate", "model", "report", "stages", "train"):
    h[f"studies/p9i/{n}.py"] = fsha(tree / "studies/p9i" / f"{n}.py")
for n in ("__init__", "controls", "core", "data", "evaluate", "model", "objective", "pool", "train"):
    h[f"studies/p9/{n}.py"] = fsha(tree / "studies/p9" / f"{n}.py")
src = hashlib.sha256(canon(h)).hexdigest()
base = tree / "src/arborlm"
fro = hashlib.sha256(canon({f"src/arborlm/{p.relative_to(base).as_posix()}": fsha(p) for p in sorted(base.rglob("*.py"))})).hexdigest()
spec = fsha(tree / "docs/decisions/ADR-0020-p10-s0-addressing-qualification.md")
cfg = hashlib.sha256(canon(tomllib.loads((tree / "configs/p10s0_qualification.toml").read_text()))).hexdigest()
expected = {"source_sha256": src, "frozen_source_sha256": fro, "spec_sha256": spec, "config_sha256": cfg}
out["expected_identity"] = expected

# --- every json record in the run directory that carries an identity
ids = collections.Counter()
bad = []
nrec = 0
for p in sorted(run.rglob("*.json")):
    try:
        d = json.loads(p.read_text())
    except Exception as e:
        bad.append((str(p), f"unreadable {e}"))
        continue
    stack = [d]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if "identity" in o and isinstance(o["identity"], dict) and "source_sha256" in o["identity"]:
                nrec += 1
                idt = {k: o["identity"].get(k) for k in expected}
                ids[json.dumps(idt, sort_keys=True)] += 1
                if idt != expected:
                    bad.append((str(p.relative_to(run)), idt))
            stack.extend(v for v in o.values() if isinstance(v, (dict, list)))
        elif isinstance(o, list):
            stack.extend(v for v in o if isinstance(v, (dict, list)))
out["identity_blocks_checked"] = nrec
out["distinct_identities"] = [json.loads(k) | {"count": c} for k, c in ids.items()]
out["identity_mismatches"] = bad[:20]
out["identity_mismatch_count"] = len(bad)

# --- byte identity of the committed record with the run directory
pairs = {}
for p in sorted(rec.rglob("*")):
    if p.is_file() and p.name != "README.md":
        rel = p.relative_to(rec)
        cand = [run / rel]
        if rel.parts[0] == "manifests":
            cand.append(run / rel.stem / "manifest.json")
        if rel.name == "ledger_after_run.json":
            cand += [run / "ledger.json", run.parent / "P10S0-ledger.json"]
        if rel.name in ("RESULTS.md", "results.json", "classes.csv"):
            cand += [run / "report" / rel.name, run / "results" / rel.name]
        if rel.name == "analysis.json":
            cand += [run / "analyze" / rel.name]
        found = [str(c.relative_to(run.parent)) for c in cand if c.exists() and fsha(c) == fsha(p)]
        pairs[str(rel)] = found or [f"NO BYTE-IDENTICAL COPY among {[str(c) for c in cand]}"]
out["byte_identity"] = pairs

# --- cell inventory
cells = sorted(d.name for d in (run / "cells").iterdir())
out["cells_total"] = len(cells)
by_block = collections.Counter(c.split("-")[0] for c in cells)
out["cells_by_block"] = dict(by_block)
status = collections.Counter()
missing_eval = []
for c in cells:
    t = json.loads((run / "cells" / c / "train.json").read_text())
    status[(t["status"], t.get("reason"))] += 1
    evs = list((run / "cells" / c / "eval").glob("*/eval.json"))
    if not evs:
        missing_eval.append(c)
out["train_status"] = {str(k): v for k, v in status.items()}
out["cells_without_eval"] = missing_eval
json.dump(out, sys.stdout, indent=1, default=str)
print()
