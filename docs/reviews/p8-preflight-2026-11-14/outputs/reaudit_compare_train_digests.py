"""Auditor (re-audit): compare state digests of the training-audit dry run (pre-fix source) with a
fresh dry run of the fixed source. Usage: compare_train_digests.py OLD_MANIFEST NEW_RUN_DIR."""
import json
import sys
from pathlib import Path

old = json.loads(Path(sys.argv[1]).read_text())
new_run = Path(sys.argv[2])
new = json.loads((new_run / "manifest.json").read_text())
new_by = {c["label"]: c for c in new["cells"]}
compared = mism = 0
for c in old["cells"]:
    n = new_by[c["label"]]
    for key in ("state_digests", "checkpoint_file_sha256"):
        for step, v in c[key].items():
            compared += 1
            same = n[key][step] == v
            mism += not same
            print(c["label"], key, step, "EQUAL" if same else f"DIFF old={v} new={n[key][step]}")
    for key in ("backbone_sha256_before", "backbone_sha256_after"):
        compared += 1
        mism += n[key] != c[key]
print(f"old source {old['code_identity'].get('source_sha256')} new source {new['code_identity'].get('source_sha256')}")
print(f"compared={compared} mismatches={mism}")
print("new stage status", new["status"], new["counts"])
