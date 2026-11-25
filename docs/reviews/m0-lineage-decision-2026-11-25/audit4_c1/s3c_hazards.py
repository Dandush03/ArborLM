# ruff: noqa
"""Audit 4 (C1), step 3c: convention hazards (Python-defined, but a reader with C/Java habits would differ):
floor division or modulo with a negative operand; slices with negative bounds or steps; maximum call depth.
Rewrites every // and % BinOp into a call of a recording function, runs in-process with a 2 s alarm. Usage: python3 s3c_hazards.py GEN_DIR OUT
"""
import ast, contextlib, glob, gzip, io, json, os, signal, sys
from collections import defaultdict


class Rw(ast.NodeTransformer):
    def visit_BinOp(self, n):
        self.generic_visit(n)
        if isinstance(n.op, (ast.FloorDiv, ast.Mod)):
            name = "__fd" if isinstance(n.op, ast.FloorDiv) else "__md"
            return ast.copy_location(ast.Call(func=ast.Name(name, ast.Load()), args=[n.left, n.right], keywords=[]), n)
        return n


def main():
    gen, outp = sys.argv[1], sys.argv[2]
    res = {}
    for fn in sorted(glob.glob(os.path.join(gen, "*.jsonl.gz"))):
        rows = [json.loads(l) for l in gzip.open(fn, "rt")]
        lid = rows[0]["lid"]
        st = defaultdict(int)
        for r in rows:
            flag = {"neg_div_mod": False}

            def fd(a, b):
                if isinstance(a, int) and isinstance(b, int) and (a < 0 or b < 0):
                    flag["neg_div_mod"] = True
                return a // b

            def md(a, b):
                if isinstance(a, int) and isinstance(b, int) and (a < 0 or b < 0):
                    flag["neg_div_mod"] = True
                return a % b

            t = Rw().visit(ast.parse(r["src"]))
            ast.fix_missing_locations(t)
            depth = {"cur": 0, "max": 0}

            def prof(frame, event, arg):
                if frame.f_code.co_filename == "<h>":
                    if event == "call":
                        depth["cur"] += 1
                        depth["max"] = max(depth["max"], depth["cur"])
                    elif event == "return":
                        depth["cur"] -= 1

            buf = io.StringIO()
            signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))
            signal.setitimer(signal.ITIMER_REAL, 2.0)
            try:
                with contextlib.redirect_stdout(buf):
                    sys.setprofile(prof)
                    try:
                        exec(compile(t, "<h>", "exec"), {"__fd": fd, "__md": md, "__name__": "__h__"})
                    finally:
                        sys.setprofile(None)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            if buf.getvalue()[:-1] != r["key"]:
                st["instrumented_output_differs"] += 1
            st["neg_div_mod"] += flag["neg_div_mod"]
            negslice = any(isinstance(s, ast.Slice) and any(isinstance(x, ast.UnaryOp) for x in (s.lower, s.upper, s.step) if x is not None)
                           for s in ast.walk(ast.parse(r["src"])))
            st["neg_slice"] += negslice
            st["max_depth"] = max(st["max_depth"], depth["max"] - 1)  # minus the module frame
        res[lid] = dict(st)
        print(lid, dict(st), flush=True)
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
