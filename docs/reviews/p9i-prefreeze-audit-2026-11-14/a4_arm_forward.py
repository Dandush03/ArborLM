"""A4 (auditor, Opus 5.5): every arm's forward against an independent implementation of section I.3,
causality / leakage probes, parameter counts, gradient reach and backbone immutability.

The reference forward below is written from the ADR text (frozen block 0 -> h; e = token + position
embedding; read at answer sites 8r+6 only; cosine keys, top 8 with ties to the lowest slot id,
temperature 0.2, gate * wo; dense sigmoid(gate) * w2 gelu(w1 f) at answer sites only; frozen block 1,
final norm, tied output). The implementer's models are built with studies.p9i.model.build_model on the
verified B101 backbone, all their addition parameters are re-drawn at a larger scale so that the
memory term is not negligible, and logits are compared. Random byte tokens (test seed 900001).
"""
import math
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9i import core, model as m, train

torch.set_num_threads(2)
torch.manual_seed(900001)
ROOT = Path(sys.argv[1])
SITES = [8 * r + 6 for r in range(8)]
bb = controls.load_backbone(core.PRIMARY_PARENT, ROOT)[0]
frozen_copy = {k: v.clone() for k, v in bb.state_dict().items()}


def ln(x, w, b):
    mu = x.mean(-1, keepdim=True)
    var = ((x - mu) ** 2).mean(-1, keepdim=True)
    return (x - mu) / torch.sqrt(var + 1e-5) * w + b


def block(sd, i, h):
    p = f"backbone.blocks.{i}."
    b, t, _ = h.shape
    qkv = (ln(h, sd[p + "attn_norm.weight"], sd[p + "attn_norm.bias"]) @ sd[p + "qkv.weight"].T + sd[p + "qkv.bias"]).reshape(b, t, 3, 4, 8)
    q, k, v = (qkv[:, :, j].permute(0, 2, 1, 3) for j in range(3))
    s = (q @ k.transpose(-1, -2) / math.sqrt(8)).masked_fill(torch.ones(t, t, dtype=torch.bool).triu(1), -math.inf)
    h = h + (s.softmax(-1) @ v).permute(0, 2, 1, 3).reshape(b, t, 32) @ sd[p + "attn_out.weight"].T + sd[p + "attn_out.bias"]
    f = ln(h, sd[p + "ffn_norm.weight"], sd[p + "ffn_norm.bias"]) @ sd[p + "ffn_in.weight"].T + sd[p + "ffn_in.bias"]
    return h + (0.5 * f * (1 + torch.erf(f / math.sqrt(2)))) @ sd[p + "ffn_out.weight"].T + sd[p + "ffn_out.bias"]


def attention4(x, aq, ak, av, t_sites):
    """4 heads x 8, bias-free, query at t from x_t, keys/values over x_0..x_t, 1/sqrt(8), no norm, no out proj."""
    out = []
    for t in t_sites:
        heads = []
        for hd in range(4):
            sl = slice(8 * hd, 8 * hd + 8)
            q = x[:, t] @ aq[sl].T  # [B, 8]
            k = x[:, : t + 1] @ ak[sl].T  # [B, t+1, 8]
            v = x[:, : t + 1] @ av[sl].T
            w = ((k @ q[:, :, None]).squeeze(-1) / math.sqrt(8)).softmax(-1)
            heads.append((w[:, :, None] * v).sum(1))
        out.append(torch.cat(heads, -1))
    return torch.stack(out, 1)  # [B, 8, 32]


def reference(arm, sd, tokens):
    t = tokens.shape[1]
    e = sd["backbone.token.weight"][tokens] + sd["backbone.position.weight"][:t]
    h = block(sd, 0, e)
    delta = torch.zeros_like(h)
    a = lambda n: sd["addition." + n]  # noqa: E731
    if arm in ("N", "BB", "W7", "E7", "A4", "A4E"):
        x = e if arm in ("E7", "A4E") else h
        if arm in ("N", "BB"):
            f = x[:, SITES]
        elif arm in ("W7", "E7"):
            f = torch.stack([torch.cat([x[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)
        else:
            f = attention4(x, a("attn_q"), a("attn_k"), a("attn_v"), SITES)
        q = f @ a("wq").T
        q = q / q.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        kn = a("keys") / a("keys").norm(dim=-1, keepdim=True).clamp_min(1e-8)
        sc = q @ kn.T / 0.2
        idx = sc.argsort(dim=-1, descending=True, stable=True)[..., :8]
        w = sc.gather(-1, idx).softmax(-1)
        read = (w[..., None] * a("values")[idx]).sum(-2)
        delta[:, SITES] = torch.sigmoid(a("gate")) * read @ a("wo").T
    elif arm in ("D", "D7", "BB-D"):
        f = h[:, SITES] if arm != "D7" else torch.stack([torch.cat([h[:, s - 6 + j] for j in range(7)], -1) for s in SITES], 1)
        g = f @ a("w1").T
        delta[:, SITES] = torch.sigmoid(a("gate")) * (0.5 * g * (1 + torch.erf(g / math.sqrt(2)))) @ a("w2").T
    h = ln(block(sd, 1, h + delta), sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"])
    return h @ sd["backbone.token.weight"].T, e, h


tokens = torch.randint(0, 256, (6, 63))
expected_extra = {"W7": 3072, "E7": 3072, "A4": 3072, "A4E": 3072}
arms = ("N", "W7", "E7", "A4", "A4E", "D", "D7", "BB", "BB-D", "BB-0")
print(f"{'arm':5} {'max|logit diff|':>15} {'trainable':>9} {'bb-train':>8} {'extra':>5} {'hidden':>6} reach stray causal-ok nonsite-delta=0")
for arm in arms:
    net = m.build_model(arm, 4096, 900001, bb, seed_rng=False)
    with torch.no_grad():
        for n, p in net.named_parameters():
            if p.requires_grad and n.startswith("addition."):
                p.copy_(torch.randn_like(p) * (0.5 if p.ndim else 1.0) + (1.0 if p.ndim == 0 else 0.0))
            if p.requires_grad and n.startswith("backbone."):
                p.add_(torch.randn_like(p) * 0.05)
    net.eval()
    sd = {k: v.detach() for k, v in net.state_dict().items()}
    with torch.no_grad():
        mine, _ = net(tokens)
        ref, _, _ = reference(arm, sd, tokens)
    diff = float((mine - ref).abs().max())
    rep = m.parameter_report(net)
    # gradient reach on a 64-byte context with alphabet answers at the sites
    tk = tokens.clone()
    full = torch.cat([tk, torch.randint(0x40, 0x60, (6, 1))], 1)
    for s in SITES:
        full[:, s + 1] = torch.randint(0x40, 0x60, (6,))
    reach = train.gradient_reach(net, full)
    # causality: changing input position p must not change logits at any answer site s < p
    causal_ok = True
    with torch.no_grad():
        base, _ = net(tokens)
        for p in range(1, 63):
            t2 = tokens.clone()
            t2[:, p] = (t2[:, p] + 1 + torch.randint(0, 255, (6,))) % 256
            out, _ = net(t2)
            before = [s for s in SITES if s < p]
            if before and not torch.equal(out[:, before], base[:, before]):
                causal_ok = False
        h = net.embed_block0(tokens)
        d = net.memory_delta(h, net.select(h, tokens))
        nonsite = [i for i in range(63) if i not in SITES]
        zero_off_site = bool((d[:, nonsite] == 0).all())
    print(f"{arm:5} {diff:15.3e} {rep.trainable:9d} {rep.trainable_backbone:8d} {rep.interface_extra:5d} {rep.dense_hidden:6d} {all(reach['reached'].values())!s:5} {reach['stray']!s:5} {causal_ok!s:9} {zero_off_site}")
    if arm in expected_extra:
        assert rep.interface_extra == expected_extra[arm]

# E7 / A4E really bypass block 0: their selection must not change when block 0 is altered
with torch.no_grad():
    for arm in ("E7", "A4E", "W7", "A4", "N"):
        net = m.build_model(arm, 4096, 900002, bb, seed_rng=False)
        h = net.embed_block0(tokens)
        s1 = net.select(h, tokens).selected.clone()
        q1 = net.answer_queries(h, tokens).clone()
        for p in net.backbone.blocks[0].parameters():
            p.add_(torch.randn_like(p) * 0.3)
        h2 = net.embed_block0(tokens)
        q2 = net.answer_queries(h2, tokens)
        print(f"{arm}: query unchanged when block 0 is perturbed: {bool(torch.equal(q1, q2))}")

# E7 window: the query at site t must depend on tokens t-6..t only (no block, so exactly)
with torch.no_grad():
    for arm in ("E7",):
        net = m.build_model(arm, 4096, 900003, bb, seed_rng=False)
        q0 = net.answer_queries(net.embed_block0(tokens), tokens)
        ok_window, ok_outside = True, True
        for p in range(63):
            t2 = tokens.clone()
            t2[:, p] = (t2[:, p] + 7) % 256
            q = net.answer_queries(net.embed_block0(t2), t2)
            for r, s in enumerate(SITES):
                changed = not torch.equal(q[:, r], q0[:, r])
                if s - 6 <= p <= s and not changed:
                    ok_window = False
                if not (s - 6 <= p <= s) and changed:
                    ok_outside = False
        print(f"E7: query at t changes for every token in t-6..t: {ok_window}; unchanged for every token outside: {ok_outside}")

# BB: exactly the 4,224 block-0 attention parameters are trainable; the shared frozen backbone object is untouched
net = m.build_model("BB", 4096, 900004, bb, seed_rng=False)
names = sorted(n for n, p in net.named_parameters() if p.requires_grad and n.startswith("backbone."))
print("BB trainable backbone tensors:", names, sum(p.numel() for n, p in net.named_parameters() if n in names))
opt = train.build_optimizers(net)
full = torch.cat([tokens, torch.randint(0x40, 0x60, (6, 1))], 1)
for s in SITES:
    full[:, s + 1] = torch.randint(0x40, 0x60, (6,))
for _ in range(3):
    opt[0].zero_grad()
    logits, _ = net(full[:, :-1])
    train.alphabet_loss(logits, full).backward()
    opt[0].step()
print("shared backbone object unchanged after 3 BB steps:", all(torch.equal(v, frozen_copy[k]) for k, v in bb.state_dict().items()),
      "| requires_grad on shared backbone:", any(p.requires_grad for p in bb.parameters()))
print("model's own block-0 attention moved:", not torch.equal(net.backbone.blocks[0].qkv.weight, frozen_copy["blocks.0.qkv.weight"]),
      "| model's block-0 FFN / norms / block 1 / embeddings unchanged:",
      all(torch.equal(v, frozen_copy[k]) for k, v in net.backbone.state_dict().items() if not k.startswith(("blocks.0.qkv", "blocks.0.attn_out"))))
# D7 widths and parameter match at the three sizes
for s in core.SLOTS_BY_SIZE:
    hd = core.d7_hidden_width(s)
    w7 = core.memory_parameters(s) + 3072
    d7 = hd * 224 + 32 * hd + 1
    print(f"D7 {s}: hidden {hd}, D7 {d7}, W7 {w7}, rel diff {abs(d7 - w7) / w7:.2e}; D plain hidden {core.dense_plain_hidden_width(s)} -> {64 * core.dense_plain_hidden_width(s) + 1} vs N {core.memory_parameters(s)}")
