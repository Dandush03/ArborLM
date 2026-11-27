# ruff: noqa: E501
"""M1 fix round 3, part C: algebra (digit puzzles, quadratics), geometry, sequences. Revisions of the rev2 / batch-1 shapes (immutable). ``tiered_pricing`` is carried over unchanged (it already states its
format, never retries and passes capacity), as in the audit's verdict REGISTRABLE AS IS."""

from __future__ import annotations

import math
import random
from typing import Any

from studies.m0.core import Built
from studies.m0.lineages_m1_fix3_common import WHOLE, and_, ctx, r3, until
from studies.m0.vocab import NAMES

# ------------------------------------------------------------------ digit puzzles

MIN_LEFT = 4  # every set of all-but-one printed clues leaves at least this many numbers (attempted construction; see the docstring and NOTES_FIX3_M1.md)
_NUMS: dict[int, list[tuple[int, tuple[int, ...]]]] = {nd: [(n, tuple(int(c) for c in str(n))) for n in range(10 ** (nd - 1), 10**nd)] for nd in (2, 3)}
_FIT: dict[tuple[int, tuple[Any, ...]], frozenset[int]] = {}


def _holds_raw(n: int, ds: tuple[int, ...], c: tuple[Any, ...], once: bool = False) -> Any:
    """Does clue ``c`` hold for the number ``n`` (digits ``ds``)? ``contains_digit`` read 'at least once' (the wording), or with ``once`` 'exactly once' (the other reading, used in the uniqueness check)."""
    k = c[0]
    if k == "digit_sum":
        return sum(ds) == c[1]
    if k == "digit_product":
        return math.prod(ds) == c[1]
    if k == "reverse_gap":
        return int(str(n)[::-1]) - n == c[1]
    if k == "multiple_of":
        return n % c[1] == 0
    if k == "parity":
        return (n % 2 == 0) == (c[1] == "even")
    if k == "first_gt_last":
        return ds[0] > ds[-1]
    if k == "first_lt_last":
        return ds[0] < ds[-1]
    if k == "greater_than":
        return n > c[1]
    if k == "less_than":
        return n < c[1]
    if k == "contains_digit":
        return (ds.count(c[1]) == 1) if once else (c[1] in ds)
    if k == "ends_differ_by":
        return abs(ds[0] - ds[-1]) == c[1]
    if k == "digits_distinct":
        return len(set(ds)) == len(ds)
    if k == "middle_is_mean":
        return len(ds) == 3 and 2 * ds[1] == ds[0] + ds[2]
    return ds[0] == c[1] * ds[-1]  # digit_relation


def clue_holds(n: int, ds: tuple[int, ...], c: tuple[Any, ...], once: bool = False) -> bool:
    return bool(_holds_raw(n, ds, c, once))


def fit_set(nd: int, c: tuple[Any, ...], once: bool = False) -> frozenset[int]:
    key = (nd, (once, *c))
    if key not in _FIT:
        _FIT[key] = frozenset(n for n, ds in _NUMS[nd] if clue_holds(n, ds, c, once))
    return _FIT[key]


def clue_text(c: list[Any]) -> str:
    k = c[0]
    if k == "digit_sum":
        return f"its digits add up to {c[1]}"
    if k == "digit_product":
        return f"the product of its digits is {c[1]}"
    if k == "reverse_gap":
        rv = "the number made by writing its digits in the opposite order (a leading 0 is dropped, so 120 turned round gives 21)"
        return f"{rv} is the same as it" if c[1] == 0 else f"{rv} is {abs(c[1])} {'more' if c[1] > 0 else 'less'} than it"
    if k == "multiple_of":
        return f"it is a multiple of {c[1]}"
    if k == "parity":
        return f"it is {c[1]}"
    if k == "first_gt_last":
        return "its first digit is larger than its last digit"
    if k == "first_lt_last":
        return "its first digit is smaller than its last digit"
    if k == "greater_than":
        return f"it is greater than {c[1]}"
    if k == "less_than":
        return f"it is less than {c[1]}"
    if k == "contains_digit":
        return f"the digit {c[1]} appears in it at least once"
    if k == "ends_differ_by":
        return f"its first and last digits differ by {c[1]} (in either order)"
    if k == "digits_distinct":
        return "no two of its digits are the same"
    if k == "middle_is_mean":
        return "its middle digit is exactly halfway between its first and last digits"
    return f"its first digit is {c[1]} times its last digit"


@r3("digit_puzzle", "algebra")
def digit_puzzle_r3(level: int, r: random.Random) -> Built:
    """structured {"digits": 2 | 3, "clues": [[kind, parameter?]]}. The secret is drawn; every clue that is TRUE of it is a candidate clue (including a random threshold 'it is greater than N' (N uniform below the secret) and 'it is less than M' (M uniform above it), and 'the digit d appears in it at least once' only for a digit that
    occurs EXACTLY once in the secret, so the clue is true under both readings 'at least once' and 'exactly once'). In a random order clues are added until exactly one number fits, then every clue whose
    removal keeps the answer unique is removed: the printed set is MINIMAL (dropping any clue leaves at least two numbers, so no proper subset of the printed clues, in particular no pair of printed
    clues when there are three or four, identifies the number; audit: 'the first two clues' gave 0.43 at level 0 and 0.13-0.16 later). Every set of all-but-one printed clues leaves at least MIN_LEFT = 4 numbers (8 was tried: with five necessary clues at levels 5-6 a valid draw is found in about 1 in 4 attempts of 20,000 and takes seconds; so no shorter list of the clues comes close to naming the answer). The number of clues is 3 + (level >= 3) + (level >= 5) (rev2 and batch 1: at least 2 + (level >= 3) + (level >= 5), usually one fewer than here once the set is
    minimal; with two necessary clues the space is only about 2,000 items, so one more clue is the price of capacity) (a loop on this validity property only). Uniqueness holds under both readings (the 'exactly once' candidates are a subset of the 'at least once' candidates and contain the secret). Level 0 uses 2-digit
    numbers, the rest 3-digit numbers (no leading 0); a leading 0 is dropped when a number is turned round, and the item says so."""
    nd = 2 if level == 0 else 3
    lo = 10 ** (nd - 1)
    want = 3 + (level >= 3) + (level >= 5)

    def draw() -> tuple[int, list[tuple[Any, ...]]] | None:
        secret = r.randint(lo, 10**nd - 1)
        ds = tuple(int(c) for c in str(secret))
        cand: list[tuple[Any, ...]] = [("digit_sum", sum(ds)), ("digit_product", math.prod(ds)), ("reverse_gap", int(str(secret)[::-1]) - secret), ("parity", "even" if secret % 2 == 0 else "odd"),
                                       ("ends_differ_by", abs(ds[0] - ds[-1])), ("first_gt_last",) if ds[0] > ds[-1] else ("first_lt_last",)]
        cand += [("multiple_of", m) for m in (3, 4, 6, 7, 9, 11, 12, 13) if secret % m == 0]
        cand += [("digit_relation", q) for q in (2, 3) if ds[0] == q * ds[-1]]
        cand += [("contains_digit", d) for d in sorted(set(ds)) if ds.count(d) == 1]
        cand.append(("greater_than", r.randint(lo - 1, secret - 1)))  # a threshold below the secret, uniform over its valid range
        cand.append(("less_than", r.randint(secret + 1, 10**nd)))  # a threshold above the secret, uniform over its valid range
        if len(set(ds)) == len(ds):
            cand.append(("digits_distinct",))
        if nd == 3 and 2 * ds[1] == ds[0] + ds[2]:
            cand.append(("middle_is_mean",))
        r.shuffle(cand)
        chosen: list[tuple[Any, ...]] = []
        fit: frozenset[int] | None = None
        for c in cand:
            chosen.append(c)
            fit = fit_set(nd, c) if fit is None else fit & fit_set(nd, c)
            if fit == frozenset({secret}):
                break
        if fit != frozenset({secret}):
            return None
        for c in list(chosen):  # prune to a minimal set
            rest = [x for x in chosen if x is not c]
            if rest and frozenset.intersection(*(fit_set(nd, x) for x in rest)) == frozenset({secret}):
                chosen = rest
        if len(chosen) != want:
            return None
        # every proper subset (in particular every pair of printed clues) must leave at least MIN_LEFT numbers, so no short subset of the clues nearly identifies the answer
        for i in range(len(chosen)):
            if len(frozenset.intersection(*(fit_set(nd, x) for j, x in enumerate(chosen) if j != i))) < MIN_LEFT:
                return None
        return secret, chosen

    secret, chosen = until(draw)
    chosen = list(chosen)
    r.shuffle(chosen)
    clues = [list(x) for x in chosen]
    q = f"{ctx(r)} Find the {nd}-digit number (it does not start with 0) for which all of these are true: " + "; ".join(clue_text(c) for c in clues) + f". There is exactly one such number. {WHOLE}"
    return Built(q, {"digits": nd, "clues": clues}, str(secret), "number", None)


# ------------------------------------------------------------------ quadratics


@r3("quadratic_area", "algebra")
def quadratic_area_r3(level: int, r: random.Random) -> Built:
    """structured {"shape": "rect_area" | "rect_perimeter" | "product" | "squares", "d", "area", "perimeter", "total"}. As batch 1 (positive whole root x of a quadratic; d >= max(3, isqrt(4x) + 3) so that
    'sqrt(area)' and 'sqrt(area) - d/2' are not the root) with the ranges widened: x 2..150+25*level, d from that minimum up to the minimum + 120 + 15*level. The shape is drawn first (a quarter each)."""
    shape = r.choice(("rect_area", "rect_perimeter", "product", "squares"))
    hi = 150 + 25 * level
    x = r.randint(2, hi)
    lo_d = max(3, math.isqrt(4 * x) + 3)
    d = r.randint(lo_d, lo_d + 120 + 15 * level)
    name = r.choice(("garden", "poster", "playing field", "banner"))
    if shape == "rect_area":
        ans, area = x, x * (x + d)
        q = f"A rectangular {name} has an area of {area} square metres. Its length is {d} metres more than its width. What is its width, in metres? {WHOLE}"
        st = {"shape": shape, "d": d, "area": area, "perimeter": 0, "total": 0}
    elif shape == "rect_perimeter":
        ln = x + d
        area, per = x * ln, 2 * (x + ln)
        ans = ln
        q = f"A rectangular {name} has a perimeter of {per} metres and an area of {area} square metres. What is the length of its longer side, in metres? {WHOLE}"
        st = {"shape": shape, "d": 0, "area": area, "perimeter": per, "total": 0}
    elif shape == "product":
        ans, area = x, x * (x + d)
        q = f"Two positive whole numbers differ by {d}, and their product is {area}. What is the smaller of the two numbers? {WHOLE}"
        st = {"shape": shape, "d": d, "area": area, "perimeter": 0, "total": 0}
    else:
        ans, tot = x, x * x + (x + d) ** 2
        q = f"Two positive whole numbers differ by {d}, and the sum of their squares is {tot}. What is the smaller of the two numbers? {WHOLE}"
        st = {"shape": shape, "d": d, "area": 0, "perimeter": 0, "total": tot}
    return Built(f"{ctx(r)} {q}", st, str(ans), "number", None)


# ------------------------------------------------------------------ geometry


def _primitives(limit: int) -> list[tuple[int, int, int]]:
    out: set[tuple[int, int, int]] = set()
    m = 2
    while m * m + 1 <= limit:
        for n in range(1, m):
            if (m - n) % 2 and math.gcd(m, n) == 1 and m * m + n * n <= limit:
                a, b = sorted((m * m - n * n, 2 * m * n))
                out.add((a, b, m * m + n * n))
        m += 1
    return sorted(out)


_PRIM = _primitives(3200)


@r3("pythagoras", "geometry")
def pythagoras_r3(level: int, r: random.Random) -> Built:
    """ATTEMPT, NOT REGISTERED (see NOT_REGISTERED in lineages_m1_fix3.py). structured {"shape", "legs": [a, b], "hyp": c, "given": [..]}. The triple is drawn PRIMITIVE-FIRST: a primitive triple uniformly from all
    primitive triples with hypotenuse <= 400 + 400*level, then a scale factor uniformly from 1..limit // c0, so that a catalogue of the few small famous triples covers a small share of the items. The
    number of integer right triangles of that size is a few hundred to a few thousand, which is far below the demand; see the manifest."""
    limit = min(400 + 400 * level, 3200)
    a0, b0, c0 = r.choice([t for t in _PRIM if t[2] <= limit])
    k = r.randint(1, limit // c0)
    a, b, c = a0 * k, b0 * k, c0 * k
    if r.random() < 0.5:
        a, b = b, a
    shape = r.choice(("ladder_top", "ladder_base", "walk", "diagonal", "perimeter"))
    name = r.choice(NAMES)
    if shape == "ladder_top":
        ans, given = b, [c, a]
        q = f"A ladder {c} metres long leans against a vertical wall. Its foot is {a} metres from the base of the wall, on level ground. How high up the wall does the top of the ladder reach, in metres? {WHOLE}"
    elif shape == "ladder_base":
        ans, given = a, [c, b]
        q = f"A ladder {c} metres long leans against a vertical wall and its top reaches {b} metres up the wall. How far is its foot from the base of the wall, in metres, on level ground? {WHOLE}"
    elif shape == "walk":
        ans, given = c, [a, b]
        q = f"{name} walks {a} metres due east and then {b} metres due north. How far is {name} now from the starting point in a straight line, in metres? {WHOLE}"
    elif shape == "diagonal":
        ans, given = c, [a, b]
        q = f"A rectangular screen is {a} centimetres wide and {b} centimetres tall. What is the length of its diagonal, in centimetres? {WHOLE}"
    else:
        ans, given = a + b + c, [a, b]
        q = f"A right-angled triangle has two short sides (the sides next to the right angle) of {a} centimetres and {b} centimetres. What is the length of the whole boundary of the triangle (its perimeter), in centimetres? {WHOLE}"
    return Built(f"{ctx(r)} {q}", {"shape": shape, "legs": [a, b], "hyp": c, "given": given}, str(ans), "number", None)


@r3("grid_perimeter", "geometry")
def grid_perimeter_r3(level: int, r: random.Random) -> Built:
    """structured {"rows": [[[first_column, last_column], ...] per row, top row first]}. n unit squares (n uniform on 5+3*level .. 13+3*level; rev2 had exactly 9+3*level) on distinct random cells of a box
    of about d * n cells (d drawn from 2, 3, 4). Wording (one reading only): two squares that share a SIDE are glued along it; the perimeter is the number of unit sides that belong to exactly ONE square
    (a side shared by two squares is not counted at all; squares that meet only at a corner share no side). Key: 4 n - 2 * (number of shared sides). The wider spread of n and of the density spreads the
    answer (rev2: the most frequent answer was 0.13-0.24)."""
    ncell = r.randint(5 + 3 * level, 13 + 3 * level)
    dens = r.choice((2, 3, 4))
    w = round(math.sqrt(dens * ncell))
    h = -(-dens * ncell // w)
    cells = set(r.sample([(y, x) for y in range(h) for x in range(w)], ncell))
    per = sum(1 for (y, x) in cells for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (y + dy, x + dx) not in cells)
    ys = sorted({y for y, _ in cells})
    rows: list[list[list[int]]] = []
    for y in range(ys[0], ys[-1] + 1):
        xs = sorted(x for yy, x in cells if yy == y)
        runs: list[list[int]] = []
        for x in xs:
            if runs and runs[-1][1] == x - 1:
                runs[-1][1] = x
            else:
                runs.append([x, x])
        rows.append([[a + 1, b + 1] for a, b in runs])
    txt = " ".join(f"Row {i + 1} (counting from the top): " + (", ".join(f"columns {a} to {b}" if a != b else f"column {a}" for a, b in rr) if rr else "no squares") + "." for i, rr in enumerate(rows))
    q = (f"Unit squares (each side 1 unit long) are placed on a grid. {txt} Squares with the same column number in neighbouring rows sit directly above and below each other. "
         f"Two squares that share a side are glued together along that side (squares that meet only at a corner share no side). The perimeter of the whole figure is the number of unit-length sides that belong to "
         f"exactly one square: a side shared by two squares is not counted at all. What is the perimeter of the figure, in units? {WHOLE}")
    return Built(q, {"rows": rows}, str(per), "number", None)


def painted_count(a: int, b: int, c: int, bottom_unpainted: bool, faces: int) -> int:
    """Cubes with exactly ``faces`` painted faces in an a x b x c box by position classes (closed form, no loops over cubes). x and y: an end (2 positions, 1 face) or inside (a - 2, 0 faces);
    z: the top (1 position, 1 face), the bottom (1 position, 0 or 1 face) or between (c - 2, 0 faces)."""
    tot = 0
    for nx, fx in ((2, 1), (a - 2, 0)):
        for ny, fy in ((2, 1), (b - 2, 0)):
            for nz, fz in ((1, 1), (1, 0 if bottom_unpainted else 1), (c - 2, 0)):
                if fx + fy + fz == faces:
                    tot += nx * ny * nz
    return tot


@r3("painted_cube", "geometry")
def painted_cube_r3(level: int, r: random.Random) -> Built:
    """structured {"dims", "bottom_unpainted", "faces"}. As rev2 with wider dimensions (3..30+4*level; rev2 level 0 had 16,968 distinct items) and the count by position classes (closed form,
    checked against a loop over every cube in the tests). Faces (0, 1 or 2) drawn first; the bottom is painted or not (stated)."""
    f = r.choice((0, 1, 2))
    ba = r.random() < 0.5
    top = 30 + 4 * level
    a, b, c = (r.randint(3, top) for _ in range(3))
    cnt = painted_count(a, b, c, ba, f)
    paint = "every outer face is painted red except the bottom face (the face on the table), which stays unpainted" if ba else "every outer face (including the bottom face on the table) is painted red"
    q = (f"{ctx(r)} A block is made from small cubes of the same size glued together into a box {a} cubes long, {b} cubes wide and {c} cubes high. The whole box is placed on a table and {paint}. "
         f"Then the box is taken apart into the small cubes. How many small cubes have exactly {f} painted {'face' if f == 1 else 'faces'}? {WHOLE}")
    return Built(q, {"dims": [a, b, c], "bottom_unpainted": ba, "faces": f}, str(cnt), "number", None)


# ------------------------------------------------------------------ sequences


@r3("recurrence_iterate", "sequences")
def recurrence_iterate_r3(level: int, r: random.Random) -> Built:
    """structured {"shape": "sum_prev_two" | "affine" | "add_index", "first": [a] or [a, b], "mult": c, "add": d, "position": n}. Terms are numbered from 1; the answer is the term at `position`.
    sum_prev_two: first two terms 1..299, position 6+level..9+2*level. affine: first term 1..199, term = c * previous + d with c in {2, 3} and d in -(min(40, (c-1)a - 1))..40, d != 0 (so every term is positive and
    the list grows), position 5+level//2..7+level//2. add_index: first term 1..400, every term is the previous plus `add` times its own position (add 1..9), position 6+level..9+2*level. All values stay
    below 10**8 by these ranges, so there is no retry (batch 1 retried on size and sign)."""
    shape = r.choice(("sum_prev_two", "affine", "add_index"))
    if shape == "sum_prev_two":
        n = r.randint(6 + level, 9 + 2 * level)
        a, b = r.randint(1, 299), r.randint(1, 299)
        t = [a, b]
        while len(t) < n:
            t.append(t[-1] + t[-2])
        rule = f"The first two numbers are {a} and {b}. Every number after those is the sum of the two numbers just before it"
        st = {"shape": shape, "first": [a, b], "mult": 0, "add": 0, "position": n}
    elif shape == "affine":
        n = r.randint(5 + level // 2, 7 + level // 2)
        a, c = r.randint(1, 199), r.randint(2, 3)
        d = r.choice([v for v in range(-min(40, (c - 1) * a - 1), 41) if v != 0])
        t = [a]
        while len(t) < n:
            t.append(c * t[-1] + d)
        rule = f"The first number is {a}. Every number after it is {c} times the number just before it, {'plus' if d >= 0 else 'minus'} {abs(d)}"
        st = {"shape": shape, "first": [a], "mult": c, "add": d, "position": n}
    else:
        n = r.randint(6 + level, 9 + 2 * level)
        a, s = r.randint(1, 400), r.randint(1, 9)
        t = [a]
        while len(t) < n:
            t.append(t[-1] + s * (len(t) + 1))
        each = "its own position in the list" if s == 1 else f"{s} times its own position in the list"
        ex = (f"so the second number is the first plus {2 * s}, the third is the second plus {3 * s}, and so on")
        rule = f"The first number is {a}. Every number after it is the number just before it plus {each} ({ex})"
        st = {"shape": shape, "first": [a], "mult": 0, "add": s, "position": n}
    assert 0 < t[-1] < 10**8
    q = f"A list of numbers is built by a rule. {rule}. What is the number in position {n} of the list (position 1 is the first number)? {WHOLE}"
    return Built(f"{ctx(r)} {q}", st, str(t[-1]), "number", None)


@r3("finite_differences", "sequences")
def finite_differences_r3(level: int, r: random.Random) -> Built:
    """structured {"terms": [the printed first terms, positions 1..m], "degree": 2 | 3, "ask": position}. Integer polynomial with NON-NEGATIVE coefficients (so every term is positive, no retry): degree 2 below level 5:
    a 1..15, b 0..25, c 0..60; degree 3 from level 5: coefficients 0..60, 0..20, 0..9 and a leading 1..4. m = degree + 3 + (level >= 3) terms printed (positions 1..m); ask = m + 1 or m + 2.
    Answer: the term at the asked position (extend the table of differences or fit the polynomial). Batch 1 retried on negative or repeated terms and had a space of about 5,000 items."""
    deg = 2 if level < 5 else 3
    if deg == 2:
        poly = [r.randint(0, 60), r.randint(0, 25), r.randint(1, 15)]
    else:
        poly = [r.randint(0, 60), r.randint(0, 20), r.randint(0, 9), r.randint(1, 4)]

    def f(x: int) -> int:
        return sum(co * x**i for i, co in enumerate(poly))

    m = deg + 3 + (level >= 3)
    terms = [f(x) for x in range(1, m + 1)]
    ask = m + r.randint(1, 2)
    q = (f"The first {m} numbers of a pattern are {and_([str(t) for t in terms])}. The pattern continues in the same way, and each number is given by a polynomial of degree {deg} in its position "
         f"(position 1 is the first number). What is the number in position {ask}? {WHOLE}")
    return Built(f"{ctx(r)} {q}", {"terms": terms, "degree": deg, "ask": ask}, str(f(ask)), "number", None)
