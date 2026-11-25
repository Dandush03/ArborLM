# ruff: noqa: E501
"""M1 strict cluster map for the fix-round-3 set (lead rulings R-2, R-6, R-12; audit AUDIT3_M1 section 4).

The auditor's strict map (22 clusters over the 36 proposed lineages) is the working map. It is over STEMS (a lineage id without the ``M1.`` prefix and without ``_r2`` / ``_r3``;
``last_digit_power`` is the stem of ``power_remainder``). ``min_cost_packs`` is NOT REGISTERED and is not in this map at all, nor in its count (R-12). A lineage marked NOT REGISTERED in
``lineages_m1_fix3.NOT_REGISTERED`` is removed from ``strict_clusters`` and from the count; a cluster with no registered member disappears.

Borderline merges are LISTED, not merged (``BORDERLINE``): merging them would give 21 (one merge) or 20 (both). Not human approval; not Astra review.
"""

from __future__ import annotations

from studies.m0.lineages_m1_fix3_common import STEM_OF

# every stem of the proposed set: 16 existing + 20 new = 36 (min_cost_packs excluded)
ALL_STEMS = (
    "shopping", "speed_distance", "pipes_work", "percent_change", "tip_split", "ratio_share", "mixture", "linear_equation", "consecutive", "ages", "average_missing", "rectangle",
    "arithmetic_series", "coins", "clock_duration", "fraction_remainder",
    "inclusion_exclusion", "binomial_choose", "slot_permutations", "change_ways", "pigeonhole_worst_case", "gcd_lcm", "crt_congruence", "prime_factors", "last_digit_power", "quadratic_area",
    "digit_puzzle", "pythagoras", "grid_perimeter", "painted_cube", "tiered_pricing", "recurrence_iterate", "finite_differences", "median_list", "mode_tally", "division_counting",
)

GROUPS: dict[str, tuple[str, ...]] = {
    "S1_linear_solve": ("linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"),
    "S2_weighted_sum": ("shopping", "speed_distance", "mixture"),
    "S3_multiplicative_chain": ("percent_change", "fraction_remainder", "tip_split", "ratio_share"),
    "S4_product_rule_counting": ("binomial_choose", "slot_permutations"),
    "S5_unbounded_table": ("change_ways",),  # min_cost_packs: NOT REGISTERED, excluded (R-12)
    "S6_exposed_faces": ("grid_perimeter", "painted_cube"),
    "S7_step_rule": ("arithmetic_series", "recurrence_iterate"),
}

# other evaluations' lineages that share a cluster's algorithm (audit AUDIT3_M1 section 4). Recorded, nothing merged or dropped on this account (R-7).
CROSS_EVALUATION: dict[str, list[str]] = {
    "crt_congruence": ["R2.crt_smallest"],
    "gcd_lcm": ["R2.gcd_euclid (gcd and lcm asks)", "C1.euclid_gcd", "C1.euclid_gcd_traced"],
    "prime_factors": ["R2.prime_factor_query"],
    "last_digit_power": ["R2.modular_power (cluster with permutation_power)", "C1.fast_power", "C1.fast_power_r2"],
    "S5_unbounded_table": ["C1.coin_change_table (the ways[T] shape)", "R2.coin_change_min (by S5's own count-versus-min merge)"],
    "inclusion_exclusion": ["R1.venn_counting", "R1.venn_counting_r4"],
    "median_list": ["R2.sort_list", "R2.kth_smallest (the audit's R2 sort / kth-smallest cluster)"],
    "S7_step_rule": ["C1.fib_like", "C1.loop_sum"],
}
CROSS_EVALUATION_BORDERLINE: dict[str, list[str]] = {
    "division_counting": ["R2.multiples_between"],
    "mode_tally": ["C1.counter_list", "R2.count_letter"],
}

# borderline merges inside M1: listed, NOT merged (R-2)
BORDERLINE: dict[str, str] = {
    "gcd_lcm + crt_congruence": "The lcm ask of gcd_lcm is the CRT sieve with every remainder 0 (auditor, AUDIT3_M1 section 4). If merged the strict count is one lower.",
    "clock_duration + S2_weighted_sum": "clock_duration is a sum of differences of clock readings; the author's batch-1 log put it with the weighted sums. The auditor keeps it apart. If merged the strict count is one lower.",
}


def stem(lineage_id: str) -> str:
    if lineage_id in STEM_OF:
        return STEM_OF[lineage_id]
    return lineage_id.removeprefix("M1.").removesuffix("_r3").removesuffix("_r2")


def cluster_of(lineage_id: str) -> str:
    st = stem(lineage_id)
    for name, members in GROUPS.items():
        if st in members:
            return name
    return st


def strict_clusters(ids: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in ids:
        out.setdefault(cluster_of(i), []).append(i)
    return out


def count_strict(ids: list[str]) -> int:
    return len(strict_clusters(ids))


def cross_evaluation_of(cluster: str) -> list[str]:
    return CROSS_EVALUATION.get(cluster, []) + [f"{x} (borderline)" for x in CROSS_EVALUATION_BORDERLINE.get(cluster, [])]
