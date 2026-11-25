# ruff: noqa
"""Audit 4 of M1: an independent solver that reads ONLY THE QUESTION TEXT of the fix-round-3 items (never `structured`, never the generator's helpers,
never m1_fix3_verify.py). Exact arithmetic (fractions / integers), brute force or simulation where cheap. Derived from the audit-3 solver
(audit3_m1/solve_text_a3.py) with every regex rewritten for the r3 wording. Where an ordinary alternative reading exists, the key under that reading is
returned in `alt` (it is NOT a mismatch; it measures R-4 exposure).
Written by arbor-auditor (Claude Opus 5.5).
"""
import math
import re
from fractions import Fraction as F
from functools import lru_cache

NUM = r"-?\d+"


def canon(v):
    v = F(v)
    if (v * 100).denominator != 1:
        raise ValueError(f"not a two-decimal value: {v}")
    if v.denominator == 1:
        return str(v.numerator)
    sign = "-" if v < 0 else ""
    whole, cents = divmod(abs(v) * 100, 100)
    return f"{sign}{int(whole)}.{int(cents):02d}".rstrip("0")


WORD_FRAC = {"half": 2, "third": 3, "quarter": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}


def my_comb(n, k):
    if k < 0 or k > n:
        return 0
    r = F(1)
    for i in range(k):
        r = r * (n - i) / (i + 1)
    assert r.denominator == 1
    return int(r)


def stem_of(lid):
    s = lid.split(".")[1].removesuffix("_r3").removesuffix("_r2")
    return "power_remainder" if s == "last_digit_power" else s


FIRST_RULES = {
    "the first digit may not be 0": lambda d: d != 0,
    "the first digit must be odd": lambda d: d % 2 == 1,
    "the first digit must be even": lambda d: d % 2 == 0,
    "the first digit must be 5 or more": lambda d: d >= 5,
    "the first digit must be less than 5": lambda d: d < 5,
}
LAST_RULES = {
    "the last digit must be odd": lambda d: d % 2 == 1,
    "the last digit must be even": lambda d: d % 2 == 0,
    "the last digit must be 5 or more": lambda d: d >= 5,
    "the last digit must be less than 5": lambda d: d < 5,
}


def solve(lid, q):
    """Returns (key, alternatives: dict reading -> key)."""
    n = stem_of(lid)
    alt = {}
    if n == "shopping":
        buys = re.findall(r"(\d+) [A-Za-z' -]+? at \$(\d+)\.(\d\d) each", q)
        pc = re.search(r"pays with \$(\d+)\.(\d\d)", q)
        tot = sum(int(c) * (int(d) * 100 + int(ct)) for c, d, ct in buys)
        paid = int(pc.group(1)) * 100 + int(pc.group(2))
        assert paid >= tot and "How many dollars of change" in q
        return canon(F(paid - tot, 100)), alt
    if n == "speed_distance":
        legs = [(int(h), int(s)) for h, s in re.findall(r"drives for (\d+) hours? at (\d+) kilometres per hour", q)]
        assert len(legs) >= 2
        if "average speed" in q:
            v = F(sum(h * s for h, s in legs), sum(h for h, _ in legs))
            assert v.denominator == 1, "average not whole although a whole number is asked"
            alt["mean_of_speeds"] = canon(round(F(sum(s for _, s in legs), len(legs))))
            return canon(v), alt
        return canon(sum(h * s for h, s in legs)), alt
    if n == "pipes_work":
        a = int(re.search(r"One pipe adds (\d+) litres", q).group(1))
        b = int(re.search(r"second pipe adds (\d+) litres", q).group(1))
        m = re.search(r"drain removes (\d+) litres", q)
        d = int(m.group(1)) if m else 0
        vol = int(re.search(r"hold (\d+) litres\?", q).group(1))
        t, v = 0, 0
        while v < vol:
            t += 1
            v += a + b - d
        assert v == vol
        return canon(t), alt
    if n == "percent_change":
        price = int(re.search(r"costs (\d+) dollars", q).group(1))
        steps = re.findall(r"(rises|falls) by (\d+) percent", q)
        v = F(price)
        for kind, p in steps:
            v = v * (100 + (int(p) if kind == "rises" else -int(p))) / 100
        net = sum(int(p) if k == "rises" else -int(p) for k, p in steps)
        try:
            alt["percents_of_original_added"] = canon(F(price) * (100 + net) / 100)
        except ValueError:
            alt["percents_of_original_added"] = "NOT_TWO_DECIMALS"
        return canon(v), alt
    if n == "tip_split":
        bill = int(re.search(r"bill is (\d+) dollars before tip", q).group(1))
        tip = int(re.search(r"adds a (\d+) percent tip", q).group(1))
        ppl = int(re.search(r"between (\d+) people", q).group(1))
        return canon(F(bill) * (100 + tip) / 100 / ppl), alt
    if n == "ratio_share":
        m = re.match(r"(.+) share (\d+) stickers in the ratio ([\d:]+) \(in that order.*How many stickers does (\w+) get\?", q)
        names = re.split(r", | and ", m.group(1))
        tot, parts, who = int(m.group(2)), [int(x) for x in m.group(3).split(":")], m.group(4)
        assert len(names) == len(parts) and names.count(who) == 1, (names, who)
        unit = F(tot, sum(parts))
        assert unit.denominator == 1
        return canon(unit * parts[names.index(who)]), alt
    if n == "mixture":
        x, a = map(int, re.search(r"mixes (\d+) kilograms of nuts costing (\d+) dollars", q).groups())
        y, b = map(int, re.search(r"with (\d+) kilograms of raisins costing (\d+) dollars", q).groups())
        pk = re.search(r"packing cost of (\d+) dollars? per kilogram", q)
        v = F(x * a + y * b, x + y) + (int(pk.group(1)) if pk else 0)
        return canon(v), alt
    if n == "linear_equation":
        def side(op, mm):
            return int(mm) if op == "adding" else -int(mm)
        m2 = re.search(r"by (\d+) and then (adding|subtracting) (\d+) gives the same result as multiplying it by (\d+) and then (adding|subtracting) (\d+)\.", q)
        if m2:
            k, m, j, e = int(m2.group(1)), side(m2.group(2), m2.group(3)), int(m2.group(4)), side(m2.group(5), m2.group(6))
            sols = [x for x in range(-20000, 20001) if k * x + m == j * x + e]
        else:
            m1 = re.search(r"by (\d+) and then (adding|subtracting) (\d+) gives (-?\d+)\.", q)
            k, m, rhs = int(m1.group(1)), side(m1.group(2), m1.group(3)), int(m1.group(4))
            sols = [x for x in range(-20000, 20001) if k * x + m == rhs]
        assert len(sols) == 1, sols
        return canon(sols[0]), alt
    if n == "consecutive":
        m = re.search(r"The sum of (\d+) (consecutive integers|consecutive numbers that each differ from the next by 2) \(listed.*?\) is (-?\d+)\. What is the (largest|smallest)", q)
        cnt, step, s, ask = int(m.group(1)), (1 if m.group(2) == "consecutive integers" else 2), int(m.group(3)), m.group(4)
        # solve n*a + step*n(n-1)/2 = s exactly, then confirm by summation
        a = F(s - step * cnt * (cnt - 1) // 2, cnt)
        assert a.denominator == 1
        a = int(a)
        assert sum(a + step * i for i in range(cnt)) == s
        return canon(a + step * (cnt - 1) if ask == "largest" else a), alt
    if n == "ages":
        m = re.search(r"(\w+) is (\d+) times as old as (\w+) now\. In (\d+) years? from now, their two ages added together will be (\d+)\..*How old is (\w+) now", q)
        n1, k, n2, t, s, who = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5)), m.group(6)
        sols = [b for b in range(0, 5000) if (k * b + t) + (b + t) == s]
        assert len(sols) == 1 and who in (n1, n2) and n1 != n2
        return canon(sols[0] if who == n2 else k * sols[0]), alt
    if n == "average_missing":
        m = re.search(r"has scored ([\d, ]+) on (\d+) tests,.*mean of all (\d+) tests exactly ([\d.]+)\?", q)
        sc = [int(x) for x in m.group(1).split(", ")]
        assert len(sc) == int(m.group(2)) and int(m.group(3)) == len(sc) + 1
        sols = [x for x in range(0, 101) if F(sum(sc) + x, len(sc) + 1) == F(m.group(4))]
        assert len(sols) == 1
        return canon(sols[0]), alt
    if n == "rectangle":
        if (m := re.search(r"perimeter of (\d+) centimetres and its length is (\d+) times its width", q)):
            P, k = map(int, m.groups())
            sols = [w * k * w for w in range(1, P) if 2 * (w + k * w) == P]
        else:
            P, d = map(int, re.search(r"perimeter of (\d+) centimetres and its length is (\d+) centimetres more than its width", q).groups())
            sols = [w * (w + d) for w in range(1, P) if 2 * (w + w + d) == P]
        assert len(sols) == 1
        return canon(sols[0]), alt
    if n == "arithmetic_series":
        a, d, days = map(int, re.search(r"saves (\d+) dollars on day 1 and then saves (\d+) dollars more each day.*after (\d+) days", q).groups())
        assert "both included" in q
        tot, cur = 0, a
        for _ in range(days):
            tot += cur
            cur += d
        return canon(tot), alt
    if n == "coins":
        lo, hi, cnt, cents, ask = map(int, re.search(r"only (\d+)-cent coins and (\d+)-cent coins\. It holds (\d+) coins worth (\d+) cents in all\. How many (\d+)-cent", q).groups())
        sols = [(i, cnt - i) for i in range(cnt + 1) if i * lo + (cnt - i) * hi == cents]
        assert len(sols) == 1
        return canon(sols[0][0] if ask == lo else sols[0][1]), alt
    if n == "clock_duration":
        legs = re.findall(r"leaves at (\d\d):(\d\d) and arrives at (\d\d):(\d\d)", q)
        tot, prev = 0, -1
        for h1, m1, h2, m2 in legs:
            a, b = int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)
            assert prev <= a < b
            prev = b
            # minute-by-minute count (not a subtraction)
            tot += sum(1 for _ in range(a, b))
        return canon(tot), alt
    if n == "fraction_remainder":
        m = re.search(r"has (\d+) dollars\. \w+ spends one (\w+) of it on books, then one (\w+) of what is left", q)
        v = F(int(m.group(1)))
        v -= v / WORD_FRAC[m.group(2)]
        v -= v / WORD_FRAC[m.group(3)]
        assert v.denominator == 1
        return canon(v), alt
    if n == "recurrence_iterate":
        pos = int(re.search(r"What is the number in position (\d+)", q).group(1))
        if (m := re.search(r"The first two numbers are (\d+) and (\d+)\. Every number after those is the sum of the two numbers just before it", q)):
            t = [int(m.group(1)), int(m.group(2))]
            step = lambda t: t[-1] + t[-2]
        elif (m := re.search(r"The first number is (\d+)\. Every number after it is (\d+) times the number just before it, (plus|minus) (\d+)", q)):
            t = [int(m.group(1))]
            c, d = int(m.group(2)), int(m.group(4)) * (1 if m.group(3) == "plus" else -1)
            step = lambda t: c * t[-1] + d
        else:
            m = re.search(r"The first number is (\d+)\. Every number after it is the number just before it plus (?:(\d+) times )?its own position in the list", q)
            t = [int(m.group(1))]
            s = int(m.group(2)) if m.group(2) else 1
            step = lambda t: t[-1] + s * (len(t) + 1)
        while len(t) < pos:
            t.append(step(t))
        return canon(t[pos - 1]), alt
    if n == "finite_differences":
        m = re.search(r"The first (\d+) numbers of a pattern are ([\d, and-]+?)\. The pattern.*degree (\d+) in its position.*position (\d+)\?", q)
        terms = [int(x) for x in re.findall(NUM, m.group(2))]
        deg, ask = int(m.group(3)), int(m.group(4))
        assert len(terms) == int(m.group(1))
        # difference table (not Lagrange): extend the deg-th differences as constant, after checking they are constant
        rows = [terms[:]]
        while len(rows) <= deg:
            r = rows[-1]
            rows.append([r[i + 1] - r[i] for i in range(len(r) - 1)])
        assert len(set(rows[deg])) == 1 and rows[deg][0] != 0
        rows = [r[:] for r in rows]
        while len(rows[0]) < ask:
            rows[deg].append(rows[deg][-1])
            for i in range(deg - 1, -1, -1):
                rows[i].append(rows[i][-1] + rows[i + 1][-1])
        return canon(rows[0][ask - 1]), alt
    if n == "quadratic_area":
        if "has an area of" in q and "Its length is" in q:
            A, d = map(int, re.search(r"area of (\d+) square metres\. Its length is (\d+) metres more", q).groups())
            sols = [x for x in range(1, math.isqrt(A) + 1) if x * (x + d) == A]
        elif "perimeter of" in q:
            P, A = map(int, re.search(r"perimeter of (\d+) metres and an area of (\d+) square", q).groups())
            sols = sorted({max(w, P // 2 - w) for w in range(1, P // 2) if P % 2 == 0 and w * (P // 2 - w) == A})
        elif "their product is" in q:
            d, A = map(int, re.search(r"differ by (\d+), and their product is (\d+)", q).groups())
            sols = [x for x in range(1, math.isqrt(A) + 1) if x * (x + d) == A]
        else:
            d, S = map(int, re.search(r"differ by (\d+), and the sum of their squares is (\d+)", q).groups())
            sols = [x for x in range(1, math.isqrt(S) + 1) if x * x + (x + d) ** 2 == S]
        assert len(sols) == 1, sols
        return canon(sols[0]), alt
    if n == "tiered_pricing":
        first = re.search(r"the first (\d+) units cost (\d+) cents each", q)
        tiers = [(int(first.group(1)), int(first.group(2)))] + [(int(u), int(c)) for u, c in re.findall(r"the next (\d+) units cost (\d+) cents each", q)]
        last = int(re.search(r"every unit after that costs (\d+) cents each", q).group(1))
        def bill(u):
            tot, left = 0, u
            for size, rate in tiers:
                take = min(size, left)
                tot += take * rate
                left -= take
            return tot + left * last
        m = re.search(r"What is the bill for (\d+) units", q)
        if m:
            return canon(F(bill(int(m.group(1))), 100)), alt
        B = F(re.search(r"bill is ([\d.]+) dollars", q).group(1)) * 100
        sols = [u for u in range(0, 20000) if bill(u) == B]
        assert len(sols) == 1
        return canon(sols[0]), alt
    if n == "gcd_lcm":
        if "ribbons of lengths" in q:
            vals = [int(x) for x in re.findall(r"\d+", re.search(r"ribbons of lengths ([\d, and]+) centimetres", q).group(1))]
            assert len(vals) == int(re.search(r"has (\d+) ribbons", q).group(1))
            g = max(L for L in range(1, min(vals) + 1) if all(v % L == 0 for v in vals))
            return canon(g), alt
        vals = [int(x) for x in re.findall(r"every (\d+) seconds", q)]
        assert len(vals) == int(re.search(r"(\d+) lights flash", q).group(1))
        mx = max(vals)
        t = mx
        while any(t % v for v in vals):
            t += mx
        return canon(t), alt
    if n == "crt_congruence":
        conds = [(int(m), int(r)) for m, r in re.findall(r"dividing it by (\d+) leaves remainder (\d+)", q, flags=re.I)]
        # sieve over multiples of the largest modulus
        conds_s = sorted(conds, reverse=True)
        M0, R0 = conds_s[0]
        P = math.prod(m for m, _ in conds)
        x = R0 if R0 > 0 else M0
        while not all(x % m == r for m, r in conds):
            x += M0
            assert x <= P + M0
        return canon(x), alt
    if n == "prime_factors":
        N = int(re.search(r"Consider the number (\d+)\.", q).group(1))
        fac, m, p = {}, N, 2
        while p * p <= m:
            while m % p == 0:
                fac[p] = fac.get(p, 0) + 1
                m //= p
            p += 1
        if m > 1:
            fac[m] = fac.get(m, 0) + 1
        if "How many different positive whole numbers divide it" in q:
            v = sum(1 for d in range(1, math.isqrt(N) + 1) if N % d == 0 for _ in ((0,) if d * d == N else (0, 1)))
        elif "largest prime" in q:
            v = max(fac)
        elif "Add up the different prime" in q:
            v = sum(fac)
        else:
            assert "How many primes are multiplied" in q
            v = sum(fac.values())
        return canon(v), alt
    if n == "power_remainder":
        p = int(re.search(r"divided by (\d+) \(a whole number from 0 to (\d+)\)", q).group(1))
        if "Let X be the product of all the following factors" in q:
            terms = [(int(e), int(b)) for e, b in re.findall(r"(\d+) factors equal to (\d+)", q)]
            X = 1
            for e, b in terms:
                X = X * pow(b, e)  # exact big integer, reduced only at the end
            return canon(X % p), alt
        terms = [(int(e), int(b)) for e, b in re.findall(r"the product of (\d+) factors, each equal to (\d+)", q)]
        if "Let X be the sum of" in q:
            X = sum(b ** e for e, b in terms)
        else:
            assert len(terms) == 1
            X = terms[0][1] ** terms[0][0]
        return canon(X % p), alt
    if n == "inclusion_exclusion":
        total = int(re.match(r"(\d+) people were asked", q).group(1))
        if "do all three" in q:
            m = re.search(r"\. (\d+) [a-z ]+?, (\d+) [a-z ]+? and (\d+) [a-z ]+?; (\d+) do both the first and the second, (\d+) do both the first and the third, (\d+) do both the second and the third, and (\d+) do all three", q)
            A, B, C, AB, AC, BC, ABC = map(int, m.groups())
            # brute force over the 8 Venn regions: enumerate abc, the 'do both' numbers include abc (stated)
            reg = {"abc": ABC, "ab": AB - ABC, "ac": AC - ABC, "bc": BC - ABC}
            reg["a"] = A - reg["ab"] - reg["ac"] - ABC
            reg["b"] = B - reg["ab"] - reg["bc"] - ABC
            reg["c"] = C - reg["ac"] - reg["bc"] - ABC
            reg["none"] = total - sum(reg.values())
            assert min(reg.values()) >= 0
            ones, twos = reg["a"] + reg["b"] + reg["c"], reg["ab"] + reg["ac"] + reg["bc"]
            # alternative reading: 'do both' = exactly those two (excluding abc)
            r2 = {"abc": ABC, "ab": AB, "ac": AC, "bc": BC}
            r2["a"] = A - AB - AC - ABC
            r2["b"] = B - AB - BC - ABC
            r2["c"] = C - AC - BC - ABC
            r2["none"] = total - sum(r2.values())
            okalt = min(r2.values()) >= 0
        else:
            m = re.search(r"\. (\d+) of them [a-z ]+?, (\d+) of them [a-z ]+?, and (\d+) of them do both", q)
            A, B, AB = map(int, m.groups())
            reg = {"ab": AB, "a": A - AB, "b": B - AB}
            reg["none"] = total - sum(reg.values())
            assert min(reg.values()) >= 0
            ones, twos = reg["a"] + reg["b"], reg["ab"]
            r2, okalt = None, False
        if "do none of" in q:
            key = reg["none"]
            ak = r2["none"] if okalt else None
        elif "at least one" in q:
            key = total - reg["none"]
            ak = total - r2["none"] if okalt else None
        elif "exactly one" in q:
            key = ones
            ak = r2["a"] + r2["b"] + r2["c"] if okalt else None
        else:
            key = twos
            ak = r2["ab"] + r2["ac"] + r2["bc"] if okalt else None
        if r2 is not None:
            alt["both_excludes_all_three"] = canon(ak) if ak is not None else "IMPOSSIBLE"
        return canon(key), alt
    if n == "binomial_choose":
        m = re.search(r"A group has (.*?)\. A team of (\d+) people is chosen .*?with exactly (.*?) on it\.", q)
        have = {w: int(c) for c, w in re.findall(r"(\d+) (women|men|children)", m.group(1))}
        pick = {}
        for c, w in re.findall(r"(\d+) (women|woman|men|man|children|child)", m.group(3)):
            pick[{"woman": "women", "man": "men", "child": "children"}.get(w, w)] = int(c)
        assert sum(pick.values()) == int(m.group(2)) and set(pick) == set(have)
        v = 1
        for w in have:
            v *= my_comb(have[w], pick[w])
        return canon(v), alt
    if n == "slot_permutations":
        s = int(re.search(r"How many (\d+)-digit codes", q).group(1))
        mm = re.search(r"only the digits ([\d, and]+?), if (.*)\? Answer", q)
        digits = [int(x) for x in re.findall(r"\d", mm.group(1))]
        rules = re.split(r", | and ", mm.group(2))
        rep = "a digit may be used more than once" in rules
        assert rep != ("no digit may be used more than once" in rules)
        first = [FIRST_RULES[r] for r in rules if r in FIRST_RULES]
        last = [LAST_RULES[r] for r in rules if r in LAST_RULES]
        explicit_zero = any("may be 0" in r or "may not be 0" in r for r in rules) or "may be 0 (a code such as" in q
        assert len(last) == 1 and len(first) <= 1
        f = first[0] if first else (lambda d: True)
        g = last[0]

        def count(no_lead_zero):
            @lru_cache(None)
            def c(pos, mask):
                if pos == s:
                    return 1
                tot = 0
                for d in digits:
                    if not rep and mask >> d & 1:
                        continue
                    if pos == 0 and (not f(d) or (no_lead_zero and d == 0)):
                        continue
                    if pos == s - 1 and not g(d):
                        continue
                    tot += c(pos + 1, mask | (1 << d))
                return tot
            return c(0, 0)
        key = count(False)
        if 0 in digits and not explicit_zero:
            alt["no_leading_zero_when_unstated"] = canon(count(True))
        return canon(key), alt
    if n == "change_ways":
        coins = [int(x) for x in re.findall(r"\d+", re.search(r"coins worth ([\d, and]+) cents", q).group(1))]
        T = int(re.search(r"exactly (\d+) cents be paid", q).group(1))
        # dynamic programme over coins (not the generator's loop order: coin-major on a dict)
        ways = {0: 1}
        for c in coins:
            new = {}
            for v, w in ways.items():
                k = 0
                while v + k * c <= T:
                    new[v + k * c] = new.get(v + k * c, 0) + w
                    k += 1
            ways = new
        return canon(ways.get(T, 0)), alt
    if n == "pigeonhole_worst_case":
        counts = [int(x) for x in re.findall(r"(\d+) [a-z]+(?:,|\.)", re.search(r"colours: (.*?)\. Marbles", q).group(1) + ".")]
        assert len(counts) == int(re.search(r"marbles of (\d+) colours", q).group(1))
        if "one marble of every colour" in q:
            worst = max(sum(counts) - c for c in counts)
            return canon(worst + 1), alt
        k = int(re.search(r"at least (\d+) marbles of the same colour", q).group(1))
        assert max(counts) >= k
        worst = sum(min(c, k - 1) for c in counts)
        return canon(worst + 1), alt
    if n == "median_list":
        vals = [int(x) for x in re.findall(r"\d+", re.search(r"The values are ([\d, and]+)\. What", q).group(1))]
        s = sorted(vals)
        L = len(s)
        med = F(s[L // 2]) if L % 2 else F(s[L // 2 - 1] + s[L // 2], 2)
        return canon(med), alt
    if n == "mode_tally":
        m = re.search(r"wrote down (\d+) test scores: ([\d, and]+)\. ", q)
        vals = [int(x) for x in re.findall(r"\d+", m.group(2))]
        assert len(vals) == int(m.group(1))
        cnt = {}
        for v in vals:
            cnt[v] = cnt.get(v, 0) + 1
        top = max(cnt.values())
        modes = [v for v, c in cnt.items() if c == top]
        assert len(modes) == 1
        if "Which value occurs most often" in q:
            return canon(modes[0]), alt
        assert "How many of the scores are not equal to the value that occurs most often" in q
        alt["distinct_other_values"] = canon(len(cnt) - 1)
        return canon(len(vals) - top), alt
    if n == "digit_puzzle":
        nd = int(re.search(r"Find the (\d)-digit number", q).group(1))
        clues_txt = re.search(r"all of these are true: (.*)\. There is exactly one", q).group(1).split("; ")
        def rev(x):
            return int(str(x)[::-1].lstrip("0") or "0")
        def holds(x, c, exactly_one=False):
            ds = [int(ch) for ch in str(x)]
            if (m := re.fullmatch(r"its digits add up to (\d+)", c)):
                return sum(ds) == int(m.group(1))
            if (m := re.fullmatch(r"the product of its digits is (\d+)", c)):
                return math.prod(ds) == int(m.group(1))
            if c.startswith("the number made by writing its digits in the opposite order"):
                if c.endswith("is the same as it"):
                    return rev(x) == x
                m = re.search(r"is (\d+) (more|less) than it$", c)
                return rev(x) - x == (int(m.group(1)) if m.group(2) == "more" else -int(m.group(1)))
            if (m := re.fullmatch(r"it is a multiple of (\d+)", c)):
                return x % int(m.group(1)) == 0
            if c in ("it is even", "it is odd"):
                return (x % 2 == 0) == (c == "it is even")
            if c == "its first digit is larger than its last digit":
                return ds[0] > ds[-1]
            if c == "its first digit is smaller than its last digit":
                return ds[0] < ds[-1]
            if (m := re.fullmatch(r"it is greater than (\d+)", c)):
                return x > int(m.group(1))
            if (m := re.fullmatch(r"it is less than (\d+)", c)):
                return x < int(m.group(1))
            if (m := re.fullmatch(r"the digit (\d) appears in it at least once", c)):
                d = int(m.group(1))
                return ds.count(d) == 1 if exactly_one else d in ds
            if (m := re.fullmatch(r"its first and last digits differ by (\d) \(in either order\)", c)):
                return abs(ds[0] - ds[-1]) == int(m.group(1))
            if c == "no two of its digits are the same":
                return len(set(ds)) == len(ds)
            if c == "its middle digit is exactly halfway between its first and last digits":
                return 2 * ds[1] == ds[0] + ds[2]
            if (m := re.fullmatch(r"its first digit is (\d) times its last digit", c)):
                return ds[0] == int(m.group(1)) * ds[-1]
            raise ValueError("unknown clue: " + c)
        rng = range(10 ** (nd - 1), 10 ** nd)
        sols = [x for x in rng if all(holds(x, c) for c in clues_txt)]
        assert len(sols) == 1, sols
        sa = [x for x in rng if all(holds(x, c, True) for c in clues_txt)]
        alt["contains_means_exactly_one"] = canon(sa[0]) if len(sa) == 1 else f"NOT_UNIQUE:{len(sa)}"
        return canon(sols[0]), alt
    if n == "pythagoras":
        def sq(v):
            r = math.isqrt(v)
            assert r * r == v
            return r
        if (m := re.search(r"A ladder (\d+) metres long leans against a vertical wall\. Its foot is (\d+) metres from the base", q)):
            c, a = map(int, m.groups())
            return canon(sq(c * c - a * a)), alt
        if (m := re.search(r"A ladder (\d+) metres long leans against a vertical wall and its top reaches (\d+) metres up", q)):
            c, b = map(int, m.groups())
            return canon(sq(c * c - b * b)), alt
        if (m := re.search(r"walks (\d+) metres due east and then (\d+) metres due north", q)):
            a, b = map(int, m.groups())
            return canon(sq(a * a + b * b)), alt
        if (m := re.search(r"screen is (\d+) centimetres wide and (\d+) centimetres tall", q)):
            a, b = map(int, m.groups())
            return canon(sq(a * a + b * b)), alt
        a, b = map(int, re.search(r"short sides \(the sides next to the right angle\) of (\d+) centimetres and (\d+) centimetres", q).groups())
        return canon(a + b + sq(a * a + b * b)), alt
    if n == "grid_perimeter":
        cells = set()
        for rno, rtxt in re.findall(r"Row (\d+) \(counting from the top\): (.*?)\.(?= Row| Squares)", q):
            if rtxt == "no squares":
                continue
            for part in rtxt.split(", "):
                if (m := re.fullmatch(r"columns (\d+) to (\d+)", part)):
                    for x in range(int(m.group(1)), int(m.group(2)) + 1):
                        cells.add((int(rno), x))
                else:
                    cells.add((int(rno), int(re.fullmatch(r"column (\d+)", part).group(1))))
        assert "belong to exactly one square" in q
        # count each unit edge's owners (edge-incidence counting, not the neighbour test)
        own = {}
        for (y, x) in cells:
            for e in (("h", y, x), ("h", y + 1, x), ("v", y, x), ("v", y, x + 1)):
                own[e] = own.get(e, 0) + 1
        key = sum(1 for v in own.values() if v == 1)
        iso = sum(1 for (y, x) in cells if all((y + dy, x + dx) not in cells for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))))
        alt["sides_of_isolated_squares"] = canon(4 * iso)
        # outer boundary only (holes not counted): flood fill from outside
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        y0, y1, x0, x1 = min(ys) - 1, max(ys) + 1, min(xs) - 1, max(xs) + 1
        outside = {(y0, x0)}
        stack = [(y0, x0)]
        while stack:
            y, x = stack.pop()
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                p = (y + dy, x + dx)
                if y0 <= p[0] <= y1 and x0 <= p[1] <= x1 and p not in cells and p not in outside:
                    outside.add(p); stack.append(p)
        outer = sum(1 for (y, x) in cells for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)) if (y + dy, x + dx) in outside)
        alt["outer_boundary_only_holes_excluded"] = canon(outer)
        return canon(key), alt
    if n == "painted_cube":
        a, b, c = map(int, re.search(r"box (\d+) cubes long, (\d+) cubes wide and (\d+) cubes high", q).groups())
        f = int(re.search(r"have exactly (\d+) painted face", q).group(1))
        bottom_unp = "except the bottom face" in q
        # brute force over every cube when small, else by region classes
        if a * b * c <= 30000:
            cnt = 0
            for x in range(a):
                for y in range(b):
                    for z in range(c):
                        p = (x == 0) + (x == a - 1) + (y == 0) + (y == b - 1) + (z == c - 1) + ((z == 0) and not bottom_unp)
                        cnt += p == f
            return canon(cnt), alt
        xs = {0: a - 2, 1: 2}
        zc = {0: c - 2, 1: 2} if not bottom_unp else {0: c - 1, 1: 1}
        cnt = sum(nx * ny * nz for px, nx in xs.items() for py, ny in {0: b - 2, 1: 2}.items() for pz, nz in zc.items() if px + py + pz == f)
        return canon(cnt), alt
    if n == "division_counting":
        if (m := re.search(r"makes (\d+) .*? boxes that each hold exactly (\d+) .*? pallets that each hold (\d+) boxes", q)):
            N, k, mm = map(int, m.groups())
            boxes, left = 0, N
            while left >= k:
                left -= k
                boxes += 1
            while boxes >= mm:
                boxes -= mm
            return canon(boxes), alt
        N, k = map(int, re.search(r"(\d+) people must travel by bus.*Each bus has (\d+) seats", q).groups())
        buses = 0
        while buses * k < N:
            buses += 1
        return canon(buses * k - N), alt
    raise KeyError(lid)
