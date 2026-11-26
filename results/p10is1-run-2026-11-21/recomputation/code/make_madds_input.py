# ruff: noqa
"""Input step (not part of the recomputation's rules): MC-A's analytic multiply-adds per update, from the FROZEN formula of ADR-0021 section 22 M6
(studies/p10s1/frozen.py at the freeze commit, archived read-only into ./frozen). Usage: PYTHONPATH=frozen:frozen/src python -B make_madds_input.py <out.json>"""
import json, sys
from studies.p10s1 import frozen as f
out = {}
for arm in ("F-OQ", "T-OQ", "H8", "D-OQ", "R2"):
    for n in (256, 1024, 4096, 16384, 32768):
        try:
            out[f"{arm}|{n}"] = float(f.analytic_madds_per_update(arm, n))
        except Exception as e:
            out[f"{arm}|{n}"] = None
json.dump({k: v for k, v in out.items() if v is not None}, open(sys.argv[1], "w"), indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in out.items() if v is not None}))
