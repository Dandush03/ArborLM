# ruff: noqa: E501
"""P10IS6 report renderer and completion messages (ADR-0031 section 15: ``printing/``). Identity of this folder binds no result: stage records carry the hashes of the computing files only (``plan.COMPUTING``).

``render`` is a pure function of the analysis result. A completion message never fails a finished stage: ``announce`` writes nothing itself and catches every printing error (requirement 5). Self-check only: not independent review, not Astra
validation, not human approval. The label is a registered outcome only after the auditor's recomputation."""

import sys
from collections.abc import Mapping
from typing import Any


def _f(x: Any, nd: int = 4) -> str:
    return "n/a" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def render(res: Mapping[str, Any], mode: str) -> str:
    lp, d, t = res["line_p"], res["d_flat"], res["trend"]
    out = [f"# P10-I-S6 report ({mode})", "", "> Self-check output. Not independent review, not Astra validation, not human approval. A label here is a registered outcome only after the auditor's independent recomputation.", ""]
    if res["r16"]["label"] != "REPLICATED AT 16,384":
        out += ["**First: the 16,384-update lead was NOT reproduced on new parents and data (R16: " + str(res["r16"]["label"]) + ").**", ""]
    out += [f"## Line P (registered): {lp['label']}", "", f"- row {lp['row']}; reading rung R = {res['reading_rung']} (K* = {res['k_star']}), k_max = {res['k_max']}; dependence-qualified: {lp['dependence_qualified']}"]
    if lp["causes"]:
        out += [f"- cause(s): {'; '.join(lp['causes'])}"]
    out += ["", f"## Trend line (descriptive; never a label): {t['text']}", "", f"- {t['lead_sentence']}", "", f"## D[FLAT] at R: {d['label']}", f"- failing: {d['failing']}; collapsed cells: {d['collapsed']}; cells with H_used > B: {d['H_used_worse_than_base_cells']}; mean B - H_vmean: {_f(d['mean_V_mean_gap'])}", "",
            "## Per rung", "", "| k | updates | rate F | rate D | L(F) | L(D) | delta F | delta D | deltarun F | deltarun D | conv F | conv D | mean Q | class |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in res["per_rung"].items():
        out.append(f"| {k} | {r['updates']} | {r['rates']['M-FLAT']} | {r['rates']['D-ADAPT']} | {_f(r['L']['M-FLAT'])} | {_f(r['L']['D-ADAPT'])} | {_f(r['delta']['M-FLAT'])} | {_f(r['delta']['D-ADAPT'])} | {_f(r['delta_run']['M-FLAT'])} | {_f(r['delta_run']['D-ADAPT'])} | {r['convergence']['M-FLAT']} | {r['convergence']['D-ADAPT']} | {_f(r['mean_Q'])} | {r['class']} |")
    out += ["", "## Harm figures per rung (strict '>')", ""]
    for k, h in res["harm"].items():
        out.append(f"- rung {k}: B-H_used {_f(h['H_used']['mean_B_minus'])} ({h['H_used']['cells_worse_than_base']} cells worse than BASE); B-H_mean {_f(h['H_mean']['mean_B_minus'])} ({h['H_mean']['cells_worse_than_base']}); B-H_vmean {_f(h['H_vmean']['mean_B_minus'])} ({h['H_vmean']['cells_worse_than_base']})")
    out += ["", f"## R16: {res['r16']['label']}; OA: {res['oa'].get('label')} (OA rates were calibrated on the new calibration parents; no label changes)", "", "## Limits", "", "Converged means converged by the rule of section 9 at a constant rate chosen per duration; nothing about cost, efficiency, the tree, SSD or other corpora; no p-value.", ""]
    return "\n".join(out)


def announce(message: str) -> None:
    """Print a completion message; any error is swallowed (the stage's record is already written)."""
    try:
        print(message)
    except Exception as e:  # noqa: BLE001
        try:
            print(f"(a completion message could not be printed: {type(e).__name__})", file=sys.stderr)
        except Exception:  # noqa: BLE001, S110
            pass
