"""Arithmetic re-check of ADR-0022 rev4 (post-E8). Pure stdlib. No project imports."""
from math import sqrt

print("== Task 2: registry ==")
cells = {  # group: (cells, store_units, lora_units)
    "ST1": (2, 2, 0), "M-append-frozen": (2, 2, 0), "M-ii": (2, 4, 0), "M-seq": (2, 2, 0),
    "M-joint": (1, 2, 0), "E-table": (2, 2, 0), "MA-gold": (2, 2, 0),
    "LoRA-1+L-seq": (4, 0, 4), "L-joint": (1, 0, 2),
}
c = sum(v[0] for v in cells.values()); su = sum(v[1] for v in cells.values()); lu = sum(v[2] for v in cells.values())
print("cells/rep", c, "store units", su, "LoRA units", lu, "x4", 4 * c, "x3", 3 * c)
mem = ["ST1", "M-append-frozen", "M-ii", "M-seq", "M-joint", "MA-gold"]
print("memory cells for ablations", sum(cells[k][0] for k in mem))

print("== Task 2: hours per rung (from 13.3 per-unit ranges) ==")
def R(n, U, end):
    store = (5, 10)[end] * su / 60 * U / 2000
    lora = (8, 15)[end] * lu / 60 * U / 2000
    score = (1.6, 5.2)[end] * c / 60
    other = (0.9, 3.0)[end]
    fixed = (0.3, 0.6)[end]
    return n * (store + lora + score + other) + fixed
for i, (n, U) in enumerate([(4, 2000), (3, 2000), (4, 1000), (3, 1000)], 1):
    lo, hi = R(n, U, 0), R(n, U, 1)
    print(f"rung {i} n={n} U={U}: {lo:.3f}-{hi:.3f} h; P+2R at P=3.5: {3.5+2*lo:.2f}-{3.5+2*hi:.2f}; at P=7: {7+2*lo:.2f}-{7+2*hi:.2f}")
for P in (3.5, 7.0):
    print(f"P={P}: max R = {(36-P)/2:.2f} h")
# per-replicate change from rev3 (18 store+4 LoRA, 19 cells) to rev4 (16+6, 18 cells)
for end in (0, 1):
    d = ((5, 10)[end] * (16 - 18) + (8, 15)[end] * (6 - 4) + (1.6, 5.2)[end] * (18 - 19)) / 60
    print("per-replicate change rev3->rev4 (end", end, ")", round(d, 3), "h")

print("== Section 9 probabilities ==")
print(0.5**4, 0.5**3, 0.8**4, 0.8**3)

print("== Wilson 95% at p=0.90 ==")
def wilson(p, n, z=1.959964):
    d = 1 + z*z/n; centre = (p + z*z/(2*n)) / d; half = z*sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return centre - half, centre + half
for n in (150, 300, 500):
    print(n, [round(x, 4) for x in wilson(0.9, n)])
# point estimate needed on Q_fit so that Wilson LB >= 0.90
for n in (150, 250, 300, 400, 500):
    k = next(k for k in range(n + 1) if wilson(k / n, n)[0] >= 0.90)
    print(f"Wilson LB>=0.90 needs >= {k}/{n} = {k/n:.3f}")

print("== Parameters ==")
N, kw, d = 4096, 16, 576
print("per stage", N * (kw + d) + 1)
lora_per_rank = 30 * ((576 + 576) + (576 + 192))
print("LoRA per rank", lora_per_rank, "r42", 42 * lora_per_rank, "r84", 84 * lora_per_rank)
st = N * (kw + d) + 1
print("r42 vs stage", (42 * lora_per_rank / st - 1) * 100, "%; r84 vs M-joint (2N rows, one gate)", (84 * lora_per_rank / (2 * N * (kw + d) + 1) - 1) * 100, "%")
student = 134_515_008; teachers = 73_944_309 + 74_669_178
store2 = 2 * N * (kw + d) + 2
print("student+2N store (2 gates)", student + store2, "teachers", teachers, "ratio", round((student + store2) / teachers, 4))

print("== Downloads (MB) ==")
tA, tB, stu = 300.8, 303.7, 272.4
tat = (24_947_715 + 12_144_786 + 9_805_546 + 3_557_634 + 2_679_128) / 1e6
spa = (6_376_323 + 1_762_602) / 1e6
sym = (3_552_331 + 2_678_076) / 1e6
print("tatoeba", round(tat, 2), "spa", round(spa, 2), "symmetry files", round(sym, 2))
print("primary", round(tA + tB + stu + tat, 1), "+spa", round(tA + tB + stu + tat + spa, 1),
      "+fallback teacher", round(tA + tB + stu + tat + spa + 315.3, 1),
      "+symmetry files", round(tA + tB + stu + tat + spa + sym, 1), round(tA + tB + stu + tat + spa + 315.3 + sym, 1))

print("== Seeds ==")
own = {}
for b in (220001, 220101, 220201, 220301):
    for k, name in enumerate(["init", "draw", "batch", "router", "perm", "gold"]):
        own[b + k] = f"rep{b} {name}"
own[220901] = "partition"
ranges = {"calibration": (221001, 221999), "rehearsal": (222001, 222999), "tests": (229001, 229999)}
def which(s):
    hits = [n for n, (a, z) in ranges.items() if a <= s <= z]
    if s in own: hits.append(own[s])
    return hits
print("declared singletons in a range:", [s for s in own if which(s) != [own[s]]])
print("P9 ScalableMemory convention seed+1000..5000 (keys, values, wq, wo, router):")
for s in sorted(own):
    hits = {off: which(s + off) for off in (1000, 2000, 3000, 4000, 5000)}
    hits = {k: v for k, v in hits.items() if v}
    if hits: print(" ", s, own[s], "->", hits)
print(" calibration 221001+1000 ->", which(222001), "; rehearsal 222001+1000 ->", which(223001))
print("P7-B/P8/P9-sim convention seed*1000+index: 220001*1000 =", 220001 * 1000, "(outside every listed namespace)")
sib = {"S0": [(200001, 209999), (2001, 2002), (2091, 2092), (920001, 920999)],
       "S1": [(210001, 219999), (2101, 2105), (2111, 2112), (2121, 2122), (2191, 2192), (921001, 921999)],
       "P9-II": [(190001, 191599), (1891, 1892), (1901, 1902), (910001, 919999)],
       "P9-I": [(182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233)],
       "P9": [(170001, 171343), (179001, 179933), (1701, 1702)]}
s2 = (220001, 229999)
print("S2 namespace overlaps:", [(k, r) for k, rs in sib.items() for r in rs if not (r[1] < s2[0] or r[0] > s2[1])])
# siblings' derived seeds (init + 1000k, k up to 9) into S2
print("sibling init+1000k (k<=9) landing in S2:", [(k, i, i + 1000 * m) for k, rs in sib.items() for r in rs if r[1] < 10000
       for i in range(r[0], r[1] + 1) for m in range(1, 10) if s2[0] <= i + 1000 * m <= s2[1]])
