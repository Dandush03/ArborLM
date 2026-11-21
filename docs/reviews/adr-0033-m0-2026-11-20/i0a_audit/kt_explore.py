# ruff: noqa
# ruff: noqa
"""M0-I0a audit: exploration of the section-9.4 procedure beyond Review 3's six scenarios.
Question: is the bias always conservative? How does it depend on items per cluster, on the power
level actually used (per-test target ~0.996), and on small G (7 to 10 clusters)?
Usage: python3 -I kt_explore.py SET DRAWS SIMS TRUTH_RUNS SEED OUT.json
  SET in {mvary, power, smallg}
"""
import json, math, random, sys, time
from statistics import NormalDist, fmean, pstdev
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from kt_lib import known_power, m0_draw, components, procedure_power, t_q

Z = NormalDist().inv_cdf


def delta_for(target, d, tau, g, n):
    return (t_q(0.95, g - 1) + Z(target)) * math.sqrt(tau * tau / g + d / n)


SETS = {
    # name: (d, tau, G (M0 and M5), m0 items per cluster, n (M5 items), target known power for choosing delta)
    "mvary": [
        ("tau0_m2", 0.3, 0.0, 300, 2, 6000, 0.8),
        ("tau0_m5", 0.3, 0.0, 300, 5, 6000, 0.8),
        ("tau0_m10", 0.3, 0.0, 300, 10, 6000, 0.8),
        ("tau0_m20", 0.3, 0.0, 300, 20, 6000, 0.8),
        ("tau05_m2", 0.3, 0.05, 300, 2, 6000, 0.8),
        ("tau05_m20", 0.3, 0.05, 300, 20, 6000, 0.8),
    ],
    "power": [
        ("tau10_m20_p50", 0.3, 0.10, 300, 20, 6000, 0.5),
        ("tau10_m20_p80", 0.3, 0.10, 300, 20, 6000, 0.8),
        ("tau10_m20_p996", 0.3, 0.10, 300, 20, 6000, 0.99636),
        ("tau05_m5_p996", 0.3, 0.05, 300, 5, 6000, 0.99636),
        ("tau0_m5_p996", 0.3, 0.0, 300, 5, 6000, 0.99636),
        ("tau05_m5_p30", 0.3, 0.05, 300, 5, 6000, 0.3),
    ],
    "smallg": [  # the written structure: about 7 to 10 lineages per part, 1,500 M0 items, sealed n = 20,000
        ("G7_tau0", 0.3, 0.0, 7, 214, 20000, 0.8),
        ("G7_tau05", 0.3, 0.05, 7, 214, 20000, 0.8),
        ("G7_tau10", 0.3, 0.10, 7, 214, 20000, 0.8),
        ("G10_tau03", 0.3, 0.03, 10, 150, 20000, 0.8),
        ("G10_tau10", 0.3, 0.10, 10, 150, 20000, 0.8),
    ],
}

if __name__ == "__main__":
    which, draws, sims, truth, seed, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    res = []
    for name, d, tau, g, m, n, target in SETS[which]:
        rng = random.Random(f"{seed}/{name}")
        t0 = time.time()
        delta = delta_for(target, d, tau, g, n)
        kp = known_power(rng, g, n, d, tau, delta, truth)
        rec, t2 = [], []
        for _ in range(draws):
            c = components(m0_draw(rng, d, tau, [m] * g))
            t2.append(c["tau2"])
            rec.append(procedure_power(rng, c, n, g, delta, sims))
        r = dict(name=name, d=d, tau=tau, G=g, m=m, n=n, delta=delta, known=kp, known_se=math.sqrt(kp * (1 - kp) / truth),
                 recovered=fmean(rec), recovered_se=pstdev(rec) / math.sqrt(draws), draw_sd=pstdev(rec),
                 tau2hat_mean=fmean(t2), share_zero=sum(1 for x in t2 if x == 0) / draws, draws=draws, sims=sims, truth_runs=truth,
                 seconds=time.time() - t0)
        r["diff"] = r["recovered"] - r["known"]
        res.append(r)
        print(f"{name}: delta={delta:.4f} known={kp:.4f}(se {r['known_se']:.4f}) recovered={r['recovered']:.4f}(se {r['recovered_se']:.4f}, sd {r['draw_sd']:.3f}) diff={r['diff']:+.4f} "
              f"tau2 true={tau*tau:.5f} tau2hat mean={r['tau2hat_mean']:.5f} zero={r['share_zero']:.2f} {r['seconds']:.0f}s", flush=True)
        with open(out, "w") as fh:
            json.dump(res, fh, indent=1)
