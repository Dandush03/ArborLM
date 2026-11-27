"""Copy auditor, step 5: units with no copy (and M1a's --only) give every survivor and only survivors?
Uses a3_registry_ids.out.json (ids of the registries the selection code reads) and the survivor list. python3 -I a5_selection.py"""
import json, subprocess
from pathlib import Path
H = Path(__file__).resolve().parent
WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
reg = json.loads((H / "a3_registry_ids.out.json").read_text())
S = json.loads((Path(WT) / "studies/m0/manifests/survivor_list_of_record.json").read_text())["evaluations"]
RULE_ALIAS = {"C1.sieve_marking_f4": "C1.sieve_marking_f3", "C1.fast_power_f4": "C1.fast_power_f3", "C1.func_branch_f4": "C1.func_branch",
              "C1.func_compose_f4": "C1.func_compose_f3", "C1.slices_f4": "C1.slices"}  # as parsed in a4_plans (equal to ALIAS)
out = []
def sub_hits(only, universe):
    """the M1a / R1b rule: an id is selected if any given string is a substring of it"""
    return sorted(i for i in universe if any(o in i for o in only))
# R1a: exact keys of r1_fix4_gen.lineages() = candidates_v4
out.append(f"R1a: survivors in candidates_v4: {all(s in reg['R1.candidates_v4'] for s in S['R1'])}; selection is exact (gen.lineages()[lid])")
# R1b: per process, heuristics4.main keeps lid of gen4.lineages() (= registered_v4) with filt in lid
for s in S["R1"]:
    hit = sub_hits([s], reg["R1.registered_v4"])
    if hit != [s]: out.append(f"R1b PROBLEM: filter {s} selects {hit}")
out.append(f"R1b: survivors in registered_v4: {all(s in reg['R1.registered_v4'] for s in S['R1'])}; registered_v4 minus survivors: {sorted(set(reg['R1.registered_v4']) - set(S['R1']))}; "
           f"substring filter selects exactly its own id for every survivor: {all(sub_hits([s], reg['R1.registered_v4']) == [s] for s in S['R1'])}")
# M1a
sel = sub_hits(S["M1"], reg["M1.load_all"])
out.append(f"M1a: load_all {len(reg['M1.load_all'])} ids; --only (29 survivor ids, substring rule) selects {len(sel)}; equal to survivors: {sel == S['M1']}; extra: {sorted(set(sel) - set(S['M1']))}")
coll = {s: [i for i in reg["M1.load_all"] if s in i and i != s] for s in S["M1"]}
out.append(f"M1a: survivor ids that are substrings of another load_all id: { {k: v for k, v in coll.items() if v} }")
man = json.loads(subprocess.run(["git", "-C", WT, "show", "b78e58b1:studies/m0/manifests/m1_fix4_survivors.json"], capture_output=True, text=True, check=True).stdout)
out.append(f"M1b/M1c: survivors() asserts load_registered == m1_fix4_survivors.json 'survivors'; that field equals the survivor list: {sorted(man['survivors']) == S['M1']}; load_registered equals it: {reg['M1.load_registered'] == S['M1']}")
# R2
out.append(f"R2a: survivors in fix4_set: {all(s in reg['R2.fix4_set'] for s in S['R2'])}; --only is an exact-membership filter (want set)")
out.append(f"R2b f_rules: 'R2.'+name looked up exactly in fix4_set; all 17 present: {all(s in reg['R2.fix4_set'] for s in S['R2'])}")
# C1
out.append(f"C1a/C1c draws: survivors in lineages_c1_fix4.all_written: {all(s in reg['C1.all_written'] for s in S['C1'])}; missing {sorted(set(S['C1']) - set(reg['C1.all_written']))}")
bn = [RULE_ALIAS.get(s, s) for s in S["C1"]]
known = set(reg["C1.bat.all_lineages"]) | {v for v in RULE_ALIAS.values()}
out.append(f"C1b: --only names (RULE_ALIAS names) all known to the battery (all_lineages() plus the patched SWAP names): {all(b in known for b in bn)}; missing {sorted(set(bn) - known)}; "
           f"alias names already in unpatched all_lineages(): {sorted(set(RULE_ALIAS.values()) & set(reg['C1.bat.all_lineages']))}")
out.append(f"C1b: survivor ids ending _f4 passed raw would fail (not in all_lineages): {[s for s in S['C1'] if s.endswith('_f4') and s in reg['C1.bat.all_lineages']]} (empty = they would fail; plan passes alias names)")
txt = "\n".join(out) + "\n"
(H / "a5_selection.out.txt").write_text(txt)
print(txt)
