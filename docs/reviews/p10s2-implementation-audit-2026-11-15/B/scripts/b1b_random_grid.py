"""Audit B, check B1b: continuous random sample of the rung rule (own code vs studies.p10s2.budget), seeds: Python random 229501 (test range)."""
import json, random, sys
from pathlib import Path
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
import importlib.util
spec = importlib.util.spec_from_file_location("b1", str(Path(__file__).with_name("b1_rung_rule_recompute.py")))
b1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(b1)
rng = random.Random(229501)
tmp = Path(sys.argv[2]); tmp.mkdir(parents=True, exist_ok=True)
mism = {"impl": 0, "adr_etable": 0, "adr_recomp": 0}; ex = {k: [] for k in mism}; maxrel = 0.0; outcomes = {}
N = 4000
for _ in range(N):
    s = rng.uniform(0.1, 6.0); P = rng.uniform(0.2, 15.0); cal = rng.choice([4, 12]); l12 = rng.uniform(0.5, 1.5); etr = rng.uniform(0.3, 3.0); ovh = rng.uniform(0, 60)
    st4 = 0.15 * s
    store = {g: {4: st4 * (2.0 if g == "MII" else 1.0), 12: st4 * l12 * (2.0 if g == "MII" else 1.0)} for g in b1.STORE}
    other = 12 if cal == 4 else 4
    store["ETABLE"][other] = store["ETABLE"][cal] * etr
    rr = {"cal": cal, "store": store, "etable_at_cal": store["ETABLE"][cal], "lora": {"LORA1": 0.24 * s, "LSEQ": 0.24 * s, "LJOINT": 0.30 * s},
          "panel": 96 * s, "extra": 0.9 * 3600 * s, "fixed": 0.3 * 3600 * s, "timing": rng.uniform(0.01, 0.5) * 3600 * s, "gates2": 0.05 * 3600 * s, "ovh": ovh}
    impl = b1.impl_decision(P, rr, tmp)
    outcomes[impl[0]] = outcomes.get(impl[0], 0) + 1
    for m in mism:
        own = b1.own_decision(P, rr, m)
        if own != impl:
            mism[m] += 1
            if len(ex[m]) < 5: ex[m].append({"P": round(P, 3), "own": own, "impl": impl, "etable_ratio": round(etr, 3), "cal": cal})
    for n, u in b1.RUNGS:
        a, b = b1.own_R(n, u, rr, model="impl"), b1.own_R(n, u, rr, model="adr_etable")
        maxrel = max(maxrel, (b - a) / a)
print(json.dumps({"samples": N, "impl_outcomes": outcomes, "mismatches": mism, "examples": ex, "max_relative_R_increase_from_etable_rule": maxrel}, indent=1))
