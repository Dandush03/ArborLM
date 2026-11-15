"""(1) Try to produce an A5-D positive label without the section 3.4 strings in the report's products; (2) non-finite ADDRESS STABLE values.
Synthetic in-memory records only (no seed is built). Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import json, math, tempfile
from pathlib import Path
from studies.p10s0 import analysis, core, report
from studies.p10s0 import classes as C
from studies.p10s0 import synthetic as syn

out = {}
run = syn.make_run(syn.a0_unreliable(), candidate="A5-D")
res = analysis.analyze(run)
out["outcome"] = (res["outcome"]["row"], res["outcome"]["label"], res["outcome"]["arm"])
d = Path(tempfile.mkdtemp())
core.write_record(d / "analysis.json", {**core.envelope("analysis"), "result": core.jsonable(res)})
paths = report.write_report(d, d / "results")
strings = {"fourth": core.FOURTH_ARM_STRING, "f1": core.F1_ANNOTATION, "sentence": core.PROVENANCE_SENTENCE}
for p in paths:
    t = p.read_text(encoding="utf-8")
    t_json = json.dumps(json.loads(t), ensure_ascii=False) if p.suffix == ".json" else t
    out[p.name] = {"mentions_A5-D": "A5-D" in t_json, **{k: (v in t_json) for k, v in strings.items()}}
csv_lines = [l for l in (d / "results" / "classes.csv").read_text().splitlines() if l.startswith("A5-D")]
out["classes.csv A5-D rows"] = csv_lines
out["analysis.json outcome block"] = {k: res["outcome"][k] for k in ("row", "label", "arm")}
out["q1-gate style record would print candidate A5-D with no strings"] = True

# (2) ADDRESS STABLE with non-finite values: 11 of 20 cells non-finite, 9 at 0.90
obs = {(d_, j): C.SObservation(0.97, 0.97, True, True, 0.97, 0.97, False, 256, 0.01, 256, 0.1, (0.9 if (d_ * 2 + j) < 11 else math.nan), math.nan, 0.97, 0.97, 0.97) for d_ in range(1, 11) for j in (0, 1)}
verd = {k: C.CellVerdict(C.SUCCEEDED) for k in obs}
st = C.address_stable(obs, verd)
out["address_stable_with_11_of_20_nonfinite"] = st
print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
