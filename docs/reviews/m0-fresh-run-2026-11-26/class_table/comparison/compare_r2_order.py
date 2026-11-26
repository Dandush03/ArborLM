import json,sys
F="/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"
S="/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_uncounted_second_20261126/deliver/uncounted_rules_second.json"
a=json.load(open(F))["R2"]["entries"]; b=[e for e in json.load(open(S))["R2"] if e["kind"]=="klass_clause"]
A=sorted(((e["text"],e["label"]) for e in a)); B=sorted(((e["match"],e["class"]) for e in b))
print("multisets of (text,class) equal:",A==B, len(A))
# the first list numbers clauses per literal (1..35); the second numbers per if-statement. Order check:
fo={(e["text"],e["label"]):e["order"] for e in a}; so={(e["match"],e["class"]):e["clause_index"] for e in b}
seq=sorted(fo,key=lambda k:fo[k]); mono=all(so[seq[i]]<=so[seq[i+1]] for i in range(len(seq)-1))
print("statement index non-decreasing along the first list's literal order:",mono)
print("first orders:",sorted(fo.values())==list(range(1,36)),"second statement indices:",sorted(set(so.values())))
sys.exit(0 if (A==B and mono) else 1)
