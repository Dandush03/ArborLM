# ruff: noqa
"""Final M1 audit: levels.
(1) No-op test: for every pair of levels (21 pairs) build 300 items from the SAME random stream at both levels; a pair is flagged if every item is byte-identical
    (question, answer and structured), i.e. the level is ignored. Also: number of distinct texts among 2,000 items per level.
(2) Parameter profile: 2,000 items per level from a fresh stream; every numeric leaf of the structured form is flattened (lists -> their length and their max);
    per level the observed MAX and MEAN of each feature; features whose observed max rises strictly over levels 0..6 are listed; the stated parameter (from the
    lineage's docstring / LEVEL_PARAMETER) is reported explicitly with its observed max per level; plus mean and median log10(|answer|+1) and mean count of printed numbers.
Seeds: SEEDS['levels'] (2611253), labels 'noop' and 'profile'."""
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from fractions import Fraction as F
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import SEEDS, items, stem, survivors
from studies.m0.core import build_item, stream

# stated parameter -> a function of the structured form (and text) whose observed max per level should rise
STATED = {
    "mixture": ("max price per kg (30 + 6L)", lambda s, q: max(s["a"], s["b"])),
    "average_missing": ("'marked out of' M (100 + 10L)", lambda s, q: int(re.search(r"marked out of (\d+)", q).group(1))),
    "clock_duration": ("longest ride (110 + 6L) + longest visible wait", lambda s, q: max(b - a for a, b in s["legs"]) + max([s["legs"][i + 1][0] - s["legs"][i][1] for i in range(len(s["legs"]) - 1)] or [0])),
    "gcd_lcm": ("answer (ceiling: GCD_LCM_TABLE)", lambda s, q: math.lcm(*s["values"]) if s["ask"] == "lcm" else math.gcd(*s["values"])),
    "finite_differences": ("answer (ceiling: fd_answer_ceiling)", None),
    "ages": ("younger age (70 + 10L)", lambda s, q: (s["sum"] - 2 * s["t"]) // (s["k"] + 1)),
    "arithmetic_series": ("days (12 + 3L)", lambda s, q: s["days"]),
    "change_ways": ("target T", lambda s, q: s["target"]),
    "consecutive": ("first number range (4000 + 2000L) via |sum|", lambda s, q: abs(s["sum"])),
    "crt_congruence": ("largest modulus x count", lambda s, q: max(m for m, _ in s["conditions"]) * 100 + len(s["conditions"])),
    "division_counting": ("number of items / people", lambda s, q: s.get("items", s.get("people"))),
    "fraction_remainder": ("start (3000 + 500L)", lambda s, q: s["start"]),
    "grid_perimeter": ("number of squares (13 + 3L)", lambda s, q: sum(b - a + 1 for row in s["rows"] for a, b in row)),
    "inclusion_exclusion": ("total", lambda s, q: s["total"]),
    "last_digit_power": ("number of terms x largest exponent", lambda s, q: len(s["terms"]) * 10000 + max(e for _, e in s["terms"])),
    "linear_equation": ("|answer| (no range stated in the docstring)", None),
    "median_list": ("number of values (10 + 2L)", lambda s, q: len(s["values"])),
    "painted_cube": ("largest dimension (30 + 4L)", lambda s, q: max(s["dims"])),
    "percent_change": ("price", lambda s, q: s["price"]),
    "pipes_work": ("volume", lambda s, q: s["volume"]),
    "prime_factors": ("N (nmax(level))", lambda s, q: s["n"]),
    "quadratic_area": ("answer x (150 + 25L)", None),
    "ratio_share": ("total", lambda s, q: s["total"]),
    "rectangle": ("perimeter", lambda s, q: s["perimeter"]),
    "recurrence_iterate": ("position (9 + 2L)", lambda s, q: s["position"]),
    "shopping": ("number of item lines", lambda s, q: len(s["items"])),
    "speed_distance": ("number of legs", lambda s, q: len(s["legs"])),
    "tiered_pricing": ("number of tiers x units", lambda s, q: len(s["tiers"]) * 10000 + (s["used"] or 0)),
    "tip_split": ("bill (400 + 100L)", lambda s, q: s["bill"]),
}


def flat(x, p=""):
    out = {}
    if isinstance(x, bool):
        out[p] = int(x)
    elif isinstance(x, (int, float)):
        out[p] = x
    elif isinstance(x, dict):
        for k in sorted(x):
            out.update(flat(x[k], f"{p}.{k}" if p else k))
    elif isinstance(x, (list, tuple)):
        out[f"len({p})"] = len(x)
        leaves = [v for v in flat_list(x)]
        if leaves:
            out[f"max({p})"] = max(leaves)
    return out


def flat_list(x):
    for v in x:
        if isinstance(v, (list, tuple)):
            yield from flat_list(v)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            yield v


def nums(q):
    return re.findall(r"(?<![\w.])\d+(?:\.\d+)?", q)


def run(lid):
    lin = survivors()[lid]
    st = stem(lid)
    # (1) no-op
    same = []
    seqs = {}
    for L in range(7):
        r = stream(SEEDS["levels"], "final-m1-a5", "noop", lid)
        seqs[L] = [json.dumps([it.question, it.answer, it.structured], sort_keys=True) for it in (build_item(lin, L, r, "A", str(i)) for i in range(300))]
    for a in range(7):
        for b in range(a + 1, 7):
            if seqs[a] == seqs[b]:
                same.append([a, b])
    # (2) profile
    prof = {}
    feats = defaultdict(dict)
    stated = []
    distinct = []
    for L in range(7):
        its = items(lin, L, 2000, SEEDS["levels"], "profile")
        distinct.append(len({it.question for it in its}))
        fl = [flat(it.structured) for it in its]
        for k in sorted({k for d in fl for k in d}):
            vals = [d[k] for d in fl if k in d]
            feats[k][L] = [max(vals), round(statistics.fmean(vals), 3)]
        la = [math.log10(abs(float(F(it.answer))) + 1) for it in its]
        prof[L] = {"mean_log10_answer": round(statistics.fmean(la), 3), "median_log10_answer": round(statistics.median(la), 3), "max_answer": max(abs(F(it.answer)) for it in its).__str__(),
                   "mean_printed_numbers": round(statistics.fmean(len(nums(it.question)) for it in its), 2)}
        fn = STATED[st][1]
        stated.append(max(fn(it.structured, it.question) for it in its) if fn else max(abs(F(it.answer)) for it in its))
    rising = sorted(k for k, d in feats.items() if len(d) == 7 and all(d[i][0] < d[i + 1][0] for i in range(6)))
    nondec = sorted(k for k, d in feats.items() if len(d) == 7 and all(d[i][0] <= d[i + 1][0] for i in range(6)) and d[0][0] < d[6][0])
    adj_diff = []
    for L in range(6):
        ks = [k for k, d in feats.items() if (L in d) != (L + 1 in d) or (L in d and L + 1 in d and (d[L][0] != d[L + 1][0] or abs(d[L][1] - d[L + 1][1]) > 0.05 * (abs(d[L][1]) + 1)))]
        adj_diff.append(len(ks))
    st_vals = [float(x) for x in stated]
    return lid, {"identical_level_pairs": same, "distinct_texts_of_2000": distinct, "profile": prof, "stated_parameter": STATED[st][0], "stated_observed_max": [str(x) for x in stated],
                 "stated_strictly_rising": all(st_vals[i] < st_vals[i + 1] for i in range(6)), "stated_nondecreasing": all(st_vals[i] <= st_vals[i + 1] for i in range(6)),
                 "features_max_strictly_rising": rising, "features_max_nondecreasing_and_rising": nondec, "adjacent_pairs_features_differing": adj_diff,
                 "features": {k: {str(L): v for L, v in d.items()} for k, d in feats.items()}}


if __name__ == "__main__":
    ids = sorted(survivors())
    with get_context("spawn").Pool(14) as p:
        res = dict(p.map(run, ids, chunksize=1))
    json.dump(res, open(sys.argv[1], "w"), indent=1, sort_keys=True)
    for lid in ids:
        r = res[lid]
        print(f"{lid}: identical pairs {r['identical_level_pairs']}; distinct texts/2000 {r['distinct_texts_of_2000']}; adjacent pairs differing in #features {r['adjacent_pairs_features_differing']}")
        print(f"   stated: {r['stated_parameter']}: observed max {r['stated_observed_max']} strictly rising={r['stated_strictly_rising']} non-decreasing={r['stated_nondecreasing']}")
        print(f"   mean log10 answer {[r['profile'][L]['mean_log10_answer'] for L in range(7)]}; median {[r['profile'][L]['median_log10_answer'] for L in range(7)]}; printed numbers {[r['profile'][L]['mean_printed_numbers'] for L in range(7)]}")
        print(f"   features with strictly rising max: {r['features_max_strictly_rising']}")
