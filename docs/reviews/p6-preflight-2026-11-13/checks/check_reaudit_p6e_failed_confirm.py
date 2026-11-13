import json, sys
from pathlib import Path
from arborlm.p6_common import StudyArgs
from arborlm.p6_retrieval_study import analyze_stage
root, out = Path(sys.argv[1]), Path(sys.argv[2])
conf = next((root / "confirm").iterdir())
r = json.loads((conf / "result.json").read_text()); r["status"] = "failed"; r["reason"] = "simulated worker cap breach"
(conf / "result.json").write_text(json.dumps(r))
args = StudyArgs(data_dir=out, parent_suite=out, output_root=out, results_root=root, synthetic=True, pair_count=2, rounds=1)
code = analyze_stage(args, ["x"])
ana = sorted((root / "analysis").iterdir())[-1]
res = json.loads((ana / "result.json").read_text())
print("exit", code, "status", res["status"], "reason", res["reason"], "has analysis:", "analysis" in res)
