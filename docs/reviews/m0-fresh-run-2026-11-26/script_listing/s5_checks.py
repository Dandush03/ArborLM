"""Step 3/4 helper checks (read-only, git show only; nothing executed):
(a) every file of the closure (listed + dependencies) has the same blob at b78e58b1 and at the branch tip;
(b) the M1 manifest that fm1_common.survivors() asserts against vs the survivor list of record (M1);
(c) R1c (new_rules_final.py) prints rule names truncated to 60 characters: the names it can print, from the
    literal lookup names in SPEC and the literal keys of the dicts its rule functions return, and their lengths."""
import ast, json, os, subprocess, sys

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
H = os.path.dirname(os.path.abspath(__file__))
def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], check=True, capture_output=True).stdout.decode()
def blob(rev, p):
    try:
        return git("rev-parse", f"{rev}:{p}").strip()
    except subprocess.CalledProcessError:
        return None
L = json.load(open(os.path.join(H, "script_listing.json")))
out = {}
paths = [e["path"] for e in L["listed"]] + [e["path"] for e in L["dependencies"]]
out["closure_files"] = len(paths)
out["closure_blob_differs_b78_vs_tip"] = sorted(p for p in paths if blob("b78e58b1", p) != blob("claude/m0-impl", p))
out["closure_blob_differs_b78_vs_7cd0ac5a"] = sorted(p for p in paths if blob("b78e58b1", p) != blob("7cd0ac5a", p))
out["tip"] = git("rev-parse", "claude/m0-impl").strip()
man = json.loads(git("show", "b78e58b1:studies/m0/manifests/m1_fix4_survivors.json"))["survivors"]
rec = json.loads(git("show", "claude/m0-impl:studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]["M1"]
out["m1_manifest_vs_record"] = {"manifest_n": len(man), "record_n": len(rec), "only_manifest": sorted(set(man) - set(rec)), "only_record": sorted(set(rec) - set(man))}
src = git("show", "b78e58b1:docs/reviews/m0-lineage-decision-2026-11-25/final_r1/new_rules_final.py")
t = ast.parse(src)
names = set()
for n in ast.walk(t):
    if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "SPEC" for x in n.targets):
        for v in n.value.values:
            for k2, v2 in zip(v.keys, v.values):
                if ast.literal_eval(k2) == "lookup":
                    names |= {"lookup " + ast.literal_eval(k) for k in v2.keys}
    if isinstance(n, ast.Dict):
        for k in n.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value not in ("rules", "lookup"):
                names.add(k.value)
for n in ast.walk(t):
    if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "out" and isinstance(n.slice, ast.Constant):
        names.add(n.slice.value)
long = sorted(x for x in names if len(x) > 60)
trunc = {}
for x in names:
    trunc.setdefault(x[:60], []).append(x)
out["r1c_name_candidates_n"] = len(names)
out["r1c_names_over_60"] = long
out["r1c_truncation_collisions"] = {k: sorted(v) for k, v in trunc.items() if len(v) > 1}
json.dump(out, sys.stdout, sort_keys=True, indent=2)
sys.stdout.write("\n")
