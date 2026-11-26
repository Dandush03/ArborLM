# ruff: noqa: E501
"""After the run: copy the small records (not the per-item bulk) into ``results/p10is2d0-run-20261124/`` and write ``RECORD.md`` from them: what was run, the commit, the gate results, the readings, the decomposition under
both orders, the fixed wording, the cost, and what ADR-0035 section 12 says is reported whatever the result. Tables are generated from the records, never typed. No interpretation beyond the ADR's fixed wording."""

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from studies.p10is2.common.core import ORACLE_LINE

from .report import POSTHOC


def f(x: float | None, nd: int = 4) -> str:
    return "n/a" if x is None else f"{x:+.{nd}f}"


def u(x: float | None, nd: int = 4) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def tables(rd: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for role in ("first", "second"):
        out += [f"### Scores, {role} capability (E_{role}; s = mean chrF-norm, G as `quantities.gap`; `differs` = share of items whose greedy output differs from the reference pass; contrast = paired per-item difference to the reference pass, standard error sd/sqrt(1000))", "", "| cell | pass | s | G | differs | contrast | se |", "|---|---|---|---|---|---|---|"]
        for key, c in rd["cells"].items():
            for pk, pv in c["passes"].items():
                if pk.startswith(role + "|"):
                    ct = pv["contrast_vs_reference"]
                    out.append(f"| {key} | {pk.split('|', 1)[1]} | {u(pv['s'])} | {u(pv['G'])} | {pv['differs_from_reference']:.4f} | {f(ct['mean'], 5)} | {u(ct['se'], 5)} |")
        out.append("")
    out += ["### Decomposition, first capability, final store (path order: slots, renormalisation, values; then values first)", "", "| cell | T | (i) slots | (ii) renorm | (iii) values | (iv) residual vs registered F | values-first values | values-first competition | interaction | (i)+(ii) share | (iii) share | comp share (values first) | values share (values first) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in rd["cells"].items():
        d = c["decomposition"]
        s = d["shares"]
        out.append(f"| {key} | {f(d['T'], 5)} | {f(d['i'], 5)} | {f(d['ii'], 5)} | {f(d['iii'], 5)} | {f(d['residual'], 9)} | {f(d['values_first_values'], 5)} | {f(d['values_first_competition'], 5)} | {f(d['interaction'], 5)} | {f(s['competition_path'], 3)} | {f(s['values_path'], 3)} | {f(s['competition_values_first'], 3)} | {f(s['values_values_first'], 3)} |")
    out += ["", "G units (term / (teacher - S0) of E_first):", "", "| cell | T | (i) | (ii) | (iii) | interaction |", "|---|---|---|---|---|---|"]
    for key, c in rd["cells"].items():
        g = c["decomposition"]["G_units"]
        out.append(f"| {key} | " + " | ".join(f(g[k], 5) if g else "n/a" for k in ("T", "i", "ii", "iii", "interaction")) + " |")
    out += ["", "### Append point (first capability)", "", "| cell | T at append | (i) | (ii) | (iii) | ((i)+(ii)) final minus append |", "|---|---|---|---|---|---|"]
    for key, c in rd["cells"].items():
        a = c["append_point"]
        out.append(f"| {key} | {f(a['T'], 5)} | {f(a['i'], 5)} | {f(a['ii'], 5)} | {f(a['iii'], 5)} | {f(a['competition_final_minus_append'], 5)} |")
    out += ["", "### Second capability: effect of the stage-1 rows on its read (not a retention loss; either sign)", "", "| cell | T2 = s[b2]-s[a] | (i) | (ii) | (iii) | values-first values | values-first competition | interaction | s[a]-s[e1] (stage 2 switched off, trained keys) |", "|---|---|---|---|---|---|---|---|---|"]
    for key, c in rd["cells"].items():
        d = c["second_capability_effect_of_stage1_rows"]
        out.append(f"| {key} | {f(d['T'], 5)} | {f(d['i'], 5)} | {f(d['ii'], 5)} | {f(d['iii'], 5)} | {f(d['values_first_values'], 5)} | {f(d['values_first_competition'], 5)} | {f(d['interaction'], 5)} | {f(d['stage2_switched_off_trained_keys']['s_a_minus_s_e1'], 5)} |")
    out += ["", "### Counterfactual RET arithmetic (it is not RET), beside the second capability's cost", "", "| cell | read | F | rho | word | second capability cost s[a]-s[c] | G_second(c) | G_second(a) | cost s[a]-s[g(2)] | G_second(g(2)) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in rd["cells"].items():
        for x, v in c["counterfactual_ret"].items():
            out.append(f"| {key} | {x} | {f(v['F'], 5)} | {u(v['rho'])} | {v['word']} | {f(v['second_capability_cost_vs_c'], 5)} | {u(v['G_second_under_c'])} | {u(v['G_second_a'])} | {f(v['second_capability_cost_vs_g2'], 5)} | {u(v['G_second_under_g2'])} |")
    out += ["", "### Registered scores for scale (Part T's registry; not recomputed)", "", "| cell | capability | S0 | TEACHER | M1 | M-append | M-sep | E-table | D-append | D-seq | D-sep | M-seq | M-ii | M-joint |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in rd["cells"].items():
        for role, row in c["registered_scale"].items():
            out.append(f"| {key} | {role} | " + " | ".join(u(row[k]) for k in ("S0", "TEACHER", "M1_registered", "M-append_registered", "M-sep", "E-table", "D-append", "D-seq", "D-sep", "M-seq", "M-ii", "M-joint")) + " |")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--results-dir", required=True)
    a = ap.parse_args(argv)
    run, res = Path(a.run_dir), Path(a.results_dir)
    res.mkdir(parents=True, exist_ok=False)
    for sub, names in (("", ("report.txt", "launch.json", "run_complete.json", "run_stopped.json", "resumes.json")), ("records", ("readings.json", "stats.json", "gate_record.json", "cost.json", "partt_run_dir_diff.json")), ("gates", ("identity.json", "repro.json", "no_write_demonstration.json", "gate_record.json")), ("inputs", ("world_inputs.json", "module_hashes.json"))):
        for n in names:
            src = run / sub / n if sub else run / n
            if src.is_file():
                dst = res / sub / n if sub else res / n
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    for n in ("partt_run_dir.before.json", "partt_run_dir.after.json"):  # file lists with SHA-256 (small)
        if (run / "inputs" / n).is_file():
            (res / "inputs").mkdir(exist_ok=True)
            shutil.copy2(run / "inputs" / n, res / "inputs" / n)
    cost_dir = res / "cost"
    cost_dir.mkdir(exist_ok=True)
    for p in sorted((run / "cost").glob("ledger_*.json")):
        shutil.copy2(p, cost_dir / p.name)
    launch = json.loads((run / "launch.json").read_text())
    rd = json.loads((run / "records" / "readings.json").read_text()) if (run / "records" / "readings.json").is_file() else {"cells": {}}
    gate = json.loads((run / "gates" / "gate_record.json").read_text()) if (run / "gates" / "gate_record.json").is_file() else None
    cost = json.loads((run / "records" / "cost.json").read_text()) if (run / "records" / "cost.json").is_file() else None
    lines = [
        "# P10-I-S2-D0 run record (ADR-0035)", "", ORACLE_LINE, POSTHOC, "",
        "Astra review: NOT_PERFORMED. Self-check only; not independent review and not human approval. Implemented by `arbor-implementer` (Claude Sonnet 5.5, `claude-sonnet-5-5`).", "",
        "## What was run", "",
        f"- `studies/p10is2d0` at commit `{launch['commit']}` (branch `{launch['branch']}`), torch {launch['torch']}, CPU only, 3 worker processes of 6 threads, deterministic algorithms, launch `studies/p10is2d0/launch_d0.sh`.",
        "- Specification: ADR-0035 draft 3 (approved as a specification by the lead under the human lead's delegation; not the human lead's own approval). Every pass is under the oracle route. No training, no download, no MPS.",
        f"- Output directory (git-ignored, bulk per-item records): `{Path(a.run_dir)}`. Part T's run directory was read only; file lists with SHA-256 before and after are in `inputs/`.",
        "", "## Gates (pass/fail and the largest deviation only)", "", "```", json.dumps(gate, sort_keys=True, indent=1) if gate else "no gate record (the run stopped before the gates finished: see run_stopped.json / gate_failure.json)", "```", "",
        "## Cost (measured)", "", "```", json.dumps(cost, sort_keys=True, indent=1) if cost else "no cost record (the run did not complete)", "```", "",
    ]  # fmt: skip
    if rd.get("cells"):
        w = rd["words"]
        lines += ["## Readings", "", *tables(rd), "", "## Summary words (ADR-0035 section 7; descriptive; none is a label)", "", f"- path order: **{w['path_order']}**", f"- values-first order: **{w['values_first_order']}**", f"- final wording: **{w['final']}**", f"- cells with T not positive: {w['cells_with_nonpositive_T']}", f"- means beside the per-cell values: `{json.dumps(rd['means_beside_cells'], sort_keys=True)}`", ""]
    else:
        lines += ["## Readings", "", "INCOMPLETE or stopped: no table and no summary sentence.", ""]
    lines += ["## Reported whatever the result (section 12)", "", "- gate record: above; every table of sections 5 and 6 for every cell and panel: in `report.txt` (and `records/`), including readings that show nothing, negative shares and conditions that make the first capability worse; the interaction and both orders' words: above; the second capability's cost beside every first-capability reading: above; registered scores for scale: above; cost against the cap: above.", "- failed attempts of this run and disagreements with the audit: none recorded here; the independent recomputation is a separate stage not performed by this record (the auditor's).", "- `row_shares` of Part T was not opened (ADR-0035 section 1.5).", ""]
    (res / "RECORD.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
