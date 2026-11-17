"""D-OQ (ADR-0021 section 5.3) and the cost measures of section 5.4.

1. Parameter match by hand (49 h + 1 against 48 N + 1,025) and from built models; init bounds and moments; D-OQ's input tensor equals F-OQ's codes;
   an independent D-OQ forward written from the ADR text equals the model's addition; the addition is zero off the answer sites.
2. Multiply-adds of ONE training update counted by torch's FlopCounterMode (forward + backward, real frozen backbone B101/O301, batch of 16 contexts,
   test-seed data), against the implementer's analytic formula 3 x 128 x W + 4 x trainable parameters (frozen.analytic_madds_per_update).
3. The MC multipliers of every pair under each measure; which pairs become MC-SHORT under the analytic measure alone (the larger multiplier is used,
   so MC-SHORT under one measure is MC-SHORT whatever the CPU measure says).

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c3_doq_and_costs.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import math
import sys

import torch
from torch.nn import functional as F
from torch.utils.flop_counter import FlopCounterMode

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as d
from studies.p10s1 import core
from studies.p10s1 import frozen as fz
from studies.p10s1 import model as M
from studies.p10s1 import train as T

torch.set_num_threads(1)
CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
SLOTS = (4096, 16384, 65536)
GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)


def by_hand():
    out = {}
    for n in SLOTS:
        p_f = n * (16 + 32) + 32 * 32 + 1
        h = round((p_f - 1) / 49)
        cands = {hh: abs(49 * hh + 1 - p_f) / p_f for hh in (h - 1, h, h + 1)}
        out[n] = {"foq_params": p_f, "h": h, "doq_params": 49 * h + 1, "rel": abs(49 * h + 1 - p_f) / p_f, "neighbours_rel": cands, "impl_h": core.doq_hidden(n)}
    return out


def doq_checks(backbone, data):
    seeds = data.seeds
    res = {}
    stream = T.training_stream_for(data, 512)
    tok = stream.batch(1).tokens[:, :63].contiguous()
    for n in SLOTS:
        foq = M.build_model("F-OQ", n, 2101, backbone, r1_seed=seeds.r1_codes, seed_rng=False)
        doq = M.build_model("D-OQ", n, 2101, backbone, r1_seed=seeds.r1_codes, seed_rng=False)
        a = doq.addition
        h = a.hidden
        w1, b1, w2 = a.w1.detach(), a.b1.detach(), a.w2.detach()
        r = {
            "trainable_built_foq": sum(p.numel() for p in foq.parameters() if p.requires_grad), "trainable_built_doq": sum(p.numel() for p in doq.parameters() if p.requires_grad),
            "trainable_backbone_doq": sum(p.numel() for n_, p in doq.named_parameters() if n_.startswith("backbone.") and p.requires_grad),
            "w1_shape": list(w1.shape), "b1_shape": list(b1.shape), "w2_shape": list(w2.shape), "gate": float(a.gate.detach()),
            "w1_absmax_le_0.25": float(w1.abs().max()) <= 0.25, "b1_absmax_le_0.25": float(b1.abs().max()) <= 0.25, "w2_absmax_le_1/sqrt(h)": float(w2.abs().max()) <= 1 / math.sqrt(h) + 1e-9,
            "w1_var_vs_uniform": float(w1.var()) / (0.25**2 / 3), "w2_var_vs_uniform": float(w2.var()) / ((1 / h) / 3), "b1_mean": float(b1.mean()),
        }
        codes_f = foq.oracle_codes(tok)
        codes_d = doq.oracle_codes(tok)
        r["codes_equal"] = bool(torch.equal(codes_f, codes_d))
        # own codes from the ADR: seeded unit code of the identifier, width 16
        with torch.no_grad():
            h_pre = doq.embed_block0(tok)
            read = doq.select(h_pre, tok)
            delta = doq.memory_delta(h_pre, read)
            mine_sites = torch.sigmoid(a.gate) * F.linear(F.gelu(codes_f @ w1.T + b1, approximate="none"), w2)
            sites = torch.tensor([8 * k + 6 for k in range(8)])
            r["delta_at_sites_equal_own_formula"] = bool(torch.allclose(delta[:, sites], mine_sites, atol=0, rtol=0)) or float((delta[:, sites] - mine_sites).abs().max())
            mask = torch.ones(63, dtype=torch.bool)
            mask[sites] = False
            r["delta_zero_off_sites"] = bool((delta[:, mask] == 0).all())
            pre = codes_f @ w1.T + b1
            r["preactivation_std_at_init"] = float(pre.std())
        res[n] = r
    return res


def flops_of_update(arm, n, backbone, data):
    seeds = data.seeds
    facts = 2048 if n == 4096 or arm != "R2" else 2048
    cell = core.make_cell("P", arm, facts, n, 1, 2101, run_updates=8, test=True)
    lut = T.fact_lut_for(data, facts) if arm == "R2" else None
    job = T.TrainJob(cell=cell, data=data, stream=T.training_stream_for(data, facts), backbone=backbone, out_dir=None, r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), mode="calibration", updates=8, fact_lut=lut)
    tr = T.Trainer(job, T.job_model(job))
    tr.step(job.stream.batch(1))
    fc = FlopCounterMode(display=False)
    with fc:
        tr.step(job.stream.batch(2))
    total = fc.get_total_flops()
    # the backbone alone: memory disabled forward + backward to h_pre (no memory parameter)
    return total


def backbone_flops(backbone, data):
    stream = T.training_stream_for(data, 512)
    tok = stream.batch(1).tokens
    m = M.build_model("H8", 4096, 2101, backbone, r1_seed=data.seeds.r1_codes, hash_seed=core.h8_seed(data.seeds), seed_rng=False)
    fc = FlopCounterMode(display=False)
    x = torch.zeros(16, 63, 32, requires_grad=True)
    with fc:
        h_pre = m.embed_block0(tok[:, :-1])
        logits = m.finish(h_pre.detach() + x, torch.zeros_like(h_pre))
        logits.sum().backward()
    return fc.get_total_flops()


def mc_mult(ratio, run_cheaper, u_p=8192):
    for g in GRID:
        if g >= ratio - 1e-12:
            return g, ("OK" if g * u_p <= run_cheaper else "MC-SHORT")
    return None, "MC-SHORT"


def main():
    root = p9core.default_experiments_root()
    backbone, _ = controls.load_backbone(p9core.PRIMARY_PARENT, root)
    data = d.build_study_data(core.test_seeds(6), CORPUS, sizes=d.DataSizes(main_trained=2048, unseen=64, lane_d_per_set=128))
    out = {"by_hand": by_hand(), "doq": doq_checks(backbone, data)}
    madds_counted = {}
    for arm in ("F-OQ", "T-OQ", "H8", "R2", "D-OQ"):
        for n in SLOTS:
            if arm == "R2" and n == 4096:
                pass
            f = flops_of_update(arm, n, backbone, data)
            madds_counted[f"{arm}|{n}"] = {"flops_counted": f, "madds_counted": f / 2, "madds_impl_formula": fz.analytic_madds_per_update(arm, n)}
    out["madds_per_update"] = madds_counted
    out["backbone_only_forward_backward_flops"] = backbone_flops(backbone, data)
    # MC pairs under each measure
    run = {4096: 6 * 8192, 16384: 4 * 8192, 65536: 2 * 8192}
    pairs = []
    for arm in ("F-OQ", "T-OQ", "H8"):
        for small, large in ((4096, 16384), (16384, 65536)):
            pairs.append((f"cap|{arm}|{small}->{large}", (arm, small), (arm, large)))
    for arm in ("F-OQ", "T-OQ", "H8"):
        for n in (16384, 65536):
            pairs.append((f"dense|{arm}|{n}", (arm, n), ("D-OQ", n)))
    rows = []
    for key, a, b in pairs:
        row = {"pair": key}
        for meas in ("madds_impl_formula", "madds_counted"):
            ca, cb = madds_counted[f"{a[0]}|{a[1]}"][meas], madds_counted[f"{b[0]}|{b[1]}"][meas]
            ratio = cb / ca  # b costlier in every pair here
            cheaper_run = run[a[1]] if ratio >= 1 else (run[b[1]] if b[0] != "R2" else 8192)
            g, st = mc_mult(max(ratio, 1 / ratio), cheaper_run)
            row[meas] = {"ratio_b_over_a": ratio, "grid": g, "status": st}
        rows.append(row)
    out["mc_pairs"] = rows
    json.dump(out, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
