"""P7-B analysis (ADR-0014 sections 2, 6, 7, 7a, 9): E, rho, the utilization-adjusted ratio,
non-degeneracy, the four classes, tie-rule dependence, HB_K / HU_K / PART_K, the ordered outcome
table, stream pairing, decision classes, the recommendation table and every descriptive item.

All criterion arithmetic is exact: the warm capacity-miss counts are integers, so E, rho, the OLS
fit (on the exact rational value of each float x) and every threshold comparison use
``fractions.Fraction``; equality at a boundary is detected, never rounded. A missing, unfinished or
failed checkpoint makes every criterion INCOMPLETE and lists the missing labels; nothing here raises
on missing data. Counts, parents and the 22/27 and 8/9 rules are as written in section 7.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

from fractions import Fraction
from typing import Any

from . import p7b_core as core
from .p5_config import FLAT
from .p6_common import Pair

Values = dict[Pair, Fraction]

# --- registered thresholds (section 7)
RHO_BETTER, RHO_WORSE = Fraction(4, 5), Fraction(5, 4)
BAND_LOW, BAND_HIGH = Fraction(9, 10), Fraction(11, 10)
MIN_CELLS, MIN_PARENTS = 22, 8
FLAT_DEN_FLOOR, TREE_DEN_FLOOR = Fraction(1, 20), Fraction(1, 100)
EACH_DEN_FLOOR, NUM_FLOOR = Fraction(1, 200), Fraction(1, 100)
PART_RATIO = Fraction(4, 5)
PART_DEN_EACH, PART_DEN_MEAN = Fraction(1, 200), Fraction(1, 100)

# class labels
TREE_BETTER, FLAT_BETTER = "TREE MATERIALLY BETTER", "FLAT MATERIALLY BETTER"
WITHIN, INTERMEDIATE = "WITHIN 10%", "INTERMEDIATE"
TIE_DEPENDENT = "TIE-RULE DEPENDENT"
DEGENERATE, INCOMPLETE = "DEGENERATE", "INCOMPLETE"
REAL_BETTER, NOT_BETTER = "REAL BRANCHES BETTER", "NOT BETTER"

# outcome labels
UNRESOLVED = "UNRESOLVED"
HIERARCHY = "HIERARCHY-SPECIFIC ADVANTAGE"
NOT_BRANCH = "ADVANTAGE NOT SHOWN TO BE BRANCH-SPECIFIC"
NOT_ROBUST = "NOT ROBUST"
FLAT_COAX_BETTER = "FLAT CO-ACCESS BETTER"
WITHIN_FLAT = "WITHIN 10% OF FLAT CO-ACCESS"
INTERMEDIATE_TREE = "INTERMEDIATE (tree-favouring)"
INTERMEDIATE_FLAT = "INTERMEDIATE (flat-favouring)"
OUTCOME_LABELS = (
    UNRESOLVED,
    HIERARCHY,
    NOT_BRANCH,
    NOT_ROBUST,
    FLAT_COAX_BETTER,
    WITHIN_FLAT,
    INTERMEDIATE_TREE,
    INTERMEDIATE_FLAT,
)
N_OUTCOMES = (WITHIN_FLAT, FLAT_COAX_BETTER, NOT_BRANCH)

REPLICATED, UNRESOLVED_BOTH = "REPLICATED", "UNRESOLVED ON BOTH STREAMS"
SINGLE_STREAM, NOT_REPLICATED = "SINGLE-STREAM", "NOT REPLICATED"
CLASS_S, CLASS_U, CLASS_N, CLASS_I = "S", "U", "N", "I"

RECOMMENDATIONS = {
    1: {
        "classes": "at least one tree kind in S",
        "statement": (
            "Under this page model, branch-constrained placement gives that tree kind incremental "
            "locality that refined co-access clustering does not give flat memory, at common "
            "utilization, in two settings and on two streams, and real branches let the layout "
            "exploit materially more structure than arbitrary groups."
        ),
        "recommendation": (
            "Grounds to propose a memory-capacity scaling design whose first question is whether "
            "the advantage persists with size, resting on the tree kind named. Both settings use "
            "hypothetical row sizes on a 768 KiB memory, so this supports a proposal for review "
            "and nothing more. It involves training and needs its own specification and approval."
        ),
    },
    2: {
        "classes": "both tree kinds in N",
        "statement": (
            "A flat memory whose slots are arranged by observed co-access gets locality within 10% "
            "of, or better than, the existing hierarchy's, or the tree's edge is not attributable "
            "to its branches. Any remaining difference is stated with its size and direction."
        ),
        "recommendation": (
            "Do not scale the existing hierarchy on storage-locality grounds. The options are to "
            "redesign it (a locality-aware objective, H3, or routing whose branches persist across "
            "queries) or to stop the hierarchy line."
        ),
    },
    3: {
        "classes": "both tree kinds in U",
        "statement": "The registered settings cannot discriminate.",
        "recommendation": "No recommendation.",
    },
    4: {
        "classes": "anything else",
        "statement": (
            "A difference smaller than the registered margin, or in one setting or one stream "
            "only, or dependent on the tie rule, or differing between tree kinds."
        ),
        "recommendation": (
            "Not sufficient to recommend scaling. Report sizes and directions for each kind; the "
            "human lead decides whether a stronger test is worth it."
        ),
    },
}


def mean(values: list[Fraction]) -> Fraction:
    return sum(values, Fraction(0)) / len(values)


def frac_str(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def fl(value: Fraction | None) -> float | None:
    return None if value is None else float(value)


def parents(pair_list: list[Pair]) -> dict[tuple[int, int], list[Pair]]:
    out: dict[tuple[int, int], list[Pair]] = {}
    for pair in pair_list:
        out.setdefault(core.parent_of(pair), []).append(pair)
    return out


# --- exact ordinary least squares -----------------------------------------------------------------
def ols_adjusted(
    e_flat: Values, e_tree: Values, x_flat: dict[Pair, float], x_tree: dict[Pair, float]
) -> dict[str, Any]:
    """Fit ``E = a + b * x + d * [tree]`` by ordinary least squares over the flat and tree cells
    (x = ln of the entropy-effective slot count = the entropy in nats) and return
    ``rho_adj = (a + b * xbar + d) / (a + b * xbar)`` with xbar the mean of x over all cells.
    The fit is exact: each float x enters as its exact rational value. ``rho_adj`` is ``None``
    when ``a + b * xbar`` is not positive or the design is singular."""
    ys: list[Fraction] = []
    xs: list[Fraction] = []
    ts: list[Fraction] = []
    for pair, value in e_flat.items():
        ys.append(value)
        xs.append(Fraction(x_flat[pair]))
        ts.append(Fraction(0))
    for pair, value in e_tree.items():
        ys.append(value)
        xs.append(Fraction(x_tree[pair]))
        ts.append(Fraction(1))
    n = len(ys)
    sx, st, sy = sum(xs, Fraction(0)), sum(ts, Fraction(0)), sum(ys, Fraction(0))
    sxx = sum((x * x for x in xs), Fraction(0))
    sxt = sum((x * t for x, t in zip(xs, ts, strict=True)), Fraction(0))
    stt = sum((t * t for t in ts), Fraction(0))
    sxy = sum((x * y for x, y in zip(xs, ys, strict=True)), Fraction(0))
    sty = sum((t * y for t, y in zip(ts, ys, strict=True)), Fraction(0))
    # normal equations for (a, b, d)
    matrix = [
        [Fraction(n), sx, st, sy],
        [sx, sxx, sxt, sxy],
        [st, sxt, stt, sty],
    ]
    solution = _solve(matrix)
    if solution is None:
        return {"defined": False, "reason": "singular design", "a": None, "b": None, "d": None}
    a, b, d = solution
    xbar = sx / n
    level = a + b * xbar
    out: dict[str, Any] = {
        "a": fl(a),
        "b": fl(b),
        "d": fl(d),
        "x_mean": float(xbar),
        "level_at_mean_utilization": fl(level),
        "a_exact": frac_str(a),
        "b_exact": frac_str(b),
        "d_exact": frac_str(d),
        "cells": n,
    }
    if level <= 0:
        out.update(defined=False, rho_adj=None, reason="a + b * xbar is not positive")
        out["rho_adj_exact"] = None
        out["_rho_adj"] = None
        return out
    rho_adj = (level + d) / level
    out.update(defined=True, rho_adj=float(rho_adj), rho_adj_exact=frac_str(rho_adj))
    out["_rho_adj"] = rho_adj
    return out


def _solve(rows: list[list[Fraction]]) -> tuple[Fraction, Fraction, Fraction] | None:
    """Gauss-Jordan elimination on a 3 x 4 augmented matrix of Fractions."""
    m = [row[:] for row in rows]
    size = len(m)
    for col in range(size):
        pivot = next((r for r in range(col, size) if m[r][col] != 0), None)
        if pivot is None:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        m[col] = [v / scale for v in m[col]]
        for r in range(size):
            if r != col and m[r][col] != 0:
                factor = m[r][col]
                m[r] = [v - factor * w for v, w in zip(m[r], m[col], strict=True)]
    return m[0][3], m[1][3], m[2][3]


# --- the class table
def classify(rho: Fraction, rho_adj: Fraction | None, favour_tree: bool, favour_flat: bool) -> str:
    """Section 7, evaluated in registered order; the first that applies is taken. An undefined
    adjusted ratio cannot satisfy any class and gives INTERMEDIATE."""
    if rho_adj is None:
        return INTERMEDIATE
    if rho <= RHO_BETTER and rho_adj <= RHO_BETTER and favour_tree:
        return TREE_BETTER
    if rho >= RHO_WORSE and rho_adj >= RHO_WORSE and favour_flat:
        return FLAT_BETTER
    if BAND_LOW <= rho <= BAND_HIGH and BAND_LOW <= rho_adj <= BAND_HIGH:
        return WITHIN
    return INTERMEDIATE


def count_rule(reference: Values, candidate: Values) -> dict[str, Any]:
    """Counts: candidate strictly lower than reference in at least 22 of the pairs and the
    candidate's parent mean strictly lower in at least 8 parents. Ties count for neither."""
    pair_list = list(reference)
    lower_cells = sum(1 for p in pair_list if candidate[p] < reference[p])
    groups = parents(pair_list)
    lower_parents = sum(
        1
        for members in groups.values()
        if mean([candidate[p] for p in members]) < mean([reference[p] for p in members])
    )
    return {
        "cells_strictly_lower": lower_cells,
        "cells_tied": sum(1 for p in pair_list if candidate[p] == reference[p]),
        "cells_total": len(pair_list),
        "parents_strictly_lower": lower_parents,
        "parents_total": len(groups),
        "holds": lower_cells >= MIN_CELLS and lower_parents >= MIN_PARENTS,
    }


# --- reading the simulation records
class Stream:
    """The simulation records of one evaluation stream, indexed by checkpoint, with the missing
    ones listed."""

    def __init__(
        self,
        name: str,
        records: dict[str, dict[str, Any]],
        expected: list[tuple[Pair, str]] | None = None,
    ) -> None:
        self.name = name
        self.expected = expected if expected is not None else core.registered_checkpoints()
        self.records = records
        self.missing = [
            core.cell_label(p, k)
            for p, k in self.expected
            if not records.get(core.cell_label(p, k), {}).get("record", {}).get("complete")
        ]
        self.pairs: list[Pair] = sorted({p for p, _ in self.expected})
        self.complete = not self.missing and len(self.pairs) == 27

    def rec(self, pair: Pair, kind: str) -> dict[str, Any] | None:
        data = self.records.get(core.cell_label(pair, kind))
        if data is None or not data.get("record", {}).get("complete"):
            return None
        return data

    def group(
        self, pair: Pair, kind: str, stream: str, layout: str, rows: int
    ) -> dict[str, Any] | None:
        rec = self.rec(pair, kind)
        if rec is None:
            return None
        found = rec["record"]["streams"].get(stream, {}).get(core.layout_key(layout, rows))
        return found if isinstance(found, dict) else None

    def counts(
        self, pair: Pair, kind: str, stream: str, layout: str, rows: int, cap: int, tie: str
    ) -> dict[str, Any] | None:
        group = self.group(pair, kind, stream, layout, rows)
        if group is None:
            return None
        found = group["by_c"].get(str(cap), {}).get(tie)
        return found if isinstance(found, dict) else None

    def counted(self, pair: Pair, kind: str) -> int:
        rec = self.rec(pair, kind)
        assert rec is not None
        queries = int(rec["record"]["queries"])
        return queries - queries // 2

    def m(
        self,
        pair: Pair,
        kind: str,
        stream: str,
        layout: str,
        rows: int,
        cap: int,
        tie: str = "asc",
    ) -> Fraction | None:
        """Warm capacity misses per query. ``L-RAND`` is the mean of its three permutations."""
        names = list(core.L_RANDS) if layout == "L-RAND" else [layout]
        parts: list[Fraction] = []
        for name in names:
            entry = self.counts(pair, kind, stream, name, rows, cap, tie)
            if entry is None:
                return None
            parts.append(
                Fraction(entry["misses_warm"] - entry["first_touch_warm"], self.counted(pair, kind))
            )
        return mean(parts)

    def null_mean(
        self, pair: Pair, kind: str, layout: str, rows: int, cap: int, tie: str
    ) -> Fraction | None:
        """The checkpoint's null: the mean of m over the three count-preserving replicates."""
        parts = []
        for stream in core.STREAMS_NULL:
            value = self.m(pair, kind, stream, layout, rows, cap, tie)
            if value is None:
                return None
            parts.append(value)
        return mean(parts)

    def entropy(self, pair: Pair, kind: str) -> float | None:
        rec = self.rec(pair, kind)
        return None if rec is None else float(rec["record"]["evaluation_counts"]["entropy_nats"])

    def values(self, kind: str, fn: Any) -> Values | None:
        out: Values = {}
        for pair in self.pairs:
            value = fn(pair, kind)
            if value is None:
                return None
            out[pair] = value
        return out

    def x_values(self, kind: str) -> dict[Pair, float] | None:
        out: dict[Pair, float] = {}
        for pair in self.pairs:
            value = self.entropy(pair, kind)
            if value is None:
                return None
            out[pair] = value
        return out


# --- the criterion comparison
def e_values(
    stream: Stream, kind: str, layout: str, rows: int, cap: int, tie: str, numerator: str
) -> tuple[Values | None, Values | None, Values | None]:
    """(numerators m, denominators, E) per pair for one architecture and layout."""
    num = stream.values(kind, lambda p, k: stream.m(p, k, numerator, layout, rows, cap, tie))
    den = stream.values(kind, lambda p, k: stream.null_mean(p, k, core.L_FREQ, rows, cap, tie))
    if num is None or den is None:
        return None, None, None
    if any(v == 0 for v in den.values()):
        return num, den, None
    return num, den, {p: num[p] / den[p] for p in num}


def comparison_one_tie(
    stream: Stream,
    tree_kind: str,
    rows: int,
    cap: int,
    tie: str,
    tree_layout: str,
    flat_layout: str,
    numerator: str = core.STREAM_ACTUAL,
) -> dict[str, Any]:
    """Non-degeneracy, E, rho, rho_adj, counts and class of tree layout against flat layout, for
    one setting and one tie rule."""
    base: dict[str, Any] = {
        "R": rows,
        "C": cap,
        "tie": tie,
        "tree_layout": tree_layout,
        "flat_layout": flat_layout,
        "numerator_stream": numerator,
    }
    f_num, f_den, f_e = e_values(stream, FLAT, flat_layout, rows, cap, tie, numerator)
    t_num, t_den, t_e = e_values(stream, tree_kind, tree_layout, rows, cap, tie, numerator)
    if f_num is None or t_num is None or f_den is None or t_den is None:
        return {**base, "status": INCOMPLETE}
    nd = {
        "flat_denominator_mean": float(mean(list(f_den.values()))),
        "tree_denominator_mean": float(mean(list(t_den.values()))),
        "min_denominator": float(min([*f_den.values(), *t_den.values()])),
        "flat_numerator_mean": float(mean(list(f_num.values()))),
        "tree_numerator_mean": float(mean(list(t_num.values()))),
    }
    ok = (
        mean(list(f_den.values())) >= FLAT_DEN_FLOOR
        and mean(list(t_den.values())) >= TREE_DEN_FLOOR
        and min([*f_den.values(), *t_den.values()]) >= EACH_DEN_FLOOR
        and mean(list(f_num.values())) >= NUM_FLOOR
        and mean(list(t_num.values())) >= NUM_FLOOR
    )
    nd["non_degenerate"] = ok
    if not ok or f_e is None or t_e is None:
        return {**base, "status": DEGENERATE, "non_degeneracy": nd}
    rho = mean(list(t_e.values())) / mean(list(f_e.values()))
    x_flat, x_tree = stream.x_values(FLAT), stream.x_values(tree_kind)
    assert x_flat is not None and x_tree is not None
    fit = ols_adjusted(f_e, t_e, x_flat, x_tree)
    rho_adj: Fraction | None = fit.pop("_rho_adj", None)
    tree_counts = count_rule(f_e, t_e)  # tree strictly lower than flat
    flat_counts = count_rule(t_e, f_e)  # flat strictly lower than tree (the mirror)
    label = classify(rho, rho_adj, tree_counts["holds"], flat_counts["holds"])
    return {
        **base,
        "status": "NON-DEGENERATE",
        "non_degeneracy": nd,
        "class": label,
        "rho": float(rho),
        "rho_exact": frac_str(rho),
        "rho_adj": fit.get("rho_adj"),
        "rho_adj_exact": fit.get("rho_adj_exact"),
        "adjustment": fit,
        "E_flat_mean": float(mean(list(f_e.values()))),
        "E_tree_mean": float(mean(list(t_e.values()))),
        "counts_favour_tree": tree_counts,
        "counts_favour_flat": flat_counts,
        "direction": "tree-favouring" if rho < 1 else "flat-favouring",
    }


def combine_ties(by_tie: dict[str, dict[str, Any]]) -> str:
    """A classification is recorded only if it is the same under every tie rule that was run;
    otherwise TIE-RULE DEPENDENT (treated as INTERMEDIATE). DEGENERATE or INCOMPLETE under any
    tie rule dominates."""
    statuses = {v["status"] for v in by_tie.values()}
    if INCOMPLETE in statuses:
        return INCOMPLETE
    if DEGENERATE in statuses:
        return DEGENERATE
    classes = {v["class"] for v in by_tie.values()}
    return classes.pop() if len(classes) == 1 else TIE_DEPENDENT


def comparison(
    stream: Stream,
    tree_kind: str,
    rows: int,
    cap: int,
    tree_layout: str,
    flat_layout: str,
    numerator: str = core.STREAM_ACTUAL,
    ties: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if ties is None:
        ties = core.TIES if (rows, cap) in core.CRITERION_SETTINGS else ("asc",)
    by_tie = {
        tie: comparison_one_tie(
            stream, tree_kind, rows, cap, tie, tree_layout, flat_layout, numerator
        )
        for tie in ties
    }
    return {
        "R": rows,
        "C": cap,
        "row_size": core.ROW_SIZE_LABEL[rows],
        "tree_layout": tree_layout,
        "flat_layout": flat_layout,
        "numerator_stream": numerator,
        "ties_run": list(ties),
        "class": combine_ties(by_tie),
        "by_tie": by_tie,
    }


# --- PART_K: real branches against arbitrary partitions, on exploited structure
def exploited(
    stream: Stream, kind: str, layout: str, rows: int, cap: int, tie: str
) -> Values | None:
    """S_c(L) = m(actual, L) / m(mean of the three nulls, L) per pair."""
    num = stream.values(
        kind, lambda p, k: stream.m(p, k, core.STREAM_ACTUAL, layout, rows, cap, tie)
    )
    den = stream.values(kind, lambda p, k: stream.null_mean(p, k, layout, rows, cap, tie))
    if num is None or den is None or any(v == 0 for v in den.values()):
        return None
    return {p: num[p] / den[p] for p in num}


def null_denominators(
    stream: Stream, kind: str, layout: str, rows: int, cap: int, tie: str
) -> Values | None:
    return stream.values(kind, lambda p, k: stream.null_mean(p, k, layout, rows, cap, tie))


def part_one_tie(stream: Stream, tree_kind: str, rows: int, cap: int, tie: str) -> dict[str, Any]:
    layouts = (core.L_BCOAX, *core.L_PCOAX)
    dens = {name: null_denominators(stream, tree_kind, name, rows, cap, tie) for name in layouts}
    base: dict[str, Any] = {"R": rows, "C": cap, "tie": tie}
    if any(v is None for v in dens.values()):
        return {**base, "status": INCOMPLETE}
    degenerate = {
        name: {
            "min": float(min(v.values())),
            "mean": float(mean(list(v.values()))),
            "degenerate": min(v.values()) < PART_DEN_EACH or mean(list(v.values())) < PART_DEN_MEAN,
        }
        for name, v in dens.items()
        if v is not None
    }
    if any(d["degenerate"] for d in degenerate.values()):
        return {**base, "status": DEGENERATE, "null_denominators": degenerate}
    s_b = exploited(stream, tree_kind, core.L_BCOAX, rows, cap, tie)
    s_i = [exploited(stream, tree_kind, name, rows, cap, tie) for name in core.L_PCOAX]
    if s_b is None or any(v is None for v in s_i):
        return {**base, "status": INCOMPLETE}
    partitions = [v for v in s_i if v is not None]
    pair_list = list(s_b)
    s_p = {p: mean([v[p] for v in partitions]) for p in pair_list}
    mean_b, mean_p = mean(list(s_b.values())), mean(list(s_p.values()))
    aggregate_counts = count_rule(s_p, s_b)  # S_B strictly lower than S_P
    aggregate = {
        "mean_S_B": float(mean_b),
        "mean_S_P": float(mean_p),
        "ratio": float(mean_b / mean_p),
        "ratio_exact": frac_str(mean_b / mean_p),
        "mean_clause": mean_b <= PART_RATIO * mean_p,
        **aggregate_counts,
    }
    aggregate["holds"] = aggregate["mean_clause"] and aggregate_counts["holds"]
    each: list[dict[str, Any]] = []
    for name, v in zip(core.L_PCOAX, partitions, strict=True):
        mean_i = mean(list(v.values()))
        each.append(
            {
                "layout": name,
                "mean_S": float(mean_i),
                "ratio": float(mean_b / mean_i),
                "clause": mean_b <= PART_RATIO * mean_i,
            }
        )
    spread = {
        "partition_ratio_min": min(e["ratio"] for e in each),
        "partition_ratio_max": max(e["ratio"] for e in each),
        "cells_S_B_lower_than_all_five": sum(
            1 for p in pair_list if all(s_b[p] < v[p] for v in partitions)
        ),
        "per_cell_spread_mean": float(
            mean(
                [
                    (max(v[p] for v in partitions) - min(v[p] for v in partitions))
                    / mean([v[p] for v in partitions])
                    for p in pair_list
                ]
            )
        ),
        "per_cell_spread_definition": (
            "(max - min) / mean of the five S values, averaged over cells"
        ),
    }
    raw_b = stream.values(
        tree_kind, lambda p, k: stream.m(p, k, core.STREAM_ACTUAL, core.L_BCOAX, rows, cap, tie)
    )
    raw_p = [
        stream.values(
            tree_kind, lambda p, k, n=name: stream.m(p, k, core.STREAM_ACTUAL, n, rows, cap, tie)
        )
        for name in core.L_PCOAX
    ]
    raw = None
    if raw_b is not None and all(v is not None for v in raw_p):
        raw_means = [mean(list(v.values())) for v in raw_p if v is not None]
        raw = {
            "label": "dominated by popularity cost (ADR-0014 section 7); not a criterion",
            "mean_m_B_over_mean_m_P": float(mean(list(raw_b.values())) / mean(raw_means)),
            "per_partition_ratio": [float(mean(list(raw_b.values())) / r) for r in raw_means],
        }
    holds = bool(aggregate["holds"]) and all(e["clause"] for e in each)
    return {
        **base,
        "status": "NON-DEGENERATE",
        "better": holds,
        "aggregate": aggregate,
        "every_partition": each,
        "spread": spread,
        "raw_misses_descriptive": raw,
        "null_denominators": degenerate,
    }


def part_k(stream: Stream, tree_kind: str, rows: int, cap: int) -> dict[str, Any]:
    """REAL BRANCHES BETTER only if every clause holds under both tie rules; otherwise NOT BETTER
    (with a flag when the two tie rules disagree); DEGENERATE if any denominator is too small."""
    by_tie = {tie: part_one_tie(stream, tree_kind, rows, cap, tie) for tie in core.TIES}
    statuses = {v["status"] for v in by_tie.values()}
    if INCOMPLETE in statuses:
        label = INCOMPLETE
    elif DEGENERATE in statuses:
        label = DEGENERATE
    elif all(v["better"] for v in by_tie.values()):
        label = REAL_BETTER
    else:
        label = NOT_BETTER
    flags = {v.get("better") for v in by_tie.values() if "better" in v}
    return {
        "R": rows,
        "C": cap,
        "label": label,
        "tie_rule_dependent": label == NOT_BETTER and len(flags) == 2,
        "by_tie": by_tie,
    }


# --- the outcome table, stream pairing, decision classes
def outcome_for(
    hb_primary: dict[str, Any], hb_confirm: dict[str, Any], part_primary: str, part_confirm: str
) -> str:
    """The ordered outcome table of section 7 for one tree kind on one stream."""
    primary, confirm = hb_primary["class"], hb_confirm["class"]
    if INCOMPLETE in (primary, confirm, part_primary, part_confirm):
        return INCOMPLETE
    if primary == DEGENERATE:
        return UNRESOLVED
    if primary == TREE_BETTER and confirm == TREE_BETTER:
        if part_primary == REAL_BETTER and part_confirm == REAL_BETTER:
            return HIERARCHY
        return NOT_BRANCH
    if primary == TREE_BETTER:
        return NOT_ROBUST
    if primary == FLAT_BETTER:
        return FLAT_COAX_BETTER
    if primary == WITHIN:
        return WITHIN_FLAT
    asc = hb_primary["by_tie"].get("asc", {})
    rho = asc.get("rho_exact")
    if rho is not None:
        num, den = rho.split("/")
        tree_favouring = Fraction(int(num), int(den)) < 1
    else:
        tree_favouring = False
    return INTERMEDIATE_TREE if tree_favouring else INTERMEDIATE_FLAT


def stream_pairing(label_a: str, label_b: str) -> dict[str, Any]:
    if INCOMPLETE in (label_a, label_b):
        return {"pairing": INCOMPLETE, "description": INCOMPLETE, "A": label_a, "B": label_b}
    if label_a == label_b and label_a != UNRESOLVED:
        description = f"{label_a}, {REPLICATED}"
        pairing = REPLICATED
    elif label_a == label_b:
        description, pairing = UNRESOLVED_BOTH, UNRESOLVED_BOTH
    elif UNRESOLVED in (label_a, label_b):
        other = label_b if label_a == UNRESOLVED else label_a
        description, pairing = f"{other}, {SINGLE_STREAM}", SINGLE_STREAM
    else:
        description = f"{NOT_REPLICATED}: A = {label_a}; B = {label_b}"
        pairing = NOT_REPLICATED
    return {"pairing": pairing, "description": description, "A": label_a, "B": label_b}


def decision_class(label_a: str, label_b: str) -> str:
    """S, U, N or I (section 9); exactly one applies to every pair of outcomes."""
    if INCOMPLETE in (label_a, label_b):
        return INCOMPLETE
    if label_a == HIERARCHY and label_b == HIERARCHY:
        return CLASS_S
    if label_a == UNRESOLVED and label_b == UNRESOLVED:
        return CLASS_U
    if label_a in N_OUTCOMES and label_b in N_OUTCOMES:
        return CLASS_N
    return CLASS_I


def recommendation(class_fixed: str, class_learned: str) -> dict[str, Any]:
    """The ordered recommendation table of section 9."""
    classes = (class_fixed, class_learned)
    if INCOMPLETE in classes:
        return {"row": None, "classes": INCOMPLETE, "recommendation": INCOMPLETE}
    if CLASS_S in classes:
        row = 1
    elif classes == (CLASS_N, CLASS_N):
        row = 2
    elif classes == (CLASS_U, CLASS_U):
        row = 3
    else:
        row = 4
    return {"row": row, **RECOMMENDATIONS[row], "tree_kind_classes": list(classes)}


# --- one stream: criteria
def stream_criteria(stream: Stream) -> dict[str, Any]:
    out: dict[str, Any] = {
        "stream": stream.name,
        "complete": stream.complete,
        "missing": stream.missing,
        "tree_kinds": {},
    }
    for kind in core.TREE_KINDS:
        if not stream.complete:
            out["tree_kinds"][kind] = {
                "HB": INCOMPLETE,
                "PART": INCOMPLETE,
                "outcome": INCOMPLETE,
                "reason": f"{len(stream.missing)} of {len(stream.expected)} checkpoints missing, "
                "failed or incomplete; the full study needs all 27 parent/seed pairs",
            }
            continue
        settings = {}
        for name, (rows, cap) in (
            ("primary", core.PRIMARY_SETTING),
            ("confirmation", core.CONFIRMATION_SETTING),
        ):
            settings[name] = {
                "HB": comparison(stream, kind, rows, cap, core.L_BCOAX, core.L_COAX),
                "HU": comparison(stream, kind, rows, cap, core.L_COAX, core.L_COAX),
                "PART": part_k(stream, kind, rows, cap),
            }
        outcome = outcome_for(
            settings["primary"]["HB"],
            settings["confirmation"]["HB"],
            settings["primary"]["PART"]["label"],
            settings["confirmation"]["PART"]["label"],
        )
        hb_p = settings["primary"]["HB"]
        out["tree_kinds"][kind] = {
            "outcome": outcome,
            "HB": {k: v["HB"]["class"] for k, v in settings.items()},
            "HU": {k: v["HU"]["class"] for k, v in settings.items()},
            "PART": {k: v["PART"]["label"] for k, v in settings.items()},
            "intermediate_direction_basis": (
                "rho under the ascending tie rule in the primary setting"
            )
            if outcome.startswith("INTERMEDIATE")
            else None,
            "primary_rho_ascending": hb_p["by_tie"]["asc"].get("rho"),
            "settings": settings,
        }
    return out


# --- descriptive items
def _ratio_of_means(num: Values | None, den: Values | None) -> float | None:
    if num is None or den is None:
        return None
    d = mean(list(den.values()))
    return None if d == 0 else float(mean(list(num.values())) / d)


def _mean_of_ratios(num: Values | None, den: Values | None) -> float | None:
    if num is None or den is None or any(v == 0 for v in den.values()):
        return None
    return float(mean([num[p] / den[p] for p in num]))


def _vals(
    stream: Stream, kind: str, st: str, layout: str, rows: int, cap: int, tie: str
) -> Values | None:
    return stream.values(kind, lambda p, k: stream.m(p, k, st, layout, rows, cap, tie))


def _nullvals(
    stream: Stream, kind: str, layout: str, rows: int, cap: int, tie: str
) -> Values | None:
    return stream.values(kind, lambda p, k: stream.null_mean(p, k, layout, rows, cap, tie))


def _settings(grid: bool) -> list[tuple[int, int, str]]:
    if grid:
        return [(r, c, "asc") for r in core.RS for c in core.CS]
    return [(r, c, t) for r, c in core.CRITERION_SETTINGS for t in core.TIES]


def co_access_gain(stream: Stream) -> dict[str, Any]:
    """G(L) = m(actual, L) / m(actual, L-FREQ) per architecture: ratio of means and mean of the
    per-checkpoint ratios; the criterion settings under both tie rules, then the full grid
    (ascending). Includes the L-NCOAX control and the five partition layouts."""
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        layouts = [core.L_COAX, core.L_NCOAX, *core.L_PCOAX]
        if core.is_tree(kind):
            layouts += [core.L_BCOAX]
        layouts += [core.L_COAX8, core.L_COAXG]
        if core.is_tree(kind):
            layouts += [core.L_BCOAX8, core.L_BCOAXG, core.L_BFREQ]
        for layout in layouts:
            for rows, cap, tie in _settings(False) + _settings(True):
                num = _vals(stream, kind, core.STREAM_ACTUAL, layout, rows, cap, tie)
                den = _vals(stream, kind, core.STREAM_ACTUAL, core.L_FREQ, rows, cap, tie)
                if num is None or den is None:
                    continue
                table[f"{kind}|{layout}|R{rows}|C{cap}|{tie}"] = {
                    "ratio_of_means": _ratio_of_means(num, den),
                    "mean_of_ratios": _mean_of_ratios(num, den),
                    "cells": len(num),
                }
    return table


def ncoax_control(stream: Stream) -> dict[str, Any]:
    """G(L-NCOAX) must be within 0.97-1.03 for every architecture's mean; the mean of the
    per-checkpoint ratios is tested (both ratios are reported) at the two criterion settings under
    both tie rules. Outside the band every co-access result is flagged."""
    low, high = core.NCOAX_BAND
    rows_out: list[dict[str, Any]] = []
    flagged = False
    incomplete = False
    for kind in core.KINDS:
        for rows, cap, tie in _settings(False):
            num = _vals(stream, kind, core.STREAM_ACTUAL, core.L_NCOAX, rows, cap, tie)
            den = _vals(stream, kind, core.STREAM_ACTUAL, core.L_FREQ, rows, cap, tie)
            if num is None or den is None:
                incomplete = True
                continue
            g = _mean_of_ratios(num, den)
            within = g is not None and low <= g <= high
            flagged = flagged or not within
            rows_out.append(
                {
                    "kind": kind,
                    "R": rows,
                    "C": cap,
                    "tie": tie,
                    "G_mean_of_ratios": g,
                    "G_ratio_of_means": _ratio_of_means(num, den),
                    "within_band": within,
                }
            )
    return {
        "band": [low, high],
        "rows": rows_out,
        "flag_every_coaccess_result": None if incomplete and not flagged else flagged,
        "incomplete": incomplete,
        "rule": "mean over the architecture's checkpoints of the per-checkpoint G; flagged if any "
        "architecture at either criterion setting under either tie rule is outside the band "
        "(PENDING LEAD REVIEW: the text does not name the setting or the mean)",
    }


def popularity_cost(stream: Stream) -> dict[str, Any]:
    """m(null, L) / m(null, L-FREQ): ratio of means and mean of per-checkpoint ratios, for the
    layouts that have null runs (L-COAX, L-BCOAX at every R and C; partitions at the criterion
    settings)."""
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        layouts = [core.L_COAX, *core.L_PCOAX] + ([core.L_BCOAX] if core.is_tree(kind) else [])
        for layout in layouts:
            grid = layout in (core.L_COAX, core.L_BCOAX)
            for rows, cap, tie in _settings(False) + (_settings(True) if grid else []):
                num = _nullvals(stream, kind, layout, rows, cap, tie)
                den = _nullvals(stream, kind, core.L_FREQ, rows, cap, tie)
                if num is None or den is None:
                    continue
                table[f"{kind}|{layout}|R{rows}|C{cap}|{tie}"] = {
                    "ratio_of_means": _ratio_of_means(num, den),
                    "mean_of_ratios": _mean_of_ratios(num, den),
                    "cells": len(num),
                }
    return table


def bc_k(stream: Stream) -> dict[str, Any]:
    """BC_K = m_tree(L-BCOAX) / m_tree(L-COAX), beside the five-partition counterpart
    mean m_P / m_tree(L-COAX). Descriptive; read only together with PART_K."""
    out: dict[str, Any] = {}
    for kind in core.TREE_KINDS:
        for rows, cap, tie in _settings(False):
            coax = _vals(stream, kind, core.STREAM_ACTUAL, core.L_COAX, rows, cap, tie)
            branch = _vals(stream, kind, core.STREAM_ACTUAL, core.L_BCOAX, rows, cap, tie)
            parts = [
                _vals(stream, kind, core.STREAM_ACTUAL, name, rows, cap, tie)
                for name in core.L_PCOAX
            ]
            if coax is None or branch is None or any(p is None for p in parts):
                continue
            mean_p = mean([mean(list(p.values())) for p in parts if p is not None])
            c = mean(list(coax.values()))
            out[f"{kind}|R{rows}|C{cap}|{tie}"] = {
                "BC": float(mean(list(branch.values())) / c) if c else None,
                "five_partition_counterpart": float(mean_p / c) if c else None,
            }
    return out


def flat_partition_layouts(stream: Stream) -> dict[str, Any]:
    """The five partition layouts on flat checkpoints, raw and in exploited-structure terms, each
    against flat L-COAX. Descriptive."""
    out: dict[str, Any] = {}
    for rows, cap, tie in _settings(False):
        base = _vals(stream, FLAT, core.STREAM_ACTUAL, core.L_COAX, rows, cap, tie)
        s_base = exploited(stream, FLAT, core.L_COAX, rows, cap, tie)
        for name in core.L_PCOAX:
            raw = _vals(stream, FLAT, core.STREAM_ACTUAL, name, rows, cap, tie)
            s_part = exploited(stream, FLAT, name, rows, cap, tie)
            if base is None or raw is None:
                continue
            out[f"{name}|R{rows}|C{cap}|{tie}"] = {
                "raw_ratio_vs_flat_coax": _ratio_of_means(raw, base),
                "exploited_ratio_vs_flat_coax": None
                if s_base is None or s_part is None
                else _ratio_of_means(s_part, s_base),
            }
    return out


NOT_RUN_DESCENDING = "not run under the descending rule"
ASC_ONLY_VARIANTS = ("HB_A8", "HB_greedy", "HB_order_shuffled")


def robustness_grid(stream: Stream) -> dict[str, Any]:
    """Every R x C with its non-degeneracy status, class, rho and rho_adj for HB_K and HU_K, the
    A8 and greedy-only variants and the order-shuffled stream. The criterion settings carry both
    tie rules; every other cell the ascending rule only (section 11). Never substitutable for a
    criterion."""
    out: dict[str, Any] = {}
    variants = {
        "HB": (core.L_BCOAX, core.L_COAX, core.STREAM_ACTUAL),
        "HU": (core.L_COAX, core.L_COAX, core.STREAM_ACTUAL),
        "HB_A8": (core.L_BCOAX8, core.L_COAX8, core.STREAM_ACTUAL),
        "HB_greedy": (core.L_BCOAXG, core.L_COAXG, core.STREAM_ACTUAL),
        "HB_order_shuffled": (core.L_BCOAX, core.L_COAX, core.STREAM_ORDER),
    }
    for kind in core.TREE_KINDS:
        rows_out = []
        for rows in core.RS:
            for cap in core.CS:
                row: dict[str, Any] = {
                    "R": rows,
                    "C": cap,
                    "cached_rows": rows * cap,
                    "row_size": core.ROW_SIZE_LABEL[rows],
                }
                for name, (tl, fl_, num) in variants.items():
                    # Descending runs exist only for criterion layouts on the actual stream; the
                    # A8, greedy-only and order-shuffled variants are ascending-rule only.
                    asc_only = name in ASC_ONLY_VARIANTS
                    result = comparison(
                        stream, kind, rows, cap, tl, fl_, num, ties=("asc",) if asc_only else None
                    )
                    asc = result["by_tie"]["asc"]
                    row[name] = {
                        "class": result["class"],
                        "status": asc["status"],
                        "rho": asc.get("rho"),
                        "rho_adj": asc.get("rho_adj"),
                        "cells_tree_lower": asc.get("counts_favour_tree", {}).get(
                            "cells_strictly_lower"
                        ),
                        "parents_tree_lower": asc.get("counts_favour_tree", {}).get(
                            "parents_strictly_lower"
                        ),
                    }
                    if asc_only and (rows, cap) in core.CRITERION_SETTINGS:
                        row[name]["descending_rule"] = NOT_RUN_DESCENDING
                rows_out.append(row)
        out[kind] = rows_out
    out["note"] = (
        "order-shuffled numerators use the same L-FREQ null denominators; sensitivity variants "
        "run the ascending rule only except at the criterion settings"
    )
    return out


def utilization(stream: Stream) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for kind in core.KINDS:
        cells = [stream.rec(p, kind) for p in stream.pairs]
        done = [c for c in cells if c is not None]
        if not done:
            continue
        ev = [c["record"]["evaluation_counts"] for c in done]
        out[kind] = {
            "cells": len(done),
            "mean_unique_selected_slots": sum(e["unique_selected_slots"] for e in ev) / len(ev),
            "mean_entropy_nats": sum(e["entropy_nats"] for e in ev) / len(ev),
            "mean_effective_slots": sum(e["effective_slots"] for e in ev) / len(ev),
        }
    return out


def pages_and_misses(stream: Stream) -> dict[str, Any]:
    """Distinct pages per query (mean and histogram), warm capacity misses, first-touch and cold
    misses, uncached and cached read amplification, and per-context quantiles (mean across
    checkpoints), actual stream, ascending rule, for every layout at every R and C."""
    table: dict[str, Any] = {}
    for kind in core.KINDS:
        done = [(p, r) for p in stream.pairs if (r := stream.rec(p, kind)) is not None]
        if not done:
            continue
        queries = [int(r["record"]["queries"]) for _, r in done]
        for layout in core.all_layouts(kind):
            for rows in core.RS:
                groups: list[dict[str, Any]] = []
                for p, _ in done:
                    group = stream.group(p, kind, core.STREAM_ACTUAL, layout, rows)
                    if group is None:
                        break
                    groups.append(group)
                if len(groups) != len(done):
                    continue
                pages = [
                    Fraction(g["stats"]["pages_sum"], q)
                    for g, q in zip(groups, queries, strict=True)
                ]
                hist = [
                    sum(g["stats"]["hist"][i] / q for g, q in zip(groups, queries, strict=True))
                    / len(done)
                    for i in range(core.TOP)
                ]
                entry: dict[str, Any] = {
                    "cells": len(done),
                    "row_size": core.ROW_SIZE_LABEL[rows],
                    "mean_distinct_pages_per_query": float(mean(pages)),
                    "distinct_pages_histogram_fraction_1_to_8": hist,
                    "uncached_read_amplification": float(mean(pages) * rows / core.TOP),
                    "by_c": {},
                }
                for cap in core.CS:
                    cold, first, amp_all, amp_cap, cap_m = [], [], [], [], []
                    quant: list[list[int]] = []
                    for (p, _), q in zip(done, queries, strict=True):
                        e = stream.counts(p, kind, core.STREAM_ACTUAL, layout, rows, cap, "asc")
                        if e is None:
                            break
                        counted = q - q // 2
                        cold.append(Fraction(e["misses_all"], q))
                        first.append(Fraction(e["first_touch_all"], q))
                        amp_all.append(Fraction(e["misses_warm"] * rows, counted * core.TOP))
                        amp_cap.append(
                            Fraction(
                                (e["misses_warm"] - e["first_touch_warm"]) * rows,
                                counted * core.TOP,
                            )
                        )
                        cap_m.append(Fraction(e["misses_warm"] - e["first_touch_warm"], counted))
                        quant.append(e["ctx_q"])
                    else:
                        entry["by_c"][str(cap)] = {
                            "warm_capacity_misses_per_query": float(mean(cap_m)),
                            "cold_misses_per_query_whole_stream": float(mean(cold)),
                            "first_touch_misses_per_query_whole_stream": float(mean(first)),
                            "cached_amplification_all_warm_misses": float(mean(amp_all)),
                            "cached_amplification_warm_capacity_misses": float(mean(amp_cap)),
                            "per_context_capacity_misses_quantiles_mean_over_checkpoints": [
                                sum(v[i] for v in quant) / len(quant) for i in range(len(quant[0]))
                            ],
                            "quantile_levels": [0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0],
                        }
                table[f"{kind}|{layout}|R{rows}"] = entry
    return table


def decomposition(stream: Stream) -> dict[str, Any]:
    """E and its decomposition per checkpoint at the criterion settings and under both tie rules:
    null under L-FREQ -> null under layout L (the popularity cost of the layout) -> actual under L
    (the structure the layout exploits)."""
    out: dict[str, Any] = {}
    for pair, kind in stream.expected:
        layouts = [core.L_COAX, *core.L_PCOAX] + ([core.L_BCOAX] if core.is_tree(kind) else [])
        for rows, cap in core.CRITERION_SETTINGS:
            for tie in core.TIES:
                base = stream.null_mean(pair, kind, core.L_FREQ, rows, cap, tie)
                if base is None or base == 0:
                    continue
                for layout in layouts:
                    null_l = stream.null_mean(pair, kind, layout, rows, cap, tie)
                    actual = stream.m(pair, kind, core.STREAM_ACTUAL, layout, rows, cap, tie)
                    if null_l is None or actual is None or null_l == 0:
                        continue
                    key = f"{core.cell_label(pair, kind)}|{layout}|R{rows}|C{cap}|{tie}"
                    out[key] = {
                        "null_L_FREQ": float(base),
                        "null_layout": float(null_l),
                        "actual_layout": float(actual),
                        "popularity_cost": float(null_l / base),
                        "exploited_structure": float(actual / null_l),
                        "E": float(actual / base),
                    }
    return out


def stream_descriptive(stream: Stream) -> dict[str, Any]:
    return {
        "utilization": utilization(stream),
        "co_access_gain": co_access_gain(stream),
        "ncoax_control": ncoax_control(stream),
        "BC_K": bc_k(stream),
        "popularity_cost": popularity_cost(stream),
        "E_decomposition_per_checkpoint": decomposition(stream),
        "flat_partition_layouts": flat_partition_layouts(stream),
        "robustness_grid": robustness_grid(stream),
        "pages_and_misses": pages_and_misses(stream),
    }


# --- quality, calibration transfer, split-half (inputs from P5 and the layout stage)
def quality_vs_misses(stream: Stream, nll: dict[str, float] | None) -> dict[str, Any]:
    """Each checkpoint's unchanged P5 NLL beside m and E at the criterion settings, and the paired
    tree-minus-flat NLL difference. 'Equivalent quality' is what P5 registered and found: both
    trees within 0.005 nats/byte of flat in 26 of 27 cells (both the signed and the absolute
    reading are counted)."""
    if nll is None:
        return {"available": False, "reason": "no P5 NLL supplied"}
    out: dict[str, Any] = {"available": True, "per_kind": {}, "paired_tree_minus_flat": {}}
    for kind in core.KINDS:
        values = [
            nll[core.cell_label(p, kind)] for p in stream.pairs if core.cell_label(p, kind) in nll
        ]
        if values:
            out["per_kind"][kind] = {"cells": len(values), "mean_nll": sum(values) / len(values)}
    for kind in core.TREE_KINDS:
        diffs = [
            nll[core.cell_label(p, kind)] - nll[core.cell_label(p, FLAT)]
            for p in stream.pairs
            if core.cell_label(p, kind) in nll and core.cell_label(p, FLAT) in nll
        ]
        if diffs:
            out["paired_tree_minus_flat"][kind] = {
                "cells": len(diffs),
                "mean_difference_nats_per_byte": sum(diffs) / len(diffs),
                "cells_tree_not_worse_by_more_than_0.005": sum(1 for d in diffs if d <= 0.005),
                "cells_absolute_difference_within_0.005": sum(1 for d in diffs if abs(d) <= 0.005),
                "registered_p5_finding": (
                    "both trees within 0.005 nats/byte of flat in 26 of 27 cells"
                ),
            }
    misses: dict[str, Any] = {}
    for rows, cap in core.CRITERION_SETTINGS:
        for kind in core.KINDS:
            for layout in (core.L_FREQ, core.L_COAX, *(() if kind == FLAT else (core.L_BCOAX,))):
                num, den, e = e_values(stream, kind, layout, rows, cap, "asc", core.STREAM_ACTUAL)
                if num is None or den is None:
                    continue
                misses[f"{kind}|{layout}|R{rows}|C{cap}"] = {
                    "mean_m": float(mean(list(num.values()))),
                    "mean_E": None if e is None else float(mean(list(e.values()))),
                    "mean_nll": out["per_kind"].get(kind, {}).get("mean_nll"),
                }
    out["misses_beside_quality"] = misses
    return out


def calibration_transfer(
    stream: Stream, layout_records: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """m on the calibration stream (layout stage) against m on this evaluation stream, per layout,
    architecture, R and C (ascending rule): ratio of means."""
    out: dict[str, Any] = {}
    for kind in core.KINDS:
        for layout in core.all_layouts(kind):
            for rows in core.RS:
                for cap in core.CS:
                    cal: list[Fraction] = []
                    ev: list[Fraction] = []
                    for p in stream.pairs:
                        label = core.cell_label(p, kind)
                        rec = layout_records.get(label)
                        group = (
                            None
                            if rec is None
                            else rec.get("calibration_transfer", {}).get(
                                core.layout_key(layout, rows)
                            )
                        )
                        e = stream.counts(p, kind, core.STREAM_ACTUAL, layout, rows, cap, "asc")
                        if group is None or e is None:
                            continue
                        c = group["by_c"].get(str(cap), {}).get("asc")
                        if c is None:
                            continue
                        cal.append(Fraction(c["misses_warm"] - c["first_touch_warm"], 16384))
                        ev.append(
                            Fraction(
                                e["misses_warm"] - e["first_touch_warm"], stream.counted(p, kind)
                            )
                        )
                    if cal:
                        d = mean(ev)
                        out[f"{kind}|{layout}|R{rows}|C{cap}"] = {
                            "cells": len(cal),
                            "mean_m_calibration": float(mean(cal)),
                            "mean_m_evaluation": float(d),
                            "evaluation_over_calibration": float(d / mean(cal))
                            if mean(cal)
                            else None,
                        }
    return out


def split_half(layout_records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Split-half stability (calibration only, from the layout stage): each criterion layout fitted
    on each half of the calibration contexts and scored on the other half, per architecture
    (means over checkpoints) and the relative difference between the two directions per
    checkpoint."""
    out: dict[str, Any] = {}
    for kind in core.KINDS:
        recs = [
            r
            for lb, r in layout_records.items()
            if core.parse_label(lb)[1] == kind and "split_half" in r
        ]
        if not recs:
            continue
        keys = sorted(recs[0]["split_half"])
        for key in keys:
            fits = [r["split_half"][key] for r in recs if key in r["split_half"]]
            m01 = [f["fit_half_0_score_half_1"] for f in fits]
            m10 = [f["fit_half_1_score_half_0"] for f in fits]
            rel = [abs(a - b) / ((a + b) / 2) for a, b in zip(m01, m10, strict=True) if a + b > 0]
            out[f"{kind}|{key}"] = {
                "cells": len(fits),
                "mean_m_fit0_score1": sum(m01) / len(m01),
                "mean_m_fit1_score0": sum(m10) / len(m10),
                "mean_relative_difference_between_directions": sum(rel) / len(rel) if rel else None,
                "max_relative_difference_between_directions": max(rel) if rel else None,
            }
    return out


# --- top level
def analyze_streams(
    streams: dict[str, dict[str, dict[str, Any]]],
    *,
    expected: list[tuple[Pair, str]] | None = None,
    nll: dict[str, float] | None = None,
    layout_records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Both streams analysed together, once. ``streams`` maps ``"A"`` and ``"B"`` to the
    per-checkpoint simulation worker results."""
    data = {name: Stream(name, streams.get(name, {}), expected) for name in core.STREAMS_EVAL}
    per_stream = {name: stream_criteria(s) for name, s in data.items()}
    combined: dict[str, Any] = {"tree_kinds": {}}
    classes: dict[str, str] = {}
    for kind in core.TREE_KINDS:
        a = per_stream["A"]["tree_kinds"][kind]["outcome"]
        b = per_stream["B"]["tree_kinds"][kind]["outcome"]
        classes[kind] = decision_class(a, b)
        combined["tree_kinds"][kind] = {
            "outcome_A": a,
            "outcome_B": b,
            "pairing": stream_pairing(a, b),
            "decision_class": classes[kind],
        }
    combined["recommendation"] = recommendation(
        classes[core.TREE_KINDS[0]], classes[core.TREE_KINDS[1]]
    )
    layout_records = layout_records or {}
    descriptive = {}
    for name, s in data.items():
        entry = stream_descriptive(s)
        entry["quality_vs_misses"] = quality_vs_misses(s, nll)
        entry["calibration_transfer"] = calibration_transfer(s, layout_records)
        descriptive[name] = entry
    ncoax_flags = {
        n: d["ncoax_control"]["flag_every_coaccess_result"] for n, d in descriptive.items()
    }
    return {
        "schema": core.SCHEMA_ANALYSIS,
        "study": core.STUDY,
        "spec_reference": core.SPEC,
        "label": "implementation self-check output; not Astra validation; not human approval",
        "quantity_labels": {
            "miss and page counts": "measured: simulated under a page model on recorded traces",
            "E, rho, rho_adj, S, G, BC, popularity cost": "derived from the measured counts",
            "R = 1, 2, 8": "HYPOTHETICAL row sizes (relabelled bytes per row)",
            "R = 32, 128, 512": "ArborLM's actual 128-byte value rows at 4, 16 and 64 KiB pages; "
            "still simulated counts",
            "not measured and not claimable": "device latency, physical I/O, throughput, hardware "
            "speed, SSD viability",
        },
        "checkpoints_expected": len(data["A"].expected),
        "streams": {
            n: {
                "checkpoints_complete": len(s.expected) - len(s.missing),
                "missing_or_failed": s.missing,
                "status": "COMPLETE" if s.complete else INCOMPLETE,
            }
            for n, s in data.items()
        },
        "per_stream": per_stream,
        "combined": combined,
        "ncoax_control_flagged": ncoax_flags,
        "split_half_stability": split_half(layout_records),
        "descriptive": descriptive,
    }
