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

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256

RECORD = "inputs/record.json"
STUDENT_FILE = "inputs/student_plain.pt"  # the converted student Part Q's step-1 equivalence test passed on (listed in Part Q's plan reuse hashes)
Q_PLAN = "studies/p10is2/freeze/partq_plan.json"  # Part Q's freeze: the hashes of its frozen files
FORWARD_CODE = ("studies/p10s2/model.py", "studies/p10s2/equivalence.py", "studies/p10s2/tokenization.py", "uv.lock")


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


def forward_code_identity(repo: Path) -> dict[str, Any]:
    """The forward code the student runs on equals Part Q's freeze: ``model.py``, ``equivalence.py``, ``tokenization.py`` and ``uv.lock`` against the hashes in ``freeze/partq_plan.json``."""
    plan = repo / Q_PLAN
    if not plan.is_file():
        return {"checked": False, "ok": None, "reason": f"{Q_PLAN} is not in this tree"}
    frozen = json.loads(plan.read_text())["frozen_files"]
    files = {rel: {"frozen": frozen.get(rel), "now": file_sha256(repo / rel) if (repo / rel).is_file() else None} for rel in FORWARD_CODE}
    differing = sorted(rel for rel, h in files.items() if h["frozen"] is None or h["frozen"] != h["now"])
    return {"checked": True, "ok": not differing, "differing": differing, "files": files}


def student_weights_identity(door: Any, student: Any) -> dict[str, Any]:
    """The student the registered path trains on is bit-identical, tensor by tensor, to the converted student of Part Q's step 1 (``inputs/student_plain.pt``, read through the checked door, hash-verified): the same
    parameter names, the same shapes, ``torch.equal`` on every tensor."""
    if door is None or STUDENT_FILE not in door.files:
        return {"checked": False, "ok": None, "reason": f"{STUDENT_FILE} is not listed by the door"}
    plain = torch.load(door.verify(STUDENT_FILE), weights_only=True, map_location="cpu")["state"]
    own = dict(student.named_parameters())
    names_equal = set(own) == set(plain)
    differing = sorted(n for n in set(own) & set(plain) if own[n].shape != plain[n].shape or not torch.equal(own[n].detach().cpu(), plain[n].to(own[n].dtype)))
    return {"checked": True, "ok": bool(names_equal and not differing), "tensors": len(own), "names_equal": names_equal, "differing": differing[:10], "n_differing": len(differing)}


def student_identity(door: Any, student: Any, repo: Path) -> dict[str, Any] | None:
    """Supporting evidence for G8 NOT RUN (ruling 44, option (a)), a field of its own and never G8 passing: weights and forward code of the tested student. ``ok`` is False if anything checked differs, None if nothing could be
    checked (no door: a unit-test fixture), True otherwise. None is returned without a door."""
    if door is None:
        return None
    weights, code = student_weights_identity(door, student), forward_code_identity(repo)
    parts = [x["ok"] for x in (weights, code) if x["ok"] is not None]
    return {"ok": (all(parts) if parts else None), "weights": weights, "forward_code": code}


def not_run(q_record: Mapping[str, Any] | None, identity: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The G8 record when the bundle holds no stored reference logits: NOT RUN, never a pass. The coded identity evidence is its own field; if it FAILS, G8 is a failure (a student that is not the tested student has no
    equivalence evidence at all)."""
    failed = identity is not None and identity.get("ok") is False
    return {
        "passed": False if failed else None,
        "identity_failed": True if failed else None,
        "student_identity_supporting_evidence": identity,
        "not_run": True,
        "skipped": "G8 NOT RUN: no stored reference logits or greedy sequences in the bundle, so half (2) of ADR-0022 section 12.3's definition cannot be tested; the lead rules",
        "half_1_part_q_step_1_record": part_one(q_record),
        "half_2_stored_reference_logits": "absent from the bundle (Part Q kept the verdicts, not the reference arrays)",
    }
