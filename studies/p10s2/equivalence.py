# ruff: noqa: E501
"""Student equivalence (ADR-0022 section 14.2 steps 3, 4 (d) and (e); gate G8).

Data-generation side: ``build_record`` runs the study's student and a *reference implementation* on a fixed 256-token text, with a fixed vector added at the output of block L, and on greedy prompts, and
stores the reference logits and sequences. Registered side: ``verify_record`` (gate G8) reproduces them with the study's student within the tolerance. The reference is any object with the interface of
``ReferenceModel`` (the real one wraps the Hugging Face ``LlamaForCausalLM``; the tests use an independently written stand-in).

Tolerance and rules (from the ADR; *(lead's choice)* values in the config): maximum absolute logit difference <= 1e-3 and identical top-1 token at every position (step 3); logits at the injection point
within 1e-3 against the reference with a forward hook at the same place, which pins the off-by-one between "output of block L" and ``hidden_states[L + 1]`` (step 4 (d)); greedy decoding with a key-value
cache identical to full recomputation and to the reference ``generate`` on 100 prompts (step 4 (e)).
"""

from collections.abc import Sequence
from typing import Any, Protocol

import torch

from . import core
from .model import Student


class ReferenceModel(Protocol):
    def logits(self, ids: torch.Tensor) -> torch.Tensor: ...
    def logits_with_injection(self, ids: torch.Tensor, layer: int, vec: torch.Tensor) -> torch.Tensor: ...
    def generate(self, ids: torch.Tensor, max_new: int) -> list[int]: ...


def tolerance() -> float:
    return float(core.CFG["gates"]["student_equivalence_tolerance"])


def compare_logits(a: torch.Tensor, b: torch.Tensor) -> dict[str, Any]:
    diff = float((a - b).abs().max())
    same_top1 = bool(torch.equal(a.argmax(-1), b.argmax(-1)))
    return {"max_abs_difference": diff, "identical_top1": same_top1, "ok": diff <= tolerance() and same_top1}


@torch.no_grad()
def build_record(student: Student, reference: ReferenceModel, ids: torch.Tensor, vec: torch.Tensor, layer: int, prompts: Sequence[Sequence[int]], max_new: int) -> dict[str, Any]:
    """The record the data-generation step writes: reference logits (plain text), injection-point logits, greedy sequences, and the study student's comparison at that time."""
    ref = reference.logits(ids)
    ref_inj = reference.logits_with_injection(ids, layer, vec)
    seqs = [reference.generate(torch.tensor([list(p)]), max_new) for p in prompts]
    add = torch.zeros(ids.shape[0], ids.shape[1], vec.shape[-1])
    add[:] = vec
    student.read_layer = layer
    mine_inj = student(ids, add=add)
    return {
        "rms_norm_eps": student.cfg.rms_norm_eps, "ids": ids.tolist(), "layer": layer, "vec": vec.tolist(), "reference_logits": ref.clone(), "reference_injection_logits": ref_inj.clone(),
        "prompts": [list(p) for p in prompts], "reference_greedy": seqs, "max_new": max_new,
        "at_creation": {"logits": compare_logits(student(ids), ref), "injection": compare_logits(mine_inj, ref_inj)},
    }  # fmt: skip


@torch.no_grad()
def verify_record(student: Student, rec: dict[str, Any]) -> dict[str, Any]:
    """Gate G8: the registered path's student reproduces the stored reference logits, the stored injection-point logits and the stored greedy sequences within the tolerance."""
    if float(rec["rms_norm_eps"]) != student.cfg.rms_norm_eps:
        return {"ok": False, "reason": f"rms_norm_eps {student.cfg.rms_norm_eps} differs from the recorded {rec['rms_norm_eps']}", "tolerance": tolerance()}
    ids = torch.tensor(rec["ids"])
    layer = int(rec["layer"])
    vec = torch.tensor(rec["vec"])
    logits = compare_logits(student(ids), torch.as_tensor(rec["reference_logits"], dtype=torch.float32))
    add = torch.zeros(ids.shape[0], ids.shape[1], vec.shape[-1])
    add[:] = vec
    student.read_layer = layer
    inj = compare_logits(student(ids, add=add), torch.as_tensor(rec["reference_injection_logits"], dtype=torch.float32))
    greedy_ok = True
    cache_ok = True
    for p, ref_seq in zip(rec["prompts"], rec["reference_greedy"], strict=True):
        pt = torch.tensor([p])
        cached = student.greedy(pt, add=None, adapter=None, max_new=int(rec["max_new"]), stop_bytes=None, use_cache=True)
        full = student.greedy(pt, add=None, adapter=None, max_new=int(rec["max_new"]), stop_bytes=None, use_cache=False)
        cache_ok = cache_ok and cached == full
        greedy_ok = greedy_ok and cached == list(ref_seq)
    ok = bool(logits["ok"] and inj["ok"] and greedy_ok and cache_ok)
    return {"ok": ok, "logits": logits, "injection": inj, "greedy_matches_reference": greedy_ok, "cache_matches_recomputation": cache_ok, "tolerance": tolerance()}


def verify_all(student: Student, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Gate G8 over every read layer the data-generation step recorded (the layers calibration may choose from, 4 and 12: audit minor 8): each record is verified on its own; the gate passes only if
    every layer passes and at least one record is given."""
    per = {layer: verify_record(student, rec) for layer, rec in sorted(records.items())}
    return {"ok": bool(per) and all(bool(v["ok"]) for v in per.values()), "layers": per, "tolerance": tolerance()}
