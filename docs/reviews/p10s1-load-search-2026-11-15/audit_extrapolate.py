"""Auditor's extrapolation stress test for ADR-0021 s24 (calibration curves; NOT measurements).

Input: audit_curves.json written by audit_curves.py (auditor's own recomputation from raw eval records).
Pure Python; no project imports. Usage: python3 -I audit_extrapolate.py
For every view (cell x draw x panel) several curve families are fitted to the post-onset snapshots and
evaluated on the amendment's candidate grid. Reported: first candidate where the s8.2 rule holds
(d(U) = i(U) - i(U/2) <= 0.10 and i(U) <= 4.0), the level there, and U_L under the lead's ruling 2
(loaded at two consecutive candidates; U_L the second). Also when i first exceeds 4.0.
"""

import json
import math
from pathlib import Path

HERE = Path(__file__).parent
raw = json.loads((HERE / "audit_curves.json").read_text())
curves = {tuple(k.split("|")): {int(u): v for u, v in c.items()} for k, c in raw.items()}

CANDS = [131072, 196608, 262144, 393216, 524288, 786432, 1048576, 1572864, 2097152, 3145728, 4194304]
CEIL = {4096: 524288, 16384: 262144}


def lstsq2(xs, ys):
    """y = c + b x, least squares; returns c, b, sse."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx > 0 else 0.0
    c = my - b * mx
    return c, b, sum((c + b * x - y) ** 2 for x, y in zip(xs, ys))


def fit_power(pts):
    """i = c - A u^-alpha (alpha > 0): grid alpha, LS for (c, -A)."""
    best = None
    for k in range(1, 400):
        a = 0.01 * k
        xs = [u ** -a for u, _ in pts]
        c, b, sse = lstsq2(xs, [y for _, y in pts])
        if b >= 0:  # need -A < 0  -> increasing curve
            continue
        if best is None or sse < best[0]:
            best = (sse, a, c, b)
    if best is None:
        return None
    _, a, c, b = best
    return ("power", lambda u: c + b * u ** -a, {"alpha": a, "asym": c, "r_per_doubling": 2 ** -a})


def fit_exp(pts):
    """i = c - B exp(-u/tau): grid tau, LS."""
    best = None
    for k in range(0, 600):
        tau = 4096 * 1.02 ** k
        xs = [math.exp(-u / tau) for u, _ in pts]
        c, b, sse = lstsq2(xs, [y for _, y in pts])
        if b >= 0:
            continue
        if best is None or sse < best[0]:
            best = (sse, tau, c, b)
    if best is None:
        return None
    _, tau, c, b = best
    return ("satexp", lambda u: c + b * math.exp(-u / tau), {"tau": tau, "asym": c})


def fit_hill(pts):
    """i = c / (1 + (u50/u)^k): logistic in log u. Grid (k, u50), LS for c (through origin)."""
    best = None
    for kk in range(5, 400, 5):
        k = kk / 100
        for j in range(0, 300):
            u50 = 1024 * 1.03 ** j
            xs = [1 / (1 + (u50 / u) ** k) for u, _ in pts]
            sxx = sum(x * x for x in xs)
            c = sum(x * y for x, (_, y) in zip(xs, pts)) / sxx
            sse = sum((c * x - y) ** 2 for x, (_, y) in zip(xs, pts))
            if best is None or sse < best[0]:
                best = (sse, k, u50, c)
    _, k, u50, c = best
    return ("hill", lambda u: c / (1 + (u50 / u) ** k), {"k": k, "u50": u50, "asym": c, "r_tail": 2 ** -k})


def geometric(pts, relax=False):
    """Draft's G (or S with relax): from the last snapshot, each further doubling adds r x previous increment;
    r = last observed ratio of doubling increments (sqrt(r) under S). Interpolated in log2(u) between doublings."""
    d = dict(pts)
    i65, i32, i16 = d[65536], d[32768], d[16384]
    inc1, inc0 = i65 - i32, i32 - i16
    r = inc1 / inc0 if inc0 > 0 else 0.0
    if relax:
        r = math.sqrt(r)
    r = min(r, 0.999)

    def f(u):
        x = math.log2(u / 65536)
        if x <= 0:
            return i65 - inc1 * (-x)  # not used
        # continuous version: increment over [0, x] doublings = inc1 * sum_{j=1..x} r^j (geometric in continuous x)
        return i65 + inc1 * r * (1 - r ** x) / (1 - r) if r < 1 else i65 + inc1 * x

    return ("G-sqrt" if relax else "G", f, {"r": r, "asym": i65 + inc1 * r / (1 - r)})


def loglin(pts):
    """No deceleration beyond the last doubling: i = i65 + inc_last * log2(u/65536)."""
    d = dict(pts)
    inc1 = d[65536] - d[32768]
    return ("loglin", lambda u: d[65536] + inc1 * math.log2(u / 65536), {"inc": inc1})


def read(f, slots):
    """first candidate passing the s8.2 rule; U_L under two consecutive passes; first U with i > 4.0."""
    first = None
    passes = []
    over4 = None
    for U in CANDS:
        iu, ih = f(U), f(U // 2)
        dd = iu - ih
        ok = dd <= 0.10 + 1e-12 and iu <= 4.0 + 1e-12
        passes.append((U, ok, iu, dd))
        if iu > 4.0 and over4 is None:
            over4 = U
    for k, (U, ok, iu, dd) in enumerate(passes):
        if ok and first is None:
            first = (U, iu, dd)
    ul = None
    for k in range(len(passes) - 1):
        if passes[k][1] and passes[k + 1][1]:
            ul = (passes[k + 1][0], passes[k + 1][2], passes[k + 1][3])
            break
    return first, ul, over4, passes


def fmt(x):
    if x is None:
        return "never(<=4M)"
    return f"{x[0]}@{x[1]:.2f}(d={x[2]:.3f})"


def views(slots, facts):
    return [curves[(str(slots), str(facts), str(d), p)] for d in (1, 2) for p in ("A", "B")]


def interp_load6():
    """Synthetic load-6 views at 4,096 slots: per snapshot, i interpolated linearly in log2(load) between
    load 4 and load 8 of the same draw/panel (weight log2(6/4)=0.585 toward load 8). A guess, not data."""
    w = math.log2(6 / 4)
    out = []
    for d in (1, 2):
        for p in ("A", "B"):
            a, b = curves[("4096", "16384", str(d), p)], curves[("4096", "32768", str(d), p)]
            out.append({u: (1 - w) * a[u] + w * b[u] for u in a})
    return out


def interp_load6_bits():
    """Alternative load-6 guess: retained bits I = i x F interpolated linearly in load between load 4 and 8, i = I / 24,576."""
    out = []
    for d in (1, 2):
        for p in ("A", "B"):
            a, b = curves[("4096", "16384", str(d), p)], curves[("4096", "32768", str(d), p)]
            out.append({u: (0.5 * a[u] * 16384 + 0.5 * b[u] * 32768) / 24576 for u in a})
    return out


def collapse_l8():
    """Data-driven shape transfer: i_L8(2u) ~= s x i_L4(u) at 4,096 slots (s fitted per view from the last three
    overlaps); predicts L8 beyond 65,536 from L4's own measured curve and its G extrapolation."""
    out = []
    for d in (1, 2):
        for p in ("A", "B"):
            l4, l8 = curves[("4096", "16384", str(d), p)], curves[("4096", "32768", str(d), p)]
            ratios = [l8[2 * u] / l4[u] for u in (8192, 16384, 32768)]
            out.append((ratios, l4, l8))
    return out


def main():
    cells = [(4096, 16384), (4096, 32768), (4096, 65536), (16384, 65536), (16384, 131072)]
    fams = ["G", "G-sqrt", "power", "satexp", "hill", "loglin"]
    print("Extrapolations from calibration curves (NOT measurements). Fit window: snapshots >= 16,384 (4K cells: 16K,24K,32K,48K,64K; 16K cells: 16K,32K,64K).")
    print("Columns: first candidate passing s8.2 (U@i(d)); U_L with two consecutive passes; first U with i>4.0; asymptote/params.")
    summary = {}

    def run(name, vs, slots):
        print(f"\n=== {name}  (ceiling U_max={CEIL[slots]})")
        for fam in fams:
            rows = []
            for v in vs:
                pts = sorted((u, y) for u, y in v.items() if u >= 16384)
                if fam == "G":
                    m = geometric(pts)
                elif fam == "G-sqrt":
                    m = geometric(pts, relax=True)
                elif fam == "power":
                    m = fit_power(pts)
                elif fam == "satexp":
                    m = fit_exp(pts)
                elif fam == "hill":
                    m = fit_hill(sorted((u, y) for u, y in v.items() if u >= 4096))
                else:
                    m = loglin(pts)
                if m is None:
                    rows.append(None)
                    continue
                _, f, par = m
                rows.append((read(f, slots), par, f))
            print(f"  [{fam}]")
            for r in rows:
                if r is None:
                    print("     no fit")
                    continue
                (first, ul, over4, passes), par, f = r
                ps = " ".join(f"{k}={v:.3g}" for k, v in par.items())
                i_at = " ".join(f"{U // 1024}K:{f(U):.2f}/{f(U) - f(U // 2):.3f}" for U in (131072, 196608, 262144, 393216, 524288))
                print(f"     first={fmt(first):28s} U_L={fmt(ul):28s} i>4 at {over4}  {ps}\n         i/d: {i_at}")
            summary[(name, fam)] = rows

    for s, f in cells:
        run(f"{s} slots, {f} facts (load {f / s:g})", views(s, f), s)
    run("4096 slots, 24576 facts (load 6) -- SYNTHETIC: i interpolated in log2(load) between L4 and L8", interp_load6(), 4096)
    run("4096 slots, 24576 facts (load 6) -- SYNTHETIC: retained bits interpolated", interp_load6_bits(), 4096)

    print("\n=== shape transfer L8(2u) ~ s * L4(u) at 4,096 slots")
    for ratios, l4, l8 in collapse_l8():
        s = ratios[-1]
        g = geometric(sorted((u, y) for u, y in l4.items() if u >= 16384))[1]
        pred = {U: s * g(U // 2) if U // 2 > 65536 else s * l4[U // 2] for U in (131072, 196608, 262144, 393216, 524288)}
        pred[65536] = l8[65536]
        pred[98304] = s * g(49152 * 1.0) if False else s * (l4[49152])
        dd = {U: pred[U] - pred[U // 2] for U in (131072, 196608, 262144, 393216, 524288) if U // 2 in pred}
        print(f"  s(8K,16K,32K)={[round(x, 3) for x in ratios]}  pred i: " + " ".join(f"{U // 1024}K:{pred[U]:.2f}" for U in sorted(pred)) + "  d: " + " ".join(f"{U // 1024}K:{v:.3f}" for U, v in dd.items()))


main()
