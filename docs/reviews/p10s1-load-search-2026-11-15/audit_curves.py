"""Auditor's independent recomputation of the P10-S1 load-calibration curves (ADR-0021 s24 check).

Reads only raw eval.json / train.json / manifest.json of the calibration run directory. Imports nothing
from arborlm or studies.* ; the information formula and chance interval are re-implemented here from
their written definitions (ADR-0021 s7.1 / G2: i = 5 - h2(e) - e log2 31, e = 1 - a_use, 0 at or below
the upper end of the exact binomial central interval of level 1 - 0.001/40 around 1/32).

Usage: python3 -I audit_curves.py <run_dir>
"""

import json
import math
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
ALPHA, TESTS, P0 = 0.001, 40, 1 / 32


def chance_high(n: int) -> int:
    tail = ALPHA / TESTS / 2
    lp, lq, top = math.log(P0), math.log1p(-P0), math.lgamma(n + 1)
    cum = 0.0
    for k in range(n, -1, -1):
        cum += math.exp(top - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq)
        if cum > tail:
            return k
    return 0


def chance_low(n: int) -> int:
    tail = ALPHA / TESTS / 2
    lp, lq, top = math.log(P0), math.log1p(-P0), math.lgamma(n + 1)
    cum = 0.0
    for k in range(0, n + 1):
        cum += math.exp(top - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * lp + (n - k) * lq)
        if cum > tail:
            return k
    return n


_CH: dict[int, int] = {}


def bits(useful: int, n: int) -> float:
    if n not in _CH:
        _CH[n] = chance_high(n)
    if useful <= _CH[n]:
        return 0.0
    a = useful / n
    e = 1 - a
    h2 = 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5 - h2 - e * math.log2(31)


def load_cells():
    out = {}
    for c in sorted((RUN / "cells").iterdir()):
        if not c.name.startswith("CAL_F-OQ") or not c.name.endswith("_y65536"):
            continue
        tr = json.loads((c / "train.json").read_text())
        series = {}
        for e in sorted((c / "eval").iterdir()):
            rec = json.loads((e / "eval.json").read_text())
            u = rec["update"]
            series[u] = {p: rec["reads"]["main"]["panels"][p] for p in ("A", "B")}
        out[(tr["slots"], tr["facts"], tr["draw"])] = {"train": tr, "series": series, "name": c.name}
    return out


def istar(curve: dict[int, float], limit: int) -> float:
    return max(v for u, v in curve.items() if u <= limit)


def main() -> None:
    print("chance highs:", {n: (chance_low(n), chance_high(n)) for n in (2048, 8192, 32768)})
    cells = load_cells()
    curves = {}
    print("\n## Part A: i(u) per view (bits per fact), i* = running max")
    for (s, f, d), c in sorted(cells.items()):
        for p in ("A", "B"):
            cur = {u: bits(v[p]["useful"], v[p]["n"]) for u, v in sorted(c["series"].items())}
            curves[(s, f, d, p)] = cur
            ns = {v[p]["n"] for v in c["series"].values()}
            print(f"{s:6d} {f:6d} L{f / s:<5g} d{d}{p} n={sorted(ns)} " + " ".join(f"{u}:{i:.3f}" for u, i in cur.items()))
    print("\n## Part B: doubling increments d(U)=i*(U)-i*(U/2) at U = 16K, 32K, 65K; ratio of last two")
    for k, cur in sorted(curves.items()):
        inc = {U: istar(cur, U) - istar(cur, U // 2) for U in (8192, 16384, 32768, 65536)}
        r = inc[65536] / inc[32768] if inc[32768] > 0 else float("nan")
        r2 = inc[32768] / inc[16384] if inc[16384] > 0 else float("nan")
        print(f"{k} i*65K={istar(cur, 65536):.4f} inc8K={inc[8192]:.3f} inc16K={inc[16384]:.3f} inc32K={inc[32768]:.3f} inc65K={inc[65536]:.3f}  r(32/16)={r2:.3f} r(65/32)={r:.3f}")
    print("\n## Part C: plateau / loaded by s8.2 read at every U with U/2 a snapshot")
    for (s, f) in sorted({(k[0], k[1]) for k in curves}):
        snaps = sorted(next(iter(cells[(s, f, 1)]["series"].keys() for _ in [0])))
        line = []
        for U in snaps:
            if U // 2 not in snaps:
                continue
            views = [curves[(s, f, d, p)] for d in (1, 2) for p in ("A", "B")]
            pl = all(istar(v, U) - istar(v, U // 2) <= 0.10 + 1e-12 for v in views)
            ld = pl and all(istar(v, U) <= 4.0 + 1e-12 for v in views)
            line.append(f"{U}:{'P' if pl else '-'}{'L' if ld else '-'}")
        print(f"{s} {f} L{f / s:g}: " + " ".join(line))
    # wall seconds per update
    man = json.loads((RUN / "calibrate" / "manifest.json").read_text())
    print("\n## Part D: manifest wall seconds and train.json wall/cpu per update (F-OQ load cells)")
    for t in man["tasks"]:
        lab = t["label"]
        tr = json.loads(Path(t["result_path"]).read_text())
        print(f"{lab:48s} manifest_s={t['seconds']:9.1f} train_wall={tr['wall_seconds']:9.1f} cpu={tr['cpu_seconds']:9.1f} run={tr['run_updates']} "
              f"man/upd={t['seconds'] / tr['run_updates']:.5f} wall/upd={tr['wall_seconds'] / tr['run_updates']:.5f} cpu/upd={tr['cpu_seconds'] / tr['run_updates']:.5f}")
    json.dump({"|".join(map(str, k)): v for k, v in curves.items()}, open(Path(__file__).with_name("audit_curves.json"), "w"), indent=0)


main()
