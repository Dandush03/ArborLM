# My own cap table (README step 9 rule: block caps = 2 x rehearsed projection of train / evaluate makespans; gates = max(60, 2 x (G + 12 P)); generate/analysis/report = max(60, 2 x measured)).
# Compared with 2 x the busy-only projection (my p3), and with the measured-condition notes.
import json, sys
p3 = json.loads(open(sys.argv[1]).read())
A = float(sys.argv[2]); R = float(sys.argv[3])
mx, busy = p3["with_overhead_max"], p3["busy_only"]
G, Pd, N = 39.755301958008204, 3.1943115839967504, 33.44888391700806
caps = {"generate": max(60, 2 * N), "gates": max(60, 2 * (G + 12 * Pd)), "analysis": max(60, 2 * A), "report": max(60, 2 * R)}
for k, v in mx.items():
    b, key = k.split(":")
    caps.setdefault(b, {})[key] = {"train": 2 * v["train_s"], "evaluate": 2 * v["eval_s"], "train_over_2x_busy": (2 * v["train_s"]) / (2 * busy[k]["train_s"]), "evaluate_over_2x_busy": (2 * v["eval_s"]) / (2 * busy[k]["eval_s"])}
caps["reserve_s"] = (caps["analysis"] + caps["report"]) / 2
caps["probe_eval_per_cell_s"] = {"A1": p3["rates_by_item"]["REH-A1-32K64K-main"]["busy_eval"], "A6": p3["rates_by_item"]["REH-A6-32K64K-main"]["busy_eval"], "A5-D": p3["rates_by_item"]["REH-A5-D-32K64K-main"]["busy_eval"]}
json.dump(caps, sys.stdout, indent=1)
