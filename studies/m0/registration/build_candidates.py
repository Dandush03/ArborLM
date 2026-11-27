"""ADR-0033 addendum 1, section 4A stage 2: the candidate list, computed by code.

The candidate list is the survivor-list lineages whose `all_conditions` is PASS in the hashed
stage-2 record, less the lineages the fresh run of stage 1S dropped. Nothing is judged here.

    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python build_candidates.py \
        --survivors studies/m0/manifests/survivor_list_of_record.json \
        --stage2 studies/m0/manifests/stage2_conditions.json \
        --dropped docs/reviews/m0-fresh-run-2026-11-26/run/pooled/dropped.json \
        --out candidate_list.json

Stops (exit 2, nothing written) if a dropped lineage is not a PASS survivor, a survivor has no
stage-2 entry, an evaluation field disagrees, or the counts differ from R1 6, R2 16, M1 24, C1 21
(the counts are a check on the reading, not a target).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EVALS = ("R1", "R2", "M1", "C1")
EXPECTED = {"R1": 6, "R2": 16, "M1": 24, "C1": 21}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(survivors: dict, stage2: dict, dropped: list) -> dict:
    """The candidate list as a plain dict (deterministic order). Raises ValueError on a stop."""
    surv = survivors["evaluations"]
    if sorted(surv) != sorted(EVALS):
        raise ValueError(f"survivor list evaluations are {sorted(surv)}")
    drop_ids = [d["lineage"] for d in dropped]
    if len(drop_ids) != len(set(drop_ids)):
        raise ValueError("a lineage is dropped twice")
    owner = {x: e for e in EVALS for x in surv[e]}
    if len(owner) != sum(len(surv[e]) for e in EVALS):
        raise ValueError("a lineage is on the survivor list twice")
    for d in dropped:
        x = d["lineage"]
        if x not in owner:
            raise ValueError(f"dropped lineage {x!r} is not on the survivor list")
        if owner[x] != d["evaluation"]:
            raise ValueError(
                f"dropped lineage {x!r}: evaluation {d['evaluation']!r} != {owner[x]!r}"
            )
    candidates: dict[str, list[str]] = {}
    not_pass: list[str] = []
    for e in EVALS:
        keep = []
        for x in sorted(surv[e]):
            if x not in stage2:
                raise ValueError(f"survivor {x!r} has no stage-2 entry")
            if stage2[x]["evaluation"] != e:
                raise ValueError(f"survivor {x!r}: stage-2 evaluation {stage2[x]['evaluation']!r}")
            if stage2[x]["all_conditions"] != "PASS":
                not_pass.append(x)
            elif x not in drop_ids:
                keep.append(x)
        candidates[e] = keep
    counts = {e: len(candidates[e]) for e in EVALS}
    if counts != EXPECTED:
        raise ValueError(f"counts {counts} differ from the expected {EXPECTED}")
    return {
        "candidates": candidates,
        "counts": counts,
        "dropped_by_fresh_run": sorted(drop_ids),
        "survivors_not_pass_in_stage2": sorted(not_pass),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--survivors", required=True, type=Path)
    ap.add_argument("--stage2", required=True, type=Path)
    ap.add_argument("--dropped", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        print("stop: the output exists", file=sys.stderr)
        return 3
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    try:
        result = build(load(args.survivors), load(args.stage2), load(args.dropped))
    except ValueError as err:
        print(f"stop: {err}", file=sys.stderr)
        return 2
    result["input_sha256"] = {
        "survivor_list_of_record": sha256_file(args.survivors),
        "stage2_conditions": sha256_file(args.stage2),
        "dropped": sha256_file(args.dropped),
    }
    result["script_sha256"] = sha256_file(Path(__file__))
    args.out.write_bytes(
        (json.dumps(result, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode("ascii")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
