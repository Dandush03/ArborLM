# ruff: noqa
"""Two-sided shortcut reading for the lineages whose generator redraws items against a shortcut (auditor's own code).

For each, a COUNTERFACTUAL copy of the builder's parameter draw with the anti-shortcut rejection removed (written by the auditor from reading the
generator; only the numbers that matter are drawn) is compared with the REAL generator (imported read-only). A heuristic whose rate in the real
generator is far BELOW its counterfactual rate is an anti-cue: a solver who knows the rule can exclude that candidate (overshoot).
Also reports the candidate-set size where elimination matters (closed-ish answer sets: last digits, list values).

Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python <this> [N]
"""
import math
import random
import sys
from collections import Counter
from fractions import Fraction
from functools import reduce

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_common import load_batch

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
LINS = {x.id: x for x in load_batch()}


def real(lid, lv):
    r = stream(777007, "overshoot", lid, str(lv))
    return [build_item(LINS[lid], lv, r, "A", "x") for _ in range(N)]


def first_rep(v):
    return next(x for i, x in enumerate(v) if x in v[:i])


def mode_cf(lv, r):
    hi = 12 + 6 * lv; f = r.randint(3, 5 + lv); m = r.randint(4, 6 + lv)
    pool = r.sample(range(1, hi + 1), m)
    counts = [f] + [r.randint(1, f - 1) for _ in range(m - 1)]
    vals = [v for v, c in zip(pool, counts) for _ in range(c)]
    r.shuffle(vals)
    return vals, pool[0], f


def report_mode():
    print("== mode_tally (ask = mode): P(first repeated value is the mode), P(last number is the mode), mean number of distinct values")
    for lv in ALL_LEVELS:
        its = [it for it in real("M1.mode_tally", lv) if it.structured["ask"] == "mode"]
        fr = sum(first_rep(it.structured["values"]) == int(it.answer) for it in its) / len(its)
        ln = sum(it.structured["values"][-1] == int(it.answer) for it in its) / len(its)
        r = random.Random(1000 + lv)
        cf = [mode_cf(lv, r) for _ in range(N)]
        frc = sum(first_rep(v) == md for v, md, _ in cf) / N
        lnc = sum(v[-1] == md for v, md, _ in cf) / N
        md_ = sum(len(set(it.structured["values"])) for it in its) / len(its)
        print(f"  L{lv}: real first_rep {fr:.3f} vs counterfactual {frc:.3f} | real last_number {ln:.3f} vs cf {lnc:.3f} | distinct values {md_:.1f} (uniform guess {1/md_:.3f}, excluding first_rep {1/(md_-1):.3f})")


def report_last_digit():
    print("== last_digit_power: answer distribution and base-digit/exponent structure")
    for lv in ALL_LEVELS:
        its = real("M1.last_digit_power", lv)
        ans = Counter(it.answer for it in its)
        e4 = Counter((b % 10, e % 4) for it in its for b, e in it.structured["terms"])
        forced = sum(1 for it in its for b, e in it.structured["terms"] if b % 10 in (4, 9))
        nterms = sum(len(it.structured["terms"]) for it in its)
        # shortcut: ignore the exponent for bases ending 4 or 9 (always even exponent -> 6 or 1); for 2,3,7,8 use the square's last digit
        def guess(it, f):
            vals = [f(b % 10) for b, _ in it.structured["terms"]]
            return (sum(vals) if it.structured["op"] == "sum" else math.prod(vals)) % 10
        sq = sum(guess(it, lambda d: d * d % 10) == int(it.answer) for it in its) / N
        bd = sum(guess(it, lambda d: d) == int(it.answer) for it in its) / N
        print(f"  L{lv}: top answers {ans.most_common(4)} | terms with base digit 4/9 (exponent forced even, value forced 6/1): {forced}/{nterms} | "
              f"'square of base digit' guess {sq:.3f} | 'base digit' guess {bd:.3f} | e mod 4 by digit: {sorted(Counter((d, k) for (d, k) in e4.elements()).items())[:12]}")
    print("  counterfactual (no rejection, t=1): P(answer == base digit) for base digits 2,3,7,8 is 1/4 (e = 1 mod 4); generator makes it 0, so the answer set is the 3 other cycle values.")


def report_gcd():
    print("== gcd_lcm: share of gcd items whose gcd equals the smallest pairwise difference (real vs counterfactual), lcm items with coprime pair")
    for lv in ALL_LEVELS:
        its = real("M1.gcd_lcm", lv)
        g = [it for it in its if it.structured["ask"] == "gcd"]
        sd = sum(min(abs(a - b) for i, a in enumerate(it.structured["values"]) for b in it.structured["values"][:i]) == int(it.answer) for it in g) / max(1, len(g))
        r = random.Random(2000 + lv); k = 2 if lv < 3 else (3 if lv < 5 else 4); hit = tot = 0
        for _ in range(N):
            gg = r.randint(2, 12 + 3 * lv); vals = [gg * r.randint(2, 14 + 6 * lv) for _ in range(k)]
            if len(set(vals)) < k:
                continue
            a = reduce(math.gcd, vals); tot += 1
            hit += min(abs(x - y) for i, x in enumerate(vals) for y in vals[:i]) == a
        print(f"  L{lv}: real 'smallest pairwise difference' {sd:.3f} vs counterfactual {hit/tot:.3f}")


def report_change():
    print("== change_ways: rate of 'target // biggest coin + 1' real vs counterfactual (no ans==that rejection; 4<=ans<=150 kept)")
    for lv in ALL_LEVELS:
        its = real("M1.change_ways", lv)
        rr = sum(it.structured["target"] // max(it.structured["coins"]) + 1 == int(it.answer) for it in its) / N
        r = random.Random(3000 + lv); hit = tot = 0
        while tot < N:
            coins = sorted(r.sample((2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25), 3))
            t = r.randint(max(coins) * 3, max(60 + 15 * lv, max(coins) * 3 + 30))
            w = [1] + [0] * t
            for v in coins:
                for a in range(v, t + 1):
                    w[a] += w[a - v]
            if w[t] < 4 or w[t] > 150:
                continue
            tot += 1; hit += t // max(coins) + 1 == w[t]
        print(f"  L{lv}: real {rr:.3f} vs counterfactual {hit/tot:.3f}")


def report_median():
    print("== median_list (table shape): 'median of distinct values' real vs counterfactual; even-count share")
    for lv in (3, 4, 5, 6):
        its = [it for it in real("M1.median_list", lv) if it.structured["shape"] == "table"]
        def md(vs):
            s = sorted(vs); n = len(s); return Fraction(s[(n - 1) // 2] + s[n // 2], 2)
        rr = sum(md([v for v, _ in it.structured["values"]]) == Fraction(it.answer) for it in its) / max(1, len(its))
        r = random.Random(4000 + lv); hit = 0
        for _ in range(N):
            rows = r.randint(4, 5 + lv // 2); hi = 30 + 20 * lv
            vs = sorted(r.sample(range(1, hi), rows)); r.shuffle(vs); tab = [[v, r.randint(1, 6)] for v in vs]
            hit += md([v for v, c in tab for _ in range(c)]) == md(vs)
        lst = [it for it in real("M1.median_list", lv) if it.structured["shape"] == "list"]
        ev = sum(len(it.structured["values"]) % 2 == 0 for it in lst) / max(1, len(lst))
        print(f"  L{lv}: real {rr:.3f} vs counterfactual {hit/N:.3f}; list items with even count {ev:.3f}")


def report_quadratic():
    print("== quadratic_area: author's isqrt heuristics real vs counterfactual d ~ U[3, 3 + max(2, hi//2)]; and P(answer < d)")
    for lv in ALL_LEVELS:
        its = real("M1.quadratic_area", lv)
        def h(st):
            if st["shape"] == "rect_perimeter":
                return st["perimeter"] // 4
            return math.isqrt(st["area"] or st["total"] // 2)
        rr = sum(h(it.structured) == int(it.answer) for it in its) / N
        r = random.Random(5000 + lv); hit = 0; hi = 30 + 10 * lv
        for _ in range(N):
            x = r.randint(2, hi); d = r.randint(3, 3 + max(2, hi // 2)); sh = r.choice(("rect_area", "rect_perimeter", "product", "squares"))
            if sh == "rect_perimeter":
                hit += (2 * (x + x + d)) // 4 == x + d
            elif sh == "squares":
                hit += math.isqrt((x * x + (x + d) ** 2) // 2) == x
            else:
                hit += math.isqrt(x * (x + d)) == x
        lt = sum(int(it.answer) < (it.structured["d"] or 10**9) for it in its if it.structured["shape"] != "rect_perimeter") / max(1, sum(it.structured["shape"] != "rect_perimeter" for it in its))
        print(f"  L{lv}: real {rr:.3f} vs counterfactual {hit/N:.3f}; P(answer < d) {lt:.3f}")


def report_min_cost():
    print("== min_cost_packs: share of items where the optimum equals each naive plan, real (redrawn) vs counterfactual (first draw accepted)")
    def naive(need, single, packs):
        big = max(packs, key=lambda p: p[0]); unit = min(packs, key=lambda pq: Fraction(pq[1], pq[0]))
        c = lambda a, b: -(-a // b)
        return [need * single, (need // big[0]) * big[1] + (need % big[0]) * single, c(need, big[0]) * big[1], (need // unit[0]) * unit[1] + (need % unit[0]) * single, c(need, unit[0]) * unit[1]]
    def best(n, single, packs):
        top = n + max(p for p, _ in packs); cost = [0] + [10**9] * top
        for i in range(1, top + 1):
            cost[i] = min([cost[i - 1] + single] + [cost[i - p] + q for p, q in packs if i >= p])
        return min(cost[n:])
    for lv in ALL_LEVELS:
        its = real("M1.min_cost_packs", lv)
        rr = [0] * 5; none_r = 0
        for it in its:
            s = it.structured; nv = naive(s["need"], s["single"], s["packs"]); b = int(it.answer)
            for i in range(5):
                rr[i] += nv[i] == b
            none_r += b not in nv
        r = random.Random(6000 + lv); cf = [0] * 5; none_c = tot = 0; npk = 2 + (lv >= 5)
        while tot < N:
            single = r.randint(2, 9); packs = []
            for _ in range(npk):
                size = r.randint(3, 6 + 2 * lv + 3 * len(packs)); packs.append([size, r.randint(max(2, size * single // 2 + 1), size * single + size // 2)])
            if len({p for p, _ in packs}) < npk:
                continue
            packs.sort(); need = r.randint(max(p for p, _ in packs) + 3, 25 + 10 * lv)
            b = best(need, single, packs); nv = naive(need, single, packs); tot += 1
            for i in range(5):
                cf[i] += nv[i] == b
            none_c += b not in nv
        print(f"  L{lv}: real naive-plan hit rates {[round(x/N,3) for x in rr]} none {none_r/N:.3f} | counterfactual {[round(x/tot,3) for x in cf]} none {none_c/tot:.3f} | real min-of-naive {sum(min(naive(it.structured['need'], it.structured['single'], it.structured['packs'])) == int(it.answer) for it in its)/N:.3f}")


def report_tiered():
    print("== tiered_pricing: no rejection in the builder; used > every tier boundary always. Shares: 'units mode' and answer stated anywhere")
    for lv in ALL_LEVELS:
        its = real("M1.tiered_pricing", lv)
        um = sum(it.structured["mode"] == "units" for it in its) / N
        print(f"  L{lv}: units-mode share {um:.3f}")


if __name__ == "__main__":
    report_mode(); report_last_digit(); report_gcd(); report_change(); report_median(); report_quadratic(); report_min_cost(); report_tiered()
