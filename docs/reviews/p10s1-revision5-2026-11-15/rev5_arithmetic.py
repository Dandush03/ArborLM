"""ADR-0021 revision 5: design arithmetic (final cell list after the independent review: 2K/256 added for F-OQ, 31 configurations, C_max 36 h). Standard library only; reads nothing; runs no study code.

Every rate below is copied from docs/reviews/p10s1-load-search-2026-11-15/audit_curves.out (Part D) and audit_costs.out
(calibration draws, commit 3ad821a). MAN = manifest task seconds per update (training plus the calibration's evaluations and
start-up); TRN = train.json wall seconds per update. Rates marked ASSUMED were never measured. Every U_L is an extrapolation.

Run: python3 -I rev5_arithmetic.py > rev5_arithmetic.out
"""
import math

K = 1024
# ---------------------------------------------------------------------------------------------------------------- analytic counts
B, T, Q = 16, 63, 128
FWD = B * (2 * (T * 32 * 96 + 4 * T * T * 8 + 4 * T * T * 8 + T * 32 * 32 + 2 * T * 32 * 64) + T * 32 * 256)
BWD = B * (T * 32 * 96 + T * 32 * 32 + 2 * T * 32 * 64 + 4 * (4 * T * T * 8) + T * 32 * 256)
BACKBONE = FWD + BWD


def params(n):  # F-OQ: keys 16 n, values 32 n, wo 32x32, gate
    return 48 * n + 1025


def hidden(n):  # 49 h + 1 = params
    return round((params(n) - 1) / 49)


def madds(arm, n):
    p = params(n)
    if arm == "F-OQ":
        a = 2 * Q * n * 16 + 3 * Q * 32 * 32 + Q * 32 * 24
    elif arm == "T-OQ":
        a = 2 * Q * (n // 256 * 16 + 512 * 16) + 3 * Q * 32 * 32 + Q * 32 * 24
        p += (n // 256) * 16  # router rows (order of magnitude only)
    elif arm == "H8":
        a = 3 * Q * 32 * 32 + Q * 32 * 16
        p = 32 * n + 1025
    elif arm == "D-OQ":
        h = hidden(n)
        a = 2 * Q * 16 * h + 3 * Q * h * 32
    else:
        raise ValueError(arm)
    return BACKBONE + a + 4 * p


MC_GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)


def grid(m):
    for g in MC_GRID:
        if g >= m - 1e-12:
            return g
    return None


def fano(a):
    e = 1 - a
    if e <= 0:
        return 5.0
    h = -e * math.log2(e) - (1 - e) * math.log2(1 - e)
    return 5 - h - e * math.log2(31)


def a_of(i):
    lo, hi = 1 / 32, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fano(mid) < i else (lo, mid)
    return lo


print("## 1. Parameters, dense width, analytic multiply-adds per update (whole update, section 22 M6)")
print(f"backbone forward+backward: {BACKBONE / 1e6:.1f} M")
for n in (1024, 4096, 16384):
    row = {a: madds(a, n) / 1e6 for a in ("F-OQ", "T-OQ", "H8", "D-OQ")}
    print(f"  N={n:6d}: params {params(n):7d}  h={hidden(n):6d}  madds M: " + "  ".join(f"{a} {v:6.1f}" for a, v in row.items()))
print("\n## 2. Matched compute: analytic multiplier and the grid snapshot it needs (cheaper cell read at m x U_P)")
print("  (a) between the cells of a step, same arm (larger / smaller):")
for arm in ("F-OQ", "T-OQ", "H8"):
    for small, large in ((1024, 4096), (4096, 16384)):
        m = madds(arm, large) / madds(arm, small)
        print(f"      {arm:5s} {small:6d}->{large:6d}: {m:5.2f} -> grid {grid(m)}")
print("  (b) dense against the arm at one cell (D-OQ / arm); the arm is the cheaper and is read at m x U_P <= its run length 6 x U_P:")
for arm in ("F-OQ", "T-OQ", "H8"):
    for n in (1024, 4096, 16384):
        m = madds("D-OQ", n) / madds(arm, n)
        print(f"      {arm:5s} N={n:6d}: {m:5.2f} -> grid {grid(m)}")
print("  measured CPU-time multipliers exist only for F-OQ and D-OQ at 16,384 (0.0245 / 0.0158-0.0175 = 1.40-1.55) and F-OQ 16,384/4,096 (1.60-1.65).")

print("\n## 3. Loaded cells: predicted saturation under the check's 17-18 bits per slot (EXTRAPOLATION; nothing at 1,024 slots was ever run)")
for facts, slots in ((8192, 1024), (32768, 4096), (131072, 16384), (2048, 1024), (8192, 4096), (32768, 16384)):
    for b in (16.0, 17.0, 18.0):
        i = min(5.0, b * slots / facts)
        print(f"  {facts // K:4d}K/{slots // K:2d}K load {facts / slots:4.1f}: {b:4.1f} bits/slot -> i = {i:4.2f} bits/fact, a_use ~ {a_of(i):.3f}", "(ceiling: not storage-limited)" if i >= 5 else "")
print("  measured for comparison (calibration, 65,536 updates, not saturated): 32K/4K 1.89-1.94 = 15.1-15.5 bits/slot; 16K/4K 4.06-4.12 = 16.3-16.5; 131K/16K 1.46-1.52 = 11.7-12.1; 64K/16K 3.49-3.54 = 14.0-14.2")
print("  bits per trainable parameter at 17.5 bits per slot: 17.5/48 = 0.36; a D-OQ of equal size would need 5 F / (48 N) = 0.83 bits per parameter to hold a load-8 fact set")

# ---------------------------------------------------------------------------------------------------------------- costs
RATES = {
    "MAN": {("F-OQ", 1024): 0.00986, ("F-OQ", 4096, "s"): 0.00986, ("F-OQ", 4096, "l"): 0.01090, ("F-OQ", 16384, "s"): 0.01582, ("F-OQ", 16384, "l"): 0.01751, ("F-OQ", 16384, "x"): 0.02590,
            ("H8", 1024): 0.00820, ("H8", 4096): 0.00820, ("H8", 16384): 0.01097, ("D-OQ", 1024): 0.0095, ("D-OQ", 4096): 0.01225, ("D-OQ", 16384): 0.02450,
            ("R2", 4096): 0.01009, ("R2", 16384): 0.01126, ("R2", 32768): 0.0160},
    "TRN": {("F-OQ", 1024): 0.00939, ("F-OQ", 4096, "s"): 0.00939, ("F-OQ", 4096, "l"): 0.00933, ("F-OQ", 16384, "s"): 0.01526, ("F-OQ", 16384, "l"): 0.01543, ("F-OQ", 16384, "x"): 0.01873,
            ("H8", 1024): 0.00746, ("H8", 4096): 0.00746, ("H8", 16384): 0.01013, ("D-OQ", 1024): 0.0091, ("D-OQ", 4096): 0.01177, ("D-OQ", 16384): 0.02353,
            ("R2", 4096): 0.00909, ("R2", 16384): 0.01024, ("R2", 32768): 0.0145},
}
ASSUMED = "ASSUMED (unmeasured): everything at 1,024 slots (set to the 4,096-slot rate, an upper bound if the backbone dominates); D-OQ at 4,096 (half its 16,384 rate) and at 1,024; R2 at 32,768 rows (interpolated); T-OQ (a multiple of F-OQ)."


def rate(rs, arm, facts, slots):
    r = RATES[rs]
    if arm in ("F-OQ", "T-OQ"):
        if slots <= 1024:  # 256 and 1,024 slots: never measured, set to the 4,096-slot rate
            return r[("F-OQ", 1024)]
        size = "x" if facts >= 131072 else ("l" if facts >= 32768 else "s")
        return r[("F-OQ", slots, size)]
    return r[(arm, slots)]


UL0 = 98304  # 2K/256 (F-OQ only): central guess, the earliest value the two-pass rule allows; an extrapolation with no data


def matrix(ul1, ul2, up=(8192, 8192, 16384), ul0=UL0):
    """(arm, facts, slots, updates) of one replicate. Rows 2K, 8K, 32K with their U_P; loaded cells run U_L, others 6 x U_P, R2 U_P."""
    u2, u8, u32 = up
    cells = [(2048, 1024, 6 * u2), (2048, 4096, 6 * u2), (8192, 1024, ul1), (8192, 4096, 6 * u8), (8192, 16384, 6 * u8), (32768, 4096, ul2), (32768, 16384, 6 * u32)]
    out = [(arm, f, n, u) for arm in ("F-OQ", "T-OQ", "H8") for f, n, u in cells]
    out += [("F-OQ", 2048, 256, ul0)]  # saturation-only cell (review M6)
    out += [("D-OQ", 2048, 4096, 6 * u2), ("D-OQ", 8192, 4096, 6 * u8), ("D-OQ", 8192, 16384, 6 * u8), ("D-OQ", 32768, 16384, 6 * u32), ("D-OQ", 8192, 1024, ul1), ("D-OQ", 32768, 4096, ul2)]
    out += [("R2", 2048, 4096, u2), ("R2", 8192, 16384, u8), ("R2", 32768, 32768, u32)]
    return out


def seconds(rs, toq, items):
    by = {}
    for arm, f, n, u in items:
        s = u * rate(rs, arm, f, n) * (toq if arm == "T-OQ" else 1.0)
        by[arm] = by.get(arm, 0.0) + s
    return by


def hours(x):
    return x / 3600


CHARGED = 5664 / 3600  # ledger_after_calibration.json
EVAL = {"low": 1.5, "high": 2.5}  # lead's estimate: calibration evaluation seconds per snapshot x 4.5 (added ablations, H1/H2, index read) x ~12 snapshots; UNMEASURED
OTHER = 0.5  # gates at real size, timing stage, simulation, analysis, report (section 10.3 allowed 0.4)
REHEARSAL = 0.5

print("\n## 4. Registered training per replicate (seconds), 31 configurations; " + ASSUMED)
assert len(matrix(1, 1)) == 31
for rs in ("MAN", "TRN"):
    for toq in (1.0, 2.0):
        for ul1, ul2 in ((98304, 196608), (131072, 262144), (131072, 393216), (196608, 393216), (262144, 524288)):
            by = seconds(rs, toq, matrix(ul1, ul2))
            tot = sum(by.values())
            longest = max(u * rate(rs, a, f, n) * (toq if a == "T-OQ" else 1) for a, f, n, u in matrix(ul1, ul2))
            print(f"  {rs} T-OQ={toq:.0f}x  U_L1={ul1:7d} U_L2={ul2:7d}: " + " ".join(f"{a} {v:6.0f}" for a, v in by.items()) + f" | total {tot:6.0f} s -> 5 replicates / 6 workers = {hours(tot * 5 / 6):5.2f} h (longest single run {hours(longest):.2f} h)")

print("\n## 5. What the long cell 32K/4K costs by itself (5 replicates, charged hours at six workers), by U_L2")
for rs in ("MAN", "TRN"):
    for ul2 in (196608, 262144, 393216, 524288):
        f = ul2 * rate(rs, "F-OQ", 32768, 4096)
        h8 = ul2 * rate(rs, "H8", 32768, 4096)
        d = ul2 * rate(rs, "D-OQ", 32768, 4096)
        print(f"  {rs} U_L2={ul2:7d}: F-OQ {f:5.0f} s, T-OQ {f:5.0f}-{2 * f:5.0f}, H8 {h8:5.0f}, D-OQ {d:5.0f} per replicate -> {hours((2 * f + h8 + d) * 5 / 6):.2f}-{hours((3 * f + h8 + d) * 5 / 6):.2f} h")

print("\n## 6. Block S3: 128K/16K (131,072 facts), F-OQ only, 5 replicates (run length U_L3 is an extrapolation of an extrapolation)")
print("  time shift between 4,096 and 16,384 slots at load 8, read off the calibration curves: i=0.970 is reached at 32,768 (16K) and ~13,970 (4K): x2.35; i=1.508 at 65,536 and ~26,560: x2.47")
print("  -> U_L3 ~ 2.4 x U_L2 = 630K-940K if both stores saturate at the same bits per fact (the hypothesis under test); 4 x U_L2 = 1.05M-1.57M if time scales with facts")
for rs in ("MAN", "TRN"):
    for ul3 in (524288, 786432, 1048576, 1572864):
        s = ul3 * rate(rs, "F-OQ", 131072, 16384)
        print(f"  {rs} U_L3={ul3:8d}: {s:6.0f} s = {hours(s):4.2f} h per run; 5 runs on 5 workers: wall >= {hours(s):4.2f} h, worker-hours {hours(5 * s):5.1f}")

print("\n## 7. New calibration (two calibration draws; every load-search run goes once to its ceiling: 262,144 at 8K/1K, 524,288 at 32K/4K), charged wall hours at six workers")


def calib(rs, toq, ul1max, ul2max, s3max):
    load = [ul1max * rate(rs, "F-OQ", 8192, 1024) * m for m in (1, 1, toq, toq)] + [ul2max * rate(rs, "F-OQ", 32768, 4096) * m for m in (1, 1, toq, toq)] + [262144 * rate(rs, "F-OQ", 2048, 256)] * 2  # 2K/256, F-OQ alone, to the 8K/1K ceiling
    s3 = [s3max * rate(rs, "F-OQ", 131072, 16384)] * 2 if s3max else []
    up = [32768 * rate(rs, "F-OQ", f, n) for f, n in ((2048, 4096), (8192, 4096), (32768, 16384))] * 2 + [32768 * rate(rs, "R2", 0, n) for n in (4096, 16384, 32768)] * 2
    h8 = [32768 * rate(rs, "H8", 0, n) for n in (4096, 4096, 16384)] * 2
    dense = [8192 * rate(rs, "D-OQ", 0, 4096)] * 10 + [16384 * rate(rs, "D-OQ", 0, 16384)] * 10 + [65536 * rate(rs, "D-OQ", 0, 1024)] * 10 + [65536 * rate(rs, "D-OQ", 0, 4096)] * 10  # five rates x two draws x four units
    tasks = load + s3 + up + h8 + dense
    return max(sum(tasks) / 6, max(tasks)), sum(tasks)


for rs in ("MAN", "TRN"):
    for toq in (1.0, 2.0):
        for name, a, b, c in (("to the ceilings, no S3", 262144, 524288, 0), ("to the ceilings, S3 to 1,048,576", 262144, 524288, 1048576)):
            wall, tot = calib(rs, toq, a, b, c)
            print(f"  {rs} T-OQ={toq:.0f}x {name:34s}: wall {hours(wall):4.2f} h (+0.1 timing preview), worker-hours {hours(tot):5.1f}")

print("\n## 8. Cap needed = charged so far + new calibration + rehearsal + 2 x (training + evaluation + other + seed block on draw 1)")
print(f"  charged so far {CHARGED:.2f} h; rehearsal {REHEARSAL} h; evaluation {EVAL['low']}-{EVAL['high']} h (UNMEASURED estimate); other {OTHER} h")


C_MAX = 36.0  # the lead's ruling 1 (LEAD_RULINGS.md), recorded in ADR section 10.3


def need(rs, toq, ul1, ul2, ev, ul3=0, seed=True, drop=()):
    by = seconds(rs, toq, [x for x in matrix(ul1, ul2) if (x[0], x[1], x[2]) not in drop])
    train = sum(by.values()) * 5 / 6
    seven = sum(u * rate(rs, a, f, n) for a, f, n, u in matrix(ul1, ul2) if a == "F-OQ" and n != 256)  # the seed block is the seven grid cells, not 2K/256
    block = seven * 2 / 6 if seed else 0.0
    cal, _ = calib(rs, toq, 262144, 524288, 1048576 if ul3 else 0)  # the calibration always runs to its ceilings
    s3 = 0.0
    if ul3:
        run = ul3 * rate(rs, "F-OQ", 131072, 16384)
        train = max(train + run * 5 / 6, run)  # five more runs share the six workers; no stage is shorter than its longest run
        s3 = 3600 * 1.0  # S3's evaluation: 131,072 facts, about 14 snapshots, five cells (UNMEASURED estimate)
    remaining = hours(train + block + s3) + ev + OTHER
    return CHARGED + hours(cal) + 0.1 + REHEARSAL + 2 * remaining, remaining, hours(cal) + 0.1


print("  (a) registered matrix without S3:")
for rs, toq, ev in (("TRN", 1.0, "low"), ("TRN", 2.0, "low"), ("MAN", 1.0, "high"), ("MAN", 2.0, "high")):
    for ul1, ul2 in ((98304, 196608), (131072, 262144), (131072, 393216), (196608, 393216), (262144, 524288)):
        c, rem, cal = need(rs, toq, ul1, ul2, EVAL[ev])
        c0, rem0, _ = need(rs, toq, ul1, ul2, EVAL[ev], seed=False)
        print(f"    {rs} T-OQ={toq:.0f}x eval {ev:4s} U_L1={ul1:7d} U_L2={ul2:7d}: calibration {cal:4.2f} h, remaining {rem:5.2f} h -> cap {c:5.1f} h (rounded up {math.ceil(c)}); without the seed block {c0:5.1f} h")
print("  (b) with block S3 (F-OQ only at 128K/16K = 131,072 facts), U_L1=131,072, U_L2=393,216:")
for rs, toq, ev in (("TRN", 1.0, "low"), ("TRN", 2.0, "low"), ("MAN", 1.0, "high"), ("MAN", 2.0, "high")):
    for ul3 in (524288, 786432, 1048576):
        c, rem, cal = need(rs, toq, 131072, 393216, EVAL[ev], ul3)
        print(f"    {rs} T-OQ={toq:.0f}x eval {ev:4s} U_L3={ul3:8d}: calibration {cal:4.2f} h, remaining {rem:5.2f} h -> cap {c:5.1f} h")
print("  (c) cheapest alternatives if (a) does not fit: drop row 2K (2K/1K, 2K/4K: 8 configurations) or D-OQ at the two loaded cells:")
for rs, toq, ev in (("TRN", 2.0, "low"), ("MAN", 2.0, "high")):
    for ul1, ul2 in ((131072, 393216), (262144, 524288)):
        full = matrix(ul1, ul2)
        no2k = [x for x in full if x[1] != 2048]
        nodl = [x for x in full if not (x[0] == "D-OQ" and (x[1], x[2]) in ((8192, 1024), (32768, 4096)))]
        for name, m in (("full", full), ("without row 2K", no2k), ("without D-OQ at loaded cells", nodl)):
            print(f"    {rs} T-OQ={toq:.0f}x U_L1={ul1} U_L2={ul2} {name:30s}: training {hours(sum(seconds(rs, toq, m).values()) * 5 / 6):5.2f} h -> cap changes by {2 * hours((sum(seconds(rs, toq, m).values()) - sum(seconds(rs, toq, full).values())) * 5 / 6):+5.2f} h")

print("\n## 9. Two side figures quoted in the ADR")
for rs in ("TRN", "MAN"):
    for name, u1, u2 in (("at the central U_L", 131072, 393216), ("at the ceilings (U_L is not known before the search ends)", 262144, 524288)):
        extra = 10 * (u1 - 65536) * rate(rs, "D-OQ", 0, 1024) + 10 * (u2 - 65536) * rate(rs, "D-OQ", 0, 4096)
        print(f"  {rs} choosing the dense rate of a loaded cell at U_L instead of at 65,536, {name}: +{hours(extra / 6):.2f} h of calibration")
for rs, toq, ev in (("TRN", 1.0, "low"), ("MAN", 2.0, "high")):
    save = 131072 * rate(rs, "F-OQ", 32768, 4096) * (2 + 2 * toq) / 6
    c, rem, cal = need(rs, toq, 262144, 393216, EVAL[ev])
    print(f"  {rs} T-OQ={toq:.0f}x a ceiling of 393,216 at 32K/4K: calibration shorter by {hours(save):.2f} h; worst case (U_L 262,144 and 393,216) C_need {c - hours(save):.1f} h")
    d = 49152 * rate(rs, "D-OQ", 0, 16384) * 5 / 6 * 2
    h = (131072 * rate(rs, "H8", 0, 1024) + 393216 * rate(rs, "H8", 0, 4096)) * 5 / 6 * 2
    print(f"  {rs} D-OQ at 8K/16K is worth {hours(d):.2f} h of C_need; H8 at the two loaded cells {hours(h):.2f} h (central U_L)")

print("\n## 10. Against C_max = 36 h, with the fixed cuts in order (cut 2: no seed block; cut 3: also no D-OQ at 8K/16K). Packing here is total/6; the review used longest-first and got 0.5-3 h less")
for rs, toq, ev in (("TRN", 1.0, "low"), ("TRN", 2.0, "low"), ("MAN", 1.0, "high"), ("MAN", 2.0, "high")):
    for ul1, ul2 in ((98304, 196608), (131072, 393216), (262144, 524288)):
        a = need(rs, toq, ul1, ul2, EVAL[ev])[0]
        b = need(rs, toq, ul1, ul2, EVAL[ev], seed=False)[0]
        c = need(rs, toq, ul1, ul2, EVAL[ev], seed=False, drop=(("D-OQ", 8192, 16384),))[0]
        verdict = "fits" if a <= C_MAX else ("fits after cut 2" if b <= C_MAX else ("fits after cut 3" if c <= C_MAX else "RETURNS: NOT STARTED, BUDGET"))
        print(f"  {rs} T-OQ={toq:.0f}x eval {ev:4s} U_L {ul1:7d}/{ul2:7d}: {a:5.1f} / {b:5.1f} / {c:5.1f} -> {verdict}")
print("  the 2K/256 cell: registered " + ", ".join(f"{rs} {hours(UL0 * rate(rs, 'F-OQ', 2048, 256) * 5 / 6):.2f} h" for rs in ("TRN", "MAN")) + " (doubled in C_need); its search two runs of " + ", ".join(f"{rs} {hours(262144 * rate(rs, 'F-OQ', 2048, 256)):.2f} h" for rs in ("TRN", "MAN")))
