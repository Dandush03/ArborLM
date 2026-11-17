"""Re-check auditor C: malformed (partial) combined records in a study record. Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
Usage: <python> check_malformed_combined.py <pin>"""
import copy, sys
from pathlib import Path
PIN = sys.argv[1]; sys.path.insert(0, PIN); sys.path.insert(0, PIN + "/src"); sys.path.insert(0, str(Path(__file__).parent))
from studies.p10s2 import analysis  # noqa: E402
import check_edges_v2_lib as E  # noqa: E402
st = E.build()
cases = {
    "C1 is an empty mapping": lambda c: c.__setitem__("C1", {}),
    "C2 lacks tested_sentences": lambda c: c["C2"].pop("tested_sentences"),
    "single lacks scores": lambda c: c.__setitem__("single", {}),
    "single scores shorter than n": lambda c: c["single"]["scores"].__setitem__("A", c["single"]["scores"]["A"][:2]),
    "tested_by_language A is None": lambda c: c["C1"]["tested_by_language"].__setitem__("A", None),
}
for name, f in cases.items():
    s = copy.deepcopy(st)
    f(s["replicates"][0]["cells"]["r0/MAF/AB"]["scores"]["r0/MAF/AB"]["combined"])
    try:
        out = analysis.analyze(s, bootstrap_mode="test", bootstrap_resamples=200)
        print(f"{name}: row {out['label_row']}; MAF C1 composition {out['composition'].get('arms', {}).get('C1', {}).get('M-append-frozen', {}).get('composition')}")
    except Exception as e:  # noqa: BLE001
        print(f"{name}: analyze raises {type(e).__name__}: {str(e)[:80]}")
