# ruff: noqa
"""Audit 4 (R1): which rejection lines fire, how often, per shape (all levels pooled), by line tracing (sys.settrace).
Counts executions of every source line of the builder modules that contains 'raise Retry' or 'continue' (inner rejection loops),
plus the number of builder calls. Throwaway seed base 8100; n items per level.
usage (implementation worktree root): PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> <n>
"""
import linecache, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import gen4

n = int(sys.argv[1])
L = gen4.lineages()
for lid in sorted(L):
    lin = L[lid]
    fn = lin.build.__code__.co_filename
    lines = {i for i, s in enumerate(open(fn).read().splitlines(), 1) if "raise Retry" in s or s.strip().startswith("continue")}
    hits = Counter()
    calls = [0]

    def tr(frame, event, arg):
        if frame.f_code.co_filename != fn:
            return None
        def lt(fr, ev, a):
            if ev == "line" and fr.f_lineno in lines:
                hits[fr.f_lineno] += 1
            return lt
        return lt

    sys.settrace(tr)
    for lv in range(7):
        gen4.items(lin, lv, n, 8100)
    sys.settrace(None)
    if hits:
        print(f"{lid}  ({os.path.basename(fn)}, {7 * n} items)")
        for ln, c in sorted(hits.items()):
            print(f"    line {ln:4d} x{c:6d}  {linecache.getline(fn, ln).strip()[:110]}")
    else:
        print(f"{lid}  no rejection line executed ({7 * n} items)")
