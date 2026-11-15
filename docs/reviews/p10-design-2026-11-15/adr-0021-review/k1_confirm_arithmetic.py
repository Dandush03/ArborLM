"""K1: arithmetic for the confirmation of ADR-0021 rev 2 (stdlib only)."""
from math import log2


def fano(a):
    e = 1 - a
    h = 0.0 if e in (0, 1) else -(e * log2(e) + (1 - e) * log2(1 - e))
    return 5 - h - e * log2(31)


def inv(target):
    lo, hi = 1 / 32, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fano(mid) < target else (lo, mid)
    return hi


for t in (3.0, 4.0, 4.5, 5 / 1.1):
    print(f"i = {t:.3f} bits <-> a_use = {inv(t):.4f}")
print("CAPACITY reachable with a loaded smaller cell: smaller i* <= 4.0, slope <= 0.10 -> larger needs i >= 4.0 + 0.5 + 2*0.10 = 4.70 (a_use", f"{inv(4.7):.3f}) < 5")
print("Study B: a_use 0.85 at the top with ceiling below gives ratio", round(4 * fano(0.85) / 5, 3))
# budget, rev 2 section 10.3
before, train, seed1, seed2, ev, fixed = 1.4, 21.4 / 6, 2.0 / 6, 2.0 / 6, 1.0, 0.4
rem1 = train + seed1 + ev + fixed
print(f"remaining (draw-1 block) {rem1:.2f} h; charged + 2x = {before + 2*rem1:.2f} h")
print(f"slack in measured remaining time before the 12 h rule fails: {(12 - before) / 2 - rem1:+.2f} h")
for name, extra_cpu in (("T-OQ at 2.5x F-OQ instead of 2x", 5 * 0.25 * 7060 / 3600), ("evaluation +20%", 0.2 * 6.0)):
    print(f"  {name}: +{extra_cpu/6 if 'T-OQ' in name else extra_cpu/6:.2f} h remaining -> 2x adds {2*(extra_cpu/6):.2f} h")
d_oq_cut = 5 * (0.0487 * 2 * 8192 + 0.0143 * 4 * 8192) / 3600 / 6
seed_cut = 2.0 / 6
print(f"cut D-OQ 8K/64K + 32K/16K saves {d_oq_cut:.2f} h remaining ({2*d_oq_cut:.2f} under 2x); cutting the draw-1 seed block saves {seed_cut:.2f} ({2*seed_cut:.2f})")
