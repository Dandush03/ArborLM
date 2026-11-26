# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Per-shape, per-level excess of the best counted shortcut rule over the base rate, by rule class (round 4; lead rulings R-24, R-26).

The classification sets ``EXCL``, ``M``, ``GENERIC``, ``CHEAP`` and the function ``cls`` are COPIED from the fourth auditor's ``final_table4.py``
(``docs/reviews/m0-lineage-decision-2026-11-25/audit4_r1/final_table4.py``, Claude Opus 5.5, audit 4 of R1) so that a rule is classed as the audit classed it:
C = cheap rule (a count, a single feature, a fitted constant / ratio / lookup, a reading of one sentence); A = approximate or partial procedure of comparable cost (bounded search, one rule kind ignored,
partial xor, a different procedure that usually agrees); M = misreading of a stated convention (listed, not counted); EXCL = exact algorithms and rules audit 3 set aside (dropped). A rule not named in
``M``, ``GENERIC`` or ``CHEAP`` is class A, as in the audit. The bound of 0.15 (R-24) applies to the larger of the C and A values at any level; the M value is reported beside it.
Rows are the dictionaries written by ``r1_fix4_a4_heur`` (the auditor's battery), ``r1_fix3_battery.measure`` (the implementer's battery) and ``r1_fix4_tells`` (fitted count-feature lookups):
effect = max(eff, anti) of a row (the exploitable direction: following the rule, or choosing among the options it did not choose); a rule that is exact on every item (accuracy 1 on all of them) is dropped.
"""

from __future__ import annotations

import json
from typing import Any

EXCL = {"latest_start_first", "duration_end_off_by_one", "inclusive_day_reading", "ccw_as_cw", "cw270_as_90", "ignore_180s", "left_right_only",
        "ignore_last_condition", "first_cond_only_then_first", "off_by_one_low", "strict_gt_D", "turn_moves_bottom_to_top", "partial_walk_3",
        "rule_at_distance_1", "second_nearest_rule", "third_nearest_rule"}
M = {"signed_axis_merged", "chebyshev", "euclid_rounded", "off_by_one_plus", "wrong_first_mover", "east_west_mirrored", "rotation_reversed", "rotations_reversed",
     "k_minus_1", "k_plus_1", "inverse_answer", "direction_ignored_p_over_q", "abstain_as_yes", "abstain_as_no", "total_minus_union_wrong_sign", "drop_negation", "all_or", "all_and",
     "direction_slip"}
GENERIC = {"first_mentioned", "last_mentioned", "most_mentioned", "least_mentioned", "alpha_first", "alpha_last", "longest_name", "shortest_name", "largest_number",
           "smallest_number", "last_number", "first_number", "modal_number", "sum_numbers", "constant_mfk_fitted", "fitted_ratio_times_size", "asked_pair_stated_verbatim",
           "asked_entity_never_mentioned"}
CHEAP = {"round_0_75n", "round_0_6n", "round_n_2", "round_2n_3", "n_minus_1", "n_minus_2", "n_minus_containing", "isolated_count", "distinct_starts", "n_minus_overlapping_pairs_half",
         "fewest_negated_matches", "signed_match_count", "matches_first_leaf", "matches_last_leaf", "most_leaves_matched", "first_listed_badge", "last_listed_badge",
         "wired_switch_count_parity", "initial_state", "majority_on_at_start", "presses_parity_all", "last_press_flips", "each_switch_once", "flip_initial", "ignore_initial",
         "first_listed_rule", "last_listed_rule", "majority_sign", "odd_yes_count", "all_can", "first_rule_group_in_chain_text", "least_specific_rule",
         "kind_constant", "mentions_both_in_one_premise", "x_has_outgoing_all", "x_or_y_in_a_no", "last_turn_only", "start_direction", "opposite_of_start",
         "q_rule_with_fact", "q_rule_with_two_literals", "q_rule_listed_first", "q_rule_listed_last", "majority_conclusion_sign", "never_concluded_cbd", "query_is_fact_else_cbd",
         "all_else", "all_then", "first_leaf", "last_leaf", "negate_all", "D_le_0", "more_yes_votes", "more_yes_weight", "heaviest_voter", "count_margin_ge_D", "approx_count_times_mean", "yes_weight_ge_D",
         "arith_original_index", "arith_ignoring_leaves", "jth_last_cut", "first_cut", "initial_position_j", "last_cut", "last_joiner", "initial_bottom", "initial_top",
         "most_wins", "first_round_winner_with_most_wins", "x_or_y_direct_diff_no", "x_or_y_has_a_different", "one_step_no", "both_have_same_links_yes", "common_same_neighbour_else_cbd",
         "local_max", "most_local_wins", "smallest_unit_count", "N_itself", "N_times_first_rate", "N_times_largest_number", "largest_rate_number", "first_leg_only",
         "largest_stated", "sum_all", "path_len_times_30", "largest_stated_gap", "sum_all_gaps", "triangle_means_no", "tree_means_yes", "edges_ge_n", "edges_ge_n_plus_1", "edges_gt_n", "anyone_with_3_rivals",
         "max_degree_ge_4_no", "odd_edge_count_no", "direct_road", "most_children_option", "parentless_option", "root_of_family", "different_parents", "both_have_grandparent_diff_parents",
         "most_children", "most_grandchildren", "most_children_plus_grandchildren", "accuses_someone_means_knave", "called_knave_means_knave", "called_knight_means_knight",
         "self_doubt_means_knight", "self_praise_means_knave", "own_statement_kind_table", "about_asked_vote", "own_kind_some_knave_knight_both_knave", "max_leaf", "min_leaf",
         "median_high", "median_low", "mean_leaf_rounded", "all_distinct", "max_gt_half_rest", "sum_mod4", "most_accused", "least_accused", "most_denied", "never_denied",
         "always_cbd", "net_degree_compare", "outdegree_compare", "x_no_outgoing", "y_no_incoming", "unmentioned_no", "x_outdeg_ge_2_yes", "many_roads_yes", "reverse_road", "x_mentioned_yes",
         "not_placed_uniform", "not_placed_end_consistent", "end_person_for_end_seat", "stated_seat", "most_constrained", "least_constrained", "start_cell", "first_leg", "last_leg",
         "max_on_path", "sum_all_legs", "initial_item", "max_duration", "sum_durations", "total_div_2", "starts_within_20", "same_format", "start_order", "starts_within_12", "starts_within_6",
         "earlier_long_20", "later_shorter", "sum_len_ge_gap", "longer_len_gt_gap", "later_event_longer", "ends_order_same_as_starts", "anchor_weekday", "last_link_only",
         "sum_all_links_unsigned", "jth_alphabetical", "jth_listed", "start_balance", "start_extreme", "net_flow_extreme", "path_first", "path_last", "path_max", "path_first_gap", "path_last_gap", "path_max_gap"}



def bare(h: str) -> str:
    return h.split(":", 1)[1] if h.startswith(("a3:", "a4:")) else h


def cls(h: str) -> str | None:
    """'C', 'A', 'M' or None (excluded). Feature-lookup rows are named 'feat:<name>' (C, or A for the family-tree option rule)."""
    if h.startswith("feat:"):
        return "A" if "family tree" in h else "C"
    b = bare(h)
    if b in EXCL:
        return None
    if b in M:
        return "M"
    if b in GENERIC or b in CHEAP:
        return "C"
    return "A"


def load_rows(path: str) -> list[dict[str, Any]]:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def per_level(rows: list[dict[str, Any]], bound_lineages: list[str] | None = None) -> dict[str, dict[int, dict[str, tuple[float, str]]]]:
    """{lineage: {level: {'C': (value, rule), 'A': (...), 'M': (...)}}}: the largest effect per class at that level (0.0 and '' if no rule of the class is positive)."""
    best: dict[str, dict[int, dict[str, tuple[float, str]]]] = {}
    for r in rows:
        lid, lv, h = r["lineage"], r["level"], r["heuristic"]
        if bound_lineages is not None and lid not in bound_lineages:
            continue
        if h.endswith("_error") or h.startswith("a4:error") or h == "a3:error":
            continue
        if r.get("acc_fired") is not None and r["acc_fired"] >= 0.999 and r.get("fired") == r.get("n"):
            continue
        c = cls(h)
        if c is None:
            continue
        v = max(r["eff"], r["anti"] if r.get("anti") is not None else -9.0)
        slot = best.setdefault(lid, {}).setdefault(lv, {"C": (0.0, ""), "A": (0.0, ""), "M": (0.0, "")})
        if v > slot[c][0]:
            slot[c] = (round(v, 4), bare(h) if not h.startswith("feat:") else h)
    return best


def level_max(slot: dict[str, tuple[float, str]]) -> tuple[float, str, str]:
    """(largest of the C and A values at this level, the rule's name, its class)."""
    c, a = slot["C"], slot["A"]
    return (c[0], c[1], "C") if c[0] >= a[0] else (a[0], a[1], "A")


def shape_max(levels: dict[int, dict[str, tuple[float, str]]]) -> tuple[float, int, str, str]:
    """(largest C/A value over levels, the level, the rule, its class)."""
    lv = max(sorted(levels), key=lambda k: level_max(levels[k])[0])
    v, name, c = level_max(levels[lv])
    return v, lv, name, c
