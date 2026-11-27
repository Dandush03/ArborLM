"""Check 6, scope 2: apply the path rule of addendum 1 draft 6, section 4A stage 1S point 1, to the tree of b78e58b1.

Standard library only. Read-only git subprocesses (ls-tree, show). Runs no rule script, generates no item,
reads no run output. For every .py file under studies/m0/ with fix3/fix4 in its name, under
docs/reviews/m0-lineage-decision-2026-11-25/final_*/ (top level and subfolders) and under the audit folders,
prints whether the rule matches it, and a static text signal (counts of words that suggest rule scoring).
Usage: python k6_path_rule.py <worktree with claude/m0-impl>
"""
from __future__ import annotations

import re
import subprocess
import sys

COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
A = re.compile(r"^studies/m0/(r1|r2|m1|c1)_fix4_(measure|battery|draw|a3_run)\.py$")
B = re.compile(r"^docs/reviews/m0-lineage-decision-2026-11-25/final_(r1|r2|m1|c1)/[^/]*(rules|closed_forms|_draw|_a3_run|heur)[^/]*\.py$")
P = "docs/reviews/m0-lineage-decision-2026-11-25/"
C = [P + "audit4_c1/s4_rules_v2.py", P + "audit4_c1/s5_analyse_v2.py", P + "audit3_c1/a3_shortcuts.py"]
DRAFTER = {
    "studies/m0/r1_fix4_measure.py", "studies/m0/r2_fix4_battery.py", "studies/m0/m1_fix4_battery.py",
    "studies/m0/c1_fix4_battery.py", "studies/m0/c1_fix4_draw.py", "studies/m0/c1_fix4_a3_run.py",
    P + "final_r1/run_rules_final.py", P + "final_r1/new_rules_final.py",
    P + "final_r2/f_rules.py", P + "final_r2/f_rules_new.py", P + "final_r2/f_new_heur.py",
    P + "final_m1/rules_a5.py", P + "final_m1/rules_a5_attempt1.py",
    P + "final_c1/f1_draw.py", P + "final_c1/f3_a3_run.py", P + "final_c1/f5_closed_forms.py",
    P + "final_c1/f5b_closed_forms_v2.py", *C,
}
SIGNAL = re.compile(r"\b(rule|rules|heur\w*|shortcut\w*|tell\w*|closed.form\w*|cheap|chance|most.frequent|eff|anti)\b", re.I)


def git(wt: str, *args: str) -> str:
    return subprocess.run(["git", "-C", wt, *args], check=True, capture_output=True, text=True).stdout


def main() -> None:
    wt = sys.argv[1]
    files = git(wt, "ls-tree", "-r", "--name-only", COMMIT).splitlines()
    print(f"commit {COMMIT}; {len(files)} paths in tree")
    ma = [f for f in files if A.match(f)]
    mb = [f for f in files if B.match(f)]
    mc = [f for f in C if f in files]
    missing_c = [f for f in C if f not in files]
    listing = sorted(set(ma) | set(mb) | set(mc))
    print(f"(a) {len(ma)}:"); [print("   ", f) for f in ma]
    print(f"(b) {len(mb)}:"); [print("   ", f) for f in mb]
    print(f"(c) {len(mc)} present, missing {missing_c}:"); [print("   ", f) for f in mc]
    print(f"union {len(listing)}; drafter's list {len(DRAFTER)}")
    print("  in rule, not in drafter's list:", sorted(set(listing) - DRAFTER))
    print("  in drafter's list, not in rule:", sorted(DRAFTER - set(listing)))
    print()
    print("Unmatched .py files in final_*/ and studies/m0/*fix4*: static signal (count of rule-scoring words; first docstring line)")
    pool = [f for f in files if f.endswith(".py") and (f.startswith(P + "final_") or re.match(r"^studies/m0/[^/]*fix4[^/]*\.py$", f))]
    for f in sorted(pool):
        if f in listing:
            continue
        txt = git(wt, "show", f"{COMMIT}:{f}")
        n = len(SIGNAL.findall(txt))
        m = re.search(r'"""(.*?)\n', txt)
        head = (m.group(1).strip() if m else "")[:110]
        print(f"  {n:4d}  {f[len(P):] if f.startswith(P) else f}  | {head}")


if __name__ == "__main__":
    main()
