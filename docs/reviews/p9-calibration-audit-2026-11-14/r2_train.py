"""Audit item 2 (experiments): the auditor's own R2 trainer on REHEARSAL draw 0 only.

Own implementation of the R2 rung (ADR 5.3): one dedicated value row per fact (slot = fact id,
found from the identifier bytes), weight 1, read at the 8 answer sites only; delta = sigmoid(gate) *
wo @ value; values N(0, 0.02) seed init+2000, wo seed init+4000 (arborlm.pilot_model._matrix, as P5),
gate -2.0; AdamW lr 0.003, betas (0.9, 0.999), eps 1e-8, wd 0, total-norm clip 1.0; answer-site
cross-entropy over all 256 bytes (the implementer's loss). The batch schedule is the study's
rehearsal-0 training stream (``data.training_stream_for``), init seeds 179001 / 179002.

Variants (``--variant``):
  base         as above (reproduces the calibration cell when run to its own U)
  sigma_loss   cross-entropy over the 32 alphabet logits only (scoring rule's support)
  warm         wo and gate copied from the given --warm snapshot (a converged larger-size R2 cell of the
               SAME parent); values fresh
  lr           base with --lr different from 0.003 (all parameters)
Evaluation: own scorer on Panels A and B restricted to F every --every updates.

Usage: uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/r2_train.py \
          --slots 4096 --parent b101 --init 179001 --updates 8192 --variant base --tag NAME
"""

import argparse
import json
import time
from pathlib import Path

import _common as c
import torch
from arborlm.pilot_model import _matrix
from torch.nn import functional as F

from studies.p9 import core, data

FACTS = {4096: 2048, 16384: 8192, 65536: 32768}
SITES = torch.tensor([8 * r + 6 for r in range(8)])


def slots_of(s, tokens):
    ident = s.facts.ident
    w = torch.tensor([1, 32, 1024, 32768])
    lut = torch.full((32**4,), -1, dtype=torch.int64)
    lut[(ident[:, :4] * w).sum(1)] = torch.arange(len(ident))
    return lut[((tokens.reshape(-1, 8, 8)[:, :, 1:5] - 0x40) * w).sum(-1)]


def forward(bb, tokens, slot, values, wo, gate, facts):
    h = c.hidden0(bb, tokens[:, :63])
    valid = (slot >= 0) & (slot < facts)
    read = values[slot.clamp_min(0)] * valid[..., None]
    delta = torch.sigmoid(gate) * read @ wo.T
    h = h.index_add(1, SITES, delta)
    return c.head(bb, h)[:, SITES].reshape(-1, 256)


@torch.no_grad()
def evaluate(bb, panels, values, wo, gate, facts):
    out = {}
    for key, (tok, sl) in panels.items():
        cr, ps, pf, ans = [], [], [], []
        for st in range(0, len(tok), 512):
            lg = forward(bb, tok[st : st + 512], sl[st : st + 512], values, wo, gate, facts)
            a = (tok[st : st + 512].reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1)
            r = c.score(lg, a)
            cr.append(r[0])
            ps.append(r[1])
            pf.append(r[2])
            ans.append(a)
        cr, ans = torch.cat(cr), torch.cat(ans)
        out[key] = {
            "acc": cr.float().mean().item(),
            "p_sigma": torch.cat(ps).mean().item(),
            "p_full": torch.cat(pf).mean().item(),
            "fail_by_symbol": [int((~cr[ans == a]).sum()) for a in range(32)],
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", type=int, default=4096)
    ap.add_argument("--parent", default="b101")
    ap.add_argument("--init", type=int, default=179001)
    ap.add_argument("--updates", type=int, default=8192)
    ap.add_argument("--every", type=int, default=256)
    ap.add_argument("--variant", default="base", choices=["base", "sigma_loss", "warm", "lr"])
    ap.add_argument("--lr", type=float, default=0.003)
    ap.add_argument("--warm", default=None)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    assert a.init >= 179001
    core.assert_not_registered_seed(a.init)
    facts = FACTS[a.slots]
    s = c.study()
    bb = c.backbone(a.parent)
    label = f"CAL-A5-flat-R2-n{a.slots}-b101-o301-s1701"
    stream = data.training_stream_for(s, core.parse_label(label))  # schedule depends on facts only
    assert stream.facts.shape[0] == facts and stream.order_seed == data._derive(s.seeds.training_order, "main")
    panels = {}
    for key, name in (("A", "panel_a"), ("B", "panel_b")):
        tok, ids = c.restrict(s.streams[name], facts)
        sl = slots_of(s, tok)
        assert torch.equal(sl, ids)
        panels[key] = (tok, sl)
    values = torch.nn.Parameter(_matrix(a.init + 2000, a.slots, 32))
    wo = torch.nn.Parameter(_matrix(a.init + 4000, 32, 32))
    gate = torch.nn.Parameter(torch.tensor(-2.0))
    if a.variant == "warm":
        m = torch.load(Path(a.warm) / "model.pt", weights_only=True)["model"]
        with torch.no_grad():
            wo.copy_(m["addition.wo"])
            gate.copy_(m["addition.gate"])
    params = [values, wo, gate]
    opt = torch.optim.AdamW(params, lr=a.lr, betas=(0.9, 0.999), eps=1e-8, weight_decay=0, foreach=False)
    curve = []
    t0 = time.time()
    for u in range(1, a.updates + 1):
        tokens = stream.batch(u).tokens
        slot = slots_of(s, tokens)
        logits = forward(bb, tokens, slot, values, wo, gate, facts)
        target = tokens[:, 1:][:, SITES].reshape(-1)
        if a.variant == "sigma_loss":
            loss = F.cross_entropy(logits[:, c.ALPHABET], target - 0x40)
        else:
            loss = F.cross_entropy(logits, target)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        if u % a.every == 0 or u in (512, 1024, 2048):
            ev = evaluate(bb, panels, values.detach(), wo.detach(), gate.detach(), facts)
            row = {
                "update": u,
                "exposure": u * 128 // facts,
                "loss": float(loss),
                "acc_A": ev["A"]["acc"],
                "acc_B": ev["B"]["acc"],
                "p_sigma_A": ev["A"]["p_sigma"],
                "p_full_A": ev["A"]["p_full"],
                "fail_by_symbol_A": ev["A"]["fail_by_symbol"],
                "sigmoid_gate": float(torch.sigmoid(gate)),
                "wo_fro": float(wo.norm()),
                "seconds": time.time() - t0,
            }
            curve.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != "fail_by_symbol_A"}), flush=True)
    out = {"args": vars(a), "facts": facts, "curve": curve}
    (c.OUT / f"r2_train_{a.tag}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
