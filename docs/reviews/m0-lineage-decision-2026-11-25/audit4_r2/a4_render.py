# ruff: noqa
"""Audit 4 (R2): print rendered items (one per shape) at L0 and L6. Seeds random.Random(f"a4r2-render|{lid}|{lv}") (throwaway, not registered)."""
import random, sys
from studies.m0.core import build_item
from studies.m0.r2_fix3_set import fix3_set
for lid, lin in fix3_set().items():
    for lv in (0, 6):
        r = random.Random(f"a4r2-render|{lid}|{lv}")
        seen = set()
        for i in range(60):
            it = build_item(lin, lv, r, "A", "x")
            sh = str(it.structured.get("ask", it.structured.get("kind", it.structured.get("convention", it.structured.get("desc", "-")))))
            if sh in seen: continue
            seen.add(sh)
            print(f"== {lid} L{lv} [{sh}] type={it.answer_type}\nQ: {it.question}\nA: {it.answer}\n")
