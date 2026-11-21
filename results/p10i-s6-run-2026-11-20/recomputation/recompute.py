"""Independent recomputation of the P10-I-S6 registered outcome (ADR-0031 + addenda 1 and 2).

Written by the auditor from the specification text. Imports nothing from studies/ or arborlm/.
Reads only JSON records of the run directory and the frozen plan / rate table of the freeze commit.
Writes only into this audit folder (recompute_out.json).

Run:  python3 -I recompute.py <run_dir> <worktree>
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(sys.argv[1])
WT = Path(sys.argv[2])
OUT = Path(__file__).resolve().parent / "recompute_out.json"

# ---- thresholds, copied by hand from ADR-0031 sections 9.1, 10, 11, 12.6, 13 and ADR-0026 6.3 -----------------
EPS = 0.001
MARGIN = 0.005
CELLS_MIN = 22
PARENTS_MIN = 8
SHARE = 0.90
DENSE_FLOOR = 0.005
TOL = -0.005
TREND = 0.005
U = {-1: 8192, 0: 16384, 1: 32768, 2: 65536, 3: 131072, 4: 262144}
KMAX = 4
NC, NP = 27, 9
F, D = "M-FLAT", "D-ADAPT"

problems: list[str] = []


def load(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def mean(xs):  # G5: Python float sum in cell order, divided by the count
    xs = list(xs)
    s = 0.0
    for x in xs:
        s += x
    return s / len(xs)


def pmeans(vals):  # parent p = cells 3p, 3p+1, 3p+2
    return [mean(vals[3 * p:3 * p + 3]) for p in range(NP)]


def rl(r: float) -> str:
    return f"{r:g}"


# ---- 1. plan vs records --------------------------------------------------------------------------------------------------
plan = load(WT / "studies/p10i_s6/freeze/plan.json")
rt = load(WT / "studies/p10i_s6/freeze/rate_table.json")
RATE = {a: {int(k): v for k, v in rt["rates"][a].items()} for a in (F, D)}
items_dir = RUN / "items"
dirs = sorted(os.listdir(items_dir))
plan_ids = [x["id"] for x in plan["items"]["train"]] + [x["id"] for x in plan["items"]["eval"]]
if len(set(plan_ids)) != len(plan_ids):
    problems.append("duplicate ids in plan")
dir_ids = {d.replace("__", "|"): d for d in dirs}
missing = [i for i in plan_ids if i not in dir_ids]
extra = [i for i in dir_ids if i not in set(plan_ids)]
if missing or extra:
    problems.append(f"plan/items mismatch: missing {len(missing)} extra {len(extra)}")

registered_start = datetime(2026, 11, 20, 10, 57, 40, tzinfo=timezone.utc)  # gates stage start (registered)
train_rec, eval_rec, births = {}, {}, []
for t in plan["items"]["train"]:
    d = items_dir / dir_ids[t["id"]]
    files = sorted(os.listdir(d))
    r = load(d / "train.json")
    if r["id"] != t["id"] or r["status"] != "ok" or r["updates_done"] != t["max_update"] or r["resumed_from"] is not None \
            or r["failed_at_update"] is not None or r["snapshots"] != t["snapshots"] or files != ["snapshots", "train.json"]:
        problems.append(f"train record anomaly {t['id']}: {r}")
    snaps = sorted(os.listdir(d / "snapshots"))
    births.append(os.stat(d / "train.json").st_birthtime)
    train_rec[t["id"]] = (r, snaps)
for e in plan["items"]["eval"]:
    d = items_dir / dir_ids[e["id"]]
    files = sorted(os.listdir(d))
    r = load(d / "eval.json")
    if r["id"] != e["id"] or r["controls"] != e["controls"] or r["update"] != e["update"] or files != ["eval.json"] or r["nonfinite_enabled"]:
        problems.append(f"eval record anomaly {e['id']}")
    for k, v in r["reads"].items():
        if not (isinstance(v, float) and math.isfinite(v)):
            problems.append(f"non-finite read {e['id']} {k}")
    births.append(os.stat(d / "eval.json").st_birthtime)
    eval_rec[e["id"]] = r
earliest = datetime.fromtimestamp(min(births), tz=timezone.utc)
latest = datetime.fromtimestamp(max(births), tz=timezone.utc)

# ---- BASE (stage G record) --------------------------------------------------------------------------------------------------
core = load(RUN / "gates/results/core.json")
bv = core["results"]["base_values"]
B = {}
for p in range(NP):
    x = bv[str(p)]
    if x["enabled"] != x["replay"]:
        problems.append(f"BASE replay mismatch parent {p}")
    B[p] = x["enabled"]
BOA = {}
for p in range(NP):
    x = bv[f"oa{p}"]
    if x["enabled"] != x["replay"]:
        problems.append(f"OA BASE replay mismatch {p}")
    BOA[p] = x["enabled"]

parent_of = {}
for t in plan["items"]["train"]:
    parent_of[(t["profile"], t["cell"])] = t["parent"]
    if t["parent"] != t["cell"] // 3:
        problems.append(f"cell/parent layout differs from c=3p+s: {t['id']}")


def ev(profile, arm, rate, cell, update):
    return eval_rec[f"eval|{profile}|{arm}|r{rl(rate)}|c{cell:02d}|u{update:06d}"]


# ---- integrity on every read a rule reads (rungs -1..4 at r(arm,k), plus the delta-run point) and on every other record --
integrity = []
for i, r in eval_rec.items():
    prof = i.split("|")[1]
    cell = int(i.split("|")[4][1:])
    base = (B if prof == "registered" else BOA)[parent_of[(prof, cell)]]
    rd = r["reads"]
    if "replay|0" in rd and rd["replay|0"] != rd["enabled|0"]:
        integrity.append(f"replay != enabled {i}")
    if "disabled|0" in rd and rd["disabled|0"] != base:
        integrity.append(f"disabled != BASE {i}")
reads_needed_triple = []
for arm in (F, D):
    for k in range(-1, KMAX + 1):
        for c in range(NC):
            r = ev("registered", arm, RATE[arm][k], c, U[k])
            if not {"enabled|0", "replay|0", "disabled|0"} <= set(r["reads"]):
                reads_needed_triple.append(f"{arm} k{k} c{c}")

# ---- the quantities --------------------------------------------------------------------------------------------------------
def nll(arm, k, c, upd=None, read="enabled|0"):
    return ev("registered", arm, RATE[arm][k], c, U[k] if upd is None else upd)["reads"][read]


H = {k: [nll(F, k, c) for c in range(NC)] for k in range(-1, KMAX + 1)}
A = {k: [nll(D, k, c) for c in range(NC)] for k in range(-1, KMAX + 1)}
Bc = [B[parent_of[("registered", c)]] for c in range(NC)]
L = {F: {k: mean(H[k]) for k in H}, D: {k: mean(A[k]) for k in A}}
delta = {a: {k: L[a][k - 1] - L[a][k] for k in range(0, KMAX + 1)} for a in (F, D)}
drun = {}
for a in (F, D):
    drun[a] = {}
    for k in range(0, KMAX + 1):
        prev = [nll(a, k, c, upd=U[k - 1]) for c in range(NC)]
        cur = [nll(a, k, c) for c in range(NC)]
        drun[a][k] = mean(prev) - mean(cur)
conv = {a: {k: (delta[a][k] < EPS and drun[a][k] < EPS) for k in range(0, KMAX + 1)} for a in (F, D)}
settled = {a: {k: all(conv[a][j] for j in range(k, KMAX + 1)) for k in range(0, KMAX + 1)} for a in (F, D)}
kstar = next((k for k in range(0, KMAX + 1) if settled[F][k] and settled[D][k]), None)
R = kstar if kstar is not None else KMAX
# j-dagger: lowest L(D,.) over 0..kmax, exact tie -> larger rung
jd = None
for k in range(0, KMAX + 1):
    if jd is None or L[D][k] <= L[D][jd]:
        jd = k

per = {}
for k in range(0, KMAX + 1):
    Q = [A[k][c] - H[k][c] for c in range(NC)]
    Qd = [A[jd][c] - H[k][c] for c in range(NC)]
    mQ, mQd = mean(Q), mean(Qd)
    pQ, pQd = pmeans(Q), pmeans(Qd)
    cpos, ppos = sum(q > 0 for q in Q), sum(q > 0 for q in pQ)
    cneg, pneg = sum(q < 0 for q in Q), sum(q < 0 for q in pQ)
    held = mQ >= MARGIN and cpos >= CELLS_MIN and ppos >= PARENTS_MIN
    heldd = mQd >= MARGIN and sum(q > 0 for q in Qd) >= CELLS_MIN and sum(q > 0 for q in pQd) >= PARENTS_MIN
    if held and heldd:
        cls = "M-AHEAD"
    elif mQ <= -MARGIN and cneg >= CELLS_MIN and pneg >= PARENTS_MIN:
        cls = "D-AHEAD"
    elif -MARGIN < mQ < MARGIN:
        cls = "LEVEL"
    else:
        cls = "UNDECIDED"
    C = [Bc[c] - H[k][c] for c in range(NC)]
    Cd = [Bc[c] - A[k][c] for c in range(NC)]
    # controls on the full read of M-FLAT at r(F,k), U_k; dense X_mean_dense at r(D,k), U_k
    fr = [ev("registered", F, RATE[F][k], c, U[k])["reads"] for c in range(NC)]
    used = [ev("registered", F, RATE[F][k], c, U[k])["stats"]["used_slots"] for c in range(NC)]
    Hused = [mean([fr[c][f"P_used|{j}"] for j in range(4)]) for c in range(NC)]
    Pused = [Hused[c] - H[k][c] for c in range(NC)]
    Pused_alt = [mean([fr[c][f"P_used|{j}"] - H[k][c] for j in range(4)]) for c in range(NC)]
    Hmean = [fr[c]["X_mean|0"] for c in range(NC)]
    Hv = [fr[c]["V_mean|0"] for c in range(NC)]
    dr = [ev("registered", D, RATE[D][k], c, U[k])["reads"] for c in range(NC)]
    xmd = [dr[c]["X_mean_dense|0"] - A[k][c] for c in range(NC)]
    per[k] = dict(
        updates=U[k], rate_F=RATE[F][k], rate_D=RATE[D][k], L_F=L[F][k], L_D=L[D][k],
        delta_F=delta[F][k], delta_D=delta[D][k], drun_F=drun[F][k], drun_D=drun[D][k],
        conv_F=conv[F][k], conv_D=conv[D][k], mean_Q=mQ, Q_cells_pos=cpos, Q_parents_pos=ppos,
        Q_min=min(Q), Q_max=max(Q), mean_Qdag=mQd, Qdag_cells_pos=sum(q > 0 for q in Qd),
        Qdag_parents_pos=sum(q > 0 for q in pQd), held=held, cls=cls,
        mean_C=mean(C), mean_Cd=mean(Cd), C_cells_pos=sum(x > 0 for x in C),
        harm_Hused=mean([Bc[c] - Hused[c] for c in range(NC)]), harm_Hused_n=sum(Hused[c] > Bc[c] for c in range(NC)),
        harm_Hmean=mean([Bc[c] - Hmean[c] for c in range(NC)]), harm_Hmean_n=sum(Hmean[c] > Bc[c] for c in range(NC)),
        harm_Hv=mean([Bc[c] - Hv[c] for c in range(NC)]), harm_Hv_n=sum(Hv[c] > Bc[c] for c in range(NC)),
        used_slots=used, used_min=min(used), used_max=max(used),
        xmd_mean=mean(xmd), xmd_min=min(xmd), xmd_max=max(xmd), xmd_pos=sum(x > 0 for x in xmd),
        _C=C, _Cd=Cd, _Pused=Pused, _Pused_alt=Pused_alt, _Xmean=[Hmean[c] - H[k][c] for c in range(NC)],
        _Q=Q, _pQ=pQ,
    )

# ---- D[FLAT] at R ------------------------------------------------------------------------------------------------------------
pr = per[R]
C, Pu, Xm = pr["_C"], pr["_Pused"], pr["_Xmean"]
collapsed = [c for c in range(NC) if pr["used_slots"][c] < 2]
F1 = mean(C) >= MARGIN and sum(x > 0 for x in C) >= CELLS_MIN and sum(x > 0 for x in pmeans(C)) >= PARENTS_MIN
F2 = (not collapsed) and mean(Pu) >= MARGIN and sum(C[c] > 0 and Pu[c] >= 0.5 * C[c] for c in range(NC)) >= CELLS_MIN \
    and sum(x > 0 for x in pmeans(Pu)) >= PARENTS_MIN
F3 = mean(Xm) >= MARGIN and sum(C[c] > 0 and Xm[c] >= 0.5 * C[c] for c in range(NC)) >= CELLS_MIN \
    and sum(x > 0 for x in pmeans(Xm)) >= PARENTS_MIN
F2_alt = (not collapsed) and mean(pr["_Pused_alt"]) >= MARGIN and sum(C[c] > 0 and pr["_Pused_alt"][c] >= 0.5 * C[c] for c in range(NC)) >= CELLS_MIN \
    and sum(x > 0 for x in pmeans(pr["_Pused_alt"])) >= PARENTS_MIN
dflat = "DEPENDENT" if (F1 and F2 and F3) else ("CAPACITY WITHOUT DEMONSTRATED DEPENDENCE" if F1 else "NO CAPACITY")
dflat_detail = dict(F1_mean=mean(C), F1_cells=sum(x > 0 for x in C), F1_parents=sum(x > 0 for x in pmeans(C)),
                    F2_mean=mean(Pu), F2_mean_alt=mean(pr["_Pused_alt"]),
                    F2_cells=sum(C[c] > 0 and Pu[c] >= 0.5 * C[c] for c in range(NC)), F2_parents=sum(x > 0 for x in pmeans(Pu)),
                    F3_mean=mean(Xm), F3_cells=sum(C[c] > 0 and Xm[c] >= 0.5 * C[c] for c in range(NC)),
                    F3_parents=sum(x > 0 for x in pmeans(Xm)), F1=F1, F2=F2, F2_alt=F2_alt, F3=F3, collapsed=collapsed)

# ---- line P ---------------------------------------------------------------------------------------------------------------
causes = []
if integrity:
    causes.append("integrity (2)")
if per[R]["mean_Cd"] < DENSE_FLOOR:
    causes.append("dense floor (4)")
classes = {k: per[k]["cls"] for k in range(0, KMAX + 1)}
if causes:
    row, label = 1, f"NOT EVALUABLE ({causes})"
elif kstar is not None:
    cs = {classes[k] for k in range(kstar, KMAX + 1)}
    if len(cs) > 1:
        row, label = 3, "ORDERING NOT STABLE AFTER CONVERGENCE"
    else:
        row, label = {"M-AHEAD": (4, "PERSISTS AT CONVERGENCE"), "LEVEL": (5, "LEVEL AT CONVERGENCE"),
                      "D-AHEAD": (6, "DENSE AHEAD AT CONVERGENCE"), "UNDECIDED": (7, "LEAD NOT ESTABLISHED AT CONVERGENCE")}[cs.pop()]
else:
    cD, cF = conv[D][KMAX], conv[F][KMAX]
    if cD and not cF and classes[KMAX] == "M-AHEAD":
        row, label = 8, "MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING)"
    elif cF and not cD and classes[KMAX] == "D-AHEAD":
        row, label = 9, "DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING)"
    elif cF and not cD:
        row, label = 10, "CONVERGENCE NOT REACHED (DENSE STILL IMPROVING)"
    elif cD and not cF:
        row, label = 11, "CONVERGENCE NOT REACHED (MEMORY STILL IMPROVING)"
    else:
        row, label = 12, "CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)"
dep_q = row in (4, 8) and dflat == "DEPENDENT"

# ---- trend line -----------------------------------------------------------------------------------------------------------
HELD = {k: per[k]["held"] for k in range(0, KMAX + 1)}
Delta = per[KMAX]["mean_Q"] - per[0]["mean_Q"]
if row in (1, 2):
    tag = "TREND NOT DETERMINED"
elif not HELD[0]:
    tag = "LEAD ABSENT AT RUNG 0 (16,384 UPDATES, NEW PARENTS AND DATA)"
elif not all(HELD.values()):
    first = min(k for k in HELD if not HELD[k])
    tag = f"LEAD LOST BY RUNG {first}" if all(not HELD[j] for j in range(first, KMAX + 1)) else "NOT MONOTONE"
elif Delta <= -TREND:
    tag = "LEAD SHRINKING"
elif Delta >= TREND:
    tag = "LEAD GROWING"
else:
    tag = "LEAD HELD AT EVERY RUNG"
absQ = abs(per[KMAX]["mean_Q"])
still = delta[F][KMAX] >= absQ or delta[D][KMAX] >= absQ

# ---- R16 and OA (ADR-0026 6.3 at rung 0; OA: old parents, 16,384 updates) ------------------------------------------------
def k_rule(Hs, As, Bs):
    Q = [As[c] - Hs[c] for c in range(NC)]
    C = [Bs[c] - Hs[c] for c in range(NC)]
    Cd = [Bs[c] - As[c] for c in range(NC)]
    pQ = pmeans(Q)
    K1 = mean(Q) >= TOL and sum(q >= TOL for q in Q) >= CELLS_MIN and sum(q >= TOL for q in pQ) >= PARENTS_MIN
    K2 = mean(C) >= SHARE * mean(Cd)
    K3 = mean(Q) >= MARGIN and sum(q > 0 for q in Q) >= CELLS_MIN and sum(q > 0 for q in pQ) >= PARENTS_MIN
    if mean(Cd) < DENSE_FLOOR:
        lab = "NOT EVALUABLE (dense floor)"
    elif K3:
        lab = "REPLICATED AT 16,384"
    elif K1 and K2:
        lab = "NOT REPLICATED (WITHIN TOLERANCE)"
    else:
        lab = "NOT REPLICATED"
    return dict(label=lab, K1=K1, K2=K2, K3=K3, mean_Q=mean(Q), mean_C=mean(C), mean_Cd=mean(Cd),
                Q_cells_pos=sum(q > 0 for q in Q), Q_parents_pos=sum(q > 0 for q in pQ), min_parent_Q=min(pQ))


r16 = k_rule(H[0], A[0], Bc)
r16["conv_rung0"] = {F: conv[F][0], D: conv[D][0]}
Hoa = [ev("oa", F, RATE[F][0], c, 16384)["reads"]["enabled|0"] for c in range(NC)]
Aoa = [ev("oa", D, RATE[D][0], c, 16384)["reads"]["enabled|0"] for c in range(NC)]
Boa = [BOA[parent_of[("oa", c)]] for c in range(NC)]
oa = k_rule(Hoa, Aoa, Boa)
oa["drun"] = {F: mean([ev("oa", F, RATE[F][0], c, 8192)["reads"]["enabled|0"] for c in range(NC)]) - mean(Hoa),
              D: mean([ev("oa", D, RATE[D][0], c, 8192)["reads"]["enabled|0"] for c in range(NC)]) - mean(Aoa)}

# ---- compare with the implementer's analysis.json (values read, code not used) -----------------------------------------
an = load(RUN / "analysis/analysis.json")["result"]
cmp = []


def same(name, mine, theirs):
    ok = mine == theirs
    cmp.append((name, ok, mine, theirs))


for k in range(0, KMAX + 1):
    a = an["per_rung"][str(k)]
    same(f"k{k} L_F", per[k]["L_F"], a["L"][F]); same(f"k{k} L_D", per[k]["L_D"], a["L"][D])
    same(f"k{k} delta_F", per[k]["delta_F"], a["delta"][F]); same(f"k{k} delta_D", per[k]["delta_D"], a["delta"][D])
    same(f"k{k} drun_F", per[k]["drun_F"], a["delta_run"][F]); same(f"k{k} drun_D", per[k]["drun_D"], a["delta_run"][D])
    same(f"k{k} conv", ("CONVERGED" if per[k]["conv_F"] else "NOT CONVERGED", "CONVERGED" if per[k]["conv_D"] else "NOT CONVERGED"),
         (a["convergence"][F], a["convergence"][D]))
    same(f"k{k} mean_Q", per[k]["mean_Q"], a["mean_Q"]); same(f"k{k} Q_cells_pos", per[k]["Q_cells_pos"], a["Q_cells_positive"])
    same(f"k{k} Q_parents_pos", per[k]["Q_parents_pos"], a["Q_parents_positive"])
    same(f"k{k} mean_Qdag", per[k]["mean_Qdag"], a["Q_dag"]["mean"]); same(f"k{k} class", per[k]["cls"], a["class"])
    same(f"k{k} held", per[k]["held"], a["held"]); same(f"k{k} rates", (per[k]["rate_F"], per[k]["rate_D"]), (a["rates"][F], a["rates"][D]))
    same(f"k{k} mean_C", per[k]["mean_C"], a["C"]["mean"]); same(f"k{k} mean_Cd", per[k]["mean_Cd"], a["Cd"]["mean"])
    same(f"k{k} xmd_mean", per[k]["xmd_mean"], a["X_mean_dense"]["mean"])
    same(f"k{k} xmd_min", per[k]["xmd_min"], a["X_mean_dense"]["min"]); same(f"k{k} xmd_max", per[k]["xmd_max"], a["X_mean_dense"]["max"])
    h = an["harm"][str(k)]
    same(f"k{k} harm_Hused", per[k]["harm_Hused"], h["H_used"]["mean_B_minus"]); same(f"k{k} harm_Hused_n", per[k]["harm_Hused_n"], h["H_used"]["cells_worse_than_base"])
    same(f"k{k} harm_Hmean", per[k]["harm_Hmean"], h["H_mean"]["mean_B_minus"]); same(f"k{k} harm_Hmean_n", per[k]["harm_Hmean_n"], h["H_mean"]["cells_worse_than_base"])
    same(f"k{k} harm_Hv", per[k]["harm_Hv"], h["H_vmean"]["mean_B_minus"]); same(f"k{k} harm_Hv_n", per[k]["harm_Hv_n"], h["H_vmean"]["cells_worse_than_base"])
    same(f"k{k} used_slots", per[k]["used_slots"], h["used_slots"])
same("j_dagger", jd, an["j_dagger"]); same("k_star", kstar, an["k_star"]); same("row", row, an["line_p"]["row"])
same("label base", label, an["line_p"]["base_label"]); same("dependence_qualified", dep_q, an["line_p"]["dependence_qualified"])
same("D[FLAT]", dflat, an["d_flat"]["label"]); same("F1 mean", dflat_detail["F1_mean"], an["d_flat"]["conditions"]["F1"]["mean"])
same("F2 mean", dflat_detail["F2_mean"], an["d_flat"]["conditions"]["F2"]["mean"]); same("F3 mean", dflat_detail["F3_mean"], an["d_flat"]["conditions"]["F3"]["mean"])
same("F1 cells/parents", (dflat_detail["F1_cells"], dflat_detail["F1_parents"]), (an["d_flat"]["conditions"]["F1"]["cells"], an["d_flat"]["conditions"]["F1"]["parents"]))
same("F2 cells/parents", (dflat_detail["F2_cells"], dflat_detail["F2_parents"]), (an["d_flat"]["conditions"]["F2"]["cells"], an["d_flat"]["conditions"]["F2"]["parents"]))
same("F3 cells/parents", (dflat_detail["F3_cells"], dflat_detail["F3_parents"]), (an["d_flat"]["conditions"]["F3"]["cells"], an["d_flat"]["conditions"]["F3"]["parents"]))
same("OA label", oa["label"], an["oa"]["label"]); same("OA mean_Q", oa["mean_Q"], an["oa"]["q_mean"])
same("OA drun_F", oa["drun"][F], an["oa"]["delta_run"][F]); same("OA drun_D", oa["drun"][D], an["oa"]["delta_run"][D])
same("BASE", [B[p] for p in range(NP)], [an["base"][str(p)] for p in range(NP)])

res = dict(problems=problems, integrity=integrity, reads_missing=reads_needed_triple, items_plan=len(plan_ids), item_dirs=len(dirs),
           missing=missing, extra=extra, earliest_record_birth=earliest.isoformat(), latest_record_birth=latest.isoformat(),
           record_births_after_registered_gates_start=earliest >= registered_start,
           rates=RATE, kstar=kstar, R=R, jdagger=jd, row=row, label=label, dependence_qualified=dep_q,
           tag=tag, Delta=Delta, absQ=absQ, still_improving_sentence=still, held=HELD,
           per_rung={k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in per.items()},
           L_minus1={F: L[F][-1], D: L[D][-1]}, dflat=dflat, dflat_detail=dflat_detail,
           dflat_Hused_worse=per[R]["harm_Hused_n"], dflat_mean_B_minus_Hv=per[R]["harm_Hv"],
           R16=r16, OA=oa, comparisons=[dict(name=n, equal=o, mine=m, theirs=t) for n, o, m, t in cmp])
OUT.write_text(json.dumps(res, indent=1, default=str))

print("problems:", problems)
print("integrity:", len(integrity), integrity[:5], "missing triple:", len(reads_needed_triple))
print("plan items", len(plan_ids), "dirs", len(dirs), "missing", len(missing), "extra", len(extra))
print("record births", earliest.isoformat(), "->", latest.isoformat())
print("rates", RATE)
print(f"L(-1): F {L[F][-1]!r} D {L[D][-1]!r}")
print("k | U | rF rD | L_F L_D | dF dD | drF drD | convF convD | meanQ cells+ parents+ | meanQdag | held | class")
for k, v in per.items():
    print(k, v["updates"], v["rate_F"], v["rate_D"], repr(v["L_F"]), repr(v["L_D"]), repr(v["delta_F"]), repr(v["delta_D"]),
          repr(v["drun_F"]), repr(v["drun_D"]), v["conv_F"], v["conv_D"], repr(v["mean_Q"]), v["Q_cells_pos"], v["Q_parents_pos"],
          repr(v["mean_Qdag"]), v["Qdag_cells_pos"], v["Qdag_parents_pos"], v["held"], v["cls"])
print("K*", kstar, "R", R, "j†", jd, "row", row, label, "dep-qualified", dep_q)
print("tag", tag, "Delta", repr(Delta), "|Q(kmax)|", repr(absQ), "still-improving sentence", still)
print("D[FLAT]", dflat, dflat_detail)
for k, v in per.items():
    print(f"harm k{k}: B-Hused {v['harm_Hused']!r} ({v['harm_Hused_n']}); B-Hmean {v['harm_Hmean']!r} ({v['harm_Hmean_n']}); "
          f"B-Hv {v['harm_Hv']!r} ({v['harm_Hv_n']}); used slots {v['used_min']}..{v['used_max']}; "
          f"XMD mean {v['xmd_mean']!r} min {v['xmd_min']!r} max {v['xmd_max']!r} pos {v['xmd_pos']}; meanC {v['mean_C']!r} meanCd {v['mean_Cd']!r}")
print("R16", r16)
print("OA", oa)
bad = [c for c in cmp if not c[1]]
print(f"comparisons with analysis.json: {len(cmp)} fields, {len(bad)} unequal")
for n, o, m, t in bad:
    print("  UNEQUAL", n, m, t)
