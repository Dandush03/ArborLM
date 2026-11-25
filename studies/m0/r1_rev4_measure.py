# ruff: noqa: E501
"""Measure every shape of the revision-4 registered set (``lineages_r1_clusters_v2.registered_v2``), per level, two-sided, with the revised gate and the auditor's heuristics added.

Output: ``manifests/r1_rev4_two_sided.json`` (every heuristic x level cell), ``r1_rev4_two_sided.md`` (worst heuristic per shape and per level) and ``r1_rev4_named_tells.md`` (the heuristics the
second audit named, per shape, pooled and per level). MEASURED, NOT THRESHOLDED (ruling R-3). Items: lineage_gates.sample_items(per level, levels 0..6, label "rev4-measure"), test-block seed.
Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r1_rev4_measure [per_level] [workers]``.
"""

from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path
from typing import Any

from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0 import r1_rev4_battery as bat

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "studies/m0/manifests"

# the heuristics each shape's audit named (AUDIT_M0_R1_2.md sections 3 and 5), by base id; the key is the name in the battery
NAMED: dict[str, list[str]] = {
    "categories_default_exceptions": ["M:rule_on_immediate_supergroup_chain1", "A:majority_sign", "A:least_specific_rule", "M:second_most_specific_rule", "A:last_listed", "M:odd_count_sign"],
    "conditional_threshold_rule": ["M:margin_le_zero", "M:heaviest_vote", "A:yes_count_majority", "M:weighted_yes_ge_no_ignore_margin"],
    "kinship_descendants": ["M:parent_of_most_children_person", "M:root_child_with_most_children", "A:most_children", "M:child_of_root", "A:most_mentioned"],
    "kinship_ancestor": ["A:parentless", "A:most_mentioned", "A:least_mentioned"],
    "elimination_bracket": ["X:round_one_neighbour", "A:most_wins_logic", "X:most_wins_overall", "X:beater_in_own_half"],
    "stable_matching": ["A:first_choice", "M:asks_second_choice", "A:first_mentioned", "M:receiver_ranking_ask_highest"],
    "containers_stack_piles": ["M:initial_bottom_of_asked", "A:last_block_moved_onto_asked", "A:initial_top"],
    "boolean_lights": ["M:initial_flipped", "A:initial_state"],
    "categories_follow": ["M:x_and_y_share_a_sentence_yes", "M:kind_default_all_none_yes_some_no", "M:all_x_subject_yes", "M:no_sentence_mentions_x_or_y"],
    "instant_runoff": ["A:plurality_winner", "M:condorcet_winner", "M:top_two_runoff"],
    "graph_shortest_route": ["M:best_within_two_roads", "A:direct_road_length", "M:greedy_nearest_walk"],
    "order_compare": ["A:asked_pair_stated_verbatim", "M:reverse_pair_stated", "M:x_never_taller_than_anyone_no"],
    "activity_selection": ["M:greedy_by_shortest_duration", "A:greedy_by_start"],
    "mst_cost": ["M:sum_of_each_towns_cheapest_road", "A:smallest_n_minus_1_roads"],
    "conditional_decision_tree": ["A:most_mentioned", "M:always_then_branch"],
    "minimax_tree": ["A:smallest_leaf", "X:median_leaf_low"],
    "nim_xor": ["A:odd_total_means_first", "M:largest_exceeds_rest_first"],
    "venn_counting": ["X:forget_the_triples", "M:total_minus_largest_group"],
    "topological_order": ["A:jth_alphabetical", "M:sort_by_depth_then_name"],
    "temporal_critical_path": ["X:none_applicable_open_number"],
    "spatial_relative_directions": ["X:largest_offset"],
}


def _run(args: tuple[str, int]) -> tuple[str, dict[str, Any]]:
    lid, per_level = args
    lin = next(x for x in v2.registered_v2() if x.id == lid)
    return lid, bat.measure(lin, per_level)


def named_table(results: dict[str, dict[str, Any]]) -> str:
    lines = ["# Named audit heuristics, per registered shape (MEASURED, not thresholded)", "",
             "gain = the better of following the heuristic and avoiding it (accuracy minus chance on the items it fires on; minus the commonest-answer share for open answers); effective gain = gain x fire rate. Cells: effective gain (gain), pooled then per level 0..6; a cell with fewer than 50 firings is `-`.", "",
             "| shape | heuristic | pooled: effective gain (gain, fire rate) | L0 | L1 | L2 | L3 | L4 | L5 | L6 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for lid in sorted(results):
        res = results[lid]
        for h in NAMED.get(bat.base(lid), []):
            row = res["heuristics"].get(h)
            if not row:
                continue
            pooled = row.get("all")
            cells = " | ".join(f"{row[str(lv)]['effective_gain']:+.2f} ({row[str(lv)]['gain']:+.2f})" if str(lv) in row and row[str(lv)]["fires"] >= 50 else "-" for lv in range(7))
            lines.append(f"| {lid} | {h} | {pooled['effective_gain']:+.3f} ({pooled['gain']:+.3f}, fire rate {pooled['fire_rate']}) | {cells} |" if pooled else f"| {lid} | {h} | - | {cells} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    per_level = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    ids = [x.id for x in v2.registered_v2()]
    with multiprocessing.get_context("fork").Pool(workers) as pool:
        results = dict(pool.map(_run, [(i, per_level) for i in ids], chunksize=1))
    (OUT / "r1_rev4_two_sided.json").write_text(json.dumps(results, sort_keys=True, separators=(",", ":")) + "\n")
    title = f"R1 revision-4 registered set: worst heuristic per shape and level, two-sided ({per_level} items per level, levels 0..6, test-block seed)"
    (OUT / "r1_rev4_two_sided.md").write_text(bat.table(results, title, min_fires=100))
    (OUT / "r1_rev4_named_tells.md").write_text(named_table(results))
    print(bat.table(results, title, min_fires=100))


if __name__ == "__main__":
    main()
