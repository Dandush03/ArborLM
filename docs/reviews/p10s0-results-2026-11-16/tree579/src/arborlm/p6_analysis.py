"""P6-E decision arithmetic (ADR-0011 sections 3.3, 3.4, 3.6), computed from raw records.

Pure Python over JSON-compatible records: no torch, no implementation imports. Medians and the
reliability rule are recomputed from the raw nanosecond samples, never read back from the
summaries the workers wrote. Every clause is reported separately. A criterion whose inputs are
incomplete is INCOMPLETE and one whose inputs are unreliable is INCONCLUSIVE; neither is ever a
PASS or FAIL.

Status: SPEC: HUMAN-APPROVED (ADR-0011); implementation self-checked only.
"""

import math
import statistics
from collections.abc import Sequence
from typing import Any

from .p2_config import BACKBONES, ORDERS
from .p5_config import SEEDS

ROUNDS, WARMUPS, CALLS = 8, 2, 10
LOOKUP, ADDITION, FORWARD = "lookup_score_select", "addition_forward", "model_forward"
FLAT, FIXED, LEARNED = "flat", "fixed_tree", "learned_tree"
TREE_KINDS = (FIXED, LEARNED)
PAIRS = [(b, o, s) for b in BACKBONES for o in ORDERS for s in SEEDS]
PRIMARY = "W8"
CLASS_OK = ("STRICT", "BOUNDED")

# ADR-0011 section 3.6. Margins and counts are the registered numbers; none is tunable.
SP = {"gm": 0.50, "cells": 26, "parents": 9}
PAR_ADDITION = {"gm": 1.00, "cells": 22, "parents": 8}
PAR_FORWARD = {"gm": 1.05, "cells": 22, "parents": 8}
PR_ADDITION = {"gm": 0.80, "cells": 22, "parents": 8}
PR_FORWARD = PAR_FORWARD


def entity(kind: str, variant: str) -> str:
    return f"{kind}:{variant}"


# ---------------------------------------------------------------------------------------------
# Raw timing records
# ---------------------------------------------------------------------------------------------
def summarize_rounds(
    rounds: list[list[int]], resolution_ns: float, *, expected_rounds: int = ROUNDS
) -> dict[str, Any]:
    """Same statistics and reliability rule as ``p5_timing.summarize`` (ADR-0010 section 7)."""
    if len(rounds) != expected_rounds or any(len(row) != CALLS for row in rounds):
        raise ValueError("wrong P6 timing repetition count")
    durations = [value for row in rounds for value in row]
    if not math.isfinite(resolution_ns) or resolution_ns <= 0:
        raise ValueError("invalid timing resolution")
    medians = [statistics.median(row) for row in rounds]
    ratio = max(medians) / min(medians) if min(medians) > 0 else None
    median = statistics.median(durations)
    ordered = sorted(durations)
    criteria = {
        "positive_durations": min(durations) > 0,
        "above_clock_resolution": median >= 100 * resolution_ns,
        "stable_rounds": ratio is not None and ratio <= 1.25,
    }
    return {
        "durations_ns": durations,
        "round_medians_ns": medians,
        # ``median_ns`` (mean of the 40th and 41st of 80 samples) is the registered statistic that
        # every ratio uses, as in P5. ``p50_ns`` is the nearest-rank p50 (the 40th sample),
        # reported alongside as section 3.4 lists it, and is never used in a ratio.
        "median_ns": median,
        **{
            f"p{int(p * 100)}_ns": ordered[math.ceil(len(ordered) * p) - 1]
            for p in (0.1, 0.5, 0.9, 0.95)
        },
        "min_ns": min(durations),
        "max_ns": max(durations),
        "round_median_ratio": ratio,
        "resolution_ns": resolution_ns,
        "reliability_criteria": criteria,
        "usable": all(criteria.values()),
    }


def recompute(record: dict[str, Any], *, expected_rounds: int = ROUNDS) -> dict[str, Any]:
    """Recompute a measurement summary from its raw samples (rows of CALLS per round)."""
    samples = record["durations_ns"]
    rows = [samples[i : i + CALLS] for i in range(0, len(samples), CALLS)]
    return summarize_rounds(rows, record["resolution_ns"], expected_rounds=expected_rounds)


def index_workers(
    workers: Sequence[dict[str, Any]], *, expected_rounds: int = ROUNDS
) -> dict[tuple[int, int, int], dict[tuple[str, str, str], dict[str, Any]]]:
    """pair -> (workload, scope, entity) -> recomputed summary."""
    indexed: dict[tuple[int, int, int], dict[tuple[str, str, str], dict[str, Any]]] = {}
    for worker in workers:
        pair = (worker["pair"][0], worker["pair"][1], worker["pair"][2])
        if pair in indexed:
            raise ValueError("duplicate worker pair")
        rows = {}
        for record in worker["timing"]["records"]:
            rows[record["workload"], record["scope"], record["entity"]] = recompute(
                record, expected_rounds=int(worker.get("rounds", expected_rounds))
            )
        indexed[pair] = rows
    return indexed


def geometric_mean(values: Sequence[float]) -> float:
    return statistics.geometric_mean(values)


def parent_groups(rows: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [
        [r for r in rows if (r["backbone"], r["order"]) == (b, o)]
        for b in BACKBONES
        for o in ORDERS
    ]


def ratio_rows(
    indexed: dict[tuple[int, int, int], dict[tuple[str, str, str], dict[str, Any]]],
    numerator: str,
    denominator: str,
    workload: str,
    scope: str,
) -> list[dict[str, Any]]:
    """Per-pair median ratio numerator/denominator, with the reliability of both measurements."""
    rows = []
    for pair in sorted(indexed):
        measurements = indexed[pair]
        top = measurements.get((workload, scope, numerator))
        bottom = measurements.get((workload, scope, denominator))
        if top is None or bottom is None:
            continue
        ratio = top["median_ns"] / bottom["median_ns"] if bottom["median_ns"] > 0 else None
        rows.append(
            {
                "backbone": pair[0],
                "order": pair[1],
                "seed": pair[2],
                "ratio": ratio,
                "usable": bool(top["usable"] and bottom["usable"]) and ratio is not None,
            }
        )
    return rows


# ---------------------------------------------------------------------------------------------
# Clause evaluation (each clause reported separately)
# ---------------------------------------------------------------------------------------------
def _clause_group(
    rows: list[dict[str, Any]],
    margins: dict[str, float],
    strict_cells: bool,
    strict_parents: bool | None = None,
) -> dict[str, Any]:
    """gm <= margin; at least ``cells`` pair ratios below/at 1 (or margin); parent GMs likewise.

    ``strict_cells``: pair ratios must be < the comparison point (else <=). The comparison point
    is 1.0 for the addition clauses and the margin for the model-forward clauses, exactly as in
    P5's L clauses (ratio < 1 for addition, <= 1.05 for model_forward).
    """
    strict_parents = strict_cells if strict_parents is None else strict_parents
    point = margins.get("point", 1.0)
    usable = [r for r in rows if r["usable"]]
    reliable = len(usable) == len(rows) and len(rows) > 0
    values = [r["ratio"] for r in rows if r["ratio"] is not None]
    gm = geometric_mean(values) if len(values) == len(rows) and values else None

    def below(value: float, strict: bool) -> bool:
        return value < point if strict else value <= point

    parents = []
    for group in parent_groups(rows):
        ratios = [r["ratio"] for r in group if r["ratio"] is not None]
        parents.append(
            {
                "backbone": group[0]["backbone"] if group else None,
                "order": group[0]["order"] if group else None,
                "geometric_mean": geometric_mean(ratios)
                if ratios and len(ratios) == len(group)
                else None,
            }
        )
    cell_count = sum(r["ratio"] is not None and below(r["ratio"], strict_cells) for r in rows)
    parent_count = sum(
        p["geometric_mean"] is not None and below(p["geometric_mean"], strict_parents)
        for p in parents
    )
    return {
        "pairs": len(rows),
        "geometric_mean": {
            "value": gm,
            "limit": margins["gm"],
            "comparison": "<=",
            "pass": gm is not None and gm <= margins["gm"],
        },
        "cells": {
            "count": cell_count,
            "required": margins["cells"],
            "of": len(rows),
            "comparison": f"{'<' if strict_cells else '<='} {point}",
            "pass": cell_count >= margins["cells"],
        },
        "parents": {
            "count": parent_count,
            "required": margins["parents"],
            "of": len(parents),
            "comparison": f"{'<' if strict_parents else '<='} {point}",
            "pass": parent_count >= margins["parents"],
            "parent_geometric_means": parents,
        },
        "reliable": reliable,
        "ratios": rows,
    }


def _passes(group: dict[str, Any]) -> bool:
    return bool(
        group["geometric_mean"]["pass"] and group["cells"]["pass"] and group["parents"]["pass"]
    )


def _status(groups: list[dict[str, Any]], expected_pairs: int) -> str:
    if any(g["pairs"] != expected_pairs for g in groups):
        return "INCOMPLETE"
    if not all(g["reliable"] for g in groups):
        return "INCONCLUSIVE"
    return "PASS" if all(_passes(g) for g in groups) else "FAIL"


def speedup_criterion(
    indexed: dict[Any, Any], variant: str, original: str, *, expected_pairs: int = 27
) -> dict[str, Any]:
    """SP(K): variant against the original implementation at W8 addition_forward."""
    rows = ratio_rows(indexed, variant, original, PRIMARY, ADDITION)
    group = _clause_group(rows, SP, strict_cells=True)
    return {"status": _status([group], expected_pairs), "addition_forward": group}


def comparator_criteria(
    indexed: dict[Any, Any], variant: str, comparator: str, *, expected_pairs: int = 27
) -> dict[str, dict[str, Any]]:
    """PAR(K) and PR(K) against a flat comparator at W8 (addition and model scopes)."""
    add = ratio_rows(indexed, variant, comparator, PRIMARY, ADDITION)
    forward = ratio_rows(indexed, variant, comparator, PRIMARY, FORWARD)
    par_add = _clause_group(add, {**PAR_ADDITION}, strict_cells=False)
    par_fwd = _clause_group(
        forward, {**PAR_FORWARD, "point": PAR_FORWARD["gm"]}, strict_cells=False
    )
    pr_add = _clause_group(add, {**PR_ADDITION}, strict_cells=True)
    pr_fwd = _clause_group(forward, {**PR_FORWARD, "point": PR_FORWARD["gm"]}, strict_cells=False)
    return {
        "PAR": {
            "status": _status([par_add, par_fwd], expected_pairs),
            "addition_forward": par_add,
            "model_forward": par_fwd,
        },
        "PR": {
            "status": _status([pr_add, pr_fwd], expected_pairs),
            "addition_forward": pr_add,
            "model_forward": pr_fwd,
        },
    }


# ---------------------------------------------------------------------------------------------
# Equivalence gate from records
# ---------------------------------------------------------------------------------------------
def eligibility_from_gate(gated: dict[str, Any]) -> dict[str, Any]:
    flat = ["F0", *[v for v in ("F1", "F2") if gated.get(v, {}).get("EQ")]]
    tree = [v for v in ("T1", "T2", "T3", "T4", "T5") if gated.get(v, {}).get("EQ")]
    return {
        "flat_variants": flat,
        "tree_variants": ["T0", *tree],
        "timing_stage_runs": bool(tree),
        "reason": None
        if tree
        else "no tree variant passed EQ: P6-E ends with the equivalence result",
    }


# ---------------------------------------------------------------------------------------------
# Selection rules (ADR-0011 sections 3.2 and 3.4)
# ---------------------------------------------------------------------------------------------
def select_variants(
    screen_workers: Sequence[dict[str, Any]], eligibility: dict[str, Any]
) -> dict[str, Any]:
    """Apply the fixed T-screen rules to the screening records.

    Tree kind K: the EQ-passing T-variant (T0 is the baseline, not a candidate) with the lowest
    W8 addition_forward geometric-mean ratio to T0. Flat comparator: the EQ-passing flat variant
    (F0, F1, F2) with the lowest median across workers of the per-worker W8 addition_forward
    median. Ties go to the lowest variant ID.
    """
    indexed = index_workers(screen_workers)
    selected: dict[str, Any] = {}
    candidates = [v for v in eligibility["tree_variants"] if v != "T0"]
    for kind in TREE_KINDS:
        table = {}
        for variant in candidates:
            rows = ratio_rows(indexed, entity(kind, variant), entity(kind, "T0"), PRIMARY, ADDITION)
            values = [r["ratio"] for r in rows]
            table[variant] = {
                "pairs": len(rows),
                "geometric_mean_ratio_to_T0": geometric_mean(values)
                if values and None not in values
                else None,
                "all_usable": all(r["usable"] for r in rows),
            }
        ranked = sorted(
            (v for v, t in table.items() if t["geometric_mean_ratio_to_T0"] is not None),
            key=lambda v: (table[v]["geometric_mean_ratio_to_T0"], v),
        )
        selected[kind] = {"selected": ranked[0] if ranked else None, "table": table}
    flat_table = {}
    for variant in eligibility["flat_variants"]:
        medians = [
            m[PRIMARY, ADDITION, entity(FLAT, variant)]["median_ns"]
            for m in indexed.values()
            if (PRIMARY, ADDITION, entity(FLAT, variant)) in m
        ]
        flat_table[variant] = {
            "workers": len(medians),
            "median_of_worker_medians_ns": statistics.median(medians) if medians else None,
        }
    ranked_flat = sorted(
        (v for v, t in flat_table.items() if t["median_of_worker_medians_ns"] is not None),
        key=lambda v: (flat_table[v]["median_of_worker_medians_ns"], v),
    )
    return {
        "rule": "tree: lowest W8 addition_forward geometric-mean ratio to T0 among EQ-passing "
        "T1-T5; flat comparator: lowest median-of-worker-medians W8 addition_forward among "
        "EQ-passing F0/F1/F2; ties to the lowest variant ID",
        "tree": selected,
        "flat": {"comparator": ranked_flat[0] if ranked_flat else None, "table": flat_table},
        "workers": len(indexed),
    }


def confirm_entities(selection: dict[str, Any]) -> dict[str, list[str]]:
    """T-confirm entities per kind: T0 and the selected variant; F0 and the flat comparator."""
    flat = ["F0"]
    if selection["flat"]["comparator"] not in (None, "F0"):
        flat.append(selection["flat"]["comparator"])
    plan = {FLAT: flat}
    for kind in TREE_KINDS:
        chosen = selection["tree"][kind]["selected"]
        if chosen is None:
            raise ValueError("no selected tree variant")
        plan[kind] = ["T0", chosen]
    return plan


# ---------------------------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------------------------
def descriptive_tables(
    workers: Sequence[dict[str, Any]], plan: dict[str, list[str]]
) -> dict[str, Any]:
    """Geometric-mean median ratios against the reference (T0 / F0) for every variant, scope,
    workload present. Reported for completeness; no criterion is read from these."""
    indexed = index_workers(workers)
    out: dict[str, Any] = {}
    for kind, variants in plan.items():
        reference = entity(kind, "F0" if kind == FLAT else "T0")
        for variant in variants:
            if entity(kind, variant) == reference:
                continue
            for workload in ("W8", "W1", "Wtok"):
                for scope in (LOOKUP, ADDITION, FORWARD):
                    rows = ratio_rows(indexed, entity(kind, variant), reference, workload, scope)
                    if not rows:
                        continue
                    values = [r["ratio"] for r in rows if r["ratio"] is not None]
                    out[f"{kind}:{variant}/{workload}/{scope}"] = {
                        "pairs": len(rows),
                        "geometric_mean_ratio_to_reference": geometric_mean(values)
                        if len(values) == len(rows)
                        else None,
                        "all_usable": all(r["usable"] for r in rows),
                    }
    return out


def analyze(
    gated: dict[str, Any],
    selection: dict[str, Any] | None,
    confirm_workers: Sequence[dict[str, Any]],
    *,
    expected_pairs: int = 27,
) -> dict[str, Any]:
    """Every registered P6-E criterion, each clause reported separately."""
    eligibility = eligibility_from_gate(gated)
    result: dict[str, Any] = {
        "equivalence": {
            v: {"EQ": g["EQ"], "complete": g["complete"], "counts": g["counts"]}
            for v, g in gated.items()
        },
        "eligibility": eligibility,
        "selection": selection,
        "complete": len(confirm_workers) == expected_pairs,
        "pairs": len(confirm_workers),
        "criteria": {},
    }
    result["hypotheses"] = {
        "E-H1": {
            "statement": "T1 and T2 STRICT on every checkpoint",
            "holds": all(
                gated.get(v, {}).get("complete")
                and gated[v]["counts"]["STRICT"] == gated[v]["checkpoints"]
                for v in ("T1", "T2")
            ),
        },
        "E-H2": {
            "statement": "T3, T4, T5 and F2 at least BOUNDED",
            "holds": all(gated.get(v, {}).get("EQ") for v in ("T3", "T4", "T5", "F2")),
        },
    }
    if selection is None or not confirm_workers:
        not_evaluated = {
            "holds": None,
            "status": "NOT_EVALUATED",
            "reason": "no T-confirm records: timing did not run (no EQ-passing tree variant) or "
            "has not completed",
        }
        result["hypotheses"]["E-H3"] = dict(not_evaluated)
        result["hypotheses"]["E-H4"] = dict(not_evaluated)
        return result
    indexed = index_workers(confirm_workers)
    comparator = selection["flat"]["comparator"]
    verdicts: dict[str, dict[str, str]] = {}
    for kind in TREE_KINDS:
        variant = selection["tree"][kind]["selected"]
        name = entity(kind, variant)
        sp = speedup_criterion(indexed, name, entity(kind, "T0"), expected_pairs=expected_pairs)
        versus = comparator_criteria(
            indexed, name, entity(FLAT, comparator), expected_pairs=expected_pairs
        )
        weaker = comparator_criteria(
            indexed, name, entity(FLAT, "F0"), expected_pairs=expected_pairs
        )
        result["criteria"][kind] = {
            "variant": variant,
            "EQ": bool(gated.get(variant, {}).get("EQ")),
            "flat_comparator": comparator,
            "SP": sp,
            "PAR": versus["PAR"],
            "PR": versus["PR"],
            "versus_F0_weaker_comparison": {"PAR": weaker["PAR"], "PR": weaker["PR"]},
        }
        verdicts[kind] = {
            "SP": sp["status"],
            "PAR": versus["PAR"]["status"],
            "PR": versus["PR"]["status"],
        }

    def hypothesis(name: str) -> dict[str, Any]:
        """ "At least one equivalent tree variant reaches the criterion": a kind counts only if
        its selected variant passed EQ. True if any kind passes; None if none passes but some
        verdict is INCOMPLETE or INCONCLUSIVE; otherwise False."""
        statuses = {k: verdicts[k][name] for k in TREE_KINDS}
        passing = [k for k in TREE_KINDS if result["criteria"][k]["EQ"] and statuses[k] == "PASS"]
        undecided = any(s in ("INCOMPLETE", "INCONCLUSIVE") for s in statuses.values())
        return {
            "per_kind": statuses,
            "kinds_passing_with_EQ": passing,
            "holds_for_any_kind": bool(passing),
            "holds_for_both_kinds": len(passing) == len(TREE_KINDS),
            "holds": True if passing else (None if undecided else False),
        }

    result["hypotheses"]["E-H3"] = hypothesis("SP")
    result["hypotheses"]["E-H4"] = hypothesis("PR")
    result["verdicts"] = verdicts
    result["note"] = (
        "A PR pass does not change P5's L or composite outcome. Analytical work counts and "
        "measured latencies are different quantities; nothing here is a quality claim."
    )
    return result


def pair_complete(workers: Sequence[dict[str, Any]]) -> bool:
    return {tuple(w["pair"]) for w in workers} == set(PAIRS)


__all__ = [
    "ADDITION",
    "FORWARD",
    "LOOKUP",
    "analyze",
    "comparator_criteria",
    "confirm_entities",
    "recompute",
    "select_variants",
    "speedup_criterion",
    "summarize_rounds",
]
