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
from .partt_g8 import not_run as g8_not_run
from .partt_mps_step import compare_steps

TOL_REPEAT = 0.0


def with_q_check(partition: Any, q_check_keys: Sequence[str] | None) -> Any:
    """Part Q's bundle holds D_cal, D_con, E_A, E_B, E_C, E_open and Q_fit but NO Q_check (audit R3); P10-S2's ``gate_g1`` indexes it. A copy of the partition with a Q_check panel made of the English keys of the Q_check
    blocks Part Q drew, read through the checked door (ruling 6), is what G1 gets. The identity groups of those items are not recoverable from Part Q's records without recomputing its partition: they carry group -1
    (the gate's group tests skip them), so G1 tests Q_check's disjointness from the training streams by English keys. Without the keys and without a Q_check panel the gate REFUSES: it never passes on a missing panel."""
    import copy as _copy

    from studies.p10s2.data import Item

    if "Q_check" in partition.panels:
        return partition
    if q_check_keys is None:
        raise core.StageRefused("refused: gate G1 needs the Q_check panel, which Part Q's bundle does not hold: pass the Q_check keys read through the checked door")
    p = _copy.copy(partition)
    p.panels = {**partition.panels, "Q_check": [Item(k, k, {}, -1) for k in sorted(set(q_check_keys))]}
    return p


def g1(world: engine.WorldT, extra_eval_refs: Sequence[str] = (), q_check_keys: Sequence[str] | None = None) -> dict[str, Any]:
    from studies.p10s2.data import Streams as S2Streams

    streams = [S2Streams(s.t, s.gold, 0, {}, 0) for s in world.streams]
    res = gate_g1(with_q_check(world.partition, q_check_keys), streams, {c: [x.target for s in world.streams for x in s.t[c]] for c in core.TASKS}, set(extra_eval_refs) or None)
    ok = bool(res.get("ok", res.get("passed")))
    if q_check_keys is not None:  # P10-S2's gate skips group -1: the Q_check items Part T has are known by English key only, so their disjointness from every training stream is tested here by key
        overlap = sorted({x.key for s in world.streams for c in core.TASKS for x in s.t[c]} & set(q_check_keys))
        res = {**res, "q_check_key_overlap": len(overlap)}
        ok = ok and not overlap
    return {"passed": ok, "detail": res}


def g2(world: engine.WorldT, arm: Any) -> dict[str, Any]:
    """Repeat-scoring identity: the same snapshot scored twice gives bit-identical panel scores. In a rehearsal or a calibration it scores D_cal (ruling 1: never an evaluation panel before the registered run)."""
    if world.plan_mode in scoring.EVALUATION_FORBIDDEN_MODES:
        from studies.p10s2.evaluate import score_panel

        a, b = ({c: score_panel(world.ctx, arm, world.d_cal[c]).mean for c in core.TASKS} for _ in range(2))
        return {"passed": a == b, "panel": "D_cal", "repeat_difference": max(abs(a[c] - b[c]) for c in a)}
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


def tensor_names(arm: Any) -> list[str]:
    """Names of the trainable tensors of an arm (``store.keys.0``, ...), by identity; a tensor with no name is ``param<i>``."""
    ids: dict[int, str] = {}
    for attr in ("store", "adapter", "module"):
        m = getattr(arm, attr, None)
        if m is not None and hasattr(m, "named_parameters"):
            ids.update({id(p): f"{attr}.{n}" for n, p in m.named_parameters()})
    return [ids.get(id(p), f"param{i}") for i, p in enumerate(arm.trainable())]


def _train_cell_on(world: engine.WorldT, spec: engine.CellSpec, dev: torch.device, updates: int) -> tuple[dict[str, Any], Any, list[Any], Mapping[str, Any]]:
    arm, rows, opts = engine.build_cell_arm(world, spec, None)
    keep, world.device = world.device, dev
    try:
        rec = engine.train_cell(world, spec, arm, rows, opts, updates, record_losses=updates)
    finally:
        world.device = keep
    return rec, arm, rows, opts


def gradients_along(world: engine.WorldT, spec: engine.CellSpec, rows: Sequence[Any], trajectory: Sequence[Sequence[torch.Tensor]], batches: Sequence[Sequence[int]], dev: torch.device) -> list[list[torch.Tensor]]:
    """The gradient of each update's batch loss on ``dev`` from the parameter values of the CPU run at that update (copied in), before the optimiser step: per update, one float64 CPU tensor per trainable tensor."""
    arm, _r, _o = engine.build_cell_arm(world, spec, None)
    world.student.to(dev)
    arm.to(dev)
    out: list[list[torch.Tensor]] = []
    try:
        for u, values in enumerate(trajectory):
            for p, v in zip(arm.trainable(), values, strict=True):
                p.data.copy_(v.to(dev))
                p.grad = None
            loss = p10train.loss_of(world.student, arm, [rows[i] for i in batches[u]], world.marker_index, dev)
            loss.backward()
            out.append([p.grad.detach().cpu().double().clone() if p.grad is not None else torch.zeros(p.shape, dtype=torch.float64) for p in arm.trainable()])
    finally:
        arm.to(torch.device("cpu"))
        world.student.to(torch.device("cpu"))
    return out


def g4_mps(world: engine.WorldT, spec: engine.CellSpec, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """MPS against CPU (amended by ruling 39, the human lead's decision of 2026-11-20; ADR-0025 addendum ``g4-mps-amendment``).

    GATING: (1) every one of the ``g4_repeat_updates`` (20) per-update losses of the CPU run and the MPS run within ``mps_loss_tolerance`` = 1e-3 (absolute), the same cell (``spec``: M1, replicate 0, order AB) built
    twice from its listed seeds and trained on the same batches; (2) GRADIENT AGREEMENT AT IDENTICAL PARAMETERS: along the CPU run's trajectory, at each update before the optimiser step, the gradient of the same batch's
    loss on CPU and on MPS from the SAME parameter values; for every trainable tensor with ||g_cpu|| > 0, ||g_mps - g_cpu|| / ||g_cpu|| <= ``mps_gradient_relative_tolerance`` = 1e-3; where ||g_cpu|| is exactly 0,
    ||g_mps|| must be exactly 0 (a violation fails the gate and is reported, never adjusted). The largest figure over tensors and updates is recorded with its tensor and update. (3) OPTIMISER STEP (ruling 43, ``partt_mps_step``): identical parameters,
    gradients and AdamW state on CPU and on MPS, one ``clip_grad_norm_`` plus ``AdamW.step`` each (fresh state; copied state; clipping active); the two updates agree relative to the step size within the same registered
    ``mps_gradient_relative_tolerance``, with the exact-zero clause. RECORDED, NOT GATING: the old relative parameter
    difference after the 20 updates per tensor (``mps_parameter_relative_tolerance`` named as superseded) and the MPS-against-MPS repeat. SKIPPED (None) unless the world's device is MPS; a skipped gate is NOT a pass."""
    t = (cfg or core.load_config("T"))["gates"]
    updates = int(t["g4_repeat_updates"])
    if world.device.type != "mps":
        return {"passed": None, "skipped": "the training device is not MPS", "compares": "per-update losses and gradients at identical parameters of one cell, CPU against MPS", "updates": updates}
    traj: list[list[torch.Tensor]] = []

    def capture(opt: Any, args: Any, kwargs: Any) -> None:  # the parameters the batch's gradient was taken at: before the optimiser step
        traj.append([p.detach().cpu().clone() for p in opt.param_groups[0]["params"]])

    from torch.optim.optimizer import register_optimizer_step_pre_hook

    handle = register_optimizer_step_pre_hook(capture)
    try:
        rec_cpu, arm_cpu, rows, opts = _train_cell_on(world, spec, torch.device("cpu"), updates)
    finally:
        handle.remove()
    if rec_cpu["status"] != "COMPLETE":
        return {"passed": False, "error": f"cpu: {rec_cpu['status']} {rec_cpu['error']}", "updates": updates}
    if opts.get("replay") is not None or len(traj) != updates:
        return {"passed": False, "error": "the gate's cell must be a first-stage arm without replay and train every update", "updates": updates}
    runs: dict[str, tuple[list[float], list[torch.Tensor]]] = {"cpu": (rec_cpu["losses_head"], [p.detach().cpu().clone() for p in arm_cpu.trainable()])}
    for name in ("mps", "mps_repeat"):
        rec, arm, _r, _o = _train_cell_on(world, spec, world.device, updates)
        if rec["status"] != "COMPLETE":
            return {"passed": False, "error": f"{name}: {rec['status']} {rec['error']}", "updates": updates}
        runs[name] = (rec["losses_head"], [p.detach().cpu().clone() for p in arm.trainable()])
    batches = p10train.batch_plan(len(rows), updates, world.batch, world.plan(spec.rep).gen(2, "batch order"))
    g_cpu = gradients_along(world, spec, rows, traj, batches, torch.device("cpu"))
    g_mps = gradients_along(world, spec, rows, traj, batches, world.device)
    grad = compare_gradients(g_cpu, g_mps, tensor_names(arm_cpu), t)
    loss = compare_runs(runs["cpu"], runs["mps"], t)
    step = compare_steps(traj[0], [[g.float() for g in gu] for gu in g_cpu[:2]], tensor_names(arm_cpu), t, world.device, lr=float(opts["rate"]), weight_decay=float(world.cfg_t["training"]["weight_decay"]), clip=float(world.cfg_t["training"]["clip_norm"]))  # ruling 43: clipping and the AdamW step
    repeat = compare_runs(runs["mps"], runs["mps_repeat"], t)
    ok = bool(loss["loss_ok"] and grad["passed"] and step["passed"])
    return {
        "passed": ok, "max_loss_difference": loss["max_loss_difference"], "loss_tolerance": loss["loss_tolerance"], "loss_ok": loss["loss_ok"], "gradient_agreement": grad, "optimiser_step_agreement": step,
        "parameters_recorded_not_gating": {**{k: loss[k] for k in ("max_relative_parameter_difference", "parameter_relative_difference_per_tensor", "parameter_tolerance_superseded")}, "tensors": tensor_names(arm_cpu), "gating": False},
        "mps_repeat_recorded_not_gating": {"max_loss_difference": repeat["max_loss_difference"], "max_relative_parameter_difference": repeat["max_relative_parameter_difference"]},
        "updates": updates, "device": str(world.device),
    }  # fmt: skip


def compare_runs(cpu: tuple[Sequence[float], Sequence[torch.Tensor]], other: tuple[Sequence[float], Sequence[torch.Tensor]], t: Mapping[str, Any]) -> dict[str, Any]:
    """The loss condition of G4's MPS gate (gating: every per-update loss within ``mps_loss_tolerance``, absolute) and the old relative parameter difference, RECORDED and never gating (``mps_parameter_relative_tolerance``
    is named as superseded by ruling 39). ``passed`` is the loss condition alone."""
    dl = max(abs(a - b) for a, b in zip(cpu[0], other[0], strict=True))
    per = [float((pm - pc).norm() / pc.norm().clamp_min(1e-30)) for pc, pm in zip(cpu[1], other[1], strict=True)]
    ok = dl <= float(t["mps_loss_tolerance"])
    return {"passed": bool(ok), "loss_ok": bool(ok), "max_loss_difference": dl, "loss_tolerance": float(t["mps_loss_tolerance"]), "max_relative_parameter_difference": max(per), "parameter_relative_difference_per_tensor": per, "parameter_tolerance_superseded": float(t["mps_parameter_relative_tolerance"])}


def compare_gradients(g_cpu: Sequence[Sequence[torch.Tensor]], g_mps: Sequence[Sequence[torch.Tensor]], names: Sequence[str], t: Mapping[str, Any]) -> dict[str, Any]:
    """The gradient condition (pure): for every update and trainable tensor, ``||g_mps - g_cpu|| / ||g_cpu|| <= mps_gradient_relative_tolerance`` where ``||g_cpu|| > 0``; where it is exactly 0 the MPS gradient must be
    exactly 0. Returns the largest relative figure with its tensor and update, and every violation of either clause."""
    tol = float(t["mps_gradient_relative_tolerance"])
    worst: dict[str, Any] = {"relative_difference": 0.0, "tensor": None, "update": None}
    over: list[dict[str, Any]] = []
    zero_violations: list[dict[str, Any]] = []
    for u, (gc_u, gm_u) in enumerate(zip(g_cpu, g_mps, strict=True), start=1):
        for i, (gc, gm) in enumerate(zip(gc_u, gm_u, strict=True)):
            n = float(gc.norm())
            if n > 0.0:
                r = float((gm - gc).norm()) / n
                if r > float(worst["relative_difference"]):
                    worst = {"relative_difference": r, "tensor": names[i], "update": u}
                if r > tol:
                    over.append({"tensor": names[i], "update": u, "relative_difference": r})
            elif float(gm.norm()) != 0.0:
                zero_violations.append({"tensor": names[i], "update": u, "mps_gradient_norm": float(gm.norm())})
    zero_cases = sum(1 for gc_u in g_cpu for gc in gc_u if float(gc.norm()) == 0.0)
    return {"passed": not over and not zero_violations, "tolerance": tol, "largest": worst, "violations_over_tolerance": over[:10], "n_violations_over_tolerance": len(over), "exact_zero_clause": {"cases": zero_cases, "violations": zero_violations[:10], "n_violations": len(zero_violations), "ok": not zero_violations}}


def g5b(store: Any, gen: torch.Generator) -> dict[str, Any]:
    """G5(b) (ADR-0022 section 12.3): a new store with gate 0 on an empty base changes nothing: with every gate at its initial 0 the store's read is exactly zero for any query, so adding it to the student adds
    nothing (checked on a clone of the store whose gates are set to 0, and on the store as it is only if its gates are 0)."""
    fresh = store.clone()
    for g in fresh.gates:
        g.data.zero_()
    q = torch.nn.functional.normalize(torch.randn(7, 16, generator=gen), dim=-1)
    zero = fresh.read(q)
    return {"passed": bool(torch.count_nonzero(zero) == 0), "max_abs_read": float(zero.abs().max())}


def g5(world: engine.WorldT, m_append: MemoryArm) -> dict[str, Any]:
    """Route "none" is bit-identical to the student (``general_by_construction``), and appended rows are isolated by their gate: with the gate at its initial 0, the values of the appended stage do not enter
    the read (the read is unchanged when they are replaced)."""
    ident = general_by_construction(world.ctx, m_append)["bit_identical_to_student"]
    store = m_append.store.clone()
    k = store.stages - 1
    q = torch.nn.functional.normalize(torch.randn(5, 16, generator=core.seeded_generator(core.g5_probe_seed(world.cfg_t, world.plan_mode), "G5 probe", {core.g5_probe_seed(world.cfg_t, world.plan_mode)})), dim=-1)
    store.gates[k].data.zero_()
    before = store.read(q)
    store.values[k].data.add_(7.0)
    after = store.read(q)
    b = g5b(m_append.store, core.seeded_generator(core.g5_probe_seed(world.cfg_t, world.plan_mode), "G5(b) probe", {core.g5_probe_seed(world.cfg_t, world.plan_mode)}))
    return {"passed": bool(ident and torch.equal(before, after) and b["passed"]), "none_route_bit_identical": ident, "appended_values_isolated_by_gate": bool(torch.equal(before, after)), "new_store_gate_zero_adds_nothing": b}


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


def g8(world: engine.WorldT, records: Mapping[str, Any] | None, q_record: Mapping[str, Any] | None = None, identity: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not records:
        return g8_not_run(q_record, identity)  # ruling 44: NOT RUN, never a pass; Part Q's step-1 verdicts are echoed
    res = equivalence.verify_all(world.student, dict(records))
    return {"passed": bool(res["ok"]), "detail": {k: v["ok"] for k, v in res["layers"].items()}}


def g9(cfg: Mapping[str, Any], root: Path | None = None) -> dict[str, Any]:
    r = gates.seed_gate("T", cfg, root=root)
    return {"passed": r["passed"], "problems": r["problems"], "checker": {k: v for k, v in r["checker"].items() if k != "problems_naming_this_study"}}


def g4_reach_all(world: engine.WorldT, updates: int = 2) -> dict[str, Any]:
    """Gradient reach on EVERY arm with a frozen part (ADR-0022 section 12.3 as carried by ADR-0025 section 7.3; audit R4), each built from a loaded/trained parent as the registered worker builds it: M-append, M-seq,
    M-ii, D-append and D-seq. In each, every trainable parameter receives a gradient and no student parameter does (the frozen first stage/adapter is checked by G7's hashes)."""
    dev, world.device = world.device, torch.device("cpu")
    out: dict[str, Any] = {}
    try:
        m1 = engine.build_cell_arm(world, engine.CellSpec("M1", "AB", 0), None)
        engine.train_cell(world, engine.CellSpec("M1", "AB", 0), m1[0], m1[1], m1[2], updates)
        d1 = engine.build_cell_arm(world, engine.CellSpec("D1", "AB", 0), None)
        engine.train_cell(world, engine.CellSpec("D1", "AB", 0), d1[0], d1[1], d1[2], updates)
        parents: dict[str, Any] = {"M-append": m1[0], "M-seq": m1[0], "D-append": d1[0], "D-seq": d1[0]}
        for name in ("M-append", "M-seq", "D-append", "D-seq"):
            spec = engine.CellSpec(name, "AB", 0)
            arm, rows, opts = engine.build_cell_arm(world, spec, parents[name])
            out[name] = reach_of(world, arm, rows)
            if name == "M-append":
                engine.train_cell(world, spec, arm, rows, opts, updates)
                parents["M-ii"] = arm
        spec = engine.CellSpec("M-ii", "AB", 0)
        arm, rows, _ = engine.build_cell_arm(world, spec, parents["M-ii"])
        out["M-ii"] = reach_of(world, arm, rows)
    finally:
        world.device = dev
    return {"passed": all(v["passed"] for v in out.values()), "arms": out}


def reach_of(world: engine.WorldT, arm: Any, rows: Sequence[Any]) -> dict[str, Any]:
    reach = p10train.gradient_reach(world.student, arm, rows[: world.batch], world.marker_index)
    return {"passed": bool(reach["arm_with_gradient"] == reach["arm_parameters"] and reach["student_with_gradient"] == 0), "reach": reach}


def run_gates(world: engine.WorldT, cfg: Mapping[str, Any], snap_dir: Path, *, equivalence_records: Mapping[str, Any] | None = None, q_equivalence_record: Mapping[str, Any] | None = None, student_identity: Mapping[str, Any] | None = None, root: Path | None = None, run_checker: bool = True, require_mps: bool = False, q_check_keys: Sequence[str] | None = None) -> dict[str, Any]:
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
        "G1": g1(world, q_check_keys=q_check_keys), "G2": g2(world, ma), "G4": {**g4_determinism(world, spec, int(cfg["gates"].get("g4_repeat_updates", 20))), "round_trip": g4_round_trip(world, copy.deepcopy(ma), snap_dir, "gate/M-append"), "reach_all_arms": g4_reach_all(world)}, "G4-MPS": g4_mps(world, spec, cfg), "G5": g5(world, ma), "G6": g6(world),
        "G7": g7(f_before, ma, sh, world.student), "G8": g8(world, equivalence_records, q_equivalence_record, student_identity), "G9": g9(cfg, root) if run_checker else {"passed": None, "skipped": "checker not run"},
    }  # fmt: skip
    del before
    out["G4"]["passed"] = bool(out["G4"]["passed"] and out["G4"]["reach_all_arms"]["passed"])  # the gate names gradient reach on every arm with a frozen part
    failed = [k for k, v in out.items() if v["passed"] is False or (require_mps and k == "G4-MPS" and v["passed"] is not True)]  # with ``require_mps`` a skipped MPS gate is a failure: it must have RUN and passed
    return {"gates": out, "failed": failed, "status": "ENGINEERING-FAILURE" if failed else "PASSED", "skipped": [k for k, v in out.items() if v["passed"] is None], "not_run": [k for k, v in out.items() if v.get("not_run")]}
