"""Compare a second solver's answers with the builders' keys. Prints counts and mismatching item ids only (no key, no answer)."""
import json, sys, pathlib, collections
K = pathlib.Path("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_keys_20261126")
name = sys.argv[1]
ans = pathlib.Path(f"/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_solver2_{name}_20261126/answers_{name}.jsonl")
got = collections.defaultdict(dict)
for line in ans.read_text().splitlines():
    r = json.loads(line); got[r["id"]][(r["level"], r["index"])] = r["answer"]
tot = bad = 0
for lid in sorted(got):
    ev = lid.split(".")[0]
    keys = {(r["level"], r["index"]): r["key"] for r in map(json.loads, (K/ev/lid/"keys.jsonl").read_text().splitlines())}
    mm = sorted(k for k in keys if str(got[lid].get(k)) != str(keys[k]))
    miss = sorted(k for k in keys if k not in got[lid])
    tot += len(keys); bad += len(mm)
    print(f"{lid}: items {len(keys)} mismatches {len(mm)} missing {len(miss)}" + (f"  first (level,index): {mm[:12]}" if mm else ""))
print(f"TOTAL {name}: items {tot} mismatches {bad}")
