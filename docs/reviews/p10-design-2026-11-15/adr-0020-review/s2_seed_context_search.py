"""Seed-context search (attempt 2; attempt 1 = s1_seed_search.py, failed on hash false positives).

Two methods:
  (J) JSON / JSONL: parse; collect every int (or list of ints) stored under a key whose name contains
      "seed" (case-insensitive), at any depth. Also any int under keys "base", "init", "draw_base".
  (T) Other text files (.py .toml .md .txt .log .csv .sh .yaml .diff): lines containing "seed"
      (case-insensitive); integers delimited by non-[0-9A-Za-z_.] characters.
Reports, per namespace, the distinct values found and example locations.

Usage: python -I s2_seed_context_search.py ROOT [ROOT ...]
"""

import json
import os
import re
import sys
from collections import defaultdict

TEXT_EXT = {".py", ".toml", ".md", ".txt", ".log", ".csv", ".sh", ".yaml", ".yml", ".diff",
            ".stdout", ".stderr", ".cfg", ".ini"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
INT = re.compile(r"(?<![0-9A-Za-z_.])([0-9]{4,6})(?![0-9A-Za-z_.])")
SEEDWORD = re.compile(r"seed", re.I)

NAMESPACES = [
    ("S0 registered+reserve data 200001-201499", 200001, 201499),
    ("S0 rest of 200001-209999 (pipeline 209001+, rehearsal 209101+)", 201500, 209999),
    ("S0 init 2001-2002", 2001, 2002),
    ("S0 pipeline/rehearsal init 2091-2092", 2091, 2092),
    ("S0 tests 920001-920999", 920001, 920999),
    ("S1 data 210001-219999", 210001, 219999),
    ("S1 init 2101-2105, 2191-2192", 2101, 2105),
    ("S1 cal/reh init 2191-2192", 2191, 2192),
    ("S1 tests 921001+ (to 929999)", 921001, 929999),
    ("S2 220001-229999", 220001, 229999),
    ("P9-II 190001-191599", 190001, 191599),
    ("P9-II init 1891,1901,1902", 1891, 1891),
    ("P9-II init 1901-1902", 1901, 1902),
    ("P9-II tests 910001-919999", 910001, 919999),
]


def ns_of(n: int) -> list[str]:
    return [name for name, lo, hi in NAMESPACES if lo <= n <= hi]


found: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))


def note(n: int, where: str) -> None:
    for name in ns_of(n):
        lst = found[name][n]
        if len(lst) < 3:
            lst.append(where)


def walk_json(obj: object, path: str, seedctx: bool) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            kk = str(k)
            ctx = seedctx or bool(SEEDWORD.search(kk)) or kk in ("base", "init", "draw_base")
            walk_json(v, path + "/" + kk, ctx)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            walk_json(v, path, seedctx)
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, int) and seedctx:
        note(obj, path)
    elif isinstance(obj, str) and seedctx:
        for m in INT.finditer(obj):
            note(int(m.group(1)), path + " (str)")


def main() -> None:
    nfiles = 0
    for root in sys.argv[1:]:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                p = os.path.join(dp, fn)
                ext = os.path.splitext(fn)[1].lower()
                try:
                    if os.path.getsize(p) > 100_000_000:
                        continue
                    if ext == ".json":
                        nfiles += 1
                        with open(p, encoding="utf-8", errors="replace") as fh:
                            try:
                                walk_json(json.load(fh), p, False)
                            except json.JSONDecodeError:
                                pass
                    elif ext == ".jsonl":
                        nfiles += 1
                        with open(p, encoding="utf-8", errors="replace") as fh:
                            for i, line in enumerate(fh):
                                if i > 20000:
                                    break
                                if "seed" not in line.lower():
                                    continue
                                try:
                                    walk_json(json.loads(line), f"{p}#L{i+1}", False)
                                except json.JSONDecodeError:
                                    pass
                    elif ext in TEXT_EXT:
                        nfiles += 1
                        with open(p, encoding="utf-8", errors="replace") as fh:
                            for ln, line in enumerate(fh, 1):
                                if SEEDWORD.search(line):
                                    for m in INT.finditer(line):
                                        note(int(m.group(1)), f"{p}:{ln}")
                except OSError as e:
                    print("SKIP", p, e)
    print(f"files scanned: {nfiles}")
    for name, _, _ in NAMESPACES:
        vals = found.get(name, {})
        print(f"\n[{name}] distinct values in seed context: {len(vals)}")
        for v in sorted(vals)[:12]:
            print(f"   {v}: {vals[v][0]}")


if __name__ == "__main__":
    main()
