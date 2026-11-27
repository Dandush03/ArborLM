# ruff: noqa
"""Audit 3 (R2): cheap-rule heuristics per lineage. Each returns an answer string or None (not applicable). Stdlib only; imports nothing from studies.m0.
A heuristic marked (P) is a valid alternative PROCEDURE or a full computation under a misreading, reported but not called a cheap cue."""
import itertools
import math
import re
from functools import lru_cache

import a3_solvers as S

L = S.L
H = {}


def h(lineage, name):
    def deco(fn):
        H.setdefault(lineage, []).append((name, fn))
        return fn
    return deco


def num(x):
    return None if x is None else str(x)


# ---------------- core ----------------
@h("count_letter", "number of words")
def _(s, q): return str(len(s["words"]))
@h("count_letter", "words containing the letter")
def _(s, q): return str(sum(1 for w in s["words"] if s["letter"] in w))


@h("count_divisible", "ignore 'greater than t'")
def _(s, q): return str(sum(1 for x in s["xs"] if x % s["m"] == 0))
@h("count_divisible", "ignore divisibility")
def _(s, q): return str(sum(1 for x in s["xs"] if x > s["t"]))
@h("count_divisible", "constant 0")
def _(s, q): return "0"
@h("count_divisible", ">= t instead of > t")
def _(s, q): return str(sum(1 for x in s["xs"] if x % s["m"] == 0 and x >= s["t"]))


@h("sort_list", "opposite direction")
def _(s, q): return L(sorted(s["xs"], reverse=not s["desc"]))


@h("kth_smallest", "k-th as written")
def _(s, q): return str(s["xs"][s["k"] - 1])
@h("kth_smallest", "k-th largest")
def _(s, q): return str(sorted(s["xs"], reverse=True)[s["k"] - 1])
@h("kth_smallest", "off by one (k+1)-th smallest")
def _(s, q): return str(sorted(s["xs"])[s["k"]]) if s["k"] < len(s["xs"]) else None


@h("list_ops", "ignore reverses")
def _(s, q):
    return S.list_ops({"xs": s["xs"], "ops": [o for o in s["ops"] if o[0] != "reverse"]}, q)
@h("list_ops", "ignore moves to the end")
def _(s, q):
    return S.list_ops({"xs": s["xs"], "ops": [o for o in s["ops"] if o[0] != "first_to_end"]}, q)


@h("to_base_wide", "digits reversed (least significant first)")
def _(s, q): return S.to_base(s, q)[::-1]


@h("from_base", "digits read right to left")
def _(s, q): return S.from_base({"digits": s["digits"][::-1], "base": s["base"]}, q)


@h("string_rewrite_nonidentity", "only the last rule, on the start string")
def _(s, q): return S.string_rewrite({"s": s["s"], "rules": s["rules"][-1:]}, q)
@h("string_rewrite_nonidentity", "only the first rule")
def _(s, q): return S.string_rewrite({"s": s["s"], "rules": s["rules"][:1]}, q)
@h("string_rewrite_nonidentity", "rules in reverse order")
def _(s, q): return S.string_rewrite({"s": s["s"], "rules": s["rules"][::-1]}, q)
@h("string_rewrite_nonidentity", "first occurrence only per rule")
def _(s, q):
    cur = s["s"]
    for p, t in s["rules"]:
        cur = cur.replace(p, t, 1)
    return cur
@h("string_rewrite_nonidentity", "(P) all rules applied simultaneously to the start string, leftmost match")
def _(s, q):
    cur, out, i = s["s"], [], 0
    while i < len(cur):
        for p, t in s["rules"]:
            if cur.startswith(p, i):
                out.append(t); i += len(p); break
        else:
            out.append(cur[i]); i += 1
    return "".join(out)


@h("caesar_shift", "shift backwards")
def _(s, q): return S.caesar_shift({"text": s["text"], "k": -s["k"]}, q)


@h("palindrome_check", "first letter equals last letter")
def _(s, q):
    t = s["phrase"].replace(" ", "")
    return "yes" if t[0] == t[-1] else "no"
@h("palindrome_check", "letter counts: at most one odd count")
def _(s, q):
    t = s["phrase"].replace(" ", "")
    odd = sum(1 for c in set(t) if t.count(c) % 2)
    return "yes" if odd <= 1 else "no"
@h("palindrome_check", "outer two letters each side match")
def _(s, q):
    t = s["phrase"].replace(" ", "")
    return "yes" if t[:2] == t[::-1][:2] else "no"
@h("palindrome_check", "the words read as mirror images (first word = reverse of last word)")
def _(s, q):
    w = s["phrase"].split(" ")
    return "yes" if w[0] == w[-1][::-1] else "no"


@h("grid_sum", "row i read as column i (or the reverse)")
def _(s, q):
    g, what = s["grid"], s["what"]
    m = re.match(r"(row|column) (\d+)$", what)
    if not m:
        return None
    i = int(m.group(2)) - 1
    if m.group(1) == "row":
        return str(sum(r[i] for r in g)) if i < len(g[0]) else None
    return str(sum(g[i])) if i < len(g) else None


@h("permutation_power", "the start")
def _(s, q): return str(s["s"])
@h("permutation_power", "one application")
def _(s, q): return str(s["img"][s["s"] - 1])
@h("permutation_power", "t mod n applications")
def _(s, q):
    x = s["s"]
    for _ in range(s["t"] % len(s["img"])):
        x = s["img"][x - 1]
    return str(x)
@h("permutation_power", "t applied to the start as a number: ((s-1+t) mod n)+1")
def _(s, q): return str((s["s"] - 1 + s["t"]) % len(s["img"]) + 1)


@h("stack_machine", "last pushed value")
def _(s, q):
    v = [p[1] for p in s["prog"] if p[0] == "push"]
    return str(v[-1]) if v else None
@h("stack_machine", "last step is push -> its value; else None")
def _(s, q):
    p = s["prog"][-1]
    return str(p[1]) if p[0] == "push" else None
@h("stack_machine", "sum of pushed values")
def _(s, q): return str(sum(p[1] for p in s["prog"] if p[0] == "push"))


@h("multiples_between", "(b-a)//m")
def _(s, q): return str((s["b"] - s["a"]) // s["m"])
@h("multiples_between", "(b-a)//m + 1")
def _(s, q): return str((s["b"] - s["a"]) // s["m"] + 1)
@h("multiples_between", "round((b-a+1)/m)")
def _(s, q): return str(round((s["b"] - s["a"] + 1) / s["m"]))
@h("multiples_between", "b//m - a//m")
def _(s, q): return str(s["b"] // s["m"] - s["a"] // s["m"])


@h("digit_root", "(P) n mod 9 with 0 -> 9 (casting out nines)")
def _(s, q): return str(1 + (s["n"] - 1) % 9)
@h("digit_root", "last digit")
def _(s, q): return str(s["n"] % 10)
@h("digit_root", "one digit sum, last digit of it")
def _(s, q): return str(sum(map(int, str(s["n"]))) % 10)


# ---------------- batch 1 unchanged ----------------
def _probes(xs, t):
    return [int(x) for x in S.binary_search_trace({"xs": xs, "target": t, "ask": "values"}, "").split(", ")]


@h("binary_search_trace", "third = the target")
def _(s, q): return str(s["target"]) if s["ask"] == "third" else None
@h("binary_search_trace", "third = list value nearest the target (ties low)")
def _(s, q):
    if s["ask"] != "third":
        return None
    return str(min(s["xs"], key=lambda x: (abs(x - s["target"]), x)))
@h("binary_search_trace", "third = value at the 1/8 or 7/8 position on the target's side")
def _(s, q):
    if s["ask"] != "third":
        return None
    xs, n = s["xs"], len(s["xs"])
    mid = xs[(1 + n) // 2 - 1]
    pos = (n + 1) // 8 if s["target"] < mid else (7 * n) // 8
    return str(xs[max(0, min(n - 1, pos - 1))])
@h("binary_search_trace", "values: midpoint rounded UP")
def _(s, q):
    if s["ask"] != "values":
        return None
    xs, t = s["xs"], s["target"]
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi + 1) // 2
        seen.append(xs[mid - 1])
        if xs[mid - 1] == t:
            break
        if t < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return L(seen)
@h("binary_search_trace", "third: midpoint rounded UP")
def _(s, q):
    if s["ask"] != "third":
        return None
    xs, t = s["xs"], s["target"]
    lo, hi, seen = 1, len(xs), []
    while lo <= hi:
        mid = (lo + hi + 1) // 2
        seen.append(xs[mid - 1])
        if xs[mid - 1] == t:
            break
        if t < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return str(seen[2]) if len(seen) > 2 else None


@h("bst_traversal", "insertion order")
def _(s, q): return L(s["xs"])
@h("bst_traversal", "sorted")
def _(s, q): return L(sorted(s["xs"]))
@h("bst_traversal", "reverse insertion order")
def _(s, q): return L(s["xs"][::-1])
@h("bst_traversal", "root, then the rest sorted")
def _(s, q): return L([s["xs"][0], *sorted(s["xs"][1:])])
@h("bst_traversal", "post: sorted then root last")
def _(s, q): return L([*sorted(s["xs"][1:]), s["xs"][0]]) if s["kind"] == "post" else None
@h("bst_traversal", "(P) other walk kind (pre<->level)")
def _(s, q):
    k = {"pre": "level", "level": "pre", "post": None}[s["kind"]]
    return None if k is None else S.bst_traversal({"xs": s["xs"], "kind": k}, q)


@h("min_heap_ops", "(P) Floyd heapify of the whole row, then removals")
def _(s, q):
    hp = list(s["xs"])
    import heapq
    heapq.heapify(hp)
    for _ in range(s["removals"]):
        heapq.heappop(hp)
    return L(hp)
@h("min_heap_ops", "sorted remainder")
def _(s, q): return L(sorted(s["xs"])[s["removals"]:])
@h("min_heap_ops", "insertion order with the minimum swapped to the front")
def _(s, q):
    if s["removals"]:
        return None
    xs = list(s["xs"]); i = xs.index(min(xs)); xs[0], xs[i] = xs[i], xs[0]
    return L(xs)
@h("min_heap_ops", "removal by deleting the minimum and keeping the order of the rest")
def _(s, q):
    hp = [int(x) for x in S.min_heap_ops({"xs": s["xs"], "removals": 0}, q).split(", ")]
    for _ in range(s["removals"]):
        hp.remove(min(hp))
    return L(hp)


@h("cellular_automaton", "one step only")
def _(s, q): return S.cellular_automaton({**s, "steps": 1}, q) if s["steps"] > 1 else None
@h("cellular_automaton", "(P) periodic boundary")
def _(s, q):
    row = list(s["row"])
    for _ in range(s["steps"]):
        n = len(row)
        row = [s["table"][f"{row[i - 1]}{row[i]}{row[(i + 1) % n]}"] for i in range(n)]
    return "".join(map(str, row)) if s["ask"] == "row" else str(sum(row))
@h("cellular_automaton", "count: ones in the start row")
def _(s, q): return str(sum(s["row"])) if s["ask"] == "count" else None
@h("cellular_automaton", "row: neighbour order reversed (right,cell,left)")
def _(s, q):
    t = {k[::-1]: v for k, v in s["table"].items()}
    return S.cellular_automaton({**s, "table": t}, q)


@h("dictionary_rank", "position: index in the FULL sorted list (no removal)")
def _(s, q):
    if s["ask"] != "position":
        return None
    w, pool, n = s["word"], sorted(s["letters"]), len(s["letters"])
    return str(1 + sum(pool.index(c) * math.factorial(n - 1 - i) for i, c in enumerate(w)))
@h("dictionary_rank", "position: off by one (0-based)")
def _(s, q):
    if s["ask"] != "position":
        return None
    return str(int(S.dictionary_rank(s, q)) - 1)
@h("dictionary_rank", "word: number k-1 read 0-based (off by one)")
def _(s, q):
    if s["ask"] != "word":
        return None
    return S.dictionary_rank({**s, "k": s["k"] + 1}, q) if s["k"] + 1 <= math.factorial(len(s["letters"])) else None


@h("hamming_error_position", "constant 0")
def _(s, q): return "0"
@h("hamming_error_position", "first failing check position only")
def _(s, q):
    bits = s["bits"]; n = len(bits); p = 1
    while p <= n:
        if sum(bits[i - 1] for i in range(1, n + 1) if i & p) % 2:
            return str(p)
        p *= 2
    return "0"
@h("hamming_error_position", "syndrome read with the bits reversed")
def _(s, q): return S.hamming_error_position({"bits": s["bits"][::-1], "n": s["n"]}, q)


@h("luhn_check", "plain digit sum (no doubling)")
def _(s, q):
    ds = s["digits"]
    if s["ask"] == "valid":
        return "yes" if sum(ds) % 10 == 0 else "no"
    return str((-sum(ds)) % 10)
@h("luhn_check", "doubling the other parity")
def _(s, q):
    ds = s["digits"]
    def tot(d):
        return sum(sum(divmod(2 * x, 10)) if i % 2 == 0 else x for i, x in enumerate(d[::-1]))
    if s["ask"] == "valid":
        return "yes" if tot(ds) % 10 == 0 else "no"
    for c in range(10):
        if tot([*ds, c]) % 10 == 0:
            return str(c)
@h("luhn_check", "check digit: payload total without the new digit, (10 - t mod 10) mod 10, payload's last digit NOT doubled")
def _(s, q):
    if s["ask"] != "check_digit":
        return None
    return str((-S._luhn(s["digits"])) % 10)
@h("luhn_check", "valid: last digit even")
def _(s, q): return ("yes" if s["digits"][-1] % 2 == 0 else "no") if s["ask"] == "valid" else None


def _iv_greedy(iv, key):
    n, last = 0, -10**9
    for a, b in sorted(iv, key=key):
        if a >= last:
            n += 1
            last = b
    return n


@h("interval_scheduling", "earliest start first")
def _(s, q): return str(_iv_greedy(s["meetings"], lambda x: (x[0], x[1])))
@h("interval_scheduling", "shortest first")
def _(s, q):
    taken = []
    for a, b in sorted(s["meetings"], key=lambda x: (x[1] - x[0], x[0])):
        if all(b <= c or a >= d for c, d in taken):
            taken.append((a, b))
    return str(len(taken))
@h("interval_scheduling", "earliest-finish greedy with touching = clash")
def _(s, q):
    n, last = 0, -10**9
    for a, b in sorted(s["meetings"], key=lambda x: (x[1], x[0])):
        if a > last:
            n += 1
            last = b
    return str(n)
@h("interval_scheduling", "horizon / mean length (rounded)")
def _(s, q):
    iv = s["meetings"]
    span = max(b for _, b in iv) - min(a for a, _ in iv)
    return str(round(span / (sum(b - a for a, b in iv) / len(iv))))
@h("interval_scheduling", "latest start first")
def _(s, q):
    n, last = 0, 10**9
    for a, b in sorted(s["meetings"], key=lambda x: (-x[0], -x[1])):
        if b <= last:
            n += 1
            last = a
    return str(n)


# ---------------- rev2 ----------------
@h("expression_eval", "LTR item: usual precedence (ignore the stated rule)")
def _(s, q): return str(S._eval_ranked(S._tok(s["text"]))) if s["convention"] == "left_to_right" else None
@h("expression_eval", "ranked item: strict left to right (ignore precedence)")
def _(s, q): return str(S._eval_ltr(S._tok(s["text"]))) if s["convention"] == "ranked" else None
@h("expression_eval", "ignore parentheses, usual precedence")
def _(s, q): return str(S._eval_ranked([t for t in S._tok(s["text"]) if t not in "()"]))
@h("expression_eval", "ignore parentheses, stated rule")
def _(s, q):
    toks = [t for t in S._tok(s["text"]) if t not in "()"]
    return str(S._eval_ranked(toks) if s["convention"] == "ranked" else S._eval_ltr(toks))
@h("expression_eval", "ranked: + before - (old 'same symbol' reading)")
def _(s, q):
    if s["convention"] != "ranked":
        return None
    prec = {"+": 2, "-": 1, "*": 3}
    out, ops = [], []
    for t in S._tok(s["text"]):
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
    out += ops[::-1]
    st = []
    for t in out:
        if isinstance(t, int):
            st.append(t)
        else:
            b, a = st.pop(), st.pop()
            st.append(a + b if t == "+" else a - b if t == "-" else a * b)
    return str(st[0])
@h("expression_eval", "LTR: usual precedence inside parentheses only (old ambiguity)")
def _(s, q):
    if s["convention"] != "left_to_right":
        return None
    toks = S._tok(s["text"])
    # evaluate innermost parentheses with precedence, then the top level left to right
    def ev(i, top):
        vals = []
        while i < len(toks) and toks[i] != ")":
            t = toks[i]
            if t == "(":
                v, i = ev(i + 1, False)
                vals.append(str(v))
            else:
                vals.append(t)
            i += 1
        r = S._eval_ltr(vals) if top else S._eval_ranked(vals)
        return r, i
    return str(ev(0, True)[0])


@h("merge_smallest_cost", "(P) adjacent piles only (old misreading)")
def _(s, q):
    ws = s["ws"]
    n = len(ws)
    pre = [0]
    for w in ws:
        pre.append(pre[-1] + w)
    @lru_cache(None)
    def f(i, j):
        if i == j:
            return 0
        return min(f(i, k) + f(k + 1, j) for k in range(i, j)) + pre[j + 1] - pre[i]
    return str(f(0, n - 1))
@h("merge_smallest_cost", "ascending chain (sorted, merge left to right)")
def _(s, q):
    ws = sorted(s["ws"]); acc = ws[0]; tot = 0
    for w in ws[1:]:
        acc += w; tot += acc
    return str(tot)
@h("merge_smallest_cost", "sum * ceil(log2 n)")
def _(s, q): return str(sum(s["ws"]) * math.ceil(math.log2(len(s["ws"]))))
@h("merge_smallest_cost", "chain in the written order")
def _(s, q):
    ws = s["ws"]; acc = ws[0]; tot = 0
    for w in ws[1:]:
        acc += w; tot += acc
    return str(tot)


@h("chip_toppling", "closed form: Green's function with the conservation final row")
def _(s, q):
    c = s["row"]; n = len(c)
    tot = sum(c)
    if tot < n:
        return None
    # final row: all ones with at most one zero; position from the first moment mod (n+1) (audit 1's formula)
    z = (n * (n + 1) // 2 - sum((i + 1) * x for i, x in enumerate(c))) % (n + 1)
    f = [1] * n
    if z:
        f[z - 1] = 0
    def G(i, j):  # 1-based Dirichlet Green's function on a path of n cells
        return min(i, j) * (n + 1 - max(i, j)) / (n + 1)
    u = [sum(G(i, j) * (c[j - 1] - f[j - 1]) for j in range(1, n + 1)) for i in range(1, n + 1)]
    if s["ask"] == "topplings":
        return str(round(sum(u)))
    return str(round(u[s["cell"] - 1]))
@h("chip_toppling", "total: chips - n")
def _(s, q): return str(sum(s["row"]) - len(s["row"])) if s["ask"] == "topplings" else None
@h("chip_toppling", "cell: its own chips // 2")
def _(s, q): return str(s["row"][s["cell"] - 1] // 2) if s["ask"] == "topplings_of" else None
@h("chip_toppling", "total: sum of max(0, c-1)")
def _(s, q): return str(sum(max(0, x - 1) for x in s["row"])) if s["ask"] == "topplings" else None


def _pairs(t):
    st, out = [], []
    for i, c in enumerate(t):
        if c in "([{":
            st.append(i)
        else:
            out.append((st.pop(), i))
    return out


@h("bracket_match", "valid: each kind balanced on its own (depth never negative)")
def _(s, q):
    if s["ask"] != "valid":
        return None
    t = s["s"]
    for o, c in ("()", "[]", "{}"):
        d = 0
        for ch in t:
            d += ch == o
            d -= ch == c
            if d < 0:
                return "no"
        if d:
            return "no"
    return "yes"
@h("bracket_match", "valid: every adjacent opener-closer pair matches")
def _(s, q):
    if s["ask"] != "valid":
        return None
    t = s["s"]; mp = {")": "(", "]": "[", "}": "{"}
    for i in range(len(t) - 1):
        if t[i] in "([{" and t[i + 1] in ")]}" and mp[t[i + 1]] != t[i]:
            return "no"
    return "yes"
@h("bracket_match", "valid: first and last characters match")
def _(s, q):
    if s["ask"] != "valid":
        return None
    t = s["s"]
    return "yes" if {"(": ")", "[": "]", "{": "}"}.get(t[0]) == t[-1] else "no"
@h("bracket_match", "valid: depth profile ignoring kinds + the closer at each depth return matches the most recent opener at that depth (kinds only)")
def _(s, q):
    if s["ask"] != "valid":
        return None
    # check only pairs whose content is a single adjacent pair or empty, i.e. depth <= 2 pairs (a partial stack check)
    t = s["s"]; mp = {")": "(", "]": "[", "}": "{"}
    st = []
    for ch in t:
        if ch in "([{":
            st.append(ch)
        else:
            o = st.pop() if st else None
            if len(st) == 0 and o != mp[ch]:
                return "no"  # only the outermost level is checked
    return "yes"
@h("bracket_match", "valid: closers read right-to-left mirror the openers (kind sequence)")
def _(s, q):
    if s["ask"] != "valid":
        return None
    t = s["s"]; mp = {")": "(", "]": "[", "}": "{"}
    ops = [c for c in t if c in "([{"]
    cls = [mp[c] for c in t if c in ")]}"][::-1]
    return "yes" if ops == cls else "no"
@h("bracket_match", "valid: per kind, the k-th opener of that kind and the k-th closer of that kind from the end match up as a nested pair ... (kind multiset equal at every prefix depth) [count only]")
def _(s, q):
    return "yes" if s["ask"] == "valid" else None


def _match_heur(t, p, mode):
    want = {"(": ")", "[": "]", "{": "}"}[t[p]]
    same = [i for i in range(p + 1, len(t)) if t[i] == want]
    if mode == "next_same":
        return same[0] if same else None
    if mode == "second_same":
        return same[1] if len(same) > 1 else None
    if mode == "last_same":
        return same[-1] if same else None
    if mode == "mirror":
        return len(t) - 1 - p
    if mode == "next_closer_any_after_content":
        cl = [i for i in range(p + 2, len(t)) if t[i] in ")]}"]
        return cl[0] if cl else None
    if mode == "next_same_after_content":
        cand = [i for i in same if i > p + 1]
        return cand[0] if cand else None


for _m in ("next_same", "second_same", "last_same", "mirror", "next_closer_any_after_content", "next_same_after_content"):
    def _mk(m):
        def f(s, q):
            if s["ask"] != "match":
                return None
            r = _match_heur(s["s"], s["p"] - 1, m)
            return None if r is None else str(r + 1)
        return f
    H.setdefault("bracket_match", []).append((f"match: {_m}", _mk(_m)))


@h("coin_change_min", "constant 1")
def _(s, q): return "1"
@h("coin_change_min", "constant 2")
def _(s, q): return "2"
@h("coin_change_min", "number of coin kinds that divide the amount")
def _(s, q): return str(sum(1 for c in s["coins"] if s["amount"] % c == 0))
@h("coin_change_min", "amount // largest + 1")
def _(s, q): return str(s["amount"] // max(s["coins"]) + 1)
@h("coin_change_min", "(P) ordered sequences (compositions) instead of sets")
def _(s, q):
    w = [1] + [0] * s["amount"]
    for v in range(1, s["amount"] + 1):
        w[v] = sum(w[v - c] for c in s["coins"] if c <= v)
    return str(w[-1])
@h("coin_change_min", "(P) fewest coins (old question)")
def _(s, q):
    INF = 10**9; d = [0] + [INF] * s["amount"]
    for v in range(1, s["amount"] + 1):
        d[v] = min([d[v - c] + 1 for c in s["coins"] if c <= v] + [INF])
    return str(d[-1]) if d[-1] < INF else None


@h("hash_probe", "slot: home (key mod m)")
def _(s, q): return str(s["target"] % s["m"]) if s["ask"] == "slot" else None
@h("hash_probe", "slot: home + earlier keys with the same home")
def _(s, q):
    if s["ask"] != "slot":
        return None
    m, ks, x = s["m"], s["keys"], s["target"]
    i = ks.index(x)
    return str((x % m + sum(1 for k in ks[:i] if k % m == x % m)) % m)
@h("hash_probe", "slot: max(home, number of keys before it + min home)")
def _(s, q):
    if s["ask"] != "slot":
        return None
    m, ks, x = s["m"], s["keys"], s["target"]
    i = ks.index(x)
    base = min(k % m for k in ks[: i + 1])
    return str(max(x % m, base + i) % m)
@h("hash_probe", "slot: insertion index (0-based)")
def _(s, q):
    return str(s["keys"].index(s["target"])) if s["ask"] == "slot" else None
@h("hash_probe", "probes: m - 1 - home  (= len(keys) - home)")
def _(s, q):
    return str(len(s["keys"]) - s["target"] % s["m"]) if s["ask"] == "probes" else None
@h("hash_probe", "probes: m - 2 - home + 1 with the block assumed to start at the smallest home")
def _(s, q):
    if s["ask"] != "probes":
        return None
    m, ks = s["m"], s["keys"]
    base = min(k % m for k in ks)
    return str(base + len(ks) - 1 - ks[-1] % m + 1)
@h("hash_probe", "probes: constant 2")
def _(s, q): return "2" if s["ask"] == "probes" else None


@h("cache_eviction", "misses: number of distinct items")
def _(s, q): return str(len(set(s["seq"]))) if s["ask"] == "misses" else None
@h("cache_eviction", "misses: (P) the other policy")
def _(s, q):
    if s["ask"] != "misses":
        return None
    return S.cache_eviction({**s, "policy": "fifo" if s["policy"] == "lru" else "lru"}, q)
@h("cache_eviction", "misses: requests that differ from the previous request")
def _(s, q):
    if s["ask"] != "misses":
        return None
    seq = s["seq"]
    return str(1 + sum(1 for a, b in zip(seq, seq[1:]) if a != b))
@h("cache_eviction", "misses: requests not among the previous cap requests")
def _(s, q):
    if s["ask"] != "misses":
        return None
    seq, c = s["seq"], s["cap"]
    return str(sum(1 for i, x in enumerate(seq) if x not in seq[max(0, i - c):i]))
@h("cache_eviction", "present: never requested -> no, else yes")
def _(s, q):
    if s["ask"] != "present":
        return None
    return "yes" if s["item"] in s["seq"] else "no"
@h("cache_eviction", "present: among the last cap DISTINCT requests (LRU answer)")
def _(s, q):
    if s["ask"] != "present":
        return None
    seen = []
    for x in reversed(s["seq"]):
        if x not in seen:
            seen.append(x)
    return "yes" if s["item"] in seen[: s["cap"]] else "no"
@h("cache_eviction", "present: in the last cap requests")
def _(s, q):
    return ("yes" if s["item"] in s["seq"][-s["cap"]:] else "no") if s["ask"] == "present" else None
@h("cache_eviction", "present: requested in the second half")
def _(s, q):
    if s["ask"] != "present":
        return None
    seq = s["seq"]
    return "yes" if s["item"] in seq[len(seq) // 2:] else "no"


def _g(n, moves):
    g = [0] * (n + 1)
    for x in range(1, n + 1):
        st = {g[x - m] for m in moves if m <= x}
        v = 0
        while v in st:
            v += 1
        g[x] = v
    return g[n]


@h("subtraction_game", "equal piles -> no, else yes")
def _(s, q): return "no" if s["piles"][0] == s["piles"][1] else "yes"
@h("subtraction_game", "n1 mod (max+1) xor n2 mod (max+1) != 0 (Nim with 1..max)")
def _(s, q):
    k = max(s["moves"]) + 1
    return "yes" if (s["piles"][0] % k) ^ (s["piles"][1] % k) else "no"
@h("subtraction_game", "n1 mod (min+max) == n2 mod (min+max) -> no")
def _(s, q):
    k = min(s["moves"]) + max(s["moves"])
    return "no" if s["piles"][0] % k == s["piles"][1] % k else "yes"
@h("subtraction_game", "(P) one pile of n1+n2: grundy != 0")
def _(s, q): return "yes" if _g(sum(s["piles"]), s["moves"]) else "no"
@h("subtraction_game", "total stones odd -> yes")
def _(s, q): return "yes" if sum(s["piles"]) % 2 else "no"
@h("subtraction_game", "plain Nim xor of the pile sizes")
def _(s, q): return "yes" if s["piles"][0] ^ s["piles"][1] else "no"
@h("subtraction_game", "smallest move is 1 -> ...: parity of (n1+n2)//min")
def _(s, q): return "yes" if (sum(s["piles"]) // min(s["moves"])) % 2 else "no"
@h("subtraction_game", "win/lose of each pile alone (grundy != 0) equal -> no")
def _(s, q):
    a = _g(s["piles"][0], s["moves"]) != 0
    b = _g(s["piles"][1], s["moves"]) != 0
    return "no" if a == b else "yes"


def _edges(s):
    idx = {t: i for i, t in enumerate(s["towns"])}
    return [(idx[a], idx[b], w) for a, b, w in s["cables"]], len(s["towns"])


@h("cheapest_network", "n-1 cheapest cables")
def _(s, q):
    e, n = _edges(s)
    return str(sum(sorted(w for _, _, w in e)[: n - 1]))
@h("cheapest_network", "sum of each town's cheapest cable")
def _(s, q):
    e, n = _edges(s)
    b = {}
    for a, c, w in e:
        for t in (a, c):
            b[t] = min(b.get(t, 99), w)
    return str(sum(b.values()))
@h("cheapest_network", "cheap cables (<=6) minus the dearest of each triangle + the (g-1) cheapest dear cables")
def _(s, q):
    e, n = _edges(s)
    cheap = sorted(w for _, _, w in e if w <= 6)
    dear = sorted(w for _, _, w in e if w > 6)
    g = n // 3
    # drop the largest of each triangle: group the cheap edges by component
    par = list(range(n))
    def f(x):
        while par[x] != x:
            x = par[x]
        return x
    for a, b, w in e:
        if w <= 6:
            par[f(a)] = f(b)
    comp = {}
    for a, b, w in e:
        if w <= 6:
            comp.setdefault(f(a), []).append(w)
    tot = sum(sum(v) - max(v) for v in comp.values())
    return str(tot + sum(dear[: g - 1]))
@h("cheapest_network", "sum of all cables minus the dearest")
def _(s, q):
    e, n = _edges(s)
    ws = sorted(w for _, _, w in e)
    return str(sum(ws) - ws[-1])


@h("max_subarray_sum", "best run of non-negative numbers")
def _(s, q):
    best = cur = 0
    for x in s["xs"]:
        cur = cur + x if x >= 0 else 0
        best = max(best, cur)
    return str(best)
@h("max_subarray_sum", "best window of exactly 7 neighbouring numbers")
def _(s, q):
    xs = s["xs"]
    return str(max(sum(xs[i:i + 7]) for i in range(len(xs) - 6))) if len(xs) >= 7 else None
@h("max_subarray_sum", "two largest positive runs + the one number between them if adjacent")
def _(s, q):
    xs = s["xs"]; runs = []; i = 0
    while i < len(xs):
        if xs[i] > 0:
            j = i
            while j < len(xs) and xs[j] > 0:
                j += 1
            runs.append((sum(xs[i:j]), i, j)); i = j
        else:
            i += 1
    best = max(r[0] for r in runs)
    for a, b in zip(runs, runs[1:]):
        if b[1] == a[2] + 1:
            best = max(best, a[0] + b[0] + xs[a[2]])
    return str(best)
@h("max_subarray_sum", "sum of all positive numbers")
def _(s, q): return str(sum(x for x in s["xs"] if x > 0))
@h("max_subarray_sum", "split at numbers <= -12, best segment total")
def _(s, q):
    best, cur = -10**9, 0
    for x in s["xs"] + [-99]:
        if x <= -12:
            best = max(best, cur); cur = 0
        else:
            cur += x
    return str(best)


@h("gcd_euclid", "gcd: a - b")
def _(s, q): return str(s["a"] - s["b"]) if s["ask"] == "gcd" else None
@h("gcd_euclid", "gcd: a mod b (one Euclid step)")
def _(s, q): return str(s["a"] % s["b"]) if s["ask"] == "gcd" else None
@h("gcd_euclid", "gcd: smallest prime >= 11 dividing b")
def _(s, q):
    if s["ask"] != "gcd":
        return None
    b = s["b"]
    for p in range(11, b + 1):
        if b % p == 0 and all(p % d for d in range(2, int(p ** 0.5) + 1)):
            return str(p)
@h("gcd_euclid", "gcd: largest prime factor of b")
def _(s, q): return str(max(S._factor(s["b"]))) if s["ask"] == "gcd" else None
@h("gcd_euclid", "lcm: a * b")
def _(s, q): return str(s["a"] * s["b"]) if s["ask"] == "lcm" else None
@h("gcd_euclid", "lcm: a*b // (a-b)")
def _(s, q): return str(s["a"] * s["b"] // (s["a"] - s["b"])) if s["ask"] == "lcm" else None


@h("modular_power", "a^2 mod m")
def _(s, q): return str(pow(s["a"], 2, s["m"]))
@h("modular_power", "a^(e mod (m-1)) mod m (Fermat misuse)")
def _(s, q): return str(pow(s["a"], s["e"] % (s["m"] - 1), s["m"]))
@h("modular_power", "(P) a^(e mod phi(m)) mod m (Euler; valid when gcd(a,m)=1)")
def _(s, q):
    m = s["m"]
    ps = sorted(set(S._factor(m)))
    phi = m
    for p in ps:
        phi = phi // p * (p - 1)
    return str(pow(s["a"], s["e"] % phi, m))
@h("modular_power", "a mod m")
def _(s, q): return str(s["a"] % s["m"])
@h("modular_power", "constant 1")
def _(s, q): return "1"
@h("modular_power", "a*e mod m")
def _(s, q): return str(s["a"] * s["e"] % s["m"])


@h("lcs_length", "letter-count overlap")
def _(s, q):
    a, b = s["a"], s["b"]
    return str(sum(min(a.count(c), b.count(c)) for c in set(a)))
@h("lcs_length", "letter-count overlap - 2")
def _(s, q):
    a, b = s["a"], s["b"]
    return str(sum(min(a.count(c), b.count(c)) for c in set(a)) - 2)
@h("lcs_length", "greedy matching, better of the two directions")
def _(s, q):
    def gr(a, b):
        j = n = 0
        for c in a:
            k = b.find(c, j)
            if k >= 0:
                n += 1; j = k + 1
        return n
    return str(max(gr(s["a"], s["b"]), gr(s["b"], s["a"])))
@h("lcs_length", "shorter length - 2")
def _(s, q): return str(min(len(s["a"]), len(s["b"])) - 2)
@h("lcs_length", "round(0.6 * shorter length)")
def _(s, q): return str(round(0.6 * min(len(s["a"]), len(s["b"]))))


@h("lis_length", "greedy: take each number larger than the last taken")
def _(s, q):
    n, last = 0, -1
    for x in s["xs"]:
        if x > last:
            n += 1; last = x
    return str(n)
@h("lis_length", "longest run of adjacent increases")
def _(s, q):
    best = cur = 1; xs = s["xs"]
    for a, b in zip(xs, xs[1:]):
        cur = cur + 1 if b > a else 1
        best = max(best, cur)
    return str(best)
@h("lis_length", "round(2 sqrt n) - 2")
def _(s, q): return str(round(2 * math.sqrt(len(s["xs"]))) - 2)
@h("lis_length", "n // 2")
def _(s, q): return str(len(s["xs"]) // 2)
@h("lis_length", "best greedy over every start")
def _(s, q):
    xs = s["xs"]; best = 0
    for i in range(len(xs)):
        n, last = 0, -1
        for x in xs[i:]:
            if x > last:
                n += 1; last = x
        best = max(best, n)
    return str(best)


@h("longest_palindromic_substring", "longest run of one letter")
def _(s, q): return str(max(len(list(g)) for _, g in itertools.groupby(s["s"])))
@h("longest_palindromic_substring", "longest odd palindrome only")
def _(s, q):
    t = s["s"]; best = 1
    for c in range(len(t)):
        lo = hi = c
        while lo >= 0 and hi < len(t) and t[lo] == t[hi]:
            lo -= 1; hi += 1
        best = max(best, hi - lo - 1)
    return str(best)
@h("longest_palindromic_substring", "longest even palindrome only")
def _(s, q):
    t = s["s"]; best = 0
    for c in range(len(t) - 1):
        lo, hi = c, c + 1
        while lo >= 0 and hi < len(t) and t[lo] == t[hi]:
            lo -= 1; hi += 1
        best = max(best, hi - lo - 1)
    return str(best)


@h("prime_factor_query", "largest: largest prime <= sqrt(n) dividing n")
def _(s, q):
    if s["ask"] != "largest":
        return None
    n = s["n"]
    ps = [p for p in range(2, int(n ** 0.5) + 1) if n % p == 0 and all(p % d for d in range(2, int(p ** 0.5) + 1))]
    return str(ps[-1]) if ps else None
@h("prime_factor_query", "sum_all: sum of the different primes")
def _(s, q): return str(sum(set(S._factor(s["n"])))) if s["ask"] == "sum_all" else None
@h("prime_factor_query", "largest: largest prime <= 97 dividing n, scanning only primes up to 61")
def _(s, q):
    if s["ask"] != "largest":
        return None
    ps = [p for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61) if s["n"] % p == 0]
    return str(ps[-1]) if ps else None


@h("crt_smallest", "product of moduli - 1")
def _(s, q): return str(math.prod(m for _, m in s["congruences"]) - 1)
@h("crt_smallest", "sum of remainders")
def _(s, q): return str(sum(r for r, _ in s["congruences"]))
@h("crt_smallest", "r1 + m1 * r2 (first two)")
def _(s, q):
    (r1, m1), (r2, m2) = s["congruences"][:2]
    return str(r1 + m1 * r2)
@h("crt_smallest", "(P) least common value ignoring the third congruence")
def _(s, q):
    cs = s["congruences"]
    if len(cs) < 3:
        return None
    return S.crt_smallest({"congruences": cs[:2]}, q)
