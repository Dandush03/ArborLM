# ruff: noqa: E501
"""P10IS3 analysis (ADR-0026 sections 5.2, 6, 12): a pure function over a registry (a dict key -> value, keys of ``core``), no torch, no IO.

``analyse`` REFUSES (raises ``EngineeringStop``) while any ``item_error`` run exists, while a required cell or evaluation is missing (denominators are never reduced), or while the registry is empty.
Only the failures the specification names as scientific make a label NOT EVALUABLE: BASE missing or failing, disabled != BASE, replay != enabled, joint outside 1e-6, a dense failed cell (line 2).
A rate table is ``{"rates": {"<arm>|<regime>": {"<duration>": rate}}, "edge": {"<arm>|<regime>": bool}}`` (frozen at Decision 2).
"""

import math
import statistics
from collections.abc import Mapping, Sequence
from typing import Any

from . import core, labels
from .core import (
    DENSE,
    FLAT,
    FRESH,
    REGIME_ARMS,
    REGIMES,
    REP,
    REPU,
    TREE,
    EngineeringStop,
    Thresholds,
)

Registry = Mapping[str, Any]
RateTable = Mapping[str, Any]
DESCRIPTIVE_CKPTS_KEY = "checkpoints"


def rate_of(rt: RateTable, arm: str, regime: str, duration: int) -> float:
    return float(rt["rates"][f"{arm}|{regime}"][str(duration)])


def refuse_if_item_errors(reg: Registry) -> None:
    errors = sorted(k for k, v in reg.items() if k.startswith("run|") and isinstance(v, Mapping) and v.get("status") == "item_error")
    if errors:
        raise EngineeringStop(f"ENGINEERING STOP — ITEM ERRORS: {len(errors)} run(s), first {errors[0]}; no line is labelled")
    if not reg:
        raise EngineeringStop("ENGINEERING STOP — the registry is empty")


def _need(reg: Registry, key: str) -> Any:
    if key not in reg:
        raise EngineeringStop(f"ENGINEERING STOP — a required evaluation is missing: {key}; nothing is labelled, denominators are never reduced")
    return reg[key]


def run_failed(reg: Registry, arm: str, regime: str, rate: float, c: int) -> bool:
    r = reg.get(core.run_key(arm, regime, rate, c))
    return isinstance(r, Mapping) and r.get("status") == "failed_cell"


def nll(reg: Registry, arm: str, regime: str, rate: float, c: int, ckpt: int, read: str, draw: int = 0) -> float | None:
    """The value of one read, or None if it is non-finite (a failed run has None at every checkpoint)."""
    if run_failed(reg, arm, regime, rate, c):
        return None
    v = _need(reg, core.nll_key(arm, regime, rate, c, ckpt, read, draw))
    return None if v is None or not math.isfinite(float(v)) else float(v)


def mean_draws(reg: Registry, arm: str, regime: str, rate: float, c: int, ckpt: int, read: str, draws: int) -> float | None:
    """Ruling 12: the draws' NLLs are averaged first."""
    vals = [nll(reg, arm, regime, rate, c, ckpt, read, d) for d in range(draws)]
    return None if any(v is None for v in vals) else sum(float(v) for v in vals if v is not None) / draws


def base_nll(reg: Registry, parent: int) -> float | None:
    v = reg.get(core.base_key(parent))
    return None if v is None or not math.isfinite(float(v)) else float(v)


def base_ok(reg: Registry, parents: Sequence[int], bitwise: bool, tol: float) -> tuple[bool, list[str]]:
    """BASE present and replaying equal on every parent (bitwise on the platform of record, within ``tol`` elsewhere)."""
    bad = []
    for p in parents:
        a, b = reg.get(core.base_key(p)), reg.get(core.base_key(p, "replay"))
        if a is None or b is None or not math.isfinite(float(a)) or not math.isfinite(float(b)):
            bad.append(core.parent_label(p))
        elif (float(a) != float(b)) if bitwise else (abs(float(a) - float(b)) > tol):
            bad.append(core.parent_label(p))
    return not bad, bad


def _sub(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def stats(v: Sequence[float | None]) -> dict[str, Any]:
    fin = [x for x in v if x is not None]
    return {"n": len(v), "n_nonfinite": len(v) - len(fin), "mean": statistics.fmean(fin) if len(fin) == len(v) and fin else None, "sd": statistics.stdev(fin) if len(fin) > 1 else None, "min": min(fin) if fin else None, "max": max(fin) if fin else None, "n_positive": sum(1 for x in fin if x > 0), "n_negative": sum(1 for x in fin if x < 0), "per_parent": labels.parent_means(v), "per_seed": [labels.mean_of([v[i] for i in range(s, len(v), 3)]) for s in range(3)]}  # fmt: skip


class Ctx:
    """The inputs of one analysis: registry, rate table, cells (index -> parent), thresholds, durations."""

    def __init__(self, reg: Registry, rt: RateTable, cells: Mapping[int, int], th: Thresholds, cfg: Mapping[str, Any], *, bitwise: bool = True) -> None:
        self.reg, self.rt, self.cells, self.th, self.bitwise = reg, rt, dict(cells), th, bitwise
        self.order = sorted(self.cells)
        self.u = int(cfg["duration"]["u_star"])
        self.ckpts = [int(x) for x in cfg["duration"]["checkpoints"]]
        self.draws_p, self.draws_x = int(cfg["controls"]["p_used_draws"]), int(cfg["controls"]["x_draws"])
        self.parents = sorted(set(self.cells.values()))

    def rate(self, arm: str, regime: str, d: int | None = None) -> float:
        return rate_of(self.rt, arm, regime, d or self.u)

    def vals(self, arm: str, regime: str, ckpt: int, read: str, *, rate: float | None = None, draws: int = 1) -> list[float | None]:
        r = self.rate(arm, regime, ckpt) if rate is None else rate
        return [mean_draws(self.reg, arm, regime, r, c, ckpt, read, draws) for c in self.order]

    def base(self) -> list[float | None]:
        return [base_nll(self.reg, self.cells[c]) for c in self.order]

    def gain(self, arm: str, regime: str, ckpt: int | None = None, *, rate: float | None = None) -> list[float | None]:
        """C or C_dense: B - H."""
        k = ckpt or self.u
        return [_sub(b, h) for b, h in zip(self.base(), self.vals(arm, regime, k, core.READ_ENABLED, rate=rate), strict=True)]

    def effect(self, arm: str, regime: str, read: str, ckpt: int | None = None, draws: int = 1) -> list[float | None]:
        k = ckpt or self.u
        return [_sub(a, h) for a, h in zip(self.vals(arm, regime, k, read, draws=draws), self.vals(arm, regime, k, core.READ_ENABLED), strict=True)]

    def collapsed(self, arm: str, regime: str) -> list[bool]:
        out = []
        for c in self.order:
            if run_failed(self.reg, arm, regime, self.rate(arm, regime), c) or nll(self.reg, arm, regime, self.rate(arm, regime), c, self.u, core.READ_ENABLED) is None:
                out.append(False)  # a failed cell has no used-slot set; it is already counted as failing everything
                continue
            s = _need(self.reg, core.stat_key(arm, regime, self.rate(arm, regime), c, self.u, "used_slots"))
            out.append(s is not None and int(s) < 2)
        return out

    def mean_curve(self, arm: str, regime: str) -> dict[int, float | None]:
        """Along the primary-rate run (the run at the rate for U*): the mean enabled NLL at each checkpoint (None with a failed cell or a non-finite value)."""
        r = self.rate(arm, regime)
        out: dict[int, float | None] = {}
        for k in self.ckpts:
            out[k] = labels.mean_of(self.vals(arm, regime, k, core.READ_ENABLED, rate=r))
        return out

    def step0(self, arm: str, regime: str) -> float | None:
        """The mean step-0 enabled NLL of the primary run, if every cell has it (a checkpoint: PAST BEST counts it as one)."""
        r = self.rate(arm, regime)
        keys = [core.nll_key(arm, regime, r, c, 0, core.READ_ENABLED) for c in self.order]
        return labels.mean_of([self.reg[k] for k in keys]) if all(k in self.reg for k in keys) else None

    def integrity(self, arm: str, regime: str) -> list[str]:
        """Section 10: disabled != BASE, replay != enabled (both bitwise on the platform of record, 1e-6 elsewhere) and, where the read exists, joint outside 1e-6, at EVERY evaluated checkpoint (512 to U*) of the run at the rate
        for that checkpoint and of the primary run (ruling: "on any cell" names no checkpoint; the reading under which fewer results count). A failed cell and a non-finite enabled value are not integrity cases."""
        bad: list[str] = []
        tol = self.th.tolerance_joint
        neq = (lambda x, y: x != y) if self.bitwise else (lambda x, y: abs(x - y) > tol)
        # Section 6.1 takes precedence (lead's ruling N3): a cell whose registered value at U* is non-finite, or whose run failed, is a FAILED CELL; no integrity check at an earlier checkpoint turns it into NOT EVALUABLE
        failed = {c for c in self.order if run_failed(self.reg, arm, regime, self.rate(arm, regime), c) or nll(self.reg, arm, regime, self.rate(arm, regime), c, self.u, core.READ_ENABLED) is None}
        for k in self.ckpts:
            for r in sorted({self.rate(arm, regime, k), self.rate(arm, regime)}):
                for c in self.order:
                    if c in failed or run_failed(self.reg, arm, regime, r, c):
                        continue
                    en = nll(self.reg, arm, regime, r, c, k, core.READ_ENABLED)
                    if en is None:
                        continue
                    rep, dis = (nll(self.reg, arm, regime, r, c, k, x) for x in (core.READ_REPLAY, core.READ_DISABLED))
                    b = base_nll(self.reg, self.cells[c])
                    where = f"{arm}|{regime}|c{c}|u{k}|r{core.rate_label(r)}"
                    if rep is None or neq(rep, en):
                        bad.append(f"{where}: replay != enabled")
                    if dis is None or b is None or neq(dis, b):
                        bad.append(f"{where}: disabled != BASE")
                    if arm == TREE and core.nll_key(arm, regime, r, c, k, core.READ_JOINT) in self.reg:
                        j = nll(self.reg, arm, regime, r, c, k, core.READ_JOINT)
                        if j is None or abs(j - en) > tol:
                            bad.append(f"{where}: joint permutation outside {tol}")
        return bad


def regime_result(ctx: Ctx, regime: str, base_good: bool) -> dict[str, Any]:
    """Both lines for one regime, with the tags of section 6.4."""
    th = ctx.th
    arms = REGIME_ARMS[regime]
    conv, past, curves = {}, {}, {}
    for a in arms:
        curve = ctx.mean_curve(a, regime)
        curves[a] = curve
        failed = any(v is None for v in ctx.vals(a, regime, ctx.u, core.READ_ENABLED))
        conv[a] = labels.convergence_tag(curve.get(8192), curve.get(ctx.u), th.epsilon, failed=failed)
        s0 = ctx.step0(a, regime)
        past[a] = labels.past_best({**({0: s0} if s0 is not None else {}), **curve}, ctx.u, th.past_best_margin, failed=failed) if regime in (REP, REPU) else {"tag": None, "flag": False}
    integ = {a: ctx.integrity(a, regime) for a in arms}
    out: dict[str, Any] = {"regime": regime, "convergence": conv, "past_best": past, "curves": curves, "integrity_problems": integ}
    # line 1 (M-TREE)
    c_t = ctx.gain(TREE, regime)
    p_t = ctx.effect(TREE, regime, core.READ_P_USED, draws=ctx.draws_p)
    x_t = ctx.effect(TREE, regime, core.READ_X_MEAN)
    stop1 = (not base_good) or bool(integ[TREE])
    l1 = labels.line1(c_t, p_t, x_t, th, integrity_stop=stop1, collapsed=ctx.collapsed(TREE, regime))
    out["line1"] = labels.apply_tags_line1(l1, regime=regime, conv=conv[TREE], past=past[TREE], edge=bool(ctx.rt["edge"].get(f"{TREE}|{regime}")))
    out["line1"]["detail"] = l1
    out["line1"]["collapsed_cells"] = len(l1["collapsed"])  # printed beside the label: one collapsed cell can decide D2
    # line 2, TREE and FLAT
    c_d = ctx.gain(DENSE, regime)
    for mem in (TREE, FLAT):
        if mem not in arms:
            continue
        c_m = c_t if mem == TREE else ctx.gain(FLAT, regime)
        stop2 = (not base_good) or bool(integ[mem]) or bool(integ[DENSE])
        l2 = labels.line2(c_m, c_d, th, integrity_stop=stop2)
        mean_h = labels.mean_of(ctx.vals(mem, regime, ctx.u, core.READ_ENABLED))
        mean_a = labels.mean_of(ctx.vals(DENSE, regime, ctx.u, core.READ_ENABLED))
        tagged = labels.apply_tags_line2(l2, regime=regime, mem_name=mem, mem_edge=bool(ctx.rt["edge"].get(f"{mem}|{regime}")), dense_edge=bool(ctx.rt["edge"].get(f"{DENSE}|{regime}")), mean_nll_mem=mean_h, mean_nll_dense=mean_a, mem_conv=conv[mem], dense_conv=conv[DENSE], mem_past=past[mem], dense_past=past[DENSE])
        tagged["detail"] = l2
        out[f"line2_{'tree' if mem == TREE else 'flat'}"] = tagged
    if FLAT in arms:  # M-FLAT's descriptive D1-D3 (never a label that qualifies anything)
        c_f = ctx.gain(FLAT, regime)
        out["flat_d1d3"] = labels.line1(c_f, ctx.effect(FLAT, regime, core.READ_P_USED, draws=ctx.draws_p), ctx.effect(FLAT, regime, core.READ_X_MEAN), th, integrity_stop=(not base_good) or bool(integ[FLAT]), collapsed=ctx.collapsed(FLAT, regime))["conditions"]
    return out


def routing(ctx: Ctx, regime: str) -> dict[str, Any]:
    """Section 6.6 (descriptive, fixed reading rule), REP and FRESH."""
    th, out = ctx.th, {}
    rows: dict[int, dict[str, Any]] = {}
    for k in ctx.ckpts:
        h_t = ctx.vals(TREE, regime, k, core.READ_ENABLED)
        h_f = ctx.vals(FLAT, regime, k, core.READ_ENABLED)
        g_train = [_sub(a, b) for a, b in zip(h_t, h_f, strict=True)]
        g_read = [_sub(a, b) for a, b in zip(h_t, ctx.vals(TREE, regime, k, core.READ_EXHAUSTIVE), strict=True)]
        g_prior = [_sub(a, b) for a, b in zip(ctx.vals(TREE, regime, k, core.READ_PRIOR_OFF), h_t, strict=True)]
        prim = [_sub(a, b) for a, b in zip(ctx.vals(TREE, regime, k, core.READ_ENABLED, rate=ctx.rate(TREE, regime)), ctx.vals(FLAT, regime, k, core.READ_ENABLED, rate=ctx.rate(FLAT, regime)), strict=True)]
        rows[k] = {"G_train": g_train, "G_read": g_read, "G_prior": g_prior, "G_train_label": labels.gap_label(g_train, th, positive="TREE BEHIND", negative="TREE AHEAD"), "G_read_label": labels.gap_label(g_read, th, positive="RESTRICTION COSTS", negative="RESTRICTION HELPS"), "G_train_primary_rate_mean": labels.mean_of(prim), "G_prior_stats": stats(g_prior)}  # fmt: skip
    first, last = ctx.ckpts[0], ctx.ckpts[-1]
    out["rows"] = rows
    for name in ("G_train", "G_read"):
        delta = [_sub(b, a) for a, b in zip(rows[first][name], rows[last][name], strict=True)]
        out[f"{name}_trend"] = {"trend": labels.trend(rows[first][f"{name}_label"], rows[last][f"{name}_label"]), "delta_G": stats(delta)}
    return out


def six_parent_readout(ctx: Ctx, regime: str, calibration_parents: Sequence[int]) -> dict[str, Any]:
    """Section 6.7: both lines on the parents not used in calibration, as plain figures (no label, no threshold applied)."""
    keep = [i for i, c in enumerate(ctx.order) if ctx.cells[c] not in calibration_parents]
    pick = lambda v: [v[i] for i in keep]  # noqa: E731
    c_t, c_d = pick(ctx.gain(TREE, regime)), pick(ctx.gain(DENSE, regime))
    p, x = pick(ctx.effect(TREE, regime, core.READ_P_USED, draws=ctx.draws_p)), pick(ctx.effect(TREE, regime, core.READ_X_MEAN))
    q = [_sub(a, b) for a, b in zip(c_t, c_d, strict=True)]
    half = ctx.th.half
    return {"cells": len(keep), "parents": len(set(ctx.cells[ctx.order[i]] for i in keep)), "C": stats(c_t), "C_dense": stats(c_d), "Q": stats(q), "P_used": stats(p), "X_mean": stats(x),
            "n_C_positive": sum(1 for v in c_t if v is not None and v > 0), "n_P_half": sum(1 for a, b in zip(c_t, p, strict=True) if a is not None and a > 0 and b is not None and b >= half * a),
            "n_X_half": sum(1 for a, b in zip(c_t, x, strict=True) if a is not None and a > 0 and b is not None and b >= half * a), "n_Q_within": sum(1 for v in q if v is not None and v >= ctx.th.dense_tolerance), "n_Q_ahead": sum(1 for v in q if v is not None and v > 0)}  # fmt: skip


def descriptive(ctx: Ctx, regime: str) -> dict[str, Any]:
    """Section 6.7: every quantity at every checkpoint for every arm, by per-duration rate. No best seed, cell or checkpoint is selected."""
    out: dict[str, Any] = {}
    for a in REGIME_ARMS[regime]:
        per: dict[str, Any] = {}
        for k in ctx.ckpts:
            row: dict[str, Any] = {"C": stats(ctx.gain(a, regime, k)), "H_mean_nll": labels.mean_of(ctx.vals(a, regime, k, core.READ_ENABLED))}
            if a in (TREE, FLAT):
                h = ctx.vals(a, regime, k, core.READ_ENABLED)
                b = ctx.base()
                for nm, rd, dr in (("P_all", core.READ_P_ALL, 1), ("P_used", core.READ_P_USED, ctx.draws_p), ("X_mean", core.READ_X_MEAN, 1), ("X", core.READ_X, ctx.draws_x)):
                    eff = ctx.effect(a, regime, rd, k, dr)
                    row[nm] = stats(eff)
                    hv = ctx.vals(a, regime, k, rd, draws=dr)
                    row[f"B-H_{nm}"] = stats([_sub(bb, x) for bb, x in zip(b, hv, strict=True)])
                    row[f"n_{nm}_above_baseline"] = sum(1 for bb, x in zip(b, hv, strict=True) if bb is not None and x is not None and x > bb)
                row["H_mean_read"] = ctx.vals(a, regime, k, core.READ_X_MEAN)
                if k > 0 and h:
                    row["used_slots"] = [ctx.reg.get(core.stat_key(a, regime, ctx.rate(a, regime, k), c, k, "used_slots")) for c in ctx.order]
                    row["branch_entropy"] = [ctx.reg.get(core.stat_key(a, regime, ctx.rate(a, regime, k), c, k, "branch_entropy")) for c in ctx.order]
            else:
                row["X_dense"] = stats(ctx.effect(a, regime, core.READ_X_DENSE, k, ctx.draws_x))
                row["X_mean_dense"] = stats(ctx.effect(a, regime, core.READ_X_MEAN_DENSE, k))
            per[str(k)] = row
        out[a] = per
    return out


def contrasts(ctx_by_regime: Mapping[str, Ctx]) -> dict[str, Any]:
    """Section 3.3 contrasts for C, C_dense and Q at the first checkpoint and U*, plus P_used and X_mean at both (section 3.4)."""
    out: dict[str, Any] = {}
    for reg_name, ctx in ctx_by_regime.items():
        row: dict[str, Any] = {}
        for k in (ctx.ckpts[0], ctx.u):
            c, cd = ctx.gain(TREE, reg_name, k), ctx.gain(DENSE, reg_name, k)
            row[str(k)] = {"C_mean": labels.mean_of(c), "C_dense_mean": labels.mean_of(cd), "Q_mean": labels.mean_of([_sub(a, b) for a, b in zip(c, cd, strict=True)]),
                           "P_used_mean": labels.mean_of(ctx.effect(TREE, reg_name, core.READ_P_USED, k, ctx.draws_p)), "X_mean_mean": labels.mean_of(ctx.effect(TREE, reg_name, core.READ_X_MEAN, k))}  # fmt: skip
        out[reg_name] = row
    return out


def anchor(ctx: Ctx, p4_rate: float) -> dict[str, Any]:
    """P4-rate anchor (section 6.7): REP, an arm whose frozen rate for U* is not 0.003 was also run at 0.003 to U*; descriptive. Enabled reads only."""
    out: dict[str, Any] = {}
    for a in (TREE, DENSE):
        if abs(ctx.rate(a, REP) - p4_rate) > 0:
            out[a] = {"rate_for_ustar": ctx.rate(a, REP), "C_at_p4_rate": stats(ctx.gain(a, REP, ctx.u, rate=p4_rate)), "C_at_frozen_rate": stats(ctx.gain(a, REP, ctx.u))}
    return out


def analyse(reg: Registry, rt: RateTable, cfg: Mapping[str, Any], *, cells: Mapping[int, int] | None = None, th: Thresholds | None = None, bitwise: bool = True, calibration_parents: Sequence[int] = core.CAL_PARENTS) -> dict[str, Any]:
    """The whole analysis. Refuses on item errors or a missing evaluation."""
    refuse_if_item_errors(reg)
    cells = cells or {c: core.parent_of(c) for c in range(int(cfg["thresholds"]["cells"]))}
    th = th or Thresholds.from_config(cfg)
    ctx = Ctx(reg, rt, cells, th, cfg, bitwise=bitwise)
    good, bad = base_ok(reg, ctx.parents, bitwise, th.tolerance_joint)
    per = {g: regime_result(ctx, g, good) for g in REGIMES}
    ctxs = {g: ctx for g in REGIMES}
    l1 = {g: per[g]["line1"] for g in REGIMES}
    l2 = {g: per[g]["line2_tree"] for g in REGIMES}
    reg1, reg2 = labels.registered_line(l1), labels.registered_line(l2)
    pos = labels.registered_positive(l1[FRESH]["label"], l2[FRESH]["label"])  # the FINAL label: an INCONCLUSIVE label is never positive
    route = labels.route_a(l1[FRESH]["label"], (l2[FRESH]["base_label"], l2[FRESH]["label"]), per[FRESH]["convergence"][DENSE])
    return {
        "kind": "analysis", "base_ok": good, "base_bad": bad, "regimes": per, "line1": reg1, "line2_tree": reg2, "line2_flat": labels.registered_line({g: per[g]["line2_flat"] for g in (REP, FRESH)} | {REPU: {"label": None}}),
        "registered_positive": pos, "route_a": route, "routing": {g: routing(ctx, g) for g in (REP, FRESH)}, "descriptive": {g: descriptive(ctx, g) for g in REGIMES}, "contrasts": contrasts(ctxs),
        "six_parent": {g: six_parent_readout(ctx, g, calibration_parents) for g in REGIMES}, "anchor": anchor(ctx, float(cfg["rates"]["p4_rate"])),
        "limits": ["REP and REP-U endpoints largely measure how each arm behaves once it can fit its training set (64 passes over 131,072 target bytes); a competitiveness label on repeated data can come from the dense adapter overfitting faster."],
    }  # fmt: skip
