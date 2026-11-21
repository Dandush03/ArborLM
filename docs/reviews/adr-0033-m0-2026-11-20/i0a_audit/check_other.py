# ruff: noqa
# ruff: noqa
"""M0-I0a audit: independent re-derivation FROM THE QUESTION TEXT for R2 (to_base, permutation_power,
string_rewrite), M1 (linear_equation, percent_change, clock_duration) and C1 (func_compose, bubble_pass,
string_methods: each program run in its own fresh `python3 -I` subprocess, 5 s timeout, after a
refusal scan). Usage: python3 -I check_other.py FILE.jsonl [LINEAGE ...]
"""
import json, re, subprocess, sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction

DIG = "0123456789abcdef"


def to_base(q):
    n, b = map(int, re.search(r"decimal number (\d+) in base (\d+)", q).groups())
    s = ""
    while n: s = DIG[n % b] + s; n //= b
    return s or "0"


def perm(q):
    pairs = dict((int(a), int(b)) for a, b in re.findall(r"(\d+) goes to (\d+)", q))
    st, k = map(int, re.search(r"Start at (\d+) and apply the mapping (\d+) times", q).groups())
    for _ in range(k): st = pairs[st]
    return str(st)


def rewrite(q):
    s = re.search(r"Start with the string (\w+)\.", q).group(1)
    steps = q.split("starts: ")[1].split(". What is")[0].split("; ")
    for st in steps:
        if m := re.fullmatch(r"replace every '(\w+)' with '(\w+)'", st): s = s.replace(m[1], m[2])
        elif m := re.fullmatch(r"delete every '(\w+)'", st): s = s.replace(m[1], "")
        else: raise ValueError(st)
    return s


def lin(q):
    def side(t):
        m = re.fullmatch(r"[Mm]ultiplying it by (\d+) and then (adding|subtracting) (\d+)", t.strip())
        return int(m[1]), (int(m[3]) if m[2] == "adding" else -int(m[3]))
    body = q.split("I think of a number. ")[1].split(". What is my number")[0]
    if " gives the same result as " in body:
        l, r = body.split(" gives the same result as ")
        (a, b), (c, d) = side(l), side(r)
        x = Fraction(d - b, a - c)
    else:
        l, r = body.split(" gives ")
        a, b = side(l); x = Fraction(int(r) - b, a)
    return str(x) if x.denominator == 1 else f"NONINTEGER {x}"


def pct(q):
    p = Fraction(int(re.search(r"costs (\d+) dollars", q).group(1)))
    for d, v in re.findall(r"(rises|falls) by (\d+) percent", q):
        p *= Fraction(100 + int(v) if d == "rises" else 100 - int(v), 100)
    dec = Decimal(p.numerator) / Decimal(p.denominator)
    return dec, p


def clock(q):
    tot = 0
    for a, b, c, d in re.findall(r"leaves at (\d\d):(\d\d) and arrives at (\d\d):(\d\d)", q):
        tot += (int(c) * 60 + int(d)) - (int(a) * 60 + int(b))
    return str(tot)


BAN = re.compile(r"\bimport\b|open\(|__|\beval\b|\bexec\b|\binput\b|\bglobals\b|\bgetattr\b")


def run_c1(q):
    prog = q.split("Here is a Python program.\n\n")[1].split("\n\nWhat exactly does it print?")[0]
    if BAN.search(prog): return "REFUSED"
    p = subprocess.run([sys.executable, "-I", "-c", prog], capture_output=True, text=True, timeout=5)
    out = p.stdout
    if p.returncode or out.count("\n") != 1: return f"BADRUN rc={p.returncode} out={out!r} err={p.stderr[-200:]!r}"
    return out.rstrip("\n")


if __name__ == "__main__":
    want = set(sys.argv[2:])
    st = Counter(); bad = []; extra = Counter()
    for line in open(sys.argv[1]):
        r = json.loads(line); lin_ = r["lineage"]
        if want and lin_ not in want: continue
        q, a = r["question"], str(r["answer"])
        if lin_ == "R2.to_base": got = to_base(q)
        elif lin_ == "R2.permutation_power": got = perm(q)
        elif lin_ == "R2.string_rewrite":
            got = rewrite(q)
            steps = q.split("starts: ")[1].split(". What is")[0].split("; ")
            if any(re.fullmatch(r"replace every '(\w+)' with '\1'", s) for s in steps): extra["string_rewrite items with an identity step"] += 1
        elif lin_ == "M1.linear_equation": got = lin(q)
        elif lin_ == "M1.percent_change":
            dec, fr = pct(q)
            got = a if Decimal(a) == dec else f"{dec} (exact {fr})"
            if fr.denominator > 100 and (fr * 100).denominator != 1: extra["percent items whose exact answer needs >2 decimals"] += 1
        elif lin_ == "M1.clock_duration": got = clock(q)
        elif lin_.startswith("C1."): got = run_c1(q)
        else: continue
        ok = got == a
        st[(lin_, "agree" if ok else "DISAGREE")] += 1
        if not ok: bad.append((r["id"], a, got))
    for k in sorted(st): print(k, st[k])
    for k in sorted(extra): print(k, extra[k])
    for b in bad[:10]: print("BAD", b)
