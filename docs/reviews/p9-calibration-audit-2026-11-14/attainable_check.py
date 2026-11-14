"""Audit item 3: compare the record's attainable_probability with the exact per-symbol ceiling on the
reachable sphere (unembed_geometry.json), weighted by the answer distribution of the 2,048-fact Panel A
set the record used; and the ceiling this implies for the secondary log-loss metric (5 + log2 p_sigma).
"""

import json
import math

import _common as c
import torch


def main():
    s = c.study()
    geo = json.loads((c.OUT / "unembed_geometry.json").read_text())
    rec = json.loads((c.RUN / "calibration.json").read_text())["attainable_probability"]
    tok, ids = c.restrict(s.streams["panel_a"], 2048)
    ans = s.facts.answer[ids.reshape(-1)]
    counts = torch.bincount(ans, minlength=32).double()
    out = {}
    for parent in ("b101", "b102"):
        rows = geo[parent]
        pf = torch.tensor([r["pmax_full"] for r in rows], dtype=torch.float64)
        ps = torch.tensor([r["pmax_sigma"] for r in rows], dtype=torch.float64)
        w = counts / counts.sum()
        out[parent] = {
            "record_mean": rec[f"{parent}-o{301 if parent == 'b101' else 302}:mean"],
            "ceiling_weighted_mean": float((w * pf).sum()),
            "record_fraction_ge_0.95": rec[f"{parent}-o{301 if parent == 'b101' else 302}:fraction_at_least_0.95"],
            "share_of_answer_at_sign": float(w[0]),
            "record_sigma_mean": rec[f"{parent}-o{301 if parent == 'b101' else 302}:sigma_mean"],
            "ceiling_sigma_weighted_mean": float((w * ps).sum()),
            "logloss_gain_ceiling_bits_per_fact": float((w * (5 + torch.log2(ps))).sum()),
            "min_margin_logits": min(r["margin_dual_upper"] for r in rows),
        }
    print(json.dumps(out, indent=1))
    (c.OUT / "attainable_check.json").write_text(json.dumps(out, indent=1))
    assert math.isfinite(out["b101"]["ceiling_weighted_mean"])


if __name__ == "__main__":
    main()
