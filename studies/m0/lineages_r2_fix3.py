# ruff: noqa: E501
"""R2, fix round 3 (human-authorised bounded round after AUDIT3_R2 and LEAD_RULINGS_2/3; no new lineages, nothing in ``core.REGISTRY``).

Revised SHAPES of lineages already on file (same ids ``R2.<name>``), in their own registry ``FIX3``. They supersede the shapes of earlier rounds that are listed in ``SUPERSEDES``;
earlier shapes stay on file untouched. Method (R-1 and R-13): a tell is removed BY CONSTRUCTION, never by redrawing items conditional on a heuristic's outcome and never with a
probability fitted to a heuristic. A ``Retry`` is used only for validity (a stated uniqueness or a stated bound). Lineages that cannot be freed of a tell are listed in
``NOT_REGISTERED`` with the reason. The shortcut bound is the lead's working target (every cheap rule within 0.10 of its base rate, two-sided) and is NOT a registered number.
Self-checked only: not independent review, not Astra validation, not human approval.

This module holds registry helpers and the first group of shapes (greedy, search, structures, dynamics, combinatorics, rle); the others are in ``lineages_r2_fix3_b.py`` and ``_c.py``.
"""

from __future__ import annotations

import math
import random
import string
from collections.abc import Callable

from studies.m0.core import Built, Lineage
from studies.m0.lineages_r2_common import lst

FIX3: list[Lineage] = []
SUPERSEDES: dict[str, str] = {}
# reporting family of each id (the families of the shapes they supersede; the batch-1 'numtheory' is renamed as in the earlier rounds)
Builder = Callable[[int, random.Random], Built]


def fix3(family: str, supersedes: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R2.{fn.__name__}"
        if any(x.id == lid for x in FIX3):
            raise ValueError(f"duplicate {lid}")
        FIX3.append(Lineage(lid, "R2", family, fn))
        SUPERSEDES[lid] = supersedes
        return fn

    return deco


def load_fix3() -> list[Lineage]:
    import studies.m0.lineages_r2_fix3_b  # noqa: F401
    import studies.m0.lineages_r2_fix3_c  # noqa: F401

    return sorted(FIX3, key=lambda x: x.id)


# ---------------------------------------------------------------- greedy


def _pick_earliest_finish(iv: list[list[int]]) -> list[int]:
    """1-based numbers of the meetings chosen by: repeatedly take, among the meetings that do not clash with the chosen ones, the one that ends first (ties: smaller number)."""
    taken: list[int] = []
    for i in sorted(range(len(iv)), key=lambda i: (iv[i][1], i)):
        a, b = iv[i]
        if all(b <= iv[j][0] or a >= iv[j][1] for j in taken):
            taken.append(i)
    return sorted(i + 1 for i in taken)


@fix3("greedy", "R2.interval_scheduling")
def interval_scheduling(level: int, r: random.Random) -> Built:
    """Procedure: pick by earliest finish time (activity selection). structured: {"meetings": [[start, end]], "ask": "chosen"} (integer times, start < end).
    R-1: the batch-1 redraw on 'earliest start' and 'shortest first' is removed, and so is the count answer (a small number: the constant guess read 0.2-0.35 whatever the construction). By construction
    the day is made of 5 + level//2 independent BLOCKS of 4-6 meetings, each in its own time window (windows 24 minutes apart; a meeting starts 0-12 minutes into its window and lasts 2-9, so none touches another block), the meetings are numbered in a shuffled order,
    and the answer is the LIST of the chosen meetings' numbers: a rule that errs in one block errs on the item, and nothing is drawn conditional on what any rule gives.
    Answer: the numbers of the meetings the stated earliest-finish rule chooses (ties in finishing minute: the smaller number), smallest number first."""
    nb = 5 + level // 2
    iv: list[list[int]] = []
    for b in range(nb):
        for _ in range(r.randint(4, 6)):
            s = 24 * b + r.randint(0, 12)
            iv.append([s, s + r.randint(2, 9)])
    r.shuffle(iv)
    text = "; ".join(f"meeting {i + 1} runs from {s} to {e}" for i, (s, e) in enumerate(iv))
    q = (f"A person can attend only one meeting at a time. Times are whole numbers of minutes: {text}. Two meetings clash if they share any stretch of time; "
         "a meeting that ends at the very minute another starts does not clash with it. The person chooses meetings in rounds: in each round, among the meetings that do not clash with any meeting already chosen, "
         "the one that ends first is chosen (if two end at the same minute, the one with the smaller number); rounds go on until no meeting can be added. "
         "Which meetings are chosen? Give their numbers, smallest first, separated by commas.")
    return Built(q, {"meetings": iv, "ask": "chosen"}, lst(_pick_earliest_finish(iv)), "list", None)


# ---------------------------------------------------------------- search


def _probe_positions(xs: list[int], target: int) -> list[int]:
    lo, hi = 1, len(xs)
    seen = []
    while lo <= hi:
        mid = (lo + hi) // 2
        seen.append(xs[mid - 1])
        if xs[mid - 1] == target:
            break
        if target < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return seen


@fix3("search", "R2.binary_search_trace")
def binary_search_trace(level: int, r: random.Random) -> Built:
    """Procedure: binary search with middle = floor((low+high)/2). structured: {"xs": [int] (ascending, distinct), "target": int, "ask": "values" | "sum"}.
    R-1: the batch-1 redraw on 'the third look is the target' is removed together with the `third` shape (its answer is one of four values near fixed fractions of the list, a 'position rule' read 0.2-0.3 whatever the construction).
    The list is longer (16+4*level .. +3 numbers; a length of 2^k - 1 is stepped over, because there the roundings up and down give the same search) so that the look sequence is long and the numbers it visits are spread.
    The target is in the list on a fair coin and otherwise a number that is not in it. Answer: the numbers looked at in order (comma list), or their sum."""
    n = 16 + 4 * level + r.randint(0, 3)
    if n in (31, 63):
        n += 1
    xs = sorted(r.sample(range(1, 4 * n), n))
    if r.random() < 0.5:
        target = r.choice(xs)
    else:
        absent = sorted(set(range(1, 4 * n)) - set(xs))
        target = r.choice(absent)
    seen = _probe_positions(xs, target)
    ask = r.choice(("values", "sum"))
    head = (f"A sorted list of {n} numbers (smallest first) is searched for {target}. The positions are numbered 1 to {n}. The search keeps a lower position (first 1) and an upper position (first {n}). "
            "Each round it looks at the number in the position halfway between them, rounded down when needed (the sum of the two positions divided by 2, rounded down). If that number is the target the search stops; "
            "if the target is smaller, the upper position becomes one less than the position just looked at; otherwise the lower position becomes one more. If the lower position ever exceeds the upper position the search stops, having found nothing. "
            f"The list: {lst(xs)}. ")
    if ask == "values":
        return Built(head + "Which numbers does the search look at, in order? Give them separated by commas.", {"xs": xs, "target": target, "ask": "values"}, lst(seen), "list", None)
    return Built(head + "What is the sum of all the numbers the search looks at (a number looked at twice would count twice)?", {"xs": xs, "target": target, "ask": "sum"}, str(sum(seen)), "number", None)


# ---------------------------------------------------------------- structures


def _bst_walk(xs: list[int], kind: str) -> list[int]:
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
    out: list[int] = []
    if kind == "level":
        row = [xs[0]]
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

    go(xs[0])
    return out


@fix3("structures", "R2.bst_traversal")
def bst_traversal(level: int, r: random.Random) -> Built:
    """Procedure: binary-search-tree insertion then a tree walk. structured: {"xs": [int] (distinct, inserted in this order), "kind": "pre" | "post" | "level"}.
    R-1: the batch-1 rejection of answers equal to the insertion order or the sorted order is REMOVED. By construction n is 8 + level (batch 1: 5 + level): for a random order the chance that a
    walk equals the insertion order is the Catalan number over n! (0.035 at n = 8, under 0.001 at n = 11), so no exclusion is needed. Answer: the numbers in that walk order, as a comma list."""
    n = 8 + level
    xs = r.sample(range(1, 100), n)
    kind = r.choice(("pre", "post", "level"))
    walk = {
        "pre": "Read the tree like this: write a number, then everything in its left branch, then everything in its right branch (applied the same way inside each branch).",
        "post": "Read the tree like this: write everything in a number's left branch, then everything in its right branch, then the number itself (applied the same way inside each branch).",
        "level": "Read the tree like this: write the top number, then the numbers one step below it from left to right, then the numbers two steps below it from left to right, and so on.",
    }[kind]
    q = (f"Numbers are put one at a time into a tree. The first number is the top of the tree. Every later number starts at the top and moves down: at each number it meets, it goes to the left if it is smaller and to the right if it is larger, "
         f"and it stays in the first empty place it reaches. The numbers are put in this order: {lst(xs)}. {walk} Give the numbers in that reading order, separated by commas.")
    return Built(q, {"xs": xs, "kind": kind}, lst(_bst_walk(xs, kind)), "list", None)


def _heap_insert(h: list[int], x: int) -> None:
    h.append(x)
    i = len(h)
    while i > 1 and h[i - 1] < h[i // 2 - 1]:
        h[i - 1], h[i // 2 - 1] = h[i // 2 - 1], h[i - 1]
        i //= 2


def _heap_pop(h: list[int]) -> None:
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


@fix3("structures", "R2.min_heap_ops")
def min_heap_ops(level: int, r: random.Random) -> Built:
    """Procedure: array binary min-heap with sift-up insertion and sift-down removal. structured: {"xs": [int] (distinct, inserted in order), "removals": int}.
    R-1: the batch-1 rejection of answers equal to the insertion order or sorted is REMOVED. By construction n is 10 + level (batch 1: 5 + level): the chance that a random order is already a heap
    is about 0.005 at n = 8, and building the heap by sifting up differs from Floyd's whole-row method (which the audit lists as a valid alternative) in most orders. Answer: the array (positions 1..) after the inserts and the removals."""
    n = 10 + level
    xs = r.sample(range(1, 100), n)
    rem = r.choice((0, 0, 1, 2)) if level >= 3 else r.choice((0, 0, 1))
    h: list[int] = []
    for x in xs:
        _heap_insert(h, x)
    for _ in range(rem):
        _heap_pop(h)
    q = ("A heap is a row of numbers in positions 1, 2, 3, ... where the number in position p is never larger than the numbers in positions 2p and 2p+1 (when those exist). "
         "To add a number: put it in the first free position at the end, then, while it is smaller than the number in position (its position divided by 2, rounded down), swap the two. "
         "To remove the smallest: take out the number in position 1, put the number from the last position into position 1 (the row is now one shorter), then, while it is larger than the smaller of the numbers in positions 2p and 2p+1 (those that exist), swap it with that smaller number. "
         f"Start with an empty heap and add these numbers in order: {lst(xs)}."
         + (f" Then remove the smallest {rem} time{'s' if rem > 1 else ''}." if rem else "")
         + " Give the row from position 1 to the end, separated by commas.")
    return Built(q, {"xs": xs, "removals": rem}, lst(h), "list", None)


# ---------------------------------------------------------------- dynamics


def _ca_step(row: list[int], table: dict[str, int]) -> list[int]:
    n = len(row)
    return [table[f"{row[i - 1] if i > 0 else 0}{row[i]}{row[i + 1] if i < n - 1 else 0}"] for i in range(n)]


@fix3("dynamics", "R2.cellular_automaton")
def cellular_automaton(level: int, r: random.Random) -> Built:
    """Procedure: synchronous three-neighbour table update. structured: {"row": [0|1], "table": {"LCR": 0|1} (all 8 triples), "steps": int, "ask": "row"}.
    R-1: the batch-1 rejections (final row equal to the start, all-equal final row, table with 000 -> 1) are REMOVED. By construction the row is 11 + 2*level cells whose two END cells are 1 (so the
    rule that a periodic edge would give differs from the stated zero edge at the first step with chance 1/2 per end), there are 2 + level//2 steps (batch 1: 1 + level//2, 4 at level 6), the `count` shape
    (a handful of answers, 0.24 constant) is dropped, the table has 64 free choices once the mirror-image pairs are tied, so the row is 11 cells at level 0 for capacity (9 cells gave 8,117 different items), the values of the mirror-image triples 100/001 and 110/011 are drawn different (by construction: the right-to-left misreading of the table then always changes the rule) and the only table excluded is a constant one (a table that ignores its input; validity, not a shortcut gate). Answer: the row after the steps as 0/1 digits."""
    n = 11 + 2 * level
    row = [1, *(r.randint(0, 1) for _ in range(n - 2)), 1]
    keys = [f"{a}{b}{c}" for a in (1, 0) for b in (1, 0) for c in (1, 0)]
    table = {k: r.randint(0, 1) for k in keys}
    table["001"] = 1 - table["100"]  # by construction the two mirror-image pairs of triples give different values, so a reader who takes the neighbours in the other order is wrong
    table["011"] = 1 - table["110"]
    from studies.m0.core import Retry

    if len(set(table.values())) < 2:
        raise Retry
    steps = 2 + level // 2
    cur = row
    for _ in range(steps):
        cur = _ca_step(cur, table)
    tt = ", ".join(f"{k} becomes {table[k]}" for k in keys)
    q = (f"A row of {n} cells holds 0s and 1s: {''.join(map(str, row))}. In one step every cell changes at the same moment, according to the three digits (left neighbour, the cell itself, right neighbour): {tt}. "
         f"The cells beyond the two ends of the row count as 0. After {steps} steps, what does the row look like? Give the digits with no spaces.")
    return Built(q, {"row": row, "table": table, "steps": steps, "ask": "row"}, "".join(map(str, cur)), "text", None)


# ---------------------------------------------------------------- combinatorics


def _falling(a: int, b: int) -> int:
    """a (a-1) ... (a-b+1)."""
    return math.perm(a, b) if 0 <= b <= a else 0


def _unrank_partial(letters: list[str], length: int, k: int) -> str:
    pool = sorted(letters)
    m = len(pool)
    k -= 1
    out = []
    for i in range(length):
        f = _falling(m - i - 1, length - i - 1)
        out.append(pool.pop(k // f))
        k %= f
    return "".join(out)


def _rank_partial(letters: list[str], word: str) -> int:
    pool = sorted(letters)
    m, length = len(pool), len(word)
    k = 0
    for i, ch in enumerate(word):
        j = pool.index(ch)
        k += j * _falling(m - i - 1, length - i - 1)
        pool.pop(j)
    return k + 1


# (length of the word, alphabet sizes drawn uniformly) per level: a word of `length` different letters taken from an alphabet of m letters
_DR_PLAN = {0: (4, (9, 10, 11)), 1: (4, (9, 10, 11, 12)), 2: (5, (7, 8, 9)), 3: (5, (8, 9, 10)), 4: (6, (8, 9, 10)), 5: (6, (9, 10, 11)), 6: (7, (9, 10, 11))}


@fix3("combinatorics", "R2.dictionary_rank")
def dictionary_rank(level: int, r: random.Random) -> Built:
    """Procedure: mixed-radix ranking/unranking of words of different letters in dictionary order. structured: {"letters": [str] (sorted), "length": int, "ask": "word" | "position", "k": int or null, "word": str or null}.
    Widened for capacity under the reading in which letters are relabelled (reading b of the fix round): the words have `length` different letters TAKEN FROM a larger alphabet (batch 1: arrangements of all the letters,
    only 24-5,040 different structures), the alphabet size is drawn per item. R-1: the batch-1 redraw on rank 1 or last is removed (it is a negligible chance here). Answer, word: the word at position k (2 .. last - 1); position: the number of `word`."""
    length, sizes = _DR_PLAN[level]
    m = r.choice(sizes)
    letters = sorted(r.sample(string.ascii_lowercase, m))
    total = _falling(m, length)
    pre = (f"Write every word of {length} letters that can be made from the letters {', '.join(letters)} when no letter is used twice in the same word, and list all the words in dictionary order "
           "(as in a dictionary, comparing letter by letter from the left, with a before b before c and so on). Number the words 1, 2, 3, ... in that list. ")
    if r.random() < 0.6:
        k = r.randint(2, total - 1)
        w = _unrank_partial(letters, length, k)
        return Built(pre + f"Which word has number {k}?", {"letters": letters, "length": length, "ask": "word", "k": k, "word": None}, w, "text", None)
    w = "".join(r.sample(letters, length))
    return Built(pre + f"What is the number of the word {w}?", {"letters": letters, "length": length, "ask": "position", "k": None, "word": w}, str(_rank_partial(letters, w)), "number", None)


# ---------------------------------------------------------------- rle


@fix3("rle", "R2.run_length")
def run_length(level: int, r: random.Random) -> Built:
    """Procedure: run-length encoding. structured: {"s": str}. Widened for capacity under the reading in which letters are relabelled (reading b): 6 + level runs of length 1 .. 4 + level//2 (batch 1: 3 + level runs of
    length 1 .. 3 + level, only 54 different letter-blind structures at level 0). Each run's letter is drawn from the six letters other than the previous run's, so every run is maximal by construction (no redraw).
    Answer: each maximal run as the letter followed by its length."""
    runs: list[tuple[str, int]] = []
    prev = ""
    for _ in range(6 + level):
        c = r.choice([x for x in "abcxyz" if x != prev])
        runs.append((c, r.randint(1, 4 + level // 2)))
        prev = c
    s = "".join(c * k for c, k in runs)
    ans = "".join(f"{c}{k}" for c, k in runs)
    q = f"Compress {s} by run-length encoding: replace each maximal run of one repeated letter by the letter followed by the run length (for example aaab becomes a3b1). What is the result?"
    return Built(q, {"s": s}, ans, "text", None)
