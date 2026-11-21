# ruff: noqa: E501
"""Part T registry and per-cell quantities (ADR-0025 sections 8.1 and 8.2). Pure functions over a registry of recorded numbers; nothing here trains, scores or reads a file.

Registry keys carry every distinguishing name (arm, order, replicate, read), so two records can never share a key (ruling L8): ``key("M-append", "AB", 0, "s:E_A")``. An arm that has no order or no
replicate (S0, the teachers, the lookup baselines per replicate) uses ``"-"`` for the field it lacks.

Reads (the names the scoring stages write): ``s:E_A`` and ``s:E_B``, the mean chrF-norm of the snapshot on the full panel; ``sub:{own|value|code|marker|words}:E_x``, the same on the 300-item subsample (own = the
arm's own score; value = value-permuted; code = word codes permuted; marker = marker-only; words = words-only); ``gen:token64`` and ``gen:first_marker``, the loss increase over the unmodified student in nats
per token at the two decision positions; ``dcon:A`` and ``dcon:B``, chrF on D_con; ``modification``, M-ii's relative change of the first-stage value rows.

Definitions: s_c(X) is the mean chrF-norm of X on E_c; gap closed G_c(X) = (s_c(X) - s_c(S0)) / (s_c(teacher c) - s_c(S0)), defined only if the denominator is at least 0.30 (full panel; on the subsample
the same with the subsample's scores, and a subsample denominator below 0.30 makes the cell's control conditions UNDEFINED, correction C3). First and second are the capabilities of the cell's order.
V1(X) is the stage-1 snapshot the arm continues (M1 for memory arms, D1 for dense arms, of the same cell). F(X) = s_first(V1) - s_first(X after stage 2); rho(X) = G_first(X after stage 2) / G_first(V1); rho, F
and RET are defined for an arm's cell only if G_first(V1(X)) >= 0.50, otherwise NOT EVALUABLE: FIRST NOT ACQUIRED.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .common import core

REPLICATES = (0, 1, 2)
ORDERS = core.ORDERS
CELLS = tuple((r, o) for r in REPLICATES for o in ORDERS)  # six cells per sequential arm
PANEL = {"A": "E_A", "B": "E_B"}
MEMORY_ARMS = ("M1", "M-append", "M-seq", "M-ii", "M-joint")
V1_OF = {"M-append": "M1", "M-seq": "M1", "M-ii": "M1", "D-append": "D1", "D-seq": "D1"}
SINGLE_OF = {"M-append": "M1", "M-seq": "M1", "M-ii": "M1", "D-append": "D1", "D-seq": "D1"}  # the single-teacher module of the same type (ACQ2's reference)
CONTROL_CONDITIONS = ("value", "code", "marker", "words")
GEN_POSITIONS = ("token64", "first_marker")
NONE = "-"


class Missing(KeyError):
    """A registered record is absent (INCOMPLETE if no error is recorded for it)."""


def key(arm: str, order: str, rep: int | str, read: str) -> str:
    if order not in (*ORDERS, NONE):
        raise ValueError(f"order {order!r}")
    return f"{arm}|{order}|{rep}|{read}"


def first(order: str) -> str:
    return order[0]


def second(order: str) -> str:
    return order[1]


class Registry:
    """The registry: key -> number. ``get`` raises ``Missing``; ``items`` lets the study status scan for non-finite values."""

    def __init__(self, values: Mapping[str, float] | None = None) -> None:
        self.values: dict[str, float] = dict(values or {})

    def put(self, arm: str, order: str, rep: int | str, read: str, value: float) -> None:
        k = key(arm, order, rep, read)
        if k in self.values:
            raise ValueError(f"{k} is already registered")
        self.values[k] = float(value)

    def get(self, arm: str, order: str, rep: int | str, read: str) -> float:
        k = key(arm, order, rep, read)
        if k not in self.values:
            raise Missing(k)
        return self.values[k]

    def has(self, arm: str, order: str, rep: int | str, read: str) -> bool:
        return key(arm, order, rep, read) in self.values

    def nonfinite(self) -> list[str]:
        return sorted(k for k, v in self.values.items() if not math.isfinite(v))


def gap(arm_score: float, s0: float, teacher: float, minimum: float) -> float | None:
    """(arm - S0) / (teacher - S0), None if the denominator is below ``minimum`` (0.30) or a value is not finite."""
    if not all(math.isfinite(x) for x in (arm_score, s0, teacher)):
        return None
    d = teacher - s0
    return None if d < minimum else (arm_score - s0) / d


@dataclass
class Thresholds:
    gap_denominator_min: float
    acq_gap_min: float
    acq_margin_min: float
    acq_marker_only_max: float
    acq2_ratio_min: float
    ret_forgetting_max: float
    ret_rho_min: float
    negative_acquisition: float
    negative_retention: float
    forgetting_pressure_cells: int
    forgetting_pressure_second_min: float
    forgetting_pressure_rho_max: float
    retention_negative_min_cells: int
    control_failed_gap: float
    gen_loss_margin: float
    dense_margin: float
    lookup_sufficient_margin: float
    lookup_adds_margin: float
    second_not_acquired: float
    first_not_acquired_g: float
    modification_dcon_tolerance: float
    modification_floor: float
    pilot_gap_min: float

    @staticmethod
    def from_config(cfg: Mapping[str, Any]) -> "Thresholds":
        g, d, p = cfg["gates"], cfg["data"], cfg["pilot"]
        return Thresholds(
            d["gap_denominator_min"], g["acq_gap_min"], g["acq_margin_min"], g["acq_marker_only_max"], g["acq2_ratio_min"], g["ret_forgetting_max"], g["ret_rho_min"], g["negative_acquisition"], g["negative_retention"],
            g["forgetting_pressure_cells"], g["forgetting_pressure_second_min"], g["forgetting_pressure_rho_max"], g["retention_negative_min_cells"], g["control_failed_gap"], g["gen_loss_margin"], g["dense_margin"],
            g["lookup_sufficient_margin"], g["lookup_adds_margin"], g["second_not_acquired"], d["first_not_acquired_g"], g["modification_dcon_tolerance"], g["modification_floor"], p["gap_min"],
        )  # fmt: skip


class Quantities:
    """Per-cell quantities from a registry (sections 8.1, 8.2). Every method returns None where the quantity is undefined; nothing here turns an undefined value into a pass."""

    def __init__(self, reg: Registry, th: Thresholds) -> None:
        self.reg, self.th = reg, th

    # --- panel level ---------------------------------------------------------------------------------------------------------------------------
    def s0(self, cap: str) -> float:
        return self.reg.get("S0", NONE, NONE, f"s:{PANEL[cap]}")

    def teacher(self, cap: str) -> float:
        return self.reg.get("TEACHER", NONE, NONE, f"s:{PANEL[cap]}")

    def denominator(self, cap: str) -> float:
        return self.teacher(cap) - self.s0(cap)

    def gap_defined(self) -> bool:
        return all(self.denominator(c) >= self.th.gap_denominator_min for c in core.TASKS)

    def sub_denominator(self, cap: str) -> float:
        return self.reg.get("TEACHER", NONE, NONE, f"sub:own:{PANEL[cap]}") - self.reg.get("S0", NONE, NONE, f"sub:own:{PANEL[cap]}")

    def controls_defined(self, cap: str) -> bool:
        """Correction C3: a subsample denominator below 0.30 makes the control conditions of the capability undefined."""
        return self.sub_denominator(cap) >= self.th.gap_denominator_min

    # --- gaps ----------------------------------------------------------------------------------------------------------------------------------
    def score(self, arm: str, order: str, rep: int | str, cap: str) -> float:
        return self.reg.get(arm, order, rep, f"s:{PANEL[cap]}")

    def G(self, arm: str, order: str, rep: int | str, cap: str) -> float | None:
        return gap(self.score(arm, order, rep, cap), self.s0(cap), self.teacher(cap), self.th.gap_denominator_min)

    def G_sub(self, arm: str, order: str, rep: int | str, cap: str, cond: str) -> float | None:
        p = PANEL[cap]
        return gap(self.reg.get(arm, order, rep, f"sub:{cond}:{p}"), self.reg.get("S0", NONE, NONE, f"sub:own:{p}"), self.reg.get("TEACHER", NONE, NONE, f"sub:own:{p}"), self.th.gap_denominator_min)

    # --- first / second ----------------------------------------------------------------------------------------------------------------------
    def G_first(self, arm: str, order: str, rep: int) -> float | None:
        return self.G(arm, order, rep, first(order))

    def G_second(self, arm: str, order: str, rep: int) -> float | None:
        return self.G(arm, order, rep, second(order))

    def v1_arm(self, arm: str) -> str:
        return V1_OF[arm]

    def G_first_v1(self, arm: str, order: str, rep: int) -> float | None:
        return self.G(self.v1_arm(arm), order, rep, first(order))

    def evaluable(self, arm: str, order: str, rep: int) -> bool:
        """rho, F and RET are defined only if G_first(V1(X)) >= 0.50 (and the gap itself is defined)."""
        g = self.G_first_v1(arm, order, rep)
        return g is not None and g >= self.th.first_not_acquired_g

    def rho(self, arm: str, order: str, rep: int) -> float | None:
        if not self.evaluable(arm, order, rep):
            return None
        g2, g1 = self.G_first(arm, order, rep), self.G_first_v1(arm, order, rep)
        return None if g2 is None or g1 is None else g2 / g1

    def forgetting(self, arm: str, order: str, rep: int) -> float | None:
        """F(X) = s_first(V1) - s_first(X after stage 2), defined only where rho is."""
        if not self.evaluable(arm, order, rep):
            return None
        c = first(order)
        return self.score(self.v1_arm(arm), order, rep, c) - self.score(arm, order, rep, c)

    # --- conditions --------------------------------------------------------------------------------------------------------------------------
    def margin_ok(self, arm: str, order: str, rep: int, cap: str) -> bool | None:
        """The control parts of ACQ1 / ACQ2: G(arm) - max(G value-permuted, G code-permuted) >= 0.30 and G marker-only <= 0.25, on the subsample. None if the controls are undefined (they then FAIL the cell)."""
        if not self.controls_defined(cap):
            return None
        own, v, c, m = (self.G_sub(arm, order, rep, cap, k) for k in ("own", "value", "code", "marker"))
        if None in (own, v, c, m):
            return None
        assert own is not None and v is not None and c is not None and m is not None
        return (own - max(v, c)) >= self.th.acq_margin_min and m <= self.th.acq_marker_only_max

    def acq1(self, order: str, rep: int) -> bool:
        g = self.G_first("M1", order, rep)
        return g is not None and g >= self.th.acq_gap_min and self.margin_ok("M1", order, rep, first(order)) is True

    def acq2(self, arm: str, order: str, rep: int) -> bool:
        """G_second(X) >= 0.50 and >= 0.80 x G of the single-teacher module of the same type on that capability in the same replicate (M1 / D1 of the OTHER order); for memory arms the same margin and
        marker-only limits on the second stage's controls."""
        g2 = self.G_second(arm, order, rep)
        other = "BA" if order == "AB" else "AB"
        ref = self.G(SINGLE_OF[arm], other, rep, second(order))
        if g2 is None or ref is None or g2 < self.th.acq_gap_min or g2 < self.th.acq2_ratio_min * ref:
            return False
        return True if arm not in MEMORY_ARMS else self.margin_ok(arm, order, rep, second(order)) is True

    def ret(self, arm: str, order: str, rep: int) -> bool:
        f, r = self.forgetting(arm, order, rep), self.rho(arm, order, rep)
        return f is not None and r is not None and f <= self.th.ret_forgetting_max and r >= self.th.ret_rho_min

    def control_gap_reads(self, arm: str, order: str) -> list[str]:
        """The capabilities whose permutation controls CONTROL-FAILED reads for a memory arm's cell: M1 the first; the stage-2 arms the second; M-joint both (each on its own panel)."""
        if arm == "M1":
            return [first(order)]
        if arm == "M-joint":
            return list(core.TASKS)
        return [second(order)]


def cells_where(preds: Iterable[tuple[int, str, bool]]) -> dict[str, list[int]]:
    """Passing replicates per order, for 'passing cells per order are printed'."""
    out: dict[str, list[int]] = {o: [] for o in ORDERS}
    for rep, order, ok in preds:
        if ok:
            out[order].append(rep)
    return out
