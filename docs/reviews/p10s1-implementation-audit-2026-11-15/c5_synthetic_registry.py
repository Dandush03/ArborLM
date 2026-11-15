"""End-to-end check of studies/p10s1/analysis.py on the auditor's OWN synthetic run directories (record schema read from analysis.read_cell; the generator is
written here, not studies/p10s1/synthetic.py). For each scenario the auditor's independent pipeline (rules of c1_rules_independent.py plus its own wiring:
REF, leakage, MC entries from the frozen cost table, dense readings MU/MC/D-BEST, DENSE NOT READ, transitions, u_T, dense-faster) is compared with
analysis.analyze_study: every replicate verdict, step class, arm class, dense label and both outcomes. Then the report is rendered for each scenario.

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c5_synthetic_registry.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import math
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1_rules_independent as R  # noqa: E402  (auditor's own rules)

from studies.p10s1 import analysis as A  # noqa: E402  object under test
from studies.p10s1 import core  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402
from studies.p10s1 import report  # noqa: E402

U_P = 8192
PANELS = ("A", "B")
GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)
# a plausible CPU table (seconds per update): F-OQ from P9-I's rehearsal (ADR section 1 fact 7), others guessed; synthetic only
CPU = {("F-OQ", 4096): 0.010, ("F-OQ", 16384): 0.014, ("F-OQ", 65536): 0.042, ("T-OQ", 4096): 0.020, ("T-OQ", 16384): 0.026, ("T-OQ", 65536): 0.05,
       ("H8", 4096): 0.008, ("H8", 16384): 0.009, ("H8", 65536): 0.012, ("R2", 4096): 0.006, ("R2", 16384): 0.007, ("R2", 65536): 0.01,
       ("D-OQ", 4096): 0.02, ("D-OQ", 16384): 0.05, ("D-OQ", 65536): 0.16}


# ------------------------------------------------------------------------------------------------ scenario: a_use(arm, facts, slots, rep, panel, u)
class Scenario:
    def __init__(self, name, seed, kind):
        self.name, self.rng, self.kind = name, random.Random(seed), kind
        self.cache = {}
        self.dep_fail = set()
        self.leak = set()
        self.ref_fail = set()
        if kind == "random":
            for _ in range(self.rng.randint(0, 3)):
                self.dep_fail.add((self.rng.choice(["F-OQ", "T-OQ", "H8"]), self.rng.choice(core.GRID_CELLS), self.rng.randint(1, 5)))
            if self.rng.random() < 0.3:
                self.leak.add((self.rng.choice(["F-OQ", "T-OQ", "H8"]), self.rng.choice(core.GRID_CELLS), self.rng.randint(1, 5)))
            if self.rng.random() < 0.3:
                self.ref_fail.add((self.rng.choice([2048, 8192, 32768]), self.rng.randint(1, 5)))

    def params(self, arm, facts, slots, rep, panel):
        key = (arm, facts, slots, rep, panel)
        if key not in self.cache:
            k, rng = self.kind, self.rng
            if arm == "R2":
                amax, tau = 1.0, 300.0
            elif arm == "D-OQ":
                amax, tau = {"capacity": (0.2, 3000), "dense_ahead": (1.0, 500), "saturated": (0.5, 3000), "random": (rng.uniform(0, 1), rng.uniform(300, 20000)), "slow_large": (0.3, 4000)}[k]
            else:
                load = facts / slots
                if k == "capacity":
                    amax, tau = min(1.0, 0.7 / load), 1500.0
                elif k == "dense_ahead":
                    amax, tau = min(1.0, 0.7 / load), 1500.0
                elif k == "saturated":
                    amax, tau = 1.0, 800.0
                elif k == "slow_large":
                    amax, tau = min(1.0, 0.7 / load), 1500.0 * (slots / 4096) ** 0.7
                else:
                    amax, tau = min(1.0, rng.uniform(0.3, 1.2) / load), rng.uniform(300, 30000)
                if arm == "T-OQ":
                    amax *= rng.uniform(0.9, 1.0) if k == "random" else 0.97
            self.cache[key] = (amax, tau, rng.uniform(-0.004, 0.004))
        return self.cache[key]

    def a(self, arm, facts, slots, rep, panel, u):
        base = "F-OQ" if arm == "F-OQ-IVF" else arm
        amax, tau, jit = self.params(base, facts, slots, rep, panel)
        if base == "R2" and (facts, rep) in self.ref_fail:
            amax = 0.9
        x = amax * (1 - math.exp(-u / tau)) + jit
        if arm == "F-OQ-IVF":
            x *= 0.985
        return min(1.0, max(0.0, x))


def counts(n, a, *, dep_fail=False, leak=False, memory=True):
    useful = int(round(a * n))
    chance = int(round(n / 32))
    return {"n": n, "correct": useful, "useful": useful, "disabled_correct": useful if dep_fail and a >= 0.3 else chance, "shuffled_correct": chance if memory else None,
            "swap_correct": chance, "unseen_n": 2048, "unseen_correct": 600 if leak else 64}


def write(run_dir, fro, scn):
    for cell in core.registered_cells(fro.plan, dense_rates=fro.dense_rates):
        folder = run_dir / "cells" / cell.label
        ups = fro.snapshots(cell)
        n = 3 * cell.facts
        cpu = CPU[(cell.arm, cell.slots)]
        meta = {str(u): {"cpu_seconds": cpu * u, "movement": {"with_own_gradient": 1.0 * u, "without_own_gradient": 0.3 * u * (cell.slots / 4096) ** 0.3, "total": u * (1 + 0.3 * (cell.slots / 4096) ** 0.3), "share_without": 0.3 * (cell.slots / 4096) ** 0.3 / (1 + 0.3 * (cell.slots / 4096) ** 0.3)}} for u in ups}
        train = {**core.envelope("train"), "label": cell.label, "status": "completed", "snapshot_meta": meta, "identity": {"source_sha256": "x"}, "trainable_parameters": 1, "stored_parameters": 2}
        core.write_record(folder / "train.json", train)
        rep = cell.draw if cell.kind == "P" else 1
        for u in ups:
            reads = {}
            for read in (["main", "ivf"] if cell.arm == "F-OQ" else ["main"]):
                arm = "F-OQ-IVF" if read == "ivf" else cell.arm
                dep = (cell.arm, (cell.facts, cell.slots), rep) in scn.dep_fail and cell.kind == "P"
                leak = (cell.arm, (cell.facts, cell.slots), rep) in scn.leak and cell.kind == "P" and read == "main"
                panels = {p: counts(n, scn.a(arm, cell.facts, cell.slots, rep, p, u), dep_fail=dep, leak=leak, memory=cell.arm != "D-OQ") for p in PANELS}
                if u == cell.u_p and cell.arm != "D-OQ":
                    panels["A"]["robustness_correct"] = {f"drop20_{k}": int(panels["A"]["correct"] * 0.9) for k in range(3)} | {f"drop5_{k}": int(panels["A"]["correct"] * 0.97) for k in range(3)}
                r = {"panels": panels, "secondary": {h: {"n": n, "correct": int(panels["A"]["correct"] * 0.95)} for h in ("H1", "H2")}, "work": {"W": 1.0}}
                if read == "ivf":
                    r["ivf_measured"] = {"W_mean": 9000.0 + 0.02 * cell.slots, "W_p99": 12000.0}
                reads[read] = r
            core.write_record(core.eval_path(run_dir, cell.label, u), {**core.envelope("eval"), "label": cell.label, "reads": reads})
    for r in range(1, 6):
        for facts in sorted({f for f, _ in core.grid_cells(fro.plan)}):
            n = 3 * facts
            panels = {p: {"KNN-W": {"correct": int(0.3 * n), "n": n, "keys_scored_per_query": 1.0}, "KNN-W-IVF": {"correct": int(0.25 * n), "n": n, "keys_scored_per_query": 1.0}, "DICT": {"correct": n, "n": n}, "NO-MEMORY": {"n": n, "correct": n // 32}} for p in PANELS}
            core.write_record(run_dir / "baselines" / f"d{r}_f{facts}.json", {**core.envelope("baseline"), "panels": panels})
    core.write_record(run_dir / "gates.json", {**core.envelope("gates"), **{f"{g}_passed": True for g in ("g1", "g2", "g4", "g5", "g6", "g7", "g8", "g9")}})


# ------------------------------------------------------------------------------------------------ auditor's pipeline
def my_mc(cost_small, cost_large, run_small, run_large):
    r = [cost_large[m] / cost_small[m] for m in ("cpu", "madds")]
    if all(x >= 1 for x in r):
        m = max(r)
        for g in GRID:
            if g >= m - 1e-12:
                return ("OK", int(g * U_P), U_P) if g * U_P <= run_small else ("MC-SHORT", None, None)
        return ("MC-SHORT", None, None)
    if all(x <= 1 for x in r):
        m = max(1 / x for x in r)
        for g in GRID:
            if g >= m - 1e-12:
                return ("OK", U_P, int(g * U_P)) if g * U_P <= run_large else ("MC-SHORT", None, None)
        return ("MC-SHORT", None, None)
    return ("MC-AMBIGUOUS", None, None)


def run_len(arm, slots):
    return U_P if arm == "R2" else {4096: 6, 16384: 4, 65536: 2}[slots] * U_P


def my_pipeline(scn, fro, run_dir):
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
                c = counts(n, scn.a(arm, facts, slots, rep, panel, u), dep_fail=dep, leak=leak, memory=base != "D-OQ")
                o[u] = R.obs(c["n"], c["useful"], c["correct"], c["disabled_correct"], c["shuffled_correct"], c["unseen_n"], c["unseen_correct"])
            series[key] = R.Series(o, run_len(base, slots), U_P)
        return series[key]

    def ref_ok(rep, facts):
        f, n = {2048: (2048, 4096), 8192: (8192, 16384), 32768: (32768, 65536)}[facts]
        return all(S("R2", f, n, rep, p).a(U_P) >= 0.95 - 1e-12 for p in PANELS)

    def leak(arm, facts, slots, rep):
        return any(R.my_leak(o) for p in PANELS for o in S(arm, facts, slots, rep, p).o.values())

    cost = lambda arm, slots: fro.cost["F-OQ" if arm == "F-OQ-IVF" else arm][str(slots)]  # noqa: E731
    steps = {"A1": (8192, 4096, 16384), "A2": (8192, 16384, 65536), "B1": (32768, 4096, 16384), "B2": (32768, 16384, 65536)}
    trans = {"4K→16K": ["A1", "B1"], "16K→64K": ["A2", "B2"]}
    out = {"verdicts": {}, "classes": {}, "arm": {}, "dense": {}}
    mcs = {}
    for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
        step_cls = {}
        for name, (f, s, l) in steps.items():
            base = "F-OQ" if arm == "F-OQ-IVF" else arm
            mc = my_mc(cost(base, s), cost(base, l), run_len(base, s), run_len(base, l))
            mcs[f"cap|{base}|{name}"] = mc
            vs = []
            for rep in range(1, 6):
                lk = leak(arm, f, s, rep) or leak(arm, f, l, rep)
                pv = {p: R.my_capacity_panel(S(arm, f, s, rep, p), S(arm, f, l, rep, p), (mc[1], mc[2]) if mc[0] == "OK" else None, ref_ok(rep, f), lk) for p in PANELS}
                vs.append(pv["A"] if pv["A"] == pv["B"] else "PANEL-DISAGREE")
            out["verdicts"][f"{arm}|{name}"] = vs
            step_cls[name] = R.my_step_class(vs)
            out["classes"][f"{arm}|{name}"] = step_cls[name]
        a80 = all(S(arm, 32768, 65536, rep, p).a(U_P) >= 0.80 - 1e-12 for rep in range(1, 6) for p in PANELS)
        cls = R.my_arm_class(step_cls, trans, a80)
        out["arm"][arm] = cls
        # dense label
        dense_cells = set(core.arm_cells(plan, "D-OQ"))
        cells, missing = [], []
        for name, (f, s, l) in steps.items():
            if step_cls[name] != "CAPACITY STEP":
                continue
            if (f, l) not in dense_cells:
                missing.append(name)
                continue
            base = "F-OQ" if arm == "F-OQ-IVF" else arm
            mc = my_mc(cost(base, l), cost("D-OQ", l), run_len(base, l), run_len("D-OQ", l))
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
                    else:
                        rr["MC"][p] = (math.inf, 1.0, 0)
                    best = sd.istar(sd.run)[0]
                    rr["D-BEST"][p] = (ia - best, None if best <= 0 else ia / best, 0)
                reps.append(rr)
            cells.append(reps)
        if not cells:
            lab = "DENSE NOT READ"
        else:
            lab = R.my_dense(cells)["both"]
        read_trans = {t: any(step_cls[n] == "CAPACITY STEP" and n not in missing for n in ns) for t, ns in trans.items()}
        if cls == "CAPACITY_SUPPORTED" and not all(read_trans.values()):
            lab = "DENSE NOT READ"
        out["dense"][arm] = lab
    every_nl = all(out["classes"][f"{a}|{n}"] == "NOT LOADED" for a in ("F-OQ", "T-OQ") for n in steps)
    oc = R.my_outcome({a: (out["arm"][a], out["dense"][a]) for a in ("F-OQ", "T-OQ", "F-OQ-IVF")}, False, False, every_nl)
    out["capacity_outcome"] = oc
    # efficiency
    eff_cls = {}
    for arm in ("F-OQ", "T-OQ"):
        sc = {}
        for name, (f, s, l) in steps.items():
            vs = []
            for rep in range(1, 6):
                us = R.my_ut([S(arm, f, s, rep, p) for p in PANELS])
                ul = R.my_ut([S(arm, f, l, rep, p) for p in PANELS])
                lk = leak(arm, f, s, rep) or leak(arm, f, l, rep)
                vs.append(R.my_eff_step(us, ul, ref_ok(rep, f), lk, run_len(arm, s), run_len(arm, l), cost(arm, s), cost(arm, l)))
            out["verdicts"][f"eff|{arm}|{name}"] = vs
            sc[name] = R.my_eff_step_class(vs)
            out["classes"][f"eff|{arm}|{name}"] = sc[name]
        eff_cls[arm] = R.my_eff_arm(sc, trans)
        out["arm"][f"eff|{arm}"] = eff_cls[arm]
    dense_e = {}
    for arm in ("F-OQ", "T-OQ"):
        labels = []
        for name, (f, s, l) in steps.items():
            if out["classes"][f"eff|{arm}|{name}"] != "FASTER STEP":
                continue
            if (f, l) not in set(core.arm_cells(plan, "D-OQ")):
                labels.append("DENSE NOT READ")
                continue
            n4 = 0
            for rep in range(1, 6):
                ua = R.my_ut([S(arm, f, l, rep, p) for p in PANELS])
                ud = R.my_ut([S("D-OQ", f, l, rep, p) for p in PANELS])
                if all(ud[2] * cost("D-OQ", l)[m] <= 0.8 * ua[1] * cost(arm, l)[m] + 1e-12 for m in ("cpu", "madds")):
                    n4 += 1
            labels.append("DENSE FASTER" if n4 >= 4 else "DENSE NOT FASTER")
        dense_e[arm] = "DENSE FASTER" if "DENSE FASTER" in labels else ("DENSE NOT READ" if labels and all(x == "DENSE NOT READ" for x in labels) else "DENSE NOT FASTER")
    out["efficiency_outcome"] = R.my_eff_outcome(eff_cls, dense_e)
    out["mc"] = mcs
    return out


def compare(scn, root):
    cpu = {k: v for k, v in CPU.items()}
    fro = fz.Frozen.build(core.Plan(seed_block_draws=()), cpu, dense_rates={4096: 0.003, 16384: 0.003, 65536: 0.003})
    run_dir = root / scn.name
    write(run_dir, fro, scn)
    study = A.load_study(run_dir, fro)
    res = A.analyze_study(study, fro, gates=json.loads((run_dir / "gates.json").read_text()))
    mine = my_pipeline(scn, fro, run_dir)
    diffs = []
    if res["assessment"]["status"] != "COMPLETE":
        diffs.append(("status", res["assessment"]["status"]))
        return {"scenario": scn.name, "diffs": diffs}
    cap, eff = res["capacity"], res["efficiency"]
    for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
        for name in ("A1", "A2", "B1", "B2"):
            if mine["verdicts"][f"{arm}|{name}"] != cap["steps"][arm][name]["verdicts"]:
                diffs.append((f"{arm}|{name} verdicts", mine["verdicts"][f"{arm}|{name}"], cap["steps"][arm][name]["verdicts"]))
            if mine["classes"][f"{arm}|{name}"] != cap["steps"][arm][name]["class"]:
                diffs.append((f"{arm}|{name} class", mine["classes"][f"{arm}|{name}"], cap["steps"][arm][name]["class"]))
            if mine["mc"][f"cap|{'F-OQ' if arm == 'F-OQ-IVF' else arm}|{name}"][0] != cap["steps"][arm][name]["mc"]["status"]:
                diffs.append((f"{arm}|{name} mc", mine["mc"][f"cap|{'F-OQ' if arm == 'F-OQ-IVF' else arm}|{name}"], cap["steps"][arm][name]["mc"]))
        if mine["arm"][arm] != cap["arms"][arm]["class"]:
            diffs.append((f"{arm} arm class", mine["arm"][arm], cap["arms"][arm]["class"]))
        theirs_dense = cap["arms"][arm]["dense"]
        theirs_dense = "BEATS DENSE" if theirs_dense.startswith("BEATS DENSE") else theirs_dense
        if mine["dense"][arm] != theirs_dense:
            diffs.append((f"{arm} dense", mine["dense"][arm], cap["arms"][arm]["dense"]))
    for arm in ("F-OQ", "T-OQ"):
        for name in ("A1", "A2", "B1", "B2"):
            if mine["verdicts"][f"eff|{arm}|{name}"] != eff["steps"][arm][name]["verdicts"]:
                diffs.append((f"eff {arm}|{name} verdicts", mine["verdicts"][f"eff|{arm}|{name}"], eff["steps"][arm][name]["verdicts"]))
        if mine["arm"][f"eff|{arm}"] != eff["arm_classes"][arm]:
            diffs.append((f"eff {arm} arm", mine["arm"][f"eff|{arm}"], eff["arm_classes"][arm]))
    if mine["capacity_outcome"] != res["outcome"]["capacity"]["label"]:
        diffs.append(("capacity outcome", mine["capacity_outcome"], res["outcome"]["capacity"]["label"]))
    if mine["efficiency_outcome"] != res["outcome"]["efficiency"]["label"]:
        diffs.append(("efficiency outcome", mine["efficiency_outcome"], res["outcome"]["efficiency"]["label"]))
    # render the report
    core.write_record(run_dir / "analysis.json", core.jsonable({**core.envelope("analysis"), "result": res}))
    try:
        report.write_report(run_dir, run_dir / "results")
        rep = "written"
    except Exception as exc:  # noqa: BLE001
        rep = f"{type(exc).__name__}: {exc}"
    return {"scenario": scn.name, "diffs": diffs, "capacity": res["outcome"]["capacity"]["label"], "efficiency": res["outcome"]["efficiency"]["label"],
            "arm_classes": {a: cap["arms"][a]["class"] for a in cap["arms"]}, "dense": {a: cap["arms"][a]["dense"] for a in cap["arms"]}, "eff_arm": eff["arm_classes"], "report": rep,
            "mc_dense": {k: (v.status, v.small_update, v.large_update, round(v.multiplier, 3)) for k, v in fro.mc.items() if k.startswith("dense")}}


def main():
    out = []
    cov = Counter()
    with tempfile.TemporaryDirectory(prefix="p10s1-audit-c5-") as tmp:
        root = Path(tmp)
        scen = [Scenario(k, 921600 + i, k) for i, k in enumerate(("capacity", "dense_ahead", "saturated", "slow_large"))]
        scen += [Scenario(f"random{i}", 921700 + i, "random") for i in range(24)]
        for s in scen:
            r = compare(s, root)
            out.append(r)
            cov[(r.get("capacity"), r.get("efficiency"))] += 1
            print(s.name, len(r["diffs"]), r.get("capacity"), r.get("efficiency"), r.get("report"), file=sys.stderr)
    json.dump({"scenarios": out, "outcome_coverage": {str(k): v for k, v in cov.items()}, "total_diffs": sum(len(r["diffs"]) for r in out)}, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
