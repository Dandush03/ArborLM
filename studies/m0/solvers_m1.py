# ruff: noqa: E501
"""Independent second solvers for M1. Read only the item's structured form; import nothing from the generators.

Algebra problems are solved by search over candidate integers; accumulation problems by stepping one unit at a time;
percentages with ``decimal.Decimal``. Written by the implementer, not by a separate auditor context: ruling needed 3.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _dec(v: Decimal) -> str:
    c = v * 100
    if c != c.to_integral_value():
        raise ValueError("more than two decimals")
    n = int(c)
    sign = "-" if n < 0 else ""
    whole, cents = divmod(abs(n), 100)
    return f"{sign}{whole}" if cents == 0 else f"{sign}{whole}.{cents:02d}".rstrip("0")


def shopping(s: dict[str, Any]) -> str:
    spent = 0
    for count, price in s["items"]:
        for _ in range(count):  # repeated addition of the unit price
            spent += price
    return _dec(Decimal(s["paid"] - spent) / 100)


def speed_distance(s: dict[str, Any]) -> str:
    km = 0
    hrs = 0
    for h, v in s["legs"]:
        for _ in range(h):  # hour by hour
            km += v
            hrs += 1
    return _dec(Decimal(km) / Decimal(hrs)) if s["average"] else str(km)


def pipes_work(s: dict[str, Any]) -> str:
    level, minutes = 0, 0
    while level < s["volume"]:
        level += s["a"] + s["b"] - s["drain"]
        minutes += 1
    if level != s["volume"]:
        raise ValueError("overshoots the volume")
    return str(minutes)


def percent_change(s: dict[str, Any]) -> str:
    v = Decimal(s["price"])
    for kind, p in s["steps"]:
        v = v * (Decimal(100) + (p if kind == "up" else -p)) / Decimal(100)
    return _dec(v)


def tip_split(s: dict[str, Any]) -> str:
    total = Decimal(s["bill"]) + Decimal(s["bill"]) * Decimal(s["tip"]) / Decimal(100)
    return _dec(total / Decimal(s["people"]))


def ratio_share(s: dict[str, Any]) -> str:
    share = [0] * len(s["parts"])
    left = s["total"]
    while left > 0:  # hand the stickers out one round at a time
        for i, p in enumerate(s["parts"]):
            share[i] += p
            left -= p
    if left != 0:
        raise ValueError("does not divide")
    return str(share[s["who"]])


def mixture(s: dict[str, Any]) -> str:
    cost = Decimal(s["x"] * s["a"] + s["y"] * s["b"]) / Decimal(s["x"] + s["y"]) + Decimal(s["packing"])
    return _dec(cost)


def linear_equation(s: dict[str, Any]) -> str:
    sol = [x for x in range(-2000, 4000) if s["k"] * x + s["m"] == s["j"] * x + s["n"]]
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return str(sol[0])


def consecutive(s: dict[str, Any]) -> str:
    sol = [a for a in range(-500, 3000) if sum(a + s["step"] * i for i in range(s["count"])) == s["sum"]]
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return str(sol[0] + s["step"] * (s["count"] - 1))


def ages(s: dict[str, Any]) -> str:
    sol = [b for b in range(1, 150) if (s["k"] * b + s["t"]) + (b + s["t"]) == s["sum"]]
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return str(sol[0])


def average_missing(s: dict[str, Any]) -> str:
    sol = [x for x in range(0, 1001) if (sum(s["scores"]) + x) * 100 == s["mean_cents"] * s["n"]]
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return str(sol[0])


def rectangle(s: dict[str, Any]) -> str:
    sol = [w for w in range(1, 500) if 2 * (w + s["ratio"] * w) == s["perimeter"]]
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return str(sol[0] * s["ratio"] * sol[0])


def arithmetic_series(s: dict[str, Any]) -> str:
    total, today = 0, s["first"]
    for _ in range(s["days"]):  # day by day
        total += today
        today += s["step"]
    return str(total)


def coins(s: dict[str, Any]) -> str:
    sol = [lo_n for lo_n in range(0, s["count"] + 1) if lo_n * s["lo"] + (s["count"] - lo_n) * s["hi"] == s["cents"]]
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return str(sol[0] if s["ask"] == "lo" else s["count"] - sol[0])


def clock_duration(s: dict[str, Any]) -> str:
    n = 0
    for dep, arr in s["legs"]:
        for minute in range(dep, arr):  # count each minute on the move
            n += 1 if minute >= 0 else 0
    return str(n)


def fraction_remainder(s: dict[str, Any]) -> str:
    money = Decimal(s["start"])
    money -= money / Decimal(s["a"])
    money -= money / Decimal(s["b"])
    if money != money.to_integral_value():
        raise ValueError("not whole dollars")
    return str(int(money))


SOLVERS = {
    f"M1.{f.__name__}": f
    for f in (shopping, speed_distance, pipes_work, percent_change, tip_split, ratio_share, mixture, linear_equation, consecutive,
              ages, average_missing, rectangle, arithmetic_series, coins, clock_duration, fraction_remainder)
}
