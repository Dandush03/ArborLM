"""Second solvers for nine M1 lineages (NAME = m1c), written from the answer-free
fixtures and SCHEMA.md only. Standard library only. Each solver takes
(question, structured) and returns the answer string.

Each lineage also has a text parser (TEXT_PARSERS) that re-reads the inputs from
the question text; run_solver2.py checks that text and `structured` agree, and the
answers are computed from `structured`.
"""
import re
from fractions import Fraction


# ---------------------------------------------------------------- formatting
def fmt_int(x):
    x = Fraction(x)
    if x.denominator != 1:
        raise ValueError("non-integer answer %s" % x)
    if x < 0:
        raise ValueError("negative answer %s" % x)
    return str(x.numerator)


def fmt_money(x):
    """Whole -> no decimal point; else one or two decimals, no trailing zero.
    Raises if the exact value has more than two decimals (caller decides rounding)."""
    x = Fraction(x)
    neg = x < 0
    x = abs(x)
    cents = x * 100
    if cents.denominator != 1:
        raise ValueError("value %s is not a whole number of cents" % x)
    c = cents.numerator
    whole, frac = divmod(c, 100)
    if frac == 0:
        s = str(whole)
    else:
        s = "%d.%02d" % (whole, frac)
        s = s.rstrip("0")
    return ("-" if neg else "") + s


def round_half_up_cents(x):
    x = Fraction(x)
    c = x * 100
    n = (c.numerator * 2 + c.denominator) // (2 * c.denominator)  # floor(c + 1/2)
    return Fraction(n, 100)


# ---------------------------------------------------------------- prime_factors_r3
def factorize(n):
    f = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1
            n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f


def solve_prime_factors(question, s):
    n = int(s["n"])
    if n < 2:
        raise ValueError("n < 2")
    f = factorize(n)
    ask = s["ask"]
    if ask == "divisors":
        r = 1
        for e in f.values():
            r *= e + 1
        return fmt_int(r)
    if ask == "largest":
        return fmt_int(max(f))
    if ask == "distinct_sum":
        return fmt_int(sum(f))
    if ask == "factor_count":
        return fmt_int(sum(f.values()))
    raise ValueError("unknown ask %r" % ask)


def text_prime_factors(q):
    n = int(re.search(r"Consider the number (\d+)\.", q).group(1))
    if "Add up the different prime numbers" in q:
        ask = "distinct_sum"
    elif "What is the largest prime number" in q:
        ask = "largest"
    elif "How many different positive whole numbers divide it" in q:
        ask = "divisors"
    elif "How many primes are multiplied" in q:
        ask = "factor_count"
    else:
        raise ValueError("unknown wording")
    return {"n": n, "ask": ask}


# ---------------------------------------------------------------- quadratic_area_r3
def isqrt_exact(m):
    if m < 0:
        return None
    r = int(m ** 0.5)
    while r * r > m:
        r -= 1
    while (r + 1) * (r + 1) <= m:
        r += 1
    return r if r * r == m else None


def solve_quadratic_area(question, s):
    shape = s["shape"]
    if shape in ("product", "rect_area"):
        # x (smaller / width), x + d; x(x+d) = A  ->  x = (-d + sqrt(d^2 + 4A)) / 2
        d, A = int(s["d"]), int(s["area"])
        r = isqrt_exact(d * d + 4 * A)
        if r is None or (r - d) % 2:
            raise ValueError("no integer root")
        x = (r - d) // 2
        if x <= 0 or x * (x + d) != A:
            raise ValueError("bad root")
        return fmt_int(x)
    if shape == "squares":
        # x^2 + (x+d)^2 = T  ->  2x^2 + 2dx + d^2 - T = 0  ->  x = (-2d + sqrt(8T - 4d^2)) / 4
        d, T = int(s["d"]), int(s["total"])
        r = isqrt_exact(8 * T - 4 * d * d)
        if r is None or (r - 2 * d) % 4:
            raise ValueError("no integer root")
        x = (r - 2 * d) // 4
        if x <= 0 or x * x + (x + d) ** 2 != T:
            raise ValueError("bad root")
        return fmt_int(x)
    if shape == "rect_perimeter":
        # L + W = P/2, L W = A; longer side L = (S + sqrt(S^2 - 4A)) / 2
        P, A = int(s["perimeter"]), int(s["area"])
        if P % 2:
            raise ValueError("odd perimeter")
        S = P // 2
        r = isqrt_exact(S * S - 4 * A)
        if r is None or (S + r) % 2:
            raise ValueError("no integer root")
        L = (S + r) // 2
        W = S - L
        if W <= 0 or L * W != A:
            raise ValueError("bad root")
        return fmt_int(L)
    raise ValueError("unknown shape %r" % shape)


def text_quadratic_area(q):
    m = re.search(r"Two positive whole numbers differ by (\d+), and their product is (\d+)\. What is the smaller", q)
    if m:
        return {"shape": "product", "d": int(m.group(1)), "area": int(m.group(2)), "perimeter": 0, "total": 0}
    m = re.search(r"Two positive whole numbers differ by (\d+), and the sum of their squares is (\d+)\. What is the smaller", q)
    if m:
        return {"shape": "squares", "d": int(m.group(1)), "area": 0, "perimeter": 0, "total": int(m.group(2))}
    m = re.search(r"A rectangular [a-z ]+ has an area of (\d+) square metres\. Its length is (\d+) metres more than its width\. What is its width, in metres\?", q)
    if m:
        return {"shape": "rect_area", "d": int(m.group(2)), "area": int(m.group(1)), "perimeter": 0, "total": 0}
    m = re.search(r"A rectangular [a-z ]+ has a perimeter of (\d+) metres and an area of (\d+) square metres\. What is the length of its longer side, in metres\?", q)
    if m:
        return {"shape": "rect_perimeter", "d": 0, "area": int(m.group(2)), "perimeter": int(m.group(1)), "total": 0}
    raise ValueError("unknown wording")


# ---------------------------------------------------------------- ratio_share_r3
def solve_ratio_share(question, s):
    parts = [int(p) for p in s["parts"]]
    total = int(s["total"])
    who = int(s["who"])
    share = Fraction(total * parts[who], sum(parts))
    return fmt_int(share)


def text_ratio_share(q):
    m = re.match(r"(.+?) share (\d+) stickers in the ratio ([\d:]+) \(", q)
    names = re.split(r", | and ", m.group(1))
    parts = [int(x) for x in m.group(3).split(":")]
    asked = re.search(r"How many stickers does ([A-Z][a-z]+) get\?", q).group(1)
    idx = [i for i, nm in enumerate(names) if nm == asked]
    if len(idx) != 1 or len(names) != len(parts):
        raise ValueError("name/parts mismatch %r %r" % (names, asked))
    return {"parts": parts, "total": int(m.group(2)), "who": idx[0]}


# ---------------------------------------------------------------- rectangle_r3
def solve_rectangle(question, s):
    P = Fraction(int(s["perimeter"]))
    half = P / 2
    if s["shape"] == "excess":
        e = int(s["excess"])
        w = (half - e) / 2
        L = w + e
    elif s["shape"] == "ratio":
        k = int(s["ratio"])
        w = half / (k + 1)
        L = k * w
    else:
        raise ValueError("unknown shape")
    if w <= 0:
        raise ValueError("non-positive width")
    return fmt_int(L * w)


def text_rectangle(q):
    m = re.search(r"A rectangle has a perimeter of (\d+) centimetres and its length is (\d+) centimetres more than its width\.", q)
    if m:
        return {"shape": "excess", "perimeter": int(m.group(1)), "ratio": 0, "excess": int(m.group(2))}
    m = re.search(r"A rectangle has a perimeter of (\d+) centimetres and its length is (\d+) times its width\.", q)
    if m:
        return {"shape": "ratio", "perimeter": int(m.group(1)), "ratio": int(m.group(2)), "excess": 0}
    raise ValueError("unknown wording")


# ---------------------------------------------------------------- recurrence_iterate_r3
def solve_recurrence(question, s):
    shape = s["shape"]
    first = [int(v) for v in s["first"]]
    pos = int(s["position"])
    if shape == "sum_prev_two":
        seq = list(first[:2])
        while len(seq) < pos:
            seq.append(seq[-1] + seq[-2])
    elif shape == "affine":
        m, a = int(s["mult"]), int(s["add"])
        seq = [first[0]]
        while len(seq) < pos:
            seq.append(m * seq[-1] + a)
    elif shape == "add_index":
        a = int(s["add"])
        seq = [first[0]]
        while len(seq) < pos:
            k = len(seq) + 1  # position of the new number
            seq.append(seq[-1] + a * k)
    else:
        raise ValueError("unknown shape")
    return fmt_int(seq[pos - 1])


def text_recurrence(q):
    pos = int(re.search(r"What is the number in position (\d+) of the list \(position 1 is the first number\)\?", q).group(1))
    m = re.search(r"The first two numbers are (\d+) and (\d+)\. Every number after those is the sum of the two numbers just before it\.", q)
    if m:
        return {"shape": "sum_prev_two", "first": [int(m.group(1)), int(m.group(2))], "mult": 0, "add": 0, "position": pos}
    m = re.search(r"The first number is (\d+)\. Every number after it is (\d+) times the number just before it, (plus|minus) (\d+)\.", q)
    if m:
        a = int(m.group(4)) * (1 if m.group(3) == "plus" else -1)
        return {"shape": "affine", "first": [int(m.group(1))], "mult": int(m.group(2)), "add": a, "position": pos}
    m = re.search(r"The first number is (\d+)\. Every number after it is the number just before it plus (?:(\d+) times )?its own position in the list \(so the second number is the first plus (\d+), the third is the second plus (\d+), and so on\)\.", q)
    if m:
        a = int(m.group(2)) if m.group(2) else 1
        if int(m.group(3)) != 2 * a or int(m.group(4)) != 3 * a:
            raise ValueError("parenthetical example disagrees with rule")
        return {"shape": "add_index", "first": [int(m.group(1))], "mult": 0, "add": a, "position": pos}
    raise ValueError("unknown wording")


# ---------------------------------------------------------------- shopping_r3
def solve_shopping(question, s):
    cost = sum(int(c) * int(p) for c, p in s["items"])
    change = Fraction(int(s["paid"]) - cost, 100)
    return fmt_money(change)


def _cents(txt):
    w, _, f = txt.partition(".")
    f = (f + "00")[:2]
    if len(txt.partition(".")[2]) > 2:
        raise ValueError("more than two decimals")
    return int(w) * 100 + int(f)


def text_shopping(q):
    m = re.match(r"([A-Z][a-z]+) buys (.+?)\. \1 pays with \$([\d.]+)\. How many dollars of change does \1 get back\?", q)
    items = []
    for part in m.group(2).split(", "):
        mm = re.fullmatch(r"(\d+) [a-zA-Z\- ]+ at \$([\d.]+) each", part)
        items.append([int(mm.group(1)), _cents(mm.group(2))])
    return {"items": items, "paid": _cents(m.group(3))}


# ---------------------------------------------------------------- speed_distance_r3
def solve_speed_distance(question, s):
    dist = sum(int(h) * int(v) for h, v in s["legs"])
    if s["average"]:
        t = sum(int(h) for h, _ in s["legs"])
        return fmt_int(Fraction(dist, t))
    return fmt_int(dist)


def text_speed_distance(q):
    legs = [[int(h), int(v)] for h, v in re.findall(r"drives for (\d+) hours? at (\d+) kilometres per hour", q)]
    if "How many kilometres does it travel in total?" in q:
        avg = False
    elif "What is its average speed over the whole trip (the total distance divided by the total time), in kilometres per hour?" in q:
        avg = True
    else:
        raise ValueError("unknown wording")
    return {"legs": legs, "average": avg}


# ---------------------------------------------------------------- tiered_pricing
def tier_cost(tiers, last_rate, u):
    c = 0
    left = u
    for size, rate in tiers:
        take = min(left, size)
        c += take * rate
        left -= take
        if left == 0:
            return c
    return c + left * last_rate


def solve_tiered_pricing(question, s):
    tiers = [(int(a), int(b)) for a, b in s["tiers"]]
    last = int(s["last_rate"])
    if s["mode"] == "bill":
        return fmt_money(Fraction(tier_cost(tiers, last, int(s["used"])), 100))
    if s["mode"] == "units":
        target = int(s["bill_cents"])
        rates = [r for _, r in tiers] + [last]
        if min(rates) <= 0:
            raise ValueError("non-positive rate: cost not strictly increasing")
        # cost is strictly increasing in u, so at most one u matches
        u = 0
        while tier_cost(tiers, last, u) < target:
            u += 1
        if tier_cost(tiers, last, u) != target:
            raise ValueError("no whole number of units gives this bill")
        return fmt_int(u)
    raise ValueError("unknown mode")


def text_tiered_pricing(q):
    m = re.search(r"A utility charges for use in steps: (.+?), and every unit after that costs (\d+) cents each\.", q)
    tiers = [[int(a), int(b)] for a, b in re.findall(r"(?:the first|the next) (\d+) units cost (\d+) cents each", m.group(1))]
    last = int(m.group(2))
    m2 = re.search(r"What is the bill for (\d+) units, in dollars\?", q)
    if m2:
        return {"mode": "bill", "tiers": tiers, "last_rate": last, "used": int(m2.group(1)), "bill_cents": None}
    m3 = re.search(r"A customer's bill is ([\d.]+) dollars\. How many units did the customer use\?", q)
    if m3:
        return {"mode": "units", "tiers": tiers, "last_rate": last, "used": None, "bill_cents": _cents(m3.group(1))}
    raise ValueError("unknown wording")


# ---------------------------------------------------------------- tip_split_r3
def tip_split_exact(s):
    return Fraction(int(s["bill"]) * (100 + int(s["tip"])), 100 * int(s["people"]))


def solve_tip_split(question, s):
    x = tip_split_exact(s)
    if (x * 100).denominator != 1:
        # Not a whole number of cents: the text asks for "no more than two decimal
        # places"; round half up to the cent (see AMBIGUITIES.md if this ever fires).
        x = round_half_up_cents(x)
    return fmt_money(x)


def text_tip_split(q):
    m = re.fullmatch(r"A dinner bill is (\d+) dollars before tip\. The group adds a (\d+) percent tip, calculated on the bill before tip, and splits the total \(bill plus tip\) equally between (\d+) people\. How many dollars does each person pay\? Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros\.", q)
    return {"bill": int(m.group(1)), "tip": int(m.group(2)), "people": int(m.group(3))}


SOLVERS = {
    "M1.prime_factors_r3": solve_prime_factors,
    "M1.quadratic_area_r3": solve_quadratic_area,
    "M1.ratio_share_r3": solve_ratio_share,
    "M1.rectangle_r3": solve_rectangle,
    "M1.recurrence_iterate_r3": solve_recurrence,
    "M1.shopping_r3": solve_shopping,
    "M1.speed_distance_r3": solve_speed_distance,
    "M1.tiered_pricing": solve_tiered_pricing,
    "M1.tip_split_r3": solve_tip_split,
}

TEXT_PARSERS = {
    "M1.prime_factors_r3": text_prime_factors,
    "M1.quadratic_area_r3": text_quadratic_area,
    "M1.ratio_share_r3": text_ratio_share,
    "M1.rectangle_r3": text_rectangle,
    "M1.recurrence_iterate_r3": text_recurrence,
    "M1.shopping_r3": text_shopping,
    "M1.speed_distance_r3": text_speed_distance,
    "M1.tiered_pricing": text_tiered_pricing,
    "M1.tip_split_r3": text_tip_split,
}
