"""P7-A analysis (ADR-0013 section 7): non-degeneracy, ADV, LRU_K, CONC_K, BR_K, the outcome table,
the robustness grid, the registered decomposition and the descriptive tables.

All criterion arithmetic is exact (``fractions.Fraction``): the warm capacity miss counts are
integers, so thresholds (0.80, 0.05, 0.01) are compared without rounding and exact equality is
detected. Ratios are between means, never per pair; a tie counts as not lower. A missing,
unfinished or failed checkpoint makes every criterion INCOMPLETE (the missing labels are listed);
nothing here raises on missing data.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

from fractions import Fraction
from typing import Any

from . import p7a_core as core
from .p5_config import FLAT
from .p6_common import Pair

Values = dict[Pair, Fraction]

HOLDS, FAILS, DEGENERATE, INCOMPLETE = "HOLDS", "FAILS", "DEGENERATE", "INCOMPLETE"
UNRESOLVED = "UNRESOLVED"
NO_ADVANTAGE = "NO ADVANTAGE"
CONC_ONLY = "CONCENTRATION-ONLY"
STRUCTURAL = "STRUCTURAL ADVANTAGE"
UNSPECIFIED = "UNSPECIFIED"


def parents(pair_list: list[Pair]) -> dict[tuple[int, int], list[Pair]]:
    out: dict[tuple[int, int], list[Pair]] = {}
    for pair in pair_list:
        out.setdefault(core.parent_of(pair), []).append(pair)
    return out


def mean(values: list[Fraction]) -> Fraction:
    return sum(values, Fraction(0)) / len(values)


def frac_str(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


# --- criterion arithmetic (pure functions of per-cell values) -------------------------------------
def nondegenerate(flat: Values, tree: Values) -> dict[str, Any]:
    """NON-DEGENERATE when the mean of m over the flat cells is at least 0.05 and over the tree
    cells at least 0.01 (per query)."""
    flat_mean, tree_mean = mean(list(flat.values())), mean(list(tree.values()))
    flat_ok, tree_ok = flat_mean >= core.FLAT_FLOOR, tree_mean >= core.TREE_FLOOR
    return {
        "flat_mean": float(flat_mean),
        "tree_mean": float(tree_mean),
        "flat_mean_exact": frac_str(flat_mean),
        "tree_mean_exact": frac_str(tree_mean),
        "flat_floor_met": flat_ok,
        "tree_floor_met": tree_ok,
        "non_degenerate": flat_ok and tree_ok,
    }


def adv_clauses(
    reference: Values,
    candidate: Values,
    *,
    min_cells: int = core.MIN_CELLS,
    min_parents: int = core.MIN_PARENTS,
) -> dict[str, Any]:
    """The three ADV clauses, each reported separately.

    ``candidate`` is the tree (or L-ID) value and ``reference`` the flat (or L-RAND) value, per
    pair. Clause 1: mean(candidate) <= 0.80 * mean(reference) (equality passes; with a zero
    reference mean it passes only if the candidate mean is also zero). Clause 2: candidate strictly
    lower than reference in at least ``min_cells`` pairs. Clause 3: candidate's parent mean strictly
    lower in at least ``min_parents`` parents. A tie is not lower.
    """
    pair_list = list(reference)
    ref_mean, cand_mean = mean(list(reference.values())), mean(list(candidate.values()))
    clause_mean = cand_mean <= core.RATIO_LIMIT * ref_mean
    lower_cells = sum(1 for p in pair_list if candidate[p] < reference[p])
    groups = parents(pair_list)
    lower_parents = sum(
        1
        for members in groups.values()
        if mean([candidate[p] for p in members]) < mean([reference[p] for p in members])
    )
    clause_cells = lower_cells >= min_cells
    clause_parents = lower_parents >= min_parents
    return {
        "reference_mean": float(ref_mean),
        "candidate_mean": float(cand_mean),
        "reference_mean_exact": frac_str(ref_mean),
        "candidate_mean_exact": frac_str(cand_mean),
        "ratio_of_means": float(cand_mean / ref_mean) if ref_mean else None,
        "ratio_limit": float(core.RATIO_LIMIT),
        "clause_mean_ratio": clause_mean,
        "cells_strictly_lower": lower_cells,
        "cells_required": min_cells,
        "cells_total": len(pair_list),
        "clause_cells": clause_cells,
        "cells_tied": sum(1 for p in pair_list if candidate[p] == reference[p]),
        "parents_strictly_lower": lower_parents,
        "parents_required": min_parents,
        "parents_total": len(groups),
        "clause_parents": clause_parents,
        "holds": clause_mean and clause_cells and clause_parents,
    }


def outcome_for(lru: str, conc: str, robust: bool | None = None) -> str:
    """The section 7 outcome table plus ADR-0013 section 14 item 9: LRU holds with CONC DEGENERATE
    (the frequency-matched flat mean is below its floor, so the concentration control cannot be
    evaluated) is **UNSPECIFIED**, never a STRUCTURAL ADVANTAGE. That state is reachable only
    through ``evaluate_setting``'s frequency-matched floor check."""
    if lru == INCOMPLETE:
        return INCOMPLETE
    if lru == DEGENERATE:
        return UNRESOLVED
    if lru == FAILS:
        return NO_ADVANTAGE
    if conc == HOLDS:
        return CONC_ONLY
    if conc == FAILS:
        return STRUCTURAL + ("" if robust is None else (", robust" if robust else ", not robust"))
    return UNSPECIFIED


# --- reading per-checkpoint simulation records ----------------------------------------------------
def layout_names(layout: str) -> list[str]:
    return list(core.LAYOUTS_RAND) if layout == "L-RAND" else [layout]


def stream_names(stream: str) -> list[str]:
    return list(core.STREAMS_FM) if stream == "freq_matched" else [stream]


def capacity_misses(rec: dict[str, Any], stream: str, layout: str, rows: int, cap: int) -> Fraction:
    """m: warm capacity misses per query for one checkpoint (L-RAND and frequency-matched are
    averaged over their three layouts / replicates)."""
    queries = rec["queries"]
    counted = queries - queries // 2
    parts = []
    for s in stream_names(stream):
        for name in layout_names(layout):
            entry = rec["record"]["streams"][s][f"{name}|R{rows}"]["by_c"][str(cap)]
            parts.append(Fraction(entry["misses_warm"] - entry["first_touch_warm"], counted))
    return mean(parts)


def distinct_pages(rec: dict[str, Any], stream: str, layout: str, rows: int) -> Fraction:
    parts = []
    for s in stream_names(stream):
        for name in layout_names(layout):
            stats = rec["record"]["streams"][s][f"{name}|R{rows}"]["stats"]
            parts.append(Fraction(stats["pages_sum"], rec["queries"]))
    return mean(parts)


class Study:
    """The records of a study run, indexed by checkpoint, with the missing ones listed."""

    def __init__(
        self,
        records: dict[str, dict[str, Any]],
        expected: list[tuple[Pair, str]] | None = None,
    ) -> None:
        self.expected = expected if expected is not None else core.registered_checkpoints()
        self.records = records
        self.missing = [
            core.cell_label(p, k)
            for p, k in self.expected
            if core.cell_label(p, k) not in records
            or not records[core.cell_label(p, k)].get("record", {}).get("complete")
        ]
        self.pairs = sorted({p for p, _ in self.expected})
        self.complete = not self.missing and len(self.pairs) == 27

    def rec(self, pair: Pair, kind: str) -> dict[str, Any] | None:
        return self.records.get(core.cell_label(pair, kind))

    def values(self, kind: str, stream: str, layout: str, rows: int, cap: int) -> Values | None:
        out: Values = {}
        for pair in self.pairs:
            rec = self.rec(pair, kind)
            if rec is None or not rec.get("record", {}).get("complete"):
                return None
            out[pair] = capacity_misses(rec, stream, layout, rows, cap)
        return out

    def pages(self, kind: str, stream: str, layout: str, rows: int) -> Values | None:
        out: Values = {}
        for pair in self.pairs:
            rec = self.rec(pair, kind)
            if rec is None or not rec.get("record", {}).get("complete"):
                return None
            out[pair] = distinct_pages(rec, stream, layout, rows)
        return out


# --- settings and criteria ------------------------------------------------------------------------
def evaluate_setting(
    study: Study, tree_kind: str, rows: int, cap: int, layout: str = core.LAYOUT_FREQ
) -> dict[str, Any]:
    """Non-degeneracy (judged on the actual stream of the setting), LRU_K, CONC_K and BR_K parts
    for one (R, C). Every clause is reported separately."""
    flat = study.values(FLAT, core.STREAM_ACTUAL, layout, rows, cap)
    tree = study.values(tree_kind, core.STREAM_ACTUAL, layout, rows, cap)
    if flat is None or tree is None:
        return {
            "R": rows,
            "C": cap,
            "layout": layout,
            "status": INCOMPLETE,
            "LRU": INCOMPLETE,
            "CONC": INCOMPLETE,
        }
    nd = nondegenerate(flat, tree)
    result: dict[str, Any] = {
        "R": rows,
        "C": cap,
        "layout": layout,
        "cached_rows": rows * cap,
        "non_degeneracy": nd,
        "status": "NON-DEGENERATE" if nd["non_degenerate"] else DEGENERATE,
    }
    lru = adv_clauses(flat, tree)
    result["LRU_clauses"] = lru
    fm_flat = study.values(FLAT, "freq_matched", layout, rows, cap)
    fm_tree = study.values(tree_kind, "freq_matched", layout, rows, cap)
    assert fm_flat is not None and fm_tree is not None
    conc = adv_clauses(fm_flat, fm_tree)
    result["CONC_clauses"] = conc
    # Item 9: CONC_K has its own non-degeneracy check on the frequency-matched stream. Only the
    # flat floor makes CONC DEGENERATE (outcome UNSPECIFIED when LRU holds). A tree mean below its
    # floor with flat at or above its own leaves the mean clause to be evaluated as written.
    fm_nd = nondegenerate(fm_flat, fm_tree)
    result["CONC_non_degeneracy"] = {
        **fm_nd,
        "stream": "frequency-matched (mean of the three replicates per checkpoint)",
        "rule": "CONC is DEGENERATE (outcome UNSPECIFIED when LRU holds) only if the flat "
        "mean is below 0.05; a tree mean below 0.01 with flat at or above 0.05 is evaluated "
        "as written",
    }
    result["CONC_stream_means"] = {
        "flat": fm_nd["flat_mean"],
        "tree": fm_nd["tree_mean"],
        "note": "frequency-matched stream means; the setting's non-degeneracy status is judged "
        "on the actual stream and CONC has the extra flat-floor check above",
    }
    if not nd["non_degenerate"]:
        result["LRU"] = DEGENERATE
        result["CONC"] = DEGENERATE
    else:
        result["LRU"] = HOLDS if lru["holds"] else FAILS
        if not fm_nd["flat_floor_met"]:
            result["CONC"] = DEGENERATE
        else:
            result["CONC"] = HOLDS if conc["holds"] else FAILS
    return result


def branch_placement(study: Study, tree_kind: str, rows: int, cap: int) -> dict[str, Any]:
    """BR_K: the tree kind's own actual traces under L-ID against L-RAND."""
    rand = study.values(tree_kind, core.STREAM_ACTUAL, "L-RAND", rows, cap)
    ident = study.values(tree_kind, core.STREAM_ACTUAL, core.LAYOUT_ID, rows, cap)
    if rand is None or ident is None:
        return {"R": rows, "C": cap, "BR": INCOMPLETE}
    rand_mean = mean(list(rand.values()))
    non_degenerate = rand_mean >= core.TREE_FLOOR
    clauses = adv_clauses(rand, ident)
    return {
        "R": rows,
        "C": cap,
        "L_RAND_tree_mean": float(rand_mean),
        "L_RAND_tree_floor_met": non_degenerate,
        "clauses": clauses,
        "BR": DEGENERATE if not non_degenerate else (HOLDS if clauses["holds"] else FAILS),
    }


def criteria(study: Study) -> dict[str, Any]:
    """Primary setting, outcome per tree kind, and the robustness grid."""
    out: dict[str, Any] = {
        "primary_setting": dict(core.PRIMARY, index="RAM-index", cached_rows=64),
        "complete": study.complete,
        "missing": study.missing,
        "tree_kinds": {},
    }
    for kind in core.TREE_KINDS:
        if not study.complete:
            out["tree_kinds"][kind] = {
                "LRU": INCOMPLETE,
                "CONC": INCOMPLETE,
                "BR": INCOMPLETE,
                "outcome": INCOMPLETE,
                "reason": f"{len(study.missing)} of {len(study.expected)} checkpoints missing, "
                "failed or incomplete; the full study needs all 27 parent/seed pairs",
            }
            continue
        grid = [evaluate_setting(study, kind, rows, cap) for rows in core.RS for cap in core.CS]
        primary = next(
            g for g in grid if (g["R"], g["C"]) == (core.PRIMARY["R"], core.PRIMARY["C"])
        )
        others = [
            g
            for g in grid
            if g["R"] <= 8
            and (g["R"], g["C"]) != (core.PRIMARY["R"], core.PRIMARY["C"])
            and g["status"] == "NON-DEGENERATE"
            and g["LRU"] == HOLDS
            and g["CONC"] == FAILS
        ]
        robust = bool(others)
        br = branch_placement(study, kind, core.PRIMARY_R, core.PRIMARY_C)
        out["tree_kinds"][kind] = {
            "LRU": primary["LRU"],
            "CONC": primary["CONC"],
            "BR": br["BR"],
            "primary": primary,
            "branch_placement": br,
            "outcome": outcome_for(primary["LRU"], primary["CONC"], robust),
            "robust_other_settings": [(g["R"], g["C"]) for g in others],
            "robustness_grid": [
                {
                    "R": g["R"],
                    "C": g["C"],
                    "cached_rows": g["cached_rows"],
                    "status": g["status"],
                    "LRU": g["LRU"],
                    "CONC": g["CONC"],
                    "CONC_flat_mean": g["CONC_non_degeneracy"]["flat_mean"],
                    "CONC_tree_mean": g["CONC_non_degeneracy"]["tree_mean"],
                    "flat_mean": g["non_degeneracy"]["flat_mean"],
                    "tree_mean": g["non_degeneracy"]["tree_mean"],
                    "ratio_of_means": g["LRU_clauses"]["ratio_of_means"],
                    "cells_lower": g["LRU_clauses"]["cells_strictly_lower"],
                    "parents_lower": g["LRU_clauses"]["parents_strictly_lower"],
                    "CONC_ratio_of_means": g["CONC_clauses"]["ratio_of_means"],
                    "CONC_cells_lower": g["CONC_clauses"]["cells_strictly_lower"],
                    "CONC_parents_lower": g["CONC_clauses"]["parents_strictly_lower"],
                }
                for g in grid
            ],
            "branch_placement_grid": [
                branch_placement(study, kind, rows, cap) for rows in core.RS for cap in core.CS
            ],
        }
    return out


# --- descriptive tables (no pass/fail) ------------------------------------------------------------
def _avg(values: Values | None) -> float | None:
    return None if values is None else float(mean(list(values.values())))


def descriptive(study: Study) -> dict[str, Any]:
    """Tables over whatever completed (each entry carries the number of cells it averages)."""
    done = [lbl for lbl in study.records if study.records[lbl].get("record", {}).get("complete")]
    out: dict[str, Any] = {"checkpoints_used": len(done)}
    kinds = core.KINDS

    def cells(kind: str) -> list[dict[str, Any]]:
        return [
            study.records[core.cell_label(p, kind)]
            for p in study.pairs
            if core.cell_label(p, kind) in study.records
            and study.records[core.cell_label(p, kind)].get("record", {}).get("complete")
        ]

    out["utilization"] = {
        kind: {
            "cells": len(cells(kind)),
            "mean_unique_selected_slots": _mean_float(
                [c["record"]["evaluation_counts"]["unique_selected_slots"] for c in cells(kind)]
            ),
        }
        for kind in kinds
    }
    layouts = {k: core.layouts_for(k) for k in kinds}
    page_table: dict[str, Any] = {}
    for kind in kinds:
        for rows in core.RS:
            for layout in ("L-ID", "L-RAND", "L-FREQ"):
                use = cells(kind)
                if not use:
                    continue
                actual = [distinct_pages(c, core.STREAM_ACTUAL, layout, rows) for c in use]
                uniform = [
                    mean(
                        [
                            Fraction(c["record"]["uniform_reference"][nm][str(rows)])
                            for nm in layout_names(layout)
                        ]
                    )
                    for c in use
                ]
                page_table[f"{kind}|{layout}|R{rows}"] = {
                    "cells": len(use),
                    "mean_distinct_pages_per_query": float(mean(actual)),
                    "mean_uniform_reference": float(mean(uniform)),
                    "ratio_of_means": float(mean(actual) / mean(uniform)),
                    "uncached_amplification": float(mean(actual) * rows / core.TOP),
                }
    out["pages_per_query_vs_uniform"] = page_table
    # Registered decomposition: uniform -> frequency-matched -> order-shuffled -> actual, per
    # architecture (mean over its cells) and per checkpoint.
    decomposition: dict[str, Any] = {}
    for kind in kinds:
        use = cells(kind)
        if use:
            decomposition.update({f"{kind}|{key}": v for key, v in _decompose(use).items()})
    per_checkpoint: dict[str, Any] = {}
    for kind in kinds:
        for cell in cells(kind):
            per_checkpoint[cell["label"]] = _decompose([cell])
    out["decomposition"] = {
        "cells_averaged": {kind: len(cells(kind)) for kind in kinds},
        "note": "The uniform step is the closed form for per-query pages only; no uniform stream "
        "is simulated, so it is null for cache misses (PENDING LEAD REVIEW). Frequency-matched "
        "is the exact count-preserving null (ADR-0013 section 14 item 8): the concentration "
        "effect no longer contains a marginal distortion.",
        "by_kind_layout_R": decomposition,
        "per_checkpoint": per_checkpoint,
    }
    out["cold_misses_and_amplification"] = _cold_and_amplification(cells)
    out["cumulative_distinct_pages"] = _curve_table(cells)
    out["eviction_order_sensitivity"] = _eviction_sensitivity(study)
    # Layout and stream tables of mean warm capacity misses.
    layout_table: dict[str, Any] = {}
    for kind in kinds:
        use = cells(kind)
        if not use:
            continue
        for layout in (*layouts[kind][:1], "L-RAND", *layouts[kind][4:]):
            for rows in core.RS:
                for cap in core.CS:
                    layout_table[f"{kind}|{layout}|R{rows}|C{cap}"] = float(
                        mean(
                            [capacity_misses(c, core.STREAM_ACTUAL, layout, rows, cap) for c in use]
                        )
                    )
    out["warm_capacity_misses_by_layout"] = layout_table
    shuffled: dict[str, Any] = {}
    for kind in kinds:
        use = cells(kind)
        if not use:
            continue
        for layout in core.LAYOUTS_OTHER:
            for rows in core.RS:
                for cap in core.CS:
                    shuffled[f"{kind}|{layout}|R{rows}|C{cap}"] = {
                        s: float(mean([capacity_misses(c, s, layout, rows, cap) for c in use]))
                        for s in (core.STREAM_ACTUAL, core.STREAM_CONTEXT)
                    }
    out["context_shuffled_vs_actual"] = shuffled
    out["page_reuse"] = _reuse_table(study, cells)
    out["bootstrap_distinct_pages"] = _bootstrap_table(cells)
    out["branch_locality"] = _branch_table(cells)
    out["ssd_index_key_reads"] = _key_table(cells)
    out["flat_layout_report_only"] = _flat_exchangeability(study)
    return out


STEPS = {
    "frequency_matched": "freq_matched",
    "order_shuffled": core.STREAM_ORDER,
    "actual": core.STREAM_ACTUAL,
    "context_shuffled": core.STREAM_CONTEXT,
}


def _decompose(use: list[dict[str, Any]]) -> dict[str, Any]:
    """The registered decomposition for the checkpoints in ``use`` (their mean when several)."""
    out: dict[str, Any] = {}
    for layout in core.LAYOUTS_OTHER:
        for rows in core.RS:
            uniform_pages = mean(
                [Fraction(c["record"]["uniform_reference"][layout][str(rows)]) for c in use]
            )
            pages = {
                name: mean([distinct_pages(c, s, layout, rows) for c in use])
                for name, s in STEPS.items()
            }
            stage: dict[str, Any] = {
                "pages_per_query": {
                    "uniform": float(uniform_pages),
                    **{k: float(v) for k, v in pages.items()},
                    "effect_concentration": float(pages["frequency_matched"] - uniform_pages),
                    "effect_co_selection": float(
                        pages["order_shuffled"] - pages["frequency_matched"]
                    ),
                    "effect_temporal_order": float(pages["actual"] - pages["order_shuffled"]),
                }
            }
            by_cap = {}
            for cap in core.CS:
                vals = {
                    name: mean([capacity_misses(c, s, layout, rows, cap) for c in use])
                    for name, s in STEPS.items()
                }
                by_cap[str(cap)] = {
                    "uniform": None,
                    **{k: float(v) for k, v in vals.items()},
                    "effect_co_selection": float(
                        vals["order_shuffled"] - vals["frequency_matched"]
                    ),
                    "effect_temporal_order": float(vals["actual"] - vals["order_shuffled"]),
                }
            stage["warm_capacity_misses_per_query"] = by_cap
            out[f"{layout}|R{rows}"] = stage
    return out


def _actual_group(c: dict[str, Any], layout: str, rows: int) -> list[dict[str, Any]]:
    return [
        c["record"]["streams"][core.STREAM_ACTUAL][f"{name}|R{rows}"]
        for name in layout_names(layout)
    ]


def _cold_and_amplification(cells: Any) -> dict[str, Any]:
    """Descriptive (ADR-0013 section 5): cold misses from an empty cache over the whole stream, and
    cached read amplification = bytes of missed pages / bytes of the rows needed
    (``misses * R / (8 * queries)``; ``R`` rows per page, eight value rows per query), over the
    counted half (all misses, and capacity misses only)."""
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        use = cells(kind)
        if not use:
            continue
        for layout in ("L-ID", "L-RAND", "L-FREQ"):
            for rows in core.RS:
                for cap in core.CS:
                    cold, amp_all, amp_cap, first = [], [], [], []
                    for c in use:
                        n, counted = c["queries"], c["queries"] - c["queries"] // 2
                        groups = [g["by_c"][str(cap)] for g in _actual_group(c, layout, rows)]
                        cold.append(mean([Fraction(g["misses_all"], n) for g in groups]))
                        first.append(mean([Fraction(g["first_touch_all"], n) for g in groups]))
                        amp_all.append(
                            mean(
                                [
                                    Fraction(g["misses_warm"] * rows, counted * core.TOP)
                                    for g in groups
                                ]
                            )
                        )
                        amp_cap.append(
                            mean(
                                [
                                    Fraction(
                                        (g["misses_warm"] - g["first_touch_warm"]) * rows,
                                        counted * core.TOP,
                                    )
                                    for g in groups
                                ]
                            )
                        )
                    table[f"{kind}|{layout}|R{rows}|C{cap}"] = {
                        "cells": len(use),
                        "cold_misses_per_query_whole_stream": float(mean(cold)),
                        "first_touch_misses_per_query_whole_stream": float(mean(first)),
                        "cached_amplification_all_warm_misses": float(mean(amp_all)),
                        "cached_amplification_warm_capacity_misses": float(mean(amp_cap)),
                    }
    return table


def _curve_table(cells: Any) -> dict[str, Any]:
    """Cumulative distinct-page curve and distinct pages per context (actual stream)."""
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        use = cells(kind)
        if not use:
            continue
        for layout in ("L-ID", "L-RAND", "L-FREQ"):
            for rows in core.RS:
                groups = [(c, _actual_group(c, layout, rows)) for c in use]
                points = groups[0][1][0]["stats"]["curve_points"]
                curve = [
                    sum(sum(g["stats"]["curve"][i] for g in gs) / len(gs) for _, gs in groups)
                    / len(groups)
                    for i in range(len(points))
                ]
                per_context = [
                    sum(g["stats"]["distinct_per_context_sum"] for g in gs)
                    / len(gs)
                    / (c["queries"] // core.CONTEXT)
                    for c, gs in groups
                ]
                table[f"{kind}|{layout}|R{rows}"] = {
                    "cells": len(use),
                    "curve_points_queries": points,
                    "mean_distinct_pages_over_first_n_queries": curve,
                    "mean_distinct_pages_per_context": sum(per_context) / len(per_context),
                }
    return table


def _eviction_sensitivity(study: Study) -> dict[str, Any]:
    """Item 10: descending-order tie rule at the primary setting (R = 2, C = 32, L-FREQ, actual
    stream, every checkpoint). A sensitivity table with NO criterion."""
    rows: dict[str, Any] = {}
    per_kind: dict[str, dict[Pair, tuple[Fraction, Fraction]]] = {k: {} for k in core.KINDS}
    for pair, kind in study.expected:
        rec = study.rec(pair, kind)
        if rec is None or not rec.get("record", {}).get("complete"):
            continue
        sens = rec["record"].get("eviction_order_sensitivity")
        if sens is None:
            continue
        counted = rec["queries"] - rec["queries"] // 2
        asc = Fraction(
            sens["ascending"]["misses_warm"] - sens["ascending"]["first_touch_warm"], counted
        )
        desc = Fraction(
            sens["descending"]["misses_warm"] - sens["descending"]["first_touch_warm"], counted
        )
        rows[core.cell_label(pair, kind)] = {
            "ascending_warm_capacity_misses_per_query": float(asc),
            "descending_warm_capacity_misses_per_query": float(desc),
        }
        per_kind[kind][pair] = (asc, desc)
    table: dict[str, Any] = {}
    for kind, values in per_kind.items():
        if values:
            table[kind] = {
                "cells": len(values),
                "mean_ascending": float(mean([a for a, _ in values.values()])),
                "mean_descending": float(mean([d for _, d in values.values()])),
            }
    flat = per_kind[FLAT]
    for kind in core.TREE_KINDS:
        shared = sorted(set(flat) & set(per_kind[kind]))
        if not shared:
            continue
        for order, index in (("ascending", 0), ("descending", 1)):
            ref = {p: flat[p][index] for p in shared}
            cand = {p: per_kind[kind][p][index] for p in shared}
            ref_mean = mean(list(ref.values()))
            table[kind][f"{order}_ratio_of_means_vs_flat"] = (
                float(mean(list(cand.values())) / ref_mean) if ref_mean else None
            )
            table[kind][f"{order}_pairs_strictly_lower_than_flat"] = sum(
                1 for p in shared if cand[p] < ref[p]
            )
        table[kind]["pairs"] = len(shared)
    return {
        "setting": dict(core.PRIMARY, index="RAM-index"),
        "label": "sensitivity of the eviction tie order (ascending is the registered rule); "
        "descriptive, NO criterion, no outcome depends on it",
        "by_architecture": table,
        "per_checkpoint": rows,
    }


def _mean_float(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def _reuse_table(study: Study, cells: Any) -> dict[str, Any]:
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        use = cells(kind)
        if not use:
            continue
        for rows in core.RS:
            for layout in core.LAYOUTS_OTHER:
                entry: dict[str, Any] = {}
                for part in ("reuse_within", "reuse_cross"):
                    reused = sum(
                        c["record"]["streams"][core.STREAM_ACTUAL][f"{layout}|R{rows}"]["stats"][
                            part
                        ][0]
                        for c in use
                    )
                    touches = sum(
                        c["record"]["streams"][core.STREAM_ACTUAL][f"{layout}|R{rows}"]["stats"][
                            part
                        ][1]
                        for c in use
                    )
                    entry[part] = reused / touches if touches else None
                table[f"{kind}|{layout}|R{rows}"] = entry
    return table


def _bootstrap_table(cells: Any) -> dict[str, Any]:
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        use = cells(kind)
        if not use:
            continue
        for layout in core.LAYOUTS_OTHER:
            for rows in core.RS:
                key = f"{layout}|R{rows}"
                boots = [c["record"]["bootstrap"][key] for c in use]
                table[f"{kind}|{key}"] = {
                    "cells": len(use),
                    "mean_of_means": sum(b["mean"] for b in boots) / len(boots),
                    "mean_lower": sum(b["boot_lower"] for b in boots) / len(boots),
                    "mean_upper": sum(b["boot_upper"] for b in boots) / len(boots),
                }
    return table


def _branch_table(cells: Any) -> dict[str, Any]:
    table: dict[str, Any] = {}
    for kind in core.TREE_KINDS:
        use = cells(kind)
        if not use:
            continue
        row: dict[str, Any] = {"cells": len(use)}
        for part in (
            "same_top1_within",
            "same_top1_across",
            "share_branch_within",
            "share_branch_across",
        ):
            hits = sum(c["record"]["branch_locality"][part][0] for c in use)
            pairs_n = sum(c["record"]["branch_locality"][part][1] for c in use)
            row[part] = hits / pairs_n
        row["top1_mean_run_length"] = sum(
            c["record"]["branch_locality"]["top1_mean_run_length"] for c in use
        ) / len(use)
        row["distinct_branches_per_context"] = sum(
            c["record"]["branch_locality"]["distinct_branches_per_context_sum"]
            / c["record"]["branch_locality"]["contexts"]
            for c in use
        ) / len(use)
        table[kind] = row
    return table


def _key_table(cells: Any) -> dict[str, Any]:
    """SSD-index key reads (descriptive, analytical for flat): warm misses per query in the key
    cache, and the value plus key warm capacity misses per query at each R and C."""
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        use = cells(kind)
        if not use:
            continue
        for rows in core.RS:
            size = str(core.PAGE_BYTES_FOR_R[rows])
            for cap in core.CS:
                counted = [c["queries"] - c["queries"] // 2 for c in use]
                if kind == FLAT:
                    keys = [
                        Fraction(
                            c["record"]["key_reads"]["flat"][str(rows)]["by_c"][str(cap)][
                                "misses_warm"
                            ],
                            n,
                        )
                        for c, n in zip(use, counted, strict=True)
                    ]
                    label = "analytical"
                else:
                    keys = []
                    for c, n in zip(use, counted, strict=True):
                        per_layout = c["record"]["key_reads"]["tree"][size]["layouts"]
                        keys.append(
                            mean(
                                [
                                    Fraction(per_layout[name]["by_c"][str(cap)]["misses_warm"], n)
                                    for name in core.KEY_LAYOUTS
                                ]
                            )
                        )
                    label = "simulated (mean of L-ID and the three L-RAND key layouts is reported "
                    label += "per layout below)"
                values = [
                    capacity_misses(c, core.STREAM_ACTUAL, core.LAYOUT_FREQ, rows, cap) for c in use
                ]
                table[f"{kind}|R{rows}|C{cap}"] = {
                    "key_warm_misses_per_query_mean": float(mean(keys)),
                    "value_warm_capacity_misses_L_FREQ_mean": float(mean(values)),
                    "label": label if kind != FLAT else "analytical",
                    "note": "key rows: 64 B; key cache capacity equals the value capacity set",
                }
    return table


def _flat_exchangeability(study: Study) -> dict[str, Any]:
    """Report-only (not a stop): per (R, C), the number of flat cells whose L-ID warm capacity
    misses fall outside the range of their three L-RAND layouts."""
    out: dict[str, Any] = {}
    flat_pairs = [
        p
        for p in study.pairs
        if study.rec(p, FLAT) is not None and study.rec(p, FLAT).get("record", {}).get("complete")  # type: ignore[union-attr]
    ]
    for rows in core.RS:
        for cap in core.CS:
            outside = 0
            for p in flat_pairs:
                rec = study.rec(p, FLAT)
                assert rec is not None
                ident = capacity_misses(rec, core.STREAM_ACTUAL, core.LAYOUT_ID, rows, cap)
                rand = [
                    capacity_misses(rec, core.STREAM_ACTUAL, name, rows, cap)
                    for name in core.LAYOUTS_RAND
                ]
                outside += ident < min(rand) or ident > max(rand)
            out[f"R{rows}|C{cap}"] = {
                "flat_cells": len(flat_pairs),
                "L_ID_outside_L_RAND_range": outside,
            }
    out["note"] = (
        "report-only; for exchangeable layouts L-ID is outside the others' range about half "
        "the time"
    )
    return out


# --- top level ------------------------------------------------------------------------------------
def analyze_records(
    records: dict[str, dict[str, Any]], expected: list[tuple[Pair, str]] | None = None
) -> dict[str, Any]:
    study = Study(records, expected)
    return {
        "schema": core.SCHEMA_ANALYSIS,
        "study": core.STUDY,
        "spec_reference": core.SPEC,
        "label": "implementation self-check output; not Astra validation; not human approval",
        "checkpoints_expected": len(study.expected),
        "checkpoints_complete": len(study.expected) - len(study.missing),
        "missing_or_failed": study.missing,
        "criteria": criteria(study),
        "descriptive": descriptive(study),
    }
