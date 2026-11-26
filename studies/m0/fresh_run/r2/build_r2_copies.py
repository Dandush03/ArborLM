"""Builds the R2 run copies (units R2a, R2b) from `git show b78e58b1:<path>` by exact line operations, and writes COPIES.md.
Run from the worktree root: PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/r2/build_r2_copies.py
Refuses to overwrite an existing file. Standard library only. Self-check, not independent review."""
from __future__ import annotations

import difflib
import hashlib
import subprocess
import sys
from pathlib import Path

COMMIT = "b78e58b1"
REV = "docs/reviews/m0-lineage-decision-2026-11-25/"
OUT = Path("studies/m0/fresh_run/r2")
ENV = "M0_FR_TAG"
GET = '__import__("os").environ["%s"]' % ENV
GET_F = "__import__('os').environ['%s']" % ENV

# (original path, copy name, [(kind, op, original line text, replacement or None)]); op 'sub' replaces a whole line, 'del' deletes it.
SPECS = [
    ("studies/m0/r2_fix4_battery.py", "r2_fix4_battery.py", [
        ("S1", "sub", '    tag = "a4r2" if seeds == "a4" else "fix4"',
         '    tag = "a4r2" if seeds == "a4" else ' + GET),
    ]),
    (REV + "final_r2/f_rules.py", "f_rules.py", [
        ("S1", "sub", '        rtr = random.Random(f"finalr2|{lid}|{lv}|5")',
         '        rtr = random.Random(f"{' + GET_F + '}|{lid}|{lv}|5")'),
        ("S1", "sub", '        rte = random.Random(f"finalr2|{lid}|{lv}|6")',
         '        rte = random.Random(f"{' + GET_F + '}|{lid}|{lv}|6")'),
    ]),
    (REV + "final_r2/f_rules_new.py", "f_rules_new.py", [
        ("S1", "sub", '        rte = random.Random(f"finalr2|{lid}|{lv}|6")',
         '        rte = random.Random(f"{' + GET_F + '}|{lid}|{lv}|6")'),
    ]),
]

# S2(b) on f_new_heur.py: delete exactly the decorated entries of lineages not on the survivor list (ruling R-48): the line ranges
# below are 1-based, inclusive, of the original; each is checked against its first line.
NEW_DELETIONS = [
    (56, 65, '@rule("interval_scheduling", "(cue) fewest clashes first (ties by end, then number)")'),
    (68, 73, '@rule("interval_scheduling", "(cue) keep every meeting that clashes with no shorter meeting")'),
    (76, 79, '@rule("digit_root", "(cue) digit sum once, last digit")'),
    (82, 85, '@rule("digit_root", "(cue) digit sum once, first digit")'),
]


def show(path: str) -> str:
    return subprocess.run(["git", "show", f"{COMMIT}:{path}"], check=True, capture_output=True, text=True).stdout


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    records = []
    specs = [(p, n, ops) for p, n, ops in SPECS]
    lines_new = show(REV + "final_r2/f_new_heur.py").split("\n")
    specs.append((REV + "final_r2/f_new_heur.py", "f_new_heur.py", None))
    for path, name, ops in specs:
        orig = show(path)
        lines = orig.split("\n")
        kinds: list[tuple[str, int]] = []  # (kind, 1-based original line)
        if ops is None:
            drop = set()
            for a, b, first in NEW_DELETIONS:
                assert lines[a - 1] == first, (a, lines[a - 1])
                for i in range(a, b + 1):
                    drop.add(i)
                    kinds.append(("S2b", i))
            new_lines = [ln for i, ln in enumerate(lines, 1) if i not in drop]
        else:
            new_lines = list(lines)
            for kind, op, text, rep in ops:
                hits = [i for i, ln in enumerate(lines) if ln == text]
                assert len(hits) == 1, (name, text, hits)
                new_lines[hits[0]] = rep
                kinds.append((kind, hits[0] + 1))
        copy = "\n".join(new_lines)
        dest = OUT / name
        if dest.exists():
            sys.exit(f"{dest} exists; not overwriting")
        dest.write_text(copy)
        diff = list(difflib.unified_diff(orig.split("\n"), new_lines, f"a/{path}", f"b/{dest}", n=0, lineterm=""))
        records.append((path, name, sha(orig), sha(copy), diff, kinds))
    md = ["# R2 run copies (units R2a, R2b)", "",
          f"Originals are the files at `{COMMIT}` (`git show {COMMIT}:<path>`). Built by `build_r2_copies.py` by exact line operations; each diff is `-U0`.",
          f"Environment variable read by every S1 line: `{ENV}`; its value is the decimal text of the unit's `tag` seed integer (run plan).",
          "No S2a copy, no S3 copy and no S4 edit is made (reasons below). Self-check, not independent review.", ""]
    for path, name, so, sc, diff, kinds in records:
        md += [f"## `{OUT}/{name}`", "", f"- original: `{path}`", f"- original SHA-256: `{so}`", f"- copy SHA-256: `{sc}`", "", "```diff", *diff, "```", ""]
        kk: dict[str, list[int]] = {}
        for k, i in kinds:
            kk.setdefault(k, []).append(i)
        for k, ii in kk.items():
            md.append(f"- {k}: original line(s) {', '.join(map(str, ii))}")
        md.append("")
    md += [
        "## Kinds not used, and why", "",
        "- S2a: not needed. `r2_fix4_battery.py` takes its lineages from `--only` and `f_rules.py` from argv[3] (names without `R2.`); the run plan gives the 17 survivors there.",
        "- S3: not needed. No absolute or scratch path in the four files; `REV` of `f_rules.py` is relative to the working directory, which the plan sets to the worktree root (R-49).",
        "- S4: no edit. `f_rules_new.py` has `from f_new_heur import NEW` (lines 24 and 54). Run as a file from `studies/m0/fresh_run/r2/`, its own directory is `sys.path[0]`, so the line resolves to the copy `f_new_heur.py` next to it (UNITS.md D4 and REPORT D4). The plan's `PYTHONPATH` is the worktree root alone, so the original directory `final_r2/` is not on the path. Verified in the smoke execution by the import of the copy (see the report).",
        "- Import of `studies.m0.*` modules is untouched: none of them is copied.",
        "- Each S1 line uses `__import__(\"os\")` inline so that no import line is added.",
        "- S2b on `f_new_heur.py`: only the four decorated entries (decorator line through the last body line) of `interval_scheduling` and `digit_root` are deleted; the blank lines around them are left, and the helper `_meet` stays (it is not an entry).",
        ""]
    Path(OUT / "COPIES.md").write_text("\n".join(md))


if __name__ == "__main__":
    main()
