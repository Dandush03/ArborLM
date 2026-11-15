"""G1 - pure arithmetic for the confirmation check of ADR-0018 revision 2 (commit 649f76f).
No backbone, no study data, no training.

1. Matrix recount (section 7).
2. Parameter counts: BB block-0 attention (Block: qkv Linear(32, 96) + attn_out Linear(32, 32), both
   with bias); A4 / W7 extras; D7 widths from 256 h + 1 = 48 S + 4,609.
3. Exposures per fact at each candidate U (batch 16 contexts x 8 answer sites).
4. Section 8.1 step 2: enumerate all 3^4 raw-class patterns (W, P, F) over (panel A, B) x (seed 1801,
   1802) under three readings of "rows 2-4 applied to each panel separately give different results",
   and count the patterns whose class depends on the reading.
5. Ratio saturation: BEATS DENSE (r >= 1.10) and BACKBONE HURTS (>= 1.03) are unreachable once the
   denominator exceeds 1/1.10 and 1/1.03.
6. Backbone contrast "first match wins, otherwise CONTRIBUTES": count seed/panel-mixed grids that
   fall into CONTRIBUTES although at least one paired ratio is >= 1.03.
7. G2 interval (exact binomial central, level 1 - 0.001/8, around 1/32) per panel size, and a union
   bound on a constant "modal answer" predictor exceeding it.
8. Time projection at U = 16,384 (assumed per-update costs stated in the output).

Usage: uv run --locked python docs/reviews/adr-0018-design-2026-11-14/g1_confirm_checks.py
"""

import itertools
import json
import math


def matrix():
    core = {"16384": 9 * 2 + 4, "65536": 5 * 2, "4096": 4 * 2}
    bb = {"16384+65536": 3 * 2 * 2 + 1, "4096": 1 * 2}
    return {"core": core, "core_total": sum(core.values()), "bb": bb, "bb_total": sum(bb.values()),
            "total": sum(core.values()) + sum(bb.values()),
            "with_bb0_at_4096": sum(core.values()) + sum(bb.values()) + 2}


def params():
    bb = (32 * 96 + 96) + (32 * 32 + 32)
    w7_extra = 16 * 224 - 16 * 32
    a4_extra = 3 * 32 * 32
    d7 = {s: (48 * s + 4609 - 1) / 256 for s in (4096, 16384, 65536)}
    return {"bb_attention": bb, "w7_extra": w7_extra, "a4_extra": a4_extra, "d7_hidden": d7}


def exposures():
    out = {}
    for u in (2048, 4096, 8192, 16384):
        out[u] = {f: u * 16 * 8 / f for f in (2048, 8192, 32768)}
    return out


def step2(raw, reading):
    # raw[(panel, seed)] in {"W", "P", "F"}
    a = (raw[("A", 1)], raw[("A", 2)])
    b = (raw[("B", 1)], raw[("B", 2)])
    if reading == "per_seed":  # NOT REPLICATED if for some seed panel A != panel B
        nr = a[0] != b[0] or a[1] != b[1]
    elif reading == "panel_class":  # panel class = common raw class or MIXED
        pa = a[0] if a[0] == a[1] else "MIXED"
        pb = b[0] if b[0] == b[1] else "MIXED"
        nr = pa != pb
    elif reading == "panel_set":  # set of raw classes on each panel
        nr = set(a) != set(b)
    else:
        raise ValueError(reading)
    if nr:
        return "NOT REPLICATED"
    if a[0] != a[1] or b[0] != b[1]:
        return "INTERMEDIATE"
    return {"W": "WORKS", "P": "PARTIAL", "F": "FAILS"}[a[0]]


def enumerate_step2():
    readings = ("per_seed", "panel_class", "panel_set")
    differ = []
    tallies = {r: {} for r in readings}
    for combo in itertools.product("WPF", repeat=4):
        raw = dict(zip([("A", 1), ("A", 2), ("B", 1), ("B", 2)], combo, strict=True))
        cls = {r: step2(raw, r) for r in readings}
        for r in readings:
            tallies[r][cls[r]] = tallies[r].get(cls[r], 0) + 1
        if len(set(cls.values())) > 1:
            differ.append({"A": combo[:2], "B": combo[2:], **cls})
    works_differs = [d for d in differ if "WORKS" in (d["per_seed"], d["panel_class"], d["panel_set"])]
    return {"patterns": 81, "tallies": tallies, "patterns_whose_class_depends_on_reading": len(differ),
            "examples": differ[:6], "patterns_where_WORKS_depends_on_reading": len(works_differs)}


def saturation():
    return {"BEATS_DENSE_unreachable_if_dense_acc_above": round(1 / 1.10, 4),
            "HURTS_unreachable_if_state_arm_acc_above": round(1 / 1.03, 4),
            "example_arm_1.00_dense_0.92_r": round(1 / 0.92, 4),
            "example_arm_0.30_dense_0.28_r": round(0.30 / 0.28, 4)}


def contrast_mixed():
    grid = [x / 100 for x in range(90, 111)]
    n_mixed_to_contributes = 0
    total = 0
    for rs in itertools.product(grid, repeat=4):
        total += 1
        lo = min(rs)
        if lo >= 1.03 or lo >= 0.97:
            continue  # HURTS or ADDS NOTHING
        if max(rs) >= 0.97:  # CONTRIBUTES although some paired ratio says otherwise
            n_mixed_to_contributes += 1
    return {"grid": "paired ratios 0.90..1.10 step 0.01, 4 seed/panel pairs", "grid_points": total,
            "CONTRIBUTES_with_some_ratio_ge_0.97": n_mixed_to_contributes}


def binom_cdf_tail(n, p, k):
    # P(X >= k), computed in log space
    s = 0.0
    lp, lq = math.log(p), math.log1p(-p)
    for j in range(k, n + 1):
        s += math.exp(math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * lp + (n - j) * lq)
    return s


def g2():
    out = {}
    alpha = 0.001 / 8
    p = 1 / 32
    for n in (2048, 8192, 32768):
        mean = n * p
        hi = int(mean)
        while binom_cdf_tail(n, p, hi + 1) > alpha / 2:
            hi += 1
        tail = binom_cdf_tail(n, p, hi + 1)
        out[n] = {"upper_count": hi, "upper_acc": round(hi / n, 4),
                  "union_bound_modal_predictor_above": round(32 * tail, 5)}
    return out


def timing():
    # assumed s/update: 65,536 -> 0.05 (auditor's upper estimate), 16,384 -> 0.02, 4,096 -> 0.015
    per = {"65536": 0.05, "16384": 0.02, "4096": 0.015}
    cells = {"65536": 10, "16384": 22, "4096": 8}
    out = {}
    for u in (8192, 16384):
        s = sum(cells[k] * u * per[k] for k in cells)
        out[u] = {"core_serial_hours": round(s / 3600, 2), "six_workers_hours": round(s / 3600 / 6, 2)}
    cal = {"65536": 0.03, "16384": 0.015, "4096": 0.012}
    s = sum(6 * 16384 * cal[k] for k in cal)  # R1 + R2 x 3 runs per size
    out["calibration_16384_updates"] = {"assumed_s_per_update": cal, "serial_minutes": round(s / 60, 1),
                                        "six_workers_minutes": round(s / 60 / 6, 1)}
    return out


def main():
    for name, fn in (("matrix", matrix), ("params", params), ("exposures", exposures),
                     ("step2", enumerate_step2), ("saturation", saturation),
                     ("contrast_mixed", contrast_mixed), ("g2", g2), ("timing", timing)):
        print(json.dumps({name: fn()}))


if __name__ == "__main__":
    main()
