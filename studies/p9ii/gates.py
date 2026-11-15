# ruff: noqa: E501
"""P9II gates G4, G5 and G6 (ADR-0019 section 9), runnable at real size on any seed set the mode allows (registered draws, calibration sets, rehearsal set,
test seeds). G1 (generator) and G2 (chance) are computed by ``stages`` from the draw's records and the controls; this module holds what needs a model.

G4 (determinism, checkpoint restoration, gradient reach for every arm on contexts the cell covers):
  * A0's forward and one training step are bit-identical to P9-I's W7;
  * every learned arm: checkpoint restoration bit-identical (model, optimizer, trainer state; A2's switch, A5-C's m and A4's schedule are inside it);
  * gradient reach of the training loss, and of each loss alone: L_addr reaches the query projection and the keys and nothing else; the answer loss reaches
    every trainable parameter; A2 phase 1 trains only wq and keys; A5-C's m has no gradient;
  * k(t) at updates 0, 1, T_A/2 and T_A equals the formula, and from T_A the read equals the standard top-8 read bit for bit;
  * A2's switch: trainable set changes at U_pre and every AdamW moment and counter is reset there;
  * A1-S's target stream is reproducible from its seed and independent of the fact;
  * L_addr uses all N scores (checked against a direct computation at 65,536); A4's read at k = N uses all N scores (checked against a direct computation at 16,384).
G5: backbone tensor hashes after training equal the frozen backbone's; with the addition disabled the logits equal the frozen backbone's bit for bit.
G6: no fact-identity input in any learned arm's forward; identical logits under changed tables.

A harness error (inputs that do not belong to the cell) raises ``HarnessError`` and is never recorded as a defect (the P9-I attempt-1 lesson).
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS
from studies.p9.data import StudyData
from studies.p9i import core as p9icore
from studies.p9i import model as p9imodel
from studies.p9i import train as p9itrain
from studies.p9i.stages import assert_covered, gate_contexts

from . import core, model, train

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

HarnessError = RuntimeError


def tiny_job(
    arm: str,
    data: StudyData,
    backbone: "Backbone",
    facts: int,
    out: Path,
    *,
    hyper: core.Hyper,
    updates: int,
    mode: str,
    slots: int = 4096,
    unit: int = core.UPDATES,
    init_seed: int,
    j: int = 0,
    stage: int = 1,
    diag_every: int = core.DIAG_EVERY,
    snapshots: tuple[int, ...] | None = None,
    max_updates: int | None = None,
    rehearsal_phase: str | None = None,
) -> train.TrainJob:
    """A job of ``arm`` at ``slots`` on the first ``facts`` facts of ``data``; ``updates`` is the cell's total (the gates run a few)."""
    cell = core.make_cell(arm, slots, stage=stage, draw=1, j=j)
    return train.TrainJob(
        cell=cell,
        hyper=hyper,
        updates=updates,
        mode=mode,
        data=data,
        stream=train.training_stream_for(data, facts),
        backbone=backbone,
        out_dir=out,
        init_seed=init_seed,
        r1_seed=data.seeds.r1_codes,
        target_seed=core.target_seed(data.seeds, j),
        stream_seed=core.stream_seed(data.seeds, j),
        unit=unit,
        stage=stage,
        diag_every=diag_every,
        snapshots=snapshots,
        max_updates=max_updates,
        rehearsal_phase=rehearsal_phase,
    )


def a0_identity(job: train.TrainJob) -> dict[str, Any]:
    """Arm A0 against P9-I's W7 with equal parameters and inputs: the parameters, the forward (every position), the selection and the read vector, and
    one training step (the loss and every parameter after the step), each ``torch.equal`` (bit for bit)."""
    bb, seed = job.backbone, job.init_seed
    batch = job.stream.batch(1)
    tokens = batch.tokens
    theirs = p9imodel.build_model("W7", job.cell.slots, seed, bb)
    mine = model.build_model("A0", job.cell.slots, seed, bb)
    same_parameters = all(torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in mine.named_parameters() if n.startswith("addition."))
    theirs.eval()
    mine.eval()
    with torch.no_grad():
        lt, st = theirs(tokens[:, :-1])
        lm, sm = mine(tokens[:, :-1])
        assert st is not None and sm is not None
        forward = {
            "logits_identical": bool(torch.equal(lt, lm)),
            "selection_identical": bool(torch.equal(st.selected, sm.selected)),
            "scores_identical": bool(torch.equal(st.scores, sm.scores)),
        }
    # one training step on the same batch
    theirs = p9imodel.build_model("W7", job.cell.slots, seed, bb)
    p9_trainer = p9itrain.Trainer(p9icore.make_cell("W7", job.cell.slots), theirs, p9itrain.build_optimizers(theirs))
    their_record = p9_trainer.step(tokens)
    fresh = train.Trainer(job, model.build_model("A0", job.cell.slots, seed, bb), train_probe(job))
    my_record = fresh.step(batch)
    params_equal = all(torch.equal(p, dict(theirs.named_parameters())[n]) for n, p in fresh.model.named_parameters() if n.startswith("addition."))
    step = {"loss_identical": their_record["task_loss"] == my_record["task_loss"], "parameters_identical_after_step": params_equal}
    return {"same_parameters": same_parameters, **forward, **step, "passed": same_parameters and all(forward.values()) and all(step.values())}


def train_probe(job: train.TrainJob) -> Any:
    from .diagnostics import build_probe

    return build_probe(job.data, int(job.stream.facts.shape[0]))


def schedule_checks(job_a4: train.TrainJob, job_a2: train.TrainJob) -> dict[str, Any]:
    """A4: k(t) at updates 0, 1, T_A/2 and T_A against the formula computed independently, and the k = 8 read equal to P9-I's standard read bit for bit.
    A2: the phase and the trainable set switch at U_pre and the AdamW state is reset there (every moment zero, every counter restarted)."""
    out: dict[str, Any] = {}
    bb = job_a4.backbone
    a4 = train.Trainer(job_a4, model.build_model("A4", job_a4.cell.slots, job_a4.init_seed, bb), train_probe(job_a4))
    k0, ta = int(a4.schedule.k0 or 0), int(a4.schedule.t_anneal or 0)
    expected = {t: (k0 if t == 0 else (8 if t >= ta else max(8, round(k0 * (8 / k0) ** (t / ta))))) for t in (0, 1, ta // 2, ta)}
    got = {t: a4.read_k(t) for t in expected}
    tokens = job_a4.stream.batch(1).tokens[:, :-1]
    std = model.build_model("A4", job_a4.cell.slots, job_a4.init_seed, bb, seed_rng=False)
    ref = p9imodel.build_model("W7", job_a4.cell.slots, job_a4.init_seed, bb, seed_rng=False)
    std.eval()
    ref.eval()
    std.set_read_k(a4.read_k(ta))
    with torch.no_grad():
        ls, ss = std(tokens)
        lr, sr = ref(tokens)
    assert ss is not None and sr is not None
    out["a4"] = {"k_expected": expected, "k_got": got, "k_matches_formula": expected == got, "final_read_is_standard_top8": bool(torch.equal(ls, lr) and torch.equal(ss.selected, sr.selected) and torch.equal(ss.scores, sr.scores)), "k0": k0, "t_anneal": ta}
    t2 = train.Trainer(job_a2, model.build_model("A2", job_a2.cell.slots, job_a2.init_seed, bb), train_probe(job_a2))
    u_pre = int(t2.schedule.u_pre or 0)
    phase1 = sorted(n.rsplit(".", 1)[-1] for n, _ in t2.named)
    for u in range(1, u_pre + 1):
        t2.step(job_a2.stream.batch(u))
    state_before = {id(p): dict(s) for p, s in t2.optimizers[0].state.items()}
    t2.step(job_a2.stream.batch(u_pre + 1))
    phase2 = sorted(n.rsplit(".", 1)[-1] for n, _ in t2.named)
    steps_after = [int(s["step"]) for s in t2.optimizers[0].state.values()]
    out["a2"] = {"u_pre": u_pre, "phase1_trainable": phase1, "phase2_trainable": phase2, "state_existed_before": bool(state_before), "counters_restarted": steps_after == [1] * len(steps_after) and len(steps_after) == len(phase2), "phase1_is_wq_and_keys": phase1 == ["keys", "wq"], "phase2_is_everything": phase2 == ["gate", "keys", "values", "wo", "wq"]}
    out["a2"]["passed"] = bool(out["a2"]["counters_restarted"] and out["a2"]["phase1_is_wq_and_keys"] and out["a2"]["phase2_is_everything"])
    out["passed"] = bool(out["a4"]["k_matches_formula"] and out["a4"]["final_read_is_standard_top8"] and out["a2"]["passed"])
    return out


def centre_and_stream_checks(job_c: train.TrainJob, tokens: "Tensor", fact_ids: "Tensor") -> dict[str, Any]:
    """A5-C: m is a buffer without gradient, unchanged by an evaluation forward. A1-S: the target stream is reproducible from its seed, changes with the seed
    and does not depend on the facts."""
    m = model.build_model("A5-C", job_c.cell.slots, job_c.init_seed, job_c.backbone)
    mem = m.addition
    assert isinstance(mem, model.IIMemory)
    mem.init_centre(train.initial_centre_rows(m, job_c.stream))
    centre = dict(mem.named_buffers())["centre"]
    before = centre.clone()
    m.eval()
    with torch.no_grad():
        m(tokens[:, :-1])
    unchanged = bool(torch.equal(before, centre))
    seed = job_c.stream_seed
    a, b = model.a1s_targets(seed, 5, 4096), model.a1s_targets(seed, 5, 4096)
    other = model.a1s_targets(seed + 1, 5, 4096)
    return {
        "centre_is_buffer": "centre" in dict(mem.named_buffers()) and "centre" not in dict(mem.named_parameters()),
        "centre_requires_grad": bool(centre.requires_grad),
        "centre_frozen_in_eval": unchanged,
        "a1s_reproducible": bool(torch.equal(a, b)),
        "a1s_depends_on_seed": not bool(torch.equal(a, other)),
        "a1s_independent_of_fact": bool(torch.equal(model.a1s_targets(seed, 5, 4096), model.a1s_targets(seed, 5, 4096))) and fact_ids.numel() > 0,
        "passed": unchanged and not bool(centre.requires_grad) and bool(torch.equal(a, b)) and not bool(torch.equal(a, other)),
    }


def full_score_checks(seed: int = 910999) -> dict[str, Any]:
    """L_addr against a direct float64 computation at 65,536 slots, and A4's read at k = N against a direct computation at 16,384 slots."""
    g = torch.Generator().manual_seed(seed)
    n = 65536
    keys = torch.randn(n, core.KEY_WIDTH, generator=g)
    q = F.normalize(torch.randn(32, core.KEY_WIDTH, generator=g), dim=-1)
    targets = torch.randint(0, n, (32,), generator=g)
    mine = model.address_loss(q, keys, targets)
    scores = (q.double() @ F.normalize(keys, dim=-1, eps=EPS).double().T) / core.TAU_ADDR
    direct = float((torch.logsumexp(scores, dim=1) - scores[torch.arange(32), targets]).mean())
    addr_ok = abs(float(mine) - direct) < 1e-4
    n2 = 16384
    keys2 = torch.randn(n2, core.KEY_WIDTH, generator=g)
    values = torch.randn(n2, core.HIDDEN_WIDTH, generator=g)
    q2 = F.normalize(torch.randn(16, core.KEY_WIDTH, generator=g), dim=-1)
    s2 = (q2 @ F.normalize(keys2, dim=-1, eps=EPS).T) / core.TEMPERATURE
    top, ids = s2.topk(n2, dim=-1)
    weights = top.softmax(-1)
    full = torch.zeros_like(weights).scatter(1, ids, weights)
    wide = full @ values
    direct2 = s2.softmax(-1) @ values
    read_ok = bool(torch.allclose(wide, direct2, atol=1e-5)) and bool(torch.allclose(full.sum(-1), torch.ones(16)))
    return {"address_loss_all_n_scores": {"slots": n, "model": float(mine), "direct": direct, "passed": addr_ok}, "a4_read_k_equals_n": {"slots": n2, "passed": read_ok}, "passed": bool(addr_ok and read_ok)}


def reach_checks(job: train.TrainJob, tokens: "Tensor", fact_ids: "Tensor") -> dict[str, Any]:
    """Gradient reach of the training loss and of each loss alone, for the arm of ``job``, on covered contexts."""
    arm = job.cell.arm
    out: dict[str, Any] = {}
    train_reach = train.gradient_reach(job, tokens, fact_ids, "training")
    trainable_ok = all(train_reach["reached"].values()) and not train_reach["stray"] and not train_reach["buffer_gradients"]
    out["training"] = {"all_reached": all(train_reach["reached"].values()), "trainable": train_reach["trainable"], "stray": train_reach["stray"], "buffer_gradients": train_reach["buffer_gradients"]}
    ok = bool(trainable_ok)
    if arm in core.TARGET_ARMS:
        r = train.gradient_reach(job, tokens, fact_ids, "addr", phase=2)
        reached = sorted(n.rsplit(".", 1)[-1] for n, v in r["reached"].items() if v)
        out["address_loss"] = {"reached": reached, "stray": r["stray"]}
        ok = ok and reached == ["keys", "wq"] and not r["stray"]
    if arm == "A5-D":
        r = train.gradient_reach(job, tokens, fact_ids, "div")
        reached = sorted(n.rsplit(".", 1)[-1] for n, v in r["reached"].items() if v)
        out["diversity_loss"] = {"reached": reached, "stray": r["stray"]}
        ok = ok and reached == ["wq"] and not r["stray"]
    if arm == "A2":
        r1 = train.gradient_reach(job, tokens, fact_ids, "training", phase=1)
        names = sorted(n.rsplit(".", 1)[-1] for n in r1["reached"])
        out["phase1"] = {"trainable": names, "all_reached": all(r1["reached"].values()), "stray": r1["stray"]}
        ok = ok and names == ["keys", "wq"] and all(r1["reached"].values()) and not r1["stray"]
    out["passed"] = bool(ok)
    return out


def run_g4_g5_g6(
    data: StudyData,
    backbone: "Backbone",
    *,
    mode: str,
    facts: int,
    restore_split: int,
    out_dir: Path,
    init_seed: int,
    rows: "Tensor",
    hyper: core.Hyper | None = None,
    unit: int = core.UPDATES,
) -> dict[str, Any]:
    """Every model-dependent gate at the cell size of 4,096 slots on ``facts`` facts (2,048 at real size). Returns ``g4_defects`` (strings), the per-check
    records and ``g4_passed`` / ``g5_passed`` / ``g6_passed``. The gates train a few updates per check on the draw's own training data (so on a rehearsal
    draw they run before the freeze, on the registered draw before training)."""
    hyper = hyper or core.Hyper(u_pre=float(restore_split), k0_fraction=0.125, lambda_=1.0, mu=0.1)
    defects: list[str] = []
    tokens_all, fact_ids = gate_contexts(data, facts)
    assert_covered(tokens_all, fact_ids, facts)  # a harness error, never a defect
    common: dict[str, Any] = {"hyper": hyper, "mode": mode, "init_seed": init_seed, "unit": unit}

    def job(arm: str, name: str, updates: int) -> train.TrainJob:
        return tiny_job(arm, data, backbone, facts, out_dir / name, updates=updates, **common)

    record: dict[str, Any] = {}
    record["a0_identity"] = a0_identity(job("A0", "a0", 4))
    if not record["a0_identity"]["passed"]:
        defects.append("arm A0 differs from P9-I's W7")
    record["schedules"] = schedule_checks(job("A4", "sched_a4", 4 * restore_split), job("A2", "sched_a2", 4 * restore_split))
    if not record["schedules"]["passed"]:
        defects.append("A4 schedule or A2 switch check failed")
    record["centre_and_streams"] = centre_and_stream_checks(job("A5-C", "centre", 4), tokens_all, fact_ids)
    if not record["centre_and_streams"]["passed"]:
        defects.append("A5-C centre or A1-S stream check failed")
    record["full_scores"] = full_score_checks()
    if not record["full_scores"]["passed"]:
        defects.append("all-N-score check failed")
    record["gradient_reach"], record["restoration"] = {}, {}
    for arm in core.ARMS:
        j = job(arm, f"reach_{arm}", 4 * restore_split)
        record["gradient_reach"][arm] = reach_checks(j, tokens_all, fact_ids)
        if not record["gradient_reach"][arm]["passed"]:
            defects.append(f"gradient reach failed for {arm}")
    for arm in core.LEARNED_ARMS:
        j = job(arm, f"restore_{arm}", 4 * restore_split)
        record["restoration"][arm] = train.checkpoint_restoration_check(j, restore_split)
        if not record["restoration"][arm]["identical"]:
            defects.append(f"checkpoint restoration is not bit-identical for {arm}")
    first = train.run_job(job("A0", "determinism_1", 6))
    second = train.run_job(job("A0", "determinism_2", 6))
    record["determinism"] = {"identical": all(torch.equal(p, dict(second.model.named_parameters())[n]) for n, p in first.model.named_parameters())}
    if not record["determinism"]["identical"]:
        defects.append("two identical runs differ")
    # G5 after training, for every learned arm
    g5: dict[str, Any] = {}
    sample = rows[:256, : core.CONTEXT_BYTES].contiguous()
    for arm in core.ARMS:
        run = train.run_job(job(arm, f"g5_{arm}", 4))
        g5[arm] = model.g5_check(run.model, backbone, sample)
    g6 = model.g6_check(backbone, 4096, init_seed, tokens_all[:, : core.INPUT_LENGTH], torch.arange(10), torch.arange(10).flip(0))
    return {
        "g4_defects": defects,
        "g4_passed": not defects,
        "g5": g5,
        "g5_passed": all(v["passed"] for v in g5.values()),
        "g6": g6,
        "g6_passed": bool(g6["passed"]),
        "checks": record,
    }
