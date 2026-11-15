# ruff: noqa: E501
"""The general-language panel (ADR-0022 section 6.4): windows of WikiText-2 validation cut on a fixed grid, strata by marker-like strings, selection with the GEN-window seed 220905.

Data-generation side (it needs the reference tokenizer's offsets): the validation file is tokenized once as a whole and cut from its first token into consecutive, non-overlapping windows of
``window`` tokens (256); a trailing remainder is dropped. A window is in the *marker-like* stratum if one of the strings lies wholly within the text of its tokens 1-64 (``decision`` tokens), and in the
*ordinary* stratum if it contains none of the strings anywhere. A window whose only such strings lie after token 64 is in neither stratum and is not used. Strings are matched case-sensitively as
substrings of the raw text; "a line ending in ':'" means a ':' immediately followed by a newline, both within the span in question. 100 windows of each stratum are sampled with the GEN-window seed.
If either stratum has fewer than the wanted count on this grid, neither the grid nor the rule is changed: ``WindowsInsufficient`` is raised and the work returns to the lead before the freeze.
"""

import bisect
from collections.abc import Mapping, Sequence

import torch

from . import core
from .evaluate import GeneralWindow
from .text import normalize
from .tokenization import ReferenceTokenizer


class WindowsInsufficient(RuntimeError):
    """A stratum has fewer windows than wanted: the work returns to the lead before the freeze (nothing is relaxed)."""


def marker_strings() -> list[str]:
    return [*core.CFG["data"]["marker_strings"], core.CFG["data"]["marker_line_ending"] + "\n"]


def first_marker(text: str) -> tuple[int, int] | None:
    """(start, end) character span of the earliest marker-like string in ``text``, or None."""
    best: tuple[int, int] | None = None
    for s in marker_strings():
        k = text.find(s)
        if k >= 0 and (best is None or k < best[0]):
            best = (k, k + len(s))
    return best


def cut_windows(tok: ReferenceTokenizer, text: str, vocab_index: Mapping[str, int], window: int, decision: int) -> list[GeneralWindow]:
    ids, offs = tok.encode_offsets(text)
    starts = [s for s, _ in offs]
    # in-vocabulary words with the last subword of each, over the whole text
    word_last: list[tuple[int, int]] = []  # (token index, vocabulary index)
    pos = 0
    for raw in text.split():
        s = text.index(raw, pos)
        e = s + len(raw)
        pos = e
        norm = normalize(raw)
        if norm in vocab_index:
            k = bisect.bisect_left(starts, e) - 1
            if k >= 0:
                word_last.append((k, vocab_index[norm]))
    out: list[GeneralWindow] = []
    for w0 in range(0, len(ids) - window + 1, window):
        span_head = text[offs[w0][0] : offs[w0 + decision - 1][1]]
        span_all = text[offs[w0][0] : offs[w0 + window - 1][1]]
        fm = first_marker(span_head)
        reads = tuple((k - w0, j) for k, j in word_last if w0 <= k < w0 + window)
        if fm is not None:
            end_char = offs[w0][0] + fm[1]
            last = max(k for k in range(w0, w0 + decision) if offs[k][0] < end_char) - w0
            out.append(GeneralWindow(tuple(ids[w0 : w0 + window]), reads, "marker", last))
        elif first_marker(span_all) is None:
            out.append(GeneralWindow(tuple(ids[w0 : w0 + window]), reads, "ordinary"))
    return out


def select_windows(windows: Sequence[GeneralWindow], per_stratum: Mapping[str, int], generator: torch.Generator) -> list[GeneralWindow]:
    """Sample the wanted number of windows of each stratum with the GEN-window seed (marker-like first, then ordinary). Fewer than wanted in either stratum raises ``WindowsInsufficient``."""
    out: list[GeneralWindow] = []
    for stratum in ("marker", "ordinary"):
        pool = [w for w in windows if w.stratum == stratum]
        want = per_stratum[stratum]
        if len(pool) < want:
            raise WindowsInsufficient(f"stratum {stratum!r} has {len(pool)} windows on the fixed grid, fewer than {want}")
        order = torch.randperm(len(pool), generator=generator).tolist()[:want]
        out += [pool[i] for i in sorted(order)]
    return out
