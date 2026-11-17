"""Compare the auditor's recomputation (mine.json) with the report's results.json, classes.csv and RESULTS.md.

Usage: python3 -I compare.py <mine.json> <run record dir>
"""
import csv, io, json, math, re, sys
from pathlib import Path

mine = json.loads(Path(sys.argv[1]).read_text())
rec = Path(sys.argv[2])
R = json.loads((rec / "results.json").read_text())["result"]
md = (rec / "RESULTS.md").read_text()
rows = []


def eq(a, b, tol=1e-9):
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is None and b is None
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    return a == b


def C(where, m, t, tol=1e-9):
    rows.append((where, m, t, eq(m, t, tol)))


CT = ("2K/4K", "8K/16K", "8K/4K")
for arm in ("A0", "A1", "A2", "A5-D"):
    for ct in CT:
        k = f"{arm}|{ct}"
        if k not in mine["arms"]:
            continue
        m, t = mine["arms"][k], R["arms"][arm][ct]
        for crit_m, crit_t in (("s0", "s0"), ("p9_criteria", "p9ii_criteria")):
            for f in ("cls", "evaluated", "successes", "failures", "draws_evaluated", "draws_succeeded", "draws_failed", "draws_not_evaluated", "per_draw_bound", "lm_flagged_cells", "lm_reduced"):
                C(f"arms/{k}/{crit_t}/{f}", m[crit_m][f], t[crit_t][f])
        C(f"arms/{k}/stable/median", m["stable_median"], t["stable"]["median"])
        C(f"arms/{k}/stable/label", "ADDRESS STABLE" if m["stable"] else None, t["stable"]["label"])
        C(f"arms/{k}/collapse_free/k", m["collapse_free_k"], t["collapse_free"]["k"])
        C(f"arms/{k}/collapse_free/n", m["cells"], t["collapse_free"]["n"])
        for cat in ("never collapsed and separated", "never collapsed, not separated", "collapsed and recovered", "collapsed and not recovered"):
            C(f"arms/{k}/categories/{cat}", m["categories"].get(cat, 0), t["categories"][cat])
        C(f"arms/{k}/information_bits/median", m["i_clip_median"], t["information_bits"]["median_of_the_smaller_panel"])
        C(f"arms/{k}/failed_conditions", {kk: sorted(v) for kk, v in m["failed_conditions"].items()}, {kk: sorted(v) for kk, v in t["failed_conditions"].items()})
        C(f"arms/{k}/sustained/cells_with_first_success", m["sustained_mean"][0], t["sustained_success"]["cells_with_first_success"])
        C(f"arms/{k}/sustained/sustained", m["sustained_mean"][1], t["sustained_success"]["sustained"])
        C(f"arms/{k}/lm/flagged", m["s0"]["lm_flagged_cells"], t["lm"]["flagged_cells"])
        if "class_at_U_s0" in m:
            C(f"arms/{k}/class_at_u", m["class_at_U_s0"], t["class_at_u"]["class"])
        if arm in ("A1", "A2"):
            C(f"arms/{k}/address_recall/median", m["recall_median_min"], t["address_recall"]["median"])
            C(f"arms/{k}/address_recall/label", "ADDRESS RECALL" if m["recall_median_min"] >= 0.90 else None, t["address_recall"]["label"])
        if ct != "8K/4K":
            C(f"arms/{k}/replication", m["replication"], t["replication"])
            C(f"arms/{k}/consistency/label", m["consistency"], t["consistency"]["label"] if t["consistency"] else None)
            C(f"arms/{k}/meets", m["meets"], t["meets"])
            C(f"arms/{k}/p9ii_class", m["p9ii_class"], (t["p9ii"] or {}).get("class") if (t["p9ii"] or {}).get("available") else None)
            if m["pooled"]:
                C(f"arms/{k}/pooled/successes", m["pooled"]["successes"], t["pooled"]["successes"])
                C(f"arms/{k}/pooled/draws", m["pooled"]["draws"], t["pooled"]["draws"])
                C(f"arms/{k}/pooled/bound", m["pooled"]["bound"], t["pooled"]["per_draw_bound"])
                C(f"arms/{k}/consistency/pooled_failed", m["pooled"]["failed"], t["consistency"]["pooled_failed"])
                C(f"arms/{k}/consistency/pooled_n", m["pooled"]["draws"], t["consistency"]["pooled_n"])
            else:
                C(f"arms/{k}/pooled/available", False, t["pooled"]["available"])
        else:
            C(f"arms/{k}/replication", "NOT COMPARABLE", t["replication"])
            C(f"arms/{k}/pooled/available", False, t["pooled"]["available"])
        if "dense" in m:
            dm, dt = m["dense"], t["dense_comparison"]
            C(f"arms/{k}/dense/label", dm["label"], dt["label"])
            C(f"arms/{k}/dense/median_ratio", dm["median_ratio"], dt["median_ratio"])
            C(f"arms/{k}/dense/median_dense_accuracy", dm["median_dense_accuracy"], dt["median_dense_accuracy"])
            C(f"arms/{k}/dense/draws_arm_higher", dm["draws_arm_higher"], dt["draws_arm_higher"])
            for d in range(1, 11):
                C(f"arms/{k}/dense/differences/{d}", dm["differences"][str(d)], dt["differences"][str(d)])
        else:
            C(f"arms/{k}/dense/absent", None, t.get("dense_comparison"))

for k, v in mine["paired"].items():
    arm, ct = k.split("|")
    for cm, ctt in (("s0", "s0"), ("p9", "p9ii")):
        t = R["paired"][arm][ct][ctt]
        for f, ft in (("d", "d"), ("x_only", "x_only"), ("a0_only", "a0_only"), ("x_successes", "x_successes"), ("a0_successes", "a0_successes"), ("p", "p_value"), ("label", "label")):
            C(f"paired/{k}/{ctt}/{ft}", v[cm][f], t[ft])
pa = R.get("paired_a2_a1") or {}
for ct, v in mine["paired_a2_a1"].items():
    m_ = re.search(rf"d\(A2 against A1\) at {re.escape(ct)} \(descriptive\): (-?\d+) \(p = ([0-9.]+)\)", md)
    C(f"RESULTS.md/d(A2,A1)/{ct}/d", v["d"], int(m_.group(1)) if m_ else None)
    C(f"RESULTS.md/d(A2,A1)/{ct}/p(3dp)", f"{v['p']:.3f}", m_.group(2) if m_ else None)

# selection, outcome, annotations
S = R["selection"]
C("selection/candidate", mine["candidate"], S["candidate"])
C("selection/also_qualifies", [f"ALSO QUALIFIES: {a}" for a in mine["also"]], S["also_qualifies"])
C("selection/qualified_4096_only", mine["qualified_4096_only"], S["qualified_4096_only"])
for arm in ("A0", "A1", "A2", "A5-D"):
    q = [ct for ct in ("2K/4K", "8K/16K") if mine["arms"][f"{arm}|{ct}"]["meets"] and mine["arms"][f"{arm}|{ct}"]["consistency"] != "INCONSISTENT ACROSS STUDIES"]
    C(f"selection/per_arm/{arm}/qualifies_at", q, S["per_arm"][arm]["qualifies_at"])
C("outcome/row", mine["outcome"][0], R["outcome"]["row"])
C("outcome/label", mine["outcome"][1], R["outcome"]["label"])
C("outcome/arm", mine["candidate"], R["outcome"]["arm"])
C("overload", mine["overload"], R["overload"])
C("record_length/label", f"RECORD-LENGTH-FREE VARIANT: {mine['record_length']}" + (" (not evidence that the record length is required)" if mine["record_length"] == "DOES NOT PASS" else ""), R["record_length"]["label"])
for ct in ("2K/4K", "8K/16K"):
    w, t = mine["wx"][ct], R["record_length"]["celltypes"][ct]
    for f in ("cls", "evaluated", "successes", "failures", "draws_evaluated", "draws_succeeded", "per_draw_bound", "lm_flagged_cells"):
        C(f"wx/{ct}/class/{f}", w["s0"][f], t["class"][f])
    C(f"wx/{ct}/stable/median", w["stable_median"], t["stable"]["median"])
    C(f"wx/{ct}/stable/label", "ADDRESS STABLE" if w["stable"] else None, t["stable"]["label"])
    C(f"wx/{ct}/auc_median", w["auc_median"], t["auc_median"])
    C(f"wx/{ct}/bits_median", w["i_clip_median"], t["bits_median"])
    C(f"wx/{ct}/meets", w["meets"], t["meets"])
    C(f"wx/{ct}/failed_conditions", {kk: sorted(v) for kk, v in w["failed_conditions"].items()}, {kk: sorted(v) for kk, v in t["failed_conditions"].items()})
P = R["probe"]
C("probe/successes", mine["probe"]["k"], P["successes"])
C("probe/draws", mine["probe"]["n"], P["draws"])
C("probe/bound", mine["probe"]["bound"], P["per_draw_bound"])
C("probe/a6_evaluated", mine["probe"]["a6_evaluated"], [P["a6_evaluated"][d] for d in ("11", "12", "13")])
for h, v in mine["hypotheses"].items():
    C(f"hypotheses/{h}", v, R["hypotheses"][h]["reading"])
C("a0_failed_cells_8k16k", mine["a0_failed_cells_8k16k"], R["a0_failed_cells_8k16k"])
C("cut3", False, R["cut3"])
for k, v in mine["a6"].items():
    ct, d = k.split("|")
    t = R["a6"][ct][d]
    C(f"a6/{k}/A", v["A"], t["accuracy_a"]); C(f"a6/{k}/B", v["B"], t["accuracy_b"]); C(f"a6/{k}/evaluated", v["evaluated"], t["evaluated"]); C(f"a6/{k}/lm_r", v["lm_r"], t["lm_relative_rise"])

# classes.csv
lines = [l for l in (rec / "classes.csv").read_text().splitlines() if not l.startswith("#")]
for row in csv.DictReader(io.StringIO("\n".join(lines))):
    k = f"{row['arm']}|{row['celltype']}"
    m = mine["arms"][k]
    C(f"csv/{k}/s0_class", m["s0"]["cls"], row["s0_class"])
    C(f"csv/{k}/p9_class", m["p9_criteria"]["cls"], row["p9ii_criteria_class"])
    C(f"csv/{k}/replication", m.get("replication", "NOT COMPARABLE"), row["replication"])
    C(f"csv/{k}/consistency", m.get("consistency") or "", row["consistency"])
    C(f"csv/{k}/address_stable", "ADDRESS STABLE" if m["stable"] else "", row["address_stable"])
    C(f"csv/{k}/evaluated", m["s0"]["evaluated"], int(row["evaluated"]))
    C(f"csv/{k}/successes", m["s0"]["successes"], int(row["successes"]))
    C(f"csv/{k}/draws_evaluated", m["s0"]["draws_evaluated"], int(row["draws_evaluated"]))
    C(f"csv/{k}/draws_succeeded", m["s0"]["draws_succeeded"], int(row["draws_succeeded"]))
    C(f"csv/{k}/per_draw_bound", f"{m['s0']['per_draw_bound']:.3f}", row["per_draw_bound"])
    C(f"csv/{k}/lm_reduced", str(m["s0"]["lm_reduced"]), row["lm_reduced"])
    C(f"csv/{k}/meets", str(bool(m.get("meets", False))), row["meets"])

# RESULTS.md class table (printed numbers)
for line in md.splitlines():
    mm = re.match(r"\| (A0|A1|A2|A5-D) \([^)]*\) \| (\S+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", line)
    if not mm:
        continue
    arm, ct = mm.group(1), mm.group(2)
    m = mine["arms"][f"{arm}|{ct}"]
    s = m["s0"]
    exp = f"{s['cls']} ({s['successes']}/{s['evaluated']} cells; {s['draws_succeeded']}/{s['draws_evaluated']} draws; per-draw bound {s['per_draw_bound']:.3f})"
    C(f"md/{arm}|{ct}/s0", exp, mm.group(3))
    s = m["p9_criteria"]
    exp = f"{s['cls']} ({s['successes']}/{s['evaluated']} cells; {s['draws_succeeded']}/{s['draws_evaluated']} draws; per-draw bound {s['per_draw_bound']:.3f})"
    C(f"md/{arm}|{ct}/p9crit", exp, mm.group(4))
    C(f"md/{arm}|{ct}/p9ii_class", m.get("p9ii_class") or "—", mm.group(5))
    C(f"md/{arm}|{ct}/replication", m.get("replication", "NOT COMPARABLE"), mm.group(6))
    C(f"md/{arm}|{ct}/consistency", m.get("consistency") or "—", mm.group(7))
    pl = m.get("pooled")
    if pl:
        txt = f"{pl['successes']} of {pl['draws']} draws succeeded (P9-II {pl['p9_succ']} of {pl['p9_draws']}; S0 {m['p9_criteria']['draws_succeeded']} of {m['p9_criteria']['draws_evaluated']}); " + ("no pooled per-draw bound is printed for A5-D" if arm == "A5-D" else f"pooled per-draw bound {pl['bound']:.3f}")
        C(f"md/{arm}|{ct}/pooled", txt, mm.group(8))
    C(f"md/{arm}|{ct}/stable", f"{'ADDRESS STABLE' if m['stable'] else 'not ADDRESS STABLE'} ({m['stable_median']:.3f})", mm.group(9))
    C(f"md/{arm}|{ct}/collapse", f"COLLAPSE-FREE: {m['collapse_free_k']} of {m['cells']} counted cells never had a collapse onset", mm.group(10))
for line in md.splitlines():
    mm = re.match(r"\| (A1|A2|A5-D) \| (\S+) \| (.+?) \| (-?\d+) \| ([0-9.]+) \| (-?\d+) \| (.+?) \|$", line)
    if mm:
        v = mine["paired"][f"{mm.group(1)}|{mm.group(2)}"]
        C(f"md/paired/{mm.group(1)}|{mm.group(2)}/label", v["s0"]["label"], mm.group(3))
        C(f"md/paired/{mm.group(1)}|{mm.group(2)}/d", v["s0"]["d"], int(mm.group(4)))
        C(f"md/paired/{mm.group(1)}|{mm.group(2)}/p", f"{v['s0']['p']:.3f}", mm.group(5))
        C(f"md/paired/{mm.group(1)}|{mm.group(2)}/d_p9", v["p9"]["d"], int(mm.group(6)))
        C(f"md/paired/{mm.group(1)}|{mm.group(2)}/label_p9", v["p9"]["label"], mm.group(7))
for line in md.splitlines():
    mm = re.match(r"\| (\S+) \| (\d+) \| ([0-9.]+) \| ([0-9.]+) \| (True|False) \|$", line)
    if mm:
        v = mine["a6"][f"{mm.group(1)}|{mm.group(2)}"]
        C(f"md/a6/{mm.group(1)}|{mm.group(2)}", (f"{v['A']:.3f}", f"{v['B']:.3f}", str(v["evaluated"])), (mm.group(3), mm.group(4), mm.group(5)))
for line in md.splitlines():
    mm = re.match(r"\| (H20-[A-Z](?: \([^)]*\))?) \| ([^|]+?) \|", line)
    if mm:
        C(f"md/hyp/{mm.group(1)}", mine["hypotheses"][mm.group(1)], mm.group(2))
# outcome block sentences
for ct, size in (("2K/4K", "4,096 slots (2K/4K)"), ("8K/16K", "16,384 slots (8K/16K)")):
    m = mine["arms"][f"A5-D|{ct}"]
    s = m["s0"]
    mm = re.search(rf"- {re.escape(size)}: S0 (\S+) \((\d+)/(\d+) cells; (\d+)/(\d+) draws; per-draw bound ([0-9.]+)\)", md)
    C(f"md/outcome/{ct}", (s["cls"], s["successes"], s["evaluated"], s["draws_succeeded"], s["draws_evaluated"], f"{s['per_draw_bound']:.3f}"), tuple(int(x) if x.isdigit() else x for x in mm.groups()) if mm else None)
    mm = re.search(rf"- {re.escape(size)}: ADDRESS STABLE \(median ([0-9.]+)\); COLLAPSE-FREE: (\d+) of (\d+)", md)
    C(f"md/outcome/{ct}/stable+cf", (f"{m['stable_median']:.3f}", str(m["collapse_free_k"]), str(m["cells"])), mm.groups() if mm else None)
    mm = re.search(rf"- {re.escape(size)}: i = ([0-9.]+) bits per fact", md)
    C(f"md/outcome/{ct}/i", f"{m['i_clip_median']:.3f}", mm.group(1) if mm else None)
for arm in ("A0", "A1", "A2", "A5-D"):
    for ct in CT:
        k = f"{arm}|{ct}"
        if k not in mine["arms"]:
            continue
        mm = re.search(rf"- {re.escape(arm)} at {re.escape(ct)}: i median ([0-9.]+) bits", md)
        C(f"md/{k}/i", f"{mine['arms'][k]['i_clip_median']:.3f}", mm.group(1) if mm else None)
        mm = re.search(rf"- {re.escape(arm)} at {re.escape(ct)}, readout at U: (\S+) —", md)
        if "class_at_U_s0" in mine["arms"][k]:
            C(f"md/{k}/class_at_U", mine["arms"][k]["class_at_U_s0"], mm.group(1) if mm else None)
wxm = re.search(r"- WX at 2K/4K: (\S+) \((\d+)/10 cells; .*?median ([0-9.]+); i median ([0-9.]+)", md)
C("md/wx/2K/4K", (mine["wx"]["2K/4K"]["s0"]["cls"], str(mine["wx"]["2K/4K"]["s0"]["successes"]), f"{mine['wx']['2K/4K']['auc_median']:.3f}", f"{mine['wx']['2K/4K']['i_clip_median']:.3f}"), wxm.groups() if wxm else None)
wxm = re.search(r"- WX at 8K/16K: (\S+) \((\d+)/10 cells; .*?median ([0-9.]+); i median ([0-9.]+)", md)
C("md/wx/8K/16K", (mine["wx"]["8K/16K"]["s0"]["cls"], str(mine["wx"]["8K/16K"]["s0"]["successes"]), f"{mine['wx']['8K/16K']['auc_median']:.3f}", f"{mine['wx']['8K/16K']['i_clip_median']:.3f}"), wxm.groups() if wxm else None)

bad = [r for r in rows if not r[3]]
print("comparisons", len(rows), "disagreements", len(bad))
for r in bad:
    print("DISAGREE", r[0], "| mine:", json.dumps(r[1], default=str)[:300], "| report:", json.dumps(r[2], default=str)[:300])
Path(sys.argv[1]).with_name("comparisons.tsv").write_text("\n".join(f"{r[0]}\t{json.dumps(r[1], default=str)}\t{json.dumps(r[2], default=str)}\t{'AGREE' if r[3] else 'DISAGREE'}" for r in rows) + "\n")
