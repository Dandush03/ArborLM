"""Calibration-only: sensitivity of the section-2 utilization-adjusted ratio (HB analogue) to the
common-slope assumption and to where it is evaluated. Reads aggregate inputs from
calib_partitions.json. Not a registered outcome. Stdlib only."""
import json, math, statistics as st
OUT = "docs/reviews/p7b-spec-review-2026-11-13/rereview/outputs"
D = json.load(open(f"{OUT}/calib_partitions.json"))
assert D["eval_files_read"] == []
def parse(lb):
    b, o, *k, s = lb.split("-"); return f"{b}-{o}", s, "-".join(k)
by = {parse(r["label"])[2:] + parse(r["label"])[:2]: r for r in D["per_checkpoint"]}
def fit(pts):
    mx = st.fmean(x for x, _ in pts); my = st.fmean(y for _, y in pts)
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    b = sum((x - mx) * (y - my) for x, y in pts) / sxx
    a = my - b * mx
    res = [y - a - b * x for x, y in pts]
    se = math.sqrt(sum(r * r for r in res) / (len(pts) - 2) / sxx)
    return a, b, se, mx
for key in ("R2C32", "R8C8"):
    for tie in ("asc", "desc"):
        for kind in ("fixed_tree", "learned_tree"):
            T, F = [], []
            for (k, p, s), r in by.items():
                lay = "B" if k == kind else "COAX" if k == "flat" else None
                if lay is None: continue
                e = r["m"][f"actual|{lay}|{key}"][tie] / r["m"][f"null|FREQ|{key}"][tie]
                (T if k == kind else F).append((math.log(r["eff_slots"]), e))
            at, bt, set_, mxt = fit(T); af, bf, sef, mxf = fit(F)
            xbar = st.fmean([x for x, _ in T + F])
            sep = lambda x: (at + bt * x) / (af + bf * x)
            z = (bt - bf) / math.sqrt(set_ ** 2 + sef ** 2)
            print(f"{key} {tie} {kind:12s} slopes tree {bt:+.3f}({set_:.3f}) flat {bf:+.3f}({sef:.3f}) z(diff) {z:+.2f} | "
                  f"separate-slope ratio at pooled mean {sep(xbar):.3f}, at flat mean {sep(mxf):.3f}, at tree mean {sep(mxt):.3f} | "
                  f"x ranges tree {min(x for x,_ in T):.2f}-{max(x for x,_ in T):.2f} flat {min(x for x,_ in F):.2f}-{max(x for x,_ in F):.2f}")
