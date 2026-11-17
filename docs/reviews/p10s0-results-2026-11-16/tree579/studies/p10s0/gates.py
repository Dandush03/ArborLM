# ruff: noqa: E501
"""P10S0 gates (ADR-0020 section 10.2). G1 (generator) and G2 (chance) are computed by ``stages`` from the draws' records and the controls; G9 (seed disjointness) and G10 (the arm-selection
record against the auditor's independent evaluation) are pure checks of files and constants; this module holds what needs a model: G4, G5 and G6.

G4, for every arm of S0's arm set (A0, A1, A2, A5-D), A6, A7 and WX of each arm that can still be the candidate (A5-D, A1), at every cell type of section 6 where the arm runs:
  * each arm's forward and one training step in S0 are bit-identical to ``studies.p9ii``'s on a shared rehearsal seed;
  * checkpoint restoration bit-identical (A2's switch inside it), gradient reach of the training loss and of each loss alone, on contexts the cell covers;
  * WX with W_X zero outside its last 224 columns and equal to a W7 projection there gives W7's query bit for bit (asserted on the registered platform; elsewhere to 1e-6);
  * schedules at 8K/4K, 8K/16K and 32K/64K equal the exposure-scaled formulas; at 65,536 slots the full-N score path equals a direct computation;
  * the read swap: pi has no fixed point and no pair with equal answers; swapping twice restores the logits; the tie rule;
  * no A1 or A2 cell exists at 8K/4K in the registry; S0's protocol at 2K/4K and 8K/16K equals P9-II's Stage 1 and Stage 2 (so the pooled count is defined).
G5: backbone tensor hashes after training equal the frozen backbone's, and with the addition disabled the logits equal the frozen backbone's bit for bit. G6: no fact-identity input in any learned arm's
forward (WX included); identical logits under changed tables, also after training.

A harness error (inputs that do not belong to the cell) raises ``HarnessError`` and is never recorded as a defect (the P9-I attempt-1 lesson).
"""

import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch

from arborlm.io import file_sha256, read_json
from studies.p9.data import StudyData
from studies.p9i.evaluate import stream_for
from studies.p9i.stages import assert_covered, gate_contexts
from studies.p9ii import core as p9iicore
from studies.p9ii import gates as p9iigates
from studies.p9ii import model as p9iimodel
from studies.p9ii import train as p9iitrain

from . import arm_selection, core, evaluate, model, train

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

HarnessError = RuntimeError
GATE_CELLTYPE_ARMS: dict[str, tuple[str, ...]] = {
    "2K/4K": ("A0", "A1", "A2", "A5-D", "A6", "A7", *core.WX_ARMS),
    "8K/16K": ("A0", "A1", "A2", "A5-D", "A6", "A7", *core.WX_ARMS),
    "8K/4K": ("A0", "A5-D", "A6"),
    "32K/64K": ("A5-D", "A1", "A6"),
}


def gate_job(arm: str, ct: str, data: StudyData, backbone: "Backbone", out: Path, *, mode: str, init_seed: int, updates: int, hyper: core.Hyper = core.HYPER, unit: int = core.UPDATES, j: int = 0, spec: core.SeedSetSpec | None = None, diag_every: int = core.DIAG_EVERY, snapshots: tuple[int, ...] | None = None, max_updates: int | None = None, rehearsal_phase: str | None = None, facts: int | None = None) -> train.Job:
    """A job of ``arm`` at cell type ``ct`` on the first ``facts`` (default ``CELLTYPES[ct].facts``) facts of ``data``; ``max_updates`` is what the gates run (a few), ``updates`` is unused (the cell's total is the cell type's)."""
    cell = core.make_cell(arm, ct, "Q1", 1, j, "REH-" if mode == "rehearsal" else "TEST-")
    facts = cell.facts if facts is None else facts
    if spec is None:
        spec = core.set_of_name(data.seeds.name) if data.seeds.name.startswith("p10s0") else core.test_set(0)
    return train.Job(
        cell=cell, mode=mode, data=data, stream=train.training_stream_for(data, facts), backbone=backbone, out_dir=out, init_seed=init_seed, r1_seed=data.seeds.r1_codes,
        target_seed=spec.target_seed(ct, j), hyper=hyper, unit=unit, diag_every=diag_every, snapshots=snapshots, max_updates=max_updates if max_updates is not None else updates, rehearsal_phase=rehearsal_phase,
    )  # fmt: skip


# --- identity with studies.p9ii ----------------------------------------------------------------------------------------------------
def identity_against_p9ii(arm: str, data: StudyData, backbone: "Backbone", out: Path, *, p9ii_mode: str, s0_mode: str, init_seed: int, unit: int = core.UPDATES, facts: int = 2048, updates: int = 1) -> dict[str, Any]:
    """Each arm's forward at initialization and one training step in S0 against ``studies.p9ii``'s (its own ``run_job``) on a shared seed set: the logits, every parameter after the step and the
    first update's task loss, each ``torch.equal`` (bit for bit). ``p9ii_mode`` and ``s0_mode`` are the modes the two ``check_seed_set`` functions accept for the shared set."""
    hyper = core.HYPER._replace(u_pre=float(max(updates, 1)) * 2) if arm == "A2" else core.HYPER
    ours_model = model.build_model(arm, 4096, init_seed, backbone, r1_seed=data.seeds.r1_codes)
    theirs_model = p9iimodel.build_model(arm, 4096, init_seed, backbone, r1_seed=data.seeds.r1_codes)
    tokens = train.training_stream_for(data, facts).batch(1).tokens[:, : core.INPUT_LENGTH]
    ours_model.eval()
    theirs_model.eval()
    with torch.no_grad():
        forward = bool(torch.equal(ours_model(tokens)[0], theirs_model(tokens)[0]))
    cell = core.make_cell(arm, "2K/4K", "Q1", 1, 0, "TEST-")
    ours = train.run_job(
        train.Job(cell=cell, mode=s0_mode, data=data, stream=train.training_stream_for(data, facts), backbone=backbone, out_dir=out / "ours", init_seed=init_seed, r1_seed=data.seeds.r1_codes, target_seed=data.seeds.facts + 40, hyper=hyper, unit=unit, max_updates=updates, snapshots=(), diag_every=10**9)
    )  # fmt: skip
    p9cell = p9iicore.make_cell(arm, 4096, stage=1, draw=1, j=0)
    theirs = p9iitrain.run_job(
        p9iitrain.TrainJob(cell=p9cell, hyper=hyper, updates=cell.ct.updates(unit), mode=p9ii_mode, data=data, stream=train.training_stream_for(data, facts), backbone=backbone, out_dir=out / "theirs", init_seed=init_seed, r1_seed=data.seeds.r1_codes, target_seed=data.seeds.facts + 40, stream_seed=0, unit=unit, stage=1, snapshots=(), max_updates=updates, diag_every=10**9)
    )  # fmt: skip
    their_params = dict(theirs.model.named_parameters())
    params = all(torch.equal(p, their_params[n]) for n, p in ours.model.named_parameters())
    loss = ours.updates[0]["task_loss"] == theirs.updates[0]["task_loss"] if ours.updates and theirs.updates else True
    return {"arm": arm, "forward_identical": forward, "parameters_identical_after_step": params, "first_loss_identical": bool(loss), "passed": bool(forward and params and loss)}


# --- WX equivalence and the read swap ---------------------------------------------------------------------------------------------------------
def wx_equivalence(backbone: "Backbone", slots: int, seed: int, tokens: "Tensor", base: str = "A5-D") -> dict[str, Any]:
    """WX with W_X zero outside its last 224 columns and equal to a W7 projection there gives W7's query bit for bit; features before position 0 are zero-padded. Bit-identity is asserted on the registered
    platform (``core.on_registered_platform``); elsewhere the gate asserts closeness (<= 1e-6) and records the difference."""
    w7 = p9iimodel.build_model(base, slots, seed, backbone, seed_rng=False)
    wx = model.build_model(f"WX-{base}", slots, seed, backbone, seed_rng=False)
    with torch.no_grad():
        wx.addition.wq.copy_(model.w7_equivalent_projection(w7.addition.wq))
        w7.eval()
        wx.eval()
        h = w7.embed_block0(tokens)
        q7, qx = w7.answer_queries(h, tokens), wx.answer_queries(wx.embed_block0(tokens), tokens)
        assert q7 is not None and qx is not None
        pad = wx.addition.full_window(h, p9iimodel.SITES)
        zero_before_start = bool((pad[:, 0, : (core.FULL_WINDOW - 7) * core.HIDDEN_WIDTH] == 0).all())  # position 6 has 57 padded steps
    identical = bool(torch.equal(q7, qx))
    diff = float((q7 - qx).abs().max())
    passed = identical if core.on_registered_platform() else bool(diff <= 1e-6)
    return {"bit_identical": identical, "max_abs_difference": diff, "zero_padding_before_position_0": zero_before_start, "asserted_bitwise": core.on_registered_platform(), "parameters": int(wx.addition.wq.numel()), "w7_parameters": int(w7.addition.wq.numel()), "passed": bool(passed and zero_before_start)}


def read_swap_checks(data: StudyData, facts: int, seed: int, model_for_swap: Any | None = None) -> dict[str, Any]:
    """pi has no fixed point and no pair with equal answers; swapping with pi and then with its inverse restores the read table (and, when a model is given, the logits bit for bit); the tie
    rule: an answer tied for the arg-max counts as still the answer."""
    answers = evaluate.fact_answers(data, facts)
    perm = evaluate.swap_permutation(data, facts, seed)
    no_fixed = not bool((perm == torch.arange(facts)).any())
    no_equal = not bool((answers[perm] == answers).any())
    is_permutation = bool(torch.equal(perm.sort().values, torch.arange(facts)))
    table = torch.randn(facts, core.HIDDEN_WIDTH, generator=torch.Generator().manual_seed(seed))
    restored = bool(torch.equal(model.swap_reads(model.swap_reads(table, perm), model.inverse(perm)), table))
    logits = torch.zeros(2, 256)
    index = evaluate.ALPHABET_INDEX
    logits[:, index] = torch.tensor([[1.0, 1.0] + [0.0] * 30, [2.0, 1.0] + [0.0] * 30])
    answer = torch.tensor([0, 0])
    inside = logits[:, index]
    tie_counts_as_answer = bool((inside[torch.arange(2), answer] >= inside.max(-1).values).all())
    model_restores = True
    if model_for_swap is not None:
        stream = stream_for(data, facts, "panel_a")
        keep = (stream.fact_ids < facts).all(dim=1)
        tok = stream.tokens[keep][:8, : core.INPUT_LENGTH].contiguous()
        ids = stream.fact_ids[keep][:8]
        model_for_swap.eval()
        with torch.no_grad():
            h = model_for_swap.embed_block0(tok)
            delta = model_for_swap.memory_delta(h, model_for_swap.select(h, tok))
            site = p9iimodel.SITES
            reads = torch.zeros(facts, core.HIDDEN_WIDTH)
            reads[ids.reshape(-1)] = delta[:, site].reshape(-1, core.HIDDEN_WIDTH)
            twice = model.swap_reads(model.swap_reads(reads, perm), model.inverse(perm))
            back = delta.clone()
            for r in range(site.numel()):
                back[:, site[r]] = twice[ids[:, r]]
            model_restores = bool(torch.equal(model_for_swap.finish(h, back), model_for_swap.finish(h, delta)))
    passed = bool(no_fixed and no_equal and is_permutation and restored and tie_counts_as_answer and model_restores)
    return {"no_fixed_point": no_fixed, "no_equal_answer_pair": no_equal, "is_permutation": is_permutation, "swap_twice_restores_table": restored, "swap_twice_restores_logits": model_restores, "tie_counts_as_answer": tie_counts_as_answer, "facts": facts, "passed": passed}


def schedule_checks() -> dict[str, Any]:
    """Schedules at every cell type equal the exposure-scaled formulas: every class readout is at 512 exposures per fact (U at 2,048 facts, 4U at 8,192, 16U at 32,768); A2's U_pre is 2,048 updates at
    2,048 facts and 8,192 at 8,192 facts (the calibrated 2,048 x F / 2,048); A1, A5-D and WX have no schedule."""
    out: dict[str, Any] = {"exposures_at_decisive_readout": {}}
    ok = True
    for name, ct in core.CELLTYPES.items():
        e = core.exposures_per_fact(ct.decisive(), ct.facts)
        out["exposures_at_decisive_readout"][name] = e
        ok = ok and e == 512.0
    u2 = {ct: core.schedule_for("A2", ct).u_pre for ct in core.CORE_CELLTYPES}
    expected = {ct: int(round(core.CALIBRATED["u_pre"] * core.CELLTYPES[ct].facts / 2048)) for ct in core.CORE_CELLTYPES}
    out["a2_u_pre"] = {"got": u2, "expected": expected}
    ok = ok and u2 == expected
    constant = all(core.schedule_for(a, ct).u_pre is None for a in ("A1", "A5-D", "WX-A1", "WX-A5-D") for ct in core.CORE_CELLTYPES)
    out["constant_objective_arms_have_no_schedule"] = constant
    refused = False
    try:
        core.schedule_for("A2", "8K/4K")
    except ValueError:
        refused = True
    out["a2_refused_at_8k_4k"] = refused
    out["passed"] = bool(ok and constant and refused)
    return out


def registry_checks() -> dict[str, Any]:
    """No A1 or A2 cell exists at 8K/4K in the registry; the registry counts are those of section 6; S0's protocol at 2K/4K and 8K/16K equals P9-II's Stage 1 and Stage 2."""
    cells = [c for c in core.q1_cells() if c.celltype == "8K/4K"]
    none_supervised = not any(c.base in core.SUPERVISED for c in cells)
    counts = {"q1": len(core.q1_cells()), "q1_cut3": len(core.q1_cells(True)), "wx": len(core.wx_cells("A5-D")), "probe": len(core.probe_cells("A5-D")), "check": len(core.check_cells())}
    p9 = p9iicore
    same = {
        "2K/4K = Stage 1": (core.CELLTYPES["2K/4K"].slots, core.CELLTYPES["2K/4K"].facts, core.CELLTYPES["2K/4K"].multiplier) == (p9.STAGE_SLOTS[1], p9.FACTS_PROPORTIONAL[p9.STAGE_SLOTS[1]], p9.STAGE_MULTIPLIER[1]),
        "8K/16K = Stage 2": (core.CELLTYPES["8K/16K"].slots, core.CELLTYPES["8K/16K"].facts, core.CELLTYPES["8K/16K"].multiplier) == (p9.STAGE_SLOTS[2], p9.FACTS_PROPORTIONAL[p9.STAGE_SLOTS[2]], p9.STAGE_MULTIPLIER[2]),
        "readouts": core.CELLTYPES["8K/16K"].readouts == (1, 4) and core.CELLTYPES["2K/4K"].readouts == (1,),
    }
    ok = none_supervised and counts == {"q1": 230, "q1_cut3": 190, "wx": 20, "probe": 6, "check": 3} and all(same.values())
    return {"no_a1_a2_at_8k_4k": none_supervised, "counts": counts, "protocol_identical_to_p9ii": same, "passed": bool(ok)}


# --- per-(arm, cell type) checks ------------------------------------------------------------------------------------------------------------------------
def reach_checks(job: train.Job, tokens: "Tensor", fact_ids: "Tensor") -> dict[str, Any]:
    """Gradient reach of the training loss and of each loss alone for the arm of ``job``, on covered contexts (as ``studies.p9ii.gates.reach_checks``, through S0's builder)."""
    base = job.cell.base
    out: dict[str, Any] = {}
    reach = train.gradient_reach(job, tokens, fact_ids, "training")
    ok = bool(all(reach["reached"].values()) and not reach["stray"] and not reach["buffer_gradients"])
    out["training"] = {"all_reached": all(reach["reached"].values()), "trainable": reach["trainable"], "stray": reach["stray"], "buffer_gradients": reach["buffer_gradients"]}
    if base in ("A1", "A2"):
        r = train.gradient_reach(job, tokens, fact_ids, "addr", phase=2)
        reached = sorted(n.rsplit(".", 1)[-1] for n, v in r["reached"].items() if v)
        out["address_loss"] = {"reached": reached, "stray": r["stray"]}
        ok = ok and reached == ["keys", "wq"] and not r["stray"]
    if base == "A5-D":
        r = train.gradient_reach(job, tokens, fact_ids, "div")
        reached = sorted(n.rsplit(".", 1)[-1] for n, v in r["reached"].items() if v)
        out["diversity_loss"] = {"reached": reached, "stray": r["stray"]}
        ok = ok and reached == ["wq"] and not r["stray"]
    if base == "A2":
        r1 = train.gradient_reach(job, tokens, fact_ids, "training", phase=1)
        names = sorted(n.rsplit(".", 1)[-1] for n in r1["reached"])
        out["phase1"] = {"trainable": names, "all_reached": all(r1["reached"].values()), "stray": r1["stray"]}
        ok = ok and names == ["keys", "wq"] and all(r1["reached"].values()) and not r1["stray"]
    out["passed"] = bool(ok)
    return out


def a2_switch_check(job: train.Job) -> dict[str, Any]:
    """A2's switch at U_pre: the trainable set changes and every AdamW moment and counter is reset there (``studies.p9ii.gates.schedule_checks``'s A2 half, through S0's job)."""
    from studies.p9ii.diagnostics import build_probe
    from studies.p9ii.train import Trainer

    m = model.build_model("A2", job.cell.slots, job.init_seed, job.backbone)
    t = Trainer(job.to_p9ii(), m, build_probe(job.data, int(job.stream.facts.shape[0])))
    u_pre = int(t.schedule.u_pre or 0)
    phase1 = sorted(n.rsplit(".", 1)[-1] for n, _ in t.named)
    for u in range(1, u_pre + 1):
        t.step(job.stream.batch(u))
    t.step(job.stream.batch(u_pre + 1))
    phase2 = sorted(n.rsplit(".", 1)[-1] for n, _ in t.named)
    steps = [int(s["step"]) for s in t.optimizers[0].state.values()]
    ok = steps == [1] * len(steps) and len(steps) == len(phase2) and phase1 == ["keys", "wq"] and phase2 == ["gate", "keys", "values", "wo", "wq"]
    return {"u_pre": u_pre, "phase1_trainable": phase1, "phase2_trainable": phase2, "counters_restarted": steps == [1] * len(steps), "passed": bool(ok)}


@torch.no_grad()
def _logits(m: Any, tokens: "Tensor") -> "Tensor":
    m.eval()
    out: Tensor = m(tokens)[0]
    return out


def g6_check(backbone: "Backbone", slots: int, seed: int, tokens: "Tensor", fact_lut_a: "Tensor", fact_lut_b: "Tensor") -> dict[str, Any]:
    """G6: no learned arm's forward (WX included) has a fact-identity input, and with the token inputs fixed, changing the R1 codes and the fact tables leaves every learned arm's logits bit-identical."""
    out: dict[str, Any] = {"arms": {}}
    for arm in core.LEARNED_ARMS:
        args = p9iimodel.forward_arguments(model.build_model(arm, slots, seed, backbone, seed_rng=False))
        a = model.build_model(arm, slots, seed, backbone, r1_seed=101, seed_rng=False)
        b = model.build_model(arm, slots, seed, backbone, r1_seed=202, seed_rng=False)
        same = bool(torch.equal(_logits(a, tokens), _logits(b, tokens)))
        out["arms"][arm] = {"forward_arguments": args, "tokens_only": args["forward"] == ["tokens"] and args["select"] == ["h_pre", "tokens"], "logits_identical_under_changed_tables": same}
    out["fact_tables_differ"] = bool(not torch.equal(fact_lut_a, fact_lut_b))
    out["passed"] = bool(out["fact_tables_differ"] and all(v["tokens_only"] and v["logits_identical_under_changed_tables"] for v in out["arms"].values()))
    return out


def g6_after_training(make_job: Callable[[str, str, int], train.Job], tokens: "Tensor", updates: int = 4) -> dict[str, Any]:
    """G6 after training (as ``studies.p9ii.gates.g6_after_training``): train every learned arm (WX included) a few updates, replace the trainer's injection and scramble the fact-to-answer table;
    the logits on the fixed tokens must not change, a model rebuilt from its ``state_dict`` alone must give identical logits, and the model must hold no tensor outside its parameters and buffers."""
    out: dict[str, Any] = {"arms": {}}
    for arm in core.LEARNED_ARMS:
        run = train.run_job(make_job(arm, f"g6_{arm}", updates))
        before = _logits(run.model, tokens)
        if run.trainer.injection is not None:
            run.trainer.injection = p9iimodel.target_injection(int(run.trainer.injection.shape[0]), run.model.slots, 12345)
        data = run.trainer.job.data
        data.facts.answer = data.facts.answer.flip(0).clone()
        try:
            after = _logits(run.model, tokens)
        finally:
            data.facts.answer = data.facts.answer.flip(0).clone()
        rebuilt = model.build_model(arm, run.model.slots, run.trainer.job.init_seed, run.trainer.job.backbone, seed_rng=False)
        rebuilt.load_state_dict(run.model.state_dict())
        stray = [n for n, v in vars(run.model.addition).items() if isinstance(v, torch.Tensor) and n not in ("last_query", "_pending_z")]
        stray += [n for n, v in vars(run.model).items() if isinstance(v, torch.Tensor)]
        ok = bool(torch.equal(before, after) and torch.equal(before, _logits(rebuilt, tokens)) and not stray)
        out["arms"][arm] = {"unchanged_by_injection_and_fact_table": bool(torch.equal(before, after)), "rebuilt_from_state_dict_identical": bool(torch.equal(before, _logits(rebuilt, tokens))), "stray_tensor_attributes": stray, "passed": ok}
    out["passed"] = all(v["passed"] for v in out["arms"].values())
    return out


def run_g4_g5_g6(
    data_by_facts: Mapping[int, StudyData],
    backbone: "Backbone",
    *,
    mode: str,
    restore_split: int,
    out_dir: Path,
    init_seed: int,
    rows: "Tensor",
    swap_seed: int,
    identity_data: StudyData | None = None,
    identity_modes: tuple[str, str] | None = None,
    celltypes: tuple[str, ...] = tuple(GATE_CELLTYPE_ARMS),
    unit: int = core.UPDATES,
    facts_of: Callable[[int], int] = lambda real: real,
) -> dict[str, Any]:
    """Every model-dependent gate at the cell types of section 6. Returns ``g4_defects`` (strings), the per-check records, ``g4_passed`` / ``g5_passed`` / ``g6_passed`` and ``harness_errors`` (reported
    apart: inputs that do not belong to the cell). The gates train a few updates per check on the draw's own training data (so on the rehearsal draw they run before the freeze, on the registered draw
    before training)."""
    defects: list[str] = []
    harness: list[str] = []
    record: dict[str, Any] = {"identity_against_p9ii": {}, "gradient_reach": {}, "restoration": {}, "a2_switch": {}}
    g5: dict[str, Any] = {}
    hyper = core.HYPER._replace(u_pre=float(restore_split))
    if identity_data is not None and identity_modes is not None:
        for arm in core.CORE_LEARNED_ARMS + core.REFERENCE_ARMS:
            r = identity_against_p9ii(arm, identity_data, backbone, out_dir / f"identity_{arm}", p9ii_mode=identity_modes[0], s0_mode=identity_modes[1], init_seed=init_seed, unit=unit, facts=facts_of(2048))
            record["identity_against_p9ii"][arm] = r
            if not r["passed"]:
                defects.append(f"arm {arm} differs from studies.p9ii's on the shared rehearsal seed")
    record["schedules"] = schedule_checks()
    record["registry"] = registry_checks()
    for key in ("schedules", "registry"):
        if not record[key]["passed"]:
            defects.append(f"{key} check failed")
    record["full_scores"] = p9iigates.full_score_checks(seed=core.TEST_SEED_TOP)
    if not record["full_scores"]["passed"]:
        defects.append("all-N-score check failed")
    first = data_by_facts[2048] if 2048 in data_by_facts else next(iter(data_by_facts.values()))
    first_facts = facts_of(2048) if 2048 in data_by_facts else facts_of(int(next(iter(data_by_facts))))
    try:
        tokens0, ids0 = gate_contexts(first, first_facts)
        assert_covered(tokens0, ids0, first_facts)
    except HarnessError as exc:
        harness.append(str(exc))
        tokens0 = torch.zeros(1, core.CONTEXT_BYTES, dtype=torch.int64)
    record["wx_equivalence"] = wx_equivalence(backbone, 4096, init_seed, tokens0[:, : core.INPUT_LENGTH])
    if not record["wx_equivalence"]["passed"]:
        defects.append("WX with W_X zero outside its last 224 columns does not give W7's query")
    record["read_swap"] = {}
    sample = rows[:256, : core.CONTEXT_BYTES].contiguous()
    for ct in celltypes:
        real = core.CELLTYPES[ct].facts
        facts = facts_of(real)
        data = data_by_facts.get(real)
        if data is None:
            harness.append(f"no data for {real} facts: {ct} was not checked")
            continue
        try:
            tokens_all, fact_ids = gate_contexts(data, facts)
            assert_covered(tokens_all, fact_ids, facts)
        except HarnessError as exc:
            harness.append(f"{ct}: {exc}")
            continue
        try:
            record["read_swap"][ct] = read_swap_checks(data, facts, swap_seed, model.build_model("A0", core.CELLTYPES[ct].slots, init_seed, backbone))
        except ValueError as exc:
            record["read_swap"][ct] = {"passed": False, "error": str(exc)}
        if not record["read_swap"][ct]["passed"]:
            defects.append(f"read swap checks failed at {ct}")
        for arm in GATE_CELLTYPE_ARMS[ct]:
            key = f"{arm}@{ct}"
            j = gate_job(arm, ct, data, backbone, out_dir / f"reach_{arm}_{core.CELLTYPES[ct].token}", mode=mode, init_seed=init_seed, updates=4 * restore_split, hyper=hyper, unit=unit, max_updates=4 * restore_split, facts=facts)
            record["gradient_reach"][key] = reach_checks(j, tokens_all, fact_ids)
            if not record["gradient_reach"][key]["passed"]:
                defects.append(f"gradient reach failed for {key}")
            if arm in core.LEARNED_ARMS:
                rj = gate_job(arm, ct, data, backbone, out_dir / f"restore_{arm}_{core.CELLTYPES[ct].token}", mode=mode, init_seed=init_seed, updates=4 * restore_split, hyper=hyper, unit=unit, max_updates=4 * restore_split, facts=facts)
                record["restoration"][key] = train.checkpoint_restoration_check(rj, restore_split)
                if not record["restoration"][key]["identical"]:
                    defects.append(f"checkpoint restoration is not bit-identical for {key}")
            gj = gate_job(arm, ct, data, backbone, out_dir / f"g5_{arm}_{core.CELLTYPES[ct].token}", mode=mode, init_seed=init_seed, updates=4, hyper=hyper, unit=unit, max_updates=4, snapshots=(), facts=facts)
            run = train.run_job(gj)
            g5[key] = p9iimodel.g5_check(run.model, backbone, sample)
        if "A2" in GATE_CELLTYPE_ARMS[ct]:
            sj = gate_job("A2", ct, data, backbone, out_dir / f"a2_{core.CELLTYPES[ct].token}", mode=mode, init_seed=init_seed, updates=4 * restore_split, hyper=hyper, unit=unit, max_updates=4 * restore_split, facts=facts)
            record["a2_switch"][ct] = a2_switch_check(sj)
            if not record["a2_switch"][ct]["passed"]:
                defects.append(f"A2's switch check failed at {ct}")
    a = gate_job("A0", "2K/4K", first, backbone, out_dir / "determinism_1", mode=mode, init_seed=init_seed, updates=6, unit=unit, max_updates=6, snapshots=(), facts=first_facts) if 2048 in data_by_facts else None
    if a is not None:
        r1, r2 = train.run_job(a), train.run_job(gate_job("A0", "2K/4K", first, backbone, out_dir / "determinism_2", mode=mode, init_seed=init_seed, updates=6, unit=unit, max_updates=6, snapshots=(), facts=first_facts))
        record["determinism"] = {"identical": all(torch.equal(p, dict(r2.model.named_parameters())[n]) for n, p in r1.model.named_parameters())}
        if not record["determinism"]["identical"]:
            defects.append("two identical runs differ")
    g6 = g6_check(backbone, 4096, init_seed, tokens0[:, : core.INPUT_LENGTH], torch.arange(10), torch.arange(10).flip(0))
    if 2048 in data_by_facts:
        g6["trained"] = g6_after_training(lambda arm, name, updates: gate_job(arm, "2K/4K", first, backbone, out_dir / name, mode=mode, init_seed=init_seed, updates=updates, hyper=hyper, unit=unit, max_updates=updates, snapshots=(), facts=first_facts), tokens0[:, : core.INPUT_LENGTH])
        g6["passed"] = bool(g6["passed"] and g6["trained"]["passed"])
    return {"g4_defects": defects, "g4_passed": not defects and not harness, "harness_errors": harness, "g5": g5, "g5_passed": bool(g5) and all(v["passed"] for v in g5.values()), "g6": g6, "g6_passed": bool(g6["passed"]), "checks": record}


# --- G9: seed disjointness ---------------------------------------------------------------------------------------------------------------------------------
def scan_p9ii_code_for_test_seeds(repo: Path) -> frozenset[int]:
    """P9-II's actual test seeds, read from its committed code and tests: the seeds of every ``test_seeds(k)`` offset called in ``studies/p9ii/*.py`` or ``tests/test_p9ii_*.py`` (an offset out of range
    is a refusal under test, not a seed in use). Integer literals are not read: P9-II's tests also contain numbers that name ranges to be refused (900001, 920001, 929999). G9 asserts the seeds found inside
    910001-919999."""
    found: set[int] = set()
    files = [*sorted((repo / "studies" / "p9ii").glob("*.py")), *sorted((repo / "tests").glob("test_p9ii_*.py"))]
    for path in files:
        for k in re.findall(r"test_seeds\((\d+)\)", path.read_text(encoding="utf-8")):
            try:
                found |= p9iicore.seed_values(p9iicore.test_seeds(int(k)))
            except ValueError:
                continue
    return frozenset(found)


def g9_check(repo: Path | None = None) -> dict[str, Any]:
    """Gate G9 (section 7): S0's seed groups are disjoint from each other, lie in their own bounded ranges and in none of the other studies' (P9, P9-I, review diagnostics, P9-II incl. 1891-1892,
    S1 incl. 2101-2105, 2111, 2121, 2112, 2122, 2191-2192, S2) or in a seed those studies' code uses or the configs of P1-P8 name; P9-II's actual test seeds, read from its committed code, lie inside 910001-919999."""
    base = repo or core.repo_root()
    problems: list[str] = []
    configs = core.config_seed_values(base)
    extra = {**core.implemented_study_seeds(), **{f"config {name}": v for name, v in configs.items()}}
    try:
        core.assert_namespaces_disjoint(extra=extra)
    except ValueError as exc:
        problems.append(str(exc))
    if (p9iicore.TEST_SEED_BASE, p9iicore.TEST_SEED_TOP) != (910001, 919999):  # P9-II's test-seed constants, asserted directly (the lead's ruling on item 8)
        problems.append(f"P9-II's test-seed constants are {p9iicore.TEST_SEED_BASE}-{p9iicore.TEST_SEED_TOP}, not 910001-919999")
    if not all(910001 <= v <= 919999 for v in p9iicore.seed_namespaces()["test"]):
        problems.append("P9-II's seed_namespaces()['test'] is not inside 910001-919999")
    test_profile = frozenset().union(*(core.registered_set(k, "test").values() for k in range(1, core.N_DRAWS + 1)), *(core.reserve_set(r, "test").values() for r in (1, 2)))
    if not all(core.TEST_SEED_BASE <= v <= core.TEST_SEED_TOP for v in test_profile):
        problems.append("a test-profile seed lies outside 920001-920999")
    p9ii_tests = core.p9ii_test_seed_values() | scan_p9ii_code_for_test_seeds(base)
    outside = sorted(v for v in p9ii_tests if not 910001 <= v <= 919999)
    if outside:
        problems.append(f"P9-II test seeds outside 910001-919999: {outside[:3]}")
    return {
        "passed": not problems, "problems": problems, "s0_ranges": {k: [list(r) for r in v] for k, v in core.S0_RANGES.items()},
        "other_ranges": {k: [list(r) for r in v] for k, v in core.OTHER_NAMESPACES.items()}, "p9ii_test_seed_count": len(p9ii_tests), "p9ii_code_scanned": True, "p9ii_test_seeds_inside_range": not outside,
        "config_files_scanned": sorted(configs), "implemented_studies_checked": sorted(core.implemented_study_seeds()),
    }  # fmt: skip


# --- G10: the arm-selection record against the independent evaluation -------------------------------------------------------------------------------------------
ADR_STRINGS = ("human_lead_words", "printed_string", "f1_annotation", "fixed_sentence")


def adr_text(repo: Path) -> str:
    return (repo / core.SPEC).read_text(encoding="utf-8")


def independent_evaluation(repo: Path) -> dict[str, Any]:
    """The IMPLEMENTER'S second reading (not the auditor's: the auditor's recomputation is the audit's own file, whose path and sha256 the freeze record names), written again from ADR-0020 sections 3.2, 3.3
    and 3.5 and not through ``arm_selection``'s functions: the table cell of section 3.3 that P9-II's committed outcome falls in, the fourth arm it gives, and the arms that can still be the candidate by
    section 8.5 (b) from P9-II's draw counts."""
    res = read_json(repo / core.P9II_RECORDS["results"])["result"]
    calibration_exists = (repo / core.P9II_RECORDS["calibration"]).is_file()
    outcome, carried = str(res["outcome"]["outcome"]), (res.get("carried_forward") or {}).get("arm")
    stage2 = (res.get("stage2") or {}).get("status")
    if not calibration_exists:
        row, c4 = None, None
    elif outcome in ("ENGINEERING_FAIL", "INCOMPLETE", "NOT_INTERPRETED", "NOT_INTERPRETED (INCOMPLETE)"):
        row, c4 = 11, None
    elif outcome == "ADDRESSING-RELIABLE":
        row, c4 = (1, carried) if carried in ("A5-C", "A5-D", "A4") else (2, None) if carried in ("A2", "A1") else (3, None)
    elif outcome == "ANSWER-ONLY RELIABLE":
        if stage2 != "COMPLETE":
            row, c4 = 7, None
        elif carried == "A0":
            row, c4 = 4, None
        elif carried in ("A5-C", "A5-D", "A4"):
            row, c4 = 5, carried
        else:
            row, c4 = 6, None
    elif outcome == "ADDRESSING-RELIABLE AT 4,096 ONLY":
        row, c4 = 8, None
    elif outcome.startswith("ADDRESSING-RELIABLE AT 4,096; 16,384"):
        row, c4 = 9, None
    else:
        row, c4 = 10, None
    candidates: list[str] = []
    excluded: dict[str, str] = {}
    interpreted = row is not None and row != 11
    for arm in ("A0", "A5-D", "A2", "A1"):
        a = (res.get("stage1") or {}).get("arms", {}).get(arm) if interpreted else None
        if a is None:
            candidates.append(arm)
            continue
        counts = a["draw_sensitivity"]["draw_counts"]
        failed = sum(int(v) for k, v in counts.items() if k != "2/2")
        if "LM CAPABILITY REDUCED" in str(a["class"]):
            excluded[arm] = "LM"
        elif failed > 2:
            excluded[arm] = f"failed draws {failed}"
        else:
            candidates.append(arm)
    return {"table_row": row, "c4": c4, "candidates": candidates, "excluded": excluded}


def run_auditor_part1(script: Path) -> dict[str, Any]:
    """Re-run Part 1 of the auditor's enumeration script (``adr-0020-review/c5_rev2_mapping_and_consistency.py``) and return what it printed. It imports its sibling ``c2_mapping_enumeration``
    from its own directory (the auditor's own model of ADR-0019 revision 4)."""
    import contextlib
    import importlib.util
    import io
    import sys

    sys.path.insert(0, str(script.parent))
    try:
        spec = importlib.util.spec_from_file_location("c5_rev2_mapping_and_consistency", script)
        if spec is None or spec.loader is None:
            raise ImportError(script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            module.part1()
    finally:
        sys.path.remove(str(script.parent))
    text = buffer.getvalue()
    match = re.search(r"rule-vs-table disagreements: (.*)", text)
    sibling = script.parent / "c2_mapping_enumeration.py"
    return {"script": str(script), "script_sha256": file_sha256(script), "sibling_sha256": file_sha256(sibling) if sibling.is_file() else None, "output": text, "disagreements": match.group(1).strip() if match else None, "no_disagreements": bool(match and match.group(1).strip() == "none")}


AUDITOR_SCRIPT = Path("docs/reviews/p10-design-2026-11-15/adr-0020-review/c5_rev2_mapping_and_consistency.py")


def g10_check(record: Mapping[str, Any], repo: Path | None = None, *, run_script: bool = False, script: Path | None = None, pinned: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Gate G10 (section 10.2): the mapping part of the arm-selection record equals the independent evaluation of section 3.2 on P9-II's committed records (whose hashes the record holds and which are
    re-hashed here); the table cell matching P9-II's committed outcome is cited; the override part equals section 3.4 character for character (read from the ADR file); the list of arms that can still
    be the candidate equals the independent evaluation of section 8.5 (b). With ``run_script``, Part 1 of the auditor's enumeration script is re-run."""
    base = repo or core.repo_root()
    problems: list[str] = []
    ind = independent_evaluation(base)
    mapping, override = record["mapping"], record["override"]
    if mapping["c4"] != ind["c4"]:
        problems.append(f"fourth arm: record {mapping['c4']!r}, independent evaluation {ind['c4']!r}")
    if mapping["table_row"] != ind["table_row"]:
        problems.append(f"table row: record {mapping['table_row']}, independent evaluation {ind['table_row']}")
    if not mapping.get("steps_equal_table"):
        problems.append("the record's steps and table readings disagree")
    if record["candidates"]["arms"] != ind["candidates"]:
        problems.append(f"arms that can still be the candidate: record {record['candidates']['arms']}, independent evaluation {ind['candidates']}")
    for key, entry in record["p9ii_inputs"].items():
        path = base / entry["path"]
        if not path.is_file() or file_sha256(path) != entry["sha256"]:
            problems.append(f"P9-II record {key} does not hash to the arm-selection record's value")
    adr = adr_text(base)
    expected = {"human_lead_words": core.HUMAN_LEAD_WORDS, "printed_string": core.FOURTH_ARM_STRING, "f1_annotation": core.F1_ANNOTATION, "fixed_sentence": core.PROVENANCE_SENTENCE}
    for key in ADR_STRINGS:
        if override[key] != expected[key]:
            problems.append(f"override {key} differs from the constants")
        if override[key] not in adr:
            problems.append(f"override {key} is not in {core.SPEC} character for character")
    if float(override["mu"]) != 1.0 or override["c4"] != "A5-D" or override["date"] != core.OVERRIDE_DATE:
        problems.append("override: arm, mu or date differs from section 3.4")
    outcome_md = base / core.P9II_RECORDS["outcome"]
    if outcome_md.is_file() and core.F1_ANNOTATION not in outcome_md.read_text(encoding="utf-8"):
        problems.append("the F1 annotation is not verbatim in P9-II's OUTCOME.md")
    cal = record["calibrated"]
    if (cal["lambda"], cal["u_pre"], cal["mu"]) != (1.0, 2048.0, 1.0) or not cal["equals_p9ii_record"]:
        problems.append("calibrated values differ from lambda = 1.0, U_pre = 2,048, mu = 1.0 or from P9-II's calibration record")
    script_result: dict[str, Any] | None = None
    if run_script:
        path = script or base / AUDITOR_SCRIPT
        if pinned is not None:  # the freeze plan pins the hash of the script this gate executes and of its sibling; nothing unhashed is run (the audit's m3)
            for f in (path, path.parent / "c2_mapping_enumeration.py"):
                if not f.is_file() or file_sha256(f) != pinned.get(f.name):
                    problems.append(f"{f.name} does not hash to the value the freeze plan pinned: it is not run")
        if not problems or pinned is None:
            script_result = run_auditor_part1(path)
        else:
            return {"passed": False, "problems": problems, "independent": ind, "table_cell_cited": None, "table_row": ind["table_row"], "auditor_script": None, "auditor_script_run": False}
        if not script_result["no_disagreements"]:
            problems.append("Part 1 of the auditor's script reports disagreements")
    row = ind["table_row"]
    return {
        "passed": not problems, "problems": problems, "independent": ind, "table_cell_cited": None if row is None else arm_selection.TABLE_ROWS[row], "table_row": row,
        "auditor_script": script_result, "auditor_script_run": bool(run_script), "arm_selection_sha256_note": "the freeze records the sha256 of the record file",
    }  # fmt: skip


def dump(record: Mapping[str, Any]) -> str:
    return json.dumps(core.jsonable(dict(record)), indent=1, sort_keys=True)

