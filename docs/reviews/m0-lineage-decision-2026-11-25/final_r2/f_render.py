# ruff: noqa
"""Final R2 audit: render sample items (question text, answer) of the 19 fix-4 survivors, to write the text-only solver from.
Usage (cwd = audited worktree): PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this> N LEVELS [names]"""
import random, sys
from studies.m0.core import build_item
from studies.m0.r2_fix4_set import fix4_set

SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]
n = int(sys.argv[1]); levels = [int(x) for x in sys.argv[2].split(",")]
names = sys.argv[3].split(",") if len(sys.argv) > 3 else SURV
S = fix4_set()
for nm in names:
    lin = S["R2." + nm]
    for lv in levels:
        r = random.Random(f"final-r2-render|{nm}|{lv}")
        for i in range(n):
            it = build_item(lin, lv, r, "A", "x")
            print(f"=== {nm} L{lv} #{i} type={it.answer_type} k={it.k}")
            print(it.question)
            print(f"--> ANSWER: {it.answer!r}")
