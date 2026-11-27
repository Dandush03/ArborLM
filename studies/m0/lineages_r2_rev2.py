# ruff: noqa: E501
"""R2 batch 1, revision 2 (fix round after audit AUDIT_M0_R2_1 and lead rulings R-1, R-4, R-5; no new lineages).

Revised SHAPES of lineages already delivered (same lineage ids ``R2.<name>``), kept in their own registry ``REV2``. The batch-1 shapes in
``lineages_r2_<family>.py`` stay on file and are SUPERSEDED where listed in ``SUPERSEDES``. Two ids are new shape ids of EXISTING core lineages
(``R2.string_rewrite_nonidentity`` of ``R2.string_rewrite``; ``R2.to_base_wide`` of ``R2.to_base``); they are shapes, not new lineages.

Method (R-1): a tell is removed by CONSTRUCTION, never by redrawing items conditional on a heuristic's outcome and never with a probability fitted to a
heuristic. Conditioning on the item's own key (balancing yes/no) and on structural bounds (a minimum number of steps) is kept and stated per builder.
Where a tell cannot be removed by construction the lineage is listed in ``NOT_REGISTERED`` with the reason (see the manifest).
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage, Retry, lineages_of
from studies.m0.lineages_r2_common import lst, until
from studies.m0.lineages_r2_dynprog import (
    coin_min as _unused_coin_min,  # noqa: F401  (kept to show the superseded shape's helper is untouched)
)
from studies.m0.lineages_r2_graphs import deferred_acceptance, mst_weight
from studies.m0.lineages_r2_parsing import (
    _render_ltr,
    _render_std,
    _tree,
    _val,
    balanced,
    evaluate,
    match_of,
    random_balanced,
)
from studies.m0.lineages_r2_structures import cache_run, hash_table
from studies.m0.vocab import NAMES, OBJECTS, TOWNS

REV2: list[Lineage] = []
# batch-1 lineage id -> what supersedes its shape(s)
SUPERSEDES: dict[str, str] = {}
# family names that clash with an existing R2 family are renamed here only (the existing files are not edited)
FAMILY_RENAME = {"numtheory": "numtheory_b1"}

Builder = Callable[[int, random.Random], Built]


def rev2(family: str, supersedes: str | None = None) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R2.{fn.__name__}"
        if any(x.id == lid for x in REV2):
            raise ValueError(f"duplicate {lid}")
        if supersedes is None and lid in {x.id for x in lineages_of("R2")}:
            raise ValueError(f"{lid} is a core id")
        REV2.append(Lineage(lid, "R2", FAMILY_RENAME.get(family, family), fn))
        SUPERSEDES[lid] = supersedes or lid
        return fn

    return deco


def load_rev2() -> list[Lineage]:
    return sorted(REV2, key=lambda x: x.id)


# ---------------------------------------------------------------- R-4 wording


@rev2("parsing")
def expression_eval(level: int, r: random.Random) -> Built:
    """Procedure: evaluate an infix expression under a stated convention. structured: {"text": str, "convention": "ranked" | "left_to_right"}.
    Both conventions now say that the rule is used inside parentheses as well, and ``ranked`` defines addition and subtraction as ONE rank worked left to right
    (the batch-1 words "operators of the same kind" could be read as the same symbol). No item is redrawn on what the other convention gives. Answer: the integer value."""
    leaves = 4 + level + r.randint(0, 1)
    hi = 9 if level < 4 else 20
    conv = r.choice(("ranked", "left_to_right"))
    t = _tree(r, leaves, hi)
    text = _render_std(t, r) if conv == "ranked" else _render_ltr(t)
    ans = _val(t)
    if evaluate(text, conv == "ranked") != ans:
        raise AssertionError("renderer and evaluator disagree")
    if conv == "ranked":
        q = (f"Work out {text}. Use these rules, in this order, also inside every pair of parentheses: do what is inside parentheses first, innermost first; then do all the multiplications, from left to right; "
             "then do all the additions and subtractions together as one group, strictly from left to right (so 8 - 3 + 2 is worked as (8 - 3) + 2 = 7, and 8 + 3 - 2 as (8 + 3) - 2 = 9). What is the result?")
    else:
        q = (f"Work out {text} by this rule, which is not the usual one: work out each pair of parentheses first, innermost first, and inside a pair of parentheses use the same rule as outside; "
             "the rule is that the operators are done strictly in the order they are written, from left to right, and multiplication gets no priority over addition or subtraction "
             "(so 2 + 3 * 4 is worked as (2 + 3) * 4 = 20). What is the result?")
    return Built(q, {"text": text, "convention": conv}, str(ans), "number", None)


def _merge_cost(ws: list[int]) -> int:
    import heapq

    h = list(ws)
    heapq.heapify(h)
    total = 0
    while len(h) > 1:
        a, b = heapq.heappop(h), heapq.heappop(h)
        total += a + b
        heapq.heappush(h, a + b)
    return total


@rev2("greedy")
def merge_smallest_cost(level: int, r: random.Random) -> Built:
    """Procedure: repeatedly merge the two smallest (Huffman-style cost). structured: {"ws": [int]}. Wording now says ANY two piles may be joined (not only neighbours).
    Widened at level 0 (5 piles of 1..20; batch 1 had 4 piles of 1..9, 488 distinct multisets). No gate on the answer. Answer: the least total cost."""
    n = 5 + level
    ws = [r.randint(1, 20 + 6 * level) for _ in range(n)]
    q = (f"There are piles of stones with these sizes: {lst(ws)}. Any two piles (they need not be next to each other in this list) can be joined into one pile; joining costs as many coins as the size of the new pile. "
         "The piles are joined, two at a time, until one pile is left. What is the smallest total number of coins that can be paid?")
    return Built(q, {"ws": ws}, str(_merge_cost(ws)), "number", None)


@rev2("rewrite", supersedes="R2.string_rewrite")
def string_rewrite_nonidentity(level: int, r: random.Random) -> Built:
    """Procedure: sequential substitution (the existing R2.string_rewrite, same cluster). structured: {"s": str, "rules": [[pattern, replacement]]}.
    Every rule is drawn so that it does something: the pattern is a substring of the string as it stands when the rule is reached, and the replacement differs from it
    (it may be empty = deletion). Steps scan left to right over non-overlapping matches. Answer: the final string (never empty)."""
    s = "".join(r.choice("abc") for _ in range(6 + 2 * level))
    cur, rules = s, []
    for _ in range(1 + (level + 1) // 2):
        ln = r.randint(1, min(2, len(cur)))
        i = r.randrange(len(cur) - ln + 1)
        p = cur[i : i + ln]
        t = "".join(r.choice("abc") for _ in range(r.randint(0, 3)))
        if t == p:
            raise Retry
        rules.append([p, t])
        cur = cur.replace(p, t)
        if cur == "":
            raise Retry
    steps = "; ".join(f"replace every '{p}' with '{t}'" if t else f"delete every '{p}'" for p, t in rules)
    q = (f"Start with the string {s}. Do these steps in order, each step scanning left to right over non-overlapping matches in the string as it is when the step starts: {steps}. What is the final string?")
    return Built(q, {"s": s, "rules": rules}, cur, "text", None)


@rev2("base", supersedes="R2.to_base")
def to_base_wide(level: int, r: random.Random) -> Built:
    """Procedure: repeated division (the existing R2.to_base, same cluster). structured: {"n": int, "base": int}. Widened: bases 2..9 at levels 0-1 and the batch-0 set
    beyond, and n up to 500 * 4^(level+1) (the existing L0 space was 151 values x 5 bases = 755 items). Answer: the digits (0-9 then a-f)."""
    dig = "0123456789abcdef"
    b = r.choice((2, 3, 4, 5, 6, 7, 8, 9) if level < 2 else (2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 16))
    n = r.randint(10, 500 * 4 ** (level + 1))
    s, x = "", n
    while x:
        s = dig[x % b] + s
        x //= b
    q = f"Write the decimal number {n} in base {b}. Use digits 0-9 and then lowercase letters a-f for ten to fifteen."
    return Built(q, {"n": n, "base": b}, s, "text", None)


# ---------------------------------------------------------------- R-1 shortcuts by construction


def _topple(row: list[int]) -> tuple[list[int], list[int]]:
    cur, cnt = list(row), [0] * len(row)
    n = len(cur)
    while True:
        i = next((j for j in range(n) if cur[j] >= 2), -1)
        if i < 0:
            return cur, cnt
        cur[i] -= 2
        cnt[i] += 1
        if i > 0:
            cur[i - 1] += 1
        if i < n - 1:
            cur[i + 1] += 1


@rev2("dynamics")
def chip_toppling(level: int, r: random.Random) -> Built:
    """Procedure: topple until stable (abelian sandpile on a path with open ends). structured: {"row": [int], "ask": "topplings" | "topplings_of", "cell": int or null (1-based)}.
    The batch-1 shapes `final` and `lost` are DROPPED: conservation of chips and of the first moment answer them in closed form (audit: 0.97-1.00 and 0.82-0.90).
    Order does not change any cell's number of topplings. Answer: the total number of topplings, or the number of times cell `cell` topples. Bound: 2 to 400 topplings (a size bound, not a heuristic gate)."""
    n = 5 + level
    row = [r.randint(0, 3 + (level + 2) // 2) for _ in range(n)]
    _fin, cnt = _topple(row)
    tot = sum(cnt)
    if not 2 <= tot <= 400:
        raise Retry
    head = (f"A row of {n} cells holds chips: {lst(row)} (from left to right). A cell that holds 2 or more chips topples: it gives up 2 chips, one going to the cell on its left and one to the cell on its right; "
            "a chip that goes past either end of the row is lost for good. Cells topple one at a time, in any order you like, until no cell holds 2 or more chips (the outcome, including how many times each cell topples, does not depend on the order). ")
    if r.random() < 0.5:
        return Built(head + "How many topplings happen in total?", {"row": row, "ask": "topplings", "cell": None}, str(tot), "number", None)
    c = r.randrange(n)
    return Built(head + f"How many times does the cell in position {c + 1} (counting from 1 at the left) topple?", {"row": row, "ask": "topplings_of", "cell": c + 1}, str(cnt[c]), "number", None)


def _pairs_with_content(s: str) -> list[tuple[int, int]]:
    out, stack = [], []
    for i, ch in enumerate(s):
        if ch in "([{":
            stack.append(i)
        else:
            j = stack.pop()
            if i - j > 1:
                out.append((j, i))
    return out


@rev2("parsing")
def bracket_match(level: int, r: random.Random) -> Built:
    """Procedure: match brackets with a stack. structured: {"s": str, "ask": "valid" | "match", "p": int or null (1-based)}.
    valid (yes/no, drawn 50/50 as a coin, not redrawn): the base text is a random correctly nested text that has at least two nested-or-enclosing pairs of DIFFERENT kinds
    (a structural requirement shared by both answers); a `no` text swaps the closing kinds of two such pairs, so counts of each kind are kept and the wrong closer never sits next to its opener
    (an adjacent wrong-kind pair cannot occur by construction). match: a random correctly nested text, and an opener drawn UNIFORMLY among those whose pair encloses something (so 'the very next position' cannot be the partner; no other partner position is excluded). Three kinds at every level (batch 1 used two kinds up to level 2) and 8+level pairs (batch 1: 5+level), because the 'last closer of the same kind' tell shrinks with length."""
    types = 3
    pairs = 8 + level
    if r.random() < 0.6:
        want_yes = r.random() < 0.5

        def base() -> str:
            return random_balanced(r, pairs, types)

        def has_two_kinds(t: str) -> bool:
            kinds = {{")": "(", "]": "[", "}": "{"}[t[i]] for _j, i in _pairs_with_content(t)}
            return len(kinds) >= 2

        t = until(300, base, has_two_kinds)
        if not want_yes:
            pc = _pairs_with_content(t)
            a = r.choice(pc)
            b = r.choice([x for x in pc if t[x[1]] != t[a[1]]])
            lst_t = list(t)
            lst_t[a[1]], lst_t[b[1]] = t[b[1]], t[a[1]]
            t = "".join(lst_t)
            if balanced(t):
                raise AssertionError("corruption left a valid text")
        q = (f"In the text {t} every opening bracket must be closed by a closing bracket of the same kind, and brackets that are opened later must be closed earlier (the kinds are round, square and curly). "
             "Is the text correctly nested? Answer yes or no.")
        return Built(q, {"s": t, "ask": "valid", "p": None}, "yes" if want_yes else "no", "yn", 2)
    t = random_balanced(r, pairs, types)
    pc = _pairs_with_content(t)
    if not pc:
        raise Retry
    p = r.choice([j for j, _i in pc])  # the asked opener always encloses something, so 'the next position' is never its partner
    q = (f"In the correctly nested text {t} (positions are counted from 1 at the left), every opening bracket is closed by a closing bracket of the same kind, and brackets opened later are closed earlier. "
         f"At which position is the closing bracket that belongs to the opening bracket at position {p + 1}?")
    return Built(q, {"s": t, "ask": "match", "p": p + 1}, str(match_of(t, p) + 1), "number", None)


def coin_ways(coins: list[int], amount: int) -> int:
    ways = [1] + [0] * amount
    for c in coins:
        for v in range(c, amount + 1):
            ways[v] += ways[v - c]
    return ways[amount]


@rev2("dynprog")
def coin_change_min(level: int, r: random.Random) -> Built:
    """Procedure: unbounded-supply capacity table (the same lineage; the final question changes). structured: {"coins": [int], "amount": int, "ask": "ways"}.
    The batch-1 question (fewest coins) is SUPERSEDED: greedy and amount/largest bounds answer it (audit: ceil+1 0.55-0.69, an overshoot created by excluding ceil). Now the question is the
    number of different sets of coins (order does not matter) that add up exactly to `amount`; no greedy or bound answers it. Answer: that count (at least 1)."""
    k = 3 if level < 3 else 4
    coins = sorted(r.sample(range(2, 16 + 4 * level), k))
    amount = r.randint(15 + 5 * level, 60 + 12 * level)
    w = coin_ways(coins, amount)
    if w < 1:
        raise Retry
    q = (f"You have an unlimited supply of coins worth {lst(coins[:-1])} and {coins[-1]}. In how many different ways can exactly {amount} be paid? "
         "Two ways are the same when they use the same number of coins of each worth (the order in which coins are handed over does not matter).")
    return Built(q, {"coins": coins, "amount": amount, "ask": "ways"}, str(w), "number", None)


@rev2("structures")
def hash_probe(level: int, r: random.Random) -> Built:
    """Procedure: linear-probing hash table. structured: {"m": int, "keys": [int], "ask": "slot" | "probes", "target": int}.
    By construction: the table is filled to m-1 of m slots and every key's home slot (key mod m) lies in the first third of the table (0..m//3), so clusters are long and spill over; the asked key is drawn UNIFORMLY among the keys (slot) or is the last key (probes); no preference for displaced keys.
    Answer: the slot where `target` ends up, or the number of slots looked at when the last key is added."""
    m = 7 + level
    h = m // 3
    keys: list[int] = []
    while len(keys) < m - 1:
        home = r.randint(0, h)
        k = home + m * r.randint(max(1, -(-(10 - home) // m)), (99 - home) // m)
        if k not in keys:
            keys.append(k)
    _tab, slot_of = hash_table(keys, m)
    head = (f"A table has {m} slots numbered 0 to {m - 1}. A number goes into the slot whose number is the remainder of the number divided by {m}; "
            f"if that slot is taken, it goes into the next slot up (slot {m - 1} is followed by slot 0), and so on until a free slot is found. Numbers are added in this order: {lst(keys)}. ")
    if r.random() < 0.75:
        x = r.choice(keys)
        return Built(head + f"In which slot does {x} end up?", {"m": m, "keys": keys, "ask": "slot", "target": x}, str(slot_of[x]), "number", None)
    last = keys[-1]
    probes = (slot_of[last] - last % m) % m + 1
    return Built(head + f"When {last} (the last number) is added, how many slots are looked at, counting the slot where it is finally placed?", {"m": m, "keys": keys, "ask": "probes", "target": last}, str(probes), "number", None)


@rev2("structures")
def cache_eviction(level: int, r: random.Random) -> Built:
    """Procedure: cache with a stated eviction rule. structured: {"cap": int, "seq": [item], "policy": "lru" | "fifo", "ask": "misses" | "present", "item": item or null}.
    Batch-1 `agree` logic removed. `misses`: either policy, no gate. `present`: FIFO only (under LRU the cache is the last cap distinct requests, which the tell "among the last requests" reads off),
    the pool is 2*cap items and the asked item is drawn uniformly from it, so about half the draws are in a full cache BY CONSTRUCTION (no balancing redraw)."""
    cap = r.randint(2, 3 + level // 3)
    ln = 10 + 2 * level + r.randint(0, 3)
    if r.random() < 0.5:
        pool = r.sample(OBJECTS, cap + 2 + level // 2)
        seq = [r.choice(pool) for _ in range(ln)]
        policy = r.choice(("lru", "fifo"))
        miss, _c = cache_run(seq, cap, policy)
        rule = ("the item that was requested longest ago (counting its latest request) is removed to make room" if policy == "lru"
                else "the item that was loaded into the cache longest ago is removed to make room (a hit does not change the order)")
        q = (f"A cache holds at most {cap} items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; "
             f"if it is not, it is put into the cache, and if the cache was full {rule}. Requests in order: {', '.join(seq)}. How many requests found the item missing from the cache?")
        return Built(q, {"cap": cap, "seq": seq, "policy": policy, "ask": "misses", "item": None}, str(miss), "number", None)
    pool = r.sample(OBJECTS, 2 * cap)
    seq = [r.choice(pool) for _ in range(ln)]
    x = r.choice(pool)
    _m, cache = cache_run(seq, cap, "fifo")
    q = (f"A cache holds at most {cap} items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; "
         "if it is not, it is put into the cache, and if the cache was full the item that was loaded into the cache longest ago is removed to make room (a hit does not change the order). "
         f"Requests in order: {', '.join(seq)}. After the last request, is {x} in the cache? Answer yes or no.")
    return Built(q, {"cap": cap, "seq": seq, "policy": "fifo", "ask": "present", "item": x}, "yes" if x in cache else "no", "yn", 2)


def _grundy(n: int, moves: list[int]) -> int:
    g = [0] * (n + 1)
    for s in range(1, n + 1):
        seen = {g[s - m] for m in moves if m <= s}
        v = 0
        while v in seen:
            v += 1
        g[s] = v
    return g[n]


@rev2("games")
def subtraction_game(level: int, r: random.Random) -> Built:
    """Procedure: label pile sizes from small to large (here with two piles, so each pile needs its own label, combined by the exclusive-or rule). structured: {"piles": [n1, n2], "n": n1 + n2, "moves": [int]}.
    Batch-1 one-pile shape SUPERSEDED (audit: residue tells 0.55-0.62 and an overshoot from excluding one). Two piles: a turn removes an allowed amount from ONE pile; the player unable to move loses.
    Answer yes/no: does the first player win with perfect play. The wanted answer is drawn 50/50 and the piles are redrawn until the KEY matches (balancing on the key, not on any heuristic)."""
    top = 8 + level
    want = r.choice(("yes", "no"))

    def make() -> tuple[list[int], list[int]]:
        return sorted(r.sample(range(1, top + 1), r.randint(3, 4))), [r.randint(5, 25 + 8 * level), r.randint(5, 25 + 8 * level)]

    def ok(x: tuple[list[int], list[int]]) -> bool:
        mv, pl = x
        return ((_grundy(pl[0], mv) ^ _grundy(pl[1], mv)) != 0) == (want == "yes")

    moves, piles = until(500, make, ok)
    q = (f"Two players take turns. There are two piles of stones, with {piles[0]} and {piles[1]} stones. On a turn a player picks ONE pile and removes from it one of these amounts of stones: {' or '.join(str(m) for m in moves)}; "
         "an amount can be chosen only if that pile still has at least that many stones. A player who cannot move on their turn loses. Both players play perfectly. Does the player who moves first win? Answer yes or no.")
    return Built(q, {"piles": piles, "n": piles[0] + piles[1], "moves": moves}, want, "yn", 2)


@rev2("graphs")
def deferred_acceptance_partner(level: int, r: random.Random) -> Built:
    """Procedure: proposal-and-hold rounds. structured as batch 1. Batch-1 redraw on the first-choice and best-ranked-by outcomes REMOVED. n is 4 + level//2 (4..7; batch 1 had 3..6), preferences independent
    and uniform. Residual heuristic rates are natural, not engineered; see the manifest (this lineage is reported NOT REGISTERED if they stay far above chance)."""
    n = 4 + level // 2
    names = r.sample(NAMES, 2 * n)
    props, resps = names[:n], names[n:]
    pp = [r.sample(range(n), n) for _ in range(n)]
    rp = [r.sample(range(n), n) for _ in range(n)]
    out = deferred_acceptance(pp, rp)
    who = r.randrange(n)
    sa = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]  # noqa: E731
    lines = " ".join(f"{props[i]} ranks {sa([resps[j] for j in pp[i]])} from best to worst." for i in range(n))
    lines2 = " ".join(f"{resps[j]} ranks {sa([props[i] for i in rp[j]])} from best to worst." for j in range(n))
    q = (f"{sa(sorted(props))} each want to be paired with one of {sa(sorted(resps))}, and each of those wants one of the first group. {lines} {lines2} "
         "They are paired by rounds: in each round every unpaired person from the first group asks the best-ranked person (on their own list) they have not asked before; "
         "a person who is asked keeps the best-ranked asker so far and turns the others down (a person who was kept is let go if someone better asks later). Rounds go on until everyone is paired. "
         f"Who is {props[who]} paired with? Choose from {sa(sorted(resps))}.")
    st = {"proposers": props, "responders": resps, "prefs_p": {props[i]: [resps[j] for j in pp[i]] for i in range(n)},
          "prefs_r": {resps[j]: [props[i] for i in rp[j]] for j in range(n)}, "who": props[who]}
    return Built(q, st, resps[out[who]], "name", n)


@rev2("graphs")
def cheapest_network(level: int, r: random.Random) -> Built:
    """Procedure: cycle-avoiding cheapest-edge selection. structured as batch 1. Batch-1 gate on the naive outcome REMOVED. By construction the n = 3g towns (g = 2 + level//3) form g groups of three; the three cables inside a group (a triangle) cost 1..6 and every cable between groups costs 7..20.
    The n cables inside groups are the n cheapest, so the n-1 cheapest always contain a cycle, and every town's cheapest cable is inside its group, so 'add up the n-1 cheapest' is never the answer and a per-town cheapest-cable sum is the answer only by coincidence (measured under 1%); a connection between groups is always needed."""
    g = 2 + level // 3
    n = 3 * g
    towns = r.sample(TOWNS, n)
    order = list(range(n))
    r.shuffle(order)
    groups = [order[3 * i : 3 * i + 3] for i in range(g)]
    pairs: dict[tuple[int, int], int] = {}
    for grp in groups:
        for a, b in itertools.combinations(sorted(grp), 2):
            pairs[(a, b)] = r.randint(1, 6)  # a triangle of cheap cables inside each group
    for i in range(1, g):
        a, b = r.choice(groups[r.randrange(i)]), r.choice(groups[i])
        pairs.setdefault((min(a, b), max(a, b)), r.randint(7, 20))  # a tree of dearer cables joining the groups
    for _ in range(g):
        i, j = r.sample(range(g), 2)
        a, b = r.choice(groups[i]), r.choice(groups[j])
        pairs.setdefault((min(a, b), max(a, b)), r.randint(7, 20))
    edges = [[a, b, w] for (a, b), w in pairs.items()]
    ans = mst_weight(n, edges)
    if ans is None:
        raise Retry
    r.shuffle(edges)
    cables = [[towns[a], towns[b], w] for a, b, w in edges]
    text = " ".join(f"A cable between {a} and {b} would cost {w}." for a, b, w in cables)
    sa = lambda xs: ", ".join(xs[:-1]) + " and " + xs[-1]  # noqa: E731
    q = (f"The towns {sa(sorted(towns))} must be joined by cables so that anyone can get from any town to any other town, directly or through other towns. {text} "
         "What is the smallest total cost of a set of cables that joins all the towns?")
    return Built(q, {"towns": towns, "cables": cables}, str(ans), "number", None)


@rev2("dynprog")
def max_subarray_sum(level: int, r: random.Random) -> Built:
    """Procedure: best-ending-here scan. structured: {"xs": [int]}. Batch-1 rejection on (largest, sum of positives, total) REMOVED. By construction the row is built from runs of positive numbers separated by
    strongly negative numbers (-20..-12), and the planted best block is two positive runs joined across ONE small dip (the dip is smaller than both runs' sums), so the best block contains a negative number
    and 'the best run of non-negative numbers' cannot be it; decoy runs of one or two numbers (1..5) are placed on either side, so the planted block (at least 16) always wins. Answer: the largest sum of a block of neighbouring numbers (computed from the row, not from the plan)."""
    def run(k: int, lo: int, hi: int) -> list[int]:
        return [r.randint(lo, hi) for _ in range(k)]

    a, b = run(3, 5, 9), run(3, 5, 9)
    dip = -r.randint(1, min(sum(a), sum(b)) - 1)
    planted = [*a, dip, *b]
    decoys = [run(r.randint(1, 2), 1, 5) for _ in range(1 + level // 2)]
    blocks = [planted, *decoys]
    r.shuffle(blocks)
    xs: list[int] = []
    for blk in blocks:
        xs += [-r.randint(12, 20) for _ in range(r.randint(1, 2))] + blk
    xs += [-r.randint(12, 20) for _ in range(r.randint(1, 2))]
    best, cur = xs[0], xs[0]
    for x in xs[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    q = f"Pick a block of one or more numbers that sit next to each other in this row (no gaps). What is the largest total a block can have? Row: {lst(xs)}."
    return Built(q, {"xs": xs}, str(best), "number", None)


@rev2("numtheory", supersedes="R2.gcd_euclid")
def gcd_euclid(level: int, r: random.Random) -> Built:
    """Procedure: Euclid's remainder algorithm. structured: {"a": int, "b": int, "ask": "gcd" | "lcm"}. The `steps` shape is DROPPED (its answers sit in a narrow range, the constant 3 scored 0.27-0.38).
    By construction the common divisor g has no prime factor below 11 (so 'the product of the common small primes' is always 1), and the cofactors p, q are coprime and not within 1 of each other."""
    lo = 11
    hi_g = 60 + 30 * level
    pool = [g for g in range(lo, hi_g + 1) if all(g % d for d in range(2, 11))]
    g = r.choice(pool)
    hi = 60 + 30 * level
    p, q2 = r.randint(2, hi), r.randint(2, hi)
    import math

    if abs(p - q2) < 2 or math.gcd(p, q2) != 1:
        raise Retry
    a, b = g * max(p, q2), g * min(p, q2)
    if r.random() < 0.5:
        return Built(f"What is the greatest common divisor of {a} and {b}?", {"a": a, "b": b, "ask": "gcd"}, str(g), "number", None)
    return Built(f"What is the least common multiple of {a} and {b}?", {"a": a, "b": b, "ask": "lcm"}, str(a * b // g), "number", None)


@rev2("numtheory", supersedes="R2.modular_power")
def modular_power(level: int, r: random.Random) -> Built:
    """Procedure: repeated squaring modulo m. structured: {"a": int, "e": int, "m": int}. Batch-1 rejection of answers 0, 1 and a REMOVED. By construction m is a product of two different primes (so
    reductions that need a prime modulus, such as Fermat's, are not valid shortcuts), m >= 35 at level 0, and e is at least 2m (so e mod (m-1) is a genuine reduction and a^2 mod m is not the answer except by chance)."""
    ps = (5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    pr = ps[: 5 + level]
    p, q2 = r.sample(pr, 2)
    m = p * q2
    a = r.randint(2, m - 1)
    e = r.randint(2 * m, 2 * m + 150 + 60 * level)
    q = f"Multiply together {e} copies of the number {a} (a product with {e} factors, each equal to {a}). What is the remainder when this product is divided by {m}?"
    return Built(q, {"a": a, "e": e, "m": m}, str(pow(a, e, m)), "number", None)


def _lcs(a: str, b: str) -> int:
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ca == cb else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


@rev2("dynprog")
def lcs_length(level: int, r: random.Random) -> Built:
    """Procedure: two-string prefix table. structured: {"a": str, "b": str}. By construction a common subsequence of length k (k uniform from 2 to the shorter length minus 2) is PLANTED, so the answer
    (>= k, computed by the table, not from the plan) does not follow the letter-count overlap or the string lengths; alphabet size 4..6 and lengths 8+level..14+2*level are drawn per item."""
    alpha = "abcdef"[: r.randint(4, 6)]
    na, nb = r.randint(8 + level, 14 + 2 * level), r.randint(8 + level, 14 + 2 * level)
    k = r.randint(2, min(na, nb) - 2)
    a = [r.choice(alpha) for _ in range(na)]
    b = [r.choice(alpha) for _ in range(nb)]
    ia, ib = sorted(r.sample(range(na), k)), sorted(r.sample(range(nb), k))
    for x, y in zip(ia, ib, strict=True):
        b[y] = a[x]
    sa, sb = "".join(a), "".join(b)
    q = ("A subsequence of a string is what is left after deleting zero or more of its letters, with the remaining letters kept in their original order (the letters need not be next to each other). "
         f"What is the length of the longest string that is a subsequence of both '{sa}' and '{sb}'?")
    return Built(q, {"a": sa, "b": sb}, str(_lcs(sa, sb)), "number", None)


def _lis(xs: list[int]) -> int:
    best = [1] * len(xs)
    for i in range(len(xs)):
        for j in range(i):
            if xs[j] < xs[i]:
                best[i] = max(best[i], best[j] + 1)
    return max(best)


@rev2("dynprog")
def lis_length(level: int, r: random.Random) -> Built:
    """Procedure: longest strictly increasing subsequence. structured: {"xs": [int]} (distinct). By construction an increasing subsequence of length k (k uniform from 3 to n-3) is PLANTED by sorting the values at k random positions of a random row (the other numbers stay random), so the answer (at least k, computed by the DP, not from the plan) is spread over a wide range and does not follow 2*sqrt(n); n is drawn from 9+level..18+3*level."""
    n = r.randint(9 + level, 18 + 3 * level)
    k = r.randint(3, n - 3)
    xs = r.sample(range(1, 10 * n), n)
    pos = sorted(r.sample(range(n), k))
    vals = sorted(xs[i] for i in pos)
    for i, v in zip(pos, vals, strict=True):
        xs[i] = v  # the values at the planted positions are put in increasing order; every other position keeps its random value
    q = ("Choose some of these numbers, keeping the order in which they are written, so that each chosen number is larger than the one chosen before it (the chosen numbers need not be next to each other). "
         f"What is the largest count of numbers you can choose? Numbers: {lst(xs)}.")
    return Built(q, {"xs": xs}, str(_lis(xs)), "number", None)


def _longest_pal(s: str) -> int:
    best = 1
    for c in range(len(s)):
        for lo, hi in ((c, c), (c, c + 1)):
            while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
                lo -= 1
                hi += 1
            best = max(best, hi - lo - 1)
    return best


@rev2("strings")
def longest_palindromic_substring(level: int, r: random.Random) -> Built:
    """Procedure: expand around each centre. structured: {"s": str}. By construction a palindrome of length uniform from 3 to 12 is planted in a string of 16+2*level letters (batch 1: 3..7+level in 14+2*level),
    so the answer is spread over about ten values. The answer is computed from the string."""
    alpha = "abc" if level <= 2 else "abcd"
    n = 16 + 2 * level
    s = "".join(r.choice(alpha) for _ in range(n))
    plant = r.randint(3, 12)
    half = "".join(r.choice(alpha) for _ in range(plant // 2))
    pal = half + (r.choice(alpha) if plant % 2 else "") + half[::-1]
    at = r.randint(0, n - plant)
    s = s[:at] + pal + s[at + plant :]
    q = f"Look at the string '{s}'. Find the longest block of letters, all next to each other in the string, that reads the same forwards and backwards. How many letters long is it?"
    return Built(q, {"s": s}, str(_longest_pal(s)), "number", None)


_PR = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97)


@rev2("numtheory", supersedes="R2.prime_factor_query")
def prime_factor_query(level: int, r: random.Random) -> Built:
    """Procedure: trial-division factorisation. structured: {"n": int, "ask": "largest" | "sum_all"}. By construction the LARGEST prime factor is drawn uniformly from the primes 17..(pool maximum: 61 at level 0, 97 after; 4 to 6 prime factors, widened for capacity),
    one prime up to it is used TWICE (so 'the sum of the different primes' is never the sum asked), and the other factors are drawn uniformly from the primes up to it (batch 1 drew all factors from the pool, so the largest sat at the top of the pool: constant 0.17-0.21). Answer: the largest prime factor, or the sum of the primes in the
    factorisation counting repeats."""
    k = (4, 5, 5, 5, 5, 5, 6)[level]
    pool = _PR[: 18] if level == 0 else _PR
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


@rev2("numtheory")
def crt_smallest(level: int, r: random.Random) -> Built:
    """Procedure: combine congruences with coprime moduli. structured: {"congruences": [[remainder, modulus]]}. Same shape as batch 1 with wider moduli (3..30+10*level) so that the structure count meets the demand
    at the G written (batch 1: 1,212 and 2,215 distinct structures at levels 0 and 1). Answer: the smallest positive whole number with all the stated remainders (unique, at most the product of the moduli)."""
    import math

    k = 2 if level <= 2 else 3
    ms = sorted(r.sample(range(3, 30 + 10 * level), k))
    if any(math.gcd(ms[i], ms[j]) != 1 for i in range(k) for j in range(i + 1, k)):
        raise Retry
    x = r.randint(1, math.prod(ms))
    cons = [[x % m, m] for m in ms]
    parts = [f"leaves remainder {c} when divided by {m}" for c, m in cons]
    return Built("What is the smallest positive whole number that " + ", and ".join(parts) + "?", {"congruences": cons}, str(x), "number", None)
