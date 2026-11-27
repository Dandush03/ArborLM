# ruff: noqa: E501
"""M1 batch 1, family "division": whole-number division with remainders (floor and ceiling), nested, and counting multiples in a range."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1_common import WHOLE, m1
from studies.m0.vocab import NAMES, OBJECTS


@m1("division")
def division_counting(level: int, r: random.Random) -> Built:
    """structured: {"shape": "crates" | "multiples" | "empty_seats", ...}. crates: {"items": N, "box": k, "crate": m}: N items go into boxes of k (the last box may be partly filled), the boxes go
    into crates holding m boxes (the last crate may be partly filled); answer the number of crates: ceil(ceil(N / k) / m). multiples: {"low": a, "high": b, "div": d}: how many whole numbers from a to b
    inclusive are divisible by d: floor(b / d) - floor((a - 1) / d). empty_seats: {"people": N, "seats": k}: buses of k seats each carry everyone in as few buses as possible; answer the empty seats overall: ceil(N / k) * k - N.
    The generator rejects items where the answer equals the plain rounded quotient."""
    shape = r.choice(("crates", "multiples", "empty_seats"))
    s = 1 + level
    if shape == "crates":
        k, m = r.randint(4, 9 + 3 * s), r.randint(3, 6 + 2 * s)
        n = r.randint(3 * k * m, 20 * k * m + 400 * level)
        boxes = -(-n // k)
        ans = -(-boxes // m)
        if n % k == 0 or boxes % m == 0 or ans == round(n / (k * m)):
            raise Retry
        item = r.choice(OBJECTS)
        q = (f"A factory makes {n} {item}s. They are packed into boxes that each hold {k} {item}s, and the last box may be only partly full. The boxes are then loaded into crates that each hold {m} boxes, "
             f"and the last crate may be only partly full. How many crates are needed? {WHOLE}")
        st = {"shape": shape, "items": n, "box": k, "crate": m}
    elif shape == "multiples":
        d = r.randint(3, 8 + 3 * s)
        low = r.randint(1, 50 * s)
        high = low + r.randint(200, 800 * s)
        ans = high // d - (low - 1) // d
        if low % d == 0 or high % d == 0 or ans == round((high - low) / d):
            raise Retry
        q = f"How many whole numbers from {low} to {high}, both included, are exactly divisible by {d} (that is, leave remainder 0 when divided by {d})? {WHOLE}"
        st = {"shape": shape, "low": low, "high": high, "div": d}
    else:
        k = r.randint(8, 20 + 5 * s)
        n = r.randint(3 * k, 25 * k + 100 * level)
        ans = -(-n // k) * k - n
        if n % k == 0:
            raise Retry
        name = r.choice(NAMES)
        q = (f"{n} people must travel by bus, and {name} hires as few buses as possible. Each bus has {k} seats, and nobody stands. When all {n} people are on board, how many seats in total are empty? {WHOLE}")
        st = {"shape": shape, "people": n, "seats": k}
    return Built(q, st, str(ans), "number", None)
