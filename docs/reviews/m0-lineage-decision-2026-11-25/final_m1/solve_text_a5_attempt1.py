# ruff: noqa
"""Final M1 audit (fix 4): second solver from a separate context. Written by the auditor from item TEXTS only (samples_L036.txt, templates.txt, asks.txt)
and the conventions printed in the items. It does not import or read the generators' answer code, the implementer's second derivation (m1_fix3_verify /
m1_fix4_verify) or the earlier auditors' text solvers (solve_text_a3.py / solve_text_a4.py). Standard library only; exact arithmetic (Fraction).

solve(lineage_id, question) -> (value: Fraction, issues: list[str])
  issues lists every reason the item has NO UNIQUE ANSWER under its stated convention (non-integer where a whole number is asked, more than two
  decimals where 'no more than two decimal places' is the only rounding convention, an inconsistent data set, a repeated name that the ask refers to, ...).
Raises on text it cannot read (counted as a solver error, never as a key mismatch)."""
import math
import re
from fractions import Fraction as F

NUM = r"-?\d+(?:\.\d+)?"
WORDS = {"half": 2, "third": 3, "quarter": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}


def nums(s):
    return [F(x) for x in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", s.replace("$", " "))]


def ints(s):
    return [int(x) for x in re.findall(r"(?<![\w.])-?\d+", s)]


def strip_ctx(q):
    for c in (r"^\S+ from \S+ found this problem in a puzzle book\. ", r"^This problem comes from a quiz held in [^,]+, set by \S+\. ",
              r"^\S+ of \S+ wrote this problem for a maths club\. ", r"^At a maths club in [^,]+, \S+ is asked this\. "):
        q = re.sub(c, "", q)
    return q


def check_format(q, v, issues):
    if "Answer with a whole number" in q:
        if v.denominator != 1:
            issues.append(f"whole number asked, exact value {v}")
    elif "no more than two decimal places" in q:
        if (v * 100).denominator != 1:
            issues.append(f"more than two decimals, exact value {v} (no rounding rule stated)")
    else:
        issues.append("no answer format stated")


def need(m, what):
    if m is None:
        raise ValueError(f"cannot read: {what}")
    return m


# ---------------------------------------------------------------- per lineage

def s_ages(q, iss):
    m = need(re.search(r"(\w+) is (\d+) times as old as (\w+) now\. In (\d+) years? from now, their two ages added together will be (\d+)\..*How old is (\w+) now", q), "ages")
    a, k, b, t, tot, who = m.group(1), int(m.group(2)), m.group(3), int(m.group(4)), int(m.group(5)), m.group(6)
    young = F(tot - 2 * t, k + 1)
    if a == b:
        iss.append("both people have the same name")
    if young <= 0:
        iss.append("non-positive age")
    return young * k if who == a else young


def s_arith(q, iss):
    m = need(re.search(r"saves (\d+) dollars on day 1 and then saves (\d+) dollars more each day.*after (\d+) days \(counting day 1 to day (\d+)", q), "arith")
    a, d, n, n2 = map(int, m.groups())
    assert n == n2
    tot, cur = 0, a
    for _ in range(n):
        tot += cur
        cur += d
    return F(tot)


def s_avgmiss(q, iss):
    m = need(re.search(r"has scored ([\d, ]+) on (\d+) tests, each marked out of (\d+) with whole-number marks\. What score is needed on the next test to make the mean of all (\d+) tests exactly (" + NUM + r")\?", q), "avg")
    sc = [int(x) for x in m.group(1).split(",")]
    k, top, n, mean = int(m.group(2)), int(m.group(3)), int(m.group(4)), F(m.group(5))
    if len(sc) != k or n != k + 1:
        iss.append("count of tests does not match the list")
    v = mean * n - sum(sc)
    if not (0 <= v <= top):
        iss.append(f"needed score {v} outside 0..{top}")
    return v


def s_change(q, iss):
    m = need(re.search(r"coins worth ([\d, and]+) cents,.*can exactly (\d+) cents be paid", q), "change")
    coins = [int(x) for x in re.findall(r"\d+", m.group(1))]
    T = int(m.group(2))
    ways = [1] + [0] * T  # unordered: coin-by-coin table
    for c in coins:
        for s in range(c, T + 1):
            ways[s] += ways[s - c]
    # cross-check by brute force for three coins
    if len(coins) == 3:
        c1, c2, c3 = coins
        bf = sum(1 for i in range(T // c1 + 1) for j in range((T - i * c1) // c2 + 1) if (T - i * c1 - j * c2) % c3 == 0)
        assert bf == ways[T], "change cross-check"
    if len(set(coins)) != len(coins):
        iss.append("repeated coin value")
    return F(ways[T])


def s_clock(q, iss):
    legs = re.findall(r"leg (\d+) leaves at (\d\d):(\d\d) and arrives at (\d\d):(\d\d)", q)
    need(legs or None, "clock")
    tot, prev = 0, -1
    for i, (n, h1, m1, h2, m2) in enumerate(legs):
        assert int(n) == i + 1
        d, a = int(h1) * 60 + int(m1), int(h2) * 60 + int(m2)
        if not (prev <= d < a) or int(h1) > 23 or int(h2) > 23 or int(m1) > 59 or int(m2) > 59:
            iss.append("times not increasing on one day")
        # count minute by minute (a different route from a subtraction)
        tot += sum(1 for _ in range(d, a))
        prev = a
    return F(tot)


def s_consec(q, iss):
    m = need(re.search(r"The sum of (\d+) consecutive (integers|numbers that each differ from the next by (\d+)) \(.*?\) is (-?\d+)\. What is the (smallest|largest) of them", q), "consec")
    n = int(m.group(1))
    d = int(m.group(3)) if m.group(3) else 1
    S, ask = int(m.group(4)), m.group(5)
    # search around S / n for the smallest term a with sum = S (exact; a different route from the closed form)
    a0 = S // n - n * d
    sol = [a for a in range(a0 - 2, a0 + n * d + 3) if sum(a + i * d for i in range(n)) == S]
    if len(sol) != 1:
        iss.append(f"{len(sol)} solutions")
        return F(S, n)
    a = sol[0]
    return F(a if ask == "smallest" else a + (n - 1) * d)


def s_crt(q, iss):
    conds = [(int(a), int(b)) for a, b in re.findall(r"by (\d+) leaves remainder (\d+)", q)]
    need(conds or None, "crt")
    for mm, r in conds:
        if r >= mm:
            iss.append("remainder not below divisor")
    big = max(conds)
    L = 1
    for mm, _ in conds:
        L = L * mm // math.gcd(L, mm)
    x = big[1] if big[1] > 0 else big[0]
    while x <= L + big[0]:
        if all(x % mm == r for mm, r in conds):
            return F(x)
        x += big[0]
    iss.append("no solution")
    return F(-1)


def s_division(q, iss):
    m = re.search(r"(\d+) people must travel by bus.*Each bus has (\d+) seats", q)
    if m:
        N, k = int(m.group(1)), int(m.group(2))
        buses = 0
        while buses * k < N:
            buses += 1
        return F(buses * k - N)
    m = need(re.search(r"A factory makes (\d+) (\w+)\. They are packed into boxes that each hold exactly (\d+) \w+;.*pallets that each hold (\d+) boxes", q), "division")
    N, k, p = int(m.group(1)), int(m.group(3)), int(m.group(4))
    boxes = N // k
    return F(boxes - (boxes // p) * p)


def s_findiff(q, iss):
    m = need(re.search(r"The first (\d+) numbers of a pattern are ([\d, and]+)\. .*polynomial of degree (\d+) in its position.*What is the number in position (\d+)\?", q), "fd")
    n, terms, deg, ask = int(m.group(1)), [int(x) for x in re.findall(r"\d+", m.group(2))], int(m.group(3)), int(m.group(4))
    assert len(terms) == n
    xs = list(range(1, deg + 2))
    def lag(x, pts):
        tot = F(0)
        for i, xi in enumerate(pts):
            w = F(terms[xi - 1])
            for j, xj in enumerate(pts):
                if j != i:
                    w *= F(x - xj, xi - xj)
            tot += w
        return tot
    for x in range(deg + 2, n + 1):  # the printed terms must all lie on the degree-d polynomial
        if lag(x, xs) != terms[x - 1]:
            iss.append("printed terms not on one polynomial of the stated degree")
            break
    # degree exactly deg (leading difference non-zero)
    diffs = terms[:]
    for _ in range(deg):
        diffs = [b - a for a, b in zip(diffs, diffs[1:])]
    if all(x == 0 for x in diffs):
        iss.append("degree lower than stated")
    return lag(ask, xs)


def s_fracrem(q, iss):
    m = need(re.search(r"has (\d+) dollars\. \w+ spends one (\w+) of it on books, then one (\w+) of what is left on lunch", q), "fracrem")
    s, a, b = int(m.group(1)), WORDS[m.group(2)], WORDS[m.group(3)]
    first = F(s, a)
    left = s - first
    second = left / b
    if first.denominator != 1 or second.denominator != 1:
        iss.append("a spend is not whole dollars")
    return left - second


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def s_gcdlcm(q, iss):
    m = re.search(r"has (\d+) ribbons of lengths ([\d, and]+) centimetres", q)
    if m:
        v = [int(x) for x in re.findall(r"\d+", m.group(2))]
        assert len(v) == int(m.group(1))
        g = 0
        for x in v:
            g = _gcd(g, x)
        return F(g)
    m = need(re.search(r"(\d+) lights flash at the same moment\. After that, (.*?)\. After how many seconds", q), "lcm")
    v = [int(x) for x in re.findall(r"every (\d+) seconds", m.group(2))]
    assert len(v) == int(m.group(1))
    L = 1
    for x in v:
        L = L * x // _gcd(L, x)
    return F(L)


def s_grid(q, iss):
    rows = re.findall(r"Row (\d+) \(counting from the top\): (.*?)\.(?= Row| Squares)", q)
    need(rows or None, "grid")
    cells = set()
    for r, desc in rows:
        if desc.strip() == "no squares":
            continue
        for part in desc.split(", "):
            m1 = re.fullmatch(r"columns (\d+) to (\d+)", part.strip())
            m2 = re.fullmatch(r"column (\d+)", part.strip())
            if m1:
                for c in range(int(m1.group(1)), int(m1.group(2)) + 1):
                    cells.add((int(r), c))
            elif m2:
                cells.add((int(r), int(m2.group(1))))
            else:
                raise ValueError("grid part " + part)
    # count unit sides: every side as a key; keep those owned by exactly one square
    owner = {}
    for (y, x) in cells:
        for side in (("h", y, x), ("h", y + 1, x), ("v", y, x), ("v", y, x + 1)):
            owner[side] = owner.get(side, 0) + 1
    return F(sum(1 for c in owner.values() if c == 1))


def s_incl(q, iss):
    T = int(need(re.match(r"(\d+) people were asked what they do\.", q), "incl").group(1))
    ask = need(re.search(r"How many of the (\d+) people do (none of these things|at least one of these things|exactly one of these things|exactly two of these things)\?", q), "incl ask")
    assert int(ask.group(1)) == T
    a = ask.group(2).split(" of")[0]
    m2 = re.search(r"\. (\d+) of them [a-z ]+, (\d+) of them [a-z ]+, and (\d+) of them do both\.", q)
    if m2:
        A, B, AB = map(int, m2.groups())
        regions = {"onlyA": A - AB, "onlyB": B - AB, "AB": AB}
        union = A + B - AB
        if min(regions.values()) < 0 or union > T:
            iss.append("inconsistent counts")
        v = {"none": T - union, "at least one": union, "exactly one": A + B - 2 * AB, "exactly two": AB}[a]
        return F(v)
    m3 = need(re.search(r"\. (\d+) [a-z ]+, (\d+) [a-z ]+ and (\d+) [a-z ]+; (\d+) do both the first and the second, (\d+) do both the first and the third, (\d+) do both the second and the third, and (\d+) do all three", q), "incl3")
    A, B, C, ab, ac, bc, t = map(int, m3.groups())
    reg = {"abc": t, "ab": ab - t, "ac": ac - t, "bc": bc - t}
    reg["a"] = A - reg["ab"] - reg["ac"] - t
    reg["b"] = B - reg["ab"] - reg["bc"] - t
    reg["c"] = C - reg["ac"] - reg["bc"] - t
    union = sum(reg.values())
    if min(reg.values()) < 0 or union > T:
        iss.append("inconsistent counts")
    v = {"none": T - union, "at least one": union, "exactly one": reg["a"] + reg["b"] + reg["c"], "exactly two": reg["ab"] + reg["ac"] + reg["bc"]}[a]
    return F(v)


def _modpow(b, e, m):
    r, b = 1 % m, b % m
    while e:
        if e & 1:
            r = r * b % m
        b = b * b % m
        e >>= 1
    return r


def s_lastdig(q, iss):
    p = int(need(re.search(r"divided by (\d+) \(a whole number from 0 to (\d+)\)", q), "mod").group(1))
    m = re.search(r"Let X be the product of (\d+) factors, each equal to (\d+)\. What", q)
    if m:
        return F(_modpow(int(m.group(2)), int(m.group(1)), p))
    m = re.search(r"Let X be the product of all the following factors: (.*?)\. What", q)
    if m:
        terms = re.findall(r"(\d+) factors equal to (\d+)", m.group(1))
        r = 1
        for e, b in terms:
            r = r * _modpow(int(b), int(e), p) % p
        return F(r)
    m = need(re.search(r"Let X be the sum of (.*?)\. What", q), "lastdig")
    terms = re.findall(r"the product of (\d+) factors, each equal to (\d+)", m.group(1))
    assert len(terms) >= 2
    return F(sum(_modpow(int(b), int(e), p) for e, b in terms) % p)


def _side(s):
    m = re.fullmatch(r"Multiplying it by (\d+) and then (adding|subtracting) (\d+)", s.strip())
    k, c = int(m.group(1)), int(m.group(3))
    return k, (c if m.group(2) == "adding" else -c)


def s_linear(q, iss):
    m = re.search(r"I think of a number\. (Multiplying it by \d+ and then (?:adding|subtracting) \d+) gives the same result as (multiplying it by \d+ and then (?:adding|subtracting) \d+)\.", q)
    if m:
        k1, c1 = _side(m.group(1))
        k2, c2 = _side("M" + m.group(2)[1:])
        if k1 == k2:
            iss.append("no unique solution (same multiplier)")
            return F(0)
        return F(c2 - c1, k1 - k2)
    m = need(re.search(r"I think of a number\. (Multiplying it by \d+ and then (?:adding|subtracting) \d+) gives (-?\d+)\.", q), "linear")
    k, c = _side(m.group(1))
    if k == 0:
        iss.append("multiplier 0")
    return F(int(m.group(2)) - c, k)


def s_median(q, iss):
    m = need(re.search(r"The values are ([\d, and]+)\. What is the median", q), "median")
    v = sorted(int(x) for x in re.findall(r"\d+", m.group(1)))
    n = len(v)
    return F(v[n // 2]) if n % 2 else F(v[n // 2 - 1] + v[n // 2], 2)


def s_mixture(q, iss):
    m = need(re.search(r"mixes (\d+) kilograms of nuts costing (\d+) dollars per kilogram with (\d+) kilograms of raisins costing (\d+) dollars per kilogram(, then adds a flat packing cost of (\d+) dollars? per kilogram of the finished mixture)?\.", q), "mixture")
    x, a, y, b = (int(m.group(i)) for i in (1, 2, 3, 4))
    p = int(m.group(6)) if m.group(6) else 0
    return F(x * a + y * b, x + y) + p


def s_painted(q, iss):
    m = need(re.search(r"box (\d+) cubes long, (\d+) cubes wide and (\d+) cubes high\. The whole box is placed on a table and every outer face (\(including the bottom face on the table\) is painted red|is painted red except the bottom face)", q), "painted")
    L, W, H = int(m.group(1)), int(m.group(2)), int(m.group(3))
    bottom = m.group(4).startswith("(including")
    k = int(need(re.search(r"have exactly (\d+) painted faces?\?", q), "painted ask").group(1))

    def classes(n, lo_painted, hi_painted):
        # positions along one axis -> (number of painted faces touched, how many positions)
        if n == 1:
            return [(int(lo_painted) + int(hi_painted), 1)]
        out = [(int(lo_painted), 1), (int(hi_painted), 1)]
        if n > 2:
            out.append((0, n - 2))
        return out
    tot = 0
    for fx, cx in classes(L, True, True):
        for fy, cy in classes(W, True, True):
            for fz, cz in classes(H, bottom, True):
                if fx + fy + fz == k:
                    tot += cx * cy * cz
    if min(L, W, H) < 2:
        iss.append("a dimension below 2")
    return F(tot)


def s_percent(q, iss):
    m = need(re.search(r"A jacket costs (\d+) dollars\. Its price (.*?), each change applied to the price just before it", q), "percent")
    v = F(int(m.group(1)))
    for d, p in re.findall(r"(rises|falls) by (\d+) percent", m.group(2)):
        v = v * (100 + (int(p) if d == "rises" else -int(p))) / 100
    if v < 0:
        iss.append("negative price")
    return v


def s_pipes(q, iss):
    m = need(re.search(r"One pipe adds (\d+) litres of water every minute and a second pipe adds (\d+) litres every minute(, while a drain removes (\d+) litres every minute)?, .*to hold (\d+) litres", q), "pipes")
    a, b = int(m.group(1)), int(m.group(2))
    d = int(m.group(4)) if m.group(4) else 0
    V = int(m.group(5))
    net = a + b - d
    if net <= 0:
        iss.append("never fills")
        return F(0)
    return F(V, net)


def _factor(n):
    f, p = {}, 2
    while p * p <= n:
        while n % p == 0:
            f[p] = f.get(p, 0) + 1
            n //= p
        p += 1 if p == 2 else 2
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f


def s_prime(q, iss):
    n = int(need(re.search(r"Consider the number (\d+)\.", q), "prime").group(1))
    f = _factor(n)
    if "How many different positive whole numbers divide it exactly" in q:
        # count divisors by direct search up to sqrt (a different route from the product formula)
        c, d = 0, 1
        while d * d <= n:
            if n % d == 0:
                c += 1 if d * d == n else 2
            d += 1
        return F(c)
    if "Add up the different prime numbers" in q:
        return F(sum(f))
    if "largest prime number that divides it" in q:
        return F(max(f))
    if "How many primes are multiplied" in q:
        return F(sum(f.values()))
    raise ValueError("prime ask")


def s_quad(q, iss):
    m = re.search(r"has an area of (\d+) square metres\. Its length is (\d+) metres more than its width\. What is its width", q)
    if m:
        A, d = int(m.group(1)), int(m.group(2))
        sol = [w for w in range(1, math.isqrt(A) + 2) if w * (w + d) == A]
    else:
        m = re.search(r"has a perimeter of (\d+) metres and an area of (\d+) square metres\. What is the length of its longer side", q)
        if m:
            P, A = int(m.group(1)), int(m.group(2))
            sol = [max(w, P // 2 - w) for w in range(1, P // 4 + 1) if P % 2 == 0 and w * (P // 2 - w) == A]
        else:
            m = re.search(r"Two positive whole numbers differ by (\d+), and their product is (\d+)\. What is the smaller", q)
            if m:
                d, Pr = int(m.group(1)), int(m.group(2))
                sol = [x for x in range(1, math.isqrt(Pr) + 2) if x * (x + d) == Pr]
            else:
                m = need(re.search(r"Two positive whole numbers differ by (\d+), and the sum of their squares is (\d+)\. What is the smaller", q), "quad")
                d, Sq = int(m.group(1)), int(m.group(2))
                sol = [x for x in range(1, math.isqrt(Sq) + 2) if x * x + (x + d) ** 2 == Sq]
    if len(sol) != 1:
        iss.append(f"{len(sol)} whole solutions")
        return F(sol[0]) if sol else F(-1)
    return F(sol[0])


def s_ratio(q, iss):
    m = need(re.search(r"^(.*?) share (\d+) stickers in the ratio ([\d:]+) \(.*How many stickers does (\w+) get\?", q), "ratio")
    names = re.split(r", | and ", m.group(1))
    tot, parts, who = int(m.group(2)), [int(x) for x in m.group(3).split(":")], m.group(4)
    assert len(names) == len(parts), (names, parts)
    if names.count(who) != 1:
        iss.append(f"the asked name appears {names.count(who)} times")
    i = names.index(who)
    unit = F(tot, sum(parts))
    if unit.denominator != 1:
        iss.append("part not whole")
    return unit * parts[i]


def s_rect(q, iss):
    m = re.search(r"perimeter of (\d+) centimetres and its length is (\d+) centimetres more than its width", q)
    if m:
        P, d = int(m.group(1)), int(m.group(2))
        w = (F(P, 2) - d) / 2
        l = w + d
    else:
        m = need(re.search(r"perimeter of (\d+) centimetres and its length is (\d+) times its width", q), "rect")
        P, k = int(m.group(1)), int(m.group(2))
        w = F(P, 2) / (k + 1)
        l = k * w
    if w <= 0:
        iss.append("non-positive width")
    return l * w


def s_recur(q, iss):
    pos = int(need(re.search(r"What is the number in position (\d+) of the list", q), "recur pos").group(1))
    m = re.search(r"The first two numbers are (\d+) and (\d+)\. Every number after those is the sum of the two numbers just before it", q)
    if m:
        t = [int(m.group(1)), int(m.group(2))]
        while len(t) < pos:
            t.append(t[-1] + t[-2])
        return F(t[pos - 1])
    first = int(need(re.search(r"The first number is (\d+)\.", q), "recur first").group(1))
    t = [first]
    m = re.search(r"Every number after it is (\d+) times the number just before it, (plus|minus) (\d+)\.", q)
    if m:
        k, c = int(m.group(1)), int(m.group(3)) * (1 if m.group(2) == "plus" else -1)
        while len(t) < pos:
            t.append(k * t[-1] + c)
        return F(t[pos - 1])
    m = re.search(r"Every number after it is the number just before it plus (?:(\d+) times )?its own position in the list \(so the second number is the first plus (\d+), the third is the second plus (\d+)", q)
    if m:
        c = int(m.group(1)) if m.group(1) else 1
        assert int(m.group(2)) == 2 * c and int(m.group(3)) == 3 * c
        while len(t) < pos:
            t.append(t[-1] + c * (len(t) + 1))
        return F(t[pos - 1])
    raise ValueError("recur rule")


def s_shop(q, iss):
    m = need(re.search(r"^(\w+) buys (.*?)\. \1 pays with \$(\d+\.\d\d)\. How many dollars of change does \1 get back", q), "shop")
    its = re.findall(r"(\d+) [a-z]+ at \$(\d+\.\d\d) each", m.group(2))
    assert its and len(its) == m.group(2).count(" at $")
    cost = sum(int(n) * F(p) for n, p in its)
    v = F(m.group(3)) - cost
    if v < 0:
        iss.append("not enough paid")
    return v


def s_speed(q, iss):
    legs = [(int(h), int(v)) for h, v in re.findall(r"drives for (\d+) hours? at (\d+) kilometres per hour", q)]
    need(legs or None, "speed")
    dist = sum(h * v for h, v in legs)
    if "average speed over the whole trip" in q:
        return F(dist, sum(h for h, _ in legs))
    assert "How many kilometres does it travel in total" in q
    return F(dist)


def s_tiered(q, iss):
    m = need(re.search(r"A utility charges for use in steps: (.*?)\. Each unit costs", q), "tiered")
    body = m.group(1)
    first = re.match(r"the first (\d+) units cost (\d+) cents each", body)
    tiers = [(int(first.group(1)), int(first.group(2)))] + [(int(a), int(b)) for a, b in re.findall(r"the next (\d+) units cost (\d+) cents each", body)]
    last = int(re.search(r"every unit after that costs (\d+) cents each", body).group(1))

    def bill(u):  # cents, unit by unit
        c, left = 0, u
        for size, rate in tiers:
            take = min(size, left)
            c += take * rate
            left -= take
        return c + left * last
    m = re.search(r"What is the bill for (\d+) units, in dollars\?", q)
    if m:
        return F(bill(int(m.group(1))), 100)
    m = need(re.search(r"A customer's bill is (\d+(?:\.\d+)?) dollars\. How many units did the customer use\?", q), "tiered ask")
    target = F(m.group(1)) * 100
    sol = [u for u in range(0, int(target) + 2) if bill(u) == target]
    if len(sol) != 1:
        iss.append(f"{len(sol)} unit counts give the bill")
        return F(sol[0]) if sol else F(-1)
    return F(sol[0])


def s_tip(q, iss):
    m = need(re.search(r"A dinner bill is (\d+) dollars before tip\. The group adds a (\d+) percent tip, .*equally between (\d+) people", q), "tip")
    b, t, n = map(int, m.groups())
    return F(b) * (100 + t) / 100 / n


SOLVERS = {"ages": s_ages, "arithmetic_series": s_arith, "average_missing": s_avgmiss, "change_ways": s_change, "clock_duration": s_clock, "consecutive": s_consec,
           "crt_congruence": s_crt, "division_counting": s_division, "finite_differences": s_findiff, "fraction_remainder": s_fracrem, "gcd_lcm": s_gcdlcm,
           "grid_perimeter": s_grid, "inclusion_exclusion": s_incl, "last_digit_power": s_lastdig, "linear_equation": s_linear, "median_list": s_median,
           "mixture": s_mixture, "painted_cube": s_painted, "percent_change": s_percent, "pipes_work": s_pipes, "prime_factors": s_prime, "quadratic_area": s_quad,
           "ratio_share": s_ratio, "rectangle": s_rect, "recurrence_iterate": s_recur, "shopping": s_shop, "speed_distance": s_speed, "tiered_pricing": s_tiered,
           "tip_split": s_tip}


def solve(stem, question):
    q = strip_ctx(question)
    iss = []
    v = SOLVERS[stem](q, iss)
    check_format(question, v, iss)
    return v, iss
