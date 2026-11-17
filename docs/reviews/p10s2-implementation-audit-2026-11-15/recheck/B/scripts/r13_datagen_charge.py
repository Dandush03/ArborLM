"""Re-check B, R13 (old B3): the data-generation step is charged to the study ledger and capped. datagen.charged_stage with a ledger in my folder (no real data, nothing downloaded).
(a) a step that completes; (b) a step stopped by its guard (cap 0.5 s around a 3 s Python loop); (c) refusal to start when the ledger has less room than the stage cap; (d) freeze.prefreeze_caps_from_ledger.
Usage: PYTHONPATH=<pin>/src python r13_datagen_charge.py <pin> <work dir>"""
import json, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from studies.p10s2 import datagen, freeze
from studies.p10s2.ledger import Ledger
W = Path(sys.argv[2]).resolve(); shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
led = Ledger(W / "ledger.jsonl"); out = {}
with datagen.charged_stage(led, 60.0, guard=True) as c:
    time.sleep(0.2)
out["a_entries"] = [(e["kind"], e["status"], round(e["wall_seconds"], 2)) for e in led.entries()]
t0 = time.perf_counter()
try:
    with datagen.charged_stage(led, 0.5, guard=True) as c:
        while time.perf_counter() - t0 < 3.0:
            sum(range(1000))
    out["b"] = "not stopped"
except datagen.StageCapExceeded as e:
    out["b"] = f"StageCapExceeded after {time.perf_counter() - t0:.2f} s: {e}"
out["b_entries"] = [(e["kind"], e["status"], round(e["wall_seconds"], 2)) for e in led.entries()][2:]
led.record("audit-other", 35.9 * 3600, process="recheck: fill the ledger")
n = len(led.entries())
try:
    with datagen.charged_stage(led, 6480.0, guard=True):
        out["c"] = "started"
except datagen.StageCapExceeded as e:
    out["c"] = f"refused: {e}"
out["c_new_entries"] = len(led.entries()) - n
out["d_prefreeze_caps"] = freeze.prefreeze_caps_from_ledger(led)
print(json.dumps(out, indent=1))
