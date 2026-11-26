"""Pair audit: line coverage of each new solver module (sys.settrace, standard library), on (a) the authoring fixtures the author saw
and (b) the fresh pair-audit items. Lines run on fresh items but never on the authoring fixtures are cases the fixtures did not show;
lines run on neither are code no item reaches. Prints, per module, those line numbers with the source line. Usage: coverage.py <file>"""
import copy, glob, importlib.util, json, sys, linecache, collections
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
OUT = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126"
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126"
name = sys.argv[1]
path = f"{W}/studies/m0/solvers2/solver2_{name}.py"
spec = importlib.util.spec_from_file_location(f"pa_cov_{name}", path)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
lids = set(mod.SOLVERS)
hit = {"fix": set(), "fresh": set()}
cur = None
def tr(frame, event, arg):
    if frame.f_code.co_filename != path:
        return None
    def lt(f, e, a):
        if e == "line":
            hit[cur].add(f.f_lineno)
        return lt
    if event == "call":
        hit[cur].add(frame.f_lineno)
    return lt
def run(rows, which):
    global cur
    cur = which
    sys.settrace(tr)
    try:
        for r in rows:
            mod.SOLVERS[r["id"]](r["question"], copy.deepcopy(r["structured"]))
    finally:
        sys.settrace(None)
fix_rows = []
for lid in sorted(lids):
    ev = lid.split(".")[0]
    fix_rows += [json.loads(l) for l in open(f"{F}/{ev}/{lid}/fixtures.jsonl")]
fresh_rows = []
for ev in sorted({l.split(".")[0] for l in lids}):
    fresh_rows += [r for r in map(json.loads, open(f"{OUT}/work/items_{ev}.jsonl")) if r["id"] in lids]
run(fix_rows, "fix"); run(fresh_rows, "fresh")
import ast
tree = ast.parse(open(path).read())
exe = set()
for n in ast.walk(tree):
    if isinstance(n, ast.stmt) and not isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
        exe.add(n.lineno)
# exclude module-level statements (run at import) and docstring expressions
mod_level = {n.lineno for n in tree.body}
exe -= mod_level
fn_lines = {}
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef):
        for m in ast.walk(n):
            if isinstance(m, ast.stmt):
                fn_lines.setdefault(m.lineno, n.name)
only_fresh = sorted((exe & hit["fresh"]) - hit["fix"])
neither = sorted(exe - hit["fresh"] - hit["fix"])
print(f"== solver2_{name}.py: statements {len(exe)}; run on fixtures {len(exe & hit['fix'])}; run on fresh {len(exe & hit['fresh'])}; "
      f"fresh-only {len(only_fresh)}; never run {len(neither)}; fixture-only {len((exe & hit['fix']) - hit['fresh'])}")
for tag, ls in (("FRESH-ONLY", only_fresh), ("NEVER", neither)):
    for ln in ls:
        print(f"  {tag} {ln} [{fn_lines.get(ln)}] {linecache.getline(path, ln).rstrip()[:150]}")
