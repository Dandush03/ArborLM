"""Auditor check A2: independent recomputation of revision 5's multiply-adds, matched-compute multipliers and charged hours.

Standard library only; imports no study code and not rev5_arithmetic.py. The multiply-add formula is transcribed from the
config's `madds_formula` string (configs/p10s1_capacity.toml line 105, ruling s22 M6/s22.1). Rates are the raw per-update
training wall seconds printed by a1_calibration.out section 6 (calibration draws, revision-4 code 3ad821a).

Usage: python3 -I a2_cost.py
"""
import heapq
import math

# ------------------------------------------------------------------ 1. multiply-adds (config formula)
B, T = 16, 63
Q = 8 * B
fwd = B * (2 * (T * 32 * 96 + 4 * T * T * 8 + 4 * T * T * 8 + T * 32 * 32 + 2 * T * 32 * 64) + T * 32 * 256)
bwd = B * (T * 32 * 96 + T * 32 * 32 + 2 * T * 32 * 64 + 4 * (4 * T * T * 8) + T * 32 * 256)
BACK = fwd + bwd


def h_of(n):
    p = 48 * n + 1025
    return round((p - 1) / 49)


def params(arm, n):
    if arm == "F-OQ":
        return 48 * n + 1025
    if arm == "T-OQ":
        return 48 * n + 1025 + (n // 256) * 16
    if arm == "H8":
        return 32 * n + 1025
    if arm == "D-OQ":
        h = h_of(n)
        return 16 * h + h + 32 * h + 1
    if arm == "R2":
        return 32 * n + 1025
    raise ValueError(arm)


def madds(arm, n):
    if arm == "F-OQ":
        a = 2 * Q * n * 16 + 3 * Q * 32 * 32 + Q * 32 * 3 * 8
    elif arm == "T-OQ":
        a = 2 * Q * ((n // 256) * 16 + 512 * 16) + 3 * Q * 32 * 32 + Q * 32 * 3 * 8
    elif arm == "H8":
        a = 3 * Q * 32 * 32 + Q * 32 * 2 * 8
    elif arm == "R2":
        a = 3 * Q * 32 * 32 + Q * 32 * 2 * 1
    elif arm == "D-OQ":
        h = h_of(n)
        a = 2 * Q * 16 * h + 3 * Q * h * 32
    return BACK + a + 4 * params(arm, n)


GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)


def snap(m):
    return next((g for g in GRID if g >= m - 1e-12), None)


print("## 1. Multiply-adds per whole update (config formula), D-OQ width and parameter match")
print(f"  backbone fwd+bwd {BACK / 1e6:.2f} M")
for n in (256, 1024, 4096, 16384):
    h = h_of(n)
    print(f"  N={n:6d}: F-OQ params {params('F-OQ', n)}, D-OQ h={h} params {params('D-OQ', n)} (diff {100 * (params('D-OQ', n) - params('F-OQ', n)) / params('F-OQ', n):+.3f}%)  madds M: " + "  ".join(f"{a} {madds(a, n) / 1e6:.2f}" for a in ("F-OQ", "T-OQ", "H8", "D-OQ") if not (a == "T-OQ" and n < 512)))
print("\n## 2. Analytic multipliers and grid snapshots")
for arm in ("F-OQ", "T-OQ", "H8"):
    for s, l in ((1024, 4096), (4096, 16384)):
        m = madds(arm, l) / madds(arm, s)
        print(f"  step {arm} {s}->{l}: {m:.3f} -> {snap(m)}")
for arm in ("F-OQ", "T-OQ", "H8"):
    for n in (1024, 4096, 16384):
        m = madds("D-OQ", n) / madds(arm, n)
        print(f"  D-OQ/{arm} at {n}: {m:.3f} -> {snap(m)}")
print("  F-OQ 256->1024 (ruling 2 pair; saturation only, no MC needed):", round(madds("F-OQ", 1024) / madds("F-OQ", 256), 3))

# ------------------------------------------------------------------ 3. a per-update cost model fitted to the measured rates
# measured training wall s/update (a1 section 6): (arm, N) -> rate. Only runs >= 32,768 updates (short runs carry start-up).
MEAS = {("F-OQ", 4096): 0.00933, ("F-OQ", 16384): 0.01543, ("H8", 4096): 0.00746, ("H8", 16384): 0.01013, ("D-OQ", 16384): 0.02389}
# least squares t = c0 + c1 * arm_madds + c2 * params (arm_madds = madds - backbone)
rows = [(1.0, (madds(a, n) - BACK) / 1e6, params(a, n) / 1e6, t) for (a, n), t in MEAS.items()]


def solve3(rows):
    ata = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
    atb = [sum(r[i] * r[3] for r in rows) for i in range(3)]
    m = [ata[i] + [atb[i]] for i in range(3)]
    for c in range(3):
        p = max(range(c, 3), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(3):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][3] / m[i][i] for i in range(3)]


c0, c1, c2 = solve3(rows)
print(f"\n## 3. Fitted cost model (training wall s/update) = {c0:.5f} + {c1:.6f} x arm M-madds + {c2:.5f} x M-params")
for (a, n), t in MEAS.items():
    pred = c0 + c1 * (madds(a, n) - BACK) / 1e6 + c2 * params(a, n) / 1e6
    print(f"  {a} {n}: measured {t:.5f} fitted {pred:.5f}")


def model(arm, n):
    return c0 + c1 * (madds(arm, n) - BACK) / 1e6 + c2 * params(arm, n) / 1e6


for n in (256, 1024, 4096, 16384):
    print(f"  predicted N={n}: " + "  ".join(f"{a} {model(a, n):.5f}" for a in ("F-OQ", "T-OQ", "H8", "D-OQ")) + f"  R2(32K rows) {model('R2', 32768):.5f}")
print("  (T-OQ 'model' has no term for its gather/bmm/router overhead; it is NOT a prediction, the bracket 1x-2x F-OQ is kept.)")

# CPU-time vs analytic disagreement risk (MC-AMBIGUOUS) under the draft's own assumed rates
DRAFT = {("F-OQ", 1024): 0.00939, ("F-OQ", 4096): 0.00933, ("F-OQ", 16384): 0.01543, ("H8", 1024): 0.00746, ("H8", 4096): 0.00746, ("H8", 16384): 0.01013, ("D-OQ", 1024): 0.0091, ("D-OQ", 4096): 0.01177, ("D-OQ", 16384): 0.02353}
print("\n## 4. Direction check of the two cost measures (MC-AMBIGUOUS when they disagree), draft's assumed CPU rates and T-OQ at 1x / 2x F-OQ")
for toq in (1.0, 2.0):
    r = dict(DRAFT)
    for n in (1024, 4096, 16384):
        r[("T-OQ", n)] = toq * r[("F-OQ", n)]
    for arm in ("F-OQ", "T-OQ", "H8"):
        for n in (1024, 4096, 16384):
            an = madds("D-OQ", n) / madds(arm, n)
            cp = r[("D-OQ", n)] / r[(arm, n)]
            amb = (an >= 1) != (cp >= 1)
            print(f"  T-OQ={toq:.0f}x  D-OQ vs {arm:4s} at {n:5d}: analytic {an:.2f}, cpu {cp:.2f}{'  -> MC-AMBIGUOUS (dense MC not established; STORE HOLDS MORE cost condition fails)' if amb else ''}")
    for arm in ("F-OQ", "T-OQ", "H8"):
        for s, l in ((1024, 4096), (4096, 16384)):
            an = madds(arm, l) / madds(arm, s)
            cp = r[(arm, l)] / r[(arm, s)]
            print(f"  T-OQ={toq:.0f}x  step {arm:4s} {s}->{l}: analytic {an:.3f}, cpu {cp:.3f}{'  -> MC-AMBIGUOUS (Delta_MC undefined; CAPACITY unreachable for this step)' if (an >= 1) != (cp >= 1 - 1e-9) else ('  (equal cpu: direction decided by timing noise)' if abs(cp - 1) < 0.02 else '')}")

# ------------------------------------------------------------------ 5. hours
CHARGED = 5663.62 / 3600


def rate(arm, n, facts, scen):
    """Training wall s/update. scen: 'draft' (1K = 4K rate, D-OQ 4K half of 16K) or 'model' (fitted); T-OQ via toq."""
    if arm == "R2":
        return {4096: 0.00909, 16384: 0.01024, 32768: 0.0145}[n] if scen == "draft" else max(0.00909, model("R2", n))
    if scen == "draft":
        if arm in ("F-OQ", "T-OQ"):
            base = {256: 0.00939, 1024: 0.00939, 4096: 0.00933, 16384: 0.01543}[n]
            return 0.01873 if (n == 16384 and facts >= 131072) else base
        return {("H8", 256): 0.00746, ("H8", 1024): 0.00746, ("H8", 4096): 0.00746, ("H8", 16384): 0.01013, ("D-OQ", 1024): 0.0091, ("D-OQ", 4096): 0.01177, ("D-OQ", 16384): 0.02353}[(arm, n)]
    a = "F-OQ" if arm == "T-OQ" else arm
    if (a, n) in MEAS:
        return MEAS[(a, n)]
    return model(a, n)


def matrix(ul1, ul2, up=(8192, 8192, 16384), with256=0):
    u2, u8, u32 = up
    cells = [(2048, 1024, 6 * u2), (2048, 4096, 6 * u2), (8192, 1024, ul1), (8192, 4096, 6 * u8), (8192, 16384, 6 * u8), (32768, 4096, ul2), (32768, 16384, 6 * u32)]
    out = [(arm, f, n, u) for arm in ("F-OQ", "T-OQ", "H8") for f, n, u in cells]
    out += [("D-OQ", 2048, 4096, 6 * u2), ("D-OQ", 8192, 4096, 6 * u8), ("D-OQ", 8192, 16384, 6 * u8), ("D-OQ", 32768, 16384, 6 * u32), ("D-OQ", 8192, 1024, ul1), ("D-OQ", 32768, 4096, ul2)]
    out += [("R2", 2048, 4096, u2), ("R2", 8192, 16384, u8), ("R2", 32768, 32768, u32)]
    if with256:
        out += [("F-OQ", 2048, 256, with256)]
    return out, cells


def lpt(durations, workers=6):
    heap = [0.0] * workers
    for d in sorted(durations, reverse=True):
        t = heapq.heappop(heap)
        heapq.heappush(heap, t + d)
    return max(heap)


# evaluation: seconds per snapshot measured in the calibration (a1 s6), interpolated by facts and slots; times a factor for the
# registered additions (F-OQ-IVF read, slot dropout and value noise at U_P, minimal supports at U_P, KNN-W, H1/H2 already included)
EVS = {(2048, 1024): 1.5, (2048, 4096): 1.5, (8192, 1024): 3.1, (8192, 4096): 3.1, (8192, 16384): 4.6, (32768, 4096): 10.3, (32768, 16384): 17.1, (2048, 256): 1.5, (32768, 32768): 17.0}


def snapshots(n_loaded, run, u_p, loaded, ul=None):
    s = {int(u_p * k) for k in (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1, 2, 4) if u_p * k <= run} | {run // 2, run} | {int(u_p * g) for g in GRID if u_p * g <= run}
    if loaded:
        s |= {32768, 49152} | {c for c in n_loaded if c <= run} | {c // 2 for c in n_loaded if c <= run}
    return len(s)


CAND1 = (65536, 98304, 131072, 196608, 262144)
CAND2 = (131072, 196608, 262144, 393216, 524288)


def stage_hours(ul1, ul2, toq, scen, ev_factor, contention=1.0, seed_block=True, with256=0, cut_doq_8k16k=False):
    items, cells = matrix(ul1, ul2, with256=with256)
    if cut_doq_8k16k:
        items = [x for x in items if not (x[0] == "D-OQ" and x[1:3] == (8192, 16384))]
    durs, evs = [], []
    for rep in range(5):
        for arm, f, n, u in items:
            r = rate(arm, n, f, scen) * (toq if arm == "T-OQ" else 1.0) * contention
            durs.append(u * r)
            loaded = (f, n) in ((8192, 1024), (32768, 4096), (2048, 256))
            u_p = 16384 if f == 32768 else 8192
            cand = CAND1 if (f, n) in ((8192, 1024), (2048, 256)) else CAND2
            k = snapshots(cand, u, u_p, loaded) if arm != "R2" else 3
            mult = ev_factor * (2.0 if arm == "F-OQ" else 1.0)  # F-OQ is also read through the index (F-OQ-IVF)
            evs.append(k * EVS[(f, n)] * mult * contention)
    if seed_block:
        for arm, f, n, u in items:
            if arm == "F-OQ" and n != 256:
                durs += [u * rate(arm, n, f, scen) * contention] * 2
                evs += [snapshots(CAND1, u, 8192, False) * EVS[(f, n)] * 2 * ev_factor * contention] * 2
    return lpt(durs) / 3600, lpt(evs) / 3600, max(durs) / 3600


def calib_hours(toq, scen, contention=1.0, with256=0):
    tasks = []
    for f, n, ceil in ((8192, 1024, 262144), (32768, 4096, 524288)):
        for d in (1, 2):
            tasks.append(ceil * rate("F-OQ", n, f, scen) * contention)
            tasks.append(ceil * rate("T-OQ", n, f, scen) * toq * contention)
    if with256:
        tasks += [with256 * rate("F-OQ", 256, 2048, scen) * contention] * 2
    for f, n in ((2048, 4096), (8192, 4096), (32768, 16384)):
        tasks += [32768 * rate("F-OQ", n, f, scen) * contention] * 2
    for n in (4096, 16384, 32768):
        tasks += [32768 * rate("R2", n, 0, scen) * contention] * 2
    for f, n, u in ((2048, 4096, 8192), (8192, 4096, 8192), (8192, 16384, 8192), (32768, 16384, 16384)):
        tasks += [u * rate("H8", n, f, scen) * contention] * 2
    for n, u in ((4096, 8192), (16384, 16384), (1024, 65536), (4096, 65536)):
        tasks += [u * rate("D-OQ", n, 0, scen) * contention] * 10
    # evaluation of the calibration: ~13-14 snapshots per load-search run, plus the others (small)
    ev = 4 * 13 * 3.1 + 4 * 14 * 10.3 + 200 * 3
    return (lpt(tasks) + ev / 6) / 3600 + 0.1, max(tasks) / 3600, sum(tasks) / 3600


print("\n## 5. Charged hours. 'draft' = the draft's rates (1K = 4K; D-OQ 4K half of 16K); 'model' = fitted model for unmeasured cells.")
print("   LPT packing on 6 workers; evaluation from measured per-snapshot seconds x registered snapshot counts x ev_factor (F-OQ x2 for the index read).")
print("   C_need = 1.57 + calibration + 0.5 rehearsal + 2 x (training + evaluation + 0.5 other), seed block on draw 1 included.")
for scen in ("draft", "model"):
    for toq in (1.0, 2.0):
        cal, longest_cal, _ = calib_hours(toq, scen)
        for ul1, ul2 in ((98304, 196608), (131072, 262144), (131072, 393216), (196608, 393216), (262144, 524288)):
            for evf in (1.5, 3.0):
                tr, ev, lo = stage_hours(ul1, ul2, toq, scen, evf)
                need = CHARGED + cal + 0.5 + 2 * (tr + ev + 0.5)
                print(f"  {scen:5s} T-OQ={toq:.0f}x U_L={ul1:6d}/{ul2:6d} ev x{evf}: calibration {cal:4.2f} h (longest run {longest_cal:4.2f}), training {tr:5.2f} h (longest {lo:4.2f}), evaluation {ev:4.2f} h -> C_need {need:5.1f}")

print("\n## 6. C_max = 36 h (ruling 1): after the fixed cuts (cut 1 n/a: draw-2 block is only added if it fits; cut 2 draw-1 seed block; cut 3 D-OQ at 8K/16K)")
for scen in ("draft", "model"):
    for toq in (1.0, 2.0):
        cal, _, _ = calib_hours(toq, scen)
        for ul1, ul2 in ((131072, 393216), (196608, 393216), (262144, 524288)):
            for evf, cont in ((3.0, 1.0), (3.0, 1.25)):
                full = CHARGED + cal * cont + 0.5 + 2 * (sum(stage_hours(ul1, ul2, toq, scen, evf, cont)[:2]) + 0.5)
                after2 = CHARGED + cal * cont + 0.5 + 2 * (sum(stage_hours(ul1, ul2, toq, scen, evf, cont, seed_block=False)[:2]) + 0.5)
                after3 = CHARGED + cal * cont + 0.5 + 2 * (sum(stage_hours(ul1, ul2, toq, scen, evf, cont, seed_block=False, cut_doq_8k16k=True)[:2]) + 0.5)
                verdict = "fits" if full <= 36 else ("fits after cut 2" if after2 <= 36 else ("fits after cut 3" if after3 <= 36 else "RETURNS (NOT STARTED: BUDGET)"))
                print(f"  {scen:5s} T-OQ={toq:.0f}x U_L={ul1:6d}/{ul2:6d} ev x{evf} contention x{cont}: full {full:5.1f}, after cut 2 {after2:5.1f}, after cut 3 {after3:5.1f} -> {verdict}")

print("\n## 7. Ruling 2's 256-slot cell (F-OQ only, 2,048 facts): search on two draws to a ceiling, five registered runs")
for ceil, ul in ((131072, 65536), (262144, 98304), (262144, 196608)):
    for scen in ("draft", "model"):
        r = rate("F-OQ", 256, 2048, scen)
        print(f"  {scen:5s} rate {r:.5f}: search 2 x {ceil} = {2 * ceil * r / 3600:.2f} worker-h; registered 5 x {ul} = {5 * ul * r / 3600:.2f} worker-h -> C_need +{(2 * ceil * r / 6 + 2 * 5 * ul * r / 6) / 3600:.2f} h (packed)")

print("\n## 8. Concurrency with S0 (6 single-thread workers, ~15 h). M5 Max: 6 'Super' + 12 'Performance' cores (sysctl hw.perflevel*).")
for cont in (1.0, 1.15, 1.3):
    cal, lc, tot = calib_hours(2.0, "draft", cont)
    print(f"  contention x{cont}: calibration (T-OQ 2x, draft rates) {cal:4.2f} h charged; longest single run (T-OQ 32K/4K to 524,288) {lc:4.2f} h; an item cap of 2 x an uncontended preview projection is exceeded only if contention > 2.0")
