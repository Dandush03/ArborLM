"""P10-S0: independent recomputation from the raw per-cell records (ADR-0020 rev 4 + addenda; ADR-0019 sections 8.1-8.4).

Auditor's own code. Imports nothing from studies/ or arborlm. Integer arithmetic on the recorded counts wherever a
threshold is compared, so that no float rounding decides a cell.

Usage: python3 -I recompute.py <run dir> <arm_selection.json> <P9-II results.json> <out.json>
"""
import json, math, sys, statistics, collections
from fractions import Fraction as Fr
from pathlib import Path

run, armsel_p, p9_p, out_p = map(Path, sys.argv[1:5])
CELLS = run / "cells"

# ----------------------------------------------------------------------------------------------- exact helpers
def binom_pmf(n, k, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def cp_lower(k, n, alpha=0.05):
    """One-sided (1-alpha) Clopper-Pearson lower bound: p with P(X >= k | n, p) = alpha; 0 if k = 0."""
    if n == 0:
        return None
    if k == 0:
        return 0.0
    if k == n:
        return alpha ** (1 / n)
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        tail = sum(binom_pmf(n, j, mid) for j in range(k, n + 1))
        if tail < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sign_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    m = min(b, c)
    s = sum(Fr(math.comb(n, j), 2 ** n) for j in range(m + 1))
    return float(min(Fr(1), 2 * s))


def chance_interval(n, level_tail):
    """Exact binomial central interval around 1/32: [lo, hi] with P(X < lo) <= tail and P(X > hi) <= tail."""
    p = Fr(1, 32)
    pm = [Fr(math.comb(n, k)) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)] if False else None
    if pm is None:  # float for large n
        pf = [math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(1 / 32) + (n - k) * math.log(31 / 32)) for k in range(n + 1)]
        pm = pf
    c = 0
    lo = 0
    for k in range(n + 1):
        if c + pm[k] > level_tail:
            lo = k
            break
        c += pm[k]
    c = 0
    hi = n
    for k in range(n, -1, -1):
        if c + pm[k] > level_tail:
            hi = k
            break
        c += pm[k]
    return [lo, hi]


def h2(e):
    return 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))


def info_bits(a_use):
    e = 1 - a_use
    return 5 - h2(e) - e * math.log2(31)


def median(xs):
    return statistics.median(xs) if xs else None


# ----------------------------------------------------------------------------------------------- load cells
def parse(name):
    block = name.split("-")[0]
    rest = name[len(block) + 1:]
    if block == "WX":
        rest = rest[3:]  # WX-WX-A5-D-...
    parts = rest.split("-")
    j = int(parts[-1][1:])
    d = int(parts[-2][1:])
    ct = parts[-3]
    arm = "-".join(parts[:-3])
    ct = {"2K4K": "2K/4K", "8K16K": "8K/16K", "8K4K": "8K/4K", "32K64K": "32K/64K"}[ct]
    if block == "WX":
        arm = "WX-" + arm
    return block, arm, ct, d, j


cells = {}
for cdir in sorted(CELLS.iterdir()):
    block, arm, ct, d, j = parse(cdir.name)
    t = json.loads((cdir / "train.json").read_text())
    ev = {}
    for e in sorted((cdir / "eval").glob("u*/eval.json")):
        r = json.loads(e.read_text())
        ev[r["update"]] = r
    diag = []
    dp = cdir / "diagnostics.jsonl"
    if dp.exists():
        with dp.open() as fh:
            for line in fh:
                r = json.loads(line)
                diag.append({k: r.get(k) for k in ("update", "distinct_top1", "largest_top1_count", "probe_accuracy", "phase", "probe_sites", "probe_facts")})
    cells[(block, arm, ct, d, j)] = {"name": cdir.name, "train": t, "eval": ev, "diag": diag}

CLASS_UPDATE = {"2K/4K": 8192, "8K/16K": 32768, "8K/4K": 32768, "32K/64K": 131072}
U = 8192

# ----------------------------------------------------------------------------------------------- plan conformance
plan_issues = []
for (block, arm, ct, d, j), c in cells.items():
    t = c["train"]
    exp_updates = {"2K/4K": 8192, "8K/16K": 32768, "8K/4K": 32768, "32K/64K": 131072}[ct]
    exp_facts = {"2K/4K": 2048, "8K/16K": 8192, "8K/4K": 8192, "32K/64K": 32768}[ct]
    exp_slots = {"2K/4K": 4096, "8K/16K": 16384, "8K/4K": 4096, "32K/64K": 65536}[ct]
    base = 200001 + 100 * (d - 1)
    if arm in ("A6", "A7") or block == "PR":
        exp_init = 2001
    elif ct == "8K/4K" or block == "WX":
        exp_init = 2001 if d % 2 == 1 else 2002
    else:
        exp_init = 2001 + j
    chk = {"run_updates": (t["run_updates"], exp_updates), "facts": (t["facts"], exp_facts), "slots": (t["slots"], exp_slots),
           "init_seed": (t["init_seed"], exp_init), "seed_set": (t["seed_set"], f"p10s0-draw-{d}"), "draw": (t["draw"], d),
           "status": (t["status"], "completed"), "exposure_min": (t.get("exposure_per_fact_min"), 512), "exposure_max": (t.get("exposure_per_fact_max"), 512),
           "hyper": (t["hyper"], {"k0_fraction": 0.125, "lambda": 1.0, "mu": 1.0, "u_pre": 2048.0}), "trainable_backbone": (t["trainable_backbone_parameters"], 0)}
    if t.get("target_seed") is not None:
        jj = exp_init - 2001
        off = {"2K/4K": 40, "8K/16K": 44, "32K/64K": 48}.get(ct)
        if off is not None:
            chk["target_seed"] = (t["target_seed"], base + off + jj)
    if arm in ("A2", "WX-A2"):
        chk["u_pre"] = (t["schedule"]["u_pre"], 2048 * exp_facts // 2048)
    exp_evals = [U, 32768] if ct in ("8K/16K", "8K/4K") else [exp_updates]
    chk["evals"] = (sorted(c["eval"]), exp_evals)
    if c["diag"]:
        ups = [r["update"] for r in c["diag"]]
        chk["diag_updates"] = (ups == list(range(64, exp_updates + 1, 64)), True)
    for k, (got, exp) in chk.items():
        if got != exp:
            plan_issues.append((c["name"], k, got, exp))
    if arm in ("A1", "A2") and ct == "8K/4K":
        plan_issues.append((c["name"], "A1/A2 at 8K/4K", True, False))

# matrix completeness
expected = set()
for d in range(1, 11):
    for ct in ("2K/4K", "8K/16K"):
        for arm in ("A0", "A1", "A2", "A5-D"):
            for j in (0, 1):
                expected.add(("Q1", arm, ct, d, j))
        for arm in ("A6", "A7"):
            expected.add(("Q1", arm, ct, d, 0))
    jj = 0 if d % 2 == 1 else 1
    for arm in ("A0", "A5-D"):
        expected.add(("Q1", arm, "8K/4K", d, jj))
    expected.add(("Q1", "A6", "8K/4K", d, 0))
    for ct in ("2K/4K", "8K/16K"):
        expected.add(("WX", "WX-A5-D", ct, d, jj))
for d in (11, 12, 13):
    expected.add(("PR", "A5-D", "32K/64K", d, 0))
    expected.add(("PR", "A6", "32K/64K", d, 0))
missing = sorted(expected - set(cells))
extra = sorted(set(cells) - expected)

# ----------------------------------------------------------------------------------------------- G2 intervals
TAIL = 0.001 / 8 / 2
g2 = {}
for n in (2048, 8192, 32768):
    g2[n] = chance_interval(n, TAIL)
g2_record_mismatch = []
for key, c in cells.items():
    for u, r in c["eval"].items():
        for pn in ("A", "B"):
            p = r["panels"][pn]
            if p["chance_interval"] != g2[p["facts"]]:
                g2_record_mismatch.append((c["name"], u, pn, p["chance_interval"], g2[p["facts"]]))
            uf = p.get("unseen_facts")
            if uf and uf not in g2:
                g2[uf] = chance_interval(uf, TAIL)


def inside(x, iv):
    return iv[0] <= x <= iv[1]


# ----------------------------------------------------------------------------------------------- per-cell conditions
def ref_cell(block, ct, d, u):
    """A6 on the same draw, cell type and readout (seed 2001). WX uses Q1's A6; the probe uses its own A6."""
    rb = "PR" if block == "PR" else "Q1"
    c = cells.get((rb, "A6", ct, d, 0))
    return None if c is None else c["eval"].get(u)


flag_mismatch = []


def conditions(key, u):
    block, arm, ct, d, j = key
    r = cells[key]["eval"][u]
    a6 = ref_cell(block, ct, d, u)
    floor = Fr(1, 2) if ct == "8K/4K" else Fr(9, 10)
    a6_ok = all(Fr(a6["panels"][pn]["correct"], a6["panels"][pn]["facts"]) >= floor for pn in ("A", "B"))
    res = {"evaluated": a6_ok}
    c1 = all(10 * r["panels"][pn]["correct"] >= 9 * a6["panels"][pn]["correct"] for pn in ("A", "B"))
    c2 = True
    for pn in ("A", "B"):
        p = r["panels"][pn]
        iv = g2[p["facts"]]
        pi, di = inside(p["permuted_correct"], iv), inside(p["disabled_correct"], iv)
        if pi != p["permuted_at_chance"] or di != p["disabled_at_chance"]:
            flag_mismatch.append((cells[key]["name"], u, pn, "c2 flags", pi, di, p["permuted_at_chance"], p["disabled_at_chance"]))
        c2 = c2 and pi and di
    pr = r["probe"]
    c3 = 2 * pr["distinct_top1"] >= pr["probe_facts"] and 50 * pr["largest_top1_count"] <= pr["probe_sites"]
    A = r["panels"]["A"]["correct"]
    c4_A = all(10 * r["secondary"][h]["correct"] >= 9 * A for h in ("H1", "H2"))
    # ADR-0019 8.3: "conditions 1, 2 and 4 on both Panels A and B" -> H1/H2 against Panel A and against Panel B
    c4 = c4_A and all(10 * r["secondary"][h]["correct"] >= 9 * r["panels"]["B"]["correct"] for h in ("H1", "H2"))
    res_c4_A = c4_A
    c5 = True
    for pn in ("A", "B"):
        p = r["panels"][pn]
        leak = not inside(p["unseen_correct"], g2[p["unseen_facts"]])
        if leak != p["leakage"]:
            flag_mismatch.append((cells[key]["name"], u, pn, "leakage", leak, p["leakage"]))
        c5 = c5 and not leak
    rs = r.get("read_swap")
    if rs is None:
        c6 = None
    else:
        c6 = all(100 * rs[pn]["a_use_count"] >= 95 * rs[pn]["correct"] for pn in ("A", "B"))
        for pn in ("A", "B"):
            if rs[pn]["correct"] != r["panels"][pn]["correct"]:
                flag_mismatch.append((cells[key]["name"], u, pn, "read_swap.correct != panel correct", rs[pn]["correct"], r["panels"][pn]["correct"]))
    res.update({1: c1, 2: c2, 3: c3, 4: c4, 5: c5, 6: c6})
    res["p9"] = c1 and c2 and c3 and c4 and c5
    res["p9_c4A"] = c1 and c2 and c3 and c4_A and c5
    res["s0_c4A"] = res["p9_c4A"] and bool(c6)
    res["s0"] = res["p9"] and bool(c6)
    res["failed"] = [k for k in (1, 2, 3, 4, 5, 6) if res[k] is False]
    # margins (for near-threshold reporting)
    m = {}
    m["c1"] = min(r["panels"][pn]["correct"] / a6["panels"][pn]["correct"] for pn in ("A", "B")) - 0.90
    m["c3_distinct"] = pr["distinct_top1"] - pr["probe_facts"] / 2
    m["c3_largest"] = 10 - pr["largest_top1_count"]
    m["c4"] = min(r["secondary"][h]["correct"] for h in ("H1", "H2")) / max(A, 1) - 0.90
    if rs:
        m["c6"] = min(rs[pn]["a_use_count"] / max(rs[pn]["correct"], 1) for pn in ("A", "B")) - 0.95
    res["margins"] = m
    # LM
    res["lm_r"] = r["language_modelling"]["relative_rise"]
    res["lm_r_a6"] = a6["language_modelling"]["relative_rise"]
    res["lm_flag"] = res["lm_r"] > res["lm_r_a6"] + 0.05
    # descriptive
    res["stability"] = r["panel_statistics"].get("address_stability")
    if rs:
        iA, iB = info_bits(rs["A"]["a_use"]), info_bits(rs["B"]["a_use"])
        res["i_raw_min"] = min(iA, iB)
        # 0 at or below the chance interval's upper end (ADR-0017 I_acc convention), per panel
        iA0 = 0.0 if r["panels"]["A"]["correct"] <= g2[r["panels"]["A"]["facts"]][1] else iA
        iB0 = 0.0 if r["panels"]["B"]["correct"] <= g2[r["panels"]["B"]["facts"]][1] else iB
        res["i_clip_min"] = min(iA0, iB0)
        res["i_rec_min"] = min(rs["A"]["information_bits"], rs["B"]["information_bits"])
    ps = r["panel_statistics"]
    if "target_top8_recall_A" in ps:
        res["recall8_min"] = min(ps["target_top8_recall_A"], ps["target_top8_recall_B"])
        res["recall8_mean"] = (ps["target_top8_recall_A"] + ps["target_top8_recall_B"]) / 2
    res["acc_mean"] = (r["panels"]["A"]["accuracy"] + r["panels"]["B"]["accuracy"]) / 2
    res["acc_A"], res["acc_B"] = r["panels"]["A"]["accuracy"], r["panels"]["B"]["accuracy"]
    if "answer_site_auc" in r:
        res["auc"] = r["answer_site_auc"]["auc"]
    return res


learned_q1 = [k for k in cells if k[0] == "Q1" and k[1] not in ("A6", "A7")]
cond = {}
for k in cells:
    if k[1] in ("A6", "A7"):
        continue
    for u in cells[k]["eval"]:
        cond[(k, u)] = conditions(k, u)


# ----------------------------------------------------------------------------------------------- dynamics
def dynamics(key):
    block, arm, ct, d, j = key
    dg = cells[key]["diag"]
    onset = next((r["update"] for r in dg if r["distinct_top1"] <= 32), None)
    def slot_ok(r):
        return 2 * r["distinct_top1"] >= r["probe_facts"] and 50 * r["largest_top1_count"] <= r["probe_sites"]
    escape = None
    if onset is not None:
        idx = next(i for i, r in enumerate(dg) if r["update"] == onset)
        for i in range(idx + 1, len(dg)):
            if all(slot_ok(r) for r in dg[i:]):
                escape = dg[i]["update"]
                break
    u = CLASS_UPDATE[ct]
    rr = cells[key]["eval"][u]["probe"]
    sep_readout = 2 * rr["distinct_top1"] >= rr["probe_facts"] and 50 * rr["largest_top1_count"] <= rr["probe_sites"]
    if onset is None:
        cat = "never collapsed and separated" if sep_readout else "never collapsed, not separated"
    else:
        cat = "collapsed and recovered" if escape is not None else "collapsed and not recovered"
    # sustained success
    a6 = ref_cell(block, ct, d, u)
    out = {"onset": onset, "escape": escape, "category": cat}
    for variant, a6acc in (("A", a6["panels"]["A"]["accuracy"]), ("mean", (a6["panels"]["A"]["accuracy"] + a6["panels"]["B"]["accuracy"]) / 2), ("min", min(a6["panels"]["A"]["accuracy"], a6["panels"]["B"]["accuracy"]))):
        line = 0.90 * a6acc
        first = next((i for i, r in enumerate(dg) if r["probe_accuracy"] >= line), None)
        if first is None:
            out[f"sus_{variant}"] = (False, False)
        else:
            sustained = all(r["probe_accuracy"] >= line - 0.05 for r in dg[first + 1:])
            out[f"sus_{variant}"] = (True, sustained)
    out["min_probe_after_first"] = None
    return out


dyn = {k: dynamics(k) for k in cells if k[1] not in ("A6", "A7")}


# ----------------------------------------------------------------------------------------------- classes
def klass(keys, u, crit, two_seed):
    """crit in {'s0','p9'}. keys: the cells of one arm and cell type. Returns the class dict."""
    by_draw = collections.defaultdict(list)
    for k in keys:
        by_draw[k[3]].append(k)
    n_cells = len(keys)
    draw_ne = [d for d, ks in by_draw.items() if not cond[(ks[0], u)]["evaluated"]]
    ev = [k for k in keys if cond[(k, u)]["evaluated"]]
    succ = [k for k in ev if cond[(k, u)][crit]]
    failed = len(ev) - len(succ)
    lmf = sum(1 for k in ev if cond[(k, u)]["lm_flag"])
    lm_reduced = lmf > 1
    d_ev = [d for d in by_draw if d not in draw_ne]
    d_succ = [d for d in d_ev if all(cond[(k, u)][crit] for k in by_draw[d])]
    both_failed = any(all(not cond[(k, u)][crit] for k in by_draw[d]) and len(by_draw[d]) == 2 for d in d_ev)
    twenty = n_cells == 20
    if len(draw_ne) > 1:
        cls = "NOT_EVALUATED"
    elif failed <= 1 and not lm_reduced and not (twenty and both_failed):
        cls = "RELIABLE"
    elif failed <= 1 and lm_reduced:
        cls = "UNRELIABLE (LM CAPABILITY REDUCED)"
    elif len(succ) >= (5 if twenty else 3):
        cls = "UNRELIABLE"
    else:
        cls = "FAILS"
    return {"cls": cls, "evaluated": len(ev), "successes": len(succ), "failures": failed, "draws_evaluated": len(d_ev),
            "draws_succeeded": len(d_succ), "draws_failed": len(d_ev) - len(d_succ), "per_draw_bound": cp_lower(len(d_succ), len(d_ev)),
            "lm_flagged_cells": lmf, "lm_reduced": lm_reduced, "draws_not_evaluated": len(draw_ne)}


armsel = json.loads(armsel_p.read_text())
p9 = json.loads(p9_p.read_text())["result"]
# independent read of P9-II's classes and draw counts from P9-II's results.json, compared with the arm-selection record
p9cls = {}
p9_check = []
for arm in ("A0", "A1", "A2", "A5-D"):
    for stage, size in (("stage1", "4096"), ("stage2", "16384")):
        a = p9[stage]["arms"].get(arm)
        if a is None:
            p9cls[(arm, size)] = None
        else:
            dc = a["draw_sensitivity"]["draw_counts"]
            p9cls[(arm, size)] = {"class": a["class"], "succ_draws": dc["2/2"], "draws": dc["0/2"] + dc["1/2"] + dc["2/2"], "failed": dc["0/2"] + dc["1/2"]}
        rec = armsel["p9ii_classes"][arm][size]
        mine = p9cls[(arm, size)]
        if mine is None:
            if rec["available"]:
                p9_check.append((arm, size, "available", rec["available"], False))
        else:
            for k1, k2 in (("class", "class"), ("failed", "failed_draws"), ("draws", "evaluated_draws")):
                if rec.get(k2) != mine[k1]:
                    p9_check.append((arm, size, k1, rec.get(k2), mine[k1]))
p9_lm = {}
for c in json.loads(p9_p.read_text())["classes"]:
    p9_lm[(c["arm"], str(c["slots"]), c["stage"])] = c["lm_flagged_cells"]

SIZE = {"2K/4K": "4096", "8K/16K": "16384"}
arms_out = {}
for arm in ("A0", "A1", "A2", "A5-D"):
    for ct in ("2K/4K", "8K/16K", "8K/4K"):
        keys = sorted(k for k in learned_q1 if k[1] == arm and k[2] == ct)
        if not keys:
            continue
        u = CLASS_UPDATE[ct]
        s0 = klass(keys, u, "s0", ct != "8K/4K")
        p9c = klass(keys, u, "p9", ct != "8K/4K")
        o = {"s0": s0, "p9_criteria": p9c, "cells": len(keys)}
        st = [cond[(k, u)]["stability"] for k in keys]
        o["stable_median"] = median(st)
        o["stable"] = o["stable_median"] >= 0.80
        o["collapse_free_k"] = sum(1 for k in keys if dyn[k]["onset"] is None)
        o["categories"] = dict(collections.Counter(dyn[k]["category"] for k in keys))
        o["i_raw_median"] = median([cond[(k, u)]["i_raw_min"] for k in keys])
        o["i_clip_median"] = median([cond[(k, u)]["i_clip_min"] for k in keys])
        o["i_rec_median"] = median([cond[(k, u)]["i_rec_min"] for k in keys])
        o["failed_conditions"] = {f"{k[3]}/{k[4]}": cond[(k, u)]["failed"] for k in keys if cond[(k, u)]["failed"]}
        for v in ("A", "mean", "min"):
            o[f"sustained_{v}"] = (sum(1 for k in keys if dyn[k][f"sus_{v}"][0]), sum(1 for k in keys if dyn[k][f"sus_{v}"][1]))
        if arm in ("A1", "A2"):
            o["recall_median_min"] = median([cond[(k, u)]["recall8_min"] for k in keys])
            o["recall_median_mean"] = median([cond[(k, u)]["recall8_mean"] for k in keys])
        if ct in ("8K/16K", "8K/4K"):
            o["class_at_U_s0"] = klass(keys, U, "s0", ct != "8K/4K")["cls"]
            o["class_at_U_p9"] = klass(keys, U, "p9", ct != "8K/4K")["cls"]
        # replication / consistency / pooled
        if ct in SIZE:
            P = p9cls[(arm, SIZE[ct])]
            o["p9ii_class"] = P["class"] if P else None
            if P is None:
                o["replication"] = "NOT COMPARABLE"
                o["consistency"] = "SINGLE-STUDY EVIDENCE"
                o["pooled"] = None
            else:
                rel_s0 = p9c["cls"] == "RELIABLE"
                rel_p9 = P["class"] == "RELIABLE"
                o["replication"] = "NOT COMPARABLE" if p9c["cls"] == "NOT_EVALUATED" or P["class"] == "NOT_EVALUATED" else ("REPLICATES P9-II" if rel_s0 == rel_p9 else "DOES NOT REPLICATE P9-II")
                stage = "stage1" if ct == "2K/4K" else "stage2"
                p9_lmred = p9_lm.get((arm, SIZE[ct], stage), 0) > 1
                pooled_failed = P["failed"] + p9c["draws_failed"]
                pooled_n = P["draws"] + p9c["draws_evaluated"]
                o["consistency"] = "CONSISTENT ACROSS STUDIES" if (not p9_lmred and pooled_failed <= 2) else "INCONSISTENT ACROSS STUDIES"
                ps = P["succ_draws"] + p9c["draws_succeeded"]
                o["pooled"] = {"successes": ps, "draws": pooled_n, "failed": pooled_failed, "p9_succ": P["succ_draws"], "p9_draws": P["draws"],
                               "bound": None if arm == "A5-D" else cp_lower(ps, pooled_n)}
            o["meets"] = s0["cls"] == "RELIABLE" and o["stable"]
        # dense comparison for RELIABLE arms
        if s0["cls"] == "RELIABLE" and ct in SIZE:
            ratios, diffs, a7acc, higher = [], {}, [], 0
            ratios_A = []
            for d in range(1, 11):
                a7 = cells[("Q1", "A7", ct, d, 0)]["eval"][u]
                a7m = (a7["panels"]["A"]["accuracy"] + a7["panels"]["B"]["accuracy"]) / 2
                xm = statistics.mean(cond[(k, u)]["acc_mean"] for k in keys if k[3] == d)
                ratios.append(xm / a7m)
                ratios_A.append(statistics.mean(cond[(k, u)]["acc_A"] for k in keys if k[3] == d) / a7["panels"]["A"]["accuracy"])
                diffs[d] = xm - a7m
                a7acc.append(a7m)
                higher += xm > a7m
            mr = median(ratios)
            o["dense"] = {"median_ratio": mr, "median_ratio_panelA": median(ratios_A), "median_dense_accuracy": median(a7acc), "draws_arm_higher": higher, "differences": diffs,
                          "label": "BEATS DENSE" if mr >= 1.10 else ("DENSE AT CEILING" if median(a7acc) > 0.909 else "DENSE SUFFICES")}
        arms_out[(arm, ct)] = o

# paired comparisons
paired = {}
def pair(x, y, ct, crit):
    u = CLASS_UPDATE[ct]
    b = c = 0
    xs = ys = 0
    for d in range(1, 11):
        for j in (0, 1):
            sx = cond[(("Q1", x, ct, d, j), u)][crit]
            sy = cond[(("Q1", y, ct, d, j), u)][crit]
            xs += sx; ys += sy
            b += sx and not sy
            c += sy and not sx
    dd = b - c
    lab = "IMPROVES ON A0" if dd >= 4 and xs > ys else ("HARMS" if dd <= -4 else "NOT DISTINGUISHED FROM A0")
    return {"d": dd, "x_only": b, "a0_only": c, "x_successes": xs, "a0_successes": ys, "p": sign_p(b, c), "label": lab}

for x in ("A1", "A2", "A5-D"):
    for ct in ("2K/4K", "8K/16K"):
        paired[(x, ct)] = {"s0": pair(x, "A0", ct, "s0"), "p9": pair(x, "A0", ct, "p9")}
paired_a2_a1 = {ct: pair("A2", "A1", ct, "s0") for ct in ("2K/4K", "8K/16K")}

# qualification
order = ["A0", "A5-D", "A2", "A1"]
def q_at(arm, ct):
    o = arms_out[(arm, ct)]
    return o["meets"] and o["consistency"] in ("CONSISTENT ACROSS STUDIES", "SINGLE-STUDY EVIDENCE")
candidate = next((a for a in order if q_at(a, "2K/4K") and q_at(a, "8K/16K")), None)
q4096 = None if candidate else next((a for a in order if q_at(a, "2K/4K")), None)
also = []
if candidate:
    for a in order[order.index(candidate) + 1:]:
        if q_at(a, "2K/4K") and q_at(a, "8K/16K"):
            also.append(f"{a} (4,096 AND 16,384)")
        elif q_at(a, "2K/4K"):
            also.append(f"{a} (4,096 ONLY)")
inconsistent_but_meets = [(a, ct) for a in order for ct in ("2K/4K", "8K/16K") if arms_out[(a, ct)]["meets"] and arms_out[(a, ct)]["consistency"] == "INCONSISTENT ACROSS STUDIES"]

# A6 / 2K/4K NOT_EVALUATED -> INCONCLUSIVE?
ne_2k = sum(1 for d in range(1, 11) if not cond[(("Q1", "A0", "2K/4K", d, 0), 8192)]["evaluated"])
if ne_2k > 1:
    outcome = (3, "INCONCLUSIVE")
elif candidate:
    outcome = (4, "ADDRESSING-QUALIFIED (4,096 AND 16,384)")
elif q4096:
    outcome = (5, "ADDRESSING-QUALIFIED AT 4,096 ONLY")
else:
    outcome = (6, "ADDRESSING-NOT-QUALIFIED")

# overload (A5-D at 8K/4K)
ov = arms_out[("A5-D", "8K/4K")]["s0"]["cls"]
overload = {"RELIABLE": "OVERLOAD-QUALIFIED", "NOT_EVALUATED": "OVERLOAD NOT_EVALUATED"}.get(ov, "OVERLOAD NOT QUALIFIED") if candidate in ("A5-D", "A0") else "OVERLOAD NOT RUN — NO TARGET INJECTION"

# WX
wx = {}
for ct in ("2K/4K", "8K/16K"):
    keys = sorted(k for k in cells if k[0] == "WX" and k[2] == ct)
    u = CLASS_UPDATE[ct]
    w = {"s0": klass(keys, u, "s0", False), "p9": klass(keys, u, "p9", False)}
    w["stable_median"] = median([cond[(k, u)]["stability"] for k in keys])
    w["stable"] = w["stable_median"] >= 0.80
    w["auc_median"] = median([cond[(k, u)]["auc"] for k in keys])
    w["i_clip_median"] = median([cond[(k, u)]["i_clip_min"] for k in keys])
    w["i_raw_median"] = median([cond[(k, u)]["i_raw_min"] for k in keys])
    w["i_rec_median"] = median([cond[(k, u)]["i_rec_min"] for k in keys])
    w["failed_conditions"] = {f"{k[3]}/{k[4]}": cond[(k, u)]["failed"] for k in keys if cond[(k, u)]["failed"]}
    w["collapse_free_k"] = sum(1 for k in keys if dyn[k]["onset"] is None)
    w["meets"] = w["s0"]["cls"] == "RELIABLE" and w["stable"]
    wx[ct] = w
if wx["2K/4K"]["meets"] and wx["8K/16K"]["meets"]:
    rl = "PASSES"
elif wx["2K/4K"]["meets"]:
    rl = "PASSES AT 4,096 ONLY"
else:
    rl = "DOES NOT PASS"

# probe
pk = sorted(k for k in cells if k[0] == "PR" and k[1] == "A5-D")
probe_ev = [cond[(k, 131072)]["evaluated"] for k in pk]
probe_k = sum(cond[(k, 131072)]["s0"] for k in pk)
probe_k_p9 = sum(cond[(k, 131072)]["p9"] for k in pk)

# hypotheses
def hread(arm):
    a, b = paired[(arm, "2K/4K")]["s0"]["label"], paired[(arm, "8K/16K")]["s0"]["label"]
    rel = arms_out[(arm, "2K/4K")]["s0"]["cls"] == "RELIABLE" and arms_out[(arm, "8K/16K")]["s0"]["cls"] == "RELIABLE"
    if "HARMS" in (a, b):
        return "CONTRADICTED"
    if rel and a == b == "IMPROVES ON A0":
        return "supported"
    return "not supported"
c2, c8 = arms_out[("A0", "2K/4K")]["s0"]["cls"], arms_out[("A0", "8K/16K")]["s0"]["cls"]
if c2 in ("UNRELIABLE", "FAILS", "UNRELIABLE (LM CAPABILITY REDUCED)") or c8 in ("UNRELIABLE", "FAILS", "UNRELIABLE (LM CAPABILITY REDUCED)"):
    h_a = "supported"
elif c2 == c8 == "RELIABLE":
    h_a = "not supported"
else:
    h_a = "not read"
hyp = {"H20-A": h_a, "H20-B": hread("A1"), "H20-C": hread("A2"), "H20-D": hread("A5-D"),
       "H20-Q": "supported" if outcome[0] == 4 else "not supported",
       "H20-O": {"OVERLOAD-QUALIFIED": "supported", "OVERLOAD NOT QUALIFIED": "not supported", "OVERLOAD NOT_EVALUATED": "not read"}.get(overload, "not tested"),
       "H20-L": "supported" if rl == "PASSES" else "not supported",
       "H20-S": "supported" if probe_k == 3 else ("contradicted" if probe_k == 0 and all(probe_ev) else "not supported")}
for arm in ("A0", "A1", "A2", "A5-D"):
    for ct in ("2K/4K", "8K/16K"):
        r = arms_out[(arm, ct)]["replication"]
        hyp[f"H20-R ({arm}, {ct})"] = {"REPLICATES P9-II": "supported", "DOES NOT REPLICATE P9-II": "not supported"}.get(r, "not read")
a0_fail_8k = 20 - arms_out[("A0", "8K/16K")]["s0"]["successes"]

# A6 per draw
a6tab = {}
for ct in ("2K/4K", "8K/16K", "8K/4K"):
    for d in range(1, 11):
        r = cells[("Q1", "A6", ct, d, 0)]["eval"][CLASS_UPDATE[ct]]
        fl = 0.5 if ct == "8K/4K" else 0.9
        a6tab[f"{ct}|{d}"] = {"A": r["panels"]["A"]["accuracy"], "B": r["panels"]["B"]["accuracy"], "evaluated": min(r["panels"]["A"]["accuracy"], r["panels"]["B"]["accuracy"]) >= fl, "lm_r": r["language_modelling"]["relative_rise"]}

def jkey(k):
    return "|".join(map(str, k))
out = {
    "plan_issues": plan_issues, "missing_cells": missing, "extra_cells": extra, "g2": {str(k): v for k, v in g2.items()},
    "g2_record_mismatch": g2_record_mismatch[:10], "g2_record_mismatch_count": len(g2_record_mismatch), "flag_mismatch": flag_mismatch,
    "p9ii_armsel_check": p9_check, "p9cls": {f"{a}|{s}": v for (a, s), v in p9cls.items()},
    "arms": {f"{a}|{ct}": v for (a, ct), v in arms_out.items()},
    "paired": {f"{a}|{ct}": v for (a, ct), v in paired.items()}, "paired_a2_a1": paired_a2_a1,
    "candidate": candidate, "qualified_4096_only": q4096, "also": also, "inconsistent_but_meets": inconsistent_but_meets,
    "outcome": outcome, "overload": overload, "wx": wx, "record_length": rl,
    "probe": {"k": probe_k, "k_p9": probe_k_p9, "n": len(pk), "a6_evaluated": probe_ev, "bound": cp_lower(probe_k, len(pk))},
    "hypotheses": hyp, "a0_failed_cells_8k16k": a0_fail_8k, "a6": a6tab,
    "cells": {jkey(k) + f"|u{u}": {kk: vv for kk, vv in v.items()} for (k, u), v in cond.items()},
    "dynamics": {jkey(k): v for k, v in dyn.items()},
}
Path(out_p).write_text(json.dumps(out, indent=1, default=str))
c4_diff = [(cells[k]["name"], u) for (k, u), v in cond.items() if v["s0"] != v["s0_c4A"] or v["p9"] != v["p9_c4A"]]
out["c4_reading_changes_success"] = c4_diff
Path(out_p).write_text(json.dumps(out, indent=1, default=str))
print("cells whose success depends on the condition-4 reading:", c4_diff)
print("cells loaded", len(cells), "missing", len(missing), "extra", len(extra), "plan issues", len(plan_issues))
print("g2", g2, "record mismatches", len(g2_record_mismatch), "flag mismatches", len(flag_mismatch))
print("p9ii arm-selection check mismatches", p9_check)
for (a, ct), o in arms_out.items():
    pooled = o.get("pooled")
    print(f"{a:5s} {ct:7s} S0 {o['s0']['cls']:11s} {o['s0']['successes']:2d}/{o['s0']['evaluated']} draws {o['s0']['draws_succeeded']}/{o['s0']['draws_evaluated']} b={o['s0']['per_draw_bound']:.3f} | P9crit {o['p9_criteria']['cls']:11s} {o['p9_criteria']['successes']:2d} draws {o['p9_criteria']['draws_succeeded']} | {o.get('replication')} | {o.get('consistency')} | pooled {pooled and (pooled['successes'], pooled['draws'], pooled['bound'])} | stable {o['stable_median']:.3f} | CF {o['collapse_free_k']} | i {o['i_clip_median']:.3f}/{o['i_raw_median']:.3f} | LMflag {o['s0']['lm_flagged_cells']}")
for k, v in paired.items():
    print(k, v["s0"]["d"], v["s0"]["label"], round(v["s0"]["p"], 4), "| p9", v["p9"]["d"], v["p9"]["label"])
print("A2 vs A1", {k: (v["d"], v["p"]) for k, v in paired_a2_a1.items()})
print("candidate", candidate, "q4096", q4096, "also", also, "outcome", outcome, "overload", overload, "record length", rl)
print("wx", {ct: (w["s0"]["cls"], w["s0"]["successes"], w["stable_median"], w["auc_median"], w["i_clip_median"]) for ct, w in wx.items()})
print("probe", out["probe"])
print("hyp", hyp)
