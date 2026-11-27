# ruff: noqa: E501
# The program trees are plain nested lists (the grammar of c1grammar), as in every other C1 lineage module; hence no type parameters on list.
# mypy: disable-error-code="type-arg"
"""C1 fix round 3, list procedures. See ``lineages_c1_fix3`` for the rules. Superseded: partition_pass, merge_two_sorted_r2, sieve_marking_r2, binary_search,
majority_vote_scan_r2, counter_list, list_build, nested_pairs, coin_change_table (widened only)."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import AND, IDX, LIST, B, C, N, S, V, finish, names
from studies.m0.lineages_c1_fix3 import f3


def _call(fn: str, *args: list) -> list:
    return ["call", fn, *args]


@f3("swaps", supersedes="C1.partition_pass")
def partition_pass_f3(level: int, r: random.Random) -> Built:
    """Lomuto partition around the last of the first m entries (the pivot): i = -1; for j before the pivot, when xs[j] <= pivot (or < pivot, stated) do i += 1 and swap
    xs[i] with xs[j]. The list is built BY CONSTRUCTION (no redraw) from a fixed pattern of 'big' (above the pivot) and 'small' (below it) entries: positions 0, 1 and 3 and every position
    from 4 to m - 2 that is not one of two drawn positions are big; position 2 and two drawn positions in 4 .. m - 3 are small. So the first swap moves xs[0] to position 2, the
    third swap displaces that same value again (the displaced values are NOT the first entries), the larger values leave in a rotated order (the stable partition is not the answer),
    and the last big entry is never displaced (the sum of the larger values is not the answer). xs[0], xs[1] and xs[3] are three different values. Shapes: the list after the sweep and the
    final pivot swap; the sum of the values xs[i] that each swap moves out of position i; the list after the sweep, before the pivot is placed. The old swap-position sum (a closed form:
    the audit) is gone. Two earlier drafts (5 + level entries, then three leading bigs with three smalls after them) were answered by the stable partition in 0.14-0.71 and 0.07-0.32 of
    the items because Lomuto restores the input order when there are as many smalls as leading bigs. 9 + level entries, m from 9 to the whole list."""
    xs, i, j, t, pv, tot = names(r, 6)
    n = 9 + level
    m = n if r.random() < 0.5 else r.randint(9, n)
    pivot = r.randint(4, 3 * n)
    vals = [r.randint(1, 3 * n) for _ in range(n)]
    vals[m - 1] = pivot
    small = {2, *r.sample(range(4, m - 2), 2)}
    lead = r.sample(range(pivot + 1, pivot + 12), 3)
    for pos in range(m - 1):
        vals[pos] = r.randint(1, pivot - 1) if pos in small else pivot + r.randint(1, 11)
    vals[0], vals[1], vals[3] = lead
    cmp_op = r.choice(("<=", "<"))
    shape = r.choice(("list", "disp", "mid"))
    swap = [["set", t, IDX(V(xs), V(i))], ["setidx", xs, V(i), IDX(V(xs), V(j))], ["setidx", xs, V(j), V(t)]]
    body_if: list[list] = [["aug", i, "+", N(1)]]
    if shape == "disp":
        body_if.append(["aug", tot, "+", IDX(V(xs), V(i))])
    body_if += swap
    prog: list[list] = [["set", xs, LIST(vals)], ["set", pv, IDX(V(xs), N(m - 1))], ["set", i, N(-1)]]
    if shape == "disp":
        prog.append(["set", tot, N(0)])
    prog.append(["for", j, N(0), N(m - 1), 1, [["if", C(cmp_op, IDX(V(xs), V(j)), V(pv)), body_if, []]]])
    if shape == "list":
        prog += [["set", t, IDX(V(xs), B("+", V(i), N(1)))], ["setidx", xs, B("+", V(i), N(1)), V(pv)], ["setidx", xs, N(m - 1), V(t)]]
    prog.append(["print", V(tot) if shape == "disp" else V(xs)])
    return finish(prog)


@f3("lists", supersedes="C1.merge_two_sorted_r2")
def merge_two_sorted_f3(level: int, r: random.Random) -> Built:
    """The comparison loop of merging two sorted lists (while both have a next element, move the smaller to the output; the left one on equal or, as stated, on 'strictly
    less' the right one; values repeat across the lists). The old shape (the number of times the source list changed: ten distinct answers, the most frequent 0.21-0.32 of
    items) is replaced by quantities summed over the comparisons that depend on where BOTH pointers are at each comparison: ``diffsum`` (sum of a[i] - b[j]) and ``maxsum`` (sum of
    the larger of a[i] and b[j]). A first draft of this module had a checksum over the values taken; it is a function of the sorted merge truncated at the list that runs out
    first (the battery rule S.chk_sorted_truncated scored 1.00), so it was dropped and is not in this file."""
    a, b, i, j, out, tot = names(r, 6)
    na, nb = r.randint(3 + level // 2, 4 + level), r.randint(3 + level // 2, 4 + level)
    hi = max(na, nb) + 3 + level
    la, lb = sorted(r.randint(1, hi) for _ in range(na)), sorted(r.randint(1, hi) for _ in range(nb))
    cmp_op = r.choice(("<=", "<"))
    shape = r.choice(("diffsum", "maxsum"))
    take_a: list[list] = [["append", out, IDX(V(a), V(i))], ["aug", i, "+", N(1)]]
    take_b: list[list] = [["append", out, IDX(V(b), V(j))], ["aug", j, "+", N(1)]]
    term = B("-", IDX(V(a), V(i)), IDX(V(b), V(j))) if shape == "diffsum" else _call("max", IDX(V(a), V(i)), IDX(V(b), V(j)))
    loop_body: list[list] = [["aug", tot, "+", term], ["if", C(cmp_op, IDX(V(a), V(i)), IDX(V(b), V(j))), take_a, take_b]]
    prog: list[list] = [["set", a, LIST(la)], ["set", b, LIST(lb)], ["set", i, N(0)], ["set", j, N(0)], ["set", out, ["list"]], ["set", tot, N(0)]]
    prog += [["while", AND(C("<", V(i), _call("len", V(a))), C("<", V(j), _call("len", V(b)))), loop_body], ["print", V(tot)]]
    return finish(prog)


@f3("lists", supersedes="C1.sieve_marking_r2")
def sieve_marking_f3(level: int, r: random.Random) -> Built:
    """Sieve marking pass over a literal 0/1 flag list (flags[2] is always 1; a prime index is 1 with a chance drawn per item from 0.25, 0.4 or 0.5 and any other index with chance 0.9, so a prime is often
    not flagged, its multiples are then often left at 1, and the sum is never 0): for i from 2, if flags[i] is 1, strike flags[j] = 0 for j = start(i), start(i) + i, ... below n (start(i) = i + i or 3 * i, stated; i * i, which
    confines the passes to i below the square root of n, is no longer used). Shapes: the sum of the indices struck (every strike write counts); the flag list after the pass. The old 'sum of the indices that remain 1' is gone: it
    equalled the sum of the flagged primes and the flagged 0 and 1 in 0.34-0.53 of its items (audit); a first draft's 'sum of the indices that ran a strike pass' equalled the sum of the
    flagged indices in 0.13-0.49 and is also gone; the flag list with a uniform density of ones equalled 'the flags at the primes only' in 0.24-0.35 of its items, which is why composites now start at 0.9. 30 to 56 flags (the old 10 to 38: at 10 to 17 flags the answer was nearly determined by which of 2 and 3 were flagged)."""
    fl, i, j, tot = names(r, 4)
    n = (30, 34, 38, 42, 46, 50, 56)[level]
    q = r.choice((0.25, 0.4, 0.5))

    def prime(k: int) -> bool:
        return k >= 2 and all(k % d for d in range(2, int(k**0.5) + 1))

    flags = [1 if r.random() < (q if prime(k) else 0.9) else 0 for k in range(n)]
    flags[2] = 1
    start = r.choice((B("+", V(i), V(i)), B("*", N(3), V(i))))
    shape = r.choice(("strikesum", "flags"))
    strike: list[list] = [["setidx", fl, V(j), N(0)], ["aug", j, "+", V(i)]]
    if shape == "strikesum":
        strike.insert(0, ["aug", tot, "+", V(j)])
    run: list[list] = [["set", j, start], ["while", C("<", V(j), N(n)), strike]]
    prog: list[list] = [["set", fl, LIST(flags)], ["set", tot, N(0)], ["for", i, N(2), N(n), 1, [["if", C("==", IDX(V(fl), V(i)), N(1)), run, []]]], ["print", V(tot) if shape == "strikesum" else V(fl)]]
    return finish(prog)


@f3("lists", supersedes="C1.binary_search")
def binary_search_f3(level: int, r: random.Random) -> Built:
    """Binary search on a sorted list of distinct integers, closed interval (lo <= hi, stop when found) or half-open lower bound (lo < hi, hi = mid), as stated. The old
    'index probed last' shape (the index of the target in 13 % of the items, with a closed interval) is replaced by ``probes``: the indices probed, in order, written as
    'm1,m2,...,'. Shapes kept: the sum of the probed values, the string of moves (l, r, h). The target is in the list about half the time. 12 to 48 entries (the old 5 to 45: at 5 entries a quarter of the half-open probe strings were one string)."""
    xs, t, lo, hi, mid, cnt = names(r, 6)
    n = (12, 14, 16, 20, 26, 34, 48)[level]
    vals = sorted(r.sample(range(1, 3 * n + 12), n))
    target = r.choice(vals) if r.random() < 0.5 else r.randint(0, 3 * n + 12)
    style = r.choice(("closed", "half"))
    shape = r.choice(("sum", "path", "probes"))

    def mark(letter: str) -> list[list]:
        return [["set", cnt, B("+", V(cnt), S(letter))]] if shape == "path" else []

    probe: list[list] = [["set", mid, B("//", B("+", V(lo), V(hi)), N(2))]]
    if shape == "sum":
        probe.append(["aug", cnt, "+", IDX(V(xs), V(mid))])
    elif shape == "probes":
        probe.append(["set", cnt, B("+", B("+", V(cnt), _call("str", V(mid))), S(","))])
    below = C("<", IDX(V(xs), V(mid)), V(t))
    if style == "closed":
        hit: list[list] = [*mark("h"), ["set", lo, B("+", V(hi), N(1))]]
        loop = ["while", C("<=", V(lo), V(hi)), [*probe, ["if", C("==", IDX(V(xs), V(mid)), V(t)), hit,
                [["if", below, [*mark("l"), ["set", lo, B("+", V(mid), N(1))]], [*mark("r"), ["set", hi, B("-", V(mid), N(1))]]]]]]]
        hi0: list = B("-", _call("len", V(xs)), N(1))
    else:
        loop = ["while", C("<", V(lo), V(hi)), [*probe, ["if", below, [*mark("l"), ["set", lo, B("+", V(mid), N(1))]], [*mark("r"), ["set", hi, V(mid)]]]]]
        hi0 = _call("len", V(xs))
    prog = [["set", xs, LIST(vals)], ["set", t, N(target)], ["set", lo, N(0)], ["set", hi, hi0], ["set", cnt, S("") if shape in ("path", "probes") else N(0)], loop, ["print", V(cnt)]]
    return finish(prog)


@f3("minmax", supersedes="C1.majority_vote_scan_r2")
def majority_vote_scan_f3(level: int, r: random.Random) -> Built:
    """Boyer-Moore pairing scan: if cnt == 0 take the element as candidate with cnt 1; else cnt += 1 on an equal element and cnt -= 1 on a different one. The 'candidate count'
    shape is replaced: the final candidate is the last element in about 0.75 of items, and 'last element, count 1' hit 0.36-0.42. Shapes now sum a quantity over the steps:
    ``repl`` (the sum of the candidates taken, each when it is taken), ``cntsum`` (the sum of cnt after each step), ``candsum`` (the sum of cand after each step). The list has
    6 + 2 * level values OR one more, drawn with equal chance, from 1 to k, k from 3 to 8."""
    xs, cand, cnt, i, tot = names(r, 5)
    n = 6 + 2 * level + r.randint(0, 1)
    k = r.randint(3, 8)
    vals = [r.randint(1, k) for _ in range(n)]
    shape = r.choice(("repl", "cntsum", "candsum"))
    take: list[list] = [["set", cand, IDX(V(xs), V(i))], ["set", cnt, N(1)]]
    if shape == "repl":
        take.append(["aug", tot, "+", V(cand)])
    body: list[list] = [["if", C("==", V(cnt), N(0)), take, [["if", C("==", IDX(V(xs), V(i)), V(cand)), [["aug", cnt, "+", N(1)]], [["aug", cnt, "-", N(1)]]]]]]
    if shape == "cntsum":
        body.append(["aug", tot, "+", V(cnt)])
    elif shape == "candsum":
        body.append(["aug", tot, "+", V(cand)])
    prog: list[list] = [["set", xs, LIST(vals)], ["set", cand, N(0)], ["set", cnt, N(0)], ["set", tot, N(0)], ["for", i, N(0), N(n), 1, body], ["print", V(tot)]]
    return finish(prog)


@f3("lists", supersedes="C1.counter_list", variant="the bucket index is the state of a small machine, not x % k")
def counter_list_f3(level: int, r: random.Random) -> Built:
    """Tally into a list of k counters (k from 3 to 5) where the bucket is the state of a small machine that is updated by each value, then counts[st] += 1; the printed counts list.
    Three transition styles (stated in the code): ``st = (st * mul + x) % k`` with mul % k at least 2; the same when x is even and ``st = (st + 1 + x // 2) % k`` when it is odd;
    the same when x is above a stated threshold and ``st = (st + mul) % k`` otherwise. The old bucket x % k made the answer a residue histogram (a closed form, audit); here the bucket
    depends on every earlier value, and in the last two styles the executed path depends on the data (the structural count of programs, with literals that do not change control flow
    discounted, was 3 for the old lineage and for the first draft of this one). 8 + 3 * level values from 0 to 30."""
    data, counts, i, st, x = names(r, 5)
    k = r.randint(3, 5)
    mul = r.choice([q for q in range(2, 21) if q % k >= 2])  # mul % k of 0 or 1 would make st the residue x % k or a prefix sum mod k: a histogram formula (battery: 0.22-0.29)
    vals = [r.randint(0, 30) for _ in range(8 + 3 * level)]
    style = r.randrange(3)
    main: list[list] = [["set", st, B("%", B("+", B("*", V(st), N(mul)), V(x)), N(k))]]
    if style == 1:
        step: list[list] = [["if", C("==", B("%", V(x), N(2)), N(0)), main, [["set", st, B("%", B("+", B("+", V(st), N(1)), B("//", V(x), N(2))), N(k))]]]]
    elif style == 2:
        step = [["if", C(">", V(x), N(r.randint(8, 22))), main, [["set", st, B("%", B("+", V(st), N(mul)), N(k))]]]]
    else:
        step = main
    prog: list[list] = [["set", data, LIST(vals)], ["set", counts, LIST([0] * k)], ["set", st, N(0)],
                        ["for", i, N(0), _call("len", V(data)), 1, [["set", x, IDX(V(data), V(i))], *step, ["setidx", counts, V(st), B("+", IDX(V(counts), V(st)), N(1))]]],
                        ["print", V(counts)]]
    return finish(prog)


@f3("lists", supersedes="C1.list_build")
def list_build_f3(level: int, r: random.Random) -> Built:
    """Build a list by appending an arithmetic expression of the loop index (one of five forms, with stated constants; optionally only when i % f differs from g) and print
    the list, its sum, or the sum of index times element. The old maximum shape (m - 1 in the audit's rule) is gone. Widened for capacity: five forms instead of two,
    constants up to 9, 5 + level to 8 + level terms."""
    xs, i, tot = names(r, 3)
    n = r.randint(5, 8) + level
    m = r.randint(3, 12)
    a, b = r.randint(2, 6), r.randint(0, 9)
    form = r.randrange(5)
    expr = [B("%", B("*", V(i), V(i)), N(m)), B("%", B("+", B("*", V(i), N(a)), N(b)), N(m)), B("%", B("+", B("*", B("*", V(i), V(i)), V(i)), N(b)), N(m)),
            B("%", B("*", B("+", V(i), N(a)), B("+", V(i), N(b))), N(m)), B("%", B("+", B("+", B("*", V(i), V(i)), B("*", N(a), V(i))), N(b)), N(m))][form]
    add: list[list] = [["append", xs, expr]]
    if r.random() < 0.4:
        f = r.randint(2, 4)
        add = [["if", C("!=", B("%", V(i), N(f)), N(r.randrange(f))), add, []]]
    shape = r.choice(("list", "sum", "wsum"))
    prog: list[list] = [["set", xs, ["list"]], ["for", i, N(0), N(n), 1, add]]
    if shape == "wsum":
        prog += [["set", tot, N(0)], ["for", i, N(0), _call("len", V(xs)), 1, [["aug", tot, "+", B("*", V(i), IDX(V(xs), V(i)))]]], ["print", V(tot)]]
    else:
        prog.append(["print", V(xs) if shape == "list" else _call("sum", V(xs))])
    return finish(prog)


@f3("nested", supersedes="C1.nested_pairs")
def nested_pairs_f3(level: int, r: random.Random) -> Built:
    """Count or add over pairs (i, j) of a double loop: the condition is one of five (i + j mod m, i + j above t, i * j above t, i - j equals d, i * j mod m; no condition that is false for every pair of a triangular loop), the inner loop runs to
    a bound or (a third of the time) to i, and the increment is one of eight expressions of i and j, plus an offset of 0 to 3 (never the bare 1: a pure count of pairs had a most-frequent answer of 0.12-0.13). Widened for capacity (the old version had three conditions, two increments,
    bounds 3 to 5 + level and 704 programs at level 1 up to renaming; now bounds 4 to 8 + level, eight increments, an optional offset 1 to 3) and so that the printed count is a wide number."""
    c, i, j = names(r, 3)
    a, b = r.randint(4, 8 + level), r.randint(4, 8 + level)
    m = r.randint(2, 6)
    inner_tri = r.random() < 0.33
    d = r.randint(0, 2) if inner_tri else r.randint(-2, 2)
    cond = [C("==", B("%", B("+", V(i), V(j)), N(m)), N(r.randrange(m))), C(">", B("+", V(i), V(j)), N(r.randint(3, 8))), C(">", B("*", V(i), V(j)), N(r.randint(2, 8))),
            C("==", B("-", V(i), V(j)), N(d)), C("==", B("%", B("*", V(i), V(j)), N(m)), N(r.randrange(m)))][r.randrange(5)]
    inc = r.choice((B("+", V(i), V(j)), B("*", V(i), V(j)), V(i), V(j), B("+", B("*", V(i), V(i)), V(j)), B("+", V(i), B("*", N(2), V(j))), B("+", B("*", N(2), V(i)), V(j)), B("+", B("*", V(j), V(j)), V(i))))
    off = r.choice((0, 0, 1, 2, 3))
    if off:
        inc = B("+", inc, N(off))
    inner_stop = V(i) if inner_tri else N(b)
    return finish([["set", c, N(0)], ["for", i, N(0), N(a), 1, [["for", j, N(0), inner_stop, 1, [["if", cond, [["aug", c, "+", inc]], []]]]]], ["print", V(c)]])


@f3("tables", supersedes="C1.coin_change_table")
def coin_change_table_f3(level: int, r: random.Random) -> Built:
    """As ``coin_change_table`` (coin table over amounts 0..T: ways[a] += ways[a - c] with the coins in the outer loop counts combinations, with the amounts in the outer loop counts ordered
    sequences, best[a] = min(best[a], best[a - c] + 1) gives the fewest coins; shapes ways[T], the fewest coins, the sum of the table) widened for capacity only: 2 to 4 coin values from 1 to 14
    (the old 1 to 12 gave about 9,000 programs per level up to renaming, below the 21,010 demanded at G = 12 when counted per lineage) and T = 8 + 3 * level + (0 to 6). The most frequent
    answer of the old lineage at level 0 (0.265) is NOT improved by this: it comes from the small tables at level 0 and is untouched. The algorithm and
    the shapes are those of the superseded lineage."""
    coins, ways, a, c, k = names(r, 5)
    t = 8 + 3 * level + r.randint(0, 6)
    cv = sorted(r.sample(range(1, 15), r.randint(2, 4)))
    shape = r.choice(("combos", "orders", "fewest", "tablesum"))
    amounts_by_coin: list[list] = [["set", c, IDX(V(coins), V(k))]]
    prog: list[list] = [["set", coins, LIST(cv)]]
    if shape == "fewest":
        reach = [True] + [False] * t
        for amt in range(1, t + 1):
            reach[amt] = any(amt >= x and reach[amt - x] for x in cv)
        if not reach[t]:
            raise Retry  # the answer must be a real count, not the 99 that marks an unreachable amount (validity)
        prog += [["set", ways, ["list", N(0)]], ["for", a, N(0), N(t), 1, [["append", ways, N(99)]]],
                 ["for", k, N(0), _call("len", V(coins)), 1, [*amounts_by_coin, ["for", a, V(c), N(t + 1), 1,
                  [["setidx", ways, V(a), _call("min", IDX(V(ways), V(a)), B("+", IDX(V(ways), B("-", V(a), V(c))), N(1)))]]]]],
                 ["print", IDX(V(ways), N(t))]]
        return finish(prog)
    add = ["setidx", ways, V(a), B("+", IDX(V(ways), V(a)), IDX(V(ways), B("-", V(a), V(c))))]
    prog += [["set", ways, ["list", N(1)]], ["for", a, N(0), N(t), 1, [["append", ways, N(0)]]]]
    if shape == "orders":
        prog.append(["for", a, N(1), N(t + 1), 1, [["for", k, N(0), _call("len", V(coins)), 1, [*amounts_by_coin, ["if", C(">=", V(a), V(c)), [add], []]]]]])
    else:
        prog.append(["for", k, N(0), _call("len", V(coins)), 1, [*amounts_by_coin, ["for", a, V(c), N(t + 1), 1, [add]]]])
    prog.append(["print", _call("sum", V(ways)) if shape == "tablesum" else IDX(V(ways), N(t))])
    return finish(prog)
