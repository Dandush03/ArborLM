import ast, json, os, collections
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
PRE = "Here is a Python program.\n\n"; SUF = "\n\nWhat exactly does it print? It prints a single line."
c = collections.Counter(); per = collections.defaultdict(set)
for lin in sorted(os.listdir(F)):
    for line in open(os.path.join(F, lin, "fixtures.jsonl")):
        it = json.loads(line); t = ast.parse(it["question"][len(PRE):-len(SUF)])
        for n in ast.walk(t):
            if isinstance(n, ast.Compare): c["compare_nops=%d" % len(n.ops)] += 1
            if isinstance(n, ast.Assign):
                c["assign_ntargets=%d" % len(n.targets)] += 1
                c["assign_target=" + type(n.targets[0]).__name__] += 1
            if isinstance(n, ast.AugAssign): c["aug_target=" + type(n.target).__name__] += 1
            if isinstance(n, ast.Slice):
                c["slice_lower=%s upper=%s step=%s" % tuple(type(x).__name__ for x in (n.lower, n.upper, n.step))] += 1
            if isinstance(n, ast.Call):
                c["call_kw=%d nargs=%d %s" % (len(n.keywords), len(n.args), ast.unparse(n.func) if not isinstance(n.func, ast.Attribute) else "." + n.func.attr)] += 1
                if isinstance(n.func, ast.Attribute): per[lin].add(n.func.attr + ":" + type(n.func.value).__name__)
            if isinstance(n, ast.FunctionDef):
                c["def_defaults=%d nested=%s" % (len(n.args.defaults), "?" )] += 1
            if isinstance(n, ast.For):
                c["for_iter=" + (ast.unparse(n.iter.func) if isinstance(n.iter, ast.Call) else type(n.iter).__name__) + " target=" + type(n.target).__name__ + " orelse=%d" % len(n.orelse)] += 1
            if isinstance(n, ast.While): c["while_orelse=%d" % len(n.orelse)] += 1
            if isinstance(n, ast.Subscript): c["subscript_value=" + type(n.value).__name__] += 1
            if isinstance(n, ast.UnaryOp): c["unary_operand=" + type(n.operand).__name__] += 1
            if isinstance(n, ast.BoolOp): c["boolop_nvalues=%d" % len(n.values)] += 1
        # top-level statement kinds and nesting of defs
        for s in t.body:
            c["top=" + type(s).__name__] += 1
        for n in ast.walk(t):
            if isinstance(n, ast.FunctionDef):
                for m in ast.walk(n):
                    if m is not n and isinstance(m, ast.FunctionDef): c["nested_def"] += 1
                    if isinstance(m, (ast.Global, ast.Nonlocal)): c["global/nonlocal"] += 1
        prints = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
        c["n_print_calls=%d" % len(prints)] += 1
for k in sorted(c): print(k, c[k])
for lin in sorted(per): print(lin, sorted(per[lin]))
