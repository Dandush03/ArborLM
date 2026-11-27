# ruff: noqa
"""Audit 4 (R2): final classification and distribution of the shortcut measurements in a4_shortcuts_2000.json.
Every rule is put in ONE class (my classification; the table below is the whole of it):
  P         valid alternative procedure, or a full solve under a misreading of a stated convention (names containing '(P' from any battery, plus the list MISREAD)
  artifact  coincides with the procedure on a subset of items (coverage), e.g. 'ignore X' on items without X; replaced by my [cond] versions
  partial   a truncated version of the procedure (checks a subset of what the procedure checks), e.g. 'outer k letter pairs'
  construct a fixed reduction that is valid only because of a construction regularity (permutation cycle length)
  cue       everything else (cheap rules wrong in general, including 'most frequent answer')
Effect: open answers = accuracy over all items of the shape (a rule's None = wrong), except [cond] rules (accuracy where they apply); yes/no = |acc - 0.5| among items where it applies.
Usage: python3 -I a4_summ2.py a4_shortcuts_2000.json"""
import json
import sys

d = json.load(open(sys.argv[1]))

MISREAD = [
    "[a3] digits read right to left", "[a3] k-th largest", "[a3] syndrome read with the bits reversed", "[a3] doubling the other parity",
    "[a3] check digit: payload total without the new digit", "[mine] check digit: payload's own last digit not doubled",
    "[a3] first occurrence only per rule", "[a3] largest: largest prime <= sqrt(n) dividing n", "[a3] (b-a)//m + 1",
    "[mine] latest start first", "[mine] Floyd bottom-up heapify", "[mine] inverse mapping t times",
]
PARTIAL = [
    "letter pairs", "[a3] outer two letters each side match", "[a3] first letter equals last letter",
    "centres only", "[a3] longest odd palindrome only", "[a3] longest even palindrome only", "longest palindrome of length <= 7",
    "scanning only primes up to 61", "first failing check", "plain digit sum",
    "count of piles that are a win alone is odd", "odd number of piles that are first-player wins alone", "[cond] ignore",
]
CONSTRUCT = ["t mod (n-1) applications", "t mod 10 applications"]


def klass(hn, sh, lv):
    if "(P" in hn:
        return "P"
    if hn in ("[a3] ignore reverses", "[a3] ignore moves to the end"):
        return "artifact"
    if hn == "[a3] removal by deleting the minimum and keeping the order of the rest" and sh == "removals=0":
        return "artifact"
    if hn in ("[a3] only the first rule", "[a3] only the last rule, on the start string", "[a3] rules in reverse order") and lv == 0:
        return "artifact"
    if hn == "[a3] rules in reverse order" or hn == "[mine] [cond] rules in reverse order" or hn == "[mine] [cond] all rules applied to the start string at once (left to right, first matching rule)":
        return "P"
    if any(hn.startswith(m) for m in MISREAD):
        return "P"
    if any(p in hn for p in PARTIAL):
        return "partial"
    if any(c in hn for c in CONSTRUCT):
        return "construct"
    return "cue"


def eff(hn, v, at):
    if at == "yn":
        return v["effect"]
    return v["acc_app"] if "[cond]" in hn else v["acc_all"]


CLASSES = ("cue", "partial", "construct")
table = {}
for lid, lv_rows in sorted(d["lineages"].items()):
    t = {c: [(0.0, "", "")] * 7 for c in CLASSES + ("P", "artifact")}
    for lv, rows in lv_rows.items():
        L = int(lv)
        for sh, ent in rows.items():
            for hn, v in ent["rules"].items():
                c = klass(hn, sh, L)
                e = eff(hn, v, ent["answer_type"])
                if e > t[c][L][0]:
                    t[c][L] = (e, hn, sh)
    table[lid] = t


def dist(classes):
    bins = {"<=0.10": [], "(0.10,0.15]": [], "(0.15,0.25]": [], ">0.25": []}
    for lid, t in table.items():
        mx = max(t[c][L][0] for c in classes for L in range(7))
        k = "<=0.10" if mx <= 0.10 else "(0.10,0.15]" if mx <= 0.15 else "(0.15,0.25]" if mx <= 0.25 else ">0.25"
        bins[k].append((lid.split(".")[1], round(mx, 2)))
    return bins


for lid, t in table.items():
    print(f"== {lid}")
    for c in ("cue", "partial", "construct", "P", "artifact"):
        vals = [x[0] for x in t[c]]
        if max(vals) == 0:
            continue
        top = max(t[c], key=lambda x: x[0])
        print(f"   {c:9s} L0..L6: " + " ".join(f"{x:.2f}" for x in vals) + f"   top: {top[1]} [{top[2]}]")

for name, cls in (("cues only", ("cue",)), ("cues + partial", ("cue", "partial")), ("cues + partial + construct", ("cue", "partial", "construct"))):
    b = dist(cls)
    print(f"\nDISTRIBUTION ({name}; per lineage, max over levels and shapes):")
    for k, v in b.items():
        print(f"  {k}: {len(v)}  {sorted(v, key=lambda x: -x[1])}")
