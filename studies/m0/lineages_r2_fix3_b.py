# ruff: noqa: E501
"""R2 fix round 3, part b: structures (hash_probe, cache_eviction), parsing (bracket_match, expression_eval), games (subtraction_game), graphs (cheapest_network).
Same method as ``lineages_r2_fix3`` (tells removed by construction; a Retry only for validity). Self-checked, not independent review."""

from __future__ import annotations

import itertools
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import and_, lst, until
from studies.m0.lineages_r2_fix3 import fix3
from studies.m0.lineages_r2_graphs import mst_weight
from studies.m0.lineages_r2_parsing import evaluate
from studies.m0.vocab import OBJECTS, TOWNS

# ---------------------------------------------------------------- hash_probe


def _hash_place(keys: list[int], m: int) -> tuple[list[int | None], list[int]]:
    table: list[int | None] = [None] * m
    looked: list[int] = []
    for k in keys:
        s, n = k % m, 1
        while table[s] is not None:
            s = (s + 1) % m
            n += 1
        table[s] = k
        looked.append(n)
    return table, looked


@fix3("structures", "R2.hash_probe")
def hash_probe(level: int, r: random.Random) -> Built:
    """Procedure: linear-probing hash table. structured: {"m": int, "keys": [int], "ask": "table" | "checksum"}.
    Fix round 3: the single-key shapes `slot` and `probes` are DROPPED. Round 2's design (almost full table, every home in the first third) made the whole table one block that starts at the smallest home, so
    'start of the block + position' read 0.73-0.98; with homes spread over the table a single key is often at its home or after only same-home keys (0.4-0.57). By construction the answer is now about the WHOLE table:
    `table`: the final contents of every slot from 0 to m-1 (a dash for a slot that stays empty), which a rule that places keys by a formula cannot get right without doing the placements; `checksum`: the sum of the numbers of the
    slots that end up holding a number (slot numbers, not the held numbers), which depends on which slots stay empty (a total of probes was tried and dropped: its answers cluster, constant guess 0.2).
    m = 10 + level slots, round(0.7 m) distinct numbers (10..99), homes spread over the whole table. No item is chosen or redrawn by what any rule gives."""
    m = 10 + level
    nk = round(0.7 * m)
    keys = r.sample(range(10, 100), nk)
    table, _looked = _hash_place(keys, m)
    head = (f"A table has {m} slots numbered 0 to {m - 1}. A number goes into the slot whose number is the remainder of the number divided by {m}; "
            f"if that slot is taken, it goes into the next slot up (slot {m - 1} is followed by slot 0), and so on until a free slot is found. Numbers are added in this order: {lst(keys)}. ")
    if r.random() < 0.6:
        ans = ", ".join("-" if x is None else str(x) for x in table)
        return Built(head + f"After all the numbers are added, what does each slot hold, from slot 0 to slot {m - 1}? Write the numbers separated by commas, with a dash for a slot that is empty.", {"m": m, "keys": keys, "ask": "table"}, ans, "text", None)
    ans = str(sum(i for i, x in enumerate(table) if x is not None))
    return Built(head + "After all the numbers are added, add up the NUMBERS OF THE SLOTS that hold a number (for example, if only slots 2 and 5 held numbers the answer would be 7; the numbers held do not matter, only which slots are taken). What is the sum?", {"m": m, "keys": keys, "ask": "checksum"}, ans, "number", None)


# ---------------------------------------------------------------- cache_eviction


def _cache_step(cache: list[str], x: str, cap: int, policy: str, evicted: list[str]) -> None:
    if x in cache:
        if policy == "lru":
            cache.remove(x)
            cache.append(x)
        return
    if len(cache) == cap:
        evicted.append(cache.pop(0))
    cache.append(x)


@fix3("structures", "R2.cache_eviction")
def cache_eviction(level: int, r: random.Random) -> Built:
    """Procedure: cache with a stated eviction rule. structured: {"cap": int, "seq": [item], "policy": "lru" | "fifo", "ask": "evicted" | "contents"}.
    Fix round 3: the `misses` count (a small answer; the other policy's count read 0.42-0.60) and the yes/no `present` question (0.85-0.91 read off the last requests) are DROPPED. The answers are now LISTS that a counting or
    last-requests rule cannot give: `evicted`: the items removed to make room, in the order they were removed (either policy); `contents` (FIFO only, because under LRU the contents are read off the last requests backwards):
    the items in the cache at the end, from the one loaded longest ago to the one loaded most recently. By construction the request sequence begins with cap+1 different items (so something is always removed)
    and each later request is, with chance 0.65 for `contents` and 0.4 for `evicted` (which needs many misses, so a long list), a re-request of an item that is in the cache at that moment (under the stated rule), otherwise a draw from a pool of cap + 3 (cap + 5 for `evicted`) + level//2 items; the hits are what make the two rules differ.
    Nothing is redrawn on what any rule gives."""
    cap = r.randint(3, 4 + level // 3)
    ask = r.choice(("evicted", "evicted", "contents"))
    pool = r.sample(OBJECTS, cap + (3 if ask == "contents" else 5) + level // 2)
    ln = (14 if ask == "contents" else 22) + 2 * level + r.randint(0, 3)
    hit = 0.65 if ask == "contents" else 0.4
    policy = "fifo" if ask == "contents" else r.choice(("lru", "fifo"))
    cache: list[str] = []
    evicted: list[str] = []
    seq: list[str] = []
    first = r.sample(pool, cap + 1)
    for i in range(ln):
        if i < cap + 1:
            x = first[i]
        elif r.random() < hit:
            x = r.choice(cache)
        else:
            x = r.choice(pool)
        seq.append(x)
        _cache_step(cache, x, cap, policy, evicted)
    rule = ("the item that was requested longest ago (counting its latest request) is removed to make room" if policy == "lru"
            else "the item that was loaded into the cache longest ago is removed to make room (a hit does not change the order)")
    head = (f"A cache holds at most {cap} items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; "
            f"if it is not, it is put into the cache, and if the cache was full {rule}. Requests in order: {', '.join(seq)}. ")
    st = {"cap": cap, "seq": seq, "policy": policy, "ask": ask}
    if ask == "evicted":
        return Built(head + "Which items are removed from the cache to make room, in the order in which they are removed? Write the item names separated by commas.", st, ", ".join(evicted), "text", None)
    return Built(head + "After the last request, which items are in the cache, from the one loaded longest ago to the one loaded most recently? Write the item names separated by commas.", st, ", ".join(cache), "text", None)


# ---------------------------------------------------------------- bracket_match

_OPEN = "([{"
_CLOSE = ")]}"
_KIND_NAME = {"(": "round ( )", "[": "square [ ]", "{": "curly { }"}


def _dyck(r: random.Random, pairs: int) -> list[tuple[int, int]]:
    """A random nested text of `pairs` pairs as a list of (open position, close position), 0-based, opening with chance 0.58 so the nesting gets deep."""
    pos = 0
    stack: list[int] = []
    out: list[tuple[int, int]] = []
    opened = 0
    while opened < pairs or stack:
        if opened < pairs and (not stack or r.random() < 0.58):
            stack.append(pos)
            opened += 1
        else:
            out.append((stack.pop(), pos))
        pos += 1
    return sorted(out)


def _bracket_text(r: random.Random, pairs: int) -> tuple[list[str], list[tuple[int, int, int]]]:
    prs = _dyck(r, pairs)
    kinds = [i % 3 for i in range(pairs)]
    r.shuffle(kinds)
    chars = [""] * (2 * pairs)
    info = []
    for (o, c), k in zip(prs, kinds, strict=True):
        chars[o], chars[c] = _OPEN[k], _CLOSE[k]
        info.append((o, c, k))
    return chars, info


def _first_mismatch(chars: list[str]) -> int:
    st: list[str] = []
    for i, ch in enumerate(chars):
        if ch in _OPEN:
            st.append(ch)
        elif _OPEN[_CLOSE.index(ch)] != st.pop():
            return i + 1
    raise ValueError("no mismatch")


@fix3("parsing", "R2.bracket_match")
def bracket_match(level: int, r: random.Random) -> Built:
    """Procedure: match brackets with a last-opened-first-closed stack. structured: {"s": str, "ask": "match_all" | "first_error", "kind": "(" | "[" | "{" or null}.
    Fix round 3 (R-1, R-13): the yes/no `valid` shape is DROPPED: a rule that checks only some of the pairs (the top-level ones, or those at one depth) reads 0.5 + half the share of pairs it checks (0.79-0.84 measured), and no
    corruption that keeps the counts of every kind can be placed so that every partial check misses it. The single-position `match` shape is DROPPED (the answer is one of about twenty positions; 'last/next closer of the same
    kind' read 0.35-0.51). New shapes whose answer is a LIST that a partial rule cannot give: `match_all`: for every opening bracket of one stated kind, the position of its closer, in the order of the openers;
    `first_error`: the text is correct except that the closers of two pairs have been swapped, a pair and a pair that encloses it, both enclosing something, of different kinds, their closers not next to each other (a swap of two separate pairs would show in the running count of a kind: the closer's kind has not been opened yet, 0.9 measured); the answer is the position of the first closing bracket that does not match
    the most recently opened bracket still open. By construction the kinds are shared out evenly over the 14 + level pairs (so every kind has at least four pairs; with 9 + level the 'k-th closer goes with the k-th opener' rule read 0.25), and the nesting is deep (opening chance 0.58)."""
    pairs = 14 + level
    chars, info = _bracket_text(r, pairs)
    if r.random() < 0.5:
        k = r.randrange(3)
        t = "".join(chars)
        stack: list[int] = []
        closer_of: dict[int, int] = {}
        for i, ch in enumerate(t):
            if ch in _OPEN:
                stack.append(i)
            else:
                closer_of[stack.pop()] = i
        ans = [closer_of[o] + 1 for o, _c, kk in sorted(info) if kk == k]
        q = (f"In the correctly nested text {t} (positions are counted from 1 at the left), every opening bracket is closed by a closing bracket of the same kind, and brackets opened later are closed earlier. "
             f"For every opening {_KIND_NAME[_OPEN[k]].split()[0]} bracket, in order from left to right, at which position is the closing bracket that belongs to it? Give the positions separated by commas, in the same order.")
        return Built(q, {"s": t, "ask": "match_all", "kind": _OPEN[k]}, lst(ans), "list", None)
    nonleaf = [(o, c, kk) for o, c, kk in info if c - o > 1]
    nested = [(a, b) for a in nonleaf for b in nonleaf if b[0] < a[0] and a[1] + 1 < b[1] and a[2] != b[2]]
    if not nested:
        raise Retry
    a, b = r.choice(nested)
    ch2 = list(chars)
    ch2[a[1]], ch2[b[1]] = chars[b[1]], chars[a[1]]
    t = "".join(ch2)
    q = (f"In the text {t} (positions are counted from 1 at the left) every opening bracket should be closed by a closing bracket of the same kind, with brackets opened later closed earlier, but the text breaks this rule. "
         "Reading from the left, each closing bracket should match the opening bracket most recently opened and not yet closed. At which position is the first closing bracket that does not match?")
    return Built(q, {"s": t, "ask": "first_error", "kind": None}, str(_first_mismatch(ch2)), "number", None)


# ---------------------------------------------------------------- expression_eval


def _num(r: random.Random, level: int) -> int:
    return r.randint(2, 9 if level < 4 else 20)


def _paren_sum(r: random.Random, level: int) -> str:
    return f"({_num(r, level)} {r.choice('+-')} {_num(r, level)})"


@fix3("parsing", "R2.expression_eval")
def expression_eval(level: int, r: random.Random) -> Built:
    """Procedure: evaluate an infix expression under a stated convention. structured: {"text": str, "convention": "ranked" | "left_to_right"}. Wording as in rev2 (the rule applies inside parentheses too; + and - are one rank).
    Fix round 3 (R-1): rev2 left the wrong-rule rate 'natural' (the item evaluated under the other rule, or with parentheses ignored, agreed with the key on 0.3-0.9 of items). Now the structure that makes each misreading
    differ is PLANTED rather than hoped for, and no item is redrawn on any rule's value. ranked: a chain of 3 + level//2 (+0/1) terms; a later term is a product; one factor of a product is a parenthesised sum;
    the operators contain '-' directly followed by '+' (so 'plus before minus' differs); further factors and parentheses are added at random with the level. left_to_right: a chain of 4 + level//2 (+0/1) numbers; some '+' or '-' is directly
    followed by '*'; one later number is a parenthesised chain with a '+'/'-' followed by '*' inside it. Numbers are 2..9 (2..20 from level 4)."""
    conv = r.choice(("ranked", "left_to_right"))
    if conv == "ranked":
        k = 3 + level // 2 + r.randint(0, 1)
        terms = [[str(_num(r, level))] for _ in range(k)]
        ops = [r.choice("+-") for _ in range(k - 1)]
        i = r.randrange(1, k)
        terms[i].append(str(_num(r, level)))
        j = r.randrange(0, k - 2)
        ops[j], ops[j + 1] = "-", "+"
        terms[i][r.randrange(len(terms[i]))] = _paren_sum(r, level)
        for t_ in terms:
            if level >= 2 and r.random() < 0.15 * (level // 2):
                t_.append(str(_num(r, level)))
        if level >= 3:
            for t_ in terms:
                if len(t_) > 1 and r.random() < 0.3:
                    f = r.randrange(len(t_))
                    if t_[f].isdigit():
                        t_[f] = _paren_sum(r, level)
        text = ""
        for n_, t_ in enumerate(terms):
            text += ("" if n_ == 0 else f" {ops[n_ - 1]} ") + " * ".join(t_)
        q = (f"Work out {text}. Use these rules, in this order, also inside every pair of parentheses: do what is inside parentheses first, innermost first; then do all the multiplications, from left to right; "
             "then do all the additions and subtractions together as one group, strictly from left to right (so 8 - 3 + 2 is worked as (8 - 3) + 2 = 7, and 8 + 3 - 2 as (8 + 3) - 2 = 9). What is the result?")
        ans = evaluate(text, True)
    else:
        k = 4 + level // 2 + r.randint(0, 1)
        atoms = [str(_num(r, level)) for _ in range(k)]
        ops = [r.choice("+-*") for _ in range(k - 1)]
        i = r.randrange(0, k - 2)
        ops[i], ops[i + 1] = r.choice("+-"), "*"
        p = r.randrange(1, k)
        atoms[p] = f"({_num(r, level)} {r.choice('+-')} {_num(r, level)} * {_num(r, level)})"
        for n_ in range(k):
            if n_ != p and n_ >= 1 and level >= 2 and r.random() < 0.1 * (level // 2):
                atoms[n_] = f"({_num(r, level)} {r.choice('+-*')} {_num(r, level)})"
        text = atoms[0]
        for n_ in range(1, k):
            text += f" {ops[n_ - 1]} {atoms[n_]}"
        q = (f"Work out {text} by this rule, which is not the usual one: work out each pair of parentheses first, innermost first, and inside a pair of parentheses use the same rule as outside; "
             "the rule is that the operators are done strictly in the order they are written, from left to right, and multiplication gets no priority over addition or subtraction "
             "(so 2 + 3 * 4 is worked as (2 + 3) * 4 = 20). What is the result?")
        ans = evaluate(text, False)
    return Built(q, {"text": text, "convention": conv}, str(ans), "number", None)


# ---------------------------------------------------------------- subtraction_game


def _grundy_table(n: int, moves: list[int]) -> list[int]:
    g = [0] * (n + 1)
    for s in range(1, n + 1):
        seen = {g[s - m] for m in moves if m <= s}
        v = 0
        while v in seen:
            v += 1
        g[s] = v
    return g


@fix3("games", "R2.subtraction_game")
def subtraction_game(level: int, r: random.Random) -> Built:
    """Procedure: label pile sizes from small to large (position values, combined over several piles by the exclusive-or rule). structured: {"piles": [int], "n": int, "moves": [int]}.
    Fix round 3 (R-1): with two piles, the rule 'each pile alone is a win or a loss; equal -> no' read 0.79-0.82, and any exclusive-or of position values has a partial-bit rule (the parity of the sum of the values: 0.75-0.86, a
    valid partial computation, reported as (P)). By construction there are FOUR piles (sizes 6 .. 20 + 6*level) and 5 allowed amounts (6 from level 3) taken from 1 .. 10 + level, so the position values spread over about six values and
    'count the winning piles' falls to about 0.6; no heuristic enters. A turn removes an allowed amount from ONE pile; a player unable to move loses. Answer yes/no: does the first player win with perfect play; the wanted answer is drawn 50/50 and the draw
    repeated until the KEY matches (balancing on the key, not on a heuristic, as in rev2)."""
    msize = 5 if level < 3 else 6
    top = 10 + level
    want = r.choice(("yes", "no"))
    top_pile = 20 + 6 * level

    def make() -> tuple[list[int], list[int]]:
        return sorted(r.sample(range(1, top + 1), msize)), [r.randint(6, top_pile) for _ in range(4)]

    def ok(x: tuple[list[int], list[int]]) -> bool:
        mv, pl = x
        g = _grundy_table(top_pile, mv)
        v = 0
        for p in pl:
            v ^= g[p]
        return (v != 0) == (want == "yes")

    moves, piles = until(800, make, ok)
    q = (f"Two players take turns. There are four piles of stones, with {piles[0]}, {piles[1]}, {piles[2]} and {piles[3]} stones. On a turn a player picks ONE pile and removes from it one of these amounts of stones: {' or '.join(str(m) for m in moves)}; "
         "an amount can be chosen only if that pile still has at least that many stones. A player who cannot move on their turn loses. Both players play perfectly. Does the player who moves first win? Answer yes or no.")
    return Built(q, {"piles": piles, "n": sum(piles), "moves": moves}, want, "yn", 2)


# ---------------------------------------------------------------- cheapest_network


@fix3("graphs", "R2.cheapest_network")
def cheapest_network(level: int, r: random.Random) -> Built:
    """Procedure: cycle-avoiding cheapest-edge selection. structured as before: {"towns": [name], "cables": [[a, b, cost]]}.
    Fix round 3: the grouped-towns construction (a cheap triangle in each group, dear cables between groups) was itself a solver: 'cheap cables minus the dearest of each triangle plus the (g-1) cheapest dear cables' read 1.00 at
    levels 0-2. By construction the towns are now POINTS on a 26 x 26 grid, a cable costs the walking distance between its two towns (at least 1), and the 2n cheapest pairs are the cables offered. Nearby towns form
    cycles of cheap cables, so adding up the n-1 cheapest cables is the answer on about 6% of items (random weights need 12 towns for that), and no group template exists. n = 8 + level//2 towns (8..11). A draw whose cables
    do not connect all the towns is drawn again (validity). Answer: the least total cost of a set of cables that joins all the towns."""
    n = 8 + level // 2
    pts = [(r.randint(0, 25), r.randint(0, 25)) for _ in range(n)]
    allp = sorted((max(1, abs(pts[a][0] - pts[b][0]) + abs(pts[a][1] - pts[b][1])), a, b) for a, b in itertools.combinations(range(n), 2))
    edges = [[a, b, w] for w, a, b in allp[: 2 * n]]
    ans = mst_weight(n, edges)
    if ans is None:
        raise Retry
    towns = r.sample(TOWNS, n)
    r.shuffle(edges)
    cables = [[towns[a], towns[b], w] for a, b, w in edges]
    text = " ".join(f"A cable between {a} and {b} would cost {w}." for a, b, w in cables)
    q = (f"The towns {and_(sorted(towns))} must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. {text} "
         "What is the smallest total cost of a set of cables that joins all the towns?")
    return Built(q, {"towns": towns, "cables": cables}, str(ans), "number", None)

