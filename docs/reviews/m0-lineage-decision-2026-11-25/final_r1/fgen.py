# ruff: noqa
"""Final R1 audit (fix 4): item generation through the repository's builders, throwaway seeds chosen by this auditor.
Lineage L, level v: random.Random(base + v); core.Retry skipped with the same rng (the same convention as audit 4's gen4.py).
The set: studies.m0.lineages_r1_fix4_clusters.registered_v4() (the twelve survivors); candidates_v4() for the fourteen re-run shapes.
Only the builders and the set definition are imported (no solver, battery, table or capacity code of the implementer)."""
import os, random, sys
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
if W not in sys.path:
    sys.path.insert(0, W)
from studies.m0.core import Retry
from studies.m0.lineages_r1_fix4_clusters import registered_v4, candidates_v4


def lineages():
    return {l.id: l for l in registered_v4()}


def candidates():
    return {l.id: l for l in candidates_v4()}


def items(lin, level, n, seed_base, count_retries=False):
    r = random.Random(seed_base + level)
    out, retries = [], 0
    while len(out) < n:
        try:
            out.append(lin.build(level, r))
        except Retry:
            retries += 1
            if retries > 500 * n:
                raise RuntimeError(f"{lin.id} level {level}: too many retries")
    return (out, retries) if count_retries else out
