# ruff: noqa: E501
"""P10IR synthetic registries with known answers (ADR-0029 section 13, 'Analysis tests'): for the analysis tests and for the rehearsal's analysis and report stages.

A tree prototype is a set of i values (bits per fact, both panels) for T0, T1, T1w, T2, T3 and F0, with CR8 of T0, built so that ``labels.tree_replicate`` returns a stated row; an index
prototype is i of F0 and of every feasible budget. ``fill_cell`` writes the read and item records of one checkpoint of one cell into a ``Registry``. Nothing here is a measurement of
anything: the values are typed here to have known answers.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core, labels
from .registry import Registry

F0_I = 4.0  # i of the flat reference in the prototypes (a_use about 0.9)

# row -> ({read: i on both panels}, cr8); F0 is F0_I
TREE_PROTOTYPES: dict[str, tuple[dict[str, float], float]] = {
    labels.NO_GAP: ({"T0": 3.8, "T1": 3.8, "T1w": 3.8, "T2": 3.8, "T3": 3.8}, 0.95),
    labels.PRIORS_AND_CANDIDATES: ({"T0": 2.0, "T1": 3.9, "T1w": 3.0, "T2": 3.9, "T3": 3.9}, 0.5),
    labels.PRIORS: ({"T0": 2.0, "T1": 3.9, "T1w": 3.5, "T2": 3.9, "T3": 2.1}, 0.5),
    labels.CANDIDATES: ({"T0": 2.0, "T1": 2.1, "T1w": 2.0, "T2": 3.9, "T3": 3.9}, 0.5),
    labels.JOINT: ({"T0": 2.0, "T1": 2.1, "T1w": 2.0, "T2": 3.9, "T3": 2.1}, 0.5),
    labels.EXACT_SEARCH_HARMS: ({"T0": 2.0, "T1": 2.1, "T1w": 2.0, "T2": 1.0, "T3": 2.1}, 0.5),
    labels.CONTENT: ({"T0": 2.0, "T1": 2.1, "T1w": 2.0, "T2": 2.0, "T3": 2.1}, 0.95),
    labels.NOT_IDENTIFIED: ({"T0": 2.0, "T1": 2.1, "T1w": 2.0, "T2": 2.0, "T3": 2.1}, 0.5),
}
# the PARTLY variants: closure 0.5 reached without RESTORED
TREE_PARTLY: dict[str, dict[str, float]] = {
    labels.PRIORS: {"T1": 3.0},
    labels.CANDIDATES: {"T3": 3.0},
    labels.JOINT: {"T2": 3.0},
}
# index row -> i of every feasible budget by budget (None: the budget is not feasible at the cell); F0 is F0_I
SPARSE_C_STAR = 256
ABOVE_C_STAR = 1024


def index_prototype(row: str, budgets: Sequence[int]) -> dict[int, float]:
    """i of I64@c for the feasible ``budgets`` such that the replicate label is ``row`` (c* = 256 for SPARSE, 1,024 for ONLY ABOVE 512, none for DOES NOT APPROACH)."""
    good, bad = 3.9, 2.0
    if row == labels.SPARSE_APPROACHES:
        return {c: good if c >= SPARSE_C_STAR else bad for c in budgets}
    if row == labels.ONLY_ABOVE_512:
        return {c: good if c >= ABOVE_C_STAR else bad for c in budgets}
    if row == labels.NOT_APPROACH:
        return dict.fromkeys(budgets, bad)
    raise ValueError(f"no index prototype for {row!r}")


@dataclass
class TreeSpec:
    i: dict[str, tuple[float, float]]
    cr8: float = 0.5
    tree_ok: bool = True
    f0_ok: bool = True


@dataclass
class IndexSpec:
    """The index reads of a replicate; F0 is the TreeSpec's (one F0 record per F-OQ checkpoint)."""

    i_budget: dict[int, tuple[float, float]] = field(default_factory=dict)
    index_ok: bool = True
    f0_ok: bool = True


def tree_spec(row: str, *, partly: bool = False) -> TreeSpec:
    """The TreeSpec that labels as ``row`` (also 'NOT EVALUABLE' and 'WEAK', and 'MIXED-PANEL')."""
    if row == labels.NOT_EVALUABLE:
        return TreeSpec({r: (F0_I, F0_I) for r in labels.TREE_READS}, tree_ok=False)
    if row == "WEAK":
        i = {r: (0.3, 0.3) for r in labels.TREE_READS}
        return TreeSpec(i, 0.5)
    if row == labels.MIXED_PANEL:
        i = {r: (3.0, 3.8) for r in ("T0", "T1", "T1w", "T2", "T3")} | {"F0": (F0_I, F0_I)}
        return TreeSpec(i, 0.5)
    base, cr8 = TREE_PROTOTYPES[row]
    base = dict(base) | (TREE_PARTLY.get(row, {}) if partly else {})
    return TreeSpec({r: (v, v) for r, v in base.items()} | {"F0": (F0_I, F0_I)}, cr8)


def index_spec(row: str, budgets: Sequence[int]) -> IndexSpec:
    if row == labels.NOT_EVALUABLE:
        return IndexSpec(i_budget={c: (3.9, 3.9) for c in budgets}, index_ok=False)
    if row == "WEAK":
        return IndexSpec({c: (0.3, 0.3) for c in budgets})
    return IndexSpec(i_budget={c: (v, v) for c, v in index_prototype(row, budgets).items()})


def _panels(i: tuple[float, float], n: int = 1000) -> dict[str, dict[str, float]]:
    from studies.p10s1 import core as s1

    out: dict[str, dict[str, float]] = {}
    for p, v in zip(labels.PANELS, i, strict=True):
        a = s1.i_to_a_use(v) if v > 0 else 0.03
        out[p] = {"n": n, "useful": int(round(a * n)), "correct": int(round(a * n)), "i": float(v), "a_use": float(a), "accuracy": float(a)}
    return out


def read_record(stage: str, cell: str, update: int, read: str, i: tuple[float, float], *, facts: Mapping[str, float] | None = None, pair: Mapping[str, float] | None = None, candidates: Mapping[str, float] | None = None, k: float = 100.0) -> dict[str, Any]:
    rec: dict[str, Any] = {**core.envelope("read"), "stage": stage, "cell": cell, "update": update, "read": read, "panels": _panels(i), "work": {"K": k}, "facts": dict(facts or {})}
    if pair is not None:
        rec["pair"] = dict(pair)
    if candidates is not None:
        rec["candidates"] = dict(candidates)
    return rec


def item_record(stage: str, cell: str, update: int, arm: str, gates: Mapping[str, tuple[str, bool]]) -> dict[str, Any]:
    return {
        **core.envelope("item"), "stage": stage, "cell": cell, "update": update, "arm": arm, "complete": True,
        "gates": {n: {"scope": scope, "passed": ok} for n, (scope, ok) in gates.items()}, "not_applicable": [],
    }  # fmt: skip


def fill_cell(
    reg: Registry, stage: str, spec: core.CellSpec, update: int, label_of: Any, tree_specs: Sequence[TreeSpec], index_specs: Sequence[IndexSpec], cfg: Mapping[str, Any] | None = None, *, share_changed: float = 0.4,
) -> None:  # fmt: skip
    """Write the records of both checkpoints (T-OQ and F-OQ) of the five replicates at ``update``."""
    cfg = cfg or core.load_config()
    seeds = core.i64_seeds(cfg)
    budgets = core.feasible_budgets(spec.slots, cfg)
    for d, (ts, ix) in enumerate(zip(tree_specs, index_specs, strict=True), start=1):
        t_label, f_label = label_of("T-OQ", spec, d), label_of("F-OQ", spec, d)
        reg.put_item(item_record(stage, t_label, update, "T-OQ", {"t0_path": ("tree", ts.tree_ok), "tree_recall": ("tree", True)}))
        reg.put_item(item_record(stage, f_label, update, "F-OQ", {"f0_counts": ("f0", ts.f0_ok and ix.f0_ok), "i256_counts": ("index", ix.index_ok), "index_rebuild": ("index", True)}))
        for r in ("T0", "T1", "T1w", "T2", "T3"):
            facts = {"cr8": ts.cr8, "cr1": ts.cr8, "sr8": ts.cr8, "am_c": ts.cr8, "am_s": ts.cr8, "share_span_both": 0.3} if r == "T0" else {"cr8": 1.0, "cr1": 1.0, "sr8": 0.9, "am_c": 1.0, "am_s": 0.9}
            pair = None if r == "T0" else {"share_selected_changed": share_changed, "tv_mean": 0.1}
            reg.put_read(read_record(stage, t_label, update, r, ts.i[r], facts=facts, pair=pair))
        for v in core.feasible_visits(spec.slots, cfg):
            if v not in (int(cfg["reads"]["visit_registered"]), spec.branches):
                for pr in core.PRIOR_STATES:
                    reg.put_read(read_record(stage, t_label, update, core.tv_name(v, pr), ts.i["T0"], facts={"cr8": 0.5}))
        reg.put_read(read_record(stage, f_label, update, "F0", ts.i["F0"], facts={"cr8": 1.0, "cr1": 1.0, "am_c": 1.0}))
        reg.put_read(read_record(stage, f_label, update, "I256@512", ix.i_budget.get(512, ts.i["F0"]), facts={"cr8": 0.8, "cr1": 0.8, "am_c": 0.8}, candidates={"mean": 512.0, "p99": 600.0}))
        for c in budgets:
            for s in seeds:
                reg.put_read(read_record(stage, f_label, update, core.i64_name(c, s), ix.i_budget[c], facts={"cr8": 0.7, "cr1": 0.7, "am_c": 0.7}, candidates={"mean": float(c) + 10, "p99": float(c) + 100}))


def default_rows(cell: core.CellSpec) -> tuple[str, str]:
    """A neutral (tree row, index row) for a cell that a test does not care about."""
    return labels.CONTENT, labels.NOT_APPROACH


def full_registry(
    stage: str,
    plan: Mapping[tuple[str, str], tuple[Sequence[str] | str, Sequence[str] | str]] | None = None,
    cfg: Mapping[str, Any] | None = None,
    label_of: Any = None,
    *,
    default: tuple[str, str] = (labels.CONTENT, labels.NOT_APPROACH),
) -> Registry:
    """A registry of every cell and checkpoint of the stage. ``plan[(cell name, checkpoint name)] = (tree rows, index rows)``: a row name or five of them (replicates 1..5); a tree row
    'PARTLY:<row>' asks for the PARTLY variant. Unlisted checkpoints get ``default``."""
    from .analysis import checkpoint_names, default_label_of

    cfg = cfg or core.load_config()
    label_of = label_of or default_label_of(stage, cfg)
    reg = Registry()
    specs = [s for s in core.cell_specs(cfg) if stage == core.STAGE_A1 or s.role == "primary"]
    for spec in specs:
        budgets = core.feasible_budgets(spec.slots, cfg)
        cps = checkpoint_names(spec)
        if stage == core.STAGE_A2:
            cps = {k: v for k, v in cps.items() if k in ("U_P", "RUN")}
        for cp, update in cps.items():
            trows, irows = (plan or {}).get((spec.name, cp), default)
            trow5 = [trows] * 5 if isinstance(trows, str) else list(trows)
            irow5 = [irows] * 5 if isinstance(irows, str) else list(irows)
            ts = [tree_spec(r.split(":", 1)[1], partly=True) if r.startswith("PARTLY:") else tree_spec(r) for r in trow5]
            ix = [index_spec(r, budgets) for r in irow5]
            fill_cell(reg, stage, spec, update, label_of, ts, ix, cfg)
    return reg


def plateau_series(cfg: Mapping[str, Any] | None = None, *, failing: Mapping[str, Sequence[int]] | None = None) -> dict[str, dict[str, list[dict[str, dict[int, float]] | None]]]:
    """Plateau series for the primary cells: every replicate plateaued (i flat at 3.5 over run/2 and run) except the replicates listed in ``failing[cell + ':' + arm]`` (still rising)."""
    cfg = cfg or core.load_config()
    out: dict[str, dict[str, list[dict[str, dict[int, float]] | None]]] = {}
    for spec in core.primary_cells(cfg):
        out[spec.name] = {}
        for arm in ("tree", "flat"):
            bad = set((failing or {}).get(f"{spec.name}:{arm}", ()))
            series = []
            for d in range(1, 6):
                top = 3.5 if d not in bad else 4.2
                series.append({p: {spec.run // 4: 3.0, spec.run // 2: 3.5, spec.run: top} for p in labels.PANELS})
            out[spec.name][arm] = series  # type: ignore[assignment]
    return out
