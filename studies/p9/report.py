# ruff: noqa: E501
"""P9 reporting (package I6): decision map, study status, CSV/JSON/Markdown and the dashboard.

Specification: ADR-0017 section 8.6 (study status ENGINEERING_FAIL / INCOMPLETE; the denominator is
never reduced), 8.7 (decision map), 13 (what must not be claimed); the human draft section 13 lists the
dashboard plots.

Labelling rule for every number written: measured, analytical or hypothetical (and SIMULATED for page
misses and LOGICAL for key products, which are never measured I/O or efficiency); logical work is never
described as a speedup; every report states "Astra review: NOT_PERFORMED" and that Claude review is not
Astra review and not human approval. No interpretation text is generated: tables and captions only say
what is shown.

Figures are described first as ``FigureSpec`` (pure data; ``None`` marks a missing or undefined value
and is never drawn as zero) and then rendered either as self-contained SVG (pure Python, always
available, used in the dashboard) or, optionally, as PNG with matplotlib. matplotlib is imported lazily
inside ``render_png`` only; it is not a dependency of the project. To use it::

    uv run --locked --with matplotlib==3.10.8 python -m studies.p9.report --png ...

(the version that was present in the local uv cache for the P8 report). The test suite and mypy never
import it.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import argparse
import base64
import csv
import html
import importlib
import io
import json
import math
import sys
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from arborlm.io import atomic_write, file_sha256, read_json, write_json

from . import analysis_a, analysis_b, analysis_c, analysis_d, core
from .core import (
    ClassResult,
    EvalKey,
    EvalRecord,
    SimRecord,
    StageManifest,
    TrainRecord,
    UpdateRecord,
)

STATUSES = ("COMPLETE", "INCOMPLETE", "ENGINEERING_FAIL")
LABELS = ("measured", "analytical", "hypothetical")
NOT_PERFORMED = "Astra review: NOT_PERFORMED"
REVIEW_STATEMENT = (
    f"{NOT_PERFORMED}. This report is the output of an implementation self-check. It is not independent review, "
    "not Astra validation and not human approval. Claude review is not Astra review."
)
TRAINING_STAGES = ("train", "incremental")
REGISTERED = "registered"
NOT_CLAIMED = (
    "That slot entropy, distinct slots or the floored information sum show capacity.",
    "That R0a, R1, R2 or oracle-branch results are system results, or that the ladder gives upper bounds.",
    "That logical work is measured efficiency, or that simulation or the key-traffic identity is storage I/O.",
    "That cross-query locality found here would arise without planted structure; within-query packing is not evidence about clusters.",
    "That the usage term revives dead slots, unless the revival count shows it.",
    "That Lane D shows continual learning in general, or teacher absorption.",
    "Anything about composition or reasoning.",
    "Any generalization across data draws, beyond 65,536 slots, or to a trainable backbone.",
)
EVIDENCE_BOUNDARY = (
    "A 27,392-parameter frozen byte-level backbone, synthetic facts, RAM only, one data draw, two initialization seeds and one "
    "replicate parent. Nothing here supports claims about large models, natural-language knowledge, composition, teacher "
    "absorption, physical I/O, throughput or production use. The earlier studies (P4-P8) are cited in ADR-0017 section 1."
)
NO_AUTHORIZATION = "No outcome authorizes further training, storage experiments or scaling."
CAPACITY_ARCHS = ("flat", "learned_tree")
GAP_COMPONENTS = {
    "R2-R1": "keys (R2 - R1)",
    "R1-R0a": "representation (R1 - R0a)",
    "R0a-R0": "interference (R0a - R0)",
}
NO_DECISION_CLASSES = (
    "no result",
    "UNDERTRAINED",
    core.INTERMEDIATE,
    core.NOT_REPLICATED,
    core.NOT_EVALUATED,
    analysis_a.INCOMPLETE,
)


# --- study status ---------------------------------------------------------------------------------------------
def _registered(manifests: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [m for m in manifests if m.get("mode") == REGISTERED]


def missing_cells(
    manifests: Sequence[StageManifest], registered: Collection[str] | None = None
) -> list[str]:
    """Registered labels with no completed training record in any registered-mode manifest of a training
    stage (``core.all_labels``, or ``registered`` when the matrix was amended before the freeze). The
    denominator is the registered set; it is never reduced here."""
    expected = set(registered) if registered is not None else set(core.all_labels())
    done = {
        t["label"]
        for m in _registered(manifests)
        if m["stage"] in TRAINING_STAGES
        for t in m["tasks"]
        if t["status"] == "completed"
    }
    return sorted(expected - done)


def study_status(manifests: Sequence[StageManifest], engineering_defects: Sequence[str]) -> str:
    """ENGINEERING_FAIL for identity, determinism, checkpoint or gradient-reach defects only (a
    regularizer being inactive is a recorded property, not a failure); INCOMPLETE if any registered
    cell lacks a record or any task of a registered stage did not complete (no class for a lane with a
    missing mandatory cell); else COMPLETE."""
    if engineering_defects or any(m["status"] == "ENGINEERING_FAIL" for m in manifests):
        return "ENGINEERING_FAIL"
    if missing_cells(manifests) or any(m["status"] != "COMPLETE" for m in _registered(manifests)):
        return "INCOMPLETE"
    return "COMPLETE"


def failed_tasks(manifests: Sequence[StageManifest]) -> list[dict[str, Any]]:
    """Every task that did not complete in any manifest (kept, never hidden)."""
    return [
        {
            "stage": m["stage"],
            "mode": m["mode"],
            "label": t["label"],
            "status": t["status"],
            "reason": t["reason"],
            "returncode": t["returncode"],
        }
        for m in manifests
        for t in m["tasks"]
        if t["status"] != "completed"
    ]


# --- decision map ---------------------------------------------------------------------------------------------------
def _by_subject(results: Sequence[ClassResult]) -> dict[str, ClassResult]:
    return {r["subject"]: r for r in results}


def _withheld(r: ClassResult) -> bool:
    return "interpretation_withheld" in r["details"]


def decision_items(results: Sequence[ClassResult], status: str) -> dict[int, dict[str, Any]]:
    """The five items of ADR 8.7 as data: ``{"applies", "text", ...}`` per item. Capacity items read the
    matched-exposure classes of Lane A; a class withheld for LEAKAGE counts as 'no capacity decision'."""
    by = _by_subject(results)
    caps = {a: by.get(f"capacity/{a}") for a in CAPACITY_ARCHS}
    ladder = by.get("ladder")
    gates = by.get(analysis_a.GATES_REPORT)
    items: dict[int, dict[str, Any]] = {
        n: {"applies": False, "text": f"Item {n}: not triggered."} for n in range(1, 6)
    }
    if status == "ENGINEERING_FAIL":
        for n in items:
            items[n]["text"] = (
                f"Item {n}: no scientific decision; the study status is ENGINEERING_FAIL."
            )
        return items

    def cls_of(a: str) -> str:
        r = caps[a]
        return "no result" if r is None else ("LEAKAGE" if _withheld(r) else r["cls"])

    positive: list[str] = []
    acceptance: dict[str, str] = {}
    for a in CAPACITY_ARCHS:
        r = caps[a]
        if r is not None and cls_of(a) == "CAPACITY_POSITIVE":
            notes = [n for n in r["annotations"] if n.startswith("OPTIMIZER")]
            note = notes[0] if notes else ""
            if note == analysis_a.A_OPT_DEP:
                continue
            positive.append(a)
            if note:
                acceptance[a] = note
    if positive:
        text = f"Item 1: {', '.join(positive)} CAPACITY_POSITIVE without OPTIMIZER-DEPENDENT: a separately approved capacity-scaling protocol may be proposed."
        if acceptance:
            text += (
                " This needs the human lead's explicit acceptance of "
                + "; ".join(f"'{v}' ({k})" for k, v in acceptance.items())
                + "."
            )
        items[1] = {
            "applies": True,
            "text": text,
            "archs": positive,
            "needs_acceptance": bool(acceptance),
            "acceptance_for": acceptance,
        }

    partial_or_positive = [
        a for a in CAPACITY_ARCHS if cls_of(a) in ("CAPACITY_POSITIVE", "CAPACITY_PARTIAL")
    ]
    locality = [
        r
        for r in results
        if r["subject"].startswith("C1/") and not r["subject"].endswith("vs_flat_same_dose")
    ]
    locality_positive = [
        r["subject"] for r in locality if r["cls"] == "LOCALITY_POSITIVE" and not _withheld(r)
    ]
    if partial_or_positive and not locality_positive:
        evaluated = [
            r
            for r in locality
            if not analysis_c.is_not_evaluated(r["cls"]) and r["cls"] != analysis_a.INCOMPLETE
        ]
        state = "evaluated and not positive" if evaluated else "not evaluated or incomplete"
        items[2] = {
            "applies": True,
            "text": f"Item 2: capacity is positive or partial for {', '.join(partial_or_positive)} and locality is not positive ({state}): redesign placement or routing.",
            "archs": partial_or_positive,
        }

    material = list(ladder["details"].get("material", [])) if ladder is not None else []
    not_supported = [a for a in CAPACITY_ARCHS if cls_of(a) == "CAPACITY_NOT_SUPPORTED"]
    indicated: dict[str, list[str]] = {}
    for a in not_supported:
        r = caps[a]
        parts = [
            f"{GAP_COMPONENTS[t.split(':')[1]]} at {t.split(':')[0]} slots"
            for t in material
            if t.split(":")[1] in GAP_COMPONENTS
        ]
        if r is not None:
            if analysis_a.A_KEY_WIDTH in r["annotations"]:
                parts.append("key width (KEY-WIDTH-LIMITED)")
            if analysis_a.A_OPT_DEP in r["annotations"]:
                parts.append("optimizer (OPTIMIZER-DEPENDENT)")
        if parts:
            indicated[a] = parts
    if indicated:
        items[3] = {
            "applies": True,
            "text": "Item 3: capacity not supported with an indicated component: "
            + "; ".join(f"{a}: investigate {', '.join(p)}" for a, p in indicated.items())
            + ".",
            "indicated": indicated,
        }

    ceiling = (
        str(gates["details"].get("TASK_CEILING_FAIL", "none")) if gates is not None else "none"
    )
    unexplained = [a for a in not_supported if a not in indicated]
    if ceiling != "none" or unexplained:
        why = ([f"TASK_CEILING_FAIL at {ceiling}"] if ceiling != "none" else []) + (
            [f"capacity not supported with no material gap for {', '.join(unexplained)}"]
            if unexplained
            else []
        )
        items[4] = {
            "applies": True,
            "text": "Item 4: " + "; ".join(why) + ": pause the line or redesign the testbed.",
            "ceiling_fail": ceiling,
        }

    undecided = [
        a for a in CAPACITY_ARCHS if cls_of(a) in NO_DECISION_CLASSES or cls_of(a) == "LEAKAGE"
    ]
    if undecided or not any(r["subject"].startswith("capacity/") for r in results):
        parts = [f"{a}: {cls_of(a)}" for a in undecided] or ["no Lane A capacity result"]
        decided = [a for a in CAPACITY_ARCHS if a not in undecided]
        text = f"Item 5: {'; '.join(parts)}: no capacity decision."
        via4 = not decided and not items[4]["applies"]
        if via4:
            text += " Item 4 applies (pause the line or redesign the testbed) unless the human lead decides otherwise."
            items[4] = {
                "applies": True,
                "text": "Item 4: applies by default through item 5 (no capacity decision), unless the human lead decides otherwise.",
                "via_item_5": True,
            }
        items[5] = {"applies": True, "text": text, "archs": undecided, "item_4_by_default": via4}
    if status == "INCOMPLETE":
        for n in items:
            items[n]["text"] += (
                " (study status INCOMPLETE: lanes with a missing cell have no class; denominators were not reduced)"
            )
    return items


def decision_map(results: Sequence[ClassResult], status: str) -> list[str]:
    """The five-item decision map of ADR 8.7 as sentences, from the lane results; item 1 requires the
    human lead's explicit acceptance when the optimizer annotation reads OPTIMIZER-ARM UNINFORMATIVE or
    'OPTIMIZER-DEPENDENT: not assessed'. No outcome authorizes further training, storage experiments or
    scaling."""
    items = decision_items(results, status)
    return [items[n]["text"] for n in sorted(items)] + [NO_AUTHORIZATION]


# --- tables ---------------------------------------------------------------------------------------------------------------
def _numeric_leaves(value: Any, path: str = "", depth: int = 0) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    if isinstance(value, bool):
        return out
    if isinstance(value, int | float):
        return [(path, float(value))]
    if depth >= 5:
        return out
    if isinstance(value, Mapping):
        for k, v in value.items():
            out += _numeric_leaves(v, f"{path}/{k}" if path else str(k), depth + 1)
    return out


def basis_of(r: ClassResult) -> str:
    subject = r["subject"]
    if subject == "key_traffic_identity":
        return "analytical"
    if subject.startswith(("C1/", "hierarchy", "d09_sweep")):
        return "SIMULATED (value-page misses of a model; not physical I/O)"
    if subject.startswith("tree_comparison"):
        return "measured (information); logical key products are analytical"
    return "measured"


def key_numbers(r: ClassResult, limit: int = 8) -> dict[str, Any]:
    """Up to ``limit`` numeric leaves of the details (finite values, in path order) for the tables."""
    leaves = [(p, v) for p, v in _numeric_leaves(r["details"]) if "/per_fact" not in p]
    chosen = [
        (p, v)
        for p, v in leaves
        if any(
            tag in p
            for tag in (
                "ratio",
                "/I",
                "ustar",
                "accuracy",
                "a_A",
                "a_B",
                "lowest",
                "e_ratio",
                "forgetting",
            )
        )
    ] or leaves
    return {p: analysis_a.jsonable(v) for p, v in chosen[:limit]}


def results_table(results: Sequence[ClassResult]) -> list[dict[str, object]]:
    """Flat rows (lane, subject, class, annotations, key numbers) for CSV and JSON."""
    rows: list[dict[str, object]] = []
    for r in results:
        rows.append(
            {
                "lane": r["lane"],
                "subject": r["subject"],
                "class": r["cls"],
                "panel_A": r["panel_classes"].get("A", ""),
                "panel_B": r["panel_classes"].get("B", ""),
                "annotations": " | ".join(r["annotations"]),
                "basis": basis_of(r),
                "missing_records": len(r["details"].get("missing", [])),
                "interpretation_withheld": r["details"].get("interpretation_withheld", ""),
                "key_numbers": json.dumps(key_numbers(r), sort_keys=True),
            }
        )
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    columns = (
        list(rows[0])
        if rows
        else [
            "lane",
            "subject",
            "class",
            "panel_A",
            "panel_B",
            "annotations",
            "basis",
            "missing_records",
            "interpretation_withheld",
            "key_numbers",
        ]
    )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in row.items()})
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, buffer.getvalue().encode())


def _md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(
    results: Sequence[ClassResult],
    status: str,
    decisions: Sequence[str],
    *,
    manifests: Sequence[StageManifest] = (),
    missing: Sequence[str] = (),
) -> str:
    """The Markdown report (``RESULTS.md`` skeleton); includes the evidence boundary, what must not be
    claimed (ADR 13) and the status of reviews. It states classes and numbers, never an interpretation."""
    lines = [
        "# P9 results (ADR-0017): skeleton generated from records",
        "",
        f"**Study status: {status}.** {REVIEW_STATEMENT}",
        "",
        "Labels: every number is *measured* (from the evaluation records), *analytical* (logical key products, the key-traffic identity, "
        "exact-retrieval accuracy by construction) or *hypothetical* (none is written here). Page misses are **SIMULATED** value-page "
        "misses of a model, never physical I/O. Logical work is not measured efficiency and is never described as a speedup.",
        "",
        "## Evidence boundary",
        "",
        EVIDENCE_BOUNDARY,
        "",
        "## Study status",
        "",
        f"- Status: **{status}** (`INCOMPLETE`: any registered cell lacks a record; no class is derived for a class whose mandatory cells are missing; the denominator is never reduced).",
        f"- Registered cells without a completed training record: {len(missing)}"
        + (f" (first: {', '.join(list(missing)[:5])})" if missing else "."),
        "",
        "## Results by lane",
    ]
    for lane, title in (
        ("A", "Lane A: capacity"),
        ("B", "Lane B: optimization and collapse"),
        ("C", "Lane C: locality (SIMULATED)"),
        ("D", "Lane D: incremental"),
    ):
        rows = [r for r in results if r["lane"] == lane]
        lines += ["", f"### {title}", ""]
        if not rows:
            lines += ["No results."]
            continue
        lines += [
            "| subject | class | panel A | panel B | annotations | basis | key numbers |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            note = "; ".join(r["annotations"])
            nums = ", ".join(f"{k}={v}" for k, v in list(key_numbers(r, 4).items()))
            lines.append(
                f"| {_md_cell(r['subject'])} | **{_md_cell(r['cls'])}** | {_md_cell(r['panel_classes'].get('A', ''))} | {_md_cell(r['panel_classes'].get('B', ''))} | {_md_cell(note)} | {_md_cell(basis_of(r))} | {_md_cell(nums)} |"
            )
        withheld = [r["subject"] for r in rows if _withheld(r)]
        if withheld:
            lines += [
                "",
                "Not interpreted (LEAKAGE until the auditor explains it): " + ", ".join(withheld),
            ]
    lines += ["", "## Decision map (ADR 8.7)", ""]
    lines += [f"- {d}" for d in decisions]
    failed = failed_tasks(manifests)
    lines += ["", "## Failed, killed or skipped tasks (kept, never retried)", ""]
    lines += [
        f"- {f['stage']} / {f['label']}: {f['status']}"
        + (f" ({f['reason']})" if f["reason"] else "")
        for f in failed
    ] or ["None recorded."]
    lines += ["", "## What must not be claimed (ADR 13)", ""] + [f"- {c}" for c in NOT_CLAIMED]
    lines += ["", "## Reviews", "", REVIEW_STATEMENT, "", NO_AUTHORIZATION, ""]
    return "\n".join(lines)


# --- figures ----------------------------------------------------------------------------------------------------------------
@dataclass
class Series:
    name: str
    x: list[float | str | None]
    y: list[float | None]
    style: str = "solid"  # solid | dashed


@dataclass
class FigureSpec:
    """One plot as data. ``kind`` is line, scatter, bar or heatmap; ``None`` is missing or undefined and is
    never drawn as zero; ``label`` is MEASURED, SIMULATED, LOGICAL or ANALYTICAL; ``question`` is the
    question the plot answers (the human draft asks the lead to state it for every plot)."""

    key: str
    title: str
    question: str
    label: str
    kind: str
    xlabel: str = ""
    ylabel: str = ""
    series: list[Series] = field(default_factory=list)
    xlog: bool = False
    row_labels: list[str] = field(default_factory=list)
    col_labels: list[str] = field(default_factory=list)
    values: list[list[float | None]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def finite_points(self) -> int:
        if self.kind == "heatmap":
            return sum(1 for row in self.values for v in row if v is not None and math.isfinite(v))
        return sum(1 for s in self.series for y in s.y if y is not None and math.isfinite(y))


@dataclass
class ReportInputs:
    """Records read for the dashboard: evaluation index, per-cell train records and update logs, simulation records."""

    index: Mapping[EvalKey, EvalRecord] = field(default_factory=dict)
    train: Mapping[str, TrainRecord] = field(default_factory=dict)
    updates: Mapping[str, Sequence[UpdateRecord]] = field(default_factory=dict)
    sims: Mapping[str, Sequence[SimRecord]] = field(default_factory=dict)
    exposure: int = core.DEFAULT_EXPOSURE
    unreadable: Sequence[str] = ()


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _eval_at(
    inputs: ReportInputs, cell: core.Cell, update: int, panel: str = "A"
) -> EvalRecord | None:
    return inputs.index.get((cell.label, update, core.PANEL_STREAM[panel]))


def _mean(values: Sequence[float | None]) -> float | None:
    return (
        sum(v for v in values if v is not None) / len(values)
        if values and all(v is not None for v in values)
        else None
    )


def _capacity_figure(inputs: ReportInputs, estimand: str) -> FigureSpec:
    fixed = estimand == "fixed_compute"
    fig = FigureSpec(
        key="capacity_" + estimand,
        title="Information retained against memory size, "
        + (
            "fixed compute (U_16K updates at every size)"
            if fixed
            else "matched exposure (E per fact)"
        ),
        question="Does the information retained about the answers (I_acc, Fano bits) grow with the number of slots, and how does it compare with the matched dense adapter? Shown for the "
        + estimand
        + " estimand; the matched-exposure classes are the primary ones.",
        label="MEASURED",
        kind="line",
        xlabel="memory slots (log scale)",
        ylabel="I_acc (bits)",
        xlog=True,
        notes=[
            "Mean over the two B101 seeds; a point is drawn only if both seeds have a record. Panel A solid, panel B dashed."
        ],
    )
    arms = (
        ("flat memory (A1)", "A1", "flat", "adamw"),
        ("learned tree (A2)", "A2", "learned_tree", "adamw"),
        ("dense adapter (A8)", "A8", "dense", "adamw"),
        ("flat, row-lazy Adam (A10)", "A10", "flat", "lazy"),
    )
    for name, block, arch, optimizer in arms:
        for panel, style in (("A", "solid"), ("B", "dashed")):
            ys: list[float | None] = []
            for slots in core.SLOTS_BY_SIZE:
                vals: list[float | None] = []
                for seed in core.INIT_SEEDS:
                    cell = analysis_a.find_cell(block, arch, slots, optimizer=optimizer, seed=seed)
                    rec = (
                        None
                        if cell is None
                        else _eval_at(
                            inputs,
                            cell,
                            analysis_a.snapshot_pair(cell, inputs.exposure, estimand)[1],
                            panel,
                        )
                    )
                    vals.append(None if rec is None else analysis_a.info_of(rec))
                ys.append(_mean(vals))
            fig.series.append(
                Series(f"{name} {panel}", [float(s) for s in core.SLOTS_BY_SIZE], ys, style)
            )
    return fig


def _slot_use_figure(inputs: ReportInputs) -> FigureSpec:
    fig = FigureSpec(
        key="slot_use_quality",
        title="Useful slots (U*) against accuracy, every evaluated cell",
        question="Do cells that use more useful slots answer more facts, or does the count of slots in use say nothing about quality?",
        label="MEASURED",
        kind="scatter",
        xlabel="U* (useful slots)",
        ylabel="accuracy on panel A",
        notes=[
            "One point per cell at its matched-exposure snapshot; cells whose U* is not recorded or NOT INTERPRETABLE are not drawn."
        ],
    )
    by_block: dict[str, Series] = {}
    for cell in core.cells():
        update = core.updates(cell, inputs.exposure)
        rec = _eval_at(inputs, cell, update)
        if rec is None:
            continue
        ustar = _num(rec.get("useful_slots")) if rec.get("ustar_interpretable") is True else None
        s = by_block.setdefault(cell.block, Series(cell.block, [], []))
        s.x.append(ustar)
        s.y.append(rec["correct"] / rec["facts"])
    fig.series = list(by_block.values())
    return fig


def _exposure_figure(inputs: ReportInputs) -> FigureSpec:
    fig = FigureSpec(
        key="per_fact_exposure_recall",
        title="Exposure per fact and recall",
        question="Did every fact get the exposure the design says it did (equal frequency), and does recall depend on the exposure a fact received?",
        label="MEASURED",
        kind="scatter",
        xlabel="exposures per fact (minimum over facts)",
        ylabel="accuracy on panel A",
        notes=[
            "From the training records and the evaluation records; the per-fact distribution files themselves are not read here."
        ],
    )
    low, high = Series("min exposure", [], []), Series("max exposure", [], [])
    for label, tr in sorted(inputs.train.items()):
        try:
            cell = core.parse_label(label)
        except ValueError:
            continue
        rec = _eval_at(inputs, cell, core.updates(cell, inputs.exposure))
        acc = None if rec is None else rec["correct"] / rec["facts"]
        low.x.append(_num(tr.get("exposure_per_fact_min")))
        low.y.append(acc)
        high.x.append(_num(tr.get("exposure_per_fact_max")))
        high.y.append(acc)
    fig.series = [low, high]
    return fig


def _entropy_figure(inputs: ReportInputs) -> FigureSpec:
    cells = [
        c
        for c in core.cells()
        if c.slots == 16384
        and c.block in ("A1", "A2", "B1", "C1")
        and c.parent == core.PRIMARY_PARENT
        and c.seed == core.INIT_SEEDS[0]
    ]
    fig = FigureSpec(
        key="entropy_coverage",
        title="Entropy-effective slots and distinct slots, 16,384-slot cells (seed 1701)",
        question="How many slots does each cell read, by distinct count and by entropy? Entropy and distinct counts are reported, never used alone as evidence of capacity.",
        label="MEASURED",
        kind="bar",
        ylabel="slots",
        notes=[
            "Hard top-8 answer-site selections; soft value is the exp of H(u) from the soft inclusion. Missing values are left blank."
        ],
    )
    names = [f"{c.block}/{c.arch[:4]}/au{c.alpha_u:g}/ac{c.alpha_c:g}" for c in cells]
    for key, name in (
        ("distinct", "distinct selected slots"),
        ("entropy_effective_hard", "entropy-effective (hard)"),
        ("entropy_effective_soft", "entropy-effective (soft)"),
    ):
        ys: list[float | None] = []
        for c in cells:
            rec = _eval_at(inputs, c, core.updates(c, inputs.exposure))
            ys.append(None if rec is None else _num(rec.get("usage", {}).get(key)))
        fig.series.append(Series(name, list(names), ys))
    return fig


def _step_of(u: Mapping[str, Any]) -> int | None:
    value = _num(u.get("update"))
    return None if value is None else int(value)


def _u_norm(u: Mapping[str, Any], which: str, group: str) -> float | None:
    """A per-group number of an update record, or None when the record lacks it (never a KeyError)."""
    block = u.get(which)
    return _num(block.get(group)) if isinstance(block, Mapping) else None


def _lambda_note(inputs: ReportInputs, label: str) -> str:
    tr = inputs.train.get(label)
    lu, lc = (None, None) if tr is None else (_num(tr.get("lambda_u")), _num(tr.get("lambda_c")))
    if lu is None or lc is None:
        return "Coefficients: see the train record (not loaded or not recorded)."
    return f"lambda_u = {lu:g}, lambda_c = {lc:g} (absolute coefficients, ADR 7)."


def _heat_figure(inputs: ReportInputs, cell: core.Cell, which: str, bins: int = 12) -> FigureSpec:
    log = inputs.updates.get(cell.label, [])
    groups = list(core.PARAM_GROUPS)
    steps = [(u, _step_of(u)) for u in log]
    n = max((k for _, k in steps if k is not None), default=0)
    edges = [round(i * n / bins) for i in range(bins + 1)] if n else []
    values: list[list[float | None]] = []
    for g in groups:
        row: list[float | None] = []
        for i in range(bins):
            sel = [
                _u_norm(u, which, g)
                for u, k in steps
                if edges and k is not None and edges[i] < k <= edges[i + 1]
            ]
            good = [v for v in sel if v is not None]
            row.append(math.log10(sum(good) / len(good)) if good and sum(good) > 0 else None)
        values.append(row)
    return FigureSpec(
        key=f"heatmap_{which}_{cell.label}",
        title=f"log10 mean {which.replace('_', ' ')} by parameter group and update bin: {cell.label}",
        question="Where does the gradient go (selected, candidate and untouched keys, values, router, projections), and does it reach the router and the unselected keys?",
        label="MEASURED",
        kind="heatmap",
        xlabel="update bin",
        ylabel="parameter group",
        row_labels=groups,
        col_labels=[f"{edges[i]}-{edges[i + 1]}" for i in range(bins)]
        if edges
        else [str(i) for i in range(bins)],
        values=values,
        notes=["Zero or missing norms are blank (log undefined), never drawn as the lowest value."],
    )


def _locality_figure(inputs: ReportInputs) -> FigureSpec:
    labels = [
        c
        for c in core.cells()
        if c.block in ("A1", "A2", "C1")
        and c.slots == 16384
        and c.parent == core.PRIMARY_PARENT
        and c.seed == core.INIT_SEEDS[0]
    ]
    cols = [f"rho {rho:g} / R {rows}" for rho, rows in analysis_c.PRIMARY_SETTINGS]
    rows_labels: list[str] = []
    values: list[list[float | None]] = []
    for cell in labels:
        recs = inputs.sims.get(cell.label, [])
        layouts = sorted({r["layout"] for r in recs})
        for layout in layouts:
            row: list[float | None] = []
            for rho, rows in analysis_c.PRIMARY_SETTINGS:
                match = [
                    r
                    for r in recs
                    if r["layout"] == layout
                    and r["rows_per_page"] == rows
                    and math.isclose(r["cache_fraction"], rho)
                    and r["tie"] == "asc"
                    and r["stream"] == "panel_a"
                    and r["trace_kind"] == "answer"
                ]
                value = None if not match or match[0]["degenerate"] else _num(match[0]["e_ratio"])
                row.append(value)
            rows_labels.append(f"{cell.block}/{cell.arch[:4]}/ac{cell.alpha_c:g} {layout}")
            values.append(row)
    return FigureSpec(
        key="locality_null_adjusted",
        title="Null-adjusted locality E (actual misses / count-preserving null) by layout and cache setting (SIMULATED)",
        question="Is the miss count below what a count-preserving null gives, under which layout and cache setting? A value near 1 means no locality beyond popularity; degenerate or undefined settings are blank.",
        label="SIMULATED",
        kind="heatmap",
        xlabel="cache fraction / rows per page (tie asc, panel A, answer-site trace)",
        ylabel="cell and layout",
        row_labels=rows_labels,
        col_labels=cols,
        values=values,
        notes=["SIMULATED value-page misses of a model, not physical I/O."],
    )


def _trace_figure(inputs: ReportInputs, cell: core.Cell) -> FigureSpec:
    log = [(u, _step_of(u)) for u in inputs.updates.get(cell.label, [])]
    log = [(u, k) for u, k in log if k is not None]
    xs: list[float | str | None] = [float(k) for _, k in log if k is not None]

    def column(which: str, group: str) -> list[float | None]:
        return [_u_norm(u, which, group) for u, _ in log]

    series = [
        Series(
            "usage gradient norm (selected keys)",
            list(xs),
            column("grad_norm_usage", "keys_selected"),
        ),
        Series(
            "co-access gradient norm (selected keys)",
            list(xs),
            column("grad_norm_coaccess", "keys_selected"),
        ),
        Series(
            "task gradient norm (selected keys)",
            list(xs),
            column("grad_norm_task", "keys_selected"),
        ),
        Series(
            "parameter change, untouched keys",
            list(xs),
            column("param_change_norm", "keys_untouched"),
            "dashed",
        ),
        Series(
            "parameter change, selected keys",
            list(xs),
            column("param_change_norm", "keys_selected"),
            "dashed",
        ),
    ]
    return FigureSpec(
        key=f"traces_{cell.label}",
        title=f"Regularizer gradients and key movement per update: {cell.label}",
        question="Do the regularizer terms move keys that have no task gradient (P8's open question)? Gradient norms of the task loss and of each regularizer, and the change of the key rows, per update.",
        label="MEASURED",
        kind="line",
        xlabel="update",
        ylabel="norm",
        series=series,
        notes=[_lambda_note(inputs, cell.label)],
    )


def _retention_figure(inputs: ReportInputs) -> FigureSpec:
    fig = FigureSpec(
        key="sequential_retention",
        title="Sequential A then B: accuracy on A and on B during phase B",
        question="Is the old fact set A retained while the new set B is acquired, compared with the dense sequential arm? Points at the end of phase A, half way and at the end of phase B.",
        label="MEASURED",
        kind="line",
        xlabel="phase B progress (0 = end of phase A, 1 = end of phase B)",
        ylabel="accuracy (panel A streams)",
        notes=[
            "A missing snapshot leaves a gap. Replay and the joint bound are beside the classes in the tables, not drawn as classes."
        ],
    )
    for arch, arm in (
        *analysis_d.CLASSED_ARMS,
        ("dense", "sequential"),
        ("flat", "replay"),
        ("dense", "replay"),
    ):
        cell = analysis_d.d_cell(arch, arm, core.INIT_SEEDS[0])
        d1 = analysis_d.d_cell(arch, "phaseA", core.INIT_SEEDS[0])
        if cell is None or d1 is None:
            continue
        u = core.updates(cell, inputs.exposure)
        for set_name in ("A", "B"):
            stream = analysis_d.lane_d_stream("A", set_name)

            def acc(label: str, update: int, stream: str = stream) -> float | None:
                rec = inputs.index.get((label, update, stream))
                return None if rec is None else rec["correct"] / rec["facts"]

            start = acc(d1.label, core.updates(d1, inputs.exposure)) if set_name == "A" else None
            fig.series.append(
                Series(
                    f"{arch}/{arm} on {set_name}",
                    [0.0, 0.5, 1.0],
                    [start, acc(cell.label, u // 2), acc(cell.label, u)],
                    "solid" if set_name == "A" else "dashed",
                )
            )
    return fig


def _logical_work_figure() -> FigureSpec:
    series = [
        Series(
            arch,
            [str(s) for s in core.SLOTS_BY_SIZE],
            [float(core.logical_key_products(arch, s)) for s in core.SLOTS_BY_SIZE],
        )
        for arch in ("flat", "learned_tree")
    ]
    return FigureSpec(
        key="logical_key_products",
        title="Logical key products per query (ADR 5.2)",
        question="How much key-comparison work does each architecture do per query by construction? This is logical work, not measured efficiency, and not a speedup.",
        label="LOGICAL",
        kind="bar",
        xlabel="memory slots",
        ylabel="key products per query",
        series=series,
    )


def figure_specs(inputs: ReportInputs | None = None) -> list[FigureSpec]:
    """All dashboard plots as data (the human draft, section 13). Every plot tolerates empty inputs: it is
    then a 'no data' plot, never a crash and never a zero."""
    inp = inputs or ReportInputs()
    flat = analysis_a.find_cell("A1", "flat", 16384, seed=core.INIT_SEEDS[0])
    tree = analysis_a.find_cell("A2", "learned_tree", 16384, seed=core.INIT_SEEDS[0])
    reg = analysis_a.find_cell(
        "C1",
        "flat",
        16384,
        alpha_u=core.ALPHA_C_WITH_ALPHA_U,
        alpha_c=0.25,
        seed=core.INIT_SEEDS[0],
    )
    usage = analysis_a.find_cell("B1", "flat", 16384, alpha_u=1.0, seed=core.INIT_SEEDS[0])
    figs = [
        _capacity_figure(inp, "matched"),
        _capacity_figure(inp, "fixed_compute"),
        _slot_use_figure(inp),
        _exposure_figure(inp),
        _entropy_figure(inp),
    ]
    for cell in (flat, tree):
        if cell is not None:
            figs.append(_heat_figure(inp, cell, "grad_norm_task"))
    figs.append(_locality_figure(inp))
    for cell in (usage, reg):
        if cell is not None:
            figs.append(_trace_figure(inp, cell))
    figs += [_retention_figure(inp), _logical_work_figure()]
    return figs


# --- SVG rendering (pure Python) ---------------------------------------------------------------------------------------
PALETTE = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
    "#332288",
    "#8C6D1F",
    "#AA4499",
    "#117733",
)
W, H, ML, MR, MT, MB = 720, 380, 70, 190, 34, 56


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def _scale(lo: float, hi: float, a: float, b: float, log: bool = False) -> Callable[[float], float]:
    if log:
        lo, hi = math.log10(lo), math.log10(hi)
    span = hi - lo or 1.0

    def f(v: float) -> float:
        x = math.log10(v) if log else v
        return a + (x - lo) / span * (b - a)

    return f


def _ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


def _fmt(v: float) -> str:
    return f"{v:.3g}"


def render_svg(fig: FigureSpec) -> str:
    """Self-contained SVG of a figure (no external assets). Missing or non-finite values are skipped and a
    figure without a finite value says so; heatmap cells without a value are hatched 'n/a'."""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{_esc(fig.title)}" font-family="sans-serif" font-size="11">'
    ]
    parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')
    parts.append(
        f'<text x="{ML}" y="18" font-size="12" font-weight="bold">{_esc(fig.title[:95])}</text>'
    )
    badge = _esc(fig.label)
    parts.append(
        f'<rect x="{W - MR + 10}" y="6" width="{MR - 20}" height="18" fill="#222"/><text x="{W - MR + 18}" y="19" fill="white" font-weight="bold">{badge}</text>'
    )
    plot_w, plot_h = W - ML - MR, H - MT - MB
    if fig.finite_points() == 0:
        parts.append(
            f'<rect x="{ML}" y="{MT}" width="{plot_w}" height="{plot_h}" fill="#f4f4f4" stroke="#999"/>'
        )
        parts.append(
            f'<text x="{ML + plot_w / 2}" y="{MT + plot_h / 2}" text-anchor="middle" fill="#555">no data: values are missing or undefined</text>'
        )
        parts.append("</svg>")
        return "".join(parts)
    if fig.kind == "heatmap":
        parts += _svg_heat(fig, plot_w, plot_h)
    else:
        parts += _svg_xy(fig, plot_w, plot_h)
    parts.append(
        f'<text x="{ML + plot_w / 2}" y="{H - 8}" text-anchor="middle">{_esc(fig.xlabel[:90])}</text>'
    )
    parts.append(
        f'<text x="14" y="{MT + plot_h / 2}" transform="rotate(-90 14 {MT + plot_h / 2})" text-anchor="middle">{_esc(fig.ylabel[:60])}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _svg_xy(fig: FigureSpec, plot_w: float, plot_h: float) -> list[str]:
    out: list[str] = []
    ys = [y for s in fig.series for y in s.y if y is not None and math.isfinite(y)]
    ylo, yhi = min(0.0, min(ys)), max(ys)
    yhi = yhi if yhi > ylo else ylo + 1.0
    categorical = any(isinstance(x, str) for s in fig.series for x in s.x)
    cats: list[str] = []
    for s in fig.series:
        for x in s.x:
            if isinstance(x, str) and x not in cats:
                cats.append(x)
    xnum = [
        float(x) for s in fig.series for x in s.x if isinstance(x, int | float) and math.isfinite(x)
    ]
    if not categorical and not xnum:
        xnum = [0.0, 1.0]
    xlo, xhi = (min(xnum), max(xnum)) if xnum else (0.0, 1.0)
    use_log = fig.xlog and xlo > 0
    xf = _scale(xlo, xhi if xhi > xlo else xlo + 1.0, ML + 10, ML + plot_w - 10, use_log)
    yf = _scale(ylo, yhi, MT + plot_h, MT, False)
    out.append(
        f'<rect x="{ML}" y="{MT}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#888"/>'
    )
    for t in _ticks(ylo, yhi):
        out.append(
            f'<line x1="{ML}" x2="{ML + plot_w}" y1="{yf(t):.1f}" y2="{yf(t):.1f}" stroke="#ddd"/><text x="{ML - 6}" y="{yf(t) + 4:.1f}" text-anchor="end">{_fmt(t)}</text>'
        )
    if categorical:
        step = plot_w / max(1, len(cats))
        for i, c in enumerate(cats):
            out.append(
                f'<text x="{ML + step * (i + 0.5):.1f}" y="{MT + plot_h + 14}" text-anchor="end" transform="rotate(-30 {ML + step * (i + 0.5):.1f} {MT + plot_h + 14})" font-size="8">{_esc(c[:22])}</text>'
            )
    else:
        for t in sorted(
            {x for s in fig.series for x in s.x if isinstance(x, int | float) and math.isfinite(x)}
        )[:8]:
            out.append(
                f'<text x="{xf(float(t)):.1f}" y="{MT + plot_h + 14}" text-anchor="middle">{_fmt(float(t))}</text>'
            )
    nser = max(1, len(fig.series))
    for si, s in enumerate(fig.series):
        color = PALETTE[si % len(PALETTE)]
        dash = ' stroke-dasharray="5 3"' if s.style == "dashed" else ""
        pts: list[tuple[float, float] | None] = []
        for i, (x, y) in enumerate(zip(s.x, s.y, strict=False)):
            if y is None or not math.isfinite(y) or x is None:
                pts.append(None)
                continue
            if isinstance(x, str):
                step = plot_w / max(1, len(cats))
                px = ML + step * (cats.index(x) + 0.5)
                if fig.kind == "bar":
                    bw = step / (nser + 1)
                    px = ML + step * cats.index(x) + bw * (si + 0.5)
            elif math.isfinite(x):
                px = xf(float(x))
            else:
                pts.append(None)
                continue
            pts.append((px, yf(y)))
        if fig.kind == "bar":
            step = plot_w / max(1, len(cats))
            bw = step / (nser + 1)
            for p in pts:
                if p is not None:
                    out.append(
                        f'<rect x="{p[0]:.1f}" y="{p[1]:.1f}" width="{bw:.1f}" height="{max(0.0, MT + plot_h - p[1]):.1f}" fill="{color}"/>'
                    )
        elif fig.kind == "line":
            run: list[tuple[float, float]] = []
            for p in [*pts, None]:
                if p is None:
                    if len(run) > 1:
                        out.append(
                            f'<polyline fill="none" stroke="{color}" stroke-width="1.5"{dash} points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in run)}"/>'
                        )
                    run = []
                else:
                    run.append(p)
            for p in pts:
                if p is not None:
                    out.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="2.5" fill="{color}"/>')
        else:
            for p in pts:
                if p is not None:
                    out.append(
                        f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="3" fill="{color}" fill-opacity="0.7"/>'
                    )
        ly = MT + 6 + 13 * si
        if si < 18:
            out.append(
                f'<rect x="{ML + plot_w + 8}" y="{ly - 8}" width="9" height="9" fill="{color}"/><text x="{ML + plot_w + 21}" y="{ly}">{_esc(s.name[:30])}</text>'
            )
    return out


def _svg_heat(fig: FigureSpec, plot_w: float, plot_h: float) -> list[str]:
    out: list[str] = []
    rows, cols = len(fig.row_labels), max((len(r) for r in fig.values), default=0)
    if not rows or not cols:
        return out
    cw, ch = plot_w / cols, plot_h / rows
    finite = [v for r in fig.values for v in r if v is not None and math.isfinite(v)]
    lo, hi = min(finite), max(finite)
    span = hi - lo or 1.0
    out.append(
        '<defs><pattern id="na" width="6" height="6" patternUnits="userSpaceOnUse"><path d="M0,6 L6,0" stroke="#999" stroke-width="1"/></pattern></defs>'
    )
    for i, row in enumerate(fig.values):
        for j in range(cols):
            v = row[j] if j < len(row) else None
            x, y = ML + j * cw, MT + i * ch
            if v is None or not math.isfinite(v):
                out.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="url(#na)" stroke="#ccc"/>'
                )
            else:
                t = (v - lo) / span
                shade = int(255 - 200 * t)
                out.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="rgb({shade},{shade},255)" stroke="#fff"><title>{_esc(fig.row_labels[i])} / {_esc(fig.col_labels[j] if j < len(fig.col_labels) else j)}: {_fmt(v)}</title></rect>'
                )
                if cw > 34 and ch > 12:
                    out.append(
                        f'<text x="{x + cw / 2:.1f}" y="{y + ch / 2 + 3:.1f}" text-anchor="middle" font-size="8">{_fmt(v)}</text>'
                    )
    for i, label in enumerate(fig.row_labels[:40]):
        out.append(
            f'<text x="{ML - 4}" y="{MT + i * ch + ch / 2 + 3:.1f}" text-anchor="end" font-size="8">{_esc(label[:40])}</text>'
        )
    for j, label in enumerate(fig.col_labels[:cols]):
        out.append(
            f'<text x="{ML + j * cw + cw / 2:.1f}" y="{MT + plot_h + 12}" text-anchor="middle" font-size="8">{_esc(label[:14])}</text>'
        )
    out.append(
        f'<text x="{ML + plot_w + 8}" y="{MT + 10}" font-size="9">scale {_fmt(lo)} to {_fmt(hi)}</text>'
    )
    return out


def render_png(fig: FigureSpec) -> bytes | None:
    """PNG of a figure with matplotlib, imported here and nowhere else; ``None`` when matplotlib is not
    installed. Missing values are skipped as in ``render_svg``."""
    try:
        matplotlib = importlib.import_module("matplotlib")
        matplotlib.use("Agg")
        plt = importlib.import_module("matplotlib.pyplot")
    except ImportError:
        return None
    figure, ax = plt.subplots(figsize=(9, 4.8), dpi=110)
    try:
        if fig.finite_points() == 0:
            ax.text(
                0.5,
                0.5,
                "no data: values are missing or undefined",
                ha="center",
                transform=ax.transAxes,
            )
        elif fig.kind == "heatmap":
            data = [[math.nan if v is None else v for v in row] for row in fig.values]
            image = ax.imshow(data, aspect="auto", cmap="Blues")
            ax.set_yticks(range(len(fig.row_labels)), fig.row_labels, fontsize=6)
            ax.set_xticks(range(len(fig.col_labels)), fig.col_labels, fontsize=6, rotation=45)
            figure.colorbar(image, ax=ax)
        else:
            cats = sorted({x for s in fig.series for x in s.x if isinstance(x, str)}, key=str)
            for s in fig.series:
                pairs = [
                    (cats.index(x) if isinstance(x, str) else x, y)
                    for x, y in zip(s.x, s.y, strict=False)
                    if x is not None
                ]
                xs = [p[0] for p in pairs]
                ys = [math.nan if p[1] is None else p[1] for p in pairs]
                if fig.kind == "bar":
                    ax.bar(
                        [float(a) + 0.2 * fig.series.index(s) for a in xs],
                        [0.0 if math.isnan(v) else v for v in ys],
                        width=0.2,
                        label=s.name,
                    )
                elif fig.kind == "line":
                    ax.plot(
                        xs,
                        ys,
                        marker="o",
                        linestyle="--" if s.style == "dashed" else "-",
                        label=s.name,
                    )
                else:
                    ax.scatter(xs, ys, label=s.name, alpha=0.7)
            if cats:
                ax.set_xticks(range(len(cats)), cats, rotation=30, fontsize=6)
            if fig.xlog:
                ax.set_xscale("log")
            ax.legend(fontsize=6)
        ax.set_title(f"{fig.title[:90]}  [{fig.label}]", fontsize=8)
        ax.set_xlabel(fig.xlabel, fontsize=8)
        ax.set_ylabel(fig.ylabel, fontsize=8)
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png")
        return buffer.getvalue()
    finally:
        plt.close(figure)


# --- dashboard -----------------------------------------------------------------------------------------------------------------
CSS = (
    "body{font-family:sans-serif;margin:24px;max-width:1100px}table{border-collapse:collapse;font-size:12px}td,th{border:1px solid #bbb;padding:3px 6px;text-align:left}"
    "figure{margin:18px 0;border:1px solid #ddd;padding:8px}figcaption{font-size:12px;margin-top:6px}.banner{background:#fff3cd;border:1px solid #d9b100;padding:8px}"
    ".tag{background:#222;color:#fff;padding:1px 6px;font-size:11px;margin-left:6px}"
)


def render_dashboard(
    results: Sequence[ClassResult],
    manifests: Sequence[StageManifest],
    status: str,
    inputs: ReportInputs | None = None,
    *,
    png: bool = False,
) -> str:
    """Self-contained static HTML dashboard (no network, no external assets): status banner, class table,
    decision map, manifests and the captioned plots. With ``png=True`` and matplotlib present the plots
    are embedded as PNG, otherwise as SVG."""
    table = results_table(results)
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>P9 dashboard (ADR-0017)</title>",
        f"<style>{CSS}</style></head><body>",
        "<h1>P9 diagnostics dashboard</h1>",
        f"<div class='banner'><b>Study status: {_esc(status)}.</b> {_esc(REVIEW_STATEMENT)}</div>",
        "<p>Labels: MEASURED (evaluation records), SIMULATED (value-page misses of a model, not physical I/O), LOGICAL / ANALYTICAL (arithmetic from the design; never measured efficiency or a speedup).</p>",
        "<h2>Classes</h2><table><tr><th>lane</th><th>subject</th><th>class</th><th>panel A</th><th>panel B</th><th>annotations</th><th>basis</th></tr>",
    ]
    for row in table:
        parts.append(
            f"<tr><td>{_esc(row['lane'])}</td><td>{_esc(row['subject'])}</td><td><b>{_esc(row['class'])}</b></td><td>{_esc(row['panel_A'])}</td><td>{_esc(row['panel_B'])}</td><td>{_esc(row['annotations'])}</td><td>{_esc(row['basis'])}</td></tr>"
        )
    parts.append("</table><h2>Decision map (ADR 8.7)</h2><ul>")
    parts += [f"<li>{_esc(d)}</li>" for d in decision_map(results, status)]
    parts.append(
        "</ul><h2>Stage manifests</h2><table><tr><th>stage</th><th>mode</th><th>status</th><th>tasks</th><th>not completed</th></tr>"
    )
    for m in manifests:
        bad = sum(1 for t in m["tasks"] if t["status"] != "completed")
        parts.append(
            f"<tr><td>{_esc(m['stage'])}</td><td>{_esc(m['mode'])}</td><td>{_esc(m['status'])}</td><td>{len(m['tasks'])}</td><td>{bad}</td></tr>"
        )
    if not manifests:
        parts.append("<tr><td colspan='5'>no manifests loaded</td></tr>")
    parts.append("</table><h2>Plots</h2>")
    for fig in figure_specs(inputs):
        image: str
        data = render_png(fig) if png else None
        image = (
            f"<img alt='{_esc(fig.title)}' src='data:image/png;base64,{base64.b64encode(data).decode()}'/>"
            if data
            else render_svg(fig)
        )
        notes = "".join(f"<br>{_esc(n)}" for n in fig.notes)
        parts.append(
            f"<figure>{image}<figcaption><b>{_esc(fig.title)}</b> <span class='tag'>{_esc(fig.label)}</span><br><b>Question answered:</b> {_esc(fig.question)}{notes}</figcaption></figure>"
        )
    parts.append(
        f"<h2>What must not be claimed (ADR 13)</h2><ul>{''.join(f'<li>{_esc(c)}</li>' for c in NOT_CLAIMED)}</ul></body></html>"
    )
    return "".join(parts)


# --- writing ---------------------------------------------------------------------------------------------------------------------
def write_report(
    run_dir: Path,
    results_dir: Path,
    results: Sequence[ClassResult],
    status: str,
    *,
    manifests: Sequence[StageManifest] = (),
    inputs: ReportInputs | None = None,
    png: bool = False,
    banner: str | None = None,
) -> list[Path]:
    """Write ``results.json``, ``results.csv``, ``RESULTS.md``, ``dashboard.html`` and ``hashes.json`` under
    ``results_dir`` (JSON through ``arborlm.io``, non-finite numbers written as '+inf', '-inf' or null);
    returns the paths. ``run_dir`` is recorded as the source of the records. ``banner`` (integration addition)
    is printed at the top of ``RESULTS.md`` and the dashboard and stored in ``results.json`` (DRY runs)."""
    results_dir.mkdir(parents=True, exist_ok=True)
    missing = missing_cells(manifests)
    decisions = decision_map(results, status)
    items = decision_items(results, status)
    paths: list[Path] = []
    payload = {
        "study": core.STUDY,
        "schema": core.SCHEMA,
        "status": status,
        "review": REVIEW_STATEMENT,
        "source_run_dir": str(run_dir),
        "missing_cells": missing,
        "unreadable_records": list(inputs.unreadable) if inputs is not None else [],
        "decision_map": decisions,
        "decision_items": analysis_a.jsonable(items),
        "results": analysis_a.jsonable(list(results)),
        "denominator": core.TOTAL_CELLS,
        "banner": banner,
    }
    markdown = render_markdown(results, status, decisions, manifests=manifests, missing=missing)
    dashboard = render_dashboard(results, manifests, status, inputs, png=png)
    if banner:  # integration addition: DRY outputs are marked in every file
        markdown = f"**{banner}**\n\n{markdown}"
        dashboard = dashboard.replace("<body>", f"<body><h2>{html.escape(banner)}</h2>", 1)
    writers: list[tuple[str, Callable[[Path], None]]] = [
        ("results.json", lambda p: write_json(p, payload)),
        ("results.csv", lambda p: write_csv(p, results_table(results))),
        ("RESULTS.md", lambda p: atomic_write(p, markdown.encode())),
        ("dashboard.html", lambda p: atomic_write(p, dashboard.encode())),
    ]
    for name, writer in writers:
        path = results_dir / name
        writer(path)
        paths.append(path)
    write_json(results_dir / "hashes.json", {p.name: file_sha256(p) for p in paths})
    paths.append(results_dir / "hashes.json")
    return paths


def load_inputs(run_dirs: Sequence[Path], exposure: int = core.DEFAULT_EXPOSURE) -> ReportInputs:
    """Read the records of one or more run directories (``cells/<label>/train.json``, ``updates.jsonl``,
    ``eval/*/*.json``, ``sim/*/*.json``). Unreadable, foreign or malformed files are skipped and listed in
    ``ReportInputs.unreadable``; they are never fatal and never deleted."""
    index: dict[EvalKey, EvalRecord] = {}
    train: dict[str, TrainRecord] = {}
    updates: dict[str, list[UpdateRecord]] = {}
    sims: dict[str, list[SimRecord]] = {}
    unreadable: list[str] = []
    for run in run_dirs:
        for cell_dir in sorted((run / "cells").glob("*")) if (run / "cells").is_dir() else []:
            label = cell_dir.name
            if (cell_dir / "train.json").is_file():
                try:
                    train[label] = core.read_record(cell_dir / "train.json", "train")  # type: ignore[assignment]
                except (OSError, ValueError):
                    unreadable.append(str(cell_dir / "train.json"))
            log = cell_dir / "updates.jsonl"
            if log.is_file():
                try:
                    updates[label] = [
                        json.loads(line) for line in log.read_text().splitlines() if line.strip()
                    ]
                except (OSError, ValueError):
                    unreadable.append(str(log))
            for path in sorted(cell_dir.glob("eval/*/*.json")):
                try:
                    rec = core.read_record(path, "eval")
                except (OSError, ValueError):
                    unreadable.append(str(path))
                    continue
                if not analysis_a.valid_eval(rec):
                    unreadable.append(str(path))
                    continue
                index[(rec["label"], int(rec["update"]), rec["stream"])] = rec  # type: ignore[assignment]
            for path in sorted(cell_dir.glob("sim/*/*.json")):
                try:
                    payload = read_json(path)
                    records = list(payload.get("records", []))
                except (OSError, ValueError, AttributeError, TypeError):
                    unreadable.append(str(path))
                    continue
                good = [r for r in records if isinstance(r, dict) and analysis_c.valid_sim(r)]
                if len(good) != len(records):
                    unreadable.append(f"{path} ({len(records) - len(good)} malformed record(s))")
                if good:
                    sims.setdefault(label, []).extend(cast(list[SimRecord], good))
    return ReportInputs(index, train, updates, sims, exposure, unreadable)


def run_analyses(
    inputs: ReportInputs,
    calibration: Mapping[str, Any] | None = None,
    controls: Mapping[str, Any] | None = None,
) -> list[ClassResult]:
    """Every lane's analysis on ``inputs`` (pure functions of the records)."""
    fail = analysis_a.ceiling_fail_sizes(calibration)
    leaky = analysis_a.leaky_labels(inputs.index)
    results = analysis_a.analyze(inputs.index, inputs.exposure, calibration, controls)
    results += analysis_b.analyze(inputs.index, inputs.exposure, ceiling_fail=fail, leaky=leaky)
    results += analysis_c.analyze(
        inputs.index, inputs.sims, inputs.exposure, ceiling_fail=fail, leaky=leaky
    )
    results += analysis_d.analyze(
        inputs.index, inputs.exposure, ceiling_fail=fail, leaky=leaky, controls=controls
    )
    return results


def _read_manifests(run_dirs: Sequence[Path]) -> list[StageManifest]:
    found: list[StageManifest] = []
    for run in run_dirs:
        for path in sorted({run / "manifest.json", *run.glob("*/manifest.json")}):
            if path.is_file():
                try:
                    found.append(core.read_record(path, "stage_manifest"))  # type: ignore[arg-type]
                except (OSError, ValueError):
                    continue
    return found


def main(argv: list[str] | None = None) -> int:
    """``python -m studies.p9.report --run-dir DIR [--run-dir DIR ...] --results-dir DIR [--exposure 32]
    [--calibration FILE] [--controls FILE] [--engineering-defect TEXT ...] [--png]``. Analysis only: it
    reads records, runs the lane analyses and writes the report; it trains and simulates nothing."""
    parser = argparse.ArgumentParser(prog="python -m studies.p9.report")
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument(
        "--exposure", type=int, default=core.DEFAULT_EXPOSURE, choices=core.EXPOSURE_MENU
    )
    parser.add_argument("--calibration", type=Path, default=None)
    parser.add_argument("--controls", type=Path, default=None)
    parser.add_argument("--engineering-defect", action="append", default=[])
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    inputs = load_inputs(args.run_dir, args.exposure)
    calibration = read_json(args.calibration) if args.calibration else None
    controls = read_json(args.controls) if args.controls else None
    results = run_analyses(inputs, calibration, controls)
    manifests = _read_manifests(args.run_dir)
    status = study_status(manifests, args.engineering_defect)
    paths = write_report(
        args.run_dir[0],
        args.results_dir,
        results,
        status,
        manifests=manifests,
        inputs=inputs,
        png=args.png,
    )
    print(json.dumps({"status": status, "written": [str(p) for p in paths]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
