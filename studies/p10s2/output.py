# ruff: noqa: E501
"""The oracle-assisted line and everything that prints (ADR-0022 section 11.3).

The human lead's rule: "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results." Every class, mechanism, router, composition and cost line, every table and figure
caption, every machine-readable record and every log summary is printed only directly under the fixed oracle-assisted line. This module is the only place that writes to the terminal; it refuses any text
in which a guarded line is not in a block headed by the line, and any record in which a class, label or annotation lacks it. The report test on synthetic records checks every such line.
"""

import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import atomic_write

from . import core
from .core import COMBINED_LINE, COMPOSITION_WORDS, GUARDED_WORDS, ORACLE_LINE

GUARDED_KEYS = ("class", "classes", "label", "label_with_design", "annotations", "annotation", "cost", "cost_lines", "router", "composition", "mechanism", "mechanisms", "outcome")


class OracleLineMissing(ValueError):
    """A guarded line, table or record without the oracle-assisted line."""


def is_composition(line: str) -> bool:
    return any(w in line for w in COMPOSITION_WORDS)


def is_guarded(line: str) -> bool:
    return any(w in line for w in GUARDED_WORDS)


def block(lines: Iterable[str]) -> str:
    """A block of lines headed by the oracle-assisted line. A markdown table passed here keeps the line directly above its header row."""
    ls = list(lines)
    head = [ORACLE_LINE, COMBINED_LINE] if any(is_composition(ln) for ln in ls) else [ORACLE_LINE]  # a composition line carries the second fixed line as well
    return "\n".join([*head, *ls])


def check_text(text: str) -> None:
    """Every block (separated by a blank line) that contains a guarded line must begin with the oracle-assisted line. A line outside any block is a block of its own."""
    for blk in text.split("\n\n"):
        lines = [ln for ln in blk.split("\n") if ln.strip()]
        if not lines:
            continue
        if any(is_guarded(ln) for ln in lines) and lines[0] != ORACLE_LINE:
            bad = next(ln for ln in lines if is_guarded(ln))
            raise OracleLineMissing(f"guarded line without the oracle-assisted line directly above its block: {bad[:120]!r}")
        if any(is_composition(ln) for ln in lines) and (len(lines) < 2 or lines[1] != COMBINED_LINE):
            bad = next(ln for ln in lines if is_composition(ln))
            raise OracleLineMissing(f"composition line without the second fixed line (combined tasks) directly under the oracle-assisted line: {bad[:120]!r}")


def guarded(record: Mapping[str, Any]) -> dict[str, Any]:
    """A record headed by the oracle-assisted line as a field of the same record."""
    return {"oracle_line": ORACLE_LINE, **record}


def check_record(obj: Any, path: str = "$") -> None:
    """Every mapping that carries a class, label, annotation, cost, router, composition or mechanism field must carry the oracle-assisted line as a field of the same mapping."""
    if isinstance(obj, Mapping):
        if any(k in obj for k in GUARDED_KEYS) and obj.get("oracle_line") != ORACLE_LINE:
            raise OracleLineMissing(f"record at {path} carries a guarded field without the oracle-assisted line")
        if "composition" in obj and obj.get("combined_line") != COMBINED_LINE:
            raise OracleLineMissing(f"record at {path} carries a composition field without the second fixed line (combined tasks)")
        for k, v in obj.items():
            check_record(v, f"{path}.{k}")
    elif isinstance(obj, list | tuple):
        for i, v in enumerate(obj):
            check_record(v, f"{path}[{i}]")


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    """Write a machine-readable record, refusing one that lacks the line where it must have it."""
    check_record(record)
    atomic_write(path, (json.dumps(core.jsonable(record), sort_keys=True, indent=1) + "\n").encode())


def write_text(path: Path, text: str) -> None:
    check_text(text)
    atomic_write(path, text.encode())


def emit(lines: Sequence[str], stream: Any = None) -> None:
    """The one place that prints. A summary for the terminal or a log: a guarded line is printed only inside a block headed by the oracle-assisted line (this function adds the block)."""
    text = "\n".join(lines)
    out = text if not any(is_guarded(ln) for ln in lines) else block(lines)
    check_text(out)
    print(out, file=stream if stream is not None else sys.stdout)


def emit_plain(line: str, stream: Any = None) -> None:
    """A line that carries no class, mechanism, router, composition or cost reading (a path, a refusal, a count). Refused if it does."""
    if is_guarded(line):
        raise OracleLineMissing(f"emit_plain refuses a guarded line: {line[:120]!r}")
    print(line, file=stream if stream is not None else sys.stdout)


def positive_wording_without_line(text: str) -> bool:
    """True if ``text`` would print a positive word outside a block headed by the line (the test of section 11.3 uses it)."""
    try:
        check_text(text)
    except OracleLineMissing:
        return True
    return False
