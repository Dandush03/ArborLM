"""Copy auditor, step 4: the four run-plan fragments against point 4 (seeds), items per level, lineage lists, id maps and must-contain lists.
Own code; reads the plans, the survivor list, the seed file and the committed scripts (git show b78e58b1, parsed with ast, never executed).
python3 -I a4_plans.py  -> a4_plans.out.txt"""
import ast, hashlib, json, re, subprocess
from pathlib import Path

WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
SPEC_WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
C = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
D = "docs/reviews/m0-lineage-decision-2026-11-25/"
FR = Path(WT) / "studies/m0/fresh_run"
out, problems = [], []

def say(s): out.append(s)
def bad(s): problems.append(s); out.append("  PROBLEM: " + s)
def show(p): return subprocess.run(["git", "-C", WT, "show", f"{C}:{p}"], check=True, capture_output=True, text=True).stdout
def h8(s): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")

# ---------------- point 4: seeds
BASES = {"1": h8("400002|fresh-shortcut|1"), "2": h8("400002|fresh-shortcut|2"), "3": h8("400002|fresh-shortcut|3"), "dry": h8("400002|fresh-shortcut-dry-run")}
TEXT_BASES = {"1": 16103270370041696293, "2": 10773834973117025986, "3": 619660634241804713, "dry": 3342082268851962967}
say(f"bases recomputed: {BASES}; equal to the approved text's: {BASES == TEXT_BASES}")
if BASES != TEXT_BASES: bad("bases differ from the approved text")
ROLES = {"R1a": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat1_fit", "feat1_test", "feat2_fit", "feat2_test"],
         "R1b": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat_fit", "feat_test"], "R1c": ["fit", "test"],
         "R2a": ["tag"], "R2b": ["tag"], "M1a": ["own", "a4", "a3"], "M1b": ["seed"], "M1c": ["seed"], "C1a": ["seed"], "C1b": ["seed"], "C1c": ["seed"]}
SEED = {(s, u, r): h8(f"{b}|{u}|{r}") for s, b in BASES.items() for u, rs in ROLES.items() for r in rs}
say(f"seed integers computed: {len(SEED)} (+4 bases); all distinct: {len(set(SEED.values()) | set(BASES.values())) == len(SEED) + 4}")
# compare with part A of the committed seed file
sf = (Path(SPEC_WT) / "docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev6_fresh_run.out.txt").read_text()
say("seed file sha256 " + hashlib.sha256(sf.encode()).hexdigest())
pa = {}
for m in re.finditer(r"^\s+(R1a|R1b|R1c|R2a|R2b|M1a|M1b|M1c|C1a|C1b|C1c)\s+(\w+)\s+'(\d+)\|\1\|\2' -> (\d+)$", sf, re.M):
    base = int(m.group(3)); s = [k for k, v in BASES.items() if v == base][0]
    pa[(s, m.group(1), m.group(2))] = int(m.group(4))
say(f"part A entries parsed: {len(pa)}; equal to mine: {pa == SEED}")
if pa != SEED: bad("part A differs from my derivation")
ALLINTS = set(SEED.values()) | set(BASES.values())
SURV = json.loads((Path(WT) / "studies/m0/manifests/survivor_list_of_record.json").read_text())["evaluations"]
ITEMS = {"R1": 3000, "R2": 4000, "M1": 4000, "C1": 2000}

def big_ints(obj):
    """every standalone integer (int or all-digit string) with >= 7 digits anywhere in obj"""
    acc = []
    if isinstance(obj, dict):
        for v in obj.values(): acc += big_ints(v)
    elif isinstance(obj, list):
        for v in obj: acc += big_ints(v)
    elif isinstance(obj, bool): pass
    elif isinstance(obj, int):
        if obj >= 10**6: acc.append(obj)
    elif isinstance(obj, str):
        if re.fullmatch(r"\d{7,}", obj): acc.append(int(obj))
        for m in re.finditer(r"(?<![\w/])(\d{7,})(?![\w/])", obj) if not re.fullmatch(r"\d{7,}", obj) else []:
            acc.append(int(m.group(1)))
    return acc

def commands(ev, plan):
    """(unit, set, argv, env, run-object) for every command of the plan"""
    res = []
    for u, U in plan["units"].items():
        if ev in ("R1", "M1"):
            for s, r in U["runs"].items():
                res.append((u, s.replace("seed", ""), r["argv"], r["env"], r))
        elif ev == "R2":
            for s, r in U["runs"].items():
                for c in r["commands"]:
                    res.append((u, s, c["argv"], r["environment"], r))
        else:
            for s, r in U.items():
                for c in r["chain"]:
                    res.append((u, s, c["argv"], c["env_set"], r))
    return res

def check_ints(ev, plan, cmds):
    say(f"[{ev}] integers: every >=7-digit integer in each run object must be its unit/set's seed or base")
    for u, s, argv, env, r in cmds:
        found = set(big_ints(r))
        allowed = {SEED[(s, u, ro)] for ro in ROLES[u]} | {BASES[s]}
        extra = found - allowed
        # numbers inside paths such as 20261126 are excluded by the regex; a date-like 8-digit token is reported if it appears standalone
        if extra: bad(f"{ev} {u} set {s}: integers not of this unit/set: {sorted(extra)}")
        missing = {SEED[(s, u, ro)] for ro in ROLES[u]} - set(big_ints({"a": argv, "e": env}))
        if missing and not (ev == "R2" or ev == "C1"):
            bad(f"{ev} {u} set {s}: seed integers absent from argv/env: {missing}")
    # outside the run objects: any big integer must be in ALLINTS
    rest = big_ints({k: v for k, v in plan.items() if k != "units"})
    stray = set(rest) - ALLINTS
    say(f"[{ev}] integers outside the units: {len(rest)}; not seeds/bases: {sorted(stray)}")

def pos_checks(ev, cmds):
    for u, s, argv, env, r in cmds:
        N = 20 if s == "dry" else ITEMS[ev]
        sd = lambda ro: str(SEED[(s, u, ro)])
        a = argv[4:] if argv[:4] == ["uv", "run", "--locked", "python"] else None
        if a is None: bad(f"{u} {s}: argv does not start with 'uv run --locked python': {argv[:5]}"); continue
        if a[0] == "-I": a = a[1:]
        if a[0] == "-m": script, rest = a[1], a[2:]
        else: script, rest = a[0], a[1:]
        ok = True
        if u == "R1a":
            ok = script == "studies.m0.fresh_run.r1.r1_fix4_measure" and rest[:5] == [str(N), sd("aud_seed"), sd("aud_fit"), sd("impl_seed"), sd("impl_fit")] \
                and sorted(rest[6:]) == SURV["R1"] and len(rest[6:]) == 10 \
                and env.get("M0FR_R1A_FEAT1_FIT") == sd("feat1_fit") and env.get("M0FR_R1A_FEAT1_TEST") == sd("feat1_test") \
                and env.get("M0FR_R1A_FEAT2_FIT") == sd("feat2_fit") and env.get("M0FR_R1A_FEAT2_TEST") == sd("feat2_test")
        elif u == "R1b":
            ok = script == D + "final_r1/run_rules_final.py" and rest[:8] == [str(N), sd("aud_seed"), sd("aud_fit"), sd("impl_seed"), sd("impl_fit"), sd("feat_fit"), sd("feat_test"), str(N)] \
                and sorted(rest[9:]) == SURV["R1"] and len(rest[9:]) == 10
        elif u == "R1c":
            ok = script == "studies/m0/fresh_run/r1/new_rules_final.py" and rest == [str(N), sd("fit"), sd("test")] \
                and env.get("PYTHONPATH", "").split(":")[-1].endswith("final_r1")
        elif u == "R2a":
            i = rest.index("--only"); ids = rest[i + 1].split(",")
            ok = script == "studies.m0.fresh_run.r2.r2_fix4_battery" and rest[0] == "run" and rest[rest.index("--n") + 1] == str(N) \
                and rest[rest.index("--seeds") + 1] == "f4" and sorted(ids) == SURV["R2"] and env.get("M0_FR_TAG") == sd("tag")
        elif u == "R2b":
            if script.endswith("f_rules.py"):
                ok = script == "studies/m0/fresh_run/r2/f_rules.py" and rest[0] == str(N) and sorted("R2." + x for x in rest[2].split(",")) == SURV["R2"] and len(rest) == 3
            else:
                ok = script == "studies/m0/fresh_run/r2/f_rules_new.py" and rest[0] == str(N) and len(rest) == 2
            ok = ok and env.get("M0_FR_TAG") == sd("tag")
        elif u == "M1a":
            i = rest.index("--only"); ids = rest[i + 1].split(",")
            ok = script == "studies.m0.fresh_run.m1.m1_fix4_battery" and rest[rest.index("--n") + 1] == str(N) and sorted(ids) == SURV["M1"] \
                and env.get("M1A_SEED_OWN") == sd("own") and env.get("M1A_SEED_A4") == sd("a4") and env.get("M1A_SEED_A3") == sd("a3")
        elif u in ("M1b", "M1c"):
            ok = script == D + ("final_m1/rules_a5.py" if u == "M1b" else "final_m1/rules_a5_attempt1.py") and rest[:3] == ["fresh", str(N), sd("seed")] and len(rest) == 4
        elif u in ("C1a", "C1b", "C1c"):
            if "--seed" in rest:
                ok = rest[rest.index("--seed") + 1] == sd("seed") and rest[rest.index("--per-level") + 1] == str(N)
                key = "--only" if "--only" in rest else "--ids"
                ids = rest[rest.index(key) + 1].split(",")
                r["_ids_" + script] = ids
            if script == "studies.m0.c1_fix4_a3_run":
                ok = rest[rest.index("--timeout") + 1] == "3000"
        say(f"  {u} set {s:3s} {'OK ' if ok else 'BAD'} {script}")
        if not ok: bad(f"{u} set {s}: positional/env check failed: {argv} {env}")

plans = {ev: json.loads((FR / ev.lower() / f"run_plan_{ev.lower()}.json").read_text()) for ev in ("R1", "R2", "M1", "C1")}
for ev, plan in plans.items():
    say(f"\n===== {ev} plan sha256 {hashlib.sha256((FR / ev.lower() / f'run_plan_{ev.lower()}.json').read_bytes()).hexdigest()}")
    cmds = commands(ev, plan)
    sets = sorted({(u, s) for u, s, *_ in cmds})
    say(f"[{ev}] units x sets: {len(sets)} {sets}")
    check_ints(ev, plan, cmds)
    pos_checks(ev, cmds)

# ---------------- C1 alias tables, parsed from the committed scripts
def literal(src, name):
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)
RULE_ALIAS = literal(show("studies/m0/c1_fix4_draw.py"), "RULE_ALIAS")
A3_ALIAS = literal(show("studies/m0/c1_fix4_a3_run.py"), "A3_ALIAS")
ALIAS = literal(show(D + "final_c1/f1_draw.py"), "ALIAS")
A3_OLD = literal(show(D + "final_c1/f3_a3_run.py"), "A3_OLD")
F1_SURV = literal(show(D + "final_c1/f1_draw.py"), "SURVIVORS")
say(f"\nC1 tables: RULE_ALIAS {len(RULE_ALIAS)}, ALIAS {len(ALIAS)} (equal to RULE_ALIAS: {ALIAS == RULE_ALIAS}), A3_ALIAS {len(A3_ALIAS)}, A3_OLD {len(A3_OLD)} (A3_OLD subset of A3_ALIAS with same values: {all(A3_ALIAS.get(k) == v for k, v in A3_OLD.items())}); keys in A3_ALIAS not in A3_OLD: {sorted(set(A3_ALIAS) - set(A3_OLD))}")
S1 = SURV["C1"]
def drawname(sid, alias): return alias.get(sid, sid)          # 'lid' written in the draw and file base
exp = {}
for unit, alias, a3 in (("C1a", RULE_ALIAS, A3_ALIAS), ("C1c", ALIAS, A3_OLD)):
    files, keys, own_keys = {}, {}, {}
    for sid in S1:
        dn = drawname(sid, alias); base = dn.replace("C1.", "")
        old = a3.get(dn)
        if old:
            files[base + "__alias.json"] = sid; files[base + "__own.json"] = sid; keys[old] = sid
        else:
            files[base + "__own.json"] = sid
        own_keys[dn] = sid
    exp[unit] = (files, keys, own_keys)
    say(f"{unit}: draw files {len(S1)}; a3 files possible {len(files)}; alias keys {len(keys)}; own keys {len(own_keys)}; lineages with no a3 alias: {[s for s in S1 if not a3.get(drawname(s, alias))]}")
c1 = plans["C1"]
for unit in ("C1a", "C1c"):
    files, keys, own_keys = exp[unit]
    for s, r in c1["units"][unit].items():
        im = r["id_map"]
        a3m = im["a3_file_name_and_key"]
        if a3m["files_to_survivor_id"] != files: bad(f"{unit} {s}: a3 file map differs: {set(a3m['files_to_survivor_id'].items()) ^ set(files.items())}")
        if a3m["key_in_alias_file_to_survivor_id"] != keys: bad(f"{unit} {s}: alias key map differs: {set(a3m['key_in_alias_file_to_survivor_id'].items()) ^ set(keys.items())}")
        other = {k: v for k, v in im.items() if k != "a3_file_name_and_key"}
        r["_other_maps"] = other
        # must_contain per survivor of the a3 dir
        a3dir = [k for k in r["must_contain"] if k.endswith("/a3")][0]
        ps = r["must_contain"][a3dir]["per_survivor"]
        if sorted(ps) != S1: bad(f"{unit} {s}: a3 must_contain lineages != survivors")
        for sid, e in ps.items():
            dn = drawname(sid, ALIAS if unit == "C1c" else RULE_ALIAS); base = dn.replace("C1.", "")
            old = (A3_OLD if unit == "C1c" else A3_ALIAS).get(dn)
            want_primary = (base + ("__alias.json" if old else "__own.json"), old if old else dn)
            got_primary = (Path(e["primary_file"]).name, e["primary_key_in_file"])
            want_fb = (base + "__own.json", dn) if old else (None, None)
            got_fb = (Path(e["fallback_file"]).name if e["fallback_file"] else None, e["fallback_key_in_file"])
            if want_primary != got_primary or want_fb != got_fb or e["run_log_key"] != dn:
                bad(f"{unit} {s} {sid}: a3 entry {got_primary} {got_fb} {e['run_log_key']} expected {want_primary} {want_fb} {dn}")
    say(f"{unit}: a3 file/key maps and must_contain checked for every set")
# print the other C1 maps for manual reading (one set)
for unit in ("C1a", "C1b", "C1c"):
    r = c1["units"][unit]["1"]
    say(f"\n{unit} id_map keys: {list(r['id_map'])}")
    for k, v in r["id_map"].items():
        if k != "a3_file_name_and_key": say(f"  {k}: {json.dumps(v)[:3000]}")
    say(f"{unit} must_contain keys: " + json.dumps({Path(k).name if '/' in k else k: (list(v) if isinstance(v, dict) else v) for k, v in r["must_contain"].items()})[:3000])

# C1 command-line ids
for s in ("1", "2", "3", "dry"):
    for unit in ("C1a", "C1b", "C1c"):
        for c in c1["units"][unit][s]["chain"]:
            a = c["argv"]
            for key in ("--ids", "--only"):
                if key in a:
                    ids = a[a.index(key) + 1].split(",")
                    if unit == "C1b":
                        swap = {v: k for k, v in RULE_ALIAS.items()}
                        want = sorted(RULE_ALIAS.get(x, x) for x in S1)
                        if sorted(ids) != want: bad(f"C1b {s}: --only {ids} != {want}")
                        mapped = sorted(swap.get(x, x) for x in ids)
                        if mapped != S1: bad(f"C1b {s}: output keys after SWAP != survivors")
                    else:
                        if sorted(ids) != S1: bad(f"{unit} {s}: {key} != survivors")
say("\nC1 --ids / --only lists checked for all sets (C1b: RULE_ALIAS names, SWAP back to survivors)")
say(f"C1c: f1_draw SURVIVORS minus survivor list: {sorted(set(F1_SURV) - set(S1))}; survivor list minus SURVIVORS: {sorted(set(S1) - set(F1_SURV))}")

# ---------------- lineage tables (S2b and must-contain)
def fns_keys(path):
    return list(literal(show(path) if not path.startswith("/") else Path(path).read_text(), "FNS").keys()) if False else None
def dict_keys_of(src, name):
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets) and isinstance(node.value, ast.Dict):
            return [ast.literal_eval(k) for k in node.value.keys]
    raise KeyError(name)
def new_keys(src):
    ks = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef):
            for dcr in node.decorator_list:
                if isinstance(dcr, ast.Call) and getattr(dcr.func, "id", "") == "rule":
                    ks.append(ast.literal_eval(dcr.args[0]))
    return ks
tabs = [("R1", "SPEC", D + "final_r1/new_rules_final.py", "r1/new_rules_final.py", lambda k: k),
        ("C1", "FNS", D + "final_c1/f5_closed_forms.py", "c1/f5_closed_forms.py", lambda k: k),
        ("C1", "FNS", D + "final_c1/f5b_closed_forms_v2.py", "c1/f5b_closed_forms_v2.py", lambda k: k)]
for ev, name, op, cp, norm in tabs:
    ko = dict_keys_of(show(op), name); kc = dict_keys_of((FR / cp).read_text(), name)
    removed = [k for k in ko if k not in kc]; added = [k for k in kc if k not in ko]
    nonsurv = [k for k in ko if norm(k) not in SURV[ev]]
    say(f"\n{cp} {name}: original {ko}; copy {kc}; removed {removed}; added {added}; non-survivors in original {nonsurv}; order kept {[k for k in ko if k in kc] == kc}")
    if removed != nonsurv or added: bad(f"{cp}: S2b removal is not exactly the non-survivors")
ko = new_keys(show(D + "final_r2/f_new_heur.py")); kc = new_keys((FR / "r2/f_new_heur.py").read_text())
from collections import Counter
co, cc = Counter(ko), Counter(kc)
removed = {k: co[k] - cc.get(k, 0) for k in co if co[k] != cc.get(k, 0)}
nonsurv = sorted({k for k in co if "R2." + k not in SURV["R2"]})
say(f"\nf_new_heur NEW: original keys {dict(co)}\n  copy keys {dict(cc)}\n  removed (entries per key) {removed}; non-survivor keys in original {nonsurv}; survivors in copy's NEW {sorted('R2.' + k for k in cc)}")
if sorted(removed) != nonsurv or any(removed[k] != co[k] for k in removed) or set(cc) - set(co): bad("f_new_heur: S2b removal is not exactly the non-survivor entries")
# must-contain checks against the tables
r2 = plans["R2"]
for s, r in r2["units"]["R2b"]["runs"].items():
    for c in r["commands"]:
        if c["name"] == "f_rules_new":
            want = sorted("R2." + k for k in cc)
            if sorted(c["must_contain"]) != want: bad(f"R2b {s} f_rules_new must_contain {c['must_contain']} != {want}")
        else:
            if sorted(c["must_contain"]) != SURV["R2"]: bad(f"R2b {s} f_rules must_contain != survivors")
    if r2["units"]["R2b"]["runs"]: pass
for s, r in r2["units"]["R2a"]["runs"].items():
    for c in r["commands"]:
        if sorted(c["must_contain"]) != SURV["R2"]: bad(f"R2a {s} must_contain != survivors")
say("R2 must_contain checked (R2a, f_rules: 17 survivors; f_rules_new: NEW keys of the copy)")
r1 = plans["R1"]
spec_c = dict_keys_of((FR / "r1/new_rules_final.py").read_text(), "SPEC")
for u in ("R1a", "R1b"):
    mc = r1["units"][u]["must_contain"]
    if sorted(mc["aud_and_impl_files_for_every_lineage"]) != SURV["R1"]: bad(f"{u} must_contain aud/impl != survivors")
say(f"R1a feat rows for {r1['units']['R1a']['must_contain']['feat_files_with_rows_for']}")
say(f"R1b feat rows for {r1['units']['R1b']['must_contain']['feat_files_with_rows_for']}; feat_defs keys {dict_keys_of(show(D + 'final_r1/run_rules_final.py'), 'FEATS')}")
mc = r1["units"]["R1c"]["must_contain"]
say(f"R1c must_contain {mc}; SPEC of the copy {spec_c}")
if sorted(list(mc.values())[0]) != sorted(spec_c): bad("R1c must_contain != SPEC keys of copy")
# FEATS_1 / FEATS_2 keys of r1_fix4_tells (base names) for R1a feat rows
tsrc = show("studies/m0/r1_fix4_tells.py")
say("r1_fix4_tells FEATS_1 keys " + str(dict_keys_of(tsrc, "FEATS_1")) + " FEATS_2 keys " + str(dict_keys_of(tsrc, "FEATS_2")))
m1 = plans["M1"]
for u, U in m1["units"].items():
    for s, r in U["runs"].items():
        lst = r.get("survivor_lineages_the_output_must_contain") or None
        if lst is not None and sorted(lst) != SURV["M1"]: bad(f"{u} {s} must_contain != survivors")
        if r["items_per_level"] != (20 if s == "dry" else 4000): bad(f"{u} {s} items_per_level")
        if r["must_contain"]["expected_row_N"] != (20 if s == "dry" else 4000): bad(f"{u} {s} expected_row_N {r['must_contain']['expected_row_N']}")
say(f"M1 id_map_to_survivor_id keys {list(m1['id_map_to_survivor_id'])}; identity for every survivor: {all(all(k == v for k, v in mp.items()) and sorted(mp) == SURV['M1'] for mp in m1['id_map_to_survivor_id'].values())}")
for u in ("C1a", "C1b", "C1c"):
    for s, r in c1["units"][u].items():
        if r["items_per_level"] != (20 if s == "dry" else 2000): bad(f"{u} {s} items_per_level")
for ev, plan in (("R1", r1),):
    for u, U in plan["units"].items():
        for s, r in U["runs"].items():
            if r["items_per_level"] != (20 if s == "dry" else 3000): bad(f"{u} {s} items_per_level")
for u, U in r2["units"].items():
    for s, r in U["runs"].items():
        if r["items_per_level"] != (20 if s == "dry" else 4000): bad(f"{u} {s} items_per_level")
say("items_per_level fields checked in all four plans")

say(f"\nPROBLEMS: {len(problems)}")
for p in problems: say(" - " + p)
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
