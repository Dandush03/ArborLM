# ruff: noqa: E501
"""R2 fix round 3: every revised lineage's answer key checked against a SECOND SOLVER written here from the structured form only (not from the builders), plus determinism and JSON stability.
These are the implementer's self-checks: they are not an independent review (a solver from a separate context does not exist yet; ruling R-9)."""

from __future__ import annotations

import itertools
import json
import math
import random
import re
from collections import OrderedDict, deque
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import pytest

from studies.m0.core import ALL_LEVELS, build_item
from studies.m0.r2_fix3_set import fix3_set

FIX3_IDS = sorted(
    "R2." + n
    for n in (
        "interval_scheduling binary_search_trace bst_traversal min_heap_ops cellular_automaton dictionary_rank run_length hash_probe cache_eviction bracket_match "
        "expression_eval subtraction_game cheapest_network max_subarray_sum coin_change_min lcs_length gcd_euclid multiples_between count_letter count_divisible "
        "palindrome_check stack_machine permutation_power prime_factor_query"
    ).split()
)


def lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


# ---------------------------------------------------------------- second solvers (structured form -> answer string)
def s_interval(s: dict[str, Any]) -> str:
    iv = s["meetings"]
    chosen: list[int] = []
    left = set(range(len(iv)))
    while True:
        cand = [i for i in left if all(iv[i][1] <= iv[j][0] or iv[i][0] >= iv[j][1] for j in chosen)]
        if not cand:
            break
        i = min(cand, key=lambda i: (iv[i][1], i))
        chosen.append(i)
        left.discard(i)
    return lst(sorted(i + 1 for i in chosen))


def s_binary(s: dict[str, Any]) -> str:
    xs, t = s["xs"], s["target"]
    looks: list[int] = []

    def go(lo: int, hi: int) -> None:
        if lo > hi:
            return
        mid = (lo + hi) // 2
        looks.append(xs[mid - 1])
        if xs[mid - 1] == t:
            return
        go(lo, mid - 1) if t < xs[mid - 1] else go(mid + 1, hi)

    go(1, len(xs))
    return lst(looks) if s["ask"] == "values" else str(sum(looks))


class _Node:
    def __init__(self, v: int) -> None:
        self.v = v
        self.l: _Node | None = None
        self.r: _Node | None = None


def s_bst(s: dict[str, Any]) -> str:
    root = _Node(s["xs"][0])
    for x in s["xs"][1:]:
        n = root
        while True:
            side = "l" if x < n.v else "r"
            if getattr(n, side) is None:
                setattr(n, side, _Node(x))
                break
            n = getattr(n, side)
    out: list[int] = []
    if s["kind"] == "level":
        q = deque([root])
        while q:
            n = q.popleft()
            out.append(n.v)
            q.extend([c for c in (n.l, n.r) if c is not None])
    else:
        def walk(n: _Node | None) -> None:
            if n is None:
                return
            if s["kind"] == "pre":
                out.append(n.v)
            walk(n.l)
            walk(n.r)
            if s["kind"] == "post":
                out.append(n.v)

        walk(root)
    return lst(out)


def s_heap(s: dict[str, Any]) -> str:
    h = [0]  # 1-based

    def up(i: int) -> None:
        if i > 1 and h[i] < h[i // 2]:
            h[i], h[i // 2] = h[i // 2], h[i]
            up(i // 2)

    def down(i: int) -> None:
        kids = [c for c in (2 * i, 2 * i + 1) if c < len(h)]
        if not kids:
            return
        c = min(kids, key=lambda k: h[k])
        if h[c] < h[i]:
            h[c], h[i] = h[i], h[c]
            down(c)

    for x in s["xs"]:
        h.append(x)
        up(len(h) - 1)
    for _ in range(s["removals"]):
        h[1] = h[-1]
        h.pop()
        if len(h) > 1:
            down(1)
    return lst(h[1:])


def s_ca(s: dict[str, Any]) -> str:
    row = "".join(map(str, s["row"]))
    for _ in range(s["steps"]):
        pad = "0" + row + "0"
        row = "".join(str(s["table"][pad[i : i + 3]]) for i in range(len(row)))
    return row


def s_dictrank(s: dict[str, Any]) -> str:
    letters, ln = sorted(s["letters"]), s["length"]
    perms = itertools.permutations(letters, ln)
    if s["ask"] == "word":
        return "".join(next(itertools.islice(perms, s["k"] - 1, s["k"])))
    w = tuple(s["word"])
    # count words before w by walking the sorted word list only as far as needed
    for i, p in enumerate(perms, 1):
        if p == w:
            return str(i)
    raise AssertionError("word not found")


def s_rle(s: dict[str, Any]) -> str:
    return "".join(f"{k}{len(list(g))}" for k, g in itertools.groupby(s["s"]))


def s_hash(s: dict[str, Any]) -> str:
    m = s["m"]
    slots: dict[int, int] = {}
    for k in s["keys"]:
        i = k % m
        while i in slots:
            i = (i + 1) % m
        slots[i] = k
    if s["ask"] == "table":
        return ", ".join(str(slots[i]) if i in slots else "-" for i in range(m))
    return str(sum(slots))


def s_cache(s: dict[str, Any]) -> str:
    c: OrderedDict[str, None] = OrderedDict()
    ev: list[str] = []
    for x in s["seq"]:
        if x in c:
            if s["policy"] == "lru":
                c.move_to_end(x)
            continue
        if len(c) >= s["cap"]:
            ev.append(c.popitem(last=False)[0])
        c[x] = None
    return ", ".join(ev) if s["ask"] == "evicted" else ", ".join(c)


def s_brackets(s: dict[str, Any]) -> str:
    t = s["s"]
    stack: list[int] = []
    mate: dict[int, int] = {}
    first_bad = None
    for i, ch in enumerate(t):
        if ch in "([{":
            stack.append(i)
        else:
            j = stack.pop()
            mate[j] = i
            if first_bad is None and {")": "(", "]": "[", "}": "{"}[ch] != t[j]:
                first_bad = i + 1
    if s["ask"] == "first_error":
        assert first_bad is not None
        return str(first_bad)
    return lst([mate[j] + 1 for j in sorted(mate) if t[j] == s["kind"]])


def s_expr(s: dict[str, Any]) -> str:
    toks: list[str] = re.findall(r"\d+|[()+*-]", s["text"])
    pos = [0]

    def peek() -> str | None:
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take() -> str:
        pos[0] += 1
        return toks[pos[0] - 1]

    def atom() -> int:
        t = take()
        if t == "(":
            v = expr()
            take()
            return v
        return int(t)

    if s["convention"] == "ranked":
        def term() -> int:
            v = atom()
            while peek() == "*":
                take()
                v *= atom()
            return v

        def expr() -> int:
            v = term()
            while peek() in ("+", "-"):
                v = v + term() if take() == "+" else v - term()
            return v
    else:
        def expr() -> int:
            v = atom()
            while peek() in ("+", "-", "*"):
                op = take()
                w = atom()
                v = v + w if op == "+" else v - w if op == "-" else v * w
            return v

    return str(int(expr()))


def s_subtraction(s: dict[str, Any]) -> str:
    moves = s["moves"]

    @lru_cache(None)
    def g(n: int) -> int:
        reach = sorted({g(n - m) for m in moves if m <= n})
        v = 0
        for x in reach:
            if x == v:
                v += 1
            elif x > v:
                break
        return v

    x = 0
    for p in s["piles"]:
        x ^= g(p)
    return "yes" if x else "no"


def s_mst(s: dict[str, Any]) -> str:
    towns = s["towns"]
    adj: dict[str, list[tuple[int, str]]] = {t: [] for t in towns}
    for a, b, w in s["cables"]:
        adj[a].append((w, b))
        adj[b].append((w, a))
    seen = {towns[0]}
    total = 0
    while len(seen) < len(towns):
        w, b = min((w, b) for a in seen for w, b in adj[a] if b not in seen)
        total += w
        seen.add(b)
    return str(total)


def s_maxsub(s: dict[str, Any]) -> str:
    xs = s["xs"]
    return str(max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1)))


def s_coin(s: dict[str, Any]) -> str:
    out = []
    for a in s["amounts"]:
        seen = {0}
        frontier = [0]
        d = 0
        while a not in seen:
            d += 1
            frontier = [v + c for v in frontier for c in s["coins"] if v + c <= a and v + c not in seen]
            seen.update(frontier)
            assert frontier, "amount not payable"
        out.append(d)
    return lst(out)


def s_lcs(s: dict[str, Any]) -> str:
    a, b = s["a"], s["b"]

    @lru_cache(None)
    def f(i: int, j: int) -> int:
        if i == len(a) or j == len(b):
            return 0
        return f(i + 1, j + 1) + 1 if a[i] == b[j] else max(f(i + 1, j), f(i, j + 1))

    return str(f(0, 0))


def s_gcd(s: dict[str, Any]) -> str:
    return str(math.gcd(s["a"], s["b"])) if s["ask"] == "gcd" else str(math.lcm(s["a"], s["b"]))


def s_multiples(s: dict[str, Any]) -> str:
    ms = [x for x in range(s["a"], s["b"] + 1) if x % s["m"] == 0]
    return str(len(ms)) if s["ask"] == "count" else str(sum(ms))


def s_count_letter(s: dict[str, Any]) -> str:
    return str(sum(1 for w in s["words"] for c in w if c == s["letter"]))


def s_count_div(s: dict[str, Any]) -> str:
    return str(sum(x for x in s["xs"] if x % s["m"] == 0 and x > s["t"]))


def s_pal(s: dict[str, Any]) -> str:
    t = s["phrase"].replace(" ", "")
    return "yes" if t == "".join(reversed(t)) else "no"


def s_stack(s: dict[str, Any]) -> str:
    st: list[int] = []
    for p in s["prog"]:
        o = p[0]
        if o == "push":
            st.append(p[1])
        elif o == "dup":
            st.append(st[-1])
        elif o == "pop":
            st.pop()
        elif o == "swap":
            st[-1], st[-2] = st[-2], st[-1]
        else:
            top, second = st.pop(), st.pop()
            st.append({"add": second + top, "mul": second * top, "sub": second - top}[o])
    return str(st[-1])


def s_perm(s: dict[str, Any]) -> str:
    x = s["s"]
    for _ in range(s["t"]):
        x = s["img"][x - 1]
    return str(x)


def s_prime(s: dict[str, Any]) -> str:
    n, fs, d = s["n"], [], 2
    while n > 1:
        while n % d == 0:
            fs.append(d)
            n //= d
        d += 1
    return str(max(fs)) if s["ask"] == "largest" else str(sum(fs))


SOLVERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "interval_scheduling": s_interval, "binary_search_trace": s_binary, "bst_traversal": s_bst, "min_heap_ops": s_heap, "cellular_automaton": s_ca,
    "dictionary_rank": s_dictrank, "run_length": s_rle, "hash_probe": s_hash, "cache_eviction": s_cache, "bracket_match": s_brackets, "expression_eval": s_expr,
    "subtraction_game": s_subtraction, "cheapest_network": s_mst, "max_subarray_sum": s_maxsub, "coin_change_min": s_coin, "lcs_length": s_lcs, "gcd_euclid": s_gcd,
    "multiples_between": s_multiples, "count_letter": s_count_letter, "count_divisible": s_count_div, "palindrome_check": s_pal, "stack_machine": s_stack,
    "permutation_power": s_perm, "prime_factor_query": s_prime,
}


def test_every_revised_lineage_has_a_solver_and_is_in_the_set() -> None:
    assert sorted("R2." + n for n in SOLVERS) == FIX3_IDS
    assert set(FIX3_IDS) <= set(fix3_set())


@pytest.mark.parametrize("lid", FIX3_IDS)
def test_keys_match_second_solver(lid: str) -> None:
    lin = fix3_set()[lid]
    sol = SOLVERS[lid.split(".", 1)[1]]
    # the brute-force ranking solver is slow at the top levels; fewer items there
    per = 12 if lid.endswith("dictionary_rank") else 60
    for lv in ALL_LEVELS:
        r = random.Random(f"fix3-keys|{lid}|{lv}")
        for i in range(per):
            it = build_item(lin, lv, r, "A", f"{lid}/{lv}/{i}")
            assert sol(it.structured) == it.answer, (lid, lv, it.structured)


@pytest.mark.parametrize("lid", FIX3_IDS)
def test_deterministic_and_json_stable_and_no_key_in_structured(lid: str) -> None:
    lin = fix3_set()[lid]
    for lv in (0, 3, 6):
        a = [build_item(lin, lv, random.Random(f"fix3-det|{lid}|{lv}"), "A", "x") for _ in range(1)]
        b = [build_item(lin, lv, random.Random(f"fix3-det|{lid}|{lv}"), "A", "x") for _ in range(1)]
        assert a == b
        it = a[0]
        assert json.loads(json.dumps(it.structured)) == it.structured
        assert "answer" not in it.structured and "key" not in it.structured
        assert it.answer != ""
