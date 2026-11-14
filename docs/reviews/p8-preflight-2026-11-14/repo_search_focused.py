"""Focused search for prior use/reservation of validation ranks 3072..4095 (auditor role, claude-opus-5-5).
Run from the worktree: uv run --locked python -I docs/reviews/p8-preflight-2026-11-14/repo_search_focused.py
(1) every tracked or untracked-not-ignored text file (excluding this review folder) whose line has a
    whole-token 3072..4096 AND a validation/panel/eval word on the same line;
(2) every JSON record under results/ and the main checkout's experiments/ with a validation-side rank
    list/ordinal >= 3072 (lists of dicts carrying 'rank' + 'chunk_sha256' are classified by file name);
(3) rank-range strings like 3072..., 3072-, [3072 anywhere in docs/, results/, src/, configs/, tests/."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
SELF = "docs/reviews/p8-preflight-2026-11-14/"
files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True, check=True).stdout.split("\n")
files = [f for f in files if f and not f.startswith(SELF)]
num = re.compile(r"(?<![0-9A-Za-z])(30[7-9][0-9]|3[1-9][0-9]{2}|40[0-8][0-9]|409[0-6])(?![0-9A-Za-z])")
ctx = re.compile(r"valid|panel|held[- ]?out|evaluat|stream b|window", re.I)
rng = re.compile(r"(3072|3584)\s*(\.\.|–|-|,|:)\s*[0-9]{4}|\[\s*(3072|3584)\s*,")
print("## (1) whole-token 3072..4096 with validation/panel context on the same line")
n1 = 0
for f in files:
    p = ROOT / f
    try:
        text = p.read_text(errors="strict")
    except Exception:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if num.search(line) and ctx.search(line):
            n1 += 1
            if n1 <= 400:
                print(f"{f}:{i}: {line.strip()[:240]}")
print("count (1):", n1)
print("\n## (3) rank-range strings starting at 3072 or 3584")
n3 = 0
for f in files:
    try:
        text = (ROOT / f).read_text(errors="strict")
    except Exception:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if rng.search(line):
            n3 += 1
            print(f"{f}:{i}: {line.strip()[:240]}")
print("count (3):", n3)
print("\n## (2) JSON records: validation-side rank ordinals/intervals >= 3072")
roots = [ROOT / "results", Path("/Users/daniellaloush/dandush03/ArborLM/experiments")]
n2 = 0
scanned = 0
for r in roots:
    for p in sorted(r.rglob("*.json")):
        scanned += 1
        try:
            d = json.loads(p.read_text())
        except Exception as e:
            print("UNREADABLE", p, type(e).__name__)
            continue
        found = []
        def walk(x, path):
            if isinstance(x, dict):
                if "rank" in x and "chunk_sha256" in x and isinstance(x["rank"], int) and x["rank"] >= 3072:
                    found.append(("/".join(path), x["rank"]))
                    return
                for k, v in x.items():
                    walk(v, path + [str(k)])
            elif isinstance(x, list):
                if path and re.search(r"valid|panel|eval|measured|scientific", path[-1], re.I) and len(x) == 2 and all(isinstance(i, int) for i in x) and max(x) > 3072:
                    found.append(("/".join(path), x))
                    return
                for i, v in enumerate(x):
                    walk(v, path + [str(i)])
        walk(d, [])
        if found:
            ranks = [v for _, v in found if isinstance(v, int)]
            other = [f for f in found if not isinstance(f[1], int)]
            n2 += 1
            print(p, "| selection-entry ranks >=3072:", (min(ranks), max(ranks), len(ranks)) if ranks else None,
                  "| first path:", found[0][0][:80], "| intervals:", other[:3])
print("JSON files scanned:", scanned, "files with hits:", n2)
