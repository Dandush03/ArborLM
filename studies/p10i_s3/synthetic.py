# ruff: noqa: E501
"""P10IS3 synthetic registry with known answers (ADR-0026 section 11, ruling 16). No torch. Each (arm, regime) has a ``Spec``: the per-cell gain at U* (B - H), the shape of its curve over the checkpoints, the effects
of each control, failed cells, collapsed cells. Everything is exactly what its numbers say, so the tests derive the expected labels by hand."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core
from .core import FLAT, TREE

B = 2.0
DEFAULT_CURVE = {512: 0.5, 2048: 0.8, 8192: 0.99, 16384: 1.0}


@dataclass
class Spec:
    gain: float | Sequence[float] = 0.02  # B - H at U*, a float or one value per cell
    curve: Mapping[int, float] = field(default_factory=lambda: dict(DEFAULT_CURVE))  # gain(k) = gain x curve[k]
    p: float | Sequence[float | None] = 0.015  # H_used - H (P_used, P_all)
    xm: float | Sequence[float | None] = 0.012  # H_mean - H
    x: float = 0.02  # X (descriptive)
    ex: float = 0.0  # H(exhaustive) = H - ex  (G_read = +ex)
    pr: float = 0.0  # H(prior off) = H + pr
    failed: Sequence[int] = ()
    used_slots: int = 300
    joint_offset: float = 0.0
    bad_disabled: Sequence[int] = ()  # cells whose disabled read != BASE
    bad_replay: Sequence[int] = ()


def _per_cell(v: Any, i: int) -> Any:
    return v[i] if isinstance(v, list | tuple) else v


def registry(cfg: Mapping[str, Any], specs: Mapping[tuple[str, str], Spec], *, rate: float = 0.003, cells: int = 27, rates: Mapping[tuple[str, str], float] | None = None, cell_parent: Mapping[int, int] | None = None) -> dict[str, Any]:
    """Every key ``analysis.analyse`` needs, for every arm-regime of ``specs`` (missing arm-regimes are filled with the default Spec)."""
    ckpts = [int(x) for x in cfg["duration"]["checkpoints"]]
    cp = dict(cell_parent or {c: core.parent_of(c) for c in range(cells)})
    reg: dict[str, Any] = {}
    for parent in sorted(set(cp.values())):
        reg[core.base_key(parent)] = B
        reg[core.base_key(parent, "replay")] = B
    for g in core.REGIMES:
        for a in core.REGIME_ARMS[g]:
            s = specs.get((a, g), Spec())
            r = (rates or {}).get((a, g), rate)
            for c in range(cells):
                if c in s.failed:
                    reg[core.run_key(a, g, r, c)] = {"status": "failed_cell", "reason": "synthetic non-finite"}
                    continue
                reg[core.run_key(a, g, r, c)] = {"status": "ok"}
                gain_end = float(_per_cell(s.gain, c))
                for k in ckpts:
                    h = B - gain_end * float(s.curve[k])
                    put = lambda read, v, d=0, k=k: reg.__setitem__(core.nll_key(a, g, r, c, k, read, d), v)  # noqa: E731
                    put(core.READ_ENABLED, h)
                    put(core.READ_REPLAY, h + (1e-3 if c in s.bad_replay else 0.0))
                    put(core.READ_DISABLED, B + (1e-3 if c in s.bad_disabled else 0.0))
                    p, xm = _per_cell(s.p, c), _per_cell(s.xm, c)
                    if a in (TREE, FLAT):
                        put(core.READ_P_ALL, None if p is None else h + p)
                        for j in range(4):
                            put(core.READ_P_USED, None if p is None else h + p, j)
                            put(core.READ_X, h + s.x, j)
                        put(core.READ_X_MEAN, None if xm is None else h + xm)
                        reg[core.stat_key(a, g, r, c, k, "used_slots")] = s.used_slots
                        reg[core.stat_key(a, g, r, c, k, "branch_entropy")] = 2.0
                        if a == TREE:
                            put(core.READ_JOINT, h + s.joint_offset)
                            put(core.READ_EXHAUSTIVE, h - s.ex)
                            put(core.READ_PRIOR_OFF, h + s.pr)
                    else:
                        for j in range(4):
                            put(core.READ_X_DENSE, h + 0.01, j)
                        put(core.READ_X_MEAN_DENSE, h + 0.02)
    return reg


def rate_table(cfg: Mapping[str, Any], *, rate: float = 0.003, edge: Sequence[tuple[str, str]] = (), rates: Mapping[tuple[str, str], float] | None = None) -> dict[str, Any]:
    ds = [str(d) for d in cfg["duration"]["checkpoints"]]
    out: dict[str, Any] = {"rates": {}, "edge": {}}
    for g in core.REGIMES:
        for a in core.REGIME_ARMS[g]:
            r = (rates or {}).get((a, g), rate)
            out["rates"][f"{a}|{g}"] = dict.fromkeys(ds, r)
            out["edge"][f"{a}|{g}"] = (a, g) in edge
    return out
