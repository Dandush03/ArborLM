# ruff: noqa
"""Check 5, scope 2: apply draft 5's membership rule (section 4A stage 0, points 1-5) MECHANICALLY to git history, for one
evaluation (M1), and print every place where the text leaves a judgement. Membership only: this script reads no run output,
computes no rate, no pooled figure, no lineage status, and does not compare anything with R-38.

Read-only git: ls-tree, show, log, diff on the implementation worktree. Standard library only.
Usage: uv run --locked python -I -B membership_m1_check5.py <impl_worktree>
"""
import re
import subprocess
import sys

REPO = sys.argv[1]
REC = "b78e58b1"      # point 1: the record of runs
GEN = "7cd0ac5a"      # point 2: the final generator version
DR = "docs/reviews/m0-lineage-decision-2026-11-25/"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], check=True, capture_output=True, text=True, timeout=120).stdout


def show(path, rev=REC):
    return git("show", f"{rev}:{path}")


files = git("ls-tree", "-r", "--name-only", REC).splitlines()
m1_py = sorted(f for f in files if f.endswith(".py") and (
    (f.startswith("studies/m0/") and re.search(r"(^|/)m1_", f)) or
    (f.startswith(DR) and re.search(r"/(audit\d?_m1|final_m1)/", f))))

# point 3: "a rule script is any script of the record that scores rules against generated items for the bound"
# Mechanical proxy (mine, not the text's test): the text draws items AND names rules / heuristics / shortcuts.
DRAW = re.compile(r"build_item|\bstream\(|\bitems\(|load_batch|load_rev2|load_all|load_registered|current_set|survivors\(")
RULE = re.compile(r"shortcut|heuristic|cheap rule|cheap-rule|\brules?\b|\btells?\b|minus_base|base rate|most.frequent", re.I)
SEED = re.compile(r"^SEED\s*=\s*(\d+)|[Ss]eed (\d+)", re.M)

print(f"PART 1. M1 scripts in the tree of {REC} ({len(m1_py)} .py files under studies/m0/m1_* and the M1 audit folders)")
print("  columns: draws-items | names-rules | seeds-in-text | first-commit | path")
cand = []
for f in m1_py:
    t = show(f)
    d = bool(DRAW.search(t)); r = bool(RULE.search(t))
    seeds = sorted({x for m in SEED.finditer(t) for x in m.groups() if x})[:4]
    first = git("log", "--diff-filter=A", "--format=%h", REC, "--", f).split()[-1:]
    print(f"  {'D' if d else '-'} {'R' if r else '-'} {','.join(seeds) or '-':>22} {first[0] if first else '?':>9}  {f}")
    if d and r:
        cand.append(f)

print()
print(f"  proxy 'draws items AND names rules': {len(cand)} scripts. The proxy is not the text's test; REVIEW.md scope 2 gives the judgement each needs.")

# point 1: is a run recorded "by its command line, its seed or seed labels and its number of items" in a NAMED file?
named_record = [f for f in files if (re.match(r"studies/m0/NOTES_FIX4_(R1|R2|M1|C1)\.md$", f) or
                (f.startswith(DR) and re.search(r"\.(md|txt|log|out)$", f)))]
other_record = [f for f in files if f.startswith("studies/m0/") and (("NOTES" in f) or "/manifests/" in f)
                and not re.match(r"studies/m0/NOTES_FIX4_", f) and f.endswith((".md", ".json", ".txt"))]
texts_named = {f: show(f) for f in named_record}
texts_other = {f: show(f) for f in other_record}

print()
print("PART 2. point 1: where each proxy rule script is mentioned (a mention is not yet a record of command + seed + N)")
for f in cand:
    base = f.rsplit("/", 1)[-1]
    mod = base[:-3]
    pat = re.compile(re.escape(base) + "|" + re.escape("studies.m0." + mod) + r"\b")
    in_named = sorted(k for k, v in texts_named.items() if pat.search(v))
    in_other = sorted(k for k, v in texts_other.items() if pat.search(v))
    own = show(f)[:4000]
    usage = bool(re.search(r"(Run|Usage)\s*[:(]", own))
    print(f"  {f}")
    print(f"     named record files mentioning it: {len(in_named)}  {[x.replace(DR, '') for x in in_named][:6]}")
    print(f"     NOT-named files mentioning it   : {len(in_other)}  {in_other[:4]}")
    print(f"     own text has a Run/Usage line   : {usage}")

# point 5: exclusion by name pattern
print()
print("PART 3. point 5, first class: files of the M1 record whose names carry attempt / FAILED / SLIP / _try / _v1")
m1_all = sorted(f for f in files if (f.startswith(DR) and re.search(r"/(audit\d?_m1|final_m1)/", f)) or
                (f.startswith("studies/m0/") and re.search(r"(^|/)m1_", f)))
for f in m1_all:
    if re.search(r"attempt|FAILED|SLIP|_try|_v1", f.rsplit("/", 1)[-1]):
        print("  ", f)
print("  files named in the text for M1: audit3_m1/shortcuts_a3_attempt1.py; audit4_m1/shortcuts_a4_attempt1.py + short_trial_n200.json;"
      " final_m1/rules_a5_attempt1.py + rules_repro_n2000_attempt1.json")
for p in ("audit4_m1/short_trial_n200.json", "audit3_m1/short_trial_n200.json", "final_m1/rules_repro_n2000_attempt1.json"):
    print(f"   in the tree of {REC}: {p}: {(DR + p) in files}")
print("  headers naming a superseded version or a kept attempt (point 5: 'every header or report that names a superseded version'):")
for f in m1_py:
    t = show(f)[:3000]
    m = re.search(r"(ATTEMPT \d|VERSION \d|v1 = |[Ss]upersed\w*|attempt 1 kept|kept as \S*attempt\S*)", t)
    if m:
        print(f"    {f}: '{m.group(0)}'")

# point 4(b): generator identity between the commit that first records a run and GEN (static proxy)
print()
print(f"PART 4. point 4(b) static proxy: did any M1 generator file or core.py change between a round's commit and {GEN}?")
gen_files = sorted(f for f in git("ls-tree", "-r", "--name-only", GEN, "studies/m0").splitlines()
                   if re.match(r"studies/m0/(lineages_m1[^/]*|core|solvers_m1)\.py$", f))
rounds = [("1b33b7b2", "M1 batch 1 (implementer screen m1_shortcut_check.py)"),
          ("9e32b317", "first audits (audit_m1/shortcuts_audit.py)"),
          ("163fa419", "M1 fix round rev2 (m1_shortcut_check_rev2.py)"),
          ("a325156e", "third audits (audit3_m1)"),
          ("a790e503", "M1 fix round 3 (m1_fix3_shortcuts.py)"),
          ("03233114", "fourth audits (audit4_m1)")]
for c, what in rounds:
    present_then = set(git("ls-tree", "-r", "--name-only", c, "studies/m0").split())
    common = [g for g in gen_files if g in present_then]
    ch = git("diff", "--name-only", c, GEN, "--", *common).split() if common else []
    added = [g for g in gen_files if g not in present_then]
    print(f"  {c} {what}: generator files present then and changed by {GEN}: {ch or 'none'}; added since: {len(added)}")
defs = [f for f in gen_files if "def tiered_pricing" in show(f, GEN)]
print("  M1.tiered_pricing (carried over unchanged since batch 1) is defined in:", defs)
print("  -> static proxy only; byte identity of items, as point 4(b) asks, needs execution at both trees (not done here).")

print()
print("PART 5. nothing here is a rate, a pooled figure or a status.")
