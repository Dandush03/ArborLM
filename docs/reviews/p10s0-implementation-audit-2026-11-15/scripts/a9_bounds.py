"""One-sided 95% Clopper-Pearson lower bounds (auditor's own bisection on the binomial tail) vs ADR 6.3 and studies.p10s0.classes.per_draw_bound."""
import json, math, sys
from math import comb
def tail_ge(k, n, p): return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))
def lower(k, n, a=0.05):
    if k == 0: return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if tail_ge(k, n, mid) < a else (lo, mid)
    return lo
cases = {"10/10": (10, 10, 0.741), "9/10": (9, 10, 0.606), "9/9": (9, 9, 0.717), "8/9": (8, 9, 0.571), "8/10": (8, 10, 0.493), "3/3": (3, 3, 0.368), "16/18": (16, 18, 0.690), "12/14": (12, 14, 0.615), "18/18": (18, 18, 0.847), "17/18": (17, 18, 0.762), "14/14": (14, 14, 0.807), "13/14": (13, 14, 0.703)}
sys.path.insert(0, sys.argv[1])
from studies.p10s0 import classes as C
out = {k: {"auditor": round(lower(a, b), 4), "adr": v, "impl": round(C.per_draw_bound(a, b), 4), "adr_matches_3dp": round(lower(a, b), 3) == v} for k, (a, b, v) in cases.items()}
print(json.dumps(out, indent=1))
