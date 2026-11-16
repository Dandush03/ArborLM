"""C2: pure arithmetic checks of ADR-0021 rev 1 (no model, no data). Python stdlib only."""
import math
from math import comb, log2


def h2(e):
    return 0.0 if e in (0.0, 1.0) else -(e * log2(e) + (1 - e) * log2(1 - e))


def fano(a):
    e = 1 - a
    return 5 - h2(e) - e * log2(31)


print("== 1. Fano bits per fact i(a)")
for a in (0.05, 0.10, 0.25, 0.50, 0.80, 0.85, 0.90, 0.95, 0.954, 0.97, 0.99, 1.0):
    print(f"  a_use={a:.3f}  i={fano(a):.3f}")
lo, hi = 0.5, 1.0
for _ in range(60):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if fano(mid) < 4.5 else (lo, mid)
print(f"  i = 4.5 is reached at a_use = {hi:.4f} (draft: 'a_use about 0.95'; i(0.95) = {fano(0.95):.3f} < 4.5)")
print("  accuracy points per 0.5 bits at several levels:")
for a in (0.3, 0.5, 0.7, 0.8, 0.9):
    lo, hi = a, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fano(mid) - fano(a) < 0.5 else (lo, mid)
    print(f"    from a={a:.2f}: +0.5 bit needs a={hi:.3f} (+{hi - a:.3f})")
d = (fano(0.5 + 1e-4) - fano(0.5 - 1e-4)) / 2e-4
print(f"  di/da at a=0.5: {d:.2f} bits per unit accuracy; SE(acc) at F=8192, p=0.5: {math.sqrt(.25/8192):.4f} -> {d*math.sqrt(.25/8192):.3f} bits")
for F in (2048, 8192, 32768):
    print(f"  max SE of accuracy at F={F}: {math.sqrt(0.25 / F):.4f}")

print("\n== 2. Diagonal ratio I_use(4N,4F)/I_use(N,F) = 4 i'/i")
for a_small, a_big in ((1.0, 0.97), (1.0, 0.90), (1.0, 0.86), (1.0, 0.80), (0.999, 0.80)):
    r = 4 * fano(a_big) / fano(a_small)
    print(f"  a {a_small:.3f} -> {a_big:.3f}: ratio {r:.2f}")
print(f"  i(0.80) = {fano(0.80):.3f}: a_use 0.80 at 32K/64K with 8K/16K at ceiling gives ratio {4*fano(0.8)/5:.2f} < 3.0")


print("\n== 3. Replicate probabilities under 'P(pass) <= 1/2 independently per replicate'")
for n in (5, 4, 3):
    for k in range(n, n - 2, -1):
        p = sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n
        print(f"  n={n}: at least {k} of {n}: {p:.4f}")
print("  if the per-replicate pass probability under the null is q, P(all 5) = q^5:")
for q in (0.5, 0.6, 0.7, 0.8):
    print(f"    q={q}: all5={q**5:.3f} all4={q**4:.3f}")


def pmf(j, n, p):
    return math.exp(math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * math.log(p) + (n - j) * math.log1p(-p))


def central_interval(n, p, alpha):
    """Smallest lo with P(X < lo) <= alpha/2 < P(X <= lo); largest hi with P(X > hi) <= alpha/2."""
    cdf, lo = 0.0, 0
    while cdf + pmf(lo, n, p) <= alpha / 2:
        cdf += pmf(lo, n, p)
        lo += 1
    tail, hi = 0.0, n
    while tail + pmf(hi, n, p) <= alpha / 2:
        tail += pmf(hi, n, p)
        hi -= 1
    return lo, hi


print("\n== 4. G2 central interval at level 1 - 0.001/40 around 1/32 (count, accuracy, Fano bits at upper end)")
alpha = 0.001 / 40
for F in (2048, 8192, 32768):
    lo, hi = central_interval(F, 1 / 32, alpha)
    print(f"  F={F}: [{lo}, {hi}] = [{lo/F:.4f}, {hi/F:.4f}]  i just above upper end = {fano((hi+1)/F):.4f} bits")
fw = 1 - (1 - alpha) ** 40
print(f"  family-wise false-fail (40 independent tests, each exact level <= alpha): <= {fw:.5f}")

print("\n== 5. Parameter counts (key 16)")
def foq(n, dv=32):
    return n * (16 + dv) + 32 * dv + 1
def h8(n, dv=32):
    return n * dv + 32 * dv + 1
for n in (4096, 16384, 65536):
    h = round((foq(n) - 1) / 48)
    print(f"  F-OQ N={n}: {foq(n):,}; D-OQ h={h}: {48*h+1:,} ({(48*h+1-foq(n))/foq(n)*100:+.3f}%); H8 N={n}: {h8(n):,}")
print(f"  F-OQ-wide 4096 x 175: {foq(4096,175):,} vs F-OQ 16384: {foq(16384):,} ({(foq(4096,175)-foq(16384))/foq(16384)*100:+.3f}%)")
for n, dv in ((4096, 127), (4096, 128), (65536, 8)):
    print(f"  H8 {n} x {dv}: {h8(n,dv):,} vs 525,313 ({(h8(n,dv)-525313)/525313*100:+.3f}%)")
print("  Key width that makes a 4,096-slot F-OQ iso-parameter with 16,384 slots at d_v = 32: k with 4096(k+32)+1025 = 787,457 -> k =", (787457 - 1025) / 4096 - 32)

print("\n== 6. Counted work W = 16 K + d_v V (+ wo, which the draft omits)")
for n in (4096, 16384, 65536):
    wf = 16 * n + 256
    wt = 16 * (n // 256 + 512) + 256
    print(f"  N={n}: F-OQ {wf:,}; T-OQ {wt:,}; D-OQ ~{48*(n+21):,}; wo adds 1,024 to each memory arm")
print(f"  T-OQ step ratios: {(16*(64+512)+256)/(16*(16+512)+256):.3f}, {(16*(256+512)+256)/(16*(64+512)+256):.3f}; F-OQ: {(16*16384+256)/(16*4096+256):.3f}, {(16*65536+256)/(16*16384+256):.3f}")
print(f"  F-OQ-wide 8K/4K: 16*4096 + 8*175 = {16*4096+8*175:,} (+ wo 32x175 = 5,600)")
