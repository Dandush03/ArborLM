"""C1b - stylized R0 addressing: what if the frozen block-0 state encodes the identifier additively?

Auditor toy, pure math, labelled STYLIZED. It does not use the ArborLM backbone (no model is run),
so the attention weights a_k below are assumptions, not measurements.

One attention layer gives, at the binding byte, approximately h = c + sum_k a_k * M_k e(s_k) + noise,
where s_1..s_4 are the identifier symbols (s_4 adjacent to the binding byte), e() are symbol
embeddings, M_k head mixing and a_k attention weights to position k. The query is
q = normalize(P h) with a 16 x 32 projection P (random here; a learned P can do better but is linear).

F identifiers are drawn without replacement from 32^4 (as in rev 1 section 4.1). Keys are placed at
the noise-free queries (best case). We report, at evaluation with context noise of relative size
sigma: top-1 key correct (the fact's own key ranks first), self weight, and naive accuracy as in C1.
"""

import json

import torch

TEMP, TOP, SYMBOLS, WIDTH, KEY = 0.2, 8, 32, 32, 16


def identifiers(f: int, seed: int) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    flat = torch.randperm(SYMBOLS**4, generator=g)[:f]
    return torch.stack([(flat // SYMBOLS**k) % SYMBOLS for k in (3, 2, 1, 0)], dim=1)


def main() -> None:
    torch.set_num_threads(4)
    g = torch.Generator().manual_seed(17)
    emb = torch.randn(SYMBOLS, WIDTH, generator=g, dtype=torch.float64) / WIDTH**0.5
    mix = [torch.linalg.qr(torch.randn(WIDTH, WIDTH, generator=g, dtype=torch.float64))[0] for _ in range(4)]
    proj = torch.randn(KEY, WIDTH, generator=g, dtype=torch.float64)
    profiles = {
        "equal (.25,.25,.25,.25)": (0.25, 0.25, 0.25, 0.25),
        "decaying (.10,.15,.25,.50)": (0.10, 0.15, 0.25, 0.50),
        "steep (.03,.07,.20,.70)": (0.03, 0.07, 0.20, 0.70),
    }
    for f in (2048, 8192, 32768):
        ids = identifiers(f, seed=f)
        for name, a in profiles.items():
            h = sum(a[k] * emb[ids[:, k]] @ mix[k].T for k in range(4))
            for sigma in (0.0, 0.1, 0.3):
                noise = torch.randn(f, WIDTH, generator=g, dtype=torch.float64)
                noise = noise / noise.norm(dim=1, keepdim=True) * h.norm(dim=1, keepdim=True) * sigma
                keys = torch.nn.functional.normalize(h @ proj.T, dim=1)
                q = torch.nn.functional.normalize((h + noise) @ proj.T, dim=1)
                own_first, wself, correct = 0, [], 0
                ans = torch.randint(0, SYMBOLS, (f,), generator=g)
                for s in range(0, f, 2048):
                    sc = q[s : s + 2048] @ keys.T
                    c, i = sc.topk(TOP, dim=1)
                    w = (c / TEMP).softmax(dim=1)
                    rows = torch.arange(s, min(s + 2048, f))
                    own_first += int((i[:, 0] == rows).sum())
                    hit = (i == rows[:, None]).double()
                    wself.append((w * hit).sum(1))
                    mass = torch.zeros(len(rows), SYMBOLS, dtype=torch.float64).scatter_add_(1, ans[i], w)
                    own = mass.gather(1, ans[rows][:, None]).squeeze(1)
                    mass.scatter_(1, ans[rows][:, None], -1.0)
                    correct += int((own > mass.max(1).values).sum())
                ws = torch.cat(wself)
                print(json.dumps({"facts": f, "attention_profile": name, "context_noise": sigma,
                                  "own_key_ranked_first": round(own_first / f, 4),
                                  "median_w_self": round(float(ws.median()), 4),
                                  "naive_accuracy": round(correct / f, 4)}), flush=True)


if __name__ == "__main__":
    main()
