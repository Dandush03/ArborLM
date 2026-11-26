"""Copy auditor, step 2 (S4 completeness): at b78e58b1, which .py files import / load / run each copied module?
python3 -I a2_importers.py  -> a2_importers.out.txt"""
import re, subprocess
from pathlib import Path
WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
C = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
MODS = ["m1_fix3_shortcuts", "r1_fix4_tells", "shortcuts_a4", "shortcuts_a3", "r1_fix4_measure", "f_new_heur",
        "new_rules_final", "f5_closed_forms", "f5b_closed_forms_v2", "r2_fix4_battery", "f_rules", "f_rules_new", "m1_fix4_battery"]
out = []
for m in MODS:
    g = subprocess.run(["git", "-C", WT, "grep", "-n", "-w", "-e", m, C, "--", "*.py"], capture_output=True, text=True).stdout
    hits = []
    for line in g.splitlines():
        _, path, ln, text = line.split(":", 3)
        t = text.strip()
        if re.search(r"\bimport\b|_load\(|spec_from_file_location|subprocess|sys\.executable|\.py\"", t) and not t.startswith("#"):
            hits.append(f"  {path}:{ln}: {t[:200]}")
    out.append(f"== {m}: {len(hits)} import/load lines")
    out += hits
txt = "\n".join(out) + "\n"
Path(__file__).with_suffix(".out.txt").write_text(txt)
print(txt)
