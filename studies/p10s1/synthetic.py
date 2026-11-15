# ruff: noqa: E501
"""P10S1 synthetic records of the whole registry (ADR-0021 section 10.2): on-disk ``train``, ``eval``, ``baseline`` and ``gates`` records in the layout of a real run directory, so
that ``analysis`` and ``report`` are exercised end to end on every verdict, class, label and outcome of section 8 (including missing, failed and non-finite cells and gates, and every
censoring case of section 8.8) without training anything. Nothing here is a measurement of a model or of a seed: the accuracies come from a declared function of (arm, cell,
replicate, update, panel) and the sizes of the facts are the registered ones. Rehearsal and unit tests only.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import core
from . import frozen as fz

AMaxFn = Callable[[str, int, int, int], float]  # (arm read, facts, slots, replicate) -> asymptotic a_use
TauFn = Callable[[str, int, int], float]  # (arm read, facts, slots) -> time constant in updates


def default_a_max(c: float = 0.7) -> AMaxFn:
    """The store holds ``c`` facts per slot at ceiling accuracy: a_use at most min(1, c x slots / facts); R2 and D-OQ at 1.0 (D-OQ at 0.15 so that it does not lead)."""

    def f(arm: str, facts: int, slots: int, rep: int) -> float:
        if arm == "R2":
            return 1.0
        if arm == "D-OQ":
            return 0.15
        return min(1.0, c * slots / facts)

    return f


def default_tau(base: float = 1500.0) -> TauFn:
    def f(arm: str, facts: int, slots: int) -> float:
        return 200.0 if arm == "R2" else base

    return f


@dataclass
class Scenario:
    name: str = "capacity"
    a_max: AMaxFn = field(default_factory=default_a_max)
    tau: TauFn = field(default_factory=default_tau)
    fail: set[str] = field(default_factory=set)  # cell labels whose train record has status failed
    missing: set[str] = field(default_factory=set)  # cell labels with no record at all
    nonfinite: set[str] = field(default_factory=set)  # cell labels whose eval records hold a non-finite count
    gates_ok: bool = True
    failed_gate: str = "g4"
    ivf_factor: float = 0.98
    jitter: float = 0.002
    knn_accuracy: float = 0.30
    movement_scale: Callable[[str, int], tuple[float, float]] = field(default=lambda arm, slots: (0.01 * (slots / 4096) ** 0.5, 0.008 * (slots / 4096) ** 0.5))
    leak_labels: set[str] = field(default_factory=set)
    dep_fail: Callable[[str, int, int, int], bool] = field(default=lambda arm, facts, slots, rep: False)  # memory disabled does not give chance: DEP fails


def a_use_of(scn: Scenario, arm: str, facts: int, slots: int, rep: int, update: int, panel: str) -> float:
    base = "F-OQ" if arm == "F-OQ-IVF" else arm
    a = scn.a_max(base, facts, slots, rep) * (1.0 - math.exp(-update / scn.tau(base, facts, slots)))
    if arm == "F-OQ-IVF":
        a *= scn.ivf_factor
    jitter = scn.jitter * (1 if panel == "A" else -1) * (((rep * 7 + slots // 4096 + facts // 2048) % 3) - 1)
    return float(min(1.0, max(0.0, a + jitter)))


def panel_counts(n: int, a: float, *, unseen_correct: int = 64) -> dict[str, Any]:
    useful = int(round(a * n))
    chance = int(round(n / 32))
    return {"n": n, "correct": useful, "useful": useful, "disabled_correct": chance, "shuffled_correct": chance, "swap_correct": chance, "unseen_n": 2048, "unseen_correct": unseen_correct}


def _read(scn: Scenario, cell: core.Cell, arm: str, rep: int, u: int, bad: bool, leak: bool) -> dict[str, Any]:
    panels: dict[str, Any] = {}
    broken = scn.dep_fail("F-OQ" if arm == "F-OQ-IVF" else arm, cell.facts, cell.slots, rep)
    for p in core.PANELS:
        c = panel_counts(cell.facts, a_use_of(scn, arm, cell.facts, cell.slots, rep, u, p), unseen_correct=900 if leak else 64)
        if broken:
            c["disabled_correct"] = c["correct"]
        if bad:
            c["useful"] = float("nan")
        if cell.arm == "D-OQ":
            c["shuffled_correct"] = None
        panels[p] = c
    if u == cell.u_p and cell.arm != "D-OQ":
        n = cell.facts
        panels["A"]["robustness_correct"] = {f"{k}_{m}": int(round(panels["A"]["correct"] * (1.0 - 0.1 * f))) for m in range(3) for k, f in (("drop5", 0.5), ("drop20", 1.0), ("noise0.1", 0.3), ("noise0.5", 0.8))}
        del n
    acc = panels["A"]["correct"] / cell.facts if not bad else 0.0
    sec = {h: {"n": cell.facts, "correct": int(round(cell.facts * acc * (0.9 if h == "H2" else 0.95)))} for h in ("H1", "H2")}
    base = "F-OQ" if arm == "F-OQ-IVF" else arm
    w: dict[str, int | float] = dict(core.work_formula(base, cell.slots)) if arm != "F-OQ-IVF" else {"W": 12000.0}
    rec: dict[str, Any] = {"panels": panels, "secondary": sec, "work": {"K": float(w.get("K") or 0), "V": float(w.get("V") or 0), "W": float(w["W"]), "queries": 100.0}}
    if arm == "F-OQ-IVF":
        rec["ivf_measured"] = {"W_mean": 12000.0 + 0.01 * cell.slots, "W_p99": 14000.0, "K_mean": 700.0, "recall_of_exhaustive_top8": 0.9}
    return rec


def write_cell(run_dir: Path, cell: core.Cell, fro: fz.Frozen, scn: Scenario) -> None:
    """The ``train.json`` and every expected ``eval.json`` of a cell, as a real run writes them."""
    if cell.label in scn.missing:
        return
    folder = core.cell_dir(run_dir, cell.label)
    updates = fro.snapshots(cell)
    rep = cell.draw
    cpu = fro.cost[cell.arm][str(cell.slots)]["cpu"]
    with_g, without_g = scn.movement_scale(cell.arm, cell.slots)
    meta = {}
    for u in updates:
        with_m, without_m = with_g * u, without_g * u
        total = with_m + without_m
        meta[str(u)] = {"cpu_seconds": cpu * u, "wall_seconds": cpu * u * 1.1, "peak_rss_bytes": 10**9, "movement": {"with_own_gradient": with_m, "without_own_gradient": without_m, "total": total, "share_without": without_m / total, "row_updates_with_gradient": 0.0}}
    stored = 4096 * 48 + 27392 + 1025
    train = {
        **core.envelope("train"), "label": cell.label, "arm": cell.arm, "facts": cell.facts, "slots": cell.slots, "draw": cell.draw, "init_seed": cell.init_seed, "u_p": cell.u_p, "status": "failed" if cell.label in scn.fail else "completed",
        "reason": "synthetic failure" if cell.label in scn.fail else None, "snapshots": list(updates), "snapshot_meta": meta, "snapshot_sha256": {}, "trainable_parameters": stored - 27392, "stored_parameters": stored,
        "identity": {"source_sha256": "synthetic", "spec_sha256": "synthetic", "config_sha256": "synthetic", "frozen_source_sha256": "synthetic"}, "mode": "registered", "movement": meta[str(updates[-1])]["movement"],
    }  # fmt: skip
    core.write_record(folder / "train.json", core.jsonable(train))
    for u in updates:
        bad = cell.label in scn.nonfinite and u == cell.u_p
        reads = {"main": _read(scn, cell, cell.arm, rep, u, bad, cell.label in scn.leak_labels)}
        if cell.arm == "F-OQ":
            reads["ivf"] = _read(scn, cell, "F-OQ-IVF", rep, u, bad, False)
        rec = {**core.envelope("eval"), "label": cell.label, "arm": cell.arm, "facts": cell.facts, "slots": cell.slots, "draw": cell.draw, "update": u, "reads": reads}
        core.write_record(core.eval_path(run_dir, cell.label, u), core.jsonable(rec))


def write_baselines(run_dir: Path, fro: fz.Frozen, scn: Scenario) -> None:
    for r in range(1, core.REPLICATES + 1):
        for facts in sorted({f for f, _ in core.grid_cells(fro.plan)}):
            panels: dict[str, Any] = {}
            for p in core.PANELS:
                n = facts
                k = int(round(scn.knn_accuracy * n))
                panels[p] = {
                    "KNN-W": {"correct": k, "n": n, "unseen_correct": 64, "unseen_n": 2048, "keys_scored_per_query": float(facts), "stored_values": float(224 * facts), "madds_per_query": float(224 * facts)},
                    "KNN-W-IVF": {"correct": int(0.9 * k), "n": n, "unseen_correct": 64, "unseen_n": 2048, "keys_scored_per_query": 700.0, "stored_values": float(224 * facts), "madds_per_query": 224.0 * 700},
                    "DICT": {"correct": n, "n": n, "probes_per_query": 1, "bits_per_fact": 25},
                    "NO-MEMORY": {"n": n, "correct": int(round(n / 32)), "unseen_n": 2048, "unseen_correct": 64},
                }
            core.write_record(run_dir / "baselines" / f"d{r}_f{facts}.json", {**core.envelope("baseline"), "draw": r, "facts": facts, "panels": panels})


def gates_record(scn: Scenario) -> dict[str, Any]:
    rec: dict[str, Any] = {**core.envelope("gates"), **{f"{k}_passed": True for k in ("g1", "g2", "g4", "g5", "g6", "g7", "g8", "g9")}}
    if not scn.gates_ok:
        rec[f"{scn.failed_gate}_passed"] = False
    return rec


def write_run(run_dir: Path, fro: fz.Frozen, scn: Scenario) -> None:
    """The records of the whole registry of ``fro.plan`` under ``scn``: one train record and every expected eval record of every registered cell (and of the seed block), the baselines of
    every draw and fact count, and the gates record."""
    run_dir.mkdir(parents=True, exist_ok=True)
    for cell in core.registered_cells(fro.plan, dense_rates=fro.dense_rates):
        if cell.kind == "LN":
            continue
        write_cell(run_dir, cell, fro, scn)
    write_baselines(run_dir, fro, scn)
    core.write_record(run_dir / "gates.json", gates_record(scn))
