# ruff: noqa
"""Final R2 audit: one example per question shape (structured 'ask'/'convention'/'kind' etc.) per lineage, levels 0..6; and the structured keys.
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this>"""
import random, re
from collections import Counter
from studies.m0.core import build_item
from studies.m0.r2_fix4_set import fix4_set

SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]
S = fix4_set()
for nm in SURV:
    lin = S["R2." + nm]
    seen = {}
    cnt = Counter()
    keys = set()
    for lv in range(7):
        r = random.Random(f"final-r2-shapes|{nm}|{lv}")
        for i in range(400):
            it = build_item(lin, lv, r, "A", "x")
            keys |= set(it.structured)
            tpl = re.sub(r"\d+", "#", it.question)
            tpl = re.sub(r"'[a-z ]*'", "'W'", tpl)
            tpl = re.sub(r"(# ?[,/] ?)+#", "#..", tpl)
            # coarse template: sentence skeleton without names/lists
            sk = re.sub(r"\b[A-Z][a-z]+\b", "N", tpl)
            sk = re.sub(r"[a-z]{6,}", "w", sk) if nm in ("run_length",) else sk
            key = (sk[-160:], it.answer_type)
            cnt[key] += 1
            if key not in seen:
                seen[key] = (lv, it.question, it.answer)
    print(f"##### {nm}: structured keys {sorted(keys)}; {len(seen)} coarse templates")
    for key, (lv, q, a) in list(seen.items())[:12]:
        print(f"  [{cnt[key]} items, first at L{lv}, type {key[1]}] ...{q[-260:]!r} -> {a!r}")
