"""Auditor C: the memory read, ties, initialization, gradient reach under real AdamW updates, LoRA and E-table forms,
parameter matching, G5(c) gate isolation. Tiny stand-in student, test seeds 229601.. only; no real model.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import math
import sys

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")

import torch  # noqa: E402

from studies.p10s2 import core  # noqa: E402
from studies.p10s2.memory import CodeBook, LoRAArm, MemoryArm, SparseStore, TableArm, make_ablation, apply_read_ablation  # noqa: E402
from studies.p10s2.model import LoRAAdapter, StudentConfig, build_student, lora_parameter_count, store_parameter_count  # noqa: E402
from studies.p10s2.tokenization import Example  # noqa: E402
from studies.p10s2.train import train_arm  # noqa: E402

out = []


def say(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)
    print(s)


def gen(seed):
    return core.seeded_generator(seed, "auditor C check", "test")


# 1. the read against the definition (float64 loop), with ties and two stages ------------------------------------------
def read_def(keys, values, gates, stage_of, q):
    res = []
    for qi in q:
        a = []
        for s in range(keys.shape[0]):
            k = keys[s].double()
            a.append(float(qi.double() @ k / k.norm()))
        idx = sorted(range(len(a)), key=lambda s: (-a[s], s))[:8]  # ties: lowest row index
        z = [a[s] / 0.2 for s in idx]
        m = max(z)
        e = [math.exp(x - m) for x in z]
        w = [x / sum(e) for x in e]
        r = sum(w[i] * float(gates[stage_of[s]]) * values[s].double() for i, s in enumerate(idx))
        res.append((idx, r))
    return res


g = gen(229601)
st = SparseStore.new(5, 30, g)
st.append_stage(20, gen(229602))
with torch.no_grad():
    st.keys[0][3] = st.keys[0][7]  # exact duplicates -> ties
    st.keys[1][2] = st.keys[0][7] * 3.0  # same direction, different norm -> cosine tie across stages
    st.gates[0].fill_(0.7)
    st.gates[1].fill_(-1.3)
keys = torch.cat(list(st.keys)).detach()
vals = torch.cat(list(st.values)).detach()
stage_of = [0] * 30 + [1] * 20
q = torch.nn.functional.normalize(torch.randn(6, 16, generator=gen(229603)), dim=-1)
q = torch.cat([q, torch.nn.functional.normalize(keys[7:8], dim=-1)])  # a query pointing exactly at the tied rows
ref = read_def(keys, vals, [0.7, -1.3], stage_of, q)
got = st.read(q).detach().double()
sel = st.selected_rows(q)
maxdiff = max(float((got[i] - ref[i][1]).abs().max()) for i in range(len(ref)))
same_sel = all(sel[i].tolist() == ref[i][0] for i in range(len(ref)))
say("1 read vs definition: max abs diff", f"{maxdiff:.2e}", "selection identical", same_sel, "tied query selection", sel[-1].tolist()[:4])

# 2. initialization statistics at real size (one stage, 4096 x (16 + 576)) -----------------------------------------------
big = SparseStore.new(576, 4096, gen(229604))
k0, v0 = big.keys[0].detach(), big.values[0].detach()
say("2 init: keys std", f"{float(k0.std()):.5f}", "mean", f"{float(k0.mean()):.2e}", "values std", f"{float(v0.std()):.5f}", "gate", float(big.gates[0]),
    "stage params", big.parameter_count(), "ADR 2,424,833:", big.parameter_count() == 2424833)
# keys then values from one generator: reproduce
g2 = gen(229604)
kk = 0.02 * torch.randn(4096, 16, generator=g2)
vv = 0.02 * torch.randn(4096, 576, generator=g2)
say("2 init order keys-then-values reproduced:", torch.equal(kk, k0) and torch.equal(vv, v0))

# 3. gradient reach under real AdamW updates on a tiny student -----------------------------------------------------------
cfg = StudentConfig.tiny(vocab=64, width=32, layers=3)
student = build_student(cfg, gen(229605))
codes = CodeBook(229606, vocabulary=10)
h0 = student.tensor_hashes()


def ex(i, task):
    ids = tuple(int(x) for x in torch.randint(1, 64, (14,), generator=gen(229610 + i)).tolist())
    return Example(f"k{i}", task, ids, 9, ((2, i % 10), (4, (i + 3) % 10), (6, (i + 5) % 10)), 8, 5)


exA = [ex(i, "A") for i in range(16)]
exB = [ex(i + 20, "B") for i in range(16)]
st1 = MemoryArm(SparseStore.new(32, 24, gen(229620)), 1, codes)
train_arm(student, st1, exA, 6, 4, 0.003, gen(229621), codes.marker)
v1 = st1.store.clone()
maf_store = v1.clone()
maf_store.append_stage(24, gen(229622))
maf_store.freeze_stage(0)
maf_store.set_trainable([1])
maf = MemoryArm(maf_store, 1, codes)
before0 = [p.detach().clone() for p in maf_store.stage_parameters(0)]
before1 = [p.detach().clone() for p in maf_store.stage_parameters(1)]
rec = train_arm(student, maf, exB, 8, 4, 0.003, gen(229623), codes.marker)
after0 = maf_store.stage_parameters(0)
after1 = maf_store.stage_parameters(1)
say("3 MAF: first-stage keys/values/gate bit-identical after 8 AdamW updates:", all(torch.equal(a, b) for a, b in zip(before0, after0)),
    "| appended rows changed:", [not torch.equal(a, b) for a, b in zip(before1, after1)], "| trainable params", rec.trainable_parameters, "=", 24 * (16 + 32) + 1)
say("3 MAF one store, one top-8 over all rows: stages", maf_store.stages, "rows", maf_store.rows)
mii_store = maf_store.clone()
mii_store.set_trainable([0, 1])
mii = MemoryArm(mii_store, 1, codes)
b0 = [p.detach().clone() for p in mii_store.stage_parameters(0)]
rec2 = train_arm(student, mii, exB, 8, 4, 0.003, gen(229624), codes.marker, replay=exA, replay_rows=4, replay_generator=gen(229625))
say("3 M-ii: first-stage params changed:", [not torch.equal(a, b) for a, b in zip(b0, mii_store.stage_parameters(0))], "rows/update", rec2.rows_per_update, "replay", rec2.replay_rows)
mseq_store = v1.clone()
mseq_store.set_trainable([0])
mseq = MemoryArm(mseq_store, 1, codes)
train_arm(student, mseq, exB, 4, 4, 0.003, gen(229626), codes.marker)
say("3 M-seq: rows", mseq_store.rows, "(no growth)")
say("3 student tensors unchanged after all training:", student.tensor_hashes() == h0, "| any student param requires_grad:", any(p.requires_grad for p in student.parameters()))

# 4. G5(c): with g2 = 0 the read does not depend on the appended values -----------------------------------------------
s5 = v1.clone()
s5.append_stage(24, gen(229627))
qq = torch.stack([codes.get("A", j) for j in range(10)])
r0 = s5.read(qq).detach()
with torch.no_grad():
    s5.values[1].copy_(1e6 * torch.randn(24, 32, generator=gen(229628)))
r1 = s5.read(qq).detach()
say("4 G5c gate isolation bit-identical:", torch.equal(r0, r1))
with torch.no_grad():
    s5.values[1][0, 0] = float("inf")
r2 = s5.read(qq).detach()
say("4 G5c with a non-finite appended value (outside 'arbitrary finite'):", "nan appears" if torch.isnan(r2).any() else "isolated")

# 5. LoRA form and parameter matching ------------------------------------------------------------------------------------
real = StudentConfig(49152, 576, 30, 9, 3, 1536, 8192, 100000.0, 1e-5)
for r in (42, 84):
    say("5 LoRA rank", r, "params", lora_parameter_count(real, r))
store1 = store_parameter_count(real, 4096)
say("5 store per stage", store1, "| LoRA-42 rel diff", f"{(lora_parameter_count(real, 42) - store1) / store1:+.4%}",
    "| LoRA-84 vs 2 stages (M-joint 2N rows + 1 gate)", f"{(lora_parameter_count(real, 84) - (8192 * 592 + 1)) / (8192 * 592 + 1):+.4%}")
ad = LoRAAdapter(real, 42, gen(229629))
a_max = max(float(a.abs().max()) for a in ad.a)
b_nz = sum(int((b != 0).sum()) for b in ad.b)
say("5 LoRA A bound 1/sqrt(576) =", f"{1 / math.sqrt(576):.6f}", "max|A|", f"{a_max:.6f}", "| B nonzeros", b_nz, "| scale", ad.scale,
    "| A shapes", tuple(ad.a[0].shape), tuple(ad.a[1].shape), "| B shapes", tuple(ad.b[0].shape), tuple(ad.b[1].shape), "| params", sum(p.numel() for p in ad.parameters()))
tiny_ad = LoRAArm(LoRAAdapter(cfg, 4, gen(229630)))
ids = torch.tensor([list(exA[0].ids)])
reads = [[(2, "A", 1)]]
from studies.p10s2.memory import NullArm, run_student  # noqa: E402

base = run_student(student, NullArm(), ids, reads)
with_ad = run_student(student, tiny_ad, ids, reads)
say("5 untrained LoRA changes nothing (bit):", torch.equal(base, with_ad))
none_route = run_student(student, tiny_ad, ids, [[]])
say("5 LoRA on route none (no reads): bit-identical to student:", torch.equal(base, none_route))

# 6. E-table -------------------------------------------------------------------------------------------------------------
et = TableArm("A", 576, 2000, 4, gen(229631))
say("6 E-table params", et.parameter_count(), "(2,001 x 576 + 1) | std", f"{float(et.table.std()):.5f}", "| gate", float(et.gate), "| vs store stage", f"{et.parameter_count() / store1:.3f}x")

# 7. ablations ------------------------------------------------------------------------------------------------------------
ab = make_ablation("code_perm", None, gen(229632), stages=[1], tasks=["B"], vocabulary=10)
rd = [(1, "A", 3), (2, "B", 3), (3, "B", 10)]
say("7 code_perm keeps marker and first task:", apply_read_ablation(rd, ab, 10), "perm", ab.code_perm.tolist())
abv = make_ablation("value_perm", maf_store, gen(229633), stages=[1], tasks=["B"], vocabulary=10)
say("7 value_perm stages permuted:", list(abv.value_perms), "| marker_only:", apply_read_ablation(rd, make_ablation("marker_only", None, gen(229634), stages=[], tasks=[], vocabulary=10), 10))
