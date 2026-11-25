# ruff: noqa
"""Summarise shortcuts_out_N1000.json. Heuristics tagged PARTIAL execute the lineage's procedure but ignore one stated condition / ask, or are an
alternative CORRECT formula; they measure condition-sensitivity, not shortcuts, and are reported separately.
Screening reading used for display only (the author's own screening rule, not a registered threshold): rate >= max(0.25, 2 x constant rate).
Run: uv run --locked --offline python shortcuts_summarise.py shortcuts_out_N1000.json
"""
import json
import sys

PARTIAL = {
    "spec:O:quadratic_diffs_for_any_degree", "spec:O:one_step_even_if_two_asked", "spec:O:extra_step",
    "spec:O:top_plus_bottom_plus_2rows_plus_steps",
    "spec:O:triple_sign_error", "spec:O:any_formula_whatever_ask", "spec:O:none_any_swapped",
    "spec:O:e_mod4_zero_bug", "spec:O:power_e_plus_1", "spec:O:power_e_minus_1",
    "spec:O:exactly_need_dp", "spec:O:min_of_all_five_naive", "spec:O:best_unit_ceil_or_floor_better",
    "spec:O:lower_middle_no_average", "spec:O:upper_middle_no_average",
    "O:most_common_number",  # for mode_tally this IS the procedure for ask=mode
    "spec:O:mode_of_first_half", "spec:O:mode_of_second_half", "spec:O:true_mode_count_minus_1",
    "spec:O:all_faces_formula_always", "spec:O:inner_with_c_minus_1",
    "spec:O:hyp_always", "spec:O:leg_always",
    "spec:O:C(n-1,k-1)_always", "spec:A:plain_ignoring_condition",
    "spec:O:always_no_leading_zero", "spec:O:ignore_parity", "spec:O:ignore_leading_zero_rule", "spec:O:repeat_rule_flipped", "spec:O:parity_flipped", "spec:A:unconstrained", "spec:A:unconstrained_half_parity",
    "spec:O:skip_middle_tiers", "spec:O:off_by_one_tier_boundary", "spec:O:answer_in_cents", "spec:O:units_cap_plus_rest_at_last_rate_floor",
    "spec:O:ceil_of_product", "spec:O:floor_b_minus_floor_a",
    "spec:O:product_over_gcd_all", "spec:O:other_operation", "spec:A:op_of_first_two_only", "spec:O:gcd_of_last_two_or_lcm",
    "spec:O:largest_prime_le_29_dividing", "spec:O:sum_with_multiplicity", "spec:O:distinct_count", "spec:O:two_pow_distinct", "spec:O:omega_plus_one",
    "spec:O:term_n_minus_1", "spec:O:term_n_plus_1",
    "spec:O:two_smallest_coins_only", "spec:O:two_largest_coins_only", "spec:O:smallest_and_largest_only",
    "spec:A:first_two_only", "spec:O:constant_deficit_trick", "spec:O:constant_remainder_trick",
    "spec:O:larger_root_instead",
    "spec:O:smallest_fit_first_two", "spec:O:largest_fit_first_two", "spec:O:smallest_fit_all_but_last",
    "spec:O:cap_at_k_plus1", "spec:A:capped_sum_no_plus1",
}
d = json.load(open(sys.argv[1]))
print(f"{'lineage':28s} {'best SURFACE heuristic (level)':55s} rate  const const_ho | flag(screen) | author's worst | best PARTIAL (level) rate")
for lid, rec in sorted(d.items()):
    best_s = (None, None, -1); best_p = (None, None, -1); best_a = (None, None, -1)
    flags = []
    for lv, r in rec.items():
        c = r["const_rate"]
        for k, v in r["rates"].items():
            if k.startswith("oracle"):
                continue
            if k in PARTIAL:
                if v > best_p[2]:
                    best_p = (k, lv, v)
                continue
            if v > best_s[2]:
                best_s = (k, lv, v)
            if (k.startswith("A:") or k.startswith("spec:A:")) and v > best_a[2]:
                best_a = (k, lv, v)
            if v >= max(0.25, 2 * c):
                flags.append(f"{k}@L{lv}={v:.3f}")
    k, lv, v = best_s
    r = rec[lv]
    print(f"{lid:28s} {k + ' (L' + lv + ')':55s} {v:.3f} {r['const_rate']:.3f} {r['const_heldout']:.3f} | {';'.join(flags) or '-'} | {best_a[0]} L{best_a[1]} {best_a[2]:.3f} | {best_p[0]} L{best_p[1]} {best_p[2]:.3f}")
print()
print("Per level: constant (most-frequent-answer) rate, held-out constant rate, oracle 'answer is a printed number', best surface heuristic rate")
for lid, rec in sorted(d.items()):
    cells = []
    for lv, r in sorted(rec.items()):
        bs = max((v for k, v in r["rates"].items() if not k.startswith("oracle") and k not in PARTIAL), default=0)
        cells.append(f"L{lv} c{r['const_rate']:.3f}/h{r['const_heldout']:.3f}/o{r['rates'].get('oracle:answer_is_a_printed_number', 0):.2f}/s{bs:.3f}")
    print(f"{lid:28s} " + "  ".join(cells))
print()
print("Author's named worst cases, re-measured:")
for lid, name in (("M1.mode_tally", "A:last_number"), ("M1.last_digit_power", None), ("M1.painted_cube", "spec:A:inner_block")):
    rec = d[lid]
    if name is None:
        top = max(((k, lv, v) for lv, r in rec.items() for k, v in r["rates"].items() if (k.startswith("A:") or k.startswith("spec:A:"))), key=lambda t: t[2])
        print(f"  {lid}: author's heuristics, max over levels: {top[0]} L{top[1]} {top[2]:.3f}; all A: per level " + str({lv: {k: v for k, v in r['rates'].items() if k.startswith('A:') or k.startswith('spec:A:')} for lv, r in rec.items()}))
    else:
        print(f"  {lid} {name}: " + ", ".join(f"L{lv} {r['rates'][name]:.3f}" for lv, r in sorted(rec.items())))
