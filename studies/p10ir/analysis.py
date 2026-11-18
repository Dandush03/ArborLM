# ruff: noqa: E501
"""P10IR analysis (ADR-0029 sections 7 to 10): registry of records -> replicate labels -> cell labels -> R-DIAGNOSIS, R-DIAGNOSIS-LOADED, R-CONFIRM, with every descriptive section.

Pure over a ``Registry`` (and the plateau series and the D-OQ context that the analysis stage extracts through the whitelist extractor). No torch. Every label dict carries the stage tag
(``REGISTERED RE-ANALYSIS OF OBSERVED CELLS`` for A1, ``FRESH CHECKPOINTS`` for A2) and the standing tag. Keys of the registry carry the read's name (``core.read_key``).
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import core, labels
from .registry import Registry, scope_ok

LabelOf = Callable[[str, core.CellSpec, int], str]
TREE_COLLECT = ("T0", "T1", "T1w", "T2", "T3")
CP_NAMES = ("TRAJ1", "TRAJ2")


def default_label_of(stage: str, cfg: Mapping[str, Any] | None = None) -> LabelOf:
    """P10-S1's cell label (A1) or the bridge cell's label (A2) of ``arm`` at a cell and draw."""

    def of(arm: str, spec: core.CellSpec, draw: int) -> str:
        if stage == core.STAGE_A1:
            return core.s1_label(arm, spec.facts, spec.slots, draw, spec.u_p, spec.run, cfg)
        return core.bridge_label(arm, spec.facts, spec.slots, draw, spec.u_p, spec.run, cfg)

    return of


def label_of_from_items(plan_items: Sequence[Mapping[str, Any]]) -> LabelOf:
    """Cell labels as the PLAN's items name them, keyed by (cell name, arm, draw): the analysis takes its labels from the plan and never from the config (audit R2; section 13: every stage derives its items from
    the plan only)."""
    table = {(it["cell_name"], it["arm"], int(it["draw"])): str(it["cell"]) for it in plan_items}

    def of(arm: str, spec: core.CellSpec, draw: int) -> str:
        try:
            return table[(spec.name, arm, draw)]
        except KeyError:
            return f"NO-PLAN-ITEM|{spec.name}|{arm}|{draw}"  # a replicate the plan does not have: no item record, NOT EVALUABLE

    return of


def checkpoint_names(spec: core.CellSpec) -> dict[str, int]:
    """U_P and RUN (co-primary) and the two trajectory points (descriptive), by name."""
    out = {"U_P": spec.u_p, "RUN": spec.run}
    for name, u in zip(CP_NAMES, sorted(spec.trajectory), strict=True):
        out[name] = u
    return out


def _mean(xs: Sequence[float | None]) -> float | None:
    got = [float(x) for x in xs if x is not None]
    return sum(got) / len(got) if got else None


def _panel_i(rec: Mapping[str, Any] | None) -> dict[str, float] | None:
    if rec is None:
        return None
    try:
        return {p: float(rec["panels"][p]["i"]) for p in labels.PANELS}
    except (KeyError, TypeError):
        return None


def _panel_mean(rec: Mapping[str, Any] | None, field: str) -> float | None:
    if rec is None:
        return None
    try:
        return _mean([float(rec["panels"][p][field]) for p in labels.PANELS])
    except (KeyError, TypeError):
        return None


def _fact(rec: Mapping[str, Any] | None, name: str) -> float | None:
    if rec is None:
        return None
    v = (rec.get("facts") or {}).get(name)
    return None if v is None else float(v)


def _pair(rec: Mapping[str, Any] | None, name: str) -> float | None:
    if rec is None:
        return None
    v = (rec.get("pair") or {}).get(name)
    return None if v is None else float(v)


def _acc(rec: Mapping[str, Any] | None, panel: str, key: str = "accuracy") -> float | None:
    try:
        return None if rec is None else float(rec["panels"][panel][key])
    except (KeyError, TypeError):
        return None


def _acc0(rec: Mapping[str, Any] | None, panel: str) -> float | None:
    """Memory-disabled accuracy of the checkpoint and panel: P10-S1's ``panel_counts`` ``disabled_correct`` / n (ruling 3)."""
    try:
        return None if rec is None else float(rec["panels"][panel]["disabled_correct"]) / float(rec["panels"][panel]["n"])
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def _retention_entry(x: Mapping[str, Any] | None, y: Mapping[str, Any] | None, th: core.Thresholds, accs_x: Sequence[Mapping[str, Any] | None] | None = None) -> dict[str, Any] | None:
    """Per panel: the retention status of X against Y (the rule, in bits) and the accuracy version [acc(X) - acc0] / [acc(Y) - acc0], printed beside it and deciding nothing. ``accs_x`` are the reads
    averaged for X (the index seeds)."""
    recs = list(accs_x) if accs_x is not None else [x]
    if y is None or any(r is None for r in recs) or x is None:
        return None
    out: dict[str, Any] = {}
    for p in labels.PANELS:
        ix = sum(float(r["panels"][p]["i"]) for r in recs if r is not None) / len(recs)
        iy = float(y["panels"][p]["i"])
        accx = [_acc(r, p) for r in recs]
        acc0 = [_acc0(r, p) for r in recs]
        accy, y0 = _acc(y, p), _acc0(y, p)
        if None in accx or None in acc0 or accy is None or y0 is None:
            ratio = None
        else:
            v = labels.accuracy_retained(sum(accx) / len(accx), accy, sum(acc0) / len(acc0))  # type: ignore[arg-type]
            ratio = None if v != v else v
        out[p] = {"status": labels.retention(ix, iy, th), "accuracy_version": ratio}
    return out


def tree_retention(reg: Registry, stage: str, spec: core.CellSpec, d: int, update: int, label_of: LabelOf, th: core.Thresholds) -> dict[str, Any]:
    treads, freads = reg.reads_of(stage, label_of("T-OQ", spec, d), update), reg.reads_of(stage, label_of("F-OQ", spec, d), update)
    return {r: _retention_entry(treads.get(r), freads.get("F0"), th) for r in ("T1", "T3", "T2")}


def index_retention(reg: Registry, stage: str, spec: core.CellSpec, d: int, update: int, label_of: LabelOf, th: core.Thresholds, cfg: Mapping[str, Any], seeds: Sequence[int]) -> dict[str, Any]:
    freads = reg.reads_of(stage, label_of("F-OQ", spec, d), update)
    return {str(c): _retention_entry(freads.get(core.i64_name(c, seeds[0])), freads.get("F0"), th, [freads.get(core.i64_name(c, s)) for s in seeds]) for c in core.feasible_budgets(spec.slots, cfg)}


# --- replicates -----------------------------------------------------------------------------------------------------------------------------
def tree_rep(reg: Registry, stage: str, spec: core.CellSpec, d: int, update: int, label_of: LabelOf) -> labels.TreeRep:
    t_label, f_label = label_of("T-OQ", spec, d), label_of("F-OQ", spec, d)
    ok_t, why_t = scope_ok(reg.item(stage, t_label, update), "tree")
    ok_f, why_f = scope_ok(reg.item(stage, f_label, update), "f0")
    if not ok_t or not ok_f:
        return labels.TreeRep(False, reason="; ".join(x for x in (f"T-OQ: {why_t}" if not ok_t else "", f"F-OQ: {why_f}" if not ok_f else "") if x))
    treads, freads = reg.reads_of(stage, t_label, update), reg.reads_of(stage, f_label, update)
    i: dict[str, dict[str, float]] = {}
    for name, source in [(r, treads) for r in TREE_COLLECT] + [("F0", freads)]:
        got = _panel_i(source.get(name))
        if got is None:
            return labels.TreeRep(False, reason=f"missing read {name}")
        i[name] = got
    cr8 = _fact(treads.get("T0"), "cr8")
    if cr8 is None:
        return labels.TreeRep(False, reason="missing CR8 of T0")
    return labels.TreeRep(True, i, cr8)


def index_rep(reg: Registry, stage: str, spec: core.CellSpec, d: int, update: int, label_of: LabelOf, cfg: Mapping[str, Any], seeds: Sequence[int] | None = None) -> labels.IndexRep:
    f_label = label_of("F-OQ", spec, d)
    item = reg.item(stage, f_label, update)
    ok_f, why_f = scope_ok(item, "f0")
    ok_i, why_i = scope_ok(item, "index")
    if not ok_f or not ok_i:
        return labels.IndexRep(False, reason="; ".join(x for x in (f"F0: {why_f}" if not ok_f else "", f"index: {why_i}" if not ok_i else "") if x))
    reads = reg.reads_of(stage, f_label, update)
    f0 = _panel_i(reads.get("F0"))
    if f0 is None:
        return labels.IndexRep(False, reason="missing read F0")
    seeds = list(seeds) if seeds else core.i64_seeds(cfg)
    budget_i: dict[int, dict[str, float]] = {}
    for c in core.feasible_budgets(spec.slots, cfg):
        per_seed = [_panel_i(reads.get(core.i64_name(c, s))) for s in seeds]
        if any(x is None for x in per_seed):
            return labels.IndexRep(False, reason=f"missing I64@{c} read")
        budget_i[c] = {p: float(sum(x[p] for x in per_seed if x is not None) / len(seeds)) for p in labels.PANELS}  # the mean over the index seeds, before the panel test
    return labels.IndexRep(True, f0, budget_i)


# --- descriptive sections ----------------------------------------------------------------------------------------------------------------------
def _read_summary(rec: Mapping[str, Any] | None) -> dict[str, Any]:
    return {"i": _panel_mean(rec, "i"), "a_use": _panel_mean(rec, "a_use"), "accuracy": _panel_mean(rec, "accuracy"), "keys_scored_per_query": None if rec is None else (rec.get("work") or {}).get("K")}


def tree_descriptive(reg: Registry, stage: str, spec: core.CellSpec, update: int, label_of: LabelOf, cfg: Mapping[str, Any], th: core.Thresholds) -> dict[str, Any]:
    """The 'printed with every label' set of section 8.3, as means over the five replicates (a missing record is skipped; the replicate count is printed)."""
    per_read: dict[str, list[Mapping[str, Any] | None]] = {r: [] for r in (*TREE_COLLECT, "F0")}
    sweep: dict[int, dict[str, list[Mapping[str, Any] | None]]] = {v: {"on": [], "off": []} for v in cfg["reads"]["visit_sweep"]}
    for d in range(1, th.replicates + 1):
        treads = reg.reads_of(stage, label_of("T-OQ", spec, d), update)
        freads = reg.reads_of(stage, label_of("F-OQ", spec, d), update)
        for r in TREE_COLLECT:
            per_read[r].append(treads.get(r))
        per_read["F0"].append(freads.get("F0"))
        for v in sweep:
            if v == int(cfg["reads"]["visit_registered"]):
                on, off = treads.get("T0"), treads.get("T1")
            elif v == spec.branches:
                on, off = treads.get("T3"), treads.get("T2")
            else:
                on, off = treads.get(core.tv_name(v, "on")), treads.get(core.tv_name(v, "off"))
            sweep[v]["on"].append(on)
            sweep[v]["off"].append(off)
    out: dict[str, Any] = {"reads": {}, "sweep": {}, "replicates_present": {r: sum(1 for x in xs if x is not None) for r, xs in per_read.items()}}
    for r, xs in per_read.items():
        s = [_read_summary(x) for x in xs]
        out["reads"][r] = {k: _mean([e[k] for e in s]) for k in ("i", "a_use", "accuracy", "keys_scored_per_query")}
    for v, sides in sweep.items():
        if v > spec.branches:
            out["sweep"][str(v)] = {"status": "NOT APPLICABLE", "reason": f"v = {v} exceeds N/256 = {spec.branches}"}
            continue
        out["sweep"][str(v)] = {
            "status": "READ" + (" (as T0 / T1)" if v == int(cfg["reads"]["visit_registered"]) else " (as T3 / T2)" if v == spec.branches else ""),
            "i_on": _mean([_panel_mean(x, "i") for x in sides["on"]]), "i_off": _mean([_panel_mean(x, "i") for x in sides["off"]]),
            "cr8_on": _mean([_fact(x, "cr8") for x in sides["on"]]), "keys_scored_per_query_on": _mean([None if x is None else (x.get("work") or {}).get("K") for x in sides["on"]]),
        }  # fmt: skip
    t0 = per_read["T0"]
    out["t0_measures"] = {k: _mean([_fact(x, k) for x in t0]) for k in ("cr8", "cr1", "sr8", "am_c", "am_s", "share_span_both")}
    i_means = {r: out["reads"][r]["i"] for r in out["reads"]}
    out["closure_means"] = {}
    if None not in (i_means["T0"], i_means["F0"]) and i_means["F0"] > i_means["T0"]:  # type: ignore[operator]
        den = i_means["F0"] - i_means["T0"]  # type: ignore[operator]
        out["closure_means"] = {k: None if i_means[r] is None else (i_means[r] - i_means["T0"]) / den for k, r in (("g_P", "T1"), ("g_C", "T3"), ("g_PC", "T2"))}  # type: ignore[operator]
    out["i_f0_minus_t2"] = None if None in (i_means["F0"], i_means["T2"]) else i_means["F0"] - i_means["T2"]  # type: ignore[operator]
    out["prior_effect"] = {
        "i_T1_minus_T0": _delta(i_means, "T1", "T0"), "i_T1w_minus_T0": _delta(i_means, "T1w", "T0"), "i_T2_minus_T3": _delta(i_means, "T2", "T3"),
        "share_selection_changed_T0_to_T1": _mean([_pair(x, "share_selected_changed") for x in per_read["T1"]]), "tv_distance_T0_to_T1": _mean([_pair(x, "tv_mean") for x in per_read["T1"]]),
        "share_selection_changed_T0_to_T1w": _mean([_pair(x, "share_selected_changed") for x in per_read["T1w"]]), "tv_distance_T0_to_T1w": _mean([_pair(x, "tv_mean") for x in per_read["T1w"]]),
        "share_selection_changed_T3_to_T2": _mean([_pair(x, "share_selected_changed") for x in per_read["T2"]]), "tv_distance_T3_to_T2": _mean([_pair(x, "tv_mean") for x in per_read["T2"]]),
        "share_facts_span_both_branches_T0": out["t0_measures"]["share_span_both"],
    }  # fmt: skip
    change = _mean([_pair(x, "share_selected_changed") for x in per_read["T3"]])
    out["testability"] = {"share_T3_selection_equals_T0": None if change is None else 1.0 - change, "note": "near 1: T3 could not differ from T0, and the row CANDIDATES was not testable at this cell"}
    return out


def _delta(i: Mapping[str, float | None], a: str, b: str) -> float | None:
    return None if i[a] is None or i[b] is None else i[a] - i[b]  # type: ignore[operator]


def index_descriptive(reg: Registry, stage: str, spec: core.CellSpec, update: int, label_of: LabelOf, cfg: Mapping[str, Any], th: core.Thresholds, seeds: Sequence[int] | None = None) -> dict[str, Any]:
    seeds = list(seeds) if seeds else core.i64_seeds(cfg)
    out: dict[str, Any] = {"budgets": {}, "I256@512": {}, "F0": {}, "N_over_8": spec.slots / 8, "shallow": spec.shallow}
    f0s, i256s = [], []
    per_budget: dict[int, list[Mapping[str, Any] | None]] = {c: [] for c in cfg["reads"]["index_budgets"]}
    for d in range(1, th.replicates + 1):
        reads = reg.reads_of(stage, label_of("F-OQ", spec, d), update)
        f0s.append(reads.get("F0"))
        i256s.append(reads.get("I256@512"))
        for c in per_budget:
            per_budget[c].extend(reads.get(core.i64_name(c, s)) for s in seeds)
    out["F0"] = _read_summary_pop(f0s)
    out["I256@512"] = {**_read_summary_pop(i256s), **_index_measures(i256s)}
    for c, recs in per_budget.items():
        if c >= spec.slots:
            out["budgets"][str(c)] = {"status": "NOT APPLICABLE", "reason": f"c = {c} is not below N = {spec.slots}"}
        else:
            out["budgets"][str(c)] = {"status": "READ", **_read_summary_pop(recs), **_index_measures(recs)}
    return out


def _read_summary_pop(recs: Sequence[Mapping[str, Any] | None]) -> dict[str, Any]:
    s = [_read_summary(x) for x in recs]
    return {k: _mean([e[k] for e in s]) for k in ("i", "a_use", "accuracy")} | {"reads_present": sum(1 for x in recs if x is not None)}


def _index_measures(recs: Sequence[Mapping[str, Any] | None]) -> dict[str, Any]:
    return {k: _mean([_fact(x, k) for x in recs]) for k in ("cr8", "cr1", "am_c")} | {
        "candidates_mean": _mean([None if x is None else (x.get("candidates") or {}).get("mean") for x in recs]),
        "candidates_p99": _mean([None if x is None else (x.get("candidates") or {}).get("p99") for x in recs]),
    }


# --- one stage -----------------------------------------------------------------------------------------------------------------------------------
def analyze_stage(
    reg: Registry,
    stage: str,
    cfg: Mapping[str, Any] | None = None,
    *,
    label_of: LabelOf | None = None,
    plateau: Mapping[str, Mapping[str, Sequence[Mapping[str, Mapping[int, float]] | None]]] | None = None,
    context: Mapping[str, Any] | None = None,
    specs: Sequence[core.CellSpec] | None = None,
    seal_broken: bool = False,
    i64_seeds: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Labels of every cell at every checkpoint, R-DIAGNOSIS (primary cells at U_P and the run length), R-DIAGNOSIS-LOADED (printed only), and every descriptive section.

    ``plateau[cell name]['tree' | 'flat']`` is, per replicate, ``{panel: {update: i}}`` of P10-S1's recorded main reads (extracted through the whitelist extractor) or None. A2 has no recorded
    series: its plateau tag is NOT CHECKED. ``specs`` default to the config's cells (A2: the two primary cells)."""
    cfg = cfg or core.load_config()
    th = core.Thresholds.from_config(cfg)
    label_of = label_of or default_label_of(stage, cfg)
    specs = list(specs) if specs is not None else [s for s in core.cell_specs(cfg) if stage == core.STAGE_A1 or s.role == "primary"]
    stage_tag = core.STAGE_TAG[stage]
    cells: dict[str, Any] = {}
    for spec in specs:
        cps = checkpoint_names(spec)
        if stage == core.STAGE_A2:
            cps = {k: v for k, v in cps.items() if k in ("U_P", "RUN")}
        entry: dict[str, Any] = {"role": spec.role, "facts": spec.facts, "slots": spec.slots, "shallow": spec.shallow, "tags": [], "checkpoints": {}}
        if spec.shallow:
            entry["tags"].append("SHALLOW (four branches; 512 candidates is half the store)")
        for cp, update in cps.items():
            tree_labels, index_labels, t_rows, i_rows = [], [], [], []
            for d in range(1, th.replicates + 1):
                tl = labels.tree_replicate(tree_rep(reg, stage, spec, d, update, label_of), th)
                il = labels.index_replicate(index_rep(reg, stage, spec, d, update, label_of, cfg, i64_seeds), th)
                tree_labels.append({"draw": d, "row": tl.row, "suffix": tl.suffix, "tags": tl.tags, "reason": tl.reason, "retention": tree_retention(reg, stage, spec, d, update, label_of, th)})
                index_labels.append({"draw": d, "row": il.row, "suffix": il.suffix, "tags": il.tags, "reason": il.reason, "retention": index_retention(reg, stage, spec, d, update, label_of, th, cfg, list(i64_seeds) if i64_seeds else core.i64_seeds(cfg))})
                t_rows.append(tl.row)
                i_rows.append(il.row)
            c_stars = [x["tags"].get("c_star") for x in index_labels]
            median_c = labels.median_c_star(c_stars)
            entry["checkpoints"][cp] = {
                "update": update, "descriptive_only": cp in CP_NAMES,
                "tree": {"label": labels.cell_label(t_rows, th), "replicates": tree_labels, "stage_tag": stage_tag, "standing_tag": core.STANDING_TAG, "descriptive": tree_descriptive(reg, stage, spec, update, label_of, cfg, th)},
                "index": {
                    "label": labels.cell_label(i_rows, th), "replicates": index_labels, "stage_tag": stage_tag, "standing_tag": core.STANDING_TAG,
                    "c_star_median": median_c, "c_star_share_of_N": None if median_c is None else median_c / spec.slots, "replicates_without_c_star": [x["draw"] for x in index_labels if x["tags"].get("c_star") is None],
                    "descriptive": index_descriptive(reg, stage, spec, update, label_of, cfg, th, i64_seeds),
                },
            }  # fmt: skip
            if cp == "RUN" and spec.role == "primary":
                entry["checkpoints"][cp]["plateau"] = _plateau_tags(plateau, spec, th, stage)
        if seal_broken:
            for cp in entry["checkpoints"].values():
                cp["tree"]["seal_note"] = "RECALL SEEN BEFORE FREEZE"
        cells[spec.name] = entry
    out: dict[str, Any] = {"stage": stage, "stage_tag": stage_tag, "standing_tag": core.STANDING_TAG, "limit": core.LIMIT_SENTENCE, "cells": cells, "readings": labels.READINGS, "context": dict(context or {}), "seal_broken": seal_broken}
    out.update(_study_level(cells, [s for s in specs if s.role == "primary"], [s for s in specs if s.role == "loaded"], stage))
    return out


def _plateau_tags(plateau: Mapping[str, Mapping[str, Sequence[Any]]] | None, spec: core.CellSpec, th: core.Thresholds, stage: str) -> dict[str, Any]:
    if stage != core.STAGE_A1 or plateau is None or spec.name not in plateau:
        return {"status": "NOT CHECKED", "reason": "no recorded snapshot series" if stage == core.STAGE_A2 else "no series supplied", "tags": []}
    tags = []
    for arm_key, tag in (("tree", "TREE STILL LEARNING"), ("flat", "FLAT STILL LEARNING")):
        series = plateau[spec.name].get(arm_key)
        padded = None if series is None else [*series, *([None] * (th.replicates - len(series)))]  # a replicate the plan does not have fails the check
        if padded is None or labels.still_learning(padded, spec.run, th):
            tags.append(tag)
    return {"status": "CHECKED", "tags": tags}


def _study_level(cells: Mapping[str, Any], primary: Sequence[core.CellSpec], loaded: Sequence[core.CellSpec], stage: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if primary:
        lab = {comp: {s.name: {cp: cells[s.name]["checkpoints"][cp][comp]["label"] for cp in labels.CHECKPOINTS} for s in primary} for comp in ("tree", "index")}
        diag = labels.combine(lab, [s.name for s in primary])
        out["r_diagnosis"] = {
            "stage_tag": core.STAGE_TAG[stage], "standing_tag": core.STANDING_TAG, "evaluable": diag.evaluable, "value": "EVALUABLE" if diag.evaluable else labels.NOT_EVALUABLE,
            "not_evaluable_cells": [list(x) for x in diag.not_evaluable],
            "components": {k: {"value": c.value, "at": c.at, "signature": [list(x) if isinstance(x, tuple) else x for x in c.signature]} for k, c in diag.components.items()},
            "pair": None if diag.pair is None else list(diag.pair), "recommended": diag.recommended, "no_read_time_cause_identified": diag.no_read_time_cause,
            "banner": labels.NO_READ_TIME_CAUSE if diag.no_read_time_cause else None,
        }  # fmt: skip
        out["_diagnosis_object"] = diag
    out["r_diagnosis_loaded"] = {
        "printed_only": True, "note": "R-DIAGNOSIS-LOADED has no combination rule and enters nothing; its labels recommend nothing; 'restored' there means restored to a full store",
        "cells": {s.name: {cp: {"tree": cells[s.name]["checkpoints"][cp]["tree"]["label"], "index": cells[s.name]["checkpoints"][cp]["index"]["label"]} for cp in labels.CHECKPOINTS if cp in cells[s.name]["checkpoints"]} for s in loaded},
    }  # fmt: skip
    return out


def public(analysis: Mapping[str, Any]) -> dict[str, Any]:
    """The analysis without its in-memory objects (what is written to ``analysis.json``)."""
    return {k: v for k, v in analysis.items() if not k.startswith("_")}


def analyze_all(a1: Mapping[str, Any], a2: Mapping[str, Any] | None, *, a2_complete: bool = True) -> dict[str, Any]:
    """A1's analysis, A2's (if any) and R-CONFIRM-TREE and R-CONFIRM-INDEX. R-CONFIRM does not change R-DIAGNOSIS."""
    d1 = a1.get("_diagnosis_object")
    d2 = None if a2 is None else a2.get("_diagnosis_object")
    if d1 is None:
        raise ValueError("A1's analysis has no primary cells")
    confirm = labels.r_confirm(d1, d2, a2_complete=a2_complete)
    return {
        "A1": public(a1), "A2": None if a2 is None else public(a2), "r_confirm": confirm,
        "statement_allowed": {
            "after_a1_alone": "the re-analysis points to ...", "caused_by_a_named_factor_at_read_time": labels.may_say_cause(confirm),
            "training_time_causes": False, "note": "neither A1 nor A2 supports a statement about training-time causes",
        },
    }  # fmt: skip
