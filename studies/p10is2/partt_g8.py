# ruff: noqa: E501
"""P10-I-S2 Part T, gate G8 on the real Part Q bundle (ruling 44; audit 8, finding 4).

ADR-0022 section 12.3 (carried by ADR-0025 section 7.3) defines G8, student equivalence, in two halves: (1) the
result recorded by the data-generation step (Part Q step 1) is present and within tolerance; (2) the registered
path's student reproduces the STORED reference logits within the same tolerance, including the stored
injection-point logits and the stored greedy sequences.

Part Q recorded only the verdicts of half (1): ``inputs/record.json`` holds, per read layer, the logits and the
injection checks (``ok``, ``max_abs_difference``, ``identical_top1``). The stored reference logits and greedy
sequences that half (2) needs are not in the bundle (``equivalence_layers`` is absent from its ``extra``). So G8 as
defined cannot be run on the real Part Q bundle. It is reported NOT RUN (``passed`` None and ``not_run`` True, never
a pass), with half (1)'s recorded verdicts echoed for the lead's ruling; nothing is recomputed and no threshold is
applied here beyond the ``ok`` flags Part Q recorded under the registered tolerance.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

RECORD = "inputs/record.json"


def q_equivalence_through_door(door: Any) -> Mapping[str, Any] | None:
    """Part Q's step-1 equivalence verdicts (``inputs/record.json``, key ``equivalence``) through the checked door: a file the door does not list gives None (no record); a listed file whose bytes differ raises
    the door's PAUSED - IDENTITY refusal, as for every Part Q file."""
    if door is None or RECORD not in door.files:
        return None
    rec = door.read_json(RECORD).get("equivalence")
    return rec if isinstance(rec, dict) and rec else None


def part_one(q_record: Mapping[str, Any] | None) -> dict[str, Any]:
    """Half (1), echoed and never recomputed: per read layer the recorded ``ok`` flags and figures."""
    if not q_record:
        return {"present": False, "layers": {}, "all_ok": None}
    layers: dict[str, Any] = {}
    for layer, rec in sorted(q_record.items()):
        lg, inj = rec.get("logits", {}), rec.get("injection", {})
        layers[str(layer)] = {
            "logits_ok": lg.get("ok"), "logits_max_abs_difference": lg.get("max_abs_difference"), "logits_identical_top1": lg.get("identical_top1"),
            "injection_ok": inj.get("ok"), "injection_max_abs_difference": inj.get("max_abs_difference"), "injection_identical_top1": inj.get("identical_top1"),
        }  # fmt: skip
    all_ok = all(v["logits_ok"] is True and v["injection_ok"] is True for v in layers.values())
    return {"present": True, "layers": layers, "all_ok": bool(all_ok)}


def not_run(q_record: Mapping[str, Any] | None) -> dict[str, Any]:
    """The G8 record when the bundle holds no stored reference logits: NOT RUN, never a pass."""
    return {
        "passed": None,
        "not_run": True,
        "skipped": "G8 NOT RUN: no stored reference logits or greedy sequences in the bundle, so half (2) of ADR-0022 section 12.3's definition cannot be tested; the lead rules",
        "half_1_part_q_step_1_record": part_one(q_record),
        "half_2_stored_reference_logits": "absent from the bundle (Part Q kept the verdicts, not the reference arrays)",
    }
