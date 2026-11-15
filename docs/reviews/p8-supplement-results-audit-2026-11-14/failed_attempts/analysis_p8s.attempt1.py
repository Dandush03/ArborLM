"""Auditor's independent check of the ADR-0016 supplementary analysis (tasks 3, 4, 5).

Steps (standard library only; imports nothing from ``arborlm`` or ``supplements``):
  1. Build a scratch sim-run directory with symlinks: 55 registered P8S sim.json + 5 P8SUP sim.json.
  2. Run the auditor's frozen P8 recomputation tool UNCHANGED (hash-pinned,
     docs/reviews/p8-preflight-2026-11-14/independent_recompute_p8.py) on (P8E, merged) and compare
     with the nested ``supplementary_analysis`` (extracted to scratch); also on (P8E, P8S) vs the
     registered analysis.json as a control.
  3. Re-typed C04/C05 case means over all six cells and over the sim-complete subset, from eval.json
     and sim.json, compared with the supplementary and registered means and scorecards.
  4. W5: own deep diff of nested supplementary vs registered analysis.json (excluding dry_run,
     inputs), and of the three CSV bodies; every differing path classified against ADR-0016 section 5.
  5. Predictions 5, 8, 9 from the recomputation.
  6. Labels and section 8 forbidden-claim scan of every supplementary output file.

Usage (repository root):
  uv run --locked python -I docs/reviews/p8-supplement-results-audit-2026-11-14/analysis_p8s.py SCRATCH OUT.json
Auditor tool (Claude Opus 5.5). Not Astra validation, not human approval.
"""

import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXP = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
EVAL = EXP / "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
SUP = EXP / "P8SUP-20261114T144104227089Z-fbfb3d18513749b081f9cdd93f22ad81"
REGSIM = EXP / "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
REGA_LOCAL = EXP / "P8A-20261114T044147896561Z-4a9976ed3c7d493c8a92293786f2572c"
REGA = ROOT / "results/p8-2026-11-14/analysis/P8A-20261114T044147896561Z-4a9976ed3c7d493c8a92293786f2572c"
SUPA = ROOT / "results/p8-supplement-2026-11-14/analysis/P8SUPA-20261114T144120084661Z-f008b8673e97484fa528ccf36beba4e9"
TOOL = ROOT / "docs/reviews/p8-preflight-2026-11-14/independent_recompute_p8.py"
TOOL_SHA = "dc3e7269976b6fdcb8accf5189ab5709f1db9b94bf03b73c3d274b655e6f1acb"
FIVE = ("b101-o301-s601-C04", "b101-o301-s601-C05", "b101-o301-s602-C04", "b101-o301-s602-C05", "b102-o302-s601-C05")
PARENTS = ((101, 301), (102, 302), (103, 303))
SEEDS = (601, 602)
LABEL = "SUPPLEMENTARY (ADR-0016) — not the registered P8 output"
ALLOWED_PREFIX = ("study_status", "cells_with_complete_records", "missing_cells", "cases.C04", "cases.C05",
                  "decision_inputs.section_8_option_indicated", "decision_inputs.section_8_reason")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def labels():
    for b, o in PARENTS:
        for s in SEEDS:
            for c in range(1, 11):
                yield f"b{b}-o{o}-s{s}-C{c:02d}"


def diff(a, b, p=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            q = f"{p}.{k}" if p else k
            if k not in a or k not in b:
                yield q, "key only in " + ("supplementary" if k in a else "registered")
            else:
                yield from diff(a[k], b[k], q)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            yield from diff(x, y, f"{p}[{i}]")
    elif a != b or type(a) is not type(b):
        yield p, f"{a!r:.80} != {b!r:.80}"


def count_leaves(x) -> int:
    if isinstance(x, dict):
        return sum(count_leaves(v) for v in x.values())
    if isinstance(x, list):
        return sum(count_leaves(v) for v in x) if x else 1
    return 1


def allowed(path: str) -> bool:
    return any(path == a or path.startswith(a + ".") or path.startswith(a + "[") for a in ALLOWED_PREFIX)


def csv_body(path: Path, supplementary: bool) -> list[list[str]]:
    text = path.read_text()
    if supplementary:
        first, _, text = text.partition("\n")
        if first != "# " + LABEL:
            raise SystemExit(f"{path}: first line is not the supplementary label: {first!r}")
    return list(csv.reader(io.StringIO(text)))


def run_tool(sim_run: Path, analysis: Path, out: Path) -> dict:
    if sha(TOOL.read_bytes()) != TOOL_SHA:
        raise SystemExit("recompute tool hash differs")
    cmd = [sys.executable, "-I", str(TOOL), "--eval-run", str(EVAL), "--sim-run", str(sim_run), "--out", str(out), "--analysis", str(analysis)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    (out.with_suffix(".stdout")).write_text(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return json.loads(out.read_text())


def main() -> int:
    scratch, outp = Path(sys.argv[1]), Path(sys.argv[2])
    scratch.mkdir(parents=True, exist_ok=True)
    o: dict = {"problems": []}
    # 1. merged directory
    merged = scratch / "merged_sim_run"
    for lb in labels():
        d = merged / "cells" / lb
        d.mkdir(parents=True, exist_ok=True)
        src = (SUP if lb in FIVE else REGSIM) / "cells" / lb / "sim.json"
        link = d / "sim.json"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(src)
    # registered analysis: committed == local experiments copy
    o["registered_analysis_committed_equals_local"] = {
        f: (REGA / f).read_bytes() == (REGA_LOCAL / f).read_bytes() for f in ("analysis.json", "cells.csv", "pairs.csv", "scorecard.csv", "manifest.json")}
    reg = json.loads((REGA / "analysis.json").read_text())
    supfile = json.loads((SUPA / "supplementary_analysis.json").read_text())
    nested = supfile["supplementary_analysis"]
    (scratch / "nested_supplementary_analysis.json").write_text(json.dumps(nested))
    o["registered_analysis_sha256"] = sha((REGA / "analysis.json").read_bytes())
    o["registered_analysis_sha256_cited_in_supplement"] = supfile["inputs"]["registered_analysis_sha256"]
    # 2. unchanged tool on merged, and control on registered
    mine = run_tool(merged, scratch / "nested_supplementary_analysis.json", outp.parent / "recompute_merged60_vs_supplementary_run1.json")
    ctrl = run_tool(REGSIM, REGA / "analysis.json", outp.parent / "recompute_registered55_control_run1.json")
    o["recompute_merged60_vs_supplementary"] = {k: mine["comparison"][k] for k in ("compared_values", "max_abs_difference", "mismatch_count")} | {"mismatches": mine["comparison"]["mismatches"]}
    o["recompute_registered55_vs_registered"] = {k: ctrl["comparison"][k] for k in ("compared_values", "max_abs_difference", "mismatch_count")}
    res = mine["result"]
    o["auditor_result_summary"] = {
        "study_status": res["study_status"], "bind": res["concentration_controls_bind"], "decision": res["decision"],
        "classes": {c: {"A": res["cases"][c]["panels"]["A"].get("class"), "B": res["cases"][c]["panels"]["B"].get("class"),
                        "study": res["cases"][c].get("study_class")} for c in ("C04", "C05", "C06", "C07", "C08", "C09", "C10")},
        "open_questions": res.get("open_questions")}
    # auditor C04/C05 guard values from the unchanged tool
    o["auditor_guard_C04_C05"] = {}
    for c in ("C04", "C05"):
        for p in ("A", "B"):
            for name, comp in res["cases"][c]["panels"][p].items():
                if name == "class" or not isinstance(comp, dict) or "quality" not in comp:
                    continue
                q = comp["quality"]
                o["auditor_guard_C04_C05"][f"{c}.{p}.{name}"] = {k: q[k] for k in ("delta_nll_mean", "pairs_above", "gain_retention", "association_retention", "u_ratio", "quality_passes")}
    # 3. re-typed case means
    def ev(lb):
        return json.loads((EVAL / "cells" / lb / "eval.json").read_text())

    def sm(lb):
        p = (SUP if lb in FIVE else REGSIM) / "cells" / lb / "sim.json"
        return json.loads(p.read_text())

    table = {}
    for c in ("C04", "C05"):
        labs = [lb for lb in labels() if lb.endswith(c)]
        for p in ("A", "B"):
            for subset_name, subset in (("all6", labs), ("sim_complete", [lb for lb in labs if lb not in FIVE])):
                vals: dict[str, list[float]] = {}
                for lb in subset:
                    e, s = ev(lb), sm(lb)
                    n = e["nll"]["step512"]
                    u = e["traces"][p]["utilization"]
                    tr = s["panels"][p]["temporal_reuse"]
                    row = {"nll": n["enabled"][p], "nll_disabled": n["disabled"][p], "nll_values_permuted": n["values_permuted"][p],
                           "nll_step0": e["nll"]["step0"]["enabled"][p],
                           "memory_gain": n["disabled"][p] - n["enabled"][p], "value_association_effect": n["values_permuted"][p] - n["enabled"][p],
                           "n_eff": u["n_eff"], "distinct_slots": u["distinct_slots"], "hot64_share": u["hot64_share"], "context_breadth": u["context_breadth_mean"],
                           "temporal_reuse": tr["actual"]["value"],
                           "temporal_reuse_null": sum(tr[f"null_{k}"]["value"] for k in (1, 2, 3)) / 3}
                    bp = s["panels"][p]["branch_persistence"]
                    if bp is not None:
                        row["branch_persistence_top"] = bp["actual"]["top_fraction"]
                        row["branch_persistence_pair"] = bp["actual"]["pair_fraction"]
                    for k, v in row.items():
                        vals.setdefault(k, []).append(v)
                means = {k: math.fsum(v) / len(v) for k, v in vals.items()}
                means["temporal_reuse_ratio_to_null"] = means["temporal_reuse"] / means["temporal_reuse_null"]
                means["cells"] = len(subset)
                table[f"{c}.{p}.{subset_name}"] = means
    o["case_means"] = table
    cmp_means = {"compared": 0, "max_rel_diff": 0.0, "differences": []}
    for c in ("C04", "C05"):
        for p in ("A", "B"):
            for subset_name, src in (("all6", nested), ("sim_complete", reg)):
                theirs = src["cases"][c]["panels"][p]["means"]
                for k, v in table[f"{c}.{p}.{subset_name}"].items():
                    if k not in theirs:
                        continue
                    cmp_means["compared"] += 1
                    t = theirs[k]
                    rd = abs(v - t) / max(1e-300, abs(t)) if t else abs(v)
                    cmp_means["max_rel_diff"] = max(cmp_means["max_rel_diff"], rd)
                    if rd > 1e-12:
                        cmp_means["differences"].append([f"{c}.{p}.{subset_name}.{k}", v, t])
    o["case_means_comparison"] = cmp_means
    # nll_disabled identical across cases of a parent? (descriptive)
    spread = 0.0
    for b, oo in PARENTS:
        for s in SEEDS:
            for p in ("A", "B"):
                xs = [ev(f"b{b}-o{oo}-s{s}-C{c:02d}")["nll"]["step512"]["disabled"][p] for c in range(1, 11)]
                spread = max(spread, max(xs) - min(xs))
    o["nll_disabled_max_spread_across_cases_within_cell_pair"] = spread
    # 4. W5 diff
    reg_cmp = {k: v for k, v in reg.items() if k not in ("dry_run", "inputs")}
    d = list(diff(nested, reg_cmp))
    o["w5"] = {"leaves_registered": count_leaves(reg_cmp), "leaves_supplementary": count_leaves(nested),
               "differing_paths": len(d),
               "disallowed": [x for x in d if not allowed(x[0])],
               "allowed_top_groups_seen": sorted({next(a for a in ALLOWED_PREFIX if x[0] == a or x[0].startswith(a)) for x in d if allowed(x[0])}),
               "decision_inputs_paths": [x for x in d if x[0].startswith("decision_inputs")]}
    o["w5"]["equal_leaves_outside_allowed"] = None  # filled below
    # count equal leaves outside the allowed set
    def leaf_paths(x, p=""):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from leaf_paths(v, f"{p}.{k}" if p else k)
        elif isinstance(x, list) and x:
            for i, v in enumerate(x):
                yield from leaf_paths(v, f"{p}[{i}]")
        else:
            yield p
    outside = [q for q in leaf_paths(reg_cmp) if not allowed(q)]
    o["w5"]["equal_leaves_outside_allowed"] = len(outside) - len([x for x in d if not allowed(x[0])])
    other_refs = [q for q in leaf_paths(reg_cmp) if not allowed(q) and re.search(r"C0[45]", q)]
    o["w5"]["paths_outside_C04_C05_naming_C04_or_C05"] = other_refs
    other_vals = []
    for case, ent in reg_cmp["cases"].items():
        if case in ("C04", "C05"):
            continue
        txt = json.dumps(ent)
        if re.search(r'"C0[45]"', txt):
            other_vals.append(case)
    o["w5"]["other_cases_with_C04_C05_value"] = other_vals
    # CSVs
    csvs = {}
    for name in ("cells.csv", "pairs.csv", "scorecard.csv"):
        a, b = csv_body(SUPA / name, True), csv_body(REGA / name, False)
        ha, hb = a[0], b[0]
        rows_a, rows_b = a[1:], b[1:]
        info = {"header_equal": ha == hb, "rows_supplementary": len(rows_a), "rows_registered": len(rows_b)}
        if name == "cells.csv":
            new = [r for r in rows_a if r[0] in FIVE]
            rest = [r for r in rows_a if r[0] not in FIVE]
            info.update(rows_new_cells=len(new), rest_equal_registered=rest == rows_b,
                        registered_has_five=any(r[0] in FIVE for r in rows_b))
        elif name == "pairs.csv":
            ci = ha.index("case")
            ri = ha.index("reference")
            ka = [r for r in rows_a if r[ci] not in ("C04", "C05")]
            kb = [r for r in rows_b if r[ci] not in ("C04", "C05")]
            info.update(rows_C04_C05_supp=len(rows_a) - len(ka), rows_C04_C05_reg=len(rows_b) - len(kb), rest_equal=ka == kb,
                        other_rows_with_reference_C04_C05=sum(1 for r in ka if r[ri] in ("C04", "C05")))
        else:
            si = ha.index("study_status")
            info["status_column_supp"] = sorted({r[si] for r in rows_a})
            info["status_column_reg"] = sorted({r[si] for r in rows_b})
            bad = []
            for ra, rb in zip(rows_a, rows_b):
                for j, (x, y) in enumerate(zip(ra, rb)):
                    if x != y and j != si and ra[0] not in ("C04", "C05"):
                        bad.append([ra[0], ha[j], x, y])
            info["disallowed_cell_differences"] = bad
            info["C04_C05_rows_supp"] = {r[0]: dict(zip(ha, r)) for r in rows_a if r[0] in ("C04", "C05")}
            info["C04_C05_rows_reg"] = {r[0]: dict(zip(ha, r)) for r in rows_b if r[0] in ("C04", "C05")}
            info["case_order_equal"] = [r[0] for r in rows_a] == [r[0] for r in rows_b]
        csvs[name] = info
    o["csv"] = csvs
    # 5. predictions 5, 8, 9 from my recomputation
    o["predictions"] = {
        "5": all(res["cases"][c]["panels"][p].get("class") == "QUALITY-FAILED" for c in ("C04", "C05") for p in ("A", "B"))
        and all(res["cases"][c].get("study_class") == "QUALITY-FAILED" for c in ("C04", "C05")),
        "8": res["concentration_controls_bind"] is False and nested["concentration_controls_bind"] is False
        and [q["case"] for q in nested["open_questions"]] == ["C09"] and nested["open_questions"] == reg["open_questions"],
        "9": res["decision"] == "c" and nested["decision_inputs"]["section_8_option_indicated"] == "c",
    }
    o["nested_status_decision"] = [nested["study_status"], nested["decision_inputs"]["section_8_option_indicated"], nested["decision_inputs"]["section_8_reason"]]
    # 6. labels and forbidden claims
    files = sorted(p for p in (ROOT / "results/p8-supplement-2026-11-14").rglob("*") if p.is_file())
    lab = {}
    forbidden = [r"registered (P8 )?study is complete", r"registered decision is \(?c\)?", r"decision[^\n]{0,20}\(c\)", r"LOCALITY-POSITIVE",
                 r"supersede", r"replicat", r"locality information", r"repaired", r"positive result", r"validated", r"approved"]
    for p in files:
        rel = str(p.relative_to(ROOT))
        text = p.read_text(errors="replace")
        entry = {"has_label": LABEL in text or "SUPPLEMENTARY (ADR-0016)" in text,
                 "first_line": text.splitlines()[0][:120] if text else "",
                 "registered_status_stated": ("INCOMPLETE" in text)}
        hits = []
        for pat in forbidden:
            for m in re.finditer(pat, text, flags=re.I):
                s = max(0, m.start() - 100)
                hits.append([pat, text[s:m.end() + 60].replace("\n", " ")])
        entry["forbidden_pattern_hits_for_manual_review"] = hits[:12]
        entry["hit_count"] = len(hits)
        lab[rel] = entry
    o["labels"] = lab
    outp.write_text(json.dumps(o, indent=1, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({"merged": o["recompute_merged60_vs_supplementary"] | {"mismatches": len(o["recompute_merged60_vs_supplementary"]["mismatches"])},
                      "control": o["recompute_registered55_vs_registered"], "means": {k: v for k, v in cmp_means.items() if k != "differences"},
                      "means_diffs": len(cmp_means["differences"]), "w5_diff_paths": o["w5"]["differing_paths"], "w5_disallowed": len(o["w5"]["disallowed"]),
                      "predictions": o["predictions"], "summary": o["auditor_result_summary"]}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
