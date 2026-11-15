"""G10 recomputation by the auditor from ADR-0020 rev 4 sections 3.2-3.5 and P9-II's committed records, with its own code (no studies.* import).
Usage: python3 a4_g10_recompute.py <worktree>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

W = Path(sys.argv[1])
res_path = W / "results/p9ii-run-2026-11-15/results.json"
out_path = W / "results/p9ii-run-2026-11-15/OUTCOME.md"
cal_path = W / "results/p9ii-calibration-2026-11-15/calibration.json"
adr = (W / "docs/decisions/ADR-0020-p10-s0-addressing-qualification.md").read_text(encoding="utf-8")
rec = json.loads((W / "studies/p10s0/freeze/arm_selection.json").read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


r = json.loads(res_path.read_text())["result"]
cal = json.loads(cal_path.read_text())
report = {"hashes": {"results.json": sha(res_path), "OUTCOME.md": sha(out_path), "calibration.json": sha(cal_path)}}
# ADR 3.4 table: calibration sha256 starts ad5d7ee2
report["calibration_prefix_matches_adr"] = report["hashes"]["calibration.json"].startswith("ad5d7ee2")
report["record_hashes_match"] = {k: rec["p9ii_inputs"][k2]["sha256"] == v for k, k2, v in (("results.json", "results", report["hashes"]["results.json"]), ("OUTCOME.md", "outcome", report["hashes"]["OUTCOME.md"]), ("calibration.json", "calibration", report["hashes"]["calibration.json"]))}

# --- section 3.2, in order --------------------------------------------------------------------------------------------
steps = []
hyper = cal["hyper"]
steps.append(("1 calibration", f"exists; lambda={hyper['lambda']} u_pre={hyper['u_pre']} k0/N={hyper['k0_fraction']} mu={hyper['mu']}"))
outcome = r["outcome"]["outcome"]
steps.append(("2 outcome row", f"{outcome} (row {r['outcome']['row']})"))
interpreted = outcome not in ("ENGINEERING_FAIL", "INCOMPLETE", "NOT_INTERPRETED", "NOT_INTERPRETED (INCOMPLETE)")
st2 = r["stage2"]["status"]
steps.append(("3 Stage 2", st2))
carried = r["carried_forward"]["arm"]
if not interpreted:
    c4, printed = None, f"FOURTH ARM: NONE — P9-II {outcome}"
elif st2 != "COMPLETE":
    c4, printed = None, "FOURTH ARM: NONE — (Stage 2 not COMPLETE)"
elif carried in ("A4", "A5-C", "A5-D"):
    c4, printed = carried, None
elif carried in ("A0", "A2", "A1"):
    c4, printed = None, f"FOURTH ARM: NONE — P9-II CARRIED {carried} (ALREADY IN S0)"
else:
    c4, printed = None, "none carried"
steps.append(("4 carried", f"{carried} -> c4={c4}"))
report["steps"] = steps
report["mapping_c4"] = c4
report["mapping_printed"] = printed
# section 3.3 row: ADDRESSING-RELIABLE with carried A0 is the third row
report["table_row_text"] = "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096) — none (already in S0)" if (outcome == "ADDRESSING-RELIABLE" and carried == "A0") else "other"
report["record_mapping_equal"] = rec["mapping"]["c4"] == c4 and rec["mapping_printed"] == printed and rec["mapping"]["table_row"] == 3

# --- section 3.5: P9-II failed draws per arm and size, LM flag, and the candidate list ----------------------------------
table = {}
for size, stage in (("4096", "stage1"), ("16384", "stage2")):
    for arm in ("A0", "A1", "A2", "A5-D"):
        a = r[stage]["arms"].get(arm)
        if a is None:
            table[(arm, size)] = None
            continue
        dc = a["draw_sensitivity"]["draw_counts"]
        table[(arm, size)] = {"class": a["class"], "failed": dc["0/2"] + dc["1/2"], "evaluated": dc["0/2"] + dc["1/2"] + dc["2/2"], "cells": f"{a['counts']['successes']}/{a['counts']['evaluated']}", "lm": "LM CAPABILITY REDUCED" in a["class"]}
report["p9ii_table"] = {f"{a} {s}": v for (a, s), v in table.items()}
expected_35 = {("A0", "4096"): ("UNRELIABLE", 6, 8), ("A0", "16384"): ("RELIABLE", 0, 4), ("A5-D", "4096"): ("RELIABLE", 0, 8), ("A5-D", "16384"): ("RELIABLE", 0, 4),
               ("A2", "4096"): ("FAILS", 8, 8), ("A2", "16384"): None, ("A1", "4096"): ("RELIABLE", 0, 8), ("A1", "16384"): ("UNRELIABLE", 2, 4)}
report["section_3_5_table_reproduced"] = all((table[k] is None and v is None) or (table[k] is not None and v is not None and (table[k]["class"], table[k]["failed"], table[k]["evaluated"]) == v) for k, v in expected_35.items())
cands = [a for a in ("A0", "A5-D", "A2", "A1") if not (table[(a, "4096")] and (table[(a, "4096")]["lm"] or table[(a, "4096")]["failed"] > 2))]
report["candidates"] = cands
report["record_candidates_equal"] = rec["candidates"]["arms"] == cands
for arm in ("A0", "A1", "A2", "A5-D"):
    for size in ("4096", "16384"):
        mine = table[(arm, size)]
        theirs = rec["p9ii_classes"][arm][size]
        ok = (mine is None and not theirs["available"]) or (mine is not None and theirs["available"] and theirs["failed_draws"] == mine["failed"] and theirs["evaluated_draws"] == mine["evaluated"] and theirs["class"] == mine["class"] and theirs["lm_reduced"] == mine["lm"])
        report.setdefault("record_p9ii_classes_equal", {})[f"{arm} {size}"] = ok

# --- section 3.4 strings, character for character ---------------------------------------------------------------------
m = re.search(r"\*\*FOURTH ARM: A5-D — [^*]+\*\*", adr)
adr_string = m.group(0).strip("*") if m else None
f1_adr = re.search(r"followed by P9-II's F1 annotation, verbatim from `results/p9ii-run-2026-11-15/OUTCOME.md`: \*([^*]+)\*", adr).group(1)
fixed = re.search(r'and by the fixed sentence: \*\*"([^"]+)"\*\*', adr).group(1)
words = re.search(r"> (yes s0 should include the penalty and i approve s2 download)\n", adr).group(1)
outcome_md = out_path.read_text(encoding="utf-8")
f1_out = re.search(r"attached wherever it is cited: \*([^*]+)\*", outcome_md).group(1)
ov = rec["override"]
report["strings"] = {
    "fourth_arm_string_record==adr": ov["printed_string"] == adr_string and rec["fourth_arm_printed"] == adr_string,
    "f1_record==adr": ov["f1_annotation"] == f1_adr,
    "f1_adr==OUTCOME.md": f1_adr == f1_out,
    "fixed_sentence_record==adr": ov["fixed_sentence"] == fixed,
    "human_lead_words_record==adr": ov["human_lead_words"] == words,
    "mu": ov["mu"] == 1.0, "c4": ov["c4"] == "A5-D", "date": ov["date"] == "2026-11-15",
    "calibrated": (rec["calibrated"]["lambda"], rec["calibrated"]["u_pre"], rec["calibrated"]["mu"]) == (hyper["lambda"], hyper["u_pre"], hyper["mu"]) == (1.0, 2048.0, 1.0),
}
report["adr_fourth_arm_string"] = adr_string
print(json.dumps(report, indent=1, ensure_ascii=False))
