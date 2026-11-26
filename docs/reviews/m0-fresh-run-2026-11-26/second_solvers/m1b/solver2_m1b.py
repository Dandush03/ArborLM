"""Second solvers (M0, ADR-0033 addendum 1, section 8 item 1) for ten M1 lineages, NAME = m1b.

Written from the answer-free fixtures (question text, `structured`, SCHEMA.md) only.
Standard library only; no randomness, no I/O, no eval/exec of item content.
Each solver computes from `structured`; the question text is used only where stated
(none of these ten lineages needs it; see NOTES.md, and check_text.py cross-checks
`structured` against values parsed from the text).
"""
from fractions import Fraction
from math import gcd

# Items whose exact value is not representable with <= 2 decimals are rounded half-up
# to 2 decimals; their ids are not known here, so the runner records them via this list.
INEXACT = []


def fmt_int(v):
    v = Fraction(v)
    if v.denominator != 1:
        raise ValueError(f"non-integer value {v}")
    return str(v.numerator)


def fmt_dec2(v):
    """Whole -> digits; else decimal with 1-2 decimals, no trailing zero; '-' only if negative."""
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    h = v * 100
    if h.denominator != 1:
        INEXACT.append(v)
        # round half away from zero to 2 decimals
        sign = -1 if h < 0 else 1
        a = abs(h)
        q, r = divmod(a.numerator, a.denominator)
        if 2 * r >= a.denominator:
            q += 1
        h = Fraction(sign * q)
        if h.denominator == 1 and h.numerator % 100 == 0:
            return str(h.numerator // 100)
    n = h.numerator
    neg = n < 0
    n = abs(n)
    s = f"{n // 100}.{n % 100:02d}".rstrip("0").rstrip(".")
    return ("-" if neg else "") + s


def lcm(a, b):
    return a * b // gcd(a, b)


# 1. gcd_lcm_r4: ask=gcd -> greatest common piece length; ask=lcm -> first common flash time.
def solve_gcd_lcm(question, s):
    vals = [int(v) for v in s["values"]]
    if s["ask"] == "gcd":
        g = 0
        for v in vals:
            g = gcd(g, v)
        return fmt_int(g)
    if s["ask"] == "lcm":
        m = 1
        for v in vals:
            m = lcm(m, v)
        return fmt_int(m)
    raise ValueError(s["ask"])


# 2. grid_perimeter_r3: perimeter = 4*cells - 2*(edge-adjacent pairs).
def solve_grid_perimeter(question, s):
    cells = set()
    for r, runs in enumerate(s["rows"]):
        for a, b in runs:
            for c in range(int(a), int(b) + 1):
                cells.add((r, c))
    shared = sum(((r + 1, c) in cells) + ((r, c + 1) in cells) for (r, c) in cells)
    return fmt_int(4 * len(cells) - 2 * shared)


# 3. inclusion_exclusion_r3.
def solve_inclusion_exclusion(question, s):
    total = int(s["total"])
    sizes = [int(v) for v in s["sizes"]]
    pairs = [int(v) for v in s["pairs"]]
    ask = s["ask"]
    if len(sizes) == 2:
        if s["triple"] is not None or len(pairs) != 1:
            raise ValueError("two-set item with triple")
        union = sizes[0] + sizes[1] - pairs[0]
        if ask == "any":
            return fmt_int(union)
        if ask == "none":
            return fmt_int(total - union)
        if ask == "exactly_one":
            return fmt_int(union - pairs[0])
        raise ValueError(ask)
    if len(sizes) == 3:
        t = int(s["triple"])
        S, P = sum(sizes), sum(pairs)
        union = S - P + t
        if ask == "any":
            return fmt_int(union)
        if ask == "none":
            return fmt_int(total - union)
        if ask == "exactly_one":
            return fmt_int(S - 2 * P + 3 * t)
        if ask == "exactly_two":
            return fmt_int(P - 3 * t)
        raise ValueError(ask)
    raise ValueError("set count")


# 4. last_digit_power_r3: X = sum or product of base**exponent terms; answer X mod modulus.
# For a single term, sum and product coincide (structured gives op="sum" there while the
# text says "the product of N factors"; same value).
def solve_last_digit_power(question, s):
    m = int(s["modulus"])
    terms = [(int(b), int(e)) for b, e in s["terms"]]
    if s["op"] == "sum":
        x = sum(pow(b, e, m) for b, e in terms) % m
    elif s["op"] == "product":
        x = 1 % m
        for b, e in terms:
            x = x * pow(b, e, m) % m
    else:
        raise ValueError(s["op"])
    return fmt_int(x)


# 5. linear_equation_r3: k*x + m = j*x + n  ->  x = (n - m) / (k - j)  (j = 0: one-sided).
def solve_linear_equation(question, s):
    k, m, j, n = (int(s[f]) for f in ("k", "m", "j", "n"))
    if k == j:
        raise ValueError("k == j")
    return fmt_int(Fraction(n - m, k - j))


# 6. median_list_r3.
def solve_median_list(question, s):
    if s.get("shape", "list") != "list":
        raise ValueError(s["shape"])
    v = sorted(Fraction(x) for x in s["values"])
    L = len(v)
    med = v[L // 2] if L % 2 else (v[L // 2 - 1] + v[L // 2]) / 2
    return fmt_dec2(med)


# 7. mixture_r4: (a*x + b*y)/(x + y) + packing.
def solve_mixture(question, s):
    a, b, x, y, p = (Fraction(s[f]) for f in ("a", "b", "x", "y", "packing"))
    return fmt_dec2((a * x + b * y) / (x + y) + p)


# 8. painted_cube_r3: count unit cubes with exactly `faces` painted faces.
def _axis(n, low_painted, high_painted):
    """Distribution {painted faces on this axis: number of positions}."""
    d = {}
    for i in range(n):
        k = (low_painted and i == 0) + (high_painted and i == n - 1)
        d[k] = d.get(k, 0) + 1
    return d


def solve_painted_cube(question, s):
    L, W, H = (int(v) for v in s["dims"])
    bottom = not s["bottom_unpainted"]
    want = int(s["faces"])
    dl, dw, dh = _axis(L, True, True), _axis(W, True, True), _axis(H, bottom, True)
    cnt = 0
    for a, ca in dl.items():
        for b, cb in dw.items():
            for c, cc in dh.items():
                if a + b + c == want:
                    cnt += ca * cb * cc
    return fmt_int(cnt)


# 9. percent_change_r3: successive multiplicative changes.
def solve_percent_change(question, s):
    p = Fraction(s["price"])
    for d, pct in s["steps"]:
        if d == "up":
            p = p * (100 + Fraction(pct)) / 100
        elif d == "down":
            p = p * (100 - Fraction(pct)) / 100
        else:
            raise ValueError(d)
    return fmt_dec2(p)


# 10. pipes_work_r3: minutes = volume / (a + b - drain); must be a positive whole number.
def solve_pipes_work(question, s):
    rate = int(s["a"]) + int(s["b"]) - int(s["drain"])
    if rate <= 0:
        raise ValueError("tank never fills")
    return fmt_int(Fraction(int(s["volume"]), rate))


SOLVERS = {
    "M1.gcd_lcm_r4": solve_gcd_lcm,
    "M1.grid_perimeter_r3": solve_grid_perimeter,
    "M1.inclusion_exclusion_r3": solve_inclusion_exclusion,
    "M1.last_digit_power_r3": solve_last_digit_power,
    "M1.linear_equation_r3": solve_linear_equation,
    "M1.median_list_r3": solve_median_list,
    "M1.mixture_r4": solve_mixture,
    "M1.painted_cube_r3": solve_painted_cube,
    "M1.percent_change_r3": solve_percent_change,
    "M1.pipes_work_r3": solve_pipes_work,
}
