"""Auditor synthetic checks for P6-E variants (no real checkpoint, no real data).

Run from the repository root:
    uv run --locked python docs/reviews/p6-preflight-2026-11-13/checks/check_p6e_variants.py

Independent of the implementer's analysis modules; imports only the code under audit
(p6_retrieval, p6_equivalence.build_fixtures) and the frozen reference (pilot_model).
"""

import time

import torch
from torch.nn import functional as F

from arborlm import p6_retrieval as rv
from arborlm.engine import configure_cpu
from arborlm.p6_equivalence import build_fixtures
from arborlm.pilot_model import EPS, TEMP, Memory


def my_registered_rule(memory: Memory, q: torch.Tensor) -> torch.Tensor:
    """Auditor's own statement of the tree rule: full float32 recomputation with the reference
    arithmetic, then a full stable sort over ascending-ID candidates (no topk)."""
    routes = (q @ F.normalize(memory.router, dim=-1, eps=EPS).T) / TEMP
    order = routes.argsort(dim=-1, descending=True, stable=True)[:, :2]  # ties -> lower branch ID
    ids = (order[..., None] * 256 + torch.arange(256)).flatten(1)
    local = F.normalize(memory.keys[ids], dim=-1, eps=EPS)
    scores = torch.bmm(local, q.unsqueeze(-1)).squeeze(-1) / TEMP
    scores = scores + routes.log_softmax(-1).gather(-1, order).repeat_interleave(256, dim=-1)
    by_id = ids.argsort(dim=-1)
    s, i = scores.gather(-1, by_id), ids.gather(-1, by_id)
    pick = s.argsort(dim=-1, descending=True, stable=True)[:, :8]
    return i.gather(-1, pick)


def memory_like(kind: str, seed: int, scale: float) -> Memory:
    g = torch.Generator().manual_seed(seed)
    m = Memory(kind, 501).eval()
    with torch.no_grad():
        m.keys.add_(torch.randn(4096, 16, generator=g) * scale)
        if kind != "flat":
            m.router.add_(torch.randn(16, 16, generator=g) * scale)
    return m


def main() -> None:
    configure_cpu()
    out: list[str] = []
    print_ = out.append
    q = F.normalize(torch.randn(4096, 16, generator=torch.Generator().manual_seed(1)), dim=-1)

    # 1. Bitwise identity of each tree variant with the frozen reference, and T3 versus T2.
    for kind in ("fixed_tree", "learned_tree"):
        for scale in (0.0, 0.06, 1.0):
            m = memory_like(kind, 3, scale)
            with torch.no_grad():
                ref_v, ref = m.lookup(q)
                mine = my_registered_rule(m, q)
                print_(f"{kind} scale={scale}: my_rule==reference selected: "
                       f"{torch.equal(mine, ref.selected)}")
                for v in rv.TREE_VARIANTS:
                    w = rv.build_memory_variant(m, v)
                    vv, look = w.lookup(q)
                    print_(
                        f"  {v}: selected_equal={torch.equal(look.selected, ref.selected)} "
                        f"scores_bitwise={rv.bit_equal(vv, ref_v)} "
                        f"maxabs={float((vv.double()-ref_v.double()).abs().max()):.3e} "
                        f"branch_ids_bitwise={rv.bit_equal(look.branch_ids, ref.branch_ids)} "
                        f"cand_bitwise={rv.bit_equal(look.candidate_ids, ref.candidate_ids)} "
                        f"routes_bitwise={rv.bit_equal(look.route_scores, ref.route_scores)} "
                        f"fallback={w.fallback_fraction()}"
                    )
                # contraction error of T3/T4 versus T2 arithmetic over all 512 candidates
                t2 = rv.build_memory_variant(m, "T2")
                routes, branch = t2._route(q)
                ordered, ids = t2._id_order(branch)
                base = torch.bmm(t2._nk[ids], q.unsqueeze(-1)).squeeze(-1) / TEMP
                for v in ("T3", "T4"):
                    w = rv.build_memory_variant(m, v)
                    c = w._contract(q, ordered)
                    diff = (c.double() - base.double()).abs()
                    print_(
                        f"  {v} contraction vs T2 bmm: bitwise={rv.bit_equal(c, base)} "
                        f"frac_differ={float((c != base).double().mean()):.4f} "
                        f"max_abs={float(diff.max()):.3e} (guard needs < {rv.GUARD_DELTA/2:.1e})"
                    )
    # 2. Flat variants.
    for scale in (0.0, 1.0):
        m = memory_like("flat", 4, scale)
        with torch.no_grad():
            ref_v, ref = m.lookup(q)
            for v in rv.FLAT_VARIANTS:
                vv, look = rv.build_memory_variant(m, v).lookup(q)
                print_(f"flat scale={scale} {v}: selected_equal="
                       f"{torch.equal(look.selected, ref.selected)} "
                       f"scores_bitwise={rv.bit_equal(vv, ref_v)}")

    # 3. Constructed-tie fixtures: exact ties actually present in the reference top 9?
    for kind in ("flat", "fixed_tree", "learned_tree"):
        m = memory_like(kind, 5, 0.06)
        for case in build_fixtures(m):
            with torch.no_grad():
                vals, look = case.memory.lookup(case.q)
            # tie inside the selected 8 or across the 8/9 boundary, from the reference itself
            from arborlm.p6_equivalence import reference_scores
            sc, _ = reference_scores(case.memory, case.q)
            top = sc.topk(9).values
            ties = int(((top[:, :-1] == top[:, 1:]).any(-1)).sum())
            boundary = int((top[:, 7] == top[:, 8]).sum())
            route_ties = None
            if look.route_scores is not None:
                r = look.route_scores.topk(3).values
                route_ties = (int((r[:, 0] == r[:, 1]).sum()), int((r[:, 1] == r[:, 2]).sum()))
            print_(f"fixture {kind}/{case.name}: queries={case.q.shape[0]} "
                   f"queries_with_exact_top9_tie={ties} boundary_8_9_ties={boundary} "
                   f"route_ties(top1=top2, top2=top3)={route_ties}")

    # 4. Fingerprint binding: which source mutations does it detect?
    for label, mutate in (
        ("no_grad in-place", lambda p: p.__setitem__((0, 0), p[0, 0] + 1)),
        (".data in-place", lambda p: p.data.__setitem__((0, 0), p.data[0, 0] + 1)),
        ("detach() in-place", lambda p: p.detach().__setitem__((0, 0), p[0, 0] + 1)),
        ("load_state_dict", None),
    ):
        m = memory_like("fixed_tree", 6, 0.06)
        w = rv.build_memory_variant(m, "T2", binding="fingerprint")
        with torch.no_grad():
            if mutate is None:
                sd = {k: v.clone() for k, v in m.state_dict().items()}
                sd["keys"][0, 0] += 1
                m.load_state_dict(sd)
            else:
                mutate(m.keys)
        try:
            with torch.no_grad():
                w.lookup(q[:4])
            detected = False
        except RuntimeError:
            detected = True
        try:
            w.verify_source()
            hashed = False
        except RuntimeError:
            hashed = True
        print_(f"fingerprint detects {label}: {detected}; full hash detects: {hashed}")
    # inside inference_mode
    m = memory_like("fixed_tree", 6, 0.06)
    w = rv.build_memory_variant(m, "T2", binding="fingerprint")
    with torch.inference_mode():
        m.keys.data[0, 0] += 1
        try:
            w.lookup(q[:4])
            print_("fingerprint detects .data write inside inference_mode: False")
        except RuntimeError:
            print_("fingerprint detects .data write inside inference_mode: True")

    # 5. Per-call cost of the guard (hash vs fingerprint) relative to one W8 lookup.
    m = memory_like("fixed_tree", 7, 0.06)
    q512 = q[:512]
    with torch.inference_mode():
        for binding in ("fingerprint", "hash"):
            w = rv.build_memory_variant(m, "T2", binding=binding)
            for _ in range(5):
                w._guard()
            t = time.perf_counter_ns()
            for _ in range(200):
                w._guard()
            g = (time.perf_counter_ns() - t) / 200
            for _ in range(3):
                w.lookup(q512)
            t = time.perf_counter_ns()
            for _ in range(20):
                w.lookup(q512)
            lk = (time.perf_counter_ns() - t) / 20
            print_(f"guard cost binding={binding}: {g/1000:.1f} us per call; "
                   f"T2 W8 lookup {lk/1000:.0f} us (exploratory, one run, not registered)")
    print("\n".join(out))


if __name__ == "__main__":
    main()
