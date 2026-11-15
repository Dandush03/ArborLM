"""Comparisons C1-C8 of FINAL_RECHECK.md: attempt 2 must reproduce attempt 1's deterministic values.

Usage: uv run --locked python <this> data|gates <committed attempt-1 dir> <attempt-1 run dir>
       <attempt-2 run dir>

Exit code 0 when every mandatory comparison holds, 1 otherwise. Reads no per-update loss log.
"""

import hashlib
import json
import sys
from pathlib import Path

STAGE = sys.argv[1]
REC, RUN1, RUN2 = (Path(p) for p in sys.argv[2:5])
SNAP = "restore_check/first/snapshots/u0000016"
failed: list[str] = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def check(name: str, ok: bool, mandatory: bool = True) -> None:
    print(f"{'ok  ' if ok else 'DIFF'} {name}{'' if mandatory else ' (reported only)'}")
    if mandatory and not ok:
        failed.append(name)


if STAGE == "data":
    check("C1 g1.json file identical", sha(REC / "g1.json") == sha(RUN2 / "g1.json"))
    old, new = load(REC / "data_manifest.json"), load(RUN2 / "data_manifest.json")
    same = old["sha256s"] == new["sha256s"] and len(new["sha256s"]) == 14
    check("C2 fourteen data hashes identical", same)
    rest_old = {k: v for k, v in old.items() if k != "identity"}
    rest_new = {k: v for k, v in new.items() if k != "identity"}
    check("C3 other manifest fields identical", rest_old == rest_new)
elif STAGE == "gates":
    old, new = load(REC / "gates.json"), load(RUN2 / "gates.json")
    check("C4 G2 block identical", old["g2"] == new["g2"])
    check("C5 controls block identical", old["controls"] == new["controls"])
    check("C6 restoration block identical", old["restoration"] == new["restoration"])
    for arm in ("N", "BB"):
        for name in ("model.pt", "optimizer.pt", "movement.pt", "snapshot.json"):
            a, b = (run / "g4_restore" / arm / SNAP / name for run in (RUN1, RUN2))
            check(f"C7 {arm} {name} identical", sha(a) == sha(b), mandatory=name != "snapshot.json")
    reach = all(r["all_reached"] and not r["stray"] for r in new["gradient_reach"].values())
    counts = {a: r["trainable"] for a, r in old["gradient_reach"].items()}
    same_counts = counts == {a: r["trainable"] for a, r in new["gradient_reach"].items()}
    check("C8 no G4 defect, all twelve arms reached, counts as attempt 1",
          not new["g4_defects"] and reach and same_counts and len(new["gradient_reach"]) == 12)
    check("gates passed", bool(new["g1_passed"] and new["g2_passed"] and new["g4_passed"]))
else:
    raise SystemExit("stage must be data or gates")
print("RESULT:", "ALL MANDATORY COMPARISONS HOLD" if not failed else f"MISMATCH: {failed}")
sys.exit(1 if failed else 0)
