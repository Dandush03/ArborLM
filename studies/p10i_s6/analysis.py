# ruff: noqa: E501
"""P10IS6 analysis (ADR-0031 sections 9 to 12): a pure function of the registry (keys of ``core``), the rate table and the config. No torch, no IO.

It refuses (``EngineeringStop``) while any run or evaluation record is an item error, and when a required record is missing with no failed run to explain it (ENGINEERING STOP — INCOMPLETE REGISTRY): denominators are never reduced.
A failed cell is a run with status ``failed_cell`` (a non-finite training loss, clipped gradient norm or parameter) or a non-finite enabled NLL at a snapshot a rule reads (section 12.2); a failed run fails every rung it serves.
"""

import statistics
from collections.abc import Mapping, Sequence
from typing import Any

from . import core, labels
from .core import DENSE, FLAT, EngineeringStop, Thresholds

Registry = Mapping[str, Any]


def rates_of(rate_table: Mapping[str, Any], k_max: int) -> dict[str, dict[int, float]]:
    """``rate_table = {"rates": {arm: {"-1": r, "0": r, ...}}}``: every rung -1..k_max for both arms."""
    out: dict[str, dict[int, float]] = {}
    for arm in core.ARMS:
        d = {int(k): float(v) for k, v in rate_table["rates"][arm].items()}
        missing = [k for k in range(-1, k_max + 1) if k not in d]
        if missing:
            raise EngineeringStop(f"ENGINEERING STOP — the rate table has no rate for {arm} at rungs {missing}")
        out[arm] = d
    return out


def _eq(a: float, b: float, bitwise: bool) -> bool:
    return a == b if bitwise else abs(a - b) <= 1e-6


class _Reader:
    def __init__(self, reg: Registry, cfg: Mapping[str, Any], rates: Mapping[str, Mapping[int, float]], k_max: int, cells: int, oa: bool = False) -> None:
        self.reg, self.cfg, self.rates, self.k_max, self.n, self.oa = reg, cfg, rates, k_max, cells, oa
        self.draws = int(cfg["controls"]["p_used_draws"])

    def u(self, k: int) -> int:
        return core.rung_updates(self.cfg, k)

    def run(self, arm: str, k: int, c: int) -> Mapping[str, Any]:
        key = core.run_key(arm, self.rates[arm][k], c, oa=self.oa)
        if key not in self.reg:
            raise EngineeringStop(f"ENGINEERING STOP — INCOMPLETE REGISTRY: no run record {key}")
        return self.reg[key]  # type: ignore[no-any-return]

    def run_failed(self, arm: str, k: int, c: int) -> bool:
        return self.run(arm, k, c).get("status") == "failed_cell"

    def read(self, arm: str, k: int, c: int, update: int, read: str, draw: int = 0) -> float | None:
        key = core.nll_key(arm, self.rates[arm][k], c, update, read, draw, oa=self.oa)
        if key not in self.reg:
            raise EngineeringStop(f"ENGINEERING STOP — INCOMPLETE REGISTRY: no record {key}")
        v = self.reg[key]
        return None if v is None else float(v)


def _refuse_item_errors(reg: Registry) -> None:
    bad = [k for k, v in reg.items() if isinstance(v, Mapping) and v.get("status") == "item_error"]
    if bad:
        raise EngineeringStop(f"ENGINEERING STOP — ITEM ERRORS: {len(bad)} record(s), first {sorted(bad)[0]}; nothing is labelled")


def _stats(v: Sequence[float | None]) -> dict[str, Any]:
    f = [x for x in v if x is not None]
    return {"mean": labels.mean_of(v), "sd": statistics.stdev(f) if len(f) > 1 else None, "min": min(f) if f else None, "max": max(f) if f else None, "n": len(f), "positive": sum(1 for x in f if x > 0), "negative": sum(1 for x in f if x < 0), "none": len(v) - len(f)}


def analyse(reg: Registry, rate_table: Mapping[str, Any], cfg: Mapping[str, Any], *, k_max: int, bitwise: bool, th: Thresholds | None = None, cells: int | None = None, oa_cells: int | None = None, calibration_states: Mapping[str, Any] | None = None) -> dict[str, Any]:
    th = th or Thresholds.from_config(cfg)
    n = cells if cells is not None else th.cells
    if n % 3:
        raise ValueError("cells must be a multiple of three (parents of three seeds)")
    _refuse_item_errors(reg)
    rates = rates_of(rate_table, k_max)
    rd = _Reader(reg, cfg, rates, k_max, n)
    cell_range = range(n)
    parent = [c // 3 for c in cell_range]
    ks = core.rung_range(k_max)
    eps = th.epsilon

    # BASE per registered parent (cause 1)
    base: dict[int, float | None] = {}
    base_ok = True
    for p in range(n // 3):
        e, r = reg.get(core.base_key(p)), reg.get(core.base_key(p, core.READ_REPLAY))
        if e is None or r is None:
            base_ok = False
            base[p] = None if e is None else float(e)
            continue
        base[p] = float(e)
        if not _eq(float(e), float(r), bitwise):
            base_ok = False

    # failed cells and the values the rules read
    failed: dict[str, dict[int, list[bool]]] = {a: {} for a in core.ARMS}
    nll: dict[str, dict[int, list[float | None]]] = {a: {} for a in core.ARMS}
    nll_prev: dict[str, dict[int, list[float | None]]] = {a: {} for a in core.ARMS}  # the enabled read at U_{k-1} of the run at r(arm, k)
    integrity_bad: list[str] = []
    for a in core.ARMS:
        for k in ks:
            fl, vals, prev = [], [], []
            for c in cell_range:
                run_failed = rd.run_failed(a, k, c)
                e = None if run_failed else rd.read(a, k, c, rd.u(k), core.READ_ENABLED)
                pv = None if (run_failed or k < 0) else rd.read(a, k, c, rd.u(k - 1), core.READ_ENABLED)
                bad = run_failed or e is None or (k >= 0 and pv is None)
                fl.append(bool(bad))
                vals.append(None if bad else e)
                prev.append(None if bad or k < 0 else pv)
                if not bad:
                    rep, dis = rd.read(a, k, c, rd.u(k), core.READ_REPLAY), rd.read(a, k, c, rd.u(k), core.READ_DISABLED)
                    b = base.get(parent[c])
                    if rep is None or dis is None or b is None:
                        integrity_bad.append(f"{a} c{c:02d} k{k}: replay, disabled or BASE not finite")
                    else:
                        if not _eq(rep, float(e), bitwise):  # type: ignore[arg-type]
                            integrity_bad.append(f"{a} c{c:02d} k{k}: replay != enabled")
                        if not _eq(dis, b, bitwise):
                            integrity_bad.append(f"{a} c{c:02d} k{k}: disabled != BASE")
            failed[a][k], nll[a][k], nll_prev[a][k] = fl, vals, prev

    L = {a: {k: labels.mean_of(nll[a][k]) for k in ks} for a in core.ARMS}
    delta = {a: {k: (None if L[a][k - 1] is None or L[a][k] is None else float(L[a][k - 1]) - float(L[a][k])) for k in range(0, k_max + 1)} for a in core.ARMS}  # type: ignore[arg-type]
    delta_run: dict[str, dict[int, float | None]] = {}
    for a in core.ARMS:
        delta_run[a] = {}
        for k in range(0, k_max + 1):
            m0, m1 = labels.mean_of(nll_prev[a][k]), L[a][k]
            delta_run[a][k] = None if m0 is None or m1 is None else float(m0) - float(m1)
    states = {a: {k: labels.convergence_state(delta[a][k], delta_run[a][k], eps) for k in range(0, k_max + 1)} for a in core.ARMS}
    ks_ = labels.k_star(states, k_max)
    reading = ks_ if ks_ is not None else k_max

    # cell lists at rungs 0..k_max
    B = [base.get(parent[c]) for c in cell_range]
    H = {k: nll[FLAT][k] for k in range(0, k_max + 1)}
    A = {k: nll[DENSE][k] for k in range(0, k_max + 1)}
    q = {k: labels.diff(A[k], H[k]) for k in H}
    jd = labels.j_dagger(L[DENSE], k_max)
    q_dag = {k: (labels.diff(A[jd], H[k]) if jd is not None else [None] * n) for k in H}
    classes = {k: labels.rung_class(q[k], q_dag[k], th) for k in H}
    cd = {k: labels.diff(B, A[k]) for k in H}
    c_flat = {k: labels.diff(B, H[k]) for k in H}

    flat_failed = any(any(failed[FLAT][k]) for k in ks)
    dense_failed = any(any(failed[DENSE][k]) for k in ks)
    causes: list[str] = []
    cause_ids: list[int] = []
    if not base_ok:
        causes.append("BASE is missing or fails its replay on a registered parent")
        cause_ids.append(1)
    if integrity_bad:
        causes.append("disabled != BASE or replay != enabled on an evaluation a rule reads")
        cause_ids.append(2)
    if dense_failed:
        causes.append("a D-ADAPT run that a rule reads is a failed cell")
        cause_ids.append(3)
    cdm = labels.mean_of(cd[reading])
    if cdm is not None and cdm < th.dense_floor:
        causes.append("mean Cd(R) < 0.005: the dense adapter adds nothing measurable at the reading rung")
        cause_ids.append(4)

    conv_end = {a: labels.is_converged(states[a][k_max]) for a in core.ARMS}
    conv_prev = {a: (labels.is_converged(states[a][k_max - 1]) if k_max >= 1 else False) for a in core.ARMS}
    lp = labels.line_p(causes=causes, flat_failed=flat_failed, k_star_=ks_, k_max=k_max, classes=classes, conv_end=conv_end, conv_prev=conv_prev)

    # D[FLAT] at the reading rung R, from M-FLAT's full read set of the run at r(M-FLAT, R)
    def flat_read(c: int, draw: int, read: str) -> float | None:
        if failed[FLAT][reading][c]:
            return None
        return rd.read(FLAT, reading, c, rd.u(reading), read, draw)

    hr = H[reading]
    p_used: list[float | None] = []
    h_used: list[float | None] = []
    x_mean: list[float | None] = []
    h_mean: list[float | None] = []
    h_vmean: list[float | None] = []
    used_slots: list[int | None] = []
    for c in cell_range:
        if hr[c] is None:
            p_used.append(None)
            h_used.append(None)
            x_mean.append(None)
            h_mean.append(None)
            h_vmean.append(None)
            used_slots.append(None)
            continue
        draws = [flat_read(c, j, core.READ_P_USED) for j in range(rd.draws)]
        hu = None if any(d is None for d in draws) else sum(float(d) for d in draws if d is not None) / len(draws)
        h_used.append(hu)
        p_used.append(None if hu is None else hu - float(hr[c]))  # type: ignore[arg-type]
        xm, vm = flat_read(c, 0, core.READ_X_MEAN), flat_read(c, 0, core.READ_V_MEAN)
        h_mean.append(xm)
        h_vmean.append(vm)
        x_mean.append(None if xm is None else xm - float(hr[c]))  # type: ignore[arg-type]
        us = reg.get(core.stat_key(FLAT, rates[FLAT][reading], c, rd.u(reading), "used_slots"))
        used_slots.append(None if us is None else int(us))
    collapsed = [(u is not None and u < int(cfg["controls"]["min_used_slots"])) for u in used_slots]
    d_ne = any(i in (1, 2) for i in cause_ids) or any(failed[FLAT][reading])
    dep = labels.d_flat(c_flat[reading], p_used, x_mean, th, collapsed=collapsed, not_evaluable=d_ne)
    qualified = labels.dependence_qualified(lp["row"], dep["label"])

    # harm figures (section 11), per rung, strict ">"
    harm: dict[int, dict[str, Any]] = {}
    for k in range(0, k_max + 1):
        entry: dict[str, Any] = {}
        used_k, hm_k, hv_k, us_k = [], [], [], []
        for c in cell_range:
            if H[k][c] is None:
                used_k.append(None)
                hm_k.append(None)
                hv_k.append(None)
                us_k.append(None)
                continue
            draws = [rd.read(FLAT, k, c, rd.u(k), core.READ_P_USED, j) for j in range(rd.draws)]
            used_k.append(None if any(d is None for d in draws) else sum(float(d) for d in draws if d is not None) / len(draws))
            hm_k.append(rd.read(FLAT, k, c, rd.u(k), core.READ_X_MEAN))
            hv_k.append(rd.read(FLAT, k, c, rd.u(k), core.READ_V_MEAN))
            us = reg.get(core.stat_key(FLAT, rates[FLAT][k], c, rd.u(k), "used_slots"))
            us_k.append(None if us is None else int(us))
        for name, vals in (("H_used", used_k), ("H_mean", hm_k), ("H_vmean", hv_k)):
            gap = labels.diff(B, vals)
            entry[name] = {"mean_B_minus": labels.mean_of(gap), "cells_worse_than_base": labels.count([v is not None and b is not None and v > b for v, b in zip(vals, B, strict=True)])}
        entry["used_slots"] = us_k
        harm[k] = entry

    # R16 (rung 0) and OA
    r16 = labels.replication(c_flat[0], cd[0], th, integrity_stop=any(i in (1, 2) for i in cause_ids))
    r16["convergence_rung0"] = {a: states[a][0] for a in core.ARMS}
    oa = _analyse_oa(reg, cfg, rates, th, bitwise, oa_cells) if oa_cells else {"label": "NOT RUN"}

    nd = lp["row"] in (1, 2)
    held = {k: labels.held(q[k], th) for k in q}
    mean_q = {k: labels.mean_of(q[k]) for k in q}
    trend = labels.trend_tag(held, mean_q, k_max, th, nd=nd)
    sentence = labels.lead_sentence(mean_q[k_max], delta[FLAT][k_max], delta[DENSE][k_max])

    label = lp["label"]
    if lp["row"] >= 3:
        label = f"{label} [{trend['text']}]"
    per_rung = {
        str(k): {
            "updates": rd.u(k), "rates": {a: rates[a][k] for a in core.ARMS}, "L": {a: L[a][k] for a in core.ARMS}, "delta": {a: delta[a][k] for a in core.ARMS}, "delta_run": {a: delta_run[a][k] for a in core.ARMS},
            "convergence": {a: states[a][k] for a in core.ARMS}, "class": classes[k], "held": held[k], "mean_Q": mean_q[k], "Q": _stats(q[k]), "Q_dag": _stats(q_dag[k]),
            "Q_cells_positive": labels.count([x is not None and x > 0 for x in q[k]]), "Q_parents_positive": labels.count([x is not None and x > 0 for x in labels.parent_means(q[k])]),
            "C": _stats(c_flat[k]), "Cd": _stats(cd[k]), "delta_per_parent": {a: _per_parent_delta(nll[a], nll_prev[a], k, n) for a in core.ARMS},
        }
        for k in range(0, k_max + 1)
    }
    rung_m1 = {a: {"updates": rd.u(-1), "rate": rates[a][-1], "L": L[a][-1]} for a in core.ARMS}
    step0 = {a: {str(k): _step0(rd, reg, a, k, n) for k in ks} for a in core.ARMS}
    out = {
        "mode": "analysis", "k_max": k_max, "cells": n, "reading_rung": reading, "k_star": ks_, "j_dagger": jd,
        "line_p": {**lp, "label": label, "base_label": lp["base"], "dependence_qualified": qualified, "causes": causes, "cause_ids": cause_ids, "integrity_problems": integrity_bad[:20]},
        "d_flat": {**dep, "reading_rung": reading, "H_used_worse_than_base_cells": harm[reading]["H_used"]["cells_worse_than_base"], "mean_V_mean_gap": harm[reading]["H_vmean"]["mean_B_minus"]},
        "r16": r16, "oa": oa, "trend": {**trend, "lead_sentence": sentence}, "per_rung": per_rung, "rung_minus_one": rung_m1, "harm": {str(k): v for k, v in harm.items()}, "step0": step0,
        "collapsed_cells": dep.get("collapsed", []), "flat_failed": flat_failed, "dense_failed": dense_failed, "base": {str(p): v for p, v in base.items()}, "calibration_states": dict(calibration_states) if calibration_states else None,
        "rates": {a: {str(k): rates[a][k] for k in ks} for a in core.ARMS},
        "note": "Self-check only; not independent review. The label is a registered outcome only after the auditor's recomputation (section 7).",
    }
    return out


def _per_parent_delta(nll_k: Mapping[int, Sequence[float | None]], nll_prev_k: Mapping[int, Sequence[float | None]], k: int, n: int) -> list[float | None]:
    """Per-parent delta of the run's own curve (printed, decides nothing): parent mean of the enabled read at U_{k-1} minus at U_k."""
    a = labels.parent_means(nll_prev_k[k])
    b = labels.parent_means(nll_k[k])
    return [None if (x is None or y is None) else x - y for x, y in zip(a, b, strict=True)]


def _step0(rd: _Reader, reg: Registry, arm: str, k: int, n: int) -> dict[str, float | None]:
    vals = []
    for c in range(n):
        key = core.nll_key(arm, rd.rates[arm][k], c, 0, core.READ_ENABLED)
        v = reg.get(key)
        vals.append(None if v is None else float(v))
    return {"enabled_mean": labels.mean_of(vals)}


def _analyse_oa(reg: Registry, cfg: Mapping[str, Any], rates: Mapping[str, Mapping[int, float]], th: Thresholds, bitwise: bool, n: int) -> dict[str, Any]:
    """OA: the old nine parents x 3 initialisations, 16,384 updates at r(arm, 0), registered pool. The same rule as R16. Prints NOT EVALUABLE (cause) and changes nothing (G17). The convergence reading is the run's own (deltarun) only: no run at r(arm, -1) exists for OA."""
    rd = _Reader(reg, cfg, rates, 0, n, oa=True)
    cause: list[str] = []
    base = {}
    for p in range(n // 3):
        e, r = reg.get(core.base_key(p, oa=True)), reg.get(core.base_key(p, core.READ_REPLAY, oa=True))
        if e is None or r is None or not _eq(float(e), float(r), bitwise):
            cause.append(f"BASE missing or fails replay on old parent {p}")
        base[p] = None if e is None else float(e)
    vals: dict[str, list[float | None]] = {a: [] for a in core.ARMS}
    runs: dict[str, list[float | None]] = {a: [] for a in core.ARMS}
    for a in core.ARMS:
        for c in range(n):
            if rd.run_failed(a, 0, c):
                cause.append(f"{a} run of OA cell {c} is a failed cell")
                vals[a].append(None)
                runs[a].append(None)
                continue
            e = rd.read(a, 0, c, rd.u(0), core.READ_ENABLED)
            prev = rd.read(a, 0, c, rd.u(-1), core.READ_ENABLED)
            rep, dis = rd.read(a, 0, c, rd.u(0), core.READ_REPLAY), rd.read(a, 0, c, rd.u(0), core.READ_DISABLED)
            b = base.get(c // 3)
            if e is None or prev is None or rep is None or dis is None or b is None:
                cause.append(f"{a} OA cell {c}: a value is not finite")
                vals[a].append(None)
                runs[a].append(None)
                continue
            if not _eq(rep, e, bitwise) or not _eq(dis, b, bitwise):
                cause.append(f"{a} OA cell {c}: replay or disabled differ")
            vals[a].append(e)
            runs[a].append(prev)
    B = [base.get(c // 3) for c in range(n)]
    if cause:
        return {"label": f"{labels.NOT_EVALUABLE} ({'; '.join(cause[:3])})"}
    c_f, c_d = labels.diff(B, vals[FLAT]), labels.diff(B, vals[DENSE])
    res = labels.replication(c_f, c_d, th)
    run_delta = {a: float(labels.mean_of(runs[a])) - float(labels.mean_of(vals[a])) for a in core.ARMS}  # type: ignore[arg-type]
    res["convergence_rung0_run_only"] = {a: labels.convergence_state(run_delta[a], run_delta[a], th.epsilon) for a in core.ARMS}
    res["delta_run"] = run_delta
    return res
