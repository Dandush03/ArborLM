"""Re-audit checks on SYNTHETIC tensors only (no real checkpoint, panel or training row).

1. bmm row invariance: is each candidate's score bitwise the same when the batched product has
   256*k rows (tree_candidates(visit=k)) as when it has 4,096 rows (X16P)? The width curve from
   captured X16P scores is exactly the frozen selection for every k iff this holds (the routes,
   prior and stable_top are otherwise identical).
2. Width curve over EVERY batch (not only the first): selections derived the way p6_fidelity now
   derives them (first 256*k captured columns + frozen stable_top) versus a direct
   tree_candidates(visit=k) call, on tensors with constructed route ties at rank k/k+1 and exact
   score ties straddling the 256*k column boundary. Also an independent selection by my own
   full sort (descending score, then ascending slot ID) on the direct scores.
3. Equivalence fixture integrity robustness (spurious-stop risk). The router case overwrites
   router rows 0-3 and 8-15 only; rows 4-7 keep the checkpoint's own values. For the FIXED tree
   those rows are the registered init (a buffer, never trained), so the facts are computed
   exactly per seed. For the LEARNED tree they are trained and unknown; I report, per seed, the
   per-query route score that a row 4-7 must exceed to destroy each rank-2/3 tie, and simulate
   perturbed rows.

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_reaudit_width_and_fixtures.py [threads]
"""

import sys

import torch
from torch.nn import functional as F

from arborlm import p6_equivalence as eq
from arborlm import p6_fidelity as fid
from arborlm import pilot_model
from arborlm.p2_config import BACKBONES, CONTROL, ORDERS
from arborlm.p2_config import Cell as ParentCell
from arborlm.p2_model import FollowupModel
from arborlm.p4_model import extract
from arborlm.p5_config import FIXED, LEARNED, SEEDS, Cell
from arborlm.p5_model import Model
from arborlm.pilot_model import EPS, TEMP, TOP, tree_candidates

WIDTHS = (2, 3, 4, 6, 8, 12, 16)


def my_rule(scores: torch.Tensor, ids: torch.Tensor) -> torch.Tensor:
    """Descending score, ties by ascending slot ID, by a full lexicographic sort (my own)."""
    out = []
    for s, i in zip(scores.tolist(), ids.tolist(), strict=True):
        out.append([x for _, x in sorted(zip(s, i, strict=True), key=lambda t: (-t[0], t[1]))[:TOP]])
    return torch.tensor(out)


def bmm_invariance(n: int, seed: int) -> dict[int, int]:
    g = torch.Generator().manual_seed(seed)
    keys = torch.randn(4096, 16, generator=g) * 0.02 + torch.randn(4096, 16, generator=g) * 0.05
    q = F.normalize(torch.randn(n, 16, generator=g), dim=-1)
    order = torch.stack([torch.randperm(16, generator=g) for _ in range(n)])
    idx = (order[..., None] * 256 + torch.arange(256)).flatten(1)
    full = torch.bmm(F.normalize(keys[idx], dim=-1, eps=EPS), q.unsqueeze(-1)).squeeze(-1)
    out = {}
    for k in WIDTHS:
        part = torch.bmm(
            F.normalize(keys[idx[:, : 256 * k]], dim=-1, eps=EPS), q.unsqueeze(-1)
        ).squeeze(-1)
        out[k] = int((part.view(torch.int32) != full[:, : 256 * k].view(torch.int32)).sum())
    return out


def tie_tensors(seed: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    g = torch.Generator().manual_seed(seed)
    keys = torch.randn(4096, 16, generator=g) * 0.05
    router = torch.randn(16, 16, generator=g) * 0.05
    q = F.normalize(torch.randn(512, 16, generator=g), dim=-1)
    # Route ties: duplicate router rows (every pair), and queries equal to a router row.
    router[3] = router[2]
    router[7] = router[6]
    router[11] = router[10]
    q[:64] = F.normalize(router[[2, 6, 10, 0] * 16], dim=-1)
    # Exact score ties straddling branch boundaries: duplicate keys across branches 2/3, 6/7, ...
    for b in (2, 6, 10):
        for j in range(0, 256, 3):
            keys[(b + 1) * 256 + j] = keys[b * 256 + j]
    # Queries aligned with a duplicated key give an exact tie at the top.
    q[64:128] = F.normalize(keys[[2 * 256 + 3 * j for j in range(64)]], dim=-1)
    routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
    return q, keys, routes


def width_every_batch(seed: int) -> dict[str, int]:
    q, keys, routes = tie_tensors(seed)
    mismatch = {f"k{k}": 0 for k in WIDTHS}
    mine = {f"k{k}": 0 for k in WIDTHS}
    route_tie_at_boundary = {f"k{k}": 0 for k in WIDTHS if k < 16}
    ordered = routes.sort(dim=-1, descending=True, stable=True).values
    for k in WIDTHS:
        if k < 16:
            route_tie_at_boundary[f"k{k}"] = int((ordered[:, k - 1] == ordered[:, k]).sum())
    for start in range(0, 512, 64):  # eight batches of 64
        qb, rb = q[start : start + 64], routes[start : start + 64]
        sink: list[tuple[torch.Tensor, torch.Tensor]] = []
        with fid._spy_candidate_scores(sink):
            tree_candidates(qb, keys, rb, visit=16, use_prior=True)
        scores, ids = sink[0]
        for k in WIDTHS:
            cols = 256 * k
            _, derived = pilot_model.stable_top(scores[:, :cols], TOP, ids[:, :cols])
            sink2: list[tuple[torch.Tensor, torch.Tensor]] = []
            with fid._spy_candidate_scores(sink2):
                _, direct, _, _ = tree_candidates(qb, keys, rb, visit=k, use_prior=True)
            mismatch[f"k{k}"] += int((derived != direct).any(-1).sum())
            dscores, dids = sink2[0]
            mine[f"k{k}"] += int((my_rule(dscores, dids) != direct).any(-1).sum())
    return {"derived_vs_direct_mismatch_queries": mismatch, "my_rule_vs_direct": mine,
            "route_ties_at_rank_k_k+1_queries": route_tie_at_boundary}


def router_case_facts(router: torch.Tensor) -> tuple[int, list[float]]:
    """Run build_fixtures on a memory with this router; count rank-2/3 route ties."""
    backbone = extract(FollowupModel(ParentCell(BACKBONES[0], 201, ORDERS[0], CONTROL)))
    memory = Model(Cell(BACKBONES[0], ORDERS[0], SEEDS[0], LEARNED), backbone).addition
    with torch.no_grad():
        memory.router.copy_(router)
    case = [c for c in eq.build_fixtures(memory) if c.name == eq.ROUTER_CASE][0]
    routes = (case.q @ F.normalize(case.memory.router, dim=-1, eps=EPS).T) / TEMP
    ordered = routes.sort(dim=-1, descending=True, stable=True).values
    tied = ordered[:, 1] == ordered[:, 2]
    # For tied queries: the route score (cosine) a row 4-7 must exceed to push the tie to 3/4.
    thresholds = (ordered[tied, 1] * TEMP).tolist()
    return int(tied.sum()), thresholds


def main() -> None:
    threads = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if threads:
        torch.set_num_threads(threads)
    print(f"torch {torch.__version__}, intra-op threads {torch.get_num_threads()}")
    print("1. bmm bitwise mismatches, M=256k rows vs M=4096 rows (per k):")
    for n, seed in ((512, 1), (512, 2), (64, 3), (1, 4)):
        print(f"   N={n} seed={seed}: {bmm_invariance(n, seed)}")
    print("2. width curve over every batch with constructed ties:")
    for seed in (5, 6):
        print(f"   seed={seed}: {width_every_batch(seed)}")
    print("3. equivalence router fixture: rank-2/3 route ties (spurious-stop risk)")
    backbone = extract(FollowupModel(ParentCell(BACKBONES[0], 201, ORDERS[0], CONTROL)))
    for seed in SEEDS:
        init = Model(Cell(BACKBONES[0], ORDERS[0], seed, FIXED), backbone).addition.router.detach()
        count, thresholds = router_case_facts(init.clone())
        print(f"   seed {seed}: fixed-tree (exact registered init) ties={count};"
              f" cos a row 4-7 must exceed to break each: {[round(t, 3) for t in thresholds]}")
        g = torch.Generator().manual_seed(seed)
        broken = {}
        for scale in (0.5, 1.0, 2.0, 5.0):
            fails = 0
            for _ in range(200):
                r = init.clone()
                r[4:8] = r[4:8] + scale * r[4:8].norm(dim=-1, keepdim=True) * torch.randn(
                    4, 16, generator=g
                ) / 4.0
                fails += router_case_facts(r)[0] == 0
            broken[scale] = fails
        rand_fail = sum(
            router_case_facts(torch.cat([init[:4], torch.randn(4, 16, generator=g), init[8:]]))[0]
            == 0
            for _ in range(200)
        )
        print(f"   seed {seed}: learned-tree simulation, rows 4-7 perturbed (relative scale ->"
              f" runs with zero ties out of 200): {broken}; rows 4-7 fully random: {rand_fail}/200")


if __name__ == "__main__":
    main()
