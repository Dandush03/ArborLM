"""Item 6 (no overwrite) and item 7 (the parts capacity.build_parts forms from the inputs of record, against mine).
No draw: main() is called only with an --out that exists (it must refuse before reading anything), with the audit
label and a guard installed in case it did not."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import SCR, W
from g_determinism import install_guard
cap = install_guard()
cand = json.load(open(f"{W}/studies/m0/registration/candidate_list.json"))
part = json.load(open(f"{W}/studies/m0/manifests/partition_of_record.json"))
mp = json.load(open(f"{W}/studies/m0/manifests/map_of_record.json"))
theirs = cap.build_parts(cand, part, mp)
mine = {r["part"]: r["clusters"] for r in json.load(open(f"{SCR}/deliver/f_round1.json"))}
ok = all({c: sorted(v) for c, v in theirs[(e, p)].items()} == mine[e + p] for e in ("R1", "R2", "M1", "C1") for p in "AB")
print("build_parts equals my parts on the inputs of record:", ok)
existing = f"{SCR}/deliver/f_round1.json"
rc = cap.main(["--candidates", "x", "--partition", "y", "--map", "z", "--out", existing])
print("main() with an existing --out returns", rc)
rc2 = cap.main(["--candidates", "x", "--partition", "y", "--map", "z", "--out", f"{SCR}/work/never_written.json", "--timings-out", existing])
print("main() with an existing --timings-out returns", rc2, "| out file created:", os.path.exists(f"{SCR}/work/never_written.json"))
