# ruff: noqa
"""Descriptive only (not a registered read): where the tree's exhaustive top-8 (E8) slots sit, at 32K/16K, T-OQ, draws 1-2, U_P and run length.
Own float64 code on the raw model.pt tensors and the facts' oracle codes. Usage: same environment as audit_tensors.py; argument: draw update."""
import json, math, sys
from pathlib import Path
import torch
torch.set_num_threads(1)
from studies.p9 import data as data_mod, core as p9core
from studies.p10s1 import core as s1core
from studies.p10s1.model import OracleCodes
from studies.p9.data import encode_identifiers

S1 = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117")
EXP = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
OUT = Path(__file__).resolve().parent
draw, update = int(sys.argv[1]), int(sys.argv[2])
seeds = s1core.registered_draw_seeds(draw)
data = data_mod.build_study_data(seeds, p9core.load_trained_corpus(EXP), sizes=data_mod.DataSizes(main_trained=32768, unseen=2048, lane_d_per_set=s1core.LANE_D_STUB))
codes = OracleCodes(seeds.r1_codes).of_codes(encode_identifiers(data.facts.ident[:32768])).double()
cell = f"P_T-OQ_f32768_n16384_d{draw}_i{2100 + draw}_u16384"
st = torch.load(S1 / "cells" / cell / "snapshots" / s1core.snapshot_stem(update) / "model.pt", weights_only=True, map_location="cpu")["model"]
keys, router = st["addition.keys"].double(), st["addition.router"].double()
init = torch.load(S1 / "cells" / cell / "snapshots" / sorted((S1 / "cells" / cell / "snapshots").iterdir())[0].name / "model.pt", weights_only=True, map_location="cpu")["model"]["addition.keys"].double()
K = keys / keys.norm(dim=1, keepdim=True).clamp_min(1e-8)
R = router / router.norm(dim=1, keepdim=True).clamp_min(1e-8)
N, B = K.shape[0], R.shape[0]
visits = torch.zeros(B)
sel_count = torch.zeros(N)
e8_count = torch.zeros(N)
e8_cos, sel_cos, e8_in_vis = [], [], 0
maxcos_visited, maxcos_global = [], []
for s in range(0, 32768, 1024):
    q = codes[s:s + 1024]
    cos = q @ K.T / 0.2
    routes = q @ R.T / 0.2
    prior = routes.log_softmax(-1)
    order = (-routes).argsort(dim=1, stable=True)[:, :2]
    visits += torch.bincount(order.reshape(-1), minlength=B).double()
    inb = torch.zeros(q.shape[0], B, dtype=torch.bool).scatter_(1, order, True)[:, torch.arange(N) // 256]
    sc = (cos + prior[:, torch.arange(N) // 256]).masked_fill(~inb, -math.inf)
    sel = (-sc).argsort(dim=1, stable=True)[:, :8]
    e8 = (-cos).argsort(dim=1, stable=True)[:, :8]
    sel_count += torch.bincount(sel.reshape(-1), minlength=N).double()
    e8_count += torch.bincount(e8.reshape(-1), minlength=N).double()
    e8_cos.append(cos.gather(1, e8).mean(1) * 0.2)
    sel_cos.append(cos.gather(1, sel).mean(1) * 0.2)
    maxcos_visited.append(cos.masked_fill(~inb, -math.inf).max(1).values * 0.2)
    maxcos_global.append(cos.max(1).values * 0.2)
used = sel_count > 0
e8_slots = e8_count > 0
moved = (keys - init).norm(dim=1)
branch_vis = visits[torch.arange(N) // 256]
out = {
    "cell": cell, "update": update,
    "share_of_slots_selected_by_T0_for_some_fact": float(used.double().mean()),
    "share_of_E8_occurrences_on_slots_T0_never_selects": float(e8_count[~used].sum() / e8_count.sum()),
    "share_of_T0_selections_on_slots_that_are_in_some_E8": float(sel_count[e8_slots].sum() / sel_count.sum()),
    "mean_key_displacement_since_first_snapshot_E8_slots_weighted": float((moved * e8_count).sum() / e8_count.sum()),
    "mean_key_displacement_since_first_snapshot_selected_slots_weighted": float((moved * sel_count).sum() / sel_count.sum()),
    "mean_key_displacement_since_first_snapshot_all": float(moved.mean()),
    "mean_branch_visits_E8_weighted": float((branch_vis * e8_count).sum() / e8_count.sum()),
    "mean_branch_visits_all_slots": float(branch_vis.mean()),
    "branches_never_visited": int((visits == 0).sum()), "branches": B,
    "mean_cos_E8": float(torch.cat(e8_cos).mean()), "mean_cos_T0_selected": float(torch.cat(sel_cos).mean()),
    "mean_max_cos_in_visited_branches": float(torch.cat(maxcos_visited).mean()), "mean_max_cos_global": float(torch.cat(maxcos_global).mean()),
    "chance_CR8_if_E8_uniform_over_branches_v2": 2 / B,
}
print(json.dumps(out, indent=1))
(OUT / f"e8_where_d{draw}_u{update}.json").write_text(json.dumps(out, indent=1))
