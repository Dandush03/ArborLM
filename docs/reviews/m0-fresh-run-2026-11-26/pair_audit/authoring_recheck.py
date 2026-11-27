"""Pair audit: recompute (independently of the lead's compare.py) the new solvers' agreement with the builder's keys on the
22,960 authoring fixtures: solver applied afresh to (question, structured), compared with keys.jsonl as strings."""
import copy, glob, importlib.util, json, collections
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126"
K = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_keys_20261126"
fn = {}
for f in ["r1", "r2a", "r2b", "m1a", "m1b", "m1c", "c1"]:
    spec = importlib.util.spec_from_file_location(f"pa_ar_{f}", f"{W}/studies/m0/solvers2/solver2_{f}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); fn.update(mod.SOLVERS)
tot = collections.Counter()
for p in sorted(glob.glob(F + "/*/*/fixtures.jsonl")):
    ev, lid = p.split("/")[-3:-1]
    keys = [json.loads(l) for l in open(f"{K}/{ev}/{lid}/keys.jsonl")]
    for r, k in zip(map(json.loads, open(p)), keys):
        assert (r["level"], r["index"]) == (k["level"], k["index"])
        tot[ev, "items"] += 1
        try:
            a = fn[lid](r["question"], copy.deepcopy(r["structured"]))
        except Exception as e:  # noqa: BLE001
            tot[ev, "errors"] += 1; print("ERROR", lid, r["level"], r["index"], e); continue
        if str(a) != str(k["key"]):
            tot[ev, "mismatches"] += 1; print("MISMATCH", lid, r["level"], r["index"])
for ev in ("R1", "R2", "M1", "C1"):
    print(ev, "items", tot[ev, "items"], "mismatches", tot[ev, "mismatches"], "errors", tot[ev, "errors"])
print("TOTAL items", sum(v for (e, t), v in tot.items() if t == "items"), "mismatches", sum(v for (e, t), v in tot.items() if t == "mismatches"),
      "errors", sum(v for (e, t), v in tot.items() if t == "errors"))
