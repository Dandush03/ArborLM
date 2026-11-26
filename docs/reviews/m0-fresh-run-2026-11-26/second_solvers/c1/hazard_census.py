"""Count, at run time, how often each semantic hazard is actually exercised by the fixtures,
and print one example item id per hazard (for hand checking)."""
import json, os, sys, collections, ast
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solver2_c1 as S
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
cnt = collections.Counter(); ex = {}
cur = [None]
def hit(k):
    cnt[k] += 1; ex.setdefault(k, cur[0])
of, om, os_ = S.floordiv, S.mod, S.slice_positions
def fd(a, b):
    if S.as_int(a) < 0 or S.as_int(b) < 0: hit("floordiv/mod with a negative operand")
    return of(a, b)
def sp(n, lo, hi, st):
    for v in (lo, hi):
        if v is not None and (v < 0 or v > n): hit("slice bound negative or out of range")
    if st is not None and st < 0: hit("slice negative step")
    if st is not None and abs(st) > 1: hit("slice |step|>1")
    return os_(n, lo, hi, st)
S.floordiv = fd; S.slice_positions = sp
oi = S.norm_index
def ni(seq, i):
    if S.as_int(i) < 0: hit("negative index")
    return oi(seq, i)
S.norm_index = ni
orig_eval = S.Interp.eval
def ev(self, e, frame):
    v = orig_eval(self, e, frame)
    if isinstance(e, ast.BoolOp) and not isinstance(v, bool): hit("and/or returned a non-bool operand")
    if isinstance(e, ast.Compare) and len(e.ops) > 1: hit("chained comparison")
    if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mult) and isinstance(v, (str, list)): hit("sequence repetition")
    return v
S.Interp.eval = ev
orig_call = S.Interp.call
def call(self, fn, args):
    if isinstance(fn, S.Function):
        if self.depth >= 1: hit("nested/recursive user call")
        if any(isinstance(a, list) for a in args): hit("list passed to a user function (aliasing via parameter)")
    return orig_call(self, fn, args)
S.Interp.call = call
orig_exec = S.Interp.exec_stmt
def exs(self, s, frame):
    if isinstance(s, ast.Assign) and isinstance(s.targets[0], ast.Name) and isinstance(s.value, ast.Name):
        v = self.lookup(s.value.id, frame)
        if isinstance(v, list): hit("name-to-name assignment of a list (alias)")
    if isinstance(s, ast.AugAssign):
        v = self.lookup(s.target.id, frame)
        if isinstance(v, list): hit("list += (in place)")
    return orig_exec(self, s, frame)
S.Interp.exec_stmt = exs
for lin in sorted(os.listdir(F)):
    for l in open(os.path.join(F, lin, "fixtures.jsonl")):
        it = json.loads(l); cur[0] = (lin, it["level"], it["index"])
        S.solve_c1(it["question"], it["structured"])
for k in sorted(cnt): print("%-60s %7d  e.g. %s" % (k, cnt[k], ex[k]))
