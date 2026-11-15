"""Auditor check A1: recompute from the RAW revision-4 calibration records (cells/*/train.json, cells/*/eval/u*/eval.json,
calibrate manifest) everything revision 5 relies on. Standard library only; imports no study code.

Usage: python3 -I a1_calibration.py <run_dir> <calibrate_manifest.json>

i is computed from the raw counts: a_use = useful / n; e = 1 - a_use; i = 5 - h2(e) - e log2 31; i = 0 when the useful count is at
or below the upper end of the exact binomial central interval of level 1 - 0.001/40 around 1/32 (gate G2).
"""
import glob
import json
import math
import os
import re
import sys

run_dir, manifest_path = sys.argv[1:3]
LEVEL = 0.001 / 40


def binom_cdf_table(n, p):
    logs = [math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p) for k in range(n + 1)]
    m = max(logs)
    w = [math.exp(x - m) for x in logs]
    s = sum(w)
    c, out = 0.0, []
    for x in w:
        c += x / s
        out.append(c)
    return out


def chance_interval(n):
    cdf = binom_cdf_table(n, 1 / 32)
    lo = next(k for k in range(n + 1) if cdf[k] > LEVEL / 2)
    hi = next(k for k in range(n + 1) if cdf[k] >= 1 - LEVEL / 2)
    return lo, hi


CI = {n: chance_interval(n) for n in (2048, 8192, 32768)}
print("## G2 chance intervals (exact binomial central, level 1-0.001/40):", CI, "(ADR lists [34,100], [192,325], [894,1159])")


def i_bits(useful, n):
    if n not in CI:
        CI[n] = chance_interval(n)
    if useful <= CI[n][1]:
        return 0.0
    a = useful / n
    e = 1 - a
    if e <= 0:
        return 5.0
    return 5 - (-e * math.log2(e) - a * math.log2(a)) - e * math.log2(31)


def i_of_a(a):
    e = 1 - a
    if e <= 0:
        return 5.0
    return 5 - (-e * math.log2(e) - a * math.log2(a)) - e * math.log2(31)


def a_of_i(i):
    lo, hi = 1 / 32, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if i_of_a(mid) < i else (lo, mid)
    return lo


print("i(0.25) =", round(i_of_a(0.25), 4), " i(0.5) =", round(i_of_a(0.5), 4), " i(0.8) =", round(i_of_a(0.8), 4), " i(0.9) =", round(i_of_a(0.9), 4), " a(4.0) =", round(a_of_i(4.0), 4), " a(4.5) =", round(a_of_i(4.5), 4), " a(3.0) =", round(a_of_i(3.0), 4))

cells = {}
for path in sorted(glob.glob(os.path.join(run_dir, "cells", "*"))):
    label = os.path.basename(path)
    m = re.match(r"CAL_(?P<arm>[A-Z0-9-]+)_f(?P<f>\d+)_n(?P<n>\d+)_d(?P<d>\d)_i\d+(?:_y(?P<y>\d+))?(?:_lr(?P<lr>[\d.]+))?$", label)
    arm, f, n, d = m["arm"], int(m["f"]), int(m["n"]), int(m["d"])
    lr = m["lr"] or ("0.003" if arm == "D-OQ" else None)
    tr = json.load(open(os.path.join(path, "train.json")))
    curve = {}
    for ep in sorted(glob.glob(os.path.join(path, "eval", "u*", "eval.json"))):
        ev = json.load(open(ep))
        u = ev["update"]
        pan = ev["reads"]["main"]["panels"]
        curve[u] = {p: (pan[p]["useful"], pan[p]["n"], pan[p]["correct"]) for p in ("A", "B")}
    cells[label] = dict(arm=arm, f=f, n=n, d=d, y=m["y"], lr=lr, train=tr, curve=curve)

man = {t["label"]: t["seconds"] for t in json.load(open(manifest_path))["tasks"]}


def series(arm, f, n, d, panel, y=None, lr=None):
    for lab, c in cells.items():
        if c["arm"] == arm and c["f"] == f and c["n"] == n and c["d"] == d and (y is None or c["y"] == str(y)) and (lr is None or c["lr"] == lr):
            return {u: i_bits(v[panel][0], v[panel][1]) for u, v in sorted(c["curve"].items())}, {u: v[panel][0] / v[panel][1] for u, v in sorted(c["curve"].items())}
    return None, None


print("\n## 1. F-OQ curves recomputed from raw counts (i bits per fact; A/B panels; draws 1,2)")
for f, n in ((8192, 4096), (16384, 4096), (32768, 4096), (65536, 4096), (8192, 16384), (32768, 16384), (65536, 16384), (131072, 16384), (2048, 4096)):
    for d in (1, 2):
        for p in ("A", "B"):
            s, _ = series("F-OQ", f, n, d, p, y=65536 if f != 2048 else 8192)
            if s is None:
                continue
            print(f"  {f // 1024:3d}K/{n // 1024:2d}K d{d}{p}: " + " ".join(f"{u}:{v:.3f}" for u, v in s.items()))

print("\n## 2. Inputs of the per-row U_P rule (F-OQ a_use at the row's larger step cell; R2 a_use at the reference cell), min over draws and panels")
for f, n, ups in ((2048, 4096, (8192,)), (8192, 4096, (8192, 16384, 32768)), (32768, 16384, (8192, 16384, 32768))):
    for u in ups:
        vals = []
        for d in (1, 2):
            for p in ("A", "B"):
                _, a = series("F-OQ", f, n, d, p, y=65536 if f != 2048 else 8192)
                vals.append(a.get(u))
        print(f"  F-OQ {f // 1024}K/{n // 1024}K at {u}: a_use min {min(vals):.4f} max {max(vals):.4f}  (>= 0.90: {min(vals) >= 0.90})")
for f, n in ((2048, 4096), (8192, 16384), (32768, 65536)):
    vals = []
    for d in (1, 2):
        for p in ("A", "B"):
            _, a = series("R2", f, n, d, p)
            vals.append(a.get(8192))
    print(f"  R2 {f // 1024}K/{n // 1024}K at 8192: a_use min {min(vals):.4f}")
print("  (R2 at 32K/32K never run.)")
# 0.80 floor at 32K/16K: what U_P = 8,192 vs 16,384 would do
for u in (8192, 16384):
    vals = [series("F-OQ", 32768, 16384, d, p, y=65536)[1][u] for d in (1, 2) for p in ("A", "B")]
    print(f"  0.80 floor at 32K/16K read at {u}: a_use {min(vals):.4f}-{max(vals):.4f} -> floor {'passes' if min(vals) >= 0.80 else 'FAILS'} on calibration draws")

print("\n## 3. Plateau guard: i*(U) - i*(U/2) <= 0.10 with and without i*(U/2) >= 0.473, every snapshot U of every F-OQ curve (calibration draws)")


def istar(s, u):
    return max([v for k, v in s.items() if k <= u] or [0.0])


for f, n in ((8192, 4096), (16384, 4096), (32768, 4096), (65536, 4096), (8192, 16384), (32768, 16384), (65536, 16384), (131072, 16384)):
    rows = []
    for d in (1, 2):
        for p in ("A", "B"):
            s, _ = series("F-OQ", f, n, d, p, y=65536)
            for u in s:
                if u // 2 not in s:
                    continue
                g = istar(s, u) - istar(s, u // 2)
                rows.append((u, d, p, g <= 0.10, g <= 0.10 and istar(s, u // 2) >= 0.473 and istar(s, u) <= 4.0, g <= 0.10 and istar(s, u) <= 4.0))
    us = sorted({r[0] for r in rows})
    old = [u for u in us if all(r[5] for r in rows if r[0] == u)]
    new = [u for u in us if all(r[4] for r in rows if r[0] == u)]
    print(f"  {f // 1024:3d}K/{n // 1024:2d}K: 'loaded' on all four views WITHOUT guard at {old}; WITH guard at {new}")
# registered run lengths of revision 4: 49,152 at 4,096; 32,768 at 16,384
print("  revision-4 registered run lengths: plateau status with/without guard at U_run (all four views):")
for f, n, ur in ((8192, 4096, 49152), (16384, 4096, 49152), (32768, 4096, 49152), (65536, 4096, 49152), (8192, 16384, 32768), (32768, 16384, 32768), (65536, 16384, 32768), (131072, 16384, 32768)):
    st = []
    for d in (1, 2):
        for p in ("A", "B"):
            s, _ = series("F-OQ", f, n, d, p, y=65536)
            g = istar(s, ur) - istar(s, ur // 2)
            st.append((g <= 0.10, g <= 0.10 and istar(s, ur // 2) >= 0.473))
    print(f"    {f // 1024:3d}K/{n // 1024:2d}K at {ur}: plateau without guard {[a for a, _ in st]}, with guard {[b for _, b in st]}")

print("\n## 4. Saturation pair 1,024 -> 4,096: what the 4,096 side already bounds (i* is non-decreasing; U_L(32K/4K) >= 131,072 > 65,536)")
lows = []
for d in (1, 2):
    for p in ("A", "B"):
        s, _ = series("F-OQ", 32768, 4096, d, p, y=65536)
        lows.append(istar(s, 65536))
lo = min(lows)
print(f"  i*(32K/4K; 65,536) = {min(lows):.4f}-{max(lows):.4f} bits/fact = {8 * min(lows):.2f}-{8 * max(lows):.2f} bits/slot (lower bound on the 4,096 side at any U_L >= 65,536 on these draws)")
for x in (lo, 2.0, 2.12, 2.25, 2.4):
    thr = 4 * x / 3.0
    print(f"  if i*(32K/4K; U_L) = {x:.3f}: SUBPROPORTIONAL (rho < 3.0) needs i*(8K/1K; U_L) > {thr:.3f} bits/fact (a_use > {a_of_i(thr):.3f}; {8 * thr:.1f} bits/slot)")
# load 4 at 4,096 slots: bits per slot already reached at 65,536
for f in (16384, 8192):
    v = [istar(series("F-OQ", f, 4096, d, p, y=65536)[0], 65536) for d in (1, 2) for p in ("A", "B")]
    print(f"  bits per slot already held at 4,096 slots, load {f // 4096}: {min(v) * f / 4096:.2f}-{max(v) * f / 4096:.2f} (65,536 updates; load 2 is at the 5-bit ceiling)")

print("\n## 5. Efficiency on N2 (8K/4K -> 8K/16K): u_T at i_T = 3.0, log2 interpolation of min over panels, per draw")


def u_t(arm, f, n, d):
    sa, _ = series(arm, f, n, d, "A", y=65536)
    sb, _ = series(arm, f, n, d, "B", y=65536)
    us = sorted(sa)
    mins = [min(sa[u], sb[u]) for u in us]
    for k, u in enumerate(us):
        if mins[k] >= 3.0:
            if k == 0:
                return ("left", u)
            u0, v0, v1 = us[k - 1], mins[k - 1], mins[k]
            t = (3.0 - v0) / (v1 - v0)
            return 2 ** (math.log2(u0) + t * (math.log2(u) - math.log2(u0)))
    return ("right", us[-1])


for d in (1, 2):
    a, b = u_t("F-OQ", 8192, 4096, d), u_t("F-OQ", 8192, 16384, d)
    print(f"  draw {d}: u_T(8K/4K) = {a:.0f}, u_T(8K/16K) = {b:.0f}, ratio {b / a:.3f}  (lead: 4,116/2,624 and 5,624/3,009 on Panel A only)")
for d in (1, 2):
    sa, _ = series("F-OQ", 8192, 4096, d, "A", y=65536)
    print(f"  N2 draw {d} at U_P=8192: i(8K/4K) A = {sa[8192]:.3f}; CEILING needs >= 4.5")

print("\n## 6. Rates (seconds per update) from raw train.json and the manifest; evaluation seconds per snapshot = (task - train wall) / snapshots")
agg = {}
for lab, c in cells.items():
    tr = c["train"]
    u = tr["run_updates"]
    key = (c["arm"], c["n"], c["f"])
    ns = len(c["curve"])
    ev = (man[lab] - tr["wall_seconds"]) / ns
    agg.setdefault(key, []).append((tr["wall_seconds"] / u, tr["cpu_seconds"] / u, man[lab] / u, ev, ns, tr["cpu_seconds"] / tr["wall_seconds"]))
for key in sorted(agg):
    v = agg[key]
    print(f"  {key[0]:5s} N={key[1]:6d} F={key[2]:6d}: wall/upd {min(x[0] for x in v):.5f}-{max(x[0] for x in v):.5f}  cpu/upd {min(x[1] for x in v):.5f}-{max(x[1] for x in v):.5f}  task/upd {min(x[2] for x in v):.5f}-{max(x[2] for x in v):.5f}  eval s/snapshot {min(x[3] for x in v):6.1f}-{max(x[3] for x in v):6.1f} ({v[0][4]} snaps)  cpu/wall {min(x[5] for x in v):.3f}-{max(x[5] for x in v):.3f}  runs {len(v)}")

print("\n## 7. Dense control (D-OQ) at the calibration cells, Panel A a_use by rate (min over draws) at each snapshot")
for f, n in ((8192, 16384), (32768, 65536)):
    for lr in ("0.001", "0.003", "0.01"):
        ss = [series("D-OQ", f, n, d, "A", lr=lr)[1] for d in (1, 2)]
        us = sorted(ss[0])
        print(f"  {f // 1024}K/{n // 1024}K lr {lr}: " + " ".join(f"{u}:{min(s[u] for s in ss):.3f}" for u in us))
