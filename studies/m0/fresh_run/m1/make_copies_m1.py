"""M0 fresh run, unit M1a: writes the four run copies and COPIES.md. Standard library only.

Every copy is the file at b78e58b1 with a fixed list of exact line replacements, each of kind S1, S2, S3 or S4 of
ADR-0033 addendum 1 section 4A stage 1S point 3. Each replacement must match exactly one line of the original.
It refuses to overwrite an existing copy.

Run from the worktree root:
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/m1/make_copies_m1.py
"""

from __future__ import annotations

import difflib
import hashlib
import subprocess
import sys
from pathlib import Path

COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
WORKTREE = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
OUT = Path("studies/m0/fresh_run/m1")
AUD = "docs/reviews/m0-lineage-decision-2026-11-25"
PKG = "studies.m0.fresh_run.m1"

# (original path, copy name, [(kind, old line, new line)])
COPIES = [
    (
        "studies/m0/m1_fix3_shortcuts.py",
        "m1_fix3_shortcuts.py",
        [
            (
                "S1",
                "SEED = 410302  # throwaway integer, not a registered study seed",
                'SEED = int(__import__("os").environ["M1A_SEED_OWN"])  # throwaway integer, not a registered study seed',
            ),
        ],
    ),
    (
        f"{AUD}/audit4_m1/shortcuts_a4.py",
        "shortcuts_a4.py",
        [
            ("S1", "SEED = 17", 'SEED = int(__import__("os").environ["M1A_SEED_A4"])'),
            (
                "S4",
                "    from studies.m0.m1_fix3_shortcuts import spec",
                f"    from {PKG}.m1_fix3_shortcuts import spec",
            ),
        ],
    ),
    (
        f"{AUD}/audit3_m1/shortcuts_a3.py",
        "shortcuts_a3.py",
        [
            ("S1", "SEED = 5", 'SEED = int(__import__("os").environ["M1A_SEED_A3"])'),
        ],
    ),
    (
        "studies/m0/m1_fix4_battery.py",
        "m1_fix4_battery.py",
        [
            (
                "S3",
                "ROOT = Path(__file__).resolve().parents[2]",
                f'ROOT = Path("{WORKTREE}")',
            ),
            (
                "S4",
                "    from studies.m0.m1_fix3_shortcuts import PROCEDURE",
                f"    from {PKG}.m1_fix3_shortcuts import PROCEDURE",
            ),
            (
                "S4",
                '    return _load(A4 / "shortcuts_a4.py", "shortcuts_a4_fix4")',
                '    return _load(ROOT / "studies" / "m0" / "fresh_run" / "m1" / "shortcuts_a4.py", "shortcuts_a4_fix4")',
            ),
            (
                "S4",
                '    return common, _load(A3 / "shortcuts_a3.py", "shortcuts_a3_fix4")',
                '    return common, _load(ROOT / "studies" / "m0" / "fresh_run" / "m1" / "shortcuts_a3.py", "shortcuts_a3_fix4")',
            ),
            (
                "S4",
                "    import studies.m0.m1_fix3_shortcuts as sc",
                f"    import {PKG}.m1_fix3_shortcuts as sc",
            ),
        ],
    ),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    md = [
        "# COPIES.md: run copies for unit M1a (M0 fresh run, ADR-0033 addendum 1, section 4A stage 1S point 3)\n",
        f"Originals are `git show {COMMIT}:<path>`. Copies are written by `make_copies_m1.py` (same directory). "
        "Each hunk is one line and is one of S1 (seed from an environment variable), S2 (lineage set), S3 (path), S4 (import / importlib path). "
        "No S2 hunk exists in unit M1a: the 29 lineages are given on the command line by `--only` (see run_plan_m1.json).\n",
        "Self-check, not independent review.\n",
    ]
    for orig, name, edits in COPIES:
        dest = OUT / name
        if dest.exists():
            sys.exit(f"refusing to overwrite {dest}")
        src = subprocess.run(["git", "show", f"{COMMIT}:{orig}"], check=True, capture_output=True).stdout
        text = src.decode()
        lines = text.split("\n")
        kinds: list[tuple[str, str, str]] = []
        for kind, old, new in edits:
            hits = [i for i, ln in enumerate(lines) if ln == old]
            if len(hits) != 1:
                sys.exit(f"{orig}: line {old!r} matched {len(hits)} lines")
            lines[hits[0]] = new
            kinds.append((kind, old, new))
        out_text = "\n".join(lines)
        dest.write_text(out_text)
        diff = "".join(
            difflib.unified_diff(
                text.splitlines(True), out_text.splitlines(True), fromfile=f"a/{orig} (b78e58b1)", tofile=f"b/{OUT / name}", n=0
            )
        )
        md.append(f"## {name}\n")
        md.append(f"- original path: `{orig}`")
        md.append(f"- original SHA-256 (`git show {COMMIT[:8]}:<path>`): `{sha(src)}`")
        md.append(f"- copy path: `{OUT / name}`")
        md.append(f"- copy SHA-256: `{sha(out_text.encode())}`")
        md.append("- hunks:")
        for k, old, _new in kinds:
            md.append(f"  - {k}: replaces `{old.strip()}`")
        md.append("\n```diff\n" + diff + "```\n")
    (OUT / "COPIES.md").write_text("\n".join(md))
    print("wrote", len(COPIES), "copies and COPIES.md")


if __name__ == "__main__":
    main()
