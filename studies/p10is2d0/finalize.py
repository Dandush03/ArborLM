# ruff: noqa: E501
"""From the per-pass and per-cell records to the readings, the decomposition, the fixed wording and the report (ADR-0035 sections 5.3, 6, 7, 12). Pure over the records and Part T's registry: nothing is computed
that the ADR does not name; no interpretation beyond the fixed wording. The report is written by this code from a fixed template after the last pass."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from studies.p10is2.quantities import Thresholds, gap

from . import passes as P
from . import report as Rep

SCALE_ARMS = (("M-sep", False), ("E-table", False), ("D-append", True), ("D-seq", True), ("D-sep", False), ("M-seq", True), ("M-ii", True), ("M-joint", False))


def load_json(p: Path) -> Any:
    return json.loads(p.read_text())


def load_passes(out: Path) -> dict[tuple[int, str, str, str, str], dict[str, Any]]:
    d: dict[tuple[int, str, str, str, str], dict[str, Any]] = {}
    for t in P.main_tasks():
        if t["kind"] == "pass":
            p = P.record_path(out, t["id"])
            if p.is_file():
                d[(t["rep"], t["order"], t["role"], t["store"], t["cond"])] = load_json(p)
    return d


def fmt(x: float | None, nd: int = 4) -> str:
    return "n/a" if x is None else f"{x:+.{nd}f}"


def fmt_u(x: float | None, nd: int = 4) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def build_records(out: Path, registry: Mapping[str, float], th: Thresholds) -> dict[str, Any]:
    ps = load_passes(out)
    expected = [(t["rep"], t["order"], t["role"], t["store"], t["cond"]) for t in P.main_tasks() if t["kind"] == "pass"]
    missing = [k for k in expected if k not in ps]
    rec: dict[str, Any] = {"passes_expected": len(expected), "passes_present": len(ps), "missing": [list(k) for k in missing], "cells": {}}
    if missing:
        return rec  # INCOMPLETE: no table, no word
    for rep, order in P.cells():
        first, second = P.PANEL[order[0]], P.PANEL[order[1]]
        s0 = {c: registry[f"S0|-|-|s:{P.PANEL[c]}"] for c in "AB"}
        te = {c: registry[f"TEACHER|-|-|s:{P.PANEL[c]}"] for c in "AB"}
        cap1, cap2 = order[0], order[1]

        def g(s: float, cap: str, s0: dict[str, float] = s0, te: dict[str, float] = te) -> float | None:
            return gap(s, s0[cap], te[cap], th.gap_denominator_min)

        cell: dict[str, Any] = {"panels": {"first": first, "second": second}, "passes": {}}
        for role, cap, plist in (("first", cap1, P.FIRST_PASSES), ("second", cap2, P.SECOND_PASSES)):
            ref_store, ref_cond = P.reference_for(role)
            ref = ps[(rep, order, role, ref_store, ref_cond)]
            for store, cond in plist:
                r = ps[(rep, order, role, store, cond)]
                differs = sum(1 for a, b in zip(r["sequences"], ref["sequences"], strict=True) if a != b) / len(r["sequences"])
                cell["passes"][f"{role}|{store}|{cond}"] = {"s": r["mean"], "G": g(r["mean"], cap), "differs_from_reference": differs, "reference": f"{ref_store}|{ref_cond}", "contrast_vs_reference": Rep.paired_contrast(r["items"], ref["items"])}
        it = {k: ps[(rep, order, "first", st, c)]["items"] for k, (st, c) in {"M1": ("M1", "a"), "a_app": ("append", "a"), "d1_app": ("append", "d1"), "a": ("final", "a"), "b1": ("final", "b1"), "c": ("final", "c"), "d1": ("final", "d1"), "e1": ("final", "e1"), "g1": ("final", "g1")}.items()}
        sm = {k: ps[(rep, order, "first", st, c)]["mean"] for k, (st, c) in {"M1": ("M1", "a"), "a_app": ("append", "a"), "d1_app": ("append", "d1"), "a": ("final", "a"), "b1": ("final", "b1"), "c": ("final", "c"), "d1": ("final", "d1"), "e1": ("final", "e1"), "g1": ("final", "g1")}.items()}
        f_reg = registry[f"M1|{order}|{rep}|s:{first}"] - registry[f"M-append|{order}|{rep}|s:{first}"]
        dec = Rep.decompose(sm, registered_f=f_reg)
        den1 = te[cap1] - s0[cap1]
        dec["G_units"] = {k: dec[k] / den1 for k in ("T", "i", "ii", "iii", "values_first_values", "values_first_competition", "interaction")} if den1 >= th.gap_denominator_min else None
        dec["contrasts"] = {name: Rep.paired_contrast(it[x], it[y]) for name, (x, y) in {"T": ("b1", "a"), "i": ("b1", "d1"), "ii": ("d1", "e1"), "iii": ("e1", "a"), "values_first_values": ("b1", "g1"), "values_first_competition": ("g1", "a")}.items()}
        cell["decomposition"] = dec
        app = Rep.decompose_append(sm["M1"], sm["d1_app"], sm["a_app"])
        app["contrasts"] = {"T": Rep.paired_contrast(it["M1"], it["a_app"]), "i": Rep.paired_contrast(it["M1"], it["d1_app"]), "ii": Rep.paired_contrast(it["d1_app"], it["a_app"])}
        app["competition_final_minus_append"] = (dec["i"] + dec["ii"]) - (app["i"] + app["ii"])
        cell["append_point"] = app
        s2 = {k: ps[(rep, order, "second", "final", k)]["mean"] for k in ("a", "b2", "c", "d2", "e2", "g2", "e1")}
        i2 = {k: ps[(rep, order, "second", "final", k)]["items"] for k in ("a", "b2", "c", "d2", "e2", "g2", "e1")}
        d2 = Rep.decompose({"b1": s2["b2"], "d1": s2["d2"], "e1": s2["e2"], "a": s2["a"], "g1": s2["g2"]})
        d2["contrasts"] = {name: Rep.paired_contrast(i2[x], i2[y]) for name, (x, y) in {"T": ("b2", "a"), "i": ("b2", "d2"), "ii": ("d2", "e2"), "iii": ("e2", "a"), "values_first_values": ("b2", "g2"), "values_first_competition": ("g2", "a")}.items()}
        d2["stage2_switched_off_trained_keys"] = {"s_e1": s2["e1"], "s_a_minus_s_e1": s2["a"] - s2["e1"], "G_e1": g(s2["e1"], cap2), "contrast_a_minus_e1": Rep.paired_contrast(i2["a"], i2["e1"])}
        cell["second_capability_effect_of_stage1_rows"] = d2
        m1_g = g(sm["M1"], cap1)
        evaluable = m1_g is not None and m1_g >= th.first_not_acquired_g
        ret: dict[str, Any] = {}
        for x in ("c", "g1"):
            fx = sm["M1"] - sm[x]
            gx = g(sm[x], cap1)
            rho = None if (gx is None or m1_g is None or m1_g == 0) else gx / m1_g
            word = Rep.counterfactual_ret(fx, rho, evaluable, th.ret_forgetting_max, th.ret_rho_min)
            ret[x] = {"F": fx, "rho": rho, "evaluable": evaluable, "word": f"COUNTERFACTUAL RET ARITHMETIC: {word}", "second_capability_cost_vs_c": s2["a"] - s2["c"], "G_second_under_c": g(s2["c"], cap2), "G_second_a": g(s2["a"], cap2), "second_capability_cost_vs_g2": s2["a"] - s2["g2"], "G_second_under_g2": g(s2["g2"], cap2)}
        cell["counterfactual_ret"] = ret
        scale: dict[str, Any] = {}
        for role, cap, pan in (("first", cap1, first), ("second", cap2, second)):
            row: dict[str, Any] = {"S0": s0[cap], "TEACHER": te[cap], "M1_registered": registry.get(f"M1|{order}|{rep}|s:{pan}"), "M-append_registered": registry.get(f"M-append|{order}|{rep}|s:{pan}")}
            for arm, has_order in SCALE_ARMS:
                row[arm] = registry.get(f"{arm}|{order if has_order else '-'}|{rep}|s:{pan}")
            scale[role] = row
        cell["registered_scale"] = scale
        cell["key"] = f"r{rep}/{order}"
        rec["cells"][f"r{rep}/{order}"] = cell
    cells = list(rec["cells"].values())
    comp = [c["decomposition"]["shares"]["competition_path"] for c in cells]
    val = [c["decomposition"]["shares"]["values_path"] for c in cells]
    comp_vf = [c["decomposition"]["shares"]["competition_values_first"] for c in cells]
    val_vf = [c["decomposition"]["shares"]["values_values_first"] for c in cells]
    w_path, w_vf = Rep.summary_word(comp, val), Rep.summary_word(comp_vf, val_vf)
    totals = [c["decomposition"]["T"] for c in cells]
    rec["words"] = {"path_order": w_path, "values_first_order": w_vf, "final": Rep.final_wording(w_path, w_vf, [c["decomposition"]["interaction"] for c in cells], totals), "cells_with_nonpositive_T": [c["key"] for c in cells if not c["decomposition"]["T"] > 0]}
    keys = ("T", "i", "ii", "iii", "values_first_values", "values_first_competition", "interaction")
    rec["means_beside_cells"] = {k: sum(c["decomposition"][k] for c in cells) / len(cells) for k in keys}
    return rec


def render(rec: Mapping[str, Any], gate_record: Mapping[str, Any], stats_by_cell: Mapping[str, Any], cost: Mapping[str, Any], commit: str, status: str) -> str:
    blocks: list[str] = []
    blocks.append(Rep.block("P10-I-S2-D0 (ADR-0035): interference diagnosis over Part T's frozen M-append snapshots", [
        f"status: {status}", f"code commit: {commit}", "Astra review: NOT_PERFORMED. Self-check only; not independent review and not human approval.",
        "Every pass is under the ORACLE route (as Part T's registered item scores). No training. CPU. All six cells, both panels, no selection. Descriptive; the summary words are not labels."]))  # fmt: skip
    blocks.append(Rep.block("GATE RECORD (pass/fail and the largest deviation only)", [json.dumps(gate_record, sort_keys=True)]))
    blocks.append(Rep.block("COST (worker-seconds = summed wall time of the computing processes; measured)", [json.dumps(cost, sort_keys=True)]))
    if rec.get("missing") or not rec.get("cells"):
        blocks.append(Rep.block("INCOMPLETE", [f"passes present {rec.get('passes_present')} of {rec.get('passes_expected')}; no table and no summary sentence is printed."]))
        return Rep.require_labelled("\n\n".join(blocks) + "\n")
    for key, st in stats_by_cell.items():
        lines = []
        for sk, v in st.items():
            if not (isinstance(v, dict) and "panel" in v):  # lead decision 1: top-level scalars (rep, order, id, label, oracle_line, pid, task_seconds, worker) are not per-store mappings
                continue
            lines.append(f"{key} {sk} panel={v['panel']} protected_stage={v['protected_stage']} reads={v['reads']} marker_reads={v['marker_reads']} gates={v['gates']}")
            for kind in ("words", "markers"):
                for q, sv in v[kind].items():
                    lines.append(f"  {kind:7s} {q:18s} n={sv['n']} undefined={sv['undefined']} mean={fmt_u(sv['mean'], 5)} median={fmt_u(sv['median'], 5)} p5={fmt_u(sv['p5'], 5)} p95={fmt_u(sv['p95'], 5)}")
        blocks.append(Rep.block(f"READ STATISTICS (section 5.2) cell {key}", lines))
    for key, c in rec["cells"].items():
        lines = [f"E_first={c['panels']['first']} E_second={c['panels']['second']}"]
        for pk, pv in c["passes"].items():
            ct = pv["contrast_vs_reference"]
            lines.append(f"{pk:18s} s={fmt_u(pv['s'])} G={fmt_u(pv['G'])} differs_from[{pv['reference']}]={pv['differs_from_reference']:.4f} contrast_vs_ref={fmt(ct['mean'], 5)} se={fmt_u(ct['se'], 5)}")
        blocks.append(Rep.block(f"SCORES (section 5.3) cell {key}", lines))
    for key, c in rec["cells"].items():
        d, a = c["decomposition"], c["append_point"]
        lines = [f"T={fmt(d['T'], 5)} (i) slots={fmt(d['i'], 5)} (ii) renormalisation={fmt(d['ii'], 5)} (iii) values={fmt(d['iii'], 5)} (iv) residual vs registered F={fmt(d['residual'], 9)}",
                 f"values first: values={fmt(d['values_first_values'], 5)} competition given values={fmt(d['values_first_competition'], 5)} interaction={fmt(d['interaction'], 5)}",
                 f"shares of T: (i)={fmt(d['shares']['i'], 3)} (ii)={fmt(d['shares']['ii'], 3)} (iii)={fmt(d['shares']['iii'], 3)} competition(path)={fmt(d['shares']['competition_path'], 3)} competition(values first)={fmt(d['shares']['competition_values_first'], 3)} values(values first)={fmt(d['shares']['values_values_first'], 3)}",
                 f"G units: {json.dumps(d['G_units'], sort_keys=True)}"]  # fmt: skip
        lines += [f"paired contrast {n}: mean={fmt(v['mean'], 5)} se={fmt_u(v['se'], 5)} n={v['n']}" for n, v in d["contrasts"].items()]
        lines += [f"append point: T={fmt(a['T'], 5)} (i)={fmt(a['i'], 5)} (ii)={fmt(a['ii'], 5)} (iii)={fmt(a['iii'], 5)}; ((i)+(ii)) final minus append = {fmt(a['competition_final_minus_append'], 5)} (effect of trained stage-2 keys on competition)"]
        blocks.append(Rep.block(f"DECOMPOSITION (section 6) first capability, cell {key}", lines))
    for key, c in rec["cells"].items():
        d = c["second_capability_effect_of_stage1_rows"]
        lines = [f"effect of stage-1 rows on the second capability's read (not a retention loss; either sign): T2=s[b2]-s[a]={fmt(d['T'], 5)} (i)={fmt(d['i'], 5)} (ii)={fmt(d['ii'], 5)} (iii)={fmt(d['iii'], 5)} values first: {fmt(d['values_first_values'], 5)}/{fmt(d['values_first_competition'], 5)} interaction={fmt(d['interaction'], 5)}",
                 f"stage 2 switched off (trained keys) e(1) on E_second: s={fmt_u(d['stage2_switched_off_trained_keys']['s_e1'])} s[a]-s[e1]={fmt(d['stage2_switched_off_trained_keys']['s_a_minus_s_e1'], 5)} G={fmt_u(d['stage2_switched_off_trained_keys']['G_e1'])}"]  # fmt: skip
        lines += [f"paired contrast {n}: mean={fmt(v['mean'], 5)} se={fmt_u(v['se'], 5)}" for n, v in d["contrasts"].items()]
        blocks.append(Rep.block(f"SECOND CAPABILITY, cell {key}", lines))
    for key, c in rec["cells"].items():
        lines = []
        for x, v in c["counterfactual_ret"].items():
            lines.append(f"read {x}: {v['word']} (F={fmt(v['F'], 5)} rho={fmt_u(v['rho'])} evaluable={v['evaluable']}) beside second capability: cost s[a]-s[c]={fmt(v['second_capability_cost_vs_c'], 5)} G_second(c)={fmt_u(v['G_second_under_c'])} (G_second(a)={fmt_u(v['G_second_a'])}); under g(2): cost={fmt(v['second_capability_cost_vs_g2'], 5)} G_second(g2)={fmt_u(v['G_second_under_g2'])}")
        blocks.append(Rep.block(f"COUNTERFACTUAL RET ARITHMETIC (not RET), cell {key}", lines))
    w = rec["words"]
    blocks.append(Rep.block("SUMMARY WORDS (section 7; descriptive; none is a label)", [f"path order: {w['path_order']}", f"values-first order: {w['values_first_order']}", f"final wording: {w['final']}", f"cells with T not positive (share undefined, never counted): {w['cells_with_nonpositive_T']}",
                                                                                          f"means beside the per-cell values: {json.dumps(rec['means_beside_cells'], sort_keys=True)}"]))  # fmt: skip
    for key, c in rec["cells"].items():
        lines = []
        for role, row in c["registered_scale"].items():
            lines.append(f"{role}: " + " ".join(f"{k}={fmt_u(v)}" for k, v in row.items()))
        blocks.append(Rep.block(f"REGISTERED SCORES FOR SCALE (taken from Part T's registry; not recomputed), cell {key}", lines))
    return Rep.require_labelled("\n\n".join(blocks) + "\n")

