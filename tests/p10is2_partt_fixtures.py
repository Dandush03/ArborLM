# ruff: noqa: E501
"""A synthetic Part T registry with known answers (ADR-0025 section 11 item 8). The defaults make every registered line positive; a test then changes the few numbers a row needs. Gap closed is written as
G here and turned into a score by s = S0 + (teacher - S0) x G, so a test states its expectation in gaps. No training, no model, no file. Seeds of the unit tests: 934001-934999."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.quantities import (  # noqa: E402
    CELLS,
    GEN_POSITIONS,
    NONE,
    ORDERS,
    PANEL,
    REPLICATES,
    Quantities,
    Registry,
    Thresholds,
    first,
    second,
)

CFG_T = core.load_config("T")
TH = Thresholds.from_config(CFG_T)
S0, TEACHER = 0.0, 1.0  # denominator 1.0 on every panel and subsample unless a test changes it: a gap equals its score, so a threshold test is exact in binary arithmetic


def score_of(g: float, s0: float = S0, teacher: float = TEACHER) -> float:
    return s0 + (teacher - s0) * g


class Spec:
    """The numbers of one synthetic registry, as gaps. ``set`` overrides one (arm, order, rep, cap, kind) entry; kinds: 'full', 'value', 'code', 'marker', 'own', 'words'."""

    def __init__(self) -> None:
        self.g: dict[tuple, float] = {}
        self.raw: dict[str, float] = {}
        self.dropped: set[str] = set()

    def set(self, arm: str, order: str, rep: int | str, cap: str, kind: str, value: float) -> "Spec":
        self.g[(arm, order, rep, cap, kind)] = value
        return self

    def all_cells(self, arm: str, cap_of: str, kind: str, value: float, reps=REPLICATES, orders=ORDERS) -> "Spec":  # type: ignore[no-untyped-def]
        for r in reps:
            for o in orders:
                self.set(arm, o, r, first(o) if cap_of == "first" else second(o), kind, value)
        return self


def default_gaps() -> dict[tuple, float]:
    d: dict[tuple, float] = {}
    for r in REPLICATES:
        for o in ORDERS:
            f, s = first(o), second(o)
            # single-teacher modules: trained on the first capability of their order
            for arm in ("M1", "D1"):
                d[(arm, o, r, f, "full")] = 0.90
                d[(arm, o, r, s, "full")] = 0.0
            for arm in ("M1",):
                for kind, v in (("own", 0.90), ("value", 0.05), ("code", 0.05), ("marker", 0.10), ("words", 0.20)):
                    d[(arm, o, r, f, kind)] = v
            # two-stage arms after stage 2
            for arm, g1, g2 in (("M-append", 0.90, 0.90), ("M-ii", 0.90, 0.90), ("M-seq", 0.30, 0.90), ("D-append", 0.90, 0.80), ("D-seq", 0.30, 0.90)):
                d[(arm, o, r, f, "full")] = g1
                d[(arm, o, r, s, "full")] = g2
            for arm in ("M-append", "M-ii", "M-seq"):
                for kind, v in (("own", 0.90), ("value", 0.05), ("code", 0.05), ("marker", 0.10), ("words", 0.20)):
                    d[(arm, o, r, s, kind)] = v
    for r in REPLICATES:
        for arm in ("M-joint", "D-joint", "M-sep", "D-sep"):
            for c in core.TASKS:
                d[(arm, NONE, r, c, "full")] = 0.85
        for c in core.TASKS:
            for kind, v in (("own", 0.85), ("value", 0.05), ("code", 0.05), ("marker", 0.10), ("words", 0.20)):
                d[("M-joint", NONE, r, c, kind)] = v
            d[("E-table", NONE, r, c, "full")] = 0.40
            for b in ("R-gloss", "R-gloss-icl", "R-nn", "R-icl"):
                d[(b, NONE, r, c, "full")] = 0.30
    return d


def build(spec: Spec | None = None, *, teacher_sub: dict[str, float] | None = None, teacher_full: dict[str, float] | None = None) -> Registry:
    """The registry. ``teacher_full`` and ``teacher_sub`` override the teacher's score per capability ('A', 'B') on the full panel and the subsample (to make a denominator small)."""
    spec = spec or Spec()
    gaps = {**default_gaps(), **spec.g}
    reg = Registry()
    tf = {"A": TEACHER, "B": TEACHER, **(teacher_full or {})}
    ts = {"A": TEACHER, "B": TEACHER, **(teacher_sub or {})}
    for c in core.TASKS:
        p = PANEL[c]
        reg.put("S0", NONE, NONE, f"s:{p}", S0)
        reg.put("S0", NONE, NONE, f"sub:own:{p}", S0)
        reg.put("TEACHER", NONE, NONE, f"s:{p}", tf[c])
        reg.put("TEACHER", NONE, NONE, f"sub:own:{p}", ts[c])
    for (arm, order, rep, cap, kind), g in gaps.items():
        p = PANEL[cap]
        if kind == "full":
            reg.put(arm, order, rep, f"s:{p}", score_of(g, S0, tf[cap]))
        else:
            reg.put(arm, order, rep, f"sub:{kind}:{p}", score_of(g, S0, ts[cap]))
    for arm in ("M1", "M-append", "M-seq", "M-ii", "D-seq"):
        for r, o in CELLS:
            for pos in GEN_POSITIONS:
                reg.put(arm, o, r, f"gen:{pos}", 0.001)
    for r, o in CELLS:
        for c in core.TASKS:
            reg.put("M-ii", o, r, f"dcon:{c}", 0.60)
            reg.put("M-append", o, r, f"dcon:{c}", 0.60)
        reg.put("M-ii", o, r, "modification", 0.20)
    for k, v in spec.raw.items():
        reg.values[k] = v
    for k in spec.dropped:
        reg.values.pop(k)
    return reg


def quantities(spec: Spec | None = None, **kw) -> Quantities:  # type: ignore[no-untyped-def]
    return Quantities(build(spec, **kw), TH)
