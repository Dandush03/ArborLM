"""Re-check of the predecessor's independent rule comparison (../c1_rules_independent.py), updated for the lead's rulings of ADR-0021 sections 22 and 22.1.

The predecessor's own helpers (Fano information, exact binomial interval, DEP, generators, step / arm / efficiency classes) are imported from c1 unchanged; the
rules that sections 22 / 22.1 changed are re-written here from the ruling text, NOT from studies/p10s1:
  (g)   DEP is read at every snapshot up to the run length of both cells;
  M5    a dense pair that is MC-SHORT or MC-AMBIGUOUS gives DENSE NOT ESTABLISHED AT MATCHED COMPUTE (<status>), never DENSE MATCHES / BEATS DENSE;
        DENSE AHEAD still takes precedence (any established reading); a positive arm with that label gives CAPACITY-POSITIVE [... DENSE COMPARISON NOT
        ESTABLISHED AT MATCHED COMPUTE] and the storage-half reading is not available to it;
  (h)   blocking labels (DENSE AHEAD, DENSE FASTER) count a replicate if EITHER panel satisfies; store-favouring labels need both panels;
  (k)m3 DENSE NOT READ and DENSE SPEED UNDECIDED never block EFFICIENCY-POSITIVE and are carried in its bracket;
  m13   a directed no-loaded transition gives CAPACITY NOT TESTED naming the transition;
  M1    study B tests the ratio of I_use = facts x i;
  M7    the dense-rate tie walk (22 and 22.1), including ties of three rates.
studies.p10s1.classes / calibrate are imported ONLY as the objects under test.

Run (worktree root): PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r1_rules_updated.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import itertools
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import c1_rules_independent as R  # noqa: E402  predecessor's own code (not the implementer's)

from studies.p10s1 import calibrate as CAL  # noqa: E402  object under test
from studies.p10s1 import classes as C  # noqa: E402  object under test

EPS = 1e-12
NE = "DENSE NOT ESTABLISHED AT MATCHED COMPUTE"
OUT = {}


# ---------------------------------------------------------------- (g) capacity verdict with DEP at every snapshot
def my_capacity_panel(S, L, mc, ref_ok, leak):
    if not ref_ok or leak:
        return "NOT_EVALUATED"
    up = S.u_p
    iS_run, _ = S.istar(S.run)
    iS_half, _ = S.istar(S.run // 2)
    iL_run, _ = L.istar(L.run)
    iL_half, _ = L.istar(L.run // 2)
    reads_S = {u for u in S.o if u <= S.run}
    reads_L = {u for u in L.o if u <= L.run}
    if any(R.my_dep(S.o[u]) is False for u in reads_S) or any(R.my_dep(L.o[u]) is False for u in reads_L):
        return "DEPENDENCE_FAILED"
    d_mu = L.i(up) - S.i(up)
    d_mc = (L.i(mc[1]) - S.i(mc[0])) if mc else None
    d_sat = L.i(up) - iS_run
    d_full = iL_run - iS_run
    plat_S = iS_run - iS_half <= 0.10 + EPS
    plat_L = iL_run - iL_half <= 0.10 + EPS
    loaded = plat_S and iS_run <= 4.0 + EPS
    g = 0.5 - EPS
    if S.i(up) >= 4.5 - EPS:
        return "CEILING"
    if d_mu >= g and d_mc is not None and d_mc >= g and d_sat >= g and loaded and d_sat - 2 * (iS_run - iS_half) >= g and L.a(up) >= 0.5 - EPS:
        return "CAPACITY"
    if d_mu >= g:
        return "GAIN WITHIN BUDGET ONLY"
    if d_mu <= -g and d_full <= -g:
        return "REVERSED"
    if d_mu <= -g:
        return "BEHIND WITHIN BUDGET"
    if abs(d_mu) < 0.25 - EPS and abs(d_full) < 0.25 - EPS and plat_S and plat_L:
        return "NULL" if loaded else "FLAT, NOT LOADED"
    return "UNRESOLVED"


def compare_capacity(trials=60000, seed=921511):
    rng = random.Random(seed)
    u_p = 8192
    mism, cov = [], Counter()
    dep_reads_mattered = 0
    for t in range(trials):
        run_s, run_l = rng.choice([(6 * u_p, 4 * u_p), (4 * u_p, 2 * u_p)])
        s = R.rand_series(rng, u_p, run_s, rng.choice(["low", "mid", "high", "any"]))
        l_ = R.rand_series(rng, u_p, run_l, rng.choice(["low", "mid", "high", "any"]))
        mc_ok = rng.random() < 0.85
        mc_u = rng.choice([u for u in s if u >= u_p]) if mc_ok else None
        mc = (mc_u, u_p) if mc_ok else None
        ref, leak = rng.random() > 0.03, rng.random() < 0.02
        mine = my_capacity_panel(R.Series(s, run_s, u_p), R.Series(l_, run_l, u_p), mc, ref, leak)
        old = R.my_capacity_panel(R.Series(s, run_s, u_p), R.Series(l_, run_l, u_p), mc, ref, leak)
        dep_reads_mattered += mine != old
        entry = C.McEntry("OK", mc_u, u_p, 1.5, "small") if mc_ok else C.McEntry(C.MC_SHORT, None, None, 9.0, None)
        theirs = C.capacity_panel(R.to_view(s, run_s, u_p), R.to_view(l_, run_l, u_p), entry, ref_ok=ref, leakage=leak).verdict
        cov[mine] += 1
        if mine != theirs:
            mism.append((t, mine, theirs))
    return {"trials": trials, "mismatches": len(mism), "first_mismatches": mism[:10], "coverage": dict(cov), "cases_where_the_ruling_g_changed_the_verdict_vs_old_reads": dep_reads_mattered}


# ---------------------------------------------------------------- M5 + (h) dense label
def my_dense(cells):
    """cells: list of (reps, status); rep: reading -> panel -> (d, r). AHEAD: d <= -0.25 on EITHER panel in >= 4 reps, in any established reading, at any cell."""
    ahead = False
    statuses = []
    for reps, status in cells:
        readings = ("MU", "MC", "D-BEST") if status == "OK" else ("MU", "D-BEST")
        if status != "OK":
            statuses.append(status)
        for rd in readings:
            n = sum(any(rep[rd][p][0] <= -0.25 + EPS for p in "AB") for rep in reps)
            ahead = ahead or n >= 4
    if ahead:
        return "DENSE AHEAD"
    if statuses:
        return f"{NE} ({', '.join(dict.fromkeys(statuses))})"
    beats = all((rep[rd][p][1] is None or rep[rd][p][1] >= 1.10 - EPS) for reps, _ in cells for rep in reps for rd in ("MU", "MC") for p in "AB")
    return "BEATS DENSE" if beats else "DENSE MATCHES"


def compare_dense(trials=30000, seed=921512, favourable=False):
    rng = random.Random(seed)
    mism, cov, matches_with_short = [], Counter(), 0
    for _ in range(trials):
        cells = []
        for _c in range(rng.choice([1, 2])):
            status = rng.choice(["OK", "OK", "MC-SHORT", "MC-AMBIGUOUS"])
            reps = []
            for _r in range(5):
                rep = {}
                for rd in ("MU", "MC", "D-BEST"):
                    if favourable:  # second pass (added after the first run showed no BEATS DENSE coverage): mostly d > 0 and r >= 1.10
                        rep[rd] = {p: (rng.choice([rng.uniform(0.0, 2.0), 1.0, -0.26]) if rng.random() < 0.3 else 1.0, None if rng.random() < 0.03 else rng.choice([1.10, 1.09, 2.0, 3.0, 1.5]), 0.5) for p in "AB"}
                    else:
                        rep[rd] = {p: (rng.choice([rng.uniform(-1, 1), -0.25, -0.26, -0.24, 2.0]), None if rng.random() < 0.03 else rng.choice([rng.uniform(0.8, 1.5), 1.10, 1.09, 3.0]), 0.5) for p in "AB"}
                if status != "OK":
                    rep["MC"] = {p: (-9.0, 0.01, 0.5) for p in "AB"}  # garbage MC numbers: must be ignored where MC is not established
                reps.append(rep)
            cells.append((reps, status))
        mine = my_dense(cells)
        th = C.dense_label([C.DenseCell(f"S{k}", reps, status) for k, (reps, status) in enumerate(cells)])["label"]
        th_n = "BEATS DENSE" if th.startswith("BEATS DENSE") else th
        cov[mine.split(" (")[0]] += 1
        if any(s != "OK" for _, s in cells) and th_n in ("DENSE MATCHES", "BEATS DENSE"):
            matches_with_short += 1
        if mine != th_n:
            mism.append((mine, th))
    return {"trials": trials, "mismatches": len(mism), "first": mism[:5], "coverage": dict(cov), "DENSE_MATCHES_or_BEATS_with_a_not_established_pair": matches_with_short}


# ---------------------------------------------------------------- M5 outcome, bracket, storage-half reading; m13
def my_outcome(arms, eng, inc, directed=()):
    if eng:
        return "S1-ENGINEERING-FAILURE"
    if inc:
        return "S1-INCOMPLETE"
    sup = [a for a in ("F-OQ", "T-OQ", "F-OQ-IVF") if arms[a][0] == "CAPACITY_SUPPORTED"]
    if any(arms[a][1] not in ("DENSE AHEAD", "DENSE NOT READ") for a in sup):
        return "CAPACITY-POSITIVE"
    if arms["F-OQ"][0] == "CAPACITY_NOT_SUPPORTED" and arms["T-OQ"][0] == "CAPACITY_NOT_SUPPORTED":
        return "CAPACITY-NEGATIVE"
    if sup and all(arms[a][1] == "DENSE AHEAD" for a in sup):
        return "CAPACITY-NEGATIVE"
    if directed:
        return "CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET"
    return "CAPACITY-INCONCLUSIVE"


def compare_outcome():
    classes = ["NOT_EVALUATED", "DEPENDENCE_FAILED", "CAPACITY_SUPPORTED", "CAPACITY_ONE_TRANSITION", "NOT_TESTED_BY_LOAD", "CAPACITY_NOT_SUPPORTED", "INTERMEDIATE"]
    dense = ["DENSE AHEAD", "BEATS DENSE", "DENSE MATCHES", "DENSE NOT READ", f"{NE} (MC-SHORT)", f"{NE} (MC-AMBIGUOUS)"]
    works = ["SUBLINEAR", "LINEAR KEY SCORING"]
    mism, cov = [], Counter()
    bracket_missing = bracket_wrong = storage_half_with_ne = storage_half_missing = neg_on_unevaluated = not_tested_unnamed = 0
    for cf, ct, ci in itertools.product(classes, repeat=3):
        for df, dt, di in itertools.product(dense, repeat=3):
            arms = {"F-OQ": (cf, df), "T-OQ": (ct, dt), "F-OQ-IVF": (ci, di)}
            objs = {a: C.ArmCapacity(a, c, d) for a, (c, d) in arms.items()}
            for eng, inc, directed in ((False, False, ()), (True, False, ()), (False, True, ()), (False, False, ("16K→64K",))):
                m = my_outcome(arms, eng, inc, directed)
                th = C.capacity_outcome(objs, engineering_failed=eng, incomplete=inc, directed_transitions=directed)
                cov[m] += 1
                if m != th.label.split(" (")[0] and not (m.startswith("CAPACITY NOT TESTED") and th.label.startswith("CAPACITY NOT TESTED")):
                    mism.append((arms, eng, inc, directed, m, th.label))
                if m.startswith("CAPACITY NOT TESTED") and directed and directed[0] not in th.printed:
                    not_tested_unnamed += 1
                if m == "CAPACITY-POSITIVE":
                    pos = [a for a in ("F-OQ", "T-OQ", "F-OQ-IVF") if arms[a][0] == "CAPACITY_SUPPORTED" and arms[a][1] not in ("DENSE AHEAD", "DENSE NOT READ")]
                    need = any(arms[a][1].startswith(NE) for a in pos)
                    has = th.printed.rstrip().endswith("DENSE COMPARISON NOT ESTABLISHED AT MATCHED COMPUTE]")
                    bracket_missing += need and not has
                    bracket_wrong += (not need) and ("DENSE COMPARISON NOT ESTABLISHED" in th.printed)
                    for wk in itertools.product(works, repeat=2):
                        work = {"T-OQ": wk[0], "F-OQ-IVF": wk[1], "F-OQ": "LINEAR KEY SCORING"}
                        reading = C.milestone_reading(th, objs, work, "TREE_COMPETITIVE", "S0 NOT YET DECIDED")
                        # ADR 8.7 + 22 M5: storage half only for a SUBLINEAR positive arm (T-OQ, F-OQ-IVF) not DENSE AHEAD whose dense comparison is established
                        eligible = [a for a in ("T-OQ", "F-OQ-IVF") if a in pos and work[a] == "SUBLINEAR" and not arms[a][1].startswith(NE)]
                        sh = reading.startswith("Storage half supported")
                        storage_half_with_ne += sh and not eligible
                        storage_half_missing += (not sh) and bool(eligible)
                if not eng and not inc and not directed and all(x[0] in ("NOT_EVALUATED", "DEPENDENCE_FAILED", "NOT_TESTED_BY_LOAD", "CAPACITY_ONE_TRANSITION", "INTERMEDIATE") for x in (arms["F-OQ"], arms["T-OQ"])) and th.label == C.CAPACITY_NEGATIVE and not any(arms[a][0] == "CAPACITY_SUPPORTED" for a in arms):
                    neg_on_unevaluated += 1
    return {"cases": sum(cov.values()), "mismatches": len(mism), "first": [str(x) for x in mism[:5]], "coverage": dict(cov), "bracket_missing": bracket_missing, "bracket_where_not_needed": bracket_wrong,
            "storage_half_printed_without_an_established_eligible_arm": storage_half_with_ne, "storage_half_missing_where_eligible": storage_half_missing,
            "negative_with_F-OQ_and_T-OQ_unevaluated_and_none_supported": neg_on_unevaluated, "not_tested_without_naming_the_transition": not_tested_unnamed}


# ---------------------------------------------------------------- (h) + m3 dense faster; efficiency outcome
def my_dense_faster(arm_ut, dense_ut, ca, cd):
    """arm_ut[rep][panel] = (kind, lo, hi). DENSE FASTER: c_T(D-OQ) <= 0.8 c_T(arm) in both measures for every value the bounds allow, in >= 4 reps, a rep counting if
    either panel satisfies it. UNDECIDED: not that, but possible for some value in >= 4 reps. Same panel paired."""
    if any(d is None for d in dense_ut):
        return "DENSE NOT READ"
    sure = possible = 0
    for a, d in zip(arm_ut, dense_ut):
        s = any(all(dp[2] * cd[m] <= 0.8 * ap[1] * ca[m] + EPS for m in ("cpu", "madds")) for ap, dp in zip(a, d))
        p = any(all(dp[1] * cd[m] <= 0.8 * ap[2] * ca[m] + EPS for m in ("cpu", "madds")) for ap, dp in zip(a, d))
        sure += s
        possible += p
    if sure >= 4:
        return "DENSE FASTER"
    if possible >= 4:
        return "DENSE SPEED UNDECIDED"
    return "DENSE NOT FASTER"


def rand_ut(rng, run):
    k = rng.choice(["exact", "exact", "left", "right"])
    if k == "exact":
        v = rng.choice([rng.uniform(300, run), 1024.0, 2048.0, 4096.0])
        return ("exact", v, v)
    if k == "left":
        return ("left", 0.0, float(rng.choice([512, 1024, 2048])))
    return ("right", float(run), math.inf)


def compare_dense_faster(trials=40000, seed=921513):
    rng = random.Random(seed)
    mism, cov = [], Counter()
    for _ in range(trials):
        run = rng.choice([16384, 32768])
        arm = [[rand_ut(rng, run) for _p in "AB"] for _r in range(5)]
        dense = [[rand_ut(rng, run) for _p in "AB"] for _r in range(5)] if rng.random() > 0.05 else [None] * 5
        ca = {"cpu": rng.uniform(0.01, 0.05), "madds": rng.uniform(5e7, 2e8)}
        cd = {"cpu": ca["cpu"] * rng.uniform(0.3, 4), "madds": ca["madds"] * rng.uniform(0.3, 4)}
        mine = my_dense_faster(arm, dense, ca, cd)
        th = C.dense_faster([[C.UT(*x) for x in r] for r in arm], [None if r is None else [C.UT(*x) for x in r] for r in dense], ca, cd)
        cov[mine] += 1
        if mine != th:
            mism.append((mine, th))
    # efficiency outcome: neither DENSE NOT READ nor DENSE SPEED UNDECIDED blocks; both carried in the bracket
    arms = ["EFFICIENCY_SUPPORTED", "EFFICIENCY_NOT_SUPPORTED", "INTERMEDIATE", "EFFICIENCY_ONE_TRANSITION", "NOT_EVALUATED", "DEPENDENCE_FAILED"]
    dl = ["DENSE FASTER", "DENSE NOT FASTER", "DENSE NOT READ", "DENSE SPEED UNDECIDED"]
    em, carried = 0, 0
    for cf, ct, df, dt in itertools.product(arms, arms, dl, dl):
        cls, d = {"F-OQ": cf, "T-OQ": ct}, {"F-OQ": df, "T-OQ": dt}
        a = R.my_eff_outcome(cls, d)
        b = C.efficiency_outcome(cls, d, engineering_failed=False, incomplete=False)
        em += a != b.label
        if b.label == "EFFICIENCY-POSITIVE":
            for arm in ("F-OQ", "T-OQ"):
                if cls[arm] == "EFFICIENCY_SUPPORTED" and d[arm] in ("DENSE NOT READ", "DENSE SPEED UNDECIDED") and d[arm] not in b.printed:
                    carried += 1
    return {"trials": trials, "mismatches": len(mism), "first": mism[:5], "coverage": dict(cov), "efficiency_outcome_mismatches": em, "positive_without_the_label_in_its_bracket": carried}


# ---------------------------------------------------------------- M1 study B with I_use
def my_study_b(per_rep, sublinear, attributed, facts=((2048, 8192), (8192, 32768))):
    """per_rep[r][reading][panel] = list of 2 (a_s, a_l, i_s, i_l) or None. Own rule from ADR 8.6 with I_use = F x i."""
    scale = sublinear and all(attributed)
    for rep in per_rep:
        for rd in ("MU", "MC"):
            for p in "AB":
                for k, st in enumerate(rep[rd][p]):
                    if st is None:
                        scale = False
                        continue
                    a_s, a_l, i_s, i_l = st
                    if a_s < 0.85 - EPS or a_l < 0.85 - EPS:
                        scale = False
                    if a_s < 0.5 - EPS or a_l < 0.5 - EPS:
                        scale = False
                        continue
                    f_s, f_l = facts[k]
                    if not (i_s > 0 and (f_l * i_l) / (f_s * i_s) >= 3.0 - EPS):
                        scale = False
    if scale:
        return "KNOWLEDGE SCALES WITH MEMORY"
    below = sum(1 for rep in per_rep if (vals := [rep[rd][p][1][1] for rd in ("MU", "MC") for p in "AB" if rep[rd][p][1] is not None]) and all(v < 0.5 - EPS for v in vals))
    return "KNOWLEDGE DOES NOT SCALE" if below >= 4 else "NOT ESTABLISHED"


def compare_study_b(trials=20000, seed=921514, favourable=False):
    rng = random.Random(seed)
    mism, cov = [], Counter()
    facts = ((2048, 8192), (8192, 32768))
    for _ in range(trials):
        top = rng.choice([0.3, 0.6, 0.86, 0.99, 1.0])
        regime_s, regime_l = rng.choice([1.0, 0.99, 0.95, 0.9]), rng.choice([1.0, 0.99, 0.95, 0.86])
        reps = []
        for _r in range(5):
            rep = {}
            for rd in ("MU", "MC"):
                rep[rd] = {}
                for p in "AB":
                    steps = []
                    for k in range(2):
                        if rd == "MC" and rng.random() < 0.05:
                            steps.append(None)
                            continue
                        if favourable:  # second pass (added after the first run showed no SCALES coverage): a_use near 1 with ratios around the 3.0 boundary
                            # (second edit, after the favourable pass still gave no SCALES: per-value dips made 'all 40 values >= 0.85' too rare)
                            # (third edit: 0.66 in the choice list and I_use ratios below 3 near a_use 0.86 still blocked every trial; a per-trial regime now)
                            a_s = regime_s if rng.random() > 0.01 else rng.choice([0.84, 0.6])
                            a_l = regime_l if rng.random() > 0.01 else rng.choice([0.84, 0.6, 0.86])
                        else:
                            a_s = min(1.0, max(0.0, top + rng.uniform(-0.1, 0.02)))
                            a_l = min(1.0, max(0.0, top + rng.uniform(-0.2, 0.02)))
                        i_s, i_l = R.fano(a_s) if a_s > 0.05 else 0.0, R.fano(a_l) if a_l > 0.05 else 0.0
                        steps.append((a_s, a_l, facts[k][0] * i_s, facts[k][1] * i_l))  # the implementation receives I_use (analysis.py passes facts x i)
                    rep[rd][p] = steps
            reps.append(rep)
        sub, att = (rng.random() < 0.9, [rng.random() < 0.9, rng.random() < 0.9]) if not favourable else (rng.random() < 0.97, [rng.random() < 0.97, rng.random() < 0.97])
        # own rule receives the per-fact i and multiplies by the facts itself
        mine_in = [{rd: {p: [None if st is None else (st[0], st[1], st[2] / facts[k][0], st[3] / facts[k][1]) for k, st in enumerate(rep[rd][p])] for p in "AB"} for rd in ("MU", "MC")} for rep in reps]
        mine = my_study_b(mine_in, sub, att)
        th = C.study_b_label(reps, sub, att)["label"]
        cov[mine] += 1
        if mine != th:
            mism.append((mine, th))
    a = 0.99
    i = R.fano(a)
    steps = [(a, a, 2048 * i, 8192 * i), (a, a, 8192 * i, 32768 * i)]
    rep = {"MU": {"A": steps, "B": steps}, "MC": {"A": steps, "B": steps}}
    prior_case = C.study_b_label([rep] * 5, True, [True, True])["label"]
    return {"trials": trials, "mismatches": len(mism), "first": mism[:5], "coverage": dict(cov), "predecessor_M1_case_a_use_0.99_everywhere": prior_case}


# ---------------------------------------------------------------- M7 tie walk (own code, integer thousandths to avoid float boundary noise)
def my_tie(minacc_k, traj_k, unit=8192):
    """minacc_k: rate -> thousandths; traj_k: rate -> {u: thousandths}."""
    best = max(minacc_k.values())
    cont = sorted(r for r, a in minacc_k.items() if best - a < 20)
    if len(cont) == 1:
        return cont[0], "U_P"
    for u in (unit // 2, unit // 4, unit // 8, unit // 16):
        top = max(traj_k[r][u] for r in cont)
        cont = sorted(r for r in cont if top - traj_k[r][u] < 20)
        if len(cont) == 1:
            return cont[0], u
    return min(cont), "smaller rate"


def compare_tie(trials=50000, seed=921515):
    rng = random.Random(seed)
    unit = 8192
    snaps = (unit // 2, unit // 4, unit // 8, unit // 16)
    rates = (0.001, 0.003, 0.01)
    mism, cov, nway = [], Counter(), Counter()
    for _ in range(trials):
        base = rng.randint(300, 980)
        minacc = {r: base + rng.choice([0, 5, 10, 15, 19, 20, 21, 25, 40, -5, -15, -19, -20]) for r in rates}
        traj = {r: {u: rng.choice([base - 300 + rng.choice([0, 5, 10, 19, 20, 21, 30])]) for u in snaps} for r in rates}
        mine = my_tie(minacc, traj, unit)
        best = max(minacc.values())
        nway[sum(1 for v in minacc.values() if best - v < 20)] += 1
        try:
            th = CAL.select_dense_rate({r: v / 1000 for r, v in minacc.items()}, {r: {u: v / 1000 for u, v in t.items()} for r, t in traj.items()}, unit)
            th_rate = th["rate"]
        except CAL.TieNeedsLead as exc:
            th_rate = f"TieNeedsLead: {exc}"
        cov[str(mine[1])] += 1
        if mine[0] != th_rate:
            mism.append((minacc, traj, mine, th_rate))
    return {"trials": trials, "mismatches": len(mism), "first": [str(x) for x in mism[:5]], "decided_at": dict(cov), "contenders_at_U_P": dict(nway)}


def main():
    OUT["capacity_panel"] = compare_capacity()
    OUT["dense_label"] = compare_dense()
    OUT["dense_label_favourable_pass"] = compare_dense(30000, 921516, favourable=True)
    OUT["outcome"] = compare_outcome()
    OUT["dense_faster_and_efficiency_outcome"] = compare_dense_faster()
    OUT["study_b"] = compare_study_b()
    OUT["study_b_favourable_pass"] = compare_study_b(20000, 921517, favourable=True)
    OUT["tie_walk"] = compare_tie()
    # unchanged rules re-run from the predecessor's code against the current classes.py
    OUT["unchanged"] = {"step_class": R.compare_step_class(), "arm_class": R.compare_arm_class(), "efficiency": R.compare_efficiency(), "efficiency_classes": R.compare_eff_classes()}
    json.dump(OUT, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
