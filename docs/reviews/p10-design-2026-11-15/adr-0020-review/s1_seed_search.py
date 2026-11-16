"""S0 seed-namespace search (ADR-0020 review, item G).

Searches text files for the seed values ADR-0020 claims are unused:
  data 200001-209999 (registered 200001-201499, pipeline 209001+, rehearsal 209101+),
  init 2001, 2002, 2091, 2092, unit tests 920001-920999,
and, for the cross-reference check, S1 210001-219999 / 921001+, S2 220001-229999,
P9-II 190001-191599 / 910001+.

Usage: python -I s1_seed_search.py ROOT [ROOT ...]
Text files only (.py .toml .json .jsonl .md .txt .log .csv .sh .yaml .yml .diff .stdout .stderr).
For bare small integers (2001, 2002, 2091, 2092) a hit is reported only if the line also contains
"seed" (case-insensitive), because these integers occur as ordinary numbers.
"""

import os
import re
import sys
from collections import Counter, defaultdict

EXT = {".py", ".toml", ".json", ".jsonl", ".md", ".txt", ".log", ".csv", ".sh", ".yaml", ".yml",
       ".diff", ".stdout", ".stderr", ".cfg", ".ini"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache"}

BIG = re.compile(r"(?<![0-9.])(1[89][0-9]{4}|2[0-2][0-9]{4}|9[12][0-9]{4})(?![0-9])")
SMALL = re.compile(r"(?<![0-9.])(2001|2002|2091|2092)(?![0-9])")
SEEDWORD = re.compile(r"seed", re.I)


def bucket(n: int) -> str | None:
    if 200001 <= n <= 209999:
        return "S0 data 200001-209999"
    if 920001 <= n <= 920999:
        return "S0 tests 920001-920999"
    if 210001 <= n <= 219999:
        return "S1 210001-219999"
    if 921001 <= n <= 929999:
        return "S1 tests 921001+"
    if 220001 <= n <= 229999:
        return "S2 220001-229999"
    if 190001 <= n <= 191599:
        return "P9-II 190001-191599"
    if 910001 <= n <= 919999:
        return "P9-II tests 910001+"
    return None


def main() -> None:
    hits: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    small_hits: Counter[str] = Counter()
    small_examples: list[str] = []
    files = 0
    for root in sys.argv[1:]:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if os.path.splitext(fn)[1].lower() not in EXT:
                    continue
                path = os.path.join(dp, fn)
                try:
                    if os.path.getsize(path) > 200_000_000:
                        continue
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        files += 1
                        for ln, line in enumerate(fh, 1):
                            for m in BIG.finditer(line):
                                b = bucket(int(m.group(1)))
                                if b:
                                    hits[b][path] += 1
                                    if len(examples[b]) < 8:
                                        examples[b].append(f"{path}:{ln}: {line.strip()[:160]}")
                            if SMALL.search(line) and SEEDWORD.search(line):
                                small_hits[path] += 1
                                if len(small_examples) < 15:
                                    small_examples.append(f"{path}:{ln}: {line.strip()[:160]}")
                except OSError as e:
                    print("SKIP", path, e)
    print(f"text files scanned: {files}")
    for b in sorted(hits):
        print(f"\n[{b}] files with hits: {len(hits[b])}, total hits: {sum(hits[b].values())}")
        for e in examples[b]:
            print("   ", e)
    if not hits:
        print("\nno hit in any bucket")
    print(f"\n[small ints 2001/2002/2091/2092 on a line containing 'seed'] files: {len(small_hits)}")
    for e in small_examples:
        print("   ", e)


if __name__ == "__main__":
    main()
