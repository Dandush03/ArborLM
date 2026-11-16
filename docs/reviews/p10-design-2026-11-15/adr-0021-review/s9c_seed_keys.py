"""S9c: structured seed scan. For every .json/.jsonl/.toml file under the given roots (skipping .git, .venv,
files > 200 MB), walk the parsed structure and collect integers stored under any key whose name contains
'seed' (case-insensitive), including integers nested in lists/dicts below such a key. For .py/.md files,
collect integers on lines that contain 'seed' (regex). Reports values in ADR-0021's declared ranges."""
import json
import os
import re
import sys
import tomllib

ROOTS = sys.argv[1:]
SKIP = {".git", ".venv", "__pycache__", "node_modules"}
def in_s1(v):
    return (210001 <= v <= 219999) or (921001 <= v <= 929999) or v in (2101, 2102, 2103, 2104, 2105, 2191, 2192)
hits, nfiles, errors = [], 0, 0
def walk(obj, path, under_seed, fpath):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, f"{path}.{k}", under_seed or ("seed" in str(k).lower()), fpath)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            walk(v, f"{path}[{i}]", under_seed, fpath)
    elif isinstance(obj, int) and not isinstance(obj, bool) and under_seed and in_s1(obj):
        hits.append((fpath, path, obj))
num = re.compile(r"(?<![\w.])(\d{4,6})(?![\w.])")
for root in ROOTS:
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            p = os.path.join(dp, fn)
            ext = os.path.splitext(fn)[1]
            try:
                if os.path.getsize(p) > 200_000_000:
                    continue
                if ext == ".json":
                    nfiles += 1
                    walk(json.load(open(p)), "", False, p)
                elif ext == ".jsonl":
                    nfiles += 1
                    for j, line in enumerate(open(p)):
                        if "seed" in line.lower():
                            walk(json.loads(line), f"L{j+1}", False, p)
                elif ext == ".toml":
                    nfiles += 1
                    walk(tomllib.load(open(p, "rb")), "", False, p)
                elif ext in (".py", ".md", ".txt", ".sh"):
                    nfiles += 1
                    for j, line in enumerate(open(p, errors="ignore")):
                        if "seed" in line.lower():
                            for m in num.finditer(line):
                                v = int(m.group(1))
                                if in_s1(v):
                                    hits.append((p, f"L{j+1}: {line.strip()[:120]}", v))
            except Exception:
                errors += 1
print(f"files parsed: {nfiles}; unreadable/unparsable: {errors}")
print(f"hits in ADR-0021 ranges (210001-219999, 921001-929999, init 2101-2105, 2191, 2192): {len(hits)}")
for h in hits[:200]:
    print(" ", h)
