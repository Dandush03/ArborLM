# ruff: noqa
"""Comparison harness ONLY (not the recomputation): runs the STUDY's own frozen analysis (archived read-only copy of commit 46bf55a in ./frozen) on the
counting rehearsal's records, with the replicate count patched to 1 in memory (config thresholds and the module constants of studies.p10s1.core), so
that its per-replicate quantities, verdicts, classes and labels can be compared with recompute.py's on the same one-replicate data.
Usage: PYTHONPATH=frozen:frozen/src python -B run_study_analysis_on_rehearsal.py <run-dir> <view-plan> <rehearsal-record> <out.json>"""

import copy
import json
import sys
from pathlib import Path

from studies.p10is1 import analysis, core
from studies.p10s1 import core as s1core

run, planp, rehp, outp = (Path(x) for x in sys.argv[1:5])
cfg = copy.deepcopy(dict(core.load_config(Path("frozen/configs/p10is1_capacity.toml"))))
th = dict(cfg["thresholds"])
FIVE = len(sys.argv) > 5 and sys.argv[5] == "five"  # a five-replicate (synthetic) run directory: no patching at all
if not FIVE:
    th.update(replicates=1, paired_all=1, paired_most=1, sparse_ratio_min_replicates=1, unloaded_min=1)  # the "at least 2" counts stay at 2, as in recompute.py --replicates 1
cfg["thresholds"] = th
if not FIVE:
    for name in ("REPLICATES",):
        if hasattr(s1core, name):
            setattr(s1core, name, 1)
    if hasattr(s1core, "PAIRED_MOST"):
        s1core.PAIRED_MOST = 1
    for name in ("REPLICATES", "PAIRED_MOST"):
        if hasattr(core, name):
            setattr(core, name, 1)
plan = json.loads(planp.read_text())
cells = plan["cells"]
reads, baselines = {}, {}
for c in cells:
    d = run / "evaluate" / c["label"]
    for p in sorted(d.glob("u*.json")) if d.is_dir() else []:
        rec = json.loads(p.read_text())
        for rn, body in rec["reads"].items():
            reads[core.read_key(c["label"], int(rec["update"]), rn)] = {"panels": body["panels"]}
for p in sorted((run / "baselines").glob("*.json")):
    r = json.loads(p.read_text())
    if r.get("kind") == "baseline":
        baselines[core.baseline_key(int(r["draw"]), int(r["facts"]))] = {k: int(v) for k, v in r["no_memory"].items()}
stops = {}
for p in sorted((run / "ladder").glob("*.json")):
    r = json.loads(p.read_text())
    if r.get("kind") != "stage_manifest" and "u_run" in r and "cell_name" in r:
        stops[r["cell_name"]] = {"u_run": int(r["u_run"])}
tp = run / "timing" / "timing.json"
cpu = {k: float(v) for k, v in json.loads(tp.read_text())["cpu"].items()} if tp.is_file() else None
cal = plan.get("calibration", {})
h8 = cal.get("h8", {})
reg = analysis.Registry(cells=cells, reads=reads, baselines=baselines, ladder_stops=stops, cpu=cpu, qualification=dict(json.loads(rehp.read_text()).get("qualification") or {}),
                        calibration={"h8_undertrained": h8.get("undertrained_cells", []), "h8_calibrated": h8.get("calibrated_cells", []), "sat256": bool(cal.get("sat256", True))}, status={}, cfg=cfg)
res = analysis.analyze(reg)
outp.write_text(json.dumps(core.jsonable(res), indent=1, sort_keys=True, default=str))
print(json.dumps({"status": res.get("status"), "lines": res.get("lines")}, indent=1))
