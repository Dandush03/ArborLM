"""Writes COPIES.md for the R2 copies made by build_r2_copies.py (which built the four copies; its own COPIES.md draft used difflib, whose
alignment showed blank lines as changes in f_new_heur.py; this script supersedes that draft and uses `diff -U0`).
Originals are `git show b78e58b1:<path>`, written to a scratch directory given as argv[1] (must not exist yet), then diffed with `diff -U0`.
Hunk kinds are assigned by line numbers of the original, listed below. Standard library only. Self-check, not independent review."""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

COMMIT = "b78e58b1"
REV = "docs/reviews/m0-lineage-decision-2026-11-25/"
OUT = Path("studies/m0/fresh_run/r2")
# (original, copy, {original line number (hunk start, as in the -U0 header): kind})
ITEMS = [
    ("studies/m0/r2_fix4_battery.py", "r2_fix4_battery.py", {90: "S1 (string-seed tag `fix4` -> environment variable)"}),
    (REV + "final_r2/f_rules.py", "f_rules.py", {61: "S1 (string-seed tag `finalr2` -> environment variable, train and test lines)"}),
    (REV + "final_r2/f_rules_new.py", "f_rules_new.py", {29: "S1 (string-seed tag `finalr2` -> environment variable, test line)"}),
    (REV + "final_r2/f_new_heur.py", "f_new_heur.py", {
        56: "S2b (entries of `interval_scheduling`, rule 1: lineage not on the survivor list)",
        68: "S2b (entries of `interval_scheduling`, rule 2)",
        76: "S2b (entries of `digit_root`, rule 1: lineage not on the survivor list)",
        82: "S2b (entries of `digit_root`, rule 2)"}),
]


def main() -> None:
    scratch = Path(sys.argv[1])
    scratch.mkdir(parents=True, exist_ok=False)
    md = ["# R2 run copies (units R2a, R2b)", "",
          f"Originals are the files at `{COMMIT}` (`git show {COMMIT}:<path>`). Diffs are `diff -U0 original copy` (written by `build_r2_copies_md.py`; the copies were built by `build_r2_copies.py`).",
          "Environment variable read by every S1 line: `M0_FR_TAG`; its value is the decimal text of the unit's `tag` seed integer (run plan).",
          "Self-check, not independent review. No S2a copy, no S3 copy and no S4 edit is made (reasons at the end).", ""]
    for i, (path, name, kinds) in enumerate(ITEMS):
        orig = subprocess.run(["git", "show", f"{COMMIT}:{path}"], check=True, capture_output=True, text=True).stdout
        o = scratch / f"{i}_{name}"
        o.write_text(orig)
        copy = (OUT / name).read_text()
        d = subprocess.run(["diff", "-U0", "--label", f"a/{path}", "--label", f"b/{OUT / name}", str(o), str(OUT / name)], capture_output=True, text=True).stdout
        hunks = [int(m.group(1)) for m in re.finditer(r"^@@ -(\d+)(?:,\d+)? ", d, re.M)]
        assert hunks, name
        md += [f"## `{OUT / name}`", "", f"- original: `{path}`", f"- original SHA-256: `{hashlib.sha256(orig.encode()).hexdigest()}`",
               f"- copy SHA-256: `{hashlib.sha256(copy.encode()).hexdigest()}`", "", "```diff", d.rstrip("\n"), "```", ""]
        for h in hunks:
            md.append(f"- hunk at original line {h}: {kinds[h]}")  # KeyError if a hunk is not one of the expected kinds
        assert set(hunks) == set(kinds), (name, hunks, kinds)
        md.append("")
    md += [
        "## Kinds not used, and why", "",
        "- S2a: not needed. `r2_fix4_battery.py` takes its lineages from `--only` and `f_rules.py` from argv[3] (names without `R2.`); the run plan gives the 17 survivors there.",
        "- S3: not needed. No absolute or scratch path in the four files; `REV` of `f_rules.py` is relative to the working directory, which the plan sets to the worktree root (R-49).",
        "- S4: no edit. `f_rules_new.py` has `from f_new_heur import NEW` (lines 24 and 54). Run as a file from `studies/m0/fresh_run/r2/`, its own directory is `sys.path[0]`, so the line resolves to the copy `f_new_heur.py` next to it (UNITS.md D4, REPORT D4). The plan's `PYTHONPATH` is the worktree root alone, so the original directory `final_r2/` is not on the path.",
        "- Imports of `studies.m0.*` modules are untouched: none of them is copied.",
        "- Each S1 line uses `__import__(\"os\")` inline so that no import line is added.",
        "- S2b on `f_new_heur.py`: only the four decorated entries (decorator line through the last body line) are deleted; the blank lines between them are left; the helper `_meet`, now unused, stays (it is not an entry).",
        ""]
    Path(OUT / "COPIES.md").write_text("\n".join(md))


if __name__ == "__main__":
    main()
