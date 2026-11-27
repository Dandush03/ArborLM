# ruff: noqa
"""Audit 4 of M1: cheap-rule battery, per lineage and level, two-sided. Seed 17 (audit throwaway), N items per level.
Rules:
  * MINE ("a4:" prefix): written by the auditor for the r3 constructions, including generic fitted rules (fit on one half, score on the other, two folds):
      a4:echo_pos            the printed number at the best position (first/second/last/second-last/max/min/sum/max-min)
      a4:echo_pos_offset     the printed number at the best position plus the best constant offset c in -12..12
      a4:mode_by_visible_ask the most frequent answer among items of the same VISIBLE question type (ask / shape / goal / faces / op / k ...)
  * THEIRS ("im:" prefix): the implementer's battery `studies.m0.m1_fix3_shortcuts.spec` (imported only for its rule definitions; scoring is mine).
Base = held-out most frequent answer (two folds). Rates are over ALL items (a rule not applicable counts as a miss); the within-applicable rate is also kept.
The implementer's PROCEDURE list is recorded and judged in the report; this script does not exclude anything.
Usage: PYTHONHASHSEED=0 PYTHONPATH=<impl> uv run --locked --offline python shortcuts_a4.py N out.json [only,ids]
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from fractions import Fraction as F
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common_a4 import ALL_LEVELS, current_set, items, stem

SEED = 17


def nums(q):
    return [F(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", q.replace("$", " "))]


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


def visible_class(n, s):
    """The question type a reader sees in the text (never the answer)."""
    keys = {"ages": ("ask",), "consecutive": ("ask", "step", "count"), "coins": ("ask",), "rectangle": ("shape",), "speed_distance": ("average",), "gcd_lcm": ("ask",),
            "prime_factors": ("ask",), "inclusion_exclusion": ("ask",), "pigeonhole_worst_case": ("goal",), "mode_tally": ("ask",), "division_counting": ("shape",),
            "quadratic_area": ("shape",), "painted_cube": ("faces", "bottom_unpainted"), "recurrence_iterate": ("shape",), "tiered_pricing": ("mode",),
            "last_digit_power": ("modulus",), "slot_permutations": ("first", "last", "repeat", "length"), "median_list": (), "pythagoras": ("shape",)}
    ks = keys.get(n, ())
    return json.dumps([s.get(k) for k in ks]) + (f"|n={len(s['values'])}" if n == "mode_tally" else "")


def mine(n, s, q):
    h = {}
    L = nums(q)
    if n == "coins":
        hi_guess = s["cents"] // s["hi"] - 1
        h["a4:hi_is_value_over_hi_minus_1"] = F(hi_guess) if s["ask"] == "hi" else F(s["count"] - hi_guess)
        h["a4:min_low_coins_ceil_hi_over_lo"] = F(-(-s["hi"] // s["lo"])) if s["ask"] == "lo" else None
    elif n == "speed_distance":
        legs = s["legs"]
        if s["average"]:
            h["a4:mean_speed_rounded"] = F(round(F(sum(v for _, v in legs), len(legs))))
            h["a4:speed_of_longest_leg"] = F(max(legs)[1])
            h["a4:median_speed"] = F(sorted(v for _, v in legs)[len(legs) // 2])
        else:
            h["a4:total_hours_x_mean_speed_rounded"] = F(round(sum(t for t, _ in legs) * F(sum(v for _, v in legs), len(legs))))
    elif n == "mixture":
        x, y, a, b, p = s["x"], s["y"], s["a"], s["b"], s["packing"]
        h["a4:swapped_weights"] = F(y * a + x * b, x + y) + p
        h["a4:unweighted_mean"] = F(a + b, 2) + p
        h["a4:packing_added_once_total"] = F(x * a + y * b + p, x + y) if p else None
    elif n == "percent_change":
        net = sum(p if k == "up" else -p for k, p in s["steps"])
        h["a4:additive_percents"] = F(s["price"]) * (100 + net) / 100
    elif n == "fraction_remainder":
        h["a4:n_minus_n_over_a_minus_n_over_b"] = F(s["start"]) - F(s["start"], s["a"]) - F(s["start"], s["b"])
        h["a4:spends_not_left"] = F(s["start"], s["a"]) + (F(s["start"]) - F(s["start"], s["a"])) / s["b"]
    elif n == "ratio_share":
        h["a4:total_over_own_parts"] = F(s["total"], s["parts"][s["who"]])
        h["a4:equal_split"] = F(s["total"], len(s["parts"]))
    elif n == "tip_split":
        h["a4:tip_only_per_person"] = F(s["bill"] * s["tip"], 100 * s["people"])
    elif n == "consecutive":
        mean = F(s["sum"], s["count"])
        h["a4:middle_or_mean"] = mean if mean.denominator == 1 else None
        h["a4:mean_plus_or_minus_step"] = mean + (s["step"] if s["ask"] == "largest" else -s["step"])
    elif n == "ages":
        h["a4:sum_over_k_plus_1"] = F(round(F(s["sum"], s["k"] + 1)))
    elif n == "average_missing":
        h["a4:target_mean"] = F(round(F(s["mean_cents"], 100)))
    elif n == "rectangle":
        P = s["perimeter"]
        h["a4:square_area"] = F(P * P, 16) if (P * P) % 16 == 0 else F(round(F(P * P, 16)))
    elif n == "gcd_lcm":
        v, k = s["values"], len(s["values"])
        if s["ask"] == "lcm":
            g = math.gcd(*v)
            h["a4:product_over_gcd_pow_k_minus_1 (k>=3; a false general rule)"] = F(math.prod(v), g ** (k - 1)) if k >= 3 else None
        else:
            l = math.lcm(*v)
            h["a4:product_over_lcm_pow_k_minus_1 (k>=3; a false general rule)"] = F(math.prod(v), l ** (k - 1)) if k >= 3 else None
            h["a4:smallest_pairwise_gcd"] = F(min(math.gcd(a, b) for i, a in enumerate(v) for b in v[i + 1:])) if k >= 3 else None
    elif n == "pigeonhole_worst_case":
        c, k = s["counts"], s["k"]
        if s["goal"] == "same":
            h["a4:all_other_colours_then_k"] = F(sum(c) - max(c) + k)
            h["a4:k_minus_1_times_colours_plus_1"] = F((k - 1) * len(c) + 1)
        else:
            h["a4:sum_minus_max_plus_1"] = F(sum(c) - max(c) + 1)
    elif n == "mode_tally":
        v = s["values"]
        if s["ask"] == "others":
            for f in (4, 5, 6):
                h[f"a4:n_minus_{f}"] = F(len(v) - f)
            h["a4:distinct_values_minus_1"] = F(len(set(v)) - 1)
        else:
            c = Counter(v)
            h["a4:most_common_first_third"] = F(Counter(v[: len(v) // 3]).most_common(1)[0][0])
            h["a4:first_value_seen_three_times"] = None
            seen = Counter()
            for x in v:
                seen[x] += 1
                if seen[x] == 3:
                    h["a4:first_value_seen_three_times"] = F(x)
                    break
    elif n == "slot_permutations":
        from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST
        digs, ln, rep, first, last = s["digits"], s["length"], s["repeat"], s["first"], s["last"]
        nn = len(digs)
        f = [d for d in digs if _RULES_FIRST[first](d)]
        p = [d for d in digs if _RULES_LAST[last](d)]
        if rep:
            h["a4:independent_slots_no_overlap_correction"] = F(len(f) * len(p) * nn ** (ln - 2))
        else:
            h["a4:no_overlap_correction"] = F(len(f) * len(p) * math.perm(nn - 2, ln - 2))
            h["a4:first_then_any_ignoring_overlap_last"] = F(len(f) * math.perm(nn - 1, ln - 2) * len(p)) if ln >= 2 else None
    elif n == "change_ways":
        cs, T = s["coins"], s["target"]
        h["a4:T_over_min_coin"] = F(T // cs[0])
    elif n == "crt_congruence":
        c = s["conditions"]
        h["a4:remainder_of_first"] = F(c[0][1])
    elif n == "last_digit_power":
        p, t = s["modulus"], s["terms"]
        def comb(vals):
            return int((sum(vals) if s["op"] == "sum" else math.prod(vals)) % p)
        h["a4:exp_mod_p_minus_1_wrong_base"] = F(comb([pow(b % 10, e % (p - 1), p) for b, e in t]))
    elif n == "grid_perimeter":
        cells = {(y, x) for y, rr in enumerate(s["rows"]) for a, b in rr for x in range(a, b + 1)}
        runs = sum(len(rr) for rr in s["rows"])
        h["a4:2n_plus_2_runs"] = F(2 * len(cells) + 2 * runs)
        h["a4:4_runs_plus_2_cells"] = F(4 * runs + 2 * len(cells) - 2 * runs)
    elif n == "painted_cube":
        a, b, c = s["dims"]
        f = s["faces"]
        if f == 1:
            h["a4:six_faces_interior"] = F(2 * ((a - 2) * (b - 2) + (a - 2) * (c - 2) + (b - 2) * (c - 2)))
        if f == 0:
            h["a4:inner_block"] = F((a - 2) * (b - 2) * (c - 2))
    elif n == "inclusion_exclusion":
        if s["triple"] is not None:
            tt, sm, pp, tr = s["total"], sum(s["sizes"]), sum(s["pairs"]), s["triple"]
            h["a4:both_read_as_exactly_two"] = {"none": F(tt - sm + pp + tr), "any": F(sm - pp - tr), "exactly_one": None, "exactly_two": F(pp)}[s["ask"]]
    elif n == "median_list":
        v = s["values"]
        sv = sorted(v)
        h["a4:upper_middle"] = F(sv[len(v) // 2]) if len(v) % 2 == 0 else None
    elif n == "division_counting":
        if s["shape"] == "pallets":
            h["a4:boxes_mod_m_with_partial_box"] = F(-(-s["items"] // s["box"]) % s["crate"])
            h["a4:N_mod_km_over_k"] = F((s["items"] % (s["box"] * s["crate"])) // s["box"])
    return h


def theirs(n, s):
    from studies.m0.m1_fix3_shortcuts import spec
    try:
        return {f"im:{k}": v for k, v in spec(n, s).items()}
    except Exception as e:  # keep failures visible
        return {"im:__error__": None}


def run(args):
    lid, N = args
    lin = current_set(True)[lid]
    n = stem(lid)
    n_im = "last_digit_power" if n in ("power_remainder", "last_digit_power") else n
    out = {}
    for lv in ALL_LEVELS:
        its = items(lin, lv, N, SEED, "short")
        ans = [F(it.answer) for it in its]
        ev, od = list(range(0, N, 2)), list(range(1, N, 2))
        def heldout_mode(classes):
            r = 0
            for tr, te in ((ev, od), (od, ev)):
                by = defaultdict(Counter)
                allc = Counter()
                for i in tr:
                    by[classes[i]][ans[i]] += 1
                    allc[ans[i]] += 1
                g = allc.most_common(1)[0][0]
                r += sum(1 for i in te if (by[classes[i]].most_common(1)[0][0] if by[classes[i]] else g) == ans[i]) / len(te)
            return r / 2
        base = heldout_mode([0] * N)
        vis = [visible_class(n_im, it.structured) for it in its]
        rates = {"a4:mode_by_visible_ask": heldout_mode(vis)}
        numl = [nums(it.question) for it in its]
        cands = {"first": lambda L: L[0], "second": lambda L: L[1] if len(L) > 1 else None, "last": lambda L: L[-1], "second_last": lambda L: L[-2] if len(L) > 1 else None,
                 "max": max, "min": min, "sum": lambda L: sum(L), "max_minus_min": lambda L: max(L) - min(L)}
        def r_pos(fn, off, idx):
            return sum(1 for i in idx if numl[i] and fn(numl[i]) is not None and fn(numl[i]) + off == ans[i]) / len(idx)
        e = eo = 0
        best_names = []
        for tr, te in ((ev, od), (od, ev)):
            k0 = max(cands, key=lambda k: r_pos(cands[k], 0, tr))
            e += r_pos(cands[k0], 0, te) / 2
            k1, o1 = max(((k, o) for k in cands for o in range(-12, 13)), key=lambda ko: r_pos(cands[ko[0]], ko[1], tr))
            eo += r_pos(cands[k1], o1, te) / 2
            best_names.append(f"{k0}|{k1}{o1:+d}")
        rates["a4:echo_pos"] = e
        rates["a4:echo_pos_offset"] = eo
        sp = []
        for it in its:
            d = mine(n_im, it.structured, it.question)
            d.update(theirs(n_im, it.structured))
            sp.append(d)
        within = {}
        for k in sorted({k for d in sp for k in d}):
            app = [(d[k], a) for d, a in zip(sp, ans) if d.get(k) is not None]
            rates[k] = sum(1 for v, a in app if v == a) / N
            if len(app) < N:
                within[k] = [round(sum(1 for v, a in app if v == a) / max(1, len(app)), 4), len(app)]
        out[str(lv)] = {"N": N, "base": round(base, 4), "best_echo": best_names, "answer_echoed_anywhere": round(sum(1 for i in range(N) if ans[i] in numl[i]) / N, 4),
                        "rates": {k: round(v, 4) for k, v in rates.items()}, "minus_base": {k: round(v - base, 4) for k, v in rates.items()},
                        "within_applicable": within}
    return lid, out


if __name__ == "__main__":
    N, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(current_set(True))
    if len(sys.argv) > 3:
        ids = [i for i in ids if any(o in i for o in sys.argv[3].split(","))]
    with get_context("spawn").Pool(14) as p:
        res = dict(p.map(run, [(i, N if "digit_puzzle" not in i else min(N, 300)) for i in ids], chunksize=1))
    json.dump(res, open(path, "w"), indent=1, sort_keys=True)
    for lid in ids:
        worst = []
        for lv in ALL_LEVELS:
            r = res[lid][str(lv)]
            k = max(r["minus_base"], key=lambda x: abs(r["minus_base"][x]))
            worst.append(f"L{lv}:{k}={r['minus_base'][k]:+.3f}(b{r['base']:.3f})")
        print(lid, " ".join(worst), flush=True)
