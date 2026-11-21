# ruff: noqa
"""Randomised check of recompute.py's efficiency step verdict (ADR-0021 8.8 rows 1-8, one cost reading) against the study's frozen classes.efficiency_step,
on synthetic u_T values (known, left- and right-censored, DEP flags), because the rehearsal and the fuzz runs never reached FASTER STEP.
Usage: PYTHONPATH=frozen:frozen/src python -B compare_eff_verdict.py"""

import math
import random
import sys
from collections import Counter

sys.path.insert(0, ".")
import recompute as R  # noqa: E402
from studies.p10s1 import classes as c1  # noqa: E402

rng = random.Random(7)


class FakeArgs:
    pass


rc = object.__new__(R.Recompute)
rc.th = {"efficiency_updates_factor": 0.5, "efficiency_cost_factor": 0.8}
diff, tally = 0, Counter()
for k in range(20000):
    run_s, run_l = rng.choice([49152, 98304]), rng.choice([49152, 98304])
    def ut(run):
        kind = rng.choice(["known", "known", "left", "right"])
        dep = rng.random() < 0.05
        if dep:
            return ("right", float(run), math.inf, None, None, True)
        if kind == "known":
            v = 2 ** rng.uniform(9, math.log2(run))
            return ("known", v, v, None, None, False)
        if kind == "left":
            return ("left", 0.0, float(rng.choice([512, 1024, 2048])), None, None, False)
        return ("right", float(run), math.inf, None, None, False)
    us, ul = ut(run_s), ut(run_l)
    cs, cl = rng.uniform(1, 3), rng.uniform(1, 3)
    refok, leak = rng.random() > 0.03, rng.random() < 0.03
    mine = R.Recompute.eff_verdict(rc, us, ul, run_s, run_l, cs, cl, refok, leak)
    to = lambda u: c1.UTResult(c1.UT({"known": "exact"}.get(u[0], u[0]), u[1], u[2]), u[5], None, None)  # noqa: E731
    st = c1.efficiency_step(to(us), to(ul), ref_ok=refok, leakage=leak, run_small=run_s, run_large=run_l, cost_small={"cpu": cs, "madds": cs}, cost_large={"cpu": cl, "madds": cl}).verdict
    tally[mine] += 1
    if mine != st:
        diff += 1
        if diff <= 10:
            print("DIFF", us[:3], ul[:3], run_s, run_l, round(cs, 3), round(cl, 3), refok, leak, "| mine", mine, "| study", st)
print("cases 20000; differences", diff, dict(tally))
