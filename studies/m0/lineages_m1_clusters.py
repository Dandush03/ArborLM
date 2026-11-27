# ruff: noqa: E501
"""M1 strict cluster map (lead ruling R-2 of 2026-11-25): the independent auditor's strict map over all 37 M1 lineages, adopted as the working map.

Source: docs/reviews/m0-lineage-decision-2026-11-25/audit_m1/AUDIT_M0_M1_1.md, section 2 (arbor-auditor, Claude Opus 5.5), and ``pairs_666.tsv``. Over-counting is the harmful
error, so where the author (this implementer) disagrees with a merge the disagreement is written in ``DISAGREEMENTS`` and the merge STANDS. Borderline groups are listed, not merged
(``BORDERLINE``), and go to the human lead as the range. Not human approval; not Astra review.

The map is over STEMS: a lineage id without the ``M1.`` prefix and without a ``_r2`` suffix (revision 2 shapes belong to the cluster of the batch-1 shape they supersede);
``power_remainder_r2`` supersedes ``last_digit_power``. The 16 existing lineages are in ``studies/m0/lineages_m1.py``; the 21 batch-1 lineages in ``lineages_m1_<family>.py``.
"""

from __future__ import annotations

EXISTING = (
    "shopping", "speed_distance", "pipes_work", "percent_change", "tip_split", "ratio_share", "mixture", "linear_equation", "consecutive", "ages", "average_missing",
    "rectangle", "arithmetic_series", "coins", "clock_duration", "fraction_remainder",
)
NEW = (
    "inclusion_exclusion", "binomial_choose", "slot_permutations", "change_ways", "pigeonhole_worst_case", "gcd_lcm", "crt_congruence", "prime_factors", "last_digit_power",
    "quadratic_area", "digit_puzzle", "pythagoras", "grid_perimeter", "painted_cube", "min_cost_packs", "tiered_pricing", "recurrence_iterate", "finite_differences",
    "median_list", "mode_tally", "division_counting",
)
ALL_STEMS = EXISTING + NEW  # 37

# the seven merged groups of the auditor's strict map (S1 to S7); every other lineage is its own cluster
GROUPS: dict[str, tuple[str, ...]] = {
    "S1_linear_solve": ("linear_equation", "ages", "consecutive", "average_missing", "pipes_work", "rectangle", "coins"),
    "S2_weighted_sum": ("shopping", "speed_distance", "mixture"),
    "S3_multiplicative_chain": ("percent_change", "fraction_remainder", "tip_split", "ratio_share"),
    "S4_product_rule_counting": ("binomial_choose", "slot_permutations"),
    "S5_unbounded_table": ("change_ways", "min_cost_packs"),
    "S6_exposed_faces": ("grid_perimeter", "painted_cube"),
    "S7_step_rule": ("arithmetic_series", "recurrence_iterate"),
}
SUPERSEDED_STEM = {"power_remainder": "last_digit_power"}
BORDERLINE = {
    "clock_duration": "Open borderline. The auditor keeps it apart (a sum of differences of clock readings); the author's batch-1 log put it in the weighted-sum group (S1 there). If merged into S2_weighted_sum the strict count is 21, not 22.",
}
# The author's disagreements with merges. They are recorded beside the map and do NOT un-merge anything (ruling R-2).
DISAGREEMENTS: dict[str, str] = {
    "S1_linear_solve: coins": "coins solves two linear equations in two unknowns (a count equation and a value equation, by substitution or elimination); the other six isolate one unknown. The author kept it apart (his batch-1 S7).",
    "S1_linear_solve: pipes_work": "pipes_work is one division, volume / net rate; the author's batch-1 note already called it 'arguably the same as' the linear group, so he does not dispute the merge.",
    "S3_multiplicative_chain: ratio_share": "The auditor calls it the weakest member (strict only). Dividing a total in a ratio is a proportional split by unit scaling (total / sum of parts x part), not a chain of factors applied to a running value; the author kept it apart (his batch-1 S4).",
    "S4_product_rule_counting": "slot_permutations fills ordered positions with restrictions (most restricted position first); binomial_choose selects an unordered group and divides out the order. Both are the product rule, so the author does not dispute that the merge is defensible, but he considers the algorithms different (his batch-1 borderline note).",
    "S5_unbounded_table": "change_ways COUNTS the solutions of a coin equation (a sum over the table), min_cost_packs MINIMISES a cost with overbuying allowed (a min over the table). Same table over amounts; different semiring and different final question. The author kept them apart (his batch-1 borderline note for change_ways was against digit_puzzle, not against this pair).",
    "S6_exposed_faces: grid_perimeter + painted_cube": "grid_perimeter counts sides between a square and a non-member cell in a 2-D set (rev2: scattered squares); painted_cube counts cubes by number of painted faces in a box by region (corner, edge, face, interior) with the bottom optionally unpainted. 'Count faces not shared with the shape' covers both; the author considers 2-D adjacency counting and 3-D region decomposition different procedures.",
    "S7_step_rule: arithmetic_series + recurrence_iterate": "Only recurrence_iterate's add_index shape is an arithmetic-progression sum; its Fibonacci-like and affine shapes are unrolled state updates, not sums. The merge is exact for one of three shapes and 'apply the step rule n times' for the rest.",
}


def stem(lineage_id: str) -> str:
    s = lineage_id.removeprefix("M1.").removesuffix("_r2")
    return SUPERSEDED_STEM.get(s, s)


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
