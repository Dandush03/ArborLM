# ruff: noqa
"""Final R2 audit: NEW cheap rules (written by the final auditor in this audit, under one hour). They do NOT decide a drop here (brief);
each reads only the question text and returns an answer string or None (= does not apply; counted wrong for open answers).
Each rule carries my class in its name: (cue), (partial) = truncated procedure, (P) = full solve under a misreading of a stated convention."""
import re
from math import gcd

NEW = {}


def rule(lineage, name):
    def deco(fn):
        NEW.setdefault(lineage, []).append((name, fn))
        return fn
    return deco


def _crt(q):
    return [(int(r), int(m)) for r, m in re.findall(r"leaves remainder (\d+) when divided by (\d+)", q)]


@rule("crt_smallest", "(partial) largest modulus: try r, r+m, r+2m against the other congruences, else r")
def _(s, q):
    p = _crt(q)
    r, m = max(p, key=lambda x: x[1])
    for t in range(3):
        x = r + m * t
        if x > 0 and all(x % mm == rr for rr, mm in p):
            return str(x)
    return str(r)


@rule("crt_smallest", "(cue) common offset: equal remainders -> r; equal (m - r) -> lcm - (m - r)")
def _(s, q):
    p = _crt(q)
    L = 1
    for _, m in p:
        L = L * m // gcd(L, m)
    if len({r for r, _ in p}) == 1 and p[0][0] > 0:
        return str(p[0][0])
    if len({m - r for r, m in p}) == 1:
        return str(L - (p[0][1] - p[0][0]))
    return None


@rule("crt_smallest", "(cue) largest remainder + its modulus")
def _(s, q):
    r, m = max(_crt(q))
    return str(r + m)


def _meet(q):
    return [(int(i), int(a), int(b)) for i, a, b in re.findall(r"meeting (\d+) runs from (\d+) to (\d+)", q)]










def _expr(q):
    return re.search(r"Work out (.*?)(?:\. Use these rules| by this rule)", q).group(1)


def _ltr(tokens):
    v = int(tokens[0])
    for i in range(1, len(tokens), 2):
        op, w = tokens[i], int(tokens[i + 1])
        v = v + w if op == "+" else v - w if op == "-" else v * w
    return v


@rule("expression_eval", "(cue) parentheses ignored, the item's own convention otherwise")
def _(s, q):
    e = _expr(q).replace("(", "").replace(")", "")
    toks = re.findall(r"\d+|[-+*]", e)
    if "multiplication gets no priority" in q:
        return str(_ltr(toks))
    return str(eval(" ".join(toks)))


@rule("expression_eval", "(cue) the other convention (ranked item worked left to right, left-to-right item worked with precedence)")
def _(s, q):
    e = _expr(q)
    if "multiplication gets no priority" in q:
        return str(eval(e))
    return None  # the ranked case is the battery's '[a3] ranked item: strict left to right'


def _towns(q):
    return [(int(c), a, b) for a, b, c in re.findall(r"A cable between ([A-Z][a-z]+) and ([A-Z][a-z]+) would cost (\d+)\.", q)]


@rule("cheapest_network", "(cue) nearest-neighbour path from the first listed town")
def _(s, q):
    towns = [t.strip() for t in re.split(r", | and ", re.search(r"The towns (.*?) must be joined", q).group(1))]
    E = {}
    for c, a, b in _towns(q):
        E[(a, b)] = E[(b, a)] = c
    cur, seen, tot = towns[0], {towns[0]}, 0
    while len(seen) < len(towns):
        opts = [(E[(cur, t)], t) for t in towns if t not in seen and (cur, t) in E]
        if not opts:
            return None
        c, t = min(opts)
        tot += c; seen.add(t); cur = t
    return str(tot)


@rule("count_divisible", "(P) misread: each distinct value counted once (the wording now excludes it)")
def _(s, q):
    m = re.search(r"divisible by (\d+) and greater than (-?\d+)\?", q)
    d, t = int(m.group(1)), int(m.group(2))
    xs = {int(x) for x in re.findall(r"-?\d+", re.search(r"List: (.*)\.$", q.strip()).group(1))}
    return str(sum(x for x in xs if x % d == 0 and x > t))


@rule("string_rewrite_nonidentity", "(P) misread: each step repeated until no match is left (capped at 50 rounds)")
def _(s, q):
    st = re.search(r"Start with the string ([a-z]+)\.", q).group(1)
    for step in re.search(r"when the step starts: (.*?)\. What is the final string", q).group(1).split("; "):
        m = re.fullmatch(r"replace every '([a-z]+)' with '([a-z]*)'", step) or re.fullmatch(r"delete every '([a-z]+)'()", step)
        a, b = m.group(1), m.group(2)
        for _ in range(50):
            if a not in st or len(st) > 2000:
                break
            st = st.replace(a, b)
        if a in st:
            return None
    return st


@rule("run_length", "(cue) each letter with its total count, in order of first appearance")
def _(s, q):
    w = re.search(r"Compress ([a-z]+) by", q).group(1)
    seen = []
    for c in w:
        if c not in seen:
            seen.append(c)
    return "".join(f"{c}{w.count(c)}" for c in seen)


@rule("min_heap_ops", "(cue) row sorted ascending except positions 2 and 3 swapped when out of order")
def _(s, q):
    xs = [int(x) for x in re.search(r"add these numbers in order: (.*?)\.", q).group(1).split(", ")]
    k = re.search(r"remove the smallest (\d+) time", q)
    xs = sorted(xs)[int(k.group(1)) if k else 0:]
    return ", ".join(map(str, xs))


@rule("binary_search_trace", "(cue) sum ask: target x ceil(log2(n+1)) ; values ask: midpoints by position only, target appended")
def _(s, q):
    n = int(re.search(r"A sorted list of (\d+) numbers", q).group(1))
    t = int(re.search(r"is searched for (-?\d+)\.", q).group(1))
    if "What is the sum" in q:
        return str(t * n.bit_length())
    return str(t)


@rule("grid_sum", "(cue) the asked row/column/diagonal read with the index off by one (next one)")
def _(s, q):
    m = re.search(r"A grid has (\d+) rows and (\d+) columns\. The rows, from top to bottom, are: (.*?)\. What is", q)
    rows = [[int(x) for x in r.split()] for r in m.group(3).split(" / ")]
    a = re.search(r"in row (\d+)\?", q)
    if a:
        i = int(a.group(1))
        return str(sum(rows[i])) if i < len(rows) else None
    a = re.search(r"in column (\d+)\?", q)
    if a:
        j = int(a.group(1))
        return str(sum(r[j] for r in rows)) if j < len(rows[0]) else None
    return str(sum(rows[i][len(rows[0]) - 1 - i] for i in range(min(len(rows), len(rows[0])))))


@rule("list_ops", "(artifact) final list = start list with adds appended and removals applied, all moves and reverses ignored")
def _(s, q):
    xs = [int(x) for x in re.search(r"Start with the list (.*?)\. Do these steps", q).group(1).split(", ")]
    for op in re.search(r"Do these steps in order: (.*?)\. What is the final list", q).group(1).split("; "):
        if op == "remove the first element":
            xs = xs[1:]
        elif op == "remove the last element":
            xs = xs[:-1]
        elif op.startswith("add "):
            xs.append(int(op.split()[1]))
    return ", ".join(map(str, xs))


@rule("luhn_check", "(cue) check digit: (10 - digit sum mod 10) mod 10 with every digit doubled")
def _(s, q):
    m = re.search(r"right end of (\d+) so that", q)
    if not m:
        return None
    t = 0
    for c in m.group(1):
        d = 2 * int(c)
        t += d - 9 if d > 9 else d
    return str((10 - t % 10) % 10)


@rule("from_base", "(cue) digits read as a decimal number")
def _(s, q):
    d = re.search(r"base-\d+ number ([0-9a-z]+) written", q).group(1)
    return d if d.isdigit() else None


@rule("to_base_wide", "(cue) remainders of repeated division by the base, written in the order produced")
def _(s, q):
    m = re.search(r"Write the decimal number (\d+) in base (\d+)\.", q)
    n, b = int(m.group(1)), int(m.group(2))
    out = ""
    while n:
        n, r = divmod(n, b)
        out += "0123456789abcdef"[r]
    return out or "0"


@rule("list_ops", "[cond] (cue) moves and reverses ignored (items with at least one move or reverse)")
def _(s, q):
    ops = re.search(r"Do these steps in order: (.*?)\. What is the final list", q).group(1).split("; ")
    if not any(o in ("reverse the list", "move the first element to the end") for o in ops):
        return None
    xs = [int(x) for x in re.search(r"Start with the list (.*?)\. Do these steps", q).group(1).split(", ")]
    for op in ops:
        if op == "remove the first element":
            xs = xs[1:]
        elif op == "remove the last element":
            xs = xs[:-1]
        elif op.startswith("add "):
            xs.append(int(op.split()[1]))
    return ", ".join(map(str, xs))
