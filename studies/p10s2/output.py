# ruff: noqa: E501
"""The oracle-assisted line and everything that prints (ADR-0022 section 11.3).

The human lead's rule: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." Every class, mechanism, router, composition, GEN and cost line, every table and figure
caption, every machine-readable record and every log summary is printed only directly under the fixed oracle-assisted line. This module is the only place that writes to the terminal; it refuses any text
in which a guarded line is not in a block headed by the line, and any record in which a class, label, GEN, router or cost field lacks it. The report test on synthetic records checks every such line.

The line is attached STRUCTURALLY, not by a list of words (the audit's C-m4): ``emit`` always heads what it prints with the line; ``emit_plain`` sends anything that reads as a class, mechanism, router,
GEN, composition, label, annotation or cost line through ``emit``; ``write_record`` requires the line at the root of every record, and ``needs_line`` (one predicate, used by the stamping and by the
check) says which mappings must carry it as a field of their own. Matching is case-insensitive and broader than the listed words, because an over-match only adds the line.
"""

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import atomic_write

from . import core
from .core import COMBINED_LINE, COMPOSITION_WORDS, GUARDED_WORDS, ORACLE_LINE

KEY_STEMS = frozenset({"class", "classes", "label", "annotation", "annotations", "cost", "costs", "router", "routers", "composition", "compositions", "mechanism", "mechanisms", "outcome", "gen", "verdict", "verdicts", "control", "controls", "summary"})
GUARDED_KEYS = tuple(sorted(KEY_STEMS))  # kept for callers that listed the keys
MARKERS = re.compile(
    r"\b(class(es)?|label|mechanisms?|routers?|route accuracy|annotations?|compos\w*|costs?|gen|gate|verdicts?|loss increase|false[- ]trigger\w*|value rows|stored parameters|replicates, U|oracle-routed|study)\b",
    re.IGNORECASE,
)


class OracleLineMissing(ValueError):
    """A guarded line, table or record without the oracle-assisted line."""


COMPOSITION_RE = re.compile(r"\bcomposes\b|\bdoes not compose\b|\bcomposition (inconclusive|\(replaced\))", re.IGNORECASE)


def is_composition(line: str) -> bool:
    """A composition verdict in any case (the three words, or their negation, or the replaced composition). A line that only names the composition rule carries no composition word (section 8 of the addendum)."""
    low = line.lower()
    return any(w.lower() in low for w in COMPOSITION_WORDS) or bool(COMPOSITION_RE.search(line))


H_LINE_RE = re.compile(r"\bH_a\b|\bH_?a? per answer\b|\bH \{|\bsingle-task G\b|Table 4\. Composition", re.IGNORECASE)


def is_h_line(line: str) -> bool:
    """A per-answer composition measure (H_a, H per answer, single-task G) or the composition table caption: it needs the second fixed line even where it carries no composition word."""
    return bool(H_LINE_RE.search(line))


def is_composition_key(key: Any) -> bool:
    return "compos" in str(key).lower() or str(key).lower() in ("h_by_answer",)


def is_guarded(line: str) -> bool:
    low = line.lower()
    return any(w.lower() in low for w in GUARDED_WORDS) or bool(MARKERS.search(line)) or bool(H_LINE_RE.search(line))


def block(lines: Iterable[str], *, composition: bool = False) -> str:
    """A block of lines headed by the oracle-assisted line. A markdown table passed here keeps the line directly above its header row. A composition block (``composition=True``, or any line with a composition
    word or an H per answer) is headed by both fixed lines, whatever its verdicts say (a table whose every line is NOT_EVALUATED still carries the second line)."""
    ls = list(lines)
    head = [ORACLE_LINE, COMBINED_LINE] if composition or any(is_composition(ln) or is_h_line(ln) for ln in ls) else [ORACLE_LINE]  # a composition line carries the second fixed line as well
    return "\n".join([*head, *ls])


AUTONOMOUS_RE = re.compile(r"autonom", re.IGNORECASE)


def _autonomous_allowed(line: str) -> bool:
    """The only lines that may say "autonomous": the fixed oracle line, the human lead's sentence and the first NOT_ESTABLISHED item (each as a whole phrase inside the line)."""
    from .report import NOT_ESTABLISHED

    return any(p in line for p in (ORACLE_LINE, core.LEAD_RULE, NOT_ESTABLISHED[0]))


def check_text(text: str) -> None:
    """Every block (separated by a blank line) that contains a guarded line must begin with the oracle-assisted line. A line outside any block is a block of its own."""
    for blk in text.split("\n\n"):
        lines = [ln for ln in blk.split("\n") if ln.strip()]
        if not lines:
            continue
        for ln in lines:
            if AUTONOMOUS_RE.search(ln) and not _autonomous_allowed(ln):  # re-check C, F12: no free-text line may speak of autonomy (the lead's rule: no autonomous learned-memory success from oracle-assisted results)
                raise OracleLineMissing(f"a line speaks of autonomy outside the three fixed phrases: {ln[:120]!r}")
        if any(is_guarded(ln) for ln in lines) and lines[0] != ORACLE_LINE:
            bad = next(ln for ln in lines if is_guarded(ln))
            raise OracleLineMissing(f"guarded line without the oracle-assisted line directly above its block: {bad[:120]!r}")
        if any(is_composition(ln) or is_h_line(ln) for ln in lines) and (len(lines) < 2 or lines[1] != COMBINED_LINE):
            bad = next(ln for ln in lines if is_composition(ln) or is_h_line(ln))
            raise OracleLineMissing(f"composition line without the second fixed line (combined tasks) directly under the oracle-assisted line: {bad[:120]!r}")


def guarded(record: Mapping[str, Any]) -> dict[str, Any]:
    """A record headed by the oracle-assisted line as a field of the same record."""
    return {"oracle_line": ORACLE_LINE, **record}


def _key_guarded(key: Any) -> bool:
    return any(t in KEY_STEMS for t in re.split(r"[^a-z0-9]+", str(key).lower()))


def _text_guarded(v: Any) -> bool:
    if isinstance(v, str):
        return is_guarded(v)
    if isinstance(v, list | tuple):
        return any(isinstance(x, str) and is_guarded(x) for x in v)
    return False


def needs_line(obj: Mapping[str, Any]) -> bool:
    """A mapping must carry the oracle-assisted line as a field of its own if one of its keys names a class, label, annotation, cost, router, GEN, composition, mechanism, outcome, verdict or control (any
    case, any compound such as ``router_table``), or one of its values is a string, or a list of strings, that reads as such a line."""
    return any(_key_guarded(k) or _text_guarded(v) for k, v in obj.items() if k != "oracle_line")


def check_record(obj: Any, path: str = "$") -> None:
    """Every mapping for which ``needs_line`` holds must carry the oracle-assisted line as a field of the same mapping; a composition field also needs the second fixed line."""
    if isinstance(obj, Mapping):
        if needs_line(obj) and obj.get("oracle_line") != ORACLE_LINE:
            raise OracleLineMissing(f"record at {path} carries a guarded field without the oracle-assisted line")
        if any(is_composition_key(k) for k in obj) and obj.get("combined_line") != COMBINED_LINE:
            raise OracleLineMissing(f"record at {path} carries a composition field without the second fixed line (combined tasks)")
        for k, v in obj.items():
            check_record(v, f"{path}.{k}")
    elif isinstance(obj, list | tuple):
        for i, v in enumerate(obj):
            check_record(v, f"{path}[{i}]")


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    """Write a machine-readable record, refusing one that lacks the line at its root or wherever ``needs_line`` says."""
    if record.get("oracle_line") != ORACLE_LINE:
        raise OracleLineMissing("a machine-readable record is written only with the oracle-assisted line as a field at its root")
    check_record(record)
    atomic_write(path, (json.dumps(core.jsonable(record), sort_keys=True, indent=1) + "\n").encode())


def write_text(path: Path, text: str) -> None:
    check_text(text)
    atomic_write(path, text.encode())


def emit(lines: Sequence[str], stream: Any = None) -> None:
    """The one place that prints. Whatever is printed here is printed inside a block headed by the oracle-assisted line (and the second fixed line for a composition line): the line is always attached,
    never decided by the words of the text."""
    out = block(lines)
    check_text(out)
    print(out, file=stream if stream is not None else sys.stdout)


def emit_plain(line: str, stream: Any = None) -> None:
    """A line that carries no class, mechanism, router, GEN, composition, label, annotation or cost reading (a path, a refusal, a count). A line that reads as one is not refused (a refusal would crash the
    command that printed it) and not printed bare: it goes through ``emit`` and is printed under the line."""
    if is_guarded(line):
        emit([line], stream)
        return
    print(line, file=stream if stream is not None else sys.stdout)


def positive_wording_without_line(text: str) -> bool:
    """True if ``text`` would print a positive word outside a block headed by the line (the test of section 11.3 uses it)."""
    try:
        check_text(text)
    except OracleLineMissing:
        return True
    return False
