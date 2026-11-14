"""C3 - is rev 1's usage floor R_util active at initialization? (toy + read-only use of P8 records)

R_util = max(0, ln(0.5 M) - H(u)) / ln N, M = min(N, 8 F_b), F_b = 128 distinct facts per batch, so the
hinge threshold is ln 512 = 6.238 nats at every size. u is the batch mean of pi normalized to sum 1;
pi_s = sigmoid((score_s - tau)/0.25) on each query's top-64, tau the midpoint of the 8th and 9th
scores, score = cos / 0.2 (as in ADR-0015 rev 3 / p8_objective.soft_inclusion; re-implemented here).
Rev 1 section 7: lambda is measured once on the first batch; ||g_R|| < 1e-6 => ENGINEERING_FAIL.

Part 1 (toy): keys i.i.d. uniform on S^15; 1024 queries q = normalize(mu + s z), z ~ N(0, I/16), for a
range of spreads s (s = 0: all queries identical; large s: isotropic). Also ||grad R_util|| on keys
and on a stand-in query projection.
Part 2 (records, read-only): P8 logged the same batch entropy at update 1 as R_conc * ln 4096
(steps.jsonl 'diagnostics.regularizer_all.conc'), on natural text, 512 queries per batch, N = 4096.
"""

import glob
import json
import math
import statistics
import sys
from pathlib import Path

import torch

TEMP, BETA, SOFT_TOP, TOP = 0.2, 0.25, 64, 8
THRESH = math.log(512)


def r_util(q: torch.Tensor, keys: torch.Tensor, n: int) -> tuple[torch.Tensor, float]:
    scores = q @ torch.nn.functional.normalize(keys, dim=1).T / TEMP
    top, idx = scores.topk(SOFT_TOP, dim=1)
    tau = 0.5 * (top[:, TOP - 1] + top[:, TOP])
    pi = torch.sigmoid((top - tau[:, None]) / BETA)
    usage = torch.zeros(q.shape[0], n, dtype=q.dtype).scatter(1, idx, pi).sum(0)
    u = usage / usage.sum()
    h = -(u[u > 0] * u[u > 0].log()).sum()
    return torch.clamp(THRESH - h, min=0) / math.log(n), float(h)


def part1() -> None:
    torch.set_num_threads(4)
    for n in (4096, 16384, 65536):
        g = torch.Generator().manual_seed(n)
        keys = torch.randn(n, 16, generator=g, dtype=torch.float64).requires_grad_(True)
        mu = torch.nn.functional.normalize(torch.randn(16, generator=g, dtype=torch.float64), dim=0)
        z = torch.randn(1024, 16, generator=g, dtype=torch.float64) / 4.0
        for s in (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 3.0):
            w = torch.eye(16, dtype=torch.float64).requires_grad_(True)  # stand-in query projection
            q = torch.nn.functional.normalize((mu + s * z) @ w.T, dim=1)
            r, h = r_util(q, keys, n)
            if r.item() > 0:
                gk, gw = torch.autograd.grad(r, (keys, w))
                gnorm = float(torch.cat([gk.flatten(), gw.flatten()]).norm())
            else:
                gnorm = 0.0
            print(json.dumps({"N": n, "query_spread_s": s, "H_nats": round(h, 3),
                              "effective_slots_exp_H": round(math.exp(h), 1),
                              "R_util": round(r.item(), 5), "grad_norm_keys_and_proj": gnorm,
                              "engineering_fail_rule_triggers": gnorm < 1e-6}), flush=True)
    for n in (4096, 16384, 65536):
        print(json.dumps({"N": n, "R_util_max_when_H_0": round(THRESH / math.log(n), 4)}))


def part2(root: Path) -> None:
    by_case: dict[str, list[float]] = {}
    files = sorted(glob.glob(str(root / "results/p8-2026-11-14/train/P8T-*/cells/*/steps.jsonl")))
    for f in files:
        case = f.split("/cells/")[1].split("/")[0].split("-")[-1]
        with open(f) as fh:
            for line in fh:
                rec = json.loads(line)
                if rec.get("step") == 1 and "diagnostics" in rec:
                    h = rec["diagnostics"]["regularizer_all"]["conc"] * math.log(4096)
                    by_case.setdefault(case, []).append(h)
                    break
    print(json.dumps({"p8_files_read": len(files)}))
    for case, hs in sorted(by_case.items()):
        print(json.dumps({"p8_case": case, "cells": len(hs), "H_at_update_1_nats_min_median_max":
                          [round(min(hs), 3), round(statistics.median(hs), 3), round(max(hs), 3)],
                          "above_ln512_threshold_6.238": sum(h > THRESH for h in hs)}))


if __name__ == "__main__":
    part1()
    part2(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd())
