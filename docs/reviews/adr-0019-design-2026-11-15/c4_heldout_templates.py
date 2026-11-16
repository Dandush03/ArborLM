"""C4 (auditor, Opus 5.5) -- DIAGNOSTIC ON UNIT-TEST SEED SETS ONLY (900001 + 100 k), NOT A RESULT.

Feasibility of condition 4 of the draft's cell-success rule (H1 and H2 accuracy >= 0.90 x the cell's own Panel A
accuracy) and of conditions 2-3, on the three W7 models trained by the P9-I review's d4 (frozen P9-I code, W7,
4,096 slots / 2,048 facts, 8,192 updates, init seed 500001, test seed sets 0, 1, 2; parameters saved outside the
repository). Own forward (as c3); nothing imported from studies.p9i. The test seed sets are rebuilt here with the
P9-I rule (base 900001 + 100 k, data seeds base + i in P9's DATA_SEEDS order, null seeds base + 20.., base + 30..).
Reports, per model: accuracy (ties wrong) on Panels A, B, H1, H2; with values permuted and memory disabled on A;
mean query cosine on A; address stability (same top-1 slot on A and B for a fact); same-fact query cosine A vs B;
and the H1/H2 query shift.
"""
import json
import math
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as p9data

torch.set_num_threads(2)
ROOT = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
SCR = Path(sys.argv[1])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
FACTS = 2048


def ln(x, w, b):
    m = x.mean(-1, keepdim=True)
    v = ((x - m) ** 2).mean(-1, keepdim=True)
    return (x - m) / torch.sqrt(v + 1e-5) * w + b


def block(sd, i, h):
    p = f"blocks.{i}."
    b, t, _ = h.shape
    qkv = (ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]).reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = (q @ k.transpose(-1, -2) / math.sqrt(8)).masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    h = h + (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    return h + (0.5 * f * (1 + torch.erf(f / math.sqrt(2)))) @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def test_seedset(k):
    names = list(p9core.DATA_SEEDS)
    base = 900001 + 100 * k
    return p9core.SeedSet(f"p9i-test-{k}", **{n: base + i for i, n in enumerate(names)},
                          null_seeds_a=tuple(base + 20 + i for i in range(3)), null_seeds_b=tuple(base + 30 + i for i in range(3)))


corpus = p9core.load_trained_corpus(ROOT)
bb = {k: v.detach() for k, v in controls.load_backbone((101, 301), ROOT)[0].state_dict().items()}
res = {"DIAGNOSTIC": True}
for k in (0, 1, 2):
    study = p9data.build_study_data(test_seedset(k), corpus)
    sd = torch.load(SCR / f"d4_test{k}_W7.pt")
    P = {n.split(".", 1)[1]: v for n, v in sd.items()}

    def run(tokens, perm=None, disabled=False):
        e = bb["token.weight"][tokens] + bb["position.weight"][: tokens.shape[1]]
        h = block(bb, 0, e)
        x = torch.stack([torch.cat([h[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)
        q = F.normalize(x.reshape(-1, 224) @ P["wq"].T, dim=-1, eps=1e-8)
        kn = F.normalize(P["keys"], dim=-1, eps=1e-8)
        top, idx = (q @ kn.T / 0.2).topk(8, dim=-1)
        vals = P["values"] if perm is None else P["values"][perm]
        read = (top.softmax(-1)[..., None] * vals[idx]).sum(1)
        add = torch.sigmoid(P["gate"]) * (read.reshape(tokens.shape[0], 8, 32) @ P["wo"].T)
        delta = torch.zeros_like(h)
        if not disabled:
            delta[:, SITES] = add
        out = ln(block(bb, 1, h + delta), bb["final_norm.weight"], bb["final_norm.bias"])
        return (out @ bb["token.weight"].T)[:, SITES][..., ALPHA], q, idx[:, 0]

    def score(stream_name, **kw):
        st = study.streams[stream_name]
        keep = (st.fact_ids < FACTS).all(1)
        toks, ids = st.tokens[keep], st.fact_ids[keep]
        ok, Q, T1 = [], [], []
        with torch.no_grad():
            for s in range(0, toks.shape[0], 256):
                t = toks[s : s + 256]
                lg, q, t1 = run(t[:, :63], **kw)
                ans = t[:, [p + 1 for p in SITES]] - 0x40
                mine = lg.gather(-1, ans[..., None]).squeeze(-1)
                other = lg.scatter(-1, ans[..., None], -math.inf).amax(-1)
                ok.append((mine > other).reshape(-1))
                Q.append(q)
                T1.append(t1)
        Q = torch.cat(Q).double()
        n = Q.shape[0]
        s = Q.sum(0)
        f = ids.reshape(-1)
        return {"accuracy": float(torch.cat(ok).float().mean()), "sites": n, "mean_cos": float((s @ s - n) / (n * (n - 1)))}, f, Q, torch.cat(T1)

    out = {}
    per = {}
    for name in ("panel_a", "panel_b", "h1", "h2"):
        r, f, Q, t1 = score(name)
        out[name] = r
        qf = torch.zeros(FACTS, 16, dtype=torch.float64)
        tf = torch.full((FACTS,), -1, dtype=torch.int64)
        qf[f] = Q
        tf[f] = t1
        per[name] = (qf, tf)
    g = torch.Generator().manual_seed(4242)
    out["panel_a_values_permuted"] = score("panel_a", perm=torch.randperm(P["values"].shape[0], generator=g))[0]["accuracy"]
    out["panel_a_memory_disabled"] = score("panel_a", disabled=True)[0]["accuracy"]
    qa, ta = per["panel_a"]
    for other in ("panel_b", "h1", "h2"):
        qo, to = per[other]
        out[f"same_fact_query_cos_A_vs_{other}"] = float((qa * qo).sum(-1).mean())
        out[f"same_top1_slot_A_vs_{other}"] = float((ta == to).double().mean())
    a = out["panel_a"]["accuracy"]
    out["H1_over_A"] = out["h1"]["accuracy"] / a if a > 0 else None
    out["H2_over_A"] = out["h2"]["accuracy"] / a if a > 0 else None
    out["condition4_holds(>=0.90)"] = bool(a > 0 and min(out["H1_over_A"], out["H2_over_A"]) >= 0.90)
    res[f"p9i-test-{k}"] = out
    print(json.dumps({k: out}), file=sys.stderr, flush=True)
print(json.dumps(res, indent=1))
