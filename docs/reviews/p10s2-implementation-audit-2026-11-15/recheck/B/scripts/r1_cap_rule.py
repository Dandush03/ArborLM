"""Re-check B, R1: the cap rule and the rung rule recomputed with my own code and compared with studies.p10s2.budget (object under test, imported only for its decisions).

My model (written from ADR-0022 13.1/13.3 and the addenda of 2026-11-15, not from budget.py):
  cells per replicate: ST1 x2, MAF x2, MII x2, MSEQ x2, MJOINT x1 (2U), ETABLE x2, MAGOLD x2, LORA1 x2, LSEQ x2, LJOINT x1 (2U) = 18
  store-type groups (E-table included, ruling B-M7): rate at the calibrated layer for U = 2,000; the slower of L4 and L12 for U = 1,000
  per-process start-up (the implementation's documented reading; the ADR has none): one per training cell, one per scored cell, one for the gates stage
  scoring per replicate: 18 x (panel + start-up) + extras + 10 combined arm-cells (addendum section 10); once: fixed + combined Stage 0 + timing
  recomputation = one repetition of every scoring row, timing included (ruling B-M7)
  analysis and report: rehearsed seconds, each at least 30 s (so 2x is the 60 s floor of the frozen caps; ruling on the reserve)
  R = training + scoring + (gates2 + start-up) + recomputation + analysis/report
Rule (lead's ruling of 2026-11-15): cap = 36 if P + 2 R1 <= 36; else the smallest whole hour h <= 72 with P + 2 R1 <= h; else 72.
  Rung = first of (4,2000), (3,2000), (4,1000), (3,1000) with P + 2R <= cap; else NOT STARTED: BUDGET. Memory is held fine here (peaks 0).
Usage: python r1_cap_rule.py <pinned tree> <out.json>
"""

import itertools
import json
import math
import random
import sys
from pathlib import Path

PIN = Path(sys.argv[1])
sys.path.insert(0, str(PIN))
from studies.p10s2 import budget  # noqa: E402  (object under test)

CELLS = [("ST1", 2), ("MAF", 2), ("MII", 2), ("MSEQ", 2), ("MJOINT", 1), ("ETABLE", 2), ("MAGOLD", 2), ("LORA1", 2), ("LSEQ", 2), ("LJOINT", 1)]
STORE = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "ETABLE", "MAGOLD")
LORA = ("LORA1", "LSEQ", "LJOINT")
RUNGS = [(4, 2000), (3, 2000), (4, 1000), (3, 1000)]


def my_R(n: int, u: int, x: dict) -> float:
    ovh = x["ovh"]
    train = 0.0
    for g, k in CELLS:
        upd = 2 * u if g in ("MJOINT", "LJOINT") else u
        if g in STORE:
            rate = max(x["store"][g][4], x["store"][g][12]) if u == 1000 else x["store"][g][x["cal"]]
        else:
            rate = x["lora"][g]
        train += k * (upd * rate + ovh)
    train *= n
    scoring = n * (18 * (x["panel"] + ovh) + x["extra"] + 10 * x["comb"]) + x["fixed"] + x["comb0"] + x["timing"]
    gates2 = x["gates2"] + ovh
    ar = max(x["an"], 30.0) + max(x["rep"], 30.0)
    return (train + scoring + gates2 + scoring + ar) / 3600.0


def my_rule(P: float, x: dict) -> tuple[float, str]:
    R = {k: my_R(*k, x) for k in RUNGS}
    need = P + 2 * R[RUNGS[0]]
    if need <= 36.0:
        cap = 36.0
    else:
        h = 37
        while h <= 72 and P + 2 * R[RUNGS[0]] > h:
            h += 1
        cap = float(h) if h <= 72 else 72.0
    for i, k in enumerate(RUNGS, 1):
        if P + 2 * R[k] <= cap:
            return cap, f"rung {i}"
    return cap, "NOT STARTED: BUDGET"


def to_rates(x: dict) -> "budget.Rates":
    us = {f"{g}@L{ly}": x["store"][g][ly] for g in STORE for ly in (4, 12)}
    us.update({g: x["lora"][g] for g in LORA})
    return budget.Rates(update_seconds=us, calibrated_layer=x["cal"], panel_seconds=x["panel"], replicate_extra_seconds=x["extra"], fixed_seconds=x["fixed"], timing_seconds=x["timing"],
                        gates2_seconds=x["gates2"], task_overhead_seconds=x["ovh"], combined_cell_seconds=x["comb"], combined_stage0_seconds=x["comb0"], analysis_seconds=x["an"], report_seconds=x["rep"])


def impl_rule(P: float, x: dict) -> tuple[float, str, float]:
    rates = to_rates(x)
    cap = budget.computed_cap(P, rates)
    dec = budget.rehearsal_rule(P, rates, cap)
    return cap, dec.outcome, budget.registered_run_seconds(4, 2000, rates)["total"] / 3600.0


def make_x(rng: random.Random | None, scale: float, cal: int, l12_ratio: float, etab_ratio: float, ovh: float, an: float) -> dict:
    """Rates in seconds per update at the ADR's projected midpoints (5-10 min per store unit of 2,000 -> 0.15-0.3 s; LoRA 8-15 min -> 0.24-0.45 s), times ``scale``."""
    j = (lambda: rng.uniform(0.8, 1.25)) if rng else (lambda: 1.0)
    base_store = 0.225 * scale
    store = {}
    for g in STORE:
        b = base_store * j() * (1.0 if g != "MII" else 2.0)
        if g == "ETABLE":
            b *= 0.5
        r4 = b
        r12 = b * l12_ratio * (etab_ratio if g == "ETABLE" else 1.0)
        store[g] = {4: r4, 12: r12}
    lora = {g: 0.35 * scale * j() for g in LORA}
    return {"store": store, "lora": lora, "cal": cal, "panel": 200.0 * scale * j(), "extra": 2700.0 * scale * j(), "fixed": 800.0 * scale * j(), "timing": 300.0 * scale * j(),
            "gates2": 900.0 * scale * j(), "ovh": ovh, "comb": 280.0 * scale * j(), "comb0": 280.0 * scale * j(), "an": an, "rep": an / 3}


def main() -> None:
    out_path = Path(sys.argv[2])
    rows, mism = 0, []
    outcomes: dict[str, int] = {}
    caps: dict[float, int] = {}
    for scale, P, cal, l12, er, ovh, an in itertools.product([0.3, 0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 2.6, 3.5], [0.0, 0.5, 2.0, 3.5, 5.0, 7.0, 12.0, 30.0, 71.5, 80.0], [4, 12], [0.8, 1.0, 1.4], [0.7, 1.3], [0.0, 25.0], [5.0, 400.0]):
        x = make_x(None, scale, cal, l12, er, ovh, an)
        mine = my_rule(P, x)
        cap, outc, _ = impl_rule(P, x)
        rows += 1
        outcomes[mine[1]] = outcomes.get(mine[1], 0) + 1
        caps[mine[0]] = caps.get(mine[0], 0) + 1
        if (cap, outc) != mine:
            mism.append({"P": P, "scale": scale, "cal": cal, "mine": mine, "impl": [cap, outc]})
    rng = random.Random(229501)
    rmis, rrows = [], 0
    for _ in range(6000):
        x = make_x(rng, rng.uniform(0.2, 4.0), rng.choice([4, 12]), rng.uniform(0.6, 1.6), rng.uniform(0.5, 1.8), rng.uniform(0.0, 60.0), rng.uniform(0.0, 900.0))
        P = rng.uniform(0.0, 20.0)
        mine = my_rule(P, x)
        cap, outc, _ = impl_rule(P, x)
        rrows += 1
        if (cap, outc) != mine:
            rmis.append({"P": P, "mine": mine, "impl": [cap, outc]})
    # boundary: choose P so that P + 2 R1 lands on, just above, and 5e-13 h above a whole hour
    bnd = []
    x = make_x(None, 0.25, 4, 1.0, 1.0, 25.0, 5.0)
    r1 = budget.registered_run_seconds(4, 2000, to_rates(x))["total"] / 3600.0
    for target in (40.0, 40.0 + 5e-13, 40.0 + 1e-9, 72.0, 72.0 + 5e-13, 36.0 + 5e-13, 37.0 + 5e-13):
        P = target - 2 * r1
        need = P + 2 * r1
        cap, outc, _ = impl_rule(P, x)
        mine = my_rule(P, x)
        bnd.append({"target_need": target, "P": P, "need_as_computed": need, "need_minus_floor": need - math.floor(need), "impl": [cap, outc], "mine": list(mine), "rung1_fits_at_impl_cap": need <= cap, "agree": (cap, outc) == mine})
    res = {"grid_points": rows, "grid_mismatches": len(mism), "grid_mismatch_examples": mism[:10], "grid_outcomes_mine": outcomes, "grid_caps_mine": {str(k): v for k, v in sorted(caps.items())},
           "random_points": rrows, "random_mismatches": len(rmis), "random_mismatch_examples": rmis[:10], "boundary": bnd}
    out_path.write_text(json.dumps(res, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in res.items() if k != "boundary"}, sort_keys=True)[:1500])
    for b in bnd:
        print(b)


if __name__ == "__main__":
    main()
