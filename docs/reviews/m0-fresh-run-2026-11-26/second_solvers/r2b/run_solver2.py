"""Apply solver2_r2b to the fixtures; write answers_r2b.jsonl; check format and text/structured agreement."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_r2b as S
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2"
FMT = {
    "R2.grid_sum": r"0|[1-9]\d*",
    "R2.list_ops": r"-?\d+(, -?\d+)*",
    "R2.min_heap_ops": r"-?\d+(, -?\d+)*",
    "R2.run_length": r"([a-z][1-9]\d*)+",
    "R2.sort_list": r"-?\d+(, -?\d+)*",
    "R2.string_rewrite_nonidentity": r"[abc]+",
    "R2.to_base_wide": r"[1-9a-f][0-9a-f]*|0",
}
out_path = os.path.join(HERE, "answers_r2b.jsonl")
if os.path.exists(out_path):
    sys.exit("refusing to overwrite " + out_path)
bad = 0; mism = 0; n = 0
with open(out_path, "w") as out:
    for lid in sorted(S.SOLVERS):
        for line in open(f"{F}/{lid}/fixtures.jsonl"):
            it = json.loads(line); n += 1
            q, st = it["question"], it["structured"]
            try:
                ans = S.SOLVERS[lid](q, st)
            except Exception as e:
                print("EXC", lid, it["level"], it["index"], repr(e)); bad += 1; ans = None
            if ans is not None:
                if lid == "R2.luhn_check":
                    ok = ans in ("yes", "no") if st["ask"] == "valid" else re.fullmatch(r"\d", ans) is not None
                else:
                    ok = re.fullmatch(FMT[lid], ans) is not None
                if not ok:
                    print("FMT", lid, it["level"], it["index"], repr(ans)); bad += 1
            tp = S.TEXT_PARSERS[lid](q)
            if tp != st:
                print("TEXT!=STRUCT", lid, it["level"], it["index"], tp, st); mism += 1
            out.write(json.dumps({"id": lid, "level": it["level"], "index": it["index"], "answer": ans}) + "\n")
print("items", n, "bad", bad, "text_struct_mismatch", mism)
