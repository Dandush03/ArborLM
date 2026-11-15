# ruff: noqa: E501
"""Gates, mechanism classes, study labels, annotations and cost lines (ADR-0022 section 11). Pure functions over plain numbers; thresholds come from the config.

Every gate returns a ``Verdict``: ``ok`` True, False, or None (NOT_EVALUATED: a gap is undefined or a value is not finite), with the reasons. Nothing here prints; the oracle-assisted line is attached by
``output`` and ``report``. Where the ADR is silent on a reading (aggregation of an annotation over replicates and orders, the panel a permutation control is read on, the LoRA form of ACQ), the choice made
is marked "reading" and listed in the implementer's report.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import core
from .text import gap_closed

G = core.CFG["gates"]


@dataclass(frozen=True)
class Verdict:
    ok: bool | None  # None: NOT_EVALUATED
    reasons: tuple[str, ...] = ()

    @property
    def not_evaluated(self) -> bool:
        return self.ok is None


def finite_all(*xs: float | None) -> bool:
    return all(x is not None and math.isfinite(x) for x in xs)


# --- cell-level gates (section 11.1) -----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Lexical:
    """Gap closed on the 300-item subsample: the arm unablated, with values permuted, with word codes permuted, marker-only (the denominators are the teacher's and Stage 0's on the same subsample)."""

    g_sub: float | None
    g_value_perm: float | None
    g_code_perm: float | None
    g_marker_only: float | None


def acq1(g: float | None, lex: Lexical | None) -> Verdict:
    """ACQ1 (ST1): G_first >= 0.50; G - max(G_value-perm, G_code-perm) >= 0.30; G_marker-only <= 0.25. A LoRA first stage has no keys or codes to permute, so only the first clause applies (reading)."""
    return _acq(g, lex, None, ratio=False)


def acq2(g: float | None, g_single: float | None, lex: Lexical | None) -> Verdict:
    """ACQ2 (stage-2 arm): G_second >= 0.50 and >= 0.80 x the single-teacher student's G on that capability in the same replicate; the same lexical margin and marker-only limit."""
    return _acq(g, lex, g_single, ratio=True)


def _acq(g: float | None, lex: Lexical | None, g_single: float | None, *, ratio: bool) -> Verdict:
    if not finite_all(g):
        return Verdict(None, ("undefined gap",))
    assert g is not None
    reasons: list[str] = []
    undefined = False
    if g < G["acq_gap_min"]:
        reasons.append("acquisition below 0.50")
    if ratio:
        if not finite_all(g_single):
            undefined = True
        else:
            assert g_single is not None
            if g < G["acq2_ratio_min"] * g_single:
                reasons.append("below 0.80 of the single-teacher student")
    if lex is not None:
        vals = (lex.g_sub, lex.g_value_perm, lex.g_code_perm, lex.g_marker_only)
        if not finite_all(*vals):
            undefined = True
        else:
            assert lex.g_sub is not None and lex.g_value_perm is not None and lex.g_code_perm is not None and lex.g_marker_only is not None
            if lex.g_sub - max(lex.g_value_perm, lex.g_code_perm) < G["acq_margin_min"]:
                reasons.append("lexical margin below 0.30")
            if lex.g_marker_only > G["acq_marker_only_max"]:
                reasons.append("marker-only above 0.25")
    if reasons:
        return Verdict(False, tuple(reasons))
    if undefined:
        return Verdict(None, ("undefined gap",))
    return Verdict(True)


def ret(s_first_after: float, s_first_v1: float, g_first_after: float | None, g_first_v1: float | None) -> Verdict:
    """RET: s_first after Stage 2 >= s_first after Stage 1 - 0.03, and G_first after >= 0.90 x G_first before; 'after Stage 1' and 'before' are V1 for every stage-2 arm, M-ii included."""
    if not finite_all(s_first_after, s_first_v1, g_first_after, g_first_v1):
        return Verdict(None, ("undefined gap",))
    assert g_first_after is not None and g_first_v1 is not None
    reasons: list[str] = []
    if s_first_after < s_first_v1 - G["ret_drop_max"]:
        reasons.append("chrF drop beyond 0.03")
    if g_first_after < G["ret_gap_ratio_min"] * g_first_v1:
        reasons.append("below 0.90 of the earlier gap closure")
    return Verdict(not reasons, tuple(reasons))


def negative_acquisition(g_second: float | None) -> bool | None:
    return None if not finite_all(g_second) else bool(g_second < G["negative_acquisition"])


def negative_retention(g_first_after: float | None, g_first_v1: float | None) -> bool | None:
    return None if not finite_all(g_first_after, g_first_v1) else bool(g_first_after < G["negative_retention_ratio"] * g_first_v1)


def gen_gate(loss_increase: float | None) -> bool | None:
    """GEN (keyword router): loss <= the unmodified student's + 0.02 nats per token on the 200-window panel."""
    return None if not finite_all(loss_increase) else bool(loss_increase <= G["gen_loss_margin"])


# --- mechanism class (section 11.2) ------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CellEval:
    """One replicate's gates for one mechanism and order."""

    acq1: Verdict
    acq2: Verdict
    ret: Verdict
    neg_acq: bool | None
    neg_ret: bool | None
    rejected: bool = False  # M-ii: CONSOLIDATION-REJECTED
    below_floor: bool = False  # M-ii: below the modification floor
    recompute_ne: bool = False  # the recomputation disagreed beyond tolerance (section 13.3)


@dataclass(frozen=True)
class ClassResult:
    name: str
    reasons: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {"class": self.name, "reasons": list(self.reasons)}


CLASS_ORDER = ("NOT_EVALUATED", "NO-NEW-CAPABILITY", "FORGETS", "RETENTION BY INERTIA", "ACQUIRES-AND-RETAINS", "NOT REPLICATED", "INTERMEDIATE")


def mechanism_class(mech: str, cells: Sequence[CellEval]) -> ClassResult:
    """First match wins, rule over all replicates. ``mech`` is "M-ii" for the rows that name it."""
    reasons: list[str] = []
    for i, c in enumerate(cells):
        if c.acq1.ok is not True:
            reasons += [f"replicate {i}: ACQ1 {r}" for r in (c.acq1.reasons or ("not met",))]
        if c.acq2.not_evaluated:
            reasons += [f"replicate {i}: ACQ2 {r}" for r in c.acq2.reasons]
        if c.ret.not_evaluated:
            reasons += [f"replicate {i}: RET {r}" for r in c.ret.reasons]
        if c.recompute_ne:
            reasons.append(f"replicate {i}: recomputation difference beyond tolerance")
    if reasons or not cells:
        return ClassResult("NOT_EVALUATED", tuple(reasons) or ("no cells",))
    if all(c.neg_acq for c in cells):
        return ClassResult("NO-NEW-CAPABILITY")
    if all(c.neg_ret for c in cells):
        return ClassResult("FORGETS")
    both = all(c.acq2.ok is True and c.ret.ok is True for c in cells)
    if mech == "M-ii" and both and any(c.below_floor for c in cells):
        return ClassResult("RETENTION BY INERTIA")
    if both and not (mech == "M-ii" and any(c.rejected for c in cells)):
        return ClassResult("ACQUIRES-AND-RETAINS")
    passes = [c.acq2.ok is True and c.ret.ok is True for c in cells]
    zone = [bool(c.neg_acq or c.neg_ret) for c in cells]
    if any(passes) and any(z for p, z in zip(passes, zone, strict=True) if not p):
        return ClassResult("NOT REPLICATED")
    return ClassResult("INTERMEDIATE")


# --- study label (section 11.3) ------------------------------------------------------------------------------------------------------------------------
@dataclass
class LabelInputs:
    engineering: list[str] = field(default_factory=list)  # defects found by G1, G4-G9; hash mismatch; frozen/running difference; ensemble difference; recomputation difference
    incomplete: list[str] = field(default_factory=list)  # a registered cell has no record; a cap stopped a stage; the recomputation cannot be completed
    prefreeze_stop: str | None = None  # TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED / DATA-INSUFFICIENT
    st1_negative_everywhere: bool = False  # ST1's G in the negative zone in every replicate, both capabilities
    control_failed: bool = False
    classes: dict[str, dict[str, ClassResult]] = field(default_factory=dict)  # mechanism -> order -> class
    gen_maf_fails: bool = False  # M-append-frozen's GEN fails in any replicate of either order
    gen_mii_holds: bool = False  # M-ii's GEN holds in every replicate of both orders
    gen_maf_holds: bool = False
    teacher_only: bool = True
    not_evaluated_reasons: list[str] = field(default_factory=list)


def study_label(i: LabelInputs) -> tuple[int, str]:
    """(row, label). First match wins."""
    if i.engineering:
        return 1, "ENGINEERING-FAILURE"
    if i.incomplete:
        return 2, "INCOMPLETE"
    if i.prefreeze_stop:
        return 3, i.prefreeze_stop
    if i.st1_negative_everywhere:
        return 4, "TRANSFER-NEGATIVE: NO-ACQUISITION"
    if i.control_failed:
        return 5, "TRANSFER-INCONCLUSIVE: CONTROL-FAILED"
    maf = i.classes.get("M-append-frozen", {})
    mii = i.classes.get("M-ii", {})

    def both(d: Mapping[str, ClassResult], name: str) -> bool:
        return len(d) == 2 and all(c.name == name for c in d.values())

    ar = "ACQUIRES-AND-RETAINS"
    if both(maf, ar) and i.teacher_only and i.gen_maf_fails:
        return 6, "TRANSFER-POSITIVE WITHHELD — GENERAL QUALITY NOT PRESERVED UNDER A LEARNED ROUTE"
    if both(maf, ar) and both(mii, ar) and i.teacher_only and i.gen_maf_holds and i.gen_mii_holds:
        return 7, "TRANSFER-POSITIVE (append-frozen + consolidation)"
    if both(maf, ar) and i.teacher_only and i.gen_maf_holds:
        return 8, "TRANSFER-POSITIVE (append-frozen)"
    if both(maf, "FORGETS"):
        return 9, "TRANSFER-NEGATIVE: FORGETTING"
    if both(maf, "NO-NEW-CAPABILITY"):
        return 10, "TRANSFER-NEGATIVE: NO-ADDITIONAL-ACQUISITION"
    if len(maf) == 2 and sum(c.name == ar for c in maf.values()) == 1:
        return 11, "TRANSFER-INCONCLUSIVE: ORDER-DEPENDENT"
    return 12, "TRANSFER-INCONCLUSIVE"


def label_with_n(label: str, n: int, u: int) -> str:
    """Every label is printed with '(n replicates, U = ...)'."""
    return f"{label} ({n} replicates, U = {u})"


# --- annotations (section 11.4) ------------------------------------------------------------------------------------------------------------------------
def within(value: float | None, reference: float | None, margin: float | None = None) -> bool | None:
    """value >= reference - margin ('within 0.03 of, or above')."""
    m = G["annotation_margin"] if margin is None else margin
    if value is None or reference is None or not finite_all(value, reference):
        return None
    return bool(value >= reference - m)


def all_or_none(xs: Sequence[bool | None]) -> bool | None:
    if any(x is None for x in xs):
        return None
    return all(bool(x) for x in xs)


def annotation_lines(a: Mapping[str, bool | None]) -> list[str]:
    """Mandatory annotation names for those that are true; an undefined one prints NOT_EVALUATED."""
    out = []
    for name, v in a.items():
        out.append(f"{name}: NOT_EVALUATED" if v is None else (name if v else f"not {name}"))
    return out


def composes(combined_mean: float | None, single_a: float | None, single_b: float | None) -> bool | None:
    """COMPOSES: mean over replicates of the combined score >= 0.80 x the mean of the arm's two single-task scores."""
    if not finite_all(combined_mean, single_a, single_b):
        return None
    assert combined_mean is not None and single_a is not None and single_b is not None
    return bool(combined_mean >= G["composes_ratio_min"] * (single_a + single_b) / 2)


def training_cost(maf_seconds: Sequence[float], lora_seconds: Sequence[float]) -> dict[str, Any]:
    """TRAINING COST COMPARABLE if training wall seconds per stage <= 1.5 x LoRA-1's on the same device and U (medians over replicates); otherwise TRAINING COST HIGHER, with the ratio."""
    if not maf_seconds or not lora_seconds:
        return {"line": "TRAINING COST: NOT_EVALUATED", "ratio": None}
    ratio = _median(maf_seconds) / _median(lora_seconds)
    word = "TRAINING COST COMPARABLE" if ratio <= G["training_cost_ratio_max"] else "TRAINING COST HIGHER"
    return {"line": f"{word} (ratio {ratio:.2f} of M-append-frozen to LoRA-1, measured wall seconds per stage, medians over replicates)", "ratio": ratio, "word": word}


def value_rows(store_value_params_per_token: float | None, adapter_params_per_token: float | None, key_products_per_read: int) -> dict[str, Any]:
    """FEWER VALUE ROWS ACTIVE if the store's value parameters read per generated token <= 0.10 x the adapter parameters applied per generated token; always printed with the key products per read,
    which a flat scan does not reduce. Both are analytical counts, never measured efficiency."""
    if not finite_all(store_value_params_per_token, adapter_params_per_token):
        return {"line": f"VALUE ROWS ACTIVE: NOT_EVALUATED (key products per read {key_products_per_read}, a flat scan)", "ratio": None}
    assert store_value_params_per_token is not None and adapter_params_per_token is not None
    ratio = store_value_params_per_token / adapter_params_per_token
    head = "FEWER VALUE ROWS ACTIVE" if ratio <= G["value_rows_ratio_max"] else "value rows active not fewer"
    return {"line": f"{head} (analytical count: ratio {ratio:.4f}; key products per read {key_products_per_read}, a flat scan, not reduced)", "ratio": ratio, "word": head}


def stored_size_line(student: int, rows: int, teachers: Sequence[int], g_first: float | None, g_second: float | None, width: int) -> str:
    """Stored size against the ensemble is arithmetic, not a comparison: student plus a 2N-row store against the two teachers, with M-append-frozen's G on each capability."""
    store = rows * (core.KEY_WIDTH + width) + 2
    total = student + store
    t = sum(teachers)
    gs = ", ".join("G not evaluated" if g is None else f"G {g:.3f}" for g in (g_first, g_second))
    return f"stored parameters (arithmetic, not a comparison): student plus a {rows}-row store {total:,} against the two teachers {t:,}, ratio {total / t:.3f}; M-append-frozen {gs}"


def _median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def gap(arm: float, s0: float, teacher: float) -> float | None:
    return gap_closed(arm, s0, teacher)
