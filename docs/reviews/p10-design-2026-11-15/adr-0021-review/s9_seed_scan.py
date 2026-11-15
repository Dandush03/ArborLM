"""S9: scan repository text, the main checkout and experiments/ for numeric tokens in ADR-0021's
declared seed ranges. Pure read; prints every hit with file and line (first 3 per file)."""
import os
import re
import sys

ROOTS = sys.argv[1:]
RANGES = {
    "registered bases+offsets 210001-210460": (210001, 210460),
    "whole 210000-219999 block": (210000, 219999),
    "calibration/rehearsal 219001-219260": (219001, 219260),
    "tests 921001-921999": (921001, 921999),
}
SMALL = {2101, 2102, 2103, 2104, 2105, 2191, 2192}
EXT = {".py", ".toml", ".json", ".jsonl", ".md", ".csv", ".txt", ".tsv", ".yaml", ".yml", ".log"}
SKIP = {".git", ".venv", "__pycache__", "node_modules"}
tok = re.compile(r"(?<![\d.])(\d{4,6})(?![\d.])")
hits = {k: [] for k in RANGES}
small_hits = []
nfiles = 0
for root in ROOTS:
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            if os.path.splitext(fn)[1] not in EXT:
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > 60_000_000:
                    continue
                with open(p, encoding="utf-8", errors="ignore") as f:
                    nfiles += 1
                    for i, line in enumerate(f, 1):
                        for m in tok.finditer(line):
                            v = int(m.group(1))
                            if "seed" not in line.lower() and "base" not in line.lower():
                                continue
                            for k, (lo, hi) in RANGES.items():
                                if lo <= v <= hi:
                                    hits[k].append((p, i, v, line.strip()[:140]))
                            if v in SMALL and ("seed" in line.lower()):
                                small_hits.append((p, i, v, line.strip()[:140]))
            except OSError:
                pass
print("files scanned:", nfiles)
for k, lst in hits.items():
    files = sorted({h[0] for h in lst})
    print(f"\n== {k}: {len(lst)} hits in {len(files)} files")
    for fpath in files[:40]:
        sub = [h for h in lst if h[0] == fpath][:3]
        for h in sub:
            print(f"  {h[0]}:{h[1]} value={h[2]} | {h[3]}")
print(f"\n== small init seeds {sorted(SMALL)} on lines mentioning 'seed': {len(small_hits)}")
for h in small_hits[:60]:
    print(f"  {h[0]}:{h[1]} value={h[2]} | {h[3]}")
