# ruff: noqa
"""Audit 4 of M1: which other-evaluation lineages that share an M1 cluster's algorithm are present (registered candidates) in the R1, R2 and C1 fix-3 maps."""
from studies.m0 import r2_fix3_clusters as r2c
from studies.m0 import lineages_r1_fix3_clusters as r1c
from studies.m0 import lineages_c1_fix3_clusters as c1c

r2 = set(r2c.working_ids())
r1 = {x.id for x in r1c.registered_v3()}
c1 = set(c1c.all_members())
pat = ["crt", "prime_factor", "gcd", "modular_power", "permutation_power", "coin_change", "sort_list", "kth_smallest", "multiples_between", "count_letter", "count_divisible",
       "venn", "euclid", "fast_power", "fib", "loop_sum", "counter_list", "majority", "bubble", "median", "mode", "pigeon", "clock", "time", "percent", "interest", "ratio", "linear", "age", "digit", "tier", "grid", "paint", "perimeter", "series", "recurr", "sequence", "division", "remainder"]
for name, s in (("R1", r1), ("R2", r2), ("C1", c1)):
    print(name, len(s), sorted(i for i in s if any(p in i.lower() for p in pat)))
print("R2 NOT_REGISTERED:", sorted(r2c.excluded()))
print("R2 cluster of crt/gcd/prime/modpow/coin/kth/multiples:", {i: r2c.cluster_of(i) for i in sorted(r2) if any(p in i for p in ("crt", "gcd", "prime_factor", "modular_power", "coin_change", "kth", "sort_list", "multiples", "count_letter"))})
