# ruff: noqa: E501
"""P10S0 synthetic registries: in-memory ``RunData`` for the whole registry (every Q1 cell, WX and probe cells for a candidate), with success patterns chosen by the caller, and arm-selection records for
every P9-II outcome. Used by the tests that exercise analysis and report before the freeze (ADR-0020 section 10.2: "synthetic records of the full registry: every row of section 3.3, every class
under both criteria, every label, annotation and outcome of section 8, every block status, missing cells, failed gates, non-finite values, a replaced draw, and each cut of section 10.4").
Nothing here is a measurement of anything, and no registered or rehearsal seed is read.
"""

import math
from collections.abc import Callable, Mapping
from typing import Any

from studies.p9ii import classes as p9c
from studies.p9ii.classes import CellKey

from . import analysis, arm_selection, core
from . import classes as C

# patterns: 'ok' succeeds under both criteria; 'dep' fails only condition 6 (a_use) so it succeeds under P9-II's criteria; 'bad' fails conditions 1 and 3 under both
Pattern = Callable[[int, int], str]


ACCEPTED = {"accepted": True, "source": "docs/decisions/ADR-0019-robust-sparse-address-learning.md section 16", "quote": "yes I do, yes we can raise to 16 and I approve the package", "source_sha256": None}


def always(kind: str) -> Pattern:
    return lambda d, j: kind


def failing_cells(cells: set[CellKey], kind: str = "bad") -> Pattern:
    return lambda d, j: kind if (d, j) in cells else "ok"


def failing_draws(draws: set[int], kind: str = "bad") -> Pattern:
    """Both cells of every listed draw fail (a draw with both seeds failed)."""
    return lambda d, j: kind if d in draws else "ok"


def observation(kind: str, *, stability: float = 0.95, lm_rise: float = 0.12, nan: bool = False, acc: float = 0.97, bits: float = 3.0, auc: float = 0.8) -> C.SObservation:
    """One cell's observation: 'ok', 'dep' (condition 6 only), 'bad' (conditions 1 and 3)."""
    if kind == "ok":
        o = C.SObservation(acc, acc, True, True, acc, acc, False, 256, 0.01, 256, lm_rise, stability, math.nan, acc, acc, acc, bits, bits, auc)
    elif kind == "dep":
        o = C.SObservation(acc, acc, True, True, acc, acc, False, 256, 0.01, 256, lm_rise, stability, math.nan, acc, acc, 0.4 * acc, bits, bits, auc)
    elif kind == "bad":
        o = C.SObservation(0.05, 0.05, True, True, 0.05, 0.05, False, 3, 0.9, 256, lm_rise, stability, math.nan, 0.05, 0.0, 0.0)
    else:
        raise ValueError(kind)
    if nan:
        o = C.SObservation(**{**o.__dict__, "acc_a": math.nan, "a_use_a": math.nan})
    return o


def summary(collapsed: bool = False) -> p9c.TrainingSummary:
    cat = p9c.Category(p9c.COLLAPSED_RECOVERED if collapsed else p9c.NEVER_SEPARATED, 64 if collapsed else None, 1024 if collapsed else None, None, None)
    return p9c.TrainingSummary(cat, collapsed, 0.5, 1024 if collapsed else 128, not collapsed)


def _cell_data(label: str, ct: str, kind: str, *, learned: bool, unit: int, stability: float, lm_rise: float, collapsed: bool, nan: bool) -> analysis.CellData:
    obs = {u: observation(kind, stability=stability, lm_rise=lm_rise, nan=nan) for u in core.CELLTYPES[ct].readout_updates(unit)}
    return analysis.CellData(obs, summary(collapsed) if learned else None)


def a6_observation(usable: bool) -> C.SObservation:
    return C.SObservation(1.0 if usable else 0.3, 1.0 if usable else 0.3, True, True, 1.0, 1.0, False, 256, 0.01, 256, 0.1, 1.0, math.nan, 1.0, 1.0, 1.0)


def p9ii_class(label: str, failed_draws: int, evaluated_draws: int, *, lm: bool = False, cells: int | None = None) -> dict[str, Any]:
    """One P9-II class record as the arm-selection record holds it (``label``: RELIABLE, UNRELIABLE, FAILS or NOT_EVALUATED)."""
    base = label.split(" ")[0]
    n = evaluated_draws * 2
    succ = n - (failed_draws if cells is None else cells)
    return {"available": True, "class": label + (" (LM CAPABILITY REDUCED)" if lm else ""), "base_class": base, "lm_reduced": lm, "evaluated_cells": n, "successes": succ, "evaluated_draws": evaluated_draws, "failed_draws": failed_draws, "draw_counts": {}, "negative_control_failed": False}


def unavailable(reason: str = "synthetic") -> dict[str, Any]:
    return {"available": False, "reason": reason}


def committed_p9ii_classes() -> dict[str, dict[str, dict[str, Any]]]:
    """P9-II's committed record as ADR-0020 section 3.5 and the re-check read it."""
    return {
        "A0": {"4096": p9ii_class("UNRELIABLE", 6, 8), "16384": p9ii_class("RELIABLE", 0, 4)},
        "A5-D": {"4096": p9ii_class("RELIABLE", 0, 8), "16384": p9ii_class("RELIABLE", 0, 4)},
        "A2": {"4096": p9ii_class("FAILS", 8, 8), "16384": unavailable("no Stage 2 class at the 4U readout (the arm did not advance)")},
        "A1": {"4096": p9ii_class("RELIABLE", 0, 8), "16384": p9ii_class("UNRELIABLE", 2, 4)},
    }


def selection_record(facts: arm_selection.P9IIFacts | None = None, classes: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """An arm-selection record for synthetic P9-II facts (default: the committed record's: ADDRESSING-RELIABLE, Stage 2 COMPLETE, carried A0) and classes."""
    facts = facts or arm_selection.P9IIFacts(True, arm_selection.ADDRESSING_RELIABLE, "COMPLETE", "A0")
    cls = dict(classes or committed_p9ii_classes())
    mapping = arm_selection.evaluate_mapping(facts)
    return {
        "kind": "arm_selection", "study": core.STUDY, "schema": core.SCHEMA, "p9ii_inputs": {}, "mapping": mapping, "fourth_arm_printed": core.FOURTH_ARM_STRING, "mapping_printed": mapping["printed"], "arm_set_conflict": mapping["c4"] not in (None, "A5-D"),
        "override": arm_selection.override_part(),
        "calibrated": {"lambda": 1.0, "u_pre": 2048.0, "mu": 1.0, "k0_fraction": 0.125, "k0_fraction_used": False, "p9ii_record_hyper": {}, "equals_p9ii_record": True},
        "arm_set": list(core.CORE_LEARNED_ARMS), "references": list(core.REFERENCE_ARMS), "p9ii_classes": cls, "p9ii_negative_control": {"4096": False, "16384": False}, "candidates": arm_selection.candidate_arms(cls),
    }  # fmt: skip


def passing_gates() -> dict[str, Any]:
    return {**{f"{g}_passed": True for g in analysis.GATES}, "g2_by_draw": {str(k): True for k in range(1, 14)}, "harness_errors": []}


def make_run(
    patterns: Mapping[tuple[str, str], Pattern] | None = None,
    *,
    default: str = "ok",
    selection: Mapping[str, Any] | None = None,
    a6_bad: Mapping[str, set[int]] | None = None,
    cut3: bool = False,
    candidate: str | None = None,
    wx_pattern: Pattern | None = None,
    probe_kind: str | Pattern = "ok",
    probe_a6_bad: set[int] | None = None,
    gates: Mapping[str, Any] | None = None,
    missing: set[str] | None = None,
    nan_cells: set[str] | None = None,
    draw_plan: Mapping[str, Any] | None = None,
    stability: Mapping[tuple[str, str], float] | None = None,
    lm_rise: Mapping[tuple[str, str], float] | None = None,
    collapsed: set[tuple[str, str]] | None = None,
    block_status: Mapping[str, str] | None = None,
    failed_tasks: list[str] | None = None,
    frozen_mismatch: list[str] | None = None,
    unit: int = core.UPDATES,
    acceptance: Mapping[str, Any] | None = None,
) -> analysis.RunData:
    """The whole registry, in memory. ``patterns[(arm, celltype)]`` gives the kind ('ok', 'dep', 'bad') of each (draw, j); ``default`` for the others. ``a6_bad[celltype]``: draws whose A6 is below its floor.
    ``candidate``: also build the WX (``wx_pattern``) and probe cells of that arm. ``missing``: labels left out; ``nan_cells``: labels with non-finite values."""
    patterns = patterns or {}
    stability = stability or {}
    lm_rise = lm_rise or {}
    collapsed = collapsed or set()
    missing = missing or set()
    nan_cells = nan_cells or set()
    cells: dict[str, analysis.CellData] = {}
    for c in core.q1_cells(cut3):
        if c.label in missing:
            continue
        if c.arm == "A6":
            usable = c.draw not in (a6_bad or {}).get(c.celltype, set())
            cells[c.label] = analysis.CellData({u: a6_observation(usable) for u in c.ct.readout_updates(unit)})
            continue
        kind = patterns.get((c.arm, c.celltype), lambda d, j: default)(c.draw, c.seed_index) if c.arm != "A7" else "ok"
        cells[c.label] = _cell_data(c.label, c.celltype, kind, learned=c.learned, unit=unit, stability=stability.get((c.arm, c.celltype), 0.95), lm_rise=lm_rise.get((c.arm, c.celltype), 0.12), collapsed=(c.arm, c.celltype) in collapsed, nan=c.label in nan_cells)
    if candidate is not None:
        wx_pattern = wx_pattern or always("ok")
        for c in core.wx_cells(candidate):
            if c.label not in missing:
                cells[c.label] = _cell_data(c.label, c.celltype, wx_pattern(c.draw, c.seed_index), learned=True, unit=unit, stability=0.95, lm_rise=0.12, collapsed=False, nan=c.label in nan_cells)
        for c in core.probe_cells(candidate):
            if c.label in missing:
                continue
            if c.arm == "A6":
                cells[c.label] = analysis.CellData({u: a6_observation(c.draw not in (probe_a6_bad or set())) for u in c.ct.readout_updates(unit)})
            else:
                kind = probe_kind(c.draw, 0) if callable(probe_kind) else probe_kind
                cells[c.label] = _cell_data(c.label, c.celltype, kind, learned=True, unit=unit, stability=0.95, lm_rise=0.12, collapsed=False, nan=False)
    return analysis.RunData(
        cells, selection or selection_record(), list(failed_tasks or []), gates if gates is not None else passing_gates(), draw_plan, cut3, dict(block_status or {}), candidate, list(frozen_mismatch or []), unit, acceptance if acceptance is not None else ACCEPTED,
    )  # fmt: skip


def qualifying_patterns(arm: str, *, failed_draws_8k16k: set[int] | None = None) -> dict[tuple[str, str], Pattern]:
    """``arm`` succeeds everywhere except at 8K/16K on the listed draws (both seeds)."""
    out: dict[tuple[str, str], Pattern] = {}
    if failed_draws_8k16k:
        out[(arm, "8K/16K")] = failing_draws(failed_draws_8k16k)
    return out


def a0_unreliable(extra: Mapping[tuple[str, str], Pattern] | None = None) -> dict[tuple[str, str], Pattern]:
    """A0 fails at 2K/4K in 12 of 20 cells and at 8K/16K in 6 of 20 (the other arms succeed): the shape P9-II found at 4,096."""
    out: dict[tuple[str, str], Pattern] = {("A0", "2K/4K"): lambda d, j: "bad" if d <= 6 else "ok", ("A0", "8K/16K"): lambda d, j: "bad" if d <= 3 else "ok"}
    out.update(extra or {})
    return out


def tiny_corpus() -> bytes:
    """A random byte corpus long enough for the generator's template pool (tests and the DRY stage only)."""
    import torch

    g = torch.Generator().manual_seed(12)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


def tiny_data(spec: core.SeedSetSpec, real_facts: int, *, main_trained: int = 512) -> Any:
    """A tiny draw of ``spec``'s ``real_facts`` fact set (unit tests: test seeds 920001+ only; no registered or rehearsal seed is ever built here)."""
    from studies.p9 import data as d

    core.check_seed_set("dry", spec.name)
    return d.build_study_data(spec.seeds(real_facts), tiny_corpus(), sizes=d.DataSizes(main_trained=main_trained, unseen=64, lane_d_per_set=128))
