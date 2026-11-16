"""B1 (auditor, Opus 5.5): per-64-update trajectories of the P9-II calibration cells, read from the raw JSONL logs with
plain json (no studies.* import). Prints, per cell, the diagnostics around A2's switch and A4's schedule, and the
per-update answer loss / clip factor / parameter movement in the first updates after A2's switch.

usage: python b1_a2_trajectories.py RUN_DIR
"""
import json
import sys
from pathlib import Path

RUN = Path(sys.argv[1])


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def fmt(v):
    return "-" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))


for label in sorted(p.name for p in (RUN / "cells").iterdir()):
    if not (label.startswith("CAL-A2") or label.startswith("CAL-A4") or label.startswith("CAL-A0")):
        continue
    d = rows(RUN / "cells" / label / "diagnostics.jsonl")
    u = rows(RUN / "cells" / label / "updates.jsonl")
    tr = json.loads((RUN / "cells" / label / "train.json").read_text())
    print(f"=== {label}  schedule={tr['schedule']}")
    print("update phase acc distinct largest cos_diff fis tgt1 tgt8 tscore cos_top1 g_ans_wq g_ans_wo g_ans_keys g_ans_values mv_wq mv_keys mv_values mv_wo read_k soft")
    keep = {64, 128, 256, 512, 1024, 1536, 1984, 2048, 2112, 2176, 2240, 2304, 2560, 3072, 4096, 6144, 8192}
    for r in d:
        if r["update"] in keep or (label.startswith("CAL-A4") and r["update"] % 1024 == 0):
            g = r["gradient_norms_by_loss"].get("answer", {})
            m = r["movement_since_previous_record"]
            print(r["update"], r["phase"], fmt(r["probe_accuracy"]), r.get("distinct_top1"), fmt(r.get("largest_top1_share")), fmt(r.get("mean_cosine_different")),
                  fmt(r.get("fact_independent_share")), fmt(r.get("target_top1_recall")), fmt(r.get("target_top8_recall")), fmt(r.get("mean_target_score")), fmt(r.get("cosine_with_top1_key")),
                  fmt(g.get("wq")), fmt(g.get("wo")), fmt(g.get("keys")), fmt(g.get("values")), fmt(m.get("wq")), fmt(m.get("keys")), fmt(m.get("values")), fmt(m.get("wo")), r.get("read_k", "-"), fmt(r.get("soft_mass_outside_top8")))
    if label.startswith("CAL-A2"):
        upre = tr["schedule"]["u_pre"]
        print(" per-update around the switch: update phase task_loss addr_loss clip_factor |dwq| |dkeys| |dvalues| |dwo| |dgate| gnorm_wq gnorm_wo gnorm_values")
        for r in u:
            if upre - 2 <= r["update"] <= upre + 12 or r["update"] in (upre + 32, upre + 64, upre + 128, upre + 256, upre + 512, 8192):
                c, gn = r["param_change_norm"], r["grad_norm"]
                print(" ", r["update"], r["phase"], fmt(r["task_loss"]), fmt(r["address_loss"]), fmt(r["clip_factor"]), fmt(c["wq"]), fmt(c["keys"]), fmt(c["values"]), fmt(c["wo"]), fmt(c["gate"]), fmt(gn["wq"]), fmt(gn["wo"]), fmt(gn["values"]))
        # moving averages of the answer loss in phase 2
        ph2 = [r for r in u if r["phase"] == 2]
        for lo in range(0, len(ph2), 512):
            seg = ph2[lo:lo + 512]
            print(f"  phase-2 updates {seg[0]['update']}-{seg[-1]['update']}: mean answer loss {sum(r['task_loss'] for r in seg)/len(seg):.4f}  mean addr loss {sum(r['address_loss'] for r in seg)/len(seg):.4f}")
