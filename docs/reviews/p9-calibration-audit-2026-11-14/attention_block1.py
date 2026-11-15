"""Audit item 1: where does block 1 attend from the answer site (no memory)? Mean attention weight of
each of the 4 heads from the answer site 8r+6 to the record's own positions 8r+0..8r+6 and to all
earlier records together (Panel A, F = 2,048, records r >= 1). Also block 0 for comparison.
"""

import json

import _common as c
import torch
from torch.nn import functional as F


@torch.no_grad()
def attn(blk, h):
    b, t, d = h.shape
    x = F.layer_norm(h, (d,), blk.attn_norm.weight, blk.attn_norm.bias, 1e-5)
    q, k, _ = (x @ blk.qkv.weight.T + blk.qkv.bias).reshape(b, t, 3, 4, 8).permute(2, 0, 3, 1, 4).unbind(0)
    s = (q @ k.transpose(-2, -1)) / 8**0.5 + torch.full((t, t), float("-inf")).triu(1)
    return s.softmax(-1)  # [B, 4, T, T]


def main():
    s = c.study()
    tok, _ = c.restrict(s.streams["panel_a"], 2048)
    out = {}
    for parent in ("b101", "b102"):
        bb = c.backbone(parent)
        x = tok[:, :63]
        e = c.embed(bb, x)
        h0 = c.hidden0(bb, x)
        res = {}
        for name, blk, h in (("block0", bb.blocks[0], e), ("block1", bb.blocks[1], h0)):
            a = attn(blk, h)
            rows = {}
            for head in range(4):
                own = torch.zeros(7)
                earlier = 0.0
                for r in range(1, 8):
                    site = 8 * r + 6
                    own += a[:, head, site, 8 * r : 8 * r + 7].mean(0)
                    earlier += float(a[:, head, site, : 8 * r].sum(-1).mean())
                rows[f"head{head}"] = {"own_record_sep_id1..id5_bind": [round(float(v) / 7, 3) for v in own], "earlier_records": round(earlier / 7, 3)}
            res[name] = rows
        out[parent] = res
        print(parent, json.dumps(res))
    (c.OUT / "attention_block1.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
