# ruff: noqa
"""Final R2 audit: distinct phrase inventory (ops, asks) from question texts only, to make sure the text solver covers every phrase.
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this>"""
import random, re
from collections import Counter
from studies.m0.core import build_item
from studies.m0.r2_fix4_set import fix4_set
S = fix4_set()
def items(nm, n=500):
    lin = S["R2." + nm]
    for lv in range(7):
        r = random.Random(f"final-r2-phr|{nm}|{lv}")
        for _ in range(n):
            yield lv, build_item(lin, lv, r, "A", "x")
c = Counter()
for lv, it in items("grid_sum"):
    c[re.sub(r"\d+", "#", it.question.split("?")[0].split(". ")[-1])] += 1
print("grid_sum asks:", c.most_common())
c = Counter()
for lv, it in items("list_ops"):
    m = re.search(r"Do these steps in order: (.*?)\. What", it.question)
    for op in m.group(1).split("; "):
        c[re.sub(r"-?\d+", "#", op)] += 1
print("list_ops ops:", c.most_common())
c = Counter()
for lv, it in items("string_rewrite_nonidentity"):
    m = re.search(r"starts: (.*?)\. What", it.question)
    for op in m.group(1).split("; "):
        c[re.sub(r"'[a-z]*'", "'X'", op)] += 1
print("rewrite ops:", c.most_common())
c = Counter()
for lv, it in items("min_heap_ops"):
    c[re.sub(r"[\d, ]+\.", "#.", it.question.split("add these numbers in order:")[1])] += 1
print("heap tails:", c.most_common())
c = Counter()
for lv, it in items("dictionary_rank", 200):
    q = it.question
    c[(lv, re.sub(r"\b[a-z]\b(, )?", "", q.split(" when ")[0]).replace("  ", " ")[:60], q.split("in that list. ")[1][:28])] += 1
print("dict:", sorted(c.items())[:40])
c = Counter()
for lv, it in items("crt_smallest", 200):
    c[(lv, len(re.findall("remainder", it.question)))] += 1
print("crt k:", sorted(c.items()))
c = Counter()
for lv, it in items("expression_eval", 200):
    c[it.question[:12].split(" ")[0]] += 1
    c["neg-literal" if re.search(r"\(-|^Work out -", it.question) else "noneg"] += 1
    c["div" if "/" in it.question else "nodiv"] += 1
print("expr:", c)
c = Counter()
for lv, it in items("caesar_shift", 200):
    c[("backward" if "backward" in it.question else "forward", "upper" if re.search("'[^']*[A-Z]", it.question) else "lower")] += 1
print("caesar:", c)
c = Counter()
for lv, it in items("cellular_automaton", 100):
    c[re.sub(r"\d+", "#", it.question.split("The cells beyond")[1])] += 1
print("ca:", c)
c = Counter()
for lv, it in items("to_base_wide", 300):
    c[(lv, int(re.search(r"in base (\d+)", it.question).group(1)))] += 1
print("tbw bases:", sorted(c.items()))
c = Counter()
for lv, it in items("from_base", 300):
    c[(lv, int(re.search(r"base-(\d+)", it.question).group(1)))] += 1
print("fb bases:", sorted(c.items()))
