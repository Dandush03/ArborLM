# ruff: noqa: E501
"""R2 batch 1, family "structures": operations on a stated data structure whose rule is NOT a plain list edit (binary search tree,
binary heap, cache with an eviction rule, open-addressing hash table). Each is a different structure with a different invariant."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1, lst, until
from studies.m0.vocab import OBJECTS


def bst_build(xs: list[int]) -> dict[int, list[int | None]]:
    """node -> [left, right]; the first number is the root."""
    kids: dict[int, list[int | None]] = {xs[0]: [None, None]}
    for x in xs[1:]:
        cur = xs[0]
        while True:
            side = 0 if x < cur else 1
            nxt = kids[cur][side]
            if nxt is None:
                kids[cur][side] = x
                kids[x] = [None, None]
                break
            cur = nxt
    return kids


def bst_order(xs: list[int], kind: str) -> list[int]:
    kids = bst_build(xs)
    root = xs[0]
    out: list[int] = []
    if kind == "level":
        row: list[int] = [root]
        while row:
            out.extend(row)
            row = [c for v in row for c in kids[v] if c is not None]
        return out

    def go(v: int | None) -> None:
        if v is None:
            return
        if kind == "pre":
            out.append(v)
        go(kids[v][0])
        go(kids[v][1])
        if kind == "post":
            out.append(v)

    go(root)
    return out


@batch1("structures")
def bst_traversal(level: int, r: random.Random) -> Built:
    """Procedure: binary-search-tree insertion then a tree walk. structured: {"xs": [int] (distinct, inserted in this order), "kind": "pre" | "post" | "level"}.
    Answer: the numbers in that walk order, as a comma list. Rejected when the answer equals the insertion order or the sorted order."""
    n = 5 + level
    xs = r.sample(range(1, 100), n)
    kind = r.choice(("pre", "post", "level"))
    ans = bst_order(xs, kind)
    if ans == xs or ans == sorted(xs):
        raise Retry
    walk = {
        "pre": "Read the tree like this: write a number, then everything in its left branch, then everything in its right branch (applied the same way inside each branch).",
        "post": "Read the tree like this: write everything in a number's left branch, then everything in its right branch, then the number itself (applied the same way inside each branch).",
        "level": "Read the tree like this: write the top number, then the numbers one step below it from left to right, then the numbers two steps below it from left to right, and so on.",
    }[kind]
    q = (f"Numbers are put one at a time into a tree. The first number is the top of the tree. Every later number starts at the top and moves down: at each number it meets, it goes to the left if it is smaller and to the right if it is larger, "
         f"and it stays in the first empty place it reaches. The numbers are put in this order: {lst(xs)}. {walk} Give the numbers in that reading order, separated by commas.")
    return Built(q, {"xs": xs, "kind": kind}, lst(ans), "list", None)


def heap_insert(h: list[int], x: int) -> None:
    h.append(x)
    i = len(h)
    while i > 1 and h[i - 1] < h[i // 2 - 1]:
        h[i - 1], h[i // 2 - 1] = h[i // 2 - 1], h[i - 1]
        i //= 2


def heap_pop(h: list[int]) -> None:
    h[0] = h[-1]
    h.pop()
    i, n = 1, len(h)
    while 2 * i <= n:
        c = 2 * i
        if c + 1 <= n and h[c] < h[c - 1]:
            c += 1
        if h[c - 1] < h[i - 1]:
            h[c - 1], h[i - 1] = h[i - 1], h[c - 1]
            i = c
        else:
            break


@batch1("structures")
def min_heap_ops(level: int, r: random.Random) -> Built:
    """Procedure: array binary min-heap with sift-up insertion and sift-down removal. structured: {"xs": [int] (distinct, inserted in order), "removals": int}.
    Answer: the array (positions 1..n) after the inserts and then `removals` removals of the smallest. Rejected when the answer is the insertion order or sorted."""
    n = 5 + level
    xs = r.sample(range(1, 100), n)
    rem = r.choice((0, 0, 1, 2)) if level >= 3 else r.choice((0, 0, 1))
    h: list[int] = []
    for x in xs:
        heap_insert(h, x)
    for _ in range(rem):
        heap_pop(h)
    if h == xs[: len(h)] or h == sorted(h):
        raise Retry
    q = ("A heap is a row of numbers in positions 1, 2, 3, ... where the number in position p is never larger than the numbers in positions 2p and 2p+1 (when those exist). "
         "To add a number: put it in the first free position at the end, then, while it is smaller than the number in position (its position divided by 2, rounded down), swap the two. "
         "To remove the smallest: take out the number in position 1, put the number from the last position into position 1 (the row is now one shorter), then, while it is larger than the smaller of the numbers in positions 2p and 2p+1 (those that exist), swap it with that smaller number. "
         f"Start with an empty heap and add these numbers in order: {lst(xs)}."
         + (f" Then remove the smallest {rem} time{'s' if rem > 1 else ''}." if rem else "")
         + " Give the row from position 1 to the end, separated by commas.")
    return Built(q, {"xs": xs, "removals": rem}, lst(h), "list", None)


def cache_run(seq: list[str], cap: int, policy: str) -> tuple[int, list[str]]:
    """returns (misses, contents ordered from first-to-leave to last-to-leave)."""
    cache: list[str] = []
    miss = 0
    for x in seq:
        if x in cache:
            if policy == "lru":
                cache.remove(x)
                cache.append(x)
        else:
            miss += 1
            if len(cache) == cap:
                cache.pop(0)
            cache.append(x)
    return miss, cache


@batch1("structures")
def cache_eviction(level: int, r: random.Random) -> Built:
    """Procedure: cache with an eviction rule. structured: {"cap": int, "seq": [item], "policy": "lru" | "fifo", "ask": "misses" | "present", "item": item or null}.
    A request for an item already in the cache is a hit; otherwise it is a miss, the item is loaded and, if the cache is full, the victim is removed first.
    lru: the victim is the item whose last request is oldest; fifo: the item loaded longest ago (a hit changes nothing). Answer: the number of misses (never the number of distinct items nor the other policy's count), or yes/no whether `item` is in the cache at the end (balanced 50/50, and "among the last cap requests" is right in about half the items)."""
    cap = r.randint(2, 3 + level // 3)
    pool = r.sample(OBJECTS, cap + 2 + level // 2)
    policy = r.choice(("lru", "fifo"))
    ask_misses = r.random() < 0.5
    want_yes = r.random() < 0.5
    agree = r.random() < 0.5 or (policy == "lru" and not want_yes)  # does "in the last cap requests" give the right answer?
    other = "fifo" if policy == "lru" else "lru"

    def make() -> tuple[list[str], str]:
        return [r.choice(pool) for _ in range(10 + 2 * level + r.randint(0, 3))], r.choice(pool)

    def ok(sx: tuple[list[str], str]) -> bool:
        s, x = sx
        miss, cache = cache_run(s, cap, policy)
        if ask_misses:
            # not the number of distinct items and not the other policy's count
            return miss not in (len(set(s)), cache_run(s, cap, other)[0])
        return (x in cache) == want_yes and ((x in s[-cap:]) == (x in cache)) == agree

    seq, x = until(300, make, ok)
    miss, cache = cache_run(seq, cap, policy)
    rule = ("the item that was requested longest ago (counting its latest request) is removed to make room" if policy == "lru"
            else "the item that was loaded into the cache longest ago is removed to make room (a hit does not change the order)")
    head = (f"A cache holds at most {cap} items and starts empty. Items are requested one after another. If the requested item is already in the cache nothing is removed; "
            f"if it is not, it is put into the cache, and if the cache was full {rule}. Requests in order: {', '.join(seq)}. ")
    if ask_misses:
        return Built(head + "How many requests found the item missing from the cache?", {"cap": cap, "seq": seq, "policy": policy, "ask": "misses", "item": None}, str(miss), "number", None)
    ans = "yes" if x in cache else "no"
    return Built(head + f"After the last request, is {x} in the cache? Answer yes or no.", {"cap": cap, "seq": seq, "policy": policy, "ask": "present", "item": x}, ans, "yn", 2)


def hash_table(keys: list[int], m: int) -> tuple[list[int | None], dict[int, int]]:
    table: list[int | None] = [None] * m
    slot_of: dict[int, int] = {}
    for k in keys:
        s = k % m
        while table[s] is not None:
            s = (s + 1) % m
        table[s] = k
        slot_of[k] = s
    return table, slot_of


@batch1("structures")
def hash_probe(level: int, r: random.Random) -> Built:
    """Procedure: open-addressing hash table with linear probing. structured: {"m": int, "keys": [int] (distinct, inserted in order), "ask": "slot" | "probes", "target": int}.
    Slot of a key = key mod m, then the next slot, wrapping from m-1 to 0, until free. Answer: the slot where `target` ends up, or the number of slots looked at when the LAST key was inserted (including the free slot).
    About 80% of the `slot` questions ask about a key that is not in its home slot, and about 80% of the `probes` questions have a last key that is not in its home slot."""
    m = 7 + level
    n = max(4, (m * 6) // 10)
    ask_slot = r.random() < 0.75
    displaced_wanted = r.random() < 0.8

    def good(ks: list[int]) -> bool:
        sl = hash_table(ks, m)[1]
        return bool([k for k in ks if sl[k] != k % m]) and (ask_slot or (sl[ks[-1]] != ks[-1] % m) == displaced_wanted)

    keys = until(300, lambda: r.sample(range(10, 100), n), good)
    table, slot_of = hash_table(keys, m)
    moved = [k for k in keys if slot_of[k] != k % m]
    x = r.choice(moved) if displaced_wanted else r.choice(keys)
    head = (f"A table has {m} slots numbered 0 to {m - 1}. A number goes into the slot whose number is the remainder of the number divided by {m}; "
            f"if that slot is taken, it goes into the next slot up (slot {m - 1} is followed by slot 0), and so on until a free slot is found. Numbers are added in this order: {lst(keys)}. ")
    if ask_slot:
        return Built(head + f"In which slot does {x} end up?", {"m": m, "keys": keys, "ask": "slot", "target": x}, str(slot_of[x]), "number", None)
    last = keys[-1]
    probes = (slot_of[last] - last % m) % m + 1
    return Built(head + f"When {last} (the last number) is added, how many slots are looked at, counting the slot where it is finally placed?", {"m": m, "keys": keys, "ask": "probes", "target": last}, str(probes), "number", None)
