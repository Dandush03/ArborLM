"""Audit item 3, correction of attainable_check.py: the record's attainable_probability is computed on
``restrict_stream(panel_a, 2048)``, which keeps the 2,048 trained-fact queries AND the 2,048 unseen-
control queries ("queries": 4096 in the record). Re-weight the per-symbol ceilings by the answers of
those 4,096 queries (answers read from the tokens).
"""

import json

import _common as c
import torch


def main():
    s = c.study()
    st = s.streams["panel_a"]
    keep = (st.fact_ids < 2048).all(1) | (st.fact_ids >= s.facts.trained).all(1)
    ans = (st.tokens[keep].reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1)
    w = torch.bincount(ans, minlength=32).double()
    w = w / w.sum()
    rec = json.loads((c.RUN / "calibration.json").read_text())["attainable_probability"]
    geo = json.loads((c.OUT / "unembed_geometry.json").read_text())
    ball = json.loads((c.OUT / "ball_check.json").read_text())
    out = {"queries": int(len(ans))}
    for parent, key in (("b101", "b101-o301"), ("b102", "b102-o302")):
        pf = torch.tensor([r["pmax_full"] for r in geo[parent]], dtype=torch.float64)
        ps = torch.tensor([r["pmax_sigma"] for r in geo[parent]], dtype=torch.float64)
        pb = torch.tensor(ball[parent]["pmax_ball"], dtype=torch.float64)
        out[parent] = {
            "record_mean": rec[f"{key}:mean"],
            "sphere_ceiling_mean": float((w * pf).sum()),
            "ball_ceiling_mean": float((w * pb).sum()),
            "record_fraction_ge_0.95": rec[f"{key}:fraction_at_least_0.95"],
            "share_answer_at_sign": float(w[0]),
            "record_sigma_mean": rec[f"{key}:sigma_mean"],
            "sigma_ceiling_mean": float((w * ps).sum()),
        }
    print(json.dumps(out, indent=1))
    (c.OUT / "attainable_check2.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
