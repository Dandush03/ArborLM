# ruff: noqa: E501
"""P10IS5 report (ADR-0028 sections 1, 5.5, 14): a pure function of the analysis result and a small context. Two verdicts, never combined: the engineering lines and the scientific line are separate sections,
no sentence joins them and neither section cites the other's label. Nothing here reads as a result about ArborLM's memory, accuracy or the trained tree. Every number is labelled measured (a counter or a clock
through this harness) or analytical (arithmetic on the measured table). Self-check output: not independent review, not Astra validation, not human approval.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from . import core
from .analysis import NS_PER_US, cell_key

NOT_APPROVED = "Astra review: NOT_PERFORMED. Claude review is not Astra review. No registered run is approved by this text; no label here is a success claim for the project."
LIMITS = (
    "It can say, for one Apple SSD behind APFS with FileVault, with uncached whole-page requests issued from CPython threads on a synthetic file of 4 GiB that fits in RAM and is only made to behave as if it did not: "
    "whether the host-side counter equals the layout's arithmetic; what one page costs at depth 1; whether a page costs less inside a contiguous request; how request latency and pages per second change over six depths "
    "and four request sizes, as seen by the host through this harness.",
    "It says nothing about: any memory, key, query or index (none is in the file); whether a tree or an index is better; the cost of routing or of any computation in RAM; whether storage is needed (the file fits in RAM); "
    "warm or hot-page caching; other drives, filesystems or operating systems; an asynchronous or native I/O path; the drive's internal queue; NAND traffic, wear, endurance, sustained writes or updates.",
)  # fmt: skip


def us(ns: float | None) -> str:
    return "n/a" if ns is None else f"{ns / NS_PER_US:,.1f}"


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _eq_a(a: Mapping[str, Any]) -> list[str]:
    lines = [f"EQ-A (measured counter against predicted bytes): **{a['label']}**"]
    fig = a.get("figures", a)
    lines.append(f"- passes counted: {fig['passes']} (every pass with both counter snapshots, every attempt)")
    for f in fig["failing"]:
        beside = f["replacing_block_pass"]
        lines.append(f"- failing pass {f['key']}: counter {f['counter_bytes']} B, predicted {f['predicted_bytes']} B, {f['counter_status']}" + (f"; same cell in the replacing block {beside['key']}: counter {beside['counter_bytes']} B, predicted {beside['predicted_bytes']} B, {beside['counter_status']}" if beside else ""))
    if "reasons" in a:
        lines.append("- NOT EVALUABLE reasons found (in the order of the ADR): " + "; ".join(a["reasons"]))
    return lines


def _eq_b(b: Mapping[str, Any]) -> list[str]:
    lines = [f"EQ-B (cost of one page, and of a page inside a contiguous request; latencies measured, ratios analytical on measured medians): **{b['label']}**"]
    fig = b.get("figures_descriptive", b) if "reasons" in b else b
    if "reasons" in b:
        lines.append("- NOT EVALUABLE reasons found (in the order of the ADR): " + "; ".join(b["reasons"]) + ". Figures below are descriptive.")
    if fig is None:
        return lines
    if "counts" in fig:
        c = fig["counts"]
        lines.append(f"- margin m_t = {fig['m_t']:.3f} (fixed from R1 and M before the candidate plan); repeats on rho(3): cheaper {c['cheaper']}, dearer {c['dearer']}, proportional {c['proportional']} of 5 (valid repeats {c['of']})")
    lines.append("| repeat | c(1) median us | p90 us | p99 us | max us | rho(3) | rho(8) | rho(64) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r, v in sorted(fig["per_repeat"].items()):
        rho = v["rho"]
        lines.append(f"| {r} | {us(v['c1']['median'])} | {us(v['c1']['p90'])} | {us(v['c1']['p99'])} | {us(v['c1']['max'])} | " + " | ".join("n/a" if rho.get(s) is None else f"{rho[s]:.3f}" for s in (3, 8, 64)) + " |")
    p = fig.get("pooled_c1")
    if p:
        lines.append(f"| pooled | {us(p['median'])} | {us(p['p90'])} | {us(p['p99'])} | {us(p['max'])} | | | |")
    return lines


def _eq_d(d: Mapping[str, Any], grid: Sequence[tuple[int, int]]) -> list[str]:
    lines = [f"EQ-D (descriptive cost table, measured; no ordering, speed-up or monotonicity is registered): **{d['label']}**"]
    fig = d.get("figures_descriptive") if "reasons" in d else d
    if "reasons" in d:
        lines.append("- NOT EVALUABLE reasons found (in the order of the ADR): " + "; ".join(d["reasons"]) + ". Figures below are descriptive.")
    if fig is None:
        return lines
    lines.append("| depth k | pages s | pooled median us | median of medians us | range us | CV | pages/s (median) | harness h(k) us | tag |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for k, s in grid:
        row = fig["rows"][cell_key(k, s)]
        rng = "n/a" if row["range"] is None else f"{us(row['range'][0])} to {us(row['range'][1])}"
        pps = "n/a" if row["pages_per_second_median"] is None else f"{row['pages_per_second_median']:,.0f}"
        lines.append(f"| {k} | {s} | {us(row['pooled_median'])} | {us(row['median_of_medians'])} | {rng} | {pct(row['cv'])} | {pps} | {us(row['harness_ns'])} | {row['tag'] or ''} |")
    return lines


def _arithmetic(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = [
        f"### {core.ARITHMETIC_HEADING}", "",
        f"{core.ARITHMETIC_HEADING}. What the page reads of one T-OQ-shaped query (2 branches x 3 pages) would cost under the measured table (analytical: arithmetic on the pooled medians of EQ-D). "
        "It excludes the routing computation in RAM, assumes the pages are not cached and assumes rounds add. No query is issued, no branch exists in the file, and nothing in these lines is a measurement of any memory.", "",
        f"{core.ARITHMETIC_HEADING}",
        "| depth k | as two 3-page requests: rounds x L(depth used, 3) us | as six 1-page requests: rounds x L(depth used, 1) us |", "|---|---|---|",
    ]  # fmt: skip
    for r in rows:
        lines.append(f"| {r['k']} | {r['two_3page_rounds']} x L({r['two_3page_depth_used']}, 3) = {us(r['two_3page_ns'])} | {r['six_1page_rounds']} x L({r['six_1page_depth_used']}, 1) = {us(r['six_1page_ns'])} |")
    return lines


def render_report(result: Mapping[str, Any], context: Mapping[str, Any], grid: Sequence[tuple[int, int]]) -> str:
    """The report text. ``context`` carries printed facts: ``device`` (EC3 values), ``write_ledger_bytes``, ``hours``, ``harness`` (E2's h(k)), ``tags``."""
    out: list[str] = ["# P10-I-S5 engineering report (ADR-0028, engineering part)", "", NOT_APPROVED, ""]
    out += ["## ENGINEERING SSD PERFORMANCE", "", "Each line below is read alone. Every latency, byte count and rate is measured through this harness on this device; ratios and the arithmetic table are analytical.", ""]
    out += _eq_a(result["EQ-A"]) + [""] + _eq_b(result["EQ-B"]) + [""] + _eq_d(result["EQ-D"], grid) + [""]
    out.append(f"valid repeats: {result['n_valid']} of 5 ({', '.join(result['valid_repeats']) or 'none'})")
    sel = result["selection"]
    if sel.get("replaced_block"):
        out.append(f"the block {sel['replaced_block']} was invalid and was replaced once by the spare {sel['spare_block']}")
    out.append("")
    if "arithmetic" in result:
        out += _arithmetic(result["arithmetic"]) + [""]
    out += ["### Device record (EC3)", ""]
    dev = context.get("device") or {}
    out.append(f"- SMART status: {dev.get('smart_status', core.NOT_READABLE)}; free space: {dev.get('free_bytes', core.NOT_READABLE)}; disk0 driver bytes written since boot: {dev.get('driver_write_bytes', core.NOT_READABLE)}")
    out.append(f"- lifetime bytes written: {core.NOT_READABLE}; percentage used: {core.NOT_READABLE}; temperature: {core.NOT_READABLE} (they cannot be read without administrator access or a tool install; wear is accounted in the study's own bytes written)")
    out.append(f"- the study's own bytes written (measured, from the write ledger): {context.get('write_ledger_bytes', core.NOT_READABLE)}; charged hours (measured): {context.get('hours', core.NOT_READABLE)}")
    out += ["", "### What the engineering result can and cannot say", ""]
    out += [f"- {x}" for x in LIMITS]
    out += ["", "## SCIENTIFIC NEURAL-MEMORY ADVANTAGE", "", f"**{result['scientific']['label']}**", ""]
    out += [f"{i}. {r}" for i, r in enumerate(result["scientific"]["reasons"], start=1)]
    out += ["", "The scientific part is not approved and was not evaluated.", ""]
    return "\n".join(out)
