# ruff: noqa: E501
"""C1 cluster map after fix round 3 (ruling R-2: the auditor's strict map governs; R-8: the procedure is the program's algorithm; R-12: NOT REGISTERED means excluded).

Source: ``docs/reviews/m0-lineage-decision-2026-11-25/audit3_c1/AUDIT3_C1.md`` section 2 (the auditor's strict map: the eight merges B1 to B8 over the 39 written lineages give
28 clusters) with ONE change the lead directed: ``recursive_calls_r2`` is merged into the fib cluster (B6), as the auditor's own map has it (his count 28 includes that
merge; the author's revision-2 split had made 29). Every other cluster of the auditor's map is kept as is. An author's disagreement does not un-merge (R-2).

``MEMBERS`` lists, per cluster, the lineages of the CURRENT set: the unchanged ones (``lineages_c1.py``, ``lineages_c1_<family>.py``, ``lineages_c1_rev2.py``) and the ones of this round
(``lineages_c1_fix3_*.py``, ids ending ``_f3``). ``NOT_REGISTERED_CLUSTERS`` names the clusters that have no registered-candidate member; they leave the count (R-12).
``CROSS_EVALUATION`` lists, per cluster, the other evaluations' lineages that share its algorithm, from the audit's section 2 (strong = same algorithm; medium = close).
Nothing here is a registration; self-checked only.
"""

from __future__ import annotations

from studies.m0.lineages_c1_fix3 import NOT_REGISTERED, SUPERSEDES3, VARIANT, load_fix3

# cluster -> current members (id of the lineage in force; an f3 id replaces the id it supersedes)
MEMBERS: dict[str, tuple[str, ...]] = {
    "B1": ("C1.loop_sum", "C1.string_build_f3", "C1.list_build_f3", "C1.nested_pairs_f3"),
    "B2": ("C1.func_branch", "C1.func_compose_f3"),
    "B3": ("C1.slices", "C1.string_methods_f3"),
    "B4": ("C1.coin_change_table_f3", "C1.string_pair_table", "C1.grid_path_table"),
    "B5": ("C1.euclid_gcd_traced_f3", "C1.cond_chain_f3"),
    "B6": ("C1.fib_like_f3", "C1.fib_shapes_recursive_f3", "C1.recursive_calls_r2"),
    "B7": ("C1.bytecode_loop_f3", "C1.turtle_walk_f3"),
    "B8": ("C1.bracket_matching_f3", "C1.postfix_evaluation"),
    "C1.while_counter": ("C1.while_counter_f3",),
    "C1.bubble_pass": ("C1.bubble_pass",),
    "C1.counter_list": ("C1.counter_list_f3",),
    "C1.minmax_track": (),  # NOT REGISTERED
    "C1.digit_peel": ("C1.digit_peel_f3",),
    "C1.fast_power": ("C1.fast_power_f3",),
    "C1.run_length_scan": ("C1.run_length_scan",),
    "C1.mirror_pointers": ("C1.mirror_pointers",),
    "C1.sieve_marking": ("C1.sieve_marking_f3",),
    "C1.binary_search": ("C1.binary_search_f3",),
    "C1.merge_two_sorted": ("C1.merge_two_sorted_f3",),
    "C1.insertion_sort": (),  # NOT REGISTERED
    "C1.partition_pass": ("C1.partition_pass_f3",),
    "C1.kadane_scan": (),  # NOT REGISTERED
    "C1.majority_vote_scan": ("C1.majority_vote_scan_f3",),
    "C1.bfs_queue": ("C1.bfs_queue",),
    "C1.union_find_links": ("C1.union_find_links_f3",),
    "C1.circle_elimination": ("C1.circle_elimination_r2",),
    "C1.cellular_update": ("C1.cellular_update_f3",),
    "C1.shared_lists": ("C1.shared_lists_f3",),
}
# lineages in the 28-cluster map that are NOT REGISTERED (kept on file; excluded from G, fixtures and capacity runs: R-12)
EXCLUDED_LINEAGES: tuple[str, ...] = ("C1.insertion_sort", "C1.minmax_track", "C1.kadane_scan")
# the lineages that are variants (their program differs from the algorithm the superseded lineage traced); lead decision pending
VARIANT_CLUSTERS: dict[str, str] = {"C1.fast_power": "C1.fast_power_f3", "C1.counter_list": "C1.counter_list_f3"}

# other evaluations' lineages that share a cluster's algorithm (audit section 2). 'strong' = the same algorithm; 'medium' = close. Read from docstrings by the auditor.
CROSS_EVALUATION: dict[str, dict[str, tuple[str, ...]]] = {
    "B1": {"medium": ("R2.count_divisible", "M1.arithmetic_series")},
    "B3": {"medium": ("R2.list_ops", "R2.string_rewrite")},
    "B4": {"strong": ("R2.coin_change_min", "R2.lcs_length", "M1.S5_unbounded_table (change_ways)")},
    "B5": {"strong": ("R2.gcd_euclid", "M1.gcd_lcm")},
    "B6": {"strong": ("M1.S7_step_rule (recurrence_iterate)",)},
    "B7": {"medium": ("R1.boolean_lights (compass_turns)", "R1.spatial_grid_walk")},
    "B8": {"strong": ("R2.bracket_match",), "medium": ("R2.stack_machine", "R2.expression_eval")},
    "C1.bubble_pass": {"medium": ("R2.sort_list",)},
    "C1.insertion_sort": {"medium": ("R2.sort_list",)},
    "C1.minmax_track": {"medium": ("R1.order_extreme",)},
    "C1.counter_list": {"medium": ("M1.mode_tally",)},
    "C1.majority_vote_scan": {"medium": ("M1.mode_tally",)},
    "C1.digit_peel": {"strong": ("R2.from_base", "R2.to_base")},
    "C1.fast_power": {"strong": ("R2.modular_power (the unmodified algorithm; the variant fast_power_f3 differs in the squaring step)",)},
    "C1.run_length_scan": {"strong": ("R2.run_length",)},
    "C1.mirror_pointers": {"medium": ("R2.palindrome_check",)},
    "C1.binary_search": {"strong": ("R2.binary_search_trace",)},
    "C1.kadane_scan": {"strong": ("R2.max_subarray_sum",)},
    "C1.bfs_queue": {"medium": ("R1.categories_follow",)},
    "C1.union_find_links": {"medium": ("R1.categories_follow",)},
    "C1.circle_elimination": {"strong": ("R1.containers_queue_line (elimination_josephus)",)},
    "C1.cellular_update": {"strong": ("R2.cellular_automaton",)},
}


def all_members() -> tuple[str, ...]:
    return tuple(i for ms in MEMBERS.values() for i in ms)


def cluster_of(lid: str) -> str:
    for c, ms in MEMBERS.items():
        if lid in ms:
            return c
    raise KeyError(lid)


def clusters() -> dict[str, tuple[str, ...]]:
    return dict(sorted(MEMBERS.items()))


def registered_candidate_clusters(include_variants: bool = True) -> dict[str, tuple[str, ...]]:
    """Clusters with at least one registered-candidate member (R-12: an excluded cluster leaves the count)."""
    out = {c: ms for c, ms in MEMBERS.items() if ms}
    if not include_variants:
        out = {c: ms for c, ms in out.items() if c not in VARIANT_CLUSTERS}
    return dict(sorted(out.items()))


def f3_ids() -> tuple[str, ...]:
    return tuple(x.id for x in load_fix3())


def check_consistency() -> list[str]:
    """Problems (empty when none): every f3 lineage is a member of exactly one cluster; every member exists; the excluded ones are in no cluster but their own empty one."""
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2

    known = {x.id for x in [*lineages_of("C1"), *load_batch1(), *load_rev2(), *load_fix3()]}
    problems: list[str] = []
    seen: dict[str, str] = {}
    for c, ms in MEMBERS.items():
        for m in ms:
            if m not in known:
                problems.append(f"{m} in {c} is not a lineage")
            if m in seen:
                problems.append(f"{m} in both {seen[m]} and {c}")
            seen[m] = c
    for i in f3_ids():
        if i not in seen:
            problems.append(f"{i} is in no cluster")
        if i not in SUPERSEDES3:
            problems.append(f"{i} supersedes nothing")
    for i in EXCLUDED_LINEAGES:
        if i in seen:
            problems.append(f"{i} is NOT REGISTERED but is a member of {seen[i]}")
        if i not in NOT_REGISTERED:
            problems.append(f"{i} has no reason in NOT_REGISTERED")
    for v in VARIANT:
        if v not in seen:
            problems.append(f"variant {v} is in no cluster")
    return problems
