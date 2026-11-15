"""A10 (auditor, Opus 5.5): gate G2 and the controls of the calibration, recomputed.

No-memory baseline on rehearsal draw 1 (Panels A and B; 2,048 / 8,192 / 32,768 trained facts and the
2,048 unseen controls) with the auditor's own backbone forward (nothing added) and ties-wrong scoring;
the exact binomial central interval of level 1 - 0.001/8 around 1/32 computed here with lgamma; exact
retrieval as a dictionary lookup of the fact table checked against the answer bytes in the panel tokens.
Compared with calibration_controls.json. usage: a10_g2_controls.py RUN_DIR EXPERIMENTS_ROOT
"""
import json
import math
import sys
from pathlib import Path

import torch

from studies.p9 import controls, data as p9data
from studies.p9 import core as p9core

torch.set_num_threads(2)
RUN, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
SITES = [8 * r + 6 for r in range(8)]
ALPHA = list(range(0x40, 0x60))
ns: dict = {}
src = Path(__file__).with_name("a4_arm_forward.py").read_text()
exec(compile("import math\nimport torch\n" + src.split("def attention4")[0].split("frozen_copy = ")[1].split("\n", 1)[1], "a4_functions", "exec"), ns)  # noqa: S102
block, ln = ns["block"], ns["ln"]


def interval(n: int, p: float = 1 / 32, alpha: float = 0.001, tests: int = 8) -> tuple[int, int]:
    tail = alpha / tests / 2
    logpmf = [math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p) for k in range(n + 1)]
    pmf = [math.exp(v) for v in logpmf]
    c, lo = 0.0, 0
    for k in range(n + 1):
        c += pmf[k]
        if c > tail:
            lo = k
            break
    c, hi = 0.0, n
    for k in range(n, -1, -1):
        c += pmf[k]
        if c > tail:
            hi = k
            break
    return lo, hi


seeds = p9core.rehearsal_seeds(1)
study = p9data.build_study_data(seeds, p9core.load_trained_corpus(ROOT))
idents = study.facts.ident
enc_all = (idents[:, :4] * torch.tensor([1, 32, 1024, 32768])).sum(-1).tolist()
index_of = {c: i for i, c in enumerate(enc_all)}
trained_total = study.facts.trained
rec = json.loads((RUN / "calibration_controls.json").read_text())["controls"]
print("seed set:", seeds.name, "| unseen controls:", idents.shape[0] - trained_total)
for parent, key in (((101, 301), "no_memory"), ((102, 302), "no_memory_replicate")):
    sd = {"backbone." + k: v for k, v in controls.load_backbone(parent, ROOT)[0].state_dict().items()}
    for panel, name in (("A", "panel_a"), ("B", "panel_b")):
        toks = study.streams[name].tokens
        counts = {2048: [0, 0], 8192: [0, 0], 32768: [0, 0], "unseen": [0, 0]}
        exact_ok = True
        with torch.no_grad():
            for s in range(0, toks.shape[0], 512):
                t = toks[s : s + 512]
                x = sd["backbone.token.weight"][t[:, :63]] + sd["backbone.position.weight"][:63]
                h = block(sd, 1, block(sd, 0, x))
                z = (ln(h, sd["backbone.final_norm.weight"], sd["backbone.final_norm.bias"]) @ sd["backbone.token.weight"].T)[:, SITES][..., ALPHA]
                ans = t[:, [p + 1 for p in SITES]] - 0x40
                mine = z.gather(-1, ans[..., None]).squeeze(-1)
                ok = mine > z.scatter(-1, ans[..., None], -math.inf).amax(-1)
                for r in range(t.shape[0]):
                    ids = [index_of[sum(((int(t[r, 8 * q + 1 + i]) - 0x40) % 32) * 32**i for i in range(4))] for q in range(8)]
                    for q, fid in enumerate(ids):
                        if fid < trained_total and int(study.facts.answer[fid]) != int(ans[r, q]):
                            exact_ok = False
                    if all(f >= trained_total for f in ids):
                        counts["unseen"][0] += int(ok[r].sum()); counts["unseen"][1] += 8
                    for F_ in (2048, 8192, 32768):
                        if all(f < F_ for f in ids):
                            counts[F_][0] += int(ok[r].sum()); counts[F_][1] += 8
        for k, (c, n) in counts.items():
            lo, hi = interval(n)
            theirs = rec[key][panel][str(k)]
            print(f"{key:19} {panel} {k!s:>6}: auditor {c}/{n} interval [{lo}, {hi}] inside={lo <= c <= hi} | run {theirs['correct']}/{theirs['facts']}")
        if parent == (101, 301):
            print(f"  exact retrieval (fact-table answers equal the answer bytes in panel {panel}): {exact_ok}")
print("run's G2 intervals:", [(r["name"], r["interval"]) for r in rec["g2"]["results"]], "passed:", rec["g2"]["passed"], "level", rec["g2"]["level"])
