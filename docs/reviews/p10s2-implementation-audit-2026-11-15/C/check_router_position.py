"""Auditor C: can a router whose input carries ONLY the position (no content) pass GEN under the registered recipe
(studies/p10s2/routing.train_router, RouterSpec.registered)? Stub student whose block-L output is a function of the
position alone. Test seeds only. Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""
import math, sys
from dataclasses import dataclass
PIN = sys.argv[1]; sys.path.insert(0, PIN); sys.path.insert(0, PIN + "/src")
import torch
from studies.p10s2 import core
from studies.p10s2.routing import RouterSpec, train_router, hidden_at_ends, false_triggers, class_counts

class Cfg: width = 576
class PositionOnlyStudent:
    cfg = Cfg()
    def block_output(self, ids, layer):
        b, t = ids.shape
        pos = torch.arange(t, dtype=torch.float32)
        freqs = torch.exp(-torch.arange(288, dtype=torch.float32) * math.log(1000.0) / 288)
        f = pos[:, None] * freqs[None, :]
        h = torch.cat([torch.sin(f), torch.cos(f)], dim=-1)
        return h[None].expand(b, t, 576).clone()

@dataclass
class Ex: prompt_ids: tuple

g = core.seeded_generator(229801, "auditor C task prompt lengths", "test")
lengths = torch.randint(9, 26, (8000,), generator=g).tolist()   # task prompts of 9..25 tokens (short sentences)
prompts = {"A": [Ex(tuple([1] * L)) for L in lengths]}
wiki = [2] * (8000 * 64 + 100)
spec = RouterSpec.registered()
print("spec", spec, "class counts ST1 / AB:", class_counts(64, 2), class_counts(64, 3))
stu = PositionOnlyStudent()
plan = core.SeedPlan("test", 0)
router, rec = train_router(stu, 4, ("A",), prompts, wiki, plan, spec)
print("final loss", rec["final_loss"], "cut_length_min", rec["cut_length_min"])
windows = [[3] * 256 for _ in range(200)]
gen_dec = false_triggers(router, stu, 4, windows, [63] * 200)
print("GEN decision at token 64 (index 63): triggers", gen_dec["count"], "of", gen_dec["n"], "-> loss increase would be exactly 0 and GEN passes" if gen_dec["count"] == 0 else "")
g2 = core.seeded_generator(229802, "auditor C marker positions", "test")
mpos = torch.randint(5, 63, (100,), generator=g2).tolist()
diag = false_triggers(router, stu, 4, windows[:100], mpos)
print("diagnostic at first marker-like string (positions 5..62): rate", diag["rate"])
acc_task = sum(p == "A" for p in router.predict(hidden_at_ends(stu, 4, [e.prompt_ids for e in prompts["A"][:500]]))) / 500
print("position-only router: task-prompt accuracy", acc_task)
