# ruff: noqa
"""Audit 3 (R2): independent solvers. Stdlib only; imports NOTHING from studies.m0. Each takes (structured dict, question text) and returns the answer string.
Where practical a different method from the generator's is used (noted per solver)."""
import itertools
import math
import re
from functools import lru_cache

DIG = "0123456789abcdef"


def L(xs):
    return ", ".join(str(x) for x in xs)


# ---------------- core 16 ----------------
def count_letter(s, q):
    return str("".join(s["words"]).count(s["letter"]))


def count_divisible(s, q):
    return str(len([x for x in s["xs"] if x > s["t"] and x % s["m"] == 0]))


def sort_list(s, q):
    xs = list(s["xs"])
    # selection sort (different from sorted())
    out = []
    while xs:
        v = max(xs) if s["desc"] else min(xs)
        out.append(v)
        xs.remove(v)
    return L(out)


def kth_smallest(s, q):
    xs, k = s["xs"], s["k"]
    # rank counting: the value with exactly k-1 smaller values
    for v in xs:
        if sum(1 for w in xs if w < v) == k - 1:
            return str(v)
    raise ValueError


def list_ops(s, q):
    cur = list(s["xs"])
    for op in s["ops"]:
        o = op[0]
        if o == "reverse":
            cur = cur[::-1]
        elif o == "drop_first":
            cur = cur[1:]
        elif o == "drop_last":
            cur = cur[:-1]
        elif o == "append":
            cur = cur + [op[1]]
        elif o == "first_to_end":
            cur = cur[1:] + cur[:1]
        else:
            raise ValueError(o)
    return L(cur)


def to_base(s, q):
    n, b = s["n"], s["base"]
    # greedy from the highest power
    p = 1
    while p * b <= n:
        p *= b
    out = ""
    while p >= 1:
        d = n // p
        out += DIG[d]
        n -= d * p
        p //= b
    return out


def from_base(s, q):
    b = s["base"]
    return str(sum(DIG.index(c) * b ** i for i, c in enumerate(reversed(s["digits"]))))


def string_rewrite(s, q):
    cur = s["s"]
    for p, t in s["rules"]:
        # manual left-to-right non-overlapping scan
        out, i = [], 0
        while i < len(cur):
            if cur.startswith(p, i):
                out.append(t)
                i += len(p)
            else:
                out.append(cur[i])
                i += 1
        cur = "".join(out)
    return cur


def caesar_shift(s, q):
    k = s["k"]
    return "".join(c if c == " " else chr((ord(c) - 97 + k) % 26 + 97) for c in s["text"])


def run_length(s, q):
    out = []
    for c, g in itertools.groupby(s["s"]):
        out.append(f"{c}{len(list(g))}")
    return "".join(out)


def palindrome_check(s, q):
    t = s["phrase"].replace(" ", "")
    return "yes" if all(t[i] == t[-1 - i] for i in range(len(t))) else "no"


def grid_sum(s, q):
    g, what = s["grid"], s["what"]
    m = re.match(r"row (\d+)$", what)
    if m:
        return str(sum(g[int(m.group(1)) - 1]))
    m = re.match(r"column (\d+)$", what)
    if m:
        return str(sum(r[int(m.group(1)) - 1] for r in g))
    assert what.startswith("the diagonal")
    return str(sum(g[i][i] for i in range(min(len(g), len(g[0])))))


def permutation_power(s, q):
    img, x, t = s["img"], s["s"], s["t"]
    # cycle reduction
    cyc = [x]
    y = img[x - 1]
    while y != x:
        cyc.append(y)
        y = img[y - 1]
    return str(cyc[t % len(cyc)])


def stack_machine(s, q):
    st = []
    for p in s["prog"]:
        o = p[0]
        if o == "push":
            st = st + [p[1]]
        elif o == "dup":
            st = st + [st[-1]]
        elif o == "pop":
            st = st[:-1]
        elif o == "swap":
            st = st[:-2] + [st[-1], st[-2]]
        elif o in ("add", "sub", "mul"):
            a, b = st[-2], st[-1]
            st = st[:-2] + [a + b if o == "add" else a - b if o == "sub" else a * b]
        else:
            raise ValueError(o)
    return str(st[-1])


def multiples_between(s, q):
    a, b, m = s["a"], s["b"], s["m"]
    first = a + (-a) % m
    return str(0 if first > b else (b - first) // m + 1)


def digit_root(s, q):
    n = s["n"]
    while n >= 10:
        n = sum(int(c) for c in str(n))
    return str(n)


# ---------------- batch 1 unchanged ----------------
def binary_search_trace(s, q):
    xs, t = s["xs"], s["target"]
    lo, hi, seen = 0, len(xs) - 1, []  # 0-based with the equivalent midpoint (lo+hi+... ) -> use 1-based arithmetic explicitly
    lo1, hi1 = 1, len(xs)
    while lo1 <= hi1:
        mid = (lo1 + hi1) // 2
        v = xs[mid - 1]
        seen.append(v)
        if v == t:
            break
        if t < v:
            hi1 = mid - 1
        else:
            lo1 = mid + 1
    return L(seen) if s["ask"] == "values" else str(seen[2])


def bst_traversal(s, q):
    # recursive split definition, no explicit tree: root is xs[0], left = later numbers smaller, right = later numbers larger (relative order kept)
    def pre(xs):
        if not xs:
            return []
        r = xs[0]
        return [r] + pre([x for x in xs[1:] if x < r]) + pre([x for x in xs[1:] if x > r])

    def post(xs):
        if not xs:
            return []
        r = xs[0]
        return post([x for x in xs[1:] if x < r]) + post([x for x in xs[1:] if x > r]) + [r]

    def level(xs):
        out, q = [], [xs]
        while q:
            nq = []
            for sub in q:
                if sub:
                    r = sub[0]
                    out.append(r)
                    nq.append([x for x in sub[1:] if x < r])
                    nq.append([x for x in sub[1:] if x > r])
            q = nq
        return out

    return L({"pre": pre, "post": post, "level": level}[s["kind"]](s["xs"]))


def min_heap_ops(s, q):
    h = [None]  # 1-based
    for x in s["xs"]:
        h.append(x)
        i = len(h) - 1
        while i > 1 and h[i] < h[i // 2]:
            h[i], h[i // 2] = h[i // 2], h[i]
            i //= 2
    for _ in range(s["removals"]):
        last = h.pop()
        if len(h) == 1:
            break
        h[1] = last
        i = 1
        n = len(h) - 1
        while True:
            kids = [c for c in (2 * i, 2 * i + 1) if c <= n]
            if not kids:
                break
            c = min(kids, key=lambda c: h[c])
            if h[c] < h[i]:
                h[c], h[i] = h[i], h[c]
                i = c
            else:
                break
    return L(h[1:])


def cellular_automaton(s, q):
    row, table, steps = list(s["row"]), s["table"], s["steps"]
    for _ in range(steps):
        p = [0] + row + [0]
        row = [table[f"{p[i - 1]}{p[i]}{p[i + 1]}"] for i in range(1, len(p) - 1)]
    return "".join(map(str, row)) if s["ask"] == "row" else str(sum(row))


def dictionary_rank(s, q):
    letters = sorted(s["letters"])
    n = len(letters)
    if s["ask"] == "word":
        # brute force: enumerate permutations in lexicographic order (itertools.permutations of a sorted pool is lexicographic)
        for i, p in enumerate(itertools.permutations(letters), 1):
            if i == s["k"]:
                return "".join(p)
        raise ValueError
    w = s["word"]
    # count words smaller than w by brute force when small, else formula with inversion counts
    cnt = 0
    for i, c in enumerate(w):
        smaller_later = sum(1 for d in w[i + 1:] if d < c)
        cnt += smaller_later * math.factorial(n - 1 - i)
    return str(cnt + 1)


def hamming_error_position(s, q):
    bits = s["bits"]
    n = len(bits)
    pos = 0
    p = 1
    while p <= n:
        par = sum(bits[i - 1] for i in range(1, n + 1) if i & p) % 2
        if par:
            pos += p
        p *= 2
    return str(pos)


def _luhn(ds):
    tot = 0
    for i, d in enumerate(ds[::-1]):
        if i % 2:
            tot += sum(divmod(2 * d, 10))
        else:
            tot += d
    return tot


def luhn_check(s, q):
    ds = s["digits"]
    if s["ask"] == "valid":
        return "yes" if _luhn(ds) % 10 == 0 else "no"
    for c in range(10):
        if _luhn([*ds, c]) % 10 == 0:
            return str(c)
    raise ValueError


def interval_scheduling(s, q):
    iv = [tuple(x) for x in s["meetings"]]
    # DP over meetings sorted by end (weighted-interval style, weight 1)
    iv.sort(key=lambda x: x[1])
    import bisect
    ends = [e for _, e in iv]
    dp = [0] * (len(iv) + 1)
    for i, (a, b) in enumerate(iv, 1):
        j = bisect.bisect_right(ends, a, 0, i - 1)
        dp[i] = max(dp[i - 1], dp[j] + 1)
    return str(dp[-1])


# ---------------- rev2 ----------------
def _tok(text):
    return re.findall(r"\d+|[()+\-*]", text)


def _eval_ranked(toks):
    # shunting-yard to postfix, + and - same precedence, left assoc; * higher
    prec = {"+": 1, "-": 1, "*": 2}
    out, ops = [], []
    for t in toks:
        if t.isdigit():
            out.append(int(t))
        elif t == "(":
            ops.append(t)
        elif t == ")":
            while ops[-1] != "(":
                out.append(ops.pop())
            ops.pop()
        else:
            while ops and ops[-1] != "(" and prec[ops[-1]] >= prec[t]:
                out.append(ops.pop())
            ops.append(t)
    while ops:
        out.append(ops.pop())
    st = []
    for t in out:
        if isinstance(t, int):
            st.append(t)
        else:
            b, a = st.pop(), st.pop()
            st.append(a + b if t == "+" else a - b if t == "-" else a * b)
    return st[0]


def _eval_ltr(toks):
    # all operators same precedence, left assoc; parentheses respected
    st = [[None, None]]  # (value, pending op)

    def feed(v):
        top = st[-1]
        if top[0] is None:
            top[0] = v
        else:
            op = top[1]
            top[0] = top[0] + v if op == "+" else top[0] - v if op == "-" else top[0] * v
            top[1] = None

    for t in toks:
        if t.isdigit():
            feed(int(t))
        elif t == "(":
            st.append([None, None])
        elif t == ")":
            v = st.pop()[0]
            feed(v)
        else:
            st[-1][1] = t
    return st[0][0]


def expression_eval(s, q):
    toks = _tok(s["text"])
    return str(_eval_ranked(toks) if s["convention"] == "ranked" else _eval_ltr(toks))


def merge_smallest_cost(s, q):
    ws = s["ws"]
    if len(ws) <= 7:
        # exhaustive over all merge orders (any two piles), memoised on the sorted multiset
        @lru_cache(None)
        def best(t):
            if len(t) == 1:
                return 0
            r = math.inf
            for i in range(len(t)):
                for j in range(i + 1, len(t)):
                    m = t[i] + t[j]
                    rest = tuple(sorted(t[:i] + t[i + 1:j] + t[j + 1:] + (m,)))
                    r = min(r, m + best(rest))
            return r
        return str(best(tuple(sorted(ws))))
    # two-queue Huffman (sorted list + FIFO of merged)
    a = sorted(ws)
    b = []
    tot = 0
    def take():
        if b and (not a or b[0] < a[0]):
            return b.pop(0)
        return a.pop(0)
    while len(a) + len(b) > 1:
        x = take(); y = take()
        tot += x + y
        b.append(x + y)
    return str(tot)


def chip_toppling(s, q):
    row = list(s["row"])
    n = len(row)
    cnt = [0] * n
    # parallel toppling: every unstable cell topples as many times as it can at once (different order from the generator)
    while True:
        k = [c // 2 for c in row]
        if not any(k):
            break
        new = [row[i] - 2 * k[i] for i in range(n)]
        for i in range(n):
            if k[i]:
                cnt[i] += k[i]
                if i > 0:
                    new[i - 1] += k[i]
                if i < n - 1:
                    new[i + 1] += k[i]
        row = new
    if s["ask"] == "topplings":
        return str(sum(cnt))
    return str(cnt[s["cell"] - 1])


def _balanced(t):
    pairs = {")": "(", "]": "[", "}": "{"}
    st = []
    for c in t:
        if c in "([{":
            st.append(c)
        else:
            if not st or st[-1] != pairs[c]:
                return False
            st.pop()
    return not st


def bracket_match(s, q):
    t = s["s"]
    if s["ask"] == "valid":
        # repeated removal of adjacent matched pairs (different method)
        u = t
        while True:
            v = u.replace("()", "").replace("[]", "").replace("{}", "")
            if v == u:
                break
            u = v
        return "yes" if u == "" else "no"
    p = s["p"] - 1
    # depth counting ignoring kind (valid because the text is correctly nested)
    d = 0
    for i in range(p, len(t)):
        d += 1 if t[i] in "([{" else -1
        if d == 0:
            return str(i + 1)
    raise ValueError


def coin_change_min(s, q):
    assert s["ask"] == "ways"
    coins, amt = s["coins"], s["amount"]

    @lru_cache(None)
    def f(i, a):
        if a == 0:
            return 1
        if i == len(coins):
            return 0
        return sum(f(i + 1, a - k * coins[i]) for k in range(a // coins[i] + 1))

    return str(f(0, amt))


def hash_probe(s, q):
    m, keys = s["m"], s["keys"]
    occ = {}
    where = {}
    for k in keys:
        for d in range(m):
            sl = (k + d) % m
            if sl not in occ:
                occ[sl] = k
                where[k] = (sl, d + 1)
                break
    if s["ask"] == "slot":
        return str(where[s["target"]][0])
    return str(where[s["target"]][1])


def cache_eviction(s, q):
    cap, seq, pol = s["cap"], s["seq"], s["policy"]
    last_use, load_t, cache = {}, {}, set()
    miss = 0
    for t, x in enumerate(seq):
        if x in cache:
            last_use[x] = t
            continue
        miss += 1
        if len(cache) == cap:
            key = last_use if pol == "lru" else load_t
            v = min(cache, key=lambda y: key[y])
            cache.discard(v)
        cache.add(x)
        last_use[x] = t
        load_t[x] = t
    if s["ask"] == "misses":
        return str(miss)
    return "yes" if s["item"] in cache else "no"


def subtraction_game(s, q):
    moves = s["moves"]
    a, b = s["piles"]

    # direct minimax on the two-pile position (no Grundy theory)
    @lru_cache(None)
    def win(x, y):
        for m in moves:
            if m <= x and not win(x - m, y):
                return True
            if m <= y and not win(x, y - m):
                return True
        return False

    return "yes" if win(a, b) else "no"


def cheapest_network(s, q):
    towns = s["towns"]
    idx = {t: i for i, t in enumerate(towns)}
    n = len(towns)
    adj = {}
    for a, b, w in s["cables"]:
        i, j = idx[a], idx[b]
        adj.setdefault(i, []).append((w, j))
        adj.setdefault(j, []).append((w, i))
    # Prim
    import heapq
    seen = {0}
    h = list(adj.get(0, []))
    heapq.heapify(h)
    tot = 0
    while h and len(seen) < n:
        w, j = heapq.heappop(h)
        if j in seen:
            continue
        seen.add(j)
        tot += w
        for e in adj[j]:
            if e[1] not in seen:
                heapq.heappush(h, e)
    assert len(seen) == n
    return str(tot)


def max_subarray_sum(s, q):
    xs = s["xs"]
    pre = [0]
    for x in xs:
        pre.append(pre[-1] + x)
    return str(max(pre[j] - pre[i] for i in range(len(xs)) for j in range(i + 1, len(xs) + 1)))


def gcd_euclid(s, q):
    a, b = s["a"], s["b"]
    # binary gcd (Stein)
    def g(x, y):
        k = 0
        while x % 2 == 0 and y % 2 == 0:
            x //= 2; y //= 2; k += 1
        while x:
            while x % 2 == 0:
                x //= 2
            while y % 2 == 0:
                y //= 2
            if x < y:
                x, y = y, x
            x -= y
        return y << k
    d = g(a, b)
    return str(d) if s["ask"] == "gcd" else str(a // d * b)


def modular_power(s, q):
    a, e, m = s["a"], s["e"], s["m"]
    # plain repeated multiplication (no square-and-multiply)
    r = 1
    for _ in range(e):
        r = r * a % m
    return str(r)


def lcs_length(s, q):
    a, b = s["a"], s["b"]

    @lru_cache(None)
    def f(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))

    return str(f(0, 0))


def lis_length(s, q):
    import bisect
    tails = []
    for x in s["xs"]:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return str(len(tails))


def longest_palindromic_substring(s, q):
    t = s["s"]
    best = 0
    for i in range(len(t)):
        for j in range(i + 1, len(t) + 1):
            u = t[i:j]
            if j - i > best and u == u[::-1]:
                best = j - i
    return str(best)


def _factor(n):
    out, d = [], 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def prime_factor_query(s, q):
    fs = _factor(s["n"])
    return str(max(fs)) if s["ask"] == "largest" else str(sum(fs))


def crt_smallest(s, q):
    cons = s["congruences"]
    # sieve search step by the largest modulus
    cons = sorted(cons, key=lambda c: -c[1])
    r0, m0 = cons[0]
    x = r0 if r0 > 0 else m0
    lim = math.prod(c[1] for c in cons)
    while x <= lim:
        if all(x % m == r for r, m in cons):
            return str(x)
        x += m0
    raise ValueError


SOLVERS = {k: v for k, v in globals().items() if callable(v) and not k.startswith("_") and k not in ("L", "lru_cache")}
SOLVERS["string_rewrite_nonidentity"] = string_rewrite
SOLVERS["to_base_wide"] = to_base
