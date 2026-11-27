import json
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2"
def items(l):
    return [json.loads(x) for x in open(f"{F}/R2.{l}/fixtures.jsonl")]
# heap duplicates
dup = [ (it["level"],it["index"]) for it in items("min_heap_ops") if len(set(it["structured"]["xs"]))!=len(it["structured"]["xs"])]
print("heap items with duplicate values:", len(dup), dup[:10])
print("heap removals>=len:", sum(1 for it in items("min_heap_ops") if it["structured"]["removals"]>=len(it["structured"]["xs"])))
g = items("grid_sum")
print("grid shapes:", sorted({(len(i["structured"]["grid"]),len(i["structured"]["grid"][0])) for i in g}))
print("non-square diag:", sum(1 for i in g if i["structured"]["what"].startswith("the diag") and len(i["structured"]["grid"])!=len(i["structured"]["grid"][0])))
print("ragged:", sum(1 for i in g if len({len(r) for r in i["structured"]["grid"]})!=1))
print("min list_ops len:", min(len(i["structured"]["xs"]) for i in items("list_ops")))
print("min n base:", min(i["structured"]["n"] for i in items("to_base_wide")))
print("sort dups:", sum(1 for i in items("sort_list") if len(set(i["structured"]["xs"]))!=len(i["structured"]["xs"])))
print("rewrite overlapping-self patterns:", sorted({r[0] for i in items("string_rewrite_nonidentity") for r in i["structured"]["rules"]}))
print("luhn lens:", sorted({len(i["structured"]["digits"]) for i in items("luhn_check")}), "leading zero:", sum(1 for i in items("luhn_check") if i["structured"]["digits"][0]==0))
print("run_length alphabet:", sorted({c for i in items("run_length") for c in i["structured"]["s"]}))
