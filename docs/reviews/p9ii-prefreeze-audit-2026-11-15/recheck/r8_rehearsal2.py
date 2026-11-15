"""R8 (auditor, Opus 5.5, re-check): rehearsal 2 recomputed from its raw records with plain json (no studies import): whitelist (every key of every
record; no loss/accuracy value), calibration binding, projections with per-task overhead (pool task seconds - timed training - timed evaluation,
added once to every training task and once to every evaluation task), the memory rule per stage with evaluation and task peaks, and the A4 consequence.

usage: r8_rehearsal2.py REHEARSAL_RUN_DIR CALIBRATION_JSON LEDGER_A_JSON
"""
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

RUN, CAL, LEDGER = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
U = 8192
WHITE = {"kind", "schema", "study", "label", "mode", "stage", "arm", "slots", "phase", "identity", "environment", "updates", "wall_seconds", "seconds_per_update", "evaluation_wall_seconds",
         "peak_rss_bytes", "sampled_rss_bytes", "load_average", "loss_finite", "parameters_finite", "gradients_finite", "shapes", "parameter_counts", "trainable_parameters", "stored_parameters",
         "optimizer_state_bytes", "trainable_backbone_parameters", "seed_set"}
files = sorted(p for p in RUN.rglob("*") if p.is_file())
kinds = sorted({p.name for p in files})
bad = []
for p in files:
    if p.parent.parent.name == "rehearsal":
        r = json.loads(p.read_text())
        extra = set(r) - WHITE
        if extra or r.get("seed_set") != "rehearsal-5" or r.get("mode") != "rehearsal":
            bad.append((str(p), extra))
        for k, v in r.items():
            if re.search(r"loss|acc|nll|perplex|entropy|correct|margin", k) and not isinstance(v, bool):
                bad.append((str(p), k))
print("files by name:", kinds, "| whitelist violations:", bad)
proj = json.loads((RUN / "projection.json").read_text())
cal = json.loads(CAL.read_text())
print("projection hyper == calibration hyper:", proj["hyper"] == cal["hyper"], "| projection calibration_sha256 == sha256(calibration.json):", proj["calibration_sha256"] == hashlib.sha256(CAL.read_bytes()).hexdigest())
man = {t["label"]: t for t in json.loads((RUN / "rehearse" / "manifest.json").read_text())["tasks"]}
rates = {}
for d in sorted((RUN / "rehearsal").iterdir()):
    t = json.loads((d / "rehearsal.json").read_text())
    e = json.loads((d / "rehearsal_evaluate.json").read_text())
    task = man[d.name]
    key = (t["arm"], t["slots"], t["phase"])
    rates[key] = {"spu": t["seconds_per_update"], "ev": e["evaluation_wall_seconds"], "ovh": max(0.0, task["seconds"] - t["wall_seconds"] - e["evaluation_wall_seconds"]),
                  "peak": max(t["peak_rss_bytes"], t["sampled_rss_bytes"], e["peak_rss_bytes"], task["peak_rss_bytes"] or 0)}
print("items:", len(rates), "| task overhead min/max: %.2f / %.2f s" % (min(r["ovh"] for r in rates.values()), max(r["ovh"] for r in rates.values())))
H = cal["hyper"]


def k_at(t, k0, ta):
    return 8 if t >= ta else max(8, round(k0 * (8 / k0) ** (t / ta)))


print("rehearsed A4 widths at 16,384: k0 =", round(H["k0_fraction"] * 16384), "mid =", k_at(16384 // 2 // 2, round(H["k0_fraction"] * 16384), 16384 // 2), "| at 4,096: k0 =", round(H["k0_fraction"] * 4096), "mid =", k_at(2048, 512, 4096))
last = {"A2": "post", "A4": "k8"}


def train_s(arm, n, st):
    total = U * (4 if st == 2 else 1)
    ovh = rates[(arm, n, last.get(arm, "main"))]["ovh"]
    if arm == "A2":
        pre = round(H["u_pre"] * (4 if st == 2 else 1))
        return pre * rates[(arm, n, "pre")]["spu"] + (total - pre) * rates[(arm, n, "post")]["spu"] + ovh
    if arm == "A4":
        ta = total // 2
        return ta * max(rates[(arm, n, "k0")]["spu"], rates[(arm, n, "mid")]["spu"]) + (total - ta) * rates[(arm, n, "k8")]["spu"] + ovh
    return total * rates[(arm, n, "main")]["spu"] + ovh


def eval_s(arm, n, st):
    r = rates[(arm, n, last.get(arm, "main"))]
    return (2 if st == 2 else 1) * r["ev"] + r["ovh"]


def mk(xs):
    xs = sorted(xs, reverse=True)
    return sum(xs[i] for i in range(0, len(xs), 6))


L = ["A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S"]
cells1 = [(a, 4096) for a in L for _ in range(16)] + [(a, 4096) for a in ("A6", "A7") for _ in range(8)]
t1, e1 = mk([train_s(a, n, 1) for a, n in cells1]), mk([eval_s(a, n, 1) for a, n in cells1])
charged = sum(e["seconds"] for e in json.loads(LEDGER.read_text())["entries"])
print(f"Stage 1: training {t1:.1f} + evaluation {e1:.1f} = {t1 + e1:.1f} s (record {proj['stage1']['projection']['total_seconds']:.1f}); doubled {2 * (t1 + e1):.1f} s vs Budget A remaining {14400 - charged:.1f} s")
mism = 0
for adv in [(), *[(a,) for a in ("A5-C", "A5-D", "A4", "A2", "A1")], *itertools.combinations(("A5-C", "A5-D", "A4", "A2", "A1"), 2)]:
    arms = ["A0", *adv] + (["A1-S"] if any(a in ("A1", "A2") for a in adv) else [])
    cells = [(a, 16384) for a in arms for _ in range(8)] + [(a, 16384) for a in ("A6", "A7") for _ in range(4)]
    tot = mk([train_s(a, n, 2) for a, n in cells]) + mk([eval_s(a, n, 2) for a, n in cells])
    key = "+".join(adv) if adv else "A0-only"
    rec = proj["stage2_table"][key]["total_seconds"]
    mism += abs(tot - rec) > 1e-6
    print(f"Stage 2 {key:10s} {len(cells):2d} cells {tot:8.1f} s (record {rec:8.1f}) doubled {2 * tot:8.1f} fits 10,800: {2 * tot <= 10800}")
for sel in ("A0", "A1", "A5-C", "A5-D"):
    arms = ["A0"] if sel == "A0" else ["A0", sel]
    cells = [(a, 65536) for a in arms + ["A6", "A7"] for _ in range(2)]
    tot = mk([train_s(a, n, 3) for a, n in cells]) + mk([eval_s(a, n, 3) for a, n in cells])
    mism += abs(tot - proj["stage3_table"][sel]["total_seconds"]) > 1e-6
    print(f"Stage 3 {sel}: {tot:.1f} s (record {proj['stage3_table'][sel]['total_seconds']:.1f}) doubled {2 * tot:.1f}")
print("projection mismatches (> 1e-6 s):", mism)
for st, n in ((1, 4096), (2, 16384), (3, 65536)):
    pk = max(r["peak"] for (a, s, ph), r in rates.items() if s == n)
    print(f"memory Stage {st}: peak {pk / 2**30:.3f} GiB, doubled {2 * pk / 2**30:.3f} GiB <= 3: {2 * pk <= 3 * 2**30}; six workers doubled {12 * pk / 2**30:.2f} GiB <= 24: {12 * pk <= 24 * 2**30}")
# A4 at 16,384: the registered rule charges the whole anneal at max(k0, mid); the k(t) path spends most updates far below k0
ta, k0 = 16384, 2048
widths = [k_at(t, k0, ta) for t in range(ta)]
print("A4 at 16,384: share of the anneal with k(t) > 512: %.3f, > 128: %.3f; rates measured k0 (2048) %.4f, mid (128) %.4f, k8 %.4f s/update" % (sum(w > 512 for w in widths) / ta, sum(w > 128 for w in widths) / ta, rates[("A4", 16384, "k0")]["spu"], rates[("A4", 16384, "mid")]["spu"], rates[("A4", 16384, "k8")]["spu"]))
