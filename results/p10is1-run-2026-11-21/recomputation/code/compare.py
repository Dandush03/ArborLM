# ruff: noqa
"""Compare recompute.py's output with the study's analysis output (same run directory). Prints every difference; exit code 0 always.
Usage: python3 compare.py <recompute.json> <study_analysis.json>"""

import json
import math
import sys

mine = json.load(open(sys.argv[1]))
study = json.load(open(sys.argv[2]))
study = study.get("result", study)
diffs, checked = [], [0]


def eq(a, b, tol=1e-9):
    checked[0] += 1
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isinf(a) or math.isinf(b):
            return a == b
        return abs(a - b) <= tol
    return a == b


def cmp(path, a, b, tol=1e-9):
    if not eq(a, b, tol):
        diffs.append((path, a, b))


if mine.get("status") != "COMPLETE" or study.get("status") != "COMPLETE":
    print("status: mine", mine.get("status"), "| study", study.get("status"), "| lines: mine", mine.get("lines"), "| study", study.get("lines"))
    print("missing (mine)", mine.get("missing_count"), mine.get("missing_ladder_decisions"), "item errors", mine.get("item_errors"), "failed cells", mine.get("failed_cells"))
    sys.exit(0)
cmp("lines", mine["lines"], study["lines"])
cmp("status", mine["status"], study["status"])
cmp("reference_failed_dep", sorted(json.dumps(x, sort_keys=True) for x in mine["reference_failed_dep"]), sorted(json.dumps(x, sort_keys=True) for x in study["reference_failed_dep"]))
cmp("ladder stops", {k: v["recorded"] for k, v in mine["ladder_stop_check"].items()}, {k: v["u_run"] for k, v in study["ladder_stops"].items()})
mc, sc = mine["capacity"], study["capacity"]
cmp("capacity.outcome", mc["outcome"], sc["outcome"]["label"])
cmp("key_learning_limited", mc["key_learning_limited"], sc["key_learning_limited"])
NAME = {"MC-A": "MC-A", "MC-T": "MC-T", "MC-C": "MC-C"}
for arm, ma in mc["arms"].items():
    sa = sc["arms"][arm]
    cmp(f"{arm}.class", ma["class"], sa["class"])
    cmp(f"{arm}.dense_arm", ma["dense_arm"], sa["dense_arm"] if isinstance(sa["dense_arm"], str) else sa["dense_arm"].get("label"))
    cmp(f"{arm}.a_use_largest", ma["a_use_largest_all"], sa["a_use_at_32K_16K_all5"])
    for st, mstep in ma["steps_detail"].items():
        sstep = sa["steps"][st]
        cmp(f"{arm}.{st}.class", mstep["class"], sstep["class"])
        cmp(f"{arm}.{st}.verdicts", mstep["verdicts"], sstep["verdicts"])
        for mr, sr in zip(mstep["replicates"], sstep["replicates"]):
            for p in ("A", "B"):
                md, sd = mr["detail"][p], sr["detail"]["panels"][p]
                cmp(f"{arm}.{st}.r{mr['replicate']}.{p}.verdict", mr["panels"][p], sd["verdict"])
                for mk, sk in (("d_mu", "delta_mu"), ("d_sat", "delta_sat"), ("d_full", "delta_full"), ("i_small_up", "i_small_up"), ("i_large_up", "i_large_up"), ("a_use_large_up", "a_use_large_up")):
                    if sk in sd:  # the study omits the quantities of a verdict decided before them (NOT_EVALUATED, DEPENDENCE_FAILED)
                        cmp(f"{arm}.{st}.r{mr['replicate']}.{p}.{mk}", md[mk], sd[sk])
                for k in ("MC-A", "MC-T", "MC-C"):
                    if "delta_mc" in sd and (k in md["d_mc"] or k in sd.get("delta_mc", {})):
                        cmp(f"{arm}.{st}.r{mr['replicate']}.{p}.d_{k}", md["d_mc"].get(k), sd.get("delta_mc", {}).get(k))
                        smc = sd.get("mc", {}).get(k)
                        if smc:
                            cmp(f"{arm}.{st}.r{mr['replicate']}.{p}.{k}.snapshots", [mr["mc"][k][0], mr["mc"][k][1], mr["mc"][k][2]], [smc.get("small_update"), smc.get("large_update"), smc.get("status")])
    for cell, md in ma["dense_cells"].items():
        sd = sa["dense_cells"].get(cell, {})
        cmp(f"{arm}.dense[{cell}].label", md["label"], sd.get("label"))
        cmp(f"{arm}.dense[{cell}].counts", md["counts"], {k: v for k, v in sd.get("counts", {}).items() if k in md["counts"]})
    for cell in set(sa["dense_cells"]) - set(ma["dense_cells"]):
        diffs.append((f"{arm}.dense[{cell}] only in study", None, sa["dense_cells"][cell].get("label")))
    for cell, md in ma["dense_at_saturation"].items():
        sd = sa["dense_at_saturation"][cell]
        cmp(f"{arm}.sat[{cell}].label", md["label"], sd["label"])
        for mr, sr in zip(md["replicates"], sd["replicates"]):
            for p in ("A", "B"):
                cmp(f"{arm}.sat[{cell}].r{mr['replicate']}.d_sat.{p}", mr["d_sat"][p], sr["d_sat"][p])
            cmp(f"{arm}.sat[{cell}].r{mr['replicate']}.lengths", [mr["arm_length"], mr["dense_length"]], [sr["arm_length"], sr["dense_length"]])
for tag in ("U_P", "run"):
    cmp(f"sparse.{tag}.label", mine["sparse"][tag]["label"], sc["sparse"][tag]["label"])
    for i, (mr, sr) in enumerate(zip(mine["sparse"][tag]["ratios"], sc["sparse"][tag]["ratios"])):
        for cell in mr:
            for p in ("A", "B"):
                cmp(f"sparse.{tag}.r{i + 1}.{cell}.{p}", mr[cell][p], sr[cell][p])
ms, ss = mine["saturation"], study["saturation"]
cmp("saturation.outcome", ms["outcome"], ss["outcome"]["label"])
for arm, ma in ms["arms"].items():
    sa = ss["arms"][arm]
    cmp(f"sat.{arm}.class", ma["class"], sa["class"])
    for pn, mp in ma["pairs"].items():
        sp = sa["pairs"][pn]
        cmp(f"sat.{arm}.{pn}.class", mp["class"], sp["class"])
        cmp(f"sat.{arm}.{pn}.verdicts", mp["verdicts"], sp["verdicts"])
        for mr, sr in zip(mp.get("replicates", []), sp.get("replicates", [])):
            for p in ("A", "B"):
                if "rho" in sr.get("detail", {}):
                    cmp(f"sat.{arm}.{pn}.r{mr['replicate']}.rho.{p}", mr["rho"][p], sr["detail"]["rho"][p], 1e-9)
me, se = mine["efficiency"], study["efficiency"]
cmp("efficiency.outcome", me["outcome"], se["outcome"]["label"])
for r, mr in me["readings"].items():
    for arm, ma in mr.items():
        sa = se["readings"][r]["arms"][arm]
        cmp(f"eff.{r}.{arm}.class", ma["class"], sa["class"])
        cmp(f"eff.{r}.{arm}.dense_speed", ma["dense_speed"], sa["dense_speed"])
        for st, mstep in ma["steps"].items():
            sstep = sa["steps"][st]
            cmp(f"eff.{r}.{arm}.{st}.class", mstep["class"], sstep["class"])
            cmp(f"eff.{r}.{arm}.{st}.verdicts", mstep["verdicts"], sstep["verdicts"])
            for x, y in zip(mstep["replicates"], sstep["replicates"]):
                for side in ("u_t_small", "u_t_large"):
                    k1, k2 = x[side], y[side]
                    kind = {"known": "exact"}.get(k1[0], k1[0])
                    cmp(f"eff.{r}.{arm}.{st}.r{x['replicate']}.{side}.kind", kind, k2[0])
                    for a_, b_ in zip(k1[1:], k2[1:]):
                        if a_ is not None and b_ is not None:
                            cmp(f"eff.{r}.{arm}.{st}.r{x['replicate']}.{side}.bound", a_, b_, 1e-6)
print(f"compared {checked[0]} values; differences: {len(diffs)}")
for d in diffs[:200]:
    print("  DIFF", d[0], "| mine:", str(d[1])[:160], "| study:", str(d[2])[:160])
