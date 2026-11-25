# ruff: noqa
"""Structural duplicates inside the fixture files (same problem after removing names/settings, and after removing presentational order)."""
import json, sys
FXDIR = sys.argv[1]; sys.argv = sys.argv[:1]  # attempt 1 failed: capacity_audit reads argv[1] as M
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capacity_audit import struct_key, canon_key, norm
fx = Path(FXDIR)
for f in sorted(fx.glob("M1.*.jsonl")):
    T, S, C = defaultdict(list), defaultdict(list), defaultdict(list)
    for l in f.read_text().splitlines():
        it = json.loads(l)
        T[norm(it["question"])].append(it["id"]); S[struct_key(it["lineage"], it["structured"])].append(it["id"]); C[canon_key(it["lineage"], it["structured"])].append(it["id"])
    d = lambda X: [v for v in X.values() if len(v) > 1]
    if d(T) or d(S) or d(C):
        print(f.stem, "text-dups", d(T), "| struct-dups", d(S), "| order-canonical dups", d(C))
