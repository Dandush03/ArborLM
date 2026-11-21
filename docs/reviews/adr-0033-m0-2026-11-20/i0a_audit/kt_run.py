# ruff: noqa
# ruff: noqa
"""M0-I0a audit: six-scenario known-truth recomputation (independent; standard library only).

Usage: python3 -I kt_run.py SCEN[,SCEN...] DRAWS SIMS TRUTH_RUNS SEED OUT.json
For each scenario: known power by fresh clusters; recovered = mean over DRAWS synthetic M0
draws of the section-9.4 procedure as worded; ORACLE = same draws, same procedure, with the
true tau^2 plugged in (diagnostic); plus the distribution of tau-hat^2 (raw and truncated).
"""
import json, math, random, sys, time
from statistics import fmean, pstdev
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from kt_lib import known_power, m0_draw, components, procedure_power, sizes_of

SCEN = {  # name: (d, tau, sizes, delta)  -- Review 3 / config [knowntruth]
    "S1": (0.30, 0.05, "bal5", 0.020),
    "S2": (0.30, 0.00, "bal5", 0.018),
    "S3": (0.30, 0.05, "unbal", 0.020),
    "S4": (0.02, 0.01, "bal5", 0.004),
    "S5": (0.50, 0.05, "bal5", 0.025),
    "S6": (0.30, 0.00, "unbal", 0.018),
}
G, N_ITEMS = 300, 6000


def run(name, draws, sims, truth_runs, seed, oracle=False):
    d, tau, kind, delta = SCEN[name]
    rng = random.Random(f"{seed}/{name}")
    t0 = time.time()
    kp = known_power(rng, G, N_ITEMS, d, tau, delta, truth_runs)
    rec, orc, t2, raw = [], [], [], []
    for _ in range(draws):
        m0 = m0_draw(rng, d, tau, sizes_of(kind, G))
        c = components(m0)
        t2.append(c["tau2"]); raw.append(c["raw_tau2"])
        rec.append(procedure_power(rng, c, N_ITEMS, G, delta, sims))
        if oracle:
            co = components(m0, tau2_override=tau * tau)
            orc.append(procedure_power(rng, co, N_ITEMS, G, delta, sims))
    r = dict(name=name, d=d, tau=tau, sizes=kind, delta=delta, draws=draws, sims=sims, truth_runs=truth_runs,
             known=kp, known_se=math.sqrt(kp * (1 - kp) / truth_runs),
             recovered=fmean(rec), recovered_se=pstdev(rec) / math.sqrt(draws), draw_sd=pstdev(rec),
             draw_min=min(rec), draw_max=max(rec),
             oracle=fmean(orc) if orc else None, oracle_se=(pstdev(orc) / math.sqrt(draws)) if orc else None,
             tau2_true=tau * tau, tau2hat_mean=fmean(t2), raw_tau2_mean=fmean(raw), share_truncated=sum(1 for x in raw if x <= 0) / draws,
             tau2hat_q=[sorted(t2)[int(q * (draws - 1))] for q in (0.05, 0.25, 0.5, 0.75, 0.95)],
             tauhat_mean=fmean(math.sqrt(x) for x in t2), seconds=time.time() - t0)
    r["diff"] = r["recovered"] - r["known"]
    r["oracle_diff"] = (r["oracle"] - r["known"]) if orc else None
    return r


if __name__ == "__main__":
    names, draws, sims, truth, seed, out = sys.argv[1].split(","), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    oracle = len(sys.argv) > 7 and sys.argv[7] == "oracle"
    res = []
    for nm in names:
        r = run(nm, draws, sims, truth, seed, oracle)
        res.append(r)
        print(f"{nm}: known={r['known']:.4f}(se {r['known_se']:.4f}) recovered={r['recovered']:.4f}(se {r['recovered_se']:.4f}, draws {r['draw_min']:.3f}-{r['draw_max']:.3f}) "
              f"diff={r['diff']:+.4f} oracle={r['oracle']} oracle_se={r['oracle_se']} oracle_diff={r['oracle_diff']} "
              f"tau2 true={r['tau2_true']:.5f} tau2hat mean={r['tau2hat_mean']:.5f} raw mean={r['raw_tau2_mean']:.5f} trunc={r['share_truncated']:.2f} "
              f"q={[round(x,5) for x in r['tau2hat_q']]} {r['seconds']:.0f}s", flush=True)
        with open(out, "w") as fh:
            json.dump(res, fh, indent=1)
