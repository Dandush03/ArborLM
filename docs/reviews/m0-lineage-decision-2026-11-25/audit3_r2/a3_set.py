# ruff: noqa
"""Audit 3 (R2): determine the CURRENT proposed R2 set by reading the registries, not the manifest.

current = core R2 (16) with a core shape replaced where a rev2 shape supersedes it (to_base -> to_base_wide, string_rewrite -> string_rewrite_nonidentity)
        + batch-1 lineages not superseded by rev2
        + rev2 shapes
        - R2.deferred_acceptance_partner (marked NOT REGISTERED in r2_rev2_build.NOT_REGISTERED)
Imports generator code only (no *_analysis, no measurement or summary script of the author)."""
from studies.m0.core import lineages_of
from studies.m0.lineages_r2_common import load_batch1
from studies.m0.lineages_r2_rev2 import load_rev2, SUPERSEDES

EXCLUDED = {"R2.deferred_acceptance_partner"}


def current():
    rev2 = load_rev2()
    superseded = set(SUPERSEDES.values())
    core = [x for x in lineages_of("R2") if x.id not in superseded]
    b1 = [x for x in load_batch1() if x.id not in superseded]
    out = {x.id: x for x in [*core, *b1, *rev2] if x.id not in EXCLUDED}
    return dict(sorted(out.items()))


# my own strict cluster map (written from my reading of the generators; see the report)
MY_MERGES = [
    ("R2.sort_list", "R2.kth_smallest"),
    ("R2.count_letter", "R2.count_divisible"),
    ("R2.to_base_wide", "R2.from_base"),
    ("R2.permutation_power", "R2.modular_power"),
]


def my_clusters(ids):
    parent = {i: i for i in ids}

    def f(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for g in MY_MERGES:
        for o in g[1:]:
            if g[0] in parent and o in parent:
                a, b = f(g[0]), f(o)
                if a != b:
                    parent[max(a, b)] = min(a, b)
    out = {}
    for i in ids:
        out.setdefault(f(i), []).append(i)
    return out


if __name__ == "__main__":
    cur = current()
    print(len(cur), "current lineages/shapes")
    for k, v in cur.items():
        print(k, v.family, v.build.__module__)
    cl = my_clusters(list(cur))
    print(len(cl), "clusters (mine)")
    for k, v in cl.items():
        if len(v) > 1:
            print("  merged:", v)
    from studies.m0.lineages_r2_clusters import strict_clusters
    sc = strict_clusters()
    print("map strict clusters:", len(sc), "covering", sum(len(v) for v in sc.values()), "ids; DA present:", any("deferred" in i for v in sc.values() for i in v))
