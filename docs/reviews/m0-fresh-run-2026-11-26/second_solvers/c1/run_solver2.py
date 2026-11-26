"""Apply solver2_c1 to the C1 fixtures; write answers_c1.jsonl.
Also runs the structured-tree front end as a consistency check and reports
any item where the two disagree or either raises."""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_c1 as S  # noqa: E402

F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/C1"
out_path = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "answers_c1.jsonl")
assert not os.path.exists(out_path), "refusing to overwrite " + out_path
n = 0; errors = []; mism = []; fmt = []; per = collections.Counter()
with open(out_path, "w") as w:
    for lin in sorted(S.SOLVERS):
        for line in open(os.path.join(F, lin, "fixtures.jsonl")):
            it = json.loads(line)
            try:
                ans = S.SOLVERS[lin](it["question"], it["structured"])
            except Exception as ex:  # record, never hide
                ans = None
                errors.append((lin, it["level"], it["index"], type(ex).__name__, str(ex)))
            try:
                alt = S.solve_c1_structured(it["question"], it["structured"])
            except Exception as ex:
                alt = "<error %s: %s>" % (type(ex).__name__, ex)
            if ans != alt:
                mism.append((lin, it["level"], it["index"], ans, alt))
            if ans is not None and (ans == "" or "\n" in ans or ans != ans.strip() or "  " in ans
                                    or ans != ans.lower() or ans.endswith(".")):
                fmt.append((lin, it["level"], it["index"], ans))
            w.write(json.dumps({"id": it["id"], "level": it["level"], "index": it["index"], "answer": ans}) + "\n")
            n += 1; per[lin] += 1
print("items", n, "lineages", len(per), "per-lineage counts", sorted(set(per.values())))
print("solver exceptions", len(errors))
for e in errors: print("  ERR", e)
print("question-vs-structured disagreements", len(mism))
for m in mism[:50]: print("  MISMATCH", m)
print("answers violating the builder's stated format rules", len(fmt))
for f in fmt[:50]: print("  FMT", f)
