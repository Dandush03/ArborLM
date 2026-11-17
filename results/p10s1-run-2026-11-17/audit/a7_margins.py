# ruff: noqa
"""Near-threshold scan (tie hazard): every capacity-panel quantity within 0.02 of a registered threshold that its verdict reads."""
import json, os
H = os.path.dirname(__file__)
cap = json.load(open(f"{H}/a2_capacity.json"))
TH = {"d_mu": (0.5, -0.5, 0.25, -0.25), "d_mc": (0.5,), "d_sat": (0.5,), "d_full": (-0.5, 0.25, -0.25), "i_s_up": (4.5,), "i_s_run": (4.0,), "a_l_up": (0.5,), "gain_s": (0.10,)}
for arm, steps in cap["steps"].items():
    for s, st in steps.items():
        for rp in st["reps"]:
            for p, d in rp["panels"].items():
                for k, ths in TH.items():
                    x = d.get(k)
                    if x is None: continue
                    for t in ths:
                        if abs(x - t) < 0.02:
                            print(f"{arm} {s} r{rp['rep']} {p} verdict {d['v']}: {k}={x} within 0.02 of {t}")
