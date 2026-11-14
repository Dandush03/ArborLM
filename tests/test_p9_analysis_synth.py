# ruff: noqa: E501
"""Synthetic evaluation and simulation records for the P9 analysis tests (package I6).

No model, data or simulator is involved: records are built by the schemas of ``studies.p9.core`` so that
every class and annotation of every lane can be triggered. Shared by ``tests/test_p9_analysis_*.py`` and
``tests/test_p9_report*.py``.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p9 import analysis_a as A  # noqa: E402
from studies.p9 import core  # noqa: E402

E = 32
IDENTITY = {
    "source_sha256": "a" * 64,
    "spec_sha256": "b" * 64,
    "config_sha256": "c" * 64,
    "frozen_source_sha256": "d" * 64,
}
CHANCE = 1.0 / 32.0


def test_synth_module_is_importable() -> None:
    assert Synth().index == {}


def record(
    label: str, update: int, stream: str, facts: int, correct: int, **kw: Any
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "kind": "eval",
        "schema": 1,
        "study": "P9",
        "label": label,
        "update": update,
        "stream": stream,
        "facts": facts,
        "correct": correct,
        "accuracy": correct / facts,
        "information_bits": A._information(correct, facts, 8),
        "logloss_gain_bits": 0.0,
        "mass_outside_alphabet_mean": 0.0,
        "accuracy_with_neighbour": None,
        "accuracy_without_neighbour": None,
        "unseen_correct": 64,
        "unseen_facts": 2048,
        "leakage": False,
        "value_permuted_accuracy": CHANCE,
        "disabled_accuracy": CHANCE,
        "useful_slots": 1000,
        "ustar_interpretable": True,
        "specificity": {},
        "mean_support_length": 2.0,
        "share_correct_with_support": 0.95,
        "share_stay_correct_without_site_read": 0.1,
        "usage": {
            "entropy_effective_hard": 1000.0,
            "entropy_soft": 6.0,
            "key_movement_without_task_grad": 10.0,
            "key_movement_share_without": 0.9,
        },
        "per_fact_file": None,
        "identity": IDENTITY,
    }
    rec.update(kw)
    return rec


class Synth:
    """An evaluation index being built."""

    def __init__(self, exposure: int = E) -> None:
        self.exposure = exposure
        self.index: dict[tuple[str, int, str], dict[str, Any]] = {}

    def put(
        self,
        cell: core.Cell,
        update: int,
        stream: str,
        acc: float,
        facts: int | None = None,
        **kw: Any,
    ) -> None:
        n = facts if facts is not None else cell.facts
        self.index[(cell.label, update, stream)] = record(
            cell.label, update, stream, n, round(acc * n), **kw
        )

    def cell(
        self,
        cell: core.Cell,
        acc: float | dict[str, float],
        half_acc: float | dict[str, float] | None = None,
        *,
        estimand: str = "matched",
        panels: tuple[str, ...] = core.PANELS,
        **kw: Any,
    ) -> None:
        """Records of ``cell`` at U/2 and U of the estimand on each panel; ``acc`` may be a panel dict."""
        half_u, full_u = A.snapshot_pair(cell, self.exposure, estimand)
        for p in panels:
            a = acc[p] if isinstance(acc, dict) else acc
            h = half_acc if half_acc is not None else a
            h = h[p] if isinstance(h, dict) else h
            self.put(cell, full_u, core.PANEL_STREAM[p], a, **kw)
            self.put(cell, half_u, core.PANEL_STREAM[p], h, **kw)

    def drop(self, cell: core.Cell, panels: tuple[str, ...] = core.PANELS) -> None:
        for key in [
            k
            for k in self.index
            if k[0] == cell.label and any(k[2] == core.PANEL_STREAM[p] for p in panels)
        ]:
            del self.index[key]


Profile = Callable[[core.Cell], tuple[float, float | None] | None]


def fill(
    world: Synth, blocks: tuple[str, ...], profile: Profile, estimand: str = "matched"
) -> None:
    """Add every registered cell of ``blocks`` for which ``profile`` returns ``(acc, half_acc)``."""
    for c in core.cells():
        if c.block in blocks:
            got = profile(c)
            if got is not None:
                world.cell(c, got[0], got[1], estimand=estimand)


SIZE_ACC = {4096: 0.90, 16384: 0.90, 65536: 0.85}


def strong_memory(c: core.Cell) -> tuple[float, float | None] | None:
    """Memory cells that learn the facts (steps supported, plateaued); dense adapters that do not."""
    if c.arch == "dense":
        return 0.5, 0.5
    return SIZE_ACC[c.slots], SIZE_ACC[c.slots]


def lane_a_world(
    profile: Profile = strong_memory, blocks: tuple[str, ...] = ("A1", "A2", "A8")
) -> Synth:
    w = Synth()
    fill(w, blocks, profile)
    return w


def patch(world: Synth, cell: core.Cell, panel: str | None = None, **fields: Any) -> None:
    """Overwrite fields of every record of ``cell`` (on one panel, or both)."""
    for (label, _update, stream), rec in world.index.items():
        if label == cell.label and (panel is None or stream == core.PANEL_STREAM[panel]):
            rec.update(fields)


def patch_usage(world: Synth, cell: core.Cell, panel: str | None = None, **usage: Any) -> None:
    for (label, _update, stream), rec in world.index.items():
        if label == cell.label and (panel is None or stream == core.PANEL_STREAM[panel]):
            rec["usage"] = {**rec["usage"], **usage}


REF_ACC = 0.8


def util_world(
    acc_fn: Callable[[core.Cell], float | dict[str, float]] | None = None,
    kw_fn: Callable[[core.Cell], dict[str, Any]] | None = None,
    blocks: tuple[str, ...] = ("A1", "A2", "B1"),
) -> Synth:
    """16,384-slot B101 cells of ``blocks`` (dose-zero references, B1, C1); every cell at ``REF_ACC`` and the
    default usage numbers unless the functions say otherwise."""
    w = Synth()
    for c in core.cells():
        if c.block in blocks and c.slots == 16384 and c.parent == core.PRIMARY_PARENT:
            acc = acc_fn(c) if acc_fn else REF_ACC
            w.cell(c, acc, **(kw_fn(c) if kw_fn else {}))
    return w


def case_cells(block: str, arch: str, alpha_u: float, alpha_c: float = 0.0) -> list[core.Cell]:
    return [
        c
        for c in core.cells()
        if c.block == block
        and c.arch == arch
        and c.alpha_u == alpha_u
        and c.alpha_c == alpha_c
        and c.parent == core.PRIMARY_PARENT
    ]
