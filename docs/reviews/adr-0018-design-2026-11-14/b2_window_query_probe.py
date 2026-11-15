"""B2 - representation-only feasibility probe of the ADR-0018 query interfaces on the FROZEN backbones,
rehearsal draw 0 (seeds 179001+; the draw that already informed the design; draw 1 is NOT touched).

Auditor's own code. ``studies.p9`` is used only to regenerate rehearsal draw 0 and to load the verified
frozen backbones (through the calibration audit's ``_common``). No memory is built or trained: there
are no learned keys, no learned values, no output projection, no gate, no block 1. For each candidate
query map phi (N, E7, W7, A1 ...), phi is fitted by a CONTRASTIVE objective that asks two occurrences of
the same fact in different contexts to have the same unit query and different facts different
queries. Then an ORACLE store is formed: key_f = normalized mean of phi over the fact's training
occurrences, value_f = one-hot of the fact's answer. Panel A queries (contexts never used) read it
exactly as ADR-0017 5.1 does (cosine, top-8, softmax at temperature 0.2), and the answer is the
symbol with the largest mass (ties wrong).

This measures whether the representation the interface sees can ADDRESS the facts, with the
interface's functional form; it does not measure whether the study's answer loss through top-8 would
find such a map (an optimistic probe), nor what learned keys and values could add (a pessimistic one).

Data: probe training uses EPOCHS epochs of the rehearsal training stream (each fact EPOCHS times, in
the study's own training contexts); test is rehearsal Panel A restricted to the trained facts.

Interfaces (key width d = 16 unless named):
  N        W h_t                                   (answer-site state only)
  E7       W [e_{t-6}..e_t]                        (token+position embeddings, no block)
  W7       W [h_{t-6}..h_t]
  W7-k32   as W7, d = 32
  W7-mlp   MLP([h_{t-6}..h_t]) 224 -> 256 GELU -> d
  A1-16    one head, q from h_t, k, v from h_{t-15..t}, 32 wide, bias-free, then W (ADR-0018 A1)
  A1-7     the same head over h_{t-6..t}
  A1E-16   the A1-16 head over embeddings e
  R1       fixed random unit code per fact (reference; context-free)

Usage: PYTHONPATH=docs/reviews/p9-calibration-audit-2026-11-14 uv run --locked python \
       docs/reviews/adr-0018-design-2026-11-14/b2_window_query_probe.py <parent> <F> [variants...]
"""

import json
import math
import sys
import time
from pathlib import Path

import _common as c
import torch
from torch.nn import functional as F

from studies.p9 import data as p9data

OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)
TOP, TEMP, S = 8, 0.2, 32
EPOCHS, STEPS, TT = 8, 2000, 0.05
VARIANTS = ["N", "E7", "W7", "W7-k32", "W7-mlp", "A1-16", "A1-7", "A1E-16", "R1"]


@torch.no_grad()
def states(bb, tokens, chunk=1024):
    e, h = [], []
    for s in range(0, len(tokens), chunk):
        x = tokens[s : s + chunk, :63]
        e.append(c.embed(bb, x))
        h.append(c.hidden0(bb, x))
    return torch.cat(e), torch.cat(h)


def windows(x, length):
    """x [C, 63, 32] -> [C*8, length, 32] windows ending at each answer site 8r+6, plus validity mask."""
    cnum = x.shape[0]
    site = torch.arange(8) * 8 + 6
    pos = site[:, None] + torch.arange(-length + 1, 1)[None, :]  # [8, length]
    valid = pos >= 0
    w = x[:, pos.clamp_min(0)]  # [C, 8, length, 32]
    return w.reshape(cnum * 8, length, 32), valid.repeat(cnum, 1)


class Lin(torch.nn.Module):
    def __init__(self, inp, d):
        super().__init__()
        self.w = torch.nn.Parameter(torch.randn(d, inp) / math.sqrt(inp))

    def forward(self, x, mask):
        return x.reshape(len(x), -1) @ self.w.T


class Mlp(torch.nn.Module):
    def __init__(self, inp, d):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(inp, 256), torch.nn.GELU(), torch.nn.Linear(256, d))

    def forward(self, x, mask):
        return self.net(x.reshape(len(x), -1))


class Head(torch.nn.Module):
    """ADR-0018 A1: one causal head, query from the last position, 32 wide, bias-free, then W."""

    def __init__(self, d):
        super().__init__()
        self.q, self.k, self.v = (torch.nn.Parameter(torch.randn(32, 32) / math.sqrt(32)) for _ in range(3))
        self.w = torch.nn.Parameter(torch.randn(d, 32) / math.sqrt(32))
        self.last_attention = None

    def forward(self, x, mask):
        q = x[:, -1] @ self.q.T
        k = x @ self.k.T
        v = x @ self.v.T
        s = (k @ q[:, :, None]).squeeze(-1) / math.sqrt(32)
        s = s.masked_fill(~mask, float("-inf"))
        a = s.softmax(-1)
        self.last_attention = a.detach()
        return (a[:, :, None] * v).sum(1) @ self.w.T


def make(variant):
    d = 32 if variant == "W7-k32" else 16
    if variant == "N":
        return Lin(32, d), "h", 1
    if variant == "E7":
        return Lin(224, d), "e", 7
    if variant in ("W7", "W7-k32"):
        return Lin(224, d), "h", 7
    if variant == "W7-mlp":
        return Mlp(224, d), "h", 7
    if variant == "A1-16":
        return Head(d), "h", 16
    if variant == "A1-7":
        return Head(d), "h", 7
    if variant == "A1E-16":
        return Head(d), "e", 16
    raise ValueError(variant)


@torch.no_grad()
def read(q, keys, ans_q, ans_keys):
    """Oracle store read: q [Q, d] unit, keys [F, d] unit (row = fact id), answers. Returns metrics."""
    correct, top1, in8, wself = 0, 0, 0, []
    fact_q = torch.arange(len(q))  # Panel A rows are ordered by fact id by the caller
    for s in range(0, len(q), 2048):
        rows = fact_q[s : s + 2048]
        sc = q[rows] @ keys.T
        cs, i = sc.topk(TOP, dim=1)
        w = (cs / TEMP).softmax(1)
        hit = (i == rows[:, None])
        top1 += int(hit[:, 0].sum())
        in8 += int(hit.any(1).sum())
        wself.append((w * hit.float()).sum(1))
        mass = torch.zeros(len(rows), S).scatter_add_(1, ans_keys[i], w)
        own = mass.gather(1, ans_q[rows][:, None]).squeeze(1)
        mass.scatter_(1, ans_q[rows][:, None], -1.0)
        correct += int((own > mass.max(1).values).sum())
    ws = torch.cat(wself)
    n = len(q)
    return {"accuracy": round(correct / n, 4), "own_first": round(top1 / n, 4), "own_in_top8": round(in8 / n, 4),
            "median_w_self": round(float(ws.median()), 4)}


def main():
    parent, facts = sys.argv[1], int(sys.argv[2])
    variants = sys.argv[3:] or VARIANTS
    torch.manual_seed(180777)
    s = c.study()
    bb = c.backbone(parent)
    ts = p9data.make_training_stream(s.facts, torch.arange(facts), s.templates,
                                     p9data._derive(s.seeds.training_order, "main"))
    upe = ts.updates_per_epoch
    tok, fid = [], []
    for u in range(1, EPOCHS * upe + 1):
        b = ts.batch(u)
        tok.append(b.tokens)
        fid.append(b.fact_ids)
    tr_tok, tr_fid = torch.cat(tok), torch.cat(fid).reshape(-1)
    te_tok, te_fid = c.restrict(s.streams["panel_a"], facts)
    te_fid = te_fid.reshape(-1)
    order = te_fid.argsort()
    assert torch.equal(te_fid[order], torch.arange(facts))
    answer = s.facts.answer[:facts]
    assert torch.equal((tr_tok.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1), answer[tr_fid])
    e_tr, h_tr = states(bb, tr_tok)
    e_te, h_te = states(bb, te_tok)
    scale = {"h": h_tr.reshape(-1, 32).std(0), "e": e_tr.reshape(-1, 32).std(0)}
    src_tr = {"h": h_tr / scale["h"], "e": e_tr / scale["e"]}
    src_te = {"h": h_te / scale["h"], "e": e_te / scale["e"]}
    # occurrences of each fact in the probe training data
    occ = tr_fid.argsort().reshape(facts, EPOCHS)
    assert torch.equal(tr_fid[occ], torch.arange(facts)[:, None].expand(facts, EPOCHS))
    results = []
    for variant in variants:
        t0 = time.time()
        if variant == "R1":
            g = torch.Generator().manual_seed(180101)
            code = F.normalize(torch.randn(facts, 16, generator=g), dim=1)
            r = read(code, code, answer, answer)
            row = {"parent": parent, "facts": facts, "variant": "R1"} | r
            print(json.dumps(row), flush=True)
            results.append(row)
            continue
        model, src, length = make(variant)
        xw_tr, m_tr = windows(src_tr[src], length)
        xw_te, m_te = windows(src_te[src], length)
        xw_te, m_te = xw_te[order], m_te[order]
        lr = 0.01 if isinstance(model, Lin) else 0.003
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        g = torch.Generator().manual_seed(180778)
        batch = min(facts, 8192)
        for step in range(STEPS):
            f = torch.randperm(facts, generator=g)[:batch]
            pick = torch.stack([torch.randperm(EPOCHS, generator=g)[:2] for _ in range(1)]).expand(batch, 2)
            pick = (pick + torch.randint(0, EPOCHS, (batch, 1), generator=g)) % EPOCHS
            ra, rb = occ[f, pick[:, 0]], occ[f, pick[:, 1]]
            za = F.normalize(model(xw_tr[ra], m_tr[ra]), dim=1)
            zb = F.normalize(model(xw_tr[rb], m_tr[rb]), dim=1)
            logits = za @ zb.T / TT
            tgt = torch.arange(batch)
            loss = 0.5 * (F.cross_entropy(logits, tgt) + F.cross_entropy(logits.T, tgt))
            opt.zero_grad()
            loss.backward()
            opt.step()
        with torch.no_grad():
            z = torch.cat([F.normalize(model(xw_tr[i : i + 8192], m_tr[i : i + 8192]), dim=1)
                           for i in range(0, len(xw_tr), 8192)])
            keys = F.normalize(z[occ].mean(1), dim=1)
            q = torch.cat([F.normalize(model(xw_te[i : i + 8192], m_te[i : i + 8192]), dim=1)
                           for i in range(0, len(xw_te), 8192)])
            r = read(q, keys, answer, answer)
            # training-context queries (one occurrence vs the same prototypes) to show the generalization gap
            r_train = read(z[occ[:, 0]], keys, answer, answer)
            cosq = q @ q[torch.randperm(facts, generator=g)[:2048]].T
            extra = {"mean_cos_between_facts": round(float(cosq.mean()), 4)}
            if isinstance(model, Head):
                model(xw_te[:8192], m_te[:8192])
                a = model.last_attention
                idpos = torch.arange(length - 6, length - 1)  # id1..id5 = offsets -5..-1
                extra["attention_on_identifier"] = round(float(a[:, idpos].sum(1).mean()), 4)
                extra["attention_profile_last7"] = [round(float(x), 3) for x in a[:, -7:].mean(0)]
        row = {"parent": parent, "facts": facts, "variant": variant, "final_loss": round(float(loss), 4)} | r | \
              {"train_contexts_accuracy": r_train["accuracy"]} | extra | {"sec": round(time.time() - t0, 1)}
        print(json.dumps(row), flush=True)
        results.append(row)
    name = f"b2_{parent}_{facts}_" + "_".join(variants) + ".json"
    (OUT / name).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
