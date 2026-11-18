# ruff: noqa: E501
"""P10IS5 analysis (ADR-0028 sections 5.3, 5.4, 5.5, 9): pure functions over records. It reads no file and touches no device.

Input (``analyse``): a registry mapping with ``passes`` (every pass record of E2, every attempt, each with a monotone ``seq``), ``blocks`` (block records with ``repeat``, ``role`` regular or spare, ``quiet_start``, ``quiet_end``,
``pass_keys``, ``complete``), ``harness`` (E2's harness figure by depth), ``r1`` (R1's record: its ``not_evaluable_reasons``), ``cold_checks``, ``manifest`` (``quiet_exhausted``, ``write_budget_declined``), ``stops`` (engineering-stop
records, each ``resolved`` True only when a complete spare block reruns it) and ``thresholds`` (from the config: ``m_t``, ``timing_spread``, the repeat counts, the harness fraction, the grid). It REFUSES (``AnalysisRefused``) while any
engineering stop is unresolved or any pass has a parity failure: that is an ENGINEERING STOP, never a label.

Valid repeat: the block was quiet at its start and its end and every pass met the counter rule (all 24 passes present). The first invalid regular block is replaced once by the spare, if the spare is itself valid; the denominator stays 5.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any

from . import core

NS_PER_US = 1000.0


class AnalysisRefused(RuntimeError):
    """The analysis REFUSES: an ENGINEERING STOP (cause) exists and nothing is labelled from the stage until it is fixed under a recorded amendment and the stage is run again."""


def cell_key(k: int, s: int) -> str:
    return f"k{k}|s{s}"


def pass_by_cell(passes: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for p in passes:
        out[cell_key(p["k"], p["s"])] = p
    return out


def block_valid(block: Mapping[str, Any], passes_by_key: Mapping[str, Mapping[str, Any]], cells: Sequence[tuple[int, int]]) -> tuple[bool, list[str]]:
    """(valid, reasons it is not): quiet at start and end, complete, all cells present, every pass's counter rule met."""
    why: list[str] = []
    if not block.get("complete"):
        why.append("block not complete")
    if not (block.get("quiet_start") or {}).get("ok"):
        why.append("not quiet at its start")
    if not (block.get("quiet_end") or {}).get("ok"):
        why.append("not quiet at its end")
    ps = [passes_by_key[k] for k in block.get("pass_keys", []) if k in passes_by_key]
    have = {cell_key(p["k"], p["s"]) for p in ps}
    missing = [cell_key(k, s) for k, s in cells if cell_key(k, s) not in have]
    if missing:
        why.append(f"{len(missing)} cells missing")
    bad = [p["key"] for p in ps if p["counter_status"] != "OK"]
    if bad:
        why.append(f"counter rule failed in {len(bad)} pass(es)")
    return not why, why


def select_valid(blocks: Sequence[Mapping[str, Any]], passes: Sequence[Mapping[str, Any]], cells: Sequence[tuple[int, int]]) -> dict[str, Any]:
    """The valid repeats: valid regular blocks, and the spare replacing the FIRST invalid regular block if the spare is valid. A second invalid block stays invalid. The spare is used once."""
    by_key = {p["key"]: p for p in passes}
    regular = sorted((b for b in blocks if b["role"] == "regular"), key=lambda b: b["repeat"])
    spares = [b for b in blocks if b["role"] == "spare"]
    verdicts = {b["key"]: block_valid(b, by_key, cells) for b in blocks}
    valid = [b for b in regular if verdicts[b["key"]][0]]
    invalid = [b for b in regular if not verdicts[b["key"]][0]]
    replaced: dict[str, Any] | None = None
    spare_used = None
    if invalid and spares:
        spare = sorted(spares, key=lambda b: (b["repeat"], b["key"]))[0]
        spare_used = spare
        if verdicts[spare["key"]][0]:
            valid = valid + [spare]
            replaced = invalid[0]
    return {
        "valid": valid, "invalid": [b for b in invalid if b is not replaced], "replaced_block": None if replaced is None else replaced["key"], "spare_block": None if spare_used is None else spare_used["key"],
        "verdicts": {k: {"valid": v[0], "why": v[1]} for k, v in verdicts.items()},
    }  # fmt: skip


def stats_of(latencies_ns: Sequence[float]) -> dict[str, float]:
    return {"median": core.median(latencies_ns), "p90": core.nearest_rank(latencies_ns, 0.90), "p99": core.nearest_rank(latencies_ns, 0.99), "max": float(max(latencies_ns))}


# --- EQ-A ------------------------------------------------------------------------------------------------------------------------------------------
def eq_a(passes: Sequence[Mapping[str, Any]], selection: Mapping[str, Any], blocks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """BYTES CONFIRMED EXACTLY only if every pass of every repeat attempted (spare and any rerun included, valid block or not) has counter bytes equal to predicted bytes. Otherwise BYTES NOT CONFIRMED with the reason of
    the first failing pass and every failing pass printed beside the same cell's pass in the replacing block, if any. There is one rule and no '4 of 5'."""
    ordered = sorted(passes, key=lambda p: p["seq"])
    failing = [p for p in ordered if p["counter_bytes"] != p["predicted_bytes"] or p.get("written_bytes", 0) != 0]
    if not failing:
        return {"label": core.EQ_A_OK, "passes": len(ordered), "failing": [], "reason": None}
    spare = next((b for b in blocks if b["key"] == selection.get("spare_block")), None)
    replaced = selection.get("replaced_block")
    by_key = {p["key"]: p for p in passes}
    rows = []
    for p in failing:
        beside = None
        if spare is not None and replaced is not None and p.get("block") == replaced:
            for k in spare.get("pass_keys", []):
                q = by_key.get(k)
                if q is not None and (q["k"], q["s"]) == (p["k"], p["s"]):
                    beside = {"key": q["key"], "counter_bytes": q["counter_bytes"], "predicted_bytes": q["predicted_bytes"], "counter_status": q["counter_status"]}
        rows.append({"key": p["key"], "counter_bytes": p["counter_bytes"], "predicted_bytes": p["predicted_bytes"], "counter_status": p["counter_status"], "replacing_block_pass": beside})
    first = failing[0]
    reason = f"{first['key']}: {first['counter_status']} (counter {first['counter_bytes']} B, predicted {first['predicted_bytes']} B)"
    return {"label": f"{core.EQ_A_NOT} ({reason})", "passes": len(ordered), "failing": rows, "reason": reason}


# --- EQ-B and EQ-D ---------------------------------------------------------------------------------------------------------------------------------
def cell_latencies(valid_blocks: Sequence[Mapping[str, Any]], passes_by_key: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[int, Mapping[str, Any]]]:
    """cell -> {block order index (1..): the pass} over the valid blocks; the order index is the position among valid blocks (the report names the block key)."""
    out: dict[str, dict[int, Mapping[str, Any]]] = {}
    for bi, b in enumerate(valid_blocks, start=1):
        for k in b["pass_keys"]:
            p = passes_by_key[k]
            out.setdefault(cell_key(p["k"], p["s"]), {})[bi] = p
    return out


def eq_b(per_cell: Mapping[str, Mapping[int, Mapping[str, Any]]], n_valid_blocks: int, m_t: float, label_min: int, sizes: Sequence[int]) -> dict[str, Any]:
    """c_r(s): the median latency of the requests of size s at depth 1 in repeat r. Registered as measured: c_r(1) with p90, p99, maximum per repeat and pooled; rho_r(s) = c_r(s) / (s c_r(1)) for s = 3, 8, 64. The
    label is on rho_r(3): at least ``label_min`` of 5 repeats (the denominator stays 5; an invalid repeat is none of the three)."""
    c1 = per_cell.get(cell_key(1, 1), {})
    per_repeat: dict[int, dict[str, Any]] = {}
    for r, p in c1.items():
        per_repeat[r] = {"c1": stats_of(p["latency_ns"]), "rho": {}}
    for s in sizes:
        if s == 1:
            continue
        for r, p in per_cell.get(cell_key(1, s), {}).items():
            if r in per_repeat:
                per_repeat[r]["rho"][s] = core.median(p["latency_ns"]) / (s * per_repeat[r]["c1"]["median"])
    pooled_lat = [x for p in c1.values() for x in p["latency_ns"]]
    pooled = stats_of(pooled_lat) if pooled_lat else None
    rho3 = {r: v["rho"].get(3) for r, v in per_repeat.items() if v["rho"].get(3) is not None}
    cheaper = sum(1 for x in rho3.values() if x <= 1 - m_t)
    dearer = sum(1 for x in rho3.values() if x >= 1 + m_t)
    prop = sum(1 for x in rho3.values() if abs(x - 1) < m_t)
    if cheaper >= label_min:
        label = core.EQ_B_CHEAPER
    elif dearer >= label_min:
        label = core.EQ_B_DEARER
    elif prop >= label_min:
        label = core.EQ_B_PROPORTIONAL
    else:
        label = core.EQ_B_NOT_SEPARATED
    return {"label": label, "m_t": m_t, "counts": {"cheaper": cheaper, "dearer": dearer, "proportional": prop, "of": n_valid_blocks, "denominator": 5}, "per_repeat": per_repeat, "pooled_c1": pooled}


def eq_d(per_cell: Mapping[str, Mapping[int, Mapping[str, Any]]], grid: Sequence[tuple[int, int]], harness: Mapping[int, Mapping[str, Any]], fraction: float) -> dict[str, Any]:
    """The measured table of the 24 cells over the valid repeats: per cell and repeat the median, p90, p99, maximum request latency and pages per second; across repeats the median of the per-repeat medians, their range
    and their coefficient of variation; the pooled median (all requests of the cell over its valid repeats). HARNESS-LIMITED when E2's h(k) is above a quarter of the cell's pooled median. Descriptive: no ordering is registered."""
    rows: dict[str, dict[str, Any]] = {}
    for k, s in grid:
        cells = per_cell.get(cell_key(k, s), {})
        per_repeat = {r: {**stats_of(p["latency_ns"]), "pages_per_second": p["pages_per_second"]} for r, p in cells.items()}
        meds = [v["median"] for v in per_repeat.values()]
        pooled = [x for p in cells.values() for x in p["latency_ns"]]
        pooled_median = core.median(pooled) if pooled else None
        h = harness.get(k) or {}
        h_ns = h.get("median_ns") if h.get("status") == "MEASURED" else None
        tag = None
        if h_ns is None:
            tag = core.HARNESS_NOT_MEASURED
        elif pooled_median is not None and h_ns > fraction * pooled_median:
            tag = core.HARNESS_LIMITED
        rows[cell_key(k, s)] = {
            "k": k, "s": s, "per_repeat": per_repeat, "median_of_medians": core.median(meds) if meds else None, "range": [min(meds), max(meds)] if meds else None, "cv": core.cv(meds), "pooled_median": pooled_median,
            "pages_per_second_median": core.median([v["pages_per_second"] for v in per_repeat.values()]) if per_repeat else None, "harness_ns": h_ns, "tag": tag, "limited": tag == core.HARNESS_LIMITED,
        }  # fmt: skip
    return {"label": core.EQ_D_OK, "rows": rows}


def arithmetic_table(eq_d_rows: Mapping[str, Mapping[str, Any]], depths: Sequence[int]) -> list[dict[str, Any]]:
    """Section 5.5, ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH. With L(k, s) the pooled median request latency of EQ-D's cell, for each depth k: as two 3-page requests ceil(2 / min(k, 2)) x L(min(k, 2), 3); as
    six 1-page requests ceil(6 / k') x L(k', 1), k' the largest grid depth not above min(k, 6)."""

    def L(k: int, s: int) -> float | None:
        row = eq_d_rows.get(cell_key(k, s))
        return None if row is None else row["pooled_median"]

    out = []
    for k in depths:
        k2 = min(k, 2)
        k1 = max(d for d in depths if d <= min(k, 6))
        a, b = L(k2, 3), L(k1, 1)
        out.append({
            "k": k, "two_3page_depth_used": k2, "two_3page_rounds": math.ceil(2 / k2), "two_3page_ns": None if a is None else math.ceil(2 / k2) * a,
            "six_1page_depth_used": k1, "six_1page_rounds": math.ceil(6 / k1), "six_1page_ns": None if b is None else math.ceil(6 / k1) * b,
        })  # fmt: skip
    return out


# --- NOT EVALUABLE reasons -------------------------------------------------------------------------------------------------------------------------
def ordered_reasons(found: Sequence[str]) -> list[str]:
    return [r for r in core.REASONS_ORDER if r in found]


def not_evaluable(line: str, reasons: Sequence[str]) -> dict[str, Any]:
    ordered = ordered_reasons(reasons)
    return {"label": f"{core.ENG_NOT_EVALUABLE} ({ordered[0]})", "reasons": ordered, "line": line}


def analyse(reg: Mapping[str, Any]) -> dict[str, Any]:
    """The engineering part's three lines and the scientific line's registered label, each its own entry (they are never combined). REFUSES while an engineering stop is unresolved or a parity failure exists."""
    th = reg["thresholds"]
    passes = list(reg["passes"])
    stops = [s for s in reg.get("stops", []) if not s.get("resolved")]
    if stops:
        raise AnalysisRefused(f"ENGINEERING STOP ({stops[0].get('cause')}) is unresolved: nothing is labelled from this stage until the cause is fixed under a recorded amendment and the stage is run again")
    covered = {s.get("key") for s in reg.get("stops", []) if s.get("resolved")}  # a stop resolved by a complete rerun on the spare covers the passes of its block (they stay in EQ-A)
    bad = [p["key"] for p in passes if p.get("parity_ok") is False and p.get("block") not in covered]
    if bad:
        raise AnalysisRefused(f"ENGINEERING STOP (DATA MISMATCH): the page hashes of {bad[0]} differ from the prediction")
    if any(p.get("memory_guard_exceeded") and p.get("block") not in covered for p in passes):
        raise AnalysisRefused("ENGINEERING STOP (MEMORY GUARD): a pass passed the 4 GiB footprint guard")
    cells = [(int(k), int(s)) for k, s in th["grid"]]
    sizes = [int(s) for s in th["sizes"]]
    depths = [int(k) for k in th["depths"]]
    selection = select_valid(reg["blocks"], passes, cells)
    by_key = {p["key"]: p for p in passes}
    per_cell = cell_latencies(selection["valid"], by_key)
    n_valid = len(selection["valid"])
    general = list((reg.get("r1") or {}).get("not_evaluable_reasons", []))
    if any("STORE CANNOT BE HELD COLD" in str(c.get("outcome", "")) for c in reg.get("cold_checks", [])):
        general.append("STORE CANNOT BE HELD COLD")
    manifest = reg.get("manifest") or {}
    if manifest.get("write_budget_declined"):
        general.append("WRITE BUDGET EXHAUSTED")
    general = [r for r in general if r in core.GENERAL_REASONS]
    timing = ["MACHINE NOT QUIET"] if manifest.get("quiet_exhausted") else []
    few = ["FEWER THAN FOUR VALID REPEATS"] if n_valid < int(th["valid_min_repeats"]) else []

    a_lines = eq_a(passes, selection, reg["blocks"])
    out: dict[str, Any] = {"valid_repeats": [b["key"] for b in selection["valid"]], "n_valid": n_valid, "selection": selection}
    if general:
        out["EQ-A"] = {**a_lines, **not_evaluable("EQ-A", general)}
        out["EQ-A"]["figures"] = a_lines
    else:
        out["EQ-A"] = a_lines
    m_t = float(th["m_t"])
    b_fig = eq_b(per_cell, n_valid, m_t, int(th["label_min_repeats"]), sizes) if n_valid else None
    b_reasons = general + (["TIMING SPREAD"] if th.get("timing_spread") else []) + timing + few
    if b_reasons:
        out["EQ-B"] = {**not_evaluable("EQ-B", b_reasons), "figures_descriptive": b_fig}
    else:
        assert b_fig is not None
        out["EQ-B"] = b_fig
    d_fig = eq_d(per_cell, cells, reg.get("harness") or {}, float(th["harness_limited_fraction"])) if n_valid else None
    d_reasons = general + timing + few
    if d_reasons:
        out["EQ-D"] = {**not_evaluable("EQ-D", d_reasons), "figures_descriptive": d_fig}
    else:
        assert d_fig is not None
        out["EQ-D"] = d_fig
        out["arithmetic"] = arithmetic_table(d_fig["rows"], depths)
    out["scientific"] = {"label": core.SCI_LABEL, "reasons": list(core.SCI_REASONS)}
    return out
