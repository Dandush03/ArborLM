# ruff: noqa
"""Audit 4 (R1): per-shape maximum exploitable effect, by class, combining (1) the auditor's battery (heur_run2_all.jsonl), (2) the fitted
count-feature tells (feature_tells_run1.txt, kept_tells_run1.txt) and (3) the implementer's battery rerun (impl_run1_all.jsonl).
Classes (the auditor's reading, stated so it can be redone): C = cheap rule (a count, a single feature, a fitted constant / ratio / lookup,
a reading of one sentence); A = approximate or partial procedure of comparable cost (bounded search, one rule kind ignored, partial xor, a
different procedure that usually agrees); M = misreading of a stated convention (not counted, listed). Exact rows (accuracy 1 on all items)
and audit 3's exclusions are dropped. Distribution of max(C, A) and of C alone; clusters left under bounds 0.10 / 0.15 / 0.25 when every
shape above the bound is removed (cluster map = the implementer's = the auditor's).
usage: python final_table4.py   (run from the deliver directory)"""
import json, re
from collections import defaultdict
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

def bare(h):
    return h.split(":", 1)[1] if h.startswith(("a3:", "a4:")) else h

def cls(h):
    b = bare(h)
    if b in EXCL: return None
    if b in M: return "M"
    if b in GENERIC or b in CHEAP: return "C"
    return "A"

best = defaultdict(lambda: {"C": (0.0, ""), "A": (0.0, ""), "M": (0.0, "")})
def take(lid, h, lv, v, src):
    c = cls(h)
    if c is None: return
    if v > best[lid][c][0]: best[lid][c] = (v, f"{src}:{bare(h)}@L{lv}")
for src, f in (("aud", "heur_run2_all.jsonl"), ("impl", "impl_run1_all.jsonl")):
    for line in open(f):
        r = json.loads(line)
        if r["acc_fired"] is not None and r["acc_fired"] >= 0.999 and r["fired"] == r["n"]: continue
        if r["heuristic"].endswith("_error"): continue
        v = max(r["eff"], r["anti"] if r["anti"] is not None else -9)
        take(r["lineage"], r["heuristic"], r["level"], v, src)
for f in ("feature_tells_run1.txt", "kept_tells_run1.txt"):
    for line in open(f):
        m = re.match(r"(R1\.\S+)\s+(.+?)\s+((?:[+-]\d\.\d{3}\s*){7})$", line.strip())
        if not m or m.group(1) == "R1.one_culprit": continue  # one_culprit 'true count' lookup is the auditor's invalid feature (a name answer)
        vals = [float(x) for x in m.group(3).split()]
        lv = max(range(7), key=lambda i: vals[i])
        kind = "A" if "family tree" in m.group(2) else "C"
        if vals[lv] > best[m.group(1)][kind][0]: best[m.group(1)][kind] = (vals[lv], f"feat:{m.group(2)}@L{lv}")

CL = [("order_compare", "road_reachability", "categories_follow", "equivalence_classes"), ("event_timeline", "temporal_weekday_shift", "spatial_relative_directions", "equivalence_exchange_rates"),
      ("kinship_ancestor", "kinship_cousins", "categories_default_exceptions"), ("knights_knaves", "one_culprit", "conditional_chain"),
      ("attribute_rule", "conditional_decision_tree", "minimax_tree", "elimination_bracket"), ("compass_turns", "boolean_lights")]
def cluster(l):
    b = re.sub(r"_r\d+$", "", l.split(".", 1)[1])
    for g in CL:
        if b in g: return min(g)
    return b
print(f"{'shape':36s} {'max(C,A)':>8s} {'C only':>7s}  C by                                              A by                                              M (not counted)")
allv, chv = {}, {}
for lid in sorted(best):
    b = best[lid]
    allv[lid] = max(b["C"][0], b["A"][0]); chv[lid] = b["C"][0]
    print(f"{lid:36s} {allv[lid]:8.3f} {chv[lid]:7.3f}  {b['C'][1][:48]:48s}  {b['A'][0]:.3f} {b['A'][1][:44]:44s}  {b['M'][0]:.3f} {b['M'][1][:40]}")
for name, d in (("max(C,A)", allv), ("C only", chv)):
    bins = {"<=0.10": 0, "0.10-0.15": 0, "0.15-0.25": 0, ">0.25": 0}
    for v in d.values():
        bins["<=0.10" if v <= 0.10 else "0.10-0.15" if v <= 0.15 else "0.15-0.25" if v <= 0.25 else ">0.25"] += 1
    print(f"\ndistribution of {name} over 37 shapes: {bins}")
    for bound in (0.10, 0.15, 0.25):
        keep = [l for l, v in d.items() if v <= bound]
        print(f"   bound {bound:.2f}: shapes kept {len(keep)}, clusters {len({cluster(l) for l in keep})}")
