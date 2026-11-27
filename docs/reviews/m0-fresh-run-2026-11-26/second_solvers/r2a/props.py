import json, math, collections
F="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2/"
def rows(l): return [json.loads(x) for x in open(F+l+"/fixtures.jsonl")]
A={json.loads(x)["id"]+"|%d|%d"%(json.loads(x)["level"],json.loads(x)["index"]):json.loads(x)["answer"] for x in open("/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_solver2_r2a_20261126/answers_r2a.jsonl")}
key=lambda r:r["id"]+"|%d|%d"%(r["level"],r["index"])
# binary search
c=collections.Counter()
for r in rows("R2.binary_search_trace"):
    s=r["structured"]; c["found" if s["target"] in s["xs"] else "notfound"]+=1; c["ask_"+s["ask"]]+=1
    c["distinct_sorted"]+= (s["xs"]==sorted(set(s["xs"])))
print("bst",dict(c))
c=collections.Counter()
for r in rows("R2.caesar_shift"):
    c["kmin"]=min(c.get("kmin",99),r["structured"]["k"]); c["kmax"]=max(c["kmax"],r["structured"]["k"])
print("caesar",dict(c))
c=collections.Counter()
for r in rows("R2.cellular_automaton"):
    s=r["structured"]; c["steps%d"%s["steps"]]+=1; c["full_table"]+= len(s["table"])==8
print("ca",dict(c))
c=collections.Counter()
for r in rows("R2.cheapest_network"):
    s=r["structured"]; pairs=[frozenset(e[:2]) for e in s["cables"]]
    c["dup_pairs"]+= len(pairs)!=len(set(pairs)); c["self_loop"]+=any(len(p)<2 for p in pairs)
    costs=[e[2] for e in s["cables"]]; c["tied_costs_items"]+= len(costs)!=len(set(costs))
    c["neg"]+=any(x<0 for x in costs)
print("mst",dict(c))
c=collections.Counter()
for r in rows("R2.count_divisible"):
    s=r["structured"]; c["t_in_list_and_div"]+= (s["t"] in s["xs"] and s["t"]%s["m"]==0); c["neg"]+=any(x<0 for x in s["xs"]); c["ans0"]+= A[key(r)]=="0"
    c["dups"]+= len(s["xs"])!=len(set(s["xs"]))
print("cd",dict(c))
c=collections.Counter(); mx=0
for r in rows("R2.crt_smallest"):
    cg=r["structured"]["congruences"]; ms=[n for _,n in cg]
    c["noncoprime"]+= any(math.gcd(a,b)>1 for i,a in enumerate(ms) for b in ms[i+1:])
    c["rem_ge_mod"]+= any(rr>=n for rr,n in cg); c["all_zero"]+= all(rr==0 for rr,_ in cg)
    mx=max(mx,int(A[key(r)]))
    c["ans_eq_lcm"]+= int(A[key(r)])==math.lcm(*ms)
print("crt",dict(c),"max answer",mx)
c=collections.Counter()
for r in rows("R2.dictionary_rank"):
    s=r["structured"]; c["L%d_n%d"%(s["length"],len(s["letters"]))]+=1
print("dict",dict(c))
c=collections.Counter()
import re
for r in rows("R2.expression_eval"):
    t=r["structured"]["text"]; c[r["structured"]["convention"]]+=1
    c["neg_ans"]+= A[key(r)].startswith("-")
    c["nested_parens"]+= bool(re.search(r"\([^()]*\(",t))
    c["paren_first_char_minus"]+= "(-" in t or t.startswith("-")
print("expr",dict(c))
c=collections.Counter()
for r in rows("R2.from_base"):
    c["base%d"%r["structured"]["base"]]+=1; c["leading0"]+= r["structured"]["digits"].startswith("0") and len(r["structured"]["digits"])>1
print("fb",dict(c))
