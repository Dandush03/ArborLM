# ruff: noqa: E501
"""R2 strict cluster map for fix round 3 (ruling R-2: the AUDITOR's strict map governs; R-12: lineages marked NOT REGISTERED are excluded from the map and from G).

Source of the merges: ``AUDIT3_R2.md`` section 2 (four merges, no disagreement found). The map covers every lineage of ``r2_fix3_set.fix3_set()``: the 16 core R2 lineages (with ``to_base``/``string_rewrite`` represented by their
rev2 shapes) and the batch-1 lineages, minus ``deferred_acceptance_partner`` and ``chip_toppling``. Strictest/borderline groups are listed, not merged. Cross-evaluation sharing (R-7, R-15) is listed per cluster from the four audits;
nothing is merged or dropped on that account. Self-checked, not independent review, not Astra, not human approval.
"""

from __future__ import annotations

import math

from studies.m0.r2_fix3_set import NOT_REGISTERED, fix3_set

# the auditor's strict merges (AUDIT3_R2 section 2); ids use the shape ids that exist in the set (to_base_wide represents to_base)
STRICT_MERGES: list[tuple[str, ...]] = [
    ("R2.sort_list", "R2.kth_smallest"),
    ("R2.count_letter", "R2.count_divisible"),
    ("R2.to_base_wide", "R2.from_base"),
    ("R2.permutation_power", "R2.modular_power"),
]

# borderline groups at the grain of the sister maps (C1 B8, B4, B7, B1; digit_peel): listed, NOT merged (AUDIT3_R2 section 2, 'about 32 clusters')
BORDERLINE_GROUPS: list[tuple[str, ...]] = [
    ("R2.bracket_match", "R2.stack_machine", "R2.list_ops"),  # C1 B8 / B7 grain: stack and command programs
    ("R2.coin_change_min", "R2.lcs_length"),  # C1 B4 grain: two dynamic-programming tables
    ("R2.count_letter", "R2.count_divisible", "R2.grid_sum"),  # C1 B1 grain: folds over a list
    ("R2.to_base_wide", "R2.from_base", "R2.digit_root"),  # C1 digit_peel grain
    ("R2.subtraction_game", "R2.coin_change_min"),  # the batch author's own 'strictest' note
    ("R2.dictionary_rank", "R2.to_base_wide"),  # the batch author's own 'strictest' note
    ("R2.list_ops", "R2.stack_machine"),  # the author's earlier borderline note
]

# per strict cluster: the OTHER evaluations' lineages that use the same algorithm (R-7; from AUDIT3_R2 section 2, AUDIT3_C1 cross-evaluation paragraph and AUDIT3_M1 table). 'weak' = same family, different procedure.
CROSS_EVAL: dict[str, list[str]] = {
    "R2.interval_scheduling": ["R1.activity_selection (strong)"],
    "R2.cheapest_network": ["R1.mst_cost_r4 (strong)"],
    "R2.subtraction_game": ["R1.nim_xor_r4 (strong in the XOR form; this round's four-pile form still sums position values)"],
    "R2.list_ops": ["R1.containers_queue_line (strong)", "C1 B3 (medium)"],
    "R2.kth_smallest": ["M1.median_list_r2 (strong)", "C1.bubble/insertion sorts (medium)"],  # cluster key: kth_smallest < sort_list
    "R2.coin_change_min": ["C1.coin_change_table (same unbounded-supply table family, C1 B4; its shape counts ways)", "M1.change_ways_r2 (S5, counts ways; its own note merges count and min)"],
    "R2.crt_smallest": ["M1.crt_congruence_r2 (strong)"],
    "R2.prime_factor_query": ["M1.prime_factors_r2 (strong)"],
    "R2.gcd_euclid": ["M1.gcd_lcm_r2 (strong)", "C1.euclid_gcd (strong)"],
    "R2.modular_power": ["M1.power_remainder_r2 (strong)", "C1.fast_power_r2 (strong)"],
    "R2.lcs_length": ["C1.string_pair_table (strong, C1 B4)"],
    "R2.max_subarray_sum": ["C1.kadane_scan (strong)"],
    "R2.binary_search_trace": ["C1.binary_search (strong)"],
    "R2.bracket_match": ["C1 B8 bracket_matching (strong)"],
    "R2.stack_machine": ["C1 B8 postfix_evaluation (strong)", "R1.containers_stack_piles (weak)"],
    "R2.cellular_automaton": ["C1.cellular_update_r2 (strong)"],
    "R2.run_length": ["C1.run_length_scan (strong)"],
    "R2.count_divisible": ["C1.counter_list (weak)", "C1 B1 folds (weak)"],  # cluster key: count_divisible < count_letter
    "R2.from_base": ["C1.digit_peel (strong)"],  # cluster key: from_base < to_base_wide
    "R2.digit_root": ["C1.digit_peel (weak)"],
    "R2.palindrome_check": ["C1.mirror_pointers (weak)"],
    "R2.multiples_between": ["M1.division_counting_r2 (weak)"],
    "R2.expression_eval": ["C1 postfix_evaluation (medium)"],
}


def working_ids() -> list[str]:
    return sorted(fix3_set())


def clusters(merges: list[tuple[str, ...]] | None = None) -> dict[str, tuple[str, ...]]:
    ids = working_ids()
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            x = parent[x]
        return x

    for grp in STRICT_MERGES if merges is None else merges:
        for other in grp[1:]:
            ra, rb = find(grp[0]), find(other)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    out: dict[str, list[str]] = {}
    for i in ids:
        out.setdefault(find(i), []).append(i)
    return {k: tuple(v) for k, v in sorted(out.items())}


def cluster_of(lineage_id: str) -> str:
    for k, v in clusters().items():
        if lineage_id in v:
            return k
    raise KeyError(lineage_id)


def part_sizes() -> tuple[int, int]:
    """The two parts of the working map (a cluster has all its members in one part): ceil and floor of half the clusters; G is the smaller part."""
    n = len(clusters())
    return (n + 1) // 2, n // 2


def demand(g: int) -> int:
    """R-11: per cluster and level, 10 x (ceil(4,000 / G) + ceil(20,000 / G) + 100); reserve levels carry the same demand (R-10)."""
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def cross_eval_for_cluster(key: str) -> list[str]:
    out: list[str] = []
    for m in clusters()[key]:
        out += CROSS_EVAL.get(m, [])
    return out


def excluded() -> dict[str, str]:
    return dict(NOT_REGISTERED)
