"""(v2: docstrings, exception messages and strings over 60 chars excluded; C1 lineages from the fixtures tree) Pair audit, provenance evidence: string literals and identifiers in each new solver module that do NOT occur anywhere in the
authoring fixtures text of the solver's own lineages (question + structured JSON + SCHEMA.md + fixtures README + brief), and,
for those, whether they occur in the generator/first-solver source under studies/m0 (excluding solvers2/). Standard library only."""
import ast, glob, json, os, re, sys, collections
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126"
BRIEF = W + "/docs/reviews/m0-fresh-run-2026-11-26/second_solvers/BRIEF_SOLVER2.md"
gen_src = {}
for p in glob.glob(W + "/studies/m0/*.py"):
    gen_src[os.path.basename(p)] = open(p).read()
PYKW = set(dir(__builtins__)) | {"self", "re", "math", "json", "fractions", "Fraction", "itertools", "functools", "collections", "ast"}
for path in sorted(glob.glob(W + "/studies/m0/solvers2/solver2_*.py")):
    src = open(path).read(); tree = ast.parse(src)
    # lineages
    ids = sorted(set(re.findall(r'((?:R1|R2|M1|C1)\.[A-Za-z0-9_]+)', src)))
    if "solver2_c1" in path: ids = [os.path.basename(x) for x in glob.glob(F + "/C1/C1.*")]
    allowed = open(F + "/README.md").read() + open(BRIEF).read()
    for lid in ids:
        ev = lid.split(".")[0]
        d = f"{F}/{ev}/{lid}"
        if os.path.isdir(d):
            allowed += open(d + "/SCHEMA.md").read() + open(d + "/fixtures.jsonl").read()
    allowed_l = allowed.lower()
    lits = collections.Counter()
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
            docs.add(id(n.body[0].value))
        if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) in ("ValueError", "RuntimeError", "AssertionError", "Exception", "TypeError", "KeyError", "IndexError", "ZeroDivisionError", "NotImplementedError", "Unsupported", "C1Error", "SolveError"):
            for a in ast.walk(n):
                if isinstance(a, ast.Constant): docs.add(id(a))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs and len(node.value) <= 60:
            for tok in re.findall(r"[A-Za-z_][A-Za-z_0-9]{3,}", node.value):
                lits[tok] += 1
        elif isinstance(node, (ast.FunctionDef, ast.Name, ast.Attribute, ast.arg)):
            pass
    missing = sorted(t for t in lits if t.lower() not in allowed_l and t not in PYKW)
    print(f"== {os.path.basename(path)}  lineages={len(ids)}  string-literal words={len(lits)}  not in own fixtures/schema/readme/brief={len(missing)}")
    for t in missing:
        where = sorted(f for f, s in gen_src.items() if re.search(r"\b" + re.escape(t) + r"\b", s))
        print(f"   {t!r}: in generator/first-solver files: {len(where)} {where[:4]}")
    # function names defined in module that coincide with function names defined in studies/m0 sources
    fn_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    gen_fns = collections.defaultdict(list)
    for f, s in gen_src.items():
        for m in re.findall(r"^\s*def ([A-Za-z_][A-Za-z_0-9]*)\(", s, re.M):
            gen_fns[m].append(f)
    common = sorted(n for n in fn_names if n in gen_fns and not n.startswith("_") and len(n) > 4)
    print(f"   def names also defined in studies/m0 (non-private, len>4): {[(n, gen_fns[n][:3]) for n in common]}")
