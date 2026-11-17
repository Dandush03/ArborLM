"""Re-check auditor C: the COMPOSES rule of the combined-tasks addendum s8, my implementation (rules_v2.comp_*) against
studies/p10s2/analysis.composition on random synthetic combined records, plus the constructed strategies
(do-nothing, first-answer-only, copy-the-first-answer, ensemble, context-blind) and a random search for a cheap passing
strategy. Seeds 229201.. (test range). Usage: <python> check_composition.py <pin> <trials> <out.json>
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval."""

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis  # noqa: E402

import rules_v2 as S  # noqa: E402

ARMS = {"M-append-frozen": ("MAF", S.ORDERS), "M-ii": ("MII", S.ORDERS), "L-seq": ("LSEQ", S.ORDERS), "M-joint": ("MJOINT", ("-",)), "L-joint": ("LJOINT", ("-",)),
        "M-i-separate": ("M-i-separate", ("-",)), "L-sep": ("L-sep", ("-",))}


def jn(x):
    return "nan" if isinstance(x, float) and math.isnan(x) else x


def build_record(n, sigma, single, c1_second, c2_first, c2_second):
    """single[a][i]: single-task score of sentence i in a; c1_second[j]: score of item j's second answer; c2_first[i], c2_second[i].
    C1's first answer is the single-task answer of s1 in T1 by construction. Fields as combined._kind_record writes them, computed by me."""
    pairs = S.c1_pairs(sigma)
    rec = {"n": n, "pairs_sha256": "x"}
    items = [{"j": j, "i": [i1, i2], "langs": [t1, t2], "scores": [single[t1][i1], c1_second[j]]} for j, i1, i2, t1, t2 in pairs]
    tested = {"A": [], "B": []}
    tscore = {"A": [], "B": []}
    for it in items:
        tested[it["langs"][1]].append(it["i"][1])
        tscore[it["langs"][1]].append(it["scores"][1])
    rec["C1"] = {"items": items, "tested_sentences": tested, "tested_by_language": {a: jn(sum(v) / len(v)) if v else None for a, v in tscore.items()},
                 "mean": jn(sum((it["scores"][0] + it["scores"][1]) / 2 for it in items) / n), "pass_rate": 0.0}
    items2 = [{"j": i, "i": [i, i], "langs": ["A", "B"], "scores": [c2_first[i], c2_second[i]]} for i in range(n)]
    rec["C2"] = {"items": items2, "tested_sentences": {"A": list(range(n)), "B": list(range(n))},
                 "tested_by_language": {"A": jn(sum(c2_first) / n), "B": jn(sum(c2_second) / n)}, "mean": jn(sum((a + b) / 2 for a, b in zip(c2_first, c2_second)) / n), "pass_rate": 0.0}
    rec["single"] = {"scores": {a: [jn(x) for x in single[a]] for a in S.TASKS}}
    return rec


def mine_inputs(rec, s0, ens, kind, n, sigma):
    """(sK, sS, s0K, s0S, tS) per language computed from the ITEMS and my own pair list, not from the record's summary fields."""
    pairs = S.c1_pairs(sigma)
    out = {}
    for a in S.TASKS:
        if kind == "C1":
            idx = [(j, i2) for j, i1, i2, t1, t2 in pairs if t2 == a]
            sK = lambda r: sum(float(r["C1"]["items"][j]["scores"][1]) for j, _ in idx) / len(idx)  # noqa: E731
            sents = [i2 for _, i2 in idx]
        else:
            k = 0 if a == "A" else 1
            sK = lambda r: sum(float(it["scores"][k]) for it in r["C2"]["items"]) / n  # noqa: E731,B023
            sents = list(range(n))
        sS = lambda r: sum(float(r["single"]["scores"][a][i]) for i in sents) / len(sents)  # noqa: E731,B023
        out[a] = (sK(rec), sS(rec), sK(s0), sS(s0), sS(ens))
    return out


def rand_record(rng, n, sigma, level):
    """level: dict a -> (single mean, combined second mean, c2 first mean). Item scores scattered around it, clipped to [0, 1]."""
    def cl(x):
        return min(1.0, max(0.0, x))

    single = {a: [cl(level[a][0] + rng.uniform(-0.15, 0.15)) for _ in range(n)] for a in S.TASKS}
    pairs = S.c1_pairs(sigma)
    c1_second = [cl(level[t2][1] + rng.uniform(-0.15, 0.15)) for j, i1, i2, t1, t2 in pairs]
    c2_first = [cl(level["A"][2] + rng.uniform(-0.15, 0.15)) for _ in range(n)]
    c2_second = [cl(level["B"][1] + rng.uniform(-0.15, 0.15)) for _ in range(n)]
    return single, c1_second, c2_first, c2_second


def study_of(n_rep, recs, s0, ens, rejected):
    reps = []
    for r in range(n_rep):
        cells = {}
        assembled = {}
        for arm, (g, vs) in ARMS.items():
            for v in vs:
                rec = recs.get((arm, r, v))
                if arm in ("M-i-separate", "L-sep"):
                    assembled[arm] = {} if rec is None else {"combined": rec}
                    continue
                label = f"r{r}/{g}/{v}"
                snap = {} if rec is None else {"combined": rec}
                cells[label] = {"label": label, "status": "completed", "scores": {label: snap}, "extras": {"consolidation": {"rejected": rejected.get((r, v), False)}} if g == "MII" else {}}
        reps.append({"cells": cells, "assembled": assembled})
    return {"replicates": reps, "baseline": {"combined": {"stage0": s0, "ensemble": ens}}}


def main():
    trials = int(sys.argv[2])
    rng = random.Random(229201)
    dis, crashes = [], []
    seen = Counter()
    for t in range(trials):
        n = rng.choice([4, 5, 6, 7])
        sigma = list(range(n))
        rng.shuffle(sigma)
        n_rep = rng.choice([3, 4])
        s0_lv = {a: (rng.uniform(0.05, 0.3),) for a in S.TASKS}
        s0_lv = {a: (s0_lv[a][0], max(0.0, s0_lv[a][0] + rng.uniform(-0.1, 0.1)), s0_lv[a][0]) for a in S.TASKS}
        s0 = build_record(n, sigma, *rand_record(rng, n, sigma, s0_lv))
        t_lv = {a: (s0_lv[a][0] + rng.choice([0.2, 0.31, 0.4, 0.6, 0.6, 0.6]),) * 3 for a in S.TASKS}
        tsingle = rand_record(rng, n, sigma, t_lv)[0]
        ens = build_record(n, sigma, tsingle, [tsingle[t2][i2] for j, i1, i2, t1, t2 in S.c1_pairs(sigma)], tsingle["A"], tsingle["B"])
        recs = {}
        rejected = {}
        for arm, (g, vs) in ARMS.items():
            dense = rng.random() < 0.6
            arm_keep = rng.choice([0.3, 0.45, 0.8, 0.82, 0.9, 1.0])
            for v in vs:
                for r in range(n_rep):
                    if rng.random() < (0.005 if dense else 0.03):
                        continue  # a missing record
                    lv = {}
                    for a in S.TASKS:
                        tg = t_lv[a][0] - s0_lv[a][0]
                        sS = s0_lv[a][0] + tg * (rng.uniform(0.55, 1.0) if dense else rng.uniform(0.0, 1.2))
                        keep = (arm_keep + rng.uniform(-0.03, 0.03)) if dense else rng.choice([0.0, 0.3, 0.49, 0.5, 0.79, 0.8, 0.85, 1.0, 1.05])
                        sK = s0_lv[a][0] + keep * (sS - s0_lv[a][0])
                        lv[a] = (sS, sK, sK if rng.random() < 0.5 else sS)
                    rec = build_record(n, sigma, *rand_record(rng, n, sigma, lv))
                    if rng.random() < (0.002 if dense else 0.02):
                        rec["C2"]["items"][0]["scores"][1] = float("nan")
                        rec["C2"]["tested_by_language"]["B"] = "nan"
                    recs[(arm, r, v)] = rec
                if arm == "M-ii" and rng.random() < 0.1:
                    rejected[(rng.randrange(n_rep), v)] = True
        st = analysis.Study(study_of(n_rep, recs, s0, ens, rejected))
        try:
            out = analysis.composition(st)
        except Exception as e:
            crashes.append((t, repr(e)[:300]))
            continue
        for kind in ("C1", "C2"):
            for arm, (g, vs) in ARMS.items():
                cells = {}
                for v in vs:
                    cells[v] = []
                    for r in range(n_rep):
                        rec = recs.get((arm, r, v))
                        cells[v].append(None if rec is None else mine_inputs(rec, s0, ens, kind, n, sigma))
                mine = S.comp_class(cells, rejected=arm == "M-ii" and any(rejected.values()))
                impl = out["arms"][kind][arm]["composition"]
                seen[mine] += 1
                if mine != impl:
                    dis.append({"trial": t, "kind": kind, "arm": arm, "mine": mine, "impl": impl, "impl_reasons": out["arms"][kind][arm]["reasons"][:3]})
    print("trials", trials, "lines compared", sum(seen.values()))
    print("auditor classes seen:", dict(seen))
    print("crashes:", len(crashes), crashes[:3])
    print("disagreements:", len(dis), Counter((d["mine"], d["impl"]) for d in dis))
    Path(sys.argv[3]).write_text(json.dumps({"disagreements": dis[:50], "crashes": crashes[:20]}, indent=1, default=str))


if __name__ == "__main__":
    main()
