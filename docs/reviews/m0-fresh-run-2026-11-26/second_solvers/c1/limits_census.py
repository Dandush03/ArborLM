"""Max user-call depth, max interpreter steps per item, and max int digit count rendered, over all C1 items."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solver2_c1 as S
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
mx = {"depth": (0, None), "digits": (0, None), "steps": (0, None)}; cur = [None]
oc = S.Interp.call
def call(self, fn, args):
    if self.depth + 1 > mx["depth"][0]: mx["depth"] = (self.depth + 1, cur[0])
    return oc(self, fn, args)
S.Interp.call = call
oi = S.int_to_str
def its(n):
    s = oi(n)
    if len(s) > mx["digits"][0]: mx["digits"] = (len(s), cur[0])
    return s
S.int_to_str = its
orun = S.run_module
for lin in sorted(os.listdir(F)):
    for l in open(os.path.join(F, lin, "fixtures.jsonl")):
        it = json.loads(l); cur[0] = (lin, it["level"], it["index"])
        import ast
        I = S.Interp(); I.exec_block(ast.parse(S.source_of(it["question"])).body, None)
        if I.steps > mx["steps"][0]: mx["steps"] = (I.steps, cur[0])
print(mx)
