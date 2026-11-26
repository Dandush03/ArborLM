# ruff: noqa
# ruff: noqa
"""M0-I0a audit, option (i): known-truth check of a FIXED-STRATA design (lineages fixed, items the unit).
Estimand: equal-weight mean over the G registered lineages of the paired difference. Test: stratified
estimate - z_.95 * stratified SE > -delta. Known power: the SAME fixed lineages (effects centred so the
estimand is exactly 0), fresh items. Procedure: from one M0 draw (1,500 items), recentre all items by the
M0 estimate (lineage differences kept), resample n/G items per lineage, same test. No tau anywhere.
Usage: python3 -I kt_fixed.py DRAWS SIMS TRUTH_RUNS SEED OUT.json
"""
import json, math, random, sys, time
from statistics import NormalDist, fmean, pstdev
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from kt_lib import clamp, cluster_sum

Z = NormalDist().inv_cdf; z95 = Z(0.95)


def strat_pass(sums, sqs, ns, delta):
    G = len(ns)
    means = [s / n for s, n in zip(sums, ns)]
    var = [(q - n * m * m) / (n - 1) for q, n, m in zip(sqs, ns, means)]
    est = fmean(means); se = math.sqrt(sum(v / n for v, n in zip(var, ns))) / G
    return est - z95 * se > -delta


def run(name, G, d, spread, n, target, draws, sims, truth, seed):
    rng = random.Random(f"{seed}/{name}"); t0 = time.time()
    raw = [rng.gauss(0, spread) for _ in range(G)]; c = fmean(raw)
    eff = [clamp(x - c, d) for x in raw]  # fixed lineage effects, estimand 0
    ns = [n // G] * G
    se0 = math.sqrt(sum((d - e * e) / m for e, m in zip(eff, ns))) / G
    delta = (z95 + Z(target)) * se0
    ok = 0
    for _ in range(truth):
        sums, sqs = [], []
        for e, m in zip(eff, ns):
            s, k = cluster_sum(rng, e, d, m); sums.append(s); sqs.append(k)
        ok += strat_pass(sums, sqs, ns, delta)
    known = ok / truth
    rec = []
    m0n = 1500 // G
    for _ in range(draws):
        m0 = [rng.choices((1, -1, 0), weights=((d + e) / 2, (d - e) / 2, 1 - d), k=m0n) for e in eff]
        th = fmean([fmean(cl) for cl in m0])
        pools = [[x - th for x in cl] for cl in m0]
        p = 0
        for _ in range(sims):
            sums, sqs = [], []
            for pool, m in zip(pools, ns):
                xs = rng.choices(pool, k=m); sums.append(sum(xs)); sqs.append(sum(x * x for x in xs))
            p += strat_pass(sums, sqs, ns, delta)
        rec.append(p / sims)
    r = dict(name=name, G=G, d=d, lineage_spread=spread, n=n, delta=delta, known=known, known_se=math.sqrt(known * (1 - known) / truth),
             recovered=fmean(rec), recovered_se=pstdev(rec) / math.sqrt(draws), recovered_sd=pstdev(rec), seconds=time.time() - t0)
    r["diff"] = r["recovered"] - r["known"]
    return r


if __name__ == "__main__":
    draws, sims, truth, seed, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    res = []
    for name, G, d, spread, n, target in (("G7_spread10_p80", 7, 0.3, 0.10, 6000, 0.8), ("G7_spread10_p996", 7, 0.3, 0.10, 6000, 0.99636),
                                          ("G10_spread05_p80", 10, 0.3, 0.05, 6000, 0.8)):
        r = run(name, G, d, spread, n, target, draws, sims, truth, seed)
        res.append(r)
        print(f"{name}: delta={r['delta']:.4f} known={r['known']:.4f}(se {r['known_se']:.4f}) recovered={r['recovered']:.4f}(se {r['recovered_se']:.4f}, sd {r['recovered_sd']:.3f}) diff={r['diff']:+.4f} {r['seconds']:.0f}s", flush=True)
        with open(out, "w") as fh: json.dump(res, fh, indent=1)
