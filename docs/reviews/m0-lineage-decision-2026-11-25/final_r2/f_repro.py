# ruff: noqa
"""Final R2 audit: reproducibility. Per survivor and level, 300 items from random.Random(f"finalr2-repro|{lid}|{level}") via core.build_item,
plus one core.generate_pool call per survivor (part_lineages replaced as in f_capacity.py, size 7 x 200, seed 777), hashed as
sha256 over Item.to_json() lines. Run in two fresh processes with different PYTHONHASHSEED and compare the printed hashes.
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=<h> PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this>"""
import hashlib, os, random
from studies.m0 import core
from studies.m0.r2_fix4_set import fix4_set
SURV = ["binary_search_trace","caesar_shift","cellular_automaton","cheapest_network","count_divisible","crt_smallest","dictionary_rank","digit_root","expression_eval","from_base","grid_sum","interval_scheduling","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]
S = fix4_set()
print("PYTHONHASHSEED", os.environ.get("PYTHONHASHSEED"), "hash('x') =", hash("x"))
allh = hashlib.sha256()
orig = core.part_lineages
for nm in SURV:
    lid = "R2." + nm
    lin = S[lid]
    h = hashlib.sha256()
    for lv in range(7):
        r = random.Random(f"finalr2-repro|{lid}|{lv}")
        for i in range(300):
            h.update(core.build_item(lin, lv, r, "A", f"{lid}/{lv}/{i}").to_json().encode()); h.update(b"\n")
    core.part_lineages = lambda e, p, seed=400004, _l=lin: [_l]
    try:
        pool = core.generate_pool("R2", "A", "repro", 777, 1400, {lv: 1.0 for lv in range(7)}, set())
    finally:
        core.part_lineages = orig
    ph = core.pool_hash(pool)
    print(f"{lid} items {h.hexdigest()} pool {ph}")
    allh.update(h.hexdigest().encode() + ph.encode())
print("ALL", allh.hexdigest())
