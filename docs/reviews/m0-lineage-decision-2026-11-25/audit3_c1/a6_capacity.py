# ruff: noqa
"""Audit 3 (C1), step 6: structural capacity per lineage and level, three criteria, own code.

  K0  distinct normalised question text (NFKC, casefold, whitespace collapsed; my own normaliser)
  K1  distinct program after renaming every identifier by first appearance (variables, parameters, function names; builtins and
      method names kept), read from the rendered source with ast (R-5: names, setting and presentation order are not distinct items)
  K2  K1 with every literal (int and str constant) replaced by a typed placeholder, PLUS the sequence of source lines the program
      executes (sys.settrace).  Two programs are the same under K2 when they have the same skeleton and take the same control-flow
      path, i.e. literal values that do not change control flow do not count (the coordinator's stricter criterion).
      K2 classes are unions of K1 classes, so K2 is computed once per new K1 class.

Draws (throwaway seed 11, my own sha256 streams) continue until K1 >= TARGET or BUDGET draws.  Checkpoints of K1/K2 are kept so that
every G can be read off.  Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python a6_capacity.py --out cap.json --target 25000 --budget 75000
"""
import argparse, ast, hashlib, json, os, random, re, sys, time, unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.getcwd())
KEEP = {"len", "sum", "max", "min", "abs", "str", "range", "print", "append", "upper", "lower", "replace", "count", "sorted"}
WS = re.compile(r"\s+")


def norm(t):
    return WS.sub(" ", unicodedata.normalize("NFKC", t).casefold()).strip()


def rename(tree):
    mp = {}

    def nm(x):
        if x in KEEP:
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


def k1_of(src):
    t = rename(ast.parse(src))
    return hashlib.sha1(ast.dump(t).encode()).hexdigest()


class Blank(ast.NodeTransformer):
    def visit_Constant(self, n):
        return ast.Constant(value="<S>" if isinstance(n.value, str) else 0)

    def visit_UnaryOp(self, n):
        if isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant):
            return ast.Constant(value=0)
        return self.generic_visit(n)


def k2_of(src):
    t = Blank().visit(rename(ast.parse(src)))
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
    g = {"__name__": "__k2__"}
    code = compile(src, "<k2>", "exec")
    with contextlib.redirect_stdout(io.StringIO()):
        sys.settrace(tr)
        try:
            exec(code, g)
        finally:
            sys.settrace(None)
    return hashlib.sha1((skel + "|" + ",".join(map(str, lines))).encode()).hexdigest()


def lineage_by_id():
    from studies.m0.core import lineages_of
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2
    return {x.id: x for x in [*lineages_of("C1"), *load_batch1(), *load_rev2()]}


CHECK = (1000, 2000, 5000, 10000, 15000, 20000, 30000, 40000, 50000, 60000, 75000)


def cell(args):
    lid, lv, target, budget, seed = args
    from studies.m0.core import Retry
    from studies.m0.c1grammar import render
    lin = lineage_by_id()[lid]
    d = hashlib.sha256(f"audit3c1-cap|{seed}|{lid}|{lv}".encode()).digest()
    r = random.Random(int.from_bytes(d[:8], "big"))
    k0, k1c, k2 = set(), Counter(), set()
    draws, checkpoints, k1_at = 0, {}, []
    t0 = time.time()
    while draws < budget and len(k1c) < target:
        try:
            b = lin.build(lv, r)
        except Retry:
            continue
        draws += 1
        src = render(b.structured["program"])
        k0.add(hashlib.sha1(norm(b.question).encode()).hexdigest())
        h1 = k1_of(src)
        if h1 not in k1c:
            k2.add(k2_of(src))
        k1c[h1] += 1
        if draws in CHECK:
            checkpoints[draws] = (len(k1c), len(k2), len(k0))
    f1 = sum(1 for v in k1c.values() if v == 1)
    f2 = sum(1 for v in k1c.values() if v == 2)
    chao1 = len(k1c) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)
    checkpoints[draws] = (len(k1c), len(k2), len(k0))
    return lid, lv, {"draws": draws, "K0": len(k0), "K1": len(k1c), "K2": len(k2), "K1_chao1": round(chao1), "f1": f1, "f2": f2,
                     "reached_target": len(k1c) >= target, "checkpoints": checkpoints, "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=25000)
    ap.add_argument("--budget", type=int, default=75000)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--workers", type=int, default=15)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    from studies.m0.lineages_c1_rev2 import SUPERSEDES, PROPOSED
    allx = lineage_by_id()
    superseded = set(SUPERSEDES.values())
    ids = sorted(i for i in allx if i not in superseded)
    if a.only:
        ids = [i for i in ids if i in a.only.split(",")]
    jobs = [(i, lv, a.target, a.budget, a.seed) for i in ids for lv in range(7)]
    jobs.sort(key=lambda j: -j[1])
    res = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, lv, rr in ex.map(cell, jobs):
            res.setdefault(lid, {})[str(lv)] = rr
            print(lid, lv, {k: rr[k] for k in ("draws", "K0", "K1", "K2", "K1_chao1", "secs")}, flush=True)
    json.dump({"ids": ids, "target": a.target, "budget": a.budget, "seed": a.seed, "rows": res}, open(a.out, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
