# ruff: noqa
# COPY, with attribution, of docs/reviews/m0-lineage-decision-2026-11-25/audit_r2/heuristics.py (arbor-auditor, Claude Opus 5.5, commit 9e32b317).
# Copied verbatim below this header so that no run imports from the audit folder (lead ruling R-3). The heuristic definitions are the AUDITOR's;
# names starting 'A:' are the batch author's heuristics as the auditor re-coded them, 'X:' are the auditor's own. Only this header was added.
# ruff: noqa
"""Auditor's shortcut heuristics for the 26 R2 batch-1 lineages. Every function takes the item's structured form (which
holds exactly what the question shows) and returns a guess string or None (not applicable to this shape). Names
starting with 'A:' re-implement the author's heuristics (from studies/m0/r2_shortcut_check.py, re-coded here, no import);
names starting with 'X:' are the auditor's own. Nothing here imports the generators."""
import bisect
import math
from collections import Counter


def L(xs):
    return ", ".join(str(x) for x in xs)


def yn(b):
    return "yes" if b else "no"


# ------------------------------------------------------------------ helpers (auditor's own code)
def lcs_greedy(a, b):
    j = n = 0
    for c in a:
        k = b.find(c, j)
        if k >= 0:
            n += 1
            j = k + 1
    return n


def longest_common_substring(a, b):
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def coin_greedy(coins, amt):
    n = 0
    for c in sorted(coins, reverse=True):
        n += amt // c
        amt %= c
    return None if amt else n


def lis_exact(xs):
    t = []
    for x in xs:
        i = bisect.bisect_left(t, x)
        t[i:i + 1] = [x]
    return len(t)


def cache_sim(seq, cap, pol):
    st = {}
    miss = 0
    for t, x in enumerate(seq):
        if x in st:
            if pol == "lru":
                st[x] = t
        else:
            miss += 1
            if len(st) == cap:
                del st[min(st, key=st.get)]
            st[x] = t
    return miss, set(st)


def bs_trace(xs, target, ceil_mid=False):
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi + (1 if ceil_mid else 0)) // 2
        seen.append(xs[mid - 1])
        if xs[mid - 1] == target:
            break
        if target < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return seen


def balanced_ignoring_kind(s):
    d = 0
    for ch in s:
        d += 1 if ch in "([{" else -1
        if d < 0:
            return False
    return d == 0


def eval_ltr(text):
    toks = text.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def seq():
        nonlocal pos
        v = atom()
        while pos < len(toks) and toks[pos] in "+-*":
            op = toks[pos]; pos += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    def atom():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == "(":
            v = seq(); pos += 1
            return v
        return int(t)

    return seq()


def eval_prec(text, plus_first=False):
    """Usual precedence; if plus_first, within the additive level all additions are done before subtractions
    (the 'operators of the same kind' misreading)."""
    toks = text.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def expr():
        nonlocal pos
        terms = [term()]
        ops = []
        while pos < len(toks) and toks[pos] in "+-":
            ops.append(toks[pos]); pos += 1
            terms.append(term())
        if not plus_first:
            v = terms[0]
            for o, t in zip(ops, terms[1:]):
                v = v + t if o == "+" else v - t
            return v
        # group: do every '+' first (merging neighbours), then the '-' from left to right
        vals = [terms[0]]
        rest_ops = []
        for o, t in zip(ops, terms[1:]):
            if o == "+":
                vals[-1] = vals[-1] + t
            else:
                rest_ops.append(o); vals.append(t)
        v = vals[0]
        for t in vals[1:]:
            v -= t
        return v

    def term():
        nonlocal pos
        v = atom()
        while pos < len(toks) and toks[pos] == "*":
            pos += 1
            v *= atom()
        return v

    def atom():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == "(":
            v = expr(); pos += 1
            return v
        return int(t)

    return expr()


def huffman(ws):
    import heapq
    h = list(ws); heapq.heapify(h); tot = 0
    while len(h) > 1:
        a = heapq.heappop(h); b = heapq.heappop(h); tot += a + b; heapq.heappush(h, a + b)
    return tot


def da(pp, rp, who_idx):
    """Proposer-optimal stable matching; pp[i] list of responder idx; rp[j] list of proposer idx."""
    n = len(pp)
    nxt = [0] * n
    held = {}
    free = list(range(n))
    while free:
        i = free.pop()
        j = pp[i][nxt[i]]; nxt[i] += 1
        if j not in held:
            held[j] = i
        elif rp[j].index(i) < rp[j].index(held[j]):
            free.append(held[j]); held[j] = i
        else:
            free.append(i)
    return {i: j for j, i in held.items()}


def ca_steps(row, table, steps, periodic=False):
    n = len(row)
    for _ in range(steps):
        if periodic:
            row = [table[f"{row[(i - 1) % n]}{row[i]}{row[(i + 1) % n]}"] for i in range(n)]
        else:
            p = [0] + row + [0]
            row = [table[f"{p[i - 1]}{p[i]}{p[i + 1]}"] for i in range(1, n + 1)]
    return row


def luhn_total(digits, double_odd_from_right=True, sub9=True):
    t = 0
    for i, d in enumerate(reversed(digits)):
        if (i % 2 == 1) == double_odd_from_right:
            d *= 2
            if sub9 and d > 9:
                d -= 9
        t += d
    return t


def factor(n):
    fs, d = [], 2
    while d * d <= n:
        while n % d == 0:
            fs.append(d); n //= d
        d += 1
    if n > 1:
        fs.append(n)
    return fs


# ------------------------------------------------------------------ heuristics per lineage
def _lcs(s):
    a, b = s["a"], s["b"]
    ca, cb = Counter(a), Counter(b)
    ov = sum(min(ca[c], cb[c]) for c in ca)
    return {
        "A:letter-multiset overlap": str(ov),
        "A:half the shorter string": str(min(len(a), len(b)) // 2),
        "X:greedy left-to-right matching": str(lcs_greedy(a, b)),
        "X:greedy matching, better of both directions": str(max(lcs_greedy(a, b), lcs_greedy(b, a))),
        "X:longest common substring": str(longest_common_substring(a, b)),
        "X:overlap minus 1": str(ov - 1),
        "X:overlap minus 2": str(ov - 2),
        "X:shorter length minus 3": str(min(len(a), len(b)) - 3),
    }


def _coin(s):
    c, a = s["coins"], s["amount"]
    g = coin_greedy(c, a)
    ce = -(-a // max(c))
    return {
        "A:largest coin first": "stuck" if g is None else str(g),
        "A:amount/largest rounded up": str(ce),
        "X:amount/largest rounded up + 1": str(ce + 1),
        "X:amount/largest rounded down": str(a // max(c)),
        "X:greedy minus 1": None if g is None else str(g - 1),
        "X:amount/second-largest rounded up": str(-(-a // sorted(c)[-2])),
        "X:amount/mean coin rounded": str(round(a / (sum(c) / len(c)))),
    }


def _lis(s):
    xs = s["xs"]; n = len(xs)
    run = best = 1
    for i in range(1, n):
        run = run + 1 if xs[i] > xs[i - 1] else 1
        best = max(best, run)
    asc = 1 + sum(1 for i in range(1, n) if xs[i] > xs[i - 1])
    g, last = 0, -10**9
    for x in xs:
        if x > last:
            g += 1; last = x
    rec = g  # left-to-right maxima count is the same greedy
    g2, last = 0, -10**9
    for x in xs:  # greedy that skips a number when the next is smaller than it
        if x > last:
            g2 += 1; last = x
    return {
        "A:longest run of ascents": str(best),
        "A:ascents + 1": str(asc),
        "X:greedy from the first number (records)": str(rec),
        "X:round(2*sqrt(n)) - 2": str(round(2 * math.sqrt(n)) - 2),
        "X:round(2*sqrt(n)) - 3": str(round(2 * math.sqrt(n)) - 3),
        "X:floor(sqrt(n)) + 1": str(math.isqrt(n) + 1),
        "X:LIS of the first half + 1": str(lis_exact(xs[: n // 2]) + 1),
    }


def _maxsub(s):
    xs = s["xs"]
    pref = [0]
    for x in xs:
        pref.append(pref[-1] + x)
    run = cur = 0
    best_run = 0
    for x in xs:
        cur = cur + x if x >= 0 else 0
        best_run = max(best_run, cur)
    two = sorted(xs)[-2:]
    return {
        "A:largest single number": str(max(xs)),
        "A:sum of positives": str(sum(x for x in xs if x > 0)),
        "A:total": str(sum(xs)),
        "X:best run of non-negative numbers": str(best_run),
        "X:largest prefix sum": str(max(pref[1:])),
        "X:largest suffix sum": str(max(pref[-1] - pref[i] for i in range(len(xs)))),
        "X:sum of the two largest": str(sum(two)),
    }


def _gcd(s):
    a, b, ask = s["a"], s["b"], s["ask"]
    if ask == "gcd":
        sm = 1
        for p in (2, 3, 5, 7):
            x, y = a, b
            while x % p == 0 and y % p == 0:
                sm *= p; x //= p; y //= p
        return {"A:a-b": str(a - b), "X:a mod b": str(a % b), "X:common small primes (2,3,5,7) product": str(sm),
                "X:smaller number": str(b), "X:b - (a mod b)": str(b - a % b)}
    if ask == "lcm":
        return {"A:a*b": str(a * b), "X:a*b/2": str(a * b // 2), "X:larger number": str(a),
                "X:a*b/(a mod b)": str(a * b // (a % b)) if a % b else None, "X:a*b/ smallest common prime": None}
    n = 0
    return {"A:3": "3", "X:2": "2", "X:4": "4", "X:digits of b": str(len(str(b))), "X:floor(log2 b)": str(int(math.log2(b)))}


def _modpow(s):
    a, e, m = s["a"], s["e"], s["m"]
    return {
        "A:a": str(a),
        "A:a^(e mod 5) mod m": str(pow(a, e % 5, m)),
        "A:e mod m": str(e % m),
        "X:a*e mod m": str(a * e % m),
        "X:a^2 mod m": str(a * a % m),
        "X:a^(e mod (m-1)) mod m (Fermat, valid only for prime m)": str(pow(a, e % (m - 1), m)),
        "X:m - a": str(m - a),
    }


def _crt(s):
    cons = s["congruences"]
    r0, m0 = cons[0]
    rmax, mmax = max(cons, key=lambda c: c[1])
    prod = math.prod(m for _, m in cons)
    return {
        "A:first remainder": str(r0),
        "A:sum of remainders": str(sum(c[0] for c in cons)),
        "A:largest remainder": str(max(c[0] for c in cons)),
        "X:first remainder + first divisor": str(r0 + m0),
        "X:remainder of the largest divisor": str(rmax),
        "X:product of divisors minus 1": str(prod - 1),
        "X:product of remainders": str(math.prod(c[0] for c in cons)),
    }


def _prime(s):
    n, ask = s["n"], s["ask"]
    small = [p for p in (2, 3, 5, 7, 11, 13) if n % p == 0]
    out = {}
    if ask == "largest":
        out["A:largest small prime dividing n"] = str(max(small)) if small else None
        out["X:smallest prime factor"] = str(factor(n)[0])
        out["X:n mod 100"] = str(n % 100)
        out["X:last two digits if prime"] = None
        out["X:isqrt(n)"] = str(math.isqrt(n))
    else:
        out["A:sum of small primes dividing n"] = str(sum(small)) if small else None
        out["X:digit sum of n"] = str(sum(map(int, str(n))))
        out["X:sum of distinct prime factors"] = str(sum(set(factor(n))))
        out["X:largest prime factor * 2"] = str(2 * max(factor(n)))
        out["X:n mod 100"] = str(n % 100)
    return out


def _sub(s):
    n, mv = s["n"], s["moves"]
    return {
        "A:n mod (largest+1) != 0": yn(n % (max(mv) + 1) != 0),
        "A:n mod (smallest+largest) != 0": yn(n % (min(mv) + max(mv)) != 0),
        "A:n odd": yn(n % 2 == 1),
        "X:n mod (smallest+1) != 0": yn(n % (min(mv) + 1) != 0),
        "X:n mod (sum of moves) != 0": yn(n % sum(mv) != 0),
        "X:1 is a move": yn(1 in mv),
        "X:number of moves is odd": yn(len(mv) % 2 == 1),
        "X:n mod (largest+1) >= smallest": yn(n % (max(mv) + 1) >= min(mv)),
        "X:gcd(moves) divides n": yn(n % math.gcd(*mv) == 0),
    }


def _bs(s):
    xs, t, ask = s["xs"], s["target"], s["ask"]
    tr = bs_trace(xs, t)
    trc = bs_trace(xs, t, ceil_mid=True)
    if ask == "values":
        return {"X:ceil-midpoint trace": L(trc), "X:trace with 0-based floor midpoint": L(_bs0(xs, t)),
                "X:trace that does not stop at the target": L(_bs_nostop(xs, t)),
                "X:first three of the true trace only": L(tr[:3]), "X:true trace minus last": L(tr[:-1])}
    pos = bisect.bisect_left(xs, t)
    near = [xs[i] for i in (pos - 1, pos) if 0 <= i < len(xs) and xs[i] != t]
    return {"A:the target": str(t), "X:ceil-midpoint third probe": str(trc[2]) if len(trc) > 2 else None,
            "X:nearest list value below the target": str(xs[pos - 1]) if pos > 0 else None,
            "X:nearest list value at/above the target": str(xs[pos]) if pos < len(xs) else None,
            "X:value at position n/8 or 7n/8 nearer the target": str(xs[len(xs) // 8] if t < xs[len(xs) // 2] else xs[(7 * len(xs)) // 8]),
            "X:0-based floor third probe": str(_bs0(xs, t)[2]) if len(_bs0(xs, t)) > 2 else None}


def _bs0(xs, t):
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
    return seen


def _bs_nostop(xs, t):
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi) // 2
        seen.append(xs[mid - 1])
        if t < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return seen


def _lps(s):
    t = s["s"]
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    odd = ev = 0
    for c in range(len(t)):
        lo = hi = c
        while lo >= 0 and hi < len(t) and t[lo] == t[hi]:
            lo -= 1; hi += 1
        odd = max(odd, hi - lo - 1)
        lo, hi = c, c + 1
        while lo >= 0 and hi < len(t) and t[lo] == t[hi]:
            lo -= 1; hi += 1
        ev = max(ev, hi - lo - 1)
    return {"A:longest run of one letter": str(best), "A:3": "3", "X:longest odd-length palindrome only": str(odd),
            "X:longest even-length palindrome only": str(ev), "X:longest run + 2": str(best + 2),
            "X:5": "5", "X:longest palindrome capped at 7": str(min(7, max(odd, ev)))}


def _dict(s):
    letters, ask = s["letters"], s["ask"]
    n = len(letters)
    if ask == "word":
        k = s["k"]
        # off-by-one: unrank with k instead of k-1
        def unrank0(k0):
            pool = sorted(letters); out = []
            k0 %= math.factorial(n)
            for i in range(n, 0, -1):
                f = math.factorial(i - 1); out.append(pool.pop(k0 // f)); k0 %= f
            return "".join(out)
        return {"A:sorted letters": "".join(letters), "A:reverse letters": "".join(reversed(letters)),
                "X:unrank with k (off by one, 0-based)": unrank0(k), "X:unrank with k-2": unrank0(k - 2),
                "X:first letter right, rest sorted": letters[(k - 1) // math.factorial(n - 1)] + "".join(x for x in letters if x != letters[(k - 1) // math.factorial(n - 1)])}
    w = s["word"]
    pool = sorted(letters)
    r0 = 0
    for i, ch in enumerate(w):
        j = pool.index(ch); r0 += j * math.factorial(n - 1 - i); pool.pop(j)
    naive2 = letters.index(w[0]) * math.factorial(n - 1) + 1
    # rank using original-alphabet index instead of remaining-letter index (Lehmer-code error)
    r_bad = sum(letters.index(ch) * math.factorial(n - 1 - i) for i, ch in enumerate(w)) + 1
    return {"A:first-letter block start": str(naive2), "X:rank 0-based (off by one)": str(r0),
            "X:rank + 1 (off by one up)": str(r0 + 2), "X:rank using alphabet index, not remaining index": str(r_bad),
            "X:first two letters only": str(letters.index(w[0]) * math.factorial(n - 1) + sorted(x for x in letters if x != w[0]).index(w[1]) * math.factorial(n - 2) + 1)}


def _bst(s):
    xs, kind = s["xs"], s["kind"]
    return {"A:insertion order": L(xs), "A:sorted": L(sorted(xs)), "A:sorted descending": L(sorted(xs, reverse=True)),
            "X:reversed insertion order": L(xs[::-1]), "X:root then sorted rest": L([xs[0]] + sorted(xs[1:])),
            "X:root, smaller in insertion order, larger in insertion order": L([xs[0]] + [x for x in xs[1:] if x < xs[0]] + [x for x in xs[1:] if x > xs[0]]),
            "X:other traversal (pre<->level)": None}


def _heap(s):
    import heapq
    xs, rem = s["xs"], s["removals"]
    h = []
    for x in xs:
        heapq.heappush(h, x)
    for _ in range(rem):
        heapq.heappop(h)
    h2 = list(xs)
    heapq.heapify(h2)
    for _ in range(rem):
        heapq.heappop(h2)
    mf = list(xs)
    i = mf.index(min(mf)); mf[0], mf[i] = mf[i], mf[0]
    return {"A:insertion order": L(xs), "A:sorted": L(sorted(xs)), "A:sorted minus removals": L(sorted(xs)[rem:]),
            "X:Python heapq push/pop (sift-to-leaf pop)": L(h), "X:heapify of the whole row then pops": L(h2),
            "X:minimum swapped to the front": L(mf) if rem == 0 else None,
            "X:insertion order minus removed minima": L([x for x in xs if x not in sorted(xs)[:rem]])}


def _cache(s):
    seq, cap, pol, ask = s["seq"], s["cap"], s["policy"], s["ask"]
    other = "fifo" if pol == "lru" else "lru"
    if ask == "misses":
        dist = len(set(seq))
        changes = 1 + sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
        return {"A:other policy": str(cache_sim(seq, cap, other)[0]), "A:number of distinct items": str(dist),
                "X:requests not equal to the previous request": str(changes),
                "X:requests not among the previous cap requests": str(sum(1 for i, x in enumerate(seq) if x not in seq[max(0, i - cap):i])),
                "X:distinct + (len-distinct)//2": str(dist + (len(seq) - dist) // 2),
                "X:cap+1 policy": str(cache_sim(seq, cap + 1, pol)[0]), "X:cap-1 policy": str(cache_sim(seq, max(1, cap - 1), pol)[0])}
    x = s["item"]
    last_distinct = []
    for y in reversed(seq):
        if y not in last_distinct:
            last_distinct.append(y)
    return {"A:item among the last cap requests": yn(x in seq[-cap:]),
            "X:item requested at all": yn(x in seq),
            "X:item among the last cap distinct items (=LRU answer)": yn(x in last_distinct[:cap]),
            "X:other policy": yn(x in cache_sim(seq, cap, other)[1]),
            "X:item requested in the second half": yn(x in seq[len(seq) // 2:]),
            "X:item is the last request": yn(x == seq[-1]),
            "X:item requested at least 3 times": yn(seq.count(x) >= 3),
            "X:item among the first cap distinct items": yn(x in list(dict.fromkeys(seq))[:cap])}


def _hash(s):
    m, keys, ask, t = s["m"], s["keys"], s["ask"], s["target"]
    if ask == "slot":
        same = sum(1 for k in keys[: keys.index(t)] if k % m == t % m)
        return {"A:home slot": str(t % m), "X:home slot + 1": str((t % m + 1) % m),
                "X:home + earlier keys with the same home": str((t % m + same) % m),
                "X:insertion index": str(keys.index(t)), "X:last digit of the key": str(t % 10),
                "X:first free slot after all keys": None}
    last = keys[-1]
    same = sum(1 for k in keys[:-1] if k % m == last % m)
    return {"A:one slot": "1", "X:2": "2", "X:earlier keys with the same home + 1": str(same + 1),
            "X:number of keys": str(len(keys)), "X:keys before it": str(len(keys) - 1)}


def _br(s):
    t, ask = s["s"], s["ask"]
    if ask == "valid":
        adj_bad = any(t[i] in "([{" and t[i + 1] in ")]}" and {"(": ")", "[": "]", "{": "}"}[t[i]] != t[i + 1] for i in range(len(t) - 1))
        return {"A:equal counts of each kind": yn(all(t.count(o) == t.count(c) for o, c in ("()", "[]", "{}"))),
                "A:starts with opener, ends with closer": yn(t[0] in "([{" and t[-1] in ")]}"),
                "X:depth never negative (kinds ignored)": yn(balanced_ignoring_kind(t)),
                "X:no adjacent wrong-kind pair": yn(not adj_bad),
                "X:only one kind of bracket": yn(len({c for c in t if c in "([{"}) == 1),
                "X:first and last are a matching pair": yn({"(": ")", "[": "]", "{": "}"}.get(t[0]) == t[-1]),
                "X:no ')(' style closer-then-opener at the middle": yn(t[len(t) // 2 - 1] in "([{")}
    p = s["p"] - 1
    want = {"(": ")", "[": "]", "{": "}"}[t[p]]
    nxt = t.find(want, p + 1)
    lastk = t.rfind(want)
    return {"A:next closer of the same kind": str(nxt + 1) if nxt >= 0 else None,
            "A:mirror position": str(len(t) - p),
            "X:immediately next position": str(p + 2),
            "X:last closer of the same kind": str(lastk + 1),
            "X:next closer of any kind": str(next(i for i in range(p + 1, len(t)) if t[i] in ")]}") + 1),
            "X:second closer of the same kind": (str(t.find(want, nxt + 1) + 1) if nxt >= 0 and t.find(want, nxt + 1) >= 0 else None)}


def _expr(s):
    text, conv = s["text"], s["convention"]
    flat = text.replace("(", "").replace(")", "")
    nums = [int(x) for x in flat.replace("+", " ").replace("-", " ").replace("*", " ").split()]
    out = {"A:the other convention": str(eval_prec(text) if conv != "ranked" else eval_ltr(text)),
           "A:parentheses ignored, ranked": str(eval_prec(flat)),
           "X:parentheses ignored, left to right": str(eval_ltr(flat)),
           "X:sum of all numbers": str(sum(nums)),
           "X:ranked with additions before subtractions ('same kind' misreading)": str(eval_prec(text, plus_first=True)) if conv == "ranked" else None,
           "X:largest number": str(max(nums))}
    return out


def _interval(s):
    iv = s["meetings"]
    def greedy(key, touch_ok=True):
        n, last = 0, -10**9
        taken = []
        for a, b in sorted(iv, key=key):
            if all((b <= c or a >= d) if touch_ok else (b < c or a > d) for c, d in taken):
                taken.append((a, b)); n += 1
        return n
    n_end_strict = 0; last = -10**9
    for a, b in sorted(iv, key=lambda x: (x[1], x[0])):
        if a > last:
            n_end_strict += 1; last = b
    return {"A:earliest start first": str(greedy(lambda x: (x[0], x[1]))),
            "A:shortest first": str(greedy(lambda x: (x[1] - x[0], x[0]))),
            "X:earliest end, touching counts as a clash": str(n_end_strict),
            "X:fewest clashes first": str(greedy(lambda x: (sum(1 for c, d in iv if not (x[1] <= c or x[0] >= d)), x[1]))),
            "X:meetings in written order, keep if no clash": str(greedy(lambda x: 0)),
            "X:half the meetings": str(len(iv) // 2),
            "X:span / mean length": str(round((max(b for _, b in iv) - min(a for a, _ in iv)) / (sum(b - a for a, b in iv) / len(iv))))}


def _merge(s):
    ws = s["ws"]
    def chain(order):
        acc, tot = order[0], 0
        for w in order[1:]:
            acc += w; tot += acc
        return tot
    srt = sorted(ws)
    return {"A:join in written order": str(chain(ws)), "A:sum of sizes": str(sum(ws)),
            "X:join in ascending order (chain)": str(chain(srt)), "X:join in descending order (chain)": str(chain(srt[::-1])),
            "X:sum * ceil(log2 n)": str(sum(ws) * math.ceil(math.log2(len(ws)))),
            "X:adjacent-only merging optimum": str(_adjacent_opt(ws)),
            "X:sum * (n-1)/2 rounded": str(round(sum(ws) * (len(ws) - 1) / 2))}


def _adjacent_opt(ws):
    n = len(ws)
    pre = [0]
    for w in ws:
        pre.append(pre[-1] + w)
    dp = [[0] * n for _ in range(n)]
    for ln in range(2, n + 1):
        for i in range(n - ln + 1):
            j = i + ln - 1
            dp[i][j] = min(dp[i][k] + dp[k + 1][j] for k in range(i, j)) + pre[j + 1] - pre[i]
    return dp[0][n - 1]


def _net(s):
    towns, cables = s["towns"], s["cables"]
    n = len(towns)
    w = sorted(c[2] for c in cables)
    best = {}
    for a, b, x in cables:
        for t in (a, b):
            best[t] = min(best.get(t, 10**9), x)
    # nearest-neighbour path from the first listed (sorted) town
    adj = {}
    for a, b, x in cables:
        adj.setdefault(a, []).append((x, b)); adj.setdefault(b, []).append((x, a))
    start = sorted(towns)[0]
    seen = {start}; cur = start; tot = 0; ok = True
    while len(seen) < n:
        cand = sorted((x, b) for x, b in adj[cur] if b not in seen)
        if not cand:
            ok = False; break
        x, b = cand[0]; tot += x; seen.add(b); cur = b
    return {"A:n-1 cheapest cables": str(sum(w[: n - 1])), "A:cheapest cable at each town": str(sum(best.values())),
            "X:all cables minus the dearest": str(sum(w) - w[-1]),
            "X:nearest-neighbour walk": str(tot) if ok else None,
            "X:n-1 cheapest + 1 step": str(sum(w[: n - 1]) + (w[n - 1] - w[n - 2] if len(w) >= n else 0)),
            "X:cheapest per town minus cheapest cable": str(sum(best.values()) - w[0]),
            "X:n * median cable": str((n - 1) * w[len(w) // 2])}


def _da(s):
    P, R = s["proposers"], s["responders"]
    pp = [[R.index(r) for r in s["prefs_p"][p]] for p in P]
    rp = [[P.index(p) for p in s["prefs_r"][r]] for r in R]
    who = P.index(s["who"])
    resp_opt = da(rp, pp, None)  # responders propose: returns responder->proposer
    partner_resp_side = {p: r for r, p in resp_opt.items()}[who]
    mutual = [r for r in range(len(R)) if pp[who][0] == r and rp[r][0] == who]
    return {"A:own first choice": R[pp[who][0]],
            "A:responder ranking them highest": min(R, key=lambda j: (s["prefs_r"][j].index(s["who"]), j)),
            "X:responder-proposing stable partner": R[partner_resp_side],
            "X:own last choice": R[pp[who][-1]],
            "X:own second choice": R[pp[who][1]],
            "X:same position in the other list": R[who] if who < len(R) else None,
            "X:best of own list among those ranking them in their top half": next((R[j] for j in pp[who] if rp[j].index(who) < (len(P) + 1) // 2), None)}


def _ca(s):
    row, table, steps, ask = s["row"], s["table"], s["steps"], s["ask"]
    per = ca_steps(row, table, steps, periodic=True)
    one = ca_steps(row, table, 1)
    more = ca_steps(row, table, steps + 1)
    less = ca_steps(row, table, steps - 1) if steps > 1 else row
    f = (lambda r: "".join(map(str, r))) if ask == "row" else (lambda r: str(sum(r)))
    out = {"A:the start": f(row), "A:one step only": f(one) if steps > 1 else None,
           "X:periodic boundary": f(per), "X:one step too many": f(more), "X:one step too few": f(less),
           "X:table read in the other neighbour order": f(ca_steps(row, {k[::-1]: v for k, v in table.items()}, steps))}
    if ask == "count":
        out["X:half the cells"] = str(len(row) // 2)
    return out


def _chip(s):
    row, ask = s["row"], s["ask"]
    n = len(row)
    tot = sum(row)
    if ask == "final":
        w = sum((i + 1) * c for i, c in enumerate(row))
        z = (n * (n + 1) // 2 - w) % (n + 1)
        pat = [1] * n
        if 1 <= z <= n:
            pat[z - 1] = 0
        return {"A:the start": L(row), "A:start mod 2": L([x % 2 for x in row]), "X:all ones": L([1] * n),
                "X:invariant formula: ones with a 0 at (n(n+1)/2 - sum i*c_i) mod (n+1)": L(pat),
                "X:all ones with a 0 in the middle": L([1] * (n // 2) + [0] + [1] * (n - n // 2 - 1)),
                "X:min(c,1) per cell": L([min(x, 1) for x in row])}
    if ask == "topplings":
        return {"A:half the chips": str(tot // 2), "X:total chips": str(tot), "X:total chips * n / 4": str(tot * n // 4),
                "X:sum of max(c-1,0)": str(sum(max(c - 1, 0) for c in row)), "X:excess over one per cell * n/2": str(max(0, tot - n) * n // 2)}
    return {"X:chips minus n": str(tot - n), "X:chips minus (n-1)": str(tot - n + 1), "X:excess over 1 per cell": str(sum(max(c - 1, 0) for c in row)),
            "X:half the chips": str(tot // 2), "X:chips minus n, +1 if chips >= n": str(tot - n + (1 if tot >= n else 0))}


def _luhn(s):
    d, ask = s["digits"], s["ask"]
    if ask == "valid":
        return {"A:plain digit sum is a multiple of 10": yn(sum(d) % 10 == 0),
                "X:last digit even": yn(d[-1] % 2 == 0),
                "X:Luhn doubling from the wrong end": yn(luhn_total(d, double_odd_from_right=False) % 10 == 0),
                "X:Luhn without subtracting 9": yn(luhn_total(d, sub9=False) % 10 == 0),
                "X:Luhn total ends in 0 or 5": yn(luhn_total(d) % 5 == 0),
                "X:always yes": "yes"}
    return {"A:plain digit-sum check digit": str(-sum(d) % 10),
            "X:check digit with doubling parity wrong": str(-luhn_total(d + [0], double_odd_from_right=False) % 10),
            "X:check digit without subtracting 9": str(-luhn_total(d + [0], sub9=False) % 10),
            "X:last payload digit": str(d[-1]),
            "X:Luhn total of the payload mod 10": str(luhn_total(d) % 10)}


def _ham(s):
    bits, n = s["bits"], s["n"]
    p, low = 1, "0"
    fails = []
    while p <= n:
        if sum(b for i, b in enumerate(bits, 1) if i & p) % 2:
            fails.append(p)
        p *= 2
    syn0 = 0
    for i, b in enumerate(bits):
        if b:
            syn0 ^= i
    return {"A:lowest failing check": str(fails[0]) if fails else "0",
            "A:first 1": str(next((i for i, b in enumerate(bits, 1) if b), 0)),
            "X:highest failing check": str(fails[-1]) if fails else "0",
            "X:syndrome with 0-based positions": str(syn0),
            "X:number of failing checks": str(len(fails)),
            "X:last 1": str(max((i for i, b in enumerate(bits, 1) if b), default=0)),
            "X:count of ones": str(sum(bits))}


H = {
    "R2.lcs_length": _lcs, "R2.coin_change_min": _coin, "R2.lis_length": _lis, "R2.max_subarray_sum": _maxsub,
    "R2.gcd_euclid": _gcd, "R2.modular_power": _modpow, "R2.crt_smallest": _crt, "R2.prime_factor_query": _prime,
    "R2.subtraction_game": _sub, "R2.binary_search_trace": _bs, "R2.longest_palindromic_substring": _lps,
    "R2.dictionary_rank": _dict, "R2.bst_traversal": _bst, "R2.min_heap_ops": _heap, "R2.cache_eviction": _cache,
    "R2.hash_probe": _hash, "R2.bracket_match": _br, "R2.expression_eval": _expr, "R2.interval_scheduling": _interval,
    "R2.merge_smallest_cost": _merge, "R2.cheapest_network": _net, "R2.deferred_acceptance_partner": _da,
    "R2.cellular_automaton": _ca, "R2.chip_toppling": _chip, "R2.luhn_check": _luhn, "R2.hamming_error_position": _ham,
}
SHAPE_KEYS = ("ask", "kind", "convention", "policy")
