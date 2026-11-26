"""Step 3 helper: the literal lineage lists / lineage-keyed tables / alias tables written in the unit
scripts at b78e58b1, read by AST (nothing executed), set against the survivor list of record at the
branch tip (studies/m0/manifests/survivor_list_of_record.json, read with git show). Membership only:
no item, rate or lineage figure is computed. Also: pairwise substring relations among survivor ids
(the R1b filter `filt in lid` and the M1a `--only` filter match by substring)."""
import ast, json, subprocess, sys

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
C = "b78e58b1"
TIP = "claude/m0-impl"
D = "docs/reviews/m0-lineage-decision-2026-11-25/"

def show(rev, p):
    return subprocess.run(["git", "-C", REPO, "show", f"{rev}:{p}"], check=True, capture_output=True).stdout.decode()

def assigned(p, name, func=None):
    t = ast.parse(show(C, p))
    nodes = ast.walk(t)
    for n in nodes:
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in n.targets):
            if isinstance(n.value, ast.Dict):
                return n.lineno, [ast.literal_eval(k) for k in n.value.keys], ({ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(n.value.keys, n.value.values)} if all(isinstance(v, ast.Constant) for v in n.value.values) else None)
            return n.lineno, ast.literal_eval(n.value), None
    raise KeyError(name)

def decorator_firsts(p, deco):
    t = ast.parse(show(C, p))
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == deco:
                    out.append(ast.literal_eval(d.args[0]))
    return out

surv = json.loads(show(TIP, "studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]
res = {"survivor_counts": {k: len(v) for k, v in surv.items()}, "tables": {}}

def put(name, path, line, ids, ev, note, alias_map=None):
    ids = list(ids)
    s = set(surv[ev])
    alias_map = alias_map or {}
    def canon(i):
        return alias_map.get(i, i)
    res["tables"][name] = {"path": path, "line": line, "n": len(ids), "note": note,
                           "not_on_survivor_list": sorted(i for i in ids if canon(i) not in s),
                           "survivors_not_in_table": sorted(x for x in s if x not in {canon(i) for i in ids})}

ln, v, _ = assigned(D + "final_c1/f1_draw.py", "SURVIVORS")
put("f1_draw.SURVIVORS (C1c default ids)", D + "final_c1/f1_draw.py", ln, v, "C1", "default lineage list when --ids is not given")
ln, v, _ = assigned(D + "final_c1/f5_closed_forms.py", "FNS")
put("f5_closed_forms.FNS", D + "final_c1/f5_closed_forms.py", ln, v, "C1", "lineage-keyed table (S2 case b)")
ln, v, _ = assigned(D + "final_c1/f5b_closed_forms_v2.py", "FNS")
put("f5b_closed_forms_v2.FNS", D + "final_c1/f5b_closed_forms_v2.py", ln, v, "C1", "lineage-keyed table (S2 case b)")
ln, v, _ = assigned(D + "final_r2/f_rules.py", "SURV")
put("f_rules.SURV (R2b default names)", D + "final_r2/f_rules.py", ln, ["R2." + x for x in v], "R2", "default list when argv[3] is not given; names written without 'R2.'")
nh = sorted(set(decorator_firsts(D + "final_r2/f_new_heur.py", "rule")))
put("f_new_heur.NEW keys (R2b f_rules_new lineages)", D + "final_r2/f_new_heur.py", None, ["R2." + x for x in nh], "R2", "lineage-keyed table built by the @rule decorator; f_rules_new runs sorted(NEW)")
# new_rules_final SPEC: dict literal with non-constant values -> keys only
t = ast.parse(show(C, D + "final_r1/new_rules_final.py"))
for n in ast.walk(t):
    if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "SPEC" for x in n.targets):
        put("new_rules_final.SPEC (R1c lineages)", D + "final_r1/new_rules_final.py", n.lineno, [ast.literal_eval(k) for k in n.value.keys], "R1", "lineage-keyed table (S2 case b); the only lineage selection of R1c")
t = ast.parse(show(C, D + "final_r1/run_rules_final.py"))
for n in ast.walk(t):
    if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "FEATS" for x in n.targets):
        put("run_rules_final.feat_defs FEATS (R1b fitted lookups)", D + "final_r1/run_rules_final.py", n.lineno, [ast.literal_eval(k) for k in n.value.keys], "R1", "lineage-keyed rule table; lineages run are argv ids or fgen.lineages()")
for nm in ("FEATS_1", "FEATS_2"):
    t = ast.parse(show(C, "studies/m0/r1_fix4_tells.py"))
    for n in ast.walk(t):
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == nm for x in n.targets):
            keys = [ast.literal_eval(k) for k in n.value.keys]
            res["tables"][f"r1_fix4_tells.{nm} (R1a lookups, keyed by base id)"] = {"path": "studies/m0/r1_fix4_tells.py", "line": n.lineno, "keys": keys,
                "survivor_bases_matching": sorted(x for x in surv["R1"] if any(x.split('.', 1)[1].rsplit('_r', 1)[0] == k or x.split('.', 1)[1] == k for k in keys))}
alias = {}
for nm, p in (("RULE_ALIAS", "studies/m0/c1_fix4_draw.py"), ("A3_ALIAS", "studies/m0/c1_fix4_a3_run.py"), ("A3_OLD", D + "final_c1/f3_a3_run.py"), ("ALIAS", D + "final_c1/f1_draw.py")):
    ln, keys, m = assigned(p, nm)
    alias[nm] = {"path": p, "line": ln, "n": len(keys), "map": m}
a3a, a3o = alias["A3_ALIAS"]["map"], alias["A3_OLD"]["map"]
res["alias_tables"] = alias
res["A3_ALIAS_vs_A3_OLD"] = {"only_in_A3_ALIAS": sorted(set(a3a) - set(a3o)), "only_in_A3_OLD": sorted(set(a3o) - set(a3a)),
                             "same_key_different_value": sorted(k for k in set(a3a) & set(a3o) if a3a[k] != a3o[k])}
res["RULE_ALIAS_vs_f1_ALIAS_equal"] = alias["RULE_ALIAS"]["map"] == alias["ALIAS"]["map"]
sub = {}
for ev, ids in surv.items():
    pairs = sorted([a, b] for a in ids for b in ids if a != b and a in b)
    sub[ev] = pairs
res["survivor_id_substring_pairs"] = sub
json.dump(res, sys.stdout, sort_keys=True, indent=2)
sys.stdout.write("\n")
