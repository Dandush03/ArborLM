"""M1a's --only matches by substring (m1_fix4_battery.py:211). Check, by reading names only (no execution), whether
any M1 survivor id is a proper substring of another M1 id visible in the M1 builder modules: function names
(`def <name>`) and quoted "M1.<name>" literals in lineages_m1_fix3{,_a,_b,_c}.py and lineages_m1_fix4.py at
b78e58b1. The full id set of load_all() needs execution and is not enumerated here."""
import json, re, subprocess, sys
REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
def show(rev, p):
    return subprocess.run(["git", "-C", REPO, "show", f"{rev}:{p}"], check=True, capture_output=True).stdout.decode()
names = set()
for m in ("lineages_m1_fix3_a", "lineages_m1_fix3_b", "lineages_m1_fix3_c", "lineages_m1_fix4", "lineages_m1_fix3"):
    s = show("b78e58b1", f"studies/m0/{m}.py")
    names |= set(re.findall(r"^def ([a-z0-9_]+)", s, re.M)) | set(re.findall(r'"M1\.([a-z0-9_]+)"', s))
surv = json.loads(show("claude/m0-impl", "studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]["M1"]
hits = {sid: sorted("M1." + n for n in names if sid in "M1." + n and "M1." + n != sid) for sid in surv}
json.dump({"names_seen": len(names), "survivor_substring_hits": {k: v for k, v in hits.items() if v}}, sys.stdout, sort_keys=True, indent=2)
sys.stdout.write("\n")
