"""S3 (auditor, Opus 5.5): independent re-scoring of registered P9-I attempt-2 snapshots.

Independent of studies.p9i and of studies.p9.model / evaluate. The backbone blocks, every arm's
addition (N, W7, E7, A4, A4E, R1, R2, D, D7, BB, BB-D, BB-0), the oracle codes, the R2 slot table, the
top-8 selection (ties to the lowest slot id), ties-wrong alphabet scoring, memory disabling, the seeded
cyclic value derangement (seed 977, as defined in the ADR-0017 implementation contract), the query
diagnostics and the next-byte loss are written here from the ADR text (the same reference forward the
auditor used in the pre-freeze audit, a2 / a4, extended to all arms).

Data are regenerated with studies.p9.data.build_study_data (the generator gated by G1, audited in the P9
calibration audit) from the seeds recorded in the run's data_manifest.json, and the regenerated stream
hashes are compared with the manifest's fourteen hashes before anything is scored. Frozen backbones come
from studies.p9.controls.load_backbone and are compared tensor by tensor with the snapshot's frozen part.

Usage: s3_rescore.py RUN_DIR EXPERIMENTS_ROOT LABEL [LABEL ...]
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

torch.set_num_threads(4)
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
LABELS = sys.argv[3:]
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
FACTS_OF = {4096: 2048, 16384: 8192, 65536: 32768}
TRAINED_TOTAL = 32768
M64 = (1 << 64) - 1
G = 0x9E3779B97F4A7C15
CI = {2048: (36, 96), 8192: (198, 318), 32768: (905, 1147)}  # own exact binomial intervals (s1_recompute.py)


def mix(x: int) -> int:
    x = (x + G) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


def code(seed: int, ident: int) -> list[float]:
    st = mix(mix(seed & M64) + ident)
    out = []
    for j in range(8):
        a = mix((st + (2 * j + 1) * G) & M64)
        b = mix((st + (2 * j + 2) * G) & M64)
        u1 = ((a >> 11) + 1) / float(1 << 53)
        u2 = (b >> 11) / float(1 << 53)
        r = math.sqrt(-2.0 * math.log(u1))
        out += [r * math.cos(2 * math.pi * u2), r * math.sin(2 * math.pi * u2)]
    n = math.sqrt(sum(v * v for v in out))
    return [v / n for v in out]


def ln(x, w, b):
    m = x.mean(-1, keepdim=True)
    v = ((x - m) ** 2).mean(-1, keepdim=True)
    return (x - m) / torch.sqrt(v + 1e-5) * w + b


def block(sd, i, h):
    p = f"backbone.blocks.{i}."
    b, t, _ = h.shape
    qkv = ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]
    qkv = qkv.reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = q @ k.transpose(-1, -2) / math.sqrt(8)
    s = s.masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    a = s.softmax(-1)
    h = h + (a @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    f = 0.5 * f * (1 + torch.erf(f / math.sqrt(2)))
    return h + f @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"], a


def ident_codes(tokens):
    out = torch.zeros(tokens.shape[0], 8, dtype=torch.int64)
    for r in range(8):
        for i in range(4):
            out[:, r] += ((tokens[:, 8 * r + 1 + i] - 0x40) % 32) * 32**i
    return out


def window(x):  # [B, 8, 224] = [x_{t-6}; ...; x_t] at each answer site
    return torch.stack([torch.cat([x[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)


def attention4(x, aq, ak, av):
    out = []
    for t in SITES:
        heads = []
        for hd in range(4):
            sl = slice(8 * hd, 8 * hd + 8)
            q = x[:, t] @ aq[sl].T
            k = x[:, : t + 1] @ ak[sl].T
            v = x[:, : t + 1] @ av[sl].T
            w = ((k @ q[:, :, None]).squeeze(-1) / math.sqrt(8)).softmax(-1)
            heads.append((w[:, :, None] * v).sum(1))
        out.append(torch.cat(heads, -1))
    return torch.stack(out, 1)


def top8(q, keys):
    """[Q, 8] slot ids: top 8 cosine scores / 0.2, ties to the lowest slot id; and their scores."""
    kn = keys / keys.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    ids, vals = [], []
    for s in range(0, q.shape[0], 1024):
        sc = (q[s : s + 1024] @ kn.T) / 0.2
        v9, i9 = sc.topk(9, dim=-1)
        tie = (v9[:, :-1] == v9[:, 1:]).any(-1)  # any tie inside the top 9: redo those rows exactly
        if bool(tie.any()):
            rows = tie.nonzero().squeeze(-1)
            order = sc[rows].argsort(dim=-1, descending=True, stable=True)[:, :9]
            i9[rows] = order
            v9[rows] = sc[rows].gather(1, order)
        ids.append(i9[:, :8])
        vals.append(v9[:, :8])
    return torch.cat(ids), torch.cat(vals)


class Cell:
    def __init__(self, label, sd, r1_seed, slot_of):
        parts = label.split("-n")
        self.arm = parts[0]
        self.slots = int(parts[1].split("-")[0])
        self.sd = sd
        self.r1_seed = r1_seed
        self.slot_of = slot_of
        self.cache: dict = {}

    def query(self, tokens, e, h):
        a = self.arm
        sd = self.sd
        if a == "R1":
            flat = ident_codes(tokens).reshape(-1).tolist()
            for c in set(flat):
                if c not in self.cache:
                    self.cache[c] = code(self.r1_seed, c)
            return torch.tensor([self.cache[c] for c in flat], dtype=torch.float32)
        x = e if a in ("E7", "A4E") else h
        if a in ("N", "BB"):
            f = x[:, SITES]
        elif a in ("W7", "E7"):
            f = window(x)
        else:
            f = attention4(x, sd["addition.attn_q"], sd["addition.attn_k"], sd["addition.attn_v"])
        z = f.reshape(-1, f.shape[-1]) @ sd["addition.wq"].T
        return z / z.norm(dim=-1, keepdim=True).clamp_min(1e-8)

    def forward(self, tokens, *, disabled=False, values=None):
        """logits [B, 8, 256] at the answer sites, the selection [B*8, 8] (or None), unit queries (or None)."""
        sd = self.sd
        e = sd["backbone.token.weight"][tokens] + sd["backbone.position.weight"][: tokens.shape[1]]
        h, _ = block(sd, 0, e)
        delta = torch.zeros_like(h)
        sel = q = None
        a = self.arm
        if not disabled and a not in ("BB-0",):
            if a in ("D", "D7", "BB-D"):
                f = window(h) if a == "D7" else h[:, SITES]
                g = f @ sd["addition.w1"].T
                delta[:, SITES] = torch.sigmoid(sd["addition.gate"]) * ((0.5 * g * (1 + torch.erf(g / math.sqrt(2)))) @ sd["addition.w2"].T)
            else:
                table = sd["addition.values"] if values is None else values
                if a == "R2":
                    slots = torch.tensor([self.slot_of.get(c, -1) for c in ident_codes(tokens).reshape(-1).tolist()])
                    read = table[slots.clamp_min(0)] * (slots >= 0).to(torch.float32)[:, None]
                    sel = slots[:, None]
                else:
                    q = self.query(tokens, e, h)
                    sel, sc = top8(q, sd["addition.keys"])
                    w = sc.softmax(-1)
                    read = (w[..., None] * table[sel]).sum(1)
                delta[:, SITES] = torch.sigmoid(sd["addition.gate"]) * (read.reshape(tokens.shape[0], 8, 32) @ sd["addition.wo"].T)
        out, _ = block(sd, 1, h + delta)
        out = ln(out, sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"])
        return (out @ sd["backbone.token.weight"].T)[:, SITES], sel, q


def correct_ties_wrong(logits, answers):
    z = logits[..., ALPHA]
    mine = z.gather(-1, answers[..., None]).squeeze(-1)
    other = z.scatter(-1, answers[..., None], -math.inf).amax(-1)
    return mine > other


def derangement(table, seed=977):
    n = table.shape[0]
    perm = torch.randperm(n, generator=torch.Generator().manual_seed(seed))
    out = torch.empty_like(table)
    out[perm] = table[perm.roll(-1)]
    return out


def next_byte_loss(sd, rows):
    tot, cnt = 0.0, 0
    for s in range(0, rows.shape[0], 256):
        ch = rows[s : s + 256]
        x = ch[:, :64]
        e = sd["backbone.token.weight"][x] + sd["backbone.position.weight"][:64]
        h, _ = block(sd, 0, e)
        h, _ = block(sd, 1, h)
        lg = ln(h, sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"]) @ sd["backbone.token.weight"].T
        tot += float(F.cross_entropy(lg.reshape(-1, 256), ch[:, 1:65].reshape(-1), reduction="sum"))
        cnt += ch[:, 1:65].numel()
    return tot / cnt


# ---------------- data ----------------
manifest = json.loads((RUN / "data_manifest.json").read_text())
sd_seeds = dict(manifest["seeds"])
name = sd_seeds.pop("name")
sd_seeds["null_seeds_a"] = tuple(sd_seeds["null_seeds_a"])
sd_seeds["null_seeds_b"] = tuple(sd_seeds["null_seeds_b"])
seeds = p9core.SeedSet(name, **sd_seeds)
corpus = p9core.load_trained_corpus(ROOT)
study = p9data.build_study_data(seeds, corpus)
regen = study.sha256s()
print("seed set", name, "| regenerated hashes equal the manifest's:", regen == manifest["sha256s"], "| count", len(regen))
if regen != manifest["sha256s"]:
    raise SystemExit("data mismatch")
rows = torch.frombuffer(bytearray(corpus), dtype=torch.uint8).to(torch.int64).reshape(-1, 65)
backbones = {}
for label in LABELS:
    ev = json.loads((RUN / "cells" / label / "eval" / "u0008192" / "eval.json").read_text())
    snap = torch.load(RUN / "cells" / label / "snapshots" / "u0008192" / "model.pt", weights_only=True)["model"]
    parent = tuple(ev["parent"])
    if parent not in backbones:
        backbones[parent] = {"backbone." + k: v.detach().clone() for k, v in controls.load_backbone(parent, ROOT)[0].state_dict().items() if k != "mask"}
    frozen = backbones[parent]
    arm = label.split("-n")[0]
    trainable_bb = ("blocks.0.qkv", "blocks.0.attn_out") if arm.startswith("BB") else ()
    same_frozen = all(torch.equal(snap[k], v) for k, v in frozen.items() if not any(t in k for t in trainable_bb))
    moved_bb = {k: float((snap[k] - v).norm()) for k, v in frozen.items() if any(t in k for t in trainable_bb)}
    slots = int(label.split("-n")[1].split("-")[0])
    nf = FACTS_OF[slots]
    idents = study.facts.ident[:nf]
    enc = (idents[:, :4] * torch.tensor([1, 32, 1024, 32768])).sum(-1).tolist()
    cell = Cell(label, snap, seeds.r1_codes, {c: i for i, c in enumerate(enc)})
    row = {"label": label, "frozen_part_equals_verified_backbone": same_frozen, "trained_block0_change_norms": moved_bb}
    with torch.no_grad():
        for panel, stream in (("A", "panel_a"), ("B", "panel_b")):
            st = study.streams[stream]
            keep = (st.fact_ids < nf).all(1) | (st.fact_ids >= TRAINED_TOTAL).all(1)
            toks, fids = st.tokens[keep], st.fact_ids[keep]
            ok_all, off_all, perm_all, sels, qs = [], [], [], [], []
            permuted = derangement(snap["addition.values"]) if "addition.values" in snap else None
            for s in range(0, toks.shape[0], 512):
                t = toks[s : s + 512]
                ans = t[:, [p + 1 for p in SITES]] - 0x40
                lg, sel, q = cell.forward(t[:, :63])
                ok_all.append(correct_ties_wrong(lg, ans))
                off_all.append(correct_ties_wrong(cell.forward(t[:, :63], disabled=True)[0], ans))
                if permuted is not None:
                    perm_all.append(correct_ties_wrong(cell.forward(t[:, :63], values=permuted)[0], ans))
                if sel is not None:
                    sels.append(sel)
                if q is not None:
                    qs.append(q)
            ok, off = torch.cat(ok_all).reshape(-1), torch.cat(off_all).reshape(-1)
            ids = fids.reshape(-1)
            tr, un = ids < nf, ids >= TRAINED_TOTAL
            res = {"facts": int(tr.sum()), "correct": int(ok[tr].sum()), "unseen_correct": int(ok[un].sum()), "unseen": int(un.sum()),
                   "disabled_correct": int(off[tr].sum())}
            if perm_all:
                res["permuted_correct"] = int(torch.cat(perm_all).reshape(-1)[tr].sum())
            if sels:
                allsel = torch.cat(sels).reshape(-1)
                res["distinct_selected_slots"] = int(torch.unique(allsel[allsel >= 0]).numel())
            if qs:
                Q = torch.cat(qs)[tr].to(torch.float64)
                n = Q.shape[0]
                tot = Q.sum(0)
                res["mean_cosine_different"] = float((tot @ tot - n) / (n * (n - 1)))
                near = 0
                Q32 = Q.float()
                for s in range(0, n, 2048):
                    sim = Q32[s : s + 2048] @ Q32.T
                    r = torch.arange(sim.shape[0])
                    sim[r, s + r] = -2.0
                    near += int((sim.max(1).values > 0.9).sum())
                res["share_nearest_above_0_9"] = near / n
            rec = ev["panels"][panel]
            res["record"] = {k: rec.get(k) for k in ("correct", "unseen_correct", "disabled_correct", "permuted_correct", "distinct_selected_slots")}
            if "query" in rec:
                res["record"]["mean_cosine_different"] = rec["query"]["mean_cosine_different"]
                res["record"]["share_nearest_above_0_9"] = rec["query"]["share_nearest_above_0_9"]
            diffs = {k: (res.get(k), v) for k, v in res["record"].items() if v is not None and k in res and
                     (abs(res[k] - v) > 1e-9 if isinstance(v, float) else res[k] != v)}
            res["differences_own_vs_record"] = diffs
            row[panel] = res
        if arm.startswith("BB"):
            before = next_byte_loss({**snap, **frozen}, rows)
            after = next_byte_loss(snap, rows)
            row["lm_own"] = {"before": before, "after": after, "rise": (after - before) / before}
            row["lm_record"] = ev["language_modelling"]
    print(json.dumps(row))
