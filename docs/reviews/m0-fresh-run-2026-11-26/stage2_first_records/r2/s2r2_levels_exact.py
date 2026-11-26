# ruff: noqa
"""M0 stage 2, R2: exact (enumerated, no sampling) level parameters for the lineages whose levels need more than a glance,
written from the builder code as read (file:line in REASONS.md). Standard library only; imports nothing from the repository.
Run: python3 -I <this>"""
from fractions import Fraction as F
from math import perm

def digits(n, b):
    d = 0
    while n:
        n //= b; d += 1
    return d

print("to_base_wide (lineages_r2_rev2.py:139-150): n ~ U{10..500*4^(L+1)}, base uniform on the level's set; division steps = digits of the answer")
for L in range(7):
    bases = (2, 3, 4, 5, 6, 7, 8, 9) if L < 2 else (2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 16)
    hi = 500 * 4 ** (L + 1)
    tot = 0
    for b in bases:
        # sum of digit counts over n in [10, hi], by blocks of equal digit count
        s = 0; d = 1
        lo = 1
        while lo <= hi:
            up = lo * b - 1
            a, z = max(lo, 10), min(up, hi)
            if a <= z:
                s += (z - a + 1) * d
            lo *= b; d += 1
        tot += F(s, hi - 9)
    e = tot / len(bases)
    print(f"  L{L}: n max {hi}, bases {bases}, E[steps] = {float(e):.4f}, E[bit length of n] ~ {hi.bit_length()} max")

print("dictionary_rank (lineages_r2_fix3.py:290-312): _DR_PLAN; list size P(m, length); steps = length positions")
plan = {0: (4, (9, 10, 11)), 1: (4, (9, 10, 11, 12)), 2: (5, (7, 8, 9)), 3: (5, (8, 9, 10)), 4: (6, (8, 9, 10)), 5: (6, (9, 10, 11)), 6: (7, (9, 10, 11))}
for L in range(7):
    ln, ms = plan[L]
    sizes = [perm(m, ln) for m in ms]
    print(f"  L{L}: length {ln}, alphabets {ms}, list sizes {sizes}, mean {sum(sizes)/len(sizes):.1f}, mean alphabet {sum(ms)/len(ms):.2f}")
# total-variation distance between the item distributions of L0 and L1: given m the item law is the same at both levels (same length 4);
# so TV = TV of the m laws = 1/2 * (sum |1/3-1/4| over 9..11 + 1/4) = 1/4
tv01 = F(1, 2) * (3 * abs(F(1, 3) - F(1, 4)) + F(1, 4))
print(f"  L0 vs L1: TV distance of the item laws = {tv01} (L1 differs only by the alphabet law; L2 vs L1: disjoint supports, length 5 vs 4)")

print("from_base (lineages_r2.py:106-112): digits = 3+L+U{0,1,2}; bases (2,3,4,5,8) for L<2, (2,3,4,5,7,8,9,16) from L2")
for L in range(7):
    print(f"  L{L}: digits {{{3+L},{4+L},{5+L}}}, E[digits] = {4+L}")
# share of the L1 law that can coincide with an L0 item: same bases; given (base, ln in {4,5}) the item laws coincide.
print("  L0 vs L1: same base law; ln laws U{3,4,5} vs U{4,5,6}; TV distance = 1/3 (identical conditional law on ln in {4,5})")
