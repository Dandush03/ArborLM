# ruff: noqa: E501
"""This round's own cheap rules for the revised shapes (the auditor's battery, ``a3_heur.py``, is applied as well). Each returns an answer string, or None when it does not apply.
A rule's name starting with (P) marks a valid alternative procedure or a full solve under a misreading (reported, not counted as a cue)."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

Heur = Callable[[dict[str, Any], str], str | None]
OWN: dict[str, list[tuple[str, Heur]]] = {}


def own(lineage: str, name: str) -> Callable[[Heur], Heur]:
    def deco(fn: Heur) -> Heur:
        OWN.setdefault(lineage, []).append((name, fn))
        return fn

    return deco


def _lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


# ---------------------------------------------------------------- binary_search_trace (shapes values | sum)
def _probes(xs: list[int], t: int, up: bool = False) -> list[int]:
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi + (1 if up else 0)) // 2
        seen.append(xs[mid - 1])
        if xs[mid - 1] == t:
            break
        if t < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return seen


@own("binary_search_trace", "sum: midpoint rounded UP")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(_probes(s["xs"], s["target"], True))) if s["ask"] == "sum" else None


@own("binary_search_trace", "sum: first look + target")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(s["xs"][(1 + len(s["xs"])) // 2 - 1] + s["target"]) if s["ask"] == "sum" else None


@own("binary_search_trace", "sum: log2(n)+1 looks, each the target")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(s["target"] * (int(math.log2(len(s["xs"]))) + 1)) if s["ask"] == "sum" else None


@own("binary_search_trace", "values: the target alone if present, else the nearest value")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "values":
        return None
    return str(min(s["xs"], key=lambda x: (abs(x - s["target"]), x)))


@own("binary_search_trace", "values: list ends with the target if present (prefix only: first look)")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(s["xs"][(1 + len(s["xs"])) // 2 - 1]) if s["ask"] == "values" else None


@own("binary_search_trace", "values: (P) same search with the target ignored once found (does not stop)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "values":
        return None
    xs, t = s["xs"], s["target"]
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi) // 2
        seen.append(xs[mid - 1])
        if t <= xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return _lst(seen)


# ---------------------------------------------------------------- dictionary_rank (words of `length` letters from the alphabet)
def _fall(a: int, b: int) -> int:
    return math.perm(a, b) if 0 <= b <= a else 0


@own("dictionary_rank", "position: index in the FULL sorted alphabet (no removal of used letters)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "position":
        return None
    pool, m, ln = sorted(s["letters"]), len(s["letters"]), s["length"]
    return str(1 + sum(pool.index(c) * _fall(m - 1 - i, ln - 1 - i) for i, c in enumerate(s["word"])))


@own("dictionary_rank", "position: off by one (0-based)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "position":
        return None
    pool, m, ln = sorted(s["letters"]), len(s["letters"]), s["length"]
    k = 0
    p = list(pool)
    for i, c in enumerate(s["word"]):
        j = p.index(c)
        k += j * _fall(m - 1 - i, ln - 1 - i)
        p.pop(j)
    return str(k)


@own("dictionary_rank", "position: weights as for arrangements of all the letters (m-1-i)!")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "position":
        return None
    p, m = sorted(s["letters"]), len(s["letters"])
    k = 0
    for i, c in enumerate(s["word"]):
        j = p.index(c)
        k += j * math.factorial(m - 1 - i)
        p.pop(j)
    return str(k + 1)


@own("dictionary_rank", "word: the k-th word of the letters in plain sorted order")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "word":
        return None
    return "".join(sorted(s["letters"])[: s["length"]])


@own("dictionary_rank", "word: first letters ascending (position index in k's base-m digits)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "word":
        return None
    m, ln, k = len(s["letters"]), s["length"], s["k"] - 1
    digs = []
    for _ in range(ln):
        digs.append(k % m)
        k //= m
    return "".join(s["letters"][d] for d in digs[::-1])


# ---------------------------------------------------------------- cellular_automaton (row only)
@own("cellular_automaton", "the start row")
def _(s: dict[str, Any], q: str) -> str | None:
    return "".join(map(str, s["row"]))


@own("cellular_automaton", "all zeros")
def _(s: dict[str, Any], q: str) -> str | None:
    return "0" * len(s["row"])


@own("cellular_automaton", "one step fewer")
def _(s: dict[str, Any], q: str) -> str | None:
    row = list(s["row"])
    for _ in range(max(0, s["steps"] - 1)):
        n = len(row)
        row = [s["table"][f"{row[i - 1] if i else 0}{row[i]}{row[i + 1] if i < n - 1 else 0}"] for i in range(n)]
    return "".join(map(str, row))


@own("cellular_automaton", "one step more")
def _(s: dict[str, Any], q: str) -> str | None:
    row = list(s["row"])
    for _ in range(s["steps"] + 1):
        n = len(row)
        row = [s["table"][f"{row[i - 1] if i else 0}{row[i]}{row[i + 1] if i < n - 1 else 0}"] for i in range(n)]
    return "".join(map(str, row))


# ---------------------------------------------------------------- interval_scheduling (ask = chosen: the list of numbers chosen by the stated rule)
def _greedy_list(iv: list[list[int]], key: Callable[[int], Any], touching_clashes: bool = False) -> str:
    taken: list[int] = []
    for i in sorted(range(len(iv)), key=key):
        a, b = iv[i]
        ok = all((b < iv[j][0] or a > iv[j][1]) if touching_clashes else (b <= iv[j][0] or a >= iv[j][1]) for j in taken)
        if ok:
            taken.append(i)
    return _lst(sorted(i + 1 for i in taken))


@own("interval_scheduling", "earliest start first")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (iv[i][0], iv[i][1], i))


@own("interval_scheduling", "shortest first")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (iv[i][1] - iv[i][0], iv[i][0], i))


@own("interval_scheduling", "longest first")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (-(iv[i][1] - iv[i][0]), iv[i][0], i))


@own("interval_scheduling", "(P) latest start first (the mirror greedy: a valid optimal strategy; its list can differ)")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (-iv[i][0], -iv[i][1], i))


@own("interval_scheduling", "(P) earliest finish, ties to the LARGER number (the stated rule with a misread tie or touching rule: a full solve)")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (iv[i][1], -i))


@own("interval_scheduling", "(P) earliest finish, touching counts as a clash (the stated rule with a misread tie or touching rule: a full solve)")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (iv[i][1], i), True)


@own("interval_scheduling", "numbers in the written order (first come first chosen)")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: i)


@own("interval_scheduling", "(P) earliest finish, ties by earliest start (the stated rule with a misread tie or touching rule: a full solve)")
def _(s: dict[str, Any], q: str) -> str | None:
    iv = s["meetings"]
    return _greedy_list(iv, lambda i: (iv[i][1], iv[i][0], i))


# ---------------------------------------------------------------- hash_probe (ask = table | checksum)
def _place_all(keys: list[int], m: int, step: int = 1, home_only: bool = False) -> list[int | None]:
    tab: list[int | None] = [None] * m
    for k in keys:
        s = k % m
        if home_only:
            tab[s] = k
            continue
        for _ in range(m):
            if tab[s] is None:
                break
            s = (s + step) % m
        tab[s] = k
    return tab


def _tab_str(tab: list[int | None]) -> str:
    return ", ".join("-" if x is None else str(x) for x in tab)


@own("hash_probe", "table: every number at its home slot (a later one overwrites)")
def _(s: dict[str, Any], q: str) -> str | None:
    return _tab_str(_place_all(s["keys"], s["m"], home_only=True)) if s["ask"] == "table" else None


@own("hash_probe", "table: (P) probing downward (the previous slot) instead of upward")
def _(s: dict[str, Any], q: str) -> str | None:
    return _tab_str(_place_all(s["keys"], s["m"], step=-1)) if s["ask"] == "table" else None


@own("hash_probe", "table: (P) numbers added in reverse order")
def _(s: dict[str, Any], q: str) -> str | None:
    return _tab_str(_place_all(s["keys"][::-1], s["m"])) if s["ask"] == "table" else None


@own("hash_probe", "table: (P) no wrap-around (a number that runs off the end is dropped)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "table":
        return None
    tab: list[int | None] = [None] * s["m"]
    for k in s["keys"]:
        i = k % s["m"]
        while i < s["m"] and tab[i] is not None:
            i += 1
        if i < s["m"]:
            tab[i] = k
    return _tab_str(tab)


@own("hash_probe", "checksum: sum of the home slots (every number at home, collisions ignored: distinct homes only)")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum({k % s["m"] for k in s["keys"]})) if s["ask"] == "checksum" else None


@own("hash_probe", "checksum: sum of the home slots of all numbers")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(k % s["m"] for k in s["keys"])) if s["ask"] == "checksum" else None


@own("hash_probe", "checksum: (P) probing downward")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "checksum":
        return None
    tab = _place_all(s["keys"], s["m"], step=-1)
    return str(sum(i for i, x in enumerate(tab) if x is not None))


@own("hash_probe", "checksum: all slots 0..n-1 filled from the lowest home")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "checksum":
        return None
    h = min(k % s["m"] for k in s["keys"])
    return str(sum((h + i) % s["m"] for i in range(len(s["keys"]))))


# ---------------------------------------------------------------- cache_eviction (ask = evicted | contents)
def _csim(seq: list[str], cap: int, policy: str) -> tuple[list[str], list[str]]:
    cache: list[str] = []
    ev: list[str] = []
    for x in seq:
        if x in cache:
            if policy == "lru":
                cache.remove(x)
                cache.append(x)
            continue
        if len(cache) == cap:
            ev.append(cache.pop(0))
        cache.append(x)
    return ev, cache


@own("cache_eviction", "evicted: (P) the other policy's evicted list")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "evicted":
        return None
    return ", ".join(_csim(s["seq"], s["cap"], "fifo" if s["policy"] == "lru" else "lru")[0])


@own("cache_eviction", "evicted: distinct items in order of first request, after the first cap of them")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "evicted":
        return None
    seen: list[str] = []
    for x in s["seq"]:
        if x not in seen:
            seen.append(x)
    return ", ".join(seen[: max(0, len(seen) - s["cap"])])


@own("cache_eviction", "evicted: the items requested once only")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "evicted":
        return None
    return ", ".join(x for x in dict.fromkeys(s["seq"]) if s["seq"].count(x) == 1)


@own("cache_eviction", "contents: the last cap distinct requests, oldest first (the LRU contents)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "contents":
        return None
    seen: list[str] = []
    for x in reversed(s["seq"]):
        if x not in seen:
            seen.append(x)
    return ", ".join(reversed(seen[: s["cap"]]))


@own("cache_eviction", "contents: (P) the LRU contents with the order of loading")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "contents":
        return None
    return ", ".join(_csim(s["seq"], s["cap"], "lru")[1])


@own("cache_eviction", "contents: the last cap requests as written")
def _(s: dict[str, Any], q: str) -> str | None:
    return ", ".join(s["seq"][-s["cap"]:]) if s["ask"] == "contents" else None


# ---------------------------------------------------------------- bracket_match (ask = match_all | first_error)
_MATE = {")": "(", "]": "[", "}": "{"}


@own("bracket_match", "match_all: the k-th closer of the kind pairs with the k-th opener of the kind (queue instead of stack)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    cl = {"(": ")", "[": "]", "{": "}"}[k]
    ops = [i for i, c in enumerate(t) if c == k]
    cls = [i for i, c in enumerate(t) if c == cl]
    return ", ".join(str(c + 1) for c in cls) if len(ops) == len(cls) else None


@own("bracket_match", "match_all: the next closer of the kind after each opener")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    cl = {"(": ")", "[": "]", "{": "}"}[k]
    out = []
    for i, c in enumerate(t):
        if c == k:
            out.append(str(t.index(cl, i + 1) + 1))
    return ", ".join(out)


@own("bracket_match", "match_all: the last closer of the kind for the first opener, then working inwards")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    cl = {"(": ")", "[": "]", "{": "}"}[k]
    cls = [i for i, c in enumerate(t) if c == cl]
    return ", ".join(str(c + 1) for c in reversed(cls))


@own("bracket_match", "first_error: first closer whose kind differs from the opener just before it (adjacent check)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    for i in range(1, len(t)):
        if t[i] in _MATE and t[i - 1] in "([{" and _MATE[t[i]] != t[i - 1]:
            return str(i + 1)
    return None


@own("bracket_match", "first_error: first closer after which the count of its kind exceeds the openers of its kind")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "first_error":
        return None
    bal = {"(": 0, "[": 0, "{": 0}
    for i, c in enumerate(s["s"]):
        if c in bal:
            bal[c] += 1
        else:
            bal[_MATE[c]] -= 1
            if bal[_MATE[c]] < 0:
                return str(i + 1)
    return None


@own("bracket_match", "first_error: first top-level closer that does not match its opener (only depth-1 pairs checked)")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "first_error":
        return None
    st: list[str] = []
    for i, c in enumerate(s["s"]):
        if c in "([{":
            st.append(c)
        else:
            o = st.pop()
            if not st and o != _MATE[c]:
                return str(i + 1)
    return None


@own("bracket_match", "first_error: position of the first closer of the kind with the fewest closers")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    from collections import Counter

    cnt = Counter(c for c in t if c in _MATE)
    k = min(cnt, key=lambda c: (cnt[c], c))
    return str(t.index(k) + 1)


@own("bracket_match", "first_error: the position after the first adjacent closer pair of different kinds")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    for i in range(1, len(t)):
        if t[i] in _MATE and t[i - 1] in _MATE and t[i] != t[i - 1]:
            return str(i + 1)
    return None


# ---------------------------------------------------------------- subtraction_game (n piles)
def _gt(n: int, moves: list[int]) -> list[int]:
    g = [0] * (n + 1)
    for x in range(1, n + 1):
        st = {g[x - m] for m in moves if m <= x}
        v = 0
        while v in st:
            v += 1
        g[x] = v
    return g


@own("subtraction_game", "count of piles that are a win alone is odd -> yes")
def _(s: dict[str, Any], q: str) -> str | None:
    g = _gt(max(s["piles"]), s["moves"])
    return "yes" if sum(1 for p in s["piles"] if g[p]) % 2 else "no"


@own("subtraction_game", "some pile is a win alone -> yes")
def _(s: dict[str, Any], q: str) -> str | None:
    g = _gt(max(s["piles"]), s["moves"])
    return "yes" if any(g[p] for p in s["piles"]) else "no"


@own("subtraction_game", "all piles are a win alone -> no, else yes")
def _(s: dict[str, Any], q: str) -> str | None:
    g = _gt(max(s["piles"]), s["moves"])
    return "no" if all(g[p] for p in s["piles"]) else "yes"


@own("subtraction_game", "plain Nim: xor of the pile sizes")
def _(s: dict[str, Any], q: str) -> str | None:
    v = 0
    for p in s["piles"]:
        v ^= p
    return "yes" if v else "no"


@own("subtraction_game", "xor of (pile mod (max move + 1))")
def _(s: dict[str, Any], q: str) -> str | None:
    k = max(s["moves"]) + 1
    v = 0
    for p in s["piles"]:
        v ^= p % k
    return "yes" if v else "no"


@own("subtraction_game", "(P) one pile of the total: position value nonzero")
def _(s: dict[str, Any], q: str) -> str | None:
    g = _gt(sum(s["piles"]), s["moves"])
    return "yes" if g[sum(s["piles"])] else "no"


@own("subtraction_game", "(P) parity of the sum of the position values (the lowest bit of the xor)")
def _(s: dict[str, Any], q: str) -> str | None:
    g = _gt(max(s["piles"]), s["moves"])
    return "yes" if sum(g[p] for p in s["piles"]) % 2 else "no"


@own("subtraction_game", "total number of stones odd -> yes")
def _(s: dict[str, Any], q: str) -> str | None:
    return "yes" if sum(s["piles"]) % 2 else "no"


# ---------------------------------------------------------------- coin_change_min (ask = fewest: a list over four amounts)
def _gr(coins: list[int], a: int) -> int:
    n = 0
    for c in sorted(coins, reverse=True):
        n += a // c
        a %= c
    return n


@own("coin_change_min", "largest-first greedy for each amount (leftover ignored)")
def _(s: dict[str, Any], q: str) -> str | None:
    return _lst([_gr(s["coins"], a) for a in s["amounts"]])


@own("coin_change_min", "ceil(amount / largest coin) for each amount")
def _(s: dict[str, Any], q: str) -> str | None:
    return _lst([-(-a // max(s["coins"])) for a in s["amounts"]])


@own("coin_change_min", "ceil(amount / largest coin) + 1 for each amount")
def _(s: dict[str, Any], q: str) -> str | None:
    return _lst([-(-a // max(s["coins"])) + 1 for a in s["amounts"]])


@own("coin_change_min", "amount // largest + (amount mod largest) // second + remainder by the smallest")
def _(s: dict[str, Any], q: str) -> str | None:
    cs = sorted(s["coins"])
    out = []
    for a in s["amounts"]:
        n, a2 = a // cs[-1], a % cs[-1]
        n += a2 // cs[0]
        out.append(n)
    return _lst(out)


@own("coin_change_min", "amount // smallest coin for each amount")
def _(s: dict[str, Any], q: str) -> str | None:
    return _lst([a // min(s["coins"]) for a in s["amounts"]])


# ---------------------------------------------------------------- count_divisible (ask = count | sum), multiples_between (ask = sum)
@own("count_divisible", "sum shape: sum ignoring 'greater than t'")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(x for x in s["xs"] if x % s["m"] == 0)) if s["ask"] == "sum" else None


@own("count_divisible", "sum shape: '>= t' instead of '> t'")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(x for x in s["xs"] if x % s["m"] == 0 and x >= s["t"])) if s["ask"] == "sum" else None


@own("count_divisible", "sum shape: sum of all numbers greater than t")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(x for x in s["xs"] if x > s["t"])) if s["ask"] == "sum" else None


@own("count_divisible", "count shape: count of multiples of m (any size)")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(1 for x in s["xs"] if x % s["m"] == 0)) if s["ask"] == "count" else None


@own("count_divisible", "count shape: half of the numbers greater than t")
def _(s: dict[str, Any], q: str) -> str | None:
    return str(sum(1 for x in s["xs"] if x > s["t"]) // s["m"]) if s["ask"] == "count" else None


@own("multiples_between", "sum of the first k multiples from m (k = count)")
def _(s: dict[str, Any], q: str) -> str | None:
    a, b, m = s["a"], s["b"], s["m"]
    k = b // m - (a - 1) // m
    return str(m * k * (k + 1) // 2) if s["ask"] == "sum" else None


@own("multiples_between", "count: (P) (b-a)/m + 1, the counting rule itself")
def _(s: dict[str, Any], q: str) -> str | None:
    return str((s["b"] - s["a"]) // s["m"] + 1) if s["ask"] == "count" else None


@own("multiples_between", "count: (b-a)/m (the fencepost slip)")
def _(s: dict[str, Any], q: str) -> str | None:
    return str((s["b"] - s["a"]) // s["m"]) if s["ask"] == "count" else None


@own("multiples_between", "sum: (P) arithmetic series, the rule itself")
def _(s: dict[str, Any], q: str) -> str | None:
    if s["ask"] != "sum":
        return None
    a, b, m = s["a"], s["b"], s["m"]
    k1, k2 = -(-a // m), b // m
    return str(m * (k1 + k2) * (k2 - k1 + 1) // 2)


@own("multiples_between", "count x average of the ends (b//m - a//m multiples at (a+b)/2)")
def _(s: dict[str, Any], q: str) -> str | None:
    a, b, m = s["a"], s["b"], s["m"]
    return str(round((b // m - a // m) * (a + b) / 2)) if s["ask"] == "sum" else None


@own("multiples_between", "sum: (P) first multiple at or below a (a valid computation when a is a multiple)")
def _(s: dict[str, Any], q: str) -> str | None:
    a, b, m = s["a"], s["b"], s["m"]
    return str(sum(x for x in range(a - a % m, b + 1, m))) if s["ask"] == "sum" else None


@own("multiples_between", "sum with the last multiple below b only (exclusive end)")
def _(s: dict[str, Any], q: str) -> str | None:
    a, b, m = s["a"], s["b"], s["m"]
    return str(sum(x for x in range(a, b) if x % m == 0)) if s["ask"] == "sum" else None


# ---------------------------------------------------------------- max_subarray_sum: windows of every length
for _k in (3, 4, 5, 6, 8, 9, 10, 11, 12):
    def _mk(k: int) -> Heur:
        def f(s: dict[str, Any], q: str) -> str | None:
            xs = s["xs"]
            return str(max(sum(xs[i : i + k]) for i in range(len(xs) - k + 1))) if len(xs) >= k else None

        return f

    OWN.setdefault("max_subarray_sum", []).append((f"best window of exactly {_k} neighbouring numbers", _mk(_k)))


@own("max_subarray_sum", "best prefix")
def _(s: dict[str, Any], q: str) -> str | None:
    xs, best, cur = s["xs"], -10**9, 0
    for x in xs:
        cur += x
        best = max(best, cur)
    return str(best)


@own("max_subarray_sum", "best suffix")
def _(s: dict[str, Any], q: str) -> str | None:
    xs, best, cur = s["xs"], -10**9, 0
    for x in reversed(xs):
        cur += x
        best = max(best, cur)
    return str(best)


@own("max_subarray_sum", "from the first positive number to the last positive number")
def _(s: dict[str, Any], q: str) -> str | None:
    xs = s["xs"]
    pos = [i for i, x in enumerate(xs) if x > 0]
    return str(sum(xs[pos[0] : pos[-1] + 1])) if pos else None


@own("max_subarray_sum", "best sum of positive numbers and dips of at most 3 in one stretch (dips over 3 end the stretch)")
def _(s: dict[str, Any], q: str) -> str | None:
    best = cur = 0
    for x in s["xs"]:
        if x < -3:
            cur = 0
        else:
            cur = max(0, cur + x)
        best = max(best, cur)
    return str(best)
