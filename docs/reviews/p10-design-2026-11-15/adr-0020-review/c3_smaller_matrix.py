"""Projections for the auditor's proposed smaller S0 matrices (same P9-I rates as ADR-0020 §10.4).
Usage: python3 -I c3_smaller_matrix.py"""
RATES = {"fastest": (0.008, 0.013, 0.035), "W7 registered": (0.0098, 0.0141, 0.0531),
         "slowest": (0.0112, 0.0195, 0.0619)}
def hours(cells, rate):
    r4, r16, r64 = rate
    s = 0.0
    for n, upd, slots in cells:
        s += n * upd * {4096: r4, 16384: r16, 65536: r64}[slots]
    return s / 3600
variants = {
  "MIN (gate only): 2K/4K A0,C x12 + A6,A7 x6; 8K/4K A0,C,A6 x6; 8K/16K A0,C x6 + A6,A7 x6":
     [(36, 8192, 4096), (18, 32768, 4096), (24, 32768, 16384)],
  "MIN, C = A0": [(24, 8192, 4096), (12, 32768, 4096), (18, 32768, 16384)],
  "REC = MIN + second init seed at 8K/16K for A0 and C (+12)":
     [(36, 8192, 4096), (18, 32768, 4096), (36, 32768, 16384)],
  "optional WX(C) at 2K/4K x12 and 8K/16K x6 (+18)": [(12, 8192, 4096), (6, 32768, 16384)],
  "optional X2 at 2K/4K x12, 8K/4K x6, 8K/16K x6 (+24)": [(12, 8192, 4096), (6, 32768, 4096), (6, 32768, 16384)],
  "optional 65,536 annotation probe: C and A6 x 3 draws at 131,072 updates (6 cells, one round)": [(6, 131072, 65536)],
  "draft largest Q1+Q2+Q3 (126 + 12 + 24 jobs), for comparison":
     [(60, 8192, 4096), (30, 32768, 4096), (36, 32768, 16384), (12, 131072, 65536), (16, 16384, 16384), (8, 32768, 16384)],
}
for name, cells in variants.items():
    n = sum(c[0] for c in cells)
    print(name)
    for rn, rate in RATES.items():
        h = hours(cells, rate)
        print(f"   {rn:14} {n:4d} cells  summed {h:6.2f} CPU-h   /6 = {h/6:5.2f} h")
