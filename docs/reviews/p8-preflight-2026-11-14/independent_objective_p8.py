"""Independent auditor reference for ADR-0015 sections 3-4 (P8 locality proxy and training step).

Written by the auditor (Claude Opus 5.5) from the ADR text only. The REFERENCE functions below
(ref_*) import nothing from arborlm.p8_*; they use plain torch. The HARNESS at the bottom imports the
implementation (p8_objective, p8_core) solely to compare against it.

Run:
  uv run --locked --extra pilot python docs/reviews/p8-preflight-2026-11-14/independent_objective_p8.py
"""

import copy
import json
import math
import sys

import torch
from torch.nn import functional as F

SLOTS, PER_BRANCH, TEMP, EPS = 4096, 256, 0.2, 1e-8
BETA, ALPHA, GROUP, WINDOW, SOFT_TOP, TOP = 0.25, 0.5, 8, 8, 64, 8
LR, B1, B2, ADAM_EPS, CLIP = 0.003, 0.9, 0.999, 1e-8, 1.0


# ============================== REFERENCE (no arborlm.p8_* imports) ==============================
def ref_unit(x):
    return x / x.norm(dim=-1, keepdim=True).clamp_min(EPS)


def ref_scores(variant, keys, wq, router, h):
    """h: [B, T, 32]. Returns q-ordered (r*T+t) scores [Q, C] and slot ids [Q, C]."""
    b, t, _ = h.shape
    q3 = ref_unit(torch.einsum("btd,kd->btk", h, wq))
    q = torch.stack([q3[r, s] for r in range(b) for s in range(t)])  # explicit context-major
    kn = ref_unit(keys)
    if variant == "flat":
        return (q @ kn.T) / TEMP, torch.arange(SLOTS).expand(q.shape[0], -1)
    routes = (q @ ref_unit(router).T) / TEMP
    # top-2 branches: highest route, ties to the lower branch id
    order = torch.sort(-routes.detach(), dim=-1, stable=True).indices[:, :2]
    ids = torch.cat([order[:, :1] * PER_BRANCH + torch.arange(PER_BRANCH),
                     order[:, 1:2] * PER_BRANCH + torch.arange(PER_BRANCH)], dim=1)
    logprior = routes - torch.logsumexp(routes, dim=-1, keepdim=True)
    prior = torch.cat([logprior.gather(1, order[:, :1]).expand(-1, PER_BRANCH),
                       logprior.gather(1, order[:, 1:2]).expand(-1, PER_BRANCH)], dim=1)
    s = (kn[ids] * q[:, None, :]).sum(-1) / TEMP + prior
    return s, ids


def ref_dense(s, ids):
    """Dense pi and (1 - pi) over all 4096 slots; pi = 0 outside each query's top 64."""
    order = torch.sort(-s.detach(), dim=-1, stable=True).indices[:, :SOFT_TOP]
    st = s.gather(1, order)
    tau = 0.5 * (st[:, TOP - 1] + st[:, TOP])  # not detached
    z = (st - tau[:, None]) / BETA
    slot = ids.gather(1, order)
    rows = torch.arange(s.shape[0])[:, None].expand_as(slot)
    pi = torch.zeros(s.shape[0], SLOTS, dtype=s.dtype).index_put((rows, slot), torch.sigmoid(z))
    one_minus = torch.ones(s.shape[0], SLOTS, dtype=s.dtype).index_put(
        (rows, slot), torch.sigmoid(-z)
    )
    gap = st[:, TOP - 1] - st[:, TOP]
    return pi, one_minus, gap


def ref_conc(pi):
    usage = pi.sum(0)
    u = usage / usage.sum()
    m = u > 0
    return -(u[m] * torch.log(u[m])).sum() / math.log(SLOTS)


def ref_co(pi, one_minus):
    touched = (1 - one_minus.reshape(-1, SLOTS // GROUP, GROUP).prod(-1)).sum(-1)
    return (touched / pi.sum(-1)).mean()


def ref_temp(pi, one_minus, rows):
    t_len = pi.shape[0] // rows
    p3, m3 = pi.reshape(rows, t_len, SLOTS), one_minus.reshape(rows, t_len, SLOTS)
    terms = []
    for r in range(rows):
        for t in range(1, t_len):
            keep = m3[r, max(0, t - WINDOW) : t].prod(0)  # prob. not selected in window, same row
            terms.append((p3[r, t] * keep).sum() / p3[r, t].sum())
    return torch.stack(terms).mean()


def ref_regs(variant, keys, wq, router, h, names):
    s, ids = ref_scores(variant, keys, wq, router, h)
    pi, om, _ = ref_dense(s, ids)
    out = {}
    for n in names:
        out[n] = {"conc": lambda: ref_conc(pi), "co": lambda: ref_co(pi, om),
                  "temp": lambda: ref_temp(pi, om, h.shape[0])}[n]()
    return out


def ref_combined_grad(model, batch, names):
    """ADR section 4 rules 1-4 up to (and including) clipping. Returns (grads, lambdas, extra)."""
    params = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    logits, _ = model(batch[:, :-1])
    loss = F.cross_entropy(logits.reshape(-1, 256), batch[:, 1:].reshape(-1))
    g_l = dict(zip([n for n, _ in params], torch.autograd.grad(loss, [p for _, p in params])))
    mem = model.addition
    theta = [n for n in ("addition.keys", "addition.wq", "addition.router") if n in g_l]
    g = {n: v.clone() for n, v in g_l.items()}
    lams = {}
    if names:
        with torch.no_grad():
            x = model.token(batch[:, :-1]) + model.position(torch.arange(batch.shape[1] - 1))
            h = model.blocks[0](x, model.mask[: x.shape[1], : x.shape[1]])
        router = mem.router if hasattr(mem, "router") else None
        regs = ref_regs(model.cell.variant, mem.keys, mem.wq, router, h, names)
        lt = torch.sqrt(sum((g_l[n].double() ** 2).sum() for n in theta))
        pulls = []
        for nm in names:
            tps = [dict(params)[n] for n in theta]
            gr = torch.autograd.grad(regs[nm], tps, retain_graph=True, allow_unused=True)
            gr = [torch.zeros_like(p) if v is None else v for v, p in zip(gr, tps)]
            nr = torch.sqrt(sum((v.double() ** 2).sum() for v in gr))
            ok = bool(torch.isfinite(nr)) and bool(torch.isfinite(lt)) and float(nr) >= 1e-12
            lam = float(ALPHA * lt / nr) if ok else 0.0
            lams[nm] = lam
            pulls.append((lam, gr))
        for lam, gr in pulls:
            if lam != 0.0:
                for n, v in zip(theta, gr):
                    g[n] = g[n] + lam * v
    total = torch.sqrt(sum((v.double() ** 2).sum() for v in g.values()))
    coef = min(1.0, CLIP / (float(total) + 1e-6))
    return {n: v * coef for n, v in g.items()}, lams, float(total)


def ref_adamw(params, grads, state, step):
    with torch.no_grad():
        for n, p in params:
            m, v = state.setdefault(n, (torch.zeros_like(p), torch.zeros_like(p)))
            gr = grads[n]
            m = B1 * m + (1 - B1) * gr
            v = B2 * v + (1 - B2) * gr * gr
            state[n] = (m, v)
            mhat = m / (1 - B1**step)
            denom = (v / (1 - B2**step)).sqrt() + ADAM_EPS
            p.sub_(LR * mhat / denom)


# ==================================== HARNESS (compares) ====================================
def main() -> int:
    sys.path.insert(0, "src")
    from arborlm import p8_core as core
    from arborlm import p8_objective as obj
    from arborlm.p5_model import insertion_hidden, optimizer_for

    torch.set_num_threads(1)
    results = {"values": [], "grads": [], "fd": [], "selection": [], "step": [], "structure": []}

    def build(case, dtype, seed=601, parent=101):
        cell = core.Cell(parent, 200 + parent, seed, case)
        m = core.build_model(cell, core.synthetic_backbone(cell))
        return m.to(dtype)

    def tokens(cell, rows, seed):
        g = torch.Generator().manual_seed(seed)
        return torch.randint(0, 256, (rows, 65), generator=g)

    # --- 1. selection equivalence on real dims (float32, as run), flat / fixed / learned -------
    for case in ("C01", "C02", "C03"):
        for seed in (601, 602):
            m = build(case, torch.float32, seed)
            batch = tokens(m.cell, 8, 11 + seed)
            with torch.no_grad():
                h = insertion_hidden(m, batch[:, :-1])
                q = F.normalize(F.linear(h, m.addition.wq), dim=-1, eps=1e-8).reshape(-1, 16)
                weights, lookup = m.addition.lookup(q)
                sc, ids = obj.candidate_scores(m.addition, q)
                from arborlm.pilot_model import stable_top

                sv, sel = stable_top(sc, 8, ids)
                _, lk_full = m(batch[:, :-1])
                rs, rids = ref_scores(m.cell.variant, m.addition.keys.double(),
                                      m.addition.wq.double(),
                                      m.addition.router.double() if case != "C01" else None,
                                      h.double())
                ref_top = rids.gather(1, torch.sort(-rs, dim=-1, stable=True).indices[:, :8])
            results["selection"].append({
                "case": case, "seed": seed,
                "impl_top8_ids_equal_lookup_selected": bool(torch.equal(sel, lookup.selected)),
                "impl_top8_scores_bitwise_equal_lookup_weights": bool(torch.equal(sv, weights)),
                "full_forward_selected_equal": bool(torch.equal(sel, lk_full.selected)),
                "ref_float64_top8_set_equal": bool(torch.equal(ref_top.sort(1).values,
                                                               sel.sort(1).values)),
                "max_abs_score_impl_minus_ref64": float((sc.double() - rs).abs().max())
                if torch.equal(ids, rids) else "ids differ",
            })

    # --- 2. regularizer values and gradients, float64 and float32 ------------------------------
    for dtype in (torch.float64, torch.float32):
        for case in ("C01", "C02", "C03"):
            m = build(case, dtype)
            mem = m.addition
            batch = tokens(m.cell, 8, 21)
            with torch.no_grad():
                h = insertion_hidden(m, batch[:, :-1])
            router = mem.router if case != "C01" else None
            theta = [mem.keys, mem.wq] + ([mem.router] if case == "C03" else [])
            tnames = ["keys", "wq"] + (["router"] if case == "C03" else [])
            for name in ("conc", "co", "temp"):
                ref = ref_regs(m.cell.variant, mem.keys, mem.wq, router, h, (name,))[name]
                q = F.normalize(F.linear(h, mem.wq), dim=-1, eps=1e-8).reshape(-1, 16)
                sc, ids = obj.candidate_scores(mem, q)
                soft = obj.soft_inclusion(sc, ids)
                imp = obj.regularizer_values(soft, 8, (name,))[name]
                gi = torch.autograd.grad(imp, theta, retain_graph=True)
                gr = torch.autograd.grad(ref, theta, retain_graph=True)
                dead = torch.autograd.grad(imp, [mem.values, mem.wo, mem.gate],
                                           allow_unused=True, retain_graph=True)
                results["values"].append({
                    "dtype": str(dtype), "case": case, "reg": name,
                    "impl": float(imp), "ref": float(ref), "abs_diff": abs(float(imp - ref))})
                for tn, a, b in zip(tnames, gi, gr):
                    results["grads"].append({
                        "dtype": str(dtype), "case": case, "reg": name, "param": tn,
                        "max_abs_diff": float((a - b).abs().max()),
                        "max_abs_ref": float(b.abs().max()),
                        "nonzero": bool(a.abs().sum() > 0)})
                results["structure"].append({
                    "dtype": str(dtype), "case": case, "reg": name,
                    "values_wo_gate_grad": [None if d is None else float(d.abs().max())
                                            for d in dead]})

    # --- 3. finite differences, float64, real dims, 2 rows x 16 positions ------------------------
    gen = torch.Generator().manual_seed(7)
    for case in ("C01", "C03"):
        m = build(case, torch.float64)
        mem = m.addition
        batch = tokens(m.cell, 2, 31)[:, :17]
        with torch.no_grad():
            h = insertion_hidden(m, batch[:, :-1])
        router = mem.router if case != "C01" else None

        def impl_val(name):
            q = F.normalize(F.linear(h, mem.wq), dim=-1, eps=1e-8).reshape(-1, 16)
            sc, ids = obj.candidate_scores(mem, q)
            return obj.regularizer_values(obj.soft_inclusion(sc, ids), 2, (name,))[name]

        for name in ("conc", "co", "temp"):
            plist = [("keys", mem.keys), ("wq", mem.wq)] + ([("router", mem.router)]
                                                           if case == "C03" else [])
            grads = torch.autograd.grad(impl_val(name), [p for _, p in plist])
            for (pn, p), gimp in zip(plist, grads):
                flat_g = gimp.reshape(-1)
                cand = torch.cat([flat_g.abs().topk(6).indices,
                                  torch.randint(0, flat_g.numel(), (4,), generator=gen)])
                worst_impl, worst_ref = 0.0, 0.0
                for c in cand.tolist():
                    e = 1e-6
                    with torch.no_grad():
                        p.view(-1)[c] += e
                        up = float(ref_regs(m.cell.variant, mem.keys, mem.wq, router, h,
                                            (name,))[name])
                        p.view(-1)[c] -= 2 * e
                        dn = float(ref_regs(m.cell.variant, mem.keys, mem.wq, router, h,
                                            (name,))[name])
                        p.view(-1)[c] += e
                    fd = (up - dn) / (2 * e)
                    worst_impl = max(worst_impl, abs(fd - float(flat_g[c])))
                results["fd"].append({"case": case, "reg": name, "param": pn,
                                      "coords": len(cand), "max_abs_fd_minus_impl": worst_impl,
                                      "max_abs_grad_checked": float(flat_g[cand].abs().max())})

    # --- 4. structural: R_temp no cross-row / future leakage ------------------------------------
    pi = torch.rand(4 * 16, SLOTS, dtype=torch.float64)
    base = ref_temp(pi, 1 - pi, 4)
    # impl on a constructed Soft whose top-64 = dense rows (via topk of pi itself)
    def impl_temp_dense(p):
        top, idx = p.topk(64, dim=-1)
        soft = obj.Soft(top, idx, torch.log1p(-top), torch.zeros(p.shape[0], dtype=p.dtype))
        return obj.r_temp(soft, 4)
    def ref_temp_top(p):
        top, idx = p.topk(64, dim=-1)
        d = torch.zeros_like(p).scatter(1, idx, top)
        return ref_temp(d, 1 - d, 4)
    a, b = impl_temp_dense(pi), ref_temp_top(pi)
    # per-row Jacobian test: gradient of the term mean wrt row-0 queries must not depend on row 1
    x = pi.clone().requires_grad_(True)
    g = torch.autograd.grad(impl_temp_dense(x), x)[0].reshape(4, 16, SLOTS)
    y = pi.clone()
    y.reshape(4, 16, SLOTS)[1] = torch.rand(16, SLOTS, dtype=torch.float64)
    y = y.requires_grad_(True)
    g2 = torch.autograd.grad(impl_temp_dense(y), y)[0].reshape(4, 16, SLOTS)
    # future: changing position 15 of row 0 cannot change gradient wrt positions <= 6 of row 0
    zz = pi.clone(); zz.reshape(4, 16, SLOTS)[0, 15] = torch.rand(SLOTS, dtype=torch.float64)
    zz = zz.requires_grad_(True)
    g3 = torch.autograd.grad(impl_temp_dense(zz), zz)[0].reshape(4, 16, SLOTS)
    results["structure"].append({
        "r_temp_impl_vs_ref_dense_abs_diff": float((a - b).abs()),
        "row0_grad_unchanged_when_row1_changes": float((g[0] - g2[0]).abs().max()),
        "row0_pos0to6_grad_unchanged_when_row0_pos15_changes": float(
            (g[0, :7] - g3[0, :7]).abs().max()),
        "grad_row0_pos15_vs_window_ok_note": "positions <=6 are outside pos15's window (7..14)",
        "unused": float(base),
    })

    # --- 5. full training step: impl final gradient (pre-clip, captured) vs reference --------------
    import torch.nn.utils as nnu
    orig = nnu.clip_grad_norm_
    captured = {}

    def spy(params, *a, **k):
        captured["g"] = [p.grad.detach().clone() for p in params]
        return orig(params, *a, **k)

    for dtype in (torch.float64, torch.float32):
        for case in ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10"):
            impl_m = build(case, dtype)
            ref_m = copy.deepcopy(impl_m)
            opt = optimizer_for(impl_m)
            names = [n for n, p in impl_m.named_parameters() if p.requires_grad]
            state = {}
            worst_g, worst_p, lam_diff = 0.0, 0.0, 0.0
            for step in range(1, 4):
                batch = tokens(impl_m.cell, 8, 100 + step)
                obj.nn.utils.clip_grad_norm_ = spy
                try:
                    rec = obj.train_step_p8(impl_m, opt, batch, step, impl_m.cell.objective)
                finally:
                    obj.nn.utils.clip_grad_norm_ = orig
                pre = dict(zip(names, captured["g"]))
                gref, lams, total = ref_combined_grad(ref_m, batch, impl_m.cell.objective)
                coef = min(1.0, CLIP / (total + 1e-6))
                for n in names:
                    worst_g = max(worst_g, float((pre[n] * coef - gref[n]).abs().max()))
                for k, v in lams.items():
                    lam_diff = max(lam_diff, abs(v - rec["lam"][k]) / max(abs(v), 1e-30))
                ref_adamw([(n, p) for n, p in ref_m.named_parameters() if p.requires_grad],
                          gref, state, step)
                ip, rp = dict(impl_m.named_parameters()), dict(ref_m.named_parameters())
                worst_p = max(worst_p, max(float((ip[n] - rp[n]).abs().max()) for n in names))
                # keep both on identical parameters so later steps compare the rule, not drift
                with torch.no_grad():
                    for n in names:
                        rp[n].copy_(ip[n])
            results["step"].append({"dtype": str(dtype), "case": case,
                                    "objective": list(impl_m.cell.objective),
                                    "max_abs_clipped_grad_diff": worst_g,
                                    "max_rel_lambda_diff": lam_diff,
                                    "max_abs_param_diff_after_step": worst_p})

    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
