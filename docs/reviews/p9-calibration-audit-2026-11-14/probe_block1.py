"""Audit item 6 input: does the residual AFTER block 1 (no memory) carry more of the identifier at the
answer site than after block 0? Logistic probe bits per identifier symbol (same method and split as
probes.py: calibration stream -> Panel A, F = 2,048 and 8,192), at the answer site and at id5.
Frozen backbone only; nothing trained except the probe.
"""

import json

import _common as c
import torch
from probes import ident_bits, logistic, nearest


@torch.no_grad()
def states(bb, tokens):
    h0, h1 = [], []
    for s in range(0, len(tokens), 512):
        x = tokens[s : s + 512, :63]
        a = c.hidden0(bb, x)
        h0.append(a)
        h1.append(c.block(bb.blocks[1], a))
    return torch.cat(h0), torch.cat(h1)


def main():
    s = c.study()
    out = []
    for parent in ("b101", "b102"):
        bb = c.backbone(parent)
        for facts in (2048, 8192):
            tr, tr_ids = c.restrict(s.streams["calibration"], facts)
            te, te_ids = c.restrict(s.streams["panel_a"], facts)
            sym_tr = s.facts.ident[tr_ids.reshape(-1)]
            sym_te = s.facts.ident[te_ids.reshape(-1)]
            ans_tr = s.facts.answer[tr_ids.reshape(-1)]
            ans_te = s.facts.answer[te_ids.reshape(-1)]
            _, h1tr = states(bb, tr)
            _, h1te = states(bb, te)
            row = {"parent": parent, "facts": facts}
            for name, off in (("bind", 6), ("id5", 5)):
                pos = torch.tensor([8 * r + off for r in range(8)])
                xa, xb = h1tr[:, pos].reshape(-1, 32), h1te[:, pos].reshape(-1, 32)
                res = [logistic(xa, sym_tr[:, i], xb, sym_te[:, i]) for i in range(5)]
                row[f"after_block1_{name}_acc"] = [r[0] for r in res]
                row[f"after_block1_{name}_bits"] = [r[1] for r in res]
                row[f"after_block1_{name}_ident_bits_lower_bound"] = ident_bits([r[1] for r in res])
                row[f"after_block1_{name}_nearest_answer"] = nearest(xa, ans_tr, xb, ans_te)
            print(json.dumps(row))
            out.append(row)
    (c.OUT / "probe_block1.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
