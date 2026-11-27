"""Writes COPIES.md for the R1 run copies: original path, original SHA-256 (git show b78e58b1:<path>), copy SHA-256, unified diff, kind of each hunk.

Standard library only. Usage (worktree root): python studies/m0/fresh_run/r1/make_copies_md_r1.py studies/m0/fresh_run/r1/COPIES.md
"""

from __future__ import annotations

import difflib
import hashlib
import subprocess
import sys
from pathlib import Path

W = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
F = "docs/reviews/m0-lineage-decision-2026-11-25/final_r1"
COPIES = [
    (
        "studies/m0/fresh_run/r1/r1_fix4_tells.py",
        "studies/m0/r1_fix4_tells.py",
        [
            "S1: the four seed literals 8300, 8400, 8500, 8600 (fit and test roots of the two lookup groups) replaced by the integers read from the environment variables M0FR_R1A_FEAT1_FIT, M0FR_R1A_FEAT1_TEST, M0FR_R1A_FEAT2_FIT, M0FR_R1A_FEAT2_TEST (read inline with __import__, so that no import line is added)"
        ],
    ),
    (
        "studies/m0/fresh_run/r1/r1_fix4_measure.py",
        "studies/m0/r1_fix4_measure.py",
        [
            "S4: the import of feature_rows from studies.m0.r1_fix4_tells redirected to its copy studies.m0.fresh_run.r1.r1_fix4_tells"
        ],
    ),
    (
        "studies/m0/fresh_run/r1/new_rules_final.py",
        f"{F}/new_rules_final.py",
        [
            "S2b: the entry of SPEC (a table keyed by lineage) for R1.conditional_decision_tree_r6, which is not on the survivor list of record, removed; no other entry touched"
        ],
    ),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    out = [
        "# M0 fresh run, stage 1S point 3: run copies of evaluation R1",
        "",
        f"Originals are the files at commit `{COMMIT}` (`git show {COMMIT}:<path>`). Self-check by the implementer context (Claude Sonnet 5.5); not an independent review, not Astra validation, not human approval.",
        "Written by `studies/m0/fresh_run/r1/make_copies_md_r1.py`. A copy differs from its original only by the hunks listed, each placed under S1 to S4. Copies are not lint-fixed.",
        "",
    ]
    for copy, orig, kinds in COPIES:
        ob = subprocess.run(
            ["git", "-C", str(W), "show", f"{COMMIT}:{orig}"], check=True, capture_output=True
        ).stdout
        cb = (W / copy).read_bytes()
        diff = list(
            difflib.unified_diff(
                ob.decode().splitlines(keepends=True),
                cb.decode().splitlines(keepends=True),
                f"a/{orig}",
                f"b/{copy}",
                n=1,
            )
        )
        hunks = sum(1 for d in diff if d.startswith("@@"))
        assert hunks == len(kinds), (copy, hunks, len(kinds))
        out += [
            f"## `{copy}`",
            "",
            f"- original path: `{orig}`",
            f"- original SHA-256: `{sha(ob)}`",
            f"- copy SHA-256: `{sha(cb)}`",
            f"- hunks: {hunks}",
            "",
        ]
        for i, k in enumerate(kinds, 1):
            out.append(f"  - hunk {i}: {k}")
        out += ["", "```diff", *[d.rstrip("\n") for d in diff], "```", ""]
    Path(sys.argv[1]).write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
