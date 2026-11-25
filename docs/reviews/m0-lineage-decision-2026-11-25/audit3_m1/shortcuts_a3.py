# ruff: noqa
"""Attempt 2 (attempt 1 kept as shortcuts_a3_attempt1.py: several of its rules were the correct procedure on items where the omitted step is idle, e.g. no drain below L3; they are now applied only where the step is active).
Audit 3 of M1: my own cheap-rule battery, per lineage and level. Seed 5 (audit throwaway), N items per level.
Base rate = the most frequent answer fitted on the even-indexed half and scored on the odd-indexed half (held out); echo_best_pos likewise fitted on one half
and scored on the other. Every other heuristic is fixed in advance and scored on all N. Reported: rate, rate - base, and a two-sided 95% half-width.
Heuristics read the structured form (the key check showed text and keys agree); none uses the answer.
Usage: PYTHONHASHSEED=0 PYTHONPATH=<impl> uv run --locked --offline python shortcuts_a3.py N out.json
"""
import json
import math
import re
import sys
from collections import Counter
from fractions import Fraction as F
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a3 import ALL_LEVELS, current_set, items

SEED = 5


def nums(q):
    return [F(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", q.replace("$", " "))]


def C(n, k):
    return math.comb(n, k) if 0 <= k <= n else 0


def fac(n):
    out, p = {}, 2
    while p * p <= n:
        while n % p == 0:
            out[p] = out.get(p, 0) + 1
            n //= p
        p += 1
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def crt_min(conds):
    x, step = 0, 1
    for m, r in conds:
        tries = 0
        while x % m != r:
            x += step
            tries += 1
            if tries > m:
                return None
        step = step * m // math.gcd(step, m)
    return x if x > 0 else step


def spec(n, s, q):
    """name -> value (or None when not applicable)."""
    h = {}
    if n == "shopping":
        h["ignore_counts"] = F(s["paid"] - sum(p for _, p in s["items"]), 100)
        h["one_item_only"] = F(s["paid"] - s["items"][0][0] * s["items"][0][1], 100)
    elif n == "speed_distance":
        legs = s["legs"]
        if s["average"]:
            h["mean_of_speeds"] = F(sum(v for _, v in legs), len(legs))
            h["last_speed"] = F(legs[-1][1])
        else:
            h["sum_speeds_x_mean_hours"] = F(sum(v for _, v in legs) * sum(t for t, _ in legs), len(legs))
            h["first_leg_only"] = F(legs[0][0] * legs[0][1])
    elif n == "pipes_work":
        h["ignore_drain"] = F(s["volume"], s["a"] + s["b"]) if s["drain"] else None
        h["one_pipe"] = F(s["volume"], s["a"])
    elif n == "percent_change":
        net = sum(p if k == "up" else -p for k, p in s["steps"])
        h["additive_percents"] = F(s["price"]) * (100 + net) / 100
        h["first_step_only"] = F(s["price"]) * (100 + s["steps"][0][1]) / 100
    elif n == "tip_split":
        h["ignore_tip"] = F(s["bill"], s["people"])
        h["no_split"] = F(s["bill"]) * (100 + s["tip"]) / 100
    elif n == "ratio_share":
        h["equal_split"] = F(s["total"], len(s["parts"]))
        h["largest_share"] = F(s["total"] * max(s["parts"]), sum(s["parts"]))
    elif n == "mixture":
        h["unweighted_mean"] = F(s["a"] + s["b"], 2) + s["packing"]
        h["ignore_packing"] = F(s["x"] * s["a"] + s["y"] * s["b"], s["x"] + s["y"]) if s["packing"] else None
    elif n == "linear_equation":
        if s["j"]:
            h["sign_error"] = F(s["m"] - s["n"], s["k"] - s["j"])
        else:
            h["ignore_constant"] = F(s["n"], s["k"])
            h["sign_error"] = F(s["n"] + s["m"], s["k"])
    elif n == "consecutive":
        h["mean_rounded"] = F(round(F(s["sum"], s["count"])))
    elif n == "ages":
        h["ignore_years"] = F(s["sum"], s["k"] + 1)
        h["years_once"] = F(s["sum"] - s["t"], s["k"] + 1)
    elif n == "average_missing":
        h["target_mean_rounded"] = F(round(F(s["mean_cents"], 100)))
    elif n == "rectangle":
        h["square"] = F(s["perimeter"], 4) ** 2
        h["width_only"] = F(s["perimeter"], 2 * (s["ratio"] + 1))
    elif n == "arithmetic_series":
        a, d, k = s["first"], s["step"], s["days"]
        h["no_growth"] = F(a * k)
        h["last_day_only"] = F(a + (k - 1) * d)
        h["off_by_one_days"] = F((k - 1) * (2 * a + (k - 2) * d), 2)
    elif n == "coins":
        h["value_over_high"] = F(s["cents"] // s["hi"])
        h["half_count"] = F(s["count"] // 2)
    elif n == "clock_duration":
        h["span_incl_waits"] = F(s["legs"][-1][1] - s["legs"][0][0])
    elif n == "fraction_remainder":
        h["both_of_original"] = F(s["start"]) - F(s["start"], s["a"]) - F(s["start"], s["b"])
        h["first_step_only"] = F(s["start"]) - F(s["start"], s["a"])
    elif n == "recurrence_iterate":
        pass  # off-by-one terms computed generically below via text is costly; done here
    elif n == "finite_differences":
        t = s["terms"]
        d1 = t[-1] - t[-2]
        h["linear_extrapolation"] = F(t[-1] + d1 * (s["ask"] - len(t)))
        dd = [t[i + 1] - t[i] for i in range(len(t) - 1)]
        d2 = [dd[i + 1] - dd[i] for i in range(len(dd) - 1)]
        h["next_term_only"] = F(t[-1] + dd[-1] + d2[-1]) if s["ask"] == len(t) + 2 else None
    elif n == "quadratic_area":
        if s["shape"] in ("rect_area", "product"):
            h["sqrt_area"] = F(math.isqrt(s["area"]))
            h["sqrt_minus_half_d"] = F(round(math.sqrt(s["area"]) - s["d"] / 2))
        elif s["shape"] == "squares":
            h["sqrt_half_sum"] = F(math.isqrt(s["total"] // 2))
            h["sqrt_half_minus_half_d"] = F(round(math.sqrt(s["total"] / 2) - s["d"] / 2))
        else:
            h["quarter_perimeter"] = F(s["perimeter"], 4)
            h["sqrt_area"] = F(math.isqrt(s["area"]))
    elif n == "tiered_pricing":
        if s["mode"] == "bill":
            h["all_at_last_rate"] = F(s["used"] * s["last_rate"], 100)
            h["all_at_first_rate"] = F(s["used"] * s["tiers"][0][1], 100)
        else:
            h["bill_over_last_rate"] = F(round(F(s["bill_cents"], s["last_rate"])))
            h["bill_over_first_rate"] = F(round(F(s["bill_cents"], s["tiers"][0][1])))
    elif n == "gcd_lcm":
        v = s["values"]
        if s["ask"] == "gcd":
            h["min_value"] = F(min(v))
            h["min_difference"] = F(min(abs(a - b) for a in v for b in v if a != b))
            h["gcd_of_two_smallest"] = F(math.gcd(*sorted(v)[:2])) if len(v) > 2 else None
        else:
            h["product"] = F(math.prod(v))
            h["max_value"] = F(max(v))
            h["lcm_of_two_largest"] = F(math.lcm(*sorted(v)[-2:])) if len(v) > 2 else None
    elif n == "crt_congruence":
        c = s["conditions"]
        h["largest_mod_remainder"] = F(max(c)[1])
        h["sum_remainders"] = F(sum(r for _, r in c))
        best = []
        for i in range(len(c)):
            x = crt_min([cc for j, cc in enumerate(c) if j != i])
            best.append(x)
        h["drop_last_condition"] = F(best[-1]) if best[-1] is not None else None
        h["product_minus_one"] = F(math.prod(m for m, _ in c) - 1)
    elif n == "prime_factors":
        f = fac(s["n"])
        a = s["ask"]
        if a == "divisors":
            h["two_pow_distinct"] = F(2 ** len(f))
            h["omega_plus_one"] = F(sum(f.values()) + 1)
        elif a == "largest":
            h["smallest_prime"] = F(min(f))
            h["largest_le_sqrt"] = F(max([p for p in f if p * p <= s["n"]] or [min(f)]))
        elif a == "distinct_sum":
            h["sum_with_multiplicity"] = F(sum(p * e for p, e in f.items()))
        else:
            h["distinct_count"] = F(len(f))
    elif n == "power_remainder":
        p, t = s["modulus"], s["terms"]
        def comb(vals):
            return (sum(vals) if s["op"] == "sum" else math.prod(vals)) % p
        h["exp_last_digit"] = F(comb([pow(b, e % 10, p) for b, e in t]))
        h["exp_mod_p"] = F(comb([pow(b, e % p, p) for b, e in t]))
        h["base_mod_p"] = F(comb([b % p for b, _ in t]))
        h["fermat_misapplied_e_mod_p_plus_1"] = F(comb([pow(b, e % (p + 1), p) for b, e in t]))
        h["one"] = F(1)
    elif n == "inclusion_exclusion":
        T, S, P, tr, a = s["total"], sum(s["sizes"]), sum(s["pairs"]), s["triple"], s["ask"]
        if tr is None:
            h["none_ignore_overlap"] = F(T - S) if a == "none" else None
            h["any_ignore_overlap"] = F(S) if a == "any" else None
            h["max_size"] = F(max(s["sizes"]))
        else:
            h["forget_triple"] = {"none": F(T - S + P), "any": F(S - P), "exactly_one": F(S - P), "exactly_two": F(P)}[a]
            h["ignore_overlaps"] = {"none": F(T - S), "any": F(S), "exactly_one": F(S - 2 * P), "exactly_two": F(P - tr)}[a]
            h["max_size"] = F(max(s["sizes"]))
    elif n == "binomial_choose":
        sh = s["shape"]
        if sh == "plain":
            h["n_times_k"] = F(s["n"] * s["k"])
            h["ordered"] = F(math.perm(s["n"], s["k"]))
        elif sh == "include":
            h["ignore_constraint"] = F(C(s["n"], s["k"]))
            h["n_minus_1_choose_k"] = F(C(s["n"] - 1, s["k"]))
        else:
            h["ignore_split"] = F(C(s["x"] + s["y"], s["k"]))
            h["sum_not_product"] = F(C(s["x"], s["j"]) + C(s["y"], s["k"] - s["j"]))
    elif n == "slot_permutations":
        D, L, rep, lead, par = s["digits"], s["length"], s["repeat"], s["lead_nonzero"], s["parity"]
        nn = len(D)
        tot = nn ** L if rep else math.perm(nn, L)
        h["ignore_all_restrictions"] = F(tot)
        npar = sum(1 for d in D if (d % 2 == 0) == (par == "even"))
        h["ignore_lead_rule"] = None if not lead else F(npar * (nn ** (L - 1) if rep else math.perm(nn - 1, L - 1)))
        h["parity_fraction_of_total"] = F(round(F(tot * npar, nn)))
        h["swap_repeat_rule"] = F(npar * (math.perm(nn - 1, L - 1) if rep else nn ** (L - 1)))
    elif n == "change_ways":
        cs, T = s["coins"], s["target"]
        h["T_over_max_plus_1"] = F(T // max(cs) + 1)
        h["T_over_min_plus_1"] = F(T // min(cs) + 1)
        h["two_smallest_coins_only"] = F(sum(1 for i in range(T // cs[0] + 1) if (T - i * cs[0]) % cs[1] == 0))
    elif n == "pigeonhole_worst_case":
        c, k = s["counts"], s["k"]
        if s["goal"] == "same":
            h["ignore_caps"] = F((k - 1) * len(c) + 1)  # right exactly when no cap bites (the min() step is idle)
            h["k_times_colours"] = F(k * len(c))
        else:
            h["sum_minus_max_plus_1"] = F(sum(c) - max(c) + 1)
            h["sum_minus_min"] = F(sum(c) - min(c))
            h["max_plus_1"] = F(max(c) + 1)
    elif n == "median_list":
        v = s["values"]
        h["unsorted_middle"] = F(v[len(v) // 2])
        h["mean_rounded"] = F(round(F(sum(v), len(v))))
        sv = sorted(v)
        h["lower_middle"] = F(sv[(len(v) - 1) // 2]) if len(v) % 2 == 0 else None
        h["mode_value"] = F(Counter(v).most_common(1)[0][0])
    elif n == "mode_tally":
        v = s["values"]
        if s["ask"] == "mode":
            h["last_value"] = F(v[-1])
            h["first_value"] = F(v[0])
            seen, fr = set(), None
            for x in v:
                if x in seen:
                    fr = x
                    break
                seen.add(x)
            h["first_repeated"] = F(fr) if fr is not None else None
            h["most_common_first_half"] = F(Counter(v[: len(v) // 2]).most_common(1)[0][0])
        else:
            h["ceil_n_over_distinct_plus_1"] = F(-(-len(v) // len(set(v))) + 1)
            h["max_count_first_half_x2"] = F(2 * Counter(v[: len(v) // 2]).most_common(1)[0][1])
    elif n == "pythagoras":
        a, b = s["legs"]
        c = s["hyp"]
        sh = s["shape"]
        if sh in ("ladder_top", "ladder_base"):
            g1, g2 = s["given"]
            h["hyp_minus_given"] = F(g1 - g2)
            h["avg"] = F(round(F(g1 + g2, 2)))
        elif sh in ("walk", "diagonal"):
            h["sum_legs"] = F(a + b)
            h["max_plus_half_min"] = F(round(max(a, b) + F(min(a, b), 2)))
        else:
            h["twice_legs"] = F(2 * (a + b))
            h["legs_plus_max"] = F(a + b + max(a, b))
        # memorised small triples scaled (3-4-5, 5-12-13, 8-15-17, 7-24-25): guess from the two given numbers
        g = sorted(s["given"])
        guess = None
        for t in ((3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)):
            for i, j in ((0, 1), (0, 2), (1, 2)):
                if g[0] * t[j] == g[1] * t[i] and g[0] % t[i] == 0:
                    kk = g[0] // t[i]
                    tri = [x * kk for x in t]
                    if sh in ("walk", "diagonal"):
                        guess = tri[2]
                    elif sh == "perimeter":
                        guess = sum(tri)
                    else:
                        guess = [x for x in tri if x not in g][0] if len(set(tri) - set(g)) == 1 else None
        h["memorised_small_triple"] = F(guess) if guess is not None else None
    elif n == "grid_perimeter":
        cells = {(y, x) for y, rr in enumerate(s["rows"]) for a, b in rr for x in range(a, b + 1)}
        nn = len(cells)
        horiz = sum(1 for (y, x) in cells if (y, x + 1) in cells)
        h["four_n"] = F(4 * nn)
        h["horizontal_only"] = F(4 * nn - 2 * horiz)
        ys = [y for y, _ in cells]
        xs = [x for _, x in cells]
        bb = 2 * (max(ys) - min(ys) + 1 + max(xs) - min(xs) + 1)
        h["bbox"] = F(bb)
        h["bbox_plus_4"] = F(bb + 4)
        h["two_n_plus_2"] = F(2 * nn + 2)
    elif n == "painted_cube":
        a, b, c = s["dims"]
        f = s["faces"]
        allp = {0: (a - 2) * (b - 2) * (c - 2), 1: 2 * ((a - 2) * (b - 2) + (a - 2) * (c - 2) + (b - 2) * (c - 2)), 2: 4 * ((a - 2) + (b - 2) + (c - 2))}[f]
        h["ignore_bottom_rule_ONLY_on_unpainted_bottom_items"] = F(allp) if s["bottom_unpainted"] else None
        h["inner_block_on_unpainted_bottom"] = F((a - 2) * (b - 2) * (c - 2)) if s["bottom_unpainted"] else None
    elif n == "division_counting":
        if s["shape"] == "pallets":
            N, k, m = s["items"], s["box"], s["crate"]
            h["full_pallets"] = F(N // (k * m))
            h["leftover_items"] = F(N % k)
            h["ceil_boxes_mod_m"] = F(-(-N // k) % m)
        else:
            N, k = s["people"], s["seats"]
            h["k_minus_remainder_ignores_exact_fit"] = F(k - N % k)
            h["remainder"] = F(N % k)
    elif n == "min_cost_packs":
        best = min(F(p, sz) for sz, p in s["packs"] + [[1, s["single"]]])
        h["relaxation_ceil"] = F(math.ceil(best * s["need"]))
    return h


def run(args):
    lid, N = args
    lin = current_set(True)[lid]
    n = lid.split(".")[1].removesuffix("_r2")
    out = {}
    for lv in ALL_LEVELS:
        its = items(lin, lv, N, SEED, "short")
        ans = [F(it.answer) for it in its]
        A, B = ans[0::2], ans[1::2]
        modeA = Counter(A).most_common(1)[0][0]
        base = sum(x == modeA for x in B) / len(B)
        modeB = Counter(B).most_common(1)[0][0]
        base2 = sum(x == modeB for x in A) / len(A)
        base = (base + base2) / 2  # two-fold held-out most-frequent-answer rate
        insample = Counter(ans).most_common(1)[0][1] / N
        # echo by position (fit on one half, score on the other, both folds)
        numl = [nums(it.question) for it in its]
        def echo_rate(idx, rng):
            ok = tot = 0
            for i in rng:
                L = numl[i]
                for pos, val in (("first", L[0] if L else None), ("last", L[-1] if L else None), ("max", max(L) if L else None), ("min", min(L) if L else None)):
                    pass
            return None
        cands = {"first": lambda L: L[0], "second": lambda L: L[1] if len(L) > 1 else None, "last": lambda L: L[-1], "max": max, "min": min,
                 "sum": lambda L: sum(L), "max_minus_min": lambda L: max(L) - min(L), "second_last": lambda L: L[-2] if len(L) > 1 else None}
        def rate(fn, idx):
            return sum(1 for i in idx if numl[i] and fn(numl[i]) == ans[i]) / len(idx)
        ev, od = list(range(0, N, 2)), list(range(1, N, 2))
        bestA = max(cands, key=lambda k: rate(cands[k], ev))
        bestB = max(cands, key=lambda k: rate(cands[k], od))
        echo = (rate(cands[bestA], od) + rate(cands[bestB], ev)) / 2
        anyecho = sum(1 for i in range(N) if ans[i] in numl[i]) / N
        rates = {f"echo_best_position[{bestA}/{bestB}]": echo}
        sp = [spec(n, it.structured, it.question) for it in its]
        names = sorted({k for d in sp for k in d})
        for k in names:
            app = [(d[k], a) for d, a in zip(sp, ans) if d.get(k) is not None]
            rates[k] = sum(1 for v, a in app if v == a) / N  # over ALL items (non-applicable count as misses)
            if len(app) < N:
                rates[k + "__within_applicable"] = sum(1 for v, a in app if v == a) / max(1, len(app))
        hw = {k: 1.96 * math.sqrt(max(r * (1 - r), 1 / N) / N) for k, r in rates.items()}
        out[str(lv)] = {"N": N, "base_heldout_mode": round(base, 4), "mode_insample": round(insample, 4), "answer_echoed_anywhere": round(anyecho, 4),
                        "rates": {k: round(v, 4) for k, v in rates.items()}, "minus_base": {k: round(v - base, 4) for k, v in rates.items()}, "halfwidth95": {k: round(v, 4) for k, v in hw.items()}}
    return lid, out


if __name__ == "__main__":
    N, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(current_set(True))
    with get_context("spawn").Pool(8) as p:
        res = dict(p.map(run, [(i, N) for i in ids], chunksize=1))
    json.dump(res, open(path, "w"), indent=1, sort_keys=True)
    for lid in ids:
        worst = []
        for lv in ALL_LEVELS:
            r = res[lid][str(lv)]
            cand = {k: v for k, v in r["rates"].items() if not k.endswith("__within_applicable")}
            k = max(cand, key=cand.get)
            worst.append(f"L{lv}:{k.split('[')[0]}={cand[k]:.2f}(b{r['base_heldout_mode']:.2f})")
        print(lid, " ".join(worst))
