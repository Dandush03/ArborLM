# ruff: noqa  (auditor's script, recorded as run except for this line)
# ruff: noqa
"""Audit 21: quick check of timing-run outputs (prefix of each record) against the stored item records. Not the registered comparison (a21_compare.py)."""
import json
import sys
from pathlib import Path

RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121")
stored = json.loads((RUN / "item_records.json").read_text())["items"]
comb = json.loads((RUN / "combined.json").read_text())["combined"]


def peek_comb(key, mine):
    s = comb[key]
    for kind in ("C1", "C2"):
        bad_ids = [it["j"] for it in mine[kind]["items"] if it["ids"] != s[kind]["items"][it["j"]]["ids"]]
        md = max(max(abs(a - b) for a, b in zip(it["scores"], s[kind]["items"][it["j"]]["scores"])) for it in mine[kind]["items"])
        print(f"{key} {kind}: n={len(mine[kind]['items'])} iddiff={len(bad_ids)} maxscore={md:.3e}", bad_ids[:5])
    for c in ("A", "B"):
        idx = mine["single"]["index"]
        bad = [i for k, i in enumerate(idx) if mine["single"]["sequences"][c][k] != s["single"]["sequences"][c][i]]
        md = max((abs(mine["single"]["scores"][c][k] - s["single"]["scores"][c][i]) for k, i in enumerate(idx)), default=0.0)
        print(f"{key} single {c}: n={len(idx)} seqdiff={len(bad)} maxscore={md:.3e}", bad[:5])


for f in sys.argv[1:]:
    d = json.loads(Path(f).read_text())
    if "combined" in d.get("extra", {}):
        peek_comb(d["extra"]["combined_key"], d["extra"]["combined"])
    if "S0" in d.get("extra", {}):
        peek_comb("S0", d["extra"]["S0"])
    for k, mine in d["records"].items():
        s = stored.get(k)
        if s is None:
            print("NOT STORED", k)
            continue
        if "gen" in mine:
            for fld in ("nll_base", "nll_arm"):
                diff = max(abs(a - b) for a, b in zip(mine["gen"][fld], s["gen"][fld]))
                d64 = max(abs(a - b) for a, b in zip(mine["gen"][fld + "_f64"], s["gen"][fld]))
                print(k, fld, "maxdiff f32", diff, "f64", d64)
            print(k, "preds equal", mine["gen"]["preds"] == s["gen"]["preds"], "strata equal", mine["gen"]["strata"] == s["gen"]["strata"], len(mine["gen"]["preds"]))
            continue
        n = len(mine.get("items", mine.get("flags", [])))
        bad_seq = [i for i in range(n) if "sequences" in mine and mine["sequences"][i] != s["sequences"][i]]
        bad_it = [i for i in range(n) if "items" in mine and abs(mine["items"][i] - s["items"][i]) > 1e-6]
        bad_ex = [i for i in range(n) if "exact" in mine and "exact" in s and mine["exact"][i] != s["exact"][i]]
        bad_fl = [i for i in range(n) if "flags" in mine and mine["flags"][i] != s["flags"][i]]
        md = max((abs(mine["items"][i] - s["items"][i]) for i in range(n)), default=0.0) if "items" in mine else 0.0
        print(f"{k}: n={n} seqdiff={len(bad_seq)} itemdiff={len(bad_it)} exactdiff={len(bad_ex)} flagdiff={len(bad_fl)} maxitem={md:.3e}", bad_seq[:5], bad_it[:5])
    print(f, d["seconds"], d["decode_calls"], d.get("extra", {}).get("route_accuracy_mine"))
