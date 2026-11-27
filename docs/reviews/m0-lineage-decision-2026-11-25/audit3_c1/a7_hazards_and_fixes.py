# ruff: noqa
"""Audit 3 (C1), step 7 (stdlib only): (a) semantic hazards per lineage, measured by running an instrumented copy of every gen7 program:
mixed-sign // or % (Python floor semantics differ from truncating languages), negative slice bounds/steps (static), max call depth,
max executed line events; (b) corrected closed forms for fast_power (my a3 formula reduced the first b modulo m; the program adds the
UNREDUCED base in round 0 -- my mistake, kept in a3's output); (c) majority_vote_scan_r2 'pair' shape: parity of the printed count.
python a7_hazards_and_fixes.py GEN_DIR OUT_JSON
"""
import ast, contextlib, glob, gzip, io, json, os, re, sys
from collections import defaultdict

REC = {}


def _mod(a, b):
    if (a < 0) != (b < 0) and a != 0:
        REC["mixed"] += 1
    return a % b


def _fdiv(a, b):
    if (a < 0) != (b < 0) and a != 0:
        REC["mixed"] += 1
    return a // b


class Inst(ast.NodeTransformer):
    def visit_BinOp(self, n):
        self.generic_visit(n)
        if isinstance(n.op, ast.Mod):
            return ast.Call(func=ast.Name("_mod", ast.Load()), args=[n.left, n.right], keywords=[])
        if isinstance(n.op, ast.FloorDiv):
            return ast.Call(func=ast.Name("_fdiv", ast.Load()), args=[n.left, n.right], keywords=[])
        return n

    def visit_AugAssign(self, n):
        self.generic_visit(n)
        if isinstance(n.op, (ast.Mod, ast.FloorDiv)):
            f = "_mod" if isinstance(n.op, ast.Mod) else "_fdiv"
            return ast.Assign(targets=[ast.Name(n.target.id, ast.Store())], value=ast.Call(func=ast.Name(f, ast.Load()), args=[ast.Name(n.target.id, ast.Load()), n.value], keywords=[]))
        return n


def neg_slice(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Slice):
            for part in (n.lower, n.upper, n.step):
                if isinstance(part, ast.UnaryOp) and isinstance(part.op, ast.USub):
                    return True
    return False


def run_inst(src):
    REC["mixed"] = 0
    depth = [0, 0, 0]  # cur, max, lines

    def tr(frame, event, arg):
        if frame.f_code.co_filename != "<h>":
            return tr
        if event == "call":
            depth[0] += 1
            depth[1] = max(depth[1], depth[0])
        elif event == "return":
            depth[0] -= 1
        elif event == "line":
            depth[2] += 1
        return tr

    t = Inst().visit(ast.parse(src))
    ast.fix_missing_locations(t)
    g = {"_mod": _mod, "_fdiv": _fdiv, "__name__": "__h__"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sys.settrace(tr)
        try:
            exec(compile(t, "<h>", "exec"), g)
        finally:
            sys.settrace(None)
    return REC["mixed"], depth[1] - 1, depth[2], buf.getvalue()


def main():
    gen, outp = sys.argv[1], sys.argv[2]
    out = {}
    for fn in sorted(glob.glob(os.path.join(gen, "*.jsonl.gz"))):
        rows = [json.loads(l) for l in gzip.open(fn, "rt")]
        lid = rows[0]["lid"]
        st = defaultdict(int)
        st["n"] = len(rows)
        extra = defaultdict(lambda: [0, 0])
        for r in rows:
            mixed, depth, lines, printed = run_inst(r["src"])
            assert printed.rstrip("\n") == r["key"], (lid, r["lv"], r["i"])
            st["items_mixed_sign_divmod"] += mixed > 0
            st["items_neg_slice"] += neg_slice(ast.parse(r["src"]))
            st["max_call_depth"] = max(st["max_call_depth"], depth)
            st["max_line_events"] = max(st["max_line_events"], lines)
            src = r["src"]
            if lid in ("C1.fast_power_r2", "C1.fast_power_traced"):
                ts = [ln.split(" = ") for ln in src.splitlines()[:6] if " = " in ln and not ln.startswith(" ")]
                vals = [int(v) for _, v in ts[:4]]
                B0, E0, M0 = vals[1], vals[2], vals[3]
                bl = E0.bit_length()
                pn = src.splitlines()[-1][6:-1]
                bterm = lambda k: B0 if k == 0 else pow(B0, 2 ** k, M0)
                if lid == "C1.fast_power_r2" and pn not in (ts[0][0], ts[1][0]):
                    e = extra[("bsum", r["lv"])]
                    e[0] += str(sum(bterm(k) for k in range(bl))) == r["key"]
                    e[1] += 1
                if lid == "C1.fast_power_traced" and not re.search(r"while .* and .* < \d+:", src):
                    e = extra[("oddsum", r["lv"])]
                    e[0] += str(sum(bterm(k) for k in range(bl) if (E0 >> k) & 1)) == r["key"]
                    e[1] += 1
            if lid == "C1.majority_vote_scan_r2" and "' '" in src.splitlines()[-1]:
                e = extra[("pair_count_even", r["lv"])]
                e[0] += int(r["key"].split()[1]) % 2 == 0
                e[1] += 1
        out[lid] = {"stats": dict(st), "extra": {f"{k[0]}|L{k[1]}": v for k, v in sorted(extra.items())}}
        print(lid, dict(st), {f"{k[0]}|L{k[1]}": v for k, v in sorted(extra.items())} if extra else "", flush=True)
    json.dump(out, open(outp, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
