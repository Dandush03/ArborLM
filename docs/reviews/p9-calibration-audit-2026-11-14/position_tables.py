"""Audit item 1 (in-principle bound for reading at all positions): frozen-upper-block capacity probes.

NOT a registered arm and not R0: no keys, no query projection, no top-k. Each probe adds a learned
vector to the block-0 residual, chosen by an ORACLE index that is a function of what one position can
see, and asks whether the frozen block 1 (one attention layer + FFN), final norm and tied output can
turn such per-position additions into the fact's answer. Rehearsal draw 0 only; init all-zero
tables (deterministic), AdamW lr 0.01, clip 1.0, batches of the study's rehearsal training stream.

  unigram    at EVERY input position p: T1[p mod 8, byte_p]   (what a query that resolves only the
             current byte can address; the measured frozen state carries ~5.4 bits per position,
             i.e. about one symbol)
  bigram     unigram + at identifier positions k = 2..5: T2[k, sym_k, sym_{k-1}] (10 bits per
             position: more than the frozen state carries; a generous bound)
  trigram    unigram + at k = 3..5: T3[k, sym_k, sym_{k-1}, sym_{k-2}] (15 bits; still more generous)
  fact_at_id5  one dedicated row per fact (full identifier, oracle), added at position 8r+5 only
             (the identifier's last byte, one position BEFORE the answer site): positive control for
             whether block 1 moves a perfectly addressed read from 8r+5 to the answer site
  fact_at_site  the same added at the answer site 8r+6 (= R2 with a direct table, positive control)

Loss: answer-site cross-entropy over all 256 bytes (as registered) or over the alphabet (--sigma).
Reported: accuracy within the alphabet (ties wrong) on Panels A and B restricted to F.

Usage: uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/position_tables.py \
          --probe unigram --facts 2048 --updates 8192 [--sigma] --parent b101
"""

import argparse
import json
import time

import _common as c
import torch
from torch.nn import functional as F

from studies.p9 import core, data

SITES = torch.tensor([8 * r + 6 for r in range(8)])
LABEL = {2048: "CAL-A5-flat-R2-n4096-b101-o301-s1701", 8192: "CAL-A5-flat-R2-n16384-b101-o301-s1701"}


def fact_ids(s, tokens):
    w = torch.tensor([1, 32, 1024, 32768])
    lut = torch.full((32**4,), -1, dtype=torch.int64)
    lut[(s.facts.ident[:, :4] * w).sum(1)] = torch.arange(len(s.facts.ident))
    return lut[((tokens.reshape(-1, 8, 8)[:, :, 1:5] - 0x40) * w).sum(-1)]


class Probe(torch.nn.Module):
    def __init__(self, kind, facts):
        super().__init__()
        self.kind, self.facts = kind, facts
        z = lambda *s: torch.nn.Parameter(torch.zeros(*s))  # noqa: E731
        if kind in ("unigram", "bigram", "trigram"):
            self.t1 = z(8, 256, 32)
        if kind == "bigram":
            self.t2 = z(8, 32, 32, 32)
        if kind == "trigram":
            self.t3 = z(8, 32 * 32 * 32, 32)
        if kind.startswith("fact"):
            self.tf = z(facts, 32)

    def delta(self, s, tokens):
        x = tokens[:, :63]
        b = x.shape[0]
        d = torch.zeros(b, 63, 32)
        k = torch.arange(63) % 8
        if hasattr(self, "t1"):
            d = d + self.t1[k[None].expand(b, -1), x]
        sym = (x - 0x40) & 31
        if hasattr(self, "t2"):
            for kk in (2, 3, 4, 5):
                p = torch.arange(kk, 63, 8)
                d[:, p] = d[:, p] + self.t2[kk, sym[:, p], sym[:, p - 1]]
        if hasattr(self, "t3"):
            for kk in (3, 4, 5):
                p = torch.arange(kk, 63, 8)
                idx = sym[:, p] * 1024 + sym[:, p - 1] * 32 + sym[:, p - 2]
                d[:, p] = d[:, p] + self.t3[kk, idx]
        if hasattr(self, "tf"):
            f = fact_ids(s, tokens)
            ok = ((f >= 0) & (f < self.facts))[..., None]
            rows = self.tf[f.clamp(0, self.facts - 1)] * ok
            pos = SITES - 1 if self.kind == "fact_at_id5" else SITES
            d = d.index_add(1, pos, rows)
        return d


def logits(bb, s, probe, tokens):
    h = c.hidden0(bb, tokens[:, :63]) + probe.delta(s, tokens)
    return c.head(bb, h)[:, SITES].reshape(-1, 256)


@torch.no_grad()
def evaluate(bb, s, probe, panels):
    out = {}
    for key, tok in panels.items():
        cr = []
        for st in range(0, len(tok), 256):
            tk = tok[st : st + 256]
            cr.append(c.score(logits(bb, s, probe, tk), (tk.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1))[0])
        out[key] = torch.cat(cr).float().mean().item()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", required=True, choices=["unigram", "bigram", "trigram", "fact_at_id5", "fact_at_site"])
    ap.add_argument("--facts", type=int, default=2048)
    ap.add_argument("--updates", type=int, default=8192)
    ap.add_argument("--every", type=int, default=1024)
    ap.add_argument("--parent", default="b101")
    ap.add_argument("--sigma", action="store_true")
    ap.add_argument("--lr", type=float, default=0.01)
    a = ap.parse_args()
    s = c.study()
    bb = c.backbone(a.parent)
    stream = data.training_stream_for(s, core.parse_label(LABEL[a.facts]))
    panels = {k: c.restrict(s.streams[n], a.facts)[0] for k, n in (("A", "panel_a"), ("B", "panel_b"))}
    probe = Probe(a.probe, a.facts)
    params = list(probe.parameters())
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0, foreach=False)
    curve, t0 = [], time.time()
    for u in range(1, a.updates + 1):
        tokens = stream.batch(u).tokens
        lg = logits(bb, s, probe, tokens)
        tgt = tokens[:, 1:][:, SITES].reshape(-1)
        loss = F.cross_entropy(lg[:, c.ALPHABET], tgt - 0x40) if a.sigma else F.cross_entropy(lg, tgt)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        if u % a.every == 0:
            with torch.no_grad():
                train_acc = c.score(lg, tgt - 0x40)[0].float().mean().item()
            ev = evaluate(bb, s, probe, panels)
            row = {"update": u, "loss": loss.item(), "train_batch_acc": train_acc, "acc_A": ev["A"], "acc_B": ev["B"], "seconds": time.time() - t0}
            curve.append(row)
            print(json.dumps(row), flush=True)
    tag = f"{a.probe}_{a.facts}_{a.parent}_{'sigma' if a.sigma else 'full'}_lr{a.lr}"
    (c.OUT / f"position_tables_{tag}.json").write_text(json.dumps({"args": vars(a), "curve": curve}, indent=1))


if __name__ == "__main__":
    main()
