# ruff: noqa
# ruff: noqa
"""M0-I0a audit: the section-9.4 procedure AS WORDED, with strata, at the structure actually written
(about 7 lineages in 6 families per part; most families have ONE lineage), against the M5 test the
implementation would actually run there (fewer than 30 clusters -> t branch: unstratified
cluster-robust SE, t on G-1 df; studies/m0/stats.py `interval`, ruling 8).

Truth A (approved rule's reading, lineages random): fresh lineage effects N(0, tau) every run.
Truth B (lineages fixed): the M0 draw's own lineage effects, centred to mean zero, fresh items only.
Usage: python3 -I kt_strata.py DRAWS SIMS TRUTH_RUNS SEED OUT.json
"""
import json, math, random, sys, time
from statistics import NormalDist, fmean, pstdev
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from kt_lib import t_q, clamp, cluster_sum, m5_pass

Z = NormalDist().inv_cdf
N_SEALED, N_M0 = 20000, 1500


def strata_layout(sizes):
    lab = []
    for h, k in enumerate(sizes): lab += [h] * k
    return lab


def m0_draw(rng, d, tau, lab):
    g = len(lab); m = N_M0 // g
    mus = [clamp(rng.gauss(0, tau), d) for _ in range(g)]
    cl = [rng.choices((1, -1, 0), weights=((d + mu) / 2, (d - mu) / 2, 1 - d), k=m) for mu in mus]
    return cl, mus


def comps(cl, lab):
    g = len(cl); m_g = [len(c) for c in cl]
    means = [sum(c) / len(c) for c in cl]
    allx = [x for c in cl for x in c]; mu = fmean(allx); d = sum(1 for x in allx if x) / len(allx)
    ssw = [sum((x - means[i]) ** 2 for x in cl[i]) for i in range(g)]
    s_w2 = sum(ssw) / sum(m - 1 for m in m_g)
    H = sorted(set(lab)); xh = {}; num = den = 0
    for h in H:
        ms = [means[i] for i in range(g) if lab[i] == h]; xh[h] = fmean(ms)
        if len(ms) >= 2: num += sum((v - xh[h]) ** 2 for v in ms); den += len(ms) - 1
    V = num / den if den else 0.0
    tau2 = max(0.0, V - s_w2 * fmean([1 / m for m in m_g]))
    lam = [math.sqrt(tau2 / (tau2 + s_w2 / m)) if tau2 > 0 else 0.0 for m in m_g]
    dev = [lam[i] * (means[i] - xh[lab[i]]) for i in range(g)]
    pool = {h: [] for h in H}
    for i in range(g):
        k = math.sqrt(m_g[i] / (m_g[i] - 1)); pool[lab[i]].extend((x - means[i]) * k for x in cl[i])
    scale = math.sqrt(d / (d - mu * mu))
    return dict(dev=dev, pool=pool, H=H, lab=lab, scale=scale, tau2=tau2, V_df=den)


def proc_power(rng, c, g_e, delta, sims):
    lab = c["lab"]; base, extra = divmod(N_SEALED, g_e)
    ml = [base + (1 if j < extra else 0) for j in range(g_e)]
    # allocation: proportional to the stratum's clusters (G_e = G here, so the same counts)
    members = {h: [i for i in range(len(lab)) if lab[i] == h] for h in c["H"]}
    slots = [h for h in c["H"] for _ in members[h]]
    tq = t_q(0.95, g_e - 1); ok = 0
    for _ in range(sims):
        sums = []
        for j, h in enumerate(slots):
            i = rng.choice(members[h]); m = ml[j]
            sums.append(m * c["dev"][i] + sum(rng.choices(c["pool"][h], k=m)))
        ok += m5_pass(sums, ml, delta, tq, c["scale"])
    return ok / sims


def truth_random(rng, g, d, tau, delta, runs):
    base, extra = divmod(N_SEALED, g); ml = [base + (1 if j < extra else 0) for j in range(g)]
    tq = t_q(0.95, g - 1); ok = 0
    for _ in range(runs):
        sums = [cluster_sum(rng, clamp(rng.gauss(0, tau), d), d, m)[0] for m in ml]
        ok += m5_pass(sums, ml, delta, tq)
    return ok / runs


def truth_fixed(rng, mus, d, delta, runs):
    g = len(mus); c = fmean(mus); fx = [clamp(m - c, d) for m in mus]
    base, extra = divmod(N_SEALED, g); ml = [base + (1 if j < extra else 0) for j in range(g)]
    tq = t_q(0.95, g - 1); ok = 0
    for _ in range(runs):
        sums = [cluster_sum(rng, fx[j], d, ml[j])[0] for j in range(g)]
        ok += m5_pass(sums, ml, delta, tq)
    return ok / runs


SC = [  # name, strata sizes, d, tau
    ("G7_6strata_tau0", [2, 1, 1, 1, 1, 1], 0.3, 0.0),
    ("G7_6strata_tau05", [2, 1, 1, 1, 1, 1], 0.3, 0.05),
    ("G10_6strata_tau05", [2, 2, 2, 2, 1, 1], 0.3, 0.05),
]

if __name__ == "__main__":
    draws, sims, truth, seed, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    res = []
    for name, sizes, d, tau in SC:
        rng = random.Random(f"{seed}/{name}"); t0 = time.time()
        lab = strata_layout(sizes); g = len(lab)
        delta = (t_q(0.95, g - 1) + Z(0.8)) * math.sqrt(tau * tau / g + d / N_SEALED)
        kr = truth_random(rng, g, d, tau, delta, truth)
        rec, kf, t2 = [], [], []
        for _ in range(draws):
            cl, mus = m0_draw(rng, d, tau, lab)
            c = comps(cl, lab); t2.append(c["tau2"])
            rec.append(proc_power(rng, c, g, delta, sims))
            kf.append(truth_fixed(rng, mus, d, delta, 200))
        r = dict(name=name, strata=sizes, G=g, d=d, tau=tau, delta=delta, known_random=kr, known_random_se=math.sqrt(kr * (1 - kr) / truth),
                 recovered=fmean(rec), recovered_se=pstdev(rec) / math.sqrt(draws), recovered_sd=pstdev(rec),
                 known_fixed_mean=fmean(kf), share_tau2_zero=sum(1 for x in t2 if x == 0) / draws, V_df=c["V_df"],
                 draws=draws, sims=sims, seconds=time.time() - t0)
        res.append(r)
        print(f"{name}: G={g} V_df={c['V_df']} delta={delta:.4f} known(random lineages)={kr:.4f} recovered(9.4 as worded)={r['recovered']:.4f}(se {r['recovered_se']:.4f}, sd {r['recovered_sd']:.3f}) "
              f"known(fixed lineages, mean over draws)={r['known_fixed_mean']:.4f} tau2hat=0 in {r['share_tau2_zero']:.2f} {r['seconds']:.0f}s", flush=True)
        with open(out, "w") as fh: json.dump(res, fh, indent=1)
