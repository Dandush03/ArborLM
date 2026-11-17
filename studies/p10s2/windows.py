# ruff: noqa: E501
"""The general-language panel (ADR-0022 section 6.4): windows of WikiText-2 validation cut on a fixed grid, strata by marker-like strings, selection with the GEN-window seed 220905.

Data-generation side (it needs the reference tokenizer's offsets): the validation file is tokenized once as a whole and cut from its first token into consecutive, non-overlapping windows of
``window`` tokens (256); a trailing remainder is dropped. A window is in the *marker-like* stratum if one of the strings lies wholly within the text of its tokens 1-64 (``decision`` tokens), and in the
*ordinary* stratum if it contains none of the strings anywhere. A window whose only such strings lie after token 64 is in neither stratum and is not used. Strings are matched case-sensitively as
substrings of the raw text; "a line ending in ':'" means a ':' immediately followed by a newline, both within the span in question. The second GEN decision is taken at the last token of the first marker-like
string EXTENDED THROUGH a colon that immediately follows it (never beyond token 64), so it can land on the colon every task prompt ends on. Every window of the marker-like stratum is taken (44 on the registered grid, stated in the configuration) and 100 ordinary windows are sampled with the GEN-window seed (ruling of 2026-11-16).
If either stratum has fewer than the wanted count on this grid, neither the grid nor the rule is changed: ``WindowsInsufficient`` is raised and the work returns to the lead before the freeze.
"""

from collections.abc import Mapping, Sequence

import torch

from . import core
from .evaluate import GeneralWindow
from .text import normalize
from .tokenization import ReferenceTokenizer, last_token_before, word_letters_end


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
        pos = s + len(raw)
        norm = normalize(raw)
        if norm in vocab_index:
            k = last_token_before(starts, word_letters_end(raw, s))  # the word's last subword, never a following punctuation token (audit C-M5)
            if k is not None:
                word_last.append((k, vocab_index[norm]))
    out: list[GeneralWindow] = []
    for w0 in range(0, len(ids) - window + 1, window):
        span_head = text[offs[w0][0] : offs[w0 + decision - 1][1]]
        span_all = text[offs[w0][0] : offs[w0 + window - 1][1]]
        fm = first_marker(span_head)
        reads = tuple((k - w0, j) for k, j in word_last if w0 <= k < w0 + window)
        if fm is not None:
            end_char = offs[w0][0] + fm[1]
            if text[end_char : end_char + 1] == ":":  # the lead's ruling m9: extended through a colon that immediately follows the string, so the decision can land on the position every task prompt ends on
                end_char += 1
            last = max(k for k in range(w0, w0 + decision) if offs[k][0] < end_char) - w0
            out.append(GeneralWindow(tuple(ids[w0 : w0 + window]), reads, "marker", last))
        elif first_marker(span_all) is None:
            out.append(GeneralWindow(tuple(ids[w0 : w0 + window]), reads, "ordinary"))
    return out


def select_windows(windows: Sequence[GeneralWindow], per_stratum: Mapping[str, int], generator: torch.Generator, *, take_all: Sequence[str] = (), exact: Mapping[str, int] | None = None) -> list[GeneralWindow]:
    """The GEN panel: for a stratum in ``take_all`` every window of the stratum on the fixed grid (nothing is sampled; ``exact`` states the count the rule must find, and any other count raises
    ``WindowsInsufficient``: the lead's ruling of 2026-11-16 for the marker-like stratum, 44); any other stratum is sampled to ``per_stratum`` with the GEN-window seed. The generator is advanced by one
    permutation of the pool for EVERY stratum, taken or sampled, in the order marker-like then ordinary, so the ordinary sample is the one the earlier code drew (it drew the marker-like permutation first).
    Fewer windows than wanted in a sampled stratum raises ``WindowsInsufficient``."""
    out: list[GeneralWindow] = []
    for stratum in ("marker", "ordinary"):
        pool = [w for w in windows if w.stratum == stratum]
        order = torch.randperm(len(pool), generator=generator).tolist()  # drawn for every stratum: the generator state before the ordinary draw is what it always was
        if stratum in take_all:
            want = (exact or {}).get(stratum)
            if want is not None and len(pool) != want:
                raise WindowsInsufficient(f"stratum {stratum!r} has {len(pool)} windows on the fixed grid, the configuration states {want}: the work returns to the lead (nothing is relaxed)")
            if not pool:
                raise WindowsInsufficient(f"stratum {stratum!r} has no window on the fixed grid")
            out += pool
            continue
        want = per_stratum[stratum]
        if len(pool) < want:
            raise WindowsInsufficient(f"stratum {stratum!r} has {len(pool)} windows on the fixed grid, fewer than {want}")
        out += [pool[i] for i in sorted(order[:want])]
    return out
