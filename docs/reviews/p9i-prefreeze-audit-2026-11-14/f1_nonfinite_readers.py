"""F1 (auditor, Opus 5.5): final re-check of the X1/X2 fix (commit 8261f22) on the reader side.

Re-uses the synthetic 57-cell record builder of g3_analyze_report.py (imported by path; g3 re-runs its own
scenarios on import into a throw-away directory). INVENTED accuracies and losses; nothing is a measurement.

  L   the BB eval record at 16,384 / seed 1801 carries a relative rise of +inf, -inf, nan, None (legacy),
      0.05, the next float above 0.05, or 0.0. Expected label (hand-written from section I.8.2 and the
      lead's ruling on X2): DEGRADED for every non-finite value and for > 0.05; PRESERVED otherwise.
      Selection and classes must equal the all-finite case (LM never blocks selection). Every written file
      must be strict JSON (no NaN / Infinity tokens).
  E   evaluate.language_modelling + evaluate._finite (the eval-record writer) on chosen (before, after)
      losses; finite cases compared with the dd8b205 formula ``rise > 0.05``.
  Q   finite equivalence: the same run inputs analysed and reported by the HEAD workers and by the dd8b205
      workers (a clone, subprocess); analysis.json and results.json compared without ``identity``,
      RESULTS.md / classes.csv / cells.csv compared byte for byte.

Usage: PYTHONPATH=. uv run --locked python <this> <scratch dir> <attempt-1 gates.json> <dd8b205 clone> <python>
"""
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SCRATCH, GATES, CLONE, PY = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4]
spec = importlib.util.spec_from_file_location("g3", HERE / "g3_analyze_report.py")
assert spec and spec.loader
sys.argv = [sys.argv[0], str(SCRATCH / "g3_import_side_effect"), GATES]
g3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g3)
print("\n######## f1 (above: g3 re-executed on import, ignore)\n")

from arborlm.io import file_sha256  # noqa: E402
from studies.p9i import classes, core, evaluate  # noqa: E402

FAIL: list[str] = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


def strict(path: Path) -> bool:
    def bad(tok):
        raise ValueError(tok)
    try:
        json.loads(path.read_text(), parse_constant=bad)
        return True
    except ValueError:
        return False


def no_bad_tokens(run: Path) -> bool:
    files = [p for p in run.rglob("*.json")]
    return all(strict(p) for p in files)


BB = "BB-n16384-b101-o301-s1801"
CASES = [("+inf", True), ("-inf", True), ("nan", True), (None, True), (0.05, False), (math.nextafter(0.05, 1.0), True), (0.0, False)]
ref_classes = None
for value, degraded in CASES:
    name = f"L_{value!s}".replace("+", "p").replace("-", "m")
    print(f"== {name}: BB 16,384 s1801 relative_rise = {value!r}; expected {'DEGRADED' if degraded else 'PRESERVED'}")
    run = g3.build(name, lambda c: g3.base(c, ("BB",)))
    p = core.eval_path(run, BB, g3.U, "eval").with_name("eval.json")
    rec = json.loads(p.read_text())
    rec["language_modelling"] = {"before_nats": 2.0, "after_nats": value if value is None or isinstance(value, str) else 2.0 * (1 + value), "relative_rise": value, "degraded": degraded}
    p.unlink()
    g3.write_json(p, rec)
    a, r, err = g3.run_workers(run)
    check(f"{name}: analyze 0, report 0", a == 0 and r == 0, err.strip().splitlines()[-1] if err else "")
    if a != 0:
        continue
    an = json.loads((run / "analysis.json").read_text())
    note = an["analysis"]["annotations"]["BB"]
    lab = {s: note[s]["language_modelling"]["label"] for s in ("4096", "16384", "65536")}
    want = classes.LM_DEGRADED if degraded else "LANGUAGE MODELLING PRESERVED"
    check(f"{name}: label at 16384", lab["16384"] == want, f"got {lab['16384']}")
    check(f"{name}: 4096 / 65536 preserved", lab["4096"] == lab["65536"] == "LANGUAGE MODELLING PRESERVED")
    stored = note["16384"]["language_modelling"]["relative_rises"]["1801"]
    want_stored = "nan" if value is None else value
    check(f"{name}: stored rise", stored == want_stored, f"stored {stored!r}")
    sel = an["analysis"]["selection"]
    check(f"{name}: selection BB step 1", (sel["outcome"], sel["step"]) == ("BB", 1))
    if ref_classes is None:
        ref_classes = an["analysis"]["classes"]
    check(f"{name}: classes equal the first case", an["analysis"]["classes"] == ref_classes)
    check(f"{name}: every JSON file strict (no NaN/Infinity)", no_bad_tokens(run))
    if r == 0:
        rows = (run / "results" / "classes.csv").read_text().splitlines()
        row = [x for x in rows if x.startswith("BB,16384,")]
        check(f"{name}: classes.csv BB 16384 column", len(row) == 1 and row[0].endswith("," + want), row[0][-60:] if row else "missing")
        cells = (run / "results" / "cells.csv").read_text().splitlines()
        head = cells[0].split(",")
        bbrow = [x for x in cells if x.startswith(BB + ",")][0].split(",")
        got = bbrow[head.index("lm_relative_rise")]
        check(f"{name}: cells.csv lm_relative_rise", got == ("" if value is None else str(value)), f"{got!r}")
        md = (run / "results" / "RESULTS.md").read_text()
        check(f"{name}: RESULTS.md BB 16384 row", f"| BB | 16384 | INTERFACE_WORKS | BEATS DENSE | {want} |" in md)

print("== E: evaluate.language_modelling + evaluate._finite on chosen losses")
inf, nan = math.inf, math.nan
pairs = [(2.0, inf), (2.0, nan), (inf, inf), (nan, 2.0), (2.0, -inf), (2.0, 2.1), (2.0, 2.0), (2.0, 1.0), (1.7, 1.785), (1.7, 1.7850001)]
orig = evaluate.next_byte_loss
for before, after in pairs:
    seq = iter([before, after])
    evaluate.next_byte_loss = lambda bb, rows, _s=seq: next(_s)
    out = evaluate._finite({"language_modelling": evaluate.language_modelling(SimpleNamespace(backbone=None), None, None)})["language_modelling"]
    rise = (after - before) / before
    if math.isfinite(rise):
        exp = {"before_nats": before, "after_nats": after, "relative_rise": rise, "degraded": rise > core.LM_DEGRADED_RELATIVE}  # dd8b205 formula
    else:
        exp = {"before_nats": before if math.isfinite(before) else core.nonfinite_str(before), "after_nats": after if math.isfinite(after) else core.nonfinite_str(after),
               "relative_rise": core.nonfinite_str(rise), "degraded": True}  # fmt: skip
    ok = out == exp and json.dumps(out, allow_nan=False) is not None
    check(f"E ({before}, {after})", ok, json.dumps(out))
evaluate.next_byte_loss = orig

print("== Q: finite equivalence HEAD vs dd8b205 (workers on identical inputs)")
CAL = g3.CAL
roots = sorted(p for p in (SCRATCH / "g3_import_side_effect").iterdir() if p.name[:2] in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8") and p.name != "S10_pool")
roots += [SCRATCH / "g3_import_side_effect" / n for n in ("L_0.05", "L_0.0", f"L_{math.nextafter(0.05, 1.0)!s}")]  # attempt 1 (kept) looked in SCRATCH: g3.build writes under g3.SCRATCH
for src in roots:
    old = SCRATCH / "dd8b205" / src.name
    shutil.copytree(src, old, ignore=shutil.ignore_patterns("analysis.json", "results"))
    common = ["--mode", "rehearsal", "--run-dir", str(old), "--calibration", str(CAL), "--calibration-sha256", file_sha256(CAL), "--experiments-root", str(SCRATCH)]
    rc = [subprocess.run([PY, "-m", "studies.p9i.stages", "work", w, *common], cwd=CLONE, env={"PYTHONPATH": str(CLONE), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True).returncode for w in ("analyze", "report")]
    new_a, old_a = json.loads((src / "analysis.json").read_text()), json.loads((old / "analysis.json").read_text())
    new_a.pop("identity"), old_a.pop("identity")
    same = [new_a == old_a]
    for f in ("RESULTS.md", "classes.csv", "cells.csv"):
        same.append((src / "results" / f).read_bytes() == (old / "results" / f).read_bytes())
    nr, orr = json.loads((src / "results" / "results.json").read_text()), json.loads((old / "results" / "results.json").read_text())
    same.append(nr == orr)
    check(f"Q {src.name}: dd8b205 exit {rc}; analysis / RESULTS.md / classes.csv / cells.csv / results.json equal", rc == [0, 0] and all(same), str(same))

print(f"\nFAILED CHECKS: {len(FAIL)} {FAIL}")
