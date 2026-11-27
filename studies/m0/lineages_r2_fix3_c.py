# ruff: noqa: E501
"""R2 fix round 3, part c: dynprog (max_subarray_sum, coin_change_min, lcs_length), numtheory (gcd_euclid, multiples_between), counting (count_letter, count_divisible), palindrome_check, stack_machine,
permutation_power. Same method as ``lineages_r2_fix3`` (tells removed by construction; a Retry only for validity). Self-checked, not independent review."""

from __future__ import annotations

import math
import random
from typing import Any

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import lst
from studies.m0.lineages_r2_fix3 import fix3
from studies.m0.vocab import PSEUDO

# ---------------------------------------------------------------- max_subarray_sum


def _kadane(xs: list[int]) -> int:
    best, cur = xs[0], xs[0]
    for x in xs[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


@fix3("dynprog", "R2.max_subarray_sum")
def max_subarray_sum(level: int, r: random.Random) -> Built:
    """Procedure: best-ending-here scan. structured: {"xs": [int]}. Fix round 3: the planted block (+++ - +++ between strongly negative separators) was a template ('best window of 7' and 'two longest runs plus the dip' read 1.00).
    By construction the row is now a chain of 2U+1 PHASES (U = 2 + level//3 'rising' phases between 'falling' ones, the row starts and ends with a falling phase), 3-8 numbers long (rising phases 6-12): in a rising phase numbers alternate between a
    positive number (3..9) and a dip (-1..-6), with a repeated positive on a 30% chance; in a falling phase a number is a small positive (1..3) on a 20% chance and otherwise -2..-9. So the best block crosses dips (a run of
    non-negative numbers is rarely the answer), it never starts at the first number or ends at the last (a prefix or a suffix is never the answer), and phase lengths vary (no fixed window). Nothing is drawn by what any rule gives.
    Answer: the largest total a block of neighbouring numbers can have (computed from the row, not from the plan)."""
    u = 2 + level // 3
    xs: list[int] = []
    for i in range(2 * u + 1):
        n = r.randint(6, 12) if i % 2 == 1 else r.randint(3, 8)
        if i % 2 == 1:
            sign = 1
            for _ in range(n):
                xs.append(r.randint(3, 9) if sign == 1 else -r.randint(1, 6))
                sign = 1 if (sign == -1 or r.random() < 0.3) else -1
        else:
            for _ in range(n):
                xs.append(r.randint(1, 3) if r.random() < 0.2 else -r.randint(2, 9))
    q = f"Pick a block of one or more numbers that sit next to each other in this row (no gaps). What is the largest total a block can have? Row: {lst(xs)}."
    return Built(q, {"xs": xs}, str(_kadane(xs)), "number", None)


# ---------------------------------------------------------------- coin_change_min


def _coin_table(coins: list[int], top: int) -> list[int]:
    inf = 10**9
    d = [0] + [inf] * top
    for v in range(1, top + 1):
        d[v] = min([d[v - c] + 1 for c in coins if c <= v] + [inf])
    return d


@fix3("dynprog", "R2.coin_change_min")
def coin_change_min(level: int, r: random.Random) -> Built:
    """Procedure: unbounded-supply capacity table, FEWEST coins (restored: round 2 had changed the question to the number of ways, which duplicated M1.change_ways_r2 and C1.coin_change_table). structured: {"coins": [int], "amounts": [int], "ask": "fewest"}.
    The batch-1 tells (largest-first greedy, amount // largest + 1) came from asking for ONE amount: a rule that is wrong on 40% of amounts is right on 60% of single questions. By construction the question now asks for the fewest coins
    for EACH of FIVE amounts, as a list, so a rule must be right on all five (a rule right on 70% of amounts is right on 17% of lists). Coins: 3 different worths from 3 .. 23 + 2*level (4 worths from level 3, the smallest at most 6),
    no coin of worth 1 (with 2 .. 14 and four amounts 'amount / largest coin, rounded up' read 0.24); an amount is drawn uniformly among the amounts from 40 + 4*level to 100 + 8*level that CAN be paid exactly (validity: a stated amount must be payable). Answer: the five least numbers of coins, in the order of the amounts."""
    k = 3 if level < 3 else 4
    top = 100 + 8 * level
    while True:
        coins = sorted(r.sample(range(3, 24 + 2 * level), k))
        if coins[0] <= 6:
            break
    tab = _coin_table(coins, top)
    lo = 40 + 4 * level
    ok = [a for a in range(lo, top + 1) if tab[a] < 10**9]
    if len(ok) < 10:
        raise Retry
    amounts = [r.choice(ok) for _ in range(5)]
    q = (f"You have an unlimited supply of coins worth {lst(coins[:-1])} and {coins[-1]}. For each of the amounts {lst(amounts[:-1])} and {amounts[-1]}, in this order, what is the smallest number of coins that adds up to exactly that amount? "
         "Give the five numbers separated by commas, in the same order as the amounts.")
    return Built(q, {"coins": coins, "amounts": amounts, "ask": "fewest"}, lst([tab[a] for a in amounts]), "list", None)


# ---------------------------------------------------------------- lcs_length


def _lcs(a: str, b: str) -> int:
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ca == cb else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


@fix3("dynprog", "R2.lcs_length")
def lcs_length(level: int, r: random.Random) -> Built:
    """Procedure: two-string prefix table. structured: {"a": str, "b": str}. Fix round 3: strings are longer (15 + 2*level .. 21 + 3*level letters; rev2 8 + level .. 14 + 2*level), because 'greedy matching, the better of both directions'
    read 0.46 at level 0 and fell to 0.08 only at level 6, and the constant guess 0.26. A common subsequence of length k (uniform from 35% of the shorter length to the shorter length minus 2, so the plant is longer than the common subsequence of two random strings) is PLANTED; the answer is computed by the table, not from the plan;
    the alphabet has 8-12 letters drawn per item (with 4-6 letters a random pair already shares a long subsequence, so the answers cluster at 60% of the length)."""
    alpha = "abcdefghijkl"[: r.randint(8, 12)]
    na, nb = r.randint(15 + 2 * level, 21 + 3 * level), r.randint(15 + 2 * level, 21 + 3 * level)
    k = r.randint(max(2, round(0.35 * min(na, nb))), min(na, nb) - 2)
    a = [r.choice(alpha) for _ in range(na)]
    b = [r.choice(alpha) for _ in range(nb)]
    ia, ib = sorted(r.sample(range(na), k)), sorted(r.sample(range(nb), k))
    for x, y in zip(ia, ib, strict=True):
        b[y] = a[x]
    sa, sb = "".join(a), "".join(b)
    q = ("A subsequence of a string is what is left after deleting zero or more of its letters, with the remaining letters kept in their original order (the letters need not be next to each other). "
         f"What is the length of the longest string that is a subsequence of both '{sa}' and '{sb}'?")
    return Built(q, {"a": sa, "b": sb}, str(_lcs(sa, sb)), "number", None)


# ---------------------------------------------------------------- gcd_euclid


def _squarefree(g: int) -> bool:
    return all(g % (p * p) for p in range(2, int(g**0.5) + 1))


@fix3("numtheory_b1", "R2.gcd_euclid")
def gcd_euclid(level: int, r: random.Random) -> Built:
    """Procedure: Euclid's remainder algorithm. structured: {"a": int, "b": int, "ask": "gcd" | "lcm"}. Fix round 3: in round 2 the common divisor g had no prime factor below 11, so at levels 0-2 it was always a PRIME (g <= 60) and
    'the smallest common prime factor' read 1.00 (0.90-0.94 at levels 3-6). By construction g is drawn uniformly among the numbers from 8 to 60 + 30*level that are NOT squarefree (they have a repeated prime factor, so g is never a prime, never
    the product of its distinct primes, and never the smallest or largest prime factor of a or b); the cofactors p, q (each at least 5, so one Euclid step 'a mod b' is not the answer) are coprime and not within 1 of each other (a stated validity: then g is the greatest common divisor).
    Answer: the greatest common divisor or the least common multiple (shape drawn 50/50)."""
    hi_g = 60 + 30 * level
    pool = [g for g in range(8, hi_g + 1) if not _squarefree(g)]
    g = r.choice(pool)
    hi = 60 + 30 * level
    p, q2 = r.randint(5, hi), r.randint(5, hi)
    if abs(p - q2) < 2 or math.gcd(p, q2) != 1:
        raise Retry
    a, b = g * max(p, q2), g * min(p, q2)
    if r.random() < 0.5:
        return Built(f"What is the greatest common divisor of {a} and {b}?", {"a": a, "b": b, "ask": "gcd"}, str(g), "number", None)
    return Built(f"What is the least common multiple of {a} and {b}?", {"a": a, "b": b, "ask": "lcm"}, str(a * b // g), "number", None)


# ---------------------------------------------------------------- multiples_between


@fix3("numtheory", "R2.multiples_between")
def multiples_between(level: int, r: random.Random) -> Built:
    """Procedure: the multiples of m inside a range, by floor division. structured: {"a": int, "b": int, "m": int, "ask": "count" | "sum"}. Fix round 3: with a and b drawn at random the count is b//m - (a-1)//m and every cheap formula is the true
    count plus an offset in {-1, 0, +1} that depends only on whether a or b is a multiple of m; a fixed offset is right whenever the end is not a multiple (measured: b//m - a//m 0.87-0.89, round((b-a+1)/m) 0.75), and no choice of how often
    the ends are multiples makes every such offset rare. By construction BOTH ENDS ARE MULTIPLES of m (the item says both ends are counted), so every formula that drops an end, floors the start or rounds is wrong on every item, and
    the only formulas that hold are the counting rule itself ((b-a)/m + 1, or the arithmetic series for the sum), which are the procedure and reported as such. The shape is drawn 50/50: the count of the multiples, or their sum.
    m 3..19; the first multiple m*k1 with k1 from 2 (so the first multiple is never m itself) to 300*(level+1)/m + 2, and the last m*k2 with k2 - k1 from max(2, 20//m) to 600*(level+1)//m (batch 1: a up to 50*(level+1), b - a up to 200*(level+1); widened for capacity: 5,915 and 14,724 different items at levels 0 and 1)."""
    m = r.randint(3, 19)
    k1 = r.randint(2, 300 * (level + 1) // m + 2)
    k2 = k1 + r.randint(max(2, 20 // m), 600 * (level + 1) // m)
    a, b = m * k1, m * k2
    if r.random() < 0.5:
        q = f"How many whole numbers from {a} to {b}, counting both ends, are multiples of {m}?"
        return Built(q, {"a": a, "b": b, "m": m, "ask": "count"}, str(k2 - k1 + 1), "number", None)
    ans = m * (k1 + k2) * (k2 - k1 + 1) // 2
    q = f"What is the sum of all the whole numbers from {a} to {b}, counting both ends, that are multiples of {m}?"
    return Built(q, {"a": a, "b": b, "m": m, "ask": "sum"}, str(ans), "number", None)


# ---------------------------------------------------------------- count_letter, count_divisible

_BY_COUNT: dict[str, dict[int, list[str]]] = {}


def _index() -> dict[str, dict[int, list[str]]]:
    if not _BY_COUNT:
        for w in PSEUDO:
            for ch in sorted(set(w)):
                _BY_COUNT.setdefault(ch, {}).setdefault(w.count(ch), []).append(w)
        for ch, d in _BY_COUNT.items():
            d[0] = [w for w in PSEUDO if ch not in w]
    return _BY_COUNT


@fix3("counting", "R2.count_letter")
def count_letter(level: int, r: random.Random) -> Built:
    """Procedure: a linear scan with a counter for a predicate. structured: {"words": [str], "letter": str}. Fix round 3: 'count the words that contain the letter' read 0.69-0.88 (most words hold the letter at most once) and the
    most frequent answer 0.59 at level 0. By construction the asked letter is one that some invented word can hold twice, each of the 8 + 2*level words holds it 0, 1 or 2 times (two independent chances each, with a per-item chance drawn from
    0.15 .. 0.75, so the totals spread), and ONE word, chosen at random, holds it exactly twice (planted: 'words that contain the letter' is then never the total). Words are drawn from the invented-word list, distinct.
    Answer: how many times the letter appears in total."""
    idx = _index()
    letters = sorted(ch for ch, d in idx.items() if 2 in d)
    ch = r.choice(letters)
    n = 8 + 2 * level
    p = r.choice((0.15, 0.3, 0.45, 0.6, 0.75))
    counts = [(r.random() < p) + (r.random() < p) for _ in range(n)]
    counts[r.randrange(n)] = 2
    words: list[str] = []
    for c in counts:
        pool = idx[ch][c]
        w = r.choice(pool)
        while w in words:
            w = r.choice(pool)
        words.append(w)
    q = f"How many times does the letter '{ch}' appear in total in these words: {' '.join(words)}?"
    return Built(q, {"words": words, "letter": ch}, str(sum(w.count(ch) for w in words)), "number", None)


@fix3("counting", "R2.count_divisible")
def count_divisible(level: int, r: random.Random) -> Built:
    """Procedure: a linear scan with a counter (or an accumulator) for a predicate. structured: {"xs": [int], "m": int, "t": int, "ask": "sum"}. Fix round 3: the COUNT shape is DROPPED (its answers are small: the constant guess read 0.23 and the estimate (numbers over t) // m 0.26, which no construction removes); '>= t' instead of '> t' read 0.98-0.99,
    'ignore > t' 0.65-0.74 and the constant 0 0.47 at level 0. By construction the threshold t is itself a multiple of m and the number t is PLANTED in the list once (so a reader who counts '>= t', or who ignores the threshold,
    always differs), m is 2, 3 or 4, the list has 18 + 4*level numbers (10 .. 99 + 100*(level//2)) so the counts spread, and the question is the SUM of the numbers that are divisible by m and greater than t.
    Answer: that sum."""
    m = r.choice((2, 3, 4))
    hi = 99 + 100 * (level // 2)
    t = m * r.randint(-(-(hi // 4) // m), (3 * hi // 5) // m)
    n = 18 + 4 * level
    xs = [r.randint(10, hi) for _ in range(n - 1)] + [t]
    r.shuffle(xs)
    sel = [x for x in xs if x % m == 0 and x > t]
    q = f"What is the sum of the numbers in this list that are divisible by {m} and greater than {t}? List: {lst(xs)}."
    return Built(q, {"xs": xs, "m": m, "t": t, "ask": "sum"}, str(sum(sel)), "number", None)


# ---------------------------------------------------------------- palindrome_check


@fix3("palindrome", "R2.palindrome_check")
def palindrome_check(level: int, r: random.Random) -> Built:
    """Procedure: compare a text with its reverse (spaces ignored). structured: {"phrase": str}. Fix round 3: 'at most one letter with an odd count' read 0.96 at every level, because a 'no' text was a palindrome with ONE letter
    replaced, which changes two letter counts. By construction a 'no' text is a palindrome with TWO of its letters SWAPPED (the letter counts are exactly those of a palindrome, so the count rule says 'yes' for both answers) and the
    texts are longer (2 * (12 + level) letters, or one more in the middle), so a rule that compares only the outer letters meets the swap on a small share of items. A swap that leaves a palindrome is drawn again (validity: the wanted
    key must hold). The key is drawn 50/50 and spaces cut the text into 2 + level//2 words at random. Answer yes/no."""
    alpha = "abcdefghijkl"
    half = "".join(r.choice(alpha) for _ in range(12 + level))
    pal = half + (r.choice(alpha) if r.random() < 0.5 else "") + half[::-1]
    if r.random() < 0.5:
        i, j = r.sample(range(len(pal)), 2)
        s = list(pal)
        s[i], s[j] = s[j], s[i]
        pal = "".join(s)
        if pal == pal[::-1]:
            raise Retry
    cuts = sorted(r.sample(range(1, len(pal)), 2 + level // 2))
    parts, last = [], 0
    for c in [*cuts, len(pal)]:
        parts.append(pal[last:c])
        last = c
    phrase = " ".join(parts)
    ans = "yes" if pal == pal[::-1] else "no"
    q = f"Ignoring the spaces, does the text '{phrase}' read the same forwards and backwards? Answer yes or no."
    return Built(q, {"phrase": phrase}, ans, "yn", 2)


# ---------------------------------------------------------------- stack_machine

_STACK_TEXT = {
    "add": "add the top two (replace them by their sum)",
    "mul": "multiply the top two (replace them by their product)",
    "sub": "subtract: second from top minus top (replace both by the result)",
    "dup": "duplicate the top",
    "pop": "discard the top",
    "swap": "swap the top two",
}


@fix3("stack", "R2.stack_machine")
def stack_machine(level: int, r: random.Random) -> Built:
    """Procedure: a stack machine. structured: {"prog": [[op, value?]]}. Fix round 3: 'the last pushed value' read 0.41-0.59 and was exact on every item whose last step is a push (31-45%). By construction the program is 5 + 2*level
    random steps (batch 1: 4 + 2*level; values 1..20, batch 1: 1..9) followed by a FINAL step that is always an arithmetic operation (add, multiply or subtract; if fewer than two numbers are on the stack a push comes first), so
    the last step is never a push. A subtraction never directly follows a duplication (dup then sub always gives 0, which made 0 the constant guess at 8-11%). Answer: the number on top of the stack at the end."""
    st: list[int] = []
    prog: list[list[Any]] = []
    hi = 20
    prev = ""
    for _ in range(5 + 2 * level):
        choices = ["push", "push"]
        if len(st) >= 1:
            choices += ["dup", "pop"] if len(st) >= 2 else ["dup"]
        if len(st) >= 2:
            choices += ["add", "mul", "swap"] + ([] if prev == "dup" else ["sub"])
        o = r.choice(choices)
        prev = o
        if o == "push":
            v = r.randint(1, hi)
            st.append(v)
            prog.append([o, v])
        elif o == "dup":
            st.append(st[-1])
            prog.append([o])
        elif o == "pop":
            st.pop()
            prog.append([o])
        elif o == "swap":
            st[-1], st[-2] = st[-2], st[-1]
            prog.append([o])
        else:
            b, a = st.pop(), st.pop()
            st.append({"add": a + b, "mul": a * b, "sub": a - b}[o])
            prog.append([o])
    while len(st) < 2:
        v = r.randint(1, hi)
        st.append(v)
        prog.append(["push", v])
        prev = "push"
    o = r.choice(("add", "mul") if prev == "dup" else ("add", "mul", "sub"))
    b, a = st.pop(), st.pop()
    st.append({"add": a + b, "mul": a * b, "sub": a - b}[o])
    prog.append([o])
    text = ", ".join(f"push {p[1]}" if p[0] == "push" else _STACK_TEXT[p[0]] for p in prog)
    q = f"A stack starts empty. Do these steps in order: {text}. What number is on top of the stack at the end?"
    return Built(q, {"prog": prog}, str(st[-1]), "number", None)


# ---------------------------------------------------------------- permutation_power


@fix3("permutation", "R2.permutation_power")
def permutation_power(level: int, r: random.Random) -> Built:
    """Procedure: apply a mapping t times (iterate a map). structured: {"img": [int], "s": int, "t": int}. Fix round 3: with a random mapping on 4 .. 10 numbers the start's cycle is short, so 'the start' (0.29-0.52), 'one
    application' (0.30-0.53) and 't mod n applications' (up to 0.83) were each right on about 1/(cycle length) of items. By construction the mapping on n = 12 + level numbers has ONE long cycle through n - a of the numbers
    (a drawn from 1..3 with a coprime to n, so the long cycle length n - a has no common factor with n and 't mod n' is not the reduction), the other a numbers are mapped among themselves at random, the numbers are labelled at random, and the start is a number of the long
    cycle; t is drawn from 30 .. 90 + 10*level. Each of those rules is then right on about 1/(n-a), under one in ten. Answer: the number reached after t applications."""
    n = 12 + level
    a = r.choice([x for x in (1, 2, 3) if math.gcd(x, n) == 1])
    labels = list(range(1, n + 1))
    r.shuffle(labels)
    big, small = labels[: n - a], labels[n - a :]
    img = [0] * (n + 1)
    for i, x in enumerate(big):
        img[x] = big[(i + 1) % len(big)]
    sm = small[:]
    r.shuffle(sm)
    for x, y in zip(small, sm, strict=True):
        img[x] = y
    s = r.choice(big)
    t = r.randint(30, 90 + 10 * level)
    cur = s
    for _ in range(t):
        cur = img[cur]
    mp = ", ".join(f"{i} goes to {img[i]}" for i in range(1, n + 1))
    q = f"A mapping on the numbers 1 to {n} sends: {mp}. Start at {s} and apply the mapping {t} times in a row. Which number do you end on?"
    return Built(q, {"img": img[1:], "s": s, "t": t}, str(cur), "number", None)


# ---------------------------------------------------------------- prime_factor_query (capacity at level 0)

_PR = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97)


@fix3("numtheory", "R2.prime_factor_query")
def prime_factor_query(level: int, r: random.Random) -> Built:
    """Procedure: trial-division factorisation. structured: {"n": int, "ask": "largest" | "sum_all"}. Same construction as rev2 (largest prime factor uniform over the primes 17 .. top of the pool, one prime used twice, the other factors
    uniform among the primes up to it; no gate), widened at level 0 only, for capacity under the reading in which a reserve level carries the core demand (R-10): rev2 had 4 factors from the primes up to 61 at level 0 (about 4,029 different
    items); now 5 factors from the primes up to 79 (the other levels are unchanged: 5 factors, primes up to 97, 6 at level 6).
    Answer: the largest prime factor, or the sum of the primes in the factorisation counting repeats."""
    k = (5, 5, 5, 5, 5, 5, 6)[level]
    pool = _PR[:22] if level == 0 else _PR
    big = r.choice([p for p in pool if p >= 17])
    below = [p for p in pool if p <= big]
    dup = r.choice(below)
    fs = sorted([big, dup, dup, *(r.choice(below) for _ in range(k - 3))])
    n = 1
    for f in fs:
        n *= f
    if r.random() < 0.5:
        return Built(f"What is the largest prime number that divides {n} exactly?", {"n": n, "ask": "largest"}, str(fs[-1]), "number", None)
    q = f"Write {n} as a product of prime numbers (for example, 12 is 2 x 2 x 3). Add up the primes in that product, counting a prime as many times as it appears. What is the sum?"
    return Built(q, {"n": n, "ask": "sum_all"}, str(sum(fs)), "number", None)
