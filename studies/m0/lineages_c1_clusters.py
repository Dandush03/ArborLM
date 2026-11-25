# ruff: noqa: E501
"""C1 cluster map (lead rulings 2: R-2 the auditors' strict map is the working map; R-8 the procedure is the program's algorithm).

Source of the map: the independent audit ``docs/reviews/m0-lineage-decision-2026-11-25/audit_c1/AUDIT_M0_C1_1.md`` (arbor-auditor, Claude Opus 5.5), section 2:
eight strict merges B1 to B8 over the 39 written lineages (14 existing, 25 batch-1) give 28 clusters; adding the author's borderline groups gives
22 ("strictest"). An author's disagreement is written beside the map (``DISAGREEMENTS``) and does NOT un-merge anything. Self-checked only.

Revision 2 changes the cluster list in one place, by the author's own split (audit B6 partial overlap): the old ``recursive_calls`` had five shapes of
which 'two' and 'tri' are the linear recurrence ``fib_like`` iterates. They are now ``fib_shapes_recursive`` (a shape of the fib_like cluster), and the
other three shapes stand as the lineage ``recursive_calls_r2`` (its own cluster). ``current_cluster_of`` maps the current lineages (the revised ones
replace the superseded ones); the count of current strict clusters is therefore 29, not 28 (one more, from the split).
"""

from __future__ import annotations

from studies.m0.core import lineages_of
from studies.m0.lineages_c1_common import load_batch1
from studies.m0.lineages_c1_rev2 import SUPERSEDES, load_rev2

STRICT_GROUPS: dict[str, tuple[str, ...]] = {
    "B1": ("C1.loop_sum", "C1.string_build", "C1.list_build", "C1.nested_pairs"),
    "B2": ("C1.func_branch", "C1.func_compose"),
    "B3": ("C1.slices", "C1.string_methods"),
    "B4": ("C1.coin_change_table", "C1.string_pair_table", "C1.grid_path_table"),
    "B5": ("C1.euclid_gcd", "C1.cond_chain"),
    "B6": ("C1.recursive_calls", "C1.fib_like"),
    "B7": ("C1.bytecode_loop", "C1.turtle_walk"),
    "B8": ("C1.bracket_matching", "C1.postfix_evaluation"),
}
# the author's borderline groupings the auditor did not adopt: they give the "strictest" 22
STRICTEST_EXTRA: dict[str, tuple[str, ...]] = {
    "S1": ("B5", "C1.while_counter", "C1.digit_peel", "C1.fast_power"),  # numeric while-loop group, joined to B5
    "S2": ("C1.bubble_pass", "C1.insertion_sort", "C1.partition_pass"),  # in-place reordering
    "S3": ("C1.mirror_pointers", "C1.run_length_scan"),  # string pointer scans
}

# The author's disagreements (R-2: written beside the map; none un-merges anything). Reasons are the author's reading and are not evidence.
DISAGREEMENTS: dict[str, str] = {
    "B1": "I would keep nested_pairs apart: it counts or adds over PAIRS (i, j) of a double loop, a different iteration space from a fold over one index; the other three are the same single-index fold.",
    "B3": "slices and string_methods use different primitive sets (index arithmetic with start, stop, step versus method chains); they are the same 'evaluate an expression on a literal' only at the level of the whole program.",
    "B4": "the three tables have different state shapes (one row of amounts, a two-dimensional table over two strings, a row over a grid) and different recurrences (sum of two earlier cells, min of three, max of two plus a local value); the audit merges them as 'fill a table from earlier cells'.",
    "B5": "cond_chain stops after a fixed number of rounds and doubles on equality, so its key is the gcd in only 43-68 % of items (audit); I accept the merge as the audit's strict reading but read the two as the same reduction family, not the same procedure.",
    "B6": "agreed in part: 'two' and 'tri' are the recurrence; the other three shapes are not. Resolved by splitting, not by merging (see module docstring).",
    "B7": "both read a command sequence and update a small state, but the state is different (position and heading versus accumulator, register and program counter); the audit merges them at the level of 'dispatch on a command'.",
    "B8": "bracket matching asks whether a closing token matches the top; postfix evaluation replaces the top two by a result; same data structure (stack in a list with a pointer), different invariants.",
}

OLD_IDS = tuple(sorted(x.id for x in lineages_of("C1")))
NEW_IDS = tuple(sorted(x.id for x in load_batch1()))
ALL_IDS = tuple(sorted(OLD_IDS + NEW_IDS))
REV2_IDS = tuple(x.id for x in load_rev2())
# which cluster the lineages of revision 2 join (all but the split stay in the cluster of what they supersede or extend)
REV2_CLUSTER_OF: dict[str, str] = {
    "C1.fib_shapes_recursive": "C1.fib_like",
    "C1.recursive_calls_r2": "C1.recursive_calls_r2",
    "C1.insertion_sort_traced": "C1.insertion_sort",
    "C1.fast_power_traced": "C1.fast_power",
    "C1.euclid_gcd_traced": "C1.euclid_gcd",
    "C1.kadane_scan_traced": "C1.kadane_scan",
    "C1.bracket_matching_traced": "C1.bracket_matching",
}


def _group_of(lid: str, groups: dict[str, tuple[str, ...]]) -> str | None:
    for gname, members in groups.items():
        if lid in members:
            return gname
    return None


def strict_clusters(ids: tuple[str, ...] = ALL_IDS) -> dict[str, tuple[str, ...]]:
    """Cluster name -> members: the auditor's strict map (B1..B8, every other lineage its own cluster)."""
    out: dict[str, list[str]] = {}
    for lid in ids:
        g = _group_of(lid, STRICT_GROUPS)
        out.setdefault(g or lid, []).append(lid)
    return {k: tuple(v) for k, v in sorted(out.items())}


def strictest_clusters(ids: tuple[str, ...] = ALL_IDS) -> dict[str, tuple[str, ...]]:
    """The strict map with the author's borderline groups also merged (S1 absorbs B5)."""
    base = strict_clusters(ids)
    out: dict[str, list[str]] = {}
    for cname, members in base.items():
        target = cname
        for sname, sm in STRICTEST_EXTRA.items():
            if cname in sm or any(m in sm for m in members):
                target = sname
        out.setdefault(target, []).extend(members)
    return {k: tuple(v) for k, v in sorted(out.items())}


def current_ids() -> tuple[str, ...]:
    """The lineages in force after revision 2: batch 1 and the old 14 minus the superseded ones, plus the revised ones (PROPOSED shapes are listed apart)."""
    superseded = set(SUPERSEDES.values())
    from studies.m0.lineages_c1_rev2 import PROPOSED

    return tuple(sorted([*(i for i in ALL_IDS if i not in superseded), *(i for i in REV2_IDS if i not in PROPOSED)]))


def current_cluster_of(lid: str) -> str:
    """Strict cluster name of a lineage of the current set (revision 2 ids resolved to the cluster they extend or replace)."""
    if lid in REV2_CLUSTER_OF:
        lid = REV2_CLUSTER_OF[lid]
    elif lid in SUPERSEDES:
        lid = SUPERSEDES[lid]
    if lid == "C1.recursive_calls":  # the split: what remains of it is its own cluster
        return "C1.recursive_calls_r2"
    return _group_of(lid, STRICT_GROUPS) or lid


def current_strict_clusters() -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for lid in current_ids():
        out.setdefault(current_cluster_of(lid), []).append(lid)
    return {k: tuple(v) for k, v in sorted(out.items())}


def current_strictest_clusters() -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for cname, members in current_strict_clusters().items():
        target = cname
        for sname, sm in STRICTEST_EXTRA.items():
            if cname in sm or cname.replace("_r2", "") in sm:
                target = sname
        out.setdefault(target, []).extend(members)
    return {k: tuple(v) for k, v in sorted(out.items())}


def families_of_current() -> dict[str, str]:
    """Lineage id -> family, for the current set (old registry, batch 1 and revision 2)."""
    fam = {x.id: x.family for x in [*lineages_of("C1"), *load_batch1(), *load_rev2()]}
    return {i: fam[i] for i in current_ids()}


def joined_family_groups() -> list[tuple[str, ...]]:
    """Families joined by a strict cluster (ruling R-6, provisional reading): the connected components over families of the current set."""
    fam = families_of_current()
    parent: dict[str, str] = {f: f for f in sorted(set(fam.values()))}

    def find(a: str) -> str:
        while parent[a] != a:
            a = parent[a]
        return a

    for members in current_strict_clusters().values():
        fs = sorted({fam[m] for m in members})
        for f in fs[1:]:
            parent[find(f)] = find(fs[0])
    groups: dict[str, list[str]] = {}
    for f in sorted(parent):
        groups.setdefault(find(f), []).append(f)
    return [tuple(v) for _, v in sorted(groups.items())]
