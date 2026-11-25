# ruff: noqa
"""Audit 3 of M1: an independent solver that reads ONLY THE QUESTION TEXT (never `structured`, never the generator's helpers), exact arithmetic
(fractions / integers), brute force where it is cheap. It also returns, where an ordinary alternative reading exists, the key under that reading.
Written by arbor-auditor (Claude Opus 5.5) without reading the implementer's second solvers.
"""
import math
import re
from fractions import Fraction as F
from itertools import permutations, product

NUM = r"-?\d+"


def canon(v):
    """Canonical answer text: integer, or a decimal with at most two places and no trailing zeros. Raises if not representable."""
    v = F(v)
    if (v * 100).denominator != 1:
        raise ValueError(f"not a two-decimal value: {v}")
    if v.denominator == 1:
        return str(v.numerator)
    s = f"{abs(v.numerator) * 100 // v.denominator:d}"
    sign = "-" if v < 0 else ""
    whole, cents = divmod(abs(v) * 100, 100)
    return f"{sign}{int(whole)}.{int(cents):02d}".rstrip("0")


def ints(s):
    return [int(x) for x in re.findall(NUM, s)]


def body(q):
    """Drop a leading setting sentence if present is NOT needed: every regex below anchors on problem words, not on positions."""
    return q


WORD_FRAC = {"half": 2, "third": 3, "quarter": 4, "fifth": 5, "sixth": 6}


def my_comb(n, k):
    if k < 0 or k > n:
        return 0
    r = F(1)
    for i in range(k):
        r = r * (n - i) / (i + 1)
    assert r.denominator == 1
    return int(r)


def solve(lid, q):
    """Returns (key, alternatives: dict reading -> key or None)."""
    n = lid.split(".")[1].removesuffix("_r2")  # attempt 1 forgot the suffix: every rev2 lineage errored (keys_trial_n20.json kept)
    alt = {}
    if n == "shopping":
        buys = re.findall(r"(\d+) [A-Za-z' -]+? at \$(\d+)\.(\d\d) each", q)
        paid = re.search(r"pays with \$(\d+)\.(\d\d)", q)
        tot = sum(int(c) * (int(d) * 100 + int(ct)) for c, d, ct in buys)
        pc = int(paid.group(1)) * 100 + int(paid.group(2))
        assert pc >= tot
        return canon(F(pc - tot, 100)), alt
    if n == "speed_distance":
        legs = [(int(h), int(s)) for h, s in re.findall(r"drives for (\d+) hours at (\d+) kilometres per hour", q)]
        if "average speed" in q:
            return canon(F(sum(h * s for h, s in legs), sum(h for h, _ in legs))), alt
        return canon(sum(h * s for h, s in legs)), alt
    if n == "pipes_work":
        a = int(re.search(r"One pipe adds (\d+) litres", q).group(1))
        b = int(re.search(r"second pipe adds (\d+) litres", q).group(1))
        m = re.search(r"drain removes (\d+) litres", q)
        d = int(m.group(1)) if m else 0
        vol = int(re.search(r"hold (\d+) litres\?", q).group(1))
        # minute-by-minute simulation (not a division)
        t, v = 0, 0
        while v < vol:
            t += 1
            v += a + b - d
        assert v == vol, "volume not reached exactly at a whole minute"
        return canon(t), alt
    if n == "percent_change":
        price = int(re.search(r"costs (\d+) dollars", q).group(1))
        v = F(price)
        for kind, p in re.findall(r"(rises|falls) by (\d+) percent", q):
            v = v * (100 + (int(p) if kind == "rises" else -int(p))) / 100
        return canon(v), alt
    if n == "tip_split":
        bill = int(re.search(r"bill is (\d+) dollars", q).group(1))
        tip = int(re.search(r"adds a (\d+) percent tip", q).group(1))
        ppl = int(re.search(r"between (\d+) people", q).group(1))
        return canon(F(bill) * (100 + tip) / 100 / ppl), alt
    if n == "ratio_share":
        m = re.match(r"(.+) share (\d+) stickers in the ratio ([\d:]+) \(in that order\)\. How many stickers does (\w+) get\?", q)
        names = re.split(r", | and ", m.group(1))
        tot, parts, who = int(m.group(2)), [int(x) for x in m.group(3).split(":")], m.group(4)
        assert len(names) == len(parts) and names.count(who) == 1
        unit = F(tot, sum(parts))
        assert unit.denominator == 1
        return canon(unit * parts[names.index(who)]), alt
    if n == "mixture":
        x, a = map(int, re.search(r"mixes (\d+) kilograms of nuts costing (\d+) dollars", q).groups())
        y, b = map(int, re.search(r"with (\d+) kilograms of raisins costing (\d+) dollars", q).groups())
        pk = re.search(r"packing cost of (\d+) dollars per kilogram", q)
        v = F(x * a + y * b, x + y) + (int(pk.group(1)) if pk else 0)
        return canon(v), alt
    if n == "linear_equation":
        def side(op, mm):
            return int(mm) if op == "adding" else -int(mm)
        m2 = re.search(r"by (\d+) and then (adding|subtracting) (\d+) gives the same result as multiplying it by (\d+) and then (adding|subtracting) (\d+)\.", q)
        sols = []
        if m2:
            k, m, j, e = int(m2.group(1)), side(m2.group(2), m2.group(3)), int(m2.group(4)), side(m2.group(5), m2.group(6))
            for x in range(-5000, 5001):
                if k * x + m == j * x + e:
                    sols.append(x)
        else:
            m1 = re.search(r"by (\d+) and then (adding|subtracting) (\d+) gives (-?\d+)\.", q)
            k, m, rhs = int(m1.group(1)), side(m1.group(2), m1.group(3)), int(m1.group(4))
            sols = [x for x in range(-5000, 5001) if k * x + m == rhs]
        assert len(sols) == 1, sols
        return canon(sols[0]), alt
    if n == "consecutive":
        m = re.search(r"The sum of (\d+) (consecutive integers|consecutive numbers that differ by 2) is (-?\d+)", q)
        cnt, step, s = int(m.group(1)), (1 if m.group(2) == "consecutive integers" else 2), int(m.group(3))
        sols = [a + step * (cnt - 1) for a in range(-10000, 10000) if sum(a + step * i for i in range(cnt)) == s]
        assert len(sols) == 1
        return canon(sols[0]), alt
    if n == "ages":
        k, t, s = map(int, re.search(r"is (\d+) times as old as \w+\. In (\d+) years, their ages will add up to (\d+)\.", q).groups())
        sols = [b for b in range(0, 1000) if (k * b + t) + (b + t) == s]
        assert len(sols) == 1
        return canon(sols[0]), alt
    if n == "average_missing":
        m = re.search(r"has scored ([\d, ]+) on (\d+) tests\..*mean of all (\d+) tests exactly ([\d.]+)\?", q)
        sc = [int(x) for x in m.group(1).split(", ")]
        assert len(sc) == int(m.group(2)) and int(m.group(3)) == len(sc) + 1
        mean = F(m.group(4))
        need = mean * (len(sc) + 1) - sum(sc)
        assert need.denominator == 1
        return canon(need), alt
    if n == "rectangle":
        P, k = map(int, re.search(r"perimeter of (\d+) centimetres and its length is (\d+) times its width", q).groups())
        sols = [w * k * w for w in range(1, P) if 2 * (w + k * w) == P]
        assert len(sols) == 1
        return canon(sols[0]), alt
    if n == "arithmetic_series":
        a, d, days = map(int, re.search(r"saves (\d+) dollars on day 1 and then saves (\d+) dollars more each day.*after (\d+) days", q).groups())
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
        tot = 0
        prev = -1
        for h1, m1, h2, m2 in legs:
            a, b = int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)
            assert prev <= a < b
            prev = b
            tot += b - a
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
        m = re.search(r"The first two numbers are (\d+) and (\d+)\. Every number after those is the sum of the two numbers just before it", q)
        if m:
            t = [int(m.group(1)), int(m.group(2))]
            while len(t) < pos:
                t.append(t[-1] + t[-2])
            return canon(t[pos - 1]), alt
        m = re.search(r"The first number is (\d+)\. Every number after it is (\d+) times the number just before it, (plus|minus) (\d+)", q)
        if m:
            t = [int(m.group(1))]
            c, d = int(m.group(2)), int(m.group(4)) * (1 if m.group(3) == "plus" else -1)
            while len(t) < pos:
                t.append(c * t[-1] + d)
            return canon(t[pos - 1]), alt
        m = re.search(r"The first number is (\d+)\. Every number after it is the number just before it plus its own position", q)
        t = [int(m.group(1))]
        while len(t) < pos:
            t.append(t[-1] + (len(t) + 1))
        return canon(t[pos - 1]), alt
    if n == "finite_differences":
        m = re.search(r"The first (\d+) numbers of a pattern are ([\d, and-]+?)\. The pattern.*degree (\d+) in its position.*position (\d+)\?", q)
        terms = [int(x) for x in re.findall(NUM, m.group(2))]
        deg, ask = int(m.group(3)), int(m.group(4))
        assert len(terms) == int(m.group(1))
        # Lagrange interpolation through the first deg+1 points, then check every printed term (so the degree claim is verified)
        pts = list(enumerate(terms, start=1))
        def lag(x, pp):
            s = F(0)
            for i, (xi, yi) in enumerate(pp):
                term = F(yi)
                for j, (xj, _) in enumerate(pp):
                    if i != j:
                        term *= F(x - xj, xi - xj)
                s += term
            return s
        base = pts[: deg + 1]
        assert all(lag(x, base) == y for x, y in pts), "printed terms are not a polynomial of the stated degree"
        # and the degree is exact (not lower): the deg-th difference is non-zero
        lower = pts[:deg]
        assert not all(lag(x, lower) == y for x, y in pts)
        v = lag(ask, base)
        assert v.denominator == 1
        return canon(v), alt
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
            g = max(L for L in range(1, min(vals) + 1) if all(v % L == 0 for v in vals))
            return canon(g), alt
        vals = [int(x) for x in re.findall(r"every (\d+) seconds", q)]
        assert len(vals) == int(re.search(r"(\d+) lights flash", q).group(1))
        # step through multiples of the largest period
        mx = max(vals)
        t = mx
        while any(t % v for v in vals):
            t += mx
        return canon(t), alt
    if n == "crt_congruence":
        conds = [(int(m), int(r)) for m, r in re.findall(r"dividing it by (\d+) leaves remainder (\d+)", q, flags=re.I)]
        # sieve: combine one condition at a time (not a brute force over 1..P)
        x, step = 0, 1
        for m, r in conds:
            while x % m != r:
                x += step
            step = step * m // math.gcd(step, m)
        if x == 0:
            x = step
        assert x > 0 and all(x % m == r for m, r in conds)
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
            v = sum(1 for d in range(1, N + 1) if N % d == 0) if N < 2_000_000 else math.prod(e + 1 for e in fac.values())
        elif "largest prime" in q:
            v = max(fac)
        elif "Add up the different prime" in q:
            v = sum(fac)
        else:
            v = sum(fac.values())
        return canon(v), alt
    if n == "power_remainder":
        p = int(re.search(r"divided by (\d+)\?", q).group(1))
        terms = [(int(e), int(b)) for e, b in re.findall(r"(\d+) factors,? (?:each )?equal to (\d+)", q)]
        if "Let X be the product of all the following factors" in q or len(terms) == 1:
            X = 1
            for e, b in terms:
                X *= b ** e
        else:
            assert "Let X be the sum of" in q
            X = sum(b ** e for e, b in terms)
        return canon(X % p), alt
    if n == "inclusion_exclusion":
        total = int(re.match(r"(\d+) people were asked", q).group(1))
        if "do all three" in q:
            m = re.search(r"\. (\d+) [a-z ]+?, (\d+) [a-z ]+? and (\d+) [a-z ]+?; (\d+) do both the first and the second, (\d+) do both the first and the third, (\d+) do both the second and the third, and (\d+) do all three", q)
            A, B, C, AB, AC, BC, ABC = map(int, m.groups())
            # brute force: reconstruct the 8 Venn regions, check non-negative, then count
            reg = {"abc": ABC, "ab": AB - ABC, "ac": AC - ABC, "bc": BC - ABC}
            reg["a"] = A - reg["ab"] - reg["ac"] - ABC
            reg["b"] = B - reg["ab"] - reg["bc"] - ABC
            reg["c"] = C - reg["ac"] - reg["bc"] - ABC
            reg["none"] = total - sum(reg.values())
            assert min(reg.values()) >= 0
            ones, twos = reg["a"] + reg["b"] + reg["c"], reg["ab"] + reg["ac"] + reg["bc"]
        else:
            m = re.search(r"\. (\d+) of them [a-z ]+?, (\d+) of them [a-z ]+?, and (\d+) of them do both", q)
            A, B, AB = map(int, m.groups())
            reg = {"ab": AB, "a": A - AB, "b": B - AB}
            reg["none"] = total - sum(reg.values())
            assert min(reg.values()) >= 0
            ones, twos = reg["a"] + reg["b"], reg["ab"]
        if "do none of" in q:
            return canon(reg["none"]), alt
        if "at least one" in q:
            return canon(total - reg["none"]), alt
        if "exactly one" in q:
            return canon(ones), alt
        return canon(twos), alt
    if n == "binomial_choose":
        m = re.search(r"A group has (\d+) women and (\d+) men\. A team of (\d+) people is chosen .*with exactly (\d+) wom[ae]n", q)
        if m:
            x, y, k, j = map(int, m.groups())
            return canon(my_comb(x, j) * my_comb(y, k - j)), alt
        nn, k = map(int, re.search(r"A club has (\d+) members.*A committee of (\d+) members", q).groups())
        if "must be on it" in q:
            return canon(my_comb(nn - 1, k - 1)), alt
        return canon(my_comb(nn, k)), alt
    if n == "slot_permutations":
        s = int(re.search(r"How many (\d+)-digit codes", q).group(1))
        digits = [int(x) for x in re.findall(r"\d", re.search(r"only the digits ([\d, and]+), if", q).group(1))]
        rep = "a digit may be used more than once" in q
        assert rep != ("no digit may be used more than once" in q)
        lead = "the first digit may not be 0" in q
        par = re.search(r"the last digit must be (even|odd)", q).group(1)
        # DP over positions with a bitmask of used digits
        from functools import lru_cache
        @lru_cache(None)
        def cnt(pos, mask, lead_ok):
            if pos == s:
                return 1
            tot = 0
            for d in digits:
                if not rep and mask >> d & 1:
                    continue
                if pos == 0 and lead and d == 0:
                    continue
                if pos == s - 1 and (d % 2 == 0) != (par == "even"):
                    continue
                tot += cnt(pos + 1, mask | (1 << d), lead_ok)
            return tot
        key = cnt(0, 0, True)
        cnt.cache_clear()
        return canon(key), alt
    if n == "change_ways":
        coins = [int(x) for x in re.findall(r"\d+", re.search(r"coins worth ([\d, and]+) cents", q).group(1))]
        T = int(re.search(r"exactly (\d+) cents be paid", q).group(1))
        a, b, c = coins
        w = 0
        for i in range(T // a + 1):
            for j in range((T - i * a) // b + 1):
                if (T - i * a - j * b) % c == 0:
                    w += 1
        return canon(w), alt
    if n == "pigeonhole_worst_case":
        counts = [int(x) for x in re.findall(r"(\d+) [a-z]+(?:,|\.)", re.search(r"colours: (.*?)\. Marbles", q).group(1) + ".")]
        if "one marble of every colour" in q:
            # the worst sequence avoids one colour as long as possible: take everything except the smallest colour
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
        return canon(modes[0] if "Which value occurs most often" in q else top), alt
    if n == "digit_puzzle":
        nd = int(re.search(r"Find the (\d)-digit number", q).group(1))
        clues_txt = re.search(r"all of these are true: (.*)\. There is exactly one", q).group(1).split("; ")
        def rev(x):
            return int(str(x)[::-1].lstrip("0") or "0")
        def holds(x, c, exactly_one_contains=False):
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
            if (m := re.fullmatch(r"one of its digits is (\d)", c)):
                d = int(m.group(1))
                return ds.count(d) == 1 if exactly_one_contains else d in ds
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
        sols_alt = [x for x in rng if all(holds(x, c, True) for c in clues_txt)]
        alt["contains_means_exactly_one"] = canon(sols_alt[0]) if len(sols_alt) == 1 else f"NOT_UNIQUE:{len(sols_alt)}"
        # alternative reading of the reversal: keep the leading zero as a 3-digit string compared numerically is the same; dropping is stated -> no alt
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
        sides = 0
        for (y, x) in cells:
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if (y + dy, x + dx) not in cells:
                    sides += 1
        # alternative parse: "the sides of [squares that do not touch another square]" = 4 x squares with no edge-neighbour
        iso = sum(1 for (y, x) in cells if all((y + dy, x + dx) not in cells for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))))
        alt["sides_of_isolated_squares"] = canon(4 * iso)
        return canon(sides), alt
    if n == "painted_cube":
        a, b, c = map(int, re.search(r"box (\d+) cubes long, (\d+) cubes wide and (\d+) cubes high", q).groups())
        f = int(re.search(r"have exactly (\d+) painted face", q).group(1))
        bottom_unp = "except the bottom face" in q
        # closed form by region (independent of the generator's triple loop): count per (x-class, y-class, z-class)
        def cls(L):  # number of positions that are on 0, 1 boundary planes along an axis with both ends painted
            return {0: L - 2, 1: 2}
        zc = {0: c - 2, 1: 2} if not bottom_unp else {0: c - 1, 1: 1}  # bottom unpainted: z=0 layer has 0 from z (if c>=2), top has 1
        cnt = 0
        for px, nx in cls(a).items():
            for py, ny in cls(b).items():
                for pz, nz in zc.items():
                    if px + py + pz == f:
                        cnt += nx * ny * nz
        return canon(cnt), alt
    if n == "division_counting":
        if (m := re.search(r"makes (\d+) .*? boxes that each hold exactly (\d+) .*? pallets that each hold (\d+) boxes", q)):
            N, k, mm = map(int, m.groups())
            boxes = 0
            left = N
            while left >= k:
                left -= k
                boxes += 1
            pallets = 0
            while boxes >= mm:
                boxes -= mm
                pallets += 1
            return canon(boxes), alt
        N, k = map(int, re.search(r"(\d+) people must travel by bus.*Each bus has (\d+) seats", q).groups())
        buses = 0
        while buses * k < N:
            buses += 1
        return canon(buses * k - N), alt
    if n == "min_cost_packs":
        single = int(re.search(r"one [a-z-]+ costs (\d+) dollars", q).group(1))
        packs = [(int(s), int(p)) for s, p in re.findall(r"a pack of (\d+) [a-z-]+ costs (\d+) dollars", q)]
        need = int(re.search(r"needs at least (\d+)", q).group(1))
        opts = [(1, single)] + packs
        top = need + max(s for s, _ in opts)
        INF = 10 ** 12
        best = [0] + [INF] * top  # best[i] = cheapest cost of EXACTLY i items
        for i in range(1, top + 1):
            best[i] = min(best[i - s] + p for s, p in opts if s <= i)
        return canon(min(best[need:])), alt
    raise KeyError(lid)
