# ruff: noqa
"""Audit 4 of M1 (arbor-auditor, Claude Opus 5.5). Shared loader for the fix-round-3 set, read from the code at f19d08c8:
lineages_m1_fix3.load_all() (35 r3 builders + tiered_pricing carried over) and NOT_REGISTERED (3). No arborlm.*_analysis import; only generators.
Audit seeds are small throwaway integers (11, 13, 17, 19, 23) passed through core.stream with audit-4 labels; none is a registered study seed.
Run from anywhere with PYTHONPATH=<impl worktree>.
"""
import sys

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_fix3 import NOT_REGISTERED, load_all


def current_set(include_not_registered=False):
    lins = list(load_all())
    if not include_not_registered:
        lins = [x for x in lins if x.id not in NOT_REGISTERED]
    return {x.id: x for x in lins}


def stem(lid):
    s = lid.split(".", 1)[1].removesuffix("_r3").removesuffix("_r2")
    return s


def items(lin, level, n, seed, tag):
    rng = stream(seed, "audit4-m1", tag, lin.id, str(level))
    return [build_item(lin, level, rng, "A", f"a4/{i}") for i in range(n)]


if __name__ == "__main__":
    cs = current_set(True)
    print(len(cs), "written (incl. not registered);", len(current_set()), "registered candidates; NOT_REGISTERED =", sorted(NOT_REGISTERED))
    levels = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [0, 3, 6]
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    for lid, lin in sorted(cs.items()):
        for lv in levels:
            for it in items(lin, lv, per, 19, "show"):
                print(f"== {lid} L{lv} ans={it.answer}\n{it.question}\n")
