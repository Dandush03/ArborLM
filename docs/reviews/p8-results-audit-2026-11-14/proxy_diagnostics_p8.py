"""Per-case means of the logged proxy diagnostics (ADR-0015 section 3 / 7.1) from every cell's
steps.jsonl. Auditor: Claude Opus 5.5. Not Astra validation, not human approval. Descriptive only.

Usage: python -I proxy_diagnostics_p8.py --train-run T
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-run", type=Path, required=True)
    a = ap.parse_args()
    acc: dict = defaultdict(lambda: defaultdict(list))
    steps_logged: set = set()
    for cdir in sorted((a.train_run / "cells").iterdir()):
        case = cdir.name[-3:]
        for line in (cdir / "steps.jsonl").read_text().splitlines():
            r = json.loads(line)
            d = r.get("diagnostics")
            if not d:
                continue
            s = r["step"]
            steps_logged.add(s)
            acc[case][f"gap@{s}"].append(d["mean_gap_8_9"])
            acc[case][f"pi_out@{s}"].append(d["mean_pi_mass_outside_top8"])
            for k, v in d["regularizer_all"].items():
                acc[case][f"R_{k}@{s}"].append(v)
            for k, v in r.get("lam", {}).items():
                acc[case][f"lam_{k}@{s}"].append(v)
    out = {c: {k: {"mean": sum(v) / len(v), "n": len(v), "min": min(v), "max": max(v)} for k, v in sorted(d.items())} for c, d in sorted(acc.items())}
    print(json.dumps({"steps_with_diagnostics": sorted(steps_logged), "cases": out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
