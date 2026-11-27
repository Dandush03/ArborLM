"""Second, independent derivation of the closed list of uncounted rules (ADR-0033 addendum 1, draft 7 at d70ba38d,
section 4A stage 1S point 8). Written by an arbor-auditor context (Claude Opus 5.5) that wrote none of the lineages, rule
scripts or the first list, and did not read the first derivation.

Reads committed files at b78e58b1 through `git show`, parses them with `ast`, and copies literals. It executes none of
them (no exec, no import of them, no eval of their code). Standard library only.

usage (from the implementation worktree root):
  uv run --locked python <this file> <impl_worktree> <out_dir>
"""
import ast
import hashlib
import json
import re
import subprocess
import sys

COMMIT = "b78e58b1"
D = "docs/reviews/m0-lineage-decision-2026-11-25"
P = {
    "final_table4": f"{D}/audit4_r1/final_table4.py",
    "pool_final_r1": f"{D}/final_r1/pool_final.py",
    "r1_fix3_battery": "studies/m0/r1_fix3_battery.py",
    "new_rules_final_r1": f"{D}/final_r1/new_rules_final.py",
    "f_pool": f"{D}/final_r2/f_pool.py",
    "r2_fix4_battery": "studies/m0/r2_fix4_battery.py",
    "f_new_heur": f"{D}/final_r2/f_new_heur.py",
    "f_rules": f"{D}/final_r2/f_rules.py",
    "f_rules_new": f"{D}/final_r2/f_rules_new.py",
    "short_summary_a4": f"{D}/audit4_m1/short_summary_a4.py",
    "pool_a5": f"{D}/final_m1/pool_a5.py",
    "shortcuts_a3": f"{D}/audit3_m1/shortcuts_a3.py",
    "m1_fix3_shortcuts": "studies/m0/m1_fix3_shortcuts.py",
    "m1_fix4_battery": "studies/m0/m1_fix4_battery.py",
    "rules_a5": f"{D}/final_m1/rules_a5.py",
    "rules_a5_attempt1": f"{D}/final_m1/rules_a5_attempt1.py",
    "f4b_pool_v2": f"{D}/final_c1/f4b_pool_v2.py",
    "s4_rules_v2": f"{D}/audit4_c1/s4_rules_v2.py",
    "s5_analyse_v2": f"{D}/audit4_c1/s5_analyse_v2.py",
    "c1_fix3_battery": "studies/m0/c1_fix3_battery.py",
    "a3_shortcuts_c1": f"{D}/audit3_c1/a3_shortcuts.py",
    "f5_closed_forms": f"{D}/final_c1/f5_closed_forms.py",
    "f5b_closed_forms_v2": f"{D}/final_c1/f5b_closed_forms_v2.py",
}

IMPL = sys.argv[1]
OUT = sys.argv[2]
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s)


SRC, TREE, HASH = {}, {}, {}
for k, p in P.items():
    b = subprocess.run(["git", "-C", IMPL, "show", f"{COMMIT}:{p}"], check=True, capture_output=True).stdout
    HASH[p] = hashlib.sha256(b).hexdigest()
    SRC[k] = b.decode()
    TREE[k] = ast.parse(SRC[k])


def mod_assign(key, name):
    for node in TREE[key].body:
        tgt = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            tgt = node.target.id
        if tgt == name:
            return node
    raise SystemExit(f"STOP: {name} not assigned at module level of {P[key]}")


def str_elts(node):
    """[(literal, lineno)] of a set/list/tuple display of string constants; stops on anything else."""
    if not isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        raise SystemExit(f"STOP: not a display: {ast.dump(node)[:80]}")
    out = []
    for e in node.elts:
        if not (isinstance(e, ast.Constant) and isinstance(e.value, str)):
            raise SystemExit(f"STOP: non-literal element {ast.dump(e)[:80]}")
        out.append((e.value, e.lineno))
    return out


def func(key, name):
    for node in TREE[key].body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise SystemExit(f"STOP: def {name} not in {P[key]}")


def src_ref(key, line):
    return f"{P[key]}:{line}"


RESULT = {"R1": [], "R2": [], "M1": [], "C1": []}
DETAIL = {"R1": [], "R2": [], "M1": [], "C1": [], "considered_and_count": {"R1": [], "R2": [], "M1": [], "C1": []}, "checks": []}

# ================================================================ R1
log("== R1")
EXCL = str_elts(mod_assign("final_table4", "EXCL").value)
M = str_elts(mod_assign("final_table4", "M").value)
assert len({x for x, _ in EXCL}) == len(EXCL) and len({x for x, _ in M}) == len(M), "duplicate literal in EXCL or M"
log("final_table4 EXCL", len(EXCL), "M", len(M), "EXCL&M", sorted({x for x, _ in EXCL} & {x for x, _ in M}))
pf = SRC["pool_final_r1"]
assert 'exec(src[: src.index("best = defaultdict")], ns)' in pf and 'cls0, bare = ns["cls"], ns["bare"]' in pf
cut = SRC["final_table4"].index("best = defaultdict")
assert mod_assign("final_table4", "EXCL").lineno < SRC["final_table4"][:cut].count("\n") + 1
cls_fn = func("final_table4", "cls")
cls_txt = ast.unparse(cls_fn)
assert "if b in EXCL:\n        return None" in cls_txt and "if b in M:\n        return 'M'" in cls_txt, cls_txt
bare_txt = ast.unparse(func("final_table4", "bare"))
log("bare():", bare_txt.replace("\n", " | "))
EXCLUDED_node = mod_assign("r1_fix3_battery", "EXCLUDED").value
EXCLUDED = [(k.value, k.lineno) for k in EXCLUDED_node.keys]
EBS_node = mod_assign("r1_fix3_battery", "EXCLUDED_BY_SHAPE").value
EBS = {}
for k, v in zip(EBS_node.keys, EBS_node.values):
    EBS[k.value] = str_elts(v)
log("r1_fix3_battery EXCLUDED", len(EXCLUDED), "EXCLUDED_BY_SHAPE stems", len(EBS), "names", sum(len(v) for v in EBS.values()))
summ = ast.unparse(func("r1_fix3_battery", "summarise"))
assert "EXCLUDED_BY_SHAPE.get(base, ())" in summ and "re.sub('_r\\\\d+$', '', lvl[0]['lineage'].split('.', 1)[1])" in summ, summ[:600]
excluded_all = {x for x, _ in EXCLUDED}
by_stem = {}
for stem_, names in EBS.items():
    for x, ln in names:
        by_stem.setdefault(x, []).append((stem_, ln))
UNITS_R1 = "R1a,R1b"
for x, ln in sorted(M):
    RESULT["R1"].append({"unit_scope": UNITS_R1, "lineage_scope": "all", "rule": x, "class": "M", "source": src_ref("final_table4", ln)})
    DETAIL["R1"].append({"rule": x, "why": "in M of final_table4 (cls -> 'M'); r1_fix3_battery gives it no class; uncounted by the ruling in point 8 (M read as procedure under another reading of a convention)", "battery": "no class"})
for x, ln in sorted(EXCL):
    if x in excluded_all:
        RESULT["R1"].append({"unit_scope": UNITS_R1, "lineage_scope": "all", "rule": x, "class": "EXCL", "source": src_ref("final_table4", ln)})
        bl = [l for n_, l in EXCLUDED if n_ == x][0]
        DETAIL["R1"].append({"rule": x, "why": "EXCL in final_table4 (all lineages) and EXCLUDED in r1_fix3_battery (all lineages): one reading", "battery_line": src_ref("r1_fix3_battery", bl)})
    elif x in by_stem:
        for stem_, bl in by_stem[x]:
            RESULT["R1"].append({"unit_scope": UNITS_R1, "lineage_scope": stem_, "rule": x, "class": "EXCL", "source": src_ref("final_table4", ln)})
            DETAIL["R1"].append({"rule": x, "lineage_scope": stem_, "why": "EXCL in final_table4 for every lineage; EXCLUDED_BY_SHAPE only for this stem: one reading on this stem, two elsewhere (counts elsewhere)", "battery_line": src_ref("r1_fix3_battery", bl)})
    else:
        DETAIL["considered_and_count"]["R1"].append({"rule": x, "why": "EXCL in final_table4 but excluded nowhere by r1_fix3_battery: two readings everywhere"})
battery_only = (excluded_all | set(by_stem)) - {x for x, _ in EXCL}
log("battery exclusions not in EXCL:", sorted(battery_only))
for x in sorted(battery_only):
    DETAIL["considered_and_count"]["R1"].append({"rule": x, "why": "excluded by r1_fix3_battery only; not in final_table4's class code"})
DETAIL["considered_and_count"]["R1"] += [
    {"rule": "classes C and A of final_table4 (GENERIC, CHEAP, and every other name)", "why": "C and A are not among the four classes"},
    {"rule": "feat:* rows (pool_final cls: 'A' if 'family tree' else 'C')", "why": "C/A"},
    {"rule": "every rule of final_r1/new_rules_final.py (unit R1c)", "why": "no class code in that file (checked: no EXCL/M/cls)"},
]
nr = SRC["new_rules_final_r1"]
assert not re.search(r"\bEXCL\b|\bcls\(|final_table4", nr)

# ================================================================ R2
log("== R2")
kf = func("f_pool", "klass")
kb = func("r2_fix4_battery", "klass")


def strip_ann(fn):
    fn = ast.parse(ast.unparse(fn)).body[0]
    fn.returns = None
    for a in fn.args.args:
        a.annotation = None
    return ast.dump(fn, include_attributes=False)


same_klass = strip_ann(kf) == strip_ann(kb)
lists_same = all(ast.dump(mod_assign("f_pool", n).value) == ast.dump(mod_assign("r2_fix4_battery", n).value) for n in ("MISREAD", "PARTIAL", "CONSTRUCT"))
log("klass body f_pool == r2_fix4_battery (annotations stripped):", same_klass, "; MISREAD/PARTIAL/CONSTRUCT equal:", lists_same)
assert same_klass and lists_same
DETAIL["checks"].append({"r2_klass_identical_in_f_pool_and_r2_fix4_battery": same_klass, "lists_identical": lists_same})
LISTS = {n: str_elts(mod_assign("f_pool", n).value) for n in ("MISREAD", "PARTIAL", "CONSTRUCT")}
params = [a.arg for a in kf.args.args]
assert params == ["hn", "sh", "lv"], params


def atom_test(t):
    """Decompose one if-test of klass into [(op, literal, line, depends_on, cond_text)]."""
    def name_cmp(c, var):
        return isinstance(c, ast.Compare) and isinstance(c.left, ast.Name) and c.left.id == var and len(c.ops) == 1
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.In) and isinstance(t.left, ast.Constant) and isinstance(t.comparators[0], ast.Name) and t.comparators[0].id == "hn":
        return [("contains", t.left.value, t.lineno, None, None)]
    if name_cmp(t, "hn") and isinstance(t.ops[0], ast.In):
        return [("equals", v, ln, None, None) for v, ln in str_elts(t.comparators[0])]
    if name_cmp(t, "hn") and isinstance(t.ops[0], ast.Eq):
        return [("equals", t.comparators[0].value, t.lineno, None, None)]
    if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.Or):
        out = []
        for v in t.values:
            out += atom_test(v)
        return out
    if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And) and len(t.values) == 2:
        a, b = t.values
        dep = None
        if name_cmp(b, "sh") and isinstance(b.ops[0], ast.Eq):
            dep = "shape"
        elif name_cmp(b, "lv") and isinstance(b.ops[0], ast.Eq):
            dep = "level"
        else:
            raise SystemExit("STOP: unrecognised And clause " + ast.unparse(t))
        return [(op, lit, ln, dep, ast.unparse(b)) for op, lit, ln, _, _ in atom_test(a)]
    if isinstance(t, ast.Call) and isinstance(t.func, ast.Name) and t.func.id == "any" and isinstance(t.args[0], ast.GeneratorExp):
        g = t.args[0]
        lst = g.generators[0].iter.id
        var = g.generators[0].target.id
        e = g.elt
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "startswith" and e.func.value.id == "hn" and e.args[0].id == var:
            op = "startswith"
        elif isinstance(e, ast.Compare) and isinstance(e.ops[0], ast.In) and e.left.id == var and e.comparators[0].id == "hn":
            op = "contains"
        else:
            raise SystemExit("STOP: unrecognised any() " + ast.unparse(t))
        return [(op, v, ln, None, None) for v, ln in LISTS[lst]]
    raise SystemExit("STOP: unrecognised clause " + ast.unparse(t))


clauses = []
for st in kf.body:
    if isinstance(st, ast.If):
        assert len(st.body) == 1 and isinstance(st.body[0], ast.Return) and not st.orelse
        cls_ = st.body[0].value.value
        for op, litv, ln, dep, cond in atom_test(st.test):
            clauses.append({"op": op, "literal": litv, "line": ln, "depends_on": dep, "cond": cond, "class": cls_, "if_line": st.lineno})
    elif isinstance(st, ast.Return):
        default = st.value.value
log("klass atomic clauses:", len(clauses), "default:", default, "by class:", {c: sum(1 for x in clauses if x["class"] == c) for c in sorted({x["class"] for x in clauses})})
UNCOUNTED_R2 = {"P", "artifact", "partial"}
for i, c in enumerate(clauses, 1):
    c["index"] = i
    if c["class"] in UNCOUNTED_R2:
        RESULT["R2"].append({"kind": "klass_clause", "clause_index": i, "match": c["literal"], "class": c["class"], "depends_on": c["depends_on"], "source": src_ref("f_pool", c["line"])})
        DETAIL["R2"].append({"clause_index": i, "test": f'{c["op"]} {c["literal"]!r}' + (f' and {c["cond"]}' if c["cond"] else ""), "class": c["class"], "if_line": c["if_line"]})
    else:
        DETAIL["considered_and_count"]["R2"].append({"clause_index": i, "test": f'{c["op"]} {c["literal"]!r}', "class": c["class"], "why": "construct is none of the four classes"})
DETAIL["considered_and_count"]["R2"].append({"clause": "default", "class": default, "why": "cue counts"})


def klass_sim(hn, sh, lv):
    for c in clauses:
        hit = (c["op"] == "equals" and hn == c["literal"]) or (c["op"] == "contains" and c["literal"] in hn) or (c["op"] == "startswith" and hn.startswith(c["literal"]))
        if hit and c["depends_on"] == "shape":
            hit = sh == c["cond"].split("==")[1].strip().strip("'\"")
        if hit and c["depends_on"] == "level":
            hit = lv == int(c["cond"].split("==")[1])
        if hit:
            return c["class"], c["index"]
    return default, None


for c in clauses:
    if c["depends_on"]:
        other = klass_sim(c["literal"], "__other_shape__", 99 if c["depends_on"] == "level" else 1)
        DETAIL["R2"].append({"conditional_clause": c["index"], "literal": c["literal"], "class_when_condition_fails": other})
        log("conditional clause", c["index"], repr(c["literal"]), c["cond"], "-> otherwise", other)
assert '"[NEW] " + hn' in SRC["f_rules_new"] and 'f"[NEW] {hn}"' in SRC["f_rules"]
doc = ast.get_docstring(TREE["f_new_heur"])
deflab = re.search(r"Each rule carries my class in its name: (.*)$", doc, re.S).group(1)
LABELS = dict(re.findall(r"(\([A-Za-z]+\))(?: = ([^,]+?))?(?:,|$)", deflab.replace("\n", " ")))
log("header labels:", deflab.strip().replace("\n", " "), "->", LABELS)
NEWR = []
for node in TREE["f_new_heur"].body:
    if isinstance(node, ast.FunctionDef):
        for d in node.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "rule":
                NEWR.append((d.args[0].value, d.args[1].value, d.lineno))
log("[NEW] rules:", len(NEWR))
LABEL_CLASS = {"(partial)": "partial", "(P)": "P"}
for lin, name, ln in NEWR:
    labs = re.findall(r"\(([A-Za-z]+)\)", name)
    lab = f"({labs[0]})" if labs else None
    full = "[NEW] " + name
    ks = klass_sim(full, None, None)
    rec = {"lineage": lin, "rule": full, "label": lab, "label_defined_in_header": lab in LABELS, "klass_on_name_any_shape_level": ks}
    if lab in LABEL_CLASS:
        RESULT["R2"].append({"kind": "new_rule", "clause_index": None, "match": full, "class": LABEL_CLASS[lab], "depends_on": None, "source": src_ref("f_new_heur", ln)})
        DETAIL["R2"].append(rec)
    else:
        rec["why"] = "label (cue) counts" if lab == "(cue)" else f"label {lab} not defined in the header: no class"
        DETAIL["considered_and_count"]["R2"].append(rec)
    if ks[0] in UNCOUNTED_R2 and lab not in LABEL_CLASS:
        log("TWO READINGS: [NEW] rule labelled", lab, "but klass gives", ks, full)
    if lab in LABEL_CLASS and ks[0] != LABEL_CLASS[lab]:
        log("note: [NEW] rule", full, "label", lab, "klass on its name", ks)

# ================================================================ M1
log("== M1")
PROC_node = mod_assign("short_summary_a4", "PROC").value
PROC = {}
for k, v in zip(PROC_node.keys, PROC_node.values):
    PROC[k.value] = [(kk.value, vv.value, kk.lineno) for kk, vv in zip(v.keys, v.values)]
log("PROC pairs:", sum(len(v) for v in PROC.values()))
pa5 = SRC["pool_a5"]
assert "short_summary_a4.py" in pa5 and "ast.literal_eval(node.value)" in pa5
stem_txt = ast.unparse(func("pool_a5", "stem"))
log("pool_a5 stem():", stem_txt.replace("\n", " | "))
DOUBT = re.compile(r"kept as a rule")
m1_entries = []
for stem_, pairs in PROC.items():
    for key, reason, ln in pairs:
        if DOUBT.search(reason):
            DETAIL["considered_and_count"]["M1"].append({"lineage_stem": stem_, "prefixed_key": key, "why": "in PROC, but its own reason reads 'kept as a rule': two readings", "reason": reason})
            continue
        m1_entries.append((stem_, key, src_ref("short_summary_a4", ln)))
        DETAIL["M1"].append({"lineage_stem": stem_, "prefixed_key": key, "reason": reason})
A3ALIAS = {}
for key in ("rules_a5", "rules_a5_attempt1", "m1_fix4_battery"):
    for n in ast.walk(TREE[key]):
        if isinstance(n, ast.IfExp) and isinstance(n.body, ast.Constant) and isinstance(n.test, ast.Compare) and isinstance(n.test.comparators[0], ast.Constant) and isinstance(n.test.ops[0], ast.Eq):
            A3ALIAS.setdefault(n.test.comparators[0].value, set()).add((n.body.value, key))
log("a3 lineage aliases:", {k: sorted(v) for k, v in A3ALIAS.items()})


def branches(fn):
    out = {}
    for st in fn.body:
        node = st
        while isinstance(node, ast.If):
            t = node.test
            if isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "n" and isinstance(t.ops[0], ast.Eq):
                out[t.comparators[0].value] = node
            node = node.orelse[0] if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) else None
    return out


def parents(fn):
    par = {}
    for n in ast.walk(fn):
        for c in ast.iter_child_nodes(n):
            par[c] = n
    return par


def bound_names(st):
    out = set()
    if isinstance(st, (ast.FunctionDef, ast.ClassDef)):
        return {st.name}
    if isinstance(st, (ast.Import, ast.ImportFrom)):
        return {(a.asname or a.name).split(".")[0] for a in st.names}
    tg = []
    if isinstance(st, ast.Assign):
        tg = st.targets
    elif isinstance(st, (ast.AugAssign, ast.AnnAssign)):
        tg = [st.target]
    elif isinstance(st, ast.For):
        tg = [st.target]
    for t in tg:
        for n in ast.walk(t):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                out.add(n.id)
    return out


def read_names(node, skip_target_base=False):
    if isinstance(node, ast.FunctionDef):
        inner = {a.arg for a in node.args.args}
        loc = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                loc.add(n.id)
        rd = set()
        for st in node.body:
            rd |= read_names(st)
        return rd - inner - loc
    if isinstance(node, ast.Assign) and skip_target_base:
        node = node.value
    rd, bnd = set(), set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            rd.add(n.id)
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            for g in n.generators:
                for t in ast.walk(g.target):
                    if isinstance(t, ast.Name):
                        bnd.add(t.id)
        if isinstance(n, ast.Lambda):
            bnd |= {a.arg for a in n.args.args}
    return rd - bnd


def ancestors_if(node, par, stop):
    out = []
    c = node
    while c is not stop and c in par:
        p = par[c]
        if isinstance(p, ast.If):
            out.append((p, "body" if c in p.body else ("orelse" if c in p.orelse else "test")))
        c = p
    return out


def exclusive(a, b, par, stop):
    pa = dict((id(p), (p, w)) for p, w in ancestors_if(a, par, stop))
    for p, w in ancestors_if(b, par, stop):
        if id(p) in pa and pa[id(p)][1] != w and w != "test" and pa[id(p)][1] != "test":
            return True
    return False


def definition(fn, stmt, skip_h=True, with_guards=False):
    par = parents(fn)
    allst = [n for n in ast.walk(fn) if isinstance(n, ast.stmt) and n is not fn]
    seen, order = set(), []
    todo = [stmt]
    while todo:
        s = todo.pop()
        if id(s) in seen:
            continue
        seen.add(id(s))
        order.append(s)
        names = read_names(s, skip_target_base=(skip_h and s is stmt))
        for nm in sorted(names):
            cands = [b for b in allst if nm in bound_names(b) and (b.lineno, b.col_offset) < (s.lineno, s.col_offset) and not exclusive(b, s, par, fn)
                     and not (isinstance(b, ast.FunctionDef) and b is s)]
            if cands:
                todo.append(max(cands, key=lambda b: (b.lineno, b.col_offset)))
    if with_guards:
        g = [p.test for p, w in ancestors_if(stmt, par, fn) if not (isinstance(p.test, ast.Compare) and isinstance(p.test.left, ast.Name) and p.test.left.id == "n")]
    else:
        g = []
    order.sort(key=lambda s: (s.lineno, s.col_offset))
    return [ast.dump(s, include_attributes=False) for s in order] + [ast.dump(x, include_attributes=False) for x in g], [s.lineno for s in order]


def assigns_to(branch, name):
    out = []
    for n in ast.walk(branch):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript):
            t = n.targets[0]
            if isinstance(t.value, ast.Name) and t.value.id == "h" and isinstance(t.slice, ast.Constant) and t.slice.value == name:
                out.append(n)
    return out


spec_a3 = func("shortcuts_a3", "spec")
spec_im = func("m1_fix3_shortcuts", "spec")
br_a3, br_im = branches(spec_a3), branches(spec_im)
PRIMARY = "primary (target container h not read)"
for stem_, key, _ in list(m1_entries):
    if not key.startswith("im:"):
        continue
    name = key[3:]
    a3stems = {v for v, _k in A3ALIAS.get(stem_, set())} or {stem_}
    assert len(a3stems) == 1, (stem_, a3stems)
    a3stem = a3stems.pop()
    a = assigns_to(br_a3[a3stem], name) if a3stem in br_a3 else []
    b = assigns_to(br_im[stem_], name) if stem_ in br_im else []
    if not a:
        log(f"M1 ext: {stem_} {name}: no audit-3 rule of that name (a3 branch {a3stem!r})")
        continue
    res = {}
    for mode, kw in ((PRIMARY, dict(skip_h=True)), ("literal (h read: its binding included)", dict(skip_h=False)),
                     ("primary + enclosing guards", dict(skip_h=True, with_guards=True))):
        da = [definition(spec_a3, s, **kw) for s in a]
        db = [definition(spec_im, s, **kw) for s in b]
        res[mode] = ([d for d, _ in da] == [d for d, _ in db], [l for _, l in da], [l for _, l in db])
    eq = res[PRIMARY][0]
    log(f"M1 ext: {stem_} a3:{name} (a3 branch {a3stem!r}) lines a3 {res[PRIMARY][1]} im {res[PRIMARY][2]}:", {m: r[0] for m, r in res.items()})
    rec = {"lineage_stem": stem_, "prefixed_key": "a3:" + name, "a3_branch": a3stem, "tests": {m: {"equal": r[0], "a3_lines": r[1], "im_lines": r[2]} for m, r in res.items()}}
    if eq:
        m1_entries.append((stem_, "a3:" + name, src_ref("shortcuts_a3", a[0].lineno)))
        DETAIL["M1"].append(rec)
    else:
        rec["why"] = "same name, definitions differ as parsed"
        DETAIL["considered_and_count"]["M1"].append(rec)
for stem_, key, src in m1_entries:
    RESULT["M1"].append({"lineage_stem": stem_, "prefixed_key": key, "source": src})
DETAIL["checks"].append({"m1_fix3_shortcuts.PROCEDURE": "not a source under point 8 (implementer's list; excludes nothing by itself)"})

# ================================================================ C1
log("== C1")
BM = str_elts(mod_assign("f4b_pool_v2", "BATTERY_MUT").value)
AM = str_elts(mod_assign("f4b_pool_v2", "A3_MUT").value)
meas = func("f4b_pool_v2", "measures")
mt = ast.unparse(meas)
assert "M['a4.EFF_SM'] = (p['EFF_SM'] * n, n, 'partial')" in mt
assert "{'S': 'cheap', 'F': 'closed', 'M': 'partial', 'H': 'hazard'}.get(c, 'other')" in mt
assert "if r.startswith('C.'):\n                cls = 'control'" in mt
assert "elif r in BATTERY_MUT:\n                cls = 'partial_battery'" in mt
assert "cls = 'artefact_a3' if r in A3_MUT" in mt
eff_sm_line = [n.lineno for n in ast.walk(meas) if isinstance(n, ast.Constant) and n.value == "a4.EFF_SM"][0]


def literal_names(key, prefixes):
    out = {}
    par = {}
    for n in ast.walk(TREE[key]):
        for c in ast.iter_child_nodes(n):
            par[c] = n
    for n in ast.walk(TREE[key]):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"[A-Z]\.[A-Za-z0-9_]+", n.value) and n.value[0] in prefixes:
            p = par[n]
            while isinstance(p, ast.IfExp):
                p = par[p]
            ok = (isinstance(p, ast.Subscript) and isinstance(p.ctx, ast.Store)) or isinstance(p, ast.Dict)
            if not ok:
                log(f"  {P[key]}:{n.lineno} {n.value!r} not used as a stored key ({type(p).__name__}); left out")
                continue
            out.setdefault(n.value, n.lineno)
        if isinstance(n, ast.JoinedStr):
            s = ast.unparse(n)
            if re.match(r"f['\"][A-Z]\.", s) and s[2] in prefixes:
                raise SystemExit(f"STOP: computed rule name with a counted-out prefix {s}")
    return out


s4 = literal_names("s4_rules_v2", "MH")
log("s4_rules_v2 M.*:", sum(1 for x in s4 if x[0] == "M"), "H.*:", sum(1 for x in s4 if x[0] == "H"))
s5 = ast.unparse(func("s5_analyse_v2", "main"))
assert "r.split('.')[0] in ('S', 'F', 'M', 'H')" in s5 and "'EFF_SM': round(eff(its, ('S', 'G', 'M')), 3)" in s5
OUT_S5 = P["s5_analyse_v2"]
RESULT["C1"].append({"output_of": OUT_S5, "rule": "EFF_SM", "class": "partial", "source": src_ref("f4b_pool_v2", eff_sm_line)})
for x, ln in sorted(s4.items()):
    RESULT["C1"].append({"output_of": OUT_S5, "rule": x, "class": "partial" if x[0] == "M" else "hazard", "source": src_ref("s4_rules_v2", ln)})
bat = literal_names("c1_fix3_battery", "C")
assert "if '|C.' in k:\n                    continue" in ast.unparse(func("c1_fix3_battery", "summarise"))
for x, ln in sorted(bat.items()):
    RESULT["C1"].append({"output_of": P["c1_fix3_battery"], "rule": x, "class": "control", "source": src_ref("c1_fix3_battery", ln)})
bat_all = set(literal_names("c1_fix3_battery", "SFLC"))
assert {x for x, _ in BM} <= bat_all, sorted({x for x, _ in BM} - bat_all)
a3c = set(literal_names("a3_shortcuts_c1", "SFLRCMH"))
assert {x for x, _ in AM} <= a3c, sorted({x for x, _ in AM} - a3c)
log("a3_shortcuts C/M/H names:", sorted(x for x in a3c if x[0] in "CMH"))
for x, ln in sorted(AM):
    RESULT["C1"].append({"output_of": P["a3_shortcuts_c1"], "rule": x, "class": "artefact_a3", "source": src_ref("f4b_pool_v2", ln)})
for key in ("f5_closed_forms", "f5b_closed_forms_v2"):
    cf = literal_names(key, "MH")
    for x, ln in sorted(cf.items()):
        RESULT["C1"].append({"output_of": P[key], "rule": x, "class": "partial" if x[0] == "M" else "hazard", "source": src_ref(key, ln)})
    log(key, "M/H names:", sorted(cf))
DETAIL["considered_and_count"]["C1"] += [
    {"rule": "EFF_S, MF, MFsh (s5 output); MF_cv, BEST_generic_cv (battery); MF_cv, MF_shape_cv, BEST_generic_cv (a3)", "why": "cheap"},
    {"rule": "EFF_F (s5 output)", "why": "no class in f4b_pool_v2 (not read by it)"},
    {"rule": "every S.*, F.*, L.*, R.* rule", "why": "cheap / closed (F.pow_res_c0: closed by prefix, 'the unmodified algorithm' in the closed-form header: two readings)"},
    {"rule": "BATTERY_MUT (12) in the battery's output: " + ", ".join(sorted(x for x, _ in BM)), "why": "f4b header: partial trace under the strict reading, counted by the implementer: two readings"},
    {"rule": "any X.* or G.* rule", "why": "class 'other' / not written one by one"},
    {"rule": "M.*/H.* names not literally written in s4_rules_v2.py", "why": "entries are literal names, not prefixes"},
]
DETAIL["checks"].append({"BATTERY_MUT": sorted(x for x, _ in BM), "A3_MUT": sorted(x for x, _ in AM)})

# ================================================================ write
ORDER = {"R1": ("unit_scope", "lineage_scope", "rule", "class", "source"), "R2": ("kind", "clause_index", "match", "class", "depends_on", "source"),
         "M1": ("lineage_stem", "prefixed_key", "source"), "C1": ("output_of", "rule", "class", "source")}


def sk(e, ev):
    return tuple((0, "") if e[f] is None else (1, e[f]) if isinstance(e[f], int) else (2, e[f]) for f in ORDER[ev])


for ev in RESULT:
    RESULT[ev] = [{f: e[f] for f in ORDER[ev]} for e in sorted(RESULT[ev], key=lambda e: sk(e, ev))]
    log(ev, "entries:", len(RESULT[ev]))
with open(f"{OUT}/uncounted_rules_second.json", "w") as f:
    json.dump(RESULT, f, indent=1, ensure_ascii=False)
    f.write("\n")
DETAIL["source_files_sha256_at_b78e58b1"] = HASH
with open(f"{OUT}/uncounted_rules_second_detail.json", "w") as f:
    json.dump(DETAIL, f, indent=1, ensure_ascii=False, sort_keys=True, default=str)
    f.write("\n")
for p, h in sorted(HASH.items()):
    log("sha256", h, p)
