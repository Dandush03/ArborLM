# ruff: noqa: E501
"""P10IS1 synthetic registries (ADR-0024 section 18): a registry of counts built from designed trajectories of i (bits per fact), with known answers, for the analysis, the report and the synthetic rehearsal. No model, no
training, no registered seed: the cells are the plan's (``core.planned_cells`` in test mode), the counts are derived from the designed i by P10-S1's own inverse of the Fano function. A module of the package, not a test
helper; the tests plant distinct values and derive their expected labels BY HAND from the design, never with the analysis' own helpers."""

import functools
from collections.abc import Callable, Mapping
from typing import Any

from . import core
from .analysis import Registry

Level = tuple[float, float]  # (final i in bits, update at which the linear rise reaches it)
CPU_MEASURED = {
    "F-OQ|256": 0.0035, "F-OQ|1024": 0.0060, "F-OQ|4096": 0.0085, "F-OQ|16384": 0.0130, "T-OQ|1024": 0.0116, "T-OQ|4096": 0.0129, "T-OQ|16384": 0.0147, "H8|1024": 0.0045, "H8|4096": 0.0050, "H8|16384": 0.0055,
    "D-OQ|1024": 0.0051, "D-OQ|4096": 0.0088, "D-OQ|16384": 0.0190, "R2|4096": 0.0040, "R2|16384": 0.0045, "R2|32768": 0.0050,
}  # fmt: skip
ROW_U_P = {2048: 8192, 8192: 8192, 32768: 16384}
U0 = {"2K/256": 98304, "8K/1K": 131072, "32K/4K": 131072}
GRANTED = {"2K/256": 196608, "8K/1K": 262144, "32K/4K": 262144}


def positive_levels() -> dict[tuple[str, int, int], Level]:
    """The 'positive' design (answers derived by hand in the tests): F-OQ gains capacity at both loaded steps, D-OQ is behind it at the larger cells, T-OQ and H8 do not gain."""
    foq = {(2048, 256): (1.0, 4096), (2048, 1024): (3.9, 8192), (2048, 4096): (4.0, 2048), (8192, 1024): (1.5, 8192), (8192, 4096): (3.5, 8192), (8192, 16384): (3.5, 2048), (32768, 4096): (1.5, 8192), (32768, 16384): (3.5, 16384)}
    flat = {(2048, 1024): (3.9, 8192), (2048, 4096): (4.0, 8192), (8192, 1024): (1.5, 8192), (8192, 4096): (1.6, 8192), (8192, 16384): (1.6, 8192), (32768, 4096): (1.5, 8192), (32768, 16384): (1.6, 16384)}
    dense = {(2048, 4096): (3.2, 8192), (8192, 4096): (3.2, 8192), (8192, 16384): (3.2, 8192), (32768, 16384): (3.2, 16384), (8192, 1024): (1.2, 8192), (32768, 4096): (1.2, 8192)}
    r2 = {(2048, 4096): (4.6, 2048), (8192, 16384): (4.6, 2048), (32768, 32768): (4.6, 4096)}
    out: dict[tuple[str, int, int], Level] = {}
    for arm, table in (("F-OQ", foq), ("T-OQ", flat), ("H8", flat), ("D-OQ", dense), ("R2", r2)):
        for (f, n), lv in table.items():
            out[(arm, f, n)] = lv
    return out


def curve(level: Level, update: int) -> float:
    final, hit = level
    return final if update >= hit else final * update / hit


@functools.cache
def _a_use_of_i(i: float) -> float:
    from studies.p10s1 import core as s1

    return float(s1.i_to_a_use(i)) if i > 0 else 0.0


def counts(n: int, i: float, *, memory: bool = True, excess: int = 0, unseen_correct: int = 2) -> dict[str, Any]:
    """Counts of one panel that give ``i`` bits per fact: useful = n x a_use(i), the backbone answers 1 in 32 of the rest, memory-off and value-shuffle at chance, the no-memory baseline at chance."""
    useful = min(n, round(_a_use_of_i(round(i, 6)) * n))
    correct = min(n, useful + round((n - useful) / 32) + excess)
    rec: dict[str, Any] = {"n": n, "correct": correct, "useful": useful, "disabled_correct": n // 32, "swap_correct": n // 32, "unseen_n": 64, "unseen_correct": unseen_correct}
    rec["shuffled_correct"] = n // 32 if memory else None
    return rec


def build(
    params: core.PlanParams | None = None,
    *,
    levels: Mapping[tuple[str, int, int], Level] | None = None,
    override: Callable[[str, int, int, int, int, str, str], float | None] | None = None,
    excess: Callable[[str, int, int, int, int, str, str], int] | None = None,
    unseen: Callable[[str, int, int, int, int], int] | None = None,
    cpu: Mapping[str, float] | None | str = "measured",
    u_run: Mapping[str, int] | None = None,
    qualification: Mapping[str, Mapping[str, list[str]]] | None = None,
    calibration: Mapping[str, Any] | None = None,
    status: Mapping[str, Any] | None = None,
    drop: Callable[[str], bool] | None = None,
) -> Registry:
    """A registry from designed levels. ``override(arm, facts, slots, draw, update, read, panel)`` returns i (bits) or None; ``excess(...)`` extra correct answers (a planted DEP-c failure); ``unseen(arm, facts, slots,
    draw, update)`` the unseen-control correct count (planted LEAKAGE); ``drop(key)`` leaves a read out (a missing record)."""
    c = core.load_config()
    rates = {u: 0.003 for u in core.units(c)}
    p = params or core.PlanParams(ROW_U_P, rates, U0, GRANTED)
    cells = core.planned_cells(p, core.TEST)
    lv = dict(levels or positive_levels())
    stops = {name: {"u_run": int((u_run or U0)[name])} for name in p.u0}
    reads: dict[str, dict[str, Any]] = {}
    baselines: dict[str, dict[str, int]] = {}
    for cell in cells:
        arm, f, n, d = cell["arm"], cell["facts"], cell["slots"], cell["draw"]
        run = int(stops[core.cell_name(f, n)]["u_run"]) if cell["ladder_cell"] else int(cell["run"])
        baselines[core.baseline_key(d, f)] = {"A": f // 32, "B": f // 32}
        for u in cell["snapshots"]:
            if u > run:
                continue
            for read in ("main", "ivf") if (arm == "F-OQ" and n != 256) else ("main",):
                key = core.read_key(cell["label"], u, read)
                if drop is not None and drop(key):
                    continue
                panels = {}
                for panel in core.PANELS:
                    i = override(arm, f, n, d, u, read, panel) if override is not None else None
                    if i is None:
                        i = curve(lv[(arm, f, n)], u)
                    ex = excess(arm, f, n, d, u, read, panel) if excess is not None else 0
                    uc = unseen(arm, f, n, d, u) if unseen is not None else 2
                    panels[panel] = counts(f, i, memory=arm != "D-OQ", excess=ex, unseen_correct=uc)
                reads[key] = {"panels": panels}
    cal = {"h8_undertrained": [], "h8_calibrated": ["2K/4K", "8K/4K", "8K/16K", "32K/16K"], "sat256": p.sat256, **(calibration or {})}
    return Registry(
        cells=cells, reads=reads, baselines=baselines, ladder_stops=stops, cpu=dict(CPU_MEASURED) if cpu == "measured" else (None if cpu is None else dict(cpu)),  # type: ignore[arg-type]
        qualification=dict(qualification or {}), calibration=cal, status=dict(status or {"run": "SYNTHETIC REGISTRY (known answers); not a registered run"}),
    )  # fmt: skip
