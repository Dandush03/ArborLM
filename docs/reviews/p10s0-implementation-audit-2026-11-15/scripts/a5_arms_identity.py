"""Arms are studies.p9ii's: forward at init and K training steps through S0's run_job against studies.p9ii's own Trainer (driven by this script),
at 2K/4K (P9-II Stage 1) and 8K/16K (Stage 2) and 8K/4K; WX only changes wq; WX with W_X = [0 | W7] gives W7's query and logits; A2's U_pre and
AdamW reset; the read swap recomputed independently. Tiny sizes, synthetic backbone, S0 unit-test seeds (p10s0-test-7: base 920701) only.

Usage (inside the audited worktree): PYTHONPATH=<worktree> uv run --locked python <this>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import math
import tempfile
from pathlib import Path

import torch
import torch.nn.functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9.data import DataSizes, build_study_data
from studies.p9i.evaluate import stream_for
from studies.p9ii import core as p9iicore
from studies.p9ii import model as p9iimodel
from studies.p9ii import train as p9iitrain
from studies.p9ii.diagnostics import build_probe
from studies.p10s0 import core, evaluate, model, train

train.configure()  # single-thread deterministic CPU, as every registered worker (stages.main -> train.configure)
out = {"torch_threads": torch.get_num_threads()}
SPEC = core.test_set(7)
assert SPEC.base == 920701 and SPEC.base + 99 <= 920999
torch.manual_seed(0)
backbone = controls.synthetic_backbone()
g = torch.Generator().manual_seed(12)
corpus = bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())
INIT = SPEC.base + 41
FACTS = 128
UNIT = 8


def data_for(real):
    return build_study_data(SPEC.seeds(real), corpus, sizes=DataSizes(main_trained=FACTS, unseen=64, lane_d_per_set=128))


def p9ii_trainer(arm, slots, stage, data, hyper):
    """P9-II's own Trainer on a P9-II cell (no S0 code on this side)."""
    cell = p9iicore.make_cell(arm, slots, stage=stage, draw=1, j=0)
    stream = p9iitrain.training_stream_for(data, FACTS) if hasattr(p9iitrain, "training_stream_for") else train.training_stream_for(data, FACTS)
    job = p9iitrain.TrainJob(cell=cell, hyper=hyper, updates=p9iicore.stage_updates(stage, UNIT), mode="calibration", data=data, stream=stream, backbone=backbone, out_dir=Path(tempfile.mkdtemp()),
                             init_seed=INIT, r1_seed=data.seeds.r1_codes, target_seed=SPEC.base + 40, stream_seed=0, unit=UNIT, stage=stage, snapshots=(), max_updates=None, diag_every=10**9)
    m = p9iimodel.build_model(arm, slots, INIT, backbone, r1_seed=data.seeds.r1_codes)
    return p9iitrain.Trainer(job, m, build_probe(data, FACTS)), m, stream


def s0_run(arm, ct, data, hyper, steps):
    cell = core.make_cell(arm, ct, "Q1", 1, 0, "TEST-")
    job = train.Job(cell=cell, mode="dry", data=data, stream=train.training_stream_for(data, FACTS), backbone=backbone, out_dir=Path(tempfile.mkdtemp()) / arm, init_seed=INIT,
                    r1_seed=data.seeds.r1_codes, target_seed=SPEC.base + 40, hyper=hyper, unit=UNIT, snapshots=(), max_updates=steps, diag_every=10**9)
    return train.run_job(job)


HY = core.HYPER._replace(u_pre=2048.0)  # registered U_pre; at UNIT=8 it scales to 2 (stage 1) and 8 (stage 2)
STEPS = 6  # < the cell's 8 updates at UNIT = 8 (2K/4K) so both sides take the same number of steps (failed attempt 05: 12 > 8)
res = {}
for ct, slots, stage in (("2K/4K", 4096, 1), ("8K/16K", 16384, 2)):
    data = data_for(2048 if ct == "2K/4K" else 8192)
    for arm in ("A0", "A1", "A2", "A5-D", "A6", "A7"):
        if arm == "A7" and ct == "8K/16K":
            pass
        tr, m9, stream = p9ii_trainer(arm, slots, stage, data, HY)
        tokens = stream.batch(1).tokens[:, : core.INPUT_LENGTH]
        m0 = model.build_model(arm, slots, INIT, backbone, r1_seed=data.seeds.r1_codes)
        m0.eval(); m9.eval()
        with torch.no_grad():
            fwd = bool(torch.equal(m0(tokens)[0], m9(tokens)[0]))
        m9.train()
        losses9 = []
        tr.anchor = {n: p.detach().clone() for n, p in tr.named}
        for u in range(1, STEPS + 1):
            losses9.append(tr.step(stream.batch(u))["task_loss"])
        ex = s0_run(arm, ct, data, HY, STEPS)
        p9 = dict(m9.named_parameters())
        params = all(torch.equal(p, p9[n]) for n, p in ex.model.named_parameters())
        losses = [r["task_loss"] for r in ex.updates] == losses9
        sched = (ex.trainer.schedule.u_pre, tr.schedule.u_pre)
        res[f"{arm}@{ct}"] = {"forward_bit_identical": fwd, "params_after_%d_steps_bit_identical" % STEPS: params, "task_losses_identical": losses, "u_pre_s0_vs_p9ii": sched}
out["identity_vs_p9ii"] = res

# 8K/4K: P9-II has no such cell; S0 builds stage-2 schedule at 4,096 slots. Check what S0 builds and that A1/A2 are refused.
data8 = data_for(8192)
r84 = {}
for arm in ("A0", "A5-D", "A6"):
    ex = s0_run(arm, "8K/4K", data8, HY, 4)
    r84[arm] = {"slots": ex.model.slots, "trainer_injection": ex.trainer.injection is not None, "updates_of_cell": core.CELLTYPES["8K/4K"].updates(UNIT)}
for arm in ("A1", "A2"):
    try:
        s0_run(arm, "8K/4K", data8, HY, 1)
        r84[arm] = "NOT REFUSED"
    except ValueError as e:
        r84[arm] = "refused: " + str(e)[:80]
out["8K/4K"] = r84

# A2: switch at U_pre, trainable set and AdamW reset (P9-II's Trainer driven through S0's Job)
data2 = data_for(2048)
ex = s0_run("A2", "2K/4K", data2, HY, 2)
t = ex.trainer
ph1 = sorted(n.split(".")[-1] for n, _ in t.named)
t.step(t.job.stream.batch(3))
ph2 = sorted(n.split(".")[-1] for n, _ in t.named)
steps_after = sorted({int(s["step"]) for o in t.optimizers for s in o.state.values()})
out["A2_switch"] = {"u_pre_at_unit8_stage1": t.schedule.u_pre, "phase1_trainable": ph1, "phase2_trainable": ph2, "adam_step_counters_after_first_phase2_update": steps_after,
                    "registered_u_pre_2K4K": core.schedule_for("A2", "2K/4K").u_pre, "registered_u_pre_8K16K": core.schedule_for("A2", "8K/16K").u_pre}

# WX: only wq differs from the base arm's model; zero-padded W7 projection gives W7's query and logits bit for bit
wx = {}
for base in ("A5-D", "A1"):
    mb = p9iimodel.build_model(base, 4096, INIT, backbone, seed_rng=False)
    mx = model.build_model(f"WX-{base}", 4096, INIT, backbone, seed_rng=False)
    sb, sx = mb.state_dict(), mx.state_dict()
    diff_keys = sorted(k for k in sb.keys() | sx.keys() if k not in sb or k not in sx or sb[k].shape != sx[k].shape or not torch.equal(sb[k], sx[k]))
    tokens = train.training_stream_for(data2, FACTS).batch(1).tokens[:, : core.INPUT_LENGTH]
    with torch.no_grad():
        mx.addition.wq.copy_(torch.cat([torch.zeros(16, 2048 - 224), mb.addition.wq], dim=1))
        mb.eval(); mx.eval()
        h = mb.embed_block0(tokens)
        q_b, q_x = mb.answer_queries(h, tokens), mx.answer_queries(h, tokens)
        lb, lx = mb(tokens)[0], mx(tokens)[0]
    # own full-window feature build: positions 8r+6, zero before position 0
    pos = torch.tensor([8 * r + 6 for r in range(8)])
    feats = []
    for t_ in pos.tolist():
        cols = [h[:, j] if j >= 0 else torch.zeros_like(h[:, 0]) for j in range(t_ - 63, t_ + 1)]
        feats.append(torch.cat(cols, dim=-1))
    feats = torch.stack(feats, 1)
    mx2 = model.build_model(f"WX-{base}", 4096, INIT, backbone, seed_rng=False)
    with torch.no_grad():
        mine_q = F.normalize(F.linear(feats, mx2.addition.wq), dim=-1, eps=1e-12).reshape(-1, 16)
        theirs_q = mx2.answer_queries(h, tokens).reshape(-1, 16)
    wx[base] = {"state_dict_keys_that_differ_from_base": diff_keys, "wq_shape": list(mx2.addition.wq.shape), "query_bit_identical_with_padded_w7": bool(torch.equal(q_b, q_x)),
                "logits_bit_identical_with_padded_w7": bool(torch.equal(lb, lx)), "own_full_window_query_max_abs_diff": float((mine_q - theirs_q).abs().max()),
                "wq_init_equals_matrix_seed_plus_3000": bool(torch.equal(mx2.addition.wq, __import__("arborlm.pilot_model", fromlist=["_matrix"])._matrix(INIT + 3000, 16, 2048)))}
    # one training step of WX-X uses X's loss terms: losses present
    ex = s0_run(f"WX-{base}", "2K/4K", data2, HY, 2)
    wx[base]["aux_loss_present"] = {"div": ex.updates[0]["diversity_loss"] is not None, "addr": ex.updates[0]["address_loss"] is not None}
out["WX"] = wx

# read swap: independent implementation against evaluate.read_swap on a model trained a few steps
ex = s0_run("A0", "2K/4K", data2, HY, 16)
m = ex.model
perm = evaluate.swap_permutation(data2, FACTS, SPEC.swap_seed(2048))
answers = evaluate.fact_answers(data2, FACTS)
ALPH = torch.tensor(p9core.ALPHABET)
rs = {}
for panel in ("A", "B"):
    impl = evaluate.read_swap(m, data2, FACTS, panel, perm)
    st = stream_for(data2, FACTS, core.PANEL_STREAM[panel])
    keep = (st.fact_ids < FACTS).all(dim=1)
    tok = st.tokens[keep][:, : core.INPUT_LENGTH]
    ids = st.fact_ids[keep]
    ans = st.answer_targets()[keep]
    m.eval()
    with torch.no_grad():
        h = m.embed_block0(tok)
        delta = m.memory_delta(h, m.select(h, tok))
        sites = p9iimodel.SITES
        own = m.finish(h, delta)
        read_of = {}
        for c in range(tok.shape[0]):
            for r in range(8):
                read_of[int(ids[c, r])] = delta[c, sites[r]].clone()
        correct = used = still = 0
        for c in range(tok.shape[0]):
            for r in range(8):
                f = int(ids[c, r])
                a = int(ans[c, r])
                lo = own[c, sites[r]][ALPH]
                ok = bool(lo[a] >= lo.max()) and int((lo == lo.max()).sum()) == 1  # strict: correct only if the answer is the unique arg-max
                d2 = delta[c : c + 1].clone()
                d2[0, sites[r]] = read_of[int(perm[f])]
                ls = m.finish(h[c : c + 1], d2)[0, sites[r]][ALPH]
                s = bool(ls[a] >= ls.max())  # ties count as still the answer
                correct += ok
                still += s
                used += ok and not s
    n = tok.shape[0] * 8
    rs[panel] = {"impl": {k: impl[k] for k in ("facts", "correct", "a_use_count", "swapped_still_answer")}, "auditor": {"facts": n, "correct": correct, "a_use_count": used, "swapped_still_answer": still}}
out["read_swap"] = rs
out["perm_checks"] = {"no_fixed_point": bool((perm != torch.arange(FACTS)).all()), "answers_differ": bool((answers[perm] != answers).all()), "is_permutation": bool(torch.equal(perm.sort().values, torch.arange(FACTS)))}
print(json.dumps(out, indent=1, default=str))
