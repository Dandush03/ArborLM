"""Per lineage: wrapper template count, number of distinct program skeletons (names and constants
abstracted), skeleton count per level, and the AST node/operator/call kinds used."""
import ast, json, os, collections
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
PRE = "Here is a Python program.\n\n"; SUF = "\n\nWhat exactly does it print? It prints a single line."
class Abs(ast.NodeTransformer):
    def visit_Name(self, n): return ast.copy_location(ast.Name("V", n.ctx), n)
    def visit_arg(self, n): return ast.arg("A")
    def visit_Constant(self, n): return ast.Constant("S" if isinstance(n.value, str) else 0)
    def visit_FunctionDef(self, n):
        self.generic_visit(n); n.name = "F"; return n
    def visit_List(self, n): return ast.List([], n.ctx)
for lin in sorted(os.listdir(F)):
    items = [json.loads(l) for l in open(os.path.join(F, lin, "fixtures.jsonl"))]
    wr = collections.Counter((it["question"][:len(PRE)], it["question"][-len(SUF):]) for it in items)
    sk = collections.Counter(); kinds = set(); perlv = collections.defaultdict(set)
    for it in items:
        t = ast.parse(it["question"][len(PRE):-len(SUF)])
        for n in ast.walk(t):
            k = type(n).__name__
            if k in ("Load", "Store", "Module", "arguments", "arg", "Name", "Constant", "Expr"): continue
            if isinstance(n, ast.Call):
                k = "call:" + (("." + n.func.attr) if isinstance(n.func, ast.Attribute) else (n.func.id if n.func.id in ("print","len","str","range","sum","max","min","abs","sorted") else "userfn"))
            kinds.add(k)
        s = ast.dump(Abs().visit(t)); sk[s] += 1; perlv[it["level"]].add(s)
    print(lin, "| wrappers:", len(wr), "| skeletons:", len(sk), "| per level:", [len(perlv[l]) for l in range(7)])
    print("    kinds:", " ".join(sorted(kinds)))
