"""Second solvers (M0, ADR-0033 addendum 1, section 8 item 1), NAME=r2b, EVAL=R2.

Written from the answer-free fixtures (question text, `structured`, SCHEMA.md) only.
Standard library only. Each solver fn(question, structured) -> answer string.
Every solver computes from `structured`; `parse_text_<lineage>` re-derives the same
inputs from the question text so run_solver2.py can check text and structure agree.
"""
import re

# ---------------- R2.grid_sum ----------------
def grid_sum(question, structured):
    g = structured["grid"]
    what = structured["what"]
    if what.startswith("the diagonal from the top left corner"):
        k = min(len(g), len(g[0]))          # cells (1,1), (2,2), ... while both exist
        return str(sum(g[i][i] for i in range(k)))
    m = re.fullmatch(r"row (\d+)", what)
    if m:
        return str(sum(g[int(m.group(1)) - 1]))   # rows numbered from 1, top first
    m = re.fullmatch(r"column (\d+)", what)
    if m:
        c = int(m.group(1)) - 1                   # columns numbered from 1, left first
        return str(sum(r[c] for r in g))
    raise ValueError("unknown 'what': %r" % what)

def parse_text_grid_sum(q):
    m = re.search(r"A grid has (\d+) rows and (\d+) columns\. The rows, from top to bottom, are: (.*?)\. What is the sum of the numbers in (.*)\?$", q)
    R, C = int(m.group(1)), int(m.group(2))
    grid = [[int(x) for x in row.split()] for row in m.group(3).split(" / ")]
    assert len(grid) == R and all(len(r) == C for r in grid)
    return {"grid": grid, "what": m.group(4)}

# ---------------- R2.list_ops ----------------
def list_ops(question, structured):
    xs = list(structured["xs"])
    for op in structured["ops"]:
        name = op[0]
        if name == "append":
            xs.append(op[1])
        elif name == "drop_first":
            if not xs: raise ValueError("drop_first on empty list")
            xs = xs[1:]
        elif name == "drop_last":
            if not xs: raise ValueError("drop_last on empty list")
            xs = xs[:-1]
        elif name == "reverse":
            xs = xs[::-1]
        elif name == "first_to_end":
            if not xs: raise ValueError("first_to_end on empty list")
            xs = xs[1:] + xs[:1]
        else:
            raise ValueError("unknown op %r" % name)
    return ", ".join(str(x) for x in xs)

_LIST_PHRASES = {"remove the first element": ["drop_first"], "remove the last element": ["drop_last"],
                 "reverse the list": ["reverse"], "move the first element to the end": ["first_to_end"]}
def parse_text_list_ops(q):
    m = re.fullmatch(r"Start with the list (.*?)\. Do these steps in order: (.*?)\. What is the final list\? Give the numbers separated by commas\.", q)
    xs = [int(x) for x in m.group(1).split(", ")]
    ops = []
    for p in m.group(2).split("; "):
        a = re.fullmatch(r"add (-?\d+) at the end", p)
        ops.append(["append", int(a.group(1))] if a else _LIST_PHRASES[p])
    return {"xs": xs, "ops": ops}

# ---------------- R2.luhn_check ----------------
def _luhn_total(digits):
    """Total per the question: rightmost digit is the 1st; even positions doubled, minus 9 if > 9."""
    tot = 0
    for pos, d in enumerate(reversed(digits), start=1):
        if pos % 2 == 0:
            d = 2 * d
            if d > 9:
                d -= 9
        tot += d
    return tot

def luhn_check(question, structured):
    digits = list(structured["digits"])
    ask = structured["ask"]
    if ask == "valid":
        return "yes" if _luhn_total(digits) % 10 == 0 else "no"
    if ask == "check_digit":
        good = [c for c in range(10) if _luhn_total(digits + [c]) % 10 == 0]
        if len(good) != 1: raise ValueError("check digit not unique: %r" % good)
        return str(good[0])
    raise ValueError("unknown ask %r" % ask)

def parse_text_luhn_check(q):
    m = re.search(r"One more digit is to be written at the right end of (\d+) so that", q)
    if m:
        return {"digits": [int(c) for c in m.group(1)], "ask": "check_digit"}
    m = re.search(r"Is the number (\d+) valid\? Answer yes or no\.$", q)
    return {"digits": [int(c) for c in m.group(1)], "ask": "valid"}

# ---------------- R2.min_heap_ops ----------------
def min_heap_ops(question, structured):
    h = [None]  # 1-based positions
    for x in structured["xs"]:
        h.append(x)
        p = len(h) - 1
        while p > 1 and h[p] < h[p // 2]:        # strictly smaller than parent -> swap
            h[p], h[p // 2] = h[p // 2], h[p]
            p //= 2
    for _ in range(structured["removals"]):
        if len(h) <= 1: raise ValueError("remove from empty heap")
        last = h.pop()
        if len(h) > 1:
            h[1] = last
            p = 1
            n = len(h) - 1
            while True:
                kids = [c for c in (2 * p, 2 * p + 1) if c <= n]
                if not kids: break
                vals = [h[c] for c in kids]
                if len(kids) == 2 and vals[0] == vals[1]:
                    raise ValueError("tie between children; rule does not say which")
                c = kids[0] if len(kids) == 1 or vals[0] < vals[1] else kids[1]
                if h[p] > h[c]:                     # strictly larger than the smaller child
                    h[p], h[c] = h[c], h[p]
                    p = c
                else:
                    break
    return ", ".join(str(x) for x in h[1:])

def parse_text_min_heap_ops(q):
    m = re.search(r"add these numbers in order: (.*?)\.( Then remove the smallest (\d+) times?\.)? Give the row from position 1 to the end, separated by commas\.$", q)
    return {"xs": [int(x) for x in m.group(1).split(", ")], "removals": int(m.group(3)) if m.group(3) else 0}

# ---------------- R2.run_length ----------------
def run_length(question, structured):
    s = structured["s"]
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(s[i] + str(j - i))
        i = j
    return "".join(out)

def parse_text_run_length(q):
    m = re.match(r"Compress ([a-z]+) by run-length encoding: ", q)
    return {"s": m.group(1)}

# ---------------- R2.sort_list ----------------
def sort_list(question, structured):
    xs = sorted(structured["xs"], reverse=bool(structured["desc"]))
    return ", ".join(str(x) for x in xs)

def parse_text_sort_list(q):
    m = re.fullmatch(r"Sort these numbers from (smallest to largest|largest to smallest) and give them separated by commas: (.*)\.", q)
    return {"xs": [int(x) for x in m.group(2).split(", ")], "desc": m.group(1) == "largest to smallest"}

# ---------------- R2.string_rewrite_nonidentity ----------------
def _replace_scan(s, pat, rep):
    """Left-to-right scan over non-overlapping matches of `pat` in s as it is at step start;
    replacement text is not rescanned within the step."""
    if not pat: raise ValueError("empty pattern")
    out = []
    i = 0
    while i < len(s):
        if s.startswith(pat, i):
            out.append(rep)
            i += len(pat)
        else:
            out.append(s[i])
            i += 1
    return "".join(out)

def string_rewrite_nonidentity(question, structured):
    s = structured["s"]
    for pat, rep in structured["rules"]:
        s = _replace_scan(s, pat, rep)
    return s

def parse_text_string_rewrite_nonidentity(q):
    m = re.fullmatch(r"Start with the string ([a-z]+)\. Do these steps in order, each step scanning left to right over non-overlapping matches in the string as it is when the step starts: (.*?)\. What is the final string\?", q)
    rules = []
    for p in m.group(2).split("; "):
        a = re.fullmatch(r"replace every '([a-z]+)' with '([a-z]*)'", p)
        if a:
            rules.append([a.group(1), a.group(2)])
        else:
            d = re.fullmatch(r"delete every '([a-z]+)'", p)
            rules.append([d.group(1), ""])
    return {"s": m.group(1), "rules": rules}

# ---------------- R2.to_base_wide ----------------
_DIG = "0123456789abcdef"
def to_base_wide(question, structured):
    n, b = int(structured["n"]), int(structured["base"])
    if not 2 <= b <= 16: raise ValueError("base out of range")
    if n < 0: raise ValueError("negative n")
    if n == 0: return "0"
    out = []
    while n:
        n, r = divmod(n, b)
        out.append(_DIG[r])
    return "".join(reversed(out))

def parse_text_to_base_wide(q):
    m = re.fullmatch(r"Write the decimal number (\d+) in base (\d+)\. Use digits 0-9 and then lowercase letters a-f for ten to fifteen\.", q)
    return {"n": int(m.group(1)), "base": int(m.group(2))}

SOLVERS = {
    "R2.grid_sum": grid_sum,
    "R2.list_ops": list_ops,
    "R2.luhn_check": luhn_check,
    "R2.min_heap_ops": min_heap_ops,
    "R2.run_length": run_length,
    "R2.sort_list": sort_list,
    "R2.string_rewrite_nonidentity": string_rewrite_nonidentity,
    "R2.to_base_wide": to_base_wide,
}

TEXT_PARSERS = {
    "R2.grid_sum": parse_text_grid_sum,
    "R2.list_ops": parse_text_list_ops,
    "R2.luhn_check": parse_text_luhn_check,
    "R2.min_heap_ops": parse_text_min_heap_ops,
    "R2.run_length": parse_text_run_length,
    "R2.sort_list": parse_text_sort_list,
    "R2.string_rewrite_nonidentity": parse_text_string_rewrite_nonidentity,
    "R2.to_base_wide": parse_text_to_base_wide,
}
