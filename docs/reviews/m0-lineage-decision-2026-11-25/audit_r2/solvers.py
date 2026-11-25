# ruff: noqa
"""Auditor's independent solvers for the 26 R2 batch-1 lineages. Each reads ONLY the rendered question text (never the
structured form and never the generator's helper functions) and returns the answer string. Written by the auditor from
the question wording; where practical a different method from the obvious one is used (round-based proposals, parallel
toppling order, DP for interval scheduling, exhaustive search for merging, brute force for CRT/LPS/max block/rank)."""
import ast
import bisect
import itertools
import math
import re
from functools import lru_cache


def ints(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


def need(m, what):
    if not m:
        raise ValueError(f"parse failure: {what}")
    return m


def split_and(s):
    # "A, B and C" -> [A, B, C]
    s = s.strip()
    if " and " in s:
        head, last = s.rsplit(" and ", 1)
        parts = [p.strip() for p in head.split(",")] + [last.strip()]
    else:
        parts = [s]
    return [p for p in parts if p]


# ---------------------------------------------------------------- search
def binary_search_trace(q):
    target = int(need(re.search(r"is searched for (-?\d+)\.", q), "target").group(1))
    xs = ints(need(re.search(r"The list: ([-\d, ]+)\. ", q), "list").group(1))
    lo, hi, seen = 1, len(xs), []
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
    if "Which numbers does the search look at" in q:
        return ", ".join(map(str, seen))
    need("Which is the third number" in q, "ask")
    if len(seen) < 3:
        raise ValueError("fewer than three probes")
    return str(seen[2])


# ---------------------------------------------------------------- parsing
PAIR = {")": "(", "]": "[", "}": "{"}


def bracket_match(q):
    m = re.search(r"In the text (\S+) every opening", q)
    if m:
        s = m.group(1)
        st = []
        for ch in s:
            if ch in "([{":
                st.append(ch)
            elif ch in PAIR:
                if not st or st[-1] != PAIR[ch]:
                    return "no"
                st.pop()
            else:
                raise ValueError(f"unexpected char {ch}")
        return "yes" if not st else "no"
    s = need(re.search(r"In the correctly nested text (\S+) \(positions", q), "text").group(1)
    p = int(need(re.search(r"opening bracket at position (\d+)\?", q), "p").group(1))
    # depth-count method (not a stack of indices)
    assert s[p - 1] in "([{"
    depth = 0
    for i in range(p - 1, len(s)):
        depth += 1 if s[i] in "([{" else -1
        if depth == 0:
            if PAIR.get(s[i]) != s[p - 1]:
                raise ValueError("kind mismatch")
            return str(i + 1)
    raise ValueError("no match")


def _eval_ranked(text):
    node = ast.parse(text, mode="eval").body

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
        raise ValueError(f"unexpected node {ast.dump(n)}")

    return ev(node)


def _eval_ltr(text):
    toks = re.findall(r"\d+|[()+\-*]", text)
    pos = 0

    def seq():
        nonlocal pos
        v = atom()
        while pos < len(toks) and toks[pos] in "+-*":
            op = toks[pos]
            pos += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    def atom():
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == "(":
            v = seq()
            assert toks[pos] == ")"
            pos += 1
            return v
        return int(t)

    v = seq()
    assert pos == len(toks)
    return v


def expression_eval(q):
    if "not the usual one" in q:
        text = need(re.search(r"Work out (.+?) by this rule", q), "expr").group(1)
        return str(_eval_ltr(text))
    text = need(re.search(r"Work out (.+?)\. Do what is inside", q), "expr").group(1)
    return str(_eval_ranked(text))


# ---------------------------------------------------------------- structures
def bst_traversal(q):
    xs = ints(need(re.search(r"put in this order: ([-\d, ]+)\. Read", q), "xs").group(1))
    root = None
    L, R = {}, {}
    for x in xs:
        if root is None:
            root = x
            continue
        cur = root
        while True:
            d = L if x < cur else R
            if x == cur:
                raise ValueError("duplicate")
            if cur in d:
                cur = d[cur]
            else:
                d[cur] = x
                break
    out = []
    if "write a number, then everything in its left branch" in q:
        def go(v):
            if v is None:
                return
            out.append(v); go(L.get(v)); go(R.get(v))
        go(root)
    elif "then the number itself" in q:
        def go(v):
            if v is None:
                return
            go(L.get(v)); go(R.get(v)); out.append(v)
        go(root)
    elif "write the top number, then the numbers one step below" in q:
        queue = [root]
        while queue:
            v = queue.pop(0)
            out.append(v)
            for c in (L.get(v), R.get(v)):
                if c is not None:
                    queue.append(c)
    else:
        raise ValueError("traversal kind")
    return ", ".join(map(str, out))


def min_heap_ops(q):
    xs = ints(need(re.search(r"add these numbers in order: ([-\d, ]+)\.", q), "xs").group(1))
    m = re.search(r"Then remove the smallest (\d+) time", q)
    rem = int(m.group(1)) if m else 0
    h = [None]  # 1-based

    for x in xs:
        h.append(x)
        p = len(h) - 1
        while p > 1 and h[p] < h[p // 2]:
            h[p], h[p // 2] = h[p // 2], h[p]
            p //= 2
    for _ in range(rem):
        last = h.pop()
        if len(h) == 1:
            continue
        h[1] = last
        p = 1
        n = len(h) - 1
        while True:
            kids = [c for c in (2 * p, 2 * p + 1) if c <= n]
            if not kids:
                break
            c = min(kids, key=lambda i: h[i])
            if h[p] > h[c]:
                h[p], h[c] = h[c], h[p]
                p = c
            else:
                break
    return ", ".join(map(str, h[1:]))


def cache_eviction(q):
    cap = int(need(re.search(r"holds at most (\d+) items", q), "cap").group(1))
    if "requested longest ago (counting its latest request)" in q:
        pol = "lru"
    elif "loaded into the cache longest ago" in q:
        pol = "fifo"
    else:
        raise ValueError("policy")
    seq_s = need(re.search(r"Requests in order: (.+?)\. (?:How many|After the last)", q), "seq").group(1)
    seq = [s.strip() for s in seq_s.split(", ")]
    order = []  # oldest first by the policy's key
    stamp = {}
    misses = 0
    for t, x in enumerate(seq):
        if x in stamp:
            if pol == "lru":
                stamp[x] = t
        else:
            misses += 1
            if len(stamp) == cap:
                victim = min(stamp, key=lambda k: stamp[k])
                del stamp[victim]
            stamp[x] = t
    if "How many requests found the item missing" in q:
        return str(misses)
    item = need(re.search(r"After the last request, is (.+?) in the cache\?", q), "item").group(1)
    return "yes" if item in stamp else "no"


def hash_probe(q):
    m = int(need(re.search(r"A table has (\d+) slots", q), "m").group(1))
    keys = ints(need(re.search(r"added in this order: ([-\d, ]+)\. ", q), "keys").group(1))
    table = {}
    where, looked = {}, {}
    for k in keys:
        s = k % m
        n = 1
        while s in table:
            s = (s + 1) % m
            n += 1
            if n > m:
                raise ValueError("full")
        table[s] = k
        where[k], looked[k] = s, n
    mm = re.search(r"In which slot does (\d+) end up\?", q)
    if mm:
        return str(where[int(mm.group(1))])
    mm = need(re.search(r"When (\d+) \(the last number\) is added, how many slots are looked at", q), "ask")
    k = int(mm.group(1))
    assert k == keys[-1]
    return str(looked[k])


# ---------------------------------------------------------------- dynamic programmes
def lcs_length(q):
    a, b = need(re.search(r"subsequence of both '([a-z]+)' and '([a-z]+)'\?", q), "ab").groups()

    @lru_cache(maxsize=None)
    def f(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))

    return str(f(0, 0))


def coin_change_min(q):
    m = need(re.search(r"coins worth ([\d, ]+?) and (\d+)\. What is the smallest number of coins that add up to exactly (\d+)\?", q), "coins")
    coins = ints(m.group(1)) + [int(m.group(2))]
    amount = int(m.group(3))
    # BFS over amounts reached
    dist = {0: 0}
    frontier = [0]
    while frontier:
        nxt = []
        for v in frontier:
            for c in coins:
                w = v + c
                if w <= amount and w not in dist:
                    dist[w] = dist[v] + 1
                    nxt.append(w)
        frontier = nxt
    if amount not in dist:
        raise ValueError("unreachable")
    return str(dist[amount])


def lis_length(q):
    xs = ints(need(re.search(r"Numbers: ([-\d, ]+)\.$", q), "xs").group(1))
    tails = []
    for x in xs:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return str(len(tails))


def max_subarray_sum(q):
    xs = ints(need(re.search(r"Row: ([-\d, ]+)\.$", q), "xs").group(1))
    best = max(sum(xs[i:j]) for i in range(len(xs)) for j in range(i + 1, len(xs) + 1))
    return str(best)


# ---------------------------------------------------------------- number theory
def gcd_euclid(q):
    m = re.search(r"greatest common divisor of (\d+) and (\d+)\?", q)
    if m:
        return str(math.gcd(int(m.group(1)), int(m.group(2))))
    m = re.search(r"least common multiple of (\d+) and (\d+)\?", q)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        x = max(a, b)
        while x % a or x % b:
            x += max(a, b)
        return str(x)
    m = need(re.search(r"Start with the pair \((\d+), (\d+)\)\. One step replaces a pair \(x, y\) by the pair \(y, the remainder of x divided by y\)", q), "steps")
    x, y = int(m.group(1)), int(m.group(2))
    n = 0
    while y != 0:
        x, y = y, x % y
        n += 1
    return str(n)


def modular_power(q):
    m = need(re.search(r"Multiply together (\d+) copies of the number (\d+) .*divided by (\d+)\?", q), "mp")
    e, a, mod = map(int, m.groups())
    r = 1
    for _ in range(e):
        r = (r * a) % mod
    return str(r)


def crt_smallest(q):
    cons = [(int(r), int(d)) for r, d in re.findall(r"leaves remainder (\d+) when divided by (\d+)", q)]
    need(cons, "cons")
    x = 1
    while not all(x % d == r for r, d in cons):
        x += 1
        if x > 10**7:
            raise ValueError("no solution")
    return str(x)


def _factor(n):
    fs, d = [], 2
    while d * d <= n:
        while n % d == 0:
            fs.append(d)
            n //= d
        d += 1
    if n > 1:
        fs.append(n)
    return fs


def prime_factor_query(q):
    m = re.search(r"largest prime number that divides (\d+) exactly\?", q)
    if m:
        return str(max(_factor(int(m.group(1)))))
    m = need(re.search(r"Write (\d+) as a product of prime numbers", q), "pf")
    return str(sum(_factor(int(m.group(1)))))


# ---------------------------------------------------------------- games / combinatorics / strings
def subtraction_game(q):
    n = int(need(re.search(r"one pile of (\d+) stones", q), "n").group(1))
    moves = ints(need(re.search(r"remove one of these amounts of stones: ([\d or]+);", q), "moves").group(1))

    @lru_cache(maxsize=None)
    def win(k):
        return any(m <= k and not win(k - m) for m in moves)

    return "yes" if win(n) else "no"


def dictionary_rank(q):
    letters = [x.strip() for x in need(re.search(r"arrangement of the letters ([a-z, ]+) \(each used", q), "letters").group(1).split(",")]
    words = sorted("".join(p) for p in itertools.permutations(letters))
    m = re.search(r"Which word has number (\d+)\?", q)
    if m:
        return words[int(m.group(1)) - 1]
    w = need(re.search(r"What is the number of the word ([a-z]+)\?", q), "word").group(1)
    return str(words.index(w) + 1)


def longest_palindromic_substring(q):
    s = need(re.search(r"Look at the string '([a-z]+)'\.", q), "s").group(1)
    best = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            t = s[i:j]
            if t == t[::-1]:
                best = max(best, j - i)
    return str(best)


# ---------------------------------------------------------------- greedy
def interval_scheduling(q):
    iv = [(int(a), int(b)) for a, b in re.findall(r"meeting \d+ runs from (\d+) to (\d+)", q)]
    need(iv, "iv")
    # DP over meetings sorted by end: best[i] = max(best[i-1], 1 + best[p(i)])
    iv.sort(key=lambda x: x[1])
    ends = [e for _, e in iv]
    best = [0] * (len(iv) + 1)
    for i, (s, e) in enumerate(iv, 1):
        p = bisect.bisect_right(ends, s, 0, i - 1)
        best[i] = max(best[i - 1], 1 + best[p])
    return str(best[-1])


def merge_smallest_cost(q):
    ws = ints(need(re.search(r"sizes: ([-\d, ]+)\. Two piles", q), "ws").group(1))
    if len(ws) <= 7:
        @lru_cache(maxsize=None)
        def f(t):
            if len(t) == 1:
                return 0
            best = None
            for i in range(len(t)):
                for j in range(i + 1, len(t)):
                    rest = list(t[:i] + t[i + 1:j] + t[j + 1:])
                    s = t[i] + t[j]
                    v = s + f(tuple(sorted(rest + [s])))
                    best = v if best is None or v < best else best
            return best
        return str(f(tuple(sorted(ws))))
    cur = sorted(ws)
    tot = 0
    while len(cur) > 1:
        a, b = cur[0], cur[1]
        cur = cur[2:]
        bisect.insort(cur, a + b)
        tot += a + b
    return str(tot)


# ---------------------------------------------------------------- graphs
def cheapest_network(q):
    towns = split_and(need(re.search(r"The towns (.+?) must be joined by cables", q), "towns").group(1))
    edges = [(a, b, int(w)) for a, b, w in re.findall(r"A cable between (.+?) and (.+?) would cost (\d+)\.", q)]
    # Prim
    inside = {towns[0]}
    tot = 0
    while len(inside) < len(towns):
        cand = [(w, a, b) for a, b, w in edges if (a in inside) != (b in inside)]
        if not cand:
            raise ValueError("disconnected")
        w, a, b = min(cand)
        inside.add(a); inside.add(b)
        tot += w
    return str(tot)


def deferred_acceptance_partner(q):
    m = need(re.search(r"^(.+?) each want to be paired with one of (.+?), and each of those", q), "groups")
    g1, g2 = split_and(m.group(1)), split_and(m.group(2))
    prefs = {}
    for who, lst_s in re.findall(r"(\w+) ranks (.+?) from best to worst\.", q):
        prefs[who] = split_and(lst_s)
    who = need(re.search(r"Who is (\w+) paired with\?", q), "who").group(1)
    nxt = {p: 0 for p in g1}
    held = {}  # responder -> proposer
    while True:
        free = [p for p in g1 if p not in held.values()]
        if not free:
            break
        asks = {}
        for p in free:
            r = prefs[p][nxt[p]]
            nxt[p] += 1
            asks.setdefault(r, []).append(p)
        for r, ps in asks.items():
            pool = ps + ([held[r]] if r in held else [])
            held[r] = min(pool, key=lambda x: prefs[r].index(x))
    inv = {p: r for r, p in held.items()}
    return inv[who]


# ---------------------------------------------------------------- dynamics
def cellular_automaton(q):
    row = [int(c) for c in need(re.search(r"holds 0s and 1s: ([01]+)\.", q), "row").group(1)]
    table = {k: int(v) for k, v in re.findall(r"([01]{3}) becomes ([01])", q)}
    assert len(table) == 8
    steps = int(need(re.search(r"After (\d+) steps?,", q), "steps").group(1))
    for _ in range(steps):
        pad = [0] + row + [0]
        row = [table[f"{pad[i - 1]}{pad[i]}{pad[i + 1]}"] for i in range(1, len(pad) - 1)]
    if "what does the row look like" in q:
        return "".join(map(str, row))
    need("how many cells hold a 1" in q, "ask")
    return str(sum(row))


def chip_toppling(q):
    row = ints(need(re.search(r"holds chips: ([-\d, ]+) \(from left to right\)", q), "row").group(1))
    n = len(row)
    cur = row[:]
    top = lost = 0
    # parallel order: topple every unstable cell once per sweep, right to left (differs from the generator's order)
    while any(c >= 2 for c in cur):
        for i in [j for j in range(n) if cur[j] >= 2][::-1]:
            k = cur[i] // 2  # topple k times at once
            cur[i] -= 2 * k
            top += k
            if i > 0:
                cur[i - 1] += k
            else:
                lost += k
            if i < n - 1:
                cur[i + 1] += k
            else:
                lost += k
    if "What does the row hold at the end" in q:
        return ", ".join(map(str, cur))
    if "How many topplings happen" in q:
        return str(top)
    need("How many chips are lost" in q, "ask")
    return str(lost)


# ---------------------------------------------------------------- codes
def _luhn_ok(s):
    tot = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2
            d = d - 9 if d > 9 else d
        tot += d
    return tot % 10 == 0


def luhn_check(q):
    m = re.search(r"Is the number (\d+) valid\?", q)
    if m:
        return "yes" if _luhn_ok(m.group(1)) else "no"
    m = need(re.search(r"written at the right end of (\d+) so that", q), "payload")
    ok = [d for d in range(10) if _luhn_ok(m.group(1) + str(d))]
    if len(ok) != 1:
        raise ValueError(f"check digit not unique: {ok}")
    return str(ok[0])


def hamming_error_position(q):
    w = need(re.search(r"Word: ([01]+)\.", q), "word").group(1)
    n = len(w)
    bad = 0
    p = 1
    while p <= n:
        cnt = sum(int(w[i - 1]) for i in range(1, n + 1) if i & p)
        if cnt % 2:
            bad += p
        p *= 2
    if bad > n:
        raise ValueError("syndrome out of range")
    return str(bad)


SOLVERS = {f"R2.{name}": fn for name, fn in list(globals().items()) if callable(fn) and not name.startswith("_") and name not in ("ints", "need", "split_and", "lru_cache", "ast", "bisect", "itertools", "math", "re")}
