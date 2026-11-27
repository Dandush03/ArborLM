# ruff: noqa: E501
"""Scorers and answer grammars (ADR-0033 section 7, "Answer extraction" and "Answer grammar").

Rule, as registered: the text after the LAST answer marker that begins its own line; trimmed; case-folded;
whitespace collapsed; one final full stop removed; numbers compared as decimals after removing thousands separators.
No extractable answer scores 0 and is a format failure; a limit reached without an answer scores 0 and is counted
separately (limit hit). Every score is in {0, 1}, given by a rule; no model grades anything.

Readings chosen for the least favourable result (ruling needed, see studies/m0/NOTES.md): the marker must begin its
line; an empty marker line is no answer; text outside the registered grammar of the answer type is a format failure;
a list is plain comma-separated items without brackets; a number has no currency sign, percent sign or unit.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from studies.m0.core import stream

# Three candidate answer-marker conventions (PROPOSED; the instruction wording that goes with them is not written here).
FORMAT_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[ \t]*answer[ \t]*:[ \t]*(.*?)[ \t]*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^[ \t]*final answer[ \t]*:[ \t]*(.*?)[ \t]*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^[ \t]*####[ \t]*(.*?)[ \t]*$", re.MULTILINE),
)

_WS = re.compile(r"\s+")
_NUM = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$")
_LIST = re.compile(r"^-?\d+(?:\s*,\s*-?\d+)*$")

CLOSED_WORDS = {"ynu": {"yes", "no", "cannot be determined"}, "yn": {"yes", "no"}}


def extract(raw: str, fmt: int) -> str | None:
    """Text after the last answer marker on its own line; None when there is none or it is empty."""
    last: str | None = None
    for m in FORMAT_MARKERS[fmt].finditer(raw):
        last = m.group(1)
    if last is None:
        return None
    return last if last.strip() else None


def normalise_answer(text: str) -> str:
    t = _WS.sub(" ", text.strip().casefold()).strip()
    if t.endswith("."):
        t = t[:-1].rstrip()
    return t


def in_grammar(answer_type: str, norm: str) -> bool:
    if norm == "":
        return False
    if answer_type == "number":
        return bool(_NUM.match(norm))
    if answer_type == "letter":
        return bool(re.match(r"^[a-j]$", norm))
    if answer_type in CLOSED_WORDS:
        return norm in CLOSED_WORDS[answer_type]
    if answer_type == "word":
        return bool(re.match(r"^[a-z]+$", norm))
    if answer_type == "name":
        return bool(re.match(r"^[a-z][a-z' -]*$", norm))
    if answer_type == "list":
        return bool(_LIST.match(norm))
    if answer_type in ("text", "line"):
        return "\n" not in norm
    raise ValueError(f"unknown answer type {answer_type}")


def canon(answer_type: str, norm: str) -> str:
    """Canonical comparison form of an in-grammar normalised answer."""
    if answer_type == "number":
        return str(Decimal(norm.replace(",", "")).normalize())
    if answer_type == "list":
        return ",".join(p.strip() for p in norm.split(","))
    return norm


@dataclass(frozen=True)
class Scored:
    score: int
    status: str  # correct | incorrect | format_failure | limit_hit
    extracted: str | None


def _valid(raw: str, fmt: int, answer_type: str) -> tuple[str | None, str | None]:
    ex = extract(raw, fmt)
    if ex is None:
        return None, None
    norm = normalise_answer(ex)
    return (ex, norm) if in_grammar(answer_type, norm) else (ex, None)


def score(raw: str, finish_reason: str, answer_type: str, gold: str, fmt: int) -> Scored:
    ex, norm = _valid(raw, fmt, answer_type)
    if norm is None:
        return Scored(0, "limit_hit" if finish_reason == "length" else "format_failure", ex)
    try:
        ok = canon(answer_type, norm) == canon(answer_type, normalise_answer(gold))
    except InvalidOperation:
        return Scored(0, "format_failure", ex)
    return Scored(int(ok), "correct" if ok else "incorrect", ex)


def score_any(raw: str, finish_reason: str, golds: Sequence[str], fmt: int) -> Scored:
    """Public free-text scoring (PopQA aliases, ReCoRD gold entities): exact match of the normalised extracted answer
    against any normalised gold string, never a substring match in free text."""
    ex, norm = _valid(raw, fmt, "text")
    if norm is None:
        return Scored(0, "limit_hit" if finish_reason == "length" else "format_failure", ex)
    ok = any(norm == normalise_answer(g) for g in golds)
    return Scored(int(ok), "correct" if ok else "incorrect", ex)


def chance_level(ks: Sequence[int | None]) -> float:
    """c: the item mean of 1/k_i for closed answers, 0 for open answers."""
    return sum((1.0 / k) if k else 0.0 for k in ks) / len(ks)


@dataclass(frozen=True)
class HandLabel:
    raw: str
    finish_reason: str
    answer_type: str
    gold: str
    fmt: int
    label: str  # correct | incorrect | format_failure | limit_hit


def check_hand_labels(labels: Sequence[HandLabel]) -> list[tuple[int, str, str]]:
    """Return (index, hand label, scorer status) for every disagreement. Any disagreement is an engineering stop."""
    bad = []
    for i, h in enumerate(labels):
        got = score(h.raw, h.finish_reason, h.answer_type, h.gold, h.fmt).status
        if got != h.label:
            bad.append((i, h.label, got))
    return bad


def draw_label_sample(record_ids_by_system: dict[str, Sequence[str]], n: int, seed: int = 400013) -> list[tuple[str, str]]:
    """Registered hand-label sample: ``n`` (system, record id) pairs, stratified evenly over systems (largest
    remainder, ties to the lower system name), each system's draw without replacement from a derived stream."""
    systems = sorted(record_ids_by_system)
    base, extra = divmod(n, len(systems))
    out: list[tuple[str, str]] = []
    for i, sysname in enumerate(systems):
        k = base + (1 if i < extra else 0)
        ids = sorted(record_ids_by_system[sysname])
        r = stream(seed, "hand-labels", sysname)
        out.extend((sysname, x) for x in r.sample(ids, min(k, len(ids))))
    return out
