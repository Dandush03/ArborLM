"""F5 (auditor, Opus 5.5): the attempt-1 values that a second attempt must reproduce, for the freeze record.

Reads the committed attempt-1 records (results/p9i-run-attempt1-2026-11-14/) and, from the kept run
directory, only file hashes of g4_restore/*/restore_check/first/snapshots/u0000016/* and the
``snapshot_sha256`` / ``run_updates`` / ``status`` fields of the restoration train.json files. It never
opens updates.jsonl (per-update losses) and prints no other train.json field.

Usage: uv run --locked python <this> <committed attempt-1 dir> <kept attempt-1 run dir>
"""
import hashlib
import json
import sys
from pathlib import Path

REC, RUN = Path(sys.argv[1]), Path(sys.argv[2])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canon(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


for f in ("data_manifest.json", "g1.json", "gates.json"):
    print(f"committed {f}: sha256 {sha(REC / f)}; kept run copy identical: {sha(REC / f) == sha(RUN / f)}")
dm = json.loads((REC / "data_manifest.json").read_text())
print("data_manifest sha256s block (14 entries expected):", len(dm["sha256s"]), "canonical sha256", canon(dm["sha256s"]))
for k, v in sorted(dm["sha256s"].items()):
    print(f"  {k:22} {v}")
print("data_manifest non-identity fields, canonical sha256:", canon({k: v for k, v in dm.items() if k != "identity"}))
print("  seed_set", dm["seed_set"], "| seeds canonical sha256", canon(dm["seeds"]), "| g1_passed", dm["g1_passed"], "| g1_failed_checks", dm["g1_failed_checks"])
g = json.loads((REC / "gates.json").read_text())
print("gates.json block digests (canonical JSON sha256):")
for k in ("g2", "controls", "restoration"):
    print(f"  {k:12} {canon(g[k])}")
print("  G2 primary (B101):", [(r["name"], r["correct"], r["interval"]) for r in g["g2"]["results"]])
rep = g["controls"]["no_memory_replicate"]
print("  no-memory replicate (B102):", {p: {n: rep[p][n]["correct"] for n in ("2048", "8192", "32768", "unseen")} for p in ("A", "B")})
print("  exact_accuracy:", g["controls"]["exact_accuracy"])
print("  restoration:", json.dumps(g["restoration"], sort_keys=True))
print("  gradient_reach trainable counts:", {a: r["trainable"] for a, r in sorted(g["gradient_reach"].items())})
print("  N-vs-R0a / initial identities all True on both parents:", all(all(v for k, v in e["n_against_r0a"].items() if isinstance(v, bool)) and all(e["initial_identities"].values()) for e in g["identity"]))
print("  g4_defects:", g["g4_defects"])
print("restoration snapshot files (u0000016 of the 'first' leg):")
for p in sorted((RUN / "g4_restore").glob("*/restore_check/first/snapshots/u0000016/*")):
    print(f"  {p.relative_to(RUN)}  {sha(p)}")
for p in sorted((RUN / "g4_restore").glob("*/restore_check/*/train.json")):
    t = json.loads(p.read_text())
    print(f"  {p.relative_to(RUN)}: snapshot_sha256 {t['snapshot_sha256']}, run_updates {t['run_updates']}, status {t['status']}")
