# ruff: noqa: E501
"""P10IS1 analysis (ADR-0024 section 9): a pure function over a registry of records, no I/O. ``analyze(Registry)`` returns every class, label and outcome of C-CAPACITY, C-SATURATION and C-EFFICIENCY with every
reading and every replicate the rules name. The registry's read keys carry the read's name (``core.read_key``), so the F-OQ and F-OQ-IVF reads of one snapshot are two records, never one (the defect of
``studies/p10s1/analysis.py`` lines 167-169).

Precedence (section 9.3 rows 1 and 2): an item error in any registered stage -> the analysis REFUSES and every line prints ENGINEERING STOP — ITEM ERRORS; a failed engineering gate or a frozen/running identity
difference that cannot be restored -> ENGINEERING-FAILURE; a registered read with no record -> INCOMPLETE (PAUSED when the cause is a resource cap, an environment stop, an unmet quiet condition or a restorable
identity stop): no outcome on any line.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core
from . import labels as L

ENGINEERING_STOP = "ENGINEERING STOP — ITEM ERRORS"
ENGINEERING_FAILURE = "ENGINEERING-FAILURE"
INCOMPLETE, PAUSED = "INCOMPLETE", "PAUSED"
NOT_REACHED = "NOT REACHED"
CAPACITY_READ = {"F-OQ": ("F-OQ", "main"), "F-OQ-IVF": ("F-OQ", "ivf"), "T-OQ": ("T-OQ", "main"), "H8": ("H8", "main")}
EFFICIENCY_STEP_NAMES = ("N1", "N2")
EFF_TRANSITIONS = {"1K→4K": ["N1"], "4K→16K": ["N2"]}


@dataclass
class Registry:
    """Everything the analysis reads. ``cells``: the plan's cells (``core.planned_cells``). ``reads``: ``core.read_key`` -> the eval record's read (``{"panels": {"A": {n, correct, useful, disabled_correct,
    shuffled_correct, unseen_n, unseen_correct}, "B": ...}}``). ``baselines``: ``core.baseline_key`` -> ``{"A": no-memory correct, "B": ...}``. ``ladder_stops``: ladder cell name -> ``{"u_run": int}``.
    ``cpu``: ``"arm|slots"`` -> measured CPU seconds per update (MC-T), None where MC-T is NOT MEASURED. ``qualification``: row (facts) -> fraction key -> qualified conditions (the rehearsal's R2 table).
    ``calibration``: ``{"h8_undertrained": [...], "h8_calibrated": [...], "sat256": bool}``. ``status``: ``{"item_errors": [...], "gate_failures": [...], "paused": [...], "run": ..., "stages": {...}}``."""

    cells: Sequence[Mapping[str, Any]]
    reads: Mapping[str, Mapping[str, Any]]
    baselines: Mapping[str, Mapping[str, int]]
    ladder_stops: Mapping[str, Mapping[str, Any]]
    cpu: Mapping[str, float] | None
    qualification: Mapping[str, Mapping[str, Sequence[str]]]
    calibration: Mapping[str, Any]
    status: Mapping[str, Any] = field(default_factory=dict)
    cfg: Mapping[str, Any] | None = None


def fraction_key(update: int, u_p: int) -> str:
    """A snapshot at update u maps to the fraction u / U_P; above 1 the qualification at fraction 1 applies (ruling 3)."""
    f = min(update / u_p, 1.0)
    return f"{f:.6g}"


class Analyzer:
    def __init__(self, reg: Registry) -> None:
        self.reg, self.cfg = reg, core.cfg_of(reg.cfg)
        self.th = core.Thresholds.from_config(self.cfg)
        self.by = {(c["arm"], c["facts"], c["slots"], c["draw"]): c for c in reg.cells}
        self.mct = reg.cpu is not None
        self.sat256 = bool(reg.calibration.get("sat256", True))
        self._series: dict[tuple[str, str, str], dict[int, L.Pt]] = {}
        self._obs: dict[tuple[str, str, int, str], L.Obs] = {}
        self.r2_fail: dict[tuple[int, int], dict[int, set[str]]] = {}
        self.reference_failed_dep: list[dict[str, Any]] = []
        self.missing: list[str] = []

    # --- cells, lengths -------------------------------------------------------------------------------------------------------
    def spec(self, arm: str, facts: int, slots: int, draw: int) -> Mapping[str, Any]:
        return self.by[(arm, facts, slots, draw)]

    def has(self, arm: str, facts: int, slots: int, draw: int) -> bool:
        return (arm, facts, slots, draw) in self.by

    def u_run(self, spec: Mapping[str, Any]) -> int:
        """The cell's run length: a ladder cell stops as a whole (ruling 27): U_run is the ladder point at which the whole cell stopped, or G."""
        if spec["ladder_cell"]:
            return int(self.reg.ladder_stops[core.cell_name(spec["facts"], spec["slots"])]["u_run"])
        return int(spec["run"])

    def snapshots(self, spec: Mapping[str, Any]) -> list[int]:
        return [u for u in spec["snapshots"] if u <= self.u_run(spec)]

    def expected_reads(self) -> list[str]:
        out = []
        for c in self.reg.cells:
            for u in self.snapshots(c):
                out.append(core.read_key(c["label"], u, "main"))
                if c["arm"] == "F-OQ" and c["slots"] != 256:
                    out.append(core.read_key(c["label"], u, "ivf"))
        return out

    def not_reached(self) -> dict[str, list[int]]:
        return {c["label"]: [u for u in c["snapshots"] if u > self.u_run(c)] for c in self.reg.cells if c["ladder_cell"] and any(u > self.u_run(c) for u in c["snapshots"])}

    # --- observations ---------------------------------------------------------------------------------------------------------------
    def obs(self, spec: Mapping[str, Any], read: str, update: int, panel: str) -> L.Obs:
        k = (spec["label"], read, update, panel)
        if k not in self._obs:
            p = self.reg.reads[core.read_key(spec["label"], update, read)]["panels"][panel]
            base = self.reg.baselines.get(core.baseline_key(spec["draw"], spec["facts"]), {}).get(panel)
            sh = p.get("shuffled_correct")
            self._obs[k] = L.Obs(
                n=int(p["n"]), correct=int(p["correct"]), useful=int(p["useful"]), disabled=None if p.get("disabled_correct") is None else int(p["disabled_correct"]), shuffled=None if sh is None else int(sh),
                baseline=None if base is None else int(base), unseen_n=int(p.get("unseen_n", 0)), unseen_correct=int(p.get("unseen_correct", 0)),
            )  # fmt: skip
        return self._obs[k]

    def series(self, spec: Mapping[str, Any], read: str, panel: str) -> dict[int, L.Pt]:
        k = (spec["label"], read, panel)
        if k not in self._series:
            out = {}
            for u in self.snapshots(spec):
                o = self.obs(spec, read, u, panel)
                out[u] = L.Pt(o.i, o.a_use)
            self._series[k] = out
        return self._series[k]

    def both(self, spec: Mapping[str, Any], read: str) -> dict[str, dict[int, L.Pt]]:
        return {p: self.series(spec, read, p) for p in core.PANELS}

    def leakage(self, spec: Mapping[str, Any], read: str) -> bool:
        return any(self.obs(spec, read, u, p).leakage for u in self.snapshots(spec) for p in core.PANELS)

    # --- DEP with the reference qualification (section 8.1) -----------------------------------------------------------------------------
    def table_qualified(self, facts: int, update: int, u_p: int) -> set[str]:
        row = self.reg.qualification.get(str(facts), {})
        key = fraction_key(update, u_p)
        return set(row[key]) if key in row else set(L.DEP_CONDITIONS)  # an off-grid fraction has no R2 read: nothing is disqualified (the stricter reading for the store)

    def compute_reference(self) -> None:
        """R2 re-read at its registered snapshots: a qualified condition that R2 fails in a replicate is not applied at that snapshot in that replicate (for every arm of that row): REFERENCE FAILED DEP."""
        for facts, (rf, rs) in {f: tuple(v) for f, v in ((int(k), v) for k, v in self.cfg["grid"]["r2_reference_cell"].items())}.items():
            for draw in range(1, self.th.replicates + 1):
                if not self.has("R2", rf, rs, draw):
                    continue
                spec = self.spec("R2", rf, rs, draw)
                fails: dict[int, set[str]] = {}
                for u in self.snapshots(spec):
                    q = self.table_qualified(facts, u, spec["u_p"])
                    for p in core.PANELS:
                        f = L.dep_failures(self.obs(spec, "main", u, p), memory=True, qualified=q)
                        if f:
                            fails.setdefault(u, set()).update(f)
                    if u in fails:
                        self.reference_failed_dep.append({"row": facts, "draw": draw, "update": u, "conditions": sorted(fails[u])})
                self.r2_fail[(facts, draw)] = fails

    def qualified(self, spec: Mapping[str, Any], update: int) -> set[str]:
        q = self.table_qualified(spec["facts"] if spec["arm"] != "R2" else spec["facts"], update, spec["u_p"])
        fails = self.r2_fail.get((spec["facts"], spec["draw"]), {})
        ru = min(update, spec["u_p"])
        return q - fails.get(ru, set())

    def dep_failed(self, spec: Mapping[str, Any], read: str, panel: str) -> frozenset[int]:
        mem = spec["arm"] != "D-OQ"
        return frozenset(u for u in self.snapshots(spec) if L.dep_failures(self.obs(spec, read, u, panel), memory=mem, qualified=self.qualified(spec, u)))

    def dep_failed_any(self, spec: Mapping[str, Any], read: str) -> bool:
        return any(self.dep_failed(spec, read, p) for p in core.PANELS)

    # --- REF, fullness -----------------------------------------------------------------------------------------------------------------
    def ref_ok(self, draw: int, facts: int) -> bool:
        rf, rs = self.cfg["grid"]["r2_reference_cell"][str(facts)]
        if not self.has("R2", int(rf), int(rs), draw):
            return False
        spec = self.spec("R2", int(rf), int(rs), draw)
        return all(L.ge(self.series(spec, "main", p)[spec["u_p"]].a_use, self.th.ref_r2_min) for p in core.PANELS)

    def full_info(self, spec: Mapping[str, Any], read: str) -> dict[str, Any]:
        """Own full length (first ladder point at which the arm is full, read on snapshots up to U_run; a cell that is not a ladder cell is full at its run length by the plateau test), fullness and loaded-ness."""
        ser = self.both(spec, read)
        run = self.u_run(spec)
        if spec["ladder_cell"]:
            length = L.first_full_length(ser, core.ladder_points(run, self.cfg), self.th, run)
        else:
            length = run if L.point_full(ser, run, self.th) else None
        return {"length": length, "full": length is not None, "loaded": L.loaded_flag(ser, length, self.th), "u_run": run}

    # --- costs ---------------------------------------------------------------------------------------------------------------------------
    def cost_a(self, arm: str, slots: int) -> float:
        from studies.p10s1 import frozen as s1frozen

        return float(s1frozen.analytic_madds_per_update("F-OQ" if arm == "F-OQ-IVF" else arm, slots))

    def cost_t(self, arm: str, slots: int) -> float | None:
        if self.reg.cpu is None:
            return None
        return float(self.reg.cpu[f"{'F-OQ' if arm == 'F-OQ-IVF' else arm}|{slots}"])

    def costs(self, arm_first: str, slots_first: int, arm_second: str, slots_second: int) -> tuple[tuple[float, float], tuple[float, float] | None]:
        a = (self.cost_a(arm_first, slots_first), self.cost_a(arm_second, slots_second))
        t1, t2 = self.cost_t(arm_first, slots_first), self.cost_t(arm_second, slots_second)
        return a, (None if t1 is None or t2 is None else (t1, t2))

    # --- the stop of a ladder cell (section 7.2 item 6, ruling 27) -------------------------------------------------------------------------
    def recompute_u_run(self, name: str) -> int:
        """The ladder point at which the whole cell stops, recomputed from the data: the first ladder point from U0 up to G at which every store arm read at the cell (F-OQ, T-OQ, H8; F-OQ alone at 2K/256) is full
        in every replicate on both panels, else G. Used to check the recorded U_run (a difference is an engineering failure, never a label)."""
        specs = [c for c in self.reg.cells if c["ladder_cell"] and core.cell_name(c["facts"], c["slots"]) == name and c["arm"] in core.STORE_ARMS]
        u0, granted = int(specs[0]["u0"]), int(specs[0]["run"])
        pts = core.ladder_points(granted, self.cfg)
        recorded = self.u_run(specs[0])
        for k, point in enumerate(pts):
            if point < u0 or point > recorded:
                continue
            prev = pts[k - 1] if k else None
            if all(L.full_at_u({p: {u: v for u, v in self.series(sp, "main", p).items() if u <= point} for p in core.PANELS}, point, prev, self.th) for sp in specs):
                return point
        return granted

    def ladder_stop_problems(self) -> list[str]:
        out = []
        for name in sorted({core.cell_name(c["facts"], c["slots"]) for c in self.reg.cells if c["ladder_cell"]}):
            rec = int(self.reg.ladder_stops[name]["u_run"])
            want = self.recompute_u_run(name)
            if rec != want:
                out.append(f"{name}: recorded U_run {rec} differs from the stop rule's {want}")
        return out

    # --- the capacity line ---------------------------------------------------------------------------------------------------------
    def capacity_step(self, arm: str, step: core.Step) -> dict[str, Any]:
        base, read = CAPACITY_READ[arm]
        reps: list[dict[str, Any]] = []
        small_not_full: list[bool] = []
        for draw in range(1, self.th.replicates + 1):
            sm, lg = self.spec(base, step.facts, step.small, draw), self.spec(base, step.facts, step.large, draw)
            fs, fl = self.full_info(sm, read), self.full_info(lg, read)
            u_p = int(sm["u_p"])
            costs_a, costs_t = self.costs(base, step.small, base, step.large)
            mc = L.mc_combined(costs_a, costs_t, u_p=u_p, run_first=fs["u_run"], run_second=fl["u_run"], grid=self.th.mc_grid, mode="capacity")
            dep_s = frozenset().union(*(self.dep_failed(sm, read, q) for q in core.PANELS))  # a blocking condition needs only ONE panel (ADR-0024 section 9; lead's ruling): the union over panels
            dep_l = frozenset().union(*(self.dep_failed(lg, read, q) for q in core.PANELS))
            panels = {}
            for p in core.PANELS:
                ctx = L.StepCtx(
                    u_p=u_p, run_small=fs["u_run"], run_large=fl["u_run"], ref_ok=self.ref_ok(draw, step.facts), leakage=self.leakage(sm, read) or self.leakage(lg, read),
                    dep_failed_small=dep_s, dep_failed_large=dep_l, small_full=fs["full"], large_full=fl["full"], small_loaded=fs["loaded"], mc=mc,
                )  # fmt: skip
                panels[p] = L.capacity_panel(self.series(sm, read, p), self.series(lg, read, p), ctx, self.th)
            rep = L.capacity_replicate(panels)
            reps.append({"replicate": draw, "verdict": rep.verdict, "detail": rep.detail, "small_full": fs["full"], "small_loaded": fs["loaded"], "small_length": fs["length"], "large_length": fl["length"], "u_run_small": fs["u_run"], "u_run_large": fl["u_run"]})
            small_not_full.append(not fs["full"])
        cls = L.capacity_step_class([r["verdict"] for r in reps], small_not_full, self.th)
        return {"step": step.name, "class": cls, "replicates": reps, "verdicts": [r["verdict"] for r in reps], "matched_compute_in_mc_a_only": not self.mct}

    def a_use_largest(self, arm: str) -> bool:
        base, read = CAPACITY_READ[arm]
        f, n = self.cfg["grid"]["u_p_larger_step_cell"]["32768"]
        return all(L.ge(self.series(self.spec(base, int(f), int(n), d), read, p)[self.spec(base, int(f), int(n), d)["u_p"]].a_use, self.th.arm_a_use_at_largest) for d in range(1, self.th.replicates + 1) for p in core.PANELS)

    def dense_reps(self, arm: str, step: core.Step) -> list[L.DenseRep]:
        base, read = CAPACITY_READ[arm]
        out = []
        for draw in range(1, self.th.replicates + 1):
            a, dq = self.spec(base, step.facts, step.large, draw), self.spec("D-OQ", step.facts, step.large, draw)
            u_p = int(a["u_p"])
            run_a, run_d = self.u_run(a), self.u_run(dq)
            costs_a, costs_t = self.costs("D-OQ", step.large, base, step.large)
            mc = L.mc_combined(costs_a, costs_t, u_p=u_p, run_first=run_d, run_second=run_a, grid=self.th.mc_grid, mode="dense")
            d: dict[str, dict[str, float | None]] = {r: {} for r in L.READINGS}
            status: dict[str, str] = {}
            blocked: dict[str, bool] = {}
            dq_fail = {p: self.dep_failed(dq, "main", p) for p in core.PANELS}
            for p in core.PANELS:
                sa, sd = self.series(a, read, p), self.series(dq, "main", p)
                d["MU"][p] = sa[u_p].i - sd[u_p].i
                best_u = max((u for u in sd if u <= run_d), key=lambda u: (sd[u].i, -u))
                d["D-BEST"][p] = sa[u_p].i - sd[best_u].i
                for name in L.MATCHED_COMPUTE_READINGS:
                    m = mc.get(name)
                    d[name][p] = None if m is None or not m.ok() else sa[int(m.second_update)].i - sd[int(m.first_update)].i  # type: ignore[arg-type]
                blocked["MU"] = blocked.get("MU", False) or u_p in dq_fail[p]
                blocked["D-BEST"] = blocked.get("D-BEST", False) or best_u in dq_fail[p]
                for name in L.MATCHED_COMPUTE_READINGS:
                    m = mc.get(name)
                    blocked[name] = blocked.get(name, False) or (m is not None and m.ok() and int(m.first_update) in dq_fail[p])  # type: ignore[arg-type]
            status["MU"] = status["D-BEST"] = L.OK
            for name in L.MATCHED_COMPUTE_READINGS:
                m = mc.get(name)
                status[name] = "NOT MEASURED" if m is None else m.status
            out.append(L.DenseRep(d, status, blocked))
        return out

    def dense_sat_reps(self, arm: str, cell: tuple[int, int]) -> tuple[list[L.SatDenseRep], list[dict[str, Any]]]:
        base, read = CAPACITY_READ[arm]
        reps, detail = [], []
        for draw in range(1, self.th.replicates + 1):
            a, dq = self.spec(base, cell[0], cell[1], draw), self.spec("D-OQ", cell[0], cell[1], draw)
            fa, fd = self.full_info(a, read), self.full_info(dq, "main")
            la, ld = int(fa["length"] or fa["u_run"]), int(fd["length"] or fd["u_run"])
            d_sat: dict[str, float] = {}
            ratio: dict[str, float | None] = {}
            blocked = False
            shorter: dict[str, float] = {}
            for p in core.PANELS:
                sa, sd = self.series(a, read, p), self.series(dq, "main", p)
                ia, idq = L.i_star(sa, la), L.i_star(sd, ld)
                d_sat[p] = ia - idq
                ratio[p] = None if idq <= 0.0 else ia / idq
                short = min(la, ld)
                shorter[p] = L.i_star(sa, short) - L.i_star(sd, short)
                fails = self.dep_failed(dq, "main", p)
                best_u = max((u for u in sd if u <= ld), key=lambda u: (sd[u].i, -u))
                blocked = blocked or best_u in fails or (self.u_run(dq) // 2) in fails  # ruling 17: the snapshot attaining i* and U_run/2 (of the cell, not of D-OQ's own length)
            cost_ok = self.mct and self.cost_t("D-OQ", cell[1]) >= self.cost_t(base, cell[1]) and self.cost_a("D-OQ", cell[1]) >= self.cost_a(base, cell[1])  # type: ignore[operator]
            reps.append(L.SatDenseRep(d_sat, ratio, fd["full"], bool(cost_ok), blocked))
            detail.append({"replicate": draw, "arm_length": la, "dense_length": ld, "d_sat": d_sat, "d_sat_at_shorter_length": shorter, "ratio": ratio, "dense_full": fd["full"], "dense_a_use_at_u_p": {p: self.series(dq, "main", p)[int(dq["u_p"])].a_use for p in core.PANELS}})
        return reps, detail

    def capacity_line(self) -> dict[str, Any]:
        trans = core.transitions(self.cfg)
        arms: dict[str, Any] = {}
        loaded = core.loaded_cells(self.cfg)
        for arm in core.CLASSIFIED_ARMS:
            steps = {s.name: self.capacity_step(arm, s) for s in core.steps(self.cfg)}
            cls = L.capacity_arm_class({k: v["class"] for k, v in steps.items()}, trans, self.a_use_largest(arm))
            cap_steps = [s for s in core.steps(self.cfg) if steps[s.name]["class"] == L.CAPACITY_STEP]
            cell_dense: dict[str, Any] = {}
            for s in cap_steps:
                cell_dense[core.cell_name(s.facts, s.large)] = L.dense_cell_label(self.dense_reps(arm, s), self.th, mct_measured=self.mct)
            sat: dict[str, Any] = {}
            for cell in loaded:
                reps, detail = self.dense_sat_reps(arm, cell)
                sat[core.cell_name(*cell)] = {**L.dense_at_saturation(reps, self.th, mct_measured=self.mct), "replicates": detail}
            arm_dense = L.dense_arm_label({k: v["label"] for k, v in cell_dense.items()}, {k: v["label"] for k, v in sat.items()}, self.th)
            arms[arm] = {"steps": steps, "class": cls, "capacity_steps": [s.name for s in cap_steps], "dense_cells": cell_dense, "dense_at_saturation": sat, "dense_arm": arm_dense, "a_use_at_32K_16K_all5": self.a_use_largest(arm)}
        outcome = L.capacity_outcome(
            {a: L.ArmCapacity(a, arms[a]["class"], arms[a]["dense_arm"]) for a in core.DECISION_ARMS},
            every_step_unloaded_or_unfull=all(arms[a]["steps"][s]["class"] in (L.NOT_LOADED, L.NOT_FULL_WITHIN_BUDGET) for a in ("F-OQ", "T-OQ") for s in arms[a]["steps"]), mct_measured=self.mct,
        )  # fmt: skip
        h8_cells = [core.cell_name(f, n) for f, n in core.arm_cells("H8", self.cfg)]
        cal = self.reg.calibration
        ann = L.h8_annotations(list(cal.get("h8_undertrained", [])), list(cal.get("h8_calibrated", [])), h8_cells)
        return {
            "arms": arms, "outcome": outcome, "key_learning_limited": L.key_learning_limited(arms["H8"]["class"], arms["F-OQ"]["class"]), "h8_annotations": ann, "matched_compute_in_mc_a_only": not self.mct,
            "sparse": self.sparse(), "not_tested_x": core.NOT_TESTED_X, "sizes": core.SIZES_CAPACITY,
        }  # fmt: skip

    def sparse(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for tag in ("U_P", "run"):
            ratios = []
            for draw in range(1, self.th.replicates + 1):
                rep: dict[str, dict[str, float]] = {}
                for f, n in (tuple(self.cfg["grid"]["u_p_larger_step_cell"]["8192"]), tuple(self.cfg["grid"]["u_p_larger_step_cell"]["32768"])):
                    t, v = self.spec("T-OQ", f, n, draw), self.spec("F-OQ", f, n, draw)
                    u = int(t["u_p"]) if tag == "U_P" else self.u_run(t)
                    rep[core.cell_name(f, n)] = {}
                    for p in core.PANELS:
                        it, iv = self.series(t, "main", p)[u].i, self.series(v, "ivf", p)[u].i
                        rep[core.cell_name(f, n)][p] = float("inf") if iv <= 0 < it else (1.0 if iv <= 0 else it / iv)
                ratios.append(rep)
            out[tag] = {"label": L.sparse_label(ratios, self.th), "ratios": ratios}
        return out

    # --- the saturation line -------------------------------------------------------------------------------------------------------
    def saturation_line(self) -> dict[str, Any]:
        from studies.p10s1 import classes as c1

        arms: dict[str, Any] = {}
        for arm, pairs_ in core.saturation_pairs(self.cfg).items():
            base, read = CAPACITY_READ[arm]
            pair_out: dict[str, Any] = {}
            for n_small, n_large in pairs_:
                cs, cl = core.saturation_cell_of_slots(n_small, self.cfg), core.saturation_cell_of_slots(n_large, self.cfg)
                name = f"{core.size_name(n_small)}→{core.size_name(n_large)}"
                if cs == core.saturation_only_cell(self.cfg) and not self.sat256:
                    pair_out[name] = {"class": c1.NOT_FULL, "verdicts": [c1.NOT_FULL] * self.th.replicates, "note": "256 NOT MEASURED — NOT FULL WITHIN CEILING", "replicates": []}
                    continue
                reps, verdicts = [], []
                for draw in range(1, self.th.replicates + 1):
                    sides, dep_any, leak = [], False, False
                    for cell in (cs, cl):
                        sp = self.spec(base, cell[0], cell[1], draw)
                        info = self.full_info(sp, read)
                        dep_any = dep_any or self.dep_failed_any(sp, read)
                        leak = leak or self.leakage(sp, read)
                        sides.append({"facts": cell[0], "slots": cell[1], "series": self.both(sp, read), "length": info["length"] or info["u_run"], "loaded": info["loaded"], "dep_failed": self.dep_failed_any(sp, read), "full": info["full"], "u_run": info["u_run"]})
                    ref = self.ref_ok(draw, cs[0]) and self.ref_ok(draw, cl[0])
                    res = L.saturation_pair(sides[0], sides[1], ref_ok=ref, leakage=leak, th=self.th)
                    verdicts.append(res.verdict)
                    reps.append({"replicate": draw, "verdict": res.verdict, "detail": res.detail, "full": {core.cell_name(*c): s["full"] for c, s in zip((cs, cl), sides, strict=True)}})
                pair_out[name] = {"class": c1.saturation_pair_class(verdicts), "verdicts": verdicts, "replicates": reps, "crowding_note": c1_crowding()}
            classes = [v["class"] for v in pair_out.values()]
            arms[arm] = {"pairs": pair_out, "class": c1.saturation_arm_class(classes)}
        return {"arms": arms, "outcome": L.saturation_outcome({a: v["class"] for a, v in arms.items()}, sat256_absent=not self.sat256), "not_tested_x": core.NOT_TESTED_X}

    # --- the efficiency line -------------------------------------------------------------------------------------------------------
    def efficiency_line(self) -> dict[str, Any]:
        from studies.p10s1 import classes as c1

        readings = ["E-A"] + (["E-T"] if self.mct else [])
        out: dict[str, Any] = {r: {"arms": {}} for r in readings}
        arm_classes: dict[str, dict[str, str]] = {r: {} for r in readings}
        dense: dict[str, dict[str, list[str]]] = {r: {} for r in readings}
        for r in readings:
            cost = (lambda a, n: self.cost_a(a, n)) if r == "E-A" else (lambda a, n: float(self.cost_t(a, n)))  # type: ignore[arg-type]
            for arm in core.EFFICIENCY_ARMS:
                steps: dict[str, Any] = {}
                for s in core.steps(self.cfg):
                    if s.name not in EFFICIENCY_STEP_NAMES:
                        continue
                    reps, verdicts = [], []
                    for draw in range(1, self.th.replicates + 1):
                        sm, lg = self.spec(arm, s.facts, s.small, draw), self.spec(arm, s.facts, s.large, draw)
                        us = L.u_t_of(self.both(sm, "main"), self.u_run(sm), {p: self.dep_failed(sm, "main", p) for p in core.PANELS})
                        ul = L.u_t_of(self.both(lg, "main"), self.u_run(lg), {p: self.dep_failed(lg, "main", p) for p in core.PANELS})
                        res = L.efficiency_step(us, ul, ref_ok=self.ref_ok(draw, s.facts), leakage=self.leakage(sm, "main") or self.leakage(lg, "main"), run_small=self.u_run(sm), run_large=self.u_run(lg), cost_small=cost(arm, s.small), cost_large=cost(arm, s.large))
                        verdicts.append(res.verdict)
                        reps.append({"replicate": draw, "verdict": res.verdict, "u_t_small": [us.ut.kind, us.ut.lo, us.ut.hi], "u_t_large": [ul.ut.kind, ul.ut.lo, ul.ut.hi], "detail": res.detail})
                    steps[s.name] = {"class": c1.efficiency_step_class(verdicts), "replicates": reps, "verdicts": verdicts}
                acls = c1.efficiency_arm_class({k: v["class"] for k, v in steps.items()}, EFF_TRANSITIONS)
                arm_classes[r][arm] = acls
                labels_here: list[str] = []
                dense_detail: dict[str, Any] = {}
                for s in core.steps(self.cfg):
                    if s.name not in EFFICIENCY_STEP_NAMES or steps[s.name]["class"] != "FASTER STEP":
                        continue
                    arm_ut, d_ut, blocked = [], [], []
                    for draw in range(1, self.th.replicates + 1):
                        a, dq = self.spec(arm, s.facts, s.large, draw), self.spec("D-OQ", s.facts, s.large, draw)
                        arm_ut.append([L.u_t_panel(self.series(a, "main", p), self.u_run(a), self.dep_failed(a, "main", p)) for p in core.PANELS])
                        d_ut.append([L.u_t_panel(self.series(dq, "main", p), self.u_run(dq), frozenset()) for p in core.PANELS])  # D-OQ's own DEP never removes its qualification for u_T (ruling 17)
                        blocked.append(any(self.dep_failed(dq, "main", p) for p in core.PANELS))
                    label = L.dense_speed(arm_ut, d_ut, cost(arm, s.large), cost("D-OQ", s.large), self.th, blocked=blocked)
                    labels_here.append(label)
                    dense_detail[core.cell_name(s.facts, s.large)] = label
                dense[r][arm] = labels_here
                steps_all = steps
                out[r]["arms"][arm] = {"steps": steps_all, "class": acls, "dense_speed": dense_detail}
        outcome = L.efficiency_outcome(arm_classes, dense, mct_measured=self.mct)
        return {"readings": out, "outcome": outcome, "sizes": "SIZES 1,024–16,384", "e_a_only": not self.mct}

    def counted_work(self) -> list[dict[str, Any]]:
        from studies.p10s1 import core as s1

        rows = []
        for arm in ("F-OQ", "T-OQ", "H8", "D-OQ", "R2"):
            for f, n in core.arm_cells(arm, self.cfg, sat256=self.sat256):
                rows.append({"arm": arm, "cell": core.cell_name(f, n), **s1.work_formula(arm, n), "note": "logical counts per query; not measured efficiency"})
        return rows


def c1_crowding() -> str:
    from studies.p10s1 import classes as c1

    return str(c1.CROWDING_CAVEAT)


def check_complete(reg: Registry, an: Analyzer) -> list[str]:
    """Registered reads with no record (a ladder cell's snapshots beyond its U_run are NOT REACHED, not missing)."""
    return sorted(k for k in an.expected_reads() if k not in reg.reads)


def analyze(reg: Registry) -> dict[str, Any]:
    """The whole analysis. Statuses first (section 9.3 rows 1 and 2); labels only when the registry is complete and clean."""
    st = dict(reg.status)
    base: dict[str, Any] = {"run": st.get("run"), "stages": st.get("stages", {}), "mct_measured": reg.cpu is not None, "lane_l": st.get("lane_l", core.LANE_L_NOT_LICENSED), "not_tested_x": core.NOT_TESTED_X}
    if st.get("item_errors"):
        return {**base, "status": ENGINEERING_STOP, "refused": True, "item_errors": list(st["item_errors"]), "lines": {k: ENGINEERING_STOP for k in ("C-CAPACITY", "C-SATURATION", "C-EFFICIENCY")}}
    if st.get("gate_failures") or st.get("identity_unrestorable"):
        return {**base, "status": ENGINEERING_FAILURE, "gate_failures": list(st.get("gate_failures", [])), "lines": {k: ENGINEERING_FAILURE for k in ("C-CAPACITY", "C-SATURATION", "C-EFFICIENCY")}}
    names = sorted({core.cell_name(c["facts"], c["slots"]) for c in reg.cells if c["ladder_cell"]})
    no_decision = [n for n in names if n not in reg.ladder_stops]
    if no_decision:  # a ladder cell without its decision (PAUSED, or a failed cell): the registry is not complete; it is a status, never a crash
        status = PAUSED if st.get("paused") else INCOMPLETE
        return {**base, "status": status, "missing_ladder_decisions": no_decision, "missing_reads": [], "missing_count": 0, "paused": list(st.get("paused", [])), "failed_cells": list(st.get("failed_cells", [])), "lines": {k: status for k in ("C-CAPACITY", "C-SATURATION", "C-EFFICIENCY")}}
    an = Analyzer(reg)
    missing = check_complete(reg, an)
    if missing or st.get("paused") or st.get("failed_cells"):
        status = PAUSED if st.get("paused") else INCOMPLETE
        return {**base, "status": status, "missing_reads": missing[:50], "missing_count": len(missing), "paused": list(st.get("paused", [])), "failed_cells": list(st.get("failed_cells", [])), "lines": {k: status for k in ("C-CAPACITY", "C-SATURATION", "C-EFFICIENCY")}}
    problems = an.ladder_stop_problems()
    if problems:
        return {**base, "status": ENGINEERING_FAILURE, "gate_failures": problems, "lines": {k: ENGINEERING_FAILURE for k in ("C-CAPACITY", "C-SATURATION", "C-EFFICIENCY")}}
    an.compute_reference()
    cap, sat, eff = an.capacity_line(), an.saturation_line(), an.efficiency_line()
    return {
        **base, "status": "COMPLETE", "refused": False, "capacity": cap, "saturation": sat, "efficiency": eff, "reference_failed_dep": an.reference_failed_dep, "not_reached": an.not_reached(), "counted_work": an.counted_work(),
        "lines": {"C-CAPACITY": cap["outcome"]["label"], "C-SATURATION": sat["outcome"]["label"], "C-EFFICIENCY": eff["outcome"]["label"]}, "ladder_stops": dict(reg.ladder_stops),
        "counts": {"cells": len(reg.cells), "reads_recorded": len(reg.reads), "reads_expected": len(an.expected_reads()), "ladder_cells_with_not_reached": len(an.not_reached())},
        "qualification": reg.qualification, "calibration": dict(reg.calibration),
    }  # fmt: skip
