"""Auditor's per-case tables for the P8 results audit (Claude Opus 5.5). Not Astra validation, not
human approval.

Reads raw eval.json / sim.json only. Loads the auditor's own frozen pre-freeze tool
(independent_recompute_p8.py, sha256 dc3e7269...acb, by path, unchanged) for the m / E / OLS /
classification code, and nothing from ``arborlm``. Adds:
  * per-case descriptive means (final NLL, gain, association effect, N_eff, distinct slots,
    context breadth) for all 10 cases and both panels;
  * the reasons any E-ratio / adjusted E-ratio is undefined (cells with null mean < 0.05 under
    L-FREQ; x-range overlap);
  * each quality-guard condition separately;
  * for C04 and C05 (registered output INCOMPLETE): the evaluation-only quantities (quality guard
    and U-ratio, which need no simulation record) and what rules 1-2 of section 7.4 WOULD give.
    This is a NON-REGISTERED DESCRIPTIVE READING.

Usage: python -I results_tables_p8.py --eval-run E --sim-run S --out tables.json
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "p8-preflight-2026-11-14" / "independent_recompute_p8.py"
TOOL_SHA = "dc3e7269976b6fdcb8accf5189ab5709f1db9b94bf03b73c3d274b655e6f1acb"


def load_tool() -> Any:
    assert hashlib.sha256(TOOL.read_bytes()).hexdigest() == TOOL_SHA, "frozen tool changed"
    spec = importlib.util.spec_from_file_location("rec", TOOL)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def f(x: Any) -> Any:
    if isinstance(x, Fraction):
        return float(x)
    if isinstance(x, dict):
        return {k: f(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [f(v) for v in x]
    return x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-run", type=Path, required=True)
    ap.add_argument("--sim-run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    R = load_tool()
    labels = [R.label(b, o, s, c) for b, o in R.PARENTS for s in R.SEEDS for c in R.CASES]
    ev = {lab: json.loads((a.eval_run / "cells" / lab / "eval.json").read_text()) for lab in labels}
    sm = {}
    for lab in labels:
        p = a.sim_run / "cells" / lab / "sim.json"
        if p.is_file():
            sm[lab] = json.loads(p.read_text())
    cells_full, missing = R.load(a.eval_run, a.sim_run)
    # evaluation-only cells: every cell with a completed eval.json (sim dict empty)
    ecells = {lab: R.Cell(ev[lab], sm.get(lab, {})) for lab in labels if ev[lab]["outcome"] == "completed"}
    out: dict[str, Any] = {"eval_completed": len(ecells), "sim_completed": len(sm), "missing": missing, "cases": {}}

    for case in R.CASES:
        ce: dict[str, Any] = {}
        for p in R.PANELS:
            labs = [R.label(b, o, s, case) for b, o in R.PARENTS for s in R.SEEDS]
            C = [ecells[x] for x in labs]
            d: dict[str, Any] = {
                "nll_final_mean": f(R.mean([c.nll(p) for c in C])),
                "nll_step0_mean": f(R.mean([R.F(c.ev["nll"]["step0"]["enabled"][p]) for c in C])),
                "gain_mean": f(R.mean([c.gain(p) for c in C])),
                "assoc_mean": f(R.mean([c.assoc(p) for c in C])),
                "n_eff_mean": sum(c.neff(p) for c in C) / 6,
                "n_eff_per_cell": {x: c.neff(p) for x, c in zip(labs, C)},
                "distinct_slots_mean": sum(c.ev["traces"][p]["utilization"]["distinct_slots"] for c in C) / 6,
                "distinct_slots_per_cell": {x: c.ev["traces"][p]["utilization"]["distinct_slots"] for x, c in zip(labs, C)},
                "context_breadth_mean": sum(c.ev["traces"][p]["utilization"]["context_breadth_mean"] for c in C) / 6,
                "x_range": [float(min(c.x(p) for c in C)), float(max(c.x(p) for c in C))],
            }
            # null means per cell (sim-complete cells only)
            nulls = {}
            for x in labs:
                if x in cells_full:
                    cc = cells_full[x]
                    nulls[x] = {f"R{r}|C{cap}|{t}": float(R.mean([cc.m(p, s, "L-FREQ", r, cap, t) for s in R.NULLS])) for r, cap, t in R.CONDS}
                else:
                    nulls[x] = "no sim.json"
            d["null_LFREQ_mean_per_cell"] = nulls
            d["cells_null_below_floor"] = {
                k: sorted(x for x, v in nulls.items() if isinstance(v, dict) and v[k] < 0.05)
                for k in [f"R{r}|C{cap}|{t}" for r, cap, t in R.CONDS]
            }
            if case in R.BASELINE:
                ref = R.BASELINE[case]
                pairs = [((b, o, s), ecells[R.label(b, o, s, case)], ecells[R.label(b, o, s, ref)]) for b, o in R.PARENTS for s in R.SEEDS]
                q = R.quality(pairs, p)
                q["conditions"] = {
                    "mean_delta_ok": q["delta_nll_mean"] <= R.QD,
                    "at_most_one_pair_above_ok": q["pairs_above"] <= 1,
                    "gain_retention_ok": q["gain_retention"] is not None and q["gain_retention"] >= R.RET,
                    "association_retention_ok": q["association_retention"] is not None and q["association_retention"] >= R.RET,
                }
                q["delta_per_pair"] = [float(C_.nll(p) - B_.nll(p)) for _, C_, B_ in pairs]
                rule12 = R.QF if not q["quality_passes"] else (R.COL if q["u_ratio"] is not None and q["u_ratio"] < R.UCOL else "rules 1-2 do not fire")
                q["rules_1_2_reading_eval_only"] = rule12
                d["quality_eval_only"] = f(q)
                comp = R.compare(cells_full, case, ref, p)
                d["registered_status"] = comp["status"]
                if comp["status"] == "complete":
                    d["conditions_LCOAX"] = f(comp["tags"]["L-COAX"])
                    if "L-BCOAX" in comp["tags"]:
                        d["conditions_LBCOAX"] = f(comp["tags"]["L-BCOAX"])
                    d["class"] = R.classify(comp)
                else:
                    d["class"] = R.INC
                    d["missing"] = comp["missing"]
                    # descriptive: M-ratio on the complete pairs only (NOT registered)
                # versus C01 and flat counterpart: delta NLL and U-ratio (eval only)
                for nm, rf in (("c01", "C01"), ("flat_counterpart", R.FLAT_CP.get(case))):
                    if rf is None or rf == case:
                        continue
                    pr = [((b, o, s), ecells[R.label(b, o, s, case)], ecells[R.label(b, o, s, rf)]) for b, o in R.PARENTS for s in R.SEEDS]
                    qq = R.quality(pr, p)
                    d[f"vs_{nm}_eval_only"] = {"ref": rf, "delta_nll_mean": float(qq["delta_nll_mean"]), "u_ratio": qq["u_ratio"]}
            ce[p] = d
        out["cases"][case] = ce
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str))
    # compact console table
    for case in R.CASES:
        for p in R.PANELS:
            d = out["cases"][case][p]
            line = f"{case} {p} nll={d['nll_final_mean']:.6f} gain={d['gain_mean']:.6f} assoc={d['assoc_mean']:.6f} neff={d['n_eff_mean']:.2f} dist={d['distinct_slots_mean']:.2f} x=[{d['x_range'][0]:.3f},{d['x_range'][1]:.3f}]"
            if "quality_eval_only" in d:
                q = d["quality_eval_only"]
                line += f" dNLL={q['delta_nll_mean']:+.6f} above={q['pairs_above']} gret={q['gain_retention']} aret={q['association_retention']} U={q['u_ratio']:.4f} guard={q['quality_passes']} {q['rules_1_2_reading_eval_only']} class={d['class']}"
                for k, v in d.get("conditions_LCOAX", {}).items():
                    line += f"\n    {k}: M={v['m_ratio']} E={v['e_ratio']} rho={v['rho_adj']} ({v.get('rho_adj_reason')}) pm={v['pairs_m_lower']} pe={v['pairs_e_lower']} par={v['parents_e_below_one']}"
                bel = {k: v for k, v in d["cells_null_below_floor"].items() if v}
                if bel:
                    line += f"\n    null<0.05: {bel}"
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
