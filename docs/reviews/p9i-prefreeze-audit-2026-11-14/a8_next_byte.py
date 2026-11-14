"""A8 (auditor, Opus 5.5): the BB next-byte loss (section I.3.2, 15.4 item 7) against an independent
computation, and the 5% rule inputs. Uses the verified B101 backbone and the first 2,048 corpus rows
(65 bytes: inputs 0..63, targets 1..64). BB at initialization must give a relative rise of exactly 0.
"""
import math
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9i import core, evaluate, model as m

torch.set_num_threads(2)
ROOT = Path(sys.argv[1])
bb = controls.load_backbone(core.PRIMARY_PARENT, ROOT)[0]
rows = evaluate.corpus_rows(p9core.load_trained_corpus(ROOT))
print("corpus rows:", tuple(rows.shape))
sd = {"backbone." + k: v.double() for k, v in bb.state_dict().items()}
ns: dict = {}
src = Path(__file__).with_name("a4_arm_forward.py").read_text()
defs = "import math\nimport torch\n" + src.split("def attention4")[0].split("frozen_copy = ")[1].split("\n", 1)[1]
exec(compile(defs, "a4_functions", "exec"), ns)  # noqa: S102
block, ln = ns["block"], ns["ln"]
tot, cnt = 0.0, 0
with torch.no_grad():
    for s in range(0, rows.shape[0], 256):
        x = rows[s : s + 256]
        t = x[:, :64]
        h = sd["backbone.token.weight"][t] + sd["backbone.position.weight"][:64]
        h = block(sd, 1, block(sd, 0, h))
        z = ln(h, sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"]) @ sd["backbone.token.weight"].T
        tot += float(F.cross_entropy(z.reshape(-1, 256), x[:, 1:65].reshape(-1), reduction="sum"))
        cnt += x[:, 1:65].numel()
mine = tot / cnt
theirs = evaluate.next_byte_loss(bb, rows)
print(f"next-byte loss, frozen B101: auditor (float64) {mine:.7f} nats, implementer {theirs:.7f}, diff {abs(mine - theirs):.1e}")
net = m.build_model("BB", 4096, 900001, bb, seed_rng=False)
lm0 = evaluate.language_modelling(net, bb, rows[:512])
print("BB at initialization:", lm0)
with torch.no_grad():
    net.backbone.blocks[0].qkv.weight.add_(torch.randn_like(net.backbone.blocks[0].qkv.weight) * 0.05)
lm1 = evaluate.language_modelling(net, bb, rows[:512])
print("BB with perturbed block-0 qkv:", lm1, "| rule: degraded iff rise > 0.05:", lm1["degraded"] == (lm1["relative_rise"] > 0.05))
