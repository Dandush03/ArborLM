"""R11 (auditor, Opus 5.5, re-check): what the A4 Stage 2 projection would be under a tighter, still conservative bound than the registered rule
(ADR-0019 section 10: "A4's annealing phase at its most expensive measured rate"). k(t) decreases monotonically; for t < T_A/2, k(t) <= k_0 and for
t >= T_A/2, k(t) <= k(T_A/2) = the rehearsed midpoint. IF the cost per update is non-decreasing in k (measured: k=2048 0.137, k=128 0.0168, k=8 0.0128 s),
charging the first half at the k_0 rate and the second half at the midpoint rate is an upper bound. Descriptive only: the registered rule is the
ADR's and is not changed by this (PENDING LEAD REVIEW).

usage: r11_a4_bound.py REHEARSAL_RUN_DIR CALIBRATION_JSON
"""
import itertools
import json
import sys
from pathlib import Path

RUN, CAL = Path(sys.argv[1]), Path(sys.argv[2])
man = {t["label"]: t for t in json.loads((RUN / "rehearse" / "manifest.json").read_text())["tasks"]}
rates = {}
for d in sorted((RUN / "rehearsal").iterdir()):
    t = json.loads((d / "rehearsal.json").read_text()); e = json.loads((d / "rehearsal_evaluate.json").read_text()); task = man[d.name]
    rates[(t["arm"], t["slots"], t["phase"])] = {"spu": t["seconds_per_update"], "ev": e["evaluation_wall_seconds"], "ovh": max(0.0, task["seconds"] - t["wall_seconds"] - e["evaluation_wall_seconds"])}
H = json.loads(CAL.read_text())["hyper"]
last = {"A2": "post", "A4": "k8"}


def train_s(arm, n, tight):
    total = 4 * 8192
    ovh = rates[(arm, n, last.get(arm, "main"))]["ovh"]
    if arm == "A2":
        pre = round(H["u_pre"] * 4)
        return pre * rates[(arm, n, "pre")]["spu"] + (total - pre) * rates[(arm, n, "post")]["spu"] + ovh
    if arm == "A4":
        ta = total // 2
        k0, mid, k8 = (rates[(arm, n, p)]["spu"] for p in ("k0", "mid", "k8"))
        anneal = (ta // 2) * k0 + (ta - ta // 2) * mid if tight else ta * max(k0, mid)
        return anneal + (total - ta) * k8 + ovh
    return total * rates[(arm, n, "main")]["spu"] + ovh


def eval_s(arm, n):
    r = rates[(arm, n, last.get(arm, "main"))]
    return 2 * r["ev"] + r["ovh"]


def mk(xs):
    xs = sorted(xs, reverse=True)
    return sum(xs[i] for i in range(0, len(xs), 6))


for adv in [("A4",), *[c for c in itertools.combinations(("A5-C", "A5-D", "A4", "A2", "A1"), 2) if "A4" in c]]:
    arms = ["A0", *adv] + (["A1-S"] if any(a in ("A1", "A2") for a in adv) else [])
    cells = [(a, 16384) for a in arms for _ in range(8)] + [(a, 16384) for a in ("A6", "A7") for _ in range(4)]
    out = {}
    for tight in (False, True):
        out[tight] = mk([train_s(a, n, tight) for a, n in cells]) + mk([eval_s(a, n) for a, n in cells])
    print(f"{'+'.join(adv):8s}: registered rule {out[False]:7.1f} s (doubled {2 * out[False]:7.1f}, fits {2 * out[False] <= 10800}) | half-at-k0, half-at-mid bound {out[True]:7.1f} s (doubled {2 * out[True]:7.1f}, fits {2 * out[True] <= 10800})")
