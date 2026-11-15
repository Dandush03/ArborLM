"""B1 - pure math, no backbone, no memory training: which query-code FAMILIES can address F checksum
identifiers with the ADR-0017 read (cosine, top-8, temperature 0.2, key width d)?

Auditor's own code. Identifiers are 5 symbols over 32, the fifth the sum of the first four mod 32
(ADR-0017 4.1), F distinct, drawn by seed (not the study's generator; no study data is used).

Code families (q_f is the unit query of fact f; keys are placed AT the noise-free queries, i.e. the
memory is an oracle store: key_f = q_f, value_f = one-hot answer_f, answers uniform random):
  R1        random unit code per identifier (the ADR's oracle query; also any hash/product code)
  ADD-rand  q = normalize(sum_k c_k[s_k]), c_k random Gaussian tables  (what a random linear W gives)
  ADD-opt   same family, tables c [5, 32, d] OPTIMIZED (contrastive, all F keys) - the best a linear
            map of per-position one-hot symbols can do: an upper bound for W7 / E7 up to context noise
  SHARED-opt q = normalize(sum_k a_k g[s_k]) with ONE shared symbol table g [32, d] and scalar position
            weights a_k (free sign), optimized - idealization of A1 (one head = weighted sum of one
            shared value map; block-0 position effects ignored)
  MLP-opt   q = normalize(MLP(one-hot 160 -> 256 GELU -> d)), optimized - a one-hidden-layer query

Evaluation (no noise): for each fact, top-8 keys by cosine, weights softmax(cos / 0.2), answer mass
from one-hot values; correct iff own answer mass is strictly the largest (ties wrong). Also reported:
median self weight, share of facts whose 2nd-best key has cosine > 0.9, median cosine of the nearest
other key. Optimization objective: InfoNCE over all F keys at training temperature 0.05; this is a
representation search, not the study's training signal (which is the answer loss through top-8).

Usage: uv run --locked python docs/reviews/adr-0018-design-2026-11-14/b1_code_families.py
"""

import json
import sys
import time
import warnings

warnings.filterwarnings("ignore", message="Failed to initialize NumPy")
import torch
from torch.nn import functional as F

TOP, TEMP, S = 8, 0.2, 32
torch.set_num_threads(8)


def identifiers(f, seed):
    g = torch.Generator().manual_seed(seed)
    flat = torch.randperm(S**4, generator=g)[:f]
    s4 = torch.stack([(flat // S**k) % S for k in (3, 2, 1, 0)], 1)
    return torch.cat([s4, (s4.sum(1) % S)[:, None]], 1)


@torch.no_grad()
def evaluate(q, k, ans):
    f = len(q)
    correct, wself, first_other, close = 0, [], [], 0
    for s in range(0, f, 2048):
        rows = torch.arange(s, min(s + 2048, f))
        sc = q[rows] @ k.T
        c, i = sc.topk(TOP + 1, dim=1)
        c8, i8 = c[:, :TOP], i[:, :TOP]
        w = (c8 / TEMP).softmax(1)
        hit = (i8 == rows[:, None]).float()
        wself.append((w * hit).sum(1))
        sc[torch.arange(len(rows)), rows] = -2
        other = sc.max(1).values
        first_other.append(other)
        close += int((other > 0.9).sum())
        mass = torch.zeros(len(rows), S).scatter_add_(1, ans[i8], w)
        own = mass.gather(1, ans[rows][:, None]).squeeze(1)
        mass.scatter_(1, ans[rows][:, None], -1.0)
        correct += int((own > mass.max(1).values).sum())
    ws, fo = torch.cat(wself), torch.cat(first_other)
    return {"naive_accuracy": round(correct / f, 4), "median_w_self": round(float(ws.median()), 4),
            "p10_w_self": round(float(ws.quantile(0.1)), 4),
            "median_cos_nearest_other": round(float(fo.median()), 4), "share_nearest_other_gt_0.9": round(close / f, 4)}


def optimize(make, params, f, steps, lr, seed, tt=0.05, batch=2048):
    opt = torch.optim.Adam(params, lr=lr)
    g = torch.Generator().manual_seed(seed)
    for step in range(steps):
        q = make()
        idx = torch.randint(0, f, (batch,), generator=g)
        loss = F.cross_entropy(q[idx] @ q.T / tt, idx)
        opt.zero_grad()
        loss.backward()
        opt.step()
    return float(loss)


def main():
    sizes = [int(a) for a in sys.argv[1:]] or [2048, 8192, 32768]
    out = []
    for f in sizes:
        ids = identifiers(f, seed=180900 + f)
        g = torch.Generator().manual_seed(180950 + f)
        ans = torch.randint(0, S, (f,), generator=g)
        onehot = F.one_hot(ids, S).float().reshape(f, 5 * S)
        for d in (16, 32):
            res = {}
            r1 = F.normalize(torch.randn(f, d, generator=g), dim=1)
            res["R1"] = evaluate(r1, r1, ans)
            tab = torch.randn(5, S, d, generator=g)
            q = F.normalize(sum(tab[k][ids[:, k]] for k in range(5)), dim=1)
            res["ADD-rand"] = evaluate(q, q, ans)

            torch.manual_seed(f + d)
            c = torch.nn.Parameter(torch.randn(5, S, d) * 0.3)
            make = lambda: F.normalize(sum(c[k][ids[:, k]] for k in range(5)), dim=1)  # noqa: E731
            t = time.time()
            loss = optimize(make, [c], f, steps=1500, lr=0.02, seed=1)
            with torch.no_grad():
                q = make()
            res["ADD-opt"] = evaluate(q, q, ans) | {"final_loss": round(loss, 3), "sec": round(time.time() - t, 1)}

            gtab = torch.nn.Parameter(torch.randn(S, d) * 0.3)
            a = torch.nn.Parameter(torch.tensor([1.0, 0.8, 0.6, 0.4, 0.2]))
            bias = torch.nn.Parameter(torch.zeros(d))
            make = lambda: F.normalize(sum(a[k] * gtab[ids[:, k]] for k in range(5)) + bias, dim=1)  # noqa: E731
            loss = optimize(make, [gtab, a, bias], f, steps=1500, lr=0.02, seed=2)
            with torch.no_grad():
                q = make()
            res["SHARED-opt"] = evaluate(q, q, ans) | {"final_loss": round(loss, 3), "a": [round(float(x), 3) for x in a]}

            net = torch.nn.Sequential(torch.nn.Linear(5 * S, 256), torch.nn.GELU(), torch.nn.Linear(256, d))
            make = lambda: F.normalize(net(onehot), dim=1)  # noqa: E731
            loss = optimize(make, list(net.parameters()), f, steps=1500, lr=0.003, seed=3)
            with torch.no_grad():
                q = make()
            res["MLP-opt"] = evaluate(q, q, ans) | {"final_loss": round(loss, 3)}
            for name, r in res.items():
                row = {"facts": f, "key_width": d, "family": name} | r
                print(json.dumps(row), flush=True)
                out.append(row)
    print(json.dumps({"python": sys.version.split()[0], "torch": torch.__version__}))


if __name__ == "__main__":
    main()
