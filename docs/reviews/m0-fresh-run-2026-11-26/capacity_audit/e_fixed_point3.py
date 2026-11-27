"""Item 3: one round and the fixed point, written from section 4A stage 4 and section 10 part A, compared with
capacity.run_stage4 driven by a model of the draws (count_fn injection; no generator is run, no stream is drawn).

Model of a draw for (x, v): a list of distinct keys, key j reached at attempt a_j (a_j increasing), an optional give-up
attempt g, an optional solver-disagreement attempt d. For target T: stop at the first of a_T (if it exists), the budget
40T + 1000, the give-up g; keys = those with a_j <= stop (a_j < g for a give-up); disagreements = 1 if d <= stop.
Keys may be shared between sibling lineages (same bytes). Part 1 uses the demand constants scaled by 1/100
(4,000 -> 40, 20,000 -> 200, 100 -> 1), patched into capacity's module globals for the comparison; part 2 uses the
registered constants on hand-made zero-slack cases; part 3 checks the demand tables against the text."""
import bisect, hashlib, json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import SCR
from studies.m0.registration import capacity as cap

LEVELS = (0, 1, 2, 3, 4, 5, 6)


def cdiv(a, b):
    return -(-a // b)


def D(G, c):
    dev, pool, tun = c
    return 10 * (cdiv(dev, G) + cdiv(pool, G) + tun)


def Dlin(G, k, c):
    dev, pool, tun = c
    return 10 * (cdiv(cdiv(dev, G), k) + cdiv(cdiv(pool, G), k) + cdiv(tun, k))


class Model:
    def __init__(self):
        self.s = {}  # (x, v) -> dict(keys=[bytes], a=[int], g=int|None, d=int|None)

    def draw(self, x, v, T):
        m = self.s[(x, v)]
        budget = 40 * T + 1000
        a = m["a"]
        stop = budget
        ended = "budget"
        if len(a) >= T and a[T - 1] <= budget:
            stop, ended = a[T - 1], "target"
        if m["g"] is not None and m["g"] <= stop and not (ended == "target" and a[T - 1] < m["g"]):
            stop, ended = m["g"], "gave_up"
        if ended == "gave_up":
            n = bisect.bisect_left(a, stop)
        else:
            n = bisect.bisect_right(a, stop)
        n = min(n, T)
        dis = 1 if (m["d"] is not None and m["d"] <= stop) else 0
        return m["keys"][:n], ended, stop, dis


def mine(parts, model, c):
    """parts: {(e, p): {cluster: [lineages]}} -> {(e, p): (registered {cluster: sorted list}, [(G, failing sorted)])}."""
    out = {}
    for ep, start in parts.items():
        S = {cl: list(xs) for cl, xs in start.items() if xs}
        trail = []
        while S:
            G = len(S)
            fail = set()
            for cl, xs in S.items():
                t = Dlin(G, len(xs), c)
                dr = {(x, v): model.draw(x, v, t) for x in xs for v in LEVELS}
                own = {x for x in xs for v in LEVELS if len(dr[(x, v)][0]) < t}
                fail |= own
                if not own:
                    for v in LEVELS:
                        u = set()
                        for x in xs:
                            u.update(dr[(x, v)][0])
                        if len(u) < D(G, c):
                            fail |= set(xs)
                for x in xs:
                    if any(dr[(x, v)][3] for v in LEVELS):
                        fail.add(x)
            trail.append((G, sorted(fail)))
            if not fail:
                break
            S = {cl: [x for x in xs if x not in fail] for cl, xs in S.items()}
            S = {cl: xs for cl, xs in S.items() if xs}
        out[ep] = ({cl: sorted(xs) for cl, xs in S.items()}, trail)
    return out


def theirs(cands, partition, mp, model):
    def fn(x, v, T):
        keys, ended, stop, dis = model.draw(x, v, T)
        return cap.Draw(x, v, T, len(keys), ended, stop, b"".join(keys), True, dis, (), stop if dis else None)
    rec = cap.run_stage4(cands, partition, mp, None, count_fn=fn)
    out = {}
    for e, pp in rec["parts"].items():
        for p, r in pp.items():
            trail = [(rd["G"], rd["failing"]) for rd in r["rounds"] if rd["G"] > 0]
            out[(e, p)] = ({cl: sorted(xs) for cl, xs in r["registered"].items()}, trail)
    return out


def key(*a):
    return hashlib.sha256(repr(a).encode()).digest()[:16]


def random_case(rng, c, case_id):
    evs = ("R1", "R2", "M1", "C1")
    clusters, part_of, cand = {}, {}, {e: [] for e in evs}
    n_cl = rng.randint(1, 14)
    for i in range(n_cl):
        cl = f"K{case_id}_{i:02d}"
        mem = []
        for e in rng.sample(evs, rng.choice([1, 1, 1, 2, 3])):
            for j in range(rng.choice([1, 1, 2, 2, 3, 4, 5, 6])):
                x = f"{e}.c{case_id}_{i}_{j}"
                mem.append(x)
                if rng.random() < 0.9:
                    cand[e].append(x)
        if rng.random() < 0.3:
            mem.append(f"R1.noncand{case_id}_{i}")  # not a candidate
        clusters[cl] = mem
        part_of[cl] = rng.choice("AB")
    model = Model()
    Dmax = D(1, c)
    for cl, mem in clusters.items():
        for x in mem:
            for v in LEVELS:
                r = rng.random()
                if r < float(os.environ.get('P_AMPLE', '0.55')):
                    cap_n = Dmax + 5  # never binds
                else:
                    cap_n = rng.randint(0, Dmax)
                rate = rng.choice([1.0, 1.0, 1.0, 1.3, 20.0, 41.0, 45.0, 60.0])
                a = [math.ceil((j + 1) * rate) for j in range(cap_n)]
                base = int.from_bytes(key(x, v), "big") >> 24 << 24
                ks = [(base + j).to_bytes(16, "big") for j in range(cap_n)]
                model.s[(x, v)] = {"keys": ks, "a": a, "g": (rng.randint(1, 4 * Dmax) if rng.random() < 0.03 else None),
                                   "d": (rng.randint(1, 60 * Dmax) if rng.random() < 0.01 else None)}
        # sibling overlaps: the key at a random early position of x2 replaced by a key of x1 (zero-slack probe)
        same_e = {}
        for x in mem:
            same_e.setdefault(x.split(".")[0], []).append(x)
        for e, xs in same_e.items():
            if len(xs) >= 2 and rng.random() < 0.5:
                x1, x2 = rng.sample(xs, 2)
                for v in rng.sample(LEVELS, rng.randint(1, 3)):
                    k1, k2 = model.s[(x1, v)]["keys"], model.s[(x2, v)]["keys"]
                    n_sh = rng.choice([1, 1, 2, 5, 50, 400])
                    for _ in range(n_sh):
                        if k1 and k2:
                            src = k1[rng.randrange(min(len(k1), 300))]
                            pos = rng.randrange(min(len(k2), 300))
                            if src not in k2:
                                k2[pos] = src
    cands = {"candidates": {e: sorted(v) for e, v in cand.items()}}
    mp = {"clusters": [{"cluster_id": cl, "members": mem} for cl, mem in clusters.items()]}
    # only clusters with a candidate need a part, but giving every cluster a part is harmless
    partition = {"cluster_part": part_of}
    parts = {(e, p): {} for e in evs for p in "AB"}
    cl_of = {x: cl for cl, mem in clusters.items() for x in mem}
    for e in evs:
        for x in sorted(cand[e]):
            parts[(e, part_of[cl_of[x]])].setdefault(cl_of[x], []).append(x)
    return cands, partition, mp, parts, model


def main():
    res = {"random_cases": 0, "disagreements": [], "stats": {}}
    rng = random.Random(4002)
    scaled = (40, 200, 1)
    cap.DEV, cap.POOL, cap.TUNING = scaled
    rounds_hist, empty_parts, zero_slack_fail = {}, 0, 0
    N = int(os.environ.get("N_CASES", "3000"))
    for case in range(N):
        cands, partition, mp, parts, model = random_case(rng, scaled, case)
        a = mine(parts, model, scaled)
        b = theirs(cands, partition, mp, model)
        res["random_cases"] += 1
        for ep in a:
            if a[ep] != b[ep]:
                res["disagreements"].append({"case": case, "part": ep, "mine": repr(a[ep])[:400], "theirs": repr(b[ep])[:400]})
            nr = len(a[ep][1])
            rounds_hist[nr] = rounds_hist.get(nr, 0) + 1
            if parts[ep] and not a[ep][0]:
                empty_parts += 1
    res["stats"] = {"rounds_per_part_histogram": {str(k): v for k, v in sorted(rounds_hist.items())},
                    "parts_that_ended_empty": empty_parts}
    print("random cases", N, "disagreements", len(res["disagreements"]), res["stats"])

    # part 2: registered constants, hand-made zero-slack cases
    cap.DEV, cap.POOL, cap.TUNING = 4000, 20000, 100
    full = (4000, 20000, 100)
    hand = []
    def mk(G_clusters, k_first, shared, both_ok=True):
        """G clusters; the first has k_first lineages (all of R2) sharing `shared` keys at level 3; others 1 lineage, ample."""
        clusters, cand = {}, []
        model = Model()
        for i in range(G_clusters):
            k = k_first if i == 0 else 1
            mem = [f"R2.z{i}_{j}" for j in range(k)]
            clusters[f"Z{i:02d}"] = mem
            cand += mem
        G = G_clusters
        for cl, mem in clusters.items():
            t = Dlin(G, len(mem), full)
            for x in mem:
                for v in LEVELS:
                    n = t  # exactly the own demand
                    base = int.from_bytes(key(x, v), "big") >> 24 << 24
                    model.s[(x, v)] = {"keys": [(base + j).to_bytes(16, "big") for j in range(n)], "a": list(range(1, n + 1)), "g": None, "d": None}
        m0 = clusters["Z00"]
        if shared and len(m0) >= 2:
            k1, k2 = model.s[(m0[0], 3)]["keys"], model.s[(m0[1], 3)]["keys"]
            for j in range(shared):
                k2[j] = k1[j]
        cands = {"candidates": {"R2": sorted(cand)}}
        mp = {"clusters": [{"cluster_id": c, "members": m} for c, m in clusters.items()]}
        part = {"cluster_part": {c: "A" for c in clusters}}
        parts = {(e, p): {} for e in ("R1", "R2", "M1", "C1") for p in "AB"}
        parts[("R2", "A")] = {c: sorted(m) for c, m in clusters.items()}
        return cands, part, mp, parts, model
    for G, k, sh in [(10, 2, 0), (10, 2, 1), (10, 3, 1), (10, 3, 10), (4, 4, 1), (5, 5, 1), (16, 2, 1), (16, 8, 160), (16, 8, 161), (1, 2, 1), (1, 2, 0)]:
        cands, part, mp, parts, model = mk(G, k, sh)
        a = mine(parts, model, full); b = theirs(cands, part, mp, model)
        ok = a == b
        slack = k * Dlin(G, k, full) - D(G, full)
        first = a[("R2", "A")][1][0]
        hand.append({"G": G, "k": k, "shared_keys": sh, "slack": slack, "round1_failing": len(first[1]), "equal": ok})
        print("HAND", "AGREE" if ok else "DISAGREE", f"G={G} k={k} shared={sh} slack={slack} round1 failing={len(first[1])} trail={[(g, len(f)) for g, f in a[('R2','A')][1]]}")
        if not ok:
            res["disagreements"].append({"hand": [G, k, sh], "mine": repr(a)[:400], "theirs": repr(b)[:400]})
    res["hand"] = hand

    # part 3: demand tables
    tab = {g: D(g, full) for g in range(1, 20)}
    text = {1: 241000, 2: 121000, 3: 81010, 4: 61000, 5: 49000, 8: 31000, 9: 27680, 10: 25000, 11: 22830, 13: 19470, 14: 18150, 15: 17010, 19: 13640}
    lin_text = {(10, 2): 12500, (13, 3): 6500}
    chk = {"D": {str(g): [tab[g], v, tab[g] == v, cap.demand(g) == v] for g, v in text.items()},
           "D_lin": {f"{g},{k}": [Dlin(g, k, full), v, Dlin(g, k, full) == v, cap.demand_lin(g, k) == v] for (g, k), v in lin_text.items()}}
    allg = all(cap.demand(g) == D(g, full) for g in range(1, 400)) and all(cap.demand_lin(g, k) == Dlin(g, k, full) for g in range(1, 60) for k in range(1, 40))
    zero = {k: [g for g in range(1, 20) if k * Dlin(g, k, full) == D(g, full)] for k in range(2, 9)}
    maxslack = max((k * Dlin(g, k, full) - D(g, full), g, k) for g in range(1, 20) for k in range(2, 9))
    minslack = min(k * Dlin(g, k, full) - D(g, full) for g in range(1, 20) for k in range(2, 9))
    chk.update({"capacity_demand_equals_mine_G1_399_k1_39": allg, "zero_slack_G_by_k": {str(k): v for k, v in zero.items()},
                "max_slack_(slack,G,k)": maxslack, "min_slack": minslack})
    print(json.dumps(chk))
    res["demand_check"] = chk
    with open(f"{SCR}/deliver/e_fixed_point3.json", "x") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print("TOTAL DISAGREEMENTS", len(res["disagreements"]))


main()
