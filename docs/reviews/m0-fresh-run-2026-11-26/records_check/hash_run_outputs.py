"""Hash the fresh run's output files on disk and compare with the committed hash records (bytes only; no file is parsed).

Usage (from the implementation worktree root):
  PYTHONDONTWRITEBYTECODE=1 uv run --locked python <this> --root . --out <file>
"""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
root = Path(a.root).resolve()
res = {}
for i in (1, 2, 3):
    rel = f"docs/reviews/m0-fresh-run-2026-11-26/run/hashes_seed{i}.json"
    d = json.loads((root / rel).read_text())
    n = ok = 0
    bad, missing, attempts, extra = [], [], 0, []
    for unit, u in sorted(d["units"].items()):
        for at in u["attempts"]:
            attempts += 1
            base = Path(at["dir"])
            listed = set()
            for name, meta in sorted(at["files"].items()):
                n += 1
                f = base / name
                listed.add(f.resolve())
                if not f.is_file():
                    missing.append(str(f))
                elif hashlib.sha256(f.read_bytes()).hexdigest() == meta["sha256"] and f.stat().st_size == meta["size"]:
                    ok += 1
                else:
                    bad.append(str(f))
            if base.is_dir():
                for f in base.rglob("*"):
                    if f.is_file() and f.resolve() not in listed:
                        extra.append(str(f.relative_to(base.parent.parent)))
    res[rel] = {"files_listed": n, "equal": ok, "differ": bad, "missing": missing, "attempts": attempts,
                "files_on_disk_not_listed": sorted(extra)[:50], "n_files_on_disk_not_listed": len(extra)}
Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
print({k: (v["files_listed"], v["equal"], len(v["differ"]), len(v["missing"]), v["n_files_on_disk_not_listed"]) for k, v in res.items()})
