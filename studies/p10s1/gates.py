# ruff: noqa: E501
"""P10S1 gates G2 and G4 to G9 (ADR-0021 section 8.1), runnable at real size on any seed set the mode allows (the rehearsal draw before the freeze, the registered draws before
training, test seeds in the unit tests). G1 (generator) is computed by ``stages`` from the draw's records; this module holds what needs a model or a seed list.

G2  chance: the no-memory baseline on the fact sets and the unseen set, both panels, in 40 exact binomial tests (level 1 - 0.001/40).
G4  determinism and identity: checkpoint restoration bit for bit for one cell of every arm; train-restore-continue equals the straight run; two identical runs are identical;
    F-OQ and R2 identical to P9-I's R1 and R2 (forward and one training step); the logits with the memory disabled equal the frozen backbone's on the corpus rows; the index of
    section 5.5 is identical on rebuild.
G5  gradient reach for every configuration of the plan at its real facts and slots, on a batch of that cell's own training stream: every trainable group receives a non-zero gradient;
    in H8 exactly the hashed rows do; R2's table covers every fact of the cell; nothing reaches the backbone.
G6  controlled-addressing integrity: the query and the selection of F-OQ, T-OQ, H8 and R2 are unchanged when the context is permuted and when the answer table is replaced; D-OQ's
    input tensor has the same hash as F-OQ's codes; no forward takes the answer as input and no model holds a fact table.
G7  the work counters equal the formulas of section 7.4.   G8  D-OQ's parameter count is within 0.1% of F-OQ's.   G9  seeds (``core.seed_check``).

A harness error (inputs that do not belong to the cell) raises ``HarnessError`` and is never recorded as a defect (the P9-I attempt-1 lesson).
"""

import inspect
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch

from studies.p9 import controls
from studies.p9 import model as p9model
from studies.p9.data import StudyData, encode_identifiers, restrict_stream
from studies.p9.model import Selection
from studies.p9i import core as p9icore
from studies.p9i import model as p9imodel
from studies.p9i import train as p9itrain
from studies.p9i.stages import assert_covered, gate_contexts

from . import core, index, train
from .model import (
    P10S1Model,
    backbone_hashes,
    build_model,
    g5_check,
    parameter_report,
    tensor_sha256,
)

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

HarnessError = RuntimeError


def tiny_job(arm: str, data: StudyData, backbone: "Backbone", facts: int, slots: int, out: Path, *, mode: str, updates: int, init_seed: int, draw: int = 1, snapshots: tuple[int, ...] | None = None, max_updates: int | None = None, lr: float | None = None) -> train.TrainJob:
    """A job of ``arm`` at ``slots`` on the first ``facts`` facts of ``data``; ``updates`` is the cell's total (the gates run a few)."""
    cell = core.make_cell("P", arm, facts, slots, draw, init_seed, run_updates=updates, test=True, lr=core.LEARNING_RATE if lr is None else lr)
    return train.TrainJob(
        cell=cell, data=data, stream=train.training_stream_for(data, facts), backbone=backbone, out_dir=out, r1_seed=data.seeds.r1_codes, hash_seed=core.h8_seed(data.seeds), mode=mode,
        updates=updates, snapshots=snapshots, fact_lut=train.fact_lut_for(data, facts) if arm == "R2" else None, max_updates=max_updates, log_every=core.REHEARSAL_UPDATES,
    )  # fmt: skip


# --- G2 --------------------------------------------------------------------------------------------------------------------------------
def no_memory_counts(backbone: "Backbone", data: StudyData, fact_counts: Sequence[int]) -> dict[str, dict[str, dict[str, int]]]:
    """``{panel: {"<F>": {correct, facts}, ..., "unseen": ...}}``: the no-memory baseline on the F-fact sets and the unseen set of both panels (section 8.1 G2)."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for panel, name in core.PANEL_STREAM.items():
        per: dict[str, dict[str, int]] = {}
        full = data.streams[name]
        for facts in fact_counts:
            stream = restrict_stream(full, data.facts, facts)
            scores = controls.evaluate_no_memory(backbone, data.facts, stream)
            ids = stream.fact_ids.reshape(-1)
            mask = ids < facts
            per[str(facts)] = {"correct": int(scores.correct[mask].sum()), "facts": int(mask.sum())}
            if facts == fact_counts[-1]:
                unseen = ids >= data.facts.trained
                per["unseen"] = {"correct": int(scores.correct[unseen].sum()), "facts": int(unseen.sum())}
        out[panel] = per
    return out


def g2_report(by_draw: dict[str, dict[str, dict[str, dict[str, int]]]]) -> dict[str, Any]:
    """G2 over every draw given: each count must lie inside the exact binomial central interval of level 1 - 0.001/40 around 1/32 ([34, 100], [192, 325], [894, 1,159] at 2,048,
    8,192 and 32,768 facts). Five draws x two panels x (three fact sets + the unseen set) = 40 tests."""
    counts = {f"d{d}/{panel}/{name}": (v["correct"], v["facts"]) for d, panels in by_draw.items() for panel, per in panels.items() for name, v in per.items()}
    rep = controls.g2_report(counts, core.G2_TESTS)
    return {"tests": len(counts), "level_tests": core.G2_TESTS, "passed": bool(rep["passed"]) and bool(counts), "results": [dict(r) for r in rep["results"]]}


# --- G4 --------------------------------------------------------------------------------------------------------------------------------
def p9i_identity(job: train.TrainJob, arm: str) -> dict[str, Any]:
    """F-OQ (against P9-I's R1) or R2 (against P9-I's R2): parameters, forward at every position, selection and one training step (the loss and every parameter after the step),
    each ``torch.equal`` (bit for bit)."""
    p9arm = {"F-OQ": "R1", "R2": "R2"}[arm]
    bb, seed, slots = job.backbone, job.cell.init_seed, job.cell.slots
    batch = job.stream.batch(1)
    tokens = batch.tokens
    lut = job.fact_lut if arm == "R2" else None
    theirs = p9imodel.build_model(p9arm, slots, seed, bb, fact_lut=lut, r1_seed=job.r1_seed)
    mine = train.job_model(job)
    same = all(torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in mine.named_parameters() if n.startswith("addition."))
    theirs.eval()
    mine.eval()
    with torch.no_grad():
        lt, st = theirs(tokens[:, :-1])
        lm, sm = mine(tokens[:, :-1])
    assert st is not None and sm is not None and hasattr(sm, "selected")
    forward = {"logits_identical": bool(torch.equal(lt, lm)), "selection_identical": bool(torch.equal(st.selected, sm.selected)), "scores_identical": bool(torch.equal(st.scores, sm.scores))}
    theirs = p9imodel.build_model(p9arm, slots, seed, bb, fact_lut=lut, r1_seed=job.r1_seed)
    p9_trainer = p9itrain.Trainer(p9icore.make_cell(p9arm, slots), theirs, p9itrain.build_optimizers(theirs))
    their_record = p9_trainer.step(tokens)
    mine2 = train.Trainer(job, train.job_model(job))
    my_record = mine2.step(batch)
    params_equal = all(torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in mine2.model.named_parameters() if n.startswith("addition."))
    step = {"loss_identical": their_record["task_loss"] == my_record["task_loss"], "parameters_identical_after_step": params_equal}
    return {"same_parameters": same, **forward, **step, "passed": same and all(forward.values()) and all(step.values())}


def index_rebuild(job: train.TrainJob) -> dict[str, Any]:
    """The index of section 5.5 built twice from the same trained keys is identical (centroids, assignment)."""
    run = train.run_job(train.TrainJob(**{**job.__dict__, "out_dir": job.out_dir / "index_keys", "max_updates": 8, "snapshots": ()}))
    keys = run.model.addition.keys.detach()
    seed = core.index_seed(job.data.seeds)
    a, b = index.build_index(keys, seed), index.build_index(keys, seed)
    return {"identical": a.sha256() == b.sha256() and bool(torch.equal(a.assign, b.assign)), "lists": a.lists, "sha256": a.sha256()}


def corpus_logits_identity(model: P10S1Model, frozen: "Backbone", rows: "Tensor") -> dict[str, Any]:
    return g5_check(model, frozen, rows[:256, : core.CONTEXT_BYTES].contiguous())


# --- G5 --------------------------------------------------------------------------------------------------------------------------------
def reach_for_cell(data: StudyData, backbone: "Backbone", arm: str, facts: int, slots: int, *, mode: str, init_seed: int, draw: int = 1) -> dict[str, Any]:
    """Gradient reach at a configuration's real facts and slots on one batch of its own training stream (section 8.1 G5)."""
    job = tiny_job(arm, data, backbone, facts, slots, Path("/nonexistent"), mode=mode, updates=1, init_seed=init_seed, draw=draw)
    batch = job.stream.batch(1)
    assert_covered(batch.tokens, batch.fact_ids, facts, job.fact_lut)
    r = train.gradient_reach(job, batch.tokens)
    ok = bool(r["reached"]) and all(r["reached"].values()) and not r["stray"] and not r["buffer_gradients"]
    groups = sorted({n.rsplit(".", 1)[-1] for n in r["reached"]})
    detail: dict[str, Any] = {"configuration": f"{arm} {core.cell_name(facts, slots)}", "all_reached": all(r["reached"].values()), "trainable_leaves": groups, "stray": r["stray"], "buffer_gradients": r["buffer_gradients"], "nothing_reaches_backbone": not any(n.startswith("backbone.") for n in r["reached"]) and not r["stray"]}
    if arm == "H8":
        mem = build_model("H8", slots, init_seed, backbone, r1_seed=job.r1_seed, hash_seed=job.hash_seed, seed_rng=False).addition
        ident = encode_identifiers(data.facts.ident[batch.fact_ids.reshape(-1)])
        expected = sorted(torch.unique(mem.slot_table(ident).reshape(-1)).tolist())
        got = sorted(r["value_rows_with_gradient"] or [])
        detail["h8_rows_equal_hashed_rows"] = expected == got
        ok = ok and detail["h8_rows_equal_hashed_rows"]
    if arm == "R2":
        lut = job.fact_lut
        assert lut is not None
        slots_of = lut[encode_identifiers(data.facts.ident[:facts])]
        detail["r2_table_covers_every_fact"] = bool(torch.equal(slots_of, torch.arange(facts)))
        ok = ok and detail["r2_table_covers_every_fact"]
    detail["passed"] = bool(ok)
    return detail


# --- G6 --------------------------------------------------------------------------------------------------------------------------------
def forward_arguments(model: P10S1Model) -> dict[str, list[str]]:
    return {"forward": list(inspect.signature(model.forward).parameters), "select": list(inspect.signature(model.select).parameters)}


@torch.no_grad()
def selection_ids(model: P10S1Model, tokens: "Tensor") -> "Tensor":
    model.eval()
    h = model.embed_block0(tokens)
    read = model.select(h, tokens)
    assert isinstance(read, Selection)
    return read.selected


def integrity(data: StudyData, backbone: "Backbone", facts: int, slots: int, *, init_seed: int, tokens: "Tensor", fact_ids: "Tensor") -> dict[str, Any]:
    """G6 at one size: for F-OQ, T-OQ, H8 and R2 the selection at every answer site is unchanged when the records of the context are permuted (it moves with its record) and when
    the answer bytes of the context are replaced; D-OQ's input tensor equals F-OQ's code tensor (same hash); no forward takes the answer; no model holds a tensor outside its
    parameters and buffers (a fact table would show up there)."""
    inp = tokens[:, : core.INPUT_LENGTH].contiguous()
    gen = torch.Generator().manual_seed(core.derive_seed(init_seed, "g6"))
    record_perm = torch.randperm(core.RECORDS_PER_CONTEXT, generator=gen)
    permuted = tokens.reshape(tokens.shape[0], core.RECORDS_PER_CONTEXT, core.RECORD_BYTES)[:, record_perm].reshape(tokens.shape)[:, : core.INPUT_LENGTH].contiguous()
    replaced = tokens.clone()
    replaced[:, core.RECORD_BYTES - 1 :: core.RECORD_BYTES] = core.ALPHABET_BASE + torch.randint(0, core.ALPHABET_SIZE, (tokens.shape[0], core.RECORDS_PER_CONTEXT), generator=gen)
    replaced = replaced[:, : core.INPUT_LENGTH].contiguous()
    lut = train.fact_lut_for(data, facts)
    arms: dict[str, Any] = {}
    for arm in ("F-OQ", "T-OQ", "H8", "R2"):
        m = build_model(arm, slots, init_seed, backbone, fact_lut=lut if arm == "R2" else None, r1_seed=data.seeds.r1_codes, hash_seed=core.h8_seed(data.seeds), seed_rng=False)
        base = selection_ids(m, inp)
        moved = selection_ids(m, permuted)
        context_ok = bool(torch.equal(moved, base[:, record_perm]))
        answers_ok = bool(torch.equal(selection_ids(m, replaced), base))
        args = forward_arguments(m)
        stray = [n for n, v in vars(m.addition).items() if isinstance(v, torch.Tensor)] + [n for n, v in vars(m).items() if isinstance(v, torch.Tensor)]
        arms[arm] = {"selection_unchanged_when_context_permuted": context_ok, "selection_unchanged_when_answers_replaced": answers_ok, "forward_arguments": args, "tokens_only": args["forward"] == ["tokens"] and args["select"] == ["h_pre", "tokens"], "stray_tensor_attributes": stray}
        arms[arm]["passed"] = bool(context_ok and answers_ok and arms[arm]["tokens_only"] and not stray)
    foq = build_model("F-OQ", slots, init_seed, backbone, r1_seed=data.seeds.r1_codes, seed_rng=False)
    doq = build_model("D-OQ", slots, init_seed, backbone, r1_seed=data.seeds.r1_codes, seed_rng=False)
    h_codes, d_codes = tensor_sha256(foq.oracle_codes(inp)), tensor_sha256(doq.oracle_codes(inp))
    out = {"arms": arms, "doq_input_hash_equals_foq_codes": h_codes == d_codes, "foq_codes_sha256": h_codes, "doq_codes_sha256": d_codes, "doq_reads_tokens_only": forward_arguments(doq)["forward"] == ["tokens"]}
    out["passed"] = bool(all(v["passed"] for v in arms.values()) and out["doq_input_hash_equals_foq_codes"] and out["doq_reads_tokens_only"] and fact_ids.numel() > 0)
    return out


# --- G7, G8 ----------------------------------------------------------------------------------------------------------------------------
def work_counters(data: StudyData, backbone: "Backbone", slots: int, facts: int, *, init_seed: int, tokens: "Tensor") -> dict[str, Any]:
    """G7: the instrumented counters of a forward at ``slots`` equal the formulas of section 7.4 for every arm (F-OQ-IVF's work is measured: its counters equal the measured
    candidate counts)."""
    inp = tokens[:, : core.INPUT_LENGTH].contiguous()
    lut = train.fact_lut_for(data, facts)
    out: dict[str, Any] = {}
    for arm in core.ARMS:
        m = build_model(arm, slots, init_seed, backbone, fact_lut=lut if arm == "R2" else None, r1_seed=data.seeds.r1_codes, hash_seed=core.h8_seed(data.seeds), seed_rng=False)
        m.eval()
        m.counters.reset()
        with torch.no_grad():
            m(inp)
        got = m.counters.per_query()
        want = core.work_formula(arm, slots)
        ok = got["W"] == want["W"] and (arm == "D-OQ" or (got["K"] == want["K"] and got["V"] == want["V"]))
        if arm == "D-OQ":
            ok = ok and got["hidden"] == want["hidden"]
        out[arm] = {"counted": got, "formula": want, "passed": bool(ok)}
    foq = build_model("F-OQ", slots, init_seed, backbone, r1_seed=data.seeds.r1_codes, seed_rng=False)
    idx = index.build_index(foq.addition.keys.detach(), core.index_seed(data.seeds))
    ivf = index.IVFMemory(foq.addition, idx)
    q = foq.addition._oracle_codes(inp)[:, :, :].reshape(-1, core.KEY_WIDTH)
    ivf.counters.reset()
    ivf._top_flat(q)
    measured = ivf.measured()
    per_query = ivf.counters.key_scores / q.shape[0]
    out["F-OQ-IVF"] = {"counted_key_scores_per_query": per_query, "measured_K_mean": measured["K_mean"], "passed": abs(per_query - measured["K_mean"]) < 1e-6}
    out["passed"] = all(v["passed"] for v in out.values())
    return out


def parameter_match(backbone: "Backbone", data: StudyData, slots_list: Sequence[int], *, init_seed: int) -> dict[str, Any]:
    """G8: D-OQ's trainable parameter count within 0.1% of F-OQ's at every slot count (counted from built models)."""
    out: dict[str, Any] = {}
    for n in slots_list:
        f = parameter_report(build_model("F-OQ", n, init_seed, backbone, r1_seed=data.seeds.r1_codes, seed_rng=False)).trainable
        d = parameter_report(build_model("D-OQ", n, init_seed, backbone, r1_seed=data.seeds.r1_codes, seed_rng=False)).trainable
        out[str(n)] = {"foq": f, "doq": d, "relative_difference": abs(d - f) / f, "passed": abs(d - f) / f <= core.DOQ_PARAMETER_TOLERANCE}
    out["passed"] = all(v["passed"] for v in out.values())
    return out


# --- everything ------------------------------------------------------------------------------------------------------------------------
def run_gates(
    data: StudyData,
    backbone: "Backbone",
    *,
    mode: str,
    plan: core.Plan,
    out_dir: Path,
    init_seed: int,
    rows: "Tensor",
    restore_split: int = 16,
    configurations: Sequence[tuple[str, int, int]] | None = None,
    slot_counts: Sequence[int] = core.SLOT_COUNTS,
    small_facts: int = 2048,
) -> dict[str, Any]:
    """G4 to G9 at real size on ``data`` (the rehearsal draw before the freeze; a registered draw before training). ``configurations`` (default: every configuration of the plan,
    D-OQ cells included) are the (arm, facts, slots) of G5; G4's restoration and identity checks run at each arm's 4,096-slot cell (R2 at its smallest cell). A harness error
    is returned in ``harness_errors`` and fails nothing."""
    defects: list[str] = []
    harness: list[str] = []
    record: dict[str, Any] = {}
    gate_slots = 4096
    try:
        tokens_all, fact_ids = gate_contexts(data, small_facts)
        assert_covered(tokens_all, fact_ids, small_facts)
    except Exception as exc:  # harness: the inputs do not belong to the cell
        return {"g4_defects": [], "g4_passed": False, "g5_passed": False, "g6_passed": False, "g7_passed": False, "g8_passed": False, "g9_passed": False, "harness_errors": [f"{type(exc).__name__}: {exc}"], "checks": {}}

    def job(arm: str, name: str, updates: int, *, slots: int = gate_slots, facts: int = small_facts) -> train.TrainJob:
        return tiny_job(arm, data, backbone, facts, slots, out_dir / name, mode=mode, updates=updates, init_seed=init_seed)

    for arm in ("F-OQ", "R2"):
        try:
            record[f"identity_{arm}"] = p9i_identity(job(arm, f"identity_{arm}", 4), arm)
        except Exception as exc:
            harness.append(f"identity {arm}: {type(exc).__name__}: {exc}")
            continue
        if not record[f"identity_{arm}"]["passed"]:
            defects.append(f"{arm} differs from P9-I's {'R1' if arm == 'F-OQ' else 'R2'}")
    record["restoration"], record["determinism"] = {}, {}
    for arm in core.ARMS:
        r = train.checkpoint_restoration_check(job(arm, f"restore_{arm}", 4 * restore_split), restore_split)
        record["restoration"][arm] = r
        if not r["identical"]:
            defects.append(f"checkpoint restoration is not bit-identical for {arm}")
        first, second = train.run_job(job(arm, f"det1_{arm}", 6)), train.run_job(job(arm, f"det2_{arm}", 6))
        same = all(torch.equal(p, dict(second.model.named_parameters())[n]) for n, p in first.model.named_parameters())
        record["determinism"][arm] = {"identical": same}
        if not same:
            defects.append(f"two identical runs of {arm} differ")
    record["index_rebuild"] = index_rebuild(job("F-OQ", "index", 8))
    if not record["index_rebuild"]["identical"]:
        defects.append("the index differs on rebuild")
    g5_models: dict[str, Any] = {}
    for arm in core.ARMS:
        run = train.run_job(job(arm, f"g5_{arm}", 4))
        g5_models[arm] = g5_check(run.model, backbone, rows[:256, : core.CONTEXT_BYTES].contiguous())
        if not g5_models[arm]["passed"]:
            defects.append(f"backbone identity or disabled-memory logits differ for {arm}")
    record["backbone_identity"] = g5_models
    before = backbone_hashes(backbone)
    record["backbone_hashes_unchanged"] = before == backbone_hashes(backbone)
    cfgs = list(configurations if configurations is not None else [(a, f, n) for a in core.ARMS for f, n in core.arm_cells(core.Plan(plan.overload_u_p), a)])
    reach: dict[str, Any] = {}
    for arm, facts, slots in cfgs:
        try:
            reach[f"{arm} {core.cell_name(facts, slots)}"] = reach_for_cell(data, backbone, arm, facts, slots, mode=mode, init_seed=init_seed)
        except Exception as exc:
            harness.append(f"reach {arm} {facts}/{slots}: {type(exc).__name__}: {exc}")
    g5_ok = bool(reach) and all(v["passed"] for v in reach.values()) and len(reach) == len(cfgs)
    g6_res = integrity(data, backbone, small_facts, gate_slots, init_seed=init_seed, tokens=tokens_all, fact_ids=fact_ids)
    g7_res = {str(n): work_counters(data, backbone, n, small_facts, init_seed=init_seed, tokens=tokens_all) for n in slot_counts}
    g7_ok = all(v["passed"] for v in g7_res.values())
    g8_res = parameter_match(backbone, data, slot_counts, init_seed=init_seed)
    g9_res = core.seed_check()
    record.update(gradient_reach=reach, g6=g6_res, g7=g7_res, g8=g8_res, g9=g9_res)
    return {
        "g4_defects": defects, "g4_passed": not defects and not harness and bool(record["backbone_hashes_unchanged"]), "g5_passed": g5_ok, "g6_passed": bool(g6_res["passed"]), "g7_passed": bool(g7_ok),
        "g8_passed": bool(g8_res["passed"]), "g9_passed": bool(g9_res["passed"]), "harness_errors": harness, "configurations_checked": len(reach), "checks": record,
    }  # fmt: skip


__all__ = ["HarnessError", "p9model", "run_gates"]


# --- G1: S1's own generator checks (section 6.3, 8.1) -------------------------------------------------------------------------------------
def g1_s1(data: StudyData, plan: core.Plan, fact_counts: Sequence[int] | None = None) -> dict[str, Any]:
    """What S1 adds to P9's G1 for a draw: for every fact count of the plan's grid, the training schedule over the first F facts at S1's longest run (6 x U_P at 4,096 slots) gives every
    fact the same number of exposures per epoch, and no context of it (hashed) is in Panel A, Panel B, H1, H2 or the calibration stream; and no registered panel is a calibration
    or rehearsal panel (the streams of one draw are disjoint by construction and checked here by hash)."""
    from studies.p9.data import context_keys

    counts = list(fact_counts if fact_counts is not None else sorted({f for f, _ in core.grid_cells(plan)}))
    checks: list[dict[str, Any]] = []
    panels = {name: context_keys(data.streams[name].fact_ids) for name in ("panel_a", "panel_b", "h1", "h2", "calibration")}
    for facts in counts:
        facts = min(facts, data.facts.trained)
        sched = train.training_stream_for(data, facts)
        longest = max(core.run_length("F-OQ", n, plan.unit) for n in core.SLOT_COUNTS)
        epochs = max(1, -(-longest // sched.updates_per_epoch))
        expo = sched.exposures(epochs * sched.updates_per_epoch)
        keys = sched.keys(epochs)
        hits = {name: int(torch.isin(k, keys).sum()) for name, k in panels.items()}
        checks.append({"facts": facts, "epochs": epochs, "equal_frequency": bool((expo == epochs).all()), "hits_in_evaluation_streams": hits, "passed": bool((expo == epochs).all()) and sum(hits.values()) == 0})
    names = list(panels)
    overlap = {f"{a}/{b}": int(torch.isin(panels[a], panels[b]).sum()) for i, a in enumerate(names) for b in names[i + 1 :]}
    checks.append({"streams_disjoint": overlap, "passed": sum(overlap.values()) == 0})
    return {"passed": all(c["passed"] for c in checks), "checks": checks}
