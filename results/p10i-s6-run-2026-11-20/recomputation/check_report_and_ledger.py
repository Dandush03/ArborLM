# ruff: noqa
"""Auditor's second checker: (a) every printed figure of report.md against recompute_out.json at the printed precision;
(b) per-parent delta / delta-run, rung -1 and step-0 figures of analysis.json against an independent computation;
(c) the ledger arithmetic, the stage manifests and the attempts records.
Imports nothing from the study. Run: python3 -I check_report_and_ledger.py <run_dir>
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

RUN = Path(sys.argv[1])
HERE = Path(__file__).resolve().parent
me = json.loads((HERE / "recompute_out.json").read_text())
rep = (RUN / "analysis/report.md").read_text()
F, D = "M-FLAT", "D-ADAPT"
out = []


def chk(name, printed, value):
    out.append((name, printed, value, printed == value))


def f4(x):
    return f"{x:.4f}"


# ---- (a) report.md -------------------------------------------------------------------------------------------------------
pr = me["per_rung"]
rows = re.findall(r"^\| (\d) \| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", rep, re.M)
chk("table rows", 5, len(rows))
for r in rows:
    k = r[0]
    v = pr[k]
    mine = [k, str(v["updates"]), f"{v['rate_F']:g}", f"{v['rate_D']:g}", f4(v["L_F"]), f4(v["L_D"]), f4(v["delta_F"]), f4(v["delta_D"]),
            f4(v["drun_F"]), f4(v["drun_D"]), "CONVERGED" if v["conv_F"] else "NOT CONVERGED", "CONVERGED" if v["conv_D"] else "NOT CONVERGED",
            f4(v["mean_Q"]), v["cls"]]
    for i, (a, b) in enumerate(zip([x.strip() for x in r], mine)):
        chk(f"table k{k} col{i}", a, b)
m = re.search(r"## Line P \(registered\): (.+?) \[(.+)\]$", rep, re.M)
chk("line P label", m.group(1), me["label"])
qs = ", ".join(f4(pr[str(k)]["mean_Q"]) for k in range(5))
trend_text = f"{me['tag']} (Δ = {me['Delta']:.4f}; {qs}); over 16,384 to U_max updates only; descriptive; this says nothing about the ordering at convergence and is not the label PERSISTS."
chk("trend inside line P", m.group(2), trend_text)
chk("trend line", re.search(r"^## Trend line \(descriptive; never a label\): (.+)$", rep, re.M).group(1), trend_text)
chk("row/R/K*/kmax/depq", re.search(r"^- row (\d+); reading rung R = (\d) \(K\* = (\w+)\), k_max = (\d); dependence-qualified: (\w+)$", rep, re.M).groups(),
    (str(me["row"]), str(me["R"]), str(me["kstar"]), "4", str(me["dependence_qualified"])))
sent = (f"- |mean Q(k_max)| = {me['absQ']:.4f}; δ(M-FLAT, k_max) = {pr['4']['delta_F']:.4f}; δ(D-ADAPT, k_max) = {pr['4']['delta_D']:.4f}."
        + (" an arm is still improving per doubling by at least the size of the lead" if me["still_improving_sentence"] else ""))
chk("lead sentence", re.search(r"^- \|mean Q\(k_max\)\|.*$", rep, re.M).group(0), sent)
chk("D[FLAT]", re.search(r"^## D\[FLAT\] at R: (.+)$", rep, re.M).group(1), me["dflat"])
chk("D[FLAT] detail", re.search(r"^- failing: .*$", rep, re.M).group(0),
    f"- failing: []; collapsed cells: {me['dflat_detail']['collapsed']}; cells with H_used > B: {me['dflat_Hused_worse']}; mean B - H_vmean: {me['dflat_mean_B_minus_Hv']:.4f}")
for k in range(5):
    v = pr[str(k)]
    chk(f"XMD k{k}", re.search(rf"^- rung {k}: mean .*cells above 0: \d+\)$", rep, re.M).group(0),
        f"- rung {k}: mean {v['xmd_mean']:.4f} (min {v['xmd_min']:.4f}, max {v['xmd_max']:.4f}, cells above 0: {v['xmd_pos']})")
    chk(f"harm k{k}", re.search(rf"^- rung {k}: B-H_used .*$", rep, re.M).group(0),
        f"- rung {k}: B-H_used {v['harm_Hused']:.4f} ({v['harm_Hused_n']} cells worse than BASE); B-H_mean {v['harm_Hmean']:.4f} ({v['harm_Hmean_n']}); B-H_vmean {v['harm_Hv']:.4f} ({v['harm_Hv_n']})")
chk("R16/OA", re.search(r"^## R16: (.+?); OA: (.+?) \(", rep, re.M).groups(), (me["R16"]["label"], me["OA"]["label"]))

# ---- (b) per-parent deltas, rung -1, step 0 -------------------------------------------------------------------------------
an = json.loads((RUN / "analysis/analysis.json").read_text())["result"]
items = RUN / "items"
rates = {a: {int(k): v for k, v in me["rates"][a].items()} for a in (F, D)}
U = {-1: 8192, 0: 16384, 1: 32768, 2: 65536, 3: 131072, 4: 262144}


def rd(arm, rate, c, u, read="enabled|0", prof="registered"):
    return json.loads((items / f"eval__{prof}__{arm}__r{rate:g}__c{c:02d}__u{u:06d}" / "eval.json").read_text())["reads"][read]


def mean(xs):
    s = 0.0
    for x in xs:
        s += x
    return s / len(xs)


pp_env, pp_run = {}, {}
for a in (F, D):
    for k in range(5):
        env = [mean([rd(a, rates[a][k - 1], c, U[k - 1]) for c in range(3 * p, 3 * p + 3)]) - mean([rd(a, rates[a][k], c, U[k]) for c in range(3 * p, 3 * p + 3)]) for p in range(9)]
        run = [mean([rd(a, rates[a][k], c, U[k - 1]) for c in range(3 * p, 3 * p + 3)]) - mean([rd(a, rates[a][k], c, U[k]) for c in range(3 * p, 3 * p + 3)]) for p in range(9)]
        chk(f"per-parent envelope delta {a} k{k} == analysis.delta_envelope_per_parent", env, an["per_rung"][str(k)]["delta_envelope_per_parent"][a])
        chk(f"per-parent run delta {a} k{k} == analysis.delta_per_parent", run, an["per_rung"][str(k)]["delta_per_parent"][a])
for a in (F, D):
    cells = [rd(a, rates[a][-1], c, 8192) for c in range(27)]
    chk(f"rung -1 L {a}", mean(cells), an["rung_minus_one"][a]["L"])
    for r in sorted(set(rates[a].values())):
        s0 = mean([rd(a, r, c, 0) for c in range(27)])
        chk(f"step0 {a} r{r:g} == analysis step0 (same for every rung)", s0, an["step0"][a]["0"]["enabled_mean"])
        chk(f"step0 disabled == BASE {a} r{r:g}", [rd(a, r, c, 0, "disabled|0") for c in range(27)],
            [an["base"][str(c // 3)] for c in range(27)])
base_mean = mean([an["base"][str(c // 3)] for c in range(27)])

# ---- (c) ledger, manifests, attempts ----------------------------------------------------------------------------------------
led = json.loads((RUN / "ledger.json").read_text())
plan_caps = json.loads((Path(sys.argv[2]) / "studies/p10i_s6/freeze/plan.json").read_text())["caps"]
charged = sum(e["seconds"] for e in led["entries"])
ledger = dict(total_seconds=led["total_seconds"], cap_hours_times_3600=plan_caps["registered_hours"] * 3600.0,
              total_equals_cap=led["total_seconds"] == plan_caps["registered_hours"] * 3600.0,
              charged_seconds=charged, charged_hours=charged / 3600.0, remaining_seconds=led["total_seconds"] - charged,
              fraction_of_cap=charged / led["total_seconds"], entries=led["entries"])
mans = {}
for s in ("gates", "train", "eval"):
    m = json.loads((RUN / s / "manifest.json").read_text())
    mans[s] = dict(status=m["status"], mode=m["mode"], charged=m["charged_seconds"], n_history=len(m["history"]),
                   history=[dict(start=h["started_utc"], end=h["finished_utc"], charged=h["charged_seconds"], caps=h["caps"],
                                 outcomes=dict(Counter(h["outcomes"].values()))) for h in m["history"]],
                   commit=m["identity"].get("commit"))
att = []
for fn in sorted(os.listdir(RUN / "attempts")):
    r = json.loads((RUN / "attempts" / fn).read_text())
    att.append((r["utc"], r["what"], r.get("item") or r.get("task") or r.get("stage"), r.get("reason", "")[:140] if r.get("reason") else ""))
att_summary = Counter((a[0][:13], a[1], (a[2] or "").split("|")[1] if a[2] and "|" in a[2] else a[2]) for a in att)

res = dict(report_checks=[dict(name=n, printed=p, mine=v, equal=e) for n, p, v, e in out], ledger=ledger, manifests=mans,
           attempts=att, attempts_summary={" / ".join(map(str, k)): v for k, v in att_summary.items()}, base_mean_27=base_mean)
(HERE / "check_out.json").write_text(json.dumps(res, indent=1, default=str, ensure_ascii=False))
bad = [x for x in out if not x[3]]
print(f"report/analysis checks: {len(out)}, unequal: {len(bad)}")
for n, p, v, e in bad:
    print("  UNEQUAL", n, "| printed:", p, "| mine:", v)
print("BASE mean over 27 cells", repr(base_mean))
print("ledger", json.dumps({k: v for k, v in ledger.items() if k != "entries"}))
for s, m in mans.items():
    print(s, json.dumps(m))
print("attempts:")
for k, v in sorted(att_summary.items()):
    print(" ", v, k)
