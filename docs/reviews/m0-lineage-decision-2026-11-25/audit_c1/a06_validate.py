# ruff: noqa
"""Validate a06_feats.facts(tree) against an ast reading of the question source (the way the author's script reads it),
on all 3,500 fixture items. Parse only; nothing executed."""
import ast
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a02_myeval import source_of_question
from a06_feats import facts


def ast_facts(src):
    tree = ast.parse(src)
    nodes = sorted((n for n in ast.walk(tree) if hasattr(n, "lineno")), key=lambda n: (n.lineno, n.col_offset))
    nums, strs, lists = [], [], []
    for n in nodes:
        if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
            nums.append(n.value)
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant) and isinstance(n.operand.value, int):
            nums.append(-n.operand.value)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            strs.append(n.value)
        if isinstance(n, ast.List):
            try:
                lists.append(ast.literal_eval(n))
            except (ValueError, TypeError):
                pass
    return nums, strs, lists


bad = 0
n = 0
for f in sorted(glob.glob("studies/m0/fixtures/c1_batch1/*.jsonl")):
    for line in open(f):
        it = json.loads(line)
        n += 1
        a = ast_facts(source_of_question(it["question"]))
        b = facts(it["structured"]["program"])
        if a != (b["nums"], b["strs"], b["lists"]):
            bad += 1
            if bad <= 5:
                print(it["id"], a, (b["nums"], b["strs"], b["lists"]))
print("checked", n, "mismatches", bad)
