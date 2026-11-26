"""Copy auditor, step 1: diff every run copy against its original at b78e58b1 (own code).

Run from anywhere: python3 -I a1_diff_copies.py  (standard library only)
Writes a1_diff_copies.out.txt and copy_hashes.json next to this script.
"""
import difflib, hashlib, json, re, subprocess, sys
from pathlib import Path

WT = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
D = "docs/reviews/m0-lineage-decision-2026-11-25/"
FR = "studies/m0/fresh_run/"
PAIRS = [
    ("R1", FR + "r1/r1_fix4_tells.py", "studies/m0/r1_fix4_tells.py"),
    ("R1", FR + "r1/r1_fix4_measure.py", "studies/m0/r1_fix4_measure.py"),
    ("R1", FR + "r1/new_rules_final.py", D + "final_r1/new_rules_final.py"),
    ("R2", FR + "r2/r2_fix4_battery.py", "studies/m0/r2_fix4_battery.py"),
    ("R2", FR + "r2/f_rules.py", D + "final_r2/f_rules.py"),
    ("R2", FR + "r2/f_rules_new.py", D + "final_r2/f_rules_new.py"),
    ("R2", FR + "r2/f_new_heur.py", D + "final_r2/f_new_heur.py"),
    ("M1", FR + "m1/m1_fix3_shortcuts.py", "studies/m0/m1_fix3_shortcuts.py"),
    ("M1", FR + "m1/shortcuts_a4.py", D + "audit4_m1/shortcuts_a4.py"),
    ("M1", FR + "m1/shortcuts_a3.py", D + "audit3_m1/shortcuts_a3.py"),
    ("M1", FR + "m1/m1_fix4_battery.py", "studies/m0/m1_fix4_battery.py"),
    ("C1", FR + "c1/f5_closed_forms.py", D + "final_c1/f5_closed_forms.py"),
    ("C1", FR + "c1/f5b_closed_forms_v2.py", D + "final_c1/f5b_closed_forms_v2.py"),
]

def show(path):
    return subprocess.run(["git", "-C", str(WT), "show", f"{COMMIT}:{path}"], check=True, capture_output=True).stdout

out = []
hashes = {}
# every .py under fresh_run that is not one of the copies is listed, so no copy is missed
copies = {p for _, p, _ in PAIRS}
allpy = sorted(str(p.relative_to(WT)) for p in (WT / FR).rglob("*.py"))
out.append("python files under fresh_run: " + str(len(allpy)))
for p in allpy:
    if p not in copies:
        # is it a copy of something at b78e58b1 with the same basename?
        ls = subprocess.run(["git", "-C", str(WT), "ls-tree", "-r", "--name-only", COMMIT], capture_output=True, text=True).stdout.split()
        same = [x for x in ls if x.endswith("/" + Path(p).name)]
        out.append(f"  not a listed copy: {p}  (files of the same name at b78e58b1: {same})")
for ev, cp, orig in PAIRS:
    a = show(orig)
    b = (WT / cp).read_bytes()
    ha, hb = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()
    hashes[cp] = {"original_path": orig, "original_sha256": ha, "copy_sha256": hb}
    al, bl = a.decode().splitlines(keepends=True), b.decode().splitlines(keepends=True)
    out.append(f"\n=== {ev} {cp}\n    original {orig}\n    original sha256 {ha}\n    copy     sha256 {hb}")
    out.append(f"    lines original {len(al)} copy {len(bl)}; trailing newline orig {a.endswith(b'\\n')} copy {b.endswith(b'\\n')}; CRLF orig {b'\\r' in a} copy {b'\\r' in b}")
    sm = difflib.SequenceMatcher(a=al, b=bl, autojunk=False)
    n = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        n += 1
        out.append(f"  hunk {n}: {tag} orig lines {i1+1}-{i2} -> copy lines {j1+1}-{j2}")
        for l in al[i1:i2]:
            out.append("    - " + l.rstrip("\n"))
        for l in bl[j1:j2]:
            out.append("    + " + l.rstrip("\n"))
    out.append(f"  hunks: {n}")
txt = "\n".join(out) + "\n"
here = Path(__file__).resolve().parent
(here / "a1_diff_copies.out.txt").write_text(txt)
(here / "copy_hashes.json").write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n")
print(txt)
