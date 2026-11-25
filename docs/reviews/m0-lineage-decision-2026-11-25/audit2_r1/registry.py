# ruff: noqa
"""Auditor helper: the registered R1 lineage set (all loaded lineages minus SUPERSEDED.txt), with families.
Read-only use of studies.m0.core (rendering helpers) and the lineage modules. No *_analysis import."""
import sys

AGENT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
if AGENT not in sys.path:
    sys.path.insert(0, AGENT)

from studies.m0 import core  # noqa: E402
from studies.m0.lineages_r1_common import load_pilot  # noqa: E402


def superseded() -> set[str]:
    out = set()
    for ln in open(f"{AGENT}/studies/m0/fixtures/r1_pilot/SUPERSEDED.txt", encoding="utf-8"):
        ln = ln.strip()
        if ln.startswith("R1."):
            out.add(ln)
    return out


def all_lineages() -> dict:
    d = {x.id: x for x in core.lineages_of("R1")}
    for x in load_pilot():
        assert x.id not in d
        d[x.id] = x
    return d


def registered() -> dict:
    sup = superseded()
    return {k: v for k, v in sorted(all_lineages().items()) if k not in sup}


if __name__ == "__main__":
    reg = registered()
    alll = all_lineages()
    print("loaded", len(alll), "superseded", len(superseded()), "registered", len(reg))
    fams = sorted({v.family for v in reg.values()})
    print("families", len(fams), fams)
    for k, v in reg.items():
        print(k, v.family)
    print("core.family_partition('R1') on core registry:", core.family_partition("R1"))
