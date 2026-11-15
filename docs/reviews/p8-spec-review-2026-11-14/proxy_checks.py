"""Auditor's throwaway checks of ADR-0015 section 3/4 proxy mathematics (synthetic only).

Independent re-implementation from the ADR text. Imports arborlm.pilot_model only for the
real Memory parameter layout in check E7 (not an analysis module). No data, no checkpoint.
Run: uv run --locked python docs/reviews/p8-spec-review-2026-11-14/proxy_checks.py
"""

import math

import torch
from torch.nn import functional as F

torch.set_default_dtype(torch.float64)
BETA, TOP, T, W, G = 0.25, 8, 0.2, 8, 8


def soft_inclusion(s: torch.Tensor) -> torch.Tensor:
    """s: [..., N] candidate scores. pi = sigmoid((s - tau)/beta), tau = mid of 8th/9th."""
    v = s.topk(TOP + 1, dim=-1).values
    tau = 0.5 * (v[..., TOP - 1] + v[..., TOP])
    return torch.sigmoid((s - tau[..., None]) / BETA)


def log1m_pi(s: torch.Tensor) -> torch.Tensor:
    v = s.topk(TOP + 1, dim=-1).values
    tau = 0.5 * (v[..., TOP - 1] + v[..., TOP])
    return -F.softplus((s - tau[..., None]) / BETA)  # exact log(1 - pi)


def r_co(pi_full: torch.Tensor, l1m_full: torch.Tensor) -> torch.Tensor:
    """pi_full: [Q, S] (zeros for non-candidates); groups of G consecutive IDs."""
    q, s = pi_full.shape
    n = (1 - torch.exp(l1m_full.reshape(q, s // G, G).sum(-1))).sum(-1)
    return (n / pi_full.sum(-1)).mean()


def r_temp(pi: torch.Tensor, l1m: torch.Tensor) -> torch.Tensor:
    """pi, l1m: [rows, positions, S]."""
    vals = []
    for t in range(1, pi.shape[1]):
        lo = max(0, t - W)
        c = 1 - torch.exp(l1m[:, lo:t].sum(1))
        vals.append((pi[:, t] * (1 - c)).sum(-1) / pi[:, t].sum(-1))
    return torch.stack(vals, 1).mean()


def r_conc(pi_full: torch.Tensor) -> torch.Tensor:
    tot = pi_full.reshape(-1, pi_full.shape[-1]).sum(0)
    u = tot / tot.sum()
    h = -(u * torch.log(u.clamp_min(1e-300))).sum()
    return h / math.log(pi_full.shape[-1])


def all_r(s_full: torch.Tensor, rows: int, pos: int, cand: torch.Tensor | None = None):
    """s_full: [Q, S] scores; cand: [Q, S] bool mask of candidates (trees), else all."""
    if cand is None:
        pi = soft_inclusion(s_full)
        l1m = log1m_pi(s_full)
    else:
        big = torch.where(cand, s_full, torch.full_like(s_full, -1e9))
        pi = soft_inclusion(big) * cand
        l1m = log1m_pi(big) * cand
    sh = (rows, pos, s_full.shape[-1])
    return r_co(pi, l1m), r_temp(pi.reshape(sh), l1m.reshape(sh)), r_conc(pi), pi


def hdr(x: str) -> None:
    print(f"\n=== {x} ===")


# E1 gradcheck (float64, away from ties) -----------------------------------------------
hdr("E1 gradcheck vs finite differences (S=40, rows=2, positions=5)")
g = torch.Generator().manual_seed(1)
s0 = torch.randn(10, 40, generator=g) * 2
for name, f in [
    ("R_co", lambda s: all_r(s, 2, 5)[0]),
    ("R_temp", lambda s: all_r(s, 2, 5)[1]),
    ("R_conc", lambda s: all_r(s, 2, 5)[2]),
]:
    ok = torch.autograd.gradcheck(f, (s0.clone().requires_grad_(),), eps=1e-6, atol=1e-6)
    print(name, "gradcheck", ok)

# E2 ties --------------------------------------------------------------------------------
hdr("E2 count of pi > 1/2 with an exact tie at the 8th/9th score")
s = torch.tensor([[9.0, 8, 7, 6, 5, 4, 3, 2, 2, 1, 0, -1]])
pi = soft_inclusion(s)
print("scores", s.tolist()[0])
print("pi", [round(x, 4) for x in pi.tolist()[0]], "count>0.5 =", int((pi > 0.5).sum()))
s32 = torch.tensor([[5.0, 4, 3, 2, 1, 0.5, 0.25, 0.1, 0.1, -1]], dtype=torch.float32)
v = s32.topk(9).values
p32 = torch.sigmoid((s32 - 0.5 * (v[0, 7] + v[0, 8])) / BETA)
print("float32 same tie: count>0.5 =", int((p32 > 0.5).sum()))

# E3 R_co one-group ratio vs p -------------------------------------------------------------
hdr("E3 R_co for 8 selected slots forming one group, all with inclusion p (no tail)")
for p in (0.51, 0.6, 0.75, 0.9, 0.99, 0.999999):
    print(f"p={p}: R_co = {(1 - (1 - p) ** 8) / (8 * p):.4f}")

# E4 'sharpen onto one slot, top-8 set unchanged' -----------------------------------------
hdr("E4 sharpening one already-selected slot (top-8 set and tau unchanged)")
S = 64
base = torch.full((1, S), -3.0)
sel = [0, 1, 8, 16, 24, 32, 40, 48]  # slots 0 and 1 share group 0; others distinct groups
for k, i in enumerate(sel):
    base[0, i] = 1.0 - 0.05 * k
base[0, 56] = 0.2  # 9th
for bump in (0.0, 1.0, 2.0, 3.0):
    s = base.clone()
    s[0, 0] += bump
    pi = soft_inclusion(s)
    print(f"bump slot0 +{bump}: tau unchanged={bool(True)} R_co={r_co(pi, log1m_pi(s)).item():.5f}")
# R_temp: slot 0 was selected at the previous position
prev = base.clone()
for bump in (0.0, 2.0):
    cur = base.clone()
    cur[0, 0] += bump
    cur[0, 1:8] -= 0  # same set
    # make current set differ from previous except slot 0: shift previous other slots away
    pv = prev.clone()
    for i in sel[1:]:
        pv[0, i] = -3.0
    for j, i in enumerate([2, 3, 4, 5, 6, 7, 9]):
        pv[0, i] = 0.9 - 0.05 * j
    st = torch.stack([pv, cur], 1)
    print(f"R_temp, bump reused slot0 +{bump}: {r_temp(soft_inclusion(st), log1m_pi(st)).item():.5f}")
# R_conc: batch of 4 queries all including slot 0 (hot); sharpen slot 0 in all
for bump in (0.0, 2.0):
    qs = []
    gg = torch.Generator().manual_seed(4)
    for r in range(4):
        x = torch.full((S,), -3.0)
        others = torch.randperm(S - 1, generator=gg)[:8] + 1
        x[others] = torch.linspace(0.9, 0.2, 8)
        x[0] = 1.0 + bump
        qs.append(x)
    sq = torch.stack(qs)
    print(f"R_conc, bump hot slot0 +{bump}: {r_conc(soft_inclusion(sq)).item():.5f}")

# E5 realistic-geometry initialization, flat vs tree --------------------------------------
hdr("E5 init-like geometry (unit keys/router/queries, 16-d, 4096 slots), 8 rows x 64 positions")
gen = torch.Generator().manual_seed(601)
keys = F.normalize(torch.randn(4096, 16, generator=gen), dim=-1)
router = F.normalize(torch.randn(16, 16, generator=gen), dim=-1)
q = F.normalize(torch.randn(512, 16, generator=gen), dim=-1)
s_flat = q @ keys.T / T
routes = q @ router.T / T
b2 = routes.topk(2, dim=-1).indices
prior = routes.log_softmax(-1)
cand = torch.zeros(512, 4096, dtype=torch.bool)
s_tree = s_flat.clone()
for j in range(2):
    for qi in range(512):
        b = int(b2[qi, j])
        cand[qi, b * 256:(b + 1) * 256] = True
        s_tree[qi, b * 256:(b + 1) * 256] += prior[qi, b]
for name, sc, cm in (("flat", s_flat, None), ("tree", s_tree, cand)):
    rco, rt, rc, pi = all_r(sc, 8, 64, cm)
    hard = (sc if cm is None else torch.where(cm, sc, torch.full_like(sc, -1e9))).topk(8).indices
    groups = torch.tensor([len(set((h // 8).tolist())) for h in hard], dtype=torch.float64)
    piq = pi.sum(-1)
    sv = (sc if cm is None else torch.where(cm, sc, torch.full_like(sc, -1e9))).topk(9).values
    print(
        f"{name}: mean sum(pi)={piq.mean():.2f} (min {piq.min():.2f}, max {piq.max():.2f}); "
        f"mass outside hard top-8 = {(piq - pi.gather(1, hard).sum(-1)).mean():.2f}; "
        f"R_co={rco:.4f} hard groups/8={(groups / 8).mean():.4f}; R_temp={rt:.4f}; R_conc={rc:.4f}; "
        f"median gap s8-s9={(sv[:, 7] - sv[:, 8]).median():.4f}"
    )
    if name == "tree":
        top_share = (hard // 256 == b2[:, :1]).double().mean()
        print(f"tree: share of hard top-8 in top branch = {top_share:.3f}; "
              f"median route gap = {(routes.topk(2).values[:, 0] - routes.topk(2).values[:, 1]).median():.3f}")

# E6 optimize each regularizer alone; does the hard outcome move? --------------------------
hdr("E6 Adam(lr .003) on R alone, keys+wq(+router) trainable, fixed synthetic h, 300 steps")


def run(kind: str, reg: str, steps: int = 300):
    gen = torch.Generator().manual_seed(7)
    h = torch.randn(512, 32, generator=gen)
    k = (torch.randn(4096, 16, generator=gen) * 0.02).requires_grad_()
    wq = (torch.randn(16, 32, generator=gen) * 0.02).requires_grad_()
    rt = (torch.randn(16, 16, generator=gen) * 0.02).requires_grad_()
    params = [k, wq] + ([rt] if kind == "tree" else [])
    opt = torch.optim.AdamW(params, lr=0.003, betas=(0.9, 0.999), eps=1e-8, weight_decay=0)

    def stats(final: bool = False):
        qq = F.normalize(h @ wq.T, dim=-1)
        sc = qq @ F.normalize(k, dim=-1).T / T
        cm = None
        if kind == "tree":
            ro = qq @ F.normalize(rt, dim=-1).T / T
            bb = ro.topk(2, dim=-1).indices
            cm = torch.zeros_like(sc, dtype=torch.bool)
            idx = (bb[..., None] * 256 + torch.arange(256)).flatten(1)
            cm.scatter_(1, idx, True)
            pr = ro.log_softmax(-1)
            add = torch.zeros_like(sc).scatter(1, idx, pr.gather(1, bb).repeat_interleave(256, 1))
            sc = sc + add
        rco, rtm, rc, pi = all_r(sc, 8, 64, cm)
        masked = sc if cm is None else torch.where(cm, sc, torch.full_like(sc, -1e9))
        hard = masked.topk(9)
        grp = torch.tensor([len(set((x // 8).tolist())) for x in hard.indices[:, :8]]).double().mean()
        uniq = hard.indices[:, :8].unique().numel()
        hset = hard.indices[:, :8].reshape(8, 64, 8)
        reuse = []
        for t in range(1, 64):
            lo = max(0, t - 8)
            for r in range(8):
                prev = set(hset[r, lo:t].flatten().tolist())
                reuse.append(sum(int(x in prev) for x in hset[r, t].tolist()) / 8)
        val = {"R_co": rco, "R_temp": rtm, "R_conc": rc}[reg]
        return val, dict(
            R=round(val.item(), 4),
            sum_pi=round(pi.sum(-1).mean().item(), 2),
            gap89=round((hard.values[:, 7] - hard.values[:, 8]).mean().item(), 3),
            hard_groups=round(grp.item(), 3),
            distinct_slots=uniq,
            hard_reuse=round(sum(reuse) / len(reuse), 3),
        )

    out = []
    for step in range(steps + 1):
        opt.zero_grad()
        val, st = stats()
        if step in (0, steps // 3, steps):
            out.append((step, st))
        if step < steps:
            val.backward()
            opt.step()
    return out


for kind in ("flat", "tree"):
    for reg in ("R_co", "R_temp", "R_conc"):
        for step, st in run(kind, reg):
            print(kind, reg, step, st)

# E7 zero gradient on values/wo/gate through the real Memory parameters -------------------
hdr("E7 gradient path through arborlm.pilot_model.Memory parameters")
from arborlm.pilot_model import Memory  # noqa: E402

for variant in ("flat", "learned_tree"):
    mem = Memory(variant, 601).double()
    h = torch.randn(1, 64, 32, generator=torch.Generator().manual_seed(3))
    qq = F.normalize(F.linear(h, mem.wq), dim=-1).reshape(-1, 16)
    sc = qq @ F.normalize(mem.keys, dim=-1).T / T
    if variant == "learned_tree":
        ro = qq @ F.normalize(mem.router, dim=-1).T / T
        sc = sc + ro.log_softmax(-1).repeat_interleave(256, 1)  # prior on all slots suffices here
    pi = soft_inclusion(sc)
    loss = r_co(pi, log1m_pi(sc)) + r_conc(pi)
    loss.backward()
    print(variant, {n: (None if p.grad is None else float(p.grad.norm())) for n, p in mem.named_parameters()})

# E8 Adam per-coordinate normalization vs the alpha-matched norm ---------------------------
hdr("E8 first Adam step: rows with only g_R move by ~lr regardless of lambda")
for lam in (1.0, 0.1, 0.01, 1e-4):
    p = torch.zeros(4, 16, requires_grad=True)
    opt = torch.optim.AdamW([p], lr=0.003, eps=1e-8, weight_decay=0)
    gl = torch.zeros(4, 16)
    gl[0] = 0.01  # row selected by L
    gr = torch.full((4, 16), 1e-4)
    p.grad = gl + lam * gr
    opt.step()
    print(f"lambda={lam:g}: |update| row0(L+R)={p[0].abs().mean():.2e}  rows1-3 (R only)={p[1:].abs().mean():.2e}")
# share of key coordinates on which g_R is the only gradient at init geometry (flat):
gen = torch.Generator().manual_seed(11)
h = torch.randn(512, 32, generator=gen)
k = (torch.randn(4096, 16, generator=gen) * 0.02).requires_grad_()
wq = (torch.randn(16, 32, generator=gen) * 0.02)
qq = F.normalize(h @ wq.T, dim=-1)
sc = qq @ F.normalize(k, dim=-1).T / T
pi = soft_inclusion(sc)
r_co(pi, log1m_pi(sc)).backward()
sel = sc.topk(8).indices.unique()
gr = k.grad
scale = 0.5 * 0.02 / gr.norm()  # assumes |g_L on Theta_r| ~ 0.02 (P5 total pre-clip median ~0.03)
big = (gr.abs() * scale > 1e-8)
print(f"key rows hard-selected in batch: {sel.numel()} of 4096")
print(f"key coordinates with |lambda g_R| > Adam eps 1e-8: {int(big.sum())} of {big.numel()}; "
      f"rows with any such coordinate: {int(big.any(1).sum())}; among unselected rows: "
      f"{int(big.any(1).sum()) - int(big[sel].any(1).sum())}")
print(f"rows with any |g_R| > 1e-12 (ADR gradient-reach metric): {int((gr.abs() > 1e-12).any(1).sum())}")
