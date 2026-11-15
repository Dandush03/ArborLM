# Compute studies.p10s0 code identity of several archived trees, plus byte-compare train/evaluate/model.
import sys, json, hashlib
from pathlib import Path
from studies.p10s0 import core
out = {}
for root in sys.argv[1:]:
    r = Path(root)
    out[r.name] = {"identity": core.code_identity(r),
                   **{f: hashlib.sha256((r/"studies/p10s0"/f).read_bytes()).hexdigest() for f in ("train.py","evaluate.py","model.py")}}
print(json.dumps(out, indent=1))
