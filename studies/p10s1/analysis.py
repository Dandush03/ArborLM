# ruff: noqa: E501
"""P10S1 analysis (ADR-0021 section 8): from the raw records of a run directory to every verdict, class, label and both outcomes. ``load_study`` reads the records (a cell has a
record only if its ``train.json`` is completed and every snapshot the freeze requires has an ``eval.json``; a missing, failed or non-finite cell makes the study S1-INCOMPLETE and
no outcome is computed: the denominator is never reduced); ``analyze_study`` applies ``classes`` to them.

The analysis reads counts and frozen tables only. It never reads a seed, a launch argument or a figure of the lead's.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import classes as C
from . import core
from . import frozen as fz

PANEL_LIST = core.PANELS
REF_CELL = {2048: (2048, 4096), 8192: (8192, 16384), 32768: (32768, 32768)}  # R2's reference cell of each row (2K/256 uses the row of 2,048 facts)
ARM_READS = ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")
CAPACITY_REPLICATE_ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")
DECISION_ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ")


class BadRecord(ValueError):
    """A record holds a value that cannot be a count (non-finite, out of range, wrong type)."""


# --- records -> observations ----------------------------------------------------------------------------------------------------------------------
def _count(value: Any, upper: int, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= upper:
        raise BadRecord(f"{what} is not a count in 0..{upper}: {value!r}")
    return int(value)


def obs_from_panel(rec: Mapping[str, Any]) -> C.PanelObs:
    n = _count(rec["n"], 10**9, "n")

    def opt(k: str) -> int | None:
        return None if rec.get(k) is None else _count(rec[k], n, k)

    return C.PanelObs(
        n=n, correct=_count(rec["correct"], n, "correct"), useful=_count(rec["useful"], n, "useful"), disabled=opt("disabled_correct"), shuffled=opt("shuffled_correct"), swap=opt("swap_correct"),
        unseen_n=_count(rec["unseen_n"], 10**9, "unseen_n"), unseen_correct=_count(rec["unseen_correct"], rec["unseen_n"], "unseen_correct"),
    )  # fmt: skip


@dataclass
class CellData:
    """One cell as the analysis sees it (one arm read: F-OQ-IVF is F-OQ's cell read through the index)."""

    label: str
    arm: str
    facts: int
    slots: int
    draw: int
    u_p: int
    run: int
    memory: bool
    views: dict[str, C.View]
    meta: dict[int, dict[str, Any]]
    secondary: dict[int, dict[str, tuple[int, int]]]
    robust: dict[str, dict[str, float]]  # panel -> condition -> accuracy retained (both panels, section 22 (n))
    work: dict[int, dict[str, float]]
    ivf_measured: dict[int, dict[str, float]]
    deep: dict[str, Any]
    leakage: bool
    train: dict[str, Any]
    panel_counts: dict[int, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def movement(self, update: int) -> dict[str, float]:
        return {k: float(v) for k, v in self.meta[update]["movement"].items()}

    def cpu(self, update: int) -> float:
        return float(self.meta[update]["cpu_seconds"])


@dataclass
class Study:
    cells: dict[tuple[int, str, int, int], CellData] = field(default_factory=dict)
    seedblock: dict[tuple[int, int, int, int], CellData] = field(default_factory=dict)  # (draw, init seed, facts, slots)
    missing: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    baselines: dict[tuple[int, int], dict[str, Any]] = field(default_factory=dict)
    identities: dict[str, dict[str, str]] = field(default_factory=dict)

    def get(self, draw: int, arm: str, facts: int, slots: int) -> CellData:
        return self.cells[(draw, arm, facts, slots)]

    def has(self, draw: int, arm: str, facts: int, slots: int) -> bool:
        return (draw, arm, facts, slots) in self.cells


def _views(panels: Mapping[int, Mapping[str, Mapping[str, Any]]], run: int, u_p: int, memory: bool) -> dict[str, C.View]:
    return {p: C.View({u: obs_from_panel(panels[u][p]) for u in panels}, run, u_p, memory=memory) for p in PANEL_LIST}


def read_cell(run_dir: Path, cell: core.Cell, fro: fz.Frozen) -> list[CellData]:
    """The CellData of a registered cell (two for an F-OQ cell: F-OQ and F-OQ-IVF). Raises ``FileNotFoundError`` for a missing record and ``BadRecord`` for a bad one."""
    folder = core.cell_dir(run_dir, cell.label)
    train_path = folder / "train.json"
    if not train_path.is_file():
        raise FileNotFoundError(f"no train record for {cell.label}")
    train = core.read_record(train_path, "train")
    if train.get("status") != "completed":
        raise BadRecord(f"{cell.label}: train status {train.get('status')!r}")
    updates = fro.snapshots(cell)
    evals: dict[int, dict[str, Any]] = {}
    for u in updates:
        p = core.eval_path(run_dir, cell.label, u)
        if not p.is_file():
            raise FileNotFoundError(f"no eval record for {cell.label} at update {u}")
        evals[u] = core.read_record(p, "eval")
    meta = {int(u): m for u, m in train["snapshot_meta"].items()}
    for u in updates:
        if u not in meta:
            raise BadRecord(f"{cell.label}: no snapshot meta at {u}")
    out: list[CellData] = []
    reads = ["main"] + (["ivf"] if cell.arm == "F-OQ" and all("ivf" in e["reads"] for e in evals.values()) else [])
    for read in reads:
        arm = "F-OQ-IVF" if read == "ivf" else cell.arm
        panels = {u: e["reads"][read]["panels"] for u, e in evals.items()}
        memory = cell.arm != "D-OQ"
        views = _views(panels, cell.run_updates, cell.u_p, memory)
        leak = any(o.leakage for v in views.values() for o in v.obs.values())
        secondary = {u: {k: (int(v["correct"]), int(v["n"])) for k, v in e["reads"][read]["secondary"].items()} for u, e in evals.items()}
        robust: dict[str, dict[str, float]] = {}
        a_u = evals.get(cell.u_p)
        if a_u is not None:
            for pn in PANEL_LIST:
                pa = a_u["reads"][read]["panels"][pn]
                if "robustness_correct" in pa:
                    robust[pn] = {k: v / pa["n"] for k, v in pa["robustness_correct"].items()}
        deep = a_u["reads"][read].get("deep", {}) if a_u is not None else {}
        out.append(CellData(
            label=cell.label, arm=arm, facts=cell.facts, slots=cell.slots, draw=cell.draw, u_p=cell.u_p, run=cell.run_updates, memory=memory, views=views, meta=meta, secondary=secondary,
            robust=robust, work={u: e["reads"][read].get("work", {}) for u, e in evals.items()}, ivf_measured={u: e["reads"][read].get("ivf_measured", {}) for u, e in evals.items()},
            deep=deep, leakage=leak, train=train, panel_counts={u: {p: dict(e["reads"][read]["panels"][p]) for p in PANEL_LIST} for u, e in evals.items()},
        ))  # fmt: skip
    return out


def load_study(run_dir: Path, fro: fz.Frozen, *, include_seed_block: bool = True) -> Study:
    """Read every registered cell of the plan (and the seed block). Nothing is guessed: a cell that cannot be read is listed in ``missing`` or ``failed`` with its reason."""
    study = Study()
    for cell in core.registered_cells(fro.plan, dense_rates=fro.dense_rates):
        if cell.kind == "SB" and not include_seed_block:
            continue
        if cell.kind == "LN":
            study.missing.append(cell.label)
            study.reasons[cell.label] = "lane L (F-LA) has no implementation in this tree"
            continue
        try:
            datas = read_cell(run_dir, cell, fro)
        except FileNotFoundError as exc:
            study.missing.append(cell.label)
            study.reasons[cell.label] = str(exc)
            continue
        except (BadRecord, KeyError, ValueError, TypeError) as exc:
            study.failed.append(cell.label)
            study.reasons[cell.label] = f"{type(exc).__name__}: {exc}"
            continue
        for d in datas:
            if cell.kind == "SB":
                study.seedblock[(cell.draw, cell.init_seed, cell.facts, cell.slots)] = d
            else:
                study.cells[(cell.draw, d.arm, cell.facts, cell.slots)] = d
        study.identities[cell.label] = datas[0].train["identity"]
    for r in range(1, core.REPLICATES + 1):
        for facts in sorted({f for f, _ in core.grid_cells(fro.plan)}):
            p = run_dir / "baselines" / f"d{r}_f{facts}.json"
            if p.is_file():
                study.baselines[(r, facts)] = core.read_record(p, "baseline")
    return study


# --- engineering status ----------------------------------------------------------------------------------------------------------------------------
GATE_KEYS = ("g1", "g2", "g4", "g5", "g6", "g7", "g8", "g9")


def engineering_status(gates: Mapping[str, Any] | None, study: Study, expected_identity: Mapping[str, str] | None) -> dict[str, Any]:
    """Section 8.7 row 1: any engineering gate fails, or frozen and running code, config, launch scripts or data identities differ."""
    reasons: list[str] = []
    if gates is None:
        reasons.append("no gates record")
    else:
        reasons += [f"gate {k.upper()} failed" for k in GATE_KEYS if gates.get(f"{k}_passed") is not True]
    mismatched = []
    if expected_identity is not None:
        mismatched = sorted(label for label, ident in study.identities.items() if any(ident.get(k) != v for k, v in expected_identity.items()))
        if mismatched:
            reasons.append(f"identity differs from the freeze in {len(mismatched)} cell(s)")
    return {"failed": bool(reasons), "reasons": reasons, "identity_mismatched_cells": mismatched[:10]}


# --- REF, movement, small helpers -----------------------------------------------------------------------------------------------------------------
def ref_ok(study: Study, draw: int, facts: int) -> bool:
    """REF (section 8.1): R2's a_use at least 0.95 on both panels at U_P at the row's reference cell."""
    f, n = REF_CELL[facts]
    if not study.has(draw, "R2", f, n):
        return False
    c = study.get(draw, "R2", f, n)
    return all(core.REF_R2_MIN - C.EPS <= c.views[p].a_use(c.u_p) for p in PANEL_LIST)


def _movement_pair(small: CellData, large: CellData, u_small: int, u_large: int) -> dict[str, Any]:
    try:
        return {"small": small.movement(u_small), "large": large.movement(u_large), "ratios": C.movement_ratios(small.movement(u_small), large.movement(u_large)),
                "optimizer_assisted": C.optimizer_assisted(small.movement(u_small)["share_without"], large.movement(u_large)["share_without"])}  # fmt: skip
    except KeyError:
        return {"ratios": None}


def _mc_key(arm: str, step: core.Step) -> str:
    return f"cap|{'F-OQ' if arm == 'F-OQ-IVF' else arm}|{step.name}"


def _row_facts(plan: core.Plan) -> list[int]:
    return sorted({s.facts for s in plan.steps})


# transitions of the capacity line (C1 and N1 in 1K->4K, C2 and N2 in 4K->16K) and of the efficiency line (the control steps only, section 8.8)
def efficiency_transitions() -> dict[str, list[str]]:
    t: dict[str, list[str]] = {}
    for step in core.EFFICIENCY_STEPS:
        t.setdefault(step.transition, []).append(step.name)
    return t


# --- capacity line ------------------------------------------------------------------------------------------------------------------------------------
def capacity_steps(study: Study, fro: fz.Frozen) -> dict[str, dict[str, Any]]:
    """For every classified arm and every step of the plan: the verdict of each replicate (both panels), the step class and the movement ratios at U_P."""
    out: dict[str, dict[str, Any]] = {}
    for arm in CAPACITY_REPLICATE_ARMS:
        out[arm] = {}
        for step in fro.plan.steps:
            reps = []
            mc = fro.entry(_mc_key(arm, step))
            for r in range(1, core.REPLICATES + 1):
                small, large = study.get(r, arm, step.facts, step.small), study.get(r, arm, step.facts, step.large)
                ok = ref_ok(study, r, step.facts)
                panel_results = {p: C.capacity_panel(small.views[p], large.views[p], mc, ref_ok=ok, leakage=small.leakage or large.leakage) for p in PANEL_LIST}
                res = C.capacity_replicate(panel_results)
                reps.append({"replicate": r, "verdict": res.verdict, "detail": res.detail, "movement": _movement_pair(small, large, small.u_p, large.u_p), "ref_ok": ok})
            cls = C.capacity_step_class([str(x["verdict"]) for x in reps])
            out[arm][step.name] = {"class": cls, "transition": step.transition, "replicates": reps, "verdicts": [x["verdict"] for x in reps], "mc": {"status": mc.status, "multiplier": mc.multiplier}}
    return out


def transitions_of(plan: core.Plan) -> dict[str, list[str]]:
    t: dict[str, list[str]] = {}
    for step in plan.steps:
        t.setdefault(step.transition, []).append(step.name)
    return t


def largest_cell_a_use(study: Study, arm: str) -> bool:
    """a_use at least 0.80 at 32K/16K at its row's U_P in all 5 replicates (both panels; section 8.4 row 3, revision 5: the largest registered cell)."""
    return all(
        all(C.ge(study.get(r, arm, 32768, 16384).views[p].a_use(study.get(r, arm, 32768, 16384).u_p), core.ARM_A_USE_AT_LARGEST) for p in PANEL_LIST) for r in range(1, core.REPLICATES + 1)
    )


def _dense_cells(study: Study, fro: fz.Frozen, arm: str, steps: Sequence[core.Step]) -> tuple[list[C.DenseCell], list[str]]:
    """Dense comparison at the larger cell of each of the arm's CAPACITY STEPs, in the readings MU, MC and D-BEST (section 8.5)."""
    cells: list[C.DenseCell] = []
    missing: list[str] = []
    dense_cells = set(core.arm_cells(fro.plan, "D-OQ"))
    for step in steps:
        key = (step.facts, step.large)
        if key not in dense_cells:
            missing.append(core.cell_name(*key))
            continue
        reps: list[dict[str, dict[str, tuple[float, float | None, float]]]] = []
        e = fro.entry(f"dense|{'F-OQ' if arm == 'F-OQ-IVF' else arm}|{core.cell_name(*key)}")
        for r in range(1, core.REPLICATES + 1):
            a, dn = study.get(r, arm, *key), study.get(r, "D-OQ", *key)
            per: dict[str, dict[str, tuple[float, float | None, float]]] = {"MU": {}, "D-BEST": {}}
            if e.ok():
                per["MC"] = {}
            for p in PANEL_LIST:
                u_p = a.u_p
                d_mu, r_mu = C.dense_reading(a.views[p].i(u_p), dn.views[p].i(u_p), a.views[p].obs[u_p].n)
                per["MU"][p] = (d_mu, r_mu, dn.views[p].a_use(u_p))
                if e.ok():
                    ia, idn = a.views[p].i(int(e.small_update)), dn.views[p].i(int(e.large_update))  # type: ignore[arg-type]
                    d_mc, r_mc = C.dense_reading(ia, idn, a.views[p].obs[u_p].n)
                    per["MC"][p] = (d_mc, r_mc, dn.views[p].a_use(int(e.large_update)))  # type: ignore[arg-type]
                best, at = dn.views[p].i_star(dn.run)
                d_b, r_b = C.dense_reading(a.views[p].i(u_p), best, a.views[p].obs[u_p].n)
                per["D-BEST"][p] = (d_b, r_b, dn.views[p].a_use(at))
            reps.append(per)
        cells.append(C.DenseCell(step.name, reps, "OK" if e.ok() else e.status, e.annotation))
    return cells, missing


def work_label_for(study: Study, arm: str, step: core.Step) -> dict[str, Any]:
    """SUBLINEAR or LINEAR KEY SCORING for a step: analytic W (section 7.4; gate G7 equates it with the counters), measured for F-OQ-IVF (the mean W per query on Panel A at both
    cells in every replicate; the 99th percentile is printed beside it)."""
    if arm == "F-OQ-IVF":
        worst = 0.0
        p99: list[float] = []
        for r in range(1, core.REPLICATES + 1):
            s, large = study.get(r, arm, step.facts, step.small), study.get(r, arm, step.facts, step.large)
            ws, wl = s.ivf_measured[s.u_p]["W_mean"], large.ivf_measured[large.u_p]["W_mean"]
            worst = max(worst, wl / ws)
            p99.append(large.ivf_measured[large.u_p].get("W_p99", math.nan))
        return {"label": C.SUBLINEAR if C.le(worst, core.SUBLINEAR_FACTOR) else C.LINEAR_KEY_SCORING, "worst_ratio": worst, "w_p99_large": p99, "basis": "measured mean W per query on Panel A, every replicate"}
    ws = core.work_formula(arm, step.small)["W"]
    wl = core.work_formula(arm, step.large)["W"]
    return {"label": C.active_work_label(ws, wl), "w_small": ws, "w_large": wl, "ratio": wl / ws, "basis": "analytic (section 7.4)"}


def capacity_arms(study: Study, fro: fz.Frozen, steps: Mapping[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    trans = transitions_of(fro.plan)
    arms: dict[str, dict[str, Any]] = {}
    for arm in CAPACITY_REPLICATE_ARMS:
        classes = {s: steps[arm][s]["class"] for s in steps[arm]}
        directed = [t for t in fro.no_loaded_transitions if t in trans]
        # a transition the human lead directed to run with no loaded row is CAPACITY NOT TESTED: its steps count as NOT LOADED, so no arm is CAPACITY_SUPPORTED (section 22 m13)
        effective = {s: (C.NOT_LOADED if any(st.name == s and st.transition == t for st in fro.plan.steps for t in directed) else c) for s, c in classes.items()}
        cls = C.capacity_arm_class(effective, trans, largest_cell_a_use(study, arm))
        cap_steps = [s for s in fro.plan.steps if classes[s.name] == C.CAPACITY_STEP]
        dense_cells, missing = _dense_cells(study, fro, arm, cap_steps)
        # a CAPACITY STEP with no D-OQ read cannot by itself support CAPACITY_SUPPORTED: every transition needs one with a read
        dense = C.dense_label(dense_cells, missing)
        works = {s.name: work_label_for(study, arm, s) for s in cap_steps}
        read_transitions = {t: any(s.transition == t and classes[s.name] == C.CAPACITY_STEP and core.cell_name(s.facts, s.large) not in missing for s in fro.plan.steps) for t in trans}
        dense_label = dense["label"]
        if cls == C.CAPACITY_SUPPORTED and not all(read_transitions.values()) and dense_label != C.DENSE_AHEAD:  # DENSE AHEAD takes precedence over every other label (m1)
            dense_label = C.DENSE_NOT_READ
        matches = None
        if dense_label == C.DENSE_MATCHES:
            parts = []
            for s in cap_steps:
                if core.cell_name(s.facts, s.large) in missing:
                    continue
                w_arm = works[s.name].get("w_large") if arm != "F-OQ-IVF" else max(study.get(r, arm, s.facts, s.large).ivf_measured[study.get(r, arm, s.facts, s.large).u_p]["W_mean"] for r in range(1, core.REPLICATES + 1))
                w_dense = core.work_formula("D-OQ", s.large)["W"]
                parts.append(f"{s.name}: " + C.DENSE_MATCHES_SENTENCE.format(w_arm=f"{w_arm:g}", w_dense=f"{w_dense:g}"))
            matches = "; ".join(parts)
        arms[arm] = {
            "class": cls, "dense": dense_label, "dense_detail": dense, "dense_matches_sentence": matches, "effective_step_classes": effective, "capacity_steps": [s.name for s in cap_steps], "work": works,
            "work_label": C.SUBLINEAR if works and all(w["label"] == C.SUBLINEAR for w in works.values()) else (C.LINEAR_KEY_SCORING if works else None),
            "undertrained_h8": [c for c in fro.h8_undertrained] if arm == "H8" and fro.h8_undertrained else [],
        }  # fmt: skip
        if arm == "F-OQ":
            arms[arm]["work_label"] = C.LINEAR_KEY_SCORING if works else None
    return arms


def hierarchy(study: Study, fro: fz.Frozen) -> dict[str, Any]:
    """T-OQ against F-OQ-IVF on I_use at 8K/4K and 32K/16K (the larger cells of the loaded steps) at the row's U_P; T-OQ against exhaustive F-OQ beside it."""
    cells = ((8192, 4096), (32768, 16384))
    ratios: list[dict[str, dict[str, float]]] = []
    exhaustive: list[dict[str, dict[str, float]]] = []
    for r in range(1, core.REPLICATES + 1):
        per: dict[str, dict[str, float]] = {}
        ex: dict[str, dict[str, float]] = {}
        for f, n in cells:
            t, v, e = study.get(r, "T-OQ", f, n), study.get(r, "F-OQ-IVF", f, n), study.get(r, "F-OQ", f, n)
            per[core.cell_name(f, n)] = {p: _ratio(t.views[p].i(t.u_p), v.views[p].i(v.u_p)) for p in PANEL_LIST}
            ex[core.cell_name(f, n)] = {p: _ratio(t.views[p].i(t.u_p), e.views[p].i(e.u_p)) for p in PANEL_LIST}
        ratios.append(per)
        exhaustive.append(ex)
    return {"label": C.hierarchy_label(ratios), "ratios_vs_ivf": ratios, "ratios_vs_exhaustive": exhaustive}


def _ratio(a: float, b: float) -> float:
    """I_use ratio of two cells with the same facts (the ratio of i); a zero denominator is +inf for a positive numerator and 1 for two zeros."""
    if b <= 0:
        return math.inf if a > 0 else 1.0
    return a / b


def baseline_i(study: Study, r: int, facts: int, which: str, panel: str) -> float | None:
    rec = study.baselines.get((r, facts))
    if rec is None:
        return None
    x = rec["panels"][panel][which]
    return core.bits_per_fact(int(x["correct"]), int(x["n"]))


def conventional(study: Study) -> dict[str, Any]:
    """CONVENTIONAL RETRIEVAL SUFFICES per arm (KNN-W or KNN-W-IVF within 0.25 of the arm or above it, both panels, at least 4 replicates, 32K/16K), and the baselines' i."""
    out: dict[str, Any] = {"dict_dominates_on_this_task": "DICT DOMINATES ON THIS TASK", "arms": {}, "baselines_32768": {}}
    for arm in DECISION_ARMS:
        i_arm, i_knn, i_ivf = [], [], []
        ok = True
        for r in range(1, core.REPLICATES + 1):
            c = study.get(r, arm, 32768, 16384)
            a = {p: c.views[p].i(c.u_p) for p in PANEL_LIST}
            k = {p: baseline_i(study, r, 32768, "KNN-W", p) for p in PANEL_LIST}
            v = {p: baseline_i(study, r, 32768, "KNN-W-IVF", p) for p in PANEL_LIST}
            if any(x is None for x in (*k.values(), *v.values())):
                ok = False
                break
            i_arm.append(a)
            i_knn.append({p: float(x) for p, x in k.items() if x is not None})
            i_ivf.append({p: float(x) for p, x in v.items() if x is not None})
        out["arms"][arm] = {"suffices": bool(ok and C.conventional_suffices(i_arm, i_knn, i_ivf)), "evaluated": ok}
    for r in range(1, core.REPLICATES + 1):
        rec = study.baselines.get((r, 32768))
        if rec is not None:
            out["baselines_32768"][str(r)] = {p: {k: v for k, v in rec["panels"][p].items()} for p in PANEL_LIST}
    return out


def _sat_side(study: Study, r: int, arm: str, size: int) -> C.SatSide | None:
    f, n = core.SATURATION_CELLS[size]
    if not study.has(r, arm, f, n):
        return None
    c = study.get(r, arm, f, n)
    return C.SatSide(c.views, f, n)  # views are read at the cell's run length U_L


def b_ranges(arms: Mapping[str, Any]) -> dict[str, dict[str, tuple[float, float]]]:
    """b(N), bits per slot of the saturation cell of each size, as the range over replicates and panels of every pair read, per arm (section 8.10)."""
    out: dict[str, dict[str, tuple[float, float]]] = {}
    for arm, v in arms.items():
        vals: dict[int, list[float]] = {}
        for p in v["pairs"].values():
            for rep in p["replicates"]:
                for side in ("small", "large"):
                    det = rep["detail"].get(side)
                    if det:
                        vals.setdefault(int(det["slots"]), []).extend(float(x) for x in det["b_bits_per_slot"].values())
        out[arm] = {str(n): (min(x), max(x)) for n, x in sorted(vals.items())}
    return out


def b_text(ranges: Mapping[str, Mapping[str, tuple[float, float]]]) -> str:
    return "b(N) bits per slot: " + "; ".join(f"{arm} " + ", ".join(f"{n} slots {lo:.2f}-{hi:.2f}" for n, (lo, hi) in r.items()) for arm, r in ranges.items() if r)


def saturation_line(study: Study, fro: fz.Frozen, dense_labels: Mapping[str, str] | None = None) -> dict[str, Any]:
    """The saturation line (section 8.10): per arm and registered pair the verdict of each replicate (rho, b(N), the last doubling's gain and full / not full per panel and size), the pair class,
    the arm class and the outcome; the separability figures of section 7.3 at each saturation cell beside every rho. A pair that uses 2K/256 when the plan does not run it is NOT FULL
    ('256 NOT MEASURED — NOT FULL WITHIN CEILING')."""
    arms: dict[str, Any] = {}
    for arm in core.SATURATION_ARMS:
        pairs: dict[str, Any] = {}
        classes_: list[str] = []
        for n, m in core.SATURATION_PAIRS[arm]:
            key = f"{n}→{m}"
            unloaded = {size for t, size in (("1K→4K", 1024), ("4K→16K", 4096)) if t in fro.no_loaded_transitions}  # a transition fixed as not tested: its loaded cell is NOT LOADED WITHIN ITS CEILING, so every pair that uses it is NOT FULL (section 10.1 item 0b; audit m5)
            if n in unloaded or m in unloaded:
                pairs[key] = {"class": C.NOT_FULL, "verdicts": None, "note": "the loaded cell of this size is fixed as not loaded (transition fixed as not tested)", "replicates": []}
                classes_.append(C.NOT_FULL)
                continue
            if n == core.SATURATION_ONLY_CELL[1] and not fro.plan.sat256:
                pairs[key] = {"class": C.NOT_FULL, "verdicts": None, "note": C.NOT_MEASURED_256, "replicates": []}
                classes_.append(C.NOT_FULL)
                continue
            reps = []
            for r in range(1, core.REPLICATES + 1):
                small, large = _sat_side(study, r, arm, n), _sat_side(study, r, arm, m)
                if small is None or large is None:
                    reps.append({"replicate": r, "verdict": C.NOT_EVALUATED, "detail": {"reason": "cell missing"}})
                    continue
                ok = ref_ok(study, r, small.facts) and ref_ok(study, r, large.facts)
                cs, cl = study.get(r, arm, small.facts, small.slots), study.get(r, arm, large.facts, large.slots)
                res = C.saturation_pair(small, large, ref_ok=ok, leakage=cs.leakage or cl.leakage)
                reps.append({"replicate": r, "verdict": res.verdict, "detail": res.detail})
            cls = C.saturation_pair_class([str(x["verdict"]) for x in reps])
            pairs[key] = {"class": cls, "verdicts": [x["verdict"] for x in reps], "replicates": reps}
            classes_.append(cls)
        arms[arm] = {"pairs": pairs, "class": C.saturation_arm_class(classes_), "pairs_read": [f"{n}→{m}" for n, m in core.SATURATION_PAIRS[arm]]}
    separability: dict[str, Any] = {}
    for size, (f, n) in core.SATURATION_CELLS.items():
        if size == core.SATURATION_ONLY_CELL[1] and not fro.plan.sat256:
            continue
        for r in range(1, core.REPLICATES + 1):
            if study.has(r, "F-OQ", f, n):
                separability[f"{core.cell_name(f, n)} replicate {r}"] = study.get(r, "F-OQ", f, n).deep.get("separability")
    ranges = b_ranges(arms)
    first_sep = next(iter(sorted(separability.items())), None)
    sep_text = "separability " + (f"{first_sep[0]}: " + ", ".join(f"{k} {x:.3f}" for k, x in first_sep[1].items() if isinstance(x, int | float)) if first_sep and isinstance(first_sep[1], dict) else "see RESULTS.md")
    dense_text = "dense at saturation: " + ", ".join(f"{a} {lab}" for a, lab in (dense_labels or {}).items())
    outcome = C.saturation_outcome({a: v["class"] for a, v in arms.items()}, engineering_failed=False, incomplete=False, pairs_read={a: v["pairs_read"] for a, v in arms.items()}, sat256_absent=not fro.plan.sat256, details=[b_text(ranges), sep_text, dense_text, fro.s0_status, core.ORACLE_SENTENCE])
    return {"arms": arms, "separability": separability, "b_ranges": {a: {n: list(r) for n, r in v.items()} for a, v in ranges.items()}, "outcome": outcome._asdict()}


def dense_saturation(study: Study, fro: fz.Frozen, arm: str) -> dict[str, Any]:
    """The dense label at saturation for ``arm`` at the two loaded cells (section 8.5): the arm and D-OQ both read at U_L; D-OQ's plateau status at U_L; D-OQ's cost per update at least the arm's in
    both cost measures (the frozen cost tables)."""
    cells: list[C.SatDenseCell] = []
    for f, n in core.LOADED_CELLS:
        base = "F-OQ" if arm == "F-OQ-IVF" else arm
        reps: list[dict[str, tuple[float, float | None]]] = []
        status: list[dict[str, str]] = []
        for r in range(1, core.REPLICATES + 1):
            a, dn = study.get(r, arm, f, n), study.get(r, "D-OQ", f, n)
            per: dict[str, tuple[float, float | None]] = {}
            st: dict[str, str] = {}
            for p in PANEL_LIST:
                ia, idn = a.views[p].i_star(a.run)[0], dn.views[p].i_star(dn.run)[0]
                d, ratio = C.dense_reading(ia, idn, a.views[p].obs[a.u_p].n)
                per[p] = (d, ratio)
                st[p] = dn.views[p].plateau_status()
            reps.append(per)
            status.append(st)
        ca, cd = fz.costs_of(fro.cost, base, n), fz.costs_of(fro.cost, "D-OQ", n)
        cells.append(C.SatDenseCell(core.cell_name(f, n), reps, status, all(cd[m] >= ca[m] - C.EPS for m in ("cpu", "madds"))))
    return C.dense_at_saturation(cells)


def robustness(study: Study, fro: fz.Frozen) -> dict[str, Any]:
    """RISES WITH SLOTS, FALLS or UNCHANGED per arm and step (cells with a_use at least 0.5), by accuracy retained under 20% slot dropout at U_P (mean of three masks), read on Panel A and
    printed for both panels (section 22 (n)); descriptive."""
    out: dict[str, Any] = {}
    for arm in ("F-OQ", "T-OQ", "H8"):
        out[arm] = {}
        for step in fro.plan.steps:
            per_panel: dict[str, Any] = {}
            for panel in PANEL_LIST:
                rises: list[float] = []
                assessed = True
                for r in range(1, core.REPLICATES + 1):
                    s_c, large = study.get(r, arm, step.facts, step.small), study.get(r, arm, step.facts, step.large)
                    if not (panel in s_c.robust and panel in large.robust and C.ge(s_c.views[panel].a_use(s_c.u_p), core.A_USE_FLOOR_CAPACITY) and C.ge(large.views[panel].a_use(large.u_p), core.A_USE_FLOOR_CAPACITY)):
                        assessed = False
                        break

                    def kept(c: CellData, panel: str = panel) -> float:
                        vals = [v for k, v in c.robust[panel].items() if k.startswith("drop20_")]
                        return sum(vals) / len(vals)

                    rises.append(kept(large) - kept(s_c))
                per_panel[panel] = {"label": C.robustness_label(rises) if assessed else "NOT ASSESSED (a_use below 0.5)", "rises": rises}
            out[arm][step.name] = {**per_panel["A"], "panel_B": per_panel["B"]}
    return out


def held_out(study: Study, fro: fz.Frozen) -> dict[str, Any]:
    """HELD-OUT FRAGILE (annotation): the arm's ratio of H1 (or H2) accuracy to Panel A accuracy below 0.90 x R2's ratio of the same replicate at the row's reference cell, at U_P."""
    out: dict[str, Any] = {}
    for (draw, arm, facts, slots), c in sorted(study.cells.items()):
        if arm in ("R2", "D-OQ", "F-OQ-IVF") or draw != 1:
            continue
        flags = {}
        for h in ("H1", "H2"):
            ratios = []
            for r in range(1, core.REPLICATES + 1):
                cc = study.get(r, arm, facts, slots)
                if facts not in REF_CELL or not study.has(r, "R2", *REF_CELL[facts]):
                    continue
                ref = study.get(r, "R2", *REF_CELL[facts])
                a_acc = cc.panel_counts[cc.u_p]["A"]["correct"] / max(1, cc.panel_counts[cc.u_p]["A"]["n"])
                r_acc = ref.panel_counts[ref.u_p]["A"]["correct"] / max(1, ref.panel_counts[ref.u_p]["A"]["n"])
                hc, hn = cc.secondary[cc.u_p][h]
                rc, rn = ref.secondary[ref.u_p][h]
                if a_acc > 0 and r_acc > 0 and rn > 0 and hn > 0:
                    ratios.append((hc / hn / a_acc, rc / rn / r_acc))
            flags[h] = sum(1 for a, b in ratios if C.held_out_fragile(a, b)) >= core.PAIRED_MOST if ratios else None
        out[f"{arm} {core.cell_name(facts, slots)}"] = {"HELD-OUT FRAGILE": flags}
    return out


def seed_block(study: Study, fro: fz.Frozen) -> dict[str, Any]:
    """Per cell and readout (U_P and U_run), the spread of i over the three initialization seeds of a seed-block draw against the spread over the five draws (section 6.2)."""
    out: dict[str, Any] = {"draws": list(fro.plan.seed_block_draws), "cells": {}}
    for draw in fro.plan.seed_block_draws:
        for f, n in core.GRID_CELLS:
            main = study.cells.get((draw, "F-OQ", f, n))
            extras = [c for (d, _i, ff, nn), c in sorted(study.seedblock.items()) if d == draw and ff == f and nn == n]
            if main is None or not extras:
                continue
            for readout, u in (("U_P", main.u_p), ("U_run", main.run)):
                within = [main.views["A"].i(u), *[e.views["A"].i(u) for e in extras]]
                across = [study.get(r, "F-OQ", f, n).views["A"].i(u) for r in range(1, core.REPLICATES + 1)]
                sw, sa = max(within) - min(within), max(across) - min(across)
                out["cells"][f"draw{draw} {core.cell_name(f, n)} {readout}"] = {"spread_within_draw": sw, "spread_across_draws": sa, "dominates": "init seed" if sw > sa else "data draw"}
    return out


# --- efficiency line --------------------------------------------------------------------------------------------------------------------------------------
def _movement_text(steps: Mapping[str, Mapping[str, Any]], arm_classes: Mapping[str, str]) -> str:
    """The row-movement ratios (larger over smaller total value-row movement at U_P) of the FASTER STEPs of the supported arms, printed with EFFICIENCY-POSITIVE (section 7.3)."""
    parts = []
    for arm, cls in arm_classes.items():
        if cls != "EFFICIENCY_SUPPORTED":
            continue
        for name, st in steps[arm].items():
            if st["class"] == "FASTER STEP":
                vals = [r["movement_at_U_P"]["ratios"]["total"] for r in st["replicates"] if r["movement_at_U_P"].get("ratios") and r["movement_at_U_P"]["ratios"]["total"] is not None]
                parts.append(f"{arm} {name} row-movement ratio " + (f"{min(vals):.2f}-{max(vals):.2f}" if vals else "not available"))
    return "; ".join(parts) or "row-movement ratios: none (no supported arm)"


def efficiency_line(study: Study, fro: fz.Frozen) -> dict[str, Any]:
    """u_T for every F-OQ and T-OQ cell, the step verdict of each replicate, the step and arm classes, the dense label at the larger cell of each FASTER STEP, the outcome."""
    trans = efficiency_transitions()
    steps: dict[str, dict[str, Any]] = {}
    for arm in core.EFFICIENCY_ARMS:
        steps[arm] = {}
        for step in core.EFFICIENCY_STEPS:
            reps = []
            for r in range(1, core.REPLICATES + 1):
                small, large = study.get(r, arm, step.facts, step.small), study.get(r, arm, step.facts, step.large)
                us, ul = C.u_t(list(small.views.values())), C.u_t(list(large.views.values()))
                ok = ref_ok(study, r, step.facts)
                res = C.efficiency_step(us, ul, ref_ok=ok, leakage=small.leakage or large.leakage, run_small=small.run, run_large=large.run, cost_small=fz.costs_of(fro.cost, arm, step.small), cost_large=fz.costs_of(fro.cost, arm, step.large))
                hit_s = us.s_hit if us.s_hit is not None else small.run
                hit_l = ul.s_hit if ul.s_hit is not None else large.run
                move = _movement_pair(small, large, small.u_p, large.u_p)
                move_hit = _movement_pair(small, large, hit_s if hit_s in small.meta else small.run, hit_l if hit_l in large.meta else large.run)
                reps.append({"replicate": r, "verdict": res.verdict, "detail": res.detail, "movement_at_U_P": move, "movement_at_hit": move_hit, "optimizer_assisted": bool(move.get("optimizer_assisted") or move_hit.get("optimizer_assisted"))})
            steps[arm][step.name] = {"class": C.efficiency_step_class([str(x["verdict"]) for x in reps]), "replicates": reps, "verdicts": [x["verdict"] for x in reps]}
    arm_classes = {arm: C.efficiency_arm_class({s: steps[arm][s]["class"] for s in steps[arm]}, trans) for arm in core.EFFICIENCY_ARMS}
    dense: dict[str, str] = {}
    dense_detail: dict[str, Any] = {}
    dense_cells = set(core.arm_cells(fro.plan, "D-OQ"))
    for arm in core.EFFICIENCY_ARMS:
        faster = [s for s in core.EFFICIENCY_STEPS if steps[arm][s.name]["class"] == "FASTER STEP"]
        if arm_classes[arm] != "EFFICIENCY_SUPPORTED" and not faster:
            continue
        labels = []
        for step in faster:
            key = (step.facts, step.large)
            if key not in dense_cells:
                labels.append(C.DENSE_NOT_READ)
                continue
            arm_ut = [[C.u_t([v]).ut for v in study.get(r, arm, *key).views.values()] for r in range(1, core.REPLICATES + 1)]  # one u_T per panel: a blocking label counts either panel
            d_ut = [[C.u_t([v]).ut for v in study.get(r, "D-OQ", *key).views.values()] for r in range(1, core.REPLICATES + 1)]
            labels.append(C.dense_faster(arm_ut, d_ut, fz.costs_of(fro.cost, arm, step.large), fz.costs_of(fro.cost, "D-OQ", step.large)))
        if "DENSE FASTER" in labels:
            dense[arm] = "DENSE FASTER"
        elif C.DENSE_SPEED_UNDECIDED in labels:
            dense[arm] = C.DENSE_SPEED_UNDECIDED
        elif labels and all(x == C.DENSE_NOT_READ for x in labels):
            dense[arm] = C.DENSE_NOT_READ
        else:
            dense[arm] = "DENSE NOT FASTER"
        dense_detail[arm] = labels
    details = [_movement_text(steps, arm_classes), fro.s0_status, core.ORACLE_SENTENCE]
    outcome = C.efficiency_outcome(arm_classes, dense, engineering_failed=False, incomplete=False, details=details)
    return {"steps": steps, "arm_classes": arm_classes, "dense": dense, "dense_detail": dense_detail, "outcome": outcome._asdict()}


# --- cost table -------------------------------------------------------------------------------------------------------------------------------------------------
def cost_rows(study: Study, fro: fz.Frozen) -> list[dict[str, Any]]:
    """Per cell (replicate 1): I_use, trainable and stored parameters and bytes, retained bits per stored byte, K, V, W, updates and exposures per fact, CPU seconds and analytic
    multiply-adds to U_P and U_run (section 7.6). Logical counts and measured CPU seconds; no efficiency claim."""
    rows: list[dict[str, Any]] = []
    for (draw, arm, facts, slots), c in sorted(study.cells.items()):
        if draw != 1:
            continue
        base = "F-OQ" if arm == "F-OQ-IVF" else arm
        train = c.train
        i_use = {p: facts * c.views[p].i(c.u_p) for p in PANEL_LIST}
        stored_bytes = 4 * int(train["stored_parameters"])
        w = c.ivf_measured.get(c.u_p, {}).get("W_mean") if arm == "F-OQ-IVF" else core.work_formula(base, slots)["W"]
        mad = fz.analytic_madds_per_update(base, slots)
        rows.append({
            "arm": arm, "cell": core.cell_name(facts, slots), "facts": facts, "slots": slots, "I_use_bits_at_U_P": i_use, "trainable_parameters": train["trainable_parameters"], "stored_parameters": train["stored_parameters"],
            "stored_bytes": stored_bytes, "retained_bits_per_stored_byte": {p: v / stored_bytes for p, v in i_use.items()}, "K": core.work_formula(base, slots).get("K"), "V": core.work_formula(base, slots).get("V"), "W": w,
            "updates_U_P": c.u_p, "updates_U_run": c.run, "exposures_per_fact_U_P": core.exposures_per_fact(c.u_p, facts), "exposures_per_fact_U_run": core.exposures_per_fact(c.run, facts),
            "cpu_seconds_to_U_P": c.cpu(c.u_p), "cpu_seconds_to_U_run": c.cpu(c.run), "analytic_madds_to_U_P": mad * c.u_p, "analytic_madds_to_U_run": mad * c.run,
        })  # fmt: skip
    return rows


def mc_mismatch(study: Study, fro: fz.Frozen) -> list[dict[str, Any]]:
    """MC-MISMATCH (section 5.4): registered CPU seconds of the two readouts compared under MC differ by more than 1.25 (a flag; it changes no class)."""
    flags: list[dict[str, Any]] = []
    for p in fz.mc_pairs(fro.plan):
        e = fro.entry(p.key)
        if not e.ok():
            continue
        for r in range(1, core.REPLICATES + 1):
            a_arm, b_arm = p.small, p.large
            try:
                a = study.get(r, a_arm[0], a_arm[1], a_arm[2])
                b = study.get(r, b_arm[0], b_arm[1], b_arm[2])
                ca, cb = a.cpu(int(e.small_update)), b.cpu(int(e.large_update))  # type: ignore[arg-type]
            except KeyError:
                continue
            ratio = max(ca, cb) / min(ca, cb) if min(ca, cb) > 0 else math.inf
            if ratio > core.MC_MISMATCH:
                flags.append({"pair": p.key, "replicate": r, "cpu_ratio": ratio, "flag": "MC-MISMATCH"})
    return flags


# --- decision map (section 8.9; recommendations only) --------------------------------------------------------------------------------------------------------
def decision_map(cap: C.Outcome, eff: C.Outcome, arms: Mapping[str, Mapping[str, Any]], klimited: bool, eff_steps: Mapping[str, Mapping[str, Any]], sat: C.Outcome | None = None, dense_sat: Mapping[str, str] | None = None) -> list[str]:
    out: list[str] = []
    sub = any(arms.get(a, {}).get("class") == C.CAPACITY_SUPPORTED and arms[a].get("work_label") == C.SUBLINEAR for a in ("T-OQ", "F-OQ-IVF"))
    if cap.label == C.CAPACITY_POSITIVE and sub:
        out.append("1. CAPACITY-POSITIVE with a SUBLINEAR arm: propose a study of the same store with a qualified learned interface, and separately a physical storage measurement.")
    elif cap.label == C.CAPACITY_POSITIVE:
        out.append("2. CAPACITY-POSITIVE with F-OQ only: the index or the tree is the next question.")
    if klimited:
        out.append("3. KEY-LEARNING-LIMITED: study key learning under load.")
    if cap.label == C.CAPACITY_NEGATIVE and "(a)" in cap.printed:
        out.append("4. CAPACITY-NEGATIVE by NO GAIN: the store keeps several facts per slot at these counts; larger fact sets or another task are needed.")
    if cap.label == C.CAPACITY_NEGATIVE and "DENSE AHEAD" in cap.printed:
        out.append("5. CAPACITY-NEGATIVE by DENSE AHEAD: the dense map is the better use of these parameters on this task.")
    if cap.label == C.CAPACITY_NOT_TESTED:
        out.append("6. CAPACITY NOT TESTED: return to the human lead with the cost of the smallest loaded row.")
    if eff.label == C.EFFICIENCY_NEGATIVE and any(s["class"] == "SLOWER STEP" for a in eff_steps.values() for s in a.values()):
        out.append("7. EFFICIENCY-NEGATIVE with SLOWER steps: larger memories cost more updates at equal facts; any scaling plan must budget for it.")
    for name, o in (("capacity", cap), ("efficiency", eff)):
        if o.label in (C.CAPACITY_INCONCLUSIVE, C.EFFICIENCY_INCONCLUSIVE):
            out.append(f"8. {name.capitalize()} line inconclusive: no decision on that line.")
    if sat is not None and sat.label == C.SAT_SUBPROPORTIONAL:
        out.append("9. SATURATION-SUBPROPORTIONAL: what a slot holds falls as the store grows; any scaling plan must budget for it, and the cause (the shared output projection, interference between keys, or crowding of the fixed width-16 oracle codes) is the next question.")
    if sat is not None and sat.label == C.SAT_PROPORTIONAL:
        out.append("10. SATURATION-PROPORTIONAL: the same measurement at 16,384 slots and above, which S1 does not fund, is the next question, for P10-I.")
    if dense_sat and C.DENSE_HOLDS_MORE in dense_sat.values():
        out.append("11. DENSE HOLDS MORE AT SATURATION: per parameter, the dense map is the better store on this task; whatever the memory offers is then in its counted work and its sparse updates, and a scaling plan must say so.")
    out.append("12. Whatever the outcome, capacity from 16,384 to 65,536 slots stays untested and is proposed for P10-I.")
    return out if len(out) > 1 else ["No recommendation: nothing is authorized by this record.", out[-1]]


# --- the whole study ---------------------------------------------------------------------------------------------------------------------------------------------
def analyze_study(
    study: Study,
    fro: fz.Frozen,
    *,
    gates: Mapping[str, Any] | None,
    failed_tasks: Sequence[str] = (),
    expected_identity: Mapping[str, str] | None = None,
    timing: Mapping[str, Any] | None = None,
    throughput: Mapping[str, Any] | None = None,
    simulation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Every verdict, class, label and both outcomes. Rows 1 and 2 of section 8.7 apply first: an engineering failure gives no scientific label, an incomplete study (any
    registered cell without a record, any failed task) gives no outcome and its denominator is never reduced."""
    eng = engineering_status(gates, study, expected_identity)
    incomplete = bool(study.missing or study.failed or failed_tasks)
    result: dict[str, Any] = {
        "assessment": {
            "status": C.S1_ENGINEERING_FAILURE if eng["failed"] else (C.S1_INCOMPLETE if incomplete else "COMPLETE"), "engineering": eng, "missing_cells": sorted(study.missing), "failed_cells": sorted(study.failed),
            "reasons": {k: study.reasons[k] for k in sorted(study.reasons)}, "failed_tasks": sorted(failed_tasks), "cells_read": len(study.cells), "plan": fro.plan.as_json(), "cuts": list(fro.cuts),
        },  # fmt: skip
        "readings": C.READINGS, "oracle_sentence": core.ORACLE_SENTENCE, "s0_status": fro.s0_status, "lane_l": fro.lane_status, "store_only_tag": core.STORE_ONLY_TAG,
        "timing": None if timing is None else dict(timing), "throughput": None if throughput is None else dict(throughput), "simulation": None if simulation is None else dict(simulation),
    }  # fmt: skip
    if eng["failed"] or incomplete:
        out_c = C.capacity_outcome({}, engineering_failed=eng["failed"], incomplete=incomplete)
        out_e = C.efficiency_outcome({}, {}, engineering_failed=eng["failed"], incomplete=incomplete)
        out_s = C.saturation_outcome({}, engineering_failed=eng["failed"], incomplete=incomplete)
        result.update(capacity=None, efficiency=None, saturation=None, outcome={"capacity": out_c._asdict(), "efficiency": out_e._asdict(), "saturation": out_s._asdict()}, decision_map=["No recommendation: no scientific label on either line."])
        return result
    steps = capacity_steps(study, fro)
    arms = capacity_arms(study, fro, steps)
    dsat = {a: dense_saturation(study, fro, a) for a in DECISION_ARMS}
    sat = saturation_line(study, fro, {a: dsat[a]["label"] for a in DECISION_ARMS})
    arm_cap = {
        a: C.ArmCapacity(a, arms[a]["class"], arms[a]["dense"], arms[a]["capacity_steps"], dense_text="; ".join(t for t in (_dense_text(arms[a]["dense_detail"]), *arms[a]["dense_detail"].get("mu_text", [])) if t),
                         dense_sat=dsat[a]["label"], dense_sat_sublabels=list(dsat[a]["sublabels"]), sat_class=sat["arms"][a]["class"])
        for a in DECISION_ARMS
    }  # fmt: skip
    hier = hierarchy(study, fro)
    conv = conventional(study)
    every_not_loaded = all(
        all(steps[a][s.name]["class"] in (C.NOT_LOADED,) for s in fro.plan.steps) for a in ("F-OQ", "T-OQ")
    )
    directed = [t for t in fro.no_loaded_transitions if t in transitions_of(fro.plan)]
    work = {a: arms[a]["work_label"] for a in DECISION_ARMS}
    cap_out = C.capacity_outcome(arm_cap, engineering_failed=False, incomplete=False, directed_transitions=directed, every_step_not_loaded=every_not_loaded, reasons_extra=_inconclusive_reasons(arms, steps, fro.plan), printed_details=_printed_details(arms, hier, conv, work, fro, sat))
    klim = C.key_learning_limited(arms["H8"]["class"], arms["F-OQ"]["class"])
    reading = C.milestone_reading(cap_out, arm_cap, work, hier["label"], fro.s0_status)
    eff = efficiency_line(study, fro)
    eff_out = C.Outcome(**eff["outcome"])
    result.update(
        saturation={**sat, "dense_at_saturation": dsat},
        capacity={"steps": steps, "arms": arms, "hierarchy": hier, "conventional": conv, "key_learning_limited": klim, "h8_annotations": C.h8_annotations(fro.h8_undertrained, fro.h8_calibrated), "mc_ambiguous_pairs": {k: {"status": e.status, "small_update": e.small_update, "large_update": e.large_update, "multiplier": e.multiplier, "reading": "read in the comparator's favour (section 5.4): the cell whose advantage would be claimed at U_P, the other at the smallest grid snapshot with multiplier at least the larger of r and 1/r"} for k, e in sorted(fro.mc.items()) if e.annotation == C.MC_AMBIGUOUS}, "robustness": robustness(study, fro), "held_out": held_out(study, fro), "seed_block": seed_block(study, fro), "mc_mismatch": mc_mismatch(study, fro), "h8_undertrained": list(fro.h8_undertrained)},
        efficiency=eff,
        outcome={"capacity": {**cap_out._asdict(), "reading": reading}, "efficiency": eff_out._asdict(), "saturation": sat["outcome"]},
        cost_table=cost_rows(study, fro),
        decision_map=decision_map(cap_out, eff_out, arms, klim, eff["steps"], C.Outcome(**sat["outcome"]), {a: dsat[a]["label"] for a in DECISION_ARMS}),
    )  # fmt: skip
    return result


def _dense_text(detail: Mapping[str, Any]) -> str:
    """D-OQ's a_use at each cell in each reading (the dense label is printed with it, section 8.5)."""
    parts = []
    for cell, readings in detail.get("cells", {}).items():
        for reading, info in readings.items():
            vals = [v for rep in info["dense_a_use"] for v in rep if isinstance(v, float) and math.isfinite(v)]
            if vals:
                parts.append(f"{cell} {reading} D-OQ a_use {min(vals):.3f}-{max(vals):.3f}")
    return ", ".join(parts)


def _inconclusive_reasons(arms: Mapping[str, Mapping[str, Any]], steps: Mapping[str, Mapping[str, Any]], plan: core.Plan) -> list[str]:
    """The reason printed with CAPACITY-INCONCLUSIVE (section 8.7): NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD (which transition), ONE TRANSITION ONLY (which), INTERMEDIATE."""
    reasons: list[str] = []
    trans = transitions_of(plan)
    for a in DECISION_ARMS:
        cls = arms[a]["class"]
        if cls == C.NOT_TESTED_BY_LOAD:
            for t, ss in trans.items():
                if all(steps[a][s]["class"] == C.NOT_LOADED for s in ss):
                    reasons.append(f"{a}: NOT_TESTED_BY_LOAD ({t})")
        elif cls == C.CAPACITY_ONE_TRANSITION:
            done = [t for t, ss in trans.items() if any(steps[a][s]["class"] == C.CAPACITY_STEP for s in ss)]
            reasons.append(f"{a}: ONE TRANSITION ONLY ({', '.join(done)})")
        else:
            reasons.append(f"{a}: {cls}")
    return reasons


def _printed_details(arms: Mapping[str, Mapping[str, Any]], hier: Mapping[str, Any], conv: Mapping[str, Any], work: Mapping[str, Any], fro: fz.Frozen, sat: Mapping[str, Any]) -> list[str]:
    sufficient = [a for a in DECISION_ARMS if conv["arms"][a]["suffices"]]
    return [
        f"saturation outcome {sat['outcome']['label']} ({b_text({a: {n: tuple(r) for n, r in v.items()} for a, v in sat['b_ranges'].items()})})", "active work: " + ", ".join(f"{a} {work[a]}" for a in DECISION_ARMS if work.get(a)), f"hierarchy: {hier['label']}",
        "conventional retrieval: " + ("CONVENTIONAL RETRIEVAL SUFFICES for " + ", ".join(sufficient) if sufficient else "not sufficient") + "; DICT DOMINATES ON THIS TASK",
        fro.s0_status, f"learned-address lane: {fro.lane_status}", core.ORACLE_SENTENCE,
    ]  # fmt: skip


def read_analysis_inputs(run_dir: Path) -> dict[str, Any]:
    """Optional side records of a run directory (timing, throughput, simulation) if present."""
    out: dict[str, Any] = {}
    for name in ("timing", "throughput", "simulation"):
        p = run_dir / f"{name}.json"
        out[name] = read_json(p) if p.is_file() else None
    return out
