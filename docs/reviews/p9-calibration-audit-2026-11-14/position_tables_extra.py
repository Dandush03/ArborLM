"""Follow-up to position_tables.py (kept unchanged): is the failure of ``fact_at_id5`` an optimisation
artefact? Extra oracle probes, same training loop and scorer:

  fact_at_prefix   the fact's dedicated row added at ALL six record positions before the answer site
                   (8r+0..8r+5): the most generous "perfect address, read anywhere but the site"
  fact_at_id5      as before, but run here with other learning rates (--lr)

Usage: uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/position_tables_extra.py \
          --probe fact_at_prefix --lr 0.003 [--sigma]
"""

import argparse
import json
import time

import _common as c
import position_tables as pt
import torch
from torch.nn import functional as F

from studies.p9 import core, data


class Extra(pt.Probe):
    def delta(self, s, tokens):
        if self.kind != "fact_at_prefix":
            return super().delta(s, tokens)
        b = tokens.shape[0]
        d = torch.zeros(b, 63, 32)
        f = pt.fact_ids(s, tokens)
        ok = ((f >= 0) & (f < self.facts))[..., None]
        rows = self.tf[f.clamp(0, self.facts - 1)] * ok
        for off in range(6):
            d = d.index_add(1, pt.SITES - 6 + off, rows)
        return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, choices=["fact_at_prefix", "fact_at_id5"])
    ap.add_argument("--facts", type=int, default=2048)
    ap.add_argument("--updates", type=int, default=8192)
    ap.add_argument("--every", type=int, default=1024)
    ap.add_argument("--parent", default="b101")
    ap.add_argument("--sigma", action="store_true")
    ap.add_argument("--lr", type=float, default=0.003)
    a = ap.parse_args()
    s = c.study()
    bb = c.backbone(a.parent)
    stream = data.training_stream_for(s, core.parse_label(pt.LABEL[a.facts]))
    panels = {k: c.restrict(s.streams[n], a.facts)[0] for k, n in (("A", "panel_a"), ("B", "panel_b"))}
    probe = Extra("fact_at_id5" if a.probe == "fact_at_id5" else "fact_x", a.facts)
    probe.kind = a.probe
    probe.tf = torch.nn.Parameter(torch.zeros(a.facts, 32))
    params = list(probe.parameters())
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0, foreach=False)
    curve, t0 = [], time.time()
    for u in range(1, a.updates + 1):
        tokens = stream.batch(u).tokens
        lg = pt.logits(bb, s, probe, tokens)
        tgt = tokens[:, 1:][:, pt.SITES].reshape(-1)
        loss = F.cross_entropy(lg[:, c.ALPHABET], tgt - 0x40) if a.sigma else F.cross_entropy(lg, tgt)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        if u % a.every == 0:
            ev = pt.evaluate(bb, s, probe, panels)
            row = {"update": u, "loss": loss.item(), "acc_A": ev["A"], "acc_B": ev["B"], "row_norm_mean": float(probe.tf.norm(dim=1).mean()), "seconds": time.time() - t0}
            curve.append(row)
            print(json.dumps(row), flush=True)
    tag = f"{a.probe}_{a.facts}_{a.parent}_{'sigma' if a.sigma else 'full'}_lr{a.lr}"
    (c.OUT / f"position_tables_extra_{tag}.json").write_text(json.dumps({"args": vars(a), "curve": curve}, indent=1))


if __name__ == "__main__":
    main()
