# ruff: noqa
"""Print item texts (question, options, key) for reading; usage: python samples.py <seed_base> <per_level> <levels csv> [id substr]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgen
sb, n, lvs = int(sys.argv[1]), int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
flt = sys.argv[4] if len(sys.argv) > 4 else ""
for lid, lin in sorted(fgen.lineages().items()):
    if flt not in lid: continue
    for lv in lvs:
        for b in fgen.items(lin, lv, n, sb):
            print(f"===== {lid} L{lv} k={b.k}")
            print(b.question)
            print("OPTIONS:", getattr(b, "options", None))
            print("KEY:", repr(b.answer))
