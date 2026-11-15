# ruff: noqa: E501
"""P10S0 arm-selection script and record (ADR-0020 sections 3.2 to 3.5; part of the freeze; recomputed by the auditor, gate G10).

Run from the repository root: ``uv run --locked python -m studies.p10s0.arm_selection --out <path>``. It reads P9-II's COMMITTED records only (never an S0 record):
``results/p9ii-run-2026-11-15/results.json`` and ``OUTCOME.md``, and ``results/p9ii-calibration-2026-11-15/calibration.json``; it records their sha256. It does not read any accuracy, per-draw
table or Stage 3 label for the mapping (section 3.2: "Nothing else is read"). The one place it reads draw-level data is part (d), the arms that can still be the candidate, whose rule is
section 3.5's: an arm is excluded if at 4,096 its P9-II failed draws already exceed two, or P9-II printed LM CAPABILITY REDUCED for it there.

The record has four parts (section 3.4):
  (a) the mapping's result (computed twice: by the steps of section 3.2 and by the table of section 3.3; they must agree) with the hashes of the P9-II records read;
  (b) the human lead's override (copied from the ADR as constants, not computed): words, date, printed string, F1 annotation, fixed sentence;
  (c) the calibrated values used: lambda = 1.0, U_pre = 2,048, mu = 1.0 (k_0/N = 0.125 is recorded and not used: A4 is not in S0);
  (d) the arms that can still be the candidate.
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

from arborlm.io import file_sha256, read_json, write_json

from . import core

# P9-II's outcome strings (studies.p9ii.classes) and statuses
ADDRESSING_RELIABLE = "ADDRESSING-RELIABLE"
ANSWER_ONLY_RELIABLE = "ANSWER-ONLY RELIABLE"
RELIABLE_4096_ONLY = "ADDRESSING-RELIABLE AT 4,096 ONLY"
RELIABLE_4096_STATUS_PREFIX = "ADDRESSING-RELIABLE AT 4,096; 16,384"
NOT_RUN_OUTCOMES = ("ENGINEERING_FAIL", "INCOMPLETE", "NOT_INTERPRETED", "NOT_INTERPRETED (INCOMPLETE)")
LABEL_FREE_C4 = ("A4", "A5-C", "A5-D")
STATUS_COMPLETE = "COMPLETE"
STEP_ONE, STEP_TWO, STEP_THREE, STEP_FOUR = "§3.2 item 1", "§3.2 item 2", "§3.2 item 3", "§3.2 item 4"

# The rows of ADR-0020 section 3.3 (the table the auditor re-enumerates), numbered in the table's order.
TABLE_ROWS: dict[int, str] = {
    1: "ADDRESSING-RELIABLE, carried arm A5-C, A5-D or A4",
    2: "ADDRESSING-RELIABLE, carried arm A2 or A1",
    3: "ADDRESSING-RELIABLE, carried arm A0 (RELIABLE at 16,384, not at 4,096)",
    4: "ANSWER-ONLY RELIABLE, Stage 2 COMPLETE, carried arm A0",
    5: "ANSWER-ONLY RELIABLE, Stage 2 COMPLETE, A0 not RELIABLE or LM-flagged at 16,384, carried arm A5-C, A5-D or A4",
    6: "ANSWER-ONLY RELIABLE, Stage 2 COMPLETE, carried arm A2 or A1, or none",
    7: "ANSWER-ONLY RELIABLE, Stage 2 not COMPLETE",
    8: "ADDRESSING-RELIABLE AT 4,096 ONLY",
    9: "ADDRESSING-RELIABLE AT 4,096; 16,384 <status>",
    10: "ADDRESSING-UNRELIABLE, ADDRESSING-FAILS, INCONCLUSIVE",
    11: "ENGINEERING_FAIL / INCOMPLETE / NOT_INTERPRETED",
}


class P9IIFacts(NamedTuple):
    """The only P9-II facts the mapping reads (section 3.2): whether an audited calibration record exists, the outcome (ADR-0019 section 8.6), Stage 2's status and the carried arm."""

    calibration_exists: bool
    outcome: str
    stage2_status: str
    carried: str | None


class Mapping_(NamedTuple):
    c4: str | None
    printed: str
    step: str
    not_started: bool
    reason: str


def mapping_by_steps(f: P9IIFacts) -> Mapping_:
    """Section 3.2, in the order written: 1 calibration, 2 outcome row, 3 Stage 2's status, 4 the carried interface."""
    if not f.calibration_exists:
        return Mapping_(None, core.NOT_STARTED, STEP_ONE, True, "no audited P9-II calibration record")
    if f.outcome in NOT_RUN_OUTCOMES:
        return Mapping_(None, core.MAPPING_NONE_STATUS_TEMPLATE.format(status=f.outcome), STEP_TWO, False, f"P9-II outcome {f.outcome}")
    if f.stage2_status != STATUS_COMPLETE:
        return Mapping_(None, f"FOURTH ARM: NONE — P9-II STAGE 2 {f.stage2_status}", STEP_THREE, False, f"Stage 2 {f.stage2_status}")
    if f.carried in LABEL_FREE_C4:
        return Mapping_(f.carried, f"FOURTH ARM: {f.carried} — P9-II CARRIED {f.carried}", STEP_FOUR, False, "carried label-free arm")
    if f.carried in ("A0", "A2", "A1"):
        return Mapping_(None, core.MAPPING_NONE_TEMPLATE.format(arm=f.carried), STEP_FOUR, False, f"carried {f.carried}, already in S0")
    return Mapping_(None, "FOURTH ARM: NONE — P9-II CARRIED NONE", STEP_FOUR, False, "no arm carried")


def table_row(f: P9IIFacts) -> int:
    """The row of section 3.3 that applies (the table is the second, independent reading of the same rule)."""
    if f.outcome in NOT_RUN_OUTCOMES:
        return 11
    if f.outcome == ADDRESSING_RELIABLE:
        return 1 if f.carried in LABEL_FREE_C4 else 2 if f.carried in ("A2", "A1") else 3
    if f.outcome == ANSWER_ONLY_RELIABLE:
        if f.stage2_status != STATUS_COMPLETE:
            return 7
        return 4 if f.carried == "A0" else 5 if f.carried in LABEL_FREE_C4 else 6
    if f.outcome == RELIABLE_4096_ONLY:
        return 8
    if f.outcome.startswith(RELIABLE_4096_STATUS_PREFIX):
        return 9
    return 10


def mapping_by_table(f: P9IIFacts) -> str | None:
    """The fourth arm the table of section 3.3 gives (None = none)."""
    if not f.calibration_exists:
        return None
    return f.carried if table_row(f) in (1, 5) and f.carried in LABEL_FREE_C4 else None


def evaluate_mapping(f: P9IIFacts) -> dict[str, Any]:
    """Part (a): the mapping's result by the steps and by the table, and whether they agree."""
    steps = mapping_by_steps(f)
    row = table_row(f)
    return {
        "facts": f._asdict(), "c4": steps.c4, "printed": steps.printed, "decided_at": steps.step, "not_started": steps.not_started, "reason": steps.reason,
        "table_row": row, "table_row_text": TABLE_ROWS[row], "table_c4": mapping_by_table(f), "steps_equal_table": steps.c4 == mapping_by_table(f),
    }  # fmt: skip


# --- reading P9-II's records -------------------------------------------------------------------------------------------------------
def p9ii_facts(results: Mapping[str, Any], calibration: Mapping[str, Any] | None) -> P9IIFacts:
    res = results["result"]
    return P9IIFacts(calibration is not None, str(res["outcome"]["outcome"]), str((res.get("stage2") or {}).get("status", "NOT RUN")), (res.get("carried_forward") or {}).get("arm"))


def _classes_at(stage: Mapping[str, Any] | None, arm: str) -> dict[str, Any] | None:
    if stage is None or arm not in (stage.get("arms") or {}):
        return None
    a = stage["arms"][arm]
    counts = a["counts"]
    draws = {k: int(v) for k, v in a["draw_sensitivity"]["draw_counts"].items()}
    evaluated = sum(draws.values())
    failed = sum(v for k, v in draws.items() if k != "2/2")
    return {
        "class": a["class"], "base_class": a["base_class"], "lm_reduced": "LM CAPABILITY REDUCED" in str(a["class"]), "evaluated_cells": int(counts["evaluated"]), "successes": int(counts["successes"]),
        "evaluated_draws": evaluated, "failed_draws": failed, "draw_counts": draws, "negative_control_failed": bool(stage.get("negative_control_failed", False)),
    }  # fmt: skip


def p9ii_classes(results: Mapping[str, Any], interpreted: bool) -> dict[str, dict[str, Any]]:
    """For each arm of S0's set and each size, P9-II's class record for consistency (section 8.5): at 4,096 the Stage 1 class; at 16,384 the Stage 2 class at the 4U readout, read only
    when P9-II's outcome is interpreted, Stage 2 is COMPLETE and the arm has a Stage 2 class. ``available`` False says why not."""
    res = results["result"]
    stage2 = res.get("stage2") or {}
    out: dict[str, dict[str, Any]] = {}
    for arm in core.CORE_LEARNED_ARMS:
        s1 = _classes_at(res.get("stage1"), arm) if interpreted else None
        s2_ok = interpreted and stage2.get("status") == STATUS_COMPLETE
        s2 = _classes_at(stage2, arm) if s2_ok else None
        out[arm] = {
            "4096": {"available": s1 is not None, **(s1 or {"reason": "P9-II not interpreted" if not interpreted else "no Stage 1 class"})},
            "16384": {"available": s2 is not None, **(s2 or {"reason": ("P9-II not interpreted" if not interpreted else f"Stage 2 {stage2.get('status', 'NOT RUN')}" if not s2_ok else "no Stage 2 class at the 4U readout (the arm did not advance)")})},
        }
    return out


def candidate_arms(classes: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    """Section 3.5: the arms of S0's set that can still be the candidate, from section 8.5 (b) and P9-II's records. An arm is excluded if at 4,096 its P9-II failed draws exceed two
    (``core.CONSISTENCY_MAX_FAILED_DRAWS``), or P9-II printed LM CAPABILITY REDUCED for it there. An arm with no 4,096 class (P9-II not interpreted) is not excluded (SINGLE-STUDY EVIDENCE)."""
    arms: list[str] = []
    excluded: dict[str, str] = {}
    for arm in core.PREFERENCE_ORDER:
        c = classes[arm]["4096"]
        if c["available"] and c["lm_reduced"]:
            excluded[arm] = "P9-II printed LM CAPABILITY REDUCED at 4,096"
        elif c["available"] and c["failed_draws"] > core.CONSISTENCY_MAX_FAILED_DRAWS:
            excluded[arm] = f"P9-II failed draws at 4,096 already exceed two ({c['failed_draws']} of {c['evaluated_draws']})"
        else:
            arms.append(arm)
    return {"arms": arms, "excluded": excluded}


def override_part() -> dict[str, Any]:
    """Part (b): copied from the ADR, never computed."""
    return {
        "human_lead_words": core.HUMAN_LEAD_WORDS, "date": core.OVERRIDE_DATE, "c4": "A5-D", "mu": core.CALIBRATED["mu"], "printed_string": core.FOURTH_ARM_STRING,
        "f1_annotation": core.F1_ANNOTATION, "fixed_sentence": core.PROVENANCE_SENTENCE, "source": "ADR-0020 section 3.4 and section 18",
        "not_an_acceptance_of_the_p9ii_outcome": True,
    }  # fmt: skip


def build_record(repo: Path, *, commit_of: bool = True) -> dict[str, Any]:
    """The arm-selection record from P9-II's committed records under ``repo``."""
    paths = {k: repo / v for k, v in core.P9II_RECORDS.items()}
    results = read_json(paths["results"])
    calibration = read_json(paths["calibration"]) if paths["calibration"].is_file() else None
    facts = p9ii_facts(results, calibration)
    mapping = evaluate_mapping(facts)
    interpreted = facts.outcome not in NOT_RUN_OUTCOMES
    classes = p9ii_classes(results, interpreted)
    hyper = (calibration or {}).get("hyper", {})
    calibrated_ok = bool(calibration) and float(hyper["lambda"]) == core.CALIBRATED["lambda"] and float(hyper["u_pre"]) == core.CALIBRATED["u_pre"] and float(hyper["mu"]) == core.CALIBRATED["mu"]
    inputs: dict[str, Any] = {}
    for key, path in paths.items():
        entry: dict[str, Any] = {"path": core.P9II_RECORDS[key], "sha256": file_sha256(path) if path.is_file() else None}
        if commit_of:
            entry["last_commit"] = _git_last_commit(repo, core.P9II_RECORDS[key])
        inputs[key] = entry
    return {
        **core.envelope("arm_selection"),
        "p9ii_inputs": inputs,
        "mapping": mapping,
        "fourth_arm_printed": core.FOURTH_ARM_STRING,
        "arm_set_conflict": mapping["c4"] not in (None, "A5-D"),
        "mapping_printed": mapping["printed"],
        "override": override_part(),
        "calibrated": {
            "lambda": core.CALIBRATED["lambda"], "u_pre": core.CALIBRATED["u_pre"], "mu": core.CALIBRATED["mu"], "k0_fraction": core.CALIBRATED["k0_fraction"], "k0_fraction_used": False,
            "p9ii_record_hyper": hyper, "equals_p9ii_record": calibrated_ok,
        },
        "arm_set": list(core.CORE_LEARNED_ARMS), "references": list(core.REFERENCE_ARMS),
        "p9ii_classes": classes,
        "p9ii_negative_control": {"4096": bool((results["result"].get("stage1") or {}).get("negative_control_failed", False)), "16384": bool((results["result"].get("stage2") or {}).get("negative_control_failed", False))},
        "candidates": candidate_arms(classes),
        "note": "recomputed by the auditor from ADR-0020 sections 3.2, 3.3 and 3.5 (gate G10); not an acceptance of the P9-II outcome",
    }  # fmt: skip


def _git_last_commit(repo: Path, relative: str) -> str | None:
    out = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%H", "--", relative], capture_output=True, check=False)  # noqa: S603, S607
    text = out.stdout.decode().strip()
    return text or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m studies.p10s0.arm_selection", description=__doc__)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--out", default=None, help="write the record here (never over an existing file)")
    args = parser.parse_args(argv)
    repo = Path(args.repo) if args.repo else core.repo_root()
    record = build_record(repo)
    text = json.dumps(core.jsonable(record), indent=1, sort_keys=True)
    if args.out:
        out = Path(args.out)
        if out.exists():
            print(f"refused: {out} exists", file=sys.stderr)
            return 2
        write_json(out, core.jsonable(record))
        print(json.dumps({"written": str(out), "sha256": file_sha256(out), "c4": record["mapping"]["c4"], "printed": record["mapping_printed"], "candidates": record["candidates"]["arms"]}))
    else:
        print(text)
    return 0 if record["mapping"]["steps_equal_table"] else 1


if __name__ == "__main__":
    sys.exit(main())
