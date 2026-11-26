# ruff: noqa
"""Final R2 audit (M0-R2, fix 4): an independent second solver that reads ONLY the question text.
Written by the final auditor from rendered sample texts (f_render.out, f_shapes.out, f_phrases.out); it imports nothing from studies.m0
and does not reuse any generator, implementer or earlier-auditor solver. Standard library only.
solve(name, question) -> (answer_string, flags) ; flags is a list of strings naming wording problems found while solving
(e.g. 'no_solution', 'heap_child_tie', 'disconnected'), used by the wording check."""
import re
from itertools import permutations
from math import gcd

NUM = r"-?\d+"


def _ints(s):
    return [int(x) for x in re.findall(NUM, s)]


def binary_search_trace(q):
    n = int(re.search(r"A sorted list of (\d+) numbers", q).group(1))
    target = int(re.search(r"is searched for (-?\d+)\.", q).group(1))
    xs = _ints(re.search(r"The list: ([^A-Za-z]*?)\. (Which|What)", q).group(1))
    assert len(xs) == n, (len(xs), n)
    lo, hi = 1, n
    seen = []
    while lo <= hi:
        mid = (lo + hi) // 2
        v = xs[mid - 1]
        seen.append(v)
        if v == target:
            break
        if target < v:
            hi = mid - 1
        else:
            lo = mid + 1
    if "What is the sum" in q:
        return str(sum(seen)), []
    assert "Which numbers does the search look at" in q
    return ", ".join(str(v) for v in seen), []


def caesar_shift(q):
    m = re.search(r"Shift every letter of '([^']*)' (forward|backward) by (\d+) places", q)
    text, d, k = m.group(1), m.group(2), int(m.group(3))
    if d == "backward":
        k = -k
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + k) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out), []


def cellular_automaton(q):
    row = re.search(r"holds 0s and 1s: ([01]+)\.", q).group(1)
    n = int(re.search(r"A row of (\d+) cells", q).group(1))
    assert len(row) == n
    table = {a: b for a, b in re.findall(r"([01]{3}) becomes ([01])", q)}
    assert len(table) == 8
    edge = re.search(r"beyond the two ends of the row count as ([01])", q).group(1)
    steps = int(re.search(r"After (\d+) steps?", q).group(1))
    cur = row
    for _ in range(steps):
        pad = edge + cur + edge
        cur = "".join(table[pad[i - 1 : i + 2]] for i in range(1, len(pad) - 1))
    return cur, []


def cheapest_network(q):
    towns = re.search(r"The towns (.*?) must be joined", q).group(1)
    towns = [t.strip() for t in re.split(r", | and ", towns)]
    edges = [(int(c), a, b) for a, b, c in re.findall(r"A cable between ([A-Z][a-z]+) and ([A-Z][a-z]+) would cost (\d+)\.", q)]
    parent = {t: t for t in towns}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    total = used = 0
    for c, a, b in sorted(edges):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            total += c
            used += 1
    flags = [] if used == len(towns) - 1 else ["disconnected"]
    return str(total), flags


def count_divisible(q):
    m = re.search(r"divisible by (\d+) and greater than (-?\d+)\?", q)
    d, t = int(m.group(1)), int(m.group(2))
    xs = _ints(re.search(r"List: (.*)\.$", q.strip()).group(1))
    states = "counts each time it appears" in q
    v = sum(x for x in xs if x % d == 0 and x > t)
    vset = sum(x for x in set(xs) if x % d == 0 and x > t)
    flags = []
    if v != vset:
        flags.append("set_reading_differs" + ("_but_stated" if states else "_UNSTATED"))
    return str(v), flags


def crt_smallest(q):
    pairs = [(int(r), int(m)) for r, m in re.findall(r"leaves remainder (\d+) when divided by (\d+)", q)]
    flags = []
    if any(r >= m for r, m in pairs):
        flags.append("remainder_not_below_divisor")
    L = 1
    for _, m in pairs:
        L = L * m // gcd(L, m)
    r0, m0 = pairs[0]
    x = r0 % m0
    if x == 0:
        x = m0
    found = None
    while x <= L + m0:
        if all(x % m == r for r, m in pairs):
            found = x
            break
        x += m0
    if found is None:
        return "NONE", flags + ["no_solution"]
    return str(found), flags


def dictionary_rank(q):
    k = int(re.search(r"Write every word of (\d+) letters", q).group(1))
    letters = re.search(r"from the letters (.*?) when no letter", q).group(1)
    letters = sorted(re.findall(r"\b([a-z])\b", letters))
    n = len(letters)

    def count_tail(remaining_slots, avail):
        c = 1
        for i in range(remaining_slots):
            c *= avail - i
        return c

    total = count_tail(k, n)
    flags = []
    m = re.search(r"Which word has number (\d+)\?", q)
    if m:
        r = int(m.group(1))
        if not 1 <= r <= total:
            return "NONE", ["rank_out_of_range"]
        r -= 1
        avail = letters[:]
        word = []
        for pos in range(k):
            block = count_tail(k - pos - 1, len(avail) - 1)
            i = r // block
            r %= block
            word.append(avail.pop(i))
        ans = "".join(word)
        if total <= 20000:  # brute-force cross-check of my own arithmetic
            allw = sorted("".join(p) for p in permutations(letters, k))
            assert allw[int(m.group(1)) - 1] == ans
        return ans, flags
    w = re.search(r"What is the number of the word ([a-z]+)\?", q).group(1)
    if len(w) != k or len(set(w)) != k or any(c not in letters for c in w):
        return "NONE", ["word_not_in_list"]
    avail = letters[:]
    r = 0
    for pos, ch in enumerate(w):
        i = avail.index(ch)
        r += i * count_tail(k - pos - 1, len(avail) - 1)
        avail.pop(i)
    ans = r + 1
    if total <= 20000:
        allw = sorted("".join(p) for p in permutations(letters, k))
        assert allw.index(w) + 1 == ans
    return str(ans), flags


def digit_root(q):
    s = re.search(r"Add up the digits of (\d+)\.", q).group(1)
    while len(s) > 1:
        s = str(sum(int(c) for c in s))
    return s, []


def _tokens(e):
    toks = re.findall(r"\d+|[-+*()]", e)
    assert "".join(toks) == e.replace(" ", ""), e
    return toks


def _eval_prec(toks):
    pos = 0

    def factor():
        nonlocal pos
        t = toks[pos]
        if t == "(":
            pos += 1
            v = expr()
            assert toks[pos] == ")"
            pos += 1
            return v
        pos += 1
        return int(t)

    def term():
        nonlocal pos
        v = factor()
        while pos < len(toks) and toks[pos] == "*":
            pos += 1
            v = v * factor()
        return v

    def expr():
        nonlocal pos
        v = term()
        while pos < len(toks) and toks[pos] in "+-":
            op = toks[pos]
            pos += 1
            w = term()
            v = v + w if op == "+" else v - w
        return v

    v = expr()
    assert pos == len(toks)
    return v


def _eval_ltr(toks):
    pos = 0

    def atom():
        nonlocal pos
        t = toks[pos]
        if t == "(":
            pos += 1
            v = seq()
            assert toks[pos] == ")"
            pos += 1
            return v
        pos += 1
        return int(t)

    def seq():
        nonlocal pos
        v = atom()
        while pos < len(toks) and toks[pos] in "+-*":
            op = toks[pos]
            pos += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    v = seq()
    assert pos == len(toks)
    return v


def expression_eval(q):
    e = re.search(r"Work out (.*?)(?:\. Use these rules| by this rule)", q).group(1)
    toks = _tokens(e)
    if "multiplication gets no priority" in q:
        return str(_eval_ltr(toks)), []
    assert "then do all the multiplications" in q
    return str(_eval_prec(toks)), []


def _digval(c):
    return int(c) if c.isdigit() else ord(c) - ord("a") + 10


def from_base(q):
    m = re.search(r"What is the base-(\d+) number ([0-9a-z]+) written in decimal", q)
    b, s = int(m.group(1)), m.group(2)
    flags = []
    if any(_digval(c) >= b for c in s):
        flags.append("digit_not_below_base")
    if len(s) > 1 and s[0] == "0":
        flags.append("leading_zero")
    v = 0
    for c in s:
        v = v * b + _digval(c)
    return str(v), flags


def to_base_wide(q):
    m = re.search(r"Write the decimal number (\d+) in base (\d+)\.", q)
    n, b = int(m.group(1)), int(m.group(2))
    if n == 0:
        return "0", []
    ds = []
    while n:
        n, r = divmod(n, b)
        ds.append("0123456789abcdef"[r])
    return "".join(reversed(ds)), []


def grid_sum(q):
    m = re.search(r"A grid has (\d+) rows and (\d+) columns\. The rows, from top to bottom, are: (.*?)\. What is", q)
    R, C = int(m.group(1)), int(m.group(2))
    rows = [[int(x) for x in r.split()] for r in m.group(3).split(" / ")]
    assert len(rows) == R and all(len(r) == C for r in rows)
    flags = []
    mm = re.search(r"in row (\d+)\?", q)
    if mm:
        return str(sum(rows[int(mm.group(1)) - 1])), flags
    mm = re.search(r"in column (\d+)\?", q)
    if mm:
        return str(sum(r[int(mm.group(1)) - 1] for r in rows)), flags
    assert "diagonal from the top left corner" in q
    if R != C:
        flags.append("diagonal_of_non_square_grid")
    return str(sum(rows[i][i] for i in range(min(R, C)))), flags


def interval_scheduling(q):
    ms = [(int(i), int(s), int(e)) for i, s, e in re.findall(r"meeting (\d+) runs from (\d+) to (\d+)", q)]
    flags = []
    if any(s >= e for _, s, e in ms):
        flags.append("empty_or_reversed_meeting")
    chosen = []
    left = ms[:]
    while True:
        ok = [m for m in left if all(not (m[1] < c[2] and c[1] < m[2]) for c in chosen)]
        if not ok:
            break
        pick = min(ok, key=lambda m: (m[2], m[0]))
        chosen.append(pick)
        left.remove(pick)
    return ", ".join(str(i) for i in sorted(m[0] for m in chosen)), flags


def list_ops(q):
    xs = _ints(re.search(r"Start with the list (.*?)\. Do these steps", q).group(1))
    ops = re.search(r"Do these steps in order: (.*?)\. What is the final list", q).group(1).split("; ")
    flags = []
    for op in ops:
        if op == "reverse the list":
            xs = xs[::-1]
        elif op == "remove the first element":
            if not xs:
                flags.append("remove_from_empty")
            xs = xs[1:]
        elif op == "remove the last element":
            if not xs:
                flags.append("remove_from_empty")
            xs = xs[:-1]
        elif op == "move the first element to the end":
            if not xs:
                flags.append("move_on_empty")
            xs = xs[1:] + xs[:1]
        else:
            m = re.fullmatch(r"add (-?\d+) at the end", op)
            assert m, op
            xs = xs + [int(m.group(1))]
    if not xs:
        flags.append("empty_final_list")
    return ", ".join(str(x) for x in xs), flags


def _luhn_total(digits):
    t = 0
    for i, c in enumerate(reversed(digits)):
        d = int(c)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        t += d
    return t


def luhn_check(q):
    m = re.search(r"One more digit is to be written at the right end of (\d+) so that", q)
    if m:
        good = [d for d in range(10) if _luhn_total(m.group(1) + str(d)) % 10 == 0]
        flags = [] if len(good) == 1 else ["check_digit_not_unique"]
        return (str(good[0]) if good else "NONE"), flags
    m = re.search(r"Is the number (\d+) valid\?", q)
    return ("yes" if _luhn_total(m.group(1)) % 10 == 0 else "no"), []


def min_heap_ops(q):
    xs = _ints(re.search(r"add these numbers in order: (.*?)\.", q).group(1))
    mm = re.search(r"Then remove the smallest (\d+) times?\.", q)
    k = int(mm.group(1)) if mm else 0
    h = []
    flags = []
    for x in xs:
        h.append(x)
        p = len(h)  # 1-based
        while p > 1 and h[p - 1] < h[p // 2 - 1]:
            h[p - 1], h[p // 2 - 1] = h[p // 2 - 1], h[p - 1]
            p //= 2
    for _ in range(k):
        last = h.pop()
        if h:
            h[0] = last
            p = 1
            while True:
                kids = [c for c in (2 * p, 2 * p + 1) if c <= len(h)]
                if not kids:
                    break
                vals = [h[c - 1] for c in kids]
                sm = min(vals)
                if not h[p - 1] > sm:
                    break
                if len(kids) == 2 and vals[0] == vals[1]:
                    flags.append("heap_child_tie")
                c = kids[vals.index(sm)]
                h[p - 1], h[c - 1] = h[c - 1], h[p - 1]
                p = c
    return ", ".join(str(x) for x in h), flags


def run_length(q):
    s = re.search(r"Compress ([a-z]+) by run-length encoding", q).group(1)
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(f"{s[i]}{j - i}")
        i = j
    return "".join(out), []


def sort_list(q):
    m = re.search(r"Sort these numbers from (smallest to largest|largest to smallest) and give them separated by commas: (.*)\.$", q.strip())
    xs = _ints(m.group(2))
    xs = sorted(xs, reverse=m.group(1) == "largest to smallest")
    return ", ".join(str(x) for x in xs), []


def _rewrite(s, pat, rep):
    out = []
    i = 0
    while i < len(s):
        if s[i : i + len(pat)] == pat:
            out.append(rep)
            i += len(pat)
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def string_rewrite_nonidentity(q):
    s = re.search(r"Start with the string ([a-z]+)\.", q).group(1)
    steps = re.search(r"when the step starts: (.*?)\. What is the final string", q).group(1).split("; ")
    for st in steps:
        m = re.fullmatch(r"replace every '([a-z]+)' with '([a-z]*)'", st)
        if m:
            s = _rewrite(s, m.group(1), m.group(2))
            continue
        m = re.fullmatch(r"delete every '([a-z]+)'", st)
        assert m, st
        s = _rewrite(s, m.group(1), "")
    return s, ([] if s else ["empty_answer"])


SOLVERS = {f.__name__: f for f in (binary_search_trace, caesar_shift, cellular_automaton, cheapest_network, count_divisible, crt_smallest,
           dictionary_rank, digit_root, expression_eval, from_base, grid_sum, interval_scheduling, list_ops, luhn_check, min_heap_ops,
           run_length, sort_list, string_rewrite_nonidentity, to_base_wide)}


def solve(name, q):
    return SOLVERS[name](q)
