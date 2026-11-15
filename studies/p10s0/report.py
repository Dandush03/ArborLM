# ruff: noqa: E501
"""P10S0 report (ADR-0020 sections 8.6, 8.7): turns ``analysis.json`` into ``RESULTS.md``, ``results.json`` and ``classes.csv``. ``render_markdown`` is a pure function of the analysis result (tests
feed it the synthetic registry). It prints what S0 found and nothing else: no statement about S1 or S2 (section 17 item 0), no success claim, no efficiency claim.

Fixed text. Wherever a class, label, annotation or hypothesis reading of A5-D is printed, or the arm-selection record or P9-II's carried arm is cited, the section carries the fourth-arm string, P9-II's F1
annotation and the fixed provenance sentence of section 3.4 (``core.a5d_block``); ``check_a5d_provenance`` is the check a test runs on every rendered report. An outcome of rows 4 and 5 carries the seven items
of section 8.7 and may not be shortened to omit one.
"""

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import write_json

from . import classes as C
from . import core

NOT_CLAIMED = (
    "Nothing about capacity, useful-capacity scaling, locality, transfer or adding facts later.",
    "Not an unbiased first test of A5-D: it was added after P9-II's outcome was observed, knowing it was RELIABLE there (confirmatory replication on new draws).",
    "Nothing about natural language, another backbone or student, loads other than 0.5 and (label-free arms) 2 facts per slot, or any regime other than 512 exposures per fact.",
    "Nothing reliable about 65,536 slots: three draws, one initialization seed, a probe.",
    "Not that the interface finds where to read: the memory is told the answer position in every arm, WX included.",
    "Not that a qualified arm beats a tuned baseline (A0 is untuned by design), and no efficiency, latency or storage claim.",
    "Not a failure of the ArborLM concept, whatever the outcome; not a success of it either.",
)
NUMBER_LABELS = "Number labels: every accuracy, count, class and label in this report is MEASURED on S0's own cells (or, where it says P9-II, copied from P9-II's committed records); per-draw bounds are ANALYTICAL (one-sided 95% Clopper-Pearson); no HYPOTHETICAL number appears; no cost figure is an efficiency claim or a speedup."
BANNER_BASE = "ArborLM is unproven research. Astra review: NOT_PERFORMED. A Claude review is neither Astra validation nor a human approval."


def banner_text(result: Mapping[str, Any]) -> str:
    """The banner. The state of the human lead's acceptance of the P9-II outcome is read from the recorded fact the analysis stored (``core.p9ii_acceptance``: the verbatim words in ADR-0019 section 16), never
    asserted here."""
    a = result.get("p9ii_acceptance")
    if a is None:
        state = "The state of the human lead's acceptance of the P9-II outcome was not recorded in this result."
    elif a.get("accepted"):
        state = f"The human lead accepted the P9-II outcome as registered ({a['source']}: \"{a['quote']}\")."
    else:
        state = f"The human lead's acceptance of the P9-II outcome is not recorded in this tree ({a.get('source')})."
    return f"{BANNER_BASE} {state}"


CALIBRATED_TEXT = {
    "A0": "no calibrated value", "A1": "λ = 1.0 (P9-II's audited calibration record)", "A5-D": "μ = 1.0 (P9-II's audited calibration record)",
    "A2": "U_pre = 2,048 updates at 2,048 facts and 8,192 at 8,192 facts (P9-II's audited calibration record, exposure-scaled)",
}  # fmt: skip
REGIME_TEXT = "512 exposures per fact (U = 8,192 updates at 2,048 facts, 4U = 32,768 at 8,192 facts); schedules in exposures per fact; 0.5 facts per slot at 2K/4K and 8K/16K"
SIZE_NAME = {"2K/4K": "4,096 slots (2K/4K)", "8K/16K": "16,384 slots (8K/16K)", "8K/4K": "8K/4K (two facts per slot)"}


def fmt(x: Any, digits: int = 3) -> str:
    if isinstance(x, bool) or x is None:
        return str(x)
    if isinstance(x, int):
        return str(x)
    try:
        v = core.number(x)
    except (TypeError, ValueError):
        return str(x)
    return "nan" if v != v else f"{v:.{digits}f}"


def _class_cell(c: Mapping[str, Any]) -> str:
    return f"{c['label']} ({c['successes']}/{c['evaluated']} cells; {c['draws_succeeded']}/{c['draws_evaluated']} draws" + (f"; per-draw bound {fmt(c['per_draw_bound'])}" if c.get("per_draw_bound") is not None else "") + ")"


def check_product_provenance(text: str) -> bool:
    """True when a machine product (JSON, CSV, stdout line) either does not name A5-D or carries all three strings (``core.assert_provenance`` raises instead)."""
    return not core.mentions_a5d(text) or core.has_provenance(text)


def check_a5d_provenance(markdown: str) -> list[str]:
    """Every ``## `` section of the report that names A5-D (other than as part of the block itself) carries the fourth-arm string, P9-II's F1 annotation and the fixed provenance sentence. Returns the
    titles of the sections that do not."""
    bad: list[str] = []
    for part in re.split(r"(?m)^## ", markdown)[1:]:
        title = part.splitlines()[0] if part else ""
        stripped = part.replace(core.FOURTH_ARM_STRING, "").replace(core.F1_ANNOTATION, "").replace(core.PROVENANCE_SENTENCE, "")
        if "A5-D" in stripped and not (core.FOURTH_ARM_STRING in part and core.F1_ANNOTATION in part and core.PROVENANCE_SENTENCE in part):
            bad.append(title)
    return bad


def _section(title: str, lines: Sequence[str]) -> str:
    body = "\n".join(lines).rstrip() + "\n"
    stripped = body.replace(core.FOURTH_ARM_STRING, "").replace(core.F1_ANNOTATION, "").replace(core.PROVENANCE_SENTENCE, "")
    if "A5-D" in stripped and not all(x in body for x in (core.FOURTH_ARM_STRING, core.F1_ANNOTATION, core.PROVENANCE_SENTENCE)):
        body += "\n" + core.a5d_block() + "\n"
    return f"## {title}\n\n{body}\n"


# --- sections ---------------------------------------------------------------------------------------------------------------------------
def _arm_selection(res: Mapping[str, Any]) -> str:
    a = res["arm_selection"]
    cal = a["calibrated"]
    lines = [
        f"- The registered mapping's own result (section 3.2, on P9-II's committed records): **{a['mapping_printed']}** (table row {a['table_row']} of section 3.3; fourth arm by the mapping: {a['c4']}).",
        "- The human lead's override (section 3.4, 2026-11-15) fixes the fourth arm as A5-D:",
        "",
        f"  > {core.HUMAN_LEAD_WORDS}",
        "",
        f"- Calibrated values used (P9-II's audited calibration record; equals the record: {cal['equals_p9ii_record']}): λ = {cal['lambda']}, U_pre = {int(cal['u_pre']):,}, μ = {cal['mu']} (k_0/N = {cal['k0_fraction']} is not used: A4 is not in S0).",
        f"- Arms that can still be the candidate (section 3.5): {', '.join(a['candidates']['arms'])}; excluded: " + ("; ".join(f"{k} ({v})" for k, v in a["candidates"]["excluded"].items()) or "none") + ".",
    ]
    return _section("Arm selection (section 3.4)", lines)


def _outcome_header(res: Mapping[str, Any]) -> list[str]:
    o = res["outcome"]
    lines = [f"**Outcome (row {o['row']}): {o['label']}**"]
    if res.get("cut3_label"):
        lines.append(f"Cut 3 of section 10.4 applies: {res['cut3_label']}.")
    if o["row"] == 1:
        lines.append(f"{core.NOT_STARTED}: S0 did not run and no scientific label is derived.")
    elif o["row"] == 2:
        lines.append("No class, annotation, selection or scientific label is derived; no denominator is reduced. Reasons:")
        lines += [f"- {r}" for r in o["detail"].get("reasons", [])]
    elif o["row"] == 3:
        lines.append("Cell type 2K/4K is NOT_EVALUATED: more than one draw has A6 below 0.90. Nothing is qualified or disqualified.")
    return lines


def _qualified_text(res: Mapping[str, Any]) -> list[str]:
    """The seven items of section 8.7 that an outcome of rows 4 and 5 is printed with and may not be shortened to omit."""
    o = res["outcome"]
    arm = o["arm"]
    arms = res["arms"]
    lines = [f"1. **Arm and calibrated value:** {arm}; {CALIBRATED_TEXT[arm]}."]
    if arm == "A5-D":
        lines += ["", core.a5d_block(), ""]
    lines.append(f"2. **Supervision:** {core.SUPERVISION_LABEL[arm]}")
    lines.append(f"3. **Regime:** {REGIME_TEXT}.")
    lines.append("4. **Per size:**" + (f" (label: {res['cut3_label']})" if res.get("cut3_label") else ""))
    for ct in core.CORE_CELLTYPES:
        e = arms[arm][ct]
        c = e["consistency"]
        pooled = e["pooled"]["text"]
        p9 = e["p9ii"]
        lines.append(f"   - {SIZE_NAME[ct]}: S0 {_class_cell(e['s0'])}; P9-II class {p9['class'] if p9 and p9.get('available') else 'NOT AVAILABLE'}; {e['replication']}; pooled: {pooled}; **{c['label']}**.")
    lines.append("5. **Annotations (sections 8.6 and 8.4):**")
    lines.append(f"   - {res['overload']}")
    lines.append(f"   - {res['record_length']['label']} (block status {res['record_length']['status']})")
    probe = res["probe"]
    lines.append(f"   - AT 65,536 (probe; not a qualification; S0 only; three draws; one initialization seed): {probe.get('label') or probe['status']}")
    for ct in core.CORE_CELLTYPES:
        e = arms[arm][ct]
        lines.append(f"   - {SIZE_NAME[ct]}: {e['stable']['label'] or 'not ADDRESS STABLE'} (median {fmt(e['stable']['median'])}); {e['collapse_free']['label']}")
    for ct in core.CORE_CELLTYPES:
        e = arms[arm][ct]
        if e.get("address_recall"):
            lines.append(f"   - {SIZE_NAME[ct]}: ADDRESS RECALL median {fmt(e['address_recall']['median'])} {e['address_recall']['label'] or ''}")
        if e.get("dense_comparison"):
            lines.append(f"   - {SIZE_NAME[ct]}: DENSE COMPARISON {e['dense_comparison']['label']}")
        if e.get("sustained_success"):
            lines.append(f"   - {SIZE_NAME[ct]}: {e['sustained_success']['label']}")
        lines.append(f"   - {SIZE_NAME[ct]}: i = {fmt(e['information_bits']['median_of_the_smaller_panel'])} bits per fact (median over cells, the smaller panel; reported)")
    if arm in core.SUPERVISED:
        nc = res["p9ii_negative_control"]
        lines.append(f"   - P9-II NEGATIVE CONTROL: 4,096: {'NEGATIVE CONTROL FAILED' if nc['4096'] else 'not failed'}; 16,384: {'NEGATIVE CONTROL FAILED' if nc['16384'] else 'not failed'}")
    lines.append("6. **The other arms** (class under S0's criteria; paired against A0 under S0's criteria with d under P9-II's criteria beside it):")
    for other in core.CORE_LEARNED_ARMS:
        if other == arm:
            continue
        for ct in core.CORE_CELLTYPES:
            e = arms[other][ct]
            pr = res["paired"].get(other, {}).get(ct)
            lines.append(f"   - {other} at {SIZE_NAME[ct]}: {e['s0']['label']}" + (f"; {pr['s0']['label']} (d = {pr['s0']['d']}; P9-II criteria: d = {pr['p9ii']['d']})" if pr else ""))
    lines += [f"7. **Fixed sentences:** {core.FIXED_SENTENCES}"]
    if res["outcome"]["row"] == 5:
        lines.insert(1, f"   *Why 16,384 is missing:* {res['outcome']['detail'].get('why_16384_missing')}.")
    return lines


def _not_qualified(res: Mapping[str, Any]) -> list[str]:
    lines = [f"**{C.NOT_QUALIFIED_TEXT}.** {C.NOT_QUALIFIED_NEUTRAL}", "", "| arm | cell type | S0 class | class under P9-II's criteria | replication | added criterion failed | met S0's criteria |", "|---|---|---|---|---|---|---|"]
    for arm in core.CORE_LEARNED_ARMS:
        for ct, e in res["arms"][arm].items():
            lines.append(f"| {arm} | {ct} | {e['s0']['label']} | {e['p9ii_criteria']['label']} | {e['replication']} | {e['added_criterion_failed'] or '—'} | {e['meets']} |")
    inc = []
    for arm in core.CORE_LEARNED_ARMS:
        for ct in core.CORE_CELLTYPES:
            e = res["arms"][arm][ct]
            if e["meets"] and e["consistency"] and not e["consistency"]["consistent"]:
                inc.append(f"- {arm} at {SIZE_NAME[ct]}: {C.inconsistent_label(e['consistency'])}; pooled count {e['pooled']['text']}")
    if inc:
        lines += ["", "Arms that met S0's criteria but were INCONSISTENT ACROSS STUDIES:", *inc]
    return lines


def _sup(arm: str) -> str:
    return "(ADDRESS-SUPERVISED IN TRAINING)" if arm in core.SUPERVISED else "(LABEL-FREE)"


def _classes_section(res: Mapping[str, Any]) -> str:
    lines = ["| arm | cell type | S0 class (S0's criteria) | class under P9-II's criteria | P9-II class | replication | consistency | pooled (P9-II's criteria) | ADDRESS STABLE | collapse |", "|---|---|---|---|---|---|---|---|---|---|"]
    for arm in core.CORE_LEARNED_ARMS:
        for ct, e in res["arms"][arm].items():
            p9 = e["p9ii"]
            cons = e["consistency"]["label"] if e["consistency"] else "—"
            lines.append(
                f"| {arm} {_sup(arm)} | {ct} | {_class_cell(e['s0'])} | {_class_cell(e['p9ii_criteria'])} | "
                f"{p9['class'] if p9 and p9.get('available') else '—'} | {e['replication']} | {cons} | {e['pooled']['text']} | {e['stable']['label'] or 'no'} ({fmt(e['stable']['median'])}) | {e['collapse_free']['label']} |"
            )
    if res.get("cut3_label"):
        lines += ["", f"Cut 3 of section 10.4 applies at 16,384: {res['cut3_label']}; the 10-cell class rule applies there."]
    lines += ["", "UNRELIABLE and FAILS enter no rule; qualification, replication and OVERLOAD use RELIABLE against not RELIABLE only. P9-II's classes are those of its registered record (read through the arm-selection record).", ""]
    for arm in ("A1", "A2"):
        nc = res["p9ii_negative_control"]
        lines.append(f"- {arm}: P9-II NEGATIVE CONTROL at 4,096: {'FAILED' if nc['4096'] else 'not failed'}; at 16,384: {'FAILED' if nc['16384'] else 'not failed'} (P9-II's printed result, repeated).")
    for arm in core.CORE_LEARNED_ARMS:
        for ct, e in res["arms"][arm].items():
            if "class_at_u" in e:
                lines.append(f"- {arm} at {ct}, readout at U: {e['class_at_u']['class']} — {e['class_at_u']['label']} (enters no rule).")
            if e.get("address_recall"):
                lines.append(f"- {arm} at {ct}: ADDRESS RECALL median {fmt(e['address_recall']['median'])} {e['address_recall']['label'] or ''}")
            if e.get("dense_comparison"):
                lines.append(f"- {arm} at {ct}: DENSE COMPARISON {e['dense_comparison']['label']}")
            lines.append(f"- {arm} at {ct}: i median {fmt(e['information_bits']['median_of_the_smaller_panel'])} bits per fact (reported); ADDRESS STABLE non-finite cells counted as 0: {e['stable'].get('non_finite', 0)}")
            if e.get("sustained_success") and e["sustained_success"]["cells_with_first_success"]:
                lines.append(f"- {arm} at {ct}: {e['sustained_success']['label']}")
    return _section("Classes per arm and cell type", lines)


def _paired_section(res: Mapping[str, Any]) -> str:
    lines = ["d(X) over the 20 pairs of cells, success under S0's criteria (the readings H20-B, H20-C and H20-D use), with d under P9-II's criteria printed beside it (it enters no reading).", "", "| arm | cell type | label (S0's criteria) | d | p (sign test) | d under P9-II's criteria | label (P9-II's criteria) |", "|---|---|---|---|---|---|---|"]
    for arm, per in res["paired"].items():
        for ct, p in per.items():
            lines.append(f"| {arm} | {ct} | {p['s0']['label']} | {p['s0']['d']} | {fmt(p['s0']['p_value'])} | {p['p9ii']['d']} | {p['p9ii']['label']} |")
    for ct in core.CORE_CELLTYPES:
        a = res["arms"]["A2"][ct].get("d_against_a1")
        if a:
            lines.append(f"\nd(A2 against A1) at {ct} (descriptive): {a['d']} (p = {fmt(a['p_value'])}).")
    if res.get("a0_failed_cells_8k16k") is not None and C.h20d_note(res["a0_failed_cells_8k16k"]):
        lines.append(f"\nH20-D note: {C.h20d_note(res['a0_failed_cells_8k16k'])}.")
    return _section("Paired comparisons with A0", lines)


def _qualification_section(res: Mapping[str, Any]) -> str:
    sel = res["selection"]
    lines = [f"Preference order, fixed: {', '.join(core.PREFERENCE_ORDER)} (C4 = A5-D; the order was fixed in revision 3, before P9-II ran; the occupant of C4 was chosen after).", ""]
    for arm, v in sel["per_arm"].items():
        lines.append(f"- {arm}: qualifies at {v['scope'] or 'no size'}" + ("; " + "; ".join(f"{ct}: {t}" for ct, t in v["inconsistent_notes"].items()) if v["inconsistent_notes"] else "") + (f"; SINGLE-STUDY EVIDENCE at {', '.join(v['single_study_sizes'])}" if v["single_study_sizes"] else ""))
    if sel["answer_only_suffices"]:
        lines.append(f"- {sel['answer_only_suffices']}")
    lines += [f"- {x}" for x in sel["also_qualifies"]]
    return _section("Qualification (section 8.5)", lines)


def _annotations_section(res: Mapping[str, Any]) -> str:
    q2 = res["q2_status"]
    lines = [f"- OVERLOAD: {res['overload']}", f"- WX block status: {q2['wx']}; {res['record_length']['label']}", f"- 65,536 probe status: {q2['probe']}; {res['probe'].get('label') or '—'}"]
    for ct, v in res["record_length"]["celltypes"].items():
        lines.append(f"- WX at {ct}: {v['class']['label']} ({v['class']['successes']}/{v['class']['evaluated']} cells; ADDRESS STABLE {v['stable']['label'] or 'no'}; descriptive AUC of max_s a_s for answer sites against the other 55 positions: median {fmt(v.get('auc_median'))}; i median {fmt(v.get('bits_median'))} bits per fact)")
    lines.append("- A failure of WX is not evidence that the record length is required; WX is never the qualified interface.")
    return _section("Annotations on the candidate (section 8.6)", lines)


def _hypotheses_section(res: Mapping[str, Any]) -> str:
    lines = ["| hypothesis | reading | notes |", "|---|---|---|"]
    for h, v in res["hypotheses"].items():
        notes = "; ".join(f"{k}: {x}" for k, x in v.items() if k != "reading" and x not in (None, ""))
        lines.append(f"| {h} | {v['reading']} | {notes} |")
    lines.append("\nEvery reading is about S0's draws. A hypothesis reading is not a success of the science.")
    return _section("Hypothesis readings (section 8.7)", lines)


def _a6_section(res: Mapping[str, Any]) -> str:
    lines = ["| cell type | draw | A6 accuracy A | A6 accuracy B | evaluated |", "|---|---|---|---|---|"]
    for ct, per in res["a6"].items():
        for d, r in per.items():
            lines.append(f"| {ct} | {d} | {fmt(r['accuracy_a'])} | {fmt(r['accuracy_b'])} | {r['evaluated']} |")
    return _section("Oracle-query reference A6 per draw", lines)


def render_markdown(result: Mapping[str, Any], *, banner: str | None = None) -> str:
    """RESULTS.md. Rows 1 to 3 print only their status (no class is derived); rows 4 to 6 print every section."""
    out = ["# P10-S0 — addressing qualification (ADR-0020 design revision 4)\n", f"{banner_text(result)}\n", f"{NUMBER_LABELS}\n"]
    if banner:
        out.append(f"**{banner}**\n")
    out.append(_arm_selection(result))
    row = result["outcome"]["row"]
    head = _outcome_header(result)
    if row in (4, 5):
        head += ["", *_qualified_text(result)]
    elif row == 6:
        head += ["", *_not_qualified(result)]
    out.append(_section("Outcome (section 8.7)", head))
    if row in (4, 5, 6) or "arms" in result:
        out += [_classes_section(result), _paired_section(result), _qualification_section(result), _annotations_section(result), _hypotheses_section(result), _a6_section(result)]
    asm = result["assessment"]
    out.append(_section("Assessment", [f"- interpretable: {asm['interpretable']}", *[f"- {r}" for r in asm["engineering"]], *[f"- {k}: {v}" for k, v in asm["replaced_draws"].items()]] or ["- none"]))
    out.append(_section("What may not be said", [f"- {s}" for s in NOT_CLAIMED]))
    return "\n".join(out)


def classes_csv(result: Mapping[str, Any]) -> str:
    buf = io.StringIO()
    if "A5-D" in (result.get("arms") or {}):
        buf.write("\n".join(core.csv_header_lines()) + "\n")  # A5-D rows carry the fourth-arm string, P9-II's F1 annotation and the fixed provenance sentence
    w = csv.writer(buf)
    w.writerow(["arm", "celltype", "s0_class", "p9ii_criteria_class", "replication", "consistency", "address_stable", "evaluated", "successes", "draws_evaluated", "draws_succeeded", "per_draw_bound", "lm_reduced", "meets"])
    for arm, per in (result.get("arms") or {}).items():
        for ct, e in per.items():
            s = e["s0"]
            w.writerow([arm, ct, s["label"], e["p9ii_criteria"]["label"], e["replication"], e["consistency"]["label"] if e["consistency"] else "", e["stable"]["label"] or "", s["evaluated"], s["successes"], s["draws_evaluated"], s["draws_succeeded"], fmt(s["per_draw_bound"]) if s["per_draw_bound"] is not None else "", s["lm_reduced"], e["meets"]])
    return buf.getvalue()


def write_report(run_dir: Path, out_dir: Path, *, banner: str | None = None) -> list[Path]:
    """Read ``<run_dir>/analysis.json`` and write ``RESULTS.md``, ``results.json`` and ``classes.csv`` into ``out_dir`` (never over an existing file)."""
    analysis = core.read_record(run_dir / "analysis.json", "analysis")
    result = analysis["result"]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "RESULTS.md", out_dir / "results.json", out_dir / "classes.csv"]
    for p in paths:
        if p.exists():
            raise FileExistsError(p)
    md = render_markdown(result, banner=banner)
    problems = check_a5d_provenance(md)
    if problems:
        raise ValueError(f"the A5-D provenance block is missing from sections {problems}")
    paths[0].write_text(md, encoding="utf-8")
    product = core.stamp(core.jsonable({**core.envelope("analysis"), "banner": banner, "result": result, "not_claimed": list(NOT_CLAIMED), "identity": analysis.get("identity"), "environment": analysis.get("environment")}))
    text = json.dumps(product, default=str, ensure_ascii=False)
    core.assert_provenance(text, "results.json")
    csv_text = classes_csv(result)
    core.assert_provenance(csv_text, "classes.csv")
    write_json(paths[1], product)
    paths[2].write_text(csv_text, encoding="utf-8")
    return paths
