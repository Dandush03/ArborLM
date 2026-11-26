"""Pair audit controls. (1) Overlap: fresh items whose question text equals an authoring fixture's question (same lineage).
(2) Sensitivity: the comparison must be able to fail - each solver's answer for item j compared with the key of item j+1 of the
same lineage and level (a shifted key); counts how often that differs. (3) Key-distribution sanity: distinct keys per lineage, and
the share of the modal key (a constant answer would make 0 mismatches cheap). (4) Determinism: each solver applied twice to the
first 50 items of each lineage, results equal. Standard library only."""
import collections, copy, importlib.util, json, sys
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
OUT = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126"
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126"
fn_of = {}
for f in ["r1", "r2a", "r2b", "m1a", "m1b", "m1c", "c1"]:
    spec = importlib.util.spec_from_file_location(f"pa_ctl_{f}", f"{W}/studies/m0/solvers2/solver2_{f}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); fn_of.update(mod.SOLVERS)
for ev in ("R1", "R2", "M1", "C1"):
    rows = [json.loads(l) for l in open(f"{OUT}/work/items_{ev}.jsonl")]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["id"]].append(r)
    ov_tot = shifted_diff = shifted_n = nondet = 0
    print(f"== {ev}")
    for lid, rs in by.items():
        fq = {json.loads(l)["question"] for l in open(f"{F}/{ev}/{lid}/fixtures.jsonl")}
        ov = sum(r["question"] in fq for r in rs); ov_tot += ov
        keys = collections.Counter(r["key"] for r in rs)
        modal = keys.most_common(1)[0][1] / len(rs)
        for a, b in zip(rs, rs[1:]):
            if a["level"] != b["level"]:
                continue
            ans = fn_of[lid](a["question"], copy.deepcopy(a["structured"]))
            shifted_n += 1; shifted_diff += (ans != b["key"])
        for r in rs[:50]:
            x = fn_of[lid](r["question"], copy.deepcopy(r["structured"])); y = fn_of[lid](r["question"], copy.deepcopy(r["structured"]))
            nondet += (x != y)
        print(f"  {lid}: fresh items equal to an authoring fixture question: {ov}; distinct keys {len(keys)}; modal-key share {modal:.3f}")
    print(f"  {ev} overlap total {ov_tot}; shifted-key control: {shifted_diff}/{shifted_n} differ; nondeterministic repeats {nondet}")
