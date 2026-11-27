# ruff: noqa: E501
"""C1 cluster map after fix round 4 (ruling R-20: the two variants are NEW lineages in their OWN clusters, not filed under ``fast_power`` and ``counter_list``; R-12: NOT REGISTERED means excluded everywhere).

A correction of the fix-3 map (``lineages_c1_fix3_clusters.py``, which stays as it is): the strict clusters B1 to B8 of the auditor's map (``audit3_c1/AUDIT3_C1.md`` section 2, adopted by audit 4 section 6) are kept
for the lineages that survive; the single-lineage clusters keep their fix-3 names; ``C1.fast_power_f4`` and ``C1.counter_list_f3`` each get a new cluster of their own. ``MEMBERS`` lists the members
that SURVIVE the fix-4 round (``manifests/c1_fix4_survivors.json`` is the record of the measurements). ``DROPPED_CLUSTERS`` lists the fix-3 clusters left with no survivor. Nothing here is a registration.
"""

from __future__ import annotations

# cluster -> surviving members (the lineage in force: an _f4 id replaces the id it supersedes)
MEMBERS: dict[str, tuple[str, ...]] = {
    "B1": ("C1.string_build_f3", "C1.list_build_f3", "C1.nested_pairs_f3"),  # loop_sum (also B1) is dropped
    "B2": ("C1.func_branch_f4", "C1.func_compose_f4"),
    "B3": ("C1.slices_f4", "C1.string_methods_f3"),
    "B5": ("C1.euclid_gcd_traced_f3", "C1.cond_chain_f3"),
    "B6": ("C1.fib_like_f3", "C1.fib_shapes_recursive_f3", "C1.recursive_calls_r2"),
    "B7": ("C1.bytecode_loop_f3", "C1.turtle_walk_f3"),
    "B8": ("C1.bracket_matching_f3", "C1.postfix_evaluation"),
    "C1.while_counter": ("C1.while_counter_f3",),
    "C1.digit_peel": ("C1.digit_peel_f3",),
    "C1.run_length_scan": ("C1.run_length_scan",),
    "C1.sieve_marking": ("C1.sieve_marking_f4",),
    "C1.binary_search": ("C1.binary_search_f3",),
    "C1.merge_two_sorted": ("C1.merge_two_sorted_f3",),
    "C1.union_find_links": ("C1.union_find_links_f3",),
    "C1.circle_elimination": ("C1.circle_elimination_r2",),
    "C1.shared_lists": ("C1.shared_lists_f3",),
    # the two variants, each in a cluster of its own (R-20)
    "C1.fast_power_square_map": ("C1.fast_power_f4",),
    "C1.counter_list_state_machine": ("C1.counter_list_f3",),
}
VARIANT_CLUSTERS: tuple[str, ...] = ("C1.fast_power_square_map", "C1.counter_list_state_machine")

# fix-3 clusters with no surviving member (every member dropped; R-12: they leave the count)
DROPPED_CLUSTERS: dict[str, tuple[str, ...]] = {
    "B4": ("C1.coin_change_table_f3", "C1.string_pair_table", "C1.grid_path_table"),
    "C1.bubble_pass": ("C1.bubble_pass",),
    "C1.partition_pass": ("C1.partition_pass_f3",),
    "C1.mirror_pointers": ("C1.mirror_pointers",),
    "C1.bfs_queue": ("C1.bfs_queue",),
    "C1.cellular_update": ("C1.cellular_update_f3",),
    "C1.majority_vote_scan": ("C1.majority_vote_scan_f3",),
    "C1.insertion_sort": (),
    "C1.minmax_track": (),
    "C1.kadane_scan": (),
}
# a lineage that left a cluster that still stands
DROPPED_MEMBERS: dict[str, str] = {"C1.loop_sum": "B1"}

# other evaluations' lineages that share a cluster's algorithm (audit 3 section 2, audit 4 section 6; 'strong' = the same algorithm, 'medium' = close, 'weak' = a loose likeness)
CROSS_EVALUATION: dict[str, dict[str, tuple[str, ...]]] = {
    "B1": {"medium": ("R2.count_divisible", "M1.arithmetic_series")},
    "B3": {"medium": ("R2.list_ops", "R2.string_rewrite")},
    "B5": {"strong": ("R2.gcd_euclid", "M1.gcd_lcm")},
    "B6": {"strong": ("M1.S7_step_rule (recurrence_iterate)",)},
    "B7": {"medium": ("R1.boolean_lights (compass_turns)", "R1.spatial_grid_walk")},
    "B8": {"strong": ("R2.bracket_match",), "medium": ("R2.stack_machine", "R2.expression_eval")},
    "C1.digit_peel": {"strong": ("R2.from_base", "R2.to_base", "R2.to_base_wide")},
    "C1.run_length_scan": {"strong": ("R2.run_length",)},
    "C1.binary_search": {"strong": ("R2.binary_search_trace",)},
    "C1.union_find_links": {"medium": ("R1.equivalence_classes",)},
    "C1.circle_elimination": {"strong": ("R1.containers_queue_line (elimination_josephus; listed NOT REGISTERED by R1)",)},
    "C1.fast_power_square_map": {"medium": ("R2.modular_power (same square-and-multiply loop skeleton, different function)", "M1.power_remainder", "M1.last_digit_power")},
    "C1.counter_list_state_machine": {"weak": ("M1.mode_tally", "R2.hash_probe")},
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


def surviving_clusters(include_variants: bool = True) -> dict[str, tuple[str, ...]]:
    out = {c: ms for c, ms in MEMBERS.items() if ms}
    if not include_variants:
        out = {c: ms for c, ms in out.items() if c not in VARIANT_CLUSTERS}
    return dict(sorted(out.items()))


def smaller_part(n_clusters: int) -> int:
    """G of ruling R-11: the cluster count of the smaller part, for ``n_clusters`` clusters split in two parts."""
    return n_clusters // 2


def check_consistency() -> list[str]:
    """Problems (empty when none): every member exists, is in exactly one cluster and is not dropped; the current set after the audit-4 drops is exactly the member set."""
    from studies.m0.lineages_c1_fix4 import (
        DROPPED_AFTER_REMEASURE,
        DROPPED_AUDIT4,
        all_written,
        current_after_audit4,
    )

    known = set(all_written())
    problems: list[str] = []
    seen: dict[str, str] = {}
    dropped = {*DROPPED_AUDIT4, *DROPPED_AFTER_REMEASURE}
    for c, ms in MEMBERS.items():
        for m in ms:
            if m not in known:
                problems.append(f"{m} in {c} is not a lineage")
            if m in seen:
                problems.append(f"{m} in both {seen[m]} and {c}")
            if m in dropped:
                problems.append(f"{m} in {c} is NOT REGISTERED")
            seen[m] = c
    if "C1.fast_power_f3" in seen or "C1.fast_power" in MEMBERS:
        problems.append("the fast_power variant must be in its own cluster")
    expect = set(current_after_audit4()) - set(DROPPED_AFTER_REMEASURE)
    if expect != set(seen):
        problems.append(f"members differ from the current set: only in the map {sorted(set(seen) - expect)}, only in the set {sorted(expect - set(seen))}")
    return problems
