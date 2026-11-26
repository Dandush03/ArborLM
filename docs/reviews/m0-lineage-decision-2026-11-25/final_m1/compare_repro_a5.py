# ruff: noqa
"""Final M1 audit: compare my recomputation at the implementer's seeds (rules_repro_n2000.json) with the implementer's raw battery
(studies/m0/manifests/m1_fix4_battery_raw.json). Standard library only. Prints every rule whose base or minus_base differs by more than 0.0006 (rounding)."""
import json
import sys

mine = json.load(open(sys.argv[1]))["results"]
theirs = json.load(open(sys.argv[2]))["raw"]
n_cmp = n_diff = 0
miss = []
for lid in sorted(mine):
    for L in range(7):
        for src in ("a4", "own", "a3"):
            m = mine[lid][str(L)][src]
            t = theirs[src][lid][str(L)]
            if abs(m["base"] - t["base"]) > 6e-4:
                print("BASE", lid, L, src, m["base"], t["base"]); n_diff += 1
            for k, v in t["minus_base"].items():
                if k.endswith("__within_applicable"):
                    continue
                if src == "a4":
                    mk = k
                elif k.startswith("echo_best_position"):
                    mk = "echo_best_position"
                else:
                    mk = ("im:" if src == "own" else "a3:") + k
                if mk not in m["minus_base"]:
                    miss.append((lid, L, src, k)); continue
                n_cmp += 1
                if abs(m["minus_base"][mk] - v) > 6e-4:
                    n_diff += 1
                    print("DIFF", lid, L, src, k, "mine", m["minus_base"][mk], "theirs", v)
            extra = set(m["minus_base"]) - {("im:" + k if src == "own" else "a3:" + k) if src != "a4" else k for k in t["minus_base"]} - {"echo_best_position"}
            if extra:
                miss.append((lid, L, src, "EXTRA in mine: " + ",".join(sorted(extra))))
print("compared", n_cmp, "differences", n_diff, "rules missing on one side", len(miss))
for x in miss[:20]:
    print("  ", x)
