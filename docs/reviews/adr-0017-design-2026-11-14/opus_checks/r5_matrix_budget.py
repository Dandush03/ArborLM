"""R5 (re-check of rev 2) - matrix recount, training-time arithmetic at E = 32/64/128 with 2 and 3 workers,
registered reductions, permutation-test resolution. Arithmetic only, no timing is measured.

Per-update planning allowances are RESOURCE_BUDGET.md rev 2's own (flat 0.013/0.04/0.13 s, tree 0.10 s,
dense 64K 0.39 s, R2 0.035 s). Dense at 4K/16K is not given there; 3x flat is assumed (as for 64K).
Key-32 cells are costed both at the budget's flat rate and at 2x flat (sensitivity). Updates: U_N = F*E/128;
4,096-slot cells and fixed-fact cells run to U_16K (rev 2 section 5.5; budget table). Lane D: phase A and
phase B 4,096 facts each; replay doubles rows per update; joint bound 8,192 facts. Evaluation is the
budget's fixed 3 serial hours over 4 simulation workers (0.75 h wall).
"""

import json

FLAT = {4096: 0.013, 16384: 0.04, 65536: 0.13}
TREE, R2 = 0.10, 0.035
DENSE = {4096: 0.039, 16384: 0.12, 65536: 0.39}
FACTS = {4096: 2048, 16384: 8192, 65536: 32768}


def cells(key32_factor: float) -> list[tuple[str, int, int, float, str]]:
    """(block, size, count, seconds per update, update-kind)"""
    c = []
    for n in FACTS:
        c += [("A1", n, 3, FLAT[n], "prop"), ("A2", n, 3, TREE, "prop"),
              ("A5-R1", n, 2, FLAT[n], "prop"), ("A5-R2", n, 2, R2, "prop"),
              ("A8", n, 2, DENSE[n], "prop"), ("A10", n, 2, FLAT[n], "prop")]
    c += [("A3", 16384, 2, TREE, "prop")]
    c += [("A4", n, 2, FLAT[n], "fixed") for n in (16384, 65536)]
    c += [("A5b", n, 2, FLAT[n], "prop") for n in (16384, 65536)]
    c += [("A6", 16384, 4, TREE, "prop")]
    c += [("A7", n, 4, FLAT[n] * key32_factor, "prop") for n in (16384, 65536)]
    c += [("B1-flat", 16384, 4, FLAT[16384], "prop"), ("B1-tree", 16384, 4, TREE, "prop"),
          ("C1-flat", 16384, 4, FLAT[16384], "prop"), ("C1-tree", 16384, 4, TREE, "prop")]
    c += [("D1-flat", 16384, 2, FLAT[16384], "laneD"), ("D1-tree", 16384, 2, TREE, "laneD"),
          ("D1-dense", 16384, 2, DENSE[16384], "laneD")]
    c += [("D2-flat-seq", 16384, 2, FLAT[16384], "laneD"), ("D2-flat-memonly", 16384, 2, FLAT[16384], "laneD"),
          ("D2-tree-seq", 16384, 2, TREE, "laneD"), ("D2-flat-replay", 16384, 2, 2 * FLAT[16384], "laneD"),
          ("D2-dense-seq", 16384, 2, DENSE[16384], "laneD"), ("D2-dense-replay", 16384, 2, 2 * DENSE[16384], "laneD"),
          ("D2-joint", 16384, 2, FLAT[16384], "joint")]
    return c


def updates(n: int, kind: str, e: int) -> int:
    u16 = FACTS[16384] * e // 128
    if kind == "laneD":
        return 4096 * e // 128
    if kind == "joint":
        return 8192 * e // 128
    if n == 4096 or kind == "fixed":
        return u16
    return FACTS[n] * e // 128


def serial_hours(cs: list[tuple[str, int, int, float, str]], e: int, drop: set[tuple[str, int]] | None = None,
                 drop_counts: dict[tuple[str, int], int] | None = None) -> tuple[float, int]:
    total, ncell = 0.0, 0
    for block, n, count, spu, kind in cs:
        if drop and (block, n) in drop:
            continue
        k = count - (drop_counts or {}).get((block, n), 0)
        total += k * updates(n, kind, e) * spu
        ncell += k
    return total / 3600, ncell


def main() -> None:
    cs = cells(1.0)
    by_size: dict[int, int] = {}
    for _, n, k, _, _ in cs:
        by_size[n] = by_size.get(n, 0) + k
    print(json.dumps({"cells_total": sum(by_size.values()), "by_size": by_size}))
    for factor in (1.0, 2.0):
        cs = cells(factor)
        for e in (32, 64, 128):
            h, ncell = serial_hours(cs, e)
            for workers in (2, 3):
                wall = h / workers + 0.75
                print(json.dumps({"key32_cost_factor": factor, "E": e, "cells": ncell, "serial_training_h": round(h, 2),
                                  "workers": workers, "projected_wall_h": round(wall, 2),
                                  "twice_projection_h": round(2 * wall, 2), "fits_8h_with_2x_headroom": 2 * wall <= 8}))
    # registered reductions 1-3 (cumulative), and 4 at E = 128
    cs = cells(1.0)
    red = [("1 drop B102 64K", {("A1", 65536): 1, ("A2", 65536): 1}),
           ("2 drop A7 64K", {("A7", 65536): 4}),
           ("3 drop dense seed 64K", {("A8", 65536): 1})]
    acc: dict[tuple[str, int], int] = {}
    for name, d in red:
        acc.update(d)
        for e in (32, 64, 128):
            h, ncell = serial_hours(cs, e, drop_counts=acc)
            for workers in (2, 3):
                wall = h / workers + 0.75
                print(json.dumps({"after_reductions_up_to": name, "E": e, "cells": ncell, "serial_training_h": round(h, 2),
                                  "workers": workers, "projected_wall_h": round(wall, 2), "fits_8h_2x": 2 * wall <= 8}))
    drop4 = {("A4", 65536), ("A5-R1", 65536), ("A5b", 65536), ("A7", 65536), ("A10", 65536)}
    h, ncell = serial_hours(cs, 128, drop=drop4, drop_counts=acc)
    for workers in (2, 3):
        wall = h / workers + 0.75
        print(json.dumps({"after_reductions_1_to_4": True, "E": 128, "cells": ncell, "serial_training_h": round(h, 2),
                          "workers": workers, "projected_wall_h": round(wall, 2), "fits_8h_2x": 2 * wall <= 8}))
    # permutation-test resolution (section 4.6 item 2)
    b = 10_000
    p_min = 1 / (b + 1)
    for k in (8, 10, 40, 80):
        print(json.dumps({"permutations": b, "bonferroni_tests_k": k, "min_attainable_p": round(p_min, 7),
                          "threshold_0.001/k": 0.001 / k, "test_can_ever_reject": p_min < 0.001 / k,
                          "permutations_needed_for_rejection_possible": int(1000 * k)}))
    # G2 count (section 8.1): distinct size x track combinations
    combos = [(4096, "prop"), (16384, "prop"), (65536, "prop"), (16384, "fixed"), (65536, "fixed")]
    print(json.dumps({"size_track_combos_distinct": len(combos), "x_panels": 2, "x_controls(no-memory, unseen)": 2,
                      "tests": len(combos) * 2 * 2, "if_4K_fixed_counted_separately": 6 * 2 * 2,
                      "rev2_states": 16}))


if __name__ == "__main__":
    main()
