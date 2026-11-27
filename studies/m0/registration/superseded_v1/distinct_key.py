# ruff: noqa: E501
"""The distinct-item key (ADR-0033 addendum 1, section 10 part A item 1; decided reading (i), section 13 item 1).

    The key of an item is its rendered question with names relabelled; two items with one key are one item.
    Reading (i): names relabelled only, exact duplicates of the rendered question removed.

What "names relabelled" means here, per evaluation (nothing else is relabelled or normalised):

* R1, R2, M1 (text evaluations). A *name* is an occurrence, in the rendered question, of an entry of one of the
  committed word lists of ``studies/m0/vocab.py`` that the builders draw entity names from:
  people (``NAMES``), places (``TOWNS``), events (``EVENTS``, without the leading "the "), objects
  (``OBJECTS``), pets (``PETS``) and invented words (``PSEUDO``, in lower case and capitalised).
  Matching is on whole words, case-sensitive for ``NAMES`` and ``TOWNS`` and on the first letter's case for the
  lower-case lists; a plural ``s``/``es`` and a possessive ``'s`` are not part of the name and stay in the text;
  "a" and "an" before a name are written "a" (the article agrees with the name, it is not part of it).
  Every name is replaced by a placeholder numbered in order of first appearance in the question (one counter
  for all classes), so two questions that differ only by a one-to-one renaming of their names get one key.
  *Labels* (``COLOURS``, ``SHAPES``, ``MARKS``, and any word of those lists that is also in a name list, for
  example "orange"), letters, numbers, weekdays and every other word are NOT relabelled: that is reading (ii).
  One lineage draws a vocabulary word as *data*, not as a name: the invented words that ``R2.caesar_shift``
  asks the solver to shift. They are not names there and are not relabelled (``DATA_VOCABULARY``).
* C1 (code tracing). A *name* is an identifier the program binds or uses: every variable, parameter and
  function name of the program the question shows, except the names of Python's builtins (``len``, ``sum``,
  ``range``, ...) unless the program binds one. The names are replaced, in the program's source text, by
  placeholders numbered in order of first appearance. String literals, numbers, operators, layout and the
  frame sentences are untouched.

The key text is the question with those replacements, byte for byte (no case folding, no Unicode or
whitespace normalisation: "exact duplicates of the rendered question"). The key is the first 16 bytes of the
SHA-256 of that text in UTF-8 (``KEY_BYTES``); for the largest count the stage can ask for (a few hundred
thousand keys) the chance of any two different texts sharing a digest is below 1e-27.

Standard library only; nothing here reads a clock, the environment or ``hash()``.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import io
import re
import tokenize
from collections.abc import Mapping
from typing import Any

KEY_BYTES = 16
KEY_VERSION = "distinct-key-v1 reading (i)"

_OPEN, _CLOSE = "⟦", "⟧"

#: name classes of the text evaluations, in the order the lists are read from ``studies/m0/vocab.py``
NAME_CLASSES = ("people", "places", "events", "objects", "pets", "invented")

#: lineage id -> name classes that are DATA in that lineage and so are not relabelled there
DATA_VOCABULARY: Mapping[str, frozenset[str]] = {
    "R2.caesar_shift": frozenset({"invented"}),
}


def _vocabulary() -> tuple[dict[str, frozenset[str]], frozenset[str]]:
    """Per class, the surface forms to match; and the label words that are never names."""
    from studies.m0 import vocab

    labels = set(vocab.COLOURS) | set(vocab.SHAPES) | {w for m in vocab.MARKS for w in m.split()}
    classes: dict[str, set[str]] = {c: set() for c in NAME_CLASSES}
    classes["people"] |= set(vocab.NAMES)
    classes["places"] |= set(vocab.TOWNS)
    for phrase in vocab.EVENTS:
        classes["events"].add(phrase[4:] if phrase.startswith("the ") else phrase)
    classes["objects"] |= set(vocab.OBJECTS)
    classes["pets"] |= set(vocab.PETS)
    classes["invented"] |= set(vocab.PSEUDO)
    out = {c: frozenset(w for w in ws if w not in labels and w.casefold() not in labels) for c, ws in classes.items()}
    return out, frozenset(labels)


_VOCAB: tuple[dict[str, frozenset[str]], frozenset[str]] | None = None
_INDEXES: dict[frozenset[str], dict[str, tuple[str, ...]]] = {}
_TOKEN = re.compile(r"[A-Za-z0-9]+")
_ALNUM = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def _index(excluded: frozenset[str]) -> dict[str, tuple[str, ...]]:
    """First word (as it may be written) -> the vocabulary phrases that start with it, longest first."""
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = _vocabulary()
    idx = _INDEXES.get(excluded)
    if idx is None:
        classes, _ = _VOCAB
        acc: dict[str, set[str]] = {}
        for c in NAME_CLASSES:
            if c in excluded:
                continue
            for phrase in classes[c]:
                m = _TOKEN.match(phrase)
                if m is None:
                    raise ValueError(f"vocabulary entry {phrase!r} does not start with a word")
                first = m.group(0)
                forms = {first, first[0].upper() + first[1:]} if first[0].islower() else {first}
                for f in forms:
                    acc.setdefault(f, set()).add(phrase)
        idx = {f: tuple(sorted(ps, key=lambda w: (-len(w), w))) for f, ps in acc.items()}
        _INDEXES[excluded] = idx
    return idx


def _spelled(phrase: str, seg: str) -> bool:
    """``seg`` is the phrase: exactly, or with the first letter's case changed when the phrase is lower case."""
    return seg == phrase or (phrase[0].islower() and seg == phrase[0].upper() + phrase[1:])


def find_names(text: str, excluded_classes: frozenset[str] = frozenset()) -> list[tuple[int, int, str, str]]:
    """The names in ``text``: (start, end of the name, the name as written, the plural suffix after it).

    A name is a whole vocabulary entry: preceded and followed by a character that is not an ASCII letter or
    digit, and when it is one word it may be followed by the plural ``s`` or ``es``. Longest entry first at a
    position ("book sale" before "book"); matches do not overlap; reading is left to right.
    """
    idx = _index(excluded_classes)
    out: list[tuple[int, int, str, str]] = []
    n = len(text)
    pos = 0
    for m in _TOKEN.finditer(text):
        s, e = m.span()
        if s < pos:
            continue
        tok = m.group(0)
        hit: tuple[int, int, str, str] | None = None
        keys = [tok]
        if tok.endswith("es") and len(tok) > 2:
            keys.append(tok[:-2])
        if tok.endswith("s") and len(tok) > 1:
            keys.append(tok[:-1])
        for key in keys:
            for phrase in idx.get(key, ()):
                end = s + len(phrase)
                if not _spelled(phrase, text[s:end]):
                    continue
                for suffix in ("", "es", "s"):
                    after = end + len(suffix)
                    if text.startswith(suffix, end) and (after >= n or text[after] not in _ALNUM):
                        hit = (s, end, text[s:end], suffix)
                        break
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is not None:
            out.append(hit)
            pos = hit[1] + len(hit[3])
    return out


_ARTICLE = re.compile(r"(?<![A-Za-z0-9])(?P<art>[Aa]n?) (?=" + _OPEN + ")")


def relabel_text(question: str, excluded_classes: frozenset[str] = frozenset()) -> str:
    """The question with every name replaced by a placeholder in order of first appearance."""
    if _OPEN in question or _CLOSE in question:
        raise ValueError("the question contains a placeholder character")
    ids: dict[str, int] = {}
    parts: list[str] = []
    at = 0
    for start, end, core, suffix in find_names(question, excluded_classes):
        i = ids.setdefault(core.casefold(), len(ids))
        parts.append(question[at:start])
        parts.append(f"{_OPEN}N{i}{_CLOSE}{suffix}")
        at = end + len(suffix)
    parts.append(question[at:])
    out = "".join(parts)
    return _ARTICLE.sub(lambda m: ("A" if m.group("art")[0] == "A" else "a") + " ", out)


# ---------------------------------------------------------------------------------------------- C1


def _bound_and_used(tree: ast.AST) -> tuple[set[str], int]:
    """Names to relabel and the number of their occurrences (Name nodes, parameters, function names)."""
    builtin_names = set(dir(builtins))
    bound: set[str] = set()
    used: set[str] = set()
    occurrences: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            occurrences.append(node.id)
            (bound if isinstance(node.ctx, ast.Store | ast.Del) else used).add(node.id)
        elif isinstance(node, ast.arg):
            occurrences.append(node.arg)
            bound.add(node.arg)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            occurrences.append(node.name)
            bound.add(node.name)
    names = bound | {n for n in used if n not in builtin_names}
    return names, sum(1 for n in occurrences if n in names)


def relabel_source(src: str) -> str:
    """Python source with its variable, parameter and function names replaced in order of first appearance."""
    names, expected = _bound_and_used(ast.parse(src))
    lines = src.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    found: list[tuple[int, int, str]] = []
    prev = ""
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.NAME and tok.string in names and prev != ".":
            a = starts[tok.start[0] - 1] + tok.start[1]
            b = starts[tok.end[0] - 1] + tok.end[1]
            found.append((a, b, tok.string))
        if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT):
            prev = tok.string
    if len(found) != expected:
        raise ValueError(f"identifier occurrences by tokens ({len(found)}) and by the syntax tree ({expected}) differ")
    ids: dict[str, int] = {}
    for _, _, s in found:
        ids.setdefault(s, len(ids))
    out: list[str] = []
    pos = 0
    for a, b, s in found:
        out.append(src[pos:a])
        out.append(f"{_OPEN}V{ids[s]}{_CLOSE}")
        pos = b
    out.append(src[pos:])
    return "".join(out)


def _c1_key_text(question: str, structured: Mapping[str, Any]) -> str:
    from studies.m0.c1grammar import render

    if _OPEN in question or _CLOSE in question:
        raise ValueError("the question contains a placeholder character")
    src = render(structured["program"])
    at = question.find(src)
    if at < 0:
        raise ValueError("the rendered program is not in the question")
    return question[:at] + relabel_source(src) + question[at + len(src) :]


# ---------------------------------------------------------------------------------------------- public


def evaluation_of(lineage_id: str) -> str:
    return lineage_id.split(".", 1)[0]


def key_text(lineage_id: str, question: str, structured: Mapping[str, Any]) -> str:
    """The rendered question with names relabelled (the key, before hashing)."""
    if evaluation_of(lineage_id) == "C1":
        return _c1_key_text(question, structured)
    return relabel_text(question, DATA_VOCABULARY.get(lineage_id, frozenset()))


def item_key(lineage_id: str, question: str, structured: Mapping[str, Any]) -> bytes:
    """The distinct-item key: ``KEY_BYTES`` bytes of the SHA-256 of ``key_text`` in UTF-8."""
    return hashlib.sha256(key_text(lineage_id, question, structured).encode("utf-8")).digest()[:KEY_BYTES]
