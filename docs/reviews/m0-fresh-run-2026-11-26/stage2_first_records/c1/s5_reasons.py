# ruff: noqa
"""Stage-2 C1 audit, step 5: write REASONS.md (per lineage: what was read, file:line, and the three results) from stage2_conditions_c1.json. Usage: python3 -I <this> JSON OUT_MD"""
import json, sys
d = json.load(open(sys.argv[1]))
L = ["# Stage 2, C1: reasons per lineage (what was read, file:line)", "",
     "Paths are in the implementation worktree `agent-a0c9d741ea96ce52f` (`claude/m0-impl`, HEAD `128a02a7`; `studies/m0/*.py` identical to `7cd0ac5a`). "
     "Builder locations from `s0_locate.out.json`. Common to every lineage, read once: `studies/m0/lineages_c1.py:29-38` (`_finish`: key and frame), "
     "`studies/m0/c1grammar.py:41-141` (renderer, `run_inprocess`), `studies/m0/core.py:26-34, 157-164` (`stream`, `build_item`), `studies/m0/lineages_c1_fix4.py:191-193` (`all_written`), "
     "the second solver `docs/reviews/m0-lineage-decision-2026-11-25/final_c1/f2_keys.py:1-147` and its report `FINAL_C1.md`, the draw script `final_c1/f1_draw.py:53-77`. "
     "Example items read: `s3_examples_L0_L6.txt` (one item at level 0 and one at level 6 per lineage, from my fixtures; I checked by hand the keys of binary_search_f3 L0, euclid_gcd_traced_f3 L6, "
     "func_branch_f4 L0, shared_lists_f3 L0, slices_f4 L0 and string_methods_f3 L0).", "",
     "Condition 4 (place in the map, the pair audited) is `see map_of_record` for every lineage: not this auditor's.", ""]
for lid, v in sorted(d["lineages"].items()):
    L.append(f"## {lid}")
    L.append("")
    L.append(f"- **wording: {v['wording']['result']}.** {v['wording']['reason']}")
    L.append(f"- **levels distinct: {v['levels_distinct']['result']}.** {v['levels_distinct']['reason']}")
    s = v["second_solver"]
    L.append(f"- **second solver: {s['result']}** ({s['fixtures']} fixtures, {s['mismatches']} mismatches). Authorship reason common to all 26: see REPORT.md, section 'Second solver'.")
    L.append("")
open(sys.argv[2], "w").write("\n".join(L))
