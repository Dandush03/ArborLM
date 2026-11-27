# ruff: noqa
"""Audit 4 (C1), step 1: establish the current candidate set from the registries' own data (my code; no *_analysis import).

Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python <this>
Rule (mine): current = (old C1 registry + batch1 + rev2 + fix3) minus every id named as superseded (rev2 SUPERSEDES, fix3 SUPERSEDES3),
minus rev2 PROPOSED shapes, minus the fix3 NOT_REGISTERED lineage ids.
"""
import json, os, sys

sys.path.insert(0, os.getcwd())


def main():
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2, SUPERSEDES, PROPOSED
    from studies.m0.lineages_c1_fix3 import load_fix3, SUPERSEDES3, VARIANT, NOT_REGISTERED as NR3

    old = {x.id: x.family for x in lineages_of("C1")}
    b1 = {x.id: x.family for x in load_batch1()}
    r2 = {x.id: x.family for x in load_rev2()}
    f3 = {x.id: x.family for x in load_fix3()}
    allx = {**old, **b1, **r2, **f3}
    superseded = set(SUPERSEDES.values()) | set(SUPERSEDES3.values())
    excluded_names = {k for k in NR3 if "[" not in k}
    cur = [i for i in sorted(allx) if i not in superseded and i not in PROPOSED and i not in excluded_names]
    chain = {}
    for i in cur:
        c, x = [i], i
        while True:
            nxt = SUPERSEDES3.get(x) or SUPERSEDES.get(x)
            if not nxt:
                break
            c.append(nxt)
            x = nxt
        chain[i] = c
    out = {
        "n_old": len(old), "n_batch1": len(b1), "n_rev2": len(r2), "n_f3": len(f3),
        "proposed_rev2": sorted(PROPOSED), "superseded": sorted(superseded), "excluded_f3": sorted(NR3),
        "current": cur, "n_current": len(cur), "chains": chain, "variants": VARIANT,
        "family": {i: allx[i] for i in cur},
        "proposed_not_superseded": sorted(p for p in PROPOSED if p not in superseded),
        "f3_ids": sorted(f3),
        "excluded_still_superseding_something": {k: v for k, v in {**SUPERSEDES, **SUPERSEDES3}.items() if k in excluded_names},
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
