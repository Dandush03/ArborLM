"""Item 4: does the widened tag regex (classes.py:69-70) open a hole? Strings a later edit could produce, through classes.emit (pure).
Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r8_tag_lookbehind.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json
import sys

from studies.p10s1 import classes as C

out = {}
for s in ("NOT CAPACITY-POSITIVE", "IS NOT CAPACITY_SUPPORTED", "DENSE CAPACITY STEP", "DENSE BEATS DENSE", "DENSE NOT FASTER", "DENSE FASTER", "F-OQ FASTER", "CAPACITY STEPS",
          "CAPACITY-POSITIVE (x) (y) [STORE ONLY; ORACLE-ADDRESSED]", "CAPACITY-POSITIVE (x) [STORE ONLY; ORACLE-ADDRESSED]", "BEATS DENSE (DENSE AT CHANCE AT A2, B2) [STORE ONLY; ORACLE-ADDRESSED]"):
    try:
        C.emit(s)
        out[s] = "accepted"
    except C.UntaggedPositiveLabel as exc:
        out[s] = f"REFUSED: {exc}"
json.dump(out, sys.stdout, indent=1)
print()
