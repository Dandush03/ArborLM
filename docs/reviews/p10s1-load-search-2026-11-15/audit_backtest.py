"""Hold-out backtest of the extrapolation families (auditor). Fit on snapshots <= 32,768 (from 8,192 for the
geometric rule, which needs i(8K), i(16K), i(32K); 16K..32K for the 3-parameter fits at 4K, where 24,576 exists;
from 4,096 for Hill), predict 49,152 (4K only) and 65,536; report the error at 65,536 and the predicted vs observed
increment d(65,536) = i(65,536) - i(32,768). Usage: python3 -I audit_backtest.py"""

import json
import math
from pathlib import Path

import importlib.util

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("ex", HERE / "audit_extrapolate.py")
src = (HERE / "audit_extrapolate.py").read_text().replace("\nmain()\n", "\n")
ns: dict = {"__file__": str(HERE / "audit_extrapolate.py")}
exec(compile(src, "audit_extrapolate.py", "exec"), ns)
curves = ns["curves"]


def geo_from(i8, i16, i32):
    inc1, inc0 = i32 - i16, i16 - i8
    r = min(inc1 / inc0 if inc0 > 0 else 0.0, 0.999)
    return lambda u: i32 + inc1 * r * (1 - r ** math.log2(u / 32768)) / (1 - r), r


print("cell view | obs i64 d64 | G: pred i64 d64 (r) | power | satexp | hill   (pred i64 / d64)")
errs = {k: [] for k in ("G", "power", "satexp", "hill")}
for (s, f, d, p), c in sorted(curves.items(), key=lambda kv: (int(kv[0][0]), int(kv[0][1]), kv[0][2], kv[0][3])):
    if float(f) / float(s) < 1:
        continue
    obs64, obs_d = c[65536], c[65536] - c[32768]
    g, r = geo_from(c[8192], c[16384], c[32768])
    window = sorted((u, y) for u, y in c.items() if 16384 <= u <= 32768)
    hillw = sorted((u, y) for u, y in c.items() if 4096 <= u <= 32768)
    out = {"G": (g(65536), g(65536) - c[32768])}
    if len(window) >= 3:
        for name, fit, w in (("power", ns["fit_power"], window), ("satexp", ns["fit_exp"], window)):
            m = fit(w)
            out[name] = (m[1](65536), m[1](65536) - m[1](32768)) if m else (float("nan"), float("nan"))
    m = ns["fit_hill"](hillw)
    out["hill"] = (m[1](65536), m[1](65536) - m[1](32768))
    for k, v in out.items():
        errs[k].append((s, f, v[0] - obs64, v[1] - obs_d))
    cols = " | ".join(f"{k}: {v[0]:.3f}/{v[1]:.3f}" for k, v in out.items())
    print(f"{s}x{f} d{d}{p} | obs {obs64:.3f}/{obs_d:.3f} | r={r:.2f} {cols}")
print("\nmean signed error of predicted d(65,536) minus observed, by family and cell (negative = predicts faster saturation than seen):")
for k, v in errs.items():
    by = {}
    for s, f, e64, ed in v:
        by.setdefault(f"{s}x{f}", []).append(ed)
    print(f"  {k:7s} " + "  ".join(f"{c}:{sum(x) / len(x):+.3f}" for c, x in by.items()))
