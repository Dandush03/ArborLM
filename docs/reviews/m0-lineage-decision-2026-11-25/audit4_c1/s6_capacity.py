# ruff: noqa
"""Audit 4 (C1), step 6: structural capacity per lineage and level, my own code (adapted from audit3_c1/a6_capacity.py with one fix).

  K1   distinct program after renaming EVERY identifier by first appearance (variables, parameters, function names); only Python builtins
       actually called as names are kept (len, sum, max, min, abs, str, range, print, sorted, list). FIX against the predecessor: its keep
       list contained 'count' (and other method names); 'count' is also a drawn VARIABLE name (lineages_c1.VARS), so a program using the
       variable 'count' was not renamed there and one skeleton split into several classes.  K1old reproduces the predecessor's keep list.
  K2   K1 with every int/str literal blanked, PLUS the executed line sequence (sys.settrace): literals that do not change control flow are
       not distinct (reading (c)).
Draws (throwaway seed 59, sha256 streams "audit4c1-cap|...") continue until K1 >= TARGET or BUDGET draws. Saves the K1 and K2 hash sets
per cell (so cluster unions can be computed).  Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python s6_capacity.py --ids s1_set_out.json --out DIR --target 21010 --budget 63030
"""
import argparse, ast, gzip, hashlib, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.getcwd())
KEEP = {"len", "sum", "max", "min", "abs", "str", "range", "print", "sorted", "list"}
KEEP_OLD = {"len", "sum", "max", "min", "abs", "str", "range", "print", "append", "upper", "lower", "replace", "count", "sorted"}


def rename(tree, keep):
    mp = {}

    def nm(x):
        if x in keep:
            return x
        if x not in mp:
            mp[x] = f"v{len(mp)}"
        return mp[x]

    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            n.id = nm(n.id)
        elif isinstance(n, ast.FunctionDef):
            n.name = nm(n.name)
        elif isinstance(n, ast.arg):
            n.arg = nm(n.arg)
    return tree


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:20]


class Blank(ast.NodeTransformer):
    def visit_Constant(self, n):
        return ast.Constant(value="<S>" if isinstance(n.value, str) else 0)

    def visit_UnaryOp(self, n):
        if isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant):
            return ast.Constant(value=0)
        return self.generic_visit(n)


def k2_of(src):
    t = Blank().visit(rename(ast.parse(src), KEEP))
    skel = ast.dump(t)
    lines = []

    def tr(frame, event, arg):
        if frame.f_code.co_filename == "<k2>":
            if event == "line":
                lines.append(frame.f_lineno)
            elif event == "call":
                lines.append(-1)
            elif event == "return":
                lines.append(-2)
        return tr

    import io, contextlib
    code = compile(src, "<k2>", "exec")
    with contextlib.redirect_stdout(io.StringIO()):
        sys.settrace(tr)
        try:
            exec(code, {"__name__": "__k2__"})
        finally:
            sys.settrace(None)
    return h(skel + "|" + ",".join(map(str, lines)))


def by_id():
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2
    from studies.m0.lineages_c1_fix3 import load_fix3
    return {x.id: x for x in [*lineages_of("C1"), *load_batch1(), *load_rev2(), *load_fix3()]}


def cell(args):
    lid, lv, target, budget, seed, out = args
    from studies.m0.core import Retry
    from studies.m0.c1grammar import render
    lin = by_id()[lid]
    d = hashlib.sha256(f"audit4c1-cap|{seed}|{lid}|{lv}".encode()).digest()
    r = random.Random(int.from_bytes(d[:8], "big"))
    k1, k1old, k2, k0 = set(), set(), set(), set()
    draws, retries = 0, 0
    t0 = time.time()
    while draws < budget and len(k1) < target:
        try:
            b = lin.build(lv, r)
        except Retry:
            retries += 1
            continue
        draws += 1
        src = render(b.structured["program"])
        k0.add(h(b.question))
        a1 = h(ast.dump(rename(ast.parse(src), KEEP)))
        k1old.add(h(ast.dump(rename(ast.parse(src), KEEP_OLD))))
        if a1 not in k1:
            k1.add(a1)
            k2.add(k2_of(src))
    fn = os.path.join(out, f"{lid.replace('C1.', '')}_L{lv}.json.gz")
    with gzip.open(fn, "wt") as f:
        json.dump({"k1": sorted(k1), "k2": sorted(k2)}, f)
    return lid, lv, {"draws": draws, "retries": retries, "K0_text": len(k0), "K1": len(k1), "K1old": len(k1old), "K2": len(k2),
                     "capped_by_budget": len(k1) < target and draws >= budget, "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=21010)
    ap.add_argument("--budget", type=int, default=63030)
    ap.add_argument("--seed", type=int, default=59)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    ids = json.load(open(a.ids))["current"]
    if a.only:
        ids = [i for i in ids if i in a.only.split(",")]
    os.makedirs(a.out, exist_ok=True)
    jobs = [(i, lv, a.target, a.budget, a.seed, a.out) for i in ids for lv in range(7)]
    res = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, lv, rr in ex.map(cell, jobs):
            res.setdefault(lid, {})[str(lv)] = rr
            print(lid, lv, rr, flush=True)
    json.dump({"ids": ids, "target": a.target, "budget": a.budget, "seed": a.seed, "rows": res}, open(os.path.join(a.out, "summary.json"), "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
