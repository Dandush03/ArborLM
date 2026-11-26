"""Second solvers (r2a) for 9 R2 lineages. Standard library only.

Written from answer-free fixtures (question text, structured, SCHEMA.md) only.
Each fn(question, structured) -> answer string. Where both `structured` and
the question text carry the inputs, the answer is computed from `structured`;
the text parsers in this module (`parse_*`) are used by run_solver2.py only to
cross-check that `structured` and the text agree.
"""
import itertools
import math
import re


# ---------------------------------------------------------------- binary search
def binary_search_trace(question, structured):
    xs = list(structured["xs"])
    target = structured["target"]
    ask = structured["ask"]
    lo, hi = 1, len(xs)
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
    if ask == "values":
        return ", ".join(str(v) for v in seen)
    if ask == "sum":
        return str(sum(seen))
    raise ValueError("unknown ask %r" % ask)


def parse_binary_search_trace(q):
    m = re.match(r"A sorted list of (\d+) numbers \(smallest first\) is searched for (-?\d+)\.", q)
    xs = [int(t) for t in re.search(r"The list: ([-\d, ]+)\.", q).group(1).split(", ")]
    if "Which numbers does the search look at, in order?" in q:
        ask = "values"
    elif "What is the sum of all the numbers the search looks at" in q:
        ask = "sum"
    else:
        raise ValueError("template")
    assert int(m.group(1)) == len(xs)
    return {"xs": xs, "target": int(m.group(2)), "ask": ask}


# ---------------------------------------------------------------- caesar shift
def caesar_shift(question, structured):
    k = structured["k"] % 26
    out = []
    for ch in structured["text"]:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + k) % 26 + 97))
        elif ch == " ":
            out.append(ch)
        else:
            raise ValueError("unexpected char %r" % ch)
    return "".join(out)


def parse_caesar_shift(q):
    m = re.fullmatch(r"Shift every letter of '([a-z ]+)' forward by (\d+) places in the alphabet, "
                     r"wrapping from z back to a\. Spaces stay\. What is the result\?", q)
    return {"text": m.group(1), "k": int(m.group(2))}


# ---------------------------------------------------------------- cellular automaton
def cellular_automaton(question, structured):
    if structured.get("ask", "row") != "row":
        raise ValueError("unknown ask")
    row = list(structured["row"])
    table = structured["table"]
    for _ in range(structured["steps"]):
        padded = [0] + row + [0]
        row = [int(table["%d%d%d" % (padded[i - 1], padded[i], padded[i + 1])])
               for i in range(1, len(padded) - 1)]
    return "".join(str(c) for c in row)


def parse_cellular_automaton(q):
    m = re.match(r"A row of (\d+) cells holds 0s and 1s: ([01]+)\.", q)
    table = dict(re.findall(r"([01]{3}) becomes ([01])", q))
    steps = int(re.search(r"After (\d+) steps?, what does the row look like\?", q).group(1))
    assert "The cells beyond the two ends of the row count as 0." in q
    assert int(m.group(1)) == len(m.group(2))
    return {"row": [int(c) for c in m.group(2)], "table": {k: int(v) for k, v in table.items()},
            "steps": steps, "ask": "row"}


# ---------------------------------------------------------------- cheapest network (MST)
def cheapest_network(question, structured):
    towns = list(structured["towns"])
    parent = {t: t for t in towns}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    total = 0
    used = 0
    for a, b, c in sorted(structured["cables"], key=lambda e: e[2]):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            total += c
            used += 1
    if used != len(towns) - 1:
        raise ValueError("towns cannot all be joined")
    return str(total)


def parse_cheapest_network(q):
    m = re.match(r"The towns (.+?) must be joined by cables", q)
    head = m.group(1)
    first, last = head.rsplit(" and ", 1)
    towns = first.split(", ") + [last]
    cables = [[a, b, int(c)] for a, b, c in
              re.findall(r"A cable between (\w+) and (\w+) would cost (\d+)\.", q)]
    return {"towns": towns, "cables": cables}


# ---------------------------------------------------------------- count divisible (sum)
def count_divisible(question, structured):
    if structured.get("ask", "sum") != "sum":
        raise ValueError("unknown ask")
    m, t = structured["m"], structured["t"]
    return str(sum(x for x in structured["xs"] if x % m == 0 and x > t))


def parse_count_divisible(q):
    m = re.match(r"What is the sum of the numbers in this list that are divisible by (\d+) "
                 r"and greater than (-?\d+)\?", q)
    xs = [int(t) for t in re.search(r"List: ([-\d, ]+)\.$", q).group(1).split(", ")]
    return {"xs": xs, "m": int(m.group(1)), "t": int(m.group(2)), "ask": "sum"}


# ---------------------------------------------------------------- CRT smallest positive
def crt_smallest(question, structured):
    cong = [(int(r), int(n)) for r, n in structured["congruences"]]
    x, mod = 0, 1
    for r, n in cong:
        r %= n
        g = math.gcd(mod, n)
        if (r - x) % g:
            raise ValueError("no solution")
        # solve x + mod*t == r (mod n)
        n_g = n // g
        t = ((r - x) // g) * pow(mod // g, -1, n_g) % n_g if n_g > 1 else 0
        x = x + mod * t
        mod = mod // g * n
        x %= mod
    if x == 0:
        x = mod  # smallest POSITIVE
    # brute-force confirmation
    assert all(x % n == r % n for r, n in cong)
    return str(x)


def parse_crt_smallest(q):
    pairs = re.findall(r"leaves remainder (\d+) when divided by (\d+)", q)
    assert q.startswith("What is the smallest positive whole number that ")
    return {"congruences": [[int(r), int(n)] for r, n in pairs]}


# ---------------------------------------------------------------- dictionary rank
def dictionary_rank(question, structured):
    letters = sorted(structured["letters"])
    L = structured["length"]
    n = len(letters)

    def count_tail(avail_after):
        # number of arrangements of the remaining L-1-i positions from avail letters
        return math.perm(avail_after[0], avail_after[1])

    if structured["ask"] == "word":
        k = structured["k"]
        total = math.perm(n, L)
        if not 1 <= k <= total:
            raise ValueError("k out of range")
        r = k - 1
        avail = list(letters)
        out = []
        for i in range(L):
            block = math.perm(len(avail) - 1, L - 1 - i)
            j = r // block
            r %= block
            out.append(avail.pop(j))
        return "".join(out)
    if structured["ask"] == "position":
        word = structured["word"]
        assert len(word) == L and len(set(word)) == L
        avail = list(letters)
        r = 0
        for i, ch in enumerate(word):
            j = avail.index(ch)
            r += j * math.perm(len(avail) - 1, L - 1 - i)
            avail.pop(j)
        return str(r + 1)
    raise ValueError("unknown ask")


def dictionary_rank_brute(structured):
    words = ["".join(p) for p in itertools.permutations(sorted(structured["letters"]), structured["length"])]
    if structured["ask"] == "word":
        return words[structured["k"] - 1]
    return str(words.index(structured["word"]) + 1)


def parse_dictionary_rank(q):
    m = re.match(r"Write every word of (\d+) letters that can be made from the letters ([a-z, ]+?) "
                 r"when no letter is used twice", q)
    letters = m.group(2).split(", ")
    m1 = re.search(r"Which word has number (\d+)\?$", q)
    m2 = re.search(r"What is the number of the word ([a-z]+)\?$", q)
    if m1:
        return {"letters": letters, "length": int(m.group(1)), "ask": "word", "k": int(m1.group(1)), "word": None}
    return {"letters": letters, "length": int(m.group(1)), "ask": "position", "k": None, "word": m2.group(1)}


# ---------------------------------------------------------------- expression evaluation
def _tokens(s):
    toks = re.findall(r"\d+|[-+*()]|\S", s)
    for t in toks:
        if not (t.isdigit() or t in "+-*()"):
            raise ValueError("bad token %r" % t)
    return toks


def _eval(text, convention):
    toks = _tokens(text)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = toks[pos[0]]
        pos[0] += 1
        return t

    def atom():
        t = take()
        if t == "(":
            v = seq()
            if take() != ")":
                raise ValueError("missing )")
            return v
        if t == "-":  # unary minus (not expected in these items)
            raise ValueError("unary minus found")
        return int(t)

    def seq():
        # read a flat sequence of operands and operators up to ')' or end
        vals = [atom()]
        ops = []
        while peek() in ("+", "-", "*"):
            ops.append(take())
            vals.append(atom())
        if convention == "left_to_right":
            acc = vals[0]
            for o, v in zip(ops, vals[1:]):
                acc = acc + v if o == "+" else acc - v if o == "-" else acc * v
            return acc
        if convention == "ranked":
            # multiplications first, left to right; then + and - left to right
            terms = [vals[0]]
            addops = []
            for o, v in zip(ops, vals[1:]):
                if o == "*":
                    terms[-1] = terms[-1] * v
                else:
                    addops.append(o)
                    terms.append(v)
            acc = terms[0]
            for o, v in zip(addops, terms[1:]):
                acc = acc + v if o == "+" else acc - v
            return acc
        raise ValueError("unknown convention %r" % convention)

    v = seq()
    if pos[0] != len(toks):
        raise ValueError("trailing tokens")
    return v


def expression_eval(question, structured):
    return str(_eval(structured["text"], structured["convention"]))


def parse_expression_eval(q):
    m = re.match(r"Work out (.+?)(\. Use these rules| by this rule, which is not the usual one)", q)
    conv = "ranked" if m.group(2).startswith(". Use") else "left_to_right"
    return {"text": m.group(1), "convention": conv}


# ---------------------------------------------------------------- from base
def from_base(question, structured):
    b = structured["base"]
    v = 0
    for ch in structured["digits"]:
        d = "0123456789abcdefghijklmnopqrstuvwxyz".index(ch)
        if d >= b:
            raise ValueError("digit out of range")
        v = v * b + d
    return str(v)


def parse_from_base(q):
    m = re.fullmatch(r"What is the base-(\d+) number ([0-9a-z]+) written in decimal\? \(Digits above 9 are "
                     r"lowercase letters: a is ten, b is eleven, and so on\.\)", q)
    return {"digits": m.group(2), "base": int(m.group(1))}


SOLVERS = {
    "R2.binary_search_trace": binary_search_trace,
    "R2.caesar_shift": caesar_shift,
    "R2.cellular_automaton": cellular_automaton,
    "R2.cheapest_network": cheapest_network,
    "R2.count_divisible": count_divisible,
    "R2.crt_smallest": crt_smallest,
    "R2.dictionary_rank": dictionary_rank,
    "R2.expression_eval": expression_eval,
    "R2.from_base": from_base,
}

PARSERS = {
    "R2.binary_search_trace": parse_binary_search_trace,
    "R2.caesar_shift": parse_caesar_shift,
    "R2.cellular_automaton": parse_cellular_automaton,
    "R2.cheapest_network": parse_cheapest_network,
    "R2.count_divisible": parse_count_divisible,
    "R2.crt_smallest": parse_crt_smallest,
    "R2.dictionary_rank": parse_dictionary_rank,
    "R2.expression_eval": parse_expression_eval,
    "R2.from_base": parse_from_base,
}
