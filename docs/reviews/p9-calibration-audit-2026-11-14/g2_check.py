"""Audit item 4: G2 and the exposure rule recomputed independently.

* No-memory baseline counts with the auditor's own forward and scorer (B101 primary, B102 reported),
  on Panels A and B restricted to 2,048 / 8,192 / 32,768 trained facts, and on the unseen set.
* Exact binomial central interval at level 1 - 0.001/k around p = 1/32 (own log-space pmf; the
  interval is [lo, hi] with P(X < lo) <= a/2 and P(X > hi) <= a/2, lo largest / hi smallest).
* Exposure rule (ADR 12 step 4) under alternative aggregations of the 9 R2 cells: minimum over all
  runs and panels (implemented), B101 only (the registered A5 R2 cells), mean over runs.
"""

import json
import math

import _common as c
import torch

SITES = torch.tensor([8 * r + 6 for r in range(8)])


def interval(n, tests, p=1 / 32):
    alpha = 0.001 / tests
    logpmf = [math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p) for k in range(n + 1)]
    pmf = [math.exp(v) for v in logpmf]
    lo, acc = 0, 0.0
    while acc + pmf[lo] <= alpha / 2:
        acc += pmf[lo]
        lo += 1
    hi, acc = n, 0.0
    while acc + pmf[hi] <= alpha / 2:
        acc += pmf[hi]
        hi -= 1
    return lo, hi


@torch.no_grad()
def nomem(bb, tok):
    cr = []
    for st in range(0, len(tok), 512):
        tk = tok[st : st + 512]
        lg = c.head(bb, c.hidden0(bb, tk[:, :63]))[:, SITES].reshape(-1, 256)
        cr.append(c.score(lg, (tk.reshape(-1, 8, 8)[:, :, 7] - 0x40).reshape(-1))[0])
    return int(torch.cat(cr).sum())


def main():
    s = c.study()
    rec = json.loads((c.RUN / "calibration.json").read_text())
    out = {"no_memory": {}, "intervals": {}, "g2": []}
    for parent in ("b101", "b102"):
        bb = c.backbone(parent)
        for name in ("panel_a", "panel_b"):
            st = s.streams[name]
            for facts in (2048, 8192, 32768):
                tok, _ = c.restrict(st, facts)
                k = nomem(bb, tok)
                out["no_memory"][f"{parent}/{name}/{facts}"] = [k, len(tok) * 8]
            unseen = (st.fact_ids >= s.facts.trained).all(1)
            k = nomem(bb, st.tokens[unseen])
            out["no_memory"][f"{parent}/{name}/unseen"] = [k, int(unseen.sum()) * 8]
    for n in (2048, 8192, 32768):
        out["intervals"][str(n)] = interval(n, 8)
    out["intervals"]["4096_lane_d"] = interval(4096, 4)
    recorded = rec["controls"]["g2"]["primary"]["results"]
    for r in recorded:
        panel, setname = r["name"].split("/")
        mine = out["no_memory"][f"b101/{panel}/{setname}"]
        iv = interval(mine[1], 8)
        out["g2"].append({"name": r["name"], "recorded": [r["correct"], r["facts"], r["interval"]], "mine": [mine[0], mine[1], list(iv)], "inside": iv[0] <= mine[0] <= iv[1]})
    for r in rec["controls"]["g2"]["lane_d"]["results"]:
        iv = interval(r["facts"], 4)
        out["g2"].append({"name": r["name"], "recorded": [r["correct"], r["facts"], r["interval"]], "my_interval": list(iv), "inside": iv[0] <= r["correct"] <= iv[1]})
    # exposure rule under aggregations
    det = rec["r2_detail"]

    def agg(fn, keep):
        curves = {}
        for label, by_e in det.items():
            if not keep(label):
                continue
            n = int(label.split("-n")[1].split("-")[0])
            for e, panels in by_e.items():
                curves.setdefault(n, {}).setdefault(int(e), []).extend(panels.values())
        curves = {n: {e: fn(v) for e, v in d.items()} for n, d in curves.items()}
        failed = sorted(n for n, d in curves.items() if d[128] < 0.95)
        live = [n for n in curves if n not in failed]
        sel = next((e for e in (32, 64, 128) if all(curves[n][e] >= 0.95 for n in live)), None)
        return {"curves": curves, "selected": sel, "failed": failed}

    out["rule"] = {
        "min_all_runs (implemented)": agg(min, lambda lab: True),
        "min_b101_only (registered A5 R2 cells)": agg(min, lambda lab: "b101" in lab),
        "mean_all_runs": agg(lambda v: sum(v) / len(v), lambda lab: True),
    }
    print(json.dumps(out, indent=1))
    (c.OUT / "g2_check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
