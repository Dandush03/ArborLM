"""Audit B, check B1: recompute the rehearsal rung rule and the cap extension of ADR-0022 section 13.3 with the auditor's own code
and compare with studies.p10s2.budget (the object under test; imported only to obtain its decisions).

Own model (written from the ADR text, not from budget.py):
  cells per replicate (section 13.1): ST1 x2, MAF x2, MII x2, MSEQ x2, MJOINT x1 (2U), ETABLE x2, MAGOLD x2, LORA1 x2, LSEQ x2, LJOINT x1 (2U)
  store-type (the 16 store-type units of 13.1): ST1, MAF, MII, MSEQ, MJOINT, ETABLE, MAGOLD; LoRA-type: LORA1, LSEQ, LJOINT
  U = 2,000: store-type at the calibrated layer; U = 1,000: the slower of L = 4 and L = 12 for every store-type cell (13.3)
  R = training + every scoring (+ timing) + second gates stage + recomputation
  recomputation: ADR text = 'one repetition of the three scoring rows (an upper estimate, because the timing benchmark is not repeated)'
  Per-process start-up: the ADR has none; to isolate rule logic from rate model the IMPL-MODEL variant adds the implementation's documented
  per-process overhead (one per training cell, one per scored cell, one for the second gates stage).
Rule: rung 1 at 36 if P + 2R1 <= 36; else cap = smallest whole hour >= P + 2R1 if <= 72 (rung 1); else registered order against 72; else NOT STARTED: BUDGET.
"""

import itertools
import json
import math
import sys
from pathlib import Path

PIN = Path(sys.argv[1])
sys.path.insert(0, str(PIN))
from studies.p10s2 import budget  # noqa: E402  (object under test)
from studies.p10s2.ledger import Ledger  # noqa: E402

CELLS = [("ST1", 2), ("MAF", 2), ("MII", 2), ("MSEQ", 2), ("MJOINT", 1), ("ETABLE", 2), ("MAGOLD", 2), ("LORA1", 2), ("LSEQ", 2), ("LJOINT", 1)]
STORE = {"ST1", "MAF", "MII", "MSEQ", "MJOINT", "ETABLE", "MAGOLD"}
DOUBLE = {"MJOINT", "LJOINT"}
RUNGS = [(4, 2000), (3, 2000), (4, 1000), (3, 1000)]


def own_R(n, u, rr, *, model):
    """rr: dict of own rate inputs. model: 'impl' (implementation's two readings), 'adr_etable' (E-table uses the slower layer at U=1,000),
    'adr_recomp' (recomputation includes the timing row, as the ADR's upper estimate), 'adr_noovh' (no per-process start-up)."""
    ovh = 0.0 if model == "adr_noovh" else rr["ovh"]
    train = 0.0
    for g, k in CELLS:
        upd = 2 * u if g in DOUBLE else u
        if g in STORE:
            if g == "ETABLE" and model != "adr_etable" and not (u == 2000):
                rate = rr["etable_at_cal"]  # the implementation's reading: one E-table rate, at the calibrated layer
            elif u == 1000:
                rate = max(rr["store"][g][4], rr["store"][g][12])
            else:
                rate = rr["store"][g][rr["cal"]]
        else:
            rate = rr["lora"][g]
        train += k * (upd * rate + ovh)
    train *= n
    scoring = n * (18 * (rr["panel"] + ovh) + rr["extra"]) + rr["fixed"] + rr["timing"]
    gates2 = rr["gates2"] + ovh
    recomp = scoring if model == "adr_recomp" else scoring - rr["timing"]
    return (train + scoring + gates2 + recomp) / 3600.0


def own_decision(P, rr, model):
    R = {k: own_R(*k, rr, model=model) for k in RUNGS}
    need = P + 2 * R[RUNGS[0]]
    if need <= 36:
        return "rung 1", 36.0
    if need <= 72:
        return "rung 1", float(math.ceil(need))
    for i, k in enumerate(RUNGS, 1):
        if P + 2 * R[k] <= 72:
            return f"rung {i}", 72.0
    return "NOT STARTED: BUDGET", 72.0


def impl_decision(P, rr, tmp: Path):
    us = {}
    for g in STORE - {"ETABLE"}:
        for ly in (4, 12):
            us[f"{g}@L{ly}"] = rr["store"][g][ly]
    us["ETABLE"] = rr["etable_at_cal"]
    for g in ("LORA1", "LSEQ", "LJOINT"):
        us[g] = rr["lora"][g]
    rates = budget.Rates(update_seconds=us, calibrated_layer=rr["cal"], panel_seconds=rr["panel"], replicate_extra_seconds=rr["extra"], fixed_seconds=rr["fixed"],
                         timing_seconds=rr["timing"], gates2_seconds=rr["gates2"], task_overhead_seconds=rr["ovh"])
    raise_path = tmp / "cap_raise.json"
    if raise_path.exists():
        raise_path.unlink()
    led = Ledger(tmp / "ledger.jsonl")
    if led.path.exists():
        led.path.unlink()
    led.record("rehearsal", P * 3600.0)
    prop = budget.propose_raise(led.total_hours(), rates)
    if prop is not None:
        budget.record_raise(prop, raise_path, led)
    cap = budget.effective_cap(raise_path)
    d = budget.rehearsal_rule(led.total_hours(), rates, cap)
    return d.outcome, cap


def main():
    tmp = Path(sys.argv[2])
    tmp.mkdir(parents=True, exist_ok=True)
    rows = []
    MODELS = ("impl", "adr_etable", "adr_recomp", "adr_noovh")
    mism = {m: 0 for m in MODELS}
    examples = {m: [] for m in MODELS}
    n = 0
    # base per-unit rates (seconds per update) at the fast end of the ADR projection, scaled by s
    for s, P, cal, l12_ratio, et_ratio, ovh in itertools.product(
        [0.15 * 1.1 ** k for k in range(40)], [0.5, 3.5, 7.0, 12.0], [4, 12], [0.6, 0.8, 1.0, 1.25], [0.6, 1.0, 1.4], [0.0, 30.0]):
        st4 = 0.15 * s
        store = {g: {4: st4 * (2.0 if g == "MII" else 1.0), 12: st4 * l12_ratio * (2.0 if g == "MII" else 1.0)} for g in STORE}
        rr = {"cal": cal, "store": store, "etable_at_cal": store["ETABLE"][cal], "lora": {"LORA1": 0.24 * s, "LSEQ": 0.24 * s, "LJOINT": 0.30 * s},
              "panel": 96 * s, "extra": 0.9 * 3600 * s / 1.0, "fixed": 0.3 * 3600 * s, "timing": 0.05 * 3600 * s, "gates2": 0.05 * 3600 * s, "ovh": ovh}
        # make the E-table rate at the non-calibrated layer differ by et_ratio, so the ADR's 'slower of L4/L12' bites
        other = 12 if cal == 4 else 4
        rr["store"]["ETABLE"][other] = rr["store"]["ETABLE"][cal] * et_ratio
        impl = impl_decision(P, rr, tmp)
        for model in MODELS:
            own = own_decision(P, rr, model)
            if own != impl:
                mism[model] += 1
                if len(examples[model]) < 8:
                    examples[model].append({"s": round(s, 4), "P": P, "cal": cal, "l12_ratio": l12_ratio, "etable_other_ratio": et_ratio, "ovh": ovh, "own": own, "impl": impl})
        n += 1
    out = {"grid_points": n, "mismatches": mism, "examples": examples}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
