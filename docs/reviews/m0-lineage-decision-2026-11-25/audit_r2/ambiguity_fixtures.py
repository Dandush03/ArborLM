# ruff: noqa
"""List fixture items whose key changes under a plausible alternative reading of the wording.
  expression_eval ranked: '+' before '-' ("operators of the same kind" read as same symbol) and '-' before '+'.
  expression_eval left_to_right: usual precedence INSIDE parentheses, left to right only at the levels outside.
  merge_smallest_cost: only neighbouring piles may be joined.
Pure stdlib, reads fixtures only."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heuristics import eval_prec, eval_ltr, _adjacent_opt

FIX = sys.argv[1]


def eval_ranked_minus_first(text):
    # additive level: all subtractions bind first (a - b + c -> a - (b + c) is plus-first; minus-first gives (a - b) + c = usual)
    # so minus-first equals the usual left-to-right reading whenever '-' precedes '+'; it differs for 'a + b - c'? no: (a+b)-c = a+(b-c).
    return eval_prec(text)


def eval_ltr_prec_inside(text):
    # top level left to right, but every parenthesised group evaluated with the usual precedence
    toks = re.findall(r"\d+|[()+\-*]", text)
    pos = 0

    def group_text():
        nonlocal pos
        depth, start = 1, pos
        while depth:
            if toks[pos] == "(":
                depth += 1
            elif toks[pos] == ")":
                depth -= 1
            pos += 1
        return " ".join(toks[start:pos - 1])

    def atom():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == "(":
            return eval_prec(group_text())
        return int(t)

    v = atom()
    while pos < len(toks):
        op = toks[pos]; pos += 1
        w = atom()
        v = v + w if op == "+" else v - w if op == "-" else v * w
    return v


rows = [json.loads(l) for l in open(os.path.join(FIX, "R2.expression_eval.jsonl"))]
plus_first, prec_inside = [], []
n_r = n_l = 0
for it in rows:
    text, conv = it["structured"]["text"], it["structured"]["convention"]
    if conv == "ranked":
        n_r += 1
        if str(eval_prec(text, plus_first=True)) != it["answer"]:
            plus_first.append(it["id"])
    else:
        n_l += 1
        if str(eval_ltr_prec_inside(text)) != it["answer"]:
            prec_inside.append(it["id"])
print(f"expression_eval ranked items={n_r}; key changes if '+' is done before '-': {len(plus_first)}")
print("  ids:", plus_first)
print(f"expression_eval left_to_right items={n_l}; key changes if precedence is used inside parentheses: {len(prec_inside)}")
print("  ids:", prec_inside)

rows = [json.loads(l) for l in open(os.path.join(FIX, "R2.merge_smallest_cost.jsonl"))]
adj = [it["id"] for it in rows if str(_adjacent_opt(it["structured"]["ws"])) != it["answer"]]
print(f"merge_smallest_cost items={len(rows)}; key changes if only neighbouring piles may be joined: {len(adj)}")
print("  ids:", adj)
