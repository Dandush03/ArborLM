"""Attempts to break the tag rule (ADR-0021 section 3 item 4: no positive label printed without "STORE ONLY; ORACLE-ADDRESSED").

1. Every label the analysis can emit, passed through report.show + classes.emit (the report path).
2. The BEATS DENSE (DENSE AT CHANCE AT <step>) label that classes.dense_label builds, through report.show and through a full render_markdown.
3. Spelling variants a later edit could produce (not produced by the current code): are they caught?
4. A detail containing ']' inside a tagged bracket before a positive label.

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c6_tag_rule.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys

from studies.p10s1 import classes as C
from studies.p10s1 import core
from studies.p10s1 import report

out = {}


def try_emit(text):
    try:
        C.emit(text)
        return "accepted"
    except C.UntaggedPositiveLabel as exc:
        return f"REFUSED: {exc}"


# 1. the dense label with a zero denominator, as dense_label builds it
reps = [{rd: {p: (1.0, None, 0.03) for p in "AB"} for rd in ("MU", "MC", "D-BEST")} for _ in range(5)]
lab = C.dense_label([C.DenseCell("A2", reps)])["label"]
out["dense_label_built"] = lab
out["report_show_then_emit"] = try_emit(report.show(lab))
out["report_show_text"] = report.show(lab)
out["printable"] = None
try:
    out["printable"] = C.printable(lab)
except C.UntaggedPositiveLabel as exc:
    out["printable"] = f"REFUSED: {exc}"

# 2. variants
for v in ("CAPACITY STEPS were found", "two CAPACITY STEPs", "Capacity-Positive", "CAPACITY POSITIVE", "CAPACITY‑POSITIVE (non-breaking hyphen)", "BEATS-DENSE", "TREE AHEAD",
          "Storage half supported", "storage half supported, as a necessary condition", "EFFICIENCY POSITIVE", "verdict FASTER in 5 of 5", "REACHED ONLY BY THE LARGER",
          "CAPACITY in all five replicates", "KNOWLEDGE SCALES", "CAPACITY_SUPPORTED[STORE ONLY; ORACLE-ADDRESSED]", "CAPACITY-POSITIVE [not STORE ONLY; ORACLE-ADDRESSED]"):
    out.setdefault("variants", {})[v] = try_emit(v)

# 3. a ']' inside a tagged bracket before a positive label
out["bracket_in_detail"] = try_emit(C.tagged("CAPACITY-POSITIVE", "S0 status [see ADR-0020]", "F-OQ: BEATS DENSE"))
out["store_only_tag"] = core.STORE_ONLY_TAG
json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
print()
