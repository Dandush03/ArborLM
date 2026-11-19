# ruff: noqa: E501
"""P10IS6 synthetic registries with known answers (tests, the synthetic-registry gate and the DRY analysis). No torch.

``registry(cfg, spec)`` builds the analysis registry of a made-up study: a distinct rate per rung (so a rung's records can never share a key), baseline B_c = 3.0 + 0.01 c for every cell, every value a plain number worked out
from the spec. The expected labels of the tests are worked out by hand from the spec, never by the analysis' own helpers.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core
from .core import DENSE, FLAT

RATES_FLAT = {-1: 0.0001, 0: 0.0003, 1: 0.001, 2: 0.003, 3: 0.01, 4: 0.03, 5: 0.1}
RATES_DENSE = {-1: 0.0003, 0: 0.001, 1: 0.003, 2: 0.01, 3: 0.03, 4: 0.1, 5: 0.3}


def rate_table(k_max: int = 4) -> dict[str, Any]:
    return {"rates": {FLAT: {str(k): RATES_FLAT[k] for k in range(-1, k_max + 1)}, DENSE: {str(k): RATES_DENSE[k] for k in range(-1, k_max + 1)}}}


@dataclass
class ArmSpec:
    """gain[k] = B - mean NLL at rung k (k = -1..k_max); drun[k] = deltarun at rung k (k = 0..k_max). ``cell`` adds a per-cell offset to the NLL at rung k (cell list), for the count rows."""

    gain: Mapping[int, float]
    drun: Mapping[int, float] | None = None
    cell: Mapping[int, Sequence[float]] = field(default_factory=dict)


@dataclass
class Spec:
    flat: ArmSpec
    dense: ArmSpec
    k_max: int = 4
    cells: int = 27
    p_used: Callable[[int, int], float] = lambda k, c: 0.02  # noqa: E731  P_used(k, c) = H_used - H
    x_mean: Callable[[int, int], float] = lambda k, c: 0.02  # noqa: E731
    v_mean: Callable[[int, int], float] = lambda k, c: 0.01  # noqa: E731
    used_slots: Callable[[int, int], int] = lambda k, c: 300  # noqa: E731
    failed: frozenset[tuple[str, int, int]] = frozenset()  # (arm, rung, cell): the run of that rung and cell is a failed cell
    nonfinite_enabled: frozenset[tuple[str, int, int]] = frozenset()
    bad_disabled: frozenset[tuple[str, int, int]] = frozenset()
    bad_replay: frozenset[tuple[str, int, int]] = frozenset()
    base_missing: frozenset[int] = frozenset()
    base_bad_replay: frozenset[int] = frozenset()
    nonfinite_draw: frozenset[tuple[int, int]] = frozenset()  # (rung, cell): a P_used draw is non-finite


def baseline(c: int) -> float:
    return 3.0 + 0.01 * c


def registry(cfg: Mapping[str, Any], spec: Spec) -> dict[str, Any]:
    reg: dict[str, Any] = {}
    n, km = spec.cells, spec.k_max
    for p in range(n // 3):
        if p not in spec.base_missing:
            b = baseline(3 * p)
            reg[core.base_key(p)] = b
            reg[core.base_key(p, core.READ_REPLAY)] = b + (1e-3 if p in spec.base_bad_replay else 0.0)
    for arm, aspec, rates in ((FLAT, spec.flat, RATES_FLAT), (DENSE, spec.dense, RATES_DENSE)):
        for k in range(-1, km + 1):
            r = rates[k]
            for c in range(n):
                b = baseline(3 * (c // 3))
                reg[core.run_key(arm, r, c)] = {"status": "failed_cell" if (arm, k, c) in spec.failed else "ok", "reason": None}
                if (arm, k, c) in spec.failed:
                    continue
                off = aspec.cell[k][c] if k in aspec.cell else 0.0
                v = b - aspec.gain[k] + off
                u = core.rung_updates(cfg, k)
                enabled = None if (arm, k, c) in spec.nonfinite_enabled else v
                reg[core.nll_key(arm, r, c, u, core.READ_ENABLED)] = enabled
                if enabled is None:
                    reg[core.nll_key(arm, r, c, u, core.READ_REPLAY)] = None
                    reg[core.nll_key(arm, r, c, u, core.READ_DISABLED)] = None
                else:
                    reg[core.nll_key(arm, r, c, u, core.READ_REPLAY)] = v + (1e-3 if (arm, k, c) in spec.bad_replay else 0.0)
                    reg[core.nll_key(arm, r, c, u, core.READ_DISABLED)] = b + (1e-3 if (arm, k, c) in spec.bad_disabled else 0.0)
                if k >= 0:
                    drun = (aspec.drun or {}).get(k, 0.0)
                    reg[core.nll_key(arm, r, c, core.rung_updates(cfg, k - 1), core.READ_ENABLED)] = v + drun
                    if arm == FLAT:
                        for j in range(4):
                            reg[core.nll_key(arm, r, c, u, core.READ_P_USED, j)] = None if (k, c) in spec.nonfinite_draw and j == 2 else v + spec.p_used(k, c)
                        reg[core.nll_key(arm, r, c, u, core.READ_X_MEAN)] = v + spec.x_mean(k, c)
                        reg[core.nll_key(arm, r, c, u, core.READ_V_MEAN)] = v + spec.v_mean(k, c)
                        reg[core.stat_key(arm, r, c, u, "used_slots")] = spec.used_slots(k, c)
                    else:
                        reg[core.nll_key(arm, r, c, u, core.READ_X_MEAN_DENSE)] = v + 0.001
    return reg


def converging_gains(k_max: int, start: float, first_delta: float, ratio: float) -> dict[int, float]:
    """gain(-1) = start, each later rung adds a delta that shrinks by ``ratio`` (delta_0 = first_delta)."""
    g = {-1: start}
    d = first_delta
    for k in range(0, k_max + 1):
        g[k] = g[k - 1] + d
        d *= ratio
    return g
