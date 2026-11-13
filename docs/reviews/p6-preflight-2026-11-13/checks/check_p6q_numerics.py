"""Auditor synthetic checks for P6-Q numerics (no real checkpoint, no real data).

    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6q_numerics.py

1. Size of float32 (frozen tree_candidates) versus float64 score error, compared with the
   registered near-tie threshold 1e-5 of gate (iv).
2. Certificate soundness on synthetic data (certified => recall_P == 1).
3. Spy on stable_top cannot change results (compare with and without the spy).
4. Concentration report of X16 rules carries T2P-specific constants.
"""

import torch
from torch.nn import functional as F

from arborlm import p6_fidelity as fid
from arborlm.engine import configure_cpu
from arborlm.p6_fidelity_reference import exhaustive_reference
from arborlm.pilot_metrics import RetrievalCounts
from arborlm.pilot_model import EPS, TEMP, Lookup, tree_candidates


def main() -> None:
    configure_cpu()
    out = []
    for seed, kscale, rscale in ((0, 0.02, 0.02), (1, 1.0, 1.0), (2, 0.06, 0.5)):
        g = torch.Generator().manual_seed(seed)
        keys = torch.randn(4096, 16, generator=g) * kscale
        router = torch.randn(16, 16, generator=g) * rscale
        q = F.normalize(torch.randn(2048, 16, generator=g), dim=-1, eps=EPS)
        routes = (q @ F.normalize(router, dim=-1, eps=EPS).T) / TEMP
        for prior in (True, False):
            sink: list[tuple[torch.Tensor, torch.Tensor]] = []
            with fid._spy_candidate_scores(sink):
                v_spy, s_spy, _, _ = tree_candidates(q, keys, routes, visit=16, use_prior=prior)
            v, s, _, b = tree_candidates(q, keys, routes, visit=16, use_prior=prior)
            scores32, ids = sink[0]
            ref, ref_ids, gap = exhaustive_reference(q, keys, router, use_prior=prior)
            aligned = ref.gather(-1, ids)
            err = (scores32.double() - aligned).abs()
            sets_differ = sum(
                set(a) != set(c) for a, c in zip(s.tolist(), ref_ids.tolist(), strict=True)
            )
            out.append(
                f"seed={seed} prior={prior}: spy_identical={torch.equal(s_spy, s) and torch.equal(v_spy, v)} "
                f"max|f32-f64| score={float(err.max()):.3e} (NEAR_TIE {fid.NEAR_TIE:.0e}) "
                f"p99.9={float(err.flatten().kthvalue(int(err.numel()*0.999)).values):.3e} "
                f"min_gap={float(gap.min()):.3e} sets_differ={sets_differ}"
            )
            if prior:
                v2, s2, _, b2 = tree_candidates(q, keys, routes, visit=2, use_prior=True)
                counts = fid.overlap_counts(s2, s)
                cert = fid.certificate_mask(v2, routes, b2)
                out.append(
                    f"   certificate: certified={int(cert.sum())}/{q.shape[0]} "
                    f"certified_with_recall<1={int((cert & (counts < 8)).sum())} "
                    f"recall_P={float(counts.double().mean()/8):.4f}"
                )
    # 4. Concentration constants under X16.
    tracker = RetrievalCounts("fixed_tree")
    sel = torch.arange(8).repeat(4, 1)
    tracker.update(Lookup(sel, torch.arange(4096).repeat(4, 1), branch_ids=torch.arange(16).repeat(4, 1),
                          route_scores=torch.zeros(4, 16)))
    report = fid.concentration_report(tracker)
    out.append(
        "X16-style tracker report fields: full_key_dots_per_query="
        f"{report['full_key_dots_per_query']} logical_key_elements_per_query="
        f"{report['logical_key_elements_per_query']} unique_candidate_slots="
        f"{report['unique_candidate_slots']} (constants are T2P's, not X16's)"
    )
    print("\n".join(out))


if __name__ == "__main__":
    main()
