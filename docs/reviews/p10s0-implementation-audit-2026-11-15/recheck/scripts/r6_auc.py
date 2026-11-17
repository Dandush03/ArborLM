"""m5: WX's descriptive AUC (ADR-0020 section 5.2 last bullet) recomputed independently: own zero-padded 64-position window per position t = 0..62, own query,
own cosine against every key, max over slots, brute-force pairwise AUC (ties 1/2) of the 8 answer sites against the other 55 positions. Tiny WX-A5-D and WX-A1
models trained 6 updates; synthetic backbone; test seeds p10s0-test-8 only. Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import json
import tempfile
from pathlib import Path

import torch
import torch.nn.functional as F

from studies.p9 import controls
from studies.p9.data import DataSizes, build_study_data
from studies.p9i.evaluate import stream_for
from studies.p10s0 import core, evaluate, train

train.configure()
SPEC = core.test_set(8)
torch.manual_seed(0)
backbone = controls.synthetic_backbone()
g = torch.Generator().manual_seed(12)
corpus = bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())
FACTS = 128
data = build_study_data(SPEC.seeds(2048), corpus, sizes=DataSizes(main_trained=FACTS, unseen=64, lane_d_per_set=128))
res = {}
for arm in ("WX-A5-D", "WX-A1"):
    cell = core.make_cell(arm, "2K/4K", "WX", 1, 0, "TEST-")
    job = train.Job(cell=cell, mode="dry", data=data, stream=train.training_stream_for(data, FACTS), backbone=backbone, out_dir=Path(tempfile.mkdtemp()) / arm, init_seed=SPEC.base + 41,
                    r1_seed=data.seeds.r1_codes, target_seed=SPEC.base + 40, hyper=core.HYPER._replace(u_pre=2048.0), unit=8, snapshots=(), max_updates=6, diag_every=10**9)
    m = train.run_job(job).model
    theirs = evaluate.answer_site_auc(m, data, FACTS)
    st = stream_for(data, FACTS, core.PANEL_STREAM["A"])
    keep = (st.fact_ids < FACTS).all(dim=1)
    tok = st.tokens[keep][:512, : core.INPUT_LENGTH]
    m.eval()
    with torch.no_grad():
        h = m.embed_block0(tok)  # [B, 63, 32]
        B, T, Dh = h.shape
        pad = torch.cat([torch.zeros(B, 63, Dh), h], dim=1)  # index j+63 holds h_j; j<0 zero
        feats = torch.stack([pad[:, t : t + 64].reshape(B, -1) for t in range(T)], dim=1)  # [B, T, 2048] = [h_{t-63}; ...; h_t]
        q = F.normalize(F.linear(feats, m.addition.wq), dim=-1)
        k = F.normalize(m.addition.keys, dim=-1)
        top = torch.einsum("btd,sd->bts", q, k).amax(-1)
    sites = torch.zeros(T, dtype=torch.bool)
    sites[[8 * r + 6 for r in range(8)]] = True
    pos, neg = top[:, sites].reshape(-1).double(), top[:, ~sites].reshape(-1).double()
    gt = (pos[:, None] > neg[None, :]).double().sum() + 0.5 * (pos[:, None] == neg[None, :]).double().sum()
    mine = float(gt / (pos.numel() * neg.numel()))
    res[arm] = {"implementation": theirs["auc"], "auditor_bruteforce": mine, "abs_diff": abs(mine - theirs["auc"]), "answer_sites": pos.numel(), "others": neg.numel(), "others_per_context": int((~sites).sum()), "impl_counts": [theirs["answer_sites"], theirs["other_positions"]]}
print(json.dumps(res, indent=1))
