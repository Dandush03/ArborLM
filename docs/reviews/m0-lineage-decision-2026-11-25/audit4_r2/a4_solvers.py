# ruff: noqa
"""Audit 4 (R2): independent TEXT-ONLY solvers. Each takes the rendered question text only and returns the answer string.
Stdlib only; imports nothing from studies.m0. Methods differ from the generators' where practical (noted)."""
import bisect
import itertools
import math
import re
import sys
from collections import deque
from functools import lru_cache

sys.setrecursionlimit(20000)


def L(xs):
    return ", ".join(str(x) for x in xs)


def ints(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


# ---------------------------------------------------------------- search
def binary_search_trace(q):
    t = int(re.search(r"is searched for (-?\d+)\.", q).group(1))
    xs = ints(re.search(r"The list: (.*?)\. (Which|What)", q).group(1))
    n = int(re.search(r"A sorted list of (\d+) numbers", q).group(1))
    assert n == len(xs) and xs == sorted(xs)
    lo, hi = 1, n  # 1-based, exactly as worded
    seen = []
    while lo <= hi:
        mid = (lo + hi) // 2
        v = xs[mid - 1]
        seen.append(v)
        if v == t:
            break
        if t < v:
            hi = mid - 1
        else:
            lo = mid + 1
    if "Which numbers does the search look at" in q:
        return L(seen)
    assert "sum of all the numbers" in q
    return str(sum(seen))


# ---------------------------------------------------------------- parsing
OPEN, CLOSE = "([{", ")]}"


def _pairs_by_deletion(t):
    """Match brackets by repeatedly deleting an adjacent opener+closer of the same kind (different method from a stack scan)."""
    idx = list(range(len(t)))
    chars = list(t)
    match = {}
    while chars:
        for i in range(len(chars) - 1):
            a, b = chars[i], chars[i + 1]
            if a in OPEN and b in CLOSE and OPEN.index(a) == CLOSE.index(b):
                match[idx[i]] = idx[i + 1]
                del chars[i : i + 2]
                del idx[i : i + 2]
                break
        else:
            raise ValueError("not nested")
    return match


def bracket_match(q):
    if "In the correctly nested text" in q:
        t = re.search(r"In the correctly nested text (\S+) \(positions", q).group(1)
        kind = re.search(r"For every opening (\w+) bracket", q).group(1)
        k = {"round": "(", "square": "[", "curly": "{"}[kind]
        match = _pairs_by_deletion(t)
        return L([match[i] + 1 for i in range(len(t)) if t[i] == k])
    t = re.search(r"In the text (\S+) \(positions", q).group(1)
    st = []
    for i, ch in enumerate(t):
        if ch in OPEN:
            st.append(ch)
        else:
            if not st or OPEN[CLOSE.index(ch)] != st[-1]:
                return str(i + 1)
            st.pop()
    raise ValueError("no error")


def _tok(text):
    return re.findall(r"\d+|[()+\-*]", text)


def _eval_ranked(text):
    toks = _tok(text)
    pos = [0]

    def atom():
        tk = toks[pos[0]]
        if tk == "(":
            pos[0] += 1
            v = expr()
            assert toks[pos[0]] == ")"
            pos[0] += 1
            return v
        pos[0] += 1
        return int(tk)

    def term():
        v = atom()
        while pos[0] < len(toks) and toks[pos[0]] == "*":
            pos[0] += 1
            v *= atom()
        return v

    def expr():
        v = term()
        while pos[0] < len(toks) and toks[pos[0]] in "+-":
            op = toks[pos[0]]
            pos[0] += 1
            w = term()
            v = v + w if op == "+" else v - w
        return v

    v = expr()
    assert pos[0] == len(toks)
    return v


def _eval_ltr(text):
    toks = _tok(text)
    pos = [0]

    def atom():
        tk = toks[pos[0]]
        if tk == "(":
            pos[0] += 1
            v = chain()
            assert toks[pos[0]] == ")"
            pos[0] += 1
            return v
        pos[0] += 1
        return int(tk)

    def chain():
        v = atom()
        while pos[0] < len(toks) and toks[pos[0]] in "+-*":
            op = toks[pos[0]]
            pos[0] += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    v = chain()
    assert pos[0] == len(toks)
    return v


def expression_eval(q):
    if ". Use these rules, in this order" in q:
        text = re.search(r"Work out (.*?)\. Use these rules", q).group(1)
        return str(_eval_ranked(text))
    text = re.search(r"Work out (.*?) by this rule, which is not the usual one", q).group(1)
    return str(_eval_ltr(text))


# ---------------------------------------------------------------- structures
def bst_traversal(q):
    xs = ints(re.search(r"put in this order: (.*?)\. Read the tree", q).group(1))

    def pre(seq):
        if not seq:
            return []
        r = seq[0]
        return [r] + pre([x for x in seq[1:] if x < r]) + pre([x for x in seq[1:] if x > r])

    def post(seq):
        if not seq:
            return []
        r = seq[0]
        return post([x for x in seq[1:] if x < r]) + post([x for x in seq[1:] if x > r]) + [r]

    if "write a number, then everything in its left branch" in q:
        return L(pre(xs))
    if "write everything in a number's left branch" in q:
        return L(post(xs))
    assert "write the top number, then the numbers one step below" in q
    depth = {}
    for x in xs:
        lo, hi, d = -math.inf, math.inf, 0
        for y in xs:
            if y == x:
                break
            if lo < y < hi:  # y lies on x's path
                d += 1
                if x < y:
                    hi = y
                else:
                    lo = y
        depth[x] = d
    return L(sorted(xs, key=lambda v: (depth[v], v)))  # within a level, left to right = ascending in a search tree


def min_heap_ops(q):
    xs = ints(re.search(r"add these numbers in order: (.*?)\.( Then| Give)", q).group(1))
    m = re.search(r"Then remove the smallest (\d+) time", q)
    rem = int(m.group(1)) if m else 0
    h = [None]
    for x in xs:
        h.append(x)
        p = len(h) - 1
        while p > 1 and h[p] < h[p // 2]:
            h[p], h[p // 2] = h[p // 2], h[p]
            p //= 2
    for _ in range(rem):
        last = h.pop()
        if len(h) == 1:
            break
        h[1] = last
        p = 1
        n = len(h) - 1
        while True:
            kids = [c for c in (2 * p, 2 * p + 1) if c <= n]
            if not kids:
                break
            c = min(kids, key=lambda c: h[c])
            if h[p] > h[c]:
                h[p], h[c] = h[c], h[p]
                p = c
            else:
                break
    return L(h[1:])


def hash_probe(q):
    m = int(re.search(r"A table has (\d+) slots", q).group(1))
    keys = ints(re.search(r"Numbers are added in this order: (.*?)\. After", q).group(1))
    tab = {}
    for k in keys:
        s = k % m
        for d in range(m):
            if (s + d) % m not in tab:
                tab[(s + d) % m] = k
                break
        else:
            raise ValueError("full")
    if "what does each slot hold" in q:
        return ", ".join(str(tab[i]) if i in tab else "-" for i in range(m))
    assert "NUMBERS OF THE SLOTS" in q
    return str(sum(tab))


def cache_eviction(q):
    cap = int(re.search(r"A cache holds at most (\d+) items", q).group(1))
    seq = re.search(r"Requests in order: (.*?)\. (Which|After)", q).group(1).split(", ")
    if "requested longest ago (counting its latest request)" in q:
        pol = "lru"
    else:
        assert "loaded into the cache longest ago" in q
        pol = "fifo"
    stamp = {}
    ev = []
    for t, x in enumerate(seq):
        if x in stamp:
            if pol == "lru":
                stamp[x] = t
            continue
        if len(stamp) == cap:
            old = min(stamp, key=stamp.get)
            ev.append(old)
            del stamp[old]
        stamp[x] = t
    if "Which items are removed" in q:
        return ", ".join(ev)
    assert "After the last request" in q
    return ", ".join(sorted(stamp, key=stamp.get))


# ---------------------------------------------------------------- dynamics / codes
def cellular_automaton(q):
    row = re.search(r"holds 0s and 1s: ([01]+)\.", q).group(1)
    tab = dict(re.findall(r"([01]{3}) becomes ([01])", q))
    assert len(tab) == 8
    steps = int(re.search(r"After (\d+) steps", q).group(1))
    assert "beyond the two ends of the row count as 0" in q
    cur = row
    for _ in range(steps):
        p = "0" + cur + "0"
        cur = "".join(tab[p[i : i + 3]] for i in range(len(cur)))
    return cur


def hamming_error_position(q):
    w = re.search(r"Word: ([01]+)\.", q).group(1)
    n = len(w)
    s = 0
    p = 1
    while p <= n:
        if sum(int(w[i - 1]) for i in range(1, n + 1) if i & p) % 2:
            s += p
        p *= 2
    return str(s)


def luhn_check(q):
    def total(ds):
        t = 0
        for i, d in enumerate(reversed(ds), 1):
            if i % 2 == 0:
                d = 2 * d
                if d > 9:
                    d -= 9
            t += d
        return t

    if "Is the number" in q:
        ds = [int(c) for c in re.search(r"Is the number (\d+) valid", q).group(1)]
        return "yes" if total(ds) % 10 == 0 else "no"
    ds = [int(c) for c in re.search(r"at the right end of (\d+) so that", q).group(1)]
    good = [d for d in range(10) if total(ds + [d]) % 10 == 0]
    assert len(good) == 1
    return str(good[0])


# ---------------------------------------------------------------- greedy / graphs
def interval_scheduling(q):
    ms = [(int(a), int(b), int(c)) for a, b, c in re.findall(r"meeting (\d+) runs from (\d+) to (\d+)", q)]
    chosen = []
    while True:  # literal reading of the rounds
        cand = [m for m in ms if m not in chosen and all(m[2] <= c[1] or m[1] >= c[2] for c in chosen)]
        if not cand:
            break
        chosen.append(min(cand, key=lambda m: (m[2], m[0])))
    return L(sorted(m[0] for m in chosen))


def merge_smallest_cost(q):
    ws = sorted(ints(re.search(r"with these sizes: (.*?)\. Any two", q).group(1)))
    a, b = deque(ws), deque()  # two-queue Huffman
    total = 0

    def take():
        if not b or (a and a[0] <= b[0]):
            return a.popleft()
        return b.popleft()

    while len(a) + len(b) > 1:
        x, y = take(), take()
        total += x + y
        b.append(x + y)
    return str(total)


def cheapest_network(q):
    cab = re.findall(r"A cable between (\w+) and (\w+) would cost (\d+)\.", q)
    towns = set()
    adj = {}
    for a, b, w in cab:
        w = int(w)
        towns |= {a, b}
        adj.setdefault(a, []).append((w, b))
        adj.setdefault(b, []).append((w, a))
    listed = re.search(r"The towns (.*?) must be joined", q).group(1).replace(" and ", ", ").split(", ")
    assert set(listed) == towns, (listed, towns)
    start = sorted(towns)[0]  # Prim
    seen = {start}
    tot = 0
    while len(seen) < len(towns):
        w, v = min((w, v) for u in seen for w, v in adj[u] if v not in seen)
        seen.add(v)
        tot += w
    return str(tot)


# ---------------------------------------------------------------- dynprog
def coin_change_min(q):
    m = re.search(r"coins worth (.*?)\. For each of the amounts (.*?), in this order", q)
    coins = ints(m.group(1))
    amts = ints(m.group(2))
    assert len(amts) == 5
    out = []
    for a in amts:  # BFS on the amount
        dist = {0: 0}
        dq = deque([0])
        while dq:
            v = dq.popleft()
            if v == a:
                break
            for c in coins:
                if v + c <= a and v + c not in dist:
                    dist[v + c] = dist[v] + 1
                    dq.append(v + c)
        out.append(dist[a])
    return L(out)


def lcs_length(q):
    a, b = re.search(r"subsequence of both '(\w+)' and '(\w+)'", q).groups()

    @lru_cache(None)
    def f(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))

    return str(f(0, 0))


def lis_length(q):
    xs = ints(re.search(r"Numbers: (.*?)\.$", q).group(1))
    tails = []  # patience sorting
    for x in xs:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return str(len(tails))


def max_subarray_sum(q):
    xs = ints(re.search(r"Row: (.*?)\.$", q).group(1))
    pre = [0]
    for x in xs:
        pre.append(pre[-1] + x)
    return str(max(pre[j] - pre[i] for i in range(len(xs)) for j in range(i + 1, len(xs) + 1)))


def longest_palindromic_substring(q):
    s = re.search(r"Look at the string '(\w+)'", q).group(1)
    best = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            if j - i > best and s[i:j] == s[i:j][::-1]:
                best = j - i
    return str(best)


# ---------------------------------------------------------------- number theory
def _stein(x, y):
    if x == 0:
        return y
    if y == 0:
        return x
    k = 0
    while (x | y) & 1 == 0:
        x >>= 1
        y >>= 1
        k += 1
    while x & 1 == 0:
        x >>= 1
    while y:
        while y & 1 == 0:
            y >>= 1
        if x > y:
            x, y = y, x
        y -= x
    return x << k


def gcd_euclid(q):
    a, b = ints(re.search(r"of (\d+) and (\d+)\?", q).group(0))
    g = _stein(a, b)
    if q.startswith("What is the greatest common divisor"):
        return str(g)
    assert q.startswith("What is the least common multiple")
    return str(a // g * b)


def multiples_between(q):
    a, b, m = ints(re.search(r"from (\d+) to (\d+), counting both ends,.*?multiples of (\d+)", q).group(0))
    xs = [x for x in range(a, b + 1) if x % m == 0]
    if q.startswith("How many"):
        return str(len(xs))
    assert q.startswith("What is the sum")
    return str(sum(xs))


def digit_root(q):
    n = int(re.search(r"digits of (\d+)\.", q).group(1))
    while n > 9:
        n = sum(int(c) for c in str(n))
    return str(n)


def modular_power(q):
    e, a = ints(re.search(r"Multiply together (\d+) copies of the number (\d+)", q).group(0))
    m = int(re.search(r"divided by (\d+)\?", q).group(1))
    v = 1
    for _ in range(e):
        v = v * a % m
    return str(v)


def prime_factor_query(q):
    n = int(re.search(r"(?:divides|Write) (\d+)", q).group(1))
    fs = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            fs.append(d)
            n //= d
        d += 1
    if n > 1:
        fs.append(n)
    if q.startswith("What is the largest prime"):
        return str(max(fs))
    assert "Add up the primes in that product" in q
    return str(sum(fs))


def crt_smallest(q):
    cons = [(int(r), int(m)) for r, m in re.findall(r"leaves remainder (\d+) when divided by (\d+)", q)]
    P = math.prod(m for _, m in cons)
    r0, m0 = max(cons, key=lambda c: c[1])
    x = r0 if r0 > 0 else m0
    while x <= P:
        if all(x % m == r for r, m in cons):
            return str(x)
        x += m0
    raise ValueError


def from_base(q):
    b, s = re.search(r"the base-(\d+) number (\w+) written", q).groups()
    b = int(b)
    v = 0
    for c in s:
        d = int(c) if c.isdigit() else ord(c) - ord("a") + 10
        assert d < b
        v = v * b + d
    return str(v)


def to_base_wide(q):
    n, b = ints(re.search(r"decimal number (\d+) in base (\d+)", q).group(0))
    p = 1
    while p * b <= n:
        p *= b
    out = ""
    while p:
        d, n = divmod(n, p)
        out += "0123456789abcdef"[d]
        p //= b
    return out


# ---------------------------------------------------------------- combinatorics
def _falling(a, b):
    r = 1
    for i in range(b):
        r *= a - i
    return r


def dictionary_rank(q):
    m = re.search(r"Write every word of (\d+) letters that can be made from the letters (.*?) when no letter", q)
    ln = int(m.group(1))
    letters = sorted(m.group(2).split(", "))
    total = _falling(len(letters), ln)
    if total <= 40000:  # brute force
        words = ["".join(p) for p in itertools.permutations(letters, ln)]
        if "Which word has number" in q:
            k = int(re.search(r"Which word has number (\d+)\?", q).group(1))
            return words[k - 1]
        w = re.search(r"What is the number of the word (\w+)\?", q).group(1)
        return str(words.index(w) + 1)
    if "Which word has number" in q:
        k = int(re.search(r"Which word has number (\d+)\?", q).group(1))
        pool = list(letters)
        out = ""
        rem = k
        for i in range(ln):
            block = _falling(len(pool) - 1, ln - i - 1)
            for c in list(pool):
                if rem > block:
                    rem -= block
                else:
                    out += c
                    pool.remove(c)
                    break
        return out
    w = re.search(r"What is the number of the word (\w+)\?", q).group(1)
    pool = list(letters)
    cnt = 0
    for i, c in enumerate(w):
        cnt += sum(1 for x in pool if x < c) * _falling(len(pool) - 1, ln - i - 1)
        pool.remove(c)
    return str(cnt + 1)


def permutation_power(q):
    n = int(re.search(r"A mapping on the numbers 1 to (\d+) sends", q).group(1))
    img = {int(a): int(b) for a, b in re.findall(r"(\d+) goes to (\d+)", q)}
    assert sorted(img) == list(range(1, n + 1)) and sorted(img.values()) == list(range(1, n + 1))
    s, t = ints(re.search(r"Start at (\d+) and apply the mapping (\d+) times", q).group(0))
    cyc = [s]
    while img[cyc[-1]] != s:
        cyc.append(img[cyc[-1]])
    return str(cyc[t % len(cyc)])


def subtraction_game(q):
    piles = ints(re.search(r"four piles of stones, with (.*?) stones\.", q).group(1))
    moves = ints(re.search(r"one of these amounts of stones: (.*?);", q).group(1))
    assert len(piles) == 4
    N = max(piles)
    g = []
    for s in range(N + 1):
        opts = {g[s - m] for m in moves if m <= s}
        v = 0
        while v in opts:
            v += 1
        g.append(v)
    x = 0
    for p in piles:
        x ^= g[p]
    return "yes" if x else "no"


# ---------------------------------------------------------------- strings / lists / misc
def caesar_shift(q):
    text, k = re.search(r"Shift every letter of '(.*?)' forward by (\d+) places", q).groups()
    k = int(k)
    return "".join(c if c == " " else chr((ord(c) - 97 + k) % 26 + 97) for c in text)


def run_length(q):
    s = re.search(r"Compress (\w+) by run-length", q).group(1)
    return "".join(f"{c}{len(list(g))}" for c, g in itertools.groupby(s))


def palindrome_check(q):
    s = re.search(r"does the text '(.*?)' read the same", q).group(1).replace(" ", "")
    return "yes" if all(s[i] == s[-1 - i] for i in range(len(s))) else "no"


def count_letter(q):
    ch, words = re.search(r"the letter '(\w)' appear in total in these words: (.*?)\?$", q).groups()
    return str(sum(1 for c in words if c == ch))


def count_divisible(q):
    m, t, xs = re.search(r"divisible by (\d+) and greater than (\d+)\? List: (.*?)\.$", q).groups()
    m, t = int(m), int(t)
    xs = ints(xs)
    if q.startswith("What is the sum"):
        return str(sum(x for x in xs if x > t and x % m == 0))
    return str(sum(1 for x in xs if x > t and x % m == 0))


def sort_list(q):
    xs = ints(q.split(": ", 1)[1])
    if "from largest to smallest" in q:
        return L(sorted(xs, reverse=True))
    assert "from smallest to largest" in q
    return L(sorted(xs))


def kth_smallest(q):
    k = int(re.search(r"in position (\d+) if", q).group(1))
    xs = ints(q.split("Numbers: ", 1)[1])
    return str(sorted(xs)[k - 1])


def list_ops(q):
    xs = ints(re.search(r"Start with the list (.*?)\. Do these steps", q).group(1))
    steps = re.search(r"Do these steps in order: (.*?)\. What is the final list", q).group(1).split("; ")
    for s in steps:
        if s == "reverse the list":
            xs = xs[::-1]
        elif s == "remove the first element":
            xs = xs[1:]
        elif s == "remove the last element":
            xs = xs[:-1]
        elif s == "move the first element to the end":
            xs = xs[1:] + xs[:1]
        else:
            xs = xs + [int(re.fullmatch(r"add (\d+) at the end", s).group(1))]
    return L(xs)


def grid_sum(q):
    rows = [ints(r) for r in re.search(r"The rows, from top to bottom, are: (.*?)\. What is", q).group(1).split(" / ")]
    if "the diagonal from the top left corner" in q:
        return str(sum(rows[i][i] for i in range(min(len(rows), len(rows[0])))))
    m = re.search(r"in (row|column) (\d+)\?", q)
    i = int(m.group(2)) - 1
    if m.group(1) == "row":
        return str(sum(rows[i]))
    return str(sum(r[i] for r in rows))


STEP = r", (?=push |add the top|multiply the top|subtract:|duplicate the top|discard the top|swap the top)"


def stack_machine(q):
    steps = re.search(r"Do these steps in order: (.*)\. What number is on top", q).group(1)
    st = []
    for p in re.split(STEP, steps):
        if p.startswith("push "):
            st.append(int(p[5:]))
        elif p.startswith("add the top two"):
            b, a = st.pop(), st.pop()
            st.append(a + b)
        elif p.startswith("multiply the top two"):
            b, a = st.pop(), st.pop()
            st.append(a * b)
        elif p.startswith("subtract: second from top minus top"):
            b, a = st.pop(), st.pop()
            st.append(a - b)
        elif p == "duplicate the top":
            st.append(st[-1])
        elif p == "discard the top":
            st.pop()
        elif p == "swap the top two":
            st[-1], st[-2] = st[-2], st[-1]
        else:
            raise ValueError(p)
    return str(st[-1])


def string_rewrite_nonidentity(q):
    s = re.search(r"Start with the string (\w+)\.", q).group(1)
    rules = []
    for m in re.finditer(r"replace every '(\w+)' with '(\w*)'|delete every '(\w+)'", q):
        rules.append((m.group(3), "") if m.group(3) else (m.group(1), m.group(2)))
    for p, t in rules:  # manual left-to-right non-overlapping scan
        out, i = "", 0
        while i < len(s):
            if s.startswith(p, i):
                out += t
                i += len(p)
            else:
                out += s[i]
                i += 1
        s = out
    return s


SOLVERS = {k: v for k, v in dict(globals()).items() if callable(v) and not k.startswith("_") and k not in ("L", "ints", "lru_cache", "deque")}
