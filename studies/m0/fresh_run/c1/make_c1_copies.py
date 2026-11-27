"""M0 fresh run, stage 1S point 3: the run copies of evaluation C1 (standard library only).

Only two C1 scripts need a copy: ``final_c1/f5_closed_forms.py`` and ``final_c1/f5b_closed_forms_v2.py``. Their lineage table ``FNS`` begins with
``C1.sieve_marking_f4``, which is not on the survivor list of record, and no command line can change it. The difference is of kind S2 (b): that one entry is
removed. Every other C1 script takes its seed, its lineages and its paths on its command line and is run as committed.

Usage (from the worktree root):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/c1/make_c1_copies.py

Writes the two copies and COPIES.md next to this file. It refuses to overwrite an existing file.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

COMMIT = "b78e58b1"
D = "docs/reviews/m0-lineage-decision-2026-11-25/final_c1/"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SURVIVORS = set(json.loads((ROOT / "studies/m0/manifests/survivor_list_of_record.json").read_text())["evaluations"]["C1"])

OLD_FNS_PREFIX = '{"C1.sieve_marking_f4": sieve, '
NEW_FNS_PREFIX = "{"

COPIES = [D + "f5_closed_forms.py", D + "f5b_closed_forms_v2.py"]


def git_show(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def main() -> None:
    assert "C1.sieve_marking_f4" not in SURVIVORS
    out = ["# C1 run copies (stage 1S point 3)\n",
           f"Originals are the files at `{COMMIT}` (`git show {COMMIT}:<path>`). Written by `make_c1_copies.py`. Every other C1 script is run as committed.\n"]
    for path in COPIES:
        orig = git_show(path)
        text = orig.decode()
        lines = text.splitlines(keepends=True)
        hits = [i for i, ln in enumerate(lines) if ln.startswith("FNS = ") and OLD_FNS_PREFIX in ln]
        assert len(hits) == 1, (path, hits)
        i = hits[0]
        lines[i] = lines[i].replace(OLD_FNS_PREFIX, NEW_FNS_PREFIX, 1)
        new = "".join(lines)
        dest = HERE / Path(path).name
        if dest.exists():
            sys.exit(f"refusing to overwrite {dest}")
        dest.write_bytes(new.encode())
        diff = "".join(difflib.unified_diff(text.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{dest.relative_to(ROOT)}", n=0))
        out.append(f"\n## {Path(path).name}\n")
        out.append(f"- original path: `{path}`\n- original SHA-256 (of `git show {COMMIT}:{path}`): `{hashlib.sha256(orig).hexdigest()}`\n")
        out.append(f"- copy path: `{dest.relative_to(ROOT)}`\n- copy SHA-256: `{hashlib.sha256(new.encode()).hexdigest()}`\n")
        out.append("- hunks: 1. Kind **S2 (b)**: the entry `\"C1.sieve_marking_f4\": sieve` of `FNS` (a lineage not on the survivor list of record) is removed; the other four entries are unchanged.\n")
        out.append("- not changed, by choice: the inline map of base file names inside `main()` also has a `C1.sieve_marking_f4` key; no `FNS` key reaches it any more, so it is dead; "
                   "the function `sieve` stays defined. Neither is an entry of `FNS`; the diff is the one line.\n")
        out.append("\n```diff\n" + diff + "```\n")
    (HERE / "COPIES.md").write_text("".join(out))
    print("done")


if __name__ == "__main__":
    main()
