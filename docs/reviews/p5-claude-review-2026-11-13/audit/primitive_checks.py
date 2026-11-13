"""SYNTHETIC primitive checks for the P5 retrieval mathematics (Part B).

Everything here uses random synthetic tensors only. No checkpoint, no experiment data, no
training. `arborlm.pilot_model` is imported solely to exercise the existing functions on
synthetic tensors. Results are machine/build specific (CPU float32, 1 thread, this torch
build) and are NOT evidence about the P5 checkpoints themselves.
"""

import json
import sys
from pathlib import Path

import torch
from torch.nn import functional as F

from arborlm.pilot_model import EPS, TEMP, TOP, Memory, stable_top, tree_candidates

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
OUT = Path(__file__).resolve().parent / "primitive_checks.json"
res: dict = {"label": "SYNTHETIC tensors only; not P5 data", "torch": torch.__version__,
             "python": sys.version, "cpu_capability": torch.backends.cpu.get_cpu_capability()}


def bit_equal(a, b):
    return bool(torch.equal(a.view(torch.int32), b.view(torch.int32))) if a.dtype == torch.float32 \
        else bool(torch.equal(a, b))


def mism(a, b):
    return int((a.view(torch.int32) != b.view(torch.int32)).sum())


g = torch.Generator().manual_seed(12345)
N = 512
keys = torch.randn(4096, 16, generator=g) * 0.02
router = torch.randn(16, 16, generator=g) * 0.02
q = F.normalize(torch.randn(N, 16, generator=g), dim=-1, eps=EPS)
routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
_, br = stable_top(routes, 2)
idx = (br[..., None] * 256 + torch.arange(256)).flatten(1)  # [N,512], top-1 branch first

# ---- (a) normalize-then-gather vs gather-then-normalize
gathered_then_norm = F.normalize(keys[idx], dim=-1, eps=EPS)
norm_then_gathered = F.normalize(keys, dim=-1, eps=EPS)[idx]
res["a_normalize_gather_bitwise_equal"] = bit_equal(gathered_then_norm, norm_then_gathered)
res["a_normalize_gather_mismatching_elements"] = mism(gathered_then_norm, norm_then_gathered)
# also with a non-contiguous / different leading shape
alt = F.normalize(keys.reshape(16, 256, 16), dim=-1, eps=EPS).reshape(4096, 16)
res["a_normalize_reshaped_table_bitwise_equal"] = bit_equal(alt, F.normalize(keys, dim=-1, eps=EPS))

# ---- scores with the existing contraction (bmm)
s_bmm = torch.bmm(gathered_then_norm, q.unsqueeze(-1)).squeeze(-1) / TEMP

# ---- (b) row position invariance of bmm: candidate rows ordered by branch id
order = idx.argsort(dim=-1)
idx_sorted = idx.gather(-1, order)
s_sorted = torch.bmm(F.normalize(keys[idx_sorted], dim=-1, eps=EPS), q.unsqueeze(-1)).squeeze(-1) / TEMP
res["b_bmm_scores_bitwise_equal_after_reordering_rows"] = bit_equal(s_bmm.gather(-1, order), s_sorted)
res["b_bmm_reorder_mismatching_elements"] = mism(s_bmm.gather(-1, order), s_sorted)
# random row permutation (stronger)
perm = torch.randperm(512, generator=g)
s_perm = torch.bmm(gathered_then_norm[:, perm], q.unsqueeze(-1)).squeeze(-1) / TEMP
res["b_bmm_scores_bitwise_equal_random_row_perm"] = bit_equal(s_bmm[:, perm], s_perm)

# ---- (c) alternative contractions
alts = {
    "einsum_bkd_bd": torch.einsum("bkd,bd->bk", gathered_then_norm, q) / TEMP,
    "matmul_3d": torch.matmul(gathered_then_norm, q.unsqueeze(-1)).squeeze(-1) / TEMP,
    "mul_sum": (gathered_then_norm * q[:, None, :]).sum(-1) / TEMP,
    "flat_mm_then_gather": ((q @ F.normalize(keys, dim=-1, eps=EPS).T) / TEMP).gather(-1, idx),
    "mul_scalar_instead_of_div": torch.bmm(gathered_then_norm, q.unsqueeze(-1)).squeeze(-1) * (1 / TEMP),
}
res["c_contractions"] = {}
for name, s in alts.items():
    res["c_contractions"][name] = {
        "bitwise_equal_to_bmm": bit_equal(s, s_bmm),
        "mismatching_elements": mism(s, s_bmm),
        "max_abs_diff": float((s - s_bmm).abs().max()),
    }
# does selection change for any of them (full tree score incl. prior)?
prior = routes.log_softmax(-1).gather(-1, br).repeat_interleave(256, dim=-1)
ref_v, ref_sel = stable_top(s_bmm + prior, TOP, idx)
sel_changes = {}
for name, s in alts.items():
    v, sel = stable_top(s + prior, TOP, idx)
    sel_changes[name] = {"queries_with_different_selected_ids": int((sel != ref_sel).any(-1).sum()),
                         "selected_score_bitwise_equal": bit_equal(v, ref_v)}
res["c_selection_changes_random_data"] = sel_changes
# smallest gap between 8th and 9th tree score in this synthetic batch (near-tie scale)
full = (s_bmm + prior)
top9 = full.topk(9).values
res["min_gap_8th_9th_synthetic"] = float((top9[:, 7] - top9[:, 8]).min())
res["float32_ulp_at_5"] = float(torch.finfo(torch.float32).eps * 4)

# ---- constructed near-tie: two candidates whose scores differ by 1 ulp under bmm
# Show that a 1-ulp reordering at the 8/9 boundary changes the selected ID set.
s_tie = torch.zeros(1, 512)
s_tie[0, :7] = torch.tensor([9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0])
s_tie[0, 300] = 1.0
s_tie[0, 10] = torch.nextafter(torch.tensor(1.0), torch.tensor(0.0))
ids_tie = idx[:1]
_, sel_a = stable_top(s_tie, TOP, ids_tie)
s_tie2 = s_tie.clone()
s_tie2[0, 10] = 1.0  # now exact tie; tie rule = lower slot id wins
_, sel_b = stable_top(s_tie2, TOP, ids_tie)
res["near_tie_demo"] = {"slot_at_pos10": int(ids_tie[0, 10]), "slot_at_pos300": int(ids_tie[0, 300]),
                        "selected_last_when_1ulp_apart": int(sel_a[0, -1]),
                        "selected_last_when_exact_tie": int(sel_b[0, -1])}

# ---- candidate_ids / branch_ids order dependence and tie invariance to candidate order
v1, s1, c1, b1 = tree_candidates(q, keys, routes)
# exact ties: duplicate a key row inside both visited branches of query 0 -> equal scores
k2 = keys.clone()
b0, b1_ = int(br[0, 0]), int(br[0, 1])
k2[b1_ * 256 + 3] = k2[b0 * 256 + 5]
k2[b0 * 256 + 7] = k2[b0 * 256 + 5]
vt, st_, ct, bt = tree_candidates(q, k2, routes)
res["tie_rule"] = {
    "branch_ids_query0_rank_order": br[0].tolist(),
    "candidate_ids_first_entry_is_top1_branch_start": int(c1[0, 0]) == b0 * 256,
    "selected_ids_sorted_desc_score_then_asc_id_check": True,
}
# verify order: descending score then ascending id for every query
ok = True
for i in range(N):
    sc, ids = v1[i].tolist(), s1[i].tolist()
    for j in range(TOP - 1):
        if sc[j] < sc[j + 1] or (sc[j] == sc[j + 1] and ids[j] > ids[j + 1]):
            ok = False
res["tie_rule"]["selected_ids_sorted_desc_score_then_asc_id_check"] = ok

# ---- gradient paths (learned tree), per query
torch.manual_seed(0)
mem = Memory("learned_tree", 501)
with torch.no_grad():
    mem.keys.mul_(25.0)  # spread scores a little; synthetic only
h = torch.randn(1, 64, 32, generator=g)
q_all = F.normalize(F.linear(h, mem.wq), dim=-1, eps=EPS).reshape(-1, 16)
direction = torch.randn(1, 64, 32, generator=g)
stats = {"single_branch_queries": 0, "two_branch_queries": 0,
         "max_router_grad_norm_single_branch": 0.0, "min_router_grad_norm_two_branch": float("inf"),
         "max_unvisited_row_grad_abs": 0.0, "max_visited_row_grad_abs": 0.0,
         "max_route_grad_sum_abs": 0.0,
         "max_prior_grad_g1_plus_g2_abs": 0.0}
for t in range(64):
    mem.zero_grad(set_to_none=True)
    hq = h[:, t:t + 1]
    qq = F.normalize(F.linear(hq, mem.wq), dim=-1, eps=EPS).reshape(-1, 16)
    routes_t = (qq @ F.normalize(mem.router, dim=-1, eps=EPS).T) / TEMP
    routes_t.retain_grad()
    scores, sel, cand, bids = tree_candidates(qq, mem.keys, routes_t)
    combined = (scores.softmax(-1)[..., None] * mem.values[sel]).sum(-2)
    out = hq + mem.gate.sigmoid() * F.linear(combined.reshape(hq.shape), mem.wo)
    (out * direction[:, t:t + 1]).sum().backward()
    rg = mem.router.grad
    branches_of_sel = set((sel[0] // 256).tolist())
    visited = set(bids[0].tolist())
    unvisited = [b for b in range(16) if b not in visited]
    gnorm = float(rg.norm())
    if len(branches_of_sel) == 1:
        stats["single_branch_queries"] += 1
        stats["max_router_grad_norm_single_branch"] = max(stats["max_router_grad_norm_single_branch"], gnorm)
    else:
        stats["two_branch_queries"] += 1
        stats["min_router_grad_norm_two_branch"] = min(stats["min_router_grad_norm_two_branch"], gnorm)
    stats["max_unvisited_row_grad_abs"] = max(stats["max_unvisited_row_grad_abs"],
                                              float(rg[unvisited].abs().max()))
    stats["max_visited_row_grad_abs"] = max(stats["max_visited_row_grad_abs"],
                                            float(rg[list(visited)].abs().max()))
    stats["max_route_grad_sum_abs"] = max(stats["max_route_grad_sum_abs"], float(routes_t.grad.sum().abs()))
    # gradient on routes at visited branches should be +g / -g
    gv = routes_t.grad[0, bids[0]]
    stats["max_prior_grad_g1_plus_g2_abs"] = max(stats["max_prior_grad_g1_plus_g2_abs"], float(gv.sum().abs()))
    # keys: only selected rows get gradient
    kg = mem.keys.grad
    nz_rows = set(torch.nonzero(kg.abs().sum(-1) > 0).flatten().tolist())
    if not nz_rows <= set(sel[0].tolist()):
        stats.setdefault("key_grad_outside_selected", 0)
        stats["key_grad_outside_selected"] = stats.get("key_grad_outside_selected", 0) + 1
res["gradient_paths_learned_tree_synthetic"] = stats

# ---- references: lemma S_R1 ∩ V ⊆ S_tree, and reference helpers
with torch.no_grad():
    _, sel_tree, cand_tree, bids_tree = tree_candidates(q, keys * 25, routes)
    _, sel_r1, _, _ = tree_candidates(q, keys * 25, routes, visit=16, use_prior=True)
    _, sel_r2, _, _ = tree_candidates(q, keys * 25, routes, visit=16, use_prior=False)
    _, sel_r2v, _, _ = tree_candidates(q, keys * 25, routes, visit=2, use_prior=False)
    flat_scores = (q @ F.normalize(keys * 25, dim=-1, eps=EPS).T) / TEMP
    _, sel_flat = stable_top(flat_scores, TOP)
lemma_ok, recall_r1, recall_r2, r1_eq, r2_eq_flat = True, 0, 0, 0, 0
for i in range(N):
    V = set(bids_tree[i].tolist())
    t = set(sel_tree[i].tolist())
    r1 = set(sel_r1[i].tolist())
    if not {x for x in r1 if x // 256 in V} <= t:
        lemma_ok = False
    recall_r1 += len(t & r1)
    recall_r2 += len(t & set(sel_r2[i].tolist()))
    r1_eq += t == r1
    r2_eq_flat += sel_r2[i].tolist() == sel_flat[i].tolist()
res["references_synthetic"] = {
    "lemma_R1_selected_in_visited_subset_of_tree_selected": lemma_ok,
    "mean_recall_vs_R1_prior_exhaustive": recall_r1 / (8 * N),
    "mean_recall_vs_R2_cosine_exhaustive": recall_r2 / (8 * N),
    "queries_tree_equals_R1": r1_eq,
    "visit16_noprior_selected_equals_flat_lookup_order_and_ids": r2_eq_flat,
    "note": "synthetic random keys; recall values are meaningless for P5 and only exercise the code",
}

# ---- shape/position dependence of the contractions themselves
kn = F.normalize(keys * 25, dim=-1, eps=EPS)
perm4096 = torch.randperm(4096, generator=g)
mm_full = q @ kn.T
mm_perm = q @ kn[perm4096].T
shape_checks = {
    "flat_mm_column_permutation_bitwise": bit_equal(mm_full[:, perm4096], mm_perm),
    "flat_mm_column_permutation_mismatches": mism(mm_full[:, perm4096], mm_perm),
    "flat_mm_row_subset_N64_vs_N512_bitwise": bit_equal((q[:64] @ kn.T), mm_full[:64]),
}
# bmm with 4096 gathered rows (visit=16) vs 512 rows (visit=2): same visited-slot scores?
_, br16 = stable_top(routes, 16)
idx16 = (br16[..., None] * 256 + torch.arange(256)).flatten(1)
s16 = torch.bmm(F.normalize((keys * 25)[idx16], dim=-1, eps=EPS), q.unsqueeze(-1)).squeeze(-1)
s2 = torch.bmm(F.normalize((keys * 25)[idx], dim=-1, eps=EPS), q.unsqueeze(-1)).squeeze(-1)
shape_checks["bmm_visit16_first512_equals_visit2_bitwise"] = bit_equal(s16[:, :512], s2)
shape_checks["bmm_visit16_first512_mismatches"] = mism(s16[:, :512], s2)
res["shape_position_checks"] = shape_checks

OUT.write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
