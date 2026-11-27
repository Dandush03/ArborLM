# ruff: noqa
"""Audit 4 (C1), step 5, VERSION 2 (for s4_rules_v2 classes; v1 kept): shortcut and closed-form rates from s4_rules records (stdlib only).

Per lineage and level (answers are open, chance 0):
  MF      most frequent key, 2-fold CV (folds: even / odd item index)
  MFsh    most frequent key per shape, 2-fold CV
  EFF_S   per shape, the best of {MF in shape, every S.* and G.* rule} chosen on one fold and scored on the other (both ways), summed over
          shapes / n: the score of the cheapest battery strategy at that level (level-wide)
  EFF_SM  the same with the M.* partial-trace mutations allowed
  EFF_F   the same with M.* and the F.* closed forms allowed
  in-shape rate of every S.*/F.* rule (hits / items of that shape), and its share of the level
Usage: python3 s5_analyse.py RULES_DIR OUT_JSON
"""
import glob, gzip, json, os, sys
from collections import Counter, defaultdict


def cv_mf(items, keyf):
    hit = 0
    for f in (0, 1):
        tab = defaultdict(Counter)
        for x in items:
            if x["i"] % 2 == f:
                tab[keyf(x)][x["key"]] += 1
        for x in items:
            if x["i"] % 2 != f:
                c = tab.get(keyf(x))
                if c:
                    best = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                    hit += best == x["key"]
    return hit / max(1, len(items))


def eff(items, allow):
    """2-fold CV: per shape choose the best predictor on train (MF of the shape or a rule whose prefix is allowed), score on test."""
    hit = 0
    for f in (0, 1):
        train = [x for x in items if x["i"] % 2 == f]
        test = [x for x in items if x["i"] % 2 != f]
        by_sh = defaultdict(list)
        for x in train:
            by_sh[x["shape"]].append(x)
        choice = {}
        for sh, sub in by_sh.items():
            sc = Counter()
            mf = Counter(x["key"] for x in sub).most_common(1)[0]
            sc[("MF", mf[0])] = mf[1]
            for x in sub:
                for r, v in x["R"].items():
                    if v is not None and r.split(".")[0] in allow and v == x["key"]:
                        sc[("R", r)] += 1
            best = sorted(sc.items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]
            choice[sh] = best
        for x in test:
            c = choice.get(x["shape"])
            if c is None:
                continue
            if c[0] == "MF":
                hit += x["key"] == c[1]
            else:
                hit += x["R"].get(c[1]) == x["key"]
    return hit / max(1, len(items))


def main():
    rd, outp = sys.argv[1], sys.argv[2]
    res = {}
    for fn in sorted(glob.glob(os.path.join(rd, "*.jsonl.gz"))):
        recs = [json.loads(l) for l in gzip.open(fn, "rt")]
        lid = recs[0]["lid"]
        per = {}
        for lv in range(7):
            its = [x for x in recs if x["lv"] == lv]
            n = len(its)
            shapes = Counter(x["shape"] for x in its)
            rules = {}
            for sh in sorted(shapes):
                sub = [x for x in its if x["shape"] == sh]
                names = sorted({r for x in sub for r, v in x["R"].items() if v is not None and r.split(".")[0] in ("S", "F", "M", "H")})
                for r in names:
                    k = sum(1 for x in sub if x["R"].get(r) == x["key"])
                    rules[f"{sh}|{r}"] = {"rate_in_shape": round(k / len(sub), 3), "share_of_level": round(k / n, 3), "n_shape": len(sub)}
                rules[f"{sh}|MF_in_shape_cv"] = {"rate_in_shape": round(cv_mf(sub, lambda x: 0), 3), "n_shape": len(sub)}
            per[lv] = {"n": n, "parse_fail": sum(1 for x in its if x["err"]), "shapes": dict(shapes), "distinct_keys": len({x["key"] for x in its}),
                       "MF": round(cv_mf(its, lambda x: 0), 3), "MFsh": round(cv_mf(its, lambda x: x["shape"]), 3),
                       "EFF_S": round(eff(its, ("S", "G")), 3), "EFF_SM": round(eff(its, ("S", "G", "M")), 3), "EFF_F": round(eff(its, ("S", "G", "M", "F")), 3), "rules": rules}
        res[lid] = per
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)
    # compact table
    for lid, per in res.items():
        row = " ".join(f"L{lv}:{per[lv]['MF']:.2f}/{per[lv]['EFF_S']:.2f}/{per[lv]['EFF_SM']:.2f}/{per[lv]['EFF_F']:.2f}" for lv in range(7))
        mx = max(per[lv]["EFF_S"] for lv in range(7))
        mxm = max(per[lv]["EFF_SM"] for lv in range(7))
        print(f"{lid:30s} maxS={mx:.3f} maxSM={mxm:.3f} {row}")


if __name__ == "__main__":
    main()
