"""Per lineage: items in which // or % sees a negative operand; first example per lineage."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solver2_c1 as S
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
of = S.floordiv; flag = [False]
def fd(a, b):
    if S.as_int(a) < 0 or S.as_int(b) < 0: flag[0] = True
    return of(a, b)
S.floordiv = fd
per = collections.Counter(); ex = {}
for lin in sorted(os.listdir(F)):
    for l in open(os.path.join(F, lin, "fixtures.jsonl")):
        it = json.loads(l); flag[0] = False
        S.solve_c1(it["question"], it["structured"])
        if flag[0]: per[lin] += 1; ex.setdefault(lin, (it["level"], it["index"]))
for k in sorted(per): print(k, per[k], "items; e.g.", ex[k])
