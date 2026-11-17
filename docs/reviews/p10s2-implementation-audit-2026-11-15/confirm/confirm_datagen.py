"""Auditor probes of the data-generation attempt machinery (fakes only; tmp dirs; no network, no real ledger, no real data).
Run from the worktree: PYTHONPATH=src .venv/bin/python <this> <scratch dir>"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from studies.p10s2 import datagen  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

scratch = Path(sys.argv[1])
scratch.mkdir(parents=True, exist_ok=True)
out = scratch / "out"


class Fake:
    def __init__(self):
        self.led = Ledger(scratch / "ledger.jsonl")

    def remaining(self):
        return 10.0

    def measure(self, *a, **k):
        return self.led.measure(*a, **k)


def boom(exc):
    def f(*a, **k):
        raise exc

    return f


datagen.package_versions = lambda: {}
seq = [datagen.ScoreMismatch("first registered-test stop"), "release", datagen.RegisteredTestStop("second registered-test stop (e.g. chrF cross-check)")]
for step in seq:
    if step == "release":
        (out / "datagen_attempts" / "lead_release.json").write_text("{}")
        print("lead_release.json written once (content not read by the gate)")
        continue
    datagen._run = boom(step)
    try:
        datagen.run(scratch / "dl", out, led=Fake(), stage_cap_seconds=3600.0)
    except Exception as e:  # noqa: BLE001
        print(f"attempt stopped: {type(e).__name__}: {e}")
gate = datagen.datagen_rerun_gate(out)
print("after the SECOND registered-test stop, rerun gate =", gate, "(None means a re-run is allowed without a new lead release)")
print("attempt records:", sorted(p.name for p in (out / "datagen_attempts").glob("*.json")))
starts = [e for e in Fake().led.entries() if e["status"] == "started"]
print("datagen start markers carry cap_seconds:", [("cap_seconds" in e) for e in starts])
print("prefreeze_record keys include code_commit:", "code_commit" in json.loads((out / "prefreeze_record.json").read_text()))
