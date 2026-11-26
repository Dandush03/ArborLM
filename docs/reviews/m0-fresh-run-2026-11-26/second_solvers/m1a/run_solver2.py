"""Apply solver2_m1a to the fixtures; write answers_m1a.jsonl; cross-check text vs structured."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_m1a as S  # noqa: E402

FIX = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1/"
NUM = re.compile(r"^(0|[1-9]\d*)$")
SNUM = re.compile(r"^(0|-?[1-9]\d*)$")

out = []
problems = []
for lin, fn in S.SOLVERS.items():
    rows = [json.loads(l) for l in open(FIX + lin + "/fixtures.jsonl")]
    assert len(rows) == 280, (lin, len(rows))
    mism = 0
    for r in rows:
        q, st = r["question"], r["structured"]
        try:
            tp = S.TEXT_PARSERS[lin](q)
            for k, v in tp.items():
                if k in st and (v != st[k]):
                    mism += 1
                    problems.append((lin, r["id"], "text!=structured", k, v, st[k]))
            ans = fn(q, st)
            rx = SNUM if lin.endswith("consecutive_r3") else NUM
            if not rx.match(ans):
                problems.append((lin, r["id"], "badformat", ans))
        except Exception as e:  # noqa: BLE001
            ans = None
            problems.append((lin, r["id"], "error", repr(e)))
        out.append({"id": r["id"], "level": r["level"], "index": r["index"], "answer": ans})
    print(f"{lin}: {len(rows)} items, text/structured mismatches {mism}")
with open(os.path.join(HERE, "answers_m1a.jsonl"), "w") as f:
    for o in out:
        f.write(json.dumps(o) + "\n")
print("answers written:", len(out), "none:", sum(o["answer"] is None for o in out))
print("problems:", len(problems))
for p in problems:
    print("  ", p)
