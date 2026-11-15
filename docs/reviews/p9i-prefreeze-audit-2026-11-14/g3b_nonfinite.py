"""G3b (auditor, Opus 5.5): which non-finite values stop the registered analyze worker. Re-uses the record
builder of g3_analyze_report.py (imported by path, scenarios there are not re-run) on synthetic records of
the 57 registered cells, INVENTED accuracies:

  S9a  only the dense comparison has a zero denominator (D7 = 0 at 65,536 while W7 is PARTIAL there);
  S9b  only the backbone contrast has a zero denominator (W7 = 0 at 16,384 while E7 is positive);
  S9c  both zero accuracies but in places no ratio reads them (D7 = 0 while W7 FAILS);
  S11  a BB eval record whose language-modelling relative rise was non-finite (``evaluate._finite`` -> None);
  S12  the pool path (cmd_analyze) on S9a: what the registered analyze stage would record.

Usage: PYTHONPATH=. uv run --locked python <this> <scratch dir> <committed attempt-1 gates.json>
"""
import importlib.util
import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g3", HERE / "g3_analyze_report.py")
assert spec and spec.loader
# g3 runs its scenarios at import; give it a throw-away scratch so that only its helpers are used here
SCRATCH = Path(sys.argv[1])
sys.argv = [sys.argv[0], str(SCRATCH / "g3_import_side_effect"), sys.argv[2]]
g3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g3)
print("\n######## g3b scenarios (above: g3 re-executed on import, ignore)\n")

from studies.p9i import stages  # noqa: E402


def attempt(name, acc, **kw):
    run = g3.build("g3b_" + name, acc, **kw)
    a, r, err = g3.run_workers(run)
    last = err.strip().splitlines()[-1] if err else ""
    print(f"{name}: analyze {a}, report {r}, analysis.json written {(run / 'analysis.json').is_file()}; {last}")
    return run


def s9a(c):
    if c.arm == "D7" and c.slots == 65536:
        return 0.0, False
    if c.arm == "W7" and c.slots == 65536:
        return 0.40, False
    return None


def s9b(c):
    if c.arm == "W7" and c.slots == 16384:
        return 0.0, True
    if c.arm == "E7":
        return 0.40, False
    return None


def s9c(c):
    if c.arm == "D7":
        return 0.0, False
    if c.arm == "W7":
        return 0.0, True
    return None


attempt("S9a_dense_zero", lambda c: g3.base(c, (), override=s9a))
attempt("S9b_contrast_zero", lambda c: g3.base(c, (), override=s9b))
attempt("S9c_zero_unread", lambda c: g3.base(c, (), override=s9c))

run = g3.build("g3b_S11_lm_none", lambda c: g3.base(c, ("BB",)))
p = g3.core.eval_path(run, "BB-n4096-b101-o301-s1801", g3.U, "eval").with_name("eval.json")
rec = json.loads(p.read_text())
rec["language_modelling"]["relative_rise"] = None
p.unlink()
g3.write_json(p, rec)
try:
    a = stages.main(["work", "analyze", "--mode", "rehearsal", "--run-dir", str(run), "--calibration", str(g3.CAL)])
    print(f"S11_lm_none: analyze {a}")
except Exception:  # noqa: BLE001
    print("S11_lm_none: analyze raised " + traceback.format_exc(limit=1).strip().splitlines()[-1])

run = g3.build("g3b_S12_pool", lambda c: g3.base(c, (), override=s9a))
common = ["--mode", "rehearsal", "--run-dir", str(run), "--calibration", str(g3.CAL), "--experiments-root", str(SCRATCH), "--ledger", str(SCRATCH / "ledger_g3b.json"), "--stage-cap-seconds", "300", "--workers", "1"]
a = stages.main(["analyze", *common])
m = json.loads((run / "analyze" / "manifest.json").read_text())
print(f"S12_pool: cmd_analyze exit {a}; manifest status {m['status']}; task {[(t['label'], t['status'], t['reason']) for t in m['tasks']]}; analysis.json {(run / 'analysis.json').is_file()}")
r = stages.main(["report", *common])
print(f"S12_pool: cmd_report exit {r}; results.json {(run / 'results' / 'results.json').is_file()}")
