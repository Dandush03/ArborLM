"""Audit item 1: frozen-hidden probes, recomputed and extended with the auditor's own code.

Train stream: the rehearsal calibration stream restricted to the first F facts (each fact twice,
contexts never in training). Test stream: rehearsal Panel A restricted to F (each fact once, new
contexts). Same split as the record, so the reproduced numbers are comparable.

Reported, per parent and F:
  R1  nearest stored state at the answer site (cosine, predict the stored answer)   [record repro]
  R2  ridge least-squares classifier per identifier symbol at the answer site      [record repro]
  N1  multinomial logistic probe (L-BFGS) and an MLP probe (1 hidden layer, 256 GELU) per symbol,
      at each of the record's 7 input positions (sep, id1..id5, binding = answer site), after block 0,
      and on the raw embedding (before block 0) at the answer site
  N2  the same probes on the concatenation of the 7 positions (224-d) and of positions id1..binding
  N3  held-out information lower bound per symbol, 5 - CE_bits (variational bound on I(symbol; h)),
      and a lower bound on identifier bits: for independent symbols I(X1..X4; h) >= sum_i I(Xi; h),
      maximised over the five choices of 4 of the 5 symbols (any 4 are independent and uniform)
  N4  nearest stored state at every record position (fact identification from one position)
  N5  MLP probe that predicts the ANSWER directly from one position / the concatenation (trained on
      the calibration stream's two occurrences of each fact, tested on Panel A) - a memorisation probe

Usage: uv run --locked python docs/reviews/p9-calibration-audit-2026-11-14/probes.py [F ...]
"""

import json
import math
import sys
import time

import _common as c
import torch
from torch.nn import functional as F

LOG2 = math.log(2)
POS_NAMES = ["sep", "id1", "id2", "id3", "id4", "id5", "bind"]


def features(bb, tokens):
    emb, h = c.hidden_states(bb, tokens)
    cidx = tokens.shape[0]
    # [C, 8 records, 7 positions, 32]
    pos = torch.tensor([[8 * r + k for k in range(7)] for r in range(8)])
    h_rec = h[:, pos].reshape(cidx * 8, 7, 32)
    e_rec = emb[:, pos].reshape(cidx * 8, 7, 32)
    return e_rec, h_rec


def standardize(xtr, xte):
    m, s = xtr.mean(0), xtr.std(0).clamp_min(1e-6)
    return (xtr - m) / s, (xte - m) / s


def logistic(xtr, ytr, xte, yte, l2=1e-4, iters=200):
    xtr, xte = standardize(xtr.double(), xte.double())
    d = xtr.shape[1]
    w = torch.zeros(d + 1, 32, dtype=torch.float64, requires_grad=True)
    xa = torch.cat([xtr, torch.ones(len(xtr), 1, dtype=torch.float64)], 1)
    opt = torch.optim.LBFGS([w], lr=1, max_iter=iters, line_search_fn="strong_wolfe", tolerance_grad=1e-9)

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(xa @ w, ytr) + l2 * (w[:-1] ** 2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        z = torch.cat([xte, torch.ones(len(xte), 1, dtype=torch.float64)], 1) @ w
        ce = F.cross_entropy(z, yte).item() / LOG2
        acc = (z.argmax(1) == yte).double().mean().item()
    return acc, 5.0 - ce


def mlp(xtr, ytr, xte, yte, hidden=256, steps=1500, wd=1e-4, seed=179901, classes=32):
    """1-hidden-layer GELU MLP; full-batch Adam; the step count is chosen on a 10% split of the
    training rows (best held-out CE every 100 steps), then the model at that step is evaluated."""
    g = torch.Generator().manual_seed(seed)
    xtr, xte = standardize(xtr.float(), xte.float())
    n = len(xtr)
    perm = torch.randperm(n, generator=g)
    va, tr = perm[: n // 10], perm[n // 10 :]
    torch.manual_seed(seed)
    net = torch.nn.Sequential(torch.nn.Linear(xtr.shape[1], hidden), torch.nn.GELU(), torch.nn.Linear(hidden, classes))
    opt = torch.optim.AdamW(net.parameters(), lr=3e-3, weight_decay=wd)
    best = (float("inf"), None)
    for step in range(1, steps + 1):
        opt.zero_grad()
        F.cross_entropy(net(xtr[tr]), ytr[tr]).backward()
        opt.step()
        if step % 100 == 0:
            with torch.no_grad():
                v = F.cross_entropy(net(xtr[va]), ytr[va]).item()
            if v < best[0]:
                best = (v, {k: t.clone() for k, t in net.state_dict().items()})
    net.load_state_dict(best[1])
    with torch.no_grad():
        z = net(xte)
        ce = F.cross_entropy(z, yte).item() / LOG2
        acc = (z.argmax(1) == yte).float().mean().item()
    return acc, 5.0 - ce


def nearest(xtr, ans_tr, xte, ans_te):
    a = F.normalize(xtr.float(), dim=-1)
    b = F.normalize(xte.float(), dim=-1)
    out = []
    for s in range(0, len(b), 2048):
        out.append(ans_tr[(b[s : s + 2048] @ a.T).argmax(1)])
    return (torch.cat(out) == ans_te).float().mean().item()


def ident_bits(info5):
    best = -1e9
    for drop in range(5):
        best = max(best, sum(v for i, v in enumerate(info5) if i != drop))
    return best


def run(parent, facts, s, quick):
    bb = c.backbone(parent)
    tr_tok, tr_ids = c.restrict(s.streams["calibration"], facts)
    te_tok, te_ids = c.restrict(s.streams["panel_a"], facts)
    tr_ids, te_ids = tr_ids.reshape(-1), te_ids.reshape(-1)
    assert len(te_ids) == facts and len(tr_ids) == 2 * facts
    assert torch.equal(torch.sort(te_ids).values, torch.arange(facts))
    # targets from the TOKENS (not the bookkeeping): symbols at positions 8r+1..8r+5, answer at 8r+7
    sym_tr = (tr_tok.reshape(-1, 8, 8)[:, :, 1:6] - 0x40).reshape(-1, 5)
    sym_te = (te_tok.reshape(-1, 8, 8)[:, :, 1:6] - 0x40).reshape(-1, 5)
    ans_tr = (tr_tok.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1)
    ans_te = (te_tok.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1)
    assert torch.equal(sym_tr, s.facts.ident[tr_ids]) and torch.equal(ans_te, s.facts.answer[te_ids])
    e_tr, h_tr = features(bb, tr_tok)
    e_te, h_te = features(bb, te_tok)
    out = {"parent": parent, "facts": facts, "train_queries": len(tr_ids), "test_queries": len(te_ids)}

    # R1 reproduction: nearest stored state at the answer site
    out["nearest_answer_site"] = nearest(h_tr[:, 6], ans_tr, h_te[:, 6], ans_te)
    out["nearest_answer_site_embedding"] = nearest(e_tr[:, 6], ans_tr, e_te[:, 6], ans_te)
    # N4: nearest stored state per position and concatenations
    out["nearest_by_position"] = {POS_NAMES[p]: nearest(h_tr[:, p], ans_tr, h_te[:, p], ans_te) for p in range(7)}
    out["nearest_concat_all7"] = nearest(h_tr.reshape(len(h_tr), -1), ans_tr, h_te.reshape(len(h_te), -1), ans_te)

    # R2 reproduction: ridge least squares per symbol at the answer site (own code; strength by 80/20)
    ridge = []
    xtr, xte = standardize(h_tr[:, 6].double(), h_te[:, 6].double())
    xtr = torch.cat([xtr, torch.ones(len(xtr), 1, dtype=torch.float64)], 1)
    xte = torch.cat([xte, torch.ones(len(xte), 1, dtype=torch.float64)], 1)
    g = torch.Generator().manual_seed(179014)
    perm = torch.randperm(len(xtr), generator=g)
    fit, hold = perm[: int(0.8 * len(xtr))], perm[int(0.8 * len(xtr)) :]
    for i in range(5):
        y = F.one_hot(sym_tr[:, i], 32).double()
        best = (-1, None)
        for lam in (1e-6, 1e-4, 1e-2, 1.0):
            pen = torch.eye(33, dtype=torch.float64) * lam * len(fit)
            pen[-1, -1] = 0
            w = torch.linalg.solve(xtr[fit].T @ xtr[fit] + pen, xtr[fit].T @ y[fit])
            a = ((xtr[hold] @ w).argmax(1) == sym_tr[hold, i]).double().mean().item()
            if a > best[0]:
                best = (a, lam)
        pen = torch.eye(33, dtype=torch.float64) * best[1] * len(xtr)
        pen[-1, -1] = 0
        w = torch.linalg.solve(xtr.T @ xtr + pen, xtr.T @ y)
        ridge.append(((xte @ w).argmax(1) == sym_te[:, i]).double().mean().item())
    out["ridge_answer_site"] = ridge

    # N1/N3: logistic probe per position x symbol, bits
    lg_acc, lg_bits = {}, {}
    for p in range(7):
        accs, bits = [], []
        for i in range(5):
            a, b = logistic(h_tr[:, p], sym_tr[:, i], h_te[:, p], sym_te[:, i])
            accs.append(a)
            bits.append(b)
        lg_acc[POS_NAMES[p]], lg_bits[POS_NAMES[p]] = accs, bits
    out["logistic_acc"] = lg_acc
    out["logistic_bits"] = lg_bits
    out["logistic_ident_bits_lower_bound"] = {k: ident_bits(v) for k, v in lg_bits.items()}
    emb_bits = [logistic(e_tr[:, 6], sym_tr[:, i], e_te[:, 6], sym_te[:, i])[1] for i in range(5)]
    out["logistic_bits_answer_site_before_block0"] = emb_bits
    # N2: concatenations
    for name, sl in (("concat_all7", slice(0, 7)), ("concat_id1_to_bind", slice(1, 7)), ("concat_id5_bind", slice(5, 7))):
        xa, xb = h_tr[:, sl].reshape(len(h_tr), -1), h_te[:, sl].reshape(len(h_te), -1)
        res = [logistic(xa, sym_tr[:, i], xb, sym_te[:, i]) for i in range(5)]
        out[f"logistic_{name}_acc"] = [r[0] for r in res]
        out[f"logistic_{name}_bits"] = [r[1] for r in res]
        out[f"logistic_{name}_ident_bits_lower_bound"] = ident_bits([r[1] for r in res])

    # N1: MLP probes per symbol at the answer site and at id5 (the best single position) and concat
    mlp_res = {}
    for name, xa, xb in (
        ("bind", h_tr[:, 6], h_te[:, 6]),
        ("id5", h_tr[:, 5], h_te[:, 5]),
        ("concat_all7", h_tr.reshape(len(h_tr), -1), h_te.reshape(len(h_te), -1)),
    ):
        res = [mlp(xa, sym_tr[:, i], xb, sym_te[:, i], steps=600 if quick else 1500) for i in range(5)]
        mlp_res[name] = {"acc": [r[0] for r in res], "bits": [r[1] for r in res], "ident_bits_lower_bound": ident_bits([r[1] for r in res])}
    out["mlp_symbol"] = mlp_res
    # N5: answer memorisation probes (fact seen twice in the calibration stream, tested in a new context)
    mem = {}
    for name, xa, xb in (
        ("bind", h_tr[:, 6], h_te[:, 6]),
        ("id5", h_tr[:, 5], h_te[:, 5]),
        ("concat_all7", h_tr.reshape(len(h_tr), -1), h_te.reshape(len(h_te), -1)),
    ):
        a, b = mlp(xa, ans_tr, xb, ans_te, hidden=1024, steps=600 if quick else 1500, wd=0.0)
        mem[name] = {"acc": a, "bits": b}
    out["mlp_answer_memorisation"] = mem
    return out


def main():
    sizes = [int(a) for a in sys.argv[1:]] or [2048, 8192, 32768]
    s = c.study()
    results = []
    for parent in ("b101", "b102"):
        for facts in sizes:
            t = time.time()
            r = run(parent, facts, s, quick=facts >= 32768)
            r["seconds"] = time.time() - t
            print(json.dumps(r))
            results.append(r)
    name = "probes_" + "_".join(map(str, sizes)) + ".json"
    (c.OUT / name).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
