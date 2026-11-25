# ruff: noqa
"""Audit D0: synthetic-store checks of my read conditions against a brute-force float64 reference typed directly from ADR-0035 section 4's table
(python loops, no torch.sort / torch.softmax), before any real snapshot is opened. Also hand-checkable cases: ties (lowest row index wins), K empty,
gate 0 at append, and the identities a = e(1) + e(2), e(1) = a when g2 = 0, b(1) = stage-1-only read.

Usage (from the D0 worktree): uv run --locked --offline python <this> -> audit_d0_out/synth_<UTC>.json
"""
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d0a_lib as L  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(6)
torch.use_deterministic_algorithms(True)


def brute(keys, vals, gates, rows, q):
    """Reference: lists of float64. Returns dict of reads (lists) per condition for one query."""
    n1 = rows[0]
    N = len(keys)
    stage = [1 if i < n1 else 2 for i in range(N)]
    kn = [[x / max(math.sqrt(sum(y * y for y in k)), 1e-12) for x in k] for k in keys]
    cos = [sum(a * b for a, b in zip(qq, kk)) for qq, kk in [(q, k) for k in kn]]

    def t8(idx):
        return sorted(idx, key=lambda i: (-cos[i], i))[:8]

    def sm(idx):
        if not idx:
            return {}
        m = max(cos[i] / 0.2 for i in idx)
        e = {i: math.exp(cos[i] / 0.2 - m) for i in idx}
        z = sum(e.values())
        return {i: e[i] / z for i in idx}

    def acc(wts):
        out = [0.0] * len(vals[0])
        for i, w in wts.items():
            for d in range(len(out)):
                out[d] += w * vals[i][d]
        return out

    gate = {1: gates[0], 2: gates[1]}
    S = {1: [i for i in range(N) if stage[i] == 1], 2: [i for i in range(N) if stage[i] == 2]}
    G = t8(range(N))
    sG = sm(G)
    res = {"a": acc({i: sG[i] * gate[stage[i]] for i in G})}
    for p in (1, 2):
        o = 3 - p
        T = t8(S[p])
        sT = sm(T)
        res[f"b{p}"] = acc({i: sT[i] * gate[p] for i in T})
        K = [i for i in G if stage[i] == p]
        sK = sm(K)
        res[f"d{p}"] = acc({i: sK[i] * gate[p] for i in K})
        res[f"e{p}"] = acc({i: sG[i] * gate[p] for i in G if stage[i] == p})
    res["c"] = [x + y for x, y in zip(res["b1"], res["b2"])]
    res["g1"] = [x + y for x, y in zip(res["b1"], res["e2"])]
    res["g2"] = [x + y for x, y in zip(res["b2"], res["e1"])]
    res["_n1"] = sum(1 for i in G if stage[i] == 1)
    return res


def make_store(rng, n1, n2, width, g1, g2, ties=False):
    def row(n):
        return [[rng.gauss(0, 1) for _ in range(16)] for _ in range(n)]

    k1, k2 = row(n1), row(n2)
    if ties:  # duplicate some keys across and within stages so cosines tie exactly
        for j in range(min(4, n2)):
            k2[j] = list(k1[j])
        if n1 > 3:
            k1[3] = list(k1[1])
    v1 = [[rng.gauss(0, 1) for _ in range(width)] for _ in range(n1)]
    v2 = [[rng.gauss(0, 1) for _ in range(width)] for _ in range(n2)]
    st = {"width": width, "stage_rows": [n1, n2], "keys": [torch.tensor(k1), torch.tensor(k2)], "values": [torch.tensor(v1), torch.tensor(v2)],
          "gates": [torch.tensor([g1]), torch.tensor([g2])]}
    return st


def main():
    rng = random.Random(20261124)
    worst = {}
    fails = []
    cases = 0
    configs = [(40, 30, 6, 0.7, 0.0, False), (40, 30, 6, 0.7, 1.3, False), (25, 25, 5, 1.0, 0.5, True), (10, 60, 4, 0.9, 0.8, False),
               (60, 10, 4, 0.9, 0.8, True), (9, 9, 3, 1.1, 0.0, True), (12, 200, 7, 0.4, 2.0, False)]
    for (n1, n2, width, g1, g2, ties) in configs:
        for rep in range(4):
            st = make_store(rng, n1, n2, width, g1, g2, ties)
            C = L.Conditions(st)
            # queries: random, plus queries equal to a stage-2 key (forces K1 small / possibly empty) and to tied keys
            qs = [[rng.gauss(0, 1) for _ in range(16)] for _ in range(20)]
            qs += [st["keys"][1][j].tolist() for j in range(min(5, n2))] + [st["keys"][0][j].tolist() for j in range(min(3, n1))]
            qs = [[x / math.sqrt(sum(y * y for y in qq)) for x in qq] for qq in qs]
            Q = torch.tensor(qs, dtype=torch.float32)
            out = C.compute(Q)
            keys = [list(map(float, k)) for k in torch.cat(st["keys"]).double().tolist()]
            vals = torch.cat(st["values"]).double().tolist()
            # the reference uses the float32 query and keys promoted to float64
            for i, qq in enumerate(Q.double().tolist()):
                ref = brute(keys, vals, [g1, float(torch.tensor(g2, dtype=torch.float32))] if False else [float(st["gates"][0]), float(st["gates"][1])], st["stage_rows"], qq)
                cases += 1
                for name in ("a", "b1", "b2", "c", "d1", "d2", "e1", "e2", "g1", "g2"):
                    dv = max(abs(x - y) for x, y in zip(out[name][i].double().tolist(), ref[name]))
                    worst[name] = max(worst.get(name, 0.0), dv)
                    if dv > 1e-5:
                        fails.append({"cfg": [n1, n2, width, g1, g2, ties], "q": i, "cond": name, "diff": dv})
                if int(out["_mask"][1][i].sum()) != ref["_n1"]:
                    fails.append({"cfg": [n1, n2, width, g1, g2, ties], "q": i, "cond": "n1", "mine": int(out["_mask"][1][i].sum()), "ref": ref["_n1"]})
            # identities
            if not torch.equal(out["a"], out["a_ref"]):
                fails.append({"cfg": [n1, n2], "identity": "a weight path == Store.read"})
            m1 = L.Store({"width": width, "stage_rows": [n1], "keys": [st["keys"][0]], "values": [st["values"][0]], "gates": [st["gates"][0]]})
            if not torch.equal(out["b1"], m1.read(Q)):
                fails.append({"cfg": [n1, n2], "identity": "b1 == stage-1-only store read"})
            if g2 == 0.0 and not torch.equal(out["e1"], out["a"]):
                fails.append({"cfg": [n1, n2], "identity": "e1 == a at gate 0"})
            dsum = float((out["a"] - out["e1"] - out["e2"]).abs().max())
            worst["a-(e1+e2)"] = max(worst.get("a-(e1+e2)", 0.0), dsum)
            if dsum > 1e-6 * max(1.0, float(out["a"].abs().max())):
                fails.append({"cfg": [n1, n2], "identity": "a = e1 + e2", "diff": dsum})
            worst["K1_empty_queries"] = worst.get("K1_empty_queries", 0) + int(out["_K_empty1"].sum())
            worst["K2_empty_queries"] = worst.get("K2_empty_queries", 0) + int(out["_K_empty2"].sum())
    # a hand-checkable tie case: two rows with identical keys in different stages; the lower index (stage 1) must be selected first
    st = {"width": 1, "stage_rows": [1, 1], "keys": [torch.tensor([[1.0] + [0.0] * 15]), torch.tensor([[1.0] + [0.0] * 15])],
          "values": [torch.tensor([[2.0]]), torch.tensor([[5.0]])], "gates": [torch.tensor([1.0]), torch.tensor([1.0])]}
    out = L.Conditions(st).compute(torch.tensor([[1.0] + [0.0] * 15]))
    hand = {"a": 3.5, "b1": 2.0, "b2": 5.0, "c": 7.0, "d1": 2.0, "d2": 5.0, "e1": 1.0, "e2": 2.5, "g1": 4.5, "g2": 6.0}
    for k, v in hand.items():
        if abs(float(out[k][0, 0]) - v) > 1e-6:
            fails.append({"hand": k, "mine": float(out[k][0, 0]), "expected": v})
    if int(out["_order"][0, 0]) != 0:
        fails.append({"hand": "tie order", "first": int(out["_order"][0, 0])})
    res = {"utc": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), "query_cases": cases, "worst_abs_diff_vs_float64_reference": worst, "failures": fails,
           "verdict": "PASS" if not fails else "FAIL", "torch": torch.__version__}
    p = L.OUT / f"synth_{res['utc']}.json"
    with open(p, "x") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1)[:3000])
    print("written", p)


if __name__ == "__main__":
    main()
