# ruff: noqa: E501
"""P9 Lane C analysis (package I6): the Lane C gate, locality classes, the hierarchy rule, and the
synthetic-trace classes.

Specification: ADR-0017 section 3 (Lane C gate: the 4K -> 16K capacity step supported for the
architecture concerned, and its B1 cell with alpha_u = 0.25, alpha_c = 0 UTILIZATION_PRESERVED or
IMPROVED against its dose-zero 16K cell; otherwise H17-LOC NOT EVALUATED, descriptive only), 8.4
(locality classes over all four primary settings, both tie rules, both seeds, both panels; first match
wins; hierarchy advantage), 9 (synthetic part and the D09 sweep).

Inputs: ``core.EvalIndex`` for quality and utilization, and the ``core.SimRecord`` lists written by
``sim.simulate_cell`` for locality. Comparison: E of the case against E of the reference, each under
its own optimized co-access layout fitted on its calibration stream (layout key ``coaccess@R``);
identity, frequency, random-partition and branch-constrained layouts and the oracle bound are reported
as controls and enter no class. References: locality reference = the dose-zero flat 16K cell;
utilization reference of a locality cell = the cell with alpha_u = 0.25, alpha_c = 0 of the same
architecture. Pages per query and cross-query reuse are reported separately for every locality cell.
All simulation numbers are SIMULATED value-page misses of a model, never physical I/O.

Rules are applied per seed (settings x tie rules inside a seed), seeds give one class if they agree and
INTERMEDIATE otherwise, panels that disagree give NOT REPLICATED. DEGENERATE is decided inside a seed
by any degenerate (or undefined) primary setting of the case or its reference.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import math
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import core
from .analysis_a import (
    INCOMPLETE,
    MissingRecord,
    accuracy_of,
    combine_panels,
    find_cell,
    get_record,
    incomplete_result,
    info_of,
    information_ratio,
    leaky_labels,
    make_result,
    missing_keys,
    panel_stream,
    snapshot_pair,
    step_result,
)
from .analysis_b import (
    LEAKAGE,
    case_needs,
    classify_utilization,
    classify_utilization_panel,
    combine_seeds,
    reference_cell,
    subject_of,
)
from .core import Cell, ClassResult, EvalIndex, EvalKey, SimRecord

LOCALITY_CLASSES = (
    "NOT REPLICATED",
    "COLLAPSED / QUALITY_FAILED",
    "DEGENERATE",
    "LOCALITY_POSITIVE",
    "CONCENTRATION_ONLY",
    "WORSE",
    "NO DIFFERENCE",
    "INTERMEDIATE",
)
SYNTHETIC_EXPECTED = {
    "popularity_only": "NO DIFFERENCE",
    "clusters_random_sharing": "NO DIFFERENCE",
    "clusters_aligned_sharing": "LOCALITY_POSITIVE",
    "collapsed_single_set": "DEGENERATE",
    "working_set_below_cache": "DEGENERATE",
    "incomplete_input": "INCOMPLETE",
}
H17_LOC_NOT_EVALUATED = "H17-LOC NOT EVALUATED"
QUALITY_FAILED = "COLLAPSED / QUALITY_FAILED"
UTILIZATION_OK = ("UTILIZATION_PRESERVED", "UTILIZATION_IMPROVED")
CONTROL_LAYOUTS = ("identity", "frequency", "random_partition", "branch_coaccess", "oracle_cluster")
PRIMARY_SETTINGS: tuple[tuple[float, int], ...] = tuple(
    (rho, rows) for rho in core.CACHE_RHOS_PRIMARY for rows in core.CACHE_ROWS_PRIMARY
)
SIMULATED = "SIMULATED"

SimIndex = Mapping[str, Sequence[SimRecord]]  # cell label -> its simulation records


SIM_REQUIRED = (
    "label",
    "update",
    "stream",
    "trace_kind",
    "layout",
    "rows_per_page",
    "cache_fraction",
    "cache_pages",
    "working_set",
    "tie",
    "actual_misses",
    "null_miss_rate",
    "e_ratio",
    "degenerate",
    "pages_per_query",
    "cross_query_reuse",
)


def valid_sim(rec: Mapping[str, Any]) -> bool:
    """True when ``rec`` carries every field the locality analysis reads (malformed records are skipped by
    the loader and listed as unreadable)."""
    return all(k in rec for k in SIM_REQUIRED)


def is_not_evaluated(cls: str) -> bool:
    return cls == core.NOT_EVALUATED or cls.startswith(H17_LOC_NOT_EVALUATED)


# --- the gate ----------------------------------------------------------------------------------------------
def lane_c_gate(
    index: EvalIndex,
    arch: str,
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
) -> dict[str, object]:
    """Gate to interpretation for ``arch``: the 4K -> 16K step supported on both panels (analysis_a step
    rule) and the B1 alpha_u = 0.25, alpha_c = 0 cell UTILIZATION_PRESERVED or IMPROVED. Returns
    ``{"passed", "step_supported", "b1_class", "reasons", "missing"}``. A TASK_CEILING_FAIL at 4,096 or
    16,384 fails the gate (the step is NOT_EVALUATED)."""
    reasons: list[str] = []
    missing: list[str] = []
    step_supported: dict[str, bool | None] = {}
    fail = set(ceiling_fail)
    if fail & {4096, 16384}:
        reasons.append(
            "TASK_CEILING_FAIL at " + ",".join(str(s) for s in sorted(fail & {4096, 16384}))
        )
    for panel in core.PANELS:
        try:
            step_supported[panel] = step_result(
                index, arch, 4096, panel, exposure, estimand=estimand
            ).supported
        except MissingRecord as exc:
            step_supported[panel] = None
            missing.append(str(exc))
    group = [
        c
        for seed in core.INIT_SEEDS
        if (c := find_cell("B1", arch, 16384, alpha_u=core.ALPHA_C_WITH_ALPHA_U, seed=seed))
        is not None
    ]
    b1 = classify_utilization(
        index, group, exposure, estimand=estimand, ceiling_fail=fail, leaky=()
    )
    if b1["cls"] == INCOMPLETE:
        missing += list(b1["details"].get("missing", []))
    if not all(v is True for v in step_supported.values()):
        reasons.append("the 4K->16K capacity step is not supported on both panels")
    if b1["cls"] not in UTILIZATION_OK:
        reasons.append(f"the B1 alpha_u = 0.25 cell is {b1['cls']}")
    return {
        "passed": not reasons and not missing,
        "arch": arch,
        "step_supported": step_supported,
        "b1_class": b1["cls"],
        "reasons": reasons,
        "missing": missing,
    }


# --- simulation records ----------------------------------------------------------------------------------------
def _same(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def find_sim(
    records: Sequence[SimRecord],
    *,
    rows: int,
    rho: float,
    tie: str,
    stream: str,
    update: int | None = None,
    trace_kind: str = "answer",
    layout: str | None = None,
) -> SimRecord | None:
    """The simulation record of one setting under ``layout`` (default: the co-access layout of ``rows``,
    key ``coaccess@R``); with ``update=None`` the latest snapshot present."""
    wanted = layout or f"coaccess@{rows}"
    matches = [
        r
        for r in records
        if r["rows_per_page"] == rows
        and _same(r["cache_fraction"], rho)
        and r["tie"] == tie
        and r["stream"] == stream
        and r["trace_kind"] == trace_kind
        and r["layout"] == wanted
        and (update is None or r["update"] == update)
    ]
    return max(matches, key=lambda r: r["update"]) if matches else None


def _e(rec: SimRecord) -> float | None:
    value = rec["e_ratio"]
    return None if value is None or rec["degenerate"] else float(value)


def e_ratio_case_vs_reference(
    case: Sequence[SimRecord],
    reference: Sequence[SimRecord],
    *,
    rows: int,
    rho: float,
    tie: str,
    stream: str,
    update: int | None = None,
    trace_kind: str = "answer",
) -> float | None:
    """E(case) / E(reference) for one primary setting, each under its own co-access layout; None when
    either E is undefined (degenerate, absent, or a zero reference)."""
    c = find_sim(
        case, rows=rows, rho=rho, tie=tie, stream=stream, update=update, trace_kind=trace_kind
    )
    r = find_sim(
        reference, rows=rows, rho=rho, tie=tie, stream=stream, update=update, trace_kind=trace_kind
    )
    if c is None or r is None:
        return None
    ec, er = _e(c), _e(r)
    return None if ec is None or er is None or er <= 0 else ec / er


def raw_miss_ratio(
    case: Sequence[SimRecord],
    reference: Sequence[SimRecord],
    *,
    rows: int,
    rho: float,
    tie: str,
    stream: str,
    update: int | None = None,
    trace_kind: str = "answer",
) -> float | None:
    """Actual-miss ratio case / reference (used by CONCENTRATION_ONLY); None when absent or the reference has no misses."""
    c = find_sim(
        case, rows=rows, rho=rho, tie=tie, stream=stream, update=update, trace_kind=trace_kind
    )
    r = find_sim(
        reference, rows=rows, rho=rho, tie=tie, stream=stream, update=update, trace_kind=trace_kind
    )
    if c is None or r is None or r["actual_misses"] <= 0:
        return None
    return c["actual_misses"] / r["actual_misses"]


@dataclass(frozen=True)
class Setting:
    """One (setting, tie) of one seed on one panel; ratios are case over reference."""

    e_ratio: float | None
    raw_ratio: float | None
    degenerate: bool


def locality_class(
    settings: Sequence[Setting], *, collapsed: bool, quality_failed: bool, utilization_ok: bool
) -> str:
    """Rows 2-6 of ADR 8.4 for one seed on one panel, over all given settings (the four primary settings
    x both tie rules), first match wins: COLLAPSED / QUALITY_FAILED, DEGENERATE (any setting degenerate
    for the case or its reference), LOCALITY_POSITIVE (every E ratio <= 0.80 and the cell UTILIZATION_
    PRESERVED or IMPROVED), CONCENTRATION_ONLY (every raw miss ratio <= 0.80 and every E ratio > 0.90),
    WORSE (every E ratio >= 1.10), NO DIFFERENCE (every E ratio in (0.90, 1.10)), else INTERMEDIATE."""
    if collapsed or quality_failed:
        return QUALITY_FAILED
    if any(s.degenerate for s in settings):
        return "DEGENERATE"
    if not settings or any(s.e_ratio is None for s in settings):
        return core.INTERMEDIATE
    es = [float(s.e_ratio) for s in settings if s.e_ratio is not None]
    if all(e <= core.LOCALITY_E_RATIO_POSITIVE for e in es) and utilization_ok:
        return "LOCALITY_POSITIVE"
    lo, hi = core.LOCALITY_E_RATIO_BAND
    if all(
        s.raw_ratio is not None and s.raw_ratio <= core.LOCALITY_E_RATIO_POSITIVE for s in settings
    ) and all(e > lo for e in es):
        return "CONCENTRATION_ONLY"
    if all(e >= hi for e in es):
        return "WORSE"
    if all(lo < e < hi for e in es):
        return "NO DIFFERENCE"
    return core.INTERMEDIATE


def classify_planted(kind: str, result_class: str) -> bool:
    """Synthetic part (ADR 9): True when the class produced for the planted trace of ``kind`` equals
    ``SYNTHETIC_EXPECTED[kind]`` (every class must be exercised by a required test)."""
    if kind not in SYNTHETIC_EXPECTED:
        raise ValueError(f"unknown planted trace kind {kind!r}")
    return result_class == SYNTHETIC_EXPECTED[kind]


def locality_reference(case: Cell) -> Cell | None:
    """The dose-zero flat 16K cell of the same seed (the locality reference, also for tree cases)."""
    return find_cell("A1", "flat", case.slots, parent=case.parent, seed=case.seed)


def _sim_key(cell: Cell, exposure: int, estimand: str) -> int:
    return snapshot_pair(cell, exposure, estimand)[1]


def _settings_for(
    sims: SimIndex, case: Cell, ref: Cell, panel: str, exposure: int, estimand: str
) -> tuple[list[Setting], dict[str, Any], list[str]]:
    stream = panel_stream(panel)
    settings: list[Setting] = []
    table: dict[str, Any] = {}
    missing: list[str] = []
    for rho, rows in PRIMARY_SETTINGS:
        for tie in core.TIE_RULES:
            c = find_sim(
                sims.get(case.label, ()),
                rows=rows,
                rho=rho,
                tie=tie,
                stream=stream,
                update=_sim_key(case, exposure, estimand),
            )
            r = find_sim(
                sims.get(ref.label, ()),
                rows=rows,
                rho=rho,
                tie=tie,
                stream=stream,
                update=_sim_key(ref, exposure, estimand),
            )
            name = f"rho{rho:g}|R{rows}|{tie}"
            if c is None or r is None:
                missing.append(f"{case.label if c is None else ref.label}:sim:{name}/{stream}")
                continue
            ec, er = _e(c), _e(r)
            e = None if ec is None or er is None or er <= 0 else ec / er
            raw = c["actual_misses"] / r["actual_misses"] if r["actual_misses"] > 0 else None
            degenerate = bool(c["degenerate"] or r["degenerate"] or e is None)
            settings.append(Setting(e, raw, degenerate))
            table[name] = {
                "e_case": c["e_ratio"],
                "e_reference": r["e_ratio"],
                "e_ratio": e,
                "raw_miss_ratio": raw,
                "degenerate_case": c["degenerate"],
                "degenerate_reference": r["degenerate"],
                "null_miss_rate_case": c["null_miss_rate"],
                "null_miss_rate_reference": r["null_miss_rate"],
                "pages_per_query_case": c["pages_per_query"],
                "pages_per_query_reference": r["pages_per_query"],
                "cross_query_reuse_case": c["cross_query_reuse"],
                "cross_query_reuse_reference": r["cross_query_reuse"],
                "cache_pages_case": c["cache_pages"],
                "working_set_case": c["working_set"],
                "label": SIMULATED,
            }
    return settings, table, missing


def _controls(
    sims: SimIndex, case: Cell, ref: Cell, stream: str, exposure: int, estimand: str
) -> dict[str, Any]:
    """E of the case and the reference under the control layouts (identity, frequency, random partition,
    branch-constrained, oracle): reported beside the class, entering none."""
    out: dict[str, Any] = {}
    for layout in {r["layout"] for label in (case.label, ref.label) for r in sims.get(label, ())}:
        name = layout.split("@")[0]
        if name not in CONTROL_LAYOUTS:
            continue
        for rho, rows in PRIMARY_SETTINGS:
            for tie in core.TIE_RULES:
                c = find_sim(
                    sims.get(case.label, ()),
                    rows=rows,
                    rho=rho,
                    tie=tie,
                    stream=stream,
                    update=_sim_key(case, exposure, estimand),
                    layout=layout,
                )
                r = find_sim(
                    sims.get(ref.label, ()),
                    rows=rows,
                    rho=rho,
                    tie=tie,
                    stream=stream,
                    update=_sim_key(ref, exposure, estimand),
                    layout=layout,
                )
                if c is not None or r is not None:
                    out.setdefault(layout, {})[f"rho{rho:g}|R{rows}|{tie}"] = {
                        "e_case": None if c is None else c["e_ratio"],
                        "e_reference": None if r is None else r["e_ratio"],
                        "label": SIMULATED,
                    }
    return out


def _cache_to_ustar(
    index: EvalIndex, case: Cell, panel: str, exposure: int, estimand: str, table: Mapping[str, Any]
) -> dict[str, float | None]:
    rec = index[(case.label, _sim_key(case, exposure, estimand), panel_stream(panel))]
    ustar = rec.get("useful_slots")
    out: dict[str, float | None] = {}
    for name, row in table.items():
        rows = int(name.split("|R")[1].split("|")[0])
        pages = row["cache_pages_case"]
        out[name] = (pages * rows) / ustar if ustar else None
    return out


def _unit(
    index: EvalIndex,
    sims: SimIndex,
    case: Cell,
    ref: Cell,
    panel: str,
    exposure: int,
    estimand: str,
) -> tuple[str, dict[str, Any], list[str]]:
    """Class of one seed on one panel against locality reference ``ref``, and the numbers behind it."""
    util = classify_utilization_panel(index, case, panel, exposure, estimand=estimand)
    stream = panel_stream(panel)
    i_ref = info_of(get_record(index, ref.label, _sim_key(ref, exposure, estimand), stream))
    i_case = info_of(get_record(index, case.label, _sim_key(case, exposure, estimand), stream))
    i_ratio = information_ratio(i_ref, i_case)
    settings, table, missing = _settings_for(sims, case, ref, panel, exposure, estimand)
    if missing:
        return INCOMPLETE, {"missing": missing}, missing
    cls = locality_class(
        settings,
        collapsed=util == "COLLAPSED",
        quality_failed=i_ratio < core.LOCALITY_QUALITY_RATIO,
        utilization_ok=util in UTILIZATION_OK,
    )
    numbers = {
        "utilization_class": util,
        "i_ratio_to_locality_reference": i_ratio,
        "accuracy_case": accuracy_of(
            get_record(index, case.label, _sim_key(case, exposure, estimand), stream)
        ),
        "settings": table,
        "cache_pages_x_rows_over_ustar": _cache_to_ustar(
            index, case, panel, exposure, estimand, table
        ),
        "controls": _controls(sims, case, ref, stream, exposure, estimand),
        "locality_reference": ref.label,
        "label": SIMULATED,
    }
    return cls, numbers, []


def classify_locality_panel(
    index: EvalIndex,
    sims: SimIndex,
    case: Cell,
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
    reference: Cell | None = None,
) -> str:
    """Rules 2-6 of ADR 8.4 for one panel and one seed's cell over all four settings and both ties:
    COLLAPSED / QUALITY_FAILED (utilization COLLAPSED or I ratio to the locality reference < 0.97) before
    DEGENERATE (any primary setting degenerate for the case or its reference), LOCALITY_POSITIVE (E ratio
    <= 0.80 and the cell UTILIZATION_PRESERVED or IMPROVED), CONCENTRATION_ONLY (raw miss ratio <= 0.80
    and E ratio > 0.90), WORSE (>= 1.10) / NO DIFFERENCE (in (0.90, 1.10)) / INTERMEDIATE. INCOMPLETE if a
    record is missing. ``reference`` defaults to the dose-zero flat 16K cell of the same seed."""
    ref = reference or locality_reference(case)
    if ref is None:
        return INCOMPLETE
    try:
        return _unit(index, sims, case, ref, panel, exposure, estimand)[0]
    except MissingRecord:
        return INCOMPLETE


def _needs(
    case_group: Sequence[Cell], ref_group: Sequence[Cell], exposure: int, estimand: str
) -> list[EvalKey]:
    needs = case_needs(list(case_group), exposure, estimand)
    for ref in ref_group:
        needs += [
            (ref.label, _sim_key(ref, exposure, estimand), panel_stream(p)) for p in core.PANELS
        ]
    return needs


def _classify_group(
    index: EvalIndex,
    sims: SimIndex,
    case_group: list[Cell],
    ref_group: Sequence[Cell],
    exposure: int,
    estimand: str,
) -> tuple[str, dict[str, str], dict[str, Any], list[str]]:
    panel_classes: dict[str, str] = {}
    details: dict[str, Any] = {"panels": {}}
    missing: list[str] = []
    refs = {c.seed: c for c in ref_group}
    for panel in core.PANELS:
        seed_classes: dict[str, str] = {}
        nums: dict[str, Any] = {}
        for case in sorted(case_group, key=lambda c: c.seed):
            ref = refs.get(case.seed)
            if ref is None:
                missing.append(f"no locality reference for seed {case.seed}")
                seed_classes[str(case.seed)] = INCOMPLETE
                continue
            cls, numbers, gaps = _unit(index, sims, case, ref, panel, exposure, estimand)
            missing += gaps
            seed_classes[str(case.seed)] = cls
            nums[str(case.seed)] = numbers
        panel_classes[panel] = combine_seeds(list(seed_classes.values()))
        details["panels"][panel] = {"seed_classes": seed_classes, "numbers": nums}
    return combine_panels(panel_classes), panel_classes, details, sorted(set(missing))


def classify_locality(
    index: EvalIndex,
    sims: SimIndex,
    case_group: list[Cell],
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] | None = None,
    gate: Mapping[str, object] | None = None,
    reference_group: Sequence[Cell] | None = None,
    subject: str | None = None,
) -> ClassResult:
    """Class of one C1 case (both seeds) with the controls, pages per query, cross-query reuse and the
    ratio of cache size to U* reported in ``details``. If the Lane C gate fails the class is
    ``H17-LOC NOT EVALUATED`` and the class that the rules would give is kept in
    ``details['descriptive_class']`` (descriptive only). ``reference_group`` replaces the dose-zero flat
    16K reference (used for the tree against the flat case of the same doses)."""
    first = case_group[0]
    subj = subject or subject_of(first)
    if sorted(c.seed for c in case_group) != sorted(core.INIT_SEEDS):
        raise ValueError("a case group holds one cell per initialization seed")
    ref_group = (
        list(reference_group)
        if reference_group is not None
        else [r for c in case_group if (r := locality_reference(c)) is not None]
    )
    gate_result = (
        dict(gate)
        if gate is not None
        else lane_c_gate(index, first.arch, exposure, estimand=estimand, ceiling_fail=ceiling_fail)
    )
    base: dict[str, Any] = {
        "estimand": estimand,
        "exposure": exposure,
        "alpha_u": first.alpha_u,
        "alpha_c": first.alpha_c,
        "arch": first.arch,
        "gate": gate_result,
        "label": SIMULATED,
        "locality_reference_labels": [c.label for c in ref_group],
    }
    if set(ceiling_fail) & {first.slots}:
        return make_result(
            "C",
            subj,
            H17_LOC_NOT_EVALUATED,
            {p: H17_LOC_NOT_EVALUATED for p in core.PANELS},
            [f"TASK_CEILING_FAIL({first.slots})"],
            base,
        )
    missing = missing_keys(index, _needs(case_group, ref_group, exposure, estimand))
    cls, panel_classes, details, gaps = (
        _classify_group(index, sims, case_group, ref_group, exposure, estimand)
        if not missing
        else (INCOMPLETE, {}, {"panels": {}}, [])
    )
    missing = sorted(set(missing) | set(gaps))
    base.update(details)
    if missing:
        return incomplete_result(
            "C", subj, missing, **{k: v for k, v in base.items() if k != "panels"}
        )
    annotations: list[str] = []
    used = sorted(
        {c.label for c in case_group}
        | {c.label for c in ref_group}
        | {r.label for c in case_group if (r := reference_cell(c)) is not None}
    )
    leaky_set = leaky_labels(index) if leaky is None else set(leaky)
    if leaky_set & set(used):
        annotations.append(LEAKAGE)
        base["interpretation_withheld"] = (
            "LEAKAGE: the lane is not interpreted until the auditor explains it"
        )
    base["used_labels"] = used
    if not gate_result["passed"]:
        base["descriptive_class"] = cls
        annotations.append(H17_LOC_NOT_EVALUATED)
        return make_result(
            "C",
            subj,
            H17_LOC_NOT_EVALUATED,
            {p: H17_LOC_NOT_EVALUATED for p in core.PANELS},
            annotations,
            base,
        )
    return make_result("C", subj, cls, panel_classes, annotations, base)


def hierarchy_advantage(flat: ClassResult, tree: ClassResult) -> bool:
    """A hierarchy advantage needs the tree case LOCALITY_POSITIVE against the flat case with the same
    doses (ADR 8.4): ``tree['details']['vs_flat_same_dose']`` is the class of the tree case computed with
    the flat case of the same doses as the locality reference."""
    vs = tree["details"].get("vs_flat_same_dose")
    if not isinstance(vs, Mapping):
        return False
    same_doses = flat["details"].get("alpha_c") == tree["details"].get("alpha_c") and flat[
        "details"
    ].get("alpha_u") == tree["details"].get("alpha_u")
    return bool(same_doses and vs.get("cls") == "LOCALITY_POSITIVE")


def d09_sweep(sims: SimIndex) -> list[dict[str, object]]:
    """Descriptive table of rho in {1/16, 1/4, 1} x R in {2, 8, 32}; settings outside the primary four
    and all rho = 1 are labelled descriptive. Every row is SIMULATED."""
    rows_out: list[dict[str, object]] = []
    for label in sorted(sims):
        for r in sims[label]:
            primary = (
                r["trace_kind"] == "answer"
                and any(_same(r["cache_fraction"], rho) for rho in core.CACHE_RHOS_PRIMARY)
                and r["rows_per_page"] in core.CACHE_ROWS_PRIMARY
                and r["layout"] == f"coaccess@{r['rows_per_page']}"
            )
            rows_out.append(
                {
                    "label": label,
                    "update": r["update"],
                    "stream": r["stream"],
                    "trace_kind": r["trace_kind"],
                    "layout": r["layout"],
                    "rows_per_page": r["rows_per_page"],
                    "cache_fraction": r["cache_fraction"],
                    "tie": r["tie"],
                    "e_ratio": r["e_ratio"],
                    "actual_misses": r["actual_misses"],
                    "null_miss_rate": r["null_miss_rate"],
                    "degenerate": r["degenerate"],
                    "status": "primary" if primary else "descriptive",
                    "kind": SIMULATED,
                }
            )
    return rows_out


def key_traffic_rows() -> list[dict[str, object]]:
    """Key traffic (ADR 9): keys in RAM move no key pages; keys on storage mean the flat memory reads
    every key (N key products per query) and the tree its router and two branches. An arithmetic
    identity from ADR 5.2, labelled ANALYTICAL, never a simulation result and never measured I/O."""
    out: list[dict[str, object]] = []
    for arch in ("flat", "learned_tree"):
        for slots in core.SLOTS_BY_SIZE:
            out.append(
                {
                    "arch": arch,
                    "slots": slots,
                    "keys_in_ram_key_products_read_from_storage": 0,
                    "keys_on_storage_key_products_per_query": core.logical_key_products(
                        arch, slots
                    ),
                    "kind": "ANALYTICAL identity (logical work), not a simulation and not storage I/O",
                }
            )
    return out


def c1_groups() -> list[list[Cell]]:
    groups: list[list[Cell]] = []
    for arch in ("flat", "learned_tree"):
        for alpha_c in (0.05, 0.25):
            groups.append(
                [
                    c
                    for seed in core.INIT_SEEDS
                    if (
                        c := find_cell(
                            "C1",
                            arch,
                            16384,
                            alpha_u=core.ALPHA_C_WITH_ALPHA_U,
                            alpha_c=alpha_c,
                            seed=seed,
                        )
                    )
                    is not None
                ]
            )
    return groups


def analyze(
    index: EvalIndex,
    sims: SimIndex,
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] | None = None,
) -> list[ClassResult]:
    """All C1 classes (flat and learned tree, alpha_c in {0.05, 0.25}) plus the gate per architecture,
    hierarchy advantages, the D09 sweep and the key-traffic identity as descriptive entries."""
    results: list[ClassResult] = []
    gates = {
        arch: lane_c_gate(index, arch, exposure, estimand=estimand, ceiling_fail=ceiling_fail)
        for arch in ("flat", "learned_tree")
    }
    for arch, gate in gates.items():
        cls = "LANE_C_GATE_PASSED" if gate["passed"] else H17_LOC_NOT_EVALUATED
        results.append(
            make_result(
                "C",
                f"lane_c_gate/{arch}",
                cls,
                {p: cls for p in core.PANELS},
                [] if gate["passed"] else [H17_LOC_NOT_EVALUATED],
                dict(gate),
            )
        )
    by_dose: dict[float, dict[str, ClassResult]] = {}
    for group in c1_groups():
        arch = group[0].arch
        res = classify_locality(
            index,
            sims,
            group,
            exposure,
            estimand=estimand,
            ceiling_fail=ceiling_fail,
            leaky=leaky,
            gate=gates[arch],
        )
        by_dose.setdefault(group[0].alpha_c, {})[arch] = res
        results.append(res)
    for alpha_c, pair in sorted(by_dose.items()):
        flat_group = [
            c
            for seed in core.INIT_SEEDS
            if (
                c := find_cell(
                    "C1",
                    "flat",
                    16384,
                    alpha_u=core.ALPHA_C_WITH_ALPHA_U,
                    alpha_c=alpha_c,
                    seed=seed,
                )
            )
            is not None
        ]
        tree_group = [
            c
            for seed in core.INIT_SEEDS
            if (
                c := find_cell(
                    "C1",
                    "learned_tree",
                    16384,
                    alpha_u=core.ALPHA_C_WITH_ALPHA_U,
                    alpha_c=alpha_c,
                    seed=seed,
                )
            )
            is not None
        ]
        vs = classify_locality(
            index,
            sims,
            tree_group,
            exposure,
            estimand=estimand,
            ceiling_fail=ceiling_fail,
            leaky=leaky,
            gate=gates["learned_tree"],
            reference_group=flat_group,
            subject=f"{subject_of(tree_group[0])}/vs_flat_same_dose",
        )
        if "learned_tree" in pair:
            pair["learned_tree"]["details"]["vs_flat_same_dose"] = {
                "cls": vs["cls"],
                "panel_classes": vs["panel_classes"],
                "missing": vs["details"].get("missing", []),
            }
        verdict = (
            "HIERARCHY_ADVANTAGE"
            if "flat" in pair
            and "learned_tree" in pair
            and hierarchy_advantage(pair["flat"], pair["learned_tree"])
            else "NO_HIERARCHY_ADVANTAGE"
        )
        results.append(
            make_result(
                "C",
                f"hierarchy/ac{alpha_c:g}",
                verdict,
                {p: verdict for p in core.PANELS},
                [],
                {"alpha_c": alpha_c, "tree_vs_flat_same_dose": vs["cls"], "label": SIMULATED},
            )
        )
    results.append(
        make_result(
            "C",
            "d09_sweep",
            "DESCRIPTIVE",
            {p: "DESCRIPTIVE" for p in core.PANELS},
            [],
            {"rows": d09_sweep(sims), "label": SIMULATED},
        )
    )
    results.append(
        make_result(
            "C",
            "key_traffic_identity",
            "DESCRIPTIVE",
            {p: "DESCRIPTIVE" for p in core.PANELS},
            [],
            {"rows": key_traffic_rows(), "label": "ANALYTICAL"},
        )
    )
    return results
