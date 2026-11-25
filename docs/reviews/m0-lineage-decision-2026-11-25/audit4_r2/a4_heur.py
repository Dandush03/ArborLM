# ruff: noqa
"""Audit 4 (R2): my own cheap-rule battery. Each heuristic takes (structured, question) and returns an answer string or None (= rule does not apply; counted
as WRONG in the main table, see a4_shortcuts.py). Names ending in '(P)' are a valid alternative procedure or a full solve (reported, not called a cue).
Stdlib only; imports nothing from studies.m0."""
import itertools
import math
import re
from collections import Counter

L = lambda xs: ", ".join(str(x) for x in xs)
H = {}


def h(name, lid):
    def deco(fn):
        H.setdefault(lid, []).append((name, fn))
        return fn

    return deco


# ---------------------------------------------------------------- binary_search_trace
def _bs(xs, t, up):
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi + (1 if up else 0)) // 2
        v = xs[mid - 1]
        seen.append(v)
        if v == t:
            break
        if t < v:
            hi = mid - 1
        else:
            lo = mid + 1
    return seen


@h("midpoint rounded up", "binary_search_trace")
def _(s, q):
    seen = _bs(s["xs"], s["target"], True)
    return L(seen) if s["ask"] == "values" else str(sum(seen))


@h("(P) 0-based positions (identical to the stated search)", "binary_search_trace")
def _(s, q):
    xs, t = s["xs"], s["target"]
    lo, hi, seen = 0, len(xs) - 1, []
    while lo <= hi:
        mid = (lo + hi) // 2
        seen.append(xs[mid])
        if xs[mid] == t:
            break
        if t < xs[mid]:
            hi = mid - 1
        else:
            lo = mid + 1
    return L(seen) if s["ask"] == "values" else str(sum(seen))


@h("sum: target x number of looks (log2 n)", "binary_search_trace")
def _(s, q):
    if s["ask"] != "sum":
        return None
    return str(s["target"] * int(math.log2(len(s["xs"]))))


# ---------------------------------------------------------------- bracket_match
OPEN, CLOSE = "([{", ")]}"


def _closers(t):
    st, m = [], {}
    for i, c in enumerate(t):
        if c in OPEN:
            st.append(i)
        else:
            m[st.pop()] = i
    return m


@h("match_all: k-th opener of the kind -> k-th closer of the kind", "bracket_match")
def _(s, q):
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    o = [i for i, c in enumerate(t) if c == k]
    c = [i for i, ch in enumerate(t) if ch == CLOSE[OPEN.index(k)]]
    return L([x + 1 for x in c])


@h("match_all: k-th opener -> k-th closer of the kind from the end", "bracket_match")
def _(s, q):
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    c = [i for i, ch in enumerate(t) if ch == CLOSE[OPEN.index(k)]]
    return L([x + 1 for x in reversed(c)])


@h("match_all: next closer of the same kind after the opener", "bracket_match")
def _(s, q):
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    ck = CLOSE[OPEN.index(k)]
    return L([t.index(ck, i) + 1 for i, ch in enumerate(t) if ch == k])


@h("match_all: same-depth closer ignoring kinds (P)", "bracket_match")
def _(s, q):
    if s["ask"] != "match_all":
        return None
    t, k = s["s"], s["kind"]
    m = _closers(t)
    return L([m[i] + 1 for i, ch in enumerate(t) if ch == k])


@h("first_error: first closer right after an opener of another kind", "bracket_match")
def _(s, q):
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    for i in range(1, len(t)):
        if t[i] in CLOSE and t[i - 1] in OPEN and OPEN.index(t[i - 1]) != CLOSE.index(t[i]):
            return str(i + 1)
    return None


@h("first_error: first closer whose kind differs from the latest opener written before it", "bracket_match")
def _(s, q):
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    last = None
    for i, c in enumerate(t):
        if c in OPEN:
            last = c
        elif last is not None and OPEN.index(last) != CLOSE.index(c):
            return str(i + 1)
    return None


@h("first_error: first closer of a kind whose running count goes negative", "bracket_match")
def _(s, q):
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    cnt = Counter()
    for i, c in enumerate(t):
        if c in OPEN:
            cnt[c] += 1
        else:
            cnt[OPEN[CLOSE.index(c)]] -= 1
            if cnt[OPEN[CLOSE.index(c)]] < 0:
                return str(i + 1)
    return None


@h("first_error: first closer that differs in kind from the previous closer and follows a closer", "bracket_match")
def _(s, q):
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    for i in range(1, len(t)):
        if t[i] in CLOSE and t[i - 1] in CLOSE and t[i] != t[i - 1]:
            return str(i + 1)
    return None


@h("first_error: same-depth matching ignoring kinds, first kind mismatch (P)", "bracket_match")
def _(s, q):
    if s["ask"] != "first_error":
        return None
    t = s["s"]
    st = []
    for i, c in enumerate(t):
        if c in OPEN:
            st.append(c)
        else:
            o = st.pop()
            if OPEN.index(o) != CLOSE.index(c):
                return str(i + 1)
    return None


# ---------------------------------------------------------------- bst_traversal
@h("insertion order", "bst_traversal")
def _(s, q):
    return L(s["xs"])


@h("sorted ascending", "bst_traversal")
def _(s, q):
    return L(sorted(s["xs"]))


@h("reverse insertion order", "bst_traversal")
def _(s, q):
    return L(s["xs"][::-1])


@h("root, then the smaller ones in insertion order, then the larger ones (one split)", "bst_traversal")
def _(s, q):
    xs = s["xs"]
    r = xs[0]
    a, b = [x for x in xs[1:] if x < r], [x for x in xs[1:] if x > r]
    if s["kind"] == "post":
        return L(a + b + [r])
    return L([r] + a + b)


@h("root, then smaller sorted, then larger sorted", "bst_traversal")
def _(s, q):
    xs = s["xs"]
    r = xs[0]
    a, b = sorted(x for x in xs[1:] if x < r), sorted(x for x in xs[1:] if x > r)
    if s["kind"] == "post":
        return L(a + b + [r])
    return L([r] + a + b)


# ---------------------------------------------------------------- min_heap_ops
def _floyd(xs):
    h = list(xs)
    n = len(h)
    for i in range(n // 2 - 1, -1, -1):
        j = i
        while 2 * j + 1 < n:
            c = 2 * j + 1
            if c + 1 < n and h[c + 1] < h[c]:
                c += 1
            if h[c] < h[j]:
                h[c], h[j] = h[j], h[c]
                j = c
            else:
                break
    return h


def _pop(h):
    h = list(h)
    h[0] = h[-1]
    h.pop()
    n = len(h)
    j = 0
    while 2 * j + 1 < n:
        c = 2 * j + 1
        if c + 1 < n and h[c + 1] < h[c]:
            c += 1
        if h[c] < h[j]:
            h[c], h[j] = h[j], h[c]
            j = c
        else:
            break
    return h


@h("sorted ascending (after removals)", "min_heap_ops")
def _(s, q):
    return L(sorted(s["xs"])[s["removals"] :])


@h("insertion order (minus removed smallest)", "min_heap_ops")
def _(s, q):
    xs = list(s["xs"])
    for _ in range(s["removals"]):
        xs.remove(min(xs))
    return L(xs)


@h("Floyd bottom-up heapify, then removals (a different construction)", "min_heap_ops")
def _(s, q):
    h = _floyd(s["xs"])
    for _ in range(s["removals"]):
        h = _pop(h)
    return L(h)


@h("[cond] sift-up inserts, removal = delete position 1 and shift left (items with removals)", "min_heap_ops")
def _(s, q):
    if s["removals"] == 0:
        return None
    h = []
    for x in s["xs"]:
        h.append(x)
        i = len(h) - 1
        while i > 0 and h[i] < h[(i - 1) // 2]:
            h[i], h[(i - 1) // 2] = h[(i - 1) // 2], h[i]
            i = (i - 1) // 2
    for _ in range(s["removals"]):
        h = h[1:]
    return L(h)


# ---------------------------------------------------------------- hash_probe
def _place(keys, m, wrap=True, order=None):
    tab = [None] * m
    for k in keys if order is None else order:
        i = k % m
        while tab[i] is not None:
            i += 1
            if i == m:
                if not wrap:
                    return None
                i = 0
        tab[i] = k
    return tab


def _tab_ans(s, tab):
    if tab is None:
        return None
    if s["ask"] == "table":
        return ", ".join("-" if x is None else str(x) for x in tab)
    return str(sum(i for i, x in enumerate(tab) if x is not None))


@h("(P) misread: keys placed in order of their home slot", "hash_probe")
def _(s, q):
    return _tab_ans(s, _place(s["keys"], s["m"], order=sorted(s["keys"], key=lambda k: (k % s["m"], s["keys"].index(k)))))


@h("(P) misread: keys added in reverse order", "hash_probe")
def _(s, q):
    return _tab_ans(s, _place(s["keys"], s["m"], order=s["keys"][::-1]))


@h("(P) misread: collision goes to the next slot DOWN", "hash_probe")
def _(s, q):
    m = s["m"]
    tab = [None] * m
    for k in s["keys"]:
        i = k % m
        while tab[i] is not None:
            i = (i - 1) % m
        tab[i] = k
    return _tab_ans(s, tab)


@h("checksum: sum of the home slots", "hash_probe")
def _(s, q):
    return str(sum(k % s["m"] for k in s["keys"])) if s["ask"] == "checksum" else None


@h("checksum: sum of the distinct home slots", "hash_probe")
def _(s, q):
    return str(sum({k % s["m"] for k in s["keys"]})) if s["ask"] == "checksum" else None


@h("checksum: occupied set by any order (P)", "hash_probe")
def _(s, q):
    if s["ask"] != "checksum":
        return None
    return _tab_ans(s, _place(s["keys"], s["m"], order=sorted(s["keys"])))


@h("table: each key at its home, collisions dropped", "hash_probe")
def _(s, q):
    if s["ask"] != "table":
        return None
    m = s["m"]
    tab = [None] * m
    for k in s["keys"]:
        if tab[k % m] is None:
            tab[k % m] = k
    return _tab_ans(s, tab)


# ---------------------------------------------------------------- cache_eviction
def _cache(seq, cap, pol):
    stamp, ev = {}, []
    for t, x in enumerate(seq):
        if x in stamp:
            if pol == "lru":
                stamp[x] = t
            continue
        if len(stamp) == cap:
            o = min(stamp, key=stamp.get)
            ev.append(o)
            del stamp[o]
        stamp[x] = t
    return ev, sorted(stamp, key=stamp.get)


@h("(P) misread: the other policy", "cache_eviction")
def _(s, q):
    ev, c = _cache(s["seq"], s["cap"], "fifo" if s["policy"] == "lru" else "lru")
    return ", ".join(ev if s["ask"] == "evicted" else c)


@h("contents: last cap distinct items, by latest request", "cache_eviction")
def _(s, q):
    if s["ask"] != "contents":
        return None
    seen = []
    for x in reversed(s["seq"]):
        if x not in seen:
            seen.append(x)
        if len(seen) == s["cap"]:
            break
    return ", ".join(reversed(seen))


@h("contents: last cap distinct items, by first appearance within the tail", "cache_eviction")
def _(s, q):
    if s["ask"] != "contents":
        return None
    seen = []
    for x in reversed(s["seq"]):
        if x not in seen:
            seen.append(x)
        if len(seen) == s["cap"]:
            break
    order = []
    for x in s["seq"]:
        if x in seen and x not in order:
            order.append(x)
    # order of first appearance in the whole sequence
    return ", ".join(order)


@h("evicted: distinct items in order of first request, minus the final cache", "cache_eviction")
def _(s, q):
    if s["ask"] != "evicted":
        return None
    _ev, c = _cache(s["seq"], s["cap"], s["policy"])
    out = []
    for x in s["seq"]:
        if x not in out:
            out.append(x)
    return ", ".join(x for x in out if x not in c)


@h("evicted: every miss after the cache fills evicts the item loaded cap misses earlier (miss list shifted)", "cache_eviction")
def _(s, q):
    if s["ask"] != "evicted":
        return None
    seen, misses = [], []
    # misses counted as 'first time requested' only
    for x in s["seq"]:
        if x not in seen:
            seen.append(x)
            misses.append(x)
    return ", ".join(misses[: max(0, len(misses) - s["cap"])])


# ---------------------------------------------------------------- caesar_shift
@h("(P) misread: shift backward", "caesar_shift")
def _(s, q):
    return "".join(c if c == " " else chr((ord(c) - 97 - s["k"]) % 26 + 97) for c in s["text"])


# ---------------------------------------------------------------- cellular_automaton
def _ca(row, tab, steps, mode):
    cur = list(row)
    n = len(cur)
    for _ in range(steps):
        nxt = []
        for i in range(n):
            l = cur[i - 1] if i > 0 else (cur[-1] if mode == "ring" else 0)
            r = cur[i + 1] if i < n - 1 else (cur[0] if mode == "ring" else 0)
            key = f"{l}{cur[i]}{r}" if mode != "mirror" else f"{r}{cur[i]}{l}"
            nxt.append(tab[key])
        cur = nxt
    return "".join(map(str, cur))


@h("(P) misread: ring edge", "cellular_automaton")
def _(s, q):
    return _ca(s["row"], s["table"], s["steps"], "ring")


@h("(P) misread: table read right-to-left", "cellular_automaton")
def _(s, q):
    return _ca(s["row"], s["table"], s["steps"], "mirror")


@h("(P) misread: one step fewer", "cellular_automaton")
def _(s, q):
    return _ca(s["row"], s["table"], s["steps"] - 1, "zero")


@h("(P) misread: one step more", "cellular_automaton")
def _(s, q):
    return _ca(s["row"], s["table"], s["steps"] + 1, "zero")


@h("(P) misread: edge cells keep their value", "cellular_automaton")
def _(s, q):
    cur = list(s["row"])
    n = len(cur)
    for _ in range(s["steps"]):
        cur = [cur[0]] + [s["table"][f"{cur[i-1]}{cur[i]}{cur[i+1]}"] for i in range(1, n - 1)] + [cur[-1]]
    return "".join(map(str, cur))


# ---------------------------------------------------------------- cheapest_network
def _mst(names, cab):
    par = {x: x for x in names}

    def f(x):
        while par[x] != x:
            x = par[x]
        return x

    tot = 0
    for a, b, w in sorted(cab, key=lambda c: c[2]):
        ra, rb = f(a), f(b)
        if ra != rb:
            par[ra] = rb
            tot += w
    return tot


@h("n-1 cheapest cables", "cheapest_network")
def _(s, q):
    return str(sum(sorted(c[2] for c in s["cables"])[: len(s["towns"]) - 1]))


@h("each town's cheapest cable, distinct cables summed", "cheapest_network")
def _(s, q):
    pick = set()
    for t in s["towns"]:
        c = min((c for c in s["cables"] if t in c[:2]), key=lambda c: c[2])
        pick.add(tuple(c))
    return str(sum(c[2] for c in pick))


@h("each town's cheapest cable except one town, summed (n-1 values)", "cheapest_network")
def _(s, q):
    vals = sorted(min(c[2] for c in s["cables"] if t in c[:2]) for t in s["towns"])
    return str(sum(vals[:-1]))


@h("(P) Kruskal", "cheapest_network")
def _(s, q):
    return str(_mst(s["towns"], s["cables"]))


# ---------------------------------------------------------------- coin_change_min
def _greedy(coins, a):
    n = 0
    for c in sorted(coins, reverse=True):
        n += a // c
        a %= c
    return n if a == 0 else None


@h("largest-first greedy per amount", "coin_change_min")
def _(s, q):
    out = [_greedy(s["coins"], a) for a in s["amounts"]]
    return None if None in out else L(out)


@h("ceil(amount / largest coin) per amount", "coin_change_min")
def _(s, q):
    return L([-(-a // max(s["coins"])) for a in s["amounts"]])


@h("greedy largest-first, falling back to the next coin when stuck", "coin_change_min")
def _(s, q):
    out = []
    cs = sorted(s["coins"], reverse=True)
    for a in s["amounts"]:
        best = None
        for start in range(len(cs)):
            g = _greedy(cs[start:], a)
            if g is not None:
                best = g
                break
        if best is None:
            return None
        out.append(best)
    return L(out)


@h("greedy with one fewer of the largest coin allowed (best of k, k-1 largest)", "coin_change_min")
def _(s, q):
    out = []
    cs = sorted(s["coins"], reverse=True)
    for a in s["amounts"]:
        cands = []
        for d in range(0, 3):
            k = a // cs[0] - d
            if k < 0:
                continue
            g = _greedy(cs[1:], a - k * cs[0])
            if g is not None:
                cands.append(k + g)
        if not cands:
            return None
        out.append(min(cands))
    return L(out)


# ---------------------------------------------------------------- count_letter / count_divisible
@h("words containing the letter", "count_letter")
def _(s, q):
    return str(sum(s["letter"] in w for w in s["words"]))


@h("words containing the letter + 1", "count_letter")
def _(s, q):
    return str(sum(s["letter"] in w for w in s["words"]) + 1)


@h("number of words", "count_letter")
def _(s, q):
    return str(len(s["words"]))


@h(">= t", "count_divisible")
def _(s, q):
    return str(sum(x for x in s["xs"] if x % s["m"] == 0 and x >= s["t"]))


@h("ignore the threshold", "count_divisible")
def _(s, q):
    return str(sum(x for x in s["xs"] if x % s["m"] == 0))


@h("ignore divisibility", "count_divisible")
def _(s, q):
    return str(sum(x for x in s["xs"] if x > s["t"]))


@h("count instead of sum", "count_divisible")
def _(s, q):
    return str(sum(1 for x in s["xs"] if x % s["m"] == 0 and x > s["t"]))


# ---------------------------------------------------------------- crt
@h("first remainder + first modulus x second remainder", "crt_smallest")
def _(s, q):
    (r1, m1), (r2, m2) = s["congruences"][:2]
    return str(r1 + m1 * r2)


@h("largest remainder", "crt_smallest")
def _(s, q):
    return str(max(r for r, m in s["congruences"]))


# ---------------------------------------------------------------- dictionary_rank
@h("word: right first letter, rest ascending", "dictionary_rank")
def _(s, q):
    if s["ask"] != "word":
        return None
    letters, ln, k = s["letters"], s["length"], s["k"]
    block = math.perm(len(letters) - 1, ln - 1)
    f = letters[(k - 1) // block]
    rest = [x for x in letters if x != f][: ln - 1]
    return f + "".join(rest)


@h("position: first letter only (index x block + 1)", "dictionary_rank")
def _(s, q):
    if s["ask"] != "position":
        return None
    letters, ln, w = s["letters"], s["length"], s["word"]
    return str(letters.index(w[0]) * math.perm(len(letters) - 1, ln - 1) + 1)


@h("position: (n-1)! radix instead of falling factorials", "dictionary_rank")
def _(s, q):
    if s["ask"] != "position":
        return None
    pool, w = list(s["letters"]), s["word"]
    k = 0
    for i, c in enumerate(w):
        j = pool.index(c)
        k += j * math.factorial(len(pool) - 1)
        pool.pop(j)
    return str(k + 1)


# ---------------------------------------------------------------- digit_root
@h("n mod 9 (0 -> 9) (P)", "digit_root")
def _(s, q):
    return str(1 + (s["n"] - 1) % 9)


@h("digit sum once, last digit", "digit_root")
def _(s, q):
    return str(sum(map(int, str(s["n"]))) % 10)


# ---------------------------------------------------------------- expression_eval
def _toks(t):
    return re.findall(r"\d+|[()+\-*]", t)


def _ev(t, mode):
    toks = _toks(t)
    pos = [0]

    def atom():
        tk = toks[pos[0]]
        pos[0] += 1
        if tk == "(":
            v = top()
            pos[0] += 1
            return v
        return int(tk)

    def ltr():
        v = atom()
        while pos[0] < len(toks) and toks[pos[0]] in "+-*":
            op = toks[pos[0]]
            pos[0] += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    def term():
        v = atom()
        while pos[0] < len(toks) and toks[pos[0]] == "*":
            pos[0] += 1
            v *= atom()
        return v

    def ranked():
        v = term()
        while pos[0] < len(toks) and toks[pos[0]] in "+-":
            op = toks[pos[0]]
            pos[0] += 1
            w = term()
            v = v + w if op == "+" else v - w
        return v

    def plusfirst():
        # products first, then all + before any -, i.e. a - b + c = a - (b + c)
        terms = [term()]
        ops = []
        while pos[0] < len(toks) and toks[pos[0]] in "+-":
            ops.append(toks[pos[0]])
            pos[0] += 1
            terms.append(term())
        v = terms[0]
        i = 0
        while i < len(ops):
            if ops[i] == "+":
                v += terms[i + 1]
                i += 1
            else:
                w = terms[i + 1]
                j = i + 1
                while j < len(ops) and ops[j] == "+":
                    w += terms[j + 1]
                    j += 1
                v -= w
                i = j
        return v

    top = {"ltr": ltr, "ranked": ranked, "plusfirst": plusfirst}[mode]
    return top()


@h("the other convention", "expression_eval")
def _(s, q):
    return str(_ev(s["text"], "ltr" if s["convention"] == "ranked" else "ranked"))


@h("parentheses ignored (stated convention)", "expression_eval")
def _(s, q):
    t = s["text"].replace("(", "").replace(")", "")
    return str(_ev(t, "ranked" if s["convention"] == "ranked" else "ltr"))


@h("ranked: + before -", "expression_eval")
def _(s, q):
    if s["convention"] != "ranked":
        return None
    return str(_ev(s["text"], "plusfirst"))


@h("left_to_right: usual precedence inside parentheses only", "expression_eval")
def _(s, q):
    if s["convention"] != "left_to_right":
        return None
    t = re.sub(r"\(([^()]*)\)", lambda m: str(_ev(m.group(1), "ranked")), s["text"])
    return str(_ev(t, "ltr"))


# ---------------------------------------------------------------- base conversions
@h("(P) misread: digits read right to left", "from_base")
def _(s, q):
    return str(int(s["digits"][::-1], s["base"]))


@h("digits read as decimal", "from_base")
def _(s, q):
    return s["digits"] if s["digits"].isdigit() else None


@h("(P) misread: digits reversed", "to_base_wide")
def _(s, q):
    n, b = s["n"], s["base"]
    out = ""
    while n:
        out += "0123456789abcdef"[n % b]
        n //= b
    return out


# ---------------------------------------------------------------- gcd_euclid
def _fac(n):
    f = Counter()
    d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] += 1
            n //= d
        d += 1
    if n > 1:
        f[n] += 1
    return f


@h("gcd: one Euclid step (a mod b)", "gcd_euclid")
def _(s, q):
    return str(s["a"] % s["b"]) if s["ask"] == "gcd" else None


@h("gcd: a - b", "gcd_euclid")
def _(s, q):
    return str(s["a"] - s["b"]) if s["ask"] == "gcd" else None


@h("gcd: smallest common prime factor", "gcd_euclid")
def _(s, q):
    if s["ask"] != "gcd":
        return None
    c = set(_fac(s["a"])) & set(_fac(s["b"]))
    return str(min(c)) if c else "1"


@h("gcd/lcm via common prime powers over primes <= 7 only", "gcd_euclid")
def _(s, q):
    g = 1
    for p in (2, 3, 5, 7):
        ea = eb = 0
        a, b = s["a"], s["b"]
        while a % p == 0:
            a //= p
            ea += 1
        while b % p == 0:
            b //= p
            eb += 1
        g *= p ** min(ea, eb)
    return str(g) if s["ask"] == "gcd" else str(s["a"] * s["b"] // g)


@h("gcd/lcm via full factorisation (P)", "gcd_euclid")
def _(s, q):
    fa, fb = _fac(s["a"]), _fac(s["b"])
    g = 1
    for p in fa:
        g *= p ** min(fa[p], fb.get(p, 0))
    return str(g) if s["ask"] == "gcd" else str(s["a"] * s["b"] // g)


@h("lcm: a x b", "gcd_euclid")
def _(s, q):
    return str(s["a"] * s["b"]) if s["ask"] == "lcm" else None


@h("lcm: a x b / (a - b)", "gcd_euclid")
def _(s, q):
    return str(s["a"] * s["b"] // (s["a"] - s["b"])) if s["ask"] == "lcm" else None


# ---------------------------------------------------------------- grid_sum
@h("row and column swapped", "grid_sum")
def _(s, q):
    g, w = s["grid"], s["what"]
    m = re.match(r"(row|column) (\d+)", w)
    if not m:
        return None
    i = int(m.group(2)) - 1
    if m.group(1) == "row":
        return str(sum(r[i] for r in g)) if i < len(g[0]) else None
    return str(sum(g[i])) if i < len(g) else None


# ---------------------------------------------------------------- hamming
@h("position of the first failing check", "hamming_error_position")
def _(s, q):
    w, n = s["bits"], s["n"]
    p = 1
    while p <= n:
        if sum(w[i - 1] for i in range(1, n + 1) if i & p) % 2:
            return str(p)
        p *= 2
    return "0"


@h("(P) misread: syndrome with bit order reversed", "hamming_error_position")
def _(s, q):
    w, n = s["bits"], s["n"]
    v = 0
    for pos, b in enumerate(w, 1):
        if b:
            v ^= pos
    k = n.bit_length()
    return str(int(format(v, f"0{k}b")[::-1], 2))


# ---------------------------------------------------------------- interval_scheduling
def _greedy_iv(iv, key):
    taken = []
    for i in sorted(range(len(iv)), key=key):
        a, b = iv[i]
        if all(b <= iv[j][0] or a >= iv[j][1] for j in taken):
            taken.append(i)
    return L(sorted(i + 1 for i in taken))


@h("shortest first", "interval_scheduling")
def _(s, q):
    iv = s["meetings"]
    return _greedy_iv(iv, lambda i: (iv[i][1] - iv[i][0], i))


@h("earliest start first", "interval_scheduling")
def _(s, q):
    iv = s["meetings"]
    return _greedy_iv(iv, lambda i: (iv[i][0], i))


@h("latest start first (mirror greedy; a maximum set, not the stated one)", "interval_scheduling")
def _(s, q):
    iv = s["meetings"]
    return _greedy_iv(iv, lambda i: (-iv[i][0], i))


@h("(P) misread: earliest finish, ties to the LARGER number", "interval_scheduling")
def _(s, q):
    iv = s["meetings"]
    return _greedy_iv(iv, lambda i: (iv[i][1], -i))


@h("(P) misread: earliest finish, touching counts as a clash", "interval_scheduling")
def _(s, q):
    iv = s["meetings"]
    taken = []
    for i in sorted(range(len(iv)), key=lambda i: (iv[i][1], i)):
        a, b = iv[i]
        if all(b < iv[j][0] or a > iv[j][1] for j in taken):
            taken.append(i)
    return L(sorted(i + 1 for i in taken))


@h("(P) misread: earliest finish, ties broken by later start", "interval_scheduling")
def _(s, q):
    iv = s["meetings"]
    return _greedy_iv(iv, lambda i: (iv[i][1], -iv[i][0], i))


# ---------------------------------------------------------------- kth_smallest / sort_list
@h("k-th number in list order", "kth_smallest")
def _(s, q):
    return str(s["xs"][s["k"] - 1])


@h("(P) misread: k-th largest", "kth_smallest")
def _(s, q):
    return str(sorted(s["xs"], reverse=True)[s["k"] - 1])


@h("(P) misread: off by one (k-1 or k+1)", "kth_smallest")
def _(s, q):
    xs, k = sorted(s["xs"]), s["k"]
    j = k - 2 if k - 1 > len(xs) / 2 else k
    return str(xs[j])


@h("list value nearest to the quantile 500 k/(n+1)", "kth_smallest")
def _(s, q):
    xs, k = s["xs"], s["k"]
    tgt = 500 * k / (len(xs) + 1)
    return str(min(xs, key=lambda x: abs(x - tgt)))


@h("list value nearest to the quantile min + (max-min)(k-1)/(n-1)", "kth_smallest")
def _(s, q):
    xs, k = s["xs"], s["k"]
    lo, hi = min(xs), max(xs)
    tgt = lo + (hi - lo) * (k - 1) / (len(xs) - 1)
    return str(min(xs, key=lambda x: abs(x - tgt)))


@h("(P) misread: opposite direction", "sort_list")
def _(s, q):
    return L(sorted(s["xs"], reverse=not s["desc"]))


# ---------------------------------------------------------------- lcs_length
def _greedy_lcs(a, b):
    i = n = 0
    for c in a:
        j = b.find(c, i)
        if j >= 0:
            n += 1
            i = j + 1
    return n


@h("greedy matching, better of both directions", "lcs_length")
def _(s, q):
    return str(max(_greedy_lcs(s["a"], s["b"]), _greedy_lcs(s["b"], s["a"])))


@h("common letters counted with multiplicity", "lcs_length")
def _(s, q):
    return str(sum((Counter(s["a"]) & Counter(s["b"])).values()))


@h("round(0.6 x shorter length)", "lcs_length")
def _(s, q):
    return str(round(0.6 * min(len(s["a"]), len(s["b"]))))


@h("greedy matching from both ends, best", "lcs_length")
def _(s, q):
    a, b = s["a"], s["b"]
    return str(max(_greedy_lcs(a, b), _greedy_lcs(b, a), _greedy_lcs(a[::-1], b[::-1]), _greedy_lcs(b[::-1], a[::-1])))


# ---------------------------------------------------------------- lis_length
@h("greedy: take every number larger than the last taken", "lis_length")
def _(s, q):
    n, last = 0, -math.inf
    for x in s["xs"]:
        if x > last:
            n += 1
            last = x
    return str(n)


@h("ascents + 1", "lis_length")
def _(s, q):
    xs = s["xs"]
    return str(1 + sum(xs[i + 1] > xs[i] for i in range(len(xs) - 1)))


@h("best greedy over every starting number", "lis_length")
def _(s, q):
    xs = s["xs"]
    best = 0
    for st in range(len(xs)):
        n, last = 0, -math.inf
        for x in xs[st:]:
            if x > last:
                n += 1
                last = x
        best = max(best, n)
    return str(best)


@h("best greedy-skip: from each start take the next number if it is the smallest larger one ahead", "lis_length")
def _(s, q):
    xs = s["xs"]
    best = 0
    for st in range(len(xs)):
        n, last = 1, xs[st]
        for x in xs[st + 1 :]:
            if x > last:
                n += 1
                last = x
        best = max(best, n)
    return str(best)


@h("round(2 sqrt n)", "lis_length")
def _(s, q):
    return str(round(2 * math.sqrt(len(s["xs"]))))


# ---------------------------------------------------------------- list_ops
def _ops(xs, ops, skip):
    xs = list(xs)
    for op in ops:
        o = op[0]
        if o in skip:
            continue
        if o == "reverse":
            xs = xs[::-1]
        elif o == "drop_first":
            xs = xs[1:]
        elif o == "drop_last":
            xs = xs[:-1]
        elif o == "append":
            xs = xs + [op[1]]
        else:
            xs = xs[1:] + xs[:1]
    return L(xs)


@h("[cond] ignore reverses (items with a reverse)", "list_ops")
def _(s, q):
    if not any(o[0] == "reverse" for o in s["ops"]):
        return None
    return _ops(s["xs"], s["ops"], {"reverse"})


@h("[cond] ignore moves (items with a move)", "list_ops")
def _(s, q):
    if not any(o[0] == "first_to_end" for o in s["ops"]):
        return None
    return _ops(s["xs"], s["ops"], {"first_to_end"})


@h("[cond] append = put at the front (items with an append)", "list_ops")
def _(s, q):
    if not any(o[0] == "append" for o in s["ops"]):
        return None
    xs = list(s["xs"])
    for op in s["ops"]:
        o = op[0]
        if o == "reverse":
            xs = xs[::-1]
        elif o == "drop_first":
            xs = xs[1:]
        elif o == "drop_last":
            xs = xs[:-1]
        elif o == "append":
            xs = [op[1]] + xs
        else:
            xs = xs[1:] + xs[:1]
    return L(xs)


# ---------------------------------------------------------------- longest_palindromic_substring
def _lp(s, odd, even):
    best = 1
    for c in range(len(s)):
        for lo, hi, ok in ((c, c, odd), (c, c + 1, even)):
            if not ok:
                continue
            while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
                lo -= 1
                hi += 1
            best = max(best, hi - lo - 1)
    return best


@h("odd-length centres only", "longest_palindromic_substring")
def _(s, q):
    return str(_lp(s["s"], True, False))


@h("even-length centres only", "longest_palindromic_substring")
def _(s, q):
    return str(_lp(s["s"], False, True))


@h("longest run of one letter", "longest_palindromic_substring")
def _(s, q):
    return str(max(len(list(g)) for _, g in itertools.groupby(s["s"])))


@h("longest palindrome of length <= 7 (short windows only)", "longest_palindromic_substring")
def _(s, q):
    t = s["s"]
    best = 1
    for i in range(len(t)):
        for j in range(i + 1, min(len(t), i + 7) + 1):
            if t[i:j] == t[i:j][::-1]:
                best = max(best, j - i)
    return str(best)


# ---------------------------------------------------------------- luhn
def _lt(ds, from_left=False, plain=False):
    t = 0
    seq = ds if from_left else list(reversed(ds))
    for i, d in enumerate(seq, 1):
        if not plain and i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        t += d
    return t


@h("plain digit sum", "luhn_check")
def _(s, q):
    ds = s["digits"]
    if s["ask"] == "valid":
        return "yes" if _lt(ds, plain=True) % 10 == 0 else "no"
    return str(-_lt(ds, plain=True) % 10)


@h("(P) misread: doubling counted from the left", "luhn_check")
def _(s, q):
    ds = s["digits"]
    if s["ask"] == "valid":
        return "yes" if _lt(ds, from_left=True) % 10 == 0 else "no"
    return str(-_lt(ds + [0], from_left=True) % 10)


@h("check digit: payload's own last digit not doubled", "luhn_check")
def _(s, q):
    if s["ask"] != "check_digit":
        return None
    return str(-_lt(s["digits"]) % 10)


# ---------------------------------------------------------------- max_subarray_sum
@h("segments cut at two adjacent negatives, trimmed, best segment total", "max_subarray_sum")
def _(s, q):
    xs = s["xs"]
    segs, cur = [], []
    i = 0
    while i < len(xs):
        if xs[i] < 0 and i + 1 < len(xs) and xs[i + 1] < 0:
            if cur:
                segs.append(cur)
            cur = []
            while i < len(xs) and xs[i] < 0:
                i += 1
            continue
        cur.append(xs[i])
        i += 1
    if cur:
        segs.append(cur)
    best = -math.inf
    for sg in segs:
        while sg and sg[0] < 0:
            sg = sg[1:]
        while sg and sg[-1] < 0:
            sg = sg[:-1]
        if sg:
            best = max(best, sum(sg))
    return str(best) if best > -math.inf else None


@h("best run of non-negative numbers", "max_subarray_sum")
def _(s, q):
    best = cur = 0
    for x in s["xs"]:
        cur = cur + x if x >= 0 else 0
        best = max(best, cur)
    return str(best)


@h("sum of the positive numbers in the best stretch with no two adjacent negatives", "max_subarray_sum")
def _(s, q):
    xs = s["xs"]
    best, cur = 0, []
    i = 0
    stretches = []
    while i < len(xs):
        if xs[i] < 0 and i + 1 < len(xs) and xs[i + 1] < 0:
            stretches.append(cur)
            cur = []
            while i < len(xs) and xs[i] < 0:
                i += 1
            continue
        cur.append(xs[i])
        i += 1
    stretches.append(cur)
    return str(max(sum(x for x in st if x > 0) for st in stretches))


# ---------------------------------------------------------------- merge_smallest_cost
@h("sorted, merged one after another (caterpillar)", "merge_smallest_cost")
def _(s, q):
    ws = sorted(s["ws"])
    tot, cur = 0, ws[0]
    for w in ws[1:]:
        cur += w
        tot += cur
    return str(tot)


@h("merged in list order", "merge_smallest_cost")
def _(s, q):
    ws = s["ws"]
    tot, cur = 0, ws[0]
    for w in ws[1:]:
        cur += w
        tot += cur
    return str(tot)


@h("total x (n-1)", "merge_smallest_cost")
def _(s, q):
    return str(sum(s["ws"]) * (len(s["ws"]) - 1))


@h("total x ceil(log2 n)", "merge_smallest_cost")
def _(s, q):
    return str(sum(s["ws"]) * math.ceil(math.log2(len(s["ws"]))))


@h("merge the two smallest once, then caterpillar", "merge_smallest_cost")
def _(s, q):
    ws = sorted(s["ws"])
    first = ws[0] + ws[1]
    rest = sorted(ws[2:] + [first])
    tot, cur = first, rest[0]
    for w in rest[1:]:
        cur += w
        tot += cur
    return str(tot)


@h("pairwise rounds (merge neighbours in sorted order, round by round)", "merge_smallest_cost")
def _(s, q):
    ws = sorted(s["ws"])
    tot = 0
    while len(ws) > 1:
        nxt = []
        for i in range(0, len(ws) - 1, 2):
            nxt.append(ws[i] + ws[i + 1])
            tot += ws[i] + ws[i + 1]
        if len(ws) % 2:
            nxt.append(ws[-1])
        ws = sorted(nxt)
    return str(tot)


# ---------------------------------------------------------------- modular_power
def _phi(m):
    f = _fac(m)
    r = m
    for p in f:
        r = r // p * (p - 1)
    return r


@h("Fermat with m-1 (not valid: m composite)", "modular_power")
def _(s, q):
    return str(pow(s["a"], s["e"] % (s["m"] - 1), s["m"]))


@h("(P) Euler: exponent mod phi(m)", "modular_power")
def _(s, q):
    return str(pow(s["a"], s["e"] % _phi(s["m"]), s["m"]))


@h("(P) Carmichael: exponent mod lambda(m)", "modular_power")
def _(s, q):
    f = _fac(s["m"])
    lam = math.lcm(*[p - 1 for p in f])
    return str(pow(s["a"], s["e"] % lam, s["m"]))


@h("a^2 mod m", "modular_power")
def _(s, q):
    return str(s["a"] ** 2 % s["m"])


@h("a mod m", "modular_power")
def _(s, q):
    return str(s["a"] % s["m"])


@h("a^(e mod 10) mod m", "modular_power")
def _(s, q):
    return str(pow(s["a"], s["e"] % 10, s["m"]))


# ---------------------------------------------------------------- multiples_between
@h("count: b//m - a//m", "multiples_between")
def _(s, q):
    return str(s["b"] // s["m"] - s["a"] // s["m"]) if s["ask"] == "count" else None


@h("count: round((b-a+1)/m)", "multiples_between")
def _(s, q):
    return str(round((s["b"] - s["a"] + 1) / s["m"])) if s["ask"] == "count" else None


@h("count: (b-a)/m + 1 (P: the counting rule with both ends multiples)", "multiples_between")
def _(s, q):
    return str((s["b"] - s["a"]) // s["m"] + 1) if s["ask"] == "count" else None


@h("sum: (a+b)/2 x (b-a)/m (fencepost dropped)", "multiples_between")
def _(s, q):
    return str((s["a"] + s["b"]) * ((s["b"] - s["a"]) // s["m"]) // 2) if s["ask"] == "sum" else None


@h("sum: (a+b)/2 x ((b-a)/m+1) (P)", "multiples_between")
def _(s, q):
    return str((s["a"] + s["b"]) * ((s["b"] - s["a"]) // s["m"] + 1) // 2) if s["ask"] == "sum" else None


# ---------------------------------------------------------------- palindrome_check
def _ph(s):
    return s["phrase"].replace(" ", "")


@h("letter counts allow a palindrome", "palindrome_check")
def _(s, q):
    t = _ph(s)
    return "yes" if sum(v % 2 for v in Counter(t).values()) <= 1 else "no"


@h("outer 3 letter pairs", "palindrome_check")
def _(s, q):
    t = _ph(s)
    return "yes" if all(t[i] == t[-1 - i] for i in range(3)) else "no"


@h("outer 5 letter pairs", "palindrome_check")
def _(s, q):
    t = _ph(s)
    return "yes" if all(t[i] == t[-1 - i] for i in range(5)) else "no"


@h("halves have the same letters (multiset)", "palindrome_check")
def _(s, q):
    t = _ph(s)
    h = len(t) // 2
    return "yes" if Counter(t[:h]) == Counter(t[-h:]) else "no"


@h("words mirror word-by-word lengths and first/last letters", "palindrome_check")
def _(s, q):
    ws = s["phrase"].split()
    return "yes" if (ws[0][0] == ws[-1][-1] and ws[0][-1] == ws[-1][0]) else "no"


@h("outer 8 letter pairs", "palindrome_check")
def _(s, q):
    t = _ph(s)
    return "yes" if all(t[i] == t[-1 - i] for i in range(8)) else "no"


@h("middle 3 letter pairs", "palindrome_check")
def _(s, q):
    t = _ph(s)
    h = len(t) // 2
    return "yes" if all(t[h - 1 - i] == t[len(t) - h + i] for i in range(3)) else "no"


# ---------------------------------------------------------------- permutation_power
def _app(img, s, t):
    for _ in range(t):
        s = img[s - 1]
    return s


@h("the start", "permutation_power")
def _(s, q):
    return str(s["s"])


@h("one application", "permutation_power")
def _(s, q):
    return str(s["img"][s["s"] - 1])


@h("t mod n applications", "permutation_power")
def _(s, q):
    return str(_app(s["img"], s["s"], s["t"] % len(s["img"])))


@h("t mod (n-1) applications (cycle length assumed n-1; valid when only one number is off the long cycle)", "permutation_power")
def _(s, q):
    return str(_app(s["img"], s["s"], s["t"] % (len(s["img"]) - 1)))


@h("t mod 10 applications", "permutation_power")
def _(s, q):
    return str(_app(s["img"], s["s"], s["t"] % 10))


@h("inverse mapping t times", "permutation_power")
def _(s, q):
    inv = [0] * len(s["img"])
    for i, v in enumerate(s["img"], 1):
        inv[v - 1] = i
    return str(_app(inv, s["s"], s["t"]))


# ---------------------------------------------------------------- prime_factor_query
@h("sum: distinct primes", "prime_factor_query")
def _(s, q):
    return str(sum(_fac(s["n"]))) if s["ask"] == "sum_all" else None


@h("largest: largest prime <= 97 dividing n (P)", "prime_factor_query")
def _(s, q):
    return str(max(_fac(s["n"]))) if s["ask"] == "largest" else None


@h("largest: second-largest prime factor", "prime_factor_query")
def _(s, q):
    if s["ask"] != "largest":
        return None
    f = sorted(_fac(s["n"]))
    return str(f[-2]) if len(f) > 1 else None


# ---------------------------------------------------------------- run_length
@h("run-length by grouping (P: the procedure)", "run_length")
def _(s, q):
    return "".join(f"{c}{len(list(g))}" for c, g in itertools.groupby(s["s"]))


# ---------------------------------------------------------------- stack_machine
def _prog(prog, skip=(), subrev=False):
    st = []
    for p in prog:
        o = p[0]
        if o in skip:
            continue
        if o == "push":
            st.append(p[1])
        elif o == "dup":
            st.append(st[-1])
        elif o == "pop":
            st.pop()
        elif o == "swap":
            st[-1], st[-2] = st[-2], st[-1]
        else:
            if len(st) < 2:
                return None
            b, a = st.pop(), st.pop()
            st.append({"add": a + b, "mul": a * b, "sub": (b - a) if subrev else (a - b)}[o])
    return str(st[-1]) if st else None


@h("last pushed value", "stack_machine")
def _(s, q):
    return str([p[1] for p in s["prog"] if p[0] == "push"][-1])


@h("last operation applied to the last two pushed values", "stack_machine")
def _(s, q):
    pv = [p[1] for p in s["prog"] if p[0] == "push"]
    o = s["prog"][-1][0]
    if len(pv) < 2:
        return None
    a, b = pv[-2], pv[-1]
    return str({"add": a + b, "mul": a * b, "sub": a - b}[o])


@h("(P) misread: ignore swaps", "stack_machine")
def _(s, q):
    return _prog(s["prog"], skip=("swap",))


@h("(P) misread: ignore dup and pop", "stack_machine")
def _(s, q):
    return _prog(s["prog"], skip=("dup", "pop"))


@h("(P) misread: subtract = top minus second", "stack_machine")
def _(s, q):
    return _prog(s["prog"], subrev=True)


@h("last op applied to the two values just before it in the text (pushed or computed), ignoring earlier history", "stack_machine")
def _(s, q):
    prog = s["prog"]
    if len(prog) >= 3 and prog[-2][0] == "push" and prog[-3][0] == "push":
        a, b = prog[-3][1], prog[-2][1]
        return str({"add": a + b, "mul": a * b, "sub": a - b}[prog[-1][0]])
    return None


# ---------------------------------------------------------------- string_rewrite_nonidentity
@h("[cond] " + "only the last rule", "string_rewrite_nonidentity")
def _(s, q):
    if len(s["rules"]) < 2:
        return None
    p, t = s["rules"][-1]
    return s["s"].replace(p, t)


@h("[cond] " + "all rules applied to the start string at once (left to right, first matching rule)", "string_rewrite_nonidentity")
def _(s, q):
    if len(s["rules"]) < 2:
        return None
    st, out, i = s["s"], "", 0
    while i < len(st):
        for p, t in s["rules"]:
            if st.startswith(p, i):
                out += t
                i += len(p)
                break
        else:
            out += st[i]
            i += 1
    return out


@h("[cond] " + "rules in reverse order", "string_rewrite_nonidentity")
def _(s, q):
    if len(s["rules"]) < 2:
        return None
    cur = s["s"]
    for p, t in reversed(s["rules"]):
        cur = cur.replace(p, t)
    return cur


# ---------------------------------------------------------------- subtraction_game
def _gr(n, moves):
    g = [0] * (n + 1)
    for x in range(1, n + 1):
        seen = {g[x - m] for m in moves if m <= x}
        v = 0
        while v in seen:
            v += 1
        g[x] = v
    return g


@h("total stones odd -> yes", "subtraction_game")
def _(s, q):
    return "yes" if sum(s["piles"]) % 2 else "no"


@h("xor of pile sizes non-zero -> yes", "subtraction_game")
def _(s, q):
    x = 0
    for p in s["piles"]:
        x ^= p
    return "yes" if x else "no"


@h("xor of (pile mod (largest amount + 1)) non-zero -> yes", "subtraction_game")
def _(s, q):
    x = 0
    for p in s["piles"]:
        x ^= p % (max(s["moves"]) + 1)
    return "yes" if x else "no"


@h("xor of (pile mod (smallest + largest amount)) non-zero -> yes", "subtraction_game")
def _(s, q):
    x = 0
    for p in s["piles"]:
        x ^= p % (min(s["moves"]) + max(s["moves"]))
    return "yes" if x else "no"


@h("odd number of piles that are first-player wins alone -> yes", "subtraction_game")
def _(s, q):
    g = _gr(max(s["piles"]), s["moves"])
    return "yes" if sum(1 for p in s["piles"] if g[p]) % 2 else "no"


@h("sum of position values odd -> yes (P partial bit)", "subtraction_game")
def _(s, q):
    g = _gr(max(s["piles"]), s["moves"])
    return "yes" if sum(g[p] for p in s["piles"]) % 2 else "no"


@h("sum of position values non-zero mod 4... (sum of values) % 4 != 0 -> yes", "subtraction_game")
def _(s, q):
    g = _gr(max(s["piles"]), s["moves"])
    return "yes" if sum(g[p] for p in s["piles"]) % 4 else "no"


@h("1 is an allowed amount and total odd -> yes, else total of piles mod (min amount+1)", "subtraction_game")
def _(s, q):
    mn = min(s["moves"])
    return "yes" if sum(s["piles"]) % (mn + 1) else "no"
