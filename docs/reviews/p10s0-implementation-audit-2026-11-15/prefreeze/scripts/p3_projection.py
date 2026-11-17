# Independent recomputation of the S0 projection from the two rehearsal records and ADR-0020 sections 6, 10.3, 10.4.
# No arborlm/studies imports. Matrix built from ADR text. Guard term read from projection.json (a measured value; not re-measurable here).
import json, math, sys
from pathlib import Path
E = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
GIB = 2 ** 30
U = 8192
CT = {"2K4K": (U, 1), "8K16K": (4 * U, 2), "8K4K": (4 * U, 2), "32K64K": (16 * U, 1)}  # updates, readouts
UPRE = {"2K4K": 2048, "8K16K": 8192}
def load(name):
    d = E / f"P10S0H-rehearsal-{name}-20261115"
    man = json.loads((d / "rehearse/manifest.json").read_text())
    task = {t["label"]: t for t in man["tasks"]}
    out = {}
    for f in (d / "rehearsal").iterdir():
        tr = json.loads((f / "rehearsal.json").read_text()); ev = json.loads((f / "rehearsal_evaluate.json").read_text())
        t = task[f.name]
        out[f.name] = {"spu": tr["seconds_per_update"], "eval": ev["evaluation_wall_seconds"], "overhead": max(0.0, t["seconds"] - tr["wall_seconds"] - ev["evaluation_wall_seconds"]),
                       "peak": max(tr["peak_rss_bytes"], tr["sampled_rss_bytes"], ev["peak_rss_bytes"], t["peak_rss_bytes"]), "task_s": t["seconds"], "train_wall": tr["wall_seconds"], "upd": tr["updates"],
                       "spu_check": tr["wall_seconds"] / tr["updates"]}
    return out
alone, busy = load("alone"), load("busy")
proj = json.loads((E / "P10S0J-projection-20261115/projection.json").read_text())
guard = proj["guard_seconds_per_task"]
def merged(with_overhead=True, which="max"):
    m = {}
    for k in alone:
        a, b = alone[k], busy[k]
        pick = (lambda f: max(a[f], b[f])) if which == "max" else (lambda f: (a if which == "alone" else b)[f])
        m[k] = {"spu": pick("spu"), "eval": pick("eval"), "ovh": (pick("overhead") + guard) if with_overhead else 0.0, "peak": pick("peak")}
    return m
def cells(block, key):
    c = []
    if block == "q1":
        for ct in ("2K4K", "8K16K"):
            for arm in ("A0", "A1", "A2", "A5-D"):
                n = 10 if (ct == "8K16K" and key == "cut3") else 20
                c += [(arm, ct)] * n
            c += [("A6", ct)] * 10 + [("A7", ct)] * 10
        c += [("A0", "8K4K")] * 10 + [("A5-D", "8K4K")] * 10 + [("A6", "8K4K")] * 10
    elif block == "wx":
        c = [(f"WX-{key}", "2K4K")] * 10 + [(f"WX-{key}", "8K16K")] * 10
    elif block == "probe":
        c = [(key, "32K64K")] * 3 + [("A6", "32K64K")] * 3
    return c
def lab(arm, ct, ph="main"): return f"REH-{arm}-{ct}-{ph}"
def train_s(arm, ct, r):
    upd = CT[ct][0]
    if arm == "A2":
        pre, post = r[lab(arm, ct, "pre")], r[lab(arm, ct, "post")]
        return UPRE[ct] * pre["spu"] + (upd - UPRE[ct]) * post["spu"] + post["ovh"]
    x = r[lab(arm, ct)]
    return upd * x["spu"] + x["ovh"]
def eval_s(arm, ct, r):
    x = r[lab(arm, ct, "post" if arm == "A2" else "main")]
    return CT[ct][1] * x["eval"] + x["ovh"]
def rounds(xs, w=6):
    xs = sorted(xs, reverse=True); return sum(xs[i] for i in range(0, len(xs), w))
def project(r):
    out = {}
    for b, k in [("q1", "full"), ("q1", "cut3"), ("wx", "A5-D"), ("wx", "A1"), ("probe", "A5-D"), ("probe", "A1")]:
        cs = cells(b, k)
        t = rounds([train_s(a, ct, r) for a, ct in cs]); e = rounds([eval_s(a, ct, r) for a, ct in cs])
        items = {lab(a, ct, ph) for a, ct in cs for ph in (("pre", "post") if a == "A2" else ("main",))}
        out[f"{b}:{k}"] = {"cells": len(cs), "train_s": t, "eval_s": e, "total_s": t + e, "total_h": (t + e) / 3600, "peak_GiB": max(r[i]["peak"] for i in items) / GIB, "sum_cpu_h": (sum(train_s(a, ct, r) for a, ct in cs) + sum(eval_s(a, ct, r) for a, ct in cs)) / 3600}
    return out
res = {"guard_seconds_per_task": guard, "with_overhead_max": project(merged(True)), "literal_no_overhead_max": project(merged(False)), "alone_only": project(merged(True, "alone")), "busy_only": project(merged(True, "busy"))}
res["compare_with_projection_json"] = {k: {"mine_s": res["with_overhead_max"][k]["total_s"], "theirs_s": v["total_seconds"], "diff_s": res["with_overhead_max"][k]["total_s"] - v["total_seconds"], "mine_train": res["with_overhead_max"][k]["train_s"], "theirs_train": v["training_seconds"], "mine_eval": res["with_overhead_max"][k]["eval_s"], "theirs_eval": v["evaluation_seconds"]} for k, v in proj["table"].items()}
res["peak_by_item_GiB"] = {k: round(v["peak"] / GIB, 4) for k, v in sorted(merged().items(), key=lambda kv: -kv[1]["peak"])}
res["rates_by_item"] = {k: {"alone_spu": alone[k]["spu"], "busy_spu": busy[k]["spu"], "busy/alone": busy[k]["spu"] / alone[k]["spu"], "alone_eval": alone[k]["eval"], "busy_eval": busy[k]["eval"], "alone_ovh": alone[k]["overhead"], "busy_ovh": busy[k]["overhead"], "spu_vs_wall/upd_relerr": (alone[k]["spu"] - alone[k]["spu_check"]) / alone[k]["spu"]} for k in sorted(alone)}
# compare merged rates with projection.json rates
pr = proj["rates"]; dif = []
for k, v in merged(True).items():
    q = pr[k]
    for f, g in (("spu", "seconds_per_update"), ("eval", "evaluation_seconds"), ("ovh", "task_overhead_seconds")):
        if abs(v[f] - q[g]) > 1e-9 * max(1, abs(q[g])): dif.append((k, f, v[f], q[g]))
res["rate_field_disagreements_vs_projection_json"] = dif
json.dump(res, sys.stdout, indent=1)
