"""D3 (auditor, Opus 5.5): address-collapse diagnostics on the REGISTERED attempt-2 snapshots (no training;
the snapshots are read, not changed). Own forward (as s3_rescore.py), registered data regenerated from the
manifest's seeds and checked against its fourteen hashes.

Per cell, on Panel A trained facts (one query per fact):
* movement of the interface parameters from their initialization (re-drawn here: N(0, 0.02) from
  torch generators seeded init + 3000 (wq), + 6000 / 7000 / 8000 (A4 q, k, v), + 1000 keys, + 2000 values);
* unit-query geometry: mean cosine between different facts (= |mean q|^2 up to the 1/n term), the
  participation-ratio effective rank of the centred query covariance, the number of distinct top-1 slots,
  the largest share of facts on one top-1 slot, "private" slots (in the top 8 of exactly one fact) and
  the share of facts with at least one private slot;
* for W7 / E7: the pre-normalization query z = sum_j W_j x_{t-6+j} split by window slot j (0 separator,
  1..5 identifier, 6 binding): ||E z||^2 / E||z||^2 (fact-independent share), and per-slot share of the
  fact-dependent variance tr Cov(W_j x_j) / sum_j tr Cov(W_j x_j); the same with the initial W;
* for A4 / A4E: the record's identifier attention mass per head (from eval.json) and the same split of the
  attention output into its fact-independent and fact-dependent parts.

Usage: d3_snapshot_diagnostics.py RUN_DIR EXPERIMENTS_ROOT LABEL [LABEL ...]
"""
import json
import math
import sys
from pathlib import Path

import torch

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as p9data

torch.set_num_threads(4)
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
SITES = [8 * r + 6 for r in range(8)]
FACTS_OF = {4096: 2048, 16384: 8192, 65536: 32768}


def ln(x, w, b):
    m = x.mean(-1, keepdim=True)
    v = ((x - m) ** 2).mean(-1, keepdim=True)
    return (x - m) / torch.sqrt(v + 1e-5) * w + b


def block0(sd, h):
    p = "backbone.blocks.0."
    b, t, _ = h.shape
    qkv = (ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]).reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = (q @ k.transpose(-1, -2) / math.sqrt(8)).masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    h = h + (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    return h + (0.5 * f * (1 + torch.erf(f / math.sqrt(2)))) @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def attention4(x, aq, ak, av):
    out = []
    for t in SITES:
        q = (x[:, t] @ aq.T).reshape(-1, 4, 8)
        k = (x[:, : t + 1] @ ak.T).reshape(x.shape[0], t + 1, 4, 8)
        v = (x[:, : t + 1] @ av.T).reshape(x.shape[0], t + 1, 4, 8)
        w = (torch.einsum("bhd,bthd->bht", q, k) / math.sqrt(8)).softmax(-1)
        out.append(torch.einsum("bht,bthd->bhd", w, v).reshape(-1, 32))
    return torch.stack(out, 1)


def mat(seed, *shape):
    return torch.empty(shape).normal_(0, 0.02, generator=torch.Generator().manual_seed(seed))


def eff_rank(X):
    Xc = X - X.mean(0)
    ev = torch.linalg.eigvalsh(Xc.T @ Xc / X.shape[0]).clamp_min(0)
    return float(ev.sum() ** 2 / (ev**2).sum())


manifest = json.loads((RUN / "data_manifest.json").read_text())
sd_seeds = dict(manifest["seeds"])
name = sd_seeds.pop("name")
sd_seeds["null_seeds_a"] = tuple(sd_seeds["null_seeds_a"])
sd_seeds["null_seeds_b"] = tuple(sd_seeds["null_seeds_b"])
seeds = p9core.SeedSet(name, **sd_seeds)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
assert study.sha256s() == manifest["sha256s"]
print("registered data regenerated; hashes equal the manifest's")
panel = study.streams["panel_a"]

for label in sys.argv[3:]:
    ev = json.loads((RUN / "cells" / label / "eval" / "u0008192" / "eval.json").read_text())
    sd = torch.load(RUN / "cells" / label / "snapshots" / "u0008192" / "model.pt", weights_only=True)["model"]
    arm = label.split("-n")[0]
    slots = int(label.split("-n")[1].split("-")[0])
    seed = ev["seed"]
    nf = FACTS_OF[slots]
    keep = (panel.fact_ids < nf).all(1)
    toks = panel.tokens[keep][:, :63]
    out = {"label": label, "accuracy_A_record": ev["panels"]["A"]["accuracy"]}
    # movement from initialization
    mv = {}
    if "addition.wq" in sd:
        w0 = mat(seed + 3000, *sd["addition.wq"].shape)
        mv["wq_rel_change"] = float((sd["addition.wq"] - w0).norm() / w0.norm())
        mv["wq_norm_init_final"] = [float(w0.norm()), float(sd["addition.wq"].norm())]
    for nm, off in (("attn_q", 6000), ("attn_k", 7000), ("attn_v", 8000)):
        if "addition." + nm in sd:
            a0 = mat(seed + off, 32, 32)
            mv[nm + "_rel_change"] = float((sd["addition." + nm] - a0).norm() / a0.norm())
    if "addition.keys" in sd:
        k0 = mat(seed + 1000, slots, 16)
        d = (sd["addition.keys"] - k0).norm(dim=-1)
        mv["keys_rows_moved_gt_0.01"] = int((d > 0.01).sum())
        mv["keys_mean_row_change"] = float(d.mean())
        kn = sd["addition.keys"] / sd["addition.keys"].norm(dim=-1, keepdim=True)
        mv["key_mean_cos_to_mean_direction"] = float((kn @ (kn.mean(0) / kn.mean(0).norm())).mean())
    if "addition.values" in sd:
        v0 = mat(seed + 2000, slots, 32)
        mv["values_mean_row_change"] = float((sd["addition.values"] - v0).norm(dim=-1).mean())
    if "addition.gate" in sd:
        mv["gate_sigmoid"] = float(torch.sigmoid(sd["addition.gate"]))
        mv["wo_norm"] = float(sd["addition.wo"].norm())
    out["movement"] = mv
    if arm not in ("W7", "E7", "A4", "A4E", "N", "BB"):
        print(json.dumps(out))
        continue
    with torch.no_grad():
        zs, parts, parts0, sel = [], [], [], []
        for s in range(0, toks.shape[0], 512):
            t = toks[s : s + 512]
            e = sd["backbone.token.weight"][t] + sd["backbone.position.weight"][:63]
            h = block0(sd, e)
            x = e if arm in ("E7", "A4E") else h
            if arm in ("W7", "E7"):
                win = torch.stack([torch.stack([x[:, st - 6 + j] for j in range(7)], 1) for st in SITES], 1)  # [b, 8, 7, 32]
                W = sd["addition.wq"].reshape(16, 7, 32)
                W0 = mat(seed + 3000, 16, 224).reshape(16, 7, 32)
                per = torch.einsum("bsjc,kjc->bsjk", win, W)  # [b, 8, 7, 16]
                per0 = torch.einsum("bsjc,kjc->bsjk", win, W0)
                parts.append(per.reshape(-1, 7, 16))
                parts0.append(per0.reshape(-1, 7, 16))
                z = per.sum(2).reshape(-1, 16)
            elif arm in ("A4", "A4E"):
                f = attention4(x, sd["addition.attn_q"], sd["addition.attn_k"], sd["addition.attn_v"])
                z = f.reshape(-1, 32) @ sd["addition.wq"].T
            else:
                z = x[:, SITES].reshape(-1, 32) @ sd["addition.wq"].T
            zs.append(z)
        Z = torch.cat(zs).double()
        Q = Z / Z.norm(dim=-1, keepdim=True)
        n = Q.shape[0]
        mq = Q.mean(0)
        geo = {"facts": n, "mean_cos_different": float((Q.sum(0) @ Q.sum(0) - n) / (n * (n - 1))), "norm_of_mean_unit_query": float(mq.norm()),
               "eff_rank_centred_queries": eff_rank(Q), "z_fact_independent_share": float(Z.mean(0).norm() ** 2 / (Z.norm(dim=-1) ** 2).mean())}
        kn = sd["addition.keys"] / sd["addition.keys"].norm(dim=-1, keepdim=True).clamp_min(1e-8)
        idx = []
        for s in range(0, n, 2048):
            sc = Q[s : s + 2048].float() @ kn.T
            idx.append(sc.topk(8, dim=-1).indices)
        I8 = torch.cat(idx)
        top1 = I8[:, 0]
        cnt1 = torch.bincount(top1, minlength=slots)
        geo["distinct_top1"] = int((cnt1 > 0).sum())
        geo["largest_top1_share"] = float(cnt1.max() / n)
        cnt8 = torch.zeros(slots, dtype=torch.int64)
        for col in range(8):
            cnt8 += torch.bincount(I8[:, col], minlength=slots)
        private = cnt8 == 1
        geo["private_slots"] = int(private.sum())
        geo["facts_with_a_private_slot"] = float(private[I8].any(1).float().mean())
        geo["distinct_top8"] = int((cnt8 > 0).sum())
        out["query_geometry"] = geo
        if parts:
            for tag, pp in (("trained", parts), ("init", parts0)):
                Pt = torch.cat(pp).double()  # [n, 7, 16]
                zt = Pt.sum(1)
                var_slot = [float(((Pt[:, j] - Pt[:, j].mean(0)) ** 2).sum(-1).mean()) for j in range(7)]
                tot = sum(var_slot)
                out[f"window_split_{tag}"] = {
                    "fact_independent_share_of_E|z|^2": float(zt.mean(0).norm() ** 2 / (zt.norm(dim=-1) ** 2).mean()),
                    "var_share_by_slot[sep,id1..id5,bind]": [round(v / tot, 4) for v in var_slot],
                    "var_share_identifier_slots": round(sum(var_slot[1:6]) / tot, 4),
                    "total_var_over_sum_slot_var": float(((zt - zt.mean(0)) ** 2).sum(-1).mean() / tot),
                    "mean_cos_unit_queries": float(((zt / zt.norm(dim=-1, keepdim=True)).sum(0).norm() ** 2 - n) / (n * (n - 1))),
                }
        if "attention" in ev["panels"]["A"]:
            out["identifier_attention_record"] = ev["panels"]["A"]["attention"]
    print(json.dumps(out))
