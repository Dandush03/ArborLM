"""Compare the character set of my answers per lineage with the format fact stated in each SCHEMA.md."""
import json, os, re, collections
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
D = os.path.dirname(os.path.abspath(__file__))
ans = collections.defaultdict(list)
for line in open(os.path.join(D, "answers_c1.jsonl")):
    r = json.loads(line); ans[r["id"]].append(r["answer"])
for lin in sorted(ans):
    sch = open(os.path.join(F, lin, "SCHEMA.md")).read()
    m = re.search(r"Character set of the builder's printed lines across this lineage's 280 items \(format fact only\): '(.*)'\.", sch)
    kinds = re.search(r"Kinds of printed value seen across this lineage's 280 builder keys \(a format fact only\): ([^.]*)\.", sch)
    stated = set(m.group(1)) if m else None
    mine = set("".join(ans[lin]))
    status = "OK" if stated is not None and mine == stated else ("SUBSET" if stated and mine < stated else "DIFF")
    print(lin, status, "stated=", "".join(sorted(stated)) if stated else None, "mine=", "".join(sorted(mine)),
          "extra=", "".join(sorted(mine - stated)) if stated else "", "| kinds:", kinds.group(1) if kinds else None)
