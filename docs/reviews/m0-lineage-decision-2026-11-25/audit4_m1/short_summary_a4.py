# ruff: noqa
"""Audit 4 of M1: summary of shortcuts_a4.py output. Standard library only.
Rules judged to be the CORRECT PROCEDURE on the item class (auditor's judgement, each with a reason) are excluded from the effect distribution but listed.
Effect = rate - base (two-sided); the distribution uses max |effect| over levels and non-excluded rules, for the 33 registered candidates.
Usage: python3 short_summary_a4.py short_n2000.json"""
import json
import sys

PROC = {
    "consecutive": {"im:mean_plus_step": "for 3 numbers largest = mean + step exactly; for 4 numbers ceil(mean)+step is exact and the im rule's half-even rounding only coincides with it"},
    "division_counting": {"im:k_minus_remainder_ignores_exact_fit": "k - (N mod k) is the textbook procedure; wrong only on exact fits (~1/k)"},
    "finite_differences": {"im:next_term_when_asked_later": "one extension of the difference table when the next position is asked IS the procedure",
                           "im:next_term_only": "the same, applied to the m+2 ask (wrong there): kept as a rule"},
    "gcd_lcm": {"im:product_over_gcd_of_all": "k = 2: lcm = ab / gcd(a, b) is the textbook procedure",
                "a4:product_over_gcd_pow_k_minus_1 (k>=3; a false general rule)": "NOT cheap (needs the gcd of all values and a big product); exact by construction; listed as a construct-validity issue",
                "a4:product_over_lcm_pow_k_minus_1 (k>=3; a false general rule)": "NOT cheap (needs the lcm); exact by construction; listed as a construct-validity issue"},
    "ratio_share": {"im:largest_share": "computing the share is the procedure; the rule only guesses which person is asked",
                    "im:smallest_share": "as above"},
    "prime_factors": {"im:largest_le_sqrt": "needs trial division to sqrt(n), i.e. the full factorisation; differs from the procedure only by dropping a prime cofactor > sqrt(n)"},
    "slot_permutations": {"im:ignore_first_rule": "exact where no first-digit rule is printed ('any'), a subclass visible in the text; see the subclass measurement",
                          "im:parity_fraction_of_total": "exact where no first-digit rule is printed (symmetry); same subclass"},
    "last_digit_power": {"im:fermat_misapplied_e_mod_p_plus_1": "when the exponent is <= p the 'reduction' is idle and the rule IS direct computation; see the subclass measurement"},
}

if __name__ == "__main__":
    res = json.load(open(sys.argv[1]))
    NR = {"M1.binomial_choose_r3", "M1.digit_puzzle_r3", "M1.pythagoras_r3"}
    dist = {"<=0.10": [], "0.10-0.15": [], "0.15-0.25": [], ">0.25": []}
    print("lineage | max|effect| (rule, level) | per-level max signed effect of non-excluded rules | excluded-procedure rules with |effect|>0.10")
    for lid in sorted(res):
        stem = lid.split(".")[1].removesuffix("_r3")
        proc = PROC.get(stem, {})
        best = (0, None, None)
        per = []
        exc = {}
        for lv in range(7):
            r = res[lid][str(lv)]
            mb = r["minus_base"]
            cand = {k: v for k, v in mb.items() if k not in proc}
            k = max(cand, key=lambda x: abs(cand[x]))
            per.append(cand[k])
            if abs(cand[k]) > abs(best[0]):
                best = (cand[k], k, lv)
            for k2, v in mb.items():
                if k2 in proc and abs(v) > 0.10:
                    exc.setdefault(k2, []).append(f"L{lv}:{v:+.3f}")
        m = abs(best[0])
        tag = "<=0.10" if m <= 0.10 else "0.10-0.15" if m <= 0.15 else "0.15-0.25" if m <= 0.25 else ">0.25"
        if lid not in NR:
            dist[tag].append(lid)
        print(f"{lid}{' (NOT REGISTERED)' if lid in NR else ''} | {best[0]:+.3f} ({best[1]}, L{best[2]}) | {' '.join(f'{x:+.3f}' for x in per)} | {exc if exc else ''}")
    print()
    print("Distribution over the 33 registered candidates (max |effect| over levels, non-excluded rules):")
    for k, v in dist.items():
        print(f"  {k}: {len(v)}  {[x.split('.')[1] for x in v] if k != '<=0.10' else ''}")
    print()
    print("Rules scoring EXACTLY 0.000 at every level on >= 200 applicable items (by-construction zeros; R-13):")
    for lid in sorted(res):
        names = set()
        for lv in range(7):
            names |= set(res[lid][str(lv)]["rates"])
        for k in sorted(names):
            ok = True
            napp = 0
            for lv in range(7):
                r = res[lid][str(lv)]
                rate = r["rates"].get(k)
                w = r["within_applicable"].get(k)
                n_app = w[1] if w else r["N"]
                napp += n_app
                if rate is None or rate != 0.0:
                    ok = False
            if ok and napp >= 200 and not k.startswith("a4:echo") and k != "a4:mode_by_visible_ask":
                print(f"  {lid}: {k} (applicable items over 7 levels: {napp})")
    print()
    print("Within-applicable rates of selected rules (rate, applicable n) per level:")
    for lid, rules in (("M1.coins_r3", ["a4:hi_is_value_over_hi_minus_1", "im:value_over_high"]), ("M1.mode_tally_r3", ["a4:n_minus_4", "a4:n_minus_5", "a4:n_minus_6", "im:first_repeated", "im:most_common_first_half"]),
                       ("M1.pigeonhole_worst_case_r3", ["a4:all_other_colours_then_k", "im:ignore_caps", "a4:k_minus_1_times_colours_plus_1"]),
                       ("M1.gcd_lcm_r3", ["im:gcd_of_two_smallest", "im:lcm_of_two_largest", "a4:product_over_gcd_pow_k_minus_1 (k>=3; a false general rule)"]),
                       ("M1.last_digit_power_r3", ["im:exp_last_digit", "im:fermat_misapplied_e_mod_p_plus_1"]), ("M1.slot_permutations_r3", ["im:ignore_first_rule", "a4:no_overlap_correction"]),
                       ("M1.median_list_r3", ["im:mode_value"]), ("M1.prime_factors_r3", ["im:largest_le_sqrt"]), ("M1.speed_distance_r3", ["a4:mean_speed_rounded", "im:mean_of_speeds"])):
        for k in rules:
            row = []
            for lv in range(7):
                r = res[lid][str(lv)]
                w = r["within_applicable"].get(k)
                row.append(f"{w[0]:.3f}/{w[1]}" if w else f"all:{r['rates'].get(k, float('nan')):.3f}")
            print(f"  {lid} {k}: {' '.join(row)}")
    print()
    print("Mode by visible ask vs base (rate - base) per level:")
    for lid in sorted(res):
        v = [res[lid][str(lv)]["minus_base"]["a4:mode_by_visible_ask"] for lv in range(7)]
        if max(abs(x) for x in v) > 0.03:
            print(f"  {lid}: {' '.join(f'{x:+.3f}' for x in v)}  base {' '.join(str(res[lid][str(lv)]['base']) for lv in range(7))}")
