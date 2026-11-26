"""Step 1: apply path patterns (a),(b),(c) of ADR-0033 addendum 1 stage 1S point 1 to
`git ls-tree -r b78e58b1` and hash matches. Read-only; standard library only."""
import hashlib, json, re, subprocess, sys

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
COMMIT = "b78e58b1"
PA = re.compile(r"^studies/m0/(r1|r2|m1|c1)_fix4_(measure|battery|draw|a3_run)\.py$")
PB = re.compile(r"^docs/reviews/m0-lineage-decision-2026-11-25/final_(r1|r2|m1|c1)/[^/]*(rules|closed_forms|_draw|_a3_run|heur)[^/]*\.py$")
D = "docs/reviews/m0-lineage-decision-2026-11-25/"
PC = [D + "audit4_c1/s4_rules_v2.py", D + "audit4_c1/s5_analyse_v2.py", D + "audit3_c1/a3_shortcuts.py"]
TEXT = {
    "a": ["studies/m0/" + x for x in ["r1_fix4_measure.py", "r2_fix4_battery.py", "m1_fix4_battery.py",
                                      "c1_fix4_battery.py", "c1_fix4_draw.py", "c1_fix4_a3_run.py"]],
    "b": [D + x for x in ["final_r1/run_rules_final.py", "final_r1/new_rules_final.py", "final_r2/f_rules.py",
                          "final_r2/f_rules_new.py", "final_r2/f_new_heur.py", "final_m1/rules_a5.py",
                          "final_m1/rules_a5_attempt1.py", "final_c1/f1_draw.py", "final_c1/f3_a3_run.py",
                          "final_c1/f5_closed_forms.py", "final_c1/f5b_closed_forms_v2.py"]],
    "c": PC,
}

def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], check=True, capture_output=True).stdout

def tree():
    out = {}
    for line in git("ls-tree", "-r", "-z", COMMIT).split(b"\0"):
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        mode, typ, blob = meta.split()
        out[path.decode()] = (mode.decode(), typ.decode(), blob.decode())
    return out

def sha(blob):
    return hashlib.sha256(git("cat-file", "blob", blob)).hexdigest()

def main():
    full = git("rev-parse", COMMIT).decode().strip()
    t = tree()
    names = sorted(t)
    listed = []
    for p in names:
        pats = []
        if PA.match(p): pats.append("a")
        if PB.match(p): pats.append("b")
        if p in PC: pats.append("c")
        if pats:
            listed.append({"path": p, "blob": t[p][2], "sha256": sha(t[p][2]), "pattern": "+".join(pats)})
    missing_c = [p for p in PC if p not in t]
    text_all = {p: k for k, v in TEXT.items() for p in v}
    got = {e["path"]: e["pattern"] for e in listed}
    diff = {
        "in_rule_not_in_text": sorted(set(got) - set(text_all)),
        "in_text_not_in_rule": sorted(set(text_all) - set(got)),
        "pattern_mismatch": sorted(p for p in set(got) & set(text_all) if got[p] != text_all[p]),
        "pattern_c_missing_at_commit": missing_c,
        "text_count": len(text_all), "rule_count": len(listed),
    }
    # near-misses for the record: same folders, .py, not matched
    near = sorted(p for p in names if p.endswith(".py") and p not in got and (
        re.match(r"^studies/m0/(r1|r2|m1|c1)_fix4_", p) or re.match(r"^" + re.escape(D) + r"final_(r1|r2|m1|c1)/", p)))
    json.dump({"commit": full, "listed": listed, "diff_vs_text": diff, "near_misses_not_matched": near},
              sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")

main()
