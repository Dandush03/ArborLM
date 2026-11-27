"""capacity.RealSource against my loader (the pair audit's gen_fresh.py loading): same lineage objects and the same
second-solver functions (by module file and function name) for all 67 candidates. No draw."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import candidates, load_lineages, load_solvers
from studies.m0.registration import capacity as cap
src = cap.RealSource(); mine_l = load_lineages(); mine_s = load_solvers()
bad = []
for e, ids in candidates().items():
    for x in ids:
        a, b = src.lineage(x), mine_l[x]
        if (a.id, a.eval, a.family, a.build.__module__, a.build.__qualname__) != (b.id, b.eval, b.family, b.build.__module__, b.build.__qualname__) or a.build is not b.build:
            bad.append(("lineage", x))
        sa, sb = src.solver(x), mine_s[x]
        if (sa.__code__.co_filename, sa.__qualname__, sa.__code__.co_code) != (sb.__code__.co_filename, sb.__qualname__, sb.__code__.co_code):
            bad.append(("solver", x))
print("candidates checked:", sum(len(v) for v in candidates().values()), "differences:", bad)
