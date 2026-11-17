"""Re-check of the predecessor's end-to-end comparison (../c5_synthetic_registry.py) after the section 22 rulings: the predecessor's own run-directory writer and
scenarios (imported from c5), my own pipeline updated for (g) DEP at every snapshot, M5 DENSE NOT ESTABLISHED, (h) either-panel blocking labels, m1 (DENSE AHEAD
survives the DENSE NOT READ override), m13 (a directed no-loaded transition), (k)/m3 DENSE SPEED UNDECIDED, compared with analysis.analyze_study; then the report is
rendered for each scenario and searched for the DENSE MATCHES sentence and the matched-updates text.

Run (worktree root): TMPDIR=<scratch> PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/recheck/r6_synthetic_registry_updated.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import c1_rules_independent as R  # noqa: E402
import c5_synthetic_registry as P  # noqa: E402  predecessor's writer, scenarios, MC
import r1_rules_updated as U  # noqa: E402  my updated rules

from studies.p10s1 import analysis as A  # noqa: E402  object under test
from studies.p10s1 import core  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402
from studies.p10s1 import report  # noqa: E402

PANELS = ("A", "B")
U_P = P.U_P
STEPS = {"A1": (8192, 4096, 16384), "A2": (8192, 16384, 65536), "B1": (32768, 4096, 16384), "B2": (32768, 16384, 65536)}
TRANS = {"4K→16K": ["A1", "B1"], "16K→64K": ["A2", "B2"]}


def my_ut_panel(series):
    return U_ut(R.my_ut([series]))


def U_ut(t):
    return t


def my_pipeline(scn, fro, directed=()):
    plan = fro.plan
    series = {}

    def S(arm, facts, slots, rep, panel):
        key = (arm, facts, slots, rep, panel)
        if key not in series:
            base = "F-OQ" if arm == "F-OQ-IVF" else arm
            cell = core.make_cell("P", base, facts, slots, rep, 2100 + rep)
            ups = fro.snapshots(cell)
            n = 3 * facts
            dep = (base, (facts, slots), rep) in scn.dep_fail
            leak = (base, (facts, slots), rep) in scn.leak and arm != "F-OQ-IVF"
            o = {}
            for u in ups:
                c = P.counts(n, scn.a(arm, facts, slots, rep, panel, u), dep_fail=dep, leak=leak, memory=base != "D-OQ")
                o[u] = R.obs(c["n"], c["useful"], c["correct"], c["disabled_correct"], c["shuffled_correct"], c["unseen_n"], c["unseen_correct"])
            series[key] = R.Series(o, P.run_len(base, slots), U_P)
        return series[key]

    def ref_ok(rep, facts):
        f, n = {2048: (2048, 4096), 8192: (8192, 16384), 32768: (32768, 65536)}[facts]
        return all(S("R2", f, n, rep, p).a(U_P) >= 0.95 - 1e-12 for p in PANELS)

    def leak(arm, facts, slots, rep):
        return any(R.my_leak(o) for p in PANELS for o in S(arm, facts, slots, rep, p).o.values())

    cost = lambda arm, slots: fro.cost["F-OQ" if arm == "F-OQ-IVF" else arm][str(slots)]  # noqa: E731
    out = {"verdicts": {}, "classes": {}, "arm": {}, "dense": {}}
    for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
        step_cls = {}
        for name, (f, s, l) in STEPS.items():
            base = "F-OQ" if arm == "F-OQ-IVF" else arm
            mc = P.my_mc(cost(base, s), cost(base, l), P.run_len(base, s), P.run_len(base, l))
            vs = []
            for rep in range(1, 6):
                lk = leak(arm, f, s, rep) or leak(arm, f, l, rep)
                pv = {p: U.my_capacity_panel(S(arm, f, s, rep, p), S(arm, f, l, rep, p), (mc[1], mc[2]) if mc[0] == "OK" else None, ref_ok(rep, f), lk) for p in PANELS}
                vs.append(pv["A"] if pv["A"] == pv["B"] else "PANEL-DISAGREE")
            out["verdicts"][f"{arm}|{name}"] = vs
            step_cls[name] = R.my_step_class(vs)
            out["classes"][f"{arm}|{name}"] = step_cls[name]
        # m13: steps of a directed transition count as NOT LOADED
        eff_cls = {n: ("NOT LOADED" if any(n in TRANS[t] for t in directed) else c) for n, c in step_cls.items()}
        a80 = all(S(arm, 32768, 65536, rep, p).a(U_P) >= 0.80 - 1e-12 for rep in range(1, 6) for p in PANELS)
        cls = R.my_arm_class(eff_cls, TRANS, a80)
        out["arm"][arm] = cls
        dense_cells = set(core.arm_cells(plan, "D-OQ"))
        cells, missing = [], []
        for name, (f, s, l) in STEPS.items():
            if step_cls[name] != "CAPACITY STEP":
                continue
            if (f, l) not in dense_cells:
                missing.append(name)
                continue
            base = "F-OQ" if arm == "F-OQ-IVF" else arm
            mc = P.my_mc(cost(base, l), cost("D-OQ", l), P.run_len(base, l), P.run_len("D-OQ", l))
            reps = []
            for rep in range(1, 6):
                rr = {"MU": {}, "MC": {}, "D-BEST": {}}
                for p in PANELS:
                    sa, sd = S(arm, f, l, rep, p), S("D-OQ", f, l, rep, p)
                    ia, idn = sa.i(U_P), sd.i(U_P)
                    rr["MU"][p] = (ia - idn, None if idn <= 0 else ia / idn, 0)
                    if mc[0] == "OK":
                        ja, jd = sa.i(mc[1]), sd.i(mc[2])
                        rr["MC"][p] = (ja - jd, None if jd <= 0 else ja / jd, 0)
                    best = sd.istar(sd.run)[0]
                    rr["D-BEST"][p] = (ia - best, None if best <= 0 else ia / best, 0)
                reps.append(rr)
            cells.append((reps, mc[0]))
        lab = "DENSE NOT READ" if not cells else U.my_dense(cells)
        read_trans = {t: any(step_cls[n] == "CAPACITY STEP" and n not in missing for n in ns) for t, ns in TRANS.items()}
        if cls == "CAPACITY_SUPPORTED" and not all(read_trans.values()) and lab != "DENSE AHEAD":
            lab = "DENSE NOT READ"
        out["dense"][arm] = lab
    every_nl = all(out["classes"][f"{a}|{n}"] == "NOT LOADED" for a in ("F-OQ", "T-OQ") for n in STEPS)
    out["capacity_outcome"] = U.my_outcome({a: (out["arm"][a], out["dense"][a]) for a in ("F-OQ", "T-OQ", "F-OQ-IVF")}, False, False, tuple(directed) or (("x",) if every_nl else ()))
    # efficiency
    eff_arm = {}
    for arm in ("F-OQ", "T-OQ"):
        sc = {}
        for name, (f, s, l) in STEPS.items():
            vs = []
            for rep in range(1, 6):
                us = R.my_ut([S(arm, f, s, rep, p) for p in PANELS])
                ul = R.my_ut([S(arm, f, l, rep, p) for p in PANELS])
                lk = leak(arm, f, s, rep) or leak(arm, f, l, rep)
                vs.append(R.my_eff_step(us, ul, ref_ok(rep, f), lk, P.run_len(arm, s), P.run_len(arm, l), cost(arm, s), cost(arm, l)))
            out["verdicts"][f"eff|{arm}|{name}"] = vs
            sc[name] = R.my_eff_step_class(vs)
            out["classes"][f"eff|{arm}|{name}"] = sc[name]
        eff_arm[arm] = R.my_eff_arm(sc, TRANS)
        out["arm"][f"eff|{arm}"] = eff_arm[arm]
    dense_e = {}
    for arm in ("F-OQ", "T-OQ"):
        faster = [n for n in STEPS if out["classes"][f"eff|{arm}|{n}"] == "FASTER STEP"]
        if eff_arm[arm] != "EFFICIENCY_SUPPORTED" and not faster:
            continue
        labels = []
        for name in faster:
            f, s, l = STEPS[name]
            if (f, l) not in set(core.arm_cells(plan, "D-OQ")):
                labels.append("DENSE NOT READ")
                continue
            arm_ut = [[R.my_ut([S(arm, f, l, rep, p)])[:3] for p in PANELS] for rep in range(1, 6)]
            d_ut = [[R.my_ut([S("D-OQ", f, l, rep, p)])[:3] for p in PANELS] for rep in range(1, 6)]
            labels.append(U.my_dense_faster(arm_ut, d_ut, cost(arm, l), cost("D-OQ", l)))
        if "DENSE FASTER" in labels:
            dense_e[arm] = "DENSE FASTER"
        elif "DENSE SPEED UNDECIDED" in labels:
            dense_e[arm] = "DENSE SPEED UNDECIDED"
        elif labels and all(x == "DENSE NOT READ" for x in labels):
            dense_e[arm] = "DENSE NOT READ"
        else:
            dense_e[arm] = "DENSE NOT FASTER"
    out["dense_eff"] = dense_e
    out["efficiency_outcome"] = R.my_eff_outcome(eff_arm, dense_e)
    return out


def compare(scn, root, directed=()):
    fro = fz.Frozen.build(core.Plan(seed_block_draws=()), dict(P.CPU), dense_rates={4096: 0.003, 16384: 0.003, 65536: 0.003}, no_loaded_transitions=list(directed))
    run_dir = root / (scn.name + ("-directed" if directed else ""))
    P.write(run_dir, fro, scn)
    study = A.load_study(run_dir, fro)
    res = A.analyze_study(study, fro, gates=json.loads((run_dir / "gates.json").read_text()))
    mine = my_pipeline(scn, fro, directed)
    diffs = []
    if res["assessment"]["status"] != "COMPLETE":
        return {"scenario": scn.name, "diffs": [("status", res["assessment"]["status"])]}
    cap, eff = res["capacity"], res["efficiency"]
    for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
        for name in STEPS:
            if mine["verdicts"][f"{arm}|{name}"] != cap["steps"][arm][name]["verdicts"]:
                diffs.append((f"{arm}|{name} verdicts", mine["verdicts"][f"{arm}|{name}"], cap["steps"][arm][name]["verdicts"]))
            if mine["classes"][f"{arm}|{name}"] != cap["steps"][arm][name]["class"]:
                diffs.append((f"{arm}|{name} class", mine["classes"][f"{arm}|{name}"], cap["steps"][arm][name]["class"]))
        if mine["arm"][arm] != cap["arms"][arm]["class"]:
            diffs.append((f"{arm} arm class", mine["arm"][arm], cap["arms"][arm]["class"]))
        th = cap["arms"][arm]["dense"]
        th = "BEATS DENSE" if th.startswith("BEATS DENSE") else th
        if mine["dense"][arm] != th:
            diffs.append((f"{arm} dense", mine["dense"][arm], cap["arms"][arm]["dense"]))
    for arm in ("F-OQ", "T-OQ"):
        for name in STEPS:
            if mine["verdicts"][f"eff|{arm}|{name}"] != eff["steps"][arm][name]["verdicts"]:
                diffs.append((f"eff {arm}|{name} verdicts", mine["verdicts"][f"eff|{arm}|{name}"], eff["steps"][arm][name]["verdicts"]))
        if mine["arm"][f"eff|{arm}"] != eff["arm_classes"][arm]:
            diffs.append((f"eff {arm} arm", mine["arm"][f"eff|{arm}"], eff["arm_classes"][arm]))
        if arm in mine["dense_eff"] and mine["dense_eff"][arm] != eff["dense"].get(arm):
            diffs.append((f"eff {arm} dense", mine["dense_eff"][arm], eff["dense"].get(arm)))
    th_cap = res["outcome"]["capacity"]["label"]
    if mine["capacity_outcome"].split(" (")[0] != th_cap.split(" (")[0] and not (mine["capacity_outcome"].startswith("CAPACITY NOT TESTED") and th_cap.startswith("CAPACITY NOT TESTED")):
        diffs.append(("capacity outcome", mine["capacity_outcome"], th_cap))
    if mine["efficiency_outcome"] != res["outcome"]["efficiency"]["label"]:
        diffs.append(("efficiency outcome", mine["efficiency_outcome"], res["outcome"]["efficiency"]["label"]))
    core.write_record(run_dir / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": res}))
    try:
        text = report.write_report(run_dir, run_dir / "results")[1].read_text()
        rep = "written"
    except Exception as exc:  # noqa: BLE001
        text, rep = "", f"{type(exc).__name__}: {exc}"
    dense_labels = {a: cap["arms"][a]["dense"] for a in cap["arms"]}
    return {
        "scenario": scn.name + (f" (directed {directed})" if directed else ""), "diffs": diffs, "capacity": th_cap, "capacity_printed": res["outcome"]["capacity"]["printed"], "reading": res["outcome"]["capacity"].get("reading"),
        "efficiency": res["outcome"]["efficiency"]["label"], "arm_classes": {a: cap["arms"][a]["class"] for a in cap["arms"]}, "dense": dense_labels, "report": rep,
        "report_has_DENSE_MATCHES_sentence": "retained as much" in text, "report_has_matched_updates_text": "matched updates (descriptive" in text,
        "analysis_has_DENSE_MATCHES_sentence": any(cap["arms"][a].get("dense_matches_sentence") for a in cap["arms"]),
        "arms_labelled_DENSE_MATCHES": [a for a, v in dense_labels.items() if v == "DENSE MATCHES"],
        "arms_NOT_ESTABLISHED_without_MU_text_in_report": [a for a, v in dense_labels.items() if v.startswith(U.NE) and not any(t.split(" matched updates")[0] + " matched updates" in text for t in cap["arms"][a]["dense_detail"].get("mu_text", []))],
    }


def main():
    out, cov = [], Counter()
    with tempfile.TemporaryDirectory(prefix="p10s1-recheck-r6-") as tmp:
        root = Path(tmp)
        scen = [P.Scenario(k, 921600 + i, k) for i, k in enumerate(("capacity", "dense_ahead", "saturated", "slow_large"))]
        scen += [P.Scenario(f"random{i}", 921700 + i, "random") for i in range(24)]
        for s in scen:
            r = compare(s, root)
            out.append(r)
            cov[(r.get("capacity"), r.get("efficiency"))] += 1
            print(s.name, len(r["diffs"]), r.get("capacity"), r.get("efficiency"), r.get("report"), file=sys.stderr)
        r = compare(P.Scenario("capacity", 921600, "capacity"), root, directed=("16K→64K",))
        out.append(r)
        print("capacity directed", len(r["diffs"]), r.get("capacity"), file=sys.stderr)
    json.dump({"scenarios": out, "outcome_coverage": {str(k): v for k, v in cov.items()}, "total_diffs": sum(len(r["diffs"]) for r in out)}, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
