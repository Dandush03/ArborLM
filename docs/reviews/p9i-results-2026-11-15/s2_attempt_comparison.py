"""S2 (auditor, Opus 5.5): own re-check of the pre-training comparisons of attempt 2 with attempt 1 (the
lead's C4-C8 of ADR-0017 section 15.8, whose output is not in the committed folder), and a scan of the run
directory for any sign of a re-run (extra files, extra snapshot or eval directories, more than one stage
manifest, log lines of a second start). Imports nothing from the study code.

Usage: s2_attempt_comparison.py ATTEMPT1_RUN_DIR ATTEMPT2_RUN_DIR
"""
import hashlib
import json
import sys
from pathlib import Path

A1, A2 = Path(sys.argv[1]), Path(sys.argv[2])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


g1, g2 = json.loads((A1 / "gates.json").read_text()), json.loads((A2 / "gates.json").read_text())
print("gates.json top-level keys attempt 1:", sorted(g1))
print("gates.json top-level keys attempt 2:", sorted(g2))
for k in ("g2", "controls", "restoration", "g1_passed", "g2_passed"):
    print(f"{k:12s} identical: {g1.get(k) == g2.get(k)}")
print("attempt 1 g4_passed / defects:", g1.get("g4_passed"), g1.get("g4_defects"))
print("attempt 2 g4_passed / defects:", g2.get("g4_passed"), g2.get("g4_defects"))
print("gradient reach attempt 2:", {a: (r["all_reached"], r["stray"], r["trainable"]) for a, r in g2["gradient_reach"].items()})
print("gradient reach trainable counts identical to attempt 1:",
      {a: r["trainable"] for a, r in g1["gradient_reach"].items()} == {a: r["trainable"] for a, r in g2["gradient_reach"].items()})
for arm in ("N", "BB"):
    for sub in ("first", "resumed", "straight"):
        d1 = A1 / "g4_restore" / arm / "restore_check" / sub
        d2 = A2 / "g4_restore" / arm / "restore_check" / sub
        f1 = sorted(p.relative_to(d1) for p in d1.rglob("*") if p.is_file())
        f2 = sorted(p.relative_to(d2) for p in d2.rglob("*") if p.is_file())
        same = {str(f): sha(d1 / f) == sha(d2 / f) for f in f1 if f in f2}
        print(f"g4_restore {arm}/{sub}: files {len(f1)} vs {len(f2)}; identical bytes: {sum(same.values())}/{len(same)}; differing: {[k for k, v in same.items() if not v]}")
# run directory scan
print()
for st in ("generate", "gates", "train", "evaluate", "analyze", "report"):
    files = sorted(p.name for p in (A2 / st).iterdir())
    print(f"{st:9s} files: {len(files)} manifest count: {sum(1 for f in files if f.startswith('manifest'))}")
cells = sorted((A2 / "cells").iterdir())
extra = []
for d in cells:
    names = sorted(p.name for p in d.iterdir())
    if names != ["eval", "snapshots", "train.json", "updates.jsonl"]:
        extra.append((d.name, names))
print("cells with files other than eval/, snapshots/, train.json, updates.jsonl:", extra)
for log in sorted((A2 / "train").glob("*.log"))[:3] + sorted((A2 / "evaluate").glob("*.log"))[:2]:
    print("--", log.relative_to(A2), "size", log.stat().st_size)
    print(log.read_text()[-600:])
starts = {}
for log in sorted((A2 / "train").glob("*.log")):
    t = log.read_text()
    starts[log.stem] = t.count("Traceback")
print("train logs with a traceback:", {k: v for k, v in starts.items() if v})
print("top-level run directory entries:", sorted(p.name for p in A2.iterdir()))
