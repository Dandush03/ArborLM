# ruff: noqa: E501
"""Part T gates G1, G2, G4, G5, G6, G7, G8, G9 (ADR-0025 section 7.3; definitions and tolerances as ADR-0022 section 12.3). A failed gate on study-produced data is ENGINEERING-FAILURE.

G1 partitions and zero R-exact hits (P10-S2's ``gate_g1`` over this study's streams); G2 repeat-scoring identity; G4 determinism on CPU (the same cell twice), snapshot round trip, gradient reach (frozen rows,
the frozen first adapter and the student receive no gradient) and MPS against CPU on 20 updates (skipped where MPS is not the device, printed as such); G5 route "none" bit-identical to the student and gate
isolation of appended rows; G6 addresses and routes take the prompt only; G7 frozen bytes; G8 student equivalence; G9 seeds. Each returns ``{"passed": bool | None, ...}``; None is skipped, never passed.
"""

import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from studies.p10s2 import equivalence
from studies.p10s2 import train as p10train
from studies.p10s2.data import gate_g1
from studies.p10s2.evaluate import general_by_construction
from studies.p10s2.memory import MemoryArm
from studies.p10s2.model import tensor_sha
from studies.p10s2.train import reads_of

from . import engine, scoring
from .common import core, gates

TOL_REPEAT = 0.0


def g1(world: engine.WorldT, extra_eval_refs: Sequence[str] = ()) -> dict[str, Any]:
    from studies.p10s2.data import Streams as S2Streams

    streams = [S2Streams(s.t, s.gold, 0, {}, 0) for s in world.streams]
    res = gate_g1(world.partition, streams, {c: [x.target for s in world.streams for x in s.t[c]] for c in core.TASKS}, set(extra_eval_refs) or None)
    return {"passed": bool(res.get("ok", res.get("passed"))), "detail": res}


def g2(world: engine.WorldT, arm: Any) -> dict[str, Any]:
    """Repeat-scoring identity: the same snapshot scored twice gives bit-identical panel scores."""
    a, b = scoring.panel_means(world, arm), scoring.panel_means(world, arm)
    return {"passed": a == b, "first": a, "second": b}


def g4_determinism(world: engine.WorldT, spec: engine.CellSpec, updates: int = 20) -> dict[str, Any]:
    """The same cell trained twice from its seeds on CPU gives the same arm hash; the snapshot round trip returns the same hash; every trainable parameter has a gradient and no student parameter has one."""
    arm1, rows, opts = engine.build_cell_arm(world, spec, None)
    arm2, _, _ = engine.build_cell_arm(world, spec, None)
    dev, world.device = world.device, torch.device("cpu")
    try:
        r1 = engine.train_cell(world, spec, arm1, rows, opts, updates)
        r2 = engine.train_cell(world, spec, arm2, rows, opts, updates)
    finally:
        world.device = dev
    same = r1["status"] == r2["status"] == "COMPLETE" and arm1.state_hash() == arm2.state_hash()
    arm3, rows3, opts3 = engine.build_cell_arm(world, spec, None)
    reach = p10train.gradient_reach(world.student, arm3, rows3[: world.batch], world.marker_index)
    ok_reach = reach["arm_with_gradient"] == reach["arm_parameters"] and reach["student_with_gradient"] == 0
    return {"passed": bool(same and ok_reach), "deterministic": same, "gradient_reach": reach}


def g4_round_trip(world: engine.WorldT, arm: Any, directory: Path, name: str) -> dict[str, Any]:
    m = engine.save_t(arm, directory, name)
    again = engine.load_t(world, 0, directory, name)
    return {"passed": again.state_hash() == arm.state_hash() == m["arm_hash"]}


def g4_mps(world: engine.WorldT, spec: engine.CellSpec, updates: int = 20) -> dict[str, Any]:
    """MPS against CPU on the same 20 updates: losses within 1e-3 and parameters within a relative norm of 1e-4 (tolerances of the frozen config). Skipped (None) unless the world's device is MPS."""
    if world.device.type != "mps":
        return {"passed": None, "skipped": "the training device is not MPS"}
    out = {}
    losses = {}
    params = {}
    for name, dev in (("cpu", torch.device("cpu")), ("mps", world.device)):
        arm, rows, opts = engine.build_cell_arm(world, spec, None)
        keep, world.device = world.device, dev
        try:
            rec = engine.train_cell(world, spec, arm, rows, opts, updates)
        finally:
            world.device = keep
        losses[name], params[name] = rec, [p.detach().cpu().clone() for p in arm.trainable()]
    del out
    agree = p10train.update_agreement([losses["cpu"]["first_loss"], losses["cpu"]["last_loss"]], [losses["mps"]["first_loss"], losses["mps"]["last_loss"]], params["cpu"], params["mps"])
    return {"passed": bool(agree["ok"]), "detail": agree}


def g5(world: engine.WorldT, m_append: MemoryArm) -> dict[str, Any]:
    """Route "none" is bit-identical to the student (``general_by_construction``), and appended rows are isolated by their gate: with the gate at its initial 0, the values of the appended stage do not enter
    the read (the read is unchanged when they are replaced)."""
    ident = general_by_construction(world.ctx, m_append)["bit_identical_to_student"]
    store = m_append.store.clone()
    k = store.stages - 1
    q = torch.nn.functional.normalize(torch.randn(5, 16, generator=torch.Generator().manual_seed(934900)), dim=-1)
    store.gates[k].data.zero_()
    before = store.read(q)
    store.values[k].data.add_(7.0)
    after = store.read(q)
    return {"passed": bool(ident and torch.equal(before, after)), "none_route_bit_identical": ident, "appended_values_isolated_by_gate": bool(torch.equal(before, after))}


def g6(world: engine.WorldT, count: int = 50) -> dict[str, Any]:
    """Addresses and routes take the prompt only: the reads of a training row equal the reads of its prompt (a target never contributes a read)."""
    bad = 0
    n = 0
    for c in core.TASKS:
        for x in world.streams[0].t[c][:count]:
            tr, pr = world.bank.train(c, x), world.bank.prompt(c, x.en)
            n += 1
            bad += int(reads_of(tr, [c], world.marker_index) != reads_of(pr, [c], world.marker_index) or tuple(tr.ids[: tr.prompt_len]) != tuple(pr.prompt_ids))
    return {"passed": bad == 0, "checked": n, "mismatches": bad}


def g7(before: Mapping[str, str], after_arm: Any, student_before: str, student: Any) -> dict[str, Any]:
    """Frozen bytes: the frozen rows (or first adapter) recorded before training equal those after, and the student's parameters are unchanged."""
    s_now = "|".join(tensor_sha(p) for p in student.parameters())
    ok = engine.frozen_hashes(after_arm) == dict(before) and s_now == student_before
    return {"passed": bool(ok), "frozen_parts": sorted(before)}


def student_hash(student: Any) -> str:
    return "|".join(tensor_sha(p) for p in student.parameters())


def g8(world: engine.WorldT, records: Mapping[str, Any] | None) -> dict[str, Any]:
    if not records:
        return {"passed": None, "skipped": "no equivalence record in the bundle (synthetic stand-in)"}
    res = equivalence.verify_all(world.student, dict(records))
    return {"passed": bool(res["ok"]), "detail": {k: v["ok"] for k, v in res["layers"].items()}}


def g9(cfg: Mapping[str, Any], root: Path | None = None) -> dict[str, Any]:
    r = gates.seed_gate("T", cfg, root=root)
    return {"passed": r["passed"], "problems": r["problems"], "checker": {k: v for k, v in r["checker"].items() if k != "problems_naming_this_study"}}


def run_gates(world: engine.WorldT, cfg: Mapping[str, Any], snap_dir: Path, *, equivalence_records: Mapping[str, Any] | None = None, root: Path | None = None, run_checker: bool = True) -> dict[str, Any]:
    """Every gate on the world's data (the registered gates stage). Trains the small cells the gates need on CPU from their seeds; nothing registered is read."""
    spec = engine.CellSpec("M1", "AB", 0)
    arm, rows, opts = engine.build_cell_arm(world, spec, None)
    sh = student_hash(world.student)
    before = engine.frozen_hashes(arm)
    keep, world.device = world.device, torch.device("cpu")
    try:
        engine.train_cell(world, spec, arm, rows, opts, 2)
        ma, rows2, opts2 = engine.build_cell_arm(world, engine.CellSpec("M-append", "AB", 0), arm)
        f_before = engine.frozen_hashes(ma)
        engine.train_cell(world, engine.CellSpec("M-append", "AB", 0), ma, rows2, opts2, 2)
    finally:
        world.device = keep
    out = {
        "G1": g1(world), "G2": g2(world, ma), "G4": {**g4_determinism(world, spec, 4), "round_trip": g4_round_trip(world, copy.deepcopy(ma), snap_dir, "gate/M-append")}, "G4-MPS": g4_mps(world, spec), "G5": g5(world, ma), "G6": g6(world),
        "G7": g7(f_before, ma, sh, world.student), "G8": g8(world, equivalence_records), "G9": g9(cfg, root) if run_checker else {"passed": None, "skipped": "checker not run"},
    }  # fmt: skip
    del before
    failed = [k for k, v in out.items() if v["passed"] is False]
    return {"gates": out, "failed": failed, "status": "ENGINEERING-FAILURE" if failed else "PASSED", "skipped": [k for k, v in out.items() if v["passed"] is None]}
