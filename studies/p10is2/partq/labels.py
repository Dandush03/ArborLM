# ruff: noqa: E501
"""Part Q outcome labels (ADR-0025 section 4.4; rulings G15, L3) as a pure function of recorded facts. First match wins; a per-teacher status table is printed under the label.

Order: 1 QUALIFICATION-ENGINEERING-FAILURE; 2 QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT; 3 QUALIFICATION-NEGATIVE: QUALITY (teacher and criterion named); 4 QUALIFICATION-INCONCLUSIVE:
DATA-EXHAUSTED; 5 TEACHERS-QUALIFIED (DISJOINT DRAWS / OVERLAPPING DRAWS). Any ending other than TEACHERS-QUALIFIED leaves Part T NOT STARTED. PAUSED and an engineering stop with item errors are
states, not outcomes: no label is derived under them. A resource-cap stop that the human lead records as final has the terminal label STOPPED AT A RESOURCE CAP BY DECISION.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from ..common import core

ENGINEERING_FAILURE = "QUALIFICATION-ENGINEERING-FAILURE"
DATA_INSUFFICIENT = "QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT"
NEGATIVE_QUALITY = "QUALIFICATION-NEGATIVE: QUALITY"
DATA_EXHAUSTED = "QUALIFICATION-INCONCLUSIVE: DATA-EXHAUSTED"
QUALIFIED = "TEACHERS-QUALIFIED"
STOPPED_BY_DECISION = "STOPPED AT A RESOURCE CAP BY DECISION"
ENGINEERING_STOP_ITEMS = "ENGINEERING STOP — ITEM ERRORS"
ENGINEERING_STOP_NONFINITE = "ENGINEERING STOP — NON-FINITE VALUE"
ENGINEERING_STOP_RECOMPUTATION = "ENGINEERING STOP — RECOMPUTATION"
PAUSED = "PAUSED"
PART_T_NOT_STARTED = "Part T: NOT STARTED"
CRITERIA = ("Q1", "Q2", "Q3", "Q4")
TEACHER_NAME = {"A": "teacher A (English to German)", "B": "teacher B (English to French)"}


def teacher_status(t: Mapping[str, Any]) -> dict[str, Any]:
    """One teacher's row. ``t`` has ``q1``, ``q2``, ``q3`` (bool or None if not run), ``q4`` (None if not run, else a dict with ``read_ok`` and ``pass``) and ``reserve_exhausted`` (bool).

    Q1-Q3 failures are quality failures. Q4 is a quality failure only when it was READ (at least 150 accepted items) and its precision is below the bar; a reading on fewer than 150 because the reserve ended is
    an exhaustion, not a precision failure (reading chosen conservatively: nothing is called a failure on a count the rule says is too small to read)."""
    q4 = t.get("q4")
    failed: list[str] = []
    for name in ("q1", "q2", "q3"):
        if t.get(name) is False:
            failed.append(name.upper())
    if q4 is not None and q4.get("read_ok") and not q4.get("pass"):
        failed.append("Q4")
    exhausted = bool(t.get("reserve_exhausted")) or (q4 is not None and not q4.get("read_ok"))
    return {"failed": failed, "reserve_exhausted": exhausted, "q1": t.get("q1"), "q2": t.get("q2"), "q3": t.get("q3"), "q4": None if q4 is None else {"read_ok": bool(q4.get("read_ok")), "pass": bool(q4.get("pass"))}}


def part_q_label(facts: Mapping[str, Any]) -> dict[str, Any]:
    """The Part Q label from the recorded facts.

    ``facts``: ``engineering_failure`` (list of reasons: a failed gate on study-produced data, a failed G1, an applied generation configuration that differs from the pinned file, a digest mismatch at a
    resume, a regeneration difference), ``data_insufficient`` (list of reasons from step 2), ``teachers`` ({"A": ..., "B": ...} as ``teacher_status`` takes), ``pools`` ({"A": n, "B": n} accepted counts after
    generation, or None if generation did not run) and ``draws`` (the rule 6 label from the counts, or None), ``item_errors`` (list), ``paused`` (list of paused stages).
    """
    if facts.get("item_errors"):
        return _out(ENGINEERING_STOP_ITEMS, "item errors are recorded; the analysis refuses and no label is derived", facts, derived=False)
    if facts.get("nonfinite"):
        return _out(ENGINEERING_STOP_NONFINITE, "a non-finite value is recorded in a registered record", facts, derived=False)
    if facts.get("engineering_failure"):
        return _out(ENGINEERING_FAILURE, "; ".join(facts["engineering_failure"]), facts)
    if facts.get("paused"):
        return _out(PAUSED, "stage(s) paused: " + ", ".join(facts["paused"]) + " (a state, not an outcome)", facts, derived=False)
    if facts.get("data_insufficient"):
        return _out(DATA_INSUFFICIENT, "; ".join(facts["data_insufficient"]), facts)
    status = {c: teacher_status(facts["teachers"][c]) for c in core.TASKS}
    named = [f"{TEACHER_NAME[c]} fails {crit}" for c in core.TASKS for crit in CRITERIA if crit in status[c]["failed"]]
    if named:
        first = next((c, crit) for c in core.TASKS for crit in CRITERIA if crit in status[c]["failed"])
        return _out(f"{NEGATIVE_QUALITY} ({TEACHER_NAME[first[0]]}, {first[1]})", "failed criteria, in order (teacher A then B; Q1 to Q4): " + "; ".join(named), facts, status=status)
    exhausted = [c for c in core.TASKS if status[c]["reserve_exhausted"]]
    if exhausted:
        return _out(DATA_EXHAUSTED, "the Q_check reserve ended before 150 accepted items: " + ", ".join(TEACHER_NAME[c] for c in exhausted), facts, status=status)
    draws = facts.get("draws")
    if facts.get("pools") is None or draws is None:
        return _out(PAUSED, "both teachers pass Q1-Q4 and generation has not ended", facts, derived=False, status=status)
    if draws == "DATA-EXHAUSTED":
        return _out(DATA_EXHAUSTED, "a pool ended below 10,000 accepted sources: " + ", ".join(f"{c} {facts['pools'][c]}" for c in core.TASKS), facts, status=status)
    return _out(f"{QUALIFIED} ({draws})", f"both teachers pass Q1-Q4; accepted sources A {facts['pools']['A']}, B {facts['pools']['B']}", facts, status=status)


def _out(label: str, why: str, facts: Mapping[str, Any], *, derived: bool = True, status: Mapping[str, Any] | None = None) -> dict[str, Any]:
    qualified = label.startswith(QUALIFIED)
    return {
        "label": label, "why": why, "derived": derived, "per_teacher": dict(status) if status is not None else None, "part_t": "may be frozen after acceptance as registered and Decision 2" if qualified else PART_T_NOT_STARTED,
        "part_t_started": False, "pools": facts.get("pools"), "oracle_line": core.ORACLE_LINE,
    }  # fmt: skip


def resource_cap_decision_label(stage: str, reached: Mapping[str, Any]) -> str:
    """The terminal label when the human lead records that a paused stage will not resume. Not negative; the per-teacher table is printed."""
    return f"{STOPPED_BY_DECISION} ({stage}; {', '.join(f'{k} {v}' for k, v in sorted(reached.items()))})"


def render(result: Mapping[str, Any], gates: Sequence[str] = ()) -> str:
    """Text with the fixed line directly above, the label, the reason and the per-teacher table; Part T NOT STARTED is printed under every ending but TEACHERS-QUALIFIED."""
    lines = [result["label"], f"why: {result['why']}"]
    if result.get("per_teacher"):
        for c in core.TASKS:
            s = result["per_teacher"][c]
            lines.append(f"  {TEACHER_NAME[c]}: Q1 {_f(s['q1'])}, Q2 {_f(s['q2'])}, Q3 {_f(s['q3'])}, Q4 {_f(None if s['q4'] is None else (s['q4']['pass'] if s['q4']['read_ok'] else None))}; failed: {', '.join(s['failed']) or 'none'}; reserve exhausted: {s['reserve_exhausted']}")
    lines.append(result["part_t"])
    lines += list(gates)
    return core.under_line(*lines)


def _f(v: bool | None) -> str:
    return "not run / not read" if v is None else ("pass" if v else "FAIL")
