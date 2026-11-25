# ruff: noqa
"""Audit 3 of M1 (arbor-auditor, Claude Opus 5.5). Shared loader: the CURRENT proposed M1 set, determined by reading the code at f122e6bc:
16 lineages in core.REGISTRY (lineages_m1.py) + load_rev2() (17 rev2 shapes + 4 carried-over batch-1 shapes) = 37, of which
M1.min_cost_packs_r2 is NOT REGISTERED (lineages_m1_rev2.NOT_REGISTERED) -> 36 proposed. No arborlm.*_analysis import; only generators are imported.
Audit seeds are small throwaway integers (3, 5, 7, 9) passed through core.stream with audit labels; none is a registered study seed.
Run from the implementation worktree with PYTHONPATH set to it.
"""
from studies.m0.core import ALL_LEVELS, build_item, stream, lineages_of
from studies.m0.lineages_m1_rev2 import load_rev2, NOT_REGISTERED


def current_set(include_not_registered=False):
    lins = list(lineages_of("M1")) + list(load_rev2())
    if not include_not_registered:
        lins = [x for x in lins if x.id not in NOT_REGISTERED]
    return {x.id: x for x in lins}


def items(lin, level, n, seed, tag):
    rng = stream(seed, "audit3-m1", tag, lin.id, str(level))
    return [build_item(lin, level, rng, "A", f"a3/{i}") for i in range(n)]


if __name__ == "__main__":
    cs = current_set(True)
    print(len(cs), "with not-registered;", len(current_set()), "proposed")
    for lid, lin in sorted(cs.items()):
        for lv in (0, 3, 6):
            it = items(lin, lv, 1, 9, "show")[0]
            print(f"== {lid} L{lv} ans={it.answer}\n{it.question}\n")
