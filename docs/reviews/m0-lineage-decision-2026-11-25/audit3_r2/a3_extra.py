# ruff: noqa
"""Audit 3 (R2): second-pass heuristics (added after reading attempt 1 of a3_shortcuts; attempt 1 is kept).
Seeds: test draw random.Random(f"a3r2|{lid}|{lv}|6") (the same test draw as a3_shortcuts). N per level from argv."""
import random
import sys

from studies.m0.core import ALL_LEVELS, build_item
from a3_set import current
import a3_solvers as S

N = int(sys.argv[1])


def spf_common(a, b):
    p = 2
    while p <= min(a, b):
        if a % p == 0 and b % p == 0:
            return p
        p += 1
    return None


def ltr_old(text):
    toks = S._tok(text)
    def ev(i, top):
        vals = []
        while i < len(toks) and toks[i] != ")":
            t = toks[i]
            if t == "(":
                v, i = ev(i + 1, False)
                vals.append(v)
            else:
                vals.append(t)
            i += 1
        # evaluate the flat token list: ints and operator strings
        def num(x):
            return x if isinstance(x, int) else int(x)
        seq = [num(x) if (isinstance(x, int) or x.isdigit()) else x for x in vals]
        if top:
            v = seq[0]
            for k in range(1, len(seq), 2):
                op, w = seq[k], seq[k + 1]
                v = v + w if op == "+" else v - w if op == "-" else v * w
            return v, i
        # usual precedence inside
        terms, ops, cur = [], [], seq[0]
        for k in range(1, len(seq), 2):
            op, w = seq[k], seq[k + 1]
            if op == "*":
                cur *= w
            else:
                terms.append(cur); ops.append(op); cur = w
        terms.append(cur)
        v = terms[0]
        for op, w in zip(ops, terms[1:]):
            v = v + w if op == "+" else v - w
        return v, i
    return ev(0, True)[0]


TESTS = {
    "R2.gcd_euclid": [("gcd: smallest common prime factor (trial division from 2)", lambda s: str(spf_common(s["a"], s["b"])) if s["ask"] == "gcd" else None),
                      ("gcd shape: share of items whose gcd is prime", lambda s: ("prime" if s["ask"] == "gcd" and all(int(S.gcd_euclid(s, ""))% d for d in range(2, int(int(S.gcd_euclid(s, ""))**0.5)+1)) else "x") if s["ask"] == "gcd" else None)],
    "R2.list_ops": [("ignore reverses (items with a reverse only)", lambda s: S.list_ops({"xs": s["xs"], "ops": [o for o in s["ops"] if o[0] != "reverse"]}, "") if any(o[0] == "reverse" for o in s["ops"]) else None),
                    ("ignore moves to the end (items with one only)", lambda s: S.list_ops({"xs": s["xs"], "ops": [o for o in s["ops"] if o[0] != "first_to_end"]}, "") if any(o[0] == "first_to_end" for o in s["ops"]) else None)],
    "R2.expression_eval": [("LTR: usual precedence inside parentheses only (old ambiguity), fixed", lambda s: str(ltr_old(s["text"])) if s["convention"] == "left_to_right" else None)],
    "R2.permutation_power": [("start is a fixed point -> start (coverage)", lambda s: str(s["s"]) if s["img"][s["s"] - 1] == s["s"] else None),
                             ("start or one application, whichever is in a 2-cycle parity: t odd -> img[s], t even -> s", lambda s: str(s["img"][s["s"] - 1]) if s["t"] % 2 else str(s["s"]))],
    "R2.stack_machine": [("last pushed value", lambda s: str([p[1] for p in s["prog"] if p[0] == "push"][-1]))],
}


def main():
    cur = current()
    for lid, tests in TESTS.items():
        lin = cur[lid]
        for name, fn in tests:
            cells = []
            for lv in ALL_LEVELS:
                r = random.Random(f"a3r2|{lid}|{lv}|6")
                n = k = 0
                for _ in range(N):
                    it = build_item(lin, lv, r, "A", "e")
                    a = fn(it.structured)
                    if a is None:
                        continue
                    n += 1
                    if name.startswith("gcd shape: share"):
                        k += a == "prime"
                    else:
                        k += a == it.answer
                cells.append(f"{k / n:.2f}(n={n})" if n else "-")
            print(f"{lid} | {name} | " + " ".join(cells), flush=True)


main()
