# ruff: noqa: E501
"""M1 batch 1, family "counting": inclusion-exclusion, choosing subsets, slot-filling with restrictions, ways to pay, worst-case (pigeonhole) draws."""

from __future__ import annotations

import itertools
import math
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_m1_common import WHOLE, and_, ctx, m1
from studies.m0.vocab import NAMES


@m1("counting")
def inclusion_exclusion(level: int, r: random.Random) -> Built:
    """structured: {"total": N, "sets": [name], "sizes": [|A|, ...], "pairs": [|A and B|, ...] (2 sets: one entry; 3 sets: AB, AC, BC), "triple": |A and B and C| or null,
    "ask": "none" | "any" | "exactly_one" | "exactly_two"}. Answer: how many of the N people are in none of the sets / at least one set / exactly one / exactly two,
    by inclusion-exclusion over the stated overlaps. The answer is never one of the stated numbers."""
    three = level >= 3
    m = 6 + 6 * level
    acts = r.sample(("play chess", "play tennis", "swim", "paint", "sing in the choir", "read comics", "ride a bike"), 3 if three else 2)
    if not three:
        ao, bo, ab, none = (r.randint(1, m) for _ in range(4))
        sizes, pairs, triple, total = [ao + ab, bo + ab], [ab], None, ao + bo + ab + none
        reg = {"none": none, "any": ao + bo + ab, "exactly_one": ao + bo, "exactly_two": ab}
        ask = r.choice(("none", "any", "any"))
    else:
        reg3 = {s: r.randint(1, m) for s in ("a", "b", "c", "ab", "ac", "bc", "abc", "none")}
        sizes = [reg3["a"] + reg3["ab"] + reg3["ac"] + reg3["abc"], reg3["b"] + reg3["ab"] + reg3["bc"] + reg3["abc"], reg3["c"] + reg3["ac"] + reg3["bc"] + reg3["abc"]]
        pairs = [reg3["ab"] + reg3["abc"], reg3["ac"] + reg3["abc"], reg3["bc"] + reg3["abc"]]
        triple = reg3["abc"]
        total = sum(reg3.values())
        reg = {"none": reg3["none"], "any": total - reg3["none"], "exactly_one": reg3["a"] + reg3["b"] + reg3["c"], "exactly_two": reg3["ab"] + reg3["ac"] + reg3["bc"]}
        ask = r.choice(("none", "any", "exactly_one", "exactly_two") if level >= 5 else ("none", "any"))
    ans = reg[ask]
    stated = [total, *sizes, *pairs] + ([triple] if triple is not None else [])
    if ans in stated:
        raise Retry
    what = {"none": "do none of these things", "any": "do at least one of these things", "exactly_one": "do exactly one of these things", "exactly_two": "do exactly two of these things"}[ask]
    if not three:
        facts = f"{sizes[0]} of them {acts[0]}, {sizes[1]} of them {acts[1]}, and {pairs[0]} of them do both"
    else:
        facts = (f"{sizes[0]} {acts[0]}, {sizes[1]} {acts[1]} and {sizes[2]} {acts[2]}; {pairs[0]} do both the first and the second, {pairs[1]} do both the first and the third, "
                 f"{pairs[2]} do both the second and the third, and {triple} do all three")
    q = f"{total} people were asked what they do. {facts[0].upper() + facts[1:]}. How many of the {total} people {what}? {WHOLE}"
    return Built(q, {"total": total, "sets": acts, "sizes": sizes, "pairs": pairs, "triple": triple, "ask": ask}, str(ans), "number", None)


@m1("counting")
def binomial_choose(level: int, r: random.Random) -> Built:
    """structured: {"shape": "plain" | "include" | "two_groups", "n": n, "k": k, "x": x, "y": y, "j": j}. plain: choose k of n people (order does not matter): C(n, k).
    include: as plain but one named person must be in the group: C(n - 1, k - 1). two_groups: x women and y men, choose k with exactly j women: C(x, j) * C(y, k - j).
    (Fields not used by a shape are 0.)"""
    shape = r.choice(("plain", "include", "two_groups"))
    top = 12 + 2 * level
    name = r.choice(NAMES)
    if shape == "plain":
        n = r.randint(7, top)
        k = r.randint(3, n - 3)
        ans = math.comb(n, k)
        q = f"A club has {n} members. A committee of {k} members is chosen (the order of choosing does not matter). How many different committees are possible? {WHOLE}"
        st = {"shape": shape, "n": n, "k": k, "x": 0, "y": 0, "j": 0}
    elif shape == "include":
        n = r.randint(7, top)
        k = r.randint(3, n - 3)
        ans = math.comb(n - 1, k - 1)
        q = f"A club has {n} members, and {name} is one of them. A committee of {k} members is chosen (the order does not matter), and {name} must be on it. How many different committees are possible? {WHOLE}"
        st = {"shape": shape, "n": n, "k": k, "x": 0, "y": 0, "j": 0}
    else:
        x, y = r.randint(3, top - 2), r.randint(3, top - 2)
        k = r.randint(3, min(x + y - 2, 3 + level))
        j = r.randint(max(1, k - y), min(x, k - 1))
        ans = math.comb(x, j) * math.comb(y, k - j)
        q = f"A group has {x} women and {y} men. A team of {k} people is chosen (the order does not matter) with exactly {j} women on it. How many different teams are possible? {WHOLE}"
        st = {"shape": shape, "n": 0, "k": k, "x": x, "y": y, "j": j}
    if ans < 10 or ans > 3_000_000:
        raise Retry
    return Built(f"{ctx(r)} {q}", st, str(ans), "number", None)


@m1("counting")
def slot_permutations(level: int, r: random.Random) -> Built:
    """structured: {"digits": [allowed digits], "length": s, "repeat": true | false, "lead_nonzero": true | false, "parity": "even" | "odd" | "any"}.
    Answer: how many s-digit numbers (every position filled from `digits`; no digit used twice unless `repeat`; first digit not 0 if `lead_nonzero`;
    last digit of the stated parity) exist. Counted by filling the most restricted positions first."""
    n = r.randint(5 + level // 3, 9 + (level >= 4))
    digits = sorted(r.sample(range(10), n))
    s = r.randint(3, 3 + (level + 1) // 3 + (level >= 5))
    s = min(s, n)
    rep = r.random() < 0.35
    lead = 0 in digits and r.random() < 0.8
    par = r.choice(("even", "odd", "any"))
    if par == "any" and not (lead and 0 in digits):
        raise Retry
    cnt = 0
    for tup in (itertools.product(digits, repeat=s) if rep else itertools.permutations(digits, s)):
        if lead and tup[0] == 0:
            continue
        if par == "even" and tup[-1] % 2:
            continue
        if par == "odd" and tup[-1] % 2 == 0:
            continue
        cnt += 1
    naive = n**s if rep else math.perm(n, s)
    if cnt == naive or cnt < 10:
        raise Retry
    rules = ["no digit may be used more than once" if not rep else "a digit may be used more than once"]
    if lead:
        rules.append("the number may not start with the digit 0")
    if par != "any":
        rules.append(f"the number must be {par}")
    q = f"How many {s}-digit numbers can be written using only the digits {and_([str(d) for d in digits])}, if " + and_(rules) + f"? {WHOLE}"
    return Built(q, {"digits": digits, "length": s, "repeat": rep, "lead_nonzero": lead, "parity": par}, str(cnt), "number", None)


@m1("counting", "borderline")
def change_ways(level: int, r: random.Random) -> Built:
    """structured: {"coins": [values in cents, distinct], "target": T}. Answer: the number of different multisets of coins (unlimited supply of each value) that add up to exactly T cents.
    Borderline against digit_puzzle (both enumerate integer solutions of linear constraints); here the answer counts all solutions."""
    c = 3
    coins = sorted(r.sample((2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25), c))
    t = r.randint(max(coins) * 3, max(60 + 15 * level, max(coins) * 3 + 30))
    ways = [1] + [0] * t
    for v in coins:
        for a in range(v, t + 1):
            ways[a] += ways[a - v]
    ans = ways[t]
    if ans < 4 or ans > 150 or t // max(coins) + 1 == ans:
        raise Retry
    q = f"Using only coins worth {and_([str(v) for v in coins])} cents, with as many coins of each value available as you like, in how many different ways can exactly {t} cents be paid? (Two ways are the same if they use the same number of coins of each value; the order does not matter.) {WHOLE}"
    return Built(q, {"coins": coins, "target": t}, str(ans), "number", None)


@m1("counting")
def pigeonhole_worst_case(level: int, r: random.Random) -> Built:
    """structured: {"counts": [n_1..n_c] (items per colour in a bag), "goal": "same" | "all", "k": k}. Items are drawn blindly one at a time without replacement.
    Answer: the number of draws that GUARANTEES, however unlucky, either k items of one colour (goal "same") or at least one item of every colour (goal "all", k = 1).
    same: 1 + sum(min(n_i, k - 1)); all: total - min(n_i) + 1. The generator requires the cap min(n_i, k - 1) to bite for goal "same"."""
    c = 3 + (level >= 2) + (level >= 4)
    counts = [r.randint(2, 12 + 4 * level) for _ in range(c)]
    goal = r.choice(("same", "all"))
    if goal == "same":
        k = r.randint(3, max(3, max(counts) - 1))
        if max(counts) < k:
            raise Retry
        ans = 1 + sum(min(n, k - 1) for n in counts)
        if ans == (k - 1) * c + 1:
            raise Retry
        what = f"at least {k} marbles of the same colour"
    else:
        k = 1
        ans = sum(counts) - min(counts) + 1
        if min(counts) == max(counts):
            raise Retry
        what = "at least one marble of every colour"
    cols = r.sample(("red", "blue", "green", "yellow", "purple", "white", "black"), c)
    inv = ", ".join(f"{n} {col}" for n, col in zip(counts, cols, strict=True))
    q = f"A bag holds marbles of {c} colours: {inv}. Marbles are drawn one at a time without looking and are not put back. What is the smallest number of marbles that must be drawn to be certain, however unlucky the draws are, of having {what}? {WHOLE}"
    return Built(q, {"counts": counts, "goal": goal, "k": k}, str(ans), "number", None)
