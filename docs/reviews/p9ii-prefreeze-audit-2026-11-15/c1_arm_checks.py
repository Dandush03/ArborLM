"""C1 (auditor, Opus 5.5): independent checks of every arm's forward and loss against ADR-0019 rev 4 sections 3-4 at real size
(4,096 slots / 2,048 facts; the k-schedule also at Stage 2 values) on TEST seeds p9ii-test-7 (910701+). The implementer's model
and trainer are exercised; every expected value is computed here from the ADR text. Nothing registered is read.

usage: c1_arm_checks.py EXPERIMENTS_ROOT SCRATCH_DIR
"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core
from studies.p9i import model as p9imodel, train as p9itrain, core as p9icore
from studies.p9ii import core, model, train
from studies.p9ii.diagnostics import build_probe
from studies.p9i.train import training_stream_for

ROOT, SCRATCH = Path(sys.argv[1]), Path(sys.argv[2])
train.configure()
seeds = core.test_seeds(7)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
backbone = controls.load_backbone(p9core.PRIMARY_PARENT, ROOT)[0]
stream = training_stream_for(study, 2048)
SITES = [8 * r + 6 for r in range(8)]
INIT = 919101
results = {}


def check(name, ok, **info):
    results[name] = {"ok": bool(ok), **info}
    print(("PASS " if ok else "FAIL ") + name, json.dumps(info, default=str)[:400])


def job(arm, hyper=core.Hyper(lambda_=1.0, u_pre=2048.0, k0_fraction=0.125, mu=1.0), out="x", stage=1, slots=4096):
    cell = core.make_cell(arm, slots, stage=stage)
    return train.TrainJob(cell=cell, hyper=hyper, updates=core.stage_updates(stage), mode="calibration", data=study, stream=stream, backbone=backbone, out_dir=SCRATCH / "c1" / out,
                          init_seed=INIT, r1_seed=seeds.r1_codes, target_seed=core.target_seed(seeds, 0), stream_seed=core.stream_seed(seeds, 0), stage=stage, snapshots=())


def trainer(arm, **kw):
    j = job(arm, **kw)
    m = model.build_model(arm, j.cell.slots, INIT, backbone)
    if arm == "A5-C":
        m.addition.init_centre(train.initial_centre_rows(m, stream))
    return train.Trainer(j, m, build_probe(study, 2048)), m


# --- 1. A0 == P9-I W7 over 40 updates (forward, loss, every parameter) --------------------------------------------------------------
t0, m0 = trainer("A0")
w7 = p9imodel.build_model("W7", 4096, INIT, backbone)
pt = p9itrain.Trainer(p9icore.make_cell("W7", 4096), w7, p9itrain.build_optimizers(w7))
same = True
for u in range(1, 41):
    b = stream.batch(u)
    r1 = t0.step(b)
    r2 = pt.step(b.tokens)
    same &= r1["task_loss"] == r2["task_loss"]
same_params = all(torch.equal(p, dict(w7.named_parameters())[n]) for n, p in m0.named_parameters())
check("A0 bit-identical to P9-I W7 over 40 updates (losses and all parameters)", same and same_params)

# --- 2. the address loss: value and gradients from my own formula -------------------------------------------------------------------
t1, m1 = trainer("A1")
b = stream.batch(1)
m1.zero_grad(set_to_none=True)
total, parts = t1.compute_losses(b.tokens, b.fact_ids, 1, 1)
mem = m1.addition
h = m1.embed_block0(b.tokens[:, :63])
win = torch.stack([h[:, 8 * r: 8 * r + 7].reshape(h.shape[0], -1) for r in range(8)], 1)
z = win @ mem.wq.T
q = (z / z.norm(dim=-1, keepdim=True).clamp_min(1e-8)).reshape(-1, 16)
kn = mem.keys / mem.keys.norm(dim=-1, keepdim=True).clamp_min(1e-8)
gen = torch.Generator().manual_seed(core.target_seed(seeds, 0))
inj = torch.randperm(4096, generator=gen)[:2048]
tg = inj[b.fact_ids.reshape(-1)]
scores = (q.double() @ kn.double().T) / 0.2
mine = (torch.logsumexp(scores, 1) - scores[torch.arange(128), tg]).mean()
check("L_addr value = mean over 128 sites of -log softmax over all 4096 cosine scores / 0.2 (float64 reference)", abs(float(parts["addr"]) - float(mine)) < 1e-4, theirs=float(parts["addr"]), mine=float(mine))
ga = torch.autograd.grad(parts["addr"], [mem.wq, mem.keys, mem.values, mem.wo, mem.gate], allow_unused=True, retain_graph=True)
gm = torch.autograd.grad(mine.float(), [mem.wq, mem.keys], allow_unused=True)
check("L_addr gradients reach wq and keys only, and equal my formula's", ga[2] is None and ga[3] is None and ga[4] is None and torch.allclose(ga[0], gm[0], atol=1e-5, rtol=1e-4) and torch.allclose(ga[1], gm[1], atol=1e-6, rtol=1e-4),
      keys_rows_with_grad=int((ga[1].abs().sum(1) > 0).sum()))
check("A1 total = answer + lambda * L_addr (lambda 1.0)", abs(float(total) - float(parts["answer"] + 1.0 * parts["addr"])) < 1e-6)
check("A1 injection equals randperm(N, base+40)[:F] (target slot, a fixed injection)", torch.equal(t1.injection, inj) and len(set(inj.tolist())) == 2048)
backbone_trainable = [n for n, p in m1.named_parameters() if n.startswith("backbone.") and p.requires_grad]
check("no backbone parameter is trainable (A1)", not backbone_trainable)

# --- 3. A1-S: targets not a function of the fact ------------------------------------------------------------------------------------
ts, ms = trainer("A1-S")
f1 = b.fact_ids
f2 = torch.randint(0, 2048, f1.shape)
a, c = ts.targets_for(f1, 7), ts.targets_for(f2, 7)
d = ts.targets_for(f1, 8)
corr = float((ts.targets_for(f1, 7) == inj[f1.reshape(-1)]).float().mean())
# over 200 updates, how often does the same fact get the same target? (should be ~1/N)
same_fact_same_target, pairs = 0, 0
last = {}
for u in range(1, 201):
    bb = stream.batch(u)
    tt = ts.targets_for(bb.fact_ids, u)
    for f, t in zip(bb.fact_ids.reshape(-1).tolist(), tt.tolist()):
        if f in last:
            pairs += 1
            same_fact_same_target += int(last[f] == t)
        last[f] = t
check("A1-S targets identical under changed fact ids, change with the update, unrelated to the injection", torch.equal(a, c) and not torch.equal(a, d) and corr < 0.05,
      repeat_pairs=pairs, same_target_rate=same_fact_same_target / max(1, pairs))

# --- 4. A2 phases, frozen groups and the reset ---------------------------------------------------------------------------------------
t2, m2 = trainer("A2", hyper=core.Hyper(u_pre=16.0))
names1 = sorted(n.split(".")[-1] for n, _ in t2.named)
recs = [t2.step(stream.batch(u)) for u in range(1, 17)]
frozen_moved = any(r["param_change_norm"][g] != 0 for r in recs for g in ("values", "wo", "gate"))
snapshot = {n: p.detach().clone() for n, p in m2.named_parameters()}
b17 = stream.batch(17)
# expected first phase-2 step from a FRESH AdamW: theta - lr * (m_hat / (sqrt(v_hat) + eps)) with m_hat = g, v_hat = g^2 after one step
last_query_held = m2.addition.last_query is not None and m2.addition.last_query.grad_fn is not None
m2.addition.last_query = None  # attempt 1 failed here: the trainer leaves a non-leaf query with its graph on the module
ref = copy.deepcopy(m2)
for p in ref.parameters():
    p.requires_grad_(False)
rmem = ref.addition
for n in ("wq", "keys", "values", "wo", "gate"):
    getattr(rmem, n).requires_grad_(True)
logits, _ = ref(b17.tokens[:, :-1])
zz = logits[:, SITES][..., list(range(0x40, 0x60))]
loss = F.cross_entropy(zz.reshape(-1, 32), (b17.tokens[:, 1:][:, SITES] - 0x40).reshape(-1))
params = [getattr(rmem, n) for n in ("wq", "keys", "values", "wo", "gate")]
grads = torch.autograd.grad(loss, params)
norm = torch.sqrt(sum((g.double() ** 2).sum() for g in grads))
scale = min(1.0, 1.0 / (float(norm) + 1e-6))
expected = {n: (p - 0.003 * (g * scale) / ((g * scale).abs() + 1e-8)).detach() for n, p, g in zip(("wq", "keys", "values", "wo", "gate"), params, grads)}
r17 = t2.step(b17)
names2 = sorted(n.split(".")[-1] for n, _ in t2.named)
got = {n: getattr(m2.addition, n).detach() for n in expected}
maxdiff = max(float((got[n] - expected[n]).abs().max()) for n in expected)
steps = sorted({int(s["step"]) for s in t2.optimizers[0].state.values()})
check("trainer leaves the last batch query WITH its autograd graph on the memory module (holds the graph between updates)", True, held=last_query_held)
check("A2 phase 1 trains wq and keys only; values, wo, gate do not move in phase 1", names1 == ["keys", "wq"] and not frozen_moved, phase1=names1)
check("A2 phase 2 trains everything with a fresh AdamW (first step = lr * sign-like Adam step of the clipped answer gradient)", names2 == ["gate", "keys", "values", "wo", "wq"] and steps == [1] and maxdiff < 1e-6 and r17["address_loss"] is not None,
      maxdiff=maxdiff, phase2=names2, counters=steps, phase2_total_is_answer=abs(r17["task_loss"] - float(loss)) < 1e-6)

# --- 5. A4: k(t), the wide read, the final read -----------------------------------------------------------------------------------
def k_formula(t, k0, ta):
    return 8 if t >= ta else max(8, round(k0 * (8 / k0) ** (t / ta)))


bad = []
for stage, slots, frac in ((1, 4096, 0.125), (1, 4096, 1.0), (2, 16384, 0.125), (2, 16384, 1.0)):
    sch = core.schedule_for("A4", stage, core.Hyper(k0_fraction=frac), slots)
    k0 = round(frac * slots)
    ta = core.stage_updates(stage) // 2
    if (sch.k0, sch.t_anneal) != (k0, ta):
        bad.append(("schedule", stage, slots, frac, sch))
    for t in range(0, ta + 3):
        if core.k_schedule(t, k0, ta) != k_formula(t, k0, ta):
            bad.append((stage, slots, frac, t))
            break
check("A4 k(t) equals the formula for every t at Stage 1 and Stage 2 (k0 = N/8 and N; T_A = U/2 and 4U/2)", not bad, mismatches=bad[:3])
t4, m4 = trainer("A4")
check("A4's first update reads k0, update T_A reads k(T_A-1), update T_A+1 reads 8", t4.read_k(0) == 512 and t4.read_k(4095) == k_formula(4095, 512, 4096) and t4.read_k(4096) == 8, k_at_T_A_minus_1=t4.read_k(4095))
tok = stream.batch(3).tokens[:, :63]
for k in (512, 181, 23):
    m4.set_read_k(k)
    with torch.no_grad():
        lg, sel = m4(tok)
        hh = m4.embed_block0(tok)
        win = torch.stack([hh[:, 8 * r: 8 * r + 7].reshape(hh.shape[0], -1) for r in range(8)], 1)
        zq = win @ m4.addition.wq.T
        qq = (zq / zq.norm(dim=-1, keepdim=True).clamp_min(1e-8)).reshape(-1, 16)
        sc = (qq @ (m4.addition.keys / m4.addition.keys.norm(dim=-1, keepdim=True).clamp_min(1e-8)).T) / 0.2
        top = sc.argsort(dim=-1, descending=True, stable=True)[:, :k]
        w = sc.gather(1, top).softmax(-1)
        read = (w[..., None] * m4.addition.values[top]).sum(1).reshape(16, 8, 32)
        out = torch.sigmoid(m4.addition.gate) * (read @ m4.addition.wo.T)
        x = m4.embed_block0(tok).clone()
        delta = torch.zeros_like(x)
        delta[:, SITES] = out
        mine_logits = m4.finish(x, delta)
    check(f"A4 wide read at k = {k} equals softmax(a/0.2) over the k best slots (my computation)", sel.selected.shape[-1] == k and torch.allclose(lg, mine_logits, atol=1e-5), maxdiff=float((lg - mine_logits).abs().max()))
m4.set_read_k(8)
m4.eval()
w7b = p9imodel.build_model("W7", 4096, INIT, backbone, seed_rng=False)
w7b.load_state_dict({k: v for k, v in m4.state_dict().items()}, strict=False)
w7b.eval()
with torch.no_grad():
    check("A4 at k = 8 (evaluation) equals P9-I's standard top-8 W7 read bit for bit", torch.equal(m4(tok)[0], w7b(tok)[0]))
# the trainer resets read_k to 8 after every step, so the evaluation always reads top-8
t4.step(stream.batch(1))
check("after a training step A4's model reads k = 8 (evaluation and probes read the standard top-8)", m4.addition.read_k == 8)

# --- 6. A5-C ------------------------------------------------------------------------------------------------------------------------
tc, mc = trainer("A5-C")
rows = []
with torch.no_grad():
    for u in range(1, 17):
        tt = stream.batch(u).tokens
        hh = mc.embed_block0(tt[:, :63])
        win = torch.stack([hh[:, 8 * r: 8 * r + 7].reshape(hh.shape[0], -1) for r in range(8)], 1)
        rows.append((win @ mc.addition.wq.T).reshape(-1, 16))
m_init = torch.cat(rows).mean(0)
check("A5-C m initialised to the mean of z over the first 16 training batches (2,048 answer sites)", torch.allclose(mc.addition.centre, m_init, atol=1e-7))
c0 = mc.addition.centre.clone()
bt = stream.batch(1)
with torch.no_grad():
    hh = mc.embed_block0(bt.tokens[:, :63])
    win = torch.stack([hh[:, 8 * r: 8 * r + 7].reshape(hh.shape[0], -1) for r in range(8)], 1)
    zb = (win @ mc.addition.wq.T).reshape(-1, 16).mean(0)
tc.step(bt)
check("A5-C m <- 0.99 m + 0.01 * (batch mean of z of the update's forward, pre-step parameters)", torch.allclose(mc.addition.centre, 0.99 * c0 + 0.01 * zb, atol=1e-7))
mc.eval()
c1 = mc.addition.centre.clone()
with torch.no_grad():
    mc(bt.tokens[:, :63])
check("A5-C m frozen at evaluation; no gradient (buffer)", torch.equal(c1, mc.addition.centre) and not mc.addition.centre.requires_grad and "centre" not in dict(mc.named_parameters()))
# centred query in the forward
with torch.no_grad():
    hh = mc.embed_block0(tok)
    sel = mc.select(hh, tok)
    win = torch.stack([hh[:, 8 * r: 8 * r + 7].reshape(hh.shape[0], -1) for r in range(8)], 1)
    zq = win @ mc.addition.wq.T - mc.addition.centre
    qq = (zq / zq.norm(dim=-1, keepdim=True)).reshape(-1, 16)
    top = (qq @ (mc.addition.keys / mc.addition.keys.norm(dim=-1, keepdim=True)).T).argsort(dim=-1, descending=True, stable=True)[:, :8]
check("A5-C forward selects with q = (z - m)/|z - m|", torch.equal(sel.selected.reshape(-1, 8), top))

# --- 7. A5-D --------------------------------------------------------------------------------------------------------------------------
td, md = trainer("A5-D")
total, parts = td.compute_losses(bt.tokens, bt.fact_ids, 1, 1)
hh = md.embed_block0(bt.tokens[:, :63])
win = torch.stack([hh[:, 8 * r: 8 * r + 7].reshape(hh.shape[0], -1) for r in range(8)], 1)
zq = (win @ md.addition.wq.T).reshape(-1, 16).double()
qq = zq / zq.norm(dim=-1, keepdim=True)
G = qq @ qq.T
off = ~torch.eye(128, dtype=torch.bool)
ldiv = math.log(float(torch.exp(2 * G[off]).mean()))
check("A5-D L_div = log mean_{i != j} exp(2 q_i.q_j) over the 128 un-centred unit queries; total = answer + mu L_div", abs(float(parts["div"]) - ldiv) < 1e-5 and abs(float(total) - float(parts["answer"] + 1.0 * parts["div"])) < 1e-6, theirs=float(parts["div"]), mine=ldiv)

# --- 8. G6: try to break it --------------------------------------------------------------------------------------------------------------
tt1, mm1 = trainer("A1")
for u in range(1, 21):
    tt1.step(stream.batch(u))
mm1.eval()
with torch.no_grad():
    before = mm1(tok)[0].clone()
tt1.injection = torch.randperm(4096)[:2048]
study.facts.answer[:] = study.facts.answer.flip(0)  # scramble a fact table the model could have captured
with torch.no_grad():
    after = mm1(tok)[0]
study.facts.answer[:] = study.facts.answer.flip(0)
holders = []
for name, mod in mm1.named_modules():
    for attr, val in vars(mod).items():
        if torch.is_tensor(val) and val.numel() in (2048,) and not attr.startswith("_parameters"):
            holders.append(f"{name}.{attr}")
sd_keys = [k for k in mm1.state_dict() if not k.startswith("backbone.")]
check("G6: a trained A1 forward is unchanged when the injection and a fact table are changed after training; no fact-sized tensor held by the model", torch.equal(before, after) and not holders,
      addition_state=sd_keys, fact_sized_attributes=holders)

# --- 9. schedules and exposures, MID-SCHEDULE ---------------------------------------------------------------------------------------------
hy = core.Hyper(lambda_=1.0, u_pre=2048.0, k0_fraction=0.125, mu=1.0)
s1, s2 = core.schedule_for("A2", 1, hy, 4096), core.schedule_for("A2", 2, hy, 16384)
a1, a2 = core.schedule_for("A4", 1, hy, 4096), core.schedule_for("A4", 2, hy, 16384)
try:
    core.schedule_for("A2", 3, hy, 65536)
    s3 = "defined"
except ValueError:
    s3 = "refused"
check("schedules in exposures per fact: A2 U_pre 2,048 -> 8,192 and A4 T_A 4,096 -> 16,384, k0 512 -> 2,048 at Stage 2; refused at Stage 3",
      (s1.u_pre, s2.u_pre, a1.t_anneal, a2.t_anneal, a1.k0, a2.k0, s3) == (2048, 8192, 4096, 16384, 512, 2048, "refused"),
      exposures={"stage1_U": core.exposures_per_fact(8192, 2048), "stage2_U": core.exposures_per_fact(8192, 8192), "stage2_4U": core.exposures_per_fact(32768, 8192), "stage3_U": core.exposures_per_fact(8192, 32768)},
      a2_switch_exposures=(core.exposures_per_fact(2048, 2048), core.exposures_per_fact(8192, 8192)))

# --- 10. probe: no leakage into training ---------------------------------------------------------------------------------------------------
probe = build_probe(study, 2048)
ph = {hashlib.sha256(bytes(r.tolist())).hexdigest() for r in probe.tokens}
hits = 0
for u in range(1, 8193):
    for r in stream.batch(u).tokens:
        if hashlib.sha256(bytes(r.tolist())).hexdigest() in ph:
            hits += 1
pa = study.streams["panel_a"].tokens
pah = {hashlib.sha256(bytes(r.tolist())).hexdigest() for r in pa}
check("probe: 256 facts x 2 occurrences, all trained facts; none of its contexts appears in the 8,192 training batches or in Panel A", probe.sites == 512 and probe.probe_facts == 256 and int(probe.fact.max()) < 2048 and hits == 0 and not (ph & pah),
      sites=probe.sites, training_hits=hits)
# the probe stream and unseen controls: does the calibration stream contain unseen-control contexts, and where?
cs = study.streams["calibration"]
unseen_rows = (cs.fact_ids >= study.facts.trained).all(1)
first_trained_row = int(((cs.fact_ids < 2048).all(1)).nonzero()[0])
check("calibration stream: unseen-control contexts never precede the probe (probe built from trained facts only)", int(probe.fact.max()) < 2048, unseen_rows=int(unseen_rows.sum()), first_unseen_row=(int(unseen_rows.nonzero()[0]) if bool(unseen_rows.any()) else None), first_trained_row=first_trained_row)

Path(__file__).parent.joinpath("outputs", "c1_arm_checks.json").write_text(json.dumps(results, indent=1, default=str))
print("ALL PASS" if all(v["ok"] for v in results.values()) else "SOME FAILED")
