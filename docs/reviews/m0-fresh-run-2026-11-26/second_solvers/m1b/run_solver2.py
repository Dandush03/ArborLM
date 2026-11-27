"""Apply solver2_m1b to the fixtures; write answers_m1b.jsonl; report format checks."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_m1b as S  # noqa: E402

F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1"
INT = re.compile(r"^(0|[1-9]\d*)$")
SINT = re.compile(r"^(0|-?[1-9]\d*)$")
DEC = re.compile(r"^-?(0|[1-9]\d*)(\.\d?[1-9])?$")
FMT = {"M1.linear_equation_r3": SINT, "M1.median_list_r3": DEC, "M1.mixture_r4": DEC,
       "M1.percent_change_r3": DEC}
out = []
bad = 0
for lin in sorted(S.SOLVERS):
    n = 0
    for line in open(f"{F}/{lin}/fixtures.jsonl"):
        d = json.loads(line)
        before = len(S.INEXACT)
        try:
            a = S.SOLVERS[lin](d["question"], d["structured"])
        except Exception as e:  # report, do not hide
            print("EXCEPTION", d["id"], d["level"], d["index"], repr(e)); bad += 1; continue
        if len(S.INEXACT) != before:
            print("INEXACT(rounded)", d["id"], d["level"], d["index"], a)
        if a == "-0" or not FMT.get(lin, INT).match(a):
            print("BADFORMAT", d["id"], d["level"], d["index"], a); bad += 1
        out.append({"id": d["id"], "level": d["level"], "index": d["index"], "answer": a})
        n += 1
    print(lin, "answered", n)
with open(os.path.join(HERE, "answers_m1b.jsonl"), "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print("total", len(out), "bad", bad, "inexact", len(S.INEXACT))
